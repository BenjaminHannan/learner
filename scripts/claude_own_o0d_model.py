"""own-O0d: OWN EAR MODEL (plan S2.1, counts S7.1). Plain torch, no transformers lib.

Architecture (full config: vocab 8192, d=512, 8 layers, 8 heads):
  - byte-level BPE tokenizer (case kept, never merges across spaces) -> token + word ids
  - 8-layer bidirectional encoder: RMSNorm (weight-only), RoPE, SwiGLU-free 4x MLP (SiLU)
  - 6 learned slot queries + 1 cross-attention layer (q,k,v,o + 2 norms, no MLP)
  - span pointers: owner/value/relation-cue start+end as 6 Linear(d->d, no bias);
    score(slot, tok) = slot . (P h_tok). Owner also sees ME/WE pseudo-positions.
  - question head: owner start/end (2x Linear d->d), 3x relation (Linear d->154),
    inverse (Linear d->1), from the pooled encoder vector (mean over tokens).
  - classifiers (all Linear with bias): relation 154 shared across slots;
    slot mode 9; act 9; count 7 (0-6); exists 1; special embeddings ME/WE/SEP 3x512.
  - MLM projection for span-pretraining is TIED to the token embedding (0 params).
  - Hungarian set loss: exact brute-force matcher over 6 slots (720 permutations,
    vectorized in torch; no scipy needed).
  - Span decoding can ONLY return whole-word spans: a validity mask built from
    word ids forces -inf on any (start,end) that cuts a word (see decode_*).
"""

import math
import re

import torch
import torch.nn as nn
import torch.nn.functional as F

# --------------------------------------------------------------------------
# Label tables (plan S2.1)
# --------------------------------------------------------------------------

ACTS = ["STATE", "CORRECT", "DENY", "ASK", "CHECK",
        "SUPPOSE", "PLAN", "CHAT", "UNCLEAR"]                      # 9
MODES = ["ASSERT", "CORRECT", "DENY", "ASK", "CHECK",
         "SUPPOSE", "PLAN", "REPORTED", "NONE"]                    # 9
WRITABLE_ACTS = {"STATE", "CORRECT", "DENY"}

N_RELATIONS = 154          # 153 rows of relation_table_v2.json + OTHER (=index 153)
REL_OTHER = 153
REL_NONE_Q = 154           # extra NONE class used only by the 3 question-relation heads
N_SLOTS = 6
MAX_COUNT = 6              # count head classes 0..6

ME_IDX, WE_IDX, SEP_IDX = 0, 1, 2   # rows of the special-embedding table


class EarConfig:
    def __init__(self, vocab_size=8192, d_model=512, n_layers=8, n_heads=8,
                 max_len=128, n_slots=N_SLOTS, n_relations=N_RELATIONS):
        assert d_model % n_heads == 0
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.n_layers = n_layers
        self.n_heads = n_heads
        self.max_len = max_len
        self.n_slots = n_slots
        self.n_relations = n_relations


# --------------------------------------------------------------------------
# Byte-level BPE tokenizer (case kept, no cross-space merges)
# --------------------------------------------------------------------------

_WORD_RE = re.compile(r"\S+")


