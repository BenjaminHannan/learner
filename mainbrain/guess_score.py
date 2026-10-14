"""Score the guesser head of a domain-mode run (mark G1).

Usage:
  python3 -m mainbrain.guess_score --run RUN --out OUT.json [--probe PROBE.json]
  python3 -m mainbrain.guess_score --selftest

Inputs: RUN/guess.jsonl (line K = day K's tries scored by the head BEFORE night K
trains) and RUN/log.jsonl (event "night" with night, quiz_per_kind, quiz_pooled).
Everything is computed over days 2..N (day 1 = untrained head, skipped), except
the walk-forward proxy_logistic which uses day 1 rows as training data.

Judged number: head within-kind AUC pooled over days 2..N. The within-kind AUC
(auc, within_kind_auc) reimplements dopamine/d0_guess.py on branch
claude/project-thread-e6smlm; the six length/digit proxies follow dopamine/d0_diag.py.

Mark G1 verdict rules:
  PASS          if head AUC >= 0.65 AND head Brier < baseline Brier (pooled rows).
  PROVED WRONG  if head AUC < 0.62,
                OR head AUC < probe floor + 0.02 (only when --probe is given;
                   otherwise this part is reported as 'not checked'),
                OR head AUC < length/digit floor + 0.05.
  FAIL          otherwise (not proved wrong).
(PROVED WRONG takes precedence over PASS/FAIL.)
Baseline Brier: each day-K row predicted by its kind's rate in night K-1's
quiz_per_kind (kind missing there -> night K-1 quiz_pooled/100).
"""
import argparse
import json
import os
import re
import sys
import tempfile

import numpy as np

PROXY_NAMES = ["len_chars", "n_digit_runs", "n_digits", "max_number",
               "n_cell_refs", "n_colon_ranges"]


# ---------- AUC (faithful to dopamine/d0_guess.py) ----------
def _avg_ranks(v):
    v = np.asarray(v, dtype=float)
    order = np.argsort(v, kind="mergesort")
    sv = v[order]
    ranks = np.empty(len(v))
    i = 0
    n = len(v)
    while i < n:
        j = i
        while j + 1 < n and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def auc(y, v):
    """Mann-Whitney AUC with average ranks for ties; None if a class is missing."""
    y = np.asarray(y)
    v = np.asarray(v, dtype=float)
    pos = y == 1
    npos = int(pos.sum())
    nneg = len(y) - npos
    if npos == 0 or nneg == 0:
        return None
    r = _avg_ranks(v)
    return float((r[pos].sum() - npos * (npos + 1) / 2.0) / (npos * nneg))


def _groups(y, kind, day, min_each=10):
    """(day, kind) groups with >= min_each positives and negatives: list of (key, idx)."""
    y = np.asarray(y)
    day = np.asarray(day)
    kind = np.asarray([str(k) for k in kind])
    out = []
    for d in sorted(set(day.tolist())):
        for k in sorted(set(kind[day == d].tolist())):
            idx = np.where((day == d) & (kind == k))[0]
            npos = int((y[idx] == 1).sum())
            if npos >= min_each and len(idx) - npos >= min_each:
                out.append(((int(d), k), idx))
    return out


def within_kind_auc(y, v, kind, day, min_each=10):
    """sum_g AUC_g*n_g / sum_g n_g over (day,kind) groups; -> (value|None, groups, rows)."""
    y = np.asarray(y)
    v = np.asarray(v, dtype=float)
    num = den = 0.0
    ng = 0
    for _, idx in _groups(y, kind, day, min_each):
        a = auc(y[idx], v[idx])
        if a is None:
            continue
        num += a * len(idx)
        den += len(idx)
        ng += 1
    return (num / den if den else None), ng, int(den)


# ---------- loading ----------
def load_run(run):
    days = {}
    with open(os.path.join(run, "guess.jsonl")) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            days[int(r["night"])] = r
    nights = {}
    lp = os.path.join(run, "log.jsonl")
    if os.path.exists(lp):
        with open(lp) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("event") == "night" and "night" in e:
                    nights[int(e["night"])] = e
    return days, nights


def proxies(p):
    runs = re.findall(r'\d+', p)
    return [len(p), len(runs), sum(len(r) for r in runs),
            max([float(r) for r in runs], default=0.0),
            len(re.findall(r'[A-Z][0-9]+', p)), p.count(':')]


def baseline_preds(rec, nights):
    prev = nights.get(int(rec["night"]) - 1)
    if prev is None:
        return None
    pk = prev.get("quiz_per_kind") or {}
    pooled = prev.get("quiz_pooled")
    out = []
    for k in rec["kind"]:
        if k in pk:
            out.append(float(pk[k]))
        elif pooled is not None:
            out.append(float(pooled) / 100.0)
        else:
            return None
    return out


