import json,re,collections,sys
sys.path.insert(0,'.')
from domain.far import join_gap as JG
CA=re.compile(r'([AB]\d)([+\-])([AB]\d)\*(\d+)')
def grid(p):
    g={}
    for part in p.split(';')[0].split('|'):
        lab,vals=part.split(':'); 
        for i,v in enumerate(vals.split()): g[f'{lab.strip()}{i+1}']=v
    return g
for name in sys.argv[1:]:
    it=[json.loads(l) for l in open(f'out/items-{name}.jsonl')]
    print(name)
    for cells in (['F0-near'],['S','HP','fit','S5','F4-two'],['HO','HPO']):
        c=collections.Counter(); n=0
        for x in it:
            if x['cell'] not in cells: continue
            f=x['prompt'].split('=',1)[1]; m=CA.search(f)
            if not m: continue
            g=grid(x['prompt']); c1,sg,c2,N=m.groups(); v1,v2=g[c1],g[c2]
            # first tool call that belongs to the CA piece
            tool=x['tool_steps']; mc=x['model_calls']
            k=[i for i,s in enumerate(tool) if s[0]=='mul' and {s[1],s[2]}=={v2,N}]
            if not k: c['(no CA mul in tool?)']+=1; continue
            k=k[0]
            if len(mc)<=k: c['stopped before CA call']+=1; n+=1; continue
            # only score the CA call when the prefix before it was right
            if any(not JG.same_call(tuple(mc[i]),tuple(tool[i])) for i in range(k)): continue
            n+=1
            op,a,b=mc[k][0],mc[k][1],mc[k][2]
            if JG.same_call(tuple(mc[k]),tuple(tool[k])): c['RIGHT']+=1; continue
            ops={a,b}
            if op=='mul' and N in ops:
                other=(ops-{N}) or {N}; o=other.pop()
                c['mul ?*N: other operand = '+('c1 (the + cell)' if o==v1 else 'another grid cell' if o in g.values() else 'not in grid')]+=1
            elif op=='mul' and ops=={v1,v2}: c['mul c1*c2 (precedence: multiplies the two cells)']+=1
            elif op=='add' or op=='sub':
                c[f'{op} first (left-to-right: '+('c1,c2' if ops=={v1,v2} else 'other')+')']+=1
            else: c[f'other: {op}']+=1
        print('  ',cells,'CA call reached with right prefix n=',n)
        for k,v in c.most_common(): print(f'      {v:4d} {100*v/max(n,1):5.1f}%  {k}')
