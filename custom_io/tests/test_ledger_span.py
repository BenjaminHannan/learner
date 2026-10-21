"""python3 -m custom_io.tests.test_ledger_span   (CPU, about 2 minutes; the loss fingerprint needs the skills data at data.DEFAULT_DATA / $CUSTOM_IO_DATA)
B1 student build (design/B1-students.md section 2): (1) span=False is exactly B2 (fingerprints taken at the commit before span existed); (2) span=True adds only
q_wend (last), exact B2-M size; (3) span loss on a tiny hand-made English batch; (4) decode never crosses span_max or the current row's word count, donor-style
talk works; (5) GEN targets are 8 chars whatever data.set_max_ans says, even when it is called before the first ledger import.
english.py (the ENGLISH implementer's module) is imported lazily by the ledger; until it exists this file installs a local stand-in for its three helpers."""
import hashlib, os, re, subprocess, sys, time, unicodedata
import numpy as np
import torch
from custom_io import data as D
from custom_io.data import DEFAULT_DATA, CharVocab, collate, word_spans
from custom_io.models.ledger import GEN_MAX, W_MAX, Ledger
from custom_io.tests.test_ledger import M_CFG, SMALL, batch_of, train_rows, vocab

try:
    import custom_io.english as _english        # noqa: F401  (the real one)
except ImportError:
    import types

    def _en_norm(s):
        s = unicodedata.normalize('NFC', s).lower().replace('’', "'").replace('‘', "'").strip()
        return re.sub(r'[.!?,;:]+$', '', re.sub(r'\s+', ' ', s)).strip()

    def _word_runs(prompt, target_norm, span_max=12, w_max=64):
        ws = word_spans(prompt)[:w_max]
        return [(s, e) for s in range(len(ws)) for e in range(s, min(s + span_max, len(ws)))
                if _en_norm(prompt[ws[s][0]:ws[e][1]]) == target_norm]
    sys.modules['custom_io.english'] = types.SimpleNamespace(en_norm=_en_norm, word_runs=_word_runs)

M_B2_SPAN, GOLD_TRAIN_BYTES = 10914681, 111878160
# fingerprints of the unmodified B2 (copy=True) code at HEAD 0265b8bc5, before span existed: torch.manual_seed(0); Ledger(vocab, copy=True, **cfg); loss on train_rows(48, 4)
GOLD = {'SMALL': dict(params=95705, keys=75, keyhash='637008fe524aa00f27f705b5509eb1ad1dcc1f40', wabs=2043.7759813, wsq=525.255862, loss=10.74450874,
                      aux=dict(prog=6.41172981, op_acc=0.0, mode=1.10034311, ans=0.60510999, word=0.86312562, gen=1.76420069, copy_share=0.50718188)),
        'M': dict(params=10890041, keys=123, keyhash='0815e1db441f3aa12d893113dc316a07873fd42c', wabs=124022.9158062, wsq=9908.6135437, loss=10.79519558,
                  aux=dict(prog=6.32143354, op_acc=0.0, mode=1.15610969, ans=0.64214128, word=0.85871714, gen=1.81679428, copy_share=0.57271063))}


def seeded(cfg, seed=0, v=None, **kw):
    torch.manual_seed(seed)
    return Ledger(v or vocab(), **cfg, **kw)


def row(i, prompt, answer, tag='sp'):
    return dict(id=f'{tag}_{i}', prompt=prompt, answer=answer, accepted=[answer], family='english', level=0, steps=[])


