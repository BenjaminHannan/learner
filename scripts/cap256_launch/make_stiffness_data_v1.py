"""Data for the stiffness test (STIFFNESS-TEST-v1.md): practice rows from two skill families that no skills run trained on.

Families clock_date and string_transform are held-out families in the PR #32 curriculum (heldout_family=True), so
neither the skills checkpoint (main2) nor its parent saw them. One fixed 200-row test set (100 per family) and six
4000-row practice sets (2000 per family, shuffled), one per paired seed. No practice prompt equals a test prompt or a
curriculum dev/family prompt. Deterministic.

usage: python make_stiffness_data_v1.py --curriculum DIR_CONTAINING_skills_curriculum --out artifacts/stiffness-test-v1/data
"""
import argparse
import json
import random
import sys
from pathlib import Path

FAMS = ('clock_date', 'string_transform')
KEEP = ('id', 'family', 'variant', 'prompt', 'answer', 'accepted', 'steps')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--curriculum', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seeds', type=int, default=6)
    ap.add_argument('--train-per-family', type=int, default=2000)
    ap.add_argument('--test-per-family', type=int, default=100)
    a = ap.parse_args()
    sys.path.insert(0, a.curriculum)
    from skills_curriculum import skills  # noqa: F401  (registers families)
    from skills_curriculum.core import FAMILIES
    from skills_curriculum.build import Maker
    assert all(FAMILIES[f]['heldout_family'] for f in FAMS)

    def slim(it, stage):
        return dict({k: it[k] for k in KEEP}, stage=stage)

    seen = set()
    for f in FAMS:  # the curriculum's own dev/family rows (namespace DF, build seed 1, 40 per family)
        m = Maker(f, 'DF', 1)
        for _ in range(40):
            it = m.next('family', seen)
            if it is not None:
                seen.add(it['prompt'])
    test = []
    for f in FAMS:
        m = Maker(f, 'XE', 1)
        for _ in range(a.test_per_family):
            it = m.next('family', seen)
            seen.add(it['prompt'])
            test.append(slim(it, 0))
    out = Path(a.out)
    manifest = {'families': FAMS, 'test_rows': len(test), 'seeds': {}}
    for s in range(1, a.seeds + 1):
        rows, own = [], set(seen)
        for f in FAMS:
            m = Maker(f, 'XT%d' % s, 1)
            for _ in range(a.train_per_family):
                it = m.next('family', own)
                own.add(it['prompt'])
                rows.append(slim(it, 1))
        random.Random('stiffness-order|%d' % s).shuffle(rows)
        d = out / ('seed%d' % s)
        (d / 'dev').mkdir(parents=True, exist_ok=True)
        (d / 'train.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
        (d / 'dev' / 'in_dist.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in test))
        manifest['seeds'][s] = len(rows)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
