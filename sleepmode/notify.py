from __future__ import annotations

import subprocess
import sys
import urllib.request
from pathlib import Path

from .config import Config
from .state import atomic_write, now_iso


def is_mac() -> bool:
    return sys.platform == "darwin"


def applescript_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def display_notification(title: str, body: str) -> bool:
    """macOS banner via osascript. False (and no effect) off macOS or on failure."""
    if not is_mac():
        return False
    script = "display notification %s with title %s" % (applescript_quote(body), applescript_quote(title))
    try:
        return subprocess.run(["osascript", "-e", script], capture_output=True, timeout=15).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def prepend_inbox(path: Path, title: str, body: str) -> None:
    try:
        old = path.read_text()
    except OSError:
        old = ""
    atomic_write(path, "## %s  %s\n%s\n\n%s" % (now_iso(), title, body, old))


def ntfy_push(topic: str, title: str, body: str) -> bool:
    req = urllib.request.Request("https://ntfy.sh/" + topic, data=body.encode("utf-8"),
                                 headers={"Title": title.encode("ascii", "replace").decode()})
    try:
        urllib.request.urlopen(req, timeout=10).read()
        return True
    except Exception:
        return False


def send(cfg: Config, title: str, body: str) -> dict:
    prepend_inbox(cfg.inbox_path, title, body)
    res = {"inbox": True, "banner": display_notification(title, body)}
    if cfg.ntfy_topic:
        res["ntfy"] = ntfy_push(cfg.ntfy_topic, title, body)
    return res
