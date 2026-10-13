# CPU check for install_at10m.ps1, run from src-at (B3AT commit 6e72a5fae5) with the queue file to check as the one argument.
# It needs no Gemma weights and no GPU (a model's parameter count is read from its layers, as atcheck.py does). It checks that queue 8aAT10M parses (data line, then the one
# AT job at 10M seed 400, --accum AT=64), that train_args('10M', 'AT', 400, ...) builds under caps_b3g2.json (g8a.configs.check_b3 asserts the 10M band of +-5%), and prints the trained
# parameter count of the agent model at 10M (shape S) next to the plain partner PTS at 10M (g2c10s; PTC, the calculator control, has the same count).
import sys, json
sys.path.insert(0, '.')
from custom_io.local_runner import parse_queue
from custom_io.g8a import caps as CP, configs as C
q = sys.argv[1]
r = parse_queue(q, work='W')
assert len(r) == 2 and r[0][0] == '8a-data' and r[1][0] == '8aAT10M-10M-s400', [x[0] for x in r]
j = r[1][2]
assert j[j.index('--arms') + 1] == 'AT' and j[j.index('--rung') + 1] == '10M' and j[j.index('--seed') + 1] == '400', j
assert j[j.index('--accum') + 1] == 'AT=64', j
assert json.loads(j[j.index('--b2-extra') + 1]) == {'eg_embed': True}, j
CP.apply(json.load(open('custom_io/g8a/caps_b3g2.json')))
bx = {'eg_embed': True}
n_loops = CP.n_loops_needed(json.load(open('custom_io/g8a/caps_b3g2.json')))
if n_loops > 8:          # job.py adds it the same way
    bx = dict(bx, n_loops=n_loops)
a = C.train_args('10M', 'AT', 400, 100, 'x', caps='custom_io/g8a/caps_b3g2.json', b2_extra=bx)
cfg = json.loads(a[a.index('--cfg') + 1])
assert a[a.index('--model') + 1] == 'b3at', a[:2]
n = C.b3_sizes(cfg, 'b3at')
tgt = C.RUNGS['10M']['target']
band = C.RUNGS['10M']['band']
assert abs(n['trained'] / tgt - 1) <= band, n
print('AT 10M shape S: model b3at, {} blocks x width {}, {} heads, mlp {}, n_loops {}, small plug'.format(cfg['blocks'], cfg['d'], cfg['n_heads'], cfg['mlp'], cfg['n_loops']))
print('AT 10M trained parameters: {:,} (frozen Gemma {:,} not counted; {:+.2f}% from the 10M target {:,.0f}, band +-{:.0f}%)'.format(n['trained'], n['frozen_gemma'], 100 * (n['trained'] / tgt - 1), tgt, 100 * band))
pc = C.pts_cfg('10M', bx)
pn = C.n(C.MODEL_OF[C.PTS_ARM], pc)
print('PTS 10M trained parameters (g2c10s; PTC equals it): {:,} ({} layers x width {}, hidden {}); AT is {:+.2f}% from it'.format(pn, pc['n_layers'], pc['d_model'], pc['hidden'], 100 * (n['trained'] / pn - 1)))
assert n['trained'] == 9_824_546, n['trained']
assert pn == 9_814_442, pn
print('AT10M CPU CHECK OK')
