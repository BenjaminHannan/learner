"""python3 -m custom_io.tests.test_no_plug   (CPU, a few minutes; no data files, no Gemma: a fake Gemma text model and test_b3's stub; run with OMP_NUM_THREADS=1)
The no-plug front (NO-PLUG-BUILD-SPEC-2026-10-11 sec. 3). Ben, 4:12 PM ET: "can you remove the converter plug and just have our model match gemma's".
At 30M / 100M our model is 512 wide and reads Gemma's own 512 numbers (after its final norm, before its 512 -> 768 projection) through a zero-initialised LayerNorm(512).
(a) FrozenEG(pre=True) with a fake Gemma; (b) Ledger / B3 / B3G2; (c) PlainStepsG; (d) configs; (e) 3M / 10M unchanged.
g8a/caps_b3g2.json is applied for the whole module (a process-wide setting; B3's place table needs its n_reg), so run it alone."""
import hashlib, json, os
import numpy as np
import torch
import torch.nn as nn
from custom_io.data import ByteVocab
from custom_io.models import build
from custom_io.models.eg import EG_PRE_DIM, FrozenEG
from custom_io.tests.test_b3 import CFG, StubEG, V as CV, batch_of, rows

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from custom_io.g8a import caps as CP, configs as C
CP.apply(json.load(open(os.path.join(ROOT, 'g8a', 'caps_b3g2.json'))))
C.count.cache_clear()
BV = ByteVocab()


# ---- (a) a fake Gemma text model, plugged into the real FrozenEG ----
class FakeOut:
    def __init__(self, h):
        self.last_hidden_state = h


class FakeGemma(nn.Module):
    """Same forward order as EmbeddingGemma2TextModel: embed -> (a mixing layer) -> self.norm -> self.embedding_projection (512 -> 768); returns last_hidden_state."""

    def __init__(self):
        super().__init__()
        torch.manual_seed(3)
        self.emb = nn.Embedding(300, EG_PRE_DIM)
        self.mix = nn.Linear(EG_PRE_DIM, EG_PRE_DIM)
        self.norm = nn.LayerNorm(EG_PRE_DIM)
        self.embedding_projection = nn.Linear(EG_PRE_DIM, 768, bias=False)
        self.norm_calls = 0

    def forward(self, input_ids, attention_mask):
        h = self.norm(torch.tanh(self.mix(self.emb(input_ids))) * attention_mask[..., None])
        return FakeOut(self.embedding_projection(h))


class FakeTok:
    """One token per char of the whole PREFIX + prompt, with the offsets the real tokenizer returns."""
    pad_token_id = 0

    def __call__(self, text, return_offsets_mapping=False):
        ids = [1] + [2 + (ord(c) % 250) for c in text] + [299]
        offs = [(0, 0)] + [(i, i + 1) for i in range(len(text))] + [(0, 0)]
        return dict(input_ids=ids, offset_mapping=offs)


def fake_eg(pre):
    eg = FrozenEG(path='fake', pre=pre)
    eg.m, eg.tok = FakeGemma().eval().requires_grad_(False), FakeTok()
    return eg


def test_a_frozen_eg_pre():
    dev = torch.device('cpu')
    P = ['add 12 5', 'sub 9 1 and more']
    on, off = fake_eg(True), fake_eg(False)
    seen = []
    hooks_before = len(on.m.norm._forward_hooks)
    H1, pool1 = on.encode(P, 20, dev)
    H0, pool0 = off.encode(P, 20, dev)
    assert H1.shape == (2, 20, EG_PRE_DIM) and H0.shape == (2, 20, 768)
    assert len(on.m.norm._forward_hooks) == hooks_before == 0, 'the hook is gone after the call'
    assert torch.equal(pool1, pool0), 'pooled is the post-projection mean either way'
    # the pre state projected equals the post state (the PC proves the same for the real Gemma)
    with torch.no_grad():
        proj = on.m.embedding_projection(H1)
    cm = torch.zeros(2, 20, 1)
    for b, p in enumerate(P):
        cm[b, :len(p)] = 1
    assert (proj - H0).abs().max() < 1e-5 and not H1[0, len(P[0]):].any()
    assert torch.equal(on.encode_texts(P, 20, dev), H1), 'encode_texts takes the same pre states'
    # the memo key includes pre: a pre=False twin sharing the model never gets the 512 answer back
    twin = FrozenEG(path='fake', pre=False)
    twin.m, twin.tok = on.m, on.tok
    assert twin.encode(P, 20, dev)[0].shape[-1] == 768
    # the hook is removed on error too
    bad = fake_eg(True)
    bad.m.forward = lambda **k: (_ for _ in ()).throw(RuntimeError('boom'))
    try:
        bad.encode(['x'], 4, dev)
        raise AssertionError('no error')
    except RuntimeError:
        pass
    assert len(bad.m.norm._forward_hooks) == 0
    # pre=False is bit-identical to a FrozenEG that has no pre argument at all (the old path): same ops, same bits
    old = FrozenEG(path='fake')
    old.m, old.tok = FakeGemma().eval().requires_grad_(False), FakeTok()
    assert torch.equal(old.encode(P, 20, dev)[0], H0) and not old.pre
    print('ok (a): pre=True returns the 512 post-norm state, pooled unchanged, hook removed (also on error), memo key has pre, pre=False bit-identical')


