#!/usr/bin/env python3
"""gr-9: separator variety for the trained reader (Plain-English puzzles thread, 2026-09-27; PASSMARKS-gr9.md).

gr-7d and gr-8 (RESULT-gr7d, RESULT-gr8d) found, on practice data, that gr-7's reader reads 99 of 100 squares in new
formats whose cell separator it saw in training, and far fewer when the separator is new. Fixing only the grid size
(gr-8) left the grids wrong. The one change here is separator variety in the training rows, sealed as one recipe:
  1. A disclosed list of 59 marks (SEP_MARKS, hand-written scaffolding) is split by code into three sets that share no
     character (marks that look alike count as one character, LOOKS; marks sharing a character with a separator gr-6
     trained on are dropped). Dev held-out = the families of the four marks that failed most in gr-8 (" . ", " * ",
     "=", " : "); test held-out = families drawn with seed 5091 until it holds at least 10 marks; training = the rest.
  2. 300 code-made squares spread evenly over the training marks, in formats drawn from gr-6's and gr-7d's part lists,
     inside the 1B's own openers and closers, and 80 near misses in those formats, labelled none, as gr-6 built them.
  3. These rows are added to gr-6's 1072 training rows, and gr-7's adapter trains for 3 more epochs on the union with
     gr-5's recipe (AdamW with fresh moments, constant lr 2e-4, batch 8, loss on the answer only), seed 5090.
Dev is a fresh code-made practice set. Every mark uses the greedy read (claude_gr5.Copier5, as in gr-7). The size pick
(claude_gr8.Copier8) is run on the same pass and reported only.

  python -B scripts/claude_gr9.py --selftest
  python -B scripts/claude_gr9.py build --out ROWS.jsonl
  python -B scripts/claude_gr9.py train --model BASE --rows ROWS.jsonl --start GR7_ADAPTER.pt --adapter ADAPTER.pt
  python -B scripts/claude_gr9.py make --out DEV_DIR
  python -B scripts/claude_gr9.py run --task squares|seen|heldout|lookalikes --arm L9|L7 --model BASE --adapter A.pt \
      --dev DEV_DIR --out OUT
  python -B scripts/claude_gr9.py count --dev DEV_DIR --run OUT
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_gr1 as G1  # noqa: E402
import claude_gr5 as G5  # noqa: E402
import claude_gr6 as G6  # noqa: E402
import claude_gr7_diag as DG  # noqa: E402

ROOT = SCRIPTS.parent
SEED_SPLIT, SEED_TRAIN, SEED_BUILD, SQ_SEED0 = 5091, 5090, 5097, 509000     # train squares: make_requests 509000-509299
SEED_SQ, SEED_SEEN, SEED_HO, SEED_FMT, SEED_LK, SEED_WRAP = 5092, 5093, 5094, 5095, 5096, 5098
EPOCHS = 3
N_NEAR = 80

# ------------------------------------------------------------------ the separator marks (hand-written list, disclosed)
SEP_MARKS = [".", "*", "=", ":", "-", "~", "+", "#", "^", "%", "$", "@", "!", "?", "'", '"', "`", "\\", "°", "·", "•",
             "×", "÷", "…", "¦", "§", "¤", "†", "∙", "○", "±", "::", "--", "..", "**", "==", "~~", "++", "||", "//",
             ":-", "-:", "^^", "!!", "''", "¬", "¶", "©", "¥", "£", "€", "¢", "µ", "■", "♦", "«", "»", "¿", "‡"]
# marks that look alike count as one character, so lookalikes never cross sets (hand-written, disclosed; it can only
# make the held-out sets harder, never easier)
LOOKS = {"·": ".", "∙": ".", "•": ".", "…": ".", "×": "*", "†": "+", "‡": "+", "±": "+", "°": "○", "`": "'",
         '"': "'", "¿": "?", "«": "»", "¦": "|"}
FORCED_DEV = [".", "*", "=", ":"]                     # the four that failed most in gr-8 (Thread manager, point 2)
N_TEST, N_TRAIN_SQ = 10, 300


def _chars(mark):
    return {LOOKS.get(c, c) for c in mark}


def families():
    """the marks grouped so that two marks sharing a character (after LOOKS) are in one family; marks sharing a
    character with a separator gr-6 trained on are dropped"""
    seen = G6.training_seps(G6.draw_layouts())
    seen_chars = {c for x in seen for c in x if not c.isspace()}
    marks = [m for m in SEP_MARKS if not (_chars(m) & seen_chars)]
    assert len(set(SEP_MARKS)) == len(SEP_MARKS) and all(G6._norm(m) == m and G6._norm(m) not in seen for m in marks)
    fams = []
    for m in marks:
        hit = [f for f in fams if any(_chars(m) & _chars(x) for x in f)]
        merged = [m] + [x for f in hit for x in f]
        fams = [f for f in fams if f not in hit] + [merged]
    return [sorted(f, key=marks.index) for f in sorted(fams, key=lambda f: min(marks.index(x) for x in f))]


def split_seps():
    """(train, dev, test): lists of marks drawn by families, so no character (after LOOKS) is in two sets; dev = the
    families of the four forced marks; test = families drawn with seed 5091 until it holds at least 10 marks"""
    fams = families()
    dev_f = [f for f in fams if set(f) & set(FORCED_DEV)]
    rest = [f for f in fams if f not in dev_f]
    random.Random(SEED_SPLIT).shuffle(rest)
    test_f = []
    while sum(map(len, test_f)) < N_TEST:
        test_f.append(rest.pop(0))
    flat = lambda fs: [m for f in fs for m in f]  # noqa: E731
    return flat(rest), flat(dev_f), flat(test_f)


def _sep_string(rng, mark):
    return rng.choice([" " + mark + " ", mark + " ", mark])


def draw_format(rng, mark=None, seps=None, taken=None):
    """one format from gr-6's and gr-7d's part lists; with mark, its separator is that mark (spacing drawn); a format
    whose row label or row end uses the separator's mark is redrawn (ambiguous); taken = signatures to avoid"""
    while True:
        rc = DG._draw_format(rng, seps or [_sep_string(rng, mark)])
        if mark is not None:
            s = _sep_string(rng, mark)
            rc["sep"] = s
            if rc["header"] != "none":
                rc["header_sep"] = s
        ns = G6._norm(rc["sep"])
        if rc["row_join"] not in ("\n", "\n\n") and G6._norm(rc["row_join"]) == ns:
            continue
        if ns and (ns in G6._norm(rc["row_prefix"]) or ns in G6._norm(rc["row_suffix"])):
            continue
        if ns and rc["header"] != "none" and ns in G6._norm(rc["header_prefix"]):
            continue
        if ns and any(ns in G6._norm(rc[k]) for k in ("divider", "before", "after")):
            continue
        if taken is not None and G6.signature(rc) in taken:
            continue
        return rc


