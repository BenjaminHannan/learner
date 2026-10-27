#!/usr/bin/env python3
"""Experiment 215 -- "X IS THE R OF Y" MEANS "Y'S R IS X" (Muse).

THE ONE CHANGE (one parser change on base loop138i): the noun phrase
"the R of Y" / "a R of Y" / "an R of Y" is read as "Y's R", for any
relation word R (1-3 lowercase words, no clause or function words; Y a
name-like span or a known entity; if the middle contains "of", split at
the last " of " whose right side is a name).

  Teaches: "X is the R of Y." is rewritten to "Y's R is X." BEFORE the
  normal pipeline, so every existing check (write checks, multi-valued,
  re-teach asks, corrections) still runs on the rewritten text.
  Questions: "Who/What is the R of Y?" is rewritten to "Who/What is Y's
  R?" only when the notebook already holds relation R for some entity
  (safe; unknown R keeps today's behaviour).

Never rewritten: first-person ("I am the ...", "I is ..."), no article
before R, Y not a name ("the best of friends", "the last of five",
"the talk of the town", "one of the cities"), multi-sentence glued
turns, "?" / "!" / ";" turns (teach side).

New files only; scripts/fable_loop138i_agent.py is never edited: the
mixin sits OUTERMOST (outside ChainOf174) and the loop subclasses the
138i loop with no behaviour change besides the ears.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop215_agent.py --daemon --dir DIR \\
    --config artifacts/fable-ofteach215-20260922/loop215-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols + thresholds, read-only)
import fable_loop102_agent as L102  # noqa: E402 (hearsay guard, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (wrapped base, read-only)

# --------------------------------------------------------------------------
# Closed function-word set for R. Relation content words (boss, mother,
# city, composer, founder, capital, captain, ...) are NOT in here.
_FUNCTION_WORDS215 = frozenset({
    "the", "a", "an", "of", "and", "or", "but", "not", "no",
    "my", "your", "his", "her", "its", "our", "their",
    "this", "that", "these", "those",
    "which", "who", "whom", "whose", "what", "when", "where", "why", "how",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "do", "does", "did", "have", "has", "had",
    "will", "would", "can", "could", "should", "shall", "may", "might", "must",
    "to", "in", "on", "at", "by", "for", "with", "from", "as",
    "into", "out", "over", "under", "after", "before", "between",
    "through", "during", "about", "against", "among", "within", "without",
    "very", "most", "more", "best", "last", "first",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "all", "any", "each", "every", "some", "such", "only", "just",
    "also", "even", "than", "then", "so", "because", "if", "while",
    "although", "though", "since", "until", "unless",
    "he", "she", "it", "they", "we", "you", "i",
    "me", "him", "us", "them",
    "say", "said", "says", "tell", "told",
    "there", "here", "now", "used",
})

_WH_WORDS215 = frozenset({
    "who", "whom", "whose", "what", "which", "where", "when", "why", "how",
})
_NAME_TOK_RE = re.compile(r"^[A-Z][A-Za-z'\-]*$")
_REL_TOK_RE = re.compile(r"^[a-z][a-z'\-]*$")
_OF_SPLIT_RE = re.compile(r"\s+[Oo][Ff]\s+")
_CORRECTION_PREFIX_RE = re.compile(r"^(actually|no)\s*,\s*(.*)$",
                                   re.IGNORECASE | re.DOTALL)
_TEACH_RE = re.compile(
    r"^(?P<x>.+?)\s+[Ii][Ss]\s+(?P<art>the|a|an)\s+(?P<mid>.+?)\s*$",
    re.IGNORECASE | re.DOTALL)
_QUESTION_RE = re.compile(
    r"^(?P<qw>who|what)\s+(?P<verb>is|are)\s+(?P<art>the|a|an)\s+"
    r"(?P<mid>.+?)\s*$",
    re.IGNORECASE | re.DOTALL)


def valid_relation215(rel: str) -> bool:
    """1-3 lowercase words, no clause/function words."""
    toks = str(rel).split()
    if not (1 <= len(toks) <= 3):
        return False
    for tok in toks:
        t = tok.strip(".,;:'\"()")
        if not t or not _REL_TOK_RE.match(t):
            return False
        if t.lower() in _FUNCTION_WORDS215:
            return False
    return True


def is_name_like215(span: str) -> bool:
    """1-4 words, each starting with an uppercase letter (strict).

    A leading lowercase article ("the Comets") is NOT name-like here;
    split_middle215 strips one leading article explicitly so teach and
    ask agree on the article-free owner.
    """
    toks = str(span).split()
    if not (1 <= len(toks) <= 4):
        return False
    for tok in toks:
        t = tok.strip(".,;:'\"()")
        if not t or not _NAME_TOK_RE.match(t):
            return False
    return True


def is_known_entity215(nb, span: str) -> bool:
    """True when the notebook already resolves the span to an entity."""
    if nb is None:
        return False
    try:
        return nb.resolve(str(span).strip()).status == L138I.C.OK
    except Exception:
        return False


def notebook_holds_relation215(nb, rel_key: str) -> bool:
    """True when the notebook already declares relation key for some entity."""
    if nb is None:
        return False
    try:
        for e in nb.events:
            if (isinstance(e, dict) and e.get("kind") == "RELATION"
                    and e.get("relation") == rel_key):
                return True
    except Exception:
        return False
    return False


def split_middle215(mid: str, nb=None) -> tuple[str, str] | None:
    """Split 'R of Y' at the last ' of ' whose right side is a name.

    Returns (R, Y) or None. R must be a valid relation word run; Y must
    be name-like or a known entity.
    """
    parts = _OF_SPLIT_RE.split(str(mid).strip())
    if len(parts) < 2:
        return None
    # Try rightmost split first ("last ' of ' whose right side is a name").
    for i in range(len(parts) - 1, 0, -1):
        rel = " ".join(" ".join(parts[:i]).split())
        who = " ".join(" ".join(parts[i:]).split())
        if not rel or not who:
            continue
        if not valid_relation215(rel):
            continue
        if is_known_entity215(nb, who):
            return rel, who
        toks = who.split()
        if (len(toks) > 1 and toks[0].lower() in ("the", "a", "an")
                and is_name_like215(" ".join(toks[1:]))
                and not is_known_entity215(nb, who)):
            # Team-style "the Comets": the base only stores the
            # article-free owner ("Comets's R is X." saves; "the
            # Comets's R ..." clarifies), so strip one leading article.
            # Teach and ask strip identically, so the pair still agrees.
            return rel, " ".join(toks[1:])
        if is_name_like215(who):
            return rel, who
    return None


def rewrite_teach215(turn: str, nb=None) -> str | None:
    """'X is the R of Y.' -> \"Y's R is X.\" or None when no rewrite fires."""
    text = " ".join(str(turn).split())
    if not text:
        return None
    if "?" in text or "!" in text or ";" in text:
        return None
    work = text.replace("\u2019", "'")
    prefix = ""
    m = _CORRECTION_PREFIX_RE.match(work)
    if m is not None:
        prefix, work = m.group(1) + ", ", m.group(2).strip()
    stem = work.strip()
    if not stem.endswith("."):
        return None  # teaches need their terminal period; bare fragments pass
    if stem[:-1].count(".") > 0:
        return None  # glued sentences: never spliced
    core = stem[:-1].strip()
    if not core:
        return None
    m = _TEACH_RE.match(core)
    if m is None:
        return None
    subj = " ".join(m.group("x").split())
    mid = " ".join(m.group("mid").split())
    if not subj or not mid:
        return None
    if subj.strip().lower() == "i":
        return None  # first-person: never rewritten
    if subj.strip().lower() in _WH_WORDS215:
        return None  # question word as subject ("What is the ... .")
    try:
        if L102.is_hearsay(text) or L102.subject_is_hearsay_shaped(subj):
            return None  # hearsay stays on the base path (refusal preserved)
        slow = subj.lower()
        if any(frag in slow for frag in L102._SUBJECT_FRAGMENTS):
            return None  # attribution vocab anywhere in X (any case)
    except Exception:
        pass
    if "." in subj:
        return None  # glued fragments on the subject side: never spliced
    split = split_middle215(mid, nb)
    if split is None:
        return None
    rel, who = split
    return f"{prefix}{who}'s {rel} is {subj}."


