import json,collections
SP='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows'
tr=collections.defaultdict(collections.Counter)
for i,l in enumerate(open(f'{SP}/logic_train.jsonl')):
    if i>=50000:break
    r=json.loads(l); tr[len(r['prompt'])//8][r['answer']]+=1
best={k:c.most_common(1)[0][0] for k,c in tr.items()}
for f in ['logic_gate','logic_dev','placebo_dev']:
    R=[json.loads(l) for l in open(f'{SP}/eval/{f}.jsonl')]
    print(f, sum(best.get(len(r['prompt'])//8)==r['answer'] for r in R)/len(R))
