#!/usr/bin/env python3
"""Exp 129 shared mailbox drivers (owned by exp 129; sealed suites read-only).

Helpers shared by the exp-129 runners: daemon factories for loop129a/b,
mailbox run_case (same semantics as the loop117/121 marks harnesses:
inbox file -> process_file -> outbox reply, restart/tear_tail/kill9 ops),
and process_pending. No existing file is edited.
"""

from __future__ import annotations

import copy
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop129a_agent as L129a  # noqa: E402 (this experiment)
import fable_loop129b_agent as L129b  # noqa: E402 (this experiment)
import fable_redteam98_runner as R98  # noqa: E402 (sealed helpers, read-only)

ROOT = SCRIPTS.parent
ART129 = ROOT / "artifacts" / "fable-fix129-20260922"

PY129A = [sys.executable, "-B", str(SCRIPTS / "fable_loop129a_agent.py")]
PY129B = [sys.executable, "-B", str(SCRIPTS / "fable_loop129b_agent.py")]
SCRIPT129A = SCRIPTS / "fable_loop129a_agent.py"
SCRIPT129B = SCRIPTS / "fable_loop129b_agent.py"


def cfg129a(state_dir) -> dict:
    cfg = copy.deepcopy(L129a.DEFAULT_CONFIG129A)
    cfg["state_dir"] = str(state_dir)
    cfg["sleep_threshold"] = 10 ** 9
    return cfg


def cfg129b(state_dir) -> dict:
    cfg = copy.deepcopy(L129b.DEFAULT_CONFIG129B)
    cfg["state_dir"] = str(state_dir)
    cfg["sleep_threshold"] = 10 ** 9
    return cfg


def new_daemon129a(root: Path):
    return L129a.Loop129aDaemon(root, cfg={"sleep_threshold": 100000},
                                idle_seconds=3600.0)


def new_daemon129b(root: Path):
    return L129b.Loop129bDaemon(root, cfg={"sleep_threshold": 100000},
                                idle_seconds=3600.0)


def process_pending(daemon, root: Path, log: list) -> None:
    for path in sorted((root / "inbox").glob("*.txt")):
        before = R98.fact_count(daemon)
        try:
            daemon.process_file(path)
            writes = R98.fact_count(daemon) - before
            reply = (root / "outbox" / path.name).read_text(encoding="utf-8")
            statuses = [r.get("status", r.get("kind", "?"))
                        for r in daemon.loop.last_records]
        except Exception as exc:  # noqa: BLE001 -- observed, never raised
            reply = f"HARNESS-CAUGHT {type(exc).__name__}: {exc}"
            statuses = ["EXCEPTION"]
            writes = 0
            try:
                os.replace(path, root / "done" / path.name)
            except OSError:
                pass
        log.append({"file": path.name, "reply": reply, "statuses": statuses,
                    "fact_writes": writes})


def do_kill9_burst(root: Path, log: list, script: Path, factory) -> dict:
    out: dict = {"phase": "kill9"}
    cmd = [sys.executable, "-B", str(script),
           "--daemon", "--dir", str(root), "--idle-seconds", "3600"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    try:
        for _ in range(900):
            if (root / "daemon_status.json").exists():
                break
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        texts, gold = [], {}
        for i in range(30):
            tag = f"{i:02d}"
            texts.append((f"b_{len(texts):02d}.txt",
                          f"The capital of C{tag} is V{tag}"))
            if i == 10:
                texts.append((f"b_{len(texts):02d}.txt",
                              "The capital of C10 is W10"))
            gold[f"C{i:02d}"] = "W10" if i == 10 else f"V{i:02d}"
        for name, text in texts:
            (root / "inbox" / name).write_text(text, encoding="utf-8")
        time.sleep(0.5)
        try:
            os.kill(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=60)
        out["killed"] = True
        out["done_before_death"] = len(list((root / "done").glob("*.txt")))
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=60)
    try:
        daemon = factory(root)
        out["boot_ok"] = True
        out["boot_notes"] = list(daemon.loop.notes)
    except Exception as exc:  # noqa: BLE001
        out["boot_ok"] = False
        out["boot_error"] = f"{type(exc).__name__}: {exc}"
        out["gold"] = gold
        return out
    correct = wrong = abstained = 0
    detail = []
    others = set(gold.values())
    for subj, want in sorted(gold.items()):
        (root / "inbox" / f"q_{subj}.txt").write_text(
            f"Who is {subj}'s capital?", encoding="utf-8")
        process_pending(daemon, root, log)
        reply = log[-1]["reply"]
        bad = [v for v in others - {want} if v in reply]
        if want in reply and not bad:
            correct += 1
        elif bad:
            wrong += 1
        else:
            abstained += 1
        detail.append({"ask": subj, "want": want, "got": reply.strip()[:80],
                        "verdict": "correct" if (want in reply and not bad)
                        else ("WRONG" if bad else "abstain")})
    out.update({"gold": gold, "correct": correct, "wrong": wrong,
                "abstained": abstained, "detail": detail})
    log.append({"file": "KILL9-SUMMARY",
                "reply": f"correct={correct} wrong={wrong} abstained={abstained}",
                "statuses": [], "fact_writes": 0})
    return out


