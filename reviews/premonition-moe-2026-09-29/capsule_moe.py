"""Hierarchical PROGRAM capsules with one immutable macroexpert per problem.

Prototype: two COMPLETE cores, not a million-small-expert architecture. Capsule
0 is the original qualified dense source; capsule 1 is an acquired body with
its existing residual microexperts and actual E/k in each block. Only
the input router learns. It sees frozen SOURCE embeddings and observed shape /
fill-mask statistics, never task IDs, targets, a checker, or expert outputs.

The inherited N.Net loop APIs select a macroexpert once in embed() and use it
throughout the trajectory. A batch can contain both routes. Each selected row
uses its own capsule's embedding, blocks, state norm, readout and halt head.
The returned embedding/state has 257 channels: 256 learned channels plus one
explicit route-control channel, repeated over tokens. step() dispatches from e;
read() dispatches from h. No cached per-batch routes or embeddings are needed,
so an executor may compact arbitrary rows between rounds. Spatial geometry
remains shared by the problem batch, as in the original acquired-body API.
"""
from __future__ import annotations

from pathlib import Path
import sys

import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import claude_fewex_net as N


def parameter_count(module):
    return sum(p.numel() for p in module.parameters())


class InputRouter(nn.Module):
    """Train-memory standardization followed by a small 32-hidden-unit MLP."""

    def __init__(self, features, hidden=32):
        super().__init__()
        self.register_buffer("mean", torch.zeros(features))
        self.register_buffer("scale", torch.ones(features))
        self.mlp = nn.Sequential(nn.Linear(features, hidden), nn.GELU(), nn.Linear(hidden, 2))

    @torch.no_grad()
    def standardize_from_train(self, features):
        self.mean.copy_(features.mean(0))
        self.scale.copy_(features.std(0, unbiased=False).clamp_min(.05))

    def forward(self, features):
        return self.mlp((features - self.mean) / self.scale)


