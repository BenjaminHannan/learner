"""Saved original/candidate/resume numeric inspection only; no model imports/forward."""
from pathlib import Path
import argparse,datetime,hashlib,json,math
import torch
ROOT=Path('/workspace/learner');OWN=ROOT/'artifacts/sol-cloud-verifier-20260930'
META=ROOT/'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/recovered-v3-small/cloud-recovery/copied/artifacts/sol-cloud-night-20260930/run-v3'
EXPECTED={'candidate-parent.pt':'5cddc77e9068f0e8336a8f65bc079c3747c23d3137596c77317508d04d80a485','candidate-English.pt':'0dca989339b758e51a773548300dada8c00f128901427d71fef671d570143967','night-resume.pt':'6be188a0cab8dc17a08936849123d7aa77cd80aaf7edb44830a283e75d5bab5e','source-parent.pt':'e7aef267c0ba32aec41f01054d019317b6025e3d29b47de88c31e136a598d925'}
def file_sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as stream:
  for b in iter(lambda:stream.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def state_sha(state):
 h=hashlib.sha256()
 for name,tensor in sorted(state.items()):
  h.update((name+':'+str(tensor.dtype)+':'+str(tuple(tensor.shape))).encode())
  h.update(tensor.detach().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
 return h.hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--raw-dir',required=True);args=parser.parse_args();raw=Path(args.raw_dir).resolve()
 assert raw.is_relative_to(ROOT/'artifacts') and not any(x in str(raw).lower() for x in ['uncle-questions','readpanel320','dev100','stop88','/blind/','/sealed'])
 out=OWN/'BRIDGE-V3-ACTUAL-TENSOR-RECOUNT-v1.json';assert not out.exists(),'preserve prior report'
 torch.set_num_threads(1);checks=[]
 def check(name,value):
  if not value:raise AssertionError(name)
  checks.append(name)
 payload={};records={}
 for name,pin in EXPECTED.items():
  path=raw/name;check('original_file_pin_'+name,file_sha(path)==pin)
  payload[name]=torch.load(path,weights_only=True,map_location='cpu')
  records[name]={'sha256':pin,'bytes':path.stat().st_size,'root_keys':list(payload[name])}
 original=payload['source-parent.pt'];candidate=payload['candidate-parent.pt'];resume=payload['night-resume.pt'];prefix=payload['candidate-English.pt']
 ledger=json.loads((META/'night-ledger.json').read_text());validation=json.loads((META/'validation.json').read_text());reported=validation['tensor_validation']
 check('constructor_preserved',original['constructor']==candidate['constructor'])
 before=original['state_dict'];after=candidate['state_dict'];saved=resume['core'];check('100_exact_state_names',before.keys()==after.keys()==saved.keys() and len(before)==100)
 archived={r['name']:r for r in reported['core_tensors']};actual=[]
 for name,old in before.items():
  new=after[name];restored=saved[name]
  check('cpu_finite_tensor_'+name,all(isinstance(t,torch.Tensor) and t.device.type=='cpu' and not t.requires_grad and bool(torch.isfinite(t).all()) for t in [old,new,restored]))
  check('shape_dtype_reload_'+name,old.shape==new.shape==restored.shape and old.dtype==new.dtype==restored.dtype and torch.equal(new,restored))
  changed=not torch.equal(old,new);a=state_sha({name:old});b=state_sha({name:new});record={'name':name,'shape':list(new.shape),'dtype':str(new.dtype),'changed':changed,'candidate_resume_exact':True,'before_sha256':a,'after_sha256':b,'finite':True}
  check('saved_tensor_record_matches_bytes_'+name,record==archived[name]);actual.append(record)
  if 'halt' in name or name in ['position_frequencies','boundary_roles']:check('frozen_halt_buffer_'+name,not changed)
 check('actual_core_fingerprints_match25update_chain',state_sha(before)==ledger['core_before']==reported['core_before'] and state_sha(after)==ledger['core_after']==reported['core_after'])
 check('90_actual_changed_tensors',sum(r['changed'] for r in actual)==reported['changed_core_tensors']==90)
 names=resume['optimizer_parameter_names'];optimizer=resume['optimizer'];ids=[i for g in optimizer['param_groups'] for i in g['params']];states=optimizer['state'];moments=[];dormant=[]
 check('96_optimizer_params90_saved_states',len(names)==len(ids)==len(set(ids))==96 and len(states)==90 and names==ledger['optimizer_parameter_names'] and set(names)<=set(before) and not any('halt' in name for name in names))
 check('one_optimizer_group_presealed_lr_wd',len(optimizer['param_groups'])==1 and optimizer['param_groups'][0]['lr']==1e-5 and optimizer['param_groups'][0]['weight_decay']==0.01)
 check('all_changed_tensors_optimizer_scoped',all(not r['changed'] or r['name'] in names for r in actual))
 for parameter_id,name in zip(ids,names):
  if parameter_id not in states:
   check('dormant_no_state_no_change_'+name,ledger['optimizer_participation_counts'][name]==0 and ledger['optimizer_nonzero_gradient_counts'][name]==0 and torch.equal(before[name],after[name]));dormant.append(name);continue
  state=states[parameter_id];check('exact_Adam_state_fields_'+name,set(state)=={'step','exp_avg','exp_avg_sq'})
  step=float(state['step']);check('actual_Adam25_participation_'+name,math.isfinite(step) and step==int(step)==25==ledger['optimizer_participation_counts'][name])
  for key in ['exp_avg','exp_avg_sq']:
   t=state[key];check('finite_aligned_CPU_moment_'+name+'_'+key,t.device.type=='cpu' and not t.requires_grad and t.shape==after[name].shape and t.dtype==after[name].dtype and bool(torch.isfinite(t).all()))
  check('nonzero_valid_second_moment_'+name,bool((state['exp_avg_sq']>=0).all()) and bool((state['exp_avg_sq']!=0).any()))
  record={'name':name,'parameter_id':parameter_id,'initial_step':0,'final_step':int(step),'exp_avg_sha256':state_sha({name:state['exp_avg']}),'exp_avg_sq_sha256':state_sha({name:state['exp_avg_sq']})};moments.append(record)
 check('actual90_Adam_moments_match_savedraw_report',moments==reported['Adam_states'])
 check('actual6_dormant_exact_report',dormant==reported['dormant_optimizer_parameters_unchanged'] and len(dormant)==6)
 check('durable_resume_metadata_exact',resume['ledger']==ledger and resume['binding_sha256']==ledger['binding_sha256'] and resume['frozen_component_fingerprints']==ledger['frozen_component_fingerprints'])
 check('prefix_adapter_saved_before_fingerprint',state_sha(prefix['adapter_state'])==ledger['frozen_component_fingerprints']['prefix'])
 check('prefix_bound_to_inactive_candidate',prefix['parent_sha256']==EXPECTED['candidate-parent.pt'] and prefix['training_stage']=='cloud-fixture-night-frozen-prefix-rebound-unqualified')
 check('all_four_bytes_still_pinned_after_load',all(file_sha(raw/name)==pin for name,pin in EXPECTED.items()))
 result={'schema':'sol.independent.actual-bridge-tensor-recount.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verdict':'PASS_ACTUAL_SAVED_TENSORS_AND_ADAM_RECOUNT','raw_directory':str(raw),'files':records,'python_torch':torch.__version__,'cuda_build':torch.version.cuda,'map_location':'cpu','weights_only':True,'deserialization_fallback':False,'model_source_imports':0,'model_forward_calls':0,'optimizer_calls':0,'rescoring':False,'checks':checks,'check_count':len(checks),'actual_state_tensors':100,'optimizer_eligible_parameters':96,'actual_changed_tensors':90,'actual_Adam_states':90,'each_Adam_final_step':25,'dormant_parameters_unchanged':dormant,'halt_tensors_frozen':2,'position_role_buffers_frozen':2,'core_before':state_sha(before),'core_after':state_sha(after),'candidate_resume_exact':True,'moment_records':moments,'tensor_records':actual,'actual_user_day':False,'activated':False,'limitations':['Saved original/candidate/resume byte and moment comparison, not a new model forward or training run.','Original output-prefix checkpoint was not amongfour recoveredfiles; candidate prefix matches archived before fingerprint but direct source-prefix bytes not compared.','Reader/LM frozen status remains source-reviewed and saved runtime evidence; their original tensors were not recovered.','Single source_seed0 engineering fixture; semantics, grammatical chat, liveuserday, learnedstopping, comparativegain/generalization NOTSHOWN.']}
 with out.open('x') as f:f.write(json.dumps(result,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'verdict':result['verdict'],'sha256':file_sha(out),'checks':len(checks),'state_tensors':100,'changed':90,'optimizer_params':96,'Adam_states':90,'finalsteps':25,'dormant':len(dormant)}))
if __name__=='__main__':main()