def test_span_false_is_b2():
    """span=False (copy=True): same modules, keys, param count, seeded init, loss and aux as B2 before span existed; state() is the old 6-tuple; no q_wend."""
    v, rows = vocab(), train_rows(48, 4)
    data_ok = os.path.exists(os.path.join(DEFAULT_DATA, 'train.jsonl')) and os.path.getsize(os.path.join(DEFAULT_DATA, 'train.jsonl')) == GOLD_TRAIN_BYTES
    for name, cfg in (('SMALL', SMALL), ('M', M_CFG)):
        gd, m = GOLD[name], seeded(cfg, 0, v, copy=True)
        sd = m.state_dict()
        assert m.n_params() == gd['params'] and len(sd) == gd['keys'], (name, m.n_params(), len(sd))
        assert hashlib.sha1(repr([(k, tuple(t.shape)) for k, t in sd.items()]).encode()).hexdigest() == gd['keyhash'], name
        assert abs(sum(float(t.double().abs().sum()) for t in sd.values()) / gd['wabs'] - 1) < 1e-8, name
        assert abs(sum(float((t.double() ** 2).sum()) for t in sd.values()) / gd['wsq'] - 1) < 1e-8, name
        assert not m.span and not hasattr(m, 'q_wend') and not any(k.startswith('q_wend') for k in sd)
        b = batch_of(rows, v)
        assert len(m.state(b)) == 6 and 'lwend' not in m.run(b)
        if data_ok:
            loss, aux = m.loss(b)
            assert abs(loss.item() - gd['loss']) < 1e-4, (name, loss.item(), gd['loss'])
            assert all(abs(float(aux[k]) - x) < 1e-4 for k, x in gd['aux'].items()) and set(aux) == set(gd['aux']), (name, aux)
        print(f'  {name}: {m.n_params():,} params, {len(sd)} keys, init + loss {"match" if data_ok else "match (loss not checked: train.jsonl differs)"} the pre-span B2')
    print('ok span_false_is_b2')


def test_span_true_size_and_init():
    """span=True adds exactly q_wend (last key), shares every other initial weight at the same seed; B2-M with span has 10,914,681 params."""
    v = vocab()
    assert len(v) == 108 and len(CharVocab.build([])) == 108
    for copy in (True, False):
        a, b = seeded(SMALL, 5, v, copy=copy), seeded(SMALL, 5, v, copy=copy, span=True)
        sa, sb = a.state_dict(), b.state_dict()
        assert list(sb)[:len(sa)] == list(sa) and list(sb)[len(sa):] == ['q_wend.weight', 'q_wend.bias'], list(sb)[len(sa):]
        assert all(torch.equal(sa[k], sb[k]) for k in sa), 'a shared weight differs at the same seed'
        assert abs(b.q_wend.weight.std().item() - 0.02) < 0.006 and (b.q_wend.bias == 0).all()
        assert b.n_params() - a.n_params() == 48 * 64 + 64 and b.LESIONS == a.LESIONS
    m = seeded(M_CFG, 0, CharVocab.build([]), copy=True, span=True)
    print(f'  B2-M copy+span: {m.n_params():,} params')
    assert m.n_params() == M_B2_SPAN == GOLD['M']['params'] + 384 * 64 + 64 and m.span_max == 12
    print('ok span_true_size_and_init')


def english_rows():
    """single-word, multi-word and yes/no rows with distinct questions (so one tiny model can memorise them)."""
    R = [('Anna gave a red ball to Ben. Who got the ball?', 'Ben'), ('Cara gave a blue kite to Dan. Who got the kite?', 'Dan'),
         ('The big blue bird sat on the old oak tree. Where did the bird sit?', 'the old oak tree'),
         ('A small green frog jumped into the cold pond. Where did the frog jump?', 'the cold pond'),
         ('Is the sky blue?', 'yes'), ('Is the grass purple?', 'no'), ('Is fire cold?', 'No'), ('Is the sun hot?', 'Yes'),
         ('Mia ate the sweet red apple. What did Mia eat?', 'the sweet red apple'), ('Leo likes tea. Who likes tea?', 'Leo')]
    return [row(i, p, a) for i, (p, a) in enumerate(R)]


