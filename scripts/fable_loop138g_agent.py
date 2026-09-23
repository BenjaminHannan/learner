#!/usr/bin/env python3
"""Experiment 138g -- MERGE LAYER A: verified overnight fixes onto loop138f.

loop138g = loop138f + FOUR verified mixins ported read-only (Step-1
file:line + composition below; no existing file edited). TWO candidate
pieces (157c title guard, 160c two-hop) are LEFT OUT: their verified
change cannot be ported cleanly (each depends on a base-chain piece
absent from 138f; porting the base would exceed the verified change).
Reasons are in design/v3/30-modes/138g-merge-layer-a-muse.md.

PORTED (each a verified mixin on the 138b lineage; files read-only):

(1) 139e tail words -- THE ONE CHANGE lives in
    scripts/fable_fix139e_tail.py (RelationGatedTailMixin + guard_action/
    guard_actions + check_value; closed LISTED_RELATIONS; 139c strip via
    scripts/fable_fix139c_tail.py:46 sanitize_action + 139d trigger/reply
    via scripts/fable_fix139d_tail.py, both read-only). Wired here at
    scripts/fable_loop139e_agent.py:66-80 (ears hear post-process) and
    :90-100 (loop _act clarify). Composition with 138f: no method
    collision (138f has no tail stage); the guard runs OUTSIDE the 138f
    ears stack (post-process of super().hear()) and OUTSIDE the 138f
    _act chain (clarify before super()._act()). Order vs 150B: tail is
    outermost (mirrors 139e, where the guard sits outside its base
    loop). NOTE: guard_action always returns the 139c-sanitized action,
    so this port also carries the 139c closed-list strip on every teach
    (intended: it fixes "Ivy too"/"Leeds btw").

(2) 137e hypothetical + hearsay framing -- three closed lists, all
    stdlib classifiers, no base dependency (137b discourse upgrade is
    NOT ported):
      - hypo: scripts/fable_fix137c_hypo.py:42 HYPO_REPLY,
        is_hypothetical (markers :48-60), wired at
        scripts/fable_loop137c_agent.py:77-84 (ears hear first);
      - say/hearsay frames: scripts/fable_fix137d_frame.py:67
        HEARSAY_REPLY, frame_kind :178, wired at
        scripts/fable_loop137d_agent.py:87-100 (ears hear first);
      - 137e unification: scripts/fable_loop137e_agent.py:91-99 --
        hearsay turns reply the EXISTING loop102 HEARSAY_MSG
        (scripts/fable_loop102_agent.py:70-71) byte-for-byte, say-group
        keeps the 137d echo. Composition: one new outermost ears stage
        (say > hearsay > hypo, mirroring 137d-then-137c order), early
        clarify return, else super().hear(). No _act/turn collision.

(3) 158c wh-city rewriter -- THE ONE CHANGE lives in
    scripts/fable_loop158c_agent.py:84-108 (rewrite_whcity: five closed
    regexes e1-e5 + entity gate via loop158b _ctx/_resolve_x/chain_split,
    read-only) and :115-150 (ears hear: only when the base returns
    all-clarify; second pass through the base; ask-bearing results only;
    teach/correct/forget2 discarded so questions never write).
    Composition: new ears stage between the 137 framing (outer) and the
    139e tail guard (inner); no _act/turn collision. ADAPTATION (open,
    documented in the design doc): the sealed second-pass target
    "Where does <X> live?" is answered on 158c's own agent by the 158b
    (d) table, which 138f lacks (verified live: loop138f clarifies
    "Where does Sue live?" after teaching her city). Porting the 158b
    whrel base would exceed the verified change, so the ported stage
    maps e1-e4 onto "What is <X>'s city?" and e5 onto "What is <X>'s
    city?" (the city path, exactly how the 158b base answers town
    shapes per the sealed 158c doc) -- same entity gate, same
    ask-only/never-write rule, same final replies on the sealed probe.

(4) 168 grounded self replies -- THE ONE CHANGE lives in
    scripts/fable_fix168_ground.py:129 ground_reply + :221
    grounded_self_answer (Self99Agent.answer_self over live loop state,
    then the grounding gate; read-only), wired at
    scripts/fable_loop168_agent.py:50-115 (turn(): L134 notebook path +
    live-state logging verbatim, self path serves grounded_self_answer
    on non-DECLINE, HONEST_DECLINE + suffix on DECLINE). Composition:
    turn() is overridden here with the 168 body verbatim (only the
    class/build names change); 138f's turn is loop138 verbatim so the
    shape matches. No ears/_act collision.

LEFT OUT (with reason):
(5) 157c title guard (scripts/fable_fix157c_titleguard.py:100
    TitleGuard157cMixin; strip at scripts/fable_fix157b_capfiller.py:59
    driven by CapFiller157bMixin.hear at :137). 138f carries 157
    (lowercase fillers, "Hey Jude" explicitly protected) but NOT 157b's
    capitalised-filler strip, so there is no strip for the title guard
    to block: porting the guard alone is a no-op, and porting
    157b+157c together would drag the whole capitalised-filler feature
    (an unrelated base-chain piece with its own refusal widening:
    "Btw Tom's..." now refuses). OUT.
(6) 160c two-hop (scripts/fable_fix160c_twohp.py:147 TwoHop160cMixin;
    resolves at scripts/fable_fix160b_laststated.py:141-151
    LastStated160bMixin._act against _last_stated160b). 138f has no
    160/160b bare-correction machinery (no bare_correct tag, no
    last-stated memory), so the 160c interceptor has nothing to
    intercept: porting it alone is a no-op, and porting 160b+160c would
    drag the bare-correction feature (an unrelated base-chain piece).
    OUT.

Ears order (outermost first):
  Frame137g (say137d > hearsay137e > hypo137c) > WhCity158cPort >
  Tail139eGuard > Loop138fEars (Qform158 > Filler157 > Smalltalk156b >
  Doubt146b > Subject150B > Reverse153 > Loop138bEars).
Loop _act: Tail139eGuard clarify > Doubt146b > Subject150B > 138b.
turn(): 168 grounded-self shape. Reasoner/notebook/sleep/daemon: 138f
unchanged (Reasoner138d, IndexedLoopNotebook, sleep145 retrofit,
settle + exactly-once daemon with idle_seconds).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138g_agent.py --daemon --dir DIR \\
    --config artifacts/fable-agent138g-20260922/loop138g-config.json
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
import fable_fix137c_hypo as H137C  # noqa: E402 (137c hypo list, read-only)
import fable_fix137d_frame as F137D  # noqa: E402 (137d frames, read-only)
import fable_fix139e_tail as T139E  # noqa: E402 (139e gated guard, read-only)
import fable_fix150b_subject150b as S150B  # noqa: E402 (150b guard, read-only)
import fable_fix153_reverse as R153  # noqa: E402 (reverse stage, read-only)
import fable_fix156b_smalltalk as S156B  # noqa: E402 (smalltalk, read-only)
import fable_fix157_filler as F157  # noqa: E402 (filler strip, read-only)
import fable_fix158_qform as Q158  # noqa: E402 (qform normalize, read-only)
import fable_fix168_ground as G168  # noqa: E402 (168 grounding, read-only)
import fable_loop102_agent as L102  # noqa: E402 (HEARSAY_MSG, read-only)
import fable_loop134_agent as L134  # noqa: E402 (138b turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (router + decline, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (donor stack, read-only)
import fable_loop138f_agent as L138F  # noqa: E402 (wrapped stack, read-only)
import fable_loop158b_agent as B158  # noqa: E402 (entity gate, read-only)
import fable_loop158c_agent as C158  # noqa: E402 (e1-e5 shapes, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
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


# ------------------------------------------------- ears: merge layer A
class Loop138gEars(L138F.Loop138fEars):
    """Loop138fEars + layer-A stages (framing > wh-city > tail guard).

    hear() runs three new stages outside the unchanged 138f stack:
      1. Frame137g: closed-list say/hearsay/hypo checks FIRST (before
         any panel read, mirroring 137d-then-137c order); framed turns
         return one clarify, everything else falls through.
      2. WhCity158cPort: the sealed 158c rewriter (e1-e5 shapes +
         158b entity gate, ask-only, never writes) on the guarded
         actions; second pass re-enters the 138f stack + tail guard.
      3. Tail139eGuard: 139c sanitize + 139e relation-gated clarify on
         teach/correct actions (post-process of the 138f ears).
    """

    name = "loop138g-merge-a"

    def hear(self, turn: str) -> list[dict]:
        framed = self._frame137g(turn)
        if framed is not None:
            return framed
        actions = T139E.guard_actions(super().hear(turn))
        return self._whcity158c(turn, actions)

    # -- stage 1: 137c hypo + 137d frames + 137e hearsay unification --
    def _frame137g(self, turn: str) -> list[dict] | None:
        kind = F137D.frame_kind(turn)
        if kind == "say":
            try:
                self.last_stage, self.last_score = ("loop138g-say137", 1.0)
            except AttributeError:
                pass
            return [{"act": "clarify", "text": F137D.say_reply(turn)}]
        if kind == "hearsay":
            try:
                self.last_stage, self.last_score = ("loop138g-hearsay137e",
                                                    1.0)
            except AttributeError:
                pass
            return [{"act": "clarify", "text": L102.HEARSAY_MSG}]
        if H137C.is_hypothetical(turn):
            try:
                self.last_stage, self.last_score = ("loop138g-hypo137c",
                                                    1.0)
            except AttributeError:
                pass
            return [{"act": "clarify", "text": H137C.HYPO_REPLY}]
        return None

    # -- stage 3 inner base call shared by both wh-city passes --
    def _guarded_base_hear(self, text: str) -> list[dict]:
        return T139E.guard_actions(
            super(Loop138gEars, self).hear(text))

    # -- stage 2: 158c wh-city rewriter (adapted target; see docstring) --
    def _whcity158c(self, turn: str,
                    actions: list[dict]) -> list[dict]:
        if not actions or any((not isinstance(a, dict))
                              or a.get("act") != "clarify"
                              for a in actions):
            return actions  # base understood the turn: never touch it
        if getattr(self, "nb", None) is None:
            return actions
        try:
            triples = L90.notebook_triples(self.nb)
            newq = C158.rewrite_whcity(turn, triples)
        except Exception:
            return actions
        if not newq:
            return actions
        # ADAPTATION vs sealed 158c (documented): the sealed target
        # "Where does <X> live?" needs the 158b (d) table, absent from
        # 138f. Try it verbatim first (harmless: ask-only, never
        # writes); when the base still clarifies, map onto the
        # possessive question the 138f base already answers (city path,
        # exactly how the 158b base answers town shapes per the sealed
        # 158c doc). Same entity gate (rewrite_whcity passed),
        # same ask-only/never-write rule.
        import re as _re
        save_stage, save_score = self.last_stage, self.last_score
        try:
            second = self._guarded_base_hear(newq)
        except Exception:
            self.last_stage, self.last_score = save_stage, save_score
            return actions
        asked = self._ask_only(second)
        if asked is not None:
            self.last_stage, self.last_score = ("loop138g-whcity158c", 1.0)
            return asked
        m = _re.match(r"^\s*where\s+does\s+(.+?)\s+live\s*\??\s*$", newq,
                      _re.I | _re.S)
        if not m or not m.group(1).strip():
            self.last_stage, self.last_score = save_stage, save_score
            return actions
        try:
            second2 = self._guarded_base_hear("What is %s's city?"
                                              % m.group(1).strip())
        except Exception:
            self.last_stage, self.last_score = save_stage, save_score
            return actions
        asked2 = self._ask_only(second2)
        if asked2 is not None:
            self.last_stage, self.last_score = ("loop138g-whcity158c", 1.0)
            return asked2
        self.last_stage, self.last_score = save_stage, save_score
        return actions

    @staticmethod
    def _ask_only(second: list[dict]) -> list[dict] | None:
        """Return second iff it is ask-bearing and write-free."""
        if not second or not all(isinstance(a, dict) for a in second):
            return None
        if any(a.get("act") in ("teach", "correct", "forget2", "person",
                                "alias", "forget", "quote", "answer")
               for a in second):
            # Questions must never write: discard anything but ask/clarify.
            return None
        if any(a.get("act") == "ask" for a in second):
            return second
        return None


# ------------------------------------------- loop: 138f + tail + self
class Loop138gAgentLoop(L138F.Loop138fAgentLoop):
    """Loop138fAgentLoop + 139e tail clarify (_act) + 168 grounded turn.

    _act mirrors scripts/fable_loop139e_agent.py:90-100 (sanitize +
    relation-gated clarify, else super). turn() mirrors
    scripts/fable_loop168_agent.py:50-115 (L134 notebook path +
    live-state logging verbatim; self path grounded; DECLINE unchanged).
    """

    def _act(self, action: dict) -> dict:
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct"):
            import fable_fix139c_tail as T139C  # noqa: E402 (read-only)
            action = T139C.sanitize_action(action)
            msg = T139E.check_value(action.get("value", ""),
                                    action.get("relation", ""))
            if msg is not None:
                self.counters["clarifications"] += 1
                return {"kind": "clarify", "text": msg}
        return super()._act(action)

    def turn(self, text: str) -> list[str]:
        before = set(self.nb.facts)
        said = L134.Loop134AgentLoop.turn(self, text)
        reply = " ".join(said) if said else "(nothing to say)"
        records = list(getattr(self, "last_records", []))
        n = len(self.self_turn_log) + 1
        after = set(self.nb.facts)
        for fid in after - before:
            self.self_origin[fid] = {"by": "Ben", "turn": n}
        self.self_turn_log.append({
            "n": n, "ben": text, "reply": reply, "records": records,
            "statuses": [r.get("status", r.get("kind")) for r in records],
            "stage": getattr(self.ears, "last_stage", ""),
            "score": getattr(self.ears, "last_score", 0.0),
            "wrote": len(after - before) > 0 or str(text).startswith("forget"),
            "via": "loop", "tick": self.tick, "mode": self.mode,
        })
        self.self_mode_log.append({"tick": self.tick, "mode": self.mode})
        self.last_routed = None
        if L138.notebook_missed(records):
            intent, info = L138._route127(text)
            if intent != "DECLINE":
                # [168] THE ONE CHANGE: grounded self answer.
                ans = G168.grounded_self_answer(self, text, intent)
                entry = {"n": n, "text": text, "intent": intent,
                         "info": {k: v for k, v in info.items()
                                  if k != "reply"},
                         "answer": ans}
                self.self_routed.append(entry)
                self.last_routed = entry
                self.self_turn_log[-1]["routed"] = intent
                self.self_turn_log[-1]["reply"] = ans
                return [ans]
            import fable_self105 as S105  # noqa: E402 (frozen text, read-only)

            ans = S105.HONEST_DECLINE + L138.DECLINE_SUFFIX
            entry = {"n": n, "text": text, "intent": "DECLINE",
                     "info": {k: v for k, v in info.items()
                              if k != "reply"},
                     "answer": ans}
            self.self_routed.append(entry)
            self.last_routed = entry
            self.self_turn_log[-1]["routed"] = "DECLINE"
            self.self_turn_log[-1]["reply"] = ans
            return [ans]
        return said


DEFAULT_CONFIG138G: dict = copy.deepcopy(L138F.DEFAULT_CONFIG138F)
DEFAULT_CONFIG138G["ears"]["stand_in"] = (
    "Loop138gEars (loop138f stack + layer A outside-in: 137 say/hearsay/"
    "hypo framing, 158c wh-city rewriter, 139e relation-gated tail "
    "guard)")
DEFAULT_CONFIG138G["daemon"]["module"] = "Loop138gDaemon (this file)"
DEFAULT_CONFIG138G["self"] = {
    "router": "route127 (frozen novelty-guard router, scripts/fable_self127.py)",
    "answerer": "grounded_self_answer (fix168 gate over Self99Agent."
                "answer_self on live loop138g state; facts only from "
                "live state, plain replies otherwise)",
    "rule": ("loop138 verbatim (138c OFF): notebook answers win; "
             "notebook-missed turns serve the grounded self reply on "
             "non-DECLINE, the honest decline + suffix on DECLINE"),
}


def build_agent138g(cfg: dict | None = None) -> Loop138gAgentLoop:
    """Build the loop138f agent shape with merge layer A stacked on."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG138G, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop138gEars(Loop96Ears(chain))
    loop = Loop138gAgentLoop(
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
    # L3 sleep145 (grow-slot + taught-beats-sleep; serving files
    # sleep145-* so sealed 104/131 state is never touched).
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138g: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop138g: loop138f + merge layer A (139e tail "
                      "guard + 137c hypo + 137d frames + 137e hearsay "
                      "unify + 158c wh-city + 168 grounded self; 157c "
                      "and 160c left out, see design doc)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop138gDaemon(L138F.Loop138fDaemon):
    """Loop138fDaemon shape with the 138g agent inside."""

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
        self.loop = build_agent138g(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon138g(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop138gDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 138g merge layer A")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138f)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG138G to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138G)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG138G)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138g(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138g(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
