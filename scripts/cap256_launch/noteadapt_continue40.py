"""Literal saved-Adam continuation: four TRAIN fits to40visits, then TRAIN-only endpoints."""
import argparse
import datetime
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import sys
import time


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def read(path):return json.loads(Path(path).read_bytes())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def validate(p):
    assert p['schema']=='cap256.noteadapt.continuation40.release.v1'
    assert p['seeds']==[0,1] and p['placements']==['notebook','inline']
    assert p['start_cursor']==128 and p['end_cursor']==1280 and p['updates_per_fit']==1152
    assert p['TRAIN_cases']==32 and p['native_calls']==128 and p['fixed_rounds']==4 and p['batch']==1
    assert p['optimizer']=={'lr':0.001,'weight_decay':0,'betas':[0.9,0.999],'eps':1e-8,'clip':1,'reset':False}
    assert p['fit_seconds']==600 and p['fit_total_seconds']==2400 and p['eval_seconds']==600
    assert p['output_cap_bytes']==512*2**20 and p['reserve_bytes']==2**30 and p['project_cap_bytes']==100*2**30
    assert p['checkpoint_cap_bytes']==108*2**20 and p['telemetry_cap_bytes']==64*2**20
    assert len(p['train_case_ids'])==len(set(p['train_case_ids']))==32
    assert {(v['seed'],v['placement']) for v in p['resumes']}=={(s,t) for s in [0,1] for t in ['notebook','inline']}
    assert len(p['resumes'])==4 and p['TEST_calls']==0
    return p


def equal_state(a,b,torch):
    if torch.is_tensor(a):return torch.is_tensor(b) and torch.equal(a.detach().cpu(),b.detach().cpu())
    if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(equal_state(a[k],b[k],torch) for k in a)
    if isinstance(a,(list,tuple)):return type(a)==type(b) and len(a)==len(b) and all(equal_state(x,y,torch) for x,y in zip(a,b))
    return a==b


