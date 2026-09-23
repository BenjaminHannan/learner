#!/usr/bin/env python3
"""Experiment 138h -- MERGE LAYER B part 1: verified 150/162b-lineage text fixes onto loop138g.

loop138h = loop138g + FIVE verified mixins ported read-only (MIXIN ONLY --
never the base chain; every rule body imported read-only, no existing file
edited). 173b is NOT ported: artifacts/fable-username173b-20260922/ has a
SEAL.sha256.txt but NO RESULTS.md saying PASS, so per the brief the 173
base is ported instead. 155 stays OUT (no 155 class in the MRO, no
fable_loop155* module imported -- verified by the M1 driver check).

PORTED (each a verified mixin; files read-only):

(1) 162b plural possessives -- Plural162bMixin.hear,
    scripts/fable_fix162b_plural.py:99 (class :88). Claims plural "s'"
    teaches only; every singular "'s" turn delegates to super untouched.
(2) 165 missing-apostrophe typos -- Typo165Mixin.hear,
    scripts/fable_fix165_typo.py:164 (class :154). Sits OUTSIDE Plural162b
    AND outside 167b/167, so the rewritten turn re-enters every inner
    stage via super().hear(fixed).
(3) 166c user "me" -- Me166Mixin.hear, scripts/fable_fix166_me.py:196
    (class :182), plus the 166c display-case _listening_tick override
    (scripts/fable_loop166c_agent.py:147, helpers :58-141). 166b is NOT
    ported (superseded by 166c). The underlying me166 reply rendering
    (scripts/fable_loop166_agent.py:57 rewrite_me166_reply, claimed-turn
    gate :89-90) is also applied here -- otherwise USER-key replies would
    leak raw -- followed by the 166c Title-case display pass.
(4) 173 user's own name -- Name173Mixin.hear,
    scripts/fable_fix173_username.py:324 (class :315), plus the loop173
    _act namecheck router (:87), _answer_namecheck (:92) and the
    _listening_tick name-reply rewrite (:108, via rewrite_name173_reply in
    scripts/fable_loop173_agent.py:58 which reuses loop166's rewrite).
(5) 167b verb facts -- Verb167Mixin.hear
    (scripts/fable_fix167_verb.py:212, class :202) with
    ValueScreen167bMixin.hear OUTSIDE it
    (scripts/fable_fix167b_valuescreen.py:158, class :148; sealed nested
    order scripts/fable_loop167b_agent.py:46).

Ears order (outermost first):
  Typo165 > ValueScreen167b > Verb167 > Name173 > Me166 > Plural162b >
  Loop138gEars (Frame137g > WhCity158cPort > Tail139eGuard > Loop138fEars...).
Why: preserves every sealed relative order (Typo>162b per loop165:42;
167b>167 per loop167b:46; 173>166 per loop173:52; Me166>162b per
loop166:49) and puts Typo outermost so fixed text re-enters the verb,
name, me and plural stages.
Loop _act: namecheck (173) > Tail139eGuard clarify (138g) > 138f chain.
_listening_tick: 173/166 reply rendering, then 166c display-case pass.
turn(): 168 grounded-self shape (138g, unchanged).
Reasoner/notebook/sleep/daemon: 138g unchanged.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138h_agent.py --daemon --dir DIR \\
    --config artifacts/fable-agent138h-20260922/loop138h-config.json
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
import fable_fix165_typo as T165  # noqa: E402 (165 typo mixin, read-only)
import fable_fix166_me as M166  # noqa: E402 (166 me mixin, read-only)
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
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop166_agent as L166  # noqa: E402 (me reply rewrite, read-only)
import fable_loop166c_agent as C166  # noqa: E402 (display-case, read-only)
import fable_loop173_agent as L173  # noqa: E402 (name reply rewrite, read-only)
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


def _norm(text: object) -> str:
    return " ".join(str(text).split())


# ------------------------------------------------- ears: merge layer B1
class Loop138hEars(T165.Typo165Mixin, S167B.ValueScreen167bMixin,
                   V167.Verb167Mixin, N173.Name173Mixin, M166.Me166Mixin,
                   B162.Plural162bMixin, L138G.Loop138gEars):
    """Loop138gEars + layer-B1 text stages (typo > verbscreen > verb >
    name > me > plural), each cooperative: unclaimed turns fall through
    to super().hear() untouched.
    """

    name = "loop138h-layer-b1"


# ------------------------------------------- loop: 138g + name rendering
class Loop138hAgentLoop(L138G.Loop138gAgentLoop):
    """Loop138gAgentLoop + 173 namecheck answering + 173/166/166c reply
    rendering (this file's _listening_tick only; no other file edited).

    _act mirrors scripts/fable_loop173_agent.py:87 (namecheck intercept,
    else super). _answer_namecheck mirrors :92 (reasoner lookup + compare,
    untouched record on miss). _listening_tick applies, in order: (a) the
    173 name rewrite for 173-claimed turns (which itself falls back to the
    166 me rewrite, mirroring loop173's tick over loop166's), else the 166
    me rewrite for me-claimed turns (mirroring loop166's tick); then (b)
    the 166c Title-case display pass (mirroring loop166c's tick over
    loop166's). The notebook log stays append-only throughout.
    """

    def _act(self, action: dict) -> dict:  # type: ignore[no-untyped-def]
        if isinstance(action, dict) and action.get("act") == "namecheck":
            return self._answer_namecheck(action)
        return super()._act(action)

    def _answer_namecheck(self, action: dict) -> dict:  # type: ignore[no-untyped-def]
        rec = self.reasoner.answer(
            {"name": action["owner"],
             "relations": list(action["relations"])}, self.nb)
        if rec.get("status") != "OK":
            return rec  # existing unknown wording, untouched
        ans = (rec.get("fields") or {}).get("answer")
        x = str(action.get("x", ""))
        owner = str(action.get("owner", ""))
        rel = " ".join(list(action.get("relations") or ["?"]))
        if ans is not None and _norm(ans).lower() == _norm(x).lower():
            return {"kind": "note",
                    "text": "Yes, %s is %s's %s." % (x, owner, rel)}
        return {"kind": "note",
                "text": "No, %s's %s is %s." % (owner, rel, ans)}

    def turn(self, text: str) -> list[str]:
        """Loop138gAgentLoop.turn + raw-USER backstop (this file only).

        The 168 self path (grounded_self_answer over live state) renders
        open-question records verbatim, so an untaught USER-name ask
        surfaces as "USER's name (never taught)". The _listening_tick
        rewrites above only cover listening events; self-routed turn()
        replies bypass them. Scrub any residual raw key exactly like
        loop166's last-resort rule; lines without the key pass through
        byte-identical.
        """
        said = super().turn(text)
        if (M166.USER_KEY not in str(text)
                and any(M166.USER_KEY in line for line in said)):
            said = [self._scrub_user_key(line) for line in said]
        return said

    @staticmethod
    def _scrub_user_key(line: str) -> str:
        if M166.USER_KEY not in line:
            return line
        out = line.replace("%s's" % M166.USER_KEY, "your")
        out = out.replace(M166.USER_KEY, "you")
        return out

    def _pre_pending_is_name_confirm(self) -> bool:
        try:
            pend = self.listening.pending
        except Exception:  # noqa: BLE001
            return False
        return (isinstance(pend, dict) and pend.get("kind") == "confirm"
                and pend.get("name") == M166.USER_KEY
                and pend.get("relation") == N173.NAME_REL)

    def _x_claimed(self, turn: str) -> bool:  # type: ignore[no-untyped-def]
        try:
            knob = N173.current_name(self.nb)
        except Exception:  # noqa: BLE001
            return False
        if not knob:
            return False
        return (N173.parse_x_teach(turn, knob) is not None
                or N173.parse_x_ask(turn, knob) is not None
                or N173.parse_name_check(turn, knob) is not None)

    def _listening_tick(self):  # type: ignore[no-untyped-def]
        try:
            pre_turn = self.inbox[0] if self.inbox else ""
        except Exception:  # noqa: BLE001
            pre_turn = ""
        pre_confirm = (N173._YESNO.match(_norm(pre_turn)) is not None
                       and self._pre_pending_is_name_confirm())
        event = super()._listening_tick()
        try:
            turn = event.get("detail", {}).get("turn", "") or pre_turn
        except Exception:  # noqa: BLE001
            return event
        # (a) 173/166 reply rendering (mirrors loop173 over loop166).
        try:
            claimed173 = bool(pre_confirm)
            if not claimed173:
                try:
                    claimed173 = (
                        N173.parse_name_statement(turn) is not None
                        or N173.parse_name_question(turn) is not None
                        or self._x_claimed(turn))
                except Exception:  # noqa: BLE001
                    claimed173 = False
            if claimed173:
                event["said"] = [L173.rewrite_name173_reply(line, turn)
                                 for line in event.get("said", [])]
            elif (M166.parse_me_teach(turn) is not None
                    or M166.parse_me_ask(turn) is not None):
                event["said"] = [L166.rewrite_me166_reply(line, turn)
                                 for line in event.get("said", [])]
        except Exception:  # noqa: BLE001
            pass
        # (b) 166c Title-case display pass (mirrors loop166c's tick).
        try:
            overrides = C166.apply_display_overrides(self, turn or "")
            if overrides:
                entities = dict(self.nb.entities)
                event["said"] = [C166.rewrite_display_case(
                    line, overrides, entities)
                    for line in event.get("said", [])]
        except Exception:  # noqa: BLE001
            pass
        return event


DEFAULT_CONFIG138H: dict = copy.deepcopy(L138G.DEFAULT_CONFIG138G)
DEFAULT_CONFIG138H["ears"]["stand_in"] = (
    "Loop138hEars (loop138g stack + layer B1 outside-in: 165 typo, 167b "
    "verb screen + 167 verb twins, 173 user-name, 166 me, 162b plural)")
DEFAULT_CONFIG138H["daemon"]["module"] = "Loop138hDaemon (this file)"
DEFAULT_CONFIG138H["self"] = dict(L138G.DEFAULT_CONFIG138G.get("self", {}))


def build_agent138h(cfg: dict | None = None) -> Loop138hAgentLoop:
    """Build the loop138g agent shape with merge layer B1 stacked on."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG138H, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop138hEars(Loop96Ears(chain))
    loop = Loop138hAgentLoop(
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
    loop.notes.append("loop138h: loop138g + merge layer B1 (162b plural + "
                      "165 typo + 166 me + 166c display-case + 173 name + "
                      "167 verb + 167b screen; 173 base not 173b: 173b has "
                      "a seal but no PASS RESULTS; 155 stays OUT)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop138hDaemon(L138G.Loop138gDaemon):
    """Loop138gDaemon shape with the 138h agent inside."""

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
        self.loop = build_agent138h(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon138h(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop138hDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 138h merge layer B1")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138g)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG138H to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138H)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG138H)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138h(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138h(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
