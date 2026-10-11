"""Sealed old-skill lookalike panel.

python3 -m domain.panel_lookalike_old --out DIR [--curriculum DIR] [--data DIR] [--parent CKPT]

Draws prompts from the OLD skills curriculum (skills_curriculum.build.Maker) for the three families that
look like the new test subjects, 100 rows per variant. Every row is fresh: its prompt is not in train.jsonl
or any dev/*.jsonl file, is at most 208 characters, and uses only characters in the parent checkpoint's vocab.
Writes lookalike-old.v1.jsonl and lookalike-old.v1.jsonl.sha256; refuses to overwrite either file.

Deviation from LOOKALIKE-MARKS sec. 3 (Opus, 8:55 PM ET 10-10, before any result): four listed variants are never in
training or in_dist, because the curriculum holds them out (larger and count_above of compare_numbers, sum of list_stats,
cost of table_calc; 'total' was a wrong name for cost). So lookalike-old.v1 (LA3) holds the 8 in-distribution variants,
and the 4 held-out variants go to a second file, lookalike-old-heldout.v1.jsonl (drawn with the curriculum's own
'variant' filter, namespace LV), scored and reported only.
"""
import argparse
import collections
import glob
import hashlib
import json
import os
import sys

SCRATCH = '/tmp/claude-0/-home-user-learner/8756871c-45c5-51b2-a641-8a1f43fbd0e2/scratchpad'
DEFAULT_CURRICULUM = os.path.join(SCRATCH, 'cur')
DEFAULT_DATA = os.path.join(SCRATCH, 'sk200k')
DEFAULT_PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'

SEED = 91031
NS = 'LA'
PER_VARIANT = 100
MAX_CHARS = 208
DRAW_CAP = 200000
NAME = 'lookalike-old.v1.jsonl'

NAME_HELD = 'lookalike-old-heldout.v1.jsonl'

TARGETS = (
    ('compare_numbers', ('smaller', 'largest_of', 'smallest_of')),
    ('list_stats', ('range', 'count_even', 'second_largest')),
    ('table_calc', ('row_total', 'column_sum')),
)
HELD_TARGETS = (   # held out of training by the curriculum (its 'variant' split): reported only
    ('compare_numbers', ('larger', 'count_above')),
    ('list_stats', ('sum',)),
    ('table_calc', ('cost',)),
)


def load_chars(parent):
    import torch
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    return set(ck['chars'])


def load_seen(data):
    paths = [os.path.join(data, 'train.jsonl')] + sorted(glob.glob(os.path.join(data, 'dev', '*.jsonl')))
    seen = set()
    for p in paths:
        with open(p, encoding='utf-8') as f:
            for line in f:
                seen.add(json.loads(line)['prompt'])
    return seen, paths


def build_rows(curriculum, data, parent, log=print, targets=TARGETS, kind='in_dist', ns=NS, seen=None):
    sys.path.insert(0, curriculum)
    from skills_curriculum.build import Maker
    from skills_curriculum.core import FAMILIES

    chars = load_chars(parent)
    if seen is None:
        seen, seen_files = load_seen(data)
        log(f'seen prompts: {len(seen)} from {len(seen_files)} files; vocab size {len(chars)}')

    rows, stats = [], {}
    for fam, variants in targets:
        missing = [v for v in variants if v not in FAMILIES[fam]['variants']]
        assert not missing, (fam, missing)
        m = Maker(fam, ns, SEED)
        kept = {v: [] for v in variants}
        st = collections.Counter()
        while any(len(kept[v]) < PER_VARIANT for v in variants):
            assert st['draws'] < DRAW_CAP, (
                f'{fam}: draw cap {DRAW_CAP} hit', {v: len(kept[v]) for v in variants})
            st['draws'] += 1
            it = m.next(kind, seen)
            if it is None:
                st['none'] += 1
                continue
            p = it['prompt']
            if len(p) > MAX_CHARS:
                st['too_long'] += 1
                continue
            if not set(p) <= chars:
                st['out_of_vocab'] += 1
                continue
            v = it['variant']
            if v not in kept:
                st['other_variant'] += 1
                continue
            if len(kept[v]) >= PER_VARIANT:
                st['variant_full'] += 1
                continue
            seen.add(p)
            kept[v].append(it)
            st['kept'] += 1
        for v in variants:
            for idx, it in enumerate(kept[v], 1):
                r = dict(it)
                r['id'] = f'{ns}-{v}-{idx:03d}'
                r['kind'] = v
                r['split'] = 'old'
                rows.append(r)
        stats[fam] = dict(st)
        log(f'{fam}: {dict(st)}')

    assert len({r['id'] for r in rows}) == len(rows), 'duplicate ids'
    assert len({r['prompt'] for r in rows}) == len(rows), 'duplicate prompts'
    return rows, stats, seen


def write_panel(out_dir, rows, name=NAME):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    sha_path = path + '.sha256'
    for p in (path, sha_path):
        if os.path.exists(p):
            raise SystemExit(f'refusing to overwrite {p}')
    data = ''.join(json.dumps(r) + '\n' for r in rows).encode('utf-8')
    digest = hashlib.sha256(data).hexdigest()
    with open(path, 'xb') as f:
        f.write(data)
    with open(path, 'rb') as f:
        assert hashlib.sha256(f.read()).hexdigest() == digest
    with open(sha_path, 'x') as f:
        f.write(f'{digest}  {name}\n')
    return path, digest


def main(argv=None):
    ap = argparse.ArgumentParser(description='Sealed old-skill lookalike panel (lookalike-old.v1.jsonl).')
    ap.add_argument('--out', required=True, help='directory to write into (created if missing)')
    ap.add_argument('--curriculum', default=DEFAULT_CURRICULUM,
                    help='directory that contains the skills_curriculum package')
    ap.add_argument('--data', default=DEFAULT_DATA, help='directory with train.jsonl and dev/*.jsonl')
    ap.add_argument('--parent', default=DEFAULT_PARENT, help='checkpoint whose chars give the vocabulary')
    a = ap.parse_args(argv)

    for p in (NAME, NAME_HELD):
        if os.path.exists(os.path.join(a.out, p)):
            raise SystemExit(f'refusing to overwrite {p}')
    rows, _stats, seen = build_rows(a.curriculum, a.data, a.parent)
    held, _hstats, _ = build_rows(a.curriculum, a.data, a.parent, targets=HELD_TARGETS, kind='variant', ns='LV', seen=seen)
    assert not {r['prompt'] for r in rows} & {r['prompt'] for r in held}
    for name, rs, targets in ((NAME, rows, TARGETS), (NAME_HELD, held, HELD_TARGETS)):
        path, digest = write_panel(a.out, rs, name)
        counts = collections.Counter((r['family'], r['variant']) for r in rs)
        for fam, variants in targets:
            for v in variants:
                print(f'{fam:16s} {v:14s} {counts[(fam, v)]}')
        opener = sum(1 for r in rs if (r.get('wrap') or {}).get('pre'))
        print(f'rows {len(rs)}; rows with opener (wrap.pre non-empty) {opener} ({opener / len(rs):.4f})')
        print(f'wrote {path}')
        print(f'sha256 {digest}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
