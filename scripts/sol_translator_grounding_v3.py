#!/usr/bin/env python3
"""V3 question-only/context-notebook HUMAN grounding; queue-only optimization, shared core training API.
Not a frozen-parent decoder proof. Does not implement inference execution.
"""
from __future__ import annotations
import argparse,copy,json,os,random,time,signal
from pathlib import Path
import torch
from torch import nn
from sol_translator_english_v3 import FrozenEnglishDecoder,load_local_lm
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


def question_notebook_tokens(tokenizer,row,device,max_question=48,max_context=256):
    q=tokenizer.encode(row['question'],add_special_tokens=False)[:max_question]+[tokenizer.eos_token_id]
    c=tokenizer.encode(row['context'],add_special_tokens=False)[:max_context]
    ids=torch.tensor([q],device=device,dtype=torch.long)
    mids=torch.tensor([c],device=device,dtype=torch.long)
    return ids,torch.ones_like(ids,dtype=torch.bool),mids,torch.ones_like(mids,dtype=torch.bool)


def target_tokens(tokenizer,rows,device,max_tokens=64):
    seq=[]
    for row in rows:
        ids=tokenizer.encode(row['target_text'],add_special_tokens=False)+[tokenizer.eos_token_id]
        if len(ids)>max_tokens:raise ValueError('human target exceeds sealed token budget; no truncated grammatical targets')
        seq.append(ids)
    out=torch.full((len(seq),max(map(len,seq))),-100,device=device,dtype=torch.long)
    for i,row in enumerate(seq):out[i,:len(row)]=torch.tensor(row,device=device)
    return out


def human_loss(lm,prefix,target,bos,eos,return_per_example=False,return_predictions=False):
    emb=lm.get_input_embeddings();start=torch.full((len(target),1),bos,device=target.device,dtype=torch.long)
    shifted=torch.cat((start,target[:,:-1].masked_fill(target[:,:-1]==-100,eos)),1)
    x=torch.cat((prefix.to(emb.weight.dtype),emb(shifted)),1)
    attention=torch.cat((torch.ones(prefix.shape[:2],device=x.device,dtype=torch.long),(target!=-100).long()),1)
    logits=lm(inputs_embeds=x,attention_mask=attention,use_cache=False).logits[:,prefix.shape[1]:].float()
    loss=torch.nn.functional.cross_entropy(logits.transpose(1,2),target,ignore_index=-100,reduction='none')
    per=loss.sum(1)/(target!=-100).sum(1)
    result=per if return_per_example else per.mean()
    return (result,logits.detach().argmax(-1)) if return_predictions else result


def guard_queue():
    if not os.environ.get('JOB') or not os.environ.get('TREE'):
        raise SystemExit('QUEUE-ONLY: optimization requires watcher JOB and TREE context')


def atomic_save(payload,path):
    tmp=path.with_suffix('.tmp')
    torch.save(payload,tmp);os.replace(tmp,path)


def export_weights(core,reader,decoder,lm,a,ledger,out):
    bundle={'constructor':{'experts':core.experts_count,'active':core.active_count},'state_dict':{k:v.detach().cpu() for k,v in core.state_dict().items()},'metadata':{'stage':'human-grounded-unqualified','human_manifest_sha256':ledger['human_pairs_sha256'],'reader_version':'human-notebook-v2','updates':ledger['updates'],'batch':ledger['batch'],'rounds':ledger['rounds'],'seed':a.seed,'ledger':dict(ledger)}}
    atomic_save(bundle,out/f'parent-s{a.seed}.pt')
    atomic_save({'state_dict':reader.state_dict(),'lm_width':lm.get_input_embeddings().weight.shape[1],'human_manifest_sha256':ledger['human_pairs_sha256'],'training_origin':'verified-human-origin','stage':'joint-grounding-unqualified','input_scope':'question query only; context notebook','reader_version':'human-notebook-v2'},out/f'input-s{a.seed}.pt')
    ledger['parent_checkpoint_sha256']=sha(out/f'parent-s{a.seed}.pt')
    atomic_save({'state_width':256,'hidden':32,'prefix_tokens':8,'adapter_state':decoder.adapter.state_dict(),'human_manifest_sha256':ledger['human_pairs_sha256'],'human_registry_sha256':sha(Path(a.corpus)/'registry.json'),'source_state_contract':'sol-stop-FinalLatent-v1','lm_provenance_sha256':sha(a.model_provenance),'training_origin':'verified-human-origin-verbatim','parent_sha256':ledger['parent_checkpoint_sha256'],'reader_sha256':sha(out/f'input-s{a.seed}.pt'),'training_stage':'joint-grounding-unqualified'},out/f'bootstrap-English-s{a.seed}.pt')
    (out/f'grounding-s{a.seed}.json').write_text(json.dumps(ledger,indent=2)+'\n')


