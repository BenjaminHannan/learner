#!/usr/bin/env python3
"""Seal tiny capacity/conditioning diagnostics only; never launches optimization."""
import ast,hashlib,json,random,subprocess,tarfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];O=ROOT/'artifacts/sol-translator-20260929'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 if (O/'TINY-V12-SEAL.json').exists():raise RuntimeError('preserve existing seal')
 spec11=json.loads((O/'ANSWER-V11-DIAGNOSTIC-PLAN.json').read_text());ids=spec11['TRAIN_diagnostic_ids'][:4]
 plan={'stage':'four-example HUMAN TRAIN memorization/causal diagnosis NOT release architecture','TRAIN_ids':ids,'same_context_pairs':spec11['same_context_pairs'][:2],'seeds':[0,1],'updates_each_arm':200,'batch':1,'arms':['connected','direct_prefix_table_capacity_ONLY'],'connected_lr':.001,'table_lr':.01,'weight_decay':0,'clip_norm':1,'trace_updates':[25,100,200],'fit_wall_seconds':900,'job_child_seconds':1600,'queue_wall_seconds':1800,'output_cap_bytes':384*1024**2,'retained_free_bytes':1024**3,'startup_free_bytes':(1024+384+16)*1024**2,'tuples':{},'annotation_manifest_sha256':sha(O/'ANSWER-V11-ANNOTATIONS.json'),'question_selection':'First two fixed sharedcontext pairs from previous TRAIN-development diagnostic; not fresh proof and not success-selected','objective':'verbatim HUMAN answer+EOS CE; connected adds existing mean8 routeraux, table has no core/aux; CE-only autograd recorded separately','capacity_control':'Task-indexed four independent8xLMwidth learned prefixes initialized from frozen starting connected outputs. This uses ID routing and is a memorization upperbound only, NEVER release/export/solver. Connected arm has NO ID routing; shared reader/core/prefix receives question/context only. Arms not matched capacity or learning rate.','output_contract':'Connected generated output only from finalquery->sharedprefix; no raw question/context/answer LM prompt; no model text labels','hypotheses':{'alignment':'Mismatch exceeding repeated numerical noise between TF firstlogit/BOS-only/HFgenerate or cache/manual tokens suggests execution/config cause; raw thresholds not silently invented','capacity':'Prespecified tiny-memorization milestone: all4 greedy outputs exactly equal tokenized HUMAN answer without EOS at update200; report raw even if unmet. Table memorizes targets but connected does not: bottleneck upstream of free prefix, not proof of reasoner impossibility. Both fail: insufficient optimization or decoder conditioning remains possible.','conditioning':'Connected reproduces different HUMAN answers for pairedquestions and swaps/zero/noNotebook change appropriate outputs: memorization-level conditioning only, not general QA.'},'preoptimization':'Exact LM/config/runtime hashes and four initial TF/BOS/repeat/cache/manual probes per seed; zeroopt real connectedgraph memory guard before optimizer','evidence':'CE-only module+activation norms, parameterdeltas, rawlabels/argmax, intermediate finalquery/normalized/projected/pooledtraces and free outputs at fixedupdates; prefixes never reused as labels','presealed_noise':'Repeat rawlogit noise measured within initial helper; no acceptancebar or semanticpromotion; source fakeLM equalitydifferences not actualLM evidence','DEV0':True,'stop88':False,'sleep0':True,'grammar':'Short memorized answers do not fulfill grammatical conversation','disk':'No LM/parent copies; resumeonly trainable core/read/prefix+Adam/RNG;384MiB aggregatebothseeds includesatomictemporary,1GiBretainbeforeeachsave. Outputs checkpointnotrelease.'}
 for seed in (0,1):
  cfg=json.loads((O/f'ground-answer-v11-s{seed}-loop/runtime-config.json').read_text());ledger=json.loads((O/f'ground-answer-v11-s{seed}-loop/grounding-s{seed}.json').read_text());transport=json.loads((O/f'ground-answer-v11-s{seed}-loop/TRANSPORT-RESULT.json').read_text());assert ledger['closed'] and ledger['updates']==200 and transport['returncode']==0
  for k,name in [('parent',f'parent-s{seed}.pt'),('reader',f'input-s{seed}.pt'),('adapter',f'bootstrap-English-s{seed}.pt')]:assert sha(O/f'answer-v11-weights-s{seed}'/name)==cfg[k+'_sha256']
  plan['tuples'][str(seed)]=cfg
  rng=random.Random(2026093012+seed);schedule=[]
  for _ in range(50):block=list(range(4));rng.shuffle(block);schedule+=block
  (O/f'TINY-V12-SCHEDULE-s{seed}.json').write_text(json.dumps(schedule)+'\n')
 (O/'TINY-V12-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
 base=json.loads((O/'ANSWER-V11-SEAL.json').read_text())['files'];pins={k:v for k,v in base.items() if '/queue-' not in k}
 for n,h in pins.items():assert sha(ROOT/n)==h
 for name in ('sol_translator_tiny_v12.py','sol_translator_package_tiny_v12.py','sol_spatial_decoder_parity_v12.py','sol_spatial_decoder_parity_adapter_v12.py'):
  p=ROOT/'scripts'/name;ast.parse(p.read_text());pins[str(p.relative_to(ROOT))]=sha(p)
 for name in ('TINY-V12-PLAN.json','TINY-V12-SCHEDULE-s0.json','TINY-V12-SCHEDULE-s1.json'):
  p=O/name;pins[str(p.relative_to(ROOT))]=sha(p)
 for seed in (0,1):
  q=f'''BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 30 minutes
LABEL: sol-translator-tiny-v12-s{seed}-pc

READY HUMAN TRAIN four-example capacity diagnosis ONLY. Two arms200updates each: connected reader/core/prefix vs task-indexed prefix table (NOT release architecture). Initial four actualLM noopt cache/label alignment probes; CE-only gradients; no rawquestionLMbypass on connected. FP32cachedLM reused, no copies.384MiBaggregatebothseedoutputs includingatomictemporary;1GiBretainedreserve, startup1424MiB. FreshDEV/stop88 untouched. Raw generated prose never training labels. No semantic/grammar/sleep gain claim.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 1800 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-translator-20260929
SOL_PC=C:/Users/benja/sol-translator-tiny-v12
ssh -T -o BatchMode=yes benspc 'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -' <<'PYREMOTE'
from pathlib import Path
import shutil
r=Path('C:/Users/benja/sol-translator-tiny-v12');assert shutil.disk_usage('C:/').free>=1424*1024**2,'NEW DISK RESERVE';r.mkdir(exist_ok=True)
assert not (r/'artifacts/sol-translator-20260929/tiny-v12-s{seed}/LAUNCH.json').exists(),'PRESERVE earlier run'
PYREMOTE
scp "$SOL_ART/translator-tiny-v12-payload.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_ART/TINY-V12-PACKAGE.json" benspc:"$SOL_PC/package.json"
set +e
ssh -T -o BatchMode=yes -o ServerAliveInterval=20 benspc 'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -' <<'PYREMOTE' 2>&1 | tee "$SOL_ART/tiny-v12-s{seed}-PC.log"
import hashlib,json,os,sys,subprocess,tarfile,time
from pathlib import Path
r=Path('C:/Users/benja/sol-translator-tiny-v12');m=json.loads((r/'package.json').read_text());assert hashlib.sha256((r/'payload.tar.gz').read_bytes()).hexdigest()==m['sha256']
with tarfile.open(r/'payload.tar.gz') as t:
 for x in t.getmembers():assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts
 t.extractall(r)
os.chdir(r);env=dict(os.environ,JOB='sol-translator-tiny-v12-s{seed}-pc',TREE=str(r),PYTHONPATH=str(r)+os.pathsep+str(r/'scripts'),PYTHONUTF8='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1');out=r/'artifacts/sol-translator-20260929/tiny-v12-s{seed}';start=time.monotonic();rc=1
try:
 proc=subprocess.Popen([sys.executable,'-X','utf8','-B','scripts/sol_translator_tiny_v12.py','--seed','{seed}'],env=env);rc=proc.wait(timeout=1600)
except subprocess.TimeoutExpired:
 proc.terminate();rc=124
 try:proc.wait(timeout=30)
 except subprocess.TimeoutExpired:proc.kill();proc.wait()
finally:
 out.mkdir(parents=True,exist_ok=True);record={{'returncode':rc,'wall_seconds':time.monotonic()-start,'hashes':{{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}},'stage':'tiny TRAIN capacity diagnostic NOTrelease'}};(out/'TRANSPORT-RESULT.json').write_text(json.dumps(record)+'\\n')
 with tarfile.open(r/'tiny-v12-s{seed}-raw.tar.gz','w:gz') as t:
  for p in out.iterdir():
   if p.is_file() and p.suffix not in ('.pt','.tmp'):t.add(p,arcname=str(p.relative_to(r)),recursive=False)
 print(json.dumps(record),flush=True)
sys.exit(rc)
PYREMOTE
SOL_RC=${{PIPESTATUS[0]}}
set -e
scp benspc:"$SOL_PC/tiny-v12-s{seed}-raw.tar.gz" "$SOL_ART/tiny-v12-s{seed}-raw.tar.gz" || true
if [ -f "$SOL_ART/tiny-v12-s{seed}-raw.tar.gz" ]; then tar -xzf "$SOL_ART/tiny-v12-s{seed}-raw.tar.gz" -C /Users/ben-hannan/Desktop/projects/beautiful-model; fi
printf '%s\\n' "$SOL_RC" > "$SOL_ART/tiny-v12-s{seed}-PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-translator-20260929/tiny-v12-s{seed} artifacts/sol-translator-20260929/tiny-v12-s{seed}-PC.log artifacts/sol-translator-20260929/tiny-v12-s{seed}-PC.exit
'''
  qp=O/f'queue-sol-translator-tiny-v12-s{seed}-pc.md';qp.write_text(q);subprocess.run(['bash','-n'],input=q.split('```bash\n')[1].split('```')[0],text=True,check=True);pins[str(qp.relative_to(ROOT))]=sha(qp)
 sp=O/'TINY-V12-SEAL.json';sp.write_text(json.dumps({'sealed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':pins,'human_origin_only':True,'fresh_panels':False,'no_semantic_promotion':True},indent=2)+'\n')
 payload=O/'translator-tiny-v12-payload.tar.gz'
 with tarfile.open(payload,'w:gz') as t:
  for n in sorted(pins):t.add(ROOT/n,arcname=n,recursive=False)
  t.add(sp,arcname=str(sp.relative_to(ROOT)),recursive=False)
 report={'sha256':sha(payload),'seal_sha256':sha(sp),'bytes':payload.stat().st_size,'pins':len(pins),'members':len(pins)+1};(O/'TINY-V12-PACKAGE.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
