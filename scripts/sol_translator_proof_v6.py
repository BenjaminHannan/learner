#!/usr/bin/env python3
"""Bounded, resumable frozen-core HUMAN decoder arm. DEV exactly once.
Core execution only shared stop adapter; output translator only FinalLatent.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse,copy,json,os,random,time,signal
from pathlib import Path
import torch
from scripts.sol_stop_api4 import make_fixed4_executor
from sol_translator_decoder import FinalLatent,validate_final
from sol_translator_english_v6 import FrozenEnglishDecoder,load_local_lm
from sol_translator_grounding_v6 import HumanInputProjection,human_rows,question_notebook_tokens,target_tokens,human_loss,atomic_save,guard_queue
from sol_translator_runtime import component_fingerprint
from sol_translator_language_proof import choose_final
from sol_translator_provenance import sha
from sol_spatial_attention_core import load_bundle
ROOT=Path(__file__).resolve().parents[1];OWN=ROOT/'artifacts/sol-translator-20260929'
ARMS=('loop','no_state','embedding','untrained','shuffled_state','plain')


def final_digest(final):
    import hashlib
    h=hashlib.sha256()
    for name in ('latent','latent_mask','answer_mask'):
        t=getattr(final,name).detach().cpu().contiguous()
        h.update(t.view(torch.uint8).numpy().tobytes())
    h.update(str(final.token_shape).encode());return h.hexdigest()


def read_source(a,lm):
    raw=torch.load(a.reader,map_location='cpu',weights_only=True)
    if raw.get('reader_version')!='human-notebook-v2' or raw.get('training_origin')!='verified-human-origin':raise ValueError('human notebook reader required')
    reader=HumanInputProjection(raw['lm_width']).to(a.device);reader.load_state_dict(raw['state_dict']);reader.eval().requires_grad_(False)
    if raw['human_manifest_sha256']!=sha(Path(a.corpus)/'pairs.json'):raise ValueError('reader/corpus mismatch')
    if a.arm=='plain':
        from sol_spatial_poc_plain import load_plain_bundle
        core,meta=load_plain_bundle(a.parent,a.device)
    else:
        core,meta=load_bundle(a.parent,a.device)
    if meta.get('reader_version')!='human-notebook-v2' or meta.get('human_manifest_sha256')!=raw['human_manifest_sha256']:raise ValueError('parent human-version binding mismatch')
    core.eval().requires_grad_(False)
    execution=core
    if a.arm=='untrained':
        execution=copy.deepcopy(core);torch.manual_seed(7300+a.seed)
        for module in execution.modules():
            if hasattr(module,'reset_parameters'):module.reset_parameters()
        execution.eval().requires_grad_(False)
    return reader,core,make_fixed4_executor(execution)


@torch.no_grad()
def state_for(row,a,lm,tok,reader,executor):
    ids,valid,mids,mvalid=question_notebook_tokens(tok,row,a.device)
    query=reader(lm.get_input_embeddings()(ids),valid).detach().flatten(1,2)
    memo=reader(lm.get_input_embeddings()(mids),mvalid).detach().flatten(1,2)
    account={'id':row['id'],'input_ids':ids.cpu().tolist(),'input_mask':valid.cpu().tolist(),'notebook_ids':mids.cpu().tolist(),'notebook_mask':mvalid.cpu().tolist(),'source':a.arm}
    if a.arm=='embedding':
        # Stronger decoder-alone control sees ALL input lexical vectors;
        # larger geometry explicitly disclosed, no reasoner transition.
        h=torch.cat((query,memo),1);mask=torch.ones(h.shape[:2],device=h.device,dtype=torch.bool)
        f=FinalLatent(h,torch.ones_like(h,dtype=torch.bool),mask,(1,h.shape[1]))
        account['geometry_limit']='all question/context cells vs final-query only in real arms'
    elif a.arm=='no_state':
        f=FinalLatent(torch.zeros_like(query),torch.ones_like(query,dtype=torch.bool),valid,(1,query.shape[1]))
    else:
        result=executor.execute_embeddings(query,valid,(1,query.shape[1]),notebook_latents=memo,notebook_mask=mvalid,policy='fixed',compact=True,cap=4)
        f=result.final
        account.update({'selected_row_rounds':result.audit.selected_row_rounds,'executed_row_rounds':result.audit.executed_row_rounds,'work':result.audit.work,'core_sha256':result.audit.core_sha256})
        if f.latent.shape[1]!=query.shape[1]:raise ValueError('notebook must not be exported')
    validate_final(f);account['final_sha256']=final_digest(f);return f,account


def proof(a):
    guard_queue();torch.set_num_threads(2)
    out=Path(a.out).resolve()
    if not out.is_relative_to(OWN):raise ValueError('owned outputs only')
    out.mkdir(parents=True,exist_ok=True)
    plan=json.loads(Path(a.plan).read_text())
    if plan['training_steps']!=500 or plan['batch']!=2 or plan['fixed_core_rounds']!=4:raise ValueError('changed proof budget requires NEW plan')
    binding={'parent_sha256':sha(a.parent),'reader_sha256':sha(a.reader),'human_pairs_sha256':sha(Path(a.corpus)/'pairs.json'),'human_registry_sha256':sha(Path(a.corpus)/'registry.json'),'LM_provenance_sha256':sha(a.model_provenance),'driver_sha256':sha(__file__),'plan_sha256':sha(a.plan),'stop_code_sha256':sha(ROOT/'scripts/sol_stop_adapter.py'),'stop_factory_sha256':sha(ROOT/'scripts/sol_stop_api4.py'),'stop_executor_sha256':sha(ROOT/'scripts/sol_stop_grounded_adapter_v4.py'),'source_seed':a.seed,'decoder_seed':a.decoder_seed,'arm':a.arm}
    # Binding seal supplied by integrator AFTER actual durable parent exists.
    expected=json.loads(Path(a.binding).read_text())
    for key in ('parent_sha256','reader_sha256','human_pairs_sha256','human_registry_sha256','LM_provenance_sha256','driver_sha256','plan_sha256','stop_code_sha256','stop_factory_sha256','stop_executor_sha256'):
        if expected[key]!=binding[key]:raise ValueError('actual checkpoint binding mismatch '+key)
    if expected.get('fixed_rounds')!=4 or expected.get('stage')!='frozen-parent-decoder-proof':raise ValueError('wrong experiment phase')
    burn=out/'DEV-CONSUMED.json'
    if burn.exists():raise RuntimeError('DEV consumed: NEVER rerun/rescore this seed/arm')
    rows,reg=human_rows(a.corpus);train=[r for r in rows if r['split']=='train'];dev=[r for r in rows if r['split']=='dev']
    lm,tok,_=load_local_lm(a.model,a.model_provenance,a.device)
    reader,core,executor=read_source(a,lm)
    frozen={'LM':lm,'reader':reader,'parent':core}
    frozen_before={name:component_fingerprint(m) for name,m in frozen.items()}
    torch.manual_seed(a.decoder_seed)
    decoder=FrozenEnglishDecoder(lm,256,tok.bos_token_id,tok.eos_token_id,prefix_tokens=8).to(a.device)
    opt=torch.optim.AdamW(decoder.adapter.parameters(),lr=plan['lr'])
    rng=random.Random(9900+a.decoder_seed);donors=random.Random(9901+a.decoder_seed)
    interrupted=[False]
    signal.signal(signal.SIGTERM,lambda signum,frame:interrupted.__setitem__(0,True))
    signal.signal(signal.SIGINT,lambda signum,frame:interrupted.__setitem__(0,True))
    start=time.monotonic();first=0;ledger={'updates':0,'LM_training_forwards':0,'target_token_visits':0,'binding':binding,'parent_frozen':True,'fixed_core_rounds':4,'noise':'INSUFFICIENT: no empirical decoder-repeat variance','optimizer_scope':'prefix adapter ONLY'}
    resume=out/'TRAIN-resume.pt'
    if a.resume:
        ck=torch.load(resume,map_location=a.device,weights_only=True)
        if ck['binding']!=binding:raise ValueError('resume bound to different frozen source')
        decoder.adapter.load_state_dict(ck['adapter']);opt.load_state_dict(ck['optimizer']);rng.setstate(ck['rng']);donors.setstate(ck['donor_rng']);torch.set_rng_state(ck['torch_rng'].cpu())
        if str(a.device).startswith('cuda'):torch.cuda.set_rng_state_all([v.cpu() for v in ck['cuda_rng']])
        ledger=ck['ledger'];first=ledger['updates']
    elif resume.exists():raise RuntimeError('explicit TRAIN resume required; no silent restart')
    # Immutable state cache contains ONLY FinalLatent; text terminates here.
    finals=[];accounts=[]
    for row in train:
        if interrupted[0] or time.monotonic()-start>plan['cache_wall_seconds']:raise RuntimeError('TRAIN cache TIME-CAP, no DEV scored')
        f,acc=state_for(row,a,lm,tok,reader,executor);finals.append(f.to('cpu'));accounts.append(acc)
    (out/'TRAIN-state-identities.json').write_text(json.dumps(accounts)+'\n')
    def pick(i,donor=None):
        if a.arm!='shuffled_state':return finals[i].to(a.device)
        cache=[{'loop':f} for f in finals]
        return choose_final(cache,i,'shuffled_state',donor).to(a.device)
    launch=time.strftime('%Y%m%dT%H%M%S',time.gmtime())+'-'+os.environ['JOB']
    with (out/'TRAIN-raw.jsonl').open('a') as f:f.write(json.dumps({'kind':'LAUNCH-WATERMARK','job':os.environ['JOB'],'launch_id':launch,'resume_start_update':first,'resume_sha256':sha(resume) if a.resume else None,'orphan_policy':'retain records beyond old watermark; do not double-count','binding':binding})+'\n')
    def durable():
        ledger['raw_watermark_update']=ledger['updates'];ledger['wall_seconds_current_launch']=time.monotonic()-start
        atomic_save({'adapter':decoder.adapter.state_dict(),'optimizer':opt.state_dict(),'rng':rng.getstate(),'donor_rng':donors.getstate(),'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all() if str(a.device).startswith('cuda') else [],'ledger':ledger,'binding':binding},resume)
        raw={'state_width':256,'hidden':32,'prefix_tokens':8,'adapter_state':decoder.adapter.state_dict(),'human_manifest_sha256':binding['human_pairs_sha256'],'human_registry_sha256':binding['human_registry_sha256'],'source_state_contract':'sol-stop-FinalLatent-v1','lm_provenance_sha256':binding['LM_provenance_sha256'],'training_origin':'verified-human-origin-verbatim','parent_sha256':binding['parent_sha256'],'reader_sha256':binding['reader_sha256'],'training_stage':'frozen-parent-fixed4-decoder-proof-unqualified'}
        atomic_save(raw,out/'English.pt');(out/'TRAIN-ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
        print(json.dumps({'status':'FROZEN-DECODER-DURABLE','arm':a.arm,'source_seed':a.seed,'decoder_seed':a.decoder_seed,'updates':ledger['updates'],'English_sha256':sha(out/'English.pt')}),flush=True)
    for step in range(first,plan['training_steps']):
        if interrupted[0] or time.monotonic()-start>plan['train_wall_seconds']:break
        indices=rng.sample(range(len(train)),plan['batch']);losses=[];records=[]
        for i in indices:
            donor=donors.randrange(len(train)-1);donor+=donor>=i
            f=pick(i,donor);targets=target_tokens(tok,[train[i]],a.device)
            loss,preds=human_loss(lm,decoder.adapter(f),targets,tok.bos_token_id,tok.eos_token_id,False,True)
            losses.append(loss);ledger['LM_training_forwards']+=1;ledger['target_token_visits']+=int((targets!=-100).sum())
            records.append({'id':train[i]['id'],'split':'train','update':step+1,'job':os.environ['JOB'],'launch_id':launch,'binding':binding,'labels':targets.cpu().tolist(),'label_mask':(targets!=-100).cpu().tolist(),'predictions':preds.cpu().tolist(),'prediction_kind':'shifted HUMAN teacher forcing diagnostic; never adaptation text','final_sha256':final_digest(f),'answer_mask':f.answer_mask.cpu().tolist(),'donor_id':train[donor]['id'] if a.arm=='shuffled_state' else None,'input_account':accounts[i],'CE':float(loss.detach())})
        opt.zero_grad(set_to_none=True);torch.stack(losses).mean().backward();torch.nn.utils.clip_grad_norm_(decoder.adapter.parameters(),1);opt.step()
        if any(p.grad is not None for m in frozen.values() for p in m.parameters()):raise RuntimeError('frozen component parameter gradient')
        ledger['updates']=step+1
        with (out/'TRAIN-raw.jsonl').open('a') as f:
            for record in records:f.write(json.dumps(record)+'\n')
        if step==first or (step+1)%25==0:durable()
    durable()
    for name,m in frozen.items():
        if component_fingerprint(m)!=frozen_before[name]:raise RuntimeError(name+' changed')
    if ledger['updates']!=plan['training_steps']:
        print(json.dumps({'status':'TRAIN-PARTIAL, NO DEV SCORED','updates':ledger['updates']}),flush=True);return
    # Consume dev only AFTER full train, once. Crash leaves burn; no rescoring.
    burn.write_text(json.dumps({'binding':binding,'English_sha256':sha(out/'English.pt'),'dev_ids':[r['id'] for r in dev],'marks_sha256':sha(a.marks),'stage':'CONSUMED before generation; partial outputs must never be rescored'})+'\n')
    dev_states=[state_for(row,a,lm,tok,reader,executor) for row in dev]
    for i,row in enumerate(dev):
        f,account=dev_states[i]
        if a.arm=='shuffled_state':f=choose_final([{'loop':v[0]} for v in dev_states],i,'shuffled_state',(i+1)%len(dev))
        pred=decoder.generate(f,64)[0];text=tok.decode(pred,skip_special_tokens=True)
        label=tok.encode(row['target_text'],add_special_tokens=False)+[tok.eos_token_id]
        record={'id':row['id'],'split':'dev','binding':binding,'English_sha256':sha(out/'English.pt'),'source_path':row['source_path'],'source_sha256':row['source_sha256'],'source_span':row['source_span'],'labels':label,'label_mask':[True]*len(label),'predictions':pred,'prediction_mask':[True]*len(pred),'target_text':row['target_text'],'answer_text':row['answer_text'],'generated_text':text,'final_sha256':final_digest(f),'latent_mask':f.latent_mask.cpu().tolist(),'answer_mask':f.answer_mask.cpu().tolist(),'input_account':account,'donor_id':dev[(i+1)%len(dev)]['id'] if a.arm=='shuffled_state' else None,'grammar_human_score':None,'faithfulness_human_score':None,'promotion':'NOT SHOWN: independent blind recount + noise + controls required'}
        with (out/'DEV-raw.jsonl').open('a') as raw:raw.write(json.dumps(record,ensure_ascii=False)+'\n')
    print(json.dumps({'status':'RAW DEV OUTPUT COMPLETE, NO SCIENTIFIC VERDICT','n':len(dev),'arm':a.arm,'seed':a.seed,'decoder_seed':a.decoder_seed}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--model-provenance',required=True);p.add_argument('--parent',required=True);p.add_argument('--reader',required=True);p.add_argument('--binding',required=True);p.add_argument('--plan',required=True);p.add_argument('--marks',required=True);p.add_argument('--arm',choices=ARMS,required=True);p.add_argument('--seed',type=int,choices=(0,1),required=True);p.add_argument('--decoder-seed',type=int,choices=(0,1),required=True);p.add_argument('--device',default='cuda');p.add_argument('--corpus',default=str(OWN/'corpus'));p.add_argument('--out',required=True);p.add_argument('--resume',action='store_true');proof(p.parse_args())
