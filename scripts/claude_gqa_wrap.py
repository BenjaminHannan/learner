#!/usr/bin/env python3
"""Keep long-prompt attention off PyTorch's slow "math" path (benchmarks thread, 2026-09-25). New file only.

Why: in bm-390's third attempt (RESULTS-benspc3.md) the plain MiniCPM5-1B arm T ran out of GPU memory on its first
whole-chat prompt: "Tried to allocate 4.62 GiB" inside scaled_dot_product_attention. transformers 5.x passes
grouped-query attention (GQA) straight to PyTorch (enable_gqa=True) when there is no attention mask. PyTorch's
memory-efficient kernel does not take enable_gqa, so a machine without the flash kernel (BensPC, Windows) falls back
to the math kernel, which builds the full heads x L x L score matrix (L = 14k-27k tokens for a whole LoCoMo chat).

What: before the next script starts, transformers' use_gqa_in_sdpa is replaced by a function that returns False.
transformers then repeats the key/value heads itself (repeat_kv, its own code path for masks and older PyTorch) and
calls scaled_dot_product_attention without enable_gqa, so the memory-efficient kernel can run. The attention
computed is the same; only the kernel, and so the last bits of floating point, can differ. Nothing else changes.

  python -B scripts/claude_gqa_wrap.py scripts/claude_bm390.py locomo --arm plain:BASE ...

It composes with the other wrappers (each runs the next script with runpy). Checked by
scripts/claude_bm390_longctx.py (peak GPU memory on a made-up long prompt, with and without this wrapper).
"""
from __future__ import annotations

import runpy
import sys


def _never(*_args, **_kwargs) -> bool:
    return False


def apply() -> None:
    import transformers.integrations.sdpa_attention as sa
    sa.use_gqa_in_sdpa = _never


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: claude_gqa_wrap.py <script.py> [args]")
    target = sys.argv[1]
    sys.argv = [target] + sys.argv[2:]
    apply()
    print("gqa-wrap: transformers repeats key/value heads itself (use_gqa_in_sdpa -> False)", flush=True)
    runpy.run_path(target, run_name="__main__")


if __name__ == "__main__":
    main()
