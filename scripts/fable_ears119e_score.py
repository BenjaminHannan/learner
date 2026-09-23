#!/usr/bin/env python3
"""Exp 119e — score-time gold-remap scorer over the frozen 119b checkpoints.

ONE CHANGE vs the 119/119b scorer (diagnosis ref: doc 119e, gate 43/50):
the scorer applies remap.json's REMAP to the 47 panels' GOLD labels at
scoring time (all 10 panels incl. CAL), then re-fits taus with the UNCHANGED
47 rule and re-scores every 119b mark on the existing 3 checkpoints
(11911/11912/11913, no retraining). reading94 golds already use the inventory
names (311/312; the single 'country' triple, El Al -> Israel, is left as-is)
so --score-panel delegates to the 119b scorer byte-for-byte.

Additive only: decode, verdicts, tau rule, marks, and the 106 normaliser are
the 119/119b code by import. No training, no panel edits, no test.pt.

    python fable_ears119e_score.py --score47e --runs <runs> --panels47 <panels> \\
        --snapshot <scibert> --out report47e.json --taus-out taus119e.json
    python fable_ears119e_score.py --score-panel --runs <runs> --taus <taus> \\
        --snapshot <scibert> --out report119e.json [--panel panel.jsonl]
"""
from __future__ import annotations

import argparse
import json
import math as _m
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears119b_score as B119  # noqa: E402  (seeds 11911-11913, W3 bars)
import fable_ears47_score as S47  # noqa: E402  (unchanged 47 rule)
import fable_ears119_score as S119  # noqa: E402  (PANELS47, executable_state_n)

REPO = Path(__file__).resolve().parent.parent

# THE ONE CHANGE: remap.json's REMAP applied to panel GOLD labels at scoring.
REMAP = {
    "country": "located in the administrative territorial entity",
    "city": "located in the administrative territorial entity",
    "birthplace": "place of birth",
    "job": "occupation",
}

_remap_file = json.loads(
    (REPO / "artifacts" / "fable-ears119b-20260922" / "remap.json")
    .read_text(encoding="utf-8"))
assert _remap_file["mapping"] == REMAP, "scorer REMAP != remap.json mapping"


def remap_gold_frame(gold):
    """Gold frame with the relation remapped; same object if no entry."""
    if gold is None:
        return None
    if gold.get("rel") in REMAP:
        gold = dict(gold)
        gold["rel"] = REMAP[gold["rel"]]
    return gold


