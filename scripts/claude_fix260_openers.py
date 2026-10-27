#!/usr/bin/env python3
"""Exp 260 -- THE ONE CHANGE: openers and greetings are never part of a fact.

Base: 138m (scripts/claude_loop138m_agent.py). New file only.

DIAGNOSIS (why the existing lists do not fire on 138m; details in
design/v3/30-modes/260-openers-opus.md):
  - 137b's DISCOURSE137B lives only in Loop137bEars (137b/c/d/e line). That
    ears class was never merged into the 138 line, so 138m never runs it.
  - 150's FILLER_OPENERS runs inside 138b's ears (S150.guard_actions) BEFORE
    138b's fix137 possessive upgrade. The upgrade builds its teach later and
    calls screen_subject_150 only for the verdict, throwing the cleaned name
    away, so "So, Pell's boss is Rhoda." stores the subject "So, Pell".
    "please" is not in the 150 list at all ("Please, Kestrel" stores).
  - 157's FILLER157 strip (Filler157Mixin) sits low in the ears MRO (inside
    the 138f level). Its re-parse of the remainder only reaches the layers
    BELOW it, so verb teaches (167/167d), copula teaches (172), 158 question
    forms and every loop-level handler never see the remainder. It also
    strips only one filler, has no "please"/"hi", and does not treat "!".
  - Greeting + question: no layer strips "Hi!"; 156b small talk only fires
    when every token is small-talk vocabulary ("hello there" has "there").

THE RULE (outermost, on the whole built turn):
  1. One closed list (below), fixed before any panel read.
  2. A turn that starts with listed openers (at most 2; a greeting may carry
     up to two of "there"/"again"/"Premonition") is tried as the rest:
       a. the ORIGINAL turn runs first (write guard on). If it wrote, keep
          it (a clean write; the guard stops opener-comma subjects).
       b. if the opener had no punctuation after it and the head did not
          clarify, keep the original (can't tell an opener from a title).
       c. otherwise the state is restored and the REST runs as if typed
          alone. If the head clarifies on the rest, the state after (a) is
          restored and the original reply stands. If the original reply
          was not a clarify and already contains the rest's reply ("Hi!
          I'm here ..." vs "I'm here ..."), the original stands. Else the
          rest's reply is used.
     Soft mode (no punctuation, next word capitalised, and the opener is a
     greeting or 2+ capitalised words follow: "Hey Jude", "So Long Summer",
     "Hey Pell"): the original is kept whenever the head acts on it (can't
     tell a title/vocative). Hard mode (every other opener turn): during
     the original run, a teach/correct whose subject starts with this
     opener ("So Pell", "Um Pell") is turned into the ears' clarify, so
     step (c) runs the rest instead ("So Pell's boss is Rhoda." stores
     Pell). Words are kept as typed; only a closed list of
     lowercase function words at the start of the rest ("is", "where",
     "my", ...) gets a capital first letter (never a name).
  3. A bare greeting gets exactly the head's reply to "Hello." (the turn is
     run as "Hello." unless the head already gives that reply to it).
  4. Write guard: no teach/correct may store a subject that starts with a
     listed opener followed by a comma (always), or -- during the original
     run of a hard-mode opener turn -- with that turn's opener followed by
     any separator ("So Pell", "Hi. Tom"). At the inner ears the action
     becomes the ears' own clarify (so the head gives its own save-failure
     reply), and again at _act just before the write.
  5. Questions ("?" turns): in a rest run only asks/clarify/namecheck/unsure
     pass _act, so a question never writes through the rest path.
  Words that are also names (Will, Hope, Joy, May, Art, Bill, Mark, Pat,
  Grace, Sunny, Faith, Rose) are NOT listed. Pretend markers ("suppose",
  "imagine", "say") and "no"/"wait"/"sorry" are in the write-guard list
  only: stripping "Suppose" would turn pretend into a fact. "Actually" is
  strippable, but the original runs first, so the head's own correction
  reading of "Actually, ..." always wins when it acts.

State: a rest run that is not used is undone by restoring every plain
attribute (lists, dicts, numbers, strings) of the loop and its helper
objects; the notebook is never written on that path (clarify = no write;
checked by the notebook event count, and a written rest run is always
kept).
"""

from __future__ import annotations

import copy
import re

# ------------------------------------------------------------ closed lists
# Greeting words (bare-greeting rule and openers).
GREETINGS260 = (
    "good morning", "good afternoon", "good evening",
    "hello", "hiya", "heya", "howdy", "hey", "hi",
)
# Words allowed after a greeting in a bare greeting / greeting opener.
GREET_TAIL260 = ("there", "again", "premonition")

