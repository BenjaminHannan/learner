"""Prepared final-only calculator prototype under one 900-second job cap.

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
UPDATES = 1024
NATIVE_CALLS = 52
LOG_CAP = MIB
REQUIRED_LAUNCHERS = ('calculator_pc_driver.py', 'pc_driver.py', 'pc_guard.py',
                      'receipt_io.py', 'recovery_guide.py')
READINESS = ('corpus_frozen', 'fresh_evaluation_frozen',
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
    if (cfg.get('seeds') != [0, 1] or cfg.get('arm') != 'calculator'
            or cfg.get('additional_updates') != UPDATES
            or cfg.get('execution_order') != [[0, 'calculator'], [1, 'calculator']]
            or cfg.get('resume_sources')):
        raise ValueError('two fresh serial focused seeds required')
    budget = cfg.get('budget', {})
    maxima = {'worker_seconds': 900, 'total_job_seconds': 900,
              'matrix_cap_bytes': 256 * MIB, 'pair_cap_bytes': 128 * MIB,
              'checkpoint_cap_bytes': 128 * MIB, 'project_cap_bytes': 100000000000}
    for key, maximum in maxima.items():
        if type(budget.get(key)) is not int or not 0 < budget[key] <= maximum:
            raise ValueError('calculator resource cap differs: ' + key)
    if type(budget.get('retained_free_bytes')) is not int or budget['retained_free_bytes'] < 1024 ** 3:
        raise ValueError('at least 1 GiB free reserve required')
    evaluation_seconds = budget.get('evaluation_seconds', 600)
    if type(evaluation_seconds) is not int or not 0 < evaluation_seconds <= 600:
        raise ValueError('native evaluation hard cap exceeds 600 seconds')
    if cfg.get('runner') is not None and cfg['runner'] != cfg.get('continuation_runner'):
        raise ValueError('continuation runner must match the TRAIN runner pin')
    if not isinstance(cfg.get('output_accounting_extra_paths'), list):
        raise ValueError('explicit extra output accounting paths required')
    if sorted(e.get('seed') for e in cfg.get('sources', [])) != [0, 1]:
        raise ValueError('two exact original safe-parent source pins required')
    if cfg.get('controls') or cfg.get('checkpoint_updates') not in (None, [1024]):
        raise ValueError('calculator prototype has no historical controls or midpoint saves')


def readiness_issues(cfg):
    issues = []
    if cfg.get('dispatch_allowed') is not True:
        issues.append('dispatch_allowed is false; preparation only')
    if cfg.get('exclusive_lock_verified') is not True:
        issues.append('exclusive_lock_verified is not true')
    issues.extend(key + ' is not verified' for key in READINESS
                  if cfg.get('readiness', {}).get(key) is not True)
    return issues


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


def consume_train(raw, offset, count, config_sha256, seed, job):
    first = None
    if raw.is_file():
        with raw.open('rb') as stream:
            stream.seek(offset)
            chunk = stream.read()
        complete = chunk[:chunk.rfind(b'\n') + 1] if b'\n' in chunk else b''
        for line in complete.splitlines():
            record = json.loads(line)
            count += 1
            if (count > UPDATES or record.get('additional_update') != count
                    or record.get('update') != 10240 + count
                    or record.get('config_sha256') != config_sha256
                    or record.get('seed') != seed or record.get('arm') != 'calculator'
                    or record.get('job') != job):
                raise ValueError('owned TRAIN sequence/config/job binding differs')
            if first is None:
                first = record
        offset += len(complete)
    return offset, count, first


def focused_endpoint(root, cfg, config_sha256, seed, count, job):
    directory = safe(root, cfg['output_namespace']) / ('seed%d' % seed) / 'calculator'
    closed_path = directory / 'CLOSED.json'
    closed = read(closed_path)
    source = next(e for e in cfg['sources'] if e['seed'] == seed)
    if (count != UPDATES or closed.get('closed') is not True
            or closed.get('seed') != seed or closed.get('arm') != 'calculator'
            or closed.get('job') != job or closed.get('config_sha256') != config_sha256
            or closed.get('additional_optimizer_updates') != UPDATES
            or closed.get('optimizer_updates_this_process') != UPDATES
            or closed.get('source_checkpoint_sha256') != source['checkpoint']['sha256']
            or closed.get('durable_model_and_Adam_reload_equal') is not True):
        raise ValueError('focused immutable closure does not prove exact completed training')
    checkpoint = pin(root, closed['checkpoint'])
    if (checkpoint != (directory / 'final-resume.pt').resolve()
            or checkpoint.stat().st_size > cfg['budget']['checkpoint_cap_bytes']):
        raise ValueError('focused checkpoint path/extent differs')
    for name, key in (('TRAIN-RAW.jsonl', 'TRAIN_raw_sha256'),):
        if sha(directory / name) != closed.get(key):
            raise ValueError('closed focused raw hash differs')
    if any(directory.glob('*midpoint*')):
        raise ValueError('calculator prototype forbids midpoint checkpoints')
    calls = closed.get('model_call_account')
    if (not isinstance(calls, dict) or not calls
            or any(type(value) is not int or value < 0 for value in calls.values())):
        raise ValueError('exact immutable TRAIN model-call accounting required')
    return {'seed': seed, 'arm': 'calculator', 'checkpoint': closed['checkpoint'],
            'closed': {'path': str(closed_path.relative_to(root)), 'sha256': sha(closed_path)}}


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
    if (Path(__file__).resolve() != pkg / 'calculator_pc_driver.py'
            or sha(__file__) != launcher_hashes['calculator_pc_driver.py']):
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
    issues = readiness_issues(cfg)
    if check:
        print(json.dumps({'status': 'PREPARED-BLOCKED' if issues else 'CPU-STRUCTURE-PASSED',
            'issues': issues, 'request_sha256': request_hash, 'config_sha256': config_hash,
            'live_execution_validated': False, 'model_calls': 0, 'optimizer_updates': 0}), flush=True)
        return 0
    if issues:
        raise ValueError('; '.join(issues))
    runner = pin(root, cfg['continuation_runner'])
    evaluator = pin(root, cfg['evaluation_runner'])
    protocol_path = pin(root, cfg['evaluation_protocol'])
    storage_path = pin(root, cfg['storage_snapshot'])
    storage_spec = importlib.util.spec_from_file_location('_calculator_driver_storage', storage_path)
    storage = importlib.util.module_from_spec(storage_spec)
    storage_spec.loader.exec_module(storage)
    dmod.write_json = receipt.write_json
    d = (driver_factory or dmod.Driver)(request)
    batch = d.state / 'mixtures' / request['batch_id']
    matrix = safe(root, cfg['output_namespace'])
    eval_dir = safe(root, cfg.get('evaluation_output_namespace', cfg['output_namespace'] + '/native-evaluation'))
    terminal = Path(request.get('terminal_path', batch / 'TERMINAL.json')).resolve()
    if not terminal.is_relative_to(root):
        raise ValueError('queue terminal receipt is outside project root')
    roots = unique_roots([matrix, batch, terminal,
        *[safe(root, p) for p in cfg['output_accounting_extra_paths']]])
    unit = storage.filesystem_allocation_unit(root)
    budget = cfg['budget']
    worker, locked = None, False
    endpoints, native_calls, training_calls = [], 0, 0
    state = {'batch_id': request['batch_id'], 'commit': request['commit'],
        'queued_utc': request['queued_utc'], 'driver_pid': os.getpid(),
        'driver_started_utc': dmod.iso(), 'request_sha256': request_hash,
        'config_sha256': config_hash, 'status': 'preflight', 'phase': 'training',
        'jobs': [], 'live_execution_validated': False, 'reserved_calls_allowed': False,
        'accounting_complete': False, 'training_model_calls': 0}

    def accounting():
        return {'schema': 'cap256.calculator-output-accounting.v1', 'allocation_unit_bytes': unit,
            'output_roots': [str(p) for p in roots],
            'new_output_allocated_bytes': sum(storage.allocated_bytes(p, unit) for p in roots),
            'project_allocated_bytes': storage.allocated_bytes(root, unit),
            'free_bytes': shutil.disk_usage(root).free, 'config_sha256': config_hash,
            'request_sha256': request_hash, 'live_execution_validated': False}

    def guard(extra=0):
        snapshot = accounting()
        if (snapshot['new_output_allocated_bytes'] + extra > budget['matrix_cap_bytes']
                or snapshot['project_allocated_bytes'] + extra > budget['project_cap_bytes']
                or snapshot['free_bytes'] - extra < budget['retained_free_bytes']):
            raise RuntimeError('calculator output/project/free resource cap exceeded')
        for seed in (0, 1):
            if storage.allocated_bytes(matrix / ('seed%d' % seed), unit) + extra > budget['pair_cap_bytes']:
                raise RuntimeError('calculator retained seed-pair cap exceeded')
        return snapshot

    def write(path, value, exclusive=False):
        data = (json.dumps(value, sort_keys=True, indent=2, default=str, allow_nan=False) + '\n').encode()
        guard(len(data) + unit)
        return receipt.write_json(path, value, exclusive=exclusive)

    def save():
        write(batch / 'BATCH.json', state)

    def immutable_request():
        if clock() - started >= budget['total_job_seconds']:
            raise RuntimeError('entire calculator job hard900-second cap exhausted')
        if sha(request_path) != request_hash or sha(cfg_path) != config_hash:
            raise ValueError('immutable request/config changed after preflight')
        for path, expected in ((runner, cfg['continuation_runner']['sha256']),
                               (evaluator, cfg['evaluation_runner']['sha256']),
                               (protocol_path, cfg['evaluation_protocol']['sha256'])):
            if sha(path) != expected:
                raise ValueError('immutable worker/protocol changed before launch')

    def argv_base():
        return [getattr(sys, '_base_executable', sys.executable), '-X', 'utf8', '-B']

    def run_worker(argv, job, directory, cap, training_seed=None, fit_started=None):
        nonlocal worker
        immutable_request()
        if not d.guard(directory)['ok']:
            raise RuntimeError('exclusive ownership/GPU guard refused')
        immutable_request()
        cap = min(cap, budget['total_job_seconds'] - (clock() - started))
        if cap <= 0:
            raise RuntimeError('no remaining calculator job wall time')
        write(directory / 'RUNNER-ARGV.json', {'argv': argv, 'job': job}, True)
        env = dict(os.environ, JOB=job, TREE=str(root), PYTHONUNBUFFERED='1',
            PYTHONPATH=os.pathsep.join(site.getsitepackages()), PYTHONDONTWRITEBYTECODE='1',
            HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        worker_start = clock()
        worker = worker_factory(argv, directory, root, env, guard)
        js = {'job_id': job, 'phase': 'training' if training_seed is not None else 'native-evaluation',
            'seed': training_seed, 'runner_pid': worker.pid, 'runner_started_utc': dmod.iso(),
            'status': 'runner_started', 'additional_updates': 0}
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
        offset, count, first, last_progress = 0, 0, False, -30
        try:
            save()
            while True:
                rc = worker.poll()
                if cap_fired.is_set():
                    raise RuntimeError('exact owned worker watchdog wall cap exceeded')
                elapsed = clock() - worker_start
                if training_seed is not None:
                    raw = matrix / ('seed%d' % training_seed) / 'calculator' / 'TRAIN-RAW.jsonl'
                    offset, count, record = consume_train(raw, offset, count, config_hash, training_seed, job)
                    js['additional_updates'] = count
                    if record is not None and not first:
                        write(directory / 'FIRST-UPDATE.json', {'job_id': job,
                            'detected_utc': dmod.iso(), 'first_update': record['update'],
                            'first_additional_update': record['additional_update'],
                            'numeric_CE': record.get('numeric_CE'), 'preclip_norm': record.get('preclip_norm'),
                            'runner_start_to_first_update_detected_seconds': elapsed}, True)
                        first = True
                if elapsed - last_progress >= 10 or rc is not None:
                    guard()
                    js.update(status='training' if first else 'runner_started', runner_wall_seconds=elapsed)
                    write(directory / 'PROGRESS.json', {**js, 'utc': dmod.iso(), 'runner_returncode': rc})
                    save()
                    last_progress = elapsed
                if rc is not None:
                    worker.finish_logs()
                    js.update(returncode=rc, runner_ended_utc=dmod.iso(), runner_wall_seconds=elapsed,
                              status='completed' if rc == 0 else 'failed')
                    write(directory / 'EXIT.json', js, True)
                    save()
                    if elapsed > cap or (fit_started is not None and clock() - fit_started > budget['total_job_seconds']):
                        raise RuntimeError('owned worker completed outside hard wall cap')
                    return rc, count
                if (elapsed >= cap or (fit_started is not None and
                        clock() - fit_started >= budget['total_job_seconds'])):
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
            raise RuntimeError('prior calculator output/terminal exists; no duplicate run')
        guard(16 * MIB)
        batch.mkdir(parents=True, exist_ok=False)
        write(batch / 'GUIDE-START.json', guide_start, True)
        save()
        # No stale-PID takeover: an unconfirmed prior owner must remain blocked.
        write(d.lock, {'pid': os.getpid(), 'batch_id': request['batch_id'], 'utc': dmod.iso(),
                      'request_sha256': request_hash, 'driver': 'calculator_pc_driver.py'}, True)
        locked = True
        for source in cfg['sources']:
            for key in ('checkpoint', 'closed'):
                pin(root, source[key])
        state['status'] = 'running'
        save()
        fit_started = started
        for seed, _ in cfg['execution_order']:
            if clock() - fit_started >= budget['total_job_seconds']:
                raise RuntimeError('aggregate focused training cap exhausted')
            job = 'calculator1024-s%d-%s' % (seed, request['batch_id'])
            directory = batch / job
            directory.mkdir()
            argv = argv_base() + [str(runner), '--root', str(root), '--config', str(cfg_path),
                '--config-sha256', config_hash, '--seed', str(seed)]
            rc, count = run_worker(argv, job, directory, budget['worker_seconds'], seed, fit_started)
            if rc != 0:
                raise RuntimeError('focused seed returned non-success')
            endpoints.append(focused_endpoint(root, cfg, config_hash, seed, count, job))
            closed = read(pin(root, endpoints[-1]['closed']))
            training_calls += sum(closed['model_call_account'].values())
            state['training_model_calls'] = training_calls
        state['training_wall_seconds'] = clock() - fit_started
        endpoints_path = matrix / 'EVALUATION-ENDPOINTS.json'
        write(endpoints_path, {'train_config_sha256': config_hash,
            'protocol_sha256': cfg['evaluation_protocol']['sha256'], 'endpoints': endpoints}, True)
        endpoints_hash = sha(endpoints_path)
        state.update(phase='native-evaluation', status='running', focused_endpoints=endpoints[:2],
                     evaluation_endpoints_sha256=endpoints_hash)
        save()
        job = 'calculator-native-%s' % request['batch_id']
        directory = batch / job
        directory.mkdir()
        argv = argv_base() + [str(evaluator), '--root', str(root), '--config', str(cfg_path),
            '--config-sha256', config_hash, '--endpoints', str(endpoints_path),
            '--endpoints-sha256', endpoints_hash]
        rc, _ = run_worker(argv, job, directory, min(budget.get('evaluation_seconds', 600), budget['total_job_seconds'] - (clock() - started)), fit_started=started)
        eval_closed_path = eval_dir / 'CLOSED.json'
        eval_closed = read(eval_closed_path)
        native_calls = eval_closed.get('native_calls', 0)
        gate = eval_closed.get('fit_gate_passed')
        expected_native = NATIVE_CALLS if gate is True else 20
        if (rc != 0 or eval_closed.get('closed') is not True or type(gate) is not bool
                or native_calls != expected_native
                or eval_closed.get('fresh_native_calls') != (32 if gate else 0)
                or eval_closed.get('optimizer_updates') != 0
                or eval_closed.get('teacherforced_examples', eval_closed.get('teacherforced_dev_examples')) != 0
                or eval_closed.get('config_sha256') != config_hash
                or eval_closed.get('endpoints_sha256') != endpoints_hash
                or eval_closed.get('protocol_sha256') != cfg['evaluation_protocol']['sha256']):
            raise ValueError('native evaluation must close TRAIN20 then gated fresh32, with zero CE/updates and frozen pins')
        immutable_request()
        state.update(status='completed', phase='completed', native_calls=native_calls,
                     accounting_complete=True, fit_gate_passed=gate,
                     evaluation_closed=eval_closed,
                     evaluation_closed_pin={'path': str(eval_closed_path.relative_to(root)), 'sha256': sha(eval_closed_path)})
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
            'focused_endpoints_verified': endpoints[:2],
            'checkpoint_candidates': [str(matrix / ('seed%d' % seed) / 'calculator' / 'final-resume.pt') for seed in (0, 1)],
            'last_safe_sources': cfg['sources']}
    finally:
        if locked and (worker is None or worker.poll() is not None):
            holder = receipt.read_json(d.lock)
            if holder.get('pid') == os.getpid() and holder.get('request_sha256') == request_hash:
                os.replace(d.lock, batch / 'LOCK.released.json')
                locked = False
        state.update(driver_ended_utc=dmod.iso(), wall_seconds=clock() - started,
            optimizer_updates=sum(j.get('additional_updates', 0) for j in state['jobs']),
            native_calls=native_calls, model_calls=training_calls + native_calls,
            exclusive_lock_preserved=locked)
        if state['status'] == 'completed' and state['wall_seconds'] > budget['total_job_seconds']:
            state.update(status='failed', error='calculator job exceeded total wall cap', accounting_complete=False)
        if worker is None:
            state['accounting_complete'] = True
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
                    {'kind': 'config', 'path': str(cfg_path), 'sha256': config_hash},
                    {'kind': 'accounting', 'path': str(accounting_path), 'sha256': sha(accounting_path)}]
                evidence.extend({'kind': 'checkpoint', 'seed': e['seed'],
                    'path': str(safe(root, e['checkpoint']['path'])), 'sha256': e['checkpoint']['sha256']}
                    for e in endpoints if e['arm'] == 'calculator')
                if state.get('evaluation_closed_pin'):
                    e = state['evaluation_closed_pin']
                    evidence.append({'kind': 'evaluation_closed', 'path': str(safe(root, e['path'])), 'sha256': e['sha256']})
                terminal_record = {'job_id': request.get('job_id', request['batch_id']),
                    'attempt_id': request['batch_id'], 'terminal': True,
                    'status': 'completed' if state['status'] == 'completed' else 'failed',
                    'phase': state['phase'], 'wall_seconds': clock() - started,
                    'output_bytes': accounting()['new_output_allocated_bytes'],
                    'model_calls': training_calls + native_calls, 'native_calls': native_calls,
                    'optimizer_updates': state['optimizer_updates'],
                    'accounting_complete': state['accounting_complete'],
                    'optimizer_updates_exact': state['accounting_complete'],
                    'proven_zero_work': worker is None, 'retry_authorized': False,
                    'request_sha256': request_hash, 'config_sha256': config_hash,
                    'output_includes_terminal_receipt': True,
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
                        'known_training_model_calls': training_calls,
                        'known_native_calls': native_calls,
                        'optimizer_updates_observed': state['optimizer_updates'],
                        'evidence': evidence}, True)
    return 0 if state['status'] == 'completed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raise SystemExit(execute(args.request, check=args.check))
