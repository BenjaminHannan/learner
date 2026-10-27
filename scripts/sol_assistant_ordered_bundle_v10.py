#!/usr/bin/env python3
"""Immutable ordered-core engineering bundle. Real owner factory only, no fallback."""
import argparse,importlib,json,os,shutil,sys
from pathlib import Path
from sol_assistant_bundle import ROOT,owned,sha,pin,verify_pin,source_closure,save_new,identity,Unavailable
FACTORY='scripts.sol_translator_runtime_ordered_v10:load_d256_notebook_factories'
ORDER='sol-ordered-notebook-v2'
OWNER_SEAL_SHA='5946f8e94da4edb3182f04684a5420ab823e46328f3718393a11627d2082ca65'
OLD_STOP='845f955e798af2f1850804e27fa74af80c5d96751cd77d36effaa72c3e67d680'
NATIVE_STOP_SHA='150290c3f2bc82d46cab91047c8e21879de2ddc231f44f06371148e1116e5238'
ORDERED_CORE_SHA='5344e622855c875312f77a88095d287a5709e17dbaca23c90bdd8733b0a38291'
SCHEMA='sol.assistant.ordered-awake.v10'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def version(b):return identity({k:v for k,v in b.items() if k!='version'})

def freeze(request,out):
    import torch
    req=read(request);config=read(req['config_path']);out=owned(out)
    if config.get('factory')!=FACTORY or config.get('order_contract')!=ORDER or config.get('reader_version')!='human-notebook-v2':raise Unavailable('exact NEW ordered owner factory/reader contract required')
    if config['stop_factory_sha256']==OLD_STOP:raise Unavailable('old API4 drops ordered begin path')
    if config['stop_factory_sha256']!=NATIVE_STOP_SHA or config.get('ordered_core_sha256')!=ORDERED_CORE_SHA:raise Unavailable('unsealed or different native ordered boundary')
    module_name=FACTORY.split(':')[0];factory_file=ROOT/(module_name.replace('.','/')+'.py')
    if sha(factory_file)!=config['runtime_factory_sha256']:raise Unavailable('ordered runtime source absent/changed')
    release=pin(req['release_path'])
    if release['sha256']!=OWNER_SEAL_SHA or req['release_sha256']!=OWNER_SEAL_SHA:raise Unavailable('owner release digest differs')
    release_files=read(release['path'])['files']
    if release_files.get(factory_file.relative_to(ROOT).as_posix())!=config['runtime_factory_sha256']:raise Unavailable('runtime not in owner release')
    for source,key in [('scripts/sol_spatial_poc_ordered_v2.py','ordered_core_sha256'),('scripts/sol_stop_ordered_api2.py','stop_factory_sha256')]:
        if sha(ROOT/source)!=config[key] or release_files.get(source)!=config[key]:raise Unavailable('core/native executor differs from owner release')
    sources=source_closure([factory_file,__file__,ROOT/'scripts/sol_assistant_ordered_chat_v10.py'])
    if config['stop_factory_sha256'] not in {p['sha256'] for p in sources}:raise Unavailable('ordered executor source not in factory closure')
    components={k:pin(config[k+'_path']) for k in ('parent','reader','adapter')}
    for k,p in components.items():
        if p['sha256']!=config[k+'_sha256']:raise Unavailable('component differs: '+k)
    evidence={k:pin(req[k+'_path']) for k in ('ledger','transport','stdout','resume')}
    ledger=read(evidence['ledger']['path']);transport=read(evidence['transport']['path'])
    if transport['returncode']!=0:raise Unavailable('owner job not complete')
    if not (ledger.get('closed') is True or ledger.get('parent_frozen') is True):raise Unavailable('requires closed owner checkpoint')
    if ledger.get('requested_updates_completed') is not True or ledger.get('interrupted') is True:raise Unavailable('ordered requested fit not complete')
    if type(ledger.get('updates')) is not int or ledger['updates']<=0 or ledger.get('raw_watermark_update')!=ledger['updates']:raise Unavailable('actual durable updates/watermark absent')
    if ledger['updates']!=500 or transport.get('seed')!=ledger['seed']:raise Unavailable('requires exact closed500 seed')
    receipts=[]
    for line in Path(evidence['stdout']['path']).read_text(encoding='utf-8').splitlines():
        try:row=json.loads(line)
        except json.JSONDecodeError:continue
        if isinstance(row,dict) and row.get('status')=='DURABLE-TRAIN-WEIGHTS':receipts.append(row)
    if not receipts:raise Unavailable('actual final stdout DURABLE receipt absent')
    final=receipts[-1]
    if any(final.get(k)!=v for k,v in {'seed':ledger['seed'],'updates':500,'parent_sha256':components['parent']['sha256'],'resume_sha256':evidence['resume']['sha256']}.items()):raise Unavailable('last DURABLE differs from closed tuple')
    hashes=transport.get('hashes',transport.get('paths_and_hashes',{}))
    for p in [*components.values(),evidence['resume'],evidence['ledger']]:
        matches=[v for k,v in hashes.items() if k.replace('\\','/').split('/')[-1]==Path(p['path']).name]
        if matches!=[p['sha256']]:raise Unavailable('transport does not bind '+p['path'])
    parent,reader,adapter=(torch.load(components[k]['path'],map_location='cpu',weights_only=True) for k in ('parent','reader','adapter'))
    constructor=parent['constructor']
    if constructor.get('family')!='ordered-loop-D256-v2' or constructor.get('order_contract')!=ORDER:raise Unavailable('not an actual ordered-loop checkpoint')
    if constructor.get('notebook_cap')!=512 or constructor.get('query_cap')!=49:raise Unavailable('release requires full TRAIN coverage cap512 and query49')
    if not all(k in parent['state_dict'] for k in ('position_frequencies','boundary_roles')):raise Unavailable('position/role buffers absent')
    if parent['metadata'].get('input_version')!='human-notebook-ordered-v10' or parent['metadata'].get('order_contract')!=ORDER:raise Unavailable('ordered input version missing')
    if reader.get('reader_version')!='human-notebook-v2' or reader.get('training_origin')!='verified-human-origin':raise Unavailable('human pointwise reader required')
    if reader.get('input_version')!='human-notebook-ordered-v10' or reader.get('order_contract')!=ORDER:raise Unavailable('reader ordered lineage absent')
    if adapter.get('training_origin')!='verified-human-origin-verbatim' or adapter['parent_sha256']!=components['parent']['sha256'] or adapter['reader_sha256']!=components['reader']['sha256']:raise Unavailable('decoder origin/exact binding mismatch')
    if adapter['human_manifest_sha256']!=reader['human_manifest_sha256']:raise Unavailable('corpus mismatch')
    if adapter.get('training_stage')!='ordered-joint-grounding-unqualified':raise Unavailable('old prefix cannot qualify new ordered parent')
    resume=torch.load(evidence['resume']['path'],map_location='cpu',weights_only=True)
    if resume['ledger']['updates']!=ledger['updates'] or resume['ledger']['raw_watermark_update']!=ledger['raw_watermark_update']:raise Unavailable('resume/ledger durable update mismatch')
    for role,export in [('core',parent['state_dict']),('reader',reader['state_dict']),('adapter',adapter['adapter_state'])]:
        if set(resume[role])!=set(export) or any(not torch.equal(resume[role][k].cpu(),v.cpu()) for k,v in export.items()):raise Unavailable('new joint resume/export differs: '+role)
    if not all(k in resume for k in ('sample_rng','torch_rng','cuda_rng','binding')):raise Unavailable('actual joint RNG/source lineage absent')
    populated=sum(all(k in state for k in ('step','exp_avg','exp_avg_sq')) and float(state['step'])>0 for state in resume['optimizer']['state'].values())
    if not populated:raise Unavailable('new joint optimizer not populated')
    lm_provenance=pin(config['lm_provenance']);inventory=read(lm_provenance['path'])
    if adapter['lm_provenance_sha256']!=lm_provenance['sha256']:raise Unavailable('decoder/LM provenance mismatch')
    loader_source='scripts/sol_translator_english_ordered_v10.py'
    if release_files.get(loader_source)!=sha(ROOT/loader_source):raise Unavailable('ordered prefix validator not sealed by owner')
    sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
    importlib.import_module('sol_translator_english_ordered_v10').validate_ordered_prefix(adapter,lm_provenance['path'])
    lmfiles=[{'path':str(Path(config['lm_path'])/name),'sha256':h} for name,h in inventory['files'].items()]
    for p in lmfiles:verify_pin(p)
    out.mkdir(parents=True,exist_ok=False);frozen={}
    for role,p in {**components,**evidence,'release':release,'lm_provenance':lm_provenance,'owner_config':pin(req['config_path'])}.items():
        src=verify_pin(p);dest=out/(role+src.suffix)
        if src.suffix=='.pt':os.link(src,dest)
        else:
            with src.open('rb') as f,dest.open('xb') as g:shutil.copyfileobj(f,g)
        frozen[role]=pin(dest)
        if frozen[role]['sha256']!=p['sha256']:raise Unavailable('source changed during freeze')
    original_config=dict(config)
    for k in ('parent','reader','adapter'):config[k+'_path']=frozen[k]['path']
    config['lm_provenance']=frozen['lm_provenance']['path']
    b={'schema':SCHEMA,'factory':FACTORY,'config':config,'assets':frozen,'sources':sources,'lm_files':lmfiles,'checkpoint':{'seed':ledger['seed'],'updates':ledger['updates'],'order_contract':ORDER,'notebook_cap':512,'query_cap':49},'execution':{'policy':'fixed','cap':4,'learned_stop_qualified':False},'sleep':{'status':'PENDING exact-checkpoint safety and actual queued update integration','learning_executed':False},'semantic_status':'NOT SHOWN until actual predeclared diagnostic outputs','candidate_lineage':{'previous_bundle':None,'optimizer_resume':frozen['resume'],'populated_adam_states':populated,'optimizer_scope':'actual new joint core/reader/prefix only; frozen LM excluded','training_binding':resume['binding']},'owner_config_original':original_config}
    b['version']=version(b)
    for p in [*components.values(),*evidence.values(),*sources]:verify_pin(p)
    save_new(out/'bundle.json',b);print(json.dumps({'bundle':str(out/'bundle.json'),'version':b['version'],'models_loaded':False,'training_steps':0}));return b

