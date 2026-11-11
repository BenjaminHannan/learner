"""Once-only sealed capability256 final evaluation; reuse the committed PC lock/guard.

No training, selection, retries, or changes to the sealed runner. Requests pin all
four final checkpoints and the committed launcher package. Raw items stay on PC.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import site
import subprocess
import sys
import time
import traceback


def execute(request_path):
    request = json.loads(Path(request_path).read_bytes())
    pkg = Path(request['pkg'])
    sys.path.insert(0, str(pkg))
    import pc_driver as driver
    import pc_guard
    if pc_guard.DRIVER_MARK != 'pc_driver.py':
        raise RuntimeError('committed live-lock fix required')
    for name, expected in request['launcher_sha256'].items():
        if driver.sha_file(pkg / name) != expected:
            raise RuntimeError('committed launcher package differs')
    d = driver.Driver(request)
    job = request['batch_id']
    receipt_dir = d.state / 'evaluations' / job
    receipt_dir.mkdir(parents=True, exist_ok=False)
    status = {'job_id': job, 'phase': 'final', 'commit': request['commit'],
              'driver_started_utc': driver.iso(), 'driver_pid': os.getpid(),
              'status': 'preflight', 'optimizer_updates': 0, 'no_retry': True}
    def mark(**values):
        status.update(values, status_utc=driver.iso())
        driver.write_json(receipt_dir / 'STATE.json', status)
    mark()
    locked = False
    try:
        if d.lock.exists():
            raise RuntimeError('another lock exists; do not queue behind it')
        d.acquire_lock(); locked = True
        plan, smoke = d.verify_package()
        closure = d.verify_closure(plan)
        matrix = d.root / driver.OWN_REL / d.spec['run_namespace']
        evidence = [p for p in matrix.rglob('*') if p.is_file()
                    and p.name.upper().startswith('FINAL') and p.name != 'final-resume.pt']
        if evidence:
            raise RuntimeError('prior final evidence exists; no duplicate evaluation')
        freeze = {'schema': 'sol.cloud.capability256.final-freeze.v1',
                  'plan_sha256': d.spec['plan']['sha256'], 'seal_sha256': d.spec['seal']['sha256'],
                  'comparators': plan['comparators'], 'checkpoints': []}
        for item in request['checkpoints']:
            out = matrix / ('seed%d' % item['seed']) / item['arm']
            checkpoint = out / 'final-resume.pt'; closed_path = out / 'CLOSED.json'
            closed = json.loads(closed_path.read_bytes())
            digest = driver.sha_file(checkpoint)
            if (digest != item['sha256'] or closed.get('closed') is not True
                    or closed.get('checkpoint', {}).get('sha256') != digest):
                raise RuntimeError('fixed checkpoint/closure differs')
            freeze['checkpoints'].append({'seed': item['seed'], 'arm': item['arm'],
                'checkpoint': closed['checkpoint'],
                'closed': {'path': closed_path.relative_to(d.root).as_posix(), 'sha256': driver.sha_file(closed_path)}})
        decision = d.guard(receipt_dir)
        if not decision['ok']:
            raise RuntimeError('exclusive ownership/GPU guard refused')
        freeze_path = matrix / 'FINAL-FREEZE.json'
        driver.write_json(freeze_path, freeze, exclusive=True)
        inventory_path, _ = d.write_inventory(job, decision, smoke, closure)
        module_spec = importlib.util.spec_from_file_location('_sealed_cap256_final', d.root / d.spec['runner']['path'])
        sealed = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(sealed)
        unit = sealed.filesystem_allocation_unit(d.root)
        delivered = {d.root / f['path'] for f in d.spec['files']}
        delivered.update(p for p in d.state.rglob('*') if p.is_file())
        delivered.update(p for p in (matrix / 'inventory').glob('*.json') if p.is_file())
        allocated = sum(((p.stat().st_size + unit - 1) // unit) * unit for p in delivered)
        # Reserve 1 MiB for final wrapper/runner logs and receipts before the gates.
        inventory = json.loads(inventory_path.read_bytes())
        inventory.update(global_shared_allocated_bytes=allocated + 1024**2,
                         actual_allocation_unit_bytes=unit,
                         global_shared_file_count=len(delivered),
                         global_shared_future_telemetry_reserve_bytes=1024**2)
        if inventory['global_shared_allocated_bytes'] > plan['budget']['delivery_cap_bytes']:
            raise RuntimeError('sealed global delivery cap refused')
        driver.write_json(inventory_path, inventory)
        argv = [sys.executable, '-X', 'utf8', '-B', str(d.root / d.spec['runner']['path']), '--phase', 'final']
        for name in ('plan', 'seal', 'release'):
            argv += ['--' + name, str(d.root / d.spec[name]['path']), '--' + name + '-sha256', d.spec[name]['sha256']]
        argv += ['--inventory', str(inventory_path), '--inventory-sha256', driver.sha_file(inventory_path),
                 '--final-freeze', str(freeze_path), '--final-freeze-sha256', driver.sha_file(freeze_path)]
        driver.write_json(receipt_dir / 'RUNNER-ARGV.json', {'argv': argv, 'final_freeze_sha256': driver.sha_file(freeze_path)}, exclusive=True)
        env = dict(os.environ, JOB=job, TREE=str(d.root.resolve()), PYTHONUNBUFFERED='1',
                   PYTHONPATH=os.pathsep.join(site.getsitepackages()), PYTHONDONTWRITEBYTECODE='1',
                   HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        started = driver.now()
        with (receipt_dir / 'runner-stdout.log').open('xb') as out, (receipt_dir / 'runner-stderr.log').open('xb') as err:
            process = subprocess.Popen(argv, cwd=str(d.root), env=env, stdout=out, stderr=err,
                                       creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
        mark(status='runner_started', runner_pid=process.pid, runner_started_utc=driver.iso(started),
             final_freeze_sha256=driver.sha_file(freeze_path))
        while True:
            rc = process.poll()
            generated = {}
            for seed, arm in ((0, 'loop'), (0, 'plain'), (1, 'loop'), (1, 'plain')):
                raw = matrix / ('seed%d' % seed) / arm / 'FINAL-RAW.jsonl'
                if raw.exists():
                    with raw.open('rb') as stream:
                        generated['s%d-%s' % (seed, arm)] = sum(line.endswith(b'\n') for line in stream)
                else: generated['s%d-%s' % (seed, arm)] = 0
            driver.write_json(receipt_dir / 'PROGRESS.json', {'job_id': job, 'utc': driver.iso(),
                'elapsed_since_runner_start_seconds': (driver.now() - started).total_seconds(),
                'saved_question_predictions': generated, 'expected_questions_per_arm': 160,
                'native_calls_per_question': 2, 'optimizer_updates': 0, 'runner_returncode': rc})
            if rc is not None: break
            time.sleep(10)
        ended = driver.now()
        closed = matrix / 'FINAL-CLOSED.json'
        final = json.loads(closed.read_bytes()) if closed.exists() else None
        record = {'job_id': job, 'phase': 'final', 'returncode': rc, 'runner_started_utc': driver.iso(started),
                  'runner_ended_utc': driver.iso(ended), 'runner_wall_seconds': (ended - started).total_seconds(),
                  'optimizer_updates': 0, 'FINAL-CLOSED': final,
                  'stdout_sha256': driver.sha_file(receipt_dir / 'runner-stdout.log'),
                  'stderr_sha256': driver.sha_file(receipt_dir / 'runner-stderr.log')}
        driver.write_json(receipt_dir / 'EXIT.json', record, exclusive=True)
        mark(status='completed' if rc == 0 and final and final.get('closed') is True else 'failed',
             returncode=rc, runner_ended_utc=driver.iso(ended), runner_wall_seconds=record['runner_wall_seconds'])
    except Exception as error:
        mark(status='failed', error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
    finally:
        if locked:
            holder = json.loads(d.lock.read_bytes())
            if holder.get('pid') == os.getpid():
                os.replace(d.lock, receipt_dir / 'LOCK.released.json')
    return 0 if status['status'] == 'completed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--request', required=True)
    raise SystemExit(execute(parser.parse_args().request))
