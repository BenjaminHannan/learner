"""Attention + sparse-MLP recurrent transformer with diagnostic program ports.

RecordAtomResidual and NumericRelation are freshly initialized, disclosed GRU
adapters. Only their internal recurrence modules are reused. Their source heads,
source logits and answer readouts are NEVER called. Target transformer board
owns final content and learned halt. No dataset, oracle, task ID, or dispatch by
opcode appears here. Both programs execute on every round in paired arms.
"""
from __future__ import annotations
from dataclasses import dataclass, fields
from pathlib import Path
import sys
import torch
from torch import nn
from torch.nn import functional as F

REVIEW = Path(__file__).resolve().parents[1] / 'artifacts/sol-compose-20260929/dependencies'
sys.path.insert(0, str(REVIEW))
from sol_compose_record_atom import RecordAtomResidual, Translator
from sol_compose_numeric_relation import NumericRelation, NumericTalker

VOCAB, D, ROUNDS = 125, 64, 6
ARMS = ('compose', 'no_communication', 'joint', 'plain', 'record_only', 'numeric_only')


@dataclass(frozen=True)
class Context:
    anchor: torch.Tensor
    program_anchor: torch.Tensor
    memory: torch.Tensor
    memory_valid: torch.Tensor
    feature: torch.Tensor
    incidence: torch.Tensor
    atom_mask: torch.Tensor
    valid: torch.Tensor

    def select(self, ids):
        return Context(**{f.name: getattr(self, f.name)[ids] for f in fields(self)})


@dataclass(frozen=True)
class State:
    board: torch.Tensor
    records: torch.Tensor
    atoms: torch.Tensor
    numeric: torch.Tensor
    public: torch.Tensor
    rounds: torch.Tensor
    aux: torch.Tensor

    def select(self, ids):
        return State(**{f.name: getattr(self, f.name)[ids] for f in fields(self)})


