#!/usr/bin/env python3
"""gr-7d: where do the trained reader's bad reads come from? (Plain-English puzzles thread, 2026-09-27; PLAN-gr7d.md)

gr-7 (VERIFY-gr7) failed on 2 false squares, 3 wrong squares and 5 wrong unseen-format squares. The spent gr-6 panel is
never read (Thread manager 07:38), so this script makes a fresh PRACTICE set by code, of the same kinds, and counts where
the bad reads of L7 (gr-7's adapter) and G5 (gr-5's adapter) come from. The practice set is never a test and never
trained on. The readers are run by the sealed `claude_gr7.py run`, unchanged, with --panel-dir pointing here.

The practice set (all code, new seeds; the words around the grids are the 1B's own openers, closers and everyday drafts,
the same pools gr-6 trained with, disclosed):
  squares.jsonl     200 {"id","text","size","grid","broken","layout","cells"}: seeds 507104-507107 (sizes 4-7, 50
                    each), about 20% broken as in 358b3, layouts "Row k:" and bare alternating (the panel's own).
  unseen.jsonl      200 {"id","text","size","grid","broken","format_id","sep_seen","cells"}: seeds 507204-507207, in 40
                    formats drawn by code (seed 5073) from the part lists below, none writing a row the same way as a
                    training or dev layout (claude_gr6.signature); formats 0-19 use a training separator, 20-39 a new one;
                    a format whose row label or row end uses the separator's mark is not drawn (ambiguous).
  lookalikes.jsonl  150 {"id","text","square","kind","shape"}: 50 near misses (s x s single digits, one above s; the kind
                    gr-6 trained on), 50 non-square blocks (r x c single digits, r != c), 50 square blocks of numbers up
                    to 40 with at least one of two digits; blocks in training layouts; square = read_latin's reading, and
                    any block read_latin reads as a square is redrawn and counted.
  "cells" = [[char index, row, col], ...] of every cell in the text (code knows where the square's own cells are).

Kinds of bad read (PLAN-gr7d, fixed before the run). A "far" row is an output row not within 1 cell of any truth row of
the same length. T is every digit and "_" in the message, in order; a token is a cell token if it is one of the square's
own cells.
  wrong grid (a square was there, the reader returned a different grid):
    A  numbers that are not cells: some far output row is an exact run of T that includes at least one non-cell token
       (a row label, a column header, a number in the words around the grid, another block)
    B  lost its place in the square: not A, and either at most one output row is far, or the output's cells in order
       are within 2 edits of the truth's (a shifted cell, a skipped or repeated row, a few slips)
    C  other: the rest (two or more rows that are neither the square's rows nor the message's numbers)
  false square (a lookalike whose truth is none, the reader returned a grid):
    A  copied the message's numbers: all but at most one output row are exact runs of T
    C  other

  python -B scripts/claude_gr7_diag.py --selftest
  python -B scripts/claude_gr7_diag.py make --out PRACTICE_DIR
  python -B scripts/claude_gr7_diag.py count --practice PRACTICE_DIR --run RUN_DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_gr1 as G1  # noqa: E402
import claude_gr6 as G6  # noqa: E402

SEED_SQ, SEED_UN, SEED_FMT, SEED_LK, SEED_WRAP = 5071, 5072, 5073, 5074, 5075
N_PER_SIZE, N_FORMATS, N_LK_KIND = 50, 40, 50
MIN_WRONG = 10                      # fewer L7 wrong grids than this and the count decides nothing (PLAN-gr7d)

# ------------------------------------------------------------------ part lists for the unseen formats (scaffolding)
NEW_LABELS = ["Row #{i} ", "r{i}: ", "{A}) ", "{i} - ", "Line {A}: ", "[{i}] ", "{A}. ", "row{i}: ", "No. {i}: "]
NEW_WRAPS = [("<", ">"), ("(", ");"), ("[", "],")]
NEW_SEPS = [" - ", " . ", " : ", " ~ ", " + ", " * ", "="]


def _draw_format(rng, seps):
    rc = dict.fromkeys(G1.RECIPE_KEYS, "")
    lab = rng.choice(G6.LABELS + NEW_LABELS)
    wo, wc = rng.choice(G6.WRAPS + NEW_WRAPS)
    sep, join = rng.choice(seps), rng.choice(G6.JOINS)
    rc.update(row_prefix=lab + wo, sep=sep, row_suffix=wc, row_join=join, header="none")
    if join == "\n":
        rc["divider"] = rng.choice(G6.DIVIDERS)
    if join in ("\n", "\n\n"):
        h = rng.choice(G6.HEADERS)
        if h != "none":
            rc.update(header=h, header_prefix=" " * len((lab + wo).replace("{i}", "1").replace("{A}", "A")),
                      header_sep=sep, header_suffix="")
    rc["before"], rc["after"] = rng.choice(G6.AROUND)
    return rc


def draw_formats():
    """40 formats, none writing a row like a training or dev layout or like each other; 0-19 training separators"""
    rng = random.Random(SEED_FMT)
    lay = G6.draw_layouts()
    taken = G6.gr1_signatures() | {G6.signature(r) for r in lay}
    seen = sorted(G6.training_seps(lay))
    seen_raw = [s for s in G6.SEPS if G6._norm(s) in seen]
    out = []
    for group, seps in (("seen", seen_raw), ("new", NEW_SEPS)):
        n = 0
        while n < N_FORMATS // 2:
            rc = _draw_format(rng, seps)
            sg = G6.signature(rc)
            if sg in taken:
                continue
            if rc["row_join"] not in ("\n", "\n\n") and G6._norm(rc["row_join"]) == G6._norm(rc["sep"]):
                continue
            ns = G6._norm(rc["sep"])
            if ns and (ns in G6._norm(rc["row_prefix"]) or ns in G6._norm(rc["row_suffix"])):
                continue                                        # a row label using the separator's mark is ambiguous
            assert (ns in seen) == (group == "seen")
            taken.add(sg)
            out.append(dict(rc, id="F%02d" % len(out), group=group))
            n += 1
    return out


# ------------------------------------------------------------------ the practice set
def _wrap(rng, openers, closers, sq, cells):
    o, c = rng.choice(openers), (rng.choice(closers) if rng.random() < 0.5 else "")
    if rng.random() < 0.75:
        text, off = o + "\n" + sq + ("\n" + c if c else ""), len(o) + 1
    else:
        text, off = sq + "\n" + o, 0
    return text, [[x + off, r, cc] for x, r, cc in cells]


def make(a) -> None:
    import claude_gr1_make_panel as M1
    import claude_gr5 as G5
    import claude_gr5_make_panel as M5
    import claude_puzzle_reader as R
    import claude_rsn358b2_bridge as B
    import claude_rsn358b3_panel as P3
    rng = random.Random(SEED_WRAP)
    wr = G5._load(G6.GR1_WRAP)
    openers = [r["text"] for r in wr if r["keep"] and r["kind"] == "opener"]
    closers = [r["text"] for r in wr if r["keep"] and r["kind"] == "closer"]
    everyday = [r["raw"] for r in G5._load(G6.RT02H)]
    squares, mism = [], 0
    for i, (s, puz, broken) in enumerate(M5.squares_for(B, P3, SEED_SQ, N_PER_SIZE)):
        layout = "row" if i % 2 == 0 else "bare"
        sq, cells = G1.render_recipe(puz, G1.layout_recipe(layout, s))
        assert sq == M1.rows_text(puz, layout)
        text, cells = _wrap(rng, openers, closers, sq, cells)
        mism += int((R.read_latin(text) or {}).get("grid") != puz)
        squares.append({"id": "d7-sq-%03d" % i, "text": text, "size": s, "grid": puz, "broken": broken,
                        "layout": layout, "cells": cells})
    fm = draw_formats()
    unseen = []
    for i, (s, puz, broken) in enumerate(M5.squares_for(B, P3, SEED_UN, N_PER_SIZE)):
        f = fm[i % N_FORMATS]
        sq, cells = G1.render_recipe(puz, f)
        text, cells = _wrap(rng, openers, closers, sq, cells)
        unseen.append({"id": "d7-un-%03d" % i, "text": text, "size": s, "grid": puz, "broken": broken,
                       "format_id": f["id"], "sep_seen": f["group"] == "seen", "cells": cells})
    lrng = random.Random(SEED_LK)
    rec = G6.training_recipes(G6.draw_layouts())
    looks, redrawn = [], Counter()
    for kind in ("near", "nonsquare", "numbers"):
        n = 0
        while n < N_LK_KIND:
            if kind == "near":
                s = lrng.randint(3, 7)
                shape = (s, s)
                g = [[lrng.randint(1, 9) for _ in range(s)] for _ in range(s)]
                if max(v for row in g for v in row) <= s:
                    g[lrng.randrange(s)][lrng.randrange(s)] = lrng.randint(s + 1, 9)
            elif kind == "nonsquare":
                r, c = lrng.sample(range(3, 8), 2)
                shape = (r, c)
                g = [[lrng.randint(1, max(r, c)) for _ in range(c)] for _ in range(r)]
            else:
                s = lrng.randint(3, 7)
                shape = (s, s)
                g = [[lrng.randint(1, 40) for _ in range(s)] for _ in range(s)]
                if max(v for row in g for v in row) < 10:
                    g[lrng.randrange(s)][lrng.randrange(s)] = lrng.randint(10, 40)
            if lrng.random() < 0.5 and kind != "numbers":
                g = [[0 if lrng.random() < 0.25 else v for v in row] for row in g]
            src, rc = lrng.choice(rec)
            blk = G1.render_recipe(g, G1.layout_recipe(rc, shape[1], lrng.randrange(4)) if src == "gr1" else rc)[0]
            t = lrng.choice(everyday + openers)
            text = t + "\n" + blk if lrng.random() < 0.6 else blk + "\n" + t
            got = R.read_latin(text)
            if got is not None:
                redrawn[kind] += 1
                continue
            looks.append({"id": "d7-lk-%03d" % len(looks), "text": text, "square": None, "kind": kind,
                          "shape": list(shape)})
            n += 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seal = []
    for name, rows in (("squares.jsonl", squares), ("unseen.jsonl", unseen), ("lookalikes.jsonl", looks)):
        p = out / name
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        seal.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}")
    p = out / "formats.json"
    p.write_text(json.dumps(fm, ensure_ascii=False, indent=1), encoding="utf-8")
    seal.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  formats.json")
    (out / "SEAL-practice.sha256.txt").write_text("\n".join(seal) + "\n")
    print(json.dumps({"squares": len(squares), "squares_broken": sum(r["broken"] for r in squares),
                      "squares_read_latin_mismatch": mism, "unseen": len(unseen),
                      "unseen_sep_seen": sum(r["sep_seen"] for r in unseen), "formats": len(fm),
                      "lookalikes": len(looks), "lookalikes_redrawn_read_latin_square": dict(redrawn)}))


# ------------------------------------------------------------------ the kinds of bad read
def _tok(v) -> str:
    return "_" if v == 0 else str(v)


def tokens(text, cells):
    """every digit and "_" in the text, in order, as (token, is_cell)"""
    cs = {x for x, _, _ in cells}
    return [(ch, i in cs) for i, ch in enumerate(text) if ch.isdigit() or ch == "_"]


def lev(a, b) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j - 1] + (x != y), prev[j] + 1, cur[j - 1] + 1))
        prev = cur
    return prev[-1]


def runs_with(row, T):
    """the start positions where row occurs as an exact contiguous run of T's tokens"""
    toks, n = [t for t, _ in T], len(row)
    return [j for j in range(len(toks) - n + 1) if toks[j:j + n] == row]


