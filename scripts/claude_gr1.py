#!/usr/bin/env python3
"""gr-1: a learned reader finds the number square in a chat message (Plain-English puzzles thread, 2026-09-26).

Marks: artifacts/claude-gr1-20260926/PASSMARKS-gr1.md, written before any head or panel. Blind TEST-ONLY panel:
artifacts/claude-panel-gr1-20260926. Only `run` and `score` read it, and they print counts only.

Brain first: a person reads a grid by seeing the layout, not by retyping it. The plain 1B (every LoRA scale 0) reads
the message twice in one prompt (ECHO), so the second copy's tokens can attend to the whole message. A small learned
head (multinomial logistic regression on one layer's hidden state) labels each token of the second copy O, B (the
first cell of a row) or I (a later cell). A cell's value is the token it points at: its digit, or "_" for a blank.
Code accepts the result only if it is s rows of s cells with 3 <= s <= 9 and values 1..s or blank.

Training text is only the 1B's own words (claude_gr1_drafts.py wrappers; rt-02h's 1B drafts). Squares, number blocks
and labels are built by code.

  python -B scripts/claude_gr1.py --selftest
  python -B scripts/claude_gr1.py build --wrap WRAP.jsonl --rt02h artifacts/claude-rt02h-20260926/train/drafts_1b.jsonl --out TRAIN.jsonl
  python -B scripts/claude_gr1.py feats --model BASE --train TRAIN.jsonl --out FEATS.pt
  python -B scripts/claude_gr1.py fit --feats FEATS.pt --head HEAD.pt
  python -B scripts/claude_gr1.py dev --model BASE --head HEAD.pt                         (dev data only; report)
  python -B scripts/claude_gr1.py run --task squares|lookalikes|general --model BASE --head HEAD.pt --panel-dir PD --out OUT
  python -B scripts/claude_gr1.py score --out OUT --panel-dir PD --score SCOREDIR
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ECHO_HEAD = "Read this message carefully.\n\n{text}\n\nThe same message again:\n\n"
LAYERS = [8, 16, 24]
TAGS = ("O", "B", "I")
TRAIN_SEED = 486000
_CELL = re.compile(r"[0-9]|_")
_MENTION = re.compile(r"\b(blanks?|underscores?)\b", re.I)
_MARKS = (" (_)", ' ("_")', " '_'", " _")


# ------------------------------------------------------------------ squares as text, with cell positions
RECIPE_KEYS = ("before", "after", "row_prefix", "sep", "row_suffix", "row_join", "divider", "header", "header_prefix",
               "header_sep", "header_suffix")
LAYOUTS = ("row", "bare", "pipe", "comma", "md", "latex", "label", "colhead")      # practice layouts (ADDENDUM-gr1-1)


def render_recipe(grid, rc):
    """a grid written in a format recipe (the RECIPE_KEYS; {i} = row number, {A} = row letter in row_prefix):
    the text and [(char index, row, col)] of every cell in it"""
    L = "ABCDEFGHI"
    text, cells = (rc["before"] + "\n") if rc["before"] else "", []
    m = max(len(r) for r in grid)
    if rc["header"] != "none":
        labels = [str(c + 1) if rc["header"] == "numbers" else L[c] for c in range(m)]
        text += rc["header_prefix"] + rc["header_sep"].join(labels) + rc["header_suffix"] + "\n"
    for r, row in enumerate(grid):
        if r:
            text += rc["row_join"]
            if rc["row_join"] == "\n" and rc["divider"]:
                text += rc["divider"] + "\n"
        text += rc["row_prefix"].replace("{i}", str(r + 1)).replace("{A}", L[r])
        for c, v in enumerate(row):
            if c:
                text += rc["sep"]
            cells.append((len(text), r, c))
            text += "_" if v == 0 else str(v)
        text += rc["row_suffix"]
    if rc["after"]:
        text += "\n" + rc["after"]
    return text, cells


def layout_recipe(layout, m, variant=0):
    """the practice layouts as recipes (m = number of columns)"""
    rc = dict.fromkeys(RECIPE_KEYS, "")
    rc.update(row_join="\n", header="none", sep=" ")
    if layout == "row":
        rc.update(row_prefix="Row {i}: ")
    elif layout == "pipe":
        rc.update(row_prefix="| ", sep=" | ", row_suffix=" |")
    elif layout == "comma":
        rc.update(sep=", ")
    elif layout == "md":
        rc.update(header=("letters", "numbers")[variant % 2], header_prefix="| " + ("", "C")[variant % 2],
                  header_sep=(" | ", " | C")[variant % 2], header_suffix=" |\n|" + "---|" * m, row_prefix="| ",
                  sep=" | ", row_suffix=" |")
    elif layout == "latex":
        rc.update(before=("", "$$\n")[variant % 2] + "\\begin{array}{" + "c" * m + "}", sep=" & ", row_suffix=" \\\\",
                  after="\\end{array}" + ("", "\n$$")[variant % 2])
    elif layout == "label":
        rc.update(row_prefix=("{A}: ", "R{i}: ", "{i}) ", "row {i} - ")[variant % 4])
    elif layout == "colhead":
        rc.update(header=("numbers", "letters")[variant % 2], header_prefix="    ", header_sep=" ",
                  row_prefix=("{i} | ", "{A} | ")[(variant // 2) % 2])
    else:
        assert layout == "bare", layout
    return rc


def render(grid, layout, variant=0):
    """text of the square and [(char index, row, col)] of every cell in it"""
    return render_recipe(grid, layout_recipe(layout, max(len(r) for r in grid), variant))


def decode(text, spans, tags):
    rows = []
    for (a, b), t in zip(spans, tags):
        if t == 0:
            continue
        m = _CELL.search(text[a:b])
        if not m:
            return None
        v = 0 if m.group(0) == "_" else int(m.group(0))
        if t == 1 or not rows:
            rows.append([])
        rows[-1].append(v)
    s = len(rows)
    if not 3 <= s <= 9 or any(len(r) != s for r in rows) or any(not 0 <= v <= s for r in rows for v in r):
        return None
    if all(v == 0 for r in rows for v in r):
        return None
    return rows


def token_tags(spans, cells):
    tags, clash = [], 0
    for a, b in spans:
        inside = [(r, c) for i, r, c in cells if a <= i < b]
        clash += int(len(inside) > 1)
        tags.append(0 if not inside else (1 if inside[0][1] == 0 else 2))
    return tags, clash


# ------------------------------------------------------------------ training messages (1B words + code squares)
def build(a) -> None:
    import claude_rsn358b2_bridge as B
    import claude_rsn358b3_panel as P3
    rng = random.Random(TRAIN_SEED)
    wr = [json.loads(x) for x in Path(a.wrap).read_text().splitlines()]
    openers = [r["text"] for r in wr if r["keep"] and r["kind"] == "opener"]
    closers = [r["text"] for r in wr if r["keep"] and r["kind"] == "closer"]
    named = [t for t in openers + closers if _MENTION.search(t)]    # 1B words that name the blank mark (ADDENDUM-gr1-2)

    def mark(t):
        """code writes the blank mark after the 1B's own word for it, e.g. 'blanks' -> 'blanks (_)'"""
        m = _MENTION.search(t)
        return t[:m.end()] + rng.choice(_MARKS) + t[m.end():]
    d1b = [json.loads(x) for x in Path(a.rt02h).read_text().splitlines()]
    everyday = [r["raw"] for r in d1b]
    out = []
    for i in range(360):                                            # squares inside the 1B's words
        s = rng.choice([3, 4, 5, 5, 6, 6, 7, 7, 8])
        puz = B.make_requests(TRAIN_SEED + i, 1, s, False)[0]["puz"]
        if rng.random() < 0.2 and any(any(row) and not all(row) for row in puz):    # a row with a clue and a blank
            puz = P3._broken(rng, puz, s)
        layout = rng.choice(["row", "bare"] + list(LAYOUTS))
        sq, cells = render(puz, layout, rng.randrange(4))
        o, c = rng.choice(openers), (rng.choice(closers) if closers and rng.random() < 0.5 else "")
        if named and rng.random() < 0.3:
            o = mark(rng.choice(named))
        if rng.random() < 0.75:
            pre, post = o + "\n", ("\n" + c if c else "")
        else:
            pre, post = "", "\n" + o
        out.append({"text": pre + sq + post, "cells": [(i0 + len(pre), r, cc) for i0, r, cc in cells], "grid": puz,
                    "kind": "square"})
    for t in rng.sample(everyday, 240):                             # the 1B's own messages with numbers
        out.append({"text": t, "cells": [], "grid": None, "kind": "everyday"})
    for t in rng.sample(openers, min(60, len(openers))):             # asks with no square pasted
        out.append({"text": t, "cells": [], "grid": None, "kind": "opener_only"})
    for t in (rng.choice(named) for _ in range(40 if named else 0)):  # the blank mark in words, no square
        out.append({"text": mark(t), "cells": [], "grid": None, "kind": "mark_only"})
    for i in range(160):                                            # number blocks that are not squares
        s = rng.randint(3, 7)
        kind = ["ragged", "big", "short", "wide", "oneline", "fmt_wide", "fmt_big"][i % 7]
        if kind == "ragged":
            g = [[rng.randint(1, s) for _ in range(s + (1 if r == 1 else 0))] for r in range(s)]
        elif kind == "big":
            g = [[rng.randint(10, 59) for _ in range(s)] for _ in range(s)]
        elif kind == "short":
            g = [[rng.randint(1, s) for _ in range(s)] for _ in range(2)]
        elif kind == "wide":
            g = [[rng.randint(1, s) for _ in range(s + 1)] for _ in range(s)]
        elif kind == "oneline":
            g = [[rng.randint(1, 9) for _ in range(s * 2)]]
        elif kind == "fmt_wide":                                    # practice layouts with a column too many
            g = [[rng.randint(1, s) for _ in range(s + 1)] for _ in range(s)]
        else:                                                       # practice layouts with numbers above 9
            g = [[rng.randint(10, 59) for _ in range(s)] for _ in range(s)]
        if kind.startswith("fmt_"):
            blk = render(g, rng.choice(LAYOUTS[2:]), rng.randrange(4))[0]
        else:
            blk = "\n".join(" ".join(str(v) for v in row) for row in g)
        t = rng.choice(everyday + openers)
        out.append({"text": t + "\n" + blk if rng.random() < 0.6 else blk + "\n" + t, "cells": [], "grid": None,
                    "kind": "block_" + kind})
    rng.shuffle(out)
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    print(json.dumps(Counter(r["kind"] for r in out)))


