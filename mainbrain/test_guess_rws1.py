"""python3 -m mainbrain.test_guess_rws1 : tiny check of the SB-2b head input "reader_ws1" in mainbrain/guess.py
(one thread, 64 tries, 64 diary rows, 3 updates)."""
import json
import os
import time

import torch

from custom_io.models import load_model
from domain import mode
from mainbrain import common, fullrun, guess

torch.set_num_threads(1)
PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
RUN = '/mnt/project-files/main-brain/runs/sheet-s200-kf97n'
SCR = '/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/guesstest-rws1'
HERE = os.path.dirname(os.path.abspath(__file__))
RWS_C = os.path.join(HERE, 'constants-kf97n-lr3e4-guess-rws1.json')
DEF_C = os.path.join(HERE, 'constants-kf97n-lr3e4-guess.json')
SEED = 200001


def main():
    os.makedirs(SCR, exist_ok=True)
    jl = os.path.join(SCR, 'guess.jsonl')
    if os.path.exists(jl):
        os.remove(jl)
    rows = common.run_rows(RUN)
    new, diary = rows[1][:64], rows[0][:64]
    cons = json.load(open(RWS_C))
    assert cons['guess']['input'] == 'reader_ws1'
    m = load_model(PARENT)
    keys0 = list(m.state_dict().keys())
    orig = (mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day)

    # (i) Z after t=0: loops=1 vs the full default run (eval mode); hook Z is the post-update Z
    m.eval()
    with torch.no_grad():
        b = guess._batch(m, new[:16])
        g1, gf = {}, {}

        def h1(t, s):
            if t == 0:
                g1['Z'] = s['Z'].clone()

        def hf(t, s):
            if t == 0:
                gf['Z'] = s['Z'].clone()
            if t == m.n_loops - 1:
                gf['last'] = s['Z'].clone()
        m.run(b, loops=1, each=h1)
        o = m.run(b, each=hf)
        assert torch.allclose(g1['Z'], gf['Z'], atol=1e-6), float((g1['Z'] - gf['Z']).abs().max())
        assert torch.equal(gf['last'][:, 8:], o['R']), 'hook Z at last t is not the post-update Z'
        assert torch.allclose(m.q_s(m.ln_z(gf['last'][:, 1])), o['qn'], atol=1e-6)
    print('(i) Z after t=0: loops=1 == full run, max diff %.2e; hook Z at last t matches out["R"] (post-update)' %
          float((g1['Z'] - gf['Z']).abs().max()))

    # (ii) widths
    f = guess.feats_of(m, new[:16], False, 'reader_ws1')
    assert f.shape == (16, 2304), f.shape
    fd = guess.feats_of(m, new[:16], False)
    assert fd.shape == (16, 256) and torch.equal(fd, guess.zf_of(m, new[:16], False))
    print('(ii) reader_ws1 width', tuple(f.shape), '; default width', tuple(fd.shape), '(== zf_of)')

    # gradients reach reader and thinker through both parts
    m.train()
    m.zero_grad()
    ff = guess.feats_of(m, new[:8], True, 'reader_ws1')
    for name, sl in (('reader mean', ff[:, :256]), ('ctrl rows', ff[:, 256:])):
        m.zero_grad()
        sl.sum().backward(retain_graph=True)
        gr = sum(float(p.grad.abs().sum()) for p in m.reader.parameters() if p.grad is not None)
        gt = sum(float(p.grad.abs().sum()) for p in m.core.parameters() if p.grad is not None)
        print('    grad via %s: reader %.3e, thinker %.3e' % (name, gr, gt))
        if name == 'reader mean':
            assert gr > 0
        else:
            assert gr > 0 and gt > 0
    m.zero_grad()
    m.eval()

    # (iii) 3-update night with the new constants
    def night(c_path, upd=3):
        mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day = orig
        fullrun.install(c_path, out=SCR, seed=SEED)
        mm = load_model(PARENT)
        t = time.time()
        mode.train_night(mm, new, diary, upd, json.load(open(c_path)), SEED)
        G = next(c.cell_contents for c in mode.save_ckpt.__closure__ if isinstance(c.cell_contents, guess.Guess))
        return mm, G, time.time() - t

    m, G, t3 = night(RWS_C)
    assert G.inp == 'reader_ws1' and G.head.weight.shape == (1, 2304)
    head0 = guess.Guess(None, 1, 1, SEED)
    head0.make_head(2304)
    assert list(m.state_dict().keys()) == keys0, 'state_dict keys changed'
    assert not torch.equal(G.head.weight, head0.head.weight), 'head did not move'
    print('(iii) night ran in %.1fs; head moved |dW|=%.5f; state_dict keys unchanged (%d)' %
          (t3, float((G.head.weight - head0.head.weight).norm()), len(keys0)))
    lines = [json.loads(l) for l in open(jl)]
    assert len(lines) == 1 and lines[0]['input'] == 'reader_ws1' and len(lines[0]['p']) == 64 and all(0 < p < 1 for p in lines[0]['p'])
    ck = torch.load(PARENT, map_location='cpu')
    path = os.path.join(SCR, 'night_1', 'checkpoint.pt')
    mode.save_ckpt(ck, m, path)
    hs = torch.load(os.path.join(SCR, 'night_1', 'guess.pt'))
    assert set(hs) == {'weight', 'bias'} and hs['weight'].shape == (1, 2304)
    print('    guess.jsonl input=reader_ws1, 64 p in (0,1); guess.pt written (weight %s)' % (tuple(hs['weight'].shape),))

    # (iv) default input
    os.remove(jl)
    md, Gd, _ = night(DEF_C)
    assert Gd.inp == 'ctrl1' and Gd.head.weight.shape == (1, 256)
    assert json.loads(open(jl).readline())['input'] == 'ctrl1'
    print('(iv) default input: width 256, night ran, jsonl input=ctrl1')

    # timing: per-update = (t5 - t1) / 4
    def per_update(inp):
        mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day = orig
        mm = load_model(PARENT)
        guess.install(SCR, 1.0, 1e-3, SEED, inp)
        ts = []
        for u in (1, 5):
            t = time.time()
            mode.train_night(mm, new, diary, u, dict(cons), SEED)
            ts.append(time.time() - t)
        return (ts[1] - ts[0]) / 4
    tr, td = per_update('reader_ws1'), per_update('ctrl1')
    print('per-update: reader_ws1 %.2fs, default ctrl1 %.2fs' % (tr, td))
    mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day = orig
    print('ALL OK')


if __name__ == '__main__':
    main()
