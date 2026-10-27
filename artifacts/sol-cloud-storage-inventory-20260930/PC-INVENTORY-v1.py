#!/usr/bin/env python3
"""Bounded read-only local storage/model metadata. Never read tensor contents."""
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
import urllib.request

USER=Path('C:/Users/benja')
OLLAMA=USER/'.ollama/models'
HF=USER/'.cache/huggingface/hub'
ROOTS=[('Temp',USER/'AppData/Local/Temp'),('pip-package-cache',USER/'AppData/Local/pip/Cache'),('Downloads-installers',USER/'Downloads')]
PROTECTED_PARTS=('learner','lis300','premonition','beautiful-model','sol-cloud','sol-translator','sol-assistant','artifacts','checkpoint','evidence','notebook','uncle-questions','readpanel320','dev100','stop88','sealed-panel','huggingface','torchinductor','torch_extensions')
PROTECTED_EXTS=frozenset(('.pt','.pth','.ckpt','.safetensors','.onnx','.gguf','.ggml','.npy','.npz','.sqlite','.sqlite3','.db','.json','.jsonl','.csv','.md','.html','.log','.ipynb','.py','.txt','.pdf','.docx','.xlsx','.png','.jpg','.jpeg','.gif','.webp','.mp3','.mp4','.wav'))
START=time.monotonic();DEADLINE=START+45;MAX_ENTRIES=50000
COUNTS=collections.Counter();COVERAGE=[]


def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def bounded():
    if time.monotonic()>=DEADLINE or COUNTS['entries']>=MAX_ENTRIES:
        COUNTS['bound_reached']+=1;return False
    return True


def entries(path):
    if not bounded():return []
    try:
        result=[]
        with os.scandir(path) as stream:
            for entry in stream:
                if not bounded():break
                COUNTS['entries']+=1;result.append(entry)
        return result
    except (PermissionError,OSError):COUNTS['denied_or_unavailable_directories']+=1;return []


def stat_info(path,follow=False):
    try:
        st=os.stat(path,follow_symlinks=follow)
        return {'path':str(path),'bytes':st.st_size,'mtime_utc':datetime.datetime.fromtimestamp(st.st_mtime,datetime.timezone.utc).isoformat(),
                'mtime_is_last_use':False,'nlink':getattr(st,'st_nlink',None),'file_id':{'device':st.st_dev,'inode':st.st_ino} if st.st_ino else None,
                'allocated_bytes':st.st_blocks*512 if hasattr(st,'st_blocks') else None,'active_use':'unknown','last_copy':'unknown','backup_status':'unknown','recreatable':'unknown'}
    except (PermissionError,OSError):COUNTS['denied_or_unavailable_stats']+=1;return None


def blocked_cleanup(path):
    text=str(path).replace('\\','/').lower()
    return any(part in text for part in PROTECTED_PARTS) or path.suffix.casefold() in PROTECTED_EXTS


def small_json(path,cap=262144):
    # This is called ONLY for model manifests/config/index metadata filenames.
    if not bounded():return None
    try:
        if path.is_symlink() and not path.resolve().is_relative_to(HF.resolve()):return None
        st=path.stat()
        if st.st_size>cap:COUNTS['overbound_metadata_files']+=1;return None
        data=path.read_bytes();value=json.loads(data)
        if not isinstance(value,dict):raise ValueError('metadata object required')
        return value,hashlib.sha256(data).hexdigest(),len(data)
    except (ValueError,PermissionError,OSError):COUNTS['unavailable_or_invalid_model_metadata']+=1;return None


def catalog():
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=2) as stream:data=stream.read(524289)
        if len(data)>524288:raise ValueError('catalog cap')
        raw=json.loads(data);models=raw.get('models',[])
        if not isinstance(models,list):raise ValueError('catalog list')
        selected=[]
        for row in models[:200]:
            if not isinstance(row,dict):continue
            details=row.get('details') or {}
            selected.append({k:row.get(k) for k in ('name','model','digest','size','modified_at')})
            selected[-1]['details']={k:details.get(k) for k in ('format','family','families','parameter_size','quantization_level')}
            selected[-1]['protected_reasons']=protection(str(row.get('name','')),details)
        return {'status':'available','endpoint':'localhost Ollama /api/tags','source_sha256':hashlib.sha256(data).hexdigest(),'models':selected,'total_catalog_models':len(models),'catalog_truncated':len(models)>200,'modified_at_is_last_use':False,'model_inference_calls':0}
    except Exception as error:return {'status':'unavailable','error_type':type(error).__name__,'models':[],'model_inference_calls':0}


