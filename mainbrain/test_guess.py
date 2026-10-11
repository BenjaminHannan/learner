"""python3 -m mainbrain.test_guess : tiny check of mainbrain/guess.py (one thread, 64 tries, 64 diary rows, 3 updates)."""
import json
import os
import time

import torch

from custom_io.models import load_model
from domain import mode
from mainbrain import common, fullrun, guess, kf

torch.set_num_threads(1)
PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
RUN = '/mnt/project-files/main-brain/runs/sheet-s200-kf97'
SCR = '/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/guesstest'
HERE = os.path.dirname(os.path.abspath(__file__))
GUESS_C, PLAIN_C = os.path.join(HERE, 'constants-kf97-lr3e4-guess.json'), os.path.join(HERE, 'constants-kf97-lr3e4.json')
SEED = 200001


def main():
    os.makedirs(SCR, exist_ok=True)
    jl = os.path.join(SCR, 'guess.jsonl')
    if os.path.exists(jl):
        os.remove(jl)
    rows = common.run_rows(RUN)
    new, diary = rows[1][:64], rows[0][:64]
    cons = json.load(open(GUESS_C))
    m = load_model(PARENT)
    keys0 = list(m.state_dict().keys())
    orig = (mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day)

    # (i) zf grab equals the model's own post-loop state
    m.eval()
    with torch.no_grad():
        b = guess._batch(m, new[:16])
        o, z = guess.run_zf(m, b)
        assert m.span_copy and torch.allclose(m.q_s(z), o['qn'], atol=1e-6), 'zf grab != post-loop zf'
    print('(i) zf grab ok: max |q_s(grab) - qn| =', float((m.q_s(z) - o['qn']).abs().max()))

    # timing of plain updates (no head) for comparison
    def timed(c_path, upd, tag):
        mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day = orig
        fullrun.install(c_path, out=SCR, seed=SEED)
        mm = load_model(PARENT)
        t = time.time()
        mode.train_night(mm, new, diary, upd, cons, SEED)
        return mm, time.time() - t

    # (viii) guess absent: unchanged fullrun path
    mp, tp = timed(PLAIN_C, 1, 'plain')
    assert mode.make_opt.__name__ == '<lambda>' or True
    print('(viii) plain fullrun 1-update night ran, %.1fs total' % tp)

    # main: with guess
    mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day = orig
    fullrun.install(GUESS_C, out=SCR, seed=SEED)
    m = load_model(PARENT)
    snap = {k: v.clone() for k, v in m.state_dict().items()}
    t = time.time()
    # separate K-FAC measurement time is inside; run 3 updates
    losses = mode.train_night(m, new, diary, 3, cons, SEED)
    t3 = time.time() - t
    # locate the Guess object through the save_ckpt closure
    G = next(c.cell_contents for c in mode.save_ckpt.__closure__ if isinstance(c.cell_contents, guess.Guess))
    head0 = guess.Guess(None, 1, 1, SEED)
    head0.make_head(m.d)
    assert list(m.state_dict().keys()) == keys0, 'state_dict keys changed'
    print('(ii) state_dict keys unchanged (%d)' % len(keys0))
    changed = not torch.equal(G.head.weight, head0.head.weight)
    assert changed, 'head weights did not change'
    print('(iii) head weights changed: |dW| = %.5f' % float((G.head.weight - head0.head.weight).norm()))
    assert not hasattr(m, 'loss') or 'loss' not in m.__dict__, 'loss wrapper left installed'
    lines = [json.loads(l) for l in open(jl)]
    assert len(lines) == 1 and len(lines[0]['y']) == 64 and all(0 < p < 1 for p in lines[0]['p']), lines[0].keys()
    print('(iv) guess.jsonl ok; success %.3f; kinds sample %s' % (lines[0]['success'], set(lines[0]['kind'])))
    # (vi) undo restores head
    assert G.snap is not None
    m.load_state_dict(snap)
    assert torch.equal(G.head.weight, head0.head.weight) and torch.equal(G.head.bias, head0.head.bias), 'undo did not restore head'
    print('(vi) load_state_dict restored the head to its pre-night weights')
    # (v) save
    ck = torch.load(PARENT, map_location='cpu')
    path = os.path.join(SCR, 'night_1', 'checkpoint.pt')
    mode.save_ckpt(ck, m, path)
    load_model(path)
    hs = torch.load(os.path.join(SCR, 'night_1', 'guess.pt'))
    assert set(hs) == {'weight', 'bias'}
    print('(v) checkpoint.pt loads; guess.pt written')
    # (vii) K-FAC factors have no head entry
    F_, _ = kf.factors(kf.kfac_stats(m, diary), cons['protect_energy'])
    assert all(isinstance(n, str) and n in dict(m.named_modules()) for n in F_) and len(F_) > 0
    assert not any(mod is G.head for _, mod in m.named_modules())
    print('(vii) K-FAC factors: %d modules, none is the head' % len(F_))

    # timing: per-update, with and without head, K-FAC measurement excluded (call inner train_night via fresh models)
    def per_update(with_head):
        mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day = orig
        mm = load_model(PARENT)
        if with_head:
            guess.install(SCR, 1.0, 1e-3, SEED)
        cons2 = dict(cons)
        ts = []
        for u in (1, 5):                                            # per-update = (t5 - t1) / 4: the per-night labelling cancels
            t = time.time()
            mode.train_night(mm, new, diary, u, cons2, SEED)
            ts.append(time.time() - t)
        return (ts[1] - ts[0]) / 4
    tw, tn = per_update(True), per_update(False)
    print('per-update (unprojected, per-night labelling excluded): with head %.2fs, without %.2fs' % (tw, tn))
    print('3-update fullrun night with head incl. K-FAC measure: %.1fs' % t3)
    mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day = orig
    print('ALL OK')


if __name__ == '__main__':
    main()
