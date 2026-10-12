# CPU check for install_agent.ps1, run from the new src-at (B3AT commit 6e72a5fae5): queue 8aAT parses (data line, then the one AT job), and
# under the caps it trains with (caps_b3g2.json) arm AT at 3M builds at 4,023,302 trained, the count the queue header and AT-0 (viii) state.
import sys, json
sys.path.insert(0, '.')
from custom_io.local_runner import parse_queue
from custom_io.g8a import caps as CP, configs as C
r = parse_queue('custom_io/queue_local/8aAT-3M-s400-pc.txt', work='W')
assert len(r) == 2 and r[0][0] == '8a-data' and r[1][0] == '8aAT-3M-s400', [x[0] for x in r]
assert r[1][2][r[1][2].index('--arms') + 1] == 'AT', r[1][2]
CP.apply(json.load(open('custom_io/g8a/caps_b3g2.json')))
a = C.train_args('3M', 'AT', 400, 100, 'x', caps='custom_io/g8a/caps_b3g2.json', b2_extra={'eg_embed': True})
cfg = json.loads(a[a.index('--cfg') + 1])
assert a[a.index('--model') + 1] == 'b3at', a[:2]
n = C.b3_sizes(cfg, 'b3at')['trained']
print('AT 3M: model b3at, {:,} trained'.format(n))
assert n == 4_023_302, n
print('AT CPU CHECK OK')
