"""Step 13: one table with every pass mark marked pass/fail, plus a plain-language note. Reads graded/*.json (grade.py) and results/*.json (GPU jobs).
  python -m sleep2.askonce.report RESULTS_DIR GRADED_DIR OUT_MD [NIGHTDATA_DIR [TAGGER_REPORT_JSON]]
The pass marks are the prereg's, fixed in advance. With ASKONCE_SCALE < 1 (or a smoke run) the marks are computed but flagged NOT VALID."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paired  # noqa: E402

from .config import jload, jl_read  # noqa: E402

ARMS = ["P", "A+", "B", "B-sft"]
NEW = ("H_new",)
GATE_RATIO = 0.5   # askonce-v2 gate, fixed before running: A+ ask rate on H_new below GATE_RATIO * P's means the shared training still suppresses asking
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


def marks_1_to_4(G, rows, seeds, arm, base="A+"):
    """Pass marks 1-4 for `arm` against `base`. Returns (marks {label: (pass, detail)}, {m1, m2, m3}).
    Wording choices: mark 2's ask rate on fully specified pools H_full + R_full (the prereg names Split R only); mark 3 pools H_know + R_know."""
    r = rows
    m1 = paired.pooled_and_per_seed(*paired_vecs(G, base, arm, seeds, NEW))
    m2 = paired.pooled_and_per_seed(*paired_vecs(G, base, arm, seeds, ("R_new", "R_know", "R_full")))
    m3 = paired.pooled_and_per_seed(*paired_vecs(G, base, arm, seeds, KNOW))
    marks = {}
    marks["1 H new ambiguity: arm >= A+ + 8, p<0.05, positive in both seeds"] = (
        m1["b_minus_a"] >= 8 and m1["p"] < 0.05 and m1["sign_ok_all_seeds"], f"{m1['b_minus_a']:+.1f} pts, p={m1['p']}, per seed {[m1['per_seed'][s]['b_minus_a'] for s in seeds]}")
    marks["2 R overall: arm >= A+ + 3 and ask-rate on fully specified <= A+ + 3"] = (
        m2["b_minus_a"] >= 3 and r[arm]["ask_full"] <= r[base]["ask_full"] + 3, f"{m2['b_minus_a']:+.1f} pts (p={m2['p']}); ask on full {r[arm]['ask_full']:.1f} vs A+ {r[base]['ask_full']:.1f}")
    marks["3 Knowable: arm >= A+ - 2"] = (m3["b_minus_a"] >= -2, f"{m3['b_minus_a']:+.1f} pts")
    marks["4 ARC within 1, recall within 2, general ask <= A+ + 3"] = (
        abs(r[arm]["arc"] - r[base]["arc"]) <= 1 and abs(r[arm]["recall"] - r[base]["recall"]) <= 2 and r[arm]["ask_general"] <= r[base]["ask_general"] + 3,
        f"ARC {r[arm]['arc']:.1f} vs {r[base]['arc']:.1f}; recall {r[arm]['recall']:.1f} vs {r[base]['recall']:.1f}; general ask {r[arm]['ask_general']:.1f} vs {r[base]['ask_general']:.1f}")
    return marks, {"m1": m1, "m2": m2, "m3": m3}


def ask_gate(G, seeds):
    """askonce-v2 gate. INCONCLUSIVE (not refuted) if A+ asks on H_new less than half as often as the untrained model P (v1: P 14/80 = 17.5%)."""
    if not any(k[0] == "P" for k in G):
        return {"status": "unevaluable", "inconclusive": True, "detail": "no P results, so the gate cannot be checked"}
    p_seed = min(s for (x, s) in G if x == "P")
    asks = {a: rate(G, a, seeds if a != "P" else [p_seed], NEW, "ask") for a in ("P", "A+", "B", "B-sft") if any(k[0] == a for k in G)}
    inc = asks["A+"] < GATE_RATIO * asks["P"]
    return {"status": "inconclusive" if inc else "ok", "inconclusive": bool(inc), "ask_rate_h_new": asks, "threshold": GATE_RATIO * asks["P"],
            "detail": f"A+ asks on {asks['A+']:.1f}% of H_new vs P {asks['P']:.1f}% (gate: A+ >= {GATE_RATIO * asks['P']:.1f}%)"}


