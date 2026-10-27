#!/usr/bin/env python3
"""rsn-358b3 panel maker and scorer (sleep research thread, 2026-09-26).

One seeded function makes a chat-asked number-square panel, so 358b3's blind panel and 0.2d row A's separate fresh
panel (Month-end ADDENDUM-8) come from the same generator with different seeds. Two files per panel:
  panel.jsonl    {"id", "message"}               what every arm (build and rivals) receives, verbatim
  answers.jsonl  {"id", "kind", "size", "puz", "sol"}   truth; the rival runner (Benchmarks) never opens it
Kinds: "solve" (a square with one answer) and "broken" (a lookalike with a clue repeated in one row, so no answer
exists; the right reply gives no finished square).

Replies come as {"id", "reply", optional "hit_max", "think_closed"} (Benchmarks' OUT/rival_<NAME>.jsonl format).
The answer read from a reply is its FINAL grid: the last run of s consecutive lines that each hold exactly s numbers
1..s ("Row k:", table bars, commas and blank lines inside the run are allowed; any other line ends a run). This
skips echoed puzzles (they hold "_") and working rows shown before the answer. Every arm is scored the same way.
Per kind: right (solve: the final grid is a valid solution; broken: a complete, non-empty reply with no attempted
square, where an attempted square is s rows of s numbers even if some fall outside 1..s),
wrong_grid (a final grid that is not a valid solution, or any attempted square on a broken item), no_grid (solve item,
nothing usable), and cut_off counts (the reply hit the token cap: never right on any item, reported beside every
score). think_closed is NOT a cut-off signal: the rival runner writes false for every thinking-off reply, and an
unclosed thinking reply is already "" (not right). A missing reply counts as no_grid / not right.
(Fix 2026-09-26 17:09 UTC, before any sealed panel: think_closed false marked every thinking-off reply cut off, so
broken items could never be right; and a capped solve reply could still count right. Found on smoke 2.)

  python -B scripts/claude_rsn358b3_panel.py make --seed S --n N --sizes 5,6,7 [--broken-share 0.2] --out DIR
  python -B scripts/claude_rsn358b3_panel.py score --panel DIR --replies FILE.jsonl
  python -B scripts/claude_rsn358b3_panel.py selftest
Seeds 35900-35999 are 358b2's; 36000 is the rival smoke panel. Test panels take seeds agreed at sealing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358b2_bridge as B  # noqa: E402


def _broken(rng, puz, s):
    """copy a clue into another cell of the same row so the row repeats a number; no solution can exist"""
    p = [row[:] for row in puz]
    rows = [r for r in range(s) if sum(1 for v in p[r] if v) >= 1 and any(v == 0 for v in p[r])]
    r = rng.choice(rows)
    src = rng.choice([c for c in range(s) if p[r][c]])
    dst = rng.choice([c for c in range(s) if p[r][c] == 0])
    p[r][dst] = p[r][src]
    return p


def make_panel(seed, n, sizes, broken_share=0.2):
    """n items per size; returns (panel_rows, answer_rows) in a seeded shuffled order"""
    rng = random.Random(seed)
    items = []
    for s in sizes:
        reqs = B.make_requests(seed * 100 + s, n, s, False)
        for r in reqs:
            kind, puz, sol = "solve", r["puz"], r["sol"]
            text = r["text"]
            if rng.random() < broken_share:
                kind, puz, sol = "broken", _broken(rng, puz, s), None
                rows = "\n".join("Row %d: %s" % (i + 1, " ".join("_" if v == 0 else str(v) for v in row))
                                 for i, row in enumerate(puz))
                text = rng.choice(B.TEMPLATES).format(s=s, rows=rows)
            items.append({"kind": kind, "size": s, "puz": puz, "sol": sol, "message": text})
    rng.shuffle(items)
    panel, answers = [], []
    for i, it in enumerate(items):
        pid = "p%d-%04d" % (seed, i)
        panel.append({"id": pid, "message": it["message"]})
        answers.append({"id": pid, "kind": it["kind"], "size": it["size"], "puz": it["puz"], "sol": it["sol"]})
    return panel, answers


def final_grid(text, s, any_values=False):
    """the last run of s consecutive rows of exactly s numbers 1..s (see the module docstring); any_values=True also
    takes rows whose numbers fall outside 1..s (an attempted square, used for broken items)"""
    runs, cur = [], []
    for line in text.splitlines():
        raw = line.replace("*", "").replace("\\\\", " ").replace("&", " ").strip()   # LaTeX array rows: & and \\
        cols = [c.strip() for c in raw.strip("|").split("|")] if raw.startswith("|") else None
        if cols and cols[0] == "" and [c for c in cols[1:] if c] == [str(i) for i in range(1, s + 1)]:
            continue                                                 # a table header "| | 1 | 2 | ... |" keeps a run going
        body = re.sub(r"^\s*(row\s*\d+\s*[:.)|-]?)", "", raw.lstrip("|` ").strip(), flags=re.I).strip("|` ")
        if not body or re.fullmatch(r"[\s|:\-]+", body) or re.fullmatch(r"\\hline", body):
            continue                                                 # blank lines and table rules keep a run going
        if "_" not in body and re.fullmatch(r"[\d\s,|;.\-]+", body):
            cells = [int(c) for c in re.findall(r"\d+", body)]
            if len(cells) == s + 1 and cells[0] == len(cur) + 1:    # a leading row-number column
                cells = cells[1:]
            if len(cells) == s and (any_values or all(1 <= c <= s for c in cells)):
                cur.append(cells)
                continue
        if cur:
            runs.append(cur)
        cur = []
    if cur:
        runs.append(cur)
    runs = [r for r in runs if len(r) >= s]
    return runs[-1][-s:] if runs else None


def score_panel(answers, replies):
    """answers: list of answer rows; replies: {id: {"reply", "hit_max", "think_closed"}} or {id: text}"""
    out = {}
    for a in answers:
        key = "%s%d" % (a["kind"], a["size"])
        res = out.setdefault(key, {"n": 0, "right": 0, "wrong_grid": 0, "no_grid": 0, "cut_off": 0, "missing": 0})
        res["n"] += 1
        r = replies.get(a["id"])
        if r is None:
            res["missing"] += 1
            r = {"reply": ""}
        elif isinstance(r, str):
            r = {"reply": r}
        cut = bool(r.get("hit_max"))
        res["cut_off"] += cut
        grid = final_grid(r["reply"], a["size"])
        tried = final_grid(r["reply"], a["size"], any_values=True)
        if cut:
            res["wrong_grid" if grid is not None else "no_grid"] += 1
        elif a["kind"] == "broken":
            if tried is not None:
                res["wrong_grid"] += 1
            elif cut or not r["reply"].strip():
                res["no_grid"] += 1
            else:
                res["right"] += 1
        elif grid is None:
            res["no_grid"] += 1
        elif B.is_solution(a["puz"], grid):
            res["right"] += 1
        else:
            res["wrong_grid"] += 1
    return dict(sorted(out.items()))


def _write(rows, path):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selftest():
    panel, answers = make_panel(36000, 20, [5, 6], 0.25)
    assert len(panel) == 40 and [p["id"] for p in panel] == [a["id"] for a in answers]
    again, _ = make_panel(36000, 20, [5, 6], 0.25)
    assert again == panel, "not deterministic"
    kinds = {a["kind"] for a in answers}
    assert kinds == {"solve", "broken"}, kinds
    for a in answers:
        if a["kind"] == "broken":
            assert any(len([v for v in row if v]) != len({v for v in row if v}) for row in a["puz"])
    replies = {}
    for a in answers:
        if a["kind"] == "solve":
            replies[a["id"]] = "Sure! Here it is:\n| " + " |\n| ".join(" | ".join(map(str, r)) for r in a["sol"]) + " |"
        else:
            replies[a["id"]] = "This one can't be finished: a row repeats a number."
    res = score_panel(answers, replies)
    assert all(v["right"] == v["n"] for v in res.values()), res
    echo = {a["id"]: B.rows_text(a["puz"]) for a in answers}
    res2 = score_panel(answers, echo)
    assert sum(v["right"] for k, v in res2.items() if k.startswith("solve")) == 0, res2
    a0 = next(a for a in answers if a["kind"] == "solve")
    sol = B.rows_text(a0["sol"])
    work = "Row 1: " + " ".join(map(str, a0["sol"][0])) + "\nthinking...\n"
    assert B.is_solution(a0["puz"], final_grid(work + "Final:\n```\n" + sol + "\n```\nDone.", a0["size"]))
    wrong = [row[:] for row in a0["sol"]]
    wrong[0][0], wrong[0][1] = wrong[0][1], wrong[0][0]
    assert final_grid(sol + "\nwait, correction:\n" + B.rows_text(wrong), a0["size"]) == wrong   # last grid counts
    assert final_grid(B.rows_text(a0["puz"]), a0["size"]) is None                                 # echo has blanks
    table = "| " + " |\n|---|---|\n| ".join(" | ".join("**%d**" % v for v in row) for row in a0["sol"]) + " |"
    assert final_grid(table, a0["size"]) == a0["sol"], table                                     # markdown table
    idx = "\n".join("| %d | " % (i + 1) + " | ".join(map(str, row)) + " |" for i, row in enumerate(a0["sol"]))
    assert final_grid(idx, a0["size"]) == a0["sol"]                                              # row-number column
    hdr = "| | " + " | ".join(str(i) for i in range(1, a0["size"] + 1)) + " |\n|" + "---|" * (a0["size"] + 1) + "\n"
    lab = hdr + "\n".join("| **Row %d** | " % (i + 1) + " | ".join("**%d**" % v for v in row) + " |" for i, row in enumerate(a0["sol"]))
    assert final_grid(lab, a0["size"]) == a0["sol"], lab                                         # header + Row labels
    num = hdr + "\n".join("| **%d** | " % (i + 1) + " | ".join(map(str, row)) + " |" for i, row in enumerate(a0["sol"]))
    assert final_grid(num, a0["size"]) == a0["sol"], num                                         # header + bold index
    tex = "$$\n\\begin{array}{|c|}\n\\hline\n" + "\n\\hline\n".join(" & ".join(map(str, row)) + " \\\\" for row in a0["sol"]) + "\n\\hline\n\\end{array}\n$$"
    assert final_grid(tex, a0["size"]) == a0["sol"], tex                                         # LaTeX array
    b0 = next(a for a in answers if a["kind"] == "broken")
    r3 = score_panel([b0], {b0["id"]: {"reply": "No square works here.", "hit_max": True}})
    assert r3["broken%d" % b0["size"]]["right"] == 0, r3                                        # cut off: not right
    assert score_panel([b0], {})["broken%d" % b0["size"]]["right"] == 0                          # missing: not right
    bad = "Here it is:\n" + "\n".join(" ".join(str(c + r + 2) for c in range(b0["size"])) for r in range(b0["size"]))
    assert final_grid(bad, b0["size"]) is None and final_grid(bad, b0["size"], any_values=True) is not None
    r7 = score_panel([b0], {b0["id"]: {"reply": bad, "hit_max": False}})
    assert r7["broken%d" % b0["size"]]["right"] == 0, r7                                        # bad square attempted
    r4 = score_panel([b0], {b0["id"]: {"reply": "No square works here.", "hit_max": False, "think_closed": False}})
    assert r4["broken%d" % b0["size"]]["right"] == 1, r4                                        # thinking off: fine
    r5 = score_panel([a0], {a0["id"]: {"reply": sol, "hit_max": True}})
    assert r5["solve%d" % a0["size"]]["right"] == 0 and r5["solve%d" % a0["size"]]["cut_off"] == 1, r5  # capped
    r6 = score_panel([a0], {a0["id"]: {"reply": sol, "hit_max": False, "think_closed": False}})
    assert r6["solve%d" % a0["size"]]["right"] == 1, r6
    print("selftest ok", json.dumps(res))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--seed", type=int, required=True)
    m.add_argument("--n", type=int, required=True)
    m.add_argument("--sizes", default="5,6,7")
    m.add_argument("--broken-share", type=float, default=0.2)
    m.add_argument("--out", required=True)
    sc = sub.add_parser("score")
    sc.add_argument("--panel", required=True)
    sc.add_argument("--replies", required=True)
    sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "make":
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        panel, answers = make_panel(a.seed, a.n, [int(x) for x in a.sizes.split(",")], a.broken_share)
        h1, h2 = _write(panel, out / "panel.jsonl"), _write(answers, out / "answers.jsonl")
        print(json.dumps({"items": len(panel), "panel_sha256": h1, "answers_sha256": h2}))
        return
    answers = [json.loads(l) for l in (Path(a.panel) / "answers.jsonl").read_text().splitlines() if l.strip()]
    replies = {}
    for l in Path(a.replies).read_text().splitlines():
        if l.strip():
            r = json.loads(l)
            replies[r["id"]] = r
    print(json.dumps(score_panel(answers, replies), indent=1))


if __name__ == "__main__":
    main()
