import json
seeds=[13,14,15,16]
D={s:json.load(open(f'slp358n3-seed{s}.json')) for s in seeds}
for s in seeds:
    d=D[s]; print(s,list(d.keys()),d['sizes'],d['torch'],d['gpu'],d['minutes'],d['excluded_day_items'],d['cfg']['night_steps'],d['cfg']['night_lr'],d['cfg']['batch'],d['ckpt_sha256'][:12])
    print('  arms in morning[3]:',list(d['morning']['3'].keys()))
def cls(a,b):
    if a>=360 and b>=360: return 'ceil'
    if a<=40 and b<=40: return 'floor'
    return 'info'
def markpair(arm2,label):
    print('==',label)
    for k in ['day_sums','day_grids']:
        ds=[];inf=[];rows=[]
        for s in seeds:
            m=D[s]['morning']['3']
            a=m['S'][k]['right']; b=m[arm2][k]['right']
            c=cls(a,b); dd=a-b
            rows.append((s,a,b,dd,c)); ds.append(dd)
            if c=='info': inf.append((s,dd))
        mean=sum(ds)/4
        npass=sum(1 for s,dd in inf if dd>=20)
        print(k,rows,'mean all',mean,'informative',len(inf),'pass>=20:',npass, 'mean informative',(sum(dd for s,dd in inf)/len(inf) if inf else None))
markpair('R','M1 S-R'); markpair('Z','M2 S-Z')
print('== M3')
for t in ['harm_sums4','harm_grids5']:
    for s in seeds:
        m=D[s]['morning']['3']; n=m['N'][t]['right']; S=m['S'][t]['right']
        print(t,s,'S',S,'N',n,'need>=',n-6,'ok',S>=n-6)
print('== M3b')
for s in seeds:
    for n in ['1','2','3']:
        print(s,n,D[s]['lost'][n]['S'])
print('== M3 all nights S (info)')
for s in seeds:
    for n in ['1','2','3']:
        m=D[s]['morning'][n]['S']; print(s,n,m['harm_sums4']['right'],m['harm_grids5']['right'])
print('== S-R at nights 1,2 (report)')
for n in ['1','2','3']:
  for s in seeds:
    m=D[s]['morning'][n]; print(n,s,[ (k,m['S'][k]['right']-m['R'][k]['right']) for k in ['day_sums','day_grids']])
print('== proved wrong: S-R<=5 both kinds')
for s in seeds:
    m=D[s]['morning']['3']; print(s,[(k,m['S'][k]['right']-m['R'][k]['right'],m['S'][k]['right'],m['R'][k]['right']) for k in ['day_sums','day_grids']])
print('== L (13,14)')
for s in [13,14]:
    m=D[s]['morning']['3']
    print(s,{t:(m['L'][t]['right'],m['S'][t]['right'],m['N'][t]['right']) for t in m['L']})
    print(' lost L',[D[s]['lost'][n]['L'] for n in '123'])
print('== day tries', [ (s,list(D[s]['day'].keys())) for s in seeds])
for s in seeds: print(s, D[s]['morning']['base']['day_sums']['right'], D[s]['morning']['base']['day_grids']['right'])
print('== Z/R vs N harm')
for s in seeds:
    m=D[s]['morning']['3']
    print(s,{a:(m[a]['harm_sums4']['right'],m[a]['harm_grids5']['right']) for a in ['S','R','Z','N']}, [D[s]['lost'][n]['Z'] for n in '123'],[D[s]['lost'][n]['R'] for n in '123'])
