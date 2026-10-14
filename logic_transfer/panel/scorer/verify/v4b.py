import json, glob, statistics as st
R='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt/logic_transfer/results/'
rows=[]
for p in glob.glob(R+'**/*.json',recursive=True):
    try: d=json.load(open(p))
    except Exception: continue
    s=(d.get('splits') or {}).get('logic_test_sampler') if isinstance(d,dict) else None
    if not s or 'by_depth_label' not in s: continue
    c=n=0
    for dep in ('2','3'):
        for lab,v in s['by_depth_label'].get(dep,{}).items(): c+=v['correct']; n+=v['n']
    aw=s['answer_words']['logic_fc']; tot=sum(sum(x.values()) for x in aw.values())
    pu=sum(aw[g].get('unknown',0) for g in aw)/tot; pt=sum(aw[g].get('true',0) for g in aw)/tot; pf=sum(aw[g].get('false',0) for g in aw)/tot
    rows.append((p.split('results/')[1],round(100*c/n,1),round(100*pu,1),round(100*pt,1),round(100*pf,1)))
print(len(rows))
rows=[r for r in rows if r[2]+r[3]+r[4]>90]   # exclude format-unaware (C/parent: <10% words)
y=[r[1] for r in rows]; x=[r[2] for r in rows]
print(len(rows),min(y),max(y))
mx,my=st.mean(x),st.mean(y)
print('corr',round(sum((a-mx)*(b-my) for a,b in zip(x,y))/(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))**.5,3))
for r in sorted(rows,key=lambda r:r[1])[:4]+sorted(rows,key=lambda r:r[1])[-4:]: print(r)
