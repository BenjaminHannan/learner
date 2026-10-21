"""python3 -m custom_io.tests.test_plain_tf_maxans   (CPU, about 1 minute; the loss fingerprint needs the skills data at data.DEFAULT_DATA / $CUSTOM_IO_DATA)
B1 student build (design/B1-students.md section 3): PlainTF `max_ans` (default 8 = exactly the old model): (1) max_ans=8 equals the fingerprints taken before it existed;
(2) max_ans=32 has a 243-position table and exactly 10,782,336 params at M size; (3) it memorises and emits a 20+ char answer; (4) train.py --max-ans."""
import hashlib, json, os, tempfile, time
import torch
from custom_io import data as D
from custom_io.data import DEFAULT_DATA, CharVocab, Dataset, collate
from custom_io.models.plain_tf import PlainTF
from custom_io.models.plain_tf_steps import PlainTFSteps
from custom_io.tests.test_ledger import batch_of, train_rows, vocab

S_CFG, M_CFG = dict(d_model=256, n_layers=4, n_heads=4), dict(d_model=384, n_layers=6, n_heads=6)
M_MAX32, GOLD_TRAIN_BYTES = 10782336, 111878160
# fingerprints of the unmodified PlainTF at HEAD 0265b8bc5: torch.manual_seed(0); PlainTF(vocab, **cfg); loss on train_rows(48, 4)
GOLD = {'S': dict(params=3244544, keys=52, keyhash='4974964883a75f67a39d3b7442ff8490335cd19a', wabs=40338.8746798, wsq=3137.6558829, loss=4.78117037),
        'M': dict(params=10775040, keys=76, keyhash='a6187f9ef6ef683bb0678b9e6c4ee2ce5b514fbf', wabs=126213.4857849, wsq=7666.7548953, loss=4.81447697)}


def seeded(cfg, seed=0, v=None, **kw):
    torch.manual_seed(seed)
    return PlainTF(v or vocab(), **cfg, **kw)


def test_max_ans_8_is_old_model():
    v, rows = vocab(), train_rows(48, 4)
    data_ok = os.path.exists(os.path.join(DEFAULT_DATA, 'train.jsonl')) and os.path.getsize(os.path.join(DEFAULT_DATA, 'train.jsonl')) == GOLD_TRAIN_BYTES
    for name, cfg in (('S', S_CFG), ('M', M_CFG)):
        gd = GOLD[name]
        for kw in (dict(), dict(max_ans=8)):
            m = seeded(cfg, 0, v, **kw)
            sd = m.state_dict()
            assert m.n_params() == gd['params'] and len(sd) == gd['keys'] and m.pos.num_embeddings == 224, (name, m.n_params())
            assert hashlib.sha1(repr([(k, tuple(t.shape)) for k, t in sd.items()]).encode()).hexdigest() == gd['keyhash'], name
            assert abs(sum(float(t.double().abs().sum()) for t in sd.values()) / gd['wabs'] - 1) < 1e-8, name
            assert abs(sum(float((t.double() ** 2).sum()) for t in sd.values()) / gd['wsq'] - 1) < 1e-8, name
            if data_ok:
                loss = m.loss(batch_of(rows, v)).item()
                assert abs(loss - gd['loss']) < 1e-4, (name, loss, gd['loss'])
        print(f'  {name}: {gd["params"]:,} params, {gd["keys"]} keys, init + loss {"match" if data_ok else "match (loss not checked: train.jsonl differs)"} the pre-max_ans model')
    assert PlainTFSteps(v, place=True).max_ans == 8 and PlainTFSteps(v).pos.num_embeddings == 288          # the steps model is untouched
    print('ok max_ans_8_is_old_model')


def test_max_ans_32_size():
    """Position table 2 + 208 + 32 + 1 = 243; every other weight starts as at max_ans 8 only up to the pos table (a different shape), so only sizes and shapes are compared."""
    v = vocab()
    assert len(v) == 108
    m = seeded(M_CFG, 0, v, max_ans=32)
    assert m.pos.num_embeddings == 243 and m.n_params() == M_MAX32 == GOLD['M']['params'] + (243 - 224) * 384, m.n_params()
    assert m.n_params() / 10914681 < 1 and abs(10914681 / m.n_params() - 1 - 0.0123) < 0.0005          # B2-M is +1.23%
    assert list(m.state_dict()) == list(seeded(M_CFG, 0, v).state_dict())
    assert seeded(S_CFG, 0, v, max_ans=9).pos.num_embeddings == 2 + 208 + 9 + 1
    print(f'  plain_tf M max_ans 32: {m.n_params():,} params')
    print('ok max_ans_32_size')


