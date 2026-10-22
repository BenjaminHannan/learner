"""Live anchor of internal states on the replay rows to the frozen pre-subject parent (constants "anchor": "state"; fullrun.py).

The diary rows are the model's own old questions. On every training update, for the replay rows of the batch, the model's internal
states are pulled toward the frozen parent's states on exactly the same inputs:

    L_anchor(row) = sum over the row's non-padded prompt positions of mean_d(((h - h_parent) / sigma_reader)^2)
                    + sum over thinker rounds r of mean_d(((s_r - s_r_parent) / sigma_state)^2)
    loss = plain loss on the whole batch (unchanged) + lambda * (n_rep / B) * mean over replay rows of L_anchor

Which tensors (custom_io/models/tool.py Tool.run):
- h: the reader output X [B, T, d] (run(): X, xm = self.read(batch, talker=True)), at every position where prompt_mask is True.
- s_r: the thinker state Z [B, 17, d] after round r (the `each` callback of run() fires after every round with Z): the 8 control tokens
  then the 9 workspace tokens (registers, which also serve as the talker's R), flattened to one 17*d vector. Rounds are matched by
  index: every row runs all n_loops rounds (the loop count is the same for every row and for model and parent), round r of the model
  against round r of the parent. The tape (call results) is not a state: it is teacher-forced and identical in both (same gold).
sigma_reader[d] (256) and sigma_state[17*d] (4352) are per-dimension standard deviations of the parent's own vectors over all the
diary rows at the subject's first night (clamped at 1e-6), so every dimension counts in units of its own natural spread.

No second model forward: the states are taken from the forward that computes the CE (run() is wrapped at instance level for the
duration of the plain loss call, adding an `each` callback that keeps Z and X, and keeping the gold the loss drew). The only extra
work is the parent's no-grad forward on the replay rows (with the same gold, so one shared ans_drill draw) and the anchor arithmetic.
If klreplay is also on, the replay rows' forward is the KL's (its m.run call); the parent then runs once more for the anchor.
"""
import torch

from custom_io.data import Dataset, collate, to_device


def _states(model, batch, gold):
    """Run `model` on batch with gold; -> (X [B,T,d], xm [B,T], Z [R, B, 17*d]) (grad as the model's mode allows)."""
    zs, kept = [], {}

    def each(t, st):
        zs.append(st['Z'].float().flatten(1))
        kept.setdefault('X', st['X'])
        kept.setdefault('xm', st['xm'])
    model.run(batch, gold=gold, each=each)
    return kept['X'].float(), kept['xm'], torch.stack(zs)


def collect_sigmas(parent, rows, bs=64):
    """Per-dimension std of the parent's reader outputs (non-padded positions) and thinker states (every round) over `rows`.
    -> (sigma_reader [d], sigma_state [17*d], info dict). Eval, no grad, teacher-forced on the rows' own answers (no drills)."""
    parent.eval()
    ds = Dataset(rows, parent.vocab)
    acc = {}
    nrounds = 0
    with torch.no_grad():
        for s in range(0, len(rows), bs):
            b = to_device(collate([ds[i] for i in range(s, min(s + bs, len(rows)))]), 'cpu')
            g = parent.gold(b['rows'], b['prompt_ids'].device)
            X, xm, Z = _states(parent, b, g)
            nrounds += Z.shape[0] * Z.shape[1]
            for k, v in (('r', X[xm]), ('s', Z.reshape(-1, Z.shape[-1]))):
                v = v.double()
                a = acc.setdefault(k, [0, torch.zeros(v.shape[1], dtype=torch.double), torch.zeros(v.shape[1], dtype=torch.double)])
                a[0] += len(v)
                a[1] += v.sum(0)
                a[2] += (v * v).sum(0)
    sig = {}
    for k, (n, s1, s2) in acc.items():
        var = (s2 / n - (s1 / n) ** 2).clamp(min=0)
        sig[k] = var.sqrt().float().clamp(min=1e-6)
    info = dict(rows=len(rows), reader_vectors=acc['r'][0], state_vectors=acc['s'][0], reader_dim=len(sig['r']), state_dim=len(sig['s']),
                mean_rounds_per_row=nrounds / len(rows), sigma_reader_mean=float(sig['r'].mean()), sigma_reader_min=float(sig['r'].min()),
                sigma_state_mean=float(sig['s'].mean()), sigma_state_min=float(sig['s'].min()))
    return sig['r'], sig['s'], info


