"""Convert logicgen rows to the custom_io row format.

  python -m logic_transfer.rows convert --in GEN.jsonl --out ROWS.jsonl [--vocab CKPT]   (also verifies)
  python -m logic_transfer.rows verify ROWS.jsonl [--vocab CKPT]

custom_io row: id, prompt, answer, accepted, family, level, stage, variant, steps (+ meta, ignored by the loader, kept by
score.py). family = logic_fc (kind logic) / logic_placebo (kind placebo); variant = the generator split name; level = the
rule-chain depth (0 when the generator gives none); stage = 9 (the curriculum's uniform-mix stage). steps = ["none"] like
the syllogism family, so progparse finds NO calculator program and the row trains NOOP calls (weight 0.1) plus the answer
through the mode head. The generator's proof sentences are kept under meta.proof and never reach the loss.
"""
import argparse
import json
import sys

FAMILY = {'logic': 'logic_fc', 'placebo': 'logic_placebo', 'rung0': 'lad_r0', 'rung1': 'lad_r1', 'rung2': 'lad_r2'}
STAGE = 9
META_KEYS = ('kind', 'split', 'label', 'depth', 'program', 'n_rules', 'n_facts', 'n_distractors', 'sampler',
             'template_set', 'query', 'ctx', 'pkind', 'template_ids', 'chars', 'sub', 'f2_triple')


OPTIONS = ('true', 'false', 'unknown')
OPTIONS_CHARS = 21          # len(' (false/true/unknown)'): generate with --max-chars 208 - OPTIONS_CHARS so the suffixed prompt fits


def options_suffix(row_id):
    """' (a/b/c)': the three answer words in a per-row (hash-seeded) random order. The answer is then a word of the prompt, so the model
    can COPY it (WORD mode) instead of writing 4-7 letters through the 9-register generator; answer position carries no information."""
    import hashlib
    h = int(hashlib.sha256(row_id.encode()).hexdigest(), 16)
    o = list(OPTIONS)
    for i in range(len(o) - 1, 0, -1):
        j = h % (i + 1)
        h //= (i + 1)
        o[i], o[j] = o[j], o[i]
    return ' (' + '/'.join(o) + ')'


def convert_row(g, options=False):
    meta = {k: g[k] for k in META_KEYS if k in g}
    meta['proof'] = list(g.get('steps') or [])
    meta['gen_id'] = g['id']
    prompt = g['question'] + (options_suffix(g['id']) if options else '')
    return {'id': 'lt-' + g['id'], 'prompt': prompt, 'answer': g['answer'], 'accepted': [g['answer']],
            'family': FAMILY[g['kind']], 'level': int(g['depth']) if g.get('depth') is not None else 0, 'stage': STAGE,
            'variant': g['split'], 'steps': ['none'], 'meta': meta}


def convert(src, dst, options=False):
    n = 0
    seen = set()
    with open(src) as f, open(dst, 'w') as o:
        for line in f:
            if not line.strip():
                continue
            r = convert_row(json.loads(line), options)
            assert r['id'] not in seen, f'duplicate id {r["id"]}'
            seen.add(r['id'])
            o.write(json.dumps(r) + '\n')
            n += 1
    return n


def verify(path, chars=None, max_prompt=208):
    """-> dict of counts; raises AssertionError on any violation. chars: the parent checkpoint's vocab chars (default: all printable
    ASCII, which is what CharVocab.build always includes)."""
    from custom_io.data import CharVocab, ASCII, UNK, MAX_ANS, load_rows
    from custom_io.models import progparse as pp
    vocab = CharVocab(chars if chars is not None else ASCII)
    rows = load_rows(path, keep=None)
    assert rows, 'no rows'
    ids = set()
    modes = {0: 0, 1: 0, 2: 0}
    for r in rows:
        for k in ('id', 'prompt', 'answer', 'accepted', 'family', 'level', 'stage', 'variant', 'steps'):
            assert k in r, (r.get('id'), k)
        assert r['id'] not in ids, f'duplicate id {r["id"]}'
        ids.add(r['id'])
        assert r['family'] in FAMILY.values(), r['family']
        assert len(r['prompt']) <= max_prompt, (r['id'], len(r['prompt']))
        assert 1 <= len(r['answer']) <= MAX_ANS, (r['id'], r['answer'])
        assert UNK not in vocab.encode(r['prompt']) and UNK not in vocab.encode(r['answer']), f'unknown char in {r["id"]}'
        assert r['answer'] in r['accepted']
        t = pp.row_targets(r)
        assert not t['prog'], f'{r["id"]} parsed to a calculator program'
        modes[t['mode']] += 1
    return {'n': len(rows), 'no_program': len(rows), 'max_prompt_chars': max(len(r['prompt']) for r in rows),
            'answer_mode_NUM_WORD_GEN': [modes[0], modes[1], modes[2]], 'unk_chars': 0}


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('convert')
    c.add_argument('--in', dest='src', required=True)
    c.add_argument('--out', required=True)
    c.add_argument('--vocab', help='checkpoint whose chars to check against (default: all printable ASCII)')
    c.add_argument('--options', action='store_true', help="append ' (true/false/unknown)' in a per-row random order (format v2)")
    v = sub.add_parser('verify')
    v.add_argument('path')
    v.add_argument('--vocab')
    a = ap.parse_args(argv)
    chars = None
    if a.vocab:
        import torch
        chars = torch.load(a.vocab, map_location='cpu', weights_only=True)['chars']
    if a.cmd == 'convert':
        n = convert(a.src, a.out, a.options)
        print(f'converted {n} rows -> {a.out}')
        path = a.out
    else:
        path = a.path
    print(json.dumps(verify(path, chars)))


if __name__ == '__main__':
    main()
