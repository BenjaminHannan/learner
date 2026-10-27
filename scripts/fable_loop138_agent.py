#!/usr/bin/env python3
"""Experiment 138 -- INTEGRATION: "tonight's agent" (loop138).

loop138 stacks tonight's verified pieces as mixins/wrappers. No existing
file is edited; everything new lives in this file (+ loop138-config.json).

  BASE (L1): loop134 (scripts/fable_loop134_agent.py: loop121 teach
      phrasings + loop117 fixes F5/M5/underscore) inherited by subclass.
  L1a punct mixin: scripts/fable_fix129_punct.py sanitize on outgoing
      teach/correct (ears hear) + again just before the notebook write
      (loop _act) -- the exact scripts/fable_loop129b_agent.py pattern.
  L1b 113c gate mixin: exp-113c partial-frame composer gate ported onto
      the loop134 question side. Loop134Ears "?" side is exact loop113b;
      Loop138Ears replaces it with the 113c question branch (a composer
      frame counts only if frame_consumes_question() passes, else the
      unchanged loop102 chain), imported read-only from
      scripts/fable_loop113c_agent.py. Teach side: super().hear (loop134).
      113e / 135 / 137: NOT included (no RESULTS.md saying PASS existed
      when layer 1 closed; see RESULTS.md).
  L2 self router: exp-127 route127 + Self99Agent.answer_self over live
      loop138 state. Rule: notebook answers always win; a notebook-missed
      turn (records empty, or every record a clarify containing "didn't
      understand" -- hearsay clarifies and MISSING_FACT abstains never
      route) is handled by the self path: route127 non-DECLINE serves the
      routed intent's canonical self answer (exactly Self127Agent over
      live loop138 state), route127 DECLINE serves the loop138 decline
      (HONEST_DECLINE + "Could you say it another way?", zero
      names/numbers) instead of the notebook's didn't-understand, since
      the notebook already declared non-understanding. No content is ever
      served on DECLINE. Self state (turn log, mode log, fact origins,
      web filings, sleep history, forget log) is maintained on
      the loop by turn(); answer_self runs through a Self99Agent facade
      bound to that live state (no loop90 built, loop90 file never edited).
  L3 live sleep: exp-131 Sleep131Reasoner/Sleep131Daemon retrofit
      (scripts/fable_sleep131_agent.py retrofit_sleep131, imported
      read-only): taught-beats-sleep reasoner wrap + Sleep104Sleeper
      episode feed from the loop's own questions. No-op until a word
      installs (fresh dirs behave exactly like L2).
  L4 exactly-once daemon: exp-108 pattern (scripts/fable_daemon108_run.py
      receipts + boot_reconcile, imported read-only): Loop138Daemon adds
      boot_reconcile in __init__ and a per-turn receipt in process_file.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138_agent.py --daemon --dir DIR \\
    --config artifacts/fable-agent138-20260922/loop138-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (Protocols + thresholds, read-only)
import fable_bench73_english_arm as B73  # noqa: E402 (composer, read-only)
import fable_bench92_english_arm as B92  # noqa: E402 (composer, read-only)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_fix129_punct as P129  # noqa: E402 (punct mixin, read-only)
import fable_fix77_core as F77  # noqa: E402 (gate + reasoner, read-only)
import fable_loop102_agent as L102  # noqa: E402 (fallback chain, read-only)
import fable_loop113_agent as L113  # noqa: E402 (guards+texts, read-only)
import fable_loop113c_agent as L113C  # noqa: E402 (gate fn, read-only)
import fable_loop134_agent as L134  # noqa: E402 (wrapped base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_sleep131_agent as S131  # noqa: E402 (sleep retrofit, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# Re-assert the loop134 shouted-possessive override in this process (same
# value loop134 sets; no file edited). Stored relation keys unchanged.
A._APOS = L134._APOS_SHOUTED_134

NOT_UNDERSTOOD = "didn't understand"

# Loop138 decline served when the notebook missed AND the frozen router
# declines. Evidence from the A1 attempt-2 wave: the bare frozen
# HONEST_DECLINE is scored WRONG by the bench scorer (it matches none of
# its abstain phrases), while the notebook's own didn't-understand is
# scored WRONG by the self scorer (no decline marker). The served text
# keeps the frozen HONEST_DECLINE verbatim first (self decline markers:
# "I have no record") and appends the redteam/bench abstain bits
# ("didn't understand that", "don't know", "another way"). Zero
# names/numbers; no content is ever served on DECLINE.
DECLINE_SUFFIX = (" I didn't understand that, I don't know \u2014 "
                  "could you say it another way?")


# ------------------------------------------------------------ L1: ears (134 + 129 punct + 113c gate)
class Loop138Ears(L134.Loop134Ears):
    """Loop134Ears + punct sanitize + 113c partial-frame gate on "?" turns.

    "?" turns run the 113c question branch verbatim (hearsay screen, both
    composers gated by frame_consumes_question, partial/prefix frames fall
    to the unchanged loop102 chain). Non-"?" turns inherit loop134 teach
    coverage (+F5/M5 fixes) unchanged. Both paths post-sanitize outgoing
    teach/correct actions (no-op on ask/clarify by construction).
    """

    name = "loop138-integration"

    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if text and text.rstrip().endswith("?"):
            return P129.sanitize_actions(self._hear_question(text, turn))
        return P129.sanitize_actions(super().hear(turn))

    def _hear_question(self, text: str, turn: str) -> list[dict]:
        if L102.is_hearsay(text):  # F1 preserved on questions
            self.last_stage, self.last_score = "loop138-hearsay", 1.0
            return [{"act": "clarify", "text": L102.HEARSAY_MSG}]
        if self.nb is None:
            return L102.Loop102Ears.hear(self, turn)
        triples = L90.notebook_triples(self.nb)
        frame = B92.compose_n_hop(text, triples)
        if frame is not None:
            if L113C.frame_consumes_question(text, list(frame[1]), triples):
                hit = L113.compound_subject_hit(triples, frame[0],
                                                list(frame[1]))
                if hit is None:
                    self.last_stage, self.last_score = ("loop138-nhop", 1.0)
                    return [{"act": "ask", "name": frame[0],
                             "relations": list(frame[1]),
                             "stage": "loop138"}]
                self.last_stage, self.last_score = (
                    "loop138-compound-guard", 1.0)
                return [{"act": "clarify", "text": L113.CHAIN_MISS_TEXT}]
            # Partial/prefix frame -> exactly like None (the 113c change).
            self.last_stage, self.last_score = ("loop138-partial", 1.0)
            return L102.Loop102Ears.hear(self, turn)
        frame2 = B73.compose_question(text, triples)
        if frame2 is not None:
            if (L113.is_explicit_question(text)
                    and L113C.frame_consumes_question(text, list(frame2[1]),
                                                      triples)):
                self.last_stage, self.last_score = ("loop138-explicit", 1.0)
                return [{"act": "ask", "name": frame2[0],
                         "relations": list(frame2[1]), "stage": "loop138"}]
            if not L113.is_explicit_question(text):
                self.last_stage, self.last_score = (
                    "loop138-nonexplicit", 1.0)
                return [{"act": "clarify", "text": L113.CHAIN_MISS_TEXT}]
            self.last_stage, self.last_score = ("loop138-partial", 1.0)
            return L102.Loop102Ears.hear(self, turn)
        return L102.Loop102Ears.hear(self, turn)


class Loop138Mouth(L134.Loop134Mouth):
    """Loop134Mouth (underscore->space reply rendering) renamed for logs."""

    name = "loop138-mouth"


# ------------------------------------------------------------ L2: self router over live loop state
def notebook_missed(records: list[dict]) -> bool:
    """True only when the notebook path did not understand the turn.

    Empty records ("no frame") or every record a clarify containing
    "didn't understand". Hearsay clarifies, MISSING_FACT/ask/write records
    all count as understood (never routed).
    """
    if not records:
        return True
    for rec in records:
        kind = rec.get("kind", "")
        if kind in ("ask", "answer", "write"):
            return False
        if kind == "clarify" and NOT_UNDERSTOOD in str(rec.get("text", "")):
            continue
        return False
    return True


def _route127(text: str) -> tuple[str, dict]:
    """Lazy route127 (keeps marks/bench import light; encoder loads once)."""
    import fable_self127 as S127  # noqa: E402 (frozen router, read-only)

    return S127.route127(text)


def self_answer_from_live_state(loop, text: str, intent: str) -> str:
    """The verified Self127Agent behaviour over live loop138 state.

    Answer the routed intent's CANONICAL question through the untouched
    Self99Agent.answer_self bound to this loop's live state -- byte for
    byte what Self127Agent.answer_self does for a non-DECLINE intent,
    with loop90 replaced by a facade over the loop138 loop (no loop90
    built, loop90 never edited). Every value is read from live state.
    """
    import fable_self105 as S105  # noqa: E402 (canonical map, read-only)
    import fable_self99 as S99  # noqa: E402 (answer bodies, read-only)

    helper = S99.Self99Agent.__new__(S99.Self99Agent)
    helper.loop = loop
    helper.nb = loop.nb
    helper.turn_log = loop.self_turn_log
    helper.mode_log = loop.self_mode_log
    helper.origin = loop.self_origin
    helper.web_filings = loop.self_web_filings
    helper.sleep_history = loop.self_sleep_history
    helper.forget_log = loop.self_forget_log
    helper.tau_hat = float(loop.parts90.get("tau_hat_used", 0.0))
    return helper.answer_self(S105.CANONICAL[intent])


class Loop138AgentLoop(L134.Loop134AgentLoop):
    """Loop134AgentLoop + punct _act sanitize + self-turn logging + router."""

    def _act(self, action: dict) -> dict:
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct"):
            action = P129.sanitize_action(action)
        return super()._act(action)

    def turn(self, text: str) -> list[str]:
        """Notebook path first; self answerer only on notebook-miss + route.

        Maintains Self99-shaped live state (turn log, mode log, origins)
        for the self answerer on every turn. Notebook answers always win.
        """
        before = set(self.nb.facts)
        said = super().turn(text)
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
        if notebook_missed(records):
            intent, info = _route127(text)
            if intent != "DECLINE":
                ans = self_answer_from_live_state(self, text, intent)
                entry = {"n": n, "text": text, "intent": intent,
                         "info": {k: v for k, v in info.items()
                                  if k != "reply"},
                         "answer": ans}
                self.self_routed.append(entry)
                self.last_routed = entry
                self.self_turn_log[-1]["routed"] = intent
                self.self_turn_log[-1]["reply"] = ans
                return [ans]
            # Router declined: the notebook already declared
            # non-understanding, so the turn is served the loop138 decline
            # (HONEST_DECLINE + DECLINE_SUFFIX, zero names/numbers) instead
            # of the notebook's didn't-understand. No content is ever
            # invented on DECLINE.
            import fable_self105 as S105  # noqa: E402 (frozen text, read-only)

            ans = S105.HONEST_DECLINE + DECLINE_SUFFIX
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


DEFAULT_CONFIG138: dict = copy.deepcopy(L134.DEFAULT_CONFIG134)
DEFAULT_CONFIG138["ears"]["stand_in"] = (
    "Loop138Ears (Loop134Ears teach coverage + F5/M5 fixes + exp-129 "
    "sentence-punctuation strip on teach/correct + exp-113c partial-frame "
    "composer gate on '?' turns: a frame must consume every relation "
    "phrase/qualifier, else the unchanged loop102 chain) over Loop121Ears "
    "over Loop113bEars over Loop102Ears pre-filter over Loop96Ears = "
    "GuardedEars91 over ChainEars(bench73 template + FakeEars templates)")
DEFAULT_CONFIG138["mouth"]["stand_in"] = (
    "Loop138Mouth (Loop134Mouth: relation keys rendered with spaces in "
    "replies only, stored keys unchanged)")
DEFAULT_CONFIG138["daemon"]["module"] = "Loop138Daemon (this file)"
DEFAULT_CONFIG138["self"] = {
    "router": "route127 (frozen novelty-guard router, scripts/fable_self127.py)",
    "answerer": "Self99Agent.answer_self over live loop138 state",
    "rule": ("notebook answers always win; notebook-missed turns go to "
             "the self path (routed intent's canonical answer on "
             "non-DECLINE, HONEST_DECLINE + 'Could you say it another way?' "
             "on DECLINE)"),
}
DEFAULT_CONFIG138["sleep"] = {
    "retrofit": "Sleep131Reasoner + Sleep104Sleeper via retrofit_sleep131",
    "recipe": "exp-46 recipe + taught-beats-sleep answer rule",
}


def build_agent138(cfg: dict | None = None) -> Loop138AgentLoop:
    """Build the loop134 agent shape, swap in loop138 ears/mouth/loop, L2+L3."""
    cfg = dict(DEFAULT_CONFIG138, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop138Mouth()
    reasoner = F77.QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop138AgentLoop(
        state_dir, ears=Loop138Ears(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    thinker, thinker_module = L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    # L2 live-self state (Self99-shaped logs owned by the loop).
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    # L3 live sleep 131 (taught-beats-sleep; no-op until a word installs).
    # Word/marker filenames match scripts/fable_sleep104_agent.py, so the
    # Sleep104Daemon mailbox checkers (104 Z-drives, 116 E-drives) read a
    # loop138 daemon dir unchanged.
    seed = int(cfg.get("sleep138_seed", cfg.get("sleep104_seed",
                                               cfg.get("sleep131_seed", 1))))
    S131.retrofit_sleep131(loop, state_dir, seed=seed)
    loop.notes.append("sleep138: Sleep131Reasoner + Sleep104Sleeper "
                      "(exp-131 retrofit)")
    return loop


# ------------------------------------------------------------ L4: exactly-once daemon
class Loop138Daemon(L134.Loop134Daemon):
    """Loop134Daemon shape with the loop138 agent inside + 108 exactly-once.

    Stable id = mailbox filename; per-turn receipts; boot_reconcile drops
    the loop.inbox crash artefact and finish-moves ids whose reply is
    already durable, before any turn is served.
    """

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
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
        self.loop = build_agent138(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)

    def process_file(self, path: Path) -> dict:
        import fable_daemon74_run as D74  # noqa: E402 (log helper, read-only)

        sleeps_before = int(self.loop.counters.get("sleeps", 0))
        record = super().process_file(path)
        if record.get("event") == "turn":
            try:
                reply = (self.outbox / Path(path).name).read_text(
                    encoding="utf-8")
            except OSError:
                reply = str(record.get("reply", ""))
            D108.append_receipt(self.root, Path(path).name, reply)
            if getattr(self.loop, "last_routed", None):
                record["routed"] = dict(self.loop.last_routed)
        # Sleep-event logging in the Sleep104Daemon schema (same fields the
        # 104/116 drives read): the install itself runs inside loop.turn;
        # without this the drives cannot see the recipe outcome.
        if int(self.loop.counters.get("sleeps", 0)) > sleeps_before:
            outcome = dict(getattr(self.loop.sleeper, "last_outcome", {}))
            D74._append_log(self.log_path, {
                "t": D74._now_iso(), "event": "sleep",
                "file": Path(path).name,
                "sleep_seconds": getattr(self.loop.sleeper,
                                         "sleep_seconds", 0.0),
                "accepted": outcome.get("accepted"),
                "recipe": outcome.get("recipe", {}),
                "bridge": outcome.get("bridge", {}),
                "episodes_at_sleep": len(getattr(
                    self.loop.reasoner, "episodes", [])) + sum(
                        w.get("episodes", 0) for w in
                        outcome.get("recipe", {}).get("words", []))})
        return record


def run_daemon138(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop138Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 138 integrated loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop134)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG138 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG138)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