def test_span_loss_on_english():
    """gold modes (single word and multi-word = 1, yes/no = 2); loss finite, backward reaches q_wend, loss falls and the tiny model prints the taught strings."""
    v, rows = CharVocab.build([]), english_rows()
    m = seeded(SMALL, 0, v, copy=True, span=True)
    g = m.gold(rows, 'cpu')
    assert g['mode'].tolist() == [1, 1, 1, 1, 2, 2, 2, 2, 1, 1], g['mode'].tolist()
    assert g['span'].shape == (10, W_MAX, W_MAX) and g['span'][4:8].sum() == 0 and (g['span'].flatten(1).sum(1) > 0).tolist() == [x == 1 for x in g['mode'].tolist()]
    ws = word_spans(rows[2]['prompt'])
    txt = sorted(rows[2]['prompt'][ws[s][0]:ws[e][1]] for s, e in g['span'][2].nonzero().tolist())
    assert txt == ['the old oak tree', 'the old oak tree.'], txt          # the trailing '.' token is a second run with the same en_norm
    assert v.decode(g['gen'][4].tolist()[::-1][-4:][::-1]) != '' and g['gen'][4].tolist()[:4] == [v.stoi['s'], v.stoi['e'], v.stoi['y'], D.EOS]
    b = batch_of(rows, v)
    loss, aux = m.loss(b)
    assert torch.isfinite(loss) and all(torch.isfinite(x) for x in aux.values())
    loss.backward()
    assert m.q_wend.weight.grad.abs().sum() > 0 and m.q_word.weight.grad.abs().sum() > 0
    m.zero_grad()
    opt = torch.optim.AdamW(m.parameters(), lr=3e-3, weight_decay=0.0)
    first = aux['word'].item()
    for step in range(500):
        loss, aux = m.loss(b)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad()
        if loss.item() < 0.05:
            break
    print(f'  {step + 1} steps: loss {loss.item():.3f}, span loss {first:.3f} -> {aux["word"].item():.3f}')
    assert aux['word'].item() < 0.2 * first and loss.item() < 0.5, (first, aux)
    m.eval()
    with torch.no_grad():
        out = m.talk(m.state(b), b)
    want = [r['answer'] for r in rows]
    en = sys.modules['custom_io.english'].en_norm            # 'Ben.' and 'Ben' are both targets (same en_norm), the scorer treats them alike
    assert [en(o) for o in out] == [en(w) for w in want], (out, want)
    print('ok span_loss_on_english')


def brute(ls, le, nw, span_max):
    best, arg = -1e30, None
    for s in range(nw):
        for e in range(s, min(s + span_max, nw)):
            if ls[s] + le[e] > best:
                best, arg = ls[s] + le[e], (s, e)
    return arg


def test_decode_bounds():
    """span_pick = brute force over s <= e < s + span_max, e < the row's word count (random logits); talk never prints more than span_max words or leaves the current row;
    donor-style talk(state(other batch), batch) copies from the CURRENT rows; return_modes leaves the output as it was."""
    v, rows = vocab(), train_rows(64, 11)
    rng = np.random.RandomState(0)
    for span_max in (1, 3, 12):
        m = seeded(SMALL, 1, v, copy=True, span=True).eval()
        m.span_max = span_max
        nw = torch.tensor([min(len(word_spans(r['prompt'])), W_MAX) for r in rows])
        ls0 = torch.from_numpy(rng.randn(64, W_MAX) * 3).float()
        le0 = torch.from_numpy(rng.randn(64, W_MAX) * 3).float()
        s_, e_, ok = m.span_pick(ls0, le0, nw)
        lsm, lem = ls0.log_softmax(-1).numpy(), le0.log_softmax(-1).numpy()
        for i in range(64):
            assert (s_[i].item(), e_[i].item()) == brute(lsm[i], lem[i], int(nw[i]), span_max), (span_max, i)
            assert s_[i] <= e_[i] < min(s_[i] + span_max, nw[i] + 1) and e_[i] < nw[i]
        # end pointer peaked far past the span window / the word count: the pair stays inside both
        ls1, le1 = torch.full((64, W_MAX), -5.), torch.full((64, W_MAX), -5.)
        ls1[:, 0], le1[:, W_MAX - 1] = 5, 5
        s_, e_, ok = m.span_pick(ls1, le1, nw)
        assert (s_ == 0).all() and (e_ < span_max).all() and (e_ < nw).all()
        assert (m.span_pick(ls0, le0, torch.zeros(64, dtype=torch.long))[2] == 0).all()                # no words: no valid pair
        b, don = batch_of(rows[:32], v), batch_of(rows[32:], v)
        with torch.no_grad():
            force = lambda st: tuple(torch.tensor([0., 5, 0]).expand(32, -1) if i == 3 else x for i, x in enumerate(st))       # every row mode 1
            st = force(m.state(don))
            assert len(st) == 7
            out, modes = m.talk(st, b, return_modes=True)
            assert out == m.talk(st, b) and set(modes) <= {1, 2} and 1 in modes
            for o, mo, r in zip(out, modes, rows[:32]):
                if mo == 1:
                    sp = word_spans(r['prompt'])[:W_MAX]
                    hit = [(s, e) for s in range(len(sp)) for e in range(s, min(s + span_max, len(sp))) if r['prompt'][sp[s][0]:sp[e][1]] == o]
                    assert hit, (o, r['prompt'])
            nat = m.talk(m.state(b), b)
            assert len(nat) == 32 and all(isinstance(x, str) for x in nat)
            for les in (None, 'zero_state', 'shuffle_state', 'nocopy', 'loops:0'):
                assert len(m.generate(b, lesion=les)) == 32, les
    print('ok decode_bounds')


