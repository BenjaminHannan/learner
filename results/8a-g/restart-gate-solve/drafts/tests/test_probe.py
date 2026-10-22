#!/usr/bin/env python3
"""python3 tests/test_probe.py   (Linux, no GPU, about a minute; test_supervisor.py runs it at its end): the `probe-resume` command against tests/fake_runner.py.
Scenarios: the pure verdict rule, PASS with small noise, FAIL when both resumes agree but differ from the run, refused while the run is armed, refused on a busy card,
a wrong resumed step, and the main run's files untouched (hash listing before / after)."""
import hashlib, json, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_supervisor as T
import fake_runner as F
S = T.S

QUEUE = '# fake\ng8a-data: 8a-data --data-pool x\ng8a: MAIN-3M --rung 3M --seed 400 --arms B3G2 --device cuda\n'


def setup(tmp, shift=0.0, armed=False, **kw):
    """a finished main run (updates 1..300 logged, step-200 kept in KEEP) -> (plan path, keep dir)."""
    T.GPU[0] = 2000
    p = T.plan_for(tmp, **kw)
    plan = json.loads(p.read_text())
    sd = Path(plan['state_dir'])
    (Path(plan['jobs'][0]['src']) / 'custom_io' / 'queue_local' / 'MAIN-pc.txt').write_text(QUEUE)
    arm = Path(plan['work']) / 'results' / 'MAIN-pc' / 'MAIN-3M' / 'B3G2'
    arm.mkdir(parents=True)
    lines = [dict(event='segment'), dict(event='start', device='cuda')] + [dict(event='train', step=s, loss=F.loss_at(s, shift if s > 200 else 0.0, 0, 1), elapsed=s) for s in range(1, 301)]
    lines += [dict(event='segment'), dict(event='resumed', step=250), dict(event='train', step=251, loss=99.0, elapsed=1)]     # a later segment: the first occurrence counts
    (arm / 'events.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in lines))
    (Path(plan['work']) / 'results' / 'MAIN-pc' / 'MAIN-3M' / 'RESULT.json').write_text('{"status": "ok"}')
    keep = Path(tmp) / 'ckpt-keep'
    keep.mkdir()
    (keep / 'step-200.pt').write_bytes(b'x')
    (keep / 'step-200.json').write_text(json.dumps(dict(step=200, accum=4, config_hash='c0ffee' * 10)))      # (gatefix: the probe now reads the sidecar: accum and step must be the job's)
    if not armed:
        (sd / 'ARMED.txt').rename(sd / 'ARMED.txt.aside-old')
        (sd / 'ALL-DONE.txt').write_text('done\n')
    return p, keep


def probe(p, keep, step=200, upto=250):
    return S.main(['--plan', str(p), 'probe-resume', '--keep', str(keep), '--step', str(step), '--upto', str(upto)])


def report(p):
    return json.loads((Path(json.loads(Path(p).read_text())['state_dir']) / 'PROBE-RESUME-g2fa4.json').read_text())


def listing(tmp):
    """sha256 of every file of the main run (results, queue file, KEEP, the state files that are not logs)."""
    out = {}
    for root, names in ((Path(tmp) / 'work' / 'results' / 'MAIN-pc', None), (Path(tmp) / 'ckpt-keep', None), (Path(tmp) / 'src' / 'custom_io' / 'queue_local' / 'MAIN-pc.txt', None)):
        for f in ([root] if root.is_file() else sorted(root.rglob('*'))):
            if f.is_file():
                out[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()
    for n in ('ARMED.txt.aside-old', 'ALL-DONE.txt', 'state.json'):
        f = Path(tmp) / 'state' / n
        if f.exists():
            out[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def t_rule():
    C = [1.0, 2.0, 3.0]
    r = S.resume_probe_verdict(C, [1.01, 2.0, 3.02], [1.0, 2.01, 3.0])
    assert r['verdict'] == 'PASS' and abs(r['n'] - 0.02) < 1e-9 and abs(r['d'] - 0.02) < 1e-9 and len(r['diff_r1_c']) == 3, r
    r = S.resume_probe_verdict(C, [1.5, 2.0, 3.0], [1.5, 2.0, 3.0])               # R1 == R2 (n = 0): the limit is 0.10
    assert r['verdict'] == 'FAIL' and r['n'] == 0 and r['limit'] == 0.10 and abs(r['d'] - 0.5) < 1e-4, r
    r = S.resume_probe_verdict(C, [1.5, 2.0, 3.0], [1.0, 2.0, 3.0])               # n = 0.5: the limit grows to 1.5
    assert r['verdict'] == 'PASS' and abs(r['limit'] - 1.5) < 1e-9, r
    print('ok the verdict rule: d <= max(0.10, 3n)')


def t_pass():
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = setup(tmp, main_extra=['--jitter', '0.01'])
        before = listing(tmp)
        assert probe(p, keep) == 0
        r = report(p)
        assert r['verdict'] == 'PASS' and r['n'] > 0 and r['d'] <= max(0.10, 3 * r['n']) and r['steps'][0] == 201 and len(r['C']) == 50, r
        assert r['C'][50 - 1] == F.loss_at(250, 0, 0, 1), 'C must come from the first segment, not the later one'
        sd = Path(json.loads(p.read_text())['state_dir'])
        assert 'In plain words' in (sd / 'PROBE-RESUME-g2fa4.md').read_text() and '| 201 |' in (sd / 'PROBE-RESUME-g2fa4.md').read_text()
        q = Path(tmp) / 'src' / 'custom_io' / 'queue_local'
        n1 = (q / 'MAINn1-pc.txt').read_text()
        assert n1 == QUEUE.replace('MAIN-3M', 'MAINn1-3M') and (q / 'MAINn2-pc.txt').exists(), n1
        for tag in ('n1', 'n2'):
            ck = Path(tmp) / 'work' / 'results' / f'MAIN{tag}-pc' / f'MAIN{tag}-3M' / 'B3G2' / 'ckpt'
            assert (ck / 'step-200.pt').exists() and (ck / 'step-200.json').exists()
        assert listing(tmp) == before, 'the probe touched the main run\'s files'                     # (f)
        assert not [x for x in S.list_procs() if 'fake_runner' in x[1] and 'MAINn' in x[1]], 'a probe runner is still alive'
        print('ok probe PASS: n %.4f d %.4f limit %.4f; main run files untouched' % (r['n'], r['d'], r['limit']))


def t_fail():
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = setup(tmp, shift=0.5)                                                              # no jitter: R1 == R2, both 0.5 away from C
        assert probe(p, keep) == 1
        r = report(p)
        assert r['verdict'] == 'FAIL' and r['n'] == 0 and abs(r['d'] - 0.5) < 1e-4, r
        print('ok probe FAIL when R1 == R2 but both differ from the run by 0.5')


def t_refuse_armed():
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = setup(tmp, armed=True)
        assert probe(p, keep) == 2 and not (Path(tmp) / 'src' / 'custom_io' / 'queue_local' / 'MAINn1-pc.txt').exists()
        print('ok refused while the supervised run is armed and unfinished')


def t_refuse_busy_gpu():
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = setup(tmp)
        T.GPU[0] = 15000
        try:
            assert probe(p, keep) == 2 and not (Path(tmp) / 'src' / 'custom_io' / 'queue_local' / 'MAINn1-pc.txt').exists()
        finally:
            T.GPU[0] = 2000
        print('ok refused while the card is busy')


def t_wrong_step():
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = setup(tmp, main_extra=['--force-resume-step', '100'])
        assert probe(p, keep) == 1
        r = report(p)
        assert r['verdict'] == 'FAIL' and any('resumed at 100, not 200' in w for w in r['why_fail']), r
        print('ok a resume at the wrong step fails the probe:', r['why_fail'][0])


if __name__ == '__main__':
    try:
        for t in (t_rule, t_pass, t_fail, t_refuse_armed, t_refuse_busy_gpu, t_wrong_step):
            try:
                t()
            finally:
                T.cleanup()
        print('PROBE TESTS OK')
    finally:
        T.cleanup()
