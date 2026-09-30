#!/usr/bin/env python3
"""Queue-only joined engineering on admitted TRAIN literals. UTF-8 explicit. Outputs never training."""
import argparse,json,os,sys,time,hashlib
from pathlib import Path
from sol_assistant_bundle import ROOT,owned,save_new,sha,verify_pin,source_closure,load,verify_bundle
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))

def fingerprint(t):return hashlib.sha256(t.detach().cpu().contiguous().view(__import__('torch').uint8).numpy().tobytes()).hexdigest()

def run(a):
    if not os.environ.get('JOB') or not os.environ.get('TREE'):raise RuntimeError('watcher job required; no direct GPU use')
    import torch
    from scripts.sol_stop_adapter import FinalLatent,module_hash
    from sol_translator_decoder import validate_final
    torch.set_num_threads(2);start=time.monotonic();out=owned(a.out);out.mkdir(parents=True,exist_ok=False)
    plan=json.loads(Path(a.plan).read_text(encoding='utf-8'))
    assert plan['seeds']==[0,1] and plan['max_tokens']==64 and plan['rows_per_seed']==2
    for p in plan['pins']:verify_pin(p)
    rows=json.loads(Path(a.rows).read_text(encoding='utf-8'));assert sha(a.rows)==plan['rows_sha256'] and len(rows)==2
    sources=source_closure([__file__]);save_new(out/'pre-execution.json',dict(plan_sha256=sha(a.plan),sources=sources,rows_sha256=sha(a.rows)))
    b,f=load(a.bundle,a.device);seed=b['checkpoint']['seed'];assert seed in plan['seeds']
    ledger=json.loads(Path(b['assets']['ledger']['path']).read_text(encoding='utf-8'))
    assert all(r['id'] in ledger['train_unique_ids'] and r['split']=='train' for r in rows)
    assert b['checkpoint']['human_manifest_sha256']==plan['human_pairs_sha256']
    core=f.frozen_reasoner.adapter.core;before=module_hash(core);torch.cuda.reset_peak_memory_stats() if a.device=='cuda' else None
    accounts=[];saved={};seen=[]
    def boundary(module,args):
        assert len(args)==1 and type(args[0]) is FinalLatent
        validate_final(args[0]);seen.append(dict(shape=list(args[0].latent.shape),latent_sha256=fingerprint(args[0].latent),payload='canonical FinalLatent ONLY'))
    handle=f.final_state_decoder.adapter.register_forward_pre_hook(boundary)
    with torch.no_grad():
        for row in rows:
            assert time.monotonic()-start<plan['seconds_per_seed']
            encoded=f.input_encoder.encode(json.dumps({'question':row['question'],'context':row['context']}))
            memo=f.notebook_encoder(encoded['notebook']);query=encoded['embeddings'];qn=query.shape[1]
            def execute(memory):
                return f.frozen_reasoner.execute_embeddings(query,encoded['answer_mask'],encoded['token_shape'],notebook_latents=memory,notebook_mask=torch.ones(memory.shape[:2],dtype=torch.bool,device=memory.device),policy='fixed',cap=4,compact=True)
            full=execute(memo);repeat=execute(memo);empty=execute(memo[:,:0])
            padded={'translated':torch.cat((memo,torch.full_like(memo[:,:1],999)),1),'mask':torch.cat((torch.ones(memo.shape[:2],dtype=torch.bool,device=memo.device),torch.zeros((1,1),dtype=torch.bool,device=memo.device)),1)}
            gathered=f.notebook_encoder(padded);masked=execute(gathered)
            final=full.final;validate_final(final)
            checks=dict(canonical=type(final) is FinalLatent,query_only=final.latent.shape==query.shape,query_answer_mask=torch.equal(final.answer_mask,encoded['answer_mask']),valid_latent_mask=bool(final.latent_mask.all()),gather_exact=torch.equal(gathered,memo),masked_padding_exact=torch.equal(final.latent,masked.final.latent),repeat_exact=torch.equal(final.latent,repeat.final.latent))
            predictions={};payloads={}
            for name,run in [('full',full),('no_memory',empty)]:
                tokens=f.final_state_decoder.generate(run.final,64)[0]
                predictions[name]={'token_ids':tokens,'text':f.tokenizer.decode(tokens,skip_special_tokens=True),'training_eligible':False,'origin':'model-output-log-only'}
                payloads[name]=dict(latent_sha256=fingerprint(run.final.latent),shape=list(run.final.latent.shape),answer_mask=run.final.answer_mask.cpu().tolist(),token_shape=list(run.final.token_shape),rounds=run.audit.rounds.cpu().tolist(),row_rounds=run.audit.executed_row_rounds)
                saved[row['id']+'-'+name]={k:getattr(run.final,k).cpu() for k in ('latent','latent_mask','answer_mask')}
            # Actual public factory API compatibility, no substitute generator.
            public=f.reply(json.dumps({'question':row['question'],'context':row['context']}),max_tokens=64)
            checks['public_reply_matches_direct']=public==predictions['full']['text']
            accounts.append(dict(id=row['id'],origin='verified-human-corpus-TRAIN; NOT interactive capture',question=row['question'],context=row['context'],human_label=row['answer_text'],human_target=row['target_text'],provenance=row['provenance'],checks=checks,query_positions=qn,notebook_positions=memo.shape[1],repeat_max_abs=float((final.latent-repeat.final.latent).abs().max()),masked_padding_max_abs=float((final.latent-masked.final.latent).abs().max()),notebook_removal_max_abs=float((final.latent-empty.final.latent).abs().max()),payloads=payloads,predictions=predictions,semantic_status='UNQUALIFIED; TRAIN familiarity, no score/generalization claim'))
    handle.remove();torch.save(saved,out/'final-payloads.pt')
    unchanged=module_hash(core)==before
    for p in sources:verify_pin(p)
    verify_bundle(a.bundle)
    result=dict(seed=seed,bundle=b['version'],updates=b['checkpoint']['updates'],scope='actual joined TRAIN-only engineering',rows=accounts,decoder_boundary_calls=seen,core_unchanged=unchanged,optimizer_steps=0,sleep_updates=0,learned_stop_ready=False,semantic_English='NOT SHOWN',benchmark='NOT SHOWN',seconds=time.monotonic()-start,peak_allocated=torch.cuda.max_memory_allocated() if a.device=='cuda' else None,training_data_created=False)
    save_new(out/'raw.json',result)
    print(json.dumps({'seed':seed,'rows':len(accounts),'checks_passed':sum(sum(x['checks'].values()) for x in accounts),'checks_total':sum(len(x['checks']) for x in accounts),'core_unchanged':unchanged,'seconds':result['seconds'],'raw_sha256':sha(out/'raw.json'),'semantic_status':'UNQUALIFIED'}))
    assert unchanged and all(all(x['checks'].values()) for x in accounts) and result['seconds']<plan['seconds_per_seed']
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('bundle','rows','plan','out'):p.add_argument('--'+k,required=True)
    p.add_argument('--device',default='cuda');run(p.parse_args())
