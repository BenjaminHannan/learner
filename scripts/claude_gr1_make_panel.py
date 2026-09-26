#!/usr/bin/env python3
"""gr-1 blind TEST panel maker (Plain-English puzzles thread, 2026-09-26). Prints counts only, never panel text.

A blind writer that saw no reader code wrote 30 wrappers (chat messages with a {rows} slot, sometimes {s}) and 40
lookalikes (chat messages with numbers in rows that do not ask for a number square); see /tmp/blind_gr1/writings.json.
This script fills the wrappers with 100 fresh squares and writes the panel:
  squares.jsonl     {"id", "text", "size", "grid", "broken", "layout", "wrapper_id"}   grid = the inserted square
  lookalikes.jsonl  {"id", "text", "square"}   square = what the reading definition gives (claude_puzzle_reader
                    .read_latin: s consecutive lines of exactly s cells 1..s or _, size words agreeing), usually null
  SEAL-panel.sha256.txt
Squares come from claude_rsn358b2_bridge.make_requests with seeds 485004-485007 (sizes 4-7, 25 each; not Sleep
research's 35900-36000, 47311 or 47399). About 20% are broken the way 358b3's panel breaks them (a clue repeated in a
row). The layout alternates "Row k: ..." lines and bare lines, as in 358b3.

Construction check (counts only): the code reading of every square message must give the inserted grid. A message
where it does not is kept, and the count is printed and written in the README. The truth stays the inserted grid.

  python -B scripts/claude_gr1_make_panel.py --writings /tmp/blind_gr1/writings.json --out artifacts/claude-panel-gr1-20260926
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SEED = 4850


def rows_text(grid, layout):
    cells = [" ".join("_" if v == 0 else str(v) for v in r) for r in grid]
    if layout == "row":
        return "\n".join("Row %d: %s" % (i + 1, c) for i, c in enumerate(cells))
    return "\n".join(cells)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--writings", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import claude_puzzle_reader as R
    import claude_rsn358b2_bridge as B
    import claude_rsn358b3_panel as P3
    w = json.loads(Path(a.writings).read_text(encoding="utf-8"))
    wr, lk = w["wrappers"], w["lookalikes"]
    assert len(wr) == 30 and len(lk) == 40
    assert all(x.count("{rows}") == 1 and not any(ch.isdigit() for ch in x) for x in wr)
    rng = random.Random(SEED)
    sq = []
    for s in (4, 5, 6, 7):
        for r in B.make_requests(SEED * 100 + s, 25, s, False):
            puz, broken = r["puz"], rng.random() < 0.2
            if broken:
                puz = P3._broken(rng, puz, s)
            sq.append((s, puz, broken))
    rng.shuffle(sq)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    squares, mismatch = [], 0
    for i, (s, puz, broken) in enumerate(sq):
        layout = "row" if i % 2 == 0 else "bare"
        wid = i % len(wr)
        text = wr[wid].replace("{s}", str(s)).replace("{rows}", rows_text(puz, layout))
        g = R.read_latin(text)
        mismatch += int(g is None or g["grid"] != puz)
        squares.append({"id": "gr1-sq-%03d" % i, "text": text, "size": s, "grid": puz, "broken": broken,
                        "layout": layout, "wrapper_id": wid})
    looks, look_sq = [], 0
    for i, t in enumerate(lk):
        g = R.read_latin(t)
        look_sq += int(g is not None)
        looks.append({"id": "gr1-lk-%03d" % i, "text": t, "square": None if g is None else g["grid"]})
    seal = []
    for name, rows in (("squares.jsonl", squares), ("lookalikes.jsonl", looks)):
        p = out / name
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        seal.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}")
    wj = out / "writings.json"
    wj.write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
    seal.append(f"{hashlib.sha256(wj.read_bytes()).hexdigest()}  writings.json")
    (out / "SEAL-panel.sha256.txt").write_text("\n".join(seal) + "\n")
    info = {"squares": len(squares), "broken": sum(r["broken"] for r in squares),
            "by_size": {s: sum(r["size"] == s for r in squares) for s in (4, 5, 6, 7)},
            "construction_mismatch": mismatch, "lookalikes": len(looks), "lookalikes_with_square": look_sq}
    (out / "README.md").write_text(
        "# gr-1 blind panel (TEST-ONLY: never trained, tuned, read or quoted)\n\nMade by scripts/claude_gr1_make_panel.py"
        " from a blind writer's wrappers and lookalikes. Only scripts/claude_gr1.py run/score read it.\n\n"
        "Counts: " + json.dumps(info) + "\n")
    print(json.dumps(info))


if __name__ == "__main__":
    main()
