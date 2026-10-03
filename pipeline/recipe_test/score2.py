import json,glob,statistics as st,math,sys
d='results2'
runs={}
for f in glob.glob(d+'/*-seed*.json'):
    if f.endswith('-rows.json') or f.endswith('-fitrows.json'): continue
    x=json.load(open(f)); runs[(x['name'].rsplit('-seed',1)[0].replace('-mix',''),x['seed'])]=x
arms=sorted({k[0] for k in runs}); seeds=sorted({k[1] for k in runs}); print(arms,seeds)
g=lambda a,s,c,k:runs[(a,s)]['eval'][c][k][0]*100
for name,fn in [('train fit final',lambda a,s:runs[(a,s)]['train_fit_192']['final_ok']*100),
 ('unseen final',lambda a,s:g(a,s,'unseen','final_ok')),('seen final',lambda a,s:g(a,s,'seen','final_ok')),('all final',lambda a,s:g(a,s,'all','final_ok')),
 ('new-wording call',lambda a,s:g(a,s,'new_wording','call_ok')),('train-wording call',lambda a,s:g(a,s,'train_wording','call_ok')),('new-wording final',lambda a,s:g(a,s,'new_wording','final_ok'))]:
    print(name)
    for a in arms:
        v=[fn(a,s) for s in seeds if (a,s) in runs]
        print(f"  {a:10s} mean {st.mean(v):6.1f} sd {st.stdev(v) if len(v)>1 else 0:5.1f} "+" ".join(f"{x:5.1f}" for x in v))
sh=[s for s in seeds if all((a,s) in runs for a in arms)]
if len(arms)==2 and len(sh)>1:
    a,b=arms[1],arms[0]  # copy-ctx minus copy
    for c,k in (('new_wording','call_ok'),('unseen','final_ok'),('train_wording','call_ok'),('new_wording','final_ok'),('all','final_ok')):
        dd=[g(a,s,c,k)-g(b,s,c,k) for s in sh]; m=st.mean(dd); t={1:99,2:4.303,3:3.182,4:2.776,5:2.571,6:2.571}[len(dd)] if len(dd)<=6 else 2.5
        h=t*st.stdev(dd)/math.sqrt(len(dd)); print(f"{a}-{b} {c}/{k}: {m:+.1f} CI {m-h:+.1f}..{m+h:+.1f} "+" ".join(f"{x:+.1f}" for x in dd))
# ADD/SUB split on new wording
import gen
for a in arms:
    t={}
    for s in seeds:
        fn=[n for n in glob.glob(d+"/*seed%d-rows.json"%s) if "fit" not in n and (("ctx" in n)==("ctx" in a))][0]
        for r in json.load(open(fn)):
            k=(r['cell'].split('/')[1],r['op']); t.setdefault(k,[0,0]); t[k][0]+=r['call_ok']; t[k][1]+=1
    print(a,{f"{k[0][:5]}/{k[1]}":round(v[0]/v[1]*100) for k,v in sorted(t.items())})
