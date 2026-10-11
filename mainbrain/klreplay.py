"""Replay loss as a KL to the frozen pre-mode model (arm KL; selected by constants "replay_loss": "kl", fullrun.py).

Instead of cross-entropy on the diary rows (targets = the pre-mode model's own greedy answers), the replay half is
W * KL(parent || model): the forward KL from a frozen copy of the pre-mode model to the model, on the same teacher-forced
inputs, over EVERY output distribution that custom_io/models/tool.py Tool.loss() covers, weighted and averaged exactly as
the CE terms are (so at W = 1 it is the soft-target version of the CE; a model equal to the parent has KL 0 and gradient 0).

Heads (one KL term per CE term of Tool.loss / call_loss / span_loss):
- op head, every call round: softmax over ops, rows weighted like the CE (1, or w_noop for rows with no call), mean over rows;
- operand cells, every call round: the pointer-generator's per-cell distribution over the vocabulary, on the cells the CE
  scores (the cell has a gold char, or for a commutative op the other operand's cell has one), call rows only, sum / B;
- span writer (span_copy): per round and side, the gate (Bernoulli) on call rows and the pointer (softmax over the context)
  on the sides where the gold string occurs; the stop head (Bernoulli, mean over the same samples); the answer pointer on
  mode-0 rows whose answer occurs in the context;
- mode head: softmax over modes, mean over rows;
- word pointer: softmax over the prompt's words, on WORD (mode 1) rows, sum / B;
- GEN registers: per-position vocabulary distribution on positions with a gold char, per row / n_target, non-WORD rows, sum / B.
The log(p + 1e-6) of the CE is used for the probability-valued heads, so a model equal to the parent gives exactly 0.

ans_drill: Tool.loss draws drills (random result strings replacing the real ones in the teacher-forced tape and targets) from
the model's own RNG in training mode. Here ONE draw per batch (m.train_golds) gives the gold g, and the same g and batch go through
both the model and the parent, so both see the same tape and the same masks. The drill draw therefore still advances the model's
RNG stream, as the CE path does.
"""
import copy

import torch
import torch.nn.functional as F

from custom_io.models import tool as T


def frozen_copy(m):
    """The pre-mode model as a frozen reference: eval mode, requires_grad False (no dropout in this model class anyway)."""
    p = copy.deepcopy(m)
    for k in ('loss', 'load_state_dict', '_guess_lsd'):   # instance-level wrappers are not part of the reference
        p.__dict__.pop(k, None)
    p.eval()
    for q in p.parameters():
        q.requires_grad_(False)
    return p


def _kl(lpp, lpm):
    """forward KL(P || Q) over the last dim from log-probs (P = exp(lpp))."""
    return (lpp.exp() * (lpp - lpm)).sum(-1)


def _bern(ap, am):
    """KL(Bernoulli(sigmoid(ap)) || Bernoulli(sigmoid(am))) from logits."""
    p = torch.sigmoid(ap)
    return p * (F.logsigmoid(ap) - F.logsigmoid(am)) + (1 - p) * (F.logsigmoid(-ap) - F.logsigmoid(-am))


