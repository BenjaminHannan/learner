"""G8: owned driver for the English pilot workers (probe, train, eval). Stdlib only.

Steps: verify the config pin and the worker self-pin; check free disk; take the
GPU-BUSY marker (C:\\Users\\benja\\GPU-BUSY.txt, content "queue job <name>") or
stop with BUSY if it names any job; spawn the pinned worker with
--require-owned-stdin; accept only its own actual-worker-ready line (pid and
config sha), release it with the kind's GO line; stream stdout to a receipt
log; kill it at the whole-job wall cap; write DRIVER-CLOSED.json or
DRIVER-FAILED.json; remove the marker only if this driver created it and it is
unchanged.

Not replicated from the numeric Windows drivers: native job-object handles and
the shared SoleWorkerLock (launch-cap256/LOCK.json). Take that lock outside
this driver, per the existing operating procedure, if it is still required.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time

SCHEMA = 'premonition.English-pilot-driver.v1'
DEFAULT_MARKER = r'C:\Users\benja\GPU-BUSY.txt'
GO_LINES = {'probe': 'BEGIN ENGLISH ZERO UPDATE PROBE\n',
            'train': 'BEGIN ENGLISH PARAPHRASE PILOT\n',
            'eval': 'BEGIN ENGLISH FRESH EVAL\n'}
EXIT_BUSY = 3
READY_SECONDS = 900


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write_new_json(path, value):
    data = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    with Path(path).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


class MarkerBusy(Exception):
    pass


class GpuMarker:
    """Create the marker if absent; never overwrite or remove another job's marker."""
    def __init__(self, path, job):
        self.path, self.content, self.created = Path(path), 'queue job ' + job, False

    def acquire(self):
        try:
            with self.path.open('x', encoding='utf-8') as stream:
                stream.write(self.content)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            try:
                existing = self.path.read_text(encoding='utf-8').strip()
            except OSError:
                existing = '<unreadable>'
            raise MarkerBusy('GPU-BUSY marker present: ' + existing)
        self.created = True

    def release(self):
        if not self.created:
            return False
        try:
            if self.path.read_text(encoding='utf-8').strip() != self.content:
                return False  # changed by someone else: leave it
        except FileNotFoundError:
            self.created = False
            return False
        self.path.unlink()
        self.created = False
        return True


def reader_thread(stream, sink):
    for line in iter(stream.readline, ''):
        sink.put(line)
    sink.put(None)


