"""DEV old-skills harm measure for every night checkpoint of a domain-mode run.

  python -m mainbrain.harm_nights --run RUN --parent PARENT_CKPT --dev DEV_JSONL --out OUT.json [--nights 1,2,3] [--threads 1]

Parent hits are cached in OUT + '.parent.json'. OUT is rewritten after each night so partial results survive.
"""
import argparse
import json
import os
import re
import time

import torch

from domain import harm


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument('--run', required=True)
    a.add_argument('--parent', required=True)
    a.add_argument('--dev', required=True)
    a.add_argument('--out', required=True)
    a.add_argument('--nights', default=None)
    a.add_argument('--threads', type=int, default=1)
    a = a.parse_args(argv)
    torch.set_num_threads(a.threads)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    rows = harm.load_rows(a.dev)
    cache = a.out + '.parent.json'
    h0 = None
    if os.path.exists(cache):
        try:
            c = json.load(open(cache))
            if len(c.get('hits', [])) == len(rows):
                h0 = c['hits']
        except Exception:
            h0 = None
    if h0 is None:
        t = time.time()
        h0, exact = harm.in_dist_hits(a.parent, rows)
        json.dump(dict(hits=h0, exact=exact), open(cache, 'w'))
        print(f'parent hits computed in {time.time() - t:.0f}s', flush=True)

    if a.nights:
        nights = [int(x) for x in a.nights.split(',') if x.strip()]
    else:
        nights = sorted(int(m.group(1)) for d in os.listdir(a.run) if (m := re.fullmatch(r'night_(\d+)', d))
                        and os.path.exists(os.path.join(a.run, d, 'checkpoint.pt')))

    checks, nevs = {}, {}
    lp = os.path.join(a.run, 'log.jsonl')
    if os.path.exists(lp):
        for line in open(lp):
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get('event') == 'check':
                checks[e['night']] = e
            elif e.get('event') == 'night':
                nevs[e['night']] = e

    res = dict(run=a.run, parent=a.parent, dev=a.dev, nights={})
    for k in nights:
        ck = os.path.join(a.run, f'night_{k}', 'checkpoint.pt')
        if not os.path.exists(ck):
            print(f'night {k}: no checkpoint, skipped', flush=True)
            continue
        t = time.time()
        h1, _ = harm.in_dist_hits(ck, rows)
        hm = harm.harm_measure(h0, h1, rows, family_drop=5.0, in_dist_drop=1.5)
        fam = hm['families']
        top = sorted(fam, key=lambda f: -fam[f]['drop'])[:5]
        ce, ne = checks.get(k, {}), nevs.get(k, {})
        res['nights'][str(k)] = dict(
            in_dist_drop=hm['in_dist_drop'], fired=hm['fired'], passes=hm['passes'],
            families_fired={f: {x: fam[f][x] for x in ('a', 'b', 'drop', 'lo', 'hi')} for f in hm['fired']},
            top_drops={f: {x: fam[f][x] for x in ('a', 'b', 'drop')} for f in top},
            agreement=ce.get('agreement'), undo=ce.get('undo'), quiz_pooled=ne.get('quiz_pooled'))
        tmp = a.out + '.tmp'
        json.dump(res, open(tmp, 'w'), indent=1)
        os.replace(tmp, a.out)
        print(f"night {k}: in_dist drop {hm['in_dist_drop']:.2f}  fired {hm['fired']}  agreement {ce.get('agreement')}  "
              f"undone {ne.get('undone')}  ({time.time() - t:.0f}s)", flush=True)


if __name__ == '__main__':
    main()