def l_anchor(parent, sig_r, sig_s, Xm, xm, Zm, batch, gold):
    """Per-row L_anchor [n] (grad through Xm, Zm). Xm [n,T,d], xm [n,T], Zm [R,n,17d] are the model's states on `batch`
    (n rows) taken from its own forward; the parent runs on the same batch and gold, no grad."""
    with torch.no_grad():
        Xp, xmp, Zp = _states(parent, batch, gold)
    assert torch.equal(xm, xmp) and Zm.shape == Zp.shape, (Zm.shape, Zp.shape)
    pos = (((Xm - Xp) / sig_r) ** 2).mean(-1) * xm            # [n, T]
    rnd = (((Zm - Zp) / sig_s) ** 2).mean(-1)                 # [R, n]
    return pos.sum(1) + rnd.sum(0)


def _part(b, idx):
    t = torch.tensor(idx)
    return {k: (v[t] if torch.is_tensor(v) else [v[i] for i in idx]) for k, v in b.items()}


def wrap(m, parent, sig_r, sig_s, lam, log):
    """Instance-level loss for the anchor, wrapping the m.loss in force now (plain, or klreplay's). Training batches with grad holding both
    diary and new rows: plain(b) as today + lam * (n_rep/B) * mean over replay rows of L_anchor; each update's mean L_anchor (unweighted)
    is appended to `log`. Anything else: the plain loss. A tuple result keeps its shape (aux dict gets 'anchor')."""
    plain = m.loss

    def loss(b):
        rows = b['rows']
        B = len(rows)
        ri = [i for i, r in enumerate(rows) if r.get('source') == 'diary']
        if not m.training or not torch.is_grad_enabled() or not ri or len(ri) == B:
            return plain(b)
        caps = []
        prev = m.__dict__.get('run')
        orig = m.run

        def run(batch, *a, **k):
            assert 'gold' in k and k.get('each') is None, 'the anchor needs run(batch, gold=g) with no each callback'
            zs, kept = [], {}

            def each(t, st):
                zs.append(st['Z'].float().flatten(1))
                kept.setdefault('X', st['X'])
                kept.setdefault('xm', st['xm'])
            o = orig(batch, *a, each=each, **k)
            caps.append((batch, k['gold'], kept['X'].float(), kept['xm'], torch.stack(zs)))
            return o
        m.run = run
        try:
            out = plain(b)
        finally:
            if prev is None:
                m.__dict__.pop('run', None)
            else:
                m.__dict__['run'] = prev
        hit = [(c, [i for i, r in enumerate(c[0]['rows']) if r.get('source') == 'diary']) for c in caps]
        hit = [(c, jj) for c, jj in hit if jj]
        assert len(hit) == 1, 'expected exactly one forward holding the replay rows, got %d' % len(hit)
        (cb, cg, X, xm, Z), jj = hit[0]
        sub = _part(cb, jj)
        gold = parent.gold(sub['rows'], sub['prompt_ids'].device, [cg['rowg'][i] for i in jj])
        la = l_anchor(parent, sig_r, sig_s, X[jj], xm[jj], Z[:, jj], sub, gold)
        lm = la.mean()
        log.append(float(lm.detach()))
        extra = lam * (len(ri) / B) * lm
        if isinstance(out, tuple):
            aux = out[1]
            if isinstance(aux, dict):
                aux = dict(aux, anchor=float(lm.detach()))
            return (out[0] + extra, aux) + tuple(out[2:])
        return out + extra
    return loss
