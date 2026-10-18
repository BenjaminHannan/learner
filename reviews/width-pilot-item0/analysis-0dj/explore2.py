from lib import *
def refs(s, grid):
    """list of (col,row) referenced in expression s, ranges expanded"""
    out=[]
    for m in re.finditer(r'([A-Z])(\d+)(?::([A-Z])(\d+))?', s):
        c,r=m.group(1),int(m.group(2))
        if m.group(3): out+= [(c,i) for i in range(r,int(m.group(4))+1)]
        else: out.append((c,r))
    return out
def main():
  pass
if __name__=="__main__":
 for L in ['L13','L14']:
    ho=[r for r in items(L) if r['cell']=='HO']
    c=collections.Counter(); ex=collections.defaultdict(list)
    for r in ho:
        if r['hit'] or r['first_diff_round'] is None: continue
        i=r['first_diff_round']; mc,ts=r['model_calls'],r['tool_steps']
        if i>=min(len(mc),len(ts)) or mc[i][0]!=ts[i][0]: continue
        g=grid(r['prompt']); f=formula(r['prompt']); op,K,J,st=split_formula(f)
        kr,jr=set(refs(K,g)),set(refs(J,g))
        prior=[x[3] for x in mc[:i]]
        t=ts[i]; m=mc[i]
        # compare as multisets of operand values (commutative ops) 
        tv=[t[1],t[2]]; mv=[m[1],m[2]]
        wrong=[v for v in mv if v not in tv] if sorted(mv)!=sorted(tv) else []
        if sorted(mv)==sorted(tv): c['same operands (non-comm order)']+=1; continue
        reg='K' if i<len(ts) and True else ''
        for v in wrong:
            cells=[(cc,rr+1) for cc,vals in g.items() for rr,x in enumerate(vals) if str(x)==v]
            if v in prior: cat='prior-result'
            elif any(x in kr for x in cells) and any(x in jr for x in cells): cat='cell in both pieces refs'
            elif any(x in jr for x in cells) and not any(x in kr for x in cells): cat='cell only in J refs'
            elif any(x in kr for x in cells): cat='cell only in K refs'
            elif cells: cat='unreferenced grid cell'
            elif v=='2' : cat='const 2'
            else: cat='other'
            c[cat]+=1; ex[cat].append((r['prompt'],i,m,t))
    print(L,dict(c))
    for k in ex: 
        for e in ex[k][:2]: print(k,e)
