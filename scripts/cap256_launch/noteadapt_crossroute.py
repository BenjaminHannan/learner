"""Frozen TRAIN-only off-diagonal placement diagnostic; no optimization."""
import argparse
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
from noteadapt_initial import sha, read, now, digest


def literal(row,placement):
    assert placement in ['notebook','inline']
    return (row['question'],row['history']) if placement=='notebook' else (row['history']+'\n'+row['question'],'')


def validate(p):
    assert p['schema']=='cap256.noteadapt.crossroute.release.v1'
    assert p['native_calls']==128 and p['optimizer_updates']==0 and p['wall_seconds']==600
    assert p['output_cap_bytes']==64*2**20 and p['reserve_bytes']==2**30 and p['project_cap_bytes']==100*2**30
    assert p['fixed_rounds']==4 and p['TEST_calls']==0
    assert len(p['cases'])==len(set(p['cases']))==32 and len(p['arms'])==4
    assert {(a['seed'],a['training_placement'],a['inference_placement']) for a in p['arms']}=={(s,t,'inline' if t=='notebook' else 'notebook') for s in [0,1] for t in ['notebook','inline']}
    return p


def run(a):
    root=Path(a.root).resolve();p=validate(read(a.plan));assert sha(a.plan)==a.plan_sha256
    assert os.environ['TREE']==str(root) and os.environ['JOB']
    def pin(v):
        path=(root/v['path']).resolve();assert path.is_relative_to(root) and sha(path)==v['sha256'];return path
    for v in p['file_pins']:pin(v)
    assert sha(p['diagonal']['path'])==p['diagonal']['sha256']
    rows=[json.loads(s) for s in pin(p['TRAIN_inputs']).read_text().splitlines()];assert [r['id'] for r in rows]==p['cases']
    assert all(r['assignment']=='TRAIN' and r['stage']=='initial' for r in rows)
    for v in p['arms']:
        assert sha(v['checkpoint']['path'])==v['checkpoint']['sha256'] and sha(v['diagonal_frames']['path'])==v['diagonal_frames']['sha256']
        m=read(pin(v['manifest']))
        assert m['seed']==v['seed'] and m['arm']=='loop'
        for name,h in m['code_pins'].items():assert sha(root/name)==h
    spec=importlib.util.spec_from_file_location('_resource',root/'scripts/sol_cloud_capability256_v1.py');res=importlib.util.module_from_spec(spec);spec.loader.exec_module(res)
    matrix=root/p['output_namespace'];assert not matrix.exists(),'no duplicate attempt';unit=res.filesystem_allocation_unit(root)
    def resource(extra=0):
        assert shutil.disk_usage(root).free>=p['reserve_bytes']+extra and res.allocated_bytes(root,unit)+extra<=p['project_cap_bytes']
        assert res.allocated_bytes(matrix,unit)+extra<=p['output_cap_bytes']
    resource(p['output_cap_bytes']);matrix.mkdir(parents=True)
    identity={'job':os.environ['JOB'],'plan_sha256':a.plan_sha256};start=time.monotonic();calls=0;active={};reports=[]
    def write(name,v,append=False):
        b=(json.dumps(v,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode();resource(len(b)+unit)
        with (matrix/name).open('ab' if append else 'xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
    write('CLAIM.json',{**identity,'utc':now(),'native_calls_expected':128,'optimizer_updates':0,'TEST_calls':0})
    try:
        sys.path[:0]=[str(root),str(root/'scripts')]
        import torch
        from sol_nextdemo_runtime_v1 import Runtime
        from sol_translator_runtime import component_fingerprint
        import sol_cloud_numeric_fit_v2 as observer
        assert torch.cuda.is_available() and torch.cuda.get_device_properties(0).total_memory<=16*2**30
        original_observe=observer.observe_generation
        def observed(*args,**kwargs):
            nonlocal calls
            assert calls<128 and time.monotonic()-start<600
            value=original_observe(*args,**kwargs);calls+=1
            write('NATIVE-RAW.jsonl',{**identity,**active,'native_call_index':calls,'observed':value},True)
            return value
        observer.observe_generation=observed
        for v in p['arms']:
            assert time.monotonic()-start<600
            runtime=Runtime(str(pin(v['manifest'])),v['manifest']['sha256']);r=runtime.r
            cp=torch.load(v['checkpoint']['path'],map_location='cpu',weights_only=True)
            assert cp['updates']==1280 and cp['schema']=='cap256.noteadapt.continuation40.checkpoint.v1' and cp['seed']==v['seed'] and cp['placement']==v['training_placement']
            for name,module in [('core',r['core']),('reader',r['reader']),('prefix',r['dec'].adapter)]:module.load_state_dict(cp[name],strict=True);module.eval().requires_grad_(False)
            modules={'core':r['core'],'reader':r['reader'],'prefix':r['dec'].adapter,'lm':r['dec'].lm}
            before={k:component_fingerprint(m) for k,m in modules.items()};assert before==cp['fingerprints'];del cp
            runtime.manifest['checkpoint']=v['checkpoint']
            frames=[json.loads(s) for s in Path(v['diagonal_frames']['path']).read_text().splitlines()];assert [f['id'] for f in frames]==p['cases']
            for row,frame in zip(rows,frames):
                assert time.monotonic()-start<600
                q,c=literal(row,v['inference_placement'])
                assert r['tok'].encode(q,add_special_tokens=False)+[r['dec'].eos_id]==frame['input_ids'][0]
                assert r['tok'].encode(c,add_special_tokens=False)==frame['notebook_ids'][0]
                assert len(frame['input_ids'][0])<=48
                active.update(seed=v['seed'],training_placement=v['training_placement'],inference_placement=v['inference_placement'],id=row['id'])
                answer=runtime.answer(q,c,'full')
                assert answer['input_ids']==frame['input_ids'] and answer['input_mask']==frame['input_mask'] and answer['notebook_ids']==frame['notebook_ids'] and answer['notebook_mask']==frame['notebook_mask']
                assert answer['rounds']==4 and answer['optimizer_updates']==0 and answer['checkpoint']==v['checkpoint']
                write('ANSWERS.jsonl',{**identity,**active,'native_call_index':calls,'answer':answer},True)
                if calls==1:write('FIRST-PREDICTION.json',{**identity,**active,'utc':now(),'native_call_index':1})
            assert {k:component_fingerprint(m) for k,m in modules.items()}==before and sha(v['checkpoint']['path'])==v['checkpoint']['sha256']
            reports.append({'seed':v['seed'],'training_placement':v['training_placement'],'inference_placement':v['inference_placement'],'checkpoint':v['checkpoint'],'weights_unchanged':True})
            del r,runtime,modules;gc.collect();torch.cuda.empty_cache()
        assert calls==128 and time.monotonic()-start<600
        assert sha(p['diagonal']['path'])==p['diagonal']['sha256']
        write('CLOSED.json',{**identity,'closed':True,'native_calls':calls,'optimizer_updates':0,'TEST_calls':0,'reports':reports,'native_raw_sha256':sha(matrix/'NATIVE-RAW.jsonl'),'answers_sha256':sha(matrix/'ANSWERS.jsonl'),'wall_seconds':time.monotonic()-start,'peak_cuda_allocated_bytes':torch.cuda.max_memory_allocated(),'generalization_claim':False,'unique_causal_component_claim':False})
    except Exception as e:
        write('FAILED.json',{**identity,'utc':now(),'native_calls':calls,'error_type':type(e).__name__,'error':str(e)});raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--plan',required=True);p.add_argument('--plan-sha256',required=True);run(p.parse_args())
