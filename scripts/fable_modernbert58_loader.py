#!/usr/bin/env python3
"""Plain-PyTorch loader for ModernBERT-base (experiment 58, design doc 62).

Why this exists: same reason as scripts/fable_bert_loader.py (our code around borrowed
weights, nothing to install on BensPC), but ModernBERT is not BERT: RoPE instead of
absolute positions, GeGLU MLP, fused Wqkv attention with alternating local (128-token
window, |i-j| <= 64) / global layers (layer i global iff i % 3 == 0), pre-LN with no
biases anywhere, layer 0 with no attention norm, and a GPT-2-style byte-level BPE
tokenizer read from the snapshot's tokenizer.json (implemented here in plain Python).

Replicates transformers 5.x ModernBertModel (eager attention path) in fp32:
    uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers \
        python -B scripts/fable_modernbert58_loader.py --check <snapshot dir>
Must reproduce the reference token ids (20/20) and hidden states (max |diff| < 1e-4).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fable_bert_loader import SENTENCES, read_safetensors  # noqa: E402  (reused, not edited)

import torch
import torch.nn as nn
import torch.nn.functional as F


# ----------------------------------------------------------------------------- tokenizer
def _bytes_to_unicode() -> dict[int, str]:
    """GPT-2 byte map: printable/latin-1 bytes map to themselves, the rest to U+0100+."""
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(
        range(ord("®"), ord("ÿ") + 1)
    )
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return dict(zip(bs, (chr(c) for c in cs)))


_BYTE_MAP = _bytes_to_unicode()
_CONTRACTIONS = ("'s", "'t", "'re", "'ve", "'m", "'ll", "'d")


def _is_letter(ch: str) -> bool:
    return unicodedata.category(ch).startswith("L")


def _is_number(ch: str) -> bool:
    return unicodedata.category(ch).startswith("N")


def _gpt2_split(text: str) -> list[tuple[str, int, int]]:
    """GPT-2 regex split with char offsets (no `regex` module needed).

    Pattern: 's|'t|'re|'ve|'m|'ll|'d| ?\\p{L}+| ?\\p{N}+| ?[^\\s\\p{L}\\p{N}]+|\\s+(?!\\S)|\\s+
    """
    out: list[tuple[str, int, int]] = []
    i, n = 0, len(text)
    while i < n:
        for c in _CONTRACTIONS:
            if text.startswith(c, i):
                out.append((c, i, i + len(c)))
                i += len(c)
                break
        else:
            m = None
            for kind in ("L", "N", "O"):
                j = i + 1 if text[i] == " " else i
                k = j
                if kind == "L":
                    while k < n and _is_letter(text[k]):
                        k += 1
                elif kind == "N":
                    while k < n and _is_number(text[k]):
                        k += 1
                else:
                    while k < n and not text[k].isspace() and not _is_letter(text[k]) and not _is_number(text[k]):
                        k += 1
                if k > j:
                    m = (text[i:k], i, k)
                    break
            if m is None and text[i].isspace():
                k0 = i
                while k0 < n and text[k0].isspace():
                    k0 += 1
                run, k = text[i:k0], k0
                while run and k < n and not text[k].isspace():
                    run = run[:-1]
                    k -= 1
                m = (run, i, k) if run else (text[i:k0], i, k0)
            assert m is not None, f"unmatched char {text[i]!r}"
            out.append(m)
            i = m[2]
    return out


class ModernBPE:
    """Byte-level BPE from the snapshot's tokenizer.json + [CLS]/[SEP] framing."""

    def __init__(self, snapshot: str):
        with open(os.path.join(snapshot, "tokenizer.json"), encoding="utf-8") as fh:
            tj = json.load(fh)
        assert tj["model"]["type"] == "BPE", tj["model"]["type"]
        assert tj["normalizer"]["type"] == "NFC", tj["normalizer"]
        self.vocab: dict[str, int] = tj["model"]["vocab"]
        self.ranks = {tuple(p.split(" ")): r for r, p in enumerate(tj["model"]["merges"])}
        self.cls, self.sep, self.pad, self.unk = 50281, 50282, 50283, 50280
        # Non-special added tokens (multi-space runs, |||IP_ADDRESS|||): emitted whole.
        self.added = {
            a["content"]: a["id"] for a in tj["added_tokens"] if not a["special"]
        }

    def _bpe(self, piece: str) -> list[int]:
        chars = [_BYTE_MAP[b] for b in piece.encode("utf-8")]
        word = tuple(chars)
        if len(word) == 1:
            return [self.vocab[word[0]]]
        while len(word) > 1:
            best, best_rank = None, None
            for j in range(len(word) - 1):
                r = self.ranks.get((word[j], word[j + 1]))
                if r is not None and (best_rank is None or r < best_rank):
                    best, best_rank = (word[j], word[j + 1]), r
            if best is None:
                break
            new, j = [], 0
            while j < len(word):
                if j < len(word) - 1 and (word[j], word[j + 1]) == best:
                    new.append(word[j] + word[j + 1])
                    j += 2
                else:
                    new.append(word[j])
                    j += 1
            word = tuple(new)
        ids = []
        for t in word:
            v = self.vocab.get(t)
            ids.append(self.unk if v is None else v)
        return ids

    def _presplit_added(self, text: str) -> list[tuple[str, int, int, bool]]:
        """Split out non-special added-token strings; returns (chunk, a, b, is_added)."""
        keys = sorted(self.added, key=len, reverse=True)
        # single pass: find earliest occurrence of any key
        chunks: list[tuple[str, int, int, bool]] = []
        i = 0
        while i < len(text):
            hit = None
            for k in keys:
                if text.startswith(k, i):
                    hit = k
                    break
            if hit is not None:
                chunks.append((hit, i, i + len(hit), True))
                i += len(hit)
            else:
                j = i + 1
                while j < len(text) and not any(text.startswith(k, j) for k in keys):
                    j += 1
                chunks.append((text[i:j], i, j, False))
                i = j
        return chunks

    def encode(self, text: str, max_len: int = 128) -> tuple[list[int], list[tuple[int, int]]]:
        """Token ids with [CLS]/[SEP] and, per token, the character span it came from."""
        text = unicodedata.normalize("NFC", text)
        ids, spans = [self.cls], [(0, 0)]
        for chunk, a, b, is_added in self._presplit_added(text):
            if is_added:
                pieces = [(chunk, a, b, True)]
            else:
                pieces = [(w, x, y, False) for w, x, y in _gpt2_split(chunk)]
            for w, x, y, added in pieces:
                if len(ids) >= max_len - 1:
                    break
                if added:
                    ids.append(self.added[w])
                    spans.append((x, y))
                else:
                    for p in self._bpe(w):
                        if len(ids) >= max_len - 1:
                            break
                        ids.append(p)
                        spans.append((x, y))
            if len(ids) >= max_len - 1:
                break
        ids.append(self.sep)
        spans.append((len(text), len(text)))
        return ids, spans

    def batch(self, texts: list[str], max_len: int = 128) -> tuple[torch.Tensor, torch.Tensor, list]:
        enc = [self.encode(t, max_len) for t in texts]
        n = max(len(e[0]) for e in enc)
        ids = torch.full((len(texts), n), self.pad, dtype=torch.long)
        mask = torch.zeros(len(texts), n, dtype=torch.bool)
        for i, (e, _) in enumerate(enc):
            ids[i, : len(e)] = torch.tensor(e)
            mask[i, : len(e)] = True
        return ids, mask, [s for _, s in enc]


