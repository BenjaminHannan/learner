"""python3 -m custom_io.tests.test_ckpt   (CPU, tiny models, a few minutes; run with OMP_NUM_THREADS=1)
train.py --ckpt-every N / --resume (periodic checkpoint + resume for the long runs):
(1) default off == the unmodified train.py: the base tree (BASE_TREE=<dir holding custom_io of commit 6e72a5fae5>; or `git archive 6e72a5fae5 custom_io` into a temp dir when run
    inside a git checkout that has that commit) and this tree give the same 40-update loss trace, the same final state_dict (bit for bit) and the same RESULT.json keys,
    for the plain model (plain_tf) and for the agent model (b3at, arm AT);
(2) interrupted == uninterrupted: 60 updates straight vs 30, a hard kill right after the step-30 checkpoint (os._exit), `--resume`, 30 more: the same loss trace and the same
    weights, bit for bit, for plain_tf (with quick evals and a log window that does not line up with the checkpoint) and for b3at (ans_drill and gap_p on, so the model's own
    random.Random streams are drawn); the random streams found are listed;
(3) a corrupt / truncated / sidecar-less newest checkpoint falls back to the previous one; a changed config or data refuses (rc 1); `--resume` with nothing to resume starts at
    step 0; every checkpoint corrupt refuses; a kill between the temp write and os.replace leaves no step file; batches_from(skip) is data.train_batches started later."""
import json, os, shutil, subprocess, sys, tempfile
import torch

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))      # the tree under test (holds custom_io/)
ENV = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONUTF8='1')
TMP = tempfile.mkdtemp(prefix='ckpt-test-')


def base_tree():
    """The tree of commit 6e72a5fae5 (unmodified train.py): $BASE_TREE, else git archive of that commit from the repo containing this file or from $BASE_REPO."""
    if os.environ.get('BASE_TREE'):
        return os.environ['BASE_TREE']
    d = os.path.join(TMP, 'base')
    os.makedirs(d)
    repo = os.environ.get('BASE_REPO', HERE)
    p = subprocess.run(f'git -C "{repo}" archive 6e72a5fae5 custom_io | tar -x -C "{d}"', shell=True, capture_output=True, text=True)
    assert p.returncode == 0 and os.path.exists(os.path.join(d, 'custom_io', 'train.py')), 'no base tree: set BASE_TREE or BASE_REPO\n' + p.stderr
    return d


def rows(n, off=0):
    rs = []
    for i in range(n):
        a, b, c = 10 + 7 * (i + off), 100 + 13 * (i + off), 3 + i % 5
        k = i % 3
        if k == 0:
            rs.append(dict(id=f'a{i + off}', family='chain_ops', prompt=f'Tom has {a} apples and buys {b} more. How many apples now?', answer=str(a + b), accepted=[str(a + b)], level=1, variant='v', stage=1, steps=[f'{a} + {b} = {a + b}']))
        elif k == 1:
            rs.append(dict(id=f'a{i + off}', family='copy_word', prompt=f'Echo: sune{i} Give only the answer.', answer=f'sune{i}', accepted=[f'sune{i}'], level=1, variant='v', stage=1, steps=[]))
        else:
            rs.append(dict(id=f'a{i + off}', family='chain_story2', prompt=f'Facts: Xavi had {a} cards. Then Xavi got {b} more. After that, Xavi lost {c}. How many now?', answer=str(a + b - c),
                           accepted=[str(a + b - c)], level=2, variant='v', stage=1, steps=[f'{a} + {b} = {a + b}', f'{a + b} - {c} = {a + b - c}']))
    return rs


def make_data(name='data', n=48):
    d = os.path.join(TMP, name)
    os.makedirs(os.path.join(d, 'dev'))
    with open(os.path.join(d, 'train.jsonl'), 'w') as f:
        for r in rows(n):
            f.write(json.dumps(r) + '\n')
    for s in ['in_dist', 'answer', 'frame', 'vocab', 'variant', 'family']:
        with open(os.path.join(d, 'dev', s + '.jsonl'), 'w') as f:
            for r in rows(12, 100):
                f.write(json.dumps(dict(r, id=r['id'] + s)) + '\n')
    caps = os.path.join(d, 'caps.json')
    json.dump(dict(max_prompt=400, max_ans=12, n_num=16, w_max=80, n_res=11, n_reg=13, plain_target=64, le=95), open(caps, 'w'))
    return d


