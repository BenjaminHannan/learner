#!/usr/bin/env python3
"""Exp 119d follow-up: distinct example sentences per top confusion pair.

Panel-only re-decode (seed 11901, Mac CPU). Prints up to 4 DISTINCT sentences
for each (gold, pred) pair given on the command line as gold||pred lines.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D  # noqa: E402
import fable_ears119_data as D119  # noqa: E402
import fable_ears47_encoder as ENC  # noqa: E402
import fable_ears47_model as M  # noqa: E402
import fable_ears47_score as S47  # noqa: E402
import fable_read106_score as R106  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

runs, snapshot = sys.argv[1], sys.argv[2]
pairs = [tuple(l.rstrip("\n").split("||")) for l in sys.stdin if "||" in l]
torch.set_num_threads(1)
enc0, tok, _ = ENC.load(snapshot)
del enc0
unk_ids = {tok.unk}
ck = torch.load(Path(runs) / "w-11901" / "ear.pt", map_location="cpu",
                weights_only=False)
enc, _, _ = ENC.load(snapshot)
model = M.FrameEars(enc, D.N_REL, freeze_layers=ck.get("freeze_layers", 0))
model.load_state_dict(ck["state"])
model.eval()
panel = [json.loads(l) for l in
         (REPO / "data" / "open" / "reading94" / "panel.jsonl")
         .read_text(encoding="utf-8").splitlines()]
gold_sets = [R106.gold_set(r) for r in panel]
rows = [{"text": r["sentence"], "gold47": {"act": "NO_FACT", "rel": "UNSURE",
                                           "subj": None, "obj": None,
                                           "dir": 0, "rep": False}}
        for r in panel]
encs = [D.encode_row(r, tok) for r in rows]
P = S47.probs_for_model(model, encs, torch.device("cpu"), batch=64)
parses = [S47.decode(rows[i], encs[i], P[i], unk_ids) for i in range(len(panel))]
for gr, pr in pairs:
    seen, out = set(), []
    for i, row in enumerate(panel):
        fr = parses[i]["frame"]
        if fr is None or fr.get("act") != "STATE":
            continue
        wt = R106.r2_triple_of(fr, rows[i]["text"], encs[i]["chspans"])
        for g in gold_sets[i]:
            if g[0] == gr and R106.norm(fr.get("rel") or "") == pr \
                    and row["id"] not in seen:
                seen.add(row["id"])
                out.append((row["sentence"], list(wt), list(g),
                            round(float(parses[i]["conf"]), 4)))
                break
        if len(out) == 4:
            break
    print(f"PAIR {gr!r} -> {pr!r}")
    for s, w, g, c in out:
        print(f"  conf={c} gold={g} pred={w}\n    {s[:160]}")
