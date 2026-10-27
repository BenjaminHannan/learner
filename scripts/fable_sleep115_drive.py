#!/usr/bin/env python3
"""Experiment 115 driver -- registered scale ladder L1..L5 (additive only).

Ladder (run in order, stop at the first rung that fails its marks):
  L1  20 train + 5 test chains x 6 teaches, 20 episode-asks x 3 words,
      5 fillers, threshold 215 (ONE sleep installs all three words),
      15 NEW-people probes (5/word).
  L2  phase 1 (threshold 75): mother chains + 20 w0 asks -> sleep 1 (A).
      Restart in the same dir (threshold 145): spouse/boss + best-friend /
      doctor teaches + 20 w1 + 20 w2 asks -> sleep 2 (B, C).
      Probes 5/word incl. A-retention after sleep 2.
  L3  3-hop word alone: mother/best-friend/doctor chains + 20 w2 asks,
      threshold 100, 5 probes.
  L4  400 turns, threshold 75 (5 sleeps): w0 / w1 / w2 in sleeps 1-3, then
      two further compositions with NO word slot (boss_of_father,
      teacher_of_spouse) in sleeps 4-5, then 25 probes (5 x 5 relations).
  L5  L4 plus kill -9 during the 3rd sleep (runs only if L4 passes).

Usage (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_sleep115_drive.py --root ART_DIR --seed 1
  (default: L1 seeds 1 2 3, then L2/L3/L4/L5 only while prior rungs pass;
   --only selects a subset, e.g. --only l1 --seed 1 is the L1 reproducer)

Nothing outside this file and the sleep115 artifacts is written. The driver
never calls sleep and never writes facts (mailbox files only).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (read-only)

ART = SCRIPTS.parent / "artifacts" / "fable-sleep115-20260922"
PY = [sys.executable, "-B", str(SCRIPTS / "fable_sleep115_agent.py")]

W0 = "maternal_grandmother"
W1 = "boss_of_spouse"
W2 = "doctor_of_mothers_friend"
WORDS = (W0, W1, W2)
# R44 skill indices (keep=0): mother 1, spouse 3, boss 4, best_friend 5.
EXPECT = {W0: [1, 1], W1: [3, 4], W2: [1, 5, 7]}
ASK = {W0: "maternal grandmother", W1: "boss of spouse",
       W2: "doctor of mothers friend"}
FILLERS = ["Hi, how are you?", "Thanks, that helps.",
           "What is the weather like today?", "Tell me a joke.",
           "Good morning!"]


# ------------------------------------------------------------------ worlds
def l1_people():
    train, test = [], []
    for i in range(1, 21):
        k = {k: f"{k}{i:02d}" for k in "KMGSBFD"}
        train.append((k["K"], k["M"], k["G"], k["S"], k["B"], k["F"],
                      k["D"]))
    for i in range(1, 6):
        t = {k: f"{k}{i:02d}" for k in "TNHUVWX"}
        test.append((t["T"], t["N"], t["H"], t["U"], t["V"], t["W"],
                     t["X"]))
    return train, test


def build_turns_l1() -> tuple[list[dict], dict]:
    train, test = l1_people()
    truth: dict = {}
    turns: list[dict] = []

    def teach(subj, rel, obj):
        turns.append({"kind": "teach", "text": f"{subj}'s {rel} is {obj}.",
                      "expect": (subj, rel, obj)})
        truth[(subj, rel.replace(" ", "_"))] = obj

    for kid, mom, gran, spo, bos, fri, doc in train + test:
        teach(kid, "mother", mom)
        teach(mom, "mother", gran)
        teach(kid, "spouse", spo)
        teach(spo, "boss", bos)
        teach(mom, "best friend", fri)
        teach(fri, "doctor", doc)
    for word in WORDS:
        for kid, *_ in train:
            turns.append({"kind": "episode", "word": word,
                          "text": f"Who is {kid}'s {ASK[word]}?",
                          "expect": None})
    for text in FILLERS:
        turns.append({"kind": "filler", "text": text})
    probes = []
    for word in WORDS:
        for kid, *_ in test:
            probes.append({"kind": "probe", "word": word,
                           "text": f"Who is {kid}'s {ASK[word]}?",
                           "expect": None})
    # Expected probe answers from the taught chains.
    exp = {}
    for kid, mom, gran, spo, bos, fri, doc in test:
        exp[(kid, W0)] = gran
        exp[(kid, W1)] = bos
        exp[(kid, W2)] = doc
    for p in probes:
        kid = p["text"].split("'")[0].split()[-1]
        p["expect"] = exp[(kid, p["word"])]
    turns.extend(probes)
    assert len(turns) == 150 + 60 + 5 + 15, len(turns)
    return turns, truth


def build_turns_l2_phase1() -> tuple[list[dict], dict]:
    train, test = l1_people()
    truth: dict = {}
    turns: list[dict] = []

    def teach(subj, rel, obj):
        turns.append({"kind": "teach", "text": f"{subj}'s {rel} is {obj}.",
                      "expect": (subj, rel, obj)})
        truth[(subj, rel.replace(" ", "_"))] = obj

    for kid, mom, gran, *_ in train + test:
        teach(kid, "mother", mom)
        teach(mom, "mother", gran)
    for kid, *_ in train:
        turns.append({"kind": "episode", "word": W0,
                      "text": f"Who is {kid}'s {ASK[W0]}?", "expect": None})
    for text in FILLERS:
        turns.append({"kind": "filler", "text": text})
    assert len(turns) == 75, len(turns)
    return turns, truth


def build_turns_l2_phase2(truth: dict) -> list[dict]:
    train, test = l1_people()
    turns: list[dict] = []
    for kid, mom, _g, spo, bos, fri, doc in train + test:
        for subj, rel, obj in ((kid, "spouse", spo), (spo, "boss", bos),
                               (mom, "best friend", fri),
                               (fri, "doctor", doc)):
            turns.append({"kind": "teach",
                          "text": f"{subj}'s {rel} is {obj}.",
                          "expect": (subj, rel, obj)})
            truth[(subj, rel.replace(" ", "_"))] = obj
    for word in (W1, W2):
        for kid, *_ in train:
            turns.append({"kind": "episode", "word": word,
                          "text": f"Who is {kid}'s {ASK[word]}?",
                          "expect": None})
    for text in FILLERS:
        turns.append({"kind": "filler", "text": text})
    assert len(turns) == 145, len(turns)
    return turns


def build_turns_l3() -> tuple[list[dict], dict]:
    train = [(f"K{i:02d}", f"M{i:02d}", f"F{i:02d}", f"D{i:02d}")
             for i in range(1, 21)]
    test = [(f"T{i:02d}", f"N{i:02d}", f"W{i:02d}", f"X{i:02d}")
            for i in range(1, 6)]
    truth: dict = {}
    turns: list[dict] = []

    def teach(subj, rel, obj):
        turns.append({"kind": "teach", "text": f"{subj}'s {rel} is {obj}.",
                      "expect": (subj, rel, obj)})
        truth[(subj, rel.replace(" ", "_"))] = obj

    for kid, mom, fri, doc in train + test:
        teach(kid, "mother", mom)
        teach(mom, "best friend", fri)
        teach(fri, "doctor", doc)
    for kid, *_ in train:
        turns.append({"kind": "episode", "word": W2,
                      "text": f"Who is {kid}'s {ASK[W2]}?", "expect": None})
    for text in FILLERS:
        turns.append({"kind": "filler", "text": text})
    exp = {kid: doc for kid, _, _, doc in test}
    for kid, *_ in test:
        turns.append({"kind": "probe", "word": W2,
                      "text": f"Who is {kid}'s {ASK[W2]}?",
                      "expect": exp[kid]})
    assert len(turns) == 75 + 20 + 5 + 5, len(turns)
    return turns, truth


def build_turns_l4() -> tuple[list[dict], dict]:
    train = [(f"K{i:02d}", f"M{i:02d}", f"G{i:02d}", f"S{i:02d}",
              f"B{i:02d}", f"F{i:02d}", f"D{i:02d}", f"P{i:02d}",
              f"Q{i:02d}", f"R{i:02d}") for i in range(1, 21)]
    test = [(f"T{i:02d}", f"N{i:02d}", f"H{i:02d}", f"U{i:02d}",
             f"V{i:02d}", f"W{i:02d}", f"X{i:02d}", f"C{i:02d}",
             f"E{i:02d}", f"A{i:02d}") for i in range(1, 6)]
    truth: dict = {}
    turns: list[dict] = []

    def teach(subj, rel, obj):
        turns.append({"kind": "teach", "text": f"{subj}'s {rel} is {obj}.",
                      "expect": (subj, rel, obj)})
        truth[(subj, rel.replace(" ", "_"))] = obj

    # Phase 1 (t001-075): w0.
    for kid, mom, gran, *_ in train + test:
        teach(kid, "mother", mom)
        teach(mom, "mother", gran)
    for kid, *_ in train:
        turns.append({"kind": "episode", "word": W0,
                      "text": f"Who is {kid}'s {ASK[W0]}?", "expect": None})
    for text in FILLERS:
        turns.append({"kind": "filler", "text": text})
    # Phase 2 (t076-150): w1.
    for kid, mom, _g, spo, bos, *_ in train + test:
        teach(kid, "spouse", spo)
        teach(spo, "boss", bos)
    for kid, *_ in train:
        turns.append({"kind": "episode", "word": W1,
                      "text": f"Who is {kid}'s {ASK[W1]}?", "expect": None})
    for text in FILLERS:
        turns.append({"kind": "filler", "text": text})
    # Phase 3 (t151-225): w2.
    for _k, mom, _g, _s, _b, fri, doc, *_ in train + test:
        teach(mom, "best friend", fri)
        teach(fri, "doctor", doc)
    for kid, *_ in train:
        turns.append({"kind": "episode", "word": W2,
                      "text": f"Who is {kid}'s {ASK[W2]}?", "expect": None})
    for text in FILLERS:
        turns.append({"kind": "filler", "text": text})
    # Phase 4 (t226-300): 4th composition, NO word slot.
    for kid, _m, _g, _s, _b, _f, _d, dad, dbos, _r in train + test:
        teach(kid, "father", dad)
        teach(dad, "boss", dbos)
    for kid, *_ in train:
        turns.append({"kind": "episode", "word": "boss_of_father",
                      "text": f"Who is {kid}'s boss of father?",
                      "expect": None})
    for text in FILLERS:
        turns.append({"kind": "filler", "text": text})
    # Phase 5 (t301-375): 5th composition, NO word slot.
    for kid, _m, _g, spo, _b, _f, _d, _p, _q, tea in train + test:
        teach(kid, "spouse", spo)  # same value: DUPLICATE_OK, no dupe row
        teach(spo, "teacher", tea)
    for kid, *_ in train:
        turns.append({"kind": "episode", "word": "teacher_of_spouse",
                      "text": f"Who is {kid}'s teacher of spouse?",
                      "expect": None})
    for text in FILLERS:
        turns.append({"kind": "filler", "text": text})
    # Probes (t376-400): 5 per relation.
    exp: dict = {}
    for row in test:
        (kid, _m, gran, _s, bos, _f, doc, _p, dbos, tea) = row
        exp[(kid, W0)] = gran
        exp[(kid, W1)] = bos
        exp[(kid, W2)] = doc
        exp[(kid, "boss_of_father")] = dbos
        exp[(kid, "teacher_of_spouse")] = tea
    surfaces = {W0: ASK[W0], W1: ASK[W1], W2: ASK[W2],
                "boss_of_father": "boss of father",
                "teacher_of_spouse": "teacher of spouse"}
    for word in (W0, W1, W2, "boss_of_father", "teacher_of_spouse"):
        for row in test:
            kid = row[0]
            turns.append({"kind": "probe", "word": word,
                          "text": f"Who is {kid}'s {surfaces[word]}?",
                          "expect": exp[(kid, word)]})
    assert len(turns) == 400, len(turns)
    return turns, truth


# ------------------------------------------------------------ mailbox helpers
def spawn(d: Path, seed: int, idle_seconds: float = 3600.0,
          threshold: int = 75):
    d.mkdir(parents=True, exist_ok=True)
    cfg = {"state_dir": str(d), "sleep_threshold": threshold,
           "sleep115_seed": seed}
    cfg_path = d / "sleep115-config.json"
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
            raise RuntimeError(f"sleep115 daemon exited early: {proc.poll()}")
        if (d / "heartbeat.json").exists() and (
                d / "daemon_status.json").exists():
            return proc
        time.sleep(0.05)
    proc.kill()
    raise RuntimeError("sleep115 daemon did not write heartbeat in time")


def submit(d: Path, name: str, text: str) -> None:
    tmp = d / "inbox" / f"{name}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text if text.endswith("\n") else text + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, d / "inbox" / f"{name}.txt")


def wait_outbox(d: Path, name: str, timeout: float = 300.0) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        path = d / "outbox" / f"{name}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        time.sleep(0.02)
    raise RuntimeError(f"no outbox reply for {name} within {timeout}s")


def stop_daemon(proc, d: Path, timeout: float = 30.0) -> None:
    (d / "STOP").write_text("stop\n", encoding="utf-8")
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    if proc.poll() is None:
        proc.kill()
        raise RuntimeError("daemon did not stop in time")
    proc._log.close()  # type: ignore[attr-defined]


def read_log(d: Path) -> list[dict]:
    p = d / "daemon.log.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8")
            .splitlines() if line.strip()]


def taught_ok(nb, truth: dict) -> tuple[int, int]:
    good = dupes = 0
    for (name, rel), want in truth.items():
        found = nb.resolve(name)
        if found.status != C.OK:
            continue
        rows = [r for r in nb.current(found.detail["entity_id"], rel)
                if r["source"] == "taught"]
        vals = [nb.entities.get(r["value"].get("entity", ""), "")
                if "entity" in r["value"] else str(r["value"].get("literal"))
                for r in rows]
        if vals.count(want) == 1 and len(vals) == 1:
            good += 1
        if len(rows) != 1:
            dupes += 1
    return good, dupes


def sleep_overwrites(nb) -> int:
    n = 0
    for fact in nb.facts.values():
        if fact.get("source") == "sleep-derived" and fact.get("supersedes"):
            old = nb.facts.get(fact["supersedes"])
            if old is not None and old.get("source") == "taught":
                n += 1
    return n


def classify(reply: str, expect: str) -> str:
    low = reply.lower()
    if expect.lower() in low:
        return "correct"
    if "don't know" in low or "do not know" in low:
        return "abstain"
    return "wrong"


def check_routing(d: Path, wname: str) -> bool:
    try:
        data = json.loads((d / "sleep115-words.json").read_text(
            encoding="utf-8"))
        logits = data["words"][wname]["logits"]
        arg = [max(range(9), key=lambda i: r[i]) for r in logits]
        want = EXPECT.get(wname)
        if want is None:
            return False
        return ([a for a in arg if a != 0] == want
                and data["words"][wname].get("report_fid") is not None)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def drive_turns(d: Path, turns: list[dict], start: int,
                sleep_at: set[int]) -> list[dict]:
    replies: list[dict] = []
    for k, turn in enumerate(turns, start):
        name = f"t{k:03d}"
        submit(d, name, turn["text"])
        reply = wait_outbox(d, name,
                            timeout=900.0 if k in sleep_at else 300.0)
        entry = {"n": k, "kind": turn["kind"], "word": turn.get("word"),
                 "text": turn["text"], "reply": reply.strip()}
        if turn["kind"] in ("episode", "probe") and turn.get("expect"):
            entry["verdict"] = classify(reply, turn["expect"])
        else:
            entry["verdict"] = None
        replies.append(entry)
    return replies


def sleep_rows(d: Path) -> list[dict]:
    return [e for e in read_log(d) if e.get("event") == "sleep"]


def score_session(d: Path, seed: int, tag: str, replies: list[dict],
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
            "routing_ok": check_routing(d, w) if w in EXPECT else False,
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
                "refit_agreement": w.get("refit_agreement")}
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


# ------------------------------------------------------------------- rung L1
def run_l1(seed: int, root: Path) -> dict:
    t0 = time.time()
    tag = f"l1-seed{seed}"
    d = root / tag
    if d.exists():
        shutil.rmtree(d)
    proc = spawn(d, seed, threshold=215)
    turns, truth = build_turns_l1()
    replies = drive_turns(d, turns, 1, {215})
    stop_daemon(proc, d)
    rep = score_session(d, seed, tag, replies, truth, list(WORDS), t0,
                        [215])
    rep["rung"] = "L1"
    rep["replies"] = replies
    return rep


def l1_pass(rep: dict) -> bool:
    if rep["n_sleeps"] < 1:
        return False
    if any((s.get("sleep_seconds") or 0) >= 120 for s in rep["sleeps"]):
        return False
    for w in WORDS:
        p = rep["per_word"][w]
        if p["correct"] != 5 or p["wrong"] != 0:
            return False
        if p["sources_sleep_derived"] != 5:
            return False
        if not p["routing_ok"]:
            return False
    for s in rep["sleeps"]:
        for wname, wrec in s["words"].items():
            if wname in EXPECT:
                if not wrec["installed"]:
                    return False
                if (wrec["oof_best"] or 0) < 0.80:
                    return False
                if (wrec["refit_agreement"] or 0) < 0.90:
                    return False
            elif wrec["installed"]:
                return False
    if rep["taught_good"] != rep["taught_total"]:
        return False
    if rep["taught_dupes"] != 0 or rep["sleep_overwrote_taught"] != 0:
        return False
    if rep["report_rows_sleep_derived"] < 3:
        return False
    return True


# ------------------------------------------------------------------- rung L2
def run_l2(seed: int, root: Path) -> dict:
    t0 = time.time()
    tag = f"l2-seed{seed}"
    d = root / tag
    if d.exists():
        shutil.rmtree(d)
    proc = spawn(d, seed, threshold=75)
    turns1, truth = build_turns_l2_phase1()
    replies = drive_turns(d, turns1, 1, {75})
    stop_daemon(proc, d)
    proc = spawn(d, seed, threshold=145)
    turns2 = build_turns_l2_phase2(truth)
    replies += drive_turns(d, turns2, 76, {220})
    # Retention + new probes through the mailbox.
    exp: dict = {}
    _train, test = l1_people()
    for kid, mom, gran, spo, bos, fri, doc in test:
        exp[(kid, W0)] = gran
        exp[(kid, W1)] = bos
        exp[(kid, W2)] = doc
    k = 221
    for w in WORDS:
        for row in test:
            kid = row[0]
            text = f"Who is {kid}'s {ASK[w]}?"
            submit(d, f"t{k:03d}", text)
            reply = wait_outbox(d, f"t{k:03d}")
            replies.append({"n": k, "kind": "probe", "word": w,
                            "text": text, "reply": reply.strip(),
                            "verdict": classify(reply, exp[(kid, w)])})
            k += 1
    stop_daemon(proc, d)
    rep = score_session(d, seed, tag, replies, truth, list(WORDS), t0,
                        [75, 145])
    rep["rung"] = "L2"
    rep["replies"] = replies
    return rep


def l2_pass(rep: dict) -> bool:
    if rep["n_sleeps"] < 2:
        return False
    if any((s.get("sleep_seconds") or 0) >= 120 for s in rep["sleeps"]):
        return False
    first, second = rep["sleeps"][0], rep["sleeps"][1]
    if W0 not in first["words"] or not first["words"][W0]["installed"]:
        return False
    for w in (W1, W2):
        if w not in second["words"] or not second["words"][w]["installed"]:
            return False
    for w in WORDS:
        p = rep["per_word"][w]
        if p["correct"] != 5 or p["wrong"] != 0:
            return False
        if p["sources_sleep_derived"] != 5:
            return False
        if not p["routing_ok"]:
            return False
    for s in rep["sleeps"]:
        for wname, wrec in s["words"].items():
            if wrec["installed"] and (
                    (wrec["oof_best"] or 0) < 0.80
                    or (wrec["refit_agreement"] or 0) < 0.90):
                return False
    if rep["taught_good"] != rep["taught_total"]:
        return False
    if rep["taught_dupes"] != 0 or rep["sleep_overwrote_taught"] != 0:
        return False
    return True


# ------------------------------------------------------------------- rung L3
def run_l3(seed: int, root: Path) -> dict:
    t0 = time.time()
    tag = f"l3-seed{seed}"
    d = root / tag
    if d.exists():
        shutil.rmtree(d)
    proc = spawn(d, seed, threshold=100)
    turns, truth = build_turns_l3()
    replies = drive_turns(d, turns, 1, {100})
    stop_daemon(proc, d)
    rep = score_session(d, seed, tag, replies, truth, [W2], t0, [100])
    rep["rung"] = "L3"
    rep["replies"] = replies
    return rep


def l3_pass(rep: dict) -> bool:
    if rep["n_sleeps"] < 1:
        return False
    if any((s.get("sleep_seconds") or 0) >= 120 for s in rep["sleeps"]):
        return False
    p = rep["per_word"][W2]
    if p["correct"] != 5 or p["wrong"] != 0:
        return False
    if p["sources_sleep_derived"] != 5:
        return False
    if not p["routing_ok"]:
        return False
    for s in rep["sleeps"]:
        for wname, wrec in s["words"].items():
            if wrec["installed"] and (
                    (wrec["oof_best"] or 0) < 0.80
                    or (wrec["refit_agreement"] or 0) < 0.90):
                return False
            if wrec["installed"] and wname != W2:
                return False
    if rep["taught_good"] != rep["taught_total"]:
        return False
    if rep["taught_dupes"] != 0 or rep["sleep_overwrote_taught"] != 0:
        return False
    return True


# ------------------------------------------------------------------- rung L4
def run_l4(seed: int, root: Path) -> dict:
    t0 = time.time()
    tag = f"l4-seed{seed}"
    d = root / tag
    if d.exists():
        shutil.rmtree(d)
    proc = spawn(d, seed, threshold=75)
    turns, truth = build_turns_l4()
    replies = drive_turns(d, turns, 1, {75, 150, 225, 300, 375})
    stop_daemon(proc, d)
    rep = score_session(
        d, seed, tag, replies, truth,
        [W0, W1, W2, "boss_of_father", "teacher_of_spouse"], t0, [75])
    rep["rung"] = "L4"
    rep["replies"] = replies
    return rep


def l4_pass(rep: dict) -> bool:
    if rep["n_sleeps"] < 5:
        return False
    if any((s.get("sleep_seconds") or 0) >= 120 for s in rep["sleeps"]):
        return False
    for w in (W0, W1, W2, "boss_of_father", "teacher_of_spouse"):
        p = rep["per_word"][w]
        if p["correct"] != 5 or p["wrong"] != 0:
            return False
        if p["sources_sleep_derived"] != 5:
            return False
        if w in EXPECT and not p["routing_ok"]:
            return False
    if rep["taught_good"] != rep["taught_total"]:
        return False
    if rep["taught_dupes"] != 0 or rep["sleep_overwrote_taught"] != 0:
        return False
    return True


# ------------------------------------------------------------------- rung L5
def run_l5(seed: int, root: Path) -> dict:
    """L4 plus kill -9 during the 3rd sleep (runs only if L4 passes)."""
    t0 = time.time()
    tag = f"l5-seed{seed}"
    d = root / tag
    if d.exists():
        shutil.rmtree(d)
    proc = spawn(d, seed, threshold=75)
    turns, truth = build_turns_l4()
    replies: list[dict] = []
    # Phases 1-2 live (sleeps 1-2 install w0, w1).
    for k, turn in enumerate(turns[:150], 1):
        submit(d, f"t{k:03d}", turn["text"])
        reply = wait_outbox(d, f"t{k:03d}",
                            timeout=900.0 if k in (75, 150) else 300.0)
        replies.append({"n": k, "kind": turn["kind"],
                        "word": turn.get("word"), "text": turn["text"],
                        "reply": reply.strip(), "verdict": None})
    # Phase 3's sleep (t225): submit, then kill -9 mid-SLEEP.
    for k, turn in enumerate(turns[150:225], 151):
        submit(d, f"t{k:03d}", turn["text"])
        if k == 225:
            break
        reply = wait_outbox(d, f"t{k:03d}")
        replies.append({"n": k, "kind": turn["kind"],
                        "word": turn.get("word"), "text": turn["text"],
                        "reply": reply.strip(), "verdict": None})
    marker = d / "sleep115-SLEEPING"
    deadline = time.time() + 600.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("daemon died before the kill")
        if marker.exists():
            break
        time.sleep(0.02)
    saw_marker = marker.exists()
    if proc.poll() is None:
        os.kill(proc.pid, signal.SIGKILL)
        proc.wait()
    try:
        proc._log.close()  # type: ignore[attr-defined]
    except (OSError, ValueError):
        pass
    proc = spawn(d, seed, threshold=75)
    status = json.loads((d / "daemon_status.json").read_text(
        encoding="utf-8"))
    reply = wait_outbox(d, "t225", timeout=900.0)
    replies.append({"n": 225, "kind": turns[224]["kind"],
                    "word": turns[224].get("word"),
                    "text": turns[224]["text"], "reply": reply.strip(),
                    "verdict": None})
    for k, turn in enumerate(turns[225:], 226):
        submit(d, f"t{k:03d}", turn["text"])
        rp = wait_outbox(d, f"t{k:03d}",
                         timeout=900.0 if k in (300, 375) else 300.0)
        entry = {"n": k, "kind": turn["kind"], "word": turn.get("word"),
                 "text": turn["text"], "reply": rp.strip()}
        if turn["kind"] == "probe" and turn.get("expect"):
            entry["verdict"] = classify(rp, turn["expect"])
        else:
            entry["verdict"] = None
        replies.append(entry)
    stop_daemon(proc, d)
    rep = score_session(
        d, seed, tag, replies, truth,
        [W0, W1, W2, "boss_of_father", "teacher_of_spouse"], t0, [75])
    rep["rung"] = "L5"
    rep["replies"] = replies
    rep["kill"] = {"saw_sleep_marker_before_kill": saw_marker,
                   "boot_ok": status.get("boot_ok")}
    return rep


# ------------------------------------------------------------------------ main
RUNNERS = {"L1": (run_l1, l1_pass), "L2": (run_l2, l2_pass),
           "L3": (run_l3, l3_pass), "L4": (run_l4, l4_pass)}
LADDER = ("L1", "L2", "L3", "L4", "L5")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 115 registered ladder")
    parser.add_argument("--root", default=str(ART / "runs"))
    parser.add_argument("--report", default=str(ART / "wave-report.json"))
    parser.add_argument("--seed", type=int, action="append", default=None)
    parser.add_argument("--only", action="append", default=None,
                        help="subset of: l1 l2 l3 l4 l5")
    args = parser.parse_args(argv)
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    seeds = tuple(args.seed) if args.seed else (1, 2, 3)
    only = None
    if args.only:
        only = set()
        for chunk in args.only:
            only.update(c.strip().upper() for c in chunk.split(",")
                        if c.strip())

    def want(rung: str) -> bool:
        return only is None or rung in only

    t0 = time.time()
    out: dict = {"rungs": {}, "breaking_point": None,
                 "stopped_by_rule": False}
    wave_replies: dict = {}
    for rung in LADDER:
        if rung == "L5":
            prev = out["rungs"].get("L4", {})
            if not prev.get("pass"):
                out["stopped_by_rule"] = True
                print("L5 skipped: L4 did not pass (stop rule).",
                      flush=True)
                break
            if not want("L5"):
                break
            reps = {}
            for seed in seeds:
                r = run_l5(seed, root / "l5")
                reps[str(seed)] = {k: v for k, v in r.items()
                                   if k != "replies"}
                print(f"L5 seed {seed}: kill_marker="
                      f"{int(r['kill']['saw_sleep_marker_before_kill'])} "
                      f"boot_ok={r['kill']['boot_ok']} "
                      f"sleeps={r['n_sleeps']} {r['seconds']}s", flush=True)
            passed = all(l4_pass(
                {**reps[s], "replies": []}) for s in reps)
            out["rungs"]["L5"] = {"seeds": reps, "pass": passed}
            if not passed:
                out["breaking_point"] = "L5"
            break
        run, check = RUNNERS[rung]
        if not want(rung):
            continue
        if out["breaking_point"] is not None:
            out["stopped_by_rule"] = True
            print(f"{rung} skipped: ladder stopped at "
                  f"{out['breaking_point']}.", flush=True)
            break
        reps = {}
        for seed in seeds:
            r = run(seed, root / rung.lower())
            reps[str(seed)] = {k: v for k, v in r.items()
                               if k != "replies"}
            if rung == "L1" and str(seed) == str(seeds[0]):
                wave_replies["l1-seed1"] = r["replies"]
            sleeps_s = ",".join(
                str(s.get("sleep_seconds")) for s in r["sleeps"])
            print(f"{rung} seed {seed}: sleeps={r['n_sleeps']} "
                  f"sleep_s=[{sleeps_s}] "
                  + " ".join(
                      f"{w}={r['per_word'][w]['correct']}/"
                      f"{r['per_word'][w]['total']}"
                      for w in r["per_word"])
                  + f" taught={r['taught_good']}/{r['taught_total']} "
                  f"{r['seconds']}s", flush=True)
        passed = all(check(reps[s]) for s in reps)
        out["rungs"][rung] = {"seeds": reps, "pass": passed}
        if not passed:
            out["breaking_point"] = rung
    out["wave_seconds"] = round(time.time() - t0, 1)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(out, indent=1, sort_keys=True),
                                 encoding="utf-8")
    if wave_replies.get("l1-seed1"):
        (Path(args.report).parent / "transcript-l1-seed1.txt").write_text(
            "\n".join(
                f"[{r['n']:03d} {r['kind']}/{r.get('word') or '-'}] "
                f"YOU: {r['text']}\n[{r['n']:03d}] DAEMON: {r['reply']}"
                for r in wave_replies["l1-seed1"]) + "\n", encoding="utf-8")
    print(f"breaking_point={out['breaking_point']} "
          f"wave {out['wave_seconds']}s -> {args.report}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
