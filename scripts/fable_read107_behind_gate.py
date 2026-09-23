#!/usr/bin/env python3
"""Exp 107 — READING BEHIND THE GATE (Muse, DIAGNOSTIC, measurement only).

Looks at rung-2 ears' (exp 47, seeds 4701/4702/4703) RAW ungated STATE frames
on the sealed reading panel `data/open/reading94/panel.jsonl` (400 sentences,
155 with >=1 in-inventory triple, 312 triples; 245 NO_FACT) and scores each
frame against gold. No gates, no pass/fail claim.

Reuses exp-106 loading/scoring code by import (read-only, never edited):
  norm, gold_set, r2_triple_of from scripts/fable_read106_score.py
and the sealed rung-2 stack (fable_ears47_data/encoder/model/score).

Per seed (never averaged):
  M1: raw STATE frames -> exact-correct / relation-right-span-wrong /
      wrong-relation / invented (NO_FACT sentence). Integer counts.
  M2: conf distribution (same score the gate uses) for correct vs wrong
      frames: decile cuts + 0.1-bin histogram; best operating point =
      largest #exact-correct at <=1% and <=5% wrong (descriptive sweep).
  M3: top 15 wrong frames verbatim (highest conf); top-10 proposed
      relations vs top-10 gold relations.
  M4: same four M1 counts on the 87 sentences rung-1 could not encode.

Usage:
    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
      python -B scripts/fable_read107_behind_gate.py --snapshot <scibert> \
      --out artifacts/fable-read107-20260921/fable_read107_results.json
"""
from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from pathlib import Path
import sys

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_read106_score as R106  # noqa: E402 (read-only reuse)
import fable_ears45_data as D1  # noqa: E402 (read-only: unencodable set)
import fable_ears47_data as D2  # noqa: E402 (read-only)
import fable_ears47_encoder as ENC2  # noqa: E402
import fable_ears47_model as M2  # noqa: E402
import fable_ears47_score as S47  # noqa: E402 (reuse decode)

REPO = Path(__file__).resolve().parent.parent
PANEL = REPO / "data" / "open" / "reading94" / "panel.jsonl"
R2_RUNS = REPO / "artifacts" / "fable-ears47-20260921" / "runs"

R2_SEEDS = (4701, 4702, 4703)


def percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def conf_summary(confs: list[float]) -> dict:
    s = sorted(confs)
    cuts = {f"d{p}": round(percentile(s, p), 6) for p in (10, 20, 30, 40, 50, 60, 70, 80, 90)}
    bins = [0] * 10
    for c in confs:
        b = min(int(c * 10), 9)
        bins[b] += 1
    return {
        "n": len(confs),
        "min": round(min(confs), 6) if confs else 0.0,
        "max": round(max(confs), 6) if confs else 0.0,
        "mean": round(sum(confs) / len(confs), 6) if confs else 0.0,
        "deciles": cuts,
        "bins_0.0_1.0": bins,
    }


def best_operating_point(frames: list[dict]) -> dict:
    """frames: dicts with exact(bool), conf. Rank high->low conf; for each
    prefix k, rate = wrong/k; record max #correct with rate<=1% and <=5%."""
    order = sorted(frames, key=lambda f: -f["conf"])
    out = {
        "at_1pct": {"correct": 0, "wrong": 0, "total": 0, "threshold": None},
        "at_5pct": {"correct": 0, "wrong": 0, "total": 0, "threshold": None},
    }
    correct = wrong = 0
    for k, f in enumerate(order, 1):
        if f["exact"]:
            correct += 1
        else:
            wrong += 1
        rate = wrong / k
        if rate <= 0.01 and correct > out["at_1pct"]["correct"]:
            out["at_1pct"] = {"correct": correct, "wrong": wrong, "total": k,
                              "threshold": round(f["conf"], 6)}
        if rate <= 0.05 and correct > out["at_5pct"]["correct"]:
            out["at_5pct"] = {"correct": correct, "wrong": wrong, "total": k,
                              "threshold": round(f["conf"], 6)}
    return out


