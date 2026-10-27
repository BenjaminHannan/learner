#!/usr/bin/env python3
"""105 -- FIX the self-question router (one change) and test it on a panel
never seen during development.

Additive wrapper/subclass of scripts/fable_self99.py (imported read-only,
never edited). THE ONE CHANGE: exact-substring intent routing is replaced by
a scored router (route()). The per-intent ANSWER functions are untouched: the
router picks an intent id, and the answer is produced by the inherited
answer_self() fed the intent's canonical exp-99 question (which provably
triggers the same answer body as exp 99). New text introduced here: only the
normaliser, the keyword tables, the guards, and one honest-decline sentence.

Router stages (in order):
  1. normalise(): lowercase, expand contractions ("can't" -> "can not",
     "what're" -> "what are", "where'd" -> "where did", ...), fix "hw" ->
     "how", fold "can <you> not" -> "cannot", strip filler
     (so/um/umm/like/ok/okay/uh/oh), apply a small lemma map
     (taught/told/gave -> teach, folks -> people, ...), tokenise [a-z]+.
  2. QUESTION-TYPE GUARD (before any intent scoring):
     - "how many / how much / count / number of" may only route to COUNT
       intents (else HONEST_DECLINE);
     - "why / how do you decide / what happens when" may only route to
       PROCESS intents {C22,C23,C24,C25} or decline intents (else DECLINE);
     - belief-worded questions ("believe"/"belief") may only route to C7 or
       a decline (else DECLINE). No produced answer ever starts with
       "Yes"/"No" except the inherited yes/no-from-state answers
       (C6,C7,C8,C15,C21,C26) and never the decline sentence.
  3. keyword-set overlap scoring: score(intent) = sum of weights of matched
     keywords. A question token matches a keyword if equal, or (both length
     >= 3) edit distance <= 1 (typo tolerance: "teech"~"teach",
     "favourite"~"favorite").
  4. margin + threshold rule: the best intent routes only if
     best >= THRESH[intent] AND best - runner_up >= MARGIN (fixed 2);
     else HONEST_DECLINE ("I ... have no record ...", carries the frozen
     decline markers "I have no record" / "do not know").

Development/tuning data ONLY: exp 99's 40 canonical questions + exp 100's 80
blind questions (120 total). The exp-105 panel was never opened before the
freeze seal (see PASSMARKS.md).

Run (Mac CPU, offline; only AFTER PASSMARKS sealed + ledger P105.*):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_self105.py --devcheck
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_self99 as S99  # noqa: E402 (read-only; wrapped, never edited)

ART_SUBDIR = "fable-self105-20260921"

MARGIN = 2

HONEST_DECLINE = ("I do not know that from what you taught me. "
                  "I have no record of it, so I will not guess.")

CANONICAL = {q["id"]: q["text"] for q in S99.QUESTIONS}

# ------------------------------------------------------------ normalisation
FILLER = {"so", "um", "umm", "like", "ok", "okay", "uh", "oh", "well",
          "same"}
# STOP: dropped after the cannot-fold. No intent keyword is a bare negation
# ("cannot" is folded pre-tokenise), while "not" typo-collides ("not"~"now":
# "what do you do when you do NOT know" scored C16-now). Verified: no dev
# question routes via a "not" token.
STOP = FILLER | {"not"}

CONTRACTIONS = [
    ("what're", "what are"), ("where'd", "where did"), ("what's", "what is"),
    ("who's", "who is"), ("how's", "how is"), ("when's", "when is"),
    ("why's", "why is"), ("that's", "that is"), ("it's", "it is"),
    ("there's", "there is"), ("here's", "here is"), ("i'm", "i am"),
    ("you're", "you are"), ("we're", "we are"), ("they're", "they are"),
    ("i've", "i have"), ("you've", "you have"), ("we've", "we have"),
    ("they've", "they have"), ("i'll", "i will"), ("you'll", "you will"),
    ("i'd", "i would"), ("you'd", "you would"), ("let's", "let us"),
    ("can't", "can not"), ("don't", "do not"), ("doesn't", "does not"),
    ("didn't", "did not"), ("isn't", "is not"), ("aren't", "are not"),
    ("wasn't", "was not"), ("weren't", "were not"), ("haven't", "have not"),
    ("hasn't", "has not"), ("hadn't", "had not"), ("won't", "will not"),
    ("wouldn't", "would not"), ("couldn't", "could not"),
    ("shouldn't", "should not"), ("mustn't", "must not"),
]

LEMMA = {
    "taught": "teach", "told": "teach", "tell": "teach", "tells": "teach",
    "telling": "teach", "gave": "teach", "given": "teach", "give": "teach",
    "knows": "know", "known": "know", "knowing": "know",
    "forgot": "forget", "forgotten": "forget", "forgets": "forget",
    "remembers": "remember", "remembered": "remember",
    "remembering": "remember",
    "believes": "believe", "believed": "believe", "believing": "believe",
    "sleeps": "sleep", "slept": "sleep", "sleeping": "sleep",
    "dreams": "dream", "dreamed": "dream", "dreaming": "dream",
    "corrected": "correct",
    "correcting": "correct", "correction": "correct",
    "does": "do", "did": "do",
    "folks": "people", "folk": "people", "persons": "people",
    "person": "people",
    "facts": "fact", "things": "thing", "rows": "row", "guesses": "guess",
    "feelings": "feeling",
    "favourite": "favorite", "favourites": "favorite",
    "colour": "color", "colours": "color",
    "mothers": "mother",
    "lives": "live", "lived": "live", "living": "live",
    "says": "say", "said": "say", "saying": "say",
    "hears": "hear", "heard": "hear",
    "writes": "write", "written": "write", "wrote": "write",
    "saves": "save", "saved": "save",
    "answers": "answer", "answered": "answer",
    "refuses": "refuse", "refused": "refuse",
    "waits": "wait", "waiting": "wait",
    "comes": "come", "came": "come", "coming": "come",
    "goes": "go", "went": "go", "going": "go",
    "happens": "happen", "happened": "happen", "happening": "happen",
    "decides": "decide", "decided": "decide",
    "changes": "change", "changed": "change",
    "picks": "pick", "picked": "pick",
    "holds": "hold", "held": "hold",
    "files": "file", "filed": "file",
    "derives": "derive", "derived": "derive",
    "rules": "rule", "reasoning": "reason",
    "limits": "limit", "names": "name",
    "anybody": "anyone", "somebody": "anyone",
    "learned": "learn", "learning": "learn",
    "newest": "new", "latest": "recent",
    "forgetting": "forget", "turned": "turn",
}


def normalise(question: str) -> tuple[str, list[str]]:
    """Return (clean string for guard phrases, lemma tokens for scoring)."""
    s = " ".join(str(question).split()).lower()
    for old, new in CONTRACTIONS:
        s = re.sub(r"(?<!\w)" + re.escape(old) + r"(?!\w)", new, s)
    # generic clitic tails
    s = re.sub(r"n't\b", " not", s)
    s = re.sub(r"'re\b", " are", s)
    s = re.sub(r"'ve\b", " have", s)
    s = re.sub(r"'ll\b", " will", s)
    s = re.sub(r"'d\b", " would", s)
    s = re.sub(r"'m\b", " am", s)
    s = re.sub(r"'s\b", " is", s)
    s = re.sub(r"\bhw\b", "how", s)  # common typo seen in dev
    # fold "can <pronoun> not" into one negative token
    s = re.sub(r"\bcan\s+(you\s+|we\s+|i\s+)?not\b", r"cannot \1", s)
    toks = [t for t in re.findall(r"[a-z]+", s) if t not in STOP]
    toks = [LEMMA.get(t, t) for t in toks]
    return s, toks


def edit1(a: str, b: str) -> bool:
    """True if a == b or (len >= 3 both, same first letter) edit distance 1.

    The same-first-letter rule kills systematic false friends seen in dev
    ("have"~"save", "now"~"know"/"how", "year"~"hear", "old"~"hold",
    "yet"~"get") while keeping real typos ("teech"~"teach").
    """
    if a == b:
        return True
    if len(a) < 3 or len(b) < 3:
        return False
    if a[0] != b[0]:
        return False
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(1 for x, y in zip(a, b) if x != y) <= 1
    long, short = (a, b) if len(a) > len(b) else (b, a)
    for i in range(len(long)):
        if long[:i] + long[i + 1:] == short:
            return True
    return False


# ------------------------------------------------------- intent keyword sets
# Weights tuned ONLY on exp99-40 + exp100-80 (120 dev questions).
KEYWORDS: dict[str, dict[str, int]] = {
    "C1": {"fact": 2, "teach": 2, "know": 1, "still": 1,
           "thing": 1, "hold": 1, "active": 1, "actually": 1},
    "C2": {"people": 3, "count": 1, "know": 1, "notebook": 2,
           "total": 1, "name": 2},
    "C3": {"last": 3, "recent": 2, "teach": 2, "fact": 1, "thing": 1,
           "new": 1},
    "C4": {"first": 3, "ever": 1, "teach": 1, "fact": 2, "thing": 1,
           "oldest": 2},
    "C5": {"mira": 1, "paris": 1, "teach": 1, "who": 2, "hear": 1, "say": 1,
           "when": 1, "oslo": 1, "correct": 1, "live": 1},
    "C6": {"internet": 3, "online": 3, "web": 2, "row": 1, "file": 1,
           "pick": 1, "get": 1},
    "C7": {"believe": 2, "online": 2, "internet": 2, "read": 1, "web": 1,
           "trust": 1},
    "C8": {"sleep": 2, "yet": 2, "since": 1, "started": 1, "ever": 1},
    "C9": {"learn": 2, "while": 2, "sleep": 1, "new": 2, "pick": 1},
    "C10": {"come": 2, "sleep": 1, "dream": 2, "derive": 2, "fact": 1},
    "C11": {"forget": 4},
    "C12": {"forget": 2, "count": 2, "number": 2, "thing": 1,
            "stuff": 1},
    "C13": {"correct": 4, "along": 1, "way": 1, "thing": 1, "change": 1},
    "C14": {"correct": 2, "corrections": 3, "many": 1, "times": 2,
            "count": 2, "number": 2, "save": 1},
    "C15": {"sure": 3, "certain": 3, "confident": 2, "mira": 1, "paris": 1,
            "really": 1},
    "C16": {"doing": 2, "now": 2, "moment": 2, "currently": 2, "right": 1,
            "up": 1},
    "C17": {"before": 4, "just": 1, "previous": 2, "earlier": 2,
            "prior": 2, "doing": 1},
    "C18": {"turn": 2, "many": 1, "count": 1, "together": 1, "far": 1},
    "C19": {"answer": 3, "question": 2, "many": 1, "actually": 1},
    "C20": {"save": 3, "write": 2, "row": 1, "thing": 1},
    "C21": {"refuse": 3, "save": 1, "ever": 1, "say": 1},
    "C22": {"unsure": 5, "uncertain": 3, "unknown": 2, "missing": 1,
            "gap": 1, "know": 1},
    "C23": {"know": 1, "guess": 2, "instead": 1, "when": 2},
    "C24": {"can": 2, "do": 1, "able": 2, "anyway": 1, "capability": 2},
    "C25": {"cannot": 3, "limit": 2, "unable": 2},
    "C26": {"besides": 3, "anyone": 2, "else": 1, "teach": 1},
    "C27": {"source": 3, "web": 2, "row": 2, "come": 1, "quote": 1,
            "page": 1, "url": 1},
    "C28": {"guess": 3, "approval": 3, "approve": 2, "wait": 2},
    "C29": {"rule": 3, "reason": 2, "come": 1, "fact": 1},
    "C30": {"mother": 3, "live": 2, "city": 2, "where": 1, "mira": 1,
            "ana": 1, "porto": 1},
    "D1": {"favorite": 3, "color": 2},
    "D2": {"feeling": 3, "feel": 1, "happy": 1, "sad": 1, "emotion": 2},
    "D3": {"yesterday": 3, "ben": 1, "say": 1},
    "D4": {"next": 3, "year": 3, "predict": 3, "future": 3, "tomorrow": 3,
           "will": 1},
    "D5": {"why": 3, "reason": 2},
    "D6": {"tom": 3, "teach": 1, "say": 1, "spoke": 2, "speak": 2},
    "D7": {"better": 3, "opinion": 2, "worse": 2, "best": 1,
           "oslo": 1, "paris": 1},
    "D8": {"name": 3, "called": 1},
    "D9": {"old": 3},
    "D10": {"dream": 4, "nightmare": 2, "night": 1},
}

THRESH: dict[str, int] = {
    "C2": 4, "C4": 4, "C5": 4, "C6": 4, "C7": 4, "C14": 4, "C15": 4,
    "C19": 6, "C20": 4, "C30": 5,
}
DEFAULT_THRESH = 3

COUNT_INTENTS = {"C1", "C2", "C6", "C8", "C10", "C12", "C14", "C18", "C19",
                 "C20", "C21", "C26", "C28", "C29"}
PROCESS_INTENTS = {"C22", "C23", "C24", "C25"}
DECLINE_INTENTS = {"D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9",
                   "D10"}


def guard(question: str, toks: list[str]) -> set[str] | None:
    """QUESTION-TYPE GUARD. Return restricted candidate set, or None for all.

    Checked BEFORE intent scoring; a guarded-out question can only decline.
    """
    s = " ".join(toks)
    count_hit = ("how many" in s or "how much" in s or "count" in toks
                 or "number" in toks)
    if count_hit:
        return set(COUNT_INTENTS)
    process_hit = ("why" in toks
                   or "how do you decide" in s or "how decide" in s
                   or "what happen when" in s or "what happens when" in s)
    # NOTE: plain "why" anywhere triggers the process guard (C22/C23/C24/C25
    # stay reachable; every D intent stays reachable; list/count answers out).
    if process_hit:
        return set(PROCESS_INTENTS) | set(DECLINE_INTENTS)
    if "believe" in toks or "belief" in toks:
        return {"C7"} | set(DECLINE_INTENTS)
    return None


def score_all(toks: list[str], candidates: set[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for intent in candidates:
        total = 0
        for kw, w in KEYWORDS[intent].items():
            if any(edit1(t, kw) for t in toks):
                total += w
        out[intent] = total
    return out


def route(question: str) -> tuple[str, dict]:
    """Return (intent_id | 'DECLINE', debug info). Frozen at seal time."""
    s, toks = normalise(question)
    cands = guard(question, toks)
    if cands is None:
        cands = set(KEYWORDS)
    scores = score_all(toks, cands)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    best, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0
    need = THRESH.get(best, DEFAULT_THRESH)
    info = {"tokens": toks, "candidates": sorted(cands), "best": best,
            "best_score": best_score, "second": second_score,
            "need": need, "margin": MARGIN}
    if best_score >= need and best_score - second_score >= MARGIN:
        return best, info
    return "DECLINE", info


class Self105Agent(S99.Self99Agent):
    """Exp-99 agent with the scored router. Answer bodies inherited intact."""

    def answer_self(self, question: str) -> str:
        intent, _ = route(question)
        if intent == "DECLINE":
            return HONEST_DECLINE
        return super().answer_self(CANONICAL[intent])


# ------------------------------------------------------------- dev checking
def devcheck() -> int:
    """Dev ONLY (exp99-40 + exp100-80). Never touches the blind panel."""
    import fable_self100_runner as R100  # noqa: E402 (read-only scoring)
    import shutil  # noqa: E402

    state = SCRIPTS / "scratchpad" / "fable_self105_devcheck_state"
    if state.exists():
        shutil.rmtree(state)
    agent = Self105Agent(str(state))
    agent.run_session()
    s = agent.snapshot()

    # K4a: exp99 40 via the inherited script checker.
    checked = agent.check_all()
    s1 = checked["correct"]
    s2 = len(checked["hallucinations"])
    s3 = sum(1 for p in checked["per_question"]
             if p["id"].startswith("D") and p["pass"])
    print(f"exp99: S1 {s1}/40 S2 hallucinations={s2} S3 {s3}/10", flush=True)

    # exp100 80 via the frozen exp100 scorer.
    gate = {"n_taught": 19, "n_entities": 6, "n_quarantine": 1,
            "n_superseded": 2, "n_forgotten": 1, "sleeps": 0, "turns": 26}
    gate_ok = all(s[k] == v for k, v in gate.items())
    per = []
    for qid, intent, text in R100.BLIND:
        ans = agent.answer_self(text)
        verdict, note = R100.score(agent, qid, intent, ans, s)
        per.append((qid, intent, verdict, note, text, ans))
        print(f"{qid}({intent}): {verdict} Q={text[:58]} :: "
              f"A={ans[:72]} ({note})", flush=True)
    wrong = sum(1 for p in per if p[2] == "WRONG")
    correct_reph = sum(1 for p in per if p[0] <= "Q60" and p[2] == "CORRECT")
    new = [p for p in per if p[0] >= "Q61"]
    b3 = {v: sum(1 for p in new if p[2] == v)
          for v in ("CORRECT", "DECLINE", "WRONG")}
    print(f"exp100-80: WRONG={wrong} rephrasing-CORRECT={correct_reph}/60 "
          f"NEW={b3} gate={gate_ok}", flush=True)
    ok = gate_ok and s1 == 40 and s2 == 0 and s3 == 10 and wrong == 0
    print("DEVCHECK " + ("PASS" if ok else "FAIL"), flush=True)
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 105 scored router")
    parser.add_argument("--devcheck", action="store_true")
    parser.add_argument("--route", default=None,
                        help="print the routed intent for one question")
    args = parser.parse_args(argv)
    if args.route is not None:
        intent, info = route(args.route)
        print(f"{intent} {info}")
        return 0
    if args.devcheck:
        return devcheck()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
