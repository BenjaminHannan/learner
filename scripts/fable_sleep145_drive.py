#!/usr/bin/env python3
"""Experiment 145 driver -- registered wave M1..M5 (additive only).

Reuses sealed drivers BY IMPORT (never edited):
  fable_sleep130_drive (M1: G1 seeds 1-2 via 115 builders verbatim; G3 L1-L3)
  fable_sleep116_drive (M2/M4: full redteam wave; t4 helpers)
  fable_sleep104_drive (M2: z104 seeds 1-3 + Z4 + Z5)
plus daemon-class swaps so every daemon booted is Sleep145Daemon:
  D104.PY / D130.PY -> scripts/fable_sleep145_agent.py
  D104.spawn wraps the original with sleep145_seed/sleep130_seed cfg keys
  D104.check_routing reads sleep145-words.json (multi-word 130 format)
  D104.run_z4 replaced by an identical copy watching sleep145-SLEEPING and
      sleep145-words.json (the original's literals cannot be patched)
  S130.WORD_FILE130 redirected to sleep145-words.json for the G1/G3
      routing audit (process-local redirect; no file edited)

Sub-runs (each under artifacts/fable-sleep145-20260922/):
  m1g1s1 / m1g1s2 : 130 G1 on seeds 1 / 2  -> wave-g1s1.json / wave-g1s2.json
  m1g3            : 130 G3 (L1/L2/L3 x seeds 1-3) -> wave-g3.json
  e116            : full 116 redteam wave -> wave-report-116.json (raw; the
                    reused checker reads bare probe names, so F/sources read
                    empty -- rescored read-only with the .txt fix, as in 131)
  z104            : full 104 wave -> wave-report-104.json
  t4              : 131 teach-after-sleep verbatim (seed 31) -> t4.json
  t6              : NEW grown-word teach-after-sleep (seed 41) -> t6.json

Usage (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_sleep145_drive.py --only e116
  (--only selects a comma-separated subset; default: all)

Nothing outside this file and artifacts/fable-sleep145-20260922/ is written.
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
import fable_sleep104_drive as D104  # noqa: E402 (read-only, never edited)
import fable_sleep115_drive as D115  # noqa: E402 (read-only, never edited)
import fable_sleep116_drive as D116  # noqa: E402 (read-only, never edited)
import fable_sleep130_agent as S130  # noqa: E402 (read-only, never edited)
import fable_sleep130_drive as D130  # noqa: E402 (read-only, never edited)
import fable_sleep145_agent as S145  # noqa: E402 (this exp's agent)

ART145 = SCRIPTS.parent / "artifacts" / "fable-sleep145-20260922"

# THE daemon class swap: every spawn boots Sleep145Daemon.
D104.PY = [sys.executable, "-B", str(SCRIPTS / "fable_sleep145_agent.py")]
D130.PY = list(D104.PY)
# G1/G3 routing audit reads the 145 serving file (redirect, process-local).
S130.WORD_FILE130 = S145.WORD_FILE145


# ------------------------------------------------- spawn with 145 seed keys
def spawn145(d: Path, seed: int, idle_seconds: float = 3600.0,
             threshold: int = D104.SLEEP_THRESHOLD):
    d.mkdir(parents=True, exist_ok=True)
    cfg = {"state_dir": str(d), "sleep_threshold": threshold,
           "sleep104_seed": seed, "sleep130_seed": seed,
           "sleep145_seed": seed}
    cfg_path = d / "sleep145-config.json"
    cfg_path.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    for stale in ("STOP", "heartbeat.json", "daemon_status.json"):
        (d / stale).unlink(missing_ok=True)
    log = open(d / "daemon.stdout.log", "w", encoding="utf-8")  # noqa: PTH123
    proc = subprocess.Popen(
        D104.PY + ["--daemon", "--dir", str(d), "--config", str(cfg_path),
                   "--idle-seconds", str(idle_seconds)],
        stdout=log, stderr=subprocess.STDOUT)
    proc._log = log  # type: ignore[attr-defined]
    deadline = time.time() + 180.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"sleep145 daemon exited early: {proc.poll()}")
        if (d / "heartbeat.json").exists() and (
                d / "daemon_status.json").exists():
            return proc
        time.sleep(0.05)
    proc.kill()
    raise RuntimeError("sleep145 daemon did not write heartbeat in time")


D104.spawn = spawn145  # type: ignore[method-assign]


# --------------------------------------- routing audit on the 145 word file
def check_routing145(d: Path) -> bool:
    """Installed maternal_grandmother logits: skill stages mother, mother."""
    try:
        data = json.loads((d / S145.WORD_FILE145).read_text(encoding="utf-8"))
        logits = data["words"]["maternal_grandmother"]["logits"]
        arg = [max(range(9), key=lambda i: r[i]) for r in logits]
        return [a for a in arg if a != 0] == [1, 1]
    except (OSError, ValueError, KeyError, TypeError):
        return False


D104.check_routing = check_routing145  # type: ignore[method-assign]


# ------------------------------------------------- z4 with 145 marker/file
def run_z4_145(root: Path) -> dict:
    """Byte-for-byte D104.run_z4 except the SLEEPING marker and word file."""
    t0 = time.time()
    d = root / "z4-kill"
    if d.exists():
        shutil.rmtree(d)
    proc = D104.spawn(d, 1)
    turns, truth = D104.build_turns()
    for i, turn in enumerate(turns[:74], 1):
        D104.submit(d, f"t{i:03d}", turn["text"])
        D104.wait_outbox(d, f"t{i:03d}")
    D104.submit(d, "t075", turns[74]["text"])
    marker = d / S145.MARKER145
    deadline = time.time() + 300.0
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
    proc = D104.spawn(d, 1)
    status = json.loads((d / "daemon_status.json").read_text(
        encoding="utf-8"))
    t075_reply = D104.wait_outbox(d, "t075", timeout=900.0)
    replies = [{"n": 75, "text": turns[74]["text"],
                "reply": t075_reply.strip(), "verdict": None}]
    for i, turn in enumerate(turns[75:], 76):
        D104.submit(d, f"t{i:03d}", turn["text"])
        reply = D104.wait_outbox(d, f"t{i:03d}")
        replies.append({"n": i, "text": turn["text"],
                        "reply": reply.strip(),
                        "verdict": D104.classify(reply, turn["expect"])})
    ask_results = []
    items = sorted(truth.items())
    for rep4 in range(4):
        for j, ((name, rel), want) in enumerate(items):
            nm = f"ask{rep4}-{j:03d}"
            D104.submit(d, nm, f"Who is {name}'s mother?")
            reply = D104.wait_outbox(d, nm)
            ask_results.append(D104.classify(reply, want))
    D104.stop_daemon(proc, d)
    nb = C.Notebook(d / "notebook")
    good, dupes = D104.taught_ok(nb, truth)
    word_path = d / S145.WORD_FILE145
    word_ok: bool | None = None
    if word_path.exists():
        word_ok = check_routing145(d)
    probes = [r for r in replies if r["n"] >= 76]
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
        "sleep_overwrote_taught": D104.sleep_overwrites(nb),
    }
    rep["pass"] = bool(
        rep["boot_ok"] and rep["word_file"] in ("valid", "absent")
        and rep["probes_wrong"] == 0
        and (rep["probes_correct"] == 5 or rep["probes_abstain"] == 5)
        and rep["taught_asks_correct"] == 200
        and rep["taught_asks_wrong"] == 0 and dupes == 0
        and rep["sleep_overwrote_taught"] == 0)
    rep["restore"] = None
    src = root / "seed1"
    if src.exists():
        rb = root / "z4-restore"
        if rb.exists():
            shutil.rmtree(rb)
        shutil.copytree(src, rb)
        proc2 = D104.spawn(rb, 1)
        got = []
        for j, (kid, _, gran) in enumerate(D104.TEST, 1):
            D104.submit(rb, f"p{j:02d}",
                        f"Who is {kid}'s maternal grandmother?")
            got.append(D104.classify(D104.wait_outbox(rb, f"p{j:02d}"), gran))
        D104.stop_daemon(proc2, rb)
        rep["restore"] = {
            "correct": sum(1 for v in got if v == "correct"),
            "abstain": sum(1 for v in got if v == "abstain"),
            "wrong": sum(1 for v in got if v == "wrong"),
            "pass": got == ["correct"] * 5}
        rep["pass"] = bool(rep["pass"] and rep["restore"]["pass"])
    return rep


D104.run_z4 = run_z4_145  # type: ignore[method-assign]


# ------------------------------------------------------------------ M1: G1
def run_m1g1(seed: int) -> int:
    return D130.main(["--root", str(ART145 / f"m1-g1s{seed}"),
                      "--report", str(ART145 / f"wave-g1s{seed}.json"),
                      "--seed", str(seed), "--only", "g1"])


# ------------------------------------------------------------------ M1: G3
def run_m1g3() -> int:
    return D130.main(["--root", str(ART145 / "m1-g3"),
                      "--report", str(ART145 / "wave-g3.json"),
                      "--only", "g3l1,g3l2,g3l3"])


# -------------------------------------------------------------- M2/M4: e116
def run_e116() -> int:
    return D116.main(["--root", str(ART145 / "runs-116"),
                      "--report", str(ART145 / "wave-report-116.json")])


# ---------------------------------------------------------------- M2: z104
def run_z104() -> int:
    return D104.main(["--root", str(ART145 / "runs-104"),
                      "--report", str(ART145 / "wave-report-104.json")])


# ------------------------------------------------------------------ M2: t4
def run_t4() -> int:
    root = ART145 / "runs-t4"
    root.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out: dict = {}
    # 131's b_teachafter verbatim: 8 clean K chains + 4 T mother chains,
    # 8 K asks, 2 fillers.
    pre = []
    for i in range(1, 9):
        k, m, g = f"K{i:02d}", f"M{i:02d}", f"G{i:02d}"
        pre.append(f"{k}'s mother is {m}.")
        pre.append(f"{m}'s mother is {g}.")
    for i in range(1, 5):
        t, n, h = f"T{i:02d}", f"N{i:02d}", f"H{i:02d}"
        pre.append(f"{t}'s mother is {n}.")
        pre.append(f"{n}'s mother is {h}.")
    for i in range(1, 9):
        pre.append(f"Who is K{i:02d}'s maternal grandmother?")
    pre.extend(["Hi, how are you?", "Thanks, that helps."])
    r = D116.drive_run(root, "teachafter", 31, pre)
    d, proc, replies = r["dir"], r["proc"], r["replies"]
    teach = D116.ask(d, replies, "s01",
                     "T01's maternal grandmother is Z01.")
    p_taught = D116.ask(d, replies, "p01",
                        "Who is T01's maternal grandmother?")
    p_ctrl = D116.ask(d, replies, "p02",
                      "Who is T02's maternal grandmother?")
    si = D116.sleep_info(d)
    log = si["log"]
    D116.finish(d, proc)
    nb = C.Notebook(d / "notebook")
    rec_t = D116.get_record(log, "p01")
    rec_c = D116.get_record(log, "p02")
    src_t = rec_t.get("fields", {}).get("source", "")
    src_c = rec_c.get("fields", {}).get("source", "")
    stored = D116.taught_pair_ok(nb, "T01", "maternal_grandmother", "Z01")
    ow = D104.sleep_overwrites(nb)
    out.update({
        "installed": si["installed"], "attempted": si["attempted"],
        "episodes": si["episodes"], "oof": si["oof"], "agree": si["agree"],
        "teach_reply": teach.strip()[:120], "stored_taught": stored,
        "probe_taught": p_taught.strip()[:120], "probe_taught_source": src_t,
        "probe_control": p_ctrl.strip()[:120],
        "probe_control_source": src_c, "overwrite": ow,
    })
    ta_ok = bool(si["installed"] and stored and D116.has(p_taught, "Z01")
                 and not D116.has(p_taught, "H01") and src_t == "taught"
                 and ow == 0)
    tb_ok = bool(si["installed"] and D116.has(p_ctrl, "H02")
                 and src_c == "sleep-derived")
    out["TA_taught_wins"] = "PASS" if ta_ok else "FAIL"
    out["TB_control_derived"] = "PASS" if tb_ok else "FAIL"
    out["T4"] = "PASS" if (ta_ok and tb_ok) else "FAIL"
    out["wave_seconds"] = round(time.time() - t0, 1)
    (ART145 / "t4.json").write_text(json.dumps(out, indent=1, sort_keys=True),
                                    encoding="utf-8")
    print(f"TA {out['TA_taught_wins']} -- taught={p_taught.strip()[:80]} "
          f"src={src_t} stored={int(stored)} ow={ow}", flush=True)
    print(f"TB {out['TB_control_derived']} -- control={p_ctrl.strip()[:80]} "
          f"src={src_c}", flush=True)
    print(f"T4 {out['T4']} {out['wave_seconds']}s -> {ART145 / 't4.json'}",
          flush=True)
    return 0 if out["T4"] == "PASS" else 1


# ------------------------------------------------------------------ M3: t6
GROWN_T6 = "boss_of_father"  # WORDS130 index 3, chain father+boss [2,4]
GROWN_T6_SURF = "boss of father"


def b_grownafter() -> tuple[list[str], dict]:
    """20 father/boss train chains + 5 disjoint test chains + episodes."""
    pre, truth = [], {}
    for i in range(1, 21):
        k, b, c = f"J{i:02d}", f"B{i:02d}", f"C{i:02d}"
        pre.append(f"{k}'s father is {b}.")
        truth[(k, "father")] = b
        pre.append(f"{b}'s boss is {c}.")
        truth[(b, "boss")] = c
    for k in range(1, 6):
        y, b, c = f"Y{k:02d}", f"BK{k:02d}", f"CK{k:02d}"
        pre.append(f"{y}'s father is {b}.")
        truth[(y, "father")] = b
        pre.append(f"{b}'s boss is {c}.")
        truth[(b, "boss")] = c
    for i in range(1, 21):
        pre.append(f"Who is J{i:02d}'s {GROWN_T6_SURF}?")
    pre.extend(["Hi, how are you?", "Thanks, that helps."])
    return pre, {"truth": truth}


def sleep_info_t6(d: Path) -> dict:
    log = D104.read_log(d)
    sleeps = [e for e in log if e.get("event") == "sleep"]
    first = sleeps[0] if sleeps else {}
    recipe = first.get("recipe", {}) if isinstance(first, dict) else {}
    words = recipe.get("words", [])
    wrec = next((w for w in words if w.get("word") == GROWN_T6), {})
    return {"log": log, "sleeps": sleeps, "first": first, "recipe": recipe,
            "installed": bool(wrec.get("installed")),
            "attempted": bool(recipe.get("attempted")),
            "episodes": sum(w.get("episodes", 0) for w in words),
            "oof": wrec.get("oof_best"), "agree": wrec.get("refit_agreement"),
            "grew": bool(wrec.get("grew_slot")),
            "frozen": wrec.get("frozen_ok")}


def rec_txt(log: list[dict], fname: str) -> dict:
    """Corrected record lookup (mailbox filenames carry .txt)."""
    for e in log:
        if e.get("event") == "turn" and e.get("file") == fname:
            recs = e.get("records", [])
            return recs[0] if recs else {}
    return {}


def run_t6() -> int:
    root = ART145 / "runs-t6"
    root.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    pre, info = b_grownafter()
    r = D116.drive_run(root, "grownafter", 41, pre)
    d, proc, replies = r["dir"], r["proc"], r["replies"]
    si = sleep_info_t6(d)
    # AFTER the grown sleep installs: teach a differing value for Y01.
    teach = D116.ask(d, replies, "s01", "Y01's boss of father is Z01.")
    p_taught = D116.ask(d, replies, "p01",
                        "Who is Y01's boss of father?")
    p_ctrl = D116.ask(d, replies, "p02",
                      "Who is Y02's boss of father?")
    log = D104.read_log(d)
    D116.finish(d, proc)
    nb = C.Notebook(d / "notebook")
    rec_t = rec_txt(log, "p01.txt")
    rec_c = rec_txt(log, "p02.txt")
    src_t = rec_t.get("fields", {}).get("source", "")
    src_c = rec_c.get("fields", {}).get("source", "")
    stored = D116.taught_pair_ok(nb, "Y01", GROWN_T6, "Z01")
    ow = D104.sleep_overwrites(nb)
    good, dupes = D104.taught_ok(nb, info["truth"])
    out = {
        "installed": si["installed"], "attempted": si["attempted"],
        "episodes": si["episodes"], "oof": si["oof"], "agree": si["agree"],
        "grew_slot": si["grew"], "frozen_ok": si["frozen"],
        "teach_reply": teach.strip()[:120], "stored_taught": stored,
        "probe_taught": p_taught.strip()[:120],
        "probe_taught_source": src_t,
        "probe_taught_trail": rec_t.get("fields", {}).get("trail", []),
        "probe_control": p_ctrl.strip()[:120],
        "probe_control_source": src_c,
        "probe_control_trail": rec_c.get("fields", {}).get("trail", []),
        "overwrite": ow, "taught_good": good,
        "taught_total": len(info["truth"]), "taught_dupes": dupes,
    }
    ta_ok = bool(si["installed"] and si["grew"] and stored
                 and D116.has(p_taught, "Z01")
                 and not D116.has(p_taught, "CK01")
                 and src_t == "taught" and ow == 0)
    tb_ok = bool(si["installed"] and D116.has(p_ctrl, "CK02")
                 and src_c == "sleep-derived")
    out["TA_taught_wins"] = "PASS" if ta_ok else "FAIL"
    out["TB_control_derived"] = "PASS" if tb_ok else "FAIL"
    out["T6"] = "PASS" if (ta_ok and tb_ok) else "FAIL"
    out["wave_seconds"] = round(time.time() - t0, 1)
    (ART145 / "t6.json").write_text(json.dumps(out, indent=1, sort_keys=True),
                                    encoding="utf-8")
    print(f"T6-TA {out['TA_taught_wins']} -- taught={p_taught.strip()[:80]} "
          f"src={src_t} stored={int(stored)} grew={int(si['grew'])} "
          f"ow={ow}", flush=True)
    print(f"T6-TB {out['TB_control_derived']} -- control={p_ctrl.strip()[:80]}"
          f" src={src_c}", flush=True)
    print(f"T6 {out['T6']} {out['wave_seconds']}s -> {ART145 / 't6.json'}",
          flush=True)
    return 0 if out["T6"] == "PASS" else 1


RUNNERS = {
    "m1g1s1": lambda: run_m1g1(1),
    "m1g1s2": lambda: run_m1g1(2),
    "m1g3": run_m1g3,
    "e116": run_e116,
    "z104": run_z104,
    "t4": run_t4,
    "t6": run_t6,
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 145 registered wave")
    ap.add_argument("--only", default="m1g1s1,m1g1s2,m1g3,e116,z104,t4,t6")
    args = ap.parse_args(argv)
    want = [c.strip() for c in args.only.split(",") if c.strip()]
    rc = 0
    t0 = time.time()
    for name in want:
        print(f"== 145 {name} ==", flush=True)
        rc |= RUNNERS[name]()
    print(f"145 [{','.join(want)}] {round(time.time() - t0, 1)}s",
          flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
