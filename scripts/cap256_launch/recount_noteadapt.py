"""CPU-only recount of frozen initial-only v2 fits and64 native predictions."""
import hashlib
import json
import math
import os
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines()]
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def score(o,target,eos):
    raw=o['MODEL_raw_generate_ids'];assert type(raw) is list and len(raw)==1 and all(type(v) is int for v in raw[0])
    full=raw[0];assert full==o['MODEL_generated_ids_with_observed_EOS']
    positions=[i for i,v in enumerate(full) if v==eos];assert positions==o['EOS_positions'] and bool(positions)==o['observed_EOS']
    stripped=full[:positions[0]] if positions else full
    assert o['MODEL_native_decoder_return']==[stripped] and o['native_stripped_output_equal']
    valid=(o['native_generate_call_count']==1 and o['native_call_contract_valid'] is True and o['generation_error'] is None
           and len(full)<=32 and positions==[len(full)-1] and o['termination_reason']=='observed_EOS')
    return bool(valid and full==target),valid,stripped==[]


def recount(root):
    root=Path(root);planpath=root/'artifacts/cap256-launch/noteadapt-initial-v2/PLAN.json';p=read(planpath);matrix=root/p['output_namespace'];cl=read(matrix/'CLOSED.json')
    assert sha(planpath)=='da6be8a8ca4e83c8edf7b5923c31e1c36edbdb5a8d9594765121aded379eb5aa'==cl['plan_sha256']
    assert cl['closed'] and cl['optimizer_updates']==512 and cl['native_calls']==64 and len(cl['fits'])==4
    assert {(f['seed'],f['placement']) for f in cl['fits']}=={(seed,arm) for seed in [0,1] for arm in ['notebook','inline']}
    def identity(v):assert v['plan_sha256']==cl['plan_sha256'] and v['job']==cl['job']
    for pin in p['file_pins']:assert sha(root/pin['path'])==pin['sha256']
    assert sha(matrix/'TEST-RAW.jsonl')==cl['TEST_raw_sha256'] and sha(matrix/'TEST-NATIVE-RAW.jsonl')==cl['TEST_native_raw_sha256']
    records=lines(matrix/'TEST-RAW.jsonl');native=lines(matrix/'TEST-NATIVE-RAW.jsonl');assert len(records)==len(native)==64
    original=read(root/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/PLAN-v3.json');audit=read(root/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/TOKEN-AUDIT-v4.json');lm=Path(original['warmstart']['tuples']['0']['lm_path'])
    for v in audit['tokenizer_files']:assert sha(lm/v['name'])==v['sha256']
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(lm,local_files_only=True);eos=tok.eos_token_id
    source={split:lines(root/p['data'][split]['inputs']['path']) for split in ['TRAIN','TEST']};labels={split:{r['episode_id']+':initial':r['numeric_target'] for r in lines(root/p['data'][split]['targets']['path'])} for split in ['TRAIN','TEST']}
    bytest={r['id']:r for r in source['TEST']};bytrain={r['id']:r for r in source['TRAIN']};results=[];fithashes=[];firststates={};EOS=0;emptyEOS=0
    for fit in cl['fits']:
        identity(fit)
        seed,placement=fit['seed'],fit['placement'];out=matrix/('seed%d'%seed)/placement
        assert fit==read(out/'FIT-CLOSED.json') and fit['closed'] and fit['optimizer_updates']==128 and fit['visits_each']==4
        assert sha(fit['checkpoint']['path'])==fit['checkpoint']['sha256'] and fit['parent_checkpoint']==p['parents'][seed]['checkpoint']
        assert sha(fit['parent_checkpoint']['path'])==fit['parent_checkpoint']['sha256']
        assert fit['durable_reload_equal'] and fit['frozen_fingerprints_unchanged']
        assert all(fit['initial_fingerprints'][k]==fit['final_fingerprints'][k] for k in ['reader','prefix','lm'])
        assert sha(out/'TRAIN-RAW.jsonl')==fit['TRAIN_raw_sha256'] and sha(out/'INPUT-FRAMES.jsonl')==fit['input_frames_sha256']
        initial=read(out/'INITIAL-STATE.json');identity(initial);assert initial['Adam_state_entries']==0 and initial['optimizer_reset'] is True
        assert all(v.startswith('core.') and not v.startswith('core.halt.') for v in initial['trainable_names'])
        assert initial['train_schedule_sha256']==digest(p['train_case_ids']*4)
        if seed in firststates:
            old=firststates[seed];assert all(initial[k]==old[k] for k in ['fingerprints','RNG_sha256','Adam_state_entries','trainable_names','train_schedule_sha256'])
        else:firststates[seed]=initial
        frames=lines(out/'INPUT-FRAMES.jsonl');assert [f['id'] for f in frames]==p['train_case_ids'];frameby={f['id']:f for f in frames}
        for f in frames:
            row=bytrain[f['id']];question=row['question'] if placement=='notebook' else row['history']+'\n'+row['question'];context=row['history'] if placement=='notebook' else ''
            assert f['input_ids']==[tok.encode(question,add_special_tokens=False)+[eos]] and f['input_mask']==[[True]*len(f['input_ids'][0])]
            assert f['notebook_ids']==[tok.encode(context,add_special_tokens=False)] and f['notebook_mask']==[[True]*len(f['notebook_ids'][0])]
            assert f['labels']==[tok.encode(labels['TRAIN'][f['id']],add_special_tokens=False)+[eos]] and f['label_mask']==[[True]*len(f['labels'][0])]
            body={k:v for k,v in f.items() if k!='frame_sha256'};assert digest(body)==f['frame_sha256']
        train=lines(out/'TRAIN-RAW.jsonl');assert len(train)==128 and [r['update'] for r in train]==list(range(1,129)) and [r['id'] for r in train]==p['train_case_ids']*4
        for j,r in enumerate(train):
            identity(r)
            assert r['visit']==j//32+1 and r['seed']==seed and r['placement']==placement
            assert r['frame_sha256']==frameby[r['id']]['frame_sha256'] and r['objective']=='numeric-answer-CE-only' and r['auxiliary_weight']==0
            assert math.isfinite(r['numeric_CE']) and math.isfinite(r['preclip_norm'])
        counts={'full':0,'empty':0};keyed={}
        selected=[(r,n) for r,n in zip(records,native) if r['seed']==seed and r['placement']==placement];assert len(selected)==16
        assert [(r['condition'],r['id']) for r,n in selected]==[(c,i) for c in ['full','empty'] for i in p['test_case_ids']]
        for r,n in selected:
            identity(r);identity(n)
            assert all(r[k]==n[k] for k in ['native_call_index','seed','placement','condition','id']) and r['answer']['observed']==n['observed']
            a=r['answer'];assert a['seed']==seed and a['arm']=='loop'
            row=bytest[r['id']];full=r['condition']=='full'
            question=(row['question'] if placement=='notebook' else row['history']+'\n'+row['question']) if full else row['question'];context=row['history'] if full and placement=='notebook' else ''
            assert a['input_ids']==[tok.encode(question,add_special_tokens=False)+[eos]] and a['input_mask']==[[True]*len(a['input_ids'][0])]
            assert a['notebook_ids']==[tok.encode(context,add_special_tokens=False)] and a['notebook_mask']==[[True]*len(a['notebook_ids'][0])]
            assert a['rounds']==4 and a['optimizer_updates']==0 and a['checkpoint']==fit['checkpoint']
            assert a['question_sha256']==hashlib.sha256(question.encode()).hexdigest() and a['context_sha256']==hashlib.sha256(context.encode()).hexdigest()
            target=tok.encode(labels['TEST'][r['id']],add_special_tokens=False)+[eos];good,valid,empty=score(a['observed'],target,eos)
            assert a['text']==tok.decode(a['observed']['MODEL_native_decoder_return'][0],skip_special_tokens=True)
            counts[r['condition']]+=int(good);keyed[(r['condition'],r['id'])]=good;EOS+=int(valid);emptyEOS+=int(empty and valid)
        pair=[v+':initial' for v in p['primary_counterfactual_pair']];pairfull=all(keyed[('full',v)] for v in pair);pairempty=all(keyed[('empty',v)] for v in pair)
        result={'seed':seed,'placement':placement,'numeric_correct_out_of_8':counts,'full_minus_empty':counts['full']-counts['empty'],'primary_pair_both_correct_full':pairfull,'primary_pair_both_correct_empty':pairempty,'pilot_condition_met':counts['full']>counts['empty'] and pairfull and not pairempty,'paired_gains':sum(keyed[('full',i)] and not keyed[('empty',i)] for i in p['test_case_ids']),'paired_losses':sum(keyed[('empty',i)] and not keyed[('full',i)] for i in p['test_case_ids']),'TRAIN_pass_mean_CE':[sum(r['numeric_CE'] for r in train[j:j+32])/32 for j in range(0,128,32)],'last_pass_teacherforced_exact_before_each_update':sum(r['teacherforced_argmax']==frameby[r['id']]['labels'] for r in train[-32:]),'TRAIN_endpoint_native_generation_accuracy':'NOT_MEASURED; no additional generation allowed','clipped_updates':sum(r['preclip_norm']>1 for r in train),'nonfinite_flags':0,'fit_wall_seconds':fit['wall_seconds']}
        results.append(result);fithashes.append({'seed':seed,'placement':placement,'checkpoint_sha256':fit['checkpoint']['sha256'],'TRAIN_raw_sha256':fit['TRAIN_raw_sha256'],'input_frames_sha256':fit['input_frames_sha256']})
    assert [r['native_call_index'] for r in records]==list(range(1,65))
    notebook=[r for r in results if r['placement']=='notebook'];inline=[r for r in results if r['placement']=='inline']
    return {'schema':'cap256.noteadapt.initial-only.independent-recount.v2','integrity_passed':True,'model_calls':0,'optimizer_updates_by_verifier':0,'recounted_optimizer_updates':512,'recounted_native_calls':64,'valid_actual_EOS_calls':EOS,'empty_EOS_calls':emptyEOS,'fits':results,'fit_hashes':fithashes,'notebook_two_seed_POC_pass':all(r['pilot_condition_met'] for r in notebook),'inline_two_seed_diagnostic_pass':all(r['pilot_condition_met'] for r in inline),'notebook_mixed_seeds':len({r['pilot_condition_met'] for r in notebook})>1,'primary_counterfactual_pair':p['primary_counterfactual_pair'],'learned_writer_claim':False,'correction_claim':False,'generalization_or_statistical_certification':False,'closed':cl,'evidence_limit':'Native argument-key contract saved; generation setting values established by unchanged pinned source, not per-call saved values. TRAIN last-pass predictions are teacher-forced before eachupdate, not fixed-endpoint native accuracy.'}


if __name__=='__main__':print(json.dumps(recount('C:/Users/benja/sol-cloud-numeric-capability-v1'),sort_keys=True))
