from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from . import checkin as checkin_mod
from .config import Config, load
from .practice import sandbox
from .scheduler import FakePractice, Scheduler
from .state import State
from .workers import CommandWorker, FakeWorker


def build_scheduler(cfg: Config, fake: bool) -> Scheduler:
    if fake:
        return Scheduler(cfg, FakeWorker(hour_s=cfg.hour_s, delay_s=min(1.0, cfg.hour_s / 10)), FakePractice())
    worker = CommandWorker([sys.executable, "-m", "sleepmode.mlx_worker"], str(cfg.worker_dir),
                           grace_s=cfg.kill_grace_s, slack_s=cfg.budget_slack_s,
                           env={"PYTHONPATH": _pkg_parent()})
    return Scheduler(cfg, worker)


def _pkg_parent() -> str:
    parent = str(Path(__file__).resolve().parent.parent)
    old = os.environ.get("PYTHONPATH")
    return parent + (os.pathsep + old if old else "")


def keep_awake() -> None:
    """On macOS stop idle sleep while this process lives (caffeinate -ims -w pid: no idle, disk or system sleep on AC). No-op elsewhere."""
    if sys.platform == "darwin" and shutil.which("caffeinate"):
        subprocess.Popen(["caffeinate", "-ims", "-w", str(os.getpid())])


def cmd_start(cfg: Config, a) -> int:
    st = State(cfg)
    pid = st.sleeping_pid()
    if pid:
        print("Already sleeping (pid %d). Use `wake` first." % pid)
        return 1
    if st.assistant_running():
        print("The assistant is running (%s exists); sleeping would stop at once." % cfg.assistant_running)
        return 1
    st.clear_wake()
    if a.foreground:
        keep_awake()
        build_scheduler(cfg, a.fake).run()
        return 0
    log = cfg.path("sleepmode.log")
    cmd = [sys.executable, "-m", "sleepmode", "start", "--foreground"] + (["--fake"] if a.fake else [])
    env = dict(os.environ, PYTHONPATH=_pkg_parent())
    with open(str(log), "ab") as lf:
        p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             start_new_session=True, env=env)
    print("Sleeping (pid %d). Log: %s" % (p.pid, log))
    return 0


def cmd_wake(cfg: Config, a) -> int:
    st = State(cfg)
    if not st.sleeping_pid():
        print("Not sleeping.")
        st.clear_wake()
        return 0
    st.request_wake()
    end = time.time() + a.timeout
    while time.time() < end and cfg.sleeping_path.exists():
        time.sleep(0.2)
    if cfg.sleeping_path.exists():
        print("Still stopping after %d s; check %s" % (a.timeout, cfg.path("sleepmode.log")))
        return 1
    return cmd_summary(cfg, a)


def cmd_status(cfg: Config, a) -> int:
    st = State(cfg)
    s = st.read_status()
    pid = st.sleeping_pid()
    print("sleeping: %s" % ("yes (pid %d)" % pid if pid else "no"))
    for k, v in s.items():
        print("  %s: %s" % (k, v))
    return 0


def cmd_summary(cfg: Config, a) -> int:
    try:
        print(cfg.summary_path.read_text())
    except OSError:
        print("No summary yet.")
        return 1
    return 0


def cmd_checkin(cfg: Config, a) -> int:
    res = checkin_mod.run(cfg, State(cfg))
    flagged = {i.id: r for i, r in res["flagged"]}
    print("scanned: %s" % (res["counts"] or "nothing"))
    for k, v in res["errors"].items():
        print("  skipped %s: %s" % (k, v))
    for it in res["items"]:
        mark = ("NOTIFY (%s)" % flagged[it.id]) if it.id in flagged else "-"
        print("  [%s] %s | %s | %s" % (it.source, it.sender[:30], it.subject[:60], mark))
    print("new notifications: %d" % len(res["notified"]))
    return 0


def preflight(cfg: Config, scanners: Optional[list] = None) -> List[tuple]:
    """Run each enabled scanner once in the foreground (this is what triggers the macOS Automation prompts)
    and check the sandbox. -> [(check, ok, detail)]"""
    rows = []
    for sc in checkin_mod.default_scanners(cfg) if scanners is None else scanners:
        name = getattr(sc, "name", type(sc).__name__)
        try:
            rows.append((name, True, "%d item(s)" % len(sc.scan(cfg))))
        except PermissionError as e:
            rows.append((name, False, "not allowed: Privacy & Security > Automation (%s)" % str(e)[:80]))
        except Exception as e:  # noqa
            rows.append((name, False, str(e)[:100]))
    iso = sandbox.detect_isolation()
    r = sandbox.run_python("print(6 * 7)")
    rows.append(("sandbox", iso != "rlimits-only", "isolation: " + iso))
    rows.append(("python run", r.ok and r.stdout.strip() == "42", "ok" if r.ok else (r.stderr.strip()[-100:] or "failed")))
    return rows


def cmd_preflight(cfg: Config, a) -> int:
    rows = preflight(cfg)
    print("%-12s %-5s %s" % ("check", "", "detail"))
    for name, ok, detail in rows:
        print("%-12s %-5s %s" % (name, "OK" if ok else "FAIL", detail))
    return 0 if all(ok for _, ok, _ in rows) else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="sleepmode")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("start")
    p.add_argument("--fake", action="store_true", help="demo with a fake trainer")
    p.add_argument("--foreground", action="store_true")
    p = sub.add_parser("wake")
    p.add_argument("--timeout", type=float, default=60.0)
    for n in ("status", "summary", "checkin", "preflight"):
        sub.add_parser(n)
    a = ap.parse_args(argv)
    cfg = load()
    Path(cfg.home).mkdir(parents=True, exist_ok=True)
    return {"start": cmd_start, "wake": cmd_wake, "status": cmd_status, "summary": cmd_summary,
            "checkin": cmd_checkin, "preflight": cmd_preflight}[a.cmd](cfg, a)