def rewrite_question215(turn: str, nb=None) -> str | None:
    """'Who/What is the R of Y?' -> \"Who/What is Y's R?\" or None.

    Fires only when the notebook already holds relation R (safe gate).
    """
    text = " ".join(str(turn).split())
    if not text:
        return None
    work = text.replace("\u2019", "'").strip()
    if not work.endswith("?"):
        return None
    if ("?" in work[:-1]) or ("!" in work):
        return None
    core = work[:-1].strip()
    m = _QUESTION_RE.match(core)
    if m is None:
        return None
    mid = " ".join(m.group("mid").split())
    if not mid:
        return None
    split = split_middle215(mid, nb)
    if split is None:
        return None
    rel, who = split
    rel_key = "_".join(rel.lower().split())
    if not notebook_holds_relation215(nb, rel_key):
        return None  # unknown R keeps today's behaviour
    qw = m.group("qw")
    qw = "Who" if qw.lower() == "who" else "What"
    return f"{qw} {m.group('verb').lower()} {who}'s {rel}?"


class OfTeach215Mixin:
    """Outermost ears rewrite: of-phrase -> possessive twin before parsing.

    Teach side: return the base's hearing of the rewritten text directly,
    so every existing check runs on the rewritten text. Question side:
    probe the candidate and take it iff the base parses it as an ask
    (asks never write, so the probe is side-effect free).
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        text = " ".join(str(turn).split())
        if text.rstrip().endswith("?"):
            cand = rewrite_question215(turn, nb)
            if cand is not None and cand != text:
                try:
                    probe = super().hear(cand)  # type: ignore[misc]
                except Exception:
                    probe = None
                if isinstance(probe, list) and any(
                        isinstance(a, dict) and a.get("act") == "ask"
                        for a in probe):
                    try:
                        self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                            "loop215-ofteach-q", 1.0)
                    except AttributeError:
                        pass
                    return probe
            return super().hear(turn)  # type: ignore[misc]
        cand = rewrite_teach215(turn, nb)
        if cand is not None and cand != text:
            try:
                self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                    "loop215-ofteach", 1.0)
            except AttributeError:
                pass
            return super().hear(cand)  # type: ignore[misc]
        return super().hear(turn)  # type: ignore[misc]


class Loop215Ears(OfTeach215Mixin, L138I.Loop138iEars):
    """Loop138iEars + the 215 of-teach rewrite outside everything."""

    name = "loop215-ofteach"


class Loop215AgentLoop(L138I.Loop138iAgentLoop):
    """Loop138iAgentLoop; ears differ, acts don't."""


