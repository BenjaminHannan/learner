"""Modality adapter: numpy reference for the AUDIO side of the shared
Workspace contract. It does not define its own contract.

Source of the contract (read 2026-10-03 from open PRs, may still move):
  - PR #23 (origin/claude/project-thread-knhc46, commit bb4d2efe4)
    critical-thinking-reasoner-design.md §6: each vector carries a
    (role, modality) pair of int ids, coords [B,N,<=3] (row, column, time),
    valid [B,N] bool; the CORE adds Embedding(role) + Embedding(modality),
    both zero-init. Audio adds one modality id and no new roles.
  - PR #22 (origin/claude/project-thread-qjn27k, commit 912bfe7de)
    design/next-parts/vision/workspace.py: Workspace(tokens [B,N,256] float,
    segment [B,N,2] long = (role id, modality id) from the role and modality id tables,
    valid [B,N] bool, coords [B,N,3] float (row, col, time) or None).

Output of ``adapt()`` is exactly those four fields, for one clip (N = ceil(T_in / k)):

    tokens   float32 [N, 256]  projected slot vectors; rows with valid False are exactly 0.
                               NO modality/role tag is added here: the core adds it.
    segment  int64   [N, 2]    (role id, modality id) from ROLE_IDS / MODALITY_IDS, built only by
                               ``audio_segment()`` so the encoding can switch in one place.
    coords   float32 [N, 3]    (row, col, time) = (0, 0, slot centre in SECONDS).
                               time = time_offset + (j + 0.5) * k * frame_period.
                               Workspace v1 wants time relative to now (<= 0): set
                               time_offset = -(clip seconds), or use stream.AudioWindow.
    coord_valid bool [N, 3]    per-axis "has this coordinate" (Workspace v1, PR #23
                               commit c208de425): audio = (False, False, valid), so row
                               and col are absent and do not collide with image patch (0, 0).
                               Padded rows are 0 and must be ignored via ``valid``.
    valid    bool    [N]       True = real content, False = right padding.

``batch()`` stacks clips to [B, N_max, ...]. SUGGESTED (not settled in the
PRs): time in seconds rather than frame index, so encoders with different
frame rates agree; row and col fixed at 0 so audio order lives only in the
time coordinate. The current core takes no segment, coords or mask: see
``to_core_layout``.

It is a THIN TRANSLATOR: downsample, project, mask. No attention, no
recurrence, no task logic. The reasoner does the thinking.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

# Workspace contract v1 id tables, from PR #23 section 6 (commit 80540de9e, matching
# vision's workspace.py on PR #26). Role and modality are separate tables; the pair is
# (role id, modality id). Example order is not a role: within "example", row = example index.
ROLE_IDS = {"question": 0, "notebook": 1, "example": 2, "tool_result": 3, "register": 4, "action": 5}
MODALITY_IDS = {"text": 0, "image": 1, "audio": 2}
ROLES = ("question", "notebook", "example", "tool_result")   # roles an input adapter may emit
MODALITIES = ("text", "image", "audio")
FIELDS = ("tokens", "segment", "coords", "coord_valid", "valid")
POOL_MODES = ("stack", "mean")


def audio_segment(role: str, n: int, modality: str = "audio") -> np.ndarray:
    """The ONLY place the segment encoding is built: [n, 2] int64 (role id, modality id).

    If PR #23 switches to a single combined id, change this function (and the
    shape check in ``check_output``) and nothing else.
    """
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    if modality not in MODALITIES:
        raise ValueError(f"modality must be one of {MODALITIES}")
    return np.tile(np.array([ROLE_IDS[role], MODALITY_IDS[modality]], np.int64), (n, 1))


def audio_coord_valid(valid: np.ndarray, has_row: bool = False) -> np.ndarray:
    """[N, 3] bool per-axis flags. Audio has no column; row only for the example role
    (row = example index); time only where valid."""
    v = np.asarray(valid, bool)
    row = v if has_row else np.zeros_like(v)
    return np.stack([row, np.zeros_like(v), v], axis=-1)


@dataclass(frozen=True)
class ModalityAdapterSpec:
    modality: str                 # one of MODALITIES, e.g. "audio"
    d_in: int                     # encoder frame width (e.g. 512 for Whisper-base encoder)
    frame_period: float           # encoder frame spacing in seconds (0.02 for Whisper)
    downsample: int = 4           # frames per output slot
    pool: str = "stack"           # "stack" concatenates k frames; "mean" averages valid frames
    hidden: int | None = 256      # None = single linear layer; int = Linear-GELU-Linear
    d_model: int = 256            # shared contract width
    min_period: float = 0.08      # shortest sinusoid period, seconds
    max_period: float = 2000.0    # longest sinusoid period, seconds
    pos_scale: float = 0.0        # sinusoid of time added into tokens; 0 = off. Order normally
                                  # travels in coords; turn on only where the reasoner ignores
                                  # coords (e.g. today's notebook). Design doc E5.
    layernorm: bool = True        # per-frame LayerNorm (no affine) before projection
    time_offset: float = 0.0      # seconds at the start of input frame 0

    def __post_init__(self):
        if self.modality not in MODALITIES:
            raise ValueError(f"modality {self.modality!r} not in {MODALITIES}")
        if self.pool not in POOL_MODES:
            raise ValueError(f"pool must be one of {POOL_MODES}")
        for name in ("d_in", "downsample", "d_model"):
            v = getattr(self, name)
            if not isinstance(v, int) or v < 1:
                raise ValueError(f"{name} must be a positive int")
        if self.hidden is not None and (not isinstance(self.hidden, int) or self.hidden < 1):
            raise ValueError("hidden must be None or a positive int")
        if self.d_model % 2:
            raise ValueError("d_model must be even (sin/cos pairs)")
        if not (self.frame_period > 0 and 0 < self.min_period < self.max_period):
            raise ValueError("need frame_period > 0 and 0 < min_period < max_period")

    @property
    def d_proj_in(self) -> int:
        return self.d_in * self.downsample if self.pool == "stack" else self.d_in

    @property
    def slot_seconds(self) -> float:
        return self.frame_period * self.downsample

    def out_len(self, t_in: int) -> int:
        if t_in < 1:
            raise ValueError("need at least one input frame")
        return math.ceil(t_in / self.downsample)

    def weight_shapes(self) -> dict:
        if self.hidden is None:
            return {"w1": (self.d_proj_in, self.d_model), "b1": (self.d_model,)}
        return {"w1": (self.d_proj_in, self.hidden), "b1": (self.hidden,),
                "w2": (self.hidden, self.d_model), "b2": (self.d_model,)}

    def parameter_count(self) -> int:
        return int(sum(np.prod(s) for s in self.weight_shapes().values()))


def init_weights(spec: ModalityAdapterSpec, seed: int = 0, scale: float = 1.0) -> dict:
    """Deterministic random weights (biases zero). For tests and shape checks only."""
    rng = np.random.default_rng(seed)
    out = {}
    for name, shape in spec.weight_shapes().items():
        if name.startswith("b"):
            out[name] = np.zeros(shape, np.float32)
        else:
            out[name] = (rng.standard_normal(shape) * (scale / math.sqrt(shape[0]))).astype(np.float32)
    return out


def sinusoid(coord: np.ndarray, dim: int, min_period: float, max_period: float) -> np.ndarray:
    """[N, dim] sin/cos features of a continuous coordinate (seconds).

    Periods are geometric from min_period to max_period, so the code depends on
    elapsed seconds, not on slot index.
    """
    coord = np.asarray(coord, dtype=np.float64)
    half = dim // 2
    periods = min_period * (max_period / min_period) ** (np.arange(half) / max(half - 1, 1))
    ang = 2.0 * np.pi * coord[:, None] / periods[None, :]
    return np.concatenate([np.sin(ang), np.cos(ang)], axis=1)


def _gelu(x):
    return 0.5 * x * (1.0 + np.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x ** 3)))


def _check_weights(spec, weights):
    shapes = spec.weight_shapes()
    if set(weights) != set(shapes):
        raise ValueError(f"weights keys {sorted(weights)} != expected {sorted(shapes)}")
    for k, s in shapes.items():
        w = weights[k]
        if not isinstance(w, np.ndarray) or w.dtype != np.float32:
            raise TypeError(f"weight {k} must be a float32 ndarray")
        if w.shape != s:
            raise ValueError(f"weight {k} has shape {w.shape}, expected {s}")


def downsample(frames: np.ndarray, valid: np.ndarray, k: int, pool: str):
    """Group k consecutive frames into one slot. Returns (pooled, slot_valid).

    Padded frames are zeroed before pooling. A slot is valid if any of its
    frames is valid. "mean" averages valid frames only.
    """
    t, d = frames.shape
    t_out = math.ceil(t / k)
    pad = t_out * k - t
    f = np.pad(np.where(valid[:, None], frames, 0.0), ((0, pad), (0, 0)))
    m = np.pad(valid, (0, pad))
    g, gm = f.reshape(t_out, k, d), m.reshape(t_out, k)
    slot_valid = gm.any(axis=1)
    if pool == "stack":
        return g.reshape(t_out, k * d), slot_valid
    return g.sum(axis=1) / np.maximum(gm.sum(axis=1), 1)[:, None], slot_valid


def slot_times(spec: ModalityAdapterSpec, n: int) -> np.ndarray:
    """Slot centres in seconds; frame i spans [i, i+1) * frame_period."""
    return spec.time_offset + (np.arange(n) + 0.5) * spec.slot_seconds


def adapt(spec: ModalityAdapterSpec, weights: dict, frames: np.ndarray,
          valid: np.ndarray | None = None, role: str = "question",
          example_index: int | None = None) -> dict:
    """Encoder frames [T_in, d_in] -> one clip's Workspace fields (module docstring).

    role "example" needs ``example_index`` (it goes in the row coordinate, as
    contract v1 says); other roles must leave it None.
    """
    if (role == "example") != (example_index is not None):
        raise ValueError("example_index is required for role 'example' and only for it")
    if example_index is not None and (not isinstance(example_index, int) or example_index < 0):
        raise ValueError("example_index must be a non-negative int")
    frames = np.asarray(frames)
    if frames.ndim != 2 or frames.shape[1] != spec.d_in:
        raise ValueError(f"frames must be [T, {spec.d_in}], got {frames.shape}")
    if not np.issubdtype(frames.dtype, np.floating):
        raise TypeError("frames must be floating point")
    if not np.all(np.isfinite(frames)):
        raise ValueError("frames contain NaN or inf")
    t_in = frames.shape[0]
    valid = np.ones(t_in, dtype=bool) if valid is None else np.asarray(valid)
    if valid.dtype != bool or valid.shape != (t_in,):
        raise ValueError(f"valid must be bool [{t_in}]")
    if not valid.any():
        raise ValueError("valid has no True frames")
    if not valid[:valid.nonzero()[0][-1] + 1].all():
        raise ValueError("valid must be a contiguous prefix (right padding only)")
    _check_weights(spec, weights)
    segment = audio_segment(role, spec.out_len(t_in), spec.modality)

    x = frames.astype(np.float64)
    if spec.layernorm:
        x = (x - x.mean(axis=1, keepdims=True)) / np.sqrt(x.var(axis=1, keepdims=True) + 1e-5)
    pooled, slot_valid = downsample(x, valid, spec.downsample, spec.pool)
    h = pooled @ weights["w1"].astype(np.float64) + weights["b1"]
    if spec.hidden is not None:
        h = _gelu(h) @ weights["w2"].astype(np.float64) + weights["b2"]

    n = len(slot_valid)
    t = slot_times(spec, n)
    h = h + spec.pos_scale * sinusoid(t, spec.d_model, spec.min_period, spec.max_period)
    tokens = np.where(slot_valid[:, None], h, 0.0).astype(np.float32)
    coords = np.zeros((n, 3), np.float32)
    coords[:, 2] = np.where(slot_valid, t, 0.0)
    if example_index is not None:
        coords[:, 0] = np.where(slot_valid, example_index, 0)
    coord_valid = audio_coord_valid(slot_valid, has_row=example_index is not None)

    out = {"tokens": tokens, "segment": segment, "coords": coords, "coord_valid": coord_valid,
           "valid": slot_valid}
    check_output(spec, out, t_in)
    return out


def check_output(spec: ModalityAdapterSpec, out: dict, t_in: int) -> None:
    """Raise if ``out`` breaks the documented contract."""
    n = spec.out_len(t_in)
    if tuple(out) != FIELDS:
        raise AssertionError(f"fields {tuple(out)} != {FIELDS}")
    s, g, c, cv, v = (out[k] for k in FIELDS)
    is_example = bool(len(g)) and g.ndim == 2 and g[0, 0] == ROLE_IDS["example"]
    if cv.dtype != bool or cv.shape != (n, 3) or not np.array_equal(cv, audio_coord_valid(v, is_example)):
        raise AssertionError("coord_valid must be bool [N, 3] = (row only for example, False, valid)")
    if s.dtype != np.float32 or s.shape != (n, spec.d_model):
        raise AssertionError(f"tokens must be float32 [{n},{spec.d_model}], got {s.dtype} {s.shape}")
    if g.dtype != np.int64 or g.shape != (n, 2):
        raise AssertionError("segment must be int64 [N, 2] (role id, modality id)")
    if not (np.isin(g[:, 0], [ROLE_IDS[r] for r in ROLES]).all() and np.all(g[:, 1] == MODALITY_IDS[spec.modality])):
        raise AssertionError("segment ids not from ROLE_IDS / MODALITY_IDS, or wrong modality")
    if c.dtype != np.float32 or c.shape != (n, 3):
        raise AssertionError("coords must be float32 [N, 3]")
    if v.dtype != bool or v.shape != (n,):
        raise AssertionError("valid must be bool [N]")
    if (not is_example and np.any(c[:, 0] != 0)) or np.any(c[:, 1] != 0) or np.any(np.diff(c[v, 2]) <= 0) \
            or np.any(c[~v] != 0):
        raise AssertionError("coords must be (row, 0, increasing seconds) on valid rows, 0 on padding")
    if not np.all(np.isfinite(s)) or np.any(s[~v] != 0):
        raise AssertionError("tokens must be finite and exactly 0 where valid is False")


def batch(clips: list) -> dict:
    """Stack single-clip outputs to [B, N_max, ...] with right padding (valid False)."""
    if not clips:
        raise ValueError("empty batch")
    n = max(len(c["valid"]) for c in clips)
    b, d = len(clips), clips[0]["tokens"].shape[1]
    out = {"tokens": np.zeros((b, n, d), np.float32), "segment": np.zeros((b, n, 2), np.int64),
           "coords": np.zeros((b, n, 3), np.float32), "coord_valid": np.zeros((b, n, 3), bool),
           "valid": np.zeros((b, n), bool)}
    for i, c in enumerate(clips):
        m = len(c["valid"])
        for k in FIELDS:
            out[k][i, :m] = c[k]
        out["segment"][i, m:] = c["segment"][0]   # padding keeps the clip's (role, modality)
    return out


def to_core_layout(out: dict):
    """Shim to TODAY's core, which takes no segment, coords or mask.

    role "question" -> ("latent", [1, 1, N_valid, 256]) for begin_latent's first argument;
    any other role  -> ("notebook", [1, N_valid, 256]).
    Padded slots are dropped because the current core has no padding mask.
    """
    x = out["tokens"][out["valid"]]
    question = out["segment"][0, 0] == ROLE_IDS["question"]
    return ("latent", x[None, None]) if question else ("notebook", x[None])
