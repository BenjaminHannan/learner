"""SB-2 guesser head: a Linear(d, 1) on the post-loop thinker control state zf (free run) that predicts whether the model's
own greedy answer to a try prompt will match the tool's value. Trained jointly with the night loss (BCE, weight `weight`);
the head is NOT part of the model (not in m.state_dict() / m.parameters()), is not projected or clipped, and persists across
nights. Per night it logs its prediction on that day's tries BEFORE it trains on them (guess.jsonl), saves guess.pt next to
each checkpoint.pt, and is restored on undo.

Composition with fullrun: guess.install must run BEFORE fullrun captures mode.train_night / mode.make_opt (fullrun.install
does this when the constants file has a "guess" key), so that guess's train_night is the INNER one: fullrun measures K-FAC
on the plain m.loss first, and only then does this wrapper add the BCE term to m.loss.
"""
import json
import os
import time

import numpy as np
import torch
import torch.nn.functional as F

from custom_io.data import Dataset, collate, to_device
from domain import mode


def _batch(m, rows):
    ds = Dataset([{'id': f'z{i}', 'prompt': r['prompt'], 'answer': '', 'accepted': [], 'family': '', 'level': 0}
                  for i, r in enumerate(rows)], m.vocab, strict=False)
    return to_device(collate([ds[i] for i in range(len(rows))]), 'cpu')


def run_zf(m, batch):
    """Free run; -> (run output, post-loop control-1 state ln_z(Z[:, 1]) of the last loop iteration)."""
    grab = {}

    def each(t, s):
        if t == m.n_loops - 1:          # called after iteration t's update, so Z is the post-loop workspace
            grab['z'] = m.ln_z(s['Z'][:, 1])
    o = m.run(batch, each=each)
    return o, grab['z']


def zf_of(m, rows, grad, bs=64):
    """[B, d] post-loop control-1 states for rows (free run on the prompts), with or without grad."""
    out = []
    with torch.set_grad_enabled(grad):
        for s in range(0, len(rows), bs):
            out.append(run_zf(m, _batch(m, rows[s:s + bs]))[1])
    return torch.cat(out)


def labels(m, rows):
    """(y float tensor, answers): y = 1 if the model's greedy answer equals the row's answer."""
    res = mode.greedy(m, [r['prompt'] for r in rows])
    ans = [a for _, a in res]
    return torch.tensor([float(a == r['answer']) for a, r in zip(ans, rows)]), ans


class Guess:
    def __init__(self, run_dir, weight, lr, seed, d=None):
        self.run_dir, self.weight, self.lr, self.seed = run_dir, weight, lr, seed
        self.d = d
        self.head = None
        self.snap = None            # head state at night start; None between a save and the next night
        self.kinds = {}             # row id -> kind (recorded from try_day's write_row)
        self.active = False         # inside a night: make_opt adds the head group
        self.last = {}

    def make_head(self, d):
        with torch.random.fork_rng():
            torch.manual_seed(self.seed)
            self.head = torch.nn.Linear(d, 1)
        self.d = d

    def logit(self, zf):
        return self.head(zf.float())[:, 0]

    def restore(self):
        if self.snap is not None:
            self.head.load_state_dict(self.snap)

    def log_start(self, m, new, night):
        y, ans = labels(m, new)
        with torch.no_grad():
            p = torch.sigmoid(self.logit(zf_of(m, new, False))).tolist()
        rec = dict(night=night, head_nights_trained=night - 1,
                   kind=[self.kinds.get(r['id'], r.get('kind', r.get('family'))) for r in new],
                   y=[int(v) for v in y.tolist()], p=p, prompt=[r['prompt'] for r in new],
                   row_source=[r.get('source') for r in new], success=float(y.mean()) if len(y) else None)
        if self.run_dir:
            os.makedirs(self.run_dir, exist_ok=True)
            with open(os.path.join(self.run_dir, 'guess.jsonl'), 'a') as f:
                f.write(json.dumps(rec) + '\n')
        return y

    def train_night(self, base_train):
        def train_night(m, new, diary, updates, cons, seed, fresh=False, picks=None, addon=None):
            t0 = time.time()
            if self.head is None:
                self.make_head(m.d)
            if not hasattr(m, '_guess_lsd'):                       # undo support: permanent instance-level wrapper
                orig_lsd = m.load_state_dict

                def lsd(*a, **k):
                    r = orig_lsd(*a, **k)
                    self.restore()
                    return r
                m.load_state_dict = lsd
                m._guess_lsd = True
            night = seed % 1000
            y = self.log_start(m, new, night)
            self.snap = {k: v.detach().clone() for k, v in self.head.state_dict().items()}
            rng, order, pos, bces = np.random.RandomState(seed + 777), np.array([], dtype=int), 0, []
            plain_loss = m.loss

            def loss(b):
                out = plain_loss(b)
                if not m.training or not len(new):
                    return out
                nonlocal order, pos
                ti = []
                while len(ti) < 32:
                    if pos >= len(order):
                        order, pos = rng.permutation(len(new)), 0
                    take = min(32 - len(ti), len(order) - pos)
                    ti += [int(i) for i in order[pos:pos + take]]
                    pos += take
                zf = zf_of(m, [new[i] for i in ti], True)
                bce = F.binary_cross_entropy_with_logits(self.logit(zf), y[ti])
                bces.append(float(bce.detach()))
                if isinstance(out, tuple):
                    aux = dict(out[1]) if isinstance(out[1], dict) else out[1]
                    if isinstance(aux, dict):
                        aux['guess_bce'] = float(bce.detach())
                    return (out[0] + self.weight * bce, aux) + tuple(out[2:])
                return out + self.weight * bce
            m.loss = loss
            self.active = True
            try:
                return base_train(m, new, diary, updates, cons, seed, fresh=fresh, picks=picks, addon=addon)
            finally:
                self.active = False
                del m.loss
                k = min(10, len(bces))
                print('guess', json.dumps(dict(night=night, n=len(new), success=round(float(y.mean()), 4) if len(y) else None,
                                               bce_first10=round(float(np.mean(bces[:k])), 4) if k else None,
                                               bce_last10=round(float(np.mean(bces[-k:])), 4) if k else None,
                                               secs=round(time.time() - t0, 1))), flush=True)
        return train_night


def install(run_dir, weight, lr, seed):
    """Monkeypatch mode (see module docstring for ordering). Returns the Guess."""
    g = Guess(run_dir, weight, lr, seed)
    base_make, base_save, base_try = mode.make_opt, mode.save_ckpt, mode.try_day

    def make_opt(m, lr_):
        opt = base_make(m, lr_)
        if g.active:
            opt.add_param_group({'params': list(g.head.parameters()), 'weight_decay': 0.0, 'lr': g.lr})
        return opt

    def save_ckpt(ck, m, path, addon=None):
        r = base_save(ck, m, path, addon)
        if g.head is not None:
            torch.save(g.head.state_dict(), os.path.join(os.path.dirname(path), 'guess.pt'))
        g.snap = None
        return r

    def try_day(m, tool, items, kinds, cons, log, day, write_row):
        def wr(**kw):
            g.kinds[kw['id']] = kw.get('kind')
            return write_row(**kw)
        return base_try(m, tool, items, kinds, cons, log, day, wr)

    mode.make_opt, mode.save_ckpt, mode.try_day = make_opt, save_ckpt, try_day
    mode.train_night = g.train_night(mode.train_night)
    return g
