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
import subprocess
import time

ROOT=Path('C:/Users/benja/.lmstudio/models')
CONFIG_BASES=[Path('C:/Users/benja/.lmstudio'),Path('C:/Users/benja/.lmstudio/.internal'),Path('C:/Users/benja/AppData/Roaming/LM Studio')]
CONFIGURATION=None
START=time.monotonic();DEADLINE=START+25;MAX_ENTRIES=10000
WEIGHTS={'.gguf','.ggml','.safetensors','.bin'}
METADATA={'model.json','config.json','manifest.json','model-info.json','metadata.json'}
COUNTS=collections.Counter()


def protected(text):
    name=text.casefold();reasons=[]
    if 'qwen' in name:reasons.append('possible Ben Qwen27B/QwenNextFlash alias; all Qwen matches protected until exact resolution')
    if 'lfm' in name or 'premonition' in name or 'learner' in name:reasons.append('possible active Premonition LFM/reader/core; protected')
    return reasons


def configured_root():
    candidates=[];records=[];listed=[]
    def visit(value,source,depth=0):
        if depth>5:return
        if isinstance(value,dict):
            for key,item in value.items():
                normalized=re.sub('[^a-z]','',str(key).casefold())
                if any(word in normalized for word in ('apikey','token','secret','password','cookie','auth')):continue
                if ('model' in normalized and any(word in normalized for word in ('dir','path','folder'))) and isinstance(item,str):
                    path=Path(item)
                    if path.is_absolute() and str(path).replace('\\','/').strip('/') not in ('C:','D:','C:/Users/benja') and path.name.casefold() not in ('desktop','documents','downloads','pictures','videos'):
                        records.append({'source':source,'key':key,'configured_path':str(path),'exists':path.is_dir()})
                        if path.is_dir():candidates.append(path)
                elif isinstance(item,(dict,list)):visit(item,source,depth+1)
        elif isinstance(value,list):
            for item in value[:100]:visit(item,source,depth+1)
    for base in CONFIG_BASES:
        if time.monotonic()>=DEADLINE:break
        try:
            for entry in list(os.scandir(base))[:100]:
                if not entry.is_file(follow_symlinks=False):continue
                path=Path(entry.path);name=path.name.casefold()
                if not re.fullmatch(r'(?:app[-_]preferences|user[-_]preferences|settings|user[-_]settings|preferences|config|model[-_]directories|models[-_]directory)\.json',name):continue
                if path.stat().st_size>262144:continue
                data=path.read_bytes();value=json.loads(data)
                listed.append({'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'read_scope':'model-directory-key allowlist only; credentials withheld'})
                visit(value,str(path))
        except (OSError,ValueError):COUNTS['configuration_unavailable_or_invalid']+=1
    # Use existing CLI only with already-running LM Studio/daemon; never startup.
    cli_info={'status':'not invoked','no_daemon_start_requested':True}
    try:
        command="Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('LM Studio.exe','llmster.exe','lms.exe')} | Select-Object ProcessId,Name | ConvertTo-Json -Compress"
        completed=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,timeout=4,check=True)
        processes=json.loads(completed.stdout or '[]');processes=[processes] if isinstance(processes,dict) else processes
        cli=shutil.which('lms')
        if not cli:
            exact=Path('C:/Users/benja/.lmstudio/bin/lms.exe');cli=str(exact) if exact.is_file() else None
        cli_info.update(existing_LM_processes=processes,existing_cli=cli)
        if cli and processes:
            run=subprocess.run([cli,'ls','--json','--detailed'],capture_output=True,text=True,timeout=5)
            cli_info.update(status='existing read-only CLI queried',returncode=run.returncode)
            if run.returncode==0 and len(run.stdout.encode('utf8'))<=524288:
                data=json.loads(run.stdout);rows=data if isinstance(data,list) else data.get('models',[])
                cli_info['catalog']=[{k:row.get(k) for k in ('name','modelKey','path','modelPath','sizeBytes','size','format','architecture','params','quantization')} for row in rows[:100] if isinstance(row,dict)]
                # A catalog model root is authoritative only when explicitly named.
                visit(data,'existing lms ls --json --detailed')
    except (OSError,ValueError,subprocess.SubprocessError):cli_info['status']='existing CLI/status unavailable; no startup attempted'
    unique=list(dict.fromkeys(candidates))
    return {'configuration_files':listed,'configured_directory_records':records,'existing_cli_metadata':cli_info,'actual_existing_configured_roots':[str(path) for path in unique],'selected_scan_root':str(unique[0]) if unique else str(ROOT),'configured_root_resolved':bool(unique),'fallback_default_is_not_proof_of_configured_root':not bool(unique)},unique[0] if unique else ROOT


def main():
    global ROOT,CONFIGURATION
    if platform.system()!='Windows' or sys.version_info[:3]!=(3,10,9):raise ValueError('verified nativePC3.10.9 required')
    CONFIGURATION,ROOT=configured_root()
    print(json.dumps({'schema':'sol.cloud.LMStudio.inventory-start.v3','configuration':CONFIGURATION,'root':str(ROOT),'root_exists':ROOT.is_dir(),'scope':'known LM Studio model root only','tensor_content_bytes_read':0}),flush=True)
    stack=[(ROOT,0)];files=[];metadata=[];dirs=collections.Counter();incomplete=False
    while stack and time.monotonic()<DEADLINE and COUNTS['entries']<MAX_ENTRIES:
        current,depth=stack.pop()
        try:
            with os.scandir(current) as stream:
                for entry in stream:
                    if time.monotonic()>=DEADLINE or COUNTS['entries']>=MAX_ENTRIES:incomplete=True;break
                    COUNTS['entries']+=1;path=Path(entry.path)
                    if any(word in str(path).casefold() for word in ('uncle-questions','readpanel320','dev100','stop88','sealed-panel')):
                        COUNTS['protected_evaluation_paths_skipped']+=1;continue
                    try:
                        if entry.is_symlink():COUNTS['symlinks_not_followed']+=1;continue
                        if entry.is_dir(follow_symlinks=False):
                            if depth<5:stack.append((path,depth+1))
                            else:COUNTS['depth_skipped']+=1;incomplete=True
                            continue
                        if not entry.is_file(follow_symlinks=False):continue
                        stat=entry.stat(follow_symlinks=False)
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
    report={'schema':'sol.cloud.LMStudio.model-inventory.v3','configuration':CONFIGURATION,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runtime':sys.version,
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
            'last_use_status':'unknown; mtime is not lastuse','scope':'known model root only; no broader disk, personal or cleanup scan'}
    print(json.dumps(report,sort_keys=True),flush=True)


if __name__=='__main__':main()
