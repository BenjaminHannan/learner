#!/usr/bin/env python3
"""Exp 119f — scorer: 119e logic + generalized panel scoring (Muse PREP).

    python fable_ears119f_score.py --score47e --runs <runs> --panels47 <panels> \\
        --snapshot <scibert> --out report47f.json --taus-out taus119f.json
    python fable_ears119f_score.py --score-panel --runs <runs> --taus <taus> \\
        --snapshot <scibert> --panel <panel.jsonl> --panel-tag 94b \\
        --w3-base-bars 27,33,30 --w3-need 3 --w2-min-correct 0 --w2-need 2 \\
        --out report119f_94b.json

--score47e: the 119e score-time re-gate VERBATIM by import (remap_gold_frame
on the 47 panels' golds incl. CAL, unchanged 47 tau rule on CAL only). All
47/119e bars unchanged.

--score-panel: the 119/119b panel path generalized for BOTH panels (reading94
+ registered reading94b). Same ungated single decode, same strict 106 match,
same gated-write verdicts. Two deliberate generalizations (sealed):
  (a) no hardcoded triple counts: the scorer counts N gold triples in the
      panel file and scales the positional W3 bars by formula
      bar_seed = ceil(base_seed * N / 312) with bases 27/33/30 (119b's
      reading94 bars). On reading94 (N=312) this reproduces 27/33/30 exactly.
      N is a fixed property of the sealed panel, never a tuned threshold.
  (b) occupation-subset exact (ungated raw decode, 106 match) per seed:
      occ_exact / occ_gold on each panel — the inputs to falsifier F1.
W2 thresholds come from flags (--w2-min-correct 30 on 94 per 119b; 0 on 94b
per the 119f brief: writes > 0 with wrong-write rate <= 0.05).

Additive only: decode, verdicts, tau rule, 106 normaliser by import. No
training, no panel edits, no test.pt. Panels are scoring-only.
"""
from __future__ import annotations

import argparse
import json
import math as _m
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears119e_score as E119  # noqa: E402  (score47e + remap logic)
import fable_ears119b_score as B119  # noqa: E402  (seed namespace 11911-11913)
import fable_ears47_data as D  # noqa: E402
import fable_ears119_data as D119  # noqa: E402  (MAX_LEN = 192 override)
import fable_ears47_encoder as ENC  # noqa: E402
import fable_ears47_score as S47  # noqa: E402
import fable_ears119_score as S119  # noqa: E402  (load_model/decode_all)
import fable_read106_score as R106  # noqa: E402

SEEDS = list(B119.S119.SEEDS119)
assert tuple(SEEDS) == (11911, 11912, 11913), SEEDS
W2_MAX_RATE = 0.05


def score_panel_gen(runs: Path, taus: dict, snapshot: str, out: Path, device,
                    panel_path: Path, panel_tag: str,
                    w3_base_bars: list[int], w3_need: int,
                    w2_min_correct: int, w2_need: int) -> dict:
    panel = [json.loads(l) for l in panel_path.read_text(
        encoding="utf-8").splitlines()]
    assert len(panel) == 400, f"{panel_tag}: {len(panel)} sentences != 400"
    gold_sets = [R106.gold_set(r) for r in panel]
    n_gold = sum(len(g) for g in gold_sets)
    n_empty = sum(1 for g in gold_sets if len(g) == 0)
    occ_gold_idx = {i: {t for t in gold_sets[i] if t[0] == "occupation"}
                    for i in range(len(panel))}
    n_occ = sum(len(v) for v in occ_gold_idx.values())
    w3_bar = {s: _m.ceil(b * n_gold / 312)
              for s, b in zip(SEEDS, w3_base_bars)}
    enc0, tok, _ = ENC.load(snapshot)
    del enc0
    unk_ids = {tok.unk}
    text_rows = [{"text": r["sentence"],
                  "gold47": {"act": "NO_FACT", "rel": "UNSURE", "subj": None,
                             "obj": None, "dir": 0, "rep": False}}
                 for r in panel]
    encs = [D.encode_row(r, tok) for r in text_rows]
    assert all(e is not None for e in encs)
    rep = {"panel": panel_tag, "sentences": len(panel),
           "n_gold_triples": n_gold, "n_empty": n_empty,
           "n_occ_gold": n_occ, "w3_bar_rule": "ceil(base*N/312)",
           "seeds": {}}
    for s in SEEDS:
        model, _ = S119.load_model(runs, s, snapshot, device)
        tau_op = float(taus["seeds"][str(s)]["tau_exec_single"])
        parses = S119.decode_all(model, text_rows, encs, device, unk_ids)
        del model
        raw = occ = 0
        for i in range(len(panel)):
            fr = parses[i]["frame"]
            if fr is None or fr.get("act") != "STATE":
                continue
            wt = R106.r2_triple_of(fr, text_rows[i]["text"], encs[i]["chspans"])
            if wt is not None and wt in gold_sets[i]:
                raw += 1
                if wt in occ_gold_idx[i]:
                    occ += 1
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
        w3_pass = raw >= w3_bar[s]
        w2_pass = (writes > 0 and rate is not None and rate <= W2_MAX_RATE
                   and correct >= w2_min_correct)
        rep["seeds"][str(s)] = {
            "seed": s, "tau_op": tau_op, "W3_raw_exact": raw,
            "W3_bar": w3_bar[s], "W3_base": w3_base_bars[SEEDS.index(s)],
            "W3_pass": w3_pass,
            "occ_exact": occ, "occ_gold": n_occ,
            "W2_writes": writes, "W2_wrong": wrong, "W2_correct": correct,
            "W2_wrong_rate": rate, "W2_pass": w2_pass}
        print(f"[{panel_tag}] seed {s}: W3={raw}/{w3_bar[s]} occ={occ}/{n_occ} "
              f"W2={correct}c/{wrong}w/{writes}t rate={rate}")
    n_w2 = sum(1 for s in SEEDS if rep["seeds"][str(s)]["W2_pass"])
    n_w3 = sum(1 for s in SEEDS if rep["seeds"][str(s)]["W3_pass"])
    rep["summary"] = {"W2_pass_seeds": n_w2, "W2_mark": n_w2 >= w2_need,
                      "W3_pass_seeds": n_w3, "W3_mark": n_w3 >= w3_need,
                      "w2_need": w2_need, "w3_need": w3_need,
                      "w2_min_correct": w2_min_correct}
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False),
                   encoding="utf-8")
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
    ap.add_argument("--panel-tag", default="94")
    ap.add_argument("--w3-base-bars", default="27,33,30")
    ap.add_argument("--w3-need", type=int, default=2)
    ap.add_argument("--w2-min-correct", type=int, default=30)
    ap.add_argument("--w2-need", type=int, default=2)
    a = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if a.score47e:
        assert a.panels47 and a.taus_out, "--score47e needs --panels47 --taus-out"
        E119.score47e(Path(a.runs), Path(a.panels47), a.snapshot,
                      Path(a.out), Path(a.taus_out), device)
    elif a.score_panel:
        assert a.taus and a.panel, "--score-panel needs --taus --panel"
        taus = json.loads(Path(a.taus).read_text(encoding="utf-8"))
        bases = [int(x) for x in a.w3_base_bars.split(",")]
        assert len(bases) == 3, bases
        score_panel_gen(Path(a.runs), taus, a.snapshot, Path(a.out), device,
                        Path(a.panel), a.panel_tag, bases, a.w3_need,
                        a.w2_min_correct, a.w2_need)
    else:
        raise SystemExit("need --score47e or --score-panel")


if __name__ == "__main__":
    main()