# ---- stubs for the models ----
class StubEG512(StubEG):
    def _H(self, prompts, T):
        return super()._H(prompts, T)[..., :EG_PRE_DIM].contiguous()


SMALL = dict(d=EG_PRE_DIM, n_heads=8, reader_layers=1, blocks=1, mlp=0.5, n_loops=8)
B3KW = {k: v for k, v in CFG.items() if k not in SMALL}


def mk(model, vocab, seed=0, **kw):
    torch.manual_seed(seed)
    m = build(model, vocab, **kw)
    if getattr(m, 'eg_embed', False):
        assert isinstance(m._eg[0], FrozenEG) and m._eg[0].pre == bool(getattr(m, 'eg_pre', False)), 'the model builds its FrozenEG with pre = eg_pre'
        m._eg = [StubEG512() if getattr(m, 'eg_pre', False) else StubEG()]
    return m


NOPLUG = dict(eg_embed=True, eg_pre=True, eg_adapter='none')
S = 'add 12 5 = 17'


# ---- (b) Ledger, B3, B3G2 ----
def check_ledger_like(model, vocab, extra):
    cfg = dict(SMALL, **extra)
    on = mk(model, vocab, **dict(cfg, **NOPLUG))
    off = mk(model, vocab, **dict(cfg, eg_embed=False))
    names = {n for n, _ in on.named_parameters()}
    assert not any(n.startswith(('eg_proj', 'eg_hid')) for n in names), model
    assert on.ln_eg.weight.shape == (512,) and not on.ln_eg.weight.any() and not on.ln_eg.bias.any(), model
    only = names - {n for n, _ in off.named_parameters()}
    assert only == {'ln_eg.weight', 'ln_eg.bias'}, (model, only)
    # step 0: the same loss as the same-seed model without Gemma, on a batch with calls (the chain rows have steps)
    b = batch_of(rows(8), vocab)
    out = []
    for m in (on, off):
        m.train()
        torch.manual_seed(5)
        loss, aux = m.loss(b)
        out.append(loss)
    assert torch.equal(out[0], out[1]), (model, out[0].item(), out[1].item())
    out[0].backward()
    assert on.ln_eg.weight.grad.abs().sum() > 0 and on.ln_eg.bias.grad.abs().sum() > 0, 'the gradient reaches ln_eg'
    with torch.no_grad():
        for p in on.parameters():
            if p.grad is not None:
                p -= 0.05 * p.grad
    assert on.ln_eg.weight.abs().sum() > 0 and on.ln_eg.bias.abs().sum() > 0, 'ln_eg moves after one optimizer step'
    # rule 1: tape strings and the question go through the same ln_eg path
    on.eval()
    one = batch_of([dict(id='x', family='copy_word', prompt=S, answer='x', steps=[])], vocab)
    T = one['prompt_ids'].shape[1]
    with torch.no_grad():
        eg = on.eg()
        w = on.ln_eg.weight.clone()
        if hasattr(on, 'read_texts'):           # Tool and its children: the calculator's reply is read like the question
            Xq, mq = on.read(one, talker=True)
            Xr, ir, mr = on.read_texts([S], 'cpu', T)
            assert torch.equal(Xr, Xq) and torch.equal(mr, mq), (model, 'reply read == question read, one row')
            reply = lambda: on.read_texts([S], 'cpu', T)[0]
        else:                                   # plain Ledger: eg_term is the one function both paths call
            assert torch.equal(on.eg_term([S], T, 'cpu'), on.eg_term([S], T, 'cpu', memo=False))
            reply = lambda: on.eg_term([S], T, 'cpu', memo=False)
        n0 = eg.text_pass_n
        a = reply()
        eg.offset[S] = 2.0
        c = reply()
        assert eg.text_pass_n == n0 + 2 and not torch.equal(a, c), 'Gemma reaches the reply through encode_texts'
        eg.offset.clear()
        on.ln_eg.weight.zero_(), on.ln_eg.bias.zero_()
        z = reply()
        on.ln_eg.weight.copy_(w)
        assert not torch.equal(z, a) and (hasattr(on, 'read_texts') or (not z.any() and a.any())), (model, 'zeroing ln_eg zeroes the Gemma term of a reply: it goes through ln_eg')
    # size(): ln_eg is trained, Gemma frozen
    sz = on.size()
    assert sz['frozen_borrowed'] == 271_002_624 and sz['trainable'] - off.size()['trainable'] == 1024
    print(f'ok (b) {model}: no eg_proj / eg_hid, ln_eg 512 zero at init, step-0 loss == no-Gemma loss, ln_eg moves, replies read through ln_eg, +1,024 trained')


