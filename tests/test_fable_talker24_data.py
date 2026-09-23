"""Tests for `scripts/fable_talker24_data.py` (talker build task 1, design 24).

Plain script, no pytest, in this repository's house style: `check(name, function)`, a
`_Skip` for anything that needs a fixture that is not on this machine, and a PASSED /
FAILED / SKIPPED tally with a non-zero exit on any failure.

  <venv>/bin/python -B tests/test_fable_talker24_data.py [--out SHARDS_DIR]

`--out` (default `artifacts/fable-talker24-20260920/shards`) points at a produced shard
tree. Everything that needs a real tokenizer or a real shard skips cleanly when it is
absent; the pure-logic tests run from nothing.

What is actually proved here:

  sentence splitting        paragraph breaks, abbreviations, initials, quotes, ellipsis
  name detection            the three-part rule of design 2.1, possessives kept separate,
                            "I" never a name, sentence-initial common words never a name
  codes are per-document    distinct, inside the training pool (never the reserved half),
                            identical for the same (seed, doc_uid) and different across
                            documents -- the M1 trick of design 4.3
  the SODA filter           a simple dialogue passes, a hard-word one does not, and an
                            unusual NAME never disqualifies an otherwise simple dialogue
  reader coverage           chunking a text corpus into units loses no document and
                            duplicates none, with the separator mid-line or on its own
  shard invariants          every rule INTERFACE-data.md states, on a synthetic shard
                            and again on every produced shard
  the numpy-only decoder    a hand-built byte-level vocab round-trips, and on a produced
                            shard the shipped decoder reproduces the `tokenizers` output
  determinism               the same seed gives byte-identical parts
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))

import fable_talker24_data as D                                           # noqa: E402

DEFAULT_OUT = HERE.parent / 'artifacts/fable-talker24-20260920/shards'
OUT = DEFAULT_OUT

PASSED = FAILED = SKIPPED = 0


class _Skip(Exception):
    pass


def check(name, function):
    global PASSED, FAILED, SKIPPED
    try:
        function()
    except _Skip as exc:
        SKIPPED += 1
        print(f'SKIPPED {name}: {exc}', flush=True)
    except Exception:                                                     # noqa: BLE001
        FAILED += 1
        print(f'FAILED  {name}', flush=True)
        traceback.print_exc()
    else:
        PASSED += 1
        print(f'PASSED  {name}', flush=True)


def toy_lexicon():
    words = {'the', 'a', 'once', 'upon', 'time', 'there', 'was', 'girl', 'friend', 'is',
             'and', 'she', 'said', 'hello', 'to', 'her', 'dog', 'ran', 'fast', 'then',
             'it', 'who', 'cat', 'sat', 'on', 'mat', 'big', 'red', 'ball', 'happy',
             'went', 'park', 'with', 'his', 'mum', 'day', 'sun', 'shone', 'bright'}
    names = {'mira', 'oren', 'tal', 'lily', 'ben'}
    simple = set(words)
    return D.Lexicon(words=words, names=names, simple=simple)


def produced_tokenizer():
    p = OUT / 'tokenizer.json'
    if not p.exists():
        raise _Skip(f'no produced tokenizer at {p}')
    from tokenizers import Tokenizer
    return Tokenizer.from_file(str(p))


def produced_manifest():
    p = OUT / 'manifest.json'
    if not p.exists():
        raise _Skip(f'no produced manifest at {p}')
    return D.read_json(p)


def shipped_decoder():
    v = OUT / 'tokenizer_vocab.json'
    d = OUT / 'decode_numpy.py'
    if not (v.exists() and d.exists()):
        raise _Skip('no produced tokenizer export')
    sys.path.insert(0, str(OUT))
    import importlib
    mod = importlib.import_module('decode_numpy')
    importlib.reload(mod)
    return mod.Decoder(str(v))


# --------------------------------------------------------------------- sentence splitting

def test_sentences_split_on_punctuation_and_paragraphs():
    t = 'Once upon a time there was a girl. She ran fast! Did she win?\nYes she did.'
    assert D.split_sentences(t) == [
        'Once upon a time there was a girl.', 'She ran fast!', 'Did she win?',
        'Yes she did.'], D.split_sentences(t)


def test_sentences_do_not_split_inside_abbreviations_or_initials():
    got = D.split_sentences('Mr. Smith went home. J. R. Brown did not.')
    assert got == ['Mr. Smith went home.', 'J. R. Brown did not.'], got


def test_sentences_keep_quotes_and_ellipsis_attached():
    got = D.split_sentences('"Hello," she said. "Goodbye." Then... she left.')
    assert got[0] == '"Hello," she said.', got
    assert got[1] == '"Goodbye."', got
    assert got[-1].endswith('she left.'), got


def test_sentences_ignore_blank_lines():
    assert D.split_sentences('\n\n  \nHi.\n\n\nBye.\n') == ['Hi.', 'Bye.']


# ------------------------------------------------------------------------ name detection

def test_known_name_is_a_name_anywhere_in_the_sentence():
    lex = toy_lexicon()
    assert D.is_name('Mira', lex)
    segs = D.segment_sentence('Then Mira ran fast.', lex)
    assert ('ent', 'Mira') in segs, segs


def test_sentence_initial_common_word_is_not_a_name():
    lex = toy_lexicon()
    assert not D.is_name('Then', lex)
    assert not D.is_name('The', lex)
    segs = D.segment_sentence('Then she said hello.', lex)
    assert all(k == 'text' for k, _ in segs), segs


def test_unknown_capitalised_word_is_treated_as_a_name():
    lex = toy_lexicon()
    assert D.is_name('Zephyrine', lex)


def test_I_is_never_a_name():
    lex = toy_lexicon()
    assert not D.is_name('I', lex)
    assert all(k == 'text' for k, _ in D.segment_sentence('I went to the park.', lex))


def test_possessive_stays_outside_the_placeholder():
    lex = toy_lexicon()
    segs = D.segment_sentence("Mira's friend is Oren.", lex)
    assert segs[0] == ('ent', 'Mira'), segs
    assert segs[1][0] == 'text' and segs[1][1].startswith("'s"), segs
    assert segs[2] == ('ent', 'Oren'), segs


def test_segments_reassemble_into_the_original_sentence():
    lex = toy_lexicon()
    s = "Mira's friend is Oren and Tal said hello to her dog."
    segs = D.segment_sentence(s, lex)
    assert ''.join(p for _k, p in segs) == s


# ------------------------------------------------------------------------- entity codes

def test_codes_are_distinct_and_inside_the_training_pool():
    codes = D.assign_codes(['Mira', 'Oren', 'Tal', 'mira'], seed=24, doc_uid='u#1')
    assert len(codes) == 3, codes
    assert len(set(codes.values())) == 3, codes
    for c in codes.values():
        assert 0 <= c <= D.ENT_CODE_TRAIN_MAX, c
        assert c != D.ENT_NONE


def test_codes_never_reach_the_reserved_half():
    """Exhaustive over many documents: no drawn code is ever >= 3072."""
    worst = -1
    for i in range(4000):
        for c in D.assign_codes([f'N{j}' for j in range(8)], 24, f'doc#{i}').values():
            worst = max(worst, c)
    assert worst <= D.ENT_CODE_TRAIN_MAX, worst
    assert D.ENT_CODE_TRAIN_MAX + 1 == 3072
    assert D.ENT_CODE_POOL == 4096


def test_codes_are_a_pure_function_of_seed_and_document():
    a = D.assign_codes(['Mira', 'Oren'], 24, 'doc#1')
    b = D.assign_codes(['Mira', 'Oren'], 24, 'doc#1')
    c = D.assign_codes(['Mira', 'Oren'], 24, 'doc#2')
    d = D.assign_codes(['Mira', 'Oren'], 25, 'doc#1')
    assert a == b, (a, b)
    assert a != c, (a, c)
    assert a != d, (a, d)


def test_codes_are_capped_per_document():
    names = [f'Name{i}' for i in range(D.MAX_ENTS_PER_DOC + 20)]
    codes = D.assign_codes(names, 24, 'doc#3')
    assert len(codes) == D.MAX_ENTS_PER_DOC, len(codes)


# --------------------------------------------------------------------- the SODA filter

def test_soda_filter_keeps_a_simple_dialogue():
    lex = toy_lexicon()
    turns = ['hello there', 'the dog ran fast and she said hello to her friend',
             'it was a big red ball on the mat']
    assert D.soda_is_simple(turns, lex)


def test_soda_filter_drops_a_hard_worded_dialogue():
    lex = toy_lexicon()
    turns = ['the quantum decoherence precipitated an epistemological crisis',
             'indeed the phenomenological hermeneutics were unsatisfactory']
    assert not D.soda_is_simple(turns, lex)


def test_soda_filter_does_not_punish_an_unusual_name():
    lex = toy_lexicon()
    plain = ['the dog ran fast and she said hello to her friend on the big red mat']
    named = ['Zephyrine the dog ran fast and Quillonax said hello to her friend '
             'on the big red mat']
    assert D.soda_is_simple(plain, lex)
    assert D.soda_is_simple(named, lex), 'names must be excluded from the simplicity test'


def test_soda_filter_drops_a_too_short_dialogue():
    assert not D.soda_is_simple(['hi', 'ok'], toy_lexicon())


# ------------------------------------------------------ readers: no loss, no duplication

def _write_eot_corpus(path: Path, n: int, one_line: bool) -> list[str]:
    docs = [f'doc number {i} said hello. it ran fast and then it sat down. bye {i}.'
            for i in range(n)]
    with open(path, 'w', encoding='utf-8') as fh:
        for d in docs:
            if one_line:
                fh.write(d + ' ' + D._EOT + '\n')
            else:
                fh.write(d + '\n' + D._EOT + '\n')
    return docs


def _collect(path: Path, kind: str, n_units: int) -> list[str]:
    size = path.stat().st_size
    step = (size + n_units - 1) // n_units
    got = []
    for i in range(n_units):
        u = D.Unit(uid=f'u{i}', source='tinystories_v2', split='train', kind=kind,
                   path=str(path), start=i * step, end=min((i + 1) * step, size))
        for _uid, turns, _n in D.iter_documents(u):
            got.append(' '.join(turns))
    return got


def test_text_reader_chunking_loses_and_duplicates_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'c.txt'
        for one_line in (False, True):
            want = _write_eot_corpus(p, 120, one_line)
            for n_units in (1, 2, 3, 7):
                got = _collect(p, 'text_eot', n_units)
                assert got == want, (one_line, n_units, len(got), len(want))


def test_tinydialogues_turns_are_split_and_speaker_tags_removed():
    body = ('**Babysitter**: Hey there. \\n\\n **Child**: Yes! Outside! \\n\\n '
            '**Child** (struggling to pull the wagon): Heavy!')
    turns = D._split_td_turns(body)
    assert turns == ['Hey there.', 'Yes! Outside!', 'Heavy!'], turns


def test_tinydialogues_reader_yields_turns():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'td.txt'
        p.write_text('**Mom**: hi there. \\n\\n **Child**: hi! ' + D._EOT + '\n'
                     '**Dad**: bye now. \\n\\n **Child**: bye! ' + D._EOT + '\n',
                     encoding='utf-8')
        u = D.Unit(uid='td', source='tinydialogues', split='train', kind='text_td',
                   path=str(p))
        docs = [turns for _uid, turns, _n in D.iter_documents(u)]
        assert docs == [['hi there.', 'hi!'], ['bye now.', 'bye!']], docs


def test_max_bytes_caps_a_unit():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'c.txt'
        _write_eot_corpus(p, 200, False)
        u = D.Unit(uid='u', source='tinystories_v2', split='train', kind='text_eot',
                   path=str(p), max_bytes=500)
        total = sum(n for _uid, _t, n in D.iter_documents(u))
        assert 500 <= total < 500 + 200, total


# ------------------------------------------------------------------- shard invariants

def _interface_invariants(stem: str, meta: dict):
    tok = np.fromfile(f'{stem}.tokens.u16', dtype='<u2')
    ent = np.fromfile(f'{stem}.ents.u16', dtype='<u2')
    sen = np.fromfile(f'{stem}.sents.u32', dtype='<u4')
    doc = np.fromfile(f'{stem}.docs.u32', dtype='<u4')

    assert tok.size == ent.size, (tok.size, ent.size)
    assert tok.size == meta['n_tokens'], (tok.size, meta['n_tokens'])
    assert sen.size == meta['n_sentences'] + 1
    assert doc.size == meta['n_documents'] + 1
    assert sen[0] == 0 and doc[0] == 0
    assert int(sen[-1]) == tok.size, (int(sen[-1]), tok.size)
    assert int(doc[-1]) == sen.size - 1
    assert np.all(np.diff(sen.astype(np.int64)) > 0), 'empty sentence'
    assert np.all(np.diff(doc.astype(np.int64)) > 0), 'empty document'

    lens = np.diff(sen.astype(np.int64))
    assert lens.max() <= D.MAX_SENTENCE_TOKENS, int(lens.max())

    is_ent = tok == D.ID_ENT
    has_code = ent != D.ENT_NONE
    assert np.array_equal(is_ent, has_code), 'ents/<ENT> misaligned'
    if has_code.any():
        assert int(ent[has_code].max()) <= D.ENT_CODE_TRAIN_MAX, int(ent[has_code].max())

    # only <ENT>, <TURN> and real BPE pieces may appear
    bad = np.unique(tok[(tok < D.N_SPECIAL) & (tok != D.ID_ENT) & (tok != D.ID_TURN)])
    assert bad.size == 0, f'forbidden special ids in a shard: {bad.tolist()}'
    assert int(tok.max(initial=0)) < D.VOCAB_SIZE


def test_synthetic_shard_obeys_the_interface():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        w = D.ShardWriter(out, 'train', cap=40, seed=24, tok_sha='x', producer_sha='y')
        rng = np.random.default_rng(0)
        for d in range(12):
            n = int(rng.integers(3, 9))
            tok = rng.integers(D.N_SPECIAL, D.VOCAB_SIZE, size=n).astype('<u2')
            ent = np.full(n, D.ENT_NONE, dtype='<u2')
            tok[0] = D.ID_ENT
            ent[0] = d
            ends = np.asarray([n], dtype='<u4') if n < 6 else np.asarray([3, n], dtype='<u4')
            w.add_doc('simplestories', tok, ent, ends)
        w.flush()
        assert len(w.shards) >= 2, 'the cap must have forced more than one shard'
        for s in w.shards:
            _interface_invariants(s['stem'], s)
            assert D.sha256_file(f"{s['stem']}.tokens.u16") == s['sha256']['tokens']


def test_produced_shards_obey_the_interface():
    manifest = produced_manifest()
    n = 0
    for _split, shards in manifest['splits'].items():
        for s in shards:
            _interface_invariants(s['stem'], s)
            for key, ext in (('tokens', 'tokens.u16'), ('ents', 'ents.u16'),
                             ('sents', 'sents.u32'), ('docs', 'docs.u32')):
                assert D.sha256_file(f"{s['stem']}.{ext}") == s['sha256'][key], \
                    f"{s['stem']} {key} hash mismatch"
            n += 1
    assert n > 0, 'manifest has no shards'


def test_produced_shards_contain_all_four_sources():
    manifest = produced_manifest()
    seen = {k: 0 for k in D.SOURCES}
    for s in manifest['splits'].get('train', []):
        for k, v in s['source_counts'].items():
            if k in seen:
                seen[k] += v
    missing = [k for k, v in seen.items() if v == 0]
    assert not missing, f'no tokens from {missing}'


# ---------------------------------------------------------------- the numpy-only decoder

def _toy_vocab_decoder(tmp: Path):
    b2u = D.bytes_to_unicode()
    vocab = dict(D.SPECIALS)
    nxt = D.N_SPECIAL
    for b in range(256):
        vocab[b2u[b]] = nxt
        nxt += 1
    vocab['Ġthe'] = nxt
    (tmp / 'v.json').write_text(json.dumps(vocab), encoding='utf-8')
    (tmp / 'decode_numpy.py').write_text(D.DECODE_NUMPY_SRC, encoding='utf-8')
    sys.path.insert(0, str(tmp))
    import importlib
    mod = importlib.import_module('decode_numpy')
    importlib.reload(mod)
    return mod, mod.Decoder(str(tmp / 'v.json')), vocab


def test_shipped_decoder_round_trips_bytes():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _mod, dec, vocab = _toy_vocab_decoder(tmp)
        b2u = D.bytes_to_unicode()
        ids = [vocab[b2u[b]] for b in 'hi there'.encode('utf-8')]
        assert dec.decode(ids) == 'hi there', dec.decode(ids)
        ids = [vocab['Ġthe']] + [vocab[b2u[b]] for b in ' dog'.encode('utf-8')]
        assert dec.decode(ids) == ' the dog', repr(dec.decode(ids))
        sys.path.remove(str(tmp))


def test_shipped_decoder_handles_specials_and_names():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _mod, dec, vocab = _toy_vocab_decoder(tmp)
        b2u = D.bytes_to_unicode()
        hi = [vocab[b2u[b]] for b in 'hi'.encode('utf-8')]
        ids = [D.SPECIALS['<bos>'], D.ID_ENT] + hi + [D.ID_TURN] + hi + \
              [D.SPECIALS['<eos>'], D.SPECIALS['<pad>']]
        ents = np.full(len(ids), D.ENT_NONE, dtype='<u2')
        ents[1] = 7
        assert dec.decode(ids, ents=ents) == '<ent:7>hi\nhi', repr(dec.decode(ids, ents=ents))
        assert dec.decode(ids, ents=ents, names={7: 'Mira'}) == 'Mirahi\nhi'
        # an unresolved copy action must stay visible, never silently vanish
        assert dec.decode([D.SPECIALS['<SUBJ>']]) == '<SUBJ>'
        assert dec.decode([D.SPECIALS['<SUBJ>']], copy={5: 'Mira'}) == 'Mira'
        sys.path.remove(str(tmp))


def test_shipped_decoder_matches_the_real_tokenizer():
    tok = produced_tokenizer()
    dec = shipped_decoder()
    texts = ["once upon a time there was a little dog.",
             "'s friend is happy, and she said: hello!",
             "the quick brown fox -- 42 apples? yes."]
    for t in texts:
        ids = tok.encode(t, add_special_tokens=False).ids
        assert dec.decode(ids) == t, (t, dec.decode(ids))


def test_shipped_decoder_reads_a_produced_shard():
    manifest = produced_manifest()
    dec = shipped_decoder()
    s = manifest['splits']['train'][0]
    tok = np.fromfile(f"{s['stem']}.tokens.u16", dtype='<u2')
    ent = np.fromfile(f"{s['stem']}.ents.u16", dtype='<u2')
    sen = np.fromfile(f"{s['stem']}.sents.u32", dtype='<u4')
    for i in range(min(200, sen.size - 1)):
        a, b = int(sen[i]), int(sen[i + 1])
        text = dec.decode(tok[a:b], ents=ent[a:b])
        assert isinstance(text, str) and text != ''
        assert '<ENT>' not in text, 'every placeholder must carry a code'


# ------------------------------------------------------------------------- determinism

def test_encoding_the_same_unit_twice_is_byte_identical():
    if not (OUT / 'tokenizer.json').exists():
        raise _Skip('no produced tokenizer')
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for f in ('tokenizer.json', 'lexicon.json'):
            shutil.copy(OUT / f, tmp / f)
        p = tmp / 'c.txt'
        _write_eot_corpus(p, 300, False)
        u = D.Unit(uid='det', source='tinystories_v2', split='train', kind='text_eot',
                   path=str(p))
        hashes = []
        for _ in range(2):
            m = D.encode_unit((D.asdict(u), str(tmp), 24))
            hashes.append([D.sha256_file(f"{m['stem']}.{e}") for e in
                           ('tokens.u16', 'ents.u16', 'sents.u32', 'docs.u32')])
            (tmp / 'parts' / 'det.json').unlink()
        assert hashes[0] == hashes[1], hashes
        assert m['n_tokens'] > 0


def test_a_finished_part_is_reused_instead_of_recomputed():
    if not (OUT / 'tokenizer.json').exists():
        raise _Skip('no produced tokenizer')
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for f in ('tokenizer.json', 'lexicon.json'):
            shutil.copy(OUT / f, tmp / f)
        p = tmp / 'c.txt'
        _write_eot_corpus(p, 50, False)
        u = D.Unit(uid='res', source='tinystories_v2', split='train', kind='text_eot',
                   path=str(p))
        first = D.encode_unit((D.asdict(u), str(tmp), 24))
        again = D.encode_unit((D.asdict(u), str(tmp), 24))
        assert not first.get('resumed')
        assert again.get('resumed') is True, again
        assert again['n_tokens'] == first['n_tokens']


# ------------------------------------------------------------------- frozen constants

def test_interface_constants_are_the_ones_the_document_promises():
    assert D.VOCAB_SIZE == 8192
    assert D.SPECIALS == {
        '<pad>': 0, '<bos>': 1, '<eos>': 2, '<unk>': 3, '<ENT>': 4, '<SUBJ>': 5,
        '<OBJ>': 6, '<OLD>': 7, '<TURN>': 8, '<DOC>': 9, '<extra_0>': 10,
        '<extra_1>': 11, '<extra_2>': 12, '<extra_3>': 13, '<extra_4>': 14,
        '<extra_5>': 15}
    assert D.ENT_NONE == 0xFFFF
    assert D.ENT_CODE_POOL == 4096 and D.ENT_CODE_TRAIN_MAX == 3071
    assert D.MAX_SENTENCE_TOKENS == 48
    assert D.SODA_SIMPLE_FRACTION == 0.98
    assert D.SOURCES == ('simplestories', 'tinystories_v2', 'tinydialogues', 'soda')
    assert D.TD_KEEP_AGES == (2, 5, 10)
    # the shipped decoder must agree with the producer about every special id
    assert 'SPECIALS = {' in D.DECODE_NUMPY_SRC
    ns = {}
    exec(compile(D.DECODE_NUMPY_SRC, 'decode_numpy.py', 'exec'), ns)
    assert ns['SPECIALS'] == D.SPECIALS
    assert ns['ENT_NONE'] == D.ENT_NONE


def test_produced_tokenizer_has_the_promised_special_ids():
    tok = produced_tokenizer()
    assert tok.get_vocab_size() == D.VOCAB_SIZE, tok.get_vocab_size()
    for piece, i in D.SPECIALS.items():
        assert tok.token_to_id(piece) == i, (piece, tok.token_to_id(piece))
    meta = D.read_json(OUT / 'tokenizer_meta.json')
    assert meta['specials'] == D.SPECIALS
    assert meta['sha256']['tokenizer.json'] == D.sha256_file(OUT / 'tokenizer.json')
    assert meta['sha256']['tokenizer_vocab.json'] == \
        D.sha256_file(OUT / 'tokenizer_vocab.json')


def test_plain_vocab_export_matches_the_native_tokenizer():
    tok = produced_tokenizer()
    if not (OUT / 'tokenizer_vocab.json').exists():
        raise _Skip('no plain vocab export')
    plain = D.read_json(OUT / 'tokenizer_vocab.json')
    assert plain == tok.get_vocab(), 'plain export differs from tokenizer.json'
    merges = (OUT / 'tokenizer_merges.txt').read_text(encoding='utf-8').splitlines()
    assert merges[0].startswith('#version'), merges[0]
    assert len(merges) - 1 + D.N_SPECIAL + 256 >= D.VOCAB_SIZE - 5, len(merges)


def test_raw_manifest_hashes_match_the_files_on_disk():
    p = OUT.parent / 'data' / 'MANIFEST-raw.json'
    if not p.exists():
        raise _Skip('no raw manifest')
    m = D.read_json(p)
    raw = p.parent / 'raw'
    assert m['files'], 'empty manifest'
    for f in m['files'][:3]:                    # hashing every GB here would be wasteful
        q = raw / f['name']
        if not q.exists():
            raise _Skip(f'{f["name"]} not on this machine')
        assert q.stat().st_size == f['bytes'], f['name']
        assert D.sha256_file(q) == f['sha256'], f['name']


TESTS = [(name, obj) for name, obj in sorted(globals().items())
         if name.startswith('test_') and callable(obj)]


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default=str(DEFAULT_OUT))
    parser.add_argument('--only', default=None)
    args = parser.parse_args()
    OUT = Path(args.out)
    for name, function in TESTS:
        if args.only and args.only not in name:
            continue
        check(name, function)
    print(f'\nPASSED {PASSED}  FAILED {FAILED}  SKIPPED {SKIPPED}', flush=True)
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
