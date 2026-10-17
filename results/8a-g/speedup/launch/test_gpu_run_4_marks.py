"""Tests of gpu_run_4_marks.py (the GPU-RUN-4 readout): synthetic box folders built in the exact file formats prof_launch.py / hostmon.sh write, one case per rule of
PREREG-launch-defer.md, plus the real GPU-RUN-3 CUDA profiler json for mark 7's field names. Fast (no torch). Run: python test_gpu_run_4_marks.py"""
import csv, json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gpu_run_4_marks as gm                                                  # noqa: E402

CH = [2.34, 2.64, 2.14, 2.62, 2.41, 1.97, 2.16, 1.97]          # GPU-RUN-3 box 3 pad64p A round 1 chunk shape (different K per chunk)
SEQ = [16.0, 8.0, 32.0, 4.0] * 40


def run(t, scale, seq=SEQ, peak=8.3):
    ch = [c * scale for c in CH]
    return dict(round_median=sorted(ch)[len(ch) // 2], chunk_values=ch, peak_mem=dict(allocated_gb=peak), rounds_seq=list(seq), t_timed_start=t, t_timed_end=t + 90,
                timed_start_utc=str(t), timed_end_utc=str(t + 90), started_utc=str(t - 20), ended_utc=str(t + 90))


def bench(path, arm, a_scales, b_scales, t0, seq_b=None, peak_b=8.3):
    a, b, t = [], [], t0
    for sa, sb in zip(a_scales, b_scales):
        a.append(run(t, sa)); t += 200
        b.append(run(t, sb, seq_b or SEQ, peak_b)); t += 200
    json.dump(dict(sections=dict(abbench=dict(arms={arm: dict(a_runs=a, b_runs=b)}))), open(path, 'w'))
    return t


def prof(path, kernels, kms, syncs, dtoh):
    json.dump(dict(sections=dict(profiler=dict(cuda=dict(kernels_per_update=kernels, kernel_time_ms_per_update=kms, stream_syncs_per_update=syncs, dtoh_copies_per_update=dtoh)))), open(path, 'w'))


def hostmon(path, t0, t1, throttle_at=None, steal_at=None):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['utc', 'epoch', 'gpu_sm_mhz', 'gpu_mem_mhz', 'gpu_power_w', 'gpu_temp_c', 'gpu_util_pct', 'gpu_mem_used_mib', 'throttle_active', 'cpu_steal_pct', 'load1', 'trainer_pid',
                    'trainer_cpu', 'trainer_cpu_mhz', 'trainer_cpu_pct'])
        for t in range(int(t0), int(t1), 10):
            th = '0x0000000000000004' if throttle_at is not None and throttle_at <= t < throttle_at + 10 else '0x0000000000000000'
            sl = 5.0 if steal_at is not None and steal_at <= t < steal_at + 10 else 0.0
            w.writerow([t, t, 2685, 10501, 185, 40, 62, 9000, th, sl, 1.0, 123, 7, 3000, 100.0])


