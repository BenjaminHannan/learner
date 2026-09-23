"""Additive, answer-only End-to-End Memory Network baseline for the frozen toy.

Sukhbaatar et al. (2015), layer-wise tying, position encoding, three soft reads:
    k_j = sum_i PE(i,len_j) * A[token_ji]
    v_j = sum_i PE(i,len_j) * C[token_ji]
    u_0 = sum_i PE(i,len_q) * B[token_qi]
    p_h = softmax(k_j . u_h); u_(h+1) = H u_h + sum_j p_hj v_j
    logits = W u_3
No parsed entities/relations, evidence labels, story-field extraction, or role masks.
All causal non-question lines, including fillers, are eligible. A zero NULL row
allows empty memory. This is a documented reimplementation, not original weights.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]


def local_runtime():
    """Use the project's already-installed dependencies, without installing anything."""
    if importlib.util.find_spec("torch") is None:
        path = ROOT / "runtime.local.json"
        if path.exists():
            roots = json.loads(path.read_text()).get("import_roots", [])
            sys.path[:0] = [p for p in roots if Path(p).is_dir()]


local_runtime()
import torch
from torch import nn
import torch.nn.functional as F

_BOOTSTRAPPED = False


def bootstrap():
    global _BOOTSTRAPPED
    if not _BOOTSTRAPPED:
        sys.path.insert(0, str(ROOT / "scripts"))
        import premonition_ovn_ladder as L
        L.bootstrap()
        _BOOTSTRAPPED = True


@dataclass
class Inputs:
    memory: torch.Tensor       # [visits, lines, tokens], question lines are zero
    questions: torch.Tensor    # [questions, tokens], through [answer] only
    owner: torch.Tensor        # [questions], visit index
    eligible: torch.Tensor     # [questions, lines], causal, non-question lines

    def to(self, device):
        return Inputs(*(x.to(device) for x in
                        (self.memory, self.questions, self.owner, self.eligible)))


def pack(memories, questions, owners, question_lines):
    """Pure visible-token/boundary conversion. No semantic field is inspected."""
    visits = len(memories)
    lines = max((len(m) for m in memories), default=1)
    width = max((len(line) for m in memories for line in m), default=1)
    q_width = max((len(q) for q in questions), default=1)
    # Construct flat lists before tensors: avoids thousands of tiny Torch writes.
    mem = torch.tensor([[line + [0] * (width - len(line)) for line in m]
                        + [[0] * width] * (lines - len(m)) for m in memories], dtype=torch.long)
    qs = torch.tensor([q + [0] * (q_width - len(q)) for q in questions], dtype=torch.long)
    own = torch.tensor(owners, dtype=torch.long)
    valid = mem.ne(0).any(-1)
    eligible = valid[own] & (torch.arange(lines)[None] < torch.tensor(question_lines)[:, None])
    assert mem.shape[0] == visits
    return Inputs(mem, qs, own, eligible)


def from_batch(batch):
    """Evaluation adapter: ignores answers, gold, depth, slices, names and line_ents."""
    tokens = batch.tokens.tolist()
    starts = batch.line_start.tolist()
    line_of = batch.line_of.tolist()
    is_question = batch.line_is_question.tolist()
    memories = []
    for v, row in enumerate(starts):
        memories.append([])
        for line, start in enumerate(row):
            if start < 0 or is_question[v][line]:
                memories[-1].append([])
                continue
            end = start
            while end < len(tokens[v]) and line_of[v][end] == line:
                end += 1
            memories[-1].append(tokens[v][start:end])
    owners = batch.q_visit.tolist()
    questions = [tokens[v][start:end] for v, (start, end) in zip(owners, batch.q_span.tolist())]
    return pack(memories, questions, owners, batch.q_line.tolist())


def training_batch(rng, visits=16):
    """Same frozen visit() RNG sequence as L.train_stream; faster boundary packing.

    Returns targets separately. Holdout metadata is inspected for an assertion only;
    it is never included in Inputs or the neural forward.
    """
    bootstrap()
    from premonition.toy_ladder import LadderSpec, visit, ANSWER
    spec = LadderSpec()
    memories, questions, owners, question_lines, targets = [], [], [], [], []
    for v in range(visits):
        lines, _, _ = visit(spec, rng, training=True)
        memories.append([[] if line.question else list(line.tokens) for line in lines])
        for j, line in enumerate(lines):
            if line.question:
                assert not (line.hops == 2 and line.relation == spec.heldout_relation)
                questions.append(line.tokens[:line.tokens.index(ANSWER) + 1])
                owners.append(v)
                question_lines.append(j)
                targets.append(line.answer[0])
    # Frozen make() consumes one additional draw for its question-ID serial.
    # The identifier is not an input here, but the draw is essential to preserve
    # every subsequent batch of the historical training stream.
    rng.randrange(1 << 30)
    return pack(memories, questions, owners, question_lines), torch.tensor(targets)


