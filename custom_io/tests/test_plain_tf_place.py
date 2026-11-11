"""python3 -m custom_io.tests.test_plain_tf_place   (CPU, about 30 s)

The place=True option of plain_tf / plain_tf_steps: the CharReader's place codes as one extra embedding table added at
the real prompt chars (BOS, SEP, answer/step positions and padding get no place term). Synthetic rows only."""
import contextlib, io, json, os, random, tempfile, time
import torch
from custom_io.data import BOS, SEP, CharVocab, Dataset, collate
from custom_io.evalx import _pad_prompt
from custom_io.models import build, load_model
from custom_io.models.plain_tf import PlainTF
from custom_io.models.plain_tf_steps import PlainTFSteps
from custom_io.models.reader import N_PLACE, PLACE_NONE, CharReader
from custom_io import train

CLASSES = {'plain_tf': PlainTF, 'plain_tf_steps': PlainTFSteps}
SMALL = dict(d_model=32, n_layers=2, n_heads=2)


def make_rows(n, seed=0):
    """Rows in the dataset format: arith_bare / var_chain / chain_ops with steps, plus one 'add 47 and 5'."""
    rng, rows = random.Random(seed), []
    for i in range(n):
        a, b, c = rng.randint(20, 99), rng.randint(1, 19), rng.randint(2, 9)
        k = i % 3
        if k == 0:
            st, p, f = [f'{a} - {b} = {a - b}'], f'Subtract {b} from {a}. State the result only.', 'arith_bare'
        elif k == 1:
            st, p, f = [f'p = {a} * {c} = {a * c}', f'n = {a * c} - {b} = {a * c - b}'], f'Facts: q = {a}. p = q * {c}. n = p - {b}. Question: What is n?', 'var_chain'
        else:
            st, p, f = [f'{a} + {c} = {a + c}'], f'Al has {a} nuts. Then Al gets {c} more. How many nuts does Al have?', 'chain_ops'
        ans = st[-1].split()[-1]
        rows.append(dict(id=f'r{i}', prompt=p, answer=ans, accepted=[ans], family=f, level=1, variant='v', steps=st))
    rows.append(dict(id='add', prompt='add 47 and 5', answer='52', accepted=['52'], family='arith_bare', level=1, variant='v', steps=['47 + 5 = 52']))
    return rows


ROWS = make_rows(11)                        # 12 rows: the last one is 'add 47 and 5', the shortest prompt
V = CharVocab.build(ROWS)                   # every printable ASCII char + 13 specials = 108 ids, like the real vocab


def batch_of(rows):
    ds = Dataset(rows, V, strict=False)
    return collate([ds[i] for i in range(len(rows))])


def seeded(name, **cfg):
    torch.manual_seed(3)
    return build(name, V, **cfg)


def test_param_counts():
    assert len(V) == 108
    for name, n in (('plain_tf', 3_244_544), ('plain_tf_steps', 3_260_928)):
        off, on = seeded(name), seeded(name, place=True)
        assert off.n_params() == seeded(name, place=False).n_params() == n, (name, off.n_params())
        assert on.n_params() == n + N_PLACE * 256 == n + 4096, (name, on.n_params())
        assert on.place.weight.shape == (N_PLACE, 256)
        ko, kn = list(off.state_dict()), list(on.state_dict())
        assert 'place.weight' not in ko and kn == ko + ['place.weight'], 'place table must be the last state_dict key'
        assert not off.has_place and on.has_place
        # the existing weights keep their seeded init when the place table is added
        so, sn = off.state_dict(), on.state_dict()
        assert all(torch.equal(so[k], sn[k]) for k in ko), 'place=True moved another weight\'s init'
        # an old (no place) checkpoint still loads into a place=False model
        seeded(name).load_state_dict(so)
        print(name, 'params', off.n_params(), '->', on.n_params())
    # cfg dict path used by --cfg: the exact example from the task
    m = build('plain_tf', V, **json.loads('{"d_model":256,"n_layers":4,"n_heads":4,"place":true}'))
    assert m.n_params() == 3_244_544 + 4096


