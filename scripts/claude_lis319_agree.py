#!/usr/bin/env python3
"""lis-319 key audit: claude_lis300_agree with the dialog's earlier turns visible to the compiler.

History rows resolve owners from earlier turns ("she" -> Nino, named 3 turns back). The plain
compiler only sees turn + prev_reply, so such owners fail owner_not_span in BOTH labels and the
rows would "agree" by writing nothing. Here the compiler's prev text is the dialog's earlier user
turns and replies (all of them, oldest first) followed by prev_reply, so the same checks apply
with history. Everything else (match rules, act, ask) is claude_lis300_agree's.

python claude_lis319_agree.py --a A.jsonl --b B.jsonl --out AGREED_IDS.txt [--report REPORT.json]
A rows {"id": "<dialog>-t<k>", "turn", "prev_reply", "frame", "family"}; B rows {"id","frame"}.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_agree import key  # noqa: E402
from claude_lis300_compiler import compile_frame  # noqa: E402
from claude_lis300_score import ask_ok  # noqa: E402


def with_history(rows):
    """id -> prev text = earlier user turns and replies of the dialog + prev_reply."""
    dialogs = defaultdict(list)
    for r in rows:
        d, t = r["id"].rsplit("-t", 1)
        dialogs[d].append((int(t), r))
    out = {}
    for d, items in dialogs.items():
        items.sort(key=lambda x: x[0])
        lines = []
        for k, (_, r) in enumerate(items):
            prev = r.get("prev_reply", "") or ""
            out[r["id"]] = "\n".join(lines + [prev])
            lines.append(r["turn"])
            nxt = items[k + 1][1].get("prev_reply", "") if k + 1 < len(items) else ""
            if nxt:
                lines.append(nxt)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    x = ap.parse_args()
    rowsA = [json.loads(l) for l in Path(x.a).read_text().splitlines() if l.strip()]
    A = {r["id"]: r for r in rowsA}
    B = {r["id"]: r for r in map(json.loads, Path(x.b).read_text().splitlines()) if r}
    prevs = with_history(rowsA)
    agreed, why, fam, fam_n = [], Counter(), Counter(), Counter()
    for i, ra in A.items():
        fam_n[ra.get("family", "?")] += 1
        rb = B.get(i)
        if not rb or not isinstance(rb.get("frame"), dict):
            why["missing"] += 1
            fam[ra.get("family", "?")] += 1
            continue
        t, p = ra["turn"], prevs[i]
        da, db = compile_frame(ra["frame"], t, p), compile_frame(rb["frame"], t, p)
        reasons = []
        if sorted(map(key, da["write"])) != sorted(map(key, db["write"])):
            reasons.append("writes")
        if bool(da["ask_whose"]) != bool(db["ask_whose"]):
            reasons.append("whose")
        if ra["frame"].get("act") != rb["frame"].get("act"):
            reasons.append("act")
        if ra["frame"].get("act") == "ASK" and rb["frame"].get("act") == "ASK" and \
                not ask_ok(rb["frame"].get("ask"), ra["frame"].get("ask") or {}):
            reasons.append("ask")
        if reasons:
            for r in reasons:
                why[r] += 1
            fam[ra.get("family", "?")] += 1
        else:
            agreed.append(i)
    Path(x.out).write_text("\n".join(agreed) + "\n")
    rep = {"rows": len(A), "agreed": len(agreed), "disagree_reasons": dict(why),
           "agreed_by_family": {f: fam_n[f] - fam[f] for f in sorted(fam_n)},
           "rows_by_family": dict(sorted(fam_n.items()))}
    if x.report:
        Path(x.report).write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
