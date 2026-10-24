"""Advantage baselines: group mean (GRPO), none (REINFORCE), learned per-scenario value, self (model's own prediction)."""
import re


def parse_pct(text):
    """First integer in text, clamped to 0..100, as a fraction; None if there is none."""
    m = re.search(r"\d+", text or "")
    return None if m is None else min(100, int(m.group())) / 100


def pearson(x, y):
    """Pearson correlation; None if either variance is 0 (or fewer than 2 points)."""
    n = len(x)
    if n < 2:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sxx, syy = sum((a - mx) ** 2 for a in x), sum((b - my) ** 2 for b in y)
    if sxx <= 1e-12 or syy <= 1e-12:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sxx * syy) ** 0.5


def advantages(r, G):
    out = []
    for i in range(0, len(r), G):
        g = r[i:i + G]
        m = sum(g) / len(g)
        out += [x - m for x in g]
    return out


def baseline_adv(r, scen, G, mode, V, v_lr, pred=None):
    """Returns (A, V). value: A uses V from before this call; V then updated per episode in order."""
    if mode == "group":
        return advantages(r, G), V
    if mode == "none":
        return list(r), V
    if mode == "batch":  # REINFORCE++/SPO-style: mean of this step's tries, no task labels
        m = sum(r) / len(r)
        return [x - m for x in r], V
    if mode == "self":
        return [x - p for x, p in zip(r, pred)], V
    V = dict(V)
    A = [x - V[s] for x, s in zip(r, scen)]
    for x, s in zip(r, scen):
        V[s] += v_lr * (x - V[s])
    return A, V
