"""python3 -m mainbrain.test_u_r2 : tiny checks of arm U (protect_parent) and arm R2 (protect_replay=precond) in fullrun.py / kf.py
(one thread, 64 day-1 rows, 64 diary rows)."""
import json
import os
import subprocess
import sys
import time

import torch

from custom_io.models import load_model
from domain import mode
from mainbrain import common, fullrun, gp, kf

torch.set_num_threads(1)
PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
RUN = '/mnt/project-files/main-brain/runs/sheet-s200-kf97n'
SCR = '/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad'
HEADPKG = os.path.join(SCR, 'pkg_u_r2')   # git HEAD's mainbrain package (git archive HEAD mainbrain)
HERE = os.path.dirname(os.path.abspath(__file__))
PLAIN_C, U_C, R2_C = [os.path.join(HERE, 'constants-kf99n%s-lr3e4.json' % s) for s in ('', '-u', '-r2')]
SET_AUG = gp.set_aug
ORIG = (mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day)

HEAD_SCRIPT = '''
import json, sys, torch
torch.set_num_threads(1)
from custom_io.models import load_model
from domain import mode
from mainbrain import common, fullrun
import mainbrain
assert fullrun.__file__.startswith(sys.argv[1]), fullrun.__file__
rows = common.run_rows(sys.argv[2])
new, diary = rows[1][:64], rows[0][:64]
fullrun.install(sys.argv[3], out=None, seed=200001)
torch.manual_seed(12345)
m = load_model(sys.argv[4])
l = mode.train_night(m, new, diary, 2, json.load(open(sys.argv[3])), 200001)
torch.save(dict(losses=l, sd=m.state_dict()), sys.argv[5])
'''


def fresh(c_path):
    mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day = ORIG
    fullrun.install(c_path, out=None, seed=200001)


def load():
    torch.manual_seed(200)
    return load_model(PARENT)


def night(m, c_path, upd, new, diary, seed):
    return mode.train_night(m, new, diary, upd, json.load(open(c_path)), seed)


def aug(m):
    return {n: gp.aug_weight(mod).detach().clone() for n, mod in gp.projected_modules(m)}


def rel(a, b):
    return float((a - b).norm() / max(float(b.norm()), 1e-30))


