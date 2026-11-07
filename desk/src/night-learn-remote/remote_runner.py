#!/usr/bin/env python3
"""Gated, leased CUDA training with verified quarantine return and local fallback."""
import argparse
import base64
import datetime
import hashlib
import json
import math
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HOME = Path.home()
SELF = Path(__file__).resolve().parent
DESK = SELF.parents[1]
NIGHT = DESK / 'src/night-learn'
POLICY = DESK / 'tools/hands-toy/policy.py'
GYM_GATE = DESK / 'src/hands-gym/hands_gym/gpu_gate.py'
P2PY = HOME / 'learner-ops/p2venv/bin/python'
STOP_FILE = HOME / 'learner-ops/aon-notes/hands-20261106/STOP-TRAINING'
FALLBACK_LOG = HOME / 'learner-ops/night-learn-remote/fallback.log'
HOST = 'benspc-lan'
TAILSCALE_HOST = 'benspc'
PC_ROOT = 'C:/Users/benja/hands-train'
PC_LEASE_ROOT = 'C:/Users/benja/hands-gym'
PC_PYTHON = r'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
PERMIT_SECONDS = 60
GPU_WAIT_SECONDS = 900
TRAIN_TIMEOUT_SECONDS = 6 * 3600
MODEL_NAMES = ('old', 'candidate', 'no-intent')


class RemoteUnavailable(RuntimeError):
    """A recoverable host, lease or transport failure."""


class RemoteBusy(RemoteUnavailable):
    """The same PC is busy on both network routes; do not repeat its lease wait."""


class CudaFailure(RuntimeError):
    """CUDA failure: stop, never silently fall back."""


class InputError(RuntimeError):
    """Invalid evidence: never upload or fall back."""


def log(message):
    print(f'[{datetime.datetime.now().astimezone().isoformat()}] {message}', file=sys.stderr, flush=True)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def mac_idle_seconds():
    if sys.platform != 'darwin':
        raise RuntimeError('Mac idle check unavailable')
    import ctypes
    core = ctypes.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
    core.CGEventSourceSecondsSinceLastEventType.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
    core.CGEventSourceSecondsSinceLastEventType.restype = ctypes.c_double
    return core.CGEventSourceSecondsSinceLastEventType(1, 0xffffffff)


def check_stop(stop_file=None):
    if Path(STOP_FILE if stop_file is None else stop_file).exists():
        raise RuntimeError('training stopped')


def real_gate(now=None, idle=None, stop_file=None):
    now = now or datetime.datetime.now().astimezone()
    idle = mac_idle_seconds() if idle is None else idle
    if not 1 <= now.hour < 7 or not math.isfinite(idle) or idle < 1200:
        raise RuntimeError('training deferred: requires 01:00–07:00 and 20 minutes of Mac idle')
    check_stop(stop_file)
    return idle


def gate_for(synthetic):
    return check_stop if synthetic else real_gate


def local_python():
    return P2PY if P2PY.exists() else Path(sys.executable)


def audit(command, process, source=None):
    destination = os.environ.get('HANDS_REMOTE_AUDIT')
    if destination:
        with open(destination, 'a', encoding='utf8') as handle:
            handle.write(json.dumps({'at': datetime.datetime.now().astimezone().isoformat(),
                                     'command': command, 'exitCode': process.returncode,
                                     'stdout': process.stdout, 'stderr': process.stderr,
                                     'stdin': source}) + '\n')


