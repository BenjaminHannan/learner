"""Advantage baselines: group mean (GRPO), none (REINFORCE), learned per-scenario value."""


def advantages(r, G):
    out = []
    for i in range(0, len(r), G):
        g = r[i:i + G]
        m = sum(g) / len(g)
        out += [x - m for x in g]
    return out


def baseline_adv(r, scen, G, mode, V, v_lr):
    """Returns (A, V). value: A uses V from before this call; V then updated per episode in order."""
    if mode == "group":
        return advantages(r, G), V
    if mode == "none":
        return list(r), V
    V = dict(V)
    A = [x - V[s] for x, s in zip(r, scen)]
    for x, s in zip(r, scen):
        V[s] += v_lr * (x - V[s])
    return A, V
