"""Read existing JSON only; no project imports, models, or experiments."""
import csv, hashlib, json, math, pathlib, statistics
R=pathlib.Path.cwd(); O=R/'reviews/astra-design-2026-09-19'
manifest={}; rows=[]; groups={}
def read(p):
 b=p.read_bytes();manifest[str(p.relative_to(R))]=hashlib.sha256(b).hexdigest();return json.loads(b)
def exact(b,c):
 n=b+c
 return min(1,2*sum(math.comb(n,i) for i in range(min(b,c)+1))/2**n) if n else 1
for wave in ('claude-keypool-20260919','claude-keypool-relcut-20260919'):
 for arm in ('control','keypool'):
  rr=[]
  for p in sorted((R/'artifacts'/wave/arm/'runs').glob('*.json')):
   j=read(p);v=j['validation']; f=v['fixed_K4'];o=f['one_hop']['correct'];t=f['two_hop_trained_rel']['correct'];h=f['two_hop_heldout_rel']['correct'];g=v['gold_read_K2_no_fetch']['two_hop_trained_rel']['correct']
   r=dict(wave=wave,arm=arm,seed=j['seed'],one=o,practised=t,held=h,reads=g,stuck=o<384,all_three=g>=307 and t>=171 and h>=86,steps=j['train_report']['steps'],seconds=j['seconds_total'],device=j['device'],gpu=j.get('gpu_name'),flops=j['train_report']['flops'],source=str(p.relative_to(R)))
   rr.append(r);rows.append(r)
  groups[wave+'/'+arm]=rr
lines=['# Newly arrived evidence — key pooling and interface probes','','**Shown:** standard-library tabulation of JSONs that appeared after the first evidence audit. This supersedes its local-availability statements. No model or test was run. The historical 30-run table is unchanged.','','## Complete saved rosters','','| Wave | Arm | N | Stuck | READS | Practised | Held-out | All three | Mean held-out | Total seconds/run |','|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
for name,rr in groups.items():
 assert sorted(r['seed'] for r in rr)==list(range(40))
 lines.append('| '+name.replace('/',' | ')+f" | {len(rr)} | {sum(r['stuck'] for r in rr)} | {sum(r['reads']>=307 for r in rr)} | {sum(r['practised']>=171 for r in rr)} | {sum(r['held']>=86 for r in rr)} | {sum(r['all_three'] for r in rr)} | {statistics.mean(r['held']/171 for r in rr):.4f} | {min(r['seconds'] for r in rr):.1f}–{max(r['seconds'] for r in rr):.1f} |")
lines+=['','**Shown:** matched-seed discordances (treatment better / worse; exact two-sided McNemar p), descriptive post-arrival analysis, not a new preregistration:','']
for wave in ('claude-keypool-20260919','claude-keypool-relcut-20260919'):
 a={r['seed']:r for r in groups[wave+'/control']};b={r['seed']:r for r in groups[wave+'/keypool']}
 for metric in ('stuck','all_three'):
  good=sum((b[s][metric]<a[s][metric] if metric=='stuck' else b[s][metric]>a[s][metric]) for s in a);bad=sum((b[s][metric]>a[s][metric] if metric=='stuck' else b[s][metric]<a[s][metric]) for s in a)
  lines.append(f'- {wave}, {metric}: {good}/{bad}; p={exact(good,bad):.6f}.')
 lines.append(f"- {wave}, mean held-out paired difference: {statistics.mean((b[s]['held']-a[s]['held'])/171 for s in a):+.4f}; actual steps {min(r['steps'] for r in [*a.values(),*b.values()])}–{max(r['steps'] for r in [*a.values(),*b.values()])}.")
P={c:read(R/f'artifacts/claude-interface-probes-20260919/probe_{c}.json') for c in 'abc'}
lines+=['','## Probe C: factual paths','','**Shown:** 30 result entries per probe. Both restoration comparisons report bit-identical answers and correctness for every checkpoint. Cast-validity masks remain; these interventions do not remove every observable world variable. A story-blind evaluation also changes the question representation distribution.','','| Arm | Condition | One-hop mean | Practised mean | Held-out mean |','|---|---|---:|---:|---:|']
for arm in ('baseline','shortcut'):
 rr=[r for r in P['c']['results'].values() if r['arm']==arm]
 for condition in ('C0_normal','C1_cards_removed','C2_story_blind_question','C3_both'):
  vals=[statistics.mean(r['conditions'][condition][h]['correct']/r['conditions'][condition][h]['n'] for r in rr) for h in ('one_hop','two_hop_trained_rel','two_hop_heldout_rel')]
  lines.append(f'| {arm} | {condition} | '+ ' | '.join(f'{v:.4f}' for v in vals)+' |')
assert all(all(z['answers_bit_identical'] and z['ok_bit_identical'] for z in r['restoration'].values()) for r in P['c']['results'].values())
lines+=['','## Probe A and B','','| Arm/group | n | Edited key cosine mean | First-card identity changes /512 mean | Card-value subject readout | Card-value object readout | Subject-token subject | Object-token object |','|---|---:|---:|---:|---:|---:|---:|---:|']
for arm in ('baseline','shortcut'):
 for group in ('stuck','learned'):
  aa=[r for r in P['a']['results'].values() if r['arm']==arm and r['group']==group];bb=[r for r in P['b']['results'].values() if r['arm']==arm and r['group']==group]
  vals=[statistics.mean(r['cosine']['key_edited']['mean'] for r in aa),statistics.mean(r['retrieval_consequence_one_hop']['top1_changed_identity'] for r in aa)]
  for loc,role in [('card_value','subject'),('card_value','object'),('state_subject_token','subject'),('state_object_token','object')]:vals.append(statistics.mean(r['read_out'][loc][role]['acc16'] for r in bb))
  lines.append(f'| {arm}/{group} | {len(aa)} | '+' | '.join(f'{v:.4f}' for v in vals)+' |')
lines+=['','**Suggested:** interpret recoverability only for this fitted linear probe and fixed layouts. High key cosine can coexist with rank changes. Probe A changes both the key and contextual question state, so its ranking change does not identify key drift as the sole cause. Probe C establishes loss of performance after cutting card access on this panel, with reversible answers; it neither certifies all factual-path closure nor establishes why story-blind questions hurt.','']
with (O/'arrivals-runs.csv').open('x') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (O/'arrivals-manifest.json').open('x') as f:json.dump(manifest,f,indent=2)
with (O/'arrivals-results.md').open('x') as f:f.write('\n'.join(lines))
print('\n'.join(lines))
