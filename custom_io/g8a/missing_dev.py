"""Fresh missing-operand file for B3G2-4 ("the inverse is found in the head", L1; PLAN.md big-run, G2 step 2b).

The pooled-5 dev splits (6,040 rows) hold only 43 rows the inverse-op rewrite touches (all arith_bare 'missing'); the mark reads at least 200. This builds 300
fresh rows of the touched family: arith_bare, variant 'missing' ("19 + ? = 30"), generator-clean ("in_dist": no held-out answer, frame, vocab or layout), every
row one that progparse's inverse rewrite fires on (checked), namespace MD, seed 71717 (training 1, long file 424242, ST1 5311/5312, 8a 400-405), prompts disjoint
from every training pool, dev split, the long file and the ST1 files. Dev-row format.

  python3 -m custom_io.g8a.missing_dev --curriculum DIR --out OUT --pools train.jsonl ... --dev DEVDIR ... --avoid FILE ...
"""
import argparse, glob, hashlib, json, os, random, re, sys

SEED, NS, N = 71717, 'MD', 300


def touched(r):
    """True iff the inverse rewrite of custom_io/models/progparse.py fires on this row (the missing-operand branch of to_program or Builder.invert)."""
    from custom_io.models import progparse as pp
    if len(r['steps']) == 1 and re.fullmatch(r'\d+', r['answer']):
        m = re.fullmatch(r'(\d+) ([-+*/]) (\d+) = (\d+)', r['steps'][0].strip())
        if m:
            a, c2, res, ans = int(m.group(1)), int(m.group(3)), int(m.group(4)), int(r['answer'])
            nums = pp.prompt_numbers(r['prompt'])
            if ans != res and res in nums and ((a == ans and a not in nums) or (c2 == ans and c2 not in nums)):
                return True
    return False


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--curriculum', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--pools', nargs='*', default=[])
    ap.add_argument('--dev', nargs='*', default=[])
    ap.add_argument('--avoid', nargs='*', default=[])
    a = ap.parse_args(argv)
    sys.path.insert(0, a.curriculum)
    from skills_curriculum import skills, build as B  # noqa: F401
    from skills_curriculum.core import make_item
    from custom_io.g8a.st1_data import prompts
    avoid = prompts(a.pools) | prompts([os.path.join(d, '*.jsonl') for d in a.dev]) | prompts(a.avoid)
    rng = random.Random(f'{NS}|{SEED}')
    rows, i = [], 0
    while len(rows) < N:
        i += 1
        assert i < 100000, len(rows)
        it = make_item('arith_bare', f'{NS}{SEED}', i, rng.choices((0, 1, 2), B.DIFF_WEIGHTS)[0], force_variant='missing')
        if any(it['flags'].values()) or it['est_tokens'] > B.MAX_TOKENS_EST or it['prompt'] in avoid or not touched(it):
            continue
        avoid.add(it['prompt'])
        it['id'] = f'missing-{len(rows):04d}'
        rows.append(it)
    os.makedirs(a.out, exist_ok=True)
    f = os.path.join(a.out, 'missing_dev.jsonl')
    with open(f, 'w', encoding='utf-8') as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + '\n')
    man = dict(file='missing_dev.jsonl', sha256=sha(f), rows=len(rows), draws=i, family='arith_bare', variant='missing', seed=SEED, namespace=NS,
               generator_files_sha256={os.path.basename(p): sha(p) for p in sorted(glob.glob(os.path.join(a.curriculum, 'skills_curriculum', '*.py')))},
               note='pooled-5 dev holds 43 touched rows (arith_bare missing); the mark needs >= 200')
    json.dump(man, open(os.path.join(a.out, 'missing_dev_MANIFEST.json'), 'w'), indent=1)
    print(json.dumps({k: man[k] for k in ('sha256', 'rows', 'draws')}))


if __name__ == '__main__':
    main()
