"""T4: compare speed and first-100-update CE of the five runs written by PC-JOB-t4.md."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])


def prof(arm):
    for line in (root / ('t4-%s.stdout.txt' % arm)).read_text().splitlines():
        if line.startswith('{') and '"skills-profile"' in line:
            return json.loads(line)
    raise SystemExit('no skills-profile in %s' % arm)


def ces(arm):
    return [float(x) for x in json.loads((root / ('t4-%s' % arm) / 'ce-first-100.json').read_text())]


base_p, base_c = prof('O1'), ces('O1')
for arm in ('O1', 'O2', 'R', 'C', 'N'):
    p, c = prof(arm), ces(arm)
    saved = 100 * (1 - p['wall_loop_seconds'] / base_p['wall_loop_seconds'])
    dce = max(abs(a - b) for a, b in zip(c, base_c))
    print('%-3s loop %.1fs  saved vs O1 %5.1f%%  max|dCE| first %d = %.3g  parts %s  cache %s/%s' % (
        arm, p['wall_loop_seconds'], saved, len(c), dce, p['seconds_by_part'], p['feat_cache_hits'], p['feat_cache_misses']))
