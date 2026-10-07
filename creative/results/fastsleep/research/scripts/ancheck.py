"""Answer-note test (marks: /mnt/project-files/fast-sleep/ANSWER-NOTE-MARKS.md). Per parent: DEV gain of M (ans 0) and M2 (ans 2) over N on W;
harm of both on data_big/dev/frame.jsonl (whole slice and its chain-5 rows). -> DIR/ancheck.json"""
import sys, os, json
from creative import fastsleep as fs, sleep, c2_stones, rules_real as R
from custom_io.data import load_rows
from custom_io.evalx import CHAIN5, evaluate
replay = sleep.load_replay('/root/work/data/train.jsonl', None, 0)
dev = c2_stones._with_nums(R.load_split(fs.DATA, 'dev'))
rows = load_rows('/root/work/data_big/dev/frame.jsonl')
for out in sys.argv[1:]:
    path = os.path.join(out, 'ancheck.json')
    if os.path.exists(path):
        continue
    N, vocab, meta, s = fs.load_setup(out)
    W = s['records']['W']
    dN, _ = fs.dev_eval(N, dev, vocab, 'cpu')
    eN = evaluate(N, rows, 256, 'cpu')
    def ch5(e):
        c = sum(e['by_family'][f]['correct'] for f in CHAIN5 if f in e['by_family']); n = sum(e['by_family'][f]['n'] for f in CHAIN5 if f in e['by_family'])
        return 100 * c / n
    res = dict(parent=os.path.basename(out), N=dict(dev_right=dN['right'], frame=eN['exact'], frame_chain5=ch5(eN)))
    for name, ans in (('M', 0), ('M2', 2)):
        m, info = fs.m_knn(N, W, replay, vocab, 'cpu', len(W), c=50.0, theta=0.9, cal=0.99, old=512, ans=ans)
        d, _ = fs.dev_eval(m, dev, vocab, 'cpu')
        e = evaluate(m, rows, 256, 'cpu')
        res[name] = dict(dev_gain=100 * (d['right'] - dN['right']), by_kind=d['by_kind'], frame_harm=eN['exact'] - e['exact'],
                         frame_chain5_harm=ch5(eN) - ch5(e), fired=m._mem.fired, info=info)
    json.dump(res, open(path, 'w'), indent=1)
    print('ANCHECK', res['parent'], json.dumps({k: {kk: round(vv, 2) for kk, vv in res[k].items() if kk in ('dev_gain', 'frame_harm', 'frame_chain5_harm')} for k in ('M', 'M2')}), flush=True)