def command_run(command, *, timeout=120, source=None):
    try:
        process = subprocess.run(command, input=source, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as error:
        raise RemoteUnavailable(f'{command[0]} failed: {error}') from error
    audit(command, process, source)
    if process.returncode:
        raise RemoteUnavailable(f'{command[0]} exit {process.returncode}: {process.stderr[-1500:]}')
    return process


def ssh_command(host, script):
    encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    return ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
            '-o', 'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=2', host,
            f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {encoded}']


def host_candidates(host):
    return (HOST, TAILSCALE_HOST) if host == HOST else (host,)


def ssh_python(host, code, timeout=30):
    script = f"$ProgressPreference='SilentlyContinue'; & '{PC_PYTHON}' -; exit $LASTEXITCODE"
    return command_run(ssh_command(host, script), timeout=timeout, source=code)


def pc_preflight(host, timeout=30):
    source = '''import importlib.metadata, json, pathlib, shutil, sys
import winreg
pending = False
try:
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired"):
        pending = True
except FileNotFoundError:
    pass
print(json.dumps({"python":sys.version.split()[0], "torch":importlib.metadata.version("torch"),
                  "rebootRequired":pending, "freeBytes":shutil.disk_usage("C:/").free,
                  "sharedLeaseRootExists":pathlib.Path("C:/Users/benja/hands-gym").is_dir()}))
'''
    process = ssh_python(host, source, timeout=timeout)
    try:
        status = json.loads(process.stdout.strip())
    except ValueError as error:
        raise RemoteUnavailable('PC preflight returned invalid JSON') from error
    if not status.get('sharedLeaseRootExists'):
        raise RemoteUnavailable('shared hands-gym GPU lease directory is unavailable')
    if status.get('freeBytes', 0) < 1024 ** 3:
        raise RemoteUnavailable('BensPC has less than 1 GiB free')
    return status


def new_job_id():
    return f'hands-{datetime.datetime.now():%Y%m%d-%H%M%S}-{os.urandom(4).hex()}'


def pack_job(dataset_path, workdir, job_id, *, steps, batch_size, lr, checkpoint_every=10):
    data = json.loads(Path(dataset_path).read_text(encoding='utf8'))
    rows = data.get('examples')
    if not isinstance(rows, list) or not rows:
        raise InputError('dataset has no examples')
    job_root = Path(workdir) / 'job'
    for relative in ('src/night-learn', 'tools/hands-toy', 'frames'):
        (job_root / relative).mkdir(parents=True, exist_ok=True)
    sources = {'src/night-learn/trainer.py': NIGHT / 'trainer.py',
               'src/night-learn/pixel_model.py': NIGHT / 'pixel_model.py',
               'tools/hands-toy/policy.py': POLICY, 'src/gpu_gate.py': GYM_GATE,
               'src/resource.py': SELF / 'windows_resource.py'}
    for name in ('train_core.py', 'train_remote.py', 'supervise_remote.py'):
        sources['src/' + name] = SELF / name
    for relative, source in sources.items():
        shutil.copy2(source, job_root / relative)
    packed_rows = []
    for index, row in enumerate(rows):
        if row.get('verified') is not True:
            raise InputError(f'unverified example {index}')
        frame = Path(row.get('frame', ''))
        if not frame.is_absolute() or not frame.is_file():
            raise InputError(f'example {index} requires an existing absolute frame path')
        expected = row.get('frameFileSha256')
        if not isinstance(expected, str) or sha256_file(frame) != expected:
            raise InputError(f'example {index} frame hash missing or changed')
        relative = f'frames/{expected}.png'
        shutil.copy2(frame, job_root / relative)
        if sha256_file(job_root / relative) != expected:
            raise InputError(f'example {index} changed while packing')
        packed_rows.append(dict(row, frame=f'{PC_ROOT}/{job_id}/{relative}'))
    previous = data.get('preSleepWeights')
    if previous:
        if not Path(previous).is_file():
            raise InputError('preSleepWeights checkpoint is missing')
        shutil.copy2(previous, job_root / 'starting.pt')
    validation = f'''import json, pathlib, sys, torch
sys.path.insert(0, {str(job_root / 'src/night-learn')!r})
import trainer
data=json.loads(pathlib.Path({str(dataset_path)!r}).read_text())
rows=data['examples']
if not (data.get('allowSparse') and (len(rows)<2 or len({{row['timeMs'] for row in rows}})<2)):
    trainer.partition(rows,data['startMs'],data['endMs'])
for row in rows:
    trainer.load_example(row)
torch.manual_seed(101)
net=trainer.pixel_model.NativeActionPolicy()
target=pathlib.Path({str(job_root / 'starting.pt')!r})
if target.exists():
    net.load_state_dict(torch.load(target,map_location='cpu',weights_only=True),strict=True)
else:
    torch.save(net.state_dict(),target)
'''
    result = subprocess.run([str(local_python()), '-c', validation], capture_output=True, text=True)
    audit([str(local_python()), '-c', validation], result)
    if result.returncode:
        raise InputError(f'dataset/checkpoint validation failed: {result.stderr[-2000:]}')
    dataset = dict(data, examples=packed_rows)
    if previous:
        dataset['preSleepWeights'] = f'{PC_ROOT}/{job_id}/starting.pt'
    file_hashes = {str(file.relative_to(job_root)).replace(os.sep, '/'): sha256_file(file)
                   for file in job_root.rglob('*') if file.is_file() and '__pycache__' not in file.parts}
    for cache in job_root.rglob('__pycache__'):
        shutil.rmtree(cache)
    manifest = {'version': 1, 'jobId': job_id, 'dataset': dataset,
                'config': {'steps': steps, 'batchSize': batch_size, 'lr': lr, 'seed': 101,
                           'checkpointEvery': checkpoint_every, 'leaseRoot': PC_LEASE_ROOT},
                'inputSha256': {'dataset': canonical_sha(dataset), 'files': file_hashes}}
    (job_root / 'job.json').write_text(json.dumps(manifest) + '\n', encoding='utf8')
    return job_root, manifest


def permit_code(remote_dir, create=False):
    return f'''import json, os, pathlib, time
root=pathlib.Path({remote_dir!r})
{("root.mkdir(parents=True,exist_ok=True)" if create else "assert root.is_dir(), 'job no longer exists'")}
temp=root/'permit.tmp'
temp.write_text(json.dumps({{"expiresAt":time.time()+{PERMIT_SECONDS}}}))
os.replace(temp,root/'permit.json')
'''


def pc_cleanup(host, remote_dir):
    source = f'''import json, pathlib, shutil
root=pathlib.Path({remote_dir!r})
assert root.parent==pathlib.Path({PC_ROOT!r}) and root.name.startswith('hands-')
shutil.rmtree(root) if root.exists() else None
print(json.dumps({{"deleted":not root.exists(),"path":str(root)}}))
'''
    process = ssh_python(host, source)
    receipt = json.loads(process.stdout.strip())
    if receipt.get('deleted') is not True:
        raise RuntimeError(f'PC cleanup failed: {remote_dir}')
    return receipt


def scp_upload(host, local_dir, remote_dir, gate=lambda: None):
    command = ['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-r',
               str(local_dir) + '/.', f'{host}:{remote_dir}/']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + 600
    next_heartbeat = 0
    try:
        while time.monotonic() < deadline:
            gate()
            if time.monotonic() >= next_heartbeat:
                ssh_python(host, permit_code(remote_dir), timeout=20)
                next_heartbeat = time.monotonic() + 10
            try:
                stdout, stderr = process.communicate(timeout=1)
                audit(command, subprocess.CompletedProcess(command, process.returncode, stdout, stderr))
                if process.returncode:
                    raise RemoteUnavailable(f'upload exit {process.returncode}: {stderr[-1000:]}')
                return
            except subprocess.TimeoutExpired:
                continue
        raise RemoteUnavailable('upload timed out')
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


def start_supervisor(host, remote_dir, job_root, *, gpu_wait, timeout):
    ssh_python(host, f"from pathlib import Path; Path({remote_dir!r}, 'src').mkdir()")
    command_run(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                 str(job_root / 'src/supervise_remote.py'), str(job_root / 'src/gpu_gate.py'),
                 f'{host}:{remote_dir}/src/'], timeout=60)
    source = f'''import json, pathlib, subprocess, sys, time
root=pathlib.Path({remote_dir!r})
command=[sys.executable, '-u', str(root/'src/supervise_remote.py'), '--job', str(root/'job.json'),
         '--gpu-wait', {str(gpu_wait)!r}, '--timeout', {str(timeout)!r}, '--events']
worker=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,close_fds=True,
                        creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB)
(root/'supervisor.json').write_text(json.dumps({{"pid":worker.pid}}))
deadline=time.monotonic()+10
while not (root/'supervisor-ready').exists():
    if worker.poll() is not None or time.monotonic()>deadline:
        raise RuntimeError('cleanup supervisor failed before any frame upload')
    time.sleep(0.1)
print(json.dumps({{"supervisorPid":worker.pid}}))
'''
    return json.loads(ssh_python(host, source).stdout)


