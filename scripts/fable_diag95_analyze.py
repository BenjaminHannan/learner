#!/usr/bin/env python3
"""Exp 95 analysis (numpy-free stdlib only). Reads fable_diag95_rows.json + sealed
report.json, reproduces sealed verdicts, and emits every integer table for doc 95.

  uv run --offline --no-project --python 3.12 --with numpy python -B \
    scripts/fable_diag95_analyze.py --rows artifacts/fable-diag95-20260921/fable_diag95_rows.json \
    --out artifacts/fable-diag95-20260921/fable_diag95_tables.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_score as S  # noqa: E402 (sealed verdict logic, read-only)

TAU_EXEC = 0.8766039311885834
TAU0_SEALED = 0.7532078623771669
WRITE_ACTS = {"STATE", "RETRACT"}
BINS = [0.0, 0.3, 0.5, 0.65, 0.75, 0.85, TAU_EXEC, 1.0001]


def parse_of(r, s):
    d = r["seeds"][s]
    f = d["frame"]
    fr = {"act": f["act"], "rel": f["rel"],
          "subj": tuple(f["subj"]) if f["subj"] else None,
          "obj": tuple(f["obj"]) if f["obj"] else None, "dir": f["dir"]}
    return {"frame": fr, "conf": d["conf"], "ok4": d["ok4"], "ok5": d["ok5"],
            "forced_echo": d["forced_echo"]}


def gold_of(r):
    g = r["gold"]
    return {"act": g["act"], "rel": g["rel"],
            "subj": tuple(g["subj"]) if g["subj"] else None,
            "obj": tuple(g["obj"]) if g["obj"] else None, "dir": g["dir"]}


def binom_tail_leq(k, m, a):
    # P(X <= k | m, a), exact
    if k >= m:
        return 1.0
    s = 0.0
    for i in range(0, k + 1):
        s += math.comb(m, i) * (a ** i) * ((1.0 - a) ** (m - i))
    return min(1.0, s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    D = json.loads(Path(a.rows).read_text(encoding="utf-8"))
    sealed = json.loads(Path(
        "artifacts/fable-ears47-20260921/runs/report.json").read_text(
        encoding="utf-8"))
    T = {"TAU_EXEC_used": TAU_EXEC}

    # ---- 0. verify reproduction of sealed verdicts at sealed tau
    repro = {}
    for pname, pd in D["panels"].items():
        rows = pd["rows"]
        exe = cor = sil = 0
        for r in rows:
            ps = [parse_of(r, s) for s in range(3)]
            v, fr = S.verdict_ensemble(ps, TAU_EXEC)
            g = gold_of(r)
            exe += v == "EXECUTE"
            cor += S.is_correct(g, v, fr, ps)
            wrote = v == "EXECUTE" and fr is not None and fr["act"] in WRITE_ACTS
            if wrote and not S.same_frame(fr, g):
                sil += 1
        se = sealed["panels"].get(pname, {}).get("ensemble")
        repro[pname] = {"exec_cpu": exe, "correct_cpu": cor, "silent_cpu": sil}
        if se is not None:
            repro[pname].update({"exec_sealed": se["executed"],
                                 "correct_sealed": se["correct"],
                                 "silent_sealed": se["silent_wrong_write"]})
    T["repro_vs_sealed"] = repro

    # ---- 1. WEB: wpos rows 1..10 per-seed top act/rel/conf
    w10 = []
    for r in D["panels"]["wpos"]["rows"][:10]:
        w10.append({"n": r["n"], "text": r["text"][:160],
                    "gold_rel": r["gold"]["rel"], "relation": r["relation"],
                    "seeds": [{"act": r["seeds"][s]["frame"]["act"],
                               "rel": r["seeds"][s]["frame"]["rel"],
                               "conf": round(r["seeds"][s]["conf"], 4),
                               "ok4": r["seeds"][s]["ok4"],
                               "ok5": r["seeds"][s]["ok5"],
                               "forced": r["seeds"][s]["forced_echo"]}
                              for s in range(3)]})
    T["wpos_first10"] = w10
    # wpos verdict mix at sealed tau (all seeds): act mix of top predictions
    from collections import Counter
    actmix = Counter()
    for r in D["panels"]["wpos"]["rows"]:
        for s in range(3):
            actmix[r["seeds"][s]["frame"]["act"]] += 1
    T["wpos_topact_mix_all_seeds"] = dict(actmix)

    # ---- 2. EXEC: SEEN/NEW STATE-gold non-executed histogram + disagreement
    for pname in ("t_seen", "t_new"):
        rows = D["panels"][pname]["rows"]
        state_rows = [r for r in rows if r["gold"]["act"] == "STATE"]
        nonex = []
        for r in state_rows:
            ps = [parse_of(r, s) for s in range(3)]
            v, _ = S.verdict_ensemble(ps, TAU_EXEC)
            if v != "EXECUTE":
                conf = min(p["conf"] for p in ps)
                agree = all(S.same_frame(ps[0]["frame"], p["frame"])
                            for p in ps[1:])
                nonex.append({"conf": conf, "verdict": v, "agree": agree})
        hist = [0] * (len(BINS) - 1)
        for e in nonex:
            for b in range(len(BINS) - 1):
                if BINS[b] <= e["conf"] < BINS[b + 1]:
                    hist[b] += 1
                    break
        T[f"{pname}_state_nonexec_hist"] = {
            "bins": ["[0,.3)", "[.3,.5)", "[.5,.65)", "[.65,.75)",
                     "[.75,.85)", "[.85,tau)", "[tau,1]"],
            "counts": hist, "n_state": len(state_rows), "n_nonexec": len(nonex),
            "verdicts": dict(Counter(e["verdict"] for e in nonex)),
            "disagree": sum(1 for e in nonex if not e["agree"]),
            "agree": sum(1 for e in nonex if e["agree"])}

    # ---- 2b. LTT candidate grid on CAL (exp-76 style), apply everywhere
    cal = D["panels"]["cal"]["rows"]
    cands = []  # (conf, row_idx, wrong_at_0)
    for i, r in enumerate(cal):
        ps = [parse_of(r, s) for s in range(3)]
        v, fr = S.verdict_ensemble(ps, 0.0)
        if v == "EXECUTE":
            g = gold_of(r)
            wrong = not S.same_frame(fr, g)
            cands.append((min(p["conf"] for p in ps), i, wrong))
    cands.sort(reverse=True)
    N = len(cands)
    T["ltt_cal"] = {"n_cand": N, "n_cal": len(cal),
                    "cand_errors_at_0": sum(1 for _, _, w in cands if w)}
    ALPHA, DELTA = 0.02, 0.10
    if N < 114:
        T["ltt_note"] = "N_cand < 114: single-point grid, no certificate claimed"
    lo = min(114, N)
    counts = sorted(set(int(round(x)) for x in
                        [lo + (N - lo) * t / 14 for t in range(15)]))
    grid = []
    that = None
    for m in counts:
        tau = cands[m - 1][0]
        k = sum(1 for _, _, w in cands[:m] if w)
        p = binom_tail_leq(k, m, ALPHA)
        accept = p <= DELTA
        grid.append({"m": m, "tau": tau, "k": k, "p": p, "accept": accept})
        if accept:
            that = tau
        else:
            break
    T["ltt_grid"] = grid
    T["ltt_tauhat"] = that
    if that is not None:
        per_panel = {}
        for pname, pd in D["panels"].items():
            if pname == "cal":
                continue
            exe = sil = exact = 0
            for r in pd["rows"]:
                ps = [parse_of(r, s) for s in range(3)]
                v, fr = S.verdict_ensemble(ps, that)
                g = gold_of(r)
                if v == "EXECUTE":
                    exe += 1
                    if fr is not None and fr["act"] in WRITE_ACTS and \
                            not S.same_frame(fr, g):
                        sil += 1
                    if S.same_frame(fr, g):
                        exact += 1
            se = sealed["panels"][pname]["ensemble"]
            per_panel[pname] = {"exec_at_tauhat": exe, "exact_at_tauhat": exact,
                                "silent_at_tauhat": sil,
                                "silent_at_sealed": se["silent_wrong_write"],
                                "new_silent": sil - se["silent_wrong_write"],
                                "exec_at_sealed": se["executed"]}
        T["ltt_apply"] = per_panel

    # ---- 3. SAFE: find the 2 trap sentences, per-seed outputs
    targets = ["Fertelovic aside, Migos's training data is dogs.",
               "quick one: lisvannov aside, yalque's car is nimes."]
    safe = []
    for t in targets:
        hit = [r for r in D["panels"]["t_trap"]["rows"] if r["text"] == t]
        assert len(hit) == 1, (t, len(hit))
        r = hit[0]
        ps = [parse_of(r, s) for s in range(3)]
        v, fr = S.verdict_ensemble(ps, TAU_EXEC)
        safe.append({"n": r["n"], "family": r["family"], "text": r["text"],
                     "gold": r["gold"], "verdict": v,
                     "ensemble_frame": {"act": fr["act"], "rel": fr["rel"],
                                        "subj": list(fr["subj"]) if fr["subj"] else None,
                                        "obj": list(fr["obj"]) if fr["obj"] else None,
                                        "dir": fr["dir"]} if fr else None,
                     "ensemble_conf": min(p["conf"] for p in ps),
                     "seeds": [{"frame": r["seeds"][s]["frame"],
                                "conf": r["seeds"][s]["conf"],
                                "ok4": r["seeds"][s]["ok4"],
                                "ok5": r["seeds"][s]["ok5"],
                                "forced": r["seeds"][s]["forced_echo"],
                                "reason": r["seeds"][s]["reason"]}
                               for s in range(3)]})
    T["safe2"] = safe

    # ---- 4. TAU drivers: per-seed tau0 recompute + worst rows + ECE on CAL
    cal_ps_per_seed = []
    for s in range(3):
        cal_ps_per_seed.append([parse_of(r, s) for r in cal])
    cal_golds = [gold_of(r) for r in cal]
    T["tau0_recompute"] = {
        "ensemble": S.tau0_from_cal(cal_golds,
                                    [[parse_of(r, s) for r in cal]
                                     for s in range(3)], ensemble=True),
        "singles": [S.tau0_from_cal(cal_golds, [cal_ps_per_seed[s]],
                                    ensemble=False) for s in range(3)]}
    # worst wrong-write rows per seed (single verdict at 0) and ensemble
    def worst_rows(ps_list, ensemble):
        worst = []
        for k, g in enumerate(cal_golds):
            if ensemble:
                ps = [parse_of(cal[k], s) for s in range(3)]
                v, fr = S.verdict_ensemble(ps, 0.0)
                conf = min(p["conf"] for p in ps)
            else:
                ps = [ps_list[k]]
                v, fr = S.verdict_single(ps[0], 0.0)
                conf = ps[0]["conf"]
            if v == "EXECUTE" and fr is not None and fr["act"] in WRITE_ACTS \
                    and not S.same_frame(fr, g):
                worst.append({"conf": conf, "n": cal[k]["n"],
                              "family": cal[k]["family"],
                              "text": cal[k]["text"][:120]})
        worst.sort(key=lambda d: -d["conf"])
        return worst
    ens_worst = worst_rows(None, True)
    T["cal_worst_ensemble"] = {"n_wrong_at_0": len(ens_worst),
                               "top3": ens_worst[:3]}
    T["cal_worst_singles"] = [
        {"seed": 4701 + s, "n_wrong_at_0": len(worst_rows(cal_ps_per_seed[s], False)),
         "top3": worst_rows(cal_ps_per_seed[s], False)[:3]} for s in range(3)]
    # ECE per seed on CAL single-seed write-candidates at tau=0
    ece = []
    for s in range(3):
        cand = []
        for k, g in enumerate(cal_golds):
            p = cal_ps_per_seed[s][k]
            v, fr = S.verdict_single(p, 0.0)
            if v == "EXECUTE":
                cand.append((p["conf"], S.same_frame(fr, g)))
        nb = 10
        tot = 0.0
        bins = []
        for b in range(nb):
            lo_, hi_ = b / nb, (b + 1) / nb
            inb = [(c, ok) for c, ok in cand
                   if (c >= lo_ and (c < hi_ or (b == nb - 1 and c <= hi_)))]
            if inb:
                acc = sum(1 for _, ok in inb) / len(inb)
                mc = sum(c for c, _ in inb) / len(inb)
                tot += abs(acc - mc) * len(inb) / max(len(cand), 1)
                bins.append({"bin": [lo_, hi_], "n": len(inb),
                             "acc": round(acc, 4), "meanconf": round(mc, 4)})
            else:
                bins.append({"bin": [lo_, hi_], "n": 0, "acc": None,
                             "meanconf": None})
        ece.append({"seed": 4701 + s, "n_cand": len(cand),
                    "ece": round(tot, 4), "bins": bins})
    T["ece_cal_singles"] = ece

    Path(a.out).write_text(json.dumps(T, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, (dict, list)) else "...")
                      for k, v in T.items()}, indent=1))
    print("WROTE", a.out)


if __name__ == "__main__":
    main()
