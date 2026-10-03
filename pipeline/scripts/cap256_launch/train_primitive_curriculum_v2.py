"""Prepared TRAIN-only primitive continuation; no default dispatch permission.

The model recipe is the pinned mixture fast-I/O recipe: four latent loops,
question-only English, numeric-answer CE, frozen LM/halt, original AdamW/RNG.
The only experimental change is balanced add/subtract TRAIN exposure. Native
TRAIN generation and fresh evaluation belong to separately pinned workers.

--check is a CPU/file-only readiness check. It never imports Torch or opens
evaluation examples. A preparation manifest must keep dispatch_allowed false
until the corpus, split, control equivalence, budget and live driver are ready.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import re
import shutil
import sys
import time


UPDATES = 10240
MIDPOINT = 5120
START_UPDATE = 10240
OPERATIONS = ('add', 'subtract')
CASES = ('carry', 'no_carry', 'borrow', 'no_borrow')
CASE_OPERATION = {'carry': 'add', 'no_carry': 'add',
                  'borrow': 'subtract', 'no_borrow': 'subtract'}
CASE_EXPOSURE = UPDATES // len(CASES)
RECIPE = {
    'batch': 1, 'rounds': 4, 'input_scope': 'question-only-empty-notebook',
    'objective': 'numeric-answer-CE-only', 'auxiliary_weight': 0,
    'trainable_modules': ['core', 'reader', 'prefix'], 'halt_frozen': True,
    'LM_frozen': True, 'full_FP32': True, 'optimizer_reset': False,
    'optimizer': {'name': 'AdamW', 'lr': 0.001, 'weight_decay': 0,
                  'betas': [0.9, 0.999], 'eps': 1e-8, 'clip_norm': 1},
    'source_update': START_UPDATE, 'additional_updates': UPDATES,
    'numeric_regime': 'positive-two-digit-operands-and-result',
    'case_exposure': {case: CASE_EXPOSURE for case in CASES},
}
FRAME_FIELDS = ('input_ids', 'input_mask', 'labels', 'label_mask',
                'notebook_ids', 'notebook_mask')
RUNTIME_FILES = (
    'scripts/sol_translator_grounding_v6.py',
    'scripts/sol_translator_english_ordered_v10.py',
    'scripts/sol_spatial_poc_ordered_v2.py',
    'scripts/sol_spatial_poc_ordered_train_api_v2.py',
    'scripts/sol_stop_ordered_api2.py',
    'scripts/sol_translator_runtime.py',
)
PROTECTED = ('uncle-questions', 'readpanel320', '/blind/', 'sealed-panels',
             'sealedquestions', 'sealed-user', 'sealeduser', 'sealed-blind',
             'dev100', 'stop88', 'reserved-pool', '/confirmation/')


def canonical(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True,
        separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def safe(root, relative):
    root = Path(root).resolve()
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('root-relative path required')
    resolved = (root / path).resolve()
    text = '/' + str(resolved).replace('\\', '/').lower().strip('/') + '/'
    if not resolved.is_relative_to(root) or any(item in text for item in PROTECTED):
        raise ValueError('protected or out-of-root path refused before content access')
    return resolved


def pinned(root, pin):
    if (type(pin) is not dict or set(pin) != {'path', 'sha256'}
            or not isinstance(pin['sha256'], str)
            or not re.fullmatch('[0-9a-f]{64}', pin['sha256'])):
        raise ValueError('exact path/SHA256 pin required')
    path = safe(root, pin['path'])
    if sha(path) != pin['sha256']:
        raise ValueError('pinned bytes differ: ' + pin['path'])
    return path


def selected_by_id(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('nonempty selected TRAIN rows required')
    result = {}
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('id'), str)
                or not row['id'] or row['id'] in result
                or row.get('operation') not in OPERATIONS
                or row.get('case') not in CASES
                or row['operation'] != CASE_OPERATION.get(row.get('case'))
                or row.get('split_role') != 'TRAIN'
                or row.get('independently_verified') is not True
                or not isinstance(row.get('source_group'), str) or not row['source_group']
                or not isinstance(row.get('question_sha256'), str)
                or not re.fullmatch('[0-9a-f]{64}', row['question_sha256'])):
            raise ValueError('unique independently checked direct add/sub TRAIN row required')
        result[row['id']] = row
    if {r['case'] for r in rows} != set(CASES):
        raise ValueError('all four included direct-arithmetic cases must have TRAIN rows')
    return result


def exposure_counts(rows):
    """Exactly 2560 visits per case; row counts differ by at most one per case.

    ID sorting fixes which rows receive an extra visit, independent of the
    manifest row order. No requirement for 256 focused rows is introduced.
    """
    byid = selected_by_id(rows)
    wanted = Counter()
    for case in CASES:
        ids = sorted(i for i, row in byid.items() if row['case'] == case)
        quotient, remainder = divmod(CASE_EXPOSURE, len(ids))
        if quotient < 1:
            raise ValueError('every selected row must receive exposure')
        wanted.update({i: quotient + (n < remainder) for n, i in enumerate(ids)})
    return wanted


def make_schedule(rows, seed):
    """Preparation helper uses an isolated RNG; never consumes model RNG."""
    if seed not in (0, 1):
        raise ValueError('two matched seeds only')
    counts = exposure_counts(rows)
    schedule = [i for i in sorted(counts) for _ in range(counts[i])]
    random.Random(seed).shuffle(schedule)
    return schedule


def validate_exposure(schedule, rows):
    if not isinstance(schedule, list) or len(schedule) != UPDATES:
        raise ValueError('exact 10240-update schedule required')
    if any(not isinstance(i, str) for i in schedule) or Counter(schedule) != exposure_counts(rows):
        raise ValueError('fixed balanced TRAIN exposure differs')


def readiness_issues(cfg):
    """Report missing decisions without promoting an unreleased manifest."""
    issues = []
    if cfg.get('dispatch_allowed') is not True:
        issues.append('dispatch_allowed is not true; preparation only')
    for key in ('corpus_frozen', 'fresh_evaluation_frozen',
                'control_equivalence_verified', 'throughput_budget_verified',
                'live_driver_verified'):
        if cfg.get('readiness', {}).get(key) is not True:
            issues.append(key + ' is not verified')
    return issues


def validate_config(cfg):
    if (cfg.get('schema') != 'cap256.primitive-curriculum.v1'
            or cfg.get('seeds') != [0, 1] or cfg.get('additional_updates') != UPDATES
            or cfg.get('lr') != 0.001 or cfg.get('recipe') != RECIPE
            or cfg.get('arm') != 'primitive'):
        raise ValueError('unchanged primitive continuation protocol required')
    selected_by_id(cfg.get('selected_rows'))
    original = cfg.get('original_ids')
    if (not isinstance(original, list) or len(original) != 256
            or any(not isinstance(i, str) for i in original) or len(set(original)) != 256):
        raise ValueError('original256 initialization IDs required')
    sources = cfg.get('sources', [])
    if len(sources) != 2 or sorted(e.get('seed') for e in sources) != [0, 1]:
        raise ValueError('one exact original-loop40 source for each seed required')
    budget = cfg.get('budget', {})
    required = ('optimizer_seconds', 'worker_seconds', 'matrix_cap_bytes',
                'pair_cap_bytes', 'project_cap_bytes', 'retained_free_bytes',
                'raw_cap_bytes_per_pair', 'checkpoint_cap_bytes',
                'cuda_peak_reserved_cap_bytes')
    if any(type(budget.get(k)) not in (int, float) or budget[k] <= 0 for k in required):
        raise ValueError('explicit positive measured resource caps required')
    if (budget['optimizer_seconds'] > 1800 or budget['worker_seconds'] > 2400
            or budget['optimizer_seconds'] >= budget['worker_seconds']
            or budget['project_cap_bytes'] > 100_000_000_000
            or budget['cuda_peak_reserved_cap_bytes'] > 16 * 1024 ** 3
            or budget['retained_free_bytes'] < 1024 ** 3
            or budget.get('source') != 'new-run-measured-planning-caps'
            or budget.get('historical_recovery_budget_reused') is not False):
        raise ValueError('current resources/planning caps differ; recovery budget is not inherited')
    if budget['checkpoint_cap_bytes'] > 128 * 1024 ** 2:
        raise ValueError('checkpoint allowance exceeds pinned storage transient reservation')
    for key in ('output_namespace', 'input_namespace'):
        if not isinstance(cfg.get(key), str) or not cfg[key]:
            raise ValueError('explicit input/output namespace required')
    if not isinstance(cfg.get('output_accounting_extra_paths'), list):
        raise ValueError('complete external output accounting paths required')


def validate_frames(packet, rows, originals):
    frames = packet.get('rows')
    if not isinstance(frames, list) or len(frames) != len(rows):
        raise ValueError('focused frame packet must contain exactly selected TRAIN rows')
    byid = {}
    original_byid = {f['id']: f for f in originals}
    for frame in frames:
        identity = frame.get('id')
        if identity not in rows or identity in byid:
            raise ValueError('unselected or duplicate frame refused')
        if frame.get('question_sha256') != rows[identity]['question_sha256']:
            raise ValueError('TRAIN frame binds a different question')
        content = {k: v for k, v in frame.items() if k != 'frame_sha256'}
        if frame.get('frame_sha256') != canonical(content):
            raise ValueError('TRAIN frame self-hash differs')
        if (frame.get('notebook_ids') != [[]] or frame.get('notebook_mask') != [[]]
                or any(not isinstance(frame.get(k), list) or len(frame[k]) != 1
                       for k in ('input_ids', 'input_mask', 'labels', 'label_mask'))
                or not frame['input_ids'][0] or not frame['labels'][0]
                or len(frame['input_ids'][0]) > 48 or len(frame['labels'][0]) > 32
                or frame['input_mask'] != [[True] * len(frame['input_ids'][0])]
                or frame['label_mask'] != [[t != -100 for t in frame['labels'][0]]]
                or any(type(t) is not int or t < 0 for k in ('input_ids', 'labels') for t in frame[k][0])):
            raise ValueError('untruncated question-only numeric TRAIN frame required')
        if identity in original_byid:
            for key in FRAME_FIELDS:
                if frame[key] != original_byid[identity][key]:
                    raise ValueError('existing original TRAIN frame differs: ' + key)
        byid[identity] = frame
    if set(byid) != set(rows):
        raise ValueError('focused TRAIN IDs differ')
    return byid


def validate_initial_metadata(prior, closed, entry, original_ids):
    if (prior.get('update') != START_UPDATE or prior.get('raw_watermark_update') != START_UPDATE
            or prior.get('visits') != {i: 40 for i in original_ids}
            or closed.get('optimizer_updates') != START_UPDATE
            or closed.get('closed') is not True or closed.get('checkpoint') != entry['checkpoint']):
        raise ValueError('actual original-loop40 checkpoint metadata must be update10240')
    required = ('constructor', 'core', 'reader', 'prefix', 'optimizer',
                'optimizer_parameter_names', 'optimizer_audit', 'participation',
                'torch_rng', 'cuda_rng', 'python_rng')
    if any(k not in prior for k in required):
        raise ValueError('complete original model/Adam/RNG state required')


def validate_control_config(control, cfg, entry, seed):
    """Validate actual pinned history inputs, never a stale source_update label."""
    if (control.get('additional_updates') != UPDATES or control.get('lr') != 0.001
            or control.get('seeds') != [0, 1] or 'repeat256' not in control.get('arms', [])
            or control.get('original_ids') != cfg['original_ids']):
        raise ValueError('historical control is not matched repeat-data continuation')
    for key in ('source_plan', 'source_seal', 'source_release', 'source_runner'):
        if control.get(key) != cfg[key]:
            raise ValueError('historical control source/runtime pin differs: ' + key)
    source = [e for e in control.get('sources', []) if e.get('seed') == seed and e.get('arm') == 'repeat256']
    if len(source) != 1 or any(source[0].get(k) != entry[k]
            for k in ('checkpoint', 'closed', 'original_frames')):
        raise ValueError('historical control actual initialization differs')


def restore_prefix(source, destination, cursor, schedule, frames, original_ids,
                   expected_hash, expected_config, guard):
    """Copy validated saved raw prefix into a new namespace; retain its identity."""
    if cursor != MIDPOINT:
        raise ValueError('only durable fixed midpoint resume is supported')
    visits = Counter({i: 40 for i in original_ids})
    digest = hashlib.sha256()
    payload = []
    with Path(source).open('rb') as stream:
        for n in range(1, cursor + 1):
            line = stream.readline()
            if not line.endswith(b'\n'):
                raise ValueError('incomplete saved TRAIN prefix')
            record = json.loads(line)
            identity = schedule[n - 1]
            visits[identity] += 1
            frame = frames[identity]
            if (record.get('additional_update') != n or record.get('update') != START_UPDATE + n
                    or record.get('id') != identity or record.get('visit_for_row') != visits[identity]
                    or record.get('config_sha256') != expected_config
                    or any(record.get(k) != frame[k] for k in ('labels', 'label_mask', 'frame_sha256'))):
                raise ValueError('saved prefix cursor/provenance/frame differs')
            digest.update(line)
            payload.append(line)
    if digest.hexdigest() != expected_hash:
        raise ValueError('saved prefix hash differs')
    data = b''.join(payload)
    guard(len(data) + 65536)
    with Path(destination).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return visits


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def state_equal(left, right, torch_api):
    """Exact recursive model/Adam/RNG coverage, including param groups/flags."""
    if torch_api.is_tensor(left):
        return torch_api.is_tensor(right) and torch_api.equal(left.detach().cpu(), right.detach().cpu())
    if isinstance(left, dict):
        return isinstance(right, dict) and left.keys() == right.keys() and all(
            state_equal(left[k], right[k], torch_api) for k in left)
    if isinstance(left, (list, tuple)):
        return type(left) is type(right) and len(left) == len(right) and all(
            state_equal(a, b, torch_api) for a, b in zip(left, right))
    return left == right


def verify_runtime_imports(root, seal, extra_pins):
    """Reject unsealed root modules and cached imports from another checkout."""
    expected_paths = {safe(root, relative): expected for relative, expected in seal['files'].items()}
    expected_paths.update({safe(root, pin['path']): pin['sha256'] for pin in extra_pins})
    virtual_torch = {
        'torch.ops': ('torch._ops', '_Ops', '_ops.py'),
        'torch.classes': ('torch._classes', '_Classes', '_classes.py'),
    }
    for module_name, module in tuple(sys.modules.items()):
        # Torch's virtual namespaces implement dynamic __getattr__. Inspect
        # stored metadata directly, never inventing module/file attributes.
        try:
            attributes = vars(module)
        except TypeError:
            continue
        location = attributes.get('__file__')
        if not location:
            continue
        signature = virtual_torch.get(module_name)
        if signature and (
                attributes.get('__name__') == module_name
                and attributes.get('__spec__') is None
                and (type(module).__module__, type(module).__name__, location) == signature
                and not Path(location).is_absolute() and not Path(location).exists()
                and not (root / location).exists()):
            continue  # only the two proven non-file Torch namespaces
        path = Path(location).resolve()
        if path.is_relative_to(root):
            if path not in expected_paths or sha(path) != expected_paths[path]:
                raise ValueError('unsealed or changed imported project module: ' + str(path))
    for name, relative in (
            ('sol_translator_grounding_v6', RUNTIME_FILES[0]),
            ('sol_translator_english_ordered_v10', RUNTIME_FILES[1]),
            ('sol_spatial_poc_ordered_v2', RUNTIME_FILES[2]),
            ('sol_spatial_poc_ordered_train_api_v2', RUNTIME_FILES[3]),
            ('scripts.sol_stop_ordered_api2', RUNTIME_FILES[4]),
            ('sol_translator_runtime', RUNTIME_FILES[5])):
        if Path(vars(sys.modules[name])['__file__']).resolve() != safe(root, relative):
            raise ValueError('named runtime import resolves outside the pinned root')


def preflight(root, cfg, seed):
    """Hash/read only TRAIN, code, provenance, control and protocol metadata."""
    validate_config(cfg)
    issues = readiness_issues(cfg)
    if issues:
        raise ValueError('; '.join(issues))
    pins = {key: pinned(root, cfg[key]) for key in (
        'source_plan', 'source_seal', 'source_release', 'source_runner',
        'runner', 'frames', 'schedules', 'storage_snapshot', 'checkpoint_io',
        'corpus_audit', 'evaluation_protocol', 'control_audit', 'throughput_receipt')}
    if pins['runner'].resolve() != Path(__file__).resolve():
        raise ValueError('running primitive code is not the declared runner pin')
    seal = read(pins['source_seal'])
    if any(path not in seal['files'] for path in RUNTIME_FILES):
        raise ValueError('runtime imports not covered by original source seal')
    for relative, expected in seal['files'].items():
        pinned(root, {'path': relative, 'sha256': expected})
    old = read(pins['source_plan'])
    entry = next(e for e in cfg['sources'] if e['seed'] == seed)
    paths = {key: pinned(root, entry[key]) for key in ('checkpoint', 'closed', 'original_frames')}
    originals = read(paths['original_frames'])['rows']
    if len(originals) != 256 or {f['id'] for f in originals} != set(cfg['original_ids']):
        raise ValueError('original frames no longer bind the original256 initialization')
    rows = selected_by_id(cfg['selected_rows'])
    frames = validate_frames(read(pins['frames']), rows, originals)
    packet = read(pins['schedules'])
    for selected_seed in (0, 1):
        validate_exposure(packet['schedules'][str(selected_seed)]['primitive'], cfg['selected_rows'])
    controls = cfg.get('controls')
    if (not isinstance(controls, list) or len(controls) != 2
            or sorted(c.get('seed') for c in controls) != [0, 1]):
        raise ValueError('both immutable matched historical controls required')
    audit = read(pins['control_audit'])
    if (audit.get('recipe') != RECIPE or audit.get('exact_equivalence_verified') is not True
            or audit.get('runner') != cfg['runner']
            or audit.get('control_endpoints') != controls):
        raise ValueError('independent exact control recipe/provenance audit incomplete')
    for control in controls:
        init = next(e for e in cfg['sources'] if e['seed'] == control['seed'])
        history_path = pinned(root, control['config'])
        history = read(history_path)
        validate_control_config(history, cfg, init, control['seed'])
        for key in ('runner', 'checkpoint', 'closed', 'schedules'):
            pinned(root, control[key])
        if control['schedules'] != history['schedules']:
            raise ValueError('control schedule provenance differs')
        control_schedule = read(root / control['schedules']['path'])['schedules'][str(control['seed'])]['repeat256']
        if len(control_schedule) != UPDATES or Counter(control_schedule) != Counter({i: 40 for i in cfg['original_ids']}):
            raise ValueError('historical control does not have matched original TRAIN exposure')
        closed = read(root / control['closed']['path'])
        if (closed.get('closed') is not True or closed.get('optimizer_updates') != START_UPDATE + UPDATES
                or closed.get('additional_optimizer_updates') != UPDATES
                or closed.get('checkpoint') != control['checkpoint']
                or closed.get('source_checkpoint_sha256') != init['checkpoint']['sha256']
                or closed.get('source_runner_sha256') != cfg['source_runner']['sha256']
                or closed.get('config_sha256') != control['config']['sha256']
                or closed.get('optimizer_reset') is not False):
            raise ValueError('actual historical control closure does not prove a matched completed arm')
    return pins, old, entry, paths, frames, packet['schedules'][str(seed)]['primitive']


def run(args):
    root = Path(args.root).resolve()
    config = Path(args.config).resolve()
    if not config.is_relative_to(root) or sha(config) != args.config_sha256:
        raise ValueError('root-bound config pin differs')
    cfg = read(config)
    if args.check:
        validate_config(cfg)
        issues = readiness_issues(cfg)
        if not issues:
            preflight(root, cfg, args.seed)
        print(json.dumps({'status': 'PREPARED-BLOCKED' if issues else 'CPU-PREFLIGHT-PASSED',
            'issues': issues, 'model_imported': False, 'optimizer_updates': 0,
            'live_execution_validated': False}), flush=True)
        return
    pins, old, entry, paths, frames_byid, schedule = preflight(root, cfg, args.seed)
    if os.environ.get('TREE') != str(root) or not os.environ.get('JOB'):
        raise ValueError('exclusive driver TREE/JOB binding required')
    # Driver owns the exclusive queue lock. Worker records its identity rather
    # than starting a second supervisor or choosing an unqueued successor.
    if cfg.get('exclusive_lock_verified') is not True:
        raise ValueError('exclusive live driver gate incomplete')
    sealed = load_module(pins['source_runner'], '_sealed_primitive_recipe')
    sealed.validate_plan(old)
    storage = load_module(pins['storage_snapshot'], '_pinned_primitive_storage')
    checkpoint_io = load_module(pins['checkpoint_io'], '_pinned_primitive_checkpoint_io')
    matrix = safe(root, cfg['output_namespace'])
    out = matrix / ('seed%d' % args.seed) / 'primitive'
    if out.exists():
        raise RuntimeError('output exists; preserve evidence instead of repeating a job')
    extra_paths = [safe(root, path) for path in cfg['output_accounting_extra_paths']]
    unit = storage.filesystem_allocation_unit(root)
    def account():
        return (storage.allocated_bytes(matrix, unit) + sum(storage.allocated_bytes(p, unit) for p in extra_paths),
                storage.allocated_bytes(out.parent, unit), storage.raw_allocated_bytes(out.parent, unit),
                storage.allocated_bytes(root, unit))
    def guard(extra=0):
        output, pair, raw, project = account()
        budget = cfg['budget']
        if output + extra > budget['matrix_cap_bytes'] or pair + extra > budget['pair_cap_bytes']:
            raise RuntimeError('new output matrix/pair cap exceeded')
        if (project + extra > budget['project_cap_bytes']
                or shutil.disk_usage(root).free - extra < budget['retained_free_bytes']):
            raise RuntimeError('project cap/free reserve exceeded')
        return output, pair, raw, project
    guard(unit)
    out.mkdir(parents=True)
    identity = {'schema': 'cap256.primitive-curriculum.identity.v1', 'job': os.environ['JOB'],
        'seed': args.seed, 'arm': 'primitive', 'config_sha256': args.config_sha256,
        'runner_sha256': cfg['runner']['sha256'], 'source_checkpoint_sha256': entry['checkpoint']['sha256'],
        'source_plan_sha256': cfg['source_plan']['sha256'], 'source_runner_sha256': cfg['source_runner']['sha256'],
        'source_seal_sha256': cfg['source_seal']['sha256'], 'schedule_sha256': cfg['schedules']['sha256'],
        'optimizer_reset': False, 'TRAIN_only': True, 'halt_frozen': True, 'LM_frozen': True,
        'qualification': 'narrow-joint-wording-and-within-regime-numeric-transfer',
        'sleep_enabled': False, 'generation_performed': False}
    def write(name, record, append=False):
        data = (json.dumps(record, sort_keys=True, allow_nan=False, separators=(',', ':')) + '\n').encode()
        snapshot = guard(len(data) + unit)
        if snapshot[2] + len(data) + unit > cfg['budget']['raw_cap_bytes_per_pair']:
            raise RuntimeError('raw pair cap exceeded')
        with (out / name).open('ab' if append else 'xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
    launched = time.monotonic()
    resume = cfg.get('resume_sources', {}).get(str(args.seed))
    cursor = MIDPOINT if resume else 0
    updates = cursor
    calls = Counter()
    write('LAUNCH.json', {**identity, 'start_update': START_UPDATE + cursor,
        'target_update': START_UPDATE + UPDATES, 'additional_updates': UPDATES,
        'operation_exposure': {'add': MIDPOINT, 'subtract': MIDPOINT},
        'case_exposure': RECIPE['case_exposure'],
        'selected_TRAIN_rows': len(frames_byid), 'initial_free_bytes': shutil.disk_usage(root).free,
        'recipe': RECIPE, 'native_TRAIN_fitting_separate': True})
    try:
        sys.path[:0] = [str(root), str(root / 'scripts')]
        os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TRANSFORMERS_OFFLINE'] = '1'
        import torch
        from sol_translator_grounding_v6 import HumanInputProjection, human_loss
        from sol_translator_english_ordered_v10 import load_ordered_english
        from sol_spatial_poc_ordered_v2 import load_ordered_bundle
        from sol_spatial_poc_ordered_train_api_v2 import fixed4_training
        from scripts.sol_stop_ordered_api2 import ordered_attention_math
        from sol_translator_runtime import component_fingerprint
        verify_runtime_imports(root, read(pins['source_seal']),
            [cfg[key] for key in ('runner', 'source_runner', 'storage_snapshot', 'checkpoint_io')])
        torch.set_num_threads(2)
        if not torch.cuda.is_available():
            raise RuntimeError('authorized CUDA unavailable')
        runtime = {'python': platform.python_version(), 'torch': str(torch.__version__),
                   'cuda': torch.version.cuda, 'device': torch.cuda.get_device_name(0)}
        if read(pins['control_audit']).get('runtime') != runtime:
            raise ValueError('actual runtime differs from audited historical controls')
        original = torch.load(paths['checkpoint'], map_location='cpu', weights_only=True)
        closed = read(paths['closed'])
        validate_initial_metadata(original, closed, entry, cfg['original_ids'])
        # Actual historical endpoint metadata is checked independently of the
        # old config's stale source_update field and audit assertions.
        for control in cfg['controls']:
            endpoint = torch.load(root / control['checkpoint']['path'], map_location='cpu', weights_only=True)
            source = next(e for e in cfg['sources'] if e['seed'] == control['seed'])
            if (endpoint.get('update') != START_UPDATE + UPDATES
                    or endpoint.get('raw_watermark_update') != START_UPDATE + UPDATES
                    or endpoint.get('source_checkpoint_sha256') != source['checkpoint']['sha256']
                    or endpoint.get('optimizer_reset') is not False
                    or endpoint.get('visits') != {i: 80 for i in cfg['original_ids']}
                    or endpoint.get('schedule_cursor') != UPDATES):
                raise ValueError('actual control checkpoint update/init/exposure differs')
            del endpoint
        binding = old['warmstart']['tuples'][str(args.seed)]
        dec, _, _ = load_ordered_english(binding['lm_path'], binding['lm_provenance'], binding['adapter_path'], 'cuda')
        lm = dec.lm; lm.eval().requires_grad_(False)
        core, _ = load_ordered_bundle(binding['parent_path'], 'cuda')
        reader_raw = torch.load(binding['reader_path'], map_location='cpu', weights_only=True)
        reader = HumanInputProjection(reader_raw['lm_width']).to('cuda'); del reader_raw
        prior = original
        if resume:
            prior = torch.load(pinned(root, resume['checkpoint']), map_location='cpu', weights_only=True)
            expected = Counter({i: 40 for i in cfg['original_ids']}); expected.update(schedule[:cursor])
            if (prior.get('update') != START_UPDATE + cursor or prior.get('raw_watermark_update') != START_UPDATE + cursor
                    or prior.get('schedule_cursor') != cursor or prior.get('visits') != dict(expected)
                    or prior.get('config_sha256') != resume['source_config_sha256']
                    or prior.get('schedule_sha256') != cfg['schedules']['sha256']
                    or prior.get('source_checkpoint_sha256') != entry['checkpoint']['sha256']
                    or prior.get('recipe') != RECIPE):
                raise ValueError('midpoint lineage/cursor/recipe differs')
        if prior['constructor'] != core.constructor():
            raise ValueError('original constructor differs')
        modules = (('core', core), ('reader', reader), ('prefix', dec.adapter))
        expected_fingerprints = prior['model_state_fingerprints'] if resume else closed['final_fingerprints']
        for name, module in modules:
            module.load_state_dict(prior[name], strict=True)
            if component_fingerprint(module) != expected_fingerprints[name]:
                raise ValueError('initial model fingerprint differs: ' + name)
            module.train().requires_grad_(True)
        core.halt.requires_grad_(False)
        if any(p.dtype != torch.float32 for module in (core, reader, dec.adapter, lm) for p in module.parameters()):
            raise ValueError('original full-FP32 recipe differs')
        named = [(group + '.' + name, p) for group, module in modules
                 for name, p in module.named_parameters() if p.requires_grad]
        if [name for name, _ in named] != prior['optimizer_parameter_names']:
            raise ValueError('Adam parameter order differs')
        params = [p for _, p in named]
        opt = torch.optim.AdamW(params, lr=0.001, weight_decay=0, betas=(0.9, 0.999), eps=1e-8)
        opt.load_state_dict(prior['optimizer'])
        if not state_equal(prior['optimizer'], opt.state_dict(), torch):
            raise ValueError('complete loaded Adam state/groups/flags differ from source')
        for group in opt.param_groups:
            if (group['lr'], group['weight_decay'], group['betas'], group['eps']) != (0.001, 0, (0.9, 0.999), 1e-8):
                raise ValueError('inherited AdamW recipe differs')
        participation = Counter(prior['participation'])
        nonzero = Counter({r['name']: r['nonzero_gradient_updates'] for r in prior['optimizer_audit']})
        for name, p in named:
            state = opt.state.get(p, {})
            if (int(state['step']) if state else 0) != participation[name]:
                raise ValueError('actual Adam step differs from parameter participation')
        rng = (prior['torch_rng'], prior['cuda_rng'], prior['python_rng'])
        visits = Counter(prior['visits'])
        inherited_seconds = prior['optimizer_runtime_seconds'] if resume else 0
        if resume:
            calls.update(prior['model_call_account'])
            raw_source = pinned(root, resume['raw'])
            if account()[2] + raw_source.stat().st_size + unit > cfg['budget']['raw_cap_bytes_per_pair']:
                raise RuntimeError('restored raw prefix exceeds new pair cap')
            copied = restore_prefix(raw_source, out / 'TRAIN-RAW.jsonl', cursor, schedule,
                frames_byid, cfg['original_ids'], prior['TRAIN_raw_sha256'],
                resume['source_config_sha256'], guard)
            if copied != visits:
                raise ValueError('restored visits differ from durable checkpoint')
        del original, prior
        frames = list(frames_byid.values())
        tokens = []
        for frame in frames:
            if (frame['input_ids'][0][-1] != dec.eos_id or frame['labels'][0][-1] != dec.eos_id
                    or dec.eos_id in frame['input_ids'][0][:-1] or dec.eos_id in frame['labels'][0][:-1]):
                raise ValueError('actual tokenizer/EOS frame differs')
            tokens.append((torch.tensor(frame['input_ids'], device='cuda'),
                torch.tensor(frame['input_mask'], device='cuda', dtype=torch.bool),
                torch.tensor(frame['labels'], device='cuda')))
        byid = {f['id']: i for i, f in enumerate(frames)}
        lm_before = component_fingerprint(lm); halt_before = component_fingerprint(core.halt)
        core_buffers_before = {name: value.detach().cpu().clone() for name, value in core.named_buffers()}
        selected = selected_by_id(cfg['selected_rows'])
        torch.set_rng_state(rng[0]); torch.cuda.set_rng_state_all(rng[1]); random.setstate(rng[2])
        if (not torch.equal(torch.get_rng_state(), rng[0])
                or len(torch.cuda.get_rng_state_all()) != len(rng[1])
                or not all(torch.equal(a.cpu(), b.cpu()) for a, b in zip(torch.cuda.get_rng_state_all(), rng[1]))
                or random.getstate() != rng[2]):
            raise ValueError('saved model RNG was not restored exactly')
        del rng
        write('RESUME.json', {**identity, 'model_fingerprints_match_source': True,
            'parameter_order_matches_source': True, 'Adam_steps_match_source_participation': True,
            'model_rng_states_restored_before_first_update': True, 'optimizer_lr': 0.001,
            'start_update': START_UPDATE + cursor, 'source_input_frames_sha256': entry['original_frames']['sha256'],
            'constructor': core.constructor(), 'recipe': RECIPE,
            'runtime': runtime,
            'control_actual_checkpoint_metadata_verified': True})
        def graph(i):
            ids, mask, _ = tokens[i]
            with torch.no_grad():
                emb = lm.get_input_embeddings()(ids)
            query = reader(emb, mask)
            with ordered_attention_math():
                h, _, auxiliary = fixed4_training(core, query, None, query_mask=mask)
            prefix = dec.adapter.project_training(h, torch.ones_like(h, dtype=torch.bool), mask, (1, h.shape[1]))
            return prefix, auxiliary
        def timeout():
            if time.monotonic() - launched > cfg['budget']['worker_seconds']:
                raise RuntimeError('current-run worker planning time cap exceeded')
            if torch.cuda.max_memory_reserved() > cfg['budget']['cuda_peak_reserved_cap_bytes']:
                raise RuntimeError('reserved CUDA memory cap exceeded')
        optimizer_budget = sealed.OptimizerBudget(cfg['budget']['optimizer_seconds'])
        optimizer_budget.elapsed = inherited_seconds; optimizer_budget.check()
        @torch.no_grad()
        def diagnostic():
            saved = (torch.get_rng_state(), torch.cuda.get_rng_state_all(), random.getstate())
            for _, module in modules:
                module.eval()
            for i, frame in enumerate(frames):
                prefix, _ = graph(i)
                per, pred = human_loss(lm, prefix, tokens[i][2], dec.bos_id, dec.eos_id, True, True)
                calls['TRAIN_endpoint_teacherforcing'] += 1
                write('DIAGNOSTIC-RAW.jsonl', {**identity, 'update': START_UPDATE + UPDATES,
                    'id': frame['id'], 'operation': selected[frame['id']]['operation'],
                    'case': selected[frame['id']]['case'],
                    'numeric_CE': float(per.mean()), 'labels': frame['labels'],
                    'teacherforced_argmax': pred.cpu().tolist(), 'native_generation': False}, True)
                timeout()
            for _, module in modules:
                module.train()
            torch.set_rng_state(saved[0]); torch.cuda.set_rng_state_all(saved[1]); random.setstate(saved[2])
        def save_checkpoint(filename, additional):
            fingerprints = {name: component_fingerprint(module) for name, module in modules}
            audit = []
            for name, p in named:
                state = opt.state.get(p, {}); step = int(state['step']) if state else 0
                if step != participation[name]:
                    raise ValueError('Adam participation differs at checkpoint')
                audit.append({'name': name, 'participation': participation[name],
                    'nonzero_gradient_updates': nonzero[name], 'Adam_step': step})
            checkpoint = {**identity, 'recipe': RECIPE, 'update': START_UPDATE + additional,
                'additional_updates': additional, 'constructor': core.constructor(),
                **{name: module.state_dict() for name, module in modules},
                'optimizer': opt.state_dict(), 'optimizer_parameter_names': [n for n, _ in named],
                'optimizer_audit': audit, 'participation': dict(participation),
                'torch_rng': torch.get_rng_state(), 'cuda_rng': torch.cuda.get_rng_state_all(),
                'python_rng': random.getstate(), 'visits': dict(visits), 'model_state_fingerprints': fingerprints,
                'TRAIN_raw_sha256': sha(out / 'TRAIN-RAW.jsonl'),
                'DIAGNOSTIC_raw_sha256': sha(out / 'DIAGNOSTIC-RAW.jsonl') if (out / 'DIAGNOSTIC-RAW.jsonl').exists() else None,
                'source_input_frames_sha256': entry['original_frames']['sha256'],
                'source_schedule_sha256': old['schedules'][str(args.seed)]['sha256'],
                'raw_watermark_update': START_UPDATE + additional, 'schedule_cursor': additional,
                'optimizer_runtime_seconds': optimizer_budget.elapsed, 'model_call_account': dict(calls)}
            allowance = cfg['budget']['checkpoint_cap_bytes']
            if 3 * sum(p.numel() * p.element_size() for p in params) + 3 * 1024 ** 2 > allowance:
                raise RuntimeError('checkpoint serialization allowance insufficient')
            path = out / filename
            checkpoint_io.save_reserved(path, allowance, lambda sink: torch.save(checkpoint, sink),
                sealed.save_new_atomic_file, guard, lambda: shutil.disk_usage(root).free,
                cfg['budget']['retained_free_bytes'], unit)
            timeout()
            restored = torch.load(path, map_location='cpu', weights_only=True)
            if not state_equal(checkpoint, restored, torch):
                raise ValueError('durable checkpoint model/Adam/RNG reload differs')
            if (not torch.equal(restored['torch_rng'], torch.get_rng_state())
                    or not state_equal(restored['cuda_rng'], torch.cuda.get_rng_state_all(), torch)
                    or restored['python_rng'] != random.getstate()):
                raise ValueError('checkpoint I/O consumed model RNG')
            del restored, checkpoint
            timeout()
            return path, fingerprints
        for add, row_id in enumerate(schedule[cursor:], cursor + 1):
            timeout(); optimizer_budget.begin(); i = byid[row_id]
            opt.zero_grad(set_to_none=True); prefix, auxiliary = graph(i)
            per, pred = human_loss(lm, prefix, tokens[i][2], dec.bos_id, dec.eos_id, True, True)
            calls['TRAIN_optimizer_teacherforcing'] += 1
            def record_gradient():
                for name, p in named:
                    if p.grad is not None:
                        participation[name] += 1
                        if bool(torch.count_nonzero(p.grad)):
                            nonzero[name] += 1
            preclip = sealed.numeric_optimizer_step(per.mean(), opt, params, torch, record_gradient)
            torch.cuda.synchronize(); optimizer_budget.end(); updates = add; visits[row_id] += 1
            if any(p.grad is not None for p in lm.parameters()) or any(p.grad is not None for p in core.halt.parameters()):
                raise ValueError('frozen LM/halt acquired gradients')
            frame = frames[i]
            write('TRAIN-RAW.jsonl', {**identity, 'update': START_UPDATE + add,
                'additional_update': add, 'id': row_id, 'visit_for_row': visits[row_id],
                'numeric_CE': float(per.mean().detach()), 'preclip_norm': float(preclip),
                'router_auxiliary_observed_excluded': float(auxiliary.detach()), 'auxiliary_weight': 0,
                'objective': 'numeric-answer-CE-only', 'lr': opt.param_groups[0]['lr'],
                'frame_sha256': frame['frame_sha256'], 'labels': frame['labels'],
                'label_mask': frame['label_mask'], 'teacherforced_argmax': pred.cpu().tolist()}, True)
            if add == MIDPOINT:
                path, _ = save_checkpoint('midpoint-resume.pt', add)
                write('MIDPOINT.json', {**identity, 'additional_optimizer_updates': add,
                    'optimizer_updates': START_UPDATE + add,
                    'checkpoint': {'path': str(path.relative_to(root)), 'sha256': sha(path)},
                    'schedule_cursor': add, 'next_schedule_id': schedule[add],
                    'model_Adam_and_rng_reload_equal': True, 'optimizer_runtime_seconds': optimizer_budget.elapsed,
                    'no_extra_model_calls': True})
        expected = Counter({i: 40 for i in cfg['original_ids']}); expected.update(schedule)
        if updates != UPDATES or visits != expected:
            raise ValueError('final actual exposure differs')
        diagnostic()
        if component_fingerprint(lm) != lm_before or component_fingerprint(core.halt) != halt_before:
            raise ValueError('frozen LM/halt fingerprint changed')
        core_buffers_after = dict(core.named_buffers())
        if (core_buffers_before.keys() != core_buffers_after.keys()
                or not all(torch.equal(value, core_buffers_after[name].detach().cpu())
                           for name, value in core_buffers_before.items())):
            raise ValueError('ordered core boundary buffers changed')
        path, fingerprints = save_checkpoint('final-resume.pt', UPDATES)
        write('CLOSED.json', {**identity, 'closed': True, 'optimizer_updates': START_UPDATE + UPDATES,
            'additional_optimizer_updates': UPDATES, 'optimizer_updates_this_process': UPDATES - cursor,
            'inherited_prefix_updates': cursor, 'visits': dict(visits),
            'checkpoint': {'path': str(path.relative_to(root)), 'sha256': sha(path)},
            'TRAIN_raw_sha256': sha(out / 'TRAIN-RAW.jsonl'), 'DIAGNOSTIC_raw_sha256': sha(out / 'DIAGNOSTIC-RAW.jsonl'),
            'strict_TRAIN_generation_performed': False, 'TRAIN_fitting_established': False,
            'fresh_evaluation_performed': False, 'LM_unchanged': True, 'halt_unchanged': True,
            'durable_model_and_Adam_reload_equal': True, 'final_fingerprints': fingerprints,
            'ordered_core_buffers_unchanged': True, 'runtime': runtime,
            'wall_seconds': time.monotonic() - launched, 'optimizer_runtime_seconds': optimizer_budget.elapsed,
            'model_call_account': dict(calls), 'new_output_matrix_allocated_bytes': account()[0],
            'project_allocated_bytes': account()[3], 'free_bytes': shutil.disk_usage(root).free})
        print(json.dumps({'status': 'CLOSED-PRIMITIVE10240', 'seed': args.seed,
            'additional_optimizer_updates': UPDATES, 'checkpoint_sha256': sha(path),
            'TRAIN_fitting_established': False}), flush=True)
    except Exception as error:
        try:
            write('FAILED.json', {**identity, 'additional_optimizer_updates': updates,
                'error_type': type(error).__name__, 'error': str(error), 'evidence_preserved': True,
                'durable_midpoint_exists': (out / 'MIDPOINT.json').exists()})
        except Exception as receipt_error:
            print(json.dumps({'status': 'FAILURE-RECEIPT-BLOCKED', 'primary_error': str(error),
                'receipt_error': str(receipt_error), 'output_directory': str(out),
                'existing_evidence_preserved': True}), flush=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--config-sha256', required=True)
    parser.add_argument('--seed', type=int, choices=(0, 1), required=True)
    parser.add_argument('--check', action='store_true')
    run(parser.parse_args())
