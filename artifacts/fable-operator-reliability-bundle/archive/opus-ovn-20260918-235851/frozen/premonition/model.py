"""Premonition-mini: a ~2M reasoner with a per-visit card store (design/06 §1-3).

READER   [minGRU, block-local attention (W = 64, RoPE), minGRU] + MLPs, causal over the
         whole visit; a tied next-token head gives L_lm.
WRITER   attention-pools each non-question line into a card (key 64 unit, value 128).
THINK    per question: question rows, entity slots, fetched cards and registers, one
         shared 2-layer block looped up to 8 times; register 0 drives ASK and HALT.
DECODER  one block, causal self-attention + cross-attention to the think rows; the
         tied head also covers ENT ids, which the detokeniser turns into spellings.

Everything a question sees is causal: reader states up to its "[answer]" token and
cards on earlier lines (plus NULL). The minGRU scan runs in fp32 (log space), so
the model trains under bf16 autocast. The controls are config flags: `store=False`
(D-noask) and `pointers=False` (D-noptr).
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Optional

import torch
from torch import nn
import torch.nn.functional as F

from learnlab.core import IGNORE_INDEX
from premonition.batch import PAD_ID, VisitBatch
from premonition.config import MiniConfig
from premonition.store import CardStore, age_bucket, set_cross_entropy

MODES = ("gold", "teacher", "own")
ROW_QUESTION, ROW_SLOT, ROW_CARD, ROW_REGISTER = range(4)


# ----------------------------------------------------------------------------- primitives
def rope(x: torch.Tensor, positions: torch.Tensor, base: float) -> torch.Tensor:
    """Rotary position embedding on the last dim of x [..., T, dh] (computed in fp32)."""
    half = x.shape[-1] // 2
    freq = base ** (-torch.arange(half, device=x.device, dtype=torch.float32) / half)
    angle = positions.to(torch.float32).unsqueeze(-1) * freq
    cos, sin = angle.cos(), angle.sin()
    x1, x2 = x.float().split(half, dim=-1)
    return torch.cat([x1 * cos - x2 * sin, x1 * sin + x2 * cos], dim=-1).to(x.dtype)


def _log_g(x: torch.Tensor) -> torch.Tensor:
    """log of g(x) = x + 0.5 (x >= 0) or sigmoid(x) (x < 0): a positive minGRU candidate."""
    return torch.where(x >= 0, torch.log(F.relu(x) + 0.5), -F.softplus(-x))


def min_gru_scan(gate: torch.Tensor, candidate: torch.Tensor, chunk: int) -> torch.Tensor:
    """h_t = (1 - z_t) h_{t-1} + z_t g(c_t), h_0 = 0, z = sigmoid(gate); [B, T, d] in fp32.

    Log-space parallel scan (Feng et al. 2024): log h_t = a*_t + logcumsumexp(log b - a*),
    a* = cumsum log(1 - z). The state is carried every `chunk` steps so a* stays small.
    """
    with torch.autocast(device_type=gate.device.type, enabled=False):
        gate, candidate = gate.float(), candidate.float()
        log_a = -F.softplus(gate)                       # log(1 - z)
        log_b = -F.softplus(-gate) + _log_g(candidate)  # log z + log g(c)
        outputs, log_h0 = [], None
        for start in range(0, gate.shape[1], chunk):
            a_star = log_a[:, start:start + chunk].cumsum(1)
            summed = torch.logcumsumexp(log_b[:, start:start + chunk] - a_star, dim=1)
            if log_h0 is not None:
                summed = torch.logaddexp(summed, log_h0.unsqueeze(1))
            log_h = a_star + summed
            log_h0 = log_h[:, -1]
            outputs.append(log_h)
        return torch.cat(outputs, dim=1).exp()


def _norm(x: torch.Tensor) -> torch.Tensor:
    """Parameter-free layer norm in fp32."""
    return F.layer_norm(x.float(), (x.shape[-1],))


class MinGRU(nn.Module):
    """128 -> 384 gives (z, h~, output gate); y = W_o (h * silu(gate))."""

    def __init__(self, config: MiniConfig) -> None:
        super().__init__()
        d = config.d_model
        self.chunk = config.scan_chunk
        self.inp = nn.Linear(d, 3 * d)
        self.out = nn.Linear(d, d)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        gate, candidate, output_gate = self.inp(x).chunk(3, dim=-1)
        h = min_gru_scan(gate, candidate, self.chunk)
        return self.out(h * F.silu(output_gate.float()))


class LocalAttention(nn.Module):
    """Causal block-local attention: each W-token block sees itself and the block before."""

    def __init__(self, config: MiniConfig) -> None:
        super().__init__()
        d = config.d_model
        self.heads, self.window, self.base = config.n_heads, config.window, config.rope_base
        self.qkv = nn.Linear(d, 3 * d)
        self.out = nn.Linear(d, d)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, length, width = x.shape
        heads, w = self.heads, self.window
        q, k, v = self.qkv(x).view(batch, length, 3, heads, width // heads).permute(2, 0, 3, 1, 4)
        positions = torch.arange(length, device=x.device)
        q, k = rope(q, positions, self.base), rope(k, positions, self.base)
        blocks = -(-length // w)
        pad = blocks * w - length
        if pad:
            q, k, v = (F.pad(t, (0, 0, 0, pad)) for t in (q, k, v))

        def split(t: torch.Tensor) -> torch.Tensor:          # [B, H, n*W, dh] -> [B, n, H, W, dh]
            return t.view(batch, heads, blocks, w, -1).transpose(1, 2)

        q, k, v = split(q), split(k), split(v)
        k = torch.cat([F.pad(k, (0, 0, 0, 0, 0, 0, 1, 0))[:, :blocks], k], dim=3)
        v = torch.cat([F.pad(v, (0, 0, 0, 0, 0, 0, 1, 0))[:, :blocks], v], dim=3)
        own = torch.ones(w, w, dtype=torch.bool, device=x.device).tril()
        prev = (torch.arange(blocks, device=x.device) > 0).view(blocks, 1, 1).expand(blocks, w, w)
        mask = torch.cat([prev, own.expand(blocks, w, w)], dim=2)        # [n, W, 2W]
        mask = mask.unsqueeze(1).expand(blocks, 1, w, 2 * w).repeat(batch, 1, 1, 1)
        shape = (batch * blocks, heads, w, -1)
        attended = F.scaled_dot_product_attention(q.reshape(shape), k.reshape(shape[:2] + (2 * w, -1)),
                                                  v.reshape(shape[:2] + (2 * w, -1)), attn_mask=mask)
        attended = attended.view(batch, blocks, heads, w, -1).permute(0, 1, 3, 2, 4)
        return self.out(attended.reshape(batch, blocks * w, width)[:, :length])


class Mlp(nn.Module):
    def __init__(self, d: int, ratio: int) -> None:
        super().__init__()
        self.fc = nn.Linear(d, ratio * d)
        self.act = nn.GELU()
        self.out = nn.Linear(ratio * d, d)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.out(self.act(self.fc(x)))


class ReaderLayer(nn.Module):
    def __init__(self, config: MiniConfig, kind: str) -> None:
        super().__init__()
        d = config.d_model
        self.norm1 = nn.LayerNorm(d)
        self.mixer = MinGRU(config) if kind == "gru" else LocalAttention(config)
        self.norm2 = nn.LayerNorm(d)
        self.mlp = Mlp(d, config.reader_mlp)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.mixer(self.norm1(x))
        return x + self.mlp(self.norm2(x))


class Reader(nn.Module):
    """forward(embedded [B, T, d]) -> normed hidden states [B, T, d]; causal."""

    def __init__(self, config: MiniConfig) -> None:
        super().__init__()
        self.layers = nn.ModuleList(ReaderLayer(config, kind) for kind in config.reader)
        self.norm = nn.LayerNorm(config.d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for layer in self.layers:
            x = layer(x)
        return self.norm(x)


class CardWriter(nn.Module):
    """p = attention pool of a line's reader states; k = normalize(W_k p), v = W_v p; NULL card."""

    def __init__(self, config: MiniConfig) -> None:
        super().__init__()
        d = config.d_model
        self.pool = nn.Linear(d, 1)
        self.key = nn.Linear(d, config.key_dim)
        self.value = nn.Linear(d, d)
        self.null_key = nn.Parameter(torch.empty(config.key_dim))
        self.null_value = nn.Parameter(torch.empty(d))

    def forward(self, hidden: torch.Tensor, batch: VisitBatch) -> CardStore:
        visits, lines = batch.line_start.shape
        real = batch.line_of >= 0
        slot = (batch.line_of.clamp_min(0)
                + lines * torch.arange(visits, device=hidden.device).unsqueeze(1))[real]
        score = self.pool(hidden).squeeze(-1).float()[real]
        peak = torch.full((visits * lines,), -math.inf, device=hidden.device)
        peak = peak.scatter_reduce(0, slot, score.detach(), "amax").clamp_min(-1e30)
        weight = torch.exp(score - peak[slot])
        total = torch.zeros(visits * lines, device=hidden.device).index_add(0, slot, weight)
        weight = weight / total[slot]
        pooled = torch.zeros(visits * lines, hidden.shape[-1], device=hidden.device).index_add(
            0, slot, weight.unsqueeze(-1) * hidden[real].float()).view(visits, lines, -1)
        return CardStore.write(self.key(pooled), self.value(pooled), batch,
                               self.null_key, self.null_value)


