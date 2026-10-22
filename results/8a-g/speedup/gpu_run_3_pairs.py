#!/usr/bin/env python3
"""GPU-RUN-3 pair runs: applies the registered gate-3 rule (compare() of results/8a-g/pc-job-cards/g2fa4/g2fa4_supervisor.py, big-run's numbers) to two 300-update
loss traces and prints window means. A and B are events.jsonl files of the pair stage (lines with event == 'train', step, loss).
usage: python3 gpu_run_3_pairs.py A.jsonl B.jsonl [A.jsonl B.jsonl ...]   -> one block per pair (A minus B)"""
import json, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pc-job-cards' / 'g2fa4'))
import g2fa4_supervisor as S

RULES = dict(upto=300, last_n=50, diff_mean_pass=0.03, diff_mean_fail=0.06, last_n_pass=0.05, last_n_fail=0.10, report_from=101)


class Ev:
    def __init__(self, path):
        self.rows = {}
        self.nonfinite = False
        for ln in open(path, encoding='utf-8'):
            try:
                e = json.loads(ln)
            except ValueError:
                continue
            if e.get('event') == 'train':
                v = e['loss']
                if v is None or v != v or abs(v) == float('inf'):
                    self.nonfinite = True
                self.rows.setdefault(e['step'], v)

    def merged(self):
        return self.rows


def windows(ev):
    return [statistics.mean(ev.rows[s] for s in range(lo, lo + 50)) for lo in range(1, 301, 50)]


def pair(pa, pb):
    a, b = Ev(pa), Ev(pb)
    r = S.compare(a, b, RULES)
    wa, wb = windows(a), windows(b)
    L = [f'### {Path(pa).name} minus {Path(pb).name}', '',
         f'registered rule (diff of means over 300 updates within +/-0.03 and last-50 within 0.05 = PASS; beyond 0.06 / 0.10 or NaN = FAIL; between = UNCLEAR, read as GO): **{r["verdict"]}** ({r.get("read_as")})',
         f'difference of means (all 300): {r.get("diff_of_means"):+.4f}; last 50: {r.get("last_n_diff"):+.4f}; from update 101 on: {r.get("report_beside", {}).get("diff_of_means"):+.4f} (mean |diff| {r.get("report_beside", {}).get("mean_abs_diff"):.4f})' if 'diff_of_means' in r else f'{r}', '',
         '| updates | ' + ' | '.join(f'{lo}-{lo + 49}' for lo in range(1, 301, 50)) + ' |', '|---|' + '---|' * 6,
         '| A mean loss | ' + ' | '.join(f'{x:.3f}' for x in wa) + ' |', '| B mean loss | ' + ' | '.join(f'{x:.3f}' for x in wb) + ' |',
         '| A minus B | ' + ' | '.join(f'{x - y:+.3f}' for x, y in zip(wa, wb)) + ' |', '']
    return '\n'.join(L)


if __name__ == '__main__':
    args = sys.argv[1:]
    assert args and len(args) % 2 == 0, __doc__
    for i in range(0, len(args), 2):
        print(pair(args[i], args[i + 1]))
