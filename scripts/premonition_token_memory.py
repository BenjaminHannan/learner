"""Token-preserving, differentiable successor candidate for the frozen Track A toy.

All causal non-question lines remain as token rows. A shared recurrent transformer
reads them with four soft attention heads, with the original encoded question as
an immutable attention source at every step. No ASK, top-k, entity binder, supplied
roles, parsed fields, evidence labels, or intermediate teacher answers are used.
The same soft forward is used in training and inference. This is a new opt-in
architecture, not a change to old checkpoints or a certified hard-card model.
"""
from __future__ import annotations

import math

import premonition_memnn as data
from premonition_memnn import torch, nn, F


def positions(length, width, reference):
    """Ordinary within-sequence positions, not semantic role/field selectors."""
    p = torch.arange(length, device=reference.device, dtype=reference.dtype)[:, None]
    f = torch.exp(torch.arange(0, width, 2, device=reference.device,
                              dtype=reference.dtype) * (-math.log(10000.) / width))
    phase = p * f
    return torch.stack((phase.sin(), phase.cos()), -1).flatten(-2)


class Attention(nn.Module):
    def __init__(self, width, heads):
        super().__init__()
        self.width, self.heads = width, heads
        self.query = nn.Linear(width, width)
        self.key = nn.Linear(width, width)
        self.value = nn.Linear(width, width)
        self.output = nn.Linear(width, width)

    def split(self, x):
        return x.reshape(*x.shape[:-1], self.heads, self.width // self.heads).transpose(-3, -2)

    def kv(self, memory):
        return self.split(self.key(memory)), self.split(self.value(memory))

    def forward(self, x, keys, values, valid, *, trace=False):
        q = self.split(self.query(x))
        scores = (q @ keys.transpose(-1, -2)) / math.sqrt(self.width // self.heads)
        weights = scores.masked_fill(~valid[:, None, None, :], -torch.inf).softmax(-1)
        read = (weights @ values).transpose(1, 2).contiguous().reshape(x.shape)
        out = self.output(read)
        return (out, weights) if trace else out


class SelfBlock(nn.Module):
    def __init__(self, width, heads):
        super().__init__()
        self.norm1, self.norm2 = nn.LayerNorm(width), nn.LayerNorm(width)
        self.attention = Attention(width, heads)
        self.ff = nn.Sequential(nn.Linear(width, 2*width), nn.GELU(), nn.Linear(2*width, width))

    def forward(self, x, valid):
        z = self.norm1(x)
        x = x + self.attention(z, *self.attention.kv(z), valid)
        return x + self.ff(self.norm2(x))


class ReadBlock(nn.Module):
    def __init__(self, width, heads):
        super().__init__()
        self.norm1, self.norm2, self.norm3 = (nn.LayerNorm(width) for _ in range(3))
        self.self_attention = Attention(width, heads)
        self.cross_attention = Attention(width, heads)
        self.ff = nn.Sequential(nn.Linear(width, 4*width), nn.GELU(), nn.Linear(4*width, width))

    def forward(self, state, anchor, question_valid, keys, values, memory_valid, *, trace=False):
        z = self.norm1(state)
        # The immutable question remains separately accessible after every read.
        source = torch.cat((z, self.norm1(anchor)), 1)
        source_valid = torch.cat((question_valid, question_valid), 1)
        state = state + self.self_attention(z, *self.self_attention.kv(source), source_valid)
        result = self.cross_attention(self.norm2(state), keys, values, memory_valid, trace=trace)
        read, attention = result if trace else (result, None)
        state = state + read
        state = state + self.ff(self.norm3(state))
        return state, attention


class TokenMemoryReasoner(nn.Module):
    def __init__(self, vocab=68, width=48, heads=4, steps=3):
        super().__init__()
        if width % 2 or width % heads or steps < 1:
            raise ValueError("even width divisible by heads and positive steps required")
        self.vocab, self.width, self.heads, self.steps = vocab, width, heads, steps
        self.embedding = nn.Embedding(vocab, width, padding_idx=0)
        self.line_encoder = SelfBlock(width, heads)
        self.question_encoder = SelfBlock(width, heads)
        self.read = ReadBlock(width, heads)
        self.memory_norm, self.answer_norm = nn.LayerNorm(width), nn.LayerNorm(width)
        self.types = nn.Parameter(torch.zeros(2, width))
        self.output_bias = nn.Parameter(torch.zeros(vocab))
        self.apply(self._initialize)
        with torch.no_grad():
            self.embedding.weight[0].zero_()

    @staticmethod
    def _initialize(module):
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, std=.02)
            if isinstance(module, nn.Linear):
                nn.init.zeros_(module.bias)

    def embed(self, ids, kind):
        x = self.embedding(ids)
        return (x + .1 * positions(ids.shape[-1], self.width, x) + self.types[kind]) * ids.ne(0)[..., None]

    def forward(self, inputs, *, trace=False):
        v, lines, length = inputs.memory.shape
        ids = inputs.memory.reshape(v * lines, length)
        valid = ids.ne(0)
        # Empty rows get a safe key locally, then are excluded from every read.
        safe = valid.clone()
        safe[:, 0] |= ~valid.any(-1)
        encoded = self.line_encoder(self.embed(ids, 0), safe)
        # Compact padding only, retaining every real token and its line identity.
        # This changes neither the attention domain nor the causal eligibility.
        encoded = self.memory_norm(encoded).reshape(v, lines * length, self.width)
        real = inputs.memory.ne(0).flatten(1)
        rank = real.long().cumsum(1) - 1
        owner = torch.arange(v, device=real.device)[:, None].expand_as(real)
        size = max(1, int(real.sum(1).max()))
        memory = encoded.new_zeros(v, size, self.width)
        memory[owner[real], rank[real]] = encoded[real]
        line_ids = torch.full((v, size), -1, device=real.device, dtype=torch.long)
        source_line = torch.arange(lines, device=real.device).repeat_interleave(length)[None].expand_as(real)
        line_ids[owner[real], rank[real]] = source_line[real]
        # Cache projections once per visit, shared across questions and loops.
        keys, values = self.read.cross_attention.kv(memory)
        keys, values = keys[inputs.owner], values[inputs.owner]
        owned_lines = line_ids[inputs.owner]
        token_valid = (owned_lines >= 0) & inputs.eligible.gather(1, owned_lines.clamp_min(0))
        # Zero NULL key/value makes empty memory safe; never an oracle fallback.
        zero = keys.new_zeros(keys.shape[0], self.heads, 1, self.width // self.heads)
        keys, values = torch.cat((keys, zero), 2), torch.cat((values, zero), 2)
        token_valid = torch.cat((token_valid, torch.ones_like(token_valid[:, :1])), 1)
        question_valid = inputs.questions.ne(0)
        if not bool(question_valid.any(-1).all()):
            raise ValueError("each question must contain a visible token")
        anchor = self.question_encoder(self.embed(inputs.questions, 1), question_valid)
        state, attention = anchor, []
        for _ in range(self.steps):
            state, weights = self.read(state, anchor, question_valid, keys, values, token_valid, trace=trace)
            if trace:
                attention.append(weights)
        last = question_valid.sum(-1) - 1
        answer = self.answer_norm(state[torch.arange(len(last), device=last.device), last])
        logits = F.linear(answer, self.embedding.weight, self.output_bias)
        return (logits, torch.stack(attention, 1)) if trace else logits

    def parameters_count(self):
        return sum(p.numel() for p in self.parameters())


def optimizer_for(model):
    return torch.optim.AdamW(model.parameters(), lr=1e-3, betas=(.9, .99), eps=1e-8, weight_decay=.1)


def training_flops(inputs, model):
    """Matmul forward/backward count; calibrated against frozen FlopCounterMode.

    Padding compaction is charged at the actual maximum real tokens per visit.
    Embedding lookups, softmax, normalization, indexing and Adam are excluded by
    the project's convention; this is not a wall-time or total energy estimate.
    """
    v, lines, t = inputs.memory.shape
    q, qt = inputs.questions.shape
    s = max(1, int(inputs.memory.ne(0).sum((1, 2)).max()))
    d = model.width
    line = 48*v*lines*t*d*d + 12*v*lines*t*t*d
    question = 48*q*qt*d*d + 12*q*qt*qt*d
    cached = 12*v*s*d*d
    reads = model.steps * (96*q*qt*d*d + 24*q*qt*qt*d + 12*q*qt*(s+1)*d)
    return line + question + cached + reads + 6*q*d*model.vocab


def training_step(model, optimizer, inputs, target, step):
    for group in optimizer.param_groups:
        group["lr"] = 1e-3 * min(1., (step + 1) / 100)
    optimizer.zero_grad(set_to_none=True)
    logits = model(inputs)
    loss = F.cross_entropy(logits, target)
    loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
    if not torch.isfinite(loss) or not torch.isfinite(norm):
        raise RuntimeError("non-finite loss/gradient")
    optimizer.step()
    return float(loss.detach()), float((logits.argmax(-1) == target).float().mean())
