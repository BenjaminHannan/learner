#!/usr/bin/env python3
"""Frozen-parent English decoder proof: human-only, same controls, two seeds.
Core inference is EXCLUSIVELY delegated to stop-owner's float executor.
"""
import argparse,copy,json,os,random,time
from pathlib import Path
import torch
from sol_translator_decoder import FinalLatent
from sol_translator_english import FrozenEnglishDecoder,load_local_lm
from sol_translator_grounding import HumanInputProjection,human_rows,input_tokens,target_tokens,guard_queue
from sol_translator_runtime import component_fingerprint,make_control,write_final
from sol_translator_provenance import sha
from sol_spatial_attention_core import load_bundle
import scripts.sol_stop_adapter as S
ROOT=Path(__file__).resolve().parents[1];OWN=ROOT/'artifacts/sol-translator-20260929'


def shared_float_adapter(core):
    # The owner supplies this API; no duplicate core transition loop here.
    if not callable(getattr(S.FinalStateAdapter,'execute_embeddings',None)):
        raise SystemExit('WAITING: stop owner immutable-float entrypoint unavailable')
    return S.FinalStateAdapter(core)


def execute_final(adapter,latent,valid):
    flat=latent.flatten(1,2)
    result=adapter.execute_embeddings(flat,valid,(1,flat.shape[1]),policy='learned',compact=True,cap=48)
    if type(result.final) is not FinalLatent:raise TypeError('wrong final-state contract')
    return result


def load_reader(path,device):
    raw=torch.load(path,map_location='cpu',weights_only=True)
    if raw['training_origin']!='verified-human-origin':raise ValueError('human-only input training provenance absent')
    reader=HumanInputProjection(raw['lm_width']).to(device);reader.load_state_dict(raw['state_dict']);return reader.eval().requires_grad_(False),raw


def plain_adapter(bundle,device):
    # Plain parent must be trained on identical human split/budget and exported
    # by core owner. A token-only plain checkpoint cannot substitute here.
    if not bundle:raise SystemExit('WAITING: matched human-grounded plain-parent bundle absent')
    import importlib
    factory=getattr(importlib.import_module('scripts.sol_spatial_attention_core'),'load_plain_bundle',None)
    if factory is None:raise SystemExit('WAITING: spatial load_plain_bundle float entrypoint absent')
    core,meta=factory(bundle,device)
    if meta.get('human_manifest_sha256')!=sha(OWN/'corpus/pairs.json'):raise ValueError('plain trained on wrong human corpus')
    return shared_float_adapter(core),core


def finals_for_rows(rows,lm,tok,reader,loop_adapter,untrained_adapter,plain,device):
    # One row per core call: no variable padding geometry leak at inference.
    result=[];account=[]
    for row in rows:
        ids,valid=input_tokens(tok,[row],device)
        with torch.no_grad():latent=reader(lm.get_input_embeddings()(ids),valid).detach()
        loop=execute_final(loop_adapter,latent,valid)
        untrained=execute_final(untrained_adapter,latent,valid)
        plain_run=execute_final(plain,latent,valid) if plain is not None else None
        e=latent.flatten(1,2)
        embedding=FinalLatent(e,torch.ones_like(e,dtype=torch.bool),valid,(1,e.shape[1]))
        result.append({'loop':loop.final,'embedding':embedding,'untrained':untrained.final,'no_state':make_control(loop.final,'no_state'),**({'plain':plain_run.final} if plain_run is not None else {})})
        for arm,run in [('loop',loop),('untrained',untrained),('plain',plain_run)]:
            if run is None:continue
            account.append({'id':row['id'],'source':arm,'selected_row_rounds':run.audit.selected_row_rounds,'executed_row_rounds':run.audit.executed_row_rounds,'core_sha256':run.audit.core_sha256,'work':run.audit.work})
    return result,account


def choose_final(cache,i,arm,other=None):
    if arm!='shuffled_state':return cache[i][arm]
    if other is None or other==i:raise ValueError('shuffle needs different example')
    own,donor=cache[i]['loop'],cache[other]['loop']
    # Match length by mask-safe interpolation; decoder metadata stays the
    # recipient's. No question/targets enter. Report this shuffled resampling.
    h=torch.nn.functional.interpolate(donor.latent.transpose(1,2),size=own.latent.shape[1],mode='nearest').transpose(1,2)
    mask=torch.nn.functional.interpolate(donor.latent_mask.float().transpose(1,2),size=own.latent.shape[1],mode='nearest').transpose(1,2).bool()
    return FinalLatent(h*mask,mask,own.answer_mask,own.token_shape)


