# CPU check for upgrade_post_g1_v3.ps1, run from src-b3g2: the four group 2 queues parse, and the PTS arm passes the size bands at 3M, 10M, 30M.
import sys
sys.path.insert(0, '.')
from custom_io.local_runner import parse_queue
from custom_io.g8a import configs as C
for q in ('8aG2C3S', '8aB3G2s400', '8aG2C10S', '8aC30S'):
    r = parse_queue('custom_io/queue_local/%s-pc.txt' % q, work='W')
    assert len(r) == 2 and r[0][0] == '8a-data', (q, r)
for rung in ('3M', '10M', '30M'):
    C.train_args(rung, 'PTS', 400, 100, 'x', caps='custom_io/g8a/caps_b3s.json', b2_extra={'eg_embed': True})
print('G2 CPU CHECK OK')
