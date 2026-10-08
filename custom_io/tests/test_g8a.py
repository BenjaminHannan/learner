"""python3 -m custom_io.tests.test_g8a   (CPU, about a minute; no data needed)
8a ladder: parameter counter and bands, caps sized from data (and today's caps reproduce q33's 3,302,481), cloze rows, pool schedule, plain_lm /
plain_tf_steps_g, local_runner kinds, and analyze_8a's marks on fake numbers (pass, each way to fail, missing data)."""
import json, os, sys, tempfile
from custom_io import analyze_8a as AN
from custom_io.g8a import caps as CP, cloze as Z, configs as C
from custom_io.g8a.pool import schedule
from custom_io.local_runner import parse_queue


def test_counts_today():
    cfgs, counts = C.sizes('3M')
    assert counts['B2'] == C.B2_S_PARAMS == 3_302_481, counts
    assert abs(counts['PT'] / counts['B2'] - 1) <= 0.02 and counts['PT'] == counts['LLM']
    for rung in ('10M', '30M'):
        c, n = C.sizes(rung)
        C.check_bands(rung, c, n)


def test_default_plain_equals_plain_tf_steps():
    import torch
    from custom_io.models import build
    v = C.vocab()
    torch.manual_seed(0); a = build('plain_tf_steps', v, d_model=256, n_layers=4, n_heads=4)
    torch.manual_seed(0); b = build('plain_tf_steps_g', v, d_model=256, n_layers=4, n_heads=4)
    assert a.n_params() == b.n_params() == 3_260_928
    assert all(torch.equal(x, y) for x, y in zip(a.state_dict().values(), b.state_dict().values()))


def test_cloze():
    text = ' '.join(['The quick brown fox jumps over the lazy dog while seventeen merchants argued about harvest prices.'] * 12)
    docs = [dict(id='d1', text=text, token_count=len(text) / 4)]
    rows = list(Z.cloze_rows(docs, 400))
    assert rows and rows == list(Z.cloze_rows(docs, 400)), 'deterministic'
    for r in rows:
        assert len(r['prompt']) <= 280 and Z.BLANK in r['prompt'] and 3 <= len(r['answer']) <= 12 and r['family'] == 'cloze' and r['steps'] == []
        assert Z.unblank(r).count(Z.BLANK) == 0


def test_schedule():
    s = schedule('3M', 40.0, 10 ** 6)
    assert s['steps'] == 24000 and s['floor_rules']
    s = schedule('30M', 40.0, 10 ** 7)
    assert s['steps'] >= 24000 and s['ok_reuse']


def test_caps_report_and_apply():
    rows = [dict(id='a', prompt='x ' * 100 + '7 + 5 =', answer='12', family='arith_bare', steps=['7 + 5 = 12']),
            dict(id='b', prompt='Say it. ' * 35, answer='abcdefghijklmnopqrstuvwxyz0123', family='copy_word', steps=[])]
    caps = CP.compute_rows(rows)
    assert caps['max_prompt'] == 280 and caps['max_ans'] == 30 and caps['n_reg'] == 31, caps
    for k in CP.TODAY:
        assert caps[k] >= CP.TODAY[k], 'never below today'
    small = CP.compute_rows([dict(id='c', prompt='1 + 2 =', answer='3', family='arith_bare', steps=['1 + 2 = 3'])])
    assert all(small[k] == CP.TODAY[k] for k in CP.TODAY), small


def test_queue_kinds():
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, 'q.txt')
        open(f, 'w').write('# MEM 9000\ng8a-data: DATA --data-pool /x\ng8a-speed: SPEED --rungs 3M\ng8a: 8a-3M-s400 --rung 3M --seed 400\nT --model m\nhf: H --hf-id x\n')
        got = [(n, k) for n, k, _, _ in parse_queue(f, d)]
        assert got == [('DATA', 'g8a-data'), ('SPEED', 'g8a-speed'), ('8a-3M-s400', 'g8a'), ('T', 'train'), ('H', 'hf')], got


class FakeEG:
    """Stands in for the frozen EmbeddingGemma 2 (271M params, needs transformers >= 5.19): fixed random per-char states."""
    def encode(self, prompts, T, device, chars=True):
        import torch
        g = torch.Generator().manual_seed(7)
        return torch.randn(len(prompts), T, 768, generator=g).to(device), torch.zeros(len(prompts), 768)


