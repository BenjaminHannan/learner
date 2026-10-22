"""orchestrate.py -- the positive-control protocol around posctrl.py.   See README.md for the commands.

  python3 orchestrate.py calib  --accum 4 8 --eps 1e-4 3e-4 ...     healthy-only sweep (C + 2 resumes per eps): mean |dL| of R vs C as a fraction of the loss level
  python3 orchestrate.py main   --e1 X --e2 Y                        full protocol for accum 4 and 8, eps in (0, e1, e2)
  python3 orchestrate.py report                                      raw/*.json -> RESULTS tables (markdown on stdout)

Environment: SCRATCH (big temp dir; default the session scratchpad), TREE (the built custom_io tree), DATA (the tiny data dir made by the pack's test helper).
"""
import argparse, concurrent.futures as cf, json, os, shutil, subprocess, sys
import itertools

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.environ.get('SCRATCH', '/tmp/claude-0/-home-user/ae36d9ec-1ca3-57a5-b846-46c890151b0f/scratchpad/posctrl')
TREE, DATA = os.environ.get('TREE', SCR + '/tree'), os.environ.get('DATA', SCR + '/data')
RAW = os.path.join(HERE, 'raw')
CFG = dict(d=48, n_heads=2, reader_layers=1, blocks=1, mlp=2.0, n_loops=12, label='settled', span_copy=True, span_idx=True, span_end=True, ans_drill=0.25, any_round=True,
           gap_p=0.25, no_slots=True, no_place=True, bytes=True, as_written=True, writer_inner=24)
K, S_END = 30, 60                                      # checkpoint at 30, redo window = updates 31..60
FAULTS = ['opt_reset', 'opt_moments_zero', 'data_shift', 'rng_noreset', 'rng_global_noreset', 'rng_model_noreset', 'lr_step_off', 'weights_eps']
CONT = ('loss', 'prog', 'call', 'ans', 'stop')
DISC = ('stop_y', 'stop_acc', 'right_last', 'call_acc', 'eos_acc')
FLOOR = 1e-5                                           # one print quantum of the logged loss (train.py prints round(loss, 5))


def targs(out, accum, resume):
    a = ['--model', 'b3g2', '--cfg', json.dumps(CFG), '--data', DATA, '--steps', str(S_END), '--batch', '8', '--lr', '3e-3', '--warmup', '5', '--seed', '1', '--out', out,
         '--eval-batch', '8', '--caps', os.path.join(DATA, 'caps.json'), '--accum', str(accum), '--log-every', '1', '--ckpt-every', str(K)]
    return a + (['--resume'] if resume else [])


def run(name, accum, eps, fault='none', resume_from=None, extra_env=None):
    """one fresh process; -> list of train-line dicts (elapsed dropped). resume_from = a folder holding step-30.pt + .json to resume from."""
    out = os.path.join(SCR, 'runs', name)
    shutil.rmtree(out, ignore_errors=True)
    if resume_from:
        os.makedirs(os.path.join(out, 'ckpt'))
        for f in os.listdir(resume_from):
            shutil.copy(os.path.join(resume_from, f), os.path.join(out, 'ckpt', f))
    env = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONUTF8='1', POSCTRL_TREE=TREE, NOISE_EPS=repr(eps), FAULT=fault, **(extra_env or {}))
    p = subprocess.run([sys.executable, os.path.join(HERE, 'posctrl.py')] + targs(out, accum, bool(resume_from)), env=env, cwd=TREE, capture_output=True, text=True)
    assert p.returncode == 0, (name, p.stdout[-1500:], p.stderr[-3000:])
    ev = [json.loads(l) for l in p.stdout.splitlines() if l.startswith('{')]
    if resume_from:
        assert any(e.get('event') == 'resumed' and e['step'] == K for e in ev), (name, [e for e in ev if e.get('event') != 'train'][:6])
        if fault != 'none':
            assert any(e.get('event') == 'posctrl_fault' for e in ev), name
    tr = [{k: v for k, v in e.items() if k not in ('elapsed', 'event')} for e in ev if e.get('event') == 'train']
    assert [e['step'] for e in tr] == list(range(K + 1 if resume_from else 1, S_END + 1)), (name, [e['step'] for e in tr][:3])
    return tr


