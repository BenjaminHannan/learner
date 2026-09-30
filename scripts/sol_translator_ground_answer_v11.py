#!/usr/bin/env python3
"""NEW verbatim HUMAN answer-annotation grounding; short answers are not grammatical-chat proof. Core/reader/thin prefix trained, frozen FP32 LM.
Fixed4 engineering only; no learned stop readiness or overnight improvement claim.
"""
from __future__ import annotations
import argparse, hashlib, json, os, random, shutil, signal, time
from pathlib import Path
import torch
from torch import nn
import claude_fewex_net as N
from sol_spatial_poc_ordered_v2 import make_ordered_source, ordered_bundle_payload, CONTRACT
from sol_spatial_attention_core import load_bundle
from sol_spatial_poc_ordered_train_api_v2 import fixed4_training
from scripts.sol_stop_ordered_api2 import ordered_attention_math,make_ordered_fixed4_executor
from sol_spatial_attention_core import AttentionReasoner
from sol_translator_grounding_v6 import HumanInputProjection, question_notebook_tokens, target_tokens, human_loss
from sol_translator_answer_data_v11 import human_rows, MANIFEST
from sol_translator_english_v6 import FrozenEnglishDecoder, load_local_lm
from sol_translator_runtime import component_fingerprint
from sol_translator_provenance import sha
from sol_stop_adapter import WorkMeter
ROOT=Path(__file__).resolve().parents[1]
OWN=ROOT/'artifacts/sol-translator-20260929'
SPEC=OWN/'ANSWER-V11-SPEC.json'
SEAL=OWN/'ANSWER-V11-SEAL.json'
TRANSLATOR=ROOT/'artifacts/sol-translator-20260929'


def write_json(path, record):
    tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(record,indent=2)+'\n');os.replace(tmp,path)


def verify():
    seal=json.loads(SEAL.read_text())
    for name,expected in seal['files'].items():
        p=(ROOT/name).resolve()
        if not p.is_relative_to(ROOT.resolve()) or sha(p)!=expected:raise ValueError('source pin mismatch '+name)
    return json.loads(SPEC.read_text())


def queued_output(a):
    if not os.environ.get('JOB') or Path(os.environ.get('TREE','')).resolve()!=ROOT.resolve():
        raise RuntimeError('watcher JOB and exact TREE required; no standalone TRAIN')
    if a.device!='cuda':raise RuntimeError('actual queued CUDA only')
    out=Path(a.out).resolve()
    if out!=OWN/f'ground-answer-v11-s{a.seed}-{a.family}':raise ValueError('exact NEW owned seed output required')
    warm=json.loads((OWN/'ANSWER-V11-WARMSTART.json').read_text())['per_seed'][str(a.seed)]
    for key in ('source','reader','prefix'):
        actual=Path(getattr(a,key))
        if actual.resolve()!=Path(warm[key+'_path']).resolve() or sha(actual)!=warm[key+'_sha256']:raise ValueError('exact CLOSED warmstart required '+key)
    if sha(a.model_provenance)!=sha(TRANSLATOR/'CACHED-LFM-ORIGINAL-PROVENANCE.json'):raise ValueError('exact frozen LM manifest required')
    out.mkdir(parents=True,exist_ok=True)
    return out


def disk_bytes():
    return sum(p.stat().st_size for d in OWN.glob('ground-answer-v11-s[01]-*') for p in d.rglob('*') if p.is_file())


def atomic_save(record,path,cap,estimated_bytes):
    # Account BOTH seeds' existing resumes/exports and this atomic temporary.
    if disk_bytes()+estimated_bytes>cap:raise RuntimeError('output cap before atomic temporary; existing durability preserved')
    reserve=json.loads(SPEC.read_text())['retained_free_bytes']
    if shutil.disk_usage(path.parent).free<estimated_bytes+reserve:raise RuntimeError('free disk must retain reserve after atomic temporary')
    tmp=path.with_suffix('.pt.tmp');torch.save(record,tmp)
    if disk_bytes()>cap:raise RuntimeError('actual serialized output cap exceeded; temporary preserved')
    os.replace(tmp,path)


