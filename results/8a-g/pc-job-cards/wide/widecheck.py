# CPU check for install_wide.ps1, run from the new src-wide: queue 8aWIDE parses, and under G1's pinned caps (caps_g.json) the rung 10MW B2
# builds at 10,173,509 trained (448 wide, 2 blocks), inside its band. Models are built on torch's meta device (shapes only, no memory: G1 trains).
import sys, json, torch
sys.path.insert(0, '.')
from custom_io.local_runner import parse_queue
from custom_io.g8a import caps as CP, configs as C
r = parse_queue('custom_io/queue_local/8aWIDE-pc.txt', work='W')
assert len(r) == 2 and r[0][0] == '8a-data' and r[1][0] == '8aWIDE-10MW-s400', [x[0] for x in r]
caps = json.load(open('custom_io/g8a/caps_g.json'))
CP.apply(caps)
extra = dict(eg_embed=True, n_loops=CP.n_loops_needed(caps))
with torch.device('meta'):
    cfgs, counts = C.sizes('10MW', extra)
C.check_bands('10MW', cfgs, counts, exact_3m=False)
assert counts['B2'] == 10_173_509 and cfgs['B2']['d'] == 448 and cfgs['B2']['blocks'] == 2 and cfgs['B2']['n_loops'] == 12, (cfgs['B2'], counts['B2'])
print('10MW B2: %s, %s trained, lr %.3g' % (json.dumps(cfgs['B2'], sort_keys=True), '{:,}'.format(counts['B2']), C.RUNGS['10MW']['lr']))
print('WIDE CPU CHECK OK')
