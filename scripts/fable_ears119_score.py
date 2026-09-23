#!/usr/bin/env python3
"""Exp 119 — 47-panel + reading94 scoring for the length-coverage wave (Muse PREP).

    python fable_ears119_score.py --score47 --runs <runs> --panels47 <47/panels> \\
        --snapshot <scibert> --out report47.json
    python fable_ears119_score.py --score-panel --runs <runs> --taus <taus.json> \\
        --snapshot <scibert> --out report119.json

--score47: the sealed exp-47 gate, re-run on the 119 checkpoints at MAX_LEN 192
with 47's calibration procedure (tau0 on CAL -> tau_exec = 1-(1-tau0)/2, ensemble
+ per-seed singles), EXCEPT the SEEN need_exec bar uses the doc-95 corrected
denominator: executable (concrete-gold, non-OPEN/UNSURE) STATE rows only
(47 sealed 654; asserted here). All other 47 bars verbatim. Also emits W1
(wclosed ensemble: executed >= 23/46 AND silent wrong writes = 0) and the
per-seed taus (taus.json) consumed by --score-panel.

--score-panel (held-out reading94, never trained/tuned on): per seed s, W3 raw
exact STATE frames (ungated single decode, 106 triple match) vs the positional
3x bars (11901>=27, 11902>=33, 11903>=30, i.e. 3x exp-107's 9/11/10); W2 gated
writes at the seed's own tau_exec_single (correct >= 30 AND wrong <= 5%).

Additive only: everything else imported read-only (MAX override via D119).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D  # noqa: E402
import fable_ears119_data as D119  # noqa: E402  (MAX_LEN = 192 override)
import fable_ears47_encoder as ENC  # noqa: E402
import fable_ears47_model as M  # noqa: E402
import fable_ears47_score as S47  # noqa: E402
import fable_read106_score as R106  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
PANEL = REPO / "data" / "open" / "reading94" / "panel.jsonl"
SEEDS119 = (11901, 11902, 11903)
POS = {11901: 4701, 11902: 4702, 11903: 4703}
W3_BAR = {11901: 27, 11902: 33, 11903: 30}  # 3x exp-107 raw exact 9/11/10
N_GOLD94 = 312

PANELS47 = ("cal", "t_seen", "t_new", "t_far", "t_trap", "t_hard",
            "wneg", "wpos", "wclosed", "wnewrel")


def load_model(runs: Path, seed: int, snapshot: str, device):
    ck = torch.load(runs / f"w-{seed}" / "ear.pt", map_location="cpu",
                    weights_only=False)
    enc, _, _ = ENC.load(snapshot)
    m = M.FrameEars(enc, D.N_REL, freeze_layers=ck.get("freeze_layers", 0))
    m.load_state_dict(ck["state"])
    return m.eval().to(device), ck


def decode_all(model, rows, encs, device, unk_ids, batch=64):
    P = S47.probs_for_model(model, encs, device, batch=batch)
    return [S47.decode(rows[i], encs[i], P[i], unk_ids) for i in range(len(rows))]


def executable_state_n(rows) -> int:
    """STATE-gold rows with a concrete (non-OPEN/UNSURE) relation: can EXECUTE."""
    n = 0
    for r in rows:
        g = r["gold47"]
        if g["act"] == "STATE" and g.get("rel") not in ("OPEN", "UNSURE"):
            n += 1
    return n


def score47(runs: Path, panels47: Path, snapshot: str, out: Path,
            taus_out: Path, device) -> dict:
    enc0, tok, _ = ENC.load(snapshot)
    del enc0
    unk_ids = {tok.unk}
    panels = {}
    encs = {}
    for name in PANELS47:
        rows = json.loads((panels47 / f"{name}.json").read_text(encoding="utf-8"))
        panels[name] = rows
        encs[name] = [D.encode_row(r, tok) for r in rows]
    parses = {}
    for s in SEEDS119:
        model, _ = load_model(runs, s, snapshot, device)
        parses[s] = {name: decode_all(model, panels[name], encs[name],
                                      device, unk_ids)
                     for name in PANELS47}
        del model
    golds = {name: [S47.gold_frame_of(e) if e is not None else None
                    for e in encs[name]] for name in PANELS47}

    tau0_ens = S47.tau0_from_cal(
        golds["cal"], [parses[s]["cal"] for s in SEEDS119], ensemble=True)
    tau_ens = 1 - (1 - tau0_ens) / 2
    tau_single = {}
    for s in SEEDS119:
        t0 = S47.tau0_from_cal(golds["cal"], [parses[s]["cal"]], ensemble=False)
        tau_single[s] = 1 - (1 - t0) / 2
    taus = {"tau0_ens": tau0_ens, "tau_exec_ens": tau_ens,
            "seeds": {str(s): {"tau0": S47.tau0_from_cal(
                golds["cal"], [parses[s]["cal"]], ensemble=False),
                "tau_exec_single": tau_single[s]} for s in SEEDS119}}
    taus_out.write_text(json.dumps(taus, indent=1), encoding="utf-8")

    ens = {name: S47.score_panel(
        panels[name], encs[name], [parses[s][name] for s in SEEDS119],
        tau_ens, golds[name], ensemble=True) for name in PANELS47}
    sing = {str(s): {name: S47.score_panel(
        panels[name], encs[name], [parses[s][name]], tau_ens, golds[name],
        ensemble=False, tau_single=tau_single[s]) for name in PANELS47}
        for s in SEEDS119}

    need_exec_seen = executable_state_n(panels["t_seen"])
    assert need_exec_seen == 654, f"executable SEEN rows {need_exec_seen} != 654"
    need_exec_new = executable_state_n(panels["t_new"])
    import math as _m
    marks = {
        "SAFE": ens["t_seen"]["silent_wrong_write"]
        + ens["t_new"]["silent_wrong_write"]
        + ens["t_trap"]["silent_wrong_write"]
        + ens["t_hard"]["silent_wrong_write"] == 0,
        "SAFE_silent": sum(ens[n]["silent_wrong_write"] for n in
                           ("t_seen", "t_new", "t_trap", "t_hard")),
        "NEG": ens["wneg"]["written"] / 2092 <= 0.02,
        "SEEN_correct": ens["t_seen"]["correct"] >= 1940,
        "SEEN_exec": sum(1 for k, r in enumerate(panels["t_seen"])
                         if S47.verdict_ensemble(
                             [parses[s]["t_seen"][k] for s in SEEDS119],
                             tau_ens)[0] == "EXECUTE"
                         and r["gold47"]["act"] == "STATE"
                         and r["gold47"].get("rel") not in ("OPEN", "UNSURE"))
        >= _m.ceil(0.90 * need_exec_seen),
        "NEW_correct": ens["t_new"]["correct"] >= 2400,
        "NEW_exec": ens["t_new"]["exec_state_gold"] >= 784,
        "NAMES": ens["t_hard"]["correct"] >= 300,
        "ASK": ens["t_seen"]["wrong_exec_ask"]
        + ens["t_new"]["wrong_exec_ask"] <= 25,
        "WEB_exec": ens["wclosed"]["executed"] >= 28,
        "WEB_exact": (ens["wclosed"]["exec_correct"] / ens["wclosed"]["executed"]
                      >= 0.85) if ens["wclosed"]["executed"] else False,
        "NEWREL": None,  # replaced below by the concrete-relation rule
    }
    # NEWREL per 47: EXECUTE with a concrete seen relation on held-out golds.
    newrel_bad = 0
    for k, r in enumerate(panels["wnewrel"]):
        v, fr = S47.verdict_ensemble(
            [parses[s]["wnewrel"][k] for s in SEEDS119], tau_ens)
        if v == "EXECUTE" and fr is not None \
                and fr.get("rel") not in ("OPEN", "UNSURE", None):
            newrel_bad += 1
    marks["NEWREL"] = newrel_bad / 1500 <= 0.01
    marks["NEWREL_bad"] = newrel_bad
    w1 = {"executed": ens["wclosed"]["executed"],
          "silent": ens["wclosed"]["silent_wrong_write"],
          "pass": ens["wclosed"]["executed"] >= 23
          and ens["wclosed"]["silent_wrong_write"] == 0}
    gate47 = all(marks[k] for k in ("SAFE", "NEG", "SEEN_correct", "SEEN_exec",
                                    "NEW_correct", "NEW_exec", "NAMES", "ASK",
                                    "WEB_exec", "WEB_exact", "NEWREL"))
    rep = {"taus": taus, "need_exec_seen": need_exec_seen,
           "need_exec_new": need_exec_new,
           "ens_correct": {n: ens[n]["correct"] for n in PANELS47},
           "ens_executed": {n: ens[n]["executed"] for n in PANELS47},
           "ens_silent": {n: ens[n]["silent_wrong_write"] for n in PANELS47},
           "ens_echoed_wrong": {n: ens[n]["echoed_wrong_write"]
                                for n in PANELS47},
           "singles_correct": {
               str(s): {n: sing[str(s)][n]["correct"] for n in PANELS47}
               for s in SEEDS119},
           "marks47_corrected": marks, "gate47": gate47, "W1": w1}
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    print(json.dumps({"gate47": gate47, "W1": w1,
                      "SEEN_exec_bar": _m.ceil(0.90 * need_exec_seen),
                      "taus": taus}, indent=1))
    return rep


def score_panel(runs: Path, taus: dict, snapshot: str, out: Path, device,
                panel_path: Path | None = None) -> dict:
    panel = [json.loads(l) for l in (panel_path or PANEL).read_text(
        encoding="utf-8").splitlines()]
    assert len(panel) == 400
    gold_sets = [R106.gold_set(r) for r in panel]
    assert sum(len(g) for g in gold_sets) == N_GOLD94
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
    for s in SEEDS119:
        model, _ = load_model(runs, s, snapshot, device)
        tau_op = float(taus["seeds"][str(s)]["tau_exec_single"])
        parses = decode_all(model, text_rows, encs, device, unk_ids)
        del model
        raw = 0
        for i in range(len(panel)):
            fr = parses[i]["frame"]
            if fr is None or fr.get("act") != "STATE":
                continue
            wt = R106.r2_triple_of(fr, text_rows[i]["text"], encs[i]["chspans"])
            if wt is not None and wt in gold_sets[i]:
                raw += 1
        writes = wrong = correct = 0
        for i in range(len(panel)):
            v, fr = S47.verdict_single(parses[i], tau_op)
            if v != "EXECUTE" or fr is None:
                continue
            wt = R106.r2_triple_of(fr, text_rows[i]["text"], encs[i]["chspans"])
            if wt is None:
                continue
            writes += 1
            if wt in gold_sets[i]:
                correct += 1
            else:
                wrong += 1
        rate = (wrong / writes) if writes else None
        w3_pass = raw >= W3_BAR[s]
        w2_pass = (writes > 0 and rate is not None and rate <= 0.05
                   and correct >= 30)
        rep["seeds"][str(s)] = {
            "seed": s, "tau_op": tau_op, "W3_raw_exact": raw,
            "W3_bar": W3_BAR[s], "W3_pass": w3_pass,
            "W2_writes": writes, "W2_wrong": wrong, "W2_correct": correct,
            "W2_wrong_rate": rate, "W2_pass": w2_pass}
        print(f"seed {s}: W3={raw}/{W3_BAR[s]} "
              f"W2={correct}c/{wrong}w/{writes}t rate={rate}")
    n_w2 = sum(1 for s in SEEDS119 if rep["seeds"][str(s)]["W2_pass"])
    n_w3 = sum(1 for s in SEEDS119 if rep["seeds"][str(s)]["W3_pass"])
    rep["summary"] = {"W2_pass_seeds": n_w2, "W2_mark": n_w2 >= 2,
                      "W3_pass_seeds": n_w3, "W3_mark": n_w3 >= 2}
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score47", action="store_true")
    ap.add_argument("--score-panel", action="store_true")
    ap.add_argument("--runs", required=True)
    ap.add_argument("--panels47", default=None)
    ap.add_argument("--taus", default=None)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--taus-out", default=None)
    ap.add_argument("--panel", default=None,
                    help="reading94 panel.jsonl (defaults to the repo copy)")
    a = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if a.score47:
        assert a.panels47 and a.taus_out, "--score47 needs --panels47 --taus-out"
        score47(Path(a.runs), Path(a.panels47), a.snapshot, Path(a.out),
                Path(a.taus_out), device)
    elif a.score_panel:
        assert a.taus, "--score-panel needs --taus"
        taus = json.loads(Path(a.taus).read_text(encoding="utf-8"))
        score_panel(Path(a.runs), taus, a.snapshot, Path(a.out), device,
                    Path(a.panel) if a.panel else None)
    else:
        raise SystemExit("need --score47 or --score-panel")


if __name__ == "__main__":
    main()
