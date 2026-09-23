#!/usr/bin/env python3
"""Experiment 142 -- loop134 + exp-128's index as mixins (port, not new science).

Loop142 = loop134 lineage (loop121 teach coverage + loop113b N-hop router +
loop102 fallback + loop117 fixes) over 128's indexed notebook with the
142 fast question routing and teach-action patches from
scripts/fable_perf142_index.py. Same log format, same decision logic, same
replies; per-turn CPU flat in notebook size.

  Loop142Ears(FastQuestionMixin142, Loop134Ears): "?" turns take the
  index-backed router; every other turn runs the loop134 path untouched.
  Loop142Mouth = Loop134Mouth (underscore->space reply rendering, unchanged).
  Loop142AgentLoop = Loop134AgentLoop shape over IndexedLoopNotebook +
  FastReasoner142 (128's reasoner + the empty-subject guard) + tail-200
  state persist (128's recipe).
  Loop142Daemon = Loop134Daemon shape with incremental mailbox bookkeeping.

No existing file is edited; everything new lives here + fable_perf142_*.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop142_agent.py --daemon --dir DIR \\
    --config artifacts/fable-perf142-20260922/loop142-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (Protocols + base loop, read-only)
import fable_daemon74_run as D74  # noqa: E402 (mailbox helpers, read-only)
import fable_fix77_core as F77  # noqa: E402 (gate + reasoner + seal, read-only)
import fable_listening_m1 as L  # noqa: E402 (doorway, read-only)
import fable_loop134_agent as L134  # noqa: E402 (wrapped base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
from fable_perf128_index import (  # noqa: E402 (128's index, reused verbatim)
    _SAVE_TAIL,
    IndexedLoopNotebook,
)
from fable_perf142_index import (  # noqa: E402 (142 mixins, this experiment)
    FastQuestionMixin142,
    FastReasoner142,
    patch_chain142,
    patch_loop121_teach,
    _patch_relation,
)
from fable_wire51_adapters import (  # noqa: E402 (sleeper, read-only)
    HardGate46Sleeper)


class Loop142Ears(FastQuestionMixin142, L134.Loop134Ears):
    """Loop134Ears + index-backed "?" routing (MRO: fast mixin first)."""


Loop142Mouth = L134.Loop134Mouth


class Loop142AgentLoop(L134.Loop134AgentLoop):
    """Loop134AgentLoop shape over the indexed notebook; tail-persisted state."""

    def __init__(self, state_dir, *, ears=None, mouth=None, reasoner=None,
                 sleeper=None, thinker=None,
                 sleep_threshold: int = A.SLEEP_THRESHOLD) -> None:
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / A.STATE_NAME
        self.ears = ears or A.FakeEars()
        self.mouth = mouth or A.FakeMouth()
        self.reasoner = reasoner or FastReasoner142()
        self.sleeper = sleeper or A.StubSleeper()
        self.thinker = thinker
        self.sleep_threshold = int(sleep_threshold)
        self.notes: list[str] = []
        self.last_records: list[dict] = []
        self.parts90: dict = {}

        self.nb = IndexedLoopNotebook(self.dir / A.NOTEBOOK_DIR)
        if self.nb.torn_tail:
            self.nb.repair_torn_tail()
            self.notes.append("repaired a torn notebook tail")
            F77.verify_full(self.nb.root)
        self.listening = L.Listening(self.nb)
        _patch_relation(self)

        self.tick = 0
        self.mode = A.THINKING
        self.inbox: list[str] = []
        self.work_queue: list[str] = []
        self.experience: list[dict] = []
        self.question_pending: dict | None = None
        self.sleep_mark = 0
        self.counters = {"turns": 0, "writes": 0, "answers": 0,
                         "clarifications": 0, "sleeps": 0, "work": 0,
                         "thinks": 0}
        self._load()

    def _save(self) -> None:
        import json as _json
        import os as _os
        exp = (self.experience[-_SAVE_TAIL:]
               if len(self.experience) > _SAVE_TAIL else self.experience)
        payload = {"version": A.STATE_VERSION, "tick": self.tick,
                   "mode": self.mode, "inbox": self.inbox,
                   "work_queue": self.work_queue, "experience": exp,
                   "question_pending": self.question_pending,
                   "sleep_mark": self.sleep_mark, "counters": self.counters,
                   "listening_pending": self.listening.pending,
                   "listening_turn": self.listening.turn,
                   "sleep_threshold": self.sleep_threshold}
        tmp = self.dir / f"{A.STATE_NAME}.tmp{_os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(_json.dumps(payload, ensure_ascii=False,
                                     sort_keys=True))
            handle.flush()
            _os.fsync(handle.fileno())
        _os.replace(tmp, self.state_path)
        nb = getattr(self, "nb", None)
        if nb is not None and hasattr(nb, "advance_seal"):
            nb.advance_seal()


DEFAULT_CONFIG142: dict = copy.deepcopy(L134.DEFAULT_CONFIG134)
DEFAULT_CONFIG142["notebook"]["class"] = "IndexedLoopNotebook (perf128 index)"
DEFAULT_CONFIG142["ears"]["stand_in"] = (
    "Loop142Ears (FastQuestionMixin142 index-backed ?-router over " +
    L134.DEFAULT_CONFIG134["ears"]["stand_in"] + ")")
DEFAULT_CONFIG142["daemon"]["module"] = "Loop142Daemon (this file)"


def build_agent142(cfg: dict | None = None) -> Loop142AgentLoop:
    """Build the loop134 agent shape over the indexed notebook."""
    cfg = dict(DEFAULT_CONFIG142, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop142Mouth()
    reasoner = FastReasoner142()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop142AgentLoop(
        state_dir, ears=Loop142Ears(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    patch_chain142(chain)
    patch_loop121_teach(loop.ears)
    thinker, thinker_module = L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    return loop


class Loop142Daemon(L134.Loop134Daemon):
    """Loop134Daemon shape with the indexed agent + incremental bookkeeping."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
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
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent142(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)

    def process_file(self, path: Path) -> dict:
        import os as _os
        nb = self.loop.nb
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            D74._atomic_write(self.outbox / path.name,
                              L134.L102.UNREADABLE_MSG + "\n")
            try:
                _os.replace(path, self.done / path.name)
            except OSError:
                pass
            record = {"t": D74._now_iso(), "event": "turn-skipped-unreadable",
                      "file": path.name,
                      "reply": L134.L102.UNREADABLE_MSG,
                      "turn_count": int(self.loop.counters.get("turns", 0)),
                      "notebook_events": len(nb.events)}
            D74._append_log(self.log_path, record)
            return record
        before_nf = len(nb.facts)
        before_ne = len(nb.entities)
        said = self.loop.turn(text)
        records = list(getattr(self.loop, "last_records", []))
        new_facts = sorted(list(nb.facts.keys())[before_nf:])
        new_entities = {eid: nb.entities[eid]
                        for eid in sorted(list(nb.entities.keys())[before_ne:])}
        reply = " ".join(said) if said else "(nothing to say)"
        D74._atomic_write(self.outbox / path.name, reply + "\n")
        _os.replace(path, self.done / path.name)
        record = {"t": D74._now_iso(), "event": "turn", "file": path.name,
                  "turn_text": text.strip()[:200], "reply": reply[:500],
                  "records": records,
                  "ears_stage": getattr(self.loop.ears, "last_stage", ""),
                  "ears_score": getattr(self.loop.ears, "last_score", 0.0),
                  "new_fact_ids": new_facts, "new_entities": new_entities,
                  "turn_count": int(self.loop.counters.get("turns", 0)),
                  "notebook_events": len(nb.events)}
        D74._append_log(self.log_path, record)
        return record


def run_daemon142(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop142Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 142 indexed loop134")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop134)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG142 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG142)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG142)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon142(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent142(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
