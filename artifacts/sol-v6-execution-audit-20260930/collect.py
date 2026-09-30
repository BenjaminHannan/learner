"""Read-only V6 execution metadata collection; no project imports/models."""
from pathlib import Path
from datetime import datetime, timezone
import collections, hashlib, json, subprocess, tarfile

ROOT=Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
OUT=Path(__file__).resolve().parent
BASE=ROOT/'artifacts/sol-translator-20260929'
EXPECTED_SEAL='e63640f98afc04b122f80423a719891646be45f4c1a40ae8de4e244fcc2924a9'
EXPECTED_PAYLOAD='d041d58ad7979447d473ea0d56d99ef079c039b42ba3307697431feeb0101b9f'
inventory={}
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    value=h.hexdigest();inventory[str(path)]={'sha256':value,'bytes':path.stat().st_size};return value
def load(path):
    digest(path);return json.loads(path.read_text())

REMOTE=r'''
from pathlib import Path
from datetime import datetime,timezone
import collections,hashlib,json,subprocess
root=Path('C:/Users/benja/sol-translator-human-v6');base=root/'artifacts/sol-translator-20260929'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def metadata(p):
 s=p.stat();return {'bytes':s.st_size,'mtime_ns':s.st_mtime_ns}
result={'observed_start_utc':datetime.now(timezone.utc).isoformat(),'root':str(root),'seeds':[]}
for seed in [0,1]:
 d=base/f'ground-v6-s{seed}';item={'seed':seed,'exists':d.is_dir(),'receipts':{},'checkpoint_hashes':{},'raw_metadata':None,'snapshot_consistency':{}}
 if not d.is_dir():result['seeds'].append(item);continue
 item['filenames']={p.name:metadata(p) for p in d.iterdir() if p.is_file()}
 ledger=d/f'grounding-s{seed}.json';before=ledger.read_bytes() if ledger.is_file() else None
 for n in ['LAUNCH.json','MEMORY-PREFLIGHT.json','MEMORY-FAILURE.json','CACHE-LOADER-VERIFICATION.json','LFM-provenance.json',f'grounding-s{seed}-STARTED.json',f'grounding-s{seed}.json','TRANSPORT-RESULT.json']:
  p=d/n
  if not p.is_file():continue
  b=p.read_bytes();x=json.loads(b)
  x={k:v for k,v in x.items() if k not in ['raw_numeric_records','train_unique_ids','claims']}
  item['receipts'][n]={'sha256':hashlib.sha256(b).hexdigest(),'path':str(p),'data':x}
 for n in [f'resume-s{seed}.pt',f'parent-s{seed}.pt',f'input-s{seed}.pt',f'bootstrap-English-s{seed}.pt']:
  p=d/n
  if p.is_file():
   a=metadata(p);h=sha(p);z=metadata(p)
   item['checkpoint_hashes'][n]={'sha256':h,'path':str(p),'bytes':a['bytes'],'file_stable_during_hash':a==z}
 p=d/f'train-raw-s{seed}.jsonl'
 if p.is_file():
  # Only metadata; never compare labels/predictions, decode or score text.
  b=p.read_bytes();rows=0;updates=collections.Counter();splits=collections.Counter();watermarks=[];malformed=0;bindings=collections.defaultdict(set);round_counts=collections.Counter();unique=set();target_visits=0;input_visits=0
  for line in b.splitlines():
   try:x=json.loads(line)
   except ValueError:malformed+=1;continue
   if x.get('kind')=='LAUNCH-WATERMARK':watermarks.append(x);continue
   rows+=1;updates[x.get('update')]+=1;splits[x.get('split')]+=1;unique.add((x.get('launch_id'),x.get('update'),x.get('id')))
   for key in ['job','seed','driver_sha256','deployment_seal_sha256','plan_sha256','source_parent_sha256','reader_version','human_pairs_sha256']:bindings[key].add(x.get(key))
   rounds=x.get('rounds',[]);round_counts[len(rounds)]+=1
   target_visits+=sum(bool(z) for row in x.get('label_mask',[]) for z in row)*len(rounds)
   input_visits+=sum(bool(z) for key in ['input_mask','notebook_mask'] for row in x.get(key,[]) for z in row)
  item['raw_metadata']={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'training_rows':rows,'updates':dict(updates),'last_recorded_update':max(updates,default=0),'split_counts':dict(splits),'watermarks':watermarks,'malformed_lines':malformed,'unique_launch_update_id_count':len(unique),'round_count_distribution':dict(round_counts),'bindings':{k:sorted(v,key=str) for k,v in bindings.items()},'target_token_visits_recount':target_visits,'input_token_visits_recount':input_visits}
 after=ledger.read_bytes() if ledger.is_file() else None
 item['snapshot_consistency']['ledger_unchanged_during_collection']=before==after
 lg=item['receipts'].get(f'grounding-s{seed}.json',{}).get('data',{})
 parent=item['checkpoint_hashes'].get(f'parent-s{seed}.pt',{})
 item['snapshot_consistency']['parent_hash_matches_ledger']=lg.get('parent_checkpoint_sha256')==parent.get('sha256') if parent else None
 result['seeds'].append(item)
cmd="Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*sol-translator-human-v6*' -or $_.CommandLine -like '*sol_translator_grounding_v6*' -or $_.CommandLine -like '*sol_translator_pc_preflight_v6*' } | Select-Object ProcessId,CreationDate,CommandLine | ConvertTo-Json -Compress"
p=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,timeout=15)
result['scoped_process_query']={'returncode':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
result['observed_end_utc']=datetime.now(timezone.utc).isoformat()
print(json.dumps(result))
'''

