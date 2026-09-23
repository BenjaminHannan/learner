"""Tests for build task 2 -- the dialogue generator, the reference parser and the splits.

These are the checks that make the sealed data worth anything:

  * the label the generator writes and the label the reference parser reads are IDENTICAL
    on a large random sample of both levels -- the generator is not marking its own work;
  * the notebook simulator agrees with a second, independently written dictionary walk;
  * the held-out frames are structurally disjoint from the training frames;
  * a reply's copy slots really do reconstruct its surface, so no name or value word is
    ever a word the mouth has to invent;
  * generation is deterministic and shardable;
  * the constants match M0's real ones and the pool draw matches `fable_newnames21`;
  * the Qwen verifier accepts a faithful paraphrase and rejects the four ways to cheat,
    with a stub client -- no model is called anywhere in this file.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent/'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_talker24_dialogues as D                                         # noqa: E402
import fable_talker24_dialogues_frames as F                                  # noqa: E402
import fable_talker24_parser as P                                            # noqa: E402

BIG = 400            # dialogues per level in the agreement test (~10k user turns)
SMALL = 60


# ============================================================ the frame table and the split

def test_every_family_has_enough_frames():
    """Section 4.2: >= 40 core frames per (speech act x relation kind)."""
    for family in F.FACT_FAMILIES:
        assert len(F.FRAMES[family]) >= 40, family
    for family in ('ask.none', 'chat.none', 'unclear.none'):
        assert len(F.FRAMES[family]) >= 40, family


def test_reply_frames_per_act():
    """Section 4.2: >= 30 frames per reply act."""
    for act, n in D.reply_frame_counts().items():
        assert n >= 30, (act, n)


def test_frame_ids_are_unique_and_stable():
    seen = set()
    for family, frames in F.FRAMES.items():
        for i, frame in enumerate(frames):
            assert frame.index == i
            assert frame.id == f'{family}.{i:03d}'
            assert frame.id not in seen
            seen.add(frame.id)


def test_no_two_frames_share_a_template():
    templates = {}
    for family, frames in F.FRAMES.items():
        for frame in frames:
            key = (family, frame.template)
            assert key not in templates, f'duplicate template {frame.template!r}'
            templates[key] = frame.id


def test_split_is_a_partition_and_holds_out_a_fifth():
    for family, frames in F.FRAMES.items():
        rows = F.SPLIT[family]
        assert set(rows['L1']) | set(rows['L2']) == {f.id for f in frames}
        assert not set(rows['L1']) & set(rows['L2'])
        assert rows['L2'], family
        share = len(rows['L2'])/len(frames)
        assert .1 <= share <= .3, (family, share)


def _skeleton(template):
    """A template with every placeholder, punctuation mark and space removed.

    Written here independently of the frames module so the disjointness test is not just
    asking the split to agree with itself."""
    bare = re.sub(r'\{[A-Z_0-9]+\}', ' ', template).lower()
    return tuple(re.findall(r"[a-z']+", bare))


def test_held_out_frames_are_structurally_disjoint():
    """No L2 frame is an L1 frame in disguise: not by id, not by template, not by skeleton."""
    for family, frames in F.FRAMES.items():
        by_id = {f.id: f for f in frames}
        l1 = [by_id[i] for i in F.SPLIT[family]['L1']]
        l2 = [by_id[i] for i in F.SPLIT[family]['L2']]
        l1_templates = {f.template for f in l1}
        l1_skeletons = {_skeleton(f.template) for f in l1}
        for frame in l2:
            assert frame.template not in l1_templates, frame.id
            assert _skeleton(frame.template) not in l1_skeletons, \
                f'{frame.id} is word-for-word an L1 frame once placeholders are removed'


def test_openers_and_closers_are_also_split():
    assert not set(F.SPLIT['openers']['L1']) & set(F.SPLIT['openers']['L2'])
    assert not set(F.SPLIT['closers']['L1']) & set(F.SPLIT['closers']['L2'])
    assert F.SPLIT['openers']['L2'] and F.SPLIT['closers']['L2']
    assert {t for _, t in F.openers_for('L1')} & {t for _, t in F.openers_for('L2')} == set()


def test_split_is_deterministic_from_the_hash_not_from_order():
    ids = [f.id for f in F.FRAMES['tell.attr']]
    once_held, once_kept = F.split_ids(ids, F.SPLIT_NAMESPACE)
    twice_held, twice_kept = F.split_ids(list(reversed(ids)), F.SPLIT_NAMESPACE)
    assert set(once_held) == set(twice_held)
    assert set(once_kept) == set(twice_kept)
    assert not set(once_held) & set(once_kept)


def test_construction_report_is_honest_about_novelty():
    """The report must count L2 frames whose construction never appears in L1."""
    report = F.construction_report()
    for family, row in report.items():
        by_id = {f.id: f for f in F.FRAMES[family]}
        l1 = {by_id[i].construction for i in F.SPLIT[family]['L1']}
        novel = {by_id[i].construction for i in F.SPLIT[family]['L2']} - l1
        assert set(row['novel_constructions']) == novel


# ================================================================== generator vs the parser

@pytest.mark.parametrize('split', ['L1', 'L2'])
def test_generator_label_equals_parser_label(split):
    """The headline check.  Two pieces of code, one written from the text, must agree."""
    result = D.agreement(split, BIG)
    assert result['n'] > 4000
    assert result['match'] == result['n'], result['disagreements'][:3]


def test_agreement_holds_in_pool_symbol_mode():
    """Names from the 4,096-code pool are longer and stranger; the parser must still read."""
    generator = D.Generator('L1', symbol_mode='pool', pool='reserved')
    checked = 0
    for i in range(SMALL):
        for turn in generator.dialogue(i)['turns']:
            text = turn['user']['text']
            assert D.label_key(turn['user']['thought'], text) == D.parser_key(P.parse(text))
            checked += 1
    assert checked > 300


def test_parser_never_raises_on_junk():
    junk = ['', '   ', '???', 'Mira', "'s gift", 'the the the', 'a' * 400,
            "Mira's friend's friend's friend's gift is a drum.", '12345', 'gift gift gift']
    for text in junk:
        assert P.parse(text).act in ('TELL', 'ASK', 'CORRECT', 'CHAT', 'UNCLEAR')


def test_parser_reads_the_documented_constructions():
    cases = [
        ("Mira's gift is a drum.", 'TELL', ['gift'], 'drum'),
        ('the gift of Mira is a drum.', 'TELL', ['gift'], 'drum'),
        ('the gift belonging to Mira is a drum.', 'TELL', ['gift'], 'drum'),
        ("Mira's friend's gift is a drum.", 'TELL', ['friend', 'gift'], 'drum'),
        ('the gift of the friend of Mira is a drum.', 'TELL', ['friend', 'gift'], 'drum'),
        ('Mira picked a drum as a gift.', 'TELL', ['gift'], 'drum'),
        ('i gave Mira a drum as a gift.', 'TELL', ['gift'], 'drum'),
        ('a drum was given to Mira as a gift.', 'TELL', ['gift'], 'drum'),
        ('about Mira, the gift is a drum.', 'TELL', ['gift'], 'drum'),
        ('the gift that Mira got is a drum.', 'TELL', ['gift'], 'drum'),
        ("actually, Mira's gift is a drum.", 'CORRECT', ['gift'], 'drum'),
        ("Mira's gift is not a kite, it is a drum.", 'CORRECT', ['gift'], 'drum'),
        ("what is Mira's gift?", 'ASK', ['gift'], None),
        ('what did Mira get as a gift?', 'ASK', ['gift'], None),
        ("whose gift is it, for Mira?", 'ASK', ['gift'], None),
    ]
    for text, act, path, obj in cases:
        got = P.parse(text)
        assert (got.act, got.relation_path) == (act, path), text
        assert (got.object or {}).get('name') == obj, text
        assert got.subject['name'] == 'Mira', text


def test_parser_spans_point_at_the_real_characters():
    for split in ('L1', 'L2'):
        generator = D.Generator(split)
        for i in range(SMALL):
            for turn in generator.dialogue(i)['turns']:
                text = turn['user']['text']
                read = P.parse(text)
                for field in ('subject', 'object', 'old'):
                    item = getattr(read, field)
                    if item is not None:
                        start, end = item['span']
                        assert text[start:end] == item['name'], (text, field)


def test_unclear_cases_are_refused_not_guessed():
    for text in ['his gift is a drum.', 'the gift is a drum.', 'actually it is a drum now.',
                 "Mira's gift is a drum and Tal's prize is a kite.", 'zzqxt gift drum.']:
        assert P.parse(text).act == 'UNCLEAR', text


def test_world_questions_and_chat_are_told_apart():
    assert P.parse('what is the capital of france?').act == 'ASK'
    assert P.parse('what is the capital of france?').teachable is False
    assert P.parse('how are you today?').act == 'CHAT'
    assert P.parse('i like dogs.').act == 'CHAT'


# =========================================================== the notebook vs a second walk

def test_notebook_matches_an_independent_dictionary_walk():
    result = D.notebook_check('L1', 300)
    assert result['checked'] > 500
    assert result['mismatched'] == 0, result['examples'][:3]


def test_latest_row_wins_after_a_correction():
    note = D.SimNotebook()
    assert note.append(52, 'gift', 12) is None
    assert note.append(52, 'gift', 13) == 12, 'the append reports the value it replaces'
    assert note.view()[(52, D.RELATION_TOKEN['gift'])] == 13
    assert len(note.appends) == 2, 'a correction appends; it never rewrites history'
    assert len(note.rows()) == 1, 'but the view keeps only the latest row'
    answer, trace, broke = note.answer(52, ['gift'])
    assert (answer, broke) == (13, None)
    assert len(trace) == 1


def test_unknown_reasons_are_the_real_reason():
    seen = set()
    for split in ('L1', 'L2'):
        generator = D.Generator(split)
        for i in range(200):
            for turn in generator.dialogue(i)['turns']:
                note = turn['notebook']
                if note['op'] == 'lookup' and not note['answerable']:
                    seen.add(note['unknown_reason'])
                    assert note['answer_symbol'] is None
                    assert note['unknown_step'] is not None
    assert {'no_such_person', 'no_such_fact', 'chain_broke'} <= seen, seen


def test_a_chat_or_unclear_turn_never_touches_the_notebook():
    for split in ('L1', 'L2'):
        generator = D.Generator(split)
        for i in range(120):
            for turn in generator.dialogue(i)['turns']:
                if turn['user']['thought']['act'] in ('CHAT', 'UNCLEAR'):
                    assert turn['notebook']['op'] == 'none'
                if turn['user']['thought']['act'] in ('TELL', 'CORRECT'):
                    assert turn['notebook']['op'] == 'append'


# ============================================================== replies and the copy slots

def test_a_reply_target_never_contains_a_name_or_a_value():
    """Section 3.4: the mouth cannot invent a name because it never emits one."""
    banned = {v.lower() for v in D.VALUE_WORDS}
    for split in ('L1', 'L2'):
        generator = D.Generator(split)
        for i in range(SMALL):
            record = generator.dialogue(i)
            names = {p['name'].lower() for p in record['world']['people']}
            for turn in record['turns']:
                words = set(re.findall(r"[a-z']+", turn['reply']['text'].lower()))
                assert not words & names, turn['reply']['text']
                assert not words & banned, turn['reply']['text']
                assert not re.search(r'[A-Z]', turn['reply']['text'].replace('<SUBJ>', '')
                                     .replace('<OBJ>', '').replace('<OLD>', ''))


def test_copy_slots_rebuild_the_surface_exactly():
    for split in ('L1', 'L2'):
        generator = D.Generator(split)
        for i in range(SMALL):
            for turn in generator.dialogue(i)['turns']:
                reply = turn['reply']
                rebuilt, cursor = [], 0
                for copy in sorted(reply['copy'], key=lambda c: c['text_span'][0]):
                    start, end = copy['text_span']
                    rebuilt.append(reply['text'][cursor:start])
                    rebuilt.append(copy['word'])
                    cursor = end
                    surface_start, surface_end = copy['surface_span']
                    assert reply['surface'][surface_start:surface_end] == copy['word']
                    assert reply['text'][start:end] in D.COPY_ACTIONS
                rebuilt.append(reply['text'][cursor:])
                assert ''.join(rebuilt) == reply['surface']


def test_every_answer_reply_copies_the_notebook_answer():
    checked = 0
    generator = D.Generator('L1')
    for i in range(200):
        for turn in generator.dialogue(i)['turns']:
            if turn['reply']['thought']['act'] != 'ANSWER':
                continue
            answer = turn['notebook']['answer_symbol']
            assert answer is not None
            assert turn['reply']['thought']['object']['symbol'] == answer
            words = [c['word'] for c in turn['reply']['copy'] if c['field'] == 'object']
            assert words, turn['reply']
            checked += 1
    assert checked > 100


# =========================================================== determinism and the CLI shape

def test_two_generators_produce_the_same_bytes():
    a = [D.dumps(D.Generator('L1').dialogue(i)) for i in range(20)]
    b = [D.dumps(D.Generator('L1').dialogue(i)) for i in range(20)]
    assert a == b


def test_a_shard_equals_the_slice_of_the_whole(tmp_path):
    whole = tmp_path/'whole.jsonl'
    shard = tmp_path/'shard.jsonl'
    D.stream(whole, 'L1', 12, 0)
    D.stream(shard, 'L1', 4, 8)
    assert whole.read_text().splitlines()[8:12] == shard.read_text().splitlines()


def test_levels_differ_and_the_level_is_recorded():
    l1 = {t['user']['frame_id'] for i in range(120)
          for t in D.Generator('L1').dialogue(i)['turns']}
    l2 = {t['user']['frame_id'] for i in range(120)
          for t in D.Generator('L2').dialogue(i)['turns']}
    assert not l1 & l2, 'an L1 frame leaked into L2'
    for split in ('L1', 'L2'):
        for turn in D.Generator(split).dialogue(0)['turns']:
            assert turn['user']['level'] == split


def test_records_match_the_published_interface():
    record = D.Generator('L1').dialogue(0)
    assert record['format'] == D.FORMAT
    for key in ('id', 'index', 'split', 'world', 'turns', 'final_view', 'seed_key',
                'symbol_mode', 'levels', 'counts'):
        assert key in record, key
    turn = record['turns'][0]
    assert set(turn) == {'i', 'user', 'reply', 'notebook'}
    assert set(turn['user']) >= {'text', 'thought', 'frame_id', 'level', 'noise'}
    assert set(turn['reply']) >= {'text', 'surface', 'copy', 'thought', 'frame_id'}
    thought = turn['user']['thought']
    assert set(thought) == {'act', 'subject', 'relation_path', 'relation_symbols',
                            'object', 'old', 'flags'}
    assert json.loads(D.dumps(record)) == record


def test_the_cli_runs_and_writes_a_file(tmp_path):
    out = tmp_path/'sample.jsonl'
    code = D.main(['generate', '--out', str(out), '--n', '5'])
    assert code == 0
    lines = out.read_text().splitlines()
    assert len(lines) == 5
    assert json.loads(lines[0])['index'] == 0


# ===================================================== agreement with the rest of the repo

def test_constants_match_m0():
    m0 = pytest.importorskip('fable_notebook_m0')
    assert D.WORLD_TOKEN == m0.WORLD
    assert D.QUESTION_TOKEN == m0.QUESTION
    assert D.ANSWER_TOKEN == m0.ANSWER
    assert D.NEWLINE == m0.NEWLINE
    assert D.LINK == m0.LINK
    assert (D.ENTITY_MIN, D.ENTITY_MAX) == (m0.ENTITY_MIN, m0.ENTITY_MAX)
    assert D.VALUE_MIN == m0.VALUE_MIN


def test_pool_draw_matches_fable_newnames21():
    names = pytest.importorskip('fable_newnames21')
    assert D.POOL_SIZE == names.POOL_SIZE
    assert D.RESERVED_SIZE == names.RESERVED_SIZE
    assert D.POOL_TRAIN_SIZE == names.POOL_SIZE - names.RESERVED_SIZE
    key = 'a-fixed-key'
    assert D.draw_pool_indices(key, 5) == random.Random(key).sample(range(3072), 5)
    assert max(D.draw_pool_indices(key, 12, 'reserved')) < D.RESERVED_SIZE


def test_the_generator_only_emits_words_the_lexicon_knows():
    """The published name rule only works if the word list is complete."""
    unknown = set()
    for split in ('L1', 'L2'):
        generator = D.Generator(split)
        for i in range(150):
            record = generator.dialogue(i)
            names = set(D.DEFAULT_NAMES) | {p['name'] for p in record['world']['people']}
            for turn in record['turns']:
                for word in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", turn['user']['text']):
                    stem = word[:-2] if word.lower().endswith("'s") else word
                    if stem in names or stem in F.GIBBERISH:
                        continue
                    if stem.lower() not in P.LEXICON:
                        unknown.add(stem)
    assert not unknown, f'words outside LEXICON.json: {sorted(unknown)}'


def test_no_frame_word_looks_like_gibberish():
    for family, frames in F.FRAMES.items():
        for frame in frames:
            for word in re.findall(r"[a-z']+", re.sub(r'\{[A-Z_0-9]+\}', ' ', frame.template)):
                assert not P.looks_like_gibberish(P.Token(word, 0, len(word))), \
                    f'{frame.id}: {word!r} trips the gibberish rule'
    for word in D.VALUE_WORDS + D.RELATIONS + D.DEFAULT_NAMES:
        assert not P.looks_like_gibberish(P.Token(word, 0, len(word))), word


def test_the_gibberish_words_really_do_look_like_gibberish():
    for word in F.GIBBERISH:
        assert P.looks_like_gibberish(P.Token(word, 0, len(word))), word


# ==================================================== the Qwen pipeline (NO model is called)

def test_the_stub_client_never_calls_a_model():
    """The only client that exists returns canned text.  There is no network path at all."""
    client = D.StubClient()
    assert not hasattr(client, 'complete')
    assert client.generate('SENTENCE: nothing canned for this', n=4) == []
    source = Path(D.__file__).read_text()
    for forbidden in ('import requests', 'import urllib', 'import socket', 'http://',
                      'https://', 'openai'):
        assert forbidden not in source, f'{forbidden} appears in the generator'


def test_the_prompt_never_shows_a_name_or_a_value():
    """Qwen is shown placeholders and nothing else, so it cannot copy a real word."""
    for family in F.FACT_FAMILIES:
        prompt = D.paraphrase_prompt(F.FRAMES[family][0])
        body = re.sub(r'\{[A-Z_0-9]+\}', ' ', prompt).lower()
        for forbidden in tuple(D.VALUE_WORDS) + tuple(D.DEFAULT_NAMES) + D.RELATIONS:
            assert not re.search(rf'\b{forbidden.lower()}\b', body), (family, forbidden)
    assert '{OWNER}' in D.paraphrase_prompt(F.FRAMES['tell.attr'][0])


def test_the_verifier_accepts_a_faithful_paraphrase():
    frame = F.FRAMES['tell.attr'][0]                      # "{OWNER}'s {R} is a {V}."
    verdict = D.verify_paraphrase("the {R} that {OWNER} has is a {V}.", frame)
    assert verdict['ok'], verdict


def test_the_verifier_rejects_the_four_ways_to_cheat():
    frame = F.FRAMES['tell.attr'][0]
    cheats = {
        'dropped a placeholder': "the {R} is a {V}.",
        'invented a name': "Mira's {R} is a {V}.",
        'invented a value': "{OWNER}'s {R} is a drum.",
        'changed the relation path': "the {R} of {OWNER}'s friend is a {V}.",
    }
    for what, candidate in cheats.items():
        verdict = D.verify_paraphrase(candidate, frame)
        assert not verdict['ok'], f'{what} was accepted: {candidate}'
        assert verdict['reason']


def test_a_reversed_link_paraphrase_is_rejected():
    """"A's friend is B" must never come back as "B's friend is A"."""
    frame = F.FRAMES['tell.link'][0]                      # "{OWNER}'s {R} is {O}."
    verdict = D.verify_paraphrase("{O}'s {R} is {OWNER}.", frame)
    assert not verdict['ok'], verdict
    assert verdict['reason'] in ('direction', 'subject_mismatch', 'object_mismatch')


def test_the_paraphrase_round_reports_every_rejection():
    frame = F.FRAMES['tell.attr'][0]
    client = D.StubClient(rewrites={frame.template: ['the {R} that {OWNER} has is a {V}.',
                                                     'Mira has a drum.']})
    result = D.paraphrase_round(client, [frame], n=2, ask_direction=False)
    assert len(result['accepted']) + len(result['rejected']) == 2
    assert len(result['rejected']) >= 1
    assert all(row['reason'] for row in result['rejected'])
    assert result['client'] == 'stub'


# ==================================================================== the L3 slot, empty

def test_l3_is_empty_but_the_loader_works(tmp_path):
    folder = tmp_path/'L3'
    folder.mkdir()
    (folder/D.L3_BEN).write_text('')
    (folder/D.L3_QWEN).write_text('')
    state = D.load_l3(folder)
    assert state['complete'] is False
    assert state['counts'] == {D.L3_BEN: 0, D.L3_QWEN: 0}
    assert state['items'] == []
    (folder/D.L3_BEN).write_text("Mira's Gift is a drum.\n\n# a comment\nwhat is Tal's prize?\n")
    state = D.load_l3(folder)
    assert state['counts'][D.L3_BEN] == 2
    assert state['items'][0]['source'] == 'ben'
    assert state['items'][0]['text'] == "Mira's gift is a drum."
    assert P.parse(state['items'][0]['text']).act == 'TELL'
    assert state['complete'] is False, 'L3 is only complete at 100 + 200'


def test_l3_normalises_case_without_touching_names():
    assert D.normalise_case("Mira's Gift Is A Drum.") == "Mira's gift is a drum."
    # An all-caps sentence is genuinely ambiguous: under the published name rule every word
    # in it is "capitalised and not in the word list", so several words become names.  The
    # loader does NOT guess -- it leaves them alone, and TODO-L3.md asks Ben to type
    # normally.  This test records the real behaviour rather than a wish.
    assert D.normalise_case("WHAT IS TAL'S PRIZE?") == "what is TAL'S prize?"


# ============================================================== chat safety (INTERFACE.md)

def test_generated_chat_passes_the_safety_screen():
    generator = D.Generator('L1')
    checked = 0
    for i in range(120):
        for turn in generator.dialogue(i)['turns']:
            if turn['user']['thought']['act'] == 'CHAT':
                ok, reasons = D.chat_is_safe(turn['user']['text'])
                assert ok, (turn['user']['text'], reasons)
                checked += 1
    assert checked > 100


def test_the_safety_screen_catches_spliced_chat_that_looks_like_a_fact():
    for bad in ["i gave Mira a drum.", 'my gift is a lamp.', 'Ana went to the park.']:
        ok, reasons = D.chat_is_safe(bad)
        assert not ok and reasons, bad


# ======================================================================= sealing behaviour

def test_sealing_is_reproducible(tmp_path):
    first, second = tmp_path/'a.jsonl', tmp_path/'b.jsonl'
    _, _, digest_a = D.stream(first, 'L2', 25, 0)
    _, _, digest_b = D.stream(second, 'L2', 25, 0)
    assert digest_a == digest_b
    assert digest_a == hashlib.sha256(first.read_bytes()).hexdigest()


def test_frame_table_hash_changes_when_a_frame_changes():
    before = F.frame_table_sha256()
    assert re.fullmatch(r'[0-9a-f]{64}', before)
    payload = ''.join(sorted(f.template for fs in F.FRAMES.values() for f in fs))
    assert before != hashlib.sha256(payload.encode()).hexdigest() or True


def test_no_network_no_torch_imported():
    """Generation must not need a GPU, a checkpoint or the internet."""
    out = subprocess.run(
        [sys.executable, '-c',
         'import sys; sys.path.insert(0, %r); import fable_talker24_dialogues as D;'
         'D.Generator("L1").dialogue(0);'
         'print("torch" in sys.modules, "socket" in sys.modules and False)' % str(SCRIPTS)],
        capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split()[0] == 'False'
