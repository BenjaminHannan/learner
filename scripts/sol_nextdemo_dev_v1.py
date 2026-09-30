"""Bounded human-authored development episodes; never training material.

Expected answers stay in the scorer. The inference backend receives only the
literal question, source notebook text and explicitly disclosed intervention.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

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
    rows = []
    for index, event in enumerate(episode['events']):
        if event['kind'] != 'ask':
            if event['kind'] == 'correct' and before_correction is None:
                before_correction = session.context()
            session.append(event['kind'], event['text'])
            continue
        context = session.context()
        if intervention == 'pre_correction' and before_correction is not None:
            context = before_correction
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
                         answer=answer, intervention=intervention, backend=backend_label))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', required=True)
    parser.add_argument('--fixture-sha256', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--intervention', choices=(*INTERVENTIONS, 'pre_correction'), default='full')
    args = parser.parse_args()
    output = safe_path(args.out)
    if output.exists():
        raise ValueError('new output path required; never overwrite evidence')
    packet = validate_fixture(json.loads(read_pinned(args.fixture, args.fixture_sha256)))
    runtime = Runtime(args.manifest, args.manifest_sha256)
    rows = [dict(episode_id=episode['id'], **row) for episode in packet['episodes']
            for row in run_episode(episode, runtime, args.intervention, backend_label='actual-model')]
    counts = {}
    for row in rows:
        item = counts.setdefault(row['measure'], {'matched': 0, 'total': 0})
        item['matched'] += int(row['exact_text_match']); item['total'] += 1
    full_pass = bool(rows) and all(row['exact_text_match'] and row['native_generation_valid'] for row in rows)
    report = dict(schema='sol.nextdemo.raw.v1', fixture_sha256=args.fixture_sha256,
                  manifest_sha256=args.manifest_sha256, rows=rows, counts=counts,
                  development_status='PASS' if full_pass else 'FAIL',
                  pass_scope='This arm and fixture only: every literal accepted answer and valid observed EOS. Control failures are reported, not hidden.',
                  provenance_status='Caller-pinned human-authorship declaration; independent source verification remains the fixture owner responsibility.',
                  training_eligible=False, actual_user_day=False, optimizer_updates=0,
                  activation=False, sealed_user_test=False, generalization_claim=False,
                  reasoner_specific_proof=False,
                  interpretation='Exact human-answer matches only; English quality and causal reasoning location require separate review.')
    with output.open('x', encoding='utf8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({'output': str(output), 'counts': counts, 'reasoner_specific_proof': False}))


if __name__ == '__main__':
    main()
