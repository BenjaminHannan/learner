#!/usr/bin/env python3
"""Exp 252 M6 / M5 checker (read-only).

m6: claude_corr252_m6check.py m6 <base138k-probe.json> <mine-probe.json> ...
    (pairs: base, mine, base, mine ...)
  - ghost answer: after a dialog's first __RESTART__, a non-write reply of
    the shape "S's R is V." or "V is the R of S." whose (S, V) pair is in
    no audit truth of that dialog (case-insensitive). Counted per arm.
  - failed duplicate check: any audit with dup_ok false.
  - reply moves: turn replies that differ between base and mine (by
    dialog index and turn index). Predicted list for 252: none.
m5: claude_corr252_m6check.py m5 <lat-k-*.json ...> -- <lat-252-*.json ...>
  - median of the per-run medians per arm; bar: mine - base <= 5 ms.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

POS = [re.compile(r"^(?P<s>[A-Z][\w-]*)'s (?P<r>[a-z ]+?) is (?P<v>.+?)\.?$"),
       re.compile(r"^(?P<v>.+?) is the (?P<r>[a-z ]+?) of (?P<s>[A-Z][\w-]*)"
                  r"\.?$")]
WRITE = ("saved:", "updated:", "ok,", "ok.", "okay", "i don't", "i do not")


def ghosts(row: dict) -> list[str]:
    pairs = set()
    for a in row.get("audits", []):
        for t in a.get("truth", []) + a.get("fast", []):
            pairs.add((str(t[0]).lower(), str(t[2]).lower()))
    for t in row.get("stored", []):
        pairs.add((str(t[0]).lower(), str(t[2]).lower()))
    out, after = [], False
    for t in row["turns"]:
        if t["turn"] == "__RESTART__":
            after = True
            continue
        rep = (t.get("reply") or "").strip()
        if not after or rep.lower().startswith(WRITE):
            continue
        for rx in POS:
            m = rx.match(rep)
            if m:
                s, v = m.group("s").lower(), m.group("v").lower()
                vals = [x.strip() for x in re.split(r",\s*|\s+and\s+", v)]
                for x in vals:
                    if x and (s, x) not in pairs:
                        out.append(f"{t['turn']!r} -> {rep!r}")
    return out


def m6(paths: list[str]) -> int:
    tot = {"ghost_base": 0, "ghost_mine": 0, "dup_fail_base": 0,
           "dup_fail_mine": 0, "reply_moves": 0, "rows_base": 0,
           "rows_mine": 0}
    for bp, mp in zip(paths[0::2], paths[1::2]):
        b = json.loads(Path(bp).read_text(encoding="utf-8"))["rows"]
        m = json.loads(Path(mp).read_text(encoding="utf-8"))["rows"]
        tot["rows_base"] += len(b)
        tot["rows_mine"] += len(m)
        for arm, rows in (("base", b), ("mine", m)):
            for r in rows:
                g = ghosts(r)
                tot[f"ghost_{arm}"] += len(g)
                for x in g:
                    print(f"GHOST {arm} {Path(bp if arm == 'base' else mp).name}"
                          f" d{r.get('dialog')}: {x}")
                tot[f"dup_fail_{arm}"] += sum(not a.get("dup_ok", False)
                                              for a in r.get("audits", []))
        for i, (rb, rm) in enumerate(zip(b, m)):
            for j, (tb, tm) in enumerate(zip(rb["turns"], rm["turns"])):
                if tb.get("reply") != tm.get("reply") \
                        or tb.get("turn") != tm.get("turn"):
                    tot["reply_moves"] += 1
                    print(f"MOVE {Path(mp).name} d{i} t{j}: {tb['turn']!r}: "
                          f"{tb.get('reply')!r} -> {tm.get('reply')!r}")
            if rb.get("stored") != rm.get("stored"):
                tot["reply_moves"] += 1
                print(f"STORE-MOVE {Path(mp).name} d{i}")
    tot["M6_pass"] = (tot["ghost_mine"] == 0 and tot["dup_fail_mine"] == 0
                      and tot["reply_moves"] == 0
                      and tot["rows_base"] == tot["rows_mine"])
    print(json.dumps(tot, indent=1))
    return 0


def m5(args: list[str]) -> int:
    k = args.index("--")
    med = {}
    for arm, ps in (("base", args[:k]), ("mine", args[k + 1:])):
        meds = [json.loads(Path(p).read_text())["median_ms"] for p in ps]
        med[arm] = {"runs": meds, "median": statistics.median(meds)}
    med["added_ms"] = med["mine"]["median"] - med["base"]["median"]
    med["M5_pass"] = med["added_ms"] <= 5.0
    print(json.dumps(med, indent=1))
    return 0


if __name__ == "__main__":
    mode = sys.argv[1]
    sys.exit(m6(sys.argv[2:]) if mode == "m6" else m5(sys.argv[2:]))
