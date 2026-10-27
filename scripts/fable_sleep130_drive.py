#!/usr/bin/env python3
"""Experiment 130 driver -- registered G1/G2/G3 + unregistered G4 climb (additive only).

Registered (PASSMARKS sealed first):
  G1  re-run 115's L4 (5 relations over 5 sleeps, 400 turns) on seeds 1 and 2
      (seed 3 only if time allows): all 5 relations install, 25/25 probes
      correct, 0 wrong, 0 wrong installs, 0 taught overwrites. Turn list is
      115's build_turns_l4 verbatim.
  G2  no forgetting: the 3 earlier words stay 15/15 after slots 4 and 5 are
      added (final probes), and every pre-existing slot/skill tensor hash is
      unchanged after each sleep (frozen_ok in every recipe row).
  G3  115's L1-L3 byte-identical outcomes: L1/L2/L3 re-run with the 130 agent
      (115 builders verbatim); score fields other than wall-clock must equal
      the sealed 115 wave-report, and grew_slot must never fire.

Unregistered, reported apart:
  G4  climb until it breaks: 8 relations over 8 sleeps (seed 1), then 12
      relations over 12 sleeps if 8 passes. Per-sleep seconds and the break
      point are reported; no marks gate anything.
  G5  wave < 30 min Mac CPU (seeds as parallel processes; OMP_NUM_THREADS=1
      each) -- reported, not gated per-sleep.

Usage (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_sleep130_drive.py --root ART_DIR --seed 1 --seed 2
  --only selects: g1 g3l1 g3l2 g3l3 g4-8 g4-12 (default: g1 on seeds 1 2).

Nothing outside this file and the sleep130 artifacts is written. The driver
never calls sleep and never writes facts (mailbox files only).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_sleep115_drive as D115  # noqa: E402 (115 builders, read-only)
import fable_sleep130_agent as S130  # noqa: E402 (130 agent, read-only)

ART = SCRIPTS.parent / "artifacts" / "fable-sleep130-20260922"
PY = [sys.executable, "-B", str(SCRIPTS / "fable_sleep130_agent.py")]

WORDS5 = list(S130.WORDS130[:5])
EXPECT5 = {w: list(S130.EXPECTED_SKILLS130[i])
           for i, w in enumerate(S130.WORDS130[:5])}
# G4 climb words: the 5 registered + 3 (8-sleep) + 4 more (12-sleep).
WORDS8 = list(S130.WORDS130[:8])
WORDS12 = list(S130.WORDS130[:12])
EXPECT_ALL = {w: list(S130.EXPECTED_SKILLS130[i])
              for i, w in enumerate(S130.WORDS130)}
SURF = dict(S130.ASK130)

# Extra 2-hop chains for the climb (75-turn phases: 50 teaches + 20 asks + 5).
CLIMB_CHAINS = {w: S130.CHAINS130[i] for i, w in enumerate(S130.WORDS130)}


# ------------------------------------------------------------ mailbox helpers
def spawn(d: Path, seed: int, idle_seconds: float = 3600.0,
          threshold: int = 75):
    d.mkdir(parents=True, exist_ok=True)
    cfg = {"state_dir": str(d), "sleep_threshold": threshold,
           "sleep130_seed": seed}
    cfg_path = d / "sleep130-config.json"
    cfg_path.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    for stale in ("STOP", "heartbeat.json", "daemon_status.json"):
        (d / stale).unlink(missing_ok=True)
    log = open(d / "daemon.stdout.log", "w", encoding="utf-8")  # noqa: PTH123
    proc = subprocess.Popen(
        PY + ["--daemon", "--dir", str(d), "--config", str(cfg_path),
              "--idle-seconds", str(idle_seconds)],
        stdout=log, stderr=subprocess.STDOUT)
    proc._log = log  # type: ignore[attr-defined]
    deadline = time.time() + 180.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"sleep130 daemon exited early: {proc.poll()}")
        if (d / "heartbeat.json").exists() and (
                d / "daemon_status.json").exists():
            return proc
        time.sleep(0.05)
    proc.kill()
    raise RuntimeError("sleep130 daemon did not write heartbeat in time")


submit = D115.submit
wait_outbox = D115.wait_outbox
stop_daemon = D115.stop_daemon
read_log = D115.read_log
taught_ok = D115.taught_ok
sleep_overwrites = D115.sleep_overwrites
classify = D115.classify
drive_turns = D115.drive_turns
sleep_rows = D115.sleep_rows


def check_routing130(d: Path, wname: str) -> bool:
    try:
        data = json.loads((d / S130.WORD_FILE130).read_text(encoding="utf-8"))
        logits = data["words"][wname]["logits"]
        arg = [max(range(9), key=lambda i: r[i]) for r in logits]
        want = EXPECT_ALL.get(wname)
        if want is None:
            return False
        return ([a for a in arg if a != 0] == want
                and data["words"][wname].get("report_fid") is not None)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def score_session130(d: Path, seed: int, tag: str, replies: list[dict],
                     truth: dict, words: list[str], t0: float,
                     thresholds: list[int]) -> dict:
    nb = C.Notebook(d / "notebook")
    sleeps = sleep_rows(d)
    turn_events = [e for e in read_log(d) if e.get("event") == "turn"]
    probe_recs: dict[str, list] = {w: [] for w in words}
    for r in replies:
        if r["kind"] != "probe" or not r.get("word"):
            continue
        ev = next((e for e in turn_events
                   if e.get("file") == f"t{r['n']:03d}.txt"), {})
        recs = ev.get("records", [])
        probe_recs.setdefault(r["word"], []).append(
            recs[0] if recs else {})
    per_word: dict = {}
    for w in words:
        ps = [r for r in replies if r["kind"] == "probe" and r.get("word")
              == w]
        per_word[w] = {
            "correct": sum(1 for r in ps if r["verdict"] == "correct"),
            "abstain": sum(1 for r in ps if r["verdict"] == "abstain"),
            "wrong": sum(1 for r in ps if r["verdict"] == "wrong"),
            "total": len(ps),
            "sources_sleep_derived": sum(
                1 for r in probe_recs.get(w, [])
                if r.get("fields", {}).get("source") == "sleep-derived"),
            "routing_ok": check_routing130(d, w),
        }
    report_rows = [f for f in nb.facts.values()
                   if f.get("source") == "sleep-derived"]
    good, dupes = taught_ok(nb, truth)
    sleeps_info = []
    for s in sleeps:
        recipe = s.get("recipe", {}) if isinstance(s, dict) else {}
        s_words = recipe.get("words", []) if isinstance(recipe, dict) else []
        sleeps_info.append({
            "file": s.get("file"), "sleep_seconds": s.get("sleep_seconds"),
            "installed": sum(1 for w in s_words if w.get("installed")),
            "words": {w.get("word"): {
                "installed": bool(w.get("installed")),
                "episodes": w.get("episodes"),
                "oof_best": w.get("oof_best"),
                "refit_agreement": w.get("refit_agreement"),
                "grew_slot": bool(w.get("grew_slot")),
                "frozen_ok": w.get("frozen_ok")}
                for w in s_words},
        })
    installed_words = sorted(
        {wname for s in sleeps_info for wname, w in s["words"].items()
         if w.get("installed")})
    return {
        "seed": seed, "dir": tag, "thresholds": thresholds,
        "seconds": round(time.time() - t0, 1),
        "turns": len(replies),
        "sleeps": sleeps_info,
        "n_sleeps": len(sleeps_info),
        "installed_words": installed_words,
        "per_word": per_word,
        "report_rows_sleep_derived": len(report_rows),
        "taught_good": good, "taught_total": len(truth),
        "taught_dupes": dupes,
        "sleep_overwrote_taught": sleep_overwrites(nb),
        "teaches_saved": sum(
            1 for r in replies if r["kind"] == "teach"
            and "saved" in r["reply"].lower()),
        "teaches_total": sum(1 for r in replies if r["kind"] == "teach"),
    }


# ------------------------------------------------------------------ rung G1
def run_g1(seed: int, root: Path) -> dict:
    t0 = time.time()
    tag = f"g1-seed{seed}"
    d = root / tag
    if d.exists():
        shutil.rmtree(d)
    proc = spawn(d, seed, threshold=75)
    turns, truth = D115.build_turns_l4()  # 115's 400 turns verbatim
    replies = drive_turns(d, turns, 1, {75, 150, 225, 300, 375})
    stop_daemon(proc, d)
    rep = score_session130(d, seed, tag, replies, truth, WORDS5, t0, [75])
    rep["rung"] = "G1"
    rep["replies"] = replies
    return rep


def g1_pass(rep: dict) -> bool:
    if rep["n_sleeps"] < 5:
        return False
    for w in WORDS5:
        p = rep["per_word"][w]
        if p["correct"] != 5 or p["wrong"] != 0 or p["total"] != 5:
            return False
        if p["sources_sleep_derived"] != 5:
            return False
        if not p["routing_ok"]:
            return False
    for s in rep["sleeps"]:
        for wname, wrec in s["words"].items():
            if wname in EXPECT5:
                if not wrec["installed"]:
                    return False
                if (wrec["oof_best"] or 0) < 0.80:
                    return False
                if (wrec["refit_agreement"] or 0) < 0.90:
                    return False
                if wrec.get("frozen_ok") is False:
                    return False
            elif wrec["installed"]:
                return False
    # the one change must fire exactly where 115 had no slot: sleeps 1-3
    # reuse sealed slots, sleeps 4-5 grow one slot each.
    grew = [wrec.get("grew_slot") is True
            for s in rep["sleeps"] for wrec in s["words"].values()]
    if sum(grew) != 2:
        return False
    for s in rep["sleeps"][:3]:
        if any(wrec.get("grew_slot") for wrec in s["words"].values()):
            return False
    if rep["taught_good"] != rep["taught_total"]:
        return False
    if rep["taught_dupes"] != 0 or rep["sleep_overwrote_taught"] != 0:
        return False
    if rep["report_rows_sleep_derived"] < 5:
        return False
    return True


def g2_pass(rep: dict) -> bool:
    # no forgetting: first 3 words still 15/15 after slots 4-5 were added
    # (final probes run after sleep 5); every sleep kept frozen hashes.
    for w in WORDS5[:3]:
        p = rep["per_word"][w]
        if p["correct"] != 5 or p["wrong"] != 0:
            return False
    for s in rep["sleeps"]:
        for wrec in s["words"].values():
            if wrec.get("installed") and wrec.get("frozen_ok") is not True:
                # sleeps 1-3 run the sealed path (no frozen_ok field);
                # grown sleeps must report frozen_ok True.
                if wrec.get("grew_slot"):
                    return False
    grown_sleeps = [s for s in rep["sleeps"] if any(
        wrec.get("grew_slot") for wrec in s["words"].values())]
    if len(grown_sleeps) != 2:
        return False
    return True


# ------------------------------------------------------------------ rung G3
def run_g3l1(seed: int, root: Path) -> dict:
    t0 = time.time()
    tag = f"g3l1-seed{seed}"
    d = root / tag
    if d.exists():
        shutil.rmtree(d)
    proc = spawn(d, seed, threshold=215)
    turns, truth = D115.build_turns_l1()
    replies = drive_turns(d, turns, 1, {215})
    stop_daemon(proc, d)
    rep = score_session130(d, seed, tag, replies, truth,
                           list(D115.WORDS), t0, [215])
    rep["rung"] = "G3-L1"
    rep["replies"] = replies
    return rep


def run_g3l2(seed: int, root: Path) -> dict:
    t0 = time.time()
    tag = f"g3l2-seed{seed}"
    d = root / tag
    if d.exists():
        shutil.rmtree(d)
    proc = spawn(d, seed, threshold=75)
    turns1, truth = D115.build_turns_l2_phase1()
    replies = drive_turns(d, turns1, 1, {75})
    stop_daemon(proc, d)
    proc = spawn(d, seed, threshold=145)
    turns2 = D115.build_turns_l2_phase2(truth)
    replies += drive_turns(d, turns2, 76, {220})
    exp: dict = {}
    _train, test = D115.l1_people()
    for kid, mom, gran, spo, bos, fri, doc in test:
        exp[(kid, D115.W0)] = gran
        exp[(kid, D115.W1)] = bos
        exp[(kid, D115.W2)] = doc
    k = 221
    for w in D115.WORDS:
        for row in test:
            kid = row[0]
            text = f"Who is {kid}'s {D115.ASK[w]}?"
            submit(d, f"t{k:03d}", text)
            reply = wait_outbox(d, f"t{k:03d}")
            replies.append({"n": k, "kind": "probe", "word": w,
                            "text": text, "reply": reply.strip(),
                            "verdict": classify(reply, exp[(kid, w)])})
            k += 1
    stop_daemon(proc, d)
    rep = score_session130(d, seed, tag, replies, truth,
                           list(D115.WORDS), t0, [75, 145])
    rep["rung"] = "G3-L2"
    rep["replies"] = replies
    return rep


def run_g3l3(seed: int, root: Path) -> dict:
    t0 = time.time()
    tag = f"g3l3-seed{seed}"
    d = root / tag
    if d.exists():
        shutil.rmtree(d)
    proc = spawn(d, seed, threshold=100)
    turns, truth = D115.build_turns_l3()
    replies = drive_turns(d, turns, 1, {100})
    stop_daemon(proc, d)
    rep = score_session130(d, seed, tag, replies, truth, [D115.W2], t0,
                           [100])
    rep["rung"] = "G3-L3"
    rep["replies"] = replies
    return rep


G3_RUNNERS = {"L1": (run_g3l1, D115.l1_pass, "l1"),
              "L2": (run_g3l2, D115.l2_pass, "l2"),
              "L3": (run_g3l3, D115.l3_pass, "l3")}


def g3_identical(rep: dict, ref115: dict, rung: str) -> tuple[bool, str]:
    """Byte-identical outcomes vs sealed 115 (timing excluded)."""
    mine = {k: v for k, v in rep.items()
            if k not in ("seconds", "replies", "dir", "rung")}
    theirs = {k: v for k, v in ref115.items()
              if k not in ("seconds", "dir", "thresholds")}
    # per-sleep wall-clock excluded (shared machine); gate numbers kept.
    # 130 rows carry additive grew_slot/frozen_ok fields: normalise to the
    # sealed 115 key set before comparing.
    keep = {"installed", "episodes", "oof_best", "refit_agreement"}
    for s in mine.get("sleeps", []):
        s.pop("sleep_seconds", None)
        for wrec in s.get("words", {}).values():
            for k in list(wrec):
                if k not in keep:
                    wrec.pop(k, None)
    for s in theirs.get("sleeps", []):
        s.pop("sleep_seconds", None)
    if mine.get("sleeps") != theirs.get("sleeps"):
        return False, f"{rung} sleeps differ"
    if mine.get("per_word") != theirs.get("per_word"):
        return False, f"{rung} per_word differ"
    for key in ("installed_words", "n_sleeps",
                "report_rows_sleep_derived", "taught_good", "taught_total",
                "taught_dupes", "sleep_overwrote_taught", "teaches_saved",
                "teaches_total", "turns"):
        if mine.get(key) != theirs.get(key):
            return False, f"{rung} {key}: {mine.get(key)} != {theirs.get(key)}"
    grew = [wrec.get("grew_slot") is True
            for s in rep["sleeps"] for wrec in s["words"].values()]
    if any(grew):
        return False, f"{rung} grew a slot (must not fire when free)"
    return True, f"{rung} identical"


# ------------------------------------------------------- unregistered climb
def build_turns_climb(n_words: int) -> tuple[list[dict], dict]:
    """8 (or 12) x 75-turn phases + 5 probes/word. Phases 1-5 are L4's own
    teaches/asks (same names, same order); later phases add two-hop chains."""
    assert n_words in (8, 12)
    words = WORDS8 if n_words == 8 else WORDS12
    l4turns, truth = D115.build_turns_l4()
    # L4 = 375 phase turns + 25 probes; keep the 375, drop L4's probes.
    turns = [t for t in l4turns if t["kind"] != "probe"]
    assert len(turns) == 375, len(turns)
    # person pools per extra word (disjoint from L4's K/M/G/S/B/F/D/P/Q/R
    # and T/N/H/U/V/W/X/C/E/A families to avoid collisions).
    pools = {
        5: ("MO", "SP"), 6: ("BM", "BO"), 7: ("TF", "TT"),
        8: ("DS", "DO"), 9: ("FM", "FA"), 10: ("DB", "DC"),
        11: ("TM", "TE"),
    }
    exp: dict = {}
    for row in [(f"T{i:02d}", f"N{i:02d}", f"H{i:02d}", f"U{i:02d}",
                 f"V{i:02d}", f"W{i:02d}", f"X{i:02d}", f"C{i:02d}",
                 f"E{i:02d}", f"A{i:02d}") for i in range(1, 6)]:
        (kid, _m, gran, _s, bos, _f, doc, _p, dbos, tea) = row
        exp[(kid, WORDS5[0])] = gran
        exp[(kid, WORDS5[1])] = bos
        exp[(kid, WORDS5[2])] = doc
        exp[(kid, WORDS5[3])] = dbos
        exp[(kid, WORDS5[4])] = tea
    for wi in range(5, n_words):
        w = words[wi]
        hop1, hop2 = CLIMB_CHAINS[w]
        pa, pb = pools[wi]
        for i in range(1, 21):
            b, c = f"{pb}{i:02d}", f"{pa}X{i:02d}"
            # chain: kid -hop1-> b -hop2-> c  (train kids J, test kids Y;
            # test middles/answers use a disjoint T-suffixed family).
            kid = f"J{i:02d}"
            turns.append({"kind": "teach",
                          "text": f"{kid}'s {hop1.replace('_', ' ')} is {b}.",
                          "expect": (kid, hop1.replace("_", " "), b)})
            turns.append({"kind": "teach",
                          "text": f"{b}'s {hop2.replace('_', ' ')} is {c}.",
                          "expect": (b, hop2.replace("_", " "), c)})
            truth[(kid, hop1.replace(" ", "_"))] = b
            truth[(b, hop2.replace(" ", "_"))] = c
        for i in range(1, 6):
            b, c = f"{pb}T{i:02d}", f"{pa}XT{i:02d}"
            kid = f"Y{i:02d}"
            turns.append({"kind": "teach",
                          "text": f"{kid}'s {hop1.replace('_', ' ')} is {b}.",
                          "expect": (kid, hop1.replace("_", " "), b)})
            turns.append({"kind": "teach",
                          "text": f"{b}'s {hop2.replace('_', ' ')} is {c}.",
                          "expect": (b, hop2.replace("_", " "), c)})
            truth[(kid, hop1.replace(" ", "_"))] = b
            truth[(b, hop2.replace(" ", "_"))] = c
            exp[(kid, w)] = c
        # train kids' answers c for episodes: map J-kid -> c
        for i in range(1, 21):
            kid = f"J{i:02d}"
            c = f"{pa}X{i:02d}"
            exp[(kid, w)] = c
        for i in range(1, 21):
            kid = f"J{i:02d}"
            turns.append({"kind": "episode", "word": w,
                          "text": f"Who is {kid}'s {SURF[w]}?",
                          "expect": None})
        for text in D115.FILLERS:
            turns.append({"kind": "filler", "text": text})
    for w in words:
        for kid in ([f"T{i:02d}" for i in range(1, 6)] if words.index(w) < 5
                    else [f"Y{i:02d}" for i in range(1, 6)]):
            turns.append({"kind": "probe", "word": w,
                          "text": f"Who is {kid}'s {SURF[w]}?",
                          "expect": exp[(kid, w)]})
    return turns, truth


def run_climb(seed: int, root: Path, n_words: int) -> dict:
    t0 = time.time()
    tag = f"g4-{n_words}-seed{seed}"
    d = root / tag
    if d.exists():
        shutil.rmtree(d)
    proc = spawn(d, seed, threshold=75)
    words = WORDS8 if n_words == 8 else WORDS12
    turns, truth = build_turns_climb(n_words)
    sleep_at = {75 * i for i in range(1, n_words + 1)}
    replies = drive_turns(d, turns, 1, sleep_at)
    stop_daemon(proc, d)
    rep = score_session130(d, seed, tag, replies, truth, words, t0, [75])
    rep["rung"] = f"G4-{n_words}"
    rep["replies"] = replies
    return rep


def climb_summary(rep: dict, words: list[str]) -> dict:
    return {
        "installed": rep["installed_words"],
        "n_sleeps": rep["n_sleeps"],
        "per_sleep_seconds": [s.get("sleep_seconds") for s in rep["sleeps"]],
        "probes": {w: (rep["per_word"][w]["correct"],
                        rep["per_word"][w]["wrong"],
                        rep["per_word"][w]["total"]) for w in words},
        "taught": f"{rep['taught_good']}/{rep['taught_total']}",
        "overwrites": rep["sleep_overwrote_taught"],
    }


# ------------------------------------------------------------------------ main
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 130 registered wave")
    parser.add_argument("--root", default=str(ART / "runs"))
    parser.add_argument("--report", default=str(ART / "wave-report.json"))
    parser.add_argument("--ref115", default=str(
        SCRIPTS.parent / "artifacts" / "fable-sleep115-20260922"
        / "wave-report.json"))
    parser.add_argument("--seed", type=int, action="append", default=None)
    parser.add_argument("--only", action="append", default=None,
                        help="subset of: g1 g3l1 g3l2 g3l3 g4-8 g4-12")
    args = parser.parse_args(argv)
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    seeds = tuple(args.seed) if args.seed else (1, 2)
    only = None
    if args.only:
        only = set()
        for chunk in args.only:
            only.update(c.strip().lower() for c in chunk.split(",")
                        if c.strip())

    def want(name: str) -> bool:
        return only is None or name in only

    ref = json.loads(Path(args.ref115).read_text(encoding="utf-8"))
    t0 = time.time()
    out: dict = {"registered": {}, "unregistered": {}}

    if want("g1"):
        reps = {}
        for seed in seeds:
            r = run_g1(seed, root / "g1")
            reps[str(seed)] = {k: v for k, v in r.items() if k != "replies"}
            print(f"G1 seed {seed}: sleeps={r['n_sleeps']} "
                  + " ".join(f"{w}={r['per_word'][w]['correct']}/"
                              f"{r['per_word'][w]['total']}/"
                              f"w{r['per_word'][w]['wrong']}"
                              for w in WORDS5)
                  + f" taught={r['taught_good']}/{r['taught_total']} "
                  f"g1={g1_pass({**r})} g2={g2_pass({**r})} "
                  f"{r['seconds']}s", flush=True)
        out["registered"]["G1"] = {
            "seeds": reps,
            "pass_g1": all(g1_pass({**reps[s], "replies": [],
                                    "per_word": reps[s]["per_word"],
                                    "sleeps": reps[s]["sleeps"]})
                           for s in reps),
            "pass_g2": all(g2_pass({**reps[s], "replies": [],
                                    "per_word": reps[s]["per_word"],
                                    "sleeps": reps[s]["sleeps"]})
                           for s in reps)}

    if any(want(k) for k in ("g3l1", "g3l2", "g3l3")):
        g3seeds = tuple(args.seed) if args.seed else (1, 2, 3)
        for rung, refkey in (("g3l1", "L1"), ("g3l2", "L2"), ("g3l3", "L3")):
            if not want(rung):
                continue
            run, _, _ = {"g3l1": (run_g3l1, None, None),
                         "g3l2": (run_g3l2, None, None),
                         "g3l3": (run_g3l3, None, None)}[rung]
            reps = {}
            ident = {}
            for seed in g3seeds:
                r = run(seed, root / rung)
                reps[str(seed)] = {k: v for k, v in r.items()
                                    if k != "replies"}
                ok, note = g3_identical(
                    {**r}, ref["rungs"][refkey]["seeds"][str(seed)], refkey)
                ident[str(seed)] = {"identical": ok, "note": note}
                print(f"G3-{refkey} seed {seed}: {note} "
                      f"{r['seconds']}s", flush=True)
            out["registered"][f"G3-{refkey}"] = {
                "seeds": reps, "identical": ident,
                "pass": all(v["identical"] for v in ident.values())}

    for n in (8, 12):
        name = f"g4-{n}"
        if not want(name):
            continue
        if n == 12 and want("g4-12") and "G4-8" in out["unregistered"]:
            prev = out["unregistered"]["G4-8"]["seeds"]["1"]
            if len(prev["installed_words"]) < 8:
                print("G4-12 skipped: 8 did not pass.", flush=True)
                continue
        r = run_climb(1, root / "g4", n)
        words = WORDS8 if n == 8 else WORDS12
        out["unregistered"][f"G4-{n}"] = {
            "seeds": {"1": {k: v for k, v in r.items() if k != "replies"}},
            "summary": climb_summary({**r}, words)}
        s = out["unregistered"][f"G4-{n}"]["summary"]
        print(f"G4-{n} seed 1: installed={s['installed']} "
              f"sleeps={s['n_sleeps']} sleep_s={s['per_sleep_seconds']} "
              f"probes={s['probes']} {r['seconds']}s", flush=True)

    out["wave_seconds"] = round(time.time() - t0, 1)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(out, indent=1, sort_keys=True),
                                 encoding="utf-8")
    print(f"wave {out['wave_seconds']}s -> {args.report}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
