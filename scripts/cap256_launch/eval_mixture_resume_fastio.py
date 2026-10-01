"""Once-only fixed dev32 endpoint evaluation:128 native calls, no updates."""
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


def run(a):
    root=Path(a.root);cfg=read(a.config)
    assert sha(a.config)==a.config_sha256 and cfg['dispatch_allowed'] is True
    for name in ('source_plan','source_seal','source_release','source_runner','dev_frames','storage_snapshot'):
        pin=cfg[name];assert sha(root/pin['path'])==pin['sha256']
    storage_spec=importlib.util.spec_from_file_location('_pinned_storage',root/cfg['storage_snapshot']['path'])
    storage=importlib.util.module_from_spec(storage_spec);storage_spec.loader.exec_module(storage)
    allocated_bytes=storage.allocated_bytes
    old=read(root/cfg['source_plan']['path'])
    for path,digest in read(root/cfg['source_seal']['path'])['files'].items():assert sha(root/path)==digest
    spec=importlib.util.spec_from_file_location('_sealed_mixture_eval',root/cfg['source_runner']['path'])
    sealed=importlib.util.module_from_spec(spec);spec.loader.exec_module(sealed);sealed.validate_plan(old)
    frames=read(root/cfg['dev_frames']['path'])['rows']
    assert len(frames)==32 and len({f['id'] for f in frames})==32
    assert not {f['id'] for f in frames}&set(cfg['original_ids']+cfg['additional_ids'])
    assert len({f['group'] for f in frames})==8
    matrix=root/cfg['output_namespace'];out=matrix/'dev32'
    extra_paths=[root/p for p in cfg['output_accounting_extra_paths']]
    assert not out.exists(),'existing dev claim; no duplicate evaluation'
    endpoints=[]
    for seed,arm in cfg['execution_order']:
        folder=matrix/('seed%d'%seed)/arm;closed=read(folder/'CLOSED.json')
        assert closed['closed'] and closed['additional_optimizer_updates']==10240
        cp=root/closed['checkpoint']['path'];assert sha(cp)==closed['checkpoint']['sha256']
        endpoints.append((seed,arm,closed,cp))
    unit=sealed.filesystem_allocation_unit(root);started=time.monotonic();out.mkdir()
    def guard(extra=0,check_wall=True):
        if check_wall:assert time.monotonic()-started<=1200,'fixed eval wall cap'
        assert allocated_bytes(matrix,unit)+sum(allocated_bytes(p,unit) for p in extra_paths)+extra<=1342177280
        assert allocated_bytes(root,unit)+extra<=cfg['budget']['project_cap_bytes']
        assert shutil.disk_usage(root).free-extra>=2**30
    def write(name,record,append=False,check_wall=True):
        raw=(json.dumps(record,sort_keys=True,allow_nan=False)+'\n').encode();guard(len(raw)+unit,check_wall)
        with (out/name).open('ab' if append else 'xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    write('CLAIM.json',{'config_sha256':a.config_sha256,'optimizer_updates':0,'native_call_limit':128})
    sys.path[:0]=[str(root),str(root/'scripts')]
    import torch
    from sol_translator_grounding_v6 import HumanInputProjection,human_loss
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
    native=0;ce_calls=0;results=[]
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
                labels=torch.tensor(f['labels'],device='cuda');query=reader(lm.get_input_embeddings()(ids),mask)
                with ordered_attention_math():h,_,_=fixed4_training(core,query,None,query_mask=mask)
                prefix=dec.adapter.project_training(h,torch.ones_like(h,dtype=torch.bool),mask,(1,h.shape[1]))
                observed=sealed.observe_generation(dec,FinalLatent(h,torch.ones_like(h,dtype=torch.bool),mask,(1,h.shape[1])),32)
                native+=1
                write('OBSERVATIONS.jsonl',{'call_index':native,'seed':seed,'arm':arm,'id':f['id'],'checkpoint_sha256':closed['checkpoint']['sha256'],**observed},True,False)
                exact=sealed.score_observed_generation(observed,f['labels'][0],dec.eos_id);correct+=exact
                per,_=human_loss(lm,prefix,labels,dec.bos_id,dec.eos_id,True,True);ce_calls+=1
                write('ANSWERS.jsonl',{'seed':seed,'arm':arm,'id':f['id'],'group':f['group'],'checkpoint_sha256':closed['checkpoint']['sha256'],'canonical_target_ids_with_EOS':f['labels'][0],'strict_exact':exact,'numeric_CE':float(per.mean()),**observed},True)
            results.append({'seed':seed,'arm':arm,'strict_correct':correct,'rows':32})
            for name,module in (('core',core),('reader',reader),('prefix',dec.adapter)):
                assert component_fingerprint(module)==closed['final_fingerprints'][name]
            del core,reader;torch.cuda.empty_cache()
    assert native==ce_calls==128 and component_fingerprint(lm)==lm_before
    write('CLOSED.json',{'closed':True,'native_calls':native,'teacherforced_dev_examples':ce_calls,'optimizer_updates':0,'results':results,'wall_seconds':time.monotonic()-started,'raw_sha256':sha(out/'ANSWERS.jsonl'),'observations_sha256':sha(out/'OBSERVATIONS.jsonl')})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--config',required=True);p.add_argument('--config-sha256',required=True)
    run(p.parse_args())
