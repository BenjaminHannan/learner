#!/usr/bin/env python3
"""Exp 235b -- run the UNCHANGED 235 v3 ear + k-best beams (+ optional gate) over a turns file.

turns.json: [{"id": ..., "turn": str}, ...]   (no gold is sent here)
Per turn: greedy reading (same as 235) with its summed log-prob; then, ONLY when the
brake keeps at least one TEACH frame and the turn does not end in "?", the top-k
beams (k=4). (No TEACH frame -> nothing for the gate to decide; "?" -> guard blocks.)
With --tau the gate itself is applied and timed, so ms = greedy + brake + beams + gate.

python claude_smolear235b_infer.py --ckpt C --base DIR --turns T --out O [--device cuda] [--tau X]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_model as E  # noqa: E402
import claude_smolear235b_beam as B  # noqa: E402


def needs_beams(raw, turn):
    kept, _ = E.brake(E.parse_frames(raw), turn)
    return any(f["act"] == "TEACH" for f in kept) and not B.ends_q(turn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--turns", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--expect-sha", default=None)
    ap.add_argument("--tau", type=float, default=None)
    ap.add_argument("--k", type=int, default=B.K)
    a = ap.parse_args()
    # --ckpt - : read the checkpoint bytes from stdin (streamed from BensPC; keeps the
    # Mac above its 8 GB free-disk floor -- nothing is written to disk)
    blob = sys.stdin.buffer.read() if a.ckpt == "-" else Path(a.ckpt).read_bytes()
    h = hashlib.sha256(blob).hexdigest()
    if a.expect_sha and h != a.expect_sha:
        raise SystemExit(f"checkpoint hash mismatch {h}")
    tok = E.Tok(Path(a.base) / "tokenizer.json")
    m = E.SmolLM()
    from safetensors.torch import load as st_load
    m.load_state_dict(st_load(blob), strict=True)
    del blob
    cuda = a.device == "cuda"
    m = m.to(a.device).to(torch.bfloat16 if cuda else torch.float32).eval()
    gd = E.GraphDecoder(m, tok) if cuda else None
    bg = B.BeamGraph(m, tok, k=a.k) if cuda else None

    def beams(turn):
        return bg.beams(turn) if cuda else B.beam_eager(m, tok, turn, k=a.k)

    def sync():
        if cuda:
            torch.cuda.synchronize()

    B.greedy_scored(m, tok, "Hello there.", gd=gd)  # warm-up, not timed
    beams("Tobble's cat is Fizz.")
    turns = json.loads(Path(a.turns).read_text(encoding="utf-8"))
    out, lat = {}, []
    for t in turns:
        sync()
        t0 = time.perf_counter()
        raw, lp, _ = B.greedy_scored(m, tok, t["turn"], gd=gd)
        sync()
        t1 = time.perf_counter()
        bm = beams(t["turn"]) if needs_beams(raw, t["turn"]) else []
        g = B.gate(t["turn"], raw, lp, bm, a.tau) if a.tau is not None else None
        sync()
        t2 = time.perf_counter()
        ms = (t2 - t0) * 1000
        lat.append(ms)
        rec = dict(raw=raw, greedy_lp=lp, beams=[[x, s] for x, s in bm],
                   ms_greedy=round((t1 - t0) * 1000, 2), ms=round(ms, 2))
        if g is not None:
            rec["gate"] = dict(saved=g["saved"], unsure=g["unsure"], guard=g["guard"])
        out[str(t["id"])] = rec
    summ = dict(n=len(lat), median_ms=statistics.median(lat), p90_ms=sorted(lat)[int(0.9 * len(lat))],
                max_ms=max(lat), n_beamed=sum(1 for r in out.values() if r["beams"]),
                device=a.device, ckpt_sha256=h, torch=torch.__version__, threads=torch.get_num_threads(),
                tau=a.tau, k=a.k, gpu=torch.cuda.get_device_name(0) if cuda else None)
    Path(a.out).write_text(json.dumps(dict(summary=summ, preds=out), indent=1, default=str), encoding="utf-8")
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