def night_trajectory(R, arm, seeds):
    """Per-night DPO margin / KL / skipped steps (B shows the margin; every trained arm shows the anchor KL)."""
    return {s: [{"night": n.get("night"), "dpo_margin": n.get("dpo_margin"), "dpo_acc": n.get("dpo_acc"), "anchor_kl": n.get("anchor_kl"), "sft_loss": n.get("sft_loss"),
                 "skipped_steps": n.get("skipped_steps")} for n in R[(arm, s)].get("nights", [])] for s in seeds if (arm, s) in R}


def build(results_dir, graded_dir, agreement=None, nightdata_dir=None, tagger_report=None):
    G, R = load(graded_dir, results_dir)
    need = ("A+", "B")
    for a_ in need:
        if not any(k[0] == a_ for k in G):
            raise SystemExit(f"report: arm {a_} has no graded results (did the job2 deadline skip it?)")
    arms_present = [a for a in ARMS if any(k[0] == a for k in G)]
    trained = [a for a in arms_present if a != "P"]
    seeds = sorted(s for s in {s for (a, s) in G if a == "A+"} if all((a, s) in G and (a, s) in R for a in trained))
    if not seeds:
        raise SystemExit("report: no seed has every trained arm; cannot pair the arms")
    rows = {a: arm_rows(G, R, a, seeds if a != "P" else [min(s for (x, s) in G if x == "P")]) for a in arms_present}
    out = {"rows": rows, "seeds": seeds, "missing_arms": [a for a in ARMS if a not in arms_present]}
    marks, ms = marks_1_to_4(G, rows, seeds, "B")
    m1, m2, m3 = ms["m1"], ms["m2"], ms["m3"]
    if "B-sft" in rows:
        m5 = paired.pooled_and_per_seed(*paired_vecs(G, "B-sft", "B", seeds, NEW))
        mbs = paired.pooled_and_per_seed(*paired_vecs(G, "A+", "B-sft", seeds, NEW))
        marks["5 B >= B-sft + 3 on new ambiguity"] = (m5["b_minus_a"] >= 3, f"{m5['b_minus_a']:+.1f} pts (p={m5['p']})")
        bs_marks, bs_ms = marks_1_to_4(G, rows, seeds, "B-sft")
        out.update(m5=m5, bsft_vs_aplus_new=mbs, bsft_marks={k: {"pass": bool(v[0]), "detail": v[1]} for k, v in bs_marks.items()})
        bsft_ok = all(v[0] for v in bs_marks.values())
    else:
        marks["5 B >= B-sft + 3 on new ambiguity"] = (False, "B-sft was not run")
        bsft_ok = False
    wrong = {"B <= A+ + 3 on new ambiguity": m1["b_minus_a"] <= 3, "B's Split R change < 0": m2["b_minus_a"] < 0, "B more than 5 below A+ on knowable": m3["b_minus_a"] < -5}
    out.update(marks={k: {"pass": bool(v[0]), "detail": v[1]} for k, v in marks.items()}, proves_wrong=wrong, m1=m1, m2=m2, m3=m3)
    out["all_five_marks"] = all(v[0] for v in marks.values())
    # prereg mark 5: "If B-sft also meets marks 1-4, adopt B-sft instead."
    out["adopt"] = "B-sft" if bsft_ok else ("B" if out["all_five_marks"] else "none")
    out["adopt_B"] = out["adopt"] == "B"
    out["diagnostic_A_plus_matches_B"] = bool(abs(m1["b_minus_a"]) < 3 and abs(m2["b_minus_a"]) < 3 and abs(m3["b_minus_a"]) < 3)
    # secondary: slot-clustered bootstrap CI of B - A+ on new ambiguity (clusters = the item's slot)
    cl = {r_["req_id"]: r_["slot"] for r_ in G[("B", seeds[0])]}
    A_, B_ = paired_vecs(G, "A+", "B", seeds, NEW)
    ids = {s_: sorted(set(vec(G, "A+", s_, NEW)) & set(vec(G, "B", s_, NEW))) for s_ in seeds}
    out["m1_cluster_ci"] = paired.cluster_bootstrap_ci([x for s_ in seeds for x in A_[s_]], [x for s_ in seeds for x in B_[s_]], [cl.get(i, i) for s_ in seeds for i in ids[s_]])
    out["gate"] = ask_gate(G, seeds)
    out["verdict"] = "INCONCLUSIVE" if out["gate"]["inconclusive"] else ("ADOPT " + out["adopt"] if out["adopt"] != "none" else "REFUTED")
    out["trajectory"] = {a: night_trajectory(R, a, seeds) for a in trained}
    ke = {a: sum(1 for r_ in G[(a, seeds[0])] if r_["split"] in KNOW and r_["knowable_effective"]) for a in ("B",)}
    out["knowable_effective"] = {"known_items": sum(1 for r_ in G[("B", seeds[0])] if r_["split"] in KNOW), "effective": ke["B"]}
    if nightdata_dir and (Path(nightdata_dir) / "plan.json").exists():
        plan = jload(Path(nightdata_dir) / "plan.json")
        out["slice_share"] = {n: {"B_slice_share": v.get("B_slice_share"), "pairs_in_B": v.get("n_pairs_in_B"), "pairs_available": v.get("n_pairs_available"),
                                  "regret_dropped_memory_has_answer": v.get("n_regret_dropped_memory_has_answer")} for n, v in plan["nights"].items()}
    if tagger_report and Path(tagger_report).exists():
        tr = jload(tagger_report)
        out["tagger"] = tr
        out["label_noise_limited"] = bool(tr.get("label_noise_limited"))
    if agreement:
        out["grader_agreement"] = agreement
    return out


