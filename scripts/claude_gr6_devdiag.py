#!/usr/bin/env python3
"""gr-6 dev FAIL, where the misses are (Plain-English puzzles thread, 2026-09-27). Post hoc, practice data only, report
only: it gates nothing and no panel is read. The copy is claude_gr5.Copier5 with the gr-6 adapter, exactly as
`claude_gr6.py dev` runs it (greedy, so it repeats the dev step's outputs).

For every held-out square (split "dev") and every dev-only-layout square (split "devlayout") in gr-6's training rows,
it writes one line per row (kind, layout, size, exact / wrong / none, and for a wrong grid its size) and prints counts
by source (gr-5's rows vs the new layouts), by layout and by layout feature (rows on one line, header, divider).

  python -B scripts/claude_gr6_devdiag.py --model BASE --rows ROWS.jsonl --layouts LAYOUTS.json --adapter A.pt --out O.jsonl
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

import claude_gr5 as G5  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("model", "rows", "layouts", "adapter", "out"):
        ap.add_argument("--" + k, required=True)
    a = ap.parse_args()
    lay = {r["id"]: r for r in json.loads(Path(a.layouts).read_text(encoding="utf-8"))}
    rows = [r for r in G5._load(a.rows) if r["grid"] is not None and r["split"] in ("dev", "devlayout")]
    cp = G5.Copier5(G5.load(a.model, a.adapter), plain=False)
    st, out = Counter(), []
    for r in rows:
        g = cp.copy(r["text"])["grid"]
        res = "exact" if g == r["grid"] else ("none" if g is None else "wrong")
        rc = lay.get(r.get("layout", ""), {})
        feats = []
        if rc:
            feats.append("oneline" if rc["row_join"] in (" / ", "; ") else "lines")
            feats += ["header"] if rc["header"] != "none" else []
            feats += ["divider"] if rc.get("divider") else []
        src = "gr5rows" if r["kind"] not in ("sq_new", "sq_devlayout") else r["kind"]
        s = len(r["grid"])
        row = {"src": src, "split": r["split"], "layout": r.get("layout", ""), "size": s, "res": res,
               "got_size": None if g is None else len(g), "feats": feats}
        out.append(row)
        for key in [src, f"{src}_size{s}"] + [f"{src}_{f}" for f in feats]:
            st[f"{key}_n"] += 1
            st[f"{key}_{res}"] += 1
        if res == "wrong":
            st[f"{src}_wrong_" + ("same_size" if len(g) == s else ("larger" if len(g) > s else "smaller"))] += 1
    Path(a.out).write_text("".join(json.dumps(x) + "\n" for x in out), encoding="utf-8")
    by_layout = Counter()
    for x in out:
        if x["layout"]:
            by_layout[(x["layout"], x["res"])] += 1
    print(json.dumps(dict(sorted(st.items()))))
    print(json.dumps({f"{k[0]}_{k[1]}": v for k, v in sorted(by_layout.items())}))


if __name__ == "__main__":
    main()
