"""Where things live. Home: env SLEEPMLX_HOME, default ~/learner-ops/sleepmlx."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def is_windows() -> bool:
    return sys.platform.startswith("win")


def appdata_root() -> Path:
    return Path(os.environ.get("APPDATA") or os.path.expanduser("~/AppData/Roaming")) / "Premonition"


def ops_dir() -> Path:
    """Where the flag files (PAUSE_OTHERS, ASSISTANT_RUNNING) live: ~/learner-ops on the Mac, the sleep root on Windows."""
    if os.environ.get("LEARNER_OPS"):
        return Path(os.path.expanduser(os.environ["LEARNER_OPS"]))
    return appdata_root() / "sleep" if is_windows() else Path(os.path.expanduser("~/learner-ops"))


@dataclass
class Paths:
    home: Path
    diary_dir: Path
    ops: Path
    user_data: Optional[Path] = None   # the Desk's userData (memory.json, tracking.md); None = env SLEEPMLX_USERDATA or the app's default folder

    @classmethod
    def from_env(cls) -> "Paths":
        ops = ops_dir()
        if is_windows():   # %APPDATA%/Premonition/sleep is the sleep root; the app's gateway log is %APPDATA%/Premonition/diary
            home_d, diary_d = ops, appdata_root() / "diary"
        else:
            home_d, diary_d = ops / "sleepmlx", ops / "diary" / "raw"
        home = Path(os.path.expanduser(os.environ.get("SLEEPMLX_HOME", str(home_d))))
        diary = Path(os.path.expanduser(os.environ.get("SLEEPMLX_DIARY_DIR", str(diary_d))))
        ud = os.environ.get("SLEEPMLX_USERDATA")
        return cls(home, diary, ops, Path(os.path.expanduser(ud)) if ud else None)

    @property
    def userdata_dir(self) -> Path:
        if self.user_data is not None:
            return Path(self.user_data)
        from .lessons import default_user_data
        return default_user_data()

    @property
    def state(self): return self.home / "state.json"
    @property
    def items(self): return self.home / "items.json"
    @property
    def cards(self): return self.home / "cards.jsonl"
    @property
    def nights(self): return self.home / "nights.jsonl"
    @property
    def adapter(self): return self._adapter_path("current", "adapter")
    @property
    def adapter_prev(self): return self._adapter_path("previous", "adapter.prev")

    def _adapter_path(self, key, legacy):
        manifest = self.home / "adapters.json"
        if not manifest.exists():
            return self.home / legacy
        try:
            data = json.loads(manifest.read_text())
            if data.get("version") != 1:
                raise ValueError("unsupported version")
            entry = data[key]
            if entry is None and key == "previous":
                return self.home / "adapters" / ".none"
            if not isinstance(entry, str) or not entry or Path(entry).is_absolute() or ".." in Path(entry).parts:
                raise ValueError("invalid adapter path")
            target = self.home / entry
            if not target.is_dir():
                raise ValueError("required adapter is missing: %s" % target)
            return target
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise RuntimeError("invalid adapter manifest %s: %s" % (manifest, e)) from e
    @property
    def work(self): return self.home / "night"          # in-progress night: night.json, gen cache, adapter checkpoint
    @property
    def work_adapter(self):
        from .checkpoint import checkpoint_path
        return checkpoint_path(self.work, read_json(self.night_json, {}) or {})
    @property
    def night_json(self): return self.work / "night.json"
    @property
    def gen_cache(self): return self.work / "gen_cache.jsonl"
    @property
    def gate_base(self): return self.home / "gate_base.json"
    @property
    def pause_file(self): return self.ops / "PAUSE_OTHERS"
    @property
    def assistant_running(self): return self.ops / "ASSISTANT_RUNNING"
    @property
    def ignore(self): return self.home / "ignore.txt"
    @property
    def log(self): return self.home / "sleepmlx.log"

    def mk(self):
        self.home.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def write_json(path: Path, obj) -> None:
    """Atomic write (tmp + rename) so a kill never leaves half a file."""
    write_text(path, json.dumps(obj, indent=1, sort_keys=True))


def write_text(path: Path, content: str) -> None:
    """Durably replace one file, without sharing a temporary name."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, str(path))
        if os.name != "nt":
            dfd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
