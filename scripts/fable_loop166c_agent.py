#!/usr/bin/env python3
"""Experiment 166c -- loop166 + display-case fix, registered cleanly (Muse).

THE ONE CHANGE versus loop166 (nothing else changes: entity identity,
matching and writes are exactly loop166's): an entity whose stored
display name is all-lowercase (e.g. "biscuit", taught from lowercase
"my dog is biscuit") takes a later mention's surface form as its
rendered display ONLY when that mention
  (a) differs ONLY in letter case from the stored display,
  (b) is Title-case: first letter uppercase and NOT all letters
      uppercase (multi-token names: EVERY token Title-case; a single
      capital letter counts as Title-case), so ALL-CAPS shouts like
      "ANA" never become the display, and
  (c) stands as the whole name: a match immediately adjacent (spaces
      only) to another capitalised word is rejected -- it is a word
      inside a longer capitalised title ("Judo" inside "World Judo
      Championships", "Hobbit" inside "The Hobbit"), not a mention of
      this entity.

Clause (c) is 166b's adjacency guard, copied here with attribution
from scripts/fable_loop166b_agent.py:_pick_capitalised_surface (which
grew the guard after 166b's seal; 166b is therefore a registered FAIL
and stays FAIL). Clause (b) is the new 166c restriction: 166b's
guarded loop still upgrades "ana" -> "ANA" on the director probe
("My friend is ana." then "ANA's city is Rome." renders "ANA"), which
is wrong. Everything else is loop166's, by construction (mixin
subclass of loop166; same ears Loop166Ears; no 166/166b/162b/contract
file edited or touched).

Mechanism (agent layer only; the notebook event log stays
append-only): the contract has no display-rename event (ENTITY sets
the display at scripts/fable_notebook_contract.py:196-198 via
new_entity at :268-277; ALIAS at :279-286 only adds a lookup key and
never changes the display), so the fix keeps a per-loop override map
{entity_id: Title-case form} and rewrites said lines. Matching stays
case-insensitive (_norm at :116-117), entity ids/facts/writes are
untouched, so stored triples and fact_writes are byte-identical to
loop166 on every turn.
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


def _is_titlecase_token(tok: str) -> bool:
    """One whitespace-separated token is Title-case (spec clause b)."""
    core = tok.strip("'-.,!?;:()\"")
    if not core or not core[0].isalpha() or not core[0].isupper():
        return False
    if len(core) == 1:
        return True  # a single capital letter counts as Title-case
    return core != core.upper()  # first upper, not all upper ("Ana" yes)


def _is_titlecase_name(surf: str) -> bool:
    """Every token Title-case (multi-token names: each token checked)."""
    toks = surf.split()
    return bool(toks) and all(_is_titlecase_token(t) for t in toks)


def _pick_titlecase_surface(turn: str, display: str) -> str | None:
    """Return a Title-case surface form of display found in turn, else None.

    Attribution: match loop + adjacency guard copied from 166b's
    scripts/fable_loop166b_agent.py:_pick_capitalised_surface (guard:
    a match next to another capitalised word is rejected). ADDED in
    166c: the surface must satisfy _is_titlecase_name, so ALL-CAPS
    shouts ("ANA") never upgrade an all-lowercase display. Only fires
    when display is all-lowercase (has cased letters) and the turn
    contains a match differing ONLY in letter case. Every match is
    scanned so a shout does not shadow a later genuine Title-case
    mention in the same turn.
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
        if not _is_titlecase_name(surf):
            continue  # 166c: shouts ("ANA") and lowercase never qualify
        prev = prev_pat.search(turn[:match.start()])
        if prev is not None and prev.group(1)[:1].isupper():
            continue  # 166b guard: word inside a longer capitalised name
        nxt = next_pat.match(turn[match.end():])
        if nxt is not None and nxt.group(1)[:1].isupper():
            continue  # 166b guard, right side
        return surf
    return None


def apply_display_overrides(loop, turn: str) -> dict:
    """Update loop._dc166c {entity_id: Title-case form} from this turn."""
    overrides = getattr(loop, "_dc166c", None)
    if overrides is None:
        overrides = loop._dc166c = {}
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
        surf = _pick_titlecase_surface(turn, disp)
        if surf is not None:
            overrides[eid] = surf
    return overrides


def rewrite_display_case(line: str, overrides: dict, entities: dict) -> str:
    """Rewrite stored-lowercase displays to their Title-case form."""
    for eid, cap in overrides.items():
        disp = entities.get(eid)
        if disp is None or disp == cap:
            continue
        line = re.sub(r"(?<!\w)" + re.escape(disp) + r"(?!\w)", cap, line)
    return line


class Loop166cAgentLoop(L166.Loop166AgentLoop):
    """Loop166AgentLoop + Title-case-only display fix (this file only)."""

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


DEFAULT_CONFIG166C: dict = copy.deepcopy(L166.DEFAULT_CONFIG166)
DEFAULT_CONFIG166C["ears"]["stand_in"] = (
    "Loop166Ears (loop166 literally) + exp-166c agent-layer Title-case "
    "display fix: an all-lowercase entity display later mentioned with a "
    "Title-case case-only-different whole-name surface renders Title-case "
    "from that turn on (ALL-CAPS shouts and words inside longer "
    "capitalised titles never qualify); notebook log stays append-only, "
    "identity/matching/writes are loop166's exactly")
DEFAULT_CONFIG166C["daemon"]["module"] = "Loop166cDaemon (this file)"


def build_agent166c(cfg: dict | None = None) -> Loop166cAgentLoop:
    """Build the loop166 shape with the 166c display-case fix inside."""
    cfg = dict(DEFAULT_CONFIG166C, **(cfg or {}))
    loop = L150.build_agent150(cfg)
    loop.ears.__class__ = L166.Loop166Ears
    loop.ears.name = L166.Loop166Ears.name
    loop.__class__ = Loop166cAgentLoop
    loop._dc166c = {}
    return loop


class _DaemonBase166c(L166._DaemonBase166):
    """166's daemon base with the loop166c agent inside (mailbox same)."""

    _builder = staticmethod(build_agent166c)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.idle_seconds = float(idle_seconds)


class Loop166cDaemon(_DaemonBase166c):
    """Loop166Daemon shape with the loop166c agent inside (mailbox same)."""

    _builder = staticmethod(build_agent166c)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 166c display-case loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop166)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG166C to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG166C)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                            encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG166C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop166cDaemon(args.dir, cfg=cfg,
                                idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent166c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
