"""LT-2 ladder driver: run the six runs of one rung and read them by the sealed marks (MARKS-LT2-2026-10-14.md).

  python -m logic_transfer.lt2 run    --rung R --work DIR --parents-dir DIR --sk200k DIR [--device cpu|cuda] [--procs 3] [--threads 1]
                                      [--updates 8000] [--eval-every 250] [--eval-n 400] [--runs s200:1,s200:2,...] [--dry]
  python -m logic_transfer.lt2 report --work DIR [--rung R ...]
  python -m logic_transfer.lt2 agree  --ckpt CKPT --rows ROWS.jsonl [--n N]       (same checkpoint, CPU vs GPU decoding)
  python -m logic_transfer.lt2 indist --work DIR --rung R --parents-dir DIR --big-data DIR [--device cuda]   (non-logic in_dist, parents vs stop checkpoints)

Layout: DIR/rows/rung<r>/{train,dev,wording,newwords}.jsonl (built here if missing, byte-for-byte deterministic, hashes checked against
ladder-hashes.json when it lists them), DIR/rung<r>/<parent>-s<seed>/ = one course run (course.py outputs), DIR/rung<r>/DONE.json.
Runs: 3 parents (s200, s201, s204) x course seeds 1, 2. Gate files: dev (and wording on rung 0); stop thresholds are max(90, baseline+25)
for dev and max(80, baseline+25) for wording, baseline = the train-fitted count baseline of that file (F3), so a run stops only when ALL its
marks hold. new-words is evaluated and reported, never gated. Rung 0 also carries the falsifier: when every run has either stopped or reached
2,000 updates and >= 5 of 6 are below 50% dev at 2,000, the driver writes ABORT and the runs end at their next eval.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PARENTS = ('s200', 's201', 's204')
SEEDS = (1, 2)
DEV_MIN, WORD_MIN, MARGIN = 90.0, 80.0, 25.0
FALSIFY_AT, FALSIFY_BELOW, FALSIFY_RUNS = 2000, 50.0, 5


def run_name(parent, seed):
    return f'{parent}-s{seed}'


def all_runs():
    return [(p, s) for p in PARENTS for s in SEEDS]


def parent_path(parents_dir, parent):
    return os.path.join(parents_dir, f'T1SDR_{parent}.pt')


# eval files per rung (names = files in rows/rung<r>/); the first is the PRIMARY one whose accuracy is tracked at 2,000 / 4,000 / 8,000 updates
EVALS = {0: ('dev', 'wording', 'newwords'), 1: ('dev', 'newwords'), 2: ('dev', 'newwords'), 3: ('dev', 'wording'), 4: ('dev', 'gate'),
         5: ('gate', 'dev', 'deeper')}
R5_DEPTH_BARS = {'0': 80.0, '1': 80.0, '2': 65.0, '3': 55.0}      # the LT-1 G-PASS bars (gate accuracy by depth)


def ensure_rows(work, rung, n_train=None, build=True):
    """Build (or find) the rung's row files; when logic_transfer/ladder-hashes.json lists the rung, every listed file's BYTES on disk must hash to the
    sealed value (a box that built different rows, a truncated or edited file, or an old build in the work dir stops here, not three hours later)."""
    from logic_transfer import ladder
    d = os.path.join(work, 'rows', f'rung{rung}')
    summ = os.path.join(d, 'summary.json')
    if not os.path.exists(summ):
        assert build, f'rung{rung}: no row summary at {summ} (reports never start a build)'
        ladder.build(rung, os.path.join(work, 'rows'), n_train=n_train)
    s = json.load(open(summ))
    hp = os.path.join(HERE, 'ladder-hashes.json')
    if os.path.exists(hp):
        want = json.load(open(hp)).get(f'rung{rung}')
        assert want, f'ladder-hashes.json has no entry for rung{rung}: refusing to run on unsealed rows'
        for name, h in want.items():
            got = ladder.sha256(os.path.join(d, name + '.jsonl'))
            assert got == h, f'rung{rung}/{name}: file on disk hashes to {got[:12]} but ladder-hashes.json says {h[:12]}'
    return d, s


def thresholds(rung, summ):
    """The rung's marks as [(eval file, by_level key or None, percent threshold)] (MARKS-LT2 + Addendum 1). Baselines are the train-fitted count
    baselines of the same file (F3): a mark is max(bar, baseline + 25)."""
    def base(f):
        """Baseline + 25 floored to 2 decimals from the EXACT hit count (rung 1: 800/1200 + 25 = 91.6667 -> 91.66, so 1100/1200 right passes)."""
        cb = summ['files'][f]['count_baseline']
        exact = 100.0 * cb['hit'] / cb['n'] if 'hit' in cb else cb['acc']
        return math.floor((exact + MARGIN) * 100 + 1e-9) / 100.0 - MARGIN
    if rung in (0, 3):
        return [('dev', None, max(DEV_MIN, base('dev') + MARGIN)), ('wording', None, max(WORD_MIN, base('wording') + MARGIN))]
    if rung in (1, 2):
        return [('dev', None, max(DEV_MIN, base('dev') + MARGIN))]
    if rung == 4:
        return [('dev', None, max(DEV_MIN, base('dev') + MARGIN)), ('gate', None, max(75.0, base('gate') + MARGIN))]
    if rung == 5:
        return [('gate', lv, bar) for lv, bar in R5_DEPTH_BARS.items()] + [('gate', None, base('gate') + MARGIN)]
    raise ValueError(rung)


def marks_string(th):
    return ','.join(f"{f}{'@' + lv if lv else ''}>={v:g}" for f, lv, v in th)


def eval_pct(e, level):
    """Accuracy in percent of one eval.jsonl record: the whole file or one by_level cell ([correct, n])."""
    if level is None:
        return e['exact']
    c = e['by_level'].get(level)
    return 100.0 * c[0] / c[1] if c and c[1] else float('nan')


def read_evals(run_dir):
    p = os.path.join(run_dir, 'eval.jsonl')
    if not os.path.exists(p):
        return []
    out = []
    for l in open(p):
        try:
            out.append(json.loads(l))
        except ValueError:
            pass                                    # a half-written last line while the run is going
    return out


def dev_at(evals, u):
    """Latest dev eval at update <= u (None if none yet)."""
    c = [e for e in evals if e['name'] == 'dev' and e['update'] <= u]
    return max(c, key=lambda e: (e['update'], e['full'])) if c else None


def run_state(run_dir):
    if os.path.exists(os.path.join(run_dir, 'run.json')):
        return 'done'
    if os.path.exists(os.path.join(run_dir, 'failure.txt')):
        return 'failed'
    return 'running' if os.path.exists(run_dir) else 'todo'


def falsifier(work, rung, runs):
    """-> (decided, fired, detail). fired = >= 5 of the 6 runs are below 50% dev at 2,000 updates (a run that stopped earlier on its marks
    counts as above). decided once that is settled: 5 runs already below, or 2 runs already at/above 50%, or every run has reported."""
    below, seen = 0, []
    for p, s in runs:
        rd = os.path.join(work, f'rung{rung}', run_name(p, s))
        ev = read_evals(rd)
        st = os.path.join(rd, 'stop.json')
        stopped = json.load(open(st)) if os.path.exists(st) else None
        e = dev_at(ev, FALSIFY_AT)
        by_marks = stopped is not None and stopped['reason'] == 'marks' and (e is None or e['update'] < FALSIFY_AT)
        if by_marks:
            seen.append(100.0)
        elif e is not None and e['update'] >= FALSIFY_AT:
            seen.append(round(e['exact'], 1))
            below += e['exact'] < FALSIFY_BELOW
    n_not_below = len(seen) - below
    decided = below >= FALSIFY_RUNS or n_not_below >= len(runs) - FALSIFY_RUNS + 1 or len(seen) == len(runs)
    return decided, below >= FALSIFY_RUNS, dict(dev_at_2000=seen, below=below, reported=len(seen))


def cmd_run(a):
    rung = a.rung
    d, summ = ensure_rows(a.work, rung)
    th = thresholds(rung, summ)
    runs = [tuple(x.split(':')) for x in a.runs.split(',')] if a.runs else all_runs()
    runs = [(p, int(s)) for p, s in runs]
    out_root = os.path.join(a.work, f'rung{rung}')
    os.makedirs(out_root, exist_ok=True)
    abort = os.path.join(out_root, 'ABORT')
    if os.path.exists(abort) and not a.keep_abort:
        os.unlink(abort)
    evs = [f'--eval={n}={d}/{n}.jsonl' for n in EVALS[rung]]
    assert all(os.path.exists(f'{d}/{n}.jsonl') for n in EVALS[rung]), f'missing eval file for rung {rung} in {d}'

    def cmd(p, s):
        c = [sys.executable, '-m', 'logic_transfer.course', '--parent', parent_path(a.parents_dir, p), '--data', a.sk200k, '--mix', f'{d}/train.jsonl',
             '--mix-frac', '0.25', '--updates', str(a.updates), '--batch', '64', '--lr', '1e-4', '--warmup', '100', '--seed', str(s),
             '--threads', str(a.threads), '--device', a.device, '--out', os.path.join(out_root, run_name(p, s)), '--log-every', '250',
             '--eval-every', str(a.eval_every), '--eval-n', str(a.eval_n), '--stop-marks', marks_string(th), '--abort-file', abort,
             '--slice-every', '25'] + (['--gpu-mem-gb', str(a.gpu_mem_gb)] if a.device == 'cuda' and a.gpu_mem_gb else []) + evs
        return c
    print(f'rung {rung}: marks {marks_string(th)}; {len(runs)} runs; device {a.device}; procs {a.procs} x {a.threads} threads', flush=True)
    todo = [(p, s) for p, s in runs if run_state(os.path.join(out_root, run_name(p, s))) != 'done']
    if a.dry:
        for p, s in todo:
            print(' '.join(cmd(p, s)))
        return
    live, t0, attempts = {}, time.time(), {}
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, [os.path.dirname(HERE), os.environ.get('PYTHONPATH')])), PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
    last_note = 0
    while todo or live:
        while todo and len(live) < a.procs:
            p, s = todo.pop(0)
            rd = os.path.join(out_root, run_name(p, s))
            os.makedirs(rd, exist_ok=True)
            attempts[(p, s)] = attempts.get((p, s), 0) + 1
            for stale in ('failure.txt', 'stop.json'):
                if os.path.exists(os.path.join(rd, stale)):
                    os.unlink(os.path.join(rd, stale))
            lf = open(os.path.join(rd, 'stdout.log'), 'w')
            live[(p, s)] = (subprocess.Popen(cmd(p, s), stdout=lf, stderr=subprocess.STDOUT, env=env, cwd=os.path.dirname(HERE)), lf)
            print(f'started {run_name(p, s)} (attempt {attempts[(p, s)]}) at {time.time() - t0:.0f}s', flush=True)
            time.sleep(a.stagger)                     # loading 330k rows peaks at several GB per process: do not start everything in the same seconds
        time.sleep(a.poll)
        for k, (pr, lf) in list(live.items()):
            if pr.poll() is not None:
                lf.close()
                del live[k]
                print(f'finished {run_name(*k)} rc={pr.returncode} at {time.time() - t0:.0f}s', flush=True)
                if pr.returncode != 0:
                    rd = os.path.join(out_root, run_name(*k))
                    tail = ''.join(open(os.path.join(rd, 'stdout.log'), errors='replace').readlines()[-40:])
                    open(os.path.join(rd, 'failure.txt'), 'w').write(f'rc={pr.returncode} attempt={attempts[k]}\n{tail}')
                    print(f'--- {run_name(*k)} failed (rc={pr.returncode}, attempt {attempts[k]}); last lines:\n{tail[-1500:]}\n---', flush=True)
                    if attempts[k] <= a.retries and not os.path.exists(abort):
                        todo.insert(0, k)
                        time.sleep(a.retry_wait)
        if rung == 0 and a.falsifier and not os.path.exists(abort):
            decided, fired, detail = falsifier(a.work, rung, runs)
            if decided and fired:
                open(abort, 'w').write(json.dumps(detail))
                print(f'R0 FALSIFIER FIRED {detail}: ABORT written', flush=True)
                todo.clear()
        if time.time() - last_note > 600:
            last_note = time.time()
            print(f'[{time.time() - t0:.0f}s] ' + ' '.join(f'{run_name(*k)}:{(read_evals(os.path.join(out_root, run_name(*k))) or [{"update": 0}])[-1]["update"]}' for k in live), flush=True)
    json.dump(dict(rung=rung, marks=marks_string(th), runs=[run_name(p, s) for p, s in runs], wall_s=round(time.time() - t0, 1), device=a.device),
              open(os.path.join(out_root, 'DONE.json'), 'w'), indent=1)
    print('all runs finished', flush=True)


def run_summary(work, rung, p, s, th):
    rd = os.path.join(work, f'rung{rung}', run_name(p, s))
    ev = read_evals(rd)
    st = json.load(open(os.path.join(rd, 'stop.json'))) if os.path.exists(os.path.join(rd, 'stop.json')) else None
    out = dict(run=run_name(p, s), state=run_state(rd), stop=(st or {}).get('reason'), updates=(st or {}).get('update'))
    full = [e for e in ev if e['full']]
    ok_at = None
    by_u = {}
    for e in full:
        by_u.setdefault(e['update'], {})[e['name']] = e
    for u in sorted(by_u):
        if all(f in by_u[u] and eval_pct(by_u[u][f], lv) >= v for f, lv, v in th):
            ok_at = u
            break
    out['pass'] = ok_at is not None
    out['pass_update'] = ok_at
    holds = lambda dct: all(f in dct and eval_pct(dct[f], lv) >= v for f, lv, v in th)
    us = sorted(by_u)
    out['pass_streak2'] = any(holds(by_u[a_]) and holds(by_u[b_]) for a_, b_ in zip(us, us[1:]))     # the stop rule's own condition (two whole-file evals in a row)
    out['holds_at_last_full_eval'] = bool(us) and holds(by_u[us[-1]])
    allp = {}
    for e in ev:                                           # prefix (non-full) evals too
        allp.setdefault(e['update'], {})[e['name']] = e
    out['near'] = ok_at is None and any(holds(d_) for d_ in allp.values())      # marks met on a prefix eval but never confirmed on the whole file
    prim = EVALS[rung][0]

    def acc_at(u):
        """Primary-file accuracy at update u: the latest eval at or before u. A run that STOPPED on its marks at update <= u is not evaluated after
        it stopped; its stopping evaluation is carried forward and the cell is listed in out['dev_at_carried'] (a run that merely passed once and then
        went on training is NOT carried: its own later evals are read)."""
        if st and st.get('reason') == 'marks' and st['update'] <= u and st['update'] in by_u and prim in by_u[st['update']]:
            carried.append(str(u))
            return round(by_u[st['update']][prim]['exact'], 2)
        c = [e for e in ev if e['name'] == prim and e['update'] <= u]
        return max(c, key=lambda e: (e['update'], e['full']))['exact'] if c else None
    carried = []
    out['primary_file'] = prim
    out['dev_at'] = {str(u): acc_at(u) for u in (2000, 4000, 8000)}
    out['dev_at_carried'] = carried
    last_dev = [e for e in ev if e['name'] == prim]
    out['last_dev'] = (last_dev[-1]['update'], last_dev[-1]['exact'], last_dev[-1]['full']) if last_dev else None
    if rung == 5:
        gl = [e for e in ev if e['name'] == 'gate' and e['full']]
        out['gate_by_depth_last'] = {lv: round(eval_pct(gl[-1], lv), 1) for lv in R5_DEPTH_BARS} if gl else None
    nw = [e for e in ev if e['name'] == 'newwords']
    out['newwords_last'] = (nw[-1]['update'], nw[-1]['exact']) if nw else None
    lf = [e for e in ev if e['name'] == prim and e['full'] and e.get('by_label')]
    out['label_recall_last'] = ({k: round(100.0 * c / max(n, 1), 1) for k, (c, n) in lf[-1]['by_label'].items()} if lf else None)
    pj = os.path.join(rd, 'probe.json')
    out['probes'] = json.load(open(pj))['probes'] if os.path.exists(pj) else None
    return out


def _code_sha():
    """Short git sha of the code that produced this report (the box refreshes its code between orders; a report shows which state it ran)."""
    try:
        return subprocess.run(['git', '-C', HERE, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception:
        return None


def cuda_available():
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def probe_runs(work, rung, rows, device, n=600):
    """Counterfactual probes (probes.py; rungs 0-2, reported never gated) on the checkpoint of every run that PASSED its marks; writes
    <run>/probe.json and fills rows[i]['probes']. A run whose probe fails keeps probes=None and an 'error' note (the report never aborts)."""
    from logic_transfer import probes
    from custom_io.data import load_rows
    rws = load_rows(os.path.join(work, 'rows', f'rung{rung}', 'dev.jsonl'), keep=None)[:n]
    for x in rows:
        if not x['pass'] or x['state'] != 'done':
            continue
        rd = os.path.join(work, f'rung{rung}', x['run'])
        pj, ck = os.path.join(rd, 'probe.json'), os.path.join(rd, 'checkpoint.pt')
        if not os.path.exists(pj) and os.path.exists(ck):
            try:
                json.dump(probes.run(ck, rws, rung, device), open(pj, 'w'), indent=1)
            except Exception as ex:               # noqa: BLE001  (a reported-only instrument must not take the report down)
                x['probe_error'] = f'{type(ex).__name__}: {ex}'[:300]
                continue
        if os.path.exists(pj):
            x['probes'] = json.load(open(pj))['probes']


def summarise_probes(rows):
    acc = {}
    for x in rows:
        for name, d in (x.get('probes') or {}).items():
            acc.setdefault(name, []).append(list(d.values())[1] if len(d) > 1 else list(d.values())[0])
    return {k: dict(mean=round(sum(v) / len(v), 1), min=round(min(v), 1), max=round(max(v), 1), n=len(v)) for k, v in acc.items()}


def summarise_recall(rows):
    acc = {}
    for x in rows:
        for lab, v in (x.get('label_recall_last') or {}).items():
            acc.setdefault(lab, []).append(v)
    return {k: dict(mean=round(sum(v) / len(v), 1), min=round(min(v), 1), max=round(max(v), 1), n=len(v)) for k, v in sorted(acc.items())}


def cmd_report(a):
    rungs = a.rung or sorted(int(x[5:]) for x in os.listdir(a.work) if x.startswith('rung') and os.path.isdir(os.path.join(a.work, x)))
    res = {}
    for r in rungs:
        d, summ = ensure_rows(a.work, r, build=False)
        th = thresholds(r, summ)
        rows = [run_summary(a.work, r, p, s, th) for p, s in all_runs()]
        pdev = {'auto': 'cuda' if cuda_available() else None, 'cpu': 'cpu', 'cuda': 'cuda', 'off': None}[a.probes]
        if r <= 2 and pdev:
            probe_runs(a.work, r, rows, pdev)
        n_pass = sum(x['pass'] for x in rows)
        finished = all(x['state'] in ('done', 'failed') for x in rows)
        n_failed = sum(x['state'] == 'failed' for x in rows)
        dec = falsifier(a.work, r, all_runs()) if r == 0 else (False, False, None)
        if r == 0 and dec[0] and dec[1]:
            verdict = 'FALSIFIED (interface cannot learn a label at this share)'
        elif n_pass >= 5:
            verdict = 'PASS'
        elif finished and n_failed:
            verdict = f'INCOMPLETE ({n_failed} runs crashed; no reading)'
        elif finished and n_pass <= 1:
            verdict = 'FAIL'
        elif finished:
            verdict = 'MIXED'
        else:
            verdict = 'PENDING'
        stats = {}
        for u in ('2000', '4000', '8000'):
            v = [x['dev_at'][u] for x in rows if x['dev_at'][u] is not None]
            if v:
                stats[u] = dict(mean=round(sum(v) / len(v), 1), min=round(min(v), 1), max=round(max(v), 1), n=len(v),
                                n_carried=sum(u in x['dev_at_carried'] for x in rows))
        res[f'rung{r}'] = dict(marks=marks_string(th), baseline={k: summ['files'][k]['count_baseline']['acc'] for k in EVALS[r] if 'count_baseline' in summ['files'][k]}, n_pass=n_pass, n_runs=len(rows),
                               verdict=verdict, dev_stats=stats, label_recall=summarise_recall(rows), probe_summary=summarise_probes(rows),
                               code=_code_sha(), runs=rows, falsifier=dec[2])
    print(json.dumps(res, indent=1))
    return res


def cmd_agree(a):
    """The GPU path must reproduce the CPU numbers: one checkpoint, the same rows, decoded on CPU and on the GPU (fp32 both)."""
    import torch
    from custom_io.data import load_rows
    from custom_io.evalx import evaluate
    from custom_io.models import load_model
    rows = load_rows(a.rows, keep=None)
    rows = rows[:a.n] if a.n else rows
    out = {'ckpt': a.ckpt, 'rows': a.rows, 'n': len(rows)}
    preds = {}
    for dev in ('cpu', 'cuda'):
        if dev == 'cuda' and not torch.cuda.is_available():
            out['cuda'] = None
            continue
        t = time.time()
        m = load_model(a.ckpt, dev)
        r = evaluate(m, rows, 128, torch.device(dev), return_preds=True)
        preds[dev] = r['preds']
        out[dev] = dict(correct=r['correct'], exact=round(r['exact'], 3), s=round(time.time() - t, 1))
    if 'cpu' in preds and 'cuda' in preds:
        same = sum(preds['cpu'][k] == preds['cuda'][k] for k in preds['cpu'])
        out['prediction_agreement'] = round(same / len(rows), 4)
        out['accuracy_gap_points'] = round(abs(out['cpu']['exact'] - out['cuda']['exact']), 3)
        out['agree_ok'] = out['accuracy_gap_points'] <= 1.0 and out['prediction_agreement'] >= 0.98       # Addendum 1 condition (a); condition (b) is the loss window in run logs
    print(json.dumps(out))
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1)
    return out


def cmd_indist(a):
    """Non-logic in_dist accuracy (score.py on the curriculum's in_dist dev split) of each parent and of each stopped checkpoint; delta = run - parent."""
    outdir = os.path.join(a.work, 'indist')
    os.makedirs(outdir, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, [os.path.dirname(HERE), os.environ.get('PYTHONPATH')])))

    def score(ckpt, dst):
        if not os.path.exists(dst):
            subprocess.run([sys.executable, '-m', 'logic_transfer.score', '--ckpt', ckpt, '--big-data', a.big_data, '--dev-splits', 'in_dist',
                            '--device', a.device, '--out', dst], check=True, env=env, cwd=os.path.dirname(HERE), stdout=subprocess.DEVNULL)
        sp = json.load(open(dst))['splits']['in_dist']
        return round(100.0 * sp['correct'] / sp['n'], 2), sp['n']
    par = {p: score(parent_path(a.parents_dir, p), os.path.join(outdir, f'parent-{p}-rung{a.rung}.json')) for p in PARENTS}      # per-rung file: rungs run at once on the box
    res = {}
    for p, s in all_runs():
        ck = os.path.join(a.work, f'rung{a.rung}', run_name(p, s), 'checkpoint.pt')
        if not os.path.exists(ck):
            continue
        acc, n = score(ck, os.path.join(outdir, f'rung{a.rung}-{run_name(p, s)}.json'))
        res[run_name(p, s)] = dict(in_dist=acc, n=n, parent=par[p][0], delta=round(acc - par[p][0], 2), flag=('DROP>3' if acc - par[p][0] < -3 else None))
    out = dict(rung=a.rung, parents={p: v[0] for p, v in par.items()}, runs=res)
    json.dump(out, open(os.path.join(outdir, f'rung{a.rung}-summary.json'), 'w'), indent=1)
    print(json.dumps(out))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    g = sub.add_parser('agree')
    g.add_argument('--ckpt', required=True)
    g.add_argument('--rows', required=True)
    g.add_argument('--n', type=int, default=0)
    g.add_argument('--out')
    d = sub.add_parser('indist')
    d.add_argument('--work', required=True)
    d.add_argument('--rung', type=int, required=True)
    d.add_argument('--parents-dir', required=True)
    d.add_argument('--big-data', required=True)
    d.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    r = sub.add_parser('run')
    r.add_argument('--rung', type=int, required=True)
    r.add_argument('--work', required=True)
    r.add_argument('--parents-dir', required=True)
    r.add_argument('--sk200k', required=True)
    r.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    r.add_argument('--procs', type=int, default=3)
    r.add_argument('--threads', type=int, default=1)
    r.add_argument('--updates', type=int, default=8000)
    r.add_argument('--eval-every', type=int, default=250)
    r.add_argument('--eval-n', type=int, default=400, help='0 = whole file at every eval (GPU)')
    r.add_argument('--runs', help='comma list parent:seed, default all six')
    r.add_argument('--poll', type=float, default=20)
    r.add_argument('--no-falsifier', dest='falsifier', action='store_false')
    r.add_argument('--keep-abort', action='store_true')
    r.add_argument('--gpu-mem-gb', type=float, default=3.5, help='cuda: per-process cap on the caching allocator (the card is shared by every run of every rung at once; an out-of-memory then waits and retries inside the run)')
    r.add_argument('--stagger', type=float, default=6, help='seconds between process starts (memory peak while loading rows)')
    r.add_argument('--retries', type=int, default=1, help='restart a run that exits non-zero (same seed, from scratch) this many times')
    r.add_argument('--retry-wait', type=float, default=30)
    r.add_argument('--dry', action='store_true')
    q = sub.add_parser('report')
    q.add_argument('--work', required=True)
    q.add_argument('--rung', type=int, action='append')
    q.add_argument('--probes', choices=['auto', 'cpu', 'cuda', 'off'], default='auto', help='counterfactual probes on passing rung 0-2 checkpoints (auto: on when a GPU is present)')
    a = ap.parse_args(argv)
    return {'run': cmd_run, 'report': cmd_report, 'agree': cmd_agree, 'indist': cmd_indist}[a.cmd](a)


if __name__ == '__main__':
    main()
