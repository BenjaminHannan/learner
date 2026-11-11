"""CPU-only saved-record paired recount; no model calls or TEST data."""
import os
from pathlib import Path
from recount_noteadapt import read, lines, sha, score


def recount(root):
    root=Path(root);pp=root/'artifacts/cap256-launch/noteadapt-crossroute-v1/PLAN.json';p=read(pp);matrix=root/p['output_namespace'];cl=read(matrix/'CLOSED.json')
    assert sha(pp)=='8f95852fa8b99d4b4561194b185c1f4e7af55e71bdd0a1cc7577f2152621623a'==cl['plan_sha256']
    assert cl['closed'] and cl['native_calls']==128 and cl['optimizer_updates']==cl['TEST_calls']==0 and cl['wall_seconds']<600
    assert len(cl['reports'])==4 and {(a['seed'],a['training_placement'],a['inference_placement']) for a in cl['reports']}=={(a['seed'],a['training_placement'],a['inference_placement']) for a in p['arms']}
    for v in p['file_pins']:assert sha(root/v['path'])==v['sha256']
    assert sha(root/p['TRAIN_targets']['path'])==p['TRAIN_targets']['sha256']
    assert sha(p['diagonal']['path'])==p['diagonal']['sha256'] and sha(matrix/'NATIVE-RAW.jsonl')==cl['native_raw_sha256'] and sha(matrix/'ANSWERS.jsonl')==cl['answers_sha256']
    raw=lines(matrix/'ANSWERS.jsonl');native=lines(matrix/'NATIVE-RAW.jsonl');diagonal=lines(p['diagonal']['path']);assert len(raw)==len(native)==len(diagonal)==128
    assert [v['native_call_index'] for v in raw]==[v['native_call_index'] for v in native]==list(range(1,129))
    assert all(v['observed']['native_generate_call_count']==1 for v in native)
    original=read(root/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/PLAN-v3.json');audit=read(root/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/TOKEN-AUDIT-v4.json');lm=Path(original['warmstart']['tuples']['0']['lm_path'])
    for v in audit['tokenizer_files']:assert sha(lm/v['name'])==v['sha256']
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(lm,local_files_only=True);eos=tok.eos_token_id
    targets={v['episode_id']+':initial':tok.encode(v['numeric_target'],add_special_tokens=False)+[eos] for v in lines(root/p['TRAIN_targets']['path'])}
    results=[];EOS=0
    def identity(v):assert v['job']==cl['job'] and v['plan_sha256']==cl['plan_sha256']
    for arm in p['arms']:
        seed,train,infer=arm['seed'],arm['training_placement'],arm['inference_placement'];assert sha(arm['checkpoint']['path'])==arm['checkpoint']['sha256']
        assert sha(arm['diagonal_frames']['path'])==arm['diagonal_frames']['sha256']
        frames=lines(arm['diagonal_frames']['path']);assert [f['id'] for f in frames]==p['cases'];fb={v['id']:v for v in frames}
        own=[v for v in diagonal if v['seed']==seed and v['placement']==train];cross=[(v,n) for v,n in zip(raw,native) if v['seed']==seed and v['training_placement']==train]
        assert len(own)==len(cross)==32 and [v['id'] for v in own]==[v['id'] for v,n in cross]==p['cases']
        ownbits=[];crossbits=[]
        for old,(v,n) in zip(own,cross):
            identity(v);identity(n);assert all(v[k]==n[k] for k in ['seed','training_placement','inference_placement','id','native_call_index']) and v['inference_placement']==infer
            a=v['answer'];f=fb[v['id']];assert a['observed']==n['observed'] and a['checkpoint']==arm['checkpoint']==old['answer']['checkpoint']
            assert a['seed']==seed and a['arm']=='loop' and a['rounds']==4 and a['optimizer_updates']==0
            assert a['input_ids']==f['input_ids'] and a['input_mask']==f['input_mask'] and a['notebook_ids']==f['notebook_ids'] and a['notebook_mask']==f['notebook_mask']
            oldgood,oldvalid,_=score(old['answer']['observed'],targets[v['id']],eos);good,valid,_=score(a['observed'],targets[v['id']],eos)
            assert oldvalid;ownbits.append(oldgood);crossbits.append(good);EOS+=valid
        results.append({'seed':seed,'training_placement':train,'inference_placement':infer,'own_route_numeric_exact_actual_EOS_out_of_32':sum(ownbits),'cross_route_numeric_exact_actual_EOS_out_of_32':sum(crossbits),'cross_minus_own':sum(crossbits)-sum(ownbits),'paired_wins':sum(b and not a for a,b in zip(ownbits,crossbits)),'paired_losses':sum(a and not b for a,b in zip(ownbits,crossbits)),'paired_both_correct':sum(a and b for a,b in zip(ownbits,crossbits)),'paired_both_wrong':sum(not a and not b for a,b in zip(ownbits,crossbits)),'checkpoint':arm['checkpoint']})
    notebook=[v for v in results if v['training_placement']=='notebook']
    return {'schema':'cap256.noteadapt.crossroute.independent-recount.v1','integrity_passed':True,'model_calls':0,'optimizer_updates':0,'TEST_files_read':False,'native_offdiagonal_calls':128,'diagonal_calls_reused_without_rerun':128,'valid_terminal_EOS':EOS,'arms':results,'both_notebook_trained_seeds_improve_inline':all(v['cross_minus_own']>0 for v in notebook),'generalization_claim':False,'unique_causal_component_claim':False,'closed':cl}


if __name__=='__main__':
    import json
    print(json.dumps(recount('C:/Users/benja/sol-cloud-numeric-capability-v1'),sort_keys=True))
