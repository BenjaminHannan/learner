#!/usr/bin/env python3
"""relnet (2026-09-27): GPT-6 Pro's design 3, the persistent relation-state network, as a drop-in for the loop.

Source: reviews/gpt6pro-brain-reasoner-contenders-REPLY-2026-09-27.md, section 2, design 3. Per round t:
  r_ij <- GRU_e(r_ij, [P_h h_i, P_h h_j, P_v (v_i - v_j), p_ij])        every directed pair, width q = 64
  m_i  =  (1/N) sum_j (U r_ij) * (V h_j)
  h~_i =  GRU_n(h_i, [x_i, m_i])
  h_i  =  LN_state(h~_i + MLP(LN(h~_i)))                                 MLP hidden 1,576 (GPT's sizing)
v_i = x_i = token + slot embedding (the unchanged input symbol). p_ij = learned embedding of the row and column
offsets, clipped at 4 like the loop. No kind label, no constraint graph, no maze adjacency, no carry rules.
r starts at zero for each puzzle and carries across rounds. Stop head: the loop's (Linear on the pooled read-out).
Two norms GPT did not write (disclosed): LN before the MLP and a state LN after the residual, as the loop has
(ln_state); without them the residual state is unbounded across 48 rounds.

The GRU input projection of GRU_e is linear in its four concatenated parts, so it is computed part by part
(a_i + b_j + c_ij) instead of materialising the [N, N, 4q] input; the symbol-difference, position and bias parts do
not change between rounds, so they are computed once per puzzle. Same function, same weights, less memory and time.

Same interface as scripts/claude_xfer1_net.py's loop (embed/read/loop_train/loop_rounds, arm "loop"), so its
train_loss and practice recipe apply unchanged.

  python -B scripts/claude_relnet_net.py checks --out artifacts/claude-relnet-20260927/checks.json
  python -B scripts/claude_relnet_net.py cost1 --net relnet|loop --size H --batch B   (one cost row, own process)
"""
from __future__ import annotations

import argparse
import json
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402  (vocabulary)

D, Q, MLP_H, CLIP = 256, 64, 1576, 4


class GRUe(nn.Module):
    """GRU over pair states; input = [P_h h_i, P_h h_j, P_v(v_i - v_j), p_ij], each width q."""

    def __init__(self, q):
        super().__init__()
        self.wi, self.wj, self.wv, self.wp = (nn.Linear(q, 3 * q, bias=False) for _ in range(4))
        self.bi = nn.Parameter(torch.zeros(3 * q))
        self.hh = nn.Linear(q, 3 * q)
        self.q = q

    def const(self, pv, pos):
        """the round-invariant parts of the input gates: symbol difference, position and bias"""
        v = self.wv(pv)
        return v + self.bi, -v, self.wp(pos)

    def forward(self, r, ph, const):
        # r [B,N,N,q]; ph [B,N,q]; const from self.const (pv [B,N,q], pos [N,N,q])
        a0, b0, c = const
        gi = (self.wi(ph) + a0)[:, :, None] + (self.wj(ph) + b0)[:, None, :] + c
        gh = self.hh(r)
        q = self.q
        rg = torch.sigmoid(gi[..., :q] + gh[..., :q])
        zg = torch.sigmoid(gi[..., q:2 * q] + gh[..., q:2 * q])
        n = torch.tanh(gi[..., 2 * q:] + rg * gh[..., 2 * q:])
        return (1 - zg) * n + zg * r


class GRUn(nn.Module):
    def __init__(self, din, d):
        super().__init__()
        self.ih, self.hh, self.d = nn.Linear(din, 3 * d), nn.Linear(d, 3 * d), d

    def forward(self, h, x):
        gi, gh, d = self.ih(x), self.hh(h), self.d
        rg = torch.sigmoid(gi[..., :d] + gh[..., :d])
        zg = torch.sigmoid(gi[..., d:2 * d] + gh[..., d:2 * d])
        n = torch.tanh(gi[..., 2 * d:] + rg * gh[..., 2 * d:])
        return (1 - zg) * n + zg * h


