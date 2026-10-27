#!/usr/bin/env python3
"""Experiment 206 — SLEEP SMOKE MARK for merges (harness addition; no agent change).

Problem (director-verified): scripts/fable_marks123_all.py forces
cfg["sleep_threshold"] = 100000 and its SLEEP suite always returns
skipped=True, pass=True, so no merge (138g/138h/138i) has ever exercised
live sleep. This script drives the exp-104/145 world (builders imported
read-only from scripts/fable_sleep104_drive.py) through a FRESH daemon of
a given agent + config, with sleep_threshold=75 (low enough that sleep
fires inside the last filler turn, exactly as in exp 104), in an isolated
scratch notebook dir. The agent script + config are read, never edited.

Per run it reports: sleeps logged, installed (maternal_grandmother in
sleep145-words.json), the 5 new-people probes after sleep (right / wrong /
abstain), one broken-chain probe (unknown person Q99: must abstain
honestly), taught facts overwritten by sleep (must be 0), seconds.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_sleepsmoke206.py \
    --agent scripts/fable_loop138i_agent.py \
    --config artifacts/fable-agent138i-20260922/loop138i-config.json \
    --root ART_DIR --label s1-138i
"""

from __future__ import annotations

import argparse
import copy
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
import fable_sleep104_drive as D104  # noqa: E402 (builders only, read-only)

WORD = "maternal_grandmother"
THRESHOLD = 75  # log full exactly at the last filler, as in exp 104
BROKEN_Q = "Who is Q99's maternal grandmother?"
BROKEN_EXPECT = "Q99zzz-never-a-name"  # never in a reply; abstain or wrong


def spawn(d: Path, agent_script: str, base_cfg: dict, seed: int,
          idle_seconds: float) -> subprocess.Popen:
    d.mkdir(parents=True, exist_ok=True)
    cfg = copy.deepcopy(base_cfg)
    cfg["state_dir"] = str(d)
    cfg["sleep_threshold"] = THRESHOLD
    for key in ("sleep145_seed", "sleep138_seed", "sleep131_seed",
                "sleep130_seed", "sleep115_seed", "sleep104_seed"):
        cfg[key] = seed
    cfg_path = d / "smoke206-config.json"
    cfg_path.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    for stale in ("STOP", "heartbeat.json", "daemon_status.json"):
        (d / stale).unlink(missing_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    log = open(d / "daemon.stdout.log", "w", encoding="utf-8")  # noqa: PTH123
    proc = subprocess.Popen(
        [sys.executable, "-B", agent_script, "--daemon", "--dir", str(d),
         "--config", str(cfg_path), "--idle-seconds", str(idle_seconds)],
        stdout=log, stderr=subprocess.STDOUT, env=env)
    proc._log = log  # type: ignore[attr-defined]
    deadline = time.time() + 300.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"smoke daemon exited early: {proc.poll()}")
        if (d / "heartbeat.json").exists() and (
                d / "daemon_status.json").exists():
            return proc
        time.sleep(0.05)
    proc.kill()
    raise RuntimeError("smoke daemon did not write heartbeat in time")


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
        path = d / "outbox" / name
        if path.exists():
            return path.read_text(encoding="utf-8")
        time.sleep(0.02)
    raise RuntimeError(f"no outbox reply for {name} within {timeout}s")


def stop_daemon(proc, d: Path, timeout: float = 60.0) -> None:
    (d / "STOP").write_text("stop\n", encoding="utf-8")
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    if proc.poll() is None:
        proc.kill()
        raise RuntimeError("daemon did not stop in time")
    try:
        proc._log.close()  # type: ignore[attr-defined]
    except (OSError, ValueError):
        pass


