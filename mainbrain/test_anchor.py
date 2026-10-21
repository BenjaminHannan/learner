"""python3 -m mainbrain.test_anchor : tiny checks of the state anchor ("anchor": "state") and the padding mask ("protect_pad_mask")
(one thread, real s201 parent and rows, a few updates). (a) keys absent = HEAD; (b) L_anchor 0 at the parent, > 0 after a jolt, gradients;
(c) 3 updates under kf and none, cost ratio; (d) pad mask: A invariant to extra padding / to the batching."""
import json
import os
import subprocess
import sys
import time

import torch

from custom_io import data as D
from custom_io.data import Dataset, collate, to_device
from custom_io.models import load_model
from domain import mode
from mainbrain import anchor, common, fullrun, gp, kf, klreplay

torch.set_num_threads(1)
PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s201/T1SDR_s201/checkpoint.pt'
RUN = '/mnt/project-files/main-brain/runs/sheet-s201-kf97n'
SCR = '/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad'
HEADPKG = os.path.join(SCR, 'pkg_anchor')   # git HEAD's mainbrain package (git archive HEAD mainbrain)
HERE = os.path.dirname(os.path.abspath(__file__))
PLAIN_C, KF_C, NONE_C, KLNONE_C = [os.path.join(HERE, n) for n in (
    'constants-kf99n-lr3e4.json', 'constants-kf99n-anchor100-lr3e4.json', 'constants-none-anchor100-lr3e4.json', 'constants-none-kl10-lr3e4.json')]
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


def grads(m):
    return {n: p.grad.detach().clone() for n, p in m.named_parameters() if p.grad is not None}


def gdiff_norm(a, b):
    return float(sum(((a.get(n, 0) - b.get(n, 0)) ** 2).sum() for n in set(a) | set(b)) ** 0.5)


def mixed_batch(m, new, diary, n=8):
    dn, dd = Dataset(new, m.vocab), Dataset(diary, m.vocab)
    return to_device(collate([dn[i] for i in range(n)] + [dd[i] for i in range(n)]), 'cpu')


def part(b, idx):
    return anchor._part(b, idx)


def total(out):
    return out[0] if isinstance(out, tuple) else out


def rel(a, b):
    return float((a - b).norm() / b.norm().clamp(min=1e-30))