# ----------------------------------------------------------------------------- model
class ModernLayer(nn.Module):
    def __init__(self, d: int, heads: int, d_ff: int, eps: float, first: bool):
        super().__init__()
        self.h = heads
        self.hd = d // heads
        self.Wqkv = nn.Linear(d, 3 * d, bias=False)
        self.Wo = nn.Linear(d, d, bias=False)
        self.attn_norm = nn.Identity() if first else nn.LayerNorm(d, eps=eps, bias=False)
        self.mlp_norm = nn.LayerNorm(d, eps=eps, bias=False)
        self.Wi = nn.Linear(d, 2 * d_ff, bias=False)
        self.Wo2 = nn.Linear(d_ff, d, bias=False)

    def forward(self, x, cos, sin, allow):
        B, T, D = x.shape
        qkv = self.Wqkv(self.attn_norm(x)).view(B, T, 3, self.h, self.hd)
        q, k, v = (t.transpose(1, 2) for t in qkv.unbind(dim=2))
        q = (q.float() * cos + _rot(q).float() * sin).to(q.dtype)
        k = (k.float() * cos + _rot(k).float() * sin).to(k.dtype)
        w = torch.matmul(q.float(), k.transpose(2, 3).float()) / math.sqrt(self.hd)
        w = w + allow
        w = torch.softmax(w, dim=-1).to(x.dtype)
        a = torch.matmul(w, v).transpose(1, 2).reshape(B, T, D)
        x = x + self.Wo(a)
        h, g = self.Wi(self.mlp_norm(x)).chunk(2, dim=-1)
        return x + self.Wo2(F.gelu(h) * g)