# ------------------------------------------------------------------ features
def encode(one_b, text, layers=LAYERS):
    """hidden states [n_tokens, len(layers), d] (fp16) of the second copy, and each token's span in `text`"""
    import claude_sleep02c as SL
    tok, model, torch = one_b.tok, one_b.model, one_b.torch
    head = ECHO_HEAD.format(text=text)
    enc = tok(head + text, return_offsets_mapping=True, return_tensors="pt")
    offs = enc.pop("offset_mapping")[0].tolist()
    start = len(head)
    idx = [i for i, (x, y) in enumerate(offs) if y > start and y > x]
    spans = [(max(x, start) - start, y - start) for x, y in (offs[i] for i in idx)]
    mods = SL.lora_mods(model)
    saved = [m.scale for m in mods]
    for m in mods:
        m.scale = 0.0
    try:
        with torch.no_grad():
            hs = model(**enc.to(one_b.dev), output_hidden_states=True).hidden_states
    finally:
        for m, sc in zip(mods, saved):
            m.scale = sc
    H = torch.stack([hs[l][0, idx].float() for l in layers], dim=1).half().cpu()
    return H, spans


def feats(a) -> None:
    import torch
    import claude_rt02g as G
    one_b = G.load_one_b(a.model)
    rows = [json.loads(x) for x in Path(a.train).read_text().splitlines()]
    Hs, T, meta, clash = [], [], [], 0
    t0 = time.time()
    for i, r in enumerate(rows):
        H, spans = encode(one_b, r["text"])
        tags, c = token_tags(spans, r["cells"])
        clash += c
        Hs.append(H)
        T.append(torch.tensor(tags))
        meta.append({"text": r["text"], "spans": spans, "grid": r["grid"], "kind": r["kind"]})
        if i % 50 == 0:
            print(i, len(rows), round(time.time() - t0), flush=True)
    assert clash == 0, clash
    torch.save({"H": Hs, "T": T, "meta": meta}, a.out)