class ThinkLayer(nn.Module):
    """Pre-norm bidirectional self-attention over the think rows (padding rows masked) + MLP."""

    def __init__(self, config: MiniConfig) -> None:
        super().__init__()
        d = config.d_model
        self.heads = config.n_heads
        self.norm1 = nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d)
        self.proj = nn.Linear(d, d)
        self.norm2 = nn.LayerNorm(d)
        self.mlp = Mlp(d, config.think_mlp)

    def forward(self, x: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
        n, rows, width = x.shape
        q, k, v = self.qkv(self.norm1(x)).view(n, rows, 3, self.heads, -1).permute(2, 0, 3, 1, 4)
        attended = F.scaled_dot_product_attention(q, k, v, attn_mask=valid[:, None, None, :])
        x = x + self.proj(attended.transpose(1, 2).reshape(n, rows, width))
        return x + self.mlp(self.norm2(x))


class Think(nn.Module):
    """The shared looped block plus row-type, register, loop-step and age embeddings,
    the ASK recency biases and the slot binder."""

    def __init__(self, config: MiniConfig) -> None:
        super().__init__()
        d = config.d_model
        self.layers = nn.ModuleList(ThinkLayer(config) for _ in range(config.think_layers))
        self.row_type = nn.Embedding(4, d)
        self.register = nn.Embedding(config.registers, d)
        self.step = nn.Embedding(config.max_loops, d)
        self.age = nn.Embedding(config.age_buckets, d) if config.store else None
        self.age_bias = nn.Parameter(torch.zeros(config.age_buckets)) if config.store else None
        self.binder = nn.Linear(2 * d, 2 * d) if config.store and config.pointers else None

    def forward(self, x: torch.Tensor, valid: torch.Tensor, step: int) -> torch.Tensor:
        x = x + self.step.weight[step]
        for layer in self.layers:
            x = layer(x, valid)
        return x

    def bind(self, slot: torch.Tensor, value: torch.Tensor) -> torch.Tensor:
        """[g, c] = (sigmoid, tanh)(W_b [s; v]); s <- s + g (c - s)."""
        gate, content = self.binder(torch.cat([slot, value.to(slot.dtype)], dim=-1)).chunk(2, -1)
        return slot + torch.sigmoid(gate.float()) * (torch.tanh(content.float()) - slot)


class Heads(nn.Module):
    """On register 0: query 128 -> 64, ASK and HALT logits, ASK temperature kappa."""

    def __init__(self, config: MiniConfig) -> None:
        super().__init__()
        d = config.d_model
        self.query = nn.Linear(d, config.key_dim) if config.store else None
        self.ask = nn.Linear(d, 1) if config.store else None
        self.halt = nn.Linear(d, 1)
        self.log_kappa = nn.Parameter(torch.tensor(math.log(config.kappa_init))) if config.store else None


class Decoder(nn.Module):
    """One block: causal self-attention (RoPE), cross-attention to the think rows, MLP x2."""

    def __init__(self, config: MiniConfig) -> None:
        super().__init__()
        d = config.d_model
        self.heads, self.base = config.n_heads, config.rope_base
        self.norm1 = nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d)
        self.proj = nn.Linear(d, d)
        self.norm2 = nn.LayerNorm(d)
        self.cross_q = nn.Linear(d, d)
        self.cross_kv = nn.Linear(d, 2 * d)
        self.cross_proj = nn.Linear(d, d)
        self.norm3 = nn.LayerNorm(d)
        self.mlp = Mlp(d, config.decoder_mlp)
        self.norm = nn.LayerNorm(d)

    def forward(self, x: torch.Tensor, memory: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
        n, length, width = x.shape
        heads = self.heads
        q, k, v = self.qkv(self.norm1(x)).view(n, length, 3, heads, -1).permute(2, 0, 3, 1, 4)
        positions = torch.arange(length, device=x.device)
        q, k = rope(q, positions, self.base), rope(k, positions, self.base)
        attended = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(attended.transpose(1, 2).reshape(n, length, width))
        q = self.cross_q(self.norm2(x)).view(n, length, heads, -1).transpose(1, 2)
        k, v = self.cross_kv(_norm(memory)).view(n, memory.shape[1], 2, heads, -1).permute(2, 0, 3, 1, 4)
        attended = F.scaled_dot_product_attention(q, k, v, attn_mask=valid[:, None, None, :])
        x = x + self.cross_proj(attended.transpose(1, 2).reshape(n, length, width))
        x = x + self.mlp(self.norm3(x))
        return self.norm(x)


# ----------------------------------------------------------------------------- the model
@dataclass
class Answers:
    """Greedy answers of `PremonitionMini.answer`; ENT ids stay `vocab_size + e`."""

    tokens: torch.Tensor      # [Q, max_answer] long: ends at (and includes) the first stop id; pad after
    lengths: torch.Tensor     # [Q] long
    loops: torch.Tensor       # [Q] long: think loops used
    first_top: torch.Tensor   # [Q, top_k] long: lines of the first ASK's top-k (-1 = NULL or none)
    fetched: Optional[torch.Tensor]   # [Q, L + 1] bool: cards fetched (NULL last); None without a store
    halt_prob: torch.Tensor   # [Q] float: HALT probability at the answering loop

    def ids(self) -> list[list[int]]:
        return [row[:length].tolist() for row, length in zip(self.tokens.cpu(), self.lengths.cpu())]


@dataclass
class _Episode:
    """Per-question think state; all tensors are [Q, ...]."""

    x: torch.Tensor               # [Q, R, d] rows
    valid: torch.Tensor           # [Q, R] bool
    count: torch.Tensor           # [Q] cards inserted so far
    fetched: Optional[torch.Tensor]   # [Q, L + 1] bool
    q_visit: torch.Tensor
    q_line: torch.Tensor


class PremonitionMini(nn.Module):
    """forward(batch, mode) -> losses; answer(batch) -> greedy entity-aware answers."""

    def __init__(self, config: MiniConfig) -> None:
        super().__init__()
        self.config = config
        self.embed = nn.Embedding(config.total_vocab, config.d_model)
        self.reader = Reader(config)
        self.writer = CardWriter(config) if config.store else None
        self.think = Think(config)
        self.heads = Heads(config)
        self.decoder = Decoder(config)
        self.reset_parameters()

    # ------------------------------------------------------------------ setup
    def reset_parameters(self) -> None:
        config, d = self.config, self.config.d_model
        nn.init.normal_(self.embed.weight, std=d ** -0.5)
        residual = {id(m) for m in self.modules() if isinstance(m, (MinGRU, LocalAttention))}
        residual_std = 0.02 / math.sqrt(2 * (len(config.reader) + config.think_layers + 1))
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.normal_(module.weight, std=0.02)
                nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding) and module is not self.embed:
                nn.init.normal_(module.weight, std=0.02)
        for module in self.modules():
            outs = []
            if id(module) in residual:
                outs.append(module.out)
            if isinstance(module, Mlp):
                outs.append(module.out)
            if isinstance(module, ThinkLayer):
                outs.append(module.proj)
            if isinstance(module, Decoder):
                outs += [module.proj, module.cross_proj]
            for linear in outs:
                nn.init.normal_(linear.weight, std=residual_std)
            if isinstance(module, MinGRU):
                # Memory time constants spread log-uniformly over 2..512 tokens: z = 1 / tau.
                tau = torch.logspace(math.log10(2), math.log10(512), d)
                with torch.no_grad():
                    module.inp.bias[:d] = torch.log(1 / tau) - torch.log1p(-1 / tau)
        if self.writer is not None:
            nn.init.normal_(self.writer.null_key)
            nn.init.normal_(self.writer.null_value, std=0.02)

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def parameter_breakdown(self) -> dict[str, int]:
        """Trained parameters per module, named as in `MiniConfig.parameter_breakdown`."""
        parts = {"embedding": self.embed, "reader": self.reader, "card_writer": self.writer,
                 "think": self.think, "heads": self.heads, "decoder": self.decoder}
        return {name: sum(p.numel() for p in module.parameters()) if module is not None else 0
                for name, module in parts.items()}

    # ------------------------------------------------------------------ reading
    def read(self, batch: VisitBatch) -> torch.Tensor:
        """Normed reader states [B, T, d]; causal over tokens."""
        return self.reader(self.embed(batch.tokens))

    def lm_loss(self, hidden: torch.Tensor, batch: VisitBatch) -> torch.Tensor:
        """Next-token cross-entropy where `lm_mask` is set (answer spans are masked by the data)."""
        keep = batch.lm_mask[:, :-1] & (batch.line_of[:, 1:] >= 0)
        if not keep.any():
            return hidden.sum() * 0.0
        logits = F.linear(hidden[:, :-1][keep], self.embed.weight)
        return F.cross_entropy(logits.float(), batch.tokens[:, 1:][keep])

    def build_store(self, hidden: torch.Tensor, batch: VisitBatch) -> Optional[CardStore]:
        return self.writer(hidden, batch) if self.writer is not None else None

    def _mentions(self, batch: VisitBatch, low: Optional[torch.Tensor] = None) -> torch.Tensor:
        """[Q, n_ent] bool: entity e occurs in the visit's tokens in [low, question's "[answer]"]."""
        config = self.config
        tokens = batch.tokens
        entity = tokens - config.vocab_size
        is_entity = (entity >= 0) & (entity < config.n_ent)
        onehot = F.one_hot(entity.clamp(0, config.n_ent - 1), config.n_ent) * is_entity.unsqueeze(-1)
        counts = F.pad(onehot.cumsum(1), (0, 0, 1, 0))                    # [B, T + 1, n_ent]
        end = batch.q_span[:, 1]
        seen = counts[batch.q_visit, end]
        if low is not None:
            seen = seen - counts[batch.q_visit, low]
        return seen > 0

    # ------------------------------------------------------------------ think
    def _start(self, batch: VisitBatch, hidden: torch.Tensor, store: Optional[CardStore],
               mentions: torch.Tensor) -> _Episode:
        config, d = self.config, self.config.d_model
        count = batch.q_visit.shape[0]
        device = hidden.device
        rows_q = config.question_rows
        start, end = batch.q_span[:, 0], batch.q_span[:, 1]
        position = end.unsqueeze(1) - rows_q + torch.arange(rows_q, device=device)
        question_ok = position >= start.unsqueeze(1)
        question = hidden[batch.q_visit.unsqueeze(1), position.clamp_min(0)].float()
        type_row = self.think.row_type.weight.float()
        parts = [question + type_row[ROW_QUESTION]]
        valid = [question_ok]
        if config.slots:
            slots = self.embed.weight[config.vocab_size:config.vocab_size + config.n_ent].float()
            parts.append((slots + type_row[ROW_SLOT]).expand(count, -1, -1))
            valid.append(mentions)
        if config.cards:
            parts.append(torch.zeros(count, config.cards, d, device=device))
            valid.append(torch.zeros(count, config.cards, dtype=torch.bool, device=device))
        parts.append((self.think.register.weight.float() + type_row[ROW_REGISTER]).expand(count, -1, -1))
        valid.append(torch.ones(count, config.registers, dtype=torch.bool, device=device))
        fetched = (torch.zeros(count, store.lines + 1, dtype=torch.bool, device=device)
                   if store is not None else None)
        return _Episode(torch.cat(parts, dim=1), torch.cat(valid, dim=1),
                        torch.zeros(count, dtype=torch.long, device=device), fetched,
                        batch.q_visit, batch.q_line)

    @property
    def _card_base(self) -> int:
        return self.config.question_rows + self.config.slots

    @property
    def _register_base(self) -> int:
        return self._card_base + self.config.cards

    def _insert(self, episode: _Episode, store: CardStore, index: torch.Tensor,
                cards: torch.Tensor) -> None:
        """Append fetched cards (indices [n, K], -1 = none) as rows of questions `index`; bind slots."""
        config = self.config
        if cards.shape[1] > config.card_rows:
            raise ValueError(f"cannot insert {cards.shape[1]} cards into {config.card_rows} rows at once")
        real = cards >= 0
        if not real.any():
            return
        values, ents, lines = store.gather(cards, episode.q_visit[index])
        bucket = age_bucket(episode.q_line[index].unsqueeze(1) - lines, config.age_buckets)
        bucket = torch.where(lines >= 0, bucket, torch.zeros_like(bucket))
        rows = values.float() + self.think.age(bucket).float() \
            + self.think.row_type.weight[ROW_CARD].float()
        order = real.long().cumsum(1) - 1
        position = self._card_base + (episode.count[index].unsqueeze(1) + order) % config.card_rows
        who = index.unsqueeze(1).expand_as(cards)
        episode.x = episode.x.index_put((who[real], position[real]), rows[real])
        episode.valid = episode.valid.index_put(
            (who[real], position[real]), torch.ones_like(position[real], dtype=torch.bool))
        episode.count = episode.count.index_add(0, index, real.long().sum(1))
        episode.fetched = episode.fetched.index_put(
            (who[real], cards[real]), torch.ones_like(cards[real], dtype=torch.bool))
        if self.think.binder is None:
            return
        for k in range(cards.shape[1]):
            ent = ents[:, k]                                                   # [n, E]
            repeat = (ent.unsqueeze(2) == ent.unsqueeze(1)).tril(-1).any(2)
            bind = (ent >= 0) & real[:, k:k + 1] & ~repeat
            if not bind.any():
                continue
            slot = config.question_rows + ent.clamp_min(0)
            owner = index.unsqueeze(1).expand_as(ent)
            state = episode.x[owner[bind], slot[bind]]
            value = values[:, k].unsqueeze(1).expand(-1, ent.shape[1], -1)[bind]
            episode.x = episode.x.index_put((owner[bind], slot[bind]), self.think.bind(state, value))

    def _step(self, episode: _Episode, index: torch.Tensor, step: int, store: Optional[CardStore]
              ) -> tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
        """One loop for questions `index`: (rows, halt logit, ask logit, ASK scores)."""
        rows = self.think(episode.x[index], episode.valid[index], step)
        episode.x = episode.x.index_copy(0, index, rows.to(episode.x.dtype))
        register = _norm(rows[:, self._register_base])
        halt = self.heads.halt(register).squeeze(-1).float()
        if store is None:
            return rows, halt, None, None
        ask = self.heads.ask(register).squeeze(-1).float()
        scores = store.ask(self.heads.query(register), episode.q_visit[index], episode.q_line[index],
                           self.heads.log_kappa.exp(), self.think.age_bias,
                           episode.fetched[index], questions=index)
        return rows, halt, ask, scores

    def _decode_logits(self, rows: torch.Tensor, valid: torch.Tensor, inputs: torch.Tensor
                       ) -> torch.Tensor:
        return self.decoder(self.embed(inputs), rows, valid)

    # ------------------------------------------------------------------ training
    def forward(self, batch: VisitBatch, mode: str = "teacher", p_own: float = 0.0,
                loops: Optional[int] = None, weights: Optional[dict[str, float]] = None,
                generator: Optional[torch.Generator] = None) -> dict[str, Any]:
        """The four losses of design/06 §3 and their weighted sum under "loss".

        mode "gold": every gold card (NULL when never told) is loaded before loop 1; 2 loops.
        mode "teacher": after each loop, fetch up to top_k cards of G minus F plus 1-2 random
            distractors while G minus F is non-empty; ceil(|G| / 4) + 3 loops.
        mode "own": like "teacher", but each (question, loop) uses the model's own top-k
            (when its ASK logit > 0) with probability p_own; max_loops loops.
        `loops` overrides the loop count. Default weights come from the config, except
        that "gold" leaves out L_ask and L_halt (the 0-5% phase trains L_lm + L_ans only).
        """
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode!r}; choose from {MODES}")
        config = self.config
        hidden = self.read(batch)
        l_lm = self.lm_loss(hidden, batch)
        store = self.build_store(hidden, batch)
        count = batch.q_visit.shape[0]
        zero = hidden.sum() * 0.0
        metrics: dict[str, torch.Tensor] = {}
        if weights is None:
            weights = {"lm": config.w_lm, "ask": config.w_ask, "ans": config.w_ans, "halt": config.w_halt}
            if mode == "gold":
                weights.update(ask=0.0, halt=0.0)
        if count == 0:
            losses = {"lm": l_lm, "ask": zero, "ans": zero, "halt": zero}
            metrics["question_loops"] = torch.zeros((), dtype=torch.long)
            return {**losses, "loss": sum(weights[k] * v for k, v in losses.items()), "metrics": metrics}

        device = hidden.device
        episode = self._start(batch, hidden, store, self._mentions(batch))
        told_lines = (batch.gold_lines >= 0).sum(1).clamp_min(1)
        if loops is not None:
            n_loops = torch.full((count,), loops, dtype=torch.long, device=device)
        elif mode == "gold":
            n_loops = torch.full((count,), 2, dtype=torch.long, device=device)
        elif mode == "teacher":
            n_loops = (-(-told_lines // config.top_k) + 3).clamp_max(config.max_loops)
        else:
            n_loops = torch.full((count,), config.max_loops, dtype=torch.long, device=device)
        n_loops = n_loops.clamp(1, config.max_loops)

        gold = None
        if store is not None:
            gold, told, missing = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
            metrics["gold_missing"] = missing.sum()
            if mode == "gold":
                width = min(gold.shape[1], batch.gold_lines.shape[1] + 1, config.card_rows)
                preload = torch.where(gold, torch.arange(gold.shape[1], device=device),
                                      torch.full_like(gold, -1, dtype=torch.long)).topk(width, 1).values
                self._insert(episode, store, torch.arange(count, device=device), preload)

        answer = batch.answer
        length = int((answer != IGNORE_INDEX).sum(1).max().item())
        targets = answer[:, :max(length, 1)]
        start_token = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1]
        inputs = torch.cat([start_token.unsqueeze(1), targets[:, :-1]], dim=1)
        inputs = inputs.masked_fill(inputs == IGNORE_INDEX, config.pad_id)

        ans_terms, halt_terms, set_terms, bce_terms = [], [], [], []
        pairs = 0
        for step in range(int(n_loops.max().item())):
            index = torch.nonzero(n_loops > step).squeeze(1)
            pairs += index.numel()
            rows, halt, ask, scores = self._step(episode, index, step, store)
            # L_ans (deep supervision) and the HALT target.
            hidden_ans = self._decode_logits(rows, episode.valid[index], inputs[index])
            target = targets[index]
            keep = target != IGNORE_INDEX
            logits = F.linear(hidden_ans[keep], self.embed.weight).float()
            owner = torch.nonzero(keep)[:, 0]
            token_ce = F.cross_entropy(logits, target[keep], reduction="none")
            per_question = torch.zeros(index.numel(), device=device).index_add(0, owner, token_ce)
            per_question = per_question / keep.sum(1).clamp_min(1)
            wrong = torch.zeros(index.numel(), device=device).index_add(
                0, owner, (logits.argmax(-1) != target[keep]).float())
            correct = (wrong == 0).float()
            if gold is not None:
                have_all = ~(gold[index] & ~episode.fetched[index]).any(1)
                scale = torch.where(have_all, 1.0, config.early_ans)
            else:
                scale = torch.ones_like(per_question)
            ans_terms.append(scale * per_question)
            halt_terms.append(F.binary_cross_entropy_with_logits(halt, correct, reduction="none"))
            if step == 0:
                metrics["answer_acc_first"] = correct.mean().detach()
            last = n_loops[index] == step + 1
            if last.any():
                metrics.setdefault("_final", []).append(correct[last].detach())
            if store is None:
                continue
            # L_ask: set cross-entropy over G minus F, plus BCE on the ASK logit.
            need = gold[index] & ~episode.fetched[index]
            asks = need.any(1)
            bce_terms.append(F.binary_cross_entropy_with_logits(ask, asks.float(), reduction="none"))
            if asks.any():
                set_terms.append(set_cross_entropy(scores[asks], need[asks]))
            if step == 0:
                metrics["recall_at_k"] = self._recall(store, episode, index, rows, gold).detach()
            # Fetch for the next loop.
            going = n_loops[index] > step + 1
            if mode == "gold" or not going.any():
                continue
            cards = self._teacher_cards(store, episode, index, need, gold[index], generator)
            if mode == "own" and p_own > 0:
                own = store.top(scores.detach(), config.top_k).masked_fill((ask <= 0).unsqueeze(1), -1)
                own = F.pad(own, (0, cards.shape[1] - own.shape[1]), value=-1)
                pick = torch.rand(index.numel(), device=device, generator=generator) < p_own
                cards = torch.where(pick.unsqueeze(1), own, cards)
            cards = cards.masked_fill(~going.unsqueeze(1), -1)
            self._insert(episode, store, index, cards)

        l_ans = torch.cat(ans_terms).sum() / pairs
        l_halt = torch.cat(halt_terms).mean()
        l_ask = zero
        if bce_terms:
            l_ask = torch.cat(bce_terms).mean()
            if set_terms:
                l_ask = l_ask + torch.cat(set_terms).mean()
        final = metrics.pop("_final")
        metrics["answer_acc"] = torch.cat(final).mean()
        metrics["question_loops"] = torch.tensor(pairs)
        losses = {"lm": l_lm, "ask": l_ask, "ans": l_ans, "halt": l_halt}
        total = sum(weights.get(name, 0.0) * value for name, value in losses.items())
        return {**losses, "loss": total, "metrics": metrics}

    def _teacher_cards(self, store: CardStore, episode: _Episode, index: torch.Tensor,
                       need: torch.Tensor, gold: torch.Tensor,
                       generator: Optional[torch.Generator]) -> torch.Tensor:
        """[n, top_k + max distractors]: up to top_k random cards of G minus F, then 1-2 random
        eligible non-gold distractors, for questions that still need cards; -1 padding."""
        config = self.config
        n, width = need.shape
        device = need.device
        noise = torch.rand(n, width, device=device, generator=generator)
        take = min(config.top_k, width)
        best, pick = noise.masked_fill(~need, -1.0).topk(take, 1)
        pick = pick.masked_fill(best < 0, -1)
        low, high = config.distractors
        if high > 0:
            pool = store.eligible(episode.q_visit[index], episode.q_line[index],
                                  episode.fetched[index], questions=index) & ~gold
            pool[:, store.null] = False
            noise = torch.rand(n, width, device=device, generator=generator)
            best, extra = noise.masked_fill(~pool, -1.0).topk(min(high, width), 1)
            wanted = low + torch.randint(high - low + 1, (n, 1), device=device, generator=generator)
            rank = torch.arange(extra.shape[1], device=device).unsqueeze(0)
            extra = extra.masked_fill((best < 0) | (rank >= wanted), -1)
            pick = torch.cat([pick, extra], dim=1)
        return pick.masked_fill(~need.any(1, keepdim=True), -1)

    def _recall(self, store: CardStore, episode: _Episode, index: torch.Tensor,
                rows: torch.Tensor, gold: torch.Tensor) -> torch.Tensor:
        """Gold recall@top_k of the first ASK over every eligible card (told questions only)."""
        told = gold[index][:, :store.null].any(1)
        if not told.any():
            return torch.zeros(())
        register = _norm(rows[:, self._register_base])
        scores = store.ask(self.heads.query(register), episode.q_visit[index], episode.q_line[index],
                           self.heads.log_kappa.exp(), self.think.age_bias, questions=index)
        top = store.top(scores, self.config.top_k)
        hit = (gold[index].gather(1, top.clamp_min(0)) & (top >= 0)).sum(1).float()
        return (hit / gold[index].sum(1).clamp_min(1))[told].mean()

    # ------------------------------------------------------------------ evaluation
    @torch.no_grad()
    def answer(self, batch: VisitBatch, *, wipe: Optional[str] = None,
               window_line: Optional[torch.Tensor] = None, stop: Optional[Iterable[int]] = None,
               max_loops: Optional[int] = None) -> Answers:
        """Greedy answers with the model's own retrieval and halting (design/06 §2).

        Loops until HALT (p > 0.5) or `max_loops`; ASK (logit > 0) fetches the top-k
        eligible cards. ENT ids are restricted to entities already mentioned (in the
        window, after a wipe). Wipes need `window_line` [Q], the first line of A's window:
        "store" keeps the reader state but drops cards and names before it; "full" also
        re-reads from the window start with a fresh reader.
        """
        config = self.config
        low = None
        if wipe is not None:
            if wipe not in ("store", "full") or window_line is None:
                raise ValueError('wipe must be "store" or "full", with window_line')
            window_line = window_line.to(batch.q_line.device)
            if wipe == "full":
                batch = crop_to_windows(batch, window_line)
            else:
                low = batch.line_start[batch.q_visit, window_line]
        hidden = self.read(batch)
        store = self.build_store(hidden, batch)
        if store is not None and wipe is not None:
            store = store.wipe(window_line)
        count = batch.q_visit.shape[0]
        device = hidden.device
        if count == 0:
            empty = torch.zeros(0, dtype=torch.long, device=device)
            return Answers(torch.zeros(0, config.max_answer, dtype=torch.long, device=device), empty,
                           empty, torch.zeros(0, config.top_k, dtype=torch.long, device=device),
                           None if store is None else torch.zeros(0, store.lines + 1, dtype=torch.bool,
                                                                  device=device),
                           torch.zeros(0, device=device))
        mentions = self._mentions(batch, low)
        episode = self._start(batch, hidden, store, mentions)
        limit = min(max_loops or config.max_loops, config.max_loops)
        running = torch.ones(count, dtype=torch.bool, device=device)
        used = torch.zeros(count, dtype=torch.long, device=device)
        halt_prob = torch.zeros(count, device=device)
        first_top = torch.full((count, config.top_k), -1, dtype=torch.long, device=device)
        for step in range(limit):
            index = torch.nonzero(running).squeeze(1)
            if index.numel() == 0:
                break
            rows, halt, ask, scores = self._step(episode, index, step, store)
            used[index] = step + 1
            prob = torch.sigmoid(halt)
            halt_prob[index] = prob
            done = (prob > 0.5) | (step + 1 == limit)
            if store is not None:
                top = store.top(scores, config.top_k)
                if step == 0:
                    first_top = torch.where(top == store.null, torch.full_like(top, -1), top)
                cards = top.masked_fill(((ask <= 0) | done).unsqueeze(1), -1)
                self._insert(episode, store, index, cards)
            running[index[done]] = False
        tokens, lengths = self._greedy(batch, episode, mentions, stop)
        return Answers(tokens, lengths, used, first_top, episode.fetched, halt_prob)

    def _greedy(self, batch: VisitBatch, episode: _Episode, mentions: torch.Tensor,
                stop: Optional[Iterable[int]]) -> tuple[torch.Tensor, torch.Tensor]:
        config = self.config
        count = batch.q_visit.shape[0]
        device = episode.x.device
        stop_ids = torch.tensor(sorted(set(stop) if stop is not None else {config.eos_id}),
                                dtype=torch.long, device=device)
        banned = torch.zeros(count, config.total_vocab, dtype=torch.bool, device=device)
        if config.pointers:
            banned[:, config.vocab_size:] = ~mentions
        sequence = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1].unsqueeze(1)
        out = torch.full((count, config.max_answer), config.pad_id, dtype=torch.long, device=device)
        lengths = torch.full((count,), config.max_answer, dtype=torch.long, device=device)
        done = torch.zeros(count, dtype=torch.bool, device=device)
        for position in range(config.max_answer):
            hidden = self._decode_logits(episode.x, episode.valid, sequence)[:, -1]
            logits = F.linear(hidden, self.embed.weight).float().masked_fill(banned, -math.inf)
            token = logits.argmax(-1)
            token = torch.where(done, torch.full_like(token, config.pad_id), token)
            out[:, position] = token
            ended = ~done & torch.isin(token, stop_ids)
            lengths = torch.where(ended, torch.full_like(lengths, position + 1), lengths)
            done |= ended
            if done.all():
                break
            sequence = torch.cat([sequence, token.unsqueeze(1)], dim=1)
        return out, lengths