def box(d, host='h1', d4b=0.62, aab=1.002, kms_defer=1300, base_kms=1415, syncs=250, seq_b=None, throttle_at=None, full=True):
    os.makedirs(d, exist_ok=True)
    t = bench(os.path.join(d, 'gr4_bench_d4.json'), 'defer', [1.0, 1.001, 0.999], [d4b, d4b * 1.002, d4b * 0.998], 1000, seq_b)
    t = bench(os.path.join(d, 'gr4_bench_aa.json'), 'same', [1.0, 1.0, 1.001], [aab, aab * 1.001, aab * 0.999], t)
    if full:
        prof(os.path.join(d, 'gr4_prof_base.json'), 76000, base_kms, 1305, 745)
        prof(os.path.join(d, 'gr4_prof_defer.json'), 33000, kms_defer, syncs, 90)
        json.dump(dict(sections=dict(abequiv=dict(variants=dict(defer=dict(bf16=dict(rel_loss_diff=2e-6, grad_cos=0.99999, grad_rel_l2=1e-3))),
                                                   reference=dict(bf16=dict(rerun=dict(bit_exact=False, rel_loss_diff=0.0, grad_rel_l2=3e-4)))))), open(os.path.join(d, 'gr4_abequiv.json'), 'w'))
        json.dump(dict(sections=dict(abequiv=dict(variants=dict(kvcat=dict(bf16=dict(bit_exact=True, rel_loss_diff=0.0, grad_rel_l2=0.0, grad_cos=1.0))),
                                                   reference=dict(bf16=dict(rerun=dict(bit_exact=True, rel_loss_diff=0.0, grad_rel_l2=0.0)))))), open(os.path.join(d, 'gr4_abequiv_det.json'), 'w'))
        json.dump(dict(sections=dict(equiv=dict(specs=dict(defer=dict(curve=dict(updates=300, E4=dict(passed=True, registered_window=True, mean_abs_diff=0.008, diff_of_means=0.002))))))),
                  open(os.path.join(d, 'gr4_e4.json'), 'w'))
        t = bench(os.path.join(d, 'gr4_bench_k4.json'), 'kvcat', [d4b] * 3, [d4b * 0.97] * 3, t)      # K4's A runs defer: same speed as D4's B
        t = bench(os.path.join(d, 'gr4_bench_d8.json'), 'defer', [1.45] * 3, [0.75] * 3, t)
    hostmon(os.path.join(d, 'hostmon.csv'), 900, t + 100, throttle_at)
    json.dump(dict(host=host, cpu_model='AMD EPYC 7742', torch='2.11.0+cu128', cuda='12.8', gpu='NVIDIA GeForce RTX 4090'), open(os.path.join(d, 'gr4_bench_d4.launch.json'), 'w'))
    return d


def read(b1, b2=None, **kw):
    argv = ['--box1', b1, '--box1-machine', 'm1', '--box1-image', 'img']
    if b2:
        argv += ['--box2', b2, '--box2-machine', 'm2', '--box2-image', 'img']
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        return gm.main(argv)


def tmp():
    return tempfile.mkdtemp(prefix='gr4m_')


def test_two_host_win_allows_the_port():
    d = tmp()
    r = read(box(d + '/b1'), box(d + '/b2', host='h2', full=False))
    assert r['outcome']['allows'].startswith('D4 wins on both hosts'), r['outcome']
    d4 = r['boxes'][0]['arms']['d4']
    assert d4['read_rounds'] == 3 and d4['mark1'] and abs(d4['speed'] - 1 / 0.62) < 1e-3
    assert r['mark7']['holds'] and r['mark2']['defer']['holds'] and r['mark2']['kvcat']['holds']
    assert r['boxes'][0]['mark5'] and r['predictions']['P1'][0]['right'] and r['P6']['R'] < 0.9


def test_framing_kill_when_counts_fall_but_speed_does_not():
    d = tmp()
    r = read(box(d + '/b1', d4b=0.95), box(d + '/b2', host='h2', d4b=0.95, full=False))
    assert r['outcome']['allows'].startswith('framing kill holds'), r['outcome']
    assert all(r['outcome']['p1_kill_by_box'])


def test_defer_inefficient_is_not_a_framing_kill():
    d = tmp()
    r = read(box(d + '/b1', d4b=0.95, kms_defer=1700), box(d + '/b2', host='h2', d4b=0.95, full=False))
    assert r['outcome']['allows'].startswith('defer is inefficient on CUDA'), r['outcome']
    assert not any(r['outcome']['p1_kill_by_box'])


def test_p6_dead_when_profiled_kernel_time_is_most_of_the_unprofiled_wall():
    d = tmp()
    b1 = box(d + '/b1', base_kms=2100)          # A median 2.34 s (CH scale 1): R = 2100 / 2340 = 0.897 ... make it dead:
    prof(os.path.join(b1, 'gr4_prof_base.json'), 76000, 2200, 1305, 745)
    r = read(b1, box(d + '/b2', host='h2', full=False))
    assert r['P6']['R'] >= 0.9 and r['P6']['dead'] and r['outcome']['allows'].startswith('framing kill holds'), (r['P6'], r['outcome'])


def test_mark7_miss_is_an_artifact():
    d = tmp()
    r = read(box(d + '/b1', syncs=900), box(d + '/b2', host='h2', full=False))
    assert r['mark7']['holds'] is False and r['outcome']['allows'].startswith('mark 7 misses'), r['outcome']