# ---------- logistic ----------
def fit_logistic(X, y, C=1.0):
    """min 0.5|w|^2 + C*sum BCE, intercept unpenalised. Returns (w, b)."""
    n, d = X.shape
    try:
        from scipy.optimize import minimize

        def f(t):
            w, b = t[:d], t[d]
            z = X @ w + b
            l = np.sum(np.logaddexp(0, z) - y * z)
            s = 1 / (1 + np.exp(-z))
            g = X.T @ (s - y)
            return 0.5 * w @ w + C * l, np.concatenate([w + C * g, [C * np.sum(s - y)]])
        r = minimize(f, np.zeros(d + 1), jac=True, method="L-BFGS-B")
        return r.x[:d], r.x[d]
    except ImportError:
        pass
    A = np.hstack([X, np.ones((n, 1))])
    t = np.zeros(d + 1)
    reg = np.eye(d + 1)
    reg[d, d] = 0.0

    def loss(t):
        z = A @ t
        return 0.5 * t[:d] @ t[:d] + C * np.sum(np.logaddexp(0, z) - y * z)
    cur = loss(t)
    for _ in range(100):
        z = A @ t
        s = 1 / (1 + np.exp(-z))
        g = reg @ t + C * A.T @ (s - y)
        H = reg + C * (A.T * (s * (1 - s))) @ A + 1e-9 * np.eye(d + 1)
        step = np.linalg.solve(H, g)
        a = 1.0
        while a > 1e-8:
            nt = t - a * step
            nl = loss(nt)
            if nl <= cur:
                break
            a /= 2
        else:
            break
        t, done = nt, abs(cur - nl) < 1e-12
        cur = nl
        if done:
            break
    return t[:d], t[d]


def proxy_logistic(days):
    ds = sorted(days)
    feats = {d: np.log1p(np.array([proxies(p) for p in days[d]["prompt"]], dtype=float))
             for d in ds}
    ys = {d: np.asarray(days[d]["y"], dtype=float) for d in ds}
    ally, allv, allk, alld = [], [], [], []
    for d in ds:
        if d < 2:
            continue
        tr = [e for e in ds if e < d]
        if not tr:
            continue
        Xt = np.vstack([feats[e] for e in tr])
        yt = np.concatenate([ys[e] for e in tr])
        Xd = feats[d]
        if len(yt) == 0:
            continue
        if yt.min() == yt.max():
            pred = np.full(len(Xd), yt[0])
        else:
            mu = Xt.mean(0)
            sd = Xt.std(0)
            sd = np.where(sd < 1e-8, 1.0, sd)
            w, b = fit_logistic((Xt - mu) / sd, yt)
            pred = 1 / (1 + np.exp(-(((Xd - mu) / sd) @ w + b)))
        ally += list(ys[d]); allv += list(pred)
        allk += list(days[d]["kind"]); alld += [d] * len(Xd)
    v, g, n = within_kind_auc(ally, allv, allk, alld)
    return {"auc_within_pooled": v, "groups": g, "rows": n}


