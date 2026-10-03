"""Seal the treatment-only fresh-process disposable benchmark (adapted from v8 sealer).

No native call, SSH, model import, GPU or lock access. Mac-side only.

Real seal: writes TREATMENT-ONLY-ACTUAL-EXECUTION-v1/{STAGE-v1, ROOT-TRANSPORT-MANIFEST-v1.json,
ROOT-ACTIVATION-RECEIPT-v1.json} next to the v8 execution and starts the exact 600 s window
(start_by = start + 240 s). Invoke once, immediately before the single transport dispatch.

--dry-run: seals into the session scratchpad instead and runs every Mac-side validator the
transport, relay, driver and worker apply. It reports failures; it never weakens a check.

The authority thread id is never chosen here: --authority-thread-id must equal the literal the
staged worker (execution_authority) and driver (authority_check) compare against, and the
approval file's source_thread_id. A real seal refuses on any mismatch.
"""
import argparse
import ast
import copy
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback
from unittest.mock import patch

W = Path(__file__).resolve().parents[2]
S = W / 'scripts/cap256_launch'
B = W / 'artifacts/cap256-launch/contextual-input-compare-v1/TRAIN-TEMPLATE-CURRICULUM-PREPARATION-v1/LOCAL-DISPOSABLE-ARITHMETIC-BENCHMARK-v1'
V8 = B / 'ACTUAL-EXECUTION-v8'
V8_MANIFEST_SHA = '7a8a0050a9ca9490a15837add86fbb0ed37f55ccce7dee81df6cb05c7b2f1ce4'
DRY_RUN_BASE = Path('/private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model/'
                    '91b7a02a-b6fe-45d5-abb9-a04bfc1082ab/scratchpad/seal-dry-run')
PROJECT = 'C:/Users/benja/sol-cloud-numeric-capability-v1'
WORKER_REL = 'scripts/cap256_launch/benchmark_matched_template_curriculum_windows_treatment_only_v1.py'
DRIVER_REL = 'scripts/cap256_launch/execute_matched_template_curriculum_benchmark_windows_treatment_only_v1.py'
RELAY_REL = 'scripts/cap256_launch/native_disposable_arithmetic_benchmark_relay_treatment_only_v1.py'
TRANSPORT = S / 'execute_bounded_disposable_arithmetic_benchmark_transport_treatment_only_v1.py'
CONFIG_REL = 'cfg/BENCHMARK-CONFIG-v1.json'
REQUEST_REL = 'cfg/BENCHMARK-REQUEST-v1.json'
APPROVAL_REL = 'proof/ROOT-BOUNDED-TREATMENT-ONLY-AUTHORITY-v1.json'
APPROVAL_SOURCE = B / 'ROOT-BOUNDED-TREATMENT-ONLY-AUTHORITY-v1.json'
APPROVAL_SCHEMA = 'premonition.disposable-benchmark-treatment-only-approved-authority.v1'
PRIOR_REL = 'proof/PRIOR-CONTROL-RESUME-v8-endpoint0.json'
PRIOR_SOURCE = V8 / 'BENCHMARK-MAC-EXPORT-v1/canonical-native-output/benchmark-output-v1/endpoint-0/seed0/control/contextual/RESUME.json'
PRIOR_SHA = '3b82624987afef0edde69335f8c838810973032688d0085210bca1c1e7015be8'
PRIOR_BYTES = 6178
NATIVE_RECEIPT_REL = 'proof/ORIGINAL-NATIVE-OWNERSHIP-CPU-PROOF-v1.json'
ORIGINAL_CP = {'nativepath': PROJECT + '/launch-cap256/pkg/train-lr-stability-v1-20261002T134712Z/artifacts/'
                             'train-contextual-lr-stability-v1/control/seed0/contextual/final-resume.pt',
               'sha256': '49a350235164a7c2f4ccc2731358dc615cf8a25086abd32afe71e4c3bd44c001',
               'bytes': 60691431, 'destination': 'input-copy/original-seed0-global5120.pt'}