def test_place_ids():
    b = batch_of(ROWS)
    pm = b['prompt_mask']
    lens = pm.sum(1)
    assert b['rows'][-1]['prompt'] == 'add 47 and 5' and int(lens[-1]) == 12 and int(lens.max()) > 30
    for name, cls in CLASSES.items():
        m = cls(V, **SMALL, place=True)
        W = pm.shape[1] + 2 + 80
        pl = m.place_seq(b, W)
        assert pl.shape == (len(ROWS), W) and pl.dtype == torch.long
        # 'add 47 and 5': sequence positions are prompt index + 1 (BOS at 0), SEP at 13
        r = pl[-1]
        assert r[0] == -1 and r[13] == -1 and (r[14:] == -1).all(), 'BOS, SEP, answer slots and padding carry no place term'
        assert r[1:4].tolist() == [2, 1, 0]                                         # 'add'
        assert r[5:7].tolist() == [1, 0]                                            # '47'
        assert r[8:11].tolist() == [2, 1, 0]                                        # 'and'
        assert r[12:13].tolist() == [0]                                             # '5'
        assert [int(r[i]) for i in (4, 7, 11)] == [PLACE_NONE] * 3                  # the spaces
        # every row: -1 outside 1..len, a valid place id inside, and the same ids CharReader gives
        ref = CharReader(len(V), 8).places(b)
        for i in range(len(ROWS)):
            n = int(lens[i])
            assert pl[i, 0] == -1 and (pl[i, 1 + n:] == -1).all()
            assert torch.equal(pl[i, 1:1 + n], ref[i, :n]) and ((pl[i, 1:1 + n] >= 0) & (pl[i, 1:1 + n] < N_PLACE)).all()
        # the sequence the model reads has the same layout (SEP at 1 + len, BOS at 0)
        seq, ls = m._build(b, False)
        assert seq[-1, 0] == BOS and seq[-1, 13] == SEP and ls[-1] == 12
        # only the prompt positions feel the table: loops=0 gives ln_f(tok + pos [+ place]) per position
        pl = m.place_seq(b, seq.shape[1])
        ids = seq
        with torch.no_grad():
            h0, h1 = m.hidden(ids, 0), m.hidden(ids, 0, pl)
        same, hit = (h0 - h1).abs().amax(-1) == 0, pl >= 0
        assert same[~hit].all() and not same[hit].any(), 'place term must be on at prompt chars and off elsewhere'
        # no place table -> place_seq is None and nothing is added
        assert cls(V, **SMALL).place_seq(b, W) is None
    print('place ids ok')


def test_loss_backward():
    b = batch_of(ROWS)
    for name, cls in CLASSES.items():
        torch.manual_seed(1)
        m = cls(V, **SMALL, place=True)
        l = m.loss(b)
        assert l.ndim == 0 and torch.isfinite(l), (name, l)
        l.backward()
        g = m.place.weight.grad
        assert g is not None and torch.isfinite(g).all() and g.abs().sum() > 0
        assert g[:4].abs().sum(1).gt(0).all() and g[PLACE_NONE].abs().sum() > 0     # units/tens/hundreds/..., and spaces
        assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in m.parameters())
        # the term changes the function: same seed without place gives a different loss
        torch.manual_seed(1)
        assert float(cls(V, **SMALL).loss(b).detach()) != float(l.detach())
        print(name, 'loss', round(float(l.detach()), 4))


def test_generate():
    b = batch_of(ROWS)
    for name, cls in CLASSES.items():
        torch.manual_seed(2)
        m = cls(V, **SMALL, place=True).eval()
        for lesion in ([None, 'loops:1', 'loops:3'] + (['calc'] if name == 'plain_tf_steps' else [])):
            out = m.generate(b, lesion)
            assert len(out) == len(ROWS) and all(isinstance(o, str) for o in out), (name, lesion, out)
        solo = [m.generate(batch_of([r]))[0] for r in ROWS]            # batched == single row (padding is invisible)
        assert solo == m.generate(b), name
        # generate reads the place table too: the next-char logits at the last prompt position move when it is rescaled
        seq, lens = m._build(b, False)
        r = torch.arange(len(ROWS))
        last = lambda: m.logits(m.hidden_upto(seq, seq.shape[1], None, m.place_seq(b, seq.shape[1]))[r, 1 + lens])
        before = last()
        with torch.no_grad():
            m.place.weight.mul_(50)
        assert (last() - before).abs().max() > 1e-3, name
    print('generate ok')


