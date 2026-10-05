"""Run custom_io queue files on Ben's own machines (BensPC RTX 5070 Ti on Windows, the M1 Pro Mac on MPS). Python only,
so it needs no bash on Windows. Standard library + whatever custom_io itself needs (torch, numpy; transformers only for
hf: lines).

  python -m custom_io.local_runner setup --work WORK --curriculum DIR
      DIR holds the skills_curriculum package (branch claude/project-thread-y0sxwe). Builds WORK/data (200k seed-1 build,
      40 dev rows per cell) and WORK/data_big (same train rows, 200 dev rows per cell), checks every file hash against
      FULL-BUILD-MANIFEST-200k-seed1.json and that both builds share train.jsonl. Skips a build that already checks out.
  python -m custom_io.local_runner run --work WORK --queue custom_io/queue_local/30-name.txt [--device cuda|mps]
         [--par 3] [--busy C:/Users/benja/GPU-BUSY.txt] [--owner custom-io]
      Runs every line of the queue file, up to --par at a time, each only when the GPU has the line's memory free.

Queue file lines: `NAME args...` = one `python -m custom_io.train --data WORK/data --big-data WORK/data_big
--out WORK/results/QUEUE/NAME args...` run; `hf: NAME args...` = one `python -m custom_io.hf_baseline --data WORK/data
--out ... args...` run. `#` starts a comment; `# MEM 5000` sets the MiB a run needs free before it starts (default 5000;
a later `# MEM` line changes it for the lines after it). Args are split like a shell does (shlex), so keep the
single-quoted JSON of the Vast queue files. On MPS, --bf16 is dropped (bf16 autocast is cuda only) and --device mps is
added; a pairing is only fair between runs on the same device, so a queue file should not be split across machines.

A run whose RESULT.json already exists is skipped, so re-running the same queue resumes it. Each run trains from a frozen
copy of custom_io taken when the queue starts (WORK/code/QUEUE), so a later git pull never changes a running queue.
Outputs per run: RESULT.json, checkpoint.pt (kept; never deleted), stdout.txt, stdout.events.txt, rc.txt.
WORK/STOP (any content) stops new launches; running ones finish. The GPU-BUSY file gets one line per running run
(`owner queue/name pid start-utc`), removed when the run ends; other owners' lines are left alone and only free memory
decides whether a run can start, so two threads can share the card.
"""
import argparse
import datetime
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../custom_io
EVENT_KEYS = ('"event"', 'Traceback', 'Error', 'RESULT')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def say(*a):
    print(f'[{utc()}]', *a, flush=True)


def child_env(device):
    env = dict(os.environ, PYTHONUNBUFFERED='1', PYTHONUTF8='1', OMP_NUM_THREADS='2', TOKENIZERS_PARALLELISM='false',
               HF_HUB_DISABLE_PROGRESS_BARS='1', TRANSFORMERS_VERBOSITY='error')
    if device == 'mps':
        env['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    if device == 'cuda':
        env.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'expandable_segments:True')
    return env


# ---------------------------------------------------------------- setup

def _manifest_files(d):
    try:
        return json.load(open(Path(d) / 'manifest.json', encoding='utf-8'))['files_sha256']
    except (OSError, KeyError, ValueError):
        return None


def setup(a):
    work, cur = Path(a.work), Path(a.curriculum)
    ref = json.load(open(cur / 'skills_curriculum' / 'FULL-BUILD-MANIFEST-200k-seed1.json', encoding='utf-8'))['files_sha256']
    work.mkdir(parents=True, exist_ok=True)
    for name, per_cell in (('data', 40), ('data_big', 200)):
        out = work / name
        have = _manifest_files(out)
        ok = have is not None and (have == ref if name == 'data' else have.get('train.jsonl') == ref['train.jsonl'])
        if ok and (out / 'train.jsonl').exists():
            say(f'{name}: already built, hashes match')
            continue
        say(f'{name}: building (200k train rows, {per_cell} dev rows per cell, seed 1)')
        r = subprocess.run([sys.executable, '-m', 'skills_curriculum.build', '--out', str(out), '--train', '200000',
                            '--dev-per-cell', str(per_cell), '--seed', '1'], cwd=cur, env=child_env('cpu'))
        if r.returncode:
            sys.exit(f'{name}: build failed rc={r.returncode}')
        have = _manifest_files(out)
        if name == 'data' and have != ref:
            sys.exit('data: curriculum hash mismatch against FULL-BUILD-MANIFEST-200k-seed1.json')
        if name == 'data_big' and (have or {}).get('train.jsonl') != ref['train.jsonl']:
            sys.exit('data_big: train.jsonl differs from the reference build')
        say(f'{name}: built, hashes match')
    say('setup ok')


# ---------------------------------------------------------------- run

def free_mib(device):
    """free GPU memory in MiB (cuda via nvidia-smi), or None when it cannot be read (then memory does not gate)."""
    if device != 'cuda':
        return None
    try:
        out = subprocess.run(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
                             capture_output=True, text=True, timeout=30).stdout
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def parse_queue(path):
    """-> [(name, kind 'train'|'hf', args list, mem MiB)]"""
    runs, mem, seen = [], 5000, set()
    for raw in open(path, encoding='utf-8'):
        line = raw.strip()
        if not line:
            continue
        if line.startswith('#'):
            parts = line[1:].split()
            if len(parts) == 2 and parts[0] == 'MEM' and parts[1].isdigit():
                mem = int(parts[1])
            continue
        kind = 'train'
        if line.startswith('hf:'):
            kind, line = 'hf', line[3:].strip()
        toks = shlex.split(line)
        name, args = toks[0], toks[1:]
        if name in seen:
            sys.exit(f'duplicate run name {name} in {path}')
        seen.add(name)
        runs.append((name, kind, args, mem))
    return runs


