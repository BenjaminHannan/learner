"""Blind composition awake recount; stdlib only, no model/data execution."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, math

ROOT=Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
OUT=Path(__file__).resolve().parent
BASE='artifacts/sol-compose-20260929/'
RAW=BASE+'awake-pc/sol_compose_awake_'
inventory={}
def sha(p):
    f=ROOT/p
    if not f.is_file(): return None
    b=f.read_bytes();h=hashlib.sha256(b).hexdigest()
    inventory[p]={'sha256':h,'bytes':len(b)}
    return h
def load(p):
    sha(p);return json.loads((ROOT/p).read_text())
seal=load(BASE+'SEAL-AWAKE.json')
spec=load(BASE+'SPEC-AWAKE.json')
original=load(BASE+'SPEC.json')
sha(BASE+'ADDENDUM-AWAKE.md');sha(BASE+'PASSMARKS.md')
sealed=[]
for p,h in seal['sha256'].items():
    if p.startswith('handoff/'):
        sealed.append({'path':p,'status':'NOT ACCESSED: prohibited handoff path','expected':h})
    else:
        actual=sha(p);sealed.append({'path':p,'expected':h,'actual':actual,'match':actual==h})
started=load(RAW+'STARTED.json');complete=load(RAW+'COMPLETE.json')
checkpoints=load(RAW+'CHECKPOINT-SEAL.json');noise=load(RAW+'NOISE.json')
data=load(RAW+'DATA.json');contract=load(RAW+'PC-CONTRACT.json')
arms=['compose','no_communication','joint','plain','record_only','numeric_only']
controls=arms[1:]
records={};training={};rows=[]
for seed in [0,1]:
    for arm in arms:
        key=f'{arm}-s{seed}'
        records[key]=load(RAW+key+'_raw.json')
        training[key]=load(RAW+key+'_training.json')
        for split,r in records[key].items():
            n=r['n'];pred=r['predictions'];fixed=r['fixed_predictions'];lab=r['labels'];rounds=r['rounds']
            learned=sum(a==b for a,b in zip(pred,lab));cap=sum(x==6 for x in rounds)
            fixed_exact=sum(a==b for a,b in zip(fixed,lab));mean=sum(rounds)/len(rounds)
            rows.append({'key':key,'seed':seed,'arm':arm,'split':split,'n':n,'learned_exact':learned,
                         'fixed_exact':fixed_exact,'stop_loss_count':fixed_exact-learned,
                         'mean_rounds':mean,'cap_hits':cap,'query_sha256':r['query_sha256'],
                         'lengths_match':len(pred)==len(fixed)==len(lab)==len(rounds)==n,
                         'stored_metrics_match':learned==r['exact'] and fixed_exact==r['fixed_exact'] and cap==r['cap_hits'] and math.isclose(mean,r['mean_rounds'],abs_tol=1e-12),
                         'rounds_valid':all(type(x) is int and 1<=x<=6 for x in rounds),
                         'scored_once_assertion':r['scored_once_per_checkpoint'],
                         'stop_readiness':learned>=90 and fixed_exact-learned<=2 and mean<=4.5 and cap<=10 if split=='TRAIN_retention' else None})
index={(x['seed'],x['arm'],x['split']):x for x in rows}
bars={};gates=[];pairing={}
for split in ['dev_structure','dev_order']:
    spans={a:abs(index[(0,a,split)]['learned_exact']-index[(1,a,split)]['learned_exact'])*0.5 for a in controls}
    span=max(spans.values());bar=max(10,2*span+1)
    bars[split]={'control_seed_spans_pp':spans,'span_pp':span,'bar_pp':bar,
                 'stored_noise_matches':spans==noise[split]['control_seed_spans_pp'] and span==noise[split]['measured_diagnostic_span_pp'] and bar==noise[split]['screen_bar_pp']}
    rr=[records[f'{a}-s{s}'][split] for s in [0,1] for a in arms]
    pairing[split]={'same_query_hash_all_arms_seeds':len({r['query_sha256'] for r in rr})==1,
                    'same_labels_all_arms_seeds':all(r['labels']==rr[0]['labels'] for r in rr),
                    'data_manifest_matches_raw_by_seed':{str(s):data[str(s)][split]['sha256']==records[f'compose-s{s}'][split]['query_sha256'] for s in [0,1]}}
    for seed in [0,1]:
        c=index[(seed,'compose',split)];best=max(index[(seed,a,split)]['learned_exact'] for a in controls)
        gaps={a:c['learned_exact']-index[(seed,a,split)]['learned_exact'] for a in controls}
        floor=c['learned_exact']>=160;gap=(c['learned_exact']-best)/200*100>=bar;stop=c['stop_loss_count']<=4
        gates.append({'seed':seed,'split':split,'candidate':c['learned_exact'],'strongest_control':best,
                      'best_arms':[a for a in controls if index[(seed,a,split)]['learned_exact']==best],
                      'candidate_control_deltas_counts':gaps,'gap_pp':(c['learned_exact']-best)/2,
                      'bar_pp':bar,'floor_pass':floor,'gap_pass':gap,'stop_pass':stop,'screen_met':floor and gap and stop})
checkpoint_checks=[]
for key,entry in checkpoints.items():
    p=BASE+'awake-pc/'+entry['path'];actual=sha(p)
    alternate=None
    if actual is None and key.startswith('compose-'):
        alternate=BASE+'awake-weights/'+key+'.pt';actual=sha(alternate)
    checkpoint_checks.append({'key':key,'manifest_path':p,'local_alternate':alternate,'expected':entry['sha256'],
                              'actual':actual,'verified':actual==entry['sha256'],'available':actual is not None})
budget=[]
for key,t in training.items():
    mac=t['forward_macs'];sample=t['losses_first_last_four']
    budget.append({'key':key,'updates':t['completed_updates'],'presentations':t['presentations'],
                   'sleep_updates':t['sleep_updates'],'seconds':t['seconds'],'counts':t['counts'],
                   'cuda_peak_allocated_bytes':t['cuda_peak_allocated_bytes'],
                   'forward_macs':mac,'backward_macs_estimate':t['backward_macs_estimate'],
                   'mac_arithmetic_match':mac['total']==sum(mac[k] for k in ['gru','linear','matrix']) and t['backward_macs_estimate']==2*mac['total'],
                   'sampled_loss_steps':[x['step'] for x in sample],
                   'sampled_losses_finite':all(math.isfinite(v) for x in sample for k,v in x.items() if isinstance(v,(float,int)))})
verdicts={str(s):'SCREEN NOT MET; NOT SHOWN ON DEV' if not all(g['screen_met'] for g in gates if g['seed']==s) else 'SCREEN MET; INDEPENDENT RECOUNT ONLY; NOT SCIENTIFICALLY SHOWN' for s in [0,1]}
causal={}
for s in [0,1]:
    a=training[f'compose-s{s}'];b=training[f'no_communication-s{s}']
    causal[str(s)]={'counts_equal':a['counts']==b['counts'],'forward_macs_equal':a['forward_macs']==b['forward_macs'],
                    'budget_equal':a['completed_updates']==b['completed_updates'] and a['presentations']==b['presentations'],
                    'initial_weights_and_minibatch_schedule_hashes':'NOT SAVED; cannot independently verify exact causal initialization/order match'}
result={'saved_utc':datetime.now(timezone.utc).isoformat(),'job_identity':'sol-compose-awake-20260929-benspc',
        'scope':'Blind saved prediction-label-round recount only; no authored SUMMARY/report/narratives, source content, holdout or notebook contents read; no inference, generation, rescoring, learning or git.',
        'verdict':'SCREEN NOT MET; SCIENTIFIC PROMOTION NOT SHOWN', 'seed_verdicts':verdicts,
        'required_raw_availability':'All 12 training and 12 evaluation JSONs, labels/predictions/fixed predictions/rounds, both presealed protocols, noise, checkpoint manifest, data manifest and completion present. Ten comparator checkpoint bytes absent locally; exact initialization/order hashes and score chronology absent.',
        'seal_checks':sealed,'started_seal_matches':started['seal']==seal,'started':{'utc':started['utc'],'device':started['device'],'torch':started['torch']},
        'complete':complete,'rows':rows,'noise_recount':bars,'gates':gates,'pairing':pairing,
        'budgets':budget,'total_updates':sum(x['updates'] for x in budget),'total_presentations':sum(x['presentations'] for x in budget),
        'total_forward_macs_subset':sum(x['forward_macs']['total'] for x in budget),
        'checkpoint_checks':checkpoint_checks,'causal_controls':causal,'contract_evidence':contract,
        'inventory':inventory}
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'recount.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
lines=['PREMONITION COMPOSITION AWAKE — INDEPENDENT BLIND RECOUNT','Saved UTC: '+result['saved_utc'],
       'Job: '+result['job_identity'],result['scope'],'Verdict: '+result['verdict'],
       'Availability: '+result['required_raw_availability'],'',
       'Authority: SPEC-AWAKE.json and ADDENDUM-AWAKE.md supersede original sleep budgets only. Awake512 updates/arm/seed, batch32 half composed/half primitive, six fp32 full-gradient rounds, lr.001/wd0/clip1, zero sleep. Original causal controls and dev gates remain. No historical RESULTS-EQ narrative was read.',
       'Gate: BOTH seeds on BOTH splits require candidate>=160/200; gap to strongest of five controls>=max(10pp,2*control span+1pp); learned-stop loss<=4/200. A screen cannot authorize scientific promotion. TRAIN stop readiness independently requires n100, learned exact>=90, loss<=2, mean rounds<=4.5, cap hits<=10; even passing author readiness does not authorize sleep.',
       '', 'Exact prediction-versus-label recount (learned/fixed; TRAIN denominator100, dev denominator200):',
       'seed arm                       TRAIN       structure   order']
for s in [0,1]:
    for a in arms:
        cells=[f"{index[(s,a,k)]['learned_exact']}/{index[(s,a,k)]['fixed_exact']}" for k in ['TRAIN_retention','dev_structure','dev_order']]
        lines.append(f'{s}    {a:26s} '+' '.join(f'{x:11s}' for x in cells))
lines+=['','All36 rows were independently compared against saved labels; 6000 learned predictions and6000 fixed predictions,6000 round values. All stored exact/fixed/mean/cap metrics and lengths are checked in recount.json. Labels were not regenerated. Query hash equality and label equality across all12 evaluations of each dev split are checked separately.']
for split,b in bars.items():lines.append(f"Noise {split}: control spans {b['control_seed_spans_pp']}; max{b['span_pp']}pp; bar{b['bar_pp']}pp; stored noise match {b['stored_noise_matches']}.")
for g in gates:lines.append(f"seed{g['seed']} {g['split']}: candidate{g['candidate']}/200, strongest{g['strongest_control']}/200 ({g['best_arms']}), gap{g['gap_pp']}pp, floor/gap/stop {g['floor_pass']}/{g['gap_pass']}/{g['stop_pass']}; SCREEN MET={g['screen_met']}; deltas to controls {g['candidate_control_deltas_counts']}.")
for s,v in verdicts.items():lines.append('Seed'+s+': '+v)
lines+=['','TRAIN readiness:']
for row in rows:
    if row['split']=='TRAIN_retention':lines.append(f"{row['key']}: exact{row['learned_exact']}/100, fixed{row['fixed_exact']}/100, loss{row['stop_loss_count']}, mean{row['mean_rounds']}, cap hits{row['cap_hits']}/100; readiness={row['stop_readiness']}.")
lines+=['','Budgets: '+str(result['total_updates'])+' awake optimizer updates; '+str(result['total_presentations'])+' presentations; each arm/seed512 and16384 (8192 composed+8192 primitive per sealed recipe). Total sleep updates0. Completion records465.75seconds (<3600); deviceCUDA torch2.11.0+cu128. No inherited source weights per sealed recipe.',
       'Only first/last four loss records per arm survive (steps1..4,509..512); no all-step ledger, sampled batch IDs/order hashes, initial state hashes or per-phase timestamps survive. Completion/budget numbers are recorded evidence, not reconstruction of actual512 steps. Partial MAC subset excludes pointwise/reductions/equality/optimizer; backward2x estimate is not measured FLOPs.',
       'Causal controls: '+json.dumps(causal,sort_keys=True),
       'Compose/no_communication intervention cuts communication after executing programs; this preserves recorded computation and shapes, not useful-capacity equality. Joint/plain stored counts are within0.5% per recorded arithmetic; single-program controls smaller. Only joint/plain count arithmetic is independently available, not architecture execution verification. No useful/active-weight, speed or equal-compute win follows.',
       'Important data-manifest discrepancy: raw dev query hashes and labels match across both seeds, but DATA.json retains seed1-specific dev manifests differing from the shared raw dev query hashes. Treat DATA seed1 dev entries as stale/inconsistent provenance, not the scored pool. Full source tables are not reconstructed; table novelty/noncommutation/label semantics beyond saved labels remain unverified. Reverse-order dev also changes topology; it cannot isolate order causality.',
       'Seal: STARTED embedded seal matches current preseal.20 permitted paths are hashed; prohibited handoff/queue path is not accessed. See exact match results below. No eval timestamps or candidate/control/noise publication chronology are recorded in raw JSON; pre-candidate noise/control sealing cannot be independently established from these records. Hash consistency is not trusted external timestamping.',
       'Checkpoint manifest lists12. Only compose-s0/s1 bytes are available under awake-weights and verified; ten comparator checkpoint bytes absent locally. No checkpoint was deserialized. Stop-readiness records do not individually embed checkpoint hashes; binding relies on filename/manifest rather than standalone raw cryptographic linkage.',
       'No sleep, statistical/general reasoning, scaling, English, benchmark, F_eq/F_few or roadmap claim is established. Diagnostic GRUs remain outside target claims. Both seeds independently fail the dev screen; no design rejection. No post-blind source review was performed for this recount. Actual code/raw/seals untouched; James owns integration/push.',
       '', 'Seal checks:',json.dumps(sealed,indent=2), '', 'Checkpoint checks:',json.dumps(checkpoint_checks,indent=2),
       '', 'Training per-arm budget/MAC/count records:',json.dumps(budget,indent=2),'','All raw/protocol SHA256 values:']
for p,x in sorted(inventory.items()):lines.append(x['sha256']+'  '+p)
(OUT/'BLIND-AUDIT.txt').write_text('\n'.join(lines)+'\n')
print(json.dumps({'saved':str(OUT),'verdicts':verdicts,'rows_valid':all(x['lengths_match'] and x['stored_metrics_match'] and x['rounds_valid'] for x in rows),'gates':gates,'permitted_seal_matches':[x.get('match') for x in sealed if 'match' in x],'checkpoint_available':sum(x['available'] for x in checkpoint_checks),'noise':bars}))
