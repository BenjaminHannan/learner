#!/usr/bin/env python3
"""python3 tests/test_supervisor.py   (Linux, no GPU, about a minute): the supervisor against tests/fake_runner.py, a stand-in for local_runner + train.py.
Scenarios: happy path (kill-and-resume at update 150, trace A, baseline alongside, compare, done), a crash that leaves a job-level arm_failed RESULT.json,
a crash loop, a NaN, GPU memory over the limit, a resume that does not match, a failing compare, a supervisor that dies and a new one that adopts the run,
a rebooted PC (the runner killed from outside), the GPU held by another program."""
import json, os, signal, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import g2fa4_supervisor as S

PY = sys.executable
FAKE = str(HERE / 'fake_runner.py')
GPU = [2000, 16303]                           # (used, total) the supervisor sees; a test changes GPU[0]
S.gpu_mem = lambda: tuple(GPU)
LIVE = []


def plan_for(tmp, steps=900, main_extra=(), base_extra=(), planextra={}, **jobkw):
    work = Path(tmp) / 'work'
    (work / 'g8a' / 'pools').mkdir(parents=True)
    src = Path(tmp) / 'src'
    (src / 'custom_io' / 'queue_local').mkdir(parents=True)
    for q in ('MAIN-pc', 'BASE-pc'):
        (src / 'custom_io' / 'queue_local' / (q + '.txt')).write_text('# fake\n')
    common = ['{python}', FAKE, '--work', '{work}', '--queue', '{qpath}', '--busy', '{busy}', '--steps', str(steps), '--step-s', '0.02', '--ckpt-every', '100']
    job = dict(id='g2fa4', title='test job', src=str(src), queue='MAIN-pc', job='MAIN-3M', arm='B3G2', steps=steps, accum=4, runner_match='fake_runner', kill_resume_at=150,
               runner_cmd=common + ['--job', 'MAIN-3M'] + list(main_extra),
               trace_a=dict(upto=300, peak_limit_mib=12288, first_n=50, last_n=50, resume_first_diff=0.01, resume_mean_abs=0.02, resume_max_abs=0.10),
               compare=dict(upto=300, last_n=50, diff_mean_pass=0.03, diff_mean_fail=0.06, last_n_pass=0.05, last_n_fail=0.10, report_from=101),
               baseline=dict(queue='BASE-pc', job='BASE-3M', upto=300, need_free_mib=4000))
    job['baseline']['runner_cmd'] = common + ['--job', 'BASE-3M'] + list(base_extra)
    job.update(jobkw)
    plan = dict(version=1, work=str(work), busy=str(Path(tmp) / 'GPU-BUSY.txt'), python=PY, state_dir=str(Path(tmp) / 'state'), poll_s=0.1, max_no_progress=2, quiet_s=0.3,
                stall_warn_s=600, stall_kill_s=1200, gpu=dict(need_free_mib=9500), jobs=[job])
    plan.update(planextra)
    p = Path(tmp) / 'plan.json'
    p.write_text(json.dumps(plan))
    (Path(plan['state_dir'])).mkdir(parents=True, exist_ok=True)
    (Path(plan['state_dir']) / 'ARMED.txt').write_text('test\n')
    return p


def drive(sup, until, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = sup.cycle()
        if until(sup) or s is None:
            return s
        time.sleep(0.1)
    raise AssertionError('timeout; log tail:\n' + '\n'.join(Path(sup.sd / 'supervisor.log').read_text().splitlines()[-15:]))


def cleanup():
    for _ in range(50):
        left = [pid for pid, cmd in S.list_procs() if 'fake_runner' in cmd and 'test_supervisor' not in cmd]
        if not left:
            return
        for pid in left:
            S.kill_tree(pid)
        time.sleep(0.2)


def js(sup):
    return sup.st['jobs']['g2fa4']


def t_happy():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, steps=1500))
        s = drive(sup, lambda x: False, 120)
        assert s is None, 'loop did not finish'
        j = js(sup)
        assert j['status'] == 'done', j
        assert j['kill_done'].startswith('killed at update'), j['kill_done']
        assert j['traceA']['verdict'] == 'PASS', j['traceA']
        assert j['compare']['verdict'] == 'PASS', j['compare']
        assert (sup.sd / 'ALL-DONE.txt').exists() and (sup.sd / 'DONE-g2fa4.txt').exists() and (sup.sd / 'TRACE-A-g2fa4.md').exists() and (sup.sd / 'COMPARE-g2fa4.md').exists()
        ev = sup.events(sup.plan['jobs'][0])
        assert ev.seg == 2 and ev.resumed and ev.resumed[0][1] == 100, (ev.seg, ev.resumed)
        r = json.load(open(sup.sd / 'TRACE-A-g2fa4.json'))
        assert r['resume']['n_redone'] >= 40 and r['resume']['max_abs'] < 1e-9, r['resume']
        assert not (Path(tmp) / 'GPU-BUSY.txt').exists() or 'MAIN-pc/' not in (Path(tmp) / 'GPU-BUSY.txt').read_text()
        print('ok happy path:', j['kill_done'], '| trace A', j['traceA']['verdict'], '| compare', j['compare']['verdict'], '| resume', r['resume'])


