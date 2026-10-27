#!/usr/bin/env python3
"""Plain-PyTorch loader for BERT-family encoders (rung 2 of the ears, design doc 47).

Why this exists: the borrowed encoder's *weights* are someone else's, but every line of
code around them is ours, and nothing needs installing on BensPC (no `transformers`,
no `safetensors`, no `tokenizers`).  Three parts:

  * `read_safetensors(path)`      -- 8-byte little-endian header length, JSON header, raw tensors
  * `WordPiece(vocab_txt)`        -- BERT's uncased basic tokenizer + WordPiece ("##" continuations)
  * `Bert(config)`                -- embeddings + N post-LN encoder layers, absolute positions

Self-test (needs the reference library, Mac only):
    uv run --offline --no-project --python 3.12 --with torch --with transformers \
        python -B scripts/fable_bert_loader.py --check <snapshot dir>
It must reproduce the reference hidden states (max |diff| < 1e-3) or the rung-2 arm is void.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import unicodedata

import torch
import torch.nn as nn
import torch.nn.functional as F

DTYPES = {"F32": torch.float32, "F16": torch.float16, "BF16": torch.bfloat16, "I64": torch.int64}


def read_safetensors(path: str) -> dict[str, torch.Tensor]:
    with open(path, "rb") as fh:
        n = struct.unpack("<Q", fh.read(8))[0]
        header = json.loads(fh.read(n))
        blob = fh.read()
    out = {}
    for name, meta in header.items():
        if name == "__metadata__":
            continue
        a, b = meta["data_offsets"]
        t = torch.frombuffer(bytearray(blob[a:b]), dtype=DTYPES[meta["dtype"]])
        out[name] = t.reshape(meta["shape"]).clone()
    return out


# ----------------------------------------------------------------------------- tokenizer
def _is_punct(ch: str) -> bool:
    cp = ord(ch)
    if 33 <= cp <= 47 or 58 <= cp <= 64 or 91 <= cp <= 96 or 123 <= cp <= 126:
        return True
    return unicodedata.category(ch).startswith("P")


class WordPiece:
    """BERT uncased tokenizer: lowercase, strip accents, split punctuation, greedy longest-match."""

    def __init__(self, vocab_txt: str, lowercase: bool = True, max_chars: int = 100):
        with open(vocab_txt, encoding="utf-8") as fh:
            self.vocab = [line.rstrip("\n") for line in fh]
        self.idx = {w: i for i, w in enumerate(self.vocab)}
        self.lowercase = lowercase
        self.max_chars = max_chars
        self.cls, self.sep, self.pad, self.unk = (self.idx[t] for t in ("[CLS]", "[SEP]", "[PAD]", "[UNK]"))

    def basic(self, text: str) -> list[tuple[str, int, int]]:
        """(token, char_start, char_end) after whitespace + punctuation splitting."""
        out, cur, start = [], [], 0
        for i, ch in enumerate(text):
            if ch.isspace() or unicodedata.category(ch).startswith("C"):
                if cur:
                    out.append(("".join(cur), start, i)); cur = []
            elif _is_punct(ch):
                if cur:
                    out.append(("".join(cur), start, i)); cur = []
                out.append((ch, i, i + 1))
            else:
                if not cur:
                    start = i
                cur.append(ch)
        if cur:
            out.append(("".join(cur), start, len(text)))
        return out

    def _norm(self, w: str) -> str:
        if self.lowercase:
            w = w.lower()
            w = "".join(c for c in unicodedata.normalize("NFD", w) if unicodedata.category(c) != "Mn")
        return w

    def wordpiece(self, word: str) -> list[int]:
        if len(word) > self.max_chars:
            return [self.unk]
        pieces, i = [], 0
        while i < len(word):
            j, found = len(word), None
            while i < j:
                sub = ("##" if i else "") + word[i:j]
                if sub in self.idx:
                    found = self.idx[sub]; break
                j -= 1
            if found is None:
                return [self.unk]
            pieces.append(found); i = j
        return pieces

    def encode(self, text: str, max_len: int = 128) -> tuple[list[int], list[tuple[int, int]]]:
        """Token ids with [CLS]/[SEP] and, per token, the character span it came from."""
        ids, spans = [self.cls], [(0, 0)]
        for word, a, b in self.basic(text):
            for p in self.wordpiece(self._norm(word)):
                if len(ids) >= max_len - 1:
                    break
                ids.append(p); spans.append((a, b))
        ids.append(self.sep); spans.append((len(text), len(text)))
        return ids, spans

    def batch(self, texts: list[str], max_len: int = 128) -> tuple[torch.Tensor, torch.Tensor, list]:
        enc = [self.encode(t, max_len) for t in texts]
        n = max(len(e[0]) for e in enc)
        ids = torch.full((len(texts), n), self.pad, dtype=torch.long)
        mask = torch.zeros(len(texts), n, dtype=torch.bool)
        for i, (e, _) in enumerate(enc):
            ids[i, : len(e)] = torch.tensor(e); mask[i, : len(e)] = True
        return ids, mask, [s for _, s in enc]


# ----------------------------------------------------------------------------- model
class Layer(nn.Module):
    def __init__(self, d, heads, d_ff, eps):
        super().__init__()
        self.h = heads
        self.q, self.k, self.v, self.o = (nn.Linear(d, d) for _ in range(4))
        self.ln1 = nn.LayerNorm(d, eps=eps)
        self.ff1, self.ff2 = nn.Linear(d, d_ff), nn.Linear(d_ff, d)
        self.ln2 = nn.LayerNorm(d, eps=eps)

    def forward(self, x, mask):
        B, T, D = x.shape
        split = lambda t: t.view(B, T, self.h, D // self.h).transpose(1, 2)
        a = F.scaled_dot_product_attention(split(self.q(x)), split(self.k(x)), split(self.v(x)),
                                           attn_mask=mask[:, None, None, :])
        x = self.ln1(x + self.o(a.transpose(1, 2).reshape(B, T, D)))
        return self.ln2(x + self.ff2(F.gelu(self.ff1(x))))


class Bert(nn.Module):
    def __init__(self, cfg: dict):
        super().__init__()
        d, eps = cfg["hidden_size"], cfg.get("layer_norm_eps", 1e-12)
        self.tok = nn.Embedding(cfg["vocab_size"], d)
        self.pos = nn.Embedding(cfg["max_position_embeddings"], d)
        self.typ = nn.Embedding(cfg.get("type_vocab_size", 2), d)
        self.ln = nn.LayerNorm(d, eps=eps)
        self.layers = nn.ModuleList(Layer(d, cfg["num_attention_heads"], cfg["intermediate_size"], eps)
                                    for _ in range(cfg["num_hidden_layers"]))
        self.d = d

    def forward(self, ids, mask):
        T = ids.shape[1]
        x = self.ln(self.tok(ids) + self.pos(torch.arange(T, device=ids.device))[None] + self.typ.weight[0])
        for layer in self.layers:
            x = layer(x, mask)
        return x

    @staticmethod
    def rename(name: str) -> str | None:
        """HF BertModel parameter name -> ours (None = not part of the encoder, e.g. pooler)."""
        n = name.replace("bert.", "", 1) if name.startswith("bert.") else name
        table = {
            "embeddings.word_embeddings.weight": "tok.weight",
            "embeddings.position_embeddings.weight": "pos.weight",
            "embeddings.token_type_embeddings.weight": "typ.weight",
            "embeddings.LayerNorm.weight": "ln.weight", "embeddings.LayerNorm.bias": "ln.bias",
        }
        if n in table:
            return table[n]
        if not n.startswith("encoder.layer."):
            return None
        parts = n.split(".")
        i, rest = parts[2], ".".join(parts[3:])
        sub = {
            "attention.self.query": "q", "attention.self.key": "k", "attention.self.value": "v",
            "attention.output.dense": "o", "attention.output.LayerNorm": "ln1",
            "intermediate.dense": "ff1", "output.dense": "ff2", "output.LayerNorm": "ln2",
        }
        for src, dst in sub.items():
            if rest.startswith(src + "."):
                return f"layers.{i}.{dst}.{rest[len(src) + 1:]}"
        return None


def load(snapshot: str) -> tuple[Bert, WordPiece, dict]:
    with open(os.path.join(snapshot, "config.json")) as fh:
        cfg = json.load(fh)
    model = Bert(cfg)
    raw = read_safetensors(os.path.join(snapshot, "model.safetensors"))
    state, skipped = {}, []
    for k, v in raw.items():
        r = Bert.rename(k)
        (state.__setitem__(r, v.float()) if r else skipped.append(k))
    missing, unexpected = model.load_state_dict(state, strict=False)
    assert not unexpected, unexpected
    assert all(m.startswith("pos") is False for m in missing) and not missing, missing
    tok = WordPiece(os.path.join(snapshot, "vocab.txt"), lowercase=cfg.get("do_lower_case", True))
    return model.eval(), tok, {"skipped": skipped, "params": sum(p.numel() for p in model.parameters())}


SENTENCES = [
    "Maria's mother is Anna.", "Rumour has it Helfimdel's hometown is Lisnovsk.",
    "The University of Tokyo is in Bunkyo-ku, Japan.", "Who is the boss of Ivan's spouse?",
    "Mitochondria are the powerhouse of the cell; ATP synthesis occurs there.",
    "We fine-tune a 110M-parameter encoder on 100k sentences (Section 4.2).",
    "SUBJ American people of OBJ Venezuelan descent", "Correspondence to: Dr Q.-H. Song, Dept. of Medicine.",
    "élan naïve café — accents and dashes!", "x = 3.14; y != x", "", "a",
    "Bob told me Carol is not Dan's sister.", "Is Anna the mother of Maria?",
    "The inflation rate of Chile was 2.3% in 2019.", "unknownwordzzzqq appears here",
    "Chemical Abstracts Service number 7732-18-5 denotes water.", "It's 5 o'clock.",
    "Ben taught the model that Sam is Ali's father.", "A very long sentence " * 20,
]


def check(snapshot: str) -> None:
    from transformers import AutoModel, AutoTokenizer  # reference library, Mac only
    ours, tok, info = load(snapshot)
    ref_tok = AutoTokenizer.from_pretrained(snapshot)
    ref = AutoModel.from_pretrained(snapshot).eval()
    worst_tok, worst = 0, 0.0
    with torch.no_grad():
        for s in SENTENCES:
            ids, _ = tok.encode(s, 128)
            ref_ids = ref_tok(s, truncation=True, max_length=128)["input_ids"]
            worst_tok += ids != ref_ids
            if ids != ref_ids:
                print("token mismatch:", repr(s[:40]), ids[:12], ref_ids[:12])
            x = torch.tensor([ids]); m = torch.ones_like(x, dtype=torch.bool)
            h_ours = ours(x, m)
            h_ref = ref(input_ids=x, attention_mask=m.long()).last_hidden_state
            worst = max(worst, (h_ours - h_ref).abs().max().item())
        # padded batch must equal the unpadded single runs at the real positions
        ids, mask, _ = tok.batch(SENTENCES[:4], 128)
        hb = ours(ids, mask)
        pad_diff = max((hb[i, : mask[i].sum()] - ours(ids[i : i + 1, : mask[i].sum()], mask[i : i + 1, : mask[i].sum()])[0]).abs().max().item() for i in range(4))
    print(f"params {info['params']:,}  skipped {info['skipped']}")
    print(f"token mismatches {worst_tok}/{len(SENTENCES)}  max|hidden diff| {worst:.2e}  pad-vs-single {pad_diff:.2e}")
    ok = worst_tok == 0 and worst < 1e-3 and pad_diff < 1e-4
    print("CHECK", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", metavar="SNAPSHOT_DIR")
    a = ap.parse_args()
    if a.check:
        check(a.check)