def cancel_supervisor(host, remote_dir):
    source = f'''import json, pathlib, time
root=pathlib.Path({remote_dir!r})
if root.exists():
    (root/'cancel').touch()
deadline=time.monotonic()+40
while root.exists() and time.monotonic()<deadline:
    time.sleep(0.5)
print(json.dumps({{"deleted":not root.exists(),"path":str(root)}}))
raise SystemExit(0 if not root.exists() else 1)
'''
    return json.loads(ssh_python(host, source, timeout=45).stdout)


def cleanup_after_failure(host, remote_dir, supervised, logger=log):
    hosts = host_candidates(host)
    if host == TAILSCALE_HOST:
        hosts = (TAILSCALE_HOST, HOST)
    errors = []
    for cleanup_host in hosts:
        try:
            cleanup = (cancel_supervisor(cleanup_host, remote_dir) if supervised else
                       pc_cleanup(cleanup_host, remote_dir))
            if cleanup.get('deleted') is not True:
                raise RuntimeError('PC deletion was not confirmed')
            logger(f'PC failure-path cleanup confirmed via {cleanup_host}: {cleanup}')
            return cleanup
        except Exception as error:
            errors.append(f'{cleanup_host}: {error}')
            logger(f'PC cleanup unavailable via {cleanup_host}: {error}')
    raise RuntimeError('; '.join(errors))


