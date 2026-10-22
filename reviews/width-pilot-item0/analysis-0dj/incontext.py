from lib import *
def ptype(p):
    m=re.match(r'(SUM|MAX|MIN|PRODUCT|ABS)\(',p)
    if m: return m.group(1)
    if '/' in p: return 'DIV'
    if '*2' in p: return 'CA'
    return 'cell'
for L in ['L13','L14']:
    its=items(L)
    print('=====',L)
    for cell in ['HO','HPO','HP','S','S5','F4-two']:
        rows=[r for r in its if r['cell']==cell]
        c=collections.Counter(); n=0
        by=collections.defaultdict(lambda:collections.Counter())
        for r in rows:
            f=formula(r['prompt']); sp=split_formula(f)
            if not sp: c['unsplit']+=1; continue
            op,K,J,st=sp; g=grid_of(r['prompt'])
            ks=sheet_tool.evaluate(f'{g} ; ={K}')['steps']; js=sheet_tool.evaluate(f'{g} ; ={J}')['steps']
            nK,nJ=len(ks),len(js); mc=r['model_calls']; ts=r['tool_steps']
            if len(ts)!=nK+nJ+1:  # pieces' steps + join; sometimes join reuses -> flag
                c['steps!=nK+nJ+1']+=1
            n+=1
            def seg(a,b): return len(mc)>=b and all(same_call(tuple(x),tuple(y)) for x,y in zip(mc[a:b],ts[a:b]))
            kok=seg(0,nK); jok=seg(nK,nK+nJ)
            # join call = rest: model calls beyond nK+nJ equals tool's remaining and same count
            jn=(len(mc)==len(ts)) and all(same_call(tuple(x),tuple(y)) for x,y in zip(mc[nK+nJ:],ts[nK+nJ:]))
            c['strict' if st else 'nonstrict']+=1
            c['K ok']+=kok; c['J ok']+=jok; c['K&J ok']+=kok and jok
            c['K&J ok & join call ok']+= kok and jok and jn
            c['K&J ok & join ok & answer right']+= kok and jok and jn and bool(r['hit'])
            c['all calls match']+= r['calls_match']; c['hit']+=r['hit']
            c['hit but calls differ']+= r['hit'] and not r['calls_match']
            kt,jt=ptype(K),ptype(J)
            by['K:'+kt][0]+=0
        both=c['K&J ok']
        print(f"{cell:7s} n={n}: Kok {c['K ok']/n*100:.1f}%  Jok {c['J ok']/n*100:.1f}%  both {both/n*100:.1f}% | join call ok | both {c['K&J ok & join call ok']}/{both} = {100*c['K&J ok & join call ok']/max(both,1):.1f}% | answer right | both {c['K&J ok & join ok & answer right']}/{both} | hit {c['hit']/n*100:.1f}%  allcalls {c['all calls match']/n*100:.1f}% hit-with-calls-differ {c['hit but calls differ']}  strict {c['strict']} nonstrict {c['nonstrict']} unsplit {c['unsplit']} misc {c['steps!=nK+nJ+1']}")