def command(kind, args, work, out, device):
    args = list(args)
    if device != 'cuda':
        args = [x for x in args if x != '--bf16']
    if device in ('mps', 'cpu') and '--device' not in args:
        args += ['--device', device]
    if kind == 'hf':
        return [sys.executable, '-m', 'custom_io.hf_baseline', '--data', str(work / 'data'), '--out', str(out)] + args
    return [sys.executable, '-m', 'custom_io.train', '--data', str(work / 'data'), '--big-data', str(work / 'data_big'),
            '--out', str(out)] + args


class Busy:
    """one line per running run in the shared GPU-BUSY file; only our own lines are ever removed."""

    def __init__(self, path, owner):
        self.path, self.owner = (Path(path) if path else None), owner

    def _rewrite(self, keep):
        lines = []
        if self.path.exists():
            lines = [ln for ln in self.path.read_text(encoding='utf-8', errors='replace').splitlines() if keep(ln)]
        if lines:
            self.path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        elif self.path.exists():
            self.path.unlink()

    def add(self, tag, pid):
        if self.path:
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write(f'{self.owner} {tag} {pid} {utc()}\n')

    def remove(self, tag):
        if self.path:
            self._rewrite(lambda ln: not ln.startswith(f'{self.owner} {tag} '))


def summary_line(out):
    try:
        r = json.load(open(out / 'RESULT.json', encoding='utf-8'))
    except (OSError, ValueError):
        return 'no RESULT.json'
    fe = r.get('final_eval') or {}
    pick = {s: round(fe[s]['exact'], 2) for s in ('in_dist', 'answer', 'frame', 'vocab', 'variant') if s in fe}
    c5 = ((r.get('chain5') or {}).get('intact') or {}).get('exact')
    return json.dumps(dict(status=r.get('status'), steps=r.get('steps'), steps_per_s=round(r.get('steps_per_s') or 0, 2),
                           chain5=c5, **pick))


def finish(out):
    try:
        with open(out / 'stdout.txt', encoding='utf-8', errors='replace') as f, \
                open(out / 'stdout.events.txt', 'w', encoding='utf-8') as g:
            for ln in f:
                if any(k in ln for k in EVENT_KEYS):
                    g.write(ln[:4000].rstrip('\n') + '\n')
    except OSError:
        pass


def run(a):
    work, qpath = Path(a.work).resolve(), Path(a.queue).resolve()
    qname = qpath.stem
    runs = parse_queue(qpath)
    device = a.device
    res = work / 'results' / qname
    res.mkdir(parents=True, exist_ok=True)
    code = work / 'code' / qname
    if not (code / 'custom_io').exists():         # frozen copy, taken once per queue
        shutil.copytree(HERE, code / 'custom_io', ignore=shutil.ignore_patterns('results', '__pycache__', '*.pt'))
    shutil.copy2(qpath, res / qpath.name)
    busy = Busy(a.busy, a.owner)
    todo = [x for x in runs if not (res / x[0] / 'RESULT.json').exists()]
    say(f'queue {qname}: {len(runs)} runs, {len(runs) - len(todo)} already done, device {device}, par {a.par}')
    active = {}                                    # name -> (Popen, out, start)
    try:
        while todo or active:
            for name, (p, out, t0) in list(active.items()):
                if p.poll() is not None:
                    (out / 'rc.txt').write_text(f'rc={p.returncode}\n', encoding='utf-8')
                    finish(out)
                    busy.remove(f'{qname}/{name}')
                    del active[name]
                    say(f'END {name} rc={p.returncode} {round((time.time() - t0) / 60, 1)} min {summary_line(out)}')
            stop = (work / 'STOP').exists()
            while todo and not stop and len(active) < a.par:
                name, kind, args, mem = todo[0]
                f = free_mib(device)
                if f is not None and f < mem:
                    break
                todo.pop(0)
                out = res / name
                out.mkdir(parents=True, exist_ok=True)
                cmd = command(kind, args, work, out, device)
                (out / 'cmd.txt').write_text(' '.join(shlex.quote(c) for c in cmd) + '\n', encoding='utf-8')
                p = subprocess.Popen(cmd, cwd=code, env=child_env(device), stdout=open(out / 'stdout.txt', 'w', encoding='utf-8'),
                                     stderr=subprocess.STDOUT)
                busy.add(f'{qname}/{name}', p.pid)
                active[name] = (p, out, time.time())
                say(f'START {name} pid {p.pid} (free {f} MiB, need {mem}; running {len(active)})')
                time.sleep(a.gap)                  # let it allocate before the next free-memory reading
            if stop and todo and not active:
                say(f'STOP file present: {len(todo)} runs not started')
                break
            time.sleep(a.poll)
    finally:
        for name in list(active):
            busy.remove(f'{qname}/{name}')
    say(f'queue {qname} done')
    for name, *_ in runs:
        say(f'  {name}: {summary_line(res / name)}')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('setup')
    s.add_argument('--work', required=True)
    s.add_argument('--curriculum', required=True, help='dir that contains the skills_curriculum package')
    r = sub.add_parser('run')
    r.add_argument('--work', required=True)
    r.add_argument('--queue', required=True)
    r.add_argument('--device', choices=['cuda', 'mps', 'cpu'], default='cuda')
    r.add_argument('--par', type=int, default=3)
    r.add_argument('--busy', help='shared GPU-BUSY file (one line per running run)')
    r.add_argument('--owner', default='custom-io')
    r.add_argument('--poll', type=float, default=20)
    r.add_argument('--gap', type=float, default=60, help='seconds between launches')
    a = ap.parse_args(argv)
    {'setup': setup, 'run': run}[a.cmd](a)


if __name__ == '__main__':
    main()