# Openers that are stripped (union of DISCOURSE137B and FILLER_OPENERS
# minus the correction/pretend markers, plus greetings, multi-word openers
# and hesitation words). Longest first at match time.
STRIP_OPENERS260 = (
    # multi-word
    "oh by the way", "by the way", "just so you know", "for the record",
    "for your information", "one more thing", "fun fact", "quick one",
    "quick question", "heads up", "guess what", "you know what",
    "oh and", "oh also", "oh yeah", "oh right", "oh well", "oh so",
    "and also", "and so", "but also", "okay so", "ok so", "alright so",
    "all right", "so anyway", "so yeah", "well then", "just fyi",
    "my friend", "my neighbor", "my neighbour",
    # single words (DISCOURSE137B minus suppose/imagine/say)
    "so", "well", "oh", "also", "and", "but", "okay", "ok", "alright",
    "right", "please", "actually", "anyway", "anyways", "btw", "fyi", "listen", "look",
    "basically", "remember", "note", "honestly", "frankly",
    # hesitation
    "um", "umm", "uh", "uhh", "er", "erm", "hmm",
)
# Guard-only words: never stripped, but never allowed as "<word>," at the
# start of a stored subject either.
GUARD_ONLY260 = ("suppose", "imagine", "say", "no", "wait",
                 "sorry", "anyhow")


def _phrase_re(p: str) -> str:
    # words of a phrase may be joined by spaces and/or a comma ("oh, and")
    return r"[\s,]+".join(re.escape(w) for w in p.split())


_ALL_OPENERS = tuple(sorted(set(STRIP_OPENERS260) | set(GREETINGS260),
                            key=lambda s: (-len(s), s)))
_GREET_ALT = "|".join(_phrase_re(g) for g in
                      sorted(GREETINGS260, key=lambda s: (-len(s), s)))
_TAIL_ALT = "|".join(GREET_TAIL260)
# An opener: a listed phrase (a greeting may carry one tail word) followed
# by punctuation+space, a spaced dash, or plain space.
_OPENER_RE = re.compile(
    r"^(?P<op>(?:" + _GREET_ALT + r")(?:[\s,]+(?:" + _TAIL_ALT + r")){0,2}"
    r"(?=[\s,!.:\-–—]|$)|(?:"
    + "|".join(_phrase_re(p) for p in _ALL_OPENERS) + r"))"
    r"(?P<sep>[,!.:]+\s+|\s+[-–—]+\s+|\s+)",
    re.IGNORECASE)
_BARE_GREETING_RE = re.compile(
    r"^\s*(?:" + _GREET_ALT + r")(?:[\s,!.]+(?:" + _TAIL_ALT + r")){0,2}"
    r"\s*[!.,]*\s*$", re.IGNORECASE)
_GUARD_WORDS = tuple(sorted(set(_ALL_OPENERS) | set(GUARD_ONLY260),
                            key=lambda s: (-len(s), s)))
_JUNK_SUBJECT_RE = re.compile(
    r"^\s*(?:" + "|".join(_phrase_re(p) for p in _GUARD_WORDS) + r")"
    r"(?:[\s,]+(?:" + _TAIL_ALT + r")){0,2}\s*,", re.IGNORECASE)

MAX_STRIP260 = 2


def is_bare_greeting260(text: str) -> bool:
    return bool(_BARE_GREETING_RE.match(str(text)))


def _cap_run(tail: str) -> int:
    """Number of capitalised words at the start of tail ("Long Summer's
    author" -> 2, "Pell's boss" -> 1, "my name" -> 0)."""
    n = 0
    for w in tail.split():
        if w[:1].isupper():
            n += 1
            if re.search(r"['\u2019]s\W*$", w) or re.search(r"[,.!?:;]$", w):
                break
        else:
            break
    return n


