"""Final latent executor: frozen N-style programs, physical active-row removal.

No data, checker, notebook, training, or sleep imports. The output translator
gets FinalLatent ONLY. Audit data stays separate. See CONTRACT.md in the own
artifact folder. Runtime proof status never upgrades itself.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import math
from contextlib import contextmanager
from typing import Literal

import torch
from torch import Tensor, nn


PROOF_STATUS = "NOT SHOWN"


@dataclass(frozen=True)
class FinalLatent:
    latent: Tensor
    latent_mask: Tensor
    answer_mask: Tensor
    token_shape: tuple[int, int]

    def __post_init__(self):
        if self.latent.ndim != 3:
            raise ValueError("latent must be [B,N,D]")
        b, n, _ = self.latent.shape
        if (self.latent.ndim != 3 or not self.latent.is_floating_point()
                or self.latent.requires_grad or self.latent_mask.shape != self.latent.shape
                or self.latent_mask.dtype != torch.bool or self.answer_mask.shape != (b, n)
                or self.answer_mask.dtype != torch.bool or len(self.token_shape) != 2
                or any(type(x) is not int or x < 1 for x in self.token_shape)
                or math.prod(self.token_shape) != n
                or self.latent_mask.device != self.latent.device
                or self.answer_mask.device != self.latent.device
                or not bool(torch.isfinite(self.latent).all())
                or not bool((self.latent.masked_select(~self.latent_mask) == 0).all())):
            raise ValueError("invalid final latent payload")

    def to(self, device):
        return FinalLatent(self.latent.to(device), self.latent_mask.to(device),
                           self.answer_mask.to(device), self.token_shape)


@dataclass(frozen=True)
class ExecutionAudit:
    predictions: Tensor
    rounds: Tensor
    stopped: Tensor
    executed_batch_sizes: tuple[int, ...]
    selected_row_rounds: int
    executed_row_rounds: int
    work: dict
    policy: str
    compact: bool
    core_sha256: str
    proof_status: str = PROOF_STATUS


@dataclass(frozen=True)
class StopRun:
    final: FinalLatent
    audit: ExecutionAudit


def module_hash(module):
    """Canonical parameter/buffer hash, independent of torch.save object IDs."""
    digest = hashlib.sha256()
    for key, tensor in sorted(module.state_dict().items()):
        t = tensor.detach().cpu().contiguous()
        digest.update(f"{key}:{t.dtype}:{tuple(t.shape)}".encode())
        digest.update(t.reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


class WorkMeter:
    """Observe actual module invocations; no output or policy changes.

    Linear MACs cover executed nn.Linear only, exclude attention matmuls,
    functional linear, GRU kernels and all elementwise work. They are partial
    counts, never total FLOPs or latency. Phase includes hidden source prefixes.
    """
    def __init__(self, module):
        self.phase = "init"
        self.records = {}
        self.handles = []
        for name, child in module.named_modules():
            if isinstance(child, (nn.Linear, nn.Conv2d, nn.GRUCell, nn.Embedding, nn.LayerNorm)):
                self.handles.append(child.register_forward_pre_hook(self._hook(name)))
            # Observe block calls directly, including graph's source16 prefix.
            elif child.__class__.__name__ in ("Block", "DeltaExpert", "SpatialMessageExpert"):
                self.handles.append(child.register_forward_pre_hook(self._hook(name)))

    def _hook(self, name):
        def hook(module, inputs):
            if not inputs or not isinstance(inputs[0], Tensor):
                return
            x = inputs[0]
            key = f"{self.phase}:{name}"
            row = self.records.setdefault(key, {"calls": 0, "input_elements": 0,
                                                "leading_entries": 0, "linear_macs": 0})
            row["calls"] += 1
            row["input_elements"] += x.numel()
            row["leading_entries"] += x.shape[0] if x.ndim else 1
            if isinstance(module, nn.Linear):
                row["linear_macs"] += x.numel() * module.out_features
        return hook

    def close(self):
        for handle in self.handles:
            handle.remove()

    def report(self):
        phases = {}
        for key, row in self.records.items():
            phase = key.split(":", 1)[0]
            value = phases.setdefault(phase, {"linear_macs": 0, "observed_module_calls": 0})
            value["linear_macs"] += row["linear_macs"]
            value["observed_module_calls"] += row["calls"]
        return {"phases": phases, "modules": self.records,
                "linear_macs_are_partial_not_FLOPs": True,
                "attention_functional_ops_and_GRU_MACs_not_counted": True,
                "latency_claim": False}


def output_features(logits, mask, round_number, cap=48):
    """Eight live-output statistics; no targets, checker or task labels."""
    lg = logits.float()
    if lg.ndim != 3 or mask.shape != lg.shape[:2] or not bool(mask.any(1).all()):
        raise ValueError("nonempty answer slots and [B,N,V] required")
    den = mask.sum(1)
    p = lg.softmax(-1)
    entropy = -(p * p.clamp_min(1e-12).log()).sum(-1)
    best = lg.topk(2, -1).values
    margin = best[..., 0] - best[..., 1]
    confidence = p.max(-1).values
    r = den.new_full(den.shape, round_number, dtype=torch.float32)
    return torch.stack(((entropy * mask).sum(1) / den,
                        entropy.masked_fill(~mask, -math.inf).max(1).values,
                        (margin * mask).sum(1) / den,
                        margin.masked_fill(~mask, math.inf).min(1).values,
                        (confidence * mask).sum(1) / den,
                        confidence.masked_fill(~mask, math.inf).min(1).values,
                        r / cap, r.log1p()), -1)


class OutputStopController(nn.Module):
    def __init__(self):
        super().__init__()
        self.register_buffer("mean", torch.zeros(8))
        self.register_buffer("scale", torch.ones(8))
        self.mlp = nn.Sequential(nn.Linear(8, 32), nn.GELU(), nn.Linear(32, 1))

    def forward(self, features):
        return self.mlp((features - self.mean) / self.scale).squeeze(-1)


class LatentStopController(nn.Module):
    """Spatial worker stop_model(query_state[B,N,256])->halt logits[B].

    No logits, raw text, targets, task labels or notebook bypass at inference.
    TRAIN-only fitting owns correctness labels and standardization.
    """
    def __init__(self, width=256, hidden=32):
        super().__init__()
        self.register_buffer("mean", torch.zeros(width))
        self.register_buffer("scale", torch.ones(width))
        self.mlp = nn.Sequential(nn.Linear(width, hidden), nn.GELU(), nn.Linear(hidden, 1))

    def features(self, query_state):
        return query_state.float().mean(1)

    def forward(self, query_state):
        pooled = self.features(query_state)
        return self.mlp((pooled-self.mean)/self.scale).squeeze(-1)


@dataclass(frozen=True)
class LatentLayout:
    """Explicit allowlist of mutable channel ranges, not an automatic fallback."""
    start: int
    stop: int


def known_layout(program):
    name = program.__class__.__name__
    if name == "GraphProgram":
        return LatentLayout(0, 64)
    if name in ("NumericProgram", "SpatialRelation"):
        return LatentLayout(program.dynamic_channels.start, program.dynamic_channels.stop)
    if name in ("GraphDenseProgram", "DenseNumericProgram", "DenseSpatialProgram", "MazeStopProgram"):
        return LatentLayout(0, 256)
    if name in ("Net", "SleepMoE", "AttentionReasoner"):
        return LatentLayout(0, program.tok.embedding_dim)
    if name == "ProgramLibrary":
        return tuple(known_layout(p) for p in program.capsules)
    raise TypeError(f"unknown latent layout for {name}; supply audited LatentLayout explicitly")


def _layout_width(layout):
    if isinstance(layout, tuple):
        return max(_layout_width(x) for x in layout)
    if not isinstance(layout, LatentLayout) or not 0 <= layout.start < layout.stop:
        raise ValueError("invalid latent layout")
    return layout.stop - layout.start


def _extract(program, state, layout, width):
    b, n, _ = state.shape
    latent = state.new_zeros(b, n, width)
    valid = torch.zeros_like(latent, dtype=torch.bool)
    if isinstance(layout, tuple):
        if program.__class__.__name__ != "ProgramLibrary" or len(layout) != len(program.capsules):
            raise ValueError("library layout mismatch")
        routes = program._routes(state)
        for i, child in enumerate(program.capsules):
            ids = (routes == i).nonzero(as_tuple=True)[0]
            if len(ids):
                value, mask = _extract(child, state[ids, :, :program.program_widths[i]], layout[i], width)
                latent[ids], valid[ids] = value, mask
    else:
        if layout.stop > state.shape[-1]:
            raise ValueError("latent range exceeds physical state width")
        d = layout.stop - layout.start
        latent[..., :d] = state[..., layout.start:layout.stop]
        valid[..., :d] = True
        # Graph pack zeros unused cells; mask them too, with no lexical handles
        # or source logits passed through. Atom count only marks storage validity.
        if program.__class__.__name__ == "GraphProgram":
            grid = program._grid(state)
            rows, ports = grid.shape[1:3]
            cells = torch.arange(n, device=state.device)
            record = cells % ports == 0
            atom = (cells % ports == 1)[None] & (cells // ports)[None].lt(
                program.private_state(state).atom_count[:, None])
            valid[..., :d] &= (record[None] | atom)[..., None]
            latent *= valid
    return latent.detach().clone(), valid


class FinalStateAdapter(nn.Module):
    """Freeze an existing reasoner; keep only completed, mutable final state.

    A decoder should have forward(final: FinalLatent), never forward(StopRun).
    Explicit layout overrides are for new audited programs; do not select
    immutable feature/logit/metadata channels. Existing inherited halt heads
    may be uncalibrated: mechanics success cannot establish quality readiness.
    """
    def __init__(self, program, controller=None, *, latent_width=256, layout=None, translation_seed=0,
                 controller_input="output_features"):
        super().__init__()
        if not all(callable(getattr(program, n, None)) for n in ("embed", "read")):
            raise TypeError("embed/read loop program required")
        self.program = program.eval().requires_grad_(False)
        self.controller = None if controller is None else controller.eval().requires_grad_(False)
        self.layout = known_layout(program) if layout is None else layout
        if type(latent_width) is not int or latent_width < _layout_width(self.layout):
            raise ValueError("latent width cannot truncate mutable state")
        self.latent_width = latent_width
        if type(translation_seed) is not int or translation_seed < 0:
            raise ValueError("translation_seed must be a nonnegative integer")
        self.translation_seed = translation_seed
        if controller_input not in ("output_features", "latent"):
            raise ValueError("controller_input must be output_features or latent")
        self.controller_input = controller_input

    def train(self, mode=True):
        super().train(False)
        return self

    @staticmethod
    def _check_inputs(tokens, slots, cap, threshold):
        if (tokens.ndim != 3 or min(tokens.shape) < 1 or tokens.dtype != torch.long
                or slots.shape != tokens.shape or slots.device != tokens.device
                or bool(((slots != 0) & (slots != 1)).any())
                or not bool(slots.flatten(1).bool().any(1).all())
                or type(cap) is not int or cap < 1 or not math.isfinite(threshold)
                or not 0 <= threshold <= 1):
            raise ValueError("nonempty int64 tokens/binary answer slots, positive cap, threshold[0,1] required")

    def _step(self, h, e, dr, dc, token_shape):
        # SleepMoE's geometry is per-call, not per-row data. Restore at every
        # step so a previously interleaved embed cannot corrupt execution.
        if hasattr(self.program, "geometry"):
            self.program.geometry = token_shape
        return self.program.step(h, e, dr, dc)

    @torch.no_grad()
    def execute(self, tokens, slots, *, policy: Literal["learned", "guarded", "original_guarded", "fixed"] = "learned",
                compact=True, cap=48, threshold=.5):
        self._check_inputs(tokens, slots, cap, threshold)
        if policy not in ("learned", "guarded", "original_guarded", "fixed") or type(compact) is not bool:
            raise ValueError("unknown policy or compaction flag")
        core_before = module_hash(self.program)
        self.eval()
        meter = WorkMeter(self)
        try:
            result = self._execute(tokens, slots, policy, compact, cap, threshold, meter, core_before)
        finally:
            meter.close()
        if module_hash(self.program) != core_before:
            raise RuntimeError("reasoning parameters/buffers changed during inference")
        return result

    def _execute(self, tokens, slots, policy, compact, cap, threshold, meter, core_before):
        b = len(tokens)
        shape = tuple(tokens.shape[1:])
        mask = slots.flatten(1).bool()
        meter.phase = "embed_prefix"
        # Existing GraphProgram permutes anonymous handles using the CPU RNG.
        # Replay the same translated initialization for mechanics/reference;
        # restore caller RNG so inference does not perturb future training.
        with torch.random.fork_rng(devices=[]):
            torch.random.default_generator.manual_seed(self.translation_seed)
            e, (dr, dc) = self.program.embed(tokens, slots)
        return self._execute_prepared(e, dr, dc, mask, shape, policy, compact, cap, threshold,
                                      meter, core_before)

    def _execute_prepared(self, e, dr, dc, mask, shape, policy, compact, cap, threshold, meter, core_before):
        b, query_n = mask.shape
        h = torch.zeros_like(e)
        live = torch.arange(b, device=e.device)
        finished = torch.zeros(b, dtype=torch.bool, device=e.device)
        latent = e.new_zeros(b, query_n, self.latent_width)
        latent_mask = torch.zeros_like(latent, dtype=torch.bool)
        predictions = torch.empty(b, query_n, dtype=torch.long, device=e.device)
        rounds = torch.empty(b, dtype=torch.long, device=e.device)
        stopped = torch.zeros(b, dtype=torch.bool, device=e.device)
        original_mask = mask.clone()
        previous = previous2 = None
        sizes = []
        plain = getattr(self.program, "arm", None) == "plain"
        for r in range(1, (1 if plain else cap) + 1):
            meter.phase = "transition"
            if plain:
                h = e
                for block in self.program.blocks:
                    h = block(h, dr, dc)
            else:
                h = self._step(h, e, dr, dc, shape)
            sizes.append(len(h))  # physical, including stopped rows in reference
            meter.phase = "read"
            query_h = h[:, :query_n]
            logits, q = self.program.read(query_h)
            if logits.shape[:2] != query_h.shape[:2] or logits.shape[-1] != 125:
                raise ValueError("full125 logits and aligned batch required")
            if not bool(torch.isfinite(logits).all()):
                raise ValueError("nonfinite reasoner readout")
            pred = logits.argmax(-1)
            fire = torch.zeros(len(h), dtype=torch.bool, device=h.device)
            if not plain and policy != "fixed":
                if self.controller is not None and policy != "original_guarded":
                    meter.phase = "controller"
                    # Controller representation is normalized to its TRAIN48
                    # horizon even when a PoC caller shortens the safety cap.
                    q = (self.controller(query_h) if self.controller_input == "latent" else
                         self.controller(output_features(logits, mask, r)))
                if q is None or q.shape != (len(h),) or not bool(torch.isfinite(q).all()):
                    raise ValueError("finite halt logits [active B] required")
                fire = q.float().sigmoid() > threshold
                if policy in ("guarded", "original_guarded"):
                    stable_mask = mask if policy == "guarded" else torch.ones_like(mask)
                    fire = (fire & ~(((pred != previous) | (previous != previous2)) & stable_mask).any(1)
                            if previous2 is not None else torch.zeros_like(fire))
            done = (fire | (r == cap) | plain)
            if not compact:
                done &= ~finished
            if bool(done.any()):
                ids = live[done]
                value, valid = _extract(self.program, query_h[done], self.layout, self.latent_width)
                latent[ids], latent_mask[ids] = value, valid
                predictions[ids], rounds[ids], stopped[ids] = pred[done], r, fire[done]
            if compact:
                keep = (~done).nonzero(as_tuple=True)[0]
                if not len(keep):
                    break
                previous2 = previous[keep] if previous is not None else None
                previous = pred[keep]
                h, e, mask, live = h[keep], e[keep], mask[keep], live[keep]
            else:
                finished |= done
                previous2, previous = previous, pred
        physical = sum(sizes)
        selected = int(rounds.sum())
        if compact and physical != selected:
            raise RuntimeError("compacted execution did not charge all physical row rounds")
        final = FinalLatent(latent.detach(), latent_mask, original_mask, shape)
        audit = ExecutionAudit(predictions, rounds, stopped, tuple(sizes), selected, physical,
                               meter.report(), policy, compact, core_before)
        return StopRun(final, audit)

    @torch.no_grad()
    def execute_embeddings(self, embeddings, answer_mask, token_shape, *, notebook_latents=None,
                           policy="learned", compact=True, cap=48, threshold=.5):
        """Immutable float reader entrypoint for N/SleepMoE/AttentionReasoner.

        embeddings[B,N,D] are translated input including any input-side slot
        representation. Notebook[B,M,D] enters attention internally. Export
        includes final QUERY hidden only, never notebook/input embeddings.
        """
        name = self.program.__class__.__name__
        if name not in ("Net", "SleepMoE", "AttentionReasoner"):
            raise TypeError("float entrypoint requires an audited transformer latent layout")
        if (embeddings.ndim != 3 or min(embeddings.shape) < 1 or not embeddings.is_floating_point()
                or embeddings.shape[-1] != self.program.tok.embedding_dim
                or embeddings.dtype != self.program.tok.weight.dtype
                or embeddings.device != self.program.tok.weight.device
                or answer_mask.dtype != torch.bool or answer_mask.shape != embeddings.shape[:2]
                or answer_mask.device != embeddings.device or not bool(answer_mask.any(1).all())
                or len(token_shape) != 2 or any(type(x) is not int or x < 1 for x in token_shape)
                or math.prod(token_shape) != embeddings.shape[1]
                or not bool(torch.isfinite(embeddings).all())
                or type(cap) is not int or cap < 1 or not math.isfinite(threshold)
                or not 0 <= threshold <= 1 or policy not in ("learned", "guarded", "original_guarded", "fixed")
                or type(compact) is not bool):
            raise ValueError("invalid immutable float input/shape/mask/stop policy")
        if notebook_latents is not None:
            memo = notebook_latents
            if (memo.ndim != 3 or memo.shape[0] != len(embeddings) or memo.shape[-1] != embeddings.shape[-1]
                    or memo.device != embeddings.device or memo.dtype != embeddings.dtype
                    or not bool(torch.isfinite(memo).all())):
                raise ValueError("notebook must be finite [B,M,D] with same device/dtype")
            if name == "SleepMoE" and memo.shape[1]:
                raise ValueError("SleepMoE local residual geometry cannot append notebook positions; use attention core")
        before = module_hash(self.program)
        self.eval()
        meter = WorkMeter(self)
        try:
            meter.phase = "embed_prefix"
            e = embeddings.detach().clone()
            dr, dc = self.program.offsets(*token_shape, e.device)
            if notebook_latents is not None and notebook_latents.shape[1]:
                n = e.shape[1]
                e = torch.cat((e, notebook_latents.detach().clone()), 1)
                total = e.shape[1]
                extended_dr = torch.full((total, total), 4, dtype=torch.long, device=e.device)
                extended_dc = extended_dr.clone()
                extended_dr[:n, :n], extended_dc[:n, :n] = dr, dc
                dr, dc = extended_dr, extended_dc
            result = self._execute_prepared(e, dr, dc, answer_mask.clone(), tuple(token_shape),
                                            policy, compact, cap, threshold, meter, before)
        finally:
            meter.close()
        if module_hash(self.program) != before:
            raise AssertionError("reasoning weights changed during float execution")
        return result


def assert_parity(a: StopRun, b: StopRun):
    for name in ("latent", "latent_mask", "answer_mask"):
        if not torch.equal(getattr(a.final, name), getattr(b.final, name)):
            raise AssertionError("final " + name + " differs")
    if a.final.token_shape != b.final.token_shape:
        raise AssertionError("final geometry differs")
    for name in ("predictions", "rounds", "stopped"):
        if not torch.equal(getattr(a.audit, name), getattr(b.audit, name)):
            raise AssertionError("audit " + name + " differs")


@torch.no_grad()
def check_stop_readiness(adapter, tokens, slots, *, cap=6, threshold=.5, policy="learned"):
    """Bounded PoC mechanics check; does not train or judge sleep/quality.

    Two identical repeats measure execution noise. Must be called for BOTH
    source seeds under a sealed smoke plan. Caller owns idle scheduling.
    """
    if len(tokens) > 4 or tokens.numel() > 64 or cap > 8:
        raise ValueError("readiness smoke exceeds bounded budget")
    before = module_hash(adapter)
    active = adapter.execute(tokens, slots, cap=cap, threshold=threshold, policy=policy)
    repeat = adapter.execute(tokens, slots, cap=cap, threshold=threshold, policy=policy)
    reference = adapter.execute(tokens, slots, compact=False, cap=cap,
                                threshold=threshold, policy=policy)
    assert_parity(active, repeat)
    assert_parity(active, reference)
    if module_hash(adapter) != before:
        raise AssertionError("adapter changed")
    return {"mechanics_passed": True, "stage_proof_status": PROOF_STATUS,
            "quality_ready": False, "sleep_ready": False,
            "raw_selected_rounds": active.audit.rounds.tolist(),
            "raw_stop_flags": active.audit.stopped.tolist(),
            "compact_physical_row_rounds": active.audit.executed_row_rounds,
            "reference_physical_row_rounds": reference.audit.executed_row_rounds,
            "raw_compact_batch_sizes": active.audit.executed_batch_sizes,
            "repeat_exact_noise": 0, "frozen_adapter_sha256": before,
            "work": active.audit.work,
            "limits": "no semantic scoring; no calibration, notebook, sleep or latency proof"}


class ComposerFinalStateAdapter(nn.Module):
    """Consume Composer Context/State.select API without exposing private ports.

    `infer(inputs, ...)` returns StopRun, not Composer.infer's logits dict.
    Final geometry is (record_count,1); slots.any(-1) is answer_mask. The four
    input fields/immutable context/private program tensors never reach decoder.
    `composer` policy reproduces Composer.infer's min2 and >= threshold rule;
    `learned` uses min1 and > threshold. Plain always runs its declared cap.
    """
    def __init__(self, composer, *, latent_width=256):
        super().__init__()
        if not all(callable(getattr(composer, n, None)) for n in ("encode", "initial_state", "step", "read")):
            raise TypeError("Composer Context/State interface required")
        self.program = composer.eval().requires_grad_(False)
        if type(latent_width) is not int or latent_width < 64:
            raise ValueError("composer board requires >=64 latent channels")
        self.latent_width = latent_width

    def train(self, mode=True):
        super().train(False)
        return self

    @torch.no_grad()
    def execute(self, inputs, *, policy="learned", compact=True, cap=6, threshold=.5, min_rounds=2):
        if (policy not in ("learned", "composer", "fixed") or type(compact) is not bool
                or type(cap) is not int or not 1 <= cap <= 6
                or type(min_rounds) is not int or not 1 <= min_rounds <= 6
                or (policy == "composer" and min_rounds > cap)
                or not math.isfinite(threshold) or not 0 <= threshold <= 1):
            raise ValueError("invalid bounded composer stopping policy")
        tokens, slots = inputs.tokens, inputs.slots
        mask = slots.any(-1)
        if not bool(mask.any(1).all()):
            raise ValueError("at least one output record per row required")
        before = module_hash(self.program)
        self.eval()
        meter = WorkMeter(self)
        try:
            meter.phase = "embed_prefix"
            ctx = self.program.encode(inputs)
            state = self.program.initial_state(ctx)
            b, records, width = state.board.shape
            if width != 64:
                raise ValueError("composer contract requires a 64-wide board")
            latent = state.board.new_zeros(b, records, self.latent_width)
            valid = torch.zeros_like(latent, dtype=torch.bool)
            predictions = torch.empty(b, records, dtype=torch.long, device=tokens.device)
            rounds = torch.empty(b, dtype=torch.long, device=tokens.device)
            stopped = torch.zeros(b, dtype=torch.bool, device=tokens.device)
            live = torch.arange(b, device=tokens.device)
            finished = torch.zeros(b, dtype=torch.bool, device=tokens.device)
            sizes = []
            for r in range(1, cap + 1):
                meter.phase = "transition"
                state = self.program.step(ctx, state)
                sizes.append(len(state.board))
                meter.phase = "read"
                lg, q = self.program.read(state)
                if (lg.shape != (len(live), records, 125) or q.shape != (len(live),)
                        or not bool(torch.isfinite(lg).all()) or not bool(torch.isfinite(q).all())):
                    raise ValueError("invalid composer readout")
                fire = (q.sigmoid() >= threshold) & (r >= min_rounds) if policy == "composer" else q.sigmoid() > threshold
                if policy == "fixed" or self.program.arm == "plain":
                    fire = torch.zeros_like(fire)
                done = fire | (r == cap)
                if not compact:
                    done &= ~finished
                ids = live[done]
                latent[ids, :, :64] = state.board[done]
                valid[ids, :, :64] = True
                predictions[ids], rounds[ids], stopped[ids] = lg[done].argmax(-1), r, fire[done]
                if compact:
                    keep = (~done).nonzero(as_tuple=True)[0]
                    if not len(keep):
                        break
                    live, ctx, state = live[keep], ctx.select(keep), state.select(keep)
                else:
                    finished |= done
            if compact and sum(sizes) != int(rounds.sum()):
                raise AssertionError("composer physical work differs from selected work")
            result = StopRun(FinalLatent(latent.detach(), valid, mask.clone(), (records, 1)),
                             ExecutionAudit(predictions, rounds, stopped, tuple(sizes), int(rounds.sum()),
                                            sum(sizes), meter.report(), policy, compact, before))
        finally:
            meter.close()
        if module_hash(self.program) != before:
            raise AssertionError("composer weights/buffers changed")
        return result

    def infer(self, inputs, **kwargs):
        return self.execute(inputs, **kwargs)


@torch.no_grad()
def check_composer_stop_readiness(adapter, inputs, *, cap=6, threshold=.5, policy="composer"):
    if len(inputs.tokens) > 4 or inputs.tokens.numel() > 64 or cap > 6:
        raise ValueError("composer readiness smoke exceeds bounded budget")
    before = module_hash(adapter)
    active = adapter.infer(inputs, cap=cap, threshold=threshold, policy=policy)
    repeat = adapter.infer(inputs, cap=cap, threshold=threshold, policy=policy)
    reference = adapter.infer(inputs, compact=False, cap=cap, threshold=threshold, policy=policy)
    assert_parity(active, repeat); assert_parity(active, reference)
    if module_hash(adapter) != before:
        raise AssertionError("composer changed during readiness check")
    return {"mechanics_passed": True, "stage_proof_status": PROOF_STATUS,
            "sleep_ready": False, "quality_ready": False,
            "raw_selected_rounds": active.audit.rounds.tolist(),
            "raw_stop_flags": active.audit.stopped.tolist(), "repeat_exact_noise": 0,
            "compact_physical_row_rounds": active.audit.executed_row_rounds,
            "reference_physical_row_rounds": reference.audit.executed_row_rounds,
            "frozen_adapter_sha256": before, "work": active.audit.work}
