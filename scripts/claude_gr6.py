#!/usr/bin/env python3
"""gr-6: wider practice for the trained reader (Plain-English puzzles thread, 2026-09-27; PASSMARKS-gr6.md).

gr-5 (VERIFY-gr5) trained the reader 1B to copy the square or say none: 100 of 100 practice-layout squares exact, but 2
false squares among the lookalikes (both 5 x 5 blocks of single digits that are not a valid partial Latin square) and
40 of 60 in new formats. The one change from gr-5 is its training data, sealed as one recipe:
  1. 40 new layouts drawn by code (seed 5040) from the part lists below (hand-written scaffolding, disclosed), none
     writing a row the same way as gr-1's 8 practice layouts; 32 go to training and 8 to dev only. 8 code-made squares
     per layout inside the 1B's own opener and closer lines, built the way gr-1 built its practice.
  2. 160 near misses: s x s blocks of single digits (s 3-7) with at least one digit above s, in a training layout,
     inside the 1B's own everyday messages or openers, labelled "none"; any block read_latin reads as a square is
     dropped and counted.
The prompt, grammar, decode, LoRA shape and training recipe (seed 4990, 3 epochs, lr 2e-4, batch 8, loss on the answer
only) are gr-5's (claude_gr5.py), unchanged.

"The same format" (PASSMARKS-gr6, sealed): two recipes are the same when they write a row the same way: the same row
label, row wrapper, cell separator, row join and divider, after {i}/{A}/digits become one mark, runs of whitespace
become one space, the ends are trimmed and case is ignored. Headers and lines before/after the grid do not count.

  python -B scripts/claude_gr6.py --selftest
  python -B scripts/claude_gr6.py layouts --out LAYOUTS.json
  python -B scripts/claude_gr6.py build --layouts LAYOUTS.json --out ROWS.jsonl
  python -B scripts/claude_gr6.py train --model BASE --rows ROWS.jsonl --adapter ADAPTER.pt
  python -B scripts/claude_gr6.py dev --model BASE --rows ROWS.jsonl --adapter ADAPTER.pt
  python -B scripts/claude_gr6.py run --task squares|lookalikes|unseen|general --arm L6|G5 --model BASE \
      --adapter ADAPTER.pt --panel-dir PD --out OUT
  python -B scripts/claude_gr6.py score --out OUT --panel-dir PD --score SCOREDIR
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_gr1 as G1  # noqa: E402
import claude_gr5 as G5  # noqa: E402

ROOT = SCRIPTS.parent
SEED_LAYOUTS, SEED_BUILD, SQ_SEED0 = 5040, 5030, 503000     # squares use make_requests seeds 503000-503319
N_LAYOUTS, N_DEV_LAYOUTS, SQ_PER_LAYOUT, N_NEAR = 40, 8, 8, 160
GR5_ROWS = ROOT / "artifacts/claude-gr5-20260926/train/rows.jsonl"
GR1_WRAP = ROOT / "artifacts/claude-gr1-20260926/train/wrap_drafts_1b.jsonl"
RT02H = ROOT / "artifacts/claude-rt02h-20260926/train/drafts_1b.jsonl"

# ------------------------------------------------------------------ the part lists (hand-written scaffolding, disclosed)
LABELS = ["", "Row {i}: ", "{A}: ", "{i}. ", "Line {i}: ", "{i}: ", "R{i} ", "#{i} ", "({A}) ", "row {i} -> "]
WRAPS = [("", ""), ("[", "]"), ("(", ")"), ("{", "}"), ("| ", " |")]
SEPS = [" ", ", ", " | ", " & ", ";", " / ", "\t"]
JOINS = ["\n", "\n\n", " / ", "; "]
DIVIDERS = ["", "", "---", "- - -"]                  # only between lines (row_join "\n")
HEADERS = ["none", "none", "numbers", "letters"]     # only when rows are on their own lines
AROUND = [("", ""), ("", ""), ("```", "```"), ("Grid:", ""), ("[", "]")]


def _norm(x: str) -> str:
    x = x.replace("{i}", "#").replace("{A}", "#")
    x = re.sub(r"\d", "#", x)
    return re.sub(r"\s+", " ", x).strip().lower()


def signature(rc) -> tuple:
    """how a recipe writes a row (PASSMARKS-gr6 "Formats that count as the same")"""
    div = rc.get("divider", "") if rc.get("row_join", "") == "\n" else ""
    return (_norm(rc.get("row_prefix", "")), _norm(rc.get("sep", "")), _norm(rc.get("row_suffix", "")),
            _norm(rc.get("row_join", "")), _norm(div))


def gr1_signatures() -> set:
    return {signature(G1.layout_recipe(lay, 5, v)) for lay in G1.LAYOUTS for v in range(4)}


def _draw_one(rng):
    rc = dict.fromkeys(G1.RECIPE_KEYS, "")
    lab, (wo, wc) = rng.choice(LABELS), rng.choice(WRAPS)
    sep, join = rng.choice(SEPS), rng.choice(JOINS)
    rc.update(row_prefix=lab + wo, sep=sep, row_suffix=wc, row_join=join, header="none")
    if join == "\n":
        rc["divider"] = rng.choice(DIVIDERS)
    if join in ("\n", "\n\n"):
        h = rng.choice(HEADERS)
        if h != "none":
            rc.update(header=h, header_prefix=" " * len((lab + wo).replace("{i}", "1").replace("{A}", "A")),
                      header_sep=sep, header_suffix="")
    rc["before"], rc["after"] = rng.choice(AROUND)
    return rc


def draw_layouts():
    """40 recipes with distinct signatures, none equal to a gr-1 layout; the first 32 train, the last 8 dev only"""
    rng = random.Random(SEED_LAYOUTS)
    taken, out = gr1_signatures(), []
    while len(out) < N_LAYOUTS:
        rc = _draw_one(rng)
        sg = signature(rc)
        if sg in taken:
            continue
        if rc["row_join"] not in ("\n", "\n\n") and _norm(rc["row_join"]) == _norm(rc["sep"]):
            continue                                            # rows on one line need a join unlike the separator
        taken.add(sg)
        out.append(rc)
    order = list(range(N_LAYOUTS))
    rng.shuffle(order)
    dev = set(order[:N_DEV_LAYOUTS])
    return [dict(rc, id="L%02d" % i, split="devlayout" if i in dev else "train") for i, rc in enumerate(out)]


def layouts(a) -> None:
    lay = draw_layouts()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(lay, ensure_ascii=False, indent=1), encoding="utf-8")
    c = Counter(r["split"] for r in lay)
    print(json.dumps({"layouts": len(lay), **c, "one_line_rows": sum(r["row_join"] in (" / ", "; ") for r in lay),
                      "header": sum(r["header"] != "none" for r in lay), "divider": sum(bool(r["divider"]) for r in lay)}))


def training_recipes(lay):
    """the 40 training layouts: gr-1's 8 (a variant drawn per use) and the 32 new ones in the training split"""
    return [("gr1", x) for x in G1.LAYOUTS] + [("new", r) for r in lay if r["split"] == "train"]


