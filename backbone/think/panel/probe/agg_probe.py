import json,sys,numpy as np
res=json.load(open(sys.argv[1])) if sys.argv[1].endswith('.json') else [json.loads(l.split(' ',2)[2]) for l in open(sys.argv[1]) if l[:1].isdigit()]
n=len(res); print('n',n)
def ms(k):
    v=np.array([r[k] for r in res]); return v.mean(), v.std(ddof=1)/np.sqrt(len(v))
A=np.array([r['A'] for r in res]); P=np.array([r['P'] for r in res])
print('A  %.3f'%A.mean(),' P %.3f'%P.mean(),' P-A %.3f +- %.3f'%((P-A).mean(),(P-A).std(ddof=1)/np.sqrt(n)))
for var in ['d2_bi','d2_ca','bslot']:
    row=[]
    for R in [1,2,4,8,12]:
        v=np.array([r[f'{var}_R{R}'] for r in res])-P
        row.append('R%d %+.3f(%.3f)'%(R,v.mean(),v.std(ddof=1)/np.sqrt(n)))
    print(var,'CE minus P:',' '.join(row))
    if f'{var}_delta' in res[0]:
        D=np.array([r[f'{var}_delta'] for r in res]); print('   delta/|Z0| laps1..12:',' '.join('%.3f'%x for x in D.mean(0)))
    print('   cos(Z12,Z0) %.3f'%np.mean([r[f'{var}_cos_z_z0'] for r in res]))
print('rms(h_b)/rms(h_a) at slots %.3f'%np.mean([r['rms_ratio_hb_over_ha'] for r in res]))
deep=[r for r in res if int(r['depth'])>=3]; sh=[r for r in res if int(r['depth'])<3]
for name,S in [('depth>=3',deep),('depth<3',sh)]:
    if S: print(name,len(S),'d2_bi R8-R1 %+.3f'%np.mean([r['d2_bi_R8']-r['d2_bi_R1'] for r in S]),' R12-P %+.3f'%np.mean([r['d2_bi_R12']-r['P'] for r in S]))