def _far(row, truth_rows) -> bool:
    return not any(len(t) == len(row) and sum(x != y for x, y in zip(row, t)) <= 1 for t in truth_rows)


def kind_wrong(out, truth, T) -> str:
    o_rows = [[_tok(v) for v in r] for r in out]
    t_rows = [[_tok(v) for v in r] for r in truth]
    far = [r for r in o_rows if _far(r, t_rows)]
    for r in far:
        if any(not all(c for _, c in T[j:j + len(r)]) for j in runs_with(r, T)):
            return "A"
    if len(far) <= 1 or lev([t for r in o_rows for t in r], [t for r in t_rows for t in r]) <= 2:
        return "B"
    return "C"


def kind_false(out, T) -> str:
    o_rows = [[_tok(v) for v in r] for r in out]
    return "A" if sum(not runs_with(r, T) for r in o_rows) <= 1 else "C"


def count(a) -> None:
    import claude_gr5 as G5
    pd, rd = Path(a.practice), Path(a.run)
    st, detail = Counter(), Counter()
    for arm in ("L7", "G5"):
        for task in ("squares", "unseen", "lookalikes"):
            items = {r["id"]: r for r in G5._load(pd / f"{task}.jsonl")}
            got = G5._load(rd / f"{arm}_{task}.jsonl")
            assert sorted(r["id"] for r in got) == sorted(items), f"{arm}_{task}: ids differ from the practice set"
            st[f"{arm}_{task}_incomplete"] += sum(not r["complete"] for r in got)
            for r in got:
                it, g = items[r["id"]], r["grid"]
                if task == "lookalikes":
                    if g is None:
                        st[f"{arm}_lookalikes_none"] += 1
                        continue
                    k = kind_false(g, tokens(it["text"], []))
                    st[f"{arm}_false_{k}"] += 1
                    st[f"{arm}_false_{it['kind']}_{k}"] += 1
                    same = [len(g), len(g[0])] == it["shape"]
                    detail[f"{arm}_false_{it['kind']}_" + ("whole_block" if same else "not_whole_block")] += 1
                    continue
                grp = task if task == "squares" else ("unseen_sepseen" if it["sep_seen"] else "unseen_sepnew")
                if g == it["grid"]:
                    st[f"{arm}_{grp}_exact"] += 1
                elif g is None:
                    st[f"{arm}_{grp}_none"] += 1
                else:
                    k = kind_wrong(g, it["grid"], tokens(it["text"], it["cells"]))
                    st[f"{arm}_{grp}_wrong_{k}"] += 1
                    st[f"{arm}_wrong_{k}"] += 1
                    detail[f"{arm}_{grp}_wrong_" + ("same_size" if len(g) == len(it["grid"]) else "other_size")] += 1
    res = {}
    for arm in ("L7", "G5"):
        n = sum(st[f"{arm}_wrong_{k}"] for k in "ABC")
        res[f"{arm}_wrong_grids"] = n
        res[f"{arm}_false_squares"] = sum(st[f"{arm}_false_{k}"] for k in "AC")
        res[f"{arm}_wrong_A_share"] = round(st[f"{arm}_wrong_A"] / n, 3) if n else None
        res[f"{arm}_wrong_B_share"] = round(st[f"{arm}_wrong_B"] / n, 3) if n else None
    n7 = res["L7_wrong_grids"]
    if n7 < MIN_WRONG:
        res["distractor_block_idea"] = "TOO-FEW (decides nothing)"
    else:
        res["distractor_block_idea"] = "SUNK" if st["L7_wrong_A"] * 3 < n7 else "NOT-SUNK"
    print(json.dumps(dict(sorted(st.items()))))
    print(json.dumps(dict(sorted(detail.items()))))
    print(json.dumps(res))


