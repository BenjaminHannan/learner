#!/usr/bin/env python3
"""The night, packaged for the joined agent (Fix-sleep thread, 2026-09-26). New file; nothing sealed is changed.

What a night does: train the 1B's own adapter on the day's CHECKED right answers (copy practice), so next morning it
is better at the day's work. It is exactly dl-2's S arm (scripts/claude_dl2_nights.py, claude_dl1_nights.train_copy):
per puzzle, the greedy answer if the checker passed it, else the first right guess; 3 epochs of cross-entropy on the
answer tokens, lr 2e-4, batch 8, continuing one growing LoRA (r16 on q,k,v,o). Wrong tries and unchecked text are
never trained. Nothing here ever writes the notebook.

Only use it after dl-2 is a registered PASS (artifacts/claude-dl2-20260926/). Until then 0.x keeps its old sleep.

For Month-end:
    import claude_night as N
    s = N.load(model_dir)                              # Solver + base 1B (thinking off)
    m = N.adapter_model(s, "state/night.pt")           # base + the adapter saved last night (or a fresh one)
    groups = N.day(s, m, todays_puzzles)               # the day's work: greedy + 30 checked guesses each
      # or: groups = N.groups_from_attempts("attempts.jsonl")   (shared attempts format v0; try 0 = greedy)
    out = N.night(s, m, groups, seed=night_number, tripwire=True)
    N.save_adapter(m, "state/night.pt")
  out = {"trained": examples, "train": {...}, "tripwire": {...}, "undone": bool}

Tripwire (research REPORT.md Q7: a tripwire, not a gate): before and after the night, the 300-item general panel of
claude_dl1_nights; if the night loses more than 5 net items (lost minus gained vs the pre-night adapter), the night is
undone (the adapter goes back to its pre-night weights) and "undone" is reported. dl-2 measures how often that would
have fired (W3). It costs 600 short greedy replies per night, so pass tripwire=False on CPU.

Where the adapter applies: the adapter is trained and tested on puzzle work only. dl-2 measures harm with it switched
on for everything (W3). The joined agent may load it only for the puzzle tool and keep the plain 1B for chat
(use_for_chat=False below); that is the safer default for 0.2c and is what this file recommends.

  python -B scripts/claude_night.py --selftest                  (no model)
  python -B scripts/claude_night.py --model M --demo --out DIR  (one tiny day and night, plumbing only)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_blurt2 as B2  # noqa: E402
import claude_dl1_nights as D1  # noqa: E402

RECIPE = dict(D1.S_RECIPE)       # {"epochs": 3, "lr": 2e-4}, dl-2's S arm
N_GUESS = 30                     # the day: greedy + 30 guesses per puzzle at T 1.5 (D1.TEMP)
TRIP_NET_HARM = 5                # undo a night that loses more than 5 net panel items
USE_FOR_CHAT = False             # recommended: adapter on for the puzzle tool only


def load(model_dir: str):
    s = B2.Solver(model_dir)
    s.model.name_or_path = model_dir
    return s


def adapter_params(m) -> dict:
    return {n: p for n, p in m.named_parameters() if p.requires_grad}


def snapshot(m) -> dict:
    return {n: p.detach().cpu().clone() for n, p in adapter_params(m).items()}


def restore(m, snap: dict) -> None:
    import torch
    with torch.no_grad():
        for n, p in adapter_params(m).items():
            p.copy_(snap[n].to(p.device))


def save_adapter(m, path) -> None:
    import torch
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save(snapshot(m), str(path))


def adapter_model(s, path=None):
    """Base 1B + LoRA. Loads the saved adapter if path exists, else a fresh one (starts exactly as the base)."""
    import torch
    m = D1.fresh_model(s)
    if path and Path(path).exists():
        restore(m, torch.load(str(path), map_location="cpu"))
    return m


def day(s, m, puzzles, n_guess=N_GUESS) -> list[dict]:
    """The day's work, checked: greedy answer + n_guess guesses per puzzle, every one marked by the exact checker."""
    return D1.gather(s, m, puzzles, n_guess)


