#!/usr/bin/env python3
"""Experiment 166b -- loop166 + display-case fix (keep a name's capital letter).

THE ONE CHANGE versus loop166 (nothing else changes: entity identity,
matching and writes are exactly loop166's): when an entity whose stored
display name is all-lowercase (e.g. "biscuit", taught from lowercase
"my dog is biscuit") is later mentioned with a capitalised surface form
that differs ONLY in letter case (e.g. "Biscuit's color is brown"), the
rendered display name becomes the capitalised form from that turn on.

Mechanism (agent layer only; the notebook event log stays append-only):
the contract has no display-rename event (ENTITY sets the display at
scripts/fable_notebook_contract.py:196-198 via new_entity at :268-277;
ALIAS at :279-286 only adds a lookup key and never changes the display),
so the fix keeps a per-loop override map {entity_id: capitalised form}
and rewrites said lines. Matching stays case-insensitive
(_norm at :116-117), entity ids/facts/writes are untouched, so stored
triples and fact_writes are byte-identical to loop166 on every turn.

Step 1 (file:line, where loop166/the contract sets and renders display):
- sets: Notebook.new_entity (scripts/fable_notebook_contract.py:268-277)
  stores name.strip() as the ENTITY event name; _apply (:196-198) sets
  entities[entity_id] = name. Value entities are created with the typed
  surface in Listening._person (scripts/fable_listening_m1.py:50-57,
  called from _teach at :115), so "biscuit" stays lowercase.
- renders: Notebook._show (:257-258) returns entities[entity]; assert_fact
  text (:349), ask answers/MISSING subjects (:390-420), and
  FakeMouth.say (scripts/fable_agent_loop.py:165-168) all copy the stored
  display verbatim. Loop166's reply rewrite
  (scripts/fable_loop166_agent.py:57-77) only maps USER -> your/Your.

No existing file is edited (no 166/162b/162/contract file touched).
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

import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)
import fable_loop166_agent as L166  # noqa: E402 (wrapped base agent, read-only)


def _pick_capitalised_surface(turn: str, display: str) -> str | None:
    """Return a capitalised surface form of display found in turn, else None.

    Only fires when display is all-lowercase (has cased letters) and the
    turn contains a match differing ONLY in letter case whose first letter
    is uppercase. Prefers a capitalised match when several exist. A match
    embedded in a longer capitalised run ("Judo" inside "World Judo
    Championships", "Hobbit" inside "The Hobbit") is NOT a mention of this
    entity, so matches immediately adjacent (spaces only) to another word
    starting with an uppercase letter are rejected.
    """
    if not display or display != display.lower():
        return None
    if display.lower() == display.upper():
        return None  # no cased letters: nothing to fix
    pattern = re.compile(r"(?<!\w)" + re.escape(display) + r"(?!\w)",
                         re.IGNORECASE)
    prev_pat = re.compile(r"([A-Za-z]+)\s*$")
    next_pat = re.compile(r"^\s*([A-Za-z]+)")
    for match in pattern.finditer(turn):
        surf = match.group(0)
        if surf == display:
            continue
        if surf.lower() != display.lower():
            continue
        if not surf[:1].isupper():
            continue
        prev = prev_pat.search(turn[:match.start()])
        if prev is not None and prev.group(1)[:1].isupper():
            continue
        nxt = next_pat.match(turn[match.end():])
        if nxt is not None and nxt.group(1)[:1].isupper():
            continue
        return surf
    return None


def apply_display_overrides(loop, turn: str) -> dict:
    """Update loop._dc166b {entity_id: capitalised form} from this turn."""
    overrides = getattr(loop, "_dc166b", None)
    if overrides is None:
        overrides = loop._dc166b = {}
    nb = getattr(loop, "nb", None)
    if nb is None or not turn:
        return overrides
    try:
        entities = dict(nb.entities)
    except Exception:  # noqa: BLE001 -- never break the loop on render
        return overrides
    for eid, disp in entities.items():
        if eid in overrides:
            continue
        surf = _pick_capitalised_surface(turn, disp)
        if surf is not None:
            overrides[eid] = surf
    return overrides


def rewrite_display_case(line: str, overrides: dict, entities: dict) -> str:
    """Rewrite stored-lowercase displays to their capitalised form."""
    for eid, cap in overrides.items():
        disp = entities.get(eid)
        if disp is None or disp == cap:
            continue
        line = re.sub(r"(?<!\w)" + re.escape(disp) + r"(?!\w)", cap, line)
    return line


class Loop166bAgentLoop(L166.Loop166AgentLoop):
    """Loop166AgentLoop + display-case fix (this file only)."""

    def _listening_tick(self):  # type: ignore[no-untyped-def]
        event = super()._listening_tick()
        try:
            turn = event.get("detail", {}).get("turn", "")
        except Exception:  # noqa: BLE001
            return event
        try:
            overrides = apply_display_overrides(self, turn or "")
            if overrides:
                entities = dict(self.nb.entities)
                event["said"] = [rewrite_display_case(line, overrides,
                                                      entities)
                                 for line in event.get("said", [])]
        except Exception:  # noqa: BLE001
            pass
        return event


DEFAULT_CONFIG166B: dict = copy.deepcopy(L166.DEFAULT_CONFIG166)
DEFAULT_CONFIG166B["ears"]["stand_in"] = (
    "Loop166Ears (loop166 literally) + exp-166b agent-layer display-case "
    "fix: an all-lowercase entity display later mentioned with a "
    "capitalised case-only-different surface renders capitalised from "
    "that turn on; notebook log stays append-only, identity/matching/"
    "writes are loop166's exactly")
DEFAULT_CONFIG166B["daemon"]["module"] = "Loop166bDaemon (this file)"


def build_agent166b(cfg: dict | None = None) -> Loop166bAgentLoop:
    """Build the loop166 shape with the 166b display-case fix inside."""
    cfg = dict(DEFAULT_CONFIG166B, **(cfg or {}))
    loop = L150.build_agent150(cfg)
    loop.ears.__class__ = L166.Loop166Ears
    loop.ears.name = L166.Loop166Ears.name
    loop.__class__ = Loop166bAgentLoop
    loop._dc166b = {}
    return loop


class _DaemonBase166b(L166._DaemonBase166):
    """166's daemon base with the loop166b agent inside (mailbox same)."""

    _builder = staticmethod(build_agent166b)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.idle_seconds = float(idle_seconds)


class Loop166bDaemon(_DaemonBase166b):
    """Loop166Daemon shape with the loop166b agent inside (mailbox same)."""

    _builder = staticmethod(build_agent166b)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 166b display-case loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop166)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG166B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG166B)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                            encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG166B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop166bDaemon(args.dir, cfg=cfg,
                                idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent166b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