# ------------------------------------------------------------------ head
def _fit(X, y, l2, steps=200):
    import torch
    mu, sd = X.mean(0), X.std(0) + 1e-4
    Z = (X - mu) / sd
    W = torch.zeros(Z.shape[1], 3, requires_grad=True)
    b = torch.zeros(3, requires_grad=True)
    opt = torch.optim.LBFGS([W, b], max_iter=steps, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = torch.nn.functional.cross_entropy(Z @ W + b, y) + l2 * (W * W).sum()
        loss.backward()
        return loss
    opt.step(closure)
    return {"mu": mu, "sd": sd, "W": W.detach().clone(), "b": b.detach().clone()}


def predict(head, H):
    x = H[:, head["layer_index"]].float()
    return (((x - head["mu"]) / head["sd"]) @ head["W"] + head["b"]).argmax(1).tolist()


def _exact(meta, grid):
    return grid == meta["grid"]


def fit(a) -> None:
    import torch
    d = torch.load(a.feats)
    Hs, T, meta = d["H"], d["T"], d["meta"]
    n = len(meta)
    fold = [i % 5 for i in range(n)]
    best = None
    for li, layer in enumerate(LAYERS):
        for l2 in (1e-3, 1e-2):
            ok = 0
            for f in range(5):
                tr = [i for i in range(n) if fold[i] != f]
                X = torch.cat([Hs[i][:, li].float() for i in tr])
                y = torch.cat([T[i] for i in tr])
                h = {**_fit(X, y, l2), "layer_index": li}
                for i in (i for i in range(n) if fold[i] == f):
                    ok += int(_exact(meta[i], decode(meta[i]["text"], meta[i]["spans"], predict(h, Hs[i]))))
            print(f"layer {layer} l2 {l2:g}: cv messages read exactly {ok}/{n}", flush=True)
            if best is None or ok > best[0]:
                best = (ok, li, l2)
    ok, li, l2 = best
    X = torch.cat([H[:, li].float() for H in Hs])
    y = torch.cat(T)
    head = {**_fit(X, y, l2), "layer_index": li, "layer": LAYERS[li], "l2": l2, "cv_exact": ok, "n_train": n}
    torch.save(head, a.head)
    print(json.dumps({"layer": LAYERS[li], "l2": l2, "cv_exact": ok, "n": n}))


def read_grid(one_b, head, text):
    """the learned reading: s rows of s ints (0 = blank), or None"""
    H, spans = encode(one_b, text)
    return decode(text, spans, predict(head, H))


# ------------------------------------------------------------------ dev (dev data only; report)
def dev(a) -> None:
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    import claude_puzzle_reader as R
    import claude_rsn358b2_bridge as B
    import claude_rt02d as RT
    import claude_rt02g as G
    import torch
    one_b = G.load_one_b(a.model)
    head = torch.load(a.head)
    root = SCRIPTS.parent
    st = Counter()
    sm = root / "artifacts/claude-panel-rsn358b3-smoke-20260926"
    ans = {r["id"]: r for r in map(json.loads, (sm / "answers.jsonl").read_text().splitlines())}
    for r in map(json.loads, (sm / "panel.jsonl").read_text().splitlines()):
        g = read_grid(one_b, head, r["message"])
        st["smoke_n"] += 1
        st["smoke_exact"] += int(g == ans[r["id"]]["puz"])
        st["smoke_wrong"] += int(g is not None and g != ans[r["id"]]["puz"])
    for s in (4, 5, 6, 7):
        for k, rq in enumerate(B.make_requests(487000 + s, 6, s, False)):
            g = read_grid(one_b, head, rq["text"])
            st["fresh_n"] += 1
            st["fresh_exact"] += int(g == rq["puz"])
            st["fresh_wrong"] += int(g is not None and g != rq["puz"])
    texts = [t for t, _ in RT.dev_cases()]
    prac = json.loads((root / "artifacts/claude-rt02e-20260926/practice/wordings_practice.json").read_text())
    ps = B2.puzzles(4881, len(prac["puzzle_templates"]))
    texts += [t.replace("{L}", ", ".join(map(str, p["nums"]))).replace("{T}", str(p["target"]))
              for t, p in zip(prac["puzzle_templates"], ps)] + prac["negatives"]
    for t in texts:
        st["nosquare_n"] += 1
        st["nosquare_fired"] += int(read_grid(one_b, head, t) is not None)
        st["nosquare_fired_codestandin"] += int(R.read_latin(t) is not None)
    print(json.dumps(dict(sorted(st.items()))))


# ------------------------------------------------------------------ registered run and score
def _load(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def run(a) -> None:
    import claude_dl1_nights as D1
    import claude_rt02g as G
    import torch
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"L_{a.task}.jsonl"
    if path.exists():
        raise SystemExit(f"gr1: {path} exists (each run is launched once)")
    if a.task == "general":
        items = [{"id": "gen-%03d" % i, "text": it["q"]} for i, it in enumerate(D1.harm_panel())]
    else:
        items = _load(Path(a.panel_dir) / {"squares": "squares.jsonl", "lookalikes": "lookalikes.jsonl",
                                           "unseen": "unseen.jsonl"}[a.task])
    head = torch.load(a.head)
    one_b = G.load_one_b(a.model)
    rows = []
    for it in items:
        t0 = time.time()
        g = read_grid(one_b, head, it["text"])
        rows.append({"id": it["id"], "grid": g, "ms": round((time.time() - t0) * 1000, 1)})
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"task": a.task, "rows": len(rows), "read_as_square": sum(r["grid"] is not None for r in rows)}))