def test_b_ledger():
    check_ledger_like('ledger', CV, dict(copy=True))


def test_b_b3():
    check_ledger_like('b3', CV, dict(B3KW, any_round=True, gap_p=0.25))


def test_b_b3g2():
    from custom_io.tests.test_b3g2 import G2
    check_ledger_like('b3g2', BV, {k: v for k, v in G2.items() if k not in ('eg_embed',) and k not in SMALL})


def test_b_guards():
    for bad in (dict(d=256), dict(eg_adapter='linear'), dict(eg_embed=False)):
        kw = dict(SMALL, **dict(NOPLUG, **bad))
        try:
            build('ledger', CV, **kw)
            raise AssertionError(bad)
        except AssertionError as e:
            assert 'eg_pre needs' in str(e), (bad, e)
    print('ok (b) guards: eg_pre needs eg_embed, adapter none and d = 512, with a clear message')


# ---- (c) the plain arm ----
def test_c_plain():
    cfg = dict(d_model=512, n_heads=8, n_layers=1)
    on = mk('plain_tf_steps_g', CV, **dict(cfg, eg_embed=True, eg_pre=True))
    off = mk('plain_tf_steps_g', CV, **cfg)
    names = {n for n, _ in on.named_parameters()}
    assert not any(n.startswith('eg_proj') for n in names) and names - {n for n, _ in off.named_parameters()} == {'ln_eg.weight', 'ln_eg.bias'}
    assert on.ln_eg.weight.shape == (512,) and not on.ln_eg.weight.any() and not on.ln_eg.bias.any()
    sz = on.size()
    assert sz['trainable'] - off.size()['trainable'] == 1024 and sz['frozen_borrowed'] == 271_002_624
    b = batch_of(rows(8), CV)
    out = []
    for m in (on, off):
        m.train()
        torch.manual_seed(5)
        r = m.loss(b)
        out.append(r[0] if isinstance(r, tuple) else r)
    assert torch.equal(out[0], out[1]), (out[0].item(), out[1].item())
    out[0].backward()
    assert on.ln_eg.weight.grad.abs().sum() > 0
    for bad in (dict(d_model=256, n_heads=4), dict(eg_embed=False)):
        try:
            mk('plain_tf_steps_g', CV, **dict(dict(cfg, eg_embed=True, eg_pre=True), **bad))
            raise AssertionError(bad)
        except AssertionError as e:
            assert 'eg_pre needs' in str(e), (bad, e)
    print('ok (c): PlainStepsG eg_pre: ln_eg(512) zero, no eg_proj, +1,024 trained, step-0 loss == no-Gemma loss, gradient reaches ln_eg')


