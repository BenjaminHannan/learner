#!/usr/bin/env python3
"""CPU mocks verify protocol, not actual cached-tokenizer token counts."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from unittest import mock

ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'scripts/sol_cloud_question_token_count_v1.py'
spec=importlib.util.spec_from_file_location('token_count_cpu',source)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=[]


class Tokenizer:
    eos_token_id=7
    def __init__(self,mapping):self.mapping=mapping;self.calls=[]
    def encode(self,text,**kwargs):
        assert kwargs=={'add_special_tokens':False}
        assert text in self.mapping,'metadata or unapproved text reached tokenizer'
        self.calls.append((text,kwargs));return list(self.mapping[text])


def check(name,op):checks.append({'name':name,'pass':True,'evidence':op()})


def reject(op):
    try:op()
    except ValueError:return {'expected_ValueError':True}
    raise AssertionError('expected refusal absent')


def target(row,value):return {'id':row['id'],'question_sha256':m.digest(row['question'].encode('utf8')),'numeric_target':value}


def full_counts():
    rows=[{'id':'META-NOT-INPUT-1','question':'Complete question ✅\nSecond line is preserved.'},
          {'id':'META-NOT-INPUT-2','question':'Entire second question.'}]
    tokenizer=Tokenizer({rows[0]['question']:list(range(48)),rows[1]['question']:list(range(49)),
                         '5/12':[101,102,103],'83':[104,105]})
    result=m.count_rows(rows,tokenizer,targets=[target(rows[0],'5/12'),target(rows[1],'83')])
    assert result['retained_ids']==[rows[0]['id']] and result['rejected_ids']==[rows[1]['id']]
    assert result['rows'][1]['question_tokens_before_EOS']==49 and len(result['rows'][1]['question_token_ids_before_EOS'])==49
    assert result['rows'][0]['target_token_ids_with_EOS']==[101,102,103,7]
    assert tokenizer.calls==[(rows[0]['question'],{'add_special_tokens':False}),('5/12',{'add_special_tokens':False}),
                             (rows[1]['question'],{'add_special_tokens':False}),('83',{'add_special_tokens':False})]
    assert result['rows'][0]['question_sha256']==m.digest(rows[0]['question'].encode())
    return {'q48_retained_q49_rejected':True,'full_unicode_newline_question_unchanged':True,
            'no_ID_or_wrappers_tokenized':True,'query_and_numeric_target_separate_calls':True,'no_truncation_kwargs':True}


check('complete string exact token-ID protocol',full_counts)


def target_caps():
    row={'id':'COUNT-1','question':'Complete bounded question.'}
    for size,retained in ((63,True),(64,False)):
        tk=Tokenizer({row['question']:[100],'8':list(range(size))})
        result=m.count_rows([row],tk,targets=[target(row,'8')]);r=result['rows'][0]
        assert r['target_tokens_with_EOS']==size+1 and r['retained']==retained
        assert len(r['target_token_ids_before_EOS'])==size and not r['truncation_performed']
    return {'target63_plusEOS_retained':True,'target64_plusEOS_rejected_fullIDs_preserved':True}


check('numeric target64 inclusiveEOS nevertruncated',target_caps)
row={'id':'COUNT-1','question':'Only the complete question.'}
for name,value in [('expression','5+12'),('unreduced','4/8'),('zerodenominator','7/0'),('negativezero','-0'),
                   ('integerfraction','2/1'),('decimalnotcanonical','2.5'),('prose','The result is8'),('nonstring',8)]:
    check('refuse target '+name,lambda value=value:reject(lambda:m.validate_targets([row],[target(row,value)])))
for name,mutant in [('facts',dict(row,facts=[8])),('tree',dict(row,tree={})),('proposed_answer',dict(row,proposed_answer='8')),
                    ('audit',dict(row,audit={})),('blank',dict(row,question=' \n '))]:
    check('refuse question field '+name,lambda mutant=mutant:reject(lambda:m.validate_questions([mutant])))
check('refuse duplicated metadataIDs',lambda:reject(lambda:m.validate_questions([row,row])))
check('refuse mismatched target questionSHA',lambda:reject(lambda:m.validate_targets([row],[dict(target(row,'8'),question_sha256='0'*64)])))
check('refuse missing verified numeric target',lambda:reject(lambda:m.validate_targets([row],[])))


def offline():
    factory=mock.Mock();tokenizer=Tokenizer({row['question']:[1]});factory.from_pretrained.return_value=tokenizer
    got=m.offline_tokenizer(m.SNAPSHOT,factory);assert got is tokenizer
    factory.from_pretrained.assert_called_once_with(m.SNAPSHOT,local_files_only=True,trust_remote_code=False)
    return {'exact_snapshot_only':True,'local_files_only':True,'trust_remote_code':False,'LM_factory_calls':0}


check('AutoTokenizer factory offline contract',offline)


def optional():
    class Missing:
        eos_token_id=7
        @property
        def name_or_path(self):raise OSError('owned optional metadata failure')
    metadata=m.optional_metadata(Missing())
    assert metadata['name_or_path']['error_type']=='OSError' and metadata['vocab_size'] is None
    return {'optionalmetadata_unavailable_nonfatal':True,'missingmetadata_nonfatal':True}


check('optional metadata failure is nonfatal',optional)
check('requiredEOS absence refuses counts',lambda:reject(lambda:m.count_rows([row],type('NoEOS',(),{'eos_token_id':None})())))


def no_access():
    with mock.patch.object(Path,'stat',side_effect=AssertionError('forbiddenfileaccess')) as stat:
        for name in ('independent_questions_only_batch_01_v2.jsonl','independent_answers_batch_01_v2.json',
                     'readpanel320.json','DEV100.json','stop88.json','uncle-questions/file.json'):
            reject(lambda name=name:m.read_pin({'path':name,'sha256':'0'*64}))
        assert stat.call_count==0
    return {'mixed_or_protected_refused_before_any_file_stat_or_read':True,'file_access_calls':0}


check('preaccess refusal protects excluded source paths',no_access)


def syntax():
    text=source.read_text();ast.parse(text,feature_version=(3,9));ast.parse(text,feature_version=(3,10))
    assert 'AutoModel' not in text.replace('No AutoModel','No model factory')
    return {'Mac39_transport_source_and_PC310_helper_syntax':True,'real_HF_tokenizer_calls':0}


check('native capability syntax only',syntax)
report={'schema':'sol.cloud.tokenizer-helper-cpu-checks.v1','passed':len(checks),'total':len(checks),'checks':checks,
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'actual_host_tokenizer_execution':False,
        'model_calls':0,'optimizer_updates':0,'GPU_calls':0,'SSH_calls':0,'queue_entries':0,
        'limits':['Token lists are explicit CPU mock fixtures, never actual tokenizer measurement or character proxy.','Native actual cached-tokenizer count pending pinned accepted-only inputs/targets and soleintegratorwatcher invocation.']}
print(json.dumps(report,indent=2))