def _pools():
    wr = G5._load(G6.GR1_WRAP)
    openers = [r["text"] for r in wr if r["keep"] and r["kind"] == "opener"]
    closers = [r["text"] for r in wr if r["keep"] and r["kind"] == "closer"]
    everyday = [r["raw"] for r in G5._load(G6.RT02H)]
    return openers, closers, everyday


def _near(rng, recipes, contexts):
    import claude_puzzle_reader as R
    while True:
        s = rng.randint(3, 7)
        g = [[rng.randint(1, 9) for _ in range(s)] for _ in range(s)]
        if max(v for row in g for v in row) <= s:
            g[rng.randrange(s)][rng.randrange(s)] = rng.randint(s + 1, 9)
        if rng.random() < 0.5:
            g = [[0 if (rng.random() < 0.25 and v <= s) else v for v in row] for row in g]
        blk = G1.render_recipe(g, rng.choice(recipes))[0]
        t = rng.choice(contexts)
        text = t + "\n" + blk if rng.random() < 0.6 else blk + "\n" + t
        if R.read_latin(text) is None:
            return text


# ------------------------------------------------------------------ training rows
def build(a) -> None:
    import claude_rsn358b2_bridge as B
    import claude_rsn358b3_panel as P3
    train_marks, _, _ = split_seps()
    rng = random.Random(SEED_BUILD)
    openers, closers, everyday = _pools()
    rows = [dict(r) for r in G5._load(ROOT / "artifacts/claude-gr6-20260927/train/rows.jsonl") if r["split"] == "train"]
    recipes = []
    for i in range(N_TRAIN_SQ):
        mark = train_marks[i % len(train_marks)]
        rc = draw_format(rng, mark)
        recipes.append(rc)
        s = rng.choice([3, 4, 5, 5, 6, 6, 7, 7, 8])
        puz = B.make_requests(SQ_SEED0 + i, 1, s, False)[0]["puz"]
        if rng.random() < 0.2 and any(any(row) and not all(row) for row in puz):
            puz = P3._broken(rng, puz, s)
        sq, cells = G1.render_recipe(puz, rc)
        text, _ = DG._wrap(rng, openers, closers, sq, cells)
        rows.append({"kind": "sq_sep", "text": text, "grid": puz, "split": "train", "sep_mark": mark,
                     "target": G5.target_of(puz)})
    for _ in range(N_NEAR):
        rows.append({"kind": "near_sep", "text": _near(rng, recipes, everyday + openers), "grid": None,
                     "split": "train", "target": "none"})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"rows": len(rows), **Counter(r.get("kind", "gr6") for r in rows),
                      "train_marks": len(train_marks)}))


