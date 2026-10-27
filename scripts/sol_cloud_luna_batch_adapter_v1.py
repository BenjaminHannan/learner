#!/usr/bin/env python3
"""Pinned accepted-only synthetic TRAIN source/target binding; CPU stdlib only.

Operation trees/expressions are checked numerically out of band and never copied
to question inputs or numeric targets. Held independent records are skipped by
ID before any value-content decoder. No model/tokenizer/optimizer/network calls.
"""
from __future__ import annotations
import argparse
import ast
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

from sol_cloud_luna_admission_v1 import QuestionInput, model_question, safe_path, text_sha
from sol_cloud_trainonly_v1 import ByteScanner

DATA = 'artifacts/sol-cloud-luna-train-20260930'
SOURCES = {
    'b00': {'directory': 'batch00-v2-input-v1', 'count': 100,
        'author': ('batch_00_v2.jsonl', '6b8371fb13e8fd7c6cadf52416281ea835005bffee88cd0726371fc796c30090'),
        'questions': ('questions_only_batch_00_v2.jsonl', '3ab4278aaac6d45ca27d773d6f865dc2ecbe65ca9d784b3bc42daa49deb37596'),
        'independent': ('independent_answers_batch_00_v2.jsonl', 'e037b01a37cebcf69b0e5329c651203ccda477537481a5925a8181aab2584e71'),
        'comparison': ('audit_batch_00_v2_rows.jsonl', '22f69e67d8421c848cc2e84b3c356178e5e2a9c510e581f0b0769c74c5492a59'),
        'metadata': ('audit_batch_00_v2_summary.json', 'bdde119ffffb0ef913aaf18079e9c41ad97f5e8f93a9afbd3f0a741ca11b80a8')},
    'b01-b03': {'directory': 'b01-b03-v2-input-v1', 'count': 296,
        'author': ('accepted_only_b01_b03_v2.jsonl', '7112b15576ee2012e3c7aae43548acc2fe311957d9562b7a6ddf29446686034f'),
        'questions': ('questions_only_accepted_b01_b03_v2.jsonl', 'a20424cad94ad26bea6b855075580ccb6594523ea313ed78aa5c6ef3a5263973'),
        'independent': ('independent_questions_only_b01_b03_v2.jsonl', '320125c70a36379caa0519bfee0311a284464672157a3677536808816cecf9aa'),
        'comparison': ('recheck_v2_comparison_b01_b03.jsonl', 'a72a1069b2d00b97d81f9b692b62ebbebcd04aaacd8fcd65bc5e10684bf4f5f0'),
        'metadata': ('accepted_only_manifest_b01_b03_v2.json', '83f1b8e4d8be81b0a3935cf0beaba1f8645cc9dcd2b97469fad835e05bf6fd22'),
        'lock': ('independent_questions_only_b01_b03_v2_lock.json', 'f2a73ebd45432f67fd3fd8b2a14ba18d0e2719508e529a824a74b69ee7ef4f4b')}}
AUTHOR_KEYS = {'id','question','proposed_answer','family','difficulty','facts',
               'operation_tree','synthetic','author_model','generation'}
HELD = {'LUNA-B01-012','LUNA-B02-025','LUNA-B02-030','LUNA-B03-033'}
NUMERIC = re.compile(r'-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*|\.[0-9]+)?\Z')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exact_number(value) -> Fraction:
    if type(value) is int:
        return Fraction(value)
    if type(value) is dict and set(value) == {'numerator','denominator'}:
        if type(value['numerator']) is not int or type(value['denominator']) is not int or value['denominator'] <= 0:
            raise ValueError('typed integer rational value required')
        return Fraction(value['numerator'], value['denominator'])
    if type(value) is str and NUMERIC.fullmatch(value):
        return Fraction(value)
    raise ValueError('numeric outcome constant required; prose/code/expression not a target')