def test_donor_style_wider_prompts():
    b = batch_of(ROWS)
    wide = _pad_prompt(b, b['prompt_ids'].shape[1] + 17)                  # what evalx.donor_eval does
    assert wide['prompt_ids'].shape[1] == b['prompt_ids'].shape[1] + 17
    for name, cls in CLASSES.items():
        torch.manual_seed(4)
        m = cls(V, **SMALL, place=True).eval()
        pw, p0 = m.place_seq(wide, wide['prompt_ids'].shape[1] + 2 + 80), m.place_seq(b, b['prompt_ids'].shape[1] + 2 + 80)
        assert torch.equal(pw[:, :p0.shape[1]], p0) and (pw[:, p0.shape[1]:] == -1).all(), 'padding must get no place term'
        with torch.no_grad():
            lw, l0 = m.loss(wide), m.loss(b)
        assert torch.isfinite(lw) and abs(float(lw) - float(l0)) < 1e-5, name
        assert m.generate(wide) == m.generate(b), name
    # the shared lookup keeps CharReader's own behaviour: padding past the prompt is PLACE_NONE, rows are cached
    rd = CharReader(len(V), 8)
    pw = rd.places(wide)
    assert pw.shape == wide['prompt_ids'].shape and (pw[-1, 12:] == PLACE_NONE).all() and len(rd._cache) == len({r['prompt'] for r in ROWS})
    assert list(rd.state_dict()) == [f'{t}.weight' for t in ('tok', 'pos', 'place')] + ['blocks.0.ln.weight', 'blocks.0.ln.bias', 'blocks.0.conv.weight', 'blocks.0.conv.bias', 'blocks.1.ln.weight', 'blocks.1.ln.bias', 'blocks.1.conv.weight', 'blocks.1.conv.bias', 'ln.weight', 'ln.bias']
    print('wider prompts ok')


def test_save_load_and_cli():
    b = batch_of(ROWS)
    cfgs = {'plain_tf': dict(SMALL, place=True), 'plain_tf_steps': dict(SMALL, place=True)}
    with tempfile.TemporaryDirectory() as d:
        for name, cfg in cfgs.items():
            torch.manual_seed(5)
            m = build(name, V, **cfg).eval()
            with torch.no_grad():
                m.place.weight.normal_(0, 0.5)                      # so the round trip would show a lost place table
            path = os.path.join(d, name + '.pt')
            torch.save(dict(model=m.state_dict(), name=name, cfg=cfg, chars=V.chars, step=0), path)
            m2 = load_model(path)
            assert type(m2) is CLASSES[name] and m2.has_place and not m2.training
            assert all(torch.equal(x, y) for x, y in zip(m.state_dict().values(), m2.state_dict().values()))
            with torch.no_grad():
                assert abs(float(m.loss(b)) - float(m2.loss(b))) < 1e-6
            assert m2.generate(b) == m.generate(b)
        # a place=False checkpoint (no place.weight key) still loads, as a model without the table
        old = seeded('plain_tf_steps')
        torch.save(dict(model=old.state_dict(), name='plain_tf_steps', cfg={}, chars=V.chars, step=0), os.path.join(d, 'old.pt'))
        assert not load_model(os.path.join(d, 'old.pt')).has_place
        # through train.py: --cfg with place true, trains, saves, reloads
        data = os.path.join(d, 'data')
        os.makedirs(os.path.join(data, 'dev'))
        for f, rows in (('train.jsonl', make_rows(63, 1)), ('dev/in_dist.jsonl', make_rows(19, 2))):
            with open(os.path.join(data, f), 'w') as fh:
                fh.writelines(json.dumps(r) + '\n' for r in rows)
        for name in CLASSES:
            out = os.path.join(d, 'run_' + name)
            args = ['--model', name, '--cfg', json.dumps(dict(SMALL, place=True)), '--steps', '8', '--batch', '8', '--warmup', '2',
                    '--device', 'cpu', '--data', data, '--log-every', '4', '--out', out]
            with contextlib.redirect_stdout(io.StringIO()) as so:
                res = train.main(args)
            tr = [json.loads(l) for l in so.getvalue().splitlines() if l.startswith('{')]
            assert res['status'] == 'ok' and res['steps'] == 8 and tr[0]['n_params'] == res['n_params'] == build(name, V, **dict(SMALL, place=True)).n_params()
            m = load_model(os.path.join(out, 'checkpoint.pt'))
            assert m.has_place and m.n_params() == res['n_params'] and 'place.weight' in m.state_dict()
            assert len(m.generate(batch_of(ROWS[:3]))) == 3
    print('save/load + train.py cfg ok')


if __name__ == '__main__':
    t0 = time.time()
    test_param_counts(); test_place_ids(); test_loss_backward(); test_generate(); test_donor_style_wider_prompts(); test_save_load_and_cli()
    print('all ok', round(time.time() - t0, 1), 's')
