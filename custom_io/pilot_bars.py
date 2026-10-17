#!/usr/bin/env python3
"""Mechanical verdicts for paired width-pilot results against a sealed bar spec.  DRAFT for review.  Standard library only.

House rule: every paired bar is sized from its OWN contrast's measured sigma_d, and the verdict is computed mechanically from
the pre-registered bars.  This tool takes paired results and a bar spec and prints the verdict with the numbers that force it.

Usage:
    python3 -m custom_io.pilot_bars RESULTS.json SPEC.json [--out REPORT.json] [--json-only | --summary-only]
    (or: python3 custom_io/pilot_bars.py RESULTS.json SPEC.json)

RESULTS.json  {"contrast": name, "unit": "parent"|"seed", "pairs": [{"unit": "s200", "a": [..], "b": [..]}, ...],
               "extra": {"pass_count": 3, ...}}          # "extra" optional: named scalars usable in rule conditions
  Each unit may carry several replicate values per arm; d_u = mean(b) - mean(a) is formed WITHIN the unit first.  The
  statistic is over units, never replicates: n = number of units, df = n - 1 (no pseudo-replication).

SPEC.json     {"floor_sd": 3.0, "alpha_two_sided": 0.05, "anchors": {...},
               "gate": {"var": "sd_obs", "op": ">", "value": 8.0, "verdict": "GATE_FAIL_EXTEND"},   # optional (dict or list)
               "rules": [{"name": "SIZE_WINS", "conditions": [{"var": "mean", "op": ">=", "value": 8}, ...]}, ...],
               "default": "UNRESOLVED"}
  Variables: mean, sd_obs (sample sd of d_u, ddof 1), s = max(sd_obs, floor_sd), n, half = t(1-alpha/2, n-1) * s / sqrt(n),
  lo = mean - half, hi = mean + half, plus the input's "extra" scalars.  Ops: >=, >, <=, <, ==.  Conditions are data
  (var/op/value), evaluated with a fixed operator table; there is no string evaluation anywhere.
  Order: gate first; then rules in order, first rule whose conditions ALL hold wins; else the spec's "default".
  A condition on a variable that is not available (e.g. an extra that was not passed) does NOT hold; it is flagged
  "missing" in the report; the summary warns when a missing variable sits in the gate or in a rule at or ahead of the
  deciding one (i.e. could have changed the verdict).  "missing_vars_any_rule" lists all of them.
"""
import argparse
import json
import math
import operator
import sys

# ---------------------------------------------------------------- Student t, by hand
# Regularised incomplete beta via the Numerical Recipes continued fraction (modified Lentz), adapted from power_cost.py.


def _betacf(a, b, x):
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 1000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = d if abs(d) > tiny else tiny
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = d if abs(d) > tiny else tiny
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-15:
            return h
    raise ArithmeticError("betacf did not converge (a=%r b=%r x=%r)" % (a, b, x))


