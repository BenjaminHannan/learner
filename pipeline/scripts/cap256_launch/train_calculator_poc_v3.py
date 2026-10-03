"""Bounded calculator prototype training, with predicted calls on all four loops.

No dispatch permission by default. The pinned runtime owns four call-before-
advance transitions and receives question-derived literals only. Checked task
labels are used here for CE targets, never passed into the runtime. Original
model/Adam/RNG state is retained; only tool parameters get a fresh Adam group.
Native TRAIN qualification and conditional fresh evaluation are separate.
"""
import argparse
from collections import Counter
import importlib.util
import importlib
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import sys
import time


UPDATES = 1024
START_UPDATE = 10240
CASES = ('carry', 'no_carry', 'borrow', 'no_borrow')
CASE_OPERATION = {'carry': 'add', 'no_carry': 'add', 'borrow': 'sub', 'no_borrow': 'sub'}
RECIPE = {
    'batch': 1, 'rounds': 4, 'calls_per_loop_max': 1, 'calls_total_max': 4,
    'call_order': 'predict-call-insert-own-pair-then-one-advance',
    'policy_features': 'original-query-h-plus-e-and-eligible-span-or-result-means',
    'literal_spans_max': 8, 'prior_results_max': 3, 'reserved_tool_pairs': 4,
    'actions': ['NONE', 'ADD', 'SUB'], 'statuses': ['PENDING', 'NONE', 'OK', 'ERROR'],
    'action_bias': True, 'pointer_bias': False,
    'predicted_calls_only': True, 'halt_frozen': True, 'LM_frozen': True,
    'full_FP32': True, 'optimizer_reset': False,
    'objective': 'final-numeric-CE-plus-mean4-action-CE-plus-eligible-loop-mean2-pointer-CE',
    'loss_weights': {'final_CE': 1, 'action_CE': 1, 'pointer_CE': 1},
    'label_policy': 'checked-task-call-until-correct-predicted-task-call-then-NONE',
    'source_update': START_UPDATE, 'additional_updates': UPDATES,
    'case_exposure': {case: 256 for case in CASES},
    'head_initialization': 'isolated-fork-rng-seed-equals-matched-seed',
    'old_Adam_group_preserved': True, 'new_tool_group_fresh': True,
    'optimizer': {'name': 'AdamW', 'lr': 0.001, 'weight_decay': 0,
                  'betas': [0.9, 0.999], 'eps': 1e-8, 'clip_norm': 1},
    'checkpoint_updates': [UPDATES], 'midpoint_checkpoint': False,
}


