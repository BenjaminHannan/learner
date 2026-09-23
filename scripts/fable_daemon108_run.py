"""Exp 108 -- exactly-once turn handling on boot (one-change follow-up to exp 93 FAIL).

THE ONE CHANGE (vs sealed scripts/fable_daemon74_run.py, which is NOT edited):
on boot the daemon reconciles crash state so each mailbox message is finished
exactly once -- either its reply is finished once (if no durable reply exists
yet) or the message is dropped (if its reply was already durably written),
never both.

Mechanism (exp 93 diagnosis): a kill -9 landing between AgentLoop.submit()'s
state save and the end-of-step save leaves the in-flight text in state.json's
loop.inbox; the rebooted daemon re-executes it as a "ghost tick" inside the
next turn(), so the reply stream is not exactly-once.

Fix, applied here as a wrapper/subclass only:
  1. Stable id: every mailbox message is already named (<seq>.txt); that
     filename is the message's stable id. A per-turn receipt
     (<dir>/receipts.jsonl: file -> reply sha256) is appended AFTER the outbox
     reply is durably written and BEFORE the input is moved to done/.
  2. On boot, boot_reconcile() runs before any turn is served:
     (a) loop.inbox (state.json) is a crash artefact, NOT a durable queue --
         it is dropped (cleared + saved + logged). The daemon mailbox's own
         inbox/*.txt files still hold every piece of undone work, so nothing
         submitted is lost.
     (b) any inbox/<id>.txt whose outbox/<id>.txt already exists had its reply
         durably written (outbox writes are atomic tmp+replace): the input is
         moved to done/ WITHOUT re-executing the turn, never both.
     Remaining inbox files (reply not yet durable) are processed normally,
     exactly once. Re-execution there is fact-safe: notebook teaches dedupe
     to DUPLICATE_OK and asks are read-only, and only one durable reply ever
     exists per id.

Usage (same CLI as daemon74, plus --loop102 for the unregistered scale step):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_daemon108_run.py --dir DIR [--loop102]

Portability: stdlib only in this file (loop102 import is lazy, only for the
--loop102 scale step); pathlib everywhere; os.replace for atomic writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as G  # noqa: E402 (Protocols + thresholds, read-only)
import fable_daemon74_run as D74  # noqa: E402 (sealed daemon, read-only)

RECEIPTS_NAME = "receipts.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _reply_sha(reply: str) -> str:
    return hashlib.sha256(reply.encode("utf-8")).hexdigest()[:16]


def append_receipt(root, filename: str, reply: str, note: str = "turn") -> None:
    """Audit receipt: one line per durably-replied id (file move may follow)."""
    path = Path(root) / RECEIPTS_NAME
    line = json.dumps({"t": _now_iso(), "file": filename,
                       "reply_sha256": _reply_sha(reply),
                       "reply_len": len(reply), "note": note},
                      sort_keys=True) + "\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass


def read_receipts(root) -> list[dict]:
    """Torn final lines (kill mid-append) are skipped; receipts are audit-only."""
    path = Path(root) / RECEIPTS_NAME
    out: list[dict] = []
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def boot_reconcile(daemon) -> dict:
    """Exactly-once boot reconciliation. Runs before any turn is served.

    (a) Drop the loop.inbox crash artefact. (b) Finish interrupted file moves
    for ids whose reply is already durable, without re-executing them.
    Returns a summary dict (also appended to the daemon log).
    """
    loop = daemon.loop
    ghost = list(getattr(loop, "inbox", []) or [])
    if ghost:
        loop.inbox = []
        loop._save()  # persist the drop atomically, like every other tick
    finished_without_reexec: list[str] = []
    for path in sorted(daemon.inbox.glob("*.txt")):
        out = daemon.outbox / path.name
        if not out.exists():
            continue  # reply not durable: will be processed normally, once
        try:
            reply = out.read_text(encoding="utf-8")
        except OSError:
            continue  # unreadable outbox: do NOT treat as durable
        try:
            os.replace(path, daemon.done / path.name)
        except OSError:
            continue
        finished_without_reexec.append(path.name)
        append_receipt(daemon.root, path.name, reply, note="boot-finish-move")
    summary = {"dropped_loop_inbox": len(ghost),
               "ghost_preview": [str(t)[:80] for t in ghost[:5]],
               "finished_without_reexec": finished_without_reexec}
    D74._append_log(daemon.log_path,
                    {"t": _now_iso(), "event": "boot-exactly-once-reconcile",
                     **summary,
                     "turn_count": int(loop.counters.get("turns", 0))})
    return summary


class Daemon108(D74.Daemon):
    """Exp-74 daemon + exactly-once boot handling. No other behaviour changes."""

    def __init__(self, root, *, idle_seconds: float = 30.0,
                 sleep_threshold: int = G.SLEEP_THRESHOLD) -> None:
        super().__init__(root, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.reconcile_report = boot_reconcile(self)

    def process_file(self, path: Path) -> dict:
        record = super().process_file(path)
        if record.get("event") == "turn":
            try:
                reply = (self.outbox / path.name).read_text(encoding="utf-8")
            except OSError:
                reply = str(record.get("reply", ""))
            append_receipt(self.root, path.name, reply)
        return record


def build_loop102_daemon108(root, cfg: dict | None = None,
                            idle_seconds: float = 30.0,
                            sleep_threshold=None):
    """Latest integrated loop daemon (scripts/fable_loop102_agent.py, unedited)
    wrapped the same way: subclass in THIS file + boot_reconcile. The loop102
    import is lazy so the registered daemon108 path stays light."""
    import fable_loop102_agent as L102  # noqa: E402 (read-only wrap)

    class Loop102Daemon108(L102.Loop102Daemon):
        def process_file(self, path: Path) -> dict:
            record = super().process_file(path)
            if record.get("event") in ("turn", "turn-skipped-unreadable"):
                try:
                    reply = (self.outbox / path.name).read_text(
                        encoding="utf-8")
                except OSError:
                    reply = str(record.get("reply", ""))
                append_receipt(self.root, path.name, reply)
            return record

    kwargs = {} if sleep_threshold is None else {
        "sleep_threshold": sleep_threshold}
    daemon = Loop102Daemon108(root, cfg=cfg, idle_seconds=idle_seconds,
                              **kwargs)
    daemon.reconcile_report = boot_reconcile(daemon)
    return daemon


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Exp 108 exactly-once daemon (wraps daemon74 / loop102)")
    parser.add_argument("--dir", required=True,
                        help="daemon directory (mailbox + notebook live here)")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--sleep-threshold", type=int, default=G.SLEEP_THRESHOLD)
    parser.add_argument("--loop102", action="store_true",
                        help="wrap the loop102 integrated daemon instead "
                             "(unregistered scale step only)")
    parser.add_argument("--config", default=None,
                        help="JSON config for --loop102 (plug points)")
    args = parser.parse_args(argv)
    root = Path(args.dir)
    root.mkdir(parents=True, exist_ok=True)
    if args.loop102:
        import json as _json
        cfg = _json.loads(Path(args.config).read_text(encoding="utf-8")) \
            if args.config else None
        daemon = build_loop102_daemon108(
            root, cfg=cfg, idle_seconds=args.idle_seconds,
            sleep_threshold=args.sleep_threshold)
        return daemon.run()
    daemon = Daemon108(root, idle_seconds=args.idle_seconds,
                       sleep_threshold=args.sleep_threshold)
    return daemon.run()


if __name__ == "__main__":
    sys.exit(main())
