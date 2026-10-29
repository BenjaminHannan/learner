"""Bounded structural smoke, with durable public-day restart obligation."""
import datetime, hashlib, json, os, pathlib, signal, subprocess, sys, tempfile, time, urllib.request

PROJECT = pathlib.Path(__file__).resolve().parents[2]
OPS = pathlib.Path.home() / 'learner-ops'
RUN = OPS / 'assistant/run'
ROOT = pathlib.Path(tempfile.mkdtemp(prefix='premonition-private-native-', dir='/private/tmp'))
STATE = ROOT / 'restore-obligation.json'
LOG = ROOT / 'restore.log'

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(state):
    temporary = STATE.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(state, stream, indent=2); stream.flush(); os.fsync(stream.fileno())
    temporary.replace(STATE)
    fd = os.open(ROOT, os.O_RDONLY); os.fsync(fd); os.close(fd)
def command(pid):
    return subprocess.check_output(['/bin/ps', '-ww', '-p', str(pid), '-o', 'args='], text=True).strip()
def health(port):
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:%d/v1/models' % port, timeout=3) as response:
            data = json.load(response)
        return {'ok': True, 'aliases': [row['id'] for row in data['data']]}
    except Exception as error: return {'ok': False, 'error': type(error).__name__}
def diary():
    files = sorted(p for p in (OPS / 'diary').rglob('*') if p.is_file())
    rows = []
    for file in files:
        content = file.read_bytes()
        rows.append({'file': str(file.relative_to(OPS / 'diary')), 'bytes': len(content), 'lines': content.count(b'\n'), 'sha256': hashlib.sha256(content).hexdigest()})
    return {'files': len(rows), 'bytes': sum(row['bytes'] for row in rows), 'lines': sum(row['lines'] for row in rows), 'snapshots': rows}

day_pid = int((RUN / 'big.pid').read_text())
day_command = command(day_pid)
expected = '%s --model %s --alias lfm3 --host 127.0.0.1 --port 18080 -c 8192 -np 1 --jinja -ngl 99 --no-webui' % (OPS/'lfm3/llama.cpp/build/bin/llama-server', OPS/'lfm3/gguf/LFM3-1.7B-QAD-Q4_0.gguf')
if day_command != expected: raise RuntimeError('Public day command changed; refusing pause.')
state = {'version': 1, 'started': now(), 'root': str(ROOT), 'publicDayPidBefore': day_pid, 'publicDayCommand': day_command,
         'publicBefore': {str(port): health(port) for port in (18080,8090)}, 'diaryBefore': diary(),
         'restoreRequired': True, 'restartCommand': [str(OPS/'assistant/serve.sh'), '--autostart']}
if not all(value['ok'] for value in state['publicBefore'].values()): raise RuntimeError('Public service not healthy before smoke.')
save(state)
print(json.dumps({'root': str(ROOT), 'obligation': str(STATE)}), flush=True)
child = None
try:
    if command(day_pid) != day_command: raise RuntimeError('Public day ownership changed before pause.')
    os.kill(day_pid, signal.SIGTERM)
    for _ in range(100):
        try: os.kill(day_pid, 0)
        except ProcessLookupError: break
        time.sleep(.1)
    else: raise RuntimeError('Public day did not exit; private run skipped.')
    state['publicPaused'] = now(); save(state)
    with (ROOT/'controller.log').open('wb') as output:
        child = subprocess.Popen(['/usr/local/bin/node', str(PROJECT/'reviews/premonition-validation-20261029/private-real-smoke.cjs'), str(ROOT)],
                                 cwd=PROJECT, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
        state['controllerPid'] = child.pid; save(state)
        try: state['controllerExit'] = child.wait(timeout=420)
        except subprocess.TimeoutExpired:
            child.terminate(); state['controllerExit'] = child.wait(timeout=60)
finally:
    # Do not stack the public model onto an unconfirmed private engine. Leave
    # the durable obligation intact for owned-process diagnosis in that case.
    if child:
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                state['restoreBlocked'] = 'Private controller did not exit after cancellation.'
                save(state); raise RuntimeError(state['restoreBlocked'])
        check_path = ROOT/'check-audit.json'
        check = json.loads(check_path.read_text()) if check_path.exists() else {}
        if check.get('idleAfter', {}).get('processStopped') is not True:
            state['restoreBlocked'] = 'Private engine shutdown was not confirmed; do not stack models.'
            save(state); raise RuntimeError(state['restoreBlocked'])
    state['restoreAttempted'] = now(); save(state)
    with LOG.open('ab') as output:
        restored = subprocess.Popen(state['restartCommand'], cwd=str(OPS/'assistant'), start_new_session=True,
                                    stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
    state['restorePid'] = restored.pid; save(state)
    end = time.monotonic() + 150
    while time.monotonic() < end:
        probes = {str(port): health(port) for port in (18080,8090)}
        if all(value['ok'] and 'lfm3' in value['aliases'] for value in probes.values()):
            state['restoreRequired'] = False; break
        if restored.poll() is not None: time.sleep(1)
        else: time.sleep(2)
    state['publicAfter'] = probes
    state['publicDayPidAfter'] = int((RUN/'big.pid').read_text())
    state['diaryAfter'] = diary()
    state['diaryUnchanged'] = state['diaryBefore'] == state['diaryAfter']
    state['finished'] = now(); save(state)
    print(json.dumps({'root': str(ROOT), 'restoreRequired': state['restoreRequired'], 'publicAfter': probes, 'diaryUnchanged': state['diaryUnchanged']}), flush=True)
    if state['restoreRequired']: sys.exit(2)
