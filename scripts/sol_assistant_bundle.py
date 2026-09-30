"""Immutable V6 bundle inventory, no model fallback or cache-policy redefinition."""
from __future__ import annotations
import ast
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
OWN=ROOT/'artifacts/sol-assistant-20260930'
SCHEMA='sol.assistant.bundle.v1'
FACTORY='scripts/sol_translator_runtime_fixed4_v6.py'
FACTORY_SHA='02c5dd5f81eeaf84378194f50101d6b87f5ef1bbf80e03935015f3182c3286b9'
STOP_SHA='845f955e798af2f1850804e27fa74af80c5d96751cd77d36effaa72c3e67d680'
SEAL_SHA='e63640f98afc04b122f80423a719891646be45f4c1a40ae8de4e244fcc2924a9'

class Unavailable(RuntimeError):pass

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def identity(value):return hashlib.sha256(canonical(value)).hexdigest()
def bundle_identity(value):return identity({k:v for k,v in value.items() if k!='version'})
def locate(path):
    p=Path(path);p=p if p.is_absolute() else ROOT/p
    if any(x in str(p).lower() for x in ('uncle-questions','readpanel','/blind','sealedquestions')):
        raise ValueError('forbidden source path')
    return p

def owned(path):
    p=locate(path).resolve()
    if not p.is_relative_to(OWN):raise ValueError('new assistant output prefix required')
    return p

def save_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:
        f.write(json.dumps(value,indent=2,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())

def pin(path):
    p=locate(path)
    if not p.is_file():raise Unavailable('asset absent: '+str(p))
    return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)

def verify_pin(record):
    p=locate(record['path'])
    if not p.is_file() or sha(p)!=record['sha256']:raise Unavailable('pinned bytes absent or changed: '+str(p))
    return p

def source_closure(entries):
    """Pin local Python imports recursively without importing/loading model weights."""
    pending=[locate(x).resolve() for x in entries];result={}
    while pending:
        p=pending.pop()
        if str(p) in result:continue
        result[str(p)]=pin(p)
        tree=ast.parse(p.read_text())
        names=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):names.extend(x.name for x in node.names)
            if isinstance(node,ast.ImportFrom) and node.module:
                names.append(node.module)
                names.extend(node.module+'.'+x.name for x in node.names)
        for name in names:
            for base in (ROOT,ROOT/'scripts'):
                target=base/(name.replace('.','/')+'.py')
                if target.is_file() and target.resolve().is_relative_to(ROOT):pending.append(target.resolve());break
    return list(result.values())

def validate_tuple(parent,reader,decoder,resume,ledger):
    """Reads actual tensors/metadata; cannot manufacture fitted checkpoint evidence."""
    import torch
    p,r,d,c=(torch.load(x,map_location='cpu',weights_only=True) for x in (parent,reader,decoder,resume))
    l=json.loads(Path(ledger).read_text());updates=l.get('updates',0)
    if type(updates) is not int or updates<=0:raise Unavailable('no actual optimizer updates')
    if c['ledger']['updates']!=updates or c['ledger']['raw_watermark_update']!=updates or l.get('raw_watermark_update')!=updates:
        raise Unavailable('durable update/watermark disagreement')
    if p['metadata']['ledger']['updates']!=updates:raise Unavailable('parent update differs')
    if r.get('reader_version')!='human-notebook-v2' or r.get('training_origin')!='verified-human-origin':raise Unavailable('wrong human reader origin/version')
    if p['metadata'].get('reader_version')!=r['reader_version'] or p['metadata'].get('human_manifest_sha256')!=r.get('human_manifest_sha256'):
        raise Unavailable('parent reader/corpus binding differs')
    if d.get('parent_sha256')!=sha(parent) or d.get('reader_sha256')!=sha(reader):raise Unavailable('decoder bound to another tuple')
    if d.get('training_origin')!='verified-human-origin-verbatim':raise Unavailable('unverified decoder adaptation origin')
    if d.get('human_manifest_sha256')!=r.get('human_manifest_sha256') or c['binding']['human_pairs_sha256']!=r.get('human_manifest_sha256'):
        raise Unavailable('corpus identity differs across tuple')
    states=c.get('optimizer',{}).get('state',{})
    populated=[v for v in states.values() if all(k in v for k in ('step','exp_avg','exp_avg_sq')) and float(v['step'])>0]
    if not populated:raise Unavailable('optimizer has no trained Adam moments')
    for ck_key,export in [('core',p['state_dict']),('reader',r['state_dict']),('adapter',d['adapter_state'])]:
        actual=c[ck_key]
        if set(actual)!=set(export) or any(not torch.equal(actual[k].cpu(),export[k].cpu()) for k in export):
            raise Unavailable('resume/export tensor mismatch: '+ck_key)
    return dict(seed=l['seed'],updates=updates,raw_watermark_update=updates,
                populated_adam_states=len(populated),human_manifest_sha256=r['human_manifest_sha256'],
                reader_version=r['reader_version'],sleep_updates=l.get('sleep_updates',0),training_binding=c['binding'])

