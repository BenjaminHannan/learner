"""Tables for REPORT.md from p0_B2_s*.json (output of p0_probe.py). python analyze_p0.py p0_B2_s100.json [p0_B2_s101.json] > p0_tables.md"""
import json, re, sys
import numpy as np

SPEC = 'meaning fixed in PROBE-SPEC.md: pass@32 - greedy >= +10 signal; <= +2 cold start; else weak signal'


def verdict(d):
    return 'SIGNAL' if d >= 10 else ('COLD START' if d <= 2 else 'WEAK SIGNAL')


def fmt(x):
    return f'{x:.1f}'


for path in sys.argv[1:]:
    R = json.load(open(path))
    name = re.search(r'(B2_s\d+)', path).group(1)
    print(f'\n## {name}  (N={R["N"]}, temps={R["temps"]}, seed={R["seed"]}, torch {R["torch"]})\n')
    if 'greedy_full' in R:
        print('Greedy on the full splits (CPU fp32): ' + '; '.join(f'{k} {v["exact"]:.2f}% of {v["n"]} ({v["n_wrong"]} wrong rows probed)' for k, v in R['greedy_full'].items()) + '\n')
    for key, S in R['splits'].items():
        summ = S['summary']
        A = summ['ALL']
        print(f'### {key}  (n={A["n"]} rows; greedy modes {A["greedy_mode"]})\n')
        print('| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |')
        print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
        for T in R['temps']:
            s = A[str(T)]
            d = s['pass32'] - A['greedy_pass1']
            v = verdict(d) if key.startswith('heldout/prog') else ('(rescue rate; ' + verdict(d) + ' by the same lines)' if key.endswith('/prog') else 'exploratory')
            print(f'| {T} | {fmt(A["greedy_pass1"])} | {fmt(s["pass1"])} | {fmt(s["pass8"])} | {fmt(s["pass32"])} | {fmt(s["greedy_or_any"])} | {s["rows_with_hit"]} | {d:+.1f} | {v} | '
                  f'{s["distinct_answers"]["mean"]:.2f} / {s["distinct_answers"]["median"]:.0f} / {s["distinct_answers"]["max"]} | {s["distinct_programs"]["mean"]:.1f} | '
                  f'{fmt(s["answer_differs_from_greedy"])} | {fmt(s["program_differs_from_greedy"])} | {fmt(s["wellformed"])} | {fmt(s["any_op"])} |')
        fams = [f for f in summ if f != 'ALL']
        print(f'\nPer family (pass@32 at T = {", ".join(map(str, R["temps"]))}; greedy):\n')
        print('| family | n | greedy | ' + ' | '.join(f'pass@32 T={T}' for T in R['temps']) + ' | rows with hit (T=1.5) | distinct answers mean (T=1.0) |')
        print('|---|---|---|' + '---|' * (len(R['temps']) + 2))
        for f in fams:
            s = summ[f]
            print(f'| {f} | {s["n"]} | {fmt(s["greedy_pass1"])} | ' + ' | '.join(fmt(s[str(T)]['pass32']) for T in R['temps'])
                  + f' | {s[str(R["temps"][-1])]["rows_with_hit"]} | {s["1.0"]["distinct_answers"]["mean"]:.2f} |')
        # where the hits come from (sampled candidates that hit on rows greedy missed)
        recs = R['records'][key]
        rescued = []
        for r in recs:
            if r['greedy_hit']:
                continue
            for T in R['temps']:
                sm = r['samples'][str(T)]
                if any(sm['hits']):
                    rescued.append((r['family'], T, r['id'], r['answer'], r['greedy'], sum(sm['hits'])))
        rows_resc = sorted({(x[0], x[2], x[3], x[4]) for x in rescued})
        print(f'\nRows greedy misses that some sample hits (any T): {len(rows_resc)}')
        for f, i, a, g in rows_resc[:12]:
            hs = {T: next((x[5] for x in rescued if x[2] == i and x[1] == T), 0) for T in R['temps']}
            print(f'- {i} ({f}): answer {a!r}, greedy {g!r}, hits of 32 by T {hs}')
        if len(rows_resc) > 12:
            print(f'- ... {len(rows_resc) - 12} more')
        print()
print('\n' + SPEC)
