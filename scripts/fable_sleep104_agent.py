#!/usr/bin/env python3
"""Experiment 104 -- LIVE SLEEP INSTALL INSIDE THE loop96 DAEMON.

The loop96 daemon (scripts/fable_loop96_agent.py, built on
scripts/fable_loop90_agent.py) has the exp-46 sleep recipe armed
(HardGate46Sleeper via scripts/fable_wire51_adapters.py) but its episode
feed is idle: loop90 binds the sleeper with reasoner=None, and the live
reasoner (QualifierAwareReasoner77) never queues word episodes. Exp 57
(scripts/fable_wire57_e2e.py) showed the recipe installing
"maternal_grandmother" from 20 episodes outside any daemon.

This file closes the loop WITHOUT editing any existing file (additive
only: subclass + wrap + retrofit, everything else imported read-only):

  Sleep104Reasoner  wraps the loop's QualifierAwareReasoner77. On a bare
                    learned-word question (relations == [maternal_grand-
                    grandmother]) it walks the mother+mother chain in the
                    live notebook and -- when the chain resolves -- queues
                    one sleep episode (start, word 0, answer), exactly the
                    wire57 _queue_word_episode rule. Pre-install the inner
                    reasoner answers MISSING_FACT (word unknown); the
                    episode is still queued. Post-install it answers OK
                    through the installed logits; the wrapper then marks
                    the record source "sleep-derived" with the install
                    report row at the head of the trail (the hop rows stay
                    the taught FACTs they are -- the mark names the routing,
                    which came from sleep).
  Sleep104Sleeper   wire57's SparseVillageSleeper (the exp-46 recipe,
                    unchanged gate) + three additive steps after an
                    install: bridge the hardened logits into the live
                    reasoner, append one sleep-derived report row to the
                    notebook (actor "sleep", relation "sleep_report",
                    exp-52 convention), and persist the word atomically
                    (tmp + os.replace) so a restart finds it either fully
                    present or cleanly absent -- never half-installed. A
                    SLEEPING marker file brackets the recipe so the Z4
                    kill can land mid-SLEEP.
  Sleep104Daemon    Loop96Daemon + retrofit (reasoner/sleeper swap) +
                    per-turn sleep logging (wall-clock seconds, outcome).
  build_agent104    build_agent96, then the retrofit. Mailbox, ears chain,
                    guard, notebook, mouth, thinker, tau-hat gate: untouched.

Crash discipline: serving state = state_dir/sleep104-word.json (atomic).
torn .tmp files are ignored on boot. torch.save checkpoints from the
recipe are never trusted for serving (only the JSON is loaded).

Run (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_sleep104_agent.py --daemon --dir DIR --config CFG
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

import fable_agent_loop as A  # noqa: E402 (Protocols, read-only)
import fable_daemon74_run as D74  # noqa: E402 (mailbox helpers, read-only)
import fable_loop90_agent as L90  # noqa: E402 (loop90 build, read-only)
import fable_loop96_agent as L96  # noqa: E402 (loop96 build, read-only)
import fable_notebook_contract as C  # noqa: E402 (contract, read-only)
import fable_wire57_e2e as W57  # noqa: E402 (sparse-village sleeper, read-only)

WORD = "maternal_grandmother"
WIDX = 0
CHAIN = ("mother", "mother")
WORD_FILE = "sleep104-word.json"
MARKER = "sleep104-SLEEPING"
REPORT_RELATION = "sleep_report"
SLEEP_ENTITY = "SLEEP104"
BASE_PT = (SCRIPTS.parent / "artifacts" / "fable-reasoner44-20260921"
           / "runs" / "base-seed4102.pt")


# ------------------------------------------------------------------ reasoner
class Sleep104Reasoner:
    """Episode feed + sleep-provenance marks around QualifierAwareReasoner77.

    Duck-types the Reasoner protocol (answer(question, notebook) -> dict).
    """

    WORD = WORD
    CHAIN = CHAIN

    def __init__(self, inner) -> None:
        self.inner = inner
        self.episodes: list[dict] = []
        self.report_fid: str | None = None
        self.install_episodes = 0

    @property
    def installed(self) -> bool:
        return WORD in getattr(self.inner, "words", {})

    def _queue(self, name: str, entity_id: str | None, notebook) -> None:
        start = entity_id
        if start is None:
            found = notebook.resolve(name)
            if found.status != C.OK:
                return
            start = found.detail["entity_id"]
        cur, ok = start, True
        for rel in CHAIN:
            rows = notebook.current(cur, rel)
            if len(rows) < 1 or "entity" not in rows[0]["value"]:
                ok = False
                break
            cur = rows[0]["value"]["entity"]
        if ok:
            self.episodes.append({"start": start, "word": WIDX,
                                  "word_name": WORD, "answer": cur})

    def answer(self, question: dict, notebook) -> dict:
        relations = list(question.get("relations") or [])
        if len(relations) == 1 and relations[0] == WORD:
            self._queue(question.get("name", ""), question.get("entity_id"),
                        notebook)
        rec = self.inner.answer(question, notebook)
        if (len(relations) == 1 and relations[0] == WORD
                and rec.get("status") == C.OK and self.installed
                and rec.get("fields", {}).get("source") == "taught"):
            # The hops are taught FACTs; the routing that chose them is the
            # sleep-installed skill. Mark the record accordingly and head
            # the trail with the sleep-derived install report row.
            rec = dict(rec)
            fields = dict(rec.get("fields", {}))
            fields["source"] = "sleep-derived"
            trail = list(fields.get("trail", []))
            if self.report_fid and self.report_fid not in trail:
                trail = [self.report_fid] + trail
            fields["trail"] = trail
            fields["sleep_word"] = WORD
            rec["fields"] = fields
        return rec


def check_word_logits(logits) -> bool:
    """The skill stages must read mother then mother.

    The hardened [3][9] rows are keep-padded to length 3 and the keep row
    can sit in any position (seed 9 installed mother/mother/keep, seed 1
    keep/mother/mother); keep stages are skipped by the hop loop, so the
    check is on the non-keep stages in row order.
    """
    try:
        if len(logits) != 3 or any(len(r) != 9 for r in logits):
            return False
        arg = [max(range(9), key=lambda i: r[i]) for r in logits]
        skills = [a for a in arg if a != 0]
        return skills == [1, 1]
    except (TypeError, ValueError):
        return False


# ------------------------------------------------------------------- sleeper
class Sleep104Sleeper(W57.SparseVillageSleeper):
    """The wire57 install path + bridge + report row + atomic persistence."""

    def __init__(self, state_dir, reasoner=None, checkpoint=None, seed=1,
                 word_file: str = WORD_FILE) -> None:
        super().__init__(state_dir, reasoner=reasoner,
                         checkpoint=checkpoint or str(BASE_PT), seed=seed)
        self.word_path = Path(state_dir) / word_file
        self.marker_path = Path(state_dir) / MARKER
        self.sleep_seconds = 0.0

    # ------------------------------------------------------- persistence
    def load_persisted(self) -> dict:
        """Boot-time load of the atomic word file. Valid full word or {}. """
        try:
            data = json.loads(self.word_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if (not isinstance(data, dict) or data.get("word") != WORD
                or not check_word_logits(data.get("logits"))):
            return {}
        try:
            self.reasoner.inner.words[WORD] = [
                [float(x) for x in row] for row in data["logits"]]
            self.reasoner.report_fid = data.get("report_fid")
            self.reasoner.install_episodes = int(data.get("episodes", 0))
        except (AttributeError, TypeError, ValueError):
            return {}
        return data

    # ------------------------------------------------------------- sleeping
    def sleep(self, experience: list[dict], notebook) -> dict:
        t0 = time.time()
        try:
            self.marker_path.write_text(
                json.dumps({"pid": os.getpid(), "t": t0}), encoding="utf-8")
        except OSError:
            pass
        try:
            outcome = super().sleep(experience, notebook)
        finally:
            try:
                self.marker_path.unlink(missing_ok=True)
            except OSError:
                pass
        self.sleep_seconds = round(time.time() - t0, 2)
        outcome = dict(outcome)
        outcome["sleep_seconds"] = self.sleep_seconds
        recipe = outcome.get("recipe", {})
        if isinstance(recipe, dict) and recipe.get("installed"):
            bridge = self._commit_install(notebook, recipe)
            outcome["bridge"] = bridge
        self.last_outcome = outcome
        return outcome

    def _commit_install(self, notebook, recipe: dict) -> dict:
        words = recipe.get("words", []) if isinstance(recipe, dict) else []
        rec = next((w for w in words if w.get("word") == WORD
                    and w.get("installed")), None)
        if rec is None:
            return {"bridged": False, "reason": "no installed word rec"}
        # The outcome dict does not carry logits (only the .pt does), so
        # load the hardened numbers from the recipe's own checkpoint file
        # (read-only w.r.t. training: hardened +/-30, gate-audited).
        ckpts = sorted(
            (self.state_dir / "sleep-checkpoints").glob(f"*{WORD}-*.pt"),
            key=lambda p: p.stat().st_mtime)
        if not ckpts:
            return {"bridged": False, "reason": "no checkpoint file"}
        try:
            import torch
            torch.set_num_threads(1)
            sd = torch.load(ckpts[-1], map_location="cpu",
                            weights_only=True)
            logits = [[float(x) for x in row]
                      for row in sd["words.0"].tolist()]
        except (OSError, ValueError, KeyError) as exc:
            return {"bridged": False,
                    "reason": f"checkpoint unreadable: {exc}"}
        if not check_word_logits(logits):
            return {"bridged": False,
                    "reason": "logits fail the mother/mother/keep audit"}
        # 1. bridge into the live reasoner
        self.reasoner.inner.words[WORD] = logits
        self.reasoner.install_episodes = int(rec.get("episodes", 0))
        # 2. one sleep-derived report row (exp-52 convention)
        try:
            if REPORT_RELATION not in notebook.functional:
                notebook.declare_relation("sleep104-rel-0", REPORT_RELATION,
                                          False)
        except (AttributeError, TypeError):
            pass
        found = notebook.resolve(SLEEP_ENTITY)
        if found.status == C.OK:
            sleep_eid = found.detail["entity_id"]
        else:
            made = notebook.new_entity("sleep104-ent-0", SLEEP_ENTITY)
            sleep_eid = made.detail["entity_id"]
        summary = {"word": WORD, "chain": list(CHAIN),
                   "episodes": rec.get("episodes"),
                   "oof_best": rec.get("oof_best"),
                   "refit_agreement": rec.get("refit_agreement"),
                   "routing": rec.get("reason"),
                   "seed": self.seed}
        rep = notebook.assert_fact(
            f"sleep104-report-{self.seed}", "sleep", "sleep-derived",
            sleep_eid, REPORT_RELATION,
            {"literal": json.dumps(summary, sort_keys=True)},
            raw="sleep104 install report row")
        if rep.status not in (C.SAVED, C.DUPLICATE_OK):
            return {"bridged": False,
                    "reason": f"report row not stored: {rep.status}"}
        self.reasoner.report_fid = rep.detail.get("fact_id")
        # 3. atomic persistence (the ONLY serving state a restart trusts)
        payload = {"word": WORD, "logits": logits,
                   "report_fid": self.reasoner.report_fid,
                   "episodes": self.reasoner.install_episodes,
                   "seed": self.seed}
        tmp = self.word_path.parent / f"{self.word_path.name}.tmp{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, self.word_path)
        return {"bridged": True, "report_fid": self.reasoner.report_fid,
                "episodes": self.reasoner.install_episodes}


# ------------------------------------------------------------------- retrofit
def retrofit_sleep104(loop, root, seed: int = 1,
                      checkpoint: str | None = None) -> Sleep104Reasoner:
    """Swap the loop96 reasoner/sleeper for the sleep104 pair (additive)."""
    root = Path(root)
    wrapper = Sleep104Reasoner(loop.reasoner)
    sleeper = Sleep104Sleeper(root, reasoner=wrapper,
                              checkpoint=checkpoint or str(BASE_PT),
                              seed=seed)
    loop.reasoner = wrapper
    loop.sleeper = sleeper
    try:
        loop.parts90["reasoner"] = wrapper
        loop.parts90["sleeper"] = sleeper
    except (AttributeError, TypeError):
        pass
    # Crash-recovery: a fully persisted word comes back installed; anything
    # else (absent, torn, half-written tmp) comes back cleanly absent.
    for stale in root.glob(f"{WORD_FILE}.tmp*"):
        try:
            stale.unlink()
        except OSError:
            pass
    loaded = sleeper.load_persisted()
    loop.notes.append(
        f"sleep104: word {'restored' if loaded else 'absent'} on boot")
    return wrapper


DEFAULT_CONFIG104: dict = copy.deepcopy(L96.DEFAULT_CONFIG96)
DEFAULT_CONFIG104["sleeper"]["stand_in"] = (
    "Sleep104Sleeper = wire57 SparseVillageSleeper (exp-46 recipe, unchanged "
    "gate) + bridge into the live reasoner + sleep-derived report row + "
    "atomic word file; episode feed = Sleep104Reasoner (mother+mother walk)")
DEFAULT_CONFIG104["daemon"]["module"] = "Sleep104Daemon (this file)"


def build_agent104(cfg: dict | None = None, seed: int = 1,
                   checkpoint: str | None = None):
    cfg = dict(DEFAULT_CONFIG104, **(cfg or {}))
    loop = L96.build_agent96(cfg)
    wrapper = retrofit_sleep104(
        loop, cfg.get("state_dir", "."),
        seed=int(cfg.get("sleep104_seed", seed)),
        checkpoint=cfg.get("sleep104_checkpoint", checkpoint))
    loop.parts90["sleep104"] = {"word": WORD, "chain": list(CHAIN)}
    return loop


# -------------------------------------------------------------------- daemon
class Sleep104Daemon(L96.Loop96Daemon):
    """Loop96Daemon with the sleep104 reasoner/sleeper + sleep logging."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 seed: int = 1) -> None:
        cfg = dict(cfg or {})
        seed = int(cfg.get("sleep104_seed", seed))
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        retrofit_sleep104(self.loop, self.root, seed=seed,
                          checkpoint=cfg.get("sleep104_checkpoint"))

    def process_file(self, path: Path) -> dict:
        import os as _os
        nb = self.loop.nb
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return {"event": "turn-skipped", "file": path.name}
        before_facts = set(nb.facts)
        before_entities = set(nb.entities)
        sleeps_before = int(self.loop.counters.get("sleeps", 0))
        t0 = time.time()
        said = self.loop.turn(text)  # SLEEP fires inside here, on its own
        wall = round(time.time() - t0, 2)
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
                  "notebook_events": len(nb.events),
                  "turn_seconds": wall}
        D74._append_log(self.log_path, record)
        if int(self.loop.counters.get("sleeps", 0)) > sleeps_before:
            outcome = dict(
                getattr(self.loop.sleeper, "last_outcome", {}))
            D74._append_log(self.log_path, {
                "t": D74._now_iso(), "event": "sleep", "file": path.name,
                "turn_seconds": wall,
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


def run_daemon104(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Sleep104Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 104 live sleep in daemon")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG104)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG104)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    cfg.setdefault("sleep104_seed", args.seed)

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon104(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent104(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
