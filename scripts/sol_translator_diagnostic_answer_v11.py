#!/usr/bin/env python3
"""TRAIN-origin grammatical generation diagnostic; no optimization or DEV scoring.
One unchanged actual ordered-joint prefix per parent across five causal controls.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import argparse,copy,json,time
from types import SimpleNamespace
import torch
from sol_translator_english_ordered_v10 import load_ordered_english
from sol_translator_grounding_v6 import guard_queue
from sol_translator_answer_data_v11 import human_rows,MANIFEST
from sol_translator_answer_states_v11 import read_source,state_for
from sol_translator_proof_v6 import final_digest
from sol_translator_language_proof import choose_final
from sol_translator_provenance import sha
from sol_translator_runtime import component_fingerprint
from scripts.sol_stop_ordered_api2 import make_ordered_fixed4_executor
OWN=ROOT/'artifacts/sol-translator-20260929'

@torch.no_grad()
def run(a):
    guard_queue();torch.set_num_threads(2)
    out=Path(a.out).resolve()
    if not out.is_relative_to(OWN):raise ValueError('owned output only')
    out.mkdir(parents=True,exist_ok=True)
    if (out/'STARTED.json').exists():raise ValueError('duplicate diagnostic: preserve raw, new version required')
    plan=json.loads(Path(a.plan).read_text());binding=json.loads(Path(a.binding).read_text())
    for name,path in [('parent_sha256',a.parent),('reader_sha256',a.reader),('bootstrap_sha256',a.bootstrap),('LM_provenance_sha256',a.model_provenance)]:
        if binding.get(name) is not None and binding[name]!=sha(path):raise ValueError('checkpoint binding mismatch '+name)
        binding[name]=sha(path)
    ledger=json.loads((Path(a.parent).parent/f'grounding-s{a.seed}.json').read_text())
    if ledger['updates']!=plan['training_updates'] or not ledger['parent_frozen'] or not ledger.get('closed'):raise ValueError('ordered joint TRAIN must close500 before diagnostic')
    binding['ordered_TRAIN_ledger_sha256']=sha(Path(a.parent).parent/f'grounding-s{a.seed}.json')
    (out/'STARTED.json').write_text(json.dumps({'binding':binding,'plan_sha256':sha(a.plan),'driver_sha256':sha(__file__),'optimizer_steps':0,'DEV0':True})+'\n')
    start=time.monotonic();rows,_=human_rows(a.corpus)
    by_id={r['id']:r for r in rows};rows=[by_id[i] for i in plan['TRAIN_diagnostic_ids']]
    if [r['id'] for r in rows]!=plan['TRAIN_diagnostic_ids']:raise ValueError('predeclared TRAIN IDs changed')
    dec,tok,_=load_ordered_english(a.model,a.model_provenance,a.bootstrap,a.device)
    args=SimpleNamespace(reader=a.reader,parent=a.parent,corpus=a.corpus,arm='loop',seed=a.seed,device=a.device)
    reader,core,executor=read_source(args,dec.lm)
    before={'core':component_fingerprint(core),'reader':component_fingerprint(reader),'adapter':component_fingerprint(dec.adapter)}
    untrained=copy.deepcopy(core);torch.manual_seed(7300+a.seed)
    for module in untrained.modules():
        if hasattr(module,'reset_parameters'):module.reset_parameters()
    untrained.eval().requires_grad_(False);uexec=make_ordered_fixed4_executor(untrained)
    real=[state_for(r,args,dec.lm,tok,reader,executor) for r in rows]
    count=0;repeats=[]
    for i,row in enumerate(rows):
        for arm in plan['arms']:
            if time.monotonic()-start>plan['diagnostic_wall_seconds']:raise TimeoutError('diagnostic cap; preserve partial raw')
            args.arm=arm
            if arm=='loop':f,account=real[i]
            elif arm=='shuffled_state':
                f=choose_final([{'loop':v[0]} for v in real],i,arm,(i+1)%len(rows));account=dict(real[i][1],donor_id=rows[(i+1)%len(rows)]['id'])
            else:f,account=state_for(row,args,dec.lm,tok,reader,uexec if arm=='untrained' else executor)
            tokens=dec.generate(f,64)[0];label=tok.encode(row['target_text'],add_special_tokens=False)+[tok.eos_token_id]
            record={'id':row['id'],'source_seed':a.seed,'arm':arm,'split':'reused-TRAIN-development-only-not-fresh-proof','binding':binding,'driver_sha256':sha(__file__),'plan_sha256':sha(a.plan),'source_path':row['source_path'],'source_sha256':row['source_sha256'],'source_span':row['source_span'],'human_question':row['question'],'human_evidence_target':row['evidence_text'],'target_origin':'official HUMAN annotation verbatim+EOS','accepted_human_answers':row['accepted_human_answers'],'context_sha256':row['context_sha256'],'annotation_manifest_sha256':sha(MANIFEST),'human_answer':row['answer_text'],'labels':label,'label_mask':[True]*len(label),'predictions':tokens,'prediction_mask':[True]*len(tokens),'generated_text':tok.decode(tokens,skip_special_tokens=True),'final_sha256':final_digest(f),'latent_mask':f.latent_mask.cpu().tolist(),'answer_mask':f.answer_mask.cpu().tolist(),'input_account':account,'grammar_score':None,'faithfulness_score':None,'output_used_as_training_text':False,'same_bootstrap_adapter_all_controls':True}
            with (out/'TRAIN-generation-raw.jsonl').open('a') as stream:stream.write(json.dumps(record,ensure_ascii=False)+'\n')
            count+=1
            if i==0 and arm=='loop':
                repeats=[tokens]+[dec.generate(f,64)[0] for _ in range(2)]
    after={'core':component_fingerprint(core),'reader':component_fingerprint(reader),'adapter':component_fingerprint(dec.adapter)}
    if before!=after:raise ValueError('diagnostic changed checkpoint parameters')
    summary={'status':'CLOSED TRAIN engineering generation; no scientific verdict','source_seed':a.seed,'rows':len(rows),'arms':plan['arms'],'outputs':count,'optimizer_steps':0,'DEV_examples':0,'sleep_updates':0,'wall_seconds':time.monotonic()-start,'same_adapter_controls':True,'three_repeat_first_TRAIN_input_same_tokens':all(x==repeats[0] for x in repeats),'noise_caveat':'One deterministic TRAIN input repeat is insufficient for DEV variance/passmarks','binding':binding,'before':before,'after':after,'peak_allocated':torch.cuda.max_memory_allocated() if a.device.startswith('cuda') else None,'plain':'ABSENT until separately human-trained parent; not a valid substitute'}
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('model','model-provenance','parent','reader','bootstrap','binding','plan','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--seed',type=int,choices=(0,1),required=True);p.add_argument('--corpus',default=str(OWN/'corpus'));p.add_argument('--device',default='cuda');run(p.parse_args())
