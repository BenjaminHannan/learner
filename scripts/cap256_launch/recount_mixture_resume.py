"""Independent saved-record recount; never loads models or calls a decoder."""
from collections import Counter,defaultdict
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def read(p):return json.loads(Path(p).read_bytes())
def records(p):return [json.loads(line) for line in Path(p).read_bytes().splitlines()]


def exact(r,target):
    """Reconstruct emitted-EOS validity directly from stored native IDs."""
    raw=r['MODEL_raw_generate_ids'];eos=target[-1]
    typed=type(raw) is list and len(raw)==1 and type(raw[0]) is list and all(type(i) is int and i>=0 for i in raw[0])
    ids=raw[0] if typed else None
    valid=(typed and 0<len(ids)<=32 and ids.count(eos)==1 and ids[-1]==eos
           and r['native_generate_call_count']==1 and r['native_call_contract_valid'] is True
           and r['generation_error'] is None and r['MODEL_native_decoder_return']==[ids[:-1]])
    assert r['MODEL_generated_ids_with_observed_EOS']==ids
    return bool(valid and ids==target)


def recount(root,config):
    root=Path(root);cfg=read(config);matrix=root/cfg['output_namespace'];config_hash=sha(config)
    schedules=read(root/cfg['schedules']['path'])['schedules']
    assert sha(root/cfg['schedules']['path'])==cfg['schedules']['sha256']
    assert sha(root/cfg['frames']['path'])==cfg['frames']['sha256']
    assert sha(root/cfg['dev_frames']['path'])==cfg['dev_frames']['sha256']
    train={f['id']:f for f in read(root/cfg['frames']['path'])['rows']}
    dev=read(root/cfg['dev_frames']['path'])['rows'];dev_byid={f['id']:f for f in dev}
    fit=[]
    for seed,arm in cfg['execution_order']:
        folder=matrix/('seed%d'%seed)/arm;closed=read(folder/'CLOSED.json')
        assert closed['closed'] is True and closed['config_sha256']==config_hash
        assert closed['optimizer_updates']==20480 and closed['additional_optimizer_updates']==10240
        source=next(e for e in cfg['sources'] if e['seed']==seed and e['arm']==arm)
        assert sha(root/source['checkpoint']['path'])==source['checkpoint']['sha256']
        assert sha(root/source['closed']['path'])==source['closed']['sha256']
        assert sha(root/source['original_frames']['path'])==source['original_frames']['sha256']
        assert sha(root/closed['checkpoint']['path'])==closed['checkpoint']['sha256']
        raw=folder/'TRAIN-RAW.jsonl';assert sha(raw)==closed['TRAIN_raw_sha256']
        visits=Counter({i:40 for i in cfg['original_ids']})
        rows=records(raw);assert len(rows)==10240
        for n,(r,identity) in enumerate(zip(rows,schedules[str(seed)][arm]),1):
            assert r['update']==10240+n and r['additional_update']==n and r['id']==identity
            resume=cfg.get('resume_sources',{}).get('%d/%s'%(seed,arm))
            expected_config=resume['source_config_sha256'] if resume and n<=5120 else config_hash
            assert r['config_sha256']==expected_config and r['objective']=='numeric-answer-CE-only'
            assert r['lr']==.001 and r['auxiliary_weight']==0
            assert math.isfinite(r['numeric_CE']) and math.isfinite(r['preclip_norm'])
            visits[identity]+=1;assert r['visit_for_row']==visits[identity]
            assert r['labels']==train[identity]['labels'] and r['label_mask']==train[identity]['label_mask']
            assert r['input_frame_sha256']==train[identity]['frame_sha256']
        assert dict(visits)==closed['visits']
        diagnostic=folder/'DIAGNOSTIC-RAW.jsonl';assert sha(diagnostic)==closed['DIAGNOSTIC_raw_sha256']
        ce=records(diagnostic);assert len(ce)==512 and {r['id'] for r in ce}==set(train)
        assert len({r['id'] for r in ce})==512
        for r in ce:
            assert r['update']==20480 and r['labels']==train[r['id']]['labels']
            assert r['cohort']==train[r['id']]['cohort'] and math.isfinite(r['numeric_CE'])
        call=closed['model_call_account']
        assert call=={'TRAIN_optimizer_teacherforcing':10240,'TRAIN_endpoint_teacherforcing':512}
        assert closed['wall_seconds']<=2400 and closed['optimizer_runtime_seconds']<=1800
        fit.append({'seed':seed,'arm':arm,'actual_additional_updates':10240,'inherited_prefix_updates':closed.get('inherited_prefix_updates',0),'physical_updates_this_process':closed.get('optimizer_updates_this_process',10240),'checkpoint_sha256':closed['checkpoint']['sha256'],'TRAIN_CE':{c:sum(r['numeric_CE'] for r in ce if r['cohort']==c)/256 for c in ('original','additional')},'optimizer_seconds':closed['optimizer_runtime_seconds'],'wall_seconds':closed['wall_seconds'],'LM_unchanged_runner_checked':closed['LM_unchanged']})
    terminal=read(matrix/'dev32/CLOSED.json');assert terminal['closed'] is True
    assert terminal['native_calls']==terminal['teacherforced_dev_examples']==128 and terminal['optimizer_updates']==0
    assert terminal['wall_seconds']<=1200
    answers=matrix/'dev32/ANSWERS.jsonl';observations=matrix/'dev32/OBSERVATIONS.jsonl'
    assert sha(answers)==terminal['raw_sha256'] and sha(observations)==terminal['observations_sha256']
    saved=records(answers);obs=records(observations);assert len(saved)==len(obs)==128
    outcomes={};buckets={};eos=0
    for (seed,arm),offset in zip(cfg['execution_order'],range(0,128,32)):
        chunk=saved[offset:offset+32];assert [r['id'] for r in chunk]==[f['id'] for f in dev]
        outcome={};groups=defaultdict(list)
        cp=next(f['checkpoint_sha256'] for f in fit if f['seed']==seed and f['arm']==arm)
        for i,r in enumerate(chunk,offset):
            f=dev_byid[r['id']];o=obs[i]
            assert r['seed']==o['seed']==seed and r['arm']==o['arm']==arm and r['id']==o['id']
            assert r['checkpoint_sha256']==o['checkpoint_sha256']==cp and o['call_index']==i+1
            assert r['canonical_target_ids_with_EOS']==f['labels'][0] and r['group']==f['group']
            assert r['MODEL_raw_generate_ids']==o['MODEL_raw_generate_ids']
            assert math.isfinite(r['numeric_CE'])
            result=exact(r,f['labels'][0]);assert result==r['strict_exact'];outcome[r['id']]=result
            groups[f['group']].append(r['numeric_CE']);eos+=r['termination_reason']=='observed_EOS'
        assert len(groups)==8
        outcomes[(seed,arm)]=outcome
        buckets[(seed,arm)]={'seed':seed,'arm':arm,'strict_correct':sum(outcome.values()),'rows':32,'story_groups':8,'story_balanced_CE':sum(sum(v)/len(v) for v in groups.values())/8}
        assert next(r['strict_correct'] for r in terminal['results'] if r['seed']==seed and r['arm']==arm)==sum(outcome.values())
    pairs=[]
    for seed in (0,1):
        c=outcomes[(seed,'repeat256')];t=outcomes[(seed,'diverse512')]
        pairs.append({'seed':seed,'control_correct':sum(c.values()),'treatment_correct':sum(t.values()),'net_correct':sum(t.values())-sum(c.values()),'both_correct':sum(c[i] and t[i] for i in c),'treatment_only':sum(not c[i] and t[i] for i in c),'control_only':sum(c[i] and not t[i] for i in c),'neither_correct':sum(not c[i] and not t[i] for i in c),'story_balanced_CE_treatment_minus_control':buckets[(seed,'diverse512')]['story_balanced_CE']-buckets[(seed,'repeat256')]['story_balanced_CE']})
    return {'schema':'cap256.mixture10240.independent-saved-recount.v1','recount_pass':True,'model_calls_by_verifier':0,'optimizer_updates_by_verifier':0,'config_sha256':config_hash,'fits':fit,'dev':list(buckets.values()),'paired':pairs,'both_seed_positive_dev_exact':all(p['net_correct']>0 for p in pairs),'native_calls':128,'observed_EOS_valid':eos,'TRAIN_CE_examples':2048,'dev_CE_examples':128,'evaluation_wall_seconds':terminal['wall_seconds'],'fit_wall_seconds_sum':sum(f['wall_seconds'] for f in fit),'generalization_scope':'Prospective common32dev/8stories changedTRAINpolicy comparison; not fullcapabilitygate or purediversity.'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--config',required=True);a=p.parse_args()
    print(json.dumps(recount(a.root,a.config)))