def betai(a, b, x):
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    bt = math.exp(lbt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    """P(T <= t) for Student t with df degrees of freedom (df > 0)."""
    if df <= 0:
        raise ValueError("df must be positive")
    if t == 0.0:
        return 0.5
    tail = 0.5 * betai(df / 2.0, 0.5, df / (df + t * t))  # P(T > |t|)
    return 1.0 - tail if t > 0 else tail


def t_quantile(p, df):
    """t such that P(T <= t) = p, for 0 < p < 1, by bisection on the (accurate) upper tail."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    if p == 0.5:
        return 0.0
    if p < 0.5:
        return -t_quantile(1.0 - p, df)
    q = 1.0 - p  # upper-tail mass wanted; compare tails directly to keep precision for p near 1
    tail = lambda t: 0.5 * betai(df / 2.0, 0.5, df / (df + t * t))
    lo, hi = 0.0, 1.0
    while tail(hi) > q:
        hi *= 2.0
        if hi > 1e300:
            raise ArithmeticError("quantile bracket overflow")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if tail(mid) > q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------- statistics
OPS = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt, "==": operator.eq}
BUILTIN_VARS = ("mean", "sd_obs", "s", "n", "half", "lo", "hi")


def _num(x, what):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError("%s must be a finite number, got %r" % (what, x))
    return float(x)


def per_unit(pairs):
    """Per-unit rows with d_u = mean(b) - mean(a); replicates are averaged inside the unit."""
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("'pairs' must be a non-empty list")
    rows, seen = [], set()
    for i, p in enumerate(pairs):
        name = p.get("unit", "u%d" % i)
        if name in seen:
            raise ValueError("duplicate unit %r (replicates of one unit belong in its a/b lists)" % (name,))
        seen.add(name)
        arms = {}
        for k in ("a", "b"):
            v = p.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                v = [v]
            if not isinstance(v, list) or not v:
                raise ValueError("unit %r: arm %r must be a non-empty list" % (name, k))
            arms[k] = [_num(x, "unit %r arm %s value" % (name, k)) for x in v]
        ma = math.fsum(arms["a"]) / len(arms["a"])
        mb = math.fsum(arms["b"]) / len(arms["b"])
        rows.append({"unit": name, "n_rep_a": len(arms["a"]), "n_rep_b": len(arms["b"]), "a": arms["a"], "b": arms["b"],
                     "mean_a": ma, "mean_b": mb, "d": mb - ma})
    return rows


def summarize(ds, floor_sd, alpha):
    """mean, sd_obs, s, n, t, half, lo, hi from the per-unit differences."""
    n = len(ds)
    if n < 2:
        raise ValueError("need at least 2 units for a t interval (got %d)" % n)
    mean = math.fsum(ds) / n
    sd_obs = math.sqrt(math.fsum((d - mean) ** 2 for d in ds) / (n - 1))
    s = max(sd_obs, floor_sd)
    t = t_quantile(1.0 - alpha / 2.0, n - 1)
    half = t * s / math.sqrt(n)
    return {"n": n, "df": n - 1, "mean": mean, "sd_obs": sd_obs, "floor_sd": floor_sd, "s": s,
            "s_source": "floor" if sd_obs < floor_sd else "observed", "alpha_two_sided": alpha, "t": t,
            "half": half, "lo": mean - half, "hi": mean + half}


# ---------------------------------------------------------------- spec
def validate_spec(spec):
    if not isinstance(spec, dict):
        raise ValueError("spec must be a JSON object")
    floor_sd = _num(spec.get("floor_sd"), "spec.floor_sd")
    if floor_sd < 0:
        raise ValueError("floor_sd must be >= 0")
    alpha = _num(spec.get("alpha_two_sided"), "spec.alpha_two_sided")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha_two_sided must be in (0, 1)")
    if not isinstance(spec.get("default"), str) or not spec["default"]:
        raise ValueError("spec.default (verdict when no rule holds) is required")
    rules = spec.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("spec.rules must be a non-empty ordered list")
    names = set()
    for r in rules:
        nm = r.get("name")
        if not isinstance(nm, str) or not nm or nm in names:
            raise ValueError("rule names must be unique non-empty strings (got %r)" % (nm,))
        names.add(nm)
        conds = r.get("conditions")
        if not isinstance(conds, list) or not conds:
            raise ValueError("rule %r needs a non-empty conditions list (an empty one would always fire)" % nm)
        for c in conds:
            _check_cond(c, "rule %r" % nm)
    for g in _gates(spec):
        _check_cond(g, "gate")
        if not isinstance(g.get("verdict"), str) or not g["verdict"]:
            raise ValueError("gate needs a 'verdict' string")
    return floor_sd, alpha


def _gates(spec):
    g = spec.get("gate")
    if g is None:
        return []
    return g if isinstance(g, list) else [g]


def _check_cond(c, where):
    if not isinstance(c, dict) or not isinstance(c.get("var"), str):
        raise ValueError("%s: condition needs a 'var' name: %r" % (where, c))
    if c.get("op") not in OPS:
        raise ValueError("%s: op must be one of %s, got %r" % (where, sorted(OPS), c.get("op")))
    _num(c.get("value"), "%s: condition value" % where)


def eval_cond(c, env):
    """One condition -> dict with the numbers.  held is False (status 'missing') if the variable is unavailable."""
    var, op, value = c["var"], c["op"], float(c["value"])
    if var not in env:
        return {"var": var, "op": op, "value": value, "actual": None, "held": False, "status": "missing"}
    actual = env[var]
    held = bool(OPS[op](actual, value))
    return {"var": var, "op": op, "value": value, "actual": actual, "held": held, "status": "held" if held else "failed"}


# ---------------------------------------------------------------- verdict
def evaluate(data, spec):
    floor_sd, alpha = validate_spec(spec)
    rows = per_unit(data.get("pairs"))
    ds = [r["d"] for r in rows]
    st = summarize(ds, floor_sd, alpha)
    extra = data.get("extra") or {}
    if not isinstance(extra, dict):
        raise ValueError("'extra' must be an object of named scalars")
    env = {k: st[k] for k in BUILTIN_VARS}
    for k, v in extra.items():
        if k in BUILTIN_VARS:
            raise ValueError("extra variable %r collides with a built-in variable" % k)
        env[k] = _num(v, "extra[%r]" % k)

    gates = []
    gate_hit = None
    for g in _gates(spec):
        res = eval_cond(g, env)
        res["verdict"] = g["verdict"]
        gates.append(res)
        if res["held"] and gate_hit is None:
            gate_hit = res

    rule_reports, fired = [], None
    for r in spec["rules"]:
        conds = [eval_cond(c, env) for c in r["conditions"]]
        all_held = all(c["held"] for c in conds)
        rule_reports.append({"name": r["name"], "all_held": all_held, "conditions": conds})
        if all_held and fired is None:
            fired = r["name"]

    if gate_hit is not None:
        verdict, via = gate_hit["verdict"], "gate"
    elif fired is not None:
        verdict, via = fired, "rule"
    else:
        verdict, via = spec["default"], "default"
    # Missing vars matter only if they could have changed the verdict: the gate, and rules ahead of (or at) the decisive one.
    # With a gate verdict nothing after it matters; with the default every rule mattered.
    if via == "gate":
        scope = [gates]
    else:
        upto = [r["name"] for r in rule_reports].index(fired) + 1 if via == "rule" else len(rule_reports)
        scope = [gates] + [r["conditions"] for r in rule_reports[:upto]]
    missing = sorted({c["var"] for blk in scope for c in blk if c["status"] == "missing"})
    missing_all = sorted({c["var"] for blk in ([gates] + [r["conditions"] for r in rule_reports]) for c in blk if c["status"] == "missing"})

    report = {
        "contrast": data.get("contrast"), "unit_kind": data.get("unit"),
        "verdict": verdict, "decided_by": via, "rule_fired": fired if via == "rule" else None,
        "stats": st, "extra": {k: env[k] for k in extra},
        "anchors": spec.get("anchors"),
        "units": [{"unit": r["unit"], "d": r["d"], "mean_a": r["mean_a"], "mean_b": r["mean_b"],
                   "n_rep_a": r["n_rep_a"], "n_rep_b": r["n_rep_b"]} for r in rows],
        "gate": gates, "rules": rule_reports,
        "missing_vars": missing, "missing_vars_any_rule": missing_all,
    }
    report["summary"] = plain_summary(report)
    return _round(report)


def _round(o):
    if isinstance(o, float):
        return round(o, 9)
    if isinstance(o, dict):
        return {k: _round(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_round(v) for v in o]
    return o


def _f(x):
    return "%+.2f" % x


def _g(x):
    return "%+g" % x


def _cond_text(c):
    if c["status"] == "missing":
        return "%s MISSING (%s %s)" % (c["var"], c["op"], _g(c["value"]))
    a = _f(c["actual"]) if c["var"] != "n" else "%d" % c["actual"]
    return "%s %s %s %s" % (c["var"], a, c["op"], _g(c["value"])) if c["status"] == "held" else \
        "%s %s %s %s [FAILS]" % (c["var"], a, c["op"], _g(c["value"]))


def _cond_text_firing(c):
    """Style from the spec example: 'mean +1.10 <= +2' when held; for a held '<' etc. the same op text is used."""
    a = _f(c["actual"]) if c["var"] != "n" else "%d" % c["actual"]
    return "%s %s %s %s" % (c["var"], a, c["op"], _g(c["value"]))


def plain_summary(rep):
    st = rep["stats"]
    units = {"parent": "parents", "seed": "seeds"}.get(rep.get("unit_kind"), "units")
    tail = "n=%d %s; s=%.2f [%s]" % (st["n"], units, st["s"], "floor" if st["s_source"] == "floor" else "observed")
    if rep["decided_by"] == "gate":
        g = next(g for g in rep["gate"] if g["held"])
        body = "GATE " + _cond_text_firing(g)
    elif rep["decided_by"] == "rule":
        r = next(r for r in rep["rules"] if r["name"] == rep["rule_fired"])
        body = "; ".join(_cond_text_firing(c) for c in r["conditions"])
    else:
        parts = []
        for r in rep["rules"]:
            bad = next(c for c in r["conditions"] if not c["held"])
            parts.append("%s: %s" % (r["name"], _cond_text(bad)))
        body = "default, no rule held (%s)" % "; ".join(parts)
    out = "VERDICT: %s (%s; %s)" % (rep["verdict"], body, tail)
    if rep["missing_vars"]:
        out += " WARNING: missing vars %s" % ",".join(rep["missing_vars"])
    return out


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("results")
    ap.add_argument("spec")
    ap.add_argument("--out", help="also write the JSON report to this file")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--json-only", action="store_true")
    g.add_argument("--summary-only", action="store_true")
    args = ap.parse_args(argv)
    with open(args.results) as f:
        data = json.load(f)
    with open(args.spec) as f:
        spec = json.load(f)
    rep = evaluate(data, spec)
    text = json.dumps(rep, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text + "\n")
    if not args.summary_only:
        print(text)
    if not args.json_only:
        print(rep["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