def cell(accum, eps, faults, n_healthy, suffix=''):
    """C, then n_healthy resumes and one resume per fault, all from C's step-30 checkpoint; the resumes in parallel (4 workers)."""
    tag = f'a{accum}_e{eps:g}{suffix}'
    C = run(f'{tag}_C', accum, eps)
    ck = os.path.join(SCR, 'runs', f'{tag}_C', 'ckpt')
    keep = os.path.join(SCR, 'ck30', tag)
    shutil.rmtree(keep, ignore_errors=True); os.makedirs(keep)
    for f in ('step-30.pt', 'step-30.json'):
        shutil.copy(os.path.join(ck, f), keep)
    jobs = {f'R{i + 1}': 'none' for i in range(n_healthy)}
    jobs.update({f'F_{f}': f for f in faults})
    res = {}
    with cf.ThreadPoolExecutor(4) as ex:
        futs = {k: ex.submit(run, f'{tag}_{k}', accum, eps, fl, keep) for k, fl in jobs.items()}
        for k, f in futs.items():
            res[k] = f.result()
    out = dict(accum=accum, eps=eps, K=K, S_END=S_END, C=C, runs=res)
    return out


def mean(x):
    x = list(x)
    return sum(x) / len(x) if x else float('nan')


def stats(a, b):
    """a, b: train-line lists of the redone window. -> dict of per-update diffs (a - b) of the loss and summaries."""
    d = [x['loss'] - y['loss'] for x, y in zip(a, b)]
    ab = [abs(v) for v in d]
    return dict(first_diff=ab[0], early_max=max(ab[:3]), mean_abs=mean(ab), max_abs=max(ab), signed_mean=mean(d), diffs=d)


def window(tr):
    return [e for e in tr if e['step'] > K]


def exact_mismatch(a, b):
    """first update at which a field outside CONT+DISC differs (these are data / RNG / lr derived and must match exactly in a healthy redo) + the field names there."""
    for x, y in zip(a, b):
        bad = [k for k in x if k not in CONT and k not in DISC and x[k] != y.get(k)]
        if bad:
            return x['step'], bad
    return None, []


def save(res):
    os.makedirs(RAW, exist_ok=True)
    json.dump(res, open(os.path.join(RAW, f'a{res["accum"]}_e{res["eps"]:g}.json'), 'w'))


def cmd_calib(a):
    rows = []
    for accum in a.accum:
        for eps in a.eps:
            r = cell(accum, eps, [], 2)
            C = window(r['C']); R1, R2 = window(r['runs']['R1']), window(r['runs']['R2'])
            lvl = mean(abs(e['loss']) for e in C)
            s1, s2, s12 = stats(R1, C), stats(R2, C), stats(R1, R2)
            line = f'accum {accum} eps {eps:g}: loss level {lvl:.4f}  mean|dL| R1-C {s1["mean_abs"]:.5f} ({100 * s1["mean_abs"] / lvl:.3f}%)  R2-C {s2["mean_abs"]:.5f} ({100 * s2["mean_abs"] / lvl:.3f}%)  R1-R2 {s12["mean_abs"]:.5f}  first {s1["first_diff"]:.1e} early_max {s1["early_max"]:.1e}'
            print(line, flush=True)
            rows.append(line)
    open(os.path.join(SCR, 'calib.txt'), 'a').write('\n'.join(rows) + '\n')


def cmd_main(a):
    for accum in (4, 8):
        for eps in [0.0] + list(a.extra_eps) + [a.e1, a.e2]:
            if os.path.exists(os.path.join(RAW, f'a{accum}_e{eps:g}.json')) and not a.redo:
                continue
            r = cell(accum, eps, FAULTS, 4)
            save(r)
            print('done', accum, eps, flush=True)


