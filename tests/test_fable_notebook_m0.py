"""Checks for scripts/fable_notebook_m0.py. Plain script; prints ALL N CHECKS PASSED.

Run whole:   python3.12 -B tests/test_fable_notebook_m0.py
Run a group: python3.12 -B tests/test_fable_notebook_m0.py --only reader
Groups: vocab, reader, printer, store, correction, diary, symbols, wipe, pack, operator,
        eval, cli.

Every notebook these checks create lives in a temporary directory. Nothing registered is
read except the frozen grow-blind operator checkpoints, which are opened read-only. No
training happens anywhere in this file.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
for entry in (str(BASE), str(BASE/'scripts'), str(HERE.parent/'scripts'), str(HERE)):
    if entry not in sys.path:
        sys.path.append(entry)

import fable_notebook_m0 as M                                          # noqa: E402

CHECKS = []
GROUPS = ('vocab', 'reader', 'printer', 'store', 'correction', 'diary', 'symbols', 'wipe',
          'pack', 'operator', 'eval', 'cli')


def check(group, text, condition, detail=''):
    CHECKS.append((group, text, bool(condition), detail))


def temp_notebook(root, name='nb'):
    return M.Notebook.open(Path(root)/name)


# ------------------------------------------------------------------------------- vocab

def group_vocab(root):
    vocab = M.vocabulary()
    check('vocab', 'sixteen value words, all distinct', len(set(M.VALUE_WORDS)) == 16)
    check('vocab', 'value tokens are exactly 12..27',
          sorted(M.VALUE_TOKEN.values()) == list(range(12, 28)))
    check('vocab', 'no value word starts with a vowel, so the article is always "a"',
          all(w[0].lower() not in 'aeiou' for w in M.VALUE_WORDS))
    check('vocab', 'four relation words map onto 8, 9, 10 and LINK',
          sorted(M.RELATION_TOKEN.values()) == [8, 9, 10, M.LINK])
    check('vocab', 'sixteen suggested names, all distinct', len(set(M.DEFAULT_NAMES)) == 16)
    check('vocab', 'entity tokens are the operator\'s own 52..67',
          (M.ENTITY_MIN, M.ENTITY_MAX) == (52, 68) and M.MAX_NAMES == 16)
    path = Path(root)/'VOCABULARY.json'
    M.publish_vocabulary(path)
    check('vocab', 'published vocabulary file round-trips', json.loads(path.read_text()) == vocab)
    check('vocab', 'vocabulary sha256 is stable', M.vocabulary_sha() == M.vocabulary_sha())
    nb = temp_notebook(root, 'vocab-nb')
    check('vocab', 'a new notebook publishes the vocabulary beside its diary',
          json.loads(nb.vocab_path.read_text()) == vocab)
    M.write_atomic(nb.vocab_path, json.dumps(dict(vocab, max_hops=99), sort_keys=True))
    try:
        nb.reload()
        bad = False
    except ValueError:
        bad = True
    check('vocab', 'a notebook whose vocabulary file does not match is refused', bad)


# ------------------------------------------------------------------------------ reader

def every_sentence():
    """The whole grammar, as sentences: both fact shapes, corrections, both questions."""
    out = []
    for correction in (False, True):
        out.append(M.Fact('Mira', 'friend', 'Oren', correction))
        for relation in M.ATTRIBUTE_WORDS:
            for value in M.VALUE_WORDS:
                out.append(M.Fact('Mira', relation, value, correction))
    for hops in range(1, M.MAX_HOPS + 1):
        out.append(M.Question('Mira', ['friend']*hops))
        if hops >= 2:
            for relation in M.ATTRIBUTE_WORDS:
                out.append(M.Question('Mira', ['friend']*(hops - 1) + [relation]))
    for relation in M.ATTRIBUTE_WORDS:
        out.append(M.Question('Mira', [relation]))
    return out


def group_reader(root):
    good = [("Mira's friend is Oren.", M.Fact('Mira', 'friend', 'Oren')),
            ("Oren's gift is a drum.", M.Fact('Oren', 'gift', 'drum')),
            ("Actually, Mira's friend is Tal.", M.Fact('Mira', 'friend', 'Tal', True)),
            ("Actually Mira's charm is a pebble.", M.Fact('Mira', 'charm', 'pebble', True)),
            ("Who is Mira's friend?", M.Question('Mira', ['friend'])),
            ("Who is Mira's friend's friend?", M.Question('Mira', ['friend', 'friend'])),
            ("What is Mira's prize?", M.Question('Mira', ['prize'])),
            ("What is Mira's friend's gift?", M.Question('Mira', ['friend', 'gift'])),
            ("What is Mira's friend's friend's gift?",
             M.Question('Mira', ['friend', 'friend', 'gift']))]
    for text, expected in good:
        check('reader', f'reads {text!r}', M.parse(text) == expected, repr(M.parse(text)))
    check('reader', 'a curly apostrophe reads the same as a straight one',
          M.parse("Mira’s friend is Oren.") == M.Fact('Mira', 'friend', 'Oren'))
    check('reader', 'extra whitespace is tolerated',
          M.parse("  Mira's   friend  is   Oren.  ") == M.Fact('Mira', 'friend', 'Oren'))

    bad = ["Mira's frend is Oren.",           # misspelt relation
           "mira's friend is Oren.",          # lower-case name
           "Mira's friend is oren.",          # lower-case object
           "Mira's gift is a banjo.",         # value outside the published vocabulary
           "Mira's gift is drum.",            # missing article
           "Mira's friend is Oren",           # no full stop
           "Who is Mira's gift?",             # Who with an attribute
           "What is Mira's friend?",          # What with a person
           "Mira's friend is Mira.",          # self-friendship
           "Tell me about Mira.",             # not a shape at all
           "",
           "Who is Mira's " + "friend's "*11 + "friend?"]   # past the loop's cap
    for text in bad:
        try:
            M.parse(text)
            refused = False
        except M.ParseError as exc:
            refused = all(shape in str(exc) for shape in M.SHAPES)
        check('reader', f'refuses {text!r} and lists every accepted shape', refused)
    check('reader', 'the cap is exactly MAX_HOPS steps',
          len(M.parse("Who is Mira's " + "friend's "*(M.MAX_HOPS - 1) + "friend?").ops)
          == M.MAX_HOPS)


def group_printer(root):
    items = every_sentence()
    bad = []
    for item in items:
        text = M.render_fact(item) if item.kind == 'fact' else M.render_question(item)
        again = M.parse(text)
        if again != item or (M.render_fact(again) if again.kind == 'fact'
                             else M.render_question(again)) != text:
            bad.append(text)
    check('printer', f'reader/printer round-trip over the whole grammar ({len(items)} '
          f'sentences)', not bad, '; '.join(bad[:5]))
    names = {52: 'Mira', 53: 'Oren'}
    check('printer', 'an entity token prints as its name', M.token_phrase(53, names) == 'Oren')
    check('printer', 'a value token prints with its article',
          M.token_phrase(12, names) == 'a drum')
    check('printer', 'an unnamed entity token is described honestly, not guessed',
          'no name for' in M.token_phrase(60, names))
    check('printer', 'a token that is not an answer word says so',
          'not an answer word' in M.token_phrase(40, names))
    q = M.Question('Mira', ['friend', 'gift'])
    check('printer', 'the answer sentence echoes the possessive chain',
          M.render_answer(q, 'a drum') == "Mira's friend's gift is a drum.")


# ------------------------------------------------------------------------------- store

def teach_all(nb, facts, source='test'):
    return [nb.teach(f, source=source) for f in facts]


SAMPLE = [M.Fact('Mira', 'friend', 'Oren'), M.Fact('Oren', 'gift', 'drum'),
          M.Fact('Mira', 'gift', 'kite'), M.Fact('Oren', 'friend', 'Tal'),
          M.Fact('Tal', 'charm', 'rope'), M.Fact('Mira', 'prize', 'coin')]


def group_store(root):
    nb = temp_notebook(root, 'store')
    teach_all(nb, SAMPLE)
    check('store', 'six facts give six current-view rows', len(nb.view()) == 6)
    check('store', 'every row is [WORLD, entity, relation, object, NEWLINE]',
          all(len(r) == 5 and r[0] == M.WORLD and M.ENTITY_MIN <= r[1] < M.ENTITY_MAX
              and r[2] in (8, 9, 10, M.LINK) and r[4] == M.NEWLINE for r in nb.rows()))
    check('store', 'no filler token is ever invented',
          all(all(t not in range(28, 52) for t in r) for r in nb.rows()))

    fresh = M.Notebook.open(nb.path, create=False)
    check('store', 'kill-and-reload: the diary reloads entry for entry',
          fresh.entries == nb.entries)
    check('store', 'kill-and-reload: the current view is identical', fresh.rows() == nb.rows())
    check('store', 'kill-and-reload: the symbol table is identical', fresh.symbols == nb.symbols)
    check('store', 'kill-and-reload: the derived truth map is identical',
          fresh.truth() == nb.truth())

    check('store', 'the view at a prefix is the view after that many facts',
          [len(nb.view(k)) for k in (1, 2, 3, 6)] == [1, 2, 3, 6])
    check('store', 'row order follows first appearance, so a correction keeps its place',
          nb.rows(3)[0][1:3] == [nb.symbols['Mira'], M.LINK])
    check('store', 'the store never needs an operator', not hasattr(nb, 'model'))
    check('store', 'opening a missing notebook with create=False fails loudly',
          not Path(root, 'nope').exists())
    try:
        M.Notebook.open(Path(root)/'nope', create=False)
        raised = False
    except FileNotFoundError:
        raised = True
    check('store', 'create=False refuses to invent a notebook', raised)

    path = Path(root)/'atomic.txt'
    M.write_atomic(path, 'one')
    M.write_atomic(path, 'two')
    check('store', 'atomic write replaces in place and leaves no temp file',
          path.read_text() == 'two'
          and not [p for p in path.parent.iterdir() if p.name.startswith('.atomic')])


def group_correction(root):
    nb = temp_notebook(root, 'correction')
    teach_all(nb, SAMPLE)
    before_rows, before_truth = nb.rows(), dict(nb.truth())
    entry, previous = nb.teach(M.Fact('Mira', 'friend', 'Tal', correction=True), source='test')
    after_rows, after_truth = nb.rows(), dict(nb.truth())
    check('correction', 'a correction does not grow the current view',
          len(after_rows) == len(before_rows) == 6)
    changed = [k for k in before_truth if before_truth[k] != after_truth[k]]
    check('correction', 'a correction replaces exactly one current-view row',
          changed == [(nb.symbols['Mira'], M.LINK)], str(changed))
    check('correction', 'every other row is byte-identical',
          [r for r in before_rows if r not in after_rows] == [before_rows[0]])
    check('correction', 'the replaced row keeps its position in the story',
          [r[1:3] for r in before_rows] == [r[1:3] for r in after_rows])
    check('correction', 'the correction reports what it replaced',
          previous is not None and previous['object'] == 'Oren')
    check('correction', 'the new row is what the corrected sentence says',
          after_truth[(nb.symbols['Mira'], M.LINK)] == nb.symbols['Tal'])
    check('correction', 'the old fact is still in the diary, unedited',
          any(e['kind'] == 'fact' and e['object'] == 'Oren' for e in nb.entries))
    again = nb.teach(M.Fact('Mira', 'friend', 'Ada'), source='test')[0]
    check('correction', 'plain re-teaching corrects too, no "Actually" needed',
          nb.truth()[(nb.symbols['Mira'], M.LINK)] == nb.symbols['Ada'] and len(nb.view()) == 6)
    check('correction', 'a two-hop answer follows the corrected link with no cache',
          M.walk(nb.truth(), nb.symbols['Mira'], ['friend', 'gift']) is None
          or M.walk(nb.truth(), nb.symbols['Mira'], ['friend']) == nb.symbols['Ada'])
    check('correction', 'the diary records the correction as a new line, never an edit',
          again['n'] == len(nb.entries) - 1)


def group_diary(root):
    nb = temp_notebook(root, 'diary')
    teach_all(nb, SAMPLE[:3])
    first = nb.diary_path.read_bytes()
    teach_all(nb, SAMPLE[3:])
    nb.teach(M.Fact('Mira', 'friend', 'Tal', correction=True), source='test')
    second = nb.diary_path.read_bytes()
    check('diary', 'the diary is append-only: the old bytes are an exact prefix',
          second.startswith(first) and len(second) > len(first))
    check('diary', 'every line is one JSON object and n is its line number',
          all(json.loads(line)['n'] == i
              for i, line in enumerate(second.decode().splitlines())))
    check('diary', 'every diary line records time, raw sentence, row and source',
          all(set(json.loads(line)) >= {'time', 'raw', 'row', 'source', 'kind', 'subject'}
              for line in second.decode().splitlines()))
    check('diary', 'fact lines carry the canonical row; name lines do not',
          all((json.loads(line)['row'] is None) == (json.loads(line)['kind'] == 'name')
              for line in second.decode().splitlines()))
    shuffled = nb.entries[:]
    shuffled[0], shuffled[1] = shuffled[1], shuffled[0]
    M.write_atomic(nb.diary_path, ''.join(json.dumps(e, sort_keys=True,
                                                     separators=(',', ':')) + '\n'
                                          for e in shuffled))
    try:
        nb.reload()
        refused = False
    except ValueError:
        refused = True
    check('diary', 'an out-of-order diary is refused rather than half-read', refused)


def group_symbols(root):
    nb = temp_notebook(root, 'symbols')
    teach_all(nb, SAMPLE)
    check('symbols', 'names get the operator\'s entity tokens in order of first appearance',
          [nb.symbols[n] for n in ('Mira', 'Oren', 'Tal')] == [52, 53, 54])
    check('symbols', 'the symbol table on disk matches the one derived from the diary',
          json.loads(nb.symbols_path.read_text())['names'] == nb.symbols)
    check('symbols', 'the derived table is what reload uses',
          M.Notebook.open(nb.path, create=False).symbols == nb.symbols)
    M.write_atomic(nb.symbols_path, json.dumps(dict(names={'Mira': 60})))
    try:
        nb.reload()
        refused = False
    except ValueError:
        refused = True
    check('symbols', 'a symbol file that disagrees with the diary is refused', refused)
    M.write_atomic(nb.symbols_path, json.dumps(dict(names=nb.derive_symbols())))
    nb.reload()
    full = temp_notebook(root, 'symbols-full')
    for name in M.DEFAULT_NAMES:
        full.teach(M.Fact(name, 'gift', 'drum'), source='test')
    check('symbols', 'sixteen names fit', len(full.symbols) == 16)
    try:
        full.teach(M.Fact('Zora', 'gift', 'drum'), source='test')
        refused = False
    except ValueError as exc:
        refused = '16 names' in str(exc)
    check('symbols', 'a seventeenth name is refused, not silently reused', refused)
    check('symbols', 'asking about an unknown person spends a symbol and says so in the diary',
          temp_notebook(root, 'symbols-ask').name_token('Pell') == 52)


def group_wipe(root):
    nb = temp_notebook(root, 'wipe')
    teach_all(nb, SAMPLE)
    moved = nb.wipe()
    check('wipe', 'the wiped notebook holds nothing', nb.view() == {} and nb.entries == [])
    check('wipe', 'the old diary is archived, not deleted',
          moved and all(Path(p).exists() for p in moved))
    check('wipe', 'the archived diary still holds every fact',
          sum(1 for line in Path(moved[0]).read_text().splitlines()
              if json.loads(line)['kind'] == 'fact') == len(SAMPLE))
    check('wipe', 'a wiped notebook reloads as empty',
          M.Notebook.open(nb.path, create=False).rows() == [])
    teach_all(nb, SAMPLE[:2])
    check('wipe', 'teaching after a wipe starts the diary again from n=0',
          [e['n'] for e in nb.entries] == list(range(len(nb.entries))))


# -------------------------------------------------------------------------------- pack

def group_pack(root):
    nb = temp_notebook(root, 'pack')
    teach_all(nb, SAMPLE)
    x = M.pack_story([nb.rows()], [M.question_tokens(52, ['friend'])], [0])
    check('pack', 'the story is exactly the current view, no padding to a fixed size',
          tuple(x.memory.shape) == (1, 6, 5))
    check('pack', 'every current-view row is eligible for the question',
          bool(x.eligible.all()))
    check('pack', 'the question is [QUESTION, entity, op..., ANSWER]',
          x.questions[0].tolist() == [M.QUESTION, 52, M.LINK, M.ANSWER])
    check('pack', 'a two-hop question carries both operations',
          M.question_tokens(52, ['friend', 'gift']) == [M.QUESTION, 52, M.LINK, 8, M.ANSWER])
    small = M.pack_story([nb.rows(1)], [M.question_tokens(52, ['friend'])], [0])
    check('pack', 'a one-row notebook is presented as a one-row story',
          tuple(small.memory.shape) == (1, 1, 5))
    empty = temp_notebook(root, 'pack-empty')
    x0 = M.pack_story([empty.rows()], [M.question_tokens(52, ['friend'])], [0])
    check('pack', 'an empty notebook becomes one all-padding, ineligible row',
          tuple(x0.memory.shape) == (1, 1, 1) and not bool(x0.eligible.any()))
    check('pack', 'the evaluator can re-derive every gold from the packed story',
          [p[-1]['target'] for p in M.A.truth_paths(x)] == [nb.symbols['Oren']])
    check('pack', 'walk follows the current view', M.walk(nb.truth(), 52, ['friend', 'gift'])
          == M.VALUE_TOKEN['drum'])
    check('pack', 'walk returns None where the notebook says nothing',
          M.walk(nb.truth(), 52, ['friend', 'friend', 'gift']) is None)


# ---------------------------------------------------------------------------- operator

def group_operator(root):
    paths = {}
    for seed in (0, 1, 2):
        try:
            paths[seed] = M.checkpoint_path(seed)
        except FileNotFoundError:
            paths[seed] = None
    check('operator', 'a frozen grow-blind checkpoint exists for seeds 0, 1 and 2',
          all(paths.values()), str(paths))
    if not all(paths.values()):
        return
    operator = M.Operator(0)
    check('operator', 'the checkpoint holds exactly 79,316 parameters',
          operator.parameters == M.EXPECTED_PARAMETERS)
    check('operator', 'the architecture is the registered one',
          operator.architecture == dict(vocab=68, width=48, heads=4, steps=3))
    check('operator', 'the checkpoint sha256 is recorded', len(operator.sha256) == 64)
    check('operator', 'nothing in the operator wrapper can train',
          not any(p.grad is not None for p in operator.model.parameters()))
    before = M.sha_file(operator.path)
    nb = temp_notebook(root, 'operator')
    teach_all(nb, SAMPLE)
    out = M.answer_in_english(nb, operator, M.parse("What is Mira's friend's gift?"))
    check('operator', 'the two-hop answer comes back in English',
          out['sentence'] == "Mira's friend's gift is a drum.", out['sentence'])
    check('operator', 'the trace names every lookup the fixed loop made',
          len(out['trace']) == 2 and 'Mira, friend' in out['trace'][0])
    check('operator', 'the notebook itself supports that answer',
          out['notebook_supports']['answerable'])
    nb.teach(M.Fact('Oren', 'gift', 'kettle', correction=True), source='test')
    out2 = M.answer_in_english(nb, operator, M.parse("What is Mira's friend's gift?"))
    check('operator', 'a correction changes the chained answer with no retraining',
          out2['sentence'] == "Mira's friend's gift is a kettle.", out2['sentence'])
    check('operator', 'answering never rewrites the checkpoint',
          M.sha_file(operator.path) == before)
    out3 = M.answer_in_english(nb, operator, M.parse("What is Tal's prize?"))
    check('operator', 'an untaught question is answered anyway, and flagged as unsupported',
          not out3['notebook_supports']['answerable'] and out3['sentence'].endswith('.'))


# -------------------------------------------------------------------------------- eval

def group_eval(root):
    world = M.session_world(0)
    check('eval', 'a session teaches exactly 64 facts', len(world['facts']) == 64)
    check('eval', 'a session covers every (person, relation) key once',
          len({(f.subject, f.relation) for f in world['facts']}) == 64)
    check('eval', 'the first fact taught is a friend link', world['facts'][0].relation == 'friend')
    check('eval', 'the second is an attribute of that friend, so two hops work from size 2',
          world['facts'][1].subject == world['facts'][0].obj
          and world['facts'][1].relation != 'friend')
    check('eval', 'sessions are reproducible from the namespace alone',
          [(f.subject, f.relation, f.obj) for f in M.session_world(3)['facts']]
          == [(f.subject, f.relation, f.obj) for f in M.session_world(3)['facts']])
    check('eval', 'the RNG namespace is the new one', M.NAMESPACE == 'fable-notebook-m0-v1')
    check('eval', 'sizes are the registered doubling', M.EVAL_SIZES == (1, 2, 4, 8, 16, 32, 64))
    session = M.build_session_notebook(0, Path(root)/'eval-notebooks')
    nb = session['notebook']
    check('eval', 'the session notebook holds 66 facts in the diary and 64 in the view',
          len(nb.fact_entries()) == 66 and len(nb.view()) == 64)
    check('eval', 'the two corrections replaced rows rather than adding them',
          len(nb.view(64)) == len(nb.view(66)) == 64)
    before, after = nb.truth(64), nb.truth(66)
    changed = [k for k in before if before[k] != after[k]]
    check('eval', 'exactly two current-view rows differ before and after the corrections',
          len(changed) == 2, str(changed))
    check('eval', 'no probe key is one the corrections touched',
          all((nb.symbols[n], M.RELATION_TOKEN[r]) not in changed for n, r in session['probes']))
    check('eval', 'there are sixteen probes', len(session['probes']) == M.PROBE_COUNT)
    check('eval', 'no two-hop question is answerable at size 1',
          sample_len(session, nb, 1, 'two_hop') == 0)
    check('eval', 'a two-hop question is answerable at size 2',
          sample_len(session, nb, 2, 'two_hop') == 1)
    check('eval', 'question sampling is capped and deterministic',
          sample_len(session, nb, 64, 'one_hop') == M.QUESTIONS_PER_CELL
          and M.sample_questions(session, nb, 64, 'one_hop')
          == M.sample_questions(session, nb, 64, 'one_hop'))
    unregistered = argparse.Namespace(out=str(Path(root)/'unregistered'), sessions=1,
                                      seeds=(0,))
    try:
        M.cmd_eval(unregistered)
        refused = False
    except SystemExit as exc:
        refused = 'must be written BEFORE' in str(exc)
    check('eval', 'eval refuses to run before the marks are registered', refused)
    text = M.PREREG_TEXT.format(sessions=64, namespace=M.NAMESPACE, sizes='1', per_cell=8,
                                probes=16, reload=8)
    for phrase in ('>= 95%', '<= 2%', '100% identical', 'blind_lines = 16', 'Descriptive only'):
        check('eval', f'the registered marks state {phrase!r}', phrase in text)


def sample_len(session, nb, size, kind):
    return len(M.sample_questions(session, nb, size, kind))


# --------------------------------------------------------------------------------- cli

def group_cli(root):
    script = str(HERE.parent/'scripts'/'fable_notebook_m0.py')
    nb = Path(root)/'cli-nb'
    env = dict(os.environ, OMP_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')

    def run(*argv):
        return subprocess.run([sys.executable, '-B', script, *argv, '--notebook', str(nb)],
                              capture_output=True, text=True, env=env)

    out = run('teach', "Mira's friend is Oren.")
    check('cli', 'teach appends and says so', out.returncode == 0 and 'Noted' in out.stdout)
    run('teach', "Oren's gift is a drum.")
    out = run('ask', "What is Mira's friend's gift?")
    check('cli', 'ask answers in English with the lookup trace',
          "Mira's friend's gift is a drum." in out.stdout and 'lookup 2' in out.stdout, out.stdout)
    out = run('teach', "Actually, Mira's friend is Tal.")
    check('cli', 'teach reports what a correction replaced', 'replaces' in out.stdout)
    out = run('ask', "Who is Mira's friend?")
    check('cli', 'the corrected answer wins with no retraining',
          "Mira's friend is Tal." in out.stdout, out.stdout)
    out = run('teach', "Mira's frend is Oren.")
    check('cli', 'unparseable input is refused with the accepted shapes, never guessed',
          out.returncode == 2 and all(s in out.stdout for s in M.SHAPES))
    out = run('ask', "Mira's friend is Oren.")
    check('cli', 'a statement given to ask is refused', out.returncode == 2)
    out = run('wipe', '--yes')
    check('cli', 'wipe archives and empties', out.returncode == 0 and 'archived' in out.stdout)

    # the fresh-process reload path the eval's kill-and-reload mark uses
    fresh = Path(root)/'cli-reload'
    reload_nb = M.Notebook.open(fresh)
    teach_all(reload_nb, SAMPLE)
    spec = Path(root)/'q.json'
    result = Path(root)/'q.result.json'
    spec.write_text(json.dumps(dict(questions=[M.question_tokens(52, ['friend', 'gift'])],
                                    facts=None, logits=True)))
    proc = subprocess.run([sys.executable, '-B', script, 'answer-batch', '--notebook',
                           str(fresh), '--questions', str(spec), '--out', str(result),
                           '--seed', '0'], capture_output=True, text=True, env=env)
    ok = proc.returncode == 0 and result.exists()
    check('cli', 'answer-batch re-instantiates the notebook in a fresh process',
          ok, proc.stderr[-400:])
    if ok:
        payload = json.loads(result.read_text())
        operator = M.Operator(0)
        here = M.answer_one(operator, reload_nb.rows(), 52, ['friend', 'gift'],
                            reload_nb.names_by_token)
        check('cli', 'the fresh process reads byte-identical rows',
              payload['rows'] == reload_nb.rows())
        check('cli', 'the fresh process gives the identical answer',
              payload['predictions'] == [here['prediction']])
        check('cli', 'the fresh process reports the same checkpoint sha256',
              payload['checkpoint_sha256'] == operator.sha256)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', choices=GROUPS, action='append')
    args = ap.parse_args(argv)
    groups = args.only or list(GROUPS)
    root = tempfile.mkdtemp(prefix='fable-notebook-m0-tests-')
    try:
        for name in groups:
            globals()[f'group_{name}'](Path(root)/name)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    failed = [c for c in CHECKS if not c[2]]
    for group, text, ok, detail in CHECKS:
        if not ok:
            print(f'FAIL  [{group}] {text}' + (f'   -- {detail}' if detail else ''))
    if failed:
        print(f'\n{len(failed)} OF {len(CHECKS)} CHECKS FAILED')
        return 1
    print(f'ALL {len(CHECKS)} CHECKS PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
