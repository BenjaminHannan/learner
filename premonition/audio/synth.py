"""Deterministic synthetic test signals (16 kHz mono float64). TESTS ONLY.

These are plumbing fixtures. They are not speech and say nothing about how a
real encoder or the reasoner will behave on real audio.
"""
from __future__ import annotations

import numpy as np

from .frontend import SAMPLE_RATE


def _t(seconds: float, sr: int) -> np.ndarray:
    n = int(round(seconds * sr))
    if n < 1:
        raise ValueError("duration too short")
    return np.arange(n) / sr


def silence(seconds: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    return np.zeros_like(_t(seconds, sr))


def tone(freq: float, seconds: float, amp: float = 0.5, sr: int = SAMPLE_RATE) -> np.ndarray:
    return amp * np.sin(2 * np.pi * freq * _t(seconds, sr))


def chirp(f0: float, f1: float, seconds: float, amp: float = 0.5, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Linear frequency sweep from f0 to f1 Hz."""
    t = _t(seconds, sr)
    phase = 2 * np.pi * (f0 * t + 0.5 * (f1 - f0) / seconds * t ** 2)
    return amp * np.sin(phase)


def noise_burst(seconds: float, start: float, length: float, amp: float = 0.3,
                seed: int = 0, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Silence with one white-noise burst; deterministic for a given seed."""
    x = silence(seconds, sr)
    a, b = int(start * sr), int((start + length) * sr)
    if not (0 <= a < b <= len(x)):
        raise ValueError("burst outside the clip")
    x[a:b] = amp * np.random.default_rng(seed).standard_normal(b - a)
    return x


def syllables(n: int = 3, rate_hz: float = 4.0, carrier: float = 220.0, seconds: float | None = None,
              amp: float = 0.5, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Amplitude-modulated 'syllable' bursts: n raised-cosine envelopes on a
    harmonic carrier (carrier, 2x, 3x), at about the rate of spoken syllables."""
    seconds = seconds if seconds is not None else n / rate_hz
    t = _t(seconds, sr)
    period = 1.0 / rate_hz
    env = np.zeros_like(t)
    for i in range(n):
        start = i * period
        local = (t - start) / (0.6 * period)
        inside = (local >= 0) & (local <= 1)
        env[inside] = 0.5 - 0.5 * np.cos(2 * np.pi * local[inside])
    wave = sum(np.sin(2 * np.pi * carrier * h * t) / h for h in (1, 2, 3))
    return amp * env * wave / 1.84
