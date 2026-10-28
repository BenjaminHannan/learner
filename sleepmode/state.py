from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import Config


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(str(tmp), str(path))


class State:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        Path(cfg.home).mkdir(parents=True, exist_ok=True)
        self.status: dict = {}

    # events
    def event(self, kind: str, **kw) -> None:
        rec = {"ts": now_iso(), "kind": kind}
        rec.update(kw)
        try:
            with open(str(self.cfg.events_path), "a") as f:
                f.write(json.dumps(rec, default=str) + "\n")
        except OSError:
            pass

    def events(self, kind: Optional[str] = None) -> List[dict]:
        out = []
        try:
            for line in self.cfg.events_path.read_text().splitlines():
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if kind is None or rec.get("kind") == kind:
                    out.append(rec)
        except OSError:
            pass
        return out

    # status
    def set_status(self, **kw) -> dict:
        self.status.update(kw)
        self.status["updated"] = now_iso()
        atomic_write(self.cfg.status_path, json.dumps(self.status, indent=2, default=str))
        return self.status

    def read_status(self) -> dict:
        try:
            return json.loads(self.cfg.status_path.read_text())
        except (OSError, ValueError):
            return {}

    # flags
    def wake_requested(self) -> bool:
        return self.cfg.wake_path.exists()

    def request_wake(self) -> None:
        atomic_write(self.cfg.wake_path, now_iso())

    def clear_wake(self) -> None:
        _rm(self.cfg.wake_path)

    def assistant_running(self) -> bool:
        return os.path.exists(self.cfg.assistant_running)

    def paused_by_file(self) -> bool:
        return os.path.exists(self.cfg.pause_others)

    def sleeping_pid(self) -> Optional[int]:
        """pid in SLEEPING if that process is alive, else None."""
        try:
            pid = int(self.cfg.sleeping_path.read_text().split()[0])
        except (OSError, ValueError, IndexError):
            return None
        return pid if pid_alive(pid) else None

    def mark_sleeping(self) -> None:
        atomic_write(self.cfg.sleeping_path, "%d\n" % os.getpid())

    def clear_sleeping(self) -> None:
        _rm(self.cfg.sleeping_path)

    # notified ids
    def notified(self) -> dict:
        try:
            return json.loads(self.cfg.notified_path.read_text())
        except (OSError, ValueError):
            return {}

    def save_notified(self, d: dict, keep_days: float = 30) -> None:
        cutoff = time.time() - keep_days * 86400
        d = {k: v for k, v in d.items() if not isinstance(v, (int, float)) or v >= cutoff}
        atomic_write(self.cfg.notified_path, json.dumps(d))

    def practice_files(self) -> List[str]:
        """sft/pairs files from earlier practice days, sorted."""
        out: List[str] = []
        for name in ("sft.jsonl", "pairs.jsonl"):
            out += [str(p) for p in self.cfg.practice_dir.glob("*/" + name)]
        return sorted(out)


def _rm(p: Path) -> None:
    try:
        os.remove(str(p))
    except OSError:
        pass