def test_batch_width_is_the_models():
    """The model pads or cuts the batch's answer columns to max_ans + 1, so a batch collated at another data.MAX_ANS still trains (loss finite)."""
    v = CharVocab.build([])
    rows = [dict(id=f'w{i}', prompt=f'Say the word number {i}.', answer='abcdefghijklmnopqrstuvwx'[:20 + i % 4], accepted=[], family='x', level=0, steps=[]) for i in range(4)]
    try:
        D.set_max_ans(32)
        b32 = collate([Dataset(rows, v)[i] for i in range(4)])
        D.set_max_ans(8)
        b8 = collate([Dataset(rows, v, strict=False)[i] for i in range(4)])
    finally:
        D.set_max_ans(8)
    assert b32['ans_ids'].shape[1] == 33 and b8['ans_ids'].shape[1] == 9
    big, small = seeded(dict(d_model=32, n_layers=1, n_heads=2), 0, v, max_ans=32), seeded(dict(d_model=32, n_layers=1, n_heads=2), 0, v)
    for m in (big, small):
        for b in (b32, b8):
            assert torch.isfinite(m.loss(b))
    assert len(big.generate(b8)) == 4 and len(small.generate(b32)) == 4
    print('ok batch_width_is_the_models')


def test_memorises_long_answer():
    """max_ans=32, answers of 20-26 chars: the loss falls and greedy decoding prints every answer exactly (the max_ans=8 model cannot)."""
    v = CharVocab.build([])
    A = ['the quick brown fox jumps', 'a very long answer indeed', 'twenty chars exactly!', 'zebras quietly vanish by', 'seven plain brown sparrows', 'mild rain falls on grass']
    rows = [dict(id=f'ml{i}', prompt=f'Question number {i}: say it.', answer=a, accepted=[a], family='x', level=0, steps=[]) for i, a in enumerate(A)]
    assert min(map(len, A)) >= 20
    try:
        D.set_max_ans(32)
        b = collate([Dataset(rows, v)[i] for i in range(len(rows))])
    finally:
        D.set_max_ans(8)
    m = seeded(dict(d_model=64, n_layers=2, n_heads=2), 0, v, max_ans=32)
    opt = torch.optim.AdamW(m.parameters(), lr=3e-3, weight_decay=0.0)
    first = m.loss(b).item()
    for step in range(400):
        loss = m.loss(b)
        loss.backward()
        opt.step(); opt.zero_grad()
        if loss.item() < 0.01:
            break
    m.eval()
    out = m.generate(b)
    print(f'  {step + 1} steps: loss {first:.2f} -> {loss.item():.4f}; {out[0]!r}')
    assert loss.item() < 0.1 * first and out == A, out
    small = seeded(dict(d_model=64, n_layers=2, n_heads=2), 0, v)
    assert all(len(o) <= 8 for o in small.eval().generate(b))
    print('ok memorises_long_answer')


def test_train_py_max_ans():
    """train.py --max-ans: refuses a model whose max_ans is smaller; 32 trains plain_tf (cfg max_ans 32) and records it; data.MAX_ANS is restored."""
    from custom_io.train import main
    tmp = tempfile.mkdtemp()
    os.makedirs(tmp + '/dev')
    rows = [dict(id=f't{i}', prompt=f'Say the word number {i}.', answer='abcdefghijklmnopqrstuvwxyz'[:i % 3 + 20], accepted=[], family='x', level=0, steps=[]) for i in range(40)]
    for f in ('train.jsonl', 'dev/in_dist.jsonl'):
        with open(os.path.join(tmp, f), 'w') as fh:
            fh.write(''.join(json.dumps(r) + '\n' for r in rows))
    base = ['--model', 'plain_tf', '--data', tmp, '--steps', '3', '--batch', '8', '--log-every', '1', '--out', tmp + '/out']
    try:
        try:
            main(base + ['--cfg', '{"d_model":32,"n_layers":1,"n_heads":2}', '--max-ans', '32'])
            raise AssertionError('--max-ans 32 accepted a model with max_ans 8')
        except SystemExit as e:
            assert 'max_ans' in str(e)
        assert D.MAX_ANS == 32                                  # set before the model was built
        r = main(base + ['--cfg', '{"d_model":32,"n_layers":1,"n_heads":2,"max_ans":32}', '--max-ans', '32'])
        assert r['steps'] == 3 and r['status'] == 'ok' and r['config']['max_ans'] == 32 and r['config']['cfg']['max_ans'] == 32
        try:
            main(base + ['--cfg', '{"d_model":32,"n_layers":1,"n_heads":2}'])          # default --max-ans 8: the strict Dataset refuses 20-char answers, as before
            raise AssertionError('default --max-ans accepted 20-char answers')
        except AssertionError as e:
            assert 'answer too long' in str(e)
        assert D.MAX_ANS == 8                                   # every main() call sets it
    finally:
        D.set_max_ans(8)
    print('ok train_py_max_ans')


if __name__ == '__main__':
    torch.set_num_threads(min(torch.get_num_threads(), 2))
    t0 = time.time()
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            t = time.time()
            fn()
            print(f'  [{name} {time.time() - t:.0f}s]')
    print(f'all ok ({time.time() - t0:.0f}s)')