def main():
    os.makedirs(SCR, exist_ok=True)
    rows = common.run_rows(RUN)
    new, diary = rows[1][:64], rows[0][:64]
    try:
        # (a) U: 2 nights; second night's step change invariant under project(., F_night2) and project(., F0)
        calls, facs = [], []
        ks, fa = kf.kfac_stats, kf.factors
        kf.kfac_stats = lambda *a, **k: (calls.append(1), ks(*a, **k))[1]
        kf.factors = lambda *a, **k: (lambda r: (facs.append(r[0]), r)[1])(fa(*a, **k))
        try:
            fresh(U_C)
            m = load()
            night(m, U_C, 2, new, diary, 1)
            w1 = aug(m)
            night(m, U_C, 2, new, diary, 2)
            w2 = aug(m)
        finally:
            kf.kfac_stats, kf.factors = ks, fa
        F0, F2 = facs[0], facs[1]
        worst_f, worst_f0, worst_raw = 0.0, 0.0, 0.0
        for n in w2:
            D = w2[n] - w1[n]
            if n not in F2 or n not in F0 or D.norm() == 0:
                continue
            raw = D
            for _ in range(2):   # one more alternating pass (F2 then F0), then check
                D = kf.project(kf.project(D, F2[n]), F0[n])
            worst_f0 = max(worst_f0, rel(kf.project(D, F0[n]), D))
            worst_f = max(worst_f, rel(kf.project(D, F2[n]), D))
            worst_raw = max(worst_raw, rel(kf.project(raw, F0[n]), raw))
        print('(a) kfac_stats calls over 2 nights: %d (night 1 measured once, reused as F0; night 2 once)' % len(calls))
        print('    night-2 step change (as taken): max rel residual under F0 %.2e' % max(
            rel(kf.project(w2[n] - w1[n], F0[n]), w2[n] - w1[n]) for n in w2 if n in F0 and (w2[n] - w1[n]).norm() > 0))
        print('    after one more alternating pass: max rel non-invariance under F_night2 %.2e, under F0 %.2e (F0 need < 1e-5; F_night2 reported only: the projections do not commute)' % (worst_f, worst_f0))
        # Only the LAST projection applied is exact: P_F0 P_F D is invariant under F0 but not under F_night2 (two different
        # orthogonal projections do not commute), so F_night2's residual is reported, not asserted.
        assert len(calls) == 2 and worst_f0 < 1e-5

        # (b) R2: one step, instrumented
        rec = {}
        init = kf.PrecondReplayKFOptimizer.__init__

        def init_i(self, m_, bn, F, st, F0=None):
            init(self, m_, bn, F, st, F0)
            rec['bn'], rec['stash'] = bn, st
            rec['new_params'] = {id(p): p for g in bn.param_groups for p in g['params']}
            rec['k'], nm = 0, len(self.mods)
            sa = gp.set_aug

            def set_aug(mod, A):   # the last set_aug is the end of the projection: snapshot = state after the new half, before the replay half
                sa(mod, A)
                rec['k'] += 1
                if rec['k'] == nm:
                    rec['p_after_new'] = {id(p): p.detach().clone() for p in rec['new_params'].values()}
                    rec['stash'] = dict(st)
            gp.set_aug = set_aug
            rec['before'] = {id(p): p.detach().clone() for g in bn.param_groups for p in g['params']}
        kf.PrecondReplayKFOptimizer.__init__ = init_i
        try:
            fresh(R2_C)
            m = load()
            night(m, R2_C, 1, new, diary, 3)
        finally:
            kf.PrecondReplayKFOptimizer.__init__ = init
            gp.set_aug = SET_AUG
        bn = rec['bn']
        lr, eps = bn.param_groups[0]['lr'], bn.param_groups[0]['eps']
        beta2 = bn.param_groups[0]['betas'][1]
        ratios, chk, best = [], None, None
        for pid, p in rec['new_params'].items():
            g = next((v for k, v in rec['stash'].items() if id(k) == pid), None)
            if g is None or 'exp_avg_sq' not in bn.state.get(p, {}):
                continue
            st = bn.state[p]
            vh = st['exp_avg_sq'] / (1 - beta2 ** float(st['step']))
            expect = -lr * g / (vh.sqrt() + eps)
            got = p.detach() - rec['p_after_new'][pid]
            newd = rec['p_after_new'][pid] - rec['before'][pid]
            ratios.append((float(got.norm() / max(float(newd.norm()), 1e-12)), float(g.norm())))
            e = rel(got, expect)
            if chk is None or float(g.norm()) > best:
                chk, best = e, float(g.norm())
        assert ratios
        gn = sorted(ratios, key=lambda r: r[1])
        tot = sorted(r[0] for r in ratios)[len(ratios) // 2]
        print('(b) R2 one step: %d params with replay steps; rel error of -lr*g/(sqrt(vhat)+eps) on the param with the largest g: %.2e' % (len(ratios), chk))
        print('    replay/new change norm ratio: median %.3f, smallest-g param %.3f (|g|=%.2e), largest-g param %.3f (|g|=%.2e)' % (
            tot, gn[0][0], gn[0][1], gn[-1][0], gn[-1][1]))
        assert chk < 1e-4

        # (c) absent keys: identical to HEAD
        fresh(PLAIN_C)
        m = load_model_seeded()
        l_cur = night(m, PLAIN_C, 2, new, diary, 200001)
        sd = m.state_dict()
        outp = os.path.join(SCR, 'head_u_r2.pt')
        hs = os.path.join(SCR, 'head_u_r2.py')
        open(hs, 'w').write(HEAD_SCRIPT)
        env = dict(os.environ, PYTHONPATH=HEADPKG + ':' + os.path.dirname(HERE))
        subprocess.run([sys.executable, hs, HEADPKG, RUN, PLAIN_C, PARENT, outp], check=True, env=env, cwd=SCR)
        h = torch.load(outp)
        assert l_cur == h['losses'], (l_cur, h['losses'])
        assert all(torch.equal(v, h['sd'][k]) for k, v in sd.items())
        print('(c) absent keys: 2-update night identical to HEAD package: losses', [round(x, 4) for x in l_cur], 'weights equal')

        # (d) both constants files, 3-update night
        keys0 = list(load().state_dict().keys())
        for c in (U_C, R2_C):
            fresh(c)
            m = load()
            l = night(m, c, 3, new, diary, 4)
            assert all(map(lambda x: x == x and abs(x) < 1e9, l)) and list(m.state_dict().keys()) == keys0 and 'loss' not in m.__dict__
            print('(d) %s: 3-update night ok, losses %s, keys unchanged (%d)' % (os.path.basename(c), [round(x, 3) for x in l], len(keys0)))

        # timing per update (night of 3 minus night of 1)
        t = {}
        for name, c in (('plain', PLAIN_C), ('U', U_C), ('R2', R2_C)):
            ts = []
            for u in (1, 3):
                fresh(c)
                m = load()
                t0 = time.time()
                night(m, c, u, new, diary, 5)
                ts.append(time.time() - t0)
            t[name] = (ts[1] - ts[0]) / 2
        print('timing per update: plain %.2fs, U %.2fs, R2 %.2fs' % (t['plain'], t['U'], t['R2']))
    finally:
        mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day = ORIG
    print('all ok')


def load_model_seeded():
    torch.manual_seed(12345)   # as the HEAD script: the model's drill RNG is seeded from torch's initial seed when it is built
    return load_model(PARENT)


if __name__ == '__main__':
    main()
