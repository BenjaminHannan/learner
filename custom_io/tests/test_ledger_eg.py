"""python3 -m custom_io.tests.test_ledger_eg   (CPU, about a minute; the loss fingerprint needs the skills data at data.DEFAULT_DATA / $CUSTOM_IO_DATA)
EG arms (design/EG2-embedding.md): (1) both switches off is exactly B2 (the fingerprints test_ledger_span took at HEAD 0265b8bc5); (2) eg_embed adds only
ln_eg / eg_proj (last), zero-initialised, so the seeded model computes B2's loss and answers exactly at step 0, and the extra input term then learns;
(3) eg_teach adds only ln_mt / mt_head (last): loss = B2 loss + w * meaning, the teacher is only ever run on the loss batch (never in generate, the
lesions or the donor swap), and the shipped size drops the head; (4) the frozen EmbeddingGemma never shows up in parameters(), the optimizer or the
checkpoint; talk() embeds the CURRENT rows (donor swap). A stub stands in for EmbeddingGemma 2 here; with $CUSTOM_IO_EG2 (a local copy) and
transformers >= 5.19 importable, (5) also checks the real tokenizer's char -> token map on 2000 training prompts and runs one real forward."""
import hashlib, os, sys, time
import numpy as np
import torch
from custom_io.data import DEFAULT_DATA
from custom_io.models.ledger import Ledger
from custom_io.tests.test_ledger import M_CFG, SMALL, batch_of, train_rows, vocab
from custom_io.tests.test_ledger_span import GOLD, GOLD_TRAIN_BYTES

S_CFG = dict(d=256, n_heads=4, reader_layers=2, blocks=2, n_loops=8, mlp=4.8)


class StubEG:
    """Deterministic stand-in for models/eg.FrozenEG: per-char states and a pooled vector made from the prompt text alone; logs every prompt it embeds."""

    def __init__(self):
        self.seen = []

    def encode(self, prompts, T, device, chars=True):
        self.seen += list(prompts)
        H = torch.zeros(len(prompts), T, 768)
        pooled = torch.zeros(len(prompts), 768)
        for b, p in enumerate(prompts):
            g = torch.Generator().manual_seed(int(hashlib.sha1(p.encode()).hexdigest()[:8], 16))
            n = min(len(p), T)
            H[b, :n] = torch.randn(n, 768, generator=g) * 40
            pooled[b] = torch.randn(768, generator=g)
        return (H.to(device) if chars else None), pooled.to(device)


def seeded(cfg, seed=0, v=None, **kw):
    torch.manual_seed(seed)
    m = Ledger(v or vocab(), **{**cfg, **kw})       # kw may override a cfg key (reader_layers)
    if hasattr(m, '_eg'):
        m._eg = [StubEG()]
    return m


def data_ok():
    f = os.path.join(DEFAULT_DATA, 'train.jsonl')
    return os.path.exists(f) and os.path.getsize(f) == GOLD_TRAIN_BYTES


def test_off_is_b2():
    """eg_embed=False, eg_teach=0: the B2 fingerprints (params, keys, seeded init, loss, aux) of the code before span or the EG arms existed."""
    v, rows = vocab(), train_rows(48, 4)
    for name, cfg in (('SMALL', SMALL), ('M', M_CFG)):
        gd, m = GOLD[name], seeded(cfg, 0, v, copy=True, eg_embed=False, eg_teach=0.0)
        sd = m.state_dict()
        assert m.n_params() == gd['params'] and len(sd) == gd['keys'], (name, m.n_params(), len(sd))
        assert hashlib.sha1(repr([(k, tuple(t.shape)) for k, t in sd.items()]).encode()).hexdigest() == gd['keyhash'], name
        assert abs(sum(float(t.double().abs().sum()) for t in sd.values()) / gd['wabs'] - 1) < 1e-8, name
        assert not hasattr(m, '_eg') and not hasattr(m, 'eg_proj') and not hasattr(m, 'mt_head')
        b = batch_of(rows, v)
        assert 'z1' not in m.run(b)
        if data_ok():
            loss, aux = m.loss(b)
            assert abs(loss.item() - gd['loss']) < 1e-4, (name, loss.item(), gd['loss'])
            assert set(aux) == set(gd['aux']) and all(abs(float(aux[k]) - x) < 1e-4 for k, x in gd['aux'].items()), (name, aux)
        print(f'  {name}: {m.n_params():,} params, init {"+ loss " if data_ok() else ""}match B2')
    print('ok off_is_b2')


