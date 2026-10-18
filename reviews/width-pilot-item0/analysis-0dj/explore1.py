from lib import *
import itertools
def ev(prompt):
    return sheet_tool.evaluate(prompt)
def feats(r):
    f=formula(r['prompt']); op,K,J,st=split_formula(f)
    g=grid_of(r['prompt'])
    kp,jp=f'{g} ; ={K}',f'{g} ; ={J}'
    kv,jv=ev(kp),ev(jp)
    return K,J,kv,jv
for L in ['L13','L14']:
    ho=[r for r in items(L) if r['cell']=='HO']
    c=collections.Counter(); n=0
    for r in ho:
        K,J,kv,jv=feats(r)
        k,j=kv['value'],jv['value']
        k,j=int(k),int(j)
        p=r['pred'].strip()
        cands={'K':k,'J':j,'K+J':k+j,'|K-J|':abs(k-j),'K-J':k-j,'J-K':j-k,
               'first call result':int(r['tool_steps'][0][3]) if r['tool_steps'][0][3].isdigit() else None,
               'gold':int(r['gold'])}
        for name,v in cands.items():
            if str(v)==p: c[name]+=1
        if not r['hit']:
            n+=1
            for name,v in cands.items():
                if str(v)==p and name!='gold': c['FAIL:'+name]+=1
    print(L,n,dict(c))
