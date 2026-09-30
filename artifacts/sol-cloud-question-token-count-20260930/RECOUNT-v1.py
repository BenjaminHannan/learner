#!/usr/bin/env python3
"""Saved TRAIN tokenizer receipt recount; never imports/executes a tokenizer."""
import collections
import datetime
import hashlib
import json
from pathlib import Path
from fractions import Fraction

ROOT=Path(__file__).resolve().parents[2]
OWN=ROOT/'artifacts/sol-cloud-question-token-count-20260930'
RAW=OWN/'cloud-pinned'
EXPECTED_STDOUT='90b0688c7632126919624d6a80b77c6c71f5dca96fd6a1a5f6031b091d576723'
OUTBOX='4b6ed6d81087c84eb6e28fdaa6ac39a7864703ff'
checks=[]


def sha(data):return hashlib.sha256(data).hexdigest()


def require(name,test):
    if not test:raise AssertionError(name)
    checks.append(name)


def integer_ids(values):return isinstance(values,list) and all(type(value) is int and 0<=value<65536 for value in values)


def histogram(values):return {str(k):v for k,v in sorted(collections.Counter(values).items())}


def metrics(values):
    values=sorted(values)
    return {'n':len(values),'min':values[0],'max':values[-1],'mean_exact':str(Fraction(sum(values),len(values))),
            'median':values[len(values)//2] if len(values)%2 else str(Fraction(values[len(values)//2-1]+values[len(values)//2],2)),
            'histogram':histogram(values)}


def main():
    github=json.loads((RAW/'GITHUB-TRANSPORT.json').read_bytes())
    require('immutable outbox exact',github['immutable_outbox']==OUTBOX)
    for entry in github['files']:
        name=entry['name'];require('fixed returned basename '+name,name in {'PC-STDOUT.json','PC-STDERR.log','TRANSPORT-v1.json','watcher.exit'})
        data=(RAW/name).read_bytes();require('GitHub exact returned content '+name,data==entry['content'].encode('utf8'))
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\x00'+data).hexdigest()
        require('immutable Git blob matches '+name,blob==entry['sha'])
    raw=(RAW/'PC-STDOUT.json').read_bytes();require('PC stdout external exact SHA',sha(raw)==EXPECTED_STDOUT)
    receipt=json.loads(raw);transport=json.loads((RAW/'TRANSPORT-v1.json').read_bytes())
    require('watcher actual rc0',(RAW/'watcher.exit').read_text().strip()=='rc=0')
    require('native transport terminal success',transport['success'] is True and transport['ssh_returncode']==0 and transport['error_type'] is None)
    require('transport binds exact stdout and empty stderr',transport['pc_stdout_sha256']==EXPECTED_STDOUT and transport['pc_stderr_sha256']==sha((RAW/'PC-STDERR.log').read_bytes()) and (RAW/'PC-STDERR.log').stat().st_size==0)
    spec_bytes=(OWN/'SPEC-v1.json').read_bytes();spec=json.loads(spec_bytes);packet_bytes=(OWN/'PACKET-v1.json').read_bytes();packet=json.loads(packet_bytes)
    require('spec immutable exact receipt binding',sha(spec_bytes)==receipt['spec_sha256'])
    require('packet immutable exact transport binding',sha(packet_bytes)==transport['packet_sha256'])
    require('delivered input/helper exact packet',packet['files']==transport['source_files'])
    for pin in packet['files']:
        data=(ROOT/pin['path']).read_bytes();require('input hash '+pin['path'],len(data)==pin['bytes'] and sha(data)==pin['sha256'])
    require('native tokenizer-only identity and flags',receipt['actual_host_tokenizer_execution'] is True and receipt['actual_user_day'] is False and receipt['model_calls']==0 and receipt['GPU_calls']==0 and receipt['optimizer_updates']==0 and receipt['LM_weights_loaded'] is False and receipt['character_proxy_used'] is False and receipt['truncation_performed'] is False and receipt['token_counts_from_actual_ID_lists'] is True)
    require('exact cached model revision',receipt['tokenizer_revision']=='0f604ada3f766f9f257460c4c9f0b5d6f69d431b' and receipt['tokenizer_metadata']['name_or_path']==spec['snapshot'])
    require('native runtime exact3109',receipt['runtime'].startswith('3.10.9 '))
    require('external tokenizer byte pins match',dict((r['name'],r['sha256']) for r in receipt['tokenizer_files'])==spec['tokenizer_files'])
    require('query/target source pins exact',receipt['question_sources']==spec['questions'] and receipt['verified_targets_pin']==spec['verified_targets'])
    require('target counting complete and limits unchanged',receipt['target_counts_complete'] is True and receipt['question_limit_before_EOS']==48 and receipt['target_limit_with_EOS']==64)
    eos=receipt['tokenizer_metadata']['eos_token_id'];require('actual EOS7 identity',type(eos) is int and eos==7 and receipt['config_identity']['eos_token_id']==eos)
    questions=[]
    for pin in spec['questions']:
        rows=[json.loads(line) for line in (ROOT/pin['path']).read_bytes().splitlines() if line.strip()]
        require('question-only source schema/count '+pin['path'],len(rows)==pin['rows'] and all(set(row)=={'id','question'} for row in rows))
        questions.extend(rows)
    labels=json.loads((ROOT/spec['verified_targets']['path']).read_bytes())['rows']
    by_label={row['id']:row for row in labels};ids=[row['id'] for row in questions]
    require('unique396 questions labels receipt ordered coverage',len(ids)==396 and len(set(ids))==396 and len(labels)==396 and len(by_label)==396 and set(by_label)==set(ids) and [r['id'] for r in receipt['rows']]==ids)
    rows=[]
    for question,record in zip(questions,receipt['rows']):
        name=question['id'];target=by_label[name];value=target['numeric_target'];qids=record['question_token_ids_before_EOS'];tids=record['target_token_ids_before_EOS'];teids=record['target_token_ids_with_EOS']
        require(name+' question/independent target SHA',record['question_sha256']==sha(question['question'].encode('utf8'))==target['question_sha256'] and record['target_sha256']==sha(value.encode('ascii')))
        require(name+' canonical independent numeric literal',str(Fraction(value))==value and record['target_independently_verified'] is True)
        require(name+' exact query token list count',integer_ids(qids) and len(qids)==record['question_tokens_before_EOS'])
        require(name+' exact target tokens and EOS',integer_ids(tids) and integer_ids(teids) and teids==tids+[eos] and len(tids)==record['target_tokens_before_EOS'] and len(teids)==record['target_tokens_with_EOS'])
        require(name+' query-only noEOS no truncation metadata',record['model_input']=='complete question string only' and record['metadata_tokenized_as_question'] is False and record['question_EOS_appended'] is False and record['truncation_performed'] is False and record['question_limit_before_EOS']==48 and record['target_limit_with_EOS']==64)
        reasons=[]
        if len(qids)>48:reasons.append('question exceeds48tokens beforeEOS')
        if len(teids)>64:reasons.append('target exceeds64tokens includingEOS; nevertruncate')
        require(name+' retained/rejected exact limits',record['retained'] is (not reasons) and record['rejection_reasons']==reasons)
        rows.append({'id':name,'question_sha256':record['question_sha256'],'target_sha256':record['target_sha256'],'question_tokens_before_EOS':len(qids),'question_tokens_with_one_EOS_derived':len(qids)+1,'query_EOS_actually_appended':False,'target_tokens_before_EOS':len(tids),'target_tokens_with_EOS':len(teids),'target_kind':'rational' if '/' in value else 'integer','target_numerator_digit_length':len(str(abs(Fraction(value).numerator))),'target_denominator_digit_length':len(str(Fraction(value).denominator)),'retained':not reasons,'rejection_reasons':reasons})
    retained=[r['id'] for r in rows if r['retained']];rejected=[r['id'] for r in rows if not r['retained']]
    require('exact retained/rejected ordered ID lists',retained==receipt['retained_ids'] and rejected==receipt['rejected_ids'])
    rational=[r for r in rows if r['target_kind']=='rational'];integer=[r for r in rows if r['target_kind']=='integer']
    report={'schema':'sol.cloud.question-token-count-recount.v1','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pass':True,'checks_passed':len(checks),'checks':checks,'raw_receipt':{'path':str((RAW/'PC-STDOUT.json').relative_to(ROOT)),'bytes':len(raw),'sha256':EXPECTED_STDOUT,'immutable_outbox':OUTBOX,'git_blob':'c73b89a184fbfa1bdba8d7ed6764910d79b25255'},'actual_native_receipt_completed_utc':receipt['completed_utc'],'accepted_source_rows':396,'question_count_coverage':396,'verified_target_count_coverage':396,'target_EOS_verified_coverage':396,'query_EOS_actually_appended':False,'query_with_one_EOS_counts_are_derived_only':True,'retained_count':len(retained),'rejected_count':len(rejected),'excluded_exact_fraction':str(Fraction(len(rejected),396)),'excluded_percent':100*len(rejected)/396,'retained_ids':retained,'rejected_rows':[r for r in rows if not r['retained']],'question_tokens_before_EOS':metrics([r['question_tokens_before_EOS'] for r in rows]),'question_tokens_with_one_EOS_derived':metrics([r['question_tokens_with_one_EOS_derived'] for r in rows]),'target_tokens_before_EOS':metrics([r['target_tokens_before_EOS'] for r in rows]),'target_tokens_with_EOS':metrics([r['target_tokens_with_EOS'] for r in rows]),'target_kinds':{'integer':len(integer),'rational':len(rational)},'rational_targets':{'count':len(rational),'query_excluded_count':sum(not r['retained'] for r in rational),'target_tokens_with_EOS':metrics([r['target_tokens_with_EOS'] for r in rational])},'by_batch':{batch:{'n':sum(r['id'].split('-')[1]==batch for r in rows),'retained':sum(r['id'].split('-')[1]==batch and r['retained'] for r in rows)} for batch in ('B00','B01','B02','B03')},'tokenizer_file_pins':receipt['tokenizer_files'],'actual_tokenizer_reruns':0,'model_calls':0,'GPU_calls':0,'optimizer_updates':0,'blind_capability_certification':False,'scope':'Nonblind accepted TRAIN tokenizer engineering; saved raw recount only.','generated_report_training_eligible':False,'literal_numeric_offsets':'not measured; optional additive tokenizer-only receipt required','semantic_question_operand_verification':'not performed'}
    row_report={'schema':'sol.cloud.question-token-row-length-recount.v1','raw_receipt_sha256':EXPECTED_STDOUT,'actual_user_day':False,'generated_report_training_eligible':False,'rows':rows}
    (OWN/'RECOUNT-ROWS-v1.json').write_text(json.dumps(row_report,indent=2,sort_keys=True)+'\n')
    (OWN/'RECOUNT-v1.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report[k] for k in ('pass','checks_passed','question_count_coverage','verified_target_count_coverage','target_EOS_verified_coverage','retained_count','rejected_count','excluded_exact_fraction','excluded_percent','rejected_rows','question_tokens_before_EOS','target_tokens_with_EOS','target_kinds','rational_targets','by_batch')},sort_keys=True))


if __name__=='__main__':main()
