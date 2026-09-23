#!/usr/bin/env python3
"""Exp 221c -- QUESTION NORMALISATION before 221's table matching.

loop221c = loop221 (scripts/fable_loop221_agent.py) + ONE change:
QNorm221cMixin sits OUTERMOST on the 221 ears (before TableAsk221Mixin).

For a question-shaped turn it builds a rewritten text (normalise221c):
  - extra spaces collapsed; a leading "so," / "um," / "hey," dropped;
  - contractions what's/who's/where's/when's/how's -> "<wh> is",
    how'd -> "how did", 're -> " are" (case-insensitive, ' or U+2019);
  - trailing fillers dropped (repeatedly): again, now, then, anyway,
    exactly, please, by the way (optionally after a comma). A filler
    written with a capital letter and no comma before it is kept (it is
    probably part of a title, e.g. "Right Now");
  - a missing final "?" added when the turn starts with a question word
    and has no final . ! or ?;
  - plural relation nouns of MULTI-valued table relations:
      "<WH> are <X>'s <plural>"   -> "<WH> is <X>'s <singular>"
      "<WH> are my <plural>"      -> "<WH> is my <singular>"
      "<WH> are the <plural> of <X>" -> "<WH> is the <singular> of <X>"
    (the base ask on a multi-valued key already lists ALL stored values).
  - case: every rule matches case-insensitively; the rewritten words are
    written lower-case; names keep their case (notebook names are
    case-sensitive keys; the table templates already ignore case).

The rewritten text is used ONLY if (1) it differs from the turn,
(2) it has exactly one table-221 reading (unique_reading221), and
(3) the full 221 stack's actions on it are all ask/clarify/answer (no
write act). Otherwise the ORIGINAL turn goes through the 221 stack exactly
as today. Statements (turns ending in "." or "!", or not starting with a
question word and not ending in "?") are never rewritten.

Optional trace: env QNORM221C_LOG=<file> appends one JSON line per
rewrite used (for predicting suite moves). No other behaviour change.

New file only; 221, 138i and every earlier piece are read-only.
Daemon launch (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop221c_agent.py --daemon --dir DIR \\
    --config artifacts/claude-qnorm221c-20260922/loop221c-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop221_agent as L221  # noqa: E402 (wrapped, read-only)
import fable_fix221_tableask as T221  # noqa: E402 (read-only)

A = L221.A
D108 = L221.D108
D141 = L221.D141
D146B = L221.D146B
L90 = L221.L90
L138b = L221.L138b
L138d = L221.L138d
L138I = L221.L138I
L167E = L221.L167E

STAGE221C = "loop221c-qnorm"
_QWORDS = ("who", "what", "where", "when", "which", "whose", "how", "why")
_APOS = "['’]"
_CONTRACT = [
    (re.compile(rf"\b(what|who|where|when|how){_APOS}s\b", re.I),
     lambda m: m.group(1).lower() + " is"),
    (re.compile(rf"\bhow{_APOS}d\b", re.I), lambda m: "how did"),
    (re.compile(rf"\b([a-z]+){_APOS}re\b", re.I),
     lambda m: m.group(1) + " are"),
]
_LEAD = re.compile(r"^(so|um|hey)\s*,\s*", re.I)
_FILLERS = ("by the way", "again", "now", "then", "anyway", "exactly",
            "please")
_TRAIL = re.compile(
    r"(?P<comma>\s*,)?\s+(?P<f>" + "|".join(re.escape(f) for f in _FILLERS)
    + r")\s*$", re.I)
_WRITE_FREE = frozenset({"ask", "clarify", "answer"})


def _plural(word: str) -> list[str]:
    w = word.lower()
    irregular = {"child": ["children"], "grandchild": ["grandchildren"],
                 "grand child": ["grand children"]}
    if w in irregular:
        return irregular[w]
    head, _, last = w.rpartition(" ")
    pre = head + " " if head else ""
    if last == "child":
        return [pre + "children"]
    if re.search(r"[^aeiou]y$", last):
        forms = [last[:-1] + "ies"]
    elif re.search(r"(s|x|z|ch|sh)$", last):
        forms = [last + "es"]
    else:
        forms = [last + "s"]
    return [pre + f for f in forms]


def plural_map221c(table: T221.Table221 | None = None) -> dict[str, str]:
    """plural surface -> singular surface, MULTI-valued relations only."""
    table = table or T221.get_table221()
    out: dict[str, str] = {}
    for name in table.order:
        r = table.rels[name]
        if r.get("cardinality") != "multi":
            continue
        for s in [name.replace("_", " ")] + list(r.get("aliases", [])):
            for p in _plural(s):
                out.setdefault(p, s.lower())
    return out


_PLURAL_CACHE: dict[int, tuple] = {}


def _plural_res(table: T221.Table221):
    key = id(table)
    if key not in _PLURAL_CACHE:
        pm = plural_map221c(table)
        alts = "|".join(re.escape(p) for p in
                        sorted(pm, key=len, reverse=True))
        wh = "|".join(_QWORDS)
        rx_poss = re.compile(
            rf"^(?P<wh>{wh}) are (?P<x>my|.+?{_APOS}s) (?P<p>{alts})$", re.I)
        rx_of = re.compile(
            rf"^(?P<wh>{wh}) are the (?P<p>{alts}) of (?P<x>.+)$", re.I)
        _PLURAL_CACHE[key] = (pm, rx_poss, rx_of)
    return _PLURAL_CACHE[key]


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def question_shaped221c(turn: str) -> bool:
    t = " ".join(str(turn).split())
    t = _LEAD.sub("", t)
    if not t:
        return False
    if t.endswith("?"):
        return True
    if t[-1] in ".!":
        return False
    first = re.split(r"[\s'’,]", t, maxsplit=1)[0].lower()
    return first in _QWORDS


def normalise221c(turn: str, table: T221.Table221 | None = None) -> str:
    """Rewritten text of a question-shaped turn (or the turn unchanged)."""
    table = table or T221.get_table221()
    raw = str(turn)
    if not question_shaped221c(raw):
        return raw
    t = " ".join(raw.split())
    t = _LEAD.sub("", t)
    had_q = t.endswith("?")
    body = t.rstrip(" ?").rstrip()
    for rx, fn in _CONTRACT:
        body = rx.sub(fn, body)
    while True:
        m = _TRAIL.search(body)
        if not m:
            break
        f = m.group("f")
        if f[:1].isupper() and not m.group("comma"):
            break  # likely part of a title ("Right Now")
        body = body[:m.start()].rstrip(" ,")
    body = " ".join(body.split())
    if body:
        first, _, rest = body.partition(" ")
        if first.lower() in _QWORDS:
            body = (first.lower() + (" " + rest if rest else ""))
    pm, rx_poss, rx_of = _plural_res(table)
    m = rx_poss.match(body)
    if m:
        body = f"{m.group('wh').lower()} is {m.group('x')} " \
               f"{pm[m.group('p').lower()]}"
    else:
        m = rx_of.match(body)
        if m:
            body = f"{m.group('wh').lower()} is the " \
                   f"{pm[m.group('p').lower()]} of {m.group('x')}"
    if not body:
        return raw
    del had_q  # the rewritten question always ends in "?"
    return _cap(body) + "?"


class QNorm221cMixin:
    """Outermost ears stage: question normalisation (never writes)."""

    last_qnorm221c: dict | None = None

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        self.last_qnorm221c = None
        try:
            table = self._table221()  # type: ignore[attr-defined]
            new = normalise221c(turn, table)
        except Exception:  # noqa: BLE001 -- normaliser never breaks a turn
            new = turn
        if new != turn and new != " ".join(str(turn).split()) \
                and T221.unique_reading221(new, table) is not None:
            acts = super().hear(new)  # type: ignore[misc]
            if isinstance(acts, list) and all(
                    isinstance(a, dict) and a.get("act") in _WRITE_FREE
                    for a in acts):
                self.last_qnorm221c = {"turn": turn, "rewritten": new}
                log = os.environ.get("QNORM221C_LOG")
                if log:
                    try:
                        with open(log, "a", encoding="utf-8") as fh:
                            fh.write(json.dumps(
                                {"turn": turn, "rewritten": new}) + "\n")
                    except OSError:
                        pass
                return acts
        return super().hear(turn)  # type: ignore[misc]


class Loop221cEars(QNorm221cMixin, L221.Loop221Ears):
    """Loop221Ears with the question normaliser outermost."""

    name = "loop221c-qnorm"


class Loop221cAgentLoop(L221.Loop221AgentLoop):
    """Loop221AgentLoop unchanged (renamed for logs)."""


DEFAULT_CONFIG221C: dict = copy.deepcopy(L221.DEFAULT_CONFIG221)
DEFAULT_CONFIG221C["ears"]["stand_in"] = (
    L221.DEFAULT_CONFIG221["ears"]["stand_in"]
    + "; 221c question normaliser outermost")
DEFAULT_CONFIG221C["daemon"]["module"] = "Loop221cDaemon (this file)"


def build_agent221c(cfg: dict | None = None) -> Loop221cAgentLoop:
    """build_agent221 (scripts/fable_loop221_agent.py) with only the ears
    class swapped for Loop221cEars."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG221C, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L167E.Label167eMouth(L138b.Loop138bMouth())
    reasoner = L138d.Reasoner138d()
    sleeper = L221.HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    inner_ears = Loop221cEars(L221.Loop96Ears(chain))
    inner_ears.table221_path = cfg.get("table221_path") or None
    loop = Loop221cAgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    L221.patch_chain142(chain)
    L221.patch_loop121_teach(inner_ears)
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
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    loop._dc166c = {}
    L138I._wrap_relation154e(loop)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138i: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop221: loop138i + TableAsk221Mixin outermost "
                      "(questions read through relation table v1; writes "
                      "untouched)")
    loop.notes.append("loop221c: loop221 + QNorm221cMixin outermost "
                      "(question normalisation; writes untouched)")
    return loop