CONTROL_CP_SHA = '0818901ed3965762fddb689ca61970c42f71a34a454026b91cc04c4e469cd84f'
PRODUCER_LOCAL = S / 'train_contextual_input_continuation_windows_driver_v1.py'
WINDOW_SECONDS, START_BY_SECONDS, WORKER_SECONDS, CLOSURE_SECONDS = 600, 240, 400, 180
# v8 staged files NOT carried over: replaced sources, regenerated cfg/authority, v8-only proofs.
V8_EXCLUDED = {
    'scripts/cap256_launch/benchmark_matched_template_curriculum_windows_v4.py',
    'scripts/cap256_launch/execute_matched_template_curriculum_benchmark_windows_v1.py',
    'scripts/cap256_launch/native_disposable_arithmetic_benchmark_relay_v1.py',
    CONFIG_REL, REQUEST_REL,
    'artifacts/cap256-launch/contextual-input-compare-v1/TRAIN-TEMPLATE-CURRICULUM-PREPARATION-v1/'
    'LOCAL-DISPOSABLE-ARITHMETIC-BENCHMARK-v1/BENCHMARK-EXECUTION-RELEASE-v1.json',
    'proof/ROOT-BOUNDED-HOST16-BENCHMARK-AUTHORITY-v8.json',
    'proof/ACTUAL-NATIVE-SOURCE-AST-OWNERSHIP-COMPATIBILITY-v8.json',
    'proof/INDEPENDENT-NARROW-SOURCE-REVIEW-v4.json'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode() + b'\n'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def thread_literals(source, function):
    """String literals compared with authority.get('authority_thread_id') inside one function."""
    tree = ast.parse(source)
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function]
    assert len(fn) == 1, function
    found = []
    for node in ast.walk(fn[0]):
        if (isinstance(node, ast.Compare) and isinstance(node.left, ast.Call)
                and isinstance(node.left.func, ast.Attribute) and node.left.func.attr == 'get'
                and node.left.args and isinstance(node.left.args[0], ast.Constant)
                and node.left.args[0].value == 'authority_thread_id'):
            assert len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Constant)
            assert isinstance(node.ops[0], (ast.Eq, ast.NotEq)), 'equality check required'
            found.append(node.comparators[0].value)
    return found


def validate_approval(approval, thread_id, dry_run):
    problems = []
    def need(ok, message):
        if not ok:
            problems.append(message)
    need(approval.get('schema') == APPROVAL_SCHEMA, 'approval schema')
    need(approval.get('source_thread_id') == thread_id, 'approval source_thread_id != --authority-thread-id')
    caps = approval.get('caps', {})
    expected = {'overall_seconds': WINDOW_SECONDS, 'start_by_seconds': START_BY_SECONDS,
                'worker_seconds': WORKER_SECONDS, 'closure_seconds': CLOSURE_SECONDS,
                'endpoint_index': 1, 'arms': 1, 'optimizer_updates_max': 64, 'new_spend_USD': '0.00'}
    need(all(caps.get(k) == v and type(caps.get(k)) is type(v) for k, v in expected.items()), 'approval caps differ')
    evidence = approval.get('evidence_messages')
    need(type(evidence) is list and evidence and all(type(e) is dict and e.get('utc') and e.get('summary') for e in evidence),
         'approval evidence_messages required')
    if not dry_run:
        need(approval.get('dry_run') is False, 'real seal requires approval dry_run false')
    return problems


