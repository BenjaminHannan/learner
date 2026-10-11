"""python3 -m mainbrain.test_replayfree : tiny check of arm R (protect_replay=free) in fullrun.py / kf.SplitKFOptimizer (one thread,
64 day-1 rows, 64 diary rows)."""
import json
import os
import time

import torch

from custom_io.data import Dataset, collate, to_device
from custom_io.models import load_model
from domain import mode
from mainbrain import common, fullrun, gp, guess, kf

torch.set_num_threads(1)
PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
RUN = '/mnt/project-files/main-brain/runs/sheet-s200-kf97'
SCR = '/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad'
HERE = os.path.dirname(os.path.abspath(__file__))
PLAIN_C, FREE_C = os.path.join(HERE, 'constants-kf97-lr3e4.json'), os.path.join(HERE, 'constants-kf97r-lr3e4.json')
BASELINE = os.path.join(SCR, 'baseline.pt')   # losses + state_dict of the pre-edit code (git HEAD copy), 2-update plain night, torch.manual_seed(12345) before load_model
SEED = 200001
ORIG = (mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day)


def fresh(c_path, out=None):
    mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day = ORIG
    fullrun.install(c_path, out=out, seed=SEED)


def night(c_path, upd, new, diary, out=None):
    fresh(c_path, out)
    torch.manual_seed(12345)   # the model's drill RNG is seeded from torch's initial seed when it is built
    m = load_model(PARENT)
    t = time.time()
    losses = mode.train_night(m, new, diary, upd, json.load(open(c_path)), SEED)
    return m, losses, time.time() - t


def main():
    os.makedirs(SCR, exist_ok=True)
    rows = common.run_rows(RUN)
    new, diary = rows[1][:64], rows[0][:64]
    free_cons = json.load(open(FREE_C))
    try:
        # (a) split loss value == plain loss (drills off so that the RNG does not differ between one call and two)
        m = load_model(PARENT)
        m.train()
        if hasattr(m, 'ans_drill'):
            m.ans_drill = False
        ds_n, ds_r = Dataset(new, m.vocab), Dataset(diary, m.vocab)
        b = to_device(collate([ds_n[i] for i in range(32)] + [ds_r[i] for i in range(32)]), 'cpu')
        plain = float(m.loss(b)[0].detach())
        stash = {}
        sl = fullrun.split_loss(m, stash)
        split = float(sl(b)[0])
        assert stash, 'no replay grads stashed'
        rel = abs(split - plain) / abs(plain)
        print('(a) plain %.6f split %.6f rel diff %.2e; stashed %d params' % (plain, split, rel, len(stash)))
        assert rel < 1e-4
        m.zero_grad(set_to_none=True)

        # (b) one optimizer step, instrumented
        rec = {}
        init = kf.SplitKFOptimizer.__init__

        def init_i(self, m_, bn, br, F, st):
            init(self, m_, bn, br, F, st)
            aug = lambda: [gp.aug_weight(mod).detach().clone() for _, mod, _ in self.mods]
            rstep = br.step

            def s_rep():   # base_new + projection are done; the replay change is what base_rep alone adds
                before = aug()
                rstep()
                rec['rep'] = [x - y for x, y in zip(aug(), before)]
            br.step = s_rep
            rec['mods'] = self.mods
        proj = kf.project
        rec['new'] = []

        def proj_i(D, f):   # the projected new-half change itself (float32 W + D - W would add rounding noise)
            r = proj(D, f)
            rec['new'].append(r)
            return r
        kf.SplitKFOptimizer.__init__, kf.project = init_i, proj_i
        try:
            night(FREE_C, 1, new, diary)
        finally:
            kf.SplitKFOptimizer.__init__, kf.project = init, proj
        inv = max(float((kf.project(D, f) - D).norm() / D.norm()) for D, (_, _, f) in zip(rec['new'], rec['mods']) if D.norm() > 0)
        out = max(float((D - kf.project(D, f)).norm()) for D, (_, _, f) in zip(rec['rep'], rec['mods']))
        print('(b) new-half change: max ||P(D)-D||/||D|| = %.2e (need < 1e-6); replay change: max ||D-P(D)|| = %.3e (need > 0)' % (inv, out))
        assert inv < 1e-6 and out > 0

        # (c) key absent: identical to the pre-edit code (BASELINE computed before the edit)
        base = torch.load(BASELINE)
        m2, l2, _ = night(PLAIN_C, 2, new, diary)
        assert l2 == base['losses'], (l2, base['losses'])
        assert all(torch.equal(v, base['sd'][k]) for k, v in m2.state_dict().items())
        print('(c) plain night identical to pre-edit baseline: losses', l2, 'weights equal')

        # (d) 3 free updates; keys unchanged, no loss wrapper left behind
        keys0 = list(load_model(PARENT).state_dict().keys())
        m3, l3, t3 = night(FREE_C, 3, new, diary)
        assert list(m3.state_dict().keys()) == keys0 and 'loss' not in m3.__dict__
        print('(d) free 3-update night ok, losses', [round(x, 3) for x in l3], 'keys unchanged (%d)' % len(keys0))

        # (e) free + guess
        both = dict(free_cons, guess=dict(lr=0.001, weight=1.0))
        bp = os.path.join(SCR, 'constants-both.json')
        json.dump(both, open(bp, 'w'))
        fresh(bp, out=os.path.join(SCR, 'replayfree-guess'))
        torch.manual_seed(12345)
        m4 = load_model(PARENT)
        l4 = mode.train_night(m4, new, diary, 2, both, SEED)
        G = next(c.cell_contents for c in mode.save_ckpt.__closure__ if isinstance(c.cell_contents, guess.Guess))
        h0 = guess.Guess(None, 1, 1, SEED)
        h0.make_head(m4.d)
        moved = float((G.head.weight - h0.head.weight).norm())
        assert moved > 0 and 'loss' not in m4.__dict__
        print('(e) free+guess 2-update night ok, losses', [round(x, 3) for x in l4], 'head moved %.5f' % moved)

        # timing per update (night of 3 minus night of 1, same protect cost)
        tp1, tp3 = night(PLAIN_C, 1, new, diary)[2], night(PLAIN_C, 3, new, diary)[2]
        tf1, tf3 = night(FREE_C, 1, new, diary)[2], night(FREE_C, 3, new, diary)[2]
        print('timing per update: plain KF %.2fs, free replay %.2fs' % ((tp3 - tp1) / 2, (tf3 - tf1) / 2))
    finally:
        mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day = ORIG
    print('all ok')


if __name__ == '__main__':
    main()