def position_encoding(ids, d, dtype):
    """Published sentence position encoding, with actual unpadded length J."""
    length = ids.ne(0).sum(-1, keepdim=True).clamp_min(1).to(dtype)
    j = torch.arange(1, ids.shape[-1] + 1, device=ids.device, dtype=dtype)
    ratio = j / length
    k = torch.arange(1, d + 1, device=ids.device, dtype=dtype) / d
    pe = (1 - ratio[..., None]) - k * (1 - 2 * ratio[..., None])
    return pe * ids.ne(0)[..., None]


class MemoryNetwork(nn.Module):
    def __init__(self, vocab=68, width=177, hops=3):
        super().__init__()
        self.vocab, self.width, self.hops = vocab, width, hops
        self.key = nn.Embedding(vocab, width, padding_idx=0)
        self.value = nn.Embedding(vocab, width, padding_idx=0)
        self.question = nn.Embedding(vocab, width, padding_idx=0)
        self.transition = nn.Linear(width, width, bias=False)
        self.output = nn.Linear(width, vocab, bias=False)
        for module in (self.key, self.value, self.question):
            nn.init.normal_(module.weight, std=.1)
            with torch.no_grad():
                module.weight[0].zero_()
        nn.init.normal_(self.output.weight, std=.1)
        nn.init.eye_(self.transition.weight)

    def encode(self, ids, table):
        return (table(ids) * position_encoding(ids, self.width, table.weight.dtype)).sum(-2)

    def forward(self, inputs, *, trace=False, hard=False):
        keys = self.encode(inputs.memory, self.key)[inputs.owner]
        values = self.encode(inputs.memory, self.value)[inputs.owner]
        q = self.encode(inputs.questions, self.question)
        zero = keys.new_zeros(keys.shape[0], 1, self.width)
        keys, values = torch.cat((keys, zero), 1), torch.cat((values, zero), 1)
        eligible = torch.cat((inputs.eligible, torch.ones_like(inputs.eligible[:, :1])), 1)
        attention = []
        for _ in range(self.hops):
            scores = torch.einsum("qld,qd->ql", keys, q).masked_fill(~eligible, -torch.inf)
            weight = scores.softmax(-1)
            if hard:  # evaluation-only diagnostic; never the primary training policy
                weight = F.one_hot(weight.argmax(-1), weight.shape[-1]).to(weight.dtype)
            q = self.transition(q) + torch.einsum("ql,qld->qd", weight, values)
            if trace:
                attention.append(weight)
        logits = self.output(q)
        return (logits, torch.stack(attention, 1)) if trace else logits

    def parameters_count(self):
        return sum(p.numel() for p in self.parameters())


def training_flops(inputs, width=177, vocab=68, hops=3):
    """Exact matmul forward/backward convention, excluding PE/embedding/Adam work.

    H and output matmuls cost 6*Q*din*dout; each hop's two memory bmm
    operations cost 12*Q*L*d. Embedding lookup has no counted matmul.
    Calibration checks this formula against the project's FlopCounterMode.
    """
    q, lines = len(inputs.owner), inputs.memory.shape[1] + 1
    return hops * (6*q*width*width + 12*q*lines*width) + 6*q*width*vocab


def optimizer_for(model):
    return torch.optim.AdamW(model.parameters(), lr=1e-3, betas=(.9, .99), eps=1e-8,
                             weight_decay=.1)


def training_step(model, optimizer, inputs, target, step):
    for group in optimizer.param_groups:
        group["lr"] = 1e-3 * min(1., (step + 1) / 100)
    optimizer.zero_grad(set_to_none=True)
    loss = F.cross_entropy(model(inputs), target)
    loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
    if not torch.isfinite(loss) or not torch.isfinite(norm):
        raise RuntimeError("non-finite training loss or gradient")
    optimizer.step()
    return float(loss.detach())
