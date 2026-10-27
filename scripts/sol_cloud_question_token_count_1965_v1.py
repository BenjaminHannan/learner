#!/usr/bin/env python3
"""Offline tokenizer-only counts for the accepted 1,965 question strings.

The tokenizer receives only the complete question string. IDs and question
hashes bind the result but never enter tokenizer.encode. No model, labels,
facts, trees, weights, generation, GPU, network or optimizer are used.
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
QUESTIONS_PREFIX = 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/'
TOKENIZER_FILES = frozenset(('tokenizer.json','tokenizer_config.json','special_tokens_map.json',
                              'added_tokens.json','config.json','tokenizer.model','vocab.json','merges.txt'))
SPEC_SCHEMA = 'sol.cloud.question-token-count-spec.v2'
MAX_ROWS, MAX_JSON_BYTES = 2048, 1024 ** 2


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
        raise ValueError('only accepted question packet; protected or mixed input forbidden before access')
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


def encode_complete(tokenizer,text):
    # No truncation/max_length or textual wrapper/ID/fact field exists here.
    ids=tokenizer.encode(text,add_special_tokens=False)
    if not isinstance(ids,list) or any(type(value) is not int or value<0 for value in ids):
        raise ValueError('exact tokenizer integer IDs required')
    return ids


def count_rows(rows,tokenizer):
    validate_questions(rows)
    eos=tokenizer.eos_token_id
    if type(eos) is not int or eos<0:raise ValueError('actual tokenizer EOS identity required')
    records=[]
    for row in rows:
        question=row['question']
        query_ids=encode_complete(tokenizer,question)
        with_eos=query_ids+[eos]
        record={'id':row['id'],'question_sha256':digest(question.encode('utf-8')),
                'question_token_ids_before_EOS':query_ids,'question_tokens_before_EOS':len(query_ids),
                'question_token_ids_with_EOS':with_eos,'question_tokens_with_EOS':len(with_eos),
                'question_limit_with_EOS':48,'model_input':'complete question string only',
                'metadata_tokenized_as_question':False,'truncation_performed':False}
        reasons=[]
        if len(with_eos)>48:reasons.append('question exceeds48tokens includingEOS')
        record.update(retained=not reasons,rejection_reasons=reasons)
        records.append(record)
    return {'schema':'sol.cloud.question-token-counts.v2','rows':records,
            'retained_ids':[r['id'] for r in records if r['retained']],
            'rejected_ids':[r['id'] for r in records if not r['retained']],
            'question_limit_with_EOS':48,'eos_appended_once':True,
            'token_counts_from_actual_ID_lists':True,'character_proxy_used':False,
            'truncation_performed':False,'LM_weights_loaded':False,'model_calls':0,'GPU_calls':0,
            'optimizer_updates':0,'target_labels_loaded':False,'actual_user_day':False,
            'generated_count_report_training_eligible':False}


def pin_tokenizer(snapshot,pins):
    snapshot=Path(snapshot)
    if not isinstance(pins,dict) or not {'config.json','tokenizer.json','tokenizer_config.json'}.issubset(pins):
        raise ValueError('external exact tokenizer/config byte pins required')
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
    if (spec.get('schema')!=SPEC_SCHEMA or spec.get('split')!='ALL_ACCEPTED_QUESTION_ONLY'
            or spec.get('accepted_only') is not True or spec.get('snapshot')!=SNAPSHOT
            or spec.get('question_model_input')!='complete question only'
            or spec.get('target_labels_included') is not False):
        raise ValueError('exact accepted-only offline question count specification required')
    if platform.system()!='Windows' or sys.version_info[:3]!=(3,10,9):
        raise ValueError('actual PC3.10.9 CPU tokenizer route required')
    if len(spec.get('questions',[]))!=1:raise ValueError('one pinned complete question-only packet required')
    record=spec['questions'][0]
    relative=record['path'].replace('\\','/')
    if (not relative.startswith(QUESTIONS_PREFIX) or '..' in Path(relative).parts
            or record.get('accepted_only') is not True or record.get('rows')!=1965):
        raise ValueError('exact pinned accepted-only question packet required before content read')
    packet_raw=read_pin(record,cap=2*1024**2)
    packet=[json.loads(line) for line in packet_raw.splitlines() if line.strip()]
    if len(packet)!=1965:raise ValueError('accepted question packet row count differs')
    for item in packet:
        if (not isinstance(item,dict) or set(item)!={'id','question','question_sha256'}
                or not isinstance(item['id'],str) or not item['id']
                or not isinstance(item['question'],str) or not item['question'].strip()
                or item['question_sha256']!=digest(item['question'].encode('utf-8'))):
            raise ValueError('question-only row identity/hash differs')
    rows=[{'id':item['id'],'question':item['question']} for item in packet]
    validate_questions(rows)
    before=pin_tokenizer(spec['snapshot'],spec['tokenizer_files'])
    config=json.loads((Path(spec['snapshot'])/'config.json').read_text(encoding='utf-8'))
    install_offline_guard()
    from transformers import AutoTokenizer
    tokenizer=offline_tokenizer(spec['snapshot'],AutoTokenizer)
    result=count_rows(rows,tokenizer)
    after=pin_tokenizer(spec['snapshot'],spec['tokenizer_files'])
    if before!=after:raise ValueError('tokenizer/config bytes changed during count')
    result.update(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  actual_host_tokenizer_execution=True,tokenizer_revision=REVISION,
                  tokenizer_files=before,tokenizer_metadata=optional_metadata(tokenizer),
                  config_identity={k:config.get(k) for k in ('model_type','architectures','vocab_size','bos_token_id','eos_token_id','pad_token_id')},
                  spec_sha256=args.spec_sha256,question_packet_sha256=record['sha256'],runtime=sys.version)
    encoded=(json.dumps(result,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')
    if len(encoded)>12*1024**2:raise ValueError('bounded tokenizer count receipt required')
    sys.stdout.buffer.write(encoded)


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'schema':'sol.cloud.tokenizer-count-failure.v2','error_type':type(error).__name__,
                          'raw_diagnostics_suppressed':True,'LM_weights_loaded':False,'model_calls':0,
                          'GPU_calls':0,'optimizer_updates':0,'target_labels_loaded':False}),flush=True)
        raise SystemExit(1)
