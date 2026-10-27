#!/usr/bin/env python3
"""Experiment 138d -- MORNING INTEGRATION: stack the verified late fixes onto loop138b.

loop138d = loop138b + (1) 142 speed index (IndexedLoopNotebook lower-layer
swap + FastReasoner142 + teach/chain index patches; the FastQuestionMixin142
"?" reroute is OUT -- see below) + (2) 138c serving rule (self serves only
grounded answers, else base reply verbatim) + (3) 146d doubt (hearsay-exempt
refused-correction doubt) + (4) 153 reverse questions + (5) 154 yes/no +
(6) 155 inverted frames (x135 variant) + (7) 156b small talk + (8) 157
fillers + (9) 158 question forms + (10) 159 hop through names (reasoner
fallback) + (11) 150b clause-swallow guard.

Base loop138b (scripts/fable_loop138b_agent.py) is imported read-only and
never edited; every rule body is imported read-only from its own module.
Everything new lives in this file (+ helpers scripts/fable_loop138d_*.py
+ artifacts/fable-agent138d-20260922/loop138d-config.json + the design doc
design/v3/30-modes/138d-stack-muse.md, which lists hook points, same-shape
pairs with the chosen order, and IN/OUT judgments).

OUT (judged in the design doc, not stacked):
  142 FastQuestionMixin142 "?" reroute -- it answers "?" turns without ever
    calling the inner ears, which would bypass 138b's sealed 148b neg/time
    screen AND the 132 rewriter (both live inside Loop138bEars.hear for "?"
    turns). Porting it changes two other pieces' behaviour; honest OUT.
    The 142 lower-layer swap (notebook + reasoner + teach/chain patches)
    IS in, so M6 may still improve.

Composition (ports, not rewrites):
  Ears (outermost first):
    Qform158 > Filler157 > Smalltalk156b > Doubt146b > Subject150B >
    Inverted155 > Reverse153 > Loop138bEars(151 twin > 148b screen > 138).
    All are super-first cooperative: each runs the inner chain first and
    only rewrites its own sealed miss shape (details + pair orders in the
    design doc).
  Loop _act (outermost first): Doubt146b record/clear > Subject150B clause
    guard > Loop138b _act (140 clean > 139b value veto > 150 subject veto).
  Loop _listening_tick: YesNo154Mixin (Is-shapes on didn't-understand only).
  turn(): the 138c serving rule verbatim (L134 turn on self = the full 138d
    loop path incl. yes/no; serve self answer only on non-DECLINE + grounded,
    else the base reply verbatim).
  Reasoner: Reasoner138d = 148b screen-tag logic over FastReasoner142
    (index-fast, same decisions); on an untagged non-OK answer the 159
    bridge gets exactly one fallback attempt (helper Hop159Reasoner77;
    served only on OK, else the fast record stands). Tagged asks never
    touch the fallback.
  Notebook: IndexedLoopNotebook (142/128 lower layer, same log format).
  L3: S145.retrofit_sleep145 (wraps ears+reasoner, as in 138b).
  L4: Loop138dDaemon = Loop138bDaemon shape (141 settle gate + exactly-once
    process_file inherited) with the 138d agent inside.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138d_agent.py --daemon --dir DIR \\
    --config artifacts/fable-agent138d-20260922/loop138d-config.json
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
import fable_daemon74_run as D74  # noqa: E402 (log helpers, read-only)
import fable_doubt146b_store as D146B  # noqa: E402 (146d doubt mixin, read-only)
import fable_fix150b_subject150b as S150B  # noqa: E402 (150b guard, read-only)
import fable_fix153_reverse as R153  # noqa: E402 (reverse stage, read-only)
import fable_fix154_yesno as Y154  # noqa: E402 (yes/no stage, read-only)
import fable_fix155_inverted as I155  # noqa: E402 (inverted stage, read-only)
import fable_fix156b_smalltalk as S156B  # noqa: E402 (smalltalk, read-only)
import fable_fix157_filler as F157  # noqa: E402 (filler strip, read-only)
import fable_fix158_qform as Q158  # noqa: E402 (qform normalize, read-only)
import fable_fix159_hop as H159  # noqa: E402 (hop bridge, read-only)
import fable_loop134_agent as L134  # noqa: E402 (base turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (missed/router/self, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop148b_agent as L148b  # noqa: E402 (screen reasoner, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_self99 as S99  # noqa: E402 (decline markers, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_perf128_index import IndexedLoopNotebook  # noqa: E402 (index store)
from fable_perf142_index import (  # noqa: E402 (142 fast pieces, read-only)
    FastReasoner142,
    _patch_relation,
    patch_chain142,
    patch_loop121_teach,
)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# THE 149 PIECE, applied at import (this process only, no file edited --
# the same process-wide override pattern loop134/loop138b use).
WM149.apply_wordmatch()

# Re-assert the loop134 shouted-possessive override in this process (same
# value loop134/loop138/loop138b set; no file edited).
A._APOS = L134._APOS_SHOUTED_134

# Exact Self99 FALLBACK text (scripts/fable_self99.py; same constant the
# 138c piece seals). Compared by equality plus a startswith guard.
FALLBACK138D = ("I do not understand that question. Ask me about what I "
                "know, where it came from, or what I am doing.")
FALLBACK138D_PREFIX = "I do not understand that question"


def self_grounded138d(ans: str) -> bool:
    """Sealed 138c grounded predicate: not FALLBACK, no decline marker."""
    if ans == FALLBACK138D or ans.startswith(FALLBACK138D_PREFIX):
        return False
    return not any(m in ans for m in S99.DECLINE_MARKERS)


# ------------------------------------------------------------ reasoner: screen + index + hop fallback
class Reasoner138d(L148b.ScreenStatusReasoner148b, FastReasoner142):
    """148b tagged-refusal logic over the 142 index-fast reasoner + 159 fallback.

    Tagged asks: ScreenStatusReasoner148b.answer handles them (real lookup
    first via super() = the fast index path, then the refusal mapping) --
    byte-identical to 138b. Untagged asks: the fast index answer stands,
    except a non-OK record gets exactly one 159-bridge fallback attempt
    (helper Hop159Reasoner77 over the same notebook; served only on OK).
    The fallback only converts abstains into answers on taught-subject
    bridge shapes (159's sealed G3 set); it never rewrites an OK record.
    """

    name = "reasoner138d-screen-index-hop"

    def answer(self, question: dict, notebook) -> dict:
        rec = super().answer(question, notebook)
        if not isinstance(question, dict):
            return rec
        if question.get("screen148b") in ("neg", "time"):
            return rec
        try:
            if (isinstance(rec, dict) and rec.get("kind") == "answer"
                    and rec.get("status") != C.OK):
                helper = H159.Hop159Reasoner77()
                rec2 = helper.answer(dict(question), notebook)
                if (isinstance(rec2, dict) and rec2.get("kind") == "answer"
                        and rec2.get("status") == C.OK):
                    return rec2
        except Exception:
            pass
        return rec


# ------------------------------------------------------------ ears: the 138d stack
class Loop138dEars(Q158.Qform158Mixin,
                   F157.Filler157Mixin,
                   S156B.Smalltalk156bMixin,
                   D146B.Doubt146bMixin,
                   S150B.Subject150BMixin,
                   I155.InvertedFrame155Mixin,
                   R153.Reverse153Mixin,
                   L138b.Loop138bEars):
    """Loop138bEars + the seven ears-level late fixes (outermost first).

    Qform158 normalises the question surface (what's/tell-me/??? stacks)
    and only uses the candidate when the inner chain parses it as a
    question. Filler157 strips ONE leading filler and accepts the
    remainder only as a complete teach/correct/question. Smalltalk156b
    answers only the exact generic fallthrough for whole-message small
    talk (never writes). Doubt146b records first-person refused teaches
    (hearsay-exempt) and screens asks over doubted hops. Subject150B
    refuses clause-in-subject teaches (SPLIT, no write). Inverted155
    saves V-is-X's-R frames (x135: officeholder never touched -- the 135
    guard runs inside the 138b core). Reverse153 answers reverse frames
    only on the forward miss (clarify acts, never writes).
    """

    name = "loop138d-stack"


# ------------------------------------------------------------ loop (138c turn rule + yes/no + doubt + 150b)
class Loop138dAgentLoop(Y154.YesNo154Mixin,
                        D146B.Doubt146bMixin,
                        S150B.Subject150BMixin,
                        L138b.Loop138bAgentLoop):
    """Loop138bAgentLoop + loop-level late fixes + the 138c serving rule.

    _listening_tick: YesNo154Mixin (Is-questions on didn't-understand).
    _act: Doubt146b record/clear > Subject150B clause guard > 138b guards.
    _ask: Doubt146b walk screen, then the 138b path (tagged asks keep the
    148b record path via _ask138b, as in 138b).
    turn(): the sealed 138c rule -- L134 turn on self (the full 138d loop
    path) is the base reply; the self answer is served ONLY on
    (non-DECLINE + grounded); every other notebook-missed turn serves the
    base reply verbatim. Notebook answers always win.
    __init__/_save: the 142 indexed shape (IndexedLoopNotebook +
    torn-tail repair + Listening + _patch_relation + tail-200 persist).
    """

    def __init__(self, state_dir, *, ears=None, mouth=None, reasoner=None,
                 sleeper=None, thinker=None,
                 sleep_threshold: int = A.SLEEP_THRESHOLD) -> None:
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / A.STATE_NAME
        self.ears = ears or A.FakeEars()
        self.mouth = mouth or A.FakeMouth()
        self.reasoner = reasoner or FastReasoner142()
        self.sleeper = sleeper or A.StubSleeper()
        self.thinker = thinker
        self.sleep_threshold = int(sleep_threshold)
        self.notes: list[str] = []
        self.last_records: list[dict] = []
        self.parts90: dict = {}

        self.nb = IndexedLoopNotebook(self.dir / A.NOTEBOOK_DIR)
        if self.nb.torn_tail:
            self.nb.repair_torn_tail()
            self.notes.append("repaired a torn notebook tail")
        import fable_fix77_core as F77  # noqa: E402 (seal verify, read-only)
        F77.verify_full(self.nb.root)
        import fable_listening_m1 as LST  # noqa: E402 (doorway, read-only)
        self.listening = LST.Listening(self.nb)
        _patch_relation(self)

        self.tick = 0
        self.mode = A.THINKING
        self.inbox: list[str] = []
        self.work_queue: list[str] = []
        self.experience: list[dict] = []
        self.question_pending: dict | None = None
        self.sleep_mark = 0
        self.counters = {"turns": 0, "writes": 0, "answers": 0,
                         "clarifications": 0, "sleeps": 0, "work": 0,
                         "thinks": 0}
        self._load()

    def _save(self) -> None:
        from fable_perf128_index import _SAVE_TAIL  # noqa: E402 (read-only)
        import json as _json
        import os as _os
        exp = (self.experience[-_SAVE_TAIL:]
               if len(self.experience) > _SAVE_TAIL else self.experience)
        payload = {"version": A.STATE_VERSION, "tick": self.tick,
                   "mode": self.mode, "inbox": self.inbox,
                   "work_queue": self.work_queue, "experience": exp,
                   "question_pending": self.question_pending,
                   "sleep_mark": self.sleep_mark, "counters": self.counters,
                   "listening_pending": self.listening.pending,
                   "listening_turn": self.listening.turn,
                   "sleep_threshold": self.sleep_threshold}
        tmp = self.dir / f"{A.STATE_NAME}.tmp{_os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(_json.dumps(payload, ensure_ascii=False,
                                     sort_keys=True))
            handle.flush()
            _os.fsync(handle.fileno())
        _os.replace(tmp, self.state_path)
        nb = getattr(self, "nb", None)
        if nb is not None and hasattr(nb, "advance_seal"):
            nb.advance_seal()

    def turn(self, text: str) -> list[str]:
        """Notebook path first; self answer only on (non-DECLINE + grounded).

        Verbatim port of the sealed 138c serving rule onto the 138d loop:
        the base reply is L134 turn on self (the full 138d loop path,
        including the yes/no stage and all ears guards). Notebook answers
        always win. On a notebook miss the frozen 127 router is consulted;
        the self answer is served ONLY when the intent is non-DECLINE AND
        the answer is grounded (not FALLBACK, no decline markers).
        Otherwise the base reply is served verbatim.
        """
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
            ans: str | None = None
            grounded = False
            if intent != "DECLINE":
                ans = L138.self_answer_from_live_state(self, text, intent)
                grounded = self_grounded138d(ans)
            entry = {"n": n, "text": text, "intent": intent,
                     "info": {k: v for k, v in info.items()
                              if k != "reply"},
                     "answer": ans, "grounded": grounded,
                     "served": ("self" if (intent != "DECLINE"
                                           and grounded) else "base")}
            self.self_routed.append(entry)
            self.last_routed = entry
            if intent != "DECLINE" and grounded:
                assert ans is not None
                self.self_turn_log[-1]["routed"] = intent
                self.self_turn_log[-1]["reply"] = ans
                return [ans]
            self.self_turn_log[-1]["routed"] = intent + " (base served)"
            self.self_turn_log[-1]["reply"] = reply
            return said
        return said


DEFAULT_CONFIG138D: dict = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
DEFAULT_CONFIG138D["notebook"]["class"] = (
    "IndexedLoopNotebook (142/128 index lower layer, same log format)")
DEFAULT_CONFIG138D["ears"]["stand_in"] = (
    "Loop138dEars (loop138b stack + 158 qform + 157 filler + 156b "
    "smalltalk + 146d hearsay-exempt doubt + 150b clause-subject guard + "
    "155 inverted frames (x135) + 153 reverse questions, outermost first)")
DEFAULT_CONFIG138D["reasoner"]["class"] = (
    "Reasoner138d (148b screen-tag logic over FastReasoner142 + one 159 "
    "bridge fallback on untagged non-OK answers)")
DEFAULT_CONFIG138D["daemon"]["module"] = "Loop138dDaemon (this file)"
DEFAULT_CONFIG138D["self"] = {
    "router": "route127 (frozen novelty-guard router, scripts/fable_self127.py)",
    "answerer": "Self99Agent.answer_self over live loop138d state",
    "rule": ("notebook answers always win; a notebook-missed turn serves "
             "the self answer ONLY on (router non-DECLINE AND grounded "
             "answer: not FALLBACK, no DECLINE_MARKERS); every other case "
             "serves the base loop's own reply verbatim (138c rule)"),
}
DEFAULT_CONFIG138D["sleep"] = {
    "retrofit": "Sleep145Reasoner + Sleep145Sleeper via retrofit_sleep145",
    "recipe": "exp-46 recipe + taught-beats-sleep answer rule (all words)",
}


def build_agent138d(cfg: dict | None = None) -> Loop138dAgentLoop:
    """Build the loop138b agent shape with the 138d stack swapped in."""
    cfg = dict(DEFAULT_CONFIG138D, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop138dEars(Loop96Ears(chain))
    loop = Loop138dAgentLoop(
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
    # L2 live-self state (Self99-shaped logs; turn() maintains them --
    # same shape loop138/loop138b/loop138c keep).
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
    loop.notes.append("sleep138d: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop138d: 138b + 142-index(swap) + 138c-serve + "
                      "146d-doubt + 153-reverse + 154-yesno + 155-inverted + "
                      "156b-smalltalk + 157-filler + 158-qform + 159-hop + "
                      "150b-guard (FastQuestionMixin142 OUT, judged)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop138dDaemon(L138b.Loop138bDaemon):
    """Loop138bDaemon shape with the 138d agent inside.

    141 settle gate + exactly-once process_file are inherited unchanged
    from Loop138bDaemon (which inherits process_file from Loop138Daemon).
    __init__ mirrors Loop138bDaemon.__init__ line for line except the
    build call. Name ends in Daemon / starts with Loop so the marks123
    loader picks this class.
    """

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
        self.loop = build_agent138d(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon138d(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop138dDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 138d stacked loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG138D to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138D)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG138D)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138d(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138d(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
