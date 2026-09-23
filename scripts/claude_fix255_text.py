#!/usr/bin/env python3
"""Exp 255 -- fixed-reply text pass (text only, one outermost layer).

rewrite255(reply) takes ONE whole reply line and, if it is exactly one of
the fixed-reply templates below (a full-string regex match, never a
fragment of free text), returns the new text and the template id.
Anything that matches no template is returned unchanged (same object).

Rules for every rewrite (brief 255):
  - meaning never changes: a decline stays a decline, a confirmation
    stays a confirmation, and every fact, name and value named in the old
    text is named in the new text;
  - the frozen-scorer anchors (241 PASSMARKS s1) that the old text matched
    are kept where a frozen suite can see the template (checked by the
    suites in the pilot; no scorer is changed);
  - no routing, no reading, no writing: this module never touches the
    notebook and the loop wrapper only rewrites returned reply strings.

Number words: counts 0-9 are words, 10 and up are digits (style sheet v2
rule 3); a zero count is said as "no ..." / "none" / "not ... yet".
The user's own entity is stored under the key USER; inside the templates
that echo stored facts, "USER's X" is said "your X" and a bare "USER" is
said "you" (brief item 2).

New file only; imports nothing from the agent stack.
"""

from __future__ import annotations

import re
from typing import Callable

# ------------------------------------------------------------------ helpers
_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven",
          "eight", "nine"]


def num(n: int | str) -> str:
    """0-9 as words, 10 and up as digits."""
    k = int(n)
    return _WORDS[k] if 0 <= k <= 9 else str(k)


def cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def plural(n: int, one: str, many: str) -> str:
    return one if int(n) == 1 else many


def user_np(s: str) -> str:
    """Stored-fact display with the user's entity said as you/your."""
    s = re.sub(r"(?<![\w'])USER's\b", "your", s)
    s = re.sub(r"(?<![\w'])USER\b", "you", s)
    return s


def sentence_start(s: str) -> str:
    """Capitalise a leading your/you produced by user_np."""
    if s.startswith("your ") or s.startswith("you "):
        return cap(s)
    return s


