#!/usr/bin/env python3
"""Exp 106 — FIRST READING-LADDER SCORE (Muse).

Runs the ears we already have (inference only, Mac CPU, no training) on the
sealed reading panel `data/open/reading94/panel.jsonl` (400 hand-labelled
Simple English Wikipedia sentences: 155 with >=1 in-inventory triple, 312
triples; 245 NO_FACT) and scores writes against the panel gold.

Ears scored (every seed separately, never averaged):
  (a) rung-1 ears tape + bigru, seeds 4301/4302/4303, behind the exp-76
      certified write gate (tau-hat from
      artifacts/fable-abstain76-20260921/ltt_summary.json);
  (b) rung-2 ears seeds 4701/4702/4703, each with its own sealed tau_exec
      from artifacts/fable-ears47-20260921/runs/report.json (tau_exec_single).
      Rung 2 is a registered FAIL; this is a measurement, not a re-test.

Sealed marks (PASSMARKS.md, hashed before any inference):
  R1: wrong writes / writes <= 1% per ears/seed (gated). Wrong write = an
      EXECUTE write whose (relation, subject, object) triple, after the
      normaliser below, is not in the gold triple set for that sentence.
      0/0 passes vacuously and is labelled as such.
  R2: correct writes / 312 gold triples per ears/seed (recall, reported only).
  R3: writes on the 245 NO_FACT sentences per ears/seed (reported; safety read
      only via R1).

Normaliser (same for every ears/seed, documented here because the two rung
decoders use different span systems): casefold + strip + collapse internal
whitespace on each of relation/subject/object; direction ignored; a missing
object normalises to "". Correct write = normalised triple is a member of the
sentence's gold triple set (counts once per write; recall denominator 312).

Verdict labels: neither decoder emits CLARIFY (reported as 0 with this note);
REPHRASE is the abstention verdict in both decoders; NO_FACT is a raw frame
act (rung 2) reported in the act histogram.

Un-encodable sentences: rung-1 toy-vocab encode returns None past 8 distinct
opaque words -> counted as REPHRASE (unencodable), never a write. Rung-2
WordPiece encode never returns None here (dummy non-representable gold).

Usage:
    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
      python -B scripts/fable_read106_score.py --snapshot <scibert> --out <json>
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_listening_english as LE  # noqa: E402 (read-only)
import fable_ears45_data as D1  # noqa: E402 (read-only)
import fable_ears45_model as M1  # noqa: E402
import fable_ears45_train as T1  # noqa: E402
import fable_ears45_score as S45  # noqa: E402 (reuse decode + verdict fns)
import fable_ears47_data as D2  # noqa: E402 (read-only)
import fable_ears47_encoder as ENC2  # noqa: E402
import fable_ears47_model as M2  # noqa: E402
import fable_ears47_score as S47  # noqa: E402 (reuse decode + verdict fns)

REPO = Path(__file__).resolve().parent.parent
PANEL = REPO / "data" / "open" / "reading94" / "panel.jsonl"
R1_RUNS = REPO / "artifacts" / "fable-ears45-20260921" / "runs"
R2_RUNS = REPO / "artifacts" / "fable-ears47-20260921" / "runs"
LTT = REPO / "artifacts" / "fable-abstain76-20260921" / "ltt_summary.json"

R1_ARMS = ("tape", "bigru")
R1_SEEDS = (4301, 4302, 4303)
R2_SEEDS = (4701, 4702, 4703)
N_GOLD_TRIPLES = 312


def norm(s: str | None) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s.casefold()).strip()


def gold_set(row: dict) -> set[tuple[str, str, str]]:
    return {(norm(t["relation"]), norm(t["subject"]), norm(t["object"]))
            for t in row.get("triples", [])}


def r1_triple_of(item: dict) -> tuple[str, str, str] | None:
    """rung-1 EXECUTE item -> normalised (rel, subj, obj) triple or None."""
    act = item.get("act")
    if act not in LE.WRITE_ACTS:
        return None
    path = item.get("relation_path") or []
    rel = path[0] if path else ""
    subj = item.get("subject") or ""
    val = item.get("value") or ""
    return (norm(rel), norm(subj), norm(val))


def r2_triple_of(frame: dict, utt: str, chspans) -> tuple[str, str, str] | None:
    """rung-2 EXECUTE frame -> normalised (rel, subj, obj) triple or None."""
    if frame is None or frame.get("act") not in S47.WRITE_ACTS:
        return None
    rel = frame.get("rel") or ""
    subj_txt, obj_txt = "", ""
    if frame.get("subj"):
        s, e = frame["subj"]
        subj_txt = utt[chspans[s][0]:chspans[e][1]]
    if frame.get("obj"):
        s, e = frame["obj"]
        obj_txt = utt[chspans[s][0]:chspans[e][1]]
    return (norm(rel), norm(subj_txt), norm(obj_txt))


def score_writes(sent_rows: list[dict]) -> dict:
    """Aggregate per-sentence write records into R1/R2/R3 integers."""
    writes = wrong = correct = 0
    nofact_writes = 0
    wrong_counter: Counter = Counter()
    wrong_examples: list[dict] = []
    for r in sent_rows:
        if r["write_triple"] is not None:
            writes += 1
            if r["nofact"]:
                nofact_writes += 1
            if r["match"]:
                correct += 1
            else:
                wrong += 1
                wrong_counter[r["write_triple"]] += 1
                if len(wrong_examples) < 200:
                    wrong_examples.append({
                        "id": r["id"], "sentence": r["sentence"],
                        "verdict": r["verdict"],
                        "write": list(r["write_triple"]),
                        "gold": sorted(list(g) for g in r["gold"]),
                    })
    rate = (wrong / writes) if writes else 0.0
    top_wrong = [
        {"triple": list(t), "count": c,
         "example_sentence": next(w["sentence"] for w in wrong_examples
                                  if tuple(w["write"]) == t)}
        for t, c in wrong_counter.most_common(10)
    ]
    return {
        "writes": writes, "wrong": wrong, "correct": correct,
        "wrong_rate": rate,
        "r1_gate_pass": (rate <= 0.01),
        "r1_vacuous": (writes == 0),
        "recall_correct_of_312": correct,
        "recall": correct / N_GOLD_TRIPLES,
        "nofact_writes": nofact_writes,
        "top_wrong": top_wrong,
        "n_wrong_distinct": len(wrong_counter),
        "wrong_examples": wrong_examples,
    }


def run_rung1(tau_hat: dict[str, float]) -> dict:
    split, pools, lex, gen = D1.load_all()
    panel = [json.loads(l) for l in PANEL.read_text(encoding="utf-8").splitlines()]
    out: dict = {}
    for arm in R1_ARMS:
        for seed in R1_SEEDS:
            key = f"rung1-{arm}-{seed}"
            ck = torch.load(R1_RUNS / f"{arm}-{seed}" / "ear.pt",
                            weights_only=False)
            m = M1.Ears(ck["vocab"], arm)
            m.load_state_dict(ck["state"])
            m.eval()
            rng = random.Random(106000 + seed)
            encs, keep, keep_idx = [], [], []
            unencodable = 0
            for i, row in enumerate(panel):
                ex = {"utterance": row["sentence"], "slots": {}, "hops": [],
                      "hop_keys": [], "hop_types": [], "act": "unsure",
                      "n_items": 1}
                e = D1.encode(ex, lex, rng, False, hash_names=False)
                if e is None:
                    unencodable += 1
                    continue
                e["idx"] = len(encs)
                encs.append(e)
                keep.append(ex)
                keep_idx.append(i)
            packs = T1.to_tensors(encs)
            res_probs = S45.run_ear(m, packs)
            sent_rows: list[dict] = []
            verdicts: Counter = Counter()
            acts: Counter = Counter()
            enc_pos = {idx: k for k, idx in enumerate(keep_idx)}
            for i, row in enumerate(panel):
                gs = gold_set(row)
                rec = {"id": row["id"], "sentence": row["sentence"],
                       "gold": gs, "nofact": (len(gs) == 0)}
                if i not in enc_pos:
                    rec.update(verdict="REPHRASE", raw_act="unencodable",
                               conf=0.0, write_triple=None, match=False,
                               note="unencodable: >8 distinct opaque words")
                    verdicts["REPHRASE"] += 1
                    acts["unencodable"] += 1
                else:
                    k = enc_pos[i]
                    P = res_probs[k]
                    p = S45.decode(keep[k], encs[k], P)
                    v, item = S45.verdict_single(p, tau_hat[arm])
                    verdicts[v] += 1
                    acts[p.get("act", "?")] += 1
                    wt = (r1_triple_of(item) if v == "EXECUTE"
                          and item is not None else None)
                    rec.update(verdict=v, raw_act=p.get("act"),
                               conf=float(p.get("conf", 0.0)),
                               write_triple=wt,
                               match=(wt in gs) if wt is not None else False)
                sent_rows.append(rec)
            agg = score_writes(sent_rows)
            out[key] = {
                "arm": arm, "seed": seed, "tau_exec": tau_hat[arm],
                "n": len(panel), "unencodable": unencodable,
                "verdicts": dict(verdicts), "raw_acts": dict(acts),
                "clarify": 0,
                **agg,
                "sentences": [
                    {**r, "gold": sorted(list(g) for g in r["gold"]),
                     "write_triple": (list(r["write_triple"])
                                      if r["write_triple"] else None)}
                    for r in sent_rows
                ],
            }
    return out


def run_rung2(snapshot: str, tau_single: list[float]) -> dict:
    enc0, tok, info = ENC2.load(snapshot)
    del enc0
    unk_ids = {tok.unk}
    panel = [json.loads(l) for l in PANEL.read_text(encoding="utf-8").splitlines()]
    rows = [{"text": r["sentence"],
             "gold47": {"act": "NO_FACT", "rel": "UNSURE", "subj": None,
                        "obj": None, "dir": 0, "rep": False}}
            for r in panel]
    encs = [D2.encode_row(r, tok) for r in rows]
    assert all(e is not None for e in encs), "dummy-gold encode must not drop"
    models = []
    for s in R2_SEEDS:
        ck = torch.load(R2_RUNS / f"c-{s}" / "ear.pt", map_location="cpu",
                        weights_only=False)
        enc, _, _ = ENC2.load(snapshot)
        m = M2.FrameEars(enc, D2.N_REL, freeze_layers=ck.get("freeze_layers", 0))
        m.load_state_dict(ck["state"])
        m.eval()
        models.append(m)
    out: dict = {}
    for si, s in enumerate(R2_SEEDS):
        key = f"rung2-c-{s}"
        P = S47.probs_for_model(models[si], encs, torch.device("cpu"), batch=64)
        parses = [S47.decode(rows[i], encs[i], P[i], unk_ids)
                  for i in range(len(rows))]
        sent_rows: list[dict] = []
        verdicts: Counter = Counter()
        acts: Counter = Counter()
        for i, row in enumerate(panel):
            gs = gold_set(row)
            v, fr = S47.verdict_single(parses[i], tau_single[si])
            verdicts[v] += 1
            acts[fr.get("act", "?") if fr else "?"] += 1
            wt = (r2_triple_of(fr, rows[i]["text"], encs[i]["chspans"])
                  if v == "EXECUTE" and fr is not None else None)
            sent_rows.append({
                "id": row["id"], "sentence": row["sentence"], "gold": gs,
                "nofact": (len(gs) == 0), "verdict": v,
                "raw_act": fr.get("act") if fr else None,
                "conf": float(parses[i].get("conf", 0.0)),
                "write_triple": wt,
                "match": (wt in gs) if wt is not None else False,
            })
        agg = score_writes(sent_rows)
        out[key] = {
            "seed": s, "tau_exec": tau_single[si],
            "n": len(panel), "unencodable": 0,
            "verdicts": dict(verdicts), "raw_acts": dict(acts),
            "clarify": 0,
            **agg,
            "sentences": [
                {**r, "gold": sorted(list(g) for g in r["gold"]),
                 "write_triple": (list(r["write_triple"])
                                  if r["write_triple"] else None)}
                for r in sent_rows
            ],
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    torch.set_num_threads(1)
    t0 = time.time()
    tau_hat = json.loads(LTT.read_text(encoding="utf-8"))["tau_hat"]
    rep = json.loads((R2_RUNS / "report.json").read_text(encoding="utf-8"))
    tau_single = list(rep["tau_exec_single"])
    res = {
        "exp": 106,
        "panel": str(PANEL),
        "n_sentences": 400,
        "n_gold_triples": N_GOLD_TRIPLES,
        "n_nofact": 245,
        "tau_hat_rung1": tau_hat,
        "tau_exec_single_rung2": tau_single,
        "elapsed_s": 0.0,
    }
    res["ears"] = run_rung1(tau_hat)
    res["ears"].update(run_rung2(a.snapshot, tau_single))
    res["elapsed_s"] = time.time() - t0
    # strip per-sentence detail into a sidecar to keep the main file small
    detail = {k: v.pop("sentences") for k, v in res["ears"].items()}
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    Path(str(a.out).replace(".json", "_sentences.json")).write_text(
        json.dumps(detail, indent=1, ensure_ascii=False), encoding="utf-8")
    for k, v in res["ears"].items():
        print(f"{k}: writes={v['writes']} wrong={v['wrong']} "
              f"correct={v['correct']} nofact_writes={v['nofact_writes']} "
              f"verdicts={v['verdicts']} R1={'PASS' if v['r1_gate_pass'] else 'FAIL'}"
              f"{' (vacuous)' if v['r1_vacuous'] else ''}")
    print(f"elapsed {res['elapsed_s']:.1f}s")


if __name__ == "__main__":
    main()
