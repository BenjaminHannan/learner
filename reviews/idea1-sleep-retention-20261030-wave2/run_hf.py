import argparse,hashlib,json,os,random,sys,time,traceback
from pathlib import Path
from datetime import datetime,timezone
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--allow-model-load',action='store_true');p.add_argument('--dry-run',action='store_true');p.add_argument('--arm',choices=['on','off'],default='on');p.add_argument('--cap-s',type=float,default=1800);p.add_argument('--seed',type=int,default=0);a=p.parse_args();r=a.root.resolve();plan=json.loads((r/'preregistration.json').read_text());manifest=json.loads((r/'source-manifest.json').read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for x in iter(lambda:f.read(8*1024*1024),b''):h.update(x)
 return h.hexdigest()
for rel,h in manifest.items():assert sha(r/'src'/rel)==h,rel
assert len(plan['blocks'])==3 and all(len(x)==3 for x in plan['blocks'])
if a.dry_run:print(json.dumps({'dry_run':True,'no_model_load':True,'source_files':len(manifest),'facts':9,'phases':3,'steps':24}));raise SystemExit
if not a.allow_model_load:p.error('root resource authorization required')
assert not (r/'HF-report.json').exists();started=time.monotonic();deadline=time.time()+min(a.cap_s,plan['absolute_total_cap_s'])
for k in list(os.environ):
 if k.startswith(('SLEEP','LEARNER_OPS','HF_','TRANSFORMERS_')) or k in ('PYTHONPATH','PYTHONHOME','TORCH_HOME'):os.environ.pop(k,None)
