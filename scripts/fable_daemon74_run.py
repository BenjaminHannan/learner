"""Exp 74 -- persistent agent daemon: the agent as a process that survives restarts.

Wraps scripts/fable_agent_loop.py (AgentLoop + Protocols) with a durable mailbox:

  <dir>/notebook/events.jsonl  the ONLY fact store (append-only JSONL + hash chain,
                                owned by fable_notebook_contract; verified on every boot)
  <dir>/state.json              loop state (AgentLoop's own atomic save)
  <dir>/inbox/*.txt             one English turn per file; daemon takes them in name order
  <dir>/outbox/<same name>.txt  the daemon's English reply (atomic write)
  <dir>/done/                   input files moved here after their reply is durably written
  <dir>/heartbeat.json          pid, boot time, turn count, notebook length, chain hash;
                                rewritten every 5 s
  <dir>/daemon_status.json      boot verdict: chain verified hash, or the exact broken line
  <dir>/daemon.log.jsonl        every turn + every idle tick + boot/stop lines
  <dir>/STOP                    drop this file in and the daemon exits gracefully (code 0)

Plug-in points for real ears/mouth (see EARS_PLUG_IN / MOUTH_PLUG_IN below):
pass any object satisfying fable_agent_loop.Ears / .Mouth (runtime-checked Protocols)
to build_loop(). Defaults are FakeEars/FakeMouth (test scaffolding, not the real thing).

Portability: stdlib only in this file; pathlib everywhere; os.replace for atomic
writes (atomic on Windows and POSIX); polling loop only -- no fork, no signals,
no Unix-only modules. Runs on Python 3.10+ (Ben's Windows PC) and macOS.

  Windows:  py -3.10 -B scripts\\fable_daemon74_run.py --dir C:\\Users\\Ben\\fable-daemon
  macOS:    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
            uv run --offline --no-project --python 3.12 --with torch --with numpy \\
              python -B scripts/fable_daemon74_run.py --dir DIR
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as G  # noqa: E402
import fable_notebook_contract as C  # noqa: E402

HEARTBEAT_EVERY_S = 5.0
POLL_S = 0.05


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------- plug-in points
# EARS_PLUG_IN: replace FakeEars() with the real ears object (must satisfy G.Ears:
#   hear(turn: str) -> list of action dicts). Nothing else in this file changes.
def build_ears(ears=None):
    ears = ears or G.FakeEars()
    assert isinstance(ears, G.Ears), f"ears must satisfy the G.Ears Protocol, got {type(ears)}"
    return ears


# MOUTH_PLUG_IN: replace FakeMouth() with the real mouth object (must satisfy G.Mouth:
#   say(record: dict) -> one English sentence, content words from the record only).
def build_mouth(mouth=None):
    mouth = mouth or G.FakeMouth()
    assert isinstance(mouth, G.Mouth), f"mouth must satisfy the G.Mouth Protocol, got {type(mouth)}"
    return mouth


def build_loop(state_dir: Path, *, ears=None, mouth=None, reasoner=None,
               sleeper=None, thinker=None, sleep_threshold: int = G.SLEEP_THRESHOLD) -> G.AgentLoop:
    """Reasoner/Sleeper/Thinker also go through the AgentLoop Protocols; real
    reasoner/sleeper/thinker objects drop in here without touching the daemon."""
    return G.AgentLoop(str(state_dir), ears=build_ears(ears), mouth=build_mouth(mouth),
                       reasoner=reasoner or G.LookupReasoner(),
                       sleeper=sleeper or G.StubSleeper(), thinker=thinker,
                       sleep_threshold=sleep_threshold)


# ------------------------------------------------------- small file helpers
def _atomic_write(path: Path, text: str) -> None:
    tmp = path.parent / f"{path.name}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)  # atomic on Windows and POSIX


def _append_log(path: Path, event: dict) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()


class Daemon:
    def __init__(self, root, *, idle_seconds: float = 30.0,
                 sleep_threshold: int = G.SLEEP_THRESHOLD) -> None:
        self.root = Path(root)
        self.idle_seconds = float(idle_seconds)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        self.pid = os.getpid()
        self.boot_time = time.time()
        self.loop = build_loop(self.root, sleep_threshold=sleep_threshold)
        self.torn_found = any("torn notebook tail" in note for note in self.loop.notes)

    # ------------------------------------------------ boot verification
    def boot_status(self) -> dict:
        """The hash chain was already verified line-by-line by Notebook.__init__
        on every boot: a bad middle line raises LogCorrupt (daemon refuses to
        start, see main()); a torn final line sets torn_tail (repaired by the
        loop, original bytes kept in notebook/torn-tail.txt). Either way the
        verdict lands here and in the log -- never silently accepted."""
        return {"boot_ok": True, "pid": self.pid,
                "boot_time_iso": datetime.fromtimestamp(
                    self.boot_time, timezone.utc).isoformat(timespec="seconds"),
                "torn_tail_found_and_repaired": self.torn_found,
                "loop_notes": list(self.loop.notes),
                "notebook_events": len(self.loop.nb.events),
                "verified_chain_hash": self.loop.nb.last_sha}

    def write_heartbeat(self) -> dict:
        beat = {"pid": self.pid,
                "boot_time_iso": datetime.fromtimestamp(
                    self.boot_time, timezone.utc).isoformat(timespec="seconds"),
                "updated_iso": _now_iso(),
                "turn_count": int(self.loop.counters.get("turns", 0)),
                "notebook_events": len(self.loop.nb.events),
                "last_verified_chain_hash": self.loop.nb.last_sha,
                "mode": self.loop.mode}
        _atomic_write(self.heartbeat_path, json.dumps(beat, indent=1, sort_keys=True))
        return beat

    # ------------------------------------------------ one mailbox turn
    def process_file(self, path: Path) -> dict:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return {"event": "turn-skipped", "file": path.name}
        said = self.loop.turn(text)  # notebook append (fsync) happens INSIDE, before we reply
        reply = " ".join(said) if said else "(nothing to say)"
        _atomic_write(self.outbox / path.name, reply + "\n")  # reply durable BEFORE ...
        os.replace(path, self.done / path.name)  # ... the input is moved away
        record = {"t": _now_iso(), "event": "turn", "file": path.name,
                  "turn_text": text.strip()[:200], "reply": reply[:500],
                  "turn_count": int(self.loop.counters.get("turns", 0)),
                  "notebook_events": len(self.loop.nb.events)}
        _append_log(self.log_path, record)
        return record

    # ------------------------------------------------ main loop
    def run(self) -> int:
        for stale in self.outbox.glob("*.tmp*"):  # half-written replies from a killed run
            try:
                stale.unlink()
            except OSError:
                pass
        status = self.boot_status()
        _atomic_write(self.status_path, json.dumps(status, indent=1, sort_keys=True))
        _append_log(self.log_path, {"t": _now_iso(), "event": "boot", **status})
        self.write_heartbeat()
        last_heartbeat = time.time()
        last_activity = time.time()
        last_idle_tick = 0.0
        while True:
            if self.stop_file.exists():  # graceful stop: finish nothing, just exit cleanly
                _append_log(self.log_path, {"t": _now_iso(), "event": "stop-file-seen"})
                self.write_heartbeat()
                _append_log(self.log_path, {"t": _now_iso(), "event": "stopped"})
                return 0
            files = sorted(self.inbox.glob("*.txt"))
            if files:
                for path in files:
                    if self.stop_file.exists():
                        break
                    try:
                        self.process_file(path)
                    except C.LogCorrupt as exc:  # notebook refused the write: report, keep file
                        _append_log(self.log_path, {"t": _now_iso(), "event": "log-corrupt",
                                                    "file": path.name, "error": str(exc)})
                last_activity = time.time()
            else:
                now = time.time()
                # Idle behaviour: exactly the loop's own hooks (Thinker/Sleeper via
                # AgentLoop.step: SLEEP tick when the experience log is full, else the
                # THINKING tick), then logged. Stubs change nothing; real hooks drop in.
                if (now - last_activity >= self.idle_seconds
                        and now - last_idle_tick >= self.idle_seconds):
                    event = self.loop.step()
                    last_idle_tick = now
                    _append_log(self.log_path, {"t": _now_iso(), "event": "idle-tick",
                                                "mode": event["mode"],
                                                "detail": str(event["detail"])[:300],
                                                "counters": dict(self.loop.counters)})
            if time.time() - last_heartbeat >= HEARTBEAT_EVERY_S:
                self.write_heartbeat()
                last_heartbeat = time.time()
            time.sleep(POLL_S)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 74 persistent agent daemon")
    parser.add_argument("--dir", required=True, help="daemon directory (mailbox + notebook live here)")
    parser.add_argument("--idle-seconds", type=float, default=30.0,
                        help="idle time before one Thinker/Sleeper tick is taken and logged")
    parser.add_argument("--sleep-threshold", type=int, default=G.SLEEP_THRESHOLD)
    args = parser.parse_args(argv)
    root = Path(args.dir)
    root.mkdir(parents=True, exist_ok=True)
    try:
        daemon = Daemon(root, idle_seconds=args.idle_seconds,
                        sleep_threshold=args.sleep_threshold)
    except C.LogCorrupt as exc:  # middle-of-log corruption: report the exact line, refuse to run
        status = {"boot_ok": False, "pid": os.getpid(), "boot_time_iso": _now_iso(),
                  "error": f"notebook hash chain broken on boot: {exc}"}
        _atomic_write(root / "daemon_status.json", json.dumps(status, indent=1, sort_keys=True))
        with open(root / "daemon.log.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"t": _now_iso(), "event": "boot-refused", **status}) + "\n")
        print(f"daemon refuses to start: {exc}", file=sys.stderr, flush=True)
        return 1
    return daemon.run()


if __name__ == "__main__":
    sys.exit(main())
