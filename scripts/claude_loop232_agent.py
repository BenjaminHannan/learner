#!/usr/bin/env python3
"""Experiment 232 -- THE ONE CHANGE vs loop138i: multi-word names in verb
sentences.

Gap (reproduced on 138i, artifacts/claude-fullname232-20260922/repro-138i.txt):
"Orrin lives in Quellmoor." saves (Orrin, city, Quellmoor) and "Where does
Orrin live?" answers, but "Orrin Vask lives in Quellmoor." writes nothing and
"Where does Orrin Vask live?" is not understood, while the possessive twin
"Orrin Vask's city is Quellmoor." saves (exp 137 upgrade inside loop138b).

Cause: the verb mixins (scripts/fable_fix167_verb.py V167._NAME / _subject_ok,
reused by scripts/fable_fix167d_verb.py) accept only ONE capital-lead token
as the subject, so every multi-word verb turn declines to the base clarify.

THE ONE CHANGE: Verb232Mixin, placed exactly where the verb mixins sit
(inside 174 of-chain and 165 typo, outside the 167b screen), claims the SAME
five verb statements and five verb questions 138i claims for one-word names
(lives in / works for / was born in / works at / speaks; Where does X live? /
Who does X work for? / Where was X born? / Where does X work? / What
language(s) does X speak?) when the subject is a 2-4 word proper name, and
hands on EXACTLY the possessive twin 138i builds for one-word names.  The
possessive path (137 upgrade + 139b value veto + 150 subject veto + every
layer-B mixin + loop _act guards + mouth) then runs as for a one-word twin.
Statement objects pass the same 167b value screen (S167B.screen_value) with
the same no-write clarify; the same declines apply (negation/tense/hedge
shapes never match; "?"/";"/extra "." in the value; bench73-owned "was born
in the city of" / "speaks the language of").

Subject rule (subject_ok232): 2-4 whitespace tokens; first and last tokens
are 137 name tokens (scripts/fable_fix137_names.py is_name137_token); middle
tokens are 137 name tokens or lower-case particles from PARTICLES232; no
token ends in a possessive 's; no token (case-insensitive) is a 150
hedge/reporting/filler word or a closed non-name word (NONNAME232); the whole
subject passes the 150c closed-class veto and S150.screen_subject_150 with
verdict "store" and the subject unchanged.  Anything else declines: the raw
turn goes on to the 138i chain untouched.  One-token subjects are never
claimed here (138i's own verb mixins own them), so one-word behaviour is
byte-identical by construction.

Particles: the 137 possessive upgrade refuses lower-case tokens, so for a
twin this mixin built (and only that twin, matched by exact text) the
loop138b _upgrade137 step is re-run on a surrogate twin whose particles are
title-cased; if it produces a teach/correct for the surrogate subject, the
original subject is put back.  All the same vetoes run (G91, 139b, 150 on
the surrogate; 150 re-run at loop _act on the real name).  User-typed
possessive turns are never widened.

Additive only: no existing file is edited; 138i modules imported read-only.
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

import fable_agent_loop as A  # noqa: E402 (read-only)
import fable_doubt146_store as D146  # noqa: E402 (doubt detector, read-only)
import fable_earsguard91 as G91  # noqa: E402 (value screen, read-only)
import fable_fix129_punct as P129  # noqa: E402 (strip rule, read-only)
import fable_fix137_names as F137  # noqa: E402 (name token rule, read-only)
import fable_fix139b_valueguard as V139B  # noqa: E402 (value guard, read-only)
import fable_fix140_tail as T140  # noqa: E402 (tail cleaner, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject guard, read-only)
import fable_fix150c_closedclass as C150  # noqa: E402 (closed class, read-only)
import fable_fix167b_valuescreen as S167B  # noqa: E402 (value screen, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (wrapped base, read-only)
from claude_fix228_srcguard import (  # noqa: E402 (required 228 flake guard)
    SrcGuardMixin228, install_srcguard228)

# Required by the 2026-09-22 rules for every new 138i-family experiment: the
# 228 fix170 _src_of identity guard (not part of the 232 change itself).
install_srcguard228()

# ----------------------------------------------------------------------------
# Closed lists (fixed in design/v3/30-modes/232-fullname-opus.md before any
# panel read).
# ----------------------------------------------------------------------------
MAX_TOKENS232 = 4
PARTICLES232 = frozenset({
    "de", "da", "di", "do", "dos", "das", "del", "della", "der", "den",
    "des", "du", "van", "von", "la", "le", "ter", "ten", "bin", "ibn", "al",
})


def _opener_words() -> frozenset:
    words = set()
    for group in (S150.HEDGE_OPENERS, S150.REPORTING_OPENERS,
                  S150.FILLER_OPENERS):
        for phrase in group:
            parts = phrase.split()
            if len(parts) == 1:
                words.add(parts[0])
    return frozenset(words)


# Single-word 150 openers anywhere in the subject -> decline.
OPENER_WORDS232 = _opener_words()
# Multi-word 150 openers anywhere in the subject (token sequence) -> decline.
OPENER_PHRASES232 = tuple(
    tuple(p.split()) for g in (S150.HEDGE_OPENERS, S150.REPORTING_OPENERS,
                               S150.FILLER_OPENERS) for p in g
    if len(p.split()) > 1)
# Closed non-name words (pronouns, determiners, conjunctions, time words):
# a capitalised one is still not part of a person's name -> decline.
NONNAME232 = frozenset({
    "i", "me", "you", "he", "she", "it", "we", "they", "him", "her", "us",
    "them", "my", "your", "his", "its", "our", "their", "mine", "yours",
    "the", "a", "an", "this", "that", "these", "those", "some", "any",
    "every", "each", "no", "yes", "not", "and", "or", "but", "if", "when",
    "then", "now", "today", "yesterday", "tomorrow", "still", "sometimes",
    "usually", "currently", "only", "even", "just", "everyone", "everybody",
    "someone", "somebody", "nobody", "anyone", "anybody", "who", "what",
    "where", "which", "why", "how", "whose", "mom", "mum", "dad", "please",
})

_SUBJ = r"(.+?)"
# One-word stand-in subject used only to ask the 146 teach detector which
# relation a twin carries (never stored, never shown).
STAND_IN232 = "Qzvrenn"

_CORRECTION_LEAD = re.compile(r"^(actually\s*,|actually\s+|no\s*,|no\s+)(.+)$",
                              re.IGNORECASE | re.DOTALL)

# Statement shapes: same verb text and case rules as V167 / V167D; only the
# subject group is widened (then checked by subject_ok232).
_STMTS = (
    (re.compile(r"^" + _SUBJ + r"\s+lives?\s+in\s+(.+?)\s*$", re.DOTALL),
     "city", "born_or_lang_none"),
    (re.compile(r"^" + _SUBJ + r"\s+works?\s+for\s+(.+?)\s*$", re.DOTALL),
     "employer", "born_or_lang_none"),
    (re.compile(r"^" + _SUBJ + r"\s+was\s+born\s+in\s+(.+?)\s*$", re.DOTALL),
     "place of birth", "born"),
    (re.compile(r"^" + _SUBJ + r"\s+works?\s+at\s+(.+?)\s*$", re.DOTALL),
     "employer", "born_or_lang_none"),
    (re.compile(r"^" + _SUBJ + r"\s+speaks?\s+(.+?)\s*$", re.DOTALL),
     "language", "lang"),
)
_BORN_CITYOF = re.compile(r"^the\s+city\s+of\s+.+", re.IGNORECASE | re.DOTALL)
_SPEAK_LANGOF = re.compile(r"^the\s+language\s+of\s+.+",
                           re.IGNORECASE | re.DOTALL)

_ASKS = (
    (re.compile(r"^where\s+does?\s+" + _SUBJ + r"\s+live\s*\??\s*$",
                re.IGNORECASE | re.DOTALL),
     lambda n: f"Where is {n}'s city?"),
    (re.compile(r"^who\s+does?\s+" + _SUBJ + r"\s+work\s+for\s*\??\s*$",
                re.IGNORECASE | re.DOTALL),
     lambda n: f"Who is {n}'s employer?"),
    (re.compile(r"^where\s+was\s+" + _SUBJ + r"\s+born\s*\??\s*$",
                re.IGNORECASE | re.DOTALL),
     lambda n: f"Where is {n}'s place of birth?"),
    (re.compile(r"^where\s+does?\s+" + _SUBJ + r"\s+work\s*\??\s*$",
                re.IGNORECASE | re.DOTALL),
     lambda n: f"Who is {n}'s employer?"),
    (re.compile(r"^what\s+languages?\s+does?\s+" + _SUBJ +
                r"\s+speak\s*\??\s*$", re.IGNORECASE | re.DOTALL),
     lambda n: f"What is {n}'s language?"),
)


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def _strip_period(body: str) -> str:
    if body.endswith(".") and not body.endswith(".."):
        return body[:-1].strip()
    return body


def _possessive_token(tok: str) -> bool:
    low = tok.lower()
    return low.endswith("'s") or low.endswith("’s") or \
        tok.endswith("'") or tok.endswith("’")


def has_particle232(subject: str) -> bool:
    return any(t in PARTICLES232 for t in _norm(subject).split())


def subject_ok232(subject: str) -> bool:
    """True for a 2-4 word proper name the verb path may claim."""
    text = _norm(subject)
    toks = text.split()
    if not 2 <= len(toks) <= MAX_TOKENS232:
        return False
    for i, tok in enumerate(toks):
        if _possessive_token(tok):
            return False
        low = tok.lower().strip(".,")
        if low in OPENER_WORDS232 or low in NONNAME232:
            return False
        if F137.is_name137_token(tok) and tok == tok.strip(",;:\"()"):
            continue
        if 0 < i < len(toks) - 1 and tok in PARTICLES232:
            continue
        return False
    lows = [t.lower() for t in toks]
    for phrase in OPENER_PHRASES232:
        n = len(phrase)
        for i in range(len(lows) - n + 1):
            if tuple(lows[i:i + n]) == phrase:
                return False
    try:
        if C150.is_closed_class_subject(text):
            return False
        verdict, clean = S150.screen_subject_150(text)
    except Exception:
        return False
    return verdict == "store" and clean == text


def parse_statement232(turn: str) -> dict | None:
    text = _norm(turn)
    if not text or text.rstrip().endswith("?"):
        return None
    body = _strip_period(text)
    if not body:
        return None
    corr = ""
    m = _CORRECTION_LEAD.match(body)
    if m and m.group(2).strip():
        corr, body = m.group(1), m.group(2).strip()
        corr = "Actually, " if corr.strip().lower().startswith("actually") \
            else "No, "
    for pat, rsurf, special in _STMTS:
        m = pat.fullmatch(body)
        if m is None:
            continue
        name, val = m.group(1).strip(), m.group(2).strip()
        if not subject_ok232(name):
            # A multi-word span that is not a clean name: this shape is not
            # ours; try no other verb (the first verb match decides, as the
            # one-word path's regexes anchor on the subject).
            return None
        if not val or "?" in val or ";" in val or "?" in name:
            return None
        if "." in val:
            return None
        if special == "born" and _BORN_CITYOF.match(val):
            return None
        if special == "lang" and _SPEAK_LANGOF.match(val):
            return None
        return {"kind": "statement", "name": name, "rsurf": rsurf,
                "val": val, "corr": corr}
    return None


def parse_question232(turn: str) -> dict | None:
    text = _norm(turn)
    if not text:
        return None
    for pat, mk in _ASKS:
        m = pat.fullmatch(text)
        if m is None:
            continue
        name = m.group(1).strip()
        if not subject_ok232(name):
            return None
        return {"kind": "question", "name": name, "twin": mk(name)}
    return None


def parse_turn232(turn: str) -> dict | None:
    hit = parse_statement232(turn)
    if hit is not None:
        return hit
    return parse_question232(turn)


class Verb232Mixin:
    """Multi-word verb turns become their possessive twin; rest delegates."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        if nb is not None:
            try:
                parsed = parse_turn232(turn)
            except Exception:
                parsed = None
            if parsed is not None:
                if parsed["kind"] == "question":
                    twin = parsed["twin"]
                else:
                    clean = None
                    try:
                        clean = S167B.screen_value(parsed["val"])
                    except Exception:
                        clean = None
                    if clean is None:
                        return [{"act": "clarify",
                                 "text": S167B.NO_WRITE_CLARIFY}]
                    twin = (f"{parsed['corr']}{parsed['name']}'s "
                            f"{parsed['rsurf']} is {clean}.")
                prev = getattr(self, "_twin232", None)
                self._twin232 = (twin, parsed["name"])
                try:
                    res = super().hear(twin)  # type: ignore[misc]
                finally:
                    self._twin232 = prev
                if parsed["kind"] == "statement":
                    try:
                        self._doubt232(parsed["name"], twin, res)
                    except Exception:
                        pass
                    if isinstance(res, list):
                        res = [dict(a, v232=True) if isinstance(a, dict)
                               and a.get("act") in ("teach", "correct")
                               and a.get("structured") else a for a in res]
                return res
        return super().hear(turn)  # type: ignore[misc]

    # The 146 doubt store records a refused teach about a known subject, but
    # its teach detector (D146.detect_teach146) parses one-word possessive
    # subjects only, so a refused multi-word twin would leave no doubt where
    # the one-word twin leaves one. Same conditions as Doubt146Mixin.hear's
    # teach side; the relation comes from detect_teach146 on the same twin
    # with a one-word stand-in subject; recording goes through the stack's
    # own _record_doubt (146b hearsay exemption included).
    def _doubt232(self, name: str, twin: str, res) -> None:
        nb = getattr(self, "nb", None)
        if nb is None or not hasattr(self, "_record_doubt"):
            return
        if getattr(self, "_doubt_store", None) is None or \
                self._doubt_store() is None:  # type: ignore[attr-defined]
            return
        if not isinstance(res, list):
            return
        if not any(isinstance(a, dict) and a.get("act") == "clarify"
                   for a in res):
            return
        if any(isinstance(a, dict) and a.get("act") in D146.TEACH_ACTS
               for a in res):
            return
        idx = twin.find(name + "'s ")
        if idx < 0:
            return
        stand_in = twin[:idx] + STAND_IN232 + twin[idx + len(name):]
        triple = D146.detect_teach146(stand_in)
        if triple is None or triple[0] != STAND_IN232:
            return
        if not D146._subject_known(nb, name):
            return
        self._record_doubt(name, triple[1], twin)  # type: ignore[attr-defined]

    # loop138b's 137 upgrade step, for a twin this mixin built (matched by
    # exact text): (1) particle names re-run the upgrade on a surrogate twin
    # whose particles are title-cased, then the real name is put back;
    # (2) when the upgrade REFUSES the twin, the refusal gets the same reply
    # the one-word twin gets (the one-word teach action is refused by G91 /
    # 139b / 150 as an action -> clarify with that guard's text; the 137 step
    # instead returns the base's generic clarify).
    def _upgrade137(self, actions: list[dict], turn: str) -> list[dict]:
        out = super()._upgrade137(actions, turn)  # type: ignore[misc]
        if out is not actions:
            return out
        info = getattr(self, "_twin232", None)
        if not info or _norm(turn) != _norm(info[0]):
            return out
        if not isinstance(actions, list) or not actions or any(
                isinstance(a, dict) and a.get("act") in (
                    "teach", "correct", "ask", "answer", "forget2",
                    "person", "alias", "forget", "quote") for a in actions):
            return out  # base understood the turn: never touch it
        name = info[1]
        pturn = turn
        surrogate = None
        if has_particle232(name):
            surrogate = " ".join(t[:1].upper() + t[1:] if t in PARTICLES232
                                 else t for t in name.split())
            idx = turn.find(name + "'s ")
            if idx < 0:
                return out
            pturn = turn[:idx] + surrogate + turn[idx + len(name):]
            up = super()._upgrade137(actions, pturn)  # type: ignore[misc]
            if up is not actions and isinstance(up, list):
                fixed = []
                for a in up:
                    if isinstance(a, dict) and a.get("act") in (
                            "teach", "correct"):
                        if a.get("name") != surrogate:
                            return out  # unexpected shape: keep 138i's
                        a = dict(a, name=name)
                    fixed.append(a)
                return fixed
        parsed = F137.parse_possessive137(pturn)
        if parsed is None:
            return out
        if surrogate is not None:
            if parsed[0] != surrogate:
                return out
            parsed = (name,) + tuple(parsed[1:])
        act = F137.build_action137(parsed)
        msg = G91.screen_value(act.get("value", ""))
        if msg is not None:
            return [{"act": "clarify", "text": msg}]
        act = T140.sanitize_action(P129.sanitize_action(act))
        for guard in (V139B.guard_action, S150.guard_action):
            g = guard(act)
            if isinstance(g, dict) and g.get("act") == "clarify":
                return [g]
        return out


