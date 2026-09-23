#!/usr/bin/env python3
"""Exp 119e STEP 1 — DIAGNOSIS ONLY (open, not registered; Mac CPU; no training).

Question: why is the 119b execute gate shut (ensemble EXECUTED 0 on every 47
panel, tau_exec_ens 0.978 / singles 0.981-0.989)? Director's hypothesis
(ledger P119b.4 risk): the 47 panels' gold labels still use the OLD names
(city/country/birthplace/job) while the remapped model predicts the NEW names,
so confident correct reads score as wrong on CAL and the tau rule pushes the
threshold above everything.

Method: decode the CAL panel (fixed random 1,000-row subset, seed 11990) with
the seed-11911 checkpoint, using the 119 scorer's decode BY IMPORT
(fable_ears119_score.load_model / decode_all; 47 tau rule via
fable_ears47_score.tau0_from_cal). Reports:
  (a) full-CAL count of gold relations in {city, country, birthplace, job};
  (b) among the 50 highest-confidence rows scored WRONG (47 is_correct at
      tau=0, single seed), how many are exactly
      "pred relation == REMAP[gold relation], same act/spans/dir";
  (c) which rows fix tau under the 47 rule (worst-conf wrong-EXECUTED rows),
      under old golds vs remapped golds.
Also prints a few synthetic "city" utterances for the person-city question.

Read-only wrt the checkpoint. Never touches reading94. Never loads test.pt.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears119_score as S119  # noqa: E402  (119 scorer, read-only decode)
import fable_ears47_score as S47  # noqa: E402  (47 tau rule + verdicts)
import fable_ears47_data as D  # noqa: E402
import fable_ears47_encoder as ENC  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OLD_NAMES = {"city", "country", "birthplace", "job"}
REMAP = {
    "country": "located in the administrative territorial entity",
    "city": "located in the administrative territorial entity",
    "birthplace": "place of birth",
    "job": "occupation",
}

# 47 tau rule, quoted: scripts/fable_ears47_score.py:458-477
# tau0_from_cal: "smallest tau0 with 0 wrong EXECUTED writes on CAL" =
#   worst = max conf over rows that EXECUTE at tau 0 with a WRITE act but a
#   non-matching gold; tau0 = math.nextafter(worst, 2.0) (0.0 if none wrong).
# scripts/fable_ears119_score.py:99,103: tau_exec = 1 - (1 - tau0) / 2.


def remapped_gold(gold):
    if gold is None:
        return None
    g = dict(gold)
    if g.get("rel") in REMAP:
        g["rel"] = REMAP[g["rel"]]
    return g


def is_remap_mismatch(pred_fr, gold):
    """True iff pred == gold except pred rel is REMAP[gold rel]."""
    if pred_fr is None or gold is None:
        return False
    if gold.get("rel") not in REMAP:
        return False
    if pred_fr.get("act") != gold.get("act"):
        return False
    if pred_fr.get("rel") != REMAP[gold["rel"]]:
        return False
    return (pred_fr.get("subj") == gold.get("subj")
            and pred_fr.get("obj") == gold.get("obj")
            and pred_fr.get("dir") == gold.get("dir"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True,
                    help="runs dir holding w-11911/ear.pt (read-only)")
    ap.add_argument("--panels47", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=11990)
    ap.add_argument("--batch", type=int, default=32)
    a = ap.parse_args()

    t0 = time.time()
    torch.set_num_threads(1)
    device = torch.device("cpu")

    cal = json.loads((Path(a.panels47) / "cal.json").read_text(encoding="utf-8"))
    n_full = len(cal)
    n_old_full = sum(1 for r in cal if r["gold47"].get("rel") in OLD_NAMES)
    by_rel_full = {}
    for r in cal:
        rel = r["gold47"].get("rel")
        if rel in OLD_NAMES:
            by_rel_full[rel] = by_rel_full.get(rel, 0) + 1

    rng = random.Random(a.seed)
    idx = sorted(rng.sample(range(n_full), min(a.n, n_full)))
    rows = [cal[i] for i in idx]

    model, ck = S119.load_model(Path(a.runs), 11911, a.snapshot, device)
    _, tok, _ = ENC.load(a.snapshot)
    unk_ids = {tok.unk}
    del tok
    # encode with the same tokenizer the scorer path uses
    _, tok2, _ = ENC.load(a.snapshot)
    encs = [D.encode_row(r, tok2) for r in rows]
    assert all(e is not None for e in encs), "CAL rows must all be encodable"
    golds = [S47.gold_frame_of(e) for e in encs]
    parses = S119.decode_all(model, rows, encs, device, unk_ids, batch=a.batch)
    del model
    enc_s = round(time.time() - t0)

    recs = []
    for k in range(len(rows)):
        p = parses[k]
        v, fr = S47.verdict_single(p, 0.0)
        gold = golds[k]
        ok = S47.is_correct(gold, v, fr, None)
        recs.append({"idx": idx[k], "conf": p["conf"], "verdict": v,
                     "gold": gold, "pred": fr, "correct": bool(ok),
                     "mismatch": is_remap_mismatch(fr, gold) if not ok else False})

    wrong = [r for r in recs if not r["correct"]]
    from collections import Counter as _C
    cat = _C()
    for r in wrong:
        g, p = r["gold"], r["pred"]
        if r["mismatch"]:
            cat["remap_mismatch_EXEC" if r["verdict"] == "EXECUTE"
                else "remap_mismatch_other"] += 1
        elif g.get("act") == "UNSURE":
            cat["unsure_gold"] += 1
        elif g.get("rel") in OLD_NAMES:
            cat["old_gold_nonmatch"] += 1
        else:
            cat["other_wrong"] += 1
    wrong_sorted_all = sorted(wrong, key=lambda r: -r["conf"])
    wrong_all = [{"cal_idx": r["idx"], "conf": round(r["conf"], 4),
                  "verdict": r["verdict"],
                  "gold_act": r["gold"]["act"], "gold_rel": r["gold"]["rel"],
                  "pred_act": r["pred"]["act"] if r["pred"] else None,
                  "pred_rel": r["pred"]["rel"] if r["pred"] else None,
                  "mismatch": r["mismatch"]} for r in wrong_sorted_all]
    # top-50 wrong by confidence (EXECUTE-capable rows sort naturally first;
    # abstain rows have conf of p_act but verdict REPHRASE — keep them, flag)
    wrong_sorted = sorted(wrong, key=lambda r: -r["conf"])
    top50 = wrong_sorted[:50]
    n_mismatch_top50 = sum(1 for r in top50 if r["mismatch"])
    n_old_gold_top50 = sum(1 for r in top50 if r["gold"].get("rel") in OLD_NAMES)

    # tau-fixing rows under the 47 rule (single seed, tau=0 EXECUTE + WRITE act
    # + gold mismatch), old golds vs remapped golds
    def tau_rows(gold_list):
        worst = -1.0
        fixers = []
        for k in range(len(rows)):
            p = parses[k]
            v, fr = S47.verdict_single(p, 0.0)
            gold = gold_list[k]
            if v == "EXECUTE" and fr is not None and fr["act"] in S47.WRITE_ACTS \
                    and (gold is None or gold["act"] == "?"
                         or not S47.same_frame(fr, gold)):
                if p["conf"] > worst:
                    worst = p["conf"]
                    fixers = [k]
                elif p["conf"] == worst:
                    fixers.append(k)
        tau0 = 0.0 if worst < 0 else math.nextafter(worst, 2.0)
        return worst, tau0, 1 - (1 - tau0) / 2, fixers

    golds_remap = [remapped_gold(g) for g in golds]
    worst_old, tau0_old, tauex_old, fix_old = tau_rows(golds)
    worst_new, tau0_new, tauex_new, fix_new = tau_rows(golds_remap)
    # cross-check single-seed tau0 against the sealed scorer rule
    tau0_check = S47.tau0_from_cal(golds, [parses], ensemble=False)
    assert tau0_check == tau0_old, (tau0_check, tau0_old)

    def slim(k):
        r = rows[k]
        return {"cal_idx": idx[k], "utterance": D.row_text(r),
                "gold": golds[k], "pred": parses[k]["frame"],
                "conf": parses[k]["conf"]}

    # person-city examples: STATE gold city rows in the subset
    city_ex = [D.row_text(rows[k]) for k in range(len(rows))
               if golds[k].get("rel") == "city" and golds[k].get("act") == "STATE"][:6]

    out = {
        "ckpt": str(Path(a.runs) / "w-11911" / "ear.pt"),
        "subset": {"n": len(rows), "seed": a.seed, "idx": idx},
        "decode_sec": enc_s,
        "cal_full": {"n": n_full, "old_name_gold_rows": n_old_full,
                     "by_rel": by_rel_full},
        "subset_wrong": {"n_wrong": len(wrong), "n_subset": len(rows),
                         "categories": dict(cat), "rows": wrong_all},
        "top50_wrong": {"n": len(top50),
                        "n_remap_mismatch": n_mismatch_top50,
                        "n_old_gold": n_old_gold_top50,
                        "rows": [{"cal_idx": r["idx"], "conf": r["conf"],
                                  "verdict": r["verdict"], "gold": r["gold"],
                                  "pred": r["pred"], "mismatch": r["mismatch"]}
                                 for r in top50]},
        "tau_rule": ("scripts/fable_ears47_score.py:458-477 tau0_from_cal "
                     "(smallest tau0 with 0 wrong EXECUTED writes on CAL) + "
                     "scripts/fable_ears119_score.py:99,103 "
                     "tau_exec = 1-(1-tau0)/2"),
        "tau_old_golds": {"worst": worst_old, "tau0": tau0_old,
                          "tau_exec_single": tauex_old,
                          "n_fixers": len(fix_old),
                          "fixers": [slim(k) for k in fix_old[:5]]},
        "tau_remapped_golds": {"worst": worst_new, "tau0": tau0_new,
                               "tau_exec_single": tauex_new,
                               "n_fixers": len(fix_new),
                               "fixers": [slim(k) for k in fix_new[:5]]},
        "city_state_examples": city_ex,
    }
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    print(json.dumps({
        "cal_full_old": n_old_full, "by_rel": by_rel_full,
        "subset": len(rows), "wrong": len(wrong),
        "top50_mismatch": n_mismatch_top50, "top50_old_gold": n_old_gold_top50,
        "tau_old": [worst_old, tau0_old, tauex_old, len(fix_old)],
        "tau_remap": [worst_new, tau0_new, tauex_new, len(fix_new)],
        "decode_sec": enc_s}, indent=1))


if __name__ == "__main__":
    main()