def score(a) -> None:
    import claude_dl1_nights as D1
    import claude_puzzle_reader as R
    out, pd = Path(a.out), Path(a.panel_dir)
    sq, lk = _load(pd / "squares.jsonl"), _load(pd / "lookalikes.jsonl")
    Ls = {r["id"]: r["grid"] for r in _load(out / "L_squares.jsonl")}
    Ll = {r["id"]: r["grid"] for r in _load(out / "L_lookalikes.jsonl")}
    Lg = _load(out / "L_general.jsonl")
    assert set(Ls) == {r["id"] for r in sq} and set(Ll) == {r["id"] for r in lk} and len(Lg) == 300
    res = {}
    for arm, rd in (("L", lambda r: Ls[r["id"]]), ("C", lambda r: (R.read_latin(r["text"]) or {}).get("grid"))):
        got = {r["id"]: rd(r) for r in sq}
        res[arm] = {"squares_exact": sum(int(got[r["id"]] == r["grid"]) for r in sq),
                    "squares_wrong": sum(int(got[r["id"]] is not None and got[r["id"]] != r["grid"]) for r in sq),
                    "squares_none": sum(int(got[r["id"]] is None) for r in sq)}
        by = Counter()
        for r in sq:
            e = int(got[r["id"]] == r["grid"])
            by[f"size{r['size']}"] += e
            by[f"layout_{r['layout']}"] += e
            by["broken" if r["broken"] else "whole"] += e
        res[arm]["exact_by"] = dict(sorted(by.items()))
    lkg = {"L": {r["id"]: Ll[r["id"]] for r in lk},
           "C": {r["id"]: (R.read_latin(r["text"]) or {}).get("grid") for r in lk}}
    for arm in ("L", "C"):
        res[arm]["lookalikes_false_square"] = sum(int(r["square"] is None and lkg[arm][r["id"]] is not None) for r in lk)
        res[arm]["lookalikes_truth_square"] = sum(int(r["square"] is not None) for r in lk)
    res["L"]["general_read_as_square"] = sum(int(r["grid"] is not None) for r in Lg)
    res["C"]["general_read_as_square"] = sum(int(R.read_latin(it["q"]) is not None) for it in D1.harm_panel())
    res["L"]["ms_median"] = sorted(r["ms"] for r in Lg)[150]
    L = res["L"]
    res["marks"] = {"R1": L["squares_exact"] >= 97, "R2": L["lookalikes_false_square"] <= 1,
                    "R3": L["squares_wrong"] <= 1, "R4": L["general_read_as_square"] == 0}
    res["pass"] = all(res["marks"].values())
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "gr1_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"L": {k: v for k, v in L.items() if k != "exact_by"},
                      "C": {k: v for k, v in res["C"].items() if k != "exact_by"}, "marks": res["marks"],
                      "pass": res["pass"]}))


