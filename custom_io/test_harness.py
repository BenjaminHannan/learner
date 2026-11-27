"""python3 -m custom_io.test_harness [--data DIR]  -- end-to-end smoke test on CPU (~1 min)."""
import argparse, contextlib, io, json, os, random, subprocess, sys, tempfile, time
from types import SimpleNamespace
import torch
import torch.nn as nn
import torch.nn.functional as F
from custom_io import data as D
from custom_io import train
from custom_io.evalx import CHAIN5, MULTISTEP, chain_panel, donor_all, donor_eval, donor_pairs, eval_all, evaluate, is_hit, norm, subsample
from custom_io import analyze
from custom_io.models import build, load_model
from custom_io.models.base import Model

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = time.time()


def step(msg):
    print(f'[{time.time() - T0:6.1f}s] {msg}', flush=True)


class ToyStateTalk(Model):
    """Toy reasoner/talker split. state = (masked mean of prompt embeddings, prompt mask: a time-dim tensor whose
    shape must match the CURRENT batch); talk = linear head -> 9 answer slots. Uses nothing from `batch` but its shape."""
    LESIONS = ['zero_state', 'shuffle_state']

    def __init__(self, vocab, d=64):
        super().__init__(vocab)
        self.emb, self.head = nn.Embedding(len(vocab), d), nn.Linear(d, (D.MAX_ANS + 1) * len(vocab))

    def logits(self, h):
        return self.head(h).view(len(h), D.MAX_ANS + 1, -1)

    def state(self, batch, loops=None):
        m = batch['prompt_mask'][..., None].float()
        return (self.emb(batch['prompt_ids']) * m).sum(1) / m.sum(1), batch['prompt_mask']

    def talk(self, state, batch):
        assert state[1].shape == batch['prompt_mask'].shape, 'state time dim must line up with the current batch'
        return [self.vocab.decode(o) for o in self.logits(state[0]).argmax(-1).tolist()]

    def loss(self, batch):
        lg, m = self.logits(self.state(batch)[0]), batch['ans_mask']
        return F.cross_entropy(lg[m], batch['ans_ids'][m])


