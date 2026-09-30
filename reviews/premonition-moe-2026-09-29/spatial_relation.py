"""Small learned local loop; synthetic mechanics only via --selftest.

No task/checker imports, token semantics, source blocks, source head, or solver.
Only a copied frozen [125,256] lexical embedding comes from the supplied source.
SpatialRelation(...)(tokens, slots, rounds=12) -> [B,2,H,W,125], full BPTT.
embed/initial_state/step/read expose the same loop as a self-contained tensor.
"""
from __future__ import annotations

import math

import torch
from torch import Tensor, nn
from torch.nn import functional as F


VOCAB = 125
SOURCE_WIDTH = 256
STENCIL = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))


class SpatialMessageExpert(nn.Module):
    """Three hidden MLP transforms; directed endpoint/direction -> gate+message."""

    def __init__(self, endpoint_width, pair_width, message_width):
        super().__init__()
        self.body = nn.Sequential(
            nn.Linear(2 * endpoint_width + 2, pair_width), nn.SiLU(),
            nn.Linear(pair_width, pair_width), nn.SiLU(),
            nn.Linear(pair_width, pair_width), nn.SiLU())
        self.output = nn.Linear(pair_width, message_width + 1)

    def statistics(self, pairs, valid):
        values = self.output(self.body(pairs))
        # FP32 reductions, including gate mass. Boundary masks are geometric only.
        gate = values[..., :1].float().sigmoid() * valid[..., None].float()
        message = values[..., 1:].float().tanh()
        total = (gate * torch.cat((message, torch.ones_like(gate)), -1)).sum(-2)
        mean = total / gate.sum(-2).clamp_min(torch.finfo(torch.float32).eps)
        return total.to(pairs.dtype), mean.to(pairs.dtype)

    def forward(self, pairs, valid, *, raw_sum=True):
        total, mean = self.statistics(pairs, valid)
        return torch.cat((total if raw_sum else mean, mean), -1)


