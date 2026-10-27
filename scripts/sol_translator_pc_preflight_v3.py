#!/usr/bin/env python3
"""Read/forward/gradient compatibility probe on cached PC LFM; NO optimization.
Hashes existing weights in place, no model copy, download or rental.
"""
import argparse,json,shutil,time
from pathlib import Path
import torch
from sol_translator_provenance import sha
from sol_translator_english_v3 import load_local_lm,FrozenEnglishDecoder
from sol_translator_decoder import FinalLatent
DEFAULT='C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b'


def run(a):
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);p=Path(a.model)
    if not p.is_dir():raise SystemExit('WAITING: cached PC LFM absent')
    free=shutil.disk_usage(p).free
    if free<2*1024**3:raise SystemExit('WAITING: less than2GiB free; no files removed')
    files={f.relative_to(p).as_posix():sha(f) for f in p.iterdir() if f.is_file() and f.suffix in ('.safetensors','.bin','.json')}
    prov={'model_id':'LiquidAI/LFM2.5-1.2B-Instruct','revision':p.name,'training_origin_disclosure':'Frozen pretrained instructed model; exact pretraining/SFT mixture human-vs-synthetic NOT verified. User explicitly permits a frozen pretrained component. No synthetic project fine-tune or adapter is admitted; NEW adaptation text is SQuAD human TRAIN only.','frozen_component_allowed':True,'files':files}
    pp=out/'LFM-provenance.json';pp.write_text(json.dumps(prov,indent=2)+'\n')
    start=time.monotonic();lm,tok,_=load_local_lm(p,pp,a.device)
    torch.manual_seed(1);h=torch.randn(1,4,256,device=a.device);f=FinalLatent(h,torch.ones_like(h,dtype=torch.bool),torch.ones(1,4,device=a.device,dtype=torch.bool),(1,4))
    dec=FrozenEnglishDecoder(lm,256,tok.bos_token_id,tok.eos_token_id).to(a.device)
    # Symbolic random-tensor gradient probe only; no English target text authored.
    ids,lg=dec.rollout(f,2);lg.square().mean().backward()
    live=sum(int(p.grad is not None and bool(p.grad.abs().sum()>0)) for p in dec.adapter.parameters());n=sum(1 for _ in dec.adapter.parameters())
    if live!=n or any(p.grad is not None for p in lm.parameters()):raise RuntimeError('gradient/freeze probe failed')
    generated=dec.generate(f,8)
    # Disclosed SYMBOLIC 64-token gradient budget probe: eight teacher-forced
    # forwards match two rows xfour rounds, zero optimization/human scoring.
    del lg
    dec.adapter.zero_grad(set_to_none=True)
    labels=torch.arange(64,device=a.device).unsqueeze(0)%lm.get_input_embeddings().weight.shape[0]
    losses=[dec.target_loss(f,labels) for _ in range(8)]
    torch.stack(losses).mean().backward()
    if any(p.grad is not None for p in lm.parameters()):raise RuntimeError('LM gradient in budget probe')
    if lm.get_input_embeddings().weight.dtype!=torch.float32 or lm.get_output_embeddings().weight.dtype!=torch.float32:raise RuntimeError('FP32 lexical/head assertion')
    if str(a.device).startswith('cuda'):
        total=torch.cuda.get_device_properties(0).total_memory
        peak=torch.cuda.max_memory_allocated()
        if peak>int(.9*total):raise RuntimeError('symbolic worst-length gradient probe leaves insufficient core VRAM')
    record={'scope':'cached-real-weight API compatibility ONLY','model_path':str(p),'revision':p.name,'model_provenance_sha256':sha(pp),'torch':torch.__version__,'cuda':torch.version.cuda,'device':a.device,'GPU':torch.cuda.get_device_name() if str(a.device).startswith('cuda') else None,'LM_stored_parameters':sum(p.numel() for p in lm.parameters()),'adapter_parameters':dec.adapter.parameter_count(),'live_adapter_tensors':live,'adapter_tensors':n,'generated_token_counts':[len(x) for x in generated],'optimizer_steps':0,'human_or_semantic_examples':0,'grammar_and_grounding':'UNTESTED','wall_seconds':time.monotonic()-start,'free_disk_before':free,'peak_cuda_bytes':torch.cuda.max_memory_allocated() if str(a.device).startswith('cuda') else None,'no_model_download':True,'no_model_copy':True,'LM_embedding_dtype':str(lm.get_input_embeddings().weight.dtype),'LM_head_dtype':str(lm.get_output_embeddings().weight.dtype),'symbolic_teacher_forcing_budget_forwards':8,'symbolic_target_tokens':64,'GPU_total_bytes':torch.cuda.get_device_properties(0).total_memory if str(a.device).startswith('cuda') else None,'VRAM_assertion':'peak <=90%physical after eight64token TRAIN-shaped frozen-LM gradients','precision_policy':'full frozen FP32 LM including lexical/head; FP32 thin adapter/core'}
    (out/'PC-preflight.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',default=DEFAULT);p.add_argument('--device',default='cuda');p.add_argument('--out',required=True);a=p.parse_args();run(a)
