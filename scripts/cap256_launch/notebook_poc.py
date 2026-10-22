"""Bounded48-call numerical note-use POC; preserve each native observation."""
import argparse
import datetime
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run(a):
    root=Path(a.root).resolve();p=read(a.plan);assert sha(a.plan)==a.plan_sha256
    assert p['native_calls']==48 and p['optimizer_updates']==0 and p['worker_seconds']==600
    assert p['seeds']==[0,1] and p['arms']==['full','no_notebook'] and p['fixed_rounds']==4
    assert os.environ['TREE']==str(root) and os.environ['JOB']
    def pin(v):
        path=(root/v['path']).resolve();assert path.is_relative_to(root) and sha(path)==v['sha256'];return path
    for v in p['file_pins']+p['source_exclusions']:pin(v)
    receipt=read(pin(p['verification']))
    for v in [receipt['verifier_source_or_review_pin']]+receipt['source_exclusion_metadata_pins']:assert sha(v['path'])==v['sha256']
    for e in p['entries']:
        m=read(pin(e['manifest']));assert sha(m['checkpoint']['path'])==m['checkpoint']['sha256']
        for v in m['continuation'].values():assert sha(v['path'])==v['sha256']
        for name,h in m['code_pins'].items():assert sha(root/name)==h
    spec=importlib.util.spec_from_file_location('_sealed_resource',root/'scripts/sol_cloud_capability256_v1.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
    matrix=root/p['output_namespace'];assert not matrix.exists(),'prior POC output; no duplicate'
    unit=s.filesystem_allocation_unit(root)
    def resource(increase=0):
        assert shutil.disk_usage(root).free>=p['reserve_bytes']+increase
        assert s.allocated_bytes(root,unit)+increase<=p['project_cap_bytes']
        assert s.allocated_bytes(matrix,unit)+increase<=p['output_cap_bytes']
    resource(p['output_cap_bytes']);matrix.mkdir(parents=True);started=time.monotonic();calls=0;active={};reports=[]
    identity={'schema':'cap256.notebook48.identity.v1','plan_sha256':a.plan_sha256,'job':os.environ['JOB'],'optimizer_updates':0,'training_eligible':False,'learned_writer_claim':False}
    def write(name,value,append=False):
        data=(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode();resource(len(data)+unit)
        with (matrix/name).open('ab' if append else 'xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    write('CLAIM.json',{**identity,'utc':now(),'calls_expected':48,'no_retries':True})
    try:
        sys.path[:0]=[str(root),str(root/'scripts')]
        import torch
        import sol_nextdemo_dev_v1 as dev
        import sol_cloud_numeric_fit_v2 as observer
        from sol_translator_runtime import component_fingerprint
        assert torch.cuda.is_available() and torch.cuda.get_device_properties(0).total_memory<=16*2**30
        initial_init=dev.Runtime.__init__;initial_answer=dev.Runtime.answer;initial_observe=observer.observe_generation
        def tracked_init(self,*args,**kwargs):
            initial_init(self,*args,**kwargs);m=self.manifest;cl=read(m['continuation']['closed']['path'])
            modules={'core':self.r['core'],'reader':self.r['reader'],'prefix':self.r['dec'].adapter,'lm':self.r['dec'].lm}
            active['runtime']=self;active['fingerprints']={k:component_fingerprint(v) for k,v in modules.items()}
            assert all(active['fingerprints'][k]==cl['final_fingerprints'][k] for k in ['core','reader','prefix'])
            write('MODEL-LOADED-s%d.json'%m['seed'],{**identity,'utc':now(),'seed':m['seed'],'checkpoint':m['checkpoint'],'fingerprints':active['fingerprints'],'native_calls_so_far':calls})
        def tracked_answer(self,question,context,intervention='full'):
            assert time.monotonic()-started<600 and calls<48
            active['metadata']={'seed':self.manifest['seed'],'intervention':intervention,'question_sha256':hashlib.sha256(question.encode()).hexdigest(),'supplied_context_sha256':hashlib.sha256(context.encode()).hexdigest()}
            answer=initial_answer(self,question,context,intervention)
            write('ANSWERS.jsonl',{**identity,'call_index':calls,**active['metadata'],'answer':answer},True)
            return answer
        def tracked_observe(*args,**kwargs):
            nonlocal calls
            assert calls<48 and time.monotonic()-started<600;resource()
            observed=initial_observe(*args,**kwargs);calls+=1
            write('CALLS.jsonl',{**identity,'utc':now(),'call_index':calls,**active['metadata'],'observed':observed},True)
            if calls==1:write('FIRST-PREDICTION.json',{**identity,'utc':now(),'seed':active['metadata']['seed'],'native_calls':1})
            return observed
        dev.Runtime.__init__=tracked_init;dev.Runtime.answer=tracked_answer;observer.observe_generation=tracked_observe
        for e in p['entries']:
            before=calls;argv=['notebook-poc','--numeric-notes',str(pin(p['notes'])),'--numeric-notes-sha256',p['notes']['sha256'],'--numeric-targets',str(pin(p['targets'])),'--numeric-targets-sha256',p['targets']['sha256'],'--numeric-verification',str(pin(p['verification'])),'--numeric-verification-sha256',p['verification']['sha256'],'--manifest',str(pin(e['manifest'])),'--manifest-sha256',e['manifest']['sha256'],'--out',str(matrix/('SEED%d-RAW.json'%e['seed'])),'--notebook-ab']
            sys.argv=argv;dev.main();assert calls-before==24
            runtime=active['runtime'];modules={'core':runtime.r['core'],'reader':runtime.r['reader'],'prefix':runtime.r['dec'].adapter,'lm':runtime.r['dec'].lm}
            assert all(component_fingerprint(v)==active['fingerprints'][k] for k,v in modules.items())
            report=read(matrix/('SEED%d-RAW.json'%e['seed']));assert len(report['rows'])==24 and report['optimizer_updates']==0
            reports.append({'seed':e['seed'],'raw_sha256':sha(matrix/('SEED%d-RAW.json'%e['seed'])),'native_calls':24,'weights_unchanged':True})
            del runtime,modules;active.clear();gc.collect();torch.cuda.empty_cache()
        assert calls==48
        write('CLOSED.json',{**identity,'closed':True,'utc':now(),'native_calls':calls,'reports':reports,'calls_sha256':sha(matrix/'CALLS.jsonl'),'answers_sha256':sha(matrix/'ANSWERS.jsonl'),'wall_seconds':time.monotonic()-started,'peak_cuda_allocated_bytes':torch.cuda.max_memory_allocated()})
    except Exception as ex:
        write('FAILURE.json',{**identity,'utc':now(),'error_type':type(ex).__name__,'error':str(ex),'native_calls':calls,'wall_seconds':time.monotonic()-started});raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--plan',required=True);p.add_argument('--plan-sha256',required=True);run(p.parse_args())
