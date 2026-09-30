#!/usr/bin/env python3
"""Queued full FP32 actual reader+core+notebook graph memory preflight."""
import argparse,json,os,shutil,time
from pathlib import Path
import torch
import claude_fewex_net as N
from sol_spatial_attention_core import AttentionReasoner
from sol_spatial_poc_memory import probe_grounding_memory
from sol_translator_english_v3 import load_local_lm,FrozenEnglishDecoder
from sol_translator_grounding_v3 import HumanInputProjection,human_loss
from sol_translator_provenance import sha
ROOT=Path(__file__).resolve().parents[1];OWN=ROOT/'artifacts/sol-translator-20260929'


def run(a):
    if not os.environ.get('JOB') or not os.environ.get('TREE'):raise RuntimeError('queue context required')
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);p=Path(a.model)
    if shutil.disk_usage(p).free<2*1024**3:raise RuntimeError('2GiB disk floor')
    files={f.relative_to(p).as_posix():sha(f) for f in p.iterdir() if f.is_file() and f.suffix in ('.safetensors','.bin','.json')}
    prov={'model_id':'LiquidAI/LFM2.5-1.2B-Instruct','revision':p.name,'training_origin_disclosure':'Frozen pretrained component permitted; original human/synthetic pretraining mixture UNVERIFIED. NEW adaptation only verified human SQuAD TRAIN verbatim. No project synthetic weights admitted.','frozen_component_allowed':True,'files':files}
    pp=out/'LFM-provenance.json';pp.write_text(json.dumps(prov,indent=2)+'\n')
    source_hash=sha(a.source);start=time.monotonic()
    try:
        torch.set_num_threads(2);torch.manual_seed(a.seed)
        lm,tok,_=load_local_lm(p,pp,a.device)
        assert all(p.dtype==torch.float32 and not p.requires_grad for p in lm.parameters() if p.is_floating_point()),'FULL FP32/frozen'
        source=N.Net('loop');raw=torch.load(a.source,map_location='cpu',weights_only=True);source.load_state_dict(raw.get('state',raw))
        core=AttentionReasoner(source).to(a.device)
        reader=HumanInputProjection(lm.get_input_embeddings().weight.shape[1]).to(a.device)
        decoder=FrozenEnglishDecoder(lm,256,tok.bos_token_id,tok.eos_token_id,prefix_tokens=8).to(a.device)
        record=probe_grounding_memory(lm,core,reader,decoder,human_loss,seed=a.seed,source_sha256=source_hash,plan_sha256=sha(OWN/'DEPLOYMENT-V3-PLAN.json'))
        record.update({'wrapper_sha256':sha(__file__),'model_provenance_sha256':sha(pp),'deployment_v3_seal_sha256':sha(OWN/'DEPLOYMENT-V3-SEAL.json'),'deployment_v4_seal_sha256':sha(OWN/'DEPLOYMENT-V4-SEAL.json'),'reader_driver_sha256':sha(ROOT/'scripts/sol_translator_grounding_v3.py'),'total_preflight_seconds':time.monotonic()-start,'child_exit_before_TRAIN':True,'training_first_optimizer_peak':'NOT YET MEASURED'})
        (out/'MEMORY-PREFLIGHT.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps({k:v for k,v in record.items() if k!='raw_numeric_records'}),flush=True)
        if not record['cap_guard_passed']:raise RuntimeError('FULL-GRAPH FP32 MEMORY CAP failed; no BF16 fallback')
    except BaseException as e:
        record={'status':'FAILED before TRAIN','seed':a.seed,'error_type':type(e).__name__,'error':str(e),'source_sha256':source_hash,'wrapper_sha256':sha(__file__),'probe_sha256':sha(ROOT/'scripts/sol_spatial_poc_memory.py'),'optimizer_steps':0,'precision':'FULL FP32; no BF16 fallback','wall_seconds':time.monotonic()-start}
        (out/'MEMORY-FAILURE.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True);raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--source',required=True);p.add_argument('--seed',required=True,type=int,choices=(0,1));p.add_argument('--out',required=True);p.add_argument('--device',default='cuda');run(p.parse_args())
