# Read-only: gate G1 seed 400 at 3M and 10M from the RESULT.json files (pooled-5 = correct / n over the five dev splits).
import json, os, sys
R = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\benja\custom-io\work\results'
S = ['in_dist', 'answer', 'frame', 'vocab', 'variant']
for p in ['8aG1d-pc/8aG1d-3M-s400/B2', '8aG1d-pc/8aG1d-3M-s400/PT', '8aG1e-pc/8aG1e-3M-s401/B2', '8aG1e-pc/8aG1e-3M-s401/PT',
          '8aG1f-pc/8aG1f-10M-s400/B2', '8aG1fR-pc/8aG1fR-10M-s400/PT']:
    f = os.path.join(R, *p.split('/'), 'RESULT.json')
    try:
        d = json.load(open(f, encoding='utf-8'))
        fe = d['final_eval']
        pooled = 100.0 * sum(fe[k]['correct'] for k in S) / sum(fe[k]['n'] for k in S)
        extra = {k: v for k, v in d.items() if k not in ('config', 'final_eval') and not isinstance(v, (dict, list))}
        print(p, 'pooled5 %.3f' % pooled, ' '.join('%s %.2f' % (k, fe[k]['exact']) for k in S), 'chain5', (d.get('chain5') or {}).get('intact', {}).get('exact'),
              'params', d.get('n_params'), json.dumps(extra))
        fam = {}
        for k in S:
            for name, v in fe[k].get('by_family', {}).items():
                c, n = fam.get(name, (0, 0)); fam[name] = (c + v['correct'], n + v['n'])
        print('  families', json.dumps({k: round(100.0 * c / n, 1) for k, (c, n) in sorted(fam.items()) if n}))
    except Exception as e:
        print(p, 'ERROR', repr(e))
