"""Run approved capability256 arms one at a time on BensPC and keep receipts.

Started detached (WMI Win32_Process Create) by mac_launch.py, so an SSH drop
cannot kill training. For each arm it:
  1. takes the single-run lock (waits if another batch holds it),
  2. refuses if the arm already has output (never overwrites evidence),
  3. re-verifies the pinned package and warm-start checkpoints,
  4. runs pc_guard (duplicate-job / GPU checks) and saves the full decision,
  5. writes the fresh resource inventory the sealed runner requires,
  6. starts the unchanged sealed runner with stdout/stderr going to files,
  7. writes FIRST-UPDATE.json as soon as TRAIN-RAW.jsonl has a line, then
     PROGRESS.json while it trains, then EXIT.json when it stops.
A failed arm stops the batch; later arms stay queued and are marked skipped.

Receipts live in <root>/launch-cap256/jobs/<job_id>/ and are never deleted.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pc_guard  # noqa: E402

OWN_REL = 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1'
HELPER_REL = 'scripts/sol_cloud_queue_recovery_v1.py'
TAIL_BYTES = 16384
GUARD_RECHECKS = 7
GUARD_RECHECK_SECONDS = 10
LOCK_WAIT_SECONDS = 8 * 3600
FIRST_POLL_SECONDS = 2
TRAIN_POLL_SECONDS = 10
PROGRESS_EVERY_SECONDS = 30


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def iso(moment=None):
    return (moment or now()).isoformat()


def sha_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, record, exclusive=False):
    data = json.dumps(record, indent=2, sort_keys=True, default=str) + '\n'
    path = Path(path)
    if exclusive:
        with path.open('x', encoding='utf8') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf8') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def tail_text(path, limit=TAIL_BYTES):
    size = path.stat().st_size
    with path.open('rb') as stream:
        stream.seek(max(0, size - limit))
        return stream.read().decode('utf8', 'replace')


class Driver:
    def __init__(self, request):
        self.request = request
        self.root = Path(request['root'])
        self.spec = request['spec']
        self.batch_id = request['batch_id']
        self.state = self.root / 'launch-cap256'
        self.batch_dir = self.state / 'batches' / self.batch_id
        self.lock = self.state / 'LOCK.json'

    # ---- probes (overridden in tests) -------------------------------------------------
    def run_text(self, argv, timeout=30):
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        if done.returncode:
            raise RuntimeError('probe %r failed rc=%s stderr=%s' % (argv[:3], done.returncode, done.stderr[-2000:]))
        return done.stdout

    def probe_processes(self):
        text = self.run_text(['powershell', '-NoProfile', '-NonInteractive', '-Command',
            'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,'
            'ExecutablePath,CommandLine | ConvertTo-Json -Compress'], timeout=60)
        rows = json.loads(text or '[]')
        rows = [rows] if isinstance(rows, dict) else rows
        return [{'pid': int(r['ProcessId']), 'ppid': int(r.get('ParentProcessId') or 0),
                 'name': r.get('Name'), 'exe': r.get('ExecutablePath'), 'cmdline': r.get('CommandLine')}
                for r in rows]

    def probe_gpu(self):
        rows = self.run_text(['nvidia-smi', '--query-gpu=index,utilization.gpu,memory.used,memory.total',
                              '--format=csv,noheader,nounits'])
        gpu_rows = [[int(v.strip()) for v in row.split(',')] for row in rows.splitlines() if row.strip()]
        apps = []
        for row in self.run_text(['nvidia-smi', '--query-compute-apps=pid,used_memory',
                                  '--format=csv,noheader,nounits']).splitlines():
            parts = [part.strip() for part in row.split(',')]
            if len(parts) == 2 and parts[0].isdecimal():
                apps.append({'pid': int(parts[0]), 'used_memory': parts[1]})
        return gpu_rows, apps

    def gpu_snapshot(self):
        try:
            return self.run_text(['nvidia-smi', '--query-gpu=memory.used,memory.total,power.draw,utilization.gpu',
                                  '--format=csv,noheader']).strip()
        except Exception as error:  # a snapshot is evidence only
            return 'unavailable: %r' % error

    def pid_alive_driver(self, pid):
        return any(p['pid'] == pid and pc_guard.DRIVER_MARK in pc_guard.norm(p.get('cmdline'))
                   for p in self.probe_processes())

    # ---- checks -------------------------------------------------------------------------
    def verify_package(self):
        helper_path = self.root / HELPER_REL
        spec_obj = importlib.util.spec_from_file_location('_cap256_helper', helper_path)
        helper = importlib.util.module_from_spec(spec_obj)
        spec_obj.loader.exec_module(helper)
        plan = json.loads((self.root / self.spec['plan']['path']).read_bytes())
        seal = json.loads((self.root / self.spec['seal']['path']).read_bytes())
        release = json.loads((self.root / self.spec['release']['path']).read_bytes())
        pins = [{k: f[k] for k in ('path', 'sha256', 'bytes')} for f in self.spec['files']]
        smoke = helper.package_smoke(self.root, pins,
                                     required_pins=helper.packaged_runtime_pins(self.spec, plan, seal, release))
        return plan, smoke

    def verify_closure(self, plan):
        closure = []
        for seed in (0, 1):
            binding = plan['warmstart']['tuples'][str(seed)]
            if binding.get('numeric_resume_sha256') != self.spec['numeric16_loop_sha256'][str(seed)]:
                raise ValueError('numeric16 warm-start seal differs for seed %d' % seed)
            for key in ('parent', 'reader', 'adapter', 'numeric_resume'):
                path = Path(binding[key + '_path'])
                if not path.is_file() or sha_file(path) != binding[key + '_sha256']:
                    raise ValueError('checkpoint differs: seed %d %s %s' % (seed, key, path))
                closure.append({'seed': seed, 'kind': key, 'sha256': binding[key + '_sha256']})
            path = Path(binding['lm_provenance'])
            if not path.is_file() or sha_file(path) != plan['LM_provenance']['sha256']:
                raise ValueError('frozen LM provenance differs: %s' % path)
        return closure

    def guard(self, job_dir):
        attempts = []
        for attempt in range(GUARD_RECHECKS):
            gpu_rows, apps = self.probe_gpu()
            decision = pc_guard.classify(self.probe_processes(), apps, gpu_rows, os.getpid(), self.root)
            decision['checked_utc'] = iso()
            attempts.append(decision)
            if decision['block'] or not decision['wait']:
                break
            if attempt + 1 < GUARD_RECHECKS:
                time.sleep(GUARD_RECHECK_SECONDS)
        write_json(job_dir / 'GUARD.json', {'attempts': attempts, 'ok': attempts[-1]['ok']})
        return attempts[-1]

    def runner_argv(self, seed, arm, inventory_path, inventory_sha):
        s = self.spec
        return [sys.executable, '-X', 'utf8', '-B', str(self.root / s['runner']['path']),
                '--phase', 'train', '--seed', str(seed), '--arm', arm,
                '--plan', str(self.root / s['plan']['path']), '--plan-sha256', s['plan']['sha256'],
                '--seal', str(self.root / s['seal']['path']), '--seal-sha256', s['seal']['sha256'],
                '--release', str(self.root / s['release']['path']), '--release-sha256', s['release']['sha256'],
                '--inventory', str(inventory_path), '--inventory-sha256', inventory_sha]

    def write_inventory(self, job_id, decision, smoke, closure):
        unit = 65536
        allocated = sum(((f['bytes'] + unit - 1) // unit) * unit for f in self.spec['files'])
        path = self.root / OWN_REL / self.spec['run_namespace'] / 'inventory' / (job_id + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        free = __import__('shutil').disk_usage(str(self.root))
        inventory = {'schema': 'sol.cloud.capability256.resource-inventory.v2', 'job': job_id,
            'observed_utc': iso(), 'C_free_bytes': free.free, 'C_total_bytes': free.total,
            'gpu_inventory_verified': True, 'gpu_rows': decision['gpu_rows'],
            'gpu_clients_allowed': decision['gpu_clients'], 'project_gpu_processes': [],
            'python_exe_conflicts': [], 'unrelated_python_allowed': decision['allowed_python'],
            'other_watcher_running_claims': [], 'source_checkpoint_closure_verified': True,
            'source_checkpoint_closure': closure, 'delivery_package_and_tree_bytes': smoke['total_bytes'],
            'package_smoke_file_count': len(smoke.get('files', [])) if isinstance(smoke, dict) else None,
            'global_shared_storage_verified': True, 'global_shared_cap_bytes': 8 * 1024 ** 2,
            'global_shared_allocated_bytes': allocated + unit, 'inventory_file_allocated_bytes': unit,
            'actual_user_day': False, 'model_calls': 0, 'optimizer_updates_before_runner': 0,
            'launcher': {'commit': self.request['commit'], 'batch_id': self.batch_id}}
        data = (json.dumps(inventory, sort_keys=True) + '\n').encode('utf8')
        if len(data) > unit:
            raise RuntimeError('inventory exceeds one allocation unit')
        with path.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return path, hashlib.sha256(data).hexdigest()

    # ---- one arm --------------------------------------------------------------------------
    def run_arm(self, seed, arm, previous_exit):
        job_id = 'cap256-s%d-%s-%s' % (seed, arm, self.batch_id)
        job_dir = self.state / 'jobs' / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        events = job_dir / 'EVENTS.jsonl'
        state = {'job_id': job_id, 'seed': seed, 'arm': arm, 'batch_id': self.batch_id,
                 'commit': self.request['commit'], 'queued_utc': self.request['queued_utc'],
                 'status': 'picked_up', 'picked_up_utc': iso(), 'optimizer_updates': 0}

        def mark(status, **extra):
            state.update(extra, status=status, status_utc=iso())
            write_json(job_dir / 'STATE.json', state)
            with events.open('a', encoding='utf8') as stream:
                stream.write(json.dumps({'utc': iso(), 'status': status, **extra}, default=str) + '\n')

        mark('picked_up', driver_pid=os.getpid())
        run_dir = self.root / OWN_REL / self.spec['run_namespace'] / ('seed%d' % seed) / arm
        try:
            if run_dir.exists():
                raise RuntimeError('arm output already exists at %s; refusing to overwrite evidence' % run_dir)
            plan, smoke = self.verify_package()
            closure = self.verify_closure(plan)
            mark('preflight_package_ok', package_total_bytes=smoke.get('total_bytes'))
            decision = self.guard(job_dir)
            if not decision['ok']:
                raise RuntimeError('launch guard refused: ' + json.dumps(
                    {'block': decision['block'], 'wait': decision['wait']}, default=str)[:4000])
            inventory_path, inventory_sha = self.write_inventory(job_id, decision, smoke, closure)
            argv = self.runner_argv(seed, arm, inventory_path, inventory_sha)
            write_json(job_dir / 'RUNNER-ARGV.json', {'argv': argv, 'inventory_sha256': inventory_sha})
        except Exception as error:
            mark('failed', stage='preflight', error_type=type(error).__name__, error=str(error),
                 traceback=traceback.format_exc(), optimizer_updates=0, runner_invoked=False)
            return state

        stdout_path, stderr_path = job_dir / 'runner-stdout.log', job_dir / 'runner-stderr.log'
        env = dict(os.environ, JOB=job_id, TREE=str(self.root.resolve()), PYTHONUNBUFFERED='1')
        flags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
        started = now()
        with stdout_path.open('xb') as out, stderr_path.open('xb') as err:
            process = subprocess.Popen(argv, cwd=str(self.root), env=env, stdout=out, stderr=err,
                                       creationflags=flags)
        idle = (started - previous_exit).total_seconds() if previous_exit else None
        mark('runner_started', runner_pid=process.pid, runner_started_utc=iso(started),
             idle_seconds_since_previous_arm=idle, run_dir=str(run_dir))

        train_raw = run_dir / 'TRAIN-RAW.jsonl'
        offset, lines, first_record = 0, 0, None
        last_progress = 0.0
        while True:
            rc = process.poll()
            if train_raw.is_file():
                with train_raw.open('rb') as stream:
                    stream.seek(offset)
                    chunk = stream.read()
                complete = chunk[:chunk.rfind(b'\n') + 1] if b'\n' in chunk else b''
                if complete:
                    if first_record is None:
                        first_record = json.loads(complete.split(b'\n', 1)[0])
                    offset += len(complete)
                    lines += complete.count(b'\n')
            if first_record is not None and state['status'] == 'runner_started':
                seen = now()
                queued = datetime.datetime.fromisoformat(self.request['queued_utc'])
                receipt = {'job_id': job_id, 'seed': seed, 'arm': arm, 'commit': self.request['commit'],
                    'first_update_detected_utc': iso(seen), 'poll_interval_seconds': FIRST_POLL_SECONDS,
                    'first_record_update': first_record.get('update'),
                    'first_record_numeric_CE': first_record.get('numeric_CE'),
                    'first_record_preclip_norm': first_record.get('preclip_norm'),
                    'first_record_job': first_record.get('job'),
                    'optimizer_updates_seen': lines, 'train_raw_path': str(train_raw),
                    'queue_to_first_update_seconds': (seen - queued).total_seconds(),
                    'picked_up_to_first_update_seconds': (seen - datetime.datetime.fromisoformat(
                        state['picked_up_utc'])).total_seconds(),
                    'runner_start_to_first_update_seconds': (seen - started).total_seconds(),
                    'gpu_at_first_update': self.gpu_snapshot()}
                write_json(job_dir / 'FIRST-UPDATE.json', receipt, exclusive=True)
                mark('training', optimizer_updates=lines, first_update_utc=iso(seen))
            if state['status'] == 'training' and (time.monotonic() - last_progress >= PROGRESS_EVERY_SECONDS
                                                  or rc is not None):
                last_progress = time.monotonic()
                state['optimizer_updates'] = lines
                write_json(job_dir / 'PROGRESS.json', {'job_id': job_id, 'utc': iso(),
                    'optimizer_updates': lines, 'target_updates': 5120,
                    'elapsed_since_runner_start_seconds': (now() - started).total_seconds(),
                    'gpu': self.gpu_snapshot()})
                write_json(job_dir / 'STATE.json', state)
            if rc is not None:
                break
            time.sleep(FIRST_POLL_SECONDS if first_record is None else TRAIN_POLL_SECONDS)

        ended = now()
        exit_record = {'job_id': job_id, 'seed': seed, 'arm': arm, 'commit': self.request['commit'],
            'returncode': rc, 'runner_pid': process.pid, 'runner_started_utc': iso(started),
            'runner_ended_utc': iso(ended), 'runner_wall_seconds': (ended - started).total_seconds(),
            'optimizer_updates_counted_from_TRAIN_RAW': lines, 'run_dir': str(run_dir)}
        for label, path in (('stdout', stdout_path), ('stderr', stderr_path)):
            exit_record[label] = {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha_file(path),
                                  'tail': tail_text(path)}
        for name in ('CLOSED.json', 'FAILED.json', 'MEMORY-PREFLIGHT.json'):
            path = run_dir / name
            if path.is_file() and path.stat().st_size <= 262144:
                try:
                    exit_record[name] = json.loads(path.read_text(encoding='utf8').splitlines()[-1])
                except ValueError:
                    exit_record[name] = {'unparsed_tail': tail_text(path, 4096)}
        failures = self.root / OWN_REL / 'runner' / 'failures'
        if failures.is_dir():
            exit_record['runner_preflight_failures'] = [
                {'path': str(p), 'record': p.read_text(encoding='utf8')[:8192]}
                for p in sorted(failures.glob('preflight-*.json'))
                if p.stat().st_mtime >= started.timestamp() - 5]
        checkpoint = run_dir / 'final-resume.pt'
        if checkpoint.is_file():
            exit_record['checkpoint'] = {'path': str(checkpoint), 'bytes': checkpoint.stat().st_size,
                                         'sha256': sha_file(checkpoint)}
        closed = exit_record.get('CLOSED.json', {})
        ok = rc == 0 and closed.get('closed') is True and lines == 5120
        write_json(job_dir / 'EXIT.json', exit_record, exclusive=True)
        mark('completed' if ok else 'failed', stage='runner', returncode=rc, optimizer_updates=lines,
             runner_ended_utc=iso(ended), checkpoint=exit_record.get('checkpoint', {}).get('path'))
        return state

    # ---- batch ----------------------------------------------------------------------------
    def acquire_lock(self):
        waited_from = time.monotonic()
        while True:
            try:
                write_json(self.lock, {'pid': os.getpid(), 'batch_id': self.batch_id, 'utc': iso()}, exclusive=True)
                return time.monotonic() - waited_from
            except FileExistsError:
                try:
                    holder = json.loads(self.lock.read_text(encoding='utf8'))
                except (OSError, ValueError):
                    holder = {}
                if holder.get('pid') and not self.pid_alive_driver(holder['pid']):
                    os.replace(self.lock, self.state / ('LOCK.stale-%s.json' % now().strftime('%Y%m%dT%H%M%S')))
                    continue
                if time.monotonic() - waited_from > LOCK_WAIT_SECONDS:
                    raise TimeoutError('lock held by %r for too long' % holder)
                time.sleep(15)

    def run(self):
        self.batch_dir.mkdir(parents=True, exist_ok=True)
        batch = {'batch_id': self.batch_id, 'commit': self.request['commit'], 'queued_utc': self.request['queued_utc'],
                 'driver_pid': os.getpid(), 'driver_started_utc': iso(), 'arms': self.request['arms'],
                 'jobs': [], 'status': 'waiting_for_lock'}
        write_json(self.batch_dir / 'BATCH.json', batch)
        try:
            batch['lock_wait_seconds'] = self.acquire_lock()
            batch['status'] = 'running'
            write_json(self.batch_dir / 'BATCH.json', batch)
            previous_exit = None
            for index, (seed, arm) in enumerate(self.request['arms']):
                if previous_exit is None and self.request.get('previous_exit_utc'):
                    previous_exit = datetime.datetime.fromisoformat(self.request['previous_exit_utc'])
                result = self.run_arm(seed, arm, previous_exit)
                batch['jobs'].append({k: result.get(k) for k in (
                    'job_id', 'status', 'optimizer_updates', 'returncode', 'idle_seconds_since_previous_arm')})
                write_json(self.batch_dir / 'BATCH.json', batch)
                previous_exit = now()
                if result['status'] != 'completed':
                    batch['skipped_arms'] = self.request['arms'][index + 1:]
                    break
            batch['status'] = 'done'
        except Exception as error:
            batch.update(status='driver_error', error=repr(error), traceback=traceback.format_exc())
        finally:
            batch['driver_ended_utc'] = iso()
            write_json(self.batch_dir / 'BATCH.json', batch)
            try:
                holder = json.loads(self.lock.read_text(encoding='utf8'))
                if holder.get('pid') == os.getpid():
                    os.replace(self.lock, self.batch_dir / 'LOCK.released.json')
            except (OSError, ValueError):
                pass
        return batch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('run',))
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--log', type=Path, help='append driver stdout/stderr here (detached runs)')
    args = parser.parse_args()
    if args.log:
        stream = open(args.log, 'a', encoding='utf8', buffering=1)
        sys.stdout = sys.stderr = stream
    request = json.loads(args.request.read_text(encoding='utf8'))
    batch = Driver(request).run()
    return 0 if batch['status'] == 'done' and all(j['status'] == 'completed' for j in batch['jobs']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