class RelNet(nn.Module):
    def __init__(self, d=D, q=Q, mlp_h=MLP_H):
        super().__init__()
        self.arm, self.d, self.q = "loop", d, q
        self.tok = nn.Embedding(E.VOCAB, d)
        self.slot = nn.Embedding(2, d)
        self.pr = nn.Embedding(2 * CLIP + 1, q)
        self.pc = nn.Embedding(2 * CLIP + 1, q)
        self.P_h = nn.Linear(d, q, bias=False)
        self.P_v = nn.Linear(d, q, bias=False)
        self.gru_e = GRUe(q)
        self.U = nn.Linear(q, d, bias=False)
        self.V = nn.Linear(d, d, bias=False)
        self.gru_n = GRUn(2 * d, d)
        self.ln_mlp = nn.LayerNorm(d)
        self.mlp = nn.Sequential(nn.Linear(d, mlp_h), nn.GELU(), nn.Linear(mlp_h, d))
        self.ln_state = nn.LayerNorm(d)
        self.ln_out = nn.LayerNorm(d)
        self.head = nn.Linear(d, E.VOCAB)
        self.halt = nn.Linear(d, 1)

    @staticmethod
    def offsets(H, W, device):
        r = torch.arange(H, device=device).repeat_interleave(W)
        c = torch.arange(W, device=device).repeat(H)
        dr = (r[:, None] - r[None, :]).clamp(-CLIP, CLIP) + CLIP
        dc = (c[:, None] - c[None, :]).clamp(-CLIP, CLIP) + CLIP
        return dr, dc

    def embed(self, tokens, slot):
        B, H, W = tokens.shape
        return self.tok(tokens.view(B, -1)) + self.slot(slot.view(B, -1)), self.offsets(H, W, tokens.device)

    def init_state(self, e):
        B, N, _ = e.shape
        return torch.zeros_like(e), e.new_zeros(B, N, N, self.q)

    def step(self, state, e, const):
        h, r = state
        N = h.shape[1]
        r = self.gru_e(r, self.P_h(h), const)
        m = torch.einsum("bijl,kl,bjk->bik", r, self.U.weight, self.V(h)) / N
        ht = self.gru_n(h, torch.cat([e, m], -1))
        return self.ln_state(ht + self.mlp(self.ln_mlp(ht))), r

    def read(self, h):
        z = self.ln_out(h)
        return self.head(z), self.halt(z.mean(1)).squeeze(-1)

    def _const(self, e, dr, dc):
        return self.gru_e.const(self.P_v(e), self.pr(dr) + self.pc(dc))

    def loop_train(self, tokens, slot, n_free, n_grad):
        e, (dr, dc) = self.embed(tokens, slot)
        state = self.init_state(e)
        with torch.no_grad():
            e0 = e.detach()
            c0 = self._const(e0, dr, dc)
            for _ in range(n_free):
                state = self.step(state, e0, c0)
        state = (state[0].detach(), state[1].detach())
        c, outs = self._const(e, dr, dc), []
        for _ in range(n_grad):
            state = self.step(state, e, c)
            outs.append(self.read(state[0]))
        return outs

    @torch.no_grad()
    def loop_rounds(self, tokens, slot, n):
        e, (dr, dc) = self.embed(tokens, slot)
        state, c = self.init_state(e), self._const(e, dr, dc)
        preds, qs = [], []
        for _ in range(n):
            state = self.step(state, e, c)
            lg, q = self.read(state[0])
            preds.append(lg.argmax(-1))
            qs.append(torch.sigmoid(q.float()))
        return torch.stack(preds, 1), torch.stack(qs, 1)


# ---------------- checks ----------------
def count(m):
    return sum(p.numel() for p in m.parameters())


def loop_net():
    """the 358e small dense loop (2 x 256, 8 heads) that the relation net must match"""
    import claude_rsn358e_moe as MOE
    return MOE.make_net("dense", "small")


def weight_table(rel, loop):
    groups = {
        "embeddings (token, slot, kind, position)": (["tok", "slot", "env", "pr", "pc"], []),
        "reasoning core": (["blocks", "P_h", "P_v", "gru_e", "U", "V", "gru_n", "ln_mlp", "mlp", "ln_state"], []),
        "answer head + read-out norm": (["head", "ln_out"], []),
        "stop head": (["halt"], []),
    }
    rows = []
    for name, (keys, _) in groups.items():
        def part(net):
            return sum(p.numel() for n, p in net.named_parameters() if n.split(".")[0] in keys)
        rows.append((name, part(rel), part(loop)))
    detail = {n: sum(p.numel() for pn, p in rel.named_parameters() if pn.split(".")[0] == n)
              for n, _ in rel.named_children()}
    return rows, detail