class SpatialRelation(nn.Module):
    """One recurrent candidate with two sparse learned message experts.

    State is [B,N,2*width+public_width+15]. It stores immutable translated
    input, hidden/public, answer slots, initialized flag, rounds, H/W, and five
    local neighbor indices/validities. No batch tensors live on the module.
    Rows of the B axis can be permuted/removed freely. Grid row permutations
    are NOT a symmetry: spatial adjacency/coordinates are an explicit prior.

    All controls have identical parameter names/shapes. Load the same state_dict
    for matched controls; top_k/raw_sum are constructor flags, not checkpoint
    tensors. identical_experts copies expert 0 to 1 once, without weight tying.
    The default halt output is a constant UNCALIBRATED -20, not success.
    """

    def __init__(self, source_embedding: nn.Embedding | Tensor, *, width=48,
                 public_width=8, endpoint_width=24, pair_width=32,
                 message_width=8, expert_count=None, top_k=None,
                 experts=None, active=None, raw_sum=True,
                 identical_experts=False, read_halt=None, halt_placeholder=-20.):
        super().__init__()
        weight = source_embedding.weight if isinstance(source_embedding, nn.Embedding) else source_embedding
        if (not isinstance(weight, Tensor) or weight.shape != (VOCAB, SOURCE_WIDTH)
                or not weight.is_floating_point()):
            raise ValueError("source_embedding must be a floating [125,256] embedding or tensor")
        if any(type(v) is not int or v < 1 for v in
               (width, public_width, endpoint_width, pair_width, message_width)):
            raise ValueError("all widths must be positive integers")
        def resolve(primary, alias, default, name):
            if any(v is not None and type(v) is not int for v in (primary, alias)):
                raise ValueError(name + " must be an integer")
            if primary is not None and alias is not None and primary != alias:
                raise ValueError("conflicting " + name + " aliases")
            return primary if primary is not None else (default if alias is None else alias)
        expert_count = resolve(expert_count, experts, 2, "expert_count/experts")
        top_k = resolve(top_k, active, 1, "top_k/active")
        if type(expert_count) is not int or expert_count != 2:
            raise ValueError("this candidate requires exactly two experts")
        if type(top_k) is not int or not 1 <= top_k <= expert_count:
            raise ValueError("top_k must be integer 1 or 2")
        if type(raw_sum) is not bool or type(identical_experts) is not bool:
            raise ValueError("control flags must be bool")
        if not math.isfinite(halt_placeholder):
            raise ValueError("halt_placeholder must be finite")
        self.arm = "loop"
        self.width, self.public_width = width, public_width
        self.expert_count, self.top_k, self.raw_sum = expert_count, top_k, raw_sum
        self.identical_experts = identical_experts
        self.halt_placeholder = float(halt_placeholder)
        self.source = nn.Embedding.from_pretrained(weight.detach().clone(), freeze=True)
        self.source_projection = nn.Linear(SOURCE_WIDTH, width)
        self.fill = nn.Embedding(2, width)
        self.coordinate_projection = nn.Linear(2, width, bias=False)
        context_width = 2 * width + public_width
        self.endpoint = nn.Linear(context_width, endpoint_width)
        self.router = nn.Linear(2 * context_width, expert_count)
        self.experts = nn.ModuleList(SpatialMessageExpert(endpoint_width, pair_width, message_width)
                                     for _ in range(expert_count))
        if identical_experts:
            self.experts[1].load_state_dict(self.experts[0].state_dict())
        aggregate_width = 2 * (message_width + 1)
        self.public_proposal = nn.Linear(width + aggregate_width, public_width)
        self.public_retention = nn.Linear(width + public_width, public_width)
        self.recurrent = nn.GRUCell(width + aggregate_width + public_width, width)
        self.read_features = nn.Linear(2 * width, width)
        self.lexical_head = nn.Linear(width + public_width, VOCAB)
        self.register_buffer("directions", torch.tensor(STENCIL, dtype=weight.dtype))
        self.anchor_channels = slice(0, width)
        self.hidden_channels = slice(width, 2 * width)
        self.public_channels = slice(2 * width, context_width)
        self.dynamic_channels = slice(width, context_width)
        (self.answer_mask_channel, self.initialized_channel, self.round_channel,
         self.rows_channel, self.cols_channel) = range(context_width, context_width + 5)
        self.neighbor_channels = slice(context_width + 5, context_width + 10)
        self.valid_channels = slice(context_width + 10, context_width + 15)
        self.state_width = context_width + 15
        self.set_read_halt(read_halt)
        self.to(device=weight.device, dtype=weight.dtype)

    @property
    def tok(self):
        return self.source

    @property
    def head(self):
        return self.lexical_head

    @property
    def halt_kind(self):
        return "external_output_callback" if self.read_halt is not None else "constant_uncalibrated_placeholder"

    def set_read_halt(self, callback):
        """Optional callback(logits[B,N,125], mask[B,N], rounds[B]) -> q[B]."""
        if callback is not None and not callable(callback):
            raise TypeError("read_halt must be callable or None")
        if "read_halt" in self._modules:
            delattr(self, "read_halt")
        self.read_halt = callback
        return self

    def _check_state(self, state):
        if (not isinstance(state, Tensor) or state.ndim != 3 or state.shape[1] < 1
                or state.shape[2] != self.state_width):
            raise ValueError("expected [B,N,state_width] with positive N")
        if state.device != self.source.weight.device or state.dtype != self.source.weight.dtype:
            raise ValueError("state and model must share device and dtype")

    def embed(self, tokens, slots):
        """Return readable round-zero e, (dr,dc); O(N*5), zero source blocks.

        dr/dc are length-five stencil offsets for interface compatibility only.
        step uses the geometry inside its state and ignores external offsets.
        Tokens are int64 [B,H,W]; slots are a binary tensor of that shape.
        """
        if (tokens.ndim != 3 or tokens.shape != slots.shape or min(tokens.shape) < 1
                or tokens.dtype != torch.long):
            raise ValueError("tokens must be nonempty int64 [B,H,W]; slots must match")
        if tokens.device != self.source.weight.device or slots.device != tokens.device:
            raise ValueError("tokens, slots and model must share device")
        if bool(((tokens < 0) | (tokens >= VOCAB)).any()):
            raise ValueError("token outside full 125-token vocabulary")
        if bool(((slots != 0) & (slots != 1)).any()):
            raise ValueError("slots must be binary")
        b, rows, cols = tokens.shape
        n = rows * cols
        # Indices live in the floating state: reject lossy integer metadata once.
        indices = torch.arange(n, device=tokens.device)
        if (not torch.equal(indices.to(self.source.weight.dtype).long(), indices)
                or int(self.source.weight.new_tensor(rows)) != rows
                or int(self.source.weight.new_tensor(cols)) != cols):
            raise ValueError("grid indices/dimensions are not exactly representable in state dtype")
        row, col = indices // cols, indices % cols
        coordinates = torch.stack((row.to(self.source.weight.dtype) / max(rows - 1, 1),
                                   col.to(self.source.weight.dtype) / max(cols - 1, 1)), -1)
        anchor = torch.tanh(self.source_projection(self.source(tokens).reshape(b, n, SOURCE_WIDTH))
                            + self.fill(slots.reshape(b, n).long())
                            + self.coordinate_projection(coordinates)[None])
        delta = self.directions.long()
        nr, nc = row[:, None] + delta[:, 0], col[:, None] + delta[:, 1]
        valid = (nr >= 0) & (nr < rows) & (nc >= 0) & (nc < cols)
        neighbor = torch.where(valid, nr * cols + nc, indices[:, None])
        def constant(value):
            return anchor.new_full((b, n, 1), value)
        metadata = torch.cat((slots.reshape(b, n, 1).to(anchor.dtype), constant(1),
                              constant(0), constant(rows), constant(cols),
                              neighbor[None].expand(b, n, 5).to(anchor.dtype),
                              valid[None].expand(b, n, 5).to(anchor.dtype)), -1)
        state = torch.cat((anchor, anchor.new_zeros(b, n, self.width + self.public_width), metadata), -1)
        return state, (self.directions[:, 0], self.directions[:, 1])

    def initial_state(self, e):
        """Clone embed's readable round-zero state (without detaching gradients)."""
        self._check_state(e)
        return e.clone()

    def route(self, state):
        """Return selected probabilities and IDs, both [B,N,k], with no cache.

        Pool ONLY within each example. Keep probabilities from the full two-way
        softmax, without top-k renormalization: top1 router gradients survive.
        Routing sees local content/state/coordinates and pooled problem content.
        """
        context = state[..., :self.public_channels.stop]
        problem = context.mean(1, keepdim=True).expand_as(context)
        probabilities = self.router(torch.cat((context, problem), -1)).float().softmax(-1)
        weights, selected = probabilities.topk(self.top_k, dim=-1)
        return weights.to(state.dtype), selected

    def communicate(self, state):
        """Only selected experts execute, each on five pairs per assigned cell."""
        b, n = state.shape[:2]
        context = state[..., :self.public_channels.stop]
        endpoints = F.silu(self.endpoint(context))
        neighbors = state[..., self.neighbor_channels].long()
        batch_offset = torch.arange(b, device=state.device)[:, None, None] * n
        sender = endpoints.reshape(b * n, -1)[(neighbors + batch_offset).reshape(-1)]
        sender = sender.reshape(b * n, 5, -1)
        receiver = endpoints.reshape(b * n, 1, -1).expand(-1, 5, -1)
        pairs = torch.cat((receiver, sender, self.directions[None].expand(b * n, -1, -1)), -1)
        valid = state[..., self.valid_channels].reshape(b * n, 5)
        weights, selected = self.route(state)
        weights, selected = weights.reshape(b * n, self.top_k), selected.reshape(b * n, self.top_k)
        output = state.new_zeros(b * n, 2 * self.experts[0].output.out_features)
        for expert_id, expert in enumerate(self.experts):
            positions, rank = torch.where(selected == expert_id)
            if positions.numel():
                messages = expert(pairs[positions], valid[positions], raw_sum=self.raw_sum)
                output = output.index_add(0, positions, messages * weights[positions, rank, None])
        return output.reshape(b, n, -1)

    def step(self, h, e=None, dr=None, dc=None):
        """One learned loop, functional: h/e and module batch state never mutate.

        Preferred fast path: h=initial_state(embed(...)[0]), then step(h).
        zeros_like(e) plus matching e is also supported. Once initialized, h
        is authoritative even with stale e/dr/dc. Malformed hand-built state
        is outside this API; values are not rescanned/synchronized every loop.
        Geometry, slots and rounds belong to h, including after B-axis slicing.
        """
        self._check_state(h)
        if h.shape[0] == 0:
            return h
        base = h
        if e is not None and e.shape == h.shape:
            self._check_state(e)
            base = torch.where(h[..., self.initialized_channel:self.initialized_channel + 1] == 1, h, e)
        anchor = base[..., self.anchor_channels]
        hidden, public = base[..., self.hidden_channels], base[..., self.public_channels]
        aggregates = self.communicate(base)
        retention = self.public_retention(torch.cat((hidden, public), -1)).sigmoid()
        proposal = self.public_proposal(torch.cat((anchor, aggregates), -1))
        new_public = retention * public + (1. - retention) * proposal
        inputs = torch.cat((anchor, aggregates, new_public), -1)
        new_hidden = self.recurrent(inputs.flatten(0, 1), hidden.reshape(-1, self.width)).reshape_as(hidden)
        metadata = base[..., self.answer_mask_channel:]
        # Concatenation, not in-place mutation: immutable anchor/geometry persist.
        updated_metadata = torch.cat((metadata[..., :2], metadata[..., 2:3] + 1, metadata[..., 3:]), -1)
        return torch.cat((anchor, new_hidden, new_public, updated_metadata), -1)

    def answer_mask(self, h):
        self._check_state(h)
        return h[..., self.answer_mask_channel].bool()

    def rounds(self, h):
        self._check_state(h)
        return h[:, 0, self.round_channel].long()

    def iteration(self, h):
        return self.rounds(h)

    def read(self, h):
        """Full lexical logits [B,N,125], halt logits [B]; no token masking."""
        self._check_state(h)
        features = F.silu(self.read_features(h[..., :2 * self.width]))
        logits = self.lexical_head(torch.cat((features, h[..., self.public_channels]), -1))
        if self.read_halt is None or not len(h):
            q = logits.new_full((len(h),), self.halt_placeholder)
        else:
            q = self.read_halt(logits, self.answer_mask(h), self.rounds(h))
            if (not isinstance(q, Tensor) or q.shape not in ((len(h),), (len(h), 1))
                    or not q.is_floating_point() or q.device != h.device):
                raise ValueError("read_halt must return floating [B] or [B,1] on state device")
            q = q.reshape(len(h)).to(logits.dtype)
        return logits, q

    def forward(self, tokens, slots, *, rounds=12, grad_rounds=None, output_rounds=None):
        """[B,len(reads),H,W,125]; default final two reads, FULL differentiability.

        grad_rounds=None keeps all rounds (12 or 24); a positive integer opts
        into detached burn-in. Explicit output_rounds are increasing 1-based
        steps, inside the retained window when grad mode is enabled.
        """
        if type(rounds) is not int or rounds < 1:
            raise ValueError("rounds must be a positive integer")
        if grad_rounds is None:
            grad_rounds = rounds
        if type(grad_rounds) is not int or not 1 <= grad_rounds <= rounds:
            raise ValueError("grad_rounds must be None or in [1,rounds]")
        reads = ((rounds - 1, rounds) if rounds > 1 else (1,)) if output_rounds is None else tuple(output_rounds)
        if (not reads or any(type(r) is not int or not 1 <= r <= rounds for r in reads)
                or any(a >= b for a, b in zip(reads, reads[1:]))):
            raise ValueError("output_rounds must be strictly increasing valid steps")
        track, burn = torch.is_grad_enabled(), rounds - grad_rounds
        if track and reads[0] <= burn:
            raise ValueError("gradient-enabled reads must be inside retained window")
        state, _ = self.embed(tokens, slots)
        anchor = state[..., self.anchor_channels]
        outputs = []
        for step in range(1, rounds + 1):
            # Burn-in never detaches the original translated input for later steps.
            if step == burn + 1 and burn:
                state = torch.cat((anchor, state[..., self.width:].detach()), -1)
            with torch.set_grad_enabled(track and step > burn):
                state = self.step(state)
                if step in reads:
                    outputs.append(self.read(state)[0].reshape(*tokens.shape, VOCAB))
        return torch.stack(outputs, 1)

    def counts(self, *, cells=1):
        stored = sum(p.numel() for p in self.parameters())
        per_expert = sum(p.numel() for p in self.experts[0].parameters())
        return {"stored_parameters": stored,
                "trainable_parameters": sum(p.numel() for p in self.parameters() if p.requires_grad),
                "frozen_source_parameters": self.source.weight.numel(),
                "source_reasoning_calls_per_embed": 0, "source_reasoning_calls_per_loop": 0,
                "source_output_head_calls": 0, "expert_count": self.expert_count,
                "active_experts_per_position": self.top_k,
                "experts_may_both_be_used_in_a_batch": True,
                "parameters_per_expert": per_expert,
                "selected_expert_parameters_per_position": self.top_k * per_expert,
                "expert_pair_evaluations_per_loop": cells * 5 * self.top_k,
                "shared_endpoint_and_router_run_at_every_position": True,
                "state_width": self.state_width, "state_scalars_per_item": cells * self.state_width,
                "dynamic_state_scalars_per_item": cells * (self.width + self.public_width),
                "raw_sum": self.raw_sum, "identical_experts_at_construction": self.identical_experts,
                "halt_kind": self.halt_kind, "parameter_counts_are_not_latency_or_flops": True}


