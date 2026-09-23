#!/usr/bin/env python3
"""Experiment 115 -- SCALE the live sleep that PASSED in exp 104 until it breaks.

Exp 104 installed ONE relation ("maternal_grandmother" = mother+mother) in ONE
sleep inside the running loop96 daemon. Exp 115 runs a scale ladder (each rung
in order, stop at the first rung that fails its marks):

  L1  three new relations in ONE sleep (all three R44 word slots:
      maternal_grandmother = mother+mother,
      boss_of_spouse = spouse+boss,
      doctor_of_mothers_friend = mother+best_friend+doctor)
  L2  two sleep cycles (A in sleep 1, B+C in sleep 2; A must still answer)
  L3  a 3-hop composition relation alone (doctor_of_mothers_friend)
  L4  400 turns, a sleep every 75 turns (5 sleeps), 5 relations total
      (the R44 architecture has exactly 3 word slots, so relations 4-5 --
      e.g. boss_of_father, teacher_of_spouse -- have no slot: structural cap)
  L5  L4 plus a kill -9 during the 3rd sleep (dormant unless L4 passes)

Additive only (nothing outside this file is edited; everything else is
imported read-only and wrapped):

  Sleep115Ears      wraps the loop's ears chain. FakeEars marks spouse /
                    best_friend / doctor teaches as literals (they are absent
                    from PERSON_RELATIONS), which would starve the episode
                    feed of entity-valued hops. This wrapper forces
                    is_person=True for teach/correct actions whose relation is
                    one of the install chains' hops (mother, spouse, boss,
                    best_friend, doctor). Everything else passes through
                    untouched (attribute delegation for last_stage/score).
  Sleep115Reasoner  wraps QualifierAwareReasoner77 with a THREE-word episode
                    feed: on a bare learned-word question (relations == [one
                    of the three WORDS]) it walks that word's chain in the
                    live notebook and queues one episode (start, word idx,
                    answer) -- the wire57 _queue_word_episode rule, per word.
                    Post-install the inner hop loop answers OK through the
                    installed logits; the wrapper marks the record
                    sleep-derived and heads the trail with that word's install
                    report row (hop rows stay the taught FACTs they are).
  Sleep115Sleeper   wire57's SparseVillageSleeper (exp-46 recipe, unchanged
                    gate) + per installed word: audit the hardened [3][9]
                    logits against that word's true chain (non-keep stages in
                    row order must equal the chain's skill indices), bridge
                    into the live reasoner's words table, append one
                    sleep-derived report row (exp-52 convention), and merge
                    into the atomic multi-word file (tmp + fsync +
                    os.replace). Serving state is that JSON file only.
                    A sleep115-SLEEPING marker brackets the recipe (kill arm).
  Sleep115Daemon    Loop96Daemon + retrofit (ears/reasoner/sleeper swap,
                    stale-tmp cleanup, boot-load of persisted words) +
                    per-turn sleep logging (one log row per SLEEP tick, so
                    multi-sleep sessions are fully recorded).
  build_agent115    build_agent96, then the retrofit.

Crash discipline: serving state = state_dir/sleep115-words.json (atomic
replace; torn .tmp files ignored on boot). Recipe .pt files are never
trusted for serving (only the JSON is loaded). A kill between report-row
write and word-file commit degrades to honest abstain-or-serve, never a
half skill (same argument as exp 104).

Run (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_sleep115_agent.py --daemon --dir DIR --config CFG
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

# The three installable relations are FIXED by the sealed R44 architecture
# (N_WORDS=3 word slots; chains below must equal R44.WORD_CHAINS -- asserted
# at import when torch is available, and re-checked in the drive).
WORDS = ("maternal_grandmother", "boss_of_spouse", "doctor_of_mothers_friend")
CHAINS = (("mother", "mother"),
          ("spouse", "boss"),
          ("mother", "best_friend", "doctor"))
# R44 skill indices are 1-based over RELATIONS (0 = keep).
RELATIONS = ("mother", "father", "spouse", "boss", "best_friend", "neighbour",
             "doctor", "teacher")
EXPECTED_SKILLS = tuple(tuple(RELATIONS.index(r) + 1 for r in c) for c in CHAINS)
# Hops that must be entity-valued for episodes to queue (FakeEars leaves
# spouse/best_friend/doctor as literals without the Sleep115Ears wrap).
PERSON_HOPS = {"mother", "spouse", "boss", "best_friend", "doctor"}

WORD_FILE = "sleep115-words.json"
MARKER = "sleep115-SLEEPING"
REPORT_RELATION = "sleep_report"
SLEEP_ENTITY = "SLEEP115"
BASE_PT = (SCRIPTS.parent / "artifacts" / "fable-reasoner44-20260921"
           / "runs" / "base-seed4102.pt")


# ---------------------------------------------------------------------- ears
class Sleep115Ears:
    """Force entity-valued teaches for install-chain hops; pass the rest."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.forced = 0

    def hear(self, turn: str) -> list[dict]:
        actions = self.inner.hear(turn)
        for action in actions:
            if (isinstance(action, dict)
                    and action.get("act") in ("teach", "correct")
                    and action.get("relation") in PERSON_HOPS
                    and not action.get("is_person")):
                action["is_person"] = True
                self.forced += 1
        return actions

    def bind(self, nb) -> None:
        inner = self.__dict__.get("inner")
        if inner is not None and hasattr(inner, "bind"):
            inner.bind(nb)

    def __getattr__(self, name: str):
        if name.startswith("__"):
            raise AttributeError(name)
        return getattr(self.__dict__["inner"], name)


