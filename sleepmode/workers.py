from __future__ import annotations

import json
import math
import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence


@dataclass
class ChunkResult:
    quiz: Optional[float]
    elapsed_s: float
    steps: int = 0
    interrupted: bool = False
    info: dict = field(default_factory=dict)


class SleepWorker:
    def run_chunk(self, budget_s: float, practice_files: Sequence[str],
                  should_stop: Callable[[], bool]) -> ChunkResult:
        raise NotImplementedError


def default_curve(h: float) -> float:
    return 50 + 30 * (1 - math.exp(-h / 1.5))


class FakeWorker(SleepWorker):
    """Quiz follows a diminishing-returns curve over virtual hours; each chunk counts budget_s/hour_s hours."""

    def __init__(self, curve: Callable[[float], float] = default_curve, hour_s: float = 3600.0,
                 delay_s: float = 0.01):
        self.curve, self.hour_s, self.delay_s = curve, hour_s, delay_s
        self.hours = 0.0
        self.calls: List[dict] = []

    def run_chunk(self, budget_s, practice_files, should_stop):
        self.calls.append({"budget_s": budget_s, "practice_files": list(practice_files)})
        end = time.time() + self.delay_s
        while time.time() < end:
            if should_stop():
                return ChunkResult(None, 0.0, 0, True)
            time.sleep(min(0.005, self.delay_s))
        self.hours += budget_s / self.hour_s
        return ChunkResult(self.curve(self.hours), budget_s, 100, False, {"hours": self.hours})


class CommandWorker(SleepWorker):
    """Runs an external trainer. Contract: env SLEEPMODE_BUDGET_S, SLEEPMODE_OUT (json to write),
    SLEEPMODE_PRACTICE (os.pathsep-joined files), SLEEPMODE_WORKDIR. Output: {"quiz": float|null, "steps": int, ...}."""

    def __init__(self, cmd: Sequence[str], workdir: str, grace_s: float = 30.0, slack_s: float = 120.0,
                 poll_s: float = 0.05, env: Optional[Dict[str, str]] = None):
        self.cmd, self.workdir = list(cmd), str(workdir)
        self.grace_s, self.slack_s, self.poll_s = grace_s, slack_s, poll_s
        self.env = env or {}

    def _terminate(self, p: subprocess.Popen) -> bool:
        """SIGTERM, wait grace_s, then SIGKILL. True if we had to kill."""
        if p.poll() is not None:
            return False
        try:
            p.send_signal(signal.SIGTERM)
        except OSError:
            return False
        try:
            p.wait(timeout=self.grace_s)
            return False
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            return True

    def run_chunk(self, budget_s, practice_files, should_stop):
        wd = Path(self.workdir)
        wd.mkdir(parents=True, exist_ok=True)
        out = wd / "chunk_out.json"
        if out.exists():
            out.unlink()
        env = dict(os.environ)
        env.update(self.env)
        env.update({"SLEEPMODE_BUDGET_S": str(int(budget_s)), "SLEEPMODE_OUT": str(out),
                    "SLEEPMODE_PRACTICE": os.pathsep.join(practice_files), "SLEEPMODE_WORKDIR": str(wd)})
        t0 = time.time()
        info: dict = {}
        interrupted = False
        with open(str(wd / "worker.log"), "ab") as log:
            p = subprocess.Popen(self.cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
            while p.poll() is None:
                if should_stop():
                    interrupted = True
                    info["killed"] = self._terminate(p)
                    break
                if time.time() - t0 > budget_s + self.slack_s:
                    info["budget_exceeded"] = True
                    info["killed"] = self._terminate(p)
                    break
                time.sleep(self.poll_s)
        elapsed = time.time() - t0
        info["returncode"] = p.returncode
        data: dict = {}
        try:
            data = json.loads(out.read_text())
        except (OSError, ValueError):
            if p.returncode == 0 and not interrupted:
                info["error"] = "no output json"
        if p.returncode not in (0, None) and not interrupted and "budget_exceeded" not in info:
            info["error"] = "exit %s" % p.returncode
        quiz = data.pop("quiz", None)
        steps = int(data.pop("steps", 0) or 0)
        interrupted = interrupted or bool(data.pop("interrupted", False))
        info.update(data)
        return ChunkResult(None if quiz is None else float(quiz), elapsed, steps, interrupted, info)