def analyse(r):
    C = window(r['C'])
    H = {k: window(v) for k, v in r['runs'].items() if k.startswith('R')}
    F = {k[2:]: window(v) for k, v in r['runs'].items() if k.startswith('F_')}
    hc = {k: stats(v, C) for k, v in H.items()}
    pairs = {(i, j): stats(H[i], H[j]) for i, j in itertools.combinations(sorted(H), 2)}
    lvl = mean(abs(e['loss']) for e in C)
    nU = len(C)
    # healthy max at each redone update over every healthy comparison (R vs C and R vs R)
    hmax = [max([abs(s['diffs'][u]) for s in list(hc.values()) + list(pairs.values())]) for u in range(nU)]
    hmean_c = mean(s['mean_abs'] for s in hc.values())
    hmean_p = mean(s['mean_abs'] for s in pairs.values())
    healthy_exact = {k: exact_mismatch(window(r['runs'][k]), C) for k in H}
    # exchangeability: C and R1..R4 as five runs; mean |dL| of each run to the other four (C should not stand out)
    allr = dict(C=C, **H)
    dist = {}
    for a_ in allr:
        dist[a_] = mean(mean(abs(x['loss'] - y['loss']) for x, y in zip(allr[a_], allr[b_])) for b_ in allr if b_ != a_)
    order = sorted(dist, key=dist.get)
    out = dict(accum=r['accum'], eps=r['eps'], loss_level=lvl, healthy_exact_fields_first_mismatch={k: v[0] for k, v in healthy_exact.items()},
               five_run_mean_dist=dist, C_rank_of_5=order.index('C') + 1, healthy_vs_C=hc, healthy_pairs={f'{i}-{j}': s for (i, j), s in pairs.items()}, hmax=hmax,
               healthy_mean_vs_C=hmean_c, healthy_mean_pairs=hmean_p, D_over_N=(hmean_c / hmean_p if hmean_p > 0 else None), steps=[e['step'] for e in C])
    ff = {}
    for k, tr in F.items():
        s = stats(tr, C)
        thr = [10 * max(h, FLOOR) for h in hmax]
        first_exc = next((C[u]['step'] for u in range(nU) if abs(s['diffs'][u]) > thr[u]), None)
        first_nonzero = next((C[u]['step'] for u in range(nU) if s['diffs'][u] != 0), None)
        em = exact_mismatch(tr, C)
        s.update(ratio_to_healthy=(s['mean_abs'] / hmean_c if hmean_c > 0 else None), first_exceed_10x=first_exc, first_nonzero_step=first_nonzero,
                 exact_fields_first_mismatch=em[0], exact_fields_bad=em[1][:6])
        ff[k] = s
    out['faults'] = ff
    return out


def f(x, n=5):
    return 'n/a' if x is None else (f'{x:.{n}f}' if abs(x) >= 1e-3 or x == 0 else f'{x:.2e}')


def cmd_wsweep(a):
    """weights_eps sensitivity: resume from the saved step-30 checkpoint of an existing cell with the weight perturbation scaled down; vs the stored C."""
    out = {}
    for accum, eps in ((4, 0.0), (4, 0.01), (8, 0.0)):
        r = json.load(open(os.path.join(RAW, f'a{accum}_e{eps:g}.json')))
        C = window(r['C'])
        keep = os.path.join(SCR, 'ck30', f'a{accum}_e{eps:g}')
        ws = [1e-3, 1e-4, 1e-5, 1e-6, 1e-7]
        with cf.ThreadPoolExecutor(4) as ex:
            futs = {w: ex.submit(run, f'ws_a{accum}_e{eps:g}_{w:g}', accum, eps, 'weights_eps', keep, dict(WEIGHTS_EPS=repr(w))) for w in ws}
            for w, fu in futs.items():
                s = stats(window(fu.result()), C)
                out[f'a{accum}_e{eps:g}_w{w:g}'] = dict(first_diff=s['first_diff'], early_max=s['early_max'], mean_abs=s['mean_abs'], max_abs=s['max_abs'], diffs=s['diffs'])
                print(f'accum {accum} noise eps {eps:g} weights_eps {w:g}: u31 diff {s["first_diff"]:.2e} early_max {s["early_max"]:.2e} mean_abs {s["mean_abs"]:.2e} max_abs {s["max_abs"]:.2e}', flush=True)
    json.dump(out, open(os.path.join(RAW, 'weights_eps_sweep.json'), 'w'))


def cmd_repeat(a):
    """healthy-only replicates of a cell (fresh C, fresh R1..R4): is D/N ~ 1 and is C an outlier among the five?"""
    for accum in a.accum:
        for i in range(a.n):
            r = cell(accum, a.eps, [], 4, suffix=f'_rep{i + 1}')
            r['rep'] = i + 1
            json.dump(r, open(os.path.join(RAW, f'rep_a{accum}_e{a.eps:g}_{i + 1}.json'), 'w'))
            o = analyse(r)
            print(f'rep accum {accum} eps {a.eps:g} #{i + 1}: mean_abs R-C {o["healthy_mean_vs_C"]:.5f}  R-R {o["healthy_mean_pairs"]:.5f}  D/N {o["D_over_N"]:.3f}  C rank of 5: {o["C_rank_of_5"]}  signed mean(R-C) {mean(h["signed_mean"] for h in o["healthy_vs_C"].values()):.5f}', flush=True)


