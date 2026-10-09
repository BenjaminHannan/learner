"""python3 -m custom_io.tests.test_g2_input   (CPU, about a minute; no data files, no real Gemma: StubEG as in test_b3, and a fake tokenizer for the alignment)
B3 group 2, input side (architecture/B3-GROUP2-BUILD-2026-10-09.md sec. 1, 6): V1 `bytes` (ByteVocab: 13 specials + 256 byte ids; lengths, positions, places, number / word
spans, tape widths and the Gemma alignment all count bytes), P1 `no_place` (the reader input has no place term; the table stays), N1 `no_slots` (the thinker reads
[tape; letters] only; ordinal and type tables deleted). Every switch off = the code at BASE (e070556ce5), bit for bit (reader output, loss, a 3-step run)."""
import json, os, re, subprocess, sys, tempfile, zlib
import numpy as np
import torch
import torch.nn as nn
from custom_io import capcount, data as D
from custom_io.data import ByteVocab, CharVocab, Dataset, collate, EOS, PAD, N_SPECIAL, SPECIALS
from custom_io.models import build, load_model
from custom_io.models.eg import FrozenEG, PREFIX
from custom_io.models.ledger import N_NUM
from custom_io.models.reader import place_ids
from custom_io.tests import legacy_widths
from custom_io.tests.test_b3 import CFG, StubEG, rows

BASE = 'e070556ce5'
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V, BV = CharVocab.build([]), ByteVocab()
UNI = ['Écho: café Give only the answer.', 'Tom has 12 apples and 5€ — buys 345 more. 日本語 ok?', 'naïve 7 + 5']


def batch_of(rs, vocab):
    ds = Dataset(rs, vocab, strict=False)
    return collate([ds[i] for i in range(len(rs))])


def uni_rows():
    return [dict(id='u0', family='copy_word', prompt=UNI[0], answer='café', steps=[]),
            dict(id='u1', family='chain_ops', prompt=UNI[1], answer='357', steps=['12 + 345 = 357']),
            dict(id='u2', family='chain_ops', prompt=UNI[2], answer='12', steps=['7 + 5 = 12'])]


def mk(vocab=V, seed=0, model='b3', eg=None, **kw):
    torch.manual_seed(seed)
    cfg = {**CFG, **kw}
    if vocab.is_bytes:
        cfg['bytes'] = True
    m = build(model, vocab, **cfg)
    if getattr(m, 'eg_embed', False):
        m._eg = [eg or StubEG()]
    return m


def steps(m, bl, n=3, lr=1e-3):
    opt = torch.optim.AdamW(m.parameters(), lr=lr)
    m.train()
    ls = []
    for s in range(n):
        loss = m.loss(bl[s % len(bl)])[0]
        assert torch.isfinite(loss), loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad()
        ls.append(loss.item())
    return ls


# ---- V1: the vocabulary ----
def test_bytevocab():
    assert len(BV) == 269 == N_SPECIAL + 256 and BV.itos[:13] == SPECIALS and BV.is_bytes and not V.is_bytes and BV.chars == ''
    assert BV.encode('A') == [13 + 65] and BV.encode('é') == [13 + 0xC3, 13 + 0xA9] and BV.encode('日') == [13 + b for b in '日'.encode()]
    for s in ['', 'abc 123.', 'Tom has 12 apples!', 'café', '日本語 ok? 5€ — x', 'a\nb\t', '😀 mixed ascii']:
        assert BV.decode(BV.encode(s)) == s, s
        assert BV.decode(BV.encode(s) + [EOS] + BV.encode('zz')) == s, 'decode stops at the first EOS'
        assert BV.decode([1, 3, 5, 12] + BV.encode(s) + [0]) == s, 'specials are skipped'
    for s in ['Tom has 12 apples, 345 more? (A+B)=#9', ' x ']:         # ASCII: the same text as CharVocab, different ids
        assert BV.decode(BV.encode(s)) == V.decode(V.encode(s)) == s and len(BV.encode(s)) == len(V.encode(s))
    assert BV.decode(BV.encode('é')[:1]) == '�' and BV.decode(BV.encode('日本')[:-1]) == '日�', 'errors=replace'
    assert (BV.length('café'), BV.length('abc'), V.length('café')) == (5, 3, 4)
    assert BV.clip('abcdef', 3) == 'abc' and BV.clip('café', 4) == 'caf' and BV.clip('café', 5) == 'café' and V.clip('café', 3) == 'caf'
    assert BV.offsets('abc') is None and V.offsets('café') is None and BV.offsets('café').tolist() == [0, 1, 2, 3, 5]
    assert D.unit_spans(BV, 'é ab', [(0, 1), (2, 4)]) == [(0, 2), (3, 5)] and D.unit_spans(V, 'é ab', [(0, 1)]) == [(0, 1)]
    print('ok ByteVocab: ids, round trips, ASCII = CharVocab text, replace on cut bytes, length / clip / offsets')


