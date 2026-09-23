#!/usr/bin/env python3
"""Experiment 180b -- silent case-insensitive known-name match on loop138h.

Base: loop138h (scripts/fable_loop138h_agent.py, read-only). ONE CHANGE,
one mechanism, outermost ears + display:

  Any token or possessive in a turn that equals, ignoring case, a name
  ALREADY IN THE NOTEBOOK (entity names: taught+active subjects and
  single-token entity values, including the user's own name) is resolved
  to that stored name BEFORE parsing; replies render every known name in
  its stored casing.

Consequences (all silent -- Ben's typo ruling, no "Did you mean"):

  - "who is oda's boss?" -> parses as "who is Oda's boss?" and replies
    "Oda's boss is Pim." (byte-identical to the capitalised twin).
  - 165's "Who is toms boss?" path replies "Tom's boss is Lee." (the
    inner 165 stage still owns the missing apostrophe; the display pass
    renders the stored casing).
  - A lowercase teach naming only known entities ("lyle's boss is ivo.")
    saves at once with exactly the capitalised twin's events (no second
    entity differing only in case can be created: the parse never sees
    the lowercase surface).
  - A turn about an already-stored fact keeps the base reply
    ("I already have that.").
  - Unknown lowercase words are never capitalised or guessed ("gus",
    "bob", "kofis" pass through byte-identical).
  - Common words ("will", "may", "rose", "mark") are touched only if
    they ARE notebook names (single-token value rule has the 180-D1
    guard: multi-word values never contribute names, so determiners
    like "the" can never misfire).
  - Pretend "say ..." turns pass through fully untouched (the say echo
    quotes the user's bytes exactly, 0 writes), byte-identical to 138h.
  - One guard (166c ownership, sealed display fix untouched): a token
    that is not all-lowercase is never rewritten to an all-lowercase
    canonical ("Biscuit" stays "Biscuit" when the notebook holds
    "biscuit"); the display path honours the loop's 166c override map.

No existing file is edited; loop138h is imported read-only. Differs
from loop180 (scripts/fable_loop180_agent.py, registered FAIL, do NOT
reuse): 180 re-cased only unparsed turns and gated teaches behind a
"Did you mean" confirm; 180b resolves known names before parsing on
EVERY non-say turn (asks included) and never confirms.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop180b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-case180b-20260922/loop180b-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (Protocols + thresholds, read-only)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_doubt146b_store as D146B  # noqa: E402 (146d doubt mixin, read-only)
import fable_fix137d_frame as F137D  # noqa: E402 (say-marker, read-only)
import fable_fix173_username as N173  # noqa: E402 (user name, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop102_agent as L102  # noqa: E402 (HEARSAY_MSG, read-only)
import fable_loop134_agent as L134  # noqa: E402 (138b turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (router + decline, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (donor stack, read-only)
import fable_loop138f_agent as L138F  # noqa: E402 (wrapped stack, read-only)
import fable_loop138g_agent as L138G  # noqa: E402 (wrapped stack, read-only)
import fable_loop138h_agent as L138H  # noqa: E402 (base stack, read-only)
import fable_loop90_agent as L90B  # noqa: E402 (chain + thinker, read-only)
import fable_loop96_agent as L96  # noqa: E402 (inner chain ears, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_perf142_index import (  # noqa: E402 (142 fast pieces, read-only)
    patch_chain142,
    patch_loop121_teach,
)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# THE 149 PIECE, applied at import (this process only, no file edited).
WM149.apply_wordmatch()

# Re-assert the loop134 shouted-possessive override in this process.
A._APOS = L134._APOS_SHOUTED_134

_WORD180B_RE = re.compile(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)?")


def _split_tokens180b(text: str) -> list[tuple[str, bool]]:
    """Split into (chunk, is_word) preserving every byte of the original."""
    parts: list[tuple[str, bool]] = []
    pos = 0
    for m in _WORD180B_RE.finditer(str(text)):
        if m.start() > pos:
            parts.append((text[pos:m.start()], False))
        parts.append((m.group(0), True))
        pos = m.end()
    if pos < len(text):
        parts.append((text[pos:], False))
    return parts


def _stem180b(word: str) -> tuple[str, str]:
    """Return (stem, suffix) splitting one trailing possessive 's/'s/'."""
    low = word.lower()
    for suf in ("'s", "\u2019s", "'"):
        if low.endswith(suf) and len(word) > len(suf):
            return word[:-len(suf)], word[-len(suf):]
    return word, ""


def _is_lower_name(s: str) -> bool:
    """True iff s is all-lowercase (has cased letters)."""
    return s == s.lower() and s != s.upper()


