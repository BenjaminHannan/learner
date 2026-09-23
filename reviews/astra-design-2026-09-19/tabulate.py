"""JSON-only audit. Standard library; never imports project code or opens tensor files.
Run once: outputs use exclusive creation and cannot overwrite a previous audit.
"""
import csv, hashlib, json, math, pathlib, statistics
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
inputs = []
def read(p):
    p = ROOT / p
    raw = p.read_bytes()
    inputs.append({'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest()})
    return json.loads(raw)
def write(name, obj):
    with (OUT / name).open('x') as f:
        json.dump(obj, f, indent=2); f.write('\n')
def tail(n,k,p):
    return sum(math.comb(n,i)*p**i*(1-p)**(n-i) for i in range(k,n+1))
def lower(n,k):
    lo,hi=0.,1.
    for _ in range(100):
        mid=(lo+hi)/2
        if tail(n,k,mid)<.05: lo=mid
        else: hi=mid
    return (lo+hi)/2
rows=[]; summaries={}
for arm, directory in [('baseline','claude-long-20260919'),('shortcut','claude-relcut-long-20260919')]:
    for p in sorted((ROOT/'artifacts'/directory/'runs').glob('*.json')):
        d=read(p.relative_to(ROOT)); v=d['validation']; own=v['fixed_K4']; gold=v['gold_read_K2_no_fetch']
        if [own[k]['n'] for k in ['one_hop','two_hop_trained_rel','two_hop_heldout_rel']] != [512,341,171]:
            raise ValueError('Unexpected denominators: '+str(p))
        if gold['two_hop_trained_rel']['n'] != 341: raise ValueError('Bad READS denominator')
        row=dict(arm=arm,seed=d['seed'],one=own['one_hop']['correct'],practised=own['two_hop_trained_rel']['correct'],heldout=own['two_hop_heldout_rel']['correct'],reads=gold['two_hop_trained_rel']['correct'],updates=d['train_report']['steps'],seconds_train=d['seconds_train'],seconds_total=d['seconds_total'],path=str(p.relative_to(ROOT)))
        row.update(stuck=row['one']<384,all_three=row['reads']>=307 and row['practised']>=171 and row['heldout']>=86)
        rows.append(row)
    panel=sorted([r for r in rows if r['arm']==arm],key=lambda r:r['seed'])
    if [r['seed'] for r in panel]!=list(range(15)): raise ValueError('Bad seed roster')
    live=[r for r in panel if not r['stuck']]
    summaries[arm]=dict(n=len(panel),stuck=sum(r['stuck'] for r in panel),stuck_seeds=[r['seed'] for r in panel if r['stuck']],reads=sum(r['reads']>=307 for r in panel),practised=sum(r['practised']>=171 for r in panel),heldout=sum(r['heldout']>=86 for r in panel),all_three=sum(r['all_three'] for r in panel),heldout_among_learned=[sum(r['heldout']>=86 for r in live),len(live)],updates=sorted(set(r['updates'] for r in panel)),train_seconds_range=[min(r['seconds_train'] for r in panel),max(r['seconds_train'] for r in panel)])
rows.sort(key=lambda r:(r['arm'],r['seed']))
with (OUT/'toy-runs.csv').open('x',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (OUT/'toy-results.md').open('x') as f:
    f.write('# Toy results regenerated from 30 run JSONs\n\n**Shown.** Validation only; fixed_K4. READS is gold_read_K2_no_fetch/practised. These are old screening gates, not certification.\n\n| Arm | Stuck | READS | Practised | Held-out | All three |\n|---|---:|---:|---:|---:|---:|\n')
    for arm,s in summaries.items():f.write(f"| {arm} | {s['stuck']}/15 | {s['reads']}/15 | {s['practised']}/15 | {s['heldout']}/15 | {s['all_three']}/15 |\n")
    f.write('\n| Arm | Seed | One /512 | READS /341 | Practised /341 | Held-out /171 | Updates | All three |\n|---|---:|---:|---:|---:|---:|---:|---|\n')
    for r in rows:f.write(f"| {r['arm']} | {r['seed']} | {r['one']} | {r['reads']} | {r['practised']} | {r['heldout']} | {r['updates']} | {r['all_three']} |\n")
    f.write('\nDefinitions: stuck one<384; READS>=307; practised>=171; held-out>=86; all_three is the conjunction of READS, practised and held-out. One-hop is a separate gate. Source paths and timings are in toy-runs.csv.\n')
# Exact Fisher under independent-arm null, paired discordance as a separate descriptive calculation.
prob=lambda a:math.comb(15,a)*math.comb(15,11-a)/math.comb(30,11)
fisher=sum(prob(a) for a in range(12) if prob(a)<=prob(4)+1e-15)
base={r['seed']:r for r in rows if r['arm']=='baseline'}; cut={r['seed']:r for r in rows if r['arm']=='shortcut'}
worse=sum(not base[s]['stuck'] and cut[s]['stuck'] for s in base)
better=sum(base[s]['stuck'] and not cut[s]['stuck'] for s in base)
stats=dict(fisher_two_sided=fisher,paired_stuck=dict(shortcut_worse=worse,shortcut_better=better,mcnemar_exact_two_sided=min(1.,2*sum(math.comb(worse+better,i)*.5**(worse+better) for i in range(min(worse,better)+1)))),one_sided_95_CP={'36/40':lower(40,36),'77/80':lower(80,77)},certification_acceptance={str(p):tail(80,77,p) for p in [.9,.95,.97,.98,.99]},sign_tests={})
for n in [10,16,24]:
    k=min(k for k in range(n+1) if tail(n,k,.5)<=.05)
    stats['sign_tests'][str(n)]={'critical_wins':k,'size':tail(n,k,.5),'power':{str(p):tail(n,k,p) for p in [.7,.75,.8,.85]}}
# Village table rebuilt from per-item JSON, seen-names from stored aggregate only.
village=[]
for p in sorted((ROOT/'artifacts/claude-pointer-ablation-20260919').glob('eval-*.json')):
    d=read(p.relative_to(ROOT)); rr=d['items']['validation']; decision=[r for r in rr if r['decision']]
    fresh=[r for r in rr if 'fresh_names' in r['slices']]
    village.append(dict(file=str(p.relative_to(ROOT)),contender=d['contender'],seed=int(p.name.split('-s')[1][0]),parameters=d['parameters'],purpose=d['purpose_used'],overall=[sum(r['correct'] for r in decision),len(decision)],fresh=[sum(r['correct'] for r in fresh),len(fresh)],fresh_qtypes_unavailable=True,seen=d['name_gap']['seen_names'],input_audit=d['directories']['validation']['input_audit'],tokenizer=d['identity']['tokenizer'],config=d['config']))
smokes=[]
for p in sorted((ROOT/'artifacts/claude-softread-20260919/runs').glob('*.json')):
    d=read(p.relative_to(ROOT));smokes.append({k:d.get(k) for k in ['name','steps_done','steps_per_second','seconds_train','seconds_total','oracle_use']})
handoff=read('artifacts/claude-handoff-20260919/d1.json')
address=read('artifacts/opus-m03-20260919-071009/confirm/compare.json')
manifest=read('artifacts/opus-ovn-20260918-235851/exp1/data/manifest.json')
write('evidence.json',dict(toy=summaries,statistics=stats,village=village,softread_smokes=smokes,handoff={k:{'bootstrap':v['bootstrap'],'advancement':v['advancement']} for k,v in handoff['panels'].items()},address_confirmation=[r for r in address['rows'] if r['condition']=='O'],toy_manifest=manifest))
write('input-json-manifest.json',inputs)
print(json.dumps({'toy':summaries,'statistics':stats,'input_files':len(inputs)},indent=2))