class Attention(nn.Module):
    def __init__(self):
        super().__init__()
        self.q = nn.Linear(D, D); self.kv = nn.Linear(D, 2*D); self.out = nn.Linear(D, D)
        self.identity_bias = nn.Parameter(torch.zeros(4))
        self.matrix_macs = 0

    def forward(self, query, memory, same=None, memory_valid=None):
        b, n, d = query.shape; m = memory.shape[1]
        q = self.q(query).reshape(b, n, 4, d//4).transpose(1, 2)
        k, v = self.kv(memory).reshape(b, m, 2, 4, d//4).permute(2, 0, 3, 1, 4)
        logits = q @ k.transpose(-2, -1) / (d//4)**.5
        if same is not None:
            logits = logits + self.identity_bias[None, :, None, None] * same[:, None]
        if memory_valid is not None:
            logits = logits.masked_fill(~memory_valid[:, None, None], float("-inf"))
        z = logits.softmax(-1) @ v
        self.matrix_macs += 2*b*n*m*d
        return self.out(z.transpose(1, 2).reshape(b, n, d))


class Block(nn.Module):
    def __init__(self, hidden=128, sparse=True):
        super().__init__()
        self.attention = Attention(); self.norm1 = nn.LayerNorm(D); self.norm2 = nn.LayerNorm(D)
        self.sparse = sparse
        if sparse:
            self.router = nn.Linear(D, 4)
            self.experts = nn.ModuleList(nn.Sequential(nn.Linear(D, hidden), nn.GELU(), nn.Linear(hidden, D))
                                         for _ in range(4))
        else:
            self.mlp = nn.Sequential(nn.Linear(D, hidden), nn.GELU(), nn.Linear(hidden, D))

    def forward(self, board, anchor, memory, same=None, memory_valid=None):
        z = board + anchor
        z = z + self.attention(self.norm1(z), memory, same, memory_valid)
        x = self.norm2(z)
        aux = x.new_zeros(len(x))
        if self.sparse:
            flat = x.flatten(0, 1)
            probability = self.router(flat).float().softmax(-1)
            weights, routes = probability.topk(2, -1)
            # Full-softmax weights retain router gradients even with top-k.
            delta = torch.zeros_like(flat)
            for index, expert in enumerate(self.experts):
                rows, lane = (routes == index).nonzero(as_tuple=True)
                if len(rows):
                    values = expert(flat[rows]) * weights[rows, lane, None].to(x.dtype)
                    delta = delta.index_add(0, rows, values)
            density = F.one_hot(routes, 4).float().mean((0, 1))
            balance = 4 * (density * probability.mean(0)).sum()
            aux = aux + .001 * balance
            z = z + delta.reshape_as(x)
        else:
            z = z + self.mlp(x)
        return z, aux


class RecordPort(nn.Module):
    """Reuse real record/atom recurrence, expose private states not answers."""
    def __init__(self):
        super().__init__()
        prototype = RecordAtomResidual('bound')
        # Unused field encoder/head are not owned or counted as capacity.
        for name in ('read_score', 'write_score', 'beta_read', 'beta_write',
                     'read_value', 'write_value', 'record_gru', 'atom_gru'):
            setattr(self, name, getattr(prototype, name))
        self.feedback = nn.Linear(D, D)
        self.export = nn.Linear(D, D)
        self.matrix_macs = 0

    def forward(self, ctx, state, feedback):
        feature, incidence = ctx.feature, ctx.incidence.to(ctx.feature.dtype)
        b, r, p, a = incidence.shape
        context = ctx.program_anchor + self.feedback(feedback)
        allowed = ctx.valid[..., None] & ctx.atom_mask[:, None, None, :]
        gates = RecordAtomResidual._gates(self, self.read_score, state.records,
                    feature, state.atoms, incidence, self.beta_read, allowed)
        total = gates.sum(2) @ self.read_value(state.atoms)
        mass = gates.sum((2, 3))[..., None]
        inputs = torch.cat((context, total/8., total/mass.clamp_min(1)), -1)
        records = self.record_gru(inputs.reshape(b*r, 3*D), state.records.reshape(b*r, D)).reshape(b, r, D)
        gates = RecordAtomResidual._gates(self, self.write_score, records,
                    feature, state.atoms, incidence, self.beta_write, allowed)
        value = self.write_value(torch.cat((records[:, :, None].expand_as(feature), feature), -1))
        total = gates.reshape(b, r*p, a).transpose(1, 2) @ value.reshape(b, r*p, D)
        mass = gates.sum((1, 2))[..., None]
        inputs = torch.cat((total/8., total/mass.clamp_min(1)), -1)
        atoms = self.atom_gru(inputs.reshape(b*a, 2*D), state.atoms.reshape(b*a, D)).reshape(b, a, D)
        atoms = atoms * ctx.atom_mask[..., None]
        self.matrix_macs += b*r*a*D + b*r*p*a*D + 2*(b*r*p*2*D*32 + b*a*D*32)
        return records, atoms, self.export(records)

    _scores = staticmethod(RecordAtomResidual._scores)
    arm = 'bound'


class NumericPort(nn.Module):
    """Reuse NumericRelation.step on communicated latents, not answer tokens."""
    def __init__(self, embedding):
        super().__init__()
        prototype = NumericRelation(embedding, orientation='rows', width=48, public_width=8)
        for name in ('expert', 'public_memory', 'recurrent'):
            setattr(self, name, getattr(prototype, name))
        self.anchor = nn.Linear(D, 48); self.feedback = nn.Linear(D, 48)
        self.export = nn.Linear(56, D)

    def forward(self, ctx, state, feedback):
        anchor = self.anchor(ctx.program_anchor) + self.feedback(feedback)
        hidden, public = NumericRelation.step(self, anchor, state.numeric, state.public)
        return hidden, public, self.export(torch.cat((hidden, public), -1))


class Composer(nn.Module):
    def __init__(self, arm='compose', *, dense_hidden=128):
        super().__init__()
        if arm not in ARMS:
            raise ValueError('unknown experiment arm')
        self.arm = arm
        # No borrowed/trained checkpoint: identical fresh lexical translator
        # seed is supplied externally. All registered parameters are charged.
        self.embedding = nn.Embedding(VOCAB, 256)
        self.translator = Translator(self.embedding)
        self.grounding = NumericTalker()
        self.project = nn.Linear(258, D)
        self.port = nn.Embedding(4, D); self.fill = nn.Embedding(2, D)
        self.encoder = nn.Sequential(nn.Linear(4*D, D), nn.GELU(), nn.Linear(D, D))
        paired = arm in ('compose', 'no_communication')
        self.record = RecordPort() if paired or arm == 'record_only' else None
        self.numeric = NumericPort(self.embedding) if paired or arm == 'numeric_only' else None
        if arm == 'plain':
            self.blocks = nn.ModuleList(Block(dense_hidden, sparse=False) for _ in range(ROUNDS))
        else:
            self.blocks = nn.ModuleList([Block(dense_hidden if arm == 'joint' else 128, sparse=arm != 'joint')])
        self.norm = nn.LayerNorm(D)
        self.head = nn.Linear(D, VOCAB)
        self.halt = nn.Linear(D, 1)

    def encode(self, inputs, memory=None):
        t, slots, valid = inputs.tokens, inputs.slots, inputs.valid
        if (t.ndim != 3 or t.shape[-1] != 4 or slots.shape != t.shape or valid.shape != t.shape
                or t.dtype != torch.long or slots.dtype != torch.bool or valid.dtype != torch.bool):
            raise ValueError('int64[B,R,4], matching bool slots/valid required')
        if not bool(valid.all()):
            raise ValueError('this bounded pilot uses full records only')
        if t.device != self.embedding.weight.device:
            raise ValueError('model and inputs must share device')
        # Deterministic grouping of symbolic identity only. No answer derivation.
        tr = self.translator(t, slots.long(), generator=torch.Generator().manual_seed(0),
                             field_mask=valid, pad_atoms_to=10)
        lexical = self.translator.embedding_fields(tr, self.embedding)
        grounded = self.grounding.ground(t)
        x = self.project(torch.cat((lexical, grounded), -1))
        x = F.gelu(x + self.port(torch.arange(4, device=t.device))[None, None] + self.fill(slots.long()))
        program_anchor = self.encoder(x.flatten(-2))
        # Symbolic table rows are the notebook facts; only the query is prompt.
        # No table token or table latent can bypass reasoner attention to head.
        anchor = program_anchor * slots.any(-1)[..., None]
        notebook = program_anchor * (~slots.any(-1))[..., None]
        memory_valid = ~slots.any(-1)
        if memory is not None:
            if memory.values.shape[0] != len(t) or memory.values.shape[-1] != D:
                raise ValueError('memory must be [B,M,64]')
            notebook = torch.cat((notebook, memory.values), 1)
            memory_valid = torch.cat((memory_valid, memory.valid), 1)
        return Context(anchor, program_anchor, notebook, memory_valid, x, tr.B, tr.atom_mask, valid)

    def initial_state(self, ctx):
        b, r, d = ctx.anchor.shape; a = ctx.incidence.shape[-1]
        zero = ctx.anchor.new_zeros
        return State(zero(b,r,d), zero(b,r,d), zero(b,a,d), zero(b,r,48), zero(b,r,8),
                     torch.zeros(b, dtype=torch.long, device=ctx.anchor.device), zero(b))

    def step(self, ctx, state):
        feedback = torch.zeros_like(state.board) if self.arm == 'no_communication' else state.board
        records, atoms, numeric, public = state.records, state.atoms, state.numeric, state.public
        exports = []
        if self.record is not None:
            records, atoms, proposal = self.record(ctx, state, feedback)
            exports.append(proposal)
        if self.numeric is not None:
            numeric, public, proposal = self.numeric(ctx, state, feedback)
            exports.append(proposal)
        # Disconnected ablation still computes both ports (same work), but their
        # proposals cannot reach the board, decoder or each other by any route.
        if self.arm == 'no_communication':
            exports = [torch.zeros_like(x) for x in exports]
        memory = torch.cat([ctx.memory, ctx.anchor, state.board] + exports, 1)
        memory_valid = torch.cat([ctx.memory_valid] + [torch.ones_like(ctx.memory_valid[:, :state.board.shape[1]])] * (2 + len(exports)), 1)
        # Atom equality is a shared input prior, supplied to every control.
        incidence = ctx.incidence.sum(2).float()
        equality = (incidence @ incidence.transpose(1,2)).clamp_max(1)
        extra = ctx.memory.shape[1] - state.board.shape[1]
        same = torch.cat([equality, equality.new_zeros(len(equality), equality.shape[1], extra)] + [equality] * (2 + len(exports)), -1)
        index = int(state.rounds[0]) if self.arm == 'plain' else 0
        if self.arm == 'plain' and not bool((state.rounds == index).all()):
            raise ValueError('plain fixed-depth batches require one layer index')
        board, aux = self.blocks[index](state.board, ctx.anchor, memory, same, memory_valid)
        return State(self.norm(board), records, atoms, numeric, public, state.rounds + 1, aux)

    def read(self, state):
        return self.head(state.board), self.halt(state.board.mean(1)).squeeze(-1)

    def rollout(self, inputs, rounds=ROUNDS, memory=None):
        if not 1 <= rounds <= ROUNDS:
            raise ValueError('round cap is six in this sealed pilot')
        ctx = self.encode(inputs, memory); state = self.initial_state(ctx)
        states, logits, halt, aux = [], [], [], []
        for _ in range(rounds):
            state = self.step(ctx, state)
            lg, q = self.read(state)
            states.append(state); logits.append(lg); halt.append(q); aux.append(state.aux)
        return dict(state=state, states=states, logits=torch.stack(logits,1),
                    halt=torch.stack(halt,1), aux=torch.stack(aux,1).mean())

    @torch.no_grad()
    def infer(self, inputs, cap=ROUNDS, min_rounds=2, threshold=.5, memory=None):
        if not 1 <= min_rounds <= cap <= ROUNDS or not 0 < threshold < 1:
            raise ValueError('invalid stopping configuration')
        ctx = self.encode(inputs, memory); state = self.initial_state(ctx)
        b, r, _ = ctx.anchor.shape
        board = ctx.anchor.new_zeros(b,r,D)
        used = torch.zeros(b, dtype=torch.long, device=board.device)
        active = torch.arange(b, device=board.device)
        while len(active):
            state = self.step(ctx, state)
            _, q = self.read(state)
            stop = (state.rounds >= cap) | ((state.rounds >= min_rounds) & (q.sigmoid() >= threshold))
            # The plain comparator always executes its six untied layers.
            if self.arm == 'plain':
                stop = state.rounds >= cap
            ids = active[stop]; board[ids] = state.board[stop]; used[ids] = state.rounds[stop]
            active = active[~stop]; ctx = ctx.select(~stop); state = state.select(~stop)
        return dict(board=board, logits=self.head(board), rounds=used)


def parameter_counts(model):
    return dict(stored=sum(x.numel() for x in model.parameters()),
                trainable=sum(x.numel() for x in model.parameters() if x.requires_grad),
                transformer=sum(x.numel() for x in model.blocks.parameters()),
                record=0 if model.record is None else sum(x.numel() for x in model.record.parameters()),
                numeric=0 if model.numeric is None else sum(x.numel() for x in model.numeric.parameters()))


def build_model(arm):
    if arm in ('joint', 'plain'):
        # Architecture-only parameter matching; no data or scores used.
        target = parameter_counts(Composer('compose'))['stored']
        m1 = Composer(arm, dense_hidden=1); m2 = Composer(arm, dense_hidden=2)
        n1, n2 = parameter_counts(m1)['stored'], parameter_counts(m2)['stored']
        hidden = max(1, round((target-n1)/(n2-n1) + 1))
        return Composer(arm, dense_hidden=hidden)
    return Composer(arm)
