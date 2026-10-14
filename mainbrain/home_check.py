"""Per-row hits for every night checkpoint of a domain-mode run on any rows file (the home self-check scorer).

  python -m mainbrain.home_check --run RUN --parent PARENT_CKPT --rows ROWS.jsonl --out OUT.json [--nights 1,2] [--threads 1] [--parent-cache DIR]

Parent hits are cached in DIR (default: dirname of OUT) keyed by the parent path and the rows file, shared across runs.
A night whose weights fingerprint equals the parent's or an earlier night's reuses those hits (undone nights restore the previous model).
OUT is rewritten after each night; on restart, nights already in OUT with the same fingerprint are skipped.
"""
import argparse
import hashlib
import json
import os
import re
import time

import torch

from domain import harm


def fingerprint(ck):
    """sha1 over the sorted names, dtypes, shapes and bytes of the checkpoint's model weights."""
    h = hashlib.sha1()
    w = ck['model']
    for k in sorted(w):
        t = w[k].detach().cpu().contiguous()
        h.update(f'{k}|{t.dtype}|{tuple(t.shape)}'.encode())
        h.update(t.reshape(-1).view(torch.uint8).numpy().tobytes())
    return h.hexdigest()


def file_fingerprint(path):
    return fingerprint(torch.load(path, map_location='cpu', weights_only=True))


def hit_string(hits):
    return ''.join(str(int(x)) for x in hits)


def find_reuse(fp, known):
    """known: list of (name, fp) in order, parent first. -> name of the first entry with the same fp, or None."""
    for name, f in known:
        if f == fp:
            return name
    return None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def run_events(run):
    checks, nevs = {}, {}
    lp = os.path.join(run, 'log.jsonl')
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
    return checks, nevs


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument('--run', required=True)
    a.add_argument('--parent', required=True)
    a.add_argument('--rows', required=True)
    a.add_argument('--out', required=True)
    a.add_argument('--nights', default=None)
    a.add_argument('--threads', type=int, default=1)
    a.add_argument('--parent-cache', default=None)
    a = a.parse_args(argv)
    torch.set_num_threads(a.threads)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cache_dir = a.parent_cache or os.path.dirname(os.path.abspath(a.out))
    os.makedirs(cache_dir, exist_ok=True)

    rows = harm.load_rows(a.rows)
    rsha = sha256_file(a.rows)
    ids = [r['id'] for r in rows]
    cache = os.path.join(cache_dir, 'parent-' + hashlib.sha1(os.path.abspath(a.parent).encode()).hexdigest()[:12] + '-' + rsha[:12] + '.json')
    par = None
    if os.path.exists(cache):
        try:
            par = json.load(open(cache))
            assert len(par['hits']) == len(rows)
        except Exception:
            par = None
    if par is None:
        t = time.time()
        fp = file_fingerprint(a.parent)
        h0, exact = harm.in_dist_hits(a.parent, rows)
        par = dict(hits=hit_string(h0), exact=exact, fp=fp)
        json.dump(par, open(cache, 'w'))
        print(f'parent hits computed in {time.time() - t:.0f}s', flush=True)

    if a.nights:
        nights = [int(x) for x in a.nights.split(',') if x.strip()]
    else:
        nights = sorted(int(m.group(1)) for d in os.listdir(a.run) if (m := re.fullmatch(r'night_(\d+)', d))
                        and os.path.exists(os.path.join(a.run, d, 'checkpoint.pt')))
    nights.sort()
    checks, nevs = run_events(a.run)

    res = dict(run=a.run, rows=a.rows, rows_sha256=rsha, ids=ids, parent=dict(path=a.parent, hits=par['hits'], exact=par['exact'], fp=par['fp']), nights={})
    if os.path.exists(a.out):
        try:
            old = json.load(open(a.out))
            if old.get('rows_sha256') == rsha and old.get('run') == a.run:
                res['nights'] = old['nights']
        except Exception:
            pass
    known = [('parent', par['fp'])]
    by_name = {'parent': par}
    for k in nights:
        ck = os.path.join(a.run, f'night_{k}', 'checkpoint.pt')
        if not os.path.exists(ck):
            print(f'night {k}: no checkpoint, skipped', flush=True)
            continue
        t = time.time()
        fp = file_fingerprint(ck)
        prev = res['nights'].get(str(k))
        if prev and prev.get('fp') == fp:
            print(f'night {k}: already done', flush=True)
            known.append((k, fp))
            by_name[k] = prev
            continue
        src = find_reuse(fp, known)
        if src is not None:
            hits, exact = by_name[src]['hits'], by_name[src]['exact']
        else:
            h, exact = harm.in_dist_hits(ck, rows)
            hits = hit_string(h)
        known.append((k, fp))
        by_name[k] = dict(hits=hits, exact=exact)
        ce, ne = checks.get(k, {}), nevs.get(k, {})
        res['nights'][str(k)] = dict(fp=fp, hits=hits, exact=exact, reused_from=src, agreement=ce.get('agreement'), undo=ce.get('undo'),
                                     undone=ne.get('undone'), quiz_pooled=ne.get('quiz_pooled'), secs=round(time.time() - t, 1))
        tmp = a.out + '.tmp'
        json.dump(res, open(tmp, 'w'), indent=1)
        os.replace(tmp, a.out)
        print(f"night {k}: exact {exact:.2f}  hits {sum(map(int, hits))}/{len(hits)} parent {sum(map(int, par['hits']))}  "
              f"reused_from {src}  agreement {ce.get('agreement')}  undone {ne.get('undone')}  ({time.time() - t:.0f}s)", flush=True)


if __name__ == '__main__':
    main()
