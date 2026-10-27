#!/usr/bin/env python3
"""Experiment 138i -- MERGE LAYER B PART 2 onto loop138h (Muse).

loop138i = loop138h + NINE verified pieces ported read-only as mixins.
New files only; no existing file edited. loop155 stays OUT (no 155 class
in the MRO, no fable_loop155* module imported -- verified by the M1
driver check).

PORTED (each verified by the director; rule bodies imported read-only):

(1) 154e multi-valued allow-list incl. language (contains 154c;
    artifacts/fable-lang154e-20260922/). The 154c/154e loop classes sit
    on the 138b lineage so they cannot be stacked directly (that would
    drag the 138b base). Ported as TWO new wrappers in THIS file (same
    pattern the 138h port plan §7 prescribes for 154c):
    Multival154eMixin.hear = Loop154eEars.hear
    (scripts/fable_loop154e_agent.py:68, which is Loop154cEars.hear with
    the gate widened to is_multi154e) with the fallthrough adapted to
    cooperative super().hear() so the full 138h chain stays in the path;
    Multival154eMixin._act = Loop154cAgentLoop._act
    (scripts/fable_loop154c_agent.py:131, gate widened to is_multi154e
    per Loop154eAgentLoop._act, scripts/fable_loop154e_agent.py:113)
    with L138b-direct calls adapted to cooperative super() so 171's
    screen (inside) still sees every teach. The leaf handlers are
    loop154b's, called UNBOUND read-only where they make no super() call
    (_act_correct_multi154b :134, _act_forget_one154b :183,
    _post_ask154e = Loop154eAgentLoop._post_ask154e
    scripts/fable_loop154e_agent.py:132); _act_multi_teach154b
    (:219, which calls super()._act and so cannot run unbound) is
    inlined here (10 lines: resolve others, force teach, cooperative
    super, append the "(I also have …)" parenthetical).
    Gate: scripts/fable_fix154e_allowlist.py:is_multi154e (154C set +
    language). Screens: V139b.screen_value_139b + S150.screen_subject_150
    (same inline re-check 154c does, :95-100).
(2) 172b copula re-teach asks (artifacts of exp 172b; the v3 sealed case
    set on the loop172 rule). Ported as Copula172Mixin.hear in THIS file
    = Loop172Ears.hear (scripts/fable_loop172_agent.py:109: super first,
    then downgrade) with ONE adapted gate: the downgrade keeps
    allow-listed keys, where allow-listed = is_multi154e (154e superset)
    instead of is_multi154c, so language re-teaches keep the 154e
    multi-add path. has_correction_prefix172 is imported read-only.
    Sits OUTSIDE the 154e port (sealed: Loop172Ears extends
    Loop154cEars).
(3) 171b word-names in values (contains 171; stacked OUTSIDE 171 per
    sealed scripts/fable_loop171b_agent.py:49,55):
    NameVal171BMixin (scripts/fable_fix171b_nameval.py:127) outside
    NameVal171Mixin (scripts/fable_fix171_nameval.py:170). Innermost-B
    (port plan §12) so delegation twins pass the hear screen and the
    _act backstop covers outer mixins' self-built teaches.
(4) 173b user word-names (scripts/fable_fix173b_username.py:181
    Name173bMixin), REPLACING 173's slot: stacked OUTSIDE Name173Mixin
    (the exact verified composition of Loop173bEars,
    scripts/fable_loop173b_agent.py:44: 173b > 173). 173b claims
    word-name statements; 173-accept-but-173b-reject turns bypass to
    Loop166Ears; questions/x-heads/namecheck keep 173's code via
    super(). The loop-level 173 _act namecheck router + rendering stay
    (138h's, unchanged; loop173b's loop class adds nothing).
    PREDICTED MOVE: 138h's G3h-4a "My name is Juno." now saves.
(5) 167e all reply templates (contains 167c): mouth-side only.
    Label167eMouth (scripts/fable_fix167e_label.py:149) wraps the same
    Loop138bMouth 138h uses. render_label already applies the 167c Saved
    rule first, so one wrap is the sealed 167e surface (M1-167e proves).
(6) 167d verb table (works at -> employer, speaks -> language;
    scripts/fable_fix167d_verb.py:193 Verb167dMixin): stacked INSIDE
    ValueScreen167b (sealed scripts/fable_loop167d_agent.py:52) and
    OUTSIDE Verb167 (disjoint shapes: only the two NEW verb pairs +
    their two questions; everything 167 owns falls through untouched).
(7) 154d grounded yes/no (scripts/fable_fix154d_yesno.py:172
    YesNo154dMixin): loop-level _listening_tick outside 138h's tick.
    Fires only on the miss (138h's R-CLARIFY contains
    "didn't understand that", the 154d trigger); grounded frames answer
    from notebook reads only, never write.
(8) 174 "of"-chain questions (scripts/fable_fix174_chainof.py:101
    ChainOf174Mixin): outermost ears (its own sealed position); probes
    super().hear(candidate) and takes it iff the base parses an ask.
(9) 170 speed index: install_index170()
    (scripts/fable_fix170_compose.py:622, called once like
    scripts/fable_loop170_agent.py:38-40) unless FABLE138I_INDEX=off
    (the G4 off-arm; default on).

Ears order (outermost first):
  ChainOf174 > Typo165 > ValueScreen167b > Verb167d > Verb167 >
  Name173b > Name173 > Me166 > Plural162b > Copula172 > Multival154e >
  NameVal171b > NameVal171 > Loop138gEars.
Preserves every sealed relative order (167b>167d? both inside the one
screen; 167d>167 disjoint; 165>162b; 173b>173>166; Me166>162b; 172>154e;
171b>171). Loop _act: 154e-multi > 171b > 171 > 173-namecheck > 138g tail
chain. _listening_tick: 154d yes/no peek, then 138h 173/166/166c
rendering. turn(): 138g 168 shape + 138h raw-USER backstop (unchanged).
Reasoner/notebook/sleep/daemon: 138g unchanged (Reasoner138d,
IndexedLoopNotebook, sleep145 retrofit, settle + exactly-once daemon
with idle_seconds).

KNOWN OVERLAP (predicted before running; M1 lists case by case):
  MULTI_VALUED_154C ∩ NAME_KEYS = {sister, brother, sibling, friend,
  child, son, daughter, colleague, dog, cat}: description values on
  these keys clarify via 171 (the multi _act re-enters cooperatively so
  the screen still sees them); name values multi-add via 154e.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138i_agent.py --daemon --dir DIR \\
    --config artifacts/fable-agent138i-20260922/loop138i-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import os
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
import fable_fix139b_valueguard as V139B  # noqa: E402 (154e value screen)
import fable_fix150_subjectguard as S150  # noqa: E402 (154e subject screen)
import fable_fix154b_multival as M154  # noqa: E402 (154b forms, read-only)
import fable_fix154e_allowlist as M154E  # noqa: E402 (154e gate, read-only)
import fable_fix162b_plural as B162  # noqa: E402 (162b plural mixin, read-only)
import fable_fix165_typo as T165  # noqa: E402 (165 typo mixin, read-only)
import fable_fix166_me as M166  # noqa: E402 (166 me mixin, read-only)
import fable_fix167_verb as V167  # noqa: E402 (167 verb mixin, read-only)
import fable_fix167b_valuescreen as S167B  # noqa: E402 (167b screen, read-only)
import fable_fix167d_verb as V167D  # noqa: E402 (167d verb mixin, read-only)
import fable_fix167e_label as L167E  # noqa: E402 (167e mouth, read-only)
import fable_fix171_nameval as N171  # noqa: E402 (171 guard, read-only)
import fable_fix171b_nameval as N171B  # noqa: E402 (171b guard, read-only)
import fable_fix173_username as N173  # noqa: E402 (173 name mixin, read-only)
import fable_fix173b_username as N173B  # noqa: E402 (173b name mixin, read-only)
import fable_fix174_chainof as C174  # noqa: E402 (174 rewrite, read-only)
import fable_loop102_agent as L102  # noqa: E402 (HEARSAY_MSG, read-only)
import fable_loop134_agent as L134  # noqa: E402 (138b turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (router + decline, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (donor stack, read-only)
import fable_loop138f_agent as L138F  # noqa: E402 (wrapped stack, read-only)
import fable_loop138g_agent as L138G  # noqa: E402 (wrapped stack, read-only)
import fable_loop138h_agent as L138H  # noqa: E402 (wrapped stack, read-only)
import fable_loop154b_agent as L154B  # noqa: E402 (multi handlers, read-only)
import fable_loop154e_agent as L154E  # noqa: E402 (154e post-ask, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop166_agent as L166  # noqa: E402 (me reply rewrite, read-only)
import fable_loop166c_agent as C166  # noqa: E402 (display-case, read-only)
import fable_loop172_agent as L172  # noqa: E402 (copula prefix, read-only)
import fable_loop173_agent as L173  # noqa: E402 (name reply rewrite, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_fix170_compose import install_index170  # noqa: E402 (170, read-only)
from fable_fix154d_yesno import YesNo154dMixin  # noqa: E402 (154d, read-only)
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

# 170 speed index: installed once at import (same pattern as
# scripts/fable_loop170_agent.py:38-40). FABLE138I_INDEX=off skips it
# (the G4 off-arm runs in a separate process with this set).
if os.environ.get("FABLE138I_INDEX", "on") != "off":
    install_index170()


def _norm(text: object) -> str:
    return " ".join(str(text).split())


# --------------------------------- the 154e port (two wrappers, this file)
def _wrap_relation154e(loop) -> None:
    """Instance-level Listening._relation: 154e allow-listed keys
    (154c set + language) are non-functional; everything else functional
    (mirrors scripts/fable_loop154e_agent.py:42 with the 154e gate)."""
    listening = loop.listening
    nb = loop.nb

    def _relation154e(relation: str) -> None:
        known = {e["relation"] for e in nb.events if e["kind"] == "RELATION"}
        if relation not in known:
            nb.declare_relation(listening._eid("rel"), relation,
                                not M154E.is_multi154e(relation))

    listening._relation = _relation154e  # type: ignore[method-assign]


class Multival154eMixin:
    """154e ears pre-scan + _act router (this file; adapted cooperative).

    hear = Loop154eEars.hear (scripts/fable_loop154e_agent.py:68) with
    the fallthrough adapted to super().hear() (154c called the 138b ears
    directly; here the full 138h chain stays in the path). _act =
    Loop154cAgentLoop._act (scripts/fable_loop154c_agent.py:131, gate
    widened to is_multi154e per Loop154eAgentLoop._act) with L138b-direct
    calls adapted to cooperative super() so 171's screen (inside) still
    sees every teach.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        if nb is not None:
            parsed = M154.parse_correct_not154b(turn)
            if parsed is not None and M154E.is_multi154e(parsed["relation"]):
                if nb.resolve(parsed["name"]).status == C.OK:
                    if V139B.screen_value_139b(parsed["new"]) is None and \
                            S150.screen_subject_150(parsed["name"])[0] == "store":
                        try:
                            self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                                "loop138i-correct-not", 1.0)
                        except AttributeError:
                            pass
                        return [{"act": "correct_multi154b",
                                 "name": parsed["name"],
                                 "relation": parsed["relation"],
                                 "rel_key": parsed["relation"],
                                 "new": parsed["new"], "old": parsed["old"],
                                 "raw": turn}]
            forgotten = M154.parse_forget_one154b(turn, nb)
            if forgotten is not None and \
                    M154E.is_multi154e(forgotten["relation"]):
                try:
                    self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                        "loop138i-forget-one", 1.0)
                except AttributeError:
                    pass
                return [{"act": "forget_one154b",
                         "name": forgotten["name"],
                         "relation": forgotten["relation"],
                         "rel_key": forgotten["relation"],
                         "value": forgotten["value"],
                         "entity_id": forgotten["entity_id"],
                         "raw": turn}]
        return super().hear(turn)  # type: ignore[misc]

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") == "correct_multi154b":
            return L154B.Loop154bAgentLoop._act_correct_multi154b(
                self, action)
        if isinstance(action, dict) and action.get("act") == "forget_one154b":
            return L154B.Loop154bAgentLoop._act_forget_one154b(self, action)
        if isinstance(action, dict) and action.get("act") in ("teach", "correct"):
            key = M154.relation_key154b(str(action.get("relation", "")))
            if M154E.is_multi154e(key) and action.get("name") and \
                    action.get("value"):
                return self._act_multi_teach138i(action, key)
            return super()._act(action)  # type: ignore[misc]
        if isinstance(action, dict) and action.get("act") == "ask":
            record = super()._act(action)  # type: ignore[misc]
            if (isinstance(record, dict) and record.get("kind") == "answer"
                    and record.get("status") == C.OK):
                return L154E.Loop154eAgentLoop._post_ask154e(
                    self, action, record)
            return record
        return super()._act(action)  # type: ignore[misc]

    def _act_multi_teach138i(self, action: dict, key: str) -> dict:  # type: ignore[no-redef]
        """Loop154bAgentLoop._act_multi_teach154b
        (scripts/fable_loop154b_agent.py:219) inlined: it calls
        super()._act, which cannot run unbound, so the 10-line body lives
        here with a cooperative super() (171's screen, inside, still sees
        the teach -- this keeps description values on overlapping
        multi∩name keys clarifying via 171)."""
        nb = self.nb  # type: ignore[attr-defined]
        incoming = str(action.get("value", ""))
        others: list[str] = []
        resolved = nb.resolve(str(action.get("name", "")))
        if resolved.status == C.OK:
            others = [v for v in M154.current_values154b(
                nb, resolved.detail["entity_id"], key) if v != incoming]
        record = super()._act(dict(action, act="teach"))  # type: ignore[misc]
        if (isinstance(record, dict) and bool(record.get("wrote"))
                and others and isinstance(record.get("text"), str)):
            record = dict(record)
            record["text"] = (record["text"]
                              + f" (I also have {M154.join_and154b(others)}.)")
        return record