def _batch(vocab):
    from custom_io.data import Dataset, collate
    rows = [dict(id=f'r{i}', prompt=p, answer=a, accepted=[a], family=f, level=1, stage=1, variant='v', steps=st)
            for i, (p, a, f, st) in enumerate([('What is 12 + 30 ?', '42', 'arith_bare', ['12 + 30 = 42']), ('Echo: sune', 'sune', 'copy_word', []),
                                                ('Tom has 5 apples and gets 7 more . How many ?', '12', 'story_addsub', ['5 + 7 = 12'])])]
    ds = Dataset(rows, vocab)
    return collate([ds[j] for j in range(len(rows))])


def test_gemma_front_is_plain_at_step_0():
    import torch
    from custom_io.models import build
    v = C.vocab()
    cfg = dict(d_model=64, n_layers=2, n_heads=4)
    torch.manual_seed(3); a = build('plain_tf_steps_g', v, **cfg)
    torch.manual_seed(3); b = build('plain_tf_steps_g', v, eg_embed=True, **cfg)
    b._eg = [FakeEG()]
    assert b.n_params() - a.n_params() == 2 * 768 + 768 * 64 + 64, (b.n_params(), a.n_params())
    for k, t in a.state_dict().items():
        assert torch.equal(t, b.state_dict()[k]), k           # every plain weight starts identical (the adapter is built last)
    batch = _batch(v)
    assert torch.equal(a.loss(batch), b.loss(batch)), 'zero-initialised front must not change the loss at step 0'
    assert a.generate(batch) == b.generate(batch)
    b.loss(batch).backward()
    assert b.eg_proj.weight.grad.abs().sum() > 0, 'the adapter gets gradients'
    with torch.no_grad():
        b.eg_proj.weight.normal_(0, 0.5)
    assert not torch.equal(a.loss(batch), b.loss(batch)), 'a non-zero adapter changes the input'
    # nothing is added past the prompt: the front is zero at BOS, SEP and every position after the prompt
    b._set_front(batch, 50)
    lens = batch['prompt_mask'].sum(1)
    assert b._front[:, 0].abs().sum() == 0 and all(b._front[i, 1 + int(lens[i]):].abs().sum() == 0 for i in range(len(lens)))
    assert b.size()['frozen_borrowed'] == 271_002_624 and a.size()['frozen_borrowed'] == 0


def test_plain_lm_refuses_the_front():
    from custom_io.models import build
    try:
        build('plain_lm', C.vocab(), d_model=64, n_layers=1, n_heads=4, eg_embed=True)
    except AssertionError:
        return
    raise AssertionError('plain_lm must refuse eg_embed')


# ---- analyze_8a on fake numbers ---------------------------------------------------------------------------------------------
def fake(p5, c5=100.0, leak=0.5, calc=None):
    """A RESULT.json with five splits of 100 rows each whose pooled-5 is p5 (%)."""
    sp = {s: dict(correct=round(p5), n=100, exact=p5) for s in ('in_dist', 'answer', 'frame', 'vocab', 'variant')}
    r = dict(status='ok', final_eval=sp, chain5=dict(intact=dict(exact=c5)),
             lesions={'loops:0': {'in_dist': dict(exact=leak)}, 'donor': {'in_dist': dict(exact=p5 - 30.0)}}, n_params=1)
    if calc is not None:
        r['lesions']['calc'] = {s: dict(correct=round(calc), n=100, exact=calc) for s in ('in_dist', 'answer', 'frame', 'vocab', 'variant')}
    return r


def world(b2, pt, pub, llm=None, c5=100.0, seeds=AN.SEEDS):
    """b2/pt: {rung: base value}; per-seed jitter +-0.5 so the CI is finite but small."""
    runs = {}
    for i, s in enumerate(seeds):
        j = (i - 2.5) * 0.2
        for r in AN.RUNGS:
            runs[(r, 'B2', s)] = fake(b2[r] + j, c5)
            runs[(r, 'PT', s)] = fake(pt[r] + j)
            if llm:
                runs[(r, 'LLM', s)] = fake(llm[r] + j)
        runs[('30M', 'PUB', s)] = fake(pub + j, calc=pub + 3)
    return runs


def verdict(runs):
    return AN.analyze(runs)


