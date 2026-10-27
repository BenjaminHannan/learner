#!/usr/bin/env python3
"""Experiment 131 -- TAUGHT-BEATS-SLEEP: registered single-change fix for the
exp-116 E-family critical finding (artifacts/fable-sleep116-20260922/
RESULTS.md, cases E2-E4).

Cause: scripts/fable_sleep104_agent.py Sleep104Reasoner.answer delegates
straight to the inner reasoner's installed-word derivation; once the
mother+mother word is installed, the word shadows any directly taught
(maternal_grandmother) row, so the daemon answers the derivation (H01)
while the taught row (Z01) stays active. Design rule: a taught fact
always beats an inference.

THE ONE CHANGE (additive only -- nothing sealed is edited; everything
below subclasses or wraps scripts/fable_sleep104_agent.py, imported
read-only as A104):

  Sleep131Reasoner(A104.Sleep104Reasoner).answer: when a question asks
      the bare sleep-installed word for an entity AND the notebook has an
      ACTIVE TAUGHT row for (entity, that word) -- checked with
      notebook.resolve / notebook.current exactly as the existing code
      does -- answer from that row with source "taught" and its own
      trail (the row's fact_id). Otherwise behave exactly as 104
      (super().answer, which queues the identical episode feed and keeps
      the sleep-derived relabel). In the taught-hit branch the 104
      episode queue call runs once first, so the sleep training feed is
      bit-identical to 104 in every path.

  Sleep131Daemon(A104.Sleep104Daemon): identical process_file/logging/
      sleeper/recipe; __init__ retrofits the loop with Sleep131Reasoner
      instead of Sleep104Reasoner (via retrofit_sleep131, otherwise the
      same steps as A104.retrofit_sleep104). Serving state filenames
      (sleep104-word.json, sleep104-SLEEPING) are unchanged on purpose,
      so persistence, reboot-restore, and the 104/116 checkers work
      byte-identically.

Run (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_sleep131_agent.py --daemon --dir DIR --config CFG
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
import fable_sleep104_agent as A104  # noqa: E402 (read-only, never edited)

WORD = A104.WORD


# ------------------------------------------------------------------ reasoner
class Sleep131Reasoner(A104.Sleep104Reasoner):
    """Sleep104Reasoner + one rule: an active taught row for the asked
    (entity, word) wins over the installed derivation.

    Duck-types the Reasoner protocol (answer(question, notebook) -> dict).
    """

    def answer(self, question: dict, notebook) -> dict:
        relations = list(question.get("relations") or [])
        if (len(relations) == 1 and relations[0] == WORD
                and self.installed and not question.get("qualifiers")):
            name = question.get("name", "")
            eid = question.get("entity_id")
            if eid is None:
                found = notebook.resolve(name)
                if found.status == C.OK:
                    eid = found.detail["entity_id"]
            if eid is not None and eid in notebook.entities:
                taught = [r for r in notebook.current(eid, WORD)
                          if r.get("source") == "taught"]
                if taught:
                    # The 104 episode feed, exactly once (104 queues on
                    # every bare-word question; the fallthrough below
                    # queues inside super().answer, so queue here only
                    # on the taught-hit early return).
                    self._queue(name, question.get("entity_id"), notebook)
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


# ------------------------------------------------------------------ retrofit
def retrofit_sleep131(loop, root, seed: int = 1,
                       checkpoint: str | None = None) -> Sleep131Reasoner:
    """Same steps as A104.retrofit_sleep104, with Sleep131Reasoner."""
    root = Path(root)
    wrapper = Sleep131Reasoner(loop.reasoner)
    sleeper = A104.Sleep104Sleeper(
        root, reasoner=wrapper,
        checkpoint=checkpoint or str(A104.BASE_PT), seed=seed)
    loop.reasoner = wrapper
    loop.sleeper = sleeper
    try:
        loop.parts90["reasoner"] = wrapper
        loop.parts90["sleeper"] = sleeper
    except (AttributeError, TypeError):
        pass
    for stale in root.glob(f"{A104.WORD_FILE}.tmp*"):
        try:
            stale.unlink()
        except OSError:
            pass
    loaded = sleeper.load_persisted()
    loop.notes.append(
        f"sleep131: word {'restored' if loaded else 'absent'} on boot "
        "(taught-beats-sleep reasoner)")
    return wrapper


DEFAULT_CONFIG131: dict = copy.deepcopy(A104.DEFAULT_CONFIG104)
DEFAULT_CONFIG131["sleeper"]["stand_in"] = (
    "Sleep104Sleeper unchanged (exp-46 recipe + bridge + report row + "
    "atomic word file); episode feed + reasoner = Sleep131Reasoner "
    "(taught row for the asked word wins, else exactly 104)")
DEFAULT_CONFIG131["daemon"]["module"] = "Sleep131Daemon (this file)"


def build_agent131(cfg: dict | None = None, seed: int = 1,
                    checkpoint: str | None = None):
    cfg = dict(DEFAULT_CONFIG131, **(cfg or {}))
    loop = L96.build_agent96(cfg)
    retrofit_sleep131(
        loop, cfg.get("state_dir", "."),
        seed=int(cfg.get("sleep131_seed", cfg.get("sleep104_seed", seed))),
        checkpoint=cfg.get("sleep131_checkpoint",
                           cfg.get("sleep104_checkpoint", checkpoint)))
    loop.parts90["sleep131"] = {"word": WORD, "fix": "taught-beats-sleep"}
    return loop


# -------------------------------------------------------------------- daemon
class Sleep131Daemon(A104.Sleep104Daemon):
    """A104.Sleep104Daemon with the Sleep131Reasoner retrofit.

    process_file (turn + per-turn sleep logging) is inherited verbatim, so
    mailbox behaviour, log schema, word/marker filenames, and the sleep
    recipe are identical to 104; only the answer rule changes.
    """

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 seed: int = 1) -> None:
        cfg = dict(cfg or {})
        seed = int(cfg.get("sleep131_seed", cfg.get("sleep104_seed", seed)))
        L96.Loop96Daemon.__init__(self, root, cfg=cfg,
                                  idle_seconds=idle_seconds,
                                  sleep_threshold=sleep_threshold)
        retrofit_sleep131(self.loop, self.root, seed=seed,
                          checkpoint=cfg.get(
                              "sleep131_checkpoint",
                              cfg.get("sleep104_checkpoint")))


def run_daemon131(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Sleep131Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Exp 131 taught-beats-sleep daemon")
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
        out = copy.deepcopy(DEFAULT_CONFIG131)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                            encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG131)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    cfg.setdefault("sleep131_seed", args.seed)

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon131(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent131(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
