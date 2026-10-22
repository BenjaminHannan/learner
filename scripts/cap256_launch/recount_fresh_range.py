"""Independent saved-record recount of the fixed fresh range comparison; no model imports."""
import argparse
import hashlib
import json
from pathlib import Path
from recount_final import score


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())


def recount(root,manifest):
    root=Path(root);m=read(manifest);out=root/m['output_namespace'];closed=read(out/'CLOSED.json')
    assert closed['closed'] and closed['manifest_sha256']==sha(manifest) and closed['native_calls']==512
    expected={e['key']:e for e in m['checkpoints']};sets={};matrix=[]
    for key in m['checkpoint_keys']:
        e=expected[key];end=read(out/key/'CLOSED.json');raw=out/key/'RAW.jsonl';assert sha(raw)==end['raw_sha256']
        records=[json.loads(l) for l in raw.read_bytes().splitlines()];assert [r['id'] for r in records]==m['selected_ids'] and len(records)==32
        primary={};zero={};modal={};eos=0
        for r in records:
            assert r['manifest_sha256']==sha(manifest) and r['checkpoint_key']==key and r['checkpoint_sha256']==e['checkpoint']['sha256']
            assert r['seed']==e['seed'] and r['arm']==e['arm'] and r['endpoint_visits']==e['visits'] and r['fixed_rounds']==4 and r['notebook_tokens']==0 and r['optimizer_updates']==0
            assert r['label_join_after_raw_generation'] and 'terminal_scoring_error' not in r
            ids=r['canonical_target_ids_with_EOS'];terminal=ids[-1]
            primary[r['id']]=score(r,ids);zero[r['id']]=score(r['native_zero_loop'],ids);modal[r['id']]=r['TRAIN_modal_target_ids_with_EOS']==ids
            assert primary[r['id']] is r['target_ids_plus_observed_EOS_exact'] and zero[r['id']] is r['native_zero_loop']['target_ids_plus_observed_EOS_exact'] and modal[r['id']] is r['TRAIN_modal_constant_ids_equal']
            assert r['TRAIN_modal_model_calls']==0 and r['TRAIN_modal_actual_terminal_EOS_observed'] is False
            eos+=bool(r['observed_EOS'])
        counts={'correct':sum(primary.values()),'zero_loop_correct':sum(zero.values()),'TRAIN_modal_correct':sum(modal.values())}
        assert all(end[k]==v for k,v in counts.items()) and end['closed'] and end['total']==32
        sets[key]=primary;matrix.append({'checkpoint_key':key,**counts,'total':32,'emitted_EOS':eos,'raw_sha256':sha(raw),'checkpoint_sha256':e['checkpoint']['sha256']})
    def pair(before,after):
        a=sets[before];b=sets[after];return {'before':before,'after':after,'both_correct':sum(a[i] and b[i] for i in a),'gained':sum(not a[i] and b[i] for i in a),'lost':sum(a[i] and not b[i] for i in a),'neither_correct':sum(not a[i] and not b[i] for i in a),'net_change':sum(b.values())-sum(a.values())}
    return {'schema':'cap256.fresh-range-independent-recount.v1','saved_record_recount_pass':True,'model_calls_by_verifier':0,'optimizer_updates':0,'manifest_sha256':sha(manifest),'matrix':matrix,'paired20_to40':[pair(f's{seed}-{arm}-v20',f's{seed}-{arm}-v40') for seed in [0,1] for arm in ['loop','plain']],'paired_plain_to_loop':[pair(f's{seed}-plain-v{v}',f's{seed}-loop-v{v}') for seed in [0,1] for v in [20,40]],'both_loop_visit40_range26_met':all(sum(sets[f's{seed}-loop-v40'].values())>=26 for seed in [0,1]),'full_capability_gate_claim':False,'partial_numeric_range_with_disclosed_supplemental_source':True,'native_calls_recounted':512,'wall_seconds':closed['wall_seconds'],'question_predictions_per_wall_second':256/closed['wall_seconds'],'peak_cuda_allocated_bytes':closed['peak_cuda_allocated_bytes']}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--manifest',required=True);a=p.parse_args();print(json.dumps(recount(a.root,a.manifest)))
