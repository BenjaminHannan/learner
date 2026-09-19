"""Idealised capacity / interference / correction probe for fast-memory stores.

No learning here: keys and values are given vectors. This isolates the storage
mechanism itself (what the memory can hold if the encoder were perfect).
Recall is correct if the read-out is closer (cosine) to the true value than to
every other stored value AND to 1000 never-stored distractor values.
"""
import numpy as np

rng = np.random.default_rng(0)
D = 128  # repo's memory width


def unit(x):
    return x / np.linalg.norm(x, axis=-1, keepdims=True)


def make_keys(n, rho, d=D):
    """Keys with pairwise cosine ~rho (a shared 'topic' component)."""
    shared = unit(rng.standard_normal(d))
    noise = unit(rng.standard_normal((n, d)))
    return unit(np.sqrt(rho) * shared + np.sqrt(1 - rho) * noise)


def noisy(q, sigma):
    if sigma == 0:
        return q
    return unit(q + sigma * unit(rng.standard_normal(q.shape)))


class Delta:
    def __init__(self, dk=D, dv=D):
        self.W = np.zeros((dv, dk))

    def write(self, k, v):
        self.W += np.outer(v - self.W @ k, k)

    def read(self, q):
        return self.W @ q


class Hebb:
    def __init__(self, dk=D, dv=D):
        self.W = np.zeros((dv, dk))

    def write(self, k, v):
        self.W += np.outer(v, k)

    def read(self, q):
        return self.W @ q


class Slots:
    """Explicit slot store; correction = overwrite nearest slot if very similar."""

    def __init__(self, beta=50.0, overwrite_cos=0.999):
        self.K, self.V = [], []
        self.beta, self.th = beta, overwrite_cos

    def write(self, k, v):
        if self.K:
            sims = np.array(self.K) @ k
            j = int(np.argmax(sims))
            if sims[j] >= self.th:
                self.V[j] = v
                return
        self.K.append(k)
        self.V.append(v)

    def read(self, q):  # softmax attention = one modern-Hopfield update
        K, V = np.array(self.K), np.array(self.V)
        s = self.beta * (K @ q)
        a = np.exp(s - s.max())
        a /= a.sum()
        return a @ V


class SparseDelta(Delta):
    """Pattern separation: fixed random expansion to m dims + top-k winners."""

    def __init__(self, m=2048, active=64):
        super().__init__(dk=m)
        self.P = rng.standard_normal((m, D)) / np.sqrt(D)
        self.active = active

    def code(self, x):
        h = self.P @ x
        out = np.zeros_like(h)
        idx = np.argpartition(h, -self.active)[-self.active:]
        out[idx] = h[idx]
        return unit(out)

    def write(self, k, v):
        super().write(self.code(k), v)

    def read(self, q):
        return super().read(self.code(q))


def recall(mem, keys, vals, sigma, distract):
    cands = unit(np.vstack([vals, distract]))
    ok = 0
    for i in range(len(keys)):
        r = mem.read(noisy(keys[i], sigma))
        ok += int(np.argmax(cands @ unit(r[None])[0]) == i)
    return ok / len(keys)


def run(kind, n, rho, sigma, trials=3):
    accs = []
    for _ in range(trials):
        keys = make_keys(n, rho)
        vals = unit(rng.standard_normal((n, D)))
        distract = unit(rng.standard_normal((1000, D)))
        mem = {"delta": Delta, "hebb": Hebb, "slots": Slots, "sparse": SparseDelta}[kind]()
        for k, v in zip(keys, vals):
            mem.write(k, v)
        accs.append(recall(mem, keys, vals, sigma, distract))
    return np.mean(accs)


def correction(kind, n=64, rho=0.0, frac=0.25):
    keys = make_keys(n, rho)
    vals = unit(rng.standard_normal((n, D)))
    distract = unit(rng.standard_normal((1000, D)))
    mem = {"delta": Delta, "hebb": Hebb, "slots": Slots, "sparse": SparseDelta}[kind]()
    for k, v in zip(keys, vals):
        mem.write(k, v)
    m = int(n * frac)
    new_vals = unit(rng.standard_normal((m, D)))
    for i in range(m):
        mem.write(keys[i], new_vals[i])
    final = vals.copy()
    final[:m] = new_vals
    # candidates include the superseded old values, so "still says old answer" counts as wrong
    cands = unit(np.vstack([final, vals[:m], distract]))
    ok_new = sum(int(np.argmax(cands @ unit(mem.read(keys[i])[None])[0]) == i) for i in range(m)) / m
    ok_rest = sum(int(np.argmax(cands @ unit(mem.read(keys[i])[None])[0]) == i) for i in range(m, n)) / (n - m)
    return ok_new, ok_rest


if __name__ == "__main__":
    kinds = ["hebb", "delta", "sparse", "slots"]
    print("Recall vs number of stored facts N (D=128, exact cue, random keys rho=0)")
    for n in [16, 64, 128, 256, 1024]:
        print(f"N={n:5d}", "  ".join(f"{k}={run(k, n, 0.0, 0.0):.2f}" for k in kinds))
    print("\nSimilar memories: keys share a component (pairwise cosine rho), N=64, exact cue")
    for rho in [0.0, 0.5, 0.8, 0.95]:
        print(f"rho={rho:.2f}", "  ".join(f"{k}={run(k, 64, rho, 0.0):.2f}" for k in kinds))
    print("\nNoisy cue (paraphrase-like): N=64, rho=0.5, query = key + noise of norm sigma")
    for sigma in [0.0, 0.3, 0.6, 1.0]:
        print(f"sigma={sigma:.1f}", "  ".join(f"{k}={run(k, 64, 0.5, sigma):.2f}" for k in kinds))
    print("\nCorrection: write 64 facts then re-write 16 of them with new values")
    for rho in [0.0, 0.8]:
        for k in kinds:
            a, b = correction(k, rho=rho)
            print(f"rho={rho:.1f} {k:6s} corrected-now-right={a:.2f} untouched-still-right={b:.2f}")


class DenseBig(SparseDelta):
    """Same 2048-d random expansion but NO winner-take-all: isolates size vs sparsity."""

    def code(self, x):
        return unit(self.P @ x)


def run2(cls, n, rho, sigma, trials=3):
    accs = []
    for _ in range(trials):
        keys = make_keys(n, rho)
        vals = unit(rng.standard_normal((n, D)))
        distract = unit(rng.standard_normal((1000, D)))
        mem = cls()
        for k, v in zip(keys, vals):
            mem.write(k, v)
        accs.append(recall(mem, keys, vals, sigma, distract))
    return np.mean(accs)


if __name__ == "__main__":
    print("\nSize vs sparsity (N=64): 2048-d dense expansion vs 2048-d sparse (64 active)")
    for rho in [0.5, 0.8]:
        print(f"rho={rho}", f"dense2048={run2(DenseBig, 64, rho, 0.0):.2f}", f"sparse2048={run2(SparseDelta, 64, rho, 0.0):.2f}")
    print("\nsparse2048 capacity, rho=0: ", "  ".join(f"N={n}:{run2(SparseDelta, n, 0.0, 0.0):.2f}" for n in [2048, 4096]))
    print("Memory floats: delta128=16384, sparse2048=262144, slots=256 per stored fact")