def join_and(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def end_punct(s: str) -> str:
    s = s.rstrip()
    return s if s.endswith((".", "?", "!")) else s + "."


def quote(s: str) -> str:
    """User words in double quotes, first letter capitalised, one end mark
    inside the quotes."""
    s = " ".join(str(s).split())
    s = s.strip('"')
    return '"' + end_punct(cap(s)) + '"'


# -------------------------------------------------------- 1. the declines
Q1_OLD = "I don't know that yet — you haven't told me."
Q1_NEW = "I don't know that yet. You haven't told me."
Q2_OLD = "I didn't understand that question — could you say it another way?"
Q2_NEW = ("I don't know that. I may have misread your question, so could "
          "you say it another way?")
S1_OLD = ("I didn't understand that well enough to save it — could you say "
          "it another way?")
S1_NEW = ("I didn't understand that well enough to save it. I may have "
          "misread it, so could you say it another way?")
GLUE_OLD = ("I do not know that from what you taught me. I have no record of "
            "it, so I will not guess. I didn't understand that, I don't know "
            "— could you say it another way?")
GLUE_NEW = ("I don't know that, and I have no record of it. I may have "
            "misread your question, so could you say it another way?")
# 188 statement fallback (QUESTION_NO_QMARK)
F188_OLD = ("I couldn't save that as a fact. I don't know that shape yet. "
            "Could you say it another way, like \"Kim's boss is Lee.\"")
F188_NEW = ("I couldn't save that as a fact. I don't know that kind of "
            "sentence yet. Could you say it another way? For example: "
            "\"Kim's boss is Lee.\"")
# 148 screens (DOUBLE_DASH)
NEG_OLD = ("I didn't understand that. I only know current facts and I can't "
           "do 'not' -- could you say it without that part?")
NEG_NEW = ("I didn't understand that. I only know current facts, and I "
           "can't handle 'not' yet. Could you say it without that part?")
TIME_OLD = ("I didn't understand that. I only know current facts, not years "
            "or 'as of' -- could you say it without that part?")
TIME_NEW = ("I didn't understand that. I only know current facts, not years "
            "or 'as of' dates. Could you say it without that part?")
# earsguard91 / fix150 split clarify
SPLIT_OLD = "I can take one fact at a time — could you split that?"
SPLIT_NEW = "I can take one fact at a time. Could you split that up?"
# loop102 unreadable message (DOUBLE_DASH)
UNREAD_OLD = "I couldn't read that message -- please send it as plain text."
UNREAD_NEW = "I couldn't read that message. Please send it as plain text."
# fable_agent_loop fixed clarifies
LIKE_OLD = 'Please say it like "Mira\'s city is Lisbon.".'
LIKE_NEW = 'Please say it like this: "Mira\'s city is Lisbon."'
PICK_OLD = "Please answer with: pick <one of the IDs I listed>."
PICK_NEW = ('Please answer with "pick" and one of the IDs I listed.')
WEB_OLD = "That write is not allowed from web."
WEB_NEW = "That write is not allowed from the web."
# 138c self fallback (Oxford comma)
C138_OLD = ("I do not understand that question. Ask me about what I know, "
            "where it came from, or what I am doing.")
C138_NEW = ("I do not understand that question. Ask me about what I know, "
            "where it came from or what I am doing.")

# -------------------------------------------------------- 4. the greeting
GREET_OLD = ('Hi! Teach me like "Tom\'s boss is Ann." Ask me like "Who is '
             'Tom\'s boss?"')
GREET_NEW = ("Hi! I'm Premonition. You can teach me a fact, for example: "
             "\"Tom's boss is Ann.\" Then you can ask me about it, for "
             "example: \"Who is Tom's boss?\"")

# ----------------------------------------------- plain-software texts (187)
SOFT_OLD = "a notebook, a lookup loop, and fixed rules"
SOFT_NEW = "a notebook, a lookup loop and fixed rules"
S187_MAKER_OLD = ("Nobody taught me who made me, so I do not know it. I am "
                  "plain software you are teaching: " + SOFT_OLD + ".")
S187_WHAT_OLD = ("I am plain software you are teaching: " + SOFT_OLD + ". I "
                 "can only tell you what you taught me.")
S187_NAME_OLD = ("You never gave me a name, so I do not have one. I am plain "
                 "software you are teaching: " + SOFT_OLD + ".")
FEEL_OLD = ("I do not have feelings. I am plain software: " + SOFT_OLD + ".")

# ---------------------------------------------- capability sheets (self99)
CAN_OLD = ("I can: save what you teach me in my notebook; answer questions "
           "from my notes, following one or two steps; correct a fact or "
           "forget one when you ask; say I do not know instead of guessing; "
           "tell you where each fact came from; hold web text in quarantine "
           "without believing it.")
CAN_NEW = ("I can save what you teach me in my notebook. I can answer "
           "questions from my notes, following one or two steps. I can "
           "correct a fact or forget one when you ask. I can say I do not "
           "know instead of guessing. I can tell you where each fact came "
           "from. I can hold web text in quarantine without believing it.")
CANNOT_OLD = ("I cannot: feel feelings or have favourites or opinions; guess, "
              "predict the future, or explain why things are so; believe the "
              "web on my own; remember anything nobody taught me; know "
              "anything from outside our turns, like yesterday; dream.")
CANNOT_NEW = ("I cannot feel feelings or have favourites or opinions. I "
              "cannot guess, predict the future or explain why things are "
              "so. I cannot believe the web on my own. I cannot remember "
              "anything nobody taught me. I cannot know anything from "
              "outside our turns, like yesterday. I cannot dream.")
AGE_OLD = "You never taught me their age, so I do not know it."
AGE_NEW = "You never taught me that person's age, so I do not know it."

# -------------------------------------------------- 226 source questions
SRC_THAT_OLD = ('I\'m not sure what "that" means — I haven\'t just told you '
                'a fact.')
SRC_THAT_NEW = ('I\'m not sure what "that" means. I haven\'t just told you '
                'a fact.')
SRC_NOTRACK_OLD = ("I can't say where that came from — I didn't keep track of "
                   "which notes that reply used, so I won't guess.")
SRC_NOTRACK_NEW = ("I can't say where that came from. I didn't keep track of "
                   "which notes that reply used, so I won't guess.")

# ------------------------------------------- 5/8. pretend echo (137d say)
SAY_BARE_OLD = "(I'm treating that as pretend, so I won't save it.)"
SAY_BARE_NEW = "I'm treating that as pretend, so I won't save it."

# ----------------------------------------------------- mode names (item 3)
MODE_NEW = {
    "LISTENING": "Right now I'm listening, ready for your next message.",
    "THINKING": "Right now I'm thinking, ready for your next message.",
    "SLEEP": "Right now I'm sleeping, ready for your next message.",
    "SLEEPING": "Right now I'm sleeping, ready for your next message.",
    "WORK": "Right now I'm working, ready for your next message.",
    "WORKING": "Right now I'm working, ready for your next message.",
}
IDLE_THINKING_OLD = ("Right now I am idle, in THINKING mode. I am waiting for "
                     "your next turn.")
IDLE_THINKING_NEW = ("Right now I'm idle and thinking, waiting for your next "
                     "message.")

# ------------------------------------------------------------ exact table
EXACT: dict[str, tuple[str, str]] = {
    Q1_OLD: ("T01_Q1", Q1_NEW),
    Q2_OLD: ("T02_Q2", Q2_NEW),
    S1_OLD: ("T03_S1", S1_NEW),
    GLUE_OLD: ("T04_GLUE", GLUE_NEW),
    F188_OLD: ("T05_F188", F188_NEW),
    NEG_OLD: ("T06_NEG148", NEG_NEW),
    TIME_OLD: ("T07_TIME148", TIME_NEW),
    SPLIT_OLD: ("T08_SPLIT", SPLIT_NEW),
    UNREAD_OLD: ("T09_UNREAD", UNREAD_NEW),
    LIKE_OLD: ("T10_SAYLIKE", LIKE_NEW),
    PICK_OLD: ("T11_PICK", PICK_NEW),
    WEB_OLD: ("T12_WEBACTOR", WEB_NEW),
    C138_OLD: ("T13_SELFFALLBACK", C138_NEW),
    GREET_OLD: ("T14_GREETING", GREET_NEW),
    S187_MAKER_OLD: ("T15_187MAKER", S187_MAKER_OLD.replace(SOFT_OLD,
                                                            SOFT_NEW)),
    S187_WHAT_OLD: ("T16_187WHAT", S187_WHAT_OLD.replace(SOFT_OLD, SOFT_NEW)),
    S187_NAME_OLD: ("T17_187NAME", S187_NAME_OLD.replace(SOFT_OLD, SOFT_NEW)),
    FEEL_OLD: ("T18_FEELINGS", FEEL_OLD.replace(SOFT_OLD, SOFT_NEW)),
    CAN_OLD: ("T19_CAN", CAN_NEW),
    CANNOT_OLD: ("T20_CANNOT", CANNOT_NEW),
    AGE_OLD: ("T21_AGETHEIR", AGE_NEW),
    SRC_THAT_OLD: ("T22_SRCTHAT", SRC_THAT_NEW),
    SRC_NOTRACK_OLD: ("T23_SRCNOTRACK", SRC_NOTRACK_NEW),
    SAY_BARE_OLD: ("T24_SAYBARE", SAY_BARE_NEW),
    IDLE_THINKING_OLD: ("T25_IDLETHINKING", IDLE_THINKING_NEW),
    "No. I hold 0 web rows.": ("T26_WEB0", "No. I don't hold any web rows."),
    "No. I have slept 0 times.": ("T27_SLEPT0", "No. I haven't slept yet."),
    "You corrected: .": ("T28_CORRECTED0",
                         "You haven't corrected anything yet."),
    "I know 0 people: .": ("T29_PEOPLE0", "I know no one yet."),
}

# -------------------------------------------------------- pattern rules
Rule = tuple[str, "re.Pattern[str]", Callable[[re.Match], str]]
RULES: list[Rule] = []


def rule(tid: str, pattern: str):
    def deco(fn):
        RULES.append((tid, re.compile(pattern, re.S), fn))
        return fn
    return deco


# item 3: mode names
@rule("T30_MODE", r"Right now I am back in ([A-Z]+) mode, waiting for your "
                  r"next turn\.")
def _mode(m):
    return MODE_NEW.get(m.group(1), m.group(0))


# item 8: pretend echo "X. (I'm treating that as pretend, ...)"
@rule("T31_SAYECHO", r"(.+?)\s*\(I'm treating that as pretend, so I won't "
                     r"save it\.\)")
def _say(m):
    return ("Okay, I'll say it: " + quote(m.group(1)) + " I'm treating that "
            "as pretend, so I won't save it.")


# item 2 + item 7: first / last taught
@rule("T32_FIRST", r"The first thing you taught me was: (.+)\.")
def _first(m):
    return ("The first thing you taught me was that "
            + user_np(m.group(1)) + ".")


@rule("T33_LAST", r"The last thing you taught me was: (.+), in turn "
                  r"(\d+|\?)\.")
def _last(m):
    fact = user_np(m.group(1))
    if m.group(2) == "?":
        return "The last thing you taught me was that " + fact + "."
    return ("The last thing you taught me, in turn " + m.group(2)
            + ", was that " + fact + ".")


# item 2 + item 7: forgotten list
@rule("T34_FORGOT", r"I forgot: (.+)\. You asked me to forget it in turn "
                    r"(\d+|\?)\. The old row is kept but retired\.")
def _forgot(m):
    facts = [user_np(f) for f in m.group(1).split("; ")]
    body = join_and(["that " + f for f in facts])
    if m.group(2) == "?":
        when = ("You asked me to forget it earlier." if len(facts) == 1 else
                "You asked me to forget them earlier.")
    elif len(facts) == 1:
        when = f"You asked me to forget it in turn {m.group(2)}."
    else:
        when = (f"You asked me to forget the first of these in turn "
                f"{m.group(2)}.")
    keep = (" I still keep the old row, but it is retired." if len(facts) == 1
            else " I still keep the old rows, but they are retired.")
    return "I forgot " + body + ". " + when + keep


# item 2: corrections
@rule("T35_CORRECTED", r"You corrected: (.+)\.")
def _corrected(m):
    pairs = [user_np(p) for p in m.group(1).split("; ")]
    return "You corrected " + join_and(pairs) + "."


# 226 source replies that echo stored facts (item 2)
@rule("T36_SRCTOLD", r"You told me: (.*\bUSER\b.*)")
def _src_told(m):
    return "You told me that " + user_np(m.group(1)).rstrip()


@rule("T37_SRCPUT", r"I put together things you told me: (.*\bUSER\b.*)")
def _src_put(m):
    return "I put together things you told me: " + user_np(m.group(1))


# counts (style sheet rule 3/4)
@rule("T38_FACTS", r"I know (\d+) facts you taught me\. I also hold (\d+) web "
                   r"row, which I do not believe\.")
def _facts(m):
    n, w = int(m.group(1)), int(m.group(2))
    if n == 0:
        a = "You haven't taught me any facts yet."
    else:
        a = f"I know {num(n)} {plural(n, 'fact', 'facts')} you taught me."
    if w == 0:
        b = " I don't hold any web rows."
    else:
        b = (f" I also hold {num(w)} {plural(w, 'web row', 'web rows')}, "
             f"which I do not believe.")
    return a + b


@rule("T39_PEOPLE", r"I know (\d+) people: (.+)\.")
def _people(m):
    names = m.group(2).split(", ")
    n = int(m.group(1))
    if len(names) != n:
        return m.group(0)
    shown = (["you"] if "USER" in names else []) + [x for x in names
                                                    if x != "USER"]
    return (f"I know {num(n)} {plural(n, 'person', 'people')}: "
            f"{join_and(shown)}.")


@rule("T40_WEBN", r"Yes\. I hold (\d+) quarantined web row\. I filed it but I "
                  r"do not believe it\.")
def _webn(m):
    n = int(m.group(1))
    if n == 1:
        return ("Yes. I hold one quarantined web row. I filed it, but I do "
                "not believe it.")
    return (f"Yes. I hold {num(n)} quarantined web rows. I filed them, but I "
            f"do not believe them.")


@rule("T41_SLEPTN", r"Yes\. I have slept (\d+) times\.")
def _sleptn(m):
    n = int(m.group(1))
    return "Yes. I have slept once." if n == 1 else \
        f"Yes. I have slept {num(n)} times."


@rule("T42_SLEEPDERIVED", r"None\. (\d+) of my facts are sleep-derived\.")
def _sleepderived(m):
    n = int(m.group(1))
    if n == 0:
        return "None of my facts came from sleep."
    # the old text said "None." before a non-zero count; the count is the
    # answer, so the contradictory "None." is dropped
    if n >= 10:
        return f"Of my facts, {n} are sleep-derived."
    return (f"{cap(num(n))} of my facts {plural(n, 'is', 'are')} "
            f"sleep-derived.")


@rule("T43_TURNS", r"We have had (\d+) turns\.")
def _turns(m):
    n = int(m.group(1))
    return f"We have had {num(n)} {plural(n, 'turn', 'turns')}."


@rule("T44_ANSWERED", r"I have answered (\d+) questions\.")
def _answered(m):
    n = int(m.group(1))
    if n == 0:
        return "I haven't answered any questions yet."
    return f"I have answered {num(n)} {plural(n, 'question', 'questions')}."


@rule("T45_SAVEDN", r"I saved (\d+) times through our turns\.")
def _savedn(m):
    n = int(m.group(1))
    if n == 0:
        return "I haven't saved anything yet."
    if n == 1:
        return "I have saved a fact once so far."
    return f"I have saved facts {num(n)} times so far."


@rule("T46_REFUSED0", r"No\. I understood all (\d+) turns; I asked for "
                      r"clarification 0 times\.")
def _refused0(m):
    n = int(m.group(1))
    if n == 1:
        return ("No. I understood your only turn, and I never asked for "
                "clarification.")
    return (f"No. I understood all {num(n)} turns, and I never asked for "
            f"clarification.")


@rule("T47_REFUSEDN", r"Yes, (\d+) times I asked for clarification instead "
                      r"of saving\.")
def _refusedn(m):
    n = int(m.group(1))
    times = "once" if n == 1 else f"{num(n)} times"
    return f"Yes. I asked for clarification {times} instead of saving."


@rule("T48_GUESSES", r"(\d+) guesses are waiting for your approval\.")
def _guesses(m):
    n = int(m.group(1))
    if n == 0:
        return "No guesses are waiting for your approval."
    if n == 1:
        return "One guess is waiting for your approval."
    if n >= 10:
        return f"There are {n} guesses waiting for your approval."
    return f"{cap(num(n))} guesses are waiting for your approval."


@rule("T49_RULES", r"(\d+) of my facts came from rules\.")
def _rules(m):
    n = int(m.group(1))
    if n == 0:
        return "None of my facts came from rules."
    if n >= 10:
        return f"Of my facts, {n} came from rules."
    return f"{cap(num(n))} of my facts came from rules."


@rule("T50_BARECOUNT", r"(\d+)\.")
def _barecount(m):
    n = int(m.group(1))
    if n == 0:
        return "None."
    if n <= 9:
        return cap(num(n)) + "."
    return f"The count is {n}."


@rule("T51_DREAM", r"I do not dream\. I have slept (\d+) times and hold (\d+) "
                   r"sleep-derived facts\.")
def _dream(m):
    s, d = int(m.group(1)), int(m.group(2))
    if s == 0:
        a = "I haven't slept yet"
    elif s == 1:
        a = "I have slept once"
    else:
        a = f"I have slept {num(s)} times"
    if d == 0:
        b = "I hold no sleep-derived facts"
    else:
        b = f"I hold {num(d)} sleep-derived {plural(d, 'fact', 'facts')}"
    return f"I do not dream. {a}, and {b}."


@rule("T52_YESTERDAY", r"I have no record of yesterday\. My log starts with "
                       r"our first turn here and holds (\d+) turns\.")
def _yesterday(m):
    n = int(m.group(1))
    return ("I have no record of yesterday. My log starts with our first "
            f"turn here and holds {num(n)} {plural(n, 'turn', 'turns')}.")


@rule("T53_NOBODYELSE", r"Nobody besides you has spoken to me\. All (\d+) "
                        r"turns are yours\.")
def _nobodyelse(m):
    n = int(m.group(1))
    if n == 1:
        return "Nobody besides you has spoken to me. Our only turn is yours."
    if n == 2:
        return "Nobody besides you has spoken to me. Both turns are yours."
    return f"Nobody besides you has spoken to me. All {num(n)} turns are yours."


@rule("T54_C5NOTURN", r"You did, in turn \?\.")
def _c5noturn(m):
    return "You did."


@rule("T55_UNSURE", r"I am unsure about: (.+)\.")
def _unsure(m):
    bits = [user_np(b) for b in m.group(1).split("; ")]

    def _prop(mm):
        n = int(mm.group(1))
        return (f"{num(n)} proposed {plural(n, 'row', 'rows')} "
                f"{plural(n, 'that is', 'that are')} waiting")
    bits = [re.sub(r"\b(\d+) proposed rows waiting", _prop, b) for b in bits]
    return "I am unsure about " + join_and(bits) + "."


@rule("T56_DONTKNOWEX", r"I say I do not know instead of guessing\. Like when "
                        r"you asked: (.+)")
def _dontknowex(m):
    return ("I say I do not know instead of guessing, like when you asked "
            + quote(m.group(1)))


@rule("T57_JUSTBEFORE", r"Just before that, in turn (\d+), you asked: (.+?) "
                        r"I replied: (.+)")
def _justbefore(m):
    verb = "asked" if m.group(2).rstrip().endswith("?") else "said"
    return (f"Just before that, in turn {m.group(1)}, you {verb} "
            f"{quote(m.group(2))} I replied {quote(m.group(3))}")


@rule("T58_UPDATEDUSER", r"Updated: (USER's .+)")
def _updated_user(m):
    return "Updated: " + user_np(m.group(1))


@rule("T59_NOTSAVED", r"I could NOT save that: the notebook reported a "
                      r"problem \((.+)\)\.")
def _notsaved(m):
    return "I could not save that, because the notebook reported a problem."


@rule("T60_NEWUNSTORED", r"(You told me something new about .+ that I could "
                         r"not store\.) I can take one fact at a time — "
                         r"could you say it again as one fact\?")
def _newunstored(m):
    return (m.group(1).replace("USER's ", "your ") +
            " I can take one fact at a time. Could you say it again as one "
            "fact?")


PREFIX_DROPPED = "(I dropped my earlier question.) "


def rewrite255(reply: str) -> tuple[str, str | None]:
    """(new text, template id) for one whole reply line; (reply, None) when
    the line is not a fixed template."""
    if not isinstance(reply, str):
        return reply, None
    if reply.startswith(PREFIX_DROPPED):
        rest, tid = rewrite255(reply[len(PREFIX_DROPPED):])
        if tid is None:
            return reply, None
        return PREFIX_DROPPED + rest, tid
    hit = EXACT.get(reply)
    if hit is not None:
        return hit[1], hit[0]
    for tid, pat, fn in RULES:
        m = pat.fullmatch(reply)
        if m is not None:
            new = fn(m)
            if new != reply:
                return new, tid
            return reply, None
    return reply, None


TEMPLATE_IDS = sorted({v[0] for v in EXACT.values()} | {r[0] for r in RULES})
