#!/usr/bin/env python3
"""Experiment 164b -- FRESH REGISTRATION of the 164 "about" feature on loop138h.

Background: exp 164 (scripts/fable_fix164_about.py, a read-only about-stage
on loop150) is a registered FAIL because its sealed files were edited after
the seal. The director's probe showed the feature works, but it was never
registered cleanly. On loop138h, "Tell me about Kim." / "What do you know
about Kim?" still fall through to the fallback clarify even when Kim has
stored facts (calibrated 2026-09-22: two Kim teaches then both asks reply
the long R-CLARIFY verbatim).

THE ONE CHANGE (this file only; no existing file edited; 138h and 164 files
imported read-only): port the current 164 about-stage onto 138h:

  Loop164bEars(About164bMixin, Loop138hEars): hear() checks the about shapes
    FIRST against the notebook (read-only); anything else delegates
    byte-identical down the 138h chain.
  Loop164bAgentLoop(Loop138hAgentLoop): act path unchanged (about-turns are
    clarify actions: 0 writes); _listening_tick adds only an idempotent
    raw-USER safety net for about-claimed turns (the mixin already renders
    USER; super()'s 173/166 rendering + 166c display pass still apply).

Ported rule body (read-only from scripts/fable_fix164_about.py): P0-P4 full-
turn shapes, X validation (charset, no possessive chains, no compounds, no
pronouns), subject-then-value active-taught-facts read, max 8 then
"and N more.", unknown-X -> the existing contract unknown-entity reply,
zero-facts/AMBIGUOUS/error -> delegate, clarify-only (0 writes).

Two disclosed deltas vs 164 (both required by the 138h base):
  (a) 138h reply templates for fact sentences: USER-subject facts render
      "Your sister is Ada." (138h's me-rendering, stored casing), USER as
      value renders "you" (138h's last-resort rule); all other sentences
      are 164's "Tom's boss is Ann." verbatim.
  (b) "me" as X: P1-P4 shapes with X == "me" (any case) read the reserved
      USER entity ("What do you know about me?" -> the user's facts).
      Bare "me" is the only pronoun claimed; reflexives and all other
      pronouns still delegate exactly like 164. Zero USER facts (or no USER
      entity yet) delegates to the base chain: no new strings invented.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop164b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-about164b-20260922/loop164b-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
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
import fable_fix162b_plural as B162  # noqa: E402 (162b plural mixin, read-only)
import fable_fix164_about as A164  # noqa: E402 (about rule body, read-only)
import fable_fix165_typo as T165  # noqa: E402 (165 typo mixin, read-only)
import fable_fix166_me as M166  # noqa: E402 (166 me mixin + USER_KEY, read-only)
import fable_fix167_verb as V167  # noqa: E402 (167 verb mixin, read-only)
import fable_fix167b_valuescreen as S167B  # noqa: E402 (167b screen, read-only)
import fable_fix173_username as N173  # noqa: E402 (173 name mixin, read-only)
import fable_loop102_agent as L102  # noqa: E402 (HEARSAY_MSG, read-only)
import fable_loop134_agent as L134  # noqa: E402 (138b turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (router + decline, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (donor stack, read-only)
import fable_loop138f_agent as L138F  # noqa: E402 (wrapped stack, read-only)
import fable_loop138g_agent as L138G  # noqa: E402 (wrapped stack, read-only)
import fable_loop138h_agent as L138H  # noqa: E402 (wrapped base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop166_agent as L166  # noqa: E402 (me reply rewrite, read-only)
import fable_loop166c_agent as C166  # noqa: E402 (display-case, read-only)
import fable_loop173_agent as L173  # noqa: E402 (name reply rewrite, read-only)
import fable_notebook_contract as C  # noqa: E402 (resolve/statuses, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_perf142_index import (  # noqa: E402 (142 fast pieces, read-only)
    patch_chain142,
    patch_loop121_teach,
)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# THE 149 PIECE, applied at import (this process only, no file edited --
# the same process-wide override pattern loop134/loop138b/loop138d use).
WM149.apply_wordmatch()

# Re-assert the loop134 shouted-possessive override in this process (same
# value loop134/loop138/loop138b/loop138d set; no file edited).
A._APOS = L134._APOS_SHOUTED_134


def _match164b(turn: str) -> tuple | None:
    """164 matcher + the disclosed me-variant (X == "me" -> USER).

    A164.match_about (read-only rule body) handles every non-pronoun X and
    the P0 summary. Bare "me" is pronoun-excluded there, so only here an
    exact-"me" tail over the same four shapes claims ("What do you know
    about me?", "Tell me about me", "What have I told you about me?",
    "Anything about me?"). Reflexives, other pronouns, compounds ("me and
    Kim"), possessives ("me's ...") all still return None (delegate).
    """
    parsed = A164.match_about(turn)
    if parsed is not None:
        return parsed
    text = " ".join(str(turn).split())
    if not text:
        return None
    for rx in (A164._P1, A164._P2, A164._P3, A164._P4):
        m = rx.match(text)
        if m:
            x = " ".join(str(m.group(1)).split()).rstrip("?.!")
            if x.lower() == "me":
                return ("about", x)
            return None
    return None


def _render_user164b(sent: str) -> str:
    """164 sentence -> 138h USER template (stored casing otherwise).

    Mirrors scripts/fable_loop166_agent.py:57 rewrite_me166_reply (read-only
    rule): "USER's sister is Ada." -> "Your sister is Ada."; residual raw
    "USER" (e.g. as a value) -> "you", exactly like the base's last resort.
    Lines without the raw key pass through unchanged.
    """
    if M166.USER_KEY not in sent:
        return sent
    out = sent.replace("%s's" % M166.USER_KEY, "your")
    if sent.startswith("%s's " % M166.USER_KEY):
        out = out[0].upper() + out[1:]
    out = out.replace(M166.USER_KEY, "you")
    return out


def _about_reply164b(nb, entity_id: str | None, x_norm: str) -> str:
    """164 truncation over 138h-rendered sentences (read-only read + render)."""
    sents = [_render_user164b(s)
             for s in A164.fact_sentences(nb, entity_id, x_norm)]
    if len(sents) <= A164.MAX_FACTS:
        return " ".join(sents)
    head = sents[:A164.MAX_FACTS]
    return " ".join(head) + f" and {len(sents) - A164.MAX_FACTS} more."


class About164bMixin:
    """Stackable read-only about-stage on the 138h chain (this experiment).

    Cooperative (super() last): anything the stage does not claim, cannot
    resolve, or fails on delegates byte-identical to the 138h chain. The
    stage only ever returns clarify actions: 0 writes on every about-turn.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        try:
            nb = getattr(self, "nb", None)
            if nb is not None:
                parsed = _match164b(turn)
                if parsed is not None and parsed[0] == "summary":
                    return [{"act": "clarify",
                             "text": A164.summary_reply(nb)}]
                if parsed is not None and parsed[0] == "about":
                    x = parsed[1]
                    if x.lower() == "me":
                        # Disclosed delta (b): the user's own facts.
                        found = nb.resolve(M166.USER_KEY)
                        if found.status == C.OK:
                            eid = found.detail["entity_id"]
                            if A164.fact_sentences(nb, eid, "me"):
                                return [{"act": "clarify", "text":
                                         _about_reply164b(nb, eid, "me")}]
                        # Zero USER facts (or no USER entity): delegate,
                        # byte-identical; no new strings invented.
                    else:
                        found = nb.resolve(x)
                        x_norm = A164._norm_lit(x)
                        if found.status == C.OK:
                            eid = found.detail["entity_id"]
                            if A164.fact_sentences(nb, eid, x_norm):
                                return [{"act": "clarify", "text":
                                         _about_reply164b(nb, eid, x_norm)}]
                            # Known name, zero facts: delegate (no strings).
                        elif found.status == C.UNKNOWN_ENTITY:
                            if A164.fact_sentences(nb, None, x_norm):
                                return [{"act": "clarify", "text":
                                         _about_reply164b(nb, None, x_norm)}]
                            return [{"act": "clarify", "text":
                                     A164.unknown_reply(x)}]
                        # AMBIGUOUS -> delegate (base behaviour, identical).
        except Exception:
            pass  # never break the loop: fall through to the base chain
        return super().hear(turn)  # type: ignore[misc]


# ------------------------------------------------- ears: 138h + about outside
class Loop164bEars(About164bMixin, L138H.Loop138hEars):
    """Loop138hEars + exp-164b read-only about-stage checked first."""

    name = "loop164b-about"


# ------------------------------------------- loop: 138h + USER safety net
class Loop164bAgentLoop(L138H.Loop138hAgentLoop):
    """Loop138hAgentLoop (act path unchanged; about-turns are clarifies).

    _listening_tick runs 138h's tick verbatim (173/166 rendering + 166c
    display pass), then applies the 138h USER template idempotently to
    about-claimed turns only, in case any raw USER key survived in said
    lines (the mixin already renders USER, so this is normally a no-op;
    non-about turns return super()'s event untouched).
    """

    def _listening_tick(self):  # type: ignore[no-untyped-def]
        event = super()._listening_tick()
        try:
            turn = event.get("detail", {}).get("turn", "")
        except Exception:  # noqa: BLE001
            return event
        try:
            if (_match164b(turn or "") is not None
                    and any(M166.USER_KEY in str(line)
                            for line in event.get("said", []))):
                event["said"] = [_render_user164b(str(line))
                                  for line in event.get("said", [])]
        except Exception:  # noqa: BLE001
            pass
        return event


DEFAULT_CONFIG164B: dict = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
DEFAULT_CONFIG164B["ears"]["stand_in"] = (
    "Loop164bEars (loop138h stack + exp-164b read-only about-stage outside: "
    "'What do you know about X?' / 'Tell me about X' / 'What have I told "
    "you about X?' / 'Anything about X?' + bare 'What do you know?' + "
    "'about me' -> USER facts; notebook-only, max 8 facts then 'and N "
    "more', unknown X -> existing unknown-entity reply, USER facts render "
    "Your/you per 138h, 0 writes)")
DEFAULT_CONFIG164B["daemon"]["module"] = "Loop164bDaemon (this file)"


def build_agent164b(cfg: dict | None = None) -> Loop164bAgentLoop:
    """Build the loop138h agent shape with the 164b about-stage stacked on.

    Same construction as scripts/fable_loop138h_agent.py:258
    build_agent138h (read-only pieces, no file edited); only the inner
    ears class is Loop164bEars instead of Loop138hEars.
    """
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG164B, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop164bEars(Loop96Ears(chain))
    loop = Loop164bAgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    # 142 teach/chain index patches on the INNER ears (before the sleep
    # wrap replaces loop.ears with its Sleep130Ears delegate).
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
    # L2 live-self state (Self99-shaped logs; the 168-style turn above
    # maintains them -- same shape loop138/loop138b keep).
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    # 146d doubt store (notebook-side doubts146.json contract, shared by
    # the loop and the inner ears; attached BEFORE the sleep wrap).
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    # 166c display-case overrides (agent-layer only; notebook append-only).
    loop._dc166c = {}
    # L3 sleep145 (grow-slot + taught-beats-sleep; serving files
    # sleep145-* so sealed 104/131 state is never touched).
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138h: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop164b: loop138h + fresh 164 about-stage port "
                      "(P0-P4 + about-me -> USER facts; USER renders "
                      "Your/you per 138h templates; 0 writes)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop164bDaemon(L138G.Loop138gDaemon):
    """Loop138gDaemon shape with the 164b agent inside (mailbox same)."""

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
        self.loop = build_agent164b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon164b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop164bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 164b about-stage on 138h")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138h)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG164B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG164B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG164B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon164b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent164b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