OUT.mkdir(parents=True,exist_ok=True)
seal=load(BASE/'DEPLOYMENT-V6-SEAL.json');package=load(BASE/'DEPLOYMENT-V6-PACKAGE.json');plan=load(BASE/'DEPLOYMENT-V6-PLAN.json')
checks=[{'path':p,'expected':h,'actual':digest(ROOT/p)} for p,h in seal['files'].items()]
for x in checks:x['match']=x['actual']==x['expected']
payload=digest(BASE/'translator-v6-payload.tar.gz')
with tarfile.open(BASE/'translator-v6-payload.tar.gz') as t:
    members={m.name:m for m in t.getmembers()}
    archive_checks=[{'path':p,'match':p in members and hashlib.sha256(t.extractfile(members[p]).read()).hexdigest()==h} for p,h in seal['files'].items()]
    archive={'files':len(members),'expanded_bytes':sum(m.size for m in members.values()),'checks':archive_checks}
remote=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','benspc',r'C:\Users\benja\lis300\venv\Scripts\python.exe -B -'],input=REMOTE,capture_output=True,text=True,timeout=90)
if remote.returncode:raise RuntimeError('Read-only SSH failed: '+remote.stderr)
snapshot=json.loads(remote.stdout)
(OUT/'PC-METADATA-SNAPSHOT.json').write_text(json.dumps(snapshot,indent=2,sort_keys=True)+'\n')
watcher=[];events=[];q=Path('/Users/ben-hannan/premonition-watch/queue')
for seed in [0,1]:
    job=f'sol-translator-human-v6-s{seed}-pc';state={'seed':seed,'files':{},'machine_status_events':[]}
    for suffix in ['md','running','exit','go1.reply.md','go1.err.txt']:
        p=q/(job+'.'+suffix);item={'path':str(p),'exists':p.is_file()}
        if p.is_file():
            item['bytes']=p.stat().st_size;item['sha256']=digest(p)
            if suffix in ['running','exit','go1.err.txt']:item['raw_status']=p.read_text()
            if suffix=='go1.reply.md':
                # Parse only machine execution-status JSON; ignore prose/output.
                for line in p.read_text().splitlines():
                    try:x=json.loads(line)
                    except ValueError:continue
                    if isinstance(x,dict) and x.get('status') in ['OPTIMIZER-READY','DURABLE-TRAIN-WEIGHTS']:state['machine_status_events'].append(x)
        state['files'][suffix]=item
    watcher.append(state)
log=q.parent/'watch.log'
if log.is_file():
    digest(log);events=[l for l in log.read_text().splitlines() if any(f'sol-translator-human-v6-s{s}-pc' in l for s in [0,1])]
local_checks=[]
for seed in [0,1]:
    d=BASE/f'ground-v6-s{seed}'
    if not (d/'TRANSPORT-RESULT.json').is_file():continue
    transport=load(d/'TRANSPORT-RESULT.json')
    for p,h in transport['paths_and_hashes'].items():
        candidate=ROOT/p.replace('\\','/')
        if not candidate.is_file() and candidate.suffix=='.pt' and not candidate.name.startswith('resume-'):candidate=BASE/f'ground-v6-weights-s{seed}'/candidate.name
        actual=digest(candidate) if candidate.is_file() else None
        local_checks.append({'seed':seed,'expected_remote_path':p,'local_path':str(candidate),'expected':h,'actual':actual,'match':actual==h,'available':actual is not None})