def training_seps(lay) -> set:
    return {_norm(G1.layout_recipe(x, 5, v)["sep"]) for x in G1.LAYOUTS for v in range(4)} | \
           {_norm(r["sep"]) for r in lay if r["split"] == "train"}


# ------------------------------------------------------------------ training rows
def build(a) -> None:
    import claude_puzzle_reader as R
    import claude_rsn358b2_bridge as B
    import claude_rsn358b3_panel as P3
    lay = json.loads(Path(a.layouts).read_text(encoding="utf-8"))
    assert [r["id"] for r in lay] == [r["id"] for r in draw_layouts()], "gr6: layouts file is not the sealed draw"
    rng = random.Random(SEED_BUILD)
    wr = G5._load(GR1_WRAP)
    openers = [r["text"] for r in wr if r["keep"] and r["kind"] == "opener"]
    closers = [r["text"] for r in wr if r["keep"] and r["kind"] == "closer"]
    named = [t for t in openers + closers if G1._MENTION.search(t)]
    everyday = [r["raw"] for r in G5._load(RT02H)]

    def mark(t):
        m = G1._MENTION.search(t)
        return t[:m.end()] + rng.choice(G1._MARKS) + t[m.end():]

    rows = [{"kind": r["kind"], "text": r["text"], "grid": r["grid"], "split": r["split"], "target": r["target"]}
            for r in G5._load(GR5_ROWS)]
    new, i = [], 0
    for rc in lay:                                              # 8 squares per new layout, in the 1B's own words
        for _ in range(SQ_PER_LAYOUT):
            s = rng.choice([3, 4, 5, 5, 6, 6, 7, 7, 8])
            puz = B.make_requests(SQ_SEED0 + i, 1, s, False)[0]["puz"]
            i += 1
            if rng.random() < 0.2 and any(any(row) and not all(row) for row in puz):
                puz = P3._broken(rng, puz, s)
            sq = G1.render_recipe(puz, rc)[0]
            o, c = rng.choice(openers), (rng.choice(closers) if closers and rng.random() < 0.5 else "")
            if named and rng.random() < 0.3:
                o = mark(rng.choice(named))
            text = (o + "\n" + sq + ("\n" + c if c else "")) if rng.random() < 0.75 else (sq + "\n" + o)
            new.append({"kind": "sq_new" if rc["split"] == "train" else "sq_devlayout", "text": text, "grid": puz,
                        "layout": rc["id"]})
    rec, dropped = training_recipes(lay), 0
    for _ in range(N_NEAR):                                     # near misses: s x s single digits, one above s
        s = rng.randint(3, 7)
        g = [[rng.randint(1, 9) for _ in range(s)] for _ in range(s)]
        if max(v for row in g for v in row) <= s:
            g[rng.randrange(s)][rng.randrange(s)] = rng.randint(s + 1, 9)
        if rng.random() < 0.5:
            g = [[0 if (rng.random() < 0.25 and v <= s) else v for v in row] for row in g]
        src, rc = rng.choice(rec)
        blk = G1.render_recipe(g, G1.layout_recipe(rc, s, rng.randrange(4)) if src == "gr1" else rc)[0]
        t = rng.choice(everyday + openers)
        text = t + "\n" + blk if rng.random() < 0.6 else blk + "\n" + t
        if R.read_latin(text) is not None:
            dropped += 1
            continue
        new.append({"kind": "near", "text": text, "grid": None, "layout": rc if src == "gr1" else rc["id"]})
    seen = Counter()
    for r in new:
        if r["kind"] == "sq_devlayout":
            r["split"] = "devlayout"
        else:
            r["split"] = "dev" if seen[r["kind"]] % 5 == 4 else "train"
            seen[r["kind"]] += 1
        r["target"] = G5.target_of(r["grid"])
    rows += new
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    c = Counter((r["split"], "square" if r["grid"] is not None else "none") for r in rows)
    print(json.dumps({"rows": len(rows), "near_dropped_read_latin_square": dropped,
                      **{f"{k[0]}_{k[1]}": v for k, v in sorted(c.items())},
                      "new_by_kind_split": {f"{k}_{s}": v for (k, s), v in
                                            sorted(Counter((r["kind"], r["split"]) for r in new).items())}}))