def train(a) -> None:
    import claude_sleep02c as SL
    import torch
    one_b = G5.load(a.model, a.start)                       # gr-7's A and B copied into the LoRA layers
    rows = [r for r in G5._load(a.rows) if r["split"] == "train"]
    params = [p for p in one_b.model.parameters() if p.requires_grad]
    assert params and len(params) == 2 * len(SL.lora_mods(one_b.model)), "gr9: only the LoRA A and B may train"
    opt = torch.optim.AdamW(params, lr=G5.LR)
    t0 = time.time()
    per_epoch, done = G5._steps(one_b, rows, EPOCHS, SEED_TRAIN, opt)
    torch.save([(m.A.detach().cpu(), m.B.detach().cpu()) for m in SL.lora_mods(one_b.model)], a.adapter)
    print(json.dumps({"device": one_b.dev, "train_rows": len(rows), "examples_seen": done,
                      "mean_loss_by_epoch": per_epoch, "minutes": round((time.time() - t0) / 60, 1)}))


# ------------------------------------------------------------------ the fresh dev practice set
def make(a) -> None:
    import claude_gr5_make_panel as M5
    import claude_puzzle_reader as R
    import claude_rsn358b2_bridge as B
    import claude_rsn358b3_panel as P3
    _, dev_marks, _ = split_seps()
    rng = random.Random(SEED_WRAP)
    openers, closers, everyday = _pools()
    lay = G6.draw_layouts()
    taken = G6.gr1_signatures() | {G6.signature(r) for r in lay}
    seen_raw = [s for s in G6.SEPS if G6._norm(s) in G6.training_seps(lay)]
    frng = random.Random(SEED_FMT)
    seen_fm, ho_fm = [], []
    for _ in range(20):
        rc = draw_format(frng, None, seen_raw, taken)
        taken.add(G6.signature(rc))
        seen_fm.append(dict(rc, id="S%02d" % len(seen_fm)))
    for mark in dev_marks:
        for _ in range(2 if mark in FORCED_DEV else 1):
            rc = draw_format(frng, mark)
            ho_fm.append(dict(rc, id="H%02d" % len(ho_fm), mark=mark))

    def squares_in(seed, fm, prefix):
        out = []
        for i, (s, puz, broken) in enumerate(M5.squares_for(B, P3, seed, 25)):
            f = fm[i % len(fm)]
            sq, cells = G1.render_recipe(puz, f)
            text, cells = DG._wrap(rng, openers, closers, sq, cells)
            out.append({"id": "%s-%03d" % (prefix, i), "text": text, "size": s, "grid": puz, "broken": broken,
                        "format_id": f["id"], "mark": f.get("mark", G6._norm(f["sep"])), "cells": cells})
        return out

    squares, mism = [], 0
    for i, (s, puz, broken) in enumerate(M5.squares_for(B, P3, SEED_SQ, 50)):
        layout = "row" if i % 2 == 0 else "bare"
        sq, cells = G1.render_recipe(puz, G1.layout_recipe(layout, s))
        text, cells = DG._wrap(rng, openers, closers, sq, cells)
        mism += int((R.read_latin(text) or {}).get("grid") != puz)
        squares.append({"id": "d9-sq-%03d" % i, "text": text, "size": s, "grid": puz, "broken": broken,
                        "layout": layout, "cells": cells})
    seen = squares_in(SEED_SEEN, seen_fm, "d9-se")
    held = squares_in(SEED_HO, ho_fm, "d9-ho")
    lrng = random.Random(SEED_LK)
    rec = G6.training_recipes(lay)
    looks = []
    for kind in ("near", "nonsquare", "numbers"):
        n = 0
        while n < DG.N_LK_KIND:
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
            if lrng.random() < 0.5:                        # half in the dev formats (held-out or seen separators)
                fmt = lrng.choice(ho_fm + seen_fm)
                blk, where = G1.render_recipe(g, fmt)[0], fmt["id"]
            else:
                src, rc = lrng.choice(rec)
                blk = G1.render_recipe(g, G1.layout_recipe(rc, shape[1], lrng.randrange(4)) if src == "gr1" else rc)[0]
                where = "train"
            t = lrng.choice(everyday + openers)
            text = t + "\n" + blk if lrng.random() < 0.6 else blk + "\n" + t
            if R.read_latin(text) is not None:
                continue
            looks.append({"id": "d9-lk-%03d" % len(looks), "text": text, "square": None, "kind": kind,
                          "shape": list(shape), "format": where})
            n += 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seal = []
    for name, rows in (("squares.jsonl", squares), ("seen.jsonl", seen), ("heldout.jsonl", held),
                       ("lookalikes.jsonl", looks)):
        p = out / name
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        seal.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}")
    p = out / "formats.json"
    p.write_text(json.dumps({"seen": seen_fm, "heldout": ho_fm}, ensure_ascii=False, indent=1), encoding="utf-8")
    seal.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  formats.json")
    (out / "SEAL-dev.sha256.txt").write_text("\n".join(seal) + "\n")
    print(json.dumps({"squares": len(squares), "squares_read_latin_mismatch": mism, "seen": len(seen),
                      "heldout": len(held), "heldout_marks": dev_marks, "lookalikes": len(looks)}))


