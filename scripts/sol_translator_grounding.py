#!/usr/bin/env python3
"""Staged HUMAN grounding; queue-only optimization, shared core training API.
Not a frozen-parent decoder proof. Does not implement inference execution.
"""
from __future__ import annotations
import argparse,copy,json,os,random,time
from pathlib import Path
import torch
from torch import nn
from sol_translator_english import FrozenEnglishDecoder,load_local_lm
from sol_translator_provenance import sha,safe_source
from sol_translator_runtime import component_fingerprint
from sol_spatial_attention_core import AttentionReasoner,load_bundle
import claude_fewex_net as N
ROOT=Path(__file__).resolve().parents[1]
OWN=ROOT/'artifacts/sol-translator-20260929'


def human_rows(corpus):
    corpus=Path(corpus);reg=json.loads((corpus/'registry.json').read_text());rows=json.loads((corpus/'pairs.json').read_text())
    raw=json.loads((corpus/'train-v1.1.json').read_text())
    originals={qa['id']:(qa['question'],para['context'],qa['answers']) for article in raw['data'] for para in article['paragraphs'] for qa in para['qas']}
    if reg['verification_status']!='verified-human-origin' or reg['official_dev_or_test_accessed'] or reg['raw_training_sha256']!=sha(corpus/'train-v1.1.json'):
        raise ValueError('human TRAIN corpus provenance failed')
    documents={'train':set(),'dev':set()};keys={'train':set(),'dev':set()};checked=set()
    for row in rows:
        question,context,answers=originals[row['id']]
        if row['question']!=question or row['context']!=context or row['answer_text'] not in {x['text'] for x in answers}:raise ValueError('input/answer not verbatim HUMAN annotation')
        p=safe_source(row['source_path'],ROOT);evidence=reg['sources'][row['source_path']]
        if evidence['origin']!='human-authored' or evidence['sha256']!=row['source_sha256']:raise ValueError('origin mismatch')
        if p not in checked:
            if sha(p)!=row['source_sha256']:raise ValueError('source changed')
            checked.add(p)
        begin,end=row['source_span']
        with p.open('rb') as f:f.seek(begin);text=f.read(end-begin).decode()
        if text!=row['target_text'] or row['answer_text'] not in text:raise ValueError('human evidence span mismatch')
        documents[row['split']].add(p);keys[row['split']].add(row['content_key'])
    if documents['train']&documents['dev'] or keys['train']&keys['dev']:raise ValueError('TRAIN/dev leakage')
    return rows,reg


class HumanInputProjection(nn.Module):
    """Frozen pretrained lexical vectors -> thin learnable nonlinguistic state.
No transformer, question solver, answer lookup or output text exists here.
"""
    def __init__(self,lm_width,state_width=256,hidden=32):
        super().__init__();self.proj=nn.Sequential(nn.LayerNorm(lm_width),nn.Linear(lm_width,hidden),nn.GELU(),nn.Linear(hidden,state_width))
    def forward(self,embeddings,valid):
        return (self.proj(embeddings.float())*valid[...,None]).unsqueeze(1)


def input_tokens(tokenizer,rows,device,max_question=48,max_context=256):
    seq=[]
    for row in rows:
        # Human question/context only; constant EOS separates fields. No prompt
        # frame, label-dependent crop, answer span or target goes to input.
        q=tokenizer.encode(row['question'],add_special_tokens=False)[:max_question]
        c=tokenizer.encode(row['context'],add_special_tokens=False)[:max_context]
        seq.append(q+[tokenizer.eos_token_id]+c)
    n=max(map(len,seq));ids=torch.full((len(seq),n),tokenizer.eos_token_id,device=device,dtype=torch.long);valid=torch.zeros_like(ids,dtype=torch.bool)
    for i,row in enumerate(seq):ids[i,:len(row)]=torch.tensor(row,device=device);valid[i,:len(row)]=True
    return ids,valid


def target_tokens(tokenizer,rows,device,max_tokens=64):
    seq=[]
    for row in rows:
        ids=tokenizer.encode(row['target_text'],add_special_tokens=False)+[tokenizer.eos_token_id]
        if len(ids)>max_tokens:raise ValueError('human target exceeds sealed token budget; no truncated grammatical targets')
        seq.append(ids)
    out=torch.full((len(seq),max(map(len,seq))),-100,device=device,dtype=torch.long)
    for i,row in enumerate(seq):out[i,:len(row)]=torch.tensor(row,device=device)
    return out


