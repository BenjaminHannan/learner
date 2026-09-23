#!/usr/bin/env python3
"""Exp 119d — EARS DIAGNOSIS ONLY (Muse, Mac CPU, no training, no sealing).

Loads the registered seed-11901 checkpoint with the exp-119 code by import,
decodes all 400 reading94 sentences UNGATED (one decode per sentence), and
buckets each of the 312 gold triples exactly once (priority order):

  1. act wrong      — predicted frame act is not STATE (NO_FACT / ASK / ...)
  2. relation wrong — normalised relation string differs (confusion pairs kept)
  3. subject span wrong — relation right, subject text differs
       (boundary = token overlap, elsewhere = no shared token)
  4. value span wrong — same split on the object text
  5. below tau — triple fully matches but conf < tau_exec_single (11901)
  6. exact — triple matches and conf >= tau (would EXECUTE correctly)

Also: conf histogram (exact vs non-exact frames), descriptive best-threshold
sweep (diagnosis only — fitting it on reading94 would contaminate the panel
as a test set), NO_FACT writes at that threshold, seed-11901 t_trap silent
wrong writes with brake states, and a frame-level comparison with exp 107.

Usage:
    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
      python -B scripts/fable_ears119d_diagnose.py \
      --runs artifacts/claude-ears119-run-20260922 \
      --snapshot <scibert-snapshot> --out artifacts/fable-ears119d-20260922/diag119d.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D  # noqa: E402
import fable_ears119_data as D119  # noqa: E402  (MAX_LEN = 192 override)
import fable_ears47_encoder as ENC  # noqa: E402
import fable_ears47_model as M  # noqa: E402
import fable_ears47_score as S47  # noqa: E402
import fable_read106_score as R106  # noqa: E402

assert D.MAX_LEN == 192, D.MAX_LEN

REPO = Path(__file__).resolve().parent.parent
PANEL = REPO / "data" / "open" / "reading94" / "panel.jsonl"
PANELS47 = REPO / "artifacts" / "fable-ears47-20260921" / "panels"
TAU_11901 = 0.9601808873527116  # sealed tau_exec_single, taus.json


def toks(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.casefold()))


def span_kind(pred: str, gold: str) -> str:
    if R106.norm(pred) == R106.norm(gold):
        return "same"
    if toks(pred) & toks(gold):
        return "boundary"
    return "elsewhere"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    torch.set_num_threads(1)
    t0 = time.time()

    enc0, tok, _ = ENC.load(a.snapshot)
    del enc0
    unk_ids = {tok.unk}

    ck = torch.load(Path(a.runs) / "w-11901" / "ear.pt", map_location="cpu",
                    weights_only=False)
    enc, _, _ = ENC.load(a.snapshot)
    model = M.FrameEars(enc, D.N_REL, freeze_layers=ck.get("freeze_layers", 0))
    model.load_state_dict(ck["state"])
    model.eval()
    device = torch.device("cpu")

    panel = [json.loads(l) for l in PANEL.read_text(encoding="utf-8").splitlines()]
    assert len(panel) == 400
    gold_sets = [R106.gold_set(r) for r in panel]
    assert sum(len(g) for g in gold_sets) == 312
    assert sum(1 for g in gold_sets if len(g) == 0) == 245

    text_rows = [{"text": r["sentence"],
                  "gold47": {"act": "NO_FACT", "rel": "UNSURE", "subj": None,
                             "obj": None, "dir": 0, "rep": False}}
                 for r in panel]
    encs = [D.encode_row(r, tok) for r in text_rows]
    assert all(e is not None for e in encs)
    P = S47.probs_for_model(model, encs, device, batch=64)
    parses = [S47.decode(text_rows[i], encs[i], P[i], unk_ids)
              for i in range(len(panel))]

    # ---- per-triple buckets (312, priority order) ----
    buckets = Counter()
    subj_split = Counter()
    val_split = Counter()
    conf_pairs = Counter()   # (gold_rel, pred_rel)
    pair_examples: dict[tuple, list] = {}
    act_miss = Counter()     # predicted act when act-wrong
    examples: dict[str, list] = {}
    conf_exact: list[float] = []
    conf_nonexact: list[float] = []

    def ex(key, rec):
        examples.setdefault(key, []).append(rec)
        if len(examples[key]) > 3:
            examples[key] = examples[key][:3]

    for i, row in enumerate(panel):
        fr = parses[i]["frame"]
        conf = float(parses[i].get("conf", 0.0))
        utt = text_rows[i]["text"]
        wt = R106.r2_triple_of(fr, utt, encs[i]["chspans"]) \
            if fr and fr.get("act") == "STATE" else None
        gs = gold_sets[i]
        frame_exact = wt in gs if wt is not None else False
        (conf_exact if frame_exact else conf_nonexact).append(conf)
        for g in gs:
            gr, gsub, gobj = g
            if fr is None or fr.get("act") != "STATE":
                buckets["act wrong"] += 1
                act_miss[fr.get("act") if fr else "?"] += 1
                ex("act wrong", {"id": row["id"], "sentence": row["sentence"],
                                 "pred_act": fr.get("act") if fr else None,
                                 "conf": round(conf, 4),
                                 "gold": list(g)})
            elif (wt is not None and R106.norm(fr.get("rel") or "") != gr):
                buckets["relation wrong"] += 1
                key = (gr, R106.norm(fr.get("rel") or ""))
                conf_pairs[key] += 1
                rec = {"id": row["id"], "sentence": row["sentence"],
                       "pred": list(wt), "conf": round(conf, 4),
                       "gold": list(g)}
                pair_examples.setdefault(key, []).append(rec)
                if len(pair_examples[key]) > 2:
                    pair_examples[key] = pair_examples[key][:2]
                ex("relation wrong", rec)
            elif wt is not None and wt[1] != gsub:
                buckets["subject span wrong"] += 1
                k = span_kind(wt[1], gsub)
                subj_split[k] += 1
                ex("subject span wrong", {"id": row["id"],
                                          "sentence": row["sentence"],
                                          "pred": list(wt), "conf": round(conf, 4),
                                          "gold": list(g), "kind": k})
            elif wt is not None and wt[2] != gobj:
                buckets["value span wrong"] += 1
                k = span_kind(wt[2], gobj)
                val_split[k] += 1
                ex("value span wrong", {"id": row["id"],
                                        "sentence": row["sentence"],
                                        "pred": list(wt), "conf": round(conf, 4),
                                        "gold": list(g), "kind": k})
            elif conf >= TAU_11901:
                buckets["exact"] += 1
            else:
                buckets["below tau"] += 1
                ex("below tau", {"id": row["id"], "sentence": row["sentence"],
                                 "pred": list(wt), "conf": round(conf, 4),
                                 "gold": list(g)})
    assert sum(buckets.values()) == 312, dict(buckets)

    # ---- frame-level M1-style counts (direct exp-107 comparison) ----
    m1 = Counter()
    for i, row in enumerate(panel):
        fr = parses[i]["frame"]
        if fr is None or fr.get("act") != "STATE":
            m1["no STATE frame"] += 1
            continue
        wt = R106.r2_triple_of(fr, text_rows[i]["text"], encs[i]["chspans"])
        gs = gold_sets[i]
        if wt in gs:
            m1["exact_correct"] += 1
        elif len(gs) == 0:
            m1["invented"] += 1
        elif wt[0] in {g[0] for g in gs}:
            m1["relation_right_span_wrong"] += 1
        else:
            m1["wrong_relation"] += 1

    # ---- conf histogram + descriptive best-threshold sweep ----
    def hist(cs):
        bins = [0] * 10
        for c in cs:
            bins[min(int(c * 10), 9)] += 1
        s = sorted(cs)
        med = s[len(s) // 2] if s else 0.0
        return {"n": len(cs), "max": round(max(cs), 4) if cs else 0.0,
                "median": round(med, 4), "bins_0.0_1.0": bins}

    order = sorted(range(len(panel)), key=lambda i: -float(parses[i]["conf"]))
    best = {"at_1pct": {"correct": 0, "wrong": 0, "total": 0, "threshold": None},
            "at_5pct": {"correct": 0, "wrong": 0, "total": 0, "threshold": None}}
    correct = wrong = 0
    for k, i in enumerate(order, 1):
        fr = parses[i]["frame"]
        wt = R106.r2_triple_of(fr, text_rows[i]["text"], encs[i]["chspans"]) \
            if fr and fr.get("act") == "STATE" else None
        hit = wt is not None and wt in gold_sets[i]
        if hit:
            correct += 1
        else:
            wrong += 1
        rate = wrong / k
        c = round(float(parses[i]["conf"]), 6)
        if rate <= 0.01 and correct > best["at_1pct"]["correct"]:
            best["at_1pct"] = {"correct": correct, "wrong": wrong, "total": k,
                               "threshold": c}
        if rate <= 0.05 and correct > best["at_5pct"]["correct"]:
            best["at_5pct"] = {"correct": correct, "wrong": wrong, "total": k,
                               "threshold": c}
    t5 = best["at_5pct"]["threshold"]
    nofact_writes_at_t5 = 0
    nofact_exec_ids = []
    if t5 is not None:
        for i, row in enumerate(panel):
            if len(gold_sets[i]) != 0:
                continue
            v, fr = S47.verdict_single(parses[i], t5)
            if v == "EXECUTE":
                nofact_writes_at_t5 += 1
                if len(nofact_exec_ids) < 5:
                    nofact_exec_ids.append(row["id"])

    # ---- t_trap silent wrong writes, seed 11901 single ----
    trap_rows = json.loads((PANELS47 / "t_trap.json").read_text(encoding="utf-8"))
    trap_encs = [D.encode_row(r, tok) for r in trap_rows]
    trap_golds = [S47.gold_frame_of(e) for e in trap_encs]
    Pt = S47.probs_for_model(model, trap_encs, device, batch=64)
    trap_parses = [S47.decode(trap_rows[i], trap_encs[i], Pt[i], unk_ids)
                   if trap_encs[i] is not None and Pt[i] is not None else None
                   for i in range(len(trap_rows))]
    silent = []
    exec_wrong_ens_tau = []  # 11901 EXECUTE-wrong at the ENSEMBLE tau (0.819):
    # the registered 5 ensemble silent writes must be a subset of rows where
    # every seed voted the same wrong frame, so this list bounds them.
    TAU_ENS = 0.8193305923655743
    for i, r in enumerate(trap_rows):
        p = trap_parses[i]
        if p is None:
            continue
        gold = trap_golds[i]
        for tau_use, store in ((TAU_11901, None), (TAU_ENS, exec_wrong_ens_tau)):
            v, fr = S47.verdict_single(p, tau_use)
            if v == "EXECUTE" and fr is not None and fr["act"] in S47.WRITE_ACTS \
                    and (gold is None or gold["act"] == "?"
                         or not S47.same_frame(fr, gold)):
                utt = D.row_text(r)
                wt = R106.r2_triple_of(fr, utt, trap_encs[i]["chspans"]) \
                    if trap_encs[i] is not None else None
                rec = {"utterance": utt, "family": r.get("family"),
                       "pred_frame": {k: (list(v2) if isinstance(v2, tuple)
                                          else v2)
                                      for k, v2 in fr.items()},
                       "pred_triple": list(wt) if wt else None,
                       "gold": gold,
                       "conf": round(float(p["conf"]), 6),
                       "ok4": bool(p["ok4"]), "ok5": bool(p["ok5"]),
                       "forced_echo": bool(p["forced_echo"]),
                       "reason": p.get("reason", ""),
                       "flags": [round(float(x), 4) for x in p["flags"]]
                       if p["flags"] is not None else None}
                if store is None:
                    silent.append(rec)
                else:
                    store.append(rec)

    out = {
        "exp": "119d", "seed": 11901, "tau_exec_single": TAU_11901,
        "buckets_312": dict(buckets),
        "subject_span_split": dict(subj_split),
        "value_span_split": dict(val_split),
        "act_miss_acts": dict(act_miss),
        "top_relation_confusions": [
            {"gold": g, "pred": p, "count": c,
             "examples": pair_examples.get((g, p), [])}
            for (g, p), c in conf_pairs.most_common(10)],
        "n_confusion_pairs": len(conf_pairs),
        "frame_level_M1": dict(m1),
        "exp107_frame_level": {
            "4701": {"raw_STATE": 276, "exact": 9, "rel_right_span_wrong": 28,
                     "wrong_relation": 110, "invented": 124},
            "4702": {"raw_STATE": 306, "exact": 11, "rel_right_span_wrong": 33,
                     "wrong_relation": 112, "invented": 155},
            "4703": {"raw_STATE": 288, "exact": 10, "rel_right_span_wrong": 33,
                     "wrong_relation": 108, "invented": 139}},
        "conf_hist_exact_frames": hist(conf_exact),
        "conf_hist_nonexact_frames": hist(conf_nonexact),
        "best_threshold_descriptive": best,
        "nofact_writes_at_t5": nofact_writes_at_t5,
        "nofact_exec_id_sample": nofact_exec_ids,
        "t_trap_n": len(trap_rows),
        "t_trap_silent_single11901": len(silent),
        "t_trap_silent_detail": silent[:5],
        "t_trap_execwrong_at_ens_tau": len(exec_wrong_ens_tau),
        "t_trap_execwrong_at_ens_tau_detail": exec_wrong_ens_tau[:12],
        "examples": examples,
        "elapsed_s": round(time.time() - t0, 1),
    }
    op = Path(a.out)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in (
        "buckets_312", "subject_span_split", "value_span_split",
        "act_miss_acts", "frame_level_M1", "best_threshold_descriptive",
        "nofact_writes_at_t5", "t_trap_silent_single11901",
        "elapsed_s")}, indent=1))


if __name__ == "__main__":
    main()