def scoreu(a) -> None:
    """gr-1U (ADDENDUM-gr1-1): the same head on squares in 20 formats practice never had (a blind writer's recipes)"""
    import claude_puzzle_reader as R
    out, pd = Path(a.out), Path(a.panel_dir)
    un = _load(pd / "unseen.jsonl")
    Lu = {r["id"]: r["grid"] for r in _load(out / "L_unseen.jsonl")}
    assert set(Lu) == {r["id"] for r in un}
    res = {}
    for arm, rd in (("L", lambda r: Lu[r["id"]]), ("C", lambda r: (R.read_latin(r["text"]) or {}).get("grid"))):
        got = {r["id"]: rd(r) for r in un}
        ex = {r["id"]: int(got[r["id"]] == r["grid"]) for r in un}
        by_fmt = Counter()
        for r in un:
            by_fmt[r["format_id"]] += ex[r["id"]]
        res[arm] = {"exact": sum(ex.values()),
                    "wrong": sum(int(got[r["id"]] is not None and got[r["id"]] != r["grid"]) for r in un),
                    "none": sum(int(got[r["id"]] is None) for r in un),
                    "exact_without_token_clash": sum(ex[r["id"]] for r in un if not r["token_clash"]),
                    "formats_all_exact": sum(int(by_fmt[f] == 3) for f in {r["format_id"] for r in un}),
                    "formats_none_exact": sum(int(by_fmt[f] == 0) for f in {r["format_id"] for r in un}),
                    "exact_by_format": dict(sorted(by_fmt.items()))}
    res["n"], res["token_clash_items"] = len(un), sum(int(r["token_clash"]) for r in un)
    res["marks"] = {"U1": res["L"]["exact"] >= 48, "U2": res["L"]["wrong"] <= 2}
    res["pass"] = all(res["marks"].values())
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "gr1u_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk != "exact_by_format"} if isinstance(v, dict) and
                          k in "LC" else v) for k, v in res.items()}))


