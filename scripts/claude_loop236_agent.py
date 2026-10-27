#!/usr/bin/env python3
"""Experiment 236 -- questions that use only a first name, on loop221.

loop236 = loop221 (scripts/fable_loop221_agent.py, read-only) + ONE change:
FirstName236Mixin sits OUTERMOST on the ears (outside TableAsk221Mixin) and
acts only on question turns (the turn ends in "?").

The change, per question turn:
  * Candidate T = a capitalised single word (>= 2 letters, not a closed
    question/function word) in the question, optionally possessive (T's),
    that is NOT followed by another capitalised word (so "Ysolde Kane" is
    never read as "Ysolde Marr"), that is not inside an occurrence of a
    stored name already written in full, and that is not itself a stored
    entity name or stored value (exact match wins).
  * Stored names = names of entities that are the SUBJECT of an active taught
    fact (fable_loop90_agent.notebook_triples), 2+ words, first word == T.
  * Exactly one stored name -> the question is heard with T replaced by that
    full name. The result is kept only if every action is read-only
    (ask / clarify / answer / unsure); otherwise the original turn is heard.
  * Two or more -> the original turn is heard; if every action it gives is
    read-only, the reply becomes the clarify
    "Which T do you mean: A or B?" (up to 3 names, sorted). No value, no
    write.
  * Anything else -> the original turn, untouched (byte-identical to 221).
Statements / teaches (no "?") never reach this code. A surname alone is out
of scope (only a first word is matched).

The 228 _src_of guard is installed at import and by the daemon mixin
(SrcGuardMixin228 first in the daemon bases).

Daemon launch (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop236_agent.py --daemon --dir DIR \\
    --config artifacts/claude-firstname236-20260922/loop236-config.json
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

from claude_fix228_srcguard import (  # noqa: E402 (REQUIRED 228 guard)
    SrcGuardMixin228, install_srcguard228)

install_srcguard228()

import fable_loop221_agent as L221  # noqa: E402 (base agent, read-only)
import fable_loop90_agent as L90  # noqa: E402 (live taught triples, read-only)

STAGE236 = "loop236-firstname"
READ_ONLY_ACTS236 = frozenset({"ask", "clarify", "answer", "unsure"})
USER_KEY236 = "USER"
# Capitalised words that are never read as a first name.
STOP236 = frozenset("""
who whom whose what where when why how which is are was were am do does did
can could will would may might shall should must tell the a an and or but
i in on at of for to from by with please has have had be been being if
then so not no yes any some my me mine our we us they them their he him his
she her hers it its this that these those there here hey hi hello okay ok
""".split())

_TOKEN236 = re.compile(r"(?<![\w'’-])([A-Z][A-Za-z-]+)((?:'s|’s|')?)(?![\w-])")


def _stored_names236(nb) -> tuple[set[str], set[str], dict[str, list[str]]]:
    """(subject names, all exact names/values, first word -> full names)."""
    subjects: set[str] = set()
    exact: set[str] = set()
    try:
        triples = L90.notebook_triples(nb)
    except Exception:  # noqa: BLE001
        triples = []
    for subj, _rel, val in triples:
        s = str(subj).strip()
        if s and s != USER_KEY236:
            subjects.add(s)
            exact.add(s.lower())
        v = str(val).strip().rstrip(".")
        if v:
            exact.add(v.lower())
    for name in getattr(nb, "entities", {}).values():
        if isinstance(name, str) and name.strip():
            exact.add(name.strip().lower())
    by_first: dict[str, list[str]] = {}
    for s in subjects:
        words = s.split()
        if len(words) >= 2:
            by_first.setdefault(words[0], []).append(s)
    return subjects, exact, by_first


def find_firstnames236(turn: str, nb) -> list[dict]:
    """Every first-name candidate in a question turn with its matches."""
    t = " ".join(str(turn).split())
    if not t.endswith("?") or nb is None:
        return []
    _subjects, exact, by_first = _stored_names236(nb)
    if not by_first:
        return []
    # spans already covered by a stored name written in full
    covered: list[tuple[int, int]] = []
    for full in {n for names in by_first.values() for n in names}:
        for m in re.finditer(r"(?<![\w-])" + re.escape(full) + r"(?![\w-])",
                             t):
            covered.append((m.start(), m.end()))
    out = []
    for m in _TOKEN236.finditer(t):
        word = m.group(1)
        if word.lower() in STOP236 or len(word) < 2:
            continue
        if any(a <= m.start() < b for a, b in covered):
            continue
        if not m.group(2):
            rest = t[m.end():]
            nxt = re.match(r"\s+([A-Za-z][\w'’-]*)", rest)
            if nxt and nxt.group(1)[0].isupper():
                continue  # "Ysolde Kane": a different full name
        if word.lower() in exact:
            continue  # exact match wins
        names = sorted(by_first.get(word, []))
        if not names:
            continue
        out.append({"word": word, "start": m.start(), "end": m.end(1),
                    "names": names})
    return out


def _read_only236(actions) -> bool:
    return isinstance(actions, list) and all(
        isinstance(a, dict) and a.get("act") in READ_ONLY_ACTS236
        for a in actions)


def clarify_text236(word: str, names: list[str]) -> str:
    shown = names[:3]
    if len(shown) == 2:
        opts = f"{shown[0]} or {shown[1]}"
    else:
        opts = ", ".join(shown[:-1]) + f" or {shown[-1]}"
    return f"Which {word} do you mean: {opts}?"


class FirstName236Mixin:
    """Outermost ears mixin: resolve a lone first name in a question."""

    def _mark236(self, how: str) -> None:
        try:
            self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                f"{STAGE236}-{how}", 1.0)
        except AttributeError:
            pass

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        t = " ".join(str(turn).split())
        nb = getattr(self, "nb", None)
        cands = find_firstnames236(t, nb) if t.endswith("?") else []
        if not cands:
            return super().hear(turn)  # type: ignore[misc]
        amb = [c for c in cands if len(c["names"]) >= 2]
        if amb:
            actions = super().hear(turn)  # type: ignore[misc]
            if not _read_only236(actions):
                return actions
            c = amb[0]
            self._mark236("clarify")
            return [{"act": "clarify", "stage": STAGE236,
                     "firstname236": c["word"],
                     "text": clarify_text236(c["word"], c["names"])}]
        new = t
        for c in sorted(cands, key=lambda c: -c["start"]):
            new = new[:c["start"]] + c["names"][0] + new[c["end"]:]
        actions = super().hear(new)  # type: ignore[misc]
        if _read_only236(actions):
            self._mark236("resolve")
            return actions
        return super().hear(turn)  # type: ignore[misc]


class Loop236Ears(FirstName236Mixin, L221.Loop221Ears):
    """Loop221Ears with the first-name stage outermost."""

    name = "loop236-firstname"


DEFAULT_CONFIG236: dict = copy.deepcopy(L221.DEFAULT_CONFIG221)
DEFAULT_CONFIG236["ears"]["stand_in"] = (
    L221.DEFAULT_CONFIG221["ears"]["stand_in"]
    + "; 236 first-name questions outermost (read-only)")
DEFAULT_CONFIG236["daemon"]["module"] = "Loop236Daemon (scripts/claude_loop236_agent.py)"


def _upgrade236(loop):
    ears, hops = loop.ears, 0
    while type(ears) is not L221.Loop221Ears:  # walk wrappers (Sleep130Ears)
        ears, hops = getattr(ears, "inner", None), hops + 1
        if ears is None or hops > 8:
            raise RuntimeError("Loop221Ears not found under loop.ears")
    ears.__class__ = Loop236Ears  # subclass, no new state
    loop.notes.append("loop236: loop221 + FirstName236Mixin outermost "
                      "(question turns only; writes untouched)")
    return loop


def build_agent236(cfg: dict | None = None):
    install_srcguard228()
    cfg = dict(DEFAULT_CONFIG236, **(cfg or {}))
    return _upgrade236(L221.build_agent221(cfg))


class Loop236Daemon(SrcGuardMixin228, L221.Loop221Daemon):
    """Loop221Daemon with the 228 guard and the 236 ears stage."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        _upgrade236(self.loop)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 236 first-name questions")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG236)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print("Wrote %s" % args.write_config)
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG236)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if not args.dir:
        ap.error("--daemon needs --dir")
    d = Loop236Daemon(args.dir, cfg=cfg, idle_seconds=args.idle_seconds)
    return d.run()


if __name__ == "__main__":
    sys.exit(main())
