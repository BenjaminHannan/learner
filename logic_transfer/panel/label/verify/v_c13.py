import json,collections
R='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/'
def load(f): return [json.loads(l) for l in open(R+f+'.jsonl')]
S=load('eval/logic_test_sampler')
print('n',len(S),collections.Counter((r['level'],r['answer']) for r in S))
print('depth None count', sum(r['meta']['depth'] is None for r in S), 'raw level0', sum(r['level']==0 for r in S))
pool=[r for r in S if r['level'] in (2,3)]
print('pooled n',len(pool),collections.Counter(r['answer'] for r in pool))
neg=lambda r: r['meta']['query'].startswith('~')
print(collections.Counter((neg(r),r['answer']) for r in pool))
for rule in [lambda r:'false' if neg(r) else 'true']:
    print('polarity acc pooled',sum(rule(r)==r['answer'] for r in pool)/len(pool),'whole',sum(rule(r)==r['answer'] for r in S)/len(S))
# check the pre-registered mark text
import re
txt=open('/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt/logic_transfer/MARKS-LT1-2026-10-12.md').read()
for m in re.finditer(r'.*(rule-first|sampler).*',txt): print('MARK>',m.group(0)[:300])
# other files: polarity-only
for f in ['logic_gate','logic_dev','logic_test_deeper','placebo_dev','placebo_test_wording']:
    X=load('eval/'+f); print(f,'pol-only',round(sum(('false' if neg(r) else 'true')==r['answer'] for r in X)/len(X),3),collections.Counter((r['level'],r['answer']) for r in X).most_common(3))
# raw: confirm depth None for unknown rule-first
raw=load('raw/logic_test_sampler'); print('raw depth None by label',collections.Counter((r['label'],r['depth'] is None) for r in raw))