def build(args):
    dry = args.dry_run
    failures = []  # Only populated in dry-run; real seal asserts.
    def gate(ok, message):
        if ok:
            return
        if dry:
            failures.append(message)
        else:
            raise SystemExit('REFUSED: ' + message)

    # 1. Reviewed treatment-only sources (unsubstituted) and the transport, pinned by argument.
    sources = {}
    for rel, expected in ((WORKER_REL, args.worker_sha256), (DRIVER_REL, args.driver_sha256), (RELAY_REL, args.relay_sha256)):
        p = W / rel
        assert not p.is_symlink()
        data = p.read_bytes()
        assert sha(data) == expected, 'source pin mismatch: ' + rel + ' ' + sha(data)
        sources[rel] = data
    assert sha(TRANSPORT.read_bytes()) == args.transport_sha256, 'transport pin mismatch ' + sha(TRANSPORT.read_bytes())

    # 2. Thread id: only the literal the sources already enforce, never weakened here.
    worker_ids = thread_literals(sources[WORKER_REL].decode(), 'execution_authority')
    driver_ids = thread_literals(sources[DRIVER_REL].decode(), 'authority_check')
    assert len(worker_ids) == 1 and len(driver_ids) == 1, (worker_ids, driver_ids)
    gate(worker_ids[0] == driver_ids[0] == args.authority_thread_id,
         'staged sources enforce authority_thread_id %r (worker) / %r (driver); --authority-thread-id is %r'
         % (worker_ids[0], driver_ids[0], args.authority_thread_id))

    # 3. Approval file.
    approval_path = Path(args.approval_path).resolve() if args.approval_path else APPROVAL_SOURCE
    if not dry:
        assert approval_path == APPROVAL_SOURCE, 'real seal uses the fixed approval file'
    assert approval_path.is_file() and not approval_path.is_symlink(), 'approval file missing: ' + str(approval_path)
    approval_bytes = approval_path.read_bytes()
    assert sha(approval_bytes) == args.approval_sha256, 'approval pin mismatch ' + sha(approval_bytes)
    for problem in validate_approval(json.loads(approval_bytes), args.authority_thread_id, dry):
        gate(False, problem)

    # 4. Prior-control RESUME (positive transport file, external evidence only).
    prior_bytes = PRIOR_SOURCE.read_bytes()
    assert sha(prior_bytes) == PRIOR_SHA and len(prior_bytes) == PRIOR_BYTES

    # 5. v8 actual staged files (exact bytes that ran in v8), minus replaced/regenerated ones.
    v8_manifest_path = V8 / 'ROOT-TRANSPORT-MANIFEST-v1.json'
    assert sha(v8_manifest_path.read_bytes()) == V8_MANIFEST_SHA
    v8 = json.loads(v8_manifest_path.read_bytes())
    v8_stage = {}
    for record in v8['staged_positive_files']:
        p = V8 / 'STAGE-v1' / record['path']
        data = p.read_bytes()
        assert not p.is_symlink() and len(data) == record['bytes'] and sha(data) == record['sha256'], record['path']
        v8_stage[record['path']] = data
    assert V8_EXCLUDED <= set(v8_stage), V8_EXCLUDED - set(v8_stage)
    v8_cfg = json.loads(v8_stage[CONFIG_REL])
    v8_req = json.loads(v8_stage[REQUEST_REL])
    v8_auth = json.loads(v8_stage[v8_cfg['execution_release']['path']])

    # 6. Fresh native namespace and window.
    start = datetime.datetime.now(datetime.timezone.utc)
    stamp = start.strftime('%Y%m%dT%H%M%SZ')
    name = 'local-arithmetic-benchmark-treatment-only-v1-' + stamp
    native_root = PROJECT + '/launch-cap256/pkg/' + name
    deadline = start + datetime.timedelta(seconds=WINDOW_SECONDS)
    window = {'start': start.isoformat(), 'deadline': deadline.isoformat()}
    start_by = (start + datetime.timedelta(seconds=START_BY_SECONDS)).isoformat()

    # 7. Unsubstituted modules (for their own normalizers / config_core / envelope).
    execution = (DRY_RUN_BASE / ('TREATMENT-ONLY-ACTUAL-EXECUTION-v2-' + stamp)) if dry else (B / 'TREATMENT-ONLY-ACTUAL-EXECUTION-v2')
    tmp_mods = execution.parent / ('.seal-modules-' + stamp)
    tmp_mods.mkdir(parents=True, exist_ok=False)
    for rel in (WORKER_REL, DRIVER_REL):
        (tmp_mods / Path(rel).name).write_bytes(sources[rel])
    wmod = load_module('_seal_worker_unsubstituted', tmp_mods / Path(WORKER_REL).name)
    dmod = load_module('_seal_driver_unsubstituted', tmp_mods / Path(DRIVER_REL).name)
    worker_ast = wmod.normalized_source_sha256(sources[WORKER_REL].decode())
    driver_ast = dmod.normalized_source_sha256(sources[DRIVER_REL].decode())

    # 8. Config (v8 config + treatment-only fields).
    cfg = copy.deepcopy(v8_cfg)
    cfg.update(schema=wmod.SCHEMA, endpoint_index=1,
               runner={'path': WORKER_REL, 'sha256': None}, runner_normalized_AST_sha256=worker_ast,
               prior_control_resume={'path': PRIOR_REL, 'sha256': PRIOR_SHA, 'bytes': PRIOR_BYTES})
    cfg['budget'] = dict(cfg['budget'], worker_seconds=WORKER_SECONDS)
    assert cfg['parents'][0]['checkpoint']['sha256'] == ORIGINAL_CP['sha256'] != CONTROL_CP_SHA
    assert cfg['original_source_checkpoint']['sha256'] == ORIGINAL_CP['sha256']
    wmod.validate_budget(cfg['budget'], 64)
    config_core_sha = sha(wmod.canonical(wmod.config_core(cfg)))

    # 9. Request (v8 request + treatment-only fields; paths under the fresh root).
    req = copy.deepcopy(v8_req)
    req.update(schema=dmod.SCHEMA, endpoint_index=1, execution_order=[[0, 'treatment']],
               optimizer_updates_allowed=64, generation_calls_allowed=16, model_calls_allowed=144,
               job_id=name, attempt_id='a0', batch_id='a0', root=native_root)
    req['driver_budget'] = dict(req['driver_budget'], whole_job_seconds=WINDOW_SECONDS, closure_seconds=CLOSURE_SECONDS)
    for key, rel in (('driver', DRIVER_REL), ('worker_source', WORKER_REL), ('continuation_config', CONFIG_REL),
                     ('authority', cfg['execution_release']['path']), ('native_CPU_receipt', NATIVE_RECEIPT_REL)):
        req[key] = {'path': native_root + '/' + rel, 'sha256': req[key]['sha256']}
    dmod.validate_request(req)
    envelope = dmod.driver_envelope(req)

    # 10. Execution authority.
    authority = copy.deepcopy(v8_auth)
    authority.update(
        authority_thread_id=args.authority_thread_id, approved_action='RUN_DISPOSABLE_LOCAL_ARITHMETIC_THROUGHPUT_ONLY',
        approval_evidence_reference=APPROVAL_REL, approval_sha256=args.approval_sha256,
        activation_performed=True, qualification_only=False, qualification_window_utc=window, start_by_utc=start_by,
        actual_optimizer_updates_authorized=64, system_physical_and_commit_reserve_exclusive_bytes=8 * 1024 ** 3,
        config_core_sha256s=[config_core_sha], driver_envelopes=[envelope],
        driver_normalized_AST_sha256=driver_ast, runner_normalized_AST_sha256=worker_ast,
        native_CPU_proof_bridge={'producer_driver': v8_auth['native_CPU_proof_bridge']['producer_driver'],
                                 'receipt': dict(req['native_CPU_receipt'])},
        note='Treatment-only fresh process: physical endpoint1 (seed0 treatment) only, 64 updates/16 native/144 model calls '
             'from the original global5120 copy 49a350... (never control 0818901e...). Exact 600s window from root staging '
             'through export (start_by +240s, worker 400s, closure 180s). FP32/architecture/loss/data/initialization and '
             '16GiB host/10GiB CUDA/>8GiB reserve/storage guards unchanged. Prior control is external pinned evidence only. '
             'No EVAL/scoring/state promotion/retry/rental; spend 0.00. Prior attempts preserved.')
    authority_data = canonical(authority)
    authority_sha = sha(authority_data)

    # 11. Substitute the trusted anchor in staged worker/driver; normalized AST must not move.
    raw = {rel: data for rel, data in v8_stage.items() if rel not in V8_EXCLUDED}
    for rel, mod in ((WORKER_REL, wmod), (DRIVER_REL, dmod)):
        source = sources[rel].decode()
        needle = 'TRUSTED_EXECUTION_RELEASE_SHA256 = None'
        assert source.count(needle) == 1
        changed = source.replace(needle, 'TRUSTED_EXECUTION_RELEASE_SHA256 = ' + repr(authority_sha))
        assert mod.normalized_source_sha256(changed) == mod.normalized_source_sha256(source)
        raw[rel] = changed.encode()
    raw[RELAY_REL] = sources[RELAY_REL]
    cfg['runner']['sha256'] = sha(raw[WORKER_REL])
    cfg['execution_release'] = {'path': v8_cfg['execution_release']['path'], 'sha256': authority_sha}
    assert sha(wmod.canonical(wmod.config_core(cfg))) == config_core_sha
    cfg_data = canonical(cfg)
    req['driver']['sha256'] = sha(raw[DRIVER_REL])
    req['worker_source']['sha256'] = sha(raw[WORKER_REL])
    req['continuation_config']['sha256'] = sha(cfg_data)
    req['authority']['sha256'] = authority_sha
    assert dmod.driver_envelope(req) == envelope
    raw[cfg['execution_release']['path']] = authority_data
    raw[CONFIG_REL] = cfg_data
    raw[REQUEST_REL] = canonical(req)
    raw[APPROVAL_REL] = approval_bytes
    raw[PRIOR_REL] = prior_bytes
    assert sha(raw[NATIVE_RECEIPT_REL]) == req['native_CPU_receipt']['sha256']
    assert all(sha(d) != CONTROL_CP_SHA for d in raw.values())

    # 12. Write STAGE, manifest, receipt.
    execution.mkdir(parents=False, exist_ok=False)
    stage = execution / 'STAGE-v1'
    files = []
    for rel, data in sorted(raw.items()):
        p = stage / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('xb') as f:
            f.write(data)
        files.append({'localpath': str(p), 'path': rel, 'sha256': sha(data), 'bytes': len(data)})
    readonly = copy.deepcopy(v8['readonly_native_pins'])
    assert any(p['path'] == ORIGINAL_CP['nativepath'] and p['sha256'] == ORIGINAL_CP['sha256'] for p in readonly)
    assert all(p['sha256'] != CONTROL_CP_SHA for p in readonly)
    project = req['pc_project_root']
    manifest = {
        'schema': 'cap256.disposable-arithmetic-benchmark.root-transport.v1',
        'ssh_alias': 'benspc', 'native_root': native_root,
        'Mac_output_root': str(execution / 'BENCHMARK-MAC-EXPORT-v1'),
        'qualification_window_utc': window,
        'staged_positive_files': files, 'readonly_native_pins': readonly,
        'request_relative': REQUEST_REL, 'request_sha256': sha(raw[REQUEST_REL]),
        'driver_relative': DRIVER_REL, 'driver_sha256': sha(raw[DRIVER_REL]),
        'python_exe': req['python_exe'], 'native_relay_relative': RELAY_REL,
        'native_relay_sha256': args.relay_sha256,
        'original_checkpoint': dict(ORIGINAL_CP),
        'export_roots': ['benchmark-output-v1', 'benchmark-controller-v1'],
        'terminal_relative': req['terminal_path'],
        'old_lock_paths': [base + '/' + n for base in (project, project + '/launch-cap256')
                           for n in ('LOCK.json', 'LOCK-contextual-Windows.guard')],
    }
    manifest_path = execution / 'ROOT-TRANSPORT-MANIFEST-v1.json'
    with manifest_path.open('xb') as f:
        f.write(canonical(manifest))
    manifest_sha = sha(manifest_path.read_bytes())
    receipt = {'schema': 'premonition.disposable-benchmark-root-activation.v1',
               'variant': 'treatment-only-fresh-process-v1', 'dry_run': dry,
               'qualification_window_utc': window, 'start_by_utc': start_by, 'native_root': native_root,
               'authority_sha256': authority_sha, 'authority_thread_id': args.authority_thread_id,
               'approval_sha256': args.approval_sha256,
               'manifest_path': str(manifest_path), 'manifest_sha256': manifest_sha,
               'staged_files': len(files), 'staged_logical_bytes': sum(r['bytes'] for r in files),
               'worker_sha256': cfg['runner']['sha256'], 'driver_sha256': req['driver']['sha256'],
               'relay_sha256': args.relay_sha256, 'transport_sha256': args.transport_sha256,
               'unsubstituted_sources': {WORKER_REL: args.worker_sha256, DRIVER_REL: args.driver_sha256},
               'runner_normalized_AST_sha256': worker_ast, 'driver_normalized_AST_sha256': driver_ast,
               'config_core_sha256': config_core_sha,
               'config_sha256': req['continuation_config']['sha256'], 'request_sha256': sha(raw[REQUEST_REL]),
               'prior_control_resume': cfg['prior_control_resume'], 'original_checkpoint': manifest['original_checkpoint'],
               'normalized_AST_preserved_by_anchor_substitution': True,
               'native_writes': 0, 'model_calls': 0, 'qualification_only': False, 'authorized_optimizer_updates': 64,
               'GPU_start_claimed': False,
               'runbook': {'version': '1.2', 'sha256': '3186e016f7a83f59a5095f719f272527a793689957c9fc639d05637def31bf5d',
                           'rule': 'execution.preflight',
                           'action': 'Treatment-only fresh-process successor; preserve v8 and all prior attempts; one transfer, one driver run, one export, no retry.'}}
    with (execution / 'ROOT-ACTIVATION-RECEIPT-v1.json').open('xb') as f:
        f.write(canonical(receipt))
    for p in tmp_mods.iterdir():
        p.unlink()
    tmp_mods.rmdir()
    return execution, manifest_path, manifest_sha, receipt, failures