# ------------------------------------------------------------------ train (gr-5's recipe, unchanged)
def train(a) -> None:
    G5.train(a)


# ------------------------------------------------------------------ dev (practice only)
def dev(a) -> None:
    import claude_rsn358b2_bridge as B
    import claude_rt02d as RT
    cp = G5.Copier5(G5.load(a.model, a.adapter), plain=False)
    items = []
    sm = ROOT / "artifacts/claude-panel-rsn358b3-smoke-20260926"
    ans = {r["id"]: r for r in map(json.loads, (sm / "answers.jsonl").read_text().splitlines())}
    items += [("smoke", r["message"], ans[r["id"]]["puz"]) for r in map(json.loads, (sm / "panel.jsonl").read_text()
                                                                         .splitlines())][:10]
    for s in (4, 5, 6, 7):
        items += [("fresh", q["text"], q["puz"]) for q in B.make_requests(487000 + s, 6, s, False)]
    items = items[:10] + [it for it in items[10:] if it[0] == "fresh"][:10]
    items += [("nosquare", t, None) for t, _ in RT.dev_cases()][:10]
    for r in G5._load(a.rows):
        if r["split"] == "dev":
            items.append(("heldout_" + ("square" if r["grid"] is not None else "none"), r["text"], r["grid"]))
        elif r["split"] == "devlayout":
            items.append(("devlayout_square", r["text"], r["grid"]))
    st = Counter()
    t0 = time.time()
    for kind, text, truth in items:
        g = cp.copy(text)["grid"]
        st[kind + "_n"] += 1
        st[kind + "_exact"] += int(g == truth)
        st[kind + "_wrong"] += int(g is not None and g != truth)
        st[kind + "_none"] += int(g is None)
    st["seconds_per_message"] = round((time.time() - t0) / max(1, len(items)), 1)
    need = math.ceil(0.9 * st["heldout_square_n"])              # PASSMARKS-gr6 dev stop rule
    st["dev_gate_need"] = need
    st["dev_gate"] = "PASS" if (st["heldout_square_exact"] >= need and st["heldout_none_wrong"] == 0) else "FAIL"
    print(json.dumps(dict(sorted(st.items()))))


