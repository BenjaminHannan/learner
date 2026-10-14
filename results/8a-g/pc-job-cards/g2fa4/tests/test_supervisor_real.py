#!/usr/bin/env python3
"""python3 tests/test_supervisor_real.py TREE   (CPU, about 10 minutes): the supervisor driving the REAL overlay train.py on a tiny b3g2 (TREE = a folder holding custom_io with the overlay train.py
and tests/test_ckpt*.py): the planned kill at update 150, the resume from step 100, trace A on the real events.jsonl, the accum-32 baseline, the compare, done."""
import json, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import g2fa4_supervisor as S

tree = sys.argv[1]
S.gpu_mem = lambda: (2000, 16303)
with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp) / 'work'
    (work / 'g8a' / 'pools').mkdir(parents=True)
    src = Path(tmp) / 'src'
    (src / 'custom_io' / 'queue_local').mkdir(parents=True)
    for q in ('MAIN-pc', 'BASE-pc'):
        (src / 'custom_io' / 'queue_local' / (q + '.txt')).write_text('#\n')
    r = str(HERE / 'real_train_runner.py')
    c = ['{python}', r, '--work', '{work}', '--queue', '{qpath}', '--tree', tree, '--busy', '{busy}']
    job = dict(id='g2fa4', title='real tiny b3g2', src=str(src), queue='MAIN-pc', job='MAIN-3M', arm='B3G2', steps=420, accum=4, runner_match='real_train_runner', kill_resume_at=150,
               runner_cmd=c + ['--job', 'MAIN-3M', '--accum', '4', '--steps', '420', '--ckpt-every', '100'],
               trace_a=dict(upto=300, peak_limit_mib=12288, first_n=50, last_n=50, resume_first_diff=0.01, resume_mean_abs=0.02, resume_max_abs=0.10),
               compare=dict(upto=300, last_n=50, diff_mean_pass=0.03, diff_mean_fail=0.06, last_n_pass=0.05, last_n_fail=0.10, report_from=101),
               baseline=dict(queue='BASE-pc', job='BASE-3M', upto=300, need_free_mib=4000, runner_cmd=c + ['--job', 'BASE-3M', '--accum', '32', '--steps', '420', '--ckpt-every', '50']))
    plan = dict(version=1, work=str(work), busy=str(Path(tmp) / 'GPU-BUSY.txt'), python=sys.executable, state_dir=str(Path(tmp) / 'state'), poll_s=2, max_no_progress=3,
                gpu=dict(need_free_mib=9500), jobs=[job])
    (Path(tmp) / 'plan.json').write_text(json.dumps(plan))
    (Path(tmp) / 'state').mkdir()
    (Path(tmp) / 'state' / 'ARMED.txt').write_text('test\n')
    sup = S.Sup(Path(tmp) / 'plan.json')
    t0 = time.time()
    while True:
        s = sup.cycle()
        if s is None or time.time() - t0 > 1500:
            break
        time.sleep(1)
    j = sup.st['jobs']['g2fa4']
    print(json.dumps({k: j.get(k) for k in ('status', 'kill_done', 'traceA', 'compare', 'why')}, indent=1))
    print((sup.sd / 'TRACE-A-g2fa4.md').read_text() if (sup.sd / 'TRACE-A-g2fa4.md').exists() else 'no trace A')
    print((sup.sd / 'COMPARE-g2fa4.md').read_text() if (sup.sd / 'COMPARE-g2fa4.md').exists() else 'no compare')
    print('\n'.join((sup.sd / 'supervisor.log').read_text().splitlines()[-14:]))
    for pid, cmd in S.list_procs():
        if 'real_train_runner' in cmd or 'custom_io.train' in cmd:
            S.kill_tree(pid)
    assert j['status'] == 'done' and j['traceA']['verdict'] == 'PASS', j
    print('ok real overlay train.py under the supervisor')
