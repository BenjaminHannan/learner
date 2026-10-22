"""Panel/target step 2b: does an option word inside the prompt BODY (before the ' (a/b/c)' suffix) carry label information?
Run: PYTHONPATH=<wt/lt> python s1b_bodyword_leak.py   Streams eval files fully and every 6th train row (<=20k)."""
import json, re, collections, os
ROWS = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows'
OUT = os.path.dirname(os.path.abspath(__file__))
SUF = re.compile(r' \((?:true|false|unknown)/(?:true|false|unknown)/(?:true|false|unknown)\)$')
W = re.compile(r"[a-z']+")
def body_words(p):
    return [w for w in W.findall(SUF.sub('', p).lower()) if w in ('true', 'false', 'unknown')]
def stream(path, stride=1, cap=None):
    n = 0
    for i, l in enumerate(open(path)):
        if i % stride: continue
        yield json.loads(l); n += 1
        if cap and n >= cap: return
files = {n: f'{ROWS}/eval/{n}.jsonl' for n in ['logic_gate','logic_dev','logic_test_sampler','logic_test_deeper','placebo_dev','placebo_test_wording']}
files['train_logic'] = f'{ROWS}/logic_train.jsonl'; files['train_placebo'] = f'{ROWS}/placebo_train.jsonl'
res = {}
for name, path in files.items():
    stride, cap = (6, 20000) if name.startswith('train') else (1, None)
    cls = collections.defaultdict(collections.Counter)   # class -> label counts
    for r in stream(path, stride, cap):
        bw = body_words(r['prompt'])
        s = set(bw)
        if not bw: k = 'none'
        elif s == {'true','false','unknown'}: k = 'frame(all3)'
        elif s == {'true'}: k = 'only-true'
        else: k = 'other:' + ','.join(sorted(s))
        cls[k][r['answer']] += 1
        cls['ALL'][r['answer']] += 1
    res[name] = {k: dict(v) for k, v in cls.items()}
    print(name)
    for k, v in sorted(cls.items()):
        n = sum(v.values()); print(f'   {k:28s} n={n:6d}  ' + '  '.join(f'{a}={v[a]/n*100:5.1f}%' for a in ('true','false','unknown')))
json.dump(res, open(os.path.join(OUT, 's1b_result.json'), 'w'), indent=1)
