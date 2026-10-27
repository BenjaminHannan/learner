#!/usr/bin/env python3
"""Exp 235 -- SmolLM2-360M-Instruct as the EAR (turn -> thought frames).

Plain-torch Llama implementation (no `transformers`: BensPC's transformers
install fails its huggingface-hub version check and we install nothing).
Loads the stock safetensors + tokenizer.json, runs greedy decoding with a KV
cache, parses frame lines, and applies the SAFETY BRAKE (plain software).

Frame lines (one per frame, nothing else):
    TEACH | subject | relation | value
    ASK | subject | rel1 [> rel2 ...]
    NONE
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

REPO = Path(__file__).resolve().parent.parent
TABLE_PATH = REPO / "artifacts/claude-relationtable-20260922/relation_table_v1.json"

CFG = dict(hidden=960, inter=2560, layers=32, heads=15, kv_heads=5,
           vocab=49152, eps=1e-5, theta=100000.0)
IM_START, IM_END = "<|im_start|>", "<|im_end|>"
SYSTEM = ("Convert the user's chat turn into memory frames. One line per frame: "
          "TEACH | subject | relation | value, or ASK | subject | relation "
          "(chains: rel1 > rel2), or NONE.")


# ---------------------------------------------------------------- model
class RMSNorm(nn.Module):
    def __init__(self, d, eps):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(d))
        self.eps = eps

    def forward(self, x):
        dt = x.dtype
        x = x.float()
        x = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return self.weight * x.to(dt)


def rope_tables(n, hd, theta, device):
    inv = 1.0 / (theta ** (torch.arange(0, hd, 2, device=device).float() / hd))
    t = torch.arange(n, device=device).float()
    f = torch.outer(t, inv)
    emb = torch.cat([f, f], -1)
    return emb.cos(), emb.sin()


def rot_half(x):
    a, b = x.chunk(2, -1)
    return torch.cat([-b, a], -1)


class Attn(nn.Module):
    def __init__(self, c):
        super().__init__()
        d, h, kv = c["hidden"], c["heads"], c["kv_heads"]
        self.h, self.kv, self.hd = h, kv, d // h
        self.q_proj = nn.Linear(d, h * self.hd, bias=False)
        self.k_proj = nn.Linear(d, kv * self.hd, bias=False)
        self.v_proj = nn.Linear(d, kv * self.hd, bias=False)
        self.o_proj = nn.Linear(h * self.hd, d, bias=False)

    def forward(self, x, cos, sin, mask, cache=None):
        B, T, _ = x.shape
        q = self.q_proj(x).view(B, T, self.h, self.hd).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.kv, self.hd).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.kv, self.hd).transpose(1, 2)
        q = q * cos + rot_half(q) * sin
        k = k * cos + rot_half(k) * sin
        if cache is not None:
            if cache.get("k") is not None:
                k = torch.cat([cache["k"], k], 2)
                v = torch.cat([cache["v"], v], 2)
            cache["k"], cache["v"] = k, v
        rep = self.h // self.kv
        k = k.repeat_interleave(rep, 1)
        v = v.repeat_interleave(rep, 1)
        if isinstance(mask, str):  # "causal" (prefill, no padding) or "none" (1-token decode)
            o = F.scaled_dot_product_attention(q, k, v, is_causal=(mask == "causal"))
        else:
            o = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        return self.o_proj(o.transpose(1, 2).reshape(B, T, -1))


class MLP(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.gate_proj = nn.Linear(c["hidden"], c["inter"], bias=False)
        self.up_proj = nn.Linear(c["hidden"], c["inter"], bias=False)
        self.down_proj = nn.Linear(c["inter"], c["hidden"], bias=False)

    def forward(self, x):
        return self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x))


class Block(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.self_attn = Attn(c)
        self.mlp = MLP(c)
        self.input_layernorm = RMSNorm(c["hidden"], c["eps"])
        self.post_attention_layernorm = RMSNorm(c["hidden"], c["eps"])

    def forward(self, x, cos, sin, mask, cache=None):
        x = x + self.self_attn(self.input_layernorm(x), cos, sin, mask, cache)
        return x + self.mlp(self.post_attention_layernorm(x))


class SmolLM(nn.Module):
    def __init__(self, c=CFG):
        super().__init__()
        self.c = c
        self.embed_tokens = nn.Embedding(c["vocab"], c["hidden"])
        self.layers = nn.ModuleList([Block(c) for _ in range(c["layers"])])
        self.norm = RMSNorm(c["hidden"], c["eps"])
        self._rope = None

    def rope(self, n, device, dtype):
        if self._rope is None or self._rope[0].shape[0] < n or self._rope[0].device != device:
            cos, sin = rope_tables(max(n, 512), self.c["hidden"] // self.c["heads"],
                                   self.c["theta"], device)
            self._rope = (cos, sin)
        return self._rope[0].to(dtype), self._rope[1].to(dtype)

    def forward(self, ids, pad_mask=None, caches=None, start=0, hidden_only=False):
        """ids (B,T). pad_mask (B,T) bool True=real token (training, right pad).
        Returns logits (B,T,V), or final hidden states if hidden_only."""
        B, T = ids.shape
        x = self.embed_tokens(ids)
        cos, sin = self.rope(start + T, ids.device, x.dtype)
        cos, sin = cos[start:start + T][None, None], sin[start:start + T][None, None]
        S = start + T
        if pad_mask is None and T == 1:
            mask = "none"
        elif pad_mask is None and start == 0:
            mask = "causal"
        else:
            causal = torch.ones(T, S, dtype=torch.bool, device=ids.device).tril(start)
            mask = causal[None, None]
            if pad_mask is not None:
                mask = mask & pad_mask[:, None, None, :]
        for i, layer in enumerate(self.layers):
            x = layer(x, cos, sin, mask, None if caches is None else caches[i])
        x = self.norm(x)
        if hidden_only:
            return x
        return F.linear(x, self.embed_tokens.weight)


def load_state(model: SmolLM, path):
    from safetensors.torch import load_file
    sd = load_file(str(path))
    sd = {k[len("model."):] if k.startswith("model.") else k: v for k, v in sd.items()}
    sd.pop("lm_head.weight", None)
    missing, unexpected = model.load_state_dict(sd, strict=False)
    missing = [m for m in missing if not m.endswith("_rope")]
    assert not missing and not unexpected, (missing, unexpected)
    return model


def find_base_dir():
    import glob
    import os
    cands = glob.glob(os.path.expanduser(
        "~/.cache/huggingface/hub/models--HuggingFaceTB--SmolLM2-360M-Instruct/snapshots/*"))
    return Path(cands[0]) if cands else None


class Tok:
    def __init__(self, tok_json):
        from tokenizers import Tokenizer
        self.t = Tokenizer.from_file(str(tok_json))
        self.im_end = self.t.token_to_id(IM_END)
        self.eos = 2

    def enc(self, s):
        return self.t.encode(s, add_special_tokens=False).ids

    def dec(self, ids):
        return self.t.decode(ids, skip_special_tokens=False)


def prompt_text(turn: str) -> str:
    return (f"{IM_START}system\n{SYSTEM}{IM_END}\n{IM_START}user\n{turn.strip()}{IM_END}\n"
            f"{IM_START}assistant\n")


def target_text(frames_lines) -> str:
    return "\n".join(frames_lines) + IM_END


@torch.no_grad()
def generate(model, tok, turn, max_new=64, device="cpu"):
    ids = torch.tensor([tok.enc(prompt_text(turn))], device=device)
    caches = [dict() for _ in model.layers]
    logits = model(ids, caches=caches, start=0)
    pos = ids.shape[1]
    out = []
    nxt = int(logits[0, -1].argmax())
    for _ in range(max_new):
        if nxt in (tok.im_end, tok.eos):
            break
        out.append(nxt)
        logits = model(torch.tensor([[nxt]], device=device), caches=caches, start=pos)
        pos += 1
        nxt = int(logits[0, -1].argmax())
    return tok.dec(out).strip()


class GraphDecoder:
    """CUDA-graph greedy decoder (same math as `generate`, static KV cache).
    Removes per-kernel launch overhead on the GPU; prefill runs eagerly."""

    def __init__(self, model, tok, lmax=256):
        self.m, self.tok, self.L = model, tok, lmax
        p = next(model.parameters())
        dev, dt = p.device, p.dtype
        c = model.c
        self.hd = c["hidden"] // c["heads"]
        self.kc = [torch.zeros(1, c["kv_heads"], lmax, self.hd, device=dev, dtype=dt)
                   for _ in model.layers]
        self.vc = [torch.zeros_like(k) for k in self.kc]
        self.tok_in = torch.zeros(1, 1, dtype=torch.long, device=dev)
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
        m = self.m
        x = m.embed_tokens(self.tok_in)
        cos = self.cos.index_select(0, self.pos)[None, None]
        sin = self.sin.index_select(0, self.pos)[None, None]
        mask = (self.ar <= self.pos)[None, None, None, :]
        for i, layer in enumerate(m.layers):
            a = layer.self_attn
            h = layer.input_layernorm(x)
            q = a.q_proj(h).view(1, 1, a.h, a.hd).transpose(1, 2)
            k = a.k_proj(h).view(1, 1, a.kv, a.hd).transpose(1, 2)
            v = a.v_proj(h).view(1, 1, a.kv, a.hd).transpose(1, 2)
            q = q * cos + rot_half(q) * sin
            k = k * cos + rot_half(k) * sin
            self.kc[i].index_copy_(2, self.pos, k)
            self.vc[i].index_copy_(2, self.pos, v)
            rep = a.h // a.kv
            K = self.kc[i].repeat_interleave(rep, 1)
            V = self.vc[i].repeat_interleave(rep, 1)
            o = F.scaled_dot_product_attention(q, K, V, attn_mask=mask)
            x = x + a.o_proj(o.transpose(1, 2).reshape(1, 1, -1))
            x = x + layer.mlp(layer.post_attention_layernorm(x))
        x = m.norm(x)
        return F.linear(x, m.embed_tokens.weight)[0, -1]

    @torch.no_grad()
    def generate(self, turn, max_new=64):
        m, tok = self.m, self.tok
        dev = self.tok_in.device
        ids = torch.tensor([tok.enc(prompt_text(turn))], device=dev)
        T = ids.shape[1]
        if T + max_new >= self.L:
            return generate(m, tok, turn, max_new=max_new, device=dev)
        caches = [dict() for _ in m.layers]
        logits = m(ids, caches=caches, start=0)
        for i, cch in enumerate(caches):
            self.kc[i][:, :, :T].copy_(cch["k"])
            self.vc[i][:, :, :T].copy_(cch["v"])
        nxt = int(logits[0, -1].argmax())
        out, pos = [], T
        for _ in range(max_new):
            if nxt in (tok.im_end, tok.eos):
                break
            out.append(nxt)
            self.tok_in.fill_(nxt)
            self.pos.fill_(pos)
            self.g.replay()
            pos += 1
            nxt = int(self.out.argmax())
        return tok.dec(out).strip()


# ---------------------------------------------------------------- frames + brake
def load_table():
    d = json.loads(TABLE_PATH.read_text())
    canon = {}
    for r in d["relations"]:
        name = r["name"]
        canon[_rkey(name)] = name
        for a in r.get("aliases", []):
            canon.setdefault(_rkey(a), name)
    return d, canon


def _rkey(s):
    return re.sub(r"[\s_\-]+", " ", str(s).strip().lower())


_TABLE, _CANON = load_table()
RELATIONS = sorted({r["name"] for r in _TABLE["relations"]})


def parse_frames(text: str):
    """Raw parse. Returns list of dicts; malformed lines become {'act':'BAD'}."""
    frames = []
    for line in str(text).splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        act = parts[0].upper()
        if act == "NONE" and len(parts) == 1:
            continue
        if act == "TEACH" and len(parts) == 4:
            frames.append(dict(act="TEACH", subject=parts[1], relation=parts[2], value=parts[3]))
        elif act == "ASK" and len(parts) == 3:
            frames.append(dict(act="ASK", subject=parts[1],
                               relation=[p.strip() for p in parts[2].split(">")]))
        else:
            frames.append(dict(act="BAD", raw=line))
    return frames


_TRIM = " \t\"'.,;:!?()[]{}"


def _norm_span(s):
    return " ".join(str(s).strip(_TRIM).split()).lower()


def _in_turn(span, turn):
    s = _norm_span(span)
    if not s:
        return False
    t = " ".join(turn.split()).lower()
    # exact span on word boundaries (only case + edge punctuation trimmed)
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(s) + r"(?![A-Za-z0-9])", t) is not None


def brake(frames, turn):
    """Keep a frame only if subject (and value) are exact spans of the turn and
    every relation maps to the table (canonical name or listed alias -> name).
    Returns (kept, dropped)."""
    kept, dropped = [], []
    for f in frames:
        if f["act"] == "BAD":
            dropped.append((f, "malformed"))
            continue
        if not _in_turn(f["subject"], turn):
            dropped.append((f, "subject_not_in_turn"))
            continue
        rels = f["relation"] if f["act"] == "ASK" else [f["relation"]]
        canon = [_CANON.get(_rkey(r)) for r in rels]
        if any(c is None for c in canon):
            dropped.append((f, "relation_not_in_table"))
            continue
        g = dict(f)
        g["subject"] = " ".join(f["subject"].strip(_TRIM).split())
        if f["act"] == "TEACH":
            if not _in_turn(f["value"], turn):
                dropped.append((f, "value_not_in_turn"))
                continue
            g["value"] = " ".join(f["value"].strip(_TRIM).split())
            g["relation"] = canon[0]
        else:
            g["relation"] = canon
        kept.append(g)
    return kept, dropped


def canon_rel(r):
    return _CANON.get(_rkey(r))
