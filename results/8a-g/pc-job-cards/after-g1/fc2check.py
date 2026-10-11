# CPU check for swap_v3c.ps1, run from src-b3g2: queue 8aFC2 parses (2 setup lines + 8 runs) and each run's config builds at about 100M trained.
import sys, json
sys.path.insert(0, '.')
from custom_io.local_runner import parse_queue
from custom_io.g8a import caps as CP, configs as C
runs = parse_queue(sys.argv[1], work='W')
assert [r[0] for r in runs[:2]] == ['8a-data', '8aFC2-caps-3M-s400'] and len(runs) == 10, [r[0] for r in runs]
CP.apply(json.load(open('custom_io/g8a/caps_b3g2.json')))
for name, kind, args, mem in runs[2:]:
    assert kind == 'train' and args[args.index('--model') + 1] == 'b3g2', name
    cfg = json.loads(args[args.index('--cfg') + 1])
    t = C.b3_sizes(cfg, 'b3g2')['trained']
    assert 95e6 < t < 106e6, (name, t)
    print(name, '{:,}'.format(t))
print('FC2 CPU CHECK OK')
