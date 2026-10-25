"""Step 13: one table with every pass mark marked pass/fail, plus a plain-language note. Reads graded/*.json (grade.py) and results/*.json (GPU jobs).
  python -m sleep2.askonce.report RESULTS_DIR GRADED_DIR OUT_MD
The pass marks are the prereg's, fixed in advance. With ASKONCE_SCALE < 1 (or a smoke run) the marks are computed but flagged NOT VALID."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paired  # noqa: E402

from .config import jload, jl_read  # noqa: E402

ARMS = ["P", "A+", "B", "B-sft"]
NEW = ("H_new",)
KNOW = ("H_know", "R_know")
FULL = ("R_full", "H_full")


def load(graded_dir, results_dir):
    G, R = {}, {}
    for f in Path(graded_dir).glob("*.json"):
        if f.stem == "grader_agreement":
            continue
        arm, seed = f.stem.rsplit("_", 1)
        G[(arm, int(seed))] = jload(f)
    for f in Path(results_dir).glob("*_*.json"):
        arm, seed = f.stem.rsplit("_", 1)
        R[(arm, int(seed))] = jload(f)
    return G, R


def vec(G, arm, seed, splits):
    return {r["req_id"]: int(r["right"]) for r in G[(arm, seed)] if r["split"] in splits}


def paired_vecs(G, a, b, seeds, splits):
    A, B = {}, {}
    for s in seeds:
        va, vb = vec(G, a, s, splits), vec(G, b, s, splits)
        ids = sorted(set(va) & set(vb))
        A[s], B[s] = [va[i] for i in ids], [vb[i] for i in ids]
    return A, B


def rate(G, arm, seeds, splits, key="right"):
    xs = [int(r[key]) if key == "right" else int(r["move"] == "ASK") for s in seeds for r in G[(arm, s)] if r["split"] in splits]
    return 100 * sum(xs) / len(xs) if xs else float("nan")


def arm_rows(G, R, arm, seeds):
    r = {"H_new": rate(G, arm, seeds, ("H_new",)), "H_know": rate(G, arm, seeds, ("H_know",)), "H_full": rate(G, arm, seeds, ("H_full",)),
         "R_all": rate(G, arm, seeds, ("R_new", "R_know", "R_full")), "silent": rate(G, arm, seeds, ("silent",)),
         "ask_full": rate(G, arm, seeds, FULL, "ask"), "ask_know": rate(G, arm, seeds, KNOW, "ask")}
    ev = [R[(arm, s)]["eval"] for s in seeds]
    r["ask_general"] = 100 * sum(x["kind"] == "ASK" for e in ev for x in e["general"]) / sum(len(e["general"]) for e in ev)
    r["arc"] = 100 * sum(e["arc"]["acc"] for e in ev) / len(ev)
    r["recall"] = 100 * sum(x["ok"] for e in ev for x in e["facts"]) / sum(len(e["facts"]) for e in ev)
    return r


def build(results_dir, graded_dir, agreement=None):
    G, R = load(graded_dir, results_dir)
    seeds = sorted({s for (a, s) in G if a == "A+"})
    rows = {a: arm_rows(G, R, a, seeds if a != "P" else [min(s for (x, s) in G if x == "P")]) for a in ARMS if any(k[0] == a for k in G)}
    out = {"rows": rows, "seeds": seeds}
    A, B = paired_vecs(G, "A+", "B", seeds, NEW)
    m1 = paired.pooled_and_per_seed(A, B)
    A2, B2 = paired_vecs(G, "A+", "B", seeds, ("R_new", "R_know", "R_full"))
    m2 = paired.pooled_and_per_seed(A2, B2)
    A3, B3 = paired_vecs(G, "A+", "B", seeds, KNOW)
    m3 = paired.pooled_and_per_seed(A3, B3)
    A5, B5 = paired_vecs(G, "B-sft", "B", seeds, NEW)
    m5 = paired.pooled_and_per_seed(A5, B5)
    Bs = paired_vecs(G, "A+", "B-sft", seeds, NEW)
    mbs = paired.pooled_and_per_seed(*Bs)
    r = rows
    marks = {}
    marks["1 H new ambiguity: B >= A+ + 8, p<0.05, positive in both seeds"] = (m1["b_minus_a"] >= 8 and m1["p"] < 0.05 and m1["sign_ok_all_seeds"], f"{m1['b_minus_a']:+.1f} pts, p={m1['p']}, per seed {[m1['per_seed'][s]['b_minus_a'] for s in seeds]}")
    marks["2 R overall: B >= A+ + 3 and ask-rate on fully specified <= A+ + 3"] = (m2["b_minus_a"] >= 3 and r["B"]["ask_full"] <= r["A+"]["ask_full"] + 3, f"{m2['b_minus_a']:+.1f} pts (p={m2['p']}); ask on full B {r['B']['ask_full']:.1f} vs A+ {r['A+']['ask_full']:.1f}")
    marks["3 Knowable: B >= A+ - 2"] = (m3["b_minus_a"] >= -2, f"{m3['b_minus_a']:+.1f} pts")
    marks["4 ARC within 1, recall within 2, general ask <= A+ + 3"] = (abs(r["B"]["arc"] - r["A+"]["arc"]) <= 1 and abs(r["B"]["recall"] - r["A+"]["recall"]) <= 2 and r["B"]["ask_general"] <= r["A+"]["ask_general"] + 3,
                                                                 f"ARC {r['B']['arc']:.1f} vs {r['A+']['arc']:.1f}; recall {r['B']['recall']:.1f} vs {r['A+']['recall']:.1f}; general ask {r['B']['ask_general']:.1f} vs {r['A+']['ask_general']:.1f}")
    marks["5 B >= B-sft + 3 on new ambiguity"] = (m5["b_minus_a"] >= 3, f"{m5['b_minus_a']:+.1f} pts (p={m5['p']})")
    wrong = {"B <= A+ + 3 on new ambiguity": m1["b_minus_a"] <= 3, "B's Split R change < 0": m2["b_minus_a"] < 0, "B more than 5 below A+ on knowable": m3["b_minus_a"] < -5}
    out.update(marks={k: {"pass": bool(v[0]), "detail": v[1]} for k, v in marks.items()}, proves_wrong=wrong, m1=m1, m2=m2, m3=m3, m5=m5, bsft_vs_aplus_new=mbs)
    out["adopt_B"] = all(v[0] for v in marks.values())
    out["diagnostic_A_plus_matches_B"] = bool(abs(m1["b_minus_a"]) < 3 and abs(m2["b_minus_a"]) < 3 and abs(m3["b_minus_a"]) < 3)
    if agreement:
        out["grader_agreement"] = agreement
    return out


def to_markdown(o, valid=True):
    L = ["# Ask once, then remember: result", ""]
    if not valid:
        L += ["**NOT A VALID TEST RUN** (shrunk world or smoke run): the pass marks below are computed for plumbing checks only.", ""]
    L += ["| arm | H new | H know | H full | R all | silent | ask(full) | ask(know) | ask(general) | ARC | recall |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for a, r in o["rows"].items():
        L.append(f"| {a} | " + " | ".join(f"{r[k]:.1f}" for k in ("H_new", "H_know", "H_full", "R_all", "silent", "ask_full", "ask_know", "ask_general", "arc", "recall")) + " |")
    L += ["", "| pass mark | result | detail |", "|---|---|---|"]
    for k, v in o["marks"].items():
        L.append(f"| {k} | {'PASS' if v['pass'] else 'FAIL'} | {v['detail']} |")
    L += ["", "Result that proves the idea wrong (any one): " + "; ".join(f"{k}: {'YES' if v else 'no'}" for k, v in o["proves_wrong"].items()),
          "", f"All five marks hold, so adopt B: **{o['adopt_B']}**. Diagnostic (A+ matches B everywhere, so the useful part is the memory, ship it without ask-training): {o['diagnostic_A_plus_matches_B']}."]
    ga = o.get("grader_agreement")
    if ga and ga.get("kappa") is not None:
        L.append(f"Grader agreement (Haiku vs Sonnet, {ga['n']} ASKs): kappa {ga['kappa']}{' (SUSPECT, below 0.7)' if ga.get('suspect') else ''}.")
    L += ["", "## In plain language (for Ben)", "",
          "We trained the assistant overnight in a made-up world. One version practised asking a short question when it was about to guess (B), "
          "another version only studied your past answers more (A+). The test is whether practising to ask makes it better at spotting a brand-new "
          "'Sam' it has never met, without nagging you on clear requests. " + ("It did, on every pass mark, so B is worth building for real. " if o["adopt_B"] else
          "It did not clear all five marks, so we do not adopt it yet. " + ("A+ ties B almost everywhere, so the useful part is just the small note of your past answers: keep that, skip the ask-training. " if o["diagnostic_A_plus_matches_B"] else ""))
          + "This is only a simulated world on one small model, so it says nothing yet about real use."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    res, gr, outp = sys.argv[1:4]
    ag = Path(gr) / "grader_agreement.json"
    o = build(res, gr, jload(ag) if ag.exists() else None)
    import os
    sm = any(jload(f).get("smoke") for f in Path(res).glob("*_*.json"))
    valid = float(os.environ.get("ASKONCE_SCALE", "1")) >= 0.999 and not sm
    Path(outp).parent.mkdir(parents=True, exist_ok=True)
    Path(outp).write_text(to_markdown(o, valid))
    Path(outp).with_suffix(".json").write_text(json.dumps(o, indent=1, default=str))
    print(Path(outp).read_text())
