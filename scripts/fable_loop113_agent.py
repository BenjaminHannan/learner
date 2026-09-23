#!/usr/bin/env python3
"""Experiment 113 -- ONE CHANGE on loop102: N-hop question composer (exp 103).

Diagnosis from exp 111: on the fresh 4-hop split the loop answered 131/200
CONFIDENTLY WRONG because loop102's ears chain asks questions through
bench73's 2-hop compose_question, which returns the first two hops of any
longer chain ("Derek Shepherd's spouse's creator is Frank Herbert.", gold
Arabic). Exp 103 proved B92.compose_n_hop walks full N-hop chains (193/200
on the fresh split via direct notebook feed) but it was never wired into
the loop.

THE ONE CHANGE (question side of the ears chain only; teach patterns and
everything else byte-identical to loop102):

  Loop113Ears(Loop102Ears) intercepts turns ending in "?" and routes:
    1. compose_n_hop(question, triples) -- the full-chain walker with its
       coverage gate. If it returns a frame, the walk is checked by the
       safety rule below; on pass the frame is asked, on fail the loop
       clarifies.
    2. else compose_question(question, triples) -- accepted ONLY for
       explicit single-hop / structural questions (Who-is-X-of-bare-Name,
       Who-verb-by-bare-Name, never-taught-relation probes). These ask
       exactly one hop or probe a missing link, so they can never be a
       truncation.
    3. else clarify (decline) -- never answer, never guess.

  SAFETY RULE ("never answer a shorter question than was asked"): a
  compose_n_hop frame is asked only if the notebook holds no further
  evidence about the walk-end entity under a compound subject the walk
  could not traverse (e.g. the walk ends at "Madonna" while the notebook
  holds ("director of Madonna", officeholder, ...) -- answering the
  1-hop prefix would answer a shorter question than asked). Chain nodes
  themselves (start + every walked object) are excluded, so genuine sinks
  still answer. On a compound-subject hit the loop clarifies.

  F1 hearsay screening still runs first on "?" turns (unchanged loop102
  behaviour). Non-"?" turns delegate to Loop102Ears.hear untouched, so the
  teach/correct/forget/qualifier path is identical (N4 regression marks).

No existing file is edited; everything new lives in this file.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop113_agent.py --daemon --dir DIR \\
    --config artifacts/fable-bench113-20260922/loop113-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (Protocols + base loop, read-only)
import fable_bench73_english_arm as B73  # noqa: E402 (2-hop composer, read-only)
import fable_bench92_english_arm as B92  # noqa: E402 (N-hop composer, read-only)
import fable_daemon74_run as D74  # noqa: E402 (mailbox helpers, read-only)
import fable_fix77_core as F77  # noqa: E402 (gate + reasoner + seal, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop102_agent as L102  # noqa: E402 (whole loop102 build, read-only)
import fable_notebook_contract as C  # noqa: E402 (contract, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper, NotebookThinker)

# Same miss text the loop90 ChainEars uses on total miss (decline, never guess).
CHAIN_MISS_TEXT = ("I didn't understand that. Could you say it another way?")

_NEVER_N_RE = re.compile(
    r"What is the never-taught relation (\d+) of (.+?)\??")
_NEVER_OF_RE = re.compile(
    r"What is the never-taught relation of the ([\w /-]+?) of (.+?)\??")
_WHO_OF_RE = re.compile(r"Who is the ([\w /-]+?) of (.+?)\??")
_WHO_BY_RE = re.compile(r"Who (\w+) by (.+?)\??")


def is_explicit_question(question: str) -> bool:
    """True for single-hop / structural probes (can never be a truncation).

    Mirrors compose_question's explicit branches: Who-is-<noun>-of-bare-Name
    (noun in the reversal map, bare-name gate), Who-<verb>-by-bare-Name
    (verb in the reversal map, bare-name gate), and the two never-taught
    relation probes (structural abstention probes).
    """
    q = " ".join(str(question).split())
    if _NEVER_N_RE.fullmatch(q) or _NEVER_OF_RE.fullmatch(q):
        return True
    m = _WHO_OF_RE.fullmatch(q)
    if m:
        label = m.group(1).strip().lower().replace(" ", "_")
        if (label in B73.REV_OF_NOUNS
                and B73._bare_name_ok(m.group(2).strip())):
            return True
    m = _WHO_BY_RE.fullmatch(q)
    if m:
        if (m.group(1).strip().lower() in B73.REV_BY_VERBS
                and B73._bare_name_ok(m.group(2).strip())):
            return True
    return False


def _walk_nodes(triples: list[tuple[str, str, str]], start: str,
                rels: list[str]) -> tuple[set[str], str | None]:
    """Chain node names (lowercased) + walk-end entity (None if unwalkable)."""
    nodes = {" ".join(str(start).split()).lower()}
    cur = start
    for rel in rels:
        objs = [o for (s, r, o) in triples if s == cur and r == rel]
        if not objs:
            return nodes, None
        cur = objs[-1]  # post-edit object: corrections supersede
        nodes.add(" ".join(str(cur).split()).lower())
    return nodes, cur


def compound_subject_hit(triples: list[tuple[str, str, str]], start: str,
                         rels: list[str]) -> tuple[str, str, str] | None:
    """Safety rule evidence: notebook knows more about the walk-end entity.

    Returns a (subject, relation, object) triple whose subject is a compound
    string containing the walk-end entity (e.g. "director of Madonna" when
    the walk ends at "Madonna") that the hop walk could not traverse --
    answering the walked prefix would answer a shorter question than asked.
    Chain nodes themselves are excluded (genuine sinks still answer).
    """
    nodes, end = _walk_nodes(triples, start, rels)
    if end is None:
        return None
    el = " ".join(str(end).split()).lower()
    for (s, r, o) in triples:
        sl = " ".join(str(s).split()).lower()
        if sl != el and sl not in nodes and el in sl:
            return (s, r, o)
    return None


def route_question(question: str,
                   triples: list[tuple[str, str, str]]
                   ) -> tuple[str, tuple[str, list[str]] | None, str]:
    """-> (decision, frame-or-None, source-tag).

    decision "ask": ask the frame (full chain or explicit single hop).
    decision "clarify": decline -- the composer cannot parse every hop.
    """
    frame = B92.compose_n_hop(question, triples)
    if frame is not None:
        hit = compound_subject_hit(triples, frame[0], list(frame[1]))
        if hit is None:
            return ("ask", (frame[0], list(frame[1])), "loop113-nhop")
        return ("clarify", None, "loop113-compound-guard")
    frame2 = B73.compose_question(question, triples)
    if frame2 is not None and is_explicit_question(question):
        return ("ask", (frame2[0], list(frame2[1])), "loop113-explicit")
    return ("clarify", None, "loop113-unparsed")


class Loop113Ears(L102.Loop102Ears):
    """Loop102Ears + the exp-103 N-hop composer on the question side.

    hear() phases: F1 hearsay screen first (unchanged); "?" turns route
    through route_question() (never the 2-hop truncator for open questions);
    every other turn delegates byte-identical to Loop102Ears.hear.
    """

    name = "loop113-nhop-prefilter"

    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if text and text.rstrip().endswith("?"):
            if L102.is_hearsay(text):  # F1 preserved on questions
                self.last_stage, self.last_score = "loop113-hearsay", 1.0
                return [{"act": "clarify", "text": L102.HEARSAY_MSG}]
            if self.nb is None:
                return self._delegate(turn)
            triples = L90.notebook_triples(self.nb)
            decision, frame, source = route_question(text, triples)
            if decision == "ask" and frame is not None:
                self.last_stage, self.last_score = source, 1.0
                return [{"act": "ask", "name": frame[0],
                         "relations": list(frame[1]), "stage": "loop113"}]
            self.last_stage, self.last_score = source, 1.0
            return [{"act": "clarify", "text": CHAIN_MISS_TEXT}]
        return super().hear(turn)


class Loop113AgentLoop(L102.Loop102AgentLoop):
    """Loop102AgentLoop (forget2 action included); ears differ, acts don't."""


DEFAULT_CONFIG113: dict = copy.deepcopy(L102.DEFAULT_CONFIG102)
DEFAULT_CONFIG113["ears"]["stand_in"] = (
    "Loop113Ears (N-hop question router + compound-subject guard) over "
    "Loop102Ears pre-filter over Loop96Ears = GuardedEars91 over "
    "ChainEars(bench73 template + FakeEars templates); teach path identical "
    "to loop102")
DEFAULT_CONFIG113["daemon"]["module"] = "Loop113Daemon (this file)"


def build_agent113(cfg: dict | None = None) -> L102.Loop102AgentLoop:
    """Build the loop102 agent shape with Loop113Ears on the question side."""
    cfg = dict(DEFAULT_CONFIG113, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    reasoner = F77.QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4102)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop113AgentLoop(
        state_dir, ears=Loop113Ears(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
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


class Loop113Daemon(L102.Loop102Daemon):
    """Loop102Daemon shape with the loop113 agent inside (mailbox identical)."""

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
        self.loop = build_agent113(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon113(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop113Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 113 N-hop loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop102)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG113 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG113)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG113)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon113(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent113(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
