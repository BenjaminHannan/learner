"""CPU-only independent recount of closed notebook48 native observations."""
import hashlib
import json
import os
from pathlib import Path


def recount(root):
    root = Path(root)
    read = lambda p: json.loads(p.read_bytes())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    text_sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
    plan_path = root / 'artifacts/cap256-launch/notebook48-v1/PLAN-DELIVERY-RETRY-v2.json'
    plan = read(plan_path)
    matrix = root / plan['output_namespace']
    closed = read(matrix / 'CLOSED.json')
    assert closed['closed'] and closed['native_calls'] == 48 and closed['optimizer_updates'] == 0
    assert closed['plan_sha256'] == sha(plan_path)
    assert not closed['training_eligible'] and not closed['learned_writer_claim']
    calls_path, answers_path = matrix / 'CALLS.jsonl', matrix / 'ANSWERS.jsonl'
    assert sha(calls_path) == closed['calls_sha256'] and sha(answers_path) == closed['answers_sha256']
    calls = [json.loads(s) for s in calls_path.read_text().splitlines()]
    answers = [json.loads(s) for s in answers_path.read_text().splitlines()]
    assert len(calls) == len(answers) == 48
    source_plan = read(root / 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/PLAN-v3.json')
    token_audit = read(root / 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/TOKEN-AUDIT-v4.json')
    lm_path = Path(source_plan['warmstart']['tuples']['0']['lm_path'])
    for f in token_audit['tokenizer_files']:
        assert sha(lm_path / f['name']) == f['sha256']
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(lm_path, local_files_only=True)
    eos = tok.eos_token_id
    results = []
    eos_count = 0
    for seed in (0, 1):
        raw_path = matrix / ('SEED%d-RAW.json' % seed)
        pin = closed['reports'][seed]
        assert pin['seed'] == seed and pin['weights_unchanged'] and sha(raw_path) == pin['raw_sha256']
        report = read(raw_path)
        assert report['optimizer_updates'] == 0 and not report['training_eligible']
        rows = report['rows']
        assert len(rows) == 24
        counts, keyed = {}, {}
        for j, row in enumerate(rows):
            index = seed * 24 + j
            call, answer = calls[index], answers[index]
            assert call['call_index'] == answer['call_index'] == index + 1
            assert call['seed'] == answer['seed'] == seed
            a = row['answer']; o = a['observed']
            assert o == call['observed'] and a == answer['answer']
            assert a['rounds'] == 4 and a['optimizer_updates'] == 0 and not a['training_eligible']
            assert a['checkpoint'] == read(root / plan['entries'][seed]['manifest']['path'])['checkpoint']
            for k in ('question_sha256', 'supplied_context_sha256', 'intervention'):
                assert a[k] == call[k] == answer[k]
            events = row['actual_source_writes']
            assert len(events) == (2 if row['measure'] == 'corrected' else 1)
            prior = '0' * 64
            for n, event in enumerate(events):
                assert event['seq'] == n and event['previous'] == prior
                body = {k: v for k, v in event.items() if k != 'sha256'}
                assert event['sha256'] == text_sha(json.dumps(body, sort_keys=True, ensure_ascii=False))
                assert row['intended_source_writes'][n] == {'seq': n, 'kind': event['kind'], 'text_sha256': text_sha(event['text'])}
                prior = event['sha256']
            context = '\n'.join(e['text'] for e in events)
            assert text_sha(context) == row['context_sha256'] == a['supplied_context_sha256']
            assert row['model_selected_correct_writes'] is None and row['model_selected_wrong_writes'] is None
            assert row['source_capture_byte_mismatches'] == 0
            if row['intervention'] == 'no_notebook':
                assert a['context_sha256'] == text_sha('') and a['notebook_ids'] == [[]]
            else:
                assert a['context_sha256'] == text_sha(context) and a['notebook_ids'] != [[]]
            raw = o['MODEL_raw_generate_ids']
            assert len(raw) == 1 and all(type(t) is int for t in raw[0])
            full = raw[0]
            assert full == o['MODEL_generated_ids_with_observed_EOS']
            positions = [i for i, v in enumerate(full) if v == eos]
            assert positions == o['EOS_positions'] and bool(positions) == o['observed_EOS']
            stripped = full[:positions[0]] if positions else full
            assert o['MODEL_native_decoder_return'] == [stripped] and o['native_stripped_output_equal']
            assert tok.decode(stripped, skip_special_tokens=True) == a['text']
            valid = (o['native_generate_call_count'] == 1 and o['native_call_contract_valid']
                     and o['generation_error'] is None
                     and len(full) <= 32 and positions == [len(full)-1]
                     and o['termination_reason'] == 'observed_EOS')
            eos_count += int(valid)
            text_match = a['text'].strip() in [v.strip() for v in row['accepted']]
            assert text_match == row['exact_text_match']
            strict = valid and any(full == tok.encode(v, add_special_tokens=False) + [eos] for v in row['accepted'])
            key = row['intervention'] + ':' + row['measure']
            c = counts.setdefault(key, {'total': 0, 'text_correct': 0, 'exact_text_and_EOS': 0, 'exact_tokens_and_EOS': 0})
            c['total'] += 1; c['text_correct'] += int(text_match)
            c['exact_text_and_EOS'] += int(text_match and valid); c['exact_tokens_and_EOS'] += int(strict)
            keyed[(row['intervention'], row['episode_id'], row['measure'])] = (bool(text_match and valid), a)
        paired = {'gains': 0, 'losses': 0, 'both_correct': 0, 'both_wrong': 0}
        for (arm, episode, measure), (good, a) in keyed.items():
            if arm != 'full' or measure == 'missing_fact': continue
            other, b = keyed[('no_notebook', episode, measure)]
            assert a['input_ids'] == b['input_ids'] and a['input_mask'] == b['input_mask']
            assert a['supplied_context_sha256'] == b['supplied_context_sha256']
            paired['both_correct' if good and other else 'gains' if good else 'losses' if other else 'both_wrong'] += 1
        supported = {arm: sum(counts[arm + ':' + m]['exact_text_and_EOS'] for m in ('before', 'corrected')) for arm in ('full', 'no_notebook')}
        results.append({'seed': seed, 'counts': counts, 'supported_correct_out_of_8': supported,
                        'with_minus_without': supported['full'] - supported['no_notebook'], 'paired_supported': paired})
    return {'schema': 'cap256.notebook48.independent-recount.v1', 'passed_integrity_checks': True,
            'model_calls': 0, 'optimizer_updates': 0, 'saved_native_calls': 48,
            'valid_actual_EOS_calls': eos_count, 'closed': closed, 'seeds': results,
            'two_seed_supported_benefit': all(r['with_minus_without'] > 0 for r in results),
            'learned_writer_claim': False, 'generalization_claim': False,
            'evidence_limit': 'Native observer saved argument-key contract, not argument values; fixed generation settings are source-pinned, not independently present in each observation.'}


if __name__ == '__main__':
    print(json.dumps(recount('C:/Users/benja/sol-cloud-numeric-capability-v1'), sort_keys=True))
