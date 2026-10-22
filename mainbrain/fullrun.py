"""Full domain-mode run with protected whole-model nights (main-brain thread).

  python -m mainbrain.fullrun --constants CONST.json --parent CKPT --tool sheet|rpn --out DIR --seed N [--threads 4]

Runs domain/mode.py's main loop unchanged (practice, tries, quiz, check, undo, stop), with two substitutions:
- the constants file is CONST.json (a v4-style whole-model file plus `protect` and `protect_energy`);
- before each night the model re-measures what its old answers use, on its current weights and its diary, and that
  night's optimizer steps are projected (mainbrain/kf.py or gp.py). Unprojectable parameters stay frozen.
The log gets one 'protect' line per night (written to stdout; mode's log.jsonl is untouched in format).
"""
import json
import os
import sys
import time

import torch

from domain import mode
from mainbrain import anchor, gp, guess, kf, klreplay


def split_loss(m, stash):
    """Arm R loss wrapper (instance-level m.loss, see install). Training batches with diary rows: replay half backward now (weighted
    n_rep/B), grads clipped to norm 1.0, stashed per parameter and zeroed; returns w_new*loss_new + w_rep*loss_rep.detach() so
    train_night's backward/clip only see the new half. Eval mode, no-grad, or no diary/new rows: the plain loss."""
    plain = m.loss

    def loss(b):
        rows = b['rows']
        B = len(rows)
        ri = [i for i, r in enumerate(rows) if r.get('source') == 'diary']
        rs = set(ri)
        ni = [i for i in range(B) if i not in rs]
        if not m.training or not torch.is_grad_enabled() or not ri or not ni:
            return plain(b)

        def part(idx):
            t = torch.tensor(idx)
            return {k: (v[t] if torch.is_tensor(v) else [v[i] for i in idx]) for k, v in b.items()}
        w_rep, w_new = len(ri) / B, len(ni) / B
        out_r = plain(part(ri))
        lr_ = out_r[0] if isinstance(out_r, tuple) else out_r
        (w_rep * lr_).backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        stash.clear()
        for p in m.parameters():
            if p.grad is not None:
                stash[p] = p.grad.detach().clone()
                p.grad = None
        out_n = plain(part(ni))
        if isinstance(out_n, tuple):
            return (w_new * out_n[0] + w_rep * lr_.detach(),) + tuple(out_n[1:])
        return w_new * out_n + w_rep * lr_.detach()
    return loss