def scp_download(host, remote_file, local_file):
    command_run(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                 f'{host}:{remote_file}', str(local_file)], timeout=180)


def read_lines(process, messages):
    try:
        for line in process.stdout:
            messages.put(line)
    finally:
        messages.put(None)


def stream_remote(host, remote_dir, *, timeout, gpu_wait, gate, logger=log):
    source = f'''import pathlib, sys, time
root=pathlib.Path({remote_dir!r})
offset=0
while root.exists():
    file=root/'events.jsonl'
    if file.exists():
        with file.open(encoding='utf8') as handle:
            handle.seek(offset)
            lines=handle.readlines()
            offset=handle.tell()
        for line in lines:
            print(line,end='',flush=True)
            if '"event": "done"' in line or '"event": "error"' in line:
                sys.exit(0)
    time.sleep(0.5)
'''
    script = f"$ProgressPreference='SilentlyContinue'; & '{PC_PYTHON}' -; exit $LASTEXITCODE"
    command = ssh_command(host, script)
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, bufsize=1)
    process.stdin.write(source)
    process.stdin.close()
    messages = queue.Queue()
    threading.Thread(target=read_lines, args=(process, messages), daemon=True).start()
    deadline = time.monotonic() + timeout + gpu_wait + 90
    next_heartbeat = 0
    transcript = []
    try:
        while time.monotonic() < deadline:
            gate()
            if time.monotonic() >= next_heartbeat:
                ssh_python(host, permit_code(remote_dir), timeout=20)
                next_heartbeat = time.monotonic() + 10
            try:
                line = messages.get(timeout=1)
            except queue.Empty:
                continue
            if line is None:
                raise RemoteUnavailable(f'PC worker stream closed: {transcript[-5:]}')
            transcript.append(line.rstrip())
            try:
                event = json.loads(line)
            except ValueError:
                logger('pc: ' + line.rstrip())
                continue
            kind = event.get('event')
            if kind == 'done':
                audit(command, subprocess.CompletedProcess(command, 0, '\n'.join(transcript), ''), source)
                return event, process
            if kind == 'error':
                error = f"BensPC {event.get('kind')}: {event.get('error')}"
                if event.get('kind') == 'cuda':
                    raise CudaFailure(error)
                if event.get('kind') == 'busy':
                    raise RemoteBusy(error)
                if event.get('kind') in ('transport', 'timeout'):
                    raise RemoteUnavailable(error)
                raise RuntimeError(error)
            if kind != 'progress' or event.get('step', 0) % 25 == 0:
                logger('pc: ' + line.rstrip())
        raise RemoteUnavailable('PC worker timed out')
    except BaseException:
        try:
            cancel_supervisor(host, remote_dir)
            process.wait(timeout=10)
        except (RemoteUnavailable, subprocess.TimeoutExpired):
            logger('PC cancel not acknowledged; supervisor expires its permit within 60 seconds')
        if process.poll() is None:
            process.kill()
            process.wait()
        audit(command, subprocess.CompletedProcess(command, process.returncode, '\n'.join(transcript), ''), source)
        raise