# ------------------------------------------------------------------ runs and the count
def run(a) -> None:
    import claude_gr8 as G8
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{a.arm}_{a.task}.jsonl"
    if path.exists():
        raise SystemExit(f"gr9: {path} exists (each run is launched once)")
    items = G5._load(Path(a.dev) / f"{a.task}.jsonl")
    one_b = G5.load(a.model, a.adapter)
    cp8, cp5 = G8.Copier8(one_b, plain=False), None
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            t0 = time.time()
            if a.arm == "L9":
                r = cp8.copy8(it["text"])
                row = {"id": it["id"], "grid": r["greedy"], "pick": r["pick"], "complete": r["complete"]}
            else:
                cp5 = cp5 or G5.Copier5(one_b, plain=False)
                r = cp5.copy(it["text"])
                row = {"id": it["id"], "grid": r["grid"], "complete": r["complete"]}
            f.write(json.dumps({**row, "ms": round((time.time() - t0) * 1000, 1)}) + "\n")
            f.flush()
    rows = G5._load(path)
    print(json.dumps({"arm": a.arm, "task": a.task, "rows": len(rows),
                      "read_as_square": sum(r["grid"] is not None for r in rows)}))


def count(a) -> None:
    dd, rd = Path(a.dev), Path(a.run)
    st = Counter()
    for arm, tasks in (("L9", ("squares", "seen", "heldout", "lookalikes")), ("L7", ("heldout", "lookalikes"))):
        for task in tasks:
            truth = {r["id"]: r for r in G5._load(dd / f"{task}.jsonl")}
            got = G5._load(rd / f"{arm}_{task}.jsonl")
            assert sorted(r["id"] for r in got) == sorted(truth), f"gr9: {arm}_{task} ids differ"
            st[f"{arm}_{task}_incomplete"] += sum(not r["complete"] for r in got)
            for r in got:
                t = truth[r["id"]]
                reads = [("greedy", r["grid"])] + ([("pick", r["pick"])] if "pick" in r else [])
                for how, g in reads:
                    if task == "lookalikes":
                        st[f"{arm}_{how}_lookalikes_false"] += int(g is not None)
                        fm = "train" if t["format"] == "train" else ("heldout" if t["format"][0] == "H" else "seen")
                        st[f"{arm}_{how}_lookalikes_{fm}fmt_false"] += int(g is not None)
                        continue
                    res = "exact" if g == t["grid"] else ("none" if g is None else "wrong")
                    st[f"{arm}_{how}_{task}_{res}"] += 1
                    if task == "heldout":
                        st[f"{arm}_{how}_heldout_mark{t['mark']}_{res}"] += 1
                        if t["mark"] in FORCED_DEV:
                            st[f"{arm}_{how}_heldout_forced4_{res}"] += 1
    ho9, ho7 = st["L9_greedy_heldout_exact"], st["L7_greedy_heldout_exact"]
    marks = {"M1_heldout_at_least_90": ho9 >= 90,
             "M2_squares_at_least_199": st["L9_greedy_squares_exact"] >= 199,
             "M3_seen_at_least_98": st["L9_greedy_seen_exact"] >= 98,
             "M4_false_at_most_L7_plus_1": st["L9_greedy_lookalikes_false"] <= st["L7_greedy_lookalikes_false"] + 1}
    too_easy = ho7 >= 85                                    # gr-7 already reads the held-out set: it tests nothing
    proved_wrong = not too_easy and ho9 - ho7 < 10
    outcome = ("TOO-EASY" if too_easy else "PROVED-WRONG" if proved_wrong else
               "DEV-PASS" if all(marks.values()) else "DEV-FAIL")
    print(json.dumps(dict(sorted(st.items())), ensure_ascii=False))
    print(json.dumps({**marks, "heldout_gain_L9_minus_L7": ho9 - ho7, "too_easy": too_easy,
                      "proved_wrong": proved_wrong,
                      "outcome": outcome}))


