"""python3 -m custom_io.test_harness [--data DIR]  -- end-to-end smoke test on CPU (~1 min)."""
import argparse, contextlib, io, json, os, random, subprocess, sys, tempfile, time
import torch
from custom_io import data as D
from custom_io import train
from custom_io.evalx import MULTISTEP, eval_all, evaluate, is_hit, norm
from custom_io.models import build, load_model

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = time.time()


def step(msg):
    print(f'[{time.time() - T0:6.1f}s] {msg}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=D.DEFAULT_DATA)
    data = ap.parse_args().data
    tmp = tempfile.TemporaryDirectory()
    vpath = os.path.join(tmp.name, 'vocab.json')

    # (a) vocab, batches, word view
    rows = D.load_rows(os.path.join(data, 'train.jsonl'))
    assert len(rows) == 200_000, len(rows)
    v = D.CharVocab.get(data, vpath, rows)
    assert os.path.exists(vpath) and len(v) == 13 + 95 and (D.PAD, D.BOS, D.EOS, D.SEP, D.UNK, D.Q0) == (0, 1, 2, 3, 4, 5)
    assert D.CharVocab.load(vpath).itos == v.itos
    assert v.encode('#') != [D.UNK] and v.encode('\u00e9') == [D.UNK] and v.decode(v.encode('a b') + [D.EOS] + v.encode('zz')) == 'a b'
    ds = D.Dataset(rows, v)
    b = D.collate([ds[i] for i in range(8)])
    B, T = b['prompt_ids'].shape
    assert B == 8 and b['ans_ids'].shape == (8, 9) and b['ans_mask'].shape == (8, 9) and b['prompt_mask'].dtype == torch.bool
    assert (b['prompt_ids'][~b['prompt_mask']] == D.PAD).all() and (b['prompt_mask'].sum(1).max() == T)
    assert all(v.decode(b['ans_ids'][i]) == b['rows'][i]['answer'] for i in range(8)) and (b['ans_ids'][b['ans_mask']] == D.EOS).sum() == 8
    cur = next(D.train_batches(ds, 8, 'curriculum', 0))
    assert [r['id'] for r in cur['rows']] == [r['id'] for r in rows[:8]]
    shuf = [r['id'] for r in next(D.train_batches(ds, 8, 'shuffled', 0))['rows']]
    assert shuf == [r['id'] for r in next(D.train_batches(ds, 8, 'shuffled', 0))['rows']] and shuf != [r['id'] for r in rows[:8]]
    p = 'Ola has 38 hats. At 9:39 -> (4 # 6)'
    assert [p[a:e] for a, e in D.word_spans(p)] == ['Ola', 'has', '38', 'hats', '.', 'At', '9:39', '->', '(', '4', '#', '6', ')']
    wid, nw = D.word_ids([p], len(p) + 3)
    assert nw[0] == 13 and wid[0, 3] == -1 and wid[0, -1] == -1 and wid[0, 0] == 0
    assert norm('  Foo  BAR ') == 'foo bar' and is_hit('Ab', {'accepted': ['ab']}) and len(MULTISTEP) == 12
    step(f'(a) vocab={len(v)} ids, collate/order/word-view ok')

    # (b) train plain_tf via the CLI (cwd=repo root), and check `-m` also works from elsewhere with PYTHONPATH
    out = os.path.join(tmp.name, 'run')
    args = ['--model', 'plain_tf', '--cfg', '{"d_model":64,"n_layers":2,"n_heads":2}', '--steps', '60', '--batch', '16',
            '--warmup', '10', '--device', 'cpu', '--data', data, '--vocab', vpath, '--log-every', '20', '--eval-every', '30',
            '--final-eval', '--eval-max', '20']
    r = subprocess.run([sys.executable, '-m', 'custom_io.train', *args, '--out', out], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    log = [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{')]
    tr = [e['loss'] for e in log if e['event'] == 'train']
    assert len(tr) == 3 and tr[-1] < tr[0], tr
    assert sum(e['event'] == 'quick_eval' for e in log) == 2
    r2 = subprocess.run([sys.executable, '-m', 'custom_io.train', '--help'], cwd=tmp.name, env=dict(os.environ, PYTHONPATH=ROOT),
                        capture_output=True, text=True)
    assert r2.returncode == 0 and '--data' in r2.stdout
    step(f'(b) trained 60 steps via CLI, loss {tr[0]:.2f} -> {tr[-1]:.2f}')
    with contextlib.redirect_stdout(io.StringIO()):        # in-process run, same seed; keep its JSON lines out of the log
        res2 = train.main([a for a in args if a != '--final-eval'] + ['--out', os.path.join(tmp.name, 'run2')])
    res = json.load(open(os.path.join(out, 'RESULT.json')))
    assert res2['final_train_loss'] == res['final_train_loss'], 'same seed must give identical training'
    step('    same seed -> identical loss (deterministic)')

    # (c) eval_all on the reloaded checkpoint
    m = load_model(os.path.join(out, 'checkpoint.pt'))
    ev = eval_all(m, data, max_per_split=20)
    assert list(ev) == D.DEV_SPLITS and all(e['n'] == 20 for e in ev.values())
    e = ev['in_dist']
    assert e['n'] == sum(f['n'] for f in e['by_family'].values()) == sum(f['n'] for f in e['by_level'].values())
    assert 0 <= e['exact'] <= 100 and e['multistep']['n'] <= 20
    assert {k: x['exact'] for k, x in ev.items()} == {k: x['exact'] for k, x in res['final_eval'].items()}, 'reload changed predictions'
    step('(c) eval_all(max_per_split=20) ok; checkpoint reload reproduces RESULT.json eval')

    # (d) RESULT.json fields
    for k in ('config', 'n_params', 'wall_s', 'train_s', 'steps_per_s', 'steps', 'final_eval', 'lesions', 'status', 'final_train_loss'):
        assert k in res, k
    assert res['n_params'] == m.n_params() and res['steps'] == 60 and res['status'] == 'ok' and res['steps_per_s'] > 0
    assert res['config']['cfg']['d_model'] == 64 and set(res['final_eval']) == set(D.DEV_SPLITS)
    assert set(res['lesions']) == {'loops:0', 'loops:1', 'loops:2'} and set(res['lesions']['loops:0']) == set(D.DEV_SPLITS)
    step(f"(d) RESULT.json ok: n_params={res['n_params']} steps/s={res['steps_per_s']:.1f} wall={res['wall_s']:.1f}s")

    # model correctness: memorise 16 dev rows (checks loss/generate alignment), batched == row-by-row decoding, lesions
    dev = random.Random(0).sample(D.load_rows(os.path.join(data, 'dev', 'in_dist.jsonl')), 16)
    torch.manual_seed(0)
    mm = build('plain_tf', v, d_model=64, n_layers=2, n_heads=2)
    batch = D.collate([D.Dataset(dev, v)[i] for i in range(16)])
    opt = torch.optim.AdamW(mm.parameters(), 3e-3)
    for _ in range(250):
        mm.loss(batch).backward(); opt.step(); opt.zero_grad()
    assert evaluate(mm, dev, 16)['exact'] == 100.0, 'could not memorise 16 rows: loss/generate misaligned'
    assert evaluate(mm, dev, 16, return_preds=True)['preds'] == evaluate(mm, dev, 1, return_preds=True)['preds']
    assert evaluate(mm, dev, 16, lesion='loops:0')['exact'] < 100
    try:
        evaluate(mm, dev, 16, lesion='shuffle_state'); raise AssertionError('should reject unknown lesion')
    except ValueError:
        pass
    assert build('plain_tf', v, d_model=64, n_layers=2, n_heads=2, n_loops=3).n_params() == mm.n_params()
    step('    memorise-16 = 100%, batched == single-row decode, lesion validation, looped has same n_params')
    print(f'PASS  total wall time {time.time() - T0:.1f}s')


if __name__ == '__main__':
    main()
