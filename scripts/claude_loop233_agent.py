#!/usr/bin/env python3
"""Experiment 233 -- POLITE NEGATIVE QUESTIONS (Opus).

Problem (verified on loop223): "Can't you tell me where Kim lives?",
"Don't you know who Kim's boss is?", "Won't you tell me Kim's city?" are
ordinary polite requests, but the exp-148 question screen sees the "n't"
and answers with the negation clarify even when the fact is stored.

THE ONE CHANGE (loop223 subclass; no earlier file edited): a "?" turn that
STARTS with a polite negative frame addressed to the assistant

    Can't / Cannot / Couldn't / Won't / Wouldn't / Don't  you
    | Do you not
    [please | just]  (tell me | know | remind me | say)  CONTENT ?

is rewritten to the plain question CONTENT contains, in the form the base
already reads, and that plain question is passed to the unchanged loop223
turn() -- i.e. it is processed exactly as if the user had typed the plain
question. Rewrites (CONTENT -> plain):

    WH SUBJ is/are/was/were TAIL   -> "WH is SUBJ TAIL?"   (who Kim's boss is)
    WH SUBJ can/will/.. TAIL       -> "WH can SUBJ TAIL?"
    WH SUBJ verb-s TAIL            -> "WH does SUBJ verb TAIL?" (where Kim lives)
    WH I/you/we/they verb TAIL     -> "WH do SUBJ verb TAIL?"
    WH is/does/... REST            -> "WH is REST?"  (already direct order)
    if/whether SUBJ is TAIL        -> "Is SUBJ TAIL?"
    if/whether SUBJ verb-s TAIL    -> "Does SUBJ verb TAIL?"
    Name's REL                     -> "What is Name's REL?"   (Kim's city)

WH may carry lowercase words before the subject ("which city Kim lives
in" -> "Which city does Kim live in?"). The subject starts at the first
capitalised word or I/you/my/your/we/they/our/their.

Guards: the rewrite applies only if (a) the frame matches at the start,
(b) CONTENT parses under one of the rules above, and (c) the rewritten
question contains NO negation word (the sealed 148 neg triggers not /
never / n't / no one / nobody / none, plus cannot / no / nothing /
nowhere / neither / nor), with taught notebook names exempt exactly as
the screen exempts them. Anything else -- true negations ("Where doesn't
Kim live?"), negated statements, frames around a negated question, or
content that does not parse -- calls the loop223 turn() with the original
text, byte-identical to today. Questions never write: the rewritten turn
always ends in "?" and follows the base question path.

Daemon launch (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop233_agent.py --daemon --dir DIR \\
    --config artifacts/claude-polite233-20260922/loop233-config.json
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

import fable_loop223_agent as L223  # noqa: E402 (wrapped base, read-only)
import fable_screen148_mixin as S148  # noqa: E402 (sealed neg list)

L138I = L223.L138I
_BUILD223 = L223.build_agent223  # original, captured before any patch

_APOS = "['’]"
_FRAME_RE = re.compile(
    r"^\s*(?:(?:oh|so|well|hey|um|okay|ok)\s*,?\s+)?"
    r"(?:(?:can" + _APOS + r"?t|cannot|couldn" + _APOS + r"?t|won" + _APOS
    + r"?t|wouldn" + _APOS + r"?t|don" + _APOS + r"?t)\s+you"
    r"|do\s+you\s+not)"
    r"\s+(?:(?:please|just)\s+)?"
    r"(?:tell\s+me|know|remind\s+me|say)\b\s*,?\s*(?P<content>.*)$",
    re.IGNORECASE)

_WH = {"where", "who", "what", "which", "whom", "whose", "when", "how"}
_BE = {"is", "are", "was", "were"}
_MODAL = {"can", "could", "will", "would", "should", "may", "might",
          "must"}
_AUX_DIRECT = _BE | _MODAL | {"does", "do", "did", "has", "have", "had",
                              "am"}
_PRON_SUBJ = {"i", "you", "we", "they"}
_SUBJ_START_LOWER = {"i", "you", "my", "your", "we", "they", "our",
                     "their"}
_CONTRACT = [(re.compile(r"\b(who|what|where|when|how|which)" + _APOS
                         + r"s\b", re.IGNORECASE), r"\1 is")]
_EXTRA_NEG_RE = re.compile(
    r"\b(cannot|no|nothing|nowhere|neither|nor|nobody|none|never|not)\b",
    re.IGNORECASE)
_TRAIL_PLEASE_RE = re.compile(r"\s*,?\s*(?:please|for me)\s*$",
                              re.IGNORECASE)


def _lemma(verb: str) -> str:
    v = verb.lower()
    irregular = {"has": "have", "does": "do", "goes": "go", "is": "be"}
    if v in irregular:
        return irregular[v]
    if v.endswith("ies") and len(v) > 4:
        return v[:-3] + "y"
    for suf in ("ches", "shes", "sses", "xes", "zes", "oes"):
        if v.endswith(suf):
            return v[:-2]
    return v[:-1]


def _is_subj_start(tok: str) -> bool:
    return tok[:1].isupper() or tok.lower() in _SUBJ_START_LOWER


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _subject_end(toks: list[str], s: int) -> int:
    """Index after the subject span starting at s (names + 's chains)."""
    i = s
    first = toks[i].lower()
    i += 1
    if first in {"my", "your", "our", "their"}:
        i += 1  # possessive determiner + its noun
    else:
        while i < len(toks) and toks[i][:1].isupper():
            i += 1  # multi-word capitalised name
    while i <= len(toks) and re.search(_APOS + r"s$", toks[i - 1]) \
            and i < len(toks):
        i += 1  # "Kim's boss", "Kim's boss's city"
    return i


def _rewrite_content(content: str) -> str | None:
    c = content.strip()
    for rx, rep in _CONTRACT:
        c = rx.sub(rep, c)
    c = re.sub(r"[?.!\s]+$", "", c)
    c = _TRAIL_PLEASE_RE.sub("", c)
    c = re.sub(r"[?.!,\s]+$", "", c)
    toks = c.split()
    if not toks:
        return None
    w0 = toks[0].lower()
    if w0 in _WH:
        if len(toks) >= 2 and toks[1].lower() in _AUX_DIRECT:
            return _cap(" ".join(toks)) + "?"
        s = next((i for i in range(1, len(toks))
                  if _is_subj_start(toks[i])), None)
        if s is None:
            return None
        whp = toks[:s]
        if any(t.lower() in _AUX_DIRECT for t in whp[1:]):
            return None
        b = next((i for i in range(s + 1, len(toks))
                  if toks[i].lower() in _BE), None)
        if b is not None:
            subj, tail = toks[s:b], toks[b + 1:]
            return _cap(" ".join(whp + [toks[b].lower()] + subj + tail)) + "?"
        e = _subject_end(toks, s)
        if e >= len(toks):
            return None
        subj, verb, tail = toks[s:e], toks[e], toks[e + 1:]
        vl = verb.lower()
        if vl in _MODAL:
            return _cap(" ".join(whp + [vl] + subj + tail)) + "?"
        if len(subj) == 1 and subj[0].lower() in _PRON_SUBJ:
            if not verb.isalpha() or not verb.islower():
                return None
            return _cap(" ".join(whp + ["do"] + subj + [vl] + tail)) + "?"
        if verb.isalpha() and verb.islower() and vl.endswith("s") \
                and not vl.endswith("ss"):
            return _cap(" ".join(whp + ["does"] + subj + [_lemma(vl)]
                                 + tail)) + "?"
        return None
    if w0 in {"if", "whether"} and len(toks) >= 3:
        s = 1
        if not _is_subj_start(toks[s]):
            return None
        b = next((i for i in range(s + 1, len(toks))
                  if toks[i].lower() in _BE), None)
        e = _subject_end(toks, s)
        if b is not None and b == e:
            return _cap(" ".join([toks[b].lower()] + toks[s:b]
                                 + toks[b + 1:])) + "?"
        if e < len(toks):
            verb = toks[e]
            vl = verb.lower()
            if verb.isalpha() and verb.islower() and vl.endswith("s") \
                    and not vl.endswith("ss"):
                return _cap(" ".join(["does"] + toks[s:e] + [_lemma(vl)]
                                     + toks[e + 1:])) + "?"
        return None
    # Bare possessive noun phrase: "Kim's city", "Kim's boss's city".
    if toks[0][:1].isupper() and any(re.search(_APOS + r"s$", t)
                                     for t in toks[:-1]):
        e = _subject_end(toks, 0)
        if e == len(toks) and not re.search(_APOS + r"s$", toks[-1]):
            if not any(t.lower() in _AUX_DIRECT for t in toks):
                return "What is " + " ".join(toks) + "?"
    return None


def _has_negation(question: str, known: list[str]) -> bool:
    try:
        if any(kind == "neg" for kind, _m in S148.trigger_spans(question,
                                                                known)):
            return True
    except Exception:  # noqa: BLE001 -- fail safe: treat as negated
        return True
    q = question
    for name in sorted({str(k) for k in known if str(k).strip()},
                       key=len, reverse=True):
        q = re.sub(re.escape(name), " ", q, flags=re.IGNORECASE)
    return _EXTRA_NEG_RE.search(q) is not None


def polite_rewrite(text: str, known: list[str] | None = None) -> str | None:
    """Plain question for a polite negative frame, else None."""
    t = " ".join(str(text).split())
    if not t.endswith("?"):
        return None
    m = _FRAME_RE.match(t)
    if m is None:
        return None
    out = _rewrite_content(m.group("content"))
    if out is None:
        return None
    if _has_negation(out, list(known or [])):
        return None
    return out


def _known_names(nb) -> list[str]:
    if nb is None:
        return []
    try:
        triples = L138I.L90.notebook_triples(nb)
    except Exception:  # noqa: BLE001
        return []
    known: list[str] = []
    for subj, _rel, val in triples:
        known.append(str(subj))
        known.append(str(val))
    return known


class Loop233AgentLoop(L223.Loop223AgentLoop):
    """Loop223AgentLoop + the polite-negative rewrite at turn() entry."""

    def turn(self, text: str) -> list[str]:  # type: ignore[override]
        try:
            plain = polite_rewrite(text, _known_names(getattr(self, "nb",
                                                              None)))
        except Exception:  # noqa: BLE001 -- never break the base path
            plain = None
        if plain is None:
            return super().turn(text)
        log = getattr(self, "polite233_log", None)
        if log is None:
            log = self.polite233_log = []
        log.append({"heard": str(text), "plain": plain})
        return super().turn(plain)


DEFAULT_CONFIG233: dict = copy.deepcopy(L223.DEFAULT_CONFIG223)
DEFAULT_CONFIG233["ears"]["stand_in"] = (
    "Loop223Ears (unchanged) behind Loop233AgentLoop.turn: a '?' turn "
    "starting with a polite negative frame (can't/cannot/couldn't/won't/"
    "wouldn't/don't you, do you not + tell me/know/remind me/say) is "
    "rewritten to its plain embedded question when that question has no "
    "negation word; else the 223 path byte-identical")
DEFAULT_CONFIG233["daemon"]["module"] = "Loop233Daemon (this file)"


def build_agent233(cfg: dict | None = None) -> Loop233AgentLoop:
    """loop223 build with the loop class swapped for Loop233AgentLoop."""
    real = L223.Loop223AgentLoop
    L223.Loop223AgentLoop = Loop233AgentLoop  # type: ignore[misc]
    try:
        loop = _BUILD223(dict(DEFAULT_CONFIG233, **(cfg or {})))
    finally:
        L223.Loop223AgentLoop = real  # type: ignore[misc]
    assert isinstance(loop, Loop233AgentLoop)
    loop.polite233_log = []
    loop.notes.append("loop233: loop223 + polite-negative rewrite at turn() "
                      "entry (frame + plain embedded question, no other "
                      "negation word)")
    return loop


class Loop233Daemon(L223.Loop223Daemon):
    """Loop223Daemon shape with the 233 agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = L138I.D141.SETTLE_GRACE_S) -> None:
        real = L223.build_agent223
        L223.build_agent223 = build_agent233  # type: ignore[assignment]
        try:
            super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                             sleep_threshold=sleep_threshold,
                             grace_s=grace_s)
        finally:
            L223.build_agent223 = real  # type: ignore[assignment]


def run_daemon233(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop233Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 233 polite loop")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--rewrite", default=None,
                        help="print the polite rewrite of TEXT and exit")
    args = parser.parse_args(argv)

    if args.rewrite is not None:
        print(polite_rewrite(args.rewrite))
        return 0
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG233)
        out["thinker"]["module"] = L138I.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG233)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon233(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent233(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