def run(a):
    root=Path(a.root).resolve();p=validate(read(a.plan));assert sha(a.plan)==a.plan_sha256
    assert os.environ['TREE']==str(root) and os.environ['JOB']
    def pin(v):
        f=(root/v['path']).resolve();assert f.is_relative_to(root) and sha(f)==v['sha256'];return f
    for v in p['file_pins']:pin(v)
    for entry in p['parents']:
        m=read(pin(entry['manifest']));assert m['seed']==entry['seed'] and m['arm']=='loop' and m['update']==10240
        assert m['checkpoint']==entry['checkpoint'] and sha(m['checkpoint']['path'])==m['checkpoint']['sha256']
        for v in m['continuation'].values():assert sha(v['path'])==v['sha256']
        for n,h in m['code_pins'].items():assert sha(root/n)==h
    train=[json.loads(s) for s in pin(p['data']['TRAIN']['inputs']).read_text().splitlines()]
    trainlabels=[json.loads(s) for s in pin(p['data']['TRAIN']['targets']).read_text().splitlines()]
    assert [r['id'] for r in train]==p['train_case_ids'] and len(trainlabels)==32
    for row,y in zip(train,trainlabels):
        assert row['assignment']=='TRAIN' and row['stage']==y['stage']=='initial' and row['episode_id']==y['episode_id']
        assert y['answerability'] is True and type(y['numeric_target']) is str
        assert row['declared_source_eligibility'] is True and row['execution_eligible'] is False and row['training_eligible'] is False
    for v in p['resumes']:
        assert sha(v['checkpoint']['path'])==v['checkpoint']['sha256']
        assert sha(v['closed']['path'])==v['closed']['sha256']
        assert sha(v['input_frames']['path'])==v['input_frames']['sha256']
    spec=importlib.util.spec_from_file_location('_sealed_resource',root/'scripts/sol_cloud_capability256_v1.py');sealed=importlib.util.module_from_spec(spec);spec.loader.exec_module(sealed)
    matrix=root/p['output_namespace'];assert not matrix.exists(),'prior output; no duplicate'
    unit=sealed.filesystem_allocation_unit(root)
    def resource(extra=0):
        assert shutil.disk_usage(root).free>=p['reserve_bytes']+extra
        assert sealed.allocated_bytes(root,unit)+extra<=p['project_cap_bytes']
        assert sealed.allocated_bytes(matrix,unit)+extra<=p['output_cap_bytes']
    resource(p['output_cap_bytes']);matrix.mkdir(parents=True)
    identity={'schema':'cap256.noteadapt.continuation40.identity.v1','job':os.environ['JOB'],'plan_sha256':a.plan_sha256}
    def write(directory,name,value,append=False):
        b=(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()
        resource(len(b)+unit)
        telemetry=sum(((f.stat().st_size+unit-1)//unit)*unit for f in matrix.rglob('*') if f.is_file() and f.suffix not in ('.pt','.tmp'))
        assert telemetry+len(b)+unit<=p['telemetry_cap_bytes']
        with (directory/name).open('ab' if append else 'xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
    write(matrix,'CLAIM.json',{**identity,'utc':now(),'updates_expected':4608,'native_calls_expected':128,'no_duplicate_or_adaptive_retry':True})
    updates=0;native_calls=0;started=time.monotonic();fits=[]
    try:
        sys.path[:0]=[str(root),str(root/'scripts')]
        import torch
        from sol_nextdemo_runtime_v1 import Runtime
        from sol_translator_grounding_v6 import human_loss
        from sol_translator_runtime import component_fingerprint
        assert torch.cuda.is_available() and torch.cuda.get_device_properties(0).total_memory<=16*2**30
        def fingerprints(r):return {k:component_fingerprint(v) for k,v in {'core':r['core'],'reader':r['reader'],'prefix':r['dec'].adapter,'lm':r['dec'].lm}.items()}
        def literal(row,placement,full=True):
            # No IDs, order, givens, labels, answers or derived information here.
            if not full:return row['question'],''
            return (row['question'],row['history']) if placement=='notebook' else (row['history']+'\n'+row['question'],'')
        def tokenized(r,row,placement):
            q,c=literal(row,placement);tok=r['tok']
            assert len(tok.encode(q,add_special_tokens=False))+1<=48 and len(tok.encode(c,add_special_tokens=False))<=512
            return r['tokenize'](tok,{'question':q,'context':c},'cuda',max_question=48,max_context=512)
        for entry in p['parents']:
            seed=entry['seed']
            for placement in p['placements']:
                armstart=time.monotonic();assert armstart-started<2400
                out=matrix/('seed%d'%seed)/placement;out.mkdir(parents=True)
                armidentity={**identity,'seed':seed,'placement':placement,'parent_checkpoint':entry['checkpoint'],'optimizer_reset':False,'core_only':True}
                write(out,'LAUNCH.json',{**armidentity,'utc':now()})
                runtime=Runtime(str(pin(entry['manifest'])),entry['manifest']['sha256']);r=runtime.r;core=r['core'];lm=r['dec'].lm
                resume=next(v for v in p['resumes'] if v['seed']==seed and v['placement']==placement)
                original_closed=read(resume['closed']['path'])
                parent=torch.load(resume['checkpoint']['path'],map_location='cpu',weights_only=True)
                assert parent['updates']==128 and parent['constructor']==core.constructor()
                assert parent['schema']=='cap256.noteadapt.initial-only.checkpoint.v2' and parent['seed']==seed and parent['placement']==placement
                assert parent['plan_sha256']==p['source_plan_sha256'] and parent['parent_checkpoint']==entry['checkpoint']
                assert original_closed['checkpoint']==resume['checkpoint'] and original_closed['closed']
                for name,module in [('core',core),('reader',r['reader']),('prefix',r['dec'].adapter)]:
                    module.load_state_dict(parent[name],strict=True)
                    assert equal_state(module.state_dict(),parent[name],torch)
                before=fingerprints(r);assert before==parent['fingerprints']==original_closed['final_fingerprints']
                rng=(parent['torch_rng'],parent['cuda_rng'],parent['python_rng'])
                core.train().requires_grad_(True);core.halt.requires_grad_(False)
                named=[('core.'+n,v) for n,v in core.named_parameters() if v.requires_grad];params=[v for _,v in named]
                assert [n for n,_ in named]==parent['optimizer_parameter_names']
                opt=torch.optim.AdamW(params,lr=0.001,weight_decay=0,betas=(0.9,0.999),eps=1e-8)
                opt.load_state_dict(parent['optimizer']);assert equal_state(opt.state_dict(),parent['optimizer'],torch)
                assert len(opt.param_groups)==1
                group=opt.param_groups[0];assert group['lr']==.001 and group['weight_decay']==0 and group['betas']==(.9,.999) and group['eps']==1e-8
                saved_frames=[json.loads(s) for s in Path(resume['input_frames']['path']).read_text().splitlines()]
                frames=[]
                for row,y in zip(train,trainlabels):
                    ids,valid,mids,mvalid=tokenized(r,row,placement)
                    label=r['tok'].encode(y['numeric_target'],add_special_tokens=False)+[r['dec'].eos_id]
                    assert label and len(label)<=64
                    with torch.no_grad():
                        query=r['reader'](lm.get_input_embeddings()(ids),valid)
                        memo=r['reader'](lm.get_input_embeddings()(mids),mvalid).flatten(1,2) if mids.shape[1] else None
                    frame={'id':row['id'],'input_ids':ids.cpu().tolist(),'input_mask':valid.cpu().tolist(),'notebook_ids':mids.cpu().tolist(),'notebook_mask':mvalid.cpu().tolist(),'labels':[label],'label_mask':[[True]*len(label)],'question_sha256':hashlib.sha256(literal(row,placement)[0].encode()).hexdigest(),'history_sha256':hashlib.sha256(row['history'].encode()).hexdigest()}
                    frame['frame_sha256']=digest(frame);write(out,'INPUT-FRAMES.jsonl',frame,True)
                    assert frame==saved_frames[len(frames)]
                    frames.append((query,memo,valid,mvalid,torch.tensor([label],device='cuda'),frame))
                initial_rng=digest({'torch':sha_bytes(rng[0].numpy().tobytes()),'cuda':[sha_bytes(v.numpy().tobytes()) for v in rng[1]],'python':repr(rng[2])})
                write(out,'INITIAL-STATE.json',{**armidentity,'fingerprints':before,'RNG_sha256':initial_rng,'Adam_state_entries':len(opt.state),'trainable_names':[n for n,_ in named],'train_schedule_sha256':digest(p['train_case_ids']*36)})
                torch.set_rng_state(rng[0]);torch.cuda.set_rng_state_all(rng[1]);random.setstate(rng[2])
                assert torch.equal(torch.get_rng_state(),rng[0]) and equal_state(torch.cuda.get_rng_state_all(),rng[1],torch) and random.getstate()==rng[2]
                write(out,'RESUME-VERIFIED.json',{**armidentity,'utc':now(),'source_checkpoint':resume['checkpoint'],'cursor':128,'next_id':p['train_case_ids'][0],'full_model_Adam_RNG_equal':True,'saved_Adam_entries':len(opt.state),'source_steps':[int(v['step']) for v in opt.state.values()]})
                del rng,parent,saved_frames
                for step in range(129,1281):
                    assert time.monotonic()-armstart<600 and time.monotonic()-started<2400
                    query,memo,valid,mvalid,label,frame=frames[(step-1)%32]
                    opt.zero_grad(set_to_none=True)
                    with r['ordered_math']():h,_,aux=r['fixed4'](core,query,memo,query_mask=valid,notebook_mask=mvalid if memo is not None else None)
                    prefix=r['dec'].adapter.project_training(h,torch.ones_like(h,dtype=torch.bool),valid,(1,h.shape[1]))
                    per,pred=human_loss(lm,prefix,label,r['dec'].bos_id,r['dec'].eos_id,True,True)
                    preclip=sealed.numeric_optimizer_step(per.mean(),opt,params,torch)
                    torch.cuda.synchronize();updates+=1
                    assert not any(v.grad is not None for module in (r['reader'],r['dec']) for v in module.parameters())
                    write(out,'TRAIN-RAW.jsonl',{**armidentity,'update':step,'id':frame['id'],'visit':(step-1)//32+1,'numeric_CE':float(per.mean().detach()),'preclip_norm':float(preclip),'objective':'numeric-answer-CE-only','auxiliary_weight':0,'router_auxiliary_observed_excluded':float(aux.detach()),'frame_sha256':frame['frame_sha256'],'teacherforced_argmax':pred.cpu().tolist()},True)
                    if step==129:write(matrix,'FIRST-OPTIMIZER-s%d-%s.json'%(seed,placement),{**armidentity,'utc':now(),'completed_update':129,'additional_updates':1})
                after=fingerprints(r);assert all(before[k]==after[k] for k in ['reader','prefix','lm'])
                checkpoint={**armidentity,'schema':'cap256.noteadapt.continuation40.checkpoint.v1','updates':1280,'source_checkpoint':resume['checkpoint'],'constructor':core.constructor(),'core':core.state_dict(),'reader':r['reader'].state_dict(),'prefix':r['dec'].adapter.state_dict(),'optimizer':opt.state_dict(),'optimizer_parameter_names':[n for n,_ in named],'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all(),'python_rng':random.getstate(),'fingerprints':after,'TRAIN_raw_sha256':sha(out/'TRAIN-RAW.jsonl')}
                saved=out/'final-resume.pt'
                def before_extent(extent):
                    temporary=saved.with_suffix('.pt.tmp');actual=temporary.stat().st_size
                    rounded=lambda n:((n+unit-1)//unit)*unit
                    resource(max(0,rounded(max(actual,extent))-rounded(actual)))
                sealed.save_new_atomic_file(saved,p['checkpoint_cap_bytes'],lambda sink:torch.save(checkpoint,sink),before_extent)
                check=torch.load(saved,map_location='cpu',weights_only=True)
                for name,module in [('core',core),('reader',r['reader']),('prefix',r['dec'].adapter)]:assert all(torch.equal(check[name][k],v.detach().cpu()) for k,v in module.state_dict().items())
                original=opt.state_dict();assert check['optimizer_parameter_names']==[n for n,_ in named]
                for k,state in original['state'].items():assert all(torch.equal(check['optimizer']['state'][k][n],v.detach().cpu()) if torch.is_tensor(v) else check['optimizer']['state'][k][n]==v for n,v in state.items())
                assert time.monotonic()-armstart<600 and time.monotonic()-started<2400
                closed={**armidentity,'closed':True,'optimizer_updates':1152,'visits_each':40,'start_cursor':128,'end_cursor':1280,'source_checkpoint':resume['checkpoint'],'checkpoint':{'path':str(saved),'sha256':sha(saved)},'TRAIN_raw_sha256':sha(out/'TRAIN-RAW.jsonl'),'input_frames_sha256':sha(out/'INPUT-FRAMES.jsonl'),'frozen_fingerprints_unchanged':True,'initial_fingerprints':before,'final_fingerprints':after,'durable_reload_equal':True,'wall_seconds':time.monotonic()-armstart}
                write(out,'FIT-CLOSED.json',closed);fits.append(closed)
                del check,original,checkpoint,opt,frames,core,lm,params,named,r,runtime;gc.collect();torch.cuda.empty_cache()
        assert updates==4608 and len(fits)==4
        evalstart=time.monotonic();write(matrix,'TRAIN-ENDPOINT-CLAIM.json',{**identity,'utc':now(),'TRAIN_cases_each':32,'native_calls_expected':128,'TEST_calls':0})
        import sol_cloud_numeric_fit_v2 as observer
        original_observe=observer.observe_generation;active_train={}
        def tracked_observe(*args,**kwargs):
            nonlocal native_calls
            assert native_calls<128 and time.monotonic()-evalstart<600
            observed=original_observe(*args,**kwargs);native_calls+=1
            write(matrix,'TRAIN-NATIVE-RAW.jsonl',{**identity,**active_train,'native_call_index':native_calls,'observed':observed},True)
            return observed
        observer.observe_generation=tracked_observe
        for fit in fits:
            seed,placement=fit['seed'],fit['placement'];entry=p['parents'][seed]
            assert sha(fit['checkpoint']['path'])==fit['checkpoint']['sha256']
            runtime=Runtime(str(pin(entry['manifest'])),entry['manifest']['sha256']);r=runtime.r
            adapted=torch.load(fit['checkpoint']['path'],map_location='cpu',weights_only=True)
            assert adapted['schema']=='cap256.noteadapt.continuation40.checkpoint.v1' and adapted['updates']==1280
            for name,module in [('core',r['core']),('reader',r['reader']),('prefix',r['dec'].adapter)]:module.load_state_dict(adapted[name],strict=True);module.eval().requires_grad_(False)
            assert fingerprints(r)==fit['final_fingerprints'];runtime.manifest['checkpoint']=fit['checkpoint'];del adapted
            for row,y in zip(train,trainlabels):
                assert time.monotonic()-evalstart<600 and time.monotonic()-started<3000
                with torch.no_grad():
                    ids,valid,mids,mvalid=tokenized(r,row,placement)
                    query=r['reader'](r['dec'].lm.get_input_embeddings()(ids),valid)
                    memo=r['reader'](r['dec'].lm.get_input_embeddings()(mids),mvalid).flatten(1,2) if mids.shape[1] else None
                    with r['ordered_math']():h,_,_=r['fixed4'](r['core'],query,memo,query_mask=valid,notebook_mask=mvalid if memo is not None else None)
                    prefix=r['dec'].adapter.project_training(h,torch.ones_like(h,dtype=torch.bool),valid,(1,h.shape[1]))
                    labels=r['tok'].encode(y['numeric_target'],add_special_tokens=False)+[r['dec'].eos_id]
                    per,pred=human_loss(r['dec'].lm,prefix,torch.tensor([labels],device='cuda'),r['dec'].bos_id,r['dec'].eos_id,True,True)
                    write(matrix,'TRAIN-ENDPOINT-TEACHERFORCED.jsonl',{**identity,'seed':seed,'placement':placement,'id':row['id'],'numeric_CE':float(per.mean()),'teacherforced_argmax':pred.cpu().tolist(),'label_sha256':digest([labels])},True)
                q,c=literal(row,placement);active_train.update(seed=seed,placement=placement,id=row['id'])
                answer=runtime.answer(q,c,'full')
                assert answer['rounds']==4 and answer['optimizer_updates']==0
                write(matrix,'TRAIN-ENDPOINT-RAW.jsonl',{**identity,'seed':seed,'placement':placement,'id':row['id'],'native_call_index':native_calls,'answer':answer},True)
            assert fingerprints(r)==fit['final_fingerprints']
            del r,runtime;gc.collect();torch.cuda.empty_cache()
        assert native_calls==128
        for v in p['resumes']:assert sha(v['checkpoint']['path'])==v['checkpoint']['sha256'] and sha(v['closed']['path'])==v['closed']['sha256']
        write(matrix,'CLOSED.json',{**identity,'closed':True,'optimizer_updates':updates,'native_calls':native_calls,'TEST_calls':0,'fits':fits,'TRAIN_endpoint_raw_sha256':sha(matrix/'TRAIN-ENDPOINT-RAW.jsonl'),'TRAIN_native_raw_sha256':sha(matrix/'TRAIN-NATIVE-RAW.jsonl'),'TRAIN_teacherforced_raw_sha256':sha(matrix/'TRAIN-ENDPOINT-TEACHERFORCED.jsonl'),'wall_seconds':time.monotonic()-started,'eval_wall_seconds':time.monotonic()-evalstart,'peak_cuda_allocated_bytes':torch.cuda.max_memory_allocated(),'generalization_claim':False})
    except Exception as ex:
        write(matrix,'FAILED.json',{**identity,'utc':now(),'optimizer_updates':updates,'native_calls':native_calls,'error_type':type(ex).__name__,'error':str(ex)});raise


def sha_bytes(b):return hashlib.sha256(b).hexdigest()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--plan',required=True);parser.add_argument('--plan-sha256',required=True);run(parser.parse_args())
