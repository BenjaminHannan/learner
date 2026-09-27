#!/usr/bin/env python3
"""rd-378g mark G5: the report-only rows ADDENDUM-K lists (Trustworthy notes thread, 2026-09-27). New file.

Not the mark itself: G5's pass/fail comes only from the sealed scripts/claude_rd378g_g5.py score. This adds, from the
same map and judge files, the rows ADDENDUM-K marks "report only": the excluded counts (split by why), the per-kind
shares (chat, overheard), notes per turn and unparsed turns per writer, plus each judge's verdict totals per writer and
the two judges' raw agreement. Prints counts only, never dialog or note text.

python -B scripts/claude_rd378g_g5_report.py --items DIR/items.jsonl --map DIR/map.json --a judge_A.jsonl \
    --b judge_B.jsonl --g notes_G.jsonl --r notes_R.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def rows(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def share(ok, un):
    return round(100 * un / (ok + un), 1) if ok + un else None


def main():
    ap = argparse.ArgumentParser()
    for k in ("items", "map", "a", "b", "g", "r"):
        ap.add_argument("--" + k, required=True)
    a = ap.parse_args()
    mp = json.loads(Path(a.map).read_text(encoding="utf-8"))
    kind = {d["dialog"]: d["kind"] for d in rows(a.items)}
    nnotes = {(d["dialog"], int(t["t"])): len(t["notes"]) for d in rows(a.items) for t in d["turns"] if "notes" in t}
    ja = {(r["dialog"], int(r["t"])): r for r in rows(a.a)}
    jb = {(r["dialog"], int(r["t"])): r for r in rows(a.b)}
    c = Counter()
    for k, n in nnotes.items():
        w, kd = mp[k[0]][0], kind[k[0]]
        c[f"{w}:turns"] += 1
        c[f"{w}:notes"] += n
        c[f"{w}:turns_with_note"] += n > 0
        ra, rb = ja.get(k), jb.get(k)
        if ra is None or rb is None or len(ra["verdicts"]) != n or len(rb["verdicts"]) != n:
            c[f"{w}:turn_mismatch"] += 1
            continue
        for j, r in (("A", ra), ("B", rb)):
            c[f"{w}:missed_gt0_{j}"] += int(r.get("missed", 0) or 0) > 0
            for v in r["verdicts"]:
                c[f"{w}:judge{j}_{v}"] += 1
        for x, y in zip(ra["verdicts"], rb["verdicts"]):
            lab = x if x == y and x in ("ok", "unsupported") else "excluded"
            c[f"{w}:{kd}:{lab}"] += 1
            c[f"{w}:{lab}"] += 1
            if lab == "excluded":
                c[f"{w}:excluded_" + ("same_other_verdict" if x == y else "judges_differ")] += 1
            c[f"{w}:judges_agree"] += x == y
    out = {"counts": dict(sorted(c.items()))}
    out["unsupported_share_pct"] = {w: share(c[f"{w}:ok"], c[f"{w}:unsupported"]) for w in ("G", "R")}
    out["unsupported_share_pct_by_kind"] = {f"{w}:{kd}": share(c[f"{w}:{kd}:ok"], c[f"{w}:{kd}:unsupported"])
                                            for w in ("G", "R") for kd in ("chat", "overheard")}
    out["notes_per_turn"] = {w: round(c[f"{w}:notes"] / c[f"{w}:turns"], 3) if c[f"{w}:turns"] else None
                             for w in ("G", "R")}
    out["unparsed_turns"] = {w: sum(r.get("notes") is None for r in rows(p)) for w, p in (("G", a.g), ("R", a.r))}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