def t_crash():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, main_extra=['--crash-at', '450']))
        drive(sup, lambda x: False, 120)
        j = js(sup)
        assert j['status'] == 'done', j
        assert sum(1 for r in j['restarts'] if not r.get('first')) >= 2, j['restarts']       # the planned kill and the crash
        asides = list((Path(sup.plan['work']) / 'results' / 'MAIN-pc' / 'MAIN-3M').glob('RESULT.json.aside-*'))
        assert asides, 'the job-level arm_failed RESULT.json was not moved aside'
        print('ok crash with a job-level arm_failed RESULT.json: relaunched, finished; restarts', len(j['restarts']), 'asides', len(asides))


def t_loop():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, main_extra=['--crash-at', '10', '--crash-always'], kill_resume_at=0))
        s = drive(sup, lambda x: False, 90)
        assert s is None and js(sup)['status'] == 'stopped' and (sup.sd / 'STOPPED.txt').exists(), js(sup)
        assert 'no new update' in js(sup)['why'], js(sup)['why']
        print('ok crash loop stops:', js(sup)['why'])


def t_nan():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, main_extra=['--nan-at', '200']))
        s = drive(sup, lambda x: False, 90)
        assert s is None and js(sup)['status'] == 'stopped' and 'nonfinite_loss' in js(sup)['why'], js(sup)
        print('ok NaN stops the job (no restart):', js(sup)['why'])


def t_memory():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 13000                                              # the GPU is "free" enough for the start (need 9500 of 16303) but the peak is over 12288
        plan = json.loads(Path(plan_for(tmp)).read_text())
        plan['gpu']['need_free_mib'] = 3000
        (Path(tmp) / 'plan.json').write_text(json.dumps(plan))
        sup = S.Sup(Path(tmp) / 'plan.json')
        s = drive(sup, lambda x: False, 90)
        assert s is None and js(sup)['status'] == 'stopped' and js(sup)['traceA']['verdict'] == 'FAIL' and 'MiB' in js(sup)['why'], js(sup)
        cleanup()
        print('ok memory over the limit fails trace A and stops the run:', js(sup)['why'][:110])


def t_resume_mismatch():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, main_extra=['--seg2-offset', '0.3']))
        s = drive(sup, lambda x: False, 90)
        assert s is None and js(sup)['status'] == 'stopped' and js(sup)['traceA']['verdict'] == 'FAIL' and 'redone' in js(sup)['why'], js(sup)
        print('ok a resume that does not match fails trace A:', js(sup)['why'][:120])


def t_compare_fail():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, base_extra=['--offset', '-0.3']))
        drive(sup, lambda x: False, 120)
        j = js(sup)
        assert j['status'] == 'done' and j['compare']['verdict'] == 'FAIL' and (sup.sd / 'ATTENTION-compare.txt').exists(), j
        print('ok a failing compare is reported and the main run goes on to the end:', j['compare'])


def t_unclear():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, base_extra=['--offset', '-0.045']))      # |diff of means| 0.045: between 0.03 and 0.06
        drive(sup, lambda x: False, 120)
        j = js(sup)
        assert j['compare']['verdict'] == 'UNCLEAR' and j['compare']['read_as'] == 'GO', j['compare']
        print('ok a diff of 0.045 is UNCLEAR, read as GO')


