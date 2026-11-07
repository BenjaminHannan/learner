"""Own the shared GPU lease, worker PID and expiring private job directory."""
import argparse
import contextlib
import json
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import gpu_gate

PC_ROOT = Path('C:/Users/benja/hands-train')
LEASE_ROOT = Path('C:/Users/benja/hands-gym')
EVENT_FILE = None


def emit(event):
    if EVENT_FILE is not None:
        with EVENT_FILE.open('a', encoding='utf8') as handle:
            handle.write(json.dumps(event) + '\n')
    print(json.dumps(event), flush=True)


def authorized(root, now=None):
    if (root / 'cancel').exists():
        return False
    try:
        expiry = json.loads((root / 'permit.json').read_text())['expiresAt']
        clock = time.time() if now is None else now
        return clock < expiry <= clock + 90
    except (OSError, ValueError, KeyError, TypeError):
        return False


def remove_job(root):
    if root.parent != PC_ROOT or not root.name.startswith('hands-'):
        raise RuntimeError('refusing cleanup outside the private job root')
    for attempt in range(10):
        try:
            if root.exists():
                shutil.rmtree(root)
            return
        except OSError:
            if attempt == 9:
                raise
            time.sleep(1)


def pipe_lines(process, messages):
    for line in process.stdout:
        messages.put(line)
    messages.put(None)


def wait_for_client(root):
    while root.exists() and authorized(root):
        time.sleep(0.5)


def supervise(root, *, gpu_wait, timeout):
    worker = None
    try:
        while not (root / 'upload-ready').exists():
            if not authorized(root):
                raise RuntimeError('Mac permit expired during upload')
            time.sleep(0.5)
        lease = gpu_gate.Lease(LEASE_ROOT)
        deadline = time.monotonic() + gpu_wait
        while True:
            if not authorized(root):
                raise RuntimeError('Mac permit expired or training cancelled')
            try:
                with contextlib.redirect_stdout(sys.stderr):
                    lease.__enter__()
                break
            except (RuntimeError, FileExistsError) as error:
                if time.monotonic() >= deadline:
                    emit({'event': 'error', 'kind': 'busy', 'error': str(error)})
                    wait_for_client(root)
                    return 3
                emit({'event': 'phase', 'name': 'wait-shared-gpu-lease', 'reason': str(error)})
                time.sleep(min(5, max(0, deadline - time.monotonic())))
        done = None
        failed = False
        try:
            emit({'event': 'phase', 'name': 'shared-gpu-lease-acquired', 'leasePath': str(lease.path)})
            worker = subprocess.Popen([sys.executable, '-u', str(root / 'src/train_remote.py'),
                                       '--job', str(root / 'job.json'), '--out', str(root / 'out')],
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            messages = queue.Queue()
            threading.Thread(target=pipe_lines, args=(worker, messages), daemon=True).start()
            deadline = time.monotonic() + timeout
            while True:
                if not authorized(root):
                    raise RuntimeError('Mac permit expired or training cancelled')
                if time.monotonic() >= deadline:
                    emit({'event': 'error', 'kind': 'timeout', 'error': 'training timeout'})
                    failed = True
                    break
                try:
                    line = messages.get(timeout=1)
                except queue.Empty:
                    continue
                if line is None:
                    break
                try:
                    event = json.loads(line)
                except ValueError:
                    sys.stderr.write(line)
                    continue
                if event.get('event') == 'done':
                    done = event
                else:
                    if event.get('event') == 'error':
                        failed = True
                    emit(event)
            code = worker.wait(timeout=10) if not failed else 1
            if code or failed or done is None:
                if not failed:
                    emit({'event': 'error', 'kind': 'training', 'error': f'worker exit {code}, no result'})
                failed = True
        finally:
            if worker is not None:
                if worker.poll() is None:
                    worker.terminate()
                    worker.wait(timeout=20)
                worker.stdout.close()
            lease.__exit__(None, None, None)
        if not failed:
            done['leaseReleased'] = True
            done['workerExitCode'] = code
            emit(done)
        wait_for_client(root)
        return 1 if failed else 0
    except Exception as error:
        emit({'event': 'error', 'kind': 'transport', 'error': str(error)})
        wait_for_client(root)
        return 1
    finally:
        remove_job(root)


def main():
    global EVENT_FILE
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', required=True)
    parser.add_argument('--gpu-wait', type=float, default=900)
    parser.add_argument('--timeout', type=float, default=21600)
    parser.add_argument('--events', action='store_true')
    args = parser.parse_args()
    root = Path(args.job).resolve().parent
    if root.parent != PC_ROOT or not root.name.startswith('hands-'):
        raise SystemExit('invalid job root')
    if args.events:
        EVENT_FILE = root / 'events.jsonl'
    (root / 'supervisor-ready').touch()
    try:
        code = supervise(root, gpu_wait=args.gpu_wait, timeout=args.timeout)
    except Exception as error:
        if root.exists():
            emit({'event': 'error', 'kind': 'transport', 'error': str(error)})
        code = 1
    raise SystemExit(code)


if __name__ == '__main__':
    main()
