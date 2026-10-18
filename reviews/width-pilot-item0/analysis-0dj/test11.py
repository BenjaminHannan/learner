"""TEST-11 numbers for the frozen heuristics. Operationalisation fixed before running:
 valid = heuristic answer == gold; invalid = heuristic defined and != gold (None/'?' counts as invalid if '?', excluded if undefined).
 validity effect = acc(valid)-acc(invalid), points; estimable only if n_valid>=20.
 depth strata = number of calculator calls in the tool's working: 3, 4, 5, 6+ (6 and 7 pooled). depth effect = max-min accuracy within invalid
 over strata with n>=20; pass < 10 points.
 invalid 1-step = shallowest HO stratum (3 calls: two one-call pieces + join). 'about chance' = accuracy <= 5% (exact-number answers: chance ~0).
"""
from lib import *
import frozen_heuristics as FH, math, json
def wilson(h,n,z=1.96):
    if n==0: return (None,None)
    p=h/n; d=1+z*z/n; c=p+z*z/(2*n); a=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))
    return (round(100*(c-a)/d,1), round(100*(c+a)/d,1))
def acc(rs): return (sum(r['hit'] for r in rs), len(rs))
def fmt(h,n): return f'{h}/{n}={100*h/n:.1f}%' if n else '0/0'
res={}
for L in ['L13','L14']:
    ho=[r for r in items(L) if r['cell']=='HO']
    for r in ho: r['depth']=len(r['tool_steps']); r['stratum']='6+' if r['depth']>=6 else str(r['depth'])
    print('=====',L,'HO',acc(ho))
    print(' accuracy by calls:', {s: fmt(*acc([r for r in ho if r['stratum']==s])) for s in ['3','4','5','6+']})
    for name in ['H1','H2','H3']:
        f=getattr(FH,name)
        for r in ho: r['h']=f(r['prompt'])
        und=[r for r in ho if r['h'] is None]
        # '?' results: sheet value '?' -> None; treat None as invalid (answer '?' can't equal gold) but report count
        valid=[r for r in ho if r['h'] is not None and str(r['h'])==r['gold']]
        inval=[r for r in ho if r not in valid]
        hv,nv=acc(valid); hi,ni=acc(inval)
        out={'undefined(None)':len(und),'valid':fmt(hv,nv),'invalid':fmt(hi,ni)}
        out['validity_effect_pts']=round(100*hv/nv-100*hi/ni,1) if nv else None
        out['valid_CI']=wilson(hv,nv)
        strata={s:acc([r for r in inval if r['stratum']==s]) for s in ['3','4','5','6+']}
        out['invalid_by_calls']={s:fmt(*v) for s,v in strata.items()}
        ok=[100*h/n for h,n in strata.values() if n>=20]
        out['depth_effect_pts(strata n>=20)']=round(max(ok)-min(ok),1) if len(ok)>1 else None
        h3,n3=strata['3']; out['invalid_3call']=fmt(h3,n3); out['invalid_3call_CI']=wilson(h3,n3)
        # capture: does the model's answer equal the heuristic's answer on invalid items?
        cap=sum(1 for r in inval if r['h'] is not None and str(r['h'])==r['pred'].strip())
        out['capture(invalid items where model answer==heuristic answer)']=fmt(cap,ni)
        out['capture_of_failures']=fmt(cap,len([r for r in ho if not r['hit']]))
        out['PASS']={'validity>=25': (out['validity_effect_pts'] is not None and nv>=20 and out['validity_effect_pts']>=25),
                     'depth<10': (out['depth_effect_pts(strata n>=20)'] is not None and out['depth_effect_pts(strata n>=20)']<10),
                     'invalid_shallow<=5%': (n3>=20 and 100*h3/n3<=5)}
        res[(L,name)]=out
        print('--',name); [print('   ',k,':',v) for k,v in out.items()]