PLAIN = dict(model='plain_tf', cfg=dict(d_model=32, n_layers=1, n_heads=2), extra=['--log-every', '7', '--eval-every', '20'])
AGENT = dict(model='b3at', cfg=dict(d=48, n_heads=2, reader_layers=1, blocks=1, mlp=2.0, n_loops=12, label='settled', span_copy=True, span_idx=True, span_end=True, ans_drill=0.5,
                                    any_round=True, gap_p=0.5, no_slots=True, no_place=True, bytes=True, as_written=True, writer_inner=24), extra=['--log-every', '3', '--caps', 'CAPS'])


def argv(kind, data, out, steps, extra=()):
    k = AGENT if kind == 'agent' else PLAIN
    a = ['--model', k['model'], '--cfg', json.dumps(k['cfg']), '--data', data, '--steps', str(steps), '--batch', '8', '--lr', '3e-3', '--warmup', '5', '--seed', '1', '--out', out,
         '--eval-batch', '8']
    a += [x if x != 'CAPS' else os.path.join(data, 'caps.json') for x in k['extra']]
    return a + list(extra)


def run(tree, args, kill_after=None, replace_crash=None, timeout=1800):
    """python -m custom_io.train ARGS in `tree`; -> (rc, stdout, stderr). kill_after=K: os._exit(137) right after the step-K checkpoint is completely written;
    replace_crash=K: os._exit(137) at the os.replace of step-K.pt (after the temp file is written and fsynced, before the rename)."""
    if kill_after is None and replace_crash is None:
        cmd = [sys.executable, '-m', 'custom_io.train'] + args
    else:
        drv = ('import os, sys\nimport custom_io.train as T\n'
               f'KILL, CRASH = {kill_after!r}, {replace_crash!r}\n'
               'if KILL is not None:\n'
               '    orig = T.save_ckpt\n'
               '    def save(ckdir, step, payload, side):\n'
               '        r = orig(ckdir, step, payload, side)\n'
               '        if step == KILL:\n'
               '            sys.stdout.flush(); os._exit(137)\n'
               '        return r\n'
               '    T.save_ckpt = save\n'
               'if CRASH is not None:\n'
               '    orig_replace = os.replace\n'
               '    def rep(src, dst):\n'
               '        if os.path.basename(dst) == "step-%d.pt" % CRASH:\n'
               '            sys.stdout.flush(); os._exit(137)\n'
               '        return orig_replace(src, dst)\n'
               '    os.replace = rep\n'
               'T.main(sys.argv[1:])\n')
        cmd = [sys.executable, '-c', drv] + args
    p = subprocess.run(cmd, cwd=tree, env=dict(ENV, PYTHONPATH=tree + os.pathsep + os.environ.get('PYTHONPATH', '')), capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def events(stdout):
    out = []
    for ln in stdout.splitlines():
        if ln.startswith('{'):
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    return out


def trace(stdout):
    """the train lines minus wall-clock fields: [(step, loss, lr, aux ...)]"""
    return [{k: v for k, v in e.items() if k != 'elapsed'} for e in events(stdout) if e.get('event') == 'train']


def load_sd(out):
    return torch.load(os.path.join(out, 'checkpoint.pt'), map_location='cpu', weights_only=False)['model']


def same_sd(a, b):
    assert list(a) == list(b), (list(a)[:5], list(b)[:5])
    bad = [k for k in a if not torch.equal(a[k], b[k])]
    assert not bad, f'{len(bad)} tensors differ, e.g. {bad[:5]}'


def result(out):
    return json.load(open(os.path.join(out, 'RESULT.json')))


def must(rc_out_err, what=''):
    rc, o, e = rc_out_err
    assert rc == 0, f'{what} rc={rc}\n{o[-2500:]}\n{e[-3500:]}'
    return o


def fresh(name):
    d = os.path.join(TMP, name)
    shutil.rmtree(d, ignore_errors=True)
    return d


# ------------------------------------------------------------------------------------------------------------------------------------------------ (1)
def test_default_off_equals_base(kind):
    data = make_data('d1-' + kind)
    steps = 40
    t_base, t_new = base_tree(), HERE
    ob, on = fresh('o1b-' + kind), fresh('o1n-' + kind)
    lb = must(run(t_base, argv(kind, data, ob, steps, ['--log-every', '1'])), 'base')
    ln = must(run(t_new, argv(kind, data, on, steps, ['--log-every', '1'])), 'new')
    tb, tn = trace(lb), trace(ln)
    assert len(tb) == steps and tb == tn, (tb[:2], tn[:2])
    same_sd(load_sd(ob), load_sd(on))
    rb, rn = result(ob), result(on)
    assert set(rb) == set(rn) and set(rb['config']) == set(rn['config']), (set(rb) ^ set(rn), set(rb['config']) ^ set(rn['config']))
    for k in ('steps', 'status', 'final_train_loss', 'n_params', 'cap_hits'):
        assert rb[k] == rn[k], (k, rb[k], rn[k])
    assert 'resumed_from' not in rn and 'ckpt' not in rn and not os.path.exists(os.path.join(on, 'ckpt')) and not os.path.exists(os.path.join(on, 'events.jsonl'))
    # the events other than wall-clock ones are the same lines too
    strip = lambda s: [{k: v for k, v in e.items() if k not in ('elapsed', 'wall_s', 'steps_per_s')} for e in events(s)]
    assert strip(lb) == strip(ln)
    print(f'ok (1) default off == base [{kind}]: {steps}-update loss trace, final state_dict ({len(load_sd(on))} tensors), RESULT.json keys and every event line identical')


# ------------------------------------------------------------------------------------------------------------------------------------------------ (2)
def test_interrupted_equals_uninterrupted(kind):
    data = make_data('d2-' + kind)
    N, K = 60, 30
    ck = ['--ckpt-every', str(K)]
    oa, ob, oc = fresh('o2a-' + kind), fresh('o2b-' + kind), fresh('o2c-' + kind)
    la = must(run(HERE, argv(kind, data, oa, N, ck)), 'straight')
    lc = must(run(HERE, argv(kind, data, oc, N)), 'ckpt off')
    rc, l1, e1 = run(HERE, argv(kind, data, ob, N, ck + ['--resume']), kill_after=K)
    assert rc == 137, (rc, l1[-1500:], e1[-2500:])
    assert not os.path.exists(os.path.join(ob, 'checkpoint.pt')) and not os.path.exists(os.path.join(ob, 'RESULT.json'))
    assert sorted(f for f in os.listdir(os.path.join(ob, 'ckpt'))) == [f'step-{K}.json', f'step-{K}.pt']
    assert not any(e.get('event') == 'resumed' for e in events(l1))                                       # --resume with an empty folder: a fresh start
    l2 = must(run(HERE, argv(kind, data, ob, N, ck + ['--resume'])), 'resumed')
    ev2 = events(l2)
    res = [e for e in ev2 if e.get('event') == 'resumed']
    assert len(res) == 1 and res[0]['step'] == K and res[0]['from'] == f'step-{K}.pt' and res[0]['msg'] == f'RESUMED step={K} from=step-{K}.pt', res
    assert f'RESUMED step={K} from=step-{K}.pt' in l2
    ta, t1, t2 = trace(la), trace(l1), trace(l2)
    assert [e for e in map(json.loads, open(os.path.join(ob, 'events.jsonl'))) if e['event'] == 'train' and 'elapsed' in e].__len__() == len(t1) + len(t2)      # events.jsonl holds both segments (stdout.txt of a restarted job holds the last)
    assert [e for e in t1 if e['step'] <= K] + t2 == ta, ([e for e in t1 if e['step'] <= K] + t2, ta)         # (the kill came at step K: t1 has no later line)
    assert ta == trace(lc), 'writing checkpoints changed the loss trace'
    same_sd(load_sd(oa), load_sd(ob))
    same_sd(load_sd(oa), load_sd(oc))
    # the final-step checkpoint (model, optimizer, every random stream, counters) is the same too
    pa, pb = (torch.load(os.path.join(o, 'ckpt', f'step-{N}.pt'), map_location='cpu', weights_only=False) for o in (oa, ob))
    same_sd(pa['model'], pb['model'])
    for k in pa['opt']['state']:
        for kk in pa['opt']['state'][k]:
            assert torch.equal(pa['opt']['state'][k][kk], pb['opt']['state'][k][kk]), ('optimizer', k, kk)
    assert pa['rng']['py'] == pb['rng']['py'] and torch.equal(pa['rng']['torch'], pb['rng']['torch'])
    assert all((x == y).all() if hasattr(x, 'all') else x == y for x, y in zip(pa['rng']['np'], pb['rng']['np']))
    assert pa['model_streams'][0] == pb['model_streams'][0], 'model-owned random streams differ'
    assert pa['loop']['last_loss'] == pb['loop']['last_loss'] and pa['loop']['run_n'] == pb['loop']['run_n'] and float(pa['loop']['run_loss']) == float(pb['loop']['run_loss'])
    sa, sb = pa['model_streams'][1], pb['model_streams'][1]
    # the model's counters: exact, except trace_stats, which the model counts once per distinct row of a cache (b3g2 trace_of) that starts empty after a resume: it can only count MORE
    for k in sa:
        if k.endswith('trace_stats'):
            assert all(sb[k][c] >= sa[k][c] for c in sa[k]), (sa[k], sb[k])
        else:
            assert sa[k] == sb[k], (k, sa[k], sb[k])
    exact = {k: ('exact' if sa[k] == sb[k] else f'resumed run counts more rows {sa[k]["rows"]} -> {sb[k]["rows"]}') for k in sa}
    ra, rb = result(oa), result(ob)
    assert ra['steps'] == rb['steps'] == N and ra['final_train_loss'] == rb['final_train_loss']
    assert ra['resumed_from'] == [] and rb['resumed_from'] == [K], (ra['resumed_from'], rb['resumed_from'])
    assert ra['cap_hits'] == rb['cap_hits'], (ra['cap_hits'], rb['cap_hits'])
    # wall time: the segments add up (the first segment's elapsed and eval time were restored; train_s = elapsed - eval time), steps_per_s = steps / train_s
    lp = torch.load(os.path.join(ob, 'ckpt', f'step-{K}.pt'), map_location='cpu', weights_only=False)['loop']       # the first segment's loop clock at its checkpoint
    assert rb['train_s'] >= pb['loop']['elapsed'] - pb['loop']['eval_s'] - 1e-6
    assert rb['train_s'] >= lp['elapsed'] - lp['eval_s'] - 1e-6 and abs(rb['steps_per_s'] - N / rb['train_s']) < 1e-6 * rb['steps_per_s']
    el2 = [e['elapsed'] for e in events(l2) if e.get('event') == 'train']
    assert el2[0] >= lp['elapsed'] - 1.0 and el2 == sorted(el2), (el2[:3], lp['elapsed'])             # the train lines' elapsed goes on from the first segment
    saved_elapsed = lp['elapsed'] - lp['eval_s']
    streams = sorted(pa['model_streams'][0])
    print(f'ok (2) interrupted == uninterrupted [{kind}]: {N} updates vs {K} + kill + --resume + {N - K}: loss trace, final weights, optimizer state, python/numpy/torch RNG and the model streams {streams} identical bit for bit;'
          f' cap_hits equal; train_s {rb["train_s"]:.2f}s over both segments (first segment {saved_elapsed:.2f}s); model counters equal after resume: {exact}')


# ------------------------------------------------------------------------------------------------------------------------------------------------ (3)
def test_corrupt_falls_back_and_refusals():
    kind = 'plain'
    data = make_data('d3')
    N = 60
    ck = ['--ckpt-every', '20', '--resume']
    oa = fresh('o3a')
    must(run(HERE, argv(kind, data, oa, N, ['--ckpt-every', '20'])), 'straight')
    assert sorted(os.listdir(os.path.join(oa, 'ckpt'))) == ['step-40.json', 'step-40.pt', 'step-60.json', 'step-60.pt'], os.listdir(os.path.join(oa, 'ckpt'))     # newest 2 kept
    ref = load_sd(oa)

    def broken(how):
        o = fresh('o3-' + how)
        shutil.copytree(oa, o, ignore=shutil.ignore_patterns('checkpoint.pt', 'RESULT.json'))
        c = os.path.join(o, 'ckpt')
        pt = os.path.join(c, 'step-60.pt')
        if how == 'flip':
            b = bytearray(open(pt, 'rb').read()); b[len(b) // 2] ^= 0xFF; open(pt, 'wb').write(bytes(b))
        elif how == 'truncate':
            b = open(pt, 'rb').read(); open(pt, 'wb').write(b[:len(b) // 2])
        elif how == 'nosidecar':
            os.remove(os.path.join(c, 'step-60.json'))
        elif how == 'badsidecar':
            open(os.path.join(c, 'step-60.json'), 'w').write('{"file": ')
        return o

    for how in ('flip', 'truncate', 'nosidecar', 'badsidecar'):
        o = broken(how)
        out = must(run(HERE, argv(kind, data, o, N, ck)), how)
        ev = events(out)
        skipped = [e for e in ev if e.get('event') == 'ckpt_skipped' and e['file'] == 'step-60.pt']
        res = [e for e in ev if e.get('event') == 'resumed']
        assert len(skipped) == 1 and res and res[0]['step'] == 40, (skipped, res)          # a file without a (readable) sidecar is an unfinished write: skipped for the previous one
        same_sd(ref, load_sd(o))                                                           # step 40 -> 60 again reproduces the straight run
        print(f'ok (3) newest checkpoint {how}: skipped, resumed from step-40.pt, final weights identical to the straight run')

    # refusals
    def refused(args, why, data_dir=None):
        o = fresh('o3r')
        shutil.copytree(oa, o, ignore=shutil.ignore_patterns('checkpoint.pt', 'RESULT.json'))
        rc, out, err = run(HERE, argv(kind, data_dir or data, o, *args), timeout=600)
        assert rc != 0 and 'refused' in err and why in err, (rc, out[-500:], err[-1200:])
        assert not os.path.exists(os.path.join(o, 'RESULT.json')) and not os.path.exists(os.path.join(o, 'checkpoint.pt'))
        return err.strip().splitlines()[-1]
    m1 = refused((N, ['--ckpt-every', '20', '--resume', '--lr', '1e-3']), 'config hash')
    m2 = refused((N + 20, ['--ckpt-every', '20', '--resume']), 'config hash')                       # --steps is part of the schedule
    d2 = make_data('d3-other', n=52)
    m3 = refused((N, ['--ckpt-every', '20', '--resume']), 'other data', d2)
    print('ok (3) refusals (rc 1, nothing written): lr changed ->', m1[:90], '| steps changed ->', m2[:60], '| other data ->', m3[:70])
    # --accum is memory only: resumes with a warning, does not refuse
    o = fresh('o3acc'); shutil.copytree(oa, o, ignore=shutil.ignore_patterns('checkpoint.pt', 'RESULT.json'))
    out = must(run(HERE, argv(kind, data, o, N, ck + ['--accum', '2'])), 'accum')
    assert any(e.get('event') == 'resume_warning' and 'accum' in e['warning'] for e in events(out))
    # every checkpoint corrupt: refuse
    o = broken('flip'); b = bytearray(open(os.path.join(o, 'ckpt', 'step-40.pt'), 'rb').read()); b[100] ^= 1; open(os.path.join(o, 'ckpt', 'step-40.pt'), 'wb').write(bytes(b))
    rc, out, err = run(HERE, argv(kind, data, o, N, ck))
    assert rc != 0 and 'none is valid' in err, (rc, err[-800:])
    print('ok (3) every checkpoint corrupt: refuses, rc', rc)
    # --resume with no checkpoint: step 0, the same run as without it
    o = fresh('o3none')
    out = must(run(HERE, argv(kind, data, o, N, ['--ckpt-every', '20', '--resume'])), 'none')
    assert not any(e.get('event') == 'resumed' for e in events(out)) and result(o)['resumed_from'] == []
    same_sd(ref, load_sd(o))
    o = fresh('o3none2')
    out = must(run(HERE, argv(kind, data, o, N, ['--resume'])), 'none, no ckpt-every')
    assert not os.path.exists(os.path.join(o, 'ckpt')) and result(o)['resumed_from'] == []
    same_sd(ref, load_sd(o))
    print('ok (3) --resume with no checkpoint starts at step 0 (same weights as the straight run; with --resume alone nothing is written to ckpt/)')


def test_atomic_write_crash():
    kind = 'plain'
    data = make_data('d3c')
    N = 60
    oa, ob = fresh('o3ca'), fresh('o3cb')
    must(run(HERE, argv(kind, data, oa, N, ['--ckpt-every', '20'])), 'straight')
    rc, out, err = run(HERE, argv(kind, data, ob, N, ['--ckpt-every', '20']), replace_crash=40)         # killed at the rename of step-40.pt
    assert rc == 137, (rc, err[-1500:])
    c = os.path.join(ob, 'ckpt')
    names = sorted(os.listdir(c))
    assert 'step-40.pt' not in names and 'step-40.json' not in names, names
    assert any(n.startswith('.step-40.pt.tmp-') for n in names), names                                   # the temp file is what is left
    assert {'step-20.pt', 'step-20.json'} <= set(names)
    out = must(run(HERE, argv(kind, data, ob, N, ['--ckpt-every', '20', '--resume'])), 'resume after crash')
    assert [e['step'] for e in events(out) if e.get('event') == 'resumed'] == [20]
    assert not any('.tmp-' in n for n in os.listdir(c)), os.listdir(c)                                  # swept by the next save
    same_sd(load_sd(oa), load_sd(ob))
    print('ok (3) kill between temp write and os.replace: no step-40 file, temp file left, previous checkpoint intact; resume from step 20 sweeps the temp and reproduces the straight run')
    # in process: a failing writer leaves the old file whole and no temp file; the sidecar is written last
    sys.path.insert(0, HERE)
    from custom_io import train as T
    d = fresh('atomic'); os.makedirs(d)
    p = os.path.join(d, 'x.bin')
    T.atomic_write(p, lambda f: f.write(b'old'))
    def boom(f):
        f.write(b'new-half'); raise RuntimeError('disk full')
    try:
        T.atomic_write(p, boom)
        raise AssertionError('no error')
    except RuntimeError:
        pass
    assert open(p, 'rb').read() == b'old' and os.listdir(d) == ['x.bin'], os.listdir(d)
    # crash after the .pt but before the sidecar: not a candidate
    pay = dict(version=1, step=5, model={}, opt={}, x=torch.zeros(3))
    T.save_ckpt(d, 5, pay, dict(config_hash='h'))
    T.save_ckpt(d, 6, dict(pay, step=6), dict(config_hash='h'))
    T.save_ckpt(d, 7, dict(pay, step=7), dict(config_hash='h'))
    assert sorted(os.listdir(d)) == ['step-6.json', 'step-6.pt', 'step-7.json', 'step-7.pt', 'x.bin'], os.listdir(d)       # newest 2 kept, 5 dropped after 7 was whole
    os.remove(os.path.join(d, 'step-7.json'))
    try:
        T.read_valid_ckpt(os.path.join(d, 'step-7.pt'), os.path.join(d, 'step-7.json'))
        raise AssertionError('a sidecar-less file passed')
    except ValueError:
        pass
    print('ok (3) atomic_write: a failing writer leaves the old file and no temp file; save_ckpt keeps the newest 2, deletes older ones only after the new one is whole; no sidecar = invalid')


def test_batches_from():
    sys.path.insert(0, HERE)
    from custom_io import data as D
    from custom_io.train import batches_from
    rs = rows(30)
    vocab = D.CharVocab.build(rs)
    ds = D.Dataset(rs, vocab)
    for order in ('shuffled', 'curriculum'):
        full = D.train_batches(ds, 4, order, 3)
        ref = [next(full) for _ in range(40)]                       # 7 batches an epoch: five-plus epochs
        for skip in (0, 1, 6, 7, 8, 13, 14, 29, 33):
            g = batches_from(ds, 4, order, 3, skip)
            for i in range(skip, 40 if skip < 20 else 40):
                b = next(g)
                for k in ('prompt_ids', 'prompt_mask', 'ans_ids', 'ans_mask'):
                    assert torch.equal(b[k], ref[i][k]), (order, skip, i, k)
                assert [r['id'] for r in b['rows']] == [r['id'] for r in ref[i]['rows']]
    print('ok (3) batches_from(skip) == data.train_batches from batch `skip` on, shuffled and curriculum, across epoch boundaries')


if __name__ == '__main__':
    torch.set_num_threads(1)
    try:
        test_batches_from()
        test_atomic_write_crash()
        for kind in ('plain', 'agent'):
            test_default_off_equals_base(kind)
        for kind in ('plain', 'agent'):
            test_interrupted_equals_uninterrupted(kind)
        test_corrupt_falls_back_and_refusals()
        print('ALL OK')
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
