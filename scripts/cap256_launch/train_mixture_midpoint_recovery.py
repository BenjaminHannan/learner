"""Frozen question-only mixture continuation; 10240 updates from original loop40."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
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


def validate_exposure(schedule,original,additional,arm):
    if len(original)!=256 or len(additional)!=256 or set(original)&set(additional):
        raise ValueError('TRAIN cohorts must be distinct256 rows')
    wanted=Counter({i:40 for i in original}) if arm=='repeat256' else Counter({i:20 for i in original+additional})
    if len(schedule)!=10240 or Counter(schedule)!=wanted:raise ValueError('fixed exposure differs')


def run(args):
    root=Path(args.root); cfg=read(args.config)
    if sha(args.config)!=args.config_sha256:raise RuntimeError('new config differs')
    source=root/cfg['source_plan']['path'];old=read(source)
    for name in ('source_plan','source_seal','source_release','source_runner'):
        pin=cfg[name]
        if sha(root/pin['path'])!=pin['sha256']:raise RuntimeError('source pin differs: '+name)
    seal=read(root/cfg['source_seal']['path'])
    for path,digest in seal['files'].items():
        if sha(root/path)!=digest:raise RuntimeError('sealed runtime source differs')
    spec=importlib.util.spec_from_file_location('_sealed_train',root/cfg['source_runner']['path'])
    sealed=importlib.util.module_from_spec(spec);spec.loader.exec_module(sealed)
    sealed.validate_plan(old)
    assert cfg['additional_updates']==10240 and cfg['lr']==0.001
    assert cfg['seeds']==[0,1] and cfg['arms']==['repeat256','diverse512']
    assert cfg['dispatch_allowed'] is True, 'manifest unreleased'
    assert cfg['budget']['optimizer_seconds']==1800 and cfg['budget']['worker_seconds']==2400
    assert cfg['budget']['matrix_cap_bytes']==1342177280
    assert os.environ.get('TREE')==str(root.resolve()) and os.environ.get('JOB')
    entry=next(e for e in cfg['sources'] if e['seed']==args.seed and e['arm']==args.arm)
    priorpath=root/entry['checkpoint']['path'];closedpath=root/entry['closed']['path']
    if sha(priorpath)!=entry['checkpoint']['sha256'] or sha(closedpath)!=entry['closed']['sha256']:raise RuntimeError('source checkpoint/closure differs')
    closed=read(closedpath);assert closed['checkpoint']==entry['checkpoint'] and closed['optimizer_updates']==10240 and closed['closed'] is True
    oldout=priorpath.parent
    original_frame_path=root/entry['original_frames']['path']
    original_frames=read(original_frame_path)['rows']
    assert sha(original_frame_path)==entry['original_frames']['sha256']
    frames_packet=read(root/cfg['frames']['path'])
    assert sha(root/cfg['frames']['path'])==cfg['frames']['sha256']
    packet=read(root/cfg['schedules']['path'])
    assert sha(root/cfg['schedules']['path'])==cfg['schedules']['sha256']
    schedule=packet['schedules'][str(args.seed)][args.arm]
    original=cfg['original_ids'];additional=cfg['additional_ids']
    validate_exposure(schedule,original,additional,args.arm)
    snapshot_pin=cfg['storage_snapshot'];assert sha(root/snapshot_pin['path'])==snapshot_pin['sha256']
    storage_spec=importlib.util.spec_from_file_location('_pinned_storage',root/snapshot_pin['path'])
    storage=importlib.util.module_from_spec(storage_spec);storage_spec.loader.exec_module(storage)
    allocated_bytes=storage.allocated_bytes;raw_allocated_bytes=storage.raw_allocated_bytes
    extra_paths=[root/p for p in cfg['output_accounting_extra_paths']]
    matrix=root/cfg['output_namespace'];out=matrix/('seed%d'%args.seed)/args.arm
    if out.exists():raise RuntimeError('continuation output exists; do not repeat')
    out.mkdir(parents=True)
    unit=sealed.filesystem_allocation_unit(root);initial_free=shutil.disk_usage(root).free
    def account():
        output=allocated_bytes(matrix,unit)+sum(allocated_bytes(p,unit) for p in extra_paths)
        pair=allocated_bytes(out.parent,unit)
        raw=raw_allocated_bytes(out.parent,unit)
        project=allocated_bytes(root,unit)
        return output,pair,raw,project
    def guard(extra=0):
        output,pair,raw,project=account()
        if output+extra>cfg['budget']['matrix_cap_bytes'] or pair+extra>cfg['budget']['pair_cap_bytes']:raise RuntimeError('new output matrix/pair cap exceeded')
        if project+extra>cfg['budget']['project_cap_bytes'] or shutil.disk_usage(root).free-extra<cfg['budget']['retained_free_bytes']:raise RuntimeError('project cap/free reserve exceeded')
    identity={'schema':'cap256.mixture10240.v1','job':os.environ['JOB'],'seed':args.seed,'arm':args.arm,'config_sha256':args.config_sha256,'source_checkpoint_sha256':entry['checkpoint']['sha256'],'source_plan_sha256':cfg['source_plan']['sha256'],'source_runner_sha256':cfg['source_runner']['sha256'],'optimizer_reset':False,'TRAIN_only':True}
    def write(name,record,append=False):
        data=(json.dumps(record,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
        guard(len(data)+unit)
        if account()[2]+len(data)+unit>cfg['budget']['raw_cap_bytes_per_pair']:raise RuntimeError('raw pair cap exceeded')
        with (out/name).open('ab' if append else 'xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    launched=time.monotonic();updates=0;calls=Counter()
    write('LAUNCH.json',{**identity,'start_update':10240,'target_update':20480,'source_visits':40,'additional_updates':10240,'initial_free_bytes':initial_free,'retained_input_matrix_allocated_bytes':allocated_bytes(root/cfg['input_namespace'],unit),'schedule_mode':cfg['schedule_mode']})
    try:
        sys.path[:0]=[str(root),str(root/'scripts')]
        import torch
        from sol_translator_grounding_v6 import HumanInputProjection,human_loss
        from sol_translator_english_ordered_v10 import load_ordered_english
        from sol_spatial_poc_ordered_v2 import load_ordered_bundle,OrderedPlainAttentionReasoner
        from sol_spatial_poc_ordered_train_api_v2 import fixed4_training
        from scripts.sol_stop_ordered_api2 import ordered_attention_math
        from sol_translator_decoder import FinalLatent
        from sol_translator_runtime import component_fingerprint
        torch.set_num_threads(2)
        if not torch.cuda.is_available():raise RuntimeError('authorized CUDA unavailable')
        binding=old['warmstart']['tuples'][str(args.seed)]
        dec,tok,_=load_ordered_english(binding['lm_path'],binding['lm_provenance'],binding['adapter_path'],'cuda')
        lm=dec.lm;lm.eval().requires_grad_(False)
        loop,_=load_ordered_bundle(binding['parent_path'],'cuda')
        core=loop
        reader_raw=torch.load(binding['reader_path'],map_location='cpu',weights_only=True)
        reader=HumanInputProjection(reader_raw['lm_width']).to('cuda');del reader_raw
        prior=torch.load(priorpath,map_location='cpu',weights_only=True)
        assert prior['update']==10240 and prior['raw_watermark_update']==10240 and prior['visits']=={i:40 for i in original}
        assert prior['constructor']==core.constructor()
        for name,module in (('core',core),('reader',reader),('prefix',dec.adapter)):
            module.load_state_dict(prior[name],strict=True)
            assert component_fingerprint(module)==closed['final_fingerprints'][name]
            module.train().requires_grad_(True)
        core.halt.requires_grad_(False)
        named=[(group+'.'+name,p) for group,module in (('core',core),('reader',reader),('prefix',dec.adapter)) for name,p in module.named_parameters() if p.requires_grad]
        assert [n for n,_ in named]==prior['optimizer_parameter_names']
        params=[p for _,p in named]
        opt=torch.optim.AdamW(params,lr=0.001,weight_decay=0,betas=(0.9,0.999),eps=1e-8)
        opt.load_state_dict(prior['optimizer'])
        for group in opt.param_groups:
            assert group['lr']==0.001 and group['weight_decay']==0 and group['betas']==(0.9,0.999) and group['eps']==1e-8
        participation=Counter(prior['participation']);nonzero=Counter({r['name']:r['nonzero_gradient_updates'] for r in prior['optimizer_audit']})
        for name,p in named:
            state=opt.state.get(p,{})
            assert (int(state['step']) if state else 0)==participation[name]
        rng=(prior['torch_rng'],prior['cuda_rng'],prior['python_rng'])
        inherited_visits=Counter(prior['visits']);del prior
        frames=frames_packet['rows']
        assert len(frames)==512 and len({f['id'] for f in frames})==512
        assert {f['id'] for f in frames}==set(original+additional)
        fresh_byid={f['id']:f for f in frames}
        for source_frame in original_frames:
            current=fresh_byid[source_frame['id']]
            for field in ('input_ids','input_mask','labels','label_mask','notebook_ids','notebook_mask'):
                assert current[field]==source_frame[field], 'original frame differs: '+field
        tokens=[]
        for f in frames:
            assert f['notebook_ids']==[[]] and f['notebook_mask']==[[]]
            assert f['label_mask']==[[t!=-100 for t in f['labels'][0]]]
            assert f['labels'][0][-1]==dec.eos_id and f['input_ids'][0][-1]==dec.eos_id
            tokens.append((torch.tensor(f['input_ids'],device='cuda'),torch.tensor(f['input_mask'],device='cuda',dtype=torch.bool),torch.tensor(f['labels'],device='cuda')))
        byid={f['id']:i for i,f in enumerate(frames)}
        lm_before=component_fingerprint(lm)
        frozen_halt=component_fingerprint(core.halt)
        write('RESUME.json',{**identity,'model_fingerprints_match_source':True,'parameter_order_matches_source':True,'Adam_steps_match_source_participation':True,'optimizer_lr':0.001,'model_rng_states_restored_before_first_update':True,'start_update':10240,'start_visits':40,'source_input_frames_sha256':entry['original_frames']['sha256'],'source_schedule_sha256':old['schedules'][str(args.seed)]['sha256']})
        torch.set_rng_state(rng[0]);torch.cuda.set_rng_state_all(rng[1]);random.setstate(rng[2]);del rng
        def graph(i):
            ids,mask,labels=tokens[i]
            with torch.no_grad():emb=lm.get_input_embeddings()(ids)
            query=reader(emb,mask)
            with ordered_attention_math():h,_,aux=fixed4_training(core,query,None,query_mask=mask)
            prefix=dec.adapter.project_training(h,torch.ones_like(h,dtype=torch.bool),mask,(1,h.shape[1]))
            return h,prefix,aux
        def timeout():
            if time.monotonic()-launched>cfg['budget']['worker_seconds']:raise RuntimeError('fixed continuation worker time cap')
            if torch.cuda.max_memory_reserved()>cfg['budget']['cuda_peak_reserved_cap_bytes']:
                raise RuntimeError('reserved CUDA memory cap exceeded')
        @torch.no_grad()
        def diagnostic():
            # No native TRAIN generation. Preserve post-optimizer RNG across CE.
            saved=(torch.get_rng_state(),torch.cuda.get_rng_state_all(),random.getstate())
            for module in (core,reader,dec.adapter):module.eval()
            for i,f in enumerate(frames):
                _,prefix,_=graph(i)
                per,pred=human_loss(lm,prefix,tokens[i][2],dec.bos_id,dec.eos_id,True,True)
                calls['TRAIN_endpoint_teacherforcing']+=1
                write('DIAGNOSTIC-RAW.jsonl',{**identity,'update':20480,'id':f['id'],'cohort':f['cohort'],'numeric_CE':float(per.mean()),'labels':f['labels'],'teacherforced_argmax':pred.cpu().tolist()},True)
                timeout()
            for module in (core,reader,dec.adapter):module.train()
            torch.set_rng_state(saved[0]);torch.cuda.set_rng_state_all(saved[1]);random.setstate(saved[2])
        optimizer_budget=sealed.OptimizerBudget(cfg['budget']['optimizer_seconds'])
        def save_checkpoint(filename,additional):
            fingerprints={n:component_fingerprint(m) for n,m in (('core',core),('reader',reader),('prefix',dec.adapter))}
            audit=[]
            for name,p in named:
                state=opt.state.get(p,{})
                assert (int(state['step']) if state else 0)==participation[name]
                audit.append({'name':name,'participation':participation[name],'nonzero_gradient_updates':nonzero[name],'Adam_step':int(state['step']) if state else 0})
            checkpoint={**identity,'update':10240+additional,'additional_updates':additional,'constructor':core.constructor(),'core':core.state_dict(),'reader':reader.state_dict(),'prefix':dec.adapter.state_dict(),'optimizer':opt.state_dict(),'optimizer_parameter_names':[n for n,_ in named],'optimizer_audit':audit,'participation':dict(participation),'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all(),'python_rng':random.getstate(),'visits':dict(inherited_visits),'model_state_fingerprints':fingerprints,'TRAIN_raw_sha256':sha(out/'TRAIN-RAW.jsonl'),'DIAGNOSTIC_raw_sha256':sha(out/'DIAGNOSTIC-RAW.jsonl') if (out/'DIAGNOSTIC-RAW.jsonl').exists() else None,'source_input_frames_sha256':entry['original_frames']['sha256'],'source_schedule_sha256':old['schedules'][str(args.seed)]['sha256'],'raw_watermark_update':10240+additional,'schedule_cursor':additional,'schedule_sha256':cfg['schedules']['sha256'],'optimizer_runtime_seconds':optimizer_budget.elapsed,'model_call_account':dict(calls)}
            parameter_bytes=sum(p.numel()*p.element_size() for p in params)
            path=out/filename;allowance=cfg['budget']['checkpoint_cap_bytes'][args.arm]
            if 3*parameter_bytes+3*1024**2>allowance:raise RuntimeError('checkpoint serialization allowance insufficient')
            def before_extent(extent):
                temporary=path.with_suffix(path.suffix+'.tmp')
                existing=temporary.stat().st_size if temporary.exists() else 0
                guard(max(0,extent-existing)+unit)
            sealed.save_new_atomic_file(path,allowance,lambda sink:torch.save(checkpoint,sink),before_extent)
            timeout()
            restored=torch.load(path,map_location='cpu',weights_only=True)
            assert restored['update']==10240+additional and restored['visits']==dict(inherited_visits)
            for name,module in (('core',core),('reader',reader),('prefix',dec.adapter)):
                assert all(torch.equal(restored[name][k],v.detach().cpu()) for k,v in module.state_dict().items())
            original_optimizer=opt.state_dict()
            for index,state in original_optimizer['state'].items():
                assert all(torch.equal(restored['optimizer']['state'][index][k],v.detach().cpu()) if torch.is_tensor(v) else restored['optimizer']['state'][index][k]==v for k,v in state.items())
            assert restored['schedule_cursor']==additional
            assert torch.equal(restored['torch_rng'],torch.get_rng_state())
            assert all(torch.equal(a,b.cpu()) for a,b in zip(restored['cuda_rng'],torch.cuda.get_rng_state_all()))
            assert restored['python_rng']==random.getstate()
            del restored,original_optimizer
            timeout()
            return path,fingerprints
        for add,identity_id in enumerate(schedule,1):
            timeout();optimizer_budget.begin();i=byid[identity_id]
            opt.zero_grad(set_to_none=True);_,prefix,aux=graph(i)
            per,pred=human_loss(lm,prefix,tokens[i][2],dec.bos_id,dec.eos_id,True,True);calls['TRAIN_optimizer_teacherforcing']+=1
            def record_grad():
                for name,p in named:
                    if p.grad is not None:
                        participation[name]+=1
                        if bool(torch.count_nonzero(p.grad)):nonzero[name]+=1
            preclip=sealed.numeric_optimizer_step(per.mean(),opt,params,torch,record_grad)
            torch.cuda.synchronize();optimizer_budget.end();updates=add;inherited_visits[identity_id]+=1
            assert not any(p.grad is not None for p in lm.parameters())
            f=frames[i]
            write('TRAIN-RAW.jsonl',{**identity,'update':10240+add,'additional_update':add,'id':identity_id,'visit_for_row':inherited_visits[identity_id],'numeric_CE':float(per.mean().detach()),'preclip_norm':float(preclip),'router_auxiliary_observed_excluded':float(aux.detach()),'auxiliary_weight':0,'objective':'numeric-answer-CE-only','lr':opt.param_groups[0]['lr'],'input_frame_sha256':f['frame_sha256'],'labels':f['labels'],'label_mask':f['label_mask'],'teacherforced_argmax':pred.cpu().tolist()},True)
            if add==5120:
                midpoint,_=save_checkpoint('midpoint-resume.pt',add)
                write('MIDPOINT.json',{**identity,'additional_optimizer_updates':add,'optimizer_updates':10240+add,'checkpoint':{'path':str(midpoint.relative_to(root)),'sha256':sha(midpoint)},'schedule_cursor':add,'schedule_sha256':cfg['schedules']['sha256'],'next_schedule_id':schedule[add],'model_Adam_and_rng_reload_equal':True,'optimizer_runtime_seconds':optimizer_budget.elapsed,'no_extra_model_calls':True})

        assert updates==10240
        expected=Counter({i:80 if args.arm=='repeat256' else 60 for i in original})
        if args.arm=='diverse512':expected.update({i:20 for i in additional})
        assert inherited_visits==expected
        diagnostic()
        assert component_fingerprint(lm)==lm_before and component_fingerprint(core.halt)==frozen_halt
        path,fingerprints=save_checkpoint('final-resume.pt',10240)
        write('CLOSED.json',{**identity,'closed':True,'optimizer_updates':20480,'additional_optimizer_updates':10240,'visits':dict(inherited_visits),'checkpoint':{'path':str(path.relative_to(root)),'sha256':sha(path)},'TRAIN_raw_sha256':sha(out/'TRAIN-RAW.jsonl'),'DIAGNOSTIC_raw_sha256':sha(out/'DIAGNOSTIC-RAW.jsonl'),'strict_TRAIN_generation_performed':False,'LM_unchanged':True,'durable_model_and_Adam_reload_equal':True,'wall_seconds':time.monotonic()-launched,'optimizer_runtime_seconds':optimizer_budget.elapsed,'model_call_account':dict(calls),'final_fingerprints':fingerprints,'retained_input_matrix_allocated_bytes':allocated_bytes(root/cfg['input_namespace'],unit),'new_output_matrix_allocated_bytes':account()[0],'project_allocated_bytes':account()[3],'free_bytes':shutil.disk_usage(root).free})
        print(json.dumps({'status':'CLOSED-MIXTURE10240','seed':args.seed,'arm':args.arm,'additional_optimizer_updates':10240,'checkpoint_sha256':sha(path)}),flush=True)
    except Exception as error:
        write('FAILED.json',{**identity,'additional_optimizer_updates':updates,'error_type':type(error).__name__,'error':str(error),'evidence_preserved':True})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--config',required=True);p.add_argument('--config-sha256',required=True);p.add_argument('--seed',type=int,choices=(0,1),required=True);p.add_argument('--arm',choices=('repeat256','diverse512'),required=True)
    run(p.parse_args())