def selftest():
    """CPU1 <1s mechanics, excluding interpreter/import; no tasks or fitting."""
    import ast
    import hashlib
    import inspect
    import time

    started = time.perf_counter()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.manual_seed(73979930)
    source = nn.Embedding(VOCAB, SOURCE_WIDTH)
    source_before = source.weight.detach().clone()
    model = SpatialRelation(source)
    tokens, slots = torch.randint(VOCAB, (3, 2, 3)), torch.randint(2, (3, 2, 3))
    tokens_before, slots_before = tokens.clone(), slots.clone()
    evidence, gradients, controls = {}, {}, {}
    tolerance = 3e-6

    def fingerprint(module):
        digest = hashlib.sha256()
        for name, tensor in module.state_dict().items():
            digest.update(name.encode())
            digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
        return digest.hexdigest()

    def parity(name, a, b):
        error = float((a - b).abs().max()) if a.numel() else 0.
        assert error <= tolerance, (name, error)
        evidence[name] = error

    before = fingerprint(model)
    # Constructor rejects booleans-as-integers and out-of-range expert choices.
    for kwargs in ({"expert_count": 1}, {"expert_count": 3}, {"expert_count": True},
                   {"top_k": 0}, {"top_k": 3}, {"top_k": True},
                   {"experts": 1}, {"active": 3}, {"active": True},
                   {"top_k": 1, "active": 2}, {"expert_count": 2, "experts": 3}):
        try:
            SpatialRelation(source, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(kwargs)

    with torch.no_grad():
        e, (dr, dc) = model.embed(tokens, slots)
        saved_e = e.clone()
        h = model.initial_state(e)
        parity("zero_start_parity", model.step(torch.zeros_like(e), e, dr, dc), model.step(h))
        h = model.step(model.step(h))
        old_h = h.clone()
        direct = model.step(h)
        assert torch.equal(h, old_h) and torch.equal(e, saved_e)
        permutation = torch.tensor([2, 0, 1])
        parity("batch_row_permutation", direct[permutation], model.step(h[permutation], e, dc, dr))
        parity("batch_row_removal_stale_embedding", direct[[2]], model.step(h[[2]], e, dr, dc))
        parity("single_item_vs_batch", direct[1:2], model.step(h[1:2]))
        other_e, offsets = model.embed(tokens.reshape(3, 3, 2), slots.reshape(3, 3, 2))
        model.step(other_e)
        parity("interleaved_same_N_geometry", direct, model.step(h, other_e, *offsets))
        parity("mixed_same_N_geometry_batch", torch.cat((direct[:1], model.step(other_e[:1]))),
               model.step(torch.cat((h[:1], other_e[:1]))))
        different_e, different_offsets = model.embed(tokens[:1, :1, :2], slots[:1, :1, :2])
        model.step(different_e)
        parity("interleaved_different_N_geometry", direct, model.step(h, different_e, *different_offsets))
        assert not torch.equal(e[..., model.neighbor_channels], other_e[..., model.neighbor_channels])
        manual, q = model.read(direct)
        parity("full_125_readout_parity", manual.reshape(3, 2, 3, VOCAB),
               model(tokens, slots, rounds=3)[:, -1])
        parity("immutable_translated_input", direct[..., model.anchor_channels], e[..., model.anchor_channels])
        assert torch.equal(model.answer_mask(direct), slots.reshape(3, 6).bool())
        assert torch.equal(model.rounds(direct), torch.full((3,), 3))
        assert torch.equal(q, q.new_full((3,), -20.))
        assert manual.shape == (3, 6, VOCAB) and bool(torch.isfinite(manual).all())
        empty = h[:0]
        assert model.step(empty).shape == empty.shape and model.read(empty)[0].shape == (0, 6, VOCAB)
        assert model.rounds(empty).shape == (0,) and model.answer_mask(empty).shape == (0, 6)
        assert float(direct[..., model.hidden_channels].abs().max()) <= 1.
        # Synthetic geometry probes: no token meanings, only stencil boundaries.
        for rows, cols in ((1, 1), (1, 3), (3, 1), (2, 3)):
            ge, _ = model.embed(torch.randint(VOCAB, (1, rows, cols)), torch.zeros(1, rows, cols))
            valid = ge[0, :, model.valid_channels]
            neighbor = ge[0, :, model.neighbor_channels].long()
            for cell in range(rows * cols):
                for edge, (drow, dcol) in enumerate(STENCIL):
                    nr, nc = cell // cols + drow, cell % cols + dcol
                    expected_valid = 0 <= nr < rows and 0 <= nc < cols
                    assert bool(valid[cell, edge]) == expected_valid
                    if expected_valid:
                        assert int(neighbor[cell, edge]) == nr * cols + nc
            assert bool(torch.isfinite(model.read(model.step(ge))[0]).all())
        pair = torch.randn(2, 5, 50)
        valid = torch.ones(2, 5)
        total, mean = model.experts[0].statistics(pair, valid)
        doubled, same_mean = model.experts[0].statistics(pair.repeat(1, 2, 1), valid.repeat(1, 2))
        parity("raw_sum_replication", doubled, 2 * total)
        parity("weighted_mean_replication", same_mean, mean)
        invalid_total, invalid_mean = model.experts[0].statistics(pair, torch.zeros_like(valid))
        assert bool((invalid_total == 0).all()) and bool((invalid_mean == 0).all())

    # Both full-gradient horizons, with hooks removed before returning.
    for top_k, horizon in ((1, 12), (2, 24)):
        arm = SpatialRelation(source, top_k=top_k)
        arm.load_state_dict(model.state_dict(), strict=True)
        hidden_states, proposals, pair_evaluations = [], [], [0, 0]
        def capture(destination):
            def hook(_module, _args, output):
                output.retain_grad()
                destination.append(output)
            return hook
        hooks = [arm.recurrent.register_forward_hook(capture(hidden_states)),
                 arm.public_proposal.register_forward_hook(capture(proposals))]
        for expert_id, expert in enumerate(arm.experts):
            def count(_module, args, _output, i=expert_id):
                pair_evaluations[i] += args[0].shape[0] * args[0].shape[1]
            hooks.append(expert.register_forward_hook(count))
        output = arm(tokens[:2], slots[:2], rounds=horizon)
        for hook in hooks:
            hook.remove()
        output[:, -1].square().mean().backward()
        assert len(hidden_states) == len(proposals) == horizon
        state_norms = [float(v.grad.abs().sum()) for v in (hidden_states[0], proposals[0])]
        assert all(math.isfinite(v) and v > 0 for v in state_norms)
        used_gradients = {}
        for name, parameter in arm.named_parameters():
            if not parameter.requires_grad:
                assert parameter.grad is None
                continue
            if name.startswith("experts.") and pair_evaluations[int(name.split(".")[1])] == 0:
                assert parameter.grad is None
                continue
            assert parameter.grad is not None, name
            norm = float(parameter.grad.abs().sum())
            assert bool(torch.isfinite(parameter.grad).all()) and norm > 0, (name, norm)
            used_gradients[name] = norm
        assert sum(pair_evaluations) == 2 * 6 * 5 * top_k * horizon
        assert fingerprint(arm) == before
        gradients[f"top{top_k}_full_{horizon}"] = {
            "used_parameter_gradient_l1": used_gradients,
            "final_read_to_first_hidden_and_public_proposal_l1": state_norms,
            "expert_pair_evaluations": pair_evaluations,
            "output_shape": list(output.shape)}

    with torch.no_grad():
        alias_arm = SpatialRelation(source, raw_sum=True, experts=2, active=2)
        alias_arm.load_state_dict(model.state_dict(), strict=True)
        assert alias_arm.expert_count == 2 and alias_arm.top_k == 2
        assert fingerprint(alias_arm) == before
        for top_k in (1, 2):
            for raw_sum in (True, False):
                arm = SpatialRelation(source, top_k=top_k, raw_sum=raw_sum)
                arm.load_state_dict(model.state_dict(), strict=True)
                assert fingerprint(arm) == before
                output = arm(tokens[:1], slots[:1], rounds=2)
                assert output.shape == (1, 2, 2, 3, VOCAB) and bool(torch.isfinite(output).all())
                controls[f"top{top_k}_{'sum' if raw_sum else 'mean'}"] = arm.counts(cells=6)
        cloned_experts = SpatialRelation(source, identical_experts=True)
        for a, b in zip(cloned_experts.experts[0].parameters(), cloned_experts.experts[1].parameters()):
            assert torch.equal(a, b) and a.data_ptr() != b.data_ptr()
        # Parent can freeze the entire model; state remains functional/readable.
        frozen = arm.eval().requires_grad_(False)
        frozen_before = fingerprint(frozen)
        fe, _ = frozen.embed(tokens[:1], slots[:1])
        fh = frozen.step(frozen.initial_state(fe))
        frozen.read(fh)
        assert fingerprint(frozen) == frozen_before
        assert not fh.requires_grad
        assert torch.equal(fe[..., frozen.anchor_channels], fh[..., frozen.anchor_channels])

    assert fingerprint(model) == before and torch.equal(source.weight, source_before)
    assert source.weight.grad is None and model.source.weight.data_ptr() != source.weight.data_ptr()
    assert not model.source.weight.requires_grad
    assert torch.equal(tokens, tokens_before) and torch.equal(slots, slots_before)
    assert list(dict(model.named_buffers())) == ["directions"]
    tree = ast.parse(inspect.getsource(inspect.getmodule(SpatialRelation)))
    imports = sorted({(node.module or "").split(".")[0] if isinstance(node, ast.ImportFrom)
                      else alias.name.split(".")[0]
                      for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                      for alias in (node.names if isinstance(node, ast.Import) else [None])})
    assert set(imports) <= {"__future__", "math", "torch", "ast", "hashlib", "inspect", "time",
                           "argparse", "json", "pathlib"}
    elapsed = time.perf_counter() - started
    assert elapsed < 1., elapsed
    return {"passed": True, "kind": "synthetic integer-token mechanics; no capability or latency claim",
            "seed": 73979930, "torch_version": torch.__version__, "device": "cpu",
            "cpu_threads": torch.get_num_threads(), "interop_threads": torch.get_num_interop_threads(),
            "mechanics_seconds_excluding_interpreter_and_import": elapsed,
            "subsecond_budget_excludes_import_and_report_serialization": True,
            "trained": False, "optimizer_steps": 0, "task_items_generated_or_evaluated": 0,
            "source_embedding_in_this_test": "random [125,256]; no checkpoint loaded",
            "qualified_source_provenance": "parent must supply and verify; not certified here",
            "numerical_tolerance": tolerance, "mechanics_max_errors": evidence,
            "full_horizon_gradient_checks": gradients, "controls": controls,
            "constructor_expert_count_and_k_rejections": True, "stencil_boundaries_checked": True,
            "invalid_boundary_messages_zero_after_biased_heads": True,
            "frozen_explicit_state_checked": True, "immutable_inputs_and_source": True,
            "identical_experts_option_copies_without_aliasing": True,
            "parameters_and_buffers_unchanged_by_forward_backward": True,
            "state_dict_sha256": before, "imports": imports,
            "only_buffer": "directions: fixed five-by-two geometric offsets",
            "default_counts": model.counts(cells=6)}


if __name__ == "__main__":
    import argparse
    import hashlib
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not args.selftest:
        parser.error("only --selftest is available; no task/training runner")
    report = selftest()
    report["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    design = Path(__file__).with_name("spatial-relation-design.md")
    if design.exists():
        report["design_sha256"] = hashlib.sha256(design.read_bytes()).hexdigest()
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(serialized)
    print(serialized)