def t_adopt_and_reboot():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        pp = plan_for(tmp, steps=1500)
        sup = S.Sup(pp)
        drive(sup, lambda x: js(x)['kill_done'] and bool(x.events(x.plan['jobs'][0]).resumed) and x.events(x.plan['jobs'][0]).last_step > 200, 60)
        # the supervisor dies (a crash of the python process): the runner goes on; a new supervisor adopts it
        sup2 = S.Sup(pp)
        pids = sup2.find('fake_runner', 'MAIN-pc')
        assert pids, 'runner not found by the new supervisor'
        drive(sup2, lambda x: x.events(x.plan['jobs'][0]).last_step > 600, 60)
        assert sup2.find('fake_runner', 'MAIN-pc') == pids, 'the new supervisor restarted a run that was alive'
        # the PC reboots: every process is gone, the new supervisor resumes from the checkpoint
        for pid in pids + sup2.find('fake_runner', 'BASE-pc'):
            S.kill_tree(pid)
        cleanup()
        time.sleep(1)
        sup3 = S.Sup(pp)
        drive(sup3, lambda x: False, 120)
        j = js(sup3)
        ev = sup3.events(sup3.plan['jobs'][0])
        assert j['status'] == 'done', j
        assert len(ev.resumed) >= 2, ev.resumed
        print('ok adopted a live run; after a "reboot" resumed from checkpoint', ev.resumed[-1][1], 'and finished (resumes at', [s for _, s in ev.resumed], ')')


def t_gpu_held():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 15615                                              # the Qwen server holds the card
        sup = S.Sup(plan_for(tmp))
        for _ in range(5):
            sup.cycle()
            time.sleep(0.05)
        assert not sup.find('fake_runner', 'MAIN-pc') and 'WAITING for the GPU' in (sup.sd / 'supervisor.log').read_text()
        GPU[0] = 2000
        drive(sup, lambda x: bool(x.find('fake_runner', 'MAIN-pc')), 20)
        cleanup()
        print('ok waits while another program holds the GPU, starts when it is free')


def t_arm_halt():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        pp = plan_for(tmp)
        sd = Path(tmp) / 'state'
        (sd / 'ARMED.txt').unlink()
        sup = S.Sup(pp)
        assert sup.cycle() is None and not sup.find('fake_runner', 'MAIN-pc'), 'started although not armed'
        assert S.main(['--plan', str(pp), 'arm', 'Ben 3:55 PM ET: go']) == 0 and 'Ben 3:55' in (sd / 'ARMED.txt').read_text()
        sup = S.Sup(pp)
        drive(sup, lambda x: bool(x.find('fake_runner', 'MAIN-pc')), 20)
        S.main(['--plan', str(pp), 'halt'])
        time.sleep(1)
        assert not S.Sup(pp).find('fake_runner', 'MAIN-pc') and not (sd / 'ARMED.txt').exists() and S.Sup(pp).cycle() is None
        ck = list((Path(sup.plan['work']) / 'results' / 'MAIN-pc' / 'MAIN-3M' / 'B3G2').glob('events.jsonl'))
        assert ck, 'events kept'
        print('ok not armed = nothing starts; arm starts; halt stops the runners and disarms (events kept)')

def t_device_cpu():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, main_extra=['--device', 'cpu']))
        s = drive(sup, lambda x: False, 60)
        assert s is None and js(sup)['status'] == 'stopped' and 'cpu' in js(sup)['why'], js(sup)
        assert not sup.find('fake_runner', 'MAIN-pc')
        print('ok a run that started on the CPU is stopped:', js(sup)['why'][:90])


def t_stall():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, main_extra=['--hang-at', '400'], planextra=dict(stall_warn_s=1.5, stall_kill_s=4)))
        drive(sup, lambda x: False, 120)
        assert js(sup)['status'] == 'done' and (sup.sd / 'ATTENTION-stall.txt').exists(), js(sup)
        print('ok a hung run: warned after 1.5 s, killed after 4 s, resumed from the checkpoint, finished')


def t_main_dies_with_baseline():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, steps=1200, main_extra=['--crash-at', '500'], base_extra=['--step-s', '0.08']))
        drive(sup, lambda x: False, 120)
        j = js(sup)
        assert j['status'] == 'done' and j['base']['status'] == 'abandoned' and (sup.sd / 'ATTENTION-baseline.txt').exists(), (j['status'], j['base'])
        assert j['no_progress'] == 0
        print('ok the main run died while the baseline shared the card: baseline stopped first, main resumed and finished (baseline abandoned, flagged)')


