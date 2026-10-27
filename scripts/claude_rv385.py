#!/usr/bin/env python3
"""rv-385: go back to an earlier state and try another way (thought-memory thread, 2026-09-25).

Why: Ben, 19:28 UTC: "if it doesn't like where it is right now in its internal representation, it can revert to an
old one with the old thread as an input, and go a different direction". Plan and research:
design/v3/30-modes/384b-revert-and-retry.md. He chose "Build it" at 19:37 UTC.

Test time only, no training. Plain MiniCPM5-1B (bf16, enable_thinking=False) fills Latin-square grids (each number once
per row and column) one empty cell at a time, in a fixed row-major order. The only "don't like where I am" signal is
the visible rule, checked after the model has chosen: the number just written already appears in its row or column.
The check never suggests a number and never looks ahead. After such a conflict the arms differ:

  restart     : wipe every number the model wrote and start again from the given grid (fresh tries).
  revert_ban  : go back to the state just before the bad move; code rules that number out there (the model sees
                nothing). A state where every number has been ruled out is a dead end: go back one more step and
                rule out the number written there. Classic backtracking.
  revert_note : go back the same way, but instead of a ban the model is shown the abandoned path from that state
                ("tried here: row 2, column 3 = 4, it broke the rule"; "row 2, column 1 = 5, then the next empty cell
                had no number that worked"). Nothing is masked. After as many failures at one state as there are
                numbers, go back one more step, as in revert_ban. Ben's version.
Every arm has the same budget of model choices per grid. Measure: grids solved within the budget.

The grid generator is the sleep research thread's (scripts/claude_rsn358a_envs.py, read-only import).

  python -B scripts/claude_rv385.py run --model DIR --seed S --n N --size 5 --budget B --out DIR [--arms a,b]
  python -B scripts/claude_rv385.py selftest
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402  (sleep research thread's Latin-square generator)

ARMS = ["restart", "revert_ban", "revert_note"]
TEMP = 1.5          # blurt-3's guesser temperature (creative thread); fixed, not tuned
BATCH = 8


# ---------------- puzzles ----------------
def make_puzzles(seed: int, n: int, size: int):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        sol, puz = E.make_latin_base(rng, size)
        # numbers 1..size for the chat model; 0 = empty
        out.append({"pid": f"{seed}-{i}", "size": size,
                    "puz": [[v + 1 if v >= 0 else 0 for v in row] for row in puz],
                    "sol": [[v + 1 for v in row] for row in sol]})
    return out


def empties(puz):
    return [(r, c) for r in range(len(puz)) for c in range(len(puz)) if puz[r][c] == 0]


def conflicts(grid, r, c, v):
    s = len(grid)
    return any(grid[r][k] == v for k in range(s) if k != c) or any(grid[k][c] == v for k in range(s) if k != r)


def is_solution(puz, grid):
    s = len(puz)
    full = set(range(1, s + 1))
    if any(puz[r][c] and puz[r][c] != grid[r][c] for r in range(s) for c in range(s)):
        return False
    return all(set(grid[r]) == full for r in range(s)) and all({grid[r][c] for r in range(s)} == full
                                                                for c in range(s))


# ---------------- one grid's search state ----------------
class Search:
    def __init__(self, p, arm, seed):
        self.p, self.arm = p, arm
        self.s = p["size"]
        self.cells = empties(p["puz"])
        self.vals = []                      # numbers written so far, one per cell in order
        self.fails = {}                     # position -> failures at this state
        self.ban = {}                       # position -> numbers ruled out (revert_ban)
        self.notes = {}                     # position -> abandoned paths shown to the model (revert_note)
        self.steps = 0
        self.solved = False
        self.log = []                       # (position, number, p(number), outcome)
        self.rng = random.Random(f"rv385|{seed}|{arm}|{p['pid']}")

    def grid(self):
        g = [row[:] for row in self.p["puz"]]
        for (r, c), v in zip(self.cells, self.vals):
            g[r][c] = v
        return g

    def pos(self):
        return len(self.vals)

    def prompt_parts(self):
        s, g = self.s, self.grid()
        r, c = self.cells[self.pos()]
        rows = "\n".join(" ".join(str(v) if v else "_" for v in row) for row in g)
        msg = (f"Fill the grid so that each row and each column contains every number from 1 to {s} exactly once. "
               f"_ is an empty cell.\n\n{rows}\n\n")
        if self.arm == "revert_note" and self.notes.get(self.pos()):
            msg += "Earlier tries from this exact grid that went wrong:\n"
            msg += "\n".join(f"- {t}" for t in self.notes[self.pos()]) + "\n\n"
        in_row = ", ".join(str(v) for v in g[r] if v) or "nothing"
        in_col = ", ".join(str(g[k][c]) for k in range(s) if g[k][c]) or "nothing"
        msg += (f"Row {r + 1} already has: {in_row}. Column {c + 1} already has: {in_col}.\n"
                f"What number goes in row {r + 1}, column {c + 1}? Answer with one number.")
        return msg, f"The number in row {r + 1}, column {c + 1} is "

    def choose(self, probs):
        """probs: list of s floats over numbers 1..s (already temperature-scaled and normalised)."""
        allowed = list(range(1, self.s + 1))
        if self.arm == "revert_ban":
            allowed = [v for v in allowed if v not in self.ban.get(self.pos(), set())]
        w = [probs[v - 1] for v in allowed]
        tot = sum(w)
        if tot <= 0:
            w = [1.0] * len(allowed)
            tot = float(len(allowed))
        x, acc = self.rng.random() * tot, 0.0
        for v, wv in zip(allowed, w):
            acc += wv
            if x <= acc:
                return v
        return allowed[-1]

    def _fail_here(self, v, why):
        i = self.pos()
        r, c = self.cells[i]
        self.fails[i] = self.fails.get(i, 0) + 1
        self.ban.setdefault(i, set()).add(v)
        line = f"row {r + 1}, column {c + 1} = {v}, {why}"
        if line not in self.notes.setdefault(i, []):     # each abandoned path is shown once
            self.notes[i].append(line)

    def step(self, probs):
        i = self.pos()
        r, c = self.cells[i]
        v = self.choose(probs)
        self.steps += 1
        g = self.grid()
        if not conflicts(g, r, c, v):
            self.vals.append(v)
            self.log.append((i, v, round(probs[v - 1], 4), "ok"))
            if self.pos() == len(self.cells):
                self.solved = is_solution(self.p["puz"], self.grid())
                if not self.solved:            # cannot happen: no conflicts in any row or column
                    raise RuntimeError("full grid without conflicts failed the check")
            return
        self.log.append((i, v, round(probs[v - 1], 4), "conflict"))
        if self.arm == "restart":
            self.vals, self.fails, self.ban, self.notes = [], {}, {}, {}
            return
        self._fail_here(v, "it broke the rule")
        # dead end: as many failures at this state as there are numbers -> go back one more step
        while self.fails.get(self.pos(), 0) >= self.s and self.pos() > 0:
            j = self.pos()
            for d in (self.fails, self.ban, self.notes):
                d.pop(j, None)
            pv = self.vals.pop()
            self._fail_here(pv, "then the next empty cell had no number that worked")
            self.log.append((self.pos(), pv, None, "back"))
        if self.arm == "revert_ban" and len(self.ban.get(self.pos(), ())) >= self.s:
            # only at the first cell with everything ruled out; impossible for a solvable grid
            raise RuntimeError("search exhausted")

    def result(self):
        return {"pid": self.p["pid"], "arm": self.arm, "size": self.s, "blanks": len(self.cells),
                "solved": self.solved, "steps": self.steps, "final": self.grid(), "log": self.log}


# ---------------- model ----------------
class Chooser:
    def __init__(self, model_dir, size):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        torch.set_num_threads(max(1, torch.get_num_threads()))
        self.tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        self.tok.padding_side = "left"
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16,
                                                          trust_remote_code=True).eval()
        self.num_ids = []
        for v in range(1, size + 1):
            ids = self.tok.encode(str(v), add_special_tokens=False)
            if len(ids) != 1:
                raise RuntimeError(f"number {v} is not one token: {ids}")
            self.num_ids.append(ids[0])

    def text(self, msg, prefix):
        return self.tok.apply_chat_template([{"role": "user", "content": msg}], tokenize=False,
                                            add_generation_prompt=True, enable_thinking=False) + prefix

    def probs(self, parts):
        torch = self.torch
        texts = [self.text(m, p) for m, p in parts]
        enc = self.tok(texts, return_tensors="pt", padding=True)
        pos = (enc["attention_mask"].cumsum(-1) - 1).clamp(min=0)
        with torch.inference_mode():
            lg = self.model(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"],
                            position_ids=pos).logits[:, -1, :].float()
        sub = lg[:, self.num_ids] / TEMP
        return torch.softmax(sub, -1).tolist()


def run(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    puzzles = make_puzzles(a.seed, a.n, a.size)
    (out / f"puzzles-seed{a.seed}.jsonl").write_text("".join(json.dumps(p) + "\n" for p in puzzles))
    ch = Chooser(a.model, a.size)
    arms = a.arms.split(",") if a.arms else ARMS
    for arm in arms:
        t0 = time.time()
        searches = [Search(p, arm, a.seed) for p in puzzles]
        while True:
            live = [x for x in searches if not x.solved and x.steps < a.budget]
            if not live:
                break
            for k in range(0, len(live), BATCH):
                chunk = live[k:k + BATCH]
                probs = ch.probs([x.prompt_parts() for x in chunk])
                for x, pr in zip(chunk, probs):
                    x.step(pr)
        res = [x.result() for x in searches]
        path = out / f"{arm}-seed{a.seed}.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in res))
        print(json.dumps({"arm": arm, "seed": a.seed, "solved": sum(r["solved"] for r in res), "n": len(res),
                          "steps": sum(r["steps"] for r in res), "sec": round(time.time() - t0)}), flush=True)


# ---------------- selftest (no model) ----------------
def selftest():
    ps = make_puzzles(7, 6, 5)
    assert all(len(empties(p["puz"])) > 0 for p in ps)
    assert all(is_solution(p["puz"], p["sol"]) for p in ps)
    assert make_puzzles(7, 6, 5) == ps, "puzzles must be reproducible from the seed"
    assert make_puzzles(8, 6, 5) != ps
    # a chooser that always knows the answer solves every grid in exactly `blanks` steps, in every arm
    for arm in ARMS:
        for p in ps:
            x = Search(p, arm, 1)
            while not x.solved:
                r, c = x.cells[x.pos()]
                pr = [0.0] * 5
                pr[p["sol"][r][c] - 1] = 1.0
                x.step(pr)
            assert x.steps == len(x.cells)
    # a uniform chooser: revert_ban is complete, so it always finishes (backtracking search)
    for p in ps:
        x = Search(p, "revert_ban", 3)
        while not x.solved:
            x.step([0.2] * 5)
            assert x.steps < 100000
    # revert_note shows the abandoned path, and bans nothing
    p = ps[0]
    x = Search(p, "revert_note", 1)
    r, c = x.cells[0]
    bad = next(v for v in range(1, 6) if conflicts(x.grid(), r, c, v)) if any(
        conflicts(x.grid(), r, c, v) for v in range(1, 6)) else None
    if bad:
        pr = [0.0] * 5
        pr[bad - 1] = 1.0
        x.step(pr)
        msg, _ = x.prompt_parts()
        assert f"row {r + 1}, column {c + 1} = {bad}, it broke the rule" in msg, msg
        assert x.choose(pr) == bad            # nothing is masked in the note arm
        y = Search(p, "revert_ban", 1)
        y.step(pr)
        assert y.choose(pr) != bad            # the ban arm masks it
        z = Search(p, "revert_ban", 1)
        z.step(pr)
        assert "Earlier tries" not in z.prompt_parts()[0]  # the ban arm shows nothing
    # restart wipes everything after a conflict
    x = Search(p, "restart", 1)
    ok = [0.0] * 5
    ok[p["sol"][x.cells[0][0]][x.cells[0][1]] - 1] = 1.0
    x.step(ok)
    assert x.pos() == 1
    r, c = x.cells[1]
    bad = next((v for v in range(1, 6) if conflicts(x.grid(), r, c, v)), None)
    if bad:
        pr = [0.0] * 5
        pr[bad - 1] = 1.0
        x.step(pr)
        assert x.pos() == 0
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "selftest"])
    ap.add_argument("--model", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--size", type=int, default=5)
    ap.add_argument("--budget", type=int, default=0)
    ap.add_argument("--arms", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    else:
        run(a)


if __name__ == "__main__":
    main()