def pack(request_path,out):
    req=json.loads(locate(request_path).read_text());out=owned(out)
    roles=('parent','reader','adapter','resume','ledger')
    pins={k:pin(req[k+'_path']) for k in roles}
    for k in ('training_seal','durable_receipt','lm_provenance'):pins[k]=pin(req[k+'_path'])
    if pins['training_seal']['sha256']!=SEAL_SHA:raise Unavailable('not the released V6 seal')
    sources=source_closure([FACTORY,Path(__file__),ROOT/'scripts/sol_assistant_runtime.py',ROOT/'scripts/sol_assistant_cli.py'])
    owner=json.loads(verify_pin(pins['training_seal']).read_text())
    owner_files=owner.get('files',{})
    driver='scripts/sol_translator_grounding_v6.py'
    if owner_files.get(driver)!=sha(ROOT/driver):raise Unavailable('training driver not in supplied owner seal')
    if sha(ROOT/FACTORY)!=FACTORY_SHA or owner_files.get(FACTORY)!=FACTORY_SHA:
        raise Unavailable('not the released fixed4 V6 factory')
    meta=validate_tuple(*(pins[k]['path'] for k in ('parent','reader','adapter','resume','ledger')))
    receipt=json.loads(verify_pin(pins['durable_receipt']).read_text())
    if (receipt.get('status')!='DURABLE-TRAIN-WEIGHTS' or receipt.get('seed')!=meta['seed']
            or receipt.get('updates')!=meta['updates'] or receipt.get('resume_sha256')!=pins['resume']['sha256']):
        raise Unavailable('stdout DURABLE receipt does not match snapshot')
    if meta['training_binding']['driver_sha256']!=sha(ROOT/driver):raise Unavailable('resume driver identity differs')
    lm=locate(req['lm_path']);prov=json.loads(verify_pin(pins['lm_provenance']).read_text())
    inventory={name:dict(path=str(lm/name),sha256=h) for name,h in prov['files'].items()}
    for record in inventory.values():verify_pin(record)
    # Cache topology/authorization remains with sealed owner's loader, not this code.
    out.mkdir(parents=True,exist_ok=False)
    copied={}
    for k in (*roles,'lm_provenance','training_seal','durable_receipt'):
        src=verify_pin(pins[k]);dest=out/(k+src.suffix)
        if src.suffix=='.pt':
            # Owner atomic_save replaces the inode. Never duplicate large Adam bytes.
            # Cross-volume callers must supply a local immutable snapshot first.
            os.link(src,dest)
        else:
            with src.open('rb') as a,dest.open('xb') as b:shutil.copyfileobj(a,b)
        if sha(dest)!=pins[k]['sha256']:raise Unavailable('source changed while snapshotting '+k)
        copied[k]=pin(dest)
    for record in pins.values():verify_pin(record)
    archived=[]
    for record in sources:
        src=verify_pin(record);dest=out/'source'/src.relative_to(ROOT)
        dest.parent.mkdir(parents=True,exist_ok=True)
        with src.open('rb') as a,dest.open('xb') as f:shutil.copyfileobj(a,f)
        if sha(dest)!=record['sha256']:raise Unavailable('source changed during archive')
        archived.append(pin(dest))
    bundle=dict(schema=SCHEMA,
        assets=copied,sources=sources,source_archive=archived,lm_inventory=inventory,lm_path=str(lm),checkpoint=meta,
        factory=dict(module='sol_translator_runtime_fixed4_v6',callable='load_d256_notebook_factories',sha256=sha(ROOT/FACTORY)),
        execution=dict(policy='fixed',cap=4,max_tokens=64),
        readiness=dict(accepted_stop_ready=False,sleep_allowed=False,owner_verifier=None),
        claims=dict(grammar='NOT SHOWN',semantic_English='NOT SHOWN',sleep='NOT SHOWN',benchmark='NOT SHOWN'),
        label='diagnostic actual fitted tuple; fixed4 is not learned-stop readiness')
    bundle['version']=bundle_identity(bundle)
    save_new(out/'bundle.json',bundle);return out/'bundle.json'