def arithmetic_expression(text: str) -> Fraction:
    """Strict arithmetic AST, never eval/exec or model input/target."""
    if type(text) is not str or len(text) > 2048:
        raise ValueError('bounded independent arithmetic expression required')
    parsed = ast.parse(text, mode='eval')
    if sum(1 for _ in ast.walk(parsed)) > 256:
        raise ValueError('arithmetic AST cap')
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int,float):
            return exact_number(ast.get_source_segment(text, node))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd,ast.USub)):
            n = visit(node.operand)
            return n if isinstance(node.op,ast.UAdd) else -n
        if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
            a,b = visit(node.left),visit(node.right)
            if isinstance(node.op,ast.Add): return a+b
            if isinstance(node.op,ast.Sub): return a-b
            if isinstance(node.op,ast.Mult): return a*b
            if not b: raise ValueError('division by zero')
            return a/b
        raise ValueError('only literal numeric arithmetic is allowed in audit AST')
    return visit(parsed.body)


def tree_value(tree, depth=0) -> Fraction:
    if type(tree) is not dict or depth > 32:
        raise ValueError('bounded numeric audit tree required')
    kind = tree.get('type')
    if kind == 'number' and set(tree) == {'type','value'}:
        return exact_number(tree['value'])
    if kind == 'solve_linear' and set(tree) == {'type','a','b','c'}:
        a,b,c = (exact_number(tree[k]) for k in ('a','b','c'))
        if not a: raise ValueError('zero linear coefficient')
        return (c-b)/a
    if kind in ('add','sub','mul','div') and set(tree) == {'type','args'}:
        if (type(tree['args']) is not list or not 2 <= len(tree['args']) <= 16
                or kind in ('sub','div') and len(tree['args']) != 2):
            raise ValueError('bounded associative or two ordered numeric arguments required')
        values = [tree_value(t,depth+1) for t in tree['args']]
        if kind == 'add': return sum(values,Fraction(0))
        if kind == 'mul':
            result = Fraction(1)
            for value in values: result *= value
            return result
        a,b = values
        if kind == 'sub': return a-b
        if not b: raise ValueError('division by zero')
        return a/b
    raise ValueError('unsupported/malformed numeric audit tree')


def accepted_jsonl(path, accepted_ids):
    """JSONL field-span scan. Only keys and ID decoded before membership."""
    if not accepted_ids:
        raise ValueError('explicit nonempty accepted ID metadata required')
    if set(accepted_ids) & HELD:
        raise ValueError('held identities cannot be admitted even by a changed caller allowlist')
    scan = ByteScanner(path)
    rows, excluded, seen, proof = {}, [], set(), []
    try:
        while True:
            scan.whitespace()
            if scan.byte() is None: break
            start = scan.pos; scan.expect(123); fields = {}
            scan.whitespace()
            while scan.byte() != 125:
                begin = scan.pos; scan.string()
                key = scan.decode((begin,scan.pos),'__key__',256)
                if type(key) is not str or key in fields: raise ValueError('ambiguous JSONL key')
                scan.expect(58); scan.whitespace(); begin = scan.pos; scan.skip()
                fields[key] = (begin,scan.pos); scan.whitespace()
                if scan.byte() == 125: break
                scan.expect(44); scan.whitespace()
            scan.expect(125); span = (start,scan.pos)
            if 'id' not in fields: raise ValueError('source ID metadata missing')
            identity = scan.decode(fields['id'],'id',256)
            if type(identity) is not str or identity in seen: raise ValueError('duplicate/invalid source ID')
            seen.add(identity)
            if identity not in accepted_ids:
                excluded.append(identity)
                proof.append({'id':identity,'decoded_candidate_fields':[]})
                continue
            # Entire eligible original row stays out of band; DTO projection is later.
            raw = scan.raw(span)
            # Preserve numeric decimal lexemes for exact Fraction arithmetic;
            # never reinterpret binary floating point as the source value.
            row = json.loads(raw.decode('utf-8'), parse_float=str)
            if row['id'] != identity: raise ValueError('structural/decoded ID differs')
            rows[identity] = {'row':row,'source_span':list(span),
                              'record_sha256':hashlib.sha256(raw).hexdigest()}
    finally:
        scan.close()
    if set(rows) != set(accepted_ids): raise ValueError('accepted ID coverage incomplete')
    return rows, {'eligible_rows':len(rows),'excluded_rows':len(excluded),
                  'excluded_ids':excluded,'excluded_candidate_decode_proof':proof,
                  'seen_ID_set_sha256':hashlib.sha256(json.dumps(sorted(seen)).encode()).hexdigest()}