def test_dataset_in_bytes():
    r = [dict(id='a', prompt='é' * 104, answer='é' * 4, family='x')]          # 104 chars = 208 bytes; answer 8 bytes
    Dataset(r, BV), Dataset(r, V)
    for rr, why in (([dict(r[0], prompt='é' * 105)], 'prompt'), ([dict(r[0], answer='é' * 5)], 'answer')):
        for vocab, ok in ((BV, False), (V, True)):
            try:
                Dataset(rr, vocab)
                assert ok, (why, 'bytes should have refused')
            except AssertionError as e:
                assert not ok and 'too long' in str(e), e
    capcount.reset() if hasattr(capcount, 'reset') else None
    n0 = capcount.snapshot()['total']
    item = Dataset([dict(r[0], answer='é' * 5)], BV, strict=False)[0]
    assert len(item[1]) == D.MAX_ANS + 1 and item[1][-1] == EOS and capcount.snapshot()['total'] == n0 + 1, 'a 10-byte answer is cut to 8 ids and counted'
    b = batch_of([dict(id='u', prompt='é1', answer='é', family='x')], BV)
    assert b['prompt_ids'].tolist() == [[13 + 0xC3, 13 + 0xA9, 13 + 49]] and b['ans_ids'][0, :3].tolist() == [13 + 0xC3, 13 + 0xA9, EOS]
    print('ok Dataset / collate count bytes: asserts, the answer cut, ids')


# ---- everything off = BASE, bit for bit ----
OFF_SCRIPT = r'''
import sys, torch
torch.set_num_threads(1)
sys.path.insert(0, sys.argv[2])
from custom_io.tests import legacy_widths
legacy_widths.apply()      # uncapped: 11 operand cells, 40-char entries (the 16-row place table)
from custom_io.data import CharVocab, Dataset, collate
from custom_io.models import build
from custom_io.tests.test_b3 import CFG, rows
V = CharVocab.build([])
rs = rows(16)
ds = Dataset(rs, V, strict=False)
bl = [collate([ds[i] for i in range(s, s + 8)]) for s in range(0, 16, 8)]
out = {}
for name, kw in (('b3', {}), ('b3_any', dict(any_round=True, gap_p=0.25)), ('tool_h1', {})):
    torch.manual_seed(0)
    m = build('tool_h1' if name == 'tool_h1' else 'b3', V, **{**CFG, **kw})
    m.eval()
    with torch.no_grad():
        out[name + '_X'] = m.reader(bl[0])[0]
        o = m.run(bl[0], gold=m.gold(bl[0]['rows'], 'cpu', m.train_golds(bl[0]['rows'])) if name != 'b3_any' else None) if name != 'b3_any' else m.run(bl[0], loops=3)
        out[name + '_R'], out[name + '_w'] = o['R'], o['lword']
    m.train()
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
    L = []
    for s in range(3):
        loss = m.loss(bl[s % 2])[0]; loss.backward(); opt.step(); opt.zero_grad(); L.append(loss.detach().clone())
    out[name + '_L'] = torch.stack(L)
    out[name + '_sd'] = {k: v.clone() for k, v in m.state_dict().items()}
torch.save(out, sys.argv[1])
'''


def test_off_is_base():
    with tempfile.TemporaryDirectory() as d:
        ref = os.path.join(d, 'ref')
        os.makedirs(ref)
        arc = subprocess.Popen(['git', 'archive', BASE, 'custom_io'], cwd=ROOT, stdout=subprocess.PIPE)
        subprocess.check_call(['tar', '-x', '-C', ref], stdin=arc.stdout)
        assert arc.wait() == 0
        res = {}
        for tag, tree in (('ref', ref), ('new', ROOT)):
            subprocess.check_call([sys.executable, '-c', OFF_SCRIPT, os.path.join(d, tag + '.pt'), tree], cwd=tree, env=dict(os.environ, PYTHONPATH=tree))
            res[tag] = torch.load(os.path.join(d, tag + '.pt'))
        a, b = res['ref'], res['new']
        assert a.keys() == b.keys()
        for k in a:
            if k.endswith('_sd'):
                assert a[k].keys() == b[k].keys() and all(torch.equal(a[k][n], b[k][n]) for n in a[k]), k
            else:
                assert torch.equal(a[k], b[k]), k
        print(f'ok all switches off = {BASE}: reader output, run() state, 3 losses and every parameter equal for', sorted({k.split("_")[0] + ("_any" if "any" in k else "") for k in a}))


