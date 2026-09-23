#!/usr/bin/env python3
"""Audit 83 dry run: randomly initialised FrameEars (seeds 4701-4703) scored by the
UNMODIFIED fable_ears47_score.py pipeline on CPU. Proves end-to-end executability and
records chance-level floors per mark. Reads ONLY the sealed panels + CAL; writes ONLY
to artifacts/fable-audit83-20260921/.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fable_ears47_data as D  # noqa: E402
import fable_ears47_model as M  # noqa: E402
import fable_ears47_encoder as ENC  # noqa: E402
import fable_ears47_score as S  # noqa: E402  (unmodified scorer)

SNAP = ("/Users/ben-hannan/.cache/huggingface/hub/models--allenai--"
        "scibert_scivocab_uncased/snapshots/24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1")
PANELS = ROOT / "artifacts" / "fable-ears47-20260921" / "panels"
OUT = ROOT / "artifacts" / "fable-audit83-20260921"
NAMES = ["cal", "t_seen", "t_new", "t_trap", "t_hard", "wneg", "wpos",
         "wclosed", "wnewrel"]
BATCH = 256


def main() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    enc0, tok, _ = ENC.load(SNAP)
    unk_ids = {tok.unk}
    del enc0
    store = {}
    for name in NAMES:
        rows = json.loads((PANELS / f"{name}.json").read_text(encoding="utf-8"))
        store[name] = (rows, S.encode_panel(rows, tok))
    models = []
    for s in S.SEEDS:
        torch.manual_seed(s)  # random init, seeded for reproducibility
        enc, _, _ = ENC.load(SNAP)
        models.append(M.FrameEars(enc, D.N_REL).eval())
    device = torch.device("cpu")
    parses_all = {}
    for name, (rows, encs) in store.items():
        golds = [S.gold_frame_of(e) for e in encs]
        parses = []
        for m in models:
            P = S.probs_for_model(m, encs, device, batch=BATCH)
            parses.append([S.decode(rows[i], encs[i], P[i], unk_ids)
                           for i in range(len(rows))])
        parses_all[name] = (rows, encs, golds, parses)
        print(f"decoded {name} n={len(rows)}", flush=True)
    cal_rows, cal_encs, cal_golds, cal_parses = parses_all["cal"]
    tau0 = S.tau0_from_cal(cal_golds, cal_parses, ensemble=True)
    tau_exec = 1.0 - (1.0 - tau0) / 2.0
    print(f"tau0={tau0} tau_exec={tau_exec} tau_echo={S.TAU_ECHO}", flush=True)
    marks = {}
    # NOTE: score_panel(rows, encs, parses, tau, golds, ensemble) -- pass positionally
    ens = {}
    for n in NAMES:
        if n == "cal":
            continue
        rows, encs, golds, parses = parses_all[n]
        ens[n] = S.score_panel(rows, encs, parses, tau_exec, golds, True)
    agg = lambda k: sum(ens[n][k] for n in ("t_seen", "t_new", "t_trap", "t_hard"))
    marks["R2-SAFE"] = {"silent_6500": agg("silent_wrong_write"),
                        "trap_written": ens["t_trap"]["written"]}
    marks["R2-NEG"] = {"n": ens["wneg"]["n"],
                       "exec_state": S._count_exec_fact(parses_all["wneg"], tau_exec)}
    for n in ("t_seen", "t_new", "t_hard"):
        marks[n] = {"n": ens[n]["n"], "correct": ens[n]["correct"],
                    "executed": ens[n]["executed"],
                    "wrong_exec_ask": ens[n]["wrong_exec_ask"],
                    "silent": ens[n]["silent_wrong_write"]}
    marks["R2-WEB"] = {"n": ens["wclosed"]["n"], "executed": ens["wclosed"]["executed"],
                       "exact": S._count_exact(parses_all["wclosed"], tau_exec)}
    marks["R2-NEWREL"] = {"n": ens["wnewrel"]["n"],
                          "wrong_seen": S._count_wrong_seen(parses_all["wnewrel"],
                                                            tau_exec)}
    marks["elapsed_min"] = round((time.time() - t0) / 60, 1)
    (OUT / "fable_audit83_dryrun_report.json").write_text(
        json.dumps(marks, indent=1), encoding="utf-8")
    print(json.dumps(marks, indent=1))


if __name__ == "__main__":
    main()