def drive(args):
    started = time.monotonic()
    root = Path(args.root).resolve()
    cfgpath = Path(args.config).resolve()
    if not cfgpath.is_relative_to(root) or digest(cfgpath) != args.config_sha256:
        raise ValueError('owned config physical pin differs')
    cfg = json.loads(cfgpath.read_bytes())
    kind = cfg.get('kind')
    if kind not in GO_LINES or cfg.get('dispatch_allowed') is not True:
        raise ValueError('dispatch-allowed probe/train/eval config required')
    runner = cfg['runner']
    worker = (root / runner['path']).resolve()
    if not worker.is_relative_to(root) or not worker.is_file() or digest(worker) != runner['sha256']:
        raise ValueError('pinned worker bytes differ')
    budget = cfg['budget']
    if type(args.whole_job_seconds) is not int or not 0 < args.whole_job_seconds <= budget['worker_seconds'] + 900:
        raise ValueError('whole-job wall cap must not exceed the worker budget plus 900 s')
    if shutil.disk_usage(root).free < budget['retained_free_bytes']:
        raise RuntimeError('free disk below the retained reserve before launch')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = root / args.driver_namespace / ('%s-%s-%d-%s' % (kind, stamp, os.getpid(), os.urandom(3).hex()))
    marker = GpuMarker(args.gpu_busy_marker, args.job_name)
    try:
        marker.acquire()
    except MarkerBusy as busy:
        print(json.dumps({'event': 'BUSY', 'detail': str(busy)}), flush=True)
        return EXIT_BUSY
    child = None
    try:
        folder.mkdir(parents=True, exist_ok=False)
        command = [args.python, str(worker), '--root', str(root), '--config', str(cfgpath),
                   '--config-sha256', args.config_sha256, '--require-owned-stdin'] + list(args.worker_arg or [])
        write_new_json(folder / 'DRIVER-LAUNCH.json', {'schema': SCHEMA, 'kind': kind, 'command': command,
            'config_sha256': args.config_sha256, 'worker_sha256': runner['sha256'],
            'gpu_busy_marker': str(marker.path), 'job': args.job_name,
            'whole_job_seconds': args.whole_job_seconds, 'utc': stamp})
        with (folder / 'WORKER-STDERR.log').open('xb') as stderr:
            child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr,
                                     text=True, bufsize=1, cwd=str(root))
            lines = queue.Queue()
            threading.Thread(target=reader_thread, args=(child.stdout, lines), daemon=True).start()
            try:
                first = lines.get(timeout=min(READY_SECONDS, args.whole_job_seconds))
            except queue.Empty:
                raise RuntimeError('worker did not report ready in time')
            ready = json.loads(first) if first else {}
            if (ready.get('event') != 'actual-worker-ready' or ready.get('pid') != child.pid
                    or ready.get('config_sha256') != args.config_sha256):
                raise RuntimeError('worker ready line is not this direct child')
            child.stdin.write(GO_LINES[kind])
            child.stdin.flush()
            child.stdin.close()
            events, timed_out = [], False
            with (folder / 'WORKER-STDOUT.log').open('x', encoding='utf-8') as log:
                log.write(first)
                while True:
                    remaining = args.whole_job_seconds - (time.monotonic() - started)
                    if remaining <= 0:
                        timed_out = True
                        break
                    try:
                        line = lines.get(timeout=min(remaining, 5))
                    except queue.Empty:
                        if child.poll() is not None and lines.empty():
                            break
                        continue
                    if line is None:
                        break
                    log.write(line)
                    log.flush()
                    events.append(line.strip()[:2000])
            if timed_out:
                child.terminate()
                try:
                    child.wait(30)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                raise RuntimeError('whole-job wall cap reached; worker stopped, evidence preserved')
            code = child.wait()
        receipt = {'schema': SCHEMA, 'kind': kind, 'returncode': code, 'worker_pid': child.pid,
                   'wall_seconds': time.monotonic() - started, 'last_events': events[-20:],
                   'stdout_sha256': digest(folder / 'WORKER-STDOUT.log')}
        write_new_json(folder / ('DRIVER-CLOSED.json' if code == 0 else 'DRIVER-FAILED.json'), receipt)
        print(json.dumps({'event': 'english-driver-finished', 'returncode': code, 'folder': str(folder)}), flush=True)
        return code
    except Exception as exc:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait()
        if folder.is_dir() and not (folder / 'DRIVER-FAILED.json').exists():
            write_new_json(folder / 'DRIVER-FAILED.json', {'schema': SCHEMA, 'error': type(exc).__name__ + ': ' + str(exc),
                                                           'wall_seconds': time.monotonic() - started})
        raise
    finally:
        if child is not None:
            for stream in (child.stdin, child.stdout):
                try:
                    stream.close()
                except (OSError, ValueError):
                    pass
        marker.release()


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--config', required=True)
    p.add_argument('--config-sha256', required=True)
    p.add_argument('--python', default=sys.executable)
    p.add_argument('--job-name', default='english-paraphrase-pilot')
    p.add_argument('--gpu-busy-marker', default=DEFAULT_MARKER)
    p.add_argument('--driver-namespace', default='artifacts/cap256-launch/contextual-input-compare-v1/ENGLISH-PILOT-v1/DRIVER-RECEIPTS')
    p.add_argument('--whole-job-seconds', type=int, required=True)
    p.add_argument('--worker-arg', action='append', help='extra worker argument, e.g. --worker-arg=--resume')
    return drive(p.parse_args(argv))


if __name__ == '__main__':
    sys.exit(main())