def verify_bundle(path):
    b=json.loads(locate(path).read_text())
    if b.get('schema')!=SCHEMA:raise Unavailable('unsupported bundle schema')
    if b.get('version')!=bundle_identity(b):raise Unavailable('bundle identity differs')
    if b.get('factory')!={'module':'sol_translator_runtime_fixed4_v6','callable':'load_d256_notebook_factories','sha256':FACTORY_SHA}:
        raise Unavailable('unreleased factory')
    if b.get('execution')!={'policy':'fixed','cap':4,'max_tokens':64}:raise Unavailable('only owner fixed4 diagnostic execution implemented')
    for record in [*b['assets'].values(),*b['sources'],*b['source_archive'],*b['lm_inventory'].values()]:verify_pin(record)
    required=source_closure([FACTORY,Path(__file__),ROOT/'scripts/sol_assistant_runtime.py',ROOT/'scripts/sol_assistant_cli.py'])
    if {r['path']:r['sha256'] for r in required}!={r['path']:r['sha256'] for r in b['sources']}:
        raise Unavailable('source closure incomplete or changed')
    if sha(ROOT/'scripts/sol_stop_api4.py')!=STOP_SHA:raise Unavailable('stop factory changed')
    if b['assets']['training_seal']['sha256']!=SEAL_SHA:raise Unavailable('unreleased training seal')
    if b['readiness']!={'accepted_stop_ready':False,'sleep_allowed':False,'owner_verifier':None}:
        raise Unavailable('fixed4 readiness cannot be promoted')
    if b['checkpoint']['updates']<=0:raise Unavailable('no fitted tuple')
    return b

def load(path,device='cpu'):
    b=verify_bundle(path)
    sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
    module=importlib.import_module(b['factory']['module'])
    if sha(module.__file__)!=b['factory']['sha256']:raise Unavailable('loaded factory version differs')
    a=b['assets']
    config=dict(updates=b['checkpoint']['updates'],device=device,reader_version='human-notebook-v2',runtime_factory_sha256=b['factory']['sha256'],
                stop_factory_sha256=sha(ROOT/'scripts/sol_stop_api4.py'),lm_path=b['lm_path'],lm_provenance=a['lm_provenance']['path'])
    for k in ('parent','reader','adapter'):config[k+'_path']=a[k]['path'];config[k+'_sha256']=a[k]['sha256']
    factory=getattr(module,b['factory']['callable'])(config)
    verify_bundle(path) # Detect source/asset changes during loading, not old smoke inference.
    return b,factory

def require_sleep_readiness(bundle):
    # Current owner schema always leaves accepted_stop_ready=False pending recount.
    # Do not invent a promotion verifier or accept a caller-written boolean.
    raise Unavailable('sleep blocked: owner independently accepted exact human tuple verifier/receipt not supplied; fixed4 never qualifies')