# ------------------------------ the 172b port (one wrapper, this file)
def _downgrade172_154e(turn: str, actions: list[dict]) -> list[dict]:
    """Loop172 downgrade172 (scripts/fable_loop172_agent.py:86) with the
    keep-gate widened to is_multi154e: correct->teach for non-allow
    structured re-teaches without an explicit correction prefix. On 154c
    keys the behaviour is byte-identical to sealed 172; on language (in
    154e only) the 154e multi-add path is preserved."""
    if not isinstance(actions, list) or not actions:
        return actions
    if L172.has_correction_prefix172(turn):
        return actions
    out = []
    for a in actions:
        if (isinstance(a, dict) and a.get("act") == "correct"
                and a.get("name") and a.get("value")):
            key = M154.relation_key154b(str(a.get("relation", "")))
            if not M154E.is_multi154e(key):
                a = dict(a, act="teach")
        out.append(a)
    return out


class Copula172Mixin:
    """172b ears post-process (this file) = Loop172Ears.hear
    (scripts/fable_loop172_agent.py:109) with the 154e gate above. Sits
    OUTSIDE the 154e port (sealed: Loop172Ears extends Loop154cEars)."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        fixed = _downgrade172_154e(turn, actions)
        if any(f is not a for f, a in zip(fixed, actions)
               if isinstance(f, dict) and isinstance(a, dict)):
            try:
                self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                    "loop138i-copula-ask", 1.0)
            except AttributeError:
                pass
        return fixed


# ------------------------------------------------- ears: merge layer B2
class Loop138iEars(C174.ChainOf174Mixin, T165.Typo165Mixin,
                   S167B.ValueScreen167bMixin, V167D.Verb167dMixin,
                   V167.Verb167Mixin, N173B.Name173bMixin, N173.Name173Mixin,
                   M166.Me166Mixin, B162.Plural162bMixin, Copula172Mixin,
                   Multival154eMixin, N171B.NameVal171BMixin,
                   N171.NameVal171Mixin, L138G.Loop138gEars):
    """Loop138gEars + layer-B2 stages, each cooperative: unclaimed turns
    fall through to super().hear() untouched. Sealed relative orders kept
    (174 outermost; 165>162b; screen>167d; screen>167; 173b>173>166;
    Me166>162b; 172>154e; 171b>171 innermost-B).
    """

    name = "loop138i-layer-b2"


# ------------------------------------------- loop: 138h + 154e/154d/171
class Loop138iAgentLoop(YesNo154dMixin, Multival154eMixin,
                        N171B.NameVal171BMixin, N171.NameVal171Mixin,
                        L138H.Loop138hAgentLoop):
    """Loop138hAgentLoop + 154d yes/no peek (outermost tick) + 154e multi
    _act (outside 171 so multi-adds re-pass the 171 screen cooperatively)
    + 171b/171 _act backstop. _act namecheck/turn/_listening_tick render
    inherited from 138h (173b needs no loop-level change: loop173b's loop
    class adds nothing over loop173's). Mouth wrapped by the builder.
    """


DEFAULT_CONFIG138I: dict = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
DEFAULT_CONFIG138I["ears"]["stand_in"] = (
    "Loop138iEars (loop138h stack + layer B2 outside-in: 174 of-chain, "
    "167d verbs, 173b word-names over 173, 172b copula over 154e multi "
    "incl. language, 171b word-names over 171; 167e label mouth; 154d "
    "yes/no tick; 170 index)")
DEFAULT_CONFIG138I["daemon"]["module"] = "Loop138iDaemon (this file)"
DEFAULT_CONFIG138I["self"] = dict(L138H.DEFAULT_CONFIG138H.get("self", {}))


def build_agent138i(cfg: dict | None = None) -> Loop138iAgentLoop:
    """Build the loop138h agent shape with merge layer B2 stacked on."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG138I, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L167E.Label167eMouth(L138b.Loop138bMouth())
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop138iEars(Loop96Ears(chain))
    loop = Loop138iAgentLoop(
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
    # 154e relation functionality (instance-level Listening._relation
    # patch: allow-listed keys incl. language are non-functional).
    _wrap_relation154e(loop)
    # L3 sleep145 (grow-slot + taught-beats-sleep; serving files
    # sleep145-* so sealed 104/131 state is never touched).
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138i: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop138i: loop138h + merge layer B2 (154e multi "
                      "incl. language + 172b copula + 171b over 171 + "
                      "173b over 173 + 167e labels + 167d verbs + 154d "
                      "yes/no + 174 of-chain + 170 index; 155 stays OUT)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop138iDaemon(L138H.Loop138hDaemon):
    """Loop138hDaemon shape with the 138i agent inside."""

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
        self.loop = build_agent138i(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon138i(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop138iDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 138i merge layer B2")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138h)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG138I to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138I)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG138I)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138i(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138i(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
