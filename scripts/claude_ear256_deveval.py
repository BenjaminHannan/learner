#!/usr/bin/env python3
"""Exp 256 step 1 -- 235's dev split (the same 800 sampled rows as 235's dev_eval.json) on the Mac.

Greedy + brake, exact-frame match with 235's own frames_equal/as_line. Also compares
the Mac raw text with 235's GPU raw text row by row.
python claude_ear256_deveval.py --ckpt C --threads N --out O [--limit N]
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_model as E  # noqa: E402
import claude_smolear235_train as T  # noqa: E402
from claude_ear256_ear import Ear, REPO  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--expect-sha", default=None)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ear = Ear(a.ckpt, expect_sha=a.expect_sha, threads=a.threads)
    rows = json.loads((REPO / "artifacts/claude-smolear235-20260922/train/dev_eval.json").read_text())["rows"]
    if a.limit:
        rows = rows[:a.limit]
    res, lat = [], []
    for r in rows:
        t0 = time.perf_counter()
        raw = E.generate(ear.m, ear.tok, r["turn"])
        kept, _ = E.brake(E.parse_frames(raw), r["turn"])
        lat.append((time.perf_counter() - t0) * 1000)
        kl = [T.as_line(f) for f in kept]
        res.append(dict(turn=r["turn"], family=r["family"], raw=raw, gpu_raw=r["raw"],
                        ok=T.frames_equal(kl, r["gold"]), gpu_ok=r["ok"], same_raw=raw == r["raw"],
                        ms=round(lat[-1], 1)))
    fam = {}
    for x in res:
        fam.setdefault(x["family"], [0, 0])
        fam[x["family"]][0] += x["ok"]
        fam[x["family"]][1] += 1
    lat_s = sorted(lat)
    summ = dict(n=len(res), mac_exact=sum(x["ok"] for x in res), gpu_exact=sum(x["gpu_ok"] for x in res),
                same_raw=sum(x["same_raw"] for x in res), by_family=fam, threads=torch.get_num_threads(),
                median_ms=statistics.median(lat), p95_ms=lat_s[int(0.95 * len(lat_s))], max_ms=lat_s[-1],
                ckpt_sha256=ear.sha, torch=torch.__version__)
    Path(a.out).write_text(json.dumps(dict(summary=summ, rows=res), indent=1))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
