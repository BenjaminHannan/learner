"""python3 -I ld_overlap.py LONG_DEV.jsonl SLICES_DIR OUT.json   (overlap13.py from data_pool on claude/data-pool-8b beside it)
Which long_dev rows share a 13-gram (or a whole 8-12 word text) with documents in the old 8a web slices, per rung."""
import json, sys, os
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
import overlap13 as O

LD, SL = sys.argv[1], sys.argv[2]
rows = [json.loads(l) for l in open(LD) if l.strip()]
hmap = {}          # (n, hash) -> set of row ids
starts = {}        # first two words of a window -> set of window lengths to hash there
for r in rows:
    hs, _ = O.panel_hashes(r['prompt'])
    for k in hs:
        hmap.setdefault(k, set()).add(r['id'])
    ws = O.words(r['prompt'])
    if len(ws) >= O.N:
        for i in range(len(ws) - O.N + 1):
            starts.setdefault((ws[i], ws[i + 1]), set()).add(O.N)
    elif len(ws) >= O.MIN_SHORT:
        starts.setdefault((ws[0], ws[1]), set()).add(len(ws))


def scan(line):
    d = json.loads(line)
    ws = O.words(d['text'])
    hit = set()
    for i in range(len(ws) - 1):
        ns = starts.get((ws[i], ws[i + 1]))
        if ns:
            for n in ns:
                if i + n <= len(ws):
                    k = (n, O.h(ws[i:i + n]))
                    if k in hmap:
                        hit |= hmap[k]
    return d['id'], sorted(hit)


out = {}
for rung in ('rung3', 'rung10', 'rung30'):
    with Pool(4) as p:
        res = [x for x in p.imap(scan, open(os.path.join(SL, f'slice_{rung}.jsonl')), chunksize=200) if x[1]]
    touched = sorted({i for _, ids in res for i in ids})
    out[rung] = dict(docs_hit=len(res), long_dev_rows_touched=len(touched), rows=touched)
    print(rung, 'docs hit', len(res), 'long_dev rows touched', len(touched), flush=True)
fam = {}
for i in out['rung30']['rows']:
    f = next(r for r in rows if r['id'] == i)
    fam[f['family'] + '/' + f['long']['bucket']] = fam.get(f['family'] + '/' + f['long']['bucket'], 0) + 1
out['rung30_by_family_bucket'] = fam
out['long_dev_rows'] = len(rows)
json.dump(out, open(sys.argv[3], 'w'), indent=1)
