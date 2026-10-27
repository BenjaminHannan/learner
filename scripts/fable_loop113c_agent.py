#!/usr/bin/env python3
"""Experiment 113c -- registered single-change follow-up to exp 113b.

Diagnosis from 113b (design doc 113b, artifact fable-bench113b-20260922):
on broken-chain / qualifier questions the B92 composer returns a 1-hop
PREFIX frame instead of None, so the 113b fallback never fires and the
agent confidently answers a SHORTER question than the one asked. The 4 P2
cases: B7 and C2 ("...country of citizenship is Atlantis/Spain" where turn
3 should abstain), C5 ("Fasti's author is Ovid" where it should abstain),
D8 (turn 1 leaks "Poland's capital is Warsaw" where it should abstain).
Loop102 handled all 4 correctly.

THE ONE CHANGE (question side only; teach path and everything else
byte-identical to loop113b):

  A composer frame counts as usable only if it consumes every relation
  phrase / qualifier in the question (no leftover content words after the
  frame is matched). Concretely, frame_consumes_question() returns False
  when (a) the question carries a trailing year qualifier ("in/since/
  until <year>", "from <year> to <year>", "as of <year>", trailing "?"
  allowed -- loop102 never strips qualifiers on questions, so a composer
  frame cannot consume one), or (b) after deleting every occurrence of the
  walked relations' own mention cues (longest cue first, word boundaries
  for single-word cues), some OTHER relation's mention cue still matches
  the remainder (the interrogative/relative word "where" is exempt: it is
  scaffolding, never a distinctive relation phrase). A partial or prefix
  frame is treated exactly like None -> delegate to the unchanged loop102
  chain (Loop102Ears.hear on the same instance), as 113b does for
  double-None. The B73 explicit-2-hop branch gets the same consumption
  test; compound-guard and non-explicit behaviour are unchanged.

No existing file is edited; everything new lives in this file.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop113c_agent.py --daemon --dir DIR \\
    --config artifacts/fable-bench113c-20260922/loop113c-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (Protocols + base loop, read-only)
import fable_bench73_english_arm as B73  # noqa: E402 (2-hop composer, read-only)
import fable_bench92_english_arm as B92  # noqa: E402 (N-hop composer, read-only)
import fable_fix77_core as F77  # noqa: E402 (gate + reasoner + seal, read-only)
import fable_loop102_agent as L102  # noqa: E402 (fallback chain, read-only)
import fable_loop113_agent as L113  # noqa: E402 (v1 routing, read-only)
import fable_loop113b_agent as L113B  # noqa: E402 (fallback routing, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper, NotebookThinker)

# Trailing year qualifiers (loop102 F4 shape, extended to a trailing "?":
# loop102 never strips these on questions, so no composer frame consumes
# one -- a frame on such a question is always a prefix frame).
_QUAL_RES = [
    re.compile(r"\s+from\s+\d{4}\s+to\s+\d{4}\s*[\?.]?\s*$",
               re.IGNORECASE),
    re.compile(r"\s+as\s+of\s+\d{4}\s*[\?.]?\s*$", re.IGNORECASE),
    re.compile(r"\s+(in|since|until)\s+\d{4}\s*[\?.]?\s*$", re.IGNORECASE),
]

# Cues exempt from leftover detection. "where" is interrogative/relative
# scaffolding (fires on every relative clause); "city where",
# "city located where", "located", "situated", "home to", "is home"
# describe WHERE a walked hop happened without naming another relation;
# bare "played"/"plays" (music performed vs sport played), bare
# "speak"/"speaks"/"spoken" (shared across every language relation) and
# bare "work" (a creation, as in "the work that ... is famous for") are
# shared vocabulary, never distinctive of one relation. None of these is
# ever the sole evidence of the 113b partial class (whose leftovers are
# precise phrases: "official language", "born"/"birthplace", or a
# trailing year qualifier).
_DROP_CUES = frozenset({"where", "city where", "city located where",
                        "located", "situated", "home to", "is home",
                        "played", "plays", "speak", "speaks", "spoken",
                        "work"})

_WORD_RES: dict[str, re.Pattern] = {}


def _word_re(cue: str) -> re.Pattern:
    rx = _WORD_RES.get(cue)
    if rx is None:
        rx = re.compile(r"\b" + re.escape(cue) + r"\b")
        _WORD_RES[cue] = rx
    return rx


def _norm_q(question: str) -> str:
    return " ".join(str(question).split()).lower()


def has_trailing_qualifier(question: str) -> bool:
    """True when a year qualifier trails the question (never consumable)."""
    q = " ".join(str(question).split())
    return any(rx.search(q) for rx in _QUAL_RES)


def frame_consumes_question(question: str, rels: list[str],
                            triples: list[tuple[str, str, str]] | None = None
                            ) -> bool:
    """True only if the frame consumes every relation phrase + qualifier.

    Steps: (1) trailing year qualifier -> False; (2) delete every
    occurrence of the walked relations' own mention cues, longest cue
    first, by SUBSTRING (stems such as "creat" must eat their inflections;
    over-eating is the safe direction -- it can only hide a partial, never
    invent one); (3) delete entity-mention spans, longest name first (a
    leftover cue inside a NAME, e.g. "death" in "Death Eater" or "language"
    in "Web Services Description Language", is not a relation phrase);
    (4) if any OTHER relation's cue (minus the scaffolding exemptions)
    still matches the remainder -- multi-word cues by substring,
    single-word cues on word boundaries so "office" never fires on
    "officer" -- -> False (a prefix frame). Else True.
    """
    q = _norm_q(question)
    if has_trailing_qualifier(question):
        return False
    walked = [str(r) for r in (rels or [])]
    if not walked:
        return False
    cues: list[str] = []
    for rel in walked:
        cues.extend(B92.REL_CUES92.get(rel, []))
    work = q
    for cue in sorted(set(cues), key=len, reverse=True):
        c = cue.lower()
        if c:
            work = work.replace(c, " ")
    if triples:
        names = sorted({str(s) for s, _, _ in triples}
                       | {str(o) for _, _, o in triples},
                       key=len, reverse=True)
        for name in names:
            n = " ".join(str(name).split()).lower()
            if n:
                work = work.replace(n, " ")
    walked_set = set(walked)
    for rel, rcues in B92.REL_CUES92.items():
        if rel in walked_set:
            continue
        for cue in rcues:
            c = cue.lower()
            if c in _DROP_CUES:
                continue
            if " " in c:
                if c in work:
                    return False
            elif _word_re(c).search(work):
                return False
    return True


class Loop113cEars(L113B.Loop113bEars):
    """Loop113bEars + partial/prefix frames treated exactly like None.

    hear() phases on "?" turns: F1 hearsay screen first (unchanged); then
    both composers are consulted on the notebook triples. A non-None frame
    is asked only if it ALSO passes frame_consumes_question() (plus the
    unchanged compound-subject guard / explicit-shape rules); a frame that
    fails consumption delegates to the exact loop102 chain
    (Loop102Ears.hear on this same instance), exactly as 113b does for
    double-None. Non-"?" turns inherit 113b behaviour (byte-identical to
    loop102 off "?" turns).
    """

    name = "loop113c-partial-frame"

    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if text and text.rstrip().endswith("?"):
            if L102.is_hearsay(text):  # F1 preserved on questions
                self.last_stage, self.last_score = "loop113c-hearsay", 1.0
                return [{"act": "clarify", "text": L102.HEARSAY_MSG}]
            if self.nb is None:
                return self._delegate(turn)
            triples = L90.notebook_triples(self.nb)
            frame = B92.compose_n_hop(text, triples)
            if frame is not None:
                if frame_consumes_question(text, list(frame[1]), triples):
                    hit = L113.compound_subject_hit(triples, frame[0],
                                                    list(frame[1]))
                    if hit is None:
                        self.last_stage, self.last_score = (
                            "loop113c-nhop", 1.0)
                        return [{"act": "ask", "name": frame[0],
                                 "relations": list(frame[1]),
                                 "stage": "loop113c"}]
                    self.last_stage, self.last_score = (
                        "loop113c-compound-guard", 1.0)
                    return [{"act": "clarify",
                             "text": L113.CHAIN_MISS_TEXT}]
                # Partial/prefix frame -> exactly like None (the one change).
                self.last_stage, self.last_score = (
                    "loop113c-partial", 1.0)
                return L102.Loop102Ears.hear(self, turn)
            frame2 = B73.compose_question(text, triples)
            if frame2 is not None:
                if (L113.is_explicit_question(text)
                        and frame_consumes_question(text, list(frame2[1]),
                                                    triples)):
                    self.last_stage, self.last_score = (
                        "loop113c-explicit", 1.0)
                    return [{"act": "ask", "name": frame2[0],
                             "relations": list(frame2[1]),
                             "stage": "loop113c"}]
                if not L113.is_explicit_question(text):
                    # Non-explicit 2-hop frame: the truncation shape.
                    self.last_stage, self.last_score = (
                        "loop113c-nonexplicit", 1.0)
                    return [{"act": "clarify",
                             "text": L113.CHAIN_MISS_TEXT}]
                self.last_stage, self.last_score = (
                    "loop113c-partial", 1.0)
                return L102.Loop102Ears.hear(self, turn)
            # Both composers None -> exact loop102 chain (unchanged 113b).
            return L102.Loop102Ears.hear(self, turn)
        return super().hear(turn)


class Loop113cAgentLoop(L113B.Loop113bAgentLoop):
    """Loop113bAgentLoop (forget2 action included); ears differ, acts don't."""