def download_outputs(host, remote_dir, local_dir, done):
    Path(local_dir).mkdir()
    hashes = {}
    for name in (*MODEL_NAMES, 'result'):
        extension = '.json' if name == 'result' else '.pt'
        file = Path(local_dir) / (name + extension)
        scp_download(host, f'{remote_dir}/out/{file.name}', file)
        expected = done['resultSha256'] if name == 'result' else done['modelSha256'][name]
        hashes[name] = sha256_file(file)
        if hashes[name] != expected:
            raise RemoteUnavailable(f'returned {file.name} SHA256 mismatch')
    return {name: hashes[name] for name in MODEL_NAMES}


def cpu_benchmark(job_root, dataset_path, config, bench_steps, gate=lambda: None):
    if not bench_steps:
        return None
    import torch
    sys.path[:0] = [str(Path(job_root) / 'src'), str(Path(job_root) / 'src/night-learn')]
    import train_core
    import trainer
    data = json.loads(Path(dataset_path).read_text())
    rows, _, _ = trainer.partition(data['examples'], data['startMs'], data['endMs'])
    cache = train_core.preload(rows, trainer.load_example)
    torch.manual_seed(config['seed'])
    net = trainer.pixel_model.NativeActionPolicy()
    net.load_state_dict(torch.load(Path(job_root) / 'starting.pt', map_location='cpu', weights_only=True))
    curve, times = train_core.fit(net, cache, torch.device('cpu'), trainer.pixel_model,
                                  steps=bench_steps, batch_size=config['batchSize'],
                                  lr=config['lr'], seed=config['seed'], gate=gate)
    return {'device': 'mac-cpu', 'threads': torch.get_num_threads(), 'torch': torch.__version__,
            'batchSize': config['batchSize'], 'seed': config['seed'],
            'stepTime': train_core.timing_summary(times), 'lossCurve': curve,
            'comparison': 'same initial weights, frames, weighted sampled batches, AdamW and loss'}