def cmd_report(a):
    import glob
    cells = [analyse(json.load(open(p))) for p in sorted([p for p in glob.glob(os.path.join(RAW, 'a*_e*.json')) if 'sweep' not in p and not os.path.basename(p).startswith('rep_')])]
    cells.sort(key=lambda o: (o['accum'], o['eps']))
    L = ['### Table A: healthy redo (4 resumes R1..R4, each a fresh process with its own noise) over updates 31..60', '',
         '| accum | NOISE_EPS | loss level (mean C, 31..60) | first_diff (u31) mean R-C | early_max (u31..33) mean | mean_abs R-C | mean_abs/level | max_abs R-C (max of 4) | signed mean R-C | mean_abs R-R pairs | mean_abs R-C (each of R1..R4) | D/N | C rank of 5 (1 = most central) | healthy exact-field mismatch |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for o in cells:
        hc = list(o['healthy_vs_C'].values())
        L.append(f"| {o['accum']} | {o['eps']:g} | {o['loss_level']:.4f} | {f(mean(h['first_diff'] for h in hc))} | {f(mean(h['early_max'] for h in hc))} | {f(o['healthy_mean_vs_C'])} | {100 * o['healthy_mean_vs_C'] / o['loss_level']:.4f}% | "
                 f"{f(max(h['max_abs'] for h in hc))} | {f(mean(h['signed_mean'] for h in hc))} | {f(o['healthy_mean_pairs'])} | {', '.join(f(h['mean_abs']) for h in hc)} | {f(o['D_over_N'], 3)} | {o['C_rank_of_5']} | {set(o['healthy_exact_fields_first_mismatch'].values())} |")
    L += ['', '### Table B: faulty resumes (same NOISE_EPS as the healthy ones, one fresh process each) vs C over updates 31..60', '',
          '"u31 diff" = |loss(R) - loss(C)| at the first redone update (0 = exact match of the logged 5-decimal loss). "first nonzero" = first redone update at which the loss differs at all. "exact-field mismatch" = first update at which a field that must be exactly equal in a healthy redo (lr, rounds, plan_*, drill_share, copy_share, stop_w, cap_hits) differs. "x healthy" = mean_abs / healthy mean_abs(R,C). ">10x" = first redone update where |dL| > 10 * max(healthy max at that update over all R-C and R-R comparisons, 1e-5).', '',
          '| accum | NOISE_EPS | fault | u31 diff | first nonzero | exact-field mismatch (update: fields) | early_max | mean_abs | max_abs | signed mean | x healthy (mean_abs) | >10x at update |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for o in cells:
        for k, s in o['faults'].items():
            em = f"{s['exact_fields_first_mismatch']}: {','.join(s['exact_fields_bad'])}" if s['exact_fields_first_mismatch'] else 'none'
            L.append(f"| {o['accum']} | {o['eps']:g} | {k} | {f(s['first_diff'])} | {s['first_nonzero_step']} | {em} | {f(s['early_max'])} | {f(s['mean_abs'])} | {f(s['max_abs'])} | {f(s['signed_mean'])} | {f(s['ratio_to_healthy'], 1) if s['ratio_to_healthy'] is not None else 'n/a (healthy=0)'} | {s['first_exceed_10x']} |")
    open(os.path.join(HERE, 'tables.md'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    c = sp.add_parser('calib'); c.add_argument('--accum', type=int, nargs='+', default=[4, 8]); c.add_argument('--eps', type=float, nargs='+', required=True)
    m = sp.add_parser('main'); m.add_argument('--e1', type=float, required=True); m.add_argument('--e2', type=float, required=True); m.add_argument('--redo', action='store_true'); m.add_argument('--extra-eps', type=float, nargs='*', default=[])
    sp.add_parser('report'); sp.add_parser('wsweep')
    rp = sp.add_parser('repeat'); rp.add_argument('--accum', type=int, nargs='+', default=[8]); rp.add_argument('--eps', type=float, default=1.0); rp.add_argument('--n', type=int, default=3)
    a = ap.parse_args()
    {'calib': cmd_calib, 'main': cmd_main, 'report': cmd_report, 'wsweep': cmd_wsweep, 'repeat': cmd_repeat}[a.cmd](a)
