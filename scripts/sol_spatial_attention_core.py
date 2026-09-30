"""Qualified attention loop with genuinely sparse, upcycled MLP replacements.

Only selected experts execute. No dense MLP runs beside the bank. No English,
task solver, routing kind, GRU or notebook text bypass exists in this core.
The initial two blocks preserve the qualified source; many-layer growth is later.
"""
from __future__ import annotations
import copy
import sys
from pathlib import Path
import torch
from torch import nn
from torch.nn import functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_net as N


class UpcycledMLP(nn.Module):
    def __init__(self, mlp, width=256, experts=8, active=2):
        super().__init__()
        self.active = active
        self.experts = nn.ModuleList(copy.deepcopy(mlp) for _ in range(experts))
        self.router = nn.Linear(width, experts)
        # Exactly equal clones at conversion; router is learned during training.
        nn.init.zeros_(self.router.weight); nn.init.zeros_(self.router.bias)
        self.last_counts = None

    def forward(self, x):
        shape = x.shape; x = x.reshape(-1, shape[-1])
        logits = self.router(x).float()
        values, ids = logits.topk(self.active, -1)
        weights = values.softmax(-1).to(x.dtype)
        out = torch.zeros_like(x)
        for i, expert in enumerate(self.experts):
            positions, slots = torch.where(ids == i)
            if positions.numel():
                out = out.index_add(0, positions, expert(x[positions]) * weights[positions, slots, None])
        self.last_counts = torch.bincount(ids.detach().flatten(), minlength=len(self.experts)).cpu().tolist()
        # Balancing reaches unselected router logits, preventing top-k-only starvation.
        fraction = F.one_hot(ids, len(self.experts)).float().mean((0, 1)).detach()
        self.aux = .001 * len(self.experts) * (fraction * logits.softmax(-1).mean(0)).sum()
        return out.reshape(shape)


class AttentionReasoner(N.Net):
    def __init__(self, source, experts=8, active=2):
        nn.Module.__init__(self)
        self.arm = "loop"
        self.experts_count, self.active_count = experts, active
        for name in ("tok", "slot", "blocks", "ln_out", "head", "ln_state", "halt"):
            setattr(self, name, copy.deepcopy(getattr(source, name)))
        for block in self.blocks:
            block.mlp = UpcycledMLP(block.mlp, self.tok.embedding_dim, experts, active)

    def auxiliary(self):
        return torch.stack([b.mlp.aux for b in self.blocks]).mean()

    def counts(self):
        per_expert = sum(p.numel() for p in self.blocks[0].mlp.experts[0].parameters())
        stored = sum(p.numel() for p in self.parameters())
        return {"stored_parameters": stored, "trainable_parameters": sum(p.numel() for p in self.parameters() if p.requires_grad),
                "blocks_per_loop": len(self.blocks), "width": self.tok.embedding_dim,
                "experts_per_MLP": self.experts_count, "active_per_token_per_MLP": self.active_count,
                "parameters_per_MLP_expert": per_expert,
                "active_parameter_accounting": stored - len(self.blocks) * (self.experts_count - self.active_count) * per_expert,
                "accounting_not_FLOPs_or_speed": True}

    def begin_latent(self, latent, notebook=None):
        """Thin translator supplies [B,H,W,256], notebook [B,M,256] with provenance.

        Notebook states enter the same learned attention on every round. They
        are never decoded directly to the user. Empty notebook preserves source
        geometry; appended notebook positions use neutral relative bias indices.
        This new notebook behavior is mechanics-only, not qualified by source.
        """
        if latent.ndim != 4 or latent.shape[-1] != 256:
            raise ValueError("expected translator latent [B,H,W,256]")
        b, h, w, d = latent.shape
        e = latent.reshape(b, h * w, d)
        dr, dc = self.offsets(h, w, e.device)
        query_n = h * w
        if notebook is not None:
            if notebook.ndim != 3 or notebook.shape[0] != b or notebook.shape[-1] != d:
                raise ValueError("expected notebook latent [B,M,256]")
            if notebook.device != e.device or notebook.dtype != e.dtype:
                raise ValueError("notebook and query latents must share device and dtype")
            if notebook.shape[1]:
                e = torch.cat((e, notebook), 1)
                n = e.shape[1]
                extended_dr = torch.full((n, n), N.CLIP, device=e.device, dtype=torch.long)
                extended_dc = extended_dr.clone()
                extended_dr[:query_n, :query_n] = dr; extended_dc[:query_n, :query_n] = dc
                dr, dc = extended_dr, extended_dc
        return {"h": torch.zeros_like(e), "e": e, "dr": dr, "dc": dc,
                "query_n": query_n, "round": 0, "height": h, "width": w}

    def advance_latent(self, state):
        return {**state, "h": self.step(state["h"], state["e"], state["dr"], state["dc"]),
                "round": state["round"] + 1}

    def read_latent(self, state):
        # The output translator consumes this nonlinguistic tensor only.
        h = state["h"][:, :state["query_n"]]
        return h, self.halt(self.ln_out(h).mean(1)).squeeze(-1)

    @torch.no_grad()
    def reason_latent(self, latent, notebook=None, cap=48):
        """Learned halt plus existing 3-round stability guard; no answer checker.

        Returns final latent, stop probability, actual rounds, cap flag. Decoder
        head is used internally only for source stability; no text is generated.
        """
        state = self.begin_latent(latent, notebook)
        b = len(latent); done = torch.zeros(b, device=latent.device, dtype=torch.bool)
        chosen = latent.new_zeros(b, state["query_n"], 256)
        stop_q = latent.new_zeros(b); rounds = torch.full((b,), cap, device=latent.device, dtype=torch.long)
        history = []
        for r in range(1, cap + 1):
            state = self.advance_latent(state)
            h, q = self.read_latent(state)
            pred = self.head(self.ln_out(h)).argmax(-1)
            history.append(pred); history = history[-3:]
            stable = (history[-1] == history[-2]).all(1) & (history[-2] == history[-3]).all(1) if len(history) == 3 else done & False
            fire = ~done & stable & (q.sigmoid() > .5)
            chosen[fire] = h[fire]; stop_q[fire] = q.sigmoid()[fire]; rounds[fire] = r
            done |= fire
            if bool(done.all()): break
        chosen[~done] = h[~done]; stop_q[~done] = q.sigmoid()[~done]
        return {"final_latent": chosen, "stop_probability": stop_q, "rounds": rounds,
                "cap_fallback": ~done}


def load_bundle(bundle, device="cpu"):
    payload = torch.load(bundle, map_location="cpu", weights_only=True)
    source = N.Net("loop")
    model = AttentionReasoner(source, **payload["constructor"])
    model.load_state_dict(payload["state_dict"], strict=True)
    return model.to(device), payload["metadata"]