def cleanup_inventory():
    files=[];directories=[];totals={}
    for category,root in ROOTS:
        total=0;observed=0;stack=[root];coverage={'category':category,'root':str(root),'started':bounded(),'recursive':category!='Downloads-installers','incomplete':False}
        while stack and bounded():
            current=stack.pop();direct=0
            for entry in entries(current):
                path=Path(entry.path)
                if blocked_cleanup(path):COUNTS['protected_cleanup_entries_skipped']+=1;continue
                try:
                    if entry.is_symlink():COUNTS['symlinks_not_followed']+=1;continue
                    if entry.is_dir(follow_symlinks=False):
                        if category!='Downloads-installers':stack.append(path)
                        continue
                    if not entry.is_file(follow_symlinks=False):continue
                except OSError:COUNTS['denied_or_unavailable_types']+=1;continue
                if category=='Downloads-installers':
                    recognized=path.suffix.casefold() in ('.msi','.msix','.msp','.appx') or (path.suffix.casefold()=='.exe' and re.search(r'setup|install|installer',path.name,re.I))
                    if not recognized:COUNTS['noninstaller_Downloads_entries_skipped']+=1;continue
                info=stat_info(path)
                if info is None:continue
                total+=info['bytes'];direct+=info['bytes'];observed+=1
                info.update(category=category,classification='recognized installer filename only' if category=='Downloads-installers' else 'package cache location; content unverified' if category=='pip-package-cache' else 'Temp location; filename/content purpose unknown',authorized_for_deletion=False,reclaimable_bytes=None)
                files.append(info)
                if len(files)>60:files=sorted(files,key=lambda x:x['bytes'],reverse=True)[:30]
            if direct:directories.append({'path':str(current),'direct_observed_file_bytes':direct,'category':category,'recursive_size':False,'reclaimable_bytes':None,'active_use':'unknown','last_copy':'unknown','authorized_for_deletion':False})
            if len(directories)>60:directories=sorted(directories,key=lambda x:x['direct_observed_file_bytes'],reverse=True)[:30]
        coverage['incomplete']=bool(stack) or not bounded();COVERAGE.append(coverage)
        totals[category]={'observed_logical_bytes':total,'observed_candidate_files':observed,'complete':not coverage['incomplete'],'reclaimable_bytes':None}
    return {'category_totals':totals,'top30_files':sorted(files,key=lambda x:x['bytes'],reverse=True)[:30],'top30_directories':sorted(directories,key=lambda x:x['direct_observed_file_bytes'],reverse=True)[:30],'recycle_bin':{'status':'not inspected','bytes':None,'reason':'optional personal-content root avoided'},'candidate_metadata_is_deletion_authorization':False}


def protection(name,details=None):
    text=name.casefold();details=details or {};parameter=str(details.get('parameter_size','')).casefold().replace(' ','')
    reasons=[]
    if 'liquidai' in text and 'lfm' in text:reasons.append('active Premonition LFM family protected')
    if 'qwen' in text:
        # Ben aliases may not map1:1 to a catalog name: protect all possibilities.
        reasons.append('possible Qwen27B/QwenNextFlash binding; conservatively protected pending exact alias resolution')
        if parameter in ('27b','27.0b'):reasons.append('catalog explicitly reports Qwen27B parameter size')
    return reasons


