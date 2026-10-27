#!/usr/bin/env python3
"""Exp 109 — WebRED calibration + reading94 panel scoring (Muse PREP).

    python fable_ears109_score.py --calibrate --runs <runs> --cal calwebred.json \\
        --snapshot <scibert> --out taus.json
    python fable_ears109_score.py --score-panel --runs <runs> --taus taus.json \\
        --snapshot <scibert> --alias relation_aliases.json --out report109.json

--calibrate (per seed, WebRED-dev split only, disjoint from training): decode
every cal row; candidate writes = frame act in {STATE,RETRACT} with brakes
ok4+ok5 passing and no forced echo (mirrors verdict_single minus tau). Gold
triple for positives = (relation, subj span text, obj span text) from char
spans under the 106 normaliser; negatives have empty gold. Rank candidates by
confidence desc; for each prefix k compute wrong-rate = wrong/k. Operating
point = the prefix with wrong-rate <= 0.05 and the most correct writes (ties
-> larger k); tau_op = that prefix's minimum confidence (conf >= tau_op
writes). No prefix qualifies, or zero candidates -> tau_op = +inf (writes
nothing). Calibrated BEFORE the panel is ever scored.

--score-panel (held-out reading94, once per seed, never averaged):
  R1 raw exact-correct frames (ungated single decode, 106 triple match) >= 94.
  R2 EXECUTE writes on the 245 NO_FACT sentences (seed tau_op) <= 25.
  R3 at seed tau_op: panel wrong writes <= 5% of writes AND >= 30 correct.
  R4 exp-47 t_seen/t_new single-seed `correct` (same is_correct definition, at
     the seed's own tau_op) drops by <= 5 points vs the sealed 47 numbers.
  Alias view (secondary, UNREGISTERED): same as R1/R3 with the predicted
  relation mapped through the sealed alias table first.

Additive only: everything else imported read-only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D  # noqa: E402
import fable_ears47_encoder as ENC  # noqa: E402
import fable_ears47_model as M  # noqa: E402
import fable_ears47_score as S47  # noqa: E402
import fable_read106_score as R106  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
PANEL = REPO / "data" / "open" / "reading94" / "panel.jsonl"
SEEDS109 = (10901, 10902, 10903)
N_GOLD = 312
# sealed exp-47 single-seed `correct` (runs/report.json), positional map
# 10901->4701, 10902->4702, 10903->4703.
BASE47 = {"t_seen": {10901: 1953, 10902: 1956, 10903: 1954},
          "t_new": {10901: 2658, 10902: 2645, 10903: 2680}}


def load_model(runs: Path, seed: int, snapshot: str, device):
    ck = torch.load(runs / f"w-{seed}" / "ear.pt", map_location="cpu",
                    weights_only=False)
    enc, _, _ = ENC.load(snapshot)
    m = M.FrameEars(enc, D.N_REL, freeze_layers=ck.get("freeze_layers", 0))
    m.load_state_dict(ck["state"])
    return m.eval().to(device), ck


def cal_gold_triple(row: dict):
    """WebRED-dev row -> gold triple set (106 normaliser) or empty set."""
    if not row["positive"]:
        return set()
    t = row["text"]
    s = R106.norm(t[row["subj_chars"][0]:row["subj_chars"][1]])
    o = R106.norm(t[row["obj_chars"][0]:row["obj_chars"][1]])
    return {(R106.norm(row["relation"]), s, o)}


def cal_triple_of(frame, utt, chspans):
    return R106.r2_triple_of(frame, utt, chspans)


def calibrate(runs: Path, cal_path: Path, snapshot: str, out: Path,
              device) -> dict:
    cal_rows = json.loads(cal_path.read_text(encoding="utf-8"))
    enc0, tok, _ = ENC.load(snapshot)
    del enc0
    unk_ids = {tok.unk}
    golds = [cal_gold_triple(r) for r in cal_rows]
    text_rows = [{"text": r["text"],
                  "gold47": {"act": "NO_FACT", "rel": "UNSURE", "subj": None,
                             "obj": None, "dir": 0, "rep": False}}
                 for r in cal_rows]
    encs = [D.encode_row(r, tok) for r in text_rows]
    assert all(e is not None for e in encs), "dummy-gold encode must not drop"
    res = {"seeds": {}, "cal_n": len(cal_rows)}
    for s in SEEDS109:
        model, _ = load_model(runs, s, snapshot, device)
        P = S47.probs_for_model(model, encs, device, batch=64)
        parses = [S47.decode(text_rows[i], encs[i], P[i], unk_ids)
                  for i in range(len(cal_rows))]
        cands = []
        for i in range(len(cal_rows)):
            p = parses[i]
            fr = p["frame"]
            if fr is None or fr.get("act") not in S47.WRITE_ACTS:
                continue
            if not (p["ok4"] and p["ok5"]) or p["forced_echo"]:
                continue
            wt = cal_triple_of(fr, text_rows[i]["text"], encs[i]["chspans"])
            if wt is None:
                continue
            cands.append({"conf": float(p["conf"]),
                          "correct": wt in golds[i]})
        cands.sort(key=lambda c: -c["conf"])
        best = {"correct": 0, "wrong": 0, "total": 0, "tau_op": float("inf")}
        correct = wrong = 0
        for k, c in enumerate(cands, 1):
            if c["correct"]:
                correct += 1
            else:
                wrong += 1
            if wrong / k <= 0.05 and (
                    correct > best["correct"]
                    or (correct == best["correct"] and k > best["total"])):
                best = {"correct": correct, "wrong": wrong, "total": k,
                        "tau_op": c["conf"]}
        res["seeds"][str(s)] = {
            "seed": s, "n_candidates": len(cands),
            "tau_op": best["tau_op"],
            "cal_correct_at_op": best["correct"],
            "cal_wrong_at_op": best["wrong"],
            "cal_total_at_op": best["total"],
        }
        print(f"seed {s}: candidates={len(cands)} tau_op={best['tau_op']} "
              f"correct={best['correct']} wrong={best['wrong']} "
              f"total={best['total']}")
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


def panel_triple(frame, utt, chspans, alias: dict):
    wt = R106.r2_triple_of(frame, utt, chspans)
    if wt is None or not alias:
        return wt
    return (alias.get(wt[0], wt[0]), wt[1], wt[2])


def score_panel(runs: Path, taus: dict, snapshot: str, alias: dict, out: Path,
                panels47: Path, device) -> dict:
    panel = [json.loads(l) for l in PANEL.read_text(encoding="utf-8").splitlines()]
    assert len(panel) == 400
    gold_sets = [R106.gold_set(r) for r in panel]
    assert sum(len(g) for g in gold_sets) == N_GOLD
    assert sum(1 for g in gold_sets if len(g) == 0) == 245
    enc0, tok, _ = ENC.load(snapshot)
    del enc0
    unk_ids = {tok.unk}
    text_rows = [{"text": r["sentence"],
                  "gold47": {"act": "NO_FACT", "rel": "UNSURE", "subj": None,
                             "obj": None, "dir": 0, "rep": False}}
                 for r in panel]
    encs = [D.encode_row(r, tok) for r in text_rows]
    assert all(e is not None for e in encs)
    rep = {"seeds": {}}
    for s in SEEDS109:
        model, _ = load_model(runs, s, snapshot, device)
        tau_op = float(taus["seeds"][str(s)]["tau_op"])
        P = S47.probs_for_model(model, encs, device, batch=64)
        parses = [S47.decode(text_rows[i], encs[i], P[i], unk_ids)
                  for i in range(len(panel))]
        # R1: raw exact (ungated), strict + alias views
        r1 = r1_alias = 0
        for i in range(len(panel)):
            fr = parses[i]["frame"]
            if fr is None or fr.get("act") != "STATE":
                continue
            wt = R106.r2_triple_of(fr, text_rows[i]["text"], encs[i]["chspans"])
            if wt is not None and wt in gold_sets[i]:
                r1 += 1
            wa = panel_triple(fr, text_rows[i]["text"], encs[i]["chspans"], alias)
            if wa is not None and wa in gold_sets[i]:
                r1_alias += 1
        # R2/R3: gated writes at tau_op
        writes = wrong = correct = nofact_writes = 0
        a_writes = a_wrong = a_correct = 0
        for i in range(len(panel)):
            v, fr = S47.verdict_single(parses[i], tau_op)
            if v != "EXECUTE" or fr is None:
                continue
            wt = R106.r2_triple_of(fr, text_rows[i]["text"], encs[i]["chspans"])
            if wt is None:
                continue
            writes += 1
            if len(gold_sets[i]) == 0:
                nofact_writes += 1
            if wt in gold_sets[i]:
                correct += 1
            else:
                wrong += 1
            wa = panel_triple(fr, text_rows[i]["text"], encs[i]["chspans"], alias)
            if wa is not None:
                a_writes += 1
                if wa in gold_sets[i]:
                    a_correct += 1
                else:
                    a_wrong += 1
        rate = (wrong / writes) if writes else None
        r3_pass = (writes > 0 and rate is not None and rate <= 0.05
                   and correct >= 30)
        # R4: template panels at the seed's own tau_op
        r4 = {}
        for name in ("t_seen", "t_new"):
            rows = json.loads((panels47 / f"{name}.json").read_text(
                encoding="utf-8"))
            e2 = [D.encode_row(r, tok) for r in rows]
            P2 = S47.probs_for_model(model, e2, device, batch=64)
            ps2 = [[S47.decode(rows[i], e2[i], P2[i], unk_ids)
                    for i in range(len(rows))]]
            golds2 = [S47.gold_frame_of(e) for e in e2]
            sc = S47.score_panel(rows, e2, ps2, tau_op, golds2,
                                 ensemble=False, tau_single=tau_op)
            base = BASE47[name][s]
            r4[name] = {"correct": sc["correct"], "baseline47": base,
                        "drop": base - sc["correct"],
                        "pass": (base - sc["correct"]) <= 5}
        rep["seeds"][str(s)] = {
            "seed": s, "tau_op": tau_op,
            "R1_raw_exact": r1, "R1_pass": r1 >= 94,
            "R1_alias_exact": r1_alias,
            "R2_nofact_writes": nofact_writes, "R2_pass": nofact_writes <= 25,
            "R3_writes": writes, "R3_wrong": wrong, "R3_correct": correct,
            "R3_wrong_rate": rate, "R3_pass": r3_pass,
            "R3_alias": {"writes": a_writes, "wrong": a_wrong,
                         "correct": a_correct},
            "R4": r4,
            "R4_pass": all(r4[n]["pass"] for n in r4),
        }
        print(f"seed {s}: R1={r1} R1alias={r1_alias} "
              f"R2nofact={nofact_writes} R3={correct}c/{wrong}w/{writes}t "
              f"rate={rate} R4seen={r4['t_seen']['correct']} "
              f"R4new={r4['t_new']['correct']}")
    n_r1 = sum(1 for s in SEEDS109 if rep["seeds"][str(s)]["R1_pass"])
    n_r3 = sum(1 for s in SEEDS109 if rep["seeds"][str(s)]["R3_pass"])
    rep["summary"] = {
        "R1_pass_seeds": n_r1, "R1_mark": n_r1 >= 2,
        "R3_pass_seeds": n_r3, "R3_mark": n_r3 >= 2,
        "R4_pass_seeds": sum(1 for s in SEEDS109
                             if rep["seeds"][str(s)]["R4_pass"]),
    }
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--score-panel", action="store_true")
    ap.add_argument("--runs", required=True)
    ap.add_argument("--cal", default=None)
    ap.add_argument("--taus", default=None)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--alias", default=None)
    ap.add_argument("--panels47", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(max(1, torch.get_num_threads()))
    if a.calibrate:
        assert a.cal, "--calibrate needs --cal calwebred.json"
        calibrate(Path(a.runs), Path(a.cal), a.snapshot, Path(a.out), device)
    elif a.score_panel:
        assert a.taus and a.panels47, "--score-panel needs --taus and --panels47"
        alias = json.loads(Path(a.alias).read_text(encoding="utf-8")) \
            if a.alias else {}
        taus = json.loads(Path(a.taus).read_text(encoding="utf-8"))
        score_panel(Path(a.runs), taus, a.snapshot, alias, Path(a.out),
                    Path(a.panels47), device)
    else:
        raise SystemExit("need --calibrate or --score-panel")


if __name__ == "__main__":
    main()
