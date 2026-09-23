#!/usr/bin/env python3
"""Exp 235 -- run the frozen SmolLM ear checkpoint over a turns file.

turns.json: [{"id": ..., "turn": str}, ...]  (no gold labels are sent here)
Writes preds.json: {id: {"raw": str, "ms": float}} + a latency summary.
The brake is applied later by the scorer (same code, claude_smolear235_model.brake);
the timing here INCLUDES parse + brake so M5 measures the full ear.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--base", required=True, help="dir with tokenizer.json")
    ap.add_argument("--turns", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--expect-sha", default=None)
    a = ap.parse_args()
    ck = Path(a.ckpt)
    h = hashlib.sha256(ck.read_bytes()).hexdigest()
    if a.expect_sha and h != a.expect_sha:
        raise SystemExit(f"checkpoint hash mismatch {h}")
    tok = E.Tok(Path(a.base) / "tokenizer.json")
    m = E.SmolLM()
    from safetensors.torch import load_file
    sd = load_file(str(ck))
    m.load_state_dict(sd, strict=True)
    dt = torch.bfloat16 if a.device == "cuda" else torch.float32
    m = m.to(a.device).to(dt).eval()
    turns = json.loads(Path(a.turns).read_text(encoding="utf-8"))
    if a.device == "cuda":
        gd = E.GraphDecoder(m, tok)
        gen = gd.generate
    else:
        def gen(turn):
            return E.generate(m, tok, turn, device=a.device)
    # warm-up (not timed, not a panel turn)
    gen("Hello there.")
    out, lat = {}, []
    for t in turns:
        if a.device == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        raw = gen(t["turn"])
        E.brake(E.parse_frames(raw), t["turn"])
        if a.device == "cuda":
            torch.cuda.synchronize()
        ms = (time.perf_counter() - t0) * 1000
        lat.append(ms)
        out[str(t["id"])] = {"raw": raw, "ms": round(ms, 2)}
    summ = dict(n=len(lat), median_ms=statistics.median(lat), p90_ms=sorted(lat)[int(0.9 * len(lat))],
                max_ms=max(lat), device=a.device, ckpt_sha256=h, torch=torch.__version__,
                threads=torch.get_num_threads(),
                gpu=torch.cuda.get_device_name(0) if a.device == "cuda" else None)
    Path(a.out).write_text(json.dumps(dict(summary=summ, preds=out), indent=1), encoding="utf-8")
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