def ollama_inventory(cat):
    manifests=[];stack=[OLLAMA/'manifests'];complete=True
    catalog_by_name={str(r.get('name')):r for r in cat['models']}
    while stack and bounded():
        directory=stack.pop()
        for entry in entries(directory):
            path=Path(entry.path)
            try:
                if entry.is_symlink():COUNTS['model_symlinks_not_followed']+=1;continue
                if entry.is_dir(follow_symlinks=False):stack.append(path);continue
                if not entry.is_file(follow_symlinks=False):continue
            except OSError:continue
            metadata=small_json(path,1048576)
            if metadata is None:complete=False;continue
            value,digest,size=metadata;parts=path.relative_to(OLLAMA/'manifests').parts
            name='/'.join(parts[1:-1])+':'+parts[-1] if len(parts)>2 else path.name
            short=name.removeprefix('library/');details=catalog_by_name.get(short,{}).get('details',{})
            refs=[]
            for ref in [value.get('config',{}),*value.get('layers',[])]:
                dig=ref.get('digest','') if isinstance(ref,dict) else ''
                if re.fullmatch('sha256:[0-9a-f]{64}',dig):refs.append(dig)
            manifests.append({'name':name,'catalog_name':short,'manifest_path':str(path),'manifest_sha256':digest,'manifest_bytes':size,'refs':sorted(set(refs)),'catalog_details':details,'quantization':details.get('quantization_level'),'quantization_source':'local catalog' if details.get('quantization_level') else 'unknown','protected_reasons':protection(name,details)})
    if stack or not bounded():complete=False
    refcounts=collections.Counter(ref for model in manifests for ref in model['refs']);stats={}
    for ref in refcounts:
        if not bounded():complete=False;break
        stats[ref]=stat_info(OLLAMA/'blobs'/ref.replace(':','-'))
    for model in manifests:
        leaves=[dict(stats[ref],manifest_digest=ref,manifest_refcount=refcounts[ref]) for ref in model['refs'] if stats.get(ref)]
        model['blob_metadata']=leaves;model['observed_apparent_bytes']=sum(r['bytes'] for r in leaves)
        exclusive=[r for r in leaves if r['manifest_refcount']==1 and r['nlink']==1]
        model['exclusive_logical_bytes_within_observed_manifests']=sum(r['bytes'] for r in exclusive) if complete else None
        model['actual_reclaimable_bytes']=None;model['reclaimability_status']='unknown; logical exclusive count is no deletion promise; active/last-copy and allocated bytes unverified'
        model['active_use']='unknown';model['last_use']='unknown';model['authorized_for_deletion']=False
    COUNTS['Ollama_manifests']=len(manifests);COVERAGE.append({'root':str(OLLAMA),'category':'Ollama model manifests+referenced blob stat only','complete':complete,'weight_bytes_read':0})
    return manifests,complete


def hf_inventory():
    models=[];complete=True
    for repository in entries(HF):
        if not bounded():complete=False;break
        if not repository.name.startswith('models--'):continue
        try:
            if not repository.is_dir(follow_symlinks=False):continue
        except OSError:continue
        repo=Path(repository.path);name=repository.name[len('models--'):].replace('--','/');snapshots=[]
        for snapshot in entries(repo/'snapshots'):
            try:
                if not snapshot.is_dir(follow_symlinks=False):continue
            except OSError:continue
            path=Path(snapshot.path);leaves=[];stack=[path];config={};config_identity=None
            parsed=small_json(path/'config.json')
            if parsed:
                value,digest,size=parsed;config={k:value.get(k) for k in ('model_type','architectures','torch_dtype','dtype','quantization_config')}
                config_identity={'path':str(path/'config.json'),'sha256':digest,'bytes':size}
            while stack and bounded():
                directory=stack.pop()
                for entry in entries(directory):
                    item=Path(entry.path)
                    try:
                        if entry.is_dir(follow_symlinks=False):stack.append(item);continue
                        target=item.resolve()
                        if not target.is_relative_to(HF.resolve()):COUNTS['outside_HF_links_skipped']+=1;continue
                        info=stat_info(target)
                        if info:leaves.append(dict(info,snapshot_path=str(item),snapshot_symlink=entry.is_symlink(),blob_basename=target.name))
                    except OSError:COUNTS['unavailable_HF_snapshot_paths']+=1
            if stack or not bounded():complete=False
            by_identity={}
            for info in leaves:
                fid=info['file_id'];identity=(fid['device'],fid['inode']) if fid else ('path',info['path'])
                by_identity[identity]=info
            snapshots.append({'revision':snapshot.name,'path':str(path),'config_identity':config_identity,'config_declared':config,
                              'observed_apparent_snapshot_bytes':sum(x['bytes'] for x in leaves),'unique_observed_file_bytes':sum(x['bytes'] for x in by_identity.values()),'files':list(by_identity.values())})
        files={}
        for snapshot in snapshots:
            for info in snapshot['files']:
                fid=info['file_id'];identity=(fid['device'],fid['inode']) if fid else ('path',info['path']);files[identity]=info
        models.append({'name':name,'root':str(repo),'snapshots':snapshots,'observed_apparent_bytes':sum(s['observed_apparent_snapshot_bytes'] for s in snapshots),
                       'unique_observed_file_bytes':sum(x['bytes'] for x in files.values()),'protected_reasons':protection(name),'actual_reclaimable_bytes':None,
                       'reclaimability_status':'unknown; shared blob/hardlink metadata does not authorize removal','last_use':'unknown','active_use':'unknown','authorized_for_deletion':False})
    if not bounded():complete=False
    COVERAGE.append({'root':str(HF),'category':'HF model repositories snapshot/config+file stat only','complete':complete,'weight_bytes_read':0})
    return models,complete


