#!/usr/bin/env python3
"""Exp 241b S1 -- anchor identity check for the one new scorer version.

New version: scripts/claude_fix172b241b_benchv3.py (replaces
scripts/fable_fix172b_benchv3.py for the 241b suite run only). Its only
difference is the confirm decision inside run_item_v3:
    frozen:  new_val and new_val in sent
    new:     new_val and confirm_match(new_val, sent)
Everything after that decision (the question turn, B.classify_v2, the row
fields) is the same code. So on a saved row the new version gives the old
verdict exactly when (1) every teach turn gets the same confirm decision
(then the driver sends exactly the same turns) and (2) the saved verdict
is what B.classify_v2 gives on the saved reply.

For every saved protocol-v3 bench row (rows carrying "confirms") under the
given roots, this script pairs each saved teach reply with its taught
sentence (from the bench item files), computes both decisions with the
REAL functions (frozen confirm_value + both matchers), checks the frozen
decisions reproduce the saved "confirms" count, and re-classifies the
saved reply. Protocol-v2 rows (no "confirms") are scored by B.run_item,
which no new version replaces; they are counted and skipped.

Usage: uv ... python -B scripts/claude_mouth241b_s1.py --label L ROOT...
Exit 0 = 100 % identical, 1 = any difference (all listed).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
REPO = SCRIPTS.parent

import fable_bench121_run as B  # noqa: E402 (read-only)
import fable_fix172b_benchv3 as V3OLD  # noqa: E402 (frozen, read-only)
import claude_fix172b241b_benchv3 as V3NEW  # noqa: E402 (new version)
import fable_suitediff as SD  # noqa: E402 (split table, read-only)


def _split_items() -> dict:
    """split tag -> {item id: item}, and filename fragments per split."""
    out = {}
    for stag, pathmark, frags in SD.BENCH_SPLITS:
        path = B.DATA_NEW if pathmark == "DATA_NEW" else (
            B.DATA_OLD if pathmark == "DATA_OLD" else Path(pathmark))
        items = {}
        for line in Path(str(path)).read_text(encoding="utf-8").splitlines():
            if line.strip():
                it = json.loads(line)
                items[str(it["id"])] = it
        out[stag] = (frags, items)
    return out


def _rows(p: Path) -> list:
    txt = p.read_text(encoding="utf-8").strip()
    if not txt:
        return []
    if txt[0] == "[":
        rows = json.loads(txt)
    else:
        rows = [json.loads(x) for x in txt.splitlines() if x.strip()]
    return SD.unwrap_rows(rows) if hasattr(SD, "unwrap_rows") else rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("roots", nargs="+")
    a = ap.parse_args(argv)
    splits = _split_items()
    n = Counter()
    diffs = []
    for root in a.roots:
        for p in sorted(Path(root).rglob("*rows.json*")):
            stag = None
            for s, (frags, _items) in splits.items():
                if any(f in p.name for f in frags):
                    stag = s if stag is None or len(s) > len(stag) else stag
            if stag is None:
                continue
            items = splits[stag][1]
            for r in _rows(p):
                if not isinstance(r, dict) or "verdict" not in r:
                    continue
                if "confirms" not in r:
                    n["v2 rows (not replaced)"] += 1
                    continue
                n["v3 rows"] += 1
                it = items.get(str(r.get("id")))
                if it is None:
                    diffs.append((str(p), r.get("id"), "item not found"))
                    continue
                sents = [str(t["sentence_en"]) for t in it["taught"]]
                reps = list(r.get("teach_replies") or [])
                if len(reps) != len(sents):
                    diffs.append((str(p), r["id"], "teach reply count",
                                  len(reps), len(sents)))
                    continue
                old_c = 0
                for rep, sent in zip(reps, sents):
                    nv = V3OLD.confirm_value(rep)
                    if not nv:
                        continue
                    n["needle replies"] += 1
                    old = bool(nv and nv in sent)
                    new = bool(nv and V3NEW.confirm_match(nv, sent))
                    old_c += old
                    if old != new:
                        diffs.append((str(p), r["id"], "confirm decision",
                                      rep, sent, old, new))
                if old_c != int(r["confirms"]):
                    diffs.append((str(p), r["id"], "frozen decisions do not "
                                  "reproduce saved confirms", old_c,
                                  r["confirms"]))
                golds = [str(g) for g in list(it.get("gold", []))
                         + list(it.get("gold_aliases", []))]
                v, _e, _c = B.classify_v2(r.get("reply", ""), golds)
                if v != r["verdict"]:
                    diffs.append((str(p), r["id"], "verdict re-classify",
                                  r["verdict"], v))
                else:
                    n["v3 rows verdict reproduced"] += 1
    ok = not diffs
    print(f"S1 [{a.label}]: {dict(n)}; differences {len(diffs)}")
    for d in diffs:
        print("  DIFF", d)
    print(f"S1 [{a.label}]", "PASS (100% identical)" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
