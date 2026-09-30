"""CPU weights_only saved tensors and saved numeric arrays, no model imports."""
import base64
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import zlib
import numpy as np
import torch

ROOT=Path('/workspace/learner')
OWN=ROOT/'artifacts/sol-cloud-verifier-20260930'
torch.set_num_threads(2)
checks=[]
def check(value,name):
    if not value: raise AssertionError(name)
    checks.append(name)
def digest(raw): return hashlib.sha256(raw).hexdigest()
def tensor_info(t):
    raw=t.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()
    return {'shape':list(t.shape),'dtype':str(t.dtype),'elements':t.numel(),'bytes':len(raw),'sha256':digest(raw)}
def fingerprint(state):
    h=hashlib.sha256()
    for name,t in sorted(state.items()):
        h.update(f'{name}:{t.dtype}:{tuple(t.shape)}'.encode())
        h.update(t.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
    return h.hexdigest()
reports=[]
for seed,checkpoint_sha in [(0,'3bf555d3b0ae6b02d757031c64f431ae8d01bfe6fd62ff7ccdf3858d2ca9bd16'),(1,'c2084fabd8fd2e58dc05399630505e45c739bea26983690f950fea27a1ea771e')]:
    binary=OWN/f'exposure16-r5-r2-s{seed}-binary-v1'
    run=OWN/f'exposure16-r5-r2-s{seed}-recount-v1/run'
    path=binary/'connected-resume.pt'
    check(digest(path.read_bytes())==checkpoint_sha,f'seed{seed} original checkpoint SHA')
    checkpoint=torch.load(path,map_location='cpu',weights_only=True)
    closed=json.loads((run/'CLOSED.json').read_bytes())
    check(checkpoint['seed']==seed and checkpoint['arm']=='connected' and checkpoint['update']==checkpoint['raw_watermark_update']==800,f'seed{seed} update/arm identity')
    for key in ['job','binding','plan_sha256','seal_sha256','release_sha256','inventory_sha256','source','visits','TRAIN_raw_sha256','frame_sha256']:
        check(checkpoint[key]==closed[key],f'seed{seed} closed binding {key}')
    check(checkpoint['actual_user_day'] is False and checkpoint['generated_training_material'] is False and checkpoint['split']=='released-HUMAN-TRAIN-memorization-only' and checkpoint['activation_qualified'] is False,f'seed{seed} engineering-only identity')
    check(len(checkpoint['visits'])==16 and set(checkpoint['visits'].values())=={50},f'seed{seed} 16x50 visits')
    check(digest((run/'TRAIN-RAW.jsonl').read_bytes())==checkpoint['TRAIN_raw_sha256'],f'seed{seed} actual TRAIN raw binds binary')
    states={}; names=[]; tensors=[]; storage=[]
    for component, expected in [('core',100),('reader',6),('prefix',6)]:
        state=checkpoint[component]
        check(len(state)==expected,f'seed{seed} {component} state coverage')
        fp=fingerprint(state)
        check(fp==checkpoint['model_state_fingerprints'][component]==closed['final_fingerprints'][component],f'seed{seed} {component} independently computed fingerprint')
        info={}
        for name,t in state.items():
            check(isinstance(t,torch.Tensor) and t.device.type=='cpu' and torch.isfinite(t).all().item(),f'seed{seed} {component}.{name} finite CPU saved tensor')
            info[name]=tensor_info(t)
            if component!='core' or name not in ('position_frequencies','boundary_roles'):
                names.append(component+'.'+name);tensors.append(t);storage.append((t.untyped_storage().data_ptr(),t.storage_offset(),t.numel()))
        states[component]={'fingerprint':fp,'state_count':len(state),'elements':sum(t.numel() for t in state.values()),'tensors':info}
    check(len(names)==110 and len(set(storage))==110,f'seed{seed} unique saved parameter order excluding2 buffers')
    opt=checkpoint['optimizer'];check(len(opt['param_groups'])==1,f'seed{seed} single exact optimizer group')
    group=opt['param_groups'][0]
    check(group['params']==list(range(110)) and group['lr']==0.001 and group['weight_decay']==0 and group['betas']==(0.9,0.999) and group['eps']==1e-8,f'seed{seed} source-compatible AdamW order/options')
    rows=[];steps=Counter();missing=[]
    for index,(name,t) in enumerate(zip(names,tensors)):
        state=opt['state'].get(index)
        if state is None:
            missing.append(name);continue
        check(set(state)=={'step','exp_avg','exp_avg_sq'},f'seed{seed} {name} closed Adam state keys')
        step=state['step'];s=float(step.item())
        check(step.ndim==0 and torch.isfinite(step).item() and s.is_integer() and 1<=s<=800,f'seed{seed} {name} exact bounded Adam participation step')
        steps[int(s)]+=1
        for key in ('exp_avg','exp_avg_sq'):
            moment=state[key]
            check(moment.shape==t.shape and moment.dtype==t.dtype and torch.isfinite(moment).all().item(),f'seed{seed} {name} {key} shape/dtype/finite')
        check((state['exp_avg_sq']>=0).all().item() and torch.count_nonzero(state['exp_avg_sq']).item()>0,f'seed{seed} {name} nonzero nonnegative second moment')
        rows.append({'name':name,'Adam_step':int(s),'exp_avg':tensor_info(state['exp_avg']),'exp_avg_sq':tensor_info(state['exp_avg_sq'])})
    expected_missing=['core.tok.weight','core.slot.weight','core.ln_out.weight','core.ln_out.bias','core.head.weight','core.head.bias','core.halt.weight','core.halt.bias']
    check(missing==expected_missing and len(rows)==102,f'seed{seed} 90core+6reader+6prefix moments and8 unused states')
    rng={'torch_rng':tensor_info(checkpoint['torch_rng']),'cuda_rng':[tensor_info(t) for t in checkpoint['cuda_rng']]}
    parity=[]
    for identity in ['5733be284776f4190066117f','5733be284776f41900661182']:
        p=binary/f'PARITY-initial-{identity}.json';wrapper=json.loads(p.read_bytes());r=wrapper['result']
        check(wrapper['seed']==seed and wrapper['id']==identity and wrapper['binding']==checkpoint['binding'],f'seed{seed} {identity} parity tuple')
        check(r['optimizer_updates']==0 and r['no_acceptance_threshold'] is True and not r['errors'],f'seed{seed} {identity} zero-update numeric parity only')
        arrays={}
        for key,record in r['raw_arrays'].items():
            check(record['dtype']=='little-endian-float32' and record['encoding']=='zlib-base64' and record['order']=='C',f'seed{seed} {identity} exact numeric encoding')
            raw=zlib.decompress(base64.b64decode(record['data'],validate=True))
            check(len(raw)==record['bytes']==int(np.prod(record['shape']))*4 and digest(raw)==key,f'seed{seed} {identity} saved array size/SHA')
            arrays[key]=np.frombuffer(raw,dtype='<f4').reshape(record['shape']).copy()
        summary_count=0
        def summaries(value):
            nonlocal_dummy=None
            if isinstance(value,dict):
                if value.get('raw_array_sha256'):
                    arr=arrays[value['raw_array_sha256']].reshape(-1); target=value['human_target_id']
                    check(int(arr.argmax())==value['argmax'] and bool(np.isfinite(arr).all())==value['finite'],f'seed{seed} {identity} saved argmax/finite')
                    check(float(arr[target])==value['human_target_logit'] and 1+int((arr>arr[target]).sum())==value['human_target_rank_strict'],f'seed{seed} {identity} saved target logit/rank')
                    check([float(arr[i]) for i in value['top8_ids']]==value['top8_logits'],f'seed{seed} {identity} saved top8 values')
                for child in value.values():summaries(child)
            elif isinstance(value,list):
                for child in value:summaries(child)
        summaries({k:v for k,v in r.items() if k!='raw_arrays'})
        def compare_saved(name,a,b):
            a=arrays[a['raw_array_sha256']].reshape(-1);b=arrays[b['raw_array_sha256']].reshape(-1);d=np.abs(a-b);saved=r[name]
            check(float(d.max())==saved['max_abs'] and np.isclose(float(d.mean()),saved['mean_abs'],rtol=1e-6,atol=1e-12),f'seed{seed} {identity} {name} saved max/mean difference')
            check(bool(np.array_equal(a,b))==saved['exact_equal'] and bool(a.argmax()==b.argmax())==saved['argmax_equal'],f'seed{seed} {identity} {name} saved equality')
        compare_saved('full_vs_BOS_first',r['first_full_teacher_forcing'],r['first_BOS_only_no_cache'])
        compare_saved('repeat_noise',r['first_BOS_only_no_cache'],r['repeat_BOS_only_no_cache'])
        def trim(ids):return ids[:ids.index(r['eos'])] if r['eos'] in ids else ids
        manual=trim(r['manual_uncached_greedy_ids'])
        generated=[]
        for key in ('generate_requested_cache_true','generate_requested_cache_false'):
            item=r[key];match=trim(item['sequence_ids'][0])==manual
            check(match==item['eos_trimmed_ids_equal_manual'] and item['effective_cache_not_instrumented'] is True,f'seed{seed} {identity} {key} saved generation/manual identity')
            generated.append(match)
        parity.append({'id':identity,'path':str(p.relative_to(ROOT)),'sha256':digest(p.read_bytes()),'packed_arrays':len(arrays),'full_vs_BOS':r['full_vs_BOS_first'],'repeat_noise':r['repeat_noise'],'teacher_history_summary_only':len(r['teacher_history_cache_vs_full']),'requested_cache_generation_matches_manual':generated,'torch':r['torch'],'transformers':r['transformers'],'effective_cache_measured':False})
    reports.append({'seed':seed,'checkpoint_sha256':checkpoint_sha,'checkpoint_bytes':path.stat().st_size,'states':states,'optimizer':{'parameter_mapping_basis':'sealed source group order: core state parameter order excluding2 buffers, reader, prefix; unique saved storage; no model constructed','parameter_count':110,'participating_core':90,'participating_reader':6,'participating_prefix':6,'state_count':102,'step_histogram':dict(sorted(steps.items())),'missing_states':missing,'states':rows},'RNG_hashes_only_not_restored':rng,'initial_parity':parity})
    del checkpoint
report={'schema':'exposure16-r5-r2-independent-binary-parity-recount-v1','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pass':True,'checks_passed':len(checks),'checks':checks,'reader_runtime':{'torch':torch.__version__,'CUDA_available':torch.cuda.is_available(),'interpreter':'/workspace/learner/.venv-cloud-cpu-v1/bin/python','weights_only':True,'map_location':'cpu'},'seeds':reports,'limits':['No module construction, forward, tokenizer, optimizer creation/step, rescoring, RNG restoration or new evaluation.','Step800 is global update count; sparse Adam states use recorded participation counts<=800, not all800.','No initial per-parameter checkpoint available here: no direct initial-to-final tensor-change claim.','Initial parity packs first-position arrays only; later teacher-history differences are saved summaries, not raw-array recounted.','Requested cache flags were recorded; effective generation cache behavior was not instrumented.','Actual source runtime Transformers5.17.0 differs from prior parameter-classification source4.57.2; cached config/header counts remain separate from runtime alias proof.','Same-prefix numerical parity and durable training state do not qualify semantics, notebook dependence, generalization or activation.'],'model_calls':0,'optimizer_updates_by_recount':0}
out=OWN/'EXPOSURE16-R5-R2-BINARY-PARITY-RECOUNT-v1.json'
with out.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({'pass':True,'checks':len(checks),'report':str(out),'sha256':digest(out.read_bytes()),'steps':[{x['seed']:x['optimizer']['step_histogram']} for x in reports]}))
