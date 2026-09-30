#!/usr/bin/env python3
"""Queued PC followups: sealed closed parents, frozen-only, no DEV execution."""
import hashlib,json,os,shutil,subprocess,sys,tarfile,time
from pathlib import Path

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def run(a):
 root=Path(a.root).resolve();own=root/'artifacts/sol-translator-20260929';os.chdir(root)
 seal=json.loads((own/'FOLLOWUP-V7-SEAL.json').read_text())
 for name,want in seal['files'].items():assert digest(root/name)==want,'PIN '+name
 assert shutil.disk_usage(root).free>=1024**3,'1GiB free floor'
 out=own/(f'diagnostic-v7-s{a.seed}' if a.mode=='diagnostic' else f'prefix-v7-s{a.seed}-d{a.decoder_seed}-{a.arm}');out.mkdir(parents=True,exist_ok=True)
 assert not (out/'TRANSPORT-LAUNCH.json').exists(),'NO DUPLICATE JOB'
 source=Path('C:/Users/benja/sol-translator-human-v6/artifacts/sol-translator-20260929')/f'ground-v6-s{a.seed}'
 binding=json.loads((own/f'PREFIX-TRAIN-V7-BINDING-s{a.seed}.json').read_text())
 for key,name in [('parent_sha256',f'parent-s{a.seed}.pt'),('reader_sha256',f'input-s{a.seed}.pt'),('bootstrap_sha256',f'bootstrap-English-s{a.seed}.pt'),('LM_provenance_sha256','LFM-provenance.json')]:assert digest(source/name)==binding[key],'CLOSED PC TUPLE '+key
 # Read existing closed weights in place; no duplicate parent or cached LM.
 env=dict(os.environ,JOB=a.job,TREE=str(root),PYTHONPATH=str(root)+os.pathsep+str(root/'scripts'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONUTF8='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
 start=time.monotonic();(out/'TRANSPORT-LAUNCH.json').write_text(json.dumps({'job':a.job,'mode':a.mode,'seal_sha256':digest(own/'FOLLOWUP-V7-SEAL.json'),'source_seed':a.seed,'decoder_seed':a.decoder_seed,'arm':a.arm,'DEV_examples':0,'sleep_updates':0,'parent_reader_LM_frozen':True})+'\n')
 lm='C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b'
 cmd=[sys.executable,'-B','scripts/sol_translator_'+('diagnostic_v7.py' if a.mode=='diagnostic' else 'prefix_train_v7.py'),'--model',lm,'--model-provenance',str(source/'LFM-provenance.json'),'--parent',str(source/f'parent-s{a.seed}.pt'),'--reader',str(source/f'input-s{a.seed}.pt'),'--bootstrap',str(source/f'bootstrap-English-s{a.seed}.pt'),'--binding',str(own/f'PREFIX-TRAIN-V7-BINDING-s{a.seed}.json'),'--plan',str(own/('DIAGNOSTIC-V7-PLAN.json' if a.mode=='diagnostic' else 'PREFIX-TRAIN-V7-PLAN.json')),'--seed',str(a.seed),'--out',str(out),'--device','cuda']
 if a.mode!='diagnostic':cmd+=['--decoder-seed',str(a.decoder_seed),'--arm',a.arm,'--marks',str(own/'ENGLISH-PASSMARKS.md')]
 rc=1
 try:
  p=subprocess.Popen(cmd,env=env)
  try:rc=p.wait(timeout=1000 if a.mode=='diagnostic' else 3100)
  except subprocess.TimeoutExpired:
   p.terminate()
   try:rc=p.wait(timeout=90)
   except subprocess.TimeoutExpired:p.kill();rc=p.wait()
 finally:
  record={'returncode':rc,'wall_seconds':time.monotonic()-start,'job':a.job,'hashes':{x.name:digest(x) for x in out.iterdir() if x.is_file()},'DEV_examples':0,'parent_reader_LM_frozen':True,'output_bytes':sum(x.stat().st_size for x in own.glob('*v7-*/*') if x.is_file())}
  (out/'TRANSPORT-RESULT.json').write_text(json.dumps(record,indent=2)+'\n')
  with tarfile.open(root/(out.name+'-raw.tar.gz'),'w:gz') as t:
   for x in out.iterdir():
    if x.is_file() and x.suffix not in ('.pt','.tmp'):t.add(x,arcname=str(x.relative_to(root)),recursive=False)
  print(json.dumps(record),flush=True)
 if record['output_bytes']>256*1024**2:raise RuntimeError('256MiB aggregate followup output cap')
 return rc
