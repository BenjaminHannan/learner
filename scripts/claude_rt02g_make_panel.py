#!/usr/bin/env python3
"""rt-02g blind panel maker (Plain-English puzzles thread, 2026-09-26). New file only.

The blind writer (an agent that never sees the route or reader code) writes wordings.json:
  {"templates": [10 strings, each with {L} and {T} exactly once], "negatives": [100 strings]}
This script fills the templates with 100 fresh puzzles from claude_blurt2.puzzles(4799, ...), excluding every puzzle
of 0.2c's days and TEST (4700-4703, 4790, 4795), rt-02d's panel seed 4797, rt-02d's dev seed 4880 and the rt-02e
practice seed 4881 (first 400 of each), 10 puzzles per wording, and writes chat_puzzles.jsonl, negatives.jsonl and
SEAL-panel.sha256.txt into --out. It prints counts only.

  python -B scripts/claude_rt02g_make_panel.py --wordings W.json --out artifacts/claude-panel-rt02g-20260926
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt2 as B2  # noqa: E402

SEED = 4799
EXCLUDE = (4700, 4701, 4702, 4703, 4790, 4795, 4797, 4880, 4881)
FMTS = [lambda o: ", ".join(map(str, o[:-1])) + " and " + str(o[-1]),
        lambda o: " ".join(map(str, o)),
        lambda o: ", ".join(map(str, o))]


def fresh(n: int) -> list[dict]:
    seen = {(tuple(p["nums"]), p["target"]) for s in EXCLUDE for p in B2.puzzles(s, 400)}
    cand = [p for p in B2.puzzles(SEED, 12 * n) if (tuple(p["nums"]), p["target"]) not in seen]
    four = [p for p in cand if len(p["nums"]) == 4]
    three = [p for p in cand if len(p["nums"]) == 3]
    n4 = (n + 2) // 3                                    # the generator's own mix: every third puzzle has 4 numbers
    if len(four) < n4 or len(three) < n - n4:
        raise SystemExit(f"only {len(four)} four-number and {len(three)} three-number fresh puzzles")
    out, i4, i3 = [], iter(four), iter(three)
    for i in range(n):
        out.append(next(i4) if i % 3 == 0 else next(i3))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wordings", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    w = json.loads(Path(a.wordings).read_text(encoding="utf-8"))
    T, N = w["templates"], w["negatives"]
    assert len(T) == 10 and all(t.count("{L}") == 1 and t.count("{T}") == 1 for t in T), "10 templates with {L}, {T}"
    assert len(N) == 100 and all(isinstance(x, str) and x.strip() for x in N), "100 negatives"
    ps = fresh(100)
    rows = []
    for i, p in enumerate(ps):
        wi, k = i // 10, i % 10
        o = list(p["nums"])[::-1] if k % 2 else list(p["nums"])
        text = T[wi].replace("{L}", FMTS[k % 3](o)).replace("{T}", str(p["target"]))
        rows.append({"id": f"rt02g-pz-{i + 1:03d}", "text": text, "nums": p["nums"], "target": p["target"],
                     "wording_id": wi})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "chat_puzzles.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                            encoding="utf-8")
    (out / "negatives.jsonl").write_text("".join(json.dumps({"id": f"rt02g-neg-{i + 1:03d}", "text": t},
                                                            ensure_ascii=False) + "\n" for i, t in enumerate(N)),
                                         encoding="utf-8")
    (out / "wordings.json").write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = []
    for f in ("chat_puzzles.jsonl", "negatives.jsonl", "wordings.json"):
        lines.append(f"{hashlib.sha256((out / f).read_bytes()).hexdigest()}  {f}\n")
    (out / "SEAL-panel.sha256.txt").write_text("".join(lines), encoding="utf-8")
    print(json.dumps({"puzzles": len(rows), "four_number": sum(len(r["nums"]) == 4 for r in rows),
                      "negatives": len(N), "wordings": len(T)}))


if __name__ == "__main__":
    main()
