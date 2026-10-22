# CPU check for install_agent.ps1, run from the new src-g2q (G2Q commit 4bdc31118a): queue 8aB3G2Q parses (data line, then the one job: arm B3G2
# with talk_question on), and under the caps it trains with (caps_b3g2.json) that arm builds at 3M at 4,023,558 trained (G2f's 4,023,302 + 256 q_type).
import sys, json
sys.path.insert(0, '.')
from custom_io.local_runner import parse_queue
from custom_io.g8a import caps as CP, configs as C
r = parse_queue('custom_io/queue_local/8aB3G2Q-pc.txt', work='W')
assert len(r) == 2 and r[0][0] == '8a-data' and r[1][0] == '8aB3G2Q-3M-s400', [x[0] for x in r]
args = r[1][2]
assert args[args.index('--arms') + 1] == 'B3G2', args
extra = json.loads(args[args.index('--b2-extra') + 1])
assert extra == {'eg_embed': True, 'talk_question': True}, extra
CP.apply(json.load(open('custom_io/g8a/caps_b3g2.json')))
a = C.train_args('3M', 'B3G2', 400, 100, 'x', caps='custom_io/g8a/caps_b3g2.json', b2_extra=extra)
assert a[a.index('--model') + 1] == 'b3g2', a[:2]
cfg = json.loads(a[a.index('--cfg') + 1])
assert cfg.get('talk_question') is True, cfg
n = C.b3_sizes(cfg, 'b3g2')['trained']
print('G2Q 3M: model b3g2, talk_question on, {:,} trained'.format(n))
assert n == 4_023_558, n
print('G2Q CPU CHECK OK')
