#!/usr/bin/env python3
"""Tables for GPU-RUN-3: reads the b3g2_abbench.json of each box dir given on the command line and prints markdown.
Money = wall time x the billed rate (default $0.4563/h), not the harness's own dollar lines (they used the DPH given at creation).
Regime rule (PREREG Amendment 5): reference = fastest A round on the same box over all arms; a round is normal speed if its A median <= 1.10 x reference;
an arm needs 3 normal-speed rounds to be decided (variants only; accum rows are listed as measured).
usage: python3 gpu_run_3_tables.py [--rate 0.4563] box_dir [box_dir ...]"""
import argparse, json, statistics
from pathlib import Path


def med(xs):
    return statistics.median(xs) if xs else float('nan')


def load(d):
    return json.loads((Path(d) / 'b3g2_abbench.json').read_text())['sections']['abbench']


def money(s, rate):
    return dict(upd_h=3600 / s, usd_1000=1000 * s / 3600 * rate, h_24000=24000 * s / 3600, usd_24000=24000 * s / 3600 * rate)


def table(d, rate):
    ab = load(d)
    arms = ab['arms']
    ran = {k: v for k, v in arms.items() if v.get('rounds_completed')}
    ref = min(r['round_median'] for v in ran.values() for r in v['a_runs'])
    out = [f'### {Path(d).name}: reference (fastest A round on this box, all arms) = {ref:.3f} s/update; normal speed = A round <= {1.10 * ref:.3f}', '']
    out += ['| arm | A rounds (s/update) | B rounds (s/update) | normal-speed rounds | A median (normal rounds) | B median (normal rounds) | B lower than A (normal rounds) | B lower than A (all rounds, any speed) | B < A in every normal round | peak alloc GB | decided? |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for name, v in ran.items():
        A = [r['round_median'] for r in v['a_runs']]
        B = [r['round_median'] for r in v['b_runs']]
        norm = [i for i, a in enumerate(A) if a <= 1.10 * ref and i < len(B)]
        if v['kind'] == 'variant':
            am, bm = med([A[i] for i in norm]), med([B[i] for i in norm])
            every = all(B[i] < A[i] for i in norm) if norm else False
            low = f'{(1 - bm / am) * 100:+.1f} %' if norm else '-'
            dec = 'yes' if len(norm) == 3 else f'**no: regime-confounded ({len(norm)} of {len(A)} rounds normal)**'
            out.append(f'| {name} | {", ".join(f"{a:.3f}" for a in A)} | {", ".join(f"{b:.3f}" for b in B)} | {len(norm)} | {am:.3f} | {bm:.3f} | {low} | {v["marks"]["b_lower_than_a_by"] * 100:+.1f} % | {every} | {v["peak_alloc_gb"]:.2f} | {dec} |')
        else:
            out.append(f'| {name} (accum row) | {", ".join(f"{a:.3f}" for a in A)} | {", ".join(f"{b:.3f}" for b in B)} | {len(norm)} | {med(A):.3f} | {med(B):.3f} | {(1 - med(B) / med(A)) * 100:+.1f} % | {v["marks"]["b_lower_than_a_by"] * 100:+.1f} % | {all(b < a for a, b in zip(A, B))} | {v["peak_alloc_gb"]:.2f} | accum row, as measured |')
    out += ['', f'money at the billed ${rate}/h (24,000-update run = 24,000 x s/update / 3600 x rate); variant rows use the normal-speed rounds only (or say they had none); accum rows and A rows are the arm\'s own medians', '',
            '| arm | s/update | updates/hour | USD per 1,000 updates | hours per 24,000 | USD per 24,000-update run | wall min (A+B) | arm cost USD (wall x rate) |', '|---|---|---|---|---|---|---|---|']
    seen_ref = set()
    for name, v in arms.items():
        if not v.get('rounds_completed'):
            out.append(f'| {name} | not measured ({v.get("skipped", "no rounds")}) | | | | | 0 | 0 |')
            continue
        bm = v['marks']['b_median']
        am = v['marks']['a_median']
        tag = ''
        if v['kind'] == 'variant':
            A = [r['round_median'] for r in v['a_runs']]
            B = [r['round_median'] for r in v['b_runs']]
            norm = [i for i, a in enumerate(A) if a <= 1.10 * ref and i < len(B)]
            if norm:
                bm, am, tag = med([B[i] for i in norm]), med([A[i] for i in norm]), f' (normal-speed rounds only: {len(norm)} of {len(A)})'
            else:
                tag = ' (all rounds were in the slow stretch: NOT normal speed)'
        m = money(bm, rate)
        wall = v['wall_min_arm']
        out.append(f'| {name} B{tag} | {bm:.3f} | {m["upd_h"]:.0f} | {m["usd_1000"]:.3f} | {m["h_24000"]:.2f} | {m["usd_24000"]:.2f} | {wall:.1f} | {wall / 60 * rate:.3f} |')
        ma = money(am, rate)
        out.append(f'| {name} A (the accum-4 reference run of this arm) | {am:.3f} | {ma["upd_h"]:.0f} | {ma["usd_1000"]:.3f} | {ma["h_24000"]:.2f} | {ma["usd_24000"]:.2f} | | |')
    tot = sum(v.get('wall_min_arm', 0) for v in arms.values())
    out += ['', f'bench wall time {tot:.1f} min; at ${rate}/h = ${tot / 60 * rate:.2f} (the bench only; the box also ran the other stages)', '']
    return '\n'.join(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--rate', type=float, default=0.4563)
    ap.add_argument('dirs', nargs='+')
    a = ap.parse_args()
    for d in a.dirs:
        print(table(d, a.rate))
