# Test C11: does sampler depth-2-3 pooled accuracy track the share of 'unknown' predictions across saved checkpoints?
import json, glob
rows=[]
for p in glob.glob('/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/**/score.json',recursive=True):
    try: d=json.load(open(p))
    except Exception: continue
    s=d.get('splits',{}).get('logic_test_sampler')
    if not s: continue
    bdl=s['by_depth_label']
    c=n=0
    for dep in ('2','3'):
        for lab,v in bdl.get(dep,{}).items(): c+=v['correct']; n+=v['n']
    aw=s['answer_words']['logic_fc']
    tot=sum(sum(x.values()) for x in aw.values())
    pred=lambda w: sum(aw[g].get(w,0) for g in aw)
    pu=pred('unknown')/tot; 
    # unknown-rows accuracy (level 0)
    unk=s['by_label'].get('unknown',{}); 
    rows.append((p.split('scratchpad/lt2/')[1],round(100*c/n,1),n,round(100*pu,1),round(100*s['correct']/s['n'],1),round(100*unk['correct']/unk['n'],1)))
rows.sort(key=lambda r:r[1])
print('n files',len(rows))
for r in rows[:6]+rows[-6:]: print(r)
import statistics as st
x=[r[3] for r in rows]; y=[r[1] for r in rows]
mx,my=st.mean(x),st.mean(y)
cor=sum((a-mx)*(b-my) for a,b in zip(x,y))/ (sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))**.5
print('corr(depth2-3 acc, % predicted unknown)=',round(cor,3),'range depth2-3',min(y),max(y),'range pred-unknown%',min(x),max(x))
# prediction: if never says unknown and random true/false -> 50 ; accuracy ~ (100-pu)/100*50ish
import numpy as np
print('fit slope',np.polyfit(x,y,1))