def test_analyze_pass():
    res = verdict(world(dict({'3M': 74, '10M': 78, '30M': 83}), {'3M': 67, '10M': 70, '30M': 74}, pub=75, llm={'3M': 60, '10M': 63, '30M': 66}))
    assert res['verdict'] == 'PASS', json.dumps([(m['id'], m['ok']) for m in res['marks']])
    assert not any(w['hit'] for w in res['proved_wrong'])
    assert abs(res['reported']['pooled5']['3M/B2']['mean'] - 74) < 0.5
    assert res['reported']['public_with_calculator']['mean'] > res['reported']['pooled5']['30M/PUB']['mean']


def marks(res):
    return {m['id']: m['ok'] for m in res['marks']}


def test_analyze_fail_modes():
    pt = {'3M': 67, '10M': 70, '30M': 74}
    # flat growth: mark 1 False and proved wrong (3M->30M gain < 2.0)
    res = verdict(world({'3M': 74, '10M': 74.5, '30M': 75}, pt, pub=70))
    assert marks(res)[1] is False and res['verdict'] == 'FAIL' and any(w['hit'] and 'flat' in w['line'] for w in res['proved_wrong'])
    # lead shrinks below half: mark 2 False, proved wrong
    res = verdict(world({'3M': 74, '10M': 78, '30M': 82}, {'3M': 66, '10M': 74, '30M': 81}, pub=70))
    assert marks(res)[2] is False and any(w['hit'] and 'half' in w['line'] for w in res['proved_wrong'])
    # mark 3: only 4 of 6 seeds ahead by 3
    runs = world({'3M': 74, '10M': 78, '30M': 83}, pt, pub=70)
    for s in (400, 401):
        runs[('30M', 'PT', s)] = fake(82.5)
    assert marks(verdict(runs))[3] is False
    # mark 4: 3M below 72 stops before 10M
    res = verdict(world({'3M': 70, '10M': 74, '30M': 79}, {'3M': 63, '10M': 66, '30M': 70}, pub=70))
    assert marks(res)[4] is False and res['stop_rules']['stop_before_10M'] is True
    # mark 5 and good-enough proved wrong: public model beats B2 at 30M
    res = verdict(world({'3M': 74, '10M': 78, '30M': 83}, pt, pub=85))
    assert marks(res)[5] is False and any(w['hit'] and 'good enough' in w['line'] for w in res['proved_wrong'])
    # public model within +2.0: mark 5 False without proved wrong
    res = verdict(world({'3M': 74, '10M': 78, '30M': 83}, pt, pub=82))
    assert marks(res)[5] is False and not any(w['hit'] and 'good enough' in w['line'] for w in res['proved_wrong'])
    # guard: chain-5 under 99
    res = verdict(world({'3M': 74, '10M': 78, '30M': 83}, pt, pub=70, c5=95.0))
    assert marks(res)['guard'] is False and res['verdict'] == 'FAIL'
    # stop rule: 10M below 3M
    res = verdict(world({'3M': 74, '10M': 73, '30M': 74}, pt, pub=70))
    assert res['stop_rules']['no_30M'] is True


def test_analyze_missing():
    res = verdict({})
    assert res['verdict'] == 'incomplete' and all(m['ok'] == 'n/a' for m in res['marks'])
    runs = world({'3M': 74, '10M': 78, '30M': 83}, {'3M': 67, '10M': 70, '30M': 74}, pub=70)
    runs = {k: v for k, v in runs.items() if not (k[0] == '30M' and k[1] == 'PUB')}
    res = verdict(runs)
    assert marks(res)[5] == 'n/a' and res['verdict'] == 'incomplete'


def test_analyze_load_layouts():
    with tempfile.TemporaryDirectory() as d:
        for sub in ('8a-3M-s400/B2', '8a-3M-s400/PT', '8a-30M-s400-PUB'):
            os.makedirs(os.path.join(d, sub))
            json.dump(fake(70), open(os.path.join(d, sub, 'RESULT.json'), 'w'))
        os.makedirs(os.path.join(d, '8a-3M-s401', 'B2'))
        json.dump(dict(status='time_cap'), open(os.path.join(d, '8a-3M-s401', 'B2', 'RESULT.json'), 'w'))
        runs, boxes, skipped = AN.load([d])
        assert set(runs) == {('3M', 'B2', 400), ('3M', 'PT', 400), ('30M', 'PUB', 400)} and len(skipped) == 1, (set(runs), skipped)


if __name__ == '__main__':
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn()
                print('ok  ', name)
            except Exception as e:
                fails += 1
                import traceback
                traceback.print_exc()
                print('FAIL', name, repr(e)[:300])
    sys.exit(1 if fails else 0)