def rung1_unencodable_ids(panel: list[dict]) -> list[str]:
    """Reproduce exp-106's rung-1 unencodable set (D1.encode -> None)."""
    split, pools, lex, gen = D1.load_all()
    rng = random.Random(106000 + 4301)
    ids = []
    for row in panel:
        ex = {"utterance": row["sentence"], "slots": {}, "hops": [],
              "hop_keys": [], "hop_types": [], "act": "unsure", "n_items": 1}
        if D1.encode(ex, lex, rng, False, hash_names=False) is None:
            ids.append(row["id"])
    return ids


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    torch.set_num_threads(1)
    t0 = time.time()

    panel = [json.loads(line) for line in PANEL.read_text(encoding="utf-8").splitlines()]
    assert len(panel) == 400
    gold_sets = [R106.gold_set(r) for r in panel]
    assert sum(len(g) for g in gold_sets) == 312
    assert sum(1 for g in gold_sets if len(g) == 0) == 245

    unenc_ids = rung1_unencodable_ids(panel)
    assert len(unenc_ids) == 87, f"expected 87 unencodable, got {len(unenc_ids)}"
    unenc_set = set(unenc_ids)

    gold_rel_counter: Counter = Counter()
    for g in gold_sets:
        for rel, _s, _o in g:
            gold_rel_counter[rel] += 1

    enc0, tok, _info = ENC2.load(a.snapshot)
    del enc0
    unk_ids = {tok.unk}
    rows = [{"text": r["sentence"],
             "gold47": {"act": "NO_FACT", "rel": "UNSURE", "subj": None,
                        "obj": None, "dir": 0, "rep": False}} for r in panel]
    encs = [D2.encode_row(r, tok) for r in rows]
    assert all(e is not None for e in encs)

    models = []
    for s in R2_SEEDS:
        ck = torch.load(R2_RUNS / f"c-{s}" / "ear.pt", map_location="cpu",
                        weights_only=False)
        enc, _, _ = ENC2.load(a.snapshot)
        m = M2.FrameEars(enc, D2.N_REL, freeze_layers=ck.get("freeze_layers", 0))
        m.load_state_dict(ck["state"])
        m.eval()
        models.append(m)

    res: dict = {"exp": 107, "panel": str(PANEL), "n_sentences": 400,
                 "n_gold_triples": 312, "n_nofact": 245,
                 "unencodable_ids": unenc_ids,
                 "gold_top10_relations": gold_rel_counter.most_common(10),
                 "seeds": {}}
    for si, s in enumerate(R2_SEEDS):
        P = S47.probs_for_model(models[si], encs, torch.device("cpu"), batch=64)
        parses = [S47.decode(rows[i], encs[i], P[i], unk_ids) for i in range(len(rows))]
        acts = Counter(p["frame"]["act"] if p["frame"] else "?" for p in parses)
        frames: list[dict] = []
        prop_rel: Counter = Counter()
        for i, row in enumerate(panel):
            fr = parses[i]["frame"]
            if fr is None or fr.get("act") != "STATE":
                continue
            wt = R106.r2_triple_of(fr, rows[i]["text"], encs[i]["chspans"])
            assert wt is not None
            gs = gold_sets[i]
            exact = wt in gs
            if exact:
                bucket = "exact_correct"
            elif len(gs) == 0:
                bucket = "invented"
            elif wt[0] in {g[0] for g in gs}:
                bucket = "relation_right_span_wrong"
            else:
                bucket = "wrong_relation"
            prop_rel[wt[0]] += 1
            frames.append({"id": row["id"], "sentence": row["sentence"],
                           "conf": float(parses[i].get("conf", 0.0)),
                           "triple": list(wt),
                           "gold": sorted(list(g) for g in gs),
                           "nofact": len(gs) == 0,
                           "bucket": bucket, "exact": exact,
                           "unencodable_rung1": row["id"] in unenc_set})
        counts = Counter(f["bucket"] for f in frames)
        m1 = {"n_raw_state": len(frames),
              "exact_correct": counts.get("exact_correct", 0),
              "relation_right_span_wrong": counts.get("relation_right_span_wrong", 0),
              "wrong_relation": counts.get("wrong_relation", 0),
              "invented": counts.get("invented", 0)}
        m1_sub = {"n_raw_state": 0, "exact_correct": 0,
                  "relation_right_span_wrong": 0, "wrong_relation": 0, "invented": 0}
        for f in frames:
            if f["unencodable_rung1"]:
                m1_sub["n_raw_state"] += 1
                m1_sub[f["bucket"]] += 1
        correct_c = [f["conf"] for f in frames if f["exact"]]
        wrong_c = [f["conf"] for f in frames if not f["exact"]]
        wrong_sorted = sorted((f for f in frames if not f["exact"]),
                              key=lambda f: -f["conf"])[:15]
        res["seeds"][str(s)] = {
            "seed": s, "raw_acts": dict(acts),
            "n_no_state_frame": 400 - len(frames),
            "M1_all": m1, "M4_unencodable87": m1_sub,
            "M2_conf_correct": conf_summary(correct_c),
            "M2_conf_wrong": conf_summary(wrong_c),
            "M2_best_operating_point": best_operating_point(frames),
            "M3_top15_wrong": [
                {"sentence": f["sentence"], "triple": f["triple"],
                 "gold": f["gold"], "conf": round(f["conf"], 6),
                 "bucket": f["bucket"]} for f in wrong_sorted],
            "M3_top10_proposed_relations": prop_rel.most_common(10),
            "frames": [{k: f[k] for k in ("id", "conf", "triple", "bucket")}
                       for f in frames],
        }
        print(f"seed {s}: raw_STATE={m1['n_raw_state']} exact={m1['exact_correct']} "
              f"rel_ok_span_bad={m1['relation_right_span_wrong']} "
              f"wrong_rel={m1['wrong_relation']} invented={m1['invented']} "
              f"acts={dict(acts)}")
    res["elapsed_s"] = round(time.time() - t0, 1)
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"elapsed {res['elapsed_s']}s")


if __name__ == "__main__":
    main()
