"""Synaptic downscaling (sleepb's SHY step) for one LoRA pair, in numpy so it is testable without MLX.

MLX layout: lora_a is (in, r), lora_b is (r, out); the weight change (transposed) is  scale * a @ b  (in x out).
SVD of that product through QR of the two thin factors, singular values x factor, those below thresh x the largest zeroed,
then refactored into the same shapes. Zeroed or padded rank slots get a fresh LoRA init column in a and a zero row in b, so the
change is untouched by them and they stay trainable.
"""
from __future__ import annotations

import math

import numpy as np


def shy_core(a: np.ndarray, b: np.ndarray, scale: float, factor: float, thresh: float, rng: np.random.Generator):
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    nin, r = a.shape
    nout = b.shape[1]
    Qa, Ra = np.linalg.qr(a)          # (in, m), (m, r)
    Qb, Rb = np.linalg.qr(b.T)        # (out, m), (m, r)
    core = scale * (Ra @ Rb.T)        # (m, m)
    U, S, Vh = np.linalg.svd(core)
    if float(S.max()) <= 0.0:
        return a.copy(), b.copy(), 0, 0, 0.0, 0.0
    S2 = S * factor
    zero = S < thresh * S.max()
    S2 = np.where(zero, 0.0, S2)
    sq = np.sqrt(S2 / scale)
    m = S.shape[0]
    a2 = np.zeros((nin, r), dtype=np.float32)
    b2 = np.zeros((r, nout), dtype=np.float32)
    a2[:, :m] = (Qa @ U) * sq[None, :]
    b2[:m, :] = sq[:, None] * (Vh @ Qb.T)
    dead = [i for i in range(r) if i >= m or bool(zero[i])]
    if dead:
        bound = 1.0 / math.sqrt(nin)
        a2[:, dead] = rng.uniform(-bound, bound, size=(nin, len(dead))).astype(np.float32)
        b2[dead, :] = 0
    return a2, b2, int(zero.sum()), m, float((S ** 2).sum()), float((S2 ** 2).sum())
