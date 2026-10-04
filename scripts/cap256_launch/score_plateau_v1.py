"""Plateau diagnosis v1 (PLATEAU-DIAG-v1.md): pick the worst families from main2's full eval, then score the fit runs.

usage: score_plateau_v1.py pick PKG_ROOT            -> prints the 8 worst in_dist families (comma list)
       score_plateau_v1.py score PKG_ROOT           -> table + verdicts, writes PLATEAU-SCORES.json
Reads PKG_ROOT/artifacts/plateau/{eval,F1..F3,N1..N3}/SKILLS-RESULT.json. Marks were fixed before training.
"""
import json
import sys
from pathlib import Path


def load(root, name):
    return json.loads((Path(root) / 'artifacts' / 'plateau' / name / 'SKILLS-RESULT.json').read_text())


def pct(c, n):
    return 100.0 * c / n if n else float('nan')


def worst(root, k=8):
    fam = load(root, 'eval')['final_dev']['in_dist']['by_family']
    return sorted(fam, key=lambda f: (fam[f][0] / fam[f][1], f))[:k]


def main():
    cmd, root = sys.argv[1], sys.argv[2]
    if cmd == 'pick':
        print(','.join(worst(root)))
        return
    ev = load(root, 'eval')['final_dev']
    fam = ev['in_dist']['by_family']
    errors = {f: v[1] - v[0] for f, v in fam.items()}
    w = worst(root)
    tot_err = sum(errors.values())
    print('main2 in_dist over all %d rows: %.1f%%; family shift: %.1f%%' % (
        ev['in_dist']['n'], pct(ev['in_dist']['correct'], ev['in_dist']['n']), pct(ev['family']['correct'], ev['family']['n'])))
    print('| family | correct/n | % |')
    print('|---|---|---|')
    for f in sorted(fam, key=lambda f: fam[f][0] / fam[f][1]):
        print('| %s | %d/%d | %.0f |' % (f, fam[f][0], fam[f][1], pct(*fam[f])))
    share = 100.0 * sum(errors[f] for f in w) / tot_err if tot_err else 0
    print('worst 8 = %s; they hold %.0f%% of all in_dist errors (concentrated if >= 60)' % (','.join(w), share))
    start = pct(sum(fam[f][0] for f in w), sum(fam[f][1] for f in w))
    rows, out = [], {}
    for arm in 'FN':
        for s in (1, 2, 3):
            r = load(root, '%s%d' % (arm, s))
            d = r['final_dev']
            row = {'run': '%s%d' % (arm, s), 'heldout': pct(d['in_dist']['correct'], d['in_dist']['n']),
                   'trainfit': pct(d['trainfit']['correct'], d['trainfit']['n']) if 'trainfit' in d else None,
                   'curve': [{k: (pct(v['correct'], v['n']) if isinstance(v, dict) else v) for k, v in c.items()} for c in r['in_dist_curve']]}
            rows.append(row)
    mean = lambda arm, k: sum(r[k] for r in rows if r['run'][0] == arm) / 3
    fit_f, gain_f, gain_n = mean('F', 'trainfit'), mean('F', 'heldout') - start, mean('N', 'heldout') - start
    print('start (main2 on the worst-8 held-out rows): %.1f%%' % start)
    print('| run | held-out % | train-fit % |')
    print('|---|---|---|')
    for r in rows:
        print('| %s | %.1f | %s |' % (r['run'], r['heldout'], '%.1f' % r['trainfit'] if r['trainfit'] is not None else '-'))
    verdicts = []
    if fit_f < 85:
        verdicts.append('CAN-NOT-FIT (capacity or answer-only signal limit): fixed-set train fit %.1f < 85' % fit_f)
    if gain_n >= 15:
        verdicts.append('UNDER-TRAINED: fresh focused practice gains %+.1f >= 15 on held-out' % gain_n)
    if fit_f >= 85 and gain_n < 15 and gain_f < 10:
        verdicts.append('MEMORIZES: fits the fixed set (%.1f) but held-out gains stay small (fixed %+.1f, fresh %+.1f)' % (fit_f, gain_f, gain_n))
    if not verdicts:
        verdicts.append('MIXED: fit %.1f, fixed-set held-out gain %+.1f, fresh-rows gain %+.1f (no registered rule fired)' % (fit_f, gain_f, gain_n))
    for v in verdicts:
        print('VERDICT: ' + v)
    out = {'worst8': w, 'worst8_error_share': share, 'start': start, 'fit_F': fit_f, 'gain_F': gain_f, 'gain_N': gain_n,
           'rows': rows, 'by_family': fam, 'verdicts': verdicts}
    (Path(root) / 'artifacts' / 'plateau' / 'PLATEAU-SCORES.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
