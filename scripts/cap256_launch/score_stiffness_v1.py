"""Score the stiffness test (STIFFNESS-TEST-v1.md) from the 12 SKILLS-RESULT.json files. Marks were fixed before training.

usage: python score_stiffness_v1.py PKG_ROOT   (reads PKG_ROOT/artifacts/stiffness/{A,B}{1..6}/SKILLS-RESULT.json)
"""
import json
import sys
from pathlib import Path


def pct(d):
    return 100.0 * d['correct'] / d['n'] if d['n'] else float('nan')


def main():
    root = Path(sys.argv[1]) / 'artifacts' / 'stiffness'
    rows = []
    for s in range(1, 7):
        r = {}
        for arm in 'AB':
            res = json.loads((root / ('%s%d' % (arm, s)) / 'SKILLS-RESULT.json').read_text())
            curve = {c['update']: pct(c['in_dist']) for c in res['in_dist_curve']}
            r[arm] = {'start': curve.get(0), 'final': pct(res['final_dev']['in_dist']), 'curve': curve,
                      'n': res['final_dev']['in_dist']['n'], 'updates': res['updates_done']}
        r['seed'], r['D'] = s, r['A']['final'] - r['B']['final']
        rows.append(r)
    mean_d = sum(r['D'] for r in rows) / 6
    behind = sum(r['D'] < 0 for r in rows)
    mean_a = sum(r['A']['final'] for r in rows) / 6
    mean_b = sum(r['B']['final'] for r in rows) / 6
    if mean_a < 10 and mean_b < 10:
        verdict = 'VOID (both arms under 10%: the new skills were not learnable in 4000 updates)'
    elif mean_d <= -5 and behind >= 5:
        verdict = 'STIFF'
    elif mean_d >= 0:
        verdict = 'NOT STIFF'
    else:
        verdict = 'INCONCLUSIVE'
    print('| seed | A main2 start | A final | B parent start | B final | A-B |')
    print('|---|---|---|---|---|---|')
    for r in rows:
        print('| %d | %.1f | %.1f | %.1f | %.1f | %+.1f |' % (r['seed'], r['A']['start'] or 0, r['A']['final'],
                                                            r['B']['start'] or 0, r['B']['final'], r['D']))
    print('mean A %.1f, mean B %.1f, mean A-B %+.1f, A behind on %d of 6 seeds' % (mean_a, mean_b, mean_d, behind))
    print('VERDICT: ' + verdict)
    (root / 'STIFFNESS-SCORES.json').write_text(json.dumps({'rows': rows, 'mean_A': mean_a, 'mean_B': mean_b,
                                                            'mean_D': mean_d, 'A_behind': behind, 'verdict': verdict}, indent=1))


if __name__ == '__main__':
    main()