def grad_check(net, H=5, W=5, B=4):
    torch.manual_seed(0)
    t = torch.randint(0, E.VOCAB, (B, H, W))
    s = torch.randint(0, 2, (B, H, W))
    y = torch.randint(0, E.VOCAB, (B, H, W))
    net.zero_grad()
    outs = net.loop_train(t, s, 2, 3)
    loss = 0
    for lg, q in outs:
        loss = loss + nn.functional.cross_entropy(lg.reshape(-1, lg.shape[-1]), y.view(-1)) + q.pow(2).mean()
    loss.backward()
    res = {}
    for n, p in net.named_parameters():
        g = p.grad
        res[n] = 0.0 if g is None else float(g.abs().sum())
    mats = {n: v for n, v in res.items() if dict(net.named_parameters())[n].dim() >= 2}
    return res, [n for n, v in mats.items() if v == 0.0], len(mats)


def time_step(net, H, W, B, n_free, n_grad, reps=2):
    torch.manual_seed(0)
    t = torch.randint(0, E.VOCAB, (B, H, W))
    s = torch.randint(0, 2, (B, H, W))
    y = torch.randint(0, E.VOCAB, (B, H, W))
    opt = torch.optim.AdamW(net.parameters(), lr=1e-4)
    fwd = (lambda: net.loop_train(t, s, n_free, n_grad))
    if not hasattr(net, "gru_e"):   # the 358 loop takes a kind id
        env = torch.zeros(B, dtype=torch.long)
        fwd = (lambda: net.loop_train(t, s, env, n_free, n_grad))
    times = []
    for _ in range(reps + 1):
        t0 = time.perf_counter()
        outs = fwd()
        loss = sum(nn.functional.cross_entropy(lg.reshape(-1, lg.shape[-1]), y.view(-1)) for lg, _ in outs)
        opt.zero_grad()
        loss.backward()
        opt.step()
        times.append(time.perf_counter() - t0)
    return min(times[1:])


def infer_time(net, H, W, B, rounds):
    t = torch.randint(0, E.VOCAB, (B, H, W))
    s = torch.randint(0, 2, (B, H, W))
    t0 = time.perf_counter()
    if hasattr(net, "gru_e"):
        net.loop_rounds(t, s, rounds)
    else:
        net.loop_rounds(t, s, torch.zeros(B, dtype=torch.long), rounds)
    return time.perf_counter() - t0


def checks(out):
    torch.set_num_threads(4)
    rel, loop = RelNet(), loop_net()
    rows, detail = weight_table(rel, loop)
    n_rel, n_loop = count(rel), count(loop)
    grads, zero_mats, n_mats = grad_check(rel)
    rep = dict(torch=torch.__version__, cpu=platform.processor() or platform.machine(), threads=4, dtype="fp32, no autocast",
               weights=dict(relnet=n_rel, loop=n_loop, diff_pct=round(100 * (n_rel - n_loop) / n_loop, 3),
                            table=rows, relnet_parts=detail),
               grad_check=dict(matrices=n_mats, zero_grad_matrices=zero_mats,
                               zero_grad_any=[n for n, v in grads.items() if v == 0.0]),
               cost=[])
    print(json.dumps(rep["weights"], indent=1), json.dumps(rep["grad_check"], indent=1), flush=True)
    # worst-case training step (16 rounds, gradient through 6) and 48-round inference, per example; each row in a
    # fresh process so peak memory belongs to that net and size alone
    for H, B in [(5, 8), (7, 32), (9, 4), (11, 2)]:
        for name in ["relnet", "loop"]:
            cmd = [sys.executable, "-B", __file__, "cost1", "--net", name, "--size", str(H), "--batch", str(B)]
            row = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1])
            rep["cost"].append(row)
            print(row, flush=True)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(rep, indent=1))


def cost1(name, H, B):
    torch.set_num_threads(4)
    net = RelNet() if name == "relnet" else loop_net()
    base = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    ti = infer_time(net, H, H, B, 48)
    infer_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    ts = time_step(net, H, H, B, 10, 6)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(json.dumps(dict(net=name, size=f"{H}x{H}", batch=B, train_step_s=round(ts, 3),
                          train_s_per_example=round(ts / B, 4), infer48_s_per_example=round(ti / B, 4),
                          rss_after_build_mb=round(base), infer_peak_rss_mb=round(infer_peak),
                          train_peak_rss_mb=round(peak))))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["checks", "cost1"])
    ap.add_argument("--out", default="artifacts/claude-relnet-20260927/checks.json")
    ap.add_argument("--net", default="relnet")
    ap.add_argument("--size", type=int, default=5)
    ap.add_argument("--batch", type=int, default=8)
    a = ap.parse_args()
    if a.cmd == "checks":
        checks(a.out)
    else:
        cost1(a.net, a.size, a.batch)
