import sys, json, time
sys.path.insert(0, '.')
from creative import fastsleep as fs, legal, c2_stones, rules_real as R
out = sys.argv[1]
N, vocab, meta, s = fs.load_setup(out)
pool = c2_stones._with_nums(R.load_split(fs.DATA, 'pool'))
rows = pool[:64]
r, fl, secs = fs.count_flops(lambda: legal.raw_samples(N, rows, vocab, 'cpu', n=32, temperature=s['T'], level=0, seed=7))
print('SAMPFLOPS', dict(T=s['T'], rows=len(rows), tflops=fl / 1e12, per_full_pool_tflops=fl / 1e12 * len(pool) / len(rows), secs=round(secs, 1)))
c = json.load(open(out + '/confirm.json')) if __import__('os').path.exists(out + '/confirm.json') else {}
print({k: v.get('sleep_tflops') for k, v in c.items() if isinstance(v, dict) and 'sleep_tflops' in v})