def groups_from_attempts(path, task_kind="number-puzzle") -> list[dict]:
    """Read shared attempts format v0 (scripts/claude_attempts.py). Rows need extras nums and target. Try 0 of a
    group is taken as the greedy answer, so the copy rule matches dl-2 (greedy if right, else first right try)."""
    by: dict[str, list] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("task_kind") == task_kind and "nums" in r and "target" in r:
            by.setdefault(r["group_id"], []).append(r)
    out = []
    for rows in by.values():
        rows.sort(key=lambda r: r["try"])
        p = {"nums": rows[0]["nums"], "target": rows[0]["target"]}
        # re-check with the exact checker: a row's own verdict is never trusted alone
        ok = [int(B1.check(r["attempt"], p["nums"], p["target"])) for r in rows]
        out.append({"puzzle": p, "greedy": rows[0]["attempt"], "greedy_right": bool(ok[0]),
                    "guesses": [r["attempt"] for r in rows[1:]], "rewards": ok[1:]})
    return out


def copy_examples(groups) -> list:
    return D1.copy_examples(groups)


def night(s, m, groups, seed=0, tripwire=True, panel=None) -> dict:
    """Train m's adapter in place on the day's checked right answers. Returns what happened."""
    ex = copy_examples(groups)
    out = {"groups": len(groups), "trained": len(ex), "undone": False}
    if not ex:
        out["train"] = {"examples": 0}
        return out
    snap = snapshot(m)
    panel = panel if panel is not None else (D1.harm_panel() if tripwire else None)
    before = D1.harm_scores(s, m, panel) if tripwire else None
    out["train"] = D1.train_copy(s, m, ex, seed, **RECIPE)
    if tripwire:
        after = D1.harm_scores(s, m, panel)
        f = D1.flips(before, after)
        out["tripwire"] = f
        if f["net_harm"] > TRIP_NET_HARM:
            restore(m, snap)
            out["undone"] = True
    return out


def selftest() -> None:
    import tempfile
    import claude_attempts as A
    d = Path(tempfile.mkdtemp()) / "a.jsonl"
    A.log_group(d, "number-puzzle", "p1", ["1 + 2", "1 * 2 + 3", "3 * 1 + 2"], ["wrong", "right", "right"],
                "claude_blurt1.check@v1", {"nums": [1, 2, 3], "target": 5})
    A.log_group(d, "number-puzzle", "p2", ["2 * 3", "2 + 3"], ["right", "wrong"], "claude_blurt1.check@v1",
                {"nums": [2, 3], "target": 6})
    A.log_group(d, "number-puzzle", "p3", ["4 + 4"], ["right"], "claude_blurt1.check@v1",  # verdict lies
                {"nums": [4, 4], "target": 9})
    g = groups_from_attempts(d)
    ex = {e[0]["target"]: e[1] for e in copy_examples(g)}
    assert ex == {5: "1 * 2 + 3", 6: "2 * 3"}, ex
    print("selftest ok")


def demo(a) -> None:
    """Plumbing only: 4 puzzles, 4 guesses, one night, save and reload. Not a result."""
    s = load(a.model)
    m = adapter_model(s)
    groups = day(s, m, B2.puzzles(70001, 4), 4)
    out = night(s, m, groups, seed=1, tripwire=True, panel=D1.harm_panel()[:6])
    p = Path(a.out) / "night.pt"
    save_adapter(m, p)
    m2 = adapter_model(s, p)
    same = all((x.detach().cpu() == y.detach().cpu()).all() for x, y in
               zip(adapter_params(m).values(), adapter_params(m2).values()))
    print(json.dumps({"night": out, "reload_same": bool(same)}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.demo:
        return demo(a)
    ap.print_help()


if __name__ == "__main__":
    main()