def _rot(x):
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat((-x2, x1), dim=-1)


class ModernBert(nn.Module):
    def __init__(self, cfg: dict):
        super().__init__()
        d, eps = cfg["hidden_size"], cfg.get("norm_eps", 1e-05)
        self.emb = nn.Embedding(cfg["vocab_size"], d, padding_idx=cfg.get("pad_token_id", 50283))
        self.embnorm = nn.LayerNorm(d, eps=eps, bias=False)
        n = cfg.get("global_attn_every_n_layers", 3)
        self.is_global = [(i % n) == 0 for i in range(cfg["num_hidden_layers"])]
        self.layers = nn.ModuleList(
            ModernLayer(d, cfg["num_attention_heads"], cfg["intermediate_size"], eps, i == 0)
            for i in range(cfg["num_hidden_layers"])
        )
        self.final = nn.LayerNorm(d, eps=eps, bias=False)
        hd = d // cfg["num_attention_heads"]
        self.rope = {
            t: 1.0 / (theta ** (torch.arange(0, hd, 2).float() / hd))
            for t, theta in (("local", cfg.get("local_rope_theta", 10000.0)),
                             ("global", cfg.get("global_rope_theta", 160000.0)))
        }
        self.half_win = cfg.get("local_attention", 128) // 2
        self._rope_cache: dict[tuple[str, int], tuple[torch.Tensor, torch.Tensor]] = {}

    def _cos_sin(self, kind: str, T: int, dev) -> tuple[torch.Tensor, torch.Tensor]:
        key = (kind, T)
        if key not in self._rope_cache:
            f = (torch.arange(T).float().unsqueeze(1) @ self.rope[kind].unsqueeze(0))
            e = torch.cat([f, f], dim=-1)
            self._rope_cache[key] = (e.cos().unsqueeze(0).unsqueeze(0),
                                     e.sin().unsqueeze(0).unsqueeze(0))
        c, s = self._rope_cache[key]
        return c.to(dev), s.to(dev)

    def forward(self, ids, mask):
        B, T, dev = ids.shape[0], ids.shape[1], ids.device
        x = self.embnorm(self.emb(ids))
        idx = torch.arange(T, device=dev)
        glob = mask[:, None, None, :].float()
        full_allow = torch.where(glob.bool(), 0.0, torch.finfo(torch.float32).min)
        win = (idx[None, :] - idx[:, None]).abs() <= self.half_win
        loc_allow = torch.where(glob.bool() & win[None, None], 0.0, torch.finfo(torch.float32).min)
        c_g, s_g = self._cos_sin("global", T, dev)
        c_l, s_l = self._cos_sin("local", T, dev)
        for layer, g in zip(self.layers, self.is_global):
            x = layer(x, c_g, s_g, full_allow) if g else layer(x, c_l, s_l, loc_allow)
        return self.final(x)

    @staticmethod
    def rename(name: str) -> str | None:
        """snapshot key -> ours (None = masked-LM head, not part of the encoder)."""
        if not name.startswith("model."):
            return None
        n = name[len("model."):]
        if n == "embeddings.tok_embeddings.weight":
            return "emb.weight"
        if n == "embeddings.norm.weight":
            return "embnorm.weight"
        if n == "final_norm.weight":
            return "final.weight"
        if not n.startswith("layers."):
            return None
        parts = n.split(".")
        i, rest = parts[1], ".".join(parts[2:])
        sub = {"attn.Wqkv.weight": "Wqkv.weight", "attn.Wo.weight": "Wo.weight",
               "attn_norm.weight": "attn_norm.weight", "mlp_norm.weight": "mlp_norm.weight",
               "mlp.Wi.weight": "Wi.weight", "mlp.Wo.weight": "Wo2.weight"}
        return f"layers.{i}.{sub[rest]}" if rest in sub else None