def modules(a):
    torch.set_num_threads(2);torch.manual_seed(a.seed)
    lm,tok,provenance=load_local_lm(a.model,a.model_provenance,a.device)
    source,meta=load_bundle(a.source,'cpu')
    if meta.get('reader_version')!='human-notebook-v2' or meta.get('human_manifest_sha256')!=sha(Path(a.corpus)/'pairs.json'):raise ValueError('wrong closed HUMAN parent lineage')
    core=make_ordered_source(source,variant='loop' if a.family=='loop' else 'sparse_unrolled4').to(a.device)
    reader=HumanInputProjection(lm.get_input_embeddings().weight.shape[1]).to(a.device)
    rawreader=torch.load(a.reader,map_location=a.device,weights_only=True)
    if rawreader['training_origin']!='verified-human-origin' or rawreader['human_manifest_sha256']!=meta['human_manifest_sha256']:raise ValueError('reader human origin/lineage')
    reader.load_state_dict(rawreader['state_dict'])
    decoder=FrozenEnglishDecoder(lm,256,tok.bos_token_id,tok.eos_token_id,prefix_tokens=8).to(a.device)
    rawprefix=torch.load(a.prefix,map_location=a.device,weights_only=True)
    if rawprefix['training_origin']!='verified-human-origin-verbatim' or rawprefix['parent_sha256']!=sha(a.source) or rawprefix['reader_sha256']!=sha(a.reader):raise ValueError('prefix human/frozen-parent lineage mismatch')
    decoder.adapter.load_state_dict(rawprefix['adapter_state'])
    core.train().requires_grad_(True);reader.train().requires_grad_(True);decoder.adapter.train().requires_grad_(True)
    if a.family!=json.loads(SPEC.read_text())['family']:raise ValueError('wrong sealed family')
    assert all(p.dtype==torch.float32 and not p.requires_grad for p in lm.parameters() if p.is_floating_point())
    assert all(p.dtype==torch.float32 for m in (core,reader,decoder.adapter) for p in m.parameters())
    return lm,tok,core,reader,decoder


def row_graph(lm,core,reader,decoder,ids,valid,mids,mvalid,targets):
    with torch.no_grad():e=lm.get_input_embeddings()(ids);memo=lm.get_input_embeddings()(mids)
    latent=reader(e,valid);book=reader(memo,mvalid).flatten(1,2)
    with ordered_attention_math():
        h,q,auxiliary=fixed4_training(core,latent,book,query_mask=valid,notebook_mask=mvalid)
    if h.shape[:2]!=ids.shape:raise RuntimeError('notebook leaked into final query')
    prefix=decoder.adapter.project_training(h,torch.ones_like(h,dtype=torch.bool),valid,(1,h.shape[1]))
    per,pred=human_loss(lm,prefix,targets,decoder.bos_id,decoder.eos_id,True,True)
    return per.mean()+auxiliary,{'round':4,'stop_logits':q.detach().cpu().tolist(),
        'stop_used':False,'order_contract':CONTRACT,'selection_mass':[1.0],'human_CE_per_example':per.detach().cpu().tolist(),
        'auxiliary_mean_all_eight_block_visits':float(auxiliary.detach()),'predictions':pred.cpu().tolist()}


