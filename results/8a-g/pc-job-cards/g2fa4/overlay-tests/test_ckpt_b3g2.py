"""python3 -m custom_io.tests.test_ckpt_b3g2   (CPU, tiny b3g2 (eg_embed off), a few minutes; run with OMP_NUM_THREADS=1)
The checkpoint / resume overlay (train.py --ckpt-every / --resume, written for the AT run) on the model G2f-a4 trains: b3g2 at accum 4, per-update log lines.
Needs custom_io/tests/test_ckpt.py (the overlay's own test, for its helpers) in the same folder, and BASE_TREE=<dir holding custom_io with the UNMODIFIED train.py of the same commit>
(or a git checkout with that commit: BASE_REPO + BASE_COMMIT, default 74d6e92c75).
(1) flags off == the unmodified train.py: same 40-update loss trace and same final state_dict, bit for bit (accum 4, log-every 1);
(2) --ckpt-every on == flags off (writing checkpoints changes nothing);
(3) a hard kill in the MIDDLE of a checkpoint interval (the process dies right after the step-45 train line; the newest checkpoint is step 30), then the same command line with
    --resume: the resumed segment redoes updates 31..45 and its losses equal the first segment's (the trace of G2f-a4's R4 test), and the whole trace and the final weights equal
    the uninterrupted run, bit for bit; the events of both segments are in B3G2/events.jsonl;
(4) a changed --log-every / --ckpt-every / --accum at the restart resumes (they are not in the config hash);
(5) none: the random streams (python, numpy, torch CPU/CUDA, the model's own random.Random objects) are listed by test_ckpt.py."""
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


def same(a, b, what):
    assert a == b, f'{what} differs:\n{a[:3]}...\n{b[:3]}...'


def main():
    torch.set_num_threads(1)
    here, base = T.HERE, base_tree()
    data = T.make_data()
    res = {}

    def go(name, tree, extra=(), steps=N, accum=4):
        out = os.path.join(T.TMP, name)
        rc, so, se = T.run(tree, argv(data, out, steps, accum, extra))
        assert rc == 0, f'{name}: rc {rc}\n{so[-2000:]}\n{se[-3000:]}'
        res[name] = (so, out)
        return so, out

    # (1) flags off == the unmodified train.py
    so_b, out_b = go('base', base)
    so_n, out_n = go('new_off', here)
    same(T.trace(so_b), T.trace(so_n), '(1) loss trace, base vs overlay with the flags off')
    sb, sn = T.load_sd(out_b), T.load_sd(out_n)
    assert set(sb) == set(sn) and all(torch.equal(sb[k], sn[k]) for k in sb), '(1) final weights differ with the flags off'
    print('ok (1) flags off: %d-update loss trace and final weights identical to the unmodified train.py' % N)

    # (2) checkpoints on == off
    so_c, out_c = go('ckpt_on', here, ['--ckpt-every', '10'])
    same(T.trace(so_n), T.trace(so_c), '(2) loss trace with --ckpt-every 10')
    sc = T.load_sd(out_c)
    assert all(torch.equal(sn[k], sc[k]) for k in sn), '(2) final weights differ with --ckpt-every 10'
    print('ok (2) --ckpt-every 10 changes nothing (trace and weights)')

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
    redo = {e['step']: e for e in t1 if e['step'] > 15}
    assert redo and all(redo[s] == e for s in redo for e in [next(x for x in t2 if x['step'] == s)]), '(3) the redone updates 16..22 do not reproduce the first segment'
    merged = [e for e in t1 if e['step'] <= 15] + t2
    same(merged, T.trace(so_n), '(3) merged trace (segment 1 up to the checkpoint + resumed segment) vs the uninterrupted run')
    sk = T.load_sd(out_k)
    assert all(torch.equal(sn[k], sk[k]) for k in sn), '(3) final weights differ after kill + resume'
    print('ok (3) killed at update 22 (checkpoint 15): redone updates 16..22 equal the first segment; whole trace and final weights equal the uninterrupted run, bit for bit')

    # (4) a changed log-every / ckpt-every / accum at the restart still resumes
    out_m = os.path.join(T.TMP, 'changed')
    rc, so1, se1 = run_kill_after_line(here, argv(data, out_m, N, 4, ['--ckpt-every', '15', '--resume']), 22)
    assert rc == 137
    rc, so3, se3 = T.run(here, argv(data, out_m, N, 8, ['--ckpt-every', '25', '--resume', '--log-every', '5']))
    assert rc == 0, (so3[-1500:], se3[-2500:])
    ev3 = T.events(so3)
    assert any(e.get('event') == 'resumed' and e['step'] == 15 for e in ev3) and any(e.get('event') == 'resume_warning' for e in ev3)
    print('ok (4) a restart with another --log-every, --ckpt-every and --accum resumes (with the accum warning)')

    print('ALL OK')


if __name__ == '__main__':
    main()
