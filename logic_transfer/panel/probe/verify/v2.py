import json,re,collections,math
SP='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows'
for f in ['logic_gate','logic_dev','logic_test_sampler','logic_test_deeper','placebo_dev','placebo_test_wording']:
    R=[json.loads(l) for l in open(f'{SP}/eval/{f}.jsonl')]
    h=0; cnt=collections.Counter()
    for r in R:
        neg=r['meta']['query'].startswith('~')
        g='false' if neg else 'true'
        h+= g==r['answer']; cnt[(neg,r['answer'])]+=1
    print(f,len(R),'polarity rule acc %.4f'%(h/len(R)), dict(cnt))
# train polarity independence (first 50k)
cnt=collections.Counter()
for i,l in enumerate(open(f'{SP}/logic_train.jsonl')):
    if i>=50000:break
    r=json.loads(l); cnt[(r['meta']['query'].startswith('~'),r['answer'])]+=1
print('train',dict(cnt))
