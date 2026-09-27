#!/usr/bin/env python3
"""rd-378g BensPC kit checks (Trustworthy notes thread, 2026-09-27; handoff/kit/rd378gpc). Kit tooling, not sealed
experiment code: it only counts and hashes files the sealed scripts wrote, and prints counts, never text.
  dialogs-hash F   sha256 of F with CRLF made LF must be rd-378u's dialogs59 hash (exit 1 if not)
  dev-check F      claude_rd378_write.py output: dev_turns, dev_unparsed; exit 3 if unparsed > 2% (ADDENDUM-B B2)
  count F          rows and unparsed (notes is null) of a claude_rd378_write.py output, and the median and p90
                   (nearest rank) of its per-turn write ms (report only)
"""
import hashlib
import json
import math
import sys

DIALOGS59 = "1e5d4d3d0a98d8fe4753c90926374debb8efc0f15a927a6297ffe785c80ec109"


def rows(p):
    with open(p, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def main():
    mode, f = sys.argv[1], sys.argv[2]
    if mode == "dialogs-hash":
        h = hashlib.sha256(open(f, "rb").read().replace(b"\r\n", b"\n")).hexdigest()
        ok = h == DIALOGS59
        print(json.dumps({"dialogs59_sha256": h, "matches_rd378u": ok}))
        return 0 if ok else 1
    r = rows(f)
    un = sum(x.get("notes") is None for x in r)
    if mode == "dev-check":
        ok = un <= 0.02 * len(r) and len(r) > 0
        print(json.dumps({"dev_turns": len(r), "dev_unparsed": un, "dev_format_ok": ok}))
        return 0 if ok else 3
    if mode == "count":
        ms = sorted(float(x["ms"]) for x in r if isinstance(x.get("ms"), (int, float)))
        rank = lambda q: ms[max(0, math.ceil(q * len(ms)) - 1)] if ms else None
        print(json.dumps({"rows": len(r), "unparsed": un, "notes": sum(len(x.get("notes") or []) for x in r),
                          "ms_median": rank(0.5), "ms_p90": rank(0.9)}))
        return 0
    print("unknown mode", mode)
    return 2


if __name__ == "__main__":
    sys.exit(main())