# ------------------------------------------------------------------ selftest (no model)
def selftest() -> None:
    import claude_rsn358b2_bridge as B
    n = 0
    for layout in LAYOUTS:
        for s in (3, 5, 8):
            puz = B.make_requests(489000 + s, 1, s, False)[0]["puz"]
            txt, cells = render(puz, layout, s)
            assert len(cells) == s * s and all(txt[i] in "_123456789" for i, _, _ in cells)
            # character-level "tokens": each char its own span
            spans = [(i, i + 1) for i in range(len(txt))]
            tags, clash = token_tags(spans, cells)
            assert clash == 0 and decode(txt, spans, tags) == puz, (layout, s)
            n += 1
    assert decode("1 2\n2 1", [(0, 1), (2, 3), (4, 5), (6, 7)], [1, 2, 1, 2]) is None; n += 1   # 2x2 too small
    assert decode("_ _ _", [(0, 1), (2, 3), (4, 5)], [1, 2, 2]) is None; n += 1                 # not square
    print(f"gr1 selftest {n}/{n}")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "feats", "fit", "dev", "run", "score", "scoreu"])
    for k in ("wrap", "rt02h", "out", "model", "train", "feats", "head", "task", "panel-dir", "score"):
        ap.add_argument("--" + k, default="")
    a = ap.parse_args()
    {"build": build, "feats": feats, "fit": fit, "dev": dev, "run": run, "score": score, "scoreu": scoreu}[a.cmd](a)


if __name__ == "__main__":
    main()
