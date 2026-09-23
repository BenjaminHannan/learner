#!/usr/bin/env python3
"""Merge 138n -- 138m + the reading line: 221 (table questions), 221b
(stored-relation fallback), 221c (question normalisation), 229 (table
teaches), 237 (relation table v1.1 reader; NOT 237b), 232c (multi-word
names in verb turns; replaces 232b) and 236 (first-name resolution).
New file only; every piece module is imported read-only and its OWN
classes are reused unchanged.

EARS (outermost first):
  221c QNorm221cMixin         question normalisation; re-hears the rewrite
                              only when it has one table reading and the
                              result is write-free
  236  FirstName236Mixin      a lone first name -> the one stored full name
                              (several -> "Which T do you mean: ...?");
                              merge glue G1 skips "First <particle> Last"
  221b StoredRel221bMixin     stored-relation fallback on base-missed or
                              abstaining one-hop asks (taught keys only)
  237  TableAsk237Mixin       relation-table question reader (221's stage,
                              reading table v1.1)
  229  TableTeach229Mixin     (merge glue G2: true no-save reason for a
                              232c name) table teaches on statements the WHOLE 138m
                              ears stack missed (not-understood clarify
                              only); the canonical sentence goes back
                              through the whole 138m ears stack (209 ears
                              screen, 222/215 gates, 167b, 139b, 150 ...),
                              then screen_turn209 again, as on its own stack
  Loop138lEars                138m's ears, unchanged
     ... 138i list ... ChainOf174, Typo165,
  232c Verb232Mixin           (with install232c's subject rule) exactly
                              where 232 puts it: after 174/165, before 167b
     ValueScreen167b ...      rest of 138i's list, unchanged

LOOP: Loop138mAgentLoop's full order, plus 232's _act parity step placed
directly above Loop138iAgentLoop (where it sits on 232c's own stack).
The 224/224c instance wrappers are installed by 138m's own build hook.

WHY this order (the full interaction analysis is in
design/v3/30-modes/138n-merge-opus.md):
  * every reading layer is an EARS stage, so everything 138m's LOOP layers
    decide (212/216 gates, 227c identity, 219/230c name line, 233, 234,
    224c declines, 226 sources) still runs around it exactly as in 138m;
  * question layers act only on turns ending in "?" and emit only
    ask / clarify actions -> questions never write;
  * 229 fires only when the whole 138m ears stack returned nothing but its
    not-understood clarify, so a gate that STOPS a write (209 split
    clarify, 222/215 refusals, 167b no-write clarify, 150 subject veto)
    is never overridden: those return their own clarify, not the
    not-understood one; and 229's own write goes through every one of
    those gates again;
  * 221c outermost so every reader below sees the normalised question;
    236 above 221b/237 so they see the resolved full name; 221b above 237
    as on its own stack (it only acts when the table reader missed or
    would abstain);
  * inferred facts are never stored: 237/221 inverse answers are clarify
    texts labelled "(worked out backwards)", 221b/236 only ask.

How the classes get in: as in 138m, build_agent138j (read-only) builds
L138J.Loop138jEars / L138J.Loop138jAgentLoop by module-global name; this
file swaps them (and L138J.build_agent138j for 138m's 224/224c hook) only
while the agent is built (process-local, restored in finally).
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

import claude_fix228_srcguard as G228  # noqa: E402 (228 guard, read-only)

G228.install_srcguard228()  # 228 first, at import

import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as M138  # noqa: E402 (base, read-only)
import claude_loop221b_agent as L221B  # noqa: E402 (piece, read-only)
import claude_loop221c_agent as L221C  # noqa: E402 (piece, read-only)
import claude_loop229_agent as L229  # noqa: E402 (piece, read-only)
import claude_loop232c_agent as L232C  # noqa: E402 (piece, read-only)
import claude_loop236_agent as L236  # noqa: E402 (piece, read-only)
import claude_loop237_agent as L237  # noqa: E402 (piece, read-only)
import fable_fix221_tableask as T221  # noqa: E402 (piece, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)

L232 = L232C.L232
L232C.install232c()  # 232c subject rule rebound into 232 (idempotent)

TABLE_PATH138N_ASK = str(L237.TABLE_PATH237)   # 237: v1.1 for questions
TABLE_PATH138N_TEACH = str(T221.TABLE_PATH221)  # 229: v1, as sealed


# ------------------------------------------------------------ merge glue
# Two cross-piece fixes found in the M1 pilot (design note, section G).
# Neither can add a write: G1 only drops a first-name candidate (the turn
# is then heard exactly as by the layers below), G2 only rewrites the
# REASON text of a 229 no-save clarify.
_PART138N = L232C.PARTICLES232C
_AFTER_PART138N = re.compile(
    r"\s+((?:[a-z]+\s+){1,%d})([A-Z][\w'\u2019-]*)"
    % L232C.MAX_PARTICLE_RUN232C)


def _before_particle_name138n(t: str, end: int) -> bool:
    """True when the word ending at `end` is followed by 232c name
    particles and then a capitalised word ("Sela ben Tamsin")."""
    m = _AFTER_PART138N.match(t[end:])
    if not m:
        return False
    return all(w in _PART138N for w in m.group(1).split())


class FirstName138nMixin(L236.FirstName236Mixin):
    """G1 (236 x 232c): 236 skips a first word that begins a multi-word
    name with a 232c particle ("Sela ben Tamsin" is a different full name,
    not a lone "Sela"). Otherwise 236's own hear, unchanged."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        t = " ".join(str(turn).split())
        nb = getattr(self, "nb", None)
        cands = L236.find_firstnames236(t, nb) if t.endswith("?") else []
        keep = [c for c in cands
                if not _before_particle_name138n(t, c["end"])]
        if len(keep) == len(cands):
            return super().hear(turn)  # 236 exactly as sealed
        if not keep:  # skip 236 entirely: the layers below hear the turn
            return super(L236.FirstName236Mixin, self).hear(turn)
        amb = [c for c in keep if len(c["names"]) >= 2]
        below = super(L236.FirstName236Mixin, self).hear
        if amb:
            actions = below(turn)
            if not L236._read_only236(actions):
                return actions
            c = amb[0]
            self._mark236("clarify")
            return [{"act": "clarify", "stage": L236.STAGE236,
                     "firstname236": c["word"],
                     "text": L236.clarify_text236(c["word"], c["names"])}]
        new = t
        for c in sorted(keep, key=lambda c: -c["start"]):
            new = new[:c["start"]] + c["names"][0] + new[c["end"]:]
        actions = below(new)
        if L236._read_only236(actions):
            self._mark236("resolve")
            return actions
        return below(turn)


