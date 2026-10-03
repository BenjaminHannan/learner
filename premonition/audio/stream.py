"""Streaming stereo hearing for game sound (numpy CPU reference, no torch).

Design: design/next-parts/audio-input.md section (j). Everything here is
plumbing. It says nothing about whether a trained ear or the reasoner will
hear a creeper; that needs the S-track experiments.

Why a second front end (SHOWN in code): ``frontend.log_mel`` is built for
Whisper and is not causal in two ways. Its STFT is centred with reflect
padding, so frame i looks 200 samples (12.5 ms) ahead, and ``whisper_norm``
floors every frame at the loudest frame of the whole clip, so one loud sound
later in the clip changes the features of everything before it. A game ear
must react to sound as it arrives, so this module uses:

  - an uncentred STFT (frame i = samples [i*hop, i*hop + n_fft)), emitted
    the moment its last sample arrives;
  - a fixed log floor and scale instead of a per-clip maximum, so a frame's
    features depend only on its own samples;
  - two channels (left, right) plus their level difference (ILD) per mel
    band, so left/right direction is in the features.

Pipeline, one step per incoming chunk of samples:

  stereo samples [n, 2]
    -> StreamingStereoMel     frames [m, 3*80] at 100 Hz  (L, R, ILD per mel band)
    -> CausalConvEar          frames [m, width]           dilated causal conv, state carried
    -> AudioWindow            last W slots of the shared Workspace record,
                              slot = k frames (k=5 -> 50 ms = one Minecraft tick),
                              coords time = slot centre minus "now" (seconds, <= 0)

``AudioWindow`` reuses ``adapter.adapt`` for the slot projection so the
Workspace fields are exactly the ones PR #22 / PR #23 define.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math

import numpy as np

from .adapter import ModalityAdapterSpec, adapt, audio_segment, _gelu
from .frontend import HOP_LENGTH, N_FFT, N_MELS, SAMPLE_RATE, hann_window, mel_filterbank

N_CHANNEL_FEATURES = 3          # left log-mel, right log-mel, ILD (left minus right)
LOG_FLOOR = -6.0                # fixed log10 power floor (replaces Whisper's clip max - 8)


def _check_stereo(chunk: np.ndarray) -> np.ndarray:
    a = np.asarray(chunk)
    if a.ndim == 1:                                   # mono: same signal both ears
        a = np.stack([a, a], axis=1)
    if a.ndim != 2 or a.shape[1] != 2:
        raise ValueError(f"chunk must be [n] mono or [n, 2] stereo, got {a.shape}")
    if not np.issubdtype(a.dtype, np.floating):
        raise TypeError("samples must be floating point in [-1, 1]")
    if not np.all(np.isfinite(a)):
        raise ValueError("samples contain NaN or inf")
    return a.astype(np.float64, copy=False)


class StreamingStereoMel:
    """Causal stereo log-mel. ``push(chunk)`` returns every frame that is now complete.

    Frame i covers samples [i*hop, i*hop + n_fft). It is emitted as soon as
    sample i*hop + n_fft - 1 has arrived, and is never revised. Output per
    frame: concat(left log-mel, right log-mel, left - right) -> [3 * n_mels],
    float32, with log10 power floored at ``floor`` and scaled by (x + 4) / 4
    (Whisper's scale, but with a fixed floor so it is causal).
    """

    def __init__(self, n_mels: int = N_MELS, n_fft: int = N_FFT, hop: int = HOP_LENGTH,
                 sr: int = SAMPLE_RATE, floor: float = LOG_FLOOR):
        self.n_mels, self.n_fft, self.hop, self.sr, self.floor = n_mels, n_fft, hop, sr, floor
        self.window = hann_window(n_fft)
        self.mel = mel_filterbank(sr=sr, n_fft=n_fft, n_mels=n_mels)
        self.reset()

    def reset(self):
        self._buf = np.zeros((0, 2))
        self.frames_out = 0

    @property
    def d_out(self) -> int:
        return N_CHANNEL_FEATURES * self.n_mels

    def frame_end_seconds(self, i) -> np.ndarray:
        """Time (s, from stream start) at which frame i becomes available."""
        return (np.asarray(i) * self.hop + self.n_fft) / self.sr

    def push(self, chunk: np.ndarray) -> np.ndarray:
        buf = np.concatenate([self._buf, _check_stereo(chunk)], axis=0)
        count = 0 if len(buf) < self.n_fft else 1 + (len(buf) - self.n_fft) // self.hop
        if count == 0:
            self._buf = buf
            return np.zeros((0, self.d_out), np.float32)
        idx = np.arange(self.n_fft)[None, :] + self.hop * np.arange(count)[:, None]
        frames = buf[idx] * self.window[None, :, None]               # [count, n_fft, 2]
        power = np.abs(np.fft.rfft(frames, axis=1)) ** 2              # [count, bins, 2]
        mel = np.einsum("mb,cbk->ckm", self.mel, power)                # [count, 2, n_mels]
        logm = np.maximum(np.log10(np.maximum(mel, 1e-12)), self.floor)
        left, right = (logm[:, 0] + 4.0) / 4.0, (logm[:, 1] + 4.0) / 4.0
        out = np.concatenate([left, right, left - right], axis=1).astype(np.float32)
        self._buf = buf[count * self.hop:]
        self.frames_out += count
        return out


def ild_pan_estimate(features: np.ndarray, n_mels: int = N_MELS) -> np.ndarray:
    """Hand-written left/right baseline: mean ILD over bands weighted by loudness.

    Positive = louder on the left. Used by tests to show the stereo features
    carry left/right. It cannot separate front from back (see synth.pan_gains).
    """
    f = np.asarray(features)
    left, right, ild = f[:, :n_mels], f[:, n_mels:2 * n_mels], f[:, 2 * n_mels:]
    w = np.maximum(np.maximum(left, right) - (LOG_FLOOR + 4.0) / 4.0, 0.0)
    return (w * ild).sum(axis=1) / np.maximum(w.sum(axis=1), 1e-9)


# ----------------------------------------------------------------------------- learned ear


@dataclass(frozen=True)
class CausalConvEarSpec:
    """Dilated causal 1-D conv stack over frames (the 'small ear', SUGGESTED default).

    Each layer: y = x + GELU(conv_causal(x)) (first layer has no residual,
    it changes width). Receptive field = 1 + (kernel - 1) * sum(dilations) frames.
    """
    d_in: int = N_CHANNEL_FEATURES * N_MELS
    width: int = 128
    kernel: int = 3
    dilations: tuple = (1, 2, 4, 8, 16)
    frame_period: float = HOP_LENGTH / SAMPLE_RATE

    def __post_init__(self):
        if self.kernel < 1 or not self.dilations or any(d < 1 for d in self.dilations):
            raise ValueError("kernel and dilations must be positive")

    @property
    def receptive_field_frames(self) -> int:
        return 1 + (self.kernel - 1) * sum(self.dilations)

    @property
    def receptive_field_seconds(self) -> float:
        return self.receptive_field_frames * self.frame_period

    def weight_shapes(self) -> dict:
        shapes = {}
        for i, _ in enumerate(self.dilations):
            c_in = self.d_in if i == 0 else self.width
            shapes[f"w{i}"] = (self.kernel, c_in, self.width)
            shapes[f"b{i}"] = (self.width,)
        return shapes

    def parameter_count(self) -> int:
        return int(sum(np.prod(s) for s in self.weight_shapes().values()))


def init_ear_weights(spec: CausalConvEarSpec, seed: int = 0) -> dict:
    """Deterministic random weights for tests and shape checks only."""
    rng = np.random.default_rng(seed)
    out = {}
    for name, shape in spec.weight_shapes().items():
        if name.startswith("b"):
            out[name] = np.zeros(shape, np.float32)
        else:
            fan_in = shape[0] * shape[1]
            out[name] = (rng.standard_normal(shape) / math.sqrt(fan_in)).astype(np.float32)
    return out


def _causal_layer(x: np.ndarray, w: np.ndarray, b: np.ndarray, dilation: int, history: np.ndarray):
    """x [T, c_in], history [(k-1)*d, c_in] of earlier inputs -> (y [T, c_out], new history)."""
    k = w.shape[0]
    span = (k - 1) * dilation
    full = np.concatenate([history, x], axis=0)
    y = np.zeros((len(x), w.shape[2]))
    for j in range(k):
        # tap j looks back (k - 1 - j) * dilation frames
        start = j * dilation
        y += full[start:start + len(x)] @ w[j]
    y += b
    new_hist = full[len(full) - span:] if span else full[:0]
    return y, new_hist


class CausalConvEar:
    """Streaming wrapper: ``push(frames)`` returns one output frame per input frame.

    Exactly equal (up to float rounding) to running the whole sequence at once
    with zero history, whatever the chunk sizes (shown by tests).
    """

    def __init__(self, spec: CausalConvEarSpec, weights: dict):
        shapes = spec.weight_shapes()
        if set(weights) != set(shapes) or any(weights[k].shape != s for k, s in shapes.items()):
            raise ValueError("ear weights do not match spec")
        self.spec, self.w = spec, {k: v.astype(np.float64) for k, v in weights.items()}
        self.reset()

    def reset(self):
        s = self.spec
        self._hist = [np.zeros(((s.kernel - 1) * d, s.d_in if i == 0 else s.width))
                      for i, d in enumerate(s.dilations)]

    def push(self, frames: np.ndarray) -> np.ndarray:
        x = np.asarray(frames, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != self.spec.d_in:
            raise ValueError(f"frames must be [T, {self.spec.d_in}]")
        for i, d in enumerate(self.spec.dilations):
            y, self._hist[i] = _causal_layer(x, self.w[f"w{i}"], self.w[f"b{i}"], d, self._hist[i])
            y = _gelu(y)
            x = y if i == 0 else x + y
        return x.astype(np.float32)


# ----------------------------------------------------------------------------- workspace window


class AudioWindow:
    """Keeps the last ``n_slots`` audio slots as a Workspace record, updated per chunk.

    ``adapter_spec`` must have frame_period equal to the ear's frame period and
    downsample = frames per slot. Slots are projected once, when complete, and
    never revised (causal). ``workspace(now)`` returns tokens/segment/coords/valid
    for the window with coords time = slot centre - now (seconds, <= 0), so the
    numbers stay small however long the game runs; the core's relative bias only
    uses differences anyway.
    """

    def __init__(self, adapter_spec: ModalityAdapterSpec, adapter_weights: dict,
                 n_slots: int = 40, role: str = "notebook"):
        self.spec, self.weights, self.n_slots, self.role = adapter_spec, adapter_weights, n_slots, role
        self.reset()

    def reset(self):
        self._pending = np.zeros((0, self.spec.d_in), np.float32)
        self._slots = deque(maxlen=self.n_slots)      # (token [256], centre seconds from start)
        self.slots_done = 0

    def push(self, frames: np.ndarray) -> int:
        """Add ear frames; returns how many new slots completed."""
        f = np.concatenate([self._pending, np.asarray(frames, np.float32)], axis=0)
        k = self.spec.downsample
        n_new = len(f) // k
        if n_new:
            out = adapt(self.spec, self.weights, f[:n_new * k], role=self.role)
            for j in range(n_new):
                centre = (self.slots_done + j + 0.5) * self.spec.slot_seconds
                self._slots.append((out["tokens"][j], centre))
            self.slots_done += n_new
        self._pending = f[n_new * k:]
        return n_new

    def workspace(self, now: float, pad_to: int | None = None) -> dict:
        n = pad_to or self.n_slots
        if n < len(self._slots):
            raise ValueError("pad_to smaller than the number of held slots")
        tokens = np.zeros((n, self.spec.d_model), np.float32)
        coords = np.zeros((n, 3), np.float32)
        valid = np.zeros(n, bool)
        for i, (tok, centre) in enumerate(self._slots):
            tokens[i], coords[i, 2], valid[i] = tok, centre - now, True
        return {"tokens": tokens, "segment": audio_segment(self.role, n, self.spec.modality),
                "coords": coords, "valid": valid}


def hearing_latency_bound(hop: int = HOP_LENGTH, n_fft: int = N_FFT, sr: int = SAMPLE_RATE,
                          slot_frames: int = 5) -> dict:
    """Worst-case algorithmic delay (s) from a sound's first sample to the first slot holding it.

    A frame is emitted when its window ends, so the first frame containing a
    sample that starts at time s is out within one hop of s. The slot holding
    that frame completes after at most slot_frames - 1 further frames. The
    learned ear adds no delay (causal). Compute time and chunk delivery are extra.
    """
    frame = hop / sr
    return {"first_frame": frame, "slot_fill": (slot_frames - 1) * frame,
            "total": slot_frames * frame, "window_seconds": n_fft / sr}