def split_openers260(text: str):
    """text -> (rest, punct, first_op, mode) after at most 2 listed openers,
    else None.

    punct is True when the last stripped opener was followed by
    punctuation (",", "!", ".", ":" or a spaced dash). mode is "hard" or
    "soft" for the first opener:
      soft = no punctuation after it AND the next word is capitalised AND
             (it is a greeting, or 2+ capitalised words follow): "Hey Jude",
             "So Long Summer", "Hey Pell" -- can't tell a title/vocative from
             an opener, so the original is never overridden when it acts;
      hard = everything else: the original's teach/correct may not store a
             subject that starts with this opener (it becomes the ears'
             clarify), so "So Pell's boss is Rhoda." cannot store "So Pell".
    """
    rest = str(text).lstrip()
    n = 0
    punct = False
    first_op, mode = None, "hard"
    while n < MAX_STRIP260:
        m = _OPENER_RE.match(rest)
        if not m:
            break
        tail = rest[m.end():]
        if not tail.strip() or not re.search(r"[A-Za-z0-9]", tail):
            break
        sep_punct = bool(re.search(r"[,!.:\-\u2013\u2014]", m.group("sep")))
        op = m.group("op")
        if n == 0:
            first_op = op
            nxt_cap = tail.lstrip()[:1].isupper()
            greet = bool(re.match(r"^(?:" + _GREET_ALT + r")\b", op,
                                  re.IGNORECASE))
            if not sep_punct and nxt_cap and (greet or _cap_run(tail) >= 2):
                mode = "soft"
        punct = sep_punct
        rest = tail
        n += 1
    if n == 0:
        return None
    return rest.strip(), punct, first_op, mode


def prefix_re260(op: str):
    """Subjects that start with this opener (as typed) + a separator."""
    return re.compile(r"^\s*" + _phrase_re(" ".join(op.replace(",", " ")
                                                     .split()))
                      + r"[\s,!.:\-\u2013\u2014]+\S", re.IGNORECASE)


def is_junk_subject260(name) -> bool:
    """A subject that starts with a listed opener followed by a comma."""
    return bool(_JUNK_SUBJECT_RE.match(str(name or "")))


# ------------------------------------------------------------ clarify test
# Head replies that mean "I did not act on that" (clarify / decline glue).
CLARIFY_MARKS260 = (
    "didn't understand", "couldn't save that", "say it another way",
    "was that a question", "do not know that from what you taught me",
    "one fact at a time", "can only handle one-word names",
    "couldn't read that message",
)


def _norm_reply(reply_lines) -> str:
    return " ".join(" ".join(str(x) for x in (reply_lines or [])).split())


# Closed list of lowercase function words that start a rest and are never
# names: only these get a capital first letter (names are never re-cased).
RECASE_WORDS260 = (
    "is", "are", "was", "were", "does", "do", "did", "who", "whom", "whose",
    "what", "what's", "whats", "where", "where's", "when", "which", "how",
    "can", "could", "will", "would", "my", "your", "the", "a", "an", "tell",
    "forget", "i", "i'm", "please",
)


def recase_rest260(rest: str) -> str:
    parts = str(rest).split(None, 1)
    if parts and parts[0].lower() == parts[0] and \
            parts[0].strip("?,.!").lower() in RECASE_WORDS260:
        return rest[:1].upper() + rest[1:]
    return rest


def is_clarify_reply260(reply_lines) -> bool:
    text = " ".join(str(x) for x in (reply_lines or [])).lower()
    if not text.strip():
        return True
    return any(m in text for m in CLARIFY_MARKS260)


# ------------------------------------------------------------ state undo
_PLAIN = (type(None), bool, int, float, str, bytes, list, dict, tuple, set,
          frozenset)
_SKIP_TYPES = ("Notebook", "Path")


def _helpers(loop):
    """The loop and its helper objects (not the notebook), depth <= 3."""
    seen, out, todo = set(), [], [(loop, 0)]
    while todo:
        obj, depth = todo.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        out.append(obj)
        if depth >= 3:
            continue
        for v in list(vars(obj).values()):
            if isinstance(v, _PLAIN) or callable(v) and not hasattr(
                    v, "__dict__"):
                continue
            tn = type(v).__name__
            if any(s in tn for s in _SKIP_TYPES):
                continue
            mod = getattr(type(v), "__module__", "") or ""
            if not (mod.startswith("fable_") or mod.startswith("claude_")
                    or mod.startswith("sleep") or "agent" in mod):
                continue
            if hasattr(v, "__dict__"):
                todo.append((v, depth + 1))
    return out


def snapshot260(loop):
    snap = []
    for obj in _helpers(loop):
        attrs = {}
        for k, v in list(vars(obj).items()):
            if isinstance(v, _PLAIN):
                attrs[k] = (v, copy.deepcopy(v))
        snap.append((obj, attrs))
    return snap


def restore260(snap) -> None:
    for obj, attrs in snap:
        d = vars(obj)
        for k in [k for k, v in d.items()
                  if isinstance(v, _PLAIN) and k not in attrs]:
            del d[k]
        for k, (ref, saved) in attrs.items():
            if isinstance(ref, list):
                ref[:] = copy.deepcopy(saved)
            elif isinstance(ref, dict):
                ref.clear()
                ref.update(copy.deepcopy(saved))
            elif isinstance(ref, set):
                ref.clear()
                ref.update(copy.deepcopy(saved))
            d[k] = ref