def replay_kl(m, parent, b):
    """-> (KL scalar with grad through m, dict of parts as floats). b: a collated batch of diary rows. m in train mode."""
    rows = b['rows']
    dev, B = b['prompt_ids'].device, len(rows)
    g = m.gold(rows, dev, m.train_golds(rows) if m.ans_drill else None)   # one draw, shared by both forwards
    o = m.run(b, gold=g)
    with torch.no_grad():
        po = parent.run(b, gold=g)
    eps = 1e-6
    lg = lambda p: torch.log(p + eps)
    parts = dict(op=0.0, cells=0.0, span=0.0, stop=0.0, mode=0.0, word=0.0, gen=0.0, ans=0.0)
    w_row = torch.where(g['has'], 1.0, m.w_noop)
    comm = torch.isin(g['op'], torch.tensor(T.COMM, device=dev))
    span = m.span_copy
    if span:
        Tn = b['prompt_ids'].shape[1]
        Ma, Mb, Mn, (cs, ts, ys) = m.span_gold(rows, Tn, o['le'], o['K'], g.get('rowg'))
        Ma, Mb, Mn = (torch.from_numpy(x).to(dev) for x in (Ma, Mb, Mn))
    for s, (sm, sp_) in enumerate(zip(o['steps'], po['steps'])):
        on = g['op'][:, s] > 0
        parts['op'] = parts['op'] + (_kl(F.log_softmax(sp_[0].float(), -1), F.log_softmax(sm[0].float(), -1)) * w_row).mean()
        ta, tb, cm = g['ca'][:, s], g['cb'][:, s], comm[:, s, None]
        mask = torch.cat([(ta >= 0) | (cm & (tb >= 0)), (tb >= 0) | (cm & (ta >= 0))], 1) & on[:, None]
        parts['cells'] = parts['cells'] + (_kl(lg(sp_[1]), lg(sm[1])) * mask).sum() / B
        if span:
            a, c = sm[2], sp_[2]
            ma, mb = Ma[:, s].any(-1), Mb[:, s].any(-1)
            cmr = comm[:, s]
            gate = _bern(c['ga'], a['ga']) + _bern(c['gb'], a['gb'])
            pa = on & (ma | (cmr & mb))
            pb = on & (mb | (cmr & ma))
            ptr = lambda k: _kl(F.log_softmax(c[k], -1), F.log_softmax(a[k], -1))
            parts['span'] = parts['span'] + ((gate * on).sum() + (ptr('la') * pa).sum() + (ptr('lb') * pb).sum()) / B
    if span and cs:
        ct, tt = torch.tensor(cs, device=dev), torch.tensor(ts, device=dev)
        with torch.no_grad():
            lp = parent.stop_logit(ct, tt)
        parts['stop'] = _bern(lp, m.stop_logit(ct, tt)).mean()
    parts['mode'] = _kl(F.log_softmax(po['lmode'].float(), -1), F.log_softmax(o['lmode'].float(), -1)).mean()
    parts['word'] = (_kl(F.log_softmax(po['lword'], -1), F.log_softmax(o['lword'], -1)) * (g['mode'] == 1)).sum() / B
    with torch.no_grad():
        pp, _ = parent.gen_copy(po['R'], po['X'], po['xm'], po['ids'])
    pm, _ = m.gen_copy(o['R'], o['X'], o['xm'], o['ids'])
    tg = g['gen']
    n_t = (tg >= 0).sum(1).clamp(min=1)
    parts['gen'] = (((_kl(lg(pp), lg(pm)) * (tg >= 0)).sum(1) / n_t) * (g['mode'] != 1)).sum() / B
    if span:
        keys = lambda mod, oo: mod.span_keys(oo['X'], Tn, oo['le'], oo['xm'])
        with torch.no_grad():
            lnp = parent.ptr(po['qn'], keys(parent, po), po['xm'])
        lnm = m.ptr(o['qn'], keys(m, o), o['xm'])
        sel = (g['mode'] == 0) & Mn.any(-1)
        parts['ans'] = (_kl(F.log_softmax(lnp, -1), F.log_softmax(lnm, -1)) * sel).sum() / B
    total = sum(parts.values())
    return total, {k: float(torch.as_tensor(v).detach()) for k, v in parts.items()}


def wrap(m, parent, weight, kls):
    """Instance-level loss for arm KL, wrapping the m.loss in force now. Batches in training mode with grad holding both diary and
    new rows: (n_new/B) * plain loss(new rows) + (n_rep/B) * weight * KL(parent || m)(diary rows); every replay KL is appended to
    `kls`. Anything else: the plain loss. A tuple result keeps its shape (the aux dict gets 'replay_kl')."""
    plain = m.loss

    def part(b, idx):
        t = torch.tensor(idx)
        return {k: (v[t] if torch.is_tensor(v) else [v[i] for i in idx]) for k, v in b.items()}

    def loss(b):
        rows = b['rows']
        B = len(rows)
        ri = [i for i, r in enumerate(rows) if r.get('source') == 'diary']
        rs = set(ri)
        ni = [i for i in range(B) if i not in rs]
        if not m.training or not torch.is_grad_enabled() or not ri or not ni:
            return plain(b)
        w_rep, w_new = len(ri) / B, len(ni) / B
        out_n = plain(part(b, ni))
        kl, parts = replay_kl(m, parent, part(b, ri))
        kls.append(float(kl.detach()))
        if isinstance(out_n, tuple):
            aux = out_n[1]
            if isinstance(aux, dict):
                aux = dict(aux, replay_kl=float(kl.detach()))
            return (w_new * out_n[0] + w_rep * weight * kl, aux) + tuple(out_n[2:])
        return w_new * out_n + w_rep * weight * kl
    return loss
