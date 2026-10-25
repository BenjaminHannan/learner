from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import List, Optional


def _ops_dir() -> str:
    return os.environ.get("SLEEPMODE_OPS") or os.path.join(os.path.expanduser("~"), "learner-ops")


def _default_home() -> str:
    return os.environ.get("SLEEPMODE_HOME") or os.path.join(_ops_dir(), "sleepmode")


@dataclass
class Config:
    home: str = ""
    pause_others: str = ""          # file whose presence pauses work
    assistant_running: str = ""     # file whose presence wakes us
    diary_dir: str = ""
    # timing
    hour_s: float = 3600.0
    poll_s: float = 5.0
    checkin_reserve_s: float = 120.0
    kill_grace_s: float = 30.0
    budget_slack_s: float = 120.0
    idle_hours: float = 6.0
    # plateau
    plateau_window: int = 2
    plateau_min_gain_per_hour: float = 0.5
    plateau_patience: int = 2
    min_sleep_hours: float = 2.0
    # worker / practice
    mlx_model: str = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"
    practice_min_share: float = 0.05
    practice_tasks: int = 12
    practice_model_url: str = ""
    practice_model: str = ""
    practice_server_cmd: List[str] = field(default_factory=list)
    research_web: bool = True
    practice_tools: bool = True     # tools (python, diary search, web) during practice
    # check-in
    mail_enabled: bool = True
    calendar_enabled: bool = True
    mail_lookback_h: float = 24.0
    calendar_ahead_h: float = 12.0
    event_soon_h: float = 2.0
    vip_senders: List[str] = field(default_factory=list)
    urgent_words: List[str] = field(default_factory=lambda: [
        "urgent", "asap", "today", "deadline", "due", "overdue", "action required",
        "payment failed", "security alert", "verify", "interview", "final notice"])
    imap_host: str = ""
    imap_user: str = ""
    imap_password_env: str = "SLEEPMODE_IMAP_PASSWORD"
    triage_url: str = ""
    triage_model: str = ""
    ntfy_topic: str = ""

    def __post_init__(self):
        self.home = self.home or _default_home()
        ops = _ops_dir()
        self.pause_others = self.pause_others or os.path.join(ops, "PAUSE_OTHERS")
        self.assistant_running = self.assistant_running or os.path.join(ops, "ASSISTANT_RUNNING")
        self.diary_dir = self.diary_dir or os.path.join(ops, "diary", "raw")

    def path(self, *parts: str) -> Path:
        return Path(self.home, *parts)

    @property
    def status_path(self): return self.path("status.json")
    @property
    def events_path(self): return self.path("events.jsonl")
    @property
    def wake_path(self): return self.path("WAKE")
    @property
    def sleeping_path(self): return self.path("SLEEPING")
    @property
    def inbox_path(self): return self.path("inbox.md")
    @property
    def notified_path(self): return self.path("notified.json")
    @property
    def summary_path(self): return self.path("summary.md")
    @property
    def worker_dir(self): return self.path("worker")
    @property
    def practice_dir(self): return self.path("practice")


def load(overrides: Optional[dict] = None) -> Config:
    """Defaults < $SLEEPMODE_HOME/config.json < overrides."""
    home = _default_home()
    data: dict = {}
    try:
        data = json.loads(Path(home, "config.json").read_text())
    except (OSError, ValueError):
        pass
    data.update(overrides or {})
    names = {f.name for f in fields(Config)}
    data = {k: v for k, v in data.items() if k in names}
    data.setdefault("home", home)
    return Config(**data)
