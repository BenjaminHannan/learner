"""Write / update logic_transfer/ladder-hashes.json from built row directories (the seal that lt2.ensure_rows checks against, byte for byte).

  python -m logic_transfer.seal_hashes --rows DIR --rungs 0 1 2 3        (DIR = a `ladder build --out` directory; merges into the existing file)
Rung 3 is additionally compared with the LT-1 sealed placebo hashes (dev 3c9a4e5b6d83..., wording 2a3649b7a957...; train 2080dbb6...).
"""
import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LT1_PREFIX = {'train': '2080dbb6', 'dev': '3c9a4e5b6d83', 'wording': '2a3649b7a957'}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', required=True)
    ap.add_argument('--rungs', type=int, nargs='+', required=True)
    ap.add_argument('--out', default=os.path.join(HERE, 'ladder-hashes.json'))
    a = ap.parse_args(argv)
    cur = json.load(open(a.out)) if os.path.exists(a.out) else {}
    for r in a.rungs:
        from logic_transfer import ladder
        d = os.path.join(a.rows, f'rung{r}')
        s = json.load(open(os.path.join(d, 'summary.json')))
        names = list(s['files'])
        if r == 2:                                       # the hard-negative subset of dev (Addendum 3) is sealed with the rung
            from logic_transfer import hard
            hard.make_hard(d)
            names.append('hard')
        cur[f'rung{r}'] = {name: ladder.sha256(os.path.join(d, name + '.jsonl')) for name in names}      # re-hashed from the bytes on disk, not copied from summary.json
        if r == 3:
            for name, pre in LT1_PREFIX.items():
                got = cur['rung3'][name]
                assert got.startswith(pre), f'rung 3 {name} {got[:12]} is not the LT-1 sealed file ({pre}...)'
        print(f'rung{r}:', {k: v[:12] for k, v in cur[f"rung{r}"].items()})
    json.dump(cur, open(a.out, 'w'), indent=1, sort_keys=True)


if __name__ == '__main__':
    main()
