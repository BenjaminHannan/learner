"""Copy guard: min Hamming distance over shifts (-1..1, vacated white) and mirror."""
import numpy as np


def _variants(ys):
    ys = np.asarray(ys, dtype=np.int8)
    out = []
    for flip in (False, True):
        g = ys[:, :, ::-1] if flip else ys
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                s = np.zeros_like(g)
                s[:, max(dy, 0):12 + min(dy, 0), max(dx, 0):12 + min(dx, 0)] = \
                    g[:, max(-dy, 0):12 + min(-dy, 0), max(-dx, 0):12 + min(-dx, 0)]
                out.append(s)
    return np.concatenate(out, axis=0)


def _onehot_flat(g):
    g = np.asarray(g).reshape(len(g), -1)
    oh = np.zeros((g.shape[0], 5, g.shape[1]), dtype=np.float32)
    idx = np.arange(g.shape[1])
    for k in range(5):
        oh[:, k, :] = (g == k)
    return oh.reshape(g.shape[0], -1)


class CopyGuard:
    def __init__(self, examples, k=0):
        self.V = _onehot_flat(_variants(examples)).T.copy()   # (720, 18M)
        self.k = int(k)

    def distances(self, xs, chunk=256):
        xs = np.asarray(xs)
        if xs.ndim == 2:
            xs = xs[None]
        out = np.empty(len(xs), dtype=np.int64)
        for i in range(0, len(xs), chunk):
            X = _onehot_flat(xs[i:i + chunk])
            m = X @ self.V
            out[i:i + chunk] = 144 - np.rint(m.max(axis=1)).astype(np.int64)
        return out

    def is_copy(self, xs):
        return self.distances(xs) <= self.k


def distance(x, ys):
    """Min distance of one grid x (or batch) to any grid in ys under shifts and mirror."""
    d = CopyGuard(ys).distances(x)
    return int(d[0]) if np.asarray(x).ndim == 2 else d


def calibrate_k(heldback, examples):
    """Largest k such that at most 1% of held-back houses have distance <= k."""
    d = np.sort(CopyGuard(examples).distances(heldback))
    allowed = int(np.floor(0.01 * len(d) + 1e-9))
    # count(d <= k) <= allowed  <=>  k < d[allowed]
    if allowed >= len(d):
        return int(d[-1])
    return int(d[allowed]) - 1