def test_embed_init_and_learning():
    """eg_embed: keys = B2's + ln_eg + eg_proj; every B2 weight identical at the same seed; eg_proj zero, so loss, aux and answers equal B2's at step 0;
    after one step eg_proj has moved and the answers depend on the EmbeddingGemma states; size counts the 271,002,624 borrowed params."""
    v, rows = vocab(), train_rows(48, 4)
    a, m = seeded(SMALL, 7, v, copy=True), seeded(SMALL, 7, v, copy=True, eg_embed=True)
    sa, sm = a.state_dict(), m.state_dict()
    assert list(sm)[:len(sa)] == list(sa) and list(sm)[len(sa):] == ['ln_eg.weight', 'ln_eg.bias', 'eg_proj.weight', 'eg_proj.bias'], list(sm)[len(sa):]
    assert all(torch.equal(sa[k], sm[k]) for k in sa)
    assert (m.eg_proj.weight == 0).all() and (m.eg_proj.bias == 0).all()
    b = batch_of(rows, v)
    la, xa = a.loss(b)
    lm, xm = m.loss(b)
    assert torch.equal(la, lm) and set(xa) == set(xm) and all(torch.equal(xa[k], xm[k]) for k in xa), (la.item(), lm.item())
    a.eval(); m.eval()
    assert a.generate(b) == m.generate(b)
    m.train()
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=1e-2)
    lm, _ = m.loss(b)
    lm.backward()
    assert m.eg_proj.weight.grad is not None and m.eg_proj.weight.grad.abs().sum() > 0
    opt.step(); opt.zero_grad()
    assert m.eg_proj.weight.abs().sum() > 0
    m.eval()
    X1 = m.read(b)[0]
    m.eg().encode = (lambda f: lambda p, T, d, chars=True: (lambda r: (r[0] * 0 if r[0] is not None else None, r[1]))(f(p, T, d, chars)))(m.eg().encode)
    X0 = m.read(b)[0]
    assert not torch.allclose(X0, X1), 'the reader output does not depend on the EmbeddingGemma states'
    S = seeded(S_CFG, 0, v, copy=True, eg_embed=True).size()
    assert S == dict(trainable=3_302_481 + 1_536 + 196_864, discarded=0, frozen_borrowed=271_002_624, shipped_trainable=3_500_881,
                     whole=3_500_881 + 271_002_624), S
    print(f'  S cfg eg_embed: {S}')
    print('ok embed_init_and_learning')


def test_no_window_arms():
    """PASS-MARKS.md addendum 6: reader_layers=0 drops exactly the 2 conv blocks (R0), and EGR (eg_embed + reader_layers=0) is R0 plus ln_eg /
    eg_proj, zero-initialised, so at step 0 its loss equals R0's; the sizes match the ones written in the addendum."""
    v, rows = vocab(), train_rows(48, 4)
    S = {k: seeded(S_CFG, 0, v, copy=True, **c).size() for k, c in (('B2', {}), ('R0', dict(reader_layers=0)),
                                                                  ('EGR', dict(eg_embed=True, reader_layers=0)))}
    assert S['B2']['whole'] - S['R0']['whole'] == 656_896 and S['R0']['whole'] == 2_645_585, S
    assert S['EGR']['trainable'] == 2_843_985 and S['EGR']['whole'] == 273_846_609 and S['EGR']['frozen_borrowed'] == 271_002_624, S['EGR']
    r0, egr = seeded(SMALL, 3, v, copy=True, reader_layers=0), seeded(SMALL, 3, v, copy=True, eg_embed=True, reader_layers=0)
    assert len(r0.reader.blocks) == 0 and not any('reader.blocks' in k for k in egr.state_dict())
    b = batch_of(rows, v)
    l0, x0 = r0.loss(b)
    l1, x1 = egr.loss(b)
    assert torch.equal(l0, l1) and all(torch.equal(x0[k], x1[k]) for k in x0), (l0.item(), l1.item())
    print(f'  R0 {S["R0"]["whole"]:,}; EGR trainable {S["EGR"]["trainable"]:,}, whole {S["EGR"]["whole"]:,}')
    print('ok no_window_arms')


