"""Saved-record CPU recount of frozen freshNX8 full versus empty evaluation."""
import os
from pathlib import Path
from recount_noteadapt import read, lines, sha, score


def recount(root):
    root=Path(root);pp=root/'artifacts/cap256-launch/noteadapt-fresh-NX8-v1/PLAN.json';p=read(pp);matrix=root/p['output_namespace'];cl=read(matrix/'CLOSED.json')
    assert sha(pp)=='9a84c3ea0df072f7f4b1b1a55b91c6ac21625ecc95512996b17732be4b8ce9b6'==cl['plan_sha256']
    assert cl['closed'] and cl['native_calls']==64 and cl['optimizer_updates']==cl['consumed_NE_POC_calls']==0 and cl['wall_seconds']<600
    assert len(cl['reports'])==4 and {(v['seed'],v['placement']) for v in cl['reports']}=={(s,t) for s in [0,1] for t in ['notebook','inline']}
    assert all(v['weights_unchanged'] for v in cl['reports'])
    for v in p['file_pins']:assert sha(root/v['path'])==v['sha256']
    assert sha(root/p['fresh_targets']['path'])==p['fresh_targets']['sha256']
    assert sha(matrix/'NATIVE-RAW.jsonl')==cl['native_raw_sha256'] and sha(matrix/'ANSWERS.jsonl')==cl['answers_sha256']
    raw=lines(matrix/'ANSWERS.jsonl');native=lines(matrix/'NATIVE-RAW.jsonl');assert len(raw)==len(native)==64
    assert [v['native_call_index'] for v in raw]==[v['native_call_index'] for v in native]==list(range(1,65))
    assert all(v['observed']['native_generate_call_count']==1 for v in native)
    original=read(root/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/PLAN-v3.json');audit=read(root/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/TOKEN-AUDIT-v4.json');lm=Path(original['warmstart']['tuples']['0']['lm_path'])
    for v in audit['tokenizer_files']:assert sha(lm/v['name'])==v['sha256']
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(lm,local_files_only=True);eos=tok.eos_token_id
    rows=lines(root/p['fresh_inputs']['path']);labels=lines(root/p['fresh_targets']['path']);assert [v['id'] for v in rows]==p['cases']
    byrow={v['id']:v for v in rows};targets={v['episode_id']+':initial':tok.encode(v['numeric_target'],add_special_tokens=False)+[eos] for v in labels}
    assert set(targets)==set(p['cases'])
    for pair in p['predeclared_pairs']:
        assert byrow[pair[0]+':initial']['question']==byrow[pair[1]+':initial']['question'] and targets[pair[0]+':initial']!=targets[pair[1]+':initial']
    results=[];EOS=0
    def identity(v):assert v['job']==cl['job'] and v['plan_sha256']==cl['plan_sha256']
    import hashlib
    for arm in p['arms']:
        seed,placement=arm['seed'],arm['placement'];assert sha(arm['checkpoint']['path'])==arm['checkpoint']['sha256']
        selected=[(v,n) for v,n in zip(raw,native) if v['seed']==seed and v['placement']==placement];assert len(selected)==16
        assert [(v['condition'],v['id']) for v,n in selected]==[(c,i) for c in ['full','empty'] for i in p['cases']]
        keyed={};counts={'full':0,'empty':0}
        for v,n in selected:
            identity(v);identity(n);assert all(v[k]==n[k] for k in ['seed','placement','condition','id','native_call_index'])
            a=v['answer'];assert a['observed']==n['observed'] and a['checkpoint']==arm['checkpoint'] and a['seed']==seed and a['arm']=='loop' and a['rounds']==4 and a['optimizer_updates']==0
            row=byrow[v['id']];full=v['condition']=='full'
            q=(row['question'] if placement=='notebook' else row['history']+'\n'+row['question']) if full else row['question'];c=row['history'] if full and placement=='notebook' else ''
            assert a['input_ids']==[tok.encode(q,add_special_tokens=False)+[eos]] and a['input_mask']==[[True]*len(a['input_ids'][0])]
            assert a['notebook_ids']==[tok.encode(c,add_special_tokens=False)] and a['notebook_mask']==[[True]*len(a['notebook_ids'][0])]
            assert a['question_sha256']==hashlib.sha256(q.encode()).hexdigest() and a['context_sha256']==hashlib.sha256(c.encode()).hexdigest()
            good,valid,_=score(a['observed'],targets[v['id']],eos);keyed[(v['condition'],v['id'])]=good;counts[v['condition']]+=good;EOS+=valid
        pairs=[]
        for pair in p['predeclared_pairs']:
            cases=[i+':initial' for i in pair];f=all(keyed[('full',i)] for i in cases);e=all(keyed[('empty',i)] for i in cases)
            pairs.append({'worlds':pair,'both_correct_full':f,'both_correct_empty':e,'condition_met':f and not e})
        results.append({'seed':seed,'placement':placement,'numeric_exact_actual_EOS_out_of_8':counts,'full_minus_empty':counts['full']-counts['empty'],'paired_wins':sum(keyed[('full',i)] and not keyed[('empty',i)] for i in p['cases']),'paired_losses':sum(keyed[('empty',i)] and not keyed[('full',i)] for i in p['cases']),'predeclared_pairs':pairs,'seed_POC_condition_met':counts['full']>counts['empty'] and any(v['condition_met'] for v in pairs),'checkpoint':arm['checkpoint']})
    route={t:all(v['seed_POC_condition_met'] for v in results if v['placement']==t) for t in ['notebook','inline']}
    return {'schema':'cap256.noteadapt.fresh-NX8.independent-recount.v1','integrity_passed':True,'model_calls':0,'optimizer_updates':0,'consumed_NE_POC_calls':0,'native_calls':64,'valid_terminal_EOS':EOS,'arms':results,'two_seed_POC_pass':route,'mixed_seed_flags':{t:len({v['seed_POC_condition_met'] for v in results if v['placement']==t})>1 for t in ['notebook','inline']},'correction_claim':False,'learned_writer_claim':False,'missing_fact_claim':False,'closed':cl}


if __name__=='__main__':
    import json
    print(json.dumps(recount('C:/Users/benja/sol-cloud-numeric-capability-v1'),sort_keys=True))
