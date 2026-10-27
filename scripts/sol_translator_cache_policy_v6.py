#!/usr/bin/env python3
"""Reviewable exact shared-blob exception. Exact target+content SHA only; no broad shared-cache scope.
No broad hub-cache allow; no copying or mutation. Verification is streaming.
"""
import hashlib,json
from pathlib import Path,PurePosixPath
MODEL='LiquidAI/LFM2.5-1.2B-Instruct'
REVISION='0f604ada3f766f9f257460c4c9f0b5d6f69d431b'
FILENAME='model.safetensors'
EXACT_LOGICAL='C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b/model.safetensors'
EXACT_BLOB='C:/Users/benja/.cache/huggingface/hub/blobs/02/0223e4373a31a728f6e306f68fc58ad4b41e86054badb87928b7a491437a8b99'
EXPECTED_SHA256='1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a'


def exact_target_guard(meta,name,logical,resolved,expected):
    """Pure exact-target guard. Job release remains integrator/user controlled."""
    return (meta['model_id']==MODEL and meta['revision']==REVISION and name==FILENAME
            and logical.absolute()==Path(EXACT_LOGICAL).absolute()
            and resolved==Path(EXACT_BLOB) and expected==EXPECTED_SHA256)


def streamed_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def verify_manifest(model,provenance):
    p=Path(model);meta=json.loads(Path(provenance).read_text());repo='models--'+meta['model_id'].replace('/','--')
    if p.name!=meta['revision'] or p.parent.name!='snapshots' or p.parent.parent.name!=repo:raise ValueError('model/revision cache topology mismatch')
    snapshot=p.resolve();blobs=(p.parent.parent/'blobs').resolve();records=[]
    for name,expected in sorted(meta['files'].items()):
        pure=PurePosixPath(name.replace('\\','/'))
        if pure.is_absolute() or '..' in pure.parts or ':' in name:raise ValueError('unsafe manifest path')
        logical=p.joinpath(*pure.parts);resolved=logical.resolve()
        local=resolved.is_relative_to(snapshot) or resolved.is_relative_to(blobs)
        exact=exact_target_guard(meta,name,logical,resolved,expected)
        if not local and not exact:raise PermissionError('outside exact model snapshot/repository/shared-object guard: '+name)
        if exact and Path(EXACT_BLOB).resolve()!=Path(EXACT_BLOB):raise ValueError('exact shared blob path itself redirects; refuse before byte read')
        actual=streamed_sha(logical)
        record={'name':name,'logical_path':str(logical),'resolved_path':str(resolved),'expected_sha256':expected,'actual_sha256':actual,'hash_matches':actual==expected,'same_repo_or_snapshot':local,'exact_human_authorized_exception':exact}
        records.append(record)
        if actual!=expected:raise ValueError('frozen model byte digest mismatch '+json.dumps(record))
    return {'records':records,'all_hashes_match':True,'policy':'same snapshot/repo OR exact single observed model path+SHA only','no_download_or_copy':True}