# ---------- scoring ----------
def score(run, probe=None):
    days, nights = load_run(run)
    ds = [d for d in sorted(days) if d >= 2]
    Y, P, K, D, PR = [], [], [], [], []
    for d in ds:
        r = days[d]
        n = len(r["y"])
        Y += list(r["y"]); P += list(r["p"]); K += list(r["kind"])
        D += [d] * n; PR += list(r["prompt"])
    Y = np.asarray(Y, dtype=float); P = np.asarray(P, dtype=float); D = np.asarray(D)
    Kn = np.asarray(K)
    # baseline predictions aligned to rows (nan where unavailable)
    B = []
    for d in ds:
        b = baseline_preds(days[d], nights)
        B += b if b is not None else [float("nan")] * len(days[d]["y"])
    B = np.asarray(B, dtype=float)

    out = {"run": run, "days": ds,
           "rows_per_day": {str(d): len(days[d]["y"]) for d in ds},
           "success_per_day": {str(d): (float(np.mean(days[d]["y"])) if len(days[d]["y"]) else None)
                               for d in ds}}

    # head AUC
    v, g, n = within_kind_auc(Y, P, Kn, D)
    per_day, per_day_kind = {}, []
    for d in ds:
        m = D == d
        pv, pg, pn = within_kind_auc(Y[m], P[m], Kn[m], D[m])
        per_day[str(d)] = {"auc": pv, "groups": pg, "rows": pn}
        for k in sorted(set(Kn[m].tolist())):
            mk = m & (Kn == k)
            npos = int((Y[mk] == 1).sum())
            nneg = int(mk.sum()) - npos
            per_day_kind.append({"day": d, "kind": k, "n": int(mk.sum()), "pos": npos,
                                 "neg": nneg, "auc": auc(Y[mk], P[mk]),
                                 "used": npos >= 10 and nneg >= 10})
    vals = [x["auc"] for x in per_day.values() if x["auc"] is not None]
    out["head"] = {"auc_within_pooled": v, "groups": g, "rows": n, "per_day": per_day,
                   "mean_of_days": float(np.mean(vals)) if vals else None,
                   "day2": per_day.get("2"), "per_day_kind": per_day_kind,
                   "auc_all_rows": auc(Y, P)}

    # Brier
    def brier(y, p):
        ok = ~np.isnan(p)
        return float(np.mean((y[ok] - p[ok]) ** 2)) if ok.any() else None
    ing = np.zeros(len(Y), dtype=bool)
    for _, idx in _groups(Y, Kn, D):
        ing[idx] = True
    pdb = {}
    for d in ds:
        m = D == d
        pdb[str(d)] = {"head": brier(Y[m], P[m]), "baseline": brier(Y[m], B[m])}
    bh, bb = brier(Y, P), brier(Y[~np.isnan(B)], B[~np.isnan(B)])
    bh_cmp = brier(Y[~np.isnan(B)], P[~np.isnan(B)])  # same rows as baseline
    out["brier"] = {"head": bh, "baseline": bb, "head_same_rows_as_baseline": bh_cmp,
                    "head_beats_baseline": (bh_cmp < bb) if bb is not None else None,
                    "head_in_groups": brier(Y[ing], P[ing]),
                    "baseline_in_groups": brier(Y[ing], B[ing]),
                    "per_day": pdb}

    # proxies
    feats = np.array([proxies(p) for p in PR], dtype=float).reshape(len(PR), 6)
    raw, sa = {}, {}
    for j, nm in enumerate(PROXY_NAMES):
        wk = within_kind_auc(Y, feats[:, j], Kn, D)[0]
        raw[nm] = wk
        sa[nm] = None if wk is None else max(wk, 1 - wk)
    cand = {k: x for k, x in sa.items() if x is not None}
    bn = max(cand, key=cand.get) if cand else None
    out["proxies"] = {"raw": raw, "sign_agnostic": sa, "best_name": bn,
                      "best": cand[bn] if bn else None}
    out["proxy_logistic"] = proxy_logistic(days)

    # probe
    pr = None
    if probe:
        with open(probe) as f:
            pj = json.load(f)["pooled_days_2_to_N"]
        G = pj["G"]["within_kind_auc"]
        Gr = pj["G_reader"]["within_kind_auc"]
        have = [x for x in (G, Gr) if x is not None]
        pr = {"G": G, "G_reader": Gr, "floor": max(have) if have else None}
    out["probe"] = pr

    # verdict
    reasons = []
    ha, floor_p = v, out["proxies"]["best"]
    wrong = False
    if ha is None:
        reasons.append("head AUC undefined (no usable groups)")
    else:
        if ha < 0.62:
            wrong = True; reasons.append(f"head AUC {ha:.3f} < 0.62")
        if pr is None:
            reasons.append("probe floor: not checked (no --probe)")
        elif pr["floor"] is not None and ha < pr["floor"] + 0.02:
            wrong = True; reasons.append(f"head AUC {ha:.3f} < probe floor {pr['floor']:.3f} + 0.02")
        if floor_p is not None and ha < floor_p + 0.05:
            wrong = True; reasons.append(f"head AUC {ha:.3f} < length/digit floor {floor_p:.3f} ({bn}) + 0.05")
    passed = (ha is not None and ha >= 0.65 and out["brier"]["head_beats_baseline"] is True)
    if wrong:
        verdict = "PROVED WRONG"
    elif passed:
        verdict = "PASS"; reasons.append("AUC >= 0.65 and head Brier < baseline Brier")
    else:
        verdict = "FAIL"
        if ha is not None and ha < 0.65:
            reasons.append(f"head AUC {ha:.3f} < 0.65")
        if out["brier"]["head_beats_baseline"] is not True:
            reasons.append("head Brier not below baseline (or baseline unavailable)")
    out["g1"] = {"verdict": verdict, "reasons": reasons}
    return out


def _f(x):
    return "n/a" if x is None else f"{x:.4f}"


