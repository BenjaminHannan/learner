"""Exp 141 -- mailbox settle gate: registered single-change robustness fix for a
mailbox race seen in exp 135's regression run.

RACE (evidence: artifacts/fable-fix135-20260922/marks135/soak-report.json,
turn 238 "What is SoakP038's city?" got "I didn't catch anything." while the
director's re-run of the same soak got 0 wrong -- intermittent under load):
scripts/fable_daemon74_run.py Daemon.run lists inbox/*.txt and serves every
file it sees, but writers (scripts/fable_marks123_all.py soak, and any real
client) write with non-atomic write_text: create file, then write bytes. A
poll landing between create and write serves a 0-byte file, and the empty
turn is answered "I didn't catch anything." -- a wrong reply on a non-empty
message.

THE ONE CHANGE (daemon side only, additive -- no existing file is edited):
a mailbox file is served only when it is "settled":

  (A) non-zero size AND unchanged (size, mtime_ns) across two consecutive
      polls, OR
  (B) first observed by the daemon at least GRACE_S (default 2.0 s) ago.

So a truly empty (0-byte) message still gets the existing "I didn't catch
anything." reply exactly once, after the grace period. No other behaviour
change: process_file, the outbox/done protocol, heartbeats, idle ticks and
the STOP path are byte-identical to the wrapped loop134 daemon (the run()
loop below mirrors D74.Daemon.run with only the file-selection line
changed).

Composition with exp 108 (scripts/fable_daemon108_run.py, read-only import):
CombinedSettleExactlyOnce141 = settle gate + 108 receipts + 108
boot_reconcile, for the R4 kill-9 burst.

Usage (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_daemon141_settle.py --daemon --dir DIR \\
    --config artifacts/fable-loop134-20260922/loop134-config.json [--combined]

Portability: stdlib only in this file; pathlib everywhere; polling only.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as G  # noqa: E402 (thresholds, read-only)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon74_run as D74  # noqa: E402 (sealed daemon, read-only)
import fable_loop134_agent as L134  # noqa: E402 (wrapped daemon, read-only)
import fable_notebook_contract as C  # noqa: E402 (LogCorrupt, read-only)

SETTLE_GRACE_S = 2.0
POLL_S = D74.POLL_S


class SettleGate141:
    """Daemon-side observation gate. No I/O except stat()."""

    def __init__(self, grace_s: float = SETTLE_GRACE_S) -> None:
        self.grace_s = float(grace_s)
        # name -> [first_seen_monotonic, (size, mtime_ns)]
        self._seen: dict[str, list] = {}

    def is_settled(self, path: Path, now: float | None = None) -> bool:
        """True only under rule (A) or rule (B) from the module docstring."""
        now = time.monotonic() if now is None else now
        try:
            st = path.stat()
        except OSError:
            self._seen.pop(path.name, None)
            return False
        key = (st.st_size, st.st_mtime_ns)
        prev = self._seen.get(path.name)
        if prev is None:
            self._seen[path.name] = [now, key]
            return False
        first_seen, last_key = prev
        prev[1] = key
        if st.st_size > 0 and last_key == key:
            return True  # rule (A): non-zero and stable across two polls
        if now - first_seen >= self.grace_s:
            return True  # rule (B): old enough (covers truly-empty files)
        return False

    def prune(self, present: set[str]) -> None:
        for name in list(self._seen):
            if name not in present:
                del self._seen[name]


class Loop134Settle141Daemon(L134.Loop134Daemon):
    """Loop134Daemon + the settle gate. process_file is inherited unchanged.

    The name ends with "Daemon" (and starts with "Loop") so the marks123
    runner's loader (first *Daemon, preferring Loop*) picks this class.
    """

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = SETTLE_GRACE_S) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.settle = SettleGate141(grace_s=grace_s)

    def settled_files(self) -> list[Path]:
        files = sorted(self.inbox.glob("*.txt"))
        self.settle.prune({p.name for p in files})
        now = time.monotonic()
        return [p for p in files if self.settle.is_settled(p, now)]

    # Mirror of D74.Daemon.run with THE ONE CHANGE: the poll serves only
    # settled files (line marked [141]). Everything else is identical.
    def run(self) -> int:
        for stale in self.outbox.glob("*.tmp*"):
            try:
                stale.unlink()
            except OSError:
                pass
        status = self.boot_status()
        D74._atomic_write(self.status_path,
                          json.dumps(status, indent=1, sort_keys=True))
        D74._append_log(self.log_path,
                        {"t": D74._now_iso(), "event": "boot", **status})
        self.write_heartbeat()
        last_heartbeat = time.time()
        last_activity = time.time()
        last_idle_tick = 0.0
        while True:
            if self.stop_file.exists():
                D74._append_log(self.log_path,
                                {"t": D74._now_iso(),
                                 "event": "stop-file-seen"})
                self.write_heartbeat()
                D74._append_log(self.log_path,
                                {"t": D74._now_iso(), "event": "stopped"})
                return 0
            files = self.settled_files()  # [141] THE ONE CHANGE (was: all *.txt)
            if files:
                for path in files:
                    if self.stop_file.exists():
                        break
                    try:
                        self.process_file(path)
                    except C.LogCorrupt as exc:
                        D74._append_log(
                            self.log_path,
                            {"t": D74._now_iso(), "event": "log-corrupt",
                             "file": path.name, "error": str(exc)})
                last_activity = time.time()
            else:
                now = time.time()
                if (now - last_activity >= self.idle_seconds
                        and now - last_idle_tick >= self.idle_seconds):
                    event = self.loop.step()
                    last_idle_tick = now
                    D74._append_log(
                        self.log_path,
                        {"t": D74._now_iso(), "event": "idle-tick",
                         "mode": event["mode"],
                         "detail": str(event["detail"])[:300],
                         "counters": dict(self.loop.counters)})
            if time.time() - last_heartbeat >= D74.HEARTBEAT_EVERY_S:
                self.write_heartbeat()
                last_heartbeat = time.time()
            time.sleep(POLL_S)


class CombinedSettleExactlyOnce141Daemon(Loop134Settle141Daemon):
    """Settle gate (141) + exactly-once boot handling (108).

    __init__ runs D108.boot_reconcile after the loop is built (drops the
    loop.inbox crash artefact; finishes interrupted moves for ids whose
    reply is already durable without re-executing them). process_file
    appends a 108 audit receipt after the durable reply, before the move.
    """

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = SETTLE_GRACE_S) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold, grace_s=grace_s)
        self.reconcile_report = D108.boot_reconcile(self)

    def process_file(self, path: Path) -> dict:
        record = super().process_file(path)
        if record.get("event") == "turn":
            try:
                reply = (self.outbox / path.name).read_text(encoding="utf-8")
            except OSError:
                reply = str(record.get("reply", ""))
            D108.append_receipt(self.root, path.name, reply)
        return record


def build_cfg(config_path: str | None) -> dict:
    cfg = copy.deepcopy(L134.DEFAULT_CONFIG134)
    if config_path:
        cfg.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
    return cfg


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 141 settle-gated daemon")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--config", default=None, help="JSON config")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--grace", type=float, default=SETTLE_GRACE_S,
                        help="settle grace period in seconds")
    parser.add_argument("--sleep-threshold", type=int, default=None)
    parser.add_argument("--combined", action="store_true",
                        help="settle gate + exp-108 exactly-once")
    args = parser.parse_args(argv)
    if not args.daemon:
        parser.print_help()
        return 0
    if not args.dir:
        parser.error("--daemon needs --dir")
    cfg = build_cfg(args.config)
    cls = CombinedSettleExactlyOnce141Daemon if args.combined else Loop134Settle141Daemon
    daemon = cls(args.dir, cfg=cfg, idle_seconds=args.idle_seconds,
                 sleep_threshold=args.sleep_threshold, grace_s=args.grace)
    return daemon.run()


if __name__ == "__main__":
    sys.exit(main())