def memory(a):
    plan=verify();out=queued_output(a);start=time.monotonic()
    try:
        lm,tok,core,reader,decoder=modules(a)
        params=[p for m in (core,reader,decoder.adapter) for p in m.parameters()]
        trainable_bytes=sum(p.numel()*p.element_size() for p in params)
        device=lm.get_input_embeddings().weight.device
        free,total=torch.cuda.mem_get_info(device);torch.cuda.reset_peak_memory_stats(device)
        records=[];losses=[]
        with torch.random.fork_rng(devices=[device.index]):
            torch.manual_seed(2026093050+a.seed);vocab=lm.get_input_embeddings().weight.shape[0]
            for i in range(2):
                ids=torch.randint(vocab,(1,49),device=device);mids=torch.randint(vocab,(1,512),device=device)
                targets=torch.randint(vocab,(1,64),device=device);valid=torch.ones_like(ids,dtype=torch.bool);mvalid=torch.ones_like(mids,dtype=torch.bool)
                loss,round_raw=row_graph(lm,core,reader,decoder,ids,valid,mids,mvalid,targets);losses.append(loss)
                records.append({'row':i,'input_ids':ids.cpu().tolist(),'input_mask':valid.cpu().tolist(),
                    'notebook_ids':mids.cpu().tolist(),'notebook_mask':mvalid.cpu().tolist(),'labels':targets.cpu().tolist(),
                    'label_mask':torch.ones_like(targets,dtype=torch.bool).cpu().tolist(),'rounds':[round_raw]})
            torch.stack(losses).mean().backward();torch.cuda.synchronize(device)
        assert all(p.grad is None for p in lm.parameters())
        # Actual PC torch backend parity under grad-enabled TRAIN vs native inference.
        with torch.no_grad():
            qe=reader(lm.get_input_embeddings()(ids),valid);be=reader(lm.get_input_embeddings()(mids),mvalid).flatten(1,2)
        with ordered_attention_math():
            h_grad,q_grad,aux_grad=fixed4_training(core,qe,be,query_mask=valid,notebook_mask=mvalid)
        expected=h_grad.detach().clone();del h_grad,q_grad,aux_grad
        execution=make_ordered_fixed4_executor(core)
        actual=execution.execute_embeddings(qe.detach().flatten(1,2),valid,(1,qe.shape[2]),query_mask=valid,notebook_latents=be.detach(),notebook_mask=mvalid,policy='fixed',cap=4,compact=True).final.latent
        parity=float((expected-actual).abs().max())
        if parity!=0.0:raise RuntimeError('actualPC TRAIN/runtime native ordered parity mismatch '+str(parity))
        torch.cuda.synchronize(device)
        allocated=torch.cuda.max_memory_allocated(device);reserved=torch.cuda.max_memory_reserved(device)
        inferred=4*trainable_bytes;reserve=512*1024**2;limit=min(plan['cuda_cap_bytes'],total)
        result={'stage':'ACTUAL-FULL-FP32-ORDERED-READER-PREFIX-FINAL4-GRAPH-NOOPT','seed':a.seed,'job':os.environ['JOB'],
            'torch':torch.__version__,'GPU':torch.cuda.get_device_name(device),'device_total_bytes':total,'free_before_bytes':free,
            'trainable_parameter_bytes':trainable_bytes,'LM_parameter_bytes':sum(p.numel()*p.element_size() for p in lm.parameters()),
            'LM_embedding_dtype':str(lm.get_input_embeddings().weight.dtype),'LM_head_dtype':str(lm.get_output_embeddings().weight.dtype),
            'peak_allocated_bytes_measured':allocated,'peak_reserved_bytes_measured':reserved,
            'optimizer_margin_bytes_inferred_not_measured':inferred,'safety_reserve_bytes':reserve,'cap_bytes':limit,
            'cap_guard_passed':reserved+inferred+reserve<=limit,'wall_seconds_measured':time.monotonic()-start,
            'raw_numeric_records':records,'optimizer_updates':0,'human_examples':0,'LM_forwards':2,
            'source_sha256':sha(a.source),'plan_sha256':sha(SPEC),'seal_sha256':sha(SEAL),'driver_sha256':sha(__file__),
            'model_provenance_sha256':sha(a.model_provenance),'reader_source_sha256':sha(a.reader),'prefix_source_sha256':sha(a.prefix),'family':a.family,'order_contract':CONTRACT,'paired_reader_initial_sha256':component_fingerprint(reader),
            'paired_prefix_initial_sha256':component_fingerprint(decoder.adapter),'warmstart_closed_parent_reader_prefix_exact':True,'native_TRAIN_runtime_max_abs_measured':parity,'child_exit_before_TRAIN':True,'precision':'FP32 no fallback'}
        write_json(out/'MEMORY-PREFLIGHT.json',result)
        print(json.dumps({k:v for k,v in result.items() if k!='raw_numeric_records'}),flush=True)
        if not result['cap_guard_passed']:raise RuntimeError('actual FP32 plain memory cap failed; do not TRAIN')
    except BaseException as exc:
        write_json(out/'MEMORY-FAILURE.json',{'error':str(exc),'type':type(exc).__name__,'seed':a.seed,
            'optimizer_updates':0,'wall_seconds':time.monotonic()-start,'driver_sha256':sha(__file__),'precision':'FP32 no fallback'})
        raise