def test_eg_only_reader():
    """PASS-MARKS.md addendum 7, EGO (eg_embed, reader_layers=0, letters_in=False): the prompt's letter ids never reach the reader (changing them
    leaves its output unchanged, while EGR's changes), the letter table still trains as the talker's alphabet, eg_proj gets a gradient, and the
    size equals EGR's. letters_in=False without eg_embed is refused."""
    v, rows = vocab(), train_rows(48, 4)
    egr = seeded(SMALL, 5, v, copy=True, eg_embed=True, reader_layers=0)
    ego = seeded(SMALL, 5, v, copy=True, eg_embed=True, reader_layers=0, letters_in=False)
    assert ego.size() == egr.size() and ego.n_params() == egr.n_params()
    assert seeded(S_CFG, 0, v, copy=True, eg_embed=True, reader_layers=0, letters_in=False).size() == dict(
        trainable=2_843_985, discarded=0, frozen_borrowed=271_002_624, shipped_trainable=2_843_985, whole=273_846_609)
    b = batch_of(rows, v)
    with torch.no_grad():
        for mm in (egr, ego):
            mm.eg_proj.weight.normal_(0, 0.02)
    n = ego.reader.tok.num_embeddings
    b_rel = dict(b, prompt_ids=torch.where(b['prompt_mask'], (b['prompt_ids'] + 7) % n, b['prompt_ids']))
    assert torch.equal(ego.read(b)[0], ego.read(b_rel)[0]), 'letters reached the EGO reader'
    assert not torch.equal(egr.read(b)[0], egr.read(b_rel)[0])
    loss, _ = ego.loss(b)
    loss.backward()
    assert ego.reader.tok.weight.grad.abs().sum() > 0 and ego.eg_proj.weight.grad.abs().sum() > 0
    try:
        Ledger(v, **SMALL, copy=True, letters_in=False)
        raise AssertionError('letters_in=False without eg_embed was accepted')
    except AssertionError as e:
        assert 'needs eg_embed' in str(e), e
    print('ok eg_only_reader')


def test_mlp_adapter():
    """PASS-MARKS.md addendum 8, EGM (EGO with eg_adapter='mlp'): adds exactly eg_hid (768 -> d) to EGO's keys, zero-initialised output, so at step 0 it
    computes what EGO computes; after one step the hidden layer gets a gradient; the S-cfg size matches the addendum."""
    v, rows = vocab(), train_rows(48, 4)
    base = dict(copy=True, eg_embed=True, reader_layers=0, letters_in=False)
    ego, egm = seeded(SMALL, 9, v, **base), seeded(SMALL, 9, v, **base, eg_adapter='mlp')
    assert set(egm.state_dict()) - set(ego.state_dict()) == {'eg_hid.weight', 'eg_hid.bias'}
    b = batch_of(rows, v)
    assert torch.equal(ego.loss(b)[0], egm.loss(b)[0])
    opt = torch.optim.AdamW(egm.parameters(), lr=1e-2)
    for _ in range(2):
        opt.zero_grad()
        egm.loss(b)[0].backward()
        opt.step()
    assert egm.eg_hid.weight.grad.abs().sum() > 0 and egm.eg_proj.weight.abs().sum() > 0
    assert seeded(S_CFG, 0, v, **base, eg_adapter='mlp').size() == dict(
        trainable=2_909_777, discarded=0, frozen_borrowed=271_002_624, shipped_trainable=2_909_777, whole=273_912_401)
    print('ok mlp_adapter')


def test_teach_loss_and_never_at_eval():
    """eg_teach: keys = B2's + ln_mt + mt_head; B2 weights identical at the same seed; loss = B2 loss + w * meaning (B2 aux unchanged); answers equal
    B2's (the head never touches inference); the teacher embeds only the loss batch's prompts, never anything in generate / lesions / donor."""
    from custom_io.evalx import donor_eval
    v, rows = vocab(), train_rows(48, 4)
    a, m = seeded(SMALL, 3, v, copy=True), seeded(SMALL, 3, v, copy=True, eg_teach=0.1)
    sa, sm = a.state_dict(), m.state_dict()
    assert list(sm)[len(sa):] == ['ln_mt.weight', 'ln_mt.bias', 'mt_head.weight', 'mt_head.bias'] and all(torch.equal(sa[k], sm[k]) for k in sa)
    b = batch_of(rows, v)
    la, xa = a.loss(b)
    lm, xm = m.loss(b)
    assert set(xm) == set(xa) | {'meaning'} and all(torch.equal(xa[k], xm[k]) for k in xa)
    assert 0 < float(xm['meaning']) < 2 and abs(lm.item() - (la.item() + 0.1 * float(xm['meaning']))) < 1e-5
    assert m.eg().seen == [r['prompt'] for r in rows]
    lm.backward()
    assert m.mt_head.weight.grad.abs().sum() > 0 and m.core[0].q.weight.grad.abs().sum() > 0
    m.eg().seen.clear()
    a.eval(); m.eval()
    assert a.generate(b) == m.generate(b)
    for les in m.LESIONS + ['loops:0', 'loops:1']:
        m.generate(b, les)
    donor_eval(m, rows[:24], 8, 'cpu')
    assert m.eg().seen == [], 'the teacher ran outside the training loss'
    S = seeded(S_CFG, 0, v, copy=True, eg_teach=0.1).size()
    assert S['discarded'] == 2 * 256 + 256 * 256 + 256 and S['shipped_trainable'] == S['whole'] == 3_302_481 and S['frozen_borrowed'] == 0, S
    print(f'  S cfg eg_teach: {S}')
    print('ok teach_loss_and_never_at_eval')


