#!/usr/bin/env python3
"""rv-386: does telling the model WHY a branch failed help, when code already bans it? (thought-memory thread, 2026-09-26)

Follow-up to rv-385 (registered FAIL: going back with a code ban solved 46/54 of 80 grids, going back with only a
note 13/14). Ben's reviewer (02:11 UTC) proposed the clean next test: ban-only against ban + note, both arms banning
exactly the same moves, so the only change is whether the model also reads about the failed branch.

Two corrections to that proposal, both from reading our code (see PASSMARKS in artifacts/claude-rv386-20260926/):
- rv-385's note only said "row 2, column 3 = 4, it broke the rule". With a shared ban that text is fully redundant
  (the number is already masked), so here the note says why, including what the current grid no longer shows:
  "row 2, column 3 = 4: row 2 already has a 4" and "row 2, column 1 = 5: after it, row 2, column 4 had no number that
  fit".
- A proposer near chance cannot use a reason, so a gate decides whether a model may be used at all.

Arms (same grids, same random numbers, same bans, same step budget):
  ban      : rv-385's revert_ban, unchanged.
  ban_note : the same, plus the abandoned paths from this exact grid, with their reasons, shown before the question.
If the model's probabilities ignored the prompt, the two arms would make identical choices (tested in selftest).

  python -B scripts/claude_rv386.py gate --model DIR          # first-choice accuracy on rv-385's practice grids
  python -B scripts/claude_rv386.py run  --model DIR --seed S --n 80 --size 5 --budget 60 --out DIR
  python -B scripts/claude_rv386.py selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rv385 as R  # noqa: E402  (rv-385's sealed search, grids and model wrapper)

ARMS = ["ban", "ban_note"]
GATE_SEED, GATE_N, GATE_BAR = 9001, 12, 0.50


class Search386(R.Search):
    def __init__(self, p, label, seed):
        super().__init__(p, "revert_ban", seed)          # ban logic from rv-385 in both arms
        self.label = label
        self.show_notes = label == "ban_note"
        self.rng = random.Random(f"rv386|{seed}|{p['pid']}")   # same random numbers in both arms

    def _fail_here(self, v, why):
        i = self.pos()
        r, c = self.cells[i]
        g = self.grid()
        if why.startswith("it broke"):
            where = f"row {r + 1}" if any(g[r][k] == v for k in range(self.s) if k != c) else f"column {c + 1}"
            reason = f"{where} already has a {v}"
        else:
            a, b = self.cells[i + 1]
            reason = f"after it, row {a + 1}, column {b + 1} had no number that fit"
        self.fails[i] = self.fails.get(i, 0) + 1
        self.ban.setdefault(i, set()).add(v)
        line = f"row {r + 1}, column {c + 1} = {v}: {reason}"
        if line not in self.notes.setdefault(i, []):
            self.notes[i].append(line)

    def prompt_parts(self):
        s, g = self.s, self.grid()
        r, c = self.cells[self.pos()]
        rows = "\n".join(" ".join(str(v) if v else "_" for v in row) for row in g)
        msg = (f"Fill the grid so that each row and each column contains every number from 1 to {s} exactly once. "
               f"_ is an empty cell.\n\n{rows}\n\n")
        if self.show_notes and self.notes.get(self.pos()):
            msg += "Earlier tries from this exact grid that went wrong, and why:\n"
            msg += "\n".join(f"- {t}" for t in self.notes[self.pos()]) + "\n\n"
        in_row = ", ".join(str(v) for v in g[r] if v) or "nothing"
        in_col = ", ".join(str(g[k][c]) for k in range(s) if g[k][c]) or "nothing"
        msg += (f"Row {r + 1} already has: {in_row}. Column {c + 1} already has: {in_col}.\n"
                f"What number goes in row {r + 1}, column {c + 1}? Answer with one number.")
        return msg, f"The number in row {r + 1}, column {c + 1} is "

    def result(self):
        out = super().result()
        out["arm"] = self.label
        return out


def weights_hash(model_dir):
    h = hashlib.sha256()
    for f in sorted(Path(model_dir).glob("*.safetensors")):
        with open(f, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 24), b""):
                h.update(chunk)
    return h.hexdigest()


def search_all(ch, puzzles, label, seed, budget):
    xs = [Search386(p, label, seed) for p in puzzles]
    toks = 0
    while True:
        live = [x for x in xs if not x.solved and x.steps < budget]
        if not live:
            return xs, toks
        for k in range(0, len(live), R.BATCH):
            chunk = live[k:k + R.BATCH]
            parts = [x.prompt_parts() for x in chunk]
            toks += sum(len(ch.tok(ch.text(m, p))["input_ids"]) for m, p in parts)
            for x, pr in zip(chunk, ch.probs(parts)):
                x.step(pr)


def gate(a):
    puzzles = R.make_puzzles(GATE_SEED, GATE_N, 5)
    ch = R.Chooser(a.model, 5)
    xs, _ = search_all(ch, puzzles, "ban", GATE_SEED, 60)
    first = right = 0
    for x in xs:
        seen = set()
        for pos, v, _p, what in x.log:
            if what != "back" and pos not in seen:
                seen.add(pos)
                r, c = x.cells[pos]
                first += 1
                right += v == x.p["sol"][r][c]
    acc = right / max(first, 1)
    print(json.dumps({"model": a.model, "weights_sha256": weights_hash(a.model), "first_choices": first,
                      "first_right": right, "accuracy": round(acc, 3), "bar": GATE_BAR, "qualifies": acc >= GATE_BAR}))


def run(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    puzzles = R.make_puzzles(a.seed, a.n, a.size)
    (out / f"puzzles-seed{a.seed}.jsonl").write_text("".join(json.dumps(p) + "\n" for p in puzzles))
    ch = R.Chooser(a.model, a.size)
    wh = weights_hash(a.model)
    for label in ARMS:
        t0 = time.time()
        xs, toks = search_all(ch, puzzles, label, a.seed, a.budget)
        res = [x.result() for x in xs]
        (out / f"{label}-seed{a.seed}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in res))
        print(json.dumps({"arm": label, "seed": a.seed, "solved": sum(r["solved"] for r in res), "n": len(res),
                          "steps": sum(r["steps"] for r in res), "prompt_tokens": toks, "weights_sha256": wh,
                          "sec": round(time.time() - t0)}), flush=True)


def selftest():
    ps = R.make_puzzles(7, 6, 5)
    # identical probabilities -> identical choices in both arms (the note is the only difference)
    for p in ps:
        runs = {}
        for label in ARMS:
            x = Search386(p, label, 1)
            while not x.solved:
                x.step([0.2] * 5)
            runs[label] = x.log
        assert runs["ban"] == runs["ban_note"]
    # the note gives the reason; the ban arm shows nothing; both arms mask the failed number
    p = ps[0]
    for label in ARMS:
        x = Search386(p, label, 1)
        r, c = x.cells[0]
        bad = next((v for v in range(1, 6) if R.conflicts(x.grid(), r, c, v)), None)
        if bad is None:
            continue
        pr = [0.0] * 5
        pr[bad - 1] = 1.0
        x.step(pr)
        msg = x.prompt_parts()[0]
        assert x.choose(pr) != bad
        if label == "ban_note":
            assert f"row {r + 1}, column {c + 1} = {bad}: " in msg and "already has a" in msg, msg
        else:
            assert "Earlier tries" not in msg
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gate", "run", "selftest"])
    ap.add_argument("--model", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--size", type=int, default=5)
    ap.add_argument("--budget", type=int, default=60)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "gate":
        gate(a)
    else:
        run(a)


if __name__ == "__main__":
    main()