def run_case(case: dict, workroot: Path, factory, script: Path) -> dict:
    """Mailbox run of one multi-turn case (same ops as the 117/121 marks)."""
    root = Path(tempfile.mkdtemp(prefix=case["id"] + "_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    log: list = []
    info: dict = {"boot_ok_count": 0, "boot_refused": None,
                   "torn_repaired": False}
    try:
        daemon = factory(root)
    except Exception as exc:  # noqa: BLE001
        return {"id": case["id"], "group": case["group"], "root": str(root),
                "log": log, "info": info, "observed": f"boot failed: {exc}",
                "verdict": "UNCLEAR", "reason": "fresh daemon would not boot"}
    auto = 0
    batch: list[Path] = []

    def next_name(explicit=None):
        nonlocal auto
        if explicit:
            return explicit
        name = f"msg_{auto:02d}.txt"
        auto += 1
        return name

    def flush_batch():
        if batch:
            stamp = time.time()
            for p in batch:
                os.utime(p, (stamp, stamp))
            batch.clear()
        process_pending(daemon, root, log)

    for step in case["steps"]:
        op = step["op"]
        if op == "send":
            name = next_name(step.get("file"))
            p = root / "inbox" / name
            p.write_text(step["text"], encoding="utf-8")
            if step.get("same_second"):
                batch.append(p)
            else:
                flush_batch()
        elif op == "send_bytes":
            flush_batch()
            auto += 1
            (root / "inbox" / f"msg_{auto:02d}.txt").write_bytes(
                bytes.fromhex(step["data_hex"]))
            process_pending(daemon, root, log)
        elif op == "restart":
            flush_batch()
            try:
                daemon = factory(root)
                info["boot_ok_count"] += 1
                if any("repaired a torn notebook tail" in n
                       for n in daemon.loop.notes):
                    info["torn_repaired"] = True
                log.append({"file": "RESTART", "reply": "boot_ok",
                            "statuses": [], "fact_writes": 0,
                            "notes": list(daemon.loop.notes)})
            except Exception as exc:  # noqa: BLE001
                info["boot_refused"] = f"{type(exc).__name__}: {exc}"
                log.append({"file": "RESTART",
                            "reply": f"BOOT-REFUSED {type(exc).__name__}: {exc}",
                            "statuses": [], "fact_writes": 0})
                break
        elif op == "tear_tail":
            flush_batch()
            ev = root / "notebook" / "events.jsonl"
            lines = ev.read_text(encoding="utf-8").split("\n")
            if lines and lines[-1] == "":
                lines.pop()
            lines[-1] = lines[-1][: max(10, len(lines[-1]) * 4 // 10)]
            ev.write_text("\n".join(lines), encoding="utf-8")
            log.append({"file": "TEAR-TAIL", "reply": "last line truncated",
                        "statuses": [], "fact_writes": 0})
        elif op == "kill9_burst":
            flush_batch()
            info["kill9"] = do_kill9_burst(root, log, script, factory)
        else:
            raise ValueError(f"unknown op {op!r}")
    flush_batch()
    return {"id": case["id"], "group": case["group"], "root": str(root),
            "log": log, "info": info}