def test_frozen_part_never_trained_or_saved():
    """The EmbeddingGemma object is not a submodule: not in parameters(), state_dict() or a checkpoint round trip; talk() embeds the CURRENT rows."""
    from custom_io.evalx import donor_eval
    v, rows = vocab(), train_rows(48, 5)
    m = seeded(SMALL, 1, v, copy=True, eg_embed=True)
    assert 'eg' not in dict(m.named_children()) and not any(k.startswith(('_eg', 'eg.')) for k in m.state_dict())
    m2 = seeded(SMALL, 2, v, copy=True, eg_embed=True)
    m2.load_state_dict(m.state_dict())
    m.eval()
    with torch.no_grad():
        m.eg_proj.weight.normal_(std=0.02)
    m.eg().seen.clear()
    r = donor_eval(m, rows[:24], 8, 'cpu')
    assert r['n'] > 0
    assert len(m.eg().seen) >= 2 * r['n'], (len(m.eg().seen), r['n'])     # each pair embeds the donor (state) and the current row (talk)
    print('ok frozen_part_never_trained_or_saved')


def test_bf16_states_without_autocast_and_queue_env():
    """EmbeddingGemma gives bf16 states on cuda: read() must work with them outside autocast too; queue 36's `# ENV` lines reach every run."""
    from custom_io.local_runner import parse_queue, queue_env
    v, rows = vocab(), train_rows(8, 6)
    m = seeded(SMALL, 4, v, copy=True, eg_embed=True)
    f = m.eg().encode
    m.eg().encode = lambda p, T, d, chars=True: (lambda r: (r[0].to(torch.bfloat16), r[1]))(f(p, T, d, chars))
    X, _ = m.read(batch_of(rows, v))
    assert X.dtype == torch.float32 and torch.isfinite(X).all()
    qd = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'queue_local')
    for name, runs in (('36-pc-eg2.txt', ['EGM_s200', 'EGM_s201', 'EGO_s200', 'EGO_s201', 'EGR_s200', 'EGR_s201']),
                       ('38-pc-eg-teacher.txt', ['R0_s200', 'R0_s201', 'EGE_s200', 'EGE_s201', 'EGT_s200', 'EGT_s201'])):
        q = os.path.join(qd, name)
        env = queue_env(q)
        assert set(env) == {'PYTHONPATH', 'CUSTOM_IO_EG2'} and env['PYTHONPATH'].startswith('C:\\Users\\benja\\eg_site;'), env
        assert [r[0] for r in parse_queue(q)] == runs, (name, [r[0] for r in parse_queue(q)])
    print('ok bf16_states_without_autocast_and_queue_env')