def human_loss(lm,prefix,target,bos,eos,return_per_example=False):
    emb=lm.get_input_embeddings();start=torch.full((len(target),1),bos,device=target.device,dtype=torch.long)
    shifted=torch.cat((start,target[:,:-1].masked_fill(target[:,:-1]==-100,eos)),1)
    x=torch.cat((prefix.to(emb.weight.dtype),emb(shifted)),1)
    attention=torch.cat((torch.ones(prefix.shape[:2],device=x.device,dtype=torch.long),(target!=-100).long()),1)
    logits=lm(inputs_embeds=x,attention_mask=attention,use_cache=False).logits[:,prefix.shape[1]:].float()
    loss=torch.nn.functional.cross_entropy(logits.transpose(1,2),target,ignore_index=-100,reduction='none')
    per=loss.sum(1)/(target!=-100).sum(1)
    return per if return_per_example else per.mean()


def guard_queue():
    if not os.environ.get('JOB') or not os.environ.get('TREE'):
        raise SystemExit('QUEUE-ONLY: optimization requires watcher JOB and TREE context')


def ground(a):
    guard_queue();out=Path(a.out).resolve()
    if not out.is_relative_to(OWN):raise ValueError('owned output directory required')
    out.mkdir(parents=True,exist_ok=True);plan=json.loads((OWN/'GROUNDING-PLAN.json').read_text())
    torch.set_num_threads(2);torch.manual_seed(a.seed)
    rows,reg=human_rows(a.corpus);train=[r for r in rows if r['split']=='train']
    lm,tok,provenance=load_local_lm(a.model,a.model_provenance,a.device)
    # Preflight targets BEFORE any optimizer: no target truncation or silent row removal.
    for row in train:target_tokens(tok,[row],a.device)
    if a.spatial_bundle:
        core,source_meta=load_bundle(a.spatial_bundle,a.device);source_hash=sha(a.spatial_bundle)
    else:
        source=N.Net('loop');payload=torch.load(a.source,map_location='cpu',weights_only=True)
        source.load_state_dict(payload.get('state',payload));core=AttentionReasoner(source).to(a.device);source_hash=sha(a.source);source_meta={'qualification':'symbolic qualified source; English not qualified'}
    reader=HumanInputProjection(lm.get_input_embeddings().weight.shape[1]).to(a.device)
    decoder=FrozenEnglishDecoder(lm,256,tok.bos_token_id,tok.eos_token_id,prefix_tokens=8).to(a.device)
    lm_before=component_fingerprint(lm);core_initial=component_fingerprint(core)
    parameters=list(core.parameters())+list(reader.parameters())+list(decoder.adapter.parameters())
    opt=torch.optim.AdamW(parameters,lr=plan['lr'],weight_decay=.01)
    rng=random.Random(2026092970+a.seed);start=time.monotonic();ledger={'stage':'JOINT-HUMAN-GROUNDING','seed':a.seed,'parent_frozen':False,'input_text_origin':'SQuAD TRAIN human-only','model_provenance_sha256':sha(a.model_provenance),'human_pairs_sha256':sha(Path(a.corpus)/'pairs.json'),'source_sha256':source_hash,'core_initial_sha256':core_initial,'stored_core_parameters':sum(p.numel() for p in core.parameters()),'active_core_parameters':core.counts()['active_parameter_accounting'],'LM_parameters':sum(p.numel() for p in lm.parameters()),'input_projection_parameters':sum(p.numel() for p in reader.parameters()),'output_adapter_parameters':decoder.adapter.parameter_count(),'updates':0,'LM_training_forwards':0,'human_target_token_visits':0,'input_token_visits':0,'trained_rows':len(train),'train_unique_ids':[],'wall_seconds':0,'sleep_updates':0,'claims':'UNTESTED: English semantics, notebook recall, real sleep, decoder-only leakage'}
    visited=set()
    for step in range(plan['updates']):
        if time.monotonic()-start>plan['wall_cap_seconds']:break
        batch=rng.sample(train,plan['batch']);visited.update(x['id'] for x in batch)
        ids,valid=input_tokens(tok,batch,a.device);targets=target_tokens(tok,batch,a.device)
        with torch.no_grad():embeddings=lm.get_input_embeddings()(ids)
        latent=reader(embeddings,valid);state=core.begin_latent(latent);survival=torch.ones(len(batch),device=a.device);expected=torch.zeros_like(survival)
        # Training unroll uses spatial owner's train API, not a duplicate final
        # state executor. Stop gets HUMAN loss gradients, no authored halt labels.
        for r in range(1,plan['rounds']+1):
            state=core.advance_latent(state);h,q=core.read_latent(state)
            prefix=decoder.adapter.project_training(h,torch.ones_like(h,dtype=torch.bool),valid,(1,h.shape[1]))
            per=human_loss(lm,prefix,targets,tok.bos_token_id,tok.eos_token_id,True)
            mass=survival if r==plan['rounds'] else survival*q.sigmoid()
            expected+=mass*(per+plan['ponder_penalty']*r)
            if r<plan['rounds']:survival=survival*(1-q.sigmoid())
            ledger['LM_training_forwards']+=1
        loss=expected.mean()+core.auxiliary()
        opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(parameters,1);opt.step()
        if any(p.grad is not None for p in lm.parameters()):raise RuntimeError('frozen LM received a parameter gradient')
        ledger['updates']=step+1;ledger['human_target_token_visits']+=int((targets!=-100).sum())*plan['rounds'];ledger['input_token_visits']+=int(valid.sum());ledger['wall_seconds']=round(time.monotonic()-start,2)
        if (step+1)%25==0:print(json.dumps({'seed':a.seed,'step':step+1,'human_CE_plus_ponder':float(loss.detach()),'seconds':ledger['wall_seconds']}),flush=True)
    if component_fingerprint(lm)!=lm_before:raise RuntimeError('LM changed')
    ledger['train_unique_ids']=sorted(visited);ledger['parent_frozen']=True;ledger['core_final_sha256']=component_fingerprint(core)
    if str(a.device).startswith('cuda'):ledger['peak_cuda_bytes']=torch.cuda.max_memory_allocated()
    bundle={'constructor':{'experts':core.experts_count,'active':core.active_count},'state_dict':{k:v.detach().cpu() for k,v in core.state_dict().items()},'metadata':{'stage':'human-grounded-unqualified','ledger':ledger}}
    torch.save(bundle,out/f'parent-s{a.seed}.pt');torch.save({'state_dict':reader.state_dict(),'lm_width':lm.get_input_embeddings().weight.shape[1],'human_manifest_sha256':ledger['human_pairs_sha256'],'training_origin':'verified-human-origin','stage':'joint-grounding-unqualified'},out/f'input-s{a.seed}.pt')
    torch.save({'state_width':256,'hidden':32,'prefix_tokens':8,'adapter_state':decoder.adapter.state_dict(),'human_manifest_sha256':ledger['human_pairs_sha256'],'human_registry_sha256':sha(Path(a.corpus)/'registry.json'),'source_state_contract':'sol-stop-FinalLatent-v1','lm_provenance_sha256':sha(a.model_provenance),'training_origin':'verified-human-origin-verbatim','parent_sha256':sha(out/f'parent-s{a.seed}.pt'),'reader_sha256':sha(out/f'input-s{a.seed}.pt'),'training_stage':'joint-grounding-unqualified'},out/f'bootstrap-English-s{a.seed}.pt')
    ledger['parent_checkpoint_sha256']=sha(out/f'parent-s{a.seed}.pt');(out/f'grounding-s{a.seed}.json').write_text(json.dumps(ledger,indent=2)+'\n')
    print(json.dumps(ledger),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--model-provenance',required=True);p.add_argument('--corpus',default=str(OWN/'corpus'));p.add_argument('--source');p.add_argument('--spatial-bundle');p.add_argument('--out',default=str(OWN/'run'));p.add_argument('--seed',type=int,choices=[0,1],required=True);p.add_argument('--device',default='cuda');a=p.parse_args()
    if not a.source and not a.spatial_bundle:p.error('qualified source or spatial bundle required')
    ground(a)
