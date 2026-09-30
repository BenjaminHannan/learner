#!/usr/bin/env python3
"""CPU weights_only audit of saved numeric fit state; no model or optimizer."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path

BASE = Path(__file__).parent
READER = BASE / 'recount_saved_numeric16_v2.py'
if hashlib.sha256(READER.read_bytes()).hexdigest() != '4dff4349b458d8b462ff712e6789c9ce68fc58f54341abc6726acded1e7eddca':
    raise ValueError('unpinned saved reader refused before import')
spec = importlib.util.spec_from_file_location('numeric_saved_reader', READER)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


APPROVED_ROOTS = ('/workspace/learner', 'c:/users/benja/sol-cloud-numeric-capability-v1')


def configure_root(repo_root):
    """Adapt only the pinned saved-reader root to the explicit original PC repo."""
    repo_root = Path(repo_root)
    normalized = repo_root.as_posix().rstrip('/').casefold()
    if not repo_root.is_absolute() or normalized not in APPROVED_ROOTS:
        raise ValueError('only the approved cloud or original PC root is allowed')
    # The pinned function's default was bound at definition time. Rebind the
    # one scope default explicitly; its rejection and scoring code is unchanged.
    C.checked(repo_root, repo_root)
    C.ROOT = repo_root
    C.OWN = repo_root / 'artifacts/sol-cloud-verifier-20260930'
    C.checked.__defaults__ = (repo_root,)
    return repo_root


def source_pins():
    for relative, expected in C.PINS.items():
        path = C.checked(C.ROOT / relative)
        if C.sha(path.read_bytes()) != expected:
            raise ValueError('pinned audit input differs: ' + relative)


def audit(checkpoint_path, run, seed, arm):
    import torch
    source_pins()
    checkpoint_path, run = C.checked(checkpoint_path), C.checked(run)
    expected_run = C.ROOT / 'artifacts/sol-cloud-numeric-fit-20260930/run-v1' / ('seed%d' % seed) / arm
    if run != C.checked(expected_run) or checkpoint_path != C.checked(expected_run / 'final-resume.pt'):
        raise ValueError('only the exact saved numeric arm checkpoint and run are allowed')
    initial = C.decode(C.checked(run / 'INITIAL-STATE.json').read_bytes())
    closed = C.decode(C.checked(run / 'CLOSED.json').read_bytes())
    assert closed['closed'] is True and closed['optimizer_updates'] == 800
    assert seed in (0, 1) and arm in ('loop', 'plain')
    for record in (initial, closed):
        assert record['seed'] == seed and record['arm'] == arm
        assert record['plan_sha256'] == C.PINS['artifacts/sol-cloud-numeric-fit-20260930/PLAN-v3.json']
        assert record['seal_sha256'] == C.PINS['artifacts/sol-cloud-numeric-fit-20260930/SEAL-v4.json']
        assert record['driver_sha256'] == C.PINS['scripts/sol_cloud_numeric_fit_v2.py']
        assert record['actual_user_day'] is False and record['sleep_enabled'] is False and record['activation'] is False
    allowance = (108 if arm == 'loop' else 416) * 1024 * 1024
    assert checkpoint_path.stat().st_size <= allowance
    stream_hash = hashlib.sha256()
    with checkpoint_path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            stream_hash.update(chunk)
    checkpoint_sha = stream_hash.hexdigest()
    assert checkpoint_sha == closed['checkpoint']['sha256']
    # No custom globals, pickle fallback, model construction, CUDA or RNG restore.
    raw = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
    checks = []
    def check(condition, reason):
        if not condition:
            raise ValueError(reason)
        checks.append(reason)
    def tensor_hash(tensor):
        check(type(tensor) is torch.Tensor and tensor.device.type == 'cpu', 'CPU saved tensor')
        value = tensor.detach().contiguous()
        return {'shape': list(value.shape), 'dtype': str(value.dtype), 'sha256': hashlib.sha256(value.numpy().tobytes()).hexdigest()}
    def fingerprint(state):
        out = hashlib.sha256()
        for name, tensor in sorted(state.items()):
            out.update(f'{name}:{tensor.dtype}:{tuple(tensor.shape)}'.encode())
            out.update(tensor.detach().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
        return out.hexdigest()
    for key in ('seed', 'arm', 'plan_sha256', 'seal_sha256', 'driver_sha256', 'job', 'binding', 'release_sha256', 'inventory_sha256'):
        check(raw[key] == closed[key], 'checkpoint/closed identity ' + key)
    check(raw['update'] == raw['raw_watermark_update'] == 800, 'saved global800 watermark')
    for key, filename in [('TRAIN_raw_sha256', 'TRAIN-RAW.jsonl'), ('DIAGNOSTIC_raw_sha256', 'DIAGNOSTIC-RAW.jsonl'), ('input_frames_sha256', 'INPUT-FRAMES.json')]:
        with C.checked(run / filename).open('rb') as stream:
            out = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                out.update(chunk)
        check(raw[key] == closed[key] == out.hexdigest(), 'saved byte binding ' + filename)
    plan = C.decode(C.checked(C.ROOT / 'artifacts/sol-cloud-numeric-fit-20260930/PLAN-v3.json').read_bytes())
    check(raw['visits'] == closed['visits'] == {rid: 50 for rid in plan['selected_ids']}, 'saved16 exact50 visits')
    check(raw['schedule_sha256'] == plan['schedules'][str(seed)]['sha256'], 'saved presealed schedule')
    final_fp = {}
    named = {}
    tensor_inventory = {}
    for group in ('core', 'reader', 'prefix'):
        check(type(raw[group]) is dict or type(raw[group]).__name__ == 'OrderedDict', 'saved component dictionary ' + group)
        count = 0
        for name, tensor in raw[group].items():
            check(type(name) is str and type(tensor) is torch.Tensor, 'typed model state ' + group)
            check(tensor.device.type == 'cpu' and tensor.dtype == torch.float32 and bool(torch.isfinite(tensor).all()), 'finite FP32 CPU model tensor ' + group + '.' + name)
            count += tensor.numel()
            named[group + '.' + name] = tensor
        final_fp[group] = fingerprint(raw[group])
        tensor_inventory[group] = {'state_tensors': len(raw[group]), 'stored_elements_including_buffers': count, 'fingerprint': final_fp[group]}
        check(final_fp[group] == raw['model_state_fingerprints'][group] == closed['final_fingerprints'][group], 'actual component fingerprint ' + group)
    buffers = initial['frozen_core']['buffers']
    for name, expected in buffers.items():
        check(tensor_hash(raw['core'][name]) == expected, 'unchanged actual core buffer ' + name)
    halt = {name[len('halt.'):]: value for name, value in raw['core'].items() if name.startswith('halt.')}
    check(bool(halt) and fingerprint(halt) == initial['frozen_core']['halt'], 'actual unchanged fixed halt')
    names = raw['optimizer_parameter_names']
    check(type(names) is list and len(names) == len(set(names)) and set(names) == set(initial['initial_parameter_hashes']), 'eligible parameter names match initial descriptors')
    excluded = {'core.' + name for name in buffers} | {'core.halt.' + name for name in halt}
    check(set(named) == set(names) | excluded and not set(names).intersection(excluded), 'complete state coverage with only fixed halt/buffers excluded')
    parameter_bytes = sum(named[name].numel() * named[name].element_size() for name in names)
    check(parameter_bytes == initial['parameter_bytes'], 'actual eligible parameter bytes')
    check(initial['checkpoint_bound_bytes'] == 3 * parameter_bytes + 3 * 1024 * 1024, 'declared3P allowance agrees with actual shapes')
    optimizer = raw['optimizer']; groups = optimizer['param_groups']; states = optimizer['state']
    check(len(groups) == 1 and groups[0]['params'] == list(range(len(names))), 'one ordered Adam parameter group')
    group = groups[0]
    check(group['lr'] == .001 and group['weight_decay'] == 0 and tuple(group['betas']) == (.9, .999) and group['eps'] == 1e-8, 'actual saved AdamW hyperparameters')
    check(all(type(index) is int and 0 <= index < len(names) for index in states), 'exact Adam index range')
    rows = raw['optimizer_audit']
    check([row['name'] for row in rows] == names, 'optimizer audit exact saved order')
    changed = Counter(); participation = Counter(); step_counts = Counter(); absent = []
    for index, (name, row) in enumerate(zip(names, rows)):
        tensor = named[name]; actual = tensor_hash(tensor); prior = initial['initial_parameter_hashes'][name]
        check(actual['shape'] == prior['shape'] and actual['dtype'] == prior['dtype'], 'unchanged parameter extent ' + name)
        check(actual == row['final_parameter'], 'actual final parameter hash ' + name)
        is_changed = actual != prior
        check(type(row['changed']) is bool and row['changed'] == is_changed, 'actual change flag ' + name)
        count = raw['participation'].get(name, 0)
        check(type(count) is int and 0 <= count <= 800 and row['participation'] == count, 'participation range ' + name)
        nonzero = row['nonzero_gradient_updates']
        check(type(nonzero) is int and 0 <= nonzero <= count, 'nonzero gradient counter range ' + name)
        state = states.get(index)
        if state is None:
            check(count == row['Adam_step'] == 0 and row['moments'] == {} and not is_changed, 'no state means unchanged nonparticipating parameter ' + name)
            absent.append(name)
        else:
            check(set(state) == {'step', 'exp_avg', 'exp_avg_sq'}, 'exact Adam state keys ' + name)
            step = state['step']
            check(type(step) is torch.Tensor and step.device.type == 'cpu' and step.numel() == 1, 'CPU scalar Adam step ' + name)
            value = float(step.item())
            check(math.isfinite(value) and value.is_integer() and 0 < value <= 800 and int(value) == count == row['Adam_step'], 'actual Adam step equals sparse participation ' + name)
            step_counts[int(value)] += 1
            for key in ('exp_avg', 'exp_avg_sq'):
                moment = state[key]
                check(type(moment) is torch.Tensor and moment.device.type == 'cpu' and moment.dtype == tensor.dtype and moment.shape == tensor.shape and bool(torch.isfinite(moment).all()), 'actual finite matching Adam moment ' + name + '/' + key)
                check(tensor_hash(moment) == row['moments'][key], 'actual Adam moment fingerprint ' + name + '/' + key)
            check(bool((state['exp_avg_sq'] >= 0).all()), 'nonnegative actual Adam second moment ' + name)
            if nonzero:
                check(bool(torch.count_nonzero(state['exp_avg_sq'])), 'nonzero gradient has durable nonzero second moment ' + name)
            participation[name.split('.')[0]] += 1
        changed[name.split('.')[0]] += int(is_changed)
    return {'schema': 'sol.cloud.independent.numeric16.actual-checkpoint-recount.v2',
            'completed_utc': datetime.now(timezone.utc).isoformat(), 'seed': seed, 'arm': arm,
            'approved_original_repo_root': C.ROOT.as_posix(), 'source_pins_verified_before_load': True,
            'checkpoint': {'path': str(checkpoint_path.relative_to(C.ROOT)), 'sha256': checkpoint_sha, 'bytes': checkpoint_path.stat().st_size},
            'safe_load': {'map_location': 'cpu', 'weights_only': True, 'unsafe_fallback': False, 'torch_version': torch.__version__},
            'actual_tensor_checks_passed': len(checks), 'component_inventory': tensor_inventory,
            'eligible_parameters': len(names), 'eligible_parameter_bytes': parameter_bytes,
            'actual_Adam_states': len(states), 'actual_Adam_step_histogram': dict(step_counts),
            'changed_parameters_per_component': dict(changed), 'participating_parameters_per_component': dict(participation),
            'unchanged_absent_Adam_parameters': absent, 'global_update': 800,
            'fixed_halt_and_buffers_unchanged': True, 'same_saved_raw_and_frame_SHA': True,
            'LM_tensor_proof': 'LM weights are not in this checkpoint; recorded frozen-LM fingerprint equality remains source/runtime evidence only.',
            'limits': ['No model construction/forward/inference/tokenizer/optimizer/RNG restore or CUDA.',
                       'Actual saved tensor/Adam mechanics only, not capability/generalization/advantage/stopping/activation qualification.',
                       'Sparse parameter Adam steps equal participation and need not all be800.'],
            'model_calls': 0, 'tokenizer_calls': 0, 'optimizer_calls': 0, 'GPU_calls': 0, 'queue_operations': 0,
            'report_training_eligible': False, 'checker_sha256': C.sha(Path(__file__).read_bytes())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--seed', type=int, choices=(0, 1), required=True)
    parser.add_argument('--arm', choices=('loop', 'plain'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    configure_root(args.repo_root)
    result = audit(args.checkpoint, args.run, args.seed, args.arm)
    output = C.checked(args.output, C.OWN)
    raw = (json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with output.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'output': str(output), 'sha256': C.sha(raw), 'checks': result['actual_tensor_checks_passed']}))