class CapsuleMoE(N.Net):
    def __init__(self, original_source, acquired_body, router_hidden=32):
        nn.Module.__init__(self)
        self.arm = "loop"
        self.capsules = nn.ModuleList((original_source, acquired_body))
        d = original_source.tok.embedding_dim
        if acquired_body.tok.embedding_dim != d or original_source.head.out_features != 125:
            raise ValueError("capsules must share width and the original 125-class vocabulary")
        if acquired_body.head.out_features != 125:
            raise ValueError("acquired capsule must retain all 125 output classes")
        banks = getattr(acquired_body, "banks", None)
        if banks is None:
            # Fair program-isolation control: an acquired dense reasoner is a
            # valid macroexpert, with no microexpert sparsity or routing.
            banks = ()
        elif len(banks) != len(acquired_body.blocks) or not len(banks):
            raise ValueError("acquired body must have one nonempty microbank per block")
        for bank in banks:
            experts = len(bank.experts)
            if type(bank.active) is not int or not 1 <= bank.active <= experts:
                raise ValueError("each microbank requires integer 1 <= k <= E")
            if bank.router.out_features != experts:
                raise ValueError("microbank router output count must equal E")
        for capsule in self.capsules:
            capsule.eval()
            for p in capsule.parameters():
                p.requires_grad_(False)
                p.grad = None
        self.router = InputRouter(3 * d + 3, router_hidden)
        self.state_width = d
        self.geometry = None
        self.last_routes = self.last_route_logits = None
        self._expert_sizes = tuple(tuple(parameter_count(e) for e in bank.experts)
                                   for bank in banks)
        self._active_k = tuple(bank.active for bank in banks)
        self._acquired_always = parameter_count(acquired_body) - sum(map(sum, self._expert_sizes))
        self._source_count = parameter_count(original_source)
        self.reset_activity()

    def train(self, mode=True):
        super().train(mode)
        for capsule in self.capsules:
            capsule.eval()
        return self

    def reset_activity(self):
        self.activity = {"problem_rounds": 0, "source_problem_rounds": 0,
                         "acquired_problem_rounds": 0, "active_core_parameter_sum": 0,
                         "active_core_parameter_min": None, "active_core_parameter_max": None,
                         "microexpert_dispatch_counts_per_block": [[0] * len(sizes) for sizes in self._expert_sizes]}

    @torch.no_grad()
    def routing_features(self, tokens, slots, source_e=None):
        if source_e is None:
            source_e, _ = self.capsules[0].embed(tokens, slots)
        mask = slots.reshape(len(tokens), -1).bool().unsqueeze(-1)
        masked = (source_e * mask).sum(1) / mask.sum(1).clamp_min(1)
        unmasked = (source_e * ~mask).sum(1) / (~mask).sum(1).clamp_min(1)
        observed = source_e.new_tensor([tokens.shape[1] / 16, tokens.shape[2] / 16])
        geometry = observed.expand(len(tokens), -1)
        fraction = mask.float().mean(1)
        return torch.cat((masked, unmasked, source_e.mean(1), geometry, fraction), -1).detach()

    def route_logits(self, features):
        return self.router(features)

    def embed(self, tokens, slots):
        with torch.no_grad():
            source_e, offsets = self.capsules[0].embed(tokens, slots)
            features = self.routing_features(tokens, slots, source_e)
        logits = self.route_logits(features)
        routes = logits.detach().argmax(-1)
        rows = tuple((routes == i).nonzero(as_tuple=True)[0] for i in range(2))
        selected = torch.zeros_like(source_e)
        with torch.no_grad():
            for i, indices in enumerate(rows):
                if not len(indices):
                    continue
                if i == 0:
                    e = source_e.index_select(0, indices)
                else:
                    e, other_offsets = self.capsules[i].embed(tokens.index_select(0, indices),
                                                              slots.index_select(0, indices))
                    if not all(torch.equal(a, b) for a, b in zip(offsets, other_offsets)):
                        raise ValueError("expert geometry differs")
                selected.index_copy_(0, indices, e)
        self.geometry = tuple(tokens.shape[1:])
        self.last_routes, self.last_route_logits = routes, logits.detach()
        control = routes.to(selected.dtype)[:, None, None].expand(-1, selected.shape[1], 1)
        return torch.cat((selected, control), -1), offsets

    def _routes(self, state):
        if state.ndim != 3 or state.shape[-1] != self.state_width + 1:
            raise ValueError("expected 256 learned channels plus one explicit route-control channel")
        routes = state[:, 0, -1].long()
        if not bool(((routes == 0) | (routes == 1)).all()):
            raise ValueError("route-control channel must identify source 0 or acquired 1")
        return routes

    def step(self, h, e, dr, dc):
        routes = self._routes(e)
        if h.shape != e.shape:
            raise ValueError("wrong per-capsule embedding shape")
        rows = tuple((routes == i).nonzero(as_tuple=True)[0] for i in range(2))
        result = torch.zeros_like(h[..., :self.state_width])
        active = torch.full((len(h),), self._source_count, dtype=torch.long, device=h.device)
        for i, indices in enumerate(rows):
            if not len(indices):
                continue
            capsule = self.capsules[i]
            if i == 1:
                if self.geometry is None or self.geometry[0] * self.geometry[1] != h.shape[1]:
                    raise RuntimeError("embed() must set matching spatial geometry")
                capsule.geometry = self.geometry
            state = capsule.step(h.index_select(0, indices)[..., :self.state_width],
                                 e.index_select(0, indices)[..., :self.state_width], dr, dc)
            result.index_copy_(0, indices, state)
            if i == 1:
                counts = torch.full((len(indices),), self._acquired_always,
                                    dtype=torch.long, device=h.device)
                for block, (bank, sizes) in enumerate(zip(getattr(capsule, "banks", ()), self._expert_sizes)):
                    ids = bank.last_indices
                    sizes_t = torch.tensor(sizes, dtype=torch.long, device=h.device)
                    counts += sizes_t[ids].sum(-1)
                    histogram = torch.bincount(ids.flatten(), minlength=len(sizes)).tolist()
                    stored = self.activity["microexpert_dispatch_counts_per_block"][block]
                    self.activity["microexpert_dispatch_counts_per_block"][block] = [a + b for a, b in zip(stored, histogram)]
                active.index_copy_(0, indices, counts)
        a = self.activity
        a["problem_rounds"] += len(h)
        a["source_problem_rounds"] += len(rows[0])
        a["acquired_problem_rounds"] += len(rows[1])
        a["active_core_parameter_sum"] += int(active.sum())
        lo, hi = int(active.min()), int(active.max())
        a["active_core_parameter_min"] = lo if a["active_core_parameter_min"] is None else min(lo, a["active_core_parameter_min"])
        a["active_core_parameter_max"] = hi if a["active_core_parameter_max"] is None else max(hi, a["active_core_parameter_max"])
        return torch.cat((result, e[..., -1:]), -1)

    def read(self, h):
        routes = self._routes(h)
        logits = h.new_zeros(len(h), h.shape[1], 125)
        halt = h.new_zeros(len(h))
        for i in range(2):
            indices = (routes == i).nonzero(as_tuple=True)[0]
            if len(indices):
                lg, q = self.capsules[i].read(h.index_select(0, indices)[..., :self.state_width])
                logits.index_copy_(0, indices, lg)
                halt.index_copy_(0, indices, q)
        return logits, halt

    def counts(self):
        source, acquired = map(parameter_count, self.capsules)
        router = parameter_count(self.router)
        source_embeddings = parameter_count(self.capsules[0].tok) + parameter_count(self.capsules[0].slot)
        minimum = self._acquired_always + sum(sum(sorted(x)[:k]) for x, k in zip(self._expert_sizes, self._active_k))
        maximum = self._acquired_always + sum(sum(sorted(x)[-k:]) for x, k in zip(self._expert_sizes, self._active_k))
        return {"source_core": source, "acquired_core": acquired, "router": router,
                "stored_parameters": self.weight_count(), "trainable_parameters": router,
                "router_standardization_buffer_floats": sum(b.numel() for b in self.router.buffers()),
                "stored_parameter_bytes_fp32": 4 * self.weight_count(),
                "overhead_parameters_vs_acquired_body": source + router,
                "stored_ratio_vs_acquired_body": self.weight_count() / acquired,
                "learned_state_channels": self.state_width, "route_control_channels": 1,
                "state_and_embedding_shape": "B,N,257; final channel is explicit immutable route metadata",
                "route_metadata_bytes_per_token_per_tensor_fp32": 4,
                "route_metadata_overhead_relative_to_256_channels": 1 / self.state_width,
                "active_source_core": source, "active_acquired_always": self._acquired_always,
                "microbank_config": [{"E": len(sizes), "k": k,
                                      "all_experts_active": k == len(sizes)}
                                     for sizes, k in zip(self._expert_sizes, self._active_k)],
                "microexpert_parameter_sizes_per_block": self._expert_sizes,
                "active_acquired_core_per_loop_min": minimum,
                "active_acquired_core_per_loop_max": maximum,
                "source_embedding_parameters_once_per_problem": source_embeddings,
                "active_source_including_input_router": source + router,
                "active_acquired_including_input_router_and_source_features_min": minimum + router + source_embeddings,
                "active_acquired_including_input_router_and_source_features_max": maximum + router + source_embeddings,
                "definition": "per-problem per-loop selected weight sets including input/readout; input embeddings and macro router actually execute once. Microexpert choices can change across rounds, so trajectory unions can exceed per-loop active counts. Counts are not FLOPs or measured speedups."}