def read_log(d: Path) -> list[dict]:
    p = d / "daemon.log.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def word_state(d: Path) -> dict:
    for name in ("sleep145-words.json", "sleep130-words.json",
                 "sleep104-word.json"):
        p = d / name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                words = data.get("words", data)
                rec = words.get(WORD, {}) if isinstance(words, dict) else {}
                return {"file": name, "installed": WORD in (words or {}),
                        "episodes": rec.get("episodes"),
                        "oof_best": rec.get("oof_best"),
                        "refit_agreement": rec.get("refit_agreement"),
                        "grew_slot": rec.get("grew_slot", rec.get("grew"))}
            except (OSError, ValueError, AttributeError):
                return {"file": name, "installed": False, "error": "unreadable"}
    return {"file": None, "installed": False}


def run_smoke(agent_script: str, config_path: str, root: Path, label: str,
              seed: int = 1, idle_seconds: float = 30.0) -> dict:
    t0 = time.time()
    d = root / label
    if d.exists():
        shutil.rmtree(d)
    base_cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    proc = spawn(d, agent_script, base_cfg, seed, idle_seconds)
    turns, truth = D104.build_turns()
    replies: list[dict] = []
    for i, turn in enumerate(turns, 1):
        name = f"t{i:03d}"
        submit(d, name, turn["text"])
        reply = wait_outbox(d, name + ".txt",
                            timeout=900.0 if i == THRESHOLD else 300.0)
        replies.append({"n": i, "kind": turn["kind"], "text": turn["text"],
                        "reply": reply.strip(),
                        "verdict": D104.classify(reply, turn["expect"])
                        if turn["kind"] in ("episode", "probe") else None})
    submit(d, "b001", BROKEN_Q)
    broken_reply = wait_outbox(d, "b001.txt").strip()
    broken_verdict = D104.classify(broken_reply, BROKEN_EXPECT)
    stop_daemon(proc, d)
    log = read_log(d)
    sleeps = [e for e in log
              if e.get("event") == "sleep" or "sleep" in str(e.get("event", ""))]
    ws = word_state(d)
    nb = C.Notebook(d / "notebook")
    report_rows = [f for f in nb.facts.values()
                   if f.get("source") == "sleep-derived"]
    good, dupes = D104.taught_ok(nb, truth)
    probes = replies[-5:]
    rep = {
        "label": label, "agent": Path(agent_script).name,
        "config": Path(config_path).name, "seed": seed,
        "sleep_threshold": THRESHOLD,
        "seconds": round(time.time() - t0, 1),
        "sleeps_logged": len(sleeps),
        "installed": bool(ws.get("installed")),
        "word_file": ws.get("file"),
        "episodes_at_install": ws.get("episodes"),
        "oof_best": ws.get("oof_best"),
        "refit_agreement": ws.get("refit_agreement"),
        "report_rows_sleep_derived": len(report_rows),
        "probes": [{"text": r["text"], "reply": r["reply"],
                    "verdict": r["verdict"]} for r in probes],
        "probes_right": sum(1 for r in probes if r["verdict"] == "correct"),
        "probes_wrong": sum(1 for r in probes if r["verdict"] == "wrong"),
        "probes_abstain": sum(1 for r in probes if r["verdict"] == "abstain"),
        "broken_chain": {"question": BROKEN_Q, "reply": broken_reply,
                         "verdict": broken_verdict},
        "taught_good": good, "taught_total": len(truth),
        "taught_dupes": dupes,
        "sleep_overwrote_taught": D104.sleep_overwrites(nb),
    }
    return {"rep": rep, "replies": replies}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 206 sleep smoke")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    args = parser.parse_args(argv)
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    r = run_smoke(args.agent, args.config, root, args.label,
                  seed=args.seed, idle_seconds=args.idle_seconds)
    p = r["rep"]
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(p, indent=1, sort_keys=True),
                                 encoding="utf-8")
    print(f"{p['label']}: sleeps={p['sleeps_logged']} "
          f"installed={int(p['installed'])} episodes={p['episodes_at_install']} "
          f"probes={p['probes_right']}/5 wrong={p['probes_wrong']} "
          f"abst={p['probes_abstain']} broken={p['broken_chain']['verdict']} "
          f"taught={p['taught_good']}/{p['taught_total']} "
          f"ow={p['sleep_overwrote_taught']} {p['seconds']}s "
          f"-> {args.report}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