for key,leaf in {'SLEEPMLX_HOME':'sleepmlx','SLEEPMLX_DIARY_DIR':'diary','SLEEPMLX_USERDATA':'userdata','LEARNER_OPS':'ops','LEARNER_OPS_HOME':'ops-home','SLEEPMODE_HOME':'mode-home','SLEEPMODE_OPS':'mode-ops','SLEEPMODE_OUT':'mode-out','HF_HOME':'hf','HF_MODULES_CACHE':'hf-modules','TORCH_HOME':'torch'}.items():os.environ[key]=str(r/'isolated-home'/leaf)
os.environ.update(CUDA_VISIBLE_DEVICES='-1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONNOUSERSITE='1');sys.path.insert(0,str(r/'src'));report={'arm':a.arm,'seed':a.seed,'experiment':plan['experiment'],'quality_claim':False,'partial':True,'plan_sha256':sha(r/'preregistration.json'),'source_manifest_sha256':sha(r/'source-manifest.json'),'checkpoints':[],'phases':[]};backend=None

def save():
 report['elapsed_s']=time.monotonic()-started;tmp=r/'HF-report.json.tmp';tmp.write_text(json.dumps(report,indent=2));os.replace(tmp,r/'HF-report.json')
import shutil
def check():
 if time.time()>=deadline:raise TimeoutError('absolute total deadline')
 if shutil.disk_usage('/System/Volumes/Data').free<2*1024**3:raise RuntimeError('ABORT: free disk under 2 GiB')
try:
 assert sha(a.model_dir/'model.safetensors')=='135922caef64e81e52af88ede8b7c3ddaa9d6da220a9737fb3065275dbfb4330';report['HF_weights_sha256']=sha(a.model_dir/'model.safetensors')
 import torch,transformers,peft
 torch.set_num_threads(2);torch.set_num_interop_threads(2);assert torch.version.cuda is None;random.seed(a.seed);torch.manual_seed(a.seed)
 from sleepmlx import gate,replay,grading
 from sleepmlx.profile import load_profile,Renderer
 from sleepmlx.worker import make_backend
 from sleepmlx.recipe import GENERIC_PROMPTS
 assert gate.GRADER=='strict-4';report.update(grading.binding());report['runtime']={'torch':torch.__version__,'transformers':transformers.__version__,'peft':peft.__version__,'threads':torch.get_num_threads(),'interop_threads':torch.get_num_interop_threads(),'cuda':torch.version.cuda};profile=load_profile('lfm3_mps',{'SLEEPMLX_MODEL_DIR':str(a.model_dir.resolve())});profile.lora['rank']=8;profile.runtime['threads']=2
 backend,tok=make_backend(profile,{'SLEEPMLX_GEN_BATCH':'1','SLEEPMLX_TOK_BUDGET':'256'});renderer=Renderer(profile,tok);assert backend.device=='mps' and backend.dtype==torch.float16 and backend.lora_cfg['rank']==8;report['runtime'].update(device=backend.device,dtype=str(backend.dtype),profile=profile.name,lora_rank=backend.lora_cfg['rank'])
 allfacts=[x for block in plan['blocks'] for x in block];general=gate.gate_questions(8);blocked=[q for q,_ in gate.GENERAL_QA]+[x for fact in allfacts for x in (fact[0],fact[2])];public=replay.public_questions(GENERIC_PROMPTS,blocked);assert not any(q in public for q in blocked)
 contexts=replay.prompt_examples(backend,[renderer.render('Answer with just the name.',q) for q in public],256);report['replay']={'mode':'prompt','examples':len(contexts),'public_prompts':public,'excludes_all9_train_and_held_and_general':True};report['identity']=replay.reference_identity(backend,renderer);backend.save_adapter(r/'initial-adapter');report['initial_adapter_files']={p.name:sha(p) for p in (r/'initial-adapter').iterdir() if p.is_file()}
 def evaluate(phase):
  cp={'phase':phase,'held':[],'general':[]}
  for i,(train,ans,q) in enumerate(allfacts):
   check();text=backend.generate([renderer.render('Answer with just the name.',q)],32,temp=0,adapter=True)[0];cp['held'].append({'block':i//3,'q':q,'a':ans,'out':text,'hit':gate.recall_hit(ans,text,q)})
  for q,acc in general:
   check();text=backend.generate([renderer.render(gate.GATE_SYS,q)],32,temp=0,adapter=True)[0];cp['general'].append({'q':q,'a':acc,'out':text,'hit':gate.correct(text,acc,q)})
  cp['held_hits']=sum(x['hit'] for x in cp['held']);cp['general_hits']=sum(x['hit'] for x in cp['general']);cp['elapsed_s']=time.monotonic()-started
  if phase:
   prev=report['checkpoints'][-1];baseline=report['checkpoints'][0];block=phase-1
   cp['new_block_gain']=sum(x['hit'] for x in cp['held'] if x['block']==block)-sum(x['hit'] for x in prev['held'] if x['block']==block)
   cp['previously_correct_old_fact_losses']=[z['q'] for z,b in zip(cp['held'],prev['held']) if z['block']<block and b['hit'] and not z['hit']]
   cp['previously_correct_general_losses_vs_baseline']=[z['q'] for z,b in zip(cp['general'],baseline['general']) if b['hit'] and not z['hit']]
   cp['previously_correct_general_losses_vs_previous_phase']=[z['q'] for z,b in zip(cp['general'],prev['general']) if b['hit'] and not z['hit']]
  report['checkpoints'].append(cp);save()
 evaluate(0);rng=random.Random(a.seed)
 import subprocess,re
 vm=subprocess.check_output(['vm_stat'],text=True);page=int(re.search(r'page size of (\d+) bytes',vm).group(1)); counts={k:int(v) for k,v in re.findall(r'Pages (free|inactive|purgeable):\s+(\d+)',vm)};available=sum(counts.values())*page
 pressure=int(subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True).strip());report['pre_training_memory']={'available_bytes':available,'pressure_level':pressure};save()
 if available<7*1024**3 or pressure>=4:raise RuntimeError('pre-training memory requirement not met')
 card_rng=random.Random(a.seed)
 for phase,block in enumerate(plan['blocks'],1):
  batch=[]
  for q,ans,_ in [fact for b in plan['blocks'][:phase] for fact in b]:
   prompt=backend.encode(renderer.render('Answer with just the name.',q));target=backend.encode(profile.training_answer_prefix+ans)+[backend.stop_id];assert len(prompt)+len(target)<=256;batch.append((prompt+target,len(prompt)))
  backend.train_begin(24,2e-4);entry={'phase':phase,'pool_blocks':phase,'selection':'3 distinct cards from cumulative pool', 'selected':[],'optimizer_reset':True,'losses':[]};report['phases'].append(entry)
  phase_started=time.monotonic();entry['phase_started_elapsed_s']=phase_started-started;save()
  for step in range(24):
   check();chosen=batch if phase==1 else (card_rng.sample(batch,3) if a.arm=='on' else batch[-3:]);entry['selected'].append([batch.index(x) for x in chosen]);step_started=time.monotonic();loss=backend.train_step(chosen,rng.sample(contexts,min(4,len(contexts))),step);torch.mps.synchronize();step_s=time.monotonic()-step_started
   if step==0:entry['first_step_s']=step_s;entry['watchdog_s']=24*step_s+120
   entry.setdefault('step_seconds',[]).append(step_s);assert backend.tok_budget==256 and backend.gen_batch==1;entry['losses'].append(loss);entry['completed_updates']=step+1;report['completed_updates_total']=sum(len(x['losses']) for x in report['phases']);save()
  entry['training_wall_s']=time.monotonic()-phase_started;save()
  path=r/('phase-'+str(phase)+'-adapter');backend.save_adapter(path);entry['adapter_files']={p.name:sha(p) for p in path.iterdir() if p.is_file()};entry['lora_b_nonzero']=sum(int(torch.count_nonzero(v).item()) for n,v in backend.model.named_parameters() if 'lora_B' in n);save();evaluate(phase)
 report['partial']=False
except BaseException as error:report['error']=type(error).__name__+': '+str(error);report['traceback']=traceback.format_exc();raise
finally:
 if backend is not None:
  if report.get('partial') and report.get('completed_updates_total',0)>0:
   try:backend.save_adapter(r/'partial-adapter')
   except Exception as error:report['partial_save_error']=str(error)
  backend.close()
 save()
