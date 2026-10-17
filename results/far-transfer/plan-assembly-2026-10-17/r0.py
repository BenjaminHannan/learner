import json,sys,collections,re
sys.path.insert(0,'.'); sys.path.insert(0,'out')
from strata import ncells,kj
from domain.far import join_gap as JG
for path in sys.argv[1:]:
    items=[json.loads(l) for l in open(path) if json.loads(l)['cell']=='HO']
    print(path)
    tab=collections.defaultdict(lambda:[0,0]); ex=collections.defaultdict(list)
    for it in items:
        n,c=len(it['tool_steps']),ncells(it['prompt'])
        K,J,nK,nJ=kj(it['prompt'])
        dz=(n,c)==(4,4)
        kshape=re.sub(r'[AB]\d','c',K); kshape=re.sub(r'\b\d+\b','N',kshape)
        ok0 = bool(it['model_calls']) and JG.same_call(tuple(it['model_calls'][0]),tuple(it['tool_steps'][0]))
        key=('DZ' if dz else f'{n}st', kshape)
        tab[key][0]+=ok0; tab[key][1]+=1
        if dz and not ok0 and len(ex[kshape])<3: ex[kshape].append((it['prompt'],it['tool_steps'][0],it['model_calls'][:2]))
    for k in sorted(tab): print('  %-5s %-18s R0 right %3d/%3d'%(k[0],k[1],*tab[k]))
    for k,v in ex.items():
        for e in v: print('   ex',k,'|',e[0].split(';')[1],'| tool',e[1],'| model',e[2])
