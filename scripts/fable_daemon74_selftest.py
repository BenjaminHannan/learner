"""Exp 74 selftest -- marks D1..D4, three seeds, every seed reported, never averaged.

  D1  teach 50 facts through the mailbox, stop, restart, ask 50 questions
      -> 50/50 correct and 0 wrong
  D2  kill -9 the daemon (subprocess.kill) mid-write during 200 rapid teaches,
      restart -> chain verifies OR the exact broken line is reported, and NO fact
      is lost or duplicated among the ones whose outbox reply was written
  D3  100 turns end-to-end < 60 s on Mac CPU
  D4  STOP file stops the process within 10 s

Each seed uses fresh daemon directories. Run:

  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_daemon74_selftest.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402

RUN = SCRIPTS / "fable_daemon74_run.py"
SEEDS = (1, 2, 3)
WAIT_S = 120.0


def spawn(d: Path, idle_seconds: float = 3600.0) -> subprocess.Popen:
    d.mkdir(parents=True, exist_ok=True)
    (d / "STOP").unlink(missing_ok=True)  # a prior graceful stop must not kill the reboot
    (d / "heartbeat.json").unlink(missing_ok=True)  # prove THIS boot came up
    (d / "daemon_status.json").unlink(missing_ok=True)
    log = open(d / "daemon.stdout.log", "w", encoding="utf-8")  # noqa: PTH123
    proc = subprocess.Popen([sys.executable, "-B", str(RUN), "--dir", str(d),
                             "--idle-seconds", str(idle_seconds)],
                            stdout=log, stderr=subprocess.STDOUT)
    proc._log = log  # type: ignore[attr-defined]
    deadline = time.time() + WAIT_S
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"daemon exited early with code {proc.poll()}")
        if (d / "heartbeat.json").exists() and (d / "daemon_status.json").exists():
            return proc
        time.sleep(0.05)
    proc.kill()
    raise RuntimeError("daemon did not write heartbeat/status in time")


def submit(d: Path, name: str, text: str) -> None:
    tmp = d / "inbox" / f"{name}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text if text.endswith("\n") else text + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, d / "inbox" / f"{name}.txt")


def wait_outbox(d: Path, name: str, timeout: float = WAIT_S) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        path = d / "outbox" / f"{name}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        time.sleep(0.02)
    raise RuntimeError(f"no outbox reply for {name} within {timeout}s")


def stop_daemon(proc: subprocess.Popen, d: Path, timeout: float = 10.0) -> float:
    t0 = time.time()
    (d / "STOP").write_text("stop\n", encoding="utf-8")
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    dt = time.time() - t0
    if proc.poll() is None:
        proc.kill()
        raise RuntimeError(f"daemon did not stop within {timeout}s")
    proc._log.close()  # type: ignore[attr-defined]
    return dt


def fact_name(prefix: str, seed: int, i: int) -> str:
    return f"{prefix}S{seed}F{i:03d}"


def fact_value(prefix: str, seed: int, i: int) -> str:
    return f"{prefix}TownS{seed}N{i:03d}"


def check_answer(reply: str, want: str, all_values: list[str]) -> str:
    if want in reply:
        return "correct"
    for other in all_values:
        if other != want and other in reply:
            return "wrong"
    return "unanswered"


# ------------------------------------------------------------------ marks
def mark_d1(seed: int) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"daemon74_d1_s{seed}_") as tmp:
        d = Path(tmp) / "daemon"
        proc = spawn(d)
        names = [fact_name("D1", seed, i) for i in range(50)]
        values = [fact_value("D1", seed, i) for i in range(50)]
        for i, (name, value) in enumerate(zip(names, values)):
            submit(d, f"teach-{i:03d}", f"{name}'s city is {value}.")
        for i in range(50):
            wait_outbox(d, f"teach-{i:03d}")
        stop_daemon(proc, d)  # stop...
        proc = spawn(d)  # ...restart, notebook must survive
        for i, name in enumerate(names):
            submit(d, f"ask-{i:03d}", f"What is {name}'s city?")
        correct = wrong = unanswered = 0
        for i, value in enumerate(values):
            verdict = check_answer(wait_outbox(d, f"ask-{i:03d}"), value, values)
            correct += verdict == "correct"
            wrong += verdict == "wrong"
            unanswered += verdict == "unanswered"
        stop_daemon(proc, d)
        passed = correct == 50 and wrong == 0
        return {"mark": "D1", "seed": seed, "pass": passed,
                "correct": correct, "wrong": wrong, "unanswered": unanswered}


def mark_d2(seed: int) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"daemon74_d2_s{seed}_") as tmp:
        d = Path(tmp) / "daemon"
        proc = spawn(d)
        names = [fact_name("D2", seed, i) for i in range(200)]
        values = [fact_value("D2", seed, i) for i in range(200)]
        for i, (name, value) in enumerate(zip(names, values)):
            submit(d, f"teach-{i:03d}", f"{name}'s city is {value}.")
        deadline = time.time() + WAIT_S  # wait until it is mid-write, then kill -9
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError("daemon died before the kill")
            if len(list((d / "outbox").glob("teach-*.txt"))) >= 5:
                break
            time.sleep(0.005)
        replied_before_kill = sorted(p.name for p in (d / "outbox").glob("teach-*.txt"))
        proc.kill()  # kill -9 equivalent: no cleanup, torn tails possible
        proc.wait()
        proc._log.close()  # type: ignore[attr-defined]
        proc = spawn(d)  # restart: chain must verify or the broken line is reported
        status = json.loads((d / "daemon_status.json").read_text(encoding="utf-8"))
        for i in range(200):  # drain whatever is left in the inbox
            wait_outbox(d, f"teach-{i:03d}")
        # Re-ask everything whose reply was written; count lost / wrong.
        for i, name in enumerate(names):
            submit(d, f"ask-{i:03d}", f"What is {name}'s city?")
        correct = wrong = unanswered = 0
        for i, value in enumerate(values):
            verdict = check_answer(wait_outbox(d, f"ask-{i:03d}"), value, values)
            correct += verdict == "correct"
            wrong += verdict == "wrong"
            unanswered += verdict == "unanswered"
        stop_daemon(proc, d)
        # No duplicates: exactly one taught FACT event per (name, value), chain clean.
        nb = C.Notebook(d / "notebook")
        dupes = 0
        for name, value in zip(names, values):
            found = nb.resolve(name)
            assert found.status == C.OK, f"{name} missing after restart"
            rows = [r for r in nb.current(found.detail["entity_id"], "city")
                    if r["source"] == "taught"]
            same = [r for r in nb.facts.values()
                    if r.get("subject") == found.detail["entity_id"]
                    and r.get("relation") == "city" and r.get("source") == "taught"
                    and r.get("value") == {"literal": value}]
            if len(rows) != 1 or len(same) != 1:
                dupes += 1
        chain_ok = (not nb.torn_tail) and status.get("boot_ok") is True
        torn_reported = status.get("torn_tail_found_and_repaired") is True or (
            d / "notebook" / "torn-tail.txt").exists()
        passed = (chain_ok or torn_reported) and correct == 200 and wrong == 0 and dupes == 0
        return {"mark": "D2", "seed": seed, "pass": passed, "correct": correct,
                "wrong": wrong, "unanswered": unanswered, "dupes": dupes,
                "replied_before_kill": len(replied_before_kill),
                "chain_ok": chain_ok, "torn_reported": torn_reported,
                "verified_hash": status.get("verified_chain_hash", "")[:16]}


def mark_d3(seed: int) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"daemon74_d3_s{seed}_") as tmp:
        d = Path(tmp) / "daemon"
        proc = spawn(d)
        names = [fact_name("D3", seed, i) for i in range(50)]
        values = [fact_value("D3", seed, i) for i in range(50)]
        t0 = time.time()
        for i, (name, value) in enumerate(zip(names, values)):
            submit(d, f"teach-{i:03d}", f"{name}'s city is {value}.")
        for i in range(50):
            wait_outbox(d, f"teach-{i:03d}")
        for i, name in enumerate(names):
            submit(d, f"ask-{i:03d}", f"What is {name}'s city?")
        correct = 0
        for i, value in enumerate(values):
            if value in wait_outbox(d, f"ask-{i:03d}"):
                correct += 1
        dt = time.time() - t0
        stop_daemon(proc, d)
        passed = dt < 60.0
        return {"mark": "D3", "seed": seed, "pass": passed,
                "turns": 100, "seconds": round(dt, 2), "correct": correct}


def mark_d4(seed: int) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"daemon74_d4_s{seed}_") as tmp:
        d = Path(tmp) / "daemon"
        proc = spawn(d)
        dt = stop_daemon(proc, d, timeout=10.0)
        passed = dt <= 10.0 and proc.poll() == 0
        return {"mark": "D4", "seed": seed, "pass": passed,
                "stop_seconds": round(dt, 2), "exit_code": proc.poll()}


def main() -> int:
    print("seed | D1 (teach50/stop/restart/ask50) | D2 (kill-9/restart) | D3 (100 turns) | D4 (STOP)")
    all_ok = True
    for seed in SEEDS:
        row = {"seed": seed}
        try:
            row["D1"] = mark_d1(seed)
            row["D2"] = mark_d2(seed)
            row["D3"] = mark_d3(seed)
            row["D4"] = mark_d4(seed)
        except Exception as exc:  # a crash is a failed mark, not a crashed script
            print(f"seed {seed}: EXCEPTION {type(exc).__name__}: {exc}")
            return 1
        ok = all(row[m]["pass"] for m in ("D1", "D2", "D3", "D4"))
        all_ok &= ok
        d1, d2, d3, d4 = row["D1"], row["D2"], row["D3"], row["D4"]
        print(f"seed {seed}: "
              f"D1 {'PASS' if d1['pass'] else 'FAIL'} correct={d1['correct']}/50 wrong={d1['wrong']} | "
              f"D2 {'PASS' if d2['pass'] else 'FAIL'} correct={d2['correct']}/200 wrong={d2['wrong']} "
              f"dupes={d2['dupes']} replied_before_kill={d2['replied_before_kill']} "
              f"chain_ok={d2['chain_ok']} torn_reported={d2['torn_reported']} | "
              f"D3 {'PASS' if d3['pass'] else 'FAIL'} {d3['seconds']}s correct={d3['correct']}/50 | "
              f"D4 {'PASS' if d4['pass'] else 'FAIL'} {d4['stop_seconds']}s exit={d4['exit_code']}")
    print("SELFTEST", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
