#!/usr/bin/env python3
"""Saved-only numeric TRAIN engineering recount; no tokenizer/model imports."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path('/workspace/learner')
OWN = ROOT / 'artifacts/sol-cloud-verifier-20260930'
PINS = {
    'scripts/sol_cloud_numeric_fit_v2.py': '218e4f26a87b44778f8ec27f3c25fee70142a677f0292a0c25f5070d94dbe965',
    'artifacts/sol-cloud-numeric-fit-20260930/PLAN-v3.json': '8c1ccaee1a2907461ec49c6febb2c1d1d108c142b03b629e930b1fd849eb4b23',
    'artifacts/sol-cloud-numeric-fit-20260930/SEAL-v4.json': '23c57948756f8493442639f1aac5ebd7198bb5892dbf4d4928c47c8f9454825d',
    'artifacts/sol-cloud-capability-plan-20260930/numeric-diagnostic-v4/ROW-SEAL-v1.json': '21f5b56db65828b241adf538f502608802b2263d02565a8761ba74c5dfd4dd74',
    'artifacts/sol-cloud-capability-plan-20260930/numeric-diagnostic-v4/SCHEDULE-s0-v1.json': '0baf2bbdfee172be829d89a1231f7da451d4cb984f3ed981da1c244d1734b1b8',
    'artifacts/sol-cloud-capability-plan-20260930/numeric-diagnostic-v4/SCHEDULE-s1-v1.json': 'c2be52e70ef5c1e81005d0962380b9700946953d93f1435e49506fd8ef75fa03',
}
FILES = ('LAUNCH.json', 'INPUT-FRAMES.json', 'INITIAL-FUNCTION-PARITY.json',
         'INITIAL-STATE.json', 'MEMORY-PREFLIGHT.json', 'TRAIN-RAW.jsonl',
         'DIAGNOSTIC-RAW.jsonl', 'CLOSED.json', 'FAILED.json')
NUMERIC = re.compile(r'-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*|\.[0-9]+)?\Z')


def checked(path, root=ROOT):
    path, root = Path(path).absolute(), Path(root).absolute()
    banned = ('uncle-questions', 'readpanel320', 'dev100', 'stop88', 'sealed', 'blind')
    if any(word in part.casefold() for part in path.parts for word in banned):
        raise ValueError('protected path rejected before filesystem access')
    actual = path.resolve()
    if any(word in part.casefold() for part in actual.parts for word in banned):
        raise ValueError('protected resolved destination')
    if not actual.is_relative_to(root.resolve()) or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('explicit scope without symlink escapes required')
    return path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(record):
    return sha(json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode())


def decode(raw):
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON field')
            result[key] = value
        return result
    def reject(value):
        raise ValueError('nonfinite literal')
    return json.loads(raw.decode('utf8'), object_pairs_hook=unique, parse_constant=reject)


def typed_ids(value):
    return type(value) is list and all(type(token) is int and token >= 0 for token in value)


def single_ids(value):
    return type(value) is list and len(value) == 1 and typed_ids(value[0])


def strict_generation(row, target, eos=7):
    """Recount complete saved return IDs and source-observer contract, no decode."""
    errors = []
    raw = row.get('MODEL_raw_generate_ids')
    valid_raw = single_ids(raw)
    full = raw[0] if valid_raw else None
    positions = [i for i, token in enumerate(full) if token == eos] if valid_raw else []
    returned = row.get('MODEL_native_decoder_return')
    stripped = full[:positions[0]] if positions else full
    valid_call = (type(row.get('native_generate_call_count')) is int
                  and row['native_generate_call_count'] == 1
                  and row.get('native_call_contract_valid') is True)
    error = row.get('generation_error')
    if not valid_call or error:
        reason = 'invalid_native_generation_call'
    elif not valid_raw:
        reason = 'invalid_or_multiple_output_sequences'
    elif len(full) > 32:
        reason = 'invalid_generation_extent'
    elif len(positions) > 1:
        reason = 'invalid_multiple_EOS'
    elif positions and positions[-1] != len(full) - 1:
        reason = 'invalid_tokens_after_EOS'
    elif positions:
        reason = 'observed_EOS'
    elif len(full) == 32:
        reason = 'max_new_tokens_without_EOS'
    else:
        reason = 'terminated_without_observed_EOS'
    strip_equal = valid_raw and single_ids(returned) and returned == [stripped]
    if not strip_equal and reason == 'observed_EOS':
        reason = 'invalid_native_stripped_output_parity'
    primary = (valid_call and valid_raw and error is None and reason == 'observed_EOS'
               and strip_equal and positions == [len(full) - 1] and full == target)
    expected = {'MODEL_generated_ids_with_observed_EOS': full, 'EOS_positions': positions,
                'observed_EOS': bool(positions), 'raw_output_single_typed_sequence': valid_raw,
                'native_stripped_output_equal': strip_equal, 'termination_reason': reason,
                'target_ids_plus_observed_EOS_exact': primary}
    for field, value in expected.items():
        if row.get(field) != value or (type(value) is bool and type(row.get(field)) is not bool):
            errors.append('generation field disagreement: ' + field)
    if row.get('same_generation_call_no_rescore') is not True:
        errors.append('missing same-call observer identity')
    generated = returned[0] if single_ids(returned) else None
    if row.get('MODEL_generated_ids') != generated:
        errors.append('stripped generated IDs disagree with native return')
    secondary = generated == target[:-1]
    if row.get('target_ids_exact') is not secondary:
        errors.append('secondary token equality disagreement')
    return {'primary': primary, 'secondary_nonEOS': secondary,
            'full_ids': full, 'stripped_ids': generated, 'termination_reason': reason,
            'observed_EOS_positions': positions, 'errors': errors}


def recount(run, seed, arm, expected_job=None):
    run = checked(run)
    if type(seed) is not int or seed not in (0, 1) or arm not in ('loop', 'plain'):
        raise ValueError('released seed and arm only')
    pinned = {}
    for relative, expected in PINS.items():
        raw = checked(ROOT / relative).read_bytes()
        if sha(raw) != expected:
            raise ValueError('frozen preparation pin differs: ' + relative)
        pinned[relative] = raw
    plan = decode(pinned['artifacts/sol-cloud-numeric-fit-20260930/PLAN-v3.json'])
    selection = decode(pinned['artifacts/sol-cloud-capability-plan-20260930/numeric-diagnostic-v4/ROW-SEAL-v1.json'])
    audits = {row['id']: row for row in selection['selected_rows']}
    ordered_ids = plan['selected_ids']
    schedule_record = decode(pinned['artifacts/sol-cloud-capability-plan-20260930/numeric-diagnostic-v4/SCHEDULE-s%d-v1.json' % seed])
    schedule = schedule_record
    if type(schedule) is not list or len(schedule) != 800 or Counter(schedule) != Counter({rid: 50 for rid in ordered_ids}):
        raise ValueError('pinned schedule is not exactly800/16times50')
    errors, file_pins, records, tails = [], {}, {}, {}
    for name in FILES:
        p = checked(run / name)
        if not p.is_file():
            continue
        raw = p.read_bytes()
        file_pins[name] = {'bytes': len(raw), 'sha256': sha(raw)}
        if name.endswith('.jsonl'):
            complete = raw.splitlines(keepends=True)
            parsed = []
            for line, data in enumerate(complete, 1):
                if not data.endswith(b'\n'):
                    tails[name] = {'line': line, 'bytes': len(data), 'sha256': sha(data)}
                    errors.append(name + ': uncommitted final JSONL extent retained')
                    continue
                try:
                    parsed.append(decode(data))
                except (ValueError, UnicodeError) as error:
                    errors.append(name + ': invalid line%d: %s' % (line, type(error).__name__))
            records[name] = parsed
        else:
            try:
                records[name] = decode(raw)
            except (ValueError, UnicodeError) as error:
                errors.append(name + ': malformed JSON: ' + type(error).__name__)
    fixed = {'seed': seed, 'arm': arm,
             'plan_sha256': PINS['artifacts/sol-cloud-numeric-fit-20260930/PLAN-v3.json'],
             'seal_sha256': PINS['artifacts/sol-cloud-numeric-fit-20260930/SEAL-v4.json'],
             'driver_sha256': PINS['scripts/sol_cloud_numeric_fit_v2.py'],
             'selection_sha256': PINS['artifacts/sol-cloud-capability-plan-20260930/numeric-diagnostic-v4/ROW-SEAL-v1.json'],
             'token_audit_sha256': PINS['artifacts/sol-cloud-capability-plan-20260930/numeric-diagnostic-v4/ROW-SEAL-v1.json'],
             'actual_user_day': False}
    launch = records.get('LAUNCH.json', {})
    job = expected_job if expected_job is not None else launch.get('job')
    fixed['job'] = job
    if type(job) is not str or not job:
        errors.append('actual watcher job identity missing')

    def check(condition, message):
        if not condition:
            errors.append(message)

    def identity(record, location):
        if type(record) is not dict:
            errors.append(location + ': dictionary identity required')
            return False
        for field, expected in fixed.items():
            value = record.get(field)
            check(value == expected and type(value) is type(expected), location + ': identity ' + field)
        return True

    for name, value in records.items():
        if not name.endswith('.jsonl'):
            identity(value, name)
            if type(value) is dict:
                check(value.get('sleep_enabled') is False and value.get('activation') is False
                      and value.get('generated_outputs_never_training_labels') is True, name + ': inactive/outputs excluded')
    frames_record = records.get('INPUT-FRAMES.json', {})
    frames = frames_record.get('rows', [])
    check(type(frames) is list and len(frames) == 16, 'exact16 input frames missing')
    by_id = {}
    for index, frame in enumerate(frames):
        if type(frame) is not dict or frame.get('id') not in audits:
            errors.append('unreleased frame ID')
            continue
        rid = frame['id']; audit = audits[rid]
        check(index < 16 and rid == ordered_ids[index] and rid not in by_id, 'frame order/identity')
        by_id[rid] = frame
        expected = {'question_sha256': audit['question_sha256'], 'canonical_numeric_target': audit['numeric_target'],
                    'input_ids': [audit['question_token_ids_with_EOS']],
                    'input_mask': [[True] * len(audit['question_token_ids_with_EOS'])],
                    'notebook_ids': [[]], 'notebook_mask': [[]], 'labels': [audit['target_token_ids_with_EOS']],
                    'label_mask': [[True] * len(audit['target_token_ids_with_EOS'])]}
        for key, value in expected.items():
            check(frame.get(key) == value, 'frame%s: %s' % (rid, key))
        check(single_ids(frame.get('input_ids')) and single_ids(frame.get('labels')), 'typed frame token IDs ' + rid)
        for key in ('input_mask', 'label_mask'):
            check(type(frame.get(key)) is list and len(frame[key]) == 1
                  and type(frame[key][0]) is list and all(type(v) is bool and v for v in frame[key][0]), 'typed frame mask ' + rid)
        check(frame.get('frame_sha256') == canonical({key: value for key, value in frame.items() if key != 'frame_sha256'}), 'frame canonical SHA ' + rid)
    visits = Counter()
    train = records.get('TRAIN-RAW.jsonl', [])
    schedule_sha = plan['schedules'][str(seed)]['sha256']
    updates = []
    for line, row in enumerate(train, 1):
        if not identity(row, 'train%d' % line):
            continue
        rid = row.get('id')
        if rid not in audits:
            errors.append('unreleased TRAIN identity at%d' % line)
            continue
        visits[rid] += 1
        updates.append(row.get('update'))
        check(type(row.get('update')) is int and row['update'] == line, 'contiguous TRAIN update%d' % line)
        check(line <= 800 and schedule[line - 1] == rid, 'presealed schedule visit%d' % line)
        check(type(row.get('visit_for_row')) is int and row['visit_for_row'] == visits[rid], 'row visit%d' % line)
        check(row.get('schedule_sha256') == schedule_sha, 'schedule pin%d' % line)
        check(row.get('source_question_sha256') == audits[rid]['question_sha256'], 'question pin%d' % line)
        check(row.get('input_frame_sha256') == by_id.get(rid, {}).get('frame_sha256'), 'frame pin%d' % line)
        check(single_ids(row.get('labels')) and row['labels'] == [audits[rid]['target_token_ids_with_EOS']], 'TRAIN canonical labels%d' % line)
        mask = row.get('label_mask')
        check(type(mask) is list and len(mask) == 1 and type(mask[0]) is list
              and len(mask[0]) == len(audits[rid]['target_token_ids_with_EOS'])
              and all(type(v) is bool and v for v in mask[0]), 'TRAIN typed mask%d' % line)
        check(single_ids(row.get('teacherforced_argmax'))
              and len(row['teacherforced_argmax'][0]) == len(audits[rid]['target_token_ids_with_EOS']), 'TRAIN argmax shape%d' % line)
        check(row.get('objective') == 'numeric-answer-CE-only' and row.get('auxiliary_weight') == 0, 'CE-only%d' % line)
        for key in ('numeric_CE', 'preclip_norm', 'router_auxiliary_observed_excluded'):
            v = row.get(key)
            check(type(v) in (int, float) and math.isfinite(v), 'finite TRAIN %s/%d' % (key, line))
            if key in ('numeric_CE', 'preclip_norm'):
                check(type(v) in (int, float) and v >= 0, 'nonnegative TRAIN %s/%d' % (key, line))
    stages = {stage: [] for stage in plan['diagnostic_updates']}
    diagnostic = records.get('DIAGNOSTIC-RAW.jsonl', [])
    for line, row in enumerate(diagnostic, 1):
        if not identity(row, 'diagnostic%d' % line):
            continue
        rid, stage = row.get('id'), row.get('update')
        if rid not in audits or type(stage) is not int or stage not in stages:
            errors.append('unreleased diagnostic ID/stage at%d' % line)
            continue
        audit = audits[rid]; target = audit['target_token_ids_with_EOS']
        check(row.get('source_question_sha256') == audit['question_sha256'], 'diagnostic question pin%d' % line)
        check(row.get('input_frame_sha256') == by_id.get(rid, {}).get('frame_sha256'), 'diagnostic frame pin%d' % line)
        check(row.get('canonical_numeric_target') == audit['numeric_target'], 'diagnostic target%d' % line)
        check(single_ids(row.get('labels')) and row['labels'] == [target] and typed_ids(row.get('canonical_target_ids_with_EOS')) and row['canonical_target_ids_with_EOS'] == target
              and row.get('expected_answer_ids_without_EOS') == target[:-1], 'diagnostic full canonical labels%d' % line)
        mask = row.get('label_mask')
        check(type(mask) is list and len(mask) == 1 and type(mask[0]) is list
              and len(mask[0]) == len(target) and all(type(v) is bool and v for v in mask[0]), 'diagnostic typed mask%d' % line)
        check(row.get('output_translator_input') == 'FinalLatent-only' and row.get('notebook_tokens') == 0
              and row.get('generated_outputs_never_training_labels') is True, 'diagnostic output boundary%d' % line)
        measured = strict_generation(row, target)
        errors.extend('diagnostic%d: %s' % (line, error) for error in measured['errors'])
        text = row.get('MODEL_generated_text')
        numeric = type(text) is str and bool(NUMERIC.fullmatch(text.strip())) and Fraction(text.strip()) == Fraction(audit['numeric_target'])
        check(row.get('numeric_constant_exact') is numeric, 'numeric text secondary%d' % line)
        stages[stage].append({'id': rid, 'primary': measured['primary'],
                              'secondary_nonEOS': measured['secondary_nonEOS'], 'numeric_text_secondary': numeric,
                              'generated_text': text, 'complete_raw_generated_ids': measured['full_ids'],
                              'canonical_target': audit['numeric_target'], 'canonical_target_ids_with_EOS': target,
                              'termination_reason': measured['termination_reason'],
                              'model_state_fingerprints': row.get('model_state_fingerprints')})
    stage_summary = {}
    for stage, rows in stages.items():
        check(not rows or [row['id'] for row in rows] == ordered_ids[:len(rows)], 'diagnostic row order%d' % stage)
        fingerprints = [row['model_state_fingerprints'] for row in rows]
        check(not fingerprints or all(fp == fingerprints[0] for fp in fingerprints), 'diagnostic stable state%d' % stage)
        stage_summary[str(stage)] = {'rows': len(rows), 'primary_canonical_plus_actual_EOS': sum(row['primary'] for row in rows),
                                     'secondary_nonEOS_exact': sum(row['secondary_nonEOS'] for row in rows),
                                     'numeric_text_secondary': sum(row['numeric_text_secondary'] for row in rows),
                                     'termination_counts': dict(Counter(row['termination_reason'] for row in rows)), 'saved_outputs': rows}
    closed = records.get('CLOSED.json')
    initial = records.get('INITIAL-STATE.json', {})
    parity = records.get('INITIAL-FUNCTION-PARITY.json', {})
    memory = records.get('MEMORY-PREFLIGHT.json', {})
    complete = closed is not None
    if complete:
        check(closed.get('closed') is True and type(closed.get('optimizer_updates')) is int and closed['optimizer_updates'] == 800, 'terminal800 CLOSED')
        check(len(train) == 800 and updates == list(range(1, 801)) and visits == Counter({rid: 50 for rid in ordered_ids}), 'exact800/fifty visits')
        check(closed.get('visits') == dict(visits), 'CLOSED visit identity')
        for field, name in [('TRAIN_raw_sha256', 'TRAIN-RAW.jsonl'), ('DIAGNOSTIC_raw_sha256', 'DIAGNOSTIC-RAW.jsonl'), ('input_frames_sha256', 'INPUT-FRAMES.json')]:
            check(closed.get(field) == file_pins.get(name, {}).get('sha256'), 'CLOSED saved byte pin ' + name)
        for stage, rows in stages.items():
            check(len(rows) == 16, 'complete diagnostic16 stage%d' % stage)
        check(closed.get('initial_fingerprints') == initial.get('fingerprints'), 'initial fingerprint binding')
        if stages[0]:
            check(stages[0][0]['model_state_fingerprints'] == initial.get('fingerprints'), 'stage0 initial fingerprint')
        if stages[800]:
            check(stages[800][0]['model_state_fingerprints'] == closed.get('final_fingerprints'), 'stage800 final fingerprint')
        for key in ('LM_unchanged', 'optimizer_reset', 'durable_model_and_Adam_reload_equal', 'checkpoint_destination_absent_before_save', 'checkpoint_atomic_rename_not_copy'):
            check(closed.get(key) is True, 'CLOSED recorded mechanic ' + key)
        check(type(closed.get('final_checkpoint_writes_per_arm')) is int and closed['final_checkpoint_writes_per_arm'] == 1, 'single final checkpoint')
        check(closed.get('primary_metric') == 'target_ids_plus_observed_EOS_exact', 'strict primary identity')
        checkpoint = closed.get('checkpoint', {})
        check(type(checkpoint) is dict and re.fullmatch('[0-9a-f]{64}', checkpoint.get('sha256', '')) is not None, 'checkpoint source byte pin')
    if parity:
        check(parity.get('all16_exact') is True and len(parity.get('rows', [])) == 16, 'recorded initial parity16')
        for index, row in enumerate(parity.get('rows', [])):
            check(index < 16 and row.get('id') == ordered_ids[index] and row.get('equal') is True
                  and row.get('loop_final') == row.get('plain_final') and row.get('max_abs_delta') == 0, 'saved initial latent fingerprint parity%d' % index)
    if initial:
        check(initial.get('optimizer_initial_steps') == 0 and initial.get('optimizer_reset') is True
              and initial.get('halt_frozen') is True and initial.get('objective') == 'numeric-answer-CE-only'
              and initial.get('auxiliary_weight') == 0 and initial.get('declared_rng_seed') == seed, 'fresh optimizer/fixed halt/RNG')
    if memory:
        check(memory.get('optimizer_updates') == 0 and memory.get('actual_graphs') == 16 and memory.get('passed') is True, 'memory preflight before updates')
    if records.get('FAILED.json'):
        errors.append('preserved FAILED disposition present')
    final = stage_summary['800']
    return {'schema': 'sol.cloud.independent.numeric16.saved-recount.v1',
            'completed_utc': datetime.now(timezone.utc).isoformat(), 'seed': seed, 'arm': arm, 'job': job,
            'run': str(run.relative_to(ROOT)), 'source_pins': PINS, 'saved_file_pins': file_pins,
            'raw_rows': {'TRAIN': len(train), 'diagnostic': len(diagnostic)}, 'visits': dict(visits),
            'stages': stage_summary, 'raw_metadata_errors': errors, 'unterminated_extents_preserved': tails,
            'complete_closed800_mechanics': bool(complete and not errors),
            'single_arm_primary16of16_at800': bool(complete and not errors and final['rows'] == 16
                                                   and final['primary_canonical_plus_actual_EOS'] == 16),
            'checkpoint_pin': closed.get('checkpoint') if closed else None,
            'tensor_Adam_recount': 'PENDING exact checkpoint bytes; source-recorded reload equality is not independent tensor proof.',
            'initial_function_parity_scope': 'Saved producer equality flags plus identical per-question latent tensor fingerprints; raw latent arrays not present.',
            'limits': ['Allowed TRAIN numeric fit only; no capability, generalization, advantage, notebook dependence, stopping or activation qualification.',
                       'Global TRAIN800 logged updates and participation/Adam counters are separate evidence; not every sparse Adam state must have800 steps.',
                       'Observed generation outputs are saved once, never re-tokenized, decoded or rescored by a model here.'],
            'model_calls': 0, 'tokenizer_calls': 0, 'optimizer_calls': 0, 'GPU_calls': 0, 'queue_operations': 0,
            'raw_evidence_training_eligible': False,
            'checker_sha256': sha(Path(__file__).read_bytes())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--seed', type=int, choices=(0, 1), required=True)
    parser.add_argument('--arm', choices=('loop', 'plain'), required=True)
    parser.add_argument('--job')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = checked(args.output, OWN)
    result = recount(args.run, args.seed, args.arm, args.job)
    data = (json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    with output.open('xb') as stream:
        stream.write(data)
    print(json.dumps({'output': str(output), 'sha256': sha(data), 'errors': len(result['raw_metadata_errors']),
                      'complete': result['complete_closed800_mechanics'],
                      'final_primary': result['stages']['800']['primary_canonical_plus_actual_EOS']}, sort_keys=True))