def bootstrap_helpers(root, cfg):
    """Only the small already CPU-tested resume utilities; no old fit dispatch."""
    pin = cfg['resume_helpers']
    if pin.get('path') != 'scripts/cap256_launch/train_primitive_curriculum_v2.py':
        raise ValueError('only the exact known CPU resume-helper module is permitted')
    path = (root / pin['path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError('resume helper outside root')
    import hashlib
    if hashlib.sha256(path.read_bytes()).hexdigest() != pin['sha256']:
        raise ValueError('resume helper hash differs')
    spec = importlib.util.spec_from_file_location('_calculator_resume_utilities', path)
    helpers = importlib.util.module_from_spec(spec); spec.loader.exec_module(helpers)
    helpers.pinned(root, pin)
    return helpers


def selected_by_id(rows):
    if not isinstance(rows, list) or len(rows) != 10:
        raise ValueError('exact frozen10 independently checked TRAIN rows required')
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('checked TRAIN row must be a dictionary')
        operation = 'sub' if row.get('operation') == 'subtract' else row.get('operation')
        if (not isinstance(row.get('id'), str) or not row['id'] or row['id'] in result
                or row.get('case') not in CASES or operation != CASE_OPERATION[row['case']]
                or row.get('split_role') != 'TRAIN' or row.get('independently_verified') is not True
                or not isinstance(row.get('operands'), list) or len(row['operands']) != 2
                or any(type(n) is not int or not 10 <= n <= 99 for n in row['operands'])
                or row['operands'][0] == row['operands'][1]
                or not isinstance(row.get('question'), str) or not row['question']
                or row.get('question_sha256') != hashlib.sha256(row['question'].encode()).hexdigest()
                or not isinstance(row.get('source_group'), str) or not row['source_group']):
            raise ValueError('checked direct-arithmetic TRAIN operation/ordered operands required')
        left, right = row['operands']
        target = left + right if operation == 'add' else left - right
        case = ('carry' if left % 10 + right % 10 >= 10 else 'no_carry') if operation == 'add' else (
            'borrow' if left % 10 < right % 10 else 'no_borrow')
        if (not 10 <= target <= 99 or row.get('canonical_numeric_target') != str(target)
                or row['case'] != case):
            raise ValueError('checked arithmetic target/carry-borrow case differs')
        result[row['id']] = row
    if {row['case'] for row in rows} != set(CASES):
        raise ValueError('all four frozen arithmetic cases required')
    return result


def exposure_counts(rows):
    byid = selected_by_id(rows); counts = Counter()
    for case in CASES:
        ids = sorted(i for i, row in byid.items() if row['case'] == case)
        whole, remainder = divmod(256, len(ids))
        counts.update({identity: whole + (n < remainder) for n, identity in enumerate(ids)})
    return counts


def make_schedule(rows, seed):
    if seed not in (0, 1):
        raise ValueError('two fixed matched seeds only')
    counts = exposure_counts(rows)
    schedule = [identity for identity in sorted(counts) for _ in range(counts[identity])]
    random.Random(seed).shuffle(schedule)
    return schedule


def validate_schedule(schedule, rows):
    if (not isinstance(schedule, list) or len(schedule) != UPDATES
            or Counter(schedule) != exposure_counts(rows)):
        raise ValueError('1024 fixed TRAIN updates,256 per case required')


def readiness_issues(cfg):
    issues = []
    if cfg.get('dispatch_allowed') is not True:
        issues.append('dispatch_allowed is not true; preparation only')
    for name in ('architecture_contract_frozen', 'corpus_frozen', 'fresh_evaluation_frozen',
                 'numeric_registry_tokenizer_qualified', 'source_state_verified',
                 'throughput_budget_verified', 'live_driver_verified'):
        if cfg.get('readiness', {}).get(name) is not True:
            issues.append(name + ' is not verified')
    return issues


def validate_config(cfg):
    if (cfg.get('schema') != 'cap256.calculator-poc.v1' or cfg.get('arm') != 'calculator'
            or cfg.get('seeds') != [0, 1] or cfg.get('additional_updates') != UPDATES
            or cfg.get('recipe') != RECIPE or cfg.get('resume_sources')
            or cfg.get('historical_controls_required') is not False):
        raise ValueError('frozen new calculator prototype required; primitive fit is parked')
    selected_by_id(cfg.get('selected_rows'))
    if (len(cfg.get('original_ids', [])) != 256 or len(set(cfg['original_ids'])) != 256
            or sorted(entry.get('seed') for entry in cfg.get('sources', [])) != [0, 1]):
        raise ValueError('two original-loop40 update10240 sources required')
    budget = cfg.get('budget', {})
    ceilings = {'optimizer_seconds': 300, 'worker_seconds': 360,
        'total_job_seconds': 900, 'matrix_cap_bytes': 1024 ** 3,
        'pair_cap_bytes': 512 * 1024 ** 2, 'checkpoint_cap_bytes': 128 * 1024 ** 2,
        'project_cap_bytes': 100_000_000_000, 'cuda_peak_reserved_cap_bytes': 16 * 1024 ** 3}
    if any(type(budget.get(name)) not in (int, float) or not 0 < budget[name] <= maximum
           for name, maximum in ceilings.items()):
        raise ValueError('explicit calculator900sec/1GiB recovery caps required')
    if (type(budget.get('retained_free_bytes')) is not int or budget['retained_free_bytes'] < 2 * 1024 ** 3
            or type(budget.get('raw_cap_bytes_per_pair')) is not int or budget['raw_cap_bytes_per_pair'] <= 0
            or budget.get('spend_usd') != 0 or budget.get('historical_recovery_budget_reused') is not False
            or budget['optimizer_seconds'] >= budget['worker_seconds']):
        raise ValueError('free reserve,zero spend,unused recovery budget and wall headroom required')
    if not isinstance(cfg.get('output_accounting_extra_paths'), list):
        raise ValueError('complete output/receipt accounting paths required')


# Replay changes operational transport/resource pins only. Scientific pins stay exact.
REPLAY_ENGINEERING_KEYS = frozenset(('runner', 'continuation_runner', 'evaluation_runner',
    'budget', 'readiness', 'dispatch_allowed', 'exclusive_lock_verified', 'input_namespace',
    'output_namespace', 'output_accounting_extra_paths', 'replay_reference'))
REPLAY_IDENTITY_EXCLUSIONS = frozenset(('job', 'config_sha256', 'runner_sha256'))


def stable_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def validate_replay_config(cfg, source_cfg):
    # Pin-path changes are not silently permitted: root reuses the exact science packet.
    left = {k: v for k, v in cfg.items() if k not in REPLAY_ENGINEERING_KEYS}
    right = {k: v for k, v in source_cfg.items() if k not in REPLAY_ENGINEERING_KEYS}
    if stable_json(left) != stable_json(right):
        changed = sorted(k for k in set(left) | set(right) if stable_json(left.get(k)) != stable_json(right.get(k)))
        raise ValueError('replay scientific config differs: ' + ','.join(changed))
    if (source_cfg.get('runner', {}).get('sha256') !=
            'a02789ccac93759b6bc09a5896129e8f28e8d5ac9a12ac50528f91d3a0813e78'):
        raise ValueError('only the preserved calculator V2 attempt can be replayed')


def replay_record_equal(observed, expected):
    actual = {k: v for k, v in observed.items() if k not in REPLAY_IDENTITY_EXCLUSIONS}
    prior = {k: v for k, v in expected.items() if k not in REPLAY_IDENTITY_EXCLUSIONS}
    if stable_json(actual) != stable_json(prior):
        changed = sorted(k for k in set(actual) | set(prior) if stable_json(actual.get(k)) != stable_json(prior.get(k)))
        raise ValueError('exact replay mismatch at additional_update%d: %s' %
            (observed['additional_update'], ','.join(changed)))


def load_replay(root, cfg, args, helpers, frames, schedule):
    reference = cfg.get('replay_reference')
    if reference is None:
        return None
    if type(reference) is not dict or set(reference) != {'seed', 'raw', 'failed', 'source_config'} or reference['seed'] != 0:
        raise ValueError('replay reference must bind exactly seed0 raw/failed/source_config')
    paths = {name: helpers.pinned(root, reference[name]) for name in ('raw', 'failed', 'source_config')}
    source_cfg = helpers.read(paths['source_config']); validate_replay_config(cfg, source_cfg)
    failed = helpers.read(paths['failed'])
    source = next(entry for entry in cfg['sources'] if entry['seed'] == 0)
    if (failed.get('seed') != 0 or failed.get('phase') != 'checkpoint'
            or failed.get('additional_optimizer_updates') != UPDATES
            or failed.get('optimizer_updates_exact') is not True
            or failed.get('error_type') != 'RuntimeError'
            or failed.get('error') != 'calculator output/pair/project/free cap exceeded'
            or failed.get('evidence_preserved') is not True
            or failed.get('no_midpoint_checkpoint') is not True
            or failed.get('last_completed_model_call_account') != {'TRAIN_optimizer_teacherforcing': UPDATES}
            or failed.get('config_sha256') != reference['source_config']['sha256']
            or failed.get('runner_sha256') != source_cfg['runner']['sha256']
            or failed.get('source_checkpoint_sha256') != source['checkpoint']['sha256']
            or failed.get('safe_parent_checkpoint') != source['checkpoint']
            or failed.get('runtime_sha256') != cfg['runtime_module']['sha256']
            or failed.get('schedule_sha256') != cfg['schedules']['sha256']):
        raise ValueError('preserved failed checkpoint-phase attempt differs')
    if paths['raw'].stat().st_size > cfg['budget']['raw_cap_bytes_per_pair']:
        raise ValueError('replay raw evidence exceeds explicit raw cap')
    raw = [json.loads(line) for line in paths['raw'].read_bytes().splitlines()]
    if len(raw) != UPDATES:
        raise ValueError('replay requires all1024 durable update records')
    frames_byid = {frame['id']: frame for frame in frames}
    seed0_schedule = helpers.read(helpers.pinned(root, cfg['schedules']))['schedules']['0']['calculator']
    counts = Counter({identity: 40 for identity in cfg['original_ids']}); requested_tools = 0
    for number, record in enumerate(raw, 1):
        identity = seed0_schedule[number - 1]; counts[identity] += 1
        if (type(record) is not dict or record.get('seed') != 0 or record.get('arm') != 'calculator'
                or record.get('additional_update') != number or record.get('update') != START_UPDATE + number
                or record.get('id') != identity or record.get('visit_for_row') != counts[identity]
                or record.get('frame_sha256') != frames_byid[identity]['frame_sha256']
                or record.get('config_sha256') != reference['source_config']['sha256']
                or record.get('runner_sha256') != source_cfg['runner']['sha256']
                or record.get('source_checkpoint_sha256') != source['checkpoint']['sha256']
                or record.get('runtime_sha256') != cfg['runtime_module']['sha256']
                or record.get('schedule_sha256') != cfg['schedules']['sha256']
                or record.get('total_advances') != 4 or len(record.get('predicted_trace', [])) != 4):
            raise ValueError('preserved replay raw sequence/provenance differs at%d' % number)
        stable_json(record)  # Reject nonfinite evidence before constructing a model.
        requested_tools += sum(trace.get('action') != 'NONE' for trace in record['predicted_trace'])
    if failed.get('last_completed_tool_call_account') != {'TRAIN_requested_tools': requested_tools}:
        raise ValueError('preserved raw and failed tool totals differ')
    return {'reference': reference, 'records': raw if args.seed == 0 else None,
        'prior_actual_optimizer_updates': UPDATES, 'prior_actual_model_calls': UPDATES,
        'prior_actual_requested_tools': requested_tools, 'prior_raw_bytes': paths['raw'].stat().st_size}


def checked_target_refs(row, registry):
    """Resolve independently checked task operands onto source literal refs.

    This produces loss labels only. Runtime inputs remain the mechanical
    registry derived from the question and exact tokenizer offsets.
    """
    literals = registry
    if not isinstance(literals, list):
        raise ValueError('mechanical literal registry must be a list')
    refs = []
    for operand in row['operands']:
        matches = [literal['id'] for literal in literals if literal.get('value') == operand
                   and literal.get('source') == 'literal' and literal.get('status') == 'OK']
        if len(matches) != 1:
            raise ValueError('checked operand does not uniquely bind an original literal span')
        refs.append(matches[0])
    if refs[0] == refs[1]:
        raise ValueError('two distinct original source refs required')
    return tuple(refs)


def action_for(row):
    return 'ADD' if row['operation'] == 'add' else 'SUB'


def task_call_matches(trace, desired_action, desired_refs):
    if trace.get('status') != 'OK' or trace.get('action') != desired_action:
        return False
    actual = tuple(trace.get('refs', ()))
    return (len(actual) == 2 and (set(actual) == set(desired_refs) if desired_action == 'ADD'
                                else actual == tuple(desired_refs)))


def supervision(row, registry, loops):
    if not isinstance(loops, list) or len(loops) != 4:
        raise ValueError('exactly four call-before-advance loop outputs required')
    desired_action = action_for(row); refs = checked_target_refs(row, registry)
    done = False; labels = []
    for output in loops:
        if done:
            labels.append({'action': 'NONE', 'pointers': None})
        else:
            candidates = [candidate['id'] for candidate in output['candidates']]
            if len(set(candidates)) != len(candidates) or any(ref not in candidates for ref in refs):
                raise ValueError('original operand refs missing or duplicated in eligible candidate registry')
            labels.append({'action': desired_action, 'pointers': [candidates.index(ref) for ref in refs]})
        if task_call_matches(output['trace'], desired_action, refs):
            done = True
    return labels


def weighted_call_loss(outputs, labels, torch_api, actions):
    """Unit-weight mean4 actionCE plus eligible-loop mean2 pointerCE."""
    action_losses, pointer_losses = [], []
    for output, label in zip(outputs, labels):
        action_target = torch_api.tensor([actions.index(label['action'])],
            device=output['action_logits'].device, dtype=torch_api.long)
        action_losses.append(torch_api.nn.functional.cross_entropy(output['action_logits'], action_target))
        if label['pointers'] is not None:
            parts = []
            for name, target in zip(('left_logits', 'right_logits'), label['pointers']):
                wanted = torch_api.tensor([target], device=output[name].device, dtype=torch_api.long)
                parts.append(torch_api.nn.functional.cross_entropy(output[name], wanted))
            pointer_losses.append(torch_api.stack(parts).mean())
    action_ce = torch_api.stack(action_losses).mean()
    pointer_ce = torch_api.stack(pointer_losses).mean() if pointer_losses else action_ce * 0
    return action_ce, pointer_ce


def preflight(root, cfg, args, helpers):
    validate_config(cfg)
    issues = readiness_issues(cfg)
    if issues:
        raise ValueError('; '.join(issues))
    keys = ('runner', 'runtime_module', 'calculator_tools', 'source_plan', 'source_seal', 'source_release',
            'source_runner', 'frames', 'schedules', 'storage_snapshot', 'checkpoint_io',
            'architecture_contract', 'corpus_audit', 'evaluation_protocol', 'throughput_receipt')
    pins = {name: helpers.pinned(root, cfg[name]) for name in keys}
    if pins['runner'].resolve() != Path(__file__).resolve():
        raise ValueError('running calculator worker is not its declared pin')
    seal = helpers.read(pins['source_seal'])
    for relative, expected in seal['files'].items():
        helpers.pinned(root, {'path': relative, 'sha256': expected})
    old = helpers.read(pins['source_plan'])
    entry = next(e for e in cfg['sources'] if e['seed'] == args.seed)
    paths = {name: helpers.pinned(root, entry[name]) for name in ('checkpoint', 'closed', 'original_frames')}
    original_frames = helpers.read(paths['original_frames'])['rows']
    if len(original_frames) != 256 or {f['id'] for f in original_frames} != set(cfg['original_ids']):
        raise ValueError('initialization-only original256 frame packet differs')
    selected = selected_by_id(cfg['selected_rows'])
    packet = helpers.read(pins['frames']); frames = packet['rows']
    if len(frames) != 10 or {f['id'] for f in frames} != set(selected):
        raise ValueError('focused TRAIN frames must be exactly frozen10')
    originals = {f['id']: f for f in original_frames}
    for frame in frames:
        identity = frame['id']; row = selected[identity]
        if (frame.get('question_sha256') != row['question_sha256']
                or frame.get('frame_sha256') != helpers.canonical({k: v for k, v in frame.items() if k != 'frame_sha256'})
                or frame.get('notebook_ids') != [[]] or frame.get('notebook_mask') != [[]]
                or frame.get('input_mask') != [[True] * len(frame['input_ids'][0])]
                or frame.get('label_mask') != [[True] * len(frame['labels'][0])]
                or frame.get('canonical_numeric_target') != row['canonical_numeric_target']
                or not 1 <= len(frame['input_ids'][0]) <= 48 or not 1 <= len(frame['labels'][0]) <= 32):
            raise ValueError('untruncated source-preserving question-only TRAIN frame required')
        registry = frame['numeric_registry']
        if (not isinstance(registry, list) or not 1 <= len(registry) <= 8
                or frame.get('question') != row['question']
                or hashlib.sha256(row['question'].encode()).hexdigest() != row['question_sha256']):
            raise ValueError('mechanical registry does not bind the exact TRAIN question')
        checked_target_refs(row, registry)
        if identity in originals and any(frame[key] != originals[identity][key] for key in helpers.FRAME_FIELDS):
            raise ValueError('existing original input/label tensors differ')
    schedules = helpers.read(pins['schedules'])['schedules']
    for seed in (0, 1):
        validate_schedule(schedules[str(seed)]['calculator'], cfg['selected_rows'])
    return pins, old, entry, paths, frames, schedules[str(args.seed)]['calculator'], selected


def run(args):
    root = Path(args.root).resolve(); config = Path(args.config).resolve()
    import hashlib
    if not config.is_relative_to(root) or hashlib.sha256(config.read_bytes()).hexdigest() != args.config_sha256:
        raise ValueError('immutable root-bound calculator config differs')
    cfg = json.loads(config.read_bytes()); validate_config(cfg)
    issues = readiness_issues(cfg)
    if args.check:
        if not issues:
            helpers = bootstrap_helpers(root, cfg)
            _, _, _, _, frames, schedule, _ = preflight(root, cfg, args, helpers)
            load_replay(root, cfg, args, helpers, frames, schedule)
        print(json.dumps({'status': 'PREPARED-BLOCKED' if issues else 'CPU-PREFLIGHT-PASSED',
            'issues': issues, 'model_calls': 0, 'optimizer_updates': 0,
            'live_execution_validated': False}), flush=True)
        return
    helpers = bootstrap_helpers(root, cfg)
    pins, old, entry, paths, frames, schedule, selected = preflight(root, cfg, args, helpers)
    replay = load_replay(root, cfg, args, helpers, frames, schedule)
    replay_matches = 0
    if (os.environ.get('TREE') != str(root) or not os.environ.get('JOB')
            or cfg.get('exclusive_lock_verified') is not True):
        raise ValueError('exclusive driver/root/job binding required')
    sealed = helpers.load_module(pins['source_runner'], '_calculator_sealed_resume')
    sealed.validate_plan(old)
    storage = helpers.load_module(pins['storage_snapshot'], '_calculator_storage')
    checkpoint_io = helpers.load_module(pins['checkpoint_io'], '_calculator_checkpoint_io')
    matrix = helpers.safe(root, cfg['output_namespace'])
    out = matrix / ('seed%d' % args.seed) / 'calculator'
    if out.exists():
        raise RuntimeError('calculator output exists; preserve it and prevent duplicates')
    extras = [helpers.safe(root, path) for path in cfg['output_accounting_extra_paths']]
    unit = storage.filesystem_allocation_unit(root); resource_rechecks = 0
    def account():
        vanished = []
        def reservation(path):
            size = storage.vanished_reservation(path); vanished.append(Path(path).resolve()); return size
        allocated = lambda path: storage.allocated_bytes(path, unit, reservation=reservation)
        return (allocated(matrix) + sum(allocated(path) for path in extras), allocated(out.parent),
                storage.raw_allocated_bytes(out.parent, unit), allocated(root), vanished)
    def guard(extra=0):
        nonlocal resource_rechecks
        def bad(snapshot):
            return (snapshot[0] + extra > cfg['budget']['matrix_cap_bytes']
                or snapshot[1] + extra > cfg['budget']['pair_cap_bytes']
                or snapshot[3] + extra > cfg['budget']['project_cap_bytes']
                or shutil.disk_usage(root).free - extra < cfg['budget']['retained_free_bytes'])
        snapshot = account()
        owned_temporary = out / 'final-resume.pt.tmp'
        if bad(snapshot) and snapshot[4] and all(p == owned_temporary.resolve() for p in snapshot[4]):
            # Recheck only the known owned atomic-save disappearance; no sleep,
            # permissions change or resource expansion, and no RNG consumption.
            resource_rechecks += 1; snapshot = account()
        if bad(snapshot):
            raise RuntimeError('calculator output/pair/project/free cap exceeded')
        return snapshot
    # Reserve both bounded final extents, both complete raw/log allowances and
    # one serializer peak before any model load/update. Existing staging and
    # preserved failed evidence are already included in project/account totals.
    whole_run_reservation = (2 * cfg['budget']['checkpoint_cap_bytes']
        + 2 * cfg['budget']['raw_cap_bytes_per_pair'] + 16 * 1024 ** 2 + 6 * 1024 ** 2)
    guard(whole_run_reservation + unit)
    guard(unit); out.mkdir(parents=True)
    identity = {'schema': 'cap256.calculator-poc.identity.v1', 'job': os.environ['JOB'],
        'seed': args.seed, 'arm': 'calculator', 'config_sha256': args.config_sha256,
        'runner_sha256': cfg['runner']['sha256'], 'runtime_sha256': cfg['runtime_module']['sha256'],
        'architecture_contract_sha256': cfg['architecture_contract']['sha256'],
        'source_checkpoint_sha256': entry['checkpoint']['sha256'], 'source_plan_sha256': cfg['source_plan']['sha256'],
        'source_seal_sha256': cfg['source_seal']['sha256'], 'schedule_sha256': cfg['schedules']['sha256'],
        'optimizer_reset': False, 'TRAIN_only': True, 'halt_frozen': True, 'LM_frozen': True,
        'predicted_calls_only': True, 'total_latent_advances': 4, 'sleep_enabled': False}
    def write(name, record, append=False):
        data = (json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
        snapshot = guard(len(data) + unit)
        if snapshot[2] + len(data) + unit > cfg['budget']['raw_cap_bytes_per_pair']:
            raise RuntimeError('calculator raw pair cap exceeded')
        with (out / name).open('ab' if append else 'xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
    launched = time.monotonic(); updates = 0; calls = Counter(); tool_calls = Counter(); phase = 'setup'
    write('LAUNCH.json', {**identity, 'source_update': START_UPDATE, 'target_update': START_UPDATE + UPDATES,
        'recipe': RECIPE, 'no_midpoint_checkpoint': True, 'initialization_only_original_frames': True,
        'native_TRAIN_gate_separate': True, 'fresh_evaluation_not_performed': True,
        'whole_run_storage_reserved_bytes': whole_run_reservation,
        'operational_replay': None if replay is None else {k: v for k, v in replay.items() if k != 'records'}})
    try:
        sys.path[:0] = [str(root), str(root / 'scripts')]
        os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TRANSFORMERS_OFFLINE'] = '1'
        import torch
        from sol_translator_grounding_v6 import HumanInputProjection, human_loss
        from sol_translator_english_ordered_v10 import load_ordered_english
        from sol_spatial_poc_ordered_v2 import load_ordered_bundle
        import sol_spatial_poc_ordered_train_api_v2  # provenance only; no fixed4 call
        from scripts.sol_stop_ordered_api2 import ordered_attention_math
        from sol_translator_runtime import component_fingerprint
        torch.set_num_threads(2)
        if not torch.cuda.is_available():
            raise RuntimeError('authorized CUDA unavailable')
        runtime = importlib.import_module('scripts.cap256_launch.calculator_runtime')
        tools = importlib.import_module('scripts.cap256_launch.calculator_tools')
        if (Path(runtime.__file__).resolve() != pins['runtime_module'].resolve()
                or Path(tools.__file__).resolve() != pins['calculator_tools'].resolve()):
            raise ValueError('calculator modules resolve outside their pinned paths')
        if runtime.ACTIONS != ('NONE', 'ADD', 'SUB') or runtime.STATUSES != ('PENDING', 'NONE', 'OK', 'ERROR'):
            raise ValueError('frozen calculator action/status alphabet differs')
        helpers.verify_runtime_imports(root, helpers.read(pins['source_seal']), [cfg[name]
            for name in ('runner', 'runtime_module', 'calculator_tools', 'resume_helpers', 'source_runner', 'storage_snapshot', 'checkpoint_io')])
        prior = torch.load(paths['checkpoint'], map_location='cpu', weights_only=True)
        closed = helpers.read(paths['closed'])
        helpers.validate_initial_metadata(prior, closed, entry, cfg['original_ids'])
        binding = old['warmstart']['tuples'][str(args.seed)]
        dec, tokenizer, _ = load_ordered_english(binding['lm_path'], binding['lm_provenance'], binding['adapter_path'], 'cuda')
        lm = dec.lm; lm.eval().requires_grad_(False)
        core, _ = load_ordered_bundle(binding['parent_path'], 'cuda')
        reader_raw = torch.load(binding['reader_path'], map_location='cpu', weights_only=True)
        reader = HumanInputProjection(reader_raw['lm_width']).to('cuda'); del reader_raw
        if prior['constructor'] != core.constructor():
            raise ValueError('source constructor differs')
        base_modules = (('core', core), ('reader', reader), ('prefix', dec.adapter))
        for name, module in base_modules:
            module.load_state_dict(prior[name], strict=True)
            if component_fingerprint(module) != closed['final_fingerprints'][name]:
                raise ValueError('source model fingerprint differs: ' + name)
            module.train().requires_grad_(True)
        core.halt.requires_grad_(False)
        with torch.random.fork_rng(devices=list(range(torch.cuda.device_count()))):
            torch.manual_seed(args.seed); torch.cuda.manual_seed_all(args.seed)
            tool = runtime.CalculatorPath(dim=256).to('cuda')
        tool.train().requires_grad_(True)
        if any(p.dtype != torch.float32 for module in (core, reader, dec.adapter, tool, lm) for p in module.parameters()):
            raise ValueError('calculator full-FP32 recipe required')
        old_named = [(group + '.' + name, p) for group, module in base_modules
            for name, p in module.named_parameters() if p.requires_grad]
        if [name for name, _ in old_named] != prior['optimizer_parameter_names']:
            raise ValueError('original Adam parameter order differs')
        old_params = [p for _, p in old_named]
        opt = torch.optim.AdamW(old_params, lr=0.001, weight_decay=0, betas=(0.9, 0.999), eps=1e-8)
        opt.load_state_dict(prior['optimizer'])
        if not helpers.state_equal(prior['optimizer'], opt.state_dict(), torch):
            raise ValueError('original Adam groups/moments/steps/flags differ')
        tool_named = [('tool.' + name, p) for name, p in tool.tool_named_parameters()]
        if not tool_named or len({id(p) for _, p in tool_named}) != len(tool_named):
            raise ValueError('unique tool-only parameter group required')
        extra_group = {key: value for key, value in opt.param_groups[0].items() if key != 'params'}
        extra_group['params'] = [p for _, p in tool_named]; opt.add_param_group(extra_group)
        if any(opt.state.get(p) for _, p in tool_named):
            raise ValueError('new tool moments must start empty')
        for group in opt.param_groups:
            if (group['lr'], group['weight_decay'], group['betas'], group['eps']) != (0.001, 0, (0.9, 0.999), 1e-8):
                raise ValueError('calculator Adam hyperparameters differ')
        named = old_named + tool_named; params = [p for _, p in named]
        participation = Counter(prior['participation'])
        nonzero = Counter({record['name']: record['nonzero_gradient_updates'] for record in prior['optimizer_audit']})
        for name, p in old_named:
            state = opt.state.get(p, {})
            if (int(state['step']) if state else 0) != participation[name]:
                raise ValueError('source Adam step differs from participation')
        rng = (prior['torch_rng'], prior['cuda_rng'], prior['python_rng']); visits = Counter(prior['visits'])
        del prior
        tokens = []
        for frame in frames:
            registry = frame['numeric_registry']; ids = tokenizer.encode(frame['question'], add_special_tokens=False)
            if (frame['input_ids'] != [ids + [dec.eos_id]] or frame['labels'][0][-1] != dec.eos_id
                    or frame['labels'] != [tokenizer.encode(frame['canonical_numeric_target'], add_special_tokens=False) + [dec.eos_id]]
                    or dec.eos_id in ids or dec.eos_id in frame['labels'][0][:-1]):
                raise ValueError('actual frozen tokenizer/EOS qualification differs')
            if registry != tools.build_registry(frame['question'], tokenizer):
                raise ValueError('exact question-offset numeric registry differs from pinned qualification')
            tokens.append((torch.tensor(frame['input_ids'], device='cuda'),
                torch.tensor(frame['input_mask'], device='cuda', dtype=torch.bool),
                torch.tensor(frame['labels'], device='cuda')))
        byid = {frame['id']: n for n, frame in enumerate(frames)}
        lm_before = component_fingerprint(lm); halt_before = component_fingerprint(core.halt)
        buffers_before = {name: value.detach().cpu().clone() for name, value in core.named_buffers()}
        torch.set_rng_state(rng[0]); torch.cuda.set_rng_state_all(rng[1]); random.setstate(rng[2])
        if (not torch.equal(torch.get_rng_state(), rng[0])
                or not helpers.state_equal(torch.cuda.get_rng_state_all(), rng[1], torch)
                or random.getstate() != rng[2]):
            raise ValueError('source model RNG restoration differs')
        del rng
        write('RESUME.json', {**identity, 'source_model_fingerprints_match': True,
            'source_Adam_groups_state_and_order_match': True, 'source_RNG_restored': True,
            'new_tool_group_empty_moments': True, 'head_seed': args.seed,
            'tool_constructor': tool.constructor(), 'optimizer_parameter_names': [name for name, _ in named],
            'optimizer_group_parameter_names': [[name for name, _ in old_named], [name for name, _ in tool_named]],
            'source_constructor': core.constructor(), 'source_update': START_UPDATE})
        optimizer_budget = sealed.OptimizerBudget(cfg['budget']['optimizer_seconds'])
        def timeout():
            if time.monotonic() - launched > cfg['budget']['worker_seconds']:
                raise RuntimeError('calculator per-seed worker planning cap exceeded')
            if torch.cuda.max_memory_reserved() > cfg['budget']['cuda_peak_reserved_cap_bytes']:
                raise RuntimeError('calculator GPU memory cap exceeded')
        def graph(index):
            ids, mask, _ = tokens[index]
            with torch.no_grad():
                emb = lm.get_input_embeddings()(ids)
            query = reader(emb, mask)
            with ordered_attention_math():
                output = tool.forward(core, reader, lm, tokenizer, query, frames[index]['numeric_registry'], mask)
            if output.get('total_advances') != 4 or len(output.get('loops', [])) != 4:
                raise ValueError('calculator runtime exceeded/fell short of four advances')
            h = output['h']
            prefix = dec.adapter.project_training(h, torch.ones_like(h, dtype=torch.bool), mask, (1, h.shape[1]))
            return output, prefix
        phase = 'training'
        for additional, identity_id in enumerate(schedule, 1):
            timeout(); optimizer_budget.begin(); index = byid[identity_id]
            opt.zero_grad(set_to_none=True); phase = 'model-forward'
            output, prefix = graph(index)
            per, pred = human_loss(lm, prefix, tokens[index][2], dec.bos_id, dec.eos_id, True, True)
            calls['TRAIN_optimizer_teacherforcing'] += 1
            labels = supervision(selected[identity_id], frames[index]['numeric_registry'], output['loops'])
            action_ce, pointer_ce = weighted_call_loss(output['loops'], labels, torch, runtime.ACTIONS)
            loss = per.mean() + action_ce + pointer_ce; phase = 'optimizer-step'
            def record_gradient():
                for name, p in named:
                    if p.grad is not None:
                        participation[name] += 1
                        if bool(torch.count_nonzero(p.grad)):
                            nonzero[name] += 1
            preclip = sealed.numeric_optimizer_step(loss, opt, params, torch, record_gradient)
            torch.cuda.synchronize(); optimizer_budget.end(); updates = additional; visits[identity_id] += 1
            tool_calls['TRAIN_requested_tools'] += sum(trace.get('action') != 'NONE' for trace in output['trace'])
            if any(p.grad is not None for p in lm.parameters()) or any(p.grad is not None for p in core.halt.parameters()):
                raise ValueError('frozen LM/halt received gradient')
            phase = 'durable-raw'
            record = {**identity, 'update': START_UPDATE + additional,
                'additional_update': additional, 'id': identity_id, 'visit_for_row': visits[identity_id],
                'frame_sha256': frames[index]['frame_sha256'], 'numeric_CE': float(per.mean().detach()),
                'action_CE': float(action_ce.detach()), 'pointer_CE': float(pointer_ce.detach()),
                'total_loss': float(loss.detach()), 'preclip_norm': float(preclip), 'loss_labels': labels,
                'predicted_trace': output['trace'], 'total_advances': 4,
                'router_auxiliary_observed_excluded': float(output['auxiliary'].detach()),
                'auxiliary_weight': 0, 'teacherforced_tool_calls': 0,
                'teacherforced_argmax': pred.cpu().tolist(), 'lr': opt.param_groups[0]['lr']}
            if replay is not None and replay['records'] is not None:
                phase = 'replay-compare'
                replay_record_equal(record, replay['records'][additional - 1]); replay_matches += 1
            phase = 'durable-raw'; write('TRAIN-RAW.jsonl', record, True)
            phase = 'training'
        expected = Counter({identity: 40 for identity in cfg['original_ids']}); expected.update(schedule)
        if replay is not None and args.seed == 0 and replay_matches != UPDATES:
            raise ValueError('all1024 exact replay comparisons required before checkpoint')
        if updates != UPDATES or visits != expected:
            raise ValueError('calculator final exposure differs')
        if component_fingerprint(lm) != lm_before or component_fingerprint(core.halt) != halt_before:
            raise ValueError('frozen LM/halt changed')
        buffers_after = dict(core.named_buffers())
        if (buffers_before.keys() != buffers_after.keys() or not all(
                torch.equal(value, buffers_after[name].detach().cpu()) for name, value in buffers_before.items())):
            raise ValueError('original ordered buffers changed')
        phase = 'checkpoint'
        modules = base_modules + (('tool', tool),)
        fingerprints = {name: component_fingerprint(module) for name, module in modules}
        audit = []
        for name, p in named:
            state = opt.state.get(p, {}); step = int(state['step']) if state else 0
            if step != participation[name]:
                raise ValueError('final Adam steps differ from participation')
            audit.append({'name': name, 'participation': participation[name],
                'nonzero_gradient_updates': nonzero[name], 'Adam_step': step})
        checkpoint = {**identity, 'recipe': RECIPE, 'update': START_UPDATE + UPDATES,
            'additional_updates': UPDATES, 'constructor': core.constructor(), 'tool_constructor': tool.constructor(),
            **{name: module.state_dict() for name, module in modules}, 'optimizer': opt.state_dict(),
            'optimizer_parameter_names': [name for name, _ in named],
            'optimizer_group_parameter_names': [[name for name, _ in old_named], [name for name, _ in tool_named]],
            'optimizer_audit': audit, 'participation': dict(participation),
            'torch_rng': torch.get_rng_state(), 'cuda_rng': torch.cuda.get_rng_state_all(),
            'python_rng': random.getstate(), 'visits': dict(visits), 'model_state_fingerprints': fingerprints,
            'TRAIN_raw_sha256': helpers.sha(out / 'TRAIN-RAW.jsonl'), 'raw_watermark_update': START_UPDATE + UPDATES,
            'schedule_cursor': UPDATES, 'optimizer_runtime_seconds': optimizer_budget.elapsed,
            'model_call_account': dict(calls), 'tool_call_account': dict(tool_calls),
            'operational_replay_reference': None if replay is None else replay['reference'],
            'exact_replay_update_matches': replay_matches,
            'source_input_frames_sha256': entry['original_frames']['sha256']}
        allowance = cfg['budget']['checkpoint_cap_bytes']
        if 3 * sum(p.numel() * p.element_size() for p in params) + 3 * 1024 ** 2 > allowance:
            raise RuntimeError('calculator final-only checkpoint bound exceeds reservation')
        path = out / 'final-resume.pt'
        checkpoint_io.save_reserved(path, allowance, lambda sink: torch.save(checkpoint, sink),
            sealed.save_new_atomic_file, guard, lambda: shutil.disk_usage(root).free,
            cfg['budget']['retained_free_bytes'], unit)
        timeout(); restored = torch.load(path, map_location='cpu', weights_only=True)
        if (not helpers.state_equal(checkpoint, restored, torch)
                or not torch.equal(restored['torch_rng'], torch.get_rng_state())
                or not helpers.state_equal(restored['cuda_rng'], torch.cuda.get_rng_state_all(), torch)
                or restored['python_rng'] != random.getstate()):
            raise ValueError('calculator durable model/Adam/RNG checkpoint equality failed')
        del restored, checkpoint
        phase = 'closure'
        write('CLOSED.json', {**identity, 'closed': True, 'optimizer_updates': START_UPDATE + UPDATES,
            'additional_optimizer_updates': UPDATES, 'optimizer_updates_this_process': UPDATES,
            'checkpoint': {'path': str(path.relative_to(root)), 'sha256': helpers.sha(path)},
            'TRAIN_raw_sha256': helpers.sha(out / 'TRAIN-RAW.jsonl'), 'visits': dict(visits),
            'final_fingerprints': fingerprints, 'tool_constructor': tool.constructor(),
            'LM_unchanged': True, 'halt_unchanged': True, 'ordered_core_buffers_unchanged': True,
            'durable_model_and_Adam_reload_equal': True, 'no_midpoint_checkpoint': True,
            'native_TRAIN_generation_performed': False, 'fresh_evaluation_performed': False,
            'teacherforced_tool_calls': 0, 'model_call_account': dict(calls),
            'operational_replay_reference': None if replay is None else replay['reference'],
            'exact_replay_update_matches': replay_matches,
            'prior_failed_attempt_optimizer_updates': 0 if replay is None else replay['prior_actual_optimizer_updates'],
            'prior_failed_attempt_model_calls': 0 if replay is None else replay['prior_actual_model_calls'],
            'tool_call_account': dict(tool_calls),
            'model_calls': calls['TRAIN_optimizer_teacherforcing'], 'model_calls_exact': True,
            'optimizer_updates_exact': True, 'optimizer_runtime_seconds': optimizer_budget.elapsed,
            'wall_seconds': time.monotonic() - launched, 'resource_owned_rename_rechecks': resource_rechecks,
            'new_output_matrix_allocated_bytes': account()[0], 'project_allocated_bytes': account()[3],
            'free_bytes': shutil.disk_usage(root).free})
        print(json.dumps({'status': 'CLOSED-CALCULATOR1024', 'seed': args.seed,
            'additional_optimizer_updates': UPDATES, 'checkpoint_sha256': helpers.sha(path),
            'native_TRAIN_gate_passed': False, 'fresh_evaluation_performed': False}), flush=True)
    except Exception as error:
        try:
            write('FAILED.json', {**identity, 'additional_optimizer_updates': updates,
                'last_completed_model_call_account': dict(calls), 'model_calls_exact': phase == 'setup',
                'last_completed_tool_call_account': dict(tool_calls),
                'optimizer_updates_exact': phase not in ('optimizer-step',), 'phase': phase,
                'error_type': type(error).__name__, 'error': str(error), 'evidence_preserved': True,
                'safe_parent_checkpoint': entry['checkpoint'], 'no_midpoint_checkpoint': True,
                'exact_replay_update_matches': replay_matches,
                'operational_replay_reference': None if replay is None else replay['reference']})
        except Exception as receipt_error:
            print(json.dumps({'status': 'FAILURE-RECEIPT-BLOCKED', 'primary_error': str(error),
                'receipt_error': str(receipt_error), 'output_directory': str(out),
                'existing_evidence_preserved': True}), flush=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True); parser.add_argument('--config', required=True)
    parser.add_argument('--config-sha256', required=True)
    parser.add_argument('--seed', type=int, choices=(0, 1), required=True)
    parser.add_argument('--check', action='store_true')
    run(parser.parse_args())
