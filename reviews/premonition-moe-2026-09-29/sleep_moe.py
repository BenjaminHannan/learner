"""Source-preserving sparse residual operators, a development candidate.

The existing dense loop is the shared expert. New experts propose state changes;
zero-initialized output projections make conversion exactly source-preserving.
Routing is per problem, per block, per recurrent step. No puzzle-kind input or
checker is available to the model. This is an original hypothesis, not a result.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import claude_fewex_net as N


class DeltaExpert(nn.Module):
    def __init__(self, d=256, hidden=64, depth=3, kind="mlp"):
        super().__init__()
        self.kind = kind
        self.norm = nn.LayerNorm(d)
        # A learned local spatial operator is useful for testing a stronger
        # propagation prior; its weights do not encode a puzzle algorithm.
        self.local = nn.Conv2d(d, d, 3, padding=1, groups=d) if kind.startswith("local") else None
        self.down = nn.Linear(d, hidden)
        self.mid = nn.ModuleList(nn.Linear(hidden, hidden) for _ in range(depth - 1))
        self.up = nn.Linear(hidden, d)
        nn.init.zeros_(self.up.weight)
        nn.init.zeros_(self.up.bias)

    def forward(self, x, geometry):
        y = self.norm(x)
        if self.local is not None:
            b, _, d = y.shape
            h, w = geometry
            spatial = y.transpose(1, 2).reshape(b, d, h, w)
            if self.kind == "local_manual":
                from fast_depthwise import depthwise3x3
                y = depthwise3x3(spatial, self.local.weight, self.local.bias)
            else:
                y = self.local(spatial)
            y = y.flatten(2).transpose(1, 2)
        y = F.gelu(self.down(y))
        for layer in self.mid:
            y = F.gelu(layer(y))
        return self.up(y)


class ResidualBank(nn.Module):
    def __init__(self, d=256, experts=8, active=2, hidden=64, depth=3, local=False):
        super().__init__()
        self.active = active
        self.typed = local in ("symbols", "counts")
        self.count_lane = local == "counts"
        self.router_norm = nn.LayerNorm(2 * d)
        self.router = nn.Linear(2 * d, experts)
        if local in ("operators", "symbols", "counts"):
            from relational_expert import RelationalDeltaExpert
            if local == "symbols":
                from symbol_transport import SymbolTransportExpert
                relation_class = SymbolTransportExpert
            elif local == "counts":
                from count_workspace import RawMassExpert
                relation_class = RawMassExpert
            else:
                relation_class = RelationalDeltaExpert
            # Separate hypothesis: local propagation AND learned relations.
            # Both operators include deep hidden transforms; all are learned.
            self.experts = nn.ModuleList(
                DeltaExpert(d, hidden, depth, "local_manual") if i % 2 else
                relation_class(d, hidden, depth) for i in range(experts))
        else:
            self.experts = nn.ModuleList(
                DeltaExpert(d, hidden, depth, ("local_manual" if local == "manual" else "local")
                            if local and i % 2 else "mlp")
                for i in range(experts))
        self.last_logits = self.last_indices = self.aux = None

    def forward(self, x, input_e, geometry):
        context = self.router_norm(torch.cat((x.mean(1), input_e.mean(1)), -1))
        logits = self.router(context).float()
        if self.typed:
            if self.active != 2 or len(self.experts) % 2:
                raise ValueError("typed transport needs two active experts and equal kind pools")
            # One transport and one local operator per step. Sparse choices
            # within each kind still change with problem and recurrent state.
            v0, i0 = logits[:, ::2].max(-1)
            v1, i1 = logits[:, 1::2].max(-1)
            vals, ids = torch.stack((v0, v1), -1), torch.stack((2 * i0, 2 * i1 + 1), -1)
        else:
            vals, ids = logits.topk(self.active, -1)
        # Unnormalized sigmoid retains a task gradient even when k=1. Dividing
        # by constant k bounds the branch without canceling the router signal.
        gates = vals.sigmoid().to(x.dtype) / self.active
        out = torch.zeros_like(x)
        mass_features = x.new_zeros(*x.shape[:2], 2) if self.count_lane else None
        for i, expert in enumerate(self.experts):
            rows, slots = (ids == i).nonzero(as_tuple=True)
            if rows.numel():
                if expert.kind == "relational":
                    delta = expert(x[rows], geometry, input_e=input_e[rows])
                    if mass_features is not None:
                        value = expert.last_mass * gates[rows, slots, None, None]
                        mass_features = mass_features.index_add(0, rows, value)
                else:
                    delta = expert(x[rows], geometry)
                delta = delta * gates[rows, slots, None, None]
                out = out.index_add(0, rows, delta)
        self.last_logits, self.last_indices = logits, ids.detach()
        if mass_features is not None:
            self.mass_features = mass_features
        fraction = F.one_hot(ids, len(self.experts)).float().mean((0, 1)).detach()
        balance = len(self.experts) * (fraction * logits.softmax(-1).mean(0)).sum()
        self.aux = .001 * balance + .0001 * logits.logsumexp(-1).square().mean()
        return out


class SleepMoE(N.Net):
    def __init__(self, source, experts=8, active=2, hidden=64, depth=3, local=False,
                 freeze_shared=True):
        nn.Module.__init__(self)
        self.arm = "loop"
        # Retain the exact shared source computation and its positional scheme.
        for name in ("tok", "slot", "blocks", "ln_out", "head", "ln_state", "halt"):
            setattr(self, name, copy.deepcopy(getattr(source, name)))
        for p in self.parameters():
            p.requires_grad_(not freeze_shared)
        d = self.tok.embedding_dim
        self.banks = nn.ModuleList(ResidualBank(d, experts, active, hidden, depth, local)
                                   for _ in self.blocks)
        self.delta_tok = nn.Embedding(self.tok.num_embeddings, d)
        self.delta_slot = nn.Embedding(2, d)
        self.delta_head = nn.Linear(d, self.head.out_features)
        self.delta_halt = nn.Linear(d, 1)
        for module in (self.delta_tok, self.delta_slot, self.delta_head, self.delta_halt):
            for p in module.parameters():
                nn.init.zeros_(p)
        self.geometry = None

    def embed(self, tokens, slots):
        self.geometry = tuple(tokens.shape[1:])
        e, offsets = super().embed(tokens, slots)
        b = tokens.shape[0]
        e = e + self.delta_tok(tokens.reshape(b, -1)) + self.delta_slot(slots.reshape(b, -1))
        return e, offsets

    def step(self, h, e, dr, dc):
        z = h + e
        for block, bank in zip(self.blocks, self.banks):
            z = block(z, dr, dc)
            z = z + bank(z, e, self.geometry)
        return self.ln_state(z)

    def read(self, h):
        z = self.ln_out(h)
        return self.head(z) + self.delta_head(z), (self.halt(z.mean(1)) +
                                                 self.delta_halt(z.mean(1))).squeeze(-1)

    def auxiliary(self):
        values = [b.aux for b in self.banks if b.aux is not None]
        return torch.stack(values).mean() if values else self.tok.weight.new_zeros(())

    def trainable_count(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def selftest():
    torch.set_num_threads(2)
    torch.manual_seed(7)
    source = N.Net("loop")
    net = SleepMoE(source, local=True)
    t = torch.randint(source.tok.num_embeddings, (2, 7, 7))
    s = torch.ones_like(t)
    a = source.loop_train(t, s, 1, 2)
    b = net.loop_train(t, s, 1, 2)
    error = max(float((u[0] - v[0]).detach().abs().max()) for u, v in zip(a, b))
    assert error < 1e-5, error
    assert all(torch.equal(u[0].argmax(-1), v[0].argmax(-1)) for u, v in zip(a, b))
    loss = b[-1][0].square().mean() + net.auxiliary()
    loss.backward()
    assert all(p.grad is None for p in net.blocks.parameters())
    assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in net.banks.parameters())
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in net.parameters())
    return {"source_conversion_max_error": error, "stored": net.weight_count(),
            "trainable": net.trainable_count(), "trained": False}


if __name__ == "__main__":
    import json
    print(json.dumps(selftest()))