def ground(a):
    guard_queue();out=Path(a.out).resolve()
    if not out.is_relative_to(OWN):raise ValueError('owned output directory required')
    out.mkdir(parents=True,exist_ok=True);plan=json.loads((OWN/'DEPLOYMENT-V3-PLAN.json').read_text())
    torch.set_num_threads(2);torch.manual_seed(a.seed)
    rows,reg=human_rows(a.corpus);train=[r for r in rows if r['split']=='train']
    lm,tok,provenance=load_local_lm(a.model,a.model_provenance,a.device)
    # Preflight targets BEFORE any optimizer: no target truncation or silent row removal.
    for row in train:target_tokens(tok,[row],a.device)
    truncation={'question_cap':48,'context_cap':256,'train_n':len(train),'question_truncated_n':sum(len(tok.encode(r['question'],add_special_tokens=False))>48 for r in train),'context_truncated_n':sum(len(tok.encode(r['context'],add_special_tokens=False))>256 for r in train),'selection':'fixed prefix; no label-dependent crop/drop; no DEV statistics'}
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
    rng=random.Random(2026092970+a.seed);start=time.monotonic();ledger={'stage':'JOINT-HUMAN-GROUNDING','seed':a.seed,'parent_frozen':False,'input_text_origin':'SQuAD TRAIN human-only','model_provenance_sha256':sha(a.model_provenance),'human_pairs_sha256':sha(Path(a.corpus)/'pairs.json'),'source_sha256':source_hash,'core_initial_sha256':core_initial,'stored_core_parameters':sum(p.numel() for p in core.parameters()),'active_core_parameters':core.counts()['active_parameter_accounting'],'LM_parameters':sum(p.numel() for p in lm.parameters()),'input_projection_parameters':sum(p.numel() for p in reader.parameters()),'output_adapter_parameters':decoder.adapter.parameter_count(),'updates':0,'LM_training_forwards':0,'human_target_token_visits':0,'input_token_visits':0,'trained_rows':len(train),'train_unique_ids':[],'wall_seconds':0,'sleep_updates':0,'input_scope':'question query only; context notebook; final query only','reader_version':'human-notebook-v2','batch':plan['batch'],'rounds':plan['rounds'],'precision':{'LM_embeddings':str(lm.get_input_embeddings().weight.dtype),'LM_head':str(lm.get_output_embeddings().weight.dtype),'reader_and_core':'FP32'},'job':os.environ['JOB'],'plan_sha256':sha(OWN/'DEPLOYMENT-V3-PLAN.json'),'deployment_seal_sha256':sha(OWN/'DEPLOYMENT-V3-SEAL.json'),'stop_code_sha256':sha(ROOT/'scripts/sol_stop_adapter.py'),'driver_sha256':sha(__file__),'fixed_input_truncation':truncation,'claims':'UNTESTED: English semantics, notebook recall, real sleep, decoder-only leakage'}
    (out/f'grounding-s{a.seed}-STARTED.json').write_text(json.dumps({'seed':a.seed,'scope':'joint-human-grounding-v3','source_sha256':source_hash,'human_pairs_sha256':ledger['human_pairs_sha256'],'optimizer_started':False})+'\n')
    visited=set();first_step=0;interrupted=[False];resume_hash=None;launch_id=time.strftime('%Y%m%dT%H%M%S',time.gmtime())+'-'+os.environ['JOB']
    def request_stop(signum,frame):interrupted[0]=True
    signal.signal(signal.SIGTERM,request_stop)
    signal.signal(signal.SIGINT,request_stop)
    if a.resume:
        ck=torch.load(a.resume,map_location=a.device,weights_only=True)
        for field,value in {'human_pairs_sha256':ledger['human_pairs_sha256'],'source_sha256':source_hash,'plan_sha256':sha(OWN/'DEPLOYMENT-V3-PLAN.json'),'driver_sha256':sha(__file__),'seed':a.seed}.items():
            if ck['binding'][field]!=value:raise ValueError('resume binding mismatch '+field)
        core.load_state_dict(ck['core']);reader.load_state_dict(ck['reader']);decoder.adapter.load_state_dict(ck['adapter']);opt.load_state_dict(ck['optimizer'])
        rng.setstate(ck['sample_rng']);torch.set_rng_state(ck['torch_rng'].cpu())
        if str(a.device).startswith('cuda'):torch.cuda.set_rng_state_all([v.cpu() for v in ck['cuda_rng']])
        ledger=ck['ledger'];first_step=ledger['updates'];visited=set(ledger['train_unique_ids'])
        resume_hash=sha(a.resume);ledger['resume_from_sha256']=resume_hash
        ledger['job']=os.environ['JOB']
    elif (out/f'resume-s{a.seed}.pt').exists():raise ValueError('existing TRAIN checkpoint requires explicit --resume; never silently restart')
    ledger['launch_id']=launch_id;ledger['resume_start_update']=first_step
    print(json.dumps({'status':'OPTIMIZER-READY','seed':a.seed,'train_rows':len(train),'device':a.device,'reader_version':'human-notebook-v2','job':os.environ['JOB'],'launch_id':launch_id,'resume_start_update':first_step,'resume_checkpoint_sha256':resume_hash,'source_parent_sha256':source_hash,'initial_core_sha256':core_initial,'plan_sha256':ledger['plan_sha256'],'deployment_seal_sha256':ledger['deployment_seal_sha256'],'stop_code_sha256':ledger['stop_code_sha256']}),flush=True)
    with (out/f'train-raw-s{a.seed}.jsonl').open('a') as f:
        f.write(json.dumps({'kind':'LAUNCH-WATERMARK','job':os.environ['JOB'],'launch_id':launch_id,'resume_start_update':first_step,'resume_checkpoint_sha256':resume_hash,'durable_raw_watermark':ledger.get('raw_watermark_update',0),'orphan_policy':'prior records after watermark are retained as noncommitted; never silently truncate/double-count; identities require launch_id+update+id'})+'\n')
    def durable():
        ledger['train_unique_ids']=sorted(visited)
        ledger['raw_watermark_update']=ledger['updates']
        ledger['wall_seconds_current_launch']=round(time.monotonic()-start,2)
        binding={'human_pairs_sha256':ledger['human_pairs_sha256'],'source_sha256':source_hash,'plan_sha256':sha(OWN/'DEPLOYMENT-V3-PLAN.json'),'driver_sha256':sha(__file__),'seed':a.seed}
        ck={'core':core.state_dict(),'reader':reader.state_dict(),'adapter':decoder.adapter.state_dict(),'optimizer':opt.state_dict(),'sample_rng':rng.getstate(),'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all() if str(a.device).startswith('cuda') else [],'ledger':dict(ledger),'binding':binding}
        atomic_save(ck,out/f'resume-s{a.seed}.pt')
        export_weights(core,reader,decoder,lm,a,ledger,out)
        print(json.dumps({'status':'DURABLE-TRAIN-WEIGHTS','seed':a.seed,'updates':ledger['updates'],'seconds_current_launch':ledger['wall_seconds_current_launch'],'resume_sha256':sha(out/f'resume-s{a.seed}.pt')}),flush=True)
    for step in range(first_step,plan['updates']):
        if interrupted[0] or time.monotonic()-start>plan['wall_cap_seconds']:break
        batch=rng.sample(train,plan['batch']);visited.update(x['id'] for x in batch)
        losses=[];target_visits=0;input_visits=0;raw=[]
        # Per-row attention avoids making padded notebook vectors facts.
        for row in batch:
            ids,valid,mids,mvalid=question_notebook_tokens(tok,row,a.device)
            targets=target_tokens(tok,[row],a.device)
            with torch.no_grad():
                embeddings=lm.get_input_embeddings()(ids)
                memo_embeddings=lm.get_input_embeddings()(mids)
            latent=reader(embeddings,valid)
            notebook=reader(memo_embeddings,mvalid).flatten(1,2)
            state=core.begin_latent(latent,notebook)
            survival=torch.ones(1,device=a.device);expected=torch.zeros_like(survival);round_raw=[]
            for r in range(1,plan['rounds']+1):
                state=core.advance_latent(state);h,q=core.read_latent(state)
                if h.shape[1]!=ids.shape[1]:raise RuntimeError('notebook leaked into exported query')
                prefix=decoder.adapter.project_training(h,torch.ones_like(h,dtype=torch.bool),valid,(1,h.shape[1]))
                per,predictions=human_loss(lm,prefix,targets,tok.bos_token_id,tok.eos_token_id,True,True)
                mass=survival if r==plan['rounds'] else survival*q.sigmoid()
                round_raw.append({'round':r,'predictions':predictions.cpu().tolist(),'stop_logits':q.detach().cpu().tolist(),'survival_before':survival.detach().cpu().tolist(),'selection_mass':mass.detach().cpu().tolist(),'human_CE_per_example':per.detach().cpu().tolist()})
                expected=expected+mass*(per+plan['ponder_penalty']*r)
                if r<plan['rounds']:survival=survival*(1-q.sigmoid())
                ledger['LM_training_forwards']+=1
            losses.append(expected.mean()+core.auxiliary())
            raw.append({'id':row['id'],'split':'train','seed':a.seed,'update':step+1,'input_ids':ids.detach().cpu().tolist(),'input_mask':valid.cpu().tolist(),'notebook_ids':mids.cpu().tolist(),'notebook_mask':mvalid.cpu().tolist(),'labels':targets.cpu().tolist(),'label_mask':(targets!=-100).cpu().tolist(),'predictions':predictions.cpu().tolist(),'prediction_kind':'teacher-forced training diagnostics ONLY; never new training text','source_sha256':row['source_sha256'],'human_pairs_sha256':ledger['human_pairs_sha256'],'driver_sha256':sha(__file__),'parent_previous_checkpoint_sha256':ledger.get('parent_checkpoint_sha256'),'reader_version':'human-notebook-v2','rounds':round_raw,'job':os.environ['JOB'],'launch_id':launch_id,'resume_start_update':first_step,'resume_checkpoint_sha256':resume_hash,'source_parent_sha256':source_hash,'initial_core_sha256':core_initial,'plan_sha256':ledger['plan_sha256'],'deployment_seal_sha256':ledger['deployment_seal_sha256'],'stop_code_sha256':ledger['stop_code_sha256']})
            target_visits+=int((targets!=-100).sum())*plan['rounds']
            input_visits+=int(valid.sum()+mvalid.sum())
        loss=torch.stack(losses).mean()
        opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(parameters,1);opt.step()
        if any(p.grad is not None for p in lm.parameters()):raise RuntimeError('frozen LM received a parameter gradient')
        ledger['updates']=step+1;ledger['human_target_token_visits']+=target_visits;ledger['input_token_visits']+=input_visits;ledger['wall_seconds']=round(time.monotonic()-start,2)
        with (out/f'train-raw-s{a.seed}.jsonl').open('a') as f:
            for record in raw:f.write(json.dumps(record)+'\n')
        if step==first_step or (step+1)%25==0:durable()
        if (step+1)%25==0:print(json.dumps({'seed':a.seed,'step':step+1,'human_CE_plus_ponder':float(loss.detach()),'seconds':ledger['wall_seconds']}),flush=True)
    ledger['interrupted']=interrupted[0];ledger['requested_updates_completed']=ledger['updates']==plan['updates']
    durable()
    if component_fingerprint(lm)!=lm_before:raise RuntimeError('LM changed')
    ledger['train_unique_ids']=sorted(visited);ledger['parent_frozen']=True;ledger['core_final_sha256']=component_fingerprint(core)
    if str(a.device).startswith('cuda'):ledger['peak_cuda_bytes']=torch.cuda.max_memory_allocated()
    export_weights(core,reader,decoder,lm,a,ledger,out)
    print(json.dumps(ledger),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--model-provenance',required=True);p.add_argument('--corpus',default=str(OWN/'corpus'));p.add_argument('--source');p.add_argument('--resume');p.add_argument('--spatial-bundle');p.add_argument('--out',default=str(OWN/'run'));p.add_argument('--seed',type=int,choices=[0,1],required=True);p.add_argument('--device',default='cuda');a=p.parse_args()
    if not a.source and not a.spatial_bundle:p.error('qualified source or spatial bundle required')
    ground(a)
