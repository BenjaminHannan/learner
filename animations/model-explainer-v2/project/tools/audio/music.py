"""Music bed by code. A calm 8-bar loop (soft pad, round bass, sparse pluck, quiet shaker) built in a circular buffer, so the
loop is seamless by construction (no crossfade needed). 96 BPM -> 2.5 s bar -> 20 s loop -> 3 loops = 60 s.
  python3 music.py --root 0 --name bed-C --seconds 60        (root = semitones above C; 0 = C, 2 = D, 5 = F, 7 = G ...)
"""
import argparse, numpy as np
from alib import *

BPM = 96; BEAT = 60 / BPM; BAR = 4 * BEAT; BARS = 8; LOOP = BAR * BARS      # 20.0 s
N = int(round(LOOP * SR))
# chord = (bass midi, [pad midis], [pluck midis])  I - vi - IV - V(sus-ish), two bars each; major keys, add9/maj7 colour, no sharp dissonance
PROG = [(36, [55, 59, 62, 64], [67, 71, 74, 76]),     # Cmaj9-ish
        (33, [57, 60, 64, 67], [69, 72, 76, 79]),     # Am7
        (41, [57, 60, 64, 65], [69, 72, 76, 77]),     # Fmaj7
        (43, [55, 59, 62, 65], [67, 71, 74, 79])]     # G7sus-ish -> pulls back to the start
mtof = lambda m: 440 * 2 ** ((m - 69) / 12)

def add(buf, x, t0):
    """add x into circular buffer starting at time t0 (wraps around the end: this is what makes the loop seamless)"""
    i0 = int(round(t0 * SR)) % N
    idx = (i0 + np.arange(len(x))) % N
    np.add.at(buf, idx, x)

def pad_note(f, dur, rng):
    L = int((dur + 1.6) * SR); t = np.arange(L) / SR
    y = np.zeros(L)
    for det in (-0.07, 0.0, 0.06):                            # three slightly detuned voices = slow warm beating
        ff = f * 2 ** (det / 12); ph = rng.uniform(0, 2 * np.pi)
        for h, a in ((1, 1.0), (2, 0.38), (3, 0.16), (4, 0.07)):
            y += a * np.sin(2 * np.pi * ff * h * t + ph * h)
    env = np.minimum(1, t / 0.9) ** 2 * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.45))
    return y * env

def pluck(f, rng):
    L = int(1.4 * SR); t = np.arange(L) / SR
    y = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.12) + 0.12 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.06)
    y = y + 0.4 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.25)    # bell-like octave layer: sparkle between 1 and 3 kHz
    return y * np.minimum(1, t / 0.004) * np.exp(-t / 0.33)

def bass(f, dur):
    L = int((dur + 0.4) * SR); t = np.arange(L) / SR
    y = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    return y * np.minimum(1, t / 0.05) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.12)) * np.exp(-t / 3.0)

def reverb_ir(rng, rt=2.4, damp=3500):
    L = int(rt * 1.2 * SR); t = np.arange(L) / SR
    ir = rng.standard_normal(L) * np.exp(-6.9 * t / rt)
    ir = fft_filter(ir, 120, damp, 2)
    ir[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
    return ir

def render_loop(root=0, seed=1):
    rng = np.random.default_rng(seed)
    sh = 2 ** (root / 12)
    padL, padR, bs, plk, shk = (np.zeros(N) for _ in range(5))
    plkR = np.zeros(N)
    for ci, (b, pad, pl) in enumerate(PROG):
        t0 = ci * 2 * BAR
        for k, m in enumerate(pad):
            add(padL if k % 2 == 0 else padR, 0.20 * pad_note(mtof(m + root), 2 * BAR, rng), t0)
            add(padR if k % 2 == 0 else padL, 0.10 * pad_note(mtof(m + root), 2 * BAR, rng), t0)   # a little of each voice in both ears
        for bar in range(2):
            add(bs, 0.9 * bass(mtof(b + root), BAR * 0.97), t0 + bar * BAR)
        # sparse pluck pattern on 8th notes: hits at steps (0,3,5,6) of the bar's 8, notes walk through the chord tones
        pat = [(0, 0), (3, 2), (5, 1), (6, 3)] if ci % 2 == 0 else [(0, 1), (2, 3), (5, 2), (7, 0)]
        for bar in range(2):
            for step, ti in pat:
                vel = 0.55 + 0.25 * rng.random()
                tt = t0 + bar * BAR + step * BEAT / 2
                add(plk if (step + bar) % 2 == 0 else plkR, vel * 0.5 * pluck(mtof(pl[(ti + bar) % 4] + root), rng), tt)
    # quiet shaker on the off-beat 8ths
    for i in range(BARS * 4):
        L = int(0.05 * SR); nz = rng.standard_normal(L); nz = fft_filter(np.concatenate([nz, np.zeros(2048)]), 5000, 11000)[:L]
        add(shk, 0.06 * nz * np.exp(-np.arange(L) / (0.012 * SR)), i * BEAT + BEAT / 2)
    L_ = padL + 0.45 * bs + 1.5 * plk + 0.9 * shk
    R_ = padR + 0.45 * bs + 1.5 * plkR + 0.9 * shk
    # circular reverb (FFT multiply of the loop with the IR wrapped to the loop length): tail of bar 8 flows into bar 1
    out = []
    for dry, seed_ in ((L_, 11), (R_, 12)):
        ir = reverb_ir(np.random.default_rng(seed_ + seed)); irp = np.zeros(N); irp[: len(ir)] = ir[:N]
        wet = np.fft.irfft(np.fft.rfft(dry) * np.fft.rfft(irp), N)
        wet *= np.sqrt(np.sum(dry ** 2) / np.sum(wet ** 2))
        y = 0.72 * dry + 0.55 * wet
        y = fft_filter(y, 35, 7500, 2)                         # remove sub rumble, keep it dark and warm
        out.append(y)
    y = np.stack(out, 1)
    return y

def normalise_rms(y, target_dbfs=-24):
    r = np.sqrt(np.mean(y ** 2)); return y * db(target_dbfs) / r

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--root', type=int, default=0); ap.add_argument('--name', default='bed-C')
    ap.add_argument('--seconds', type=float, default=60); ap.add_argument('--out', default='.')
    a = ap.parse_args()
    y = normalise_rms(render_loop(a.root))
    reps = int(np.ceil(a.seconds / LOOP)); z = np.tile(y, (reps, 1))[: int(a.seconds * SR)]
    print('loop seconds', LOOP, 'peak', np.abs(z).max())
    write_wav(f'{a.out}/{a.name}-loop.wav', y); write_wav(f'{a.out}/{a.name}-{int(a.seconds)}s.wav', z)
