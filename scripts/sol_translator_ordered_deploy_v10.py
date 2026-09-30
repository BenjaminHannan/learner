"""Queued ordered joint training: full FP32, real512graph probe, durable lineage."""
import json,os,shutil,subprocess,sys,tarfile,time
from pathlib import Path
from sol_translator_provenance import sha

def run(a):
 root=Path(a.root).resolve();own=root/'artifacts/sol-translator-20260929';os.chdir(root)
 seal=json.loads((own/'ORDERED-GROUND-V10-SEAL.json').read_text())
 for p,v in seal['files'].items():assert sha(root/p)==v,'PIN '+p
 assert shutil.disk_usage(root).free>=2*1024**3,'2GiB free floor'
 sources=json.loads((own/'ORDERED-GROUND-V10-WARMSTART.json').read_text())['per_seed'][str(a.seed)]
 for k in ('source','reader','prefix'):
  assert sha(sources[k+'_path'])==sources[k+'_sha256'],'warmstart CLOSED tuple '+k
 out=own/f'ground-ordered-v10-s{a.seed}-loop';out.mkdir(parents=True,exist_ok=True)
 assert not (out/'LAUNCH.json').exists(),'closed/new job or explicit new resume version only'
 env=dict(os.environ,PYTHONPATH=str(root)+os.pathsep+str(root/'scripts'),JOB=a.job,TREE=str(root),PYTHONUTF8='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
 start=time.monotonic();(out/'LAUNCH.json').write_text(json.dumps({'job':a.job,'seed':a.seed,'stage':'ordered final4 joint HUMAN TRAIN','seal_sha256':sha(own/'ORDERED-GROUND-V10-SEAL.json'),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'warmstart':sources,'DEV_examples':0,'sleep_updates':0,'precision':'FULL FP32 frozen LFM embedding/head/all parameters; thin reader/core/prefix trainable'})+'\n')
 lm='C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b'
 common=['--model',lm,'--model-provenance',str(own/'CACHED-LFM-ORIGINAL-PROVENANCE.json'),'--source',sources['source_path'],'--reader',sources['reader_path'],'--prefix',sources['prefix_path'],'--seed',str(a.seed),'--family','loop','--out',str(out),'--device','cuda']
 rc=1
 try:
  subprocess.run([sys.executable,'-X','utf8','-B','scripts/sol_translator_ground_ordered_v10.py','memory']+common,check=True,env=env,timeout=350)
  proc=subprocess.Popen([sys.executable,'-X','utf8','-B','scripts/sol_translator_ground_ordered_v10.py','train']+common,env=env)
  try:rc=proc.wait(timeout=2800)
  except subprocess.TimeoutExpired:
   proc.terminate()
   try:rc=proc.wait(timeout=90)
   except subprocess.TimeoutExpired:proc.kill();rc=proc.wait()
  if rc==0 and json.loads((out/f'grounding-s{a.seed}.json').read_text()).get('closed'):
   # Exact trained tuple config, emitted only after CLOSED positive actual500.
   config={'factory':'scripts.sol_translator_runtime_ordered_v10:load_d256_notebook_factories','runtime_factory_sha256':sha(root/'scripts/sol_translator_runtime_ordered_v10.py'),'stop_factory_sha256':sha(root/'scripts/sol_stop_ordered_api2.py'),'ordered_core_sha256':sha(root/'scripts/sol_spatial_poc_ordered_v2.py'),'order_contract':'sol-ordered-notebook-v2','reader_version':'human-notebook-v2','lm_path':lm,'lm_provenance':str(own/'CACHED-LFM-ORIGINAL-PROVENANCE.json'),'device':'cuda','semantic_status':'UNQUALIFIED until actual allowed-input diagnostic; fixed4 unqualified learnedstop','grounding_updates_measured':500}
   for k,name in [('parent',f'parent-s{a.seed}.pt'),('reader',f'input-s{a.seed}.pt'),('adapter',f'bootstrap-English-s{a.seed}.pt')]:config[k+'_path']=str(out/name);config[k+'_sha256']=sha(out/name)
   (out/'runtime-config.json').write_text(json.dumps(config,indent=2)+'\n')
   bind=dict(parent_sha256=config['parent_sha256'],reader_sha256=config['reader_sha256'],bootstrap_sha256=config['adapter_sha256'],LM_provenance_sha256=sha(own/'CACHED-LFM-ORIGINAL-PROVENANCE.json'),runtime_factory_sha256=config['runtime_factory_sha256'],stop_factory_sha256=config['stop_factory_sha256'],order_contract=config['order_contract'])
   (out/'DIAGNOSTIC-BINDING.json').write_text(json.dumps(bind,indent=2)+'\n')
   subprocess.run([sys.executable,'-X','utf8','-B','scripts/sol_translator_diagnostic_ordered_v10.py','--model',lm,'--model-provenance',config['lm_provenance'],'--parent',config['parent_path'],'--reader',config['reader_path'],'--bootstrap',config['adapter_path'],'--binding',str(out/'DIAGNOSTIC-BINDING.json'),'--plan',str(own/'ORDERED-GROUND-V10-DIAGNOSTIC-PLAN.json'),'--seed',str(a.seed),'--out',str(own/f'ordered-diagnostic-v10-s{a.seed}'),'--device','cuda'],check=True,env=env,timeout=450)
 except Exception as exc:
  rc=1
  (out/'TRANSPORT-FAILURE.json').write_text(json.dumps({'error':str(exc),'type':type(exc).__name__,'phase':'memory/TRAIN/diagnostic; raw preserved'})+'\n')
 finally:
  # No LM duplicate: only new trainable exports/resume and raw copied.
  record={'returncode':rc,'seed':a.seed,'wall_seconds':time.monotonic()-start,'paths_and_hashes':{str(p.relative_to(root)):sha(p) for p in out.iterdir() if p.is_file()},'stage':'TRAIN+TRAIN-only diagnostic; no DEV/sleep/no semantic promotion','DEV_examples':0}
  (out/'TRANSPORT-RESULT.json').write_text(json.dumps(record,indent=2)+'\n')
  with tarfile.open(root/f'ordered-raw-s{a.seed}.tar.gz','w:gz') as t:
   for directory in (out,own/f'ordered-diagnostic-v10-s{a.seed}'):
    if directory.exists():
     for p in directory.iterdir():
      if p.is_file() and p.suffix not in ('.pt','.tmp'):t.add(p,arcname=str(p.relative_to(root)),recursive=False)
  print(json.dumps(record),flush=True)
 return rc
