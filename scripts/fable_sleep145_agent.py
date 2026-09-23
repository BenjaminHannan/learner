#!/usr/bin/env python3
"""Experiment 145 -- MERGE of exp 130 (grow-one-word-slot sleep) and exp 131
(taught-beats-sleep answer rule). No new behaviour: the union of the two.

Feature A = exp 131 (scripts/fable_sleep131_agent.py): when a question is
about an installed sleep word, an ACTIVE TAUGHT row answers first (source
taught), otherwise the sleep rule as in 104.

Feature B = exp 130 (scripts/fable_sleep130_agent.py, doc
design/v3/30-modes/130-sleep-grow-slot-muse.md): when all word slots are
taken, sleep grows one frozen-hashed slot (115 lineage).

Class map (parents imported read-only, never edited):
  Sleep131Reasoner(A104.Sleep104Reasoner) -- 131 answer rule, 1 word
      (scripts/fable_sleep131_agent.py, lines 62-106).
  Sleep131Daemon(A104.Sleep104Daemon) -- inherits process_file verbatim.
  Sleep130Reasoner(S115.Sleep115Reasoner) -- extended feed _queue130 +
      sleep-derived relabel over WORDS130
      (scripts/fable_sleep130_agent.py, lines 147-193).
  Sleep130Sleeper(S115.Sleep115Sleeper) -- grow-one-zero-slot; free slot
      delegates to the untouched 115/wire57 _run_exp46 path; else
      _run_exp46_grow with pre/post sha256 frozen hashes.

THE MERGE (this file, additive only):
  Sleep145Reasoner(S130.Sleep130Reasoner).answer: 131's taught-first rule
      generalised from 1 word to every word in WORDS130. On a bare
      installed-word question with no qualifiers, resolve the entity and
      read notebook.current(eid, word) filtered to source == "taught" (the
      same calls 131 uses). On a hit, run the 130 episode feed exactly once
      (_queue130, so sleep training sees the identical feed) and return OK
      from that row with source taught and its own trail. Every other path
      calls super().answer (identical queueing, derivation, sleep-derived
      relabel).
  Sleep145Sleeper(S130.Sleep130Sleeper): identical grow logic; only the
      serving filenames change (sleep145-words.json / sleep145-SLEEPING /
      SLEEP145) so 145 state never touches sealed 130/115 files.
  Sleep145Daemon(S130.Sleep130Daemon): inherits process_file verbatim;
      __init__ runs the same retrofit with the 145 reasoner.

Run (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_sleep145_agent.py --daemon --dir DIR --config CFG
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

import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_loop96_agent as L96  # noqa: E402 (read-only)
import fable_sleep130_agent as S130  # noqa: E402 (read-only, never edited)

WORDS145 = S130.WORDS130
CHAINS145 = S130.CHAINS130
WORD_FILE145 = "sleep145-words.json"
MARKER145 = "sleep145-SLEEPING"
SLEEP_ENTITY145 = "SLEEP145"


# ------------------------------------------------------------------ reasoner
class Sleep145Reasoner(S130.Sleep130Reasoner):
    """Sleep130Reasoner + 131's rule generalised to every word in WORDS130.

    Duck-types the Reasoner protocol (answer(question, notebook) -> dict).
    """

    def answer(self, question: dict, notebook) -> dict:
        relations = list(question.get("relations") or [])
        if (len(relations) == 1 and relations[0] in WORDS145
                and not question.get("qualifiers")):
            word = relations[0]
            w = WORDS145.index(word)
            if self.installed(word):
                name = question.get("name", "")
                eid = question.get("entity_id")
                if eid is None:
                    found = notebook.resolve(name)
                    if found.status == C.OK:
                        eid = found.detail["entity_id"]
                if eid is not None and eid in notebook.entities:
                    taught = [r for r in notebook.current(eid, word)
                              if r.get("source") == "taught"]
                    if taught:
                        # The 130 episode feed, exactly once (130 queues on
                        # every bare-word question; the fallthrough below
                        # queues inside super().answer, so queue here only
                        # on the taught-hit early return).
                        self._queue130(word, w, name,
                                       question.get("entity_id"), notebook)
                        if len(taught) == 1:
                            val = taught[0]["value"]
                            shown = (notebook.entities[val["entity"]]
                                     if "entity" in val
                                     else str(val.get("literal", "")))
                            fields = {"answer": shown,
                                      "trail": [taught[0]["fact_id"]],
                                      "source": "taught"}
                        else:
                            shows = [(notebook.entities[r["value"]["entity"]]
                                      if "entity" in r["value"]
                                      else str(r["value"].get("literal", "")))
                                     for r in taught]
                            fields = {"answer": ", ".join(shows),
                                      "trail": [r["fact_id"] for r in taught],
                                      "source": "taught", "multi": True}
                        return {"kind": "answer", "status": C.OK, "name": name,
                                "relations": relations, "fields": fields}
        return super().answer(question, notebook)


# ------------------------------------------------------------------- sleeper
class Sleep145Sleeper(S130.Sleep130Sleeper):
    """Sleep130Sleeper with 145 serving filenames (grow logic verbatim)."""

    def __init__(self, state_dir, reasoner=None, checkpoint=None, seed=1,
                 word_file: str = WORD_FILE145) -> None:
        super().__init__(state_dir, reasoner=reasoner,
                         checkpoint=checkpoint or str(S130.BASE_PT130),
                         seed=seed, word_file=word_file)
        self.marker_path = Path(state_dir) / MARKER145

    def _commit_one(self, notebook, rec: dict, w: int, wname: str,
                    merged: dict) -> dict:
        # Grow/bridge logic is 130 verbatim (shared sleep_report relation by
        # contract convention); only the serving word file differs.
        return super()._commit_one(notebook, rec, w, wname, merged)


# ------------------------------------------------------------------- retrofit
def retrofit_sleep145(loop, root, seed: int = 1,
                       checkpoint: str | None = None) -> Sleep145Reasoner:
    """Same steps as S130.retrofit_sleep130, with the 145 pair."""
    root = Path(root)
    ears = S130.Sleep130Ears(loop.ears)
    wrapper = Sleep145Reasoner(loop.reasoner)
    sleeper = Sleep145Sleeper(root, reasoner=wrapper,
                              checkpoint=checkpoint or str(S130.BASE_PT130),
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
    for stale in root.glob(f"{WORD_FILE145}.tmp*"):
        try:
            stale.unlink()
        except OSError:
            pass
    loaded = sleeper.load_persisted()
    sleeper.grown = None  # rebuilt lazily from checkpoint + live words
    loop.notes.append(
        "sleep145: words "
        f"{sorted(loaded.get('words', {})) if loaded else []} on boot "
        "(grow-slot + taught-beats-sleep reasoner)")
    return wrapper


DEFAULT_CONFIG145: dict = copy.deepcopy(S130.DEFAULT_CONFIG130)
DEFAULT_CONFIG145["sleeper"]["stand_in"] = (
    "Sleep145Sleeper = Sleep130Sleeper verbatim (grow-one-zero-slot, frozen "
    "hashes, 115/wire57 delegation); episode feed + reasoner = "
    "Sleep145Reasoner (131 taught-first generalised to all WORDS130)")
DEFAULT_CONFIG145["daemon"]["module"] = "Sleep145Daemon (this file)"


def build_agent145(cfg: dict | None = None, seed: int = 1,
                   checkpoint: str | None = None):
    cfg = dict(DEFAULT_CONFIG145, **(cfg or {}))
    loop = L96.build_agent96(cfg)
    retrofit_sleep145(
        loop, cfg.get("state_dir", "."),
        seed=int(cfg.get("sleep145_seed", cfg.get("sleep130_seed", seed))),
        checkpoint=cfg.get("sleep145_checkpoint",
                           cfg.get("sleep130_checkpoint", checkpoint)))
    loop.parts90["sleep145"] = {"words": list(WORDS145),
                                "chains": [list(c) for c in CHAINS145]}
    return loop


# -------------------------------------------------------------------- daemon
class Sleep145Daemon(S130.Sleep130Daemon):
    """Sleep130Daemon with the 145 pair (process_file inherited verbatim)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 seed: int = 1) -> None:
        cfg = dict(cfg or {})
        seed = int(cfg.get("sleep145_seed",
                           cfg.get("sleep130_seed",
                                   cfg.get("sleep115_seed", seed))))
        L96.Loop96Daemon.__init__(self, root, cfg=cfg,
                                  idle_seconds=idle_seconds,
                                  sleep_threshold=sleep_threshold)
        retrofit_sleep145(self.loop, self.root, seed=seed,
                          checkpoint=cfg.get(
                              "sleep145_checkpoint",
                              cfg.get("sleep130_checkpoint",
                                      cfg.get("sleep115_checkpoint"))))


def run_daemon145(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Sleep145Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 145 merged sleep daemon")
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
        out = copy.deepcopy(DEFAULT_CONFIG145)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                            encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG145)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    cfg.setdefault("sleep145_seed", args.seed)

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon145(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent145(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