def run_dry_validators(execution, manifest_path, manifest_sha, receipt, failures, thread_id):
    """Every Mac-reproducible check the transport, relay, driver and worker apply."""
    results = []
    def check(label, fn):
        try:
            value = fn()
            results.append({'check': label, 'ok': True, 'detail': value})
        except Exception as error:
            results.append({'check': label, 'ok': False, 'error': '%s: %s' % (type(error).__name__, error)})
    stage = execution / 'STAGE-v1'
    m = json.loads(manifest_path.read_bytes())
    t = load_module('_dry_transport', TRANSPORT)
    check('transport --check: pin(manifest) + validate(manifest)',
          lambda: (t.pin(manifest_path, manifest_sha), t.validate(m))[1])
    check('transport: window live at seal (start <= now < deadline)',
          lambda: t.utc(m['qualification_window_utc']['start']) <= __import__('time').time() < t.utc(m['qualification_window_utc']['deadline']) or 1 / 0)
    check('transport: Mac_output_root absent, no symlinked ancestor',
          lambda: (not Path(m['Mac_output_root']).exists() and not any(p.is_symlink() for p in Path(m['Mac_output_root']).parents)) or 1 / 0)
    check('transport: Mac 2GiB resource/free floor (at execution dir)',
          lambda: t.resource(execution, sum(x['bytes'] for x in m['staged_positive_files']) + 1024 ** 2) or 'ok')
    n = load_module('_dry_relay', stage / RELAY_REL)
    check('relay: window() exact 600 live', lambda: n.window(m))
    check('relay: manifest schema/native root prefix',
          lambda: (m['schema'] == n.SCHEMA and m['native_root'].startswith(n.PROJECT + '/launch-cap256/pkg/local-arithmetic-benchmark-')) or 1 / 0)
    check('relay: every staged positive file physically pinned (Mac STAGE copies)',
          lambda: [n.pin(stage / f['path'], f['sha256'], f['bytes']) for f in m['staged_positive_files']] and len(m['staged_positive_files']))
    check('relay: driver/request/relay entrypoint pins',
          lambda: (n.pin(stage / m['driver_relative'], m['driver_sha256']), n.pin(stage / m['request_relative'], m['request_sha256']),
                   n.pin(stage / m['native_relay_relative'], m['native_relay_sha256'])) and 'ok')
    req = json.loads((stage / REQUEST_REL).read_bytes())
    check('relay: request/transport binding',
          lambda: (req['root'].replace('\\', '/') == m['native_root'] and req['driver']['sha256'] == m['driver_sha256']
                   and req['driver']['path'] == m['native_root'] + '/' + m['driver_relative'] and req['python_exe'] == m['python_exe']
                   and req['terminal_path'] == m['terminal_relative'] and req['state_namespace'] in m['export_roots']
                   and req['worker_output_namespace'] in m['export_roots']) or 1 / 0)
    rel_auth = req['authority']['path'][len(m['native_root']) + 1:]
    authority_path = stage / rel_auth
    authority = json.loads(authority_path.read_bytes())
    check('relay: authority pin + same absolute window as manifest',
          lambda: (n.pin(authority_path, req['authority']['sha256']), authority['qualification_window_utc'] == m['qualification_window_utc'] or 1 / 0) and 'ok')
    check('relay: original checkpoint record = 49a350.../60691431 -> input-copy (relay copies it; never 0818901e)',
          lambda: (m['original_checkpoint'] == ORIGINAL_CP and m['original_checkpoint']['sha256'] == n.CP_SHA
                   and n.CP_SHA != CONTROL_CP_SHA) or 1 / 0)
    check('relay: canonical global lock path listed', lambda: (n.PROJECT + '/launch-cap256/LOCK.json' in m['old_lock_paths']) or 1 / 0)
    # Driver (staged copy, anchor substituted).
    d = load_module('_dry_driver', stage / DRIVER_REL)
    w = load_module('_dry_worker', stage / WORKER_REL)
    check('driver: TRUSTED anchor == authority sha', lambda: (d.TRUSTED_EXECUTION_RELEASE_SHA256 == req['authority']['sha256'] == receipt['authority_sha256']) or 1 / 0)
    check('driver: validate_request', lambda: d.validate_request(req) or 'ok')
    check('driver: root inside project, request inside root',
          lambda: (req['root'].startswith(req['pc_project_root'] + '/') and m['request_relative'].startswith('cfg/')) or 1 / 0)
    mac_req = copy.deepcopy(req)
    for key in ('authority', 'worker_source', 'continuation_config', 'driver', 'native_CPU_receipt'):
        mac_req[key]['path'] = str(stage / req[key]['path'][len(m['native_root']) + 1:])
        check('driver: physical pin ' + key, lambda key=key: (d.sha(mac_req[key]['path']) == req[key]['sha256']) or 1 / 0)
    check('driver: authority_check (verbatim; Mac-mapped authority/worker/config paths)',
          lambda: d.authority_check(authority, mac_req) or 'ok')
    # The remaining authority_check conditions, evaluated individually so one failure does not mask the rest.
    cfg = json.loads((stage / CONFIG_REL).read_bytes())
    check('driver authority_check part: schema/approved_action/approval reference',
          lambda: (authority['schema'] == 'cap256.disposable-arithmetic-benchmark.execution-authority.v1'
                   and authority['approved_action'] == 'RUN_DISPOSABLE_LOCAL_ARITHMETIC_THROUGHPUT_ONLY'
                   and authority['approval_evidence_reference'] == APPROVAL_REL) or 1 / 0)
    check('driver authority_check part: authority_thread_id equals driver literal',
          lambda: (authority['authority_thread_id'] == thread_literals((stage / DRIVER_REL).read_text(), 'authority_check')[0]) or 1 / 0)
    check('driver authority_check part: driver_envelope in authority', lambda: (d.driver_envelope(req) in authority['driver_envelopes']) or 1 / 0)
    check('driver authority_check part: driver normalized AST', lambda: (d.normalized_source_sha256((stage / DRIVER_REL).read_text()) == authority['driver_normalized_AST_sha256']) or 1 / 0)
    check('driver authority_check part: worker normalized AST', lambda: (d.normalized_source_sha256((stage / WORKER_REL).read_text()) == authority['runner_normalized_AST_sha256']) or 1 / 0)
    check('driver authority_check part: config core/endpoint/budgets',
          lambda: (hashlib.sha256(w.canonical(w.config_core(cfg))).hexdigest() in authority['config_core_sha256s']
                   and cfg['endpoint_index'] == req['endpoint_index'] == 1 and cfg['budget']['worker_seconds'] == d.WORKER_SECONDS == 400
                   and req['driver_budget']['whole_job_seconds'] == d.WHOLE_JOB_SECONDS == 600
                   and req['driver_budget']['closure_seconds'] == d.CLOSURE_SECONDS == 180
                   and cfg['budget']['worker_seconds'] + req['driver_budget']['closure_seconds'] <= req['driver_budget']['whole_job_seconds']
                   and cfg['budget']['new_output_bytes'] + req['driver_budget']['controller_reserve_bytes'] <= req['driver_budget']['whole_output_bytes']) or 1 / 0)
    check('driver authority_check part: worker.qualification_window live 600', lambda: str(w.qualification_window(authority)))
    check('driver: start_by = start + 240 and not yet passed',
          lambda: ((datetime.datetime.fromisoformat(authority['start_by_utc']) - datetime.datetime.fromisoformat(authority['qualification_window_utc']['start'])).total_seconds() == 240
                   and datetime.datetime.now(datetime.timezone.utc) <= datetime.datetime.fromisoformat(authority['start_by_utc'])) or 1 / 0)
    check('driver: cfg.output_namespace == worker_output_namespace', lambda: (cfg['output_namespace'] == req['worker_output_namespace']) or 1 / 0)
    receipt_body = json.loads((stage / NATIVE_RECEIPT_REL).read_bytes())
    def native_cpu():
        bridge = authority['native_CPU_proof_bridge']
        assert set(bridge) == {'receipt', 'producer_driver'} and bridge['receipt'] == req['native_CPU_receipt']
        assert d.sha(PRODUCER_LOCAL) == bridge['producer_driver']['sha256'], 'local producer copy differs'
        assert d.sha(stage / NATIVE_RECEIPT_REL) == bridge['receipt']['sha256']
        expected = {k: req[k] for k in ('runtime_adapter', 'python_exe', 'ownership_runtime')}
        expected['driver'] = bridge['producer_driver']
        assert receipt_body.get('pins') == expected, 'receipt pins differ'
        for key, value in {'schema': 'cap256.TRAIN-continuation-native-CPU-proof-receipt.v1', 'status': 'PASSED',
                           'global_lock_preserved': False, 'no_GPU_calls': True, 'no_Torch_or_model_calls': True,
                           'optimizer_updates': 0, 'native_generation_calls': 0}.items():
            assert receipt_body.get(key) == value, key
        assert 0 <= receipt_body['wall_seconds'] <= 20
        def proc(src):
            tree = ast.parse(src)
            return ([ast.dump(x, include_attributes=False) for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'native_cpu_proof'],
                    [ast.dump(x.value, include_attributes=False) for x in tree.body if isinstance(x, ast.Assign)
                     and any(isinstance(t_, ast.Name) and t_.id == 'CPU_CHILD' for t_ in x.targets)])
        assert proc(PRODUCER_LOCAL.read_text()) == proc((stage / DRIVER_REL).read_text()), 'native_cpu_proof/CPU_CHILD changed'
        for name in ('stop', 'normal_exit'):
            p = receipt_body.get(name, {})
            assert p.get('actual_child_exit_confirmed') is True and p.get('launcher_exit_confirmed') is True and p.get('original_handles_retained') is True
        return 'ok'
    check('driver: validate_native_cpu_receipt conditions (Mac-mapped producer/receipt)', native_cpu)
    check('driver: prepare_benchmark_queue_job wall 600 (fixture authorization pin)',
          lambda: _queue_job(d, stage, m))
    # Worker (staged copy, anchor substituted), STAGE as root.
    check('worker: TRUSTED anchor == authority sha', lambda: (w.TRUSTED_EXECUTION_RELEASE_SHA256 == receipt['authority_sha256']) or 1 / 0)
    check('worker: execution_authority(root=STAGE) verbatim', lambda: bool(w.execution_authority(stage, cfg, stage / WORKER_REL)))
    check('worker: runner physical pin + AST', lambda: (w.pin(stage, cfg['runner']).resolve() == (stage / WORKER_REL).resolve()
                                                        and cfg['runner_normalized_AST_sha256'] == w.normalized_source_sha256((stage / WORKER_REL).read_text())) or 1 / 0)
    check('worker: prior_control_resume pin + validate_prior_control_resume',
          lambda: (cfg['prior_control_resume'] == {'path': PRIOR_REL, 'sha256': PRIOR_SHA, 'bytes': PRIOR_BYTES}
                   and bool(w.validate_prior_control_resume(w.read_pin(stage, cfg['prior_control_resume'])))) or 1 / 0)
    def preflight():
        seen = []
        real = w.pin
        def spy(root, record):
            seen.append(record['path'])
            return real(root, record)
        try:
            with patch.object(w, 'execution_authority', return_value=authority), \
                    patch.object(w, 'benchmark_rows', side_effect=w.checked_benchmark_rows_unmarked), \
                    patch.object(w, 'pin', side_effect=spy):
                w.cpu_preflight(stage, cfg, stage / WORKER_REL)
        except ValueError as error:
            if seen and seen[-1] == ORIGINAL_CP['destination'] and 'ordinary nonsymlink file required' in str(error):
                return 'all checks pass up to the native-only input copy (%s, created by the relay on the PC); pins read: %d' % (seen[-1], len(seen))
            raise
        return 'completed'
    check('worker: cpu_preflight on STAGE (execution_authority checked separately above; stops at native-only input copy)', preflight)
    return results


