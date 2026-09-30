#!/usr/bin/env python3
"""Known LM Studio root only: file stat and bounded local JSON model metadata."""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import time

ROOT=None
SETTINGS=Path('C:/Users/benja/.lmstudio/settings.json')
SETTINGS_SHA='1e37e73877413d62998d2be2ff56af5d07bedc49ebb8fcacc9472f73b35c44bf'
SETTINGS_SIZE=3476
START=time.monotonic();DEADLINE=START+25;MAX_ENTRIES=10000
WEIGHTS={'.gguf','.safetensors'}
METADATA={'model.json','config.json','manifest.json','model-info.json','metadata.json'}
COUNTS=collections.Counter()


def protected(text):
    name=text.casefold();reasons=[]
    if 'qwen' in name:reasons.append('possible Ben Qwen27B/QwenNextFlash alias; all Qwen matches protected until exact resolution')
    if 'lfm' in name or 'premonition' in name or 'learner' in name:reasons.append('possible active Premonition LFM/reader/core; protected')
    return reasons


def main():
    global ROOT
    if platform.system()!='Windows' or sys.version_info[:3]!=(3,10,9):raise ValueError('verified nativePC3.10.9 required')
    if SETTINGS.stat().st_size!=SETTINGS_SIZE:raise ValueError('actual pinnedsettings size differs')
    data=SETTINGS.read_bytes()
    if hashlib.sha256(data).hexdigest()!=SETTINGS_SHA:raise ValueError('actual pinnedsettings bytes differ')
    settings=json.loads(data);folder=settings['downloadsFolder']
    if not isinstance(folder,str) or not folder:raise ValueError('actual downloadsFolder string required')
    ROOT=Path(folder)
    if not ROOT.is_absolute() or len(ROOT.parts)<2 or ROOT.name.casefold() in ('benja','users','desktop','documents','pictures','videos'):
        raise ValueError('specific configuredmodel folder required; broad/personalroot refused')
    print(json.dumps({'schema':'sol.cloud.LMStudio.downloadsFolder-start.v5','settings_path':str(SETTINGS),'settings_sha256':SETTINGS_SHA,'only_setting_key_read_to_output':'downloadsFolder','root':str(ROOT),'root_exists':ROOT.is_dir(),'scope':'known LM Studio model root only','tensor_content_bytes_read':0}),flush=True)
    stack=[(ROOT,0)];files=[];metadata=[];dirs=collections.Counter();incomplete=False
    while stack and time.monotonic()<DEADLINE and COUNTS['entries']<MAX_ENTRIES:
        current,depth=stack.pop()
        try:
            with os.scandir(current) as stream:
                for entry in stream:
                    if time.monotonic()>=DEADLINE or COUNTS['entries']>=MAX_ENTRIES:incomplete=True;break
                    COUNTS['entries']+=1;path=Path(entry.path)
                    if any(word in str(path).casefold() for word in ('uncle-questions','readpanel320','dev100','stop88','sealed-panel','premonition','learner','lis300','sol-cloud','sol-translator','evidence','notebook','checkpoint','artifacts')):
                        COUNTS['protected_evaluation_paths_skipped']+=1;continue
                    try:
                        if entry.is_symlink():COUNTS['symlinks_not_followed']+=1;continue
                        if entry.is_dir(follow_symlinks=False):
                            if depth<5:stack.append((path,depth+1))
                            else:COUNTS['depth_skipped']+=1;incomplete=True
                            continue
                        if not entry.is_file(follow_symlinks=False):continue
                        if path.suffix.casefold() not in WEIGHTS and path.name.casefold() not in METADATA:continue
                        if path.name.casefold() in METADATA and not any(Path(record['path']).parent==current for record in files):
                            COUNTS['JSON_without_observed_sibling_model_not_read']+=1;continue
                        stat=os.stat(path,follow_symlinks=False)
                        relative=path.relative_to(ROOT)
                        if path.suffix.casefold() in WEIGHTS:
                            info={'path':str(path),'relative':relative.as_posix(),'bytes':stat.st_size,
                                  'mtime_utc':datetime.datetime.fromtimestamp(stat.st_mtime,datetime.timezone.utc).isoformat(),
                                  'mtime_is_last_use':False,'nlink':stat.st_nlink,'file_id':{'device':stat.st_dev,'inode':stat.st_ino} if stat.st_ino else None,
                                  'allocated_bytes':stat.st_blocks*512 if hasattr(stat,'st_blocks') else None,'format_from_extension':path.suffix.lower(),
                                  'protected_reasons':protected(relative.as_posix()),'last_use':'unknown','active_use':'unknown','last_copy':'unknown','backup_status':'unknown',
                                  'actual_reclaimable_bytes':None,'deletion_authorized':False,'quantization_verified':None,'weight_bytes_read':0}
                            match=re.search(r'(?:^|[-_.])(Q[2-8](?:_[0-9A-Z]+)*|IQ[1-4](?:_[0-9A-Z]+)*|F16|BF16|F32)(?:[-_.]|$)',path.name,re.I)
                            info['filename_quantization_label']=match.group(1) if match else None
                            info['filename_quantization_is_actual_header_verification']=False
                            files.append(info)
                            group='/'.join(relative.parts[:-1]) or '.';dirs[group]+=stat.st_size
                        elif path.name.casefold() in METADATA:
                            if stat.st_size>65536:COUNTS['overbound_JSON_metadata_skipped']+=1;continue
                            data=path.read_bytes();value=json.loads(data)
                            if not isinstance(value,dict):continue
                            selected={k:value.get(k) for k in ('name','model_name','model_type','architecture','quantization','quantization_level','quantization_config','version') if k in value}
                            # No template/system/tokenizer strings or credential fields are emitted.
                            for key,item in list(selected.items()):
                                if isinstance(item,dict):selected[key]={k:v for k,v in item.items() if k in ('quant_method','bits','group_size','load_in_4bit','load_in_8bit') and type(v) in (str,int,bool,type(None))}
                                elif type(item) not in (str,int,bool,type(None)):selected[key]='unsupported metadata value withheld'
                            metadata.append({'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'local_metadata':selected})
                    except (OSError,ValueError):COUNTS['denied_or_invalid_file_metadata']+=1
        except OSError:COUNTS['denied_or_unavailable_directories']+=1
    if stack:incomplete=True
    physical={};duplicates=[]
    for record in files:
        fid=record['file_id'];identity=(fid['device'],fid['inode']) if fid else ('path',record['path'])
        if identity in physical:duplicates.append({'first_path':physical[identity]['path'],'also_path':record['path'],'bytes':record['bytes'],'definition':'same observed device/inode, not a newly computed tensor hash'})
        else:physical[identity]=record
    report={'schema':'sol.cloud.LMStudio.downloadsFolder-model-inventory.v5','configuration':{'source_path':str(SETTINGS),'source_sha256':SETTINGS_SHA,'key':'downloadsFolder','configured_root':str(ROOT),'other_setting_values_withheld':True},'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runtime':sys.version,
            'root':str(ROOT),'root_exists':ROOT.is_dir(),'scan_wall_seconds':time.monotonic()-START,'limits':{'seconds':25,'entries':MAX_ENTRIES,'depth':5},
            'files_observed':len(files),'largest30_model_files':sorted(files,key=lambda row:row['bytes'],reverse=True)[:30],
            'top30_model_directories':[{'relative':group,'path':str(ROOT/group),'observed_apparent_bytes':size,'actual_reclaimable_bytes':None,'deletion_authorized':False} for group,size in dirs.most_common(30)],
            'local_model_metadata':metadata[:30],'observed_apparent_bytes':sum(r['bytes'] for r in files),'unique_observed_file_bytes':sum(r['bytes'] for r in physical.values()),
            'observed_hardlink_aliases':duplicates[:30],'hardlink_count_greater_than_observed_aliases':'outside links possible; no reclaimability promise',
            'protected_candidate_paths':[{'path':r['path'],'bytes':r['bytes'],'reasons':r['protected_reasons']} for r in files if r['protected_reasons']],
            'Qwen27B_alias_resolution':'not equated automatically; actual local filename/config evidence provided','QwenNextFlash_alias_resolution':'not equated automatically; allpossibleQwen protected',
            'counts':dict(COUNTS),'partial':incomplete or bool(COUNTS['denied_or_unavailable_directories']),'actual_reclaimable_bytes':None,
            'tensor_content_bytes_read':0,'GGUF_header_read':False,'filename_quantization_label_is_only_filename_metadata':True,
            'model_inference_calls':0,'GPU_calls':0,'optimizer_updates':0,'PC_files_written':0,'deletions':0,'deletion_authorized':False,
            'last_use_status':'unknown; mtime is not lastuse','scope':'only exactdownloadsFolder from pinnedactualsettings; modelweights stat+knownlocalmodelJSONmetadata, no otherroots/CLI/daemon/personal/cleanup scan'}
    print(json.dumps(report,sort_keys=True),flush=True)


if __name__=='__main__':main()
