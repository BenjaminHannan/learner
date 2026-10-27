#!/usr/bin/env python3
"""slp-363 registered run: does a night of practice school make the loop reasoner better? (marks:
artifacts/claude-slp363-20260925/PASSMARKS.md). Runs on BensPC (GPU: yes), --workers 0 on Windows.

Per seed S in (1, 2):
  BASE     = "the reasoner before the night": 296's recipe, plain arm, default steps
             (claude_rsn_recipe.py train --base 296 --arm plain --mix 0 --seed S)
  NOSLEEP  = BASE, untouched
  PLAIN    = BASE + one night of plain practice:   --init BASE --mix 0                        (same steps)
  PLACEBO  = BASE + one night on scrambled grades: --init BASE --episodes placebo-sS --mix 0.5 (same steps)
  SCHOOL   = BASE + one night of school:           --init BASE --episodes night-sS   --mix 0.5 (same steps)
  A night = --copy-steps 1000 --rl-steps 2000, the same seed and init in every arm.
Night files: claude_slp363_night.py, world seed 363000+S (a notebook of ~120 invented people, taught), 2000 items;
the placebo keeps the episodes and scrambles the grades (placebo_legal).
Judged on: the SCHOOL PANEL, 1000 items built the same way from a world never used in training (world seed
364417, facts "taught after the freeze"); it is written only inside this run, never printed, scored once per
checkpoint, category counts only. Also reasonpanel296 (general skill, no-harm) and the runner's dev check.

  python -B scripts/claude_slp363_run.py --work W --out artifacts/claude-slp363-20260925/run [--pilot]
--pilot: timing only (base 100+50 steps, nights 50+50, seed 9, no panels).
--dry: local plumbing check only (tiny model, 20+20 steps, seed 9, the whole flow incl. panels); never registered.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RECIPE = HERE / "claude_rsn_recipe.py"
NIGHT = HERE / "claude_slp363_night.py"
PANEL296 = ROOT / "artifacts" / "claude-reasonpanel296-20260924" / "items-v2.jsonl"
NIGHT_COPY, NIGHT_RL = 1000, 2000
PANEL_WORLD = 364417
DRY_PANEL_WORLD = 9001
ARMS = ("PLAIN", "PLACEBO", "SCHOOL")


def run(args: list[str], log) -> None:
    t0 = time.time()
    cmd = [sys.executable, "-B"] + [str(a) for a in args]
    log.write(json.dumps({"cmd": " ".join(cmd[2:])}) + "\n")
    log.flush()
    p = subprocess.run(cmd, capture_output=True, text=True)
    log.write(json.dumps({"rc": p.returncode, "min": round((time.time() - t0) / 60, 2),
                          "tail": (p.stdout or "")[-400:], "err": (p.stderr or "")[-1200:]}) + "\n")
    log.flush()
    if p.returncode != 0:
        raise SystemExit(f"step failed ({p.returncode}): {' '.join(cmd[2:])}\n{(p.stderr or '')[-1200:]}")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True, help="folder for checkpoints and panel (kept on BensPC)")
    ap.add_argument("--out", required=True, help="folder for the small result files to push")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--device", default=None)
    ap.add_argument("--dry", action="store_true", help="local plumbing check only: tiny model, 20+20 steps, seed 9")
    a = ap.parse_args(argv)
    W, O = Path(a.work), Path(a.out)
    W.mkdir(parents=True, exist_ok=True)
    O.mkdir(parents=True, exist_ok=True)
    log = open(O / ("pilot_log.jsonl" if a.pilot else "run_log.jsonl"), "a", encoding="utf-8")
    dev = ["--device", a.device] if a.device else []
    seeds = (9,) if (a.pilot or a.dry) else (1, 2)
    base_steps = ["--copy-steps", "100", "--rl-steps", "50"] if a.pilot else []
    night_steps = ["--copy-steps", "50", "--rl-steps", "50"] if a.pilot else \
        ["--copy-steps", str(NIGHT_COPY), "--rl-steps", str(NIGHT_RL)]
    if a.dry:
        base_steps = night_steps = ["--copy-steps", "20", "--rl-steps", "20", "--size", "tiny"]
    ck = {}
    for s in seeds:
        night, plac = W / f"night-s{s}.jsonl", W / f"placebo-s{s}.jsonl"
        if not night.exists():
            run([NIGHT, "night", "--world-seed", 363000 + s, "--seed", s, "--n", 2000, "--out", night,
                 "--placebo", plac], log)
        base = W / f"BASE-s{s}"
        if not (base / "final.pt").exists():
            run([RECIPE, "train", "--base", "296", "--arm", "plain", "--seed", s, "--mix", "0", "--out", base,
                 "--workers", "0"] + base_steps + dev, log)
        ck[("NOSLEEP", s)] = base / "final.pt"
        for arm in ARMS:
            d = W / f"{arm}-s{s}"
            extra = {"PLAIN": ["--mix", "0"], "PLACEBO": ["--episodes", plac, "--mix", "0.5"],
                     "SCHOOL": ["--episodes", night, "--mix", "0.5"]}[arm]
            if not (d / "final.pt").exists():
                run([RECIPE, "train", "--base", "296", "--arm", "plain", "--seed", s, "--init", base / "final.pt",
                     "--out", d, "--workers", "0"] + extra + night_steps + dev, log)
            ck[(arm, s)] = d / "final.pt"
    if a.pilot:
        print("pilot done; see", O / "pilot_log.jsonl")
        return 0
    seal = O / "SEAL-run.sha256.txt"
    if not seal.exists():                      # checkpoints sealed before any panel is built or scored
        seal.write_text("".join(f"{sha(p)}  {k[0]}-s{k[1]}/final.pt\n" for k, p in sorted(ck.items())),
                        encoding="utf-8")
    panel = W / "school-panel.jsonl"
    if not panel.exists():
        pw = DRY_PANEL_WORLD if a.dry else PANEL_WORLD
        run([NIGHT, "panel", "--world-seed", pw, "--seed", pw, "--n", 1000, "--out", panel], log)
    res = {}
    for (arm, s), p in sorted(ck.items()):
        tag = f"{arm}-s{s}"
        r = {}
        for name, pan in (("school", panel), ("p296", panel if a.dry else PANEL296)):   # dry never opens 296
            out = O / f"{tag}-{name}.json"
            if not out.exists():
                run([RECIPE, "eval", "--base", "296", "--ckpt", p, "--panel", pan, "--out", out] + dev, log)
            r[name] = json.loads(out.read_text(encoding="utf-8"))
        dv = O / f"{tag}-dev.json"
        if not dv.exists():
            run([RECIPE, "dev", "--base", "296", "--ckpt", p, "--out", dv] + dev, log)
        res[tag] = {k: v["total"] for k, v in r.items()}
    json.dump(res, open(O / "totals.json", "w"), indent=1)
    print(json.dumps(score(res, seeds), indent=1))
    return 0


def score(res: dict, seeds=(1, 2)) -> dict:
    out = {}
    for s in seeds:
        g = lambda arm, pan, key="checked_right": res[f"{arm}-s{s}"][pan].get(key, 0)  # noqa: E731
        sch = g("SCHOOL", "school")
        out[f"s{s}"] = {
            "S1": all(sch >= g(x, "school") + 20 for x in ("PLAIN", "PLACEBO", "NOSLEEP")),
            "S2": g("SCHOOL", "p296") >= g("PLAIN", "p296") - 5,
            "S3": g("SCHOOL", "school", "checked_answered_without_fact")
                  <= min(g(x, "school", "checked_answered_without_fact") for x in ("PLAIN", "NOSLEEP")) + 2,
            "school_panel": {x: g(x, "school") for x in ("NOSLEEP", "PLAIN", "PLACEBO", "SCHOOL")},
            "p296": {x: g(x, "p296") for x in ("NOSLEEP", "PLAIN", "PLACEBO", "SCHOOL")},
        }
    out["PASS"] = all(out[f"s{s}"][m] for s in seeds for m in ("S1", "S2", "S3"))
    out["proved_wrong"] = all(out[f"s{s}"]["school_panel"]["SCHOOL"] - out[f"s{s}"]["school_panel"]["PLACEBO"] <= 5
                              for s in seeds)
    return out


if __name__ == "__main__":
    sys.exit(main())