def summarize(o):
    h, b = o["head"], o["brier"]
    L = [f"run {o['run']}  days {o['days']}",
         f"head within-kind AUC pooled {_f(h['auc_within_pooled'])} "
         f"({h['groups']} groups, {h['rows']} rows); mean of days {_f(h['mean_of_days'])}; "
         f"day2 {_f((h['day2'] or {}).get('auc'))}; all-rows AUC {_f(h['auc_all_rows'])}",
         f"Brier head {_f(b['head'])} vs baseline {_f(b['baseline'])} "
         f"(head<baseline: {b['head_beats_baseline']}); in groups {_f(b['head_in_groups'])} vs {_f(b['baseline_in_groups'])}",
         f"length/digit floor {_f(o['proxies']['best'])} ({o['proxies']['best_name']}); "
         f"proxy_logistic {_f(o['proxy_logistic']['auc_within_pooled'])}"]
    if o["probe"]:
        L.append(f"probe floor {_f(o['probe']['floor'])}")
    L.append(f"G1: {o['g1']['verdict']}  -- " + "; ".join(o["g1"]["reasons"]))
    return "\n".join(L)


# ---------- self-test ----------
def selftest():
    # hand example with ties: pos {3,2}, neg {2,1}: pairs 3>2,3>1,2==2(.5),2>1 -> 3.5/4
    assert abs(auc([1, 1, 0, 0], [3, 2, 2, 1]) - 0.875) < 1e-12
    assert auc([1, 1], [1, 2]) is None
    # groups with < 10 of a class dropped
    y = [1] * 12 + [0] * 12 + [1] * 9 + [0] * 15
    kind = ["a"] * 24 + ["b"] * 24
    day = [2] * 48
    v = [1.0] * 12 + [0.0] * 12 + list(np.linspace(0, 1, 24))
    val, g, n = within_kind_auc(y, v, kind, day)
    assert (g, n) == (1, 24) and abs(val - 1.0) < 1e-12, (val, g, n)

    rng = np.random.default_rng(0)
    kinds = ["a", "b", "c"]
    rates = {"a": 0.3, "b": 0.5, "c": 0.7}
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "guess.jsonl"), "w") as gf, \
            open(os.path.join(tmp, "log.jsonl"), "w") as lf:
        for K in range(1, 5):
            ks = [kinds[i % 3] for i in range(200)]
            yy = [int(rng.random() < rates[k]) for k in ks]
            pp = [min(max(0.5 * t + 0.25 + 0.1 * rng.random(), 0), 1) for t in yy]
            prompts = [f"sum A{i}:B{i} of {i * 7}" for i in range(200)]
            gf.write(json.dumps({"night": K, "head_nights_trained": K - 1, "kind": ks,
                                 "y": yy, "p": pp, "prompt": prompts}) + "\n")
            lf.write(json.dumps({"event": "night", "night": K,
                                 "quiz_per_kind": {"a": 0.1 * K, "b": 0.2},
                                 "quiz_pooled": 40.0}) + "\n")
    o = score(tmp)
    assert o["days"] == [2, 3, 4] and o["head"]["groups"] == 9
    assert o["head"]["auc_within_pooled"] > 0.9
    assert o["brier"]["head"] < 0.25
    # baseline uses previous night's rate: day 2 -> night 1: a=0.1, b=0.2, c -> 0.40
    d2 = json.loads(open(os.path.join(tmp, "guess.jsonl")).readlines()[1])
    yy = np.array(d2["y"], float)
    exp = np.mean([(yy[i] - {"a": 0.1, "b": 0.2, "c": 0.4}[k]) ** 2 for i, k in enumerate(d2["kind"])])
    assert abs(o["brier"]["per_day"]["2"]["baseline"] - exp) < 1e-12
    # perfect p -> AUC 1.0 ; constant within kind -> 0.5
    for mode in ("perfect", "const"):
        with open(os.path.join(tmp, "guess.jsonl")) as f:
            recs = [json.loads(l) for l in f]
        for r in recs:
            r["p"] = list(map(float, r["y"])) if mode == "perfect" else [rates[k] for k in r["kind"]]
        t2 = tempfile.mkdtemp()
        with open(os.path.join(t2, "guess.jsonl"), "w") as f:
            f.write("".join(json.dumps(r) + "\n" for r in recs))
        os.replace(os.path.join(tmp, "log.jsonl"), os.path.join(t2, "log.jsonl"))
        os.replace(os.path.join(t2, "log.jsonl"), os.path.join(tmp, "log.jsonl"))
        a = score(t2)["head"]["auc_within_pooled"]
        assert abs(a - (1.0 if mode == "perfect" else 0.5)) < 1e-12, (mode, a)
    print(summarize(o))
    print("selftest OK")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--out")
    ap.add_argument("--probe")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return 0
    if not a.run or not a.out:
        ap.error("--run and --out are required")
    o = score(a.run, a.probe)
    with open(a.out, "w") as f:
        json.dump(o, f, indent=1)
    print(summarize(o))
    return 0


if __name__ == "__main__":
    sys.exit(main())