# ------------------------------------------------------------------ registered run and score
def run(a) -> None:
    import claude_dl1_nights as D1
    if a.arm not in ("L6", "G5"):
        raise SystemExit("gr6: --arm is L6 (the gr-6 adapter) or G5 (the gr-5 adapter)")
    if not a.adapter:
        raise SystemExit("gr6: --adapter is required")
    if a.arm == "G5" and a.task == "general":
        raise SystemExit("gr6: G5 runs squares, lookalikes and unseen only")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{a.arm}_{a.task}.jsonl"
    if path.exists():
        raise SystemExit(f"gr6: {path} exists (each run is launched once)")
    if a.task == "general":
        items = [{"id": "gen-%03d" % i, "text": it["q"]} for i, it in enumerate(D1.harm_panel())]
    else:
        items = G5._load(Path(a.panel_dir) / f"{a.task}.jsonl")
    cp = G5.Copier5(G5.load(a.model, a.adapter), plain=False)
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            t0 = time.time()
            r = cp.copy(it["text"])
            f.write(json.dumps({"id": it["id"], "grid": r["grid"], "complete": r["complete"],
                                "ms": round((time.time() - t0) * 1000, 1)}) + "\n")
            f.flush()
    rows = G5._load(path)
    print(json.dumps({"arm": a.arm, "task": a.task, "rows": len(rows),
                      "read_as_square": sum(r["grid"] is not None for r in rows)}))


