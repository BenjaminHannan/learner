"""CPU-only checked source loader/exporter for the frozen 56-world contract.

No Torch, model, optimizer, network, tokenizer download or dataset repair.
Arithmetic verifies offline numeric labels only; model_inputs exports literal
question/context and never supplies structured givens, targets or this verifier.
Exports are preparation candidates, not a training/evaluation release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata

POOL = 'luna-noteuse-branch-source-v1'
ORIGIN = 'Luna-authored-numeric-wordproblem'
SPLITS = {'TRAIN': ('NT', 16), 'EXPERIENCE': ('NX', 8), 'TEST': ('NE', 4)}
FIELDS = {'id', 'assignment', 'family', 'question', 'notes', 'correction',
          'missing_notes', 'givens', 'corrected_givens', 'lineage'}
PROTECTED = ('uncle-questions', 'readpanel320', 'sealed-panels', 'sealed-user',
             'sealed-blind', 'dev100', 'stop88', 'reserved', '/blind/')
STAGES = ('initial', 'corrected', 'missing_fact')
REJECTED_IDS = ['NX-P04', 'NX-P05']


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value):
    raw = value.encode('utf8') if type(value) is str else canonical(value).encode('utf8')
    return hashlib.sha256(raw).hexdigest()


def safe(path):
    p = Path(path)
    for candidate in (p, p.resolve()):
        text = '/' + str(candidate).replace('\\', '/').lower().strip('/') + '/'
        if any(term in text for term in PROTECTED):
            raise ValueError('protected path refused before reading')
    return p.resolve()


def read_pin(path, sha):
    if type(sha) is not str or not re.fullmatch('[0-9a-f]{64}', sha):
        raise ValueError('external SHA256 required')
    raw = safe(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError('source pin differs')
    return json.loads(raw)


def pin_shape(value):
    return (type(value) is dict and set(value) == {'path', 'sha256'} and
            type(value['path']) is str and bool(value['path']) and
            type(value['sha256']) is str and bool(re.fullmatch('[0-9a-f]{64}', value['sha256'])))


def expected_ids():
    return {split: [f'{prefix}-{family}{i:02d}' for family in ('I', 'P') for i in range(n)]
            for split, (prefix, n) in SPLITS.items()}


def replay_world_ids():
    """Balanced eight-world proposal, frozen before outcomes, not a release."""
    return [f'NX-{family}{i:02d}' for family in ('I', 'P') for i in range(4)]


def normalized_record(question, history):
    normalize = lambda s: ' '.join(unicodedata.normalize('NFKC', s).casefold().split())
    return digest({'question': normalize(question), 'history': normalize(history)})


def numeric_value(family, givens):
    keys = {'boxes', 'items_per_box', 'removed_items'} if family == 'I' else {'first_batch_items', 'second_batch_items', 'number_of_packs'}
    if type(givens) is not dict or set(givens) != keys or any(type(v) is not int for v in givens.values()):
        raise ValueError('exact bounded integer givens required')
    if family == 'I':
        b, p, r = givens['boxes'], givens['items_per_box'], givens['removed_items']
        if not (2 <= b <= 9 and 3 <= p <= 15 and 1 <= r <= 10 and r < b*p):
            raise ValueError('inventory bounds differ')
        return b*p-r
    if family != 'P':
        raise ValueError('family must be I/P')
    a, b, n = givens['first_batch_items'], givens['second_batch_items'], givens['number_of_packs']
    if not (4 <= a <= 60 and 4 <= b <= 60 and 2 <= n <= 6 and (a+b) % n == 0):
        raise ValueError('equal-packing bounds/exact division differ')
    return (a+b)//n


def numeric_witness_value(family, givens):
    """Offline literal missing-fact witnesses; not TRAIN generator ranges.

    Fixed disclosed givens were already range-checked by numeric_value. Only the
    omitted quantity varies here, using the recorded independent witnesses.
    Positive feasible inventories and exact complete packing are required.
    """
    keys = ({'boxes', 'items_per_box', 'removed_items'} if family == 'I' else
            {'first_batch_items', 'second_batch_items', 'number_of_packs'})
    if type(givens) is not dict or set(givens) != keys or any(type(v) is not int for v in givens.values()):
        raise ValueError('exact integer literal witness required')
    if family == 'I':
        b,p,r = givens['boxes'],givens['items_per_box'],givens['removed_items']
        if b < 1 or p < 1 or r < 0 or r > b*p:
            raise ValueError('infeasible inventory witness')
        return b*p-r
    if family != 'P':
        raise ValueError('family must be I/P')
    a,b,n = givens['first_batch_items'],givens['second_batch_items'],givens['number_of_packs']
    if a < 1 or b < 1 or n < 1 or (a+b) % n:
        raise ValueError('infeasible exact equal-packing witness')
    return (a+b)//n


def model_inputs(row, placement):
    """Only literal strings cross the model boundary. No labels or computation."""
    if placement == 'notebook':
        return {'question': row['question'], 'context': row['history']}
    if placement == 'inline':
        return {'question': row['history'] + '\n' + row['question'], 'context': ''}
    raise ValueError('supervised placement must retain full information; no empty-note arm')


def load_source(notes, targets, receipt, pins, *, preparation_only=False):
    ids = expected_ids(); all_ids = [identity for values in ids.values() for identity in values]
    accepted_ids = [identity for identity in all_ids if identity not in REJECTED_IDS]
    if (type(notes) is not dict or set(notes) != {'schema', 'origin', 'source_pool', 'assignments', 'episodes'} or
            notes['schema'] != 'sol.nextdemo.branch-numeric-notes.v1' or notes['origin'] != ORIGIN or
            notes['source_pool'] != POOL or notes['assignments'] != ids):
        raise ValueError('exact independently assigned Luna branch notes required')
    if (type(targets) is not dict or set(targets) != {'schema', 'source_pool', 'cases'} or
            targets['schema'] != 'sol.nextdemo.branch-numeric-targets.v1' or targets['source_pool'] != POOL):
        raise ValueError('separate branch numeric targets required')
    required = {'schema', 'source_pool', 'notes_sha256', 'targets_sha256', 'approved_ids',
                'independent_verifier_identity', 'review_pin', 'source_exclusion_metadata_pins',
                'per_field_sha256', 'literal_wording_checked', 'numeric_labels_checked',
                'missing_fact_witnesses', 'no_answer_or_intermediate_checked', 'assignments_checked',
                'rejected_ids', 'rejection_review_pin'}
    if type(receipt) is not dict or set(receipt) != required or receipt['schema'] != 'sol.nextdemo.branch-numeric-check.v1':
        raise ValueError('complete independent branch verification receipt required')
    if (receipt['source_pool'] != POOL or receipt['notes_sha256'] != pins['notes'] or
            receipt['targets_sha256'] != pins['targets'] or receipt['approved_ids'] != accepted_ids or
            receipt['rejected_ids'] != REJECTED_IDS or not pin_shape(receipt['rejection_review_pin'])):
        raise ValueError('branch receipt source pins/approved assignment differ')
    for flag in ('literal_wording_checked', 'numeric_labels_checked', 'no_answer_or_intermediate_checked', 'assignments_checked'):
        if receipt[flag] is not True:
            raise ValueError('independent check missing: ' + flag)
    if type(receipt['independent_verifier_identity']) is not str or not receipt['independent_verifier_identity'].strip() or not pin_shape(receipt['review_pin']):
        raise ValueError('independent verifier identity/review pin required')
    exclusions = receipt['source_exclusion_metadata_pins']
    if type(exclusions) is not list or not exclusions or not all(pin_shape(p) for p in exclusions):
        raise ValueError('source exclusion metadata references required; owner qualification still pending')
    if type(notes['episodes']) is not list or len(notes['episodes']) != 56 or [e.get('id') for e in notes['episodes']] != all_ids:
        raise ValueError('exact ordered 56 worlds required; no replacement/topup')
    if type(targets['cases']) is not list or len(targets['cases']) != 162:
        raise ValueError('exact independently accepted54-world targets required; rejected cases excluded')
    expected_cases = [(identity, stage) for identity in accepted_ids for stage in STAGES]
    if [(c.get('episode_id'), c.get('stage')) for c in targets['cases']] != expected_cases:
        raise ValueError('duplicate, missing, unknown or reordered target case')
    target_by_case = {(c['episode_id'], c['stage']): c for c in targets['cases']}
    inputs = []; labels = []; source_ids = set(); tuples = {}; records = set(); by_id = {}
    for index, e in enumerate(notes['episodes']):
        if type(e) is not dict or set(e) != FIELDS:
            raise ValueError('exact literal episode fields required')
        split = next(split for split in ids if e['id'] in ids[split])
        family = e['id'][3]
        if e['assignment'] != split or e['family'] != family:
            raise ValueError('episode split/family differs from reserved identity')
        if e['id'] in REJECTED_IDS:
            continue  # Preserve authored source, never repair/redraw/admit these worlds.
        for field in ('question', 'notes', 'correction', 'missing_notes'):
            if type(e[field]) is not str or not e[field].strip():
                raise ValueError('nonempty literal numeric word-problem text required')
        if len(e['question'].split()) > 20 or re.search(r'\d', e['question']):
            raise ValueError('base query exceeds20words or contains numerical instance clues')
        lineage = e['lineage']
        if (type(lineage) is not dict or set(lineage) != {'writer_model', 'source_instance_id'} or
                any(type(v) is not str or not v.strip() for v in lineage.values()) or lineage['source_instance_id'] in source_ids):
            raise ValueError('unique source-instance lineage required; same writer model is allowed')
        source_ids.add(lineage['source_instance_id'])
        old, new = e['givens'], e['corrected_givens']
        answers = [numeric_value(family, old), numeric_value(family, new)]
        changed = 'items_per_box' if family == 'I' else 'first_batch_items'
        if [k for k in sorted(old) if old[k] != new[k]] != [changed]:
            raise ValueError('exactly one declared given must change')
        numbers = lambda text: [int(n) for n in re.findall(r'(?<!\w)-?\d+(?!\w)', text)]
        if sorted(numbers(e['notes'])) != sorted(old.values()) or sorted(numbers(e['missing_notes'])) != sorted(v for k, v in old.items() if k != changed):
            raise ValueError('literal givens or missing-fact isolation differ')
        correction = numbers(e['correction'])
        if new[changed] not in correction or not set(correction).issubset({old[changed], new[changed]}):
            raise ValueError('correction contains missing or extra numerical information')
        for field in FIELDS - {'id', 'assignment', 'family'}:
            if receipt['per_field_sha256'].get(e['id'], {}).get(field) != digest(e[field]):
                raise ValueError('independent literal-field hash differs')
        for g in (old, new):
            fingerprint = digest({'family': family, 'givens': g})
            if fingerprint in tuples:
                raise ValueError('given tuple reused across worlds/stages/assignments')
            tuples[fingerprint] = split
        witness = receipt['missing_fact_witnesses'].get(e['id'])
        if type(witness) is not dict or set(witness) != {'first', 'second'}:
            raise ValueError('independent underdetermination witness required')
        possible = []
        for completion in witness.values():
            if type(completion) is not int:
                raise ValueError('bounded integer missing-given witness required')
            possible.append((numeric_witness_value if preparation_only else numeric_value)(family, {**old, changed: completion}))
        if possible[0] == possible[1]:
            raise ValueError('missing given must change possible numeric answer')
        histories = [e['notes'], e['notes'] + '\n' + e['correction'], e['missing_notes']]
        by_id[e['id']] = e
        for stage_index, stage in enumerate(STAGES):
            target = target_by_case[(e['id'], stage)]
            if set(target) != {'episode_id', 'stage', 'answerability', 'numeric_target', 'verification_pin', 'training_eligible'} or not pin_shape(target['verification_pin']):
                raise ValueError('exact independently verified target fields required')
            numeric = stage != 'missing_fact'
            eligible = numeric and split in ('TRAIN', 'EXPERIENCE')
            if (target['answerability'] is not numeric or target['training_eligible'] is not (False if preparation_only else eligible) or
                    target['numeric_target'] != (str(answers[stage_index]) if numeric else None)):
                raise ValueError('numeric target/answerability or TEST/missing eligibility differs')
            row = dict(id=e['id']+':'+stage, episode_id=e['id'], assignment=split, stage=stage,
                       question=e['question'], history=histories[stage_index], origin=ORIGIN,
                       lineage=lineage, source_sha256=digest(e), actual_user_day=False,
                       training_eligible=False, declared_source_eligibility=eligible,
                       execution_eligible=False, tokenizer_admission='PENDING',
                       global_source_qualification='OWNER_PENDING')
            record_hash = normalized_record(row['question'], row['history'])
            if record_hash in records:
                raise ValueError('normalized question/history duplicate')
            records.add(record_hash); row['normalized_record_sha256'] = record_hash
            # Exact parity is created mechanically, never by semantic rewriting.
            row['inline_sha256'] = digest(model_inputs(row, 'inline')['question'])
            row['notebook_history_sha256'] = digest(row['history'])
            inputs.append(row); labels.append(dict(target))
    for split, (prefix, n) in SPLITS.items():
        for family in ('I', 'P'):
            for index in range(0, n, 2):
                if f'{prefix}-{family}{index:02d}' in REJECTED_IDS:
                    continue
                pair = [by_id[f'{prefix}-{family}{i:02d}'] for i in (index, index+1)]
                if pair[0]['question'] != pair[1]['question']:
                    raise ValueError('paired worlds must share byte-identical base query')
                values = [numeric_value(family, e[k]) for e in pair for k in ('givens', 'corrected_givens')]
                literal = {v for e in pair for k in ('givens', 'corrected_givens') for v in e[k].values()}
                if len(set(values)) != 4 or set(values) & literal:
                    raise ValueError('pair targets must be distinct and unequal to pair givens; no global answer uniqueness')
    return inputs, labels


def candidate_schedule(inputs, labels, assignment):
    """Unreleased candidate IDs only; TEST and missing facts never train."""
    if assignment not in ('TRAIN', 'EXPERIENCE'):
        raise ValueError('TEST must never enter adaptation/replay schedules')
    by_case = {(c['episode_id'], c['stage']): c for c in labels}
    rows = [r for r in inputs if r['assignment'] == assignment and r['stage'] != 'missing_fact' and
            (assignment != 'EXPERIENCE' or r['episode_id'] in replay_world_ids())]
    if any(r['declared_source_eligibility'] is not True or
            type(by_case[(r['episode_id'], r['stage'])]['training_eligible']) is not bool for r in rows):
        raise ValueError('unadmitted supervised candidate')
    return [r['id'] for r in rows] * (2 if assignment == 'TRAIN' else 1)


def token_check(inputs, labels, tokenizer, tokenizer_sha256, *, actual_frozen_tokenizer=False):
    """Owner invokes this with the selected frozen tokenizer; no model calls.

    Doubles can exercise rejection but cannot yield a qualified admission.
    Global exclusions and execution release are still separate owner checks.
    """
    if not re.fullmatch('[0-9a-f]{64}', tokenizer_sha256):
        raise ValueError('selected tokenizer provenance digest required')
    target_by_case = {(c['episode_id'], c['stage']): c for c in labels}
    audit = {}
    for row in inputs:
        encode = lambda text: tokenizer.encode(text, add_special_tokens=False)
        notebook = model_inputs(row, 'notebook'); inline = model_inputs(row, 'inline')
        q, h, full = encode(notebook['question']), encode(notebook['context']), encode(inline['question'])
        if not q or len(q)+1 > 48 or len(h) > 512 or not full or len(full)+1 > 48:
            raise ValueError('actual query/INLINE48inclEOS or notebook512 exceeded; never truncate')
        target = target_by_case[(row['episode_id'], row['stage'])]['numeric_target']
        target_ids = encode(target) if target is not None else None
        if target_ids is not None and (not target_ids or len(target_ids)+1 > 64):
            raise ValueError('numeric target token cap exceeded')
        audit[row['id']] = dict(question_tokens_including_EOS=len(q)+1, inline_tokens_including_EOS=len(full)+1,
                               notebook_tokens=len(h), target_tokens_including_EOS=len(target_ids)+1 if target_ids is not None else None,
                               inline_sha256=row['inline_sha256'], history_sha256=row['notebook_history_sha256'])
    return dict(schema='sol.nextdemo.branch-token-check.v1', tokenizer_sha256=tokenizer_sha256,
                actual_frozen_tokenizer=actual_frozen_tokenizer is True, cases=audit,
                execution_eligible=False, global_source_qualification='OWNER_PENDING')


def export_new(directory, inputs, labels, source_pins):
    directory = safe(directory)
    if directory.exists():
        raise ValueError('new export directory required; do not replace evidence')
    directory.mkdir(parents=True)
    hashes = {}; counts = {}
    for split in SPLITS:
        rows = [r for r in inputs if r['assignment'] == split]
        targets = [c for c in labels if c['episode_id'] in expected_ids()[split]]
        counts[split] = len(rows)
        for suffix, values in (('inputs', rows), ('targets', targets)):
            path = directory / (split+'-'+suffix+'.jsonl')
            raw = ''.join(canonical(v)+'\n' for v in values).encode('utf8')
            with path.open('xb') as stream: stream.write(raw)
            hashes[path.name] = hashlib.sha256(raw).hexdigest()
    manifest = dict(schema='sol.nextdemo.branch-export.v1', source_pins=source_pins, counts=counts,
        sha256=hashes, candidate_TRAIN_schedule=candidate_schedule(inputs, labels, 'TRAIN'),
        candidate_EXPERIENCE_ids=candidate_schedule(inputs, labels, 'EXPERIENCE'),
        authored_world_counts={'TRAIN':32, 'EXPERIENCE':16, 'TEST':8},
        accepted_world_counts={'TRAIN':32, 'EXPERIENCE':14, 'TEST':8},
        rejected_ids=REJECTED_IDS, balanced_replay_world_ids=replay_world_ids(),
        execution_eligible=False, training_eligible=False, actual_user_day=False,
        tokenizer_admission='PENDING', global_source_qualification='OWNER_PENDING',
        write_claim='Host source capture only; model-selected write metrics unavailable/null',
        release='Root/soleowner must finish actual frozen token and exclusion admission, select branch and authorize execution.')
    with (directory/'EXPORT-MANIFEST.json').open('x') as stream: json.dump(manifest, stream, indent=2)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('notes', 'targets', 'verification'):
        parser.add_argument('--'+name, required=True)
        parser.add_argument('--'+name+'-sha256', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    pins = {name: getattr(args, name+'_sha256') for name in ('notes', 'targets', 'verification')}
    notes = read_pin(args.notes, pins['notes']); targets = read_pin(args.targets, pins['targets'])
    receipt = read_pin(args.verification, pins['verification'])
    inputs, labels = load_source(notes, targets, receipt, pins)
    manifest = export_new(args.out, inputs, labels, pins)
    print(json.dumps({'counts': manifest['counts'], 'execution_eligible': False, 'tokenizer_admission': 'PENDING'}))


if __name__ == '__main__':
    main()