def _nb_events(loop) -> int:
    nb = getattr(loop, "nb", None)
    for o in (nb, getattr(nb, "nb", None)):
        if o is not None and hasattr(o, "events"):
            try:
                return len(o.events)
            except TypeError:
                pass
    return -1


# ------------------------------------------------------------ the layer
CLARIFY_ACTION260 = {"act": "clarify",
                     "text": "I didn't understand that. Could you say it "
                             "another way?"}
QUESTION_OK_ACTS260 = ("ask", "clarify", "namecheck", "unsure")


def _junk_action(a, prefix=None) -> bool:
    if not (isinstance(a, dict) and a.get("act") in ("teach", "correct")):
        return False
    name = str(a.get("name") or "")
    return is_junk_subject260(name) or bool(prefix and prefix.match(name))


def install_openers260(loop):
    """Install the 260 layer on a built 138m loop (outermost, instance)."""
    inner_turn = loop.turn            # turn224c(turn224(class turn))
    loop.turn260_inner = inner_turn
    loop.openers260_log = []
    state = {"question_rest": False, "prefix": None}

    # write guard at the inner ears (the head then gives its own reply)
    ears = getattr(loop, "_inner138j_ears", None)
    if ears is not None:
        ears_hear = ears.hear

        def hear260(turn, _h=ears_hear):
            acts = _h(turn)
            if isinstance(acts, list) and any(
                    _junk_action(a, state["prefix"]) for a in acts):
                loop.openers260_log.append({"guard": "ears", "turn": turn})
                return [dict(CLARIFY_ACTION260)]
            return acts

        ears.hear = hear260

    # write guard at _act (braces), plus the question-rest write block
    class_act = loop._act

    def act260(action, _a=class_act):
        if _junk_action(action, state["prefix"]) or (
                state["question_rest"] and isinstance(action, dict)
                and action.get("act") not in QUESTION_OK_ACTS260):
            loop.openers260_log.append({"guard": "act",
                                        "act": action.get("act")})
            loop.counters["clarifications"] += 1
            return {"kind": "clarify", "text": CLARIFY_ACTION260["text"]}
        return _a(action)

    loop._act = act260

    def run_rest(rest, is_q):
        state["question_rest"] = is_q
        try:
            return inner_turn(rest)
        finally:
            state["question_rest"] = False

    def turn260(text: str) -> list[str]:
        t = str(text)
        if is_bare_greeting260(t):
            s0 = snapshot260(loop)
            r0 = inner_turn(t)
            if list(r0) == greeting_reply():
                return r0
            restore260(s0)
            loop.openers260_log.append({"bare": t})
            return inner_turn("Hello.")
        sp = split_openers260(t)
        if sp is None:
            return inner_turn(t)
        rest, punct, first_op, mode = sp
        rest = recase_rest260(rest)
        is_q = t.rstrip().endswith("?")
        # 1. the original turn, as the head hears it (write guard active;
        #    in hard mode also no subject starting with this opener)
        s0 = snapshot260(loop)
        e0 = _nb_events(loop)
        state["prefix"] = prefix_re260(first_op) if mode == "hard" else None
        try:
            r0 = inner_turn(t)
        finally:
            state["prefix"] = None
        if _nb_events(loop) != e0:
            return r0                       # a clean write: keep it
        r0_clarify = is_clarify_reply260(r0)
        if not r0_clarify and not punct:
            return r0                       # can't tell: don't strip
        # 2. the rest, as if typed alone
        s1 = snapshot260(loop)
        restore260(s0)
        r1 = run_rest(rest, is_q)
        wrote = _nb_events(loop) != e0
        if not wrote and is_clarify_reply260(r1):
            restore260(s1)
            return r0                       # rest not understood
        if (not wrote and not r0_clarify
                and _norm_reply(r1) in _norm_reply(r0)):
            restore260(s1)
            return r0                       # base already says it (+more)
        loop.openers260_log.append({"rest": rest, "punct": punct,
                                    "mode": mode})
        return r1

    cache = {}

    def greeting_reply():
        # the head's own reply to "Hello." (computed once, state undone)
        if "g" not in cache:
            s = snapshot260(loop)
            cache["g"] = list(inner_turn("Hello."))
            restore260(s)
        return cache["g"]

    turn260.__name__ = "turn260"
    loop.turn = turn260
    return loop
