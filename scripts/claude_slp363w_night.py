#!/usr/bin/env python3
"""slp-363w: a SCHOOL NIGHT inside idle sleep (Fix-sleep thread, 2026-09-25; road map 365 stage 2, wiring).

Ben, 00:32 UTC: while the model is idle it should improve itself, "much as a human brain will do", in sleep.
slp-363 (queued on BensPC) asks whether practice built from the user's taught facts makes the loop reasoner better.
This file is the plumbing that would run that practice every night, so it is ready when 363 reports. It does not
itself claim any learning.

ONE CHANGE: install_school363w(loop, school) wraps loop._sleep_tick. After the night's normal sleep (the word
sleeper, its gate and undo, all unchanged), a school night runs on the reasoner checkpoint:
  1. practice items and a separate self-check set are built from the loop's OWN notebook (taught rows only,
     claude_slp363_school.build_night, two different seeds). Nothing is written to the notebook.
  2. the current checkpoint is scored on the self-check set, a copy is trained on the practice items
     (claude_rsn_recipe.py train --init <current> --episodes <night> --mix M), and the copy is scored.
  3. the copy is KEPT only if, on the self-check set, right answers did not fall by more than TOL of the set, wrong
     answers did not rise by more than TOL, and answers given where the row is missing did not rise by more than
     TOL. Otherwise the copy is moved aside to <work>/aside/ (never deleted) and the old checkpoint stays.
  4. the main notebook log's bytes are compared before and after; a change is recorded as an error.
The self-check set shares the notebook's facts with the practice (it is the model checking itself, not a blind test).
Training runs in a child process; it runs only inside a sleep tick, and slp-367 makes those happen only when idle.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import claude_slp363_school as S  # noqa: E402

RECIPE = HERE / "claude_rsn_recipe.py"
TOL363W = 0.02


def _sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


class SchoolNight:
    def __init__(self, ckpt, work, n_practice=400, n_check=300, mix=0.5, train_args=(), tol=TOL363W,
                 seed=1, relabel=None):
        self.current = Path(ckpt)
        self.work = Path(work)
        self.work.mkdir(parents=True, exist_ok=True)
        self.n_practice, self.n_check, self.mix, self.tol, self.seed = n_practice, n_check, mix, tol, seed
        self.train_args = [str(a) for a in train_args]
        self.relabel = relabel            # test hook only: rewrite practice grades (used to model a bad night)
        self.nights: list[dict] = []

    def _run(self, args) -> None:
        p = subprocess.run([sys.executable, "-B", str(RECIPE)] + [str(a) for a in args],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"recipe failed ({p.returncode}): {(p.stderr or '')[-800:]}")

    def _score(self, ckpt: Path, panel: Path, out: Path) -> dict:
        self._run(["eval", "--base", "296", "--ckpt", ckpt, "--panel", panel, "--out", out])
        t = json.loads(out.read_text(encoding="utf-8"))["total"]
        return {k: int(t.get(k, 0)) for k in ("n", "checked_right", "checked_wrong", "raw_answered_without_fact")}

    def night(self, loop) -> dict:
        k = len(self.nights) + 1
        d = self.work / f"night-{k:03d}"
        d.mkdir(parents=True, exist_ok=True)
        log = Path(loop.dir) / "notebook" / "events.jsonl"
        main0 = _sha(log)
        t0 = time.time()
        rec = {"night": k, "old": str(self.current)}
        try:
            practice, plog = S.build_night(loop.nb, self.seed * 100003 + k, self.n_practice)
            check, _ = S.build_night(loop.nb, self.seed * 100003 + 50000 + k, self.n_check)
            if not practice or not check:
                rec.update({"ran": False, "reason": "no taught rows"})
                return rec
            if self.relabel is not None:
                practice = self.relabel(practice, k)
            for name, items in (("practice", practice), ("check", check)):
                with open(d / f"{name}.jsonl", "w", encoding="utf-8") as fh:
                    for it in items:
                        fh.write(json.dumps(it, ensure_ascii=False) + "\n")
            before = self._score(self.current, d / "check.jsonl", d / "check-old.json")
            new_dir = d / "trained"
            self._run(["train", "--base", "296", "--arm", "plain", "--seed", self.seed, "--init", self.current,
                       "--episodes", d / "practice.jsonl", "--mix", self.mix, "--out", new_dir, "--workers", "0"]
                      + self.train_args)
            new = new_dir / "final.pt"
            after = self._score(new, d / "check.jsonl", d / "check-new.json")
            slack = self.tol * before["n"]
            why = []
            if after["checked_right"] < before["checked_right"] - slack:
                why.append("fewer right")
            if after["checked_wrong"] > before["checked_wrong"] + slack:
                why.append("more wrong")
            if after["raw_answered_without_fact"] > before["raw_answered_without_fact"] + slack:
                why.append("more answers without a fact")
            keep = not why
            rec.update({"ran": True, "practice": len(practice), "check": len(check), "kinds": plog.get("kinds"),
                        "before": before, "after": after, "kept": keep, "why": why})
            if keep:
                self.current = new
            else:
                aside = self.work / "aside" / f"night-{k:03d}"
                aside.parent.mkdir(parents=True, exist_ok=True)
                new_dir.replace(aside)
                rec["aside"] = str(aside)
            rec["current"] = str(self.current)
        except Exception as exc:  # noqa: BLE001  (a failed school night keeps the old checkpoint)
            rec.update({"ran": False, "error": f"{type(exc).__name__}: {exc}"[:400]})
        finally:
            rec["main_same"] = _sha(log) == main0
            rec["min"] = round((time.time() - t0) / 60, 2)
            self.nights.append(rec)
            (d / "record.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        return rec


def install_school363w(loop, school: SchoolNight) -> SchoolNight:
    staged = loop._sleep_tick

    def sleep363w():
        event = staged()
        school.night(loop)
        return event

    loop._sleep_tick = sleep363w
    loop.school363w = school
    loop.notes.append("slp-363w: after each sleep, a school night practises on taught facts and keeps the new "
                      "reasoner checkpoint only if its self-check does not get worse")
    return school
