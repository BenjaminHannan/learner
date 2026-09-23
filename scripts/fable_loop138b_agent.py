#!/usr/bin/env python3
"""Experiment 138b -- STACK: tonight's verified single-change fixes onto loop138.

loop138b = loop138 + (in this order) 135 officeholder guard, 137 multi-word
possessive subjects, 139b value guard (rule + UN table), 140 tail cleaner,
144 two-"of" names, 150 subject guard, 149 whole-word names, 132
relative-clause rewriter (149-qrewrite shape: rewriter + whole-word match),
151 no-"?" questions, 148+148b negation/time screen as abstentions,
sleep145 in place of sleep131 in L3, 141 mailbox settle + atomic-write
client rule. L2 (127 router + Self99 answers) is UNTOUCHED by director
order (agents 138c/161 own the self layer); Loop138AgentLoop.turn is
inherited verbatim.

OUT (judged, listed, not stacked):
  113e fallback gate -- registered FAIL on its own bars (E2 198/200,
    L5-Z1 58/60, L5-Z2 2 MISS remain); replacing the frozen 113c gate to
    fix the single A2-174 item risks new wrongs on unseen phrasing.
  142 speed index -- requires swapping the notebook class to
    IndexedLoopNotebook (a lower-layer change, barred by the brief);
    B7 reports wall-clock ask times instead.

Composition (ports, not rewrites; every rule body is imported read-only):
  Teach side, inside one transient 135 patch window (B73.hear_teach_template
  -> F135.hear_teach135, restored in finally):
    super().hear (151 twin -> 148b screen -> loop138 113c/134 teach path),
    then 140 clean (superset of the 129 strip), 139b value veto, 150
    subject veto, 137 upgrade, 144 upgrade, 132 rewrite.
  137 upgrade = F137.parse_possessive137 + G91 value screen (as exp 137)
    PLUS the 139b value veto and the 150 subject veto (else a 137-taught
    compound value / polluted subject would bypass the stacked guards).
  144 upgrade = L144._parse_single_teach + F144.screen_value_144 (as exp
    144) PLUS the 139b value veto and the 150 subject veto (else a
    139b-refused "and" value passing 144's narrower screen would be
    re-taught through the upgrade). Officeholder sentences parse to None
    under the held 135 patch, so no upgrade path can re-teach them.
  Question side: 148b screen runs FIRST on the original text (tagged ask
  through the reasoner record path); the 132 rewriter only reconsiders
  pure clarifies, and its second pass re-enters super().hear so a
  rewritten neg/time question is screened, never answered.
  149 = WM149.apply_wordmatch() at import (process-wide, same pattern
  loop134 uses for _APOS) + re-assert at bind.
  Loop _act: tagged asks via the 148b record path (copied tag-carry);
  teach/correct via 140 clean -> 139b veto -> 150 veto -> super()._act.
  L3 = S145.retrofit_sleep145 (grow-slot + taught-beats-sleep for all
  words) instead of retrofit_sleep131.
  L4 = Loop138bDaemon: Loop138Daemon behaviour (108 receipts + reconcile
  + 104-schema sleep logs, inherited process_file) + 141 settle gate
  (size/mtime stable across two polls or grace; tmp/dot files skipped).

No existing file is edited; everything new lives in this file (+
artifacts/fable-agent138b-20260922/loop138b-config.json + drivers).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-agent138b-20260922/loop138b-config.json
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
import fable_bench73_english_arm as B73  # noqa: E402 (patched transiently, restored)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_daemon74_run as D74  # noqa: E402 (log helpers, read-only)
import fable_earsguard91 as G91  # noqa: E402 (value screens, read-only)
import fable_fix129_punct as P129  # noqa: E402 (strip rule, read-only)
import fable_fix135_office as F135  # noqa: E402 (officeholder guard, read-only)
import fable_fix137_names as F137  # noqa: E402 (possessive parse, read-only)
import fable_fix139b_valueguard as V139b  # noqa: E402 (value screen, read-only)
import fable_fix140_tail as T140  # noqa: E402 (tail cleaner, read-only)
import fable_fix144_ofname as F144  # noqa: E402 (of-name screen, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject screen, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop102_agent as L102  # noqa: E402 (guards + texts, read-only)
import fable_loop134_agent as L134  # noqa: E402 (read-only value source)
import fable_loop138_agent as L138  # noqa: E402 (wrapped base, read-only)
import fable_loop144_agent as L144  # noqa: E402 (single-teach parse, read-only)
import fable_loop148b_agent as L148b  # noqa: E402 (screen reasoner/mouth, read-only)
import fable_loop151_agent as L151  # noqa: E402 (qmark mixin, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_qrewrite132 as Q132  # noqa: E402 (rewriter, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# THE 149 PIECE, applied at import (this process only, no file edited --
# the same process-wide override pattern loop134 uses for _APOS).
WM149.apply_wordmatch()

# Re-assert the loop134 shouted-possessive override in this process (same
# value loop134/loop138 set; no file edited).
A._APOS = L134._APOS_SHOUTED_134


# ------------------------------------------------------------ ears: the stack
class Loop138bEars(L151.QMarkMixin151, L148b.ScreenStatusMixin148b,
                   L138.Loop138Ears):
    """Loop138Ears + 151 twin + 148b status screen + teach-guard stack.

    hear(): with the 135 officeholder patch held, run the MRO chain
    (151 -> 148b -> 138), then 140 clean, 139b value veto, 150 subject
    veto, 137 upgrade, 144 upgrade, 132 rewrite. L2 lives in turn(),
    which is inherited untouched from Loop138AgentLoop.
    """

    name = "loop138b-stack"

    def bind(self, nb):
        WM149.apply_wordmatch()
        return super().bind(nb)

    def hear(self, turn: str) -> list[dict]:
        original = B73.hear_teach_template
        B73.hear_teach_template = F135.hear_teach135  # type: ignore[method-assign]
        try:
            actions = super().hear(turn)
            actions = T140.sanitize_actions(actions)
            actions = V139b.guard_actions(actions)
            actions = S150.guard_actions(actions)
            actions = self._upgrade137(actions, turn)
            actions = self._upgrade144(actions, turn)
            actions = self._rewrite132(actions, turn)
            return actions
        finally:
            B73.hear_teach_template = original

    # -- (2) 137 multi-word possessive subjects (+ stacked vetoes) ---------
    def _upgrade137(self, actions: list[dict], turn: str) -> list[dict]:
        if not isinstance(actions, list) or not actions:
            return actions
        if any(isinstance(a, dict) and a.get("act") in (
                "teach", "correct", "ask", "answer", "forget2",
                "person", "alias", "forget", "quote") for a in actions):
            return actions  # base understood the turn: never touch it
        parsed = F137.parse_possessive137(turn)
        if parsed is None:
            return actions
        if G91.screen_value(parsed[2]) is not None:
            return actions  # value refusal: base clarifies, byte-identical
        stripped_v = P129.strip_sentence_punct(parsed[2])
        if V139b.screen_value_139b(
                stripped_v if stripped_v else parsed[2]) is not None:
            return actions  # stacked 139b veto (compound values stay out)
        verdict, _clean = S150.screen_subject_150(parsed[0])
        if verdict != "store":
            return actions  # stacked 150 veto (polluted subjects stay out)
        action = T140.sanitize_action(
            P129.sanitize_action(F137.build_action137(parsed)))
        if not action.get("name") or not action.get("value"):
            return actions
        try:
            self.last_stage, self.last_score = ("loop138b-fix137", 1.0)
        except AttributeError:
            pass
        return [action]

    # -- (5) 144 two-"of" names (+ stacked vetoes) --------------------------
    def _upgrade144(self, actions: list[dict], turn: str) -> list[dict]:
        if not (len(actions) == 1 and actions[0].get("act") == "clarify"
                and "split that" in str(actions[0].get("text", "")).lower()
                and getattr(self, "nb", None) is not None):
            return actions
        parsed = L144._parse_single_teach(turn)
        if parsed is None:
            return actions
        triple, correction = parsed
        if L102.subject_is_hearsay_shaped(triple[0]):
            return actions
        if F144.screen_value_144(triple[2]) is not None:
            return actions
        stripped_v = P129.strip_sentence_punct(triple[2])
        if V139b.screen_value_139b(
                stripped_v if stripped_v else triple[2]) is not None:
            return actions  # stacked 139b veto
        verdict, _clean = S150.screen_subject_150(triple[0])
        if verdict != "store":
            return actions  # stacked 150 veto
        try:
            if correction:
                action = self._structured_correct(triple)  # type: ignore[attr-defined]
            else:
                action = self._bench73_action(triple)  # type: ignore[attr-defined]
        except AttributeError:
            return actions
        action = T140.sanitize_action(action)
        action["stage"] = "loop138b-ofname"
        self.last_stage, self.last_score = ("loop138b-ofname", 1.0)
        return [action]

    # -- (8) 132 relative-clause rewriter (149-qrewrite shape) --------------
    def _rewrite132(self, actions: list[dict], turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if not (text and text.rstrip().endswith("?")
                and getattr(self, "nb", None) is not None):
            return actions
        if not actions or any((not isinstance(a, dict))
                              or a.get("act") != "clarify" for a in actions):
            return actions  # asks (incl. 148b-tagged) + teaches pass through
        try:
            triples = L90.notebook_triples(self.nb)
            newq, _info = Q132.rewrite_question(text, triples)
        except Exception:
            return actions
        if newq == text:
            return actions
        save_stage, save_score = self.last_stage, self.last_score
        try:
            second = super().hear(newq)
        except Exception:
            self.last_stage, self.last_score = save_stage, save_score
            return actions
        # Tagged asks (148b screen on the rewrite) are honoured, never
        # answered around: only a real ask converts the clarify.
        second = T140.sanitize_actions(second)
        if second and all(isinstance(a, dict) for a in second) and any(
                a.get("act") == "ask" and not a.get("screen148b")
                for a in second):
            self.last_stage, self.last_score = ("loop138b-rewrite", 1.0)
            return second
        if second and any(isinstance(a, dict) and a.get("screen148b")
                          for a in second if a.get("act") == "ask"):
            self.last_stage, self.last_score = (
                "loop138b-rewrite-screened", 1.0)
            return second
        self.last_stage, self.last_score = save_stage, save_score
        return actions


class Loop138bMouth(L148b.ScreenTextMouth148b, L138.Loop138Mouth):
    """Loop138Mouth + exact 148 screen texts for marked records."""

    name = "loop138b-mouth"


# ------------------------------------------------------------ loop (L2 frozen)
class Loop138bAgentLoop(L138.Loop138AgentLoop):
    """Loop138AgentLoop + 148b tag-carry + 140/139b/150 pre-write guards.

    turn() is inherited VERBATIM from loop138 (L2 router + Self99 live
    answers + decline rule unchanged -- other agents own the self layer).
    """

    def _ask138b(self, name: str, relations: list[str],
                 entity_id: str | None = None) -> dict:
        tag = getattr(self, "_screen148b_tag", None)
        record = self.reasoner.answer(
            {"name": name, "relations": relations, "entity_id": entity_id,
             **({"screen148b": tag} if tag else {})}, self.nb)
        self.counters["answers"] += 1
        if record.get("status") == C.AMBIGUOUS:
            self.question_pending = {"name": name, "relations": relations,
                                     "ids": list(record["fields"].get(
                                         "ids", []))}
        return record

    def _act(self, action: dict) -> dict:
        if isinstance(action, dict) and action.get("act") == "ask" and \
                action.get("screen148b") in ("neg", "time"):
            self._screen148b_tag = action["screen148b"]
            try:
                return self._ask138b(action.get("name", ""),
                                     list(action.get("relations") or []),
                                     action.get("entity_id"))
            finally:
                self._screen148b_tag = None
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct"):
            action = T140.sanitize_action(action)
            checked = copy.copy(action)
            cleaned = P129.strip_sentence_punct(checked.get("value", ""))
            if cleaned:
                checked["value"] = cleaned
            msg = V139b.screen_value_139b(checked.get("value", ""))
            if msg is not None:
                self.counters["clarifications"] += 1
                return {"kind": "clarify", "text": msg}
            cleaned_n = P129.strip_sentence_punct(checked.get("name", ""))
            if cleaned_n:
                checked["name"] = cleaned_n
            verdict, payload = S150.screen_subject_150(
                checked.get("name", ""))
            if verdict in ("split", "hearsay"):
                self.counters["clarifications"] += 1
                return {"kind": "clarify", "text": payload}
            action = checked
        return super()._act(action)


DEFAULT_CONFIG138B: dict = copy.deepcopy(L138.DEFAULT_CONFIG138)
DEFAULT_CONFIG138B["ears"]["stand_in"] = (
    "Loop138bEars (loop138 + 135 officeholder guard + 137 2-4-token "
    "possessive subjects + 139b value guard + 140 tail cleaner + 144 "
    "of-name upgrade + 150 subject guard + 149 whole-word match + 132 "
    "rewriter + 151 no-? twin + 148b neg/time screen, in that order)")
DEFAULT_CONFIG138B["mouth"]["stand_in"] = (
    "Loop138bMouth (Loop138Mouth + 148b screen texts for marked records)")
DEFAULT_CONFIG138B["daemon"]["module"] = "Loop138bDaemon (this file)"
DEFAULT_CONFIG138B["sleep"] = {
    "retrofit": "Sleep145Reasoner + Sleep145Sleeper via retrofit_sleep145",
    "recipe": "exp-46 recipe + taught-beats-sleep answer rule (all words)",
}


def build_agent138b(cfg: dict | None = None) -> Loop138bAgentLoop:
    """Build the loop138 agent shape with the 138b stack swapped in."""
    cfg = dict(DEFAULT_CONFIG138B, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop138bMouth()
    reasoner = L148b.ScreenStatusReasoner148b()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop138bAgentLoop(
        state_dir, ears=Loop138bEars(Loop96Ears(chain)), mouth=mouth,
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
    loop._screen148b_tag = None
    # L2 live-self state (Self99-shaped logs owned by the loop; turn()
    # maintains them exactly as loop138 -- frozen by director order).
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    # L3 sleep145 (grow-slot + taught-beats-sleep; no-op until a word
    # installs; serving files sleep145-* so sealed 104/131 state is
    # never touched).
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138b: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop138bDaemon(L138.Loop138Daemon):
    """Loop138Daemon shape with the 138b agent inside + 141 settle gate.

    process_file is inherited unchanged from Loop138Daemon (108 receipts
    + routed log + 104-schema sleep-event logs). run() serves only settled
    files (141 rule A/B) and skips tmp/dot files; writers use tmp+rename
    (atomic-write client rule). Name ends in Daemon / starts with Loop so
    the marks123 loader picks this class.
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
        self.loop = build_agent138b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)

    def settled_files(self) -> list[Path]:
        files = sorted(p for p in self.inbox.glob("*.txt")
                       if not p.name.startswith(".")
                       and ".tmp" not in p.name)
        self.settle.prune({p.name for p in files})
        now = time.monotonic()
        return [p for p in files if self.settle.is_settled(p, now)]

    # Mirror of D74.Daemon.run with THE ONE CHANGE (line marked [138b]):
    # the poll serves only settled files. Everything else identical.
    def run(self) -> int:
        for stale in self.outbox.glob("*.tmp*"):
            try:
                stale.unlink()
            except OSError:
                pass
        status = self.boot_status()
        D74._atomic_write(self.status_path,
                          json.dumps(status, indent=1, sort_keys=True))
        D74._append_log(self.log_path,
                        {"t": D74._now_iso(), "event": "boot", **status})
        self.write_heartbeat()
        last_heartbeat = time.time()
        last_activity = time.time()
        last_idle_tick = 0.0
        while True:
            if self.stop_file.exists():
                D74._append_log(self.log_path,
                                {"t": D74._now_iso(),
                                 "event": "stop-file-seen"})
                self.write_heartbeat()
                D74._append_log(self.log_path,
                                {"t": D74._now_iso(), "event": "stopped"})
                return 0
            files = self.settled_files()  # [138b] THE ONE CHANGE
            if files:
                for path in files:
                    if self.stop_file.exists():
                        break
                    try:
                        self.process_file(path)
                    except C.LogCorrupt as exc:
                        D74._append_log(
                            self.log_path,
                            {"t": D74._now_iso(), "event": "log-corrupt",
                             "file": path.name, "error": str(exc)})
                last_activity = time.time()
            else:
                now = time.time()
                if (now - last_activity >= self.idle_seconds
                        and now - last_idle_tick >= self.idle_seconds):
                    event = self.loop.step()
                    last_idle_tick = now
                    D74._append_log(
                        self.log_path,
                        {"t": D74._now_iso(), "event": "idle-tick",
                         "mode": event["mode"],
                         "detail": str(event["detail"])[:300],
                         "counters": dict(self.loop.counters)})
            if time.time() - last_heartbeat >= D74.HEARTBEAT_EVERY_S:
                self.write_heartbeat()
                last_heartbeat = time.time()
            time.sleep(D74.POLL_S)


def atomic_write_text(path: Path, text: str) -> None:
    """Atomic-write client rule: write tmp in the same dir, then rename."""
    import os as _os
    tmp = Path(str(path) + ".tmp%d" % _os.getpid())
    tmp.write_text(text, encoding="utf-8")
    _os.replace(tmp, path)


def run_daemon138b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop138bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 138b stacked loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG138B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG138B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
