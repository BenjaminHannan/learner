#!/usr/bin/env python3
"""Experiment 180 -- lowercase-names recase on loop138g (ears only, outermost).

Base: loop138g (scripts/fable_loop138g_agent.py, read-only). ONE CHANGE:
an outermost ears stage. If a turn does not parse as-is, re-case it ONCE
and retry through the unchanged 138g stack:

  recase(turn): capitalise the first word; capitalise any other lowercase
    token whose possessive-stripped stem equals (case-insensitively) a name
    ALREADY IN THE NOTEBOOK as a subject or value (notebook canonical
    casing is used); never touch any other token (unknown words such as
    "bob" or "kofis", and common words like will/may/rose when absent from
    the notebook, keep their case).

Gate (sealed in artifacts/fable-lowercase180-20260922/PASSMARKS.md):
  - ASK-bearing base parses are returned untouched (asks answer directly;
    a lowercase ask is never re-cased -- this keeps every already-working
    lowercase ask byte-identical, including its echo).
  - TEACH/CORRECT base parses are returned untouched when every
    name-token already matches notebook-canonical case (capitalised
    teaches byte-identical). When a name-token matches a known notebook
    name but is typed lowercase, the turn counts as not-parsed-as-is:
    NOTHING is written; ears returns a confirm clarify
    ("Did you mean: Lou's boss is Kim?"). The recased teach runs only
    after the user says yes, producing exactly the capitalised twin's
    events (stored text uses the notebook's existing casing).
  - all-clarify base parses are retried ONCE as recase(turn) through the
    full 138g stack: ask-bearing retry is returned (asks answer directly);
    teach/correct retry becomes a confirm (no write); anything else falls
    back to the base reply byte-identical (traps: unknown names,
    missing-apostrophe "kofis" shapes owned by exp 165, common words).

Missing-apostrophe typos ("kofis") are exp 165's: never repaired here
("kofis" is not a notebook name, so it is never capitalised); listed as
out of scope in the design doc.

No existing file is edited; loop138g is imported read-only.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop180_agent.py --daemon --dir DIR \\
    --config artifacts/fable-lowercase180-20260922/loop180-config.json
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
import fable_fix168_ground as G168  # noqa: E402 (168 grounding, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop102_agent as L102  # noqa: E402 (HEARSAY_MSG, read-only)
import fable_loop134_agent as L134  # noqa: E402 (138b turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (router + decline, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (donor stack, read-only)
import fable_loop138f_agent as L138F  # noqa: E402 (wrapped stack, read-only)
import fable_loop138g_agent as L138G  # noqa: E402 (wrapped stack, read-only)
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

# Closed yes-words: only these commit a pending teach. Anything else drops
# the pending confirm and is processed as a fresh turn.
YES180 = frozenset({"yes", "yeah", "yep"})
YES180_RE = re.compile(r"^\s*(yes|yeah|yep)\s*\.?\s*$", re.I | re.S)

_WORD180_RE = re.compile(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)?")


def _split_tokens180(text: str) -> list[tuple[str, bool]]:
    """Split into (chunk, is_word) preserving every byte of the original."""
    parts: list[tuple[str, bool]] = []
    pos = 0
    for m in _WORD180_RE.finditer(text):
        if m.start() > pos:
            parts.append((text[pos:m.start()], False))
        parts.append((m.group(0), True))
        pos = m.end()
    if pos < len(text):
        parts.append((text[pos:], False))
    return parts


def _stem180(word: str) -> tuple[str, str]:
    """Return (stem, suffix) splitting one trailing possessive 's/'s."""
    low = word.lower()
    for suf in ("'s", "\u2019s", "'"):
        if low.endswith(suf) and len(word) > len(suf):
            return word[:-len(suf)], word[-len(suf):]
    return word, ""


def notebook_names180(nb) -> dict[str, str]:
    """Map lowercased name -> notebook-canonical casing.

    Names = taught+active subjects and values (values split on
    whitespace; first-seen casing wins). Read-only over the notebook.
    """
    names: dict[str, str] = {}
    try:
        triples = L90.notebook_triples(nb)
    except Exception:
        return names
    for subj, _rel, val in triples:
        stem, _ = _stem180(subj)
        key = stem.lower()
        if key and key not in names:
            names[key] = stem
        # Values count ONLY when single-token: a multi-word value is a
        # phrase, not a name (POST-SEAL FIX D1: value tokens such as
        # "The" from "The Glass Orchard" must never become names, else a
        # determiner "the" misfires the confirm, e.g. rt143 C5).
        if isinstance(val, str) and val.strip() and not re.search(
                r"\s", val.strip()):
            vstem, _ = _stem180(val.strip())
            vkey = vstem.lower()
            if vkey and vkey not in names:
                names[vkey] = vstem
    return names


def recase180(turn: str, names: dict[str, str]) -> str:
    """Capitalise the first word + lowercase tokens matching known names."""
    parts = _split_tokens180(str(turn))
    out: list[str] = []
    first_done = False
    for chunk, is_word in parts:
        if not is_word:
            out.append(chunk)
            continue
        stem, suffix = _stem180(chunk)
        canon = names.get(stem.lower())
        if not first_done:
            first_done = True
            if canon is not None and stem != canon:
                out.append(canon + suffix)
            elif stem[:1].islower():
                out.append(stem[:1].upper() + stem[1:] + suffix)
            else:
                out.append(chunk)
        else:
            if canon is not None and stem != canon:
                out.append(canon + suffix)
            else:
                out.append(chunk)
    return "".join(out)


def needs_recase180(turn: str, names: dict[str, str]) -> bool:
    """True iff some token matches a known notebook name but is not in
    canonical case. The first-word rule is NOT part of the trigger: a
    turn whose names are already canonical is never re-cased."""
    if not names:
        return False
    for chunk, is_word in _split_tokens180(str(turn)):
        if not is_word:
            continue
        stem, _suffix = _stem180(chunk)
        canon = names.get(stem.lower())
        if canon is not None and stem != canon:
            return True
    return False


def confirm_predicate180(turn: str, names: dict[str, str]) -> bool:
    """True iff a TEACH/CORRECT may confirm instead of writing.

    POST-SEAL refinements D2/D3 (reported; forced by frozen-sessions
    evidence): needs_recase AND the first AND last word-token stems are
    known notebook names. Rationale: the confirm protects the write path
    only when the recased teach resolves both ends to notebook-canonical
    form. A lowercase teach carrying a still-unknown name (sessions
    S2/S3/S5: "vera's city is lima", "ned's teacher is quinn",
    "btw marta's brother is kai", filler leads) is teaching a new name
    and must save as-is exactly like the base. A first-word-only repair
    ("no Vera's city is Quito", S6) never confirms on the retry path.
    """
    if not names or not needs_recase180(turn, names):
        return False
    words = [chunk for chunk, is_word in _split_tokens180(str(turn))
             if is_word]
    if not words:
        return False
    first, _ = _stem180(words[0])
    last, _ = _stem180(words[-1])
    return first.lower() in names and last.lower() in names


def confirm_text180(recased: str) -> str:
    return "Did you mean: %s?" % recased.strip().rstrip(".?!").strip()


def _acts180(actions) -> list[str]:
    if not actions:
        return []
    return [a.get("act") for a in actions if isinstance(a, dict)]


class Loop180Ears(L138G.Loop138gEars):
    """Loop138gEars + outermost lowercase-names recase (ears only)."""

    name = "loop180-lowercase"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pending180: dict | None = None

    def _base_hear180(self, text: str) -> list[dict]:
        return L138G.Loop138gEars.hear(self, text)

    def hear(self, turn: str) -> list[dict]:
        # Pending confirm: "yes" commits the stashed recased teach.
        if self._pending180 is not None:
            if YES180_RE.match(str(turn)):
                recased = self._pending180["text"]
                self._pending180 = None
                try:
                    names = notebook_names180(getattr(self, "nb", None))
                    if needs_recase180(recased, names):
                        # Notebook changed under us; re-derive canonical.
                        recased = recase180(recased, names)
                    redone = self._base_hear180(recased)
                except Exception:
                    redone = []
                kinds = _acts180(redone)
                if any(k in ("teach", "correct") for k in kinds):
                    try:
                        self.last_stage, self.last_score = (
                            "loop180-yes-commit", 1.0)
                    except AttributeError:
                        pass
                    return redone
                return self._base_hear180(turn)
            self._pending180 = None
        try:
            actions = self._base_hear180(turn)
        except Exception:
            return super().hear(turn)
        kinds = _acts180(actions)
        if any(k == "ask" for k in kinds):
            return actions  # asks answer directly; never re-case
        names = notebook_names180(getattr(self, "nb", None))
        if any(k in ("teach", "correct") for k in kinds):
            if names and confirm_predicate180(turn, names):
                recased = recase180(turn, names)
                self._pending180 = {"text": recased}
                try:
                    self.last_stage, self.last_score = (
                        "loop180-confirm", 1.0)
                except AttributeError:
                    pass
                return [{"act": "clarify", "text": confirm_text180(recased)}]
            return actions  # canonical teach: byte-identical
        # all-clarify: retry the re-cased turn ONCE through the full stack.
        if not names:
            return actions
        try:
            recased = recase180(turn, names)
        except Exception:
            return actions
        if recased == str(turn):
            return actions  # nothing to repair: byte-identical
        save_stage, save_score = self.last_stage, self.last_score
        try:
            retry = self._base_hear180(recased)
        except Exception:
            self.last_stage, self.last_score = save_stage, save_score
            return actions
        retry_kinds = _acts180(retry)
        if any(k == "ask" for k in retry_kinds):
            try:
                self.last_stage, self.last_score = ("loop180-recase", 1.0)
            except AttributeError:
                pass
            return retry
        if any(k in ("teach", "correct") for k in retry_kinds):
            if not confirm_predicate180(turn, names):
                self.last_stage, self.last_score = save_stage, save_score
                return actions  # D2: first-word-only repairs never confirm
            self._pending180 = {"text": recased}
            try:
                self.last_stage, self.last_score = ("loop180-confirm", 1.0)
            except AttributeError:
                pass
            return [{"act": "clarify", "text": confirm_text180(recased)}]
        self.last_stage, self.last_score = save_stage, save_score
        return actions


class Loop180AgentLoop(L138G.Loop138gAgentLoop):
    """Loop138gAgentLoop unchanged (ears carry the one change)."""


DEFAULT_CONFIG180: dict = copy.deepcopy(L138G.DEFAULT_CONFIG138G)
DEFAULT_CONFIG180["ears"]["stand_in"] = (
    "Loop180Ears (loop138g stack + outermost lowercase-names recase: "
    "re-case once and retry; teaches confirm before writing)")
DEFAULT_CONFIG180["daemon"]["module"] = "Loop180Daemon (this file)"


def build_agent180(cfg: dict | None = None) -> Loop180AgentLoop:
    """Build the loop138g agent shape with the loop180 ears on top."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)

    cfg = dict(DEFAULT_CONFIG180, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    inner_ears = Loop180Ears(L96.Loop96Ears(chain))
    loop = Loop180AgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    patch_chain142(chain)
    patch_loop121_teach(inner_ears)
    thinker, thinker_module = L90.build_thinker(loop.nb)
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
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep180: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop180: loop138g + outermost lowercase-names "
                      "recase (exp-180 ears-only; teaches confirm "
                      "before writing)")
    return loop


class Loop180Daemon(L138G.Loop138gDaemon):
    """Loop138gDaemon shape with the 180 agent inside."""

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
        self.loop = build_agent180(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon180(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop180Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 180 lowercase-recase")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138g)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG180 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG180)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG180)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon180(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent180(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