def score(a) -> None:
    import claude_dl1_nights as D1
    import claude_puzzle_reader as R
    out, pd = Path(a.out), Path(a.panel_dir)
    tasks = ("squares", "lookalikes", "unseen")
    panel = {t: G5._load(pd / f"{t}.jsonl") for t in tasks}
    got = {arm: {t: {r["id"]: r for r in G5._load(out / f"{arm}_{t}.jsonl")} for t in tasks} for arm in ("L6", "G5")}
    got["L6"]["general"] = {r["id"]: r for r in G5._load(out / "L6_general.jsonl")}
    for arm in ("L6", "G5"):
        for t in tasks:
            assert set(got[arm][t]) == {r["id"] for r in panel[t]}, (arm, t)
    assert len(got["L6"]["general"]) == 300
    res = {}
    for arm in ("L6", "G5", "C"):
        rd = (lambda t, r: (R.read_latin(r["text"]) or {}).get("grid")) if arm == "C" else \
             (lambda t, r, arm=arm: got[arm][t][r["id"]]["grid"])
        x = {}
        for t in ("squares", "unseen"):
            g = {r["id"]: rd(t, r) for r in panel[t]}
            x[t + "_exact"] = sum(int(g[r["id"]] == r["grid"]) for r in panel[t])
            x[t + "_wrong"] = sum(int(g[r["id"]] is not None and g[r["id"]] != r["grid"]) for r in panel[t])
            x[t + "_none"] = sum(int(g[r["id"]] is None) for r in panel[t])
            by = Counter()
            for r in panel[t]:
                e = int(g[r["id"]] == r["grid"])
                by[f"size{r['size']}"] += e
                by["broken" if r["broken"] else "whole"] += e
                if t == "squares":
                    by[f"layout_{r['layout']}"] += e
                else:
                    by[f"format_{r['format_id']:02d}"] += e
                    by["sep_seen" if r["sep_seen"] else "sep_new"] += e
            x[t + "_exact_by"] = dict(sorted(by.items()))
        x["lookalikes_false_square"] = sum(int(r["square"] is None and rd("lookalikes", r) is not None)
                                           for r in panel["lookalikes"])
        if arm != "C":
            sq = [r for r in panel["lookalikes"] if r["square"] is not None]
            x["lookalikes_with_square_read_as_square"] = sum(int(rd("lookalikes", r) is not None) for r in sq)
            x["lookalikes_with_square_same_grid"] = sum(int(rd("lookalikes", r) == r["square"]) for r in sq)
            x["lookalikes_with_square_read_as_none"] = sum(int(rd("lookalikes", r) is None) for r in sq)
        if arm == "L6":
            x["general_read_as_square"] = sum(int(r["grid"] is not None) for r in got["L6"]["general"].values())
        elif arm == "C":
            x["general_read_as_square"] = sum(int(R.read_latin(it["q"]) is not None) for it in D1.harm_panel())
        res[arm] = x
    L = res["L6"]
    res["unseen_n_sep_seen"] = sum(int(r["sep_seen"]) for r in panel["unseen"])
    res["incomplete_L6"] = sum(int(not r["complete"]) for t in got["L6"] for r in got["L6"][t].values())
    res["lookalikes_truth_none"] = sum(int(r["square"] is None) for r in panel["lookalikes"])
    res["ms_median_squares_L6"] = sorted(r["ms"] for r in got["L6"]["squares"].values())[50]
    res["marks"] = {"R1": L["squares_exact"] >= 97, "R2": L["lookalikes_false_square"] <= 1,
                    "R3": L["squares_wrong"] <= 1, "R4": L["general_read_as_square"] == 0,
                    "U1": L["unseen_exact"] >= 48, "U2": L["unseen_wrong"] <= 2}
    res["gr6_pass"] = all(res["marks"][k] for k in ("R1", "R2", "R3", "R4"))
    res["gr6U_pass"] = res["marks"]["U1"] and res["marks"]["U2"]
    res["proved_wrong_L6_U1_not_above_G5"] = not (L["unseen_exact"] > res["G5"]["unseen_exact"])
    res["prediction_L6_U1_at_least_G5_plus_6"] = L["unseen_exact"] >= res["G5"]["unseen_exact"] + 6
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "gr6_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if not kk.endswith("_by")} if k in ("L6", "G5", "C")
                          else v) for k, v in res.items()}))


# ------------------------------------------------------------------ selftest
def selftest() -> None:
    n = 0
    lay = draw_layouts()
    assert len(lay) == N_LAYOUTS and Counter(r["split"] for r in lay) == {"train": 32, "devlayout": 8}
    sg = [signature(r) for r in lay]
    assert len(set(sg)) == N_LAYOUTS and not set(sg) & gr1_signatures()
    n += 1
    probe = [[1, 0, 3, 4], [0, 2, 0, 1], [3, 0, 1, 0], [4, 1, 0, 3]]
    for rc in lay:                                  # every drawn layout puts each cell where it says
        text, cells = G1.render_recipe(probe, rc)
        assert len(cells) == 16 and all(text[i] == ("_" if probe[r][c] == 0 else str(probe[r][c])) for i, r, c in cells)
    n += 1
    a = dict.fromkeys(G1.RECIPE_KEYS, "")
    a.update(row_prefix="Row {i}: ", sep=" ", row_join="\n", header="none")
    b = dict(a, row_prefix="row {A}:  ", sep="\t", row_join="\n\n", header="numbers", before="Grid:")
    assert signature(a) == signature(b) and signature(a) in gr1_signatures()
    assert signature(dict(a, sep=", ")) != signature(a)
    n += 1
    assert draw_layouts() == lay                    # the draw is fixed by its seed
    n += 1
    print(f"gr6 selftest {n}/{n}")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["layouts", "build", "train", "dev", "run", "score"])
    for k in ("model", "rows", "adapter", "out", "task", "arm", "panel-dir", "score", "layouts"):
        ap.add_argument("--" + k, default="")
    a = ap.parse_args()
    {"layouts": layouts, "build": build, "train": train, "dev": dev, "run": run, "score": score}[a.cmd](a)


if __name__ == "__main__":
    main()