def load(snapshot: str) -> tuple[ModernBert, ModernBPE, dict]:
    t0 = time.time()
    with open(os.path.join(snapshot, "config.json")) as fh:
        cfg = json.load(fh)
    model = ModernBert(cfg)
    raw = read_safetensors(os.path.join(snapshot, "model.safetensors"))
    state, skipped = {}, []
    for k, v in raw.items():
        r = ModernBert.rename(k)
        (state.__setitem__(r, v.float()) if r else skipped.append(k))
    missing, unexpected = model.load_state_dict(state, strict=False)
    assert not unexpected, unexpected
    assert not missing, missing
    tok = ModernBPE(snapshot)
    info = {"skipped": skipped, "params": sum(p.numel() for p in model.parameters()),
            "load_s": time.time() - t0}
    return model.eval(), tok, info


def check(snapshot: str) -> None:
    from transformers import AutoModel, AutoTokenizer  # reference library, Mac only
    t0 = time.time()
    ours, tok, info = load(snapshot)
    load_s = info["load_s"]
    ref_tok = AutoTokenizer.from_pretrained(snapshot)
    ref = AutoModel.from_pretrained(snapshot).eval()
    worst_tok, worst, worst_span = 0, 0.0, 0
    with torch.no_grad():
        for s in SENTENCES:
            ids, spans = tok.encode(s, 128)
            ref_ids = ref_tok(s, truncation=True, max_length=128)["input_ids"]
            worst_tok += ids != ref_ids
            worst_span += len(spans) != len(ids)
            if ids != ref_ids:
                print("token mismatch:", repr(s[:40]), ids[:16], ref_ids[:16])
            x = torch.tensor([ids])
            m = torch.ones_like(x, dtype=torch.bool)
            h_ours = ours(x, m)
            h_ref = ref(input_ids=x, attention_mask=m.long()).last_hidden_state
            worst = max(worst, (h_ours - h_ref).abs().max().item())
        ids, mask, _ = tok.batch(SENTENCES[:4], 128)
        hb = ours(ids, mask)
        pad_diff = max(
            (hb[i, : mask[i].sum()] - ours(ids[i:i + 1, : mask[i].sum()],
                                          mask[i:i + 1, : mask[i].sum()])[0]).abs().max().item()
            for i in range(4))
    total_s = time.time() - t0
    print(f"params {info['params']:,}  skipped {info['skipped']}")
    print(f"token mismatches {worst_tok}/{len(SENTENCES)}  max|hidden diff| {worst:.2e}  "
          f"pad-vs-single {pad_diff:.2e}  span-len mismatches {worst_span}/{len(SENTENCES)}")
    print(f"load {load_s:.1f}s  check-total {total_s:.1f}s")
    ok = worst_tok == 0 and worst < 1e-4 and worst_span == 0 and load_s < 60
    print("CHECK", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", metavar="SNAPSHOT_DIR")
    a = ap.parse_args()
    if a.check:
        check(a.check)