class TableTeach138nMixin(L229.TableTeach229Mixin):
    """G2 (229 x 232c): when 229 refuses because the subject "does not look
    like a name" but 232c's subject rule accepts that name, give the true
    reason instead (the value check's reason, else "I could not store it
    that way"). Text only: the action stays a no-save clarify."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)
        if not (isinstance(actions, list) and len(actions) == 1
                and isinstance(actions[0], dict)
                and actions[0].get("table229") == "nosave"):
            return actions
        text = str(actions[0].get("text", ""))
        t = " ".join(str(turn).split())
        tb = L229.load_table229(getattr(self, "table229_path", None))
        for r_ in L229.table_teach_readings229(t, tb):
            x = r_["X"]
            if x == L229.USER229:
                continue
            tail = f", but {x} does not look like a name."
            if not text.endswith(tail) or \
                    L229.subject_ok229(x) is None or \
                    not L232C.subject_ok232c(x):
                continue
            why = L229.value_ok229(tb["rels"][r_["rel"]], r_["Y"], r_["how"])
            why = why or "I could not store it that way"
            return [dict(actions[0], merge138n="reason232c",
                         text=text[:-len(tail)] + f", but {why}.")]
        return actions


class Loop138nEars(L221C.QNorm221cMixin, FirstName138nMixin,
                   L221B.StoredRel221bMixin, L237.TableAsk237Mixin,
                   TableTeach138nMixin, M138.Loop138mEars,
                   L232.Verb232Mixin, L138I.S167B.ValueScreen167bMixin):
    """138m ears + the reading line (see the module docstring)."""

    name = "loop138n-reading"
    table221_path = TABLE_PATH138N_ASK
    table229_path = TABLE_PATH138N_TEACH


class Cap138nMixin:
    """G3 (221/237 USER template x 138m renderer): a table-read answer about
    the user comes back as "your city is ..." (lower-case first letter, as
    on 237's own stack). Capitalise that one word when it opens a reply.
    Text only; nothing else in the reply changes."""

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
        out = super().turn(text)  # type: ignore[misc]
        return [("Y" + r[1:]) if isinstance(r, str) and r.startswith("your ")
                else r for r in out]


class Loop138nAgentLoop(Cap138nMixin, M138.Loop138mAgentLoop,
                        L232.Loop232AgentLoop):
    """138m loop + 232's pending-drop parity step above Loop138iAgentLoop
    (+ G3 capital "Your" on top)."""


def _mro_names(cls) -> list[str]:
    return [c.__name__ for c in cls.__mro__]


_E = _mro_names(Loop138nEars)
assert _E[:9] == ["Loop138nEars", "QNorm221cMixin", "FirstName138nMixin",
                  "FirstName236Mixin", "StoredRel221bMixin",
                  "TableAsk237Mixin", "TableAsk221Mixin",
                  "TableTeach138nMixin", "TableTeach229Mixin"], _E
assert _E[9] == "Loop138lEars", _E
_i = _E.index("Verb232Mixin")
assert _E[_i - 2:_i + 2] == ["ChainOf174Mixin", "Typo165Mixin",
                             "Verb232Mixin", "ValueScreen167bMixin"], _E
_L = _mro_names(Loop138nAgentLoop)
_M = _mro_names(M138.Loop138mAgentLoop)
_j = _L.index("Loop232AgentLoop")
assert _L[1] == "Cap138nMixin", _L
assert _L[2:_j] == _M[:_M.index("Loop138iAgentLoop")], _L
assert _L[_j + 1] == "Loop138iAgentLoop", _L
assert _L[_j + 2:] == _M[_M.index("Loop138iAgentLoop") + 1:], _L


def _with_138n(fn, *args, **kwargs):
    with M138._Swap([(L138J, "Loop138jEars", Loop138nEars),
                     (L138J, "Loop138jAgentLoop", Loop138nAgentLoop),
                     (L138J, "build_agent138j",
                      M138._build138j_plus224c)]):
        return fn(*args, **kwargs)


NOTE138N = ("loop138n: loop138m + reading line (221c normalise, 236 first "
            "names, 221b stored-relation fallback, 237 table v1.1 reader, "
            "229 table teaches, 232c multi-word verb names)")

DEFAULT_CONFIG138N: dict = copy.deepcopy(M138.DEFAULT_CONFIG138M)
DEFAULT_CONFIG138N["daemon"]["module"] = (
    "Loop138nDaemon (scripts/claude_loop138n_agent.py) over Loop138kDaemon")
DEFAULT_CONFIG138N["table221_path"] = TABLE_PATH138N_ASK
DEFAULT_CONFIG138N["table229_path"] = TABLE_PATH138N_TEACH
DEFAULT_CONFIG138N["merge138n"] = {
    "base": "loop138m (scripts/claude_loop138m_agent.py)",
    "added": ["221 relation-table questions (fable_fix221_tableask)",
              "237 table v1.1 reader (claude_loop237_agent.TableAsk237Mixin)",
              "221b stored-relation fallback (claude_loop221b_agent)",
              "221c question normalisation (claude_loop221c_agent)",
              "236 first-name resolution (claude_loop236_agent)",
              "229 table teaches on base-missed statements, table v1 "
              "(claude_loop229_agent)",
              "232c multi-word verb names (claude_loop232c_agent over "
              "claude_loop232_agent)"],
    "ears_mro": _E[:11] + ["...", "ChainOf174Mixin", "Typo165Mixin",
                          "Verb232Mixin", "ValueScreen167bMixin", "..."],
    "loop_extra": "Loop232AgentLoop directly above Loop138iAgentLoop; "
                  "Cap138nMixin (G3) outermost",
    "glue": ["G1 236 skips 'First <232c particle> Last' candidates",
             "G2 229 no-save reason for a 232c-valid subject",
             "G3 capital 'Your' at the start of a reply"],
}


def _set_paths(loop, cfg: dict) -> None:
    inner = getattr(loop, "_inner138j_ears", None)
    if inner is None:
        raise RuntimeError("138n: inner ears handle missing")
    inner.table221_path = cfg.get("table221_path") or TABLE_PATH138N_ASK
    inner.table229_path = cfg.get("table229_path") or TABLE_PATH138N_TEACH


def _check(loop):
    M138._check(loop)  # 138m's own checks (224c, 228, 220 notebook)
    loop.notes.pop()   # drop 138m's note; ours follows
    if not isinstance(loop, Loop138nAgentLoop):
        raise RuntimeError("138n: loop is not Loop138nAgentLoop")
    inner = getattr(loop, "_inner138j_ears", None)
    if not isinstance(inner, Loop138nEars):
        raise RuntimeError("138n: inner ears are not Loop138nEars")
    if L232.subject_ok232 is not L232C.subject_ok232c:
        raise RuntimeError("138n: 232c subject rule not installed")
    loop.notes.append(M138.NOTE138M)
    loop.notes.append(NOTE138N)


def build_agent138n(cfg: dict | None = None):
    G228.install_srcguard228()
    L232C.install232c()
    cfg = dict(DEFAULT_CONFIG138N, **(cfg or {}))
    loop = _with_138n(L138K.build_agent138k, cfg)
    _set_paths(loop, cfg)
    _check(loop)
    return loop


class _Guard138n(G228.SrcGuardMixin228):
    """SrcGuardMixin228, first in the daemon's MRO (installs the guard)."""


class Classes138nMixin:
    """Daemon mixin: 138k's daemon __init__ with the 138n classes and the
    224c-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        L232C.install232c()
        _with_138n(super().__init__, *args, **kwargs)
        cfg = dict(DEFAULT_CONFIG138N, **(getattr(self, "cfg", None) or {}))
        _set_paths(self.loop, cfg)
        _check(self.loop)


class Loop138nDaemon(_Guard138n, Classes138nMixin, L138K.Loop138kDaemon):
    """Loop138kDaemon + the 138l/138m pieces + the 138n reading line."""


def run_daemon138n(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    return Loop138nDaemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    parser = argparse.ArgumentParser(description="Merge 138n (138m + 7)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138N)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG138N)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138n(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        if not args.state_dir:
            parser.error("--once needs --state-dir (never the repo notebook)")
        cfg["state_dir"] = args.state_dir
        loop = build_agent138n(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
