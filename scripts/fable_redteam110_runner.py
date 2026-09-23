#!/usr/bin/env python3
"""Experiment 110 -- RED TEAM round 2 harness driving the loop102 agent.

Public interface only: each case gets a fresh dir under the exp-110 artifact
dir; a REAL loop102 daemon subprocess serves inbox/*.txt in sorted name
order exactly like Daemon.run() does; replies are read from outbox/*.txt.
We never call loop.turn() or touch the notebook except to COUNT FACT events
for the zero-write checks. Ops: send | send_bytes | vanish | burst200.
Run: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \
  --python 3.12 --with torch --with numpy python -B \
  scripts/fable_redteam110_runner.py --export   # before seal
  scripts/fable_redteam110_runner.py --run      # registered run
"""

from __future__ import annotations

import argparse
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

import fable_redteam110_cases as RC  # noqa: E402 (our own cases file)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-redteam110-20260921"
CONFIG = ROOT / "artifacts" / "fable-loop102-20260921" / "loop102-config.json"
ABSTAIN_BITS = ["don't know", "which one", "didn't understand",
                "didn't catch", "another way", "only handle one-word",
                "1 to 3", "wasn't waiting", "left it as it was",
                "not someone i can look up", "could not save"]
BOOT_TIMEOUT_S = 240.0
FILE_TIMEOUT_S = 120.0
BURST_TIMEOUT_S = 900.0
POLL_S = 0.05


def is_abstain(reply: str) -> bool:
    return any(bit in reply.lower() for bit in ABSTAIN_BITS)


