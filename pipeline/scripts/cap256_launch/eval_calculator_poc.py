"""Native calculator qualification: TRAIN20, then strictly gated fresh32.

No loss, optimizer, labels or desired calls enter generation. Each complete
stage's raw observations are durable before its oracle is consulted. The fresh
frame file is neither opened nor hashed until BOTH TRAIN gates pass.
"""
import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

SEEDS = (0, 1)
TERMINAL_RESERVE = 4 * 1024 ** 2
PROTOCOL_REQUIRED = {
    'schema': 'cap256.calculator-evaluation.v1', 'seeds': [0, 1],
    'execution_order': [[0, 'calculator'], [1, 'calculator']],
    'train_rows': 10, 'fresh_rows': 16, 'train_native_calls': 20,
    'fresh_native_calls': 32, 'native_call_limit': 52,
    'teacherforced_examples': 0, 'optimizer_updates': 0,
    'latent_advances': 4, 'max_new_tokens': 32,
    'fit_gate': 'both-seeds-all10-correct-equivalent-task-call-and-strict-final',
    'addition_refs_order_equivalent': True, 'subtraction_refs_ordered': True,
    'fresh_after_fit_gate_only': True,
}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def canonical(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def safe(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('root-relative owned path required')
    result = (root / path).resolve()
    if not result.is_relative_to(root):
        raise ValueError('path outside root')
    return result


def pin(root, value):
    if (type(value) is not dict or set(value) != {'path', 'sha256'}
            or not re.fullmatch('[0-9a-f]{64}', value.get('sha256', ''))):
        raise ValueError('exact path/SHA256 pin required')
    path = safe(root, value['path'])
    if sha(path) != value['sha256']:
        raise ValueError('pinned bytes differ: ' + value['path'])
    return path


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_protocol(protocol):
    for key, expected in PROTOCOL_REQUIRED.items():
        actual = protocol.get(key)
        if type(actual) is not type(expected) or actual != expected:
            raise ValueError('frozen evaluation protocol differs: ' + key)


def desired_call(row, registry):
    operation = row.get('operation')
    if operation not in ('add', 'sub', 'subtract'):
        raise ValueError('independently checked direct add/sub metadata required')
    operands = row.get('operands')
    if (type(operands) is not list or len(operands) != 2
            or any(type(value) is not int or not 10 <= value <= 99 for value in operands)
            or operands[0] == operands[1] or row.get('independently_verified') is not True):
        raise ValueError('two distinct checked positive two-digit operands required')
    result = sum(operands) if operation == 'add' else operands[0] - operands[1]
    if not 10 <= result <= 99 or row.get('canonical_numeric_target') != str(result):
        raise ValueError('checked exact integer target differs')
    refs = []
    for value in operands:
        matches = [literal['id'] for literal in registry if literal.get('source') == 'literal'
            and literal.get('status') == 'OK' and literal.get('value') == value]
        if len(matches) != 1:
            raise ValueError('task operand must bind one original literal span')
        refs.append(matches[0])
    return ('ADD' if operation == 'add' else 'SUB'), refs, operands, result


def score_trace(trace, row, registry):
    """Independent operation, ordered-ref and integer-result checks after raw save."""
    if (type(trace) is not list or len(trace) != 4
            or [entry.get('loop_index') for entry in trace] != list(range(4))):
        raise ValueError('four sequential native loop traces required')
    action, refs, operands, target = desired_call(row, registry)
    byid = {entry['id']: entry for entry in registry}
    operation_correct = references_correct = result_correct = False
    loop_checks = []
    for entry in trace:
        actual_refs = entry.get('refs')
        op_correct = entry.get('status') == 'OK' and entry.get('action') == action
        bound_refs = (type(actual_refs) is list and len(actual_refs) == 2
            and all(type(reference) is str for reference in actual_refs))
        refs_correct = bool(op_correct and bound_refs and (
            set(actual_refs) == set(refs) if action == 'ADD' else actual_refs == refs))
        expected_values = [byid[reference]['value'] for reference in actual_refs] if (
            bound_refs and all(type(reference) is str and reference in byid for reference in actual_refs)) else None
        value = entry.get('result')
        numeric_correct = bool(refs_correct and expected_values is not None
            and entry.get('operand_values') == expected_values and type(value) is dict
            and type(value.get('value')) is int and value['value'] == target
            and value.get('source') == 'result' and value.get('status') == 'OK')
        operation_correct |= op_correct
        references_correct |= refs_correct
        result_correct |= numeric_correct
        loop_checks.append({'loop_index': entry['loop_index'], 'operation_correct': op_correct,
            'references_correct': refs_correct, 'result_correct': numeric_correct})
    return {'desired_action': action, 'desired_original_refs': refs, 'desired_operands': operands,
        'desired_result': target, 'operation_correct': operation_correct,
        'references_correct': references_correct, 'result_correct': result_correct,
        'equivalent_task_call_correct': result_correct, 'loop_checks': loop_checks}


def score_saved(records, frames, metadata, phase, scorer, eos_id, call_start=0):
    """Score a frozen complete stage; no model calls and no runtime inputs."""
    count = 10 if phase == 'TRAIN' else 16
    if (phase not in ('TRAIN', 'FRESH') or len(frames) != count or len(records) != 2 * count
            or len({frame['id'] for frame in frames}) != count
            or set(metadata) != {frame['id'] for frame in frames}):
        raise ValueError('complete two-seed fixed stage required')
    answers, results = [], []
    for seed_slot, seed in enumerate(SEEDS):
        summary = {'seed': seed, 'rows': count, 'operation_correct': 0, 'references_correct': 0,
            'result_correct': 0, 'equivalent_task_call_correct': 0, 'strict_final_correct': 0,
            'combined_correct': 0}
        for offset, frame in enumerate(frames):
            index = seed_slot * count + offset
            record = records[index]
            if (record.get('call_index') != call_start + index + 1 or record.get('seed') != seed
                    or record.get('id') != frame['id'] or record.get('phase') != phase
                    or record.get('total_advances') != 4 or record.get('native_generate_call_count') != 1):
                raise ValueError('saved native sequence/seed/frame/four-loop binding differs')
            trace = score_trace(record['predicted_trace'], metadata[frame['id']], frame['numeric_registry'])
            strict_final = bool(record.get('native_call_contract_valid') is True
                and record.get('raw_output_single_typed_sequence') is True
                and record.get('generation_error') is None
                and scorer(record, frame['labels'][0], eos_id))
            combined = trace['equivalent_task_call_correct'] and strict_final
            answer = {**record, **trace, 'strict_final_correct': strict_final,
                'combined_correct': combined, 'canonical_target_ids_with_EOS': frame['labels'][0]}
            answers.append(answer)
            for key in ('operation_correct', 'references_correct', 'result_correct', 'equivalent_task_call_correct'):
                summary[key] += int(trace[key])
            summary['strict_final_correct'] += int(strict_final)
            summary['combined_correct'] += int(combined)
        results.append(summary)
    return results, answers


def fit_gate_passed(results):
    if (type(results) is not list or len(results) != 2
            or [result.get('seed') for result in results] != list(SEEDS)
            or any(result.get('rows') != 10 for result in results)):
        raise ValueError('two complete frozen TRAIN10 seed results required')
    return all(type(result.get('combined_correct')) is int and result['combined_correct'] == 10
        for result in results)


def gated_fresh(train_results, load_fresh, observe_fresh):
    """Both callbacks are unreachable on a failed fit gate, including file hashing."""
    if not fit_gate_passed(train_results):
        return None
    return observe_fresh(load_fresh())


def qualify_targets(frames, tokenizer, eos_id):
    """Post-observation oracle target qualification; never used as a model input."""
    for frame in frames:
        expected = tokenizer.encode(frame['canonical_numeric_target'], add_special_tokens=False)
        if (type(expected) is not list or not expected or eos_id in expected
                or any(type(token) is not int or token < 0 for token in expected)
                or frame['labels'] != [expected + [eos_id]]):
            raise ValueError('frozen exact canonical numeric target/EOS differs')


def validate_frames(frames, count, metadata=None):
    if type(frames) is not list or len(frames) != count or len({f['id'] for f in frames}) != count:
        raise ValueError('exact unique frozen frame count required')
    for frame in frames:
        row = metadata[frame['id']] if metadata is not None else frame
        if (frame.get('frame_sha256') != canonical({k: v for k, v in frame.items() if k != 'frame_sha256'})
                or frame.get('question') != row.get('question')
                or not isinstance(frame.get('question'), str)
                or frame.get('question_sha256') != hashlib.sha256(frame['question'].encode()).hexdigest()
                or frame.get('question_sha256') != row.get('question_sha256')
                or frame.get('notebook_ids') != [[]] or frame.get('notebook_mask') != [[]]
                or not 1 <= len(frame['input_ids'][0]) <= 48 or not 1 <= len(frame['labels'][0]) <= 32
                or frame.get('input_mask') != [[True] * len(frame['input_ids'][0])]
                or frame.get('label_mask') != [[True] * len(frame['labels'][0])]
                or frame.get('canonical_numeric_target') != row.get('canonical_numeric_target')
                or type(frame.get('numeric_registry')) is not list):
            raise ValueError('untruncated question-only pinned frame differs')
        desired_call(row, frame['numeric_registry'])
    return {frame['id']: (metadata[frame['id']] if metadata is not None else frame) for frame in frames}


def run(args):
    started = time.monotonic()
    root = Path(args.root).resolve()
    config_path, endpoints_path = Path(args.config).resolve(), Path(args.endpoints).resolve()
    if (not config_path.is_relative_to(root) or not endpoints_path.is_relative_to(root)
            or sha(config_path) != args.config_sha256 or sha(endpoints_path) != args.endpoints_sha256):
        raise ValueError('root-bound immutable config/endpoints differ')
    cfg, packet = read(config_path), read(endpoints_path)
    if (cfg.get('dispatch_allowed') is not True or cfg.get('exclusive_lock_verified') is not True
            or os.environ.get('TREE') != str(root) or not os.environ.get('JOB')
            or packet.get('train_config_sha256') != args.config_sha256
            or packet.get('protocol_sha256') != cfg['evaluation_protocol']['sha256']
            or 'fresh_rows' in cfg):
        raise ValueError('exclusive driver and fresh-isolated config binding required')
    names = ('runner', 'resume_helpers', 'runtime_module', 'calculator_tools', 'source_plan',
        'source_seal', 'source_release', 'source_runner', 'frames', 'storage_snapshot',
        'architecture_contract', 'corpus_audit', 'evaluation_protocol', 'evaluation_runner')
    pins = {name: pin(root, cfg[name]) for name in names}
    if pins['evaluation_runner'] != Path(__file__).resolve():
        raise ValueError('running evaluator is not its declared pin')
    trainer = load_module(pins['runner'], '_calculator_eval_train_contract')
    trainer.validate_config(cfg)
    issues = trainer.readiness_issues(cfg)
    if issues:
        raise ValueError('; '.join(issues))
    protocol = read(pins['evaluation_protocol']); validate_protocol(protocol)
    helpers = load_module(pins['resume_helpers'], '_calculator_eval_helpers')
    old = read(pins['source_plan'])
    seal = read(pins['source_seal'])
    for relative, digest in seal['files'].items():
        pin(root, {'path': relative, 'sha256': digest})
    sealed = load_module(pins['source_runner'], '_calculator_eval_sealed')
    sealed.validate_plan(old)
    train_frames = read(pins['frames'])['rows']
    train_metadata = validate_frames(train_frames, 10, trainer.selected_by_id(cfg['selected_rows']))
    endpoints = packet.get('endpoints')
    if (type(endpoints) is not list or [(e.get('seed'), e.get('arm')) for e in endpoints]
            != [(0, 'calculator'), (1, 'calculator')]):
        raise ValueError('two exact trained calculator endpoints required')
    closed_by_seed = {}
    for endpoint in endpoints:
        cp = pin(root, endpoint['checkpoint']); closed = read(pin(root, endpoint['closed']))
        source = next(entry for entry in cfg['sources'] if entry['seed'] == endpoint['seed'])
        if (closed.get('closed') is not True or closed.get('seed') != endpoint['seed']
                or closed.get('arm') != 'calculator' or closed.get('config_sha256') != args.config_sha256
                or closed.get('optimizer_updates') != 11264
                or closed.get('additional_optimizer_updates') != 1024
                or closed.get('checkpoint') != endpoint['checkpoint']
                or closed.get('runtime_sha256') != cfg['runtime_module']['sha256']
                or closed.get('architecture_contract_sha256') != cfg['architecture_contract']['sha256']
                or closed.get('source_checkpoint_sha256') != source['checkpoint']['sha256']
                or closed.get('durable_model_and_Adam_reload_equal') is not True
                or cp.stat().st_size > cfg['budget']['checkpoint_cap_bytes']):
            raise ValueError('calculator endpoint closure/provenance differs')
        closed_by_seed[endpoint['seed']] = closed
    matrix = safe(root, cfg['output_namespace'])
    out = safe(root, cfg.get('evaluation_output_namespace', cfg['output_namespace'] + '/native-evaluation'))
    if out.exists() or not out.is_relative_to(matrix):
        raise ValueError('new matrix-contained evaluation namespace required; preserve existing evidence')
    storage = load_module(pins['storage_snapshot'], '_calculator_eval_storage')
    unit = storage.filesystem_allocation_unit(root)
    extras = [safe(root, path) for path in cfg['output_accounting_extra_paths']]
    budget = cfg['budget']; wall_cap = budget.get('evaluation_seconds', 600)
    if type(wall_cap) is not int or not 0 < wall_cap <= 600:
        raise ValueError('native evaluation wall cap at most600sec')
    native_calls = fresh_calls = requested_tools = 0
    phase = 'setup'

    def guard(extra=0, check_wall=True):
        if check_wall and time.monotonic() - started > wall_cap:
            raise RuntimeError('native evaluation wall cap exceeded')
        if (storage.allocated_bytes(matrix, unit) + sum(storage.allocated_bytes(p, unit) for p in extras)
                + extra + TERMINAL_RESERVE > budget['matrix_cap_bytes']
                or storage.allocated_bytes(root, unit) + extra + TERMINAL_RESERVE > budget['project_cap_bytes']
                or shutil.disk_usage(root).free - extra - TERMINAL_RESERVE < budget['retained_free_bytes']):
            raise RuntimeError('native evaluation matrix/project/free cap exceeded')
        if out.exists() and storage.allocated_bytes(out, unit) + extra > budget['raw_cap_bytes_per_pair']:
            raise RuntimeError('native evaluation raw cap exceeded')

    def write(name, record, append=False, check_wall=True):
        data = (json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
        guard(len(data) + unit, check_wall)
        with (out / name).open('ab' if append else 'xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())

    guard(16 * unit); out.mkdir(parents=True)
    identity = {'schema': 'cap256.calculator-evaluation.v1', 'job': os.environ['JOB'],
        'config_sha256': args.config_sha256, 'endpoints_sha256': args.endpoints_sha256,
        'protocol_sha256': cfg['evaluation_protocol']['sha256'],
        'runner_sha256': cfg['evaluation_runner']['sha256'],
        'runtime_sha256': cfg['runtime_module']['sha256'],
        'calculator_tools_sha256': cfg['calculator_tools']['sha256'],
        'architecture_contract_sha256': cfg['architecture_contract']['sha256']}
    write('CLAIM.json', {**identity, 'native_call_limit': 52, 'teacherforced_examples': 0,
        'optimizer_updates': 0, 'fresh_frame_file_accessed': False})
    try:
        sys.path[:0] = [str(root), str(root / 'scripts')]
        os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TRANSFORMERS_OFFLINE'] = '1'
        import torch
        from sol_translator_grounding_v6 import HumanInputProjection
        from sol_translator_english_ordered_v10 import load_ordered_english
        from sol_spatial_poc_ordered_v2 import load_ordered_bundle
        import sol_spatial_poc_ordered_train_api_v2
        from scripts.sol_stop_ordered_api2 import ordered_attention_math
        from sol_translator_decoder import FinalLatent
        from sol_translator_runtime import component_fingerprint
        runtime = importlib.import_module('scripts.cap256_launch.calculator_runtime')
        tools = importlib.import_module('scripts.cap256_launch.calculator_tools')
        if (Path(runtime.__file__).resolve() != pins['runtime_module']
                or Path(tools.__file__).resolve() != pins['calculator_tools']):
            raise ValueError('calculator package imports differ from pinned paths')
        helpers.verify_runtime_imports(root, seal, [cfg[name] for name in (
            'runner', 'evaluation_runner', 'resume_helpers', 'runtime_module', 'calculator_tools',
            'source_runner', 'storage_snapshot')])
        torch.set_num_threads(2)
        if not torch.cuda.is_available() or torch.cuda.get_device_properties(0).total_memory > 16 * 1024 ** 3:
            raise RuntimeError('authorized16GiB CUDA device required')
        torch.cuda.reset_peak_memory_stats()

        def gpu_guard():
            peak = torch.cuda.max_memory_reserved()
            if peak > budget['cuda_peak_reserved_cap_bytes']:
                raise RuntimeError('native evaluation GPU peak cap exceeded')
            return {'peak_reserved_bytes': peak, 'reserved_bytes': torch.cuda.memory_reserved(),
                'allocated_bytes': torch.cuda.memory_allocated()}

        binding0 = old['warmstart']['tuples']['0']
        dec, tokenizer, _ = load_ordered_english(binding0['lm_path'], binding0['lm_provenance'], binding0['adapter_path'], 'cuda')
        lm = dec.lm; lm.eval().requires_grad_(False)
        lm_before = component_fingerprint(lm); gpu_guard(); guard()

        def observe_stage(frames, stage):
            nonlocal native_calls, fresh_calls, requested_tools, phase
            phase = stage
            raw_name = stage + '-OBSERVATIONS.jsonl'
            with torch.no_grad():
                for endpoint in endpoints:
                    seed = endpoint['seed']; binding = old['warmstart']['tuples'][str(seed)]
                    if (binding['lm_path'], binding['lm_provenance']) != (binding0['lm_path'], binding0['lm_provenance']):
                        raise ValueError('matched endpoints must share pinned frozen LM')
                    saved = torch.load(pin(root, endpoint['checkpoint']), map_location='cpu', weights_only=True)
                    closed = closed_by_seed[seed]
                    core, _ = load_ordered_bundle(binding['parent_path'], 'cuda')
                    rr = torch.load(binding['reader_path'], map_location='cpu', weights_only=True)
                    reader = HumanInputProjection(rr['lm_width']).to('cuda'); del rr
                    tool = runtime.CalculatorPath(dim=256).to('cuda')
                    modules = (('core', core), ('reader', reader), ('prefix', dec.adapter), ('tool', tool))
                    if (saved.get('update') != 11264 or saved.get('additional_updates') != 1024
                            or saved.get('constructor') != core.constructor()
                            or saved.get('tool_constructor') != tool.constructor()
                            or saved.get('config_sha256') != args.config_sha256
                            or saved.get('runtime_sha256') != cfg['runtime_module']['sha256']
                            or saved.get('model_state_fingerprints') != closed['final_fingerprints']):
                        raise ValueError('trained calculator checkpoint metadata differs')
                    for name, module in modules:
                        module.load_state_dict(saved[name], strict=True); module.eval().requires_grad_(False)
                        if component_fingerprint(module) != closed['final_fingerprints'][name]:
                            raise ValueError('loaded endpoint fingerprint differs: ' + name)
                    del saved; gpu_guard(); guard()
                    for frame in frames:
                        guard(); gpu_guard()
                        limit = 20 if stage == 'TRAIN' else 52
                        if native_calls >= limit:
                            raise RuntimeError('native call cap reached before generation')
                        # Only source question/literals/masks enter the runtime.
                        ids = tokenizer.encode(frame['question'], add_special_tokens=False)
                        registry = tools.build_registry(frame['question'], tokenizer)
                        if (frame['input_ids'] != [ids + [dec.eos_id]] or dec.eos_id in ids
                                or registry != frame['numeric_registry']):
                            raise ValueError('actual question tokenizer/offset qualification differs')
                        input_ids = torch.tensor(frame['input_ids'], device='cuda')
                        mask = torch.tensor(frame['input_mask'], device='cuda', dtype=torch.bool)
                        query = reader(lm.get_input_embeddings()(input_ids), mask)
                        with ordered_attention_math():
                            output = tool.forward(core, reader, lm, tokenizer, query, registry, mask)
                        if output['total_advances'] != 4 or len(output['trace']) != 4:
                            raise ValueError('exactly four native tool-loop advances required')
                        h = output['h']
                        observed = sealed.observe_generation(dec, FinalLatent(h, torch.ones_like(h, dtype=torch.bool), mask, (1, h.shape[1])), 32)
                        native_calls += observed['native_generate_call_count']
                        if stage == 'FRESH': fresh_calls += observed['native_generate_call_count']
                        requested_tools += sum(trace['action'] != 'NONE' for trace in output['trace'])
                        write(raw_name, {**identity, 'call_index': native_calls, 'seed': seed,
                            'arm': 'calculator', 'phase': stage, 'id': frame['id'],
                            'checkpoint_sha256': endpoint['checkpoint']['sha256'],
                            'frame_sha256': frame['frame_sha256'], 'predicted_trace': output['trace'],
                            'total_advances': output['total_advances'], **observed}, True, False)
                        if observed['native_generate_call_count'] != 1:
                            raise ValueError('one native generate call required per row')
                        gpu_guard(); guard()
                    for name, module in modules:
                        if component_fingerprint(module) != closed['final_fingerprints'][name]:
                            raise ValueError('endpoint changed during native evaluation: ' + name)
                    pin(root, endpoint['checkpoint']); pin(root, endpoint['closed'])
                    del core, reader, tool, modules, output, h, query, input_ids, mask
                    torch.cuda.empty_cache(); gpu_guard(); guard()
            raw_hash = sha(out / raw_name)
            records = [json.loads(line) for line in (out / raw_name).read_bytes().splitlines()]
            return records, raw_hash

        train_records, train_raw_hash = observe_stage(train_frames, 'TRAIN')
        if native_calls != 20:
            raise ValueError('exact20TRAIN native calls required before scoring')
        phase = 'TRAIN-scoring'
        qualify_targets(train_frames, tokenizer, dec.eos_id)
        train_results, answers = score_saved(train_records, train_frames, train_metadata,
            'TRAIN', sealed.score_observed_generation, dec.eos_id)
        for answer in answers: write('TRAIN-ANSWERS.jsonl', answer, True)
        gate = fit_gate_passed(train_results)
        if sha(out / 'TRAIN-OBSERVATIONS.jsonl') != train_raw_hash:
            raise ValueError('TRAIN raw observations changed after oracle scoring')
        write('FIT-GATE.json', {**identity, 'fit_gate_passed': gate, 'results': train_results,
            'train_observations_sha256': train_raw_hash, 'fresh_frame_file_accessed': False})

        def load_fresh():
            # This is the ONLY path to fresh frame hashing or content access.
            frames = read(pin(root, cfg['fresh_frames']))['rows']
            validate_frames(frames, 16)
            if {frame['id'] for frame in frames} & {frame['id'] for frame in train_frames}:
                raise ValueError('fresh IDs overlap TRAIN')
            return frames

        def qualify_fresh(frames):
            records, raw_hash = observe_stage(frames, 'FRESH')
            qualify_targets(frames, tokenizer, dec.eos_id)
            results, answers = score_saved(records, frames, {f['id']: f for f in frames},
                'FRESH', sealed.score_observed_generation, dec.eos_id, call_start=20)
            for answer in answers: write('FRESH-ANSWERS.jsonl', answer, True)
            if sha(out / 'FRESH-OBSERVATIONS.jsonl') != raw_hash:
                raise ValueError('fresh raw observations changed after oracle scoring')
            return {'results': results, 'observations_sha256': raw_hash}

        fresh_result = gated_fresh(train_results, load_fresh, qualify_fresh)
        if native_calls != (52 if gate else 20) or fresh_calls != (32 if gate else 0):
            raise ValueError('native TRAIN/fresh branch accounting differs')
        if component_fingerprint(lm) != lm_before:
            raise ValueError('frozen LM changed during evaluation')
        for endpoint in endpoints:
            pin(root, endpoint['checkpoint']); pin(root, endpoint['closed'])
        if sha(config_path) != args.config_sha256 or sha(endpoints_path) != args.endpoints_sha256:
            raise ValueError('immutable evaluator input changed')
        phase = 'closure'; final_gpu = gpu_guard(); guard()
        hashes = {path.name: sha(path) for path in out.iterdir() if path.is_file()}
        write('CLOSED.json', {**identity, 'closed': True, 'fit_gate_passed': gate,
            'native_calls': native_calls, 'fresh_native_calls': fresh_calls,
            'teacherforced_examples': 0, 'optimizer_updates': 0, 'requested_tool_calls': requested_tools,
            'TRAIN_results': train_results, 'fresh_results': fresh_result,
            'fresh_status': 'CONSUMED_ONCE' if gate else 'UNUSED',
            'fresh_frame_file_accessed': gate, 'raw_frozen_before_scoring': True,
            'endpoint_weights_and_checkpoint_bytes_unchanged': True, 'LM_unchanged': True,
            'file_sha256': hashes, 'endpoints': endpoints, 'final_gpu': final_gpu,
            'wall_seconds': time.monotonic() - started, 'driver_terminal_reserve_bytes': TERMINAL_RESERVE})
        gpu_guard(); guard()
        print(json.dumps({'status': 'CLOSED-CALCULATOR-NATIVE', 'fit_gate_passed': gate,
            'native_calls': native_calls, 'fresh_native_calls': fresh_calls,
            'optimizer_updates': 0, 'teacherforced_examples': 0}), flush=True)
    except Exception as error:
        try:
            write('FAILED.json', {**identity, 'closed': False, 'phase': phase,
                'native_calls': native_calls, 'fresh_native_calls': fresh_calls,
                'teacherforced_examples': 0, 'optimizer_updates': 0,
                'error_type': type(error).__name__, 'error': str(error)}, check_wall=False)
        except Exception:
            pass
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True); parser.add_argument('--config', required=True)
    parser.add_argument('--config-sha256', required=True); parser.add_argument('--endpoints', required=True)
    parser.add_argument('--endpoints-sha256', required=True)
    run(parser.parse_args())