# ------------------------------------------------------------------ reasoner
class Sleep115Reasoner:
    """Three-word episode feed + sleep-provenance marks around reasoner77."""

    WORDS = WORDS
    CHAINS = CHAINS

    def __init__(self, inner) -> None:
        self.inner = inner
        self.episodes: list[dict] = []
        self.report_fids: dict[str, str] = {}
        self.install_episodes: dict[str, int] = {}

    def installed(self, word: str) -> bool:
        return word in getattr(self.inner, "words", {})

    def _queue(self, word: str, w: int, name: str,
               entity_id: str | None, notebook) -> None:
        start = entity_id
        if start is None:
            found = notebook.resolve(name)
            if found.status != C.OK:
                return
            start = found.detail["entity_id"]
        cur, ok = start, True
        for rel in CHAINS[w]:
            rows = notebook.current(cur, rel)
            if len(rows) < 1 or "entity" not in rows[0]["value"]:
                ok = False
                break
            cur = rows[0]["value"]["entity"]
        if ok:
            self.episodes.append({"start": start, "word": w,
                                  "word_name": word, "answer": cur})

    def answer(self, question: dict, notebook) -> dict:
        relations = list(question.get("relations") or [])
        w = None
        if len(relations) == 1 and relations[0] in WORDS:
            w = WORDS.index(relations[0])
            self._queue(relations[0], w, question.get("name", ""),
                        question.get("entity_id"), notebook)
        rec = self.inner.answer(question, notebook)
        if (w is not None and rec.get("status") == C.OK
                and self.installed(WORDS[w])
                and rec.get("fields", {}).get("source") == "taught"):
            rec = dict(rec)
            fields = dict(rec.get("fields", {}))
            fields["source"] = "sleep-derived"
            trail = list(fields.get("trail", []))
            fid = self.report_fids.get(WORDS[w])
            if fid and fid not in trail:
                trail = [fid] + trail
            fields["trail"] = trail
            fields["sleep_word"] = WORDS[w]
            rec["fields"] = fields
        return rec


def check_word_logits(logits, w: int) -> bool:
    """Hardened [3][9] rows: non-keep stages (row order) == chain skills."""
    try:
        if len(logits) != 3 or any(len(r) != 9 for r in logits):
            return False
        arg = [max(range(9), key=lambda i: r[i]) for r in logits]
        skills = [a for a in arg if a != 0]
        return skills == list(EXPECTED_SKILLS[w])
    except (TypeError, ValueError):
        return False