# ------------------------------------------------------------ ears + agent
class Loop232Ears(L138I.C174.ChainOf174Mixin, L138I.T165.Typo165Mixin,
                  Verb232Mixin,
                  L138I.S167B.ValueScreen167bMixin, L138I.V167D.Verb167dMixin,
                  L138I.V167.Verb167Mixin, L138I.N173B.Name173bMixin,
                  L138I.N173.Name173Mixin, L138I.M166.Me166Mixin,
                  L138I.B162.Plural162bMixin, L138I.Copula172Mixin,
                  L138I.Multival154eMixin, L138I.N171B.NameVal171BMixin,
                  L138I.N171.NameVal171Mixin, L138I.L138G.Loop138gEars):
    """Loop138iEars' exact base list with Verb232Mixin inserted where the
    verb mixins sit (after 174/165, before the 167b screen)."""

    name = "loop232-fullname"


DROP_NOTE232 = "(I dropped my earlier question.) "


class Loop232AgentLoop(L138I.Loop138iAgentLoop):
    """Loop138iAgentLoop + one parity step for 232 twins.

    A one-word verb twin reaches the notebook through Listening.hear (the M1
    line path), which first drops any pending yes/no question with the note
    "(I dropped my earlier question.) ". A multi-word twin is a structured
    137 action that calls Listening._teach directly and so kept the stale
    question alive (a later "yes" applied it). For structured teach/correct
    actions tagged v232 only: the pending question is dropped the same way
    and the same note is put in front of the reply; if the action never
    reached the doorway (a loop guard refused it), the pending question is
    restored untouched, as on the line path.
    """

    def _act(self, action: dict) -> dict:  # type: ignore[override]
        lis = getattr(self, "listening", None)
        if (isinstance(action, dict) and action.get("v232")
                and action.get("structured")
                and action.get("act") in ("teach", "correct")
                and lis is not None and lis.pending is not None):
            old = lis.pending
            lis.pending = None
            rec = super()._act(action)
            if isinstance(rec, dict) and rec.get("structured") is not None \
                    and isinstance(rec.get("text"), str):
                return dict(rec, text=DROP_NOTE232 + rec["text"])
            if lis.pending is None:
                lis.pending = old
            return rec
        return super()._act(action)


