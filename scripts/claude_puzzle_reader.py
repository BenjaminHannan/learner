#!/usr/bin/env python3
"""Shared puzzle reader: turns a chat message into a solver's input format (Plain-English puzzles thread owns it,
2026-09-26). One reader, one format per solver, so the chat route (rt-02d/e) and the learned reasoner's chat bridge
(Sleep research's rsn-358b3) do not each grow their own. Nothing is added here without this thread's review.

Formats
  latin  {"kind": "latin", "size": s, "grid": s rows of s ints (0 = blank), "blanks": n, "clash": bool,
          "clashes": [[axis, index, value], ...]}
         HAND-WRITTEN STAND-IN for the learned grid reader, which is still owed (owner: this thread). 358b2 showed the
         plain 1B cannot copy a square (25/39/28 of 100 exact; it drops "_"), so for now code reads it. A square is a
         run of s consecutive lines, each holding exactly s cells and nothing else (digits 1..s or "_"; cells split
         by spaces, commas or "|"; a leading "Row k:" is allowed). If the message also names a size ("1 to s",
         "1-s", "s by s", "s x s", with s in 3..9), one of them must be the square's size, or the message is not read. A broken square (a clue repeated in a
         row or column) is still read, with clash true, and the route decides the reply.
  arith  {"kind": "arith", "nums": sorted ints, "target": t}
         The plain 1B copies the numbers and target (rt-02g's V1 instruction, answer forced to start "numbers:",
         greedy, every LoRA scale 0; 156 of 159 exact on practice data). Code accepts it only if the numbers plus the
         target are exactly the message's whole numbers. It runs only when a decider passed in by the caller says
         the message asks for a puzzle, because the plain 1B cannot decide that itself: rt-02g fired on 15 of 55
         lookalikes (artifacts/claude-rt02g-20260926/WITHDRAWN-rt02g.md). No decider has passed yet; rt-02h is the
         learned candidate.

  read(text, one_b=None, decide_arith=None) -> dict | None     (latin first; arith only with one_b and decide_arith)
  python -B scripts/claude_puzzle_reader.py --selftest         (code only, no model, no TEST panel)
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# ------------------------------------------------------------------ latin (hand-written stand-in)
_ROWPFX = re.compile(r"^\s*row\s*\d+\s*[:.)\-]?\s*", re.I)
_GRIDLINE = re.compile(r"^[\s|,]*(?:(?:_|\d{1,2})[\s|,]+)*(?:_|\d{1,2})[\s|,]*$")
_SIZE = re.compile(r"\b1\s*(?:to|-|–|through)\s*(\d{1,2})\b|\b(\d{1,2})\s*(?:by|x|×)\s*(\d{1,2})\b", re.I)


def _cells(line: str):
    s = _ROWPFX.sub("", line.strip())
    if not s or not _GRIDLINE.match(s):
        return None
    return [0 if c == "_" else int(c) for c in re.findall(r"_|\d{1,2}", s)]


def _named_sizes(text: str) -> set[int]:
    out = set()
    for m in _SIZE.finditer(text):
        if m.group(1):
            out.add(int(m.group(1)))
        elif m.group(2) == m.group(3):
            out.add(int(m.group(2)))
    return out


def _clashes(grid):
    s, out = len(grid), []
    for axis in ("row", "col"):
        for i in range(s):
            vals = [grid[i][j] if axis == "row" else grid[j][i] for j in range(s)]
            out += [[axis, i + 1, v] for v, n in sorted(Counter(v for v in vals if v).items()) if n > 1]
    return out


def read_latin(text: str):
    lines = (text or "").splitlines()
    rows = [_cells(x) for x in lines]
    found = []
    i = 0
    while i < len(rows):
        if rows[i] is None:
            i += 1
            continue
        j = i
        while j < len(rows) and rows[j] is not None and len(rows[j]) == len(rows[i]):
            j += 1
        s = len(rows[i])
        if j - i == s and 3 <= s <= 9 and all(1 <= v <= s or v == 0 for r in rows[i:j] for v in r):
            found.append(rows[i:j])
        i = j
    if len(found) != 1:
        return None
    grid = found[0]
    s = len(grid)
    named = {v for v in _named_sizes(text) if 3 <= v <= 9}
    if named and s not in named:
        return None
    cl = _clashes(grid)
    return {"kind": "latin", "size": s, "grid": grid, "blanks": sum(v == 0 for r in grid for v in r),
            "clash": bool(cl), "clashes": cl}


# ------------------------------------------------------------------ arith (1B copies; caller's decider decides)
ARITH_ASK = ("Message: {text}\n\nIs this person asking you to find a way to combine the numbers they give, using + - * /, "
             "so that the result equals a target number? Most messages that contain numbers are not: ages, times, "
             "prices, scores, codes, lists and totals, checking a sum, or sharing an answer they already found. If it "
             "is a request to solve such a puzzle, reply exactly \"numbers: <the numbers to combine>; target: <the "
             "target>\". Otherwise reply exactly \"none\".")
ARITH_SHOT = [
    ("Can you get 10 out of 2, 3 and 4? Each one used once.", "numbers: 2, 3, 4; target: 10"),
    ("My sister has 3 cats, 2 dogs and 1 rabbit, 6 pets in all.", "none"),
    ("We need 4 chairs, 6 plates and 2 tables for 11 guests. Can you write the shopping list?", "none"),
    ("24 using 1 5 5 6 please", "numbers: 1, 5, 5, 6; target: 24"),
    ("Is 5 * 4 + 2 equal to 22?", "none"),
    ("Flight 12 boards at gate 7 from row 3 to row 9. Can you remind me in a text?", "none"),
    ("My numbers are 3 7 8 12. How do I make 20 from them?", "numbers: 3, 7, 8, 12; target: 20"),
    ("I solved it myself: (9 - 3) * 2 = 12!", "none"),
    ("I finally made 18 from 2, 6 and 9 by myself, so happy!", "none"),
    ("What is 7 + 8 + 2 + 1?", "none"),
    ("The swim times were 11, 13, 12 and 10 seconds, and the record is 9. Who should race?", "none"),
    ("Find a way to reach 15 with 9, 2 and 5 using + - * /.", "numbers: 9, 2, 5; target: 15"),
]
ARITH_MAX_NEW = 24


def copy_arith(one_b, text: str):
    """The 1B's copy of the numbers and target (forced to start "numbers:"), checked by code; None if it fails."""
    import claude_rt02g as G
    import claude_sleep02c as SL
    if not G.pre_gate(text):
        return None
    tok, model, torch = one_b.tok, one_b.model, one_b.torch
    msgs = []
    for q, a in ARITH_SHOT:
        msgs += [{"role": "user", "content": ARITH_ASK.format(text=q)}, {"role": "assistant", "content": a}]
    msgs.append({"role": "user", "content": ARITH_ASK.format(text=text)})
    prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    ids = tok(prompt + "numbers:", return_tensors="pt").to(one_b.dev)
    mods = SL.lora_mods(model)
    saved = [x.scale for x in mods]
    for x in mods:
        x.scale = 0.0
    try:
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=ARITH_MAX_NEW, do_sample=False, pad_token_id=tok.eos_token_id)
    finally:
        for x, sc in zip(mods, saved):
            x.scale = sc
    raw = "numbers:" + tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).split("\n")[0]
    p = G.accept(text, raw)
    return None if p is None else {"kind": "arith", **p}