def t_no_checkpoint():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, main_extra=['--ckpt-every', '100000']))
        s = drive(sup, lambda x: False, 60)
        assert s is None and js(sup)['status'] == 'stopped' and 'no checkpoint' in js(sup)['why'], js(sup)
        print('ok no checkpoint by update 150 stops the run instead of leaving it unprotected')


def t_empty_segment():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, main_extra=['--die-after-resume-once']))
        drive(sup, lambda x: False, 120)
        j = js(sup)
        assert j['status'] == 'done' and j['traceA']['verdict'] == 'PASS', j
        print('ok a resumed segment that died before its first update does not break trace A')


def t_lock():
    with tempfile.TemporaryDirectory() as tmp:
        a = S.acquire_lock(Path(tmp) / 'x.lock')
        assert a is not None and S.acquire_lock(Path(tmp) / 'x.lock') is None
        a.close()
        assert S.acquire_lock(Path(tmp) / 'x.lock') is not None
        print('ok the OS-level lock admits one holder at a time')


def t_kill_fails_then_works():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, steps=1500))
        real = S.kill_tree
        S.kill_tree = lambda pid: None                                  # taskkill "fails"
        try:
            drive(sup, lambda x: 'KILL FAILED' in (x.sd / 'supervisor.log').read_text(), 60)
            assert not js(sup)['kill_done'], 'kill_done set although the kill failed'
        finally:
            S.kill_tree = real
        for pid, cmd in S.list_procs():                                 # clean the processes the failed kills left
            if 'fake_runner' in cmd and 'test_supervisor' not in cmd:
                real(pid)
        time.sleep(1)
        drive(sup, lambda x: False, 120)
        assert js(sup)['status'] == 'done' and js(sup)['traceA']['verdict'] == 'PASS', js(sup)
        print('ok a failed kill is not counted as done; it is retried')


def t_reboot_not_crash():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp, main_extra=['--crash-at', '10', '--crash-always'], kill_resume_at=0))
        n = [0]

        def bt():
            n[0] += 1000
            return n[0]
        real = S.boot_time
        S.boot_time = bt
        try:
            t0 = time.time()
            while time.time() - t0 < 12:
                assert sup.cycle() is not None, js(sup)
                time.sleep(0.1)
        finally:
            S.boot_time = real
            cleanup()
        assert js(sup)['status'] != 'stopped' and len(js(sup)['restarts']) >= 4, js(sup)
        print('ok deaths across a reboot are not counted as crashes (%d launches, still not stopped)' % len(js(sup)['restarts']))


def t_stale_busy_lock():
    with tempfile.TemporaryDirectory() as tmp:
        GPU[0] = 2000
        sup = S.Sup(plan_for(tmp))
        work = Path(sup.plan['work'])
        (work / 'g8a' / 'pools' / 'p10-rung30-s400-a64-L.lock').write_text('')
        Path(sup.plan['busy']).write_text('custom-io MAIN-pc/MAIN-3M 1234 old\ncustom-io other-pc/x 99 keep\n')
        sup.cycle()
        pools = work / 'g8a' / 'pools'
        assert not (pools / 'p10-rung30-s400-a64-L.lock').exists() and list(pools.glob('*.lock.aside-*')), (list(pools.iterdir()), [(p, c[:80]) for p, c in S.list_procs() if 'custom_io' in c or 'fake_runner' in c])
        b = Path(sup.plan['busy']).read_text()
        assert 'other-pc/x' in b and 'MAIN-pc/MAIN-3M 1234' not in b, b
        cleanup()
        print('ok a stale lock is moved aside and only the job\'s own GPU-BUSY line is removed')


if __name__ == '__main__':
    todo = [t_happy, t_crash, t_loop, t_nan, t_memory, t_resume_mismatch, t_compare_fail, t_unclear, t_adopt_and_reboot, t_gpu_held, t_arm_halt, t_stale_busy_lock, t_device_cpu, t_stall, t_main_dies_with_baseline, t_no_checkpoint, t_empty_segment, t_lock, t_kill_fails_then_works, t_reboot_not_crash]
    only = sys.argv[1:]
    try:
        for t in todo:
            if not only or t.__name__ in only:
                try:
                    t()
                finally:
                    cleanup()
        if not only:
            r = subprocess.run([PY, str(HERE / 'test_probe.py')])           # the resume-noise probe has its own file
            assert r.returncode == 0, 'tests/test_probe.py failed'
        print('ALL OK')
    finally:
        cleanup()
