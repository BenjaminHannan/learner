"""Toy sanity check: does a small net forget old arbitrary facts when it learns
16 new ones, and how much does interleaved replay / self-distillation help?
Pure numpy MLP with Adam. Facts: (subject, relation) -> object.
Not the real model; only checks that the proposed measurement protocol
produces distinguishable numbers at tiny scale.
"""
import numpy as np, time, sys

def run(seed, cond, ratio=0.5, steps=300, verbose=False):
    rng = np.random.default_rng(seed)
    S_old, S_new, R, O, D, H = 200, 8, 4, 64, 32, 256
    S = S_old + S_new
    facts = rng.integers(0, O, size=(S, R))           # ground-truth object per (s,r)
    old = [(s, r) for s in range(S_old) for r in range(R)]    # 800 old facts
    new = [(s, r) for s in range(S_old, S) for r in rng.choice(R, 2, replace=False)]  # 16 new facts
    P = {
        'Es': rng.normal(0, 0.3, (S, D)), 'Er': rng.normal(0, 0.3, (R, D)),
        'W1': rng.normal(0, np.sqrt(2 / (2 * D)), (2 * D, H)), 'b1': np.zeros(H),
        'W2': rng.normal(0, np.sqrt(1 / H), (H, O)), 'b2': np.zeros(O)}
    m = {k: np.zeros_like(v) for k, v in P.items()}; v2 = {k: np.zeros_like(v) for k, v in P.items()}
    t = [0]

    def fwd(Pp, s, r):
        x = np.concatenate([Pp['Es'][s], Pp['Er'][r]], 1)
        h = np.maximum(0, x @ Pp['W1'] + Pp['b1'])
        z = h @ Pp['W2'] + Pp['b2']
        return x, h, z

    def step(s, r, target_probs, lr):
        x, h, z = fwd(P, s, r)
        p = np.exp(z - z.max(1, keepdims=True)); p /= p.sum(1, keepdims=True)
        g = (p - target_probs) / len(s)
        G = {'W2': h.T @ g, 'b2': g.sum(0)}
        gh = g @ P['W2'].T * (h > 0)
        G['W1'] = x.T @ gh; G['b1'] = gh.sum(0)
        gx = gh @ P['W1'].T
        G['Es'] = np.zeros_like(P['Es']); np.add.at(G['Es'], s, gx[:, :D])
        G['Er'] = np.zeros_like(P['Er']); np.add.at(G['Er'], r, gx[:, D:])
        t[0] += 1
        for k in P:
            m[k] = 0.9 * m[k] + 0.1 * G[k]; v2[k] = 0.999 * v2[k] + 0.001 * G[k] ** 2
            mh = m[k] / (1 - 0.9 ** t[0]); vh = v2[k] / (1 - 0.999 ** t[0])
            P[k] -= lr * mh / (np.sqrt(vh) + 1e-8)

    def acc(fs, Pp=None):
        s = np.array([a for a, _ in fs]); r = np.array([b for _, b in fs])
        z = fwd(Pp or P, s, r)[2]
        return float((z.argmax(1) == facts[s, r]).mean())

    def onehot(s, r):
        y = np.zeros((len(s), O)); y[np.arange(len(s)), facts[s, r]] = 1; return y

    # "Childhood": learn old facts to criterion
    oa = np.array(old)
    for i in range(3000):
        idx = rng.integers(0, len(oa), 64); s, r = oa[idx, 0], oa[idx, 1]
        step(s, r, onehot(s, r), 3e-3)
    base_old = acc(old)
    snap = {k: v.copy() for k, v in P.items()}   # pre-sleep snapshot (teacher for old knowledge)

    # "Sleep": consolidate 16 new facts (assumed perfectly held by fast memory)
    na = np.array(new); B = 32; n_old = int(round(B * ratio)) if cond != 'new_only' else 0
    min_old = 1.0
    for i in range(steps):
        idx = rng.integers(0, len(na), B - n_old); s, r = na[idx, 0], na[idx, 1]
        y = onehot(s, r)
        if n_old:
            if cond == 'replay_exact':          # stored old episodes with their true answers
                j = rng.integers(0, len(oa), n_old); so, ro = oa[j, 0], oa[j, 1]; yo = onehot(so, ro)
            elif cond == 'self_distill':        # no stored answers: pre-sleep model labels random known cues
                so = rng.integers(0, S_old, n_old); ro = rng.integers(0, R, n_old)
                zo = fwd(snap, so, ro)[2]; yo = np.exp(zo - zo.max(1, keepdims=True)); yo /= yo.sum(1, keepdims=True)
            s = np.concatenate([s, so]); r = np.concatenate([r, ro]); y = np.concatenate([y, yo])
        step(s, r, y, 1e-3)
        if i % 20 == 0:
            min_old = min(min_old, acc(old))
    return dict(cond=cond, ratio=ratio, base_old=base_old, new=acc(new), old=acc(old), min_old=min_old)

if __name__ == '__main__':
    t0 = time.time()
    rows = []
    for cond, ratio in [('new_only', 0), ('replay_exact', 0.1), ('replay_exact', 0.5), ('self_distill', 0.5)]:
        rs = [run(seed, cond, ratio) for seed in range(3)]
        mean = lambda k: np.mean([x[k] for x in rs])
        print(f"{cond:13s} old_frac={ratio:.1f}  old_before={mean('base_old'):.3f}  new_after={mean('new'):.3f}  "
              f"old_after={mean('old'):.3f}  worst_old_during={mean('min_old'):.3f}")
    print(f"total {time.time()-t0:.1f}s")
