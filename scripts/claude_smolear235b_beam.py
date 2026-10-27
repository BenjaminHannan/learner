#!/usr/bin/env python3
"""Exp 235b -- k-best decoding + the write gate for the UNCHANGED 235 v3 ear.

Pieces (plain torch, no transformers):
- greedy_scored(): the same greedy reading as 235 (batch-1 CUDA graph from
  claude_smolear235_model.GraphDecoder on GPU, eager KV-cache on CPU), plus its
  summed log-prob.
- BeamGraph / beam_eager(): k-best beam search (k=4), scores = summed token
  log-probs of the whole output (lines + <|im_end|>), no length normalisation.
  Exact stopping rule: stop once k finished hypotheses exist and the best alive
  one scores below the k-th finished one (log-probs only fall).
- gate(): applied to the brake's kept frames of the GREEDY reading (so the gate
  can only remove frames the 235 arm would save; it never adds one).
    (a) question guard: turn ends in "?" (after trailing space/quotes/brackets)
        -> no TEACH saved (status GUARD_Q); or some other top-k decode within
        tau of the greedy one contains an ASK frame -> UNSURE_ASK.
    (b) margin gate: for each TEACH frame f, competitors = top-k decodes
        (other than the greedy text) whose normalised frame set does NOT
        contain f (i.e. f is changed in act/subject/relation/value, or gone).
        Only VALID readings compete: a decode whose frames the brake would drop in
        any part (non-span subject/value, relation not in the table, malformed) is
        ignored; a NONE decode is valid. Duplicate texts (different token paths):
        the greedy lp is the best one among them.
        margin = lp(greedy) - max lp(competitor); no competitor in the top-k ->
        margin = +inf. margin < tau -> UNSURE (not saved), else SAVE.
  Frame normalisation for "same frame" = the 235 scorer's rules (case, edge
  punctuation, leading the/a/an, first-person subjects one entity, relation by
  canonical table name).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_model as E  # noqa: E402
import claude_smolear235_score as S  # noqa: E402  (norm helpers only)

K = 4


def _stops(tok):
    return {tok.im_end, tok.eos}


# ------------------------------------------------------------------ greedy + score
@torch.no_grad()
def greedy_scored(m, tok, turn, gd=None, max_new=64):
    """Same tokens as E.GraphDecoder.generate / E.generate; also returns summed log-prob
    (including the stop token)."""
    dev = next(m.parameters()).device
    ids = torch.tensor([tok.enc(E.prompt_text(turn))], device=dev)
    T = ids.shape[1]
    caches = [dict() for _ in m.layers]
    logits = m(ids, caches=caches, start=0)[0, -1]
    use_graph = gd is not None and T + max_new < gd.L
    if use_graph:
        for i, cch in enumerate(caches):
            gd.kc[i][:, :, :T].copy_(cch["k"])
            gd.vc[i][:, :, :T].copy_(cch["v"])
    out, lp, pos = [], 0.0, T
    stops = _stops(tok)
    for _ in range(max_new + 1):
        ls = F.log_softmax(logits.float(), -1)
        nxt = int(logits.argmax())
        lp += float(ls[nxt])
        if nxt in stops or len(out) >= max_new:
            break
        out.append(nxt)
        if use_graph:
            gd.tok_in.fill_(nxt)
            gd.pos.fill_(pos)
            gd.g.replay()
            logits = gd.out
        else:
            logits = m(torch.tensor([[nxt]], device=dev), caches=caches, start=pos)[0, -1]
        pos += 1
    return tok.dec(out).strip(), lp, out


# ------------------------------------------------------------------ beam search core
def _beam_loop(first_logp, step, tok, k=K, max_new=64):
    """first_logp: (V,) float log-probs after the prompt.
    step(tokens LongTensor(k), parents LongTensor(k), pos_offset int) -> (k,V) float log-probs.
    Returns [(token_list, score)] best-first, len <= k."""
    stops = _stops(tok)
    finished = []
    sc, ix = torch.topk(first_logp, 2 * k)
    alive = []
    for s, t in zip(sc.tolist(), ix.tolist()):
        if t in stops:
            finished.append(([], s))
        elif len(alive) < k:
            alive.append(([t], s, 0))
    parents = [a[2] for a in alive]
    for t in range(max_new):
        if len(finished) >= k:
            kth = sorted(s for _, s in finished)[-k]
            if alive[0][1] < kth:
                break
        toks = torch.tensor([a[0][-1] for a in alive], dtype=torch.long)
        logp = step(toks, torch.tensor(parents, dtype=torch.long), t)  # (k,V)
        base = torch.tensor([a[1] for a in alive], dtype=torch.float32, device=logp.device)
        cand = (base[:, None] + logp).view(-1)
        csc, cix = torch.topk(cand, 2 * k)
        V = logp.shape[1]
        new = []
        for s, i in zip(csc.tolist(), cix.tolist()):
            row, tk = divmod(i, V)
            if tk in stops:
                finished.append((alive[row][0], s))
            elif len(new) < k:
                new.append((alive[row][0] + [tk], s, row))
        alive = new
        parents = [a[2] for a in alive]
    else:
        finished.extend((a[0], a[1]) for a in alive)
    finished.sort(key=lambda x: -x[1])
    return finished[:k]


class BeamGraph:
    """Batch-k CUDA-graph decode step with an in-graph KV-cache reorder by parent index."""

    def __init__(self, model, tok, k=K, lmax=256):
        self.m, self.tok, self.k, self.L = model, tok, k, lmax
        p = next(model.parameters())
        dev, dt = p.device, p.dtype
        c = model.c
        self.hd = c["hidden"] // c["heads"]
        self.kc = [torch.zeros(k, c["kv_heads"], lmax, self.hd, device=dev, dtype=dt) for _ in model.layers]
        self.vc = [torch.zeros_like(x) for x in self.kc]
        self.tok_in = torch.zeros(k, 1, dtype=torch.long, device=dev)
        self.parent = torch.arange(k, dtype=torch.long, device=dev)
        self.pos = torch.zeros(1, dtype=torch.long, device=dev)
        cos, sin = model.rope(lmax, dev, dt)
        self.cos, self.sin = cos[:lmax].contiguous(), sin[:lmax].contiguous()
        self.ar = torch.arange(lmax, device=dev)
        s = torch.cuda.Stream()
        s.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(s), torch.no_grad():
            for _ in range(3):
                self.out = self._step()
        torch.cuda.current_stream().wait_stream(s)
        self.g = torch.cuda.CUDAGraph()
        with torch.cuda.graph(self.g), torch.no_grad():
            self.out = self._step()

    def _step(self):
        m, k = self.m, self.k
        for i in range(len(m.layers)):
            self.kc[i].copy_(self.kc[i].index_select(0, self.parent))
            self.vc[i].copy_(self.vc[i].index_select(0, self.parent))
        x = m.embed_tokens(self.tok_in)
        cos = self.cos.index_select(0, self.pos)[None, None]
        sin = self.sin.index_select(0, self.pos)[None, None]
        mask = (self.ar <= self.pos)[None, None, None, :]
        for i, layer in enumerate(m.layers):
            a = layer.self_attn
            h = layer.input_layernorm(x)
            q = a.q_proj(h).view(k, 1, a.h, a.hd).transpose(1, 2)
            kk = a.k_proj(h).view(k, 1, a.kv, a.hd).transpose(1, 2)
            v = a.v_proj(h).view(k, 1, a.kv, a.hd).transpose(1, 2)
            q = q * cos + E.rot_half(q) * sin
            kk = kk * cos + E.rot_half(kk) * sin
            self.kc[i].index_copy_(2, self.pos, kk)
            self.vc[i].index_copy_(2, self.pos, v)
            rep = a.h // a.kv
            Kx = self.kc[i].repeat_interleave(rep, 1)
            Vx = self.vc[i].repeat_interleave(rep, 1)
            o = F.scaled_dot_product_attention(q, Kx, Vx, attn_mask=mask)
            x = x + a.o_proj(o.transpose(1, 2).reshape(k, 1, -1))
            x = x + layer.mlp(layer.post_attention_layernorm(x))
        x = m.norm(x)
        return F.log_softmax(F.linear(x, m.embed_tokens.weight)[:, -1].float(), -1)

    @torch.no_grad()
    def beams(self, turn, max_new=64):
        m, tok = self.m, self.tok
        dev = self.tok_in.device
        ids = torch.tensor([tok.enc(E.prompt_text(turn))], device=dev)
        T = ids.shape[1]
        if T + max_new >= self.L:
            return beam_eager(m, tok, turn, max_new=max_new)
        caches = [dict() for _ in m.layers]
        logits = m(ids, caches=caches, start=0)[0, -1]
        for i, cch in enumerate(caches):
            self.kc[i][:, :, :T].copy_(cch["k"].expand(self.k, -1, -1, -1))
            self.vc[i][:, :, :T].copy_(cch["v"].expand(self.k, -1, -1, -1))

        def step(toks, parents, t):
            n = toks.shape[0]
            tk = torch.zeros(self.k, dtype=torch.long)
            pr = torch.arange(self.k, dtype=torch.long)
            tk[:n], pr[:n] = toks, parents
            self.tok_in.copy_(tk.view(-1, 1))
            self.parent.copy_(pr)
            self.pos.fill_(T + t)
            self.g.replay()
            return self.out[:n]

        res = _beam_loop(F.log_softmax(logits.float(), -1), step, tok, k=self.k, max_new=max_new)
        return [(tok.dec(t).strip(), s) for t, s in res]


@torch.no_grad()
def beam_eager(m, tok, turn, k=K, max_new=64):
    dev = next(m.parameters()).device
    ids = torch.tensor([tok.enc(E.prompt_text(turn))], device=dev)
    T = ids.shape[1]
    caches = [dict() for _ in m.layers]
    logits = m(ids, caches=caches, start=0)[0, -1]
    state = {"first": True}

    def step(toks, parents, t):
        n = toks.shape[0]
        for c in caches:
            if state["first"]:
                c["k"] = c["k"].expand(n, -1, -1, -1).contiguous()
                c["v"] = c["v"].expand(n, -1, -1, -1).contiguous()
            else:
                c["k"] = c["k"].index_select(0, parents.to(dev))
                c["v"] = c["v"].index_select(0, parents.to(dev))
        state["first"] = False
        lg = m(toks.view(-1, 1).to(dev), caches=caches, start=T + t)[:, -1]
        return F.log_softmax(lg.float(), -1)

    res = _beam_loop(F.log_softmax(logits.float(), -1), step, tok, k=k, max_new=max_new)
    return [(tok.dec(t).strip(), s) for t, s in res]


# ------------------------------------------------------------------ gate
def fkey(f):
    if f["act"] == "TEACH":
        return ("TEACH", S.norm_subj(f["subject"]), E.canon_rel(f["relation"]) or S.rkey(f["relation"]),
                S.norm_val(f["value"]))
    if f["act"] == "ASK":
        return ("ASK", S.norm_subj(f["subject"]),
                tuple(E.canon_rel(r) or S.rkey(r) for r in f["relation"]))
    return ("BAD", f.get("raw", ""))


def ends_q(turn):
    return turn.rstrip().rstrip("\"')]}").rstrip().endswith("?")


def gate(turn, greedy_text, greedy_lp, beams, tau):
    """Returns dict(kept_brake, dropped_brake, saved, unsure, guard, asks, margins).
    beams: [(text, lp)] best-first (top-k). The greedy lp is taken from the beam list when
    the greedy text is in it (same numerics as the competitors)."""
    frames = E.parse_frames(greedy_text)
    kept, dropped = E.brake(frames, turn)
    same = [lp for text, lp in beams if text.strip() == greedy_text.strip()]
    g_lp = max(same) if same else greedy_lp
    others = []
    for text, lp in beams:
        if text.strip() == greedy_text.strip():
            continue
        fr = E.parse_frames(text)
        bk, bd = E.brake(fr, turn)
        if bd:  # a reading the brake would reject can never be saved: not a competitor
            continue
        others.append((text, lp, {fkey(f) for f in fr}))
    qmark = ends_q(turn)
    ask_near = any(lp >= g_lp - tau and any(k[0] == "ASK" for k in keys) for _, lp, keys in others)
    saved, unsure, guard, asks, margins = [], [], [], [], []
    for f in kept:
        if f["act"] == "ASK":
            asks.append(f)
            saved.append(f)
            continue
        k = fkey(f)
        comp = [lp for _, lp, keys in others if k not in keys]
        margin = (g_lp - max(comp)) if comp else math.inf
        margins.append(margin)
        if qmark:
            guard.append(dict(f, why="GUARD_Q", margin=margin))
        elif ask_near:
            unsure.append(dict(f, why="UNSURE_ASK", margin=margin))
        elif margin < tau:
            unsure.append(dict(f, why="UNSURE", margin=margin))
        else:
            saved.append(f)
    return dict(kept_brake=kept, dropped_brake=[(f, w) for f, w in dropped], saved=saved,
                unsure=unsure, guard=guard, margins=margins, greedy_lp=g_lp)
