"""Sound effects by code (numpy only, fixed seeds). Each is rendered mono 48 kHz, peak -3 dBFS, with 5 ms fades so nothing clicks.
  python3 sfx.py OUTDIR
Gains used in the mix (dB relative to these files) are in mix.py / AUDIO.md."""
import sys, numpy as np
from alib import *
rng = lambda s: np.random.default_rng(s)
def fade(x, a=0.005, b=0.01):
    n, m = int(a * SR), int(b * SR); x = x.copy(); x[:n] *= np.linspace(0, 1, n); (x.__setitem__(slice(-m, None), x[-m:] * np.linspace(1, 0, m)) if m else None); return x
def peak(x, d=-3): return x * db(d) / np.abs(x).max()

def whoosh(dur=0.7):
    """scene change: airy noise whose brightness sweeps up then down (8 bands, each peaking at a different time)"""
    n = int(dur * SR); t = np.linspace(0, 1, n); nz = rng(1).standard_normal(n); y = np.zeros(n)
    cs = np.geomspace(250, 3800, 8)
    for i, c in enumerate(cs):
        band = fft_filter(fft_filter(nz, c / 1.5, c * 1.5, 2), None, None)
        centre = 0.25 + 0.5 * i / 7 if i % 1 == 0 else 0.5
        y += band / np.sqrt(c) * np.exp(-((t - centre) / 0.17) ** 2)
    y *= np.sin(np.pi * t) ** 1.5                                  # soft in, soft out
    return fade(peak(y))

def pop(dur=0.18):
    """item appears: a round 'bloop', pitch falls 620 -> 300 Hz in 70 ms"""
    n = int(dur * SR); t = np.arange(n) / SR
    f = 300 + 320 * np.exp(-t / 0.03); ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.05) + 0.2 * np.sin(2 * ph) * np.exp(-t / 0.02)
    return fade(peak(y), 0.002, 0.03)

def tick(dur=0.05):
    """count-up: a light dry click (2.4 kHz + a little 4.8 kHz), 30 ms"""
    n = int(dur * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * 2400 * t) + 0.3 * np.sin(2 * np.pi * 4800 * t)) * np.exp(-t / 0.008)
    return fade(peak(y), 0.0005, 0.01)

def chime(dur=1.6):
    """key result: two soft bell notes G5 then C6 (a rising fourth, 'ta-da' but quiet), bell partials 1, 2.0, 3.0, 4.2"""
    n = int(dur * SR); y = np.zeros(n)
    for f, t0, a in ((784, 0.0, 1.0), (1047, 0.14, 0.9)):
        i0 = int(t0 * SR); t = np.arange(n - i0) / SR
        note = sum(p * np.sin(2 * np.pi * f * h * t) * np.exp(-t / d) for h, p, d in ((1, 1, 0.55), (2, 0.35, 0.3), (3, 0.12, 0.18), (4.2, 0.05, 0.1)))
        y[i0:] += a * note * np.minimum(1, t / 0.004)
    return fade(peak(y), 0.002, 0.2)

def riser(dur=1.6):
    """before a reveal: filtered noise rising 200 Hz -> 5 kHz with a sine glide 220 -> 660 Hz, swells and stops 30 ms before the end"""
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur; nz = rng(2).standard_normal(n)
    y = np.zeros(n)
    for c in np.geomspace(250, 5000, 10):
        pos = np.log(c / 250) / np.log(20)
        y += fft_filter(nz, c / 1.4, c * 1.4, 2) / np.sqrt(c) * np.exp(-((u - (0.15 + 0.8 * pos)) / 0.22) ** 2)
    glide = np.sin(2 * np.pi * np.cumsum(220 * 3 ** u) / SR)
    y = peak(y) * u ** 1.6 + 0.25 * glide * u ** 2
    y[int((dur - 0.03) * SR):] *= np.linspace(1, 0, n - int((dur - 0.03) * SR))
    return fade(peak(y), 0.01, 0.0)

EFFECTS = {'whoosh': whoosh, 'pop': pop, 'tick': tick, 'chime': chime, 'riser': riser}
if __name__ == '__main__':
    out = sys.argv[1]
    for k, f in EFFECTS.items():
        x = f(); write_wav(f'{out}/sfx-{k}.wav', x)
        print(k, 'dur', round(len(x) / SR, 2), 's', 'peak dBFS', round(20 * np.log10(np.abs(x).max()), 1), 'rms dBFS', round(20 * np.log10(np.sqrt(np.mean(x ** 2))), 1))
