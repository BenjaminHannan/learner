"""Independently recount saved capability256 tokens; no model imports or calls.

Only aggregate verdicts and hash metadata are emitted, never test items/tokens.
"""
import argparse
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024**2), b''):
            h.update(data)
    return h.hexdigest()


def score(record, target):
    # Independently derive the strict score from the saved native output and EOS.
    assert type(target) is list and target and all(type(t) is int and t >= 0 for t in target)
    eos = target[-1]
    assert target.count(eos) == 1
    raw = record['MODEL_raw_generate_ids']
    full = raw[0] if (type(raw) is list and len(raw) == 1 and type(raw[0]) is list
                     and all(type(t) is int and t >= 0 for t in raw[0])) else None
    if full is None:
        return False
    assert full == record['MODEL_generated_ids_with_observed_EOS']
    positions = [i for i, t in enumerate(full) if t == eos]
    assert positions == record['EOS_positions']
    assert bool(positions) == record['observed_EOS']
    stripped = full[:positions[0]] if positions else full
    parity = record['MODEL_native_decoder_return'] == [stripped]
    assert parity == record['native_stripped_output_equal']
    options = record['native_generation_options']
    valid = (record['native_generate_call_count'] == 1 and record['native_call_contract_valid'] is True
             and record['generation_error'] is None and type(options) is dict
             and options.get('max_new_tokens') == 32 and options.get('do_sample') is False
             and options.get('use_cache') is True and options.get('eos_token_id') == eos
             and options.get('pad_token_id') == eos)
    exact = (valid and len(full) <= 32 and positions == [len(full) - 1] and parity and full == target)
    if exact:
        assert record['termination_reason'] == 'observed_EOS'
    assert exact is record['target_ids_plus_observed_EOS_exact']
    return exact


