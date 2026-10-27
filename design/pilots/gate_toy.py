"""Toy check of write-gating rules on a delta-rule matrix memory (pure Python, oracle keys).

Stream = new important facts, repeats of known facts, corrections, unimportant one-offs,
and 'noisy TV' keys whose value is random every time. Compare gating rules.
"""
import math, random, sys

def unit(rng, d):
    v = [rng.gauss(0, 1) for _ in range(d)]
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]

def matvec(W, k):
    return [sum(r[j] * k[j] for j in range(len(k))) for r in W]

def write(W, k, v, beta):
    if beta <= 0:
        return
    Wk = matvec(W, k)
    for i in range(len(W)):
        e = beta * (v[i] - Wk[i])
        row = W[i]
        for j in range(len(k)):
            row[j] += e * k[j]

def decode(W, k, codebook):
    y = matvec(W, k)
    best, bi = -1e9, -1
    for i, c in enumerate(codebook):
        s = sum(a * b for a, b in zip(y, c))
        if s > best:
            best, bi = s, i
    return bi

def run(policy, seed, d, n_old, n_new, n_rep, n_corr, n_unimp, n_tv, tv_reps, budget_p=None):
    rng = random.Random(seed)
    codebook = [unit(rng, d) for _ in range(64)]
    W = [[0.0] * d for _ in range(d)]
    old = [(unit(rng, d), rng.randrange(64)) for _ in range(n_old)]
    for k, vi in old:
        write(W, k, codebook[vi], 1.0)
    truth_old = {i: vi for i, (k, vi) in enumerate(old)}
    events = []  # (key, value_idx, important, tag, id)
    new = [(unit(rng, d), rng.randrange(64)) for _ in range(n_new)]
    for i, (k, vi) in enumerate(new):
        events.append((k, vi, 1, 'new', i))
    corr_ids = rng.sample(range(n_old), n_corr)
    stable = [i for i in range(n_old) if i not in set(corr_ids)]
    for _ in range(n_rep):
        i = rng.choice(stable)
        events.append((old[i][0], old[i][1], 0, 'rep', i))
    for i in corr_ids:
        nv = (old[i][1] + 1 + rng.randrange(63)) % 64
        truth_old[i] = nv
        events.append((old[i][0], nv, 1, 'corr', i))
    unimp = [(unit(rng, d), rng.randrange(64)) for _ in range(n_unimp)]
    for i, (k, vi) in enumerate(unimp):
        events.append((k, vi, 0, 'unimp', i))
    tv = [unit(rng, d) for _ in range(n_tv)]
    for t in range(n_tv):
        for _ in range(tv_reps):
            events.append((tv[t], rng.randrange(64), 0, 'tv', t))
    rng.shuffle(events)
    # corrections must come after nothing in particular; fine.
    surprise_hist = {}  # per-key count of past high-surprise events (label-free noise estimate)
    writes = 0
    tv_writes = 0
    cons = {}
    tau = 0.5
    for k, vi, imp, tag, idx in events:
        v = codebook[vi]
        Wk = matvec(W, k)
        s = math.sqrt(sum((a - b) ** 2 for a, b in zip(v, Wk)))  # residual norm, |v|=1
        key_id = (tag if tag != 'rep' and tag != 'corr' else 'old', idx)
        if policy == 'always':
            beta = 1.0
        elif policy == 'random':
            beta = 1.0 if rng.random() < budget_p else 0.0
        elif policy == 'surprise':
            beta = 1.0 if s > tau else 0.0
        elif policy == 'importance':
            beta = 1.0 if imp else 0.0
        elif policy == 'surprise_x_importance':
            beta = 1.0 if (imp and s > tau) else 0.0
        elif policy == 'surprise_noise_discount':
            n_prev = surprise_hist.get(key_id, 0)
            beta = (1.0 / (1 + 2 * n_prev)) if s > tau else 0.0
            beta = 1.0 if beta >= 0.99 else (beta if beta > 0.2 else 0.0)
        elif policy == 'noise_discount_only':
            n_prev = surprise_hist.get(key_id, 0)
            beta = 1.0 / (1 + 2 * n_prev)
            beta = beta if beta > 0.2 else 0.0
        elif policy == 'noise_discount_plus_importance':
            n_prev = surprise_hist.get(key_id, 0)
            beta = 1.0 if imp else (1.0 / (1 + 2 * n_prev))
            beta = beta if beta > 0.2 else 0.0
        elif policy in ('consistency', 'consistency_plus_importance'):
            # ACh-like expected uncertainty: how often has this key's outcome changed between presentations?
            n_seen, n_changed, last = cons.get(key_id, (0, 0, None))
            u = n_changed / (n_seen + 1.0)
            beta = 1.0 - u
            if policy == 'consistency_plus_importance' and imp:
                beta = 1.0
            beta = beta if beta > 0.34 else 0.0
        elif policy == 'three_factor':
            # beta = importance boost x reliability (1 - expected uncertainty); delta rule supplies the surprise term
            n_seen, n_changed, last = cons.get(key_id, (0, 0, None))
            u = n_changed / max(1.0, n_seen)
            rel = 1.0 - u
            beta = 1.0 if imp else 0.5 * rel
            beta = beta if beta > 0.2 else 0.0
        elif policy == 'importance_plus_repeats':
            beta = 1.0 if (imp or tag == 'rep') else 0.0
        else:
            raise ValueError(policy)
        n_seen, n_changed, last = cons.get(key_id, (0, 0, None))
        cons[key_id] = (n_seen + 1, n_changed + (1 if (last is not None and last != vi) else 0), vi)
        if s > tau:
            surprise_hist[key_id] = surprise_hist.get(key_id, 0) + 1
        if beta > 0:
            writes += 1
            if tag == 'tv':
                tv_writes += 1
        write(W, k, v, beta)
    acc = lambda items: sum(decode(W, k, codebook) == vi for k, vi in items) / max(1, len(items))
    corr_set = set(corr_ids)
    return {
        'new': acc(new),
        'corr': acc([(old[i][0], truth_old[i]) for i in corr_ids]),
        'old_untouched': acc([(old[i][0], truth_old[i]) for i in range(n_old) if i not in corr_set]),
        'unimp': acc(unimp),
        'writes': writes,
        'tv_writes': tv_writes,
        'n_events': len(events),
    }

