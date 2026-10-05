"""Bounded human-authored development episodes; never training material.

Expected answers stay in the scorer. The inference backend receives only the
literal question, source notebook text and explicitly disclosed intervention.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

try:
    from .sol_nextdemo_runtime_v1 import Runtime, read_pinned, safe_path, text_sha, INTERVENTIONS
except ImportError:
    from sol_nextdemo_runtime_v1 import Runtime, read_pinned, safe_path, text_sha, INTERVENTIONS


def validate_fixture(packet):
    if type(packet) is not dict or set(packet) != {'schema', 'origin', 'source_ref', 'training_eligible', 'episodes'}:
        raise ValueError('exact development fixture fields required')
    if packet['schema'] != 'sol.nextdemo.human-dev.v1' or packet['origin'] != 'human-authored-development' or packet['training_eligible'] is not False:
        raise ValueError('human development-only provenance declaration required')
    if type(packet['source_ref']) is not str or not packet['source_ref'].strip():
        raise ValueError('human source reference required; declaration is not independent attestation')
    if type(packet['episodes']) is not list or not 1 <= len(packet['episodes']) <= 2:
        raise ValueError('one or two episodes only')
    identities = set()
    for episode in packet['episodes']:
        if type(episode) is not dict or set(episode) != {'id', 'events'}:
            raise ValueError('exact episode fields required')
        if type(episode['id']) is not str or not episode['id'] or episode['id'] in identities:
            raise ValueError('unique episode identity required')
        identities.add(episode['id'])
        events = episode['events']
        if type(events) is not list or not 1 <= len(events) <= 12:
            raise ValueError('bounded literal event list required')
        for event in events:
            if type(event) is not dict or event.get('kind') not in ('teach', 'correct', 'ask'):
                raise ValueError('unknown event kind')
            fields = {'kind', 'text'} if event['kind'] != 'ask' else {'kind', 'text', 'accepted', 'measure'}
            if set(event) != fields or type(event['text']) is not str or not event['text'].strip():
                raise ValueError('literal event fields required')
            if event['kind'] == 'ask':
                if event['measure'] not in ('before', 'corrected', 'missing_fact', 'fresh_multihop'):
                    raise ValueError('explicit separate measurement required')
                if type(event['accepted']) is not list or not event['accepted'] or any(type(s) is not str or not s.strip() for s in event['accepted']):
                    raise ValueError('explicit human accepted answers required')
    return packet


def numeric_episodes(packet, targets, receipt, pins):
    """Admit distinct checked numerical development sources, never HUMAN text.

    Integer operations below verify targets offline. They are never called by
    Runtime.answer, and structured givens/targets never enter that interface.
    The pinned independent receipt owns semantic wording/provenance checks.
    """
    pool = 'luna-notebook-wordproblem-dev-v1'
    ids = ['I0', 'I1', 'P0', 'P1']
    if (type(packet) is not dict or set(packet) != {'schema', 'origin', 'source_pool', 'training_eligible', 'episodes'} or
            packet['schema'] != 'sol.nextdemo.numeric-notes.v1' or
            packet['origin'] != 'Luna-authored-numeric-wordproblem-development' or
            packet['source_pool'] != pool or packet['training_eligible'] is not False):
        raise ValueError('distinct Luna numeric-development notes required')
    if (type(targets) is not dict or set(targets) != {'schema', 'source_pool', 'training_eligible', 'episodes'} or
            targets['schema'] != 'sol.nextdemo.numeric-targets.v1' or targets['source_pool'] != pool or
            targets['training_eligible'] is not False):
        raise ValueError('separate numeric development targets required')
    required_receipt = {'schema', 'writer_model_lineage', 'source_pool_id',
        'question_note_packet_sha256', 'numeric_targets_sha256', 'per_field_sha256',
        'independent_verifier_identity', 'verifier_source_or_review_pin',
        'per_world_givens_and_correction_verified', 'numeric_target_verification',
        'wording_review', 'no_answer_or_intermediate_in_notes', 'query_identity_check',
        'source_exclusion_metadata_pins', 'freshness_review', 'token_cap_audit',
        'approved_episode_ids', 'training_eligible_false'}
    if type(receipt) is not dict or set(receipt) != required_receipt or receipt['schema'] != 'sol.nextdemo.numeric-check.v1':
        raise ValueError('complete pinned independent numeric verification receipt required')
    if (receipt['source_pool_id'] != pool or receipt['approved_episode_ids'] != ids or
            receipt['question_note_packet_sha256'] != pins['notes'] or receipt['numeric_targets_sha256'] != pins['targets']):
        raise ValueError('numeric verification source pins/identities differ')
    for field in ('per_world_givens_and_correction_verified', 'numeric_target_verification',
            'wording_review', 'no_answer_or_intermediate_in_notes', 'query_identity_check',
            'freshness_review', 'training_eligible_false'):
        if receipt[field] is not True:
            raise ValueError('independent verification missing: ' + field)
    for field in ('writer_model_lineage', 'independent_verifier_identity'):
        if type(receipt[field]) is not str or not receipt[field].strip():
            raise ValueError('explicit verifier/writer identities required')
    def valid_pin(pin):
        return type(pin) is dict and set(pin) == {'path', 'sha256'} and type(pin['path']) is str and bool(pin['path']) and type(pin['sha256']) is str and bool(re.fullmatch('[0-9a-f]{64}', pin['sha256']))
    if not valid_pin(receipt['verifier_source_or_review_pin']):
        raise ValueError('independent review/source pin required')
    if type(receipt['source_exclusion_metadata_pins']) is not list or not receipt['source_exclusion_metadata_pins'] or not all(valid_pin(p) for p in receipt['source_exclusion_metadata_pins']):
        raise ValueError('source-exclusion metadata pins required; never open panels')
    if type(packet['episodes']) is not list or type(targets['episodes']) is not list or len(packet['episodes']) != 4 or len(targets['episodes']) != 4:
        raise ValueError('exact four numeric worlds required')
    if [e.get('id') for e in packet['episodes']] != ids or [e.get('id') for e in targets['episodes']] != ids:
        raise ValueError('exact ordered I0/I1/P0/P1 packet required')
    result = []; family_questions = {}; family_answers = {'I': [], 'P': []}; family_givens = {'I': [], 'P': []}
    for e, target in zip(packet['episodes'], targets['episodes']):
        fields = {'id', 'family', 'question', 'notes', 'correction', 'missing_notes', 'givens', 'corrected_givens'}
        if set(e) != fields or set(target) != {'id', 'initial', 'corrected', 'missing_accepted'}:
            raise ValueError('exact numeric episode/target fields required')
        family = e['id'][0]
        if e['family'] != family:
            raise ValueError('explicit family I/P required')
        for field in ('question', 'notes', 'correction', 'missing_notes'):
            if type(e[field]) is not str or not e[field].strip():
                raise ValueError('literal numeric word-problem text required')
        if re.search(r'\d', e['question']) or family_questions.setdefault(family, e['question']) != e['question']:
            raise ValueError('byte-identical family query without instance numbers required')
        if len(e['question'].split()) > 20:
            raise ValueError('numeric development question exceeds20words')
        givens, corrected = e['givens'], e['corrected_givens']
        keys = {'boxes', 'items_per_box', 'removed_items'} if family == 'I' else {'first_batch_items', 'second_batch_items', 'number_of_packs'}
        changed = 'items_per_box' if family == 'I' else 'first_batch_items'
        if type(givens) is not dict or type(corrected) is not dict or set(givens) != keys or set(corrected) != keys:
            raise ValueError('exact independently mapped numeric givens required')
        if any(type(v) is not int for g in (givens, corrected) for v in g.values()) or [k for k in sorted(keys) if givens[k] != corrected[k]] != [changed]:
            raise ValueError('exactly one declared integer given must change')
        computed = []
        for g in (givens, corrected):
            if family == 'I':
                b, p, r = g['boxes'], g['items_per_box'], g['removed_items']
                if not (2 <= b <= 9 and 3 <= p <= 15 and 1 <= r <= 10 and r < b*p):
                    raise ValueError('inventory bounds differ')
                computed.append(b*p-r)
            else:
                a, b, packs = g['first_batch_items'], g['second_batch_items'], g['number_of_packs']
                if not (4 <= a <= 60 and 4 <= b <= 60 and 2 <= packs <= 6 and (a+b) % packs == 0):
                    raise ValueError('exact equal-packing bounds differ')
                computed.append((a+b)//packs)
        if target['initial'] != str(computed[0]) or target['corrected'] != str(computed[1]):
            raise ValueError('independently computed numeric target differs')
        numbers = lambda text: [int(s) for s in re.findall(r'(?<!\w)-?\d+(?!\w)', text)]
        if sorted(numbers(e['notes'])) != sorted(givens.values()) or sorted(numbers(e['missing_notes'])) != sorted(v for k, v in givens.items() if k != changed):
            raise ValueError('notes must contain only exact givens; missing given must be absent')
        correction_numbers = numbers(e['correction'])
        if corrected[changed] not in correction_numbers or not set(correction_numbers).issubset({givens[changed], corrected[changed]}):
            raise ValueError('correction may contain only old/new changed given')
        for field in fields - {'id', 'family'}:
            value = e[field]
            canonical = value if type(value) is str else json.dumps(value, sort_keys=True, separators=(',', ':'))
            if receipt['per_field_sha256'].get(e['id'], {}).get(field) != text_sha(canonical):
                raise ValueError('verified per-field hash differs')
        audit = receipt['token_cap_audit'].get(e['id'], {})
        for name, cap in [('question_tokens_before_EOS', 47), ('notes_plus_correction_tokens', 512), ('answer_tokens_before_EOS', 63)]:
            if type(audit.get(name)) is not int or not 0 < audit[name] <= cap:
                raise ValueError('independent tokenizer-cap receipt required')
        abstentions = target['missing_accepted']
        if abstentions != ["I don't know", "I don't know.", "Not enough information", "Not enough information."]:
            raise ValueError('frozen four-variant numeric abstention set differs; reject before outputs')
        family_answers[family].extend(computed); family_givens[family].extend(givens.values()); family_givens[family].extend(corrected.values())
        result.append(dict(id=e['id'], origin=packet['origin'], source_pool=pool, events=[
            dict(kind='teach', text=e['notes']),
            dict(kind='ask', text=e['question'], accepted=[target['initial']], measure='before'),
            dict(kind='correct', text=e['correction']),
            dict(kind='ask', text=e['question'], accepted=[target['corrected']], measure='corrected'),
            dict(kind='reset', text=e['missing_notes']),
            dict(kind='ask', text=e['question'], accepted=abstentions, measure='missing_fact')]))
    for family in family_answers:
        if len(set(family_answers[family])) != 4 or set(family_answers[family]) & set(family_givens[family]):
            raise ValueError('counterfactual targets must be distinct and unequal to all givens')
    return result


class Session:
    """Append-only source order; no semantic resolution, retrieval or fact solver."""
    def __init__(self):
        self.events = []

    def append(self, kind, text):
        if kind not in ('teach', 'correct') or type(text) is not str or not text.strip():
            raise ValueError('literal teach/correct event required')
        prior = self.events[-1]['sha256'] if self.events else '0' * 64
        row = dict(seq=len(self.events), kind=kind, text=text, previous=prior)
        row['sha256'] = text_sha(json.dumps(row, sort_keys=True, ensure_ascii=False))
        self.events.append(row)

    def context(self):
        return '\n'.join(row['text'] for row in self.events)


def run_episode(episode, runtime, intervention='full', *, backend_label='unit-test-only'):
    if intervention not in (*INTERVENTIONS, 'pre_correction'):
        raise ValueError('unknown intervention')
    session = Session()
    before_correction = None
    before_events = None
    rows = []
    for index, event in enumerate(episode['events']):
        if event['kind'] == 'reset':
            session = Session(); before_correction = None; before_events = None
            session.append('teach', event['text'])
            continue
        if event['kind'] != 'ask':
            if event['kind'] == 'correct' and before_correction is None:
                before_correction = session.context()
                before_events = list(session.events)
            session.append(event['kind'], event['text'])
            continue
        context = session.context()
        supplied_events = session.events
        if intervention == 'pre_correction' and before_correction is not None:
            context = before_correction
            supplied_events = before_events
        answer = runtime.answer(event['text'], context, 'full' if intervention == 'pre_correction' else intervention)
        if type(answer) is not dict or type(answer.get('text')) is not str:
            raise ValueError('backend must return literal generated text')
        rows.append(dict(event_index=index, measure=event['measure'], accepted=event['accepted'],
                         exact_text_match=answer['text'].strip() in [s.strip() for s in event['accepted']],
                         native_generation_valid=(answer.get('observed', {}).get('native_call_contract_valid') is True and
                             answer.get('observed', {}).get('observed_EOS') is True and
                             answer.get('observed', {}).get('native_stripped_output_equal') is True and
                             answer.get('observed', {}).get('termination_reason') == 'observed_EOS'),
                         source_events=[r['sha256'] for r in session.events], context_sha256=text_sha(context),
                         intended_source_writes=[dict(seq=r['seq'], kind=r['kind'], text_sha256=text_sha(r['text'])) for r in session.events],
                         actual_source_writes=[dict(r) for r in session.events],
                         source_capture_byte_mismatches=0,
                         supplied_notebook_event_count=0 if intervention == 'no_notebook' else len(supplied_events),
                         model_selected_correct_writes=None, model_selected_wrong_writes=None,
                         write_scope='Host append-only source capture; no model-selected write interface exposed. Byte equality is not factual truth.',
                         answer=answer, intervention=intervention, backend=backend_label))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--fixture')
    source.add_argument('--numeric-notes')
    parser.add_argument('--fixture-sha256')
    for name in ('numeric-notes-sha256', 'numeric-targets', 'numeric-targets-sha256', 'numeric-verification', 'numeric-verification-sha256'):
        parser.add_argument('--'+name)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--intervention', choices=(*INTERVENTIONS, 'pre_correction'), default='full')
    parser.add_argument('--notebook-ab', action='store_true', help='Same loaded checkpoint: full versus no_notebook; seed-balanced execution order.')
    args = parser.parse_args()
    output = safe_path(args.out)
    if output.exists():
        raise ValueError('new output path required; never overwrite evidence')
    if args.numeric_notes:
        if not all((args.numeric_notes_sha256, args.numeric_targets, args.numeric_targets_sha256, args.numeric_verification, args.numeric_verification_sha256)):
            raise ValueError('all separate numeric source/target/verification paths and pins required')
        notes = json.loads(read_pinned(args.numeric_notes, args.numeric_notes_sha256))
        targets = json.loads(read_pinned(args.numeric_targets, args.numeric_targets_sha256))
        receipt = json.loads(read_pinned(args.numeric_verification, args.numeric_verification_sha256))
        episodes = numeric_episodes(notes, targets, receipt, {'notes':args.numeric_notes_sha256, 'targets':args.numeric_targets_sha256})
        source_origin = notes['origin']
    else:
        packet = validate_fixture(json.loads(read_pinned(args.fixture, args.fixture_sha256)))
        episodes = packet['episodes']; source_origin = packet['origin']
    runtime = Runtime(args.manifest, args.manifest_sha256)
    if args.numeric_notes:
        for episode in episodes:
            question = episode['events'][1]['text']
            if len(runtime.r['tok'].encode(question, add_special_tokens=False)) + 1 > 48:
                raise ValueError('actual numeric question exceeds48tokens INCLUDING EOS; no cap relaxation')
    arms = (['full', 'no_notebook'] if runtime.manifest['seed'] == 0 else ['no_notebook', 'full']) if args.notebook_ab else [args.intervention]
    rows = [dict(episode_id=episode['id'], source_origin=source_origin, **row) for intervention in arms for episode in episodes
            for row in run_episode(episode, runtime, intervention, backend_label='actual-model')]
    counts = {}
    for row in rows:
        key = row['intervention'] + ':' + row['measure']
        item = counts.setdefault(key, {'matched': 0, 'total': 0})
        item['matched'] += int(row['exact_text_match']); item['total'] += 1
    judged = [r for r in rows if r['intervention'] == 'full'] if args.notebook_ab else rows
    full_pass = bool(judged) and all(row['exact_text_match'] and row['native_generation_valid'] for row in judged)
    ab_summary = None
    if args.notebook_ab:
        supported = [r for r in rows if r['measure'] != 'missing_fact']
        matched = {arm: sum(r['exact_text_match'] and r['native_generation_valid'] for r in supported if r['intervention'] == arm) for arm in arms}
        ab_summary = dict(seed=runtime.manifest['seed'], supported_correct=matched,
            with_minus_without=matched['full'] - matched['no_notebook'],
            missing_fact_counts={key: value for key, value in counts.items() if key.endswith(':missing_fact')},
            system_notebook_benefit_this_seed=matched['full'] > matched['no_notebook'],
            two_seed_consistency='Requires separate other-seed raw recount; not established by this file.',
            model_selected_write_benefit='UNTESTED: no model-selected write operation exposed')
    report = dict(schema='sol.nextdemo.raw.v1', fixture_sha256=args.fixture_sha256,
                  numeric_notes_sha256=args.numeric_notes_sha256, numeric_targets_sha256=args.numeric_targets_sha256,
                  numeric_verification_sha256=args.numeric_verification_sha256, source_origin=source_origin,
                  manifest_sha256=args.manifest_sha256, rows=rows, counts=counts,
                  notebook_ab=ab_summary,
                  development_status='PASS' if full_pass else 'FAIL',
                  pass_scope='This arm and fixture only: every literal accepted answer and valid observed EOS. Control failures are reported, not hidden.',
                  provenance_status=('Pinned independently reviewed Luna numeric development, never human-authored; semantic/source review is attested by the external verification receipt.' if args.numeric_notes else 'Caller-pinned human-authorship declaration; independent source verification remains the fixture owner responsibility.'),
                  training_eligible=False, actual_user_day=False, optimizer_updates=0,
                  activation=False, sealed_user_test=False, generalization_claim=False,
                  reasoner_specific_proof=False,
                  interpretation='Exact human-answer matches only; English quality and causal reasoning location require separate review.')
    with output.open('x', encoding='utf8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({'output': str(output), 'counts': counts, 'reasoner_specific_proof': False}))


if __name__ == '__main__':
    main()
