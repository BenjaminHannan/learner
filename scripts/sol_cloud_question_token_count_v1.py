#!/usr/bin/env python3
"""Offline tokenizer-only admission counts; question strings are the sole input.

Numeric target tokenization is a separate verified-label count. IDs/provenance/
facts/trees/audit/answers are never concatenated into question/model inputs.
No AutoModel, tensor checkpoint, GPU, optimizer, generation or network action.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
from fractions import Fraction
import re
import sys

REVISION = '0f604ada3f766f9f257460c4c9f0b5d6f69d431b'
SNAPSHOT = 'C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/' + REVISION
QUESTIONS_PREFIX = 'artifacts/sol-cloud-luna-train-20260930/'
TOKENIZER_FILES = frozenset(('tokenizer.json','tokenizer_config.json','special_tokens_map.json',
                              'added_tokens.json','config.json','tokenizer.model','vocab.json','merges.txt'))
SPEC_SCHEMA = 'sol.cloud.question-token-count-spec.v1'
MAX_ROWS, MAX_JSON_BYTES = 512, 1024 ** 2


def digest(data):return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def read_pin(record,cap=MAX_JSON_BYTES):
    path=Path(record['path'])
    lowered=path.as_posix().lower()
    if any(word in lowered for word in ('uncle-questions','readpanel320','dev100','stop88',
                                        'sealed-panels','independent_questions','independent_answers')):
        raise ValueError('only accepted exports/normalized targets; protected or mixed input forbidden before access')
    if path.stat().st_size>cap:raise ValueError('bounded metadata/source file required')
    data=path.read_bytes()
    if digest(data)!=record['sha256']:raise ValueError('external immutable input pin differs')
    return data


def validate_questions(rows):
    if not isinstance(rows,list) or not 1<=len(rows)<=MAX_ROWS:raise ValueError('bounded accepted question rows required')
    seen=set()
    for row in rows:
        if (not isinstance(row,dict) or set(row)!={'id','question'}
                or not isinstance(row['id'],str) or not row['id'] or row['id'] in seen
                or not isinstance(row['question'],str) or not row['question'].strip()):
            raise ValueError('accepted unique complete question-only rows required')
        seen.add(row['id'])
    return rows


def validate_targets(rows,targets):
    """Normalization is owned by the independent accepted-only numeric binder."""
    if targets is None:return None
    if not isinstance(targets,list):raise ValueError('independently verified target rows required')
    by={r['id']:r for r in rows};seen=set();result={}
    for item in targets:
        if (not isinstance(item,dict) or set(item)!={'id','question_sha256','numeric_target'}
                or item['id'] not in by or item['id'] in seen
                or type(item['numeric_target']) is not str
                or not re.fullmatch(r'-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?',item['numeric_target'])
                or str(Fraction(item['numeric_target']))!=item['numeric_target']
                or item['question_sha256']!=digest(by[item['id']]['question'].encode('utf-8'))):
            raise ValueError('independent numeric target identity/question binding differs')
        seen.add(item['id']);result[item['id']]=item['numeric_target']
    if seen!=set(by):raise ValueError('every accepted question needs one verified numeric target')
    return result


def encode_complete(tokenizer,text):
    # No truncation/max_length or textual wrapper/ID/fact field exists here.
    ids=tokenizer.encode(text,add_special_tokens=False)
    if not isinstance(ids,list) or any(type(value) is not int or value<0 for value in ids):
        raise ValueError('exact tokenizer integer IDs required')
    return ids


def count_rows(rows,tokenizer,*,targets=None):
    validate_questions(rows);verified=validate_targets(rows,targets)
    eos=tokenizer.eos_token_id
    if type(eos) is not int or eos<0:raise ValueError('actual tokenizer EOS identity required')
    records=[]
    for row in rows:
        question=row['question']
        query_ids=encode_complete(tokenizer,question)
        record={'id':row['id'],'question_sha256':digest(question.encode('utf-8')),
                'question_token_ids_before_EOS':query_ids,'question_tokens_before_EOS':len(query_ids),
                'question_EOS_appended':False,'question_limit_before_EOS':48,
                'model_input':'complete question string only','metadata_tokenized_as_question':False,
                'target_independently_verified':verified is not None,'truncation_performed':False}
        reasons=[]
        if len(query_ids)>48:reasons.append('question exceeds48tokens beforeEOS')
        if verified is not None:
            target=str(verified[row['id']]);target_ids=encode_complete(tokenizer,target)
            record.update(target_sha256=digest(target.encode('ascii')),
                          target_token_ids_before_EOS=target_ids,target_tokens_before_EOS=len(target_ids),
                          target_token_ids_with_EOS=target_ids+[eos],target_tokens_with_EOS=len(target_ids)+1,
                          target_limit_with_EOS=64)
            if len(target_ids)+1>64:reasons.append('target exceeds64tokens includingEOS; nevertruncate')
        record.update(retained=not reasons,rejection_reasons=reasons)
        records.append(record)
    return {'schema':'sol.cloud.question-token-counts.v1','rows':records,
            'retained_ids':[r['id'] for r in records if r['retained']],
            'rejected_ids':[r['id'] for r in records if not r['retained']],
            'target_counts_complete':verified is not None,'question_limit_before_EOS':48,'target_limit_with_EOS':64,
            'actual_user_day':False,'token_counts_from_actual_ID_lists':True,'character_proxy_used':False,
            'truncation_performed':False,'LM_weights_loaded':False,'model_calls':0,'GPU_calls':0,'optimizer_updates':0,
            'generated_count_report_training_eligible':False}


def pin_tokenizer(snapshot,pins):
    snapshot=Path(snapshot)
    if not isinstance(pins,dict) or not {'config.json','tokenizer.json','tokenizer_config.json'}.issubset(pins):
        raise ValueError('external exact tokenizer/config byte pins required before tokenizer load')
    if set(pins)-TOKENIZER_FILES:raise ValueError('model weights/unknown files cannot be admitted as tokenizer metadata')
    files=[]
    for name,expected in sorted(pins.items()):
        path=snapshot/name
        if not path.is_file() or file_sha(path)!=expected:raise ValueError('cached shipped tokenizer/config bytes differ')
        files.append({'name':name,'bytes':path.stat().st_size,'sha256':expected})
    return files


def offline_tokenizer(snapshot,factory):
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',
                      PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
    return factory.from_pretrained(str(snapshot),local_files_only=True,trust_remote_code=False)


def optional_metadata(tokenizer):
    result={}
    for name in ('name_or_path','vocab_size','model_max_length','bos_token_id','eos_token_id','pad_token_id'):
        try:
            value=getattr(tokenizer,name,None)
            result[name]=value if value is None or type(value) in (str,int,bool) else {'status':'nonprimitive withheld'}
        except Exception as error:result[name]={'status':'unavailable','error_type':type(error).__name__}
    return result


def install_offline_guard():
    def audit(event,args):
        if event in ('socket.connect','socket.connect_ex','socket.getaddrinfo','subprocess.Popen'):
            raise RuntimeError('offline tokenizer helper prohibits network/subprocess')
        if event=='open' and args and isinstance(args[0],(str,bytes)):
            path=os.fsdecode(args[0]).lower()
            if path.endswith(('.safetensors','.pt','.pth','.bin')):
                raise RuntimeError('LM/checkpoint bytes prohibited in tokenizer-only helper')
    sys.addaudithook(audit)


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--spec-sha256',required=True)
    args=p.parse_args();raw=read_pin({'path':args.spec,'sha256':args.spec_sha256});spec=json.loads(raw)
    if (spec.get('schema')!=SPEC_SCHEMA or spec.get('split')!='TRAIN'
            or spec.get('accepted_only') is not True or spec.get('actual_user_day') is not False
            or spec.get('snapshot')!=SNAPSHOT or spec.get('question_model_input')!='complete question only'):
        raise ValueError('exact explicitly accepted offline TRAIN-question count specification required')
    if platform.system()!='Windows' or sys.version_info[:3]!=(3,10,9):
        raise ValueError('actual PC3.10.9 CPU tokenizer route required')
    rows=[]
    for record in spec['questions']:
        relative=record['path'].replace('\\','/')
        if not relative.startswith(QUESTIONS_PREFIX) or '..' in Path(relative).parts or record.get('accepted_only') is not True:
            raise ValueError('explicit accepted-only question export required before content read')
        raw=read_pin(record)
        parsed=[json.loads(line) for line in raw.splitlines() if line.strip()]
        if len(parsed)!=record['rows']:raise ValueError('accepted question row count differs')
        rows.extend(parsed)
    validate_questions(rows)
    targets=None
    if spec.get('verified_targets') is not None:
        record=spec['verified_targets']
        if record.get('independently_verified') is not True or record.get('accepted_only') is not True:
            raise ValueError('separate independent accepted-only target artifact required')
        packet=json.loads(read_pin(record))
        if not isinstance(packet,dict) or packet.get('schema')!='sol.cloud.luna.accepted-numeric-targets.v1':
            raise ValueError('exact accepted independently verified numeric target packet required')
        targets=packet['rows']
        validate_targets(rows,targets)
    before=pin_tokenizer(spec['snapshot'],spec['tokenizer_files'])
    config=json.loads((Path(spec['snapshot'])/'config.json').read_text(encoding='utf-8'))
    install_offline_guard()
    from transformers import AutoTokenizer
    tokenizer=offline_tokenizer(spec['snapshot'],AutoTokenizer)
    result=count_rows(rows,tokenizer,targets=targets)
    after=pin_tokenizer(spec['snapshot'],spec['tokenizer_files'])
    if before!=after:raise ValueError('tokenizer/config bytes changed during count')
    result.update(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  actual_host_tokenizer_execution=True,tokenizer_revision=REVISION,
                  tokenizer_files=before,tokenizer_metadata=optional_metadata(tokenizer),
                  config_identity={k:config.get(k) for k in ('model_type','architectures','vocab_size','bos_token_id','eos_token_id','pad_token_id')},
                  spec_sha256=args.spec_sha256,question_sources=spec['questions'],
                  verified_targets_pin=spec.get('verified_targets'),runtime=sys.version)
    encoded=(json.dumps(result,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')
    if len(encoded)>4*1024**2:raise ValueError('bounded tokenizer count receipt required')
    sys.stdout.buffer.write(encoded)


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'schema':'sol.cloud.tokenizer-count-failure.v1','error_type':type(error).__name__,
                          'raw_diagnostics_suppressed':True,'LM_weights_loaded':False,'model_calls':0,
                          'GPU_calls':0,'optimizer_updates':0,'actual_user_day':False}),flush=True)
        raise SystemExit(1)