def to_markdown(o, valid=True):
    L = ["# Ask once, then remember: result", ""]
    if not valid:
        L += ["**NOT A VALID TEST RUN** (shrunk world or smoke run): the pass marks below are computed for plumbing checks only.", ""]
    if o.get("missing_arms"):
        L += [f"**Arms missing (not run): {', '.join(o['missing_arms'])}.**", ""]
    g = o.get("gate")
    if g:
        L += [f"**Gate (fixed before the run): {'INCONCLUSIVE, the shared training still suppresses asking, so this is NOT a refutation' if g['inconclusive'] else 'passed'}.** {g['detail']}.", ""]
    L += ["| arm | H new | H know | H full | R all | silent | ask(full) | ask(know) | ask(general) | ARC | recall |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for a, r in o["rows"].items():
        L.append(f"| {a} | " + " | ".join(f"{r[k]:.1f}" for k in ("H_new", "H_know", "H_full", "R_all", "silent", "ask_full", "ask_know", "ask_general", "arc", "recall")) + " |")
    L += ["", "| pass mark (B vs A+) | result | detail |", "|---|---|---|"]
    for k, v in o["marks"].items():
        L.append(f"| {k} | {'PASS' if v['pass'] else 'FAIL'} | {v['detail']} |")
    if o.get("bsft_marks"):
        L += ["", "| marks 1-4 for B-sft (vs A+) | result | detail |", "|---|---|---|"]
        for k, v in o["bsft_marks"].items():
            L.append(f"| {k} | {'PASS' if v['pass'] else 'FAIL'} | {v['detail']} |")
    ci = o.get("m1_cluster_ci")
    if ci:
        L += ["", f"Secondary: slot-clustered bootstrap 95% CI for B - A+ on new ambiguity: [{ci['lo']:+.1f}, {ci['hi']:+.1f}] points ({ci['n_clusters']} slots)."]
    L += ["", "Result that proves the idea wrong (any one): " + "; ".join(f"{k}: {'YES' if v else 'no'}" for k, v in o["proves_wrong"].items()),
          "", f"All five marks hold for B: **{o['all_five_marks']}**. Decision under the prereg rule (B-sft replaces B when it also meets marks 1-4): **adopt {o['adopt']}**. "
          f"Diagnostic (A+ matches B everywhere, so the useful part is the memory, ship it without ask-training): {o['diagnostic_A_plus_matches_B']}."]
    L += ["Adoption on a simulated world is provisional: the Step 0 gate on real logs (at least 5 events per night, tagger precision >= 0.8) must pass before any real-use decision."]
    ke = o.get("knowable_effective")
    if ke:
        L.append(f"Knowable eval items whose slot actually reached the memory (knowable_effective): {ke['effective']} of {ke['known_items']} (marks use all of them).")
    if "label_noise_limited" in o:
        tr = o["tagger"]
        L.append(f"Tagger on the simulated logs: precision {tr['all']['precision']}, recall {tr['all']['recall']}"
                 + (" -> **LABEL-NOISE-LIMITED (precision below 0.8)**; a follow-up on oracle labels is a diagnosis only." if o["label_noise_limited"] else "."))
    ga = o.get("grader_agreement")
    if ga and ga.get("kappa") is not None:
        L.append(f"Grader agreement (Haiku vs Sonnet, {ga['n']} ASKs): kappa {ga['kappa']}{' (SUSPECT, below 0.7)' if ga.get('suspect') else ''}.")
    if o.get("slice_share"):
        L += ["", "B slice share per night (the slice is sized on the median night, so it is not a fixed 15%; it is equal across arms):", "", "| night | B slice share | pairs in B / available | regret dropped (memory had the answer) |", "|---|---|---|---|"]
        for n, v in sorted(o["slice_share"].items(), key=lambda kv: int(kv[0])):
            L.append(f"| {n} | {100 * (v['B_slice_share'] or 0):.1f}% | {v['pairs_in_B']} / {v['pairs_available']} | {v['regret_dropped_memory_has_answer']} |")
    traj = o.get("trajectory", {})
    if traj.get("B"):
        L += ["", "Per-night training trajectory for B (DPO margin should rise, anchor KL should stay small; skipped = fp16 loss-scale skips):", "", "| seed | night | DPO margin | DPO acc | anchor KL | SFT loss | skipped |", "|---|---|---|---|---|---|---|"]
        for s, nl in traj["B"].items():
            for n in nl:
                L.append(f"| {s} | {n['night']} | {n['dpo_margin']} | {n['dpo_acc']} | {n['anchor_kl']} | {n['sft_loss']} | {n['skipped_steps']} |")
    ad = o["adopt"]
    inc = bool(g and g["inconclusive"])
    L += ["", "## In plain language (for Ben)", "",
          "We trained the assistant overnight in a made-up world. One version practised asking a short question when it was about to guess (B), "
          "another version only studied your past answers more (A+), and a third copied the good questions without the practice step (B-sft). The test is whether practising to ask makes it better at spotting a brand-new "
          "'Sam' it has never met, without nagging you on clear requests. "
          + ("The assistant trained on the shared lessons still almost never asked (compared with the untrained one), so the test cannot tell us whether practising to ask helps. That is inconclusive, not a failure of the idea. " if inc else
             f"B cleared all five marks, so B looks promising, but the final call waits for the real-log check. " if ad == "B" else
             "B-sft also cleared marks 1-4, and it is simpler, so the rule says to prefer B-sft over B, but the final call waits for the real-log check. " if ad == "B-sft" else
             "It did not clear the marks, so we do not adopt it. " + ("A+ ties B almost everywhere, so the useful part is just the small note of your past answers: keep that, skip the ask-training. " if o["diagnostic_A_plus_matches_B"] else ""))
          + "This is only a simulated world on one small model, so it says nothing yet about real use."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    res, gr, outp = sys.argv[1:4]
    nd_dir = sys.argv[4] if len(sys.argv) > 4 else None     # optional: night-file dir (plan.json) for the slice shares
    tg_rep = sys.argv[5] if len(sys.argv) > 5 else None     # optional: tagger_report.json for the label-noise flag
    ag = Path(gr) / "grader_agreement.json"
    o = build(res, gr, jload(ag) if ag.exists() else None, nd_dir, tg_rep)
    import os
    sm = any(jload(f).get("smoke") for f in Path(res).glob("*_*.json"))
    valid = float(os.environ.get("ASKONCE_SCALE", "1")) >= 0.999 and not sm
    Path(outp).parent.mkdir(parents=True, exist_ok=True)
    Path(outp).write_text(to_markdown(o, valid))
    Path(outp).with_suffix(".json").write_text(json.dumps(o, indent=1, default=str))
    print(Path(outp).read_text())