def verify(path):
    b=read(path)
    if b.get('schema')!=SCHEMA or b.get('version')!=version(b) or b.get('factory')!=FACTORY:raise Unavailable('ordered bundle identity/schema mismatch')
    if b['execution']!={'policy':'fixed','cap':4,'learned_stop_qualified':False}:raise Unavailable('cannot inherit learned stop')
    for p in [*b['assets'].values(),*b['sources'],*b['lm_files']]:verify_pin(p)
    if b['config']['order_contract']!=ORDER or b['config']['stop_factory_sha256']==OLD_STOP:raise Unavailable('wrong order/executor')
    if b['config']['stop_factory_sha256']!=NATIVE_STOP_SHA or b['config'].get('ordered_core_sha256')!=ORDERED_CORE_SHA:raise Unavailable('native boundary pin differs')
    for k in ('parent','reader','adapter'):
        if b['config'][k+'_path']!=b['assets'][k]['path'] or b['config'][k+'_sha256']!=b['assets'][k]['sha256']:raise Unavailable('runtime tuple differs from frozen assets')
    return b

def load(path,device='cuda'):
    b=verify(path);sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
    name,call=FACTORY.split(':');module=importlib.import_module(name)
    if sha(module.__file__)!=b['config']['runtime_factory_sha256']:raise Unavailable('loaded runtime version differs')
    config=dict(b['config'],device=device);actual=getattr(module,call)(config);verify(path)
    return b,actual
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--out',required=True);a=p.parse_args();freeze(a.request,a.out)