def run_remote(dataset_path, output, *, synthetic, steps, batch_size, lr, host=HOST,
               gpu_wait=GPU_WAIT_SECONDS, timeout=TRAIN_TIMEOUT_SECONDS, bench_steps=0,
               logger=log, gate=None):
    gate = gate or gate_for(synthetic)
    gate()
    status = pc_preflight(host)
    logger(f'PC reachable via {host} (no CUDA context created): {status}')
    if status.get('rebootRequired'):
        logger('Pending-reboot flag: not an active reboot; saving both arms every 10 steps')
    job_id = new_job_id()
    remote_dir = f'{PC_ROOT}/{job_id}'
    process = None
    uploaded = False
    supervised = False
    with tempfile.TemporaryDirectory(prefix='hands-remote-') as temporary:
        job_root, manifest = pack_job(dataset_path, temporary, job_id, steps=steps,
                                      batch_size=batch_size, lr=lr)
        gate()
        try:
            uploaded = True
            ssh_python(host, permit_code(remote_dir, create=True))
            supervisor = start_supervisor(host, remote_dir, job_root, gpu_wait=gpu_wait, timeout=timeout)
            supervised = True
            logger(f'Independent cleanup supervisor started before frames: {supervisor}')
            scp_upload(host, job_root, remote_dir, gate)
            gate()
            ssh_python(host, permit_code(remote_dir))
            ssh_python(host, f"from pathlib import Path; Path({remote_dir!r}, 'upload-ready').touch()")
            done, process = stream_remote(host, remote_dir, timeout=timeout, gpu_wait=gpu_wait,
                                           gate=gate, logger=logger)
            gate()
            download_dir = Path(temporary) / 'download'
            local_sha = download_outputs(host, remote_dir, download_dir, done)
            result = json.loads((download_dir / 'result.json').read_text())
            if result['modelSha256'] != local_sha:
                raise RuntimeError('result manifest disagrees with verified checkpoint hashes')
            gate()
            cleanup = pc_cleanup(host, remote_dir)
            process.wait(timeout=15)
            process.stdout.close()
            logger(f'PC job folder deleted: {cleanup}')
            gate()
            benchmark = cpu_benchmark(job_root, dataset_path, manifest['config'], bench_steps, gate)
            gate()
            output = Path(output)
            output.mkdir(parents=True, exist_ok=True, mode=0o700)
            for name in MODEL_NAMES:
                temporary_file = output / (name + '.tmp')
                shutil.copy2(download_dir / (name + '.pt'), temporary_file)
                os.chmod(temporary_file, 0o600)
                os.replace(temporary_file, output / (name + '.pt'))
            result['trainingBackend'] = 'benspc-gpu'
            result['remote']['benchmark'] = benchmark
            result['remote']['transport'] = {
                'host': host, 'jobId': job_id, 'remoteDir': remote_dir,
                'inputSha256': manifest['inputSha256'], 'inputsVerified': done['inputsVerified'],
                'outputSha256': {'remote': done['modelSha256'], 'local': local_sha},
                'resultSha256': {'remote': done['resultSha256'],
                                 'local': sha256_file(download_dir / 'result.json')},
                'pcCleanup': cleanup, 'preflight': status, 'eventStreamExitCode': process.returncode,
                'workerExitCode': done['workerExitCode'], 'sharedLeaseReleased': done['leaseReleased']}
            result['remote']['transport']['supervisor'] = supervisor
            (output / 'remote-result.json').write_text(json.dumps(result, indent=2) + '\n')
            os.chmod(output / 'remote-result.json', 0o600)
            return result
        except BaseException as error:
            if uploaded:
                try:
                    cleanup_after_failure(host, remote_dir, supervised, logger)
                except Exception as cleanup_error:
                    raise RuntimeError(f'Cleanup unconfirmed for {remote_dir}; watchdog will expire. '
                                       f'No local fallback permitted: {cleanup_error}; original: {error}') from error
            raise
        finally:
            if process is not None:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stdout.close()


