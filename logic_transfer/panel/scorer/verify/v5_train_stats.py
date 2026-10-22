import json, collections, re
D='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/'
R=re.compile(r'\((\w+)/(\w+)/(\w+)\)$')
for f in ['logic_train','placebo_train']:
    lab=collections.Counter(); pos=collections.Counter(); dn=collections.Counter(); dep=collections.Counter(); nosuf=0; ev=set(); 
    for l in open(D+f+'.jsonl'):
        r=json.loads(l); lab[r['answer']]+=1
        m=R.search(r['prompt'])
        if m: pos[m.groups().index(r['answer'])]+=1
        else: nosuf+=1
        d=r['meta'].get('depth'); dep[(d,r['answer'])]+=1
    print(f,dict(lab),dict(pos),'nosuffix',nosuf)
    print(sorted(((str(k),v) for k,v in dep.items())))