def read(text: str, one_b=None, decide_arith=None):
    g = read_latin(text)
    if g is not None:
        return g
    if one_b is not None and decide_arith is not None and decide_arith(text):
        return copy_arith(one_b, text)
    return None


# ------------------------------------------------------------------ selftest (code only)
def selftest() -> None:
    import json
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    import claude_rsn358b2_bridge as B
    import claude_rt02d as RT
    n = Counter()
    root = SCRIPTS.parent
    # 1. Sleep research's free smoke panel: every square read exactly; broken ones flagged
    sm = root / "artifacts/claude-panel-rsn358b3-smoke-20260926"
    ans = {r["id"]: r for r in map(json.loads, (sm / "answers.jsonl").read_text().splitlines())}
    for r in map(json.loads, (sm / "panel.jsonl").read_text().splitlines()):
        a, g = ans[r["id"]], read_latin(r["message"])
        assert g and g["size"] == a["size"] and g["grid"] == a["puz"] and g["clash"] == (a["kind"] == "broken"), r["id"]
        n["smoke"] += 1
    # 2. fresh squares from 358b2's generator (seed 4830xx; Sleep research uses 35900-36000), in several layouts
    layouts = [lambda p: B.rows_text(p),
               lambda p: "\n".join("Row %d: %s" % (i + 1, " ".join("_" if v == 0 else str(v) for v in r)) for i, r in enumerate(p)),
               lambda p: "\n".join("| " + " | ".join("_" if v == 0 else str(v) for v in r) + " |" for r in p),
               lambda p: "\n".join(", ".join("_" if v == 0 else str(v) for v in r) for r in p)]
    heads = ["Can you finish this?", "hey fill the blanks pls, rows and columns 1-{s} once each", "Solve:",
             "Here's a {s} by {s} one from my puzzle book."]
    for s in (4, 5, 6, 7):
        for k, rq in enumerate(B.make_requests(483000 + s, 12, s, False)):
            text = heads[k % 4].format(s=s) + "\n" + layouts[k % 4](rq["puz"]) + ("\nThanks!" if k % 2 else "")
            g = read_latin(text)
            assert g and g["grid"] == rq["puz"] and not g["clash"], (s, k, text)
            n["fresh"] += 1
    # 3. size named in words must agree with the square
    p5 = B.make_requests(483099, 1, 5, False)[0]["puz"]
    assert read_latin("Use 1 to 6 in each row.\n" + B.rows_text(p5)) is None
    assert read_latin("Use 1 to 5 in each row.\n" + B.rows_text(p5))["size"] == 5
    n["size"] += 2
    # 4. no square in sum puzzles, lookalikes, dev and practice messages or the 300 general items
    texts = [t for t, _ in RT.dev_cases()] + [it["q"] for it in D1.harm_panel()]
    prac = json.loads((root / "artifacts/claude-rt02e-20260926/practice/wordings_practice.json").read_text())
    ps = B2.puzzles(4881, len(prac["puzzle_templates"]))
    texts += [t.replace("{L}", ", ".join(map(str, p["nums"]))).replace("{T}", str(p["target"]))
              for t, p in zip(prac["puzzle_templates"], ps)] + prac["negatives"]
    texts += ["Meetings:\n9 10 11\n1 2 3\n4 5 6", "Scores\n3 4\n5 6", "My PIN is\n1 2 3 4"]
    for t in texts:
        assert read_latin(t) is None, t
        n["no_square"] += 1
    # 5. the arith copy's few-shot answers obey rt-02g's code check
    import claude_rt02g as G
    for q, a in ARITH_SHOT:
        assert (G.accept(q, a) is not None) == (a != "none"), q
    n["arith_shot"] += 1
    assert read("What is the capital of France?") is None
    n["read"] += 1
    print("puzzle_reader selftest ok", json.dumps(dict(n)))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
