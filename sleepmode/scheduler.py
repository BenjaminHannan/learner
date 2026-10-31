"""Main sleep loop. See DESIGN.md. Mac-only bits (memory pressure) are module functions tests can patch."""
from __future__ import annotations

import os
import math
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from . import checkin as checkin_mod
from .config import Config
from .plateau import Plateau
from .state import State, now_iso
from .workers import SleepWorker

PracticeFn = Callable[[float], Optional[dict]]


def wake_deadline_ms(value: str) -> Optional[int]:
    """Parse an optional absolute Unix deadline, ignoring malformed values."""
    try:
        deadline = float(value)
        # Keep the value exact when Desktop reads it as a JavaScript number.
        return int(deadline) if math.isfinite(deadline) and 1 <= deadline <= 9007199254740991 else None
    except (TypeError, ValueError, OverflowError):
        return None


def memory_pressure() -> int:
    """macOS kern.memorystatus_vm_pressure_level (1 normal, 2 warn, 4 critical); 1 elsewhere or on error."""
    if sys.platform != "darwin":
        return 1
    try:
        out = subprocess.run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"],
                             capture_output=True, text=True, timeout=5).stdout
        return int(out.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return 1


class FakePractice:
    """Demo practice: pass rate climbs a little each round, writes nothing."""

    def __init__(self):
        self.n = 0

    def __call__(self, budget_s: float) -> Optional[dict]:
        self.n += 1
        return {"kind": "spreadsheet", "n": 8, "pass1": min(0.95, 0.4 + 0.1 * self.n), "pass_any": 0.9,
                "files": [], "elapsed_s": 0.0}


def default_practice_fn(cfg: Config, state: State) -> PracticeFn:
    """Built lazily from sleepmode.practice. Returns None for 'nothing practicable' or when the package is missing."""
    def fn(budget_s: float) -> Optional[dict]:
        try:
            from sleepmode.practice import habits, loop
            from sleepmode.practice.model import ChatModel
        except ImportError:
            return None
        if not cfg.practice_model_url:
            return None
        if habits.pick_kind(habits.analyze(str(cfg.diary_dir)), cfg.practice_min_share) is None:
            return None  # checked before starting a model server
        server = None
        try:
            if cfg.practice_server_cmd:
                server = subprocess.Popen(cfg.practice_server_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                _wait_for(cfg.practice_model_url, 180)
            model = ChatModel(cfg.practice_model_url, cfg.practice_model)
            res = loop.make_practice_fn(str(cfg.home), str(cfg.diary_dir), model, n_tasks=cfg.practice_tasks,
                                        research_web=cfg.research_web, min_share=cfg.practice_min_share,
                                        tools=cfg.practice_tools,
                                        heldout_families=tuple(cfg.heldout_families))(budget_s)
            if res is None:
                return None
            res = dict(res)
            res["files"] = [p for p in (res.get("sft_path"), res.get("pairs_path")) if p and Path(p).exists()]
            return res
        finally:
            if server is not None:
                server.terminate()
                try:
                    server.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    server.kill()
    return fn


def _wait_for(url: str, timeout_s: float) -> None:
    end = time.time() + timeout_s
    while time.time() < end:
        try:
            urllib.request.urlopen(url.rstrip("/") + "/v1/models", timeout=3).read()
            return
        except Exception:
            time.sleep(2)


class Scheduler:
    def __init__(self, cfg: Config, worker: SleepWorker, practice_fn: Optional[PracticeFn] = None,
                 scanners: Optional[list] = None, clock: Callable[[], float] = time.time,
                 sleep: Callable[[float], None] = time.sleep, checkin_sender=None):
        self.cfg, self.worker = cfg, worker
        self.state = State(cfg)
        self.practice_fn = practice_fn or default_practice_fn(cfg, self.state)
        self.scanners, self.clock, self.sleep = scanners, clock, sleep
        self.wake_at_ms = wake_deadline_ms(os.environ.get("SLEEPMODE_WAKE_AT_MS", ""))
        self.checkin_sender = checkin_sender
        self.plateau = Plateau(cfg.plateau_window, cfg.plateau_min_gain_per_hour, cfg.plateau_patience,
                               cfg.min_sleep_hours, cfg.plateau_noise, cfg.plateau_general_drop)
        self.mode = "sleep"
        self.practice_turn = True
        self.idle_until = 0.0
        self.last_checkin = -1e18
        self.blocked_scanners: set = set()    # scanners that need macOS permission: not retried this run
        self._signal = ""
        self.stop_reason = ""
        self.practice_files: List[str] = self.state.practice_files()
        # summary counters
        self.t_start = 0.0
        self.chunks = 0
        self.hours_slept = 0.0
        self.quizzes: List[float] = []
        self.switches: List[str] = []
        self.rounds: List[dict] = []
        self.checkins = 0
        self.notified: List[str] = []
        self.pauses = 0
        self.errors: List[str] = []

    # ---- stop conditions ----
    def should_stop(self) -> bool:
        if self.stop_reason:
            return True
        if self._signal:
            self.stop_reason = "signal " + self._signal
        elif self.state.wake_requested():
            self.stop_reason = "WAKE file"
        elif self.state.assistant_running():
            self.stop_reason = "assistant started"
        elif self.wake_at_ms is not None and self.clock() >= self.wake_at_ms / 1000:
            self.stop_reason = "wake deadline"
        return bool(self.stop_reason)

    def pause_reason(self) -> str:
        if self.state.paused_by_file():
            return "PAUSE_OTHERS"
        if memory_pressure() >= 2:
            return "memory pressure"
        return ""

    def _chunk_stop(self) -> bool:
        return self.should_stop() or bool(self.pause_reason())

    def _on_signal(self, signum, frame) -> None:
        self._signal = signal.Signals(signum).name

    # ---- loop ----
    def run(self) -> None:
        self.start()
        old = {}
        if threading.current_thread() is threading.main_thread():
            for s in (signal.SIGTERM, signal.SIGINT):
                old[s] = signal.signal(s, self._on_signal)
        try:
            errors = 0
            while not self.should_stop():
                try:
                    self.tick()
                    errors = 0
                except Exception as e:  # a crashed worker or practice round must not end a multi-day sleep
                    errors += 1
                    self.err("tick", e)
                    if errors >= self.cfg.max_errors:
                        errors = 0
                        self.idle_until = self.clock() + self.cfg.idle_hours * self.cfg.hour_s
                        self.state.event("idle", reason="%d errors in a row" % self.cfg.max_errors,
                                         hours=self.cfg.idle_hours)
                    self.wait_until(self.clock() + self.cfg.hour_s / 4)
        except Exception as e:  # keep the summary honest even on a bug
            self.err("loop", e)
            self.stop_reason = self.stop_reason or "error: %r" % e
        finally:
            for s, h in old.items():
                signal.signal(s, h)
            self.finish()

    def err(self, where: str, e: Exception) -> None:
        self.errors.append("%s: %r" % (where, e))
        self.state.event("error", where=where, error=repr(e))

    def start(self) -> None:
        other = self.state.sleeping_pid()
        if other and other != os.getpid():
            raise RuntimeError("already sleeping (pid %d)" % other)
        self.state.clear_wake()
        self.state.mark_sleeping()
        self.t_start = self.clock()
        self.state.event("start", pid=os.getpid(), hour_s=self.cfg.hour_s)
        self.status("sleep")

    def status(self, state_name: str, **kw) -> None:
        d = dict(mode=self.mode)
        d.update(kw)
        self.state.set_status(
            state=state_name, pid=os.getpid(), wake_at_ms=self.wake_at_ms, since=self.state.status.get("since") or now_iso(),
            hours_slept=round(self.hours_slept, 4), last_quiz=self.quizzes[-1] if self.quizzes else None,
            chunks=self.chunks, practice_rounds=len(self.rounds),
            last_pass1=self.rounds[-1].get("pass1") if self.rounds else None,
            last_checkin=self.state.status.get("last_checkin"), **d)

    def tick(self) -> None:
        hour_start = self.clock()
        if hour_start - self.last_checkin >= self.cfg.hour_s:
            self.do_checkin()
        budget = max(self.cfg.hour_s - min(self.cfg.checkin_reserve_s, 0.1 * self.cfg.hour_s),
                     0.1 * self.cfg.hour_s)
        why = self.pause_reason()
        if self.should_stop():
            return
        if why:
            self.pauses += 1
            self.state.event("paused", reason=why)
            self.status("paused", pause_reason=why)
        elif self.clock() < self.idle_until:
            self.status("idle")
        elif self.mode == "sleep":
            self.sleep_chunk(budget)
        else:
            self.practice_hour(budget)
        self.wait_until(hour_start + self.cfg.hour_s)

    def wait_until(self, t: float) -> None:
        while not self.should_stop():
            left = t - self.clock()
            if left <= 0:
                return
            self.sleep(min(self.cfg.poll_s, left))

    def do_checkin(self) -> None:
        self.last_checkin = self.clock()
        kw = {"blocked": self.blocked_scanners}
        if self.checkin_sender is not None:
            kw["sender"] = self.checkin_sender
        try:
            res = checkin_mod.run(self.cfg, self.state, self.scanners, **kw)
            self.checkins += 1
            self.notified += [i.subject for i in res["notified"]]
        except Exception as e:
            self.err("checkin", e)
        self.state.status["last_checkin"] = now_iso()
        self.status(self.state.status.get("state", "sleep"))

    def sleep_chunk(self, budget: float) -> None:
        if self.wake_at_ms is not None and self.clock() + budget + 300 >= self.wake_at_ms / 1000:
            self.stop_reason = "insufficient time before wake deadline"
            return
        self.status("sleeping")
        r = self.worker.run_chunk(budget, list(self.practice_files), self._chunk_stop)
        self.chunks += 1
        self.hours_slept += r.elapsed_s / 3600.0
        self.state.event("chunk_done", quiz=r.quiz, elapsed_s=round(r.elapsed_s, 2), steps=r.steps,
                         interrupted=r.interrupted, info=r.info)
        if r.interrupted:
            return
        # Failed trainers use the same bounded retry/idle path as raised exceptions.
        # A deliberate stop or an expired chunk budget is not a worker failure.
        if (r.info or {}).get("error") and not (r.info or {}).get("budget_exceeded"):
            raise RuntimeError("sleep worker: %s" % r.info["error"])
        if r.quiz is not None:
            self.quizzes.append(r.quiz)
        self.plateau.add(r.quiz, r.elapsed_s / self.cfg.hour_s, (r.info or {}).get("general"))
        if self.mode == "sleep" and self.plateau.flat():
            self.mode = "practice"
            self.practice_turn = True
            why = self.plateau.reason()
            self.switches.append("sleep -> practice: " + why)
            self.state.event("switch", to="practice", reason=why)
        self.status("sleeping")

    def practice_hour(self, budget: float) -> None:
        if not self.practice_turn:
            self.practice_turn = True
            self.sleep_chunk(budget)          # consolidate on the new practice data
            return
        self.status("practicing")
        try:
            res = self.practice_fn(budget)
        except Exception as e:
            self.err("practice", e)
            res = None
        if res is None:
            self.mode = "sleep"
            self.idle_until = self.clock() + self.cfg.idle_hours * self.cfg.hour_s
            self.plateau.reset()
            self.state.event("idle", reason="nothing practicable", hours=self.cfg.idle_hours)
            self.status("idle")
            return
        self.rounds.append(res)
        new = [f for f in res.get("files", []) if f not in self.practice_files]
        self.practice_files += new
        if new or res.get("sft_n", 0) or res.get("pairs_n", 0):
            self.plateau.reset()      # fresh material: sleep may pay off again
        self.practice_turn = False
        self.state.event("practice_round", result={k: v for k, v in res.items() if k != "files"}, new_files=len(new))
        self.status("practicing")

    def finish(self) -> None:
        reason = self.stop_reason or "stopped"
        try:
            self.write_summary(reason)
        finally:
            self.state.event("wake", reason=reason)
            self.status("awake", mode="awake")
            self.state.clear_sleeping()
            self.state.clear_wake()

    def write_summary(self, reason: str) -> None:
        dur_h = (self.clock() - self.t_start) / 3600.0
        q = self.quizzes
        lines = ["# Sleep summary", "",
                 "- Woke up: %s (%s)" % (now_iso(), reason),
                 "- Slept for %.2f h of wall time; training time %.2f h in %d chunk(s)" % (dur_h, self.hours_slept, self.chunks),
                 "- Quiz score: " + ("%.2f -> %.2f (%d checks)" % (q[0], q[-1], len(q)) if q else "no score recorded"),
                 "- Practice rounds: %d" % len(self.rounds)]
        if self.rounds:
            p = [r.get("pass1") for r in self.rounds if r.get("pass1") is not None]
            if p:
                lines.append("- First-try pass rate: " + " -> ".join("%.0f%%" % (100 * x) for x in p[:1] + p[-1:]))
        lines += ["- Hourly check-ins: %d; pauses: %d" % (self.checkins, self.pauses)]
        for s in self.switches:
            lines.append("- Switch: " + s)
        if self.notified:
            lines += ["", "## Things that needed you"] + ["- " + s for s in self.notified]
        if self.errors:
            lines += ["", "## Errors"] + ["- " + e for e in self.errors[-5:]]
        from .state import atomic_write
        atomic_write(self.cfg.summary_path, "\n".join(lines) + "\n")