def run_local(dataset_path, output, *, steps=None, logger=log):
    data = json.loads(Path(dataset_path).read_text())
    command = [str(local_python()), str(SELF / 'train_local.py')]
    if data.get('synthetic') is True:
        command.append('--synthetic')
    command += ['--steps', str(steps or data.get('trainingSteps', 100)), str(dataset_path), str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    audit(command, result)
    if result.returncode:
        raise RuntimeError(f'local training failed: {result.stderr[-2000:]}')
    logger('Local Mac training complete; candidate remains quarantined')
    return json.loads(result.stdout)


def append_fallback(reason, dataset_path, output, hosts_tried=None):
    FALLBACK_LOG.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    entry = {'at': datetime.datetime.now().astimezone().isoformat(), 'reason': str(reason),
             'dataset': str(dataset_path), 'output': str(output)}
    if hosts_tried is not None:
        entry['hostsTried'] = hosts_tried
    with open(FALLBACK_LOG, 'a', encoding='utf8') as handle:
        handle.write(json.dumps(entry) + '\n')
    os.chmod(FALLBACK_LOG, 0o600)
    return entry


def run(dataset_path, output, *, synthetic=None, steps=None, batch_size=8, lr=0.0005,
        host=HOST, gpu_wait=GPU_WAIT_SECONDS, timeout=TRAIN_TIMEOUT_SECONDS,
        bench_steps=0, force_local=False, no_fallback=False, remote_fn=None,
        local_fn=None, logger=log):
    try:
        data = json.loads(Path(dataset_path).read_text(encoding='utf8'))
        is_synthetic = data.get('synthetic') is True
        steps = steps if steps is not None else data.get('trainingSteps', 100)
        if synthetic and not is_synthetic:
            raise InputError('--synthetic cannot bypass the real-recording gate; dataset must be synthetic')
        if type(steps) is not int or not 1 <= steps <= 20000 or not 1 <= batch_size <= 64:
            raise InputError('invalid steps or batch size')
        if not 0 < lr <= 0.01 or not math.isfinite(lr) or not 0 <= gpu_wait <= 900:
            raise InputError('invalid learning rate or GPU wait (maximum 900 seconds)')
    except (OSError, ValueError, AttributeError) as error:
        raise InputError(f'unreadable dataset: {error}') from error
    gate_for(is_synthetic)()
    remote_fn = remote_fn or run_remote
    local_fn = local_fn or (lambda data, out: run_local(data, out, steps=steps, logger=logger))
    if force_local:
        result = local_fn(str(dataset_path), str(output))
        result['trainingBackend'] = 'mac-cpu-forced'
        return result
    hosts_tried = []
    last_error = None
    for remote_host in host_candidates(host):
        gate_for(is_synthetic)()
        hosts_tried.append(remote_host)
        logger(f'Trying PC host {remote_host}')
        try:
            result = remote_fn(str(dataset_path), str(output), synthetic=is_synthetic,
                               steps=steps, batch_size=batch_size, lr=lr, host=remote_host,
                               gpu_wait=gpu_wait, timeout=timeout, bench_steps=bench_steps, logger=logger)
        except RemoteUnavailable as error:
            last_error = error
            logger(f'PC host {remote_host} unavailable: {error}')
            if isinstance(error, RemoteBusy):
                break
            continue
        result['trainingBackend'] = 'benspc-gpu'
        result.setdefault('remote', {}).update(fallback=False, selectedHost=remote_host,
                                              hostsTried=hosts_tried)
        logger(f'PC training completed via {remote_host}; no local fallback')
        return result
    if no_fallback:
        raise last_error
    logger(f'PC unavailable via {hosts_tried}; local fallback: {last_error}')
    entry = append_fallback(last_error, dataset_path, output, hosts_tried)
    gate_for(is_synthetic)()
    result = local_fn(str(dataset_path), str(output))
    result.update(trainingBackend='mac-cpu-fallback', fallbackReason=str(last_error),
                  fallbackLoggedAt=entry['at'])
    result.setdefault('remote', {}).update(fallback=True, hostsTried=hosts_tried)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset_path')
    parser.add_argument('output')
    parser.add_argument('--synthetic', action='store_true', default=None)
    parser.add_argument('--force-local', action='store_true')
    parser.add_argument('--no-fallback', action='store_true')
    parser.add_argument('--steps', type=int)
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--lr', type=float, default=0.0005)
    parser.add_argument('--host', default=HOST)
    parser.add_argument('--gpu-wait', type=int, default=GPU_WAIT_SECONDS)
    parser.add_argument('--timeout', type=int, default=TRAIN_TIMEOUT_SECONDS)
    parser.add_argument('--bench-steps', type=int, default=0)
    print(json.dumps(run(**vars(parser.parse_args()))))


if __name__ == '__main__':
    main()