def install(cons_path, out=None, seed=None):
    cons = json.load(open(cons_path))
    method = cons['protect']
    energy = cons['protect_energy'] if method != 'none' else cons.get('protect_energy')
    pg = cons.get('protect_g', 'empirical')
    assert pg in ('empirical', 'example'), pg
    assert method in ('kf', 'gp', 'none') and (method == 'none' or 0 < energy < 1), (method, energy)   # 'none': no projection, plain AdamW
    rl = cons.get('replay_loss', 'ce')
    assert rl in ('ce', 'kl'), rl
    kl_w = float(cons.get('replay_kl_weight', 10.0))
    an = cons.get('anchor')
    assert an in (None, 'state'), an
    an_lam = float(cons.get('anchor_lambda', 100.0))
    pad = bool(cons.get('protect_pad_mask'))
    soft = cons.get('protect_soft')   # graded mask (kf.mask_for soft); missing or null: the hard mask
    assert soft is None or method == 'kf', 'protect_soft needs protect=kf'
    assert soft is None or (isinstance(soft, (int, float)) and soft >= 0), soft
    assert not pad or method == 'kf', 'protect_pad_mask masks the K-FAC statistics: needs protect=kf'
    # frozen pre-mode model (arms KL and anchor share it), taken when mode.main builds the model (before any training); the anchor's
    # per-dimension scales are measured once, on the parent over the diary of the first night
    klstate = {'parent': None, 'sig': None}
    assert not cons.get('addon'), 'protection replaces the add-on'
    mode.CONST_PATH = cons_path
    if 'guess' in cons:   # SB-2 head: installed first, so it is the inner train_night/make_opt (K-FAC is measured on the plain loss)
        guess.install(out, cons['guess']['weight'], cons['guess']['lr'], seed, cons['guess'].get('input', 'ctrl1'))
    replay = cons.get('protect_replay')
    assert replay in (None, 'free', 'precond'), replay
    parent = bool(cons.get('protect_parent'))
    assert not parent or method == 'kf', 'protect_parent needs protect=kf'
    keep = {}   # arm U: the parent factors F0, measured once at the first night and kept for the whole run
    base_train, base_make = mode.train_night, mode.make_opt
    if rl == 'kl' or an:
        base_load = mode.load_model

        def load_model(*a, **k):
            m_ = base_load(*a, **k)
            if klstate['parent'] is None:
                klstate['parent'] = klreplay.frozen_copy(m_)
            return m_
        mode.load_model = load_model

    def train_night(m, new, diary, updates, cons, seed, fresh=False, picks=None, addon=None):
        t = time.time()
        for p in m.parameters():
            p.requires_grad_(True)
        F0 = None
        if method == 'none':
            info = {}
        elif method == 'kf':
            F, info = kf.factors(kf.kfac_stats(m, diary, norm='example' if pg == 'example' else None, pad_mask=pad), energy, soft=soft)
            if parent and 'F0' not in keep:
                keep['F0'] = F   # night 1: factors measured on the parent weights are F0
            F0 = keep['F0'] if parent else None
            wrap = lambda mm, base: kf.KFOptimizer(mm, base, F, F0=F0)
        else:
            P, info = gp.projectors(gp.covariances(m, diary), energy)
            wrap = lambda mm, base: gp.GPOptimizer(mm, base, P)
        frozen = gp.freeze_unprojected(m) if method != 'none' else []
        free = replay in ('free', 'precond')   # both split the batch (split_loss)
        stash = {}
        if replay == 'precond':   # arm R2: replay half stepped with base_new's own second moment (kf.PrecondReplayKFOptimizer)
            assert method == 'kf', 'protect_replay=precond needs protect=kf'
            mode.make_opt = lambda mm, lr: kf.PrecondReplayKFOptimizer(mm, base_make(mm, lr), F, stash, F0=F0)
        elif free:   # arm R: replay half unprojected (kf.SplitKFOptimizer); guess's BCE (inner train_night) lands in the projected new half
            assert method == 'kf', 'protect_replay=free needs protect=kf'
            mode.make_opt = lambda mm, lr: kf.SplitKFOptimizer(mm, base_make(mm, lr), torch.optim.AdamW(
                [p for p in mm.parameters() if p.requires_grad], lr=lr, betas=(0.9, 0.95), weight_decay=0.0), F, stash)
        elif method != 'none':
            mode.make_opt = lambda mm, lr: wrap(mm, base_make(mm, lr))
        extra = dict(g=pg) if 'protect_g' in cons else {}
        if free:
            extra['replay'] = replay
        if parent:
            extra['parent'] = True
        if pad:
            extra['pad_mask'] = True
        if soft is not None:
            extra['soft'] = soft
        print('protect', json.dumps(dict(method=method, energy=energy, **extra, seed=seed, frozen=len(frozen), secs=round(time.time() - t, 1),
                                         free_share={n: v.get('free_share', v.get('free')) for n, v in info.items()})), flush=True)
        kls, ans = [], []
        had, prev = 'loss' in m.__dict__, m.__dict__.get('loss')
        if rl == 'kl':
            assert not free, 'replay_loss=kl replaces the split replay half'
            if klstate['parent'] is None:   # not built through mode.load_model (direct train_night call): the model as it is now
                klstate['parent'] = klreplay.frozen_copy(m)
            extra['replay_loss'] = 'kl'
            m.loss = klreplay.wrap(m, klstate['parent'], kl_w, kls)
        if an:
            assert not free, 'anchor replaces nothing of the split replay half; not combined with protect_replay'
            if klstate['parent'] is None:
                klstate['parent'] = klreplay.frozen_copy(m)
            if klstate['sig'] is None:   # subject start: the first night, before any update
                t1 = time.time()
                sr, ss, sinfo = anchor.collect_sigmas(klstate['parent'], diary)
                klstate['sig'] = (sr, ss)
                sinfo['secs'] = round(time.time() - t1, 1)
                print('anchor_sigma', json.dumps(sinfo), flush=True)
                if out:
                    os.makedirs(out, exist_ok=True)
                    with open(os.path.join(out, 'anchor.jsonl'), 'a') as f_:
                        f_.write(json.dumps(dict(sigma=sinfo)) + '\n')
            m.loss = anchor.wrap(m, klstate['parent'], klstate['sig'][0], klstate['sig'][1], an_lam, ans)
        if free:
            m.loss = split_loss(m, stash)
        try:
            return base_train(m, new, diary, updates, cons, seed, fresh=fresh, picks=picks, addon=addon)
        finally:
            if rl == 'kl' and kls:
                rec = dict(night=None if seed is None else seed % 1000, replay_kl_mean=sum(kls) / len(kls), n=len(kls), weight=kl_w)
                print('replay_kl', json.dumps(rec), flush=True)
                if out:
                    os.makedirs(out, exist_ok=True)
                    with open(os.path.join(out, 'replay_kl.jsonl'), 'a') as f_:
                        f_.write(json.dumps(rec) + '\n')
            if an and ans:
                rec = dict(night=None if seed is None else seed % 1000, anchor_mean=sum(ans) / len(ans), n=len(ans), lam=an_lam)
                print('anchor', json.dumps(rec), flush=True)
                if out:
                    os.makedirs(out, exist_ok=True)
                    with open(os.path.join(out, 'anchor.jsonl'), 'a') as f_:
                        f_.write(json.dumps(rec) + '\n')
            if free or rl == 'kl' or an:
                if had:
                    m.loss = prev
                else:
                    m.__dict__.pop('loss', None)
            mode.make_opt = base_make
            for p in m.parameters():
                p.requires_grad_(True)

    mode.train_night = train_night


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    i = argv.index('--constants')
    cons_path = argv[i + 1]
    del argv[i:i + 2]
    install(cons_path, out=argv[argv.index('--out') + 1], seed=int(argv[argv.index('--seed') + 1]))
    mode.main(argv)


if __name__ == '__main__':
    main()
