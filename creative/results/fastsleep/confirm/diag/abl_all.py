"""Post-hoc diagnosis on every confirm parent: memory+old with the answer note off (W gain, skills harm). Labelled post hoc; verdict unchanged."""
import sys, json
from creative import fastsleep as fs, sleep, c2_stones, rules_real as R
replay = sleep.load_replay('/root/work/data/train.jsonl', None, 0)
dev = c2_stones._with_nums(R.load_split(fs.DATA, 'dev'))
for S in sys.argv[1:]:
    out = f'/mnt/project-files/fast-sleep/confirm/{S}'
    N, vocab, meta, s = fs.load_setup(out)
    c = json.load(open(f'{out}/confirm.json'))
    recs = s['records']['W']
    m, info = fs.m_knn(N, recs, replay, vocab, 'cpu', len(recs), **fs.MEMORY_OLD[1])
    m._mem.theta_ans = 9.0
    d, _ = fs.dev_eval(m, dev, vocab, 'cpu')
    r = dict(parent=S, gain=100 * (d['right'] - c['N']['dev']['right']), harm=100 * (c['N']['skills5'] - fs.skills5(m, '/root/work/data_big', 'cpu')))
    print('ABL', json.dumps(r), flush=True)
