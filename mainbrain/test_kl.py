"""python3 -m mainbrain.test_kl : tiny checks of replay_loss "kl" and protect "none" (fullrun.py, klreplay.py)
(one thread, 64 day-1 rows, 64 diary rows, a few updates)."""
import json
import os
import subprocess
import sys

import torch

from custom_io.data import Dataset, collate, to_device
from custom_io.models import load_model
from domain import mode
from mainbrain import common, fullrun, gp, klreplay

torch.set_num_threads(1)
PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s201/T1SDR_s201/checkpoint.pt'
RUN = '/mnt/project-files/main-brain/runs/sheet-s201-kf97n'
SCR = '/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad'
HEADPKG = os.path.join(SCR, 'pkg_kl')   # git HEAD's mainbrain package (git archive HEAD mainbrain)
HERE = os.path.dirname(os.path.abspath(__file__))
PLAIN_C, KF_C, NONE_C = [os.path.join(HERE, n) for n in ('constants-kf99n-lr3e4.json', 'constants-kf99n-kl10-lr3e4.json', 'constants-none-kl10-lr3e4.json')]
ORIG = (mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day, mode.load_model)

HEAD_SCRIPT = '''
import json, sys, torch
torch.set_num_threads(1)
from custom_io.models import load_model
from domain import mode
from mainbrain import common, fullrun
assert fullrun.__file__.startswith(sys.argv[1]), fullrun.__file__
rows = common.run_rows(sys.argv[2])
new, diary = rows[1][:64], rows[0][:64]
fullrun.install(sys.argv[3], out=None, seed=200001)
torch.manual_seed(12345)
m = load_model(sys.argv[4])
l = mode.train_night(m, new, diary, 3, json.load(open(sys.argv[3])), 200001)
torch.save(dict(losses=l, sd=m.state_dict()), sys.argv[5])
'''


def fresh(c_path, out=None):
    mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day, mode.load_model = ORIG
    fullrun.install(c_path, out=out, seed=200001)


def load(seed=12345):
    torch.manual_seed(seed)
    return load_model(PARENT)


def night(m, c_path, upd, new, diary, seed):
    return mode.train_night(m, new, diary, upd, json.load(open(c_path)), seed)


def gnorm(m):
    return float(sum((p.grad.float() ** 2).sum() for p in m.parameters() if p.grad is not None) ** 0.5)


def diary_batch(m, diary, n=16):
    ds = Dataset(diary, m.vocab)
    return to_device(collate([ds[i] for i in range(n)]), 'cpu')


def main():
    os.makedirs(SCR, exist_ok=True)
    rows = common.run_rows(RUN)
    new, diary = rows[1][:64], rows[0][:64]
    assert all(r['source'] == 'diary' for r in diary) and not any(r['source'] == 'diary' for r in new)
    try:
        # (a) replay_loss absent: identical to HEAD's package (3 updates, losses and weights)
        fresh(PLAIN_C)
        m = load()
        l_cur = night(m, PLAIN_C, 3, new, diary, 200001)
        sd = m.state_dict()
        assert 'loss' not in m.__dict__ and mode.load_model is ORIG[4]
        if not os.path.isdir(HEADPKG):
            os.makedirs(HEADPKG)
            subprocess.run('git archive HEAD mainbrain | tar -x -C %s' % HEADPKG, shell=True, check=True, cwd=os.path.dirname(HERE))
        outp, hs = os.path.join(SCR, 'head_kl.pt'), os.path.join(SCR, 'head_kl.py')
        open(hs, 'w').write(HEAD_SCRIPT)
        env = dict(os.environ, PYTHONPATH=HEADPKG + ':' + os.path.dirname(HERE))
        subprocess.run([sys.executable, hs, HEADPKG, RUN, PLAIN_C, PARENT, outp], check=True, env=env, cwd=SCR)
        h = torch.load(outp)
        assert l_cur == h['losses'], (l_cur, h['losses'])
        assert all(torch.equal(v, h['sd'][k]) for k, v in sd.items())
        print('(a) replay_loss absent: 3-update night identical to HEAD package: losses', [round(x, 4) for x in l_cur], 'weights bit-equal')

        # (b) at the parent: KL 0, gradient ~0; CE gradient on the same diary rows clearly nonzero
        m = load()
        parent = klreplay.frozen_copy(m)
        assert not parent.training and not any(p.requires_grad for p in parent.parameters())
        m.train()
        b = diary_batch(m, diary)
        kl, parts = klreplay.replay_kl(m, parent, b)
        kl.backward()
        gk = gnorm(m)
        m.zero_grad()
        out = m.loss(b)
        (out[0] if isinstance(out, tuple) else out).backward()
        gc = gnorm(m)
        m.zero_grad()
        print('(b) at the parent: replay KL %.2e, KL grad norm %.2e; CE on the same rows: grad norm %.3f' % (float(kl), gk, gc))
        assert abs(float(kl)) < 1e-6 and gk < 1e-4 and gc > 1e-2 and gk < 1e-3 * gc
        # (c) perturbed weights: KL > 0 and gradient nonzero
        g = torch.Generator().manual_seed(7)
        with torch.no_grad():
            for p in m.parameters():
                p.add_(5e-2 * p.abs().mean() * torch.randn(p.shape, generator=g))
        kl, parts = klreplay.replay_kl(m, parent, b)
        kl.backward()
        gk2 = gnorm(m)
        print('(c) perturbed: replay KL %.3e, grad norm %.3f; parts %s' % (float(kl), gk2, {k: float("%.2e" % v) for k, v in parts.items()}))
        assert float(kl) > 1e-6 and gk2 > 1e-3 and all(v >= -1e-5 for v in parts.values())

        # (d) 3 updates under kf and none
        probe = load()
        frozen = gp.freeze_unprojected(probe)
        ln = next(n for n in frozen if 'ln' in n.lower() and n.endswith('weight'))
        init = {k: v.clone() for k, v in load().state_dict().items()}
        for name, c, projected in (('kf', KF_C, True), ('none', NONE_C, False)):
            od = os.path.join(SCR, 'out_kl_' + name)
            if os.path.exists(os.path.join(od, 'replay_kl.jsonl')):
                os.remove(os.path.join(od, 'replay_kl.jsonl'))
            fresh(c, out=od)
            m = load()
            l = night(m, c, 3, new, diary, 4)
            assert all(map(lambda x: x == x and abs(x) < 1e9, l)) and 'loss' not in m.__dict__ and mode.train_night is not ORIG[0]
            sd = m.state_dict()
            moved_ln = not torch.equal(sd[ln], init[ln])
            nfro = sum(not torch.equal(sd[n], init[n]) for n in frozen if n in sd)
            print('(d) %s: losses %s; frozen-by-K-FAC params: %d, changed: %d; %s changed: %s; log: %s' % (
                name, [round(x, 3) for x in l], len(frozen), nfro, ln, moved_ln, open(os.path.join(od, 'replay_kl.jsonl')).read().strip()))
            if projected:
                assert nfro == 0 and not moved_ln
            else:
                assert moved_ln and nfro > 0
            assert len(open(os.path.join(od, 'replay_kl.jsonl')).read().strip().splitlines()) == 1
    finally:
        mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day, mode.load_model = ORIG
    print('all ok')


if __name__ == '__main__':
    main()
