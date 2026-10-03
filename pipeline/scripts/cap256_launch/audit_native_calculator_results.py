"""Independent stdlib recount of copied native calculator/baseline receipts.

Input is a local manifest of absolute file/SHA pins. It never imports model or
evaluator code. Fresh pins are opened only after a complete independent TRAIN
gate and matching calculator closure. A first pass can authorize transferring
fresh evidence without having those files locally yet.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


class AuditError(ValueError): pass


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class Files:
    def __init__(self): self.opened = []
    def bytes(self, pin, label):
        if type(pin) is not dict or set(pin) != {'path', 'sha256'} or not Path(pin['path']).is_absolute():
            raise AuditError('absolute local path/SHA pin required: ' + label)
        path = Path(pin['path']); content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != pin['sha256']:
            raise AuditError('copied bytes/hash differ: ' + label)
        self.opened.append({'label': label, **pin})
        return content
    def json(self, pin, label): return json.loads(self.bytes(pin, label))
    def lines(self, pin, label):
        return [json.loads(line) for line in self.bytes(pin, label).splitlines()]


def target(row, frame):
    op = row.get('operation'); operands = row.get('operands')
    if (op not in ('add', 'sub', 'subtract') or type(operands) is not list or len(operands) != 2
            or any(type(n) is not int or not 10 <= n <= 99 for n in operands)
            or operands[0] == operands[1] or row.get('independently_verified') is not True):
        raise AuditError('checked distinct two-digit task metadata required: ' + frame['id'])
    answer = operands[0] + operands[1] if op == 'add' else operands[0] - operands[1]
    if not 10 <= answer <= 99 or row.get('canonical_numeric_target') != str(answer):
        raise AuditError('independent arithmetic differs: ' + frame['id'])
    registry = frame['numeric_registry']; refs = []
    for operand in operands:
        choices = [entry['id'] for entry in registry if entry.get('source') == 'literal'
            and entry.get('status') == 'OK' and entry.get('value') == operand]
        if len(choices) != 1: raise AuditError('operand source span not uniquely bound')
        refs.append(choices[0])
    return 'ADD' if op == 'add' else 'SUB', refs, answer


def validate_frames(frames, rows, count):
    if (type(frames) is not list or len(frames) != count or len({f['id'] for f in frames}) != count
            or set(rows) != {frame['id'] for frame in frames}):
        raise AuditError('fixed unique frame/metadata panel differs')
    for frame in frames:
        row = rows[frame['id']]
        if (frame.get('frame_sha256') != canonical({k: v for k, v in frame.items() if k != 'frame_sha256'})
                or frame.get('question') != row.get('question')
                or frame.get('question_sha256') != hashlib.sha256(frame['question'].encode()).hexdigest()
                or frame.get('question_sha256') != row.get('question_sha256')
                or frame.get('notebook_ids') != [[]] or frame.get('notebook_mask') != [[]]
                or frame.get('input_mask') != [[True] * len(frame['input_ids'][0])]
                or frame.get('label_mask') != [[True] * len(frame['labels'][0])]
                or not 1 <= len(frame['input_ids'][0]) <= 48 or not 1 <= len(frame['labels'][0]) <= 32
                or frame['canonical_numeric_target'] != row['canonical_numeric_target']):
            raise AuditError('frame hash/question/tensor qualification differs: ' + frame['id'])
        target(row, frame)


def strict_final(record, frame):
    expected = frame['labels'][0]; eos = expected[-1]; ids = record.get('MODEL_generated_ids_with_observed_EOS')
    options = record.get('native_generation_options')
    valid = (type(expected) is list and expected and all(type(n) is int and n >= 0 for n in expected)
        and expected.count(eos) == 1 and type(ids) is list and 0 < len(ids) <= 32
        and all(type(n) is int and n >= 0 for n in ids) and ids.count(eos) == 1 and ids[-1] == eos
        and record.get('MODEL_raw_generate_ids') == [ids]
        and record.get('MODEL_native_decoder_return') == [ids[:-1]]
        and record.get('native_generate_call_count') == 1 and record.get('native_call_contract_valid') is True
        and record.get('raw_output_single_typed_sequence') is True
        and record.get('native_stripped_output_equal') is True and record.get('observed_EOS') is True
        and record.get('EOS_positions') == [len(ids) - 1] and record.get('generation_error') is None
        and record.get('termination_reason') == 'observed_EOS' and type(options) is dict
        and set(options) == {'max_new_tokens', 'do_sample', 'use_cache', 'bos_token_id', 'eos_token_id', 'pad_token_id'}
        and options['max_new_tokens'] == 32 and options['do_sample'] is False and options['use_cache'] is True
        and options['eos_token_id'] == options['pad_token_id'] == eos
        and type(options['bos_token_id']) is int and options['bos_token_id'] >= 0)
    return bool(valid and ids == expected), bool(valid)


def trace_recount(record, frame, row):
    desired_op, desired_refs, answer = target(row, frame)
    traces = record.get('predicted_trace')
    if type(traces) is not list or len(traces) != 4:
        raise AuditError('four calculator loop traces required')
    eligible = [dict(entry) for entry in frame['numeric_registry']]
    counters = Counter(); loop_checks = []; mechanical_errors = []
    correct_call = op_chosen = refs_chosen = host_answer = copied_tool = False
    query_n = len(frame['input_ids'][0]); eos = frame['labels'][0][-1]
    for loop, call in enumerate(traces):
        if (call.get('loop_index') != loop or call.get('call_index') != loop + 1
                or call.get('candidate_ids') != [entry['id'] for entry in eligible]
                or call.get('value_slot') != query_n + 2 * loop
                or call.get('status_slot') != query_n + 2 * loop + 1
                or call.get('original_query_unchanged_on_insert') is not True
                or call.get('policy_features') != 'h+e'):
            mechanical_errors.append('loop%d geometry/candidate/advance metadata differs' % loop)
        action, status, refs = call.get('action'), call.get('status'), call.get('refs')
        if action not in ('NONE', 'ADD', 'SUB') or status not in ('NONE', 'OK', 'ERROR'):
            mechanical_errors.append('loop%d invalid action/status' % loop)
        counters['action_' + str(action)] += 1; counters['status_' + str(status)] += 1
        if action != 'NONE': counters['requested_calls'] += 1
        if status == 'ERROR': counters['error_' + str(call.get('error_code'))] += 1
        op = action == desired_op
        bound = type(refs) is list and len(refs) == 2 and all(type(ref) is str for ref in refs)
        original_refs = bool(op and bound and (set(refs) == set(desired_refs) if desired_op == 'ADD' else refs == desired_refs))
        op_chosen |= op; refs_chosen |= original_refs
        byid = {entry['id']: entry for entry in eligible}
        available = bool(bound and refs[0] != refs[1] and all(ref in byid for ref in refs))
        if action == 'NONE':
            if (status != 'NONE' or refs != [] or call.get('result') is not None
                    or call.get('left_index') is not None or call.get('right_index') is not None):
                mechanical_errors.append('loop%d NONE trace malformed' % loop)
        elif bound:
            for key, ref in zip(('left_index', 'right_index'), refs):
                index = call.get(key)
                if type(index) is not int or not 0 <= index < len(eligible) or eligible[index]['id'] != ref:
                    mechanical_errors.append('loop%d pointer index/ref mismatch' % loop)
        numeric_correct = False
        if status == 'OK':
            result = call.get('result')
            values = [byid[ref]['value'] for ref in refs] if available else None
            arithmetic = values[0] + values[1] if values is not None and action == 'ADD' else (
                values[0] - values[1] if values is not None and action == 'SUB' else None)
            sound = (available and type(result) is dict and type(result.get('value')) is int
                and result['value'] == arithmetic and call.get('operand_values') == values
                and call.get('ordered_references') == refs and call.get('resolved_references') == refs
                and result.get('id') == 'result:%d' % (loop + 1) and result.get('index') == len(eligible)
                and result.get('source') == 'result' and result.get('status') == 'OK'
                and result.get('source_call_index') == loop + 1 and result.get('operand_references') == refs
                and type(call.get('numeric_token_id')) is int and call['numeric_token_id'] >= 0
                and call['numeric_token_id'] != eos and call.get('value_content_zero') is False)
            if not sound:
                mechanical_errors.append('loop%d OK exact host integer/provenance differs' % loop)
            else:
                numeric_correct = original_refs and result['value'] == answer
                host_answer |= result['value'] == answer
                copied_tool |= record.get('MODEL_generated_ids_with_observed_EOS') == [call['numeric_token_id'], eos]
                eligible.append({**result, 'slot_index': query_n + 2 * loop, 'token_indices': [query_n + 2 * loop]})
        elif call.get('result') is not None or call.get('value_content_zero') is not True:
            mechanical_errors.append('loop%d non-OK carried numeric result' % loop)
        correct_call |= numeric_correct
        loop_checks.append({'loop': loop, 'action': action, 'status': status, 'refs': refs,
            'host_result': call['result'].get('value') if type(call.get('result')) is dict else None,
            'task_operation_chosen': op, 'task_original_refs_chosen': original_refs,
            'correct_equivalent_task_call': numeric_correct})
    return {'task_operation_chosen': op_chosen, 'task_original_refs_chosen': refs_chosen,
        'equivalent_task_call_correct': correct_call, 'any_OK_host_result_equals_answer': host_answer,
        'final_copies_any_OK_tool_token': copied_tool, 'calls': dict(counters),
        'loop_checks': loop_checks, 'mechanical_errors': mechanical_errors}


def recount(records, frames, rows, phase, endpoint_packet, kind, config_hash, endpoints_hash, protocol_hash, identity=None):
    count = 10 if phase == 'TRAIN' else 16
    if len(records) != 2 * count: raise AuditError('%s raw must contain%d records' % (phase, 2 * count))
    endpoints = endpoint_packet['endpoints']; scores = []; answers = []; issues = []
    for seed in (0, 1):
        endpoint = next(entry for entry in endpoints if entry['seed'] == seed)
        total = Counter(); calls = Counter()
        for offset, frame in enumerate(frames):
            record = records[seed * count + offset]
            expected_index = (20 if phase == 'FRESH' else 0) + seed * count + offset + 1
            if (record.get('call_index') != expected_index or record.get('seed') != seed
                    or record.get('id') != frame['id'] or record.get('phase') != phase
                    or record.get('arm') != kind or record.get('total_advances') != 4
                    or record.get('native_generate_call_count') != 1
                    or record.get('frame_sha256') != frame['frame_sha256']
                    or record.get('checkpoint_sha256') != endpoint['checkpoint']['sha256']
                    or record.get('config_sha256') != config_hash
                    or record.get('endpoints_sha256') != endpoints_hash
                    or record.get('protocol_sha256') != protocol_hash):
                issues.append('%s seed%d row%s sequence/provenance differs' % (phase, seed, frame['id']))
            if identity is not None and any(record.get(key) != value for key, value in identity.items()):
                issues.append('%s seed%d row%s code/runtime identity differs' % (phase, seed, frame['id']))
            exact, native_valid = strict_final(record, frame)
            detail = trace_recount(record, frame, rows[frame['id']]) if kind == 'calculator' else {}
            total['strict_final_correct'] += int(exact); total['native_observation_valid'] += int(native_valid)
            full = record.get('MODEL_generated_ids_with_observed_EOS')
            total['final_nonempty'] += int(type(full) is list and any(token != frame['labels'][0][-1] for token in full))
            total['observed_EOS'] += int(record.get('observed_EOS') is True)
            if kind == 'calculator':
                for key in ('task_operation_chosen', 'task_original_refs_chosen', 'equivalent_task_call_correct',
                            'any_OK_host_result_equals_answer', 'final_copies_any_OK_tool_token'):
                    total[key] += int(detail[key])
                total['combined_correct'] += int(exact and detail['equivalent_task_call_correct'])
                total['correct_task_call_but_wrong_final'] += int(detail['equivalent_task_call_correct'] and not exact)
                total['correct_final_without_correct_task_call'] += int(exact and not detail['equivalent_task_call_correct'])
                total['correct_host_answer_but_wrong_final'] += int(detail['any_OK_host_result_equals_answer'] and not exact)
                calls.update(detail['calls'])
                issues.extend('%s seed%d row%s %s' % (phase, seed, frame['id'], message)
                    for message in detail['mechanical_errors'])
            elif record.get('tool_calls') != 0:
                issues.append('baseline raw unexpectedly contains tool calls')
            answers.append({'seed': seed, 'id': frame['id'], 'strict_final_correct': exact,
                'native_observation_valid': native_valid, 'final_ids': record.get('MODEL_generated_ids_with_observed_EOS'),
                'target_ids': frame['labels'][0], **detail})
        scores.append({'seed': seed, 'rows': count, **dict(total), 'call_breakdown': dict(calls)})
    return {'results': scores, 'rows': answers, 'issues': issues}


def check_saved_scores(saved, audited, kind):
    if len(saved) != len(audited['rows']): return ['saved score count differs from raw recount']
    errors = []
    for declared, independent in zip(saved, audited['rows']):
        if (declared.get('seed'), declared.get('id')) != (independent['seed'], independent['id']):
            errors.append('saved score row order differs'); continue
        keys = ['strict_final_correct'] + (['equivalent_task_call_correct'] if kind == 'calculator' else [])
        if any(declared.get(key) is not independent[key] for key in keys):
            errors.append('saved score disagrees seed%d row%s' % (independent['seed'], independent['id']))
        if kind == 'calculator' and declared.get('combined_correct') is not (
                independent['strict_final_correct'] and independent['equivalent_task_call_correct']):
            errors.append('saved combined score disagrees')
    return errors


def host_order(evidence, kind, phase):
    entry = evidence.get(kind, {}).get(phase)
    if entry is None: return {'status': 'NOT_INDEPENDENTLY_OBSERVED',
        'limit': 'Hash equality and pinned raw-first code support ordering; local copy times do not prove host write order.'}
    raw_done, scored_born = entry['raw_last_write_utc'], entry['scored_creation_utc']
    return {'status': 'PASS' if raw_done <= scored_born else 'FAIL',
        'raw_last_write_utc': raw_done, 'scored_creation_utc': scored_born,
        'source': 'owner-provided host filesystem observation'}


def audit(manifest):
    files = Files(); issues = []; sources = []
    calculator = manifest['calculator']; cfg = files.json(calculator['config'], 'calculator config')
    endpoints = files.json(calculator['endpoints'], 'calculator endpoints')
    closed = files.json(calculator['closed'], 'calculator CLOSED')
    protocol = files.json(calculator['protocol'], 'calculator protocol')
    config_hash = calculator['config']['sha256']; endpoint_hash = calculator['endpoints']['sha256']
    protocol_hash = calculator['protocol']['sha256']
    if (endpoints.get('train_config_sha256') != config_hash or endpoints.get('protocol_sha256') != protocol_hash
            or cfg['evaluation_protocol']['sha256'] != protocol_hash or closed.get('config_sha256') != config_hash
            or closed.get('endpoints_sha256') != endpoint_hash or closed.get('protocol_sha256') != protocol_hash
            or closed.get('endpoints') != endpoints['endpoints'] or closed.get('closed') is not True
            or closed.get('optimizer_updates') != 0 or closed.get('teacherforced_examples') != 0
            or protocol.get('fit_gate') != 'both-seeds-all10-correct-equivalent-task-call-and-strict-final'
            or protocol.get('latent_advances') != 4 or protocol.get('native_call_limit') != 52):
        issues.append('calculator config/endpoints/protocol/zero-update closure binding differs')
    frames = files.json(manifest['train_frames'], 'TRAIN frames')['rows']
    if manifest['train_frames']['sha256'] != cfg['frames']['sha256']:
        issues.append('TRAIN frames do not bind calculator config')
    rows = {row['id']: row for row in cfg['selected_rows']}; validate_frames(frames, rows, 10)
    for label, code in manifest.get('code_files', {}).items():
        files.bytes(code['local'], 'code ' + label)
        if code['local']['sha256'] != code['expected_sha256']: issues.append('code pin differs: ' + label)
        if code.get('config_key') is not None and code['expected_sha256'] != cfg[code['config_key']]['sha256']:
            issues.append('code pin is not bound to calculator config: ' + label)
        sources.append({'kind': 'code', 'name': label, 'sha256': code['local']['sha256']})
    calculator_source_seeds = []
    for source in manifest.get('source_closures', []):
        receipt = files.json(source['local'], 'source closure ' + source['kind'] + str(source['seed']))
        expected = source['expected']
        if source['local']['sha256'] != expected['closed']['sha256'] or receipt.get('checkpoint') != expected['checkpoint']:
            issues.append('source/endpoint closure pin differs: ' + source['kind'] + str(source['seed']))
        if source['kind'] == 'calculator':
            calculator_source_seeds.append(source['seed'])
            binding = next(entry for entry in endpoints['endpoints'] if entry['seed'] == source['seed'])
            original = next(entry for entry in cfg['sources'] if entry['seed'] == source['seed'])
            if (expected != binding or receipt.get('closed') is not True
                    or receipt.get('config_sha256') != config_hash
                    or receipt.get('source_checkpoint_sha256') != original['checkpoint']['sha256']
                    or receipt.get('optimizer_updates') != 11264 or receipt.get('additional_optimizer_updates') != 1024
                    or receipt.get('optimizer_updates_this_process') != 1024 or receipt.get('model_calls') != 1024
                    or sum(receipt.get('model_call_account', {}).values()) != 1024):
                issues.append('calculator endpoint update/source/model-call accounting differs')
        sources.append({'kind': source['kind'], 'seed': source['seed'],
            'optimizer_updates': receipt.get('optimizer_updates'),
            'additional_optimizer_updates': receipt.get('additional_optimizer_updates'),
            'training_model_calls': receipt.get('model_calls'), 'checkpoint': receipt.get('checkpoint'),
            'prior_failed_attempt_optimizer_updates': receipt.get('prior_failed_attempt_optimizer_updates', 0),
            'prior_failed_attempt_model_calls': receipt.get('prior_failed_attempt_model_calls', 0),
            'exact_replay_update_matches': receipt.get('exact_replay_update_matches'),
            'config_sha256': receipt.get('config_sha256'), 'source_checkpoint_sha256': receipt.get('source_checkpoint_sha256')})
    if sorted(calculator_source_seeds) != [0, 1]:
        issues.append('both unique calculator trained endpoint closures required for source/count audit')
    records = files.lines(calculator['train_raw'], 'calculator TRAIN raw')
    calc_identity = {'runner_sha256': cfg['evaluation_runner']['sha256'],
        'runtime_sha256': cfg['runtime_module']['sha256'], 'calculator_tools_sha256': cfg['calculator_tools']['sha256'],
        'architecture_contract_sha256': cfg['architecture_contract']['sha256']}
    calc_train = recount(records, frames, rows, 'TRAIN', endpoints, 'calculator', config_hash, endpoint_hash, protocol_hash, calc_identity)
    issues.extend(calc_train['issues'])
    saved = files.lines(calculator['train_answers'], 'calculator TRAIN scored')
    issues.extend(check_saved_scores(saved, calc_train, 'calculator'))
    for key, filename in (('train_raw', 'TRAIN-OBSERVATIONS.jsonl'), ('train_answers', 'TRAIN-ANSWERS.jsonl')):
        if closed.get('file_sha256', {}).get(filename) != calculator[key]['sha256']:
            issues.append('calculator CLOSED frozen file hash differs: ' + filename)
    gate = all(seed.get('combined_correct') == 10 for seed in calc_train['results'])
    if type(closed.get('fit_gate_passed')) is not bool or closed['fit_gate_passed'] != gate:
        issues.append('calculator declared fit gate differs from independent raw recount')
    if closed.get('native_calls') != (52 if gate else 20) or closed.get('fresh_native_calls') != (32 if gate else 0):
        issues.append('calculator gated native call counts differ')
    if closed.get('raw_frozen_before_scoring') is not True:
        issues.append('calculator closure lacks raw-before-score declaration')
    fit = files.json(calculator['fit_gate'], 'calculator saved FIT-GATE')
    if (fit.get('fit_gate_passed') != gate or fit.get('train_observations_sha256') != calculator['train_raw']['sha256']
            or fit.get('config_sha256') != config_hash): issues.append('saved FIT-GATE binding/recount differs')
    if closed.get('file_sha256', {}).get('FIT-GATE.json') != calculator['fit_gate']['sha256']:
        issues.append('calculator CLOSED frozen FIT-GATE hash differs')
    train_order = host_order(manifest.get('host_file_order', {}), 'calculator', 'TRAIN')
    if train_order['status'] == 'FAIL': issues.append('host TRAIN raw final write followed first gold score file creation')
    calc_errors = list(issues)
    fresh_authorized = gate and not calc_errors
    report = {'schema': 'premonition.native-independent-audit.v1',
        'calculator_TRAIN': calc_train, 'independent_calculator_fit_gate': gate,
        'fresh_transfer_authorized': fresh_authorized, 'fresh_files_accessed': False,
        'calculator_fresh': 'NOT_LOCALLY_AVAILABLE' if fresh_authorized else 'UNUSED_GATE_FAILED',
        'sources': sources, 'issues': issues,
        'raw_before_gold': {'calculator_TRAIN': train_order},
        'limits': ['No model/checkpoint tensors/tokenizer are loaded. Checkpoint bytes unchanged are owner observations, unless separately supplied.',
            'Canonical numeric label tokenization is adopted from the frozen frame qualification; arithmetic is recomputed independently.',
            'No claim of unknown-live checking or generalization follows from TRAIN scores.'],
        'execution': {'model_calls': 0, 'optimizer_updates': 0, 'GPU_calls': 0, 'SSH_calls': 0}}
    fresh_frames = None; fresh_rows = None
    if fresh_authorized and 'fresh_frames' in manifest and 'fresh_raw' in calculator:
        # The sole fresh-file read/hash path; independent TRAIN recount precedes it.
        fresh_frames = files.json(manifest['fresh_frames'], 'authorized FRESH frames')['rows']
        if manifest['fresh_frames']['sha256'] != cfg['fresh_frames']['sha256']:
            issues.append('fresh frame pin differs from calculator config')
        fresh_rows = {frame['id']: frame for frame in fresh_frames}; validate_frames(fresh_frames, fresh_rows, 16)
        fresh_records = files.lines(calculator['fresh_raw'], 'calculator FRESH raw')
        fresh = recount(fresh_records, fresh_frames, fresh_rows, 'FRESH', endpoints, 'calculator', config_hash, endpoint_hash, protocol_hash, calc_identity)
        issues.extend(fresh['issues'])
        issues.extend(check_saved_scores(files.lines(calculator['fresh_answers'], 'calculator FRESH scored'), fresh, 'calculator'))
        for key, filename in (('fresh_raw', 'FRESH-OBSERVATIONS.jsonl'), ('fresh_answers', 'FRESH-ANSWERS.jsonl')):
            if closed['file_sha256'].get(filename) != calculator[key]['sha256']: issues.append('calculator frozen fresh hash differs')
        report['calculator_fresh'] = fresh; report['fresh_files_accessed'] = True
        report['raw_before_gold']['calculator_FRESH'] = host_order(manifest.get('host_file_order', {}), 'calculator', 'FRESH')
        if report['raw_before_gold']['calculator_FRESH']['status'] == 'FAIL': issues.append('host calculator FRESH raw/score order failed')
    baseline = manifest.get('baseline')
    if baseline is not None:
        bc = files.json(baseline['config'], 'baseline native config')
        be = files.json(baseline['endpoints'], 'baseline endpoints')
        bz = files.json(baseline['closed'], 'baseline CLOSED')
        bp = files.json(baseline['protocol'], 'baseline comparison protocol')
        bch, beh, bph = baseline['config']['sha256'], baseline['endpoints']['sha256'], baseline['protocol']['sha256']
        baseline_gate = bz.get('fit_gate_passed')
        if (bc['frames']['sha256'] != manifest['train_frames']['sha256'] or bc['calculator_config']['sha256'] != config_hash
                or bc['evaluation_protocol']['sha256'] != bph or be.get('comparison_protocol_sha256') != bph
                or bp.get('baseline_endpoints') != be['endpoints'] or bp.get('calculator_endpoints') != endpoints['endpoints']
                or be.get('calculator_endpoints') != endpoints['endpoints'] or bz.get('config_sha256') != bch
                or bz.get('endpoints_sha256') != beh or bz.get('protocol_sha256') != bph
                or bz.get('closed') is not True or bz.get('optimizer_updates') != 0 or bz.get('teacherforced_examples') != 0
                or bz.get('tool_calls') != 0 or type(baseline_gate) is not bool or (baseline_gate and not gate)
                or bz.get('native_calls') != (52 if baseline_gate else 20)
                or bz.get('fresh_native_calls') != (32 if baseline_gate else 0)):
            issues.append('baseline shared questions/comparison protocol/gated counters differ')
        baseline_sources = [source for source in manifest.get('source_closures', []) if source['kind'] == 'primitive_baseline']
        if sorted(source['seed'] for source in baseline_sources) != [0, 1]:
            issues.append('both unique baseline trained endpoint closures required for source/count audit')
        for source in baseline_sources:
            receipt = files.json(source['local'], 'baseline verified endpoint ' + str(source['seed']))
            binding = next(entry for entry in be['endpoints'] if entry['seed'] == source['seed'])
            if (source['expected'] != binding or receipt.get('closed') is not True
                    or receipt.get('config_sha256') != bc['baseline_training_config']['sha256']
                    or receipt.get('optimizer_updates') != 11264 or receipt.get('additional_optimizer_updates') != 1024
                    or receipt.get('model_calls') != 1024 or sum(receipt.get('model_call_account', {}).values()) != 1024):
                issues.append('baseline endpoint update/model-call accounting differs')
        br = files.lines(baseline['train_raw'], 'baseline TRAIN raw')
        baseline_identity = {'runner_sha256': bc['evaluation_runner']['sha256']}
        bt = recount(br, frames, rows, 'TRAIN', be, 'primitive_baseline', bch, beh, bph, baseline_identity)
        issues.extend(bt['issues']); issues.extend(check_saved_scores(files.lines(baseline['train_answers'], 'baseline TRAIN scored'), bt, 'primitive_baseline'))
        report['baseline_TRAIN'] = bt
        for key, filename in (('train_raw', 'TRAIN-OBSERVATIONS.jsonl'), ('train_answers', 'TRAIN-ANSWERS.jsonl')):
            if bz.get('file_sha256', {}).get(filename) != baseline[key]['sha256']: issues.append('baseline frozen TRAIN hash differs')
        for calc_record, baseline_record in zip(records, br):
            if calc_record.get('native_generation_options') != baseline_record.get('native_generation_options'):
                issues.append('baseline/calculator greedy BOS/EOS/max32 native options differ')
        report['raw_before_gold']['baseline_TRAIN'] = host_order(manifest.get('host_file_order', {}), 'baseline', 'TRAIN')
        if report['raw_before_gold']['baseline_TRAIN']['status'] == 'FAIL': issues.append('host baseline TRAIN raw/score order failed')
        if fresh_authorized and baseline_gate and fresh_frames is not None and 'fresh_raw' in baseline:
            bfr = files.lines(baseline['fresh_raw'], 'baseline FRESH raw')
            bf = recount(bfr, fresh_frames, fresh_rows, 'FRESH', be, 'primitive_baseline', bch, beh, bph, baseline_identity)
            issues.extend(bf['issues']); issues.extend(check_saved_scores(files.lines(baseline['fresh_answers'], 'baseline FRESH scored'), bf, 'primitive_baseline'))
            report['baseline_fresh'] = bf
            for key, filename in (('fresh_raw', 'FRESH-OBSERVATIONS.jsonl'), ('fresh_answers', 'FRESH-ANSWERS.jsonl')):
                if bz.get('file_sha256', {}).get(filename) != baseline[key]['sha256']: issues.append('baseline frozen fresh hash differs')
            report['raw_before_gold']['baseline_FRESH'] = host_order(manifest.get('host_file_order', {}), 'baseline', 'FRESH')
            if report['raw_before_gold']['baseline_FRESH']['status'] == 'FAIL': issues.append('host baseline FRESH raw/score order failed')
        else: report['baseline_fresh'] = 'NOT_LOCALLY_AVAILABLE' if baseline_gate else 'UNUSED_AT_BASELINE_EXECUTION'
    report['opened_files'] = files.opened
    report['audit_passed'] = not issues
    report['verified_native_calls'] = 20 + (32 if report['fresh_files_accessed'] else 0) + (
        20 + (32 if isinstance(report.get('baseline_fresh'), dict) else 0) if baseline is not None else 0)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--manifest', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); manifest_path = Path(args.manifest); output = Path(args.output)
    if output.exists(): raise SystemExit('existing report preserved; choose a new output path')
    try:
        result = audit(json.loads(manifest_path.read_bytes()))
        result['manifest_sha256'] = file_sha(manifest_path)
    except Exception as error:
        result = {'schema': 'premonition.native-independent-audit.v1', 'audit_passed': False,
            'fresh_transfer_authorized': False, 'error_type': type(error).__name__, 'error': str(error),
            'execution': {'model_calls': 0, 'optimizer_updates': 0, 'GPU_calls': 0, 'SSH_calls': 0}}
    with output.open('x') as stream: json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'audit_passed': result['audit_passed'], 'fresh_transfer_authorized': result['fresh_transfer_authorized'],
        'output': str(output)}, sort_keys=True))
    raise SystemExit(0 if result['audit_passed'] else 2)