def test_one_host_win_asks_for_one_more_box():
    d = tmp()
    r = read(box(d + '/b1'), box(d + '/b2', host='h2', d4b=0.88, full=False))       # box 2: 1.14x, neither a win nor a kill
    assert r['outcome']['allows'].startswith('D4 wins on one host only'), r['outcome']


def test_same_host_is_not_a_replication():
    d = tmp()
    r = read(box(d + '/b1'), box(d + '/b2', host='h1', full=False))
    assert not r['outcome']['replication_hosts_distinct'] and r['outcome']['allows'].startswith('D4 wins on one host only'), r['outcome']


def test_throttle_sample_in_a_window_unreads_that_round():
    d = tmp()
    r = read(box(d + '/b1', throttle_at=1010), box(d + '/b2', host='h2', full=False))
    d4 = r['boxes'][0]['arms']['d4']
    assert d4['read_rounds'] == 2 and d4['status'] == 'regime-confounded', d4['rounds'][0]
    assert any('(c) throttle' in w for w in d4['rounds'][0]['a_why'])


def test_rounds_seq_mismatch_voids_rounds():
    d = tmp()
    r = read(box(d + '/b1', seq_b=[4.0] * 160), box(d + '/b2', host='h2', full=False))
    d4 = r['boxes'][0]['arms']['d4']
    assert not any(x['mark4'] for x in d4['rounds']) and not d4['decided']


def test_aa_over_one_percent_voids_the_box():
    d = tmp()
    r = read(box(d + '/b1', aab=1.015), box(d + '/b2', host='h2', full=False))
    assert r['boxes'][0]['mark5'] is False and not r['boxes'][0]['box_counts'], r['boxes'][0]['mark5']
    assert r['outcome']['allows'].startswith('D4 wins on one host only') and r['outcome']['voided_boxes'] == [1], r['outcome']      # box 1 void: only box 2's win counts


def test_kill_on_one_host_and_win_on_the_other_is_a_disagreement():
    d = tmp()
    r = read(box(d + '/b1'), box(d + '/b2', host='h2', d4b=0.97, full=False))
    assert r['outcome']['p1_kill_by_box'] == [False, True] and r['outcome']['allows'].startswith('hosts disagree'), r['outcome']


def test_kill_needs_both_hosts():
    d = tmp()
    b2 = box(d + '/b2', host='h2', full=False, aab=1.03)                 # box 2 void by mark 5
    r = read(box(d + '/b1', d4b=0.95), b2)
    assert r['outcome']['p1_kill_by_box'][0] and not r['outcome']['allows'].startswith('framing kill'), r['outcome']


def test_chunk_rule_uses_same_numbered_chunks_not_spread():
    """The old spread rule (largest / smallest chunk <= 1.05) fails every GPU-RUN-3 round (1.35); the new rule passes the same clean rounds."""
    assert max(CH) / min(CH) > 1.3
    d = tmp()
    r = read(box(d + '/b1'), box(d + '/b2', host='h2', full=False))
    assert all(x['a_normal'] and x['b_normal'] for x in r['boxes'][0]['arms']['d4']['rounds'])


def test_mark7_reads_the_real_cuda_profiler_json():
    d = tmp()
    real = os.path.join(HERE, '..', 'gpu-run-3-box3', 'b3g2_profile.json')
    shutil.copy(real, os.path.join(d, 'gr4_prof_base.json')); shutil.copy(real, os.path.join(d, 'gr4_prof_defer.json'))
    m7 = gm.mark7(d)
    assert m7['base_syncs'] == 1305.0 and m7['base_dtoh'] == 745.0 and m7['base_kernels'] == 75967.0 and m7['kernel_ratio'] == 1.0 and m7['holds'] is False, m7


def main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith('test_') and callable(f)]
    bad = 0
    for n, f in tests:
        try:
            f(); print('PASS', n)
        except Exception as e:                                           # noqa: BLE001
            bad += 1; print('FAIL', n, type(e).__name__, str(e)[:1500])
    print(f'{len(tests) - bad} passed, {bad} failed, of {len(tests)}')
    return bad


if __name__ == '__main__':
    sys.exit(main())
