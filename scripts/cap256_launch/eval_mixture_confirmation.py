"""Conditional confirmation:128 native calls; score only after all raw outputs."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
try:
    from .train_mixture_resume_fastio import sha, read
except ImportError:
    from train_mixture_resume_fastio import sha, read


def score_saved(saved,frames,order,scorer,eos):
    """Score an already complete immutable128-record stream; no model calls."""
    assert len(saved)==128 and len(frames)==32 and len(order)==4
    assert len({f['id'] for f in frames})==32
    answers=[];results=[]
    for slot,(seed,arm) in enumerate(order):
        correct=0
        for index,f in enumerate(frames):
            n=slot*32+index;r=saved[n]
            assert r['call_index']==n+1 and (r['seed'],r['arm'],r['id'])==(seed,arm,f['id'])
            exact=scorer(r,f['labels'][0],eos);correct+=exact
            answers.append({**r,'group':f['group'],'canonical_target_ids_with_EOS':f['labels'][0],'strict_exact':bool(exact)})
        results.append({'seed':seed,'arm':arm,'strict_correct':correct,'rows':32})
    return results,answers


def run(a):
    root=Path(a.root);cfg=read(a.config)
    assert sha(a.config)==a.config_sha256 and cfg['dispatch_allowed'] is True
    for name in ('source_plan','source_seal','source_release','source_runner','dev_frames','storage_snapshot','selection','label_provenance'):
        pin=cfg[name];assert sha(root/pin['path'])==pin['sha256']
    storage_spec=importlib.util.spec_from_file_location('_pinned_storage',root/cfg['storage_snapshot']['path'])
    storage=importlib.util.module_from_spec(storage_spec);storage_spec.loader.exec_module(storage)
    allocated_bytes=storage.allocated_bytes
    proof=read(root/cfg['conditional_proof']['path'])
    assert sha(root/cfg['conditional_proof']['path'])==cfg['conditional_proof']['sha256']
    assert proof['recount_pass'] and proof['both_seed_positive_dev_exact']
    assert cfg['native_call_limit']==128 and cfg['teacherforced_call_limit']==0
    assert cfg['execution_order']==[[0,'repeat256'],[0,'diverse512'],[1,'diverse512'],[1,'repeat256']]
    assert cfg['budget']['wall_seconds']==600 and cfg['budget']['new_output_bytes']==67108864
    old=read(root/cfg['source_plan']['path'])
    for path,digest in read(root/cfg['source_seal']['path'])['files'].items():assert sha(root/path)==digest
    spec=importlib.util.spec_from_file_location('_sealed_mixture_eval',root/cfg['source_runner']['path'])
    sealed=importlib.util.module_from_spec(spec);spec.loader.exec_module(sealed);sealed.validate_plan(old)
    frames=read(root/cfg['dev_frames']['path'])['rows']
    selected=read(root/cfg['selection']['path'])['rows']
    assert [f['id'] for f in frames]==[r['id'] for r in selected]
    assert all(f['group']==r['group'] and f['question_sha256']==r['question_sha256'] for f,r in zip(frames,selected))
    assert all(1<=len(f['input_ids'][0])<=48 and 1<=len(f['labels'][0])<=32 for f in frames)
    assert len(frames)==32 and len({f['id'] for f in frames})==32
    assert not {f['id'] for f in frames}&set(cfg['original_ids']+cfg['additional_ids'])
    assert len({f['group'] for f in frames})==12
    matrix=root/cfg['output_namespace'];out=matrix/'confirmation32'
    extra_paths=[root/p for p in cfg['output_accounting_extra_paths']]
    assert not matrix.exists(),'existing confirmation namespace; no duplicate evaluation'
    endpoints=[]
    for seed,arm in cfg['execution_order']:
        binding=next(e for e in cfg['endpoints'] if e['seed']==seed and e['arm']==arm)
        assert sha(root/binding['closed']['path'])==binding['closed']['sha256']
        closed=read(root/binding['closed']['path'])
        assert closed['closed'] and closed['additional_optimizer_updates']==10240
        cp=root/closed['checkpoint']['path'];assert closed['optimizer_updates']==20480
        assert closed['checkpoint']==binding['checkpoint'] and sha(cp)==binding['checkpoint']['sha256']
        endpoints.append((seed,arm,closed,cp))
    unit=sealed.filesystem_allocation_unit(root);started=time.monotonic()
    def guard(extra=0,check_wall=True):
        if check_wall:assert time.monotonic()-started<=600,'confirmation wall cap'
        assert allocated_bytes(matrix,unit)+sum(allocated_bytes(p,unit) for p in extra_paths)+extra<=67108864
        assert allocated_bytes(root,unit)+extra<=cfg['budget']['project_cap_bytes']
        assert shutil.disk_usage(root).free-extra>=2**30
    def write(name,record,append=False,check_wall=True):
        raw=(json.dumps(record,sort_keys=True,allow_nan=False)+'\n').encode();guard(len(raw)+unit,check_wall)
        with (out/name).open('ab' if append else 'xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    guard(16*unit);matrix.mkdir();out.mkdir()
    write('CLAIM.json',{'config_sha256':a.config_sha256,'optimizer_updates':0,'native_call_limit':128})
    sys.path[:0]=[str(root),str(root/'scripts')]
    import torch
    from sol_translator_grounding_v6 import HumanInputProjection
    from sol_translator_english_ordered_v10 import load_ordered_english
    from sol_spatial_poc_ordered_v2 import load_ordered_bundle
    from sol_spatial_poc_ordered_train_api_v2 import fixed4_training
    from scripts.sol_stop_ordered_api2 import ordered_attention_math
    from sol_translator_decoder import FinalLatent
    from sol_translator_runtime import component_fingerprint
    torch.set_num_threads(2);assert torch.cuda.is_available()
    assert torch.cuda.get_device_properties(0).total_memory<=16*2**30
    b=old['warmstart']['tuples']['0']
    dec,tok,_=load_ordered_english(b['lm_path'],b['lm_provenance'],b['adapter_path'],'cuda')
    lm=dec.lm;lm.eval().requires_grad_(False);lm_before=component_fingerprint(lm)
    native=0;results=[]
    with torch.no_grad():
        for seed,arm,closed,cp in endpoints:
            binding=old['warmstart']['tuples'][str(seed)]
            core,_=load_ordered_bundle(binding['parent_path'],'cuda')
            rr=torch.load(binding['reader_path'],map_location='cpu',weights_only=True)
            reader=HumanInputProjection(rr['lm_width']).to('cuda');del rr
            saved=torch.load(cp,map_location='cpu',weights_only=True)
            assert saved['update']==20480 and saved['constructor']==core.constructor()
            for name,module in (('core',core),('reader',reader),('prefix',dec.adapter)):
                module.load_state_dict(saved[name],strict=True);module.eval().requires_grad_(False)
                assert component_fingerprint(module)==closed['final_fingerprints'][name]
            del saved;correct=0
            for f in frames:
                guard();assert torch.cuda.max_memory_reserved()<=15032385536
                assert f['notebook_ids']==[[]] and f['notebook_mask']==[[]]
                assert f['input_ids'][0][-1]==f['labels'][0][-1]==dec.eos_id
                ids=torch.tensor(f['input_ids'],device='cuda');mask=torch.tensor(f['input_mask'],device='cuda',dtype=torch.bool)
                query=reader(lm.get_input_embeddings()(ids),mask)
                with ordered_attention_math():h,_,_=fixed4_training(core,query,None,query_mask=mask)
                observed=sealed.observe_generation(dec,FinalLatent(h,torch.ones_like(h,dtype=torch.bool),mask,(1,h.shape[1])),32)
                native+=1
                write('OBSERVATIONS.jsonl',{'call_index':native,'seed':seed,'arm':arm,'id':f['id'],'checkpoint_sha256':closed['checkpoint']['sha256'],**observed},True,False)

            for name,module in (('core',core),('reader',reader),('prefix',dec.adapter)):
                assert component_fingerprint(module)==closed['final_fingerprints'][name]
            del core,reader;torch.cuda.empty_cache()
    assert native==128 and component_fingerprint(lm)==lm_before
    raw_hash=sha(out/'OBSERVATIONS.jsonl')
    saved=[json.loads(line) for line in (out/'OBSERVATIONS.jsonl').read_bytes().splitlines()]
    results,answers=score_saved(saved,frames,cfg['execution_order'],sealed.score_observed_generation,dec.eos_id)
    for answer in answers:write('ANSWERS.jsonl',answer,True)
    assert sha(out/'OBSERVATIONS.jsonl')==raw_hash
    write('CLOSED.json',{'closed':True,'schema':'cap256.confirmation32.closed.v1','config_sha256':a.config_sha256,'native_calls':native,'teacherforced_dev_examples':0,'optimizer_updates':0,'results':results,'raw_frozen_before_scoring':True,'wall_seconds':time.monotonic()-started,'raw_sha256':sha(out/'ANSWERS.jsonl'),'observations_sha256':raw_hash})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--config',required=True);p.add_argument('--config-sha256',required=True)
    run(p.parse_args())
