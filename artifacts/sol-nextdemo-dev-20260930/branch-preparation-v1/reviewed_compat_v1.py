"""Lossless CPU preparation projection of the actual reviewed Luna packet.

Original bytes retained. This projection is not tokenizer/global admission,
training eligibility, GPU release, a new source writer, or POC runtime change.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,zipfile
from pathlib import Path
import branch_source_v1 as loader

ARCHIVE_SHA='3f7a957c4186ab9f6b5d41a5c0701878e47a892d5825a9c70f2452728ffb89e4'
ASSIGNMENTS={'TRAIN32':'TRAIN','EXPERIENCE16':'EXPERIENCE','TEST8':'TEST'}
STAGES={'initial':'initial','corrected':'corrected','missing':'missing_fact'}
REJECTED=['NX-P04','NX-P05']
MEMBERS=('notes.json','independent_targets.json','semantic_review.json',
    'independent_derivations.json','independent_derivations_freeze.json',
    'derive_independently.py','finalize_independent_review.py','advisory_targets.json',
    'verification_hashes.json')

def byte_sha(raw):return hashlib.sha256(raw).hexdigest()
def json_bytes(value):return (loader.canonical(value)+'\n').encode('utf8')
def relative_pin(name,raw):return {'path':'evidence/'+name,'sha256':byte_sha(raw)}

def project(archive_path,archive_sha256=ARCHIVE_SHA):
    raw_archive=Path(archive_path).read_bytes()
    if archive_sha256!=ARCHIVE_SHA or byte_sha(raw_archive)!=ARCHIVE_SHA:
        raise ValueError('exact externally approved reviewed archive required')
    with zipfile.ZipFile(archive_path) as z:
        if set(z.namelist())!=set(MEMBERS):raise ValueError('unexpected reviewed archive members')
        raw={name:z.read(name) for name in MEMBERS}
    hashes=json.loads(raw['verification_hashes.json'])
    for name,pin in hashes['files'].items():
        if name not in raw or byte_sha(raw[name])!=pin:raise ValueError('review evidence hash changed')
    source=json.loads(raw['notes.json']);labels=json.loads(raw['independent_targets.json'])
    review=json.loads(raw['semantic_review.json']);deriv=json.loads(raw['independent_derivations.json'])
    freeze=json.loads(raw['independent_derivations_freeze.json'])
    if (source['schema']!='sol.nextdemo.branch-numeric-notes.v1' or
        source['origin']!=loader.ORIGIN or source['source_pool']!=loader.POOL or
        labels['schema']!='sol.nextdemo.branch-numeric-independent-targets.v1' or
        review['schema']!='sol.nextdemo.branch-numeric-semantic-review.v1' or
        review['rejected_episode_ids']!=REJECTED or
        review['accepted_assignment_counts']!={'TRAIN32':32,'EXPERIENCE16':14,'TEST8':8} or
        labels['source_sha256']!=byte_sha(raw['notes.json']) or
        review['source_sha256']!=byte_sha(raw['notes.json']) or
        deriv['source_sha256']!=byte_sha(raw['notes.json']) or deriv['advisory_targets_read'] is not False or
        review['pre_advisory_derivations_sha256']!=byte_sha(raw['independent_derivations.json']) or
        review['pre_advisory_freeze_sha256']!=byte_sha(raw['independent_derivations_freeze.json']) or
        freeze['notes.json']!=byte_sha(raw['notes.json']) or
        freeze['independent_derivations.json']!=byte_sha(raw['independent_derivations.json']) or
        freeze['semantic_accepted']!=54 or freeze['semantic_rejected']!=2):
        raise ValueError('actual independent source/freeze/54accepted boundary differs')
    checks=review['checks']
    for name in ('all_metadata_givens_match_literal_parsing',
        'all_28_adjacent_pairs_identical_questions','all_pairs_have_same_assignment_and_family',
        'all_56_missing_cases_have_distinct_constructive_witnesses',
        'no_within_world_target_numbers_in_supplied_notes_or_corrections',
        'no_within_world_intermediate_numbers_in_supplied_notes_or_corrections'):
        if checks[name] is not True:raise ValueError('recorded independent check absent: '+name)
    expected=loader.expected_ids();old_assignments={ASSIGNMENTS[k]:v for k,v in source['assignments'].items()}
    if old_assignments!=expected:raise ValueError('original source assignments differ')
    by_deriv={e['id']:e for e in deriv['episodes']}
    by_case={(c['episode_id'],c['stage']):c for c in labels['cases']}
    if len(by_deriv)!=56 or len(by_case)!=168:raise ValueError('original evidence extent differs')
    normalized={'schema':source['schema'],'origin':source['origin'],'source_pool':source['source_pool'],
        'assignments':expected,'episodes':[]}
    provenance={'schema':'sol.nextdemo.reviewed-compat-provenance.v1',
        'original_archive_sha256':ARCHIVE_SHA,'original_notes_sha256':byte_sha(raw['notes.json']),
        'original_independent_targets_sha256':byte_sha(raw['independent_targets.json']),
        'assignment_mapping':ASSIGNMENTS,'stage_mapping':STAGES,'rejected_ids':REJECTED,
        'original_source_retained':True,'source_repair_or_redraw':False,'episodes':{},'cases':{},
        'writer_model_version':'NOT RECORDED; writer_model field preserves literal source attribution only',
        'reviewer_personal_identity':'NOT RECORDED; computational verifier/review artifacts are explicitly pinned',
        'tokenizer_check':'PENDING','external_global_exclusions':'PENDING'}
    witness_map={};field_hashes={};approved=[];accepted_numeric_count=0
    projected_targets=[]
    review_pin=relative_pin('semantic_review.json',raw['semantic_review.json'])
    for e in source['episodes']:
        original_id=e['id'];d=by_deriv[original_id]
        if d['literal_input_sha256']!=loader.digest({k:e[k] for k in ('id','question','notes','correction','missing_notes')}):
            raise ValueError('literal derivation input digest differs')
        if type(e['lineage']) is not str or not e['lineage'].strip():raise ValueError('documented literal lineage absent')
        ne=copy.deepcopy(e);ne['assignment']=ASSIGNMENTS[e['assignment']]
        for field,count in (('notes',3),('missing_notes',2)):
            values=e[field]
            if type(values) is not list or len(values)!=count or any(type(v) is not str or not v.strip() for v in values):
                raise ValueError('exact literal source note list required')
            ne[field]='\n'.join(values)
        ne['lineage']={'writer_model':e['lineage'],
            'source_instance_id':source['source_pool']+'/'+original_id+'@sha256:'+byte_sha(raw['notes.json'])}
        normalized['episodes'].append(ne)
        provenance['episodes'][original_id]={'original_episode':copy.deepcopy(e),
            'original_episode_canonical_sha256':loader.digest(e),
            'normalized_episode_canonical_sha256':loader.digest(ne),
            'literal_notes_join':'newline; original list elements and order unchanged',
            'writer_reference':{'kind':'literal-source-attribution','value':e['lineage'],'model_version':None},
            'source_reference':{'source_pool':source['source_pool'],'original_episode_id':original_id,
                'original_assignment':e['assignment'],'original_source_sha256':byte_sha(raw['notes.json'])},
            'semantic_status':d['semantic_status'],'admitted_numeric_source':original_id not in REJECTED}
        if original_id in REJECTED:
            if d['semantic_status']!='reject_ambiguous':raise ValueError('rejected world review changed')
            continue
        if d['semantic_status']!='accept' or d['missing_underdetermined'] is not True:
            raise ValueError('selected world lacks semantic/answerability evidence')
        approved.append(original_id)
        field_hashes[original_id]={f:loader.digest(ne[f]) for f in loader.FIELDS-{'id','assignment','family'}}
        changed='items_per_box' if e['family']=='I' else 'first_batch_items'
        completion_key='items_in_each_container' if e['family']=='I' else 'first_batch_items'
        ws=d['missing_witnesses']
        if type(ws) is not list or len(ws)!=2:raise ValueError('two recorded independent missing witnesses required')
        witness_map[original_id]={}
        for name,w in zip(('first','second'),ws):
            completion=w['completion'][completion_key]
            if e['family']=='P' and w['completion'].get('equal_distribution_of_all_items') is not True:
                raise ValueError('packing witness lacks complete distribution premise')
            observed=loader.numeric_witness_value(e['family'],{**e['givens'],changed:completion})
            if observed!=w['answer']:raise ValueError('recorded witness answer does not reproduce')
            witness_map[original_id][name]=completion
        if ws[0]['answer']==ws[1]['answer']:raise ValueError('missing given not independently underdetermined')
        for old_stage,new_stage in STAGES.items():
            c=by_case[(original_id,old_stage)]
            numeric=old_stage!='missing';value=c['numeric_target']
            if (c['semantic_status']!='accept' or c['episode_rejected'] is not False or
                c['independently_derived'] is not True or c['answerability'] is not numeric):
                raise ValueError('independently accepted case evidence absent')
            if numeric:
                given=e['givens'] if old_stage=='initial' else e['corrected_givens']
                if value!=str(loader.numeric_value(e['family'],given)) or value!=str(d[old_stage+'_target']):
                    raise ValueError('accepted independent numeric value changed')
                accepted_numeric_count+=1
            elif value is not None:raise ValueError('missing-given case must not have numeric label')
            projected_targets.append({'episode_id':original_id,'stage':new_stage,'answerability':numeric,
                'numeric_target':value,'verification_pin':review_pin,'training_eligible':False})
            provenance['cases'][original_id+':'+new_stage]={
                'original_stage':old_stage,'normalized_stage':new_stage,
                'original_assignment':c['assignment'],'normalized_assignment':ASSIGNMENTS[c['assignment']],
                'independent_target_row_canonical_sha256':loader.digest(c),
                'original_numeric_target':value,'numeric_value_unchanged':True,
                'original_training_eligible_flag':c['training_eligible'],
                'projected_training_eligible':False,'verification_evidence':review_pin,
                'pre_advisory_derivation_evidence':relative_pin('independent_derivations.json',raw['independent_derivations.json'])}
    if accepted_numeric_count!=108 or len(projected_targets)!=162 or len(approved)!=54:
        raise ValueError('exact accepted projection extent required')
    targets={'schema':'sol.nextdemo.branch-numeric-targets.v1','source_pool':loader.POOL,'cases':projected_targets}
    receipt={'schema':'sol.nextdemo.branch-numeric-check.v1','source_pool':loader.POOL,
        'notes_sha256':byte_sha(json_bytes(normalized)),'targets_sha256':byte_sha(json_bytes(targets)),
        'approved_ids':approved,'independent_verifier_identity':
            'derive_independently.py@sha256:'+byte_sha(raw['derive_independently.py'])+
            ';finalize_independent_review.py@sha256:'+byte_sha(raw['finalize_independent_review.py']),
        'review_pin':review_pin,
        'source_exclusion_metadata_pins':[review_pin],
        'per_field_sha256':field_hashes,'literal_wording_checked':True,'numeric_labels_checked':True,
        'missing_fact_witnesses':witness_map,'no_answer_or_intermediate_checked':True,
        'assignments_checked':True,'rejected_ids':REJECTED,'rejection_review_pin':review_pin}
    qualifications={'schema':'sol.nextdemo.reviewed-compat-qualification.v1',
        'status':'CPU NORMALIZATION VERIFIED; EXECUTION HELD',
        'supported_numeric_values_preserved':108,'numeric_mismatches':0,'accepted_worlds':54,
        'accepted_assignment_counts':{'TRAIN':32,'EXPERIENCE':14,'TEST':8},'rejected_ids':REJECTED,
        'internal_assignment_review_checked':True,'external_global_exclusions_checked':False,
        'actual_frozen_tokenizer_checked':False,'writer_model_version_recorded':False,
        'reviewer_personal_identity_recorded':False,'computational_verifier_artifact_identity_pinned':True,
        'training_eligible':False,'execution_eligible':False,'model_calls':0,
        'receipt_source_exclusion_metadata_scope':'published internal split/rejection metadata ONLY; external exclusions not supplied or checked',
        'missing_evidence':['selected frozen tokenizer/caps/IDs audit','original-source/global exclusion metadata and collision audit',
            'exact writer model/version if that is mandatory for final origin admission','named reviewer identity if final policy requires it',
            'selected closed checkpoint/branch/root execution release'],
        'witness_scope':'recorded positive feasible literal completions; TRAIN generator ranges unchanged; witnesses never supervised'}
    return normalized,targets,receipt,provenance,qualifications,raw

def check_projection(notes,targets,receipt):
    return loader.load_source(notes,targets,receipt,
        {'notes':byte_sha(json_bytes(notes)),'targets':byte_sha(json_bytes(targets))},preparation_only=True)

def initial_only_selection(inputs,labels):
    """Prospective branch: untouched initial facts, TRAIN/TEST only; no correction claim."""
    selected=[r for r in inputs if r['stage']=='initial' and r['assignment'] in ('TRAIN','TEST')]
    keys={(r['episode_id'],r['stage']) for r in selected}
    selected_labels=[c for c in labels if (c['episode_id'],c['stage']) in keys]
    if len(selected)!=40 or len(selected_labels)!=40 or any(c['answerability'] is not True or c['numeric_target'] is None for c in selected_labels):
        raise ValueError('exact 32 TRAIN + 8 TEST supported initial cases required')
    return selected,selected_labels

def export(archive_path,out,archive_sha256=ARCHIVE_SHA,*,stage_selection='all-audit'):
    if stage_selection not in ('all-audit','initial-only-v2'):raise ValueError('unsupported prospective stage selection')
    out=Path(out).resolve()
    if out.exists():raise ValueError('new compatibility output only; no source/evidence overwrite')
    notes,targets,receipt,provenance,qualifications,raw=project(archive_path,archive_sha256)
    inputs,labels=check_projection(notes,targets,receipt)
    out.mkdir(parents=True);(out/'evidence').mkdir()
    for name,data in raw.items():(out/'evidence'/name).write_bytes(data)
    for name,data in [('NORMALIZED-NOTES.json',notes),('NORMALIZED-TARGETS.json',targets),
        ('NORMALIZED-VERIFICATION.json',receipt),('PROVENANCE-MAPPING.json',provenance),('QUALIFICATION.json',qualifications)]:
        (out/name).write_bytes(json_bytes(data))
    if stage_selection=='initial-only-v2':inputs,labels=initial_only_selection(inputs,labels)
    manifest=loader.export_new(out/'candidate-export',inputs,labels,
        {'notes':receipt['notes_sha256'],'targets':receipt['targets_sha256'],
         'verification':byte_sha(json_bytes(receipt)),
         'original_notes':byte_sha(raw['notes.json']),'original_independent_targets':byte_sha(raw['independent_targets.json']),
         'original_reviewed_archive':ARCHIVE_SHA})
    if stage_selection=='initial-only-v2':
        train_ids=[r['id'] for r in inputs if r['assignment']=='TRAIN']
        manifest.update(stage_selection='initial-only-v2',candidate_TRAIN_schedule=train_ids*4,
            candidate_EXPERIENCE_ids=[],selected_case_counts={'TRAIN':32,'EXPERIENCE':0,'TEST':8},
            complete_source_audit_retained=True,correction_claim=False,missing_fact_claim=False,
            candidate_fit_spec={'seeds':2,'placements':['notebook','inline'],'updates_per_fit':128,
                'passes':4,'parent':'same closed parent40 model within seed','optimizer':'identical fresh Adam within seed; no parent optimizer carryover',
                'learning_rate':0.001,'weight_decay':0,'RNG_and_order':'matched within seed',
                'evaluation_calls':64,'evaluation':'4 fits x 8 initial TEST questions x own placement history present/removed',
                'cross_placement_scoring':False,'all_TEST_world_variants_consumed_together':True,
                'admission_and_execution':'ROOT/SOLEOWNER PENDING; all rows remain ineligible'})
        (out/'candidate-export'/'EXPORT-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return qualifications,manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reviewed-zip',required=True);p.add_argument('--sha256',required=True);p.add_argument('--out',required=True);p.add_argument('--stage-selection',choices=('all-audit','initial-only-v2'),default='all-audit')
    a=p.parse_args();q,m=export(a.reviewed_zip,a.out,a.sha256,stage_selection=a.stage_selection)
    print(json.dumps({'status':q['status'],'accepted_worlds':54,'candidate_case_counts':m['counts'],
        'numeric_values_preserved':108,'training_eligible':False,'tokenizer_checked':False,'global_exclusions_checked':False}))
