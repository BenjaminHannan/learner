"""Lightweight guide loading/acknowledgment gate; no process or model execution.

CURRENT.json is a versioned repository file, not a caller-selected guide. An
acknowledgment proves matching bytes and declared action, not comprehension.
"""
import datetime
import hashlib
import json
from pathlib import Path

CURRENT_REL='docs/premonition-recovery/CURRENT.json'
START_RULE='execution.preflight'
FAILURE_RULE='failure.preserve'
RECEIPT_RULE='windows.atomic-receipts'
STORAGE_RULE='storage.atomic-renames'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def load_current(root):
    root=Path(root).resolve();current=root/CURRENT_REL
    manifest_raw=current.read_bytes();manifest=json.loads(manifest_raw)
    version=manifest['version'];relative=manifest['path'];expected=manifest['sha256']
    if not isinstance(version,str) or not version.strip():raise ValueError('guide version missing')
    guide=(root/relative).resolve()
    if not guide.is_relative_to((root/'docs/premonition-recovery').resolve()):raise ValueError('guide outside versioned guide directory')
    raw=guide.read_bytes()
    if sha(raw)!=expected:raise ValueError('current guide bytes do not match manifest')
    text=raw.decode('utf8');rules=manifest['rules']
    for key in (START_RULE,FAILURE_RULE,RECEIPT_RULE,STORAGE_RULE):
        excerpt=rules.get(key)
        if not isinstance(excerpt,str) or not excerpt.strip() or excerpt not in text:raise ValueError('guide rule missing or unsupported: '+key)
    return {'version':version,'path':relative,'sha256':expected,'current_manifest_sha256':sha(manifest_raw),'rules':rules,'loaded_bytes':len(raw)}


def require_start(root,request):
    current=load_current(root);ack=request.get('guide_acknowledgment')
    if not isinstance(ack,dict):raise ValueError('current guide acknowledgment required before launch')
    for key in ('version','sha256','current_manifest_sha256'):
        if ack.get(key)!=current[key]:raise ValueError('stale or mismatched guide acknowledgment: '+key)
    if ack.get('phase')!='task_start' or ack.get('batch_id')!=request['batch_id']:raise ValueError('guide acknowledgment task binding mismatch')
    if ack.get('loaded') is not True:raise ValueError('guide loading not acknowledged')
    if not isinstance(ack.get('actor'),str) or not ack['actor'].strip():raise ValueError('guide acknowledgment actor missing')
    rules=ack.get('applicable_rules')
    if not isinstance(rules,list) or START_RULE not in rules or any(k not in current['rules'] for k in rules):raise ValueError('applicable guide rules missing')
    if not isinstance(ack.get('action'),str) or not ack['action'].strip():raise ValueError('guide acknowledgment action missing')
    return {**ack,'schema':'premonition.guide-consultation.v1','guide_path':current['path'],'loaded_bytes':current['loaded_bytes'],'acknowledgment_validated':True,'comprehension_verified':False,'consulted_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}


def consult_failure(root,batch_id,error,action,*,incident_id=None):
    current=load_current(root)
    message=str(error)
    if isinstance(error,FileNotFoundError) and '.tmp' in message:rule=STORAGE_RULE
    elif getattr(error,'winerror',None) in (5,32,33):rule=RECEIPT_RULE
    else:rule=FAILURE_RULE
    if not isinstance(action,str) or not action.strip():raise ValueError('failure consultation action missing')
    return {'schema':'premonition.guide-consultation.v1','phase':'failure','batch_id':batch_id,'incident_id':incident_id,'guide_path':current['path'],'version':current['version'],'sha256':current['sha256'],'current_manifest_sha256':current['current_manifest_sha256'],'loaded_bytes':current['loaded_bytes'],'applicable_rules':[rule,FAILURE_RULE] if rule!=FAILURE_RULE else [rule],'rule_excerpt':current['rules'][rule],'action':action,'error_type':type(error).__name__,'error':message,'comprehension_verified':False,'consulted_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
