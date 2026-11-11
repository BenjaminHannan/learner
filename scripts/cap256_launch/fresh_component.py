"""Presealed fresh new-story/seen-footprint comparison; fixed eight endpoints.

No optimizer, checkpoint selection, dataset redraw, or heldout-driven adaptation.
Uses the original sealed native generation observer and strict emitted-EOS scorer.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def read(p):return json.loads(Path(p).read_bytes())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run(a):
    root=Path(a.root).resolve();m=read(a.manifest)
    assert sha(a.manifest)==a.manifest_sha256
    assert m['component']=='seen' and m['expected_rows']==64 and m['fixed_rounds']==4
    assert m['optimizer_updates']==0 and m['owner']=='Mac-PC' and m['worker_seconds']==1800
    assert m['checkpoint_keys']==['s0-loop-v20','s0-loop-v40','s0-plain-v20','s0-plain-v40','s1-loop-v20','s1-loop-v40','s1-plain-v20','s1-plain-v40']
    assert os.environ['TREE']==str(root) and os.environ['JOB']
    def pin(p):
        path=(root/p['path']).resolve();assert path.is_relative_to(root)
        assert sha(path)==p['sha256'],p['path'];return path
    for p in m['file_pins']:pin(p)
    old=read(pin(m['source_plan']));seal=read(pin(m['source_seal']))
    for p,h in seal['files'].items():assert sha(root/p)==h,'sealed runtime differs: '+p
    spec=importlib.util.spec_from_file_location('_sealed_fresh',pin(m['source_runner']))
    s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s);s.validate_plan(old)
    frozen={}
    for e in m['checkpoints']:
        cp=pin(e['checkpoint']);cl=read(pin(e['closed']))
        assert cl['closed'] is True and cl['checkpoint']==e['original_checkpoint_pin']
        assert cl['checkpoint']['sha256']==e['checkpoint']['sha256']
        assert cl['optimizer_updates']==e['expected_update']
        frozen[e['key']]=(e,cl,cp)
    questions=[json.loads(l) for l in pin(m['questions']).read_bytes().splitlines()]
    assert [r['id'] for r in questions]==m['selected_ids'] and len(set(m['selected_ids']))==64
    for r in questions:assert hashlib.sha256(r['question'].encode()).hexdigest()==r['question_sha256']
    loc={r['id']:r for r in m['locators']};assert set(loc)==set(m['selected_ids'])
    binding=old['warmstart']['tuples']
    for b in binding.values():
        for k in ('parent','reader','adapter'):assert sha(b[k+'_path'])==b[k+'_sha256']
        assert sha(b['lm_provenance'])==old['LM_provenance']['sha256']
        for f in m['tokenizer_files']:assert sha(Path(b['lm_path'])/f['name'])==f['sha256']
    matrix=root/m['output_namespace'];assert not matrix.exists(),'prior output/claim exists; no repeat'
    unit=s.filesystem_allocation_unit(root)
    def resource(increase=0):
        assert shutil.disk_usage(root).free>=2**30+increase,'free reserve'
        assert s.allocated_bytes(root,unit)+increase<=107374182400,'project cap'
        assert s.allocated_bytes(matrix,unit)+increase<=1140850688,'output cap'
    resource(1140850688);matrix.mkdir(parents=True)
    launched=time.monotonic();identity={'schema':'cap256.fresh-newstory-seen.v1','job':os.environ['JOB'],'manifest_sha256':a.manifest_sha256,'component':'seen','optimizer_updates':0,'partial_component_only':True,'full_capability_gate_claim':False}
    def write(p,r,append=False):
        data=(json.dumps(r,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode();resource(len(data)+unit)
        with p.open('ab' if append else 'xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    write(matrix/'CLAIM.json',{**identity,'utc':now(),'checkpoint_keys':m['checkpoint_keys'],'no_retries_or_redraw':True})
    completed=[];calls=0
    try:
        sys.path[:0]=[str(root),str(root/'scripts')]
        import torch
        from sol_translator_grounding_v6 import HumanInputProjection
        from sol_translator_english_ordered_v10 import load_ordered_english
        from sol_spatial_poc_ordered_v2 import load_ordered_bundle,OrderedPlainAttentionReasoner
        from sol_spatial_poc_ordered_train_api_v2 import fixed4_training
        from scripts.sol_stop_ordered_api2 import ordered_attention_math
        from sol_translator_decoder import FinalLatent
        from sol_translator_runtime import component_fingerprint
        torch.set_num_threads(2)
        assert torch.cuda.is_available() and torch.cuda.get_device_properties(0).total_memory<=16*2**30
        os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
        b=binding['0'];dec,tok,_=load_ordered_english(b['lm_path'],b['lm_provenance'],b['adapter_path'],'cuda')
        lm=dec.lm;lm.eval().requires_grad_(False);lmfp=component_fingerprint(lm)
        modal=s.modal_train_target(s.load_numeric_slice(old['source'],old['selected_ids']));modalids=tok.encode(modal,add_special_tokens=False)+[dec.eos_id]
        tokens=[]
        for r in questions:
            ids=tok.encode(r['question'],add_special_tokens=False);assert ids and len(ids)+1<=48 and dec.eos_id not in ids
            assert len(ids)+1==r['known_question_plus_EOS_tokens']
            tokens.append(torch.tensor([ids+[dec.eos_id]],dtype=torch.long,device='cuda'))
        write(matrix/'MODEL-LOADED.json',{**identity,'utc':now(),'device':torch.cuda.get_device_name(0),'torch':torch.__version__,'native_calls':0})
        for key in m['checkpoint_keys']:
            e,cl,cp=frozen[key];b=binding[str(e['seed'])]
            assert b['lm_path']==binding['0']['lm_path']
            loop,_=load_ordered_bundle(b['parent_path'],'cuda');core=loop if e['arm']=='loop' else OrderedPlainAttentionReasoner(loop).to('cuda')
            if e['arm']=='plain':del loop
            rr=torch.load(b['reader_path'],map_location='cpu',weights_only=True);reader=HumanInputProjection(rr['lm_width']).to('cuda');del rr
            checkpoint=torch.load(cp,map_location='cpu',weights_only=True)
            assert checkpoint['update']==e['expected_update'] and checkpoint['constructor']==core.constructor()
            for n,module in [('core',core),('reader',reader),('prefix',dec.adapter)]:
                module.load_state_dict(checkpoint[n],strict=True);module.eval().requires_grad_(False)
                assert component_fingerprint(module)==cl['final_fingerprints'][n]
            del checkpoint
            out=matrix/key;out.mkdir();correct=zero_correct=modal_correct=0
            for r,ids in zip(questions,tokens):
                assert time.monotonic()-launched<1800,'wall budget exhausted; preserve partials'
                resource()
                with torch.no_grad():
                    mask=torch.ones_like(ids,dtype=torch.bool);query=reader(lm.get_input_embeddings()(ids),mask)
                    with ordered_attention_math():h,_,_=fixed4_training(core,query,None,query_mask=mask)
                    obs=s.observe_generation(dec,FinalLatent(h.detach(),torch.ones_like(h,dtype=torch.bool),mask,(1,h.shape[1])),32);calls+=1
                    with ordered_attention_math():state=core.begin_latent(query,None,query_mask=mask);zh,_=core.read_latent(state)
                    zero=s.observe_generation(dec,FinalLatent(zh.detach(),torch.ones_like(zh,dtype=torch.bool),mask,(1,zh.shape[1])),32);calls+=1
                # Gold is joined only after both native calls; no answer is fed back.
                rec={**identity,'checkpoint_key':key,'seed':e['seed'],'arm':e['arm'],'endpoint_visits':e['visits'],'id':r['id'],'question_sha256':r['question_sha256'],'checkpoint_sha256':e['checkpoint']['sha256'],'fixed_rounds':4,'notebook_tokens':0,'label_join_after_raw_generation':True,**obs,'native_zero_loop':zero}
                try:
                    target=s.terminal_target(m['targets'],loc[r['id']],r['question_sha256']);tids=tok.encode(target,add_special_tokens=False)+[dec.eos_id];assert len(tids)<=64
                    hit=s.score_observed_generation(obs,tids,dec.eos_id);zhit=s.score_observed_generation(zero,tids,dec.eos_id)
                    rec.update(canonical_target_ids_with_EOS=tids,target_ids_plus_observed_EOS_exact=hit,TRAIN_modal_numeric_target=modal,TRAIN_modal_target_ids_with_EOS=modalids,TRAIN_modal_constant_ids_equal=modalids==tids,TRAIN_modal_model_calls=0,TRAIN_modal_actual_terminal_EOS_observed=False)
                    rec['native_zero_loop']={**zero,'target_ids_plus_observed_EOS_exact':zhit}
                except Exception as error:
                    rec['terminal_scoring_error']={'error_type':type(error).__name__,'error':str(error)}
                    write(out/'RAW.jsonl',rec,True)
                    raise
                write(out/'RAW.jsonl',rec,True);correct+=hit;zero_correct+=zhit;modal_correct+=modalids==tids
                if not (matrix/'FIRST-PREDICTION.json').exists():write(matrix/'FIRST-PREDICTION.json',{**identity,'utc':now(),'checkpoint_key':key,'saved_predictions':1,'native_calls':calls})
            for n,module in [('core',core),('reader',reader),('prefix',dec.adapter)]:assert component_fingerprint(module)==cl['final_fingerprints'][n]
            result={**identity,'checkpoint_key':key,'correct':correct,'total':64,'absolute52_mark_met':correct>=52,'zero_loop_correct':zero_correct,'TRAIN_modal_correct':modal_correct,'raw_sha256':sha(out/'RAW.jsonl'),'checkpoint_sha256':e['checkpoint']['sha256'],'closed':True}
            write(out/'CLOSED.json',result);completed.append(result);del core,reader;torch.cuda.empty_cache()
        assert component_fingerprint(lm)==lmfp and calls==1024
        write(matrix/'CLOSED.json',{**identity,'closed':True,'utc':now(),'completed':completed,'native_calls':calls,'wall_seconds':time.monotonic()-launched,'peak_cuda_allocated_bytes':torch.cuda.max_memory_allocated()})
    except Exception as ex:
        write(matrix/'FAILURE.json',{**identity,'utc':now(),'error_type':type(ex).__name__,'error':str(ex),'native_calls':calls,'wall_seconds':time.monotonic()-launched});raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--manifest',required=True);p.add_argument('--manifest-sha256',required=True);run(p.parse_args())
