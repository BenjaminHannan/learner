"""TinyLM: STAND-IN for the frozen LFM2.5-1.2B (same five-member interface), plus a word tokenizer.

claims: plumbing only; toy data; not an eval. It is pretrained briefly on toy text so the prefix
route has a language to steer, then frozen for good. The real swap implements the same members
over a Hugging Face causal LM (get_input_embeddings, output_hidden_states, inputs_embeds).
"""
from __future__ import annotations

import hashlib
import re
import torch
from torch import nn
import torch.nn.functional as F

SPECIALS = ["<pad>", "<bos>", "<eos>", "<unk>"]
PIECE = re.compile(r"\d+|[A-Za-z]+|[^\sA-Za-z\d]")
WORDS = ("ana ben cy dee likes has buys loses gets gives away red blue pens cards and the more of "
         "colour how many that colour then times as many shares equally between friends remember "
         "each does friend get she he they a an to from . , ? : = - / err in is are what pen card").split()
MAX_INT = 400


class Tokenizer:
    """Word-level, case-insensitive. Integers up to MAX_INT are single tokens. Offsets index the original text."""

    def __init__(self):
        self.itos = SPECIALS + sorted(set(WORDS)) + [str(i) for i in range(MAX_INT + 1)]
        self.stoi = {t: i for i, t in enumerate(self.itos)}
        self.pad_id, self.bos_id, self.eos_id, self.unk_id = (self.stoi[s] for s in SPECIALS)
        self.vocab_size = len(self.itos)

    def encode(self, text: str):
        ids, offsets = [], []
        for m in PIECE.finditer(text):
            ids.append(self.stoi.get(m.group().lower(), self.unk_id)); offsets.append((m.start(), m.end()))
        return ids, offsets

    def decode(self, ids) -> str:
        out = ""
        for i in ids:
            if i in (self.pad_id, self.bos_id, self.eos_id):
                continue
            t = self.itos[i]
            out += t if (t in ".,?:/-" or not out) else " " + t
        return out.replace(" /", "/").replace("/ ", "/").replace("- ", "-")


class _Block(nn.Module):
    def __init__(self, d, heads, mlp):
        super().__init__()
        self.n1, self.n2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.o = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.fc1, self.fc2, self.heads = nn.Linear(d, mlp), nn.Linear(mlp, d), heads

    def forward(self, x, key_ok):
        b, t, d = x.shape
        q, k, v = self.qkv(self.n1(x)).view(b, t, 3, self.heads, d // self.heads).permute(2, 0, 3, 1, 4)
        causal = torch.ones(t, t, dtype=torch.bool, device=x.device).tril()
        mask = causal[None, None] & key_ok[:, None, None, :]
        mask = mask | torch.eye(t, dtype=torch.bool, device=x.device)[None, None]  # no empty rows
        x = x + self.o(F.scaled_dot_product_attention(q, k, v, attn_mask=mask).transpose(1, 2).reshape(b, t, d))
        return x + self.fc2(F.gelu(self.fc1(self.n2(x))))


class TinyLM(nn.Module):
    """STAND-IN for frozen LFM2.5-1.2B: causal pre-LN transformer, D=128, 2 layers, tied head."""
    IS_STAND_IN = True

    def __init__(self, vocab_size, d_model=128, layers=2, heads=4, mlp=512, max_len=64, pad_id=0, bos_id=1, eos_id=2):
        super().__init__()
        self.d_model, self.vocab_size, self.max_len = d_model, vocab_size, max_len
        self.pad_id, self.bos_id, self.eos_id = pad_id, bos_id, eos_id
        self.tok, self.pos = nn.Embedding(vocab_size, d_model), nn.Embedding(max_len, d_model)
        self.blocks = nn.ModuleList(_Block(d_model, heads, mlp) for _ in range(layers))
        self.norm = nn.LayerNorm(d_model)

    def embed(self, ids): return self.tok(ids)

    def _run(self, x, attn_mask, layer=-1):
        x = x + self.pos(torch.arange(x.shape[1], device=x.device))[None]
        states = []
        for blk in self.blocks:
            x = blk(x, attn_mask); states.append(x)
        return self.norm(x) if layer == -1 else states[layer]

    def hidden(self, ids, attn_mask, layer: int = -1):
        return self._run(self.embed(ids), attn_mask, layer)

    def logits_from_embeds(self, inputs_embeds, attn_mask):
        return self._run(inputs_embeds, attn_mask) @ self.tok.weight.T

    def fingerprint(self) -> str:
        h = hashlib.sha256()
        for k, v in sorted(self.state_dict().items()):
            h.update(k.encode()); h.update(v.detach().cpu().contiguous().numpy().tobytes())
        return h.hexdigest()

    def freeze(self):
        self.eval().requires_grad_(False)
        for p in self.parameters(): p.grad = None   # drop pretrain grads: a frozen LM must have none
        return self


def build_frozen_lm(corpus, tok: Tokenizer, steps=300, seed=0, batch=16):
    """Build TinyLM, give it a one-off next-token pretrain on `corpus` (list[str]), freeze it. A fixture, not the system under test."""
    g = torch.Generator().manual_seed(seed)
    torch.manual_seed(seed)
    lm = TinyLM(tok.vocab_size, pad_id=tok.pad_id, bos_id=tok.bos_id, eos_id=tok.eos_id)
    seqs = [[tok.bos_id] + tok.encode(t)[0][:60] + [tok.eos_id] for t in corpus]
    opt = torch.optim.AdamW(lm.parameters(), lr=2e-3, weight_decay=0.0)
    for _ in range(steps):
        idx = torch.randint(0, len(seqs), (batch,), generator=g).tolist()
        n = max(len(seqs[i]) for i in idx)
        ids = torch.full((batch, n), tok.pad_id, dtype=torch.long)
        for r, i in enumerate(idx): ids[r, :len(seqs[i])] = torch.tensor(seqs[i])
        ok = ids != tok.pad_id
        logits = lm.logits_from_embeds(lm.embed(ids[:, :-1]), ok[:, :-1])
        loss = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), ids[:, 1:].reshape(-1), ignore_index=tok.pad_id)
        opt.zero_grad(); loss.backward(); opt.step()
    return lm.freeze()
