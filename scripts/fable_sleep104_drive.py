#!/usr/bin/env python3
"""Experiment 104 driver -- registered mailbox wave Z1..Z5 (additive only).

World: 20 train chains (K kid, M mom, G gran) + 5 test chains (T/N/H).
Session (80 mailbox turns through the Sleep104Daemon ONLY):
  t001-t050  teach mother chains (test chains taught, never asked pre-sleep)
  t051-t070  20 "Who is Kxx's maternal grandmother?" -> 20 sleep episodes
  t071-t075  5 small-talk fillers (write nothing)
  [sleep_threshold=75: at the end of the 75th mailbox turn the log is
   full, so the daemon takes a SLEEP tick by itself inside that same turn;
   the exp-46 recipe installs maternal_grandmother, the bridge loads it
   into the live reasoner, one sleep-derived report row lands]
  t076-t080  5 "Who is Txx's maternal grandmother?" on NEW people.

Z4: fresh daemon, t001-t075, submit t076, SIGKILL (-9) when the SLEEPING
    marker appears (mid-SLEEP), restart, then reprocessed t076 + t077-t080
    + 200 taught-fact asks (50 mother facts x4) through the mailbox.
Z5: same 80 turns with 4 (resp. 8) of the 20 train second-hops taught
    wrong ("Mm's mother is Xx."), seed 1.

Usage (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_sleep104_drive.py --root ART_DIR --seed 1
  (default: seeds 1 2 3 + z4 + z5noise4 + z5noise8; --only selects a subset)

Nothing outside this file and the sleep104 artifacts is written. The
driver never calls sleep, never touches the notebook except read-only.
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

ART = SCRIPTS.parent / "artifacts" / "fable-sleep104-20260921"
PY = [sys.executable, "-B", str(SCRIPTS / "fable_sleep104_agent.py")]
SLEEP_THRESHOLD = 75
WORD = "maternal_grandmother"

TRAIN = [(f"K{i:02d}", f"M{i:02d}", f"G{i:02d}") for i in range(1, 21)]
TEST = [(f"T{i:02d}", f"N{i:02d}", f"H{i:02d}") for i in range(1, 6)]
FILLERS = ["Hi, how are you?", "Thanks, that helps.",
           "What is the weather like today?", "Tell me a joke.",
           "Good morning!"]


def build_turns(noise: int = 0) -> tuple[list[dict], dict]:
    """noise = number of train chains deliberately CORRUPTED AFTER the
    episode questions (a noisy teacher mis-corrects).

    Mechanism note: episodes are queued by walking the live notebook, so a
    wrong teach BEFORE the asks would still queue a notebook-consistent
    episode the gate cannot see (trial evidence: 8/20 pre-ask wrong teaches
    installed correctly, OOF 1.0). Genuine episode noise -- queued answers
    contradicting the notebook at sleep time, the exp-46 noise semantics --
    needs the corruption to land after the episodes are queued. So: correct
    teaches, correct asks (20 episodes queued), then `noise` wrong
    corrections ("Actually, Mm's mother is Xx."), then fillers, then probes.
    """
    truth = {}
    turns: list[dict] = []
    for kid, mom, gran in TRAIN + TEST:
        turns.append({"kind": "teach", "text": f"{kid}'s mother is {mom}.",
                      "expect": (kid, "mother", mom)})
        truth[(kid, "mother")] = mom
        turns.append({"kind": "teach",
                      "text": f"{mom}'s mother is {gran}.",
                      "expect": (mom, "mother", gran)})
        truth[(mom, "mother")] = gran
    for kid, _, gran in TRAIN:
        turns.append({"kind": "episode",
                      "text": f"Who is {kid}'s maternal grandmother?",
                      "expect": gran})
    for idx in range(noise):
        mom = TRAIN[idx][1]
        wrong = f"X{idx + 1:02d}"
        turns.append({"kind": "correction",
                      "text": f"Actually, {mom}'s mother is {wrong}.",
                      "expect": (mom, "mother", wrong)})
        truth[(mom, "mother")] = wrong
    for text in FILLERS:
        turns.append({"kind": "filler", "text": text})
    for kid, _, gran in TEST:
        turns.append({"kind": "probe",
                      "text": f"Who is {kid}'s maternal grandmother?",
                      "expect": gran})
    assert len(turns) == 80 + noise, len(turns)
    return turns, truth


def sleep_threshold_for(noise: int) -> int:
    # Log full exactly at the last filler: sleep fires inside that turn.
    return 75 + noise


# ------------------------------------------------------------ mailbox helpers
def spawn(d: Path, seed: int, idle_seconds: float = 3600.0,
          threshold: int = SLEEP_THRESHOLD):
    d.mkdir(parents=True, exist_ok=True)
    cfg = {"state_dir": str(d), "sleep_threshold": threshold,
           "sleep104_seed": seed}
    cfg_path = d / "sleep104-config.json"
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
            raise RuntimeError(f"sleep104 daemon exited early: {proc.poll()}")
        if (d / "heartbeat.json").exists() and (
                d / "daemon_status.json").exists():
            return proc
        time.sleep(0.05)
    proc.kill()
    raise RuntimeError("sleep104 daemon did not write heartbeat in time")


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
    """(facts answering correctly, dupes) over the intended taught set."""
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
    """sleep-derived facts that supersede a taught row (must be 0)."""
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


# ------------------------------------------------------------------ main wave
def run_seed(seed: int, root: Path, noise: int = 0) -> dict:
    t0 = time.time()
    tag = f"seed{seed}" + (f"-noise{noise}" if noise else "")
    d = root / tag
    if d.exists():
        shutil.rmtree(d)
    thr = sleep_threshold_for(noise)
    proc = spawn(d, seed, threshold=thr)
    turns, truth = build_turns(noise=noise)
    replies: list[dict] = []
    for i, turn in enumerate(turns, 1):
        name = f"t{i:03d}"
        submit(d, name, turn["text"])
        # The threshold-th turn fills the log: SLEEP fires inside it.
        reply = wait_outbox(d, name, timeout=900.0 if i == thr else 300.0)
        replies.append({"n": i, "kind": turn["kind"], "text": turn["text"],
                        "reply": reply.strip(),
                        "verdict": classify(reply, turn["expect"])
                        if turn["kind"] in ("episode", "probe") else None})
    stop_daemon(proc, d)
    log = read_log(d)
    sleeps = [e for e in log if e.get("event") == "sleep"]
    first = sleeps[0] if sleeps else {}
    recipe = first.get("recipe", {}) if isinstance(first, dict) else {}
    words = recipe.get("words", [])
    wrec = next((w for w in words if w.get("word") == WORD), {})
    nb = C.Notebook(d / "notebook")
    report_rows = [f for f in nb.facts.values()
                   if f.get("source") == "sleep-derived"]
    turn_events = [e for e in log if e.get("event") == "turn"]
    probe_recs = []
    for e in turn_events[-5:]:
        recs = e.get("records", [])
        probe_recs.append(recs[0] if recs else {})
    good, dupes = taught_ok(nb, truth)
    rep = {
        "seed": seed, "noise": noise, "dir": tag,
        "turns": len(turns), "sleep_threshold": thr,
        "seconds": round(time.time() - t0, 1),
        "sleeps_logged": len(sleeps),
        "sleep_file": first.get("file"),
        "sleep_seconds": first.get("sleep_seconds"),
        "turn_seconds_at_sleep": first.get("turn_seconds"),
        "recipe_attempted": bool(recipe.get("attempted")),
        "installed": bool(recipe.get("installed")),
        "episodes_at_install": sum(w.get("episodes", 0) for w in words),
        "oof_best": wrec.get("oof_best"),
        "refit_agreement": wrec.get("refit_agreement"),
        "bridge": first.get("bridge", {}),
        "report_rows_sleep_derived": len(report_rows),
        "probes": [{"text": r["text"], "reply": r["reply"],
                    "verdict": r["verdict"]} for r in replies[-5:]],
        "probes_correct": sum(1 for r in replies[-5:]
                              if r["verdict"] == "correct"),
        "probes_abstain": sum(1 for r in replies[-5:]
                              if r["verdict"] == "abstain"),
        "probes_wrong": sum(1 for r in replies[-5:]
                            if r["verdict"] == "wrong"),
        "probe_sources_sleep_derived": sum(
            1 for r in probe_recs
            if r.get("fields", {}).get("source") == "sleep-derived"),
        "taught_good": good, "taught_total": len(truth),
        "taught_dupes": dupes,
        "sleep_overwrote_taught": sleep_overwrites(nb),
        "teaches_saved": sum(
            1 for r in replies[:50] if "saved" in r["reply"].lower()),
    }
    rep["wrong_install"] = bool(
        rep["installed"] and (
            (rep["oof_best"] or 0) < 0.80
            or (rep["refit_agreement"] or 0) < 0.90
            or rep["probes_correct"] < 5
            or not check_routing(d)))
    return {"rep": rep, "replies": replies}


def check_routing(d: Path) -> bool:
    """Installed logits (atomic word file): skill stages mother, mother."""
    try:
        data = json.loads((d / "sleep104-word.json").read_text(
            encoding="utf-8"))
        logits = data["logits"]
        arg = [max(range(9), key=lambda i: r[i]) for r in logits]
        return ([a for a in arg if a != 0] == [1, 1]
                and data.get("word") == WORD)
    except (OSError, ValueError, KeyError, TypeError):
        return False


# ------------------------------------------------------------------------- Z4
def run_z4(root: Path) -> dict:
    t0 = time.time()
    d = root / "z4-kill"
    if d.exists():
        shutil.rmtree(d)
    proc = spawn(d, 1)
    turns, truth = build_turns()
    # SLEEP fires inside the 75th turn (log full at its end), so the kill
    # targets t075's processing.
    for i, turn in enumerate(turns[:74], 1):
        submit(d, f"t{i:03d}", turn["text"])
        wait_outbox(d, f"t{i:03d}")
    # The sleep-triggering turn: submit, then kill -9 mid-SLEEP.
    submit(d, "t075", turns[74]["text"])
    marker = d / "sleep104-SLEEPING"
    deadline = time.time() + 300.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("daemon died before the kill")
        if marker.exists():
            break
        time.sleep(0.02)
    saw_marker = marker.exists()
    if proc.poll() is None:
        os.kill(proc.pid, signal.SIGKILL)  # kill -9 during SLEEP
        proc.wait()
    try:
        proc._log.close()  # type: ignore[attr-defined]
    except (OSError, ValueError):
        pass
    # Restart in the same dir: boot must verify the chain.
    proc = spawn(d, 1)
    status = json.loads((d / "daemon_status.json").read_text(
        encoding="utf-8"))
    # The killed turn is reprocessed on boot (its input never moved to done):
    # with the episodes cleared mid-recipe it finds < 8 and stays absent.
    t075_reply = wait_outbox(d, "t075", timeout=900.0)
    replies = [{"n": 75, "text": turns[74]["text"],
                "reply": t075_reply.strip(), "verdict": None}]
    for i, turn in enumerate(turns[75:], 76):
        submit(d, f"t{i:03d}", turn["text"])
        reply = wait_outbox(d, f"t{i:03d}")
        replies.append({"n": i, "text": turn["text"],
                        "reply": reply.strip(),
                        "verdict": classify(reply, turn["expect"])})
    # 200 taught-fact asks through the mailbox (50 facts x4).
    ask_results = []
    items = sorted(truth.items())
    for rep4 in range(4):
        for j, ((name, rel), want) in enumerate(items):
            nm = f"ask{rep4}-{j:03d}"
            submit(d, nm, f"Who is {name}'s mother?")
            reply = wait_outbox(d, nm)
            ask_results.append(classify(reply, want))
    stop_daemon(proc, d)
    nb = C.Notebook(d / "notebook")
    good, dupes = taught_ok(nb, truth)
    word_path = d / "sleep104-word.json"
    word_ok: bool | None = None
    if word_path.exists():
        word_ok = check_routing(d)
    probes = [r for r in replies if r["n"] >= 76]  # t076..t080
    rep = {
        "seconds": round(time.time() - t0, 1),
        "saw_sleep_marker_before_kill": saw_marker,
        "boot_ok": status.get("boot_ok"),
        "torn_reported": status.get("torn_tail_found_and_repaired"),
        "word_file": ("valid" if word_ok else
                      "absent" if word_ok is None else "INVALID"),
        "probes": probes,
        "probes_correct": sum(1 for r in probes if r["verdict"] == "correct"),
        "probes_abstain": sum(1 for r in probes if r["verdict"] == "abstain"),
        "probes_wrong": sum(1 for r in probes if r["verdict"] == "wrong"),
        "taught_asks_correct": sum(1 for v in ask_results if v == "correct"),
        "taught_asks_wrong": sum(1 for v in ask_results if v == "wrong"),
        "taught_asks_total": len(ask_results),
        "taught_good": good, "taught_dupes": dupes,
        "sleep_overwrote_taught": sleep_overwrites(nb),
    }
    rep["pass"] = bool(
        rep["boot_ok"] and rep["word_file"] in ("valid", "absent")
        and rep["probes_wrong"] == 0
        and (rep["probes_correct"] == 5 or rep["probes_abstain"] == 5)
        and rep["taught_asks_correct"] == 200
        and rep["taught_asks_wrong"] == 0 and dupes == 0
        and rep["sleep_overwrote_taught"] == 0)
    # Z4b: a COMPLETED install also survives a restart. Copy the registered
    # seed-1 dir (installed + bridged), boot it, ask the 5 NEW-people probes
    # through the mailbox: 5/5 proves the persisted word serves after boot.
    rep["restore"] = None
    src = root / "seed1"
    if src.exists():
        rb = root / "z4-restore"
        if rb.exists():
            shutil.rmtree(rb)
        shutil.copytree(src, rb)
        proc2 = spawn(rb, 1)
        got = []
        for j, (kid, _, gran) in enumerate(TEST, 1):
            submit(rb, f"p{j:02d}", f"Who is {kid}'s maternal grandmother?")
            got.append(classify(wait_outbox(rb, f"p{j:02d}"), gran))
        stop_daemon(proc2, rb)
        rep["restore"] = {
            "correct": sum(1 for v in got if v == "correct"),
            "abstain": sum(1 for v in got if v == "abstain"),
            "wrong": sum(1 for v in got if v == "wrong"),
            "pass": got == ["correct"] * 5}
        rep["pass"] = bool(rep["pass"] and rep["restore"]["pass"])
    return rep


# ------------------------------------------------------------------------ main
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 104 registered wave")
    parser.add_argument("--root", default=str(ART / "runs"))
    parser.add_argument("--report", default=str(ART / "wave-report.json"))
    parser.add_argument("--seed", type=int, action="append", default=None)
    parser.add_argument("--only", action="append", default=None,
                        help="subset of: s1 s2 s3 z4 z5n4 z5n8")
    args = parser.parse_args(argv)
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    seeds = tuple(args.seed) if args.seed else (1, 2, 3)
    only = None
    if args.only:
        only = set()
        for chunk in args.only:
            only.update(c.strip() for c in chunk.split(",") if c.strip())

    def want(*names: str) -> bool:
        return only is None or any(n in only for n in names)

    t0 = time.time()
    out: dict = {"sleep_threshold": SLEEP_THRESHOLD, "seeds": {},
                 "z4": None, "z5": {}}
    transcripts: dict = {}
    for seed in seeds:
        if not want(f"s{seed}"):
            continue
        r = run_seed(seed, root)
        out["seeds"][str(seed)] = r["rep"]
        transcripts[str(seed)] = r["replies"]
        p = r["rep"]
        print(f"seed {seed}: sleep@{p['sleep_file']} "
              f"installed={int(p['installed'])} "
              f"episodes={p['episodes_at_install']} "
              f"sleep_s={p['sleep_seconds']} probes={p['probes_correct']}/5 "
              f"taught={p['taught_good']}/{p['taught_total']} "
              f"wrong_install={int(p['wrong_install'])} "
              f"{p['seconds']}s", flush=True)
    if want("z4"):
        out["z4"] = run_z4(root)
        z = out["z4"]
        print(f"Z4: marker={int(z['saw_sleep_marker_before_kill'])} "
              f"boot_ok={z['boot_ok']} word={z['word_file']} "
              f"probes={z['probes_correct']}/5 abst={z['probes_abstain']} "
              f"taught_asks={z['taught_asks_correct']}/200 "
              f"restore={z['restore']} "
              f"PASS={int(z['pass'])} {z['seconds']}s", flush=True)
    for noise, key in ((4, "noise4"), (8, "noise8")):
        if not want(f"z5n{noise}"):
            continue
        r = run_seed(1, root / "z5", noise=noise)
        out["z5"][key] = r["rep"]
        p = r["rep"]
        print(f"Z5 {key}: installed={int(p['installed'])} "
              f"probes={p['probes_correct']}/5 abst={p['probes_abstain']} "
              f"wrong={p['probes_wrong']} "
              f"wrong_install={int(p['wrong_install'])} "
              f"{p['seconds']}s", flush=True)
    out["wave_seconds"] = round(time.time() - t0, 1)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(out, indent=1, sort_keys=True),
                                 encoding="utf-8")
    if transcripts.get("1"):
        (Path(args.report).parent / "transcript-seed1.txt").write_text(
            "\n".join(f"[{r['n']:02d} {r['kind']}] YOU: {r['text']}\n"
                      f"[{r['n']:02d} {r['kind']}] DAEMON: {r['reply']}"
                      for r in transcripts["1"]) + "\n", encoding="utf-8")
    print(f"wave {out['wave_seconds']}s -> {args.report}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