def proof(a):
    guard_queue();torch.set_num_threads(2);rows,registry=human_rows(a.corpus)
    train=[x for x in rows if x['split']=='train'];dev=[x for x in rows if x['split']=='dev']
    out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    if not out.is_relative_to(OWN):raise ValueError('owned output path required')
    lm,tok,prov=load_local_lm(a.model,a.model_provenance,a.device)
    reader,readmeta=load_reader(a.reader,a.device)
    if readmeta['human_manifest_sha256']!=sha(Path(a.corpus)/'pairs.json'):raise ValueError('reader corpus mismatch')
    core,meta=load_bundle(a.parent,a.device);core.eval().requires_grad_(False)
    loop=shared_float_adapter(core)
    plain,plain_core=plain_adapter(a.plain_bundle,a.device) if a.plain_bundle else (None,None)
    frozen={'core':core,'reader':reader,'LM':lm}
    if plain_core is not None:frozen['plain']=plain_core
    torch.manual_seed(7300+a.seed);untrained=copy.deepcopy(core)
    for module in untrained.modules():
        if hasattr(module,'reset_parameters'):module.reset_parameters()
    untrained.eval().requires_grad_(False);random_adapter=shared_float_adapter(untrained)
    frozen_before={k:component_fingerprint(v) for k,v in frozen.items()}
    start=time.monotonic();training,work_tr=finals_for_rows(train,lm,tok,reader,loop,random_adapter,plain,a.device)
    development,work_dv=finals_for_rows(dev,lm,tok,reader,loop,random_adapter,plain,a.device)
    (out/f'core-work-s{a.seed}.json').write_text(json.dumps(work_tr+work_dv)+'\n')
    plan=json.loads((OWN/'ENGLISH-PLAN.json').read_text());results=[]
    if plain is None:
        results.append({'arm':'plain','status':'WAITING: matched human-grounded plain parent missing','loop_credit':'NOT SHOWN'})
    for dseed in (0,1):
        for arm in ('loop','no_state','embedding','untrained','shuffled_state','plain'):
            if arm=='plain' and plain is None:continue
            torch.manual_seed(dseed);decoder=FrozenEnglishDecoder(lm,256,tok.bos_token_id,tok.eos_token_id,prefix_tokens=8).to(a.device)
            if decoder.adapter.parameter_count()>plan['max_adapter_reasoner_ratio']*sum(p.numel() for p in core.parameters()):raise ValueError('output adapter over cap')
            opt=torch.optim.AdamW(decoder.adapter.parameters(),lr=plan['lr']);rng=random.Random(9900+dseed)
            tokens=0;forward_calls=0
            for step in range(plan['training_steps']):
                if time.monotonic()-start>plan['max_wall_seconds']:raise SystemExit('TIME-CAP: partial proof only; no verdict')
                # Same example stream across arms; batch=2 accumulated per-row
                # losses handle variable geometry without encoding label length.
                indices=rng.sample(range(len(train)),plan['batch']);losses=[]
                for i in indices:
                    donor=(i+1+step)%len(train)
                    if donor==i:donor=(donor+1)%len(train)
                    f=choose_final(training,i,arm,donor)
                    target=target_tokens(tok,[train[i]],a.device)
                    losses.append(decoder.target_loss(f,target));tokens+=int((target!=-100).sum());forward_calls+=1
                loss=torch.stack(losses).mean();opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(decoder.adapter.parameters(),1);opt.step()
            outputs=[]
            for i,row in enumerate(dev):
                final=choose_final(development,i,arm,(i+1)%len(dev))
                generated=decoder.generate(final,64)[0];text=tok.decode(generated,skip_special_tokens=True)
                outputs.append({'id':row['id'],'source_seed':a.seed,'decoder_seed':dseed,'source':arm,'output':text,'evidence_exact':text.strip()==row['target_text'].strip(),'human_answer_span_present':row['answer_text'].casefold() in text.casefold(),'grammar_human_score':None,'faithfulness_human_score':None})
            raw={'state_width':256,'hidden':32,'prefix_tokens':8,'adapter_state':decoder.adapter.state_dict(),'human_manifest_sha256':sha(Path(a.corpus)/'pairs.json'),'human_registry_sha256':sha(Path(a.corpus)/'registry.json'),'source_state_contract':'sol-stop-FinalLatent-v1','lm_provenance_sha256':sha(a.model_provenance),'training_origin':'verified-human-origin-verbatim','parent_sha256':sha(a.parent),'reader_sha256':sha(a.reader),'training_stage':'frozen-parent-decoder-proof-unqualified'}
            torch.save(raw,out/f'English-{arm}-s{a.seed}-d{dseed}.pt')
            path=out/f'outputs-{arm}-s{a.seed}-d{dseed}.json';path.write_text(json.dumps(outputs,ensure_ascii=False,indent=1)+'\n')
            report={'source_seed':a.seed,'decoder_seed':dseed,'arm':arm,'exact_evidence':sum(x['evidence_exact'] for x in outputs),'n':len(dev),'human_answer_span_present_report_only':sum(x['human_answer_span_present'] for x in outputs),'grammar_and_semantic_fidelity':'HUMAN_SCORE_REQUIRED','updates':plan['training_steps'],'human_target_token_visits':tokens,'LM_training_forwards':forward_calls,'adapter_parameters':decoder.adapter.parameter_count(),'elapsed_seconds_total':time.monotonic()-start,'verdict':'UNTESTED: human score/noise/matched-parent gates pending','shuffled_resampling':'nearest by position into recipient geometry' if arm=='shuffled_state' else None}
            results.append(report);(out/f'proof-s{a.seed}.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(report),flush=True)
            for k,v in frozen.items():
                if component_fingerprint(v)!=frozen_before[k]:raise RuntimeError(k+' changed in frozen proof')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--model-provenance',required=True);p.add_argument('--parent',required=True);p.add_argument('--reader',required=True);p.add_argument('--plain-bundle');p.add_argument('--seed',type=int,choices=(0,1),required=True);p.add_argument('--device',default='cuda');p.add_argument('--corpus',default=str(OWN/'corpus'));p.add_argument('--out',default=str(OWN/'run'));a=p.parse_args();proof(a)