# ---- P1 ----
def test_no_place():
    b = batch_of(rows(8), V)
    torch.manual_seed(0)
    on, off = mk(), mk(no_place=True)
    assert on.size() == off.size() and off.reader.place.num_embeddings == on.reader.place.num_embeddings, 'the table stays a parameter'
    off.load_state_dict(on.state_dict())
    with torch.no_grad():
        xa, xb = on.reader(b)[0], off.reader(b)[0]
        assert not torch.equal(xa, xb) and (xa - xb).abs().max() > 1e-4, 'no_place changes the reader output'
        off.reader.place.weight.normal_(0, 5.0)
        assert torch.equal(xb, off.reader(b)[0]), 'with no_place the place table does not reach the reader output'
    assert torch.equal(torch.cat([off.ctrl.weight, off.reader.place.weight[:9]])[8:], off.reader.place.weight[:9]), 'registers still start from place rows'
    from custom_io.models import tool as T
    assert off.cells(torch.zeros(1, off.d)).shape[1] == 2 * T.CELLS
    print('ok no_place: output changes, table kept (same size), table not read by the reader')


# ---- N1 ----
def test_no_slots():
    rs = rows(16)
    bl = [batch_of(rs[s:s + 8], V) for s in (0, 8)]
    for any_round in (True, False):
        kw = dict(any_round=any_round, gap_p=0.25 if any_round else 0.0)
        on, off = mk(**kw), mk(no_slots=True, **kw)
        d = on.d
        dropped = (N_NUM + 3) * d
        assert on.size()['trainable'] - off.size()['trainable'] == dropped, (on.size(), off.size(), dropped)
        assert not hasattr(off, 'ordinal') and not hasattr(off, 'stype') and hasattr(on, 'ordinal')
        sd_on, sd_off = on.state_dict(), off.state_dict()
        assert set(sd_on) - set(sd_off) == {'ordinal.weight', 'stype.weight'} and all(torch.equal(sd_on[k], sd_off[k]) for k in sd_off), 'every other weight starts identical'
        X = torch.randn(2, 7, d)
        ns = torch.zeros(2, N_NUM, dtype=torch.long)
        v, S0 = off.num_memory(X, ns, ns)
        assert v.shape == (2, 0) and S0 is None and off.slot_kv(S0) is None
        v, S0 = on.num_memory(X, ns, ns)
        kv = on.slot_kv(S0)
        assert v.shape == (2, N_NUM) and S0.shape == (2, N_NUM, d) and len(kv) == len(on.core)
        kvt = [torch.randn(2, 2, on.core[0].h, 5, d // on.core[0].h) for _ in on.core]
        assert all(torch.equal(a, c) for a, c in zip(off.join_kv(None, kvt), kvt)) and off.join_kv(kv, kvt)[0].shape[3] == N_NUM + 5
        sp = off.spans('Tom has 12 apples and 345 more, 6 7 8.')
        assert int(sp[0].sum()) == int(sp[1].sum()) == 0 and int(sp[4].sum()) > 0, 'no number spans, word spans kept'
        assert int(on.spans('Tom has 12 apples and 345 more, 6 7 8.')[0].sum()) > 0
        ls = steps(off, bl)
        print(f'  any_round={any_round}: size {on.size()["trainable"]:,} -> {off.size()["trainable"]:,} (-{dropped}), 3 steps finite', [round(x, 2) for x in ls])
        off.eval()
        with torch.no_grad():
            ans = off.generate(batch_of(rs[:2], V))
        assert len(ans) == 2
    t = mk(no_slots=True, eg_embed=True, tok_think=True, any_round=True)       # tok_think combines: the letters are token spots, the slots are gone
    steps(t, bl, 2)
    print('ok no_slots: exactly (N_NUM + 3) * d fewer weights, others identical, no slots in mask / K/V, no number spans, trains (with and without any_round, with tok_think)')


# ---- V1 in the model ----
def test_bytes_model():
    assert D.MAX_PROMPT == 208
    mod_rows = uni_rows() + rows(5)
    b = batch_of(mod_rows, BV)
    T = b['prompt_ids'].shape[1]
    assert int(b['prompt_mask'][0].sum()) == len(UNI[0].encode()) > len(UNI[0])
    m = mk(BV, any_round=True, gap_p=0.25)
    assert m.is_bytes and m.reader.by_bytes and m.reader.tok.num_embeddings == 269 and m.bias.shape[0] == 269
    try:
        build('b3', BV, **CFG)
        raise SystemExit('bytes vocab without cfg bytes should be refused')
    except AssertionError as e:
        assert 'ByteVocab' in str(e)
    try:
        build('b3', V, **{**CFG, 'bytes': True})
        raise SystemExit('cfg bytes with CharVocab should be refused')
    except AssertionError:
        pass
    # places count bytes from the word's right end; spans are byte offsets
    pi = place_ids(['é ab'], 5, by_bytes=True)[0].tolist()
    assert pi == [1, 0, 15, 1, 0], pi
    assert place_ids(['é ab'], 4)[0].tolist() == [0, 15, 1, 0]
    ns, ne, nv, ws, we = (x[0].tolist() for x in m.tokenize(batch_of(uni_rows()[1:2], BV)))
    p = UNI[1].encode()
    assert [p[a:e].decode() for a, e in zip(ns, ne) if e > a] == ['12', '5', '345'] and [p[a:e].decode() for a, e in zip(ws, we) if e > a][:9] == ['Tom', 'has', '12', 'apples', 'and', '5', '€', '—', 'buys']
    # the reader reads positions up to 208 bytes, and one position per byte
    with torch.no_grad():
        X, mk_ = m.reader(b)
    assert X.shape[:2] == (len(mod_rows), T) and int(mk_[0].sum()) == len(UNI[0].encode())
    ls = steps(m, [b], 3)
    m.eval()
    b3 = batch_of(uni_rows(), BV)
    with torch.no_grad():
        out = m.generate(b3)
    assert len(out) == 3 and all(isinstance(x, str) for x in out)
    # tape entries / gold GEN targets in bytes: a non-ASCII answer
    assert m.cell_ids('é1')[:4] == BV.encode('1é') + [EOS] and m.cell_ids('x' * 25)[-1] == EOS and len(m.cell_ids('é' * 20)) == len(m.cell_ids('1')), 'operand cells count bytes'
    m.train_golds(b['rows'])
    x, ids, msk = m.read_texts(['add 1 2 = 3', 'é' * 40], 'cpu', 20)
    assert int(msk[1].sum()) == 20 and ids[1, :2].tolist() == BV.encode('é'), 'tape entries are cut at LE bytes'
    print('ok bytes in B3: vocab check, 269-id tables, byte places and spans, batch of non-ASCII rows trains (losses', [round(x, 2) for x in ls], ') and generates')


class FakeTok:
    """A whitespace tokenizer in Gemma's style (a token carries its leading space) with char offsets."""
    pad_token_id = 0

    def __call__(self, text, return_offsets_mapping=False):
        ms = list(re.finditer(r' ?\S+', text))
        return {'input_ids': [1 + zlib.crc32(m.group().encode()) % 500 for m in ms], 'offset_mapping': [m.span() for m in ms]}


class FakeLM(nn.Module):
    def __init__(self):
        super().__init__()
        self.emb = nn.Embedding(501, 768)

    def forward(self, input_ids, attention_mask):
        class O: pass
        o = O(); o.last_hidden_state = self.emb(input_ids)
        return o


def fake_eg(by_bytes):
    torch.manual_seed(5)
    eg = FrozenEG(by_bytes=by_bytes)
    eg.tok, eg.m = FakeTok(), FakeLM().eval()
    return eg


def test_eg_alignment():
    dev = torch.device('cpu')
    ch, by = fake_eg(False), fake_eg(True)
    by.m.load_state_dict(ch.m.state_dict())
    asc = ['Tom has 12 apples and 345 more.', 'Echo: sune Give only the answer.', 'a  b']
    for p in asc:
        assert np.array_equal(ch.align(p)[1], by.align(p)[1]) and np.array_equal(ch.align(p)[0], by.align(p)[0]), p
    Hc, pc = ch.encode(asc, 40, dev)
    Hb, pb = by.encode(asc, 40, dev)
    assert torch.equal(Hc, Hb) and torch.equal(pc, pb), 'ASCII prompts give exactly the char path'
    p = 'Écho: café 日本'
    c2t_c, c2t_b = ch.align(p)[1], by.align(p)[1]
    assert len(c2t_c) == len(p) and len(c2t_b) == len(p.encode())
    w = [len(c.encode()) for c in p]
    assert np.array_equal(np.repeat(c2t_c, w), c2t_b), 'each byte takes its character\'s token'
    i = p.index('é')
    j = len(p[:i].encode())
    assert c2t_b[j] == c2t_b[j + 1] == c2t_c[i] and w[i] == 2
    k = len(p[:p.index('日')].encode())
    assert len(set(c2t_b[k:k + 6])) == 1, 'the three bytes of each CJK char (and the word they form) share a token'
    H, _ = by.encode([p], 40, dev)
    assert torch.equal(H[0, j], H[0, j + 1]) and not torch.equal(H[0, j], H[0, 0])
    # a model with bytes + eg_embed (+ tok_think) trains on non-ASCII text through this alignment
    b = batch_of(uni_rows() + rows(5), BV)
    m = mk(BV, eg=by, eg_embed=True, any_round=True, gap_p=0.25)
    steps(m, [b], 2)
    m2 = mk(BV, eg=fake_eg(True), eg_embed=True, tok_think=True, no_slots=True, no_place=True)
    steps(m2, [b], 2)
    print('ok Gemma alignment in bytes: ASCII = char path (H, pooled equal), a multi-byte char\'s bytes share one token, B3 trains with bytes + eg_embed (+ tok_think, no_slots, no_place)')


# ---- the switch together, the checkpoint, configs, caps ----
def test_all_on_and_checkpoint():
    from custom_io import train
    with tempfile.TemporaryDirectory() as d:
        data = os.path.join(d, 'data')
        os.makedirs(os.path.join(data, 'dev'))
        rs = rows(16)
        for name, rr in (('train.jsonl', rs), ('dev/in_dist.jsonl', rs[:4])):
            with open(os.path.join(data, name), 'w') as f:
                f.write('\n'.join(json.dumps(r) for r in rr) + '\n')
        for cfgx, vocab_kind in (({'bytes': True, 'no_slots': True, 'no_place': True}, 'bytes'), ({}, 'chars')):
            out = os.path.join(d, 'out_' + vocab_kind)
            cfg = {**CFG, **cfgx, 'any_round': True, 'gap_p': 0.25}
            res = train.main(['--model', 'b3', '--cfg', json.dumps(cfg), '--data', data, '--steps', '1', '--batch', '4', '--log-every', '1', '--out', out, '--device', 'cpu'])
            ck = torch.load(os.path.join(out, 'checkpoint.pt'))
            assert ck['vocab'] == vocab_kind and ck['cfg'] == cfg and (ck['chars'] == '' if vocab_kind == 'bytes' else len(ck['chars']) == 95)
            m = load_model(os.path.join(out, 'checkpoint.pt'))
            assert m.is_bytes == (vocab_kind == 'bytes') and len(m.vocab) == (269 if vocab_kind == 'bytes' else 108) and m.no_slots == bool(cfgx.get('no_slots'))
            assert res['n_params'] == m.n_params()
    from custom_io.g8a import caps, configs as C
    r = dict(prompt='Écho café 12', answer='é', id='x')
    assert caps.measure(r, progs=False)['max_prompt'] == 12 and caps.measure(r, progs=False, by_bytes=True)['max_prompt'] == 14
    assert caps.measure(r, progs=False, by_bytes=True)['n_reg'] == 3
    base = C.b3_cfg('3M')
    base_n = C.n('b3', base)
    print(f'  3M B3 (chars, 108 ids): {base_n:,} trained')
    rep = {}
    for name, extra in (('bytes', dict(bytes=True)), ('no_place', dict(no_place=True)), ('no_slots', dict(no_slots=True)),
                        ('bytes+no_place+no_slots', dict(bytes=True, no_place=True, no_slots=True))):
        n = C.n('b3', dict(base, **extra))
        rep[name] = n
        print(f'  3M B3 + {name}: {n:,} trained ({n - base_n:+,})')
    assert rep['no_place'] == base_n
    assert rep['bytes'] - base_n == (269 - 108) * base['d'] * 1 + (269 - 108), (rep['bytes'] - base_n)           # tok table rows + the output bias
    assert rep['no_slots'] - base_n == -(N_NUM + 3) * base['d']
    print('ok train.py picks the vocab from cfg, the checkpoint records it and load_model rebuilds it; caps measure bytes; configs count with the right vocab')


def main():
    torch.set_num_threads(1)        # tiny models: one thread is far faster than four fighting for the cores
    legacy_widths.apply()       # uncapped tests: the 16-row place table needs T1SDR's 11 cells / 40-char entries (see legacy_widths)
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            print('==', name)
            fn()
    print('ALL OK')


if __name__ == '__main__':
    main()