class ByteBPE:
    """Minimal byte-level BPE. vocab[0:256] = single bytes; merges appended.
    encode() returns (ids, word_ids); every token belongs to exactly one word,
    so whole-word spans are well defined. Greedy longest-match via a trie.
    """

    def __init__(self, vocab, merges):
        self.vocab = list(vocab)            # list of bytes objects
        self.merges = list(merges)          # list of (bytes, bytes)
        self._index = {b: i for i, b in enumerate(self.vocab)}
        self._trie = {}
        for i, b in enumerate(self.vocab):
            node = self._trie
            for byte in b:
                node = node.setdefault(byte, {})
            node["$"] = i

    @staticmethod
    def train(texts, vocab_size=8192):
        vocab = [bytes([i]) for i in range(256)]
        index = {b: i for i, b in enumerate(vocab)}
        # corpus as list of words, each a list of vocab ids
        words = []
        for t in texts:
            for w in _WORD_RE.findall(t):
                words.append([index[bytes([b])] for b in w.encode("utf-8")])
        merges = []
        cur = len(vocab)
        while cur < vocab_size:
            counts = {}
            for w in words:
                for a, b in zip(w, w[1:]):
                    counts[(a, b)] = counts.get((a, b), 0) + 1
            if not counts:
                break
            (a, b), _ = max(counts.items(), key=lambda kv: kv[1])
            na = vocab[a] + vocab[b]
            if na in index:
                # already merged form exists; rewrite words and continue
                pass
            else:
                index[na] = cur
                vocab.append(na)
                merges.append((vocab[a], vocab[b]))
                cur += 1
            # apply merge to corpus
            for w in words:
                i = 0
                while i < len(w) - 1:
                    if w[i] == a and w[i + 1] == b:
                        w[i:i + 2] = [index[na]]
                    else:
                        i += 1
        return ByteBPE(vocab, merges)

    def encode(self, text):
        ids, word_ids = [], []
        for wi, w in enumerate(_WORD_RE.findall(text)):
            raw = w.encode("utf-8")
            i = 0
            toks = []
            while i < len(raw):
                node = self._trie
                j = i
                last = None
                while j < len(raw) and raw[j] in node:
                    node = node[raw[j]]
                    j += 1
                    if "$" in node:
                        last = (node["$"], j)
                if last is None:  # cannot happen (all single bytes in vocab)
                    raise ValueError("unencodable byte")
                toks.append(last[0])
                i = last[1]
            ids.extend(toks)
            word_ids.extend([wi] * len(toks))
        return ids, word_ids

    def decode(self, ids):
        return b"".join(self.vocab[i] for i in ids).decode("utf-8", errors="replace")

    def word_start_end(self, word_ids):
        """Boolean masks: is a token a word start / word end."""
        n = len(word_ids)
        start = [True] * n
        end = [True] * n
        for i in range(1, n):
            if word_ids[i] == word_ids[i - 1]:
                start[i] = False
            else:
                end[i - 1] = False
        return start, end

    def valid_span_mask(self, word_ids):
        """(T,T) bool mask: (s,e) valid iff s<=e and span covers whole words."""
        T = len(word_ids)
        m = torch.zeros(T, T, dtype=torch.bool)
        if T == 0:
            return m
        start, end = self.word_start_end(word_ids)
        for s in range(T):
            if not start[s]:
                continue
            for e in range(s, T):
                if end[e]:
                    m[s, e] = True
        return m


# --------------------------------------------------------------------------
# Encoder pieces
# --------------------------------------------------------------------------

class RMSNorm(nn.Module):
    def __init__(self, d, eps=1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d))

    def forward(self, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps) * self.weight


def build_rope(d_head, max_len):
    inv = 1.0 / (10000 ** (torch.arange(0, d_head, 2).float() / d_head))
    pos = torch.arange(max_len).float()
    freqs = torch.outer(pos, inv)  # (L, d/2)
    return torch.cos(freqs), torch.sin(freqs)  # cached in module buffers


def apply_rope(x, cos, sin):
    # x: (B, H, T, Dh)
    xf = x.float()
    x1, x2 = xf[..., 0::2], xf[..., 1::2]
    c, s = cos[:x.size(2)].to(x.device), sin[:x.size(2)].to(x.device)
    r1 = x1 * c - x2 * s
    r2 = x1 * s + x2 * c
    out = torch.stack([r1, r2], dim=-1).flatten(-2)
    return out.to(x.dtype)


class EncoderBlock(nn.Module):
    """Bidirectional attention + SwiGLU-free 4x MLP (SiLU). No biases."""

    def __init__(self, d, n_heads):
        super().__init__()
        self.n_heads = n_heads
        self.d_head = d // n_heads
        self.n1 = RMSNorm(d)
        self.n2 = RMSNorm(d)
        self.q = nn.Linear(d, d, bias=False)
        self.k = nn.Linear(d, d, bias=False)
        self.v = nn.Linear(d, d, bias=False)
        self.o = nn.Linear(d, d, bias=False)
        self.up = nn.Linear(d, 4 * d, bias=False)
        self.down = nn.Linear(4 * d, d, bias=False)

    def forward(self, x, cos, sin, key_mask=None):
        B, T, d = x.shape
        h = self.n1(x)
        q = self.q(h).view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        k = self.k(h).view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        v = self.v(h).view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        q, k = apply_rope(q, cos, sin), apply_rope(k, cos, sin)
        att = (q @ k.transpose(-2, -1)) / math.sqrt(self.d_head)
        if key_mask is not None:
            att = att.masked_fill(~key_mask[:, None, None, :], float("-inf"))
        att = F.softmax(att, dim=-1)
        a = (att @ v).transpose(1, 2).reshape(B, T, d)
        x = x + self.o(a)
        x = x + self.down(F.silu(self.up(self.n2(x))))
        return x


