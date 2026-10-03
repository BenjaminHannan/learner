"""D256 unshared-depth controls for the four-step human attention loop.

No training or corpus access. Sparse plain matches the fixed-depth candidate's
attention/expert calls, not stored parameters, optimizer work or learned-stop
cost. Dense plain is a separate unmatched-active-compute diagnostic.
"""
from __future__ import annotations
import copy
from pathlib import Path
import torch
from torch import nn
from sol_spatial_attention_core import AttentionReasoner, load_bundle


class PlainAttentionReasoner(nn.Module):
    """Four independent two-block segments, forming one feedforward DAG.

    advance_latent advances the depth cursor; it does NOT reuse learned blocks.
    Input is injected at each segment to preserve the initial source function.
    Source halt is retained for matched intermediate TRAIN losses only. It has
    no plain stopping qualification and cannot extend depth past the constructor.
    """
    begin_latent = AttentionReasoner.begin_latent
    read_latent = AttentionReasoner.read_latent
    offsets = staticmethod(AttentionReasoner.offsets)

    def __init__(self, parent, rounds=4, sparse=True):
        super().__init__()
        if type(rounds) is not int or not 1 <= rounds <= 16:
            raise ValueError("plain depth must be an integer in [1,16]")
        if type(sparse) is not bool or not isinstance(parent, AttentionReasoner):
            raise TypeError("qualified AttentionReasoner parent and boolean sparse required")
        self.arm = "plain-unshared-D256"
        self.rounds, self.sparse = rounds, sparse
        self.blocks_per_segment = len(parent.blocks)
        self.experts_count = parent.experts_count if sparse else 1
        self.active_count = parent.active_count if sparse else 1
        for name in ("tok", "slot", "ln_out", "head", "halt"):
            setattr(self, name, copy.deepcopy(getattr(parent, name)))
        self.blocks = nn.ModuleList()
        self.state_norms = nn.ModuleList()
        for _ in range(rounds):
            for original in parent.blocks:
                block = copy.deepcopy(original)
                if not sparse:
                    block.mlp = copy.deepcopy(original.mlp.experts[0])
                self.blocks.append(block)
            self.state_norms.append(copy.deepcopy(parent.ln_state))

    def advance_latent(self, state):
        r = state["round"]
        if type(r) is not int or not 0 <= r < self.rounds:
            raise ValueError("plain depth exhausted; this control cannot loop")
        z = state["h"] + state["e"]
        start = r * self.blocks_per_segment
        for block in self.blocks[start:start + self.blocks_per_segment]:
            z = block(z, state["dr"], state["dc"])
        return {**state, "h": self.state_norms[r](z), "round": r + 1}

    def forward_latent(self, latent, notebook=None):
        state = self.begin_latent(latent, notebook)
        for _ in range(self.rounds):
            state = self.advance_latent(state)
        return self.read_latent(state)

    def auxiliary(self):
        if not self.sparse:
            return self.tok.weight.new_zeros(())
        terms = [b.mlp.aux for b in self.blocks if hasattr(b.mlp, "aux")]
        if not terms:
            return self.tok.weight.new_zeros(())
        # Average all visited blocks, matching loop's per-round mean only when
        # the driver accumulates the loop auxiliary over all four rounds too.
        return torch.stack(terms).mean()

    def counts(self):
        stored = sum(p.numel() for p in self.parameters())
        expert = self.blocks[0].mlp.experts[0] if self.sparse else self.blocks[0].mlp
        per_expert = sum(p.numel() for p in expert.parameters())
        inactive = len(self.blocks) * (self.experts_count - self.active_count) * per_expert
        return {"stored_parameters": stored,
                "trainable_parameters": sum(p.numel() for p in self.parameters() if p.requires_grad),
                "width": 256, "segments": self.rounds,
                "blocks_per_segment": self.blocks_per_segment,
                "distinct_blocks": len(self.blocks), "shared_blocks": False,
                "experts_per_MLP": self.experts_count,
                "active_per_token_per_MLP": self.active_count,
                "parameters_per_MLP_expert": per_expert,
                "active_parameter_accounting": stored - inactive,
                "attention_block_calls_per_full_pass": len(self.blocks),
                "selected_expert_token_calls_per_full_pass": len(self.blocks) * self.active_count,
                "accounting_not_FLOPs_or_speed": True}

    def constructor(self):
        return {"family": "plain-unshared-D256-v1", "rounds": self.rounds,
                "sparse": self.sparse, "experts": self.experts_count,
                "active": self.active_count}


def make_plain_parent(parent, *, rounds=4, sparse=True):
    return PlainAttentionReasoner(parent, rounds=rounds, sparse=sparse)


def make_plain_source(source, variant="sparse_unrolled4"):
    """Driver factory from qualified dense source OR exact upcycled core.

    The primary comparator is sparse_unrolled4. dense_unrolled4 is optional
    and differs in selected-MLP work. Callers supply seed/manifest in metadata.
    """
    if variant not in ("sparse_unrolled4", "dense_unrolled4"):
        raise ValueError("unknown plain variant")
    parent = source if isinstance(source, AttentionReasoner) else AttentionReasoner(source)
    return make_plain_parent(parent, rounds=4, sparse=variant == "sparse_unrolled4")


def plain_bundle_payload(model, metadata):
    if not isinstance(model, PlainAttentionReasoner):
        raise TypeError("plain parent required")
    return {"constructor": model.constructor(),
            "state_dict": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
            "metadata": dict(metadata)}


def load_plain_bundle(bundle, device="cpu", *, rounds=4, sparse=True):
    """Load saved plain parent OR construct from an exact upcycled parent bundle.

    Upcycled input is a conversion, not a trained human plain checkpoint.
    Saved plain bundle's own constructor overrides conversion defaults.
    """
    payload = torch.load(Path(bundle), map_location="cpu", weights_only=True)
    constructor = payload.get("constructor", {})
    if constructor.get("family") == "plain-unshared-D256-v1":
        from sol_spatial_attention_core import N
        source = N.Net("loop")
        # Dense constructors need only one expert in their temporary skeleton.
        parent = AttentionReasoner(source, experts=constructor["experts"],
                                   active=constructor["active"])
        model = make_plain_parent(parent, rounds=constructor["rounds"],
                                  sparse=constructor["sparse"])
        model.load_state_dict(payload["state_dict"], strict=True)
        return model.to(device), payload["metadata"]
    if set(constructor) != {"experts", "active"}:
        raise ValueError("unsupported bundle constructor")
    parent, metadata = load_bundle(bundle, "cpu")
    model = make_plain_parent(parent, rounds=rounds, sparse=sparse).to(device)
    return model, {**metadata, "plain_conversion_only": True,
                   "human_trained": False, "plain_constructor": model.constructor()}
