"""Saved-record/CPU-only recount of the TRAIN-only literal continuation."""
import json
import math
import os
from pathlib import Path
from recount_noteadapt import sha, read, lines, digest, score


def recount(root):
    root=Path(root);pp=root/'artifacts/cap256-launch/noteadapt-continue40-v1/PLAN.json';p=read(pp)
    matrix=root/p['output_namespace'];cl=read(matrix/'CLOSED.json')
    assert sha(pp)=='3677409621f43b21c522f74262651c545b8c24f307660e796fe1830ef5b267e2'==cl['plan_sha256']
    assert cl['closed'] and cl['optimizer_updates']==4608 and cl['native_calls']==128 and cl['TEST_calls']==0
    assert len(cl['fits'])==4 and {(v['seed'],v['placement']) for v in cl['fits']}=={(s,t) for s in [0,1] for t in ['notebook','inline']}
    for v in p['file_pins']:assert sha(root/v['path'])==v['sha256']
    for v in p['resumes']:
        for key in ['checkpoint','closed','input_frames']:assert sha(v[key]['path'])==v[key]['sha256']
    for name,key in [('TRAIN-ENDPOINT-RAW.jsonl','TRAIN_endpoint_raw_sha256'),('TRAIN-NATIVE-RAW.jsonl','TRAIN_native_raw_sha256'),('TRAIN-ENDPOINT-TEACHERFORCED.jsonl','TRAIN_teacherforced_raw_sha256')]:assert sha(matrix/name)==cl[key]
    raw=lines(matrix/'TRAIN-ENDPOINT-RAW.jsonl');native=lines(matrix/'TRAIN-NATIVE-RAW.jsonl');tf=lines(matrix/'TRAIN-ENDPOINT-TEACHERFORCED.jsonl');assert len(raw)==len(native)==len(tf)==128
    assert sum(v['observed']['native_generate_call_count'] for v in native)==128 and all(v['observed']['native_generate_call_count']==1 for v in native)
    assert [v['native_call_index'] for v in raw]==[v['native_call_index'] for v in native]==list(range(1,129))
    original=read(root/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/PLAN-v3.json');audit=read(root/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/TOKEN-AUDIT-v4.json');lm=Path(original['warmstart']['tuples']['0']['lm_path'])
    for v in audit['tokenizer_files']:assert sha(lm/v['name'])==v['sha256']
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(lm,local_files_only=True);eos=tok.eos_token_id
    inputs=lines(root/p['data']['TRAIN']['inputs']['path']);labels=lines(root/p['data']['TRAIN']['targets']['path'])
    assert [v['id'] for v in inputs]==p['train_case_ids']
    byrow={v['id']:v for v in inputs};bylabel={v['episode_id']+':initial':tok.encode(v['numeric_target'],add_special_tokens=False)+[eos] for v in labels}
    def identity(v):assert v['job']==cl['job'] and v['plan_sha256']==cl['plan_sha256']
    import torch
    results=[];validEOS=0
    for fit in cl['fits']:
        identity(fit);seed,placement=fit['seed'],fit['placement'];out=matrix/('seed%d'%seed)/placement
        assert fit==read(out/'FIT-CLOSED.json') and fit['optimizer_updates']==1152 and fit['visits_each']==40 and fit['start_cursor']==128 and fit['end_cursor']==1280
        resume=next(v for v in p['resumes'] if v['seed']==seed and v['placement']==placement)
        assert fit['source_checkpoint']==resume['checkpoint'] and sha(fit['checkpoint']['path'])==fit['checkpoint']['sha256']
        rv=read(out/'RESUME-VERIFIED.json');identity(rv);assert rv['full_model_Adam_RNG_equal'] and rv['cursor']==128 and rv['next_id']==p['train_case_ids'][0] and rv['source_checkpoint']==resume['checkpoint']
        initial=read(out/'INITIAL-STATE.json');assert not initial['optimizer_reset'] and initial['train_schedule_sha256']==digest(p['train_case_ids']*36)
        assert sha(out/'INPUT-FRAMES.jsonl')==fit['input_frames_sha256']==resume['input_frames']['sha256']
        frames=lines(out/'INPUT-FRAMES.jsonl');fb={v['id']:v for v in frames};assert [v['id'] for v in frames]==p['train_case_ids']
        for frame in frames:
            assert frame['labels']==[bylabel[frame['id']]] and frame['label_mask']==[[True]*len(bylabel[frame['id']])]
        train=lines(out/'TRAIN-RAW.jsonl');assert sha(out/'TRAIN-RAW.jsonl')==fit['TRAIN_raw_sha256']
        assert len(train)==1152 and [v['update'] for v in train]==list(range(129,1281)) and [v['id'] for v in train]==p['train_case_ids']*36
        for index,v in enumerate(train):
            identity(v);assert v['visit']==(index+128)//32+1 and v['seed']==seed and v['placement']==placement
            assert v['frame_sha256']==fb[v['id']]['frame_sha256'] and v['objective']=='numeric-answer-CE-only' and v['auxiliary_weight']==0
            assert math.isfinite(v['numeric_CE']) and math.isfinite(v['preclip_norm'])
        assert fit['frozen_fingerprints_unchanged'] and fit['durable_reload_equal'] and all(fit['initial_fingerprints'][k]==fit['final_fingerprints'][k] for k in ['reader','prefix','lm'])
        cp=torch.load(fit['checkpoint']['path'],map_location='cpu',weights_only=True)
        assert cp['optimizer_parameter_names']==initial['trainable_names']
        assert cp['updates']==1280 and cp['schema']=='cap256.noteadapt.continuation40.checkpoint.v1' and cp['source_checkpoint']==resume['checkpoint'] and cp['TRAIN_raw_sha256']==fit['TRAIN_raw_sha256']
        group=cp['optimizer']['param_groups'][0];assert group['lr']==.001 and group['weight_decay']==0 and group['betas']==(.9,.999) and group['eps']==1e-8
        assert all(0<int(v['step'])<=1280 and torch.isfinite(v['exp_avg']).all() and torch.isfinite(v['exp_avg_sq']).all() for v in cp['optimizer']['state'].values())
        selected=[(v,n,t) for v,n,t in zip(raw,native,tf) if v['seed']==seed and v['placement']==placement];assert len(selected)==32
        assert [v['id'] for v,n,t in selected]==p['train_case_ids']
        correct=teacher=0;endpointloss=[]
        for v,n,t in selected:
            identity(v);identity(n);identity(t)
            assert all(v[k]==n[k]==t[k] for k in ['seed','placement','id']) and v['native_call_index']==n['native_call_index']
            a=v['answer'];assert a['observed']==n['observed'] and a['seed']==seed and a['arm']=='loop' and a['checkpoint']==fit['checkpoint'] and a['rounds']==4 and a['optimizer_updates']==0
            row=byrow[v['id']];q=row['question'] if placement=='notebook' else row['history']+'\n'+row['question'];c=row['history'] if placement=='notebook' else ''
            assert a['input_ids']==[tok.encode(q,add_special_tokens=False)+[eos]] and a['input_mask']==[[True]*len(a['input_ids'][0])]
            assert a['notebook_ids']==[tok.encode(c,add_special_tokens=False)] and a['notebook_mask']==[[True]*len(a['notebook_ids'][0])]
            import hashlib
            assert a['question_sha256']==hashlib.sha256(q.encode()).hexdigest() and a['context_sha256']==hashlib.sha256(c.encode()).hexdigest()
            good,valid,empty=score(a['observed'],bylabel[v['id']],eos);correct+=good;validEOS+=valid
            assert t['label_sha256']==digest([bylabel[v['id']]]) and math.isfinite(t['numeric_CE'])
            teacher+=t['teacherforced_argmax']==[bylabel[v['id']]];endpointloss.append(t['numeric_CE'])
        results.append({'seed':seed,'placement':placement,'native_TRAIN_numeric_exact_actual_EOS_out_of_32':correct,'fixed_endpoint_teacherforced_exact_out_of_32':teacher,'fixed_endpoint_mean_numeric_CE':sum(endpointloss)/32,'online_pass_mean_CE_visits5_to40':[sum(v['numeric_CE'] for v in train[j:j+32])/32 for j in range(0,1152,32)],'last_online_pass_teacherforced_exact_before_updates':sum(v['teacherforced_argmax']==fb[v['id']]['labels'] for v in train[-32:]),'clipped_updates':sum(v['preclip_norm']>1 for v in train),'nonfinite_flags':0,'fit_wall_seconds':fit['wall_seconds'],'checkpoint':fit['checkpoint']})
        del cp
    return {'schema':'cap256.noteadapt.continuation40.independent-recount.v1','integrity_passed':True,'model_calls':0,'optimizer_updates_by_verifier':0,'TEST_files_read':False,'recounted_additional_updates':4608,'native_TRAIN_calls':128,'valid_actual_EOS_calls':validEOS,'fits':results,'closed':cl,'generalization_claim':False}


if __name__=='__main__':print(json.dumps(recount('C:/Users/benja/sol-cloud-numeric-capability-v1'),sort_keys=True))