class SlotLayer(nn.Module):
    """One cross-attention layer for the slot queries (+ the queries). No MLP."""

    def __init__(self, d, n_heads, n_slots=N_SLOTS):
        super().__init__()
        self.n_heads = n_heads
        self.d_head = d // n_heads
        self.n1 = RMSNorm(d)
        self.n2 = RMSNorm(d)
        self.queries = nn.Parameter(torch.randn(n_slots, d) * 0.02)
        self.q = nn.Linear(d, d, bias=False)
        self.k = nn.Linear(d, d, bias=False)
        self.v = nn.Linear(d, d, bias=False)
        self.o = nn.Linear(d, d, bias=False)

    def forward(self, enc, cos, sin, key_mask=None):
        B, T, d = enc.shape
        S = self.n_slots = self.queries.size(0)
        h = self.n1(self.queries).unsqueeze(0).expand(B, S, d)
        q = self.q(h).view(B, S, self.n_heads, self.d_head).transpose(1, 2)
        k = self.k(enc).view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        v = self.v(enc).view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        q, k = apply_rope(q, cos, sin), apply_rope(k, cos, sin)
        att = (q @ k.transpose(-2, -1)) / math.sqrt(self.d_head)
        if key_mask is not None:
            att = att.masked_fill(~key_mask[:, None, None, :], float("-inf"))
        att = F.softmax(att, dim=-1)
        a = (att @ v).transpose(1, 2).reshape(B, S, d)
        out = self.queries.unsqueeze(0).expand(B, S, d) + self.o(a)
        return self.n2(out)


# --------------------------------------------------------------------------
# Full ear model
# --------------------------------------------------------------------------

