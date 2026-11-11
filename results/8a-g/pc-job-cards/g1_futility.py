"""Gate G1 futility check (spec design/8a-g-gemma-growth-2026-10-08.md, addendum I), run on BensPC by q8aG1s401_wait.ps1.

After 10M s400: gain difference = (G-B2 10M - G-B2 3M) - (G-PT 10M - G-PT 3M), pooled-5 = correct / n summed over the five
splits. At or below -1.0 the gate cannot pass (Go needs +1.0 on both seeds), so 10M s401 is skipped. Exit 3 = skip 10M s401,
exit 0 = run it. Any error also exits 0, so a fault here never holds the GPU back. Writes WORK\\g1-futility.json."""
import glob, json, os, sys

SPLITS = ['in_dist', 'answer', 'frame', 'vocab', 'variant']
RES = r'C:\Users\benja\custom-io\work\results'
LIMIT = -1.0


def pooled(path):
    fe = json.load(open(path, encoding='utf-8'))['final_eval']
    return 100.0 * sum(fe[k]['correct'] for k in SPLITS) / sum(fe[k]['n'] for k in SPLITS)


def ok_job(d):
    try:
        return json.load(open(os.path.join(d, 'RESULT.json'), encoding='utf-8')).get('status') == 'ok'
    except (OSError, ValueError):
        return False


def main():
    out, skip = {}, False
    try:
        d3 = os.path.join(RES, '8aG1d-pc', '8aG1d-3M-s400')
        tens = sorted((d for d in glob.glob(os.path.join(RES, '8aG1*-pc', '8aG1*-10M-s400')) if ok_job(d)), key=os.path.getmtime)
        if not ok_job(d3) or not tens:
            raise RuntimeError('3M s400 or 10M s400 job missing or not ok')
        d10 = tens[-1]
        p = {f'{r}_{a}': pooled(os.path.join(d, a, 'RESULT.json')) for r, d in (('3M', d3), ('10M', d10)) for a in ('B2', 'PT')}
        d_b2, d_pt = p['10M_B2'] - p['3M_B2'], p['10M_PT'] - p['3M_PT']
        out = dict(seed=400, dir_3m=d3, dir_10m=d10, pooled5={k: round(v, 3) for k, v in p.items()}, d_B2=round(d_b2, 3),
                   d_PT=round(d_pt, 3), gain_difference=round(d_b2 - d_pt, 3), limit=LIMIT)
        skip = (d_b2 - d_pt) <= LIMIT
    except Exception as e:                       # fail open: run 10M s401
        out = dict(error=repr(e))
    out['decision'] = 'skip 10M s401' if skip else 'run 10M s401'
    try:
        json.dump(out, open(os.path.join(os.path.dirname(RES), 'g1-futility.json'), 'w', encoding='utf-8'), indent=1)
    except OSError:
        pass
    print(json.dumps(out))
    sys.exit(3 if skip else 0)


if __name__ == '__main__':
    main()
