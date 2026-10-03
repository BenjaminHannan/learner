"""Deterministic synthetic test signals (16 kHz, float64; mono, plus stereo toy scenes). TESTS ONLY.

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


# ----------------------------------------------------------------------------- stereo toy scenes
# Toy "game-like" sounds for plumbing tests and for the CPU scene generator in
# design section (j). They are NOT Minecraft sounds and train nothing real.

def pan_gains(azimuth_deg: float) -> tuple:
    """Constant-power amplitude panning. 0 = ahead, +90 = left, -90 = right, 180 = behind.

    Only sin(azimuth) is used, so azimuth a and 180 - a give IDENTICAL gains:
    plain amplitude panning cannot tell front from back. Whether Minecraft's
    default (non-HRTF) mixing behaves like this is UNTESTED here.
    """
    p = float(np.sin(np.deg2rad(azimuth_deg)))          # +1 full left, -1 full right
    theta = (p + 1.0) * np.pi / 4.0
    return float(np.sin(theta)), float(np.cos(theta))    # (left, right)


def toy_sound(kind: str, seconds: float, seed: int = 0, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Mono toy sounds: 'hiss' (rising 2-6 kHz noise), 'steps' (clicks at 2.5 Hz),
    'groan' (110 Hz harmonics with vibrato), 'twang' (fast falling chirp)."""
    t = _t(seconds, sr)
    rng = np.random.default_rng(seed)
    if kind == "hiss":
        x = rng.standard_normal(len(t))
        spec = np.fft.rfft(x)
        f = np.fft.rfftfreq(len(t), 1 / sr)
        spec[(f < 2000) | (f > 6000)] = 0
        x = np.fft.irfft(spec, len(t))
        x = x / (np.abs(x).max() + 1e-12) * np.linspace(0.3, 1.0, len(t))
    elif kind == "steps":
        x = np.zeros(len(t))
        for c in np.arange(0.0, seconds, 0.4):
            a = int(c * sr)
            n = min(int(0.03 * sr), len(t) - a)
            x[a:a + n] = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.006 * sr))
    elif kind == "groan":
        f0 = 110 * (1 + 0.03 * np.sin(2 * np.pi * 5 * t))
        ph = 2 * np.pi * np.cumsum(f0) / sr
        x = sum(np.sin(h * ph) / h for h in (1, 2, 3, 4)) / 2.1
    elif kind == "twang":
        x = chirp(3000, 600, seconds, amp=1.0, sr=sr) * np.exp(-t / 0.08)
    else:
        raise ValueError(f"unknown kind {kind!r}")
    return x


def stereo_scene(events: list, seconds: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    """[n, 2] stereo mix. events: dicts with kind, start, length, azimuth (deg), gain, seed.

    Labels are exact by construction (the event list itself), which is what
    makes generated scenes usable as sealed CPU test sets.
    """
    n = int(round(seconds * sr))
    out = np.zeros((n, 2))
    for e in events:
        a = int(round(e["start"] * sr))
        x = e.get("gain", 0.5) * toy_sound(e["kind"], e["length"], e.get("seed", 0), sr)
        b = min(a + len(x), n)
        if not 0 <= a < n:
            raise ValueError("event starts outside the clip")
        gl, gr = pan_gains(e.get("azimuth", 0.0))
        out[a:b, 0] += gl * x[:b - a]
        out[a:b, 1] += gr * x[:b - a]
    return out
