"""python3 -m custom_io.tests.test_ckpt_b3g2   (CPU, tiny b3g2 (eg_embed off), a few minutes; run with OMP_NUM_THREADS=1)
The checkpoint / resume overlay (train.py --ckpt-every / --resume, written for the AT run) on the model G2f-a4 trains: b3g2 at accum 4, per-update log lines.
Needs custom_io/tests/test_ckpt.py (the overlay's own test, for its helpers) in the same folder, and BASE_TREE=<dir holding custom_io with the UNMODIFIED train.py of the same commit>
(or a git checkout with that commit: BASE_REPO + BASE_COMMIT, default 74d6e92c75).
(1) flags off == the unmodified train.py: same 40-update loss trace and same final state_dict (accum 4, log-every 1);
(2) --ckpt-every on == flags off (writing checkpoints changes nothing);
(3) a hard kill in the MIDDLE of a checkpoint interval (the process dies right after the step-22 train line; the newest checkpoint is step 15), then the same command line with
    --resume: the resumed segment redoes updates 16..22 and its losses equal the first segment's (the trace of G2f-a4's R4 test), and the whole trace and the final weights equal
    the uninterrupted run; the events of both segments are in B3G2/events.jsonl;
(4) a changed --log-every / --ckpt-every / --accum at the restart resumes (they are not in the config hash);
(5) none: the random streams (python, numpy, torch CPU/CUDA, the model's own random.Random objects) are listed by test_ckpt.py.
"Equal" means BIT FOR BIT when this machine is bit-reproducible (the same command run twice gives identical traces and weights: true in the sandbox where this was written).
On a machine whose CPU runs are NOT bit-reproducible (the PC: the unmodified train.py differs from itself between two runs from update 4 on) the test first measures that noise
(the unmodified train.py run twice), then allows a difference of 20x the noise seen so far (floors: 2e-4 relative on the loss terms, 0.05 on the accuracy-type fields, 1e-5 on
the weights); the random/plan fields (lr, rounds = the drawn loop length, plan_*, drill_share, cap_hits, ...) must still be EXACTLY equal, so a shifted random stream is caught
by those and by the loss; and a control run with another seed must differ by at least 5x the allowed difference, else the test says it cannot tell and FAILS."""
import json, os, shutil, subprocess, sys
import torch
from custom_io.tests import test_ckpt as T

CFG = dict(d=48, n_heads=2, reader_layers=1, blocks=1, mlp=2.0, n_loops=12, label='settled', span_copy=True, span_idx=True, span_end=True, ans_drill=0.25, any_round=True,
           gap_p=0.25, no_slots=True, no_place=True, bytes=True, as_written=True, writer_inner=24)
N = 40


def base_tree():
    if os.environ.get('BASE_TREE'):
        return os.environ['BASE_TREE']
    d = os.path.join(T.TMP, 'base')
    os.makedirs(d)
    repo, commit = os.environ.get('BASE_REPO', T.HERE), os.environ.get('BASE_COMMIT', '74d6e92c75')
    p = subprocess.run(f'git -C "{repo}" archive {commit} custom_io | tar -x -C "{d}"', shell=True, capture_output=True, text=True)
    assert p.returncode == 0 and os.path.exists(os.path.join(d, 'custom_io', 'train.py')), 'no base tree: set BASE_TREE or BASE_REPO\n' + p.stderr
    return d


def argv(data, out, steps, accum=4, extra=()):
    return ['--model', 'b3g2', '--cfg', json.dumps(CFG), '--data', data, '--steps', str(steps), '--batch', '8', '--lr', '3e-3', '--warmup', '5', '--seed', '1', '--out', out,
            '--eval-batch', '8', '--caps', os.path.join(data, 'caps.json'), '--accum', str(accum), '--log-every', '1'] + list(extra)