DEFAULT_CONFIG113C: dict = copy.deepcopy(L113B.DEFAULT_CONFIG113B)
DEFAULT_CONFIG113C["ears"]["stand_in"] = (
    "Loop113cEars (113b router + partial/prefix composer frames treated "
    "exactly like None: a frame must consume every relation phrase / "
    "qualifier in the question, else delegate to the exact loop102 chain) "
    "over Loop102Ears pre-filter over Loop96Ears = GuardedEars91 over "
    "ChainEars(bench73 template + FakeEars templates); teach path identical "
    "to loop102")
DEFAULT_CONFIG113C["daemon"]["module"] = "Loop113cDaemon (this file)"


def build_agent113c(cfg: dict | None = None) -> Loop113cAgentLoop:
    """Build the loop113b agent shape with Loop113cEars on the question side."""
    cfg = dict(DEFAULT_CONFIG113C, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    reasoner = F77.QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4102)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop113cAgentLoop(
        state_dir, ears=Loop113cEars(Loop96Ears(chain)), mouth=mouth,
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
    return loop


class Loop113cDaemon(L113B.Loop113bDaemon):
    """Loop113bDaemon shape with the loop113c agent inside (mailbox identical)."""

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
        self.loop = build_agent113c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon113c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop113cDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 113c partial-frame loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop113b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG113C to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG113C)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG113C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon113c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent113c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