if __name__ == '__main__':
    d = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    cfg = dict(d=d, n_old=24, n_new=24, n_rep=48, n_corr=12, n_unimp=48, n_tv=6, tv_reps=8)
    seeds = range(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
    policies = ['always', 'surprise', 'importance', 'surprise_x_importance', 'surprise_noise_discount', 'noise_discount_only', 'noise_discount_plus_importance', 'importance_plus_repeats', 'consistency', 'three_factor']
    res = {}
    for p in policies:
        rs = [run(p, s, **cfg) for s in seeds]
        res[p] = {k: sum(r[k] for r in rs) / len(rs) for k in rs[0]}
    # random at matched budget to surprise_x_importance
    p_budget = res['surprise_x_importance']['writes'] / res['always']['n_events']
    rs = [run('random', s, budget_p=p_budget, **cfg) for s in seeds]
    res['random@budget'] = {k: sum(r[k] for r in rs) / len(rs) for k in rs[0]}
    print('config', cfg, 'seeds', len(seeds))
    print(f"{'policy':28s} {'new':>6s} {'corr':>6s} {'oldU':>6s} {'unimp':>6s} {'writes':>7s} {'tvW':>5s}")
    for p, r in res.items():
        print(f"{p:28s} {r['new']:6.2f} {r['corr']:6.2f} {r['old_untouched']:6.2f} {r['unimp']:6.2f} {r['writes']:7.1f} {r['tv_writes']:5.1f}")