def test_round_readout():
    """Test LR (PASS-MARKS.md addendum 5): round_readout=0 is B2 (fingerprints); round_readout=1 adds no parameter and no key, keeps the init and the
    answers, and adds exactly the final readout's losses taken after earlier iterations: the round-3 term equals the final losses of the same model
    stopped after iteration 3, on rows whose program (L <= 2 steps) is written by then."""
    from custom_io.models import progparse as pp
    v = vocab()
    gd, m0 = GOLD['SMALL'], seeded(SMALL, 0, v, copy=True, round_readout=0.0)
    assert m0.n_params() == gd['params'] and len(m0.state_dict()) == gd['keys']
    if data_ok():
        loss, aux = m0.loss(batch_of(train_rows(48, 4), v))
        assert abs(loss.item() - gd['loss']) < 1e-4 and 'rounds' not in aux
    a, m = seeded(SMALL, 8, v, copy=True), seeded(SMALL, 8, v, copy=True, round_readout=1.0)
    sa, sm = a.state_dict(), m.state_dict()
    assert list(sa) == list(sm) and all(torch.equal(sa[k], sm[k]) for k in sa) and a.n_params() == m.n_params()
    rows = train_rows(48, 4)
    b = batch_of(rows, v)
    la, xa = a.loss(b)
    lm, xm = m.loss(b)
    assert set(xm) == set(xa) | {'rounds'} and all(torch.allclose(xa[k], xm[k]) for k in xa)
    assert float(xm['rounds']) > 0 and abs(lm.item() - (la.item() + float(xm['rounds']))) < 1e-4
    a.eval(); m.eval()
    assert a.generate(b) == m.generate(b)
    # equivalence: round t = 3 vs the final readout of the same weights stopped after iteration 3
    short = [r for r in train_rows(400, 11) if len(pp.row_targets(r)['prog']) <= 2][:40]
    bs = batch_of(short, v)
    g = m.gold(short, 'cpu')
    o = m.run(bs, gold=g, rounds=True)
    assert [t for t, *_ in o['rounds']] == [1, 2, 3, 4, 5, 6]
    r3 = m.round_loss(dict(o, rounds=[x for x in o['rounds'] if x[0] == 3]), g, bs)
    import types
    m4 = seeded(SMALL, 8, v, copy=True)
    m4.load_state_dict(m.state_dict())
    m4.run = types.MethodType(lambda self, batch, gold=None, rounds=False, **kw: Ledger.run(self, batch, loops=4, gold=gold), m4)
    _, x4 = m4.loss(bs)
    want = sum(float(x4[k]) for k in ('mode', 'ans', 'word', 'gen'))
    assert abs(r3.item() - want) < 1e-4, (r3.item(), want)
    print(f'  round-3 term {r3.item():.5f} = final readout after iteration 3 {want:.5f}')
    print('ok round_readout')


def test_real_tokenizer_alignment():
    """With $CUSTOM_IO_EG2 and transformers >= 5.19: every char of 2000 training prompts lies inside the token it maps to; digits map to single-digit
    tokens; one real forward gives finite states of the right shape and zeros past each prompt."""
    path = os.environ.get('CUSTOM_IO_EG2')
    try:
        import transformers
        ok = path and tuple(int(x) for x in transformers.__version__.split('.')[:2]) >= (5, 19)
    except ImportError:
        ok = False
    if not ok:
        print('  skipped: set CUSTOM_IO_EG2 to a local copy and put transformers >= 5.19 on the path')
        return
    from custom_io.models.eg import PREFIX, FrozenEG
    eg = FrozenEG(path).load(torch.device('cpu'))
    rows = train_rows(2000, 9)
    n0, bad, digits = len(PREFIX), 0, 0
    for r in rows:
        p = r['prompt']
        ids, c2t = eg.align(p)
        off = eg.tok(PREFIX + p, return_offsets_mapping=True)['offset_mapping']
        assert len(c2t) == len(p) and (c2t >= 0).all()
        for i, j in enumerate(c2t.tolist()):
            s, e = off[j]
            bad += not (s <= n0 + i < e)
            if p[i].isdigit():
                digits += 1
                assert eg.tok.convert_ids_to_tokens(int(ids[j])) == p[i], (p, i, eg.tok.convert_ids_to_tokens(int(ids[j])))
    assert bad == 0, bad
    ps = [r['prompt'] for r in rows[:4]]
    T = max(map(len, ps)) + 3
    H, pooled = eg.encode(ps, T, torch.device('cpu'))
    assert H.shape == (4, T, 768) and pooled.shape == (4, 768) and torch.isfinite(H).all()
    assert all((H[b, len(p):] == 0).all() for b, p in enumerate(ps)) and all((H[b, :len(p)].abs().sum(-1) > 0).all() for b, p in enumerate(ps))
    print(f'  real tokenizer: {len(rows)} prompts, every char inside its token, {digits} digit chars on single-digit tokens')
    print('ok real_tokenizer_alignment')


if __name__ == '__main__':
    torch.set_num_threads(min(torch.get_num_threads(), 2))
    t0 = time.time()
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            t = time.time()
            fn()
            print(f'  [{name} {time.time() - t:.0f}s]')
    print(f'all ok ({time.time() - t0:.0f}s)')