def _queue_job(d, stage, m):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        auth = Path(tmp) / 'auth.json'
        req = json.loads((stage / REQUEST_REL).read_bytes())
        auth.write_text(json.dumps({'job_id': req['job_id'], 'authorized': False}))
        job = d.prepare_benchmark_queue_job({'path': str(stage / REQUEST_REL), 'sha256': m['request_sha256']},
                                            {'path': str(auth), 'sha256': d.sha(auth)})
        assert [a['wall_cap_seconds'] for a in job['attempts']] == [600]
        return 'wall_cap_seconds=600'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worker-sha256', required=True)
    ap.add_argument('--driver-sha256', required=True)
    ap.add_argument('--relay-sha256', required=True)
    ap.add_argument('--transport-sha256', required=True)
    ap.add_argument('--approval-sha256', required=True)
    ap.add_argument('--approval-path')
    ap.add_argument('--authority-thread-id', required=True)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    execution, manifest_path, manifest_sha, receipt, failures = build(args)
    if not args.dry_run:
        print(json.dumps(receipt))
        return 0
    results = run_dry_validators(execution, manifest_path, manifest_sha, receipt, failures, args.authority_thread_id)
    report = {'dry_run': True, 'execution': str(execution), 'manifest_sha256': manifest_sha,
              'seal_gate_failures': failures, 'validators': results,
              'passed': sum(r['ok'] for r in results), 'failed': sum(not r['ok'] for r in results)}
    with (execution / 'DRY-RUN-VALIDATION-REPORT.json').open('xb') as f:
        f.write(canonical(report))
    print(json.dumps(report, indent=1))
    return 0 if not failures and report['failed'] == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
