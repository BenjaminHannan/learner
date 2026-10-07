"""Read-only ablation on s205: is the answer note the cause of the harm? (diagnosis, not a retune; the confirm verdict stands)"""
from creative import fastsleep as fs, sleep, c2_stones, rules_real as R
out = '/mnt/project-files/fast-sleep/confirm/s205'
N, vocab, meta, s = fs.load_setup(out)
replay = sleep.load_replay('/root/work/data/train.jsonl', None, 0)
recs = s['records']['W']
dev = c2_stones._with_nums(R.load_split(fs.DATA, 'dev'))
base5 = fs.skills5(N, '/root/work/data_big', 'cpu'); dN, _ = fs.dev_eval(N, dev, vocab, 'cpu')
m, info = fs.m_knn(N, recs, replay, vocab, 'cpu', len(recs), **fs.MEMORY_OLD[1])
for name, th in (('as run', None), ('answer note off', 9.0)):
    if th: m._mem.theta_ans = th
    d, _ = fs.dev_eval(m, dev, vocab, 'cpu')
    print(name, 'gain', round(100 * (d['right'] - dN['right']), 1), 'harm', round(100 * (base5 - fs.skills5(m, '/root/work/data_big', 'cpu')), 1), d['by_kind'])