class OwnEar(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        d = cfg.d_model
        self.embed = nn.Embedding(cfg.vocab_size, d)          # 8192 x 512
        self.special = nn.Embedding(3, d)                     # ME / WE / SEP
        self.blocks = nn.ModuleList(
            [EncoderBlock(d, cfg.n_heads) for _ in range(cfg.n_layers)])
        self.final_norm = RMSNorm(d)
        cos, sin = build_rope(d // cfg.n_heads, cfg.max_len + 2)
        self.register_buffer("rope_cos", cos)
        self.register_buffer("rope_sin", sin)
        self.slots = SlotLayer(d, cfg.n_heads, cfg.n_slots)
        # span pointers: owner / value / cue x start/end (no bias)
        self.p_own_s = nn.Linear(d, d, bias=False)
        self.p_own_e = nn.Linear(d, d, bias=False)
        self.p_val_s = nn.Linear(d, d, bias=False)
        self.p_val_e = nn.Linear(d, d, bias=False)
        self.p_cue_s = nn.Linear(d, d, bias=False)
        self.p_cue_e = nn.Linear(d, d, bias=False)
        # question owner pointers
        self.p_qown_s = nn.Linear(d, d, bias=False)
        self.p_qown_e = nn.Linear(d, d, bias=False)
        # classifiers (with bias)
        R = cfg.n_relations
        self.rel_slot = nn.Linear(d, R)
        self.rel_q = nn.ModuleList([nn.Linear(d, R) for _ in range(3)])
        self.mode = nn.Linear(d, len(MODES))
        self.act = nn.Linear(d, len(ACTS))
        self.count = nn.Linear(d, MAX_COUNT + 1)
        self.exists = nn.Linear(d, 1)
        self.inverse = nn.Linear(d, 1)

    # -- encoding ---------------------------------------------------------
    def encode(self, ids, key_mask=None):
        """ids: (B,T) token ids, V+0/1/2 = ME/WE/SEP specials. Returns (B,T,d)."""
        V = self.cfg.vocab_size
        tok = ids.clamp_max(V - 1)
        x = self.embed(tok)
        is_sp = ids >= V
        if is_sp.any():
            x[is_sp] = self.special[(ids[is_sp] - V).clamp_max(2)]
        for b in self.blocks:
            x = b(x, self.rope_cos, self.rope_sin, key_mask)
        return self.final_norm(x)

    def forward(self, ids, key_mask=None):
        enc = self.encode(ids, key_mask)                       # (B,T,d)
        pooled = enc.mean(dim=1)                               # (B,d)
        slot = self.slots(enc, self.rope_cos, self.rope_sin, key_mask)  # (B,S,d)
        B, T, d = enc.shape
        S = slot.size(1)
        kh = {
            "own_s": self.p_own_s(enc), "own_e": self.p_own_e(enc),
            "val_s": self.p_val_s(enc), "val_e": self.p_val_e(enc),
            "cue_s": self.p_cue_s(enc), "cue_e": self.p_cue_e(enc),
            "qown_s": self.p_qown_s(enc), "qown_e": self.p_qown_e(enc),
        }
        # slot span logits over real tokens
        span = {}
        for name, sname in [("own_s", None), ("own_e", None), ("val_s", None),
                            ("val_e", None), ("cue_s", None), ("cue_e", None)]:
            span[name] = torch.einsum("bsd,btd->bst", slot, kh[name])  # (B,S,T)
        # owner special positions ME/WE: key = raw special embedding
        me_we = self.special.weight[:2]                        # (2,d)
        own_sp = torch.einsum("bsd,kd->bsk", slot, me_we)      # (B,S,2)
        # question owner logits from pooled vector
        qown = {k: torch.einsum("bd,btd->bt", pooled, kh[k])
                for k in ("qown_s", "qown_e")}
        qown_sp = pooled @ me_we.T                             # (B,2)
        return {
            "enc": enc, "pooled": pooled, "slot": slot,
            "span": span, "own_sp": own_sp, "qown": qown, "qown_sp": qown_sp,
            "rel_slot": self.rel_slot(slot),                   # (B,S,154)
            "rel_q": [h(pooled) for h in self.rel_q],          # 3x (B,154)
            "mode": self.mode(slot),                           # (B,S,9)
            "act": self.act(pooled),                           # (B,9)
            "count": self.count(pooled),                       # (B,7)
            "exists": self.exists(slot).squeeze(-1),           # (B,S)
            "inverse": self.inverse(pooled).squeeze(-1),       # (B,)
        }

    # -- parameter audit --------------------------------------------------
    def audit(self):
        """Exact parameter count per part, to sit next to the plan S7.1 table."""
        def n(m):
            return sum(p.numel() for p in m.parameters())
        parts = {
            "embeddings": n(self.embed),
            "encoder": sum(n(b) for b in self.blocks) + n(self.final_norm),
            "slot_layer": n(self.slots),
            "pointers": sum(n(m) for m in
                            [self.p_own_s, self.p_own_e, self.p_val_s,
                             self.p_val_e, self.p_cue_s, self.p_cue_e]),
            "question_pointers": n(self.p_qown_s) + n(self.p_qown_e),
            "classifiers": (n(self.rel_slot) + sum(n(m) for m in self.rel_q)
                            + n(self.mode) + n(self.act) + n(self.count)
                            + n(self.exists) + n(self.inverse)),
            "special_tokens": n(self.special),
        }
        parts["total"] = sum(parts.values())
        return parts


PLAN_COUNTS = {
    "embeddings": 4194304, "encoder": 25174528, "slot_layer": 1052672,
    "pointers": 1572864, "question_pointers": 524288,
    "classifiers": 329859, "special_tokens": 1536, "total": 32850051,
}


# --------------------------------------------------------------------------
# Whole-word span decoding (can ONLY return whole-word spans)
# --------------------------------------------------------------------------

def decode_span(start_logits, end_logits, valid_mask):
    """start/end_logits: (T,) tensors. valid_mask: (T,T) bool whole-word mask.
    Returns (s, e, score). Invalid (word-cutting) pairs are -inf: unreturnable.
    Score of a span = start[s] + end[e]."""
    T = start_logits.numel()
    scores = start_logits.unsqueeze(1) + end_logits.unsqueeze(0)  # (T,T)
    scores = scores.masked_fill(~valid_mask, float("-inf"))
    flat = scores.reshape(-1)
    if not torch.isfinite(flat).any():
        return (0, 0, float("-inf"))
    bi = int(torch.argmax(flat).item())
    return (bi // T, bi % T, float(flat[bi].item()))


def decode_owner(start_logits, end_logits, valid_mask, sp_scores):
    """Owner span over [ME, WE, tok0..T-1]. sp_scores: (2,) ME/WE scores.
    Returns ('ME'|'WE'|('span', s, e), score). Word-cutting spans impossible."""
    s, e, sc = decode_span(start_logits, end_logits, valid_mask)
    best = ("span", s, e)
    if float(sp_scores[0]) > sc and float(sp_scores[0]) >= float(sp_scores[1]):
        return ("ME", float(sp_scores[0]))
    if float(sp_scores[1]) > sc:
        return ("WE", float(sp_scores[1]))
    return (best, sc)


def is_whole_word_span(s, e, word_ids):
    """True iff [s,e] covers whole words only (s at a word start, e at end)."""
    if not (0 <= s <= e < len(word_ids)):
        return False
    if s > 0 and word_ids[s] == word_ids[s - 1]:
        return False
    if e < len(word_ids) - 1 and word_ids[e] == word_ids[e + 1]:
        return False
    return True


# --------------------------------------------------------------------------
# Hungarian (exact) matching loss for the 6 slots
# --------------------------------------------------------------------------

_PERMS6 = None


def _perms6():
    global _PERMS6
    if _PERMS6 is None:
        import itertools
        _PERMS6 = torch.tensor(list(itertools.permutations(range(6))),
                               dtype=torch.long)
    return _PERMS6


def hungarian_match(cost):
    """cost: (B,6,G) with G<=6 gold facts (padded with zero-cost empties to 6).
    Returns (B,6) assignment: slot s -> gold index (0..5, where G..5 = empty).
    Exact: evaluates all 720 permutations, vectorized."""
    B, S, G = cost.shape
    assert S == 6
    full = torch.zeros(B, 6, 6, dtype=cost.dtype, device=cost.device)
    full[:, :, :G] = cost
    # unmatched slots take the empty column: cost 0 (columns G..5 are zeros)
    P = _perms6().to(cost.device)                      # (720,6): perm[p,s]=gold
    rows = torch.arange(S, device=cost.device)
    tot = full[:, rows[:, None], P.T].sum(1)          # (B,720)
    best = tot.argmin(-1)                              # (B,)
    return P[best]                                     # (B,6)


def slot_match_cost(out, gold, b):
    """Negative-log-prob cost matrix (6 x G) for batch item b.

    Gold fact keys: rel, mode, val_s, val_e, cue_s, cue_e, own_s, own_e,
    own_special (None = plain token span, 0 = ME, 1 = WE). Owner logits are
    extended as [ME, WE, tok0..tokT-1] for both start and end.
    """
    G = len(gold)
    device = out["exists"].device
    S = out["exists"].size(1)
    cost = torch.zeros(S, G, dtype=torch.float32, device=device)
    for g, gf in enumerate(gold):
        cost[:, g] += F.softplus(-out["exists"][b])          # -log sigm(exists)
        cost[:, g] += F.cross_entropy(
            out["rel_slot"][b], torch.full((S,), gf["rel"],
                                           dtype=torch.long, device=device),
            reduction="none")
        cost[:, g] += F.cross_entropy(
            out["mode"][b], torch.full((S,), gf["mode"],
                                       dtype=torch.long, device=device),
            reduction="none")
        for head, key in [("val_s", "val_s"), ("val_e", "val_e"),
                          ("cue_s", "cue_s"), ("cue_e", "cue_e")]:
            tgt = torch.full((S,), gf[key], dtype=torch.long, device=device)
            cost[:, g] += F.cross_entropy(out["span"][head][b], tgt,
                                          reduction="none")
        ext_s = torch.cat([out["own_sp"][b], out["span"]["own_s"][b]], dim=1)
        ext_e = torch.cat([out["own_sp"][b], out["span"]["own_e"][b]], dim=1)
        if gf.get("own_special") is None:
            ts, te = 2 + gf["own_s"], 2 + gf["own_e"]
        else:
            ts = te = int(gf["own_special"])  # 0 = ME, 1 = WE
        cost[:, g] += F.cross_entropy(
            ext_s, torch.full((S,), ts, dtype=torch.long, device=device),
            reduction="none")
        cost[:, g] += F.cross_entropy(
            ext_e, torch.full((S,), te, dtype=torch.long, device=device),
            reduction="none")
    return cost
