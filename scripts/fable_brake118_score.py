#!/usr/bin/env python3
"""Exp 118 registered scoring (sealed panels + reading94), Mac CPU, no retraining.

Re-uses the cached per-row inference from exp 95
(artifacts/fable-diag95-20260921/fable_diag95_rows.json); recomputes verdicts
from the raw ears outputs with the ONE change (leftover brake) at the SEALED
taus. No model re-run on sealed panels (only the WordPiece tokenizer re-encodes
texts to recover chspans for span mapping — deterministic, no weights).
Reading94 (400 real sentences, absent from the cache) runs the sealed
checkpoints on the Mac CPU once (inference only).

Run:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_brake118_score.py --out artifacts/fable-brake118-20260922/fable_brake118_results.json
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
import fable_ears47_score as S  # noqa: E402 (sealed decode/verdict logic, read-only)
import fable_ears47_data as D  # noqa: E402 (read-only)
import fable_ears47_encoder as ENC  # noqa: E402 (read-only)
import fable_ears47_model as M  # noqa: E402 (read-only)
import fable_bert_loader as L  # noqa: E402 (tokenizer only)
import fable_brake118_leftover as B  # noqa: E402 (the one change)
import fable_read106_score as R106  # noqa: E402 (reading94 gold logic, read-only)

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "artifacts" / "fable-diag95-20260921" / "fable_diag95_rows.json"
SEALED = REPO / "artifacts" / "fable-ears47-20260921" / "runs" / "report.json"
RUNS = REPO / "artifacts" / "fable-ears47-20260921" / "runs"
PANEL94 = REPO / "data" / "open" / "reading94" / "panel.jsonl"
SNAP = ("/Users/ben-hannan/.cache/huggingface/hub/models--allenai--"
        "scibert_scivocab_uncased/snapshots/24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1")

SEEDS = (4701, 4702, 4703)
TAU_ENS = 0.8766039311885834
TAU_SINGLE = [0.9483702182769775, 0.8766039311885834, 0.9547552053165873]
WRITE_ACTS = {"STATE", "RETRACT"}
TEST6500 = ("t_seen", "t_new", "t_trap", "t_hard")


def parse_of(r, s):
    d = r["seeds"][s]
    f = d["frame"]
    fr = {"act": f["act"], "rel": f["rel"],
          "subj": tuple(f["subj"]) if f["subj"] else None,
          "obj": tuple(f["obj"]) if f["obj"] else None, "dir": f["dir"]}
    return {"frame": fr, "conf": d["conf"], "ok4": d["ok4"], "ok5": d["ok5"],
            "forced_echo": d["forced_echo"]}


def gold_of(r):
    g = r["gold"]
    return {"act": g["act"], "rel": g["rel"],
            "subj": tuple(g["subj"]) if g["subj"] else None,
            "obj": tuple(g["obj"]) if g["obj"] else None, "dir": g["dir"]}


def verdict_ens_braked(ps, tau, text, ch):
    v, fr = S.verdict_ensemble(ps, tau)
    brake = False
    if v == "EXECUTE":
        blk, _, _ = B.leftover_blocks(text, fr, ch)
        if blk:
            brake = True
            v = "ECHO" if _echo_ok(ps) else "REPHRASE"
    return v, fr, brake


def verdict_single_braked(p, tau, text, ch):
    v, fr = S.verdict_single(p, tau)
    brake = False
    if v == "EXECUTE":
        blk, _, _ = B.leftover_blocks(text, fr, ch)
        if blk:
            brake = True
            v = "ECHO" if (p["ok4"] and p["ok5"] and p["conf"] >= S.TAU_ECHO) else "REPHRASE"
    return v, fr, brake


def _echo_ok(ps):
    for i in range(3):
        for j in range(i + 1, 3):
            fi, fj = ps[i]["frame"], ps[j]["frame"]
            if fi["act"] not in S.ABSTAIN and fi["act"] != "?" and S.same_frame(fi, fj):
                maj = [ps[i], ps[j]]
                if all(p["ok4"] and p["ok5"] for p in maj) \
                        and min(p["conf"] for p in maj) >= S.TAU_ECHO:
                    return True
    return False


def score_cached_panel(rows, ch_of, tau_ens, tau_singles):
    """Full mark quantities with brake, ensemble + singles."""
    out = {"n": len(rows)}
    ens = {"correct": 0, "executed": 0, "echoed": 0, "silent": 0, "echo_wrong": 0,
           "exec_correct_stmt": 0, "exec_state_fact": 0, "exec_retract": 0,
           "wrong_exec_ask": 0, "brake_fires": 0, "verdicts": Counter(),
           "silent_examples": []}
    sng = [{"correct": 0, "executed": 0, "echoed": 0, "silent": 0, "echo_wrong": 0,
            "exec_correct_stmt": 0, "wrong_exec_ask": 0, "brake_fires": 0,
            "verdicts": Counter()} for _ in range(3)]
    for r in rows:
        g = gold_of(r)
        ch = ch_of[r["n"]]
        ps = [parse_of(r, s) for s in range(3)]
        v, fr, br = verdict_ens_braked(ps, tau_ens, r["text"], ch)
        ens["verdicts"][v] += 1
        ens["brake_fires"] += int(br)
        ens["correct"] += int(S.is_correct(g, v, fr, ps))
        if v == "EXECUTE":
            ens["executed"] += 1
            if fr is not None and fr["act"] == "STATE":
                ens["exec_state_fact"] += 1
            if fr is not None and fr["act"] == "RETRACT":
                ens["exec_retract"] += 1
            if g["act"] == "STATE" and fr is not None and S.same_frame(fr, g):
                ens["exec_correct_stmt"] += 1
            if fr is not None and fr["act"] in WRITE_ACTS \
                    and (g["act"] == "?" or not S.same_frame(fr, g)):
                ens["silent"] += 1
                if len(ens["silent_examples"]) < 50:
                    ens["silent_examples"].append({"n": r["n"], "family": r["family"],
                                                   "utterance": r["text"],
                                                   "gold_act": g["act"], "got": fr})
            if fr is not None and fr["act"] == "ASK" \
                    and (g["act"] == "?" or not S.same_frame(fr, g)):
                ens["wrong_exec_ask"] += 1
        elif v == "ECHO":
            ens["echoed"] += 1
            if fr is not None and fr["act"] in WRITE_ACTS \
                    and (g["act"] == "?" or not S.same_frame(fr, g)):
                ens["echo_wrong"] += 1
        for s in range(3):
            vs, frs, brs = verdict_single_braked(ps[s], tau_singles[s], r["text"], ch)
            q = sng[s]
            q["verdicts"][vs] += 1
            q["brake_fires"] += int(brs)
            q["correct"] += int(S.is_correct(g, vs, frs, None))
            if vs == "EXECUTE":
                q["executed"] += 1
                if g["act"] == "STATE" and frs is not None and S.same_frame(frs, g):
                    q["exec_correct_stmt"] += 1
                if frs is not None and frs["act"] in WRITE_ACTS \
                        and (g["act"] == "?" or not S.same_frame(frs, g)):
                    q["silent"] += 1
                if frs is not None and frs["act"] == "ASK" \
                        and (g["act"] == "?" or not S.same_frame(frs, g)):
                    q["wrong_exec_ask"] += 1
            elif vs == "ECHO":
                q["echoed"] += 1
                if frs is not None and frs["act"] in WRITE_ACTS \
                        and (g["act"] == "?" or not S.same_frame(frs, g)):
                    q["echo_wrong"] += 1
    ens["verdicts"] = dict(ens["verdicts"])
    for q in sng:
        q["verdicts"] = dict(q["verdicts"])
    out["ensemble"] = ens
    out["single"] = sng
    return out


def run_reading94(tau_singles):
    """Inference on the 400-sentence reading94 panel (absent from cache)."""
    torch.set_num_threads(1)
    enc0, tok, _ = ENC.load(SNAP)
    del enc0
    unk_ids = {tok.unk}
    panel = [json.loads(l) for l in PANEL94.read_text(encoding="utf-8").splitlines()]
    rows = [{"text": r["sentence"],
             "gold47": {"act": "NO_FACT", "rel": "UNSURE", "subj": None,
                        "obj": None, "dir": 0, "rep": False}} for r in panel]
    encs = [D.encode_row(r, tok) for r in rows]
    assert all(e is not None for e in encs)
    device = torch.device("cpu")
    per_seed = {}
    for si, s in enumerate(SEEDS):
        ck = torch.load(RUNS / f"c-{s}" / "ear.pt", map_location="cpu",
                        weights_only=False)
        enc, _, _ = ENC.load(SNAP)
        m = M.FrameEars(enc, D.N_REL, freeze_layers=ck.get("freeze_layers", 0))
        m.load_state_dict(ck["state"])
        m.eval()
        P = S.probs_for_model(m, encs, device, batch=64)
        parses = [S.decode(rows[i], encs[i], P[i], unk_ids) for i in range(len(rows))]
        del m, P
        import gc
        gc.collect()
        sent = []
        for i, prow in enumerate(panel):
            gs = R106.gold_set(prow)
            utt = prow["sentence"]
            ch = encs[i]["chspans"]
            p = parses[i]
            fr = {"act": p["frame"]["act"], "rel": p["frame"]["rel"],
                  "subj": tuple(p["frame"]["subj"]) if p["frame"]["subj"] else None,
                  "obj": tuple(p["frame"]["obj"]) if p["frame"]["obj"] else None,
                  "dir": p["frame"]["dir"]}
            pp = {"frame": fr, "conf": p["conf"], "ok4": p["ok4"],
                  "ok5": p["ok5"], "forced_echo": p["forced_echo"]}
            v0, _ = S.verdict_single(pp, tau_singles[si])
            v1, _, br = verdict_single_braked(pp, tau_singles[si], utt, ch)
            wt0 = R106.r2_triple_of(
                {"act": fr["act"], "rel": fr["rel"],
                 "subj": list(fr["subj"]) if fr["subj"] else None,
                 "obj": list(fr["obj"]) if fr["obj"] else None},
                utt, ch) if v0 == "EXECUTE" else None
            wt1 = R106.r2_triple_of(
                {"act": fr["act"], "rel": fr["rel"],
                 "subj": list(fr["subj"]) if fr["subj"] else None,
                 "obj": list(fr["obj"]) if fr["obj"] else None},
                utt, ch) if v1 == "EXECUTE" else None
            sent.append({
                "id": prow["id"], "nofact": len(gs) == 0,
                "v_nobrake": v0, "v_brake": v1, "brake": br,
                "w0": list(wt0) if wt0 else None, "w1": list(wt1) if wt1 else None,
                "m0": (wt0 in gs) if wt0 else None, "m1": (wt1 in gs) if wt1 else None,
            })
        per_seed[str(s)] = sent
    return per_seed


def agg_writes(sent, which):
    writes = sum(1 for r in sent if r[which] is not None)
    correct = sum(1 for r in sent if r[which] is not None and r["m" + which[1:]])
    wrong = writes - correct
    nofact_writes = sum(1 for r in sent if r[which] is not None and r["nofact"])
    return {"writes": writes, "right": correct, "wrong": wrong,
            "nofact_writes": nofact_writes}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0 = time.time()
    torch.set_num_threads(1)
    Dcache = json.loads(CACHE.read_text(encoding="utf-8"))
    sealed = json.loads(SEALED.read_text(encoding="utf-8"))
    tok = L.WordPiece(SNAP + "/vocab.txt")

    panels = {}
    for pname, pd in Dcache["panels"].items():
        rows = pd["rows"]
        ch_of = {r["n"]: tok.encode(r["text"], 96)[1] for r in rows}
        panels[pname] = score_cached_panel(rows, ch_of, TAU_ENS, TAU_SINGLE)

    # corrected execution bar inputs (verify doc-95 integers from cache)
    seen_state = [r for r in Dcache["panels"]["t_seen"]["rows"] if r["gold"]["act"] == "STATE"]
    seen_concrete = [r for r in seen_state if r["gold"]["rel"] not in (None, "OPEN", "UNSURE")]
    seen_open = [r for r in seen_state if r["gold"]["rel"] in ("OPEN", "UNSURE", None)]
    new_state = [r for r in Dcache["panels"]["t_new"]["rows"] if r["gold"]["act"] == "STATE"]
    exec_bar = {"n_state_seen": len(seen_state), "n_concrete_seen": len(seen_concrete),
                "n_open_seen": len(seen_open), "n_state_new": len(new_state)}

    # B3 reference: exp47 own numbers (sealed report)
    ref = {}
    for pname in ("t_seen", "t_new"):
        ref[pname] = {
            "ensemble_exec_stmt": sealed["marks"][
                "R2-SEEN" if pname == "t_seen" else "R2-NEW"]["exec_correct_stmt"],
            "ensemble_executed": sealed["panels"][pname]["ensemble"]["executed"],
            "single_exec_state_gold": [
                sealed["panels"][pname]["single"][s]["exec_state_gold"] for s in range(3)],
            "single_executed": [
                sealed["panels"][pname]["single"][s]["executed"] for s in range(3)],
        }

    r94 = run_reading94(TAU_SINGLE)
    r94_agg = {}
    for s in ("4701", "4702", "4703"):
        r94_agg[s] = {"brake": agg_writes(r94[s], "w1"),
                      "nobrake_context": agg_writes(r94[s], "w0"),
                      "brake_fires": sum(1 for r in r94[s] if r["brake"])}

    out = {"taus": {"ensemble": TAU_ENS, "singles": TAU_SINGLE},
           "panels": panels, "exec_bar_check": exec_bar, "exp47_ref": ref,
           "reading94_per_seed": r94_agg,
           "reading94_sentences": r94,
           "timing_s": round(time.time() - t0, 1)}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({p: {"ens": panels[p]["ensemble"]["executed"],
                          "silent": panels[p]["ensemble"]["silent"],
                          "correct": panels[p]["ensemble"]["correct"]}
                      for p in panels}, indent=1))
    print("exec_bar_check", exec_bar)
    print("reading94", json.dumps(r94_agg, indent=1))
    print("WROTE %s in %.0fs" % (a.out, time.time() - t0))


if __name__ == "__main__":
    main()
