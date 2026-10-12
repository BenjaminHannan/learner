"""python3 -m custom_io.tests.test_b3at_run   (CPU, a few minutes; no Gemma: eg_embed off; run with OMP_NUM_THREADS=2)
(1) train.py end to end with --model b3at (the agent-turn model, arm AT) on a tiny synthetic data dir (train.jsonl, six dev splits, a 'big' dev for the chain-5 panel), caps with le 95
(--caps), a few steps, --final-eval: RESULT.json has the final eval, the lesions (loops:0, loops:32, donor, noexec, opswap, nocopy, zero_state, shuffle_state), chain-5, extra (g2,
op_acc, noexec, write_copy, h1, b3, talker ...), the cap counters (every fault counter 0: turns_over, tape_entry_over, writer_over, unended, turn_rounds_over,
steps_unparsed, no_trace, steps_over; turn_cap and turn_rounds_capped are reported only) and a checkpoint that load_model rebuilds as a B3AT.
(2) AT-0 (viii) (AT-BUILD-SPEC sec. 6 item 8): the 3M config of arm AT (g8a/configs.b3at_cfg under g8a/caps_b3g2.json, as job.py builds it) has a trained count within 2% of g2c3s
(4,023,976), printed with its breakdown; the job path's helpers accept the AT arm (train_args builds a b3at command, check_b3 passes, the arm pins caps_b3g2.json)."""
import json, os, subprocess, sys, tempfile
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def test_train_py():
    d, big = tempfile.mkdtemp(), tempfile.mkdtemp()
    for root in (d, big):
        os.makedirs(os.path.join(root, 'dev'))
    with open(os.path.join(d, 'train.jsonl'), 'w') as f:
        for r in rows(48):
            f.write(json.dumps(r) + '\n')
    sp = ['in_dist', 'answer', 'frame', 'vocab', 'variant', 'family']
    for root in (d, big):
        for s in sp:
            with open(os.path.join(root, 'dev', s + '.jsonl'), 'w') as f:
                for r in rows(12, 100):
                    f.write(json.dumps(dict(r, id=r['id'] + s)) + '\n')
    caps = os.path.join(d, 'caps.json')
    json.dump(dict(max_prompt=400, max_ans=12, n_num=16, w_max=80, n_res=11, n_reg=13, plain_target=64, le=95), open(caps, 'w'))
    out = os.path.join(d, 'out')
    cfg = dict(d=48, n_heads=2, reader_layers=1, blocks=1, mlp=2.0, n_loops=12, label='settled', span_copy=True, span_idx=True, span_end=True, ans_drill=0.25, any_round=True, gap_p=0,
               no_slots=True, no_place=True, bytes=True, as_written=True, writer_inner=24)
    cmd = [sys.executable, '-m', 'custom_io.train', '--model', 'b3at', '--cfg', json.dumps(cfg), '--data', d, '--big-data', big, '--steps', '80', '--batch', '8', '--lr', '3e-3', '--warmup', '5',
           '--log-every', '2', '--final-eval', '--eval-batch', '8', '--eval-max', '12', '--caps', caps, '--out', out, '--seed', '1']
    p = subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, PYTHONPATH=ROOT, OMP_NUM_THREADS='1'), capture_output=True, text=True)
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-4000:]
    res = json.load(open(os.path.join(out, 'RESULT.json')))
    assert res['status'] == 'ok' and res['steps'] == 80 and 'extra_error' not in res, res.get('extra_error')
    for k in ('loops:0', 'loops:32', 'donor', 'noexec', 'opswap', 'nocopy', 'zero_state', 'shuffle_state'):
        assert k in res['lesions'], (k, list(res['lesions']))
    assert 'nowordc' not in res['lesions']
    ex = res['extra']
    for k in ('g2', 'op_acc', 'noexec', 'write_copy', 'h1', 'b3', 'chain5_lesions', 'opswap', 'talker', 'at', 'at_lines', 'call_text'):
        assert k in ex, k
    assert set(ex['talker']) == {'call_lines', 'copyable'}, ex['talker'].keys()
    assert set(res['chain5']) >= {'intact', 'loops:0', 'loops:32'}
    cap = res['cap_hits']
    from custom_io import capcount
    assert all(cap[k] == 0 for k in capcount.NAMES), cap       # every fault counter the code has, not only the b3at ones
    for k in ('turns_over', 'tape_entry_over', 'writer_over', 'unended', 'turn_rounds_over', 'steps_unparsed', 'no_trace', 'steps_over', 'total'):
        assert cap[k] == 0, cap
    assert 'turn_cap' in cap and 'turn_rounds_capped' in cap, cap       # reported, not faults
    from custom_io.g8a import caps as CP
    from custom_io.models import load_model
    CP.apply(json.load(open(caps)))           # a checkpoint is rebuilt under the caps it was trained with
    m = load_model(os.path.join(out, 'checkpoint.pt'))
    assert type(m).__name__ == 'B3AT' and m.WCAP == 96
    print('ok train.py --model b3at: 80 steps, final eval + lesions %s, chain-5, extra %s, cap counters 0, checkpoint reloads (n_params %d)' % (len(res['lesions']), sorted(ex), res['n_params']))


def test_3m_count():
    """AT-0 (viii): the trained count of arm AT at 3M within 2% of g2c3s, printed with its breakdown; the job path accepts the arm."""
    from custom_io.g8a import caps as CP, configs as C
    here = os.path.join(ROOT, 'custom_io', 'g8a')
    caps = CP.apply(json.load(open(os.path.join(here, 'caps_b3g2.json'))))
    extra = {'eg_embed': True}
    if CP.n_loops_needed(caps) > 8:
        extra['n_loops'] = CP.n_loops_needed(caps)
    cfg = C.b3at_cfg('3M', extra)
    assert cfg['gap_p'] == 0 and cfg['bytes'] and cfg['no_slots'] and cfg['as_written'], cfg
    bd = C.b3g2_breakdown(cfg, 'b3at')
    n = C.n('b3at', cfg)
    assert bd['total'] == n, (bd, n)
    assert abs(n / C.G2C3S - 1) <= 0.02, f'3M B3AT {n:,} is more than 2% from g2c3s {C.G2C3S:,}'
    assert C.check_b3('3M', cfg, 3) == n
    assert C.MODEL_OF[C.AT_ARM] == 'b3at' and C.AT_ARM in C.ALL_ARMS
    a = C.train_args('3M', C.AT_ARM, 400, 10, '/job/pool', caps='/job/caps.json', b2_extra=extra)
    assert a[a.index('--model') + 1] == 'b3at' and json.loads(a[a.index('--cfg') + 1]) == cfg, a
    from custom_io.g8a import job
    class A:      # caps_dir / get_caps pin caps_b3g2.json for the AT arm exactly as for B3G2
        arms = [C.AT_ARM]
    assert job.caps_dir(A, '/job/pool') == '/job/pool.caps-AT'
    print(f'ok AT-0 (viii): 3M B3AT trained {n:,} ({100 * (n / C.G2C3S - 1):+.2f}% from g2c3s {C.G2C3S:,}; writer_mlp {cfg["writer_mlp"]}): ' + ', '.join(f'{k} {v:,}' for k, v in bd.items() if k != 'total'))


if __name__ == '__main__':
    torch.set_num_threads(1)
    test_train_py()
    test_3m_count()
    print('ALL OK')