class Loop221cDaemon(L221.Loop221Daemon):
    """Loop221Daemon shape with the 221c agent inside."""

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
        self.pid = os.getpid()
        self.boot_time = time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent221c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon221c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop221cDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def selftest221c() -> int:
    tb = T221.get_table221()
    checks = [
        ("When's Tamsin Orle's birthday?", "When is Tamsin Orle's birthday?"),
        ("When is my birthday again?", "When is my birthday?"),
        ("Who's my manager?", "Who is my manager?"),
        ("Who are Garrow Blythe's friends?", "Who is Garrow Blythe's friend?"),
        ("Who're my cousins?", "Who is my cousin?"),
        ("so, where does Pim Arlo work now?", "Where does Pim Arlo work?"),
        ("Who is Pim Arlo's boss", "Who is Pim Arlo's boss?"),
        ("who  is Pim Arlo's boss,  please?", "Who is Pim Arlo's boss?"),
        ("Who composed Right Now?", "Who composed Right Now?"),
        ("Pim Arlo's boss is Tev Oran.", "Pim Arlo's boss is Tev Oran."),
        ("What a day.", "What a day."),
        ("Who are Pim Arlo's bosses?", "Who are Pim Arlo's bosses?"),
        ("What are the hobbies of Pim Arlo?", "What is the hobby of Pim Arlo?"),
        ("Who are my children?", "Who is my child?"),
    ]
    ok = True
    for text, want in checks:
        got = normalise221c(text, tb)
        good = got == want
        ok = ok and good
        print(f"{'OK' if good else 'MISMATCH'}: {text!r} -> {got!r}"
              f" (want {want!r})")
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 221c qnorm on 221")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest221c()
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG221C)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print("Wrote %s" % args.write_config)
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG221C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon221c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent221c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