# ------------------------------------------------------------------- sleeper
class Sleep115Sleeper(W57.SparseVillageSleeper):
    """The wire57 install path + per-word bridge/report/persist (additive)."""

    def __init__(self, state_dir, reasoner=None, checkpoint=None, seed=1,
                 word_file: str = WORD_FILE) -> None:
        super().__init__(state_dir, reasoner=reasoner,
                         checkpoint=checkpoint or str(BASE_PT), seed=seed)
        self.word_path = Path(state_dir) / word_file
        self.marker_path = Path(state_dir) / MARKER
        self.sleep_seconds = 0.0

    # ------------------------------------------------------- persistence
    def load_persisted(self) -> dict:
        """Boot-time load of the atomic multi-word file. Valid words or {}."""
        try:
            data = json.loads(self.word_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(data, dict) or not isinstance(
                data.get("words"), dict):
            return {}
        good: dict = {}
        for wname, rec in data["words"].items():
            if wname not in WORDS or not isinstance(rec, dict):
                continue
            if not check_word_logits(rec.get("logits"),
                                     WORDS.index(wname)):
                continue
            try:
                self.reasoner.inner.words[wname] = [
                    [float(x) for x in row] for row in rec["logits"]]
                self.reasoner.report_fids[wname] = rec.get("report_fid")
                self.reasoner.install_episodes[wname] = int(
                    rec.get("episodes", 0))
            except (AttributeError, TypeError, ValueError):
                continue
            good[wname] = rec
        return {"words": good, "seed": data.get("seed")}

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
            outcome = dict(outcome)
            recipe = outcome.get("recipe", {})
            if isinstance(recipe, dict) and recipe.get("installed"):
                outcome["bridge"] = self._commit_installs(notebook, recipe)
        finally:
            try:
                self.marker_path.unlink(missing_ok=True)
            except OSError:
                pass
        # The latency mark covers recipe + bridge: serving the install is
        # part of the sleep.
        self.sleep_seconds = round(time.time() - t0, 2)
        outcome["sleep_seconds"] = self.sleep_seconds
        self.last_outcome = outcome
        return outcome

    def _commit_installs(self, notebook, recipe: dict) -> dict:
        words = recipe.get("words", []) if isinstance(recipe, dict) else []
        try:
            prior = json.loads(self.word_path.read_text(encoding="utf-8"))
            merged = dict(prior.get("words", {})) if isinstance(
                prior, dict) else {}
        except (OSError, ValueError):
            merged = {}
        per_word: dict = {}
        for rec in words:
            if not rec.get("installed"):
                continue
            wname = rec.get("word")
            if wname not in WORDS:
                continue
            w = WORDS.index(wname)
            bridged = self._commit_one(notebook, rec, w, wname, merged)
            per_word[wname] = bridged
        if per_word:
            payload = {"words": merged, "seed": self.seed}
            tmp = (self.word_path.parent
                   / f"{self.word_path.name}.tmp{os.getpid()}")
            with open(tmp, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.word_path)
        return per_word

    def _commit_one(self, notebook, rec: dict, w: int, wname: str,
                    merged: dict) -> dict:
        ckpts = sorted(
            (self.state_dir / "sleep-checkpoints").glob(
                f"word-seed*-wire57-live-{wname}-ep*.pt"),
            key=lambda p: p.stat().st_mtime)
        if not ckpts:
            alt = sorted(
                (self.state_dir / "sleep-checkpoints").glob(f"*{wname}-*.pt"),
                key=lambda p: p.stat().st_mtime)
            ckpts = alt
        if not ckpts:
            return {"bridged": False, "reason": "no checkpoint file"}
        try:
            import torch
            torch.set_num_threads(1)
            sd = torch.load(ckpts[-1], map_location="cpu",
                            weights_only=True)
            logits = [[float(x) for x in row]
                      for row in sd[f"words.{w}"].tolist()]
        except (OSError, ValueError, KeyError) as exc:
            return {"bridged": False,
                    "reason": f"checkpoint unreadable: {exc}"}
        if not check_word_logits(logits, w):
            return {"bridged": False,
                    "reason": "logits fail the chain audit"}
        # 1. bridge into the live reasoner (additive: other words untouched)
        self.reasoner.inner.words[wname] = logits
        self.reasoner.install_episodes[wname] = int(rec.get("episodes", 0))
        # 2. one sleep-derived report row per installed word (exp-52 style)
        try:
            if REPORT_RELATION not in notebook.functional:
                notebook.declare_relation("sleep115-rel-0", REPORT_RELATION,
                                          False)
        except (AttributeError, TypeError):
            pass
        found = notebook.resolve(SLEEP_ENTITY)
        if found.status == C.OK:
            sleep_eid = found.detail["entity_id"]
        else:
            made = notebook.new_entity("sleep115-ent-0", SLEEP_ENTITY)
            sleep_eid = made.detail["entity_id"]
        summary = {"word": wname, "chain": list(CHAINS[w]),
                   "episodes": rec.get("episodes"),
                   "oof_best": rec.get("oof_best"),
                   "refit_agreement": rec.get("refit_agreement"),
                   "routing": rec.get("reason"),
                   "seed": self.seed}
        rep = notebook.assert_fact(
            f"sleep115-report-{self.seed}-{wname}", "sleep", "sleep-derived",
            sleep_eid, REPORT_RELATION,
            {"literal": json.dumps(summary, sort_keys=True)},
            raw="sleep115 install report row")
        if rep.status not in (C.SAVED, C.DUPLICATE_OK):
            return {"bridged": False,
                    "reason": f"report row not stored: {rep.status}"}
        self.reasoner.report_fids[wname] = rep.detail.get("fact_id")
        # 3. merge into the persisted multi-word payload (commit is atomic
        #    in _commit_installs after all words are bridged).
        merged[wname] = {"logits": logits,
                         "report_fid": self.reasoner.report_fids[wname],
                         "episodes": self.reasoner.install_episodes[wname],
                         "seed": self.seed}
        return {"bridged": True,
                "report_fid": self.reasoner.report_fids[wname],
                "episodes": self.reasoner.install_episodes[wname]}


# ------------------------------------------------------------------- retrofit
def retrofit_sleep115(loop, root, seed: int = 1,
                       checkpoint: str | None = None) -> Sleep115Reasoner:
    """Swap the loop96 ears/reasoner/sleeper for the sleep115 trio."""
    root = Path(root)
    ears = Sleep115Ears(loop.ears)
    wrapper = Sleep115Reasoner(loop.reasoner)
    sleeper = Sleep115Sleeper(root, reasoner=wrapper,
                              checkpoint=checkpoint or str(BASE_PT),
                              seed=seed)
    loop.ears = ears
    loop.reasoner = wrapper
    loop.sleeper = sleeper
    try:
        loop.parts90["ears"] = ears
        loop.parts90["reasoner"] = wrapper
        loop.parts90["sleeper"] = sleeper
    except (AttributeError, TypeError):
        pass
    for stale in root.glob(f"{WORD_FILE}.tmp*"):
        try:
            stale.unlink()
        except OSError:
            pass
    loaded = sleeper.load_persisted()
    loop.notes.append(
        "sleep115: words "
        f"{sorted(loaded.get('words', {})) if loaded else []} on boot")
    return wrapper


DEFAULT_CONFIG115: dict = copy.deepcopy(L96.DEFAULT_CONFIG96)
DEFAULT_CONFIG115["sleeper"]["stand_in"] = (
    "Sleep115Sleeper = wire57 SparseVillageSleeper (exp-46 recipe, unchanged "
    "gate) + per-word bridge into the live reasoner + per-word "
    "sleep-derived report row + atomic multi-word file; episode feed = "
    "Sleep115Reasoner (three chains); ears = Sleep115Ears (entity-valued "
    "teaches for chain hops)")
DEFAULT_CONFIG115["daemon"]["module"] = "Sleep115Daemon (this file)"


def build_agent115(cfg: dict | None = None, seed: int = 1,
                   checkpoint: str | None = None):
    cfg = dict(DEFAULT_CONFIG115, **(cfg or {}))
    loop = L96.build_agent96(cfg)
    retrofit_sleep115(
        loop, cfg.get("state_dir", "."),
        seed=int(cfg.get("sleep115_seed", seed)),
        checkpoint=cfg.get("sleep115_checkpoint", checkpoint))
    loop.parts90["sleep115"] = {"words": list(WORDS),
                                "chains": [list(c) for c in CHAINS]}
    return loop


# -------------------------------------------------------------------- daemon
class Sleep115Daemon(L96.Loop96Daemon):
    """Loop96Daemon with the sleep115 trio + per-sleep logging."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 seed: int = 1) -> None:
        cfg = dict(cfg or {})
        seed = int(cfg.get("sleep115_seed", seed))
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        retrofit_sleep115(self.loop, self.root, seed=seed,
                          checkpoint=cfg.get("sleep115_checkpoint"))

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
            queued = len(getattr(self.loop.reasoner, "episodes", []))
            installed_eps = sum(
                w.get("episodes", 0) for w in
                outcome.get("recipe", {}).get("words", []))
            D74._append_log(self.log_path, {
                "t": D74._now_iso(), "event": "sleep", "file": path.name,
                "turn_seconds": wall,
                "sleep_seconds": getattr(self.loop.sleeper,
                                         "sleep_seconds", 0.0),
                "accepted": outcome.get("accepted"),
                "recipe": outcome.get("recipe", {}),
                "bridge": outcome.get("bridge", {}),
                "episodes_at_sleep": queued + installed_eps})
        return record


def run_daemon115(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Sleep115Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 115 sleep scale ladder")
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
        out = copy.deepcopy(DEFAULT_CONFIG115)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG115)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    cfg.setdefault("sleep115_seed", args.seed)

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon115(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent115(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
