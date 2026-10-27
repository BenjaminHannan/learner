#!/usr/bin/env python3
"""slp-363x card test: school night with a wider self-check (marks: artifacts/claude-slp363x-20260925/PASSMARKS.md). Same as the slp-363w test except the school class.
CPU, $0, tiny reasoner (the plumbing, not the learning claim; 363 on BensPC tests learning at full size).

Day: ~60 invented people taught through the chat loop ("A's mother is B.", seven one-person relations), a few
corrections and questions, in bursts of BURST turns with one idle step after each burst (fake clock), then evening
idle steps. Every arm has slp-360 scrap + slp-367 idle sleep + slp-368 lock + slp-369 restore.
Arms:  NOSCHOOL  no school night (twin for replies)
       SCHOOL    school night after each sleep (practice built from the loop's taught rows)
       SABOTAGE  the same, but every practice grade is replaced by a legal WRONG answer and all practice comes from
                 the night file (mix 1.0): a model of a bad night, a test fixture, not a treatment
Fixed panel (never trained on, not a blind panel): 600 items from the 363 dry world 9001, scored for the base
checkpoint and each arm's final checkpoint.
  python3 -B scripts/claude_slp363x_test.py --out artifacts/claude-slp363x-20260925/results.json [--seeds 1 2]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_slp363_night as N  # noqa: E402

RELS = ("mother", "father", "spouse", "boss", "doctor", "teacher", "best_friend")
BURST = 30
TRAIN = ["--copy-steps", "100", "--rl-steps", "100", "--size", "tiny"]
BASE_TRAIN = ["--copy-steps", "400", "--rl-steps", "200", "--size", "tiny"]
PANEL_WORLD = 9001


def make_day(seed: int, n_people: int = 60) -> list[str]:
    rng = random.Random(seed * 7919 + 363)
    names = N._names(rng, n_people)
    turns, facts = [], []
    for a in names:
        for rel in RELS:
            if rng.random() < 0.4:
                b = rng.choice([x for x in names if x != a])
                turns.append(f"{a}'s {rel.replace('_', ' ')} is {b}.")
                facts.append((a, rel, b))
    for a, rel, b in rng.sample(facts, 8):
        c = rng.choice([x for x in names if x not in (a, b)])
        turns.insert(rng.randrange(len(turns) // 2, len(turns)), f"Actually, {a}'s {rel.replace('_', ' ')} is {c}.")
    for a, rel, _ in rng.sample(facts, 20):
        turns.insert(rng.randrange(len(turns)), f"Who is {a}'s {rel.replace('_', ' ')}?")
    return turns


class Clock:
    def __init__(self) -> None:
        self.t = 1_000_000.0

    def __call__(self) -> float:
        return self.t


def wrong_legal(items, k):
    rng = random.Random(363_000 + k)
    out = []
    for it in items:
        gold = str(it["gold"]["answer"]).strip().lower()
        bad = [(a, s) for a, s in N._legal(it) if str(a).strip().lower() != gold] or [("UNKNOWN", [])]
        a, s = rng.choice(bad)
        out.append(dict(it, gold={"answer": a, "support": s}, source="slp363w-sabotage"))
    return out


def _sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def recipe(args) -> None:
    p = subprocess.run([sys.executable, "-B", str(SCRIPTS / "claude_rsn_recipe.py")] + [str(a) for a in args],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or "")[-800:])


def base_ckpt(seed: int, root: Path) -> Path:
    d = root / f"BASE-s{seed}"
    if not (d / "final.pt").exists():
        recipe(["train", "--base", "296", "--arm", "plain", "--seed", seed, "--mix", "0", "--out", d,
                "--workers", "0"] + BASE_TRAIN)
    return d / "final.pt"


def run_arm(args) -> dict:
    seed, arm, root, base = args
    import claude_slp360_test as X
    import claude_slp363x_night as W
    import claude_slp367_idle as I367
    import claude_slp368_lock as L
    import claude_slp369_restore as R
    root = Path(root)
    d = root / f"{arm}-s{seed}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    loop = X.build(str(d / "state"), seed, "P")
    clock = Clock()
    st = I367.install_idle367(loop, clock=clock)
    L.install_lock368(loop)
    R.install_restore369(loop)
    base_copy = d / "base.pt"
    shutil.copy2(base, base_copy)
    school = None
    if arm != "NOSCHOOL":
        school = W.SchoolNightX(base_copy, d / "school", n_practice=300, n_check=400, train_args=TRAIN, seed=seed,
                               mix=1.0 if arm == "SABOTAGE" else 0.5,
                               relabel=wrong_legal if arm == "SABOTAGE" else None)
        W.install_school363x(loop, school)
    in_turn_nights = [0]
    inner = loop._sleep_tick

    def watch():
        if st["in_turn"]:
            in_turn_nights[0] += 1
        return inner()

    loop._sleep_tick = watch
    log = Path(loop.dir) / "notebook" / "events.jsonl"
    replies, modes, main_changes = [], [], 0
    turns = make_day(seed)
    for i in range(0, len(turns), BURST):
        for t in turns[i:i + BURST]:
            replies.append(X.say(loop, t))
        before = _sha(log)
        clock.t += 60
        modes.append(loop.step()["mode"])
        main_changes += int(_sha(log) != before)
    for _ in range(2):
        before = _sha(log)
        clock.t += 60
        modes.append(loop.step()["mode"])
        main_changes += int(_sha(log) != before)
    out = {"seed": seed, "arm": arm, "replies": replies, "modes": modes, "sleeps": st["sleeps"],
           "nights_in_turn": in_turn_nights[0], "main_changed_on_idle_steps": main_changes,
           "saved": sum(1 for r in replies if r.startswith("Saved")), "turns": len(turns)}
    if school is not None:
        out["nights"] = school.nights
        out["final"] = str(school.current)
        out["base_bytes_same"] = _sha(base_copy) == _sha(Path(base))
    return out


def panel_score(ckpt: Path, panel: Path, out: Path) -> dict:
    recipe(["eval", "--base", "296", "--ckpt", ckpt, "--panel", panel, "--out", out])
    return json.loads(out.read_text(encoding="utf-8"))["total"]


def score(rows, panel) -> dict:
    by = {(r["seed"], r["arm"]): r for r in rows}
    seeds = sorted({r["seed"] for r in rows})
    m = {}
    main_ok = all(n.get("main_same") for r in rows for n in r.get("nights", [])) and \
        all(r["main_changed_on_idle_steps"] == 0 for r in rows)
    in_turn = sum(r["nights_in_turn"] for r in rows)
    sab = [n for s in seeds for n in by[(s, "SABOTAGE")].get("nights", []) if n.get("ran")]
    sab_rej = sum(1 for n in sab if not n["kept"])
    sab_final = all(by[(s, "SABOTAGE")]["final"].endswith("base.pt") for s in seeds)
    same = sum(1 for s in seeds for a in ("SCHOOL", "SABOTAGE") if by[(s, a)]["replies"] == by[(s, "NOSCHOOL")]["replies"])
    ran = [n for s in seeds for a in ("SCHOOL", "SABOTAGE") for n in by[(s, a)].get("nights", [])]
    errors = [n.get("error") for n in ran if n.get("error")]
    harm = {s: panel[(s, "SCHOOL")]["checked_right"] - panel[(s, "BASE")]["checked_right"] for s in seeds}
    m["P363x.1 main notebook log unchanged on every idle step and school night"] = main_ok
    m["P363x.2 school nights inside a user turn"] = in_turn == 0
    m["P363x.3 sabotaged nights rejected (all) and the sabotage arm ends on the base checkpoint"] = \
        len(sab) >= 2 * len(seeds) and sab_rej == len(sab) and sab_final
    m["P363x.4 user replies identical to NOSCHOOL"] = same == 2 * len(seeds)
    m["P363x.5 SCHOOL final vs base on the fixed panel: right answers not lower by more than 12 (2%)"] = \
        all(v >= -12 for v in harm.values())
    m["detail"] = {"sabotage_rejected": f"{sab_rej}/{len(sab)}", "nights_in_turn": in_turn,
                   "replies_same": f"{same}/{2 * len(seeds)}", "errors": errors,
                   "school_kept": {s: [n.get("kept") for n in by[(s, "SCHOOL")].get("nights", [])] for s in seeds},
                   "panel_right_gain_school_minus_base": harm,
                   "panel": {f"{k[1]}-s{k[0]}": v for k, v in sorted(panel.items())}}
    m["proved_wrong"] = not main_ok or in_turn > 0 or sab_rej < len(sab)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--work", default=None)
    a = ap.parse_args(argv)
    root = Path(a.work or tempfile.mkdtemp(prefix="slp363x-"))
    root.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=2) as ex:
        bases = dict(zip(a.seeds, ex.map(base_ckpt, a.seeds, [root] * len(a.seeds))))
        jobs = [(s, arm, str(root), str(bases[s])) for s in a.seeds for arm in ("NOSCHOOL", "SCHOOL", "SABOTAGE")]
        rows = list(ex.map(run_arm, jobs))
    panel_file = root / "panel.jsonl"
    items, _ = N.world_items(PANEL_WORLD, PANEL_WORLD, 600)
    with open(panel_file, "w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    panel = {}
    for r in rows:
        if r["arm"] == "SCHOOL":
            s = r["seed"]
            panel[(s, "BASE")] = panel_score(bases[s], panel_file, root / f"panel-BASE-s{s}.json")
            panel[(s, "SCHOOL")] = panel_score(Path(r["final"]), panel_file, root / f"panel-SCHOOL-s{s}.json")
    res = {"rows": rows, "marks": score(rows, panel)}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(res["marks"], indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
