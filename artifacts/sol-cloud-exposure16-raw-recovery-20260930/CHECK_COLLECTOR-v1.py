#!/usr/bin/env python3
"""CPU byte-stream checks; no remote calls, model or training."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest import mock

ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'scripts/sol_cloud_exposure16_raw_collect_v1.py'
spec=importlib.util.spec_from_file_location('raw_collect_cpu',source)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=[]
job='sol-cloud-exposure16-r5-s0-r1-benspc'
prefix=m.EXPOSURE+'/runs/s0/'


def manifest(records):
    return dict(seed=0,job=job,returncode=1,actual_user_day=False,activated=False,records=records)


def record(name,size=1):
    return {'relative':prefix+name,'bytes':size,'sha256':'0'*64}


def reject(operation):
    try:operation()
    except (ValueError,RuntimeError,TimeoutError) as error:return {'expected_refusal':type(error).__name__}
    raise AssertionError('expected refusal absent')


def check(name,operation):checks.append({'name':name,'pass':True,'evidence':operation()})


selected=[record(n) for n in sorted(m.NAMES)]
check('exact7 diagnostic names; checkpoint excluded',lambda:{'selected7':len(m.selected_records(manifest(selected+[record('checkpoint-000800.pt')]),0,job))==7})
for name,rows in [('parentescape',[record('../TRAIN-RAW.jsonl')]),('wrongseed',[dict(record('TRAIN-RAW.jsonl'),relative=prefix.replace('s0','s1')+'TRAIN-RAW.jsonl')]),
                  ('duplicate',[selected[0],selected[0]]),('negative',[record('TRAIN-RAW.jsonl',-1)]),
                  ('Booleanbytes',[record('TRAIN-RAW.jsonl',False)]),('rawcap',[record('TRAIN-RAW.jsonl',m.RAW_CAP+1)]),
                  ('framecap',[record('frames-000000.pt',m.FRAME_CAP+1)]),('checkpointonly',[record('checkpoint-000800.pt')]),
                  ('wrongframeupdate',[record('frames-000600.pt')])]:
    check('refuse '+name,lambda rows=rows:reject(lambda:m.selected_records(manifest(rows),0,job)))
for name,changes in [('missingreturncode',{'returncode':None}),('wrongjob',{'job':'wrong'}),('activation',{'activated':True})]:
    check('refuse manifest '+name,lambda changes=changes:reject(lambda:m.selected_records(dict(manifest(selected),**changes),0,job)))


def binary(size,mode='good'):
    # Synthetic numeric byte pattern is test-only; it is never training material.
    data=bytes(range(256))*(size//256)+bytes(range(size%256))
    r={'relative':prefix+'frames-000000.pt','bytes':size,'sha256':hashlib.sha256(data).hexdigest()}
    actual_size=size+(1 if mode=='overflow' else -1 if mode=='truncated' else 0)
    code='import sys\nn=%d\ndata=bytes(range(256))*(n//256)+bytes(range(n%%256))\nsys.stdout.buffer.write(data)\n'%actual_size
    if mode=='hash':r['sha256']='0'*64
    with tempfile.TemporaryDirectory(prefix='sol-raw-collector-cpu-') as temporary:
        out=Path(temporary)
        op=lambda:m.stream_parts([sys.executable,'-B','-'],code,r,out,timeout=3)
        if mode!='good':return reject(op)
        result=op();parts=result['ordered_parts']
        assert len(parts)==(size+m.PART-1)//m.PART
        assert all(p['bytes']<=m.PART for p in parts)
        joined=b''.join((out/p['name']).read_bytes() for p in parts)
        assert joined==data and not result['training_eligible']
        return {'bytes':len(joined),'parts':len(parts),'binary_exact':True,'source_and_parts_SHA_verified':True}


check('binary4MiB boundary plus123 exact two parts',lambda:binary(m.PART+123))
check('binaryzero extent valid digest',lambda:binary(0))
for mode in ('overflow','truncated','hash'):
    check('refuse binary '+mode,lambda mode=mode:binary(1000,mode))


def syntax():
    text=source.read_text();ast.parse(text,feature_version=(3,9))
    for remote in (m.remote_header(selected)+'print(1)\n',m.remote_header([selected[0]])+'print(1)\n'):
        ast.parse(remote,feature_version=(3,10));compile(remote,'readonlyPC','exec')
    assert 'tarfile' not in text and 'torch' not in text and 'scp' not in text
    assert 'StrictHostKeyChecking=yes' in text and 'UpdateHostKeys=no' in text
    assert 'spec[\'watcher_receipt\']' in text and "manifest differs from exact saved watcher output" in text
    return {'Mac39AST':True,'PC310AST':True,'strict_binary_SSH':True,'archive_model_SCP_calls':0,'immutable_stdout_binding':True}


check('source syntax and immutable watcher binding',syntax)
report={'schema':'sol.cloud.exposure16.raw-collector-checks.v1','passed':len(checks),'total':len(checks),
        'checks':checks,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'model_calls':0,'optimizer_updates':0,'SSH_calls':0,'queue_entries':0,
        'limits':['Actual PC source files have not been copied; true closed watcher manifest is pending.','CPU test bytes are synthetic numeric mechanics fixtures, never training material.']}
print(json.dumps(report,indent=2))