class ToyOracle(Model):
    """state = the batch's own answers (cheats on purpose). mode 'donor': talk() copies them out; 'current': talk()
    copies the CURRENT batch's answers instead. Checks donor/current alignment in donor_eval."""

    def __init__(self, vocab, mode):
        super().__init__(vocab)
        self.mode, self.dummy = mode, nn.Parameter(torch.zeros(1))

    def state(self, batch, loops=None):
        return batch['ans_ids'], batch['prompt_mask']

    def talk(self, state, batch):
        assert state[1].shape == batch['prompt_mask'].shape and len(state[0]) == len(batch['rows'])
        return [self.vocab.decode(a) for a in (state[0] if self.mode == 'donor' else batch['ans_ids'])]


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
    assert res['lesions'] == {}, 'a 1-loop model runs no loops sweep'
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
    # donor swap: pairing, interface, order/batch-size independence, memorised-state toy, eval_all / final_eval plumbing
    mk = lambda f, a: {'family': f, 'answer': a, 'accepted': [a], 'prompt': 'p' * len(a), 'level': 1}
    toy_rows = [mk('A', '1'), mk('A', ' One '), mk('A', 'one'), mk('B', 'z'), mk('B', 'Z'), mk('C', 'q'), mk('C', 'r')]
    pairs, skip = donor_pairs(toy_rows)
    assert dict(pairs).keys() == {0, 1, 2, 5, 6} and skip == 2 and all(j != i for i, j in pairs)       # B: one normalised answer
    assert all(toy_rows[i]['family'] == toy_rows[j]['family'] and norm(toy_rows[i]['answer']) != norm(toy_rows[j]['answer']) for i, j in pairs)
    assert dict(pairs)[1] == 0 and dict(pairs)[2] == 0 and dict(pairs)[0] in (1, 2) and donor_pairs(toy_rows) == (pairs, skip)
    ind = [r for r in D.load_rows(os.path.join(data, 'dev', 'in_dist.jsonl')) if len(r['answer']) <= D.MAX_ANS]
    sub = subsample(ind, 300)
    pairs, skip = donor_pairs(sub, 0)
    assert len(pairs) + skip == 300 and pairs == donor_pairs(sub, 0)[0] != donor_pairs(sub, 1)[0]
    assert all(sub[i]['family'] == sub[j]['family'] and norm(sub[j]['answer']) not in {norm(a) for a in sub[i]['accepted']} for i, j in pairs)
    for mode, want in (('donor', (100.0, 0.0)), ('current', (0.0, 100.0))):      # (donor_match, exact)
        orc, shuf = ToyOracle(v, mode), random.Random(1).sample(sub, 300)
        for rows_, bs in ((sub, 128), (shuf, 7), (shuf, 1)):                       # any order / batch size pairs the same rows
            r = donor_eval(orc, rows_, bs, 'cpu')
            assert (r['donor_match'], r['exact']) == want and r['n'] + r['skipped'] == 300 and r['n'] > 250, (mode, bs, r)
            assert sum(f['n'] for f in r['by_family'].values()) == r['n'] and set(r['by_family']) <= {x['family'] for x in sub}
    assert not build('plain_tf', v, d_model=64, n_layers=2, n_heads=2).supports_donor() and ToyStateTalk(v).supports_donor()
    fams = {}
    for r in ind:
        fams.setdefault(r['family'], []).append(r)
    mem = [r for f in sorted(fams)[:4] for r in subsample(fams[f], 6)]
    torch.manual_seed(0)
    toy = ToyStateTalk(v)
    mb = D.collate([D.Dataset(mem, v)[i] for i in range(len(mem))])
    opt = torch.optim.AdamW(toy.parameters(), 1e-2)
    for _ in range(300):
        toy.loss(mb).backward(); opt.step(); opt.zero_grad()
    assert evaluate(toy, mem, 8)['exact'] == 100.0, 'toy talker could not memorise its states'
    assert evaluate(toy, mem, 24, lesion='zero_state')['exact'] < 50 and evaluate(toy, mem, 24, lesion='shuffle_state')['exact'] < 50
    dr = donor_eval(toy, mem, 5, 'cpu')
    assert dr['donor_match'] == 100.0 and dr['exact'] == 0.0 and dr['n'] + dr['skipped'] == len(mem) and dr['n'] >= 12, dr
    ea = eval_all(toy, data, 20, donor=True)
    assert all(e['donor']['n'] + e['donor']['skipped'] == 20 for e in ea.values())
    assert all('donor' not in e for e in eval_all(mm, data, 4, donor=True).values()), 'plain_tf has no donor swap'
    out_io = io.StringIO()
    with contextlib.redirect_stdout(out_io):
        fin, les = train.final_eval(toy, SimpleNamespace(data=data, eval_max=20, eval_batch=16), torch.device('cpu'), contextlib.nullcontext)
    ev = [json.loads(l) for l in out_io.getvalue().splitlines()]
    assert set(les) == {'zero_state', 'shuffle_state', 'donor'} and set(les['donor']) == set(D.DEV_SPLITS) and json.dumps(les)
    assert les['donor'] == donor_all(toy, data, 20, 16, torch.device('cpu')) and set(fin) == set(D.DEV_SPLITS)
    assert ev[-1]['event'] == 'eval' and ev[-1]['lesion'] == 'donor' and set(ev[-1]['in_dist']) == {'exact', 'donor_match'}
    step(f"(e) donor swap: pairs same-family/different-answer, oracle alignment ok at batch 128/7/1, toy donor_match={dr['donor_match']:.0f} exact={dr['exact']:.0f} n={dr['n']} skipped={dr['skipped']}")
    # (f) chain-5 panel + extra_evals through train.main, and analyze on synthetic RESULT.json dicts
    bigd = os.path.join(tmp.name, 'big')
    os.makedirs(os.path.join(bigd, 'dev'))
    ind5 = [r for r in D.load_rows(os.path.join(data, 'dev', 'in_dist.jsonl'))]
    keep = [r for f_ in CHAIN5 for r in [x for x in ind5 if x['family'] == f_][:6]]
    with open(os.path.join(bigd, 'dev', 'in_dist.jsonl'), 'w') as fh:
        fh.writelines(json.dumps(r) + '\n' for r in keep)
    cp = chain_panel(mm, bigd, None, 8, 'cpu')
    assert cp['n'] == len(keep) == sum(x['n'] for x in cp['by_family'].values()) and set(cp['by_family']) == set(CHAIN5)
    class Ex(type(mm)):
        def extra_evals(self, ctx):
            assert ctx['big'] == bigd and callable(ctx['amp']) and ctx['batch_size'] == 16
            return {'interchange': {'cf_match': 50.0}, 'n': 3}
    class Bad(Ex):
        def extra_evals(self, ctx):
            raise RuntimeError('boom')
    for cls, key in ((Ex, 'extra'), (Bad, 'extra_error')):
        m2 = cls(v, d_model=64, n_layers=2, n_heads=2)
        res_ = SimpleNamespace(data=data, big_data=bigd, eval_batch=16)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            c5 = train.chain5_eval(m2, res_, torch.device('cpu'), contextlib.nullcontext)
            result = {}
            train.run_extra(m2, res_, torch.device('cpu'), contextlib.nullcontext, result)
        assert set(c5) == {'intact'} and set(c5['intact']['hits']) == {r['id'] for r in keep}
        assert key in result and (key == 'extra' or 'boom' in result[key]) and json.dumps(result)
    rr = lambda p5, c5, ind, **kw: {'status': 'ok', 'final_eval': {s: {'correct': round(10 * p5), 'n': 1000, 'exact': ind if s == 'in_dist' else p5}
                                                                   for s in analyze.POOL}, 'chain5': {'intact': {'exact': c5, 'hits': kw.get('hits', {})}}, 'lesions': {}}
    syn = tempfile.TemporaryDirectory()
    ids = [str(i) for i in range(400)]
    for nm, seed, args_ in (('tf', 100, (50, 20, 60)), ('tf', 101, (51, 22, 61)), ('tfsteps', 100, (50.5, 25, 60)), ('tfsteps', 101, (51.5, 25, 60)),
                            ('A', 100, (53, 33, 60)), ('A', 101, (53, 35, 59))):
        r = rr(*args_, hits={i: int(nm == 'A' or int(i) < 100) for i in ids} if nm in ('A', 'tf') else {})
        os.makedirs(os.path.join(syn.name, f'{nm}_s{seed}')); json.dump(r, open(os.path.join(syn.name, f'{nm}_s{seed}', 'RESULT.json'), 'w'))
    os.makedirs(os.path.join(syn.name, 'junk_s1')); open(os.path.join(syn.name, 'junk_s1', 'RESULT.json'), 'w').write('{bad')
    with contextlib.redirect_stdout(io.StringIO()):
        o = analyze.main(['--stage', 'screen', '--results', syn.name, '--out', os.path.join(syn.name, 'o.json')])
    A = o['arms']['A']
    assert abs(A['diffs']['pooled5_vs_tf']['mean'] - 2.5) < 1e-9 and abs(A['diffs']['chain5_vs_tf']['mean'] - 13) < 1e-9
    assert A['diffs']['chain5_vs_tf']['pos'] == 2 and A['diffs']['in_dist_vs_tf']['mean'] == -1.0
    G = {m['id']: m['ok'] for m in A['G']}
    assert G['G1'] is True and G['G2'] is True and G['G3'] is True and G['G4'] is True and G['G5'] == 'n/a' and 'incomplete' in A['verdict']
    assert json.load(open(os.path.join(syn.name, 'o.json')))['skipped']
    s2 = analyze.stats({1: 1.0, 2: 3.0, 3: 5.0})                         # mean 3, sd 2, t(.975,2)=4.303 -> half-width 4.303*2/sqrt(3)
    assert abs(s2['ci'][1] - 3 - 4.303 * 2 / 3 ** .5) < 1e-9 and s2['pos'] == 3 and abs(analyze.tq(5) - 2.571) < 1e-9
    assert abs(analyze.binom_two_sided(0, 10) - 2 / 1024) < 1e-12 and analyze.binom_two_sided(5, 5) == 1.0
    mc = analyze.mcnemar({('A', 100): rr(1, 1, 1, hits={i: 1 for i in ids}), ('tf', 100): rr(1, 1, 1, hits={i: 0 for i in ids[:30]} | {i: 1 for i in ids[30:]})}, 'A', 'tf', [100])
    assert (mc['b_design_only'], mc['c_base_only']) == (30, 0) and mc['p'] < 1e-8
    assert analyze.mcnemar({}, 'A', 'tf', [100])['p'] == 'not computed'
    with contextlib.redirect_stdout(io.StringIO()):
        oc = analyze.main(['--stage', 'confirm', '--results', syn.name, '--out', os.path.join(syn.name, 'c.json'), '--seeds', '100,101'])
    assert oc['arms']['A']['PASS1'][1]['mcnemar']['p'] < 0.01 and oc['arms']['A']['verdict'].startswith(('PASS-1', 'INCONCLUSIVE', 'FAIL'))
    assert 'A.A-A0' in {m['id'] for m in A['evidence']} and {m['id']: m['ok'] for m in oc['arms']['A']['PASS2']}['P2.smollm_fewshot'] == 'n/a'
    step('(f) chain-5 panel, chain5_eval/run_extra (ok + error path), analyze (CI, McNemar, G marks, n/a handling) ok')
    print(f'PASS  total wall time {time.time() - T0:.1f}s')


if __name__ == '__main__':
    main()