def score47e(runs: Path, panels47: Path, snapshot: str, out: Path,
             taus_out: Path, device) -> dict:
    import fable_ears47_encoder as ENC
    import fable_ears47_data as D
    enc0, tok, _ = ENC.load(snapshot)
    del enc0
    unk_ids = {tok.unk}
    panels, encs = {}, {}
    for name in S119.PANELS47:
        rows = json.loads((panels47 / f"{name}.json").read_text(encoding="utf-8"))
        panels[name] = rows
        encs[name] = [D.encode_row(r, tok) for r in rows]
    parses = {}
    seeds = list(B119.S119.SEEDS119)  # (11911, 11912, 11913) via the 119b shim
    for s in seeds:
        model, _ = S119.load_model(runs, s, snapshot, device)
        parses[s] = {name: S119.decode_all(model, panels[name], encs[name],
                                           device, unk_ids)
                     for name in S119.PANELS47}
        del model
    # THE ONE CHANGE: gold frames remapped (acts/spans/dirs untouched).
    golds = {name: [remap_gold_frame(S47.gold_frame_of(e)) if e is not None
                    else None for e in encs[name]] for name in S119.PANELS47}
    n_remap_cal = sum(1 for k, e in enumerate(encs["cal"])
                      if S47.gold_frame_of(e) is not None
                      and S47.gold_frame_of(e).get("rel") in REMAP)
    assert n_remap_cal == 346, f"CAL remapped golds {n_remap_cal} != 346"

    tau0_ens = S47.tau0_from_cal(
        golds["cal"], [parses[s]["cal"] for s in seeds], ensemble=True)
    tau_ens = 1 - (1 - tau0_ens) / 2
    tau_single = {}
    for s in seeds:
        t0 = S47.tau0_from_cal(golds["cal"], [parses[s]["cal"]], ensemble=False)
        tau_single[s] = 1 - (1 - t0) / 2
    taus = {"tau0_ens": tau0_ens, "tau_exec_ens": tau_ens,
            "seeds": {str(s): {"tau0": S47.tau0_from_cal(
                golds["cal"], [parses[s]["cal"]], ensemble=False),
                "tau_exec_single": tau_single[s]} for s in seeds}}
    taus_out.write_text(json.dumps(taus, indent=1), encoding="utf-8")

    ens = {name: S47.score_panel(
        panels[name], encs[name], [parses[s][name] for s in seeds],
        tau_ens, golds[name], ensemble=True) for name in S119.PANELS47}
    sing = {str(s): {name: S47.score_panel(
        panels[name], encs[name], [parses[s][name]], tau_ens, golds[name],
        ensemble=False, tau_single=tau_single[s]) for name in S119.PANELS47}
        for s in seeds}

    # Marks block = fable_ears119_score.score47 verbatim (bars unchanged).
    need_exec_seen = S119.executable_state_n(panels["t_seen"])
    assert need_exec_seen == 654, f"executable SEEN rows {need_exec_seen} != 654"
    need_exec_new = S119.executable_state_n(panels["t_new"])
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
                             [parses[s]["t_seen"][k] for s in seeds],
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
        "NEWREL": None,
    }
    newrel_bad = 0
    for k, r in enumerate(panels["wnewrel"]):
        v, fr = S47.verdict_ensemble(
            [parses[s]["wnewrel"][k] for s in seeds], tau_ens)
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
           "remap_applied": {"cal_remapped_golds": n_remap_cal,
                             "table": REMAP},
           "ens_correct": {n: ens[n]["correct"] for n in S119.PANELS47},
           "ens_executed": {n: ens[n]["executed"] for n in S119.PANELS47},
           "ens_silent": {n: ens[n]["silent_wrong_write"]
                          for n in S119.PANELS47},
           "ens_echoed_wrong": {n: ens[n]["echoed_wrong_write"]
                                for n in S119.PANELS47},
           "singles_correct": {
               str(s): {n: sing[str(s)][n]["correct"] for n in S119.PANELS47}
               for s in seeds},
           "marks47_corrected": marks, "gate47": gate47, "W1": w1}
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    print(json.dumps({"gate47": gate47, "W1": w1,
                      "SEEN_exec_bar": _m.ceil(0.90 * need_exec_seen),
                      "taus": taus,
                      "cal_remapped_golds": n_remap_cal}, indent=1))
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score47e", action="store_true")
    ap.add_argument("--score-panel", action="store_true")
    ap.add_argument("--runs", required=True)
    ap.add_argument("--panels47", default=None)
    ap.add_argument("--taus", default=None)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--taus-out", default=None)
    ap.add_argument("--panel", default=None)
    a = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if a.score47e:
        assert a.panels47 and a.taus_out, "--score47e needs --panels47 --taus-out"
        score47e(Path(a.runs), Path(a.panels47), a.snapshot, Path(a.out),
                 Path(a.taus_out), device)
    elif a.score_panel:
        # reading94 path: 119b scorer verbatim (golds already inventory names).
        import sys as _sys
        _sys.argv = ["fable_ears119b_score.py", "--score-panel",
                     "--runs", a.runs, "--taus", a.taus,
                     "--snapshot", a.snapshot, "--out", a.out] + (
                         ["--panel", a.panel] if a.panel else [])
        B119.S119.main()
    else:
        raise SystemExit("need --score47e or --score-panel")


if __name__ == "__main__":
    main()
