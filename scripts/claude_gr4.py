#!/usr/bin/env python3
"""gr-4: the plain 1B copies the square with constrained decoding (Plain-English puzzles thread, 2026-09-26).

The plainest well-known fix for reading a structure out of text, with nothing trained: the model writes the answer
under a grammar (structured output). 358b2 (bb8af6e93) tested the free copy: the plain 1B, asked to copy the square
one row per line, was exact on 25, 39 and 28 of 100, and it dropped blanks inside runs of "_". The one change here is a
grammar on the 1B's greedy copy. Every output token must keep the text inside:
    none                                           (the message holds no square)
  | s rows of s cells, cells 1-9 or "_", one space between cells, one row per line, 3 <= s <= 9
The first row's length fixes s. Code then keeps the grid only if every value is at most s and not every cell is blank.
The grammar is hand-written code (disclosed scaffolding, like gr-2's search). The reading is the plain 1B's (every
LoRA scale 0).

  python -B scripts/claude_gr4.py --selftest
  python -B scripts/claude_gr4.py dev --model BASE [--limit N]
  python -B scripts/claude_gr4.py run --task squares|lookalikes|unseen|general --model BASE --panel-dir PD --out OUT
  python -B scripts/claude_gr4.py score --out OUT --panel-dir PD --score SCOREDIR
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
PROMPT = ("Copy the square from the message below exactly, one row per line, numbers separated by spaces, with _ for "
          "each empty cell. If the message has no number square to fill in, write none. Write nothing else.\n\n"
          "Message:\n{req}")
CELLS = "123456789_"
MAX_NEW = 200


# ------------------------------------------------------------------ the grammar (character level)
class Machine:
    """state of a partial output; feed() returns a new Machine or None if the text leaves the grammar"""
    __slots__ = ("mode", "row", "cells", "s")

    def __init__(self, mode="start", row=0, cells=0, s=None):
        self.mode, self.row, self.cells, self.s = mode, row, cells, s

    def copy(self):
        return Machine(self.mode, self.row, self.cells, self.s)

    def feed(self, text):
        m = self.copy()
        for ch in text:
            if not m._step(ch):
                return None
        return m

    def _step(self, ch):
        if self.mode in ("start", "cell"):
            if ch not in CELLS:
                return False
            self.cells += 1
            self.mode = "after"
            return self.cells <= (self.s or 9)
        if self.mode == "after":
            if ch == " ":
                if self.s is not None and self.cells >= self.s:
                    return False
                self.mode = "cell"
                return self.cells < 9
            if ch == "\n":
                if self.s is None:
                    if self.cells < 3:
                        return False
                    self.s = self.cells
                elif self.cells != self.s:
                    return False
                self.row += 1
                self.cells = 0
                self.mode = "done" if self.row == self.s else "cell"
                return True
            return False
        return False                                   # "done" or "none": nothing may follow

    def can_end(self):
        if self.mode == "done":
            return True
        return self.mode == "after" and self.s is not None and self.cells == self.s and self.row == self.s - 1


def parse(text):
    """the grid a finished output gives, or None"""
    t = text.strip()
    if not t or t == "none":
        return None
    rows = [[0 if c == "_" else int(c) for c in ln.split(" ")] for ln in t.split("\n")]
    s = len(rows)
    if not 3 <= s <= 9 or any(len(r) != s for r in rows) or any(v > s for r in rows for v in r):
        return None
    if all(v == 0 for r in rows for v in r):
        return None
    return rows


# ------------------------------------------------------------------ constrained greedy decoding
class Copier:
    def __init__(self, one_b):
        import claude_sleep02c as SL
        self.one_b, self.tok, self.model, self.torch = one_b, one_b.tok, one_b.model, one_b.torch
        self.mods = SL.lora_mods(self.model)
        vocab = {}
        for i in range(len(self.tok)):
            s = self.tok.decode([i])
            if s and all(ch in CELLS + " \n" for ch in s):
                vocab[i] = s
        self.vocab = vocab                              # every token made only of cell, space and newline characters
        self.none_ids = [i for i in range(len(self.tok)) if self.tok.decode([i]) in ("none", "None")]
        assert self.none_ids, "no single 'none' token"
        self.eos = self.tok.eos_token_id

    def allowed(self, m, first):
        ids = {i: m.feed(s) for i, s in self.vocab.items()}
        ids = {i: x for i, x in ids.items() if x is not None}
        if first:
            for i in self.none_ids:
                ids[i] = Machine("none")
        return ids

    def copy(self, text):
        torch = self.torch
        prompt = self.tok.apply_chat_template([{"role": "user", "content": PROMPT.format(req=text)}], tokenize=False,
                                              add_generation_prompt=True, enable_thinking=False)
        ids = self.tok(prompt, return_tensors="pt").input_ids.to(self.one_b.dev)
        saved = [x.scale for x in self.mods]
        for x in self.mods:
            x.scale = 0.0
        out, m, past = [], Machine(), None
        try:
            with torch.no_grad():
                cur = ids
                for step in range(MAX_NEW):
                    r = self.model(input_ids=cur, past_key_values=past, use_cache=True)
                    past, logits = r.past_key_values, r.logits[0, -1]
                    if m.mode == "none":
                        break
                    opts = self.allowed(m, step == 0)
                    cand = list(opts)
                    if m.can_end():
                        cand.append(self.eos)
                    if not cand:
                        break
                    idx = torch.tensor(cand, device=logits.device)
                    pick = cand[int(logits[idx].argmax())]
                    if pick == self.eos:
                        break
                    m = opts[pick]
                    out.append(pick)
                    cur = torch.tensor([[pick]], device=ids.device)
        finally:
            for x, sc in zip(self.mods, saved):
                x.scale = sc
        raw = self.tok.decode(out)
        raw = raw.lower() if m.mode == "none" else raw
        return {"raw": raw, "grid": parse(raw) if (m.mode == "none" or m.can_end()) else None,
                "complete": m.mode == "none" or m.can_end()}


# ------------------------------------------------------------------ dev (dev data only; report)
def dev(a) -> None:
    import claude_rt02d as RT
    import claude_rt02g as G
    import claude_rsn358b2_bridge as B
    one_b = G.load_one_b(a.model)
    cp = Copier(one_b)
    items = []
    sm = ROOT / "artifacts/claude-panel-rsn358b3-smoke-20260926"
    ans = {r["id"]: r for r in map(json.loads, (sm / "answers.jsonl").read_text().splitlines())}
    items += [("smoke", r["message"], ans[r["id"]]["puz"]) for r in map(json.loads, (sm / "panel.jsonl").read_text()
                                                                         .splitlines())]
    for s in (4, 5, 6, 7):
        items += [("fresh", q["text"], q["puz"]) for q in B.make_requests(487000 + s, 6, s, False)]
    items += [("nosquare", t, None) for t, _ in RT.dev_cases()]
    lim = int(a.limit) if a.limit else 0
    if lim:
        by = Counter()
        keep = []
        for it in items:
            if by[it[0]] < lim:
                keep.append(it)
                by[it[0]] += 1
        items = keep
    st = Counter()
    t0 = time.time()
    for kind, text, truth in items:
        r = cp.copy(text)
        st[kind + "_n"] += 1
        st[kind + "_exact"] += int(r["grid"] == truth)
        st[kind + "_wrong"] += int(r["grid"] is not None and r["grid"] != truth)
        st[kind + "_incomplete"] += int(not r["complete"])
    st["seconds_per_message"] = round((time.time() - t0) / max(1, len(items)), 1)
    print(json.dumps(dict(sorted(st.items()))))


# ------------------------------------------------------------------ registered run and score
def _load(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def run(a) -> None:
    import claude_dl1_nights as D1
    import claude_rt02g as G
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"L_{a.task}.jsonl"
    if path.exists():
        raise SystemExit(f"gr4: {path} exists (each run is launched once)")
    if a.task == "general":
        items = [{"id": "gen-%03d" % i, "text": it["q"]} for i, it in enumerate(D1.harm_panel())]
    else:
        items = _load(Path(a.panel_dir) / f"{a.task}.jsonl")
    cp = Copier(G.load_one_b(a.model))
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            t0 = time.time()
            r = cp.copy(it["text"])
            f.write(json.dumps({"id": it["id"], "grid": r["grid"], "complete": r["complete"],
                                "ms": round((time.time() - t0) * 1000, 1)}) + "\n")
            f.flush()
    rows = _load(path)
    print(json.dumps({"task": a.task, "rows": len(rows), "read_as_square": sum(r["grid"] is not None for r in rows)}))


def score(a) -> None:
    import claude_dl1_nights as D1
    import claude_puzzle_reader as R
    out, pd = Path(a.out), Path(a.panel_dir)
    panel = {t: _load(pd / f"{t}.jsonl") for t in ("squares", "lookalikes", "unseen")}
    got = {t: {r["id"]: r for r in _load(out / f"L_{t}.jsonl")} for t in ("squares", "lookalikes", "unseen", "general")}
    for t in ("squares", "lookalikes", "unseen"):
        assert set(got[t]) == {r["id"] for r in panel[t]}
    assert len(got["general"]) == 300
    res = {}
    for arm in ("L", "C"):
        rd = (lambda t, r: (R.read_latin(r["text"]) or {}).get("grid")) if arm == "C" else \
             (lambda t, r: got[t][r["id"]]["grid"])
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
                by[f"layout_{r['layout']}" if t == "squares" else f"format_{r['format_id']:02d}"] += e
            x[t + "_exact_by"] = dict(sorted(by.items()))
        x["lookalikes_false_square"] = sum(int(r["square"] is None and rd("lookalikes", r) is not None)
                                           for r in panel["lookalikes"])
        x["general_read_as_square"] = (sum(int(R.read_latin(it["q"]) is not None) for it in D1.harm_panel())
                                       if arm == "C" else sum(int(r["grid"] is not None) for r in got["general"].values()))
        res[arm] = x
    L = res["L"]
    res["incomplete"] = sum(int(not r["complete"]) for t in got for r in got[t].values())
    res["lookalikes_truth_square"] = sum(int(r["square"] is not None) for r in panel["lookalikes"])
    res["ms_median_squares"] = sorted(r["ms"] for r in got["squares"].values())[50]
    res["marks"] = {"R1": L["squares_exact"] >= 97, "R2": L["lookalikes_false_square"] <= 1,
                    "R3": L["squares_wrong"] <= 1, "R4": L["general_read_as_square"] == 0,
                    "U1": L["unseen_exact"] >= 48, "U2": L["unseen_wrong"] <= 2}
    res["gr4_pass"] = all(res["marks"][k] for k in ("R1", "R2", "R3", "R4"))
    res["gr4U_pass"] = res["marks"]["U1"] and res["marks"]["U2"]
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "gr4_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if not kk.endswith("_by")} if k in ("L", "C") else v)
                      for k, v in res.items()}))


def selftest() -> None:
    n = 0
    ok = ["1 _ 3\n3 1 _\n_ 3 1", "1 _ 3\n3 1 _\n_ 3 1\n", "_ _ _ 4\n1 2 3 4\n4 _ _ 1\n2 _ _ _"]
    bad = ["1 _ 3\n3 1 _\n_ 3 1\n\n", "1 _\n3 1", "1 _ 3\n3 1\n_ 3 1", "1  _ 3", "1 _ 3\n3 1 _\n_ 3 1\n4 4 4", "1 _ 3 x", " 1 _ 3", "1 2 3 4 5 6 7 8 9 1"]
    for t in ok:
        m = Machine().feed(t)
        assert m is not None and m.can_end(), t
        n += 1
    for t in bad:
        m = Machine().feed(t)
        assert m is None or not m.can_end(), t
        n += 1
    assert Machine().feed("1 _ 3\n3 1").can_end() is False                 # a partial row cannot end
    assert parse("1 _ 3\n3 1 _\n_ 3 1") == [[1, 0, 3], [3, 1, 0], [0, 3, 1]]
    assert parse("none") is None and parse("_ _ _\n_ _ _\n_ _ _") is None and parse("4 _ _\n_ _ _\n_ _ _") is None
    n += 4
    print(f"gr4 selftest {n}/{n}")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dev", "run", "score"])
    for k in ("model", "limit", "task", "panel-dir", "out", "score"):
        ap.add_argument("--" + k, default="")
    a = ap.parse_args()
    {"dev": dev, "run": run, "score": score}[a.cmd](a)


if __name__ == "__main__":
    main()