def fact_count(root: Path) -> int:
    ev = root / "notebook" / "events.jsonl"
    if not ev.exists():
        return 0
    n = 0
    try:
        with open(ev, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    if json.loads(line).get("kind") == "FACT":
                        n += 1
                except ValueError:
                    continue
    except OSError:
        pass
    return n


def last_statuses(root: Path, name: str) -> list:
    log = root / "daemon.log.jsonl"
    if not log.exists():
        return []
    out: list = []
    try:
        with open(log, encoding="utf-8") as handle:
            for line in handle:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("event") == "turn" and rec.get("file") == name:
                    out = [r.get("status", r.get("kind", "?"))
                           for r in rec.get("records", [])]
    except OSError:
        pass
    return out


def daemon_cmd(root: Path) -> list[str]:
    return ["uv", "run", "--offline", "--no-project", "--python", "3.12",
            "--with", "torch", "--with", "numpy", "python", "-B",
            str(SCRIPTS / "fable_loop102_agent.py"),
            "--daemon", "--dir", str(root), "--config", str(CONFIG),
            "--idle-seconds", "3600"]


def boot_daemon(root: Path):
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    proc = subprocess.Popen(daemon_cmd(root), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, env=env)
    deadline = time.time() + BOOT_TIMEOUT_S
    while time.time() < deadline:
        if proc.poll() is not None:
            return proc, "daemon exited during boot"
        if (root / "daemon_status.json").exists():
            return proc, ""
        time.sleep(POLL_S)
    return proc, "boot timeout"


def stop_daemon(proc, root: Path) -> None:
    try:
        (root / "STOP").write_text("stop\n", encoding="utf-8")
    except OSError:
        pass
    deadline = time.time() + 30.0
    while time.time() < deadline and proc.poll() is None:
        time.sleep(POLL_S)
    if proc.poll() is None:
        try:
            proc.kill()
        except OSError:
            pass
        proc.wait(timeout=60)


def wait_done(root: Path, name: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if (root / "done" / name).exists() and (root / "outbox" / name).exists():
            return True
        time.sleep(POLL_S)
    return False


class Driver:
    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "inbox").mkdir(parents=True, exist_ok=True)
        self.proc, err = boot_daemon(root)
        if err:
            raise RuntimeError(err)
        self.log: list = []
        self.auto = 0
        self.info: dict = {"ghost": None}

    def close(self) -> None:
        try:
            stop_daemon(self.proc, self.root)
        except OSError:
            pass

    def dead(self) -> bool:
        return self.proc.poll() is not None

    def one_file(self, name: str, timeout: float = FILE_TIMEOUT_S) -> dict:
        before = fact_count(self.root)
        if not wait_done(self.root, name, timeout):
            return {"harness_error": True,
                    "reason": f"no reply for {name} (daemon alive={not self.dead()})"}
        try:
            reply = (self.root / "outbox" / name).read_text(encoding="utf-8")
        except OSError as exc:
            return {"harness_error": True, "reason": f"outbox unreadable: {exc}"}
        writes = fact_count(self.root) - before
        entry = {"file": name, "reply": reply,
                 "statuses": last_statuses(self.root, name),
                 "fact_writes": writes}
        self.log.append(entry)
        return entry

    def send(self, text: str, name: str | None = None,
             timeout: float = FILE_TIMEOUT_S) -> dict:
        if name is None:
            name = f"msg_{self.auto:02d}.txt"
            self.auto += 1
        (self.root / "inbox" / name).write_text(text, encoding="utf-8")
        return self.one_file(name, timeout)

    def send_bytes(self, data_hex: str) -> dict:
        name = f"msg_{self.auto:02d}.txt"
        self.auto += 1
        (self.root / "inbox" / name).write_bytes(bytes.fromhex(data_hex))
        return self.one_file(name)

    def vanish(self, text: str) -> dict:
        # Deterministic delete-mid-read: stop the daemon, plant + delete the
        # file while nothing can read it, reboot, prove it was never served.
        stop_daemon(self.proc, self.root)
        ghost = f"ghost_{self.auto:02d}.txt"
        self.auto += 1
        (self.root / "STOP").unlink(missing_ok=True)
        (self.root / "inbox" / ghost).write_text(text, encoding="utf-8")
        try:
            (self.root / "inbox" / ghost).unlink()
        except OSError:
            pass
        self.proc, err = boot_daemon(self.root)
        if err:
            return {"harness_error": True, "reason": f"reboot failed: {err}"}
        self.info["ghost"] = ghost
        return {"vanished": ghost}

    def burst200(self) -> dict:
        for i in range(100):
            (self.root / "inbox" / f"b_{i:03d}.txt").write_text(
                f"The capital of C{i:02d} is V{i:02d}", encoding="utf-8")
        for i in range(100):
            (self.root / "inbox" / f"q_{i:03d}.txt").write_text(
                f"Who is C{i:02d}'s capital?", encoding="utf-8")
        before = fact_count(self.root)
        deadline = time.time() + BURST_TIMEOUT_S
        while time.time() < deadline:
            if self.dead():
                return {"harness_error": False, "daemon_died": True,
                        "reason": "daemon died mid-burst"}
            try:
                if len(list((self.root / "done").glob("*.txt"))) >= 200:
                    break
            except OSError:
                pass
            time.sleep(POLL_S)
        else:
            return {"harness_error": True,
                    "reason": "burst200 did not finish in time"}
        for k, i in ((100, 0), (150, 50), (199, 99)):
            try:
                reply = (self.root / "outbox" / f"q_{i:03d}.txt").read_text(
                    encoding="utf-8")
            except OSError as exc:
                return {"harness_error": True,
                        "reason": f"burst reply unreadable: {exc}"}
            self.log.append({"file": f"q_{i:03d}.txt", "reply": reply,
                             "statuses": [], "fact_writes": -1})
        # Pad the log so checked turn indices line up: 100 teaches + asks.
        full = []
        for i in range(100):
            try:
                r = (self.root / "outbox" / f"b_{i:03d}.txt").read_text(
                    encoding="utf-8")
            except OSError:
                r = "HARNESS-MISSING"
            full.append({"file": f"b_{i:03d}.txt", "reply": r, "statuses": [],
                         "fact_writes": -1})
        for i in range(100):
            try:
                r = (self.root / "outbox" / f"q_{i:03d}.txt").read_text(
                    encoding="utf-8")
            except OSError:
                r = "HARNESS-MISSING"
            full.append({"file": f"q_{i:03d}.txt", "reply": r, "statuses": [],
                         "fact_writes": -1})
        self.log = full
        self.info["burst_writes"] = fact_count(self.root) - before
        return {"burst_ok": True}


def run_case(case: dict, workroot: Path) -> dict:
    root = Path(tempfile.mkdtemp(prefix=case["id"] + "_", dir=str(workroot)))
    try:
        drv = Driver(root)
    except RuntimeError as exc:
        return {"id": case["id"], "group": case["group"], "root": str(root),
                "log": [], "info": {},
                "harness_error": True, "reason": f"boot failed: {exc}"}
    result: dict = {"id": case["id"], "group": case["group"],
                    "root": str(root), "log": [], "info": drv.info}
    try:
        for step in case["steps"]:
            op = step["op"]
            if drv.dead():
                result.update({"daemon_died": True,
                               "reason": "daemon died mid-case"})
                break
            if op == "send":
                out = drv.send(step["text"], step.get("file"))
            elif op == "send_bytes":
                out = drv.send_bytes(step["data_hex"])
            elif op == "vanish":
                out = drv.vanish(step["text"])
                continue
            elif op == "burst200":
                out = drv.burst200()
                if out.get("daemon_died"):
                    result.update(out)
                    break
                if out.get("harness_error"):
                    result.update(out)
                    break
                continue
            else:
                result.update({"harness_error": True,
                               "reason": f"unknown op {op!r}"})
                break
            if out.get("harness_error"):
                result.update(out)
                break
            if out.get("reply", "").startswith("HARNESS-MISSING"):
                result.update({"harness_error": True,
                               "reason": "burst reply missing"})
                break
    finally:
        result["log"] = drv.log
        result["info"] = drv.info
        drv.close()
    return result


def judge(case: dict, res: dict) -> dict:
    if res.get("harness_error"):
        return {"verdict": "HARNESS-ERROR",
                "reason": res.get("reason", "harness failure")}
    if res.get("daemon_died"):
        return {"verdict": "BUG", "severity": "high",
                "reason": res.get("reason", "daemon died mid-case")}
    exp = case.get("expect", {})
    fails: list[str] = []
    replies = [e["reply"] for e in res["log"]]
    for chk in exp.get("checks", []):
        i = chk["turn"]
        if i >= len(replies):
            fails.append(f"turn {i} missing from transcript")
            continue
        for sub in chk.get("contains", []):
            if sub not in replies[i]:
                fails.append(f"turn {i} lacks {sub!r} (got {replies[i][:120]!r})")
        for sub in chk.get("absent", []):
            if sub in replies[i]:
                fails.append(f"turn {i} leaks {sub!r}")
    for i in exp.get("abstain_on", []):
        if i >= len(replies):
            fails.append(f"turn {i} missing from transcript")
        elif not is_abstain(replies[i]):
            fails.append(f"turn {i} should abstain (got {replies[i][:120]!r})")
    blob = "\n".join(replies)
    for sub in exp.get("absent_everywhere", []):
        if sub in blob:
            fails.append(f"{sub!r} appears somewhere in the transcript")
    for i in exp.get("zero_fact_writes_on", []):
        if i < len(res["log"]) and res["log"][i]["fact_writes"] != 0:
            fails.append(f"turn {i} wrote {res['log'][i]['fact_writes']} FACT events")
    if exp.get("no_exception") and not (res["log"] and True):
        fails.append("empty transcript")
    if exp.get("vanished"):
        ghost = (res.get("info") or {}).get("ghost", "")
        root = Path(res["root"])
        for sub in ("outbox", "done"):
            if ghost and (root / sub / ghost).exists():
                fails.append(f"deleted file {ghost} was served from {sub}")
    if exp.get("all_done"):
        root = Path(res["root"])
        try:
            n = len(list((root / "done").glob("*.txt")))
        except OSError:
            n = -1
        if n != exp["all_done"]:
            fails.append(f"only {n} files in done/, want {exp['all_done']}")
    if fails:
        return {"verdict": "BUG", "severity": case["severity_if_fail"],
                "reason": "; ".join(fails)}
    if not replies:
        return {"verdict": "HARNESS-ERROR", "reason": "empty transcript"}
    return {"verdict": "OK", "reason": "all sealed checks held"}


REPRO_HEAD = """import os, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "fable-redteam110-20260921"
CFG = ROOT / "artifacts" / "fable-loop102-20260921" / "loop102-config.json"
root = Path(tempfile.mkdtemp())
env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
proc = subprocess.Popen(
    ["uv", "run", "--offline", "--no-project", "--python", "3.12",
     "--with", "torch", "--with", "numpy", "python", "-B",
     str(ROOT / "scripts" / "fable_loop102_agent.py"),
     "--daemon", "--dir", str(root), "--config", str(CFG),
     "--idle-seconds", "3600"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
for _ in range(2400):
    if (root / "daemon_status.json").exists() or proc.poll() is not None:
        break
    time.sleep(0.05)
def say(text, name):
    (root / "inbox" / name).write_text(text)
    for _ in range(2400):
        if (root / "done" / name).exists():
            break
        time.sleep(0.05)
    print(name, "->", (root / "outbox" / name).read_text().strip()[:150])
"""


def make_repro(case: dict, res: dict) -> str:
    lines = [REPRO_HEAD]
    n = 0
    for step in case["steps"]:
        if step["op"] == "send":
            lines.append(f"say({step['text']!r}, 'm{n}.txt')")
            n += 1
        elif step["op"] == "send_bytes":
            lines.append(f"(root/'inbox'/'m{n}.txt').write_bytes(bytes.fromhex({step['data_hex']!r}))")
            lines.append(f"say((root/'inbox'/'m{n}.txt').read_text(errors='replace'), 'm{n}.txt')")
            n += 1
        elif step["op"] == "vanish":
            lines.append(f"# vanish step (delete-mid-read): {step['text']!r}")
        elif step["op"] == "burst200":
            lines.append("# burst200: 100 teaches (The capital of Cxx is Vxx) + 100 asks")
    exp = case.get("expect", {})
    tail = []
    for chk in exp.get("checks", []):
        for sub in chk.get("contains", []):
            tail.append(f"turn {chk['turn']} must contain {sub!r}")
    lines.append(f"# EXPECTED (sealed pre-run): {'; '.join(tail) or exp}")
    lines.append(f"# OBSERVED: {res.get('verdict')} -- {res.get('reason','')[:200]}")
    lines.append("(root/'STOP').write_text('stop\\n'); proc.wait(timeout=60)")
    return "\n".join(lines) + "\n"


def expand_markers(text: str) -> str:
    if text == "BIG_X_1MB":
        return "x" * 10**6
    if text == "BIG_WS_150KB":
        return " \n" * 75000
    return text


def cmd_export(_args) -> int:
    ART.mkdir(parents=True, exist_ok=True)
    payload = []
    for c in RC.CASES:
        steps = []
        for s in c["steps"]:
            s = dict(s)
            if "text" in s:
                s["text"] = expand_markers(s["text"])
            steps.append(s)
        payload.append({"id": c["id"], "group": c["group"],
                        "severity_if_fail": c["severity_if_fail"],
                        "note": c["note"], "steps": steps,
                        "expect": c["expect"]})
    (ART / "fable_redteam110_cases.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"exported {len(payload)} cases -> {ART / 'fable_redteam110_cases.json'}")
    return 0


def cmd_run(_args) -> int:
    t0 = time.time()
    workroot = ART / "tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    reprodir = ART / "repro"
    reprodir.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ART / "fable_redteam110_cases.json").read_text(
        encoding="utf-8"))
    by_id = {c["id"]: c for c in RC.CASES}
    results = []
    for case in cases:
        res = run_case(case, workroot)
        verdict = judge(case, res)
        res.update(verdict)
        if verdict["verdict"] in ("BUG", "HARNESS-ERROR"):
            rp = reprodir / f"fable_redteam110_repro_{case['id']}.py"
            rp.write_text(make_repro(by_id[case["id"]], res),
                          encoding="utf-8")
            res["reproducer"] = str(rp.relative_to(ROOT))
        results.append(res)
        print(f"{case['id']:>3} {verdict['verdict']:13} "
              f"{verdict.get('severity',''):8} {verdict['reason'][:100]}",
              flush=True)
    ok = sum(1 for r in results if r["verdict"] == "OK")
    bugs = [r for r in results if r["verdict"] == "BUG"]
    herr = [r for r in results if r["verdict"] == "HARNESS-ERROR"]
    sev: dict[str, int] = {}
    for r in bugs:
        sev[r.get("severity", "?")] = sev.get(r.get("severity", "?"), 0) + 1
    fam: dict[str, dict] = {}
    for r in results:
        g = r["group"]
        fam.setdefault(g, {"OK": 0, "BUG": 0, "HARNESS-ERROR": 0})
        fam[g][r["verdict"]] += 1
    summary = {"cases": len(results), "OK": ok, "BUG": len(bugs),
               "by_severity": sev, "HARNESS-ERROR": len(herr),
               "by_family": fam,
               "bug_ids": [r["id"] for r in bugs],
               "harness_error_ids": [r["id"] for r in herr],
               "seconds": round(time.time() - t0, 1)}
    (ART / "fable_redteam110_results.json").write_text(
        json.dumps({"summary": summary, "cases": results}, indent=1,
                   ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 110 red-team harness")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args(argv)
    if args.export:
        return cmd_export(args)
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
