"""Inference-only calculator evaluation resume; original frozen TRAIN20 gate/fresh32.

The queue starts this driver with --request only and never kills it. This
driver owns each direct base-Python worker handle and its hard wall cap.
--check is file/CPU preparation only; it neither probes the PC nor dispatches.
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
import site
import subprocess
import sys
import threading
import time

MIB = 1024 ** 2
NATIVE_LIMIT = 52
LOG_CAP = MIB
REQUIRED_LAUNCHERS = ('calculator_eval_resume_pc_driver.py', 'pc_driver.py', 'pc_guard.py',
                      'receipt_io.py', 'recovery_guide.py')
READINESS = ('corpus_frozen', 'source_state_verified',
             'throughput_budget_verified', 'live_driver_verified')
PROTECTED = ('uncle-questions', 'readpanel320', '/blind/', 'sealed-panels',
             'sealedquestions', 'sealed-user', 'sealeduser', 'sealed-blind',
             'dev100', 'stop88', 'reserved-pool')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(MIB), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def safe(root, relative):
    root = Path(root).resolve()
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('root-relative path required')
    result = (root / path).resolve()
    text = '/' + str(result).replace('\\', '/').lower().strip('/') + '/'
    if not result.is_relative_to(root) or any(mark in text for mark in PROTECTED):
        raise ValueError('protected or out-of-root path refused before access')
    return result


def pin(root, value):
    if (type(value) is not dict or set(value) != {'path', 'sha256'}
            or not re.fullmatch('[0-9a-f]{64}', value.get('sha256', ''))):
        raise ValueError('exact path/SHA256 pin required')
    path = safe(root, value['path'])
    if sha(path) != value['sha256']:
        raise ValueError('pinned bytes differ: ' + value['path'])
    return path


def validate_config(cfg):
    if cfg.get('schema') != 'cap256.calculator-poc.v1' or cfg.get('seeds') != [0, 1]:
        raise ValueError('original two-seed calculator config required')
    if cfg.get('additional_updates') != 1024 or cfg.get('budget', {}).get('evaluation_seconds') != 180:
        raise ValueError('original calculator1024/evaluation180 protocol required')
    if cfg.get('budget', {}).get('spend_usd') != 0:
        raise ValueError('zero spend original config required')


def validate_request_policy(request, cfg):
    required = {'wall_seconds': 180, 'new_output_bytes': 32 * MIB,
        'project_cap_bytes': 100000000000, 'retained_free_bytes': 2147483648, 'spend_usd': 0}
    if request.get('resume_budget') != required or any(type(request['resume_budget'][k]) is not int for k in required):
        raise ValueError('exact independently authorized inference-only resume caps required')
    if not isinstance(request.get('output_accounting_extra_paths'), list):
        raise ValueError('new resume output accounting paths required')
    if (request.get('checkpoint_write_allowed', False) is not False
            or type(request.get('optimizer_updates', 0)) is not int or request.get('optimizer_updates', 0) != 0):
        raise ValueError('resume cannot train or write checkpoints')


def readiness_issues(cfg):
    return [key + ' is not true; preparation only' for key in
            ('dispatch_allowed', 'exclusive_lock_verified') if cfg.get(key) is not True]


def endpoint_list(root, endpoints, arm, config_hash, cfg):
    if [(e.get('seed'), e.get('arm')) for e in endpoints] != [(0, arm), (1, arm)]:
        raise ValueError('exact serial endpoint identities required')
    for endpoint in endpoints:
        closed = read(pin(root, endpoint['closed']))
        checkpoint = pin(root, endpoint['checkpoint'])
        source = next(e for e in cfg['sources'] if e['seed'] == endpoint['seed'])
        if (closed.get('closed') is not True or closed.get('config_sha256') != config_hash
                or closed.get('seed') != endpoint['seed'] or closed.get('arm') != arm
                or closed.get('checkpoint') != endpoint['checkpoint']
                or closed.get('optimizer_updates') != 11264 or closed.get('additional_optimizer_updates') != 1024
                or closed.get('runtime_sha256') != cfg['runtime_module']['sha256']
                or closed.get('architecture_contract_sha256') != cfg['architecture_contract']['sha256']
                or closed.get('source_checkpoint_sha256') != source['checkpoint']['sha256']
                or closed.get('durable_model_and_Adam_reload_equal') is not True
                or checkpoint.stat().st_size > cfg['budget']['checkpoint_cap_bytes']):
            raise ValueError('actual immutable calculator endpoint closure differs')
    return endpoints


def native_closure(root, cfg, config_hash, packet_hash):
    out = safe(root, cfg.get('evaluation_output_namespace', cfg['output_namespace'] + '/native-evaluation'))
    path = out / 'CLOSED.json'; closed = read(path)
    gate = closed.get('fit_gate_passed')
    train = closed.get('TRAIN_results')
    if (type(train) is not list or len(train) != 2 or [r.get('seed') for r in train] != [0, 1]
            or any(type(r.get('rows')) is not int or r['rows'] != 10
                   or type(r.get('combined_correct')) is not int or not 0 <= r['combined_correct'] <= 10 for r in train)
            or gate is not all(r['combined_correct'] == 10 for r in train)):
        raise ValueError('calculator fresh gate must match both strict TRAIN10 results')
    calls, fresh = (52, 32) if gate is True else (20, 0)
    if (type(gate) is not bool or closed.get('fit_gate_passed') != gate
            or closed.get('closed') is not True or closed.get('config_sha256') != config_hash
            or closed.get('endpoints_sha256') != packet_hash
            or closed.get('protocol_sha256') != cfg['evaluation_protocol']['sha256']
            or type(closed.get('native_calls')) is not int or closed.get('native_calls') != calls
            or type(closed.get('fresh_native_calls')) is not int or closed.get('fresh_native_calls') != fresh
            or closed.get('optimizer_updates') != 0
            or type(closed.get('optimizer_updates')) is not int
            or type(closed.get('teacherforced_examples')) is not int or closed.get('teacherforced_examples') != 0
            or type(closed.get('requested_tool_calls')) is not int or not 0 <= closed['requested_tool_calls'] <= 4 * calls
            or closed.get('fresh_frame_file_accessed') is not gate
            or closed.get('raw_frozen_before_scoring') is not True
            or closed.get('endpoint_weights_and_checkpoint_bytes_unchanged') is not True
            or closed.get('LM_unchanged') is not True):
        raise ValueError('native closure branch/provenance/counters differ')
    for name, expected in closed.get('file_sha256', {}).items():
        if Path(name).name != name or sha(out / name) != expected:
            raise ValueError('native saved raw/scored file differs')
    for phase, count, first in [('TRAIN', 20, 1)] + ([('FRESH', 32, 21)] if gate else []):
        records = [json.loads(line) for line in (out / (phase + '-OBSERVATIONS.jsonl')).read_bytes().splitlines()]
        if len(records) != count or [r.get('call_index') for r in records] != list(range(first, first + count)):
            raise ValueError('durable native call sequence differs')
    if not gate and any(out.glob('FRESH-*')):
        raise ValueError('failed calculator gate must leave fresh unused')
    return closed, {'path': str(path.relative_to(root)), 'sha256': sha(path)}


def unique_roots(paths):
    result = []
    for path in sorted(set(map(lambda p: Path(p).resolve(), paths)), key=lambda p: len(p.parts)):
        if not any(path == other or path.is_relative_to(other) for other in result):
            result.append(path)
    return result


def stop_owned(process):
    """Only the Popen handle we created; an unknown exit never releases LOCK."""
    result = {'runner_pid': process.pid, 'exit_confirmed': False}
    try:
        if process.poll() is None:
            process.kill()
            result['kill_requested'] = True
        process.wait(timeout=10)
        result['exit_confirmed'] = process.poll() is not None
        result['returncode'] = process.returncode
    except Exception as error:
        result['stop_error'] = repr(error)
        try:
            result['exit_confirmed'] = process.poll() is not None
        except Exception:
            pass
    return result


class OwnedWorker:
    """Direct worker handle with bounded stdout/stderr, without a shell."""
    def __init__(self, argv, directory, root, env, guard):
        guard(2 * LOG_CAP + 2 * 65536)
        self.errors, self.threads = [], []
        self.process = subprocess.Popen(argv, cwd=str(root), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
        self.pid = self.process.pid
        self.directory = Path(directory)
        self._guard_lock = threading.Lock()
        for label in ('stdout', 'stderr'):
            source = getattr(self.process, label)
            target = self.directory / ('runner-' + label + '.log')
            thread = threading.Thread(target=self._copy, args=(source, target, guard), daemon=True)
            thread.start()
            self.threads.append(thread)

    def _copy(self, source, target, guard):
        count = 0
        try:
            with target.open('xb') as stream:
                while True:
                    data = source.read(16384)
                    if not data:
                        break
                    if count + len(data) > LOG_CAP:
                        raise RuntimeError('owned worker log exceeds 1 MiB cap')
                    with self._guard_lock:
                        guard(len(data) + 65536)
                        stream.write(data)
                        stream.flush()
                    count += len(data)
                os.fsync(stream.fileno())
        except Exception as error:
            self.errors.append(repr(error))
        finally:
            source.close()

    def poll(self):
        return self.process.poll()

    def finish_logs(self):
        for thread in self.threads:
            thread.join(timeout=2)
        if any(thread.is_alive() for thread in self.threads):
            raise RuntimeError('owned worker log completion unconfirmed')
        if self.errors:
            raise RuntimeError('owned worker log failure: ' + '; '.join(self.errors))


def execute(request_path, *, check=False, driver_factory=None, worker_factory=OwnedWorker,
            clock=time.monotonic, sleeper=time.sleep):
    started = clock()
    request_path = Path(request_path).resolve()
    request_hash = sha(request_path)
    request = read(request_path)
    root, pkg = Path(request['root']).resolve(), Path(request['pkg']).resolve()
    if not request_path.is_relative_to(root) or not pkg.is_relative_to(root):
        raise ValueError('request/package must be inside the exact project root')
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*', request['batch_id']):
        raise ValueError('literal safe batch identity required')
    launcher_hashes = request['launcher_sha256']
    if any(name not in launcher_hashes for name in REQUIRED_LAUNCHERS):
        raise ValueError('driver/guard/receipt/recovery script pins required')
    for name, expected in launcher_hashes.items():
        if Path(name).name != name or sha(pkg / name) != expected:
            raise ValueError('launcher package differs: ' + name)
    if (Path(__file__).resolve() != pkg / 'calculator_eval_resume_pc_driver.py'
            or sha(__file__) != launcher_hashes['calculator_eval_resume_pc_driver.py']):
        raise ValueError('executing driver is not the immutable package pin')
    sys.path.insert(0, str(pkg))
    modules = {name: importlib.import_module(name) for name in
               ('pc_guard', 'receipt_io', 'recovery_guide', 'pc_driver')}
    for name, module in modules.items():
        if Path(module.__file__).resolve() != pkg / (name + '.py'):
            raise ValueError('cached launcher module is outside pinned package: ' + name)
    dmod, receipt, guide = modules['pc_driver'], modules['receipt_io'], modules['recovery_guide']
    if modules['pc_guard'].DRIVER_MARK != 'pc_driver.py':
        raise ValueError('exclusive PC guard contract differs')
    guide_start = guide.require_start(root, request)
    cfg_path = pin(root, request['config'])
    cfg, config_hash = read(cfg_path), request['config']['sha256']
    validate_config(cfg)
    validate_request_policy(request, cfg)
    packet_path = pin(root, request['endpoints']); packet_hash = request['endpoints']['sha256']
    packet = read(packet_path)
    if (packet.get('train_config_sha256') != config_hash or packet.get('protocol_sha256') != cfg['evaluation_protocol']['sha256']):
        raise ValueError('saved endpoint packet does not bind original config/protocol')
    endpoints = endpoint_list(root, packet['endpoints'], 'calculator', config_hash, cfg)
    pin(root, cfg['evaluation_protocol'])
    pin(root, cfg['evaluation_runner'])
    issues = readiness_issues(cfg)
    proposed_output = safe(root, cfg.get('evaluation_output_namespace', cfg['output_namespace'] + '/native-evaluation'))
    if not proposed_output.is_relative_to(safe(root, cfg['output_namespace'])):
        issues.append('evaluation output is outside original matrix')
    if proposed_output.exists() or proposed_output.is_symlink():
        issues.append('original evaluation namespace already exists; preserve it, no resume')
    if check:
        print(json.dumps({'status': 'PREPARED-BLOCKED' if issues else 'CPU-STRUCTURE-PASSED',
            'issues': issues, 'request_sha256': request_hash, 'config_sha256': config_hash,
            'live_execution_validated': False, 'model_calls': 0, 'optimizer_updates': 0}), flush=True)
        return 0
    if issues:
        raise ValueError('; '.join(issues))
    runner_pin = cfg['evaluation_runner']
    runner = pin(root, runner_pin)
    storage_path = pin(root, cfg['storage_snapshot'])
    storage_spec = importlib.util.spec_from_file_location('_calculator_resume_driver_storage', storage_path)
    storage = importlib.util.module_from_spec(storage_spec)
    storage_spec.loader.exec_module(storage)
    dmod.write_json = receipt.write_json
    d = (driver_factory or dmod.Driver)(request)
    batch = (d.state / 'mixtures' / request['batch_id']).resolve()
    matrix = safe(root, cfg.get('evaluation_output_namespace', cfg['output_namespace'] + '/native-evaluation'))
    terminal = Path(request.get('terminal_path', batch / 'TERMINAL.json')).resolve()
    if not terminal.is_relative_to(root):
        raise ValueError('queue terminal receipt is outside project root')
    roots = unique_roots([matrix, batch, terminal,
        pkg, request_path, *[safe(root, p) for p in request['output_accounting_extra_paths']]])
    unit = storage.filesystem_allocation_unit(root)
    budget = request['resume_budget']
    worker, locked = None, False
    native_calls, fresh_calls = 0, 0
    template_path, template_hash = cfg_path, config_hash
    evaluation_pin = None
    protocol_path = pin(root, cfg['evaluation_protocol'])
    state = {'batch_id': request['batch_id'], 'commit': request['commit'],
        'queued_utc': request['queued_utc'], 'driver_pid': os.getpid(),
        'driver_started_utc': dmod.iso(), 'request_sha256': request_hash,
        'config_sha256': config_hash, 'status': 'preflight', 'phase': 'native_evaluation',
        'jobs': [], 'live_execution_validated': False, 'reserved_calls_allowed': False,
        'accounting_complete': False, 'teacherforced_examples': 0,
        'evaluation_performed': False, 'fresh_evaluation_performed': False, 'fresh_examples_used': 0}

    def accounting():
        return {'schema': 'cap256.calculator-evaluation-resume-output-accounting.v1', 'allocation_unit_bytes': unit,
            'output_roots': [str(p) for p in roots],
            'new_output_allocated_bytes': sum(storage.allocated_bytes(p, unit) for p in roots),
            'project_allocated_bytes': storage.allocated_bytes(root, unit),
            'free_bytes': shutil.disk_usage(root).free, 'config_sha256': template_hash,
            'execution_config_sha256': config_hash,
            'request_sha256': request_hash, 'live_execution_validated': False}

    def guard(extra=0):
        snapshot = accounting()
        if (snapshot['new_output_allocated_bytes'] + extra > budget['new_output_bytes']
                or snapshot['project_allocated_bytes'] + extra > budget['project_cap_bytes']
                or snapshot['free_bytes'] - extra < budget['retained_free_bytes']):
            raise RuntimeError('calculator evaluation resume output/project/free resource cap exceeded')
        return snapshot

    def write(path, value, exclusive=False):
        data = (json.dumps(value, sort_keys=True, indent=2, default=str, allow_nan=False) + '\n').encode()
        guard(len(data) + unit)
        return receipt.write_json(path, value, exclusive=exclusive)

    def save():
        write(batch / 'BATCH.json', state)

    def immutable_request():
        if clock() - started >= budget['wall_seconds']:
            raise RuntimeError('entire calculator evaluation resume job hard180-second cap exhausted')
        if (sha(request_path) != request_hash or sha(cfg_path) != config_hash
                or sha(template_path) != template_hash or sha(packet_path) != packet_hash):
            raise ValueError('immutable request/config changed after preflight')
        for path, expected in ((runner, runner_pin['sha256']),):
            if sha(path) != expected:
                raise ValueError('immutable worker changed before launch')

    def argv_base():
        return [getattr(sys, '_base_executable', sys.executable), '-X', 'utf8', '-B']

    def run_worker(argv, job, directory, cap):
        nonlocal worker
        immutable_request()
        if not d.guard(directory)['ok']:
            raise RuntimeError('exclusive ownership/GPU guard refused')
        immutable_request()
        cap = min(cap, budget['wall_seconds'] - (clock() - started))
        if cap <= 0:
            raise RuntimeError('no remaining calculator evaluation resume job wall time')
        write(directory / 'RUNNER-ARGV.json', {'argv': argv, 'job': job}, True)
        env = dict(os.environ, JOB=job, TREE=str(root), PYTHONUNBUFFERED='1',
            PYTHONPATH=os.pathsep.join(site.getsitepackages()), PYTHONDONTWRITEBYTECODE='1',
            HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        worker_start = clock()
        worker = worker_factory(argv, directory, root, env, guard)
        js = {'job_id': job, 'phase': 'native_evaluation',
            'runner_pid': worker.pid, 'runner_started_utc': dmod.iso(),
            'status': 'runner_started', 'native_calls_observed': 0}
        state['jobs'].append(js)
        cap_fired = threading.Event()
        owned = worker
        def hard_stop():
            cap_fired.set()
            js['cap_exceeded'] = True
            try:
                if owned.process.poll() is None:
                    owned.process.kill()  # Exact direct worker handle, never a PID lookup.
            except Exception as error:
                js['hard_cap_kill_error'] = repr(error)
        watchdog = threading.Timer(max(0, cap - (clock() - worker_start)), hard_stop)
        watchdog.daemon = True
        watchdog.start()
        count, last_progress = 0, -30
        try:
            save()
            while True:
                rc = worker.poll()
                if cap_fired.is_set():
                    raise RuntimeError('exact owned worker watchdog wall cap exceeded')
                elapsed = clock() - worker_start
                count = 0
                for phase in ('TRAIN', 'FRESH'):
                    raw = matrix / (phase + '-OBSERVATIONS.jsonl')
                    if raw.is_file():
                        data = raw.read_bytes()
                        count += len(data[:data.rfind(b'\n') + 1].splitlines()) if b'\n' in data else 0
                if count > NATIVE_LIMIT:
                    raise ValueError('native call observation limit exceeded')
                js['native_calls_observed'] = count
                if elapsed - last_progress >= 10 or rc is not None:
                    guard()
                    js.update(status='native_evaluation', runner_wall_seconds=elapsed)
                    write(directory / 'PROGRESS.json', {**js, 'utc': dmod.iso(), 'runner_returncode': rc})
                    save()
                    last_progress = elapsed
                if rc is not None:
                    worker.finish_logs()
                    js.update(returncode=rc, runner_ended_utc=dmod.iso(), runner_wall_seconds=elapsed,
                              status='completed' if rc == 0 else 'failed')
                    write(directory / 'EXIT.json', js, True)
                    save()
                    if elapsed > cap or clock() - started > budget['wall_seconds']:
                        raise RuntimeError('owned worker completed outside hard wall cap')
                    return rc, count
                if elapsed >= cap or clock() - started >= budget['wall_seconds']:
                    js['cap_exceeded'] = True
                    raise RuntimeError('exact owned runner hard wall cap exceeded')
                if getattr(worker, 'errors', []):
                    raise RuntimeError('owned worker bounded log capture failed')
                sleeper(min(1, max(0, cap - elapsed)))
        finally:
            watchdog.cancel()

    try:
        if d.lock.exists() or d.lock.is_symlink():
            raise RuntimeError('existing exclusive lock; preserve it and do not queue behind')
        if matrix.exists() or matrix.is_symlink() or terminal.exists():
            raise RuntimeError('prior calculator evaluation resume output/terminal exists; no duplicate run')
        guard(16 * MIB)
        batch.mkdir(parents=True, exist_ok=False)
        write(batch / 'GUIDE-START.json', guide_start, True)
        save()
        # No stale-PID takeover: an unconfirmed prior owner must remain blocked.
        write(d.lock, {'pid': os.getpid(), 'batch_id': request['batch_id'], 'utc': dmod.iso(),
                      'request_sha256': request_hash, 'driver': 'calculator_eval_resume_pc_driver.py'}, True)
        locked = True
        # Reuse the exact saved endpoints and original config; derive nothing.
        endpoint_list(root, endpoints, 'calculator', config_hash, cfg)
        state.update(status='running', config_sha256=config_hash,
            endpoint_packet_sha256=packet_hash, protocol_sha256=cfg['evaluation_protocol']['sha256'],
            calculator_endpoints=endpoints, checkpoint_write_allowed=False,
            training_updates_allowed=False)
        save()
        job = 'calculator-native-resume-%s' % request['batch_id']
        directory = batch / job; directory.mkdir()
        argv = argv_base() + [str(runner), '--root', str(root), '--config', str(cfg_path),
            '--config-sha256', config_hash, '--endpoints', str(packet_path), '--endpoints-sha256', packet_hash]
        rc, observed = run_worker(argv, job, directory, budget['wall_seconds'])
        if rc != 0:
            raise RuntimeError('calculator evaluation resume evaluator returned non-success')
        closed, evaluation_pin = native_closure(root, cfg, config_hash, packet_hash)
        endpoint_list(root, endpoints, 'calculator', config_hash, cfg)
        native_calls, fresh_calls = closed['native_calls'], closed['fresh_native_calls']
        if observed != native_calls:
            raise ValueError('native raw count differs from immutable closure')
        immutable_request()
        state.update(status='completed', phase='completed', accounting_complete=True,
            evaluation_closed=evaluation_pin, native_calls=native_calls,
            evaluation_performed=True, fresh_evaluation_performed=bool(fresh_calls),
            fresh_examples_used=fresh_calls, fit_gate_passed=closed['fit_gate_passed'],
            calculator_fit_gate_passed=closed['fit_gate_passed'],
            fresh_status=closed['fresh_status'], total_optimizer_updates=0)
    except Exception as error:
        state.update(status='failed', error_type=type(error).__name__, error=str(error))
        if worker is not None and worker.poll() is None:
            stopped = stop_owned(worker.process)
            state['owned_runner_stop'] = stopped
            if not stopped['exit_confirmed']:
                state['status'] = 'owned_runner_exit_unconfirmed_lock_preserved'
            else:
                try:
                    worker.finish_logs()
                except Exception as log_error:
                    state['log_completion_error'] = repr(log_error)
        try:
            state['guide_failure_consultation'] = guide.consult_failure(root, request['batch_id'], error,
                'Stop only the exact owned worker; preserve raw/checkpoints/logs and the lock when exit is unconfirmed. No automatic scientific retry or resource expansion.')
        except Exception as guide_error:
            state['guide_consultation_error'] = repr(guide_error)
        state['recovery'] = {'automatic_retry_allowed': False, 'reserved_calls_allowed': False,
            'evidence_preserved': True, 'live_execution_validated': False,
            'calculator_endpoints_verified': endpoints, 'training_updates_allowed': False}
    finally:
        if locked and (worker is None or worker.poll() is not None):
            holder = receipt.read_json(d.lock)
            if holder.get('pid') == os.getpid() and holder.get('request_sha256') == request_hash:
                os.replace(d.lock, batch / 'LOCK.released.json')
                locked = False
        state.update(driver_ended_utc=dmod.iso(), wall_seconds=clock() - started,
            optimizer_updates=0,
            native_calls=native_calls if state['accounting_complete'] else None,
            model_calls=native_calls if state['accounting_complete'] else None,
            native_calls_observed_lower_bound=max([0] + [j.get('native_calls_observed', 0) for j in state['jobs']]),
            exclusive_lock_preserved=locked)
        if state['status'] == 'completed' and state['wall_seconds'] > budget['wall_seconds']:
            state.update(status='failed', error='calculator evaluation resume job exceeded total wall cap', accounting_complete=False)
        if worker is None:
            state['accounting_complete'] = True
            state.update(native_calls=0, model_calls=0)
        if batch.exists():
            try:
                save()
            except Exception as receipt_error:
                state['terminal_receipt_error'] = repr(receipt_error)
                receipt.write_terminal_failure(batch / 'BATCH.json', state)
            if state['status'] != 'owned_runner_exit_unconfirmed_lock_preserved':
                completion_path = batch / 'COMPLETION.json'
                accounting_path = batch / 'OUTPUT-ACCOUNTING.json'
                write(completion_path, {**state, 'terminal': True}, True)
                # Reserve the accounting/terminal allocation before measuring the
                # final retained total. No reader-facing receipt invents free space.
                guard(2 * MIB + 2 * unit)
                census = accounting()
                accounting_base = census['new_output_allocated_bytes']
                census['accounting_complete'] = state['accounting_complete']
                census['accounting_path'] = str(accounting_path)
                # Include this immutable census file in its own allocation total.
                # Its content hash belongs in the terminal, avoiding hash cycles.
                for _ in range(8):
                    size = len((json.dumps(census, sort_keys=True, indent=2, default=str,
                        allow_nan=False) + '\n').encode())
                    own = ((size + unit - 1) // unit) * unit
                    total = accounting_base + own
                    if census.get('new_output_allocated_bytes') == total:
                        break
                    census['new_output_allocated_bytes'] = total
                else:
                    raise RuntimeError('output-accounting self-size did not stabilize')
                write(accounting_path, census, True)
                if accounting()['new_output_allocated_bytes'] != census['new_output_allocated_bytes']:
                    raise RuntimeError('immutable output-accounting census differs after save')
                evidence = [{'kind': 'completion', 'path': str(completion_path), 'sha256': sha(completion_path)},
                    {'kind': 'config', 'path': str(template_path), 'sha256': template_hash},
                    {'kind': 'execution_config', 'path': str(cfg_path), 'sha256': config_hash},
                    {'kind': 'accounting', 'path': str(accounting_path), 'sha256': sha(accounting_path)}]
                evidence.append({'kind': 'request_config', 'path': str(template_path), 'sha256': template_hash})
                if evaluation_pin is not None:
                    evidence.append({'kind': 'evaluation', 'path': str(safe(root, evaluation_pin['path'])),
                                     'sha256': evaluation_pin['sha256']})
                if packet_path is not None:
                    evidence.append({'kind': 'endpoints', 'path': str(packet_path), 'sha256': packet_hash})
                    evidence.append({'kind': 'protocol', 'path': str(protocol_path), 'sha256': sha(protocol_path)})
                terminal_record = {'job_id': request.get('job_id', request['batch_id']),
                    'attempt_id': request['batch_id'], 'terminal': True,
                    'status': 'completed' if state['status'] == 'completed' else 'failed',
                    'phase': state['phase'], 'wall_seconds': clock() - started,
                    'output_bytes': accounting()['new_output_allocated_bytes'],
                    'model_calls': native_calls, 'native_calls': native_calls,
                    'optimizer_updates': state['optimizer_updates'],
                    'accounting_complete': state['accounting_complete'],
                    'optimizer_updates_exact': state['accounting_complete'],
                    'proven_zero_work': False, 'worker_started': worker is not None, 'retry_authorized': False,
                    'request_sha256': request_hash, 'config_sha256': template_hash,
                    'execution_config_sha256': config_hash,
                    'output_includes_terminal_receipt': True,
                    'evaluation_performed': state['evaluation_performed'],
                    'fresh_evaluation_performed': state['fresh_evaluation_performed'],
                    'fit_gate_passed': state.get('fit_gate_passed'),
                    'calculator_fit_gate_passed': state.get('calculator_fit_gate_passed'),
                    'fresh_native_calls': fresh_calls, 'teacherforced_examples': 0,
                    'live_execution_validated': False, 'evidence': evidence}
                if state['accounting_complete']:
                    for _ in range(8):
                        size = len((json.dumps(terminal_record, sort_keys=True, indent=2,
                            default=str, allow_nan=False) + '\n').encode())
                        total = census['new_output_allocated_bytes'] + ((size + unit - 1) // unit) * unit
                        if terminal_record['output_bytes'] == total:
                            break
                        terminal_record['output_bytes'] = total
                    else:
                        raise RuntimeError('terminal receipt allocation did not stabilize')
                    write(terminal, terminal_record, True)
                    if accounting()['new_output_allocated_bytes'] != terminal_record['output_bytes']:
                        raise RuntimeError('terminal output allocation differs after save')
                else:
                    write(batch / 'ACCOUNTING-UNCONFIRMED.json', {
                        'accounting_complete': False, 'queue_successors_blocked': True,
                        'known_counters_are_lower_bounds': True,
                        'training_model_calls': 0,
                        'native_calls_observed_lower_bound': max([0] + [j.get('native_calls_observed', 0) for j in state['jobs']]),
                        'optimizer_updates_observed': state['optimizer_updates'],
                        'evidence': evidence}, True)
    return 0 if state['status'] == 'completed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raise SystemExit(execute(args.request, check=args.check))
