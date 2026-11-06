"""Table + pre-registered verdicts (PREREG-tricks1.md) from out/**/result_*.json. Usage: summarize.py [outdir]"""
import json, random, sys
from pathlib import Path

COLS = ["gsmh", "math", "popqa", "popqa_rare", "popqa_pop"]

def load(root="out"):
    res = {}
    for f in sorted(Path(root).rglob("result_*.json")):
        try:
            res[f.stem[7:]] = json.loads(f.read_text())
        except Exception:
            pass
    return res

def acc(res, arm, s):
    v = res.get(arm, {}).get(s)
    return v["accuracy"] if isinstance(v, dict) else None

def verdicts(res):
    """Returns {P1,P2,P3: (verdict, detail)}; verdict in PASS / WRONG / MIXED / n/a. Accuracies are fractions."""
    g = lambda arm, s: acc(res, arm, s)
    out = {}
    py, pl, bp = g("s_py", "gsmh"), g("s_plain", "gsmh"), g("b_plain", "gsmh")
    if None in (py, pl, bp):
        out["P1"] = ("n/a", "need s_py, s_plain, b_plain on gsmh")
    else:
        v = "PASS" if py >= pl + 0.05 and py >= bp else ("WRONG" if py - pl < 0.02 else "MIXED")
        out["P1"] = (v, f"s_py={py:.3f} s_plain={pl:.3f} (+{100*(py-pl):.1f}pt) b_plain={bp:.3f}")
    w = {s: g("s_wiki", s) for s in ("popqa", "popqa_rare")}; b = {s: g("b_plain", s) for s in ("popqa", "popqa_rare")}
    if None in (*w.values(), *b.values()):
        out["P2"] = ("n/a", "need s_wiki, b_plain on popqa (+rare)")
    else:
        ok = all(w[s] >= b[s] + 0.10 for s in w)
        v = "PASS" if ok else ("WRONG" if w["popqa"] <= b["popqa"] else "MIXED")
        out["P2"] = (v, f"s_wiki all={w['popqa']:.3f} rare={w['popqa_rare']:.3f}; b_plain all={b['popqa']:.3f} rare={b['popqa_rare']:.3f}")
    cands = {a: g(a, "math") for a in ("s_think", "s_vote8") if g(a, "math") is not None}; bm = g("b_plain", "math")
    if not cands or bm is None:
        out["P3"] = ("n/a", "need b_plain and s_think/s_vote8 on math")
    else:
        best = max(cands.values())
        v = "PASS" if best >= bm - 0.03 else ("WRONG" if all(c < bm - 0.10 for c in cands.values()) else "MIXED")
        out["P3"] = (v, " ".join(f"{a}={c:.3f}" for a, c in cands.items()) + f" b_plain={bm:.3f}" + ("" if len(cands) == 2 else " (one arm missing)"))
    return out

def paired_diff_ci(rows_a, rows_b, B=2000):
    """95% bootstrap CI of acc(a)-acc(b) over shared question ids; rows are lists of dicts with id/correct."""
    a = {r["id"]: r["correct"] for r in rows_a}; b = {r["id"]: r["correct"] for r in rows_b}
    ids = sorted(set(a) & set(b))
    if not ids:
        return None
    d = [int(a[i]) - int(b[i]) for i in ids]; rng = random.Random(0); n = len(d)
    xs = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return xs[int(0.025 * B)], xs[int(0.975 * B) - 1]

def read_rows(root, arm, s):
    for f in Path(root).rglob(f"rows_{arm}_{s}.jsonl"):
        return [json.loads(l) for l in f.open()]
    return []

def table(res):
    lines = ["| arm | " + " | ".join(COLS) + " | tok/q | tools/q |", "|" + "---|" * (len(COLS) + 3)]
    for arm, d in res.items():
        cells = []
        for c in COLS:
            v = d.get(c)
            cells.append(f"{100*v['accuracy']:.1f} [{100*v['ci95'][0]:.0f}-{100*v['ci95'][1]:.0f}]" if isinstance(v, dict) and v.get("ci95") and v["ci95"][0] is not None else "-")
        ref = next((d[c] for c in COLS if isinstance(d.get(c), dict)), {})
        lines.append(f"| {arm} | " + " | ".join(cells) + f" | {ref.get('mean_tokens', 0):.0f} | {ref.get('mean_tool_calls', 0):.2f} |")
    return "\n".join(lines)

def report(root="out"):
    res = load(root)
    parts = ["# Tricks-1 results (accuracy %, [95% bootstrap CI])", "", table(res), "", "## Verdicts (pass marks from PREREG-tricks1.md)"]
    for k, (v, d) in verdicts(res).items():
        parts.append(f"- {k}: {v} - {d}")
    for name, (a, b, s) in {"P1 s_py-s_plain gsmh": ("s_py", "s_plain", "gsmh"), "P3 s_think-b_plain math": ("s_think", "b_plain", "math"),
                            "P3 s_vote8-b_plain math": ("s_vote8", "b_plain", "math"), "P2 s_wiki-b_plain popqa": ("s_wiki", "b_plain", "popqa")}.items():
        ci = paired_diff_ci(read_rows(root, a, s), read_rows(root, b, s))
        if ci:
            parts.append(f"- paired diff {name}: [{100*ci[0]:+.1f}, {100*ci[1]:+.1f}] pt" + (" (excludes 0)" if ci[0] > 0 or ci[1] < 0 else " (includes 0 -> 'suggested' only)"))
    return "\n".join(parts)

if __name__ == "__main__":
    print(report(sys.argv[1] if len(sys.argv) > 1 else "out"))
