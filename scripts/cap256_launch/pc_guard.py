"""Decide whether a capability256 arm may start on BensPC.

Pure functions only (no process or GPU calls), so the rules are unit-tested on
the Mac. The driver gathers the process table and nvidia-smi rows and passes
them in.

Rules (why each exists):
- A process is *Premonition-owned* when it runs the Premonition venv
  interpreter, is a base-Python child of one, or its command line names the
  capability tree / runner / this launcher. Other Python apps (the reminder
  server, Manim) have their own interpreters and are never owned.
- BLOCK: another capability runner (a duplicate job). Other launcher drivers
  are allowed because only the holder of the single-run lock starts arms.
- BLOCK: any Premonition-owned process or local model server (llama-server,
  LM Studio, ...) holding the GPU.
- BLOCK: GPU memory already above the desktop baseline cap.
- WAIT then BLOCK: other Premonition-owned Python that stays alive. Short
  status probes vanish within seconds, so the driver re-checks before blocking.
- ALLOW and record: unrelated Python, desktop/UI GPU clients, unknown GPU
  clients (WDDM lists every windowed app; the memory cap guards capacity).
"""

PREMONITION_PYTHONS = (
    r'c:\users\benja\lis300\venv\scripts\python.exe',
    r'c:\users\benja\lis300\venv\scripts\pythonw.exe',
)
BASE_PYTHONS = (
    r'c:\users\benja\appdata\local\programs\python\python310\python.exe',
    r'c:\users\benja\appdata\local\programs\python\python310\pythonw.exe',
)
RUNNER_MARKS = ('sol_cloud_capability256_v1.py',)
DRIVER_MARK = 'pc_driver.py'  # PC path: launch-cap256\\pkg\\<commit>\\pc_driver.py
MODEL_SERVER_MARKS = ('llama-server', 'lm studio', 'lmstudio', 'ollama', 'vllm',
                      'text-generation', 'kobold', 'exllama', 'torchrun')
GPU_MEMORY_CAP_MIB = 3000


def norm(text):
    return str(text or '').replace('/', '\\').casefold()


def is_owned(proc, by_pid, root, _depth=0):
    exe = norm(proc.get('exe'))
    cmd = norm(proc.get('cmdline'))
    if exe in PREMONITION_PYTHONS:
        return True
    if norm(root) in cmd or DRIVER_MARK in cmd or any(mark in cmd for mark in RUNNER_MARKS):
        return True
    if exe in BASE_PYTHONS and _depth < 4:
        parent = by_pid.get(proc.get('ppid'))
        return parent is not None and is_owned(parent, by_pid, root, _depth + 1)
    return False


def is_runner_like(proc):
    cmd = norm(proc.get('cmdline'))
    return any(mark in cmd for mark in RUNNER_MARKS)


def lineage(pid, by_pid):
    seen = {pid}
    cursor = pid
    while cursor in by_pid:
        parent = by_pid[cursor].get('ppid')
        if not parent or parent in seen:
            break
        seen.add(parent)
        cursor = parent
    return seen


def summary(proc):
    return {'pid': proc.get('pid'), 'ppid': proc.get('ppid'), 'name': proc.get('name'),
            'exe': proc.get('exe'), 'cmdline': str(proc.get('cmdline') or '')[:400]}


def classify(procs, gpu_apps, gpu_rows, self_pid, root):
    """Return a decision dict. procs: all processes [{pid,ppid,name,exe,cmdline}].

    gpu_apps: [{pid, used_memory}] from --query-compute-apps.
    gpu_rows: [[index, util, mem_used_mib, mem_total_mib]].
    """
    by_pid = {p['pid']: p for p in procs}
    mine = lineage(self_pid, by_pid)
    block, wait, allowed = [], [], []

    for proc in procs:
        if proc['pid'] in mine:
            continue
        name = norm(proc.get('name'))
        if not name.startswith('python'):
            continue
        if is_runner_like(proc):
            block.append(dict(summary(proc), reason='duplicate capability runner process'))
        elif DRIVER_MARK in norm(proc.get('cmdline')):
            allowed.append(dict(summary(proc), reason='another launcher driver; it waits on the single-run lock'))
        elif is_owned(proc, by_pid, root):
            wait.append(dict(summary(proc), reason='Premonition Python still running (re-checked before blocking)'))
        else:
            allowed.append(dict(summary(proc), reason='unrelated Python app; left alone'))

    gpu_clients = []
    for app in gpu_apps:
        pid = app['pid']
        proc = by_pid.get(pid)
        entry = {'pid': pid, 'used_memory': app.get('used_memory'),
                 'name': proc.get('name') if proc else None}
        if pid in mine:
            continue
        if proc is not None and is_owned(proc, by_pid, root):
            block.append(dict(entry, reason='Premonition process holds the GPU'))
        elif proc is not None and any(m in norm(proc.get('name')) + ' ' + norm(proc.get('cmdline'))
                                      for m in MODEL_SERVER_MARKS):
            block.append(dict(entry, reason='local model server holds the GPU'))
        else:
            entry['reason'] = ('desktop/other GPU client; allowed' if proc is not None
                               else 'GPU client exited before lookup; allowed')
            gpu_clients.append(entry)

    if len(gpu_rows) != 1 or len(gpu_rows[0]) != 4:
        block.append({'reason': 'expected exactly one GPU row', 'gpu_rows': gpu_rows})
    elif gpu_rows[0][2] >= GPU_MEMORY_CAP_MIB:
        block.append({'reason': 'GPU memory in use %d MiB >= cap %d MiB' % (gpu_rows[0][2], GPU_MEMORY_CAP_MIB),
                      'gpu_rows': gpu_rows})

    return {'ok': not block and not wait, 'block': block, 'wait': wait,
            'allowed_python': allowed, 'gpu_clients': gpu_clients, 'gpu_rows': gpu_rows,
            'self_lineage': sorted(mine)}