def recount(root):
    own = root / 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1'
    matrix = own / 'run-capability256-v1'
    plan = read(own / 'PLAN-v3.json'); final = read(matrix / 'FINAL-CLOSED.json')
    freeze = read(matrix / 'FINAL-FREEZE.json')
    assert final['closed'] is True
    assert plan['marks'] == {'train': 244, 'seen': 52, 'new_structure': 52, 'range': 26}
    assert plan['rounds'] == 4 and plan['visits_per_row'] == 20
    assert final['final_freeze_sha256'] == sha(matrix / 'FINAL-FREEZE.json')
    assert final['plan_sha256'] == sha(own / 'PLAN-v3.json')
    frozen = {(e['seed'], e['arm']): e for e in freeze['checkpoints']}
    summaries = []; paired_records = {}; native_calls = 0; modal_pin = None
    train_targets = {}; train_histogram = Counter()
    for line in (matrix / 'seed0/loop/DIAGNOSTIC-RAW.jsonl').open(encoding='utf8'):
        record = json.loads(line)
        if record['update'] == 5120:
            label = record['canonical_numeric_target']; train_histogram[label] += 1
            train_targets[label] = record['canonical_target_ids_with_EOS']
    assert sum(train_histogram.values()) == 256
    maximum = max(train_histogram.values())
    modal_label = min(label for label, count in train_histogram.items() if count == maximum)
    expected_modal_ids = train_targets[modal_label]
    hashes = {'FINAL-CLOSED.json': sha(matrix / 'FINAL-CLOSED.json'),
              'FINAL-FREEZE.json': sha(matrix / 'FINAL-FREEZE.json'),
              'FINAL-CLAIM.json': sha(matrix / 'FINAL-CLAIM.json')}
    for seed, arm in ((0, 'loop'), (0, 'plain'), (1, 'loop'), (1, 'plain')):
        out = matrix / ('seed%d' % seed) / arm
        checkpoint_hash = sha(out / 'final-resume.pt')
        assert checkpoint_hash == frozen[(seed, arm)]['checkpoint']['sha256']
        counts = Counter(train=0, seen=0, new_structure=0, range=0)
        modal = Counter(seen=0, new_structure=0, range=0); zero = modal.copy()
        seen = set(); observations = {}; stops = Counter(); zero_stops = Counter()
        train_seen = set(); train_records = {}
        for line in (out / 'DIAGNOSTIC-RAW.jsonl').open(encoding='utf8'):
            record = json.loads(line)
            if record['update'] != 5120: continue
            identity = record['id']; assert identity in plan['selected_ids'] and identity not in train_seen
            train_seen.add(identity)
            correct = score(record, record['canonical_target_ids_with_EOS'])
            counts['train'] += correct; train_records[identity] = correct
        assert train_seen == set(plan['selected_ids'])
        for line in (out / 'FINAL-RAW.jsonl').open(encoding='utf8'):
            record = json.loads(line); identity = record['id']; bucket = record['slice']
            assert bucket in plan['evaluation_ids'] and identity in plan['evaluation_ids'][bucket] and identity not in seen
            seen.add(identity)
            assert record['seed'] == seed and record['arm'] == arm
            assert record['checkpoint_sha256'] == checkpoint_hash
            assert record['fixed_rounds'] == 4 and record['attention_block_calls'] == 8
            assert record['label_join_after_raw_generation'] is True and record['notebook_tokens'] == 0
            assert 'terminal_scoring_error' not in record
            target = record['canonical_target_ids_with_EOS']; correct = score(record, target)
            counts[bucket] += correct; observations[identity] = (bucket, correct)
            control = record['native_zero_loop']
            assert control['rounds'] == 0 and control['attention_block_calls'] == 0
            zero[bucket] += score(control, target)
            native_calls += record['native_generate_call_count'] + control['native_generate_call_count']
            stops[record['termination_reason']] += 1; zero_stops[control['termination_reason']] += 1
            mode_ids = record['TRAIN_modal_target_ids_with_EOS']
            if modal_pin is None: modal_pin = mode_ids
            assert mode_ids == modal_pin == expected_modal_ids
            assert record['TRAIN_modal_numeric_target'] == modal_label
            mode_correct = mode_ids == target
            assert mode_correct is record['TRAIN_modal_constant_ids_equal']
            assert record['TRAIN_modal_model_calls'] == 0 and record['TRAIN_modal_actual_terminal_EOS_observed'] is False
            modal[bucket] += mode_correct
        assert seen == set(sum(plan['evaluation_ids'].values(), []))
        closed = read(out / 'FINAL-CLOSED.json')
        assert closed['closed'] is True and closed['counts'] == dict(counts)
        assert closed['TRAIN_modal_counts'] == dict(modal) and closed['native_zero_loop_counts'] == dict(zero)
        assert closed['final_raw_sha256'] == sha(out / 'FINAL-RAW.jsonl')
        saved = next(e for e in final['matrix'] if e['seed'] == seed and e['arm'] == arm)
        assert saved == {k: closed[k] for k in saved}
        passed = all(counts[k] >= plan['marks'][k] for k in counts)
        assert passed is closed['marks_met']
        summaries.append({'seed': seed, 'arm': arm, 'counts': dict(counts), 'marks_met': passed,
                          'TRAIN_modal_counts': dict(modal), 'native_zero_loop_counts': dict(zero),
                          'termination_reasons': dict(stops), 'zero_loop_termination_reasons': dict(zero_stops),
                          'checkpoint_sha256': checkpoint_hash, 'final_raw_sha256': sha(out / 'FINAL-RAW.jsonl'),
                          'questions': len(seen), 'final_train_diagnostics': len(train_seen)})
        paired_records[(seed, arm)] = {**observations, **{k: ('train', v) for k, v in train_records.items()}}
        for name in ('FINAL-RAW.jsonl', 'FINAL-CLOSED.json', 'TRAIN-RAW.jsonl', 'DIAGNOSTIC-RAW.jsonl'):
            hashes['seed%d/%s/%s' % (seed, arm, name)] = sha(out / name)
    pairs = []
    for seed in (0, 1):
        loop = paired_records[(seed, 'loop')]; plain = paired_records[(seed, 'plain')]
        assert loop.keys() == plain.keys()
        for bucket in ('train', 'seen', 'new_structure', 'range'):
            c = Counter(both_correct=0, loop_only=0, plain_only=0, neither=0)
            for identity, (name, left) in loop.items():
                if name != bucket: continue
                other_name, right = plain[identity]; assert name == other_name
                c['both_correct' if left and right else 'loop_only' if left else 'plain_only' if right else 'neither'] += 1
            pairs.append({'seed': seed, 'bucket': bucket, **dict(c), 'loop_minus_plain': c['loop_only'] - c['plain_only']})
    loop_passes = [s['marks_met'] for s in summaries if s['arm'] == 'loop']
    verdict = 'marks-met' if all(loop_passes) else 'marks-not-met' if loop_passes[0] == loop_passes[1] else 'discordant-seeds'
    assert final['primary_verdict'] == verdict
    assert final['current_size_synthetic_numeric_capability_marks_met'] is all(loop_passes)
    assert native_calls == final['native_generation_calls'] == final['expected_native_generation_calls'] == 1280
    return {'schema': 'cap256.independent-final-recount.v1', 'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'saved_token_recount_pass': True, 'model_calls_by_verifier': 0, 'optimizer_calls_by_verifier': 0,
            'matrix': summaries, 'paired_loop_plain': pairs, 'primary_verdict': verdict,
            'both_recurrent_seeds_pass': all(loop_passes), 'native_generation_calls': native_calls,
            'sealed_phase_wall_seconds': final['wall_seconds'], 'sealed_phase_native_calls_per_second': native_calls / final['wall_seconds'],
            'marks': plan['marks'], 'TRAIN_modal_baseline_verified_from_TRAIN_only': True,
            'TRAIN_modal_frequency': maximum, 'file_sha256': hashes}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--root', required=True)
    args = parser.parse_args()
    print(json.dumps(recount(Path(args.root)), indent=2, sort_keys=True))