def main():
    os.makedirs(SCR, exist_ok=True)
    rows = common.run_rows(RUN)
    new, diary = rows[1][:64], rows[0][:64]
    assert all(r['source'] == 'diary' for r in diary) and not any(r['source'] == 'diary' for r in new)
    try:
        # (a) keys absent: identical to HEAD's package (3 updates, losses and weights)
        fresh(PLAIN_C)
        m = load()
        l_cur = night(m, PLAIN_C, 3, new, diary, 200001)
        sd = m.state_dict()
        assert 'loss' not in m.__dict__ and 'run' not in m.__dict__ and mode.load_model is ORIG[4]
        if os.path.isdir(HEADPKG):
            subprocess.run('rm -rf %s' % HEADPKG, shell=True, check=True)
        os.makedirs(HEADPKG)
        subprocess.run('git archive HEAD mainbrain | tar -x -C %s' % HEADPKG, shell=True, check=True, cwd=os.path.dirname(HERE))
        outp, hs = os.path.join(SCR, 'head_anchor.pt'), os.path.join(SCR, 'head_anchor.py')
        open(hs, 'w').write(HEAD_SCRIPT)
        env = dict(os.environ, PYTHONPATH=HEADPKG + ':' + os.path.dirname(HERE))
        subprocess.run([sys.executable, hs, HEADPKG, RUN, PLAIN_C, PARENT, outp], check=True, env=env, cwd=SCR)
        h = torch.load(outp)
        assert l_cur == h['losses'], (l_cur, h['losses'])
        assert all(torch.equal(v, h['sd'][k]) for k, v in sd.items())
        print('(a) anchor / protect_pad_mask absent: 3-update night identical to HEAD package: losses', [round(x, 4) for x in l_cur], 'weights bit-equal')

        # (b) L_anchor at the parent and after a jolt, through the real loss wrapper
        m = load()
        parent = klreplay.frozen_copy(m)
        sr, ss, info = anchor.collect_sigmas(parent, diary)
        print('(b) sigmas over %d diary rows:' % len(diary), json.dumps(info))
        assert sr.shape == (256,) and ss.shape == (17 * 256,) and info['mean_rounds_per_row'] == m.n_loops
        m.train()
        b = mixed_batch(m, new, diary)
        B, ri = 16, list(range(8, 16))
        log = []
        wrapped = anchor.wrap(m, parent, sr, ss, 1.0, log)
        rng0 = m._drill_rng.getstate()

        def measure(tag):
            m._drill_rng.setstate(rng0)
            m.zero_grad(set_to_none=True)
            total(m.loss(b)).backward()
            g_plain = grads(m)
            m._drill_rng.setstate(rng0)
            m.zero_grad(set_to_none=True)
            total(wrapped(b)).backward()
            g_wrap = grads(m)
            ga = gdiff_norm(g_wrap, g_plain)          # lam = 1: the gradient of (n_rep/B) * mean L_anchor
            m.zero_grad(set_to_none=True)
            total(m.loss(part(b, ri))).backward()     # replay CE on the replay rows alone (drills drawn fresh; norm only)
            gce = gnorm(m) * len(ri) / B              # as weighted in the batch loss
            m.zero_grad(set_to_none=True)
            return log[-1], ga, gce
        L0, ga0, gce0 = measure('parent')
        print('(b) at the parent: L_anchor %.3e, anchor grad norm %.3e (weighted n_rep/B, lam=1); replay CE grad norm (weighted) %.3f' % (L0, ga0, gce0))
        assert L0 <= 1e-8 and ga0 < 1e-3 * gce0 and gce0 > 1e-2
        g = torch.Generator().manual_seed(7)
        with torch.no_grad():
            for p in m.parameters():
                p.add_(5e-2 * p.abs().mean() * torch.randn(p.shape, generator=g))
        L1, ga1, gce1 = measure('jolt')
        print('(b) after a 5%% jolt: L_anchor %.3e, anchor grad norm %.3e (lam=1; x100 = %.3e); replay CE grad norm (weighted) %.3f; ratio lam=100 anchor / CE = %.2f' % (
            L1, ga1, 100 * ga1, gce1, 100 * ga1 / gce1))
        assert L1 > 1e-6 and ga1 > 1e-3 * gce1

        # (c) 3 updates under kf and none; cost of the anchor term per update
        init = {k: v.clone() for k, v in load().state_dict().items()}
        for name, c in (('kf', KF_C), ('none', NONE_C)):
            od = os.path.join(SCR, 'out_anchor_' + name)
            if os.path.exists(os.path.join(od, 'anchor.jsonl')):
                os.remove(os.path.join(od, 'anchor.jsonl'))
            fresh(c, out=od)
            m = load()
            l = night(m, c, 3, new, diary, 4)
            assert all(map(lambda x: x == x and abs(x) < 1e9, l)) and 'loss' not in m.__dict__ and 'run' not in m.__dict__
            assert mode.load_model is not ORIG[4]
            sd = m.state_dict()
            print('(c) %s: losses %s; changed params: %d / %d' % (name, [round(x, 3) for x in l], sum(not torch.equal(sd[k], init[k]) for k in sd), len(sd)))
            lines = open(os.path.join(od, 'anchor.jsonl')).read().strip().splitlines()
            print('(c) %s anchor.jsonl:' % name, lines)
            assert len(lines) == 2 and 'sigma' in json.loads(lines[0]) and json.loads(lines[1])['n'] == 3 and json.loads(lines[1])['anchor_mean'] > 0
        mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day, mode.load_model = ORIG
        # cost: loss + backward on the same 64-row batches (32 new + 32 diary), with and without the anchor term
        m = load()
        parent = klreplay.frozen_copy(m)
        sr, ss, _ = anchor.collect_sigmas(parent, diary)
        dn, dd = Dataset(new, m.vocab), Dataset(diary, m.vocab)
        bs = [to_device(collate([dn[(i * 32 + j) % 64] for j in range(32)] + [dd[(i * 32 + j + 5) % 64] for j in range(32)]), 'cpu') for i in range(3)]
        wrapped = anchor.wrap(m, parent, sr, ss, 100.0, [])
        m.train()
        tp, ta = [], []
        for rep in range(2):
            for fn, acc in ((m.loss, tp), (wrapped, ta)):
                for b in bs:
                    t = time.time()
                    total(fn(b)).backward()
                    acc.append(time.time() - t)
                    m.zero_grad(set_to_none=True)
        print('(c) seconds per update (loss + backward, 64 rows, 1 thread, machine shared): plain %.2f, with anchor %.2f, ratio %.2f' % (
            sum(tp) / len(tp), sum(ta) / len(ta), sum(ta) / sum(tp)))
        # anchor together with the KL replay loss (one update): the replay forward is the KL's
        c2 = os.path.join(SCR, 'constants-none-kl10-anchor.json')
        d = json.load(open(KLNONE_C))
        d.update(anchor='state', anchor_lambda=100.0)
        json.dump(d, open(c2, 'w'))
        od = os.path.join(SCR, 'out_anchor_kl')
        fresh(c2, out=od)
        m = load()
        l = night(m, c2, 1, new, diary, 4)
        assert all(map(lambda x: x == x and abs(x) < 1e9, l))
        print('(c) anchor + replay_loss kl, 1 update: loss %s, ok' % [round(x, 3) for x in l])
        mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day, mode.load_model = ORIG

        # (d) pad mask: A (and G) of kfac_stats on rows of very different lengths, with extra padding / other batching
        m = load()
        by = sorted(diary, key=lambda r: len(r['prompt']))
        pick = by[:8] + by[-8:]
        print('(d) prompt lengths of the 16 rows:', [len(r['prompt']) for r in pick])
        base_collate = D.collate
        extra_pad = 40

        def collate_extra(items):
            b = base_collate(items)
            B_, T_ = b['prompt_ids'].shape
            b['prompt_ids'] = torch.cat([b['prompt_ids'], torch.zeros(B_, extra_pad, dtype=b['prompt_ids'].dtype)], 1)
            b['prompt_mask'] = torch.cat([b['prompt_mask'], torch.zeros(B_, extra_pad, dtype=torch.bool)], 1)
            return b
        res = {}
        for pm in (False, True):
            rep = {}
            res[pm, 'base'] = kf.kfac_stats(m, pick, bs=16, norm='example', pad_mask=pm, report=rep)
            masked = dict(rep)
            kf.collate = collate_extra
            try:
                res[pm, 'pad'] = kf.kfac_stats(m, pick, bs=16, norm='example', pad_mask=pm)
            finally:
                kf.collate = base_collate
            res[pm, 'bs1'] = kf.kfac_stats(m, pick, bs=1, norm='example', pad_mask=pm)
            assert not any(k in m.__dict__ for k in ('run',)) and not any('kv_of' in blk.__dict__ for blk in m.core)
        print('(d) layers that got the mask (calls per pass):', masked)
        assert set(masked) == {'reader.blocks.0.conv', 'reader.blocks.1.conv', 'core.0.kv', 'core.1.kv'}
        for other, what in (('pad', 'rows padded %d extra columns' % extra_pad), ('bs1', 'one row per batch (bs=1) vs bs=16')):
            for which, idx in (('A', 0), ('G', 1)):
                for pm in (False, True):
                    ch = {n: rel(res[pm, other][n][idx], res[pm, 'base'][n][idx]) for n in res[pm, 'base']}
                    worst = max(ch, key=ch.get)
                    nz = sum(v > 1e-5 for v in ch.values())
                    print('(d) %s, %s of %s, mask %-5s: max rel change %.3e (%s); layers with change > 1e-5: %d / %d; %s' % (
                        what, '', which, pm, ch[worst], worst, nz, len(ch), {n: float('%.1e' % v) for n, v in ch.items() if v > 1e-5}))
                    if which == 'A' and pm:
                        assert ch[worst] < 1e-5, (other, worst, ch[worst])
                    if which == 'A' and not pm and other == 'pad':
                        assert ch[worst] > 1e-3
    finally:
        mode.train_night, mode.make_opt, mode.save_ckpt, mode.try_day, mode.load_model = ORIG
    print('all ok')


if __name__ == '__main__':
    main()