# ---- (d) configs (caps_b3g2 in force) ----
def test_d_configs():
    for rung in ('3M', '10M'):
        for f in (lambda: C.b2_cfg(rung, {'noplug': True}), lambda: C.b3_cfg(rung, {'noplug': True}, 2), lambda: C.plain_cfg(rung, extra={'noplug': True}), lambda: C.sizes(rung, {'noplug': True})):
            try:
                f()
                raise AssertionError('no error at ' + rung)
            except ValueError as e:
                assert 'noplug is for the 30M and 100M rungs only' in str(e)
    c30 = C.b3_cfg('30M', {'noplug': True}, 2)
    n30 = C.check_b3('30M', c30, 2)
    assert (c30['d'], c30['n_heads'], c30['blocks'], c30['eg_pre'], c30['eg_adapter'], c30['eg_embed']) == (512, 8, 9, True, 'none', True) and 'noplug' not in c30
    assert abs(n30 / 30e6 - 1) <= 0.05 and abs(c30['mlp'] - 1.253) < 0.01, (n30, c30['mlp'])
    today = C.n('b3g2', C.b3_cfg('100M', None, 2))
    assert today == 102_641_692
    rows_ = []
    for bl in (None, 26, 30, 34, 37):
        c = C.b3_cfg('100M', dict({'noplug': True}, **({'blocks': bl} if bl else {})), 2)
        cnt = C.check_b3('100M', c, 2)
        assert c['blocks'] == (bl or 21) and abs(cnt / today - 1) <= 0.001, (bl, cnt)
        if bl is None:
            assert abs(c['mlp'] - 4.835) < 0.005
        bd = C.noplug_breakdown('b3g2', c)
        assert bd['ln_eg'] == 1024 and bd['total'] == cnt
        pc = C.plain_cfg('100M', C.b2_cfg('100M', {'noplug': True, **({'blocks': bl} if bl else {})}))
        pcount = C.n('plain_tf_steps_g', pc)
        assert pc['eg_pre'] and pc['d_model'] == 512 and abs(pcount / cnt - 1) <= C.PLAIN_BAND, (bl, pcount, cnt)
        rows_.append((bl or 21, cnt, pcount))
    cfgs, cnt = C.sizes('30M', {'noplug': True})
    C.check_bands('30M', cfgs, cnt)
    assert cfgs['PT']['eg_pre'] and 'LLM' not in cfgs
    # plain_cfg without b2: the blocks override (and the other extras) reach b2_cfg, not only the noplug key
    assert C.plain_cfg('100M', extra={'noplug': True, 'blocks': 30}) == C.plain_cfg('100M', C.b2_cfg('100M', {'noplug': True, 'blocks': 30}))
    seen, b2_orig = [], C.b2_cfg
    C.b2_cfg = lambda rung, extra=None: (seen.append(dict(extra or {})), b2_orig(rung, extra))[1]
    try:
        C.plain_cfg('100M', extra={'noplug': True, 'blocks': 30})
        C.plain_cfg('30M', extra={'noplug': True, 'n_loops': 10})
    finally:
        C.b2_cfg = b2_orig
    assert seen == [{'noplug': True, 'blocks': 30}, {'noplug': True, 'n_loops': 10}], seen
    print('ok (d): 30M', f'{n30:,}', 'mlp', c30['mlp'], '| 100M', ' '.join(f'{b}:{c:,}/plain {p:,}' for b, c, p in rows_), '| 3M / 10M raise')


# ---- (e) every 3M / 10M config and count unchanged (values taken at 24b0a92112) ----
def test_e_3m_10m_unchanged():
    want = {('3M', 1): 4_041_685, ('3M', 2): 4_081_871, ('10M', 1): 9_834_705, ('10M', 2): 9_930_403, ('30M', 1): 29_791_421, ('30M', 2): 30_059_983}
    for (rung, g), w in want.items():
        c = C.b3_cfg(rung, None, g)
        assert C.n('b3g2' if g == 2 else 'b3', c) == w and 'eg_pre' not in c and c['d'] == (256 if rung != '30M' else 384), (rung, g)
    assert C.n('b3g2', C.b3_cfg('100M', None, 2)) == 102_641_692
    for rung, (b2, pt) in {'3M': (4_022_353, 4_022_440), '10M': (9_815_373, 9_814_442), '30M': (29_716_793, 29_556_480)}.items():
        cfgs, cnt = C.sizes(rung, {'eg_embed': True})
        assert (cnt['B2'], cnt['PT']) == (b2, pt) and not any('eg_pre' in c for c in cfgs.values()), rung
    cfgs, cnt = C.sizes('3M', None)
    assert cnt == {'B2': 3_823_953, 'PT': 3_824_040, 'LLM': 3_824_040}
    # behaviour: the small eg_embed B3G2 (plug) loss and the parameter names are what they were
    from custom_io.tests.test_b3g2 import G2, V
    torch.manual_seed(0)
    m = build('b3g2', V, **G2)
    m._eg = [StubEG()]
    names = {n for n, _ in m.named_parameters()}
    assert {'ln_eg.weight', 'ln_eg.bias', 'eg_proj.weight', 'eg_proj.bias'} <= names and m.ln_eg.weight.shape == (768,) and not m.eg_pre
    torch.manual_seed(0)
    m.train()
    loss, _ = m.loss(batch_of(rows(8), V))
    assert abs(loss.item() - 19.309206008911133) < 1e-3, loss.item()
    print('ok (e): every 3M / 10M / 30M plug config and count unchanged; the plugged B3G2 loss is 19.3092 as before')