def main():
    if platform.system()!='Windows' or sys.version_info[:3]!=(3,10,9):raise ValueError('verified nativePC3.10.9 required')
    cat=catalog();print(json.dumps({'schema':'sol.cloud.storage.catalog-upfront.v1','observed_utc':now(),'catalog':cat,'no_inference':True}),flush=True)
    ollama,ollama_complete=ollama_inventory(cat);hf,hf_complete=hf_inventory();cleanup=cleanup_inventory()
    all_models=ollama+hf;largest=sorted(all_models,key=lambda row:row.get('observed_apparent_bytes',0),reverse=True)[:10]
    # Avoid unrestricted config output, model template/system text or huge catalogs.
    for model in largest:
        for snapshot in model.get('snapshots',[]):
            raw=snapshot['config_declared'].get('quantization_config')
            if isinstance(raw,dict):snapshot['config_declared']['quantization_config']={k:raw.get(k) for k in ('quant_method','bits','group_size','load_in_4bit','load_in_8bit','sym') if type(raw.get(k)) in (str,int,bool,float,type(None))}
            snapshot['files']=sorted(snapshot['files'],key=lambda x:x['bytes'],reverse=True)[:40]
    protected=[{'name':row.get('name'),'source':'local Ollama catalog','reasons':row['protected_reasons']} for row in cat['models'] if row.get('protected_reasons')]+[{'name':model['name'],'root':model.get('root'),'manifest_path':model.get('manifest_path'),'reasons':model['protected_reasons']} for model in all_models if model['protected_reasons']]
    report={'schema':'sol.cloud.storage-inventory.v1','completed_utc':now(),'runtime':sys.version,'C_free_bytes':shutil.disk_usage('C:/').free,
            'wall_seconds':time.monotonic()-START,'limits':{'scan_seconds':45,'entries':50000,'cleanup_top_files':30,'cleanup_top_dirs':30,'largest_models':10},
            'catalog':cat,'models_observed':len(all_models),'largest10_models':largest,'protected_candidate_bindings':protected,
            'Ben_alias_resolution':{'Qwen27B':'unresolved exact alias; every possible Qwen protected','QwenNextFlash':'unresolved exact alias; every possible Qwen protected'},
            'protected_active_project_roots_not_scanned':['C:/Users/benja/lis300','C:/Users/benja/sol-translator-tiny-v11','C:/Users/benja/sol-translator-tiny-v12','C:/Users/benja/sol-cloud-exposure16-r5','C:/Users/benja/sol-cloud-exposure16-r5-r1','C:/Users/benja/sol-cloud-numeric-capability-v1'],
            'cleanup':cleanup,'coverage':COVERAGE,'counts':dict(COUNTS),'partial':not(ollama_complete and hf_complete) or any(r.get('incomplete') for r in COVERAGE),
            'read_actions':'fixed localhosttags; model manifest/config JSON only; all other files stat metadata only','weight_content_bytes_read':0,
            'model_inference_calls':0,'GPU_calls':0,'optimizer_updates':0,'PC_files_written':0,'deletions':0,'deletion_authorized':False,
            'last_copy_status':'unknown','last_use_status':'unknown; mtime is not last-use','duplicate_definition':'same observed file device/inode; digest filenames/manifest refs not independently weight-hashed'}
    encoded=json.dumps(report,sort_keys=True).encode('utf8')
    if len(encoded)>2*1024**2:raise ValueError('bounded metadata receipt exceeded')
    sys.stdout.buffer.write(encoded+b'\n');sys.stdout.flush()


if __name__=='__main__':main()