def run_kill_after_line(tree, args, step, timeout=1800):
    """python -m custom_io.train ARGS; os._exit(137) right after the `train` line of update `step` is printed (a kill in the middle of a checkpoint interval)."""
    drv = ('import os, sys\nimport custom_io.train as T\norig = T.jprint\n'
           'def jp(*a, **k):\n    r = orig(*a, **k)\n'
           f'    if k.get("event") == "train" and k.get("step") == {step}:\n        sys.stdout.flush(); os._exit(137)\n    return r\n'
           'T.jprint = jp\nT.main(sys.argv[1:])\n')
    p = subprocess.run([sys.executable, '-c', drv] + args, cwd=tree, env=dict(T.ENV, PYTHONPATH=tree + os.pathsep + os.environ.get('PYTHONPATH', '')), capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


CONT = ('loss', 'prog', 'call', 'ans', 'stop')                                 # continuous train-line fields: compared with a tolerance on a noisy machine
DISC = ('stop_y', 'stop_acc', 'right_last', 'call_acc', 'eos_acc')              # model-output counts (an argmax can flip with float noise): wide floor
FACTOR, REL_FLOOR, DISC_FLOOR, W_FLOOR = 20.0, 2e-4, 0.05, 1e-5                 # every other field is data/RNG-derived and must be exactly equal


def tdiff(ta, tb, what):
    """per update {field: |a - b|} over CONT + DISC; the updates, the field names and every other field must be equal."""
    sa, sb = [e['step'] for e in ta], [e['step'] for e in tb]
    assert sa == sb, f'{what}: different updates {sa[:3]}... vs {sb[:3]}...'
    out = {}
    for ea, eb in zip(ta, tb):
        assert set(ea) == set(eb), f'{what}: update {ea["step"]}: fields {sorted(set(ea) ^ set(eb))} differ'
        d = {}
        for k in ea:
            if k in CONT or k in DISC:
                d[k] = abs(ea[k] - eb[k])
            else:
                assert ea[k] == eb[k], f'{what}: update {ea["step"]}: {k} = {ea[k]!r} vs {eb[k]!r} (must be exactly equal)'
        out[ea['step']] = d
    return out


def wdiff(a, b):
    """largest |a - b| over the float tensors; the keys, shapes and any non-float tensor must be equal."""
    assert list(a) == list(b), (list(a)[:5], list(b)[:5])
    m = 0.0
    for k in a:
        assert a[k].shape == b[k].shape, k
        if a[k].is_floating_point():
            m = max(m, float((a[k].double() - b[k].double()).abs().max())) if a[k].numel() else m
        else:
            assert torch.equal(a[k], b[k]), k
    return m


class Noise:
    """What this machine does to the same command run twice (the unmodified train.py): exact = no difference at all (then every comparison is bit for bit)."""

    def __init__(self, ta, tb, sa, sb):
        d = tdiff(ta, tb, 'noise: unmodified train.py twice')
        self.env, run = {}, {}                              # running maximum per field, by update
        for s in sorted(d):
            for k, v in d[s].items():
                run[k] = max(run.get(k, 0.0), v)
            self.env[s] = dict(run)
        self.w = wdiff(sa, sb)
        self.exact = self.w == 0.0 and all(v == 0.0 for r in self.env.values() for v in r.values())
        if os.environ.get('CKPT_TEST_FORCE_TOL'):                 # rehearse the tolerance path on a bit-reproducible machine (floors only)
            self.exact = False

    def tol(self, k, s, ref):
        if self.exact:
            return 0.0
        floor = DISC_FLOOR if k in DISC else REL_FLOOR * max(1.0, abs(ref))
        e = self.env.get(s) or (self.env[max(self.env)] if s > max(self.env) else {})
        return max(FACTOR * e.get(k, 0.0), floor)

    def w_tol(self):
        return 0.0 if self.exact else max(FACTOR * self.w, W_FLOOR)

    def check(self, ta, tb, what):
        d = tdiff(ta, tb, what)
        worst = 0.0
        for e in tb:
            for k, v in d[e['step']].items():
                t = self.tol(k, e['step'], e[k])
                assert v <= t, f'{what}: update {e["step"]}: {k} differs by {v:.3g} (allowed {t:.3g}; {a_or_b(ta, tb, e["step"], k)})'
                worst = max(worst, v / t if t else 0.0)
        return worst

    def check_w(self, a, b, what):
        m, t = wdiff(a, b), self.w_tol()
        assert m <= t, f'{what}: final weights differ by {m:.3g} (allowed {t:.3g})'
        return m


def a_or_b(ta, tb, s, k):
    x = next(e[k] for e in ta if e['step'] == s)
    y = next(e[k] for e in tb if e['step'] == s)
    return f'{x} vs {y}'


def main():
    torch.set_num_threads(1)
    here, base = T.HERE, base_tree()
    data = T.make_data()

    def go(name, tree, extra=(), steps=N, accum=4):
        out = os.path.join(T.TMP, name)
        rc, so, se = T.run(tree, argv(data, out, steps, accum, extra))
        assert rc == 0, f'{name}: rc {rc}\n{so[-2000:]}\n{se[-3000:]}'
        return so, out

    # the machine's own noise: the unmodified train.py twice
    so_b, out_b = go('base', base)
    so_b2, out_b2 = go('base2', base)
    sb, sb2 = T.load_sd(out_b), T.load_sd(out_b2)
    nz = Noise(T.trace(so_b), T.trace(so_b2), sb, sb2)
    if nz.exact:
        print('machine noise: none (the unmodified train.py gives identical traces and weights twice): every check below is bit for bit')
    else:
        big = max((v for r in nz.env.values() for k, v in r.items() if k in CONT), default=0.0)
        print(f'machine noise: the unmodified train.py differs from itself (largest loss-term difference {big:.3g}, weights {nz.w:.3g}): checks below allow {FACTOR:g}x that (floors {REL_FLOOR:g} relative, {DISC_FLOOR:g} on the accuracy fields, {W_FLOOR:g} on weights)')

    # (1) flags off == the unmodified train.py
    so_n, out_n = go('new_off', here)
    r1 = nz.check(T.trace(so_b), T.trace(so_n), '(1) loss trace, base vs overlay with the flags off')
    sn = T.load_sd(out_n)
    w1 = nz.check_w(sb, sn, '(1) flags off')
    print('ok (1) flags off: %d-update trace and final weights equal to the unmodified train.py (%s; worst trace difference %.2f of the allowed, weights %.3g)' % (N, 'bit for bit' if nz.exact else 'within the machine noise', r1, w1))

    # (2) checkpoints on == off
    so_c, out_c = go('ckpt_on', here, ['--ckpt-every', '10'])
    r2 = nz.check(T.trace(so_n), T.trace(so_c), '(2) loss trace with --ckpt-every 10')
    w2 = nz.check_w(sn, T.load_sd(out_c), '(2) --ckpt-every 10')
    print('ok (2) --ckpt-every 10 changes nothing (trace and weights; worst %.2f of the allowed, weights %.3g)' % (r2, w2))

    # (3) a kill in the middle of an interval, then --resume
    out_k = os.path.join(T.TMP, 'killed')
    a = argv(data, out_k, N, 4, ['--ckpt-every', '15', '--resume'])
    rc, so1, se1 = run_kill_after_line(here, a, 22)
    assert rc == 137, (rc, so1[-1500:], se1[-2500:])
    t1 = T.trace(so1)
    assert t1[-1]['step'] == 22 and os.path.exists(os.path.join(out_k, 'ckpt', 'step-15.pt')) and not os.path.exists(os.path.join(out_k, 'ckpt', 'step-30.pt'))
    rc, so2, se2 = T.run(here, a)
    assert rc == 0, (so2[-1500:], se2[-2500:])
    ev2 = T.events(so2)
    assert any(e.get('event') == 'resumed' and e['step'] == 15 for e in ev2), [e for e in ev2 if e.get('event') in ('resumed', 'resume_warning')]
    t2 = T.trace(so2)
    assert [e['step'] for e in t2][:1] == [16], t2[:1]
    redo1 = [e for e in t1 if e['step'] > 15]
    assert redo1, t1[-3:]
    r3a = nz.check(redo1, [e for e in t2 if e['step'] <= 22], '(3) the redone updates 16..22 vs the first segment')
    merged = [e for e in t1 if e['step'] <= 15] + t2
    r3b = nz.check(T.trace(so_n), merged, '(3) merged trace (segment 1 up to the checkpoint + resumed segment) vs the uninterrupted run')
    w3 = nz.check_w(sn, T.load_sd(out_k), '(3) after kill + resume')
    print('ok (3) killed at update 22 (checkpoint 15): redone updates 16..22 equal the first segment (%s; worst %.2f of the allowed); whole trace (worst %.2f) and final weights (%.3g) equal the uninterrupted run' % ('bit for bit' if nz.exact else 'within the machine noise', r3a, r3b, w3))

    # (4) a changed log-every / ckpt-every / accum at the restart still resumes
    out_m = os.path.join(T.TMP, 'changed')
    rc, so1, se1 = run_kill_after_line(here, argv(data, out_m, N, 4, ['--ckpt-every', '15', '--resume']), 22)
    assert rc == 137
    rc, so3, se3 = T.run(here, argv(data, out_m, N, 8, ['--ckpt-every', '25', '--resume', '--log-every', '5']))
    assert rc == 0, (so3[-1500:], se3[-2500:])
    ev3 = T.events(so3)
    assert any(e.get('event') == 'resumed' and e['step'] == 15 for e in ev3) and any(e.get('event') == 'resume_warning' for e in ev3)
    print('ok (4) a restart with another --log-every, --ckpt-every and --accum resumes (with the accum warning)')

    # (5) the control: a run that SHOULD differ (another seed) must differ by far more than the allowed difference, else this test cannot tell a broken resume from noise
    if not nz.exact:
        so_s, out_s = go('seed2', here, ['--seed', '2'])
        tb_, ts_ = T.trace(so_b), T.trace(so_s)
        assert [e['step'] for e in tb_] == [e['step'] for e in ts_]
        losses = sorted(abs(x['loss'] - y['loss']) for x, y in zip(tb_, ts_))
        med = losses[len(losses) // 2]
        allowed = max(nz.tol('loss', e['step'], e['loss']) for e in tb_)
        wd = wdiff(sb, T.load_sd(out_s))
        assert med >= 5 * allowed and wd >= 5 * nz.w_tol(), f'(5) the test cannot tell: a run with another seed differs by (median loss {med:.3g}, weights {wd:.3g}) but the allowed differences are (loss {allowed:.3g}, weights {nz.w_tol():.3g})'
        print(f'ok (5) control: another seed differs by {med:.3g} (median loss) and {wd:.3g} (weights), at least 5x the allowed {allowed:.3g} and {nz.w_tol():.3g}: a broken resume would be seen')

    print('ALL OK')


if __name__ == '__main__':
    main()