DEFAULT_CONFIG215: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG215["ears"]["stand_in"] = (
    "Loop215Ears (loop138i stack + outermost of-teach rewrite: "
    "'X is the R of Y.' -> \"Y's R is X.\"; "
    "'Who/What is the R of Y?' -> \"Y's R?\" iff R known)")
DEFAULT_CONFIG215["daemon"]["module"] = "Loop215Daemon (this file)"


def build_agent215(cfg: dict | None = None) -> Loop215AgentLoop:
    """Build the loop138i agent shape with the 215 rewrite stacked on."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG215, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L138I.L90.ChainEars(cfg)
    mouth = L138I.L167E.Label167eMouth(L138I.L138b.Loop138bMouth())
    reasoner = L138I.L138d.Reasoner138d()
    from fable_wire51_adapters import (  # noqa: E402 (read-only)
        HardGate46Sleeper)
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop215Ears(Loop96Ears(chain))
    loop = Loop215AgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    L138I.patch_chain142(chain)
    L138I.patch_loop121_teach(inner_ears)
    thinker, thinker_module = L138I.L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    loop._screen148b_tag = None
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    store = L138I.D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    loop._dc166c = {}
    L138I._wrap_relation154e(loop)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138i: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop215: loop138i + of-teach rewrite ('X is the R "
                      "of Y.' -> \"Y's R is X.\"; of-questions iff R known)")
    return loop


class Loop215Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon shape with the 215 agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = L138I.D141.SETTLE_GRACE_S) -> None:
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
        self.loop = build_agent215(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L138I.D108.boot_reconcile(self)
        self.settle = L138I.D141.SettleGate141(grace_s=grace_s)


def run_daemon215(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop215Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 215 of-teach loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138i)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG215 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG215)
        out["thinker"]["module"] = L138I.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG215)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon215(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent215(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
