#!/usr/bin/env python3
"""Exercise real lifecycle methods through a fake vast executable, before renting."""
import argparse, hashlib, importlib.util, json, os, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('lis320host',Path(__file__).with_name('host.py'))
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
FAKE='''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
p=Path(os.environ['FAKE_LIS320_STATE']);d=json.loads(p.read_text());a=sys.argv[1:]
with p.with_suffix('.calls').open('a') as f:f.write(json.dumps(a)+'\\n')
if a[:2]==['show','instances']:print(json.dumps(d['instances']))
elif a[:2]==['show','user']:print(json.dumps({'credit':9.99}))
elif a[:2]==['search','offers']:print(json.dumps([]))
elif a[:2]==['create','instance']:
 print(json.dumps({'success':False}))
elif a[0] in ('stop','destroy') and a[1]=='instance':
 i=int(a[2]);assert i==42,'attempt to alter another rental'
 if a[0]=='destroy':d['instances']=[x for x in d['instances'] if x['id']!=i]
 else:
  for x in d['instances']:
   if x['id']==i:x['actual_status']='exited'
 p.write_text(json.dumps(d));print(json.dumps({'success':True}))
else:raise SystemExit(7)
'''
def main():
    cases={}
    with tempfile.TemporaryDirectory(prefix='lis320-mock-') as tmp:
        d=Path(tmp);fake=d/'vastai';fake.write_text(FAKE.replace('/usr/bin/env python3',sys.executable));fake.chmod(0o700)
        db=d/'state.json';os.environ['FAKE_LIS320_STATE']=str(db);os.environ['LIS320_VAST']=str(fake)
        a=argparse.Namespace(state=str(d/'job'),repo=str(ROOT),pin='fake',outbox='fake',job='fake')
        r=h.Runner(a);r.r=dict(id=42,label=h.LABEL,dph=.6,started=time.time()-3600)
        other=dict(id=99,label='another-agent',actual_status='running')
        def reset(label=h.LABEL):db.write_text(json.dumps({'instances':[dict(id=42,label=label,actual_status='running'),other]}))
        # Remove sleeps only inside the test. No real CLI or SSH can be called here.
        sleep=h.time.sleep;h.time.sleep=lambda _:None
        try:
            reset();assert r.vastjson('show','user')['credit']==9.99;cases['credit_counts_only']=True
            assert r.vastjson('create','instance','123')['success'] is False;cases['create_failure_visible']=True
            assert abs(r.spent()-.6)<.01;cases['cost_meter']=True
            reset();assert r.finish_instance(False)=='stop'
            data=json.loads(db.read_text())['instances'];assert data[0]['actual_status']=='exited' and data[1]==other
            cases['copy_failure_stops_preserves_disk_and_other_rental']=True
            reset()
            try:r.finish_instance(True)
            except RuntimeError:pass
            else:raise AssertionError('destroy allowed without verified manifest')
            cases['destroy_without_verified_copy_refused']=True
            reset('someone-elses-label')
            before=db.with_suffix('.calls').read_text()
            try:r.finish_instance(True)
            except RuntimeError:pass
            else:raise AssertionError('label mismatch allowed')
            calls=db.with_suffix('.calls').read_text()[len(before):]
            assert 'destroy' not in calls and 'stop' not in calls;cases['ownership_mismatch_refused']=True
            db.write_text(json.dumps({'instances':[other]}));assert r.finish_instance(True)=='gone';cases['gone_is_confirmed_without_destroy']=True
        finally:h.time.sleep=sleep
        # A real tar pipeline substitutes fake SSH, so manifest verification is exercised.
        src=d/'remote';(src/'W').mkdir(parents=True);(src/'W/result.json').write_text('{"rows":336}\n');(src/'drive.log').write_text('done\n')
        fake_ssh=d/'ssh';fake_ssh.write_text('#!/bin/bash\ncd '+str(src)+'\nexec bash -c "${!#}"\n');fake_ssh.chmod(0o700)
        r.host='fake';r.port=123;r.sshbin=str(fake_ssh)
        # The remote path is rewritten only by this mock transport.
        fake_ssh.write_text('#!/bin/bash\nc=${!#}\nc=${c//\/root\/lis320/'+str(src)+'}\nexec bash -c "$c"\n');fake_ssh.chmod(0o700)
        assert r.copy_back(False);cases['manifest_checked_copy_pipeline']=True
        reset();h.time.sleep=lambda _:None
        try:assert r.finish_instance(True)=='destroy'
        finally:h.time.sleep=sleep
        assert json.loads(db.read_text())['instances']==[other];cases['verified_copy_allows_destroy_exact_id_only']=True
        m=r.g/'copy/COPY.sha256';assert m.exists();(r.g/'copy/W/result.json').write_text('corrupt')
        assert h.sha(r.g/'copy/W/result.json')!=m.read_text().split('  W/result.json')[0].splitlines()[-1];cases['manifest_hash_detects_corruption']=True
        reset()
        try:r.finish_instance(True)
        except RuntimeError:pass
        else:raise AssertionError('destroy after copy corruption allowed')
        cases['destroy_after_copy_corruption_refused']=True
    # Static contracts supplement the executable fake-CLI tests.
    remote=Path(__file__).with_name('box').joinpath('drive.py').read_text()
    assert "with (R/f'panel-{arm}.started').open('x')" in remote
    assert "'--batch',16" in remote and "'--seed',300" in remote and "'--max-len',512" in remote
    cases['exclusive_once_only_reads_and_fixed_training_args']=True
    files=['handoff/kit/lis320v/host.py','handoff/kit/lis320v/start.sh','handoff/kit/lis320v/box/drive.py','handoff/kit/lis320v/mock_test.py','scripts/codex_lis320_data.py']
    result=dict(status='PASS',utc=subprocess.check_output(['date','-u','+%FT%TZ'],text=True).strip(),cases=cases,tested_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},limits='Fake CLI and local tar transport; actual GPU training, remote imports and network failures remain untested.')
    out=ROOT/'artifacts/claude-lis320-20260926/MOCK-TEST.json'
    with out.open('w') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'PASS','checks':len(cases),'real_rentals':0}))
if __name__=='__main__':main()