DEFAULT_CONFIG232: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG232["ears"]["stand_in"] = (
    L138I.DEFAULT_CONFIG138I["ears"]["stand_in"]
    + "; 232 multi-word verb subjects (Verb232Mixin beside the verb mixins)")
DEFAULT_CONFIG232["daemon"]["module"] = "Loop232Daemon (this file)"


def build_agent232(cfg: dict | None = None) -> Loop232AgentLoop:
    """build_agent138i with only the inner ears class swapped."""
    install_srcguard228()
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG232, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L138I.L90.ChainEars(cfg)
    mouth = L138I.L167E.Label167eMouth(L138I.L138b.Loop138bMouth())
    reasoner = L138I.L138d.Reasoner138d()
    sleeper = L138I.HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop232Ears(Loop96Ears(chain))
    loop = Loop232AgentLoop(
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
    loop.notes.append("loop232: loop138i + Verb232Mixin (multi-word verb "
                      "subjects)")
    return loop


class Loop232Daemon(SrcGuardMixin228, L138I.Loop138iDaemon):
    """Loop138iDaemon shape with the 232 agent inside."""

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
        self.loop = build_agent232(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L138I.D108.boot_reconcile(self)
        self.settle = L138I.D141.SettleGate141(grace_s=grace_s)


def run_daemon232(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop232Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 232 full-name verbs")
    parser.add_argument("--config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    cfg = copy.deepcopy(DEFAULT_CONFIG232)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon232(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        if not args.state_dir:
            parser.error("--once needs --state-dir (never the repo notebook)")
        cfg["state_dir"] = args.state_dir
        loop = build_agent232(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