def train(a):
    plan=verify();out=queued_output(a)
    receipt=json.loads((out/'MEMORY-PREFLIGHT.json').read_text())
    for key,value in {'seed':a.seed,'source_sha256':sha(a.source),'plan_sha256':sha(SPEC),'seal_sha256':sha(SEAL),
                      'driver_sha256':sha(__file__),'model_provenance_sha256':sha(a.model_provenance),'reader_source_sha256':sha(a.reader),'prefix_source_sha256':sha(a.prefix),'family':a.family,'order_contract':CONTRACT}.items():
        if receipt[key]!=value:raise ValueError('memory receipt binding '+key)
    if not receipt['cap_guard_passed'] or receipt['optimizer_updates']!=0:raise ValueError('positive noopt memory receipt required')
    if shutil.disk_usage(out).free<plan['disk_floor_bytes']:raise RuntimeError('sealed disk floor before TRAIN')
    rows,reg=human_rows(a.corpus);rows=[r for r in rows if r['split']=='train']
    if len(rows)!=512:raise ValueError('exact human TRAIN512 required')
    lm,tok,core,reader,decoder=modules(a)
    for row in rows:
        target_tokens(tok,[row],a.device)
        if len(tok.encode(row['context'],add_special_tokens=False))>512:raise ValueError('predeclared full TRAIN context coverage512 exceeded; no drop/crop fallback')
    if component_fingerprint(reader)!=receipt['paired_reader_initial_sha256'] or component_fingerprint(decoder.adapter)!=receipt['paired_prefix_initial_sha256']:raise ValueError('preflight/train initialization drift')
    before=component_fingerprint(lm);core_initial=component_fingerprint(core)
    parameters=[p for m in (core,reader,decoder.adapter) for p in m.parameters()]
    opt=torch.optim.AdamW(parameters,lr=plan['lr'],weight_decay=plan['weight_decay'])
    meter=WorkMeter(nn.ModuleDict({'core':core,'reader':reader,'prefix':decoder.adapter}));meter.phase='TRAIN'
    sampling=random.Random(2026092970+a.seed);visited=set();interrupted=[False];first=0;resume_hash=None
    signal.signal(signal.SIGTERM,lambda *_:interrupted.__setitem__(0,True));signal.signal(signal.SIGINT,lambda *_:interrupted.__setitem__(0,True))
    ledger={'seed':a.seed,'stage':'ordered-human-final4-unqualified','updates':0,'batch':2,'rounds':4,'reader_version':'human-notebook-v2',
        'variant':a.family,'order_contract':CONTRACT,'human_pairs_sha256':sha(Path(a.corpus)/'pairs.json'),'human_registry_sha256':sha(Path(a.corpus)/'registry.json'),
        'source_sha256':sha(a.source),'core_initial_sha256':core_initial,'reader_initial_sha256':component_fingerprint(reader),
        'prefix_initial_sha256':component_fingerprint(decoder.adapter),'plan_sha256':sha(SPEC),'seal_sha256':sha(SEAL),'driver_sha256':sha(__file__),
        'model_provenance_sha256':sha(a.model_provenance),'reader_source_sha256':sha(a.reader),'prefix_source_sha256':sha(a.prefix),'family':a.family,'order_contract':CONTRACT,'core_counts':core.counts(),'LM_training_forwards':0,'human_target_token_visits':0,
        'input_token_visits':0,'train_unique_ids':[],'parent_frozen':False,'raw_watermark_update':0,'sleep_updates':0,'DEV_model_calls':0,
        'fixed_input_truncation':{'question_cap':48,'context_cap':512,'question_truncated_n':sum(len(tok.encode(r['question'],add_special_tokens=False))>48 for r in rows),
            'context_truncated_n':sum(len(tok.encode(r['context'],add_special_tokens=False))>512 for r in rows),'selection':'fixed prefix; no target crop/drop'},
        'annotation_manifest_sha256':sha(MANIFEST),'objective':'verbatim HUMAN answer annotation+EOS final4 CE + mean8 auxiliary; no authored sentence target; no halt/ponder',
        'fairness':'NEW ordered-loop cohort; V6halt-weighted objective differs. Future ordered-plain must same ordered inputs/final4 CE/all8 aux; capacity/optimizer work differ',
        'noise':'INSUFFICIENT; no semantic promotion','precision':'FULL FP32','output_sizes_measured':{}}
    schedule=json.loads((OWN/f'ANSWER-V11-TRAIN-SCHEDULE-s{a.seed}.json').read_text());by_id={r['id']:r for r in rows}
    if len(schedule)!=plan['updates']:raise ValueError('exact schedule length')
    for pair in schedule:
        left,right=(by_id[i] for i in pair)
        if left['context']!=right['context'] or left['id']==right['id'] or set(x.casefold().strip() for x in left['accepted_human_answers'])&set(x.casefold().strip() for x in right['accepted_human_answers']):raise ValueError('invalid shared-context disjoint-answer pair')
    ledger['pretrain_sample_schedule_sha256']=hashlib.sha256(json.dumps(schedule,separators=(',',':')).encode()).hexdigest()
    if ledger['pretrain_sample_schedule_sha256']!=plan['TRAIN_schedule_sha256'][str(a.seed)]:raise ValueError('presealed TRAIN ID schedule mismatch')
    ledger['warmstart_closed_parent_reader_prefix_exact']=True
    binding={k:ledger[k] for k in ('seed','family','human_pairs_sha256','human_registry_sha256','source_sha256','reader_source_sha256','prefix_source_sha256','order_contract','plan_sha256','seal_sha256','driver_sha256','model_provenance_sha256','annotation_manifest_sha256')}
    if a.resume:
        ck=torch.load(a.resume,map_location=a.device,weights_only=True)
        if ck['binding']!=binding:raise ValueError('resume exact binding mismatch')
        core.load_state_dict(ck['core']);reader.load_state_dict(ck['reader']);decoder.adapter.load_state_dict(ck['adapter']);opt.load_state_dict(ck['optimizer'])
        sampling.setstate(ck['sample_rng']);torch.set_rng_state(ck['torch_rng'].cpu());torch.cuda.set_rng_state_all([v.cpu() for v in ck['cuda_rng']])
        ledger=ck['ledger'];first=ledger['updates'];visited=set(ledger['train_unique_ids']);resume_hash=sha(a.resume)
        meter.records=ledger.get('work_meter',{}).get('modules',{})
    elif (out/f'resume-s{a.seed}.pt').exists():raise ValueError('existing checkpoint requires NEW explicit-resume job')
    launch=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+os.environ['JOB'];ledger.update(job=os.environ['JOB'],launch_id=launch,resume_start_update=first,resume_checkpoint_sha256=resume_hash)
    started={'status':'TRAIN-STARTED-BEFORE-OPTIMIZER-STEP','job':os.environ['JOB'],'launch_id':launch,'seed':a.seed,'optimizer_updates_this_launch':0,'resume_start_update':first,'binding':binding,**{k:ledger[k] for k in ('pretrain_sample_schedule_sha256','reader_initial_sha256','prefix_initial_sha256','core_initial_sha256')}}
    started_path=out/('TRAIN-STARTED.json' if not a.resume else 'TRAIN-STARTED-'+launch+'.json')
    if started_path.exists():raise ValueError('preserve previous preoptimizer receipt')
    write_json(started_path,started);print(json.dumps(started),flush=True)
    rawpath=out/f'train-raw-s{a.seed}.jsonl'
    with rawpath.open('a') as f:f.write(json.dumps({'kind':'LAUNCH-WATERMARK','launch_id':launch,'resume_start_update':first,
        'resume_checkpoint_sha256':resume_hash,'durable_raw_watermark':ledger['raw_watermark_update'],
        'orphan_policy':'retain prior noncommitted rows; identify by launch+update+id; no silent truncation'})+'\n')
    start=time.monotonic();prior_wall=ledger.get('TRAIN_wall_seconds',0);torch.cuda.reset_peak_memory_stats()
    def durable():
        ledger['train_unique_ids']=sorted(visited);ledger['raw_watermark_update']=ledger['updates']
        ledger['TRAIN_wall_seconds']=prior_wall+time.monotonic()-start;ledger['work_meter']=meter.report()
        ledger['output_directory_bytes_measured_before_save']=disk_bytes()
        meta={'stage':'human-grounded-ordered-unqualified','human_manifest_sha256':ledger['human_pairs_sha256'],'order_contract':CONTRACT,'input_version':'human-notebook-ordered-v10',
            'reader_version':'human-notebook-v2','seed':a.seed,'updates':ledger['updates'],'batch':2,'rounds':4,'ledger':dict(ledger)}
        cap=plan['max_disk_bytes'];parambytes=sum(p.numel()*p.element_size() for p in parameters)
        # Upper estimate includes populated two Adam moments plus serialization overhead.
        ck={'core':core.state_dict(),'reader':reader.state_dict(),'adapter':decoder.adapter.state_dict(),'optimizer':opt.state_dict(),
            'sample_rng':sampling.getstate(),'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all(),
            'ledger':dict(ledger),'binding':binding}
        atomic_save(ck,out/f'resume-s{a.seed}.pt',cap,3*parambytes+4*1024**2)
        atomic_save(ordered_bundle_payload(core,meta),out/f'parent-s{a.seed}.pt',cap,sum(p.numel()*p.element_size() for p in core.parameters())+4*1024**2)
        atomic_save({'state_dict':reader.state_dict(),'lm_width':lm.get_input_embeddings().weight.shape[1],
            'human_manifest_sha256':ledger['human_pairs_sha256'],'training_origin':'verified-human-origin','stage':'ordered-joint-grounding-unqualified','input_version':'human-notebook-ordered-v10','order_contract':CONTRACT,
            'input_scope':'question only query; fixed512context notebook; fullTRAINcontext max479','reader_version':'human-notebook-v2'},out/f'input-s{a.seed}.pt',cap,2*1024**2)
        ledger['parent_checkpoint_sha256']=sha(out/f'parent-s{a.seed}.pt')
        atomic_save({'state_width':256,'hidden':32,'prefix_tokens':8,'adapter_state':decoder.adapter.state_dict(),
            'human_manifest_sha256':ledger['human_pairs_sha256'],'human_registry_sha256':ledger['human_registry_sha256'],
            'source_state_contract':'sol-stop-FinalLatent-v1','lm_provenance_sha256':ledger['model_provenance_sha256'],
            'training_origin':'verified-human-origin-verbatim','parent_sha256':ledger['parent_checkpoint_sha256'],
            'reader_sha256':sha(out/f'input-s{a.seed}.pt'),'training_stage':'ordered-joint-grounding-unqualified','input_version':'human-notebook-ordered-v10','order_contract':CONTRACT},out/f'bootstrap-English-s{a.seed}.pt',cap,2*1024**2)
        ledger['output_sizes_measured']={p.name:p.stat().st_size for p in out.glob('*.pt')}
        # Save resume again so closed ledger embeds exact final component hashes/sizes.
        ck['ledger']=dict(ledger)
        atomic_save(ck,out/f'resume-s{a.seed}.pt',cap,3*parambytes+4*1024**2)
        write_json(out/f'grounding-s{a.seed}.json',ledger)
        print(json.dumps({'status':'DURABLE-TRAIN-WEIGHTS','seed':a.seed,'updates':ledger['updates'],
            'seconds_current_launch':time.monotonic()-start,'resume_sha256':sha(out/f'resume-s{a.seed}.pt'),
            'parent_sha256':ledger['parent_checkpoint_sha256'],'actual_output_sizes':ledger['output_sizes_measured'],'both_seed_output_bytes':disk_bytes()}),flush=True)
    print(json.dumps({'status':'OPTIMIZER-READY','seed':a.seed,'job':os.environ['JOB'],'updates_requested':plan['updates'],'first_resume_update':first,'stored_core_parameters':core.counts()['stored_parameters']}),flush=True)
    for step in range(first,plan['updates']):
        if interrupted[0] or time.monotonic()-start>=plan['wall_cap_seconds']:break
        batch=[by_id[i] for i in schedule[step]];visited.update(r['id'] for r in batch);losses=[];raw=[]
        opt.zero_grad(set_to_none=True)
        for row in batch:
            ids,valid,mids,mvalid=question_notebook_tokens(tok,row,a.device,max_context=512);targets=target_tokens(tok,[row],a.device)
            loss,round_raw=row_graph(lm,core,reader,decoder,ids,valid,mids,mvalid,targets);losses.append(loss)
            identity={'input_ids':ids.cpu().tolist(),'input_mask':valid.cpu().tolist(),'notebook_ids':mids.cpu().tolist(),'notebook_mask':mvalid.cpu().tolist()}
            raw.append({**identity,'input_identity_sha256':hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest(),
                'human_question':row['question'],'human_answer':row['answer_text'],'accepted_human_answers':row['accepted_human_answers'],'context_sha256':row['context_sha256'],'target_origin':'official HUMAN answer annotation verbatim+EOS','id':row['id'],'content_key':row['content_key'],'split':'train','seed':a.seed,'update':step+1,'labels':targets.cpu().tolist(),
                'label_mask':(targets!=-100).cpu().tolist(),'predictions':round_raw['predictions'],'rounds':[round_raw],
                'prediction_kind':'teacher-forced TRAIN ONLY; never reused as targets','source_sha256':row['source_sha256'],
                **binding,'launch_id':launch,'job':os.environ['JOB'],'resume_start_update':first,'resume_checkpoint_sha256':resume_hash,
                'source_parent_sha256':ledger['source_sha256'],'initial_core_sha256':core_initial,
                'parent_previous_checkpoint_sha256':ledger.get('parent_checkpoint_sha256'),'reader_version':'human-notebook-v2',
                'physical_attention_block_calls':8,'physical_row_segments':4,'selected_expert_token_calls':16*int(valid.sum()+mvalid.sum()),
                'analytical_attention_matmul_MACs_not_total':8*2*(ids.numel()+mids.numel())**2*256})
            ledger['LM_training_forwards']+=1;ledger['human_target_token_visits']+=int((targets!=-100).sum());ledger['input_token_visits']+=int(valid.sum()+mvalid.sum())
        loss=torch.stack(losses).mean()
        if not bool(torch.isfinite(loss)):raise RuntimeError('nonfinite loss; preserve latest durable checkpoint')
        loss.backward();norm=torch.nn.utils.clip_grad_norm_(parameters,plan['clip_grad_norm'],error_if_nonfinite=True);opt.step()
        if any(p.grad is not None for p in lm.parameters()):raise RuntimeError('frozen LM gradient')
        ledger['updates']=step+1
        with rawpath.open('a') as f:
            for r in raw:r.update(batch_objective=float(loss.detach()),batch_grad_norm=float(norm));f.write(json.dumps(r)+'\n')
        if step==first or (step+1)%25==0:durable()
    ledger['requested_updates_completed']=ledger['updates']==plan['updates'];ledger['interrupted']=interrupted[0]
    ledger['peak_cuda_bytes_measured']=torch.cuda.max_memory_allocated();ledger['peak_reserved_bytes_measured']=torch.cuda.max_memory_reserved()
    ledger['core_final_sha256']=component_fingerprint(core);ledger['core_changed']=ledger['core_final_sha256']!=core_initial
    if component_fingerprint(lm)!=before:raise RuntimeError('frozen LM changed')
    ledger['LM_unchanged']=True;ledger['parent_frozen']=True;ledger['closed']=bool(ledger['requested_updates_completed']);core.eval().requires_grad_(False);reader.eval().requires_grad_(False);decoder.adapter.eval().requires_grad_(False)
    durable();meter.close()
    print(json.dumps(ledger),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('check','memory','train'));p.add_argument('--model');p.add_argument('--model-provenance',default=str(TRANSLATOR/'CACHED-LFM-ORIGINAL-PROVENANCE.json'))
    p.add_argument('--corpus',default=str(TRANSLATOR/'corpus'));p.add_argument('--source');p.add_argument('--reader');p.add_argument('--prefix');p.add_argument('--family',choices=('loop','plain'),default='loop');p.add_argument('--out');p.add_argument('--seed',type=int,choices=(0,1));p.add_argument('--device',default='cuda');p.add_argument('--resume');a=p.parse_args()
    if a.mode=='check':print(json.dumps({'checked':True,'plan':verify()}));return
    if None in (a.model,a.source,a.reader,a.prefix,a.out,a.seed):p.error('model/source/out/seed required for queued graph or TRAIN')
    if a.mode=='memory':memory(a)
    else:train(a)
if __name__=='__main__':main()