def _pin(root, spec, key):
    name,expected = spec[key]
    p = safe_path(root/DATA/spec['directory']/name,root/DATA/spec['directory'])
    if sha(p) != expected: raise ValueError('original synthetic source byte pin differs: '+key)
    return p


def build(root):
    root = Path(root).resolve(); questions,targets,provenance = [],[],[]
    scans,source_pins = {},{}
    for batch,spec in SOURCES.items():
        paths = {k:_pin(root,spec,k) for k in ('metadata','author','questions','independent','comparison')}
        metadata = json.loads(paths['metadata'].read_bytes())
        ids = metadata['accepted_ids']
        if type(ids) is not list or len(ids) != spec['count'] or len(set(ids)) != len(ids):
            raise ValueError('exact predeclared accepted ID metadata required')
        accepted = set(ids)
        if accepted & HELD: raise ValueError('held identity cannot become a candidate')
        if batch == 'b00':
            if metadata['quarantined_ids'] != [] or metadata['accepted_rows'] != 100:
                raise ValueError('Batch00 acceptance metadata differs')
        else:
            paths['lock'] = _pin(root,spec,'lock')
            lock = json.loads(paths['lock'].read_bytes())
            if (set(metadata['excluded_held_ids']) != HELD or set(lock['held_ids']) != HELD
                    or lock['stage'] != 'BLIND_LOCK_BEFORE_LABEL_ACCESS'):
                raise ValueError('accepted-only/independent lock membership differs')
        sources = {}
        for key in ('author','questions','independent','comparison'):
            sources[key],scans[batch+':'+key] = accepted_jsonl(paths[key],accepted)
            if key in ('author','questions') and scans[batch+':'+key]['excluded_rows']:
                raise ValueError('author/question export is not accepted-only')
        source_pins[batch] = {key:{'path':str(p.relative_to(root)),'sha256':sha(p)} for key,p in paths.items()}
        records_by_id = {r['id']:r for r in metadata.get('records',[])}
        for identity in ids:
            a,q,i,c = (sources[k][identity]['row'] for k in ('author','questions','independent','comparison'))
            if set(a) != AUTHOR_KEYS or set(q) != {'id','question'} or a['synthetic'] is not True:
                raise ValueError('exact authorized author/question-only schema required')
            question = model_question(QuestionInput(a['question']))
            qhash = text_sha(question)
            if q['question'] != question: raise ValueError('source/question-only text differs')
            if batch == 'b00':
                if (i['question'] != question or i['wording_flags'] != [] or c['disposition'] != 'accepted'
                        or type(c['findings']) is not list
                        or any(type(f) is not dict or f.get('blocking') is not False for f in c['findings'])):
                    raise ValueError('independent prose/acceptance receipt differs')
                if not c['checks'] or any(v is not True for v in c['checks'].values()):
                    raise ValueError('independent semantic/arithmetic checks not accepted')
                independent = exact_number(i['independent_exact_answer'])
                if exact_number(c['independent_exact_answer']) != independent or exact_number(c['exact_tree_value']) != independent:
                    raise ValueError('Batch00 numeric receipt differs')
                independence = i['basis']
            else:
                rec = records_by_id[identity]
                if (rec['question_text_utf8_sha256'] != qhash
                        or rec['record_utf8_no_newline_sha256'] != sources['author'][identity]['record_sha256']
                        or i['question_sha256'] != qhash or i['status'] != 'accepted'
                        or c['classification'] != 'accepted'):
                    raise ValueError('accepted-only source/independent receipt identity differs')
                if any(c[k] is not True for k in ('question_copy_matches','exact_numeric_match','author_tree_matches_proposed','unit_semantically_correct')):
                    raise ValueError('independent comparison rejects semantics/arithmetic')
                independent = exact_number(i['exact_answer'])
                if exact_number(c['independent_exact_answer']) != independent or exact_number(c['author_tree_exact_value']) != independent:
                    raise ValueError('B01-B03 exact numeric receipts differ')
                independence = 'Pinned independent question-only lock before label access; accepted-only manifest/comparison'
            # Audit-only exact arithmetic does not assert English meaning itself.
            if (arithmetic_expression(i['independent_expression']) != independent
                    or tree_value(a['operation_tree']) != independent
                    or exact_number(a['proposed_answer']['value']) != independent):
                raise ValueError('independent AST/tree/author outcome disagree')
            target = str(independent)  # one numeric constant, including reduced rational notation
            questions.append({'id':identity,'question':question})
            targets.append({'id':identity,'question_sha256':qhash,'numeric_target':target})
            provenance.append({'id':identity,'question_sha256':qhash,'numeric_target_sha256':text_sha(target),
                'source_origin':'explicitly-authorized-synthetic-TRAIN','author_model':a['author_model'],
                'source':{'path':source_pins[batch]['author']['path'],'sha256':source_pins[batch]['author']['sha256'],
                          'span':sources['author'][identity]['source_span'],'record_sha256':sources['author'][identity]['record_sha256']},
                'independent_answer':{'path':source_pins[batch]['independent']['path'],'sha256':source_pins[batch]['independent']['sha256'],
                                      'span':sources['independent'][identity]['source_span'],'record_sha256':sources['independent'][identity]['record_sha256']},
                'audit':{'path':source_pins[batch]['comparison']['path'],'sha256':source_pins[batch]['comparison']['sha256'],
                         'span':sources['comparison'][identity]['source_span'],'record_sha256':sources['comparison'][identity]['record_sha256']},
                'independent_derivation_basis':independence,'audit_only_tree_sha256':text_sha(json.dumps(a['operation_tree'],sort_keys=True)),
                'arithmetic_checked':True,'English_semantics':'pinned independent reviewer acceptance, not infallible local semantic proof',
                'model_input_fields':['question'],'notebook_tokens':0,'actual_token_admission':'PENDING','training_or_fit_release':False})
    if len(questions) != 396 or len({r['id'] for r in questions}) != 396:
        raise ValueError('exact combined accepted396 identity closure failed')
    return {'questions':questions,'targets':targets,'provenance':provenance,
            'source_pins':source_pins,'scans':scans}


