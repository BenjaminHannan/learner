# CPU check for the swap / install scripts, run from src-b3g2: queue 8aFC2 parses (2 setup lines + one a64 and one a256 run per shape) and each run's
# config builds at about 100M trained. The models are built on torch's meta device (shapes only, no memory): the 16 GB-class PC is near
# its memory limit while G1 trains, and ten real 100M builds peaked at 3.8 GB (install_rr ran out of memory at the tenth, 9:20 PM ET 11 Oct).
import sys, json, torch
sys.path.insert(0, '.')
from custom_io.local_runner import parse_queue
from custom_io.g8a import caps as CP, configs as C
runs = parse_queue(sys.argv[1], work='W')
names = [r[0] for r in runs]
assert names[:2] == ['8a-data', '8aFC2-caps-3M-s400'] and len(runs) > 2, names
shapes = [n.split('-')[1] for n in names[2:]]
assert sorted(n for n in names[2:] if n.endswith('-a64')) == sorted('8aFC2-%s-a64' % x for x in set(shapes)) and len(runs) == 2 + 2 * len(set(shapes)), names
CP.apply(json.load(open('custom_io/g8a/caps_b3g2.json')))
for name, kind, args, mem in runs[2:]:
    assert kind == 'train' and args[args.index('--model') + 1] == 'b3g2', name
    cfg = json.loads(args[args.index('--cfg') + 1])
    with torch.device('meta'):
        t = C.b3_sizes(cfg, 'b3g2')['trained']
    assert 95e6 < t < 106e6, (name, t)
    print(name, '{:,}'.format(t))
print('FC2 CPU CHECK OK')
