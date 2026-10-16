# CPU check for upgrade_post_g1_v3.ps1 and install_rr.ps1, run from src-b3g2: the four group 2 queues parse, and the PTS arm passes the size bands at 3M,
# 10M, 30M. A c30s queue with --noplug (Ben, 4:12 PM ET 11 Oct: no plug at 30M) is checked with the no-plug front: this code must have job.py --noplug,
# and its 30M PTS must be 512 wide on Gemma's own numbers (eg_pre). Last, B3 group 2 at 3M (G2f) must build and pass its size check.
import sys, json
sys.path.insert(0, '.')
from custom_io.local_runner import parse_queue
from custom_io.g8a import configs as C
for q in ('8aG2C3S', '8aB3G2s400', '8aG2C10S', '8aC30S'):
    r = parse_queue('custom_io/queue_local/%s-pc.txt' % q, work='W')
    assert len(r) == 2 and r[0][0] == '8a-data', (q, r)
noplug = '--noplug' in parse_queue('custom_io/queue_local/8aC30S-pc.txt', work='W')[1][2]
if noplug:
    assert "'--noplug'" in open('custom_io/g8a/job.py').read(), 'c30s asks for --noplug but this job.py has no --noplug'
for rung in ('3M', '10M', '30M'):
    C.train_args(rung, 'PTS', 400, 100, 'x', caps='custom_io/g8a/caps_b3s.json', b2_extra={'eg_embed': True})
if noplug:          # under the caps the run applies (caps_b3s.json), so the printed shape is the one that trains
    from custom_io.g8a import caps as CP
    CP.apply(json.load(open('custom_io/g8a/caps_b3s.json')))
    a = C.train_args('30M', 'PTS', 400, 100, 'x', caps='custom_io/g8a/caps_b3s.json', b2_extra={'eg_embed': True, C.NOPLUG: True})
    cfg = json.loads(a[a.index('--cfg') + 1])
    assert cfg.get('eg_pre') and cfg['d_model'] == 512, cfg
    print('c30s no plug: PTS %d layers, hidden %d, width 512 on Gemma\'s own numbers, lr %s' % (cfg['n_layers'], cfg['hidden'], a[a.index('--lr') + 1]))
# B3 group 2 at 3M (8aB3G2s400, G2f) builds and passes its own size check under the caps it runs with (caps_b3g2.json)
from custom_io.g8a import caps as CP
CP.apply(json.load(open('custom_io/g8a/caps_b3g2.json')))
a = C.train_args('3M', 'B3G2', 400, 100, 'x', caps='custom_io/g8a/caps_b3g2.json', b2_extra={'eg_embed': True})
print('B3G2 3M: {:,} trained'.format(C.b3_sizes(json.loads(a[a.index('--cfg') + 1]), 'b3g2')['trained']))
print('G2 CPU CHECK OK')