states=[]
for item,w in zip(snapshot['seeds'],watcher):
    seed=item['seed'];receipts=item['receipts'];lg=receipts.get(f'grounding-s{seed}.json',{}).get('data',{});transport=receipts.get('TRANSPORT-RESULT.json',{}).get('data',{})
    processes=snapshot['scoped_process_query']['stdout'];live=f'ground-v6-s{seed}' in processes
    if transport.get('returncode')==0 and lg.get('requested_updates_completed'):status='COMPLETED'
    elif transport.get('returncode') not in (None,0) or 'MEMORY-FAILURE.json' in receipts:status='FAILED'
    elif live or w['files']['running']['exists']:status='RUNNING'
    elif w['files']['md']['exists'] and not item['exists']:status='QUEUED / NO PC START RECEIPT'
    else:status='INCOMPLETE / NOT ESTABLISHED'
    raw=item.get('raw_metadata') or {};statuses=w['machine_status_events'];durable=[x for x in statuses if x.get('status')=='DURABLE-TRAIN-WEIGHTS']
    states.append({'seed':seed,'state':status,'launch':receipts.get('LAUNCH.json',{}).get('data'),
                   'optimizer_ready_events':[x for x in statuses if x.get('status')=='OPTIMIZER-READY'],
                   'first_durable_event':durable[0] if durable else None,'last_durable_event':durable[-1] if durable else None,
                   'durable_ledger_update':lg.get('updates'),'raw_watermark_update':lg.get('raw_watermark_update'),
                   'last_raw_complete_update':raw.get('last_recorded_update'),'raw_training_rows':raw.get('training_rows'),
                   'update_rows_all_batch2':all(n==2 for n in raw.get('updates',{}).values()),
                   'target_token_visits_match_ledger':raw.get('target_token_visits_recount')==lg.get('human_target_token_visits'),
                   'input_token_visits_match_ledger':raw.get('input_token_visits_recount')==lg.get('input_token_visits'),
                   'ledger':lg,'preflight':receipts.get('MEMORY-PREFLIGHT.json',{}).get('data'),
                   'transport':transport,'checkpoint_hashes':item['checkpoint_hashes'],'snapshot_consistency':item['snapshot_consistency'],
                   'process_live':live})
result={'saved_utc':datetime.now(timezone.utc).isoformat(),'scope':'Engineering execution audit only; no behavior narratives read, no TRAIN/evaluation scoring, model deserialization, inference, learning, cache mutation, queue edits, process kills or Git. SSH runs stdlib metadata/hash reads and scoped process query only.',
        'expected_seal_sha256':EXPECTED_SEAL,'seal_hash_match':digest(BASE/'DEPLOYMENT-V6-SEAL.json')==EXPECTED_SEAL,
        'expected_payload_sha256':EXPECTED_PAYLOAD,'payload_hash_match':payload==EXPECTED_PAYLOAD==package['sha256'],
        'seal_checks':checks,'archive':archive,'plan':plan,'states':states,'watcher':watcher,'watcher_events_local_EDT':events,
        'local_transport_hash_checks':local_checks,'inventory':inventory,'PC_snapshot_path':str(OUT/'PC-METADATA-SNAPSHOT.json'),
        'limitations':['Live seed snapshots are time-bounded; unchanged files and ledger/parent matches are reported separately.','STARTED.optimizer_started=false describes pre-optimizer stage, not final state.','Logged durable updates and verified checkpoint bytes establish execution evidence; optimizer/RNG internals were not deserialized or independently restored.','Exact wall-clock first optimizer completion is not logged; launch_id UTC and first durable elapsed time are supplied without inventing a timestamp.','Preflight optimizer margin is inferred, not measured; separate first-optimizer peak is absent.','No English/grammar/stop/semantic quality inference or scientific promotion.']}
(OUT/'audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
lines=['V6 — INDEPENDENT ACTUAL EXECUTION-RECEIPT AUDIT',result['saved_utc'],result['scope'],
       'PC snapshot UTC: '+snapshot['observed_start_utc']+' to '+snapshot['observed_end_utc'],
       f'Seal expected {EXPECTED_SEAL}; match={result["seal_hash_match"]}. Payload expected {EXPECTED_PAYLOAD}; match={result["payload_hash_match"]}. All {len(checks)} pin checks match='+str(all(x['match'] for x in checks))+'.',
       'No authored behavior verdict used. Watcher local dates are EDT (UTC-4). LAUNCH precedes preflight/optimizer and alone does not prove training.']
for s in states:
    lines+=['',f'SEED {s["seed"]}: {s["state"]}',json.dumps(s,indent=2)]
lines+=['','Watcher events:',*events,'','Limits:',*result['limitations'],
        'Sealed budget500 updates/seed,batch2,4 rounds,3000s TRAIN/3950s watcher,zero sleep. Preflight measured VRAM on RTX5070Ti; actual TRAIN peak allocated is ledger evidence, not first-optimizer peak. Receipt hashes and bounds are execution support only.',
        '', 'Local copied artifact checks:',json.dumps(local_checks,indent=2),'','Evidence SHA256:']
for p,x in sorted(inventory.items()):lines.append(x['sha256']+'  '+p)
(OUT/'EXECUTION-AUDIT.txt').write_text('\n'.join(lines)+'\n')
print(json.dumps({'observed_start_utc':snapshot['observed_start_utc'],'observed_end_utc':snapshot['observed_end_utc'],'states':[{'seed':s['seed'],'state':s['state'],'durable_step':s['durable_ledger_update'],'last_raw_step':s['last_raw_complete_update'],'rows':s['raw_training_rows'],'consistent':s['snapshot_consistency']} for s in states],'all_seals_match':all(x['match'] for x in checks)}))
