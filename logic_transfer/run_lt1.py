"""LT-1 driver: builds the job list and runs it (K jobs in parallel, T threads each, dependency-aware, resumable).

  python -m logic_transfer.run_lt1 plan [--plan lt1|gate|screen] [--far] [--out jobs.json]   write the job list (JSON)
  python -m logic_transfer.run_lt1 run  [--jobs jobs.json] --root DIR --workers K --threads T [--light-workers L] [--only REGEX] [--dry-run]
  python -m logic_transfer.run_lt1 make-rows --out DIR       (what the make_rows job runs)

Job list: {"paths": {...}, "jobs": [{"name", "stage": make_rows|course|score|far, "args": {...}, "deps": [names], "priority": n,
"light": bool}]} (a bare list of jobs is accepted too). Lower priority number runs first (ties: list order). `light` jobs (logic-only
scoring, make_rows) run in their own small pool (--light-workers, default 1) so they never wait behind a long course.
Placeholders {ROOT} {ROWS} {DATA} {BIG} {FAR} {REPO} in string args come from paths. An arg {"from": "<course job>"} means that job's
final checkpoint (and adds the dependency "that job is DONE"); {"from": "<course job>", "file": "checkpoint-3000.pt"} means that
saved checkpoint: the job waits only until that file exists (courses save atomically), so scoring follows training as it goes; it is
BLOCKED if the course failed without producing the file.
Layout under --root: rows/ (raw/, eval/, converted train files), jobs/<name>/{cmd.txt, stdout.txt, out/, DONE|FAILED}, driver.log.
A job with a DONE marker is skipped. A job without one is re-run from a clean out/ dir (learn_probe refuses a dir that holds
scores.jsonl). A job whose dependency failed is marked BLOCKED (not run). The driver never starts anything by itself: `run` is
the launch. No full scoring and no far jobs are in the default list; far_jobs() and score_jobs(full=True) make them on request.

Launch of the default (gate + screen) list, from the repo root:
  python -m logic_transfer.run_lt1 run --root $SP/lt1 --workers 2 --threads 2 --light-workers 1
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SP = Path(os.environ.get('LT1_SP') or REPO.parents[1])          # .../scratchpad when the repo is SP/wt/lt
CKPTS = '/mnt/project-files/checkpoints/cio-1007'
PARENTS = {'s200': f'{CKPTS}/70-t1sdr-s200/T1SDR_s200/checkpoint.pt',
           's201': f'{CKPTS}/70-t1sdr-s201/T1SDR_s201/checkpoint.pt',
           's204': f'{CKPTS}/80-t1sdr-s204/T1SDR_s204/checkpoint.pt'}
DEFAULT_PATHS = {'ROOT': str(SP / 'lt1'), 'DATA': str(SP / 'data/sk200k'), 'BIG': str(SP / 'data/sk200k_big'),
                 'FAR': str(SP / 'far_inputs'), 'REPO': str(REPO)}
LEARN = '/mnt/project-files/far-transfer/learn'
FAR_STEPS = '0,500,1000,2000'
FAR_UPDATES = 2000

# make_rows spec: (kind, split, n, seed, converted file name relative to ROWS)
TRAIN_ROWS = [('logic', 'train', 120000, 11, 'logic_train.jsonl'), ('placebo', 'train', 120000, 12, 'placebo_train.jsonl')]
EVAL_ROWS = [('logic', 'gate', 1600, 21, 'eval/logic_gate.jsonl'),               # held-out wording, 400 per depth 0-3
             ('logic', 'test_sampler', 1600, 22, 'eval/logic_test_sampler.jsonl'),
             ('logic', 'dev', 1200, 23, 'eval/logic_dev.jsonl'),
             ('logic', 'test_deeper', 800, 24, 'eval/logic_test_deeper.jsonl'),
             ('placebo', 'dev', 1200, 25, 'eval/placebo_dev.jsonl'),
             ('placebo', 'test_wording', 1200, 26, 'eval/placebo_test_wording.jsonl')]
GATE_UPDATES, SAVE_EVERY = 8000, 1000


# ---------------------------------------------------------------- job list

MIX = {'C': None, 'L': '{ROWS}/logic_train.jsonl', 'P': '{ROWS}/placebo_train.jsonl'}


def course_job(p, arm, seed, priority, parents=None, updates=GATE_UPDATES, save_every=SAVE_EVERY):
    parents = parents or PARENTS
    return {'name': f'course-{p}-{arm}-s{seed}', 'stage': 'course', 'deps': ['make_rows'] if MIX[arm] else [], 'priority': priority,
            'args': {'parent': parents[p], 'mix': MIX[arm], 'mix_frac': 0.25, 'seed': seed, 'updates': updates, 'batch': 64,
                     'lr': 1e-4, 'warmup': 100, 'data': '{DATA}', 'save_every': save_every}}


def score_jobs(course, priority, every=SAVE_EVERY, updates=GATE_UPDATES, full=False):
    """One score job per saved checkpoint of a course job (checkpoint-<k>.pt, k = every, 2*every, .. updates). Logic-only (light) unless
    full=True (the full dev + logic scoring; never queued by build_jobs)."""
    base = course['name'][len('course-'):]
    out = []
    for k in range(every, updates + 1, every):
        j = {'name': f'score{"" if full else "L"}-{base}-u{k}', 'stage': 'score', 'deps': ['make_rows'], 'priority': priority,
             'args': {'ckpt': {'from': course['name'], 'file': f'checkpoint-{k}.pt'}, 'logic_dir': '{ROWS}/eval', 'logic_only': not full,
                      **({} if full else {'threads': 1})}}
        if full:
            j['args']['big_data'] = '{BIG}'
        else:
            j['light'] = True
        out.append(j)
    return out


def far_jobs(course, priority=3, far_updates=FAR_UPDATES, far_steps=FAR_STEPS):
    """The L9 learn test (arm LB) from a finished course checkpoint. Not in the default list; add on request."""
    base = course['name'][len('course-'):]
    return [{'name': f'far-{base}', 'stage': 'far', 'deps': [], 'priority': priority,
             'args': {'parent': {'from': course['name']}, 'updates': far_updates, 'steps': far_steps}}]


def build_jobs(plan='lt1', far=False, parents=None, updates=GATE_UPDATES, save_every=SAVE_EVERY):
    """plan 'gate': s200 arms L and C to `updates` updates (priority 0) + logic-only scoring of every saved checkpoint (priority 0) + logic-only
    baselines of the three parents. plan 'screen': s200 P (1), s201 {L,P,C} (1), s204 {L,P,C} (2), each with logic-only scoring of its
    checkpoints at its own priority. plan 'lt1' = gate + screen. Full scoring is not queued. far=True adds a far job per course."""
    parents = parents or PARENTS
    jobs = [{'name': 'make_rows', 'stage': 'make_rows', 'args': {}, 'deps': [], 'priority': 0, 'light': True}]
    plans = []
    if plan in ('gate', 'lt1'):
        plans += [('s200', 'L', 0), ('s200', 'C', 0)]
        for p in parents:
            jobs.append({'name': f'scoreL-parent-{p}', 'stage': 'score', 'deps': ['make_rows'], 'priority': 0, 'light': True,
                         'args': {'ckpt': parents[p], 'logic_dir': '{ROWS}/eval', 'logic_only': True, 'threads': 1}})
    if plan in ('screen', 'lt1'):
        plans += [('s200', 'P', 1)] + [('s201', arm, 1) for arm in 'LPC'] + [('s204', arm, 2) for arm in 'LPC']
    for p, arm, prio in plans:
        c = course_job(p, arm, 1, prio, parents, updates, save_every)
        jobs.append(c)
        jobs += score_jobs(c, prio, save_every, updates)
        if far:
            jobs += far_jobs(c)
    return {'paths': dict(DEFAULT_PATHS), 'jobs': jobs}


# ---------------------------------------------------------------- make_rows

def make_rows(out, spec=None):
    """Generate (logicgen CLI, run from the repo root) and convert every row file; write summary.json (counts, train/eval overlap)."""
    from logic_transfer import rows as R
    out = Path(out)
    (out / 'raw').mkdir(parents=True, exist_ok=True)
    (out / 'eval').mkdir(parents=True, exist_ok=True)
    summary = {}
    prompts = {}
    for kind, split, n, seed, rel in (spec or TRAIN_ROWS + EVAL_ROWS):
        raw = out / 'raw' / f'{kind}_{split}.jsonl'
        subprocess.run([sys.executable, '-m', 'logicgen.make', '--kind', kind, '--split', split, '--n', str(n), '--seed', str(seed),
                        '--max-chars', '208', '--out', str(raw)], check=True, cwd=REPO)
        dst = out / rel
        R.convert(raw, dst)
        summary[rel] = R.verify(dst)
        summary[rel].update(seed=seed, kind=kind, split=split)
        prompts[rel] = {json.loads(l)['prompt'] for l in open(dst)}
    for rel, ps in prompts.items():
        kind = 'logic' if 'logic' in rel else 'placebo'
        tr = prompts.get(f'{kind}_train.jsonl')
        if rel.startswith('eval/') and tr is not None:
            summary[rel]['prompts_also_in_train'] = len(ps & tr)
    json.dump(summary, open(out / 'summary.json', 'w'), indent=1)
    print(json.dumps(summary, indent=1))


# ---------------------------------------------------------------- commands

def sub(v, paths):
    if isinstance(v, str):
        for k, p in paths.items():
            v = v.replace('{' + k + '}', p)
    return v


def resolve(job, paths):
    """-> (argv list, extra deps [job names that must be DONE], waits [(job name, file path)]: the file must exist). Pure."""
    root = Path(paths['ROOT'])
    paths = dict(paths, ROWS=str(root / 'rows'))
    a = {k: (v if isinstance(v, dict) else sub(v, paths)) for k, v in job['args'].items()}
    extra, waits, py = [], [], sys.executable
    out = str(root / 'jobs' / job['name'] / 'out')
    threads = str(a.get('threads', paths.get('THREADS', 1)))

    def ck(v):
        if isinstance(v, dict):
            f = str(root / 'jobs' / v['from'] / 'out' / v.get('file', 'checkpoint.pt'))
            if 'file' in v:
                waits.append((v['from'], f))
            else:
                extra.append(v['from'])
            return f
        return v
    st = job['stage']
    if st == 'make_rows':
        cmd = [py, '-m', 'logic_transfer.run_lt1', 'make-rows', '--out', paths['ROWS']]
    elif st == 'course':
        cmd = [py, '-m', 'logic_transfer.course', '--parent', ck(a['parent']), '--data', a['data'], '--mix-frac', str(a['mix_frac']),
               '--updates', str(a['updates']), '--batch', str(a['batch']), '--lr', str(a['lr']), '--warmup', str(a['warmup']),
               '--seed', str(a['seed']), '--threads', threads, '--out', out, '--log-every', str(a.get('log_every', 250)), '--save-every', str(a.get('save_every', 0))]
        if a.get('mix'):
            cmd += ['--mix', a['mix']]
    elif st == 'score':
        cmd = [py, '-m', 'logic_transfer.score', '--ckpt', ck(a['ckpt']), '--threads', threads,
               '--out', str(root / 'jobs' / job['name'] / 'out' / 'score.json')]
        if a.get('big_data'):
            cmd += ['--big-data', a['big_data']]
        if a.get('logic_only'):
            cmd += ['--logic-only']
        if a.get('logic_dir'):
            cmd += ['--logic-dir', a['logic_dir']]
    elif st == 'far':
        fi = paths['FAR']
        cmd = [py, '-m', 'domain.far.learn_probe', 'train', '--arm', a.get('arm', 'LB'), '--cells', a.get('cells', 'l8'),
               '--updates', str(a['updates']), '--steps', a['steps'], '--threads', threads, '--out', out, '--parent', ck(a['parent'])]
        for flag, fname, default in (('--rows', 'train-rows-l9.jsonl', f'{LEARN}/train-rows-l9.jsonl'),
                                     ('--probe', 'sheet-probe.jsonl', '/mnt/project-files/far-transfer/diag/sheet-probe.jsonl'),
                                     ('--eval-rows', 'eval-rows-l5.jsonl', f'{LEARN}/eval-rows-l5.jsonl')):
            mine = os.path.join(fi, fname)
            cmd += [flag, a.get(flag[2:].replace('-', '_')) or (mine if os.path.exists(mine) else default)]
    else:
        raise SystemExit(f'unknown stage {st}')
    return cmd, extra, waits


def log(root, msg):
    line = f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    with open(Path(root) / 'driver.log', 'a') as f:
        f.write(line + '\n')


def run(jobs_doc, root, workers, threads, only=None, dry=False, poll=2.0, light_workers=1):
    root = Path(root)
    paths = dict(DEFAULT_PATHS, **jobs_doc.get('paths', {})) if isinstance(jobs_doc, dict) else dict(DEFAULT_PATHS)
    paths['ROOT'] = str(root)
    paths['THREADS'] = str(threads)
    jobs = jobs_doc['jobs'] if isinstance(jobs_doc, dict) else jobs_doc
    root.mkdir(parents=True, exist_ok=True)
    cmds, deps, waits, prio, light = {}, {}, {}, {}, {}
    for j in jobs:
        n = j['name']
        cmds[n], extra, waits[n] = resolve(j, dict(paths, ROWS=str(root / 'rows')))
        deps[n] = list(dict.fromkeys(list(j.get('deps', [])) + extra))
        prio[n], light[n] = j.get('priority', 5), bool(j.get('light'))
    names = [j['name'] for j in jobs]
    assert len(set(names)) == len(names), 'duplicate job names'
    for n in names:
        assert all(x in cmds for x in deps[n] + [w[0] for w in waits[n]]), (n, deps[n], waits[n])
    want = [n for n in names if not only or re.search(only, n)]
    if only:                                   # pull in the dependencies of what was asked for
        stack = list(want)
        while stack:
            n = stack.pop()
            for d in deps[n] + [w[0] for w in waits[n]]:
                if d not in want:
                    want.append(d); stack.append(d)
    want.sort(key=lambda n: (prio[n], names.index(n)))       # lower priority number first, then list order
    jdir = lambda n: root / 'jobs' / n
    state = {n: ('done' if (jdir(n) / 'DONE').exists() else 'todo') for n in want}
    log(root, f'start: {len(want)} jobs ({sum(s == "done" for s in state.values())} already DONE), workers {workers} (+{light_workers} light), threads {threads}')
    if dry:
        for n in want:
            print(f'{state[n]:5s} p{prio[n]} {"light " if light[n] else ""}{n}: deps={deps[n]} waits={[w[1].split("/jobs/")[-1] for w in waits[n]]}\n      {" ".join(cmds[n])}')
        return state
    env = dict(os.environ, PYTHONPATH=str(REPO), OMP_NUM_THREADS=str(threads), MKL_NUM_THREADS=str(threads),
               PYTHONUNBUFFERED='1', TOKENIZERS_PARALLELISM='false')
    running = {}
    ready = lambda n: all(state.get(d) == 'done' for d in deps[n]) and all(os.path.exists(f) for _, f in waits[n])
    while True:
        for n, (p, t0) in list(running.items()):
            rc = p.poll()
            if rc is None:
                continue
            del running[n]
            if rc == 0:
                (jdir(n) / 'DONE').write_text(time.strftime('%Y-%m-%dT%H:%M:%S') + '\n')
                state[n] = 'done'
            else:
                (jdir(n) / 'FAILED').write_text(f'rc={rc}\n')
                state[n] = 'failed'
            log(root, f'{n}: {state[n]} rc={rc} in {time.time() - t0:.0f}s')
        for n in want:      # blocked: a dependency failed, or the course that should write the awaited file is over without it
            if state[n] != 'todo':
                continue
            bad = any(state.get(d) in ('failed', 'blocked') for d in deps[n]) or \
                any(not os.path.exists(f) and state.get(j) in ('failed', 'blocked', 'done') for j, f in waits[n])
            if bad:
                state[n] = 'blocked'
                log(root, f'{n}: BLOCKED (dependency failed or its file will not appear)')
        nrun = lambda lt: sum(1 for m in running if light[m] == lt)
        for n in want:
            if state[n] == 'todo' and ready(n) and nrun(light[n]) < (light_workers if light[n] else workers):
                d = jdir(n)
                d.mkdir(parents=True, exist_ok=True)
                for stale in ('FAILED', 'DONE'):
                    (d / stale).unlink(missing_ok=True)
                if (d / 'out').exists() and n != 'make_rows':
                    shutil.rmtree(d / 'out')
                (d / 'out').mkdir(exist_ok=True)
                (d / 'cmd.txt').write_text(' '.join(cmds[n]) + '\n')
                f = open(d / 'stdout.txt', 'a')
                running[n] = (subprocess.Popen(cmds[n], cwd=REPO, env=env, stdout=f, stderr=subprocess.STDOUT), time.time())
                state[n] = 'running'
                log(root, f'{n}: started')
        if not running and not any(state[n] == 'todo' and ready(n) for n in want):
            break
        time.sleep(poll)
    summ = {s: [n for n in want if state[n] == s] for s in ('done', 'failed', 'blocked', 'todo')}
    log(root, 'finished: ' + ', '.join(f'{len(v)} {k}' for k, v in summ.items()))
    return state


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('plan')
    p.add_argument('--plan', default='lt1', choices=['lt1', 'gate', 'screen'])
    p.add_argument('--far', action='store_true')
    p.add_argument('--out')
    r = sp.add_parser('run')
    r.add_argument('--jobs')
    r.add_argument('--root', default=str(SP / 'lt1'))
    r.add_argument('--workers', type=int, default=2)
    r.add_argument('--threads', type=int, default=2)
    r.add_argument('--only')
    r.add_argument('--dry-run', action='store_true')
    r.add_argument('--light-workers', type=int, default=1)
    r.add_argument('--plan', default='lt1', choices=['lt1', 'gate', 'screen'], help='when --jobs is not given')
    r.add_argument('--far', action='store_true')
    m = sp.add_parser('make-rows')
    m.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'make-rows':
        make_rows(a.out)
    elif a.cmd == 'plan':
        doc = build_jobs(a.plan, a.far)
        s = json.dumps(doc, indent=1)
        if a.out:
            Path(a.out).write_text(s)
        else:
            print(s)
    else:
        doc = json.load(open(a.jobs)) if a.jobs else build_jobs(a.plan, a.far)
        st = run(doc, a.root, a.workers, a.threads, a.only, a.dry_run, light_workers=a.light_workers)
        if not a.dry_run and any(v in ('failed', 'blocked') for v in st.values()):
            sys.exit(1)


if __name__ == '__main__':
    main()
