"""Research-loop holdout for C2 (locked; written 10-07 before any loop trial). Fresh C2 questions over the same five held-out kinds and the same
representable rules, from a new generator tag, sharing no (kind, params, examples, query) key with warm, dev, pool or labelled. The sealed test split is
never read. Only the harness's `calibrate`/`confirm` evaluates this file; nothing trains on it.

  python3 -m creative.rl.make_holdout          (writes creative/data/c2rl/holdout.jsonl + MANIFEST.json, prints counts only)
"""
import hashlib, json, os
from creative import rules_real as R

DATA, OUT, N, SEED, TAG = 'creative/data/c2', 'creative/data/c2rl', 512, 7031, 'rlholdout'


def main():
    use_h, _, _ = R.representable_params(R.HELD_OUT)
    avoid = set()
    for name in ('warm', 'dev', 'pool', 'labelled'):
        for r in R.load_split(DATA, name):
            p = R.fewshot.parse(r['prompt'])
            avoid.add((r['kind'], tuple(r['params']), tuple(p['xs']), p['q']))
    held = tuple(k for k in R.HELD_OUT if use_h.get(k))
    rows = R.make_questions(held, use_h, N, SEED, TAG, avoid)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'holdout.jsonl')
    with open(path, 'w') as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + '\n')
    man = dict(holdout=dict(n=len(rows), sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(),
                            kinds={k: sum(r['kind'] == k for r in rows) for k in held}),
               _spec=dict(seed=SEED, tag=TAG, avoid_splits=['warm', 'dev', 'pool', 'labelled'], note='sealed test never read'))
    json.dump(man, open(os.path.join(OUT, 'MANIFEST.json'), 'w'), indent=1, sort_keys=True)
    print('holdout', man['holdout']['n'], man['holdout']['kinds'], man['holdout']['sha256'][:12])


if __name__ == '__main__':
    main()
