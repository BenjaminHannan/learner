import json,sys,pathlib
S=pathlib.Path(sys.argv[1]);O={}
G=1024**3
for arm in('on','off'):
 for seed in(1,2):
  d=S/f'{arm}-s{seed}';r=json.load(open(d/'HF-report.json'));w=json.load(open(d/'watch.json'))
  cps=r['checkpoints'];assert not r['partial'] and len(cps)==4 and r['seed']==seed and w['exit_code']==0
  facts=[]
  for i in range(6):
   b=i//3;lrn=cps[b+1]['held'][i]['hit'];kept=lrn and cps[3]['held'][i]['hit']
   facts.append({'a':cps[0]['held'][i]['a'],'block':b+1,'learned':bool(lrn),'kept':bool(kept),'out_after_own_block':cps[b+1]['held'][i]['out'].strip()[:40],'out_final':cps[3]['held'][i]['out'].strip()[:40]})
  rd=w['readings']
  O[f'{arm}-{seed}']={'arm':arm,'seed':seed,'facts':facts,'learned':sum(f['learned'] for f in facts),'kept':sum(f['kept'] for f in facts),
   'general_hits':[c['general_hits'] for c in cps],'held_hits_all9':[c['held_hits'] for c in cps],
   'harm':cps[3]['general_hits']<cps[0]['general_hits']-2,'wall_s':round(w['wall_s'],1),
   'first_step_s':[round(p['first_step_s'],2) for p in r['phases']],
   'min_avail_gib':round(min(x['available_bytes'] for x in rd)/G,2),'max_rss_gib':round(max(x.get('process_rss_bytes',0) for x in rd)/G,2),
   'min_disk_free_gib':round(min(x['disk_free_bytes'] for x in rd)/G,2),'max_pressure':max(x['pressure_level'] for x in rd)}
  json.dump(r,open(d.name+'-HF-report.json','w'),indent=1) if False else None
T=lambda a,k:sum(O[f'{a}-{s}'][k] for s in(1,2))
on_l,on_k,off_l,off_k=T('on','learned'),T('on','kept'),T('off','learned'),T('off','kept')
harm=any(v['harm'] for v in O.values())
if on_l<4 or off_l<4:v='TOO_FEW'
elif off_k>=on_k:v='FAIL'
elif (off_k==0 and on_k>=2) or (off_k>0 and on_k>=2*off_k):v='PASS'
else:v='INCONCLUSIVE'
res={'experiment':'sequential-retention-rehearsal-wave2','verdict':v,'harm_any_run':harm,'seeds12':{'on_learned':on_l,'on_kept':on_k,'off_learned':off_l,'off_kept':off_k},
 'three_seed_incl_wave1':{'on_learned':on_l+3,'on_kept':on_k+3,'off_learned':off_l+3,'off_kept':off_k+0},'runs':O}
json.dump(res,open('results.json','w'),indent=1);print(json.dumps({k:v for k,v in res.items() if k!='runs'}))
for k,x in O.items():print(k,x['learned'],x['kept'],x['general_hits'],x['held_hits_all9'],x['wall_s'],x['min_avail_gib'],x['max_rss_gib'],x['min_disk_free_gib'],x['max_pressure'],x['first_step_s']);[print('  ',f['block'],f['a'],f['learned'],f['kept'],'|',f['out_after_own_block'],'|',f['out_final']) for f in x['facts']]
