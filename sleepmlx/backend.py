"""The model interface the recipe talks to, plus the time / safety guards.

Backend (implemented by model.MLXBackend; tests use a fake):
    encode(text) -> list[int]                       tokenizer ids (no special tokens added)
    stop_id -> int                                   id appended to training targets (end of turn)
    generate(prompts, max_tokens, temp=0.0, adapter=True, stops=()) -> list[str]   one batch; adapter=False = base model; stops: strings that end a reply early (best effort)
    train_begin(total_steps, lr) / train_step(batch, replay, step) -> dict(ce, kl)   batch/replay: [(ids, loss_start)]
    save_adapter(new_dir) / load_adapter(dir_or_None)    immutable destination; None = a fresh (zero) adapter; missing non-None is an error
    downscale(factor, thresh, seed) -> dict          SHY step on the LoRA
    bench() -> (t_step_s, t_gen_s)                   seconds for a reference train step and one generation batch
    gen_batch -> int                                 prompts per generate() call
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Callable, List, Optional, Sequence, Tuple

Example = Tuple[List[int], int]  # (token ids, loss starts at this index)


class Backend:
    gen_batch = 8
    stop_id = 0

    def encode(self, text: str) -> List[int]: raise NotImplementedError
    def generate(self, prompts: Sequence[str], max_tokens: int, temp: float = 0.0, adapter: bool = True, stops: Sequence[str] = ()) -> List[str]: raise NotImplementedError
    def train_begin(self, total_steps: int, lr: float) -> None: raise NotImplementedError
    def train_step(self, batch: Sequence[Example], replay: Sequence[Example], step: int) -> dict: raise NotImplementedError
    def save_adapter(self, path) -> None: raise NotImplementedError
    def load_adapter(self, path) -> None: raise NotImplementedError
    def downscale(self, factor: float, thresh: float, seed: int) -> dict: raise NotImplementedError
    def bench(self) -> Tuple[float, float]: raise NotImplementedError
    def close(self) -> None: pass


class Stop(Exception):
    """Raised to leave the night cleanly. reason: 'budget' (chunk time is up) or an external reason (wake, assistant, pause, pressure, signal)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason

    @property
    def external(self) -> bool:
        return self.reason != "budget"


def memory_pressure_level(min_free_gb: float = 1.0) -> int:
    """Returns 1 (fine), 2 (warn) or 4 (critical). macOS: kern.memorystatus_vm_pressure_level. Elsewhere: psutil available memory below
    min_free_gb is critical (4); without psutil the check is skipped (1)."""
    if sys.platform == "darwin":
        try:
            out = subprocess.run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], capture_output=True, text=True, timeout=3)
            return int(out.stdout.strip() or 1)
        except Exception:
            return 1
    try:
        import psutil
        return 4 if psutil.virtual_memory().available < min_free_gb * 1e9 else 1
    except Exception:
        return 1


class Guards:
    """External stop conditions, polled at most every poll_s: SIGTERM flag, ASSISTANT_RUNNING, PAUSE_OTHERS, memory pressure > 1
    on `hot_polls` polls in a row (one reading is not enough: loading the model lifts an 8 GB Mac to "warn" for a few seconds)."""

    def __init__(self, paths=None, poll_s: float = 10.0, pressure: Optional[Callable[[], int]] = None, min_free_gb: float = 1.0,
                 now: Callable[[], float] = time.time, hot_polls: int = 2):
        self.paths, self.poll_s, self.now, self.hot_polls, self._hot = paths, poll_s, now, max(1, hot_polls), 0
        self.pressure = pressure or (lambda: memory_pressure_level(min_free_gb))
        self.signalled: Optional[str] = None
        self._last, self._reason = -1e18, None

    def signal(self, name: str = "signal") -> None:
        self.signalled = name

    def reason(self) -> Optional[str]:
        if self.signalled:
            return self.signalled
        t = self.now()
        if t - self._last >= self.poll_s:
            self._last = t
            r = None
            if self.paths is not None:
                if os.path.exists(str(self.paths.assistant_running)):
                    r = "assistant_running"
                elif os.path.exists(str(self.paths.pause_file)):
                    r = "pause_others"
            if r is None:
                self._hot = self._hot + 1 if self.pressure() > 1 else 0
                if self._hot >= self.hot_polls:
                    r = "memory_pressure"
            self._reason = r
        return self._reason


class Clock:
    """Chunk deadline. check(need_s) raises Stop when a guard fires or fewer than need_s seconds remain before the reserve."""

    def __init__(self, budget_s: float, guards: Optional[Guards] = None, reserve_s: Optional[float] = None,
                 now: Callable[[], float] = time.time):
        self.now, self.guards = now, guards or Guards()
        self.t0 = now()
        self.budget_s = float(budget_s)
        self.reserve_s = reserve_s if reserve_s is not None else max(20.0, 0.05 * self.budget_s)

    def elapsed(self) -> float:
        return self.now() - self.t0

    def left(self) -> float:
        return self.budget_s - self.reserve_s - self.elapsed()

    def check(self, need_s: float = 0.0) -> None:
        r = self.guards.reason()
        if r:
            raise Stop(r)
        if self.left() < need_s:
            raise Stop("budget")