def notebook_names180b(nb, overrides=None) -> dict[str, str]:
    """Map lowercased name -> canonical casing (read-only).

    Names = taught+active subjects (entity displays, single-token only)
    and single-token values (multi-word values are phrases, not names --
    the 180-D1 guard, so a determiner such as "the" from "The Glass
    Orchard" never becomes a name), plus the user's own name.
    First-seen casing wins, EXCEPT an entity's 166c display override
    (agent-layer Title-case form for an all-lowercase stored display)
    always wins for that entity: the override IS the agent's canonical
    render, so resolving to the raw lowercase display would undo the
    sealed 166c display fix. Callers on the input path pass no
    overrides (a lowercase mention must parse exactly as the base sees
    it, keeping stored events identical); the display path passes the
    loop's _dc166c map.
    """
    names: dict[str, str] = {}
    entities: dict = {}
    try:
        entities = dict(nb.entities)
    except Exception:
        entities = {}
    try:
        ov = dict(overrides or {})
    except Exception:
        ov = {}
    for eid, disp in entities.items():
        if (isinstance(disp, str) and disp.strip()
                and not re.search(r"\s", disp.strip())):
            canon = ov.get(eid, disp.strip())
            if isinstance(canon, str) and canon.strip() and not re.search(
                    r"\s", canon.strip()):
                key = disp.strip().lower()
                if key and key not in names:
                    names[key] = canon.strip()
    try:
        triples = L90.notebook_triples(nb)
    except Exception:
        triples = []
    for _subj, _rel, val in triples:
        if isinstance(val, str) and val.strip() and not re.search(
                r"\s", val.strip()):
            vstem, _ = _stem180b(val.strip())
            vkey = vstem.lower()
            if vkey and vkey not in names:
                names[vkey] = vstem
    try:
        knob = N173.current_name(nb)
    except Exception:
        knob = None
    if knob and not re.search(r"\s", str(knob).strip()):
        kstem, _ = _stem180b(str(knob).strip())
        if kstem.lower() not in names:
            names[kstem.lower()] = kstem
    return names


def resolve180b(text: str, names: dict[str, str]) -> str:
    """Resolve any token/possessive matching a known name (case-insensitively)
    to its canonical casing. Every other byte is preserved.

    One guard (166c ownership): a token that is NOT all-lowercase is
    never rewritten to an all-lowercase canonical. A Title-case mention
    of an all-lowercase-stored name ("Biscuit" for stored "biscuit") is
    the sealed 166c display-upgrade path: the base stores the surface
    as typed and renders Title-case, and 180b must do exactly the same
    (otherwise stored events and sealed replies would move).
    """
    if not names:
        return str(text)
    out: list[str] = []
    for chunk, is_word in _split_tokens180b(text):
        if not is_word:
            out.append(chunk)
            continue
        stem, suffix = _stem180b(chunk)
        canon = names.get(stem.lower())
        if canon is not None and stem != canon:
            if _is_lower_name(canon) and stem != stem.lower():
                out.append(chunk)  # 166c owns this direction
            else:
                out.append(canon + suffix)
        else:
            out.append(chunk)
    return "".join(out)


def is_say180b(turn: str) -> bool:
    """True iff the turn is a pretend say-group turn (echo path)."""
    try:
        return F137D.say_marker(turn) is not None
    except Exception:
        return False


class Case180bMixin:
    """Outermost ears: resolve known names (any case) before parsing."""

    name = "loop180b-case"

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-untyped-def]
        if is_say180b(turn):
            return super().hear(turn)  # pretend echo: bytes untouched
        try:
            names = notebook_names180b(getattr(self, "nb", None))
        except Exception:
            return super().hear(turn)
        try:
            fixed = resolve180b(turn, names)
        except Exception:
            return super().hear(turn)
        if fixed == str(turn):
            return super().hear(turn)
        return super().hear(fixed)


class Loop180bEars(Case180bMixin, L138H.Loop138hEars):
    """Loop138hEars + outermost silent known-name case resolution."""

    name = "loop180b-ears"


class Loop180bAgentLoop(L138H.Loop138hAgentLoop):
    """Loop138hAgentLoop + stored-casing display pass on said lines."""

    def _listening_tick(self):  # type: ignore[no-untyped-def]
        try:
            pre_turn = self.inbox[0] if self.inbox else ""
        except Exception:  # noqa: BLE001
            pre_turn = ""
        event = super()._listening_tick()
        try:
            if is_say180b(pre_turn):
                return event  # pretend echo: bytes untouched
            # Rebuilt AFTER super's tick so freshly learned 166c display
            # overrides are honoured (never undo the sealed display fix).
            try:
                ov = getattr(self, "_dc166c", None)
            except Exception:  # noqa: BLE001
                ov = None
            names = notebook_names180b(self.nb, ov)
            if not names:
                return event
            said = event.get("said", [])
            event["said"] = [resolve180b(line, names) for line in said]
        except Exception:  # noqa: BLE001
            pass
        return event


DEFAULT_CONFIG180B: dict = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
DEFAULT_CONFIG180B["ears"]["stand_in"] = (
    "Loop180bEars (loop138h stack + outermost silent known-name case "
    "resolution: any token/possessive matching a notebook name in any "
    "case parses as the stored name; replies render stored casing)")
DEFAULT_CONFIG180B["daemon"]["module"] = "Loop180bDaemon (this file)"


def build_agent180b(cfg: dict | None = None) -> Loop180bAgentLoop:
    """Build the loop138h agent shape with the 180b case layer on top."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)

    cfg = dict(DEFAULT_CONFIG180B, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90B.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    inner_ears = Loop180bEars(L96.Loop96Ears(chain))
    loop = Loop180bAgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    patch_chain142(chain)
    patch_loop121_teach(inner_ears)
    thinker, thinker_module = L90B.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    loop._screen148b_tag = None
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    loop._dc166c = {}
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep180b: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop180b: loop138h + outermost silent known-name "
                      "case resolution (exp-180b ears+display, one "
                      "mechanism; no confirms; say-pretend untouched)")
    return loop


class Loop180bDaemon(L138H.Loop138hDaemon):
    """Loop138hDaemon shape with the 180b agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = D141.SETTLE_GRACE_S) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.idle_seconds = float(idle_seconds)
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent180b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon180b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop180bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 180b silent case fix")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138h)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG180B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG180B)
        out["thinker"]["module"] = L90B.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG180B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon180b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent180b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