def write_outputs(root,output):
    results = build(root);output=Path(output);output.mkdir(parents=True,exist_ok=False)
    artifacts = {
        'QUESTION-PACKET.json':{'schema':'sol.cloud.luna.accepted-questions.v1','rows':results['questions']},
        'NUMERIC-TARGETS.json':{'schema':'sol.cloud.luna.accepted-numeric-targets.v1','rows':results['targets']},
        'ROW-PROVENANCE.json':{'schema':'sol.cloud.luna.accepted-row-provenance.v1','rows':results['provenance']}}
    for name,payload in artifacts.items():
        (output/name).write_text(json.dumps(payload,sort_keys=True,indent=2,ensure_ascii=False)+'\n')
    manifest={'schema':'sol.cloud.luna.accepted396-source-binding.v1','accepted_rows':396,
        'source_pins':results['source_pins'],'metadata_first_scans':results['scans'],
        'accepted_ID_set_sha256':text_sha(json.dumps(sorted(r['id'] for r in results['questions']))),
        'packets':{n:{'path':str(output/n),'sha256':sha(output/n),'bytes':(output/n).stat().st_size} for n in artifacts},
        'model_input_fields':['question'],'synthetic_notebook_tokens':0,
        'target_scope':'independently accepted exact numeric constant+EOS; expressions/tree/code/units excluded',
        'real_tokenizer_admission':'PENDING','global_grouping_dedup':'separate owner, pending',
        'no_semantic_generalization_or_scientific_claim':True,'actual_user_day':False,
        'model_calls':0,'optimizer_calls':0,'fit_release':False}
    (output/'MANIFEST.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    return manifest


@dataclass(frozen=True)
class NumericExample:
    """Identity/target remain separate from the question-only input DTO."""
    id: str
    input: QuestionInput
    numeric_target: str
    question_sha256: str

    def model_input(self) -> str:
        return model_question(self.input)

    def target_text(self) -> str:
        return self.numeric_target


def load_verified_numeric_packet(question_path, question_sha256, target_path, target_sha256,
                                 manifest_path, manifest_sha256, approved_root):
    """Runtime opens only the three prepared pinned packets; no raw/audit source.

    This returns source-verified records, not tokenizer-qualified or fit-released
    rows. Exact current-tokenizer counts and reviewed fit release stay separate.
    """
    from sol_cloud_luna_admission_v1 import pinned_json
    manifest=pinned_json(manifest_path,manifest_sha256,approved_root)
    if (manifest.get('schema')!='sol.cloud.luna.accepted396-source-binding.v1'
            or manifest.get('accepted_rows')!=396 or manifest.get('model_input_fields')!=['question']
            or manifest.get('synthetic_notebook_tokens')!=0):
        raise ValueError('exact accepted396 metadata admission contract required')
    if (manifest['packets']['QUESTION-PACKET.json']['sha256']!=question_sha256
            or manifest['packets']['NUMERIC-TARGETS.json']['sha256']!=target_sha256):
        raise ValueError('externally pinned question/target/manifest tuple differs')
    questions=pinned_json(question_path,question_sha256,approved_root)
    targets=pinned_json(target_path,target_sha256,approved_root)
    if (type(questions)is not dict or set(questions)!={'schema','rows'}
            or questions['schema']!='sol.cloud.luna.accepted-questions.v1'
            or type(targets)is not dict or set(targets)!={'schema','rows'}
            or targets['schema']!='sol.cloud.luna.accepted-numeric-targets.v1'):
        raise ValueError('closed prepared question/target packet schemas required')
    if type(questions['rows'])is not list or type(targets['rows'])is not list:
        raise ValueError('typed prepared row lists required')
    by={}
    for target in targets['rows']:
        if type(target)is not dict or set(target)!={'id','question_sha256','numeric_target'}:
            raise ValueError('closed numeric constant target schema required')
        identity=target['id']
        if type(identity)is not str or identity in by or identity in HELD:
            raise ValueError('duplicate/held/non-string target identity')
        if type(target['numeric_target'])is not str or str(exact_number(target['numeric_target']))!=target['numeric_target']:
            raise ValueError('canonical exact numeric constant target required')
        by[identity]=target
    result=[];seen=set()
    for row in questions['rows']:
        if type(row)is not dict or set(row)!={'id','question'}:
            raise ValueError('closed question-only packet row schema required')
        identity=row['id']
        if type(identity)is not str or identity in seen or identity in HELD or identity not in by:
            raise ValueError('source/question/target membership or duplicate identity differs')
        dto=QuestionInput(row['question']);qhash=text_sha(model_question(dto))
        if by[identity]['question_sha256']!=qhash:
            raise ValueError('numeric target binds a different question')
        seen.add(identity)
        result.append(NumericExample(identity,dto,by[identity]['numeric_target'],qhash))
    if (len(result)!=396 or seen!=set(by)
            or text_sha(json.dumps(sorted(seen)))!=manifest['accepted_ID_set_sha256']):
        raise ValueError('exact396 accepted ID membership/digest differs')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=write_outputs(args.root,args.output)
    print(json.dumps({'accepted_rows':result['accepted_rows'],'manifest_sha256':sha(args.output/'MANIFEST.json'),
                      'packets':result['packets'],'model_calls':0,'optimizer_calls':0},sort_keys=True))