def test_donor_eval_works():
    from custom_io.evalx import donor_eval, evaluate
    v, rows = vocab(), train_rows(48, 3)
    m = seeded(SMALL, 2, v, copy=True, span=True).eval()
    d = donor_eval(m, rows, 16, 'cpu')
    assert 'exact' in d and 'donor_match' in d and evaluate(m, rows, 16, 'cpu')['n'] == 48
    print('ok donor_eval_works')


_SUB = """
import sys
from custom_io import data
data.set_max_ans(32)
assert 'custom_io.models.ledger' not in sys.modules
from custom_io.models.ledger import Ledger
from custom_io.data import CharVocab
v = CharVocab.build([])
r = dict(id='gm_1', prompt='What is the word?', answer='abcdefghijklmnopqrst', accepted=['abcdefghijklmnopqrst'], family='x', level=0, steps=[])
for span in (False, True):
    m = Ledger(v, d=32, n_heads=2, reader_layers=1, blocks=1, n_loops=2, mlp=2.0, span=span)
    g = m.gold([r], 'cpu')
    assert g['mode'].tolist() == [2] and (g['gen'][0] >= 0).sum().item() == 9 and g['gen'][0][8].item() == 2 and g['gen'][0][9 - 1].item() == 2, (span, g['gen'])
    assert v.decode(g['gen'][0][:8].tolist()[::-1]) == 'abcdefgh'
print('ok')
"""


def test_gen_targets_ignore_max_ans():
    """set_max_ans(32) before the first ledger import: gold() on a 20-char non-span answer still gives 8 chars + EOS (also with span)."""
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    r = subprocess.run([sys.executable, '-c', _SUB], cwd=here, capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=here))
    assert r.returncode == 0 and r.stdout.strip() == 'ok', r.stderr[-1500:]
    v, m = CharVocab.build([]), seeded(SMALL, 0, CharVocab.build([]), span=True)
    rw = row(0, 'What is the word?', 'abcdefghijklmnopqrst', 'gm')
    try:
        D.set_max_ans(32)
        g = m.gold([rw], 'cpu')['gen'][0]
        assert (g >= 0).sum().item() == GEN_MAX + 1 and v.decode(g[:GEN_MAX].tolist()[::-1]) == 'abcdefgh'
        assert collate([D.Dataset([rw], v)[0]])['ans_ids'].shape[1] == 33
    finally:
        D.set_max_ans(8)
    assert collate([D.Dataset([row(1, 'Hi there.', 'abc')], v)[0]])['ans_ids'].shape[1] == 9
    print('ok gen_targets_ignore_max_ans')


if __name__ == '__main__':
    torch.set_num_threads(min(torch.get_num_threads(), 2))
    t0 = time.time()
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            t = time.time()
            fn()
            print(f'  [{name} {time.time() - t:.0f}s]')
    print(f'all ok ({time.time() - t0:.0f}s)')
