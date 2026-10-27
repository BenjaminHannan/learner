#!/usr/bin/env python3
"""Exp nb-323: a durable, hash-chained turn log. CPU only (GPU: no).

ONE change, on the verified 274 base (scripts/claude_loop274_agent.py on
origin/builder-outbox: build_agent274, Loop274Daemon; that file is
imported read-only and never edited): a NEW file (this one) holding a
durable per-turn log built on log (a), the daemon's daemon.log.jsonl
shape (scripts/fable_daemon74_run.py _append_log; record fields as in
scripts/fable_loop102_agent.py process_file), made crash-safe.

Why: Premonition has two turn logs today and neither survives a crash or
a sleep intact. (a) daemon.log.jsonl is flush-only (no fsync), has no
hash chain, truncates turn text at 200 chars and replies at 500, and is
written only in daemon mode, never when a harness calls loop.turn().
(b) The loop's experience list in state.json is emptied by every
accepted sleep and holds no replies. This file fixes (a)'s shape into a
durable log; it never touches (b).

The log (scripts/claude_nb323_turnlog.py):

  class TurnLog323(path).
    Appends one JSON line per record: flush + os.fsync + read-back
    before returning (the same pattern as
    scripts/fable_notebook_contract.py Notebook._append).
    Hash chain: each line carries prev = sha256 of the previous line,
    starting from the contract's GENESIS. Opening verifies the whole
    chain. A torn final line (crash mid-write) is reported
    (self.torn_tail) and set aside with repair_torn_tail(), as in the
    contract. Any other broken link raises TurnLog323Corrupt.
    Nothing ever rewrites or deletes a line, and sleep never touches
    the file (the sleeper is not given the log).
    Reader: read_turns(path) returns the records in order, plus the
    list of interrupted turns (a BEGIN with no END), plus whether the
    tail was torn.

  Records (no truncation anywhere):
    BEGIN, written before the inner turn runs: n, prev, kind,
      turn_id, t (UTC ISO), full text.
    END, written after the reply exists: the same turn_id, the full
      reply lines, and the daemon.log fields (records, ears_stage,
      ears_score, new_fact_ids, new_entities, turn_count,
      notebook_events before and after), mode, and deaf_s from 274's
      deaf_log274 when present.

  install_turnlog323(loop, path): wraps loop.turn as it is at install
    time, so the month-end joiner installs it LAST and it captures the
    final reply. Replies are returned unchanged. daemon.log.jsonl keeps
    being written exactly as before (the daemon is untouched).

  build_agent323(cfg) = build_agent274(cfg) plus install_turnlog323
    with the log at <state_dir>/turns323.jsonl. Loop323Daemon =
    Loop274Daemon with the same install.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_loop274_agent as A274  # noqa: E402 (verified base, read-only)
from fable_notebook_contract import GENESIS  # noqa: E402 (chain start)

TURNLOG_NAME323 = "turns323.jsonl"
FORMAT323 = 1

NOTE323 = ("turnlog323: durable hash-chained turn log "
           "(scripts/claude_nb323_turnlog.py: TurnLog323 at "
           "<state_dir>/turns323.jsonl, installed LAST around loop.turn; "
           "one BEGIN before + one END after every turn, full text and "
           "reply, fsync + read-back, GENESIS-chained; replies unchanged)")


class TurnLog323Corrupt(RuntimeError):
    """Any broken link that is not a torn final line."""


def _sha323(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now_iso323() -> str:
    return datetime.now(timezone.utc).isoformat()


class TurnLog323:
    """One append-only, hash-chained JSON line per turn record.

    Opening verifies the whole chain. A torn final line sets
    self.torn_tail (and self.torn_bytes) instead of raising; call
    repair_torn_tail() to set it aside. Any other broken link raises
    TurnLog323Corrupt.
    """

    def __init__(self, path: str | os.PathLike) -> None:
        self.path = Path(path)
        if self.path.parent and str(self.path.parent):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.torn_tail = False
        self.torn_bytes = ""
        self.last_turn_id = 0
        self._reset_counts()
        self._verify()

    def _reset_counts(self) -> None:
        self.n_lines = 0
        self.n_begins = 0
        self.last_sha = GENESIS
        self.open_ids: list[int] = []

    def _verify(self) -> None:
        self._reset_counts()
        self.torn_tail = False
        self.torn_bytes = ""
        if not self.path.exists():
            return
        try:
            raw = self.path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as exc:
            # Our writer only ever emits valid UTF-8, so undecodable
            # bytes are corruption (e.g. a tamper edit), never a clean
            # torn tail of our own writes: fail closed and loud.
            raise TurnLog323Corrupt(
                f"turnlog323 {self.path}: not valid UTF-8 ({exc})")
        lines = raw.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        for number, line in enumerate(lines):
            last = number == len(lines) - 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                if last:
                    self.torn_tail = True
                    self.torn_bytes = line
                    return
                raise TurnLog323Corrupt(
                    f"turnlog323 {self.path}: line {number + 1} is not "
                    "JSON and is not the final line")
            try:
                prev = rec["prev"]
                kind = rec["kind"]
            except (KeyError, TypeError):
                if last:
                    self.torn_tail = True
                    self.torn_bytes = line
                    return
                raise TurnLog323Corrupt(
                    f"turnlog323 {self.path}: line {number + 1} has no "
                    "prev/kind and is not the final line")
            if prev != self.last_sha:
                raise TurnLog323Corrupt(
                    f"turnlog323 {self.path}: line {number + 1} hash "
                    "chain broken")
            if kind == "BEGIN":
                try:
                    tid = int(rec["turn_id"])
                except (KeyError, TypeError, ValueError):
                    raise TurnLog323Corrupt(
                        f"turnlog323 {self.path}: line {number + 1} "
                        "BEGIN has no turn_id")
                self.n_begins += 1
                self.last_turn_id = max(self.last_turn_id, tid)
                self.open_ids.append(tid)
            elif kind == "END":
                try:
                    tid = int(rec["turn_id"])
                except (KeyError, TypeError, ValueError):
                    raise TurnLog323Corrupt(
                        f"turnlog323 {self.path}: line {number + 1} "
                        "END has no turn_id")
                if tid in self.open_ids:
                    self.open_ids.remove(tid)
            self.n_lines += 1
            self.last_sha = _sha323(line)

    def repair_torn_tail(self) -> None:
        """Set the torn final bytes aside and re-verify (contract pattern)."""
        if not self.torn_tail:
            return
        try:
            raw = self.path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TurnLog323Corrupt(
                f"turnlog323 {self.path}: not valid UTF-8 ({exc})")
        good, _, torn = raw.rpartition("\n")
        sidecar = self.path.parent / (self.path.name + ".torn-tail.txt")
        sidecar.write_text(torn, encoding="utf-8")
        tmp = self.path.with_suffix(".tmp323")
        tmp.write_text(good + "\n" if good else "", encoding="utf-8")
        os.replace(tmp, self.path)
        self._verify()
        if self.torn_tail:
            raise TurnLog323Corrupt(
                f"turnlog323 {self.path}: tail still torn after repair")

    def _append(self, record: dict) -> dict:
        if self.torn_tail:
            raise TurnLog323Corrupt(
                f"turnlog323 {self.path}: torn final line present; run "
                "repair_torn_tail() first")
        record = dict(record, n=self.n_lines + 1, prev=self.last_sha,
                      v=FORMAT323)
        line = json.dumps(record, sort_keys=True, ensure_ascii=False)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        with open(self.path, "rb") as handle:  # read-back before returning
            handle.seek(-(len(line.encode("utf-8")) + 1), os.SEEK_END)
            if handle.read().decode("utf-8") != line + "\n":
                raise TurnLog323Corrupt("turnlog323: read-back mismatch")
        self.n_lines += 1
        self.last_sha = _sha323(line)
        return record

    def append_begin(self, text: str) -> int:
        """Write the BEGIN record before the inner turn runs; return turn_id."""
        turn_id = self.n_begins + 1
        self._append({"kind": "BEGIN", "turn_id": turn_id,
                      "t": _now_iso323(), "text": str(text)})
        self.n_begins += 1
        self.last_turn_id = turn_id
        self.open_ids.append(turn_id)
        return turn_id

    def append_end(self, turn_id: int, reply: list[str], records: list,
                   ears_stage: str, ears_score: float,
                   new_fact_ids: list, new_entities: dict,
                   turn_count: int, notebook_events_before: int,
                   notebook_events_after: int, mode: str,
                   deaf_s: float | None) -> dict:
        """Write the END record after the reply exists."""
        rec = self._append({
            "kind": "END", "turn_id": int(turn_id), "t": _now_iso323(),
            "reply": [str(line) for line in (reply or [])],
            "records": list(records or []),
            "ears_stage": str(ears_stage or ""),
            "ears_score": float(ears_score or 0.0),
            "new_fact_ids": list(new_fact_ids or []),
            "new_entities": dict(new_entities or {}),
            "turn_count": int(turn_count),
            "notebook_events_before": int(notebook_events_before),
            "notebook_events_after": int(notebook_events_after),
            "mode": str(mode or ""),
            "deaf_s": (None if deaf_s is None else float(deaf_s)),
        })
        if int(turn_id) in self.open_ids:
            self.open_ids.remove(int(turn_id))
        return rec


def read_turns(path: str | os.PathLike) -> dict:
    """Read the log in order; report interrupted turns (BEGIN with no END).

    Returns {"records", "interrupted", "torn"} where interrupted is a
    list of {"turn_id", "text", "t"} in turn order. Raises
    TurnLog323Corrupt on any broken link that is not a torn final line.
    """
    log = TurnLog323(path)
    torn = bool(log.torn_tail)
    if not log.path.exists():
        return {"records": [], "interrupted": [], "torn": torn}
    raw = log.path.read_bytes().decode("utf-8")  # verified above
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if torn:
        lines = lines[:-1]
    records = [json.loads(line) for line in lines]
    begins = {int(r["turn_id"]): r for r in records
              if r.get("kind") == "BEGIN"}
    ended = {int(r["turn_id"]) for r in records if r.get("kind") == "END"}
    interrupted = [{"turn_id": tid, "text": begins[tid].get("text", ""),
                    "t": begins[tid].get("t", "")}
                   for tid in sorted(begins) if tid not in ended]
    return {"records": records, "interrupted": interrupted, "torn": torn}


def _nb_snapshot323(loop) -> tuple[int, set, dict]:
    """Read-only notebook snapshot (never writes)."""
    nb = getattr(loop, "nb", None)
    for obj in (nb, getattr(nb, "nb", None)):
        try:
            if obj is not None and hasattr(obj, "events"):
                return (len(obj.events), set(obj.facts),
                        dict(obj.entities))
        except (AttributeError, TypeError):
            continue
    return (-1, set(), {})


def _deaf_last323(loop):
    try:
        rows = getattr(loop, "deaf_log274", None)
        if isinstance(rows, list) and rows:
            return float(rows[-1].get("deaf_s"))
    except (AttributeError, TypeError, ValueError):
        pass
    return None


def _turn323(self, text: str) -> list[str]:
    """BEGIN before the saved turn runs, END after the reply exists.

    The saved (274 reply-first) turn stack is kept whole; the reply it
    returns is written to the log and returned unchanged.
    """
    log = self.turnlog323
    nb_before, facts_before, ents_before = _nb_snapshot323(self)
    turn_id = log.append_begin(text)
    log.last_turn_id = turn_id
    try:
        said = self._orig_turn323(text)
    except Exception:
        raise  # the BEGIN stays without an END: an interrupted turn
    nb_after, facts_after, ents_after = _nb_snapshot323(self)
    try:
        records = list(getattr(self, "last_records", []) or [])
    except TypeError:
        records = []
    new_entities = {eid: ents_after[eid]
                    for eid in set(ents_after) - set(ents_before)}
    try:
        ears = getattr(self, "ears", None)
        stage = getattr(ears, "last_stage", "")
        score = float(getattr(ears, "last_score", 0.0))
    except (AttributeError, TypeError, ValueError):
        stage, score = "", 0.0
    try:
        turn_count = int(self.counters.get("turns", 0))
    except (AttributeError, TypeError, ValueError):
        turn_count = 0
    log.append_end(
        turn_id, list(said) if said else [], records, stage, score,
        sorted(set(facts_after) - set(facts_before)), new_entities,
        turn_count, nb_before, nb_after, getattr(self, "mode", ""),
        _deaf_last323(self))
    return said


def install_turnlog323(loop, path: str | os.PathLike):
    """Wrap loop.turn as it is at install time (install LAST, idempotent)."""
    import types
    cur = getattr(loop, "__dict__", {}).get("turn", None)
    if (isinstance(cur, types.MethodType)
            and cur.__func__ is _turn323):
        return loop
    log = TurnLog323(path)
    loop.turnlog323 = log
    loop._orig_turn323 = loop.turn
    loop.turn = types.MethodType(_turn323, loop)
    if NOTE323 not in getattr(loop, "notes", []):
        loop.notes.append(NOTE323)
    return loop


DEFAULT_CONFIG323: dict = copy.deepcopy(A274.DEFAULT_CONFIG274)
DEFAULT_CONFIG323["daemon"]["module"] = (
    "Loop323Daemon (scripts/claude_nb323_turnlog.py) over Loop274Daemon "
    "with the durable hash-chained turn log installed LAST around "
    "loop.turn (<state_dir>/turns323.jsonl)")
DEFAULT_CONFIG323["exp323"] = {
    "base": "loop274 (scripts/claude_loop274_agent.py: 292t + "
            "listen-before-sleep step order + reply-first turn + "
            "deaf meter)",
    "added": ["durable hash-chained turn log (TurnLog323: one BEGIN "
              "before + one END after every turn, full text and reply, "
              "fsync + read-back, GENESIS chain, torn-tail repair; "
              "installed LAST around loop.turn so it captures the "
              "final reply)"],
    "touches": ["loop.turn wrapper only (log appends around the saved "
                "274 stack)"],
    "untouched": ["turn stack", "step() order", "reader stage",
                  "ear stages", "guards", "sleeper", "thinker",
                  "notebook", "daemon.log.jsonl"],
}


def build_agent323(cfg: dict | None = None):
    """Build the 274 agent shape with the turn log installed LAST."""
    loop = A274.build_agent274(cfg)
    install_turnlog323(loop, Path(str(loop.dir)) / TURNLOG_NAME323)
    if getattr(loop.turn, "__func__", None) is not _turn323:
        raise RuntimeError("323: turn log not installed LAST")
    return loop


class Loop323Daemon(A274.Loop274Daemon):
    """Loop274Daemon with the 323 turn log installed LAST around loop.turn."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        install_turnlog323(self.loop,
                           Path(str(self.root)) / TURNLOG_NAME323)


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp nb-323 (durable turn log)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG323)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG323)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop323Daemon(
            args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent323(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    _sys = sys
    _sys.exit(main())
