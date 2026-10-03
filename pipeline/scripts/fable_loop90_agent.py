#!/usr/bin/env python3
"""Experiment 90 -- INTEGRATION build: one loop composing every verified piece.

Factory ``build_agent(cfg)`` returns an AgentLoop-compatible object where:

  notebook = Loop90Notebook: GatedThoughtNotebook (fix77 rule-2 gate) with the
             VerifiedNotebook tail-seal discipline (verify on open via
             fix77.verify_full, advance the sidecar seal on every save).
  reasoner = Reasoner77 (QualifierAwareReasoner77: qual56 hop loop + bool fix).
  ears     = ChainEars: [bench73 template stage now; ears47:<ckpt> adapter
             when a checkpoint exists; FakeEars template stage for M1-style
             turns], every stage score gated by the certified abstention
             thresholds tau-hat read at run time from the exp-76 JSON
             (score < tau-hat -> abstain/CLARIFY, never write).
  mouth    = FakeMouth now; the Mouth Protocol slot is documented for mouth53.
  thinker  = exp-89 fixed Thinking wrapper if scripts/fable_webfix89_thinking.py
             exists at run time, else the m2 Thinking wrapper (import guarded).
  sleeper  = HardGate46Sleeper: the exp-46 recipe (robust loss + harden-before-
             gate + unchanged gate) called, not re-implemented.
  all behind the daemon74 mailbox (Loop90Daemon).

Additive only: every other module is imported read-only and wrapped or
subclassed here. Nothing outside this file is edited.

Run examples (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop90_agent.py --write-config /tmp/loop90.json
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop90_agent.py --daemon --dir DIR --config CFG
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (Protocols + AgentLoop base, read-only)
import fable_bench73_english_arm as B73  # noqa: E402 (template ears, read-only)
import fable_daemon74_run as D74  # noqa: E402 (mailbox daemon base, read-only)
import fable_fix77_core as F77  # noqa: E402 (gate + reasoner + seal, read-only)
import fable_listening_m1 as L  # noqa: E402 (doorway, read-only)
import fable_notebook_contract as C  # noqa: E402 (contract, read-only)
from fable_wire51_adapters import HardGate46Sleeper, NotebookThinker  # noqa: E402

ROOT = SCRIPTS.parent
TAU_PATH_DEFAULT = (ROOT / "artifacts" / "fable-abstain76-20260921"
                    / "ltt_summary.json")
MOUTH53_MODULE = "fable_mouth53_mouth"

try:
    import fable_webfix89_thinking as W89  # noqa: E402 (exp-89 fix, if landed)
    THINKER_MODULE = "fable_webfix89_thinking"
except ImportError:
    W89 = None
    THINKER_MODULE = "fable_thinking_m2"


def load_tau_hat(path=None) -> dict:
    """Certified write thresholds, read from the exp-76 JSON (never hard-coded)."""
    with open(path or TAU_PATH_DEFAULT, encoding="utf-8") as handle:
        return dict(json.load(handle)["tau_hat"])


# ------------------------------------------------------------------ notebook
class Loop90Notebook(F77.GatedThoughtNotebook):
    """GatedThoughtNotebook semantics + VerifiedNotebook seal discipline.

    verify_full() on every clean open (raises LogCorrupt on a tail edit);
    the sidecar seal advances on every loop save (see Loop90AgentLoop._save).
    A torn tail loads with the flag set (legacy crash-recovery behaviour);
    the loop repairs first, then seals.
    """

    def __init__(self, root) -> None:
        super().__init__(root)
        if self.torn_tail:
            return
        F77.verify_full(self.root)

    def advance_seal(self) -> None:
        try:
            F77._write_seal(Path(self.root), len(self.events), self.last_sha)
        except OSError:
            pass


# ------------------------------------------------------------------ ears chain
def _display(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], value["entity"])
    return str(value.get("literal", ""))


def notebook_triples(nb) -> list[tuple[str, str, str]]:
    """Active taught facts as (subject-name, relation, value-display).

    This is the triple context bench73's compose_question needs; here it is
    sourced from the loop's own notebook (post-edit values only, because
    superseded rows are inactive).
    """
    out = []
    for fact in nb.facts.values():
        if fact.get("source") != "taught" or not nb.active(fact["fact_id"]):
            continue
        out.append((nb.entities.get(fact["subject"], "?"),
                    fact["relation"], _display(nb, fact["value"])))
    return out


class Bench73Stage:
    """bench73 template ears as a ChainEars stage (deterministic 1.0 / 0.0)."""

    name = "bench73"

    def __init__(self, family: str = "tape") -> None:
        self.family = family
        self.nb = None

    def bind(self, nb) -> None:
        self.nb = nb

    def hear(self, turn: str, tau: dict) -> tuple[list[dict], float] | None:
        text = " ".join(str(turn).split())
        if not text:
            return None
        triples = notebook_triples(self.nb) if self.nb is not None else []
        # Questions first when the turn asks, teaches first otherwise.
        if text.rstrip().endswith("?"):
            frame = B73.compose_question(text, triples)
            if frame is not None:
                return ([{"act": "ask", "name": frame[0],
                           "relations": list(frame[1])}], 1.0)
            triple = B73.hear_teach_template(text)
            if triple is not None:
                return ([self._teach_action(triple)], 1.0)
            return None
        triple = B73.hear_teach_template(text)
        if triple is not None:
            return ([self._teach_action(triple)], 1.0)
        frame = B73.compose_question(text, triples)
        if frame is not None:
            return ([{"act": "ask", "name": frame[0],
                       "relations": list(frame[1])}], 1.0)
        return None

    def _teach_action(self, triple: tuple[str, str, str]) -> dict:
        subj, rel, obj = triple
        act = "teach"
        if self.nb is not None:
            found = self.nb.resolve(subj)
            if found.status == C.OK:
                eid = found.detail["entity_id"]
                for fact in self.nb.facts.values():
                    if (fact.get("subject") == eid and fact.get("relation") == rel
                            and fact.get("source") == "taught"
                            and self.nb.active(fact["fact_id"])):
                        if _display(self.nb, fact["value"]) != obj:
                            act = "correct"  # same (s,r), new object: supersede
                        break
        # Every bench value is entity-like (bench65 teaches ALL values as
        # entities); the "->" arrow keeps mid-chain hops entity-valued.
        return {"act": act, "name": subj, "relation": rel, "value": obj,
                "is_person": True, "structured": True, "stage": "bench73"}


class FakeStage:
    """M1-style template ears as a ChainEars stage (FakeEars, deterministic)."""

    name = "fake"

    def __init__(self) -> None:
        self._fake = A.FakeEars()

    def bind(self, nb) -> None:
        pass

    def hear(self, turn: str, tau: dict) -> tuple[list[dict], float] | None:
        actions = self._fake.hear(turn)
        if len(actions) == 1 and actions[0].get("act") == "clarify":
            return None
        for action in actions:
            action["stage"] = "fake"
        return (actions, 1.0)


class Ears47Stage:
    """ears47:<ckpt> neural adapter stage (abstains until decode is validated).

    hear_teach is UNVALIDATED upstream (raises NotImplementedError), so this
    stage only ever answers questions via the shared compose_question over
    neurally-independent triples; until a checkpoint loads AND decodes, it
    abstains and the chain falls through.
    """

    name = "ears47"

    def __init__(self, ckpt: str, snapshot: str | None = None) -> None:
        self.adapter = B73.Ears47Adapter(ckpt, snapshot)
        self.nb = None
        self.ready = False
        self.skip_reason = ""
        try:
            self.adapter.load()
            self.ready = True
        except Exception as exc:  # noqa: BLE001 -- offline / no snapshot yet
            self.skip_reason = f"ears47 unavailable: {exc}"

    def bind(self, nb) -> None:
        self.nb = nb

    def hear(self, turn: str, tau: dict) -> tuple[list[dict], float] | None:
        if not self.ready:
            return None
        try:
            self.adapter.hear_teach(turn)
        except NotImplementedError:
            pass  # neural teach decode unvalidated: abstain, never guess
        except Exception:
            return None
        return None


class ChainEars:
    """Pluggable ears chain with the certified abstention gate.

    Stages are tried in order; a stage whose score < tau-hat abstains and the
    chain falls through. Total miss -> a single CLARIFY (never a write).
    """

    def __init__(self, cfg: dict) -> None:
        ears_cfg = dict(cfg.get("ears") or {})
        self.tau = load_tau_hat(ears_cfg.get("tau_hat_path"))
        self.family = str(ears_cfg.get("tau_family", "tape"))
        self.tau_hat = float(self.tau[self.family])
        self.stages: list = []
        self.stage_names: list[str] = []
        for name in ears_cfg.get("chain", ["bench73", "fake"]):
            if name == "bench73":
                self.stages.append(Bench73Stage(self.family))
            elif name == "fake":
                self.stages.append(FakeStage())
            elif name.startswith("ears47:"):
                self.stages.append(
                    Ears47Stage(name.split(":", 1)[1],
                                ears_cfg.get("snapshot")))
            else:
                raise ValueError(f"unknown ears stage {name!r}")
        self.stage_names = [s.name for s in self.stages]
        # Auto-append the ears47 adapter when a checkpoint exists and the
        # config did not name one (plug-in slot, template stays first).
        if "ears47" not in self.stage_names:
            ckpts = B73.fable_bench73_find_checkpoints()
            if ckpts:
                self.stages.append(Ears47Stage(str(ckpts[0]),
                                               ears_cfg.get("snapshot")))
                self.stage_names.append("ears47")
        self.last_stage = ""
        self.last_score = 0.0
        self.nb = None

    def bind(self, nb) -> None:
        self.nb = nb
        for stage in self.stages:
            stage.bind(nb)

    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if not text:
            self.last_stage, self.last_score = "none", 0.0
            return [{"act": "clarify", "text": "I didn't catch anything."}]
        for stage in self.stages:
            try:
                got = stage.hear(text, self.tau)
            except Exception:
                continue
            if got is None:
                continue
            actions, score = got
            if score < self.tau_hat:
                continue  # certified gate: below tau-hat, never write
            self.last_stage, self.last_score = stage.name, float(score)
            return actions
        self.last_stage, self.last_score = "none", 0.0
        return [{"act": "clarify",
                 "text": "I didn't understand that. Could you say it another way?"}]


# ------------------------------------------------------------------ the loop
class Loop90AgentLoop(A.AgentLoop):
    """AgentLoop with the Loop90 notebook, structured teaches, seal on save."""

    def __init__(self, state_dir, *, ears=None, mouth=None, reasoner=None,
                 sleeper=None, thinker=None,
                 sleep_threshold: int = A.SLEEP_THRESHOLD) -> None:
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / A.STATE_NAME
        self.ears = ears or A.FakeEars()
        self.mouth = mouth or A.FakeMouth()
        self.reasoner = reasoner or A.LookupReasoner()
        self.sleeper = sleeper or A.StubSleeper()
        self.thinker = thinker
        self.sleep_threshold = int(sleep_threshold)
        self.notes: list[str] = []
        self.last_records: list[dict] = []
        self.parts90: dict = {}

        self.nb = Loop90Notebook(self.dir / A.NOTEBOOK_DIR)
        if self.nb.torn_tail:  # crash mid-write: repair, then re-seal
            self.nb.repair_torn_tail()
            self.notes.append("repaired a torn notebook tail")
            F77.verify_full(self.nb.root)
        self.listening = L.Listening(self.nb)

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
        super()._save()
        nb = getattr(self, "nb", None)
        if nb is not None and hasattr(nb, "advance_seal"):
            nb.advance_seal()

    def _listening_tick(self) -> dict:
        text = self.inbox.pop(0)
        self.counters["turns"] += 1
        records = [self._act(action) for action in self.ears.hear(text)]
        self.last_records = records
        said = [line for line in (self.mouth.say(record) for record in records)
                if line]
        self.experience.append({"tick": self.tick, "kind": "turn", "text": text,
                                "statuses": [r.get("status", r["kind"])
                                             for r in records]})
        return self._event(A.LISTENING, {"turn": text, "records": records},
                           said)

    def _act(self, action: dict) -> dict:
        # Structured frame actions (bench73 stage) bypass the single-word line
        # renderer and call the doorway directly: same rights, same statuses,
        # multi-word names intact. Everything else uses the parent path.
        if action.get("structured") and action.get("act") in ("teach",
                                                              "correct"):
            arrow = "->" if action.get("is_person") else "="
            before = len(self.nb.events)
            try:
                text = self.listening._teach(
                    action["name"], action["relation"], arrow,
                    action["value"], action["act"] == "correct")
            except C.LogCorrupt as exc:
                text = ("I could NOT save that: the notebook reported a "
                        f"problem ({exc}).")
            wrote = len(self.nb.events) > before
            self.counters["writes"] += int(wrote)
            return {"kind": "write", "structured": action,
                    "text": text, "wrote": wrote,
                    "pending": self.listening.pending is not None}
        return super()._act(action)


# ------------------------------------------------------------------ factory
DEFAULT_CONFIG: dict = {
    "ears": {
        "chain": ["bench73", "fake"],
        "ears47_ckpt": None,
        "tau_hat_path": str(TAU_PATH_DEFAULT),
        "tau_family": "tape",
        "stand_in": "ChainEars(bench73 template + FakeEars templates)",
        "replacement": ("real ears: ears47 FrameEars checkpoint "
                        "(scripts/fable_ears47_model.py) via 'ears47:<ckpt>'"),
    },
    "notebook": {
        "class": "Loop90Notebook",
        "semantics": ("GatedThoughtNotebook (fix77 rule-2 gate) + "
                      "VerifiedNotebook tail-seal discipline"),
        "stand_in": "none -- this notebook IS the verified piece",
        "replacement": "none",
    },
    "reasoner": {
        "class": "QualifierAwareReasoner77",
        "module": "scripts/fable_fix77_core.py",
        "stand_in": "none -- this reasoner IS the verified piece",
        "replacement": "none",
    },
    "mouth": {
        "stand_in": "FakeMouth (template sentences, content words from record)",
        "replacement": "real mouth: scripts/fable_mouth53_mouth.py:Mouth",
    },
    "thinker": {
        "module": THINKER_MODULE,
        "stand_in": ("exp-89 QuarantinedThinking89 when "
                     "scripts/fable_webfix89_thinking.py exists at run time, "
                     "else m2 Thinking (quarantine + 2-site trust)"),
        "replacement": "no further replacement; web text stays quarantined",
    },
    "sleeper": {
        "recipe": ("HardGate46Sleeper: exp-46 recipe (robust loss eps=0.10, "
                   "harden phi +/-30, unchanged 4-fold gate), called via "
                   "scripts/fable_wire51_adapters.py"),
        "install_path": ("wire57 SparseVillageSleeper subclass + word bridge "
                         "(scripts/fable_wire57_e2e.py) once word episodes flow"),
        "stand_in": "recipe armed; episode feed idle until learned-word asks",
        "replacement": "scripts/fable_wire57_e2e.py install path",
    },
    "sleep_threshold": A.SLEEP_THRESHOLD,
    "daemon": {"module": "Loop90Daemon (daemon74 mailbox, this file)"},
}


def build_thinker(nb):
    import fable_thinking_m2 as M  # noqa: E402
    if W89 is not None and hasattr(W89, "QuarantinedThinking89"):
        thinking = W89.QuarantinedThinking89(nb, M.BridgeSearcher())
        return NotebookThinker(thinking), THINKER_MODULE
    thinking = M.Thinking(nb, M.BridgeSearcher())
    return NotebookThinker(thinking), THINKER_MODULE


def build_agent(cfg: dict | None = None) -> Loop90AgentLoop:
    """Build the integrated agent from a config dict (see DEFAULT_CONFIG)."""
    cfg = dict(DEFAULT_CONFIG, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    ears = ChainEars(cfg)
    mouth = A.FakeMouth()
    reasoner = F77.QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4102)
    loop = Loop90AgentLoop(
        state_dir, ears=ears, mouth=mouth, reasoner=reasoner,
        sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    ears.bind(loop.nb)
    thinker, thinker_module = build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(ears.tau), "tau_family": ears.family,
                    "tau_hat_used": ears.tau_hat,
                    "config": cfg}
    return loop


# ------------------------------------------------------------------ daemon
class Loop90Daemon(D74.Daemon):
    """daemon74 mailbox around the integrated loop (records land in the log)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.idle_seconds = float(idle_seconds)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)

    def process_file(self, path: Path) -> dict:
        import os as _os
        nb = self.loop.nb
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return {"event": "turn-skipped", "file": path.name}
        before_facts = set(nb.facts)
        before_entities = set(nb.entities)
        said = self.loop.turn(text)  # notebook append happens INSIDE first
        records = list(getattr(self.loop, "last_records", []))
        new_facts = sorted(set(nb.facts) - before_facts)
        new_entities = {eid: nb.entities[eid]
                        for eid in set(nb.entities) - before_entities}
        reply = " ".join(said) if said else "(nothing to say)"
        D74._atomic_write(self.outbox / path.name, reply + "\n")
        _os.replace(path, self.done / path.name)
        record = {"t": D74._now_iso(), "event": "turn", "file": path.name,
                  "turn_text": text.strip()[:200], "reply": reply[:500],
                  "records": records,
                  "ears_stage": getattr(self.loop.ears, "last_stage", ""),
                  "ears_score": getattr(self.loop.ears, "last_score", 0.0),
                  "new_fact_ids": new_facts, "new_entities": new_entities,
                  "turn_count": int(self.loop.counters.get("turns", 0)),
                  "notebook_events": len(nb.events)}
        D74._append_log(self.log_path, record)
        return record


def run_daemon(root, cfg: dict | None = None,
               idle_seconds: float = 30.0) -> int:
    daemon = Loop90Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


# ------------------------------------------------------------------ CLI
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 90 integrated loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (plug points + stand-ins)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = dict(DEFAULT_CONFIG)
        out["thinker"]["module"] = THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = dict(DEFAULT_CONFIG)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon(args.dir, cfg=cfg,
                          idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
