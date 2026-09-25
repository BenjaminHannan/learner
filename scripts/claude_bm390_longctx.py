#!/usr/bin/env python3
"""Long-prompt memory check for bm-390's whole-chat arms (benchmarks thread, 2026-09-25). New file only.

A check, not a benchmark: the prompt is made up (a fictional diary, no benchmark text). It loads a model exactly as
bm-390's plain arms do (claude_bm390.plain_model: same dtype, same device, same chat template, greedy), builds a
prompt of about --tokens tokens, generates 4 tokens, and prints one JSON line: prompt tokens, peak GPU memory,
seconds, and how many attention calls asked PyTorch for grouped-query attention (enable_gqa=True; with the flash
kernel missing those go to the math kernel, which caused T's out-of-memory error in RESULTS-benspc3.md).

  python -B scripts/claude_bm390_longctx.py --model DIR [--tokens 27000] [--gqa-off]

--gqa-off installs scripts/claude_gqa_wrap.py's change first (transformers repeats key/value heads itself).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

NAMES = ("Wren Ashdown", "Tobin Marle", "Ilsa Fenwick", "Corin Vale")
PLACES = ("Oakvale", "Brindle Cove", "Harrowgate", "Millbrook")


def diary(i: int) -> str:
    who, other = NAMES[i % 4], NAMES[(i + 1) % 4]
    return (f"[Day {i}] {who}: I walked to {PLACES[i % 4]} and planted {i % 9 + 2} rows of beans. "
            f"{other}: Did the rain on day {i // 3} hold off long enough?\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tokens", type=int, default=27000)
    ap.add_argument("--gqa-off", action="store_true")
    a = ap.parse_args()
    if a.gqa_off:
        import claude_gqa_wrap
        claude_gqa_wrap.apply()
    import torch
    import torch.nn.functional as F
    import claude_bm390 as B

    calls = {"sdpa": 0, "enable_gqa": 0}
    real = F.scaled_dot_product_attention

    def counting(*args, **kwargs):
        calls["sdpa"] += 1
        calls["enable_gqa"] += int(bool(kwargs.get("enable_gqa", False)))
        return real(*args, **kwargs)

    F.scaled_dot_product_attention = counting
    tok, _, dev, ctx = B.plain_model(a.model)
    lines, n, i = [], 0, 0
    while n < a.tokens:
        lines += [diary(i + k) for k in range(200)]
        i += 200
        user = "".join(lines) + B.QA_PROMPT.format("How many rows of beans were planted on day 7?")
        n = int(B._ids(tok, B.LOCOMO_SYSTEM, user)["input_ids"].shape[1])
    out = {"model": os.path.basename(os.path.normpath(a.model)), "device": dev, "context": ctx,
           "prompt_tokens": n, "gqa_off": a.gqa_off}
    if dev == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    try:
        reply, _ = B.generate(a.model, B.LOCOMO_SYSTEM, user, 4)
        out.update(ok=True, reply_chars=len(reply))
    except Exception as exc:  # noqa: BLE001
        out.update(ok=False, error=f"{type(exc).__name__}: {str(exc)[:300]}")
    out["seconds"] = round(time.time() - t0, 2)
    if dev == "cuda":
        out["peak_gib"] = round(torch.cuda.max_memory_allocated() / 2 ** 30, 2)
    out.update(sdpa_calls=calls["sdpa"], sdpa_enable_gqa_calls=calls["enable_gqa"])
    print(json.dumps(out), flush=True)
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
