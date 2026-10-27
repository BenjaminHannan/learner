#!/usr/bin/env python3
"""dl-11 launcher (ADDENDUM-1, Fix-sleep thread, 2026-09-27; artifacts/claude-dl11-20260927/ADDENDUM-1.md).
The sealed scripts/claude_dl11_router.py is run UNCHANGED; only its Q TEST draw moves. While checking the generator
(before sealing) I printed the first 8 expressions of the old Q TEST seed 2991, so on the Thread manager's 12:53 UTC
review the run uses a new Q TEST seed, 2981, and also drops those 8 seen expressions from the new draw (1 of them is in
seed 2981's first 400). Everything else (days, P TEST, pool, marks) is as sealed.

  python -B scripts/claude_dl11_run.py --selftest
  python -B scripts/claude_dl11_run.py --model M --out DIR        (the registered run; same flags as the router)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dl11_router as R  # noqa: E402

OLD_Q_TEST_SEED, NEW_Q_TEST_SEED = 2991, 2981
_expressions = R.expressions
SEEN = {e["expr"] for e in _expressions(OLD_Q_TEST_SEED, 8)}


def expressions(seed, n):
    """The sealed generator; on the new Q TEST seed the 8 seen expressions are skipped and more are drawn."""
    if seed % 10000 != NEW_Q_TEST_SEED % 10000:
        return _expressions(seed, n)
    out = [e for e in _expressions(seed, n + len(SEEN)) if e["expr"] not in SEEN]
    return out[:n]


def selftest():
    assert R.Q_TEST_SEED == OLD_Q_TEST_SEED and len(SEEN) == 8
    got = expressions(NEW_Q_TEST_SEED, 500)
    assert len(got) == 500 and not SEEN & {e["expr"] for e in got}
    assert expressions(2800 + 1801, 20) == _expressions(2800 + 1801, 20)
    assert len(SEEN & {e["expr"] for e in _expressions(NEW_Q_TEST_SEED, 500)}) >= 1
    print("dl11 run selftest ok")


def main():
    if "--selftest" in sys.argv:
        R.selftest()
        return selftest()
    R.Q_TEST_SEED = NEW_Q_TEST_SEED
    R.expressions = expressions
    R.main()


if __name__ == "__main__":
    main()