# ------------------------------------------------------------------ selftest
def selftest() -> None:
    ok = 0
    truth = [[1, 2, 3, 4], [2, 1, 4, 3], [3, 4, 1, 2], [4, 3, 2, 1]]
    text, cells = G1.render_recipe(truth, G1.layout_recipe("row", 4))          # Row 1: 1 2 3 4 ...
    T = tokens(text, cells)
    ok += kind_wrong([[1, 2, 3, 4], [2, 1, 4, 3], [3, 4, 1, 2], [4, 3, 2, 2]], truth, T) == "B"   # one slip
    ok += kind_wrong([[1, 2, 3, 4], [3, 4, 1, 2], [4, 3, 2, 1], [4, 3, 2, 1]], truth, T) == "B"   # skipped a row
    ok += kind_wrong([[1, 1, 2, 3], [4, 2, 2, 1], [4, 3, 3, 3], [4, 1, 2, 4]], truth, T) == "A"   # labels as cells
    ok += kind_wrong([[1, 3, 2, 4], [3, 1, 4, 2], [3, 4, 1, 2], [4, 3, 2, 1]], truth, T) == "C"   # rows not there
    ok += kind_false([[1, 2], [3, 4]], tokens("a 1 2\nb 3 4 5", [])) == "A"
    ok += kind_false([[4, 3], [2, 1]], tokens("a 1 2\nb 3 4 5", [])) == "C"
    ok += lev("abc", "abd") == 1 and lev("", "ab") == 2
    fm = draw_formats()
    ok += len(fm) == N_FORMATS and sum(f["group"] == "seen" for f in fm) == N_FORMATS // 2
    print(f"gr7d selftest {ok}/8")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--out", required=True)
    c = sub.add_parser("count")
    c.add_argument("--practice", required=True)
    c.add_argument("--run", required=True)
    a = ap.parse_args()
    {"make": make, "count": count}[a.cmd](a)


if __name__ == "__main__":
    main()