# ------------------------------------------------------------------ selftest
def selftest() -> None:
    ok = 0
    tr, dv, te = split_seps()
    ch = [set().union(*map(_chars, x)) for x in (tr, dv, te)]
    ok += len(te) >= N_TEST and len(tr) >= 20 and not (ch[0] & ch[1]) and not (ch[0] & ch[2]) and not (ch[1] & ch[2])
    ok += not (set(tr) & set(dv)) and not (set(tr) & set(te)) and not (set(dv) & set(te))
    ok += all(m in dv for m in FORCED_DEV)
    seen = G6.training_seps(G6.draw_layouts())
    ok += not ({G6._norm(m) for m in tr + dv + te} & seen)
    rng = random.Random(1)
    rc = draw_format(rng, "*")
    ok += G6._norm(rc["sep"]) == "*" and "*" not in G6._norm(rc["row_prefix"])
    print(f"gr9 selftest {ok}/5")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--out", required=True)
    t = sub.add_parser("train")
    for k in ("model", "rows", "start", "adapter"):
        t.add_argument("--" + k, required=True)
    m = sub.add_parser("make")
    m.add_argument("--out", required=True)
    r = sub.add_parser("run")
    for k in ("task", "arm", "model", "adapter", "dev", "out"):
        r.add_argument("--" + k, required=True)
    c = sub.add_parser("count")
    c.add_argument("--dev", required=True)
    c.add_argument("--run", required=True)
    a = ap.parse_args()
    {"build": build, "train": train, "make": make, "run": run, "count": count}[a.cmd](a)


if __name__ == "__main__":
    main()
