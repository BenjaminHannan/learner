#!/usr/bin/env python3
"""Four-HUMAN-example capacity diagnostic, never a release model or general QA proof."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import argparse,hashlib,json,os,random,shutil,time
import torch
from sol_translator_answer_data_v11 import human_rows
from sol_translator_grounding_v6 import HumanInputProjection,question_notebook_tokens,target_tokens,human_loss
from sol_translator_english_ordered_v10 import load_ordered_english
from sol_spatial_poc_ordered_v2 import load_ordered_bundle
from sol_spatial_poc_ordered_train_api_v2 import fixed4_training
from scripts.sol_stop_ordered_api2 import ordered_attention_math
from sol_translator_decoder import FinalLatent
from sol_translator_runtime import component_fingerprint
from sol_translator_provenance import sha
OWN=ROOT/'artifacts/sol-translator-20260929'
PLAN=OWN/'TINY-V12-PLAN.json';SEAL=OWN/'TINY-V12-SEAL.json'
def write(path,obj):
    tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False)+'\n',encoding='utf-8');os.replace(tmp,path)
def diskbytes():return sum(p.stat().st_size for d in OWN.glob('tiny-v12-s[01]') for p in d.rglob('*') if p.is_file())
def save(path,obj,plan,estimate):
    if diskbytes()+estimate>plan['output_cap_bytes'] or shutil.disk_usage(path.parent).free<plan['retained_free_bytes']+estimate:raise RuntimeError('disk reserve/cap; preserve prior checkpoint')
    tmp=path.with_suffix('.pt.tmp');torch.save(obj,tmp)
    if diskbytes()>plan['output_cap_bytes']:raise RuntimeError('serialized cap exceeded; preserve temporary')
    os.replace(tmp,path)
def tensor_raw(x):
    x=x.detach().float().cpu();return {'shape':list(x.shape),'values':x.tolist(),'l2':float(x.norm()),'sha256':hashlib.sha256(x.numpy().tobytes()).hexdigest()}
def norm(gs):return float(torch.sqrt(sum(g.detach().float().square().sum() for g in gs if g is not None))) if any(g is not None for g in gs) else 0.0

def main(a):
    if not os.environ.get('JOB') or Path(os.environ.get('TREE','')).resolve()!=ROOT:raise RuntimeError('watcher only')
    plan=json.loads(PLAN.read_text());seal=json.loads(SEAL.read_text())
    for p,h in seal['files'].items():
        if sha(ROOT/p)!=h:raise ValueError('source pin '+p)
    out=OWN/f'tiny-v12-s{a.seed}'
    if (out/'LAUNCH.json').exists():raise ValueError('preserve earlier job; new identity required')
    out.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(out).free<plan['startup_free_bytes']:raise RuntimeError('declared startup disk reserve')
    binding=plan['tuples'][str(a.seed)]
    for k in ('parent','reader','adapter'):
        if sha(binding[k+'_path'])!=binding[k+'_sha256']:raise ValueError('closed checkpoint '+k)
    write(out/'LAUNCH.json',{'job':os.environ['JOB'],'seed':a.seed,'plan_sha256':sha(PLAN),'seal_sha256':sha(SEAL),'binding':binding,'optimizer_updates':0})
    torch.set_num_threads(2);torch.manual_seed(a.seed);device='cuda'
    dec,tok,_=load_ordered_english(binding['lm_path'],str(OWN/'CACHED-LFM-ORIGINAL-PROVENANCE.json'),binding['adapter_path'],device)
    lm=dec.lm;core,_=load_ordered_bundle(binding['parent_path'],device)
    rraw=torch.load(binding['reader_path'],weights_only=True,map_location=device);reader=HumanInputProjection(rraw['lm_width']).to(device);reader.load_state_dict(rraw['state_dict'])
    original,_=human_rows(OWN/'corpus');byid={r['id']:r for r in original};rows=[byid[i] for i in plan['TRAIN_ids']]
    tokens=[(*question_notebook_tokens(tok,r,device,max_context=512),target_tokens(tok,[r],device)) for r in rows]
    before_lm=component_fingerprint(lm);initial={k:component_fingerprint(m) for k,m in [('core',core),('reader',reader),('prefix',dec.adapter)]}
    groups=[('core',list(core.parameters())),('reader',list(reader.parameters())),('prefix',list(dec.adapter.parameters()))]
    initial_weights={k:[p.detach().cpu().clone() for p in ps] for k,ps in groups}
    params=[p for _,ps in groups for p in ps];parambytes=sum(p.numel()*p.element_size() for p in params)
    hooks={};handles=[dec.adapter.project[0].register_forward_pre_hook(lambda m,x:hooks.__setitem__('normalized_geometry',x[0])),dec.adapter.project[-1].register_forward_hook(lambda m,x,y:hooks.__setitem__('token_projected',y))]
    def graph(i,no_book=False):
        ids,valid,mids,mvalid,tgt=tokens[i]
        with torch.no_grad():qe=lm.get_input_embeddings()(ids);be=lm.get_input_embeddings()(mids)
        query=reader(qe,valid);book=reader(be,mvalid).flatten(1,2)
        if no_book:book=book[:,:0];mvalid=mvalid[:,:0]
        with ordered_attention_math():h,q,aux=fixed4_training(core,query,book,query_mask=valid,notebook_mask=mvalid)
        prefix=dec.adapter.project_training(h,torch.ones_like(h,dtype=torch.bool),valid,(1,h.shape[1]))
        return prefix,aux,dict(final_query=h,normalized_geometry=hooks['normalized_geometry'],token_projected=hooks['token_projected'],pooled_prefix=prefix)
    @torch.no_grad()
    def generate(prefix,max_tokens=32):
        bos=torch.full((1,1),dec.bos_id,device=device,dtype=torch.long);x=torch.cat((prefix,lm.get_input_embeddings()(bos)),1)
        ids=lm.generate(inputs_embeds=x,attention_mask=torch.ones(x.shape[:2],device=device,dtype=torch.long),max_new_tokens=max_tokens,do_sample=False,use_cache=True,bos_token_id=dec.bos_id,eos_token_id=dec.eos_id,pad_token_id=dec.eos_id)[0].tolist()
        return ids[:ids.index(dec.eos_id)] if dec.eos_id in ids else ids
    @torch.no_grad()
    def diagnostic(stage,arm,table=None):
        prefixes=[];traces=[]
        for i in range(4):
            if table is None:p,_,trace=graph(i)
            else:p=table[i:i+1];trace={'direct_prefix_table_NOT_release':p}
            prefixes.append(p.detach());traces.append({k:tensor_raw(v) for k,v in trace.items()})
        for i,row in enumerate(rows):
            p=prefixes[i];labels=tokens[i][-1];per,pred=human_loss(lm,p,labels,dec.bos_id,dec.eos_id,True,True)
            controls={'actual':p,'swapped_same_context':prefixes[i^1],'zero_prefix':torch.zeros_like(p)}
            if table is None:controls['no_notebook']=graph(i,True)[0]
            outputs={k:generate(v) for k,v in controls.items()}
            rec={'stage':stage,'arm':arm,'id':row['id'],'human_question':row['question'],'human_reference_answer_NOT_generated':row['answer_text'],
                'labels':labels.cpu().tolist(),'label_mask':(labels!=-100).cpu().tolist(),'teacherforced_argmax':pred.cpu().tolist(),'teacherforced_CE':per.cpu().tolist(),
                'MODEL_generated_ids':outputs,'MODEL_generated_text':{k:tok.decode(v,skip_special_tokens=True) for k,v in outputs.items()},'outputs_never_training_labels':True,'traces':traces[i],
                'binding':binding,'plan_sha256':sha(PLAN),'seed':a.seed,'split':'TRAIN-memorization-diagnostic-NOT-generalization'}
            with (out/'diagnostic-raw.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(rec,ensure_ascii=False)+'\n')
    core.train().requires_grad_(True);reader.train().requires_grad_(True);dec.adapter.train().requires_grad_(True)
    with torch.no_grad():initial_prefix=torch.cat([graph(i)[0].detach() for i in range(4)]).clone()
    # Helper is owned by Peirce; injected import name is sealed by packager.
    from sol_spatial_decoder_parity_adapter_v12 import probe_decoder_parity
    for i in range(4):
        with torch.no_grad():
            pp,aa,trace=graph(i);h=trace['final_query'];valid=tokens[i][1];packet=FinalLatent(h.detach(),torch.ones_like(h,dtype=torch.bool),valid,(1,h.shape[1]))
        parity=probe_decoder_parity(dec,packet,tokens[i][-1],max_new_tokens=16)
        write(out/f'parity-initial-{i}.json',{'id':rows[i]['id'],'seed':a.seed,'binding':binding,'result':parity,'training_origin':'verbatim HUMAN TRAIN annotations','generated_text_used_for_training':False})
    # Actual one-row CE/aux backward guard; zero optimizer, same train graph.
    torch.cuda.reset_peak_memory_stats();p0,aux0,_=graph(0);ce0,_=human_loss(lm,p0,tokens[0][-1],dec.bos_id,dec.eos_id,True,True);(ce0.mean()+aux0).backward()
    allocated=torch.cuda.max_memory_allocated();reserved=torch.cuda.max_memory_reserved();limit=min(16*1024**3,torch.cuda.get_device_properties(0).total_memory)
    guard=reserved+4*parambytes+512*1024**2<=limit
    write(out/'MEMORY-PREFLIGHT.json',{'optimizer_updates':0,'human_TRAIN_probe_id':rows[0]['id'],'allocated':allocated,'reserved':reserved,'optimizer_margin_inferred':4*parambytes,'safety_bytes':512*1024**2,'cap':limit,'guard_passed':guard,'all_LM_FP32_frozen':all(p.dtype==torch.float32 and not p.requires_grad for p in lm.parameters()),'binding':binding})
    if not guard:raise RuntimeError('actual FP32 graph memory cap failed')
    for p in params:p.grad=None
    del p0,aux0,ce0;hooks.clear()
    diagnostic('initial','connected')
    torch.cuda.reset_peak_memory_stats();start=time.monotonic();summary=[]
    schedule=json.loads((OWN/f'TINY-V12-SCHEDULE-s{a.seed}.json').read_text())
    for arm in ('connected','direct_prefix_table_capacity_ONLY'):
        table=torch.nn.Parameter(initial_prefix.clone()) if arm!='connected' else None
        ps=params if table is None else [table];opt=torch.optim.AdamW(ps,lr=plan['connected_lr'] if table is None else plan['table_lr'],weight_decay=0)
        armstart=time.monotonic();updates=0
        for step,i in enumerate(schedule):
            if time.monotonic()-start>plan['fit_wall_seconds']:break
            opt.zero_grad(set_to_none=True);hooks.clear()
            if table is None:prefix,aux,acts=graph(i)
            else:prefix=table[i:i+1];aux=torch.zeros((),device=device);acts={'pooled_prefix':prefix}
            labels=tokens[i][-1];per,pred=human_loss(lm,prefix,labels,dec.bos_id,dec.eos_id,True,True);ce=per.mean()
            capture=step==0 or (step+1)%25==0 or step+1==len(schedule);gradraw={}
            if capture:
                actitems=list(acts.items());gs=torch.autograd.grad(ce,ps+[v for k,v in actitems],retain_graph=True,allow_unused=True)
                if table is None:
                    at=0
                    for key,pp in groups:sub=gs[at:at+len(pp)];gradraw[key]={'CE_only_L2':norm(sub),'tensors_with_grad':sum(g is not None for g in sub),'parameters':len(pp)};at+=len(pp)
                else:gradraw['table']={'CE_only_L2':norm(gs[:1])}
                gradraw['activations']={k:{'CE_only_L2':norm([g]),'present':g is not None} for (k,v),g in zip(actitems,gs[len(ps):])}
            loss=ce+aux
            if not bool(torch.isfinite(loss)):raise RuntimeError('nonfinite loss')
            loss.backward();totalnorm=torch.nn.utils.clip_grad_norm_(ps,1,error_if_nonfinite=True);opt.step();updates=step+1
            if any(p.grad is not None for p in lm.parameters()):raise RuntimeError('frozenLM gradient')
            rec={'arm':arm,'update':updates,'id':rows[i]['id'],'labels':labels.cpu().tolist(),'label_mask':(labels!=-100).cpu().tolist(),'teacherforced_argmax':pred.cpu().tolist(),
                'human_CE':float(ce.detach()),'auxiliary_separate':float(aux.detach()),'total_preclip_norm':float(totalnorm),'CE_only_gradients':gradraw,'parameter_delta_L2_from_initial':{k:float(torch.sqrt(sum((p.detach().cpu()-v).square().sum() for p,v in zip(pp,initial_weights[k])))) for k,pp in groups} if capture and table is None else None,'plan_sha256':sha(PLAN),'binding':binding,'seed':a.seed}
            with (out/'TRAIN-raw.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(rec)+'\n')
            if capture:
                ck={'arm':arm,'seed':a.seed,'update':updates,'optimizer':opt.state_dict(),'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all(),'schedule_sha256':sha(OWN/f'TINY-V12-SCHEDULE-s{a.seed}.json'),'plan_sha256':sha(PLAN),'binding':binding}
                if table is None:ck.update(core=core.state_dict(),reader=reader.state_dict(),prefix=dec.adapter.state_dict())
                else:ck['table']=table.detach()
                save(out/f'{arm}-resume.pt',ck,plan,3*(parambytes if table is None else table.numel()*4)+8*1024**2)
                print(json.dumps({'status':'DURABLE-TINY-TRAIN','arm':arm,'seed':a.seed,'updates':updates,'seconds':time.monotonic()-armstart}),flush=True)
            if updates in plan['trace_updates']:diagnostic('update'+str(updates),arm,table)
        summary.append({'arm':arm,'updates':updates,'requested':len(schedule),'seconds':time.monotonic()-armstart,'complete':updates==len(schedule)})
        del opt
    for h in handles:h.remove()
    if component_fingerprint(lm)!=before_lm:raise RuntimeError('frozenLM changed')
    write(out/'SUMMARY.json',{'arms':summary,'initial_fingerprints':initial,'final_fingerprints':{k:component_fingerprint(m) for k,m in [('core',core),('reader',reader),('prefix',dec.adapter)]},'seed':a.seed,'binding':binding,'LM_unchanged':True,'peak_allocated':torch.cuda.max_memory_allocated(),'peak_reserved':torch.cuda.max_memory_reserved(),'wall_seconds':time.monotonic()-start,'DEV0':True,'not_release_architecture':True,'semantic_promotion':False})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,choices=(0,1),required=True);main(p.parse_args())
