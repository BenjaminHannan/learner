#!/usr/bin/env python3
"""Exp F1 bench driver with 241b's sealed NEW-1 confirm (harness only).

Mirrors scripts/claude_mouth241b_suites.py --scorer241b (read-only,
unchanged): puts the NEW 172b version
(scripts/claude_fix172b241b_benchv3.py, imported unchanged) in sys.modules
under the old name fable_fix172b_benchv3 before fable_suitediff imports it,
so the v3 bench splits of the F1 run confirm case/article-insensitively
(confirm_match). The 292t base runs never use this driver and stay frozen.

Why (pilot evidence, pre-seal): 241b's sealed CONFLICT rendering adds
articles ("the United Kingdom", "a basketball coach"), so the frozen
byte-verbatim confirm needle (`new_val in sent`) misses 10 confirmations
and the driver never sends "yes" (pilot: 10 correct->wrong, confirms
2->1 / 1->0, every one article-only). NEW-1 matches all 10
(case/article-insensitive) and agrees with the frozen needle on 721/721
of 292t's saved conflict replies (S1 anchor). New file only.

Usage:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/claude_f1_suites.py -- <fable_suitediff218 args>
"""

from __future__ import annotations

import sys
import types


def main() -> int:
    if "--" not in sys.argv:
        raise SystemExit("usage: claude_f1_suites.py -- <218 args>")
    rest = sys.argv[sys.argv.index("--") + 1:]
    proxy = types.ModuleType("fable_fix172b_benchv3")

    def _lazy(name):
        import claude_fix172b241b_benchv3 as V3B  # new version, read-only
        return getattr(V3B, name)

    proxy.__getattr__ = _lazy
    sys.modules["fable_fix172b_benchv3"] = proxy
    print("scorer: fable_fix172b_benchv3 -> claude_fix172b241b_benchv3",
          flush=True)
    import fable_suitediff218 as S218  # noqa: E402 (read-only import)
    return S218.main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
