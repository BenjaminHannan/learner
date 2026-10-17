"""CPU tests for prof_launch.py's GPU-RUN-4 additions (condition 3): the do-nothing A-A arm, the clock times and rounds sequence on every bench run, the host sidecar, and the
--deterministic switch. Tiny shapes, stub Gemma, synthetic rows. Run: python test_prof_launch.py  (about 2 minutes on one thread)."""
import json, os, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
PKG = os.environ.get('PROF_PKG_ROOT', '/home/user/src-g2f')
TINY = ['--arm', 'B3G2', '--tiny', '--data', 'synthetic', '--rows', '600', '--batch', '16', '--accum', '4', '--eg', 'stub', '--device', 'cpu', '--pkg-root', PKG]
ENV = dict(os.environ, OMP_NUM_THREADS='1', PROF_PKG_ROOT=PKG)


def run(args, out):
    p = subprocess.run([PY, os.path.join(HERE, 'prof_launch.py')] + TINY + args + ['--out', out], capture_output=True, text=True, env=ENV, timeout=1800)
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
    return json.load(open(out)), p.stdout


def test_same_arm_registered_and_bit_exact_rule():
    sys.path.insert(0, HERE)
    import prof_launch as pl
    names = pl.register_all(say=lambda *a: None)
    assert 'same' in names, names
    assert pl.prof.AB_CPU_RULE['same'] == 'bit_exact'
    assert pl.prof.parse_ab_variants('same') == ['same']           # prof_train refuses 'baseline' as a B arm; 'same' passes
    assert pl.Same.setup is pl.prof.Variant.setup and pl.Same.prep is pl.prof.Variant.prep   # does nothing: every hook is the base class's


def test_abbench_records_clock_times_and_rounds_seq():
    d = tempfile.mkdtemp(prefix='pl_')
    out = os.path.join(d, 'bench.json')
    t0 = time.time()
    res, _ = run(['--sections', 'abbench', '--ab-variants', 'same,defer', '--ab-accums', '', '--ab-rounds', '2', '--ab-warmup', '1', '--ab-updates', '4', '--chunk', '2'], out)
    arms = res['sections']['abbench']['arms']
    assert set(arms) == {'same', 'defer'}, set(arms)
    for name, arm in arms.items():
        runs = arm['a_runs'] + arm['b_runs']
        assert len(runs) == 4, (name, len(runs))
        for r in runs:
            for k in ('started_utc', 'ended_utc', 'timed_start_utc', 'timed_end_utc', 'rounds_seq', 't_start', 't_end'):
                assert k in r, (name, k, sorted(r))
            assert t0 - 5 <= r['t_start'] <= r['t_timed_start'] <= r['t_timed_end'] <= r['t_end'] <= time.time() + 5
            assert len(r['rounds_seq']) == 4 * 4, len(r['rounds_seq'])   # 4 timed updates x accum 4 micro-batches
        seqs = {tuple(r['rounds_seq']) for r in runs}
        assert len(seqs) == 1, (name, seqs)                             # identical work in every A and B run (mark 4): same seed, same rows, same K draws
        assert len(arm['a_runs'][0]['chunk_values']) == 2
    assert os.path.exists(os.path.join(d, 'bench.launch.json'))
    side = json.load(open(os.path.join(d, 'bench.launch.json')))
    assert side['cpu_model'] and side['torch'] and side['deterministic'] is False and 'ended_utc' in side


def test_deterministic_switch_sets_env_before_torch():
    d = tempfile.mkdtemp(prefix='pl_')
    out = os.path.join(d, 'eq.json')
    env = {k: v for k, v in ENV.items() if k != 'CUBLAS_WORKSPACE_CONFIG'}
    p = subprocess.run([PY, os.path.join(HERE, 'prof_launch.py'), '--deterministic'] + TINY + ['--sections', 'abequiv', '--ab-variants', 'same', '--curve-updates', '0', '--out', out],
                       capture_output=True, text=True, env=env, timeout=1800)
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
    side = json.load(open(os.path.join(d, 'eq.launch.json')))
    assert side['deterministic'] is True and side['cublas_workspace_config'] == ':4096:8' and side['deterministic_algorithms'] is True, side
    assert '--deterministic' not in side['argv']
    eq = json.load(open(out))['sections']['abequiv']
    assert eq['mark6_by_variant'].get('same') is True, eq['mark6_by_variant']


def main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith('test_') and callable(f)]
    bad = 0
    for n, f in tests:
        t = time.time()
        try:
            f()
            print(f'PASS {n} ({time.time() - t:.1f}s)', flush=True)
        except Exception as e:                                           # noqa: BLE001
            bad += 1
            print(f'FAIL {n}: {type(e).__name__}: {str(e)[:2000]}', flush=True)
    print(f'{len(tests) - bad} passed, {bad} failed, of {len(tests)}')
    return bad


if __name__ == '__main__':
    sys.exit(main())
