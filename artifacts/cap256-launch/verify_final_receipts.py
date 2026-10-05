import collections,datetime,hashlib,json,pathlib,subprocess,sys,os
root=pathlib.Path('C:/Users/benja/sol-cloud-numeric-capability-v1')
ns=root/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/run-capability256-v1'
state=root/'launch-cap256'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_bytes())
ps=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command','Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress'],capture_output=True,text=True,check=True)
procs=json.loads(ps.stdout)
mine={os.getpid()}; bypid={p['ProcessId']:p for p in procs}
cur=os.getpid()
while cur in bypid and bypid[cur]['ParentProcessId'] not in mine:
 cur=bypid[cur]['ParentProcessId'];mine.add(cur)
workers=[{'pid':p['ProcessId'],'name':p['Name']} for p in procs if p['ProcessId'] not in mine and ('pc_driver.py' in (p.get('CommandLine') or '') or 'sol_cloud_capability256_v1.py' in (p.get('CommandLine') or '') or ('python' in (p.get('Name') or '').lower() and ('lis300' in (p.get('CommandLine') or '').lower() or str(root).replace('/','\\').lower() in (p.get('CommandLine') or '').lower())))]
if workers:print(json.dumps({'active_workers':workers}));sys.exit(3)
result={'schema':'cap256.independent-readonly-verification.v1','verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'active_workers':workers,'lock_exists':(state/'LOCK.json').exists(),'arms':[],'receipt_sha256':{}}
spec=read(state/'batches/20260930T212058Z/REQUEST.json')['spec']
result['pinned_file_checks']={k:{'sha256':sha(root/spec[k]['path']),'matches_spec':sha(root/spec[k]['path'])==spec[k]['sha256']} for k in ('runner','plan','seal','release')}
for seed,arm,batch in [(0,'loop','20260930T210659Z'),(0,'plain','20260930T212058Z'),(1,'loop','20260930T212058Z'),(1,'plain','20260930T212058Z')]:
 job='cap256-s%d-%s-%s'%(seed,arm,batch);out=ns/('seed%d'%seed)/arm
 exit=read(state/'jobs'/job/'EXIT.json');closed=read(out/'CLOSED.json');first=read(state/'jobs'/job/'FIRST-UPDATE.json')
 updates=[];visits=collections.Counter();visit_ok=True;identity_ok=True;objective_ok=True;bad=0
 with (out/'TRAIN-RAW.jsonl').open(encoding='utf8') as f:
  for line in f:
   try:r=json.loads(line)
   except ValueError:bad+=1;continue
   updates.append(r.get('update'));identity=r.get('id');visits[identity]+=1
   visit_ok &= r.get('visit_for_row')==visits[identity]
   identity_ok &= r.get('seed')==seed and r.get('arm')==arm and r.get('job')==job
   objective_ok &= r.get('objective')=='numeric-answer-CE-only' and r.get('auxiliary_weight')==0
 rawsha=sha(out/'TRAIN-RAW.jsonl');checkpoint=sha(out/'final-resume.pt')
 checks={'returncode_zero':exit.get('returncode')==0,'closed_true':closed.get('closed') is True,'checkpoint_matches_EXIT':checkpoint==exit['checkpoint']['sha256'],'checkpoint_matches_CLOSED':checkpoint==closed.get('checkpoint',{}).get('sha256'),'raw_matches_CLOSED':rawsha==closed.get('TRAIN_raw_sha256'),'updates_exactly_1_through_5120':updates==list(range(1,5121)),'visit_sequence_valid':visit_ok,'256_rows_20_visits':len(visits)==256 and set(visits.values())=={20},'visits_match_CLOSED':dict(visits)==closed.get('visits'),'identity_valid':identity_ok,'objective_valid':objective_ok,'no_malformed_records':bad==0,'closed_updates_5120':closed.get('optimizer_updates')==5120,'EXIT_count_matches':exit.get('optimizer_updates_counted_from_TRAIN_RAW')==len(updates)}
 result['arms'].append({'seed':seed,'arm':arm,'job_id':job,'launcher_commit':exit['commit'],'runner_started_utc':exit['runner_started_utc'],'runner_ended_utc':exit['runner_ended_utc'],'FIRST-UPDATE':first,'checkpoint_sha256':checkpoint,'checkpoint_bytes':(out/'final-resume.pt').stat().st_size,'TRAIN_raw_sha256':rawsha,'records':len(updates),'distinct_rows':len(visits),'checks':checks,'all_checks_pass':all(checks.values())})
for category in ('jobs','batches'):
 for d in sorted((state/category).iterdir()):
  if not d.is_dir():continue
  for p in sorted(d.iterdir()):
   if p.is_file():result['receipt_sha256'][str(p.relative_to(state)).replace('\\','/')]=sha(p)
print(json.dumps(result,indent=2,sort_keys=True))
