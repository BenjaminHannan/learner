#!/usr/bin/env python3
"""Convert owner-approved night manifest into a complete assistant bundle.
Does not train, infer, grant learned-stop readiness or activate a pointer.
"""
import argparse,copy,importlib.util,json,os,shutil
from pathlib import Path
from sol_assistant_bundle import owned,pin,verify_pin,sha,save_new,Unavailable
from sol_assistant_ordered_bundle_v10 import verify,version

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def validator(record):
    path=verify_pin(record)
    if path.name!='sol_sleep_ordered_v1.py':raise Unavailable('expected James ordered-night verifier')
    spec=importlib.util.spec_from_file_location('_assistant_actual_night_validator',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.check_decision

def safety(record,parent,reader,prefix):
    r=read(verify_pin(record))
    if (r.get('execution_policy')!='native-fixed4' or r.get('native_state_parity') is not True
        or r.get('parent_sha256')!=parent['sha256'] or r.get('reader_sha256')!=reader['sha256']
        or r.get('prefix_sha256')!=prefix['sha256']):raise Unavailable('candidate exact native fixed4 validation missing')

def build(request,out):
    import torch
    req=read(request);out=owned(out)
    base=verify(req['previous_bundle']);previous=pin(req['previous_bundle'])
    decision=pin(req['decision_path']);check=pin(req['verifier_path']);safe=pin(req['candidate_safety_path'])
    for record,key in ((decision,'trusted_decision_sha256'),(check,'trusted_verifier_sha256'),(safe,'trusted_candidate_safety_sha256')):
        if record['sha256']!=req[key]:raise Unavailable('external trusted evidence bytes differ: '+key)
    d=read(decision['path']);manifest=pin(d['candidate_manifest']);m=read(manifest['path'])
    # Owner API takes digest STRINGS, not BundlePointer pin dictionaries.
    if validator(check)(decision['path'],previous['sha256'],manifest['sha256']) is not True:raise Unavailable('owner candidate rejected')
    if m['previous_bundle_pin']!=previous['sha256'] or m['seed']!=base['checkpoint']['seed']:raise Unavailable('candidate parent session/seed differs')
    a=base['assets']
    for k,role in (('reader','reader'),('provenance','lm_provenance')):
        verify_pin(m[k])
        if m[k]['sha256']!=a[role]['sha256']:raise Unavailable('night changed frozen '+role)
    parent=pin(verify_pin(m['parent']));prefix=pin(verify_pin(m['prefix']))
    safety(safe,parent,a['reader'],prefix)
    resume_paths=[p for p in d['candidate_files'] if Path(p).name=='night-resume.pt']
    if len(resume_paths)!=1:raise Unavailable('unique actual night resume required')
    resume=pin(resume_paths[0]);ledger=pin(d['ledger'])
    if resume['sha256']!=d['candidate_files'][resume_paths[0]]:raise Unavailable('night optimizer bytes differ')
    p=torch.load(parent['path'],map_location='cpu',weights_only=True)
    new=torch.load(prefix['path'],map_location='cpu',weights_only=True)
    old=torch.load(a['adapter']['path'],map_location='cpu',weights_only=True)
    ck=torch.load(resume['path'],map_location='cpu',weights_only=True)
    if p['constructor']['order_contract']!='sol-ordered-notebook-v2' or p['constructor']['notebook_cap']!=512:raise Unavailable('night changed architecture/cap')
    if new['parent_sha256']!=parent['sha256'] or new['reader_sha256']!=a['reader']['sha256'] or new['training_origin']!='verified-human-origin-verbatim':raise Unavailable('candidate prefix not rebound to exact parent')
    if new['training_stage']!='ordered-night-frozen-prefix-rebound-unqualified':raise Unavailable('candidate stage differs')
    if set(new['adapter_state'])!=set(old['adapter_state']) or any(not torch.equal(v.cpu(),old['adapter_state'][k].cpu()) for k,v in new['adapter_state'].items()):raise Unavailable('night altered frozen prefix tensors')
    if set(ck['core'])!=set(p['state_dict']) or any(not torch.equal(v.cpu(),ck['core'][k].cpu()) for k,v in p['state_dict'].items()):raise Unavailable('night resume/core export differs')
    if ck['ledger']!=read(ledger['path']) or ck['ledger']['updates']!=25 or not ck['ledger']['closed']:raise Unavailable('incomplete night resume')
    if not all(k in ck for k in ('sample_rng','torch_rng','cuda_rng','optimizer','binding')) or not ck['optimizer']['state']:raise Unavailable('night optimizer/RNG absent')
    out.mkdir(parents=True,exist_ok=False);frozen={}
    for role,record in {'parent':parent,'adapter':prefix,'resume':resume,'ledger':ledger,'night_decision':decision,'night_manifest':manifest,'night_safety':safe,'night_verifier':check,'night_bundle_builder':pin(__file__)}.items():
        source=verify_pin(record);dest=out/(role+source.suffix)
        if source.suffix=='.pt':os.link(source,dest)
        else:
            with source.open('rb') as f,dest.open('xb') as g:shutil.copyfileobj(f,g)
        frozen[role]=pin(dest)
        if frozen[role]['sha256']!=record['sha256']:raise Unavailable('night snapshot changed')
    b=copy.deepcopy(base);b['assets'].update(frozen)
    for role in ('parent','adapter'):
        b['config'][role+'_path']=frozen[role]['path'];b['config'][role+'_sha256']=frozen[role]['sha256']
    b['checkpoint']['overnight_updates']=25
    b['sleep']={'status':'one actual queued cycle completed; acceptance engineering only','learning_executed':True,'comparative_improvement':'NOT SHOWN'}
    b['candidate_lineage']={'previous_bundle':previous,'awake_joint_resume':a['resume'],'optimizer_resume':frozen['resume'],'optimizer_scope':'ordered core ONLY; halt frozen','training_binding':ck['binding']}
    b['night_link']={'previous_bundle':previous,'decision':decision,'candidate_manifest':manifest,'verifier':check,'candidate_safety':safe,'manifest_sha256':manifest['sha256'],'builder':pin(__file__)}
    b['version']=version(b)
    verify(req['previous_bundle'])
    validator(check)(decision['path'],previous['sha256'],manifest['sha256'])
    save_new(out/'bundle.json',b);verify(out/'bundle.json')
    print(json.dumps({'candidate_bundle':str(out/'bundle.json'),'bundle_sha256':sha(out/'bundle.json'),'candidate_manifest_sha256':manifest['sha256'],'activated':False,'comparative_gain':'NOT SHOWN'}));return out/'bundle.json'

def check_pointer_decision(decision_path,previous_pin,candidate_pin):
    """BundlePointer callback: bridge bundle digest to OWNER candidate-manifest digest."""
    verify_pin(previous_pin);verify_pin(candidate_pin)
    candidate=verify(candidate_pin['path']);link=candidate['night_link']
    for key in ('previous_bundle','decision','candidate_manifest','verifier','candidate_safety','builder'):verify_pin(link[key])
    if link['previous_bundle']['sha256']!=previous_pin['sha256'] or sha(decision_path)!=link['decision']['sha256']:raise Unavailable('different previous model/decision')
    manifest=read(link['candidate_manifest']['path']);a=candidate['assets']
    for role,name in (('parent','parent'),('prefix','adapter'),('reader','reader'),('provenance','lm_provenance')):
        if manifest[role]['sha256']!=a[name]['sha256']:raise Unavailable('assistant bundle does not represent accepted candidate')
    safety(link['candidate_safety'],a['parent'],a['reader'],a['adapter'])
    return validator(link['verifier'])(decision_path,previous_pin['sha256'],link['candidate_manifest']['sha256'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--out',required=True);a=p.parse_args();build(a.request,a.out)