# ---- (f) g8a/speed.py --noplug builds the cfgs and lr job.py --noplug gives train.py; configs --noplug defaults to group 2 (CPU, nothing is timed) ----
def test_f_speed_and_configs_noplug():
    import contextlib, io, tempfile
    from custom_io.g8a import speed as S
    caps_f = os.path.join(ROOT, 'g8a', 'caps_b3g2.json')
    caps = CP.apply(json.load(open(caps_f)))        # what speed.main applies with --caps (the same caps: nothing changes for the counts cached above)
    loops = dict(n_loops=CP.n_loops_needed(caps)) if CP.n_loops_needed(caps) > 8 else {}

    def job_side(rung, arm):
        """job.py --noplug --rung RUNG: b2_extra as main() builds it, then the --cfg and --lr train_args hands to train.py for the arm."""
        b2_extra = {C.NOPLUG: True}
        b2_extra = dict(b2_extra, **loops) if loops else b2_extra
        a = C.train_args(rung, arm, 400, 100, '/x', b2_extra=b2_extra, lr=C.rung_lr(rung, b2_extra) * 1.0, caps=caps_f)
        return json.loads(a[a.index('--cfg') + 1]), float(a[a.index('--lr') + 1])

    def run_speed(*flags):
        """speed.main with probe_rows / compute_rows / time_arm stubbed: records (model, cfg, lr) per timed arm; no model is built, nothing is timed."""
        timed, saved = [], (S.probe_rows, S.time_arm, S.CP.compute_rows)
        S.probe_rows = lambda d, *a, **k: [dict(prompt='q', answer='a')]
        S.CP.compute_rows = lambda rows: dict(max_prompt=0, max_ans=0, n_num=0, w_max=0, n_res=0, n_reg=0, plain_target=0)
        S.time_arm = lambda model, cfg, rows, batch, accum, updates, warmup, device, bf16, lr: (timed.append((model, cfg, lr)), (0.1, None, 1))[1]
        try:
            with tempfile.TemporaryDirectory() as out, contextlib.redirect_stdout(io.StringIO()):
                res = S.main(['--data', 'unused', '--out', out, '--caps', caps_f, '--device', 'cpu'] + list(flags))
        finally:
            S.probe_rows, S.time_arm, S.CP.compute_rows = saved
        return timed, res

    for rung in ('30M', '100M'):
        timed, res = run_speed('--noplug', '--rungs', rung)
        assert [m for m, _, _ in timed] == ['ledger', 'plain_tf_steps_g'] and list(res['rungs'][rung])[:2] == ['B2', 'PT'], (rung, timed)
        for (model, cfg, lr), arm in zip(timed, ('B2', 'PT')):
            jcfg, jlr = job_side(rung, arm)
            assert model == C.MODEL_OF[arm] and cfg == jcfg and lr == jlr == 5e-4, (rung, arm, cfg, jcfg, lr, jlr)
            assert cfg['d' if arm == 'B2' else 'd_model'] == 512 and cfg['eg_pre'] and 'noplug' not in cfg
    assert res['rungs']['100M']['_schedule']['steps'] is None      # 100M: no pool yet, so no schedule / cost, and nothing crashed after the timing
    # without --noplug: the rungs are 3M 10M 30M (not 100M, which has no plugged B2 shape), all three arms, the rung's own lr
    timed, res = run_speed()
    assert [r for r in res['rungs']] == ['3M', '10M', '30M'] and len(timed) == 9 and [t[2] for t in timed] == [1e-3] * 6 + [1e-3 * 256 / 384] * 3, [t[2] for t in timed]
    assert all('eg_pre' not in t[1] and 'eg_embed' not in t[1] for t in timed)
    for flags in (('--noplug', '--rungs', '10M'), ('--noplug', '--rungs', '3M', '30M'), ('--noplug', '--arms', 'LLM'), ('--noplug', '--public', 'pythia31m')):
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                run_speed(*flags)
            raise AssertionError(flags)
        except SystemExit as e:
            assert e.code == 2 and '--noplug' in err.getvalue(), (flags, err.getvalue())
    # configs --noplug: group 2 unless --group is given
    def table(*flags):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            C.main(['--noplug', caps_f] + list(flags))
        return [ln.split(' noplug ')[1].split()[0] for ln in buf.getvalue().splitlines() if ' noplug ' in ln]      # the model named on each line: b3g2 or b3
    g2, g1 = table(), table('--group', '1')
    assert len(g2) == 6 and set(g2) == {'b3g2'} and table('--group', '2') == g2, g2
    assert len(g1) == 6 and set(g1) == {'b3'}, g1
    print('ok (f): speed.py --noplug times the cfgs and lr job.py --noplug gives train.py (30M, 100M; lr 5e-4), default rungs 3M 10M 30M, bad flag combos refuse; configs --noplug defaults to b3g2')


def main():
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            print(name)
            fn()
    print('ALL OK')


if __name__ == '__main__':
    main()