def crop_to_windows(batch: VisitBatch, window_line: torch.Tensor) -> VisitBatch:
    """One row per question: the visit re-read from line `window_line[q]` up to the question's
    "[answer]" (W-full). Line indices are kept, so lines before the window simply have no card."""
    count = batch.q_visit.shape[0]
    device = batch.tokens.device
    start = batch.line_start[batch.q_visit, window_line]
    end = batch.q_span[:, 1]
    if (start < 0).any() or (start >= end).any():
        raise ValueError("window_line must start a line at or before each question")
    width = int((end - start).max().item())
    offset = torch.arange(width, device=device)
    source = start.unsqueeze(1) + offset
    inside = source < end.unsqueeze(1)
    source = torch.where(inside, source, torch.zeros_like(source))
    visit = batch.q_visit.unsqueeze(1)

    def take(value: torch.Tensor, fill: Any) -> torch.Tensor:
        return torch.where(inside, value[visit, source], torch.full_like(value[visit, source], fill))

    line_start = batch.line_start[batch.q_visit] - start.unsqueeze(1)
    lines = torch.arange(batch.line_start.shape[1], device=device)
    line_ok = (lines >= window_line.unsqueeze(1)) & (line_start >= 0) & (line_start < width) \
        & (batch.line_start[batch.q_visit] >= 0)
    line_ents = batch.line_ents[batch.q_visit]
    return VisitBatch(
        tokens=take(batch.tokens, PAD_ID),
        line_of=take(batch.line_of, -1),
        card_end=take(batch.card_end, False),
        lengths=end - start,
        lm_mask=torch.zeros(count, width, dtype=torch.bool, device=device),
        line_is_question=batch.line_is_question[batch.q_visit],
        line_start=torch.where(line_ok, line_start, torch.full_like(line_start, -1)),
        line_ents=torch.where(line_ok.unsqueeze(-1), line_ents, torch.full_like(line_ents, -1)),
        q_visit=torch.arange(count, device=device),
        q_line=batch.q_line,
        q_span=batch.q_span - start.unsqueeze(1),
        answer=batch.answer,
        gold_lines=batch.gold_lines,
        depth=batch.depth,
        question_ids=list(batch.question_ids),
        names=[batch.names[v] for v in batch.q_visit.tolist()],
        slices=batch.slices,
    )


__all__ = ["Answers", "CardWriter", "Decoder", "MODES", "PremonitionMini", "Reader", "Think",
           "crop_to_windows", "min_gru_scan", "rope"]
