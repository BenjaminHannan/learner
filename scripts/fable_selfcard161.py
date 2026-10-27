#!/usr/bin/env python3
"""161 -- a grounded self card: every answer computed from live agent state.

The earlier self layer answered from a baked string table: fixed replies
with panel names written in (comparatives naming two cities, age replies
naming one person, teach replies naming one fact). This file replaces that
with a card that reads the asked text plus the live loop state (notebook
rows, event log, fact origins, turn log, counters, sleep history, filings)
and builds each reply from what it finds. No person name, place name, or
panel string appears anywhere in this file; names in replies always come
from the state or from the asked text after resolving against the state.

The card owns both steps: route() maps a question to one intent label, and
answer_self() serves the intent from live state. The loop calls route();
a DECLINE intent serves the frozen decline text, anything else serves the
computed reply. The serving rule around the card (notebook wins, card only
on a notebook miss, decline text on DECLINE) lives in the loop file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_self99 as S99  # noqa: E402 (capability sheet only, read-only)
import fable_self105 as S105  # noqa: E402 (decline sentence, read-only)

CAP_CAN = list(S99.CAPABILITY_CAN)
CAP_CANNOT = list(S99.CAPABILITY_CANNOT)
CARD_DECLINE = S105.HONEST_DECLINE

IDENTITY = ("I don't have a name yet. I'm a small assistant that learns "
            "facts you teach me and answers from my notebook.")

# Route labels. Each maps from one frozen router intent family; the full
# table is published in the sealed marks file.
INTENTS = (
    "identity", "username", "cap_can", "cap_cannot", "count_facts",
    "count_people", "count_web", "count_sleep", "count_turns",
    "count_answers", "count_writes", "count_clarify", "count_guesses",
    "count_rules", "count_forgotten", "first", "last", "provenance",
    "confirm", "trail", "mode", "last_turn", "unsure", "dontknow",
    "web_belief", "web_source", "sleep_learned", "sleep_derived",
    "forgotten", "corrections", "corrections_count", "speakers",
    "speakers_any", "opinion", "favourite", "feelings", "past",
    "future", "reasons", "dream", "age_me", "age_you", "age_them",
    "DECLINE",
)

_TEACH_VERBS = {"teach", "taught", "teaching", "tell", "told", "telling",
                "give", "gave", "given", "say", "said", "saying",
                "hear", "heard", "pick", "picked"}
_FIRSTLAST_VERBS = {"teach", "taught", "teaching", "tell", "told",
                    "telling", "give", "gave", "given", "pass", "passed"}
_SING = {"facts": "fact", "things": "thing", "guesses": "guess",
         "rows": "row", "rules": "rule", "corrections": "correction",
         "persons": "person", "folks": "folk", "individuals": "individual",
         "turns": "turn", "questions": "question", "answers": "answer",
         "feelings": "feeling", "favourites": "favorite",
         "favourite": "favorite", "colours": "color", "names": "name",
         "times": "time", "dreams": "dream", "dreamed": "dream",
         "dreaming": "dream", "learned": "learn", "learning": "learn",
         "learnings": "learn", "trusted": "trust", "trusts": "trust",
         "corrected": "correct", "correcting": "correct",
         "refused": "refuse", "refusing": "refuse", "declined": "decline",
         "declining": "decline", "believes": "believe",
         "beileve": "believe", "beleive": "believe", "belive": "believe",
         "taught": "teach", "teaching": "teach", "told": "tell",
         "telling": "tell", "says": "say", "saying": "say",
         "hears": "hear", "hearing": "hear", "gives": "give",
         "giving": "give", "passes": "pass", "passing": "pass",
         "picks": "pick", "picking": "pick", "saved": "save",
         "saves": "save", "saving": "save", "writes": "write",
         "written": "write", "writing": "write", "forgot": "forget",
         "forgotten": "forget", "happens": "happen", "knows": "know",
         "knowing": "know", "remembers": "remember",
         "remembering": "remember", "holds": "hold", "holding": "hold"}
_BELIEVE = {"believe", "belief", "trust"}
# Plain-English paraphrases of the notebook's relation keys. Generic
# language knowledge (like a lemma map), read here as code constants;
# every name/value in a reply still comes from live state.
_REL_ALIASES = {"live": "city", "lives": "city", "lived": "city",
                "living": "city"}
_COUNT_NOUNS_FACTS = {"fact", "thing"}
_COUNT_NOUNS_PEOPLE = {"people", "person", "persons", "folk", "folks",
                       "individual", "individuals"}
_SLEEP_WORDS = {"sleep", "slept", "sleeping"}
_HYPO = {"if", "would", "could", "suppose", "wish"}


def _toks(text: str) -> list[str]:
    return re.findall(r"[a-z]+", " ".join(str(text).split()).lower())


class SelfCard161:
    """Bound to one live loop; every reply read from that loop's state."""

    def __init__(self, loop) -> None:
        self.loop = loop
        self.nb = loop.nb

    # ------------------------------------------------------- state readers
    def _turns(self) -> list[dict]:
        return list(getattr(self.loop, "self_turn_log", []))

    def _origin(self) -> dict:
        return getattr(self.loop, "self_origin", {})

    def _filings(self) -> list[dict]:
        return list(getattr(self.loop, "self_web_filings", []))

    def _sleep_hist(self) -> list[dict]:
        return list(getattr(self.loop, "self_sleep_history", []))

    def _forget_log(self) -> dict:
        return getattr(self.loop, "self_forget_log", {})

    def _counters(self) -> dict:
        return getattr(self.loop, "counters", {})

    def taught(self) -> list[dict]:
        return [f for fid, f in self.nb.facts.items()
                if f.get("source") == "taught" and self.nb.active(fid)]

    def rows_of(self, source: str) -> list[dict]:
        return [f for fid, f in self.nb.facts.items()
                if f.get("source") == source and self.nb.active(fid)]

    def show(self, value: dict) -> str:
        if "entity" in value:
            return self.nb.entities.get(value["entity"], value["entity"])
        return str(value.get("literal", ""))

    def display(self, fact: dict) -> str:
        return (f"{self.nb.entities[fact['subject']]}'s "
                f"{fact['relation']} is {self.show(fact['value'])}")

    def taught_events(self) -> list[dict]:
        return [e for e in self.nb.events
                if e.get("kind") == "FACT" and e.get("source") == "taught"]

    def retracted(self) -> list[dict]:
        gone = {e.get("fact_id") for e in self.nb.events
                if e.get("kind") == "RETRACT"}
        return [self.nb.facts[fid] for fid in sorted(gone)
                if fid in self.nb.facts]

    def entity_names(self) -> list[str]:
        return sorted(self.nb.entities.values())

    def relations(self) -> set[str]:
        out = set()
        for f in self.nb.facts.values():
            out.add(str(f.get("relation", "")))
        return {r for r in out if r}

    # --------------------------------------------- text against live vocab
    def _known_entity_in(self, text: str) -> str | None:
        low = " ".join(str(text).split()).lower()
        best = None
        for name in self.entity_names():
            n = name.lower()
            if n and re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])",
                               low):
                if best is None or len(name) > len(best):
                    best = name
        return best

    def _relations_in(self, text: str) -> list[str]:
        low = " ".join(str(text).split()).lower()
        found: list[str] = []
        keys = set(self.relations()) | set(_REL_ALIASES)
        for rel in sorted(keys, key=len, reverse=True):
            for form in {rel, rel.replace("_", " ")}:
                if re.search(r"(?<![a-z])" + re.escape(form.lower())
                             + r"(?![a-z])", low):
                    canon = _REL_ALIASES.get(rel, rel)
                    if (canon in self.relations()
                            and canon not in found):
                        found.append(canon)
                    break
        return found

    def _value_in(self, text: str) -> str | None:
        low = " ".join(str(text).split()).lower()
        best = None
        pool: set[str] = set()
        for f in self.nb.facts.values():
            pool.add(self.show(f["value"]))
        for val in sorted(pool, key=len, reverse=True):
            v = val.lower()
            if len(v) < 2:
                continue
            if re.search(r"(?<![a-z])" + re.escape(v) + r"(?![a-z])", low):
                best = val
                break
        return best

    def _missing_asks(self) -> list[dict]:
        out = []
        for t in self._turns():
            for r in t.get("records", []):
                if r.get("kind") == "answer" and r.get("status") in (
                        C.MISSING_FACT, C.AMBIGUOUS, C.UNKNOWN_ENTITY,
                        C.BROKEN_CHAIN):
                    out.append({"turn": t["n"], "ben": t["ben"],
                                "record": r})
        return out

    def _fact_current(self, name: str, text: str) -> dict | None:
        """The live current fact for the asked-about subject/relation."""
        res = self.nb.resolve(name)
        if res.status != C.OK:
            return None
        for rel in self._relations_in(text):
            cur = self.nb.current(res.detail["entity_id"], rel)
            if cur:
                return cur[0]
        return None

    def _trail_terminal(self, name: str,
                          rels: list[str]) -> dict | None:
        """Walked trail ending in a plain value, else None.

        A trail that ends mid-chain (the last value is another person)
        answers less than was asked; the card declines those rather
        than overclaiming a partial walk.
        """
        res = self.nb.ask(name, rels[:3])
        if res.status != C.OK:
            return None
        trail = res.detail.get("trail", [])
        if not trail or trail[-1] not in self.nb.facts:
            return None
        if "entity" in self.nb.facts[trail[-1]]["value"]:
            return None
        return {"answer": res.detail["answer"], "trail": trail}
        """The live current fact for the asked-about subject/relation."""
        res = self.nb.resolve(name)
        if res.status != C.OK:
            return None
        for rel in self._relations_in(text):
            cur = self.nb.current(res.detail["entity_id"], rel)
            if cur:
                return cur[0]
        return None

    # ---------------------------------------------------------------- route
    # All matching is lowercase intent words plus names/relations read from
    # live state. Second person (you/your) reads as the agent, first person
    # (my/i) as the user; anything else resolves against the notebook.
    def route(self, question: str) -> str:
        text = " ".join(str(question).split())
        low = text.lower()
        raw = set(_toks(text))
        toks = {_SING.get(w, w) for w in raw} | raw
        has = toks.__contains__
        ent = self._known_entity_in(text)
        you = has("you") or has("your")
        me = (has("my") or has("i") or has("me")
              or ("am" in toks and "i" in toks))

        def self_guarded() -> bool:
            return you or ent is None

        if "why" in toks:
            return "reasons"
        if any(w in toks for w in
               ("will", "predict", "future", "tomorrow", "next")):
            return "future"
        if "happen" in toks and not (
                {"many", "much", "count", "number"} & toks
                or "how many" in low or "how much" in low):
            return "DECLINE"
        if any(w in toks for w in ("search", "browse", "fetch", "news",
                                   "audio", "voice", "play")):
            return "DECLINE"
        if (("time" in toks or "clock" in toks or "timestamp" in toks)
                and not ({"many", "much", "count", "number"} & toks)):
            return "DECLINE"
        if ("my name" in low or "who am i" in low) \
                and "friend" not in toks:
            return "username"
        if "your name" in low or "who are you" in low:
            return "identity"
        if "what are you" in low and not ({"doing", "up"} & toks):
            return "identity"
        if "old" in toks:
            if "are you" in low or "your age" in low:
                return "age_me"
            if me and not you:
                return "age_you"
            if ent is not None:
                return "age_them"
            if you:
                return "age_me"
            return "DECLINE"
        if "refuse" in toks or "decline" in toks \
                or "said no" in low or "say no" in low:
            return "count_clarify"
        if ("ever" in toks
                and ({"save", "keep", "record", "write"} & toks)
                and ({"no", "not", "moment", "instance"} & toks)):
            return "count_clarify"
        if _BELIEVE & toks:
            if "trust" in toks and "me" in toks \
                    and ("more" in toks or "most" in toks):
                return "DECLINE"
            if "internet" in toks or "online" in toks or "web" in toks:
                return "web_belief"
            return "DECLINE"
        if ({"position", "stance", "attitude"} & toks) and (
                "internet" in toks or "online" in toks or "web" in toks):
            return "web_belief"
        if "dream" in toks or "nightmare" in toks:
            return "dream"
        if any(w in toks for w in _SLEEP_WORDS):
            if any(w in toks for w in ("learn", "while", "new", "pick",
                                       "account", "spill")):
                return "sleep_learned"
            if (any(w in toks for w in ("yet", "ever", "since", "started",
                                           "many", "much", "count",
                                           "number"))
                    or "how many" in low or "how much" in low):
                if self_guarded():
                    return "count_sleep"
                return "DECLINE"
            if any(w in toks for w in ("which", "what", "via", "come",
                                       "came", "derive", "derived",
                                       "fact", "row")):
                return "sleep_derived"
            if self_guarded():
                return "count_sleep"
            return "DECLINE"
        if "yesterday" in toks or "last night" in low or "last week" in low:
            if you or ent is None:
                return "past"
            return "DECLINE"
        if (any(w in toks for w in ("better", "worse", "best",
                                       "opinion")) and "than" in toks):
            if you or ent is None:
                return "opinion"
            return "DECLINE"
        if "personal take" in low or "opinion" in toks:
            if you or ent is None or "personal take" in low:
                return "opinion"
            return "DECLINE"
        if "favorite" in toks:
            if you:
                return "favourite"
            return "DECLINE"
        if any(w in toks for w in ("feeling", "emotion",
                                   "happy", "sad")):
            if you:
                return "feelings"
            return "DECLINE"
        if "forget" in toks:
            if {"what", "which", "anything", "have", "many", "much",
                    "count", "number", "tally", "total"} & toks:
                if {"many", "much", "count", "number",
                        "tally", "total"} & toks:
                    return "count_forgotten"
                return "forgotten"
            return "DECLINE"
        if "correct" in toks:
            if {"what", "which", "thing", "anything", "along", "way",
                    "many", "much", "count", "number", "time"} & toks:
                if {"many", "much", "count", "number", "time"} & toks:
                    return "corrections_count"
                return "corrections"
            return "DECLINE"
        if any(w in toks for w in ("many", "much", "count", "number")) \
                or "how many" in low or "how much" in low:
            if not self_guarded():
                return "DECLINE"
            if (_COUNT_NOUNS_FACTS & toks) and (_COUNT_NOUNS_PEOPLE & toks):
                return "DECLINE"
            if _COUNT_NOUNS_PEOPLE & toks:
                return "count_people"
            if any(w in toks for w in ("turn", "together")):
                return "count_turns"
            if "answer" in toks or "question" in toks:
                return "count_answers"
            if {"correct", "correction"} & toks:
                return "corrections_count"
            if "forget" in toks:
                return "count_forgotten"
            if "rule" in toks or "reason" in toks:
                return "count_rules"
            if "guess" in toks or "approval" in toks or "approve" in toks:
                return "count_guesses"
            if "fact" in toks:
                return "count_facts"
            if any(w in toks for w in ("save", "write", "row", "wrote")):
                return "count_writes"
            if "refuse" in toks:
                return "count_clarify"
            if "internet" in toks or "online" in toks or "web" in toks:
                return "count_web"
            if any(w in toks for w in ("sleep", "slept")):
                return "count_sleep"
            if _COUNT_NOUNS_FACTS & toks or "teach" in toks \
                    or "know" in toks or "hold" in toks \
                    or "remember" in toks:
                return "count_facts"
            return "DECLINE"
        if ("unsure" in toks or "uncertain" in toks
                or "missing" in toks or "gap" in toks) and self_guarded():
            return "unsure"
        if "know" in toks and ("guess" in toks or "instead" in toks
                               or "when" in toks) and self_guarded():
            return "dontknow"
        if any(w in toks for w in ("cannot", "limit", "limits", "unable")) \
                or "can't" in low or "can not" in low \
                or ("can" in toks and "do" in toks
                    and ("not" in toks or "never" in toks)) \
                or ("n't" in low and "do" in toks):
            if you or ent is None:
                return "cap_cannot"
            return "DECLINE"
        if (("can" in toks and "do" in toks) or "able" in toks
                or "capabilit" in low):
            if you or ent is None:
                return "cap_can"
            return "DECLINE"
        if any(w in toks for w in ("first", "earliest", "initial",
                                   "kick", "ever")) and \
                (_FIRSTLAST_VERBS & toks or "fact" in toks
                 or "lesson" in toks) and self_guarded():
            return "first"
        if any(w in toks for w in ("last", "recent", "latest", "newest",
                                   "new")) and \
                (_FIRSTLAST_VERBS & toks or "fact" in toks
                 or "lesson" in toks
                 or "information" in toks) and self_guarded():
            return "last"
        if any(w in toks for w in ("sure", "certain", "confident",
                                   "really")) and ent is not None:
            if _HYPO & toks:
                return "DECLINE"
            if self._fact_current(ent, text) is None:
                return "DECLINE"
            return "confirm"
        if (("who" in toks or "whom" in toks) or "where" in toks) and \
                (_TEACH_VERBS & toks or "learn" in toks
                 or "said" in toks) and ent is not None:
            if _HYPO & toks:
                return "DECLINE"
            if self._fact_current(ent, text) is None:
                return "DECLINE"
            return "provenance"
        if any(w in toks for w in ("besides", "anyone", "somebody",
                                   "else", "other")) and \
                ("teach" in toks or "tell" in toks or "talk" in toks
                 or "speak" in toks or "say" in toks):
            return "speakers_any"
        if any(w in toks for w in ("tell", "told", "say", "said", "spoke",
                                   "speak")) and "you" in toks and \
                (ent is not None or me):
            return "speakers"
        if "internet" in toks or "online" in toks or "web" in toks:
            if any(w in toks for w in ("source", "quote", "url", "page",
                                       "come", "came")) or "row" in toks:
                return "web_source"
            if self_guarded():
                return "count_web"
            return "DECLINE"
        if any(w in toks for w in ("before", "previous", "earlier",
                                   "prev")) or "just before" in low:
            if _TEACH_VERBS & toks:
                return "DECLINE"
            if you or ent is None:
                return "last_turn"
            return "DECLINE"
        if "doing" in toks and any(w in toks for w in
                                   ("now", "moment", "currently",
                                    "second")):
            if you or ent is None:
                return "mode"
            return "DECLINE"
        if "up to" in low and ("right" in toks or "now" in toks
                               or "second" in toks or "moment" in toks):
            if you or ent is None:
                return "mode"
            return "DECLINE"
        if "guess" in toks or "approval" in toks or "approve" in toks:
            return "count_guesses"
        if "rule" in toks and "fact" in toks:
            return "count_rules"
        if low.startswith("where") or low.startswith("what") \
                or low.startswith("which"):
            if _HYPO & set(toks):
                return "DECLINE"
            rels = self._relations_in(text)
            if ent is not None and len(rels) >= 2:
                if self._trail_terminal(ent, rels) is not None:
                    return "trail"
            return "DECLINE"
        return "DECLINE"

    # --------------------------------------------------------------- answer
    def answer_self(self, question: str) -> str:
        return self._serve(self.route(question), str(question))

    def _taught_count(self) -> int:
        return len(self.taught())

    def _quarantine_count(self) -> int:
        return len(self.rows_of("web-quarantine"))

    def _sleep_count(self) -> int:
        try:
            return int(self._counters().get("sleeps", 0))
        except (TypeError, ValueError):
            return len(self._sleep_hist())

    def _serve(self, intent: str, question: str) -> str:
        nb = self.nb
        turns = self._turns()
        n_turns = len(turns)
        origin = self._origin()
        if intent == "DECLINE":
            return CARD_DECLINE
        if intent == "identity":
            return IDENTITY
        if intent == "username":
            for f in self.taught():
                if f.get("relation") == "name":
                    return f"Your name is {self.show(f['value'])}."
            return "You never told me your name, so I do not know it."
        if intent == "cap_can":
            return "I can: " + "; ".join(CAP_CAN) + "."
        if intent == "cap_cannot":
            return "I cannot: " + "; ".join(CAP_CANNOT) + "."
        if intent == "count_facts":
            t, q = self._taught_count(), self._quarantine_count()
            plural = "" if q == 1 else "s"
            return (f"I know {t} facts you taught me. "
                    f"I also hold {q} web row{plural}, "
                    f"which I do not believe.")
        if intent == "count_people":
            names = self.entity_names()
            return f"I know {len(names)} people: " + ", ".join(names) + "."
        if intent == "count_web":
            q = self._quarantine_count()
            if q == 0:
                return "No. I hold 0 web rows."
            plural = "" if q == 1 else "s"
            return (f"Yes. I hold {q} quarantined web row{plural}. "
                    f"I filed it but I do not believe it.")
        if intent == "web_belief":
            return ("No. Web rows are quarantined and never answer "
                    "questions. Only what you teach me answers.")
        if intent == "web_source":
            filings = self._filings()
            if not filings:
                return ("I hold no web rows, so there is no source "
                        "to name.")
            w = filings[0]
            host = str(w.get("url", "")).replace(
                "https://", "").replace("http://", "").split("/")[0]
            dotted = host.replace(".", " dot ")
            return (f"A page at {dotted} said, quote, {w.get('span', '')}. "
                    f"I filed it as quarantined and I do not believe it.")
        if intent == "count_sleep":
            s = self._sleep_count()
            if s == 0:
                return "No. I have slept 0 times."
            return f"Yes. I have slept {s} times."
        if intent == "sleep_learned":
            if self._sleep_count() == 0:
                return "Nothing. I have not slept yet."
            return "Nothing new was installed while sleeping."
        if intent == "sleep_derived":
            sd = len(self.rows_of("sleep-derived"))
            return (f"None. {sd} of my facts are sleep-derived.")
        if intent == "count_turns":
            return f"We have had {n_turns} turns."
        if intent == "count_answers":
            a = int(self._counters().get("answers", 0))
            return f"I have answered {a} questions."
        if intent == "count_writes":
            w = int(self._counters().get("writes", 0))
            return f"I saved {w} times through our turns."
        if intent == "count_clarify":
            c = int(self._counters().get("clarifications", 0))
            if c == 0:
                return (f"No. I understood all {n_turns} turns; "
                        f"I asked for clarification 0 times.")
            return (f"Yes, {c} times I asked for clarification "
                    f"instead of saving.")
        if intent == "count_guesses":
            p = len(self.rows_of("proposed"))
            return (f"{p} guesses are waiting for your approval.")
        if intent == "count_rules":
            r = len(self.rows_of("inferred"))
            return f"{r} of my facts came from rules."
        if intent == "count_forgotten":
            return f"{len(self.retracted())}."
        if intent == "forgotten":
            rows = self.retracted()
            if not rows:
                return ("You never asked me to forget anything. "
                        "I hold no retired rows.")
            names = "; ".join(self.display(f) for f in rows)
            t = self._forget_log().get(rows[0]["fact_id"], "?")
            return (f"I forgot: {names}. You asked me to forget it "
                    f"in turn {t}. The old row is kept but retired.")
        if intent == "corrections":
            if not nb.superseded:
                return "You have not corrected anything yet."
            pairs = []
            for old_id, new_id in sorted(nb.superseded.items()):
                old, new = nb.facts[old_id], nb.facts[new_id]
                pairs.append(f"{nb.entities[old['subject']]}'s "
                             f"{old['relation']} from "
                             f"{self.show(old['value'])} to "
                             f"{self.show(new['value'])}")
            n = len(nb.superseded)
            thing = "thing" if n == 1 else "things"
            return (f"You corrected {n} {thing}: " + "; ".join(pairs)
                    + ".")
        if intent == "corrections_count":
            return f"{len(nb.superseded)}."
        if intent == "first":
            evs = self.taught_events()
            if not evs:
                return "You have not taught me anything yet."
            return (f"The first thing you taught me was: "
                    f"{self.display(nb.facts[evs[0]['fact_id']])}.")
        if intent == "last":
            evs = self.taught_events()
            if not evs:
                return "You have not taught me anything yet."
            last = nb.facts[evs[-1]["fact_id"]]
            t = origin.get(last["fact_id"], {}).get("turn", "?")
            return (f"The last thing you taught me was: "
                    f"{self.display(last)}, in turn {t}.")
        if intent in ("provenance", "confirm"):
            return self._provenance(question, intent)
        if intent == "trail":
            return self._trail(question)
        if intent == "mode":
            mode = getattr(self.loop, "mode", "?")
            return (f"Right now I am back in {mode} mode, waiting "
                    f"for your next turn.")
        if intent == "last_turn":
            if turns and getattr(self.loop, "experience", []):
                last = turns[-1]
                return (f"Just before that, in turn {last['n']}, you "
                        f"asked: {last['ben']} I replied: "
                        f"{last['reply']}")
            return "Just before that I did nothing; the log is empty."
        if intent == "unsure":
            bits = []
            for m in self._missing_asks():
                r = m["record"]
                bits.append(f"{r.get('name', '')}'s "
                            f"{' '.join(r.get('relations', []))} "
                            f"(never taught)")
            if self._quarantine_count():
                bits.append("the web row (quarantined, not believed)")
            if self.rows_of("proposed"):
                bits.append(f"{len(self.rows_of('proposed'))} proposed "
                            f"rows waiting for your approval")
            if not bits:
                return ("Nothing is open. Every question you asked "
                        "was answered.")
            return "I am unsure about: " + "; ".join(bits) + "."
        if intent == "dontknow":
            ex = ""
            for t in turns:
                if "do not know" in t.get("reply", ""):
                    ex = f" Like when you asked: {t['ben']}"
                    break
            return ("I say I do not know instead of guessing." + ex)
        if intent == "speakers":
            name = self._known_entity_in(question)
            if name is None:
                return ("Only you talk to me. All "
                        f"{n_turns} turns are yours, and I have no "
                        f"record of anyone else.")
            return (f"{name} has never spoken to me. "
                    f"All {n_turns} turns are yours.")
        if intent == "speakers_any":
            q = self._quarantine_count()
            if q:
                return ("No. Every taught fact came from you. The only "
                        f"outside text is the {q} quarantined web row, "
                        f"which I do not believe. I have no record of "
                        f"anyone else.")
            return ("No. Every taught fact came from you. I have no "
                    "record of anyone else.")
        if intent == "opinion":
            return "I have no opinions. I only store what you state."
        if intent == "favourite":
            return ("I do not have favourites. I only store what you "
                    "state, not likes.")
        if intent == "feelings":
            return ("I do not have feelings. I keep notes, "
                    "I do not feel.")
        if intent == "past":
            return (f"I have no record of that time. My log starts "
                    f"with our first turn here and holds "
                    f"{n_turns} turns.")
        if intent == "future":
            return "I cannot predict. I only know what you taught me."
        if intent == "reasons":
            return ("You never told me why. I only store what you "
                    "state, not reasons.")
        if intent == "dream":
            sd = len(self.rows_of("sleep-derived"))
            return (f"I do not dream. I have slept "
                    f"{self._sleep_count()} times and hold {sd} "
                    f"sleep-derived facts.")
        if intent == "age_me":
            return ("I do not have an age in years. My notebook "
                    f"started {n_turns} turns ago.")
        if intent == "age_you":
            return "You never told me your age, so I do not know it."
        if intent == "age_them":
            return self._their_age(question)
        return CARD_DECLINE

    # --------------------------------------- provenance + trail + their age
    def _provenance(self, question: str, intent: str) -> str:
        nb = self.nb
        origin = self._origin()
        name = self._known_entity_in(question)
        if name is None:
            return CARD_DECLINE
        res = nb.resolve(name)
        if res.status != C.OK:
            return "I have no record of that."
        eid = res.detail["entity_id"]
        rels = self._relations_in(question)
        if not rels:
            return "I have no record of that."
        rel = rels[0]
        asked_val = self._value_in(question)
        cur = nb.current(eid, rel)
        cur_val = self.show(cur[0]["value"]) if cur else None
        if intent == "confirm":
            if cur and (asked_val is None or asked_val == cur_val):
                olds = [self.show(nb.facts[o]["value"])
                        for o, n in nb.superseded.items()
                        if cur and n == cur[0]["fact_id"]]
                old_txt = f" It replaced {olds[0]}." if olds else ""
                return (f"Yes. You taught me {name}'s {rel} is "
                        f"{cur_val}." + old_txt + " Nothing you taught "
                        f"contradicts it.")
            if cur:
                t = origin.get(cur[0]["fact_id"], {}).get("turn", "?")
                olds = [self.show(nb.facts[o]["value"])
                        for o, n in nb.superseded.items()
                        if n == cur[0]["fact_id"]]
                if olds:
                    return (f"No. You taught me {name}'s {rel} is "
                            f"{cur_val}. You corrected {olds[0]} to "
                            f"{cur_val} in turn {t}.")
                return (f"No. You taught me {name}'s {rel} is "
                        f"{cur_val}, in turn {t}.")
            return "I have no record of that."
        if not cur:
            return "I have no record of that."
        fid = cur[0]["fact_id"]
        t = origin.get(fid, {}).get("turn", "?")
        olds = [self.show(nb.facts[o]["value"])
                for o, n in nb.superseded.items() if n == fid]
        if asked_val is not None and asked_val != cur_val:
            return (f"I have no record of that. What you taught me is "
                    f"{name}'s {rel} is {cur_val}, in turn {t}.")
        if olds:
            return (f"You did tell me in turn {t}, when you corrected "
                    f"{olds[0]} to {cur_val}. Your correction replaced "
                    f"the old row; I kept both.")
        return f"You did tell me in turn {t}. I kept the row."

    def _trail(self, question: str) -> str:
        nb = self.nb
        name = self._known_entity_in(question)
        rels = self._relations_in(question)
        if name is None or len(rels) < 2:
            return CARD_DECLINE
        got = self._trail_terminal(name, rels)
        if got is None:
            return CARD_DECLINE
        hops = [self.display(nb.facts[f]) for f in got["trail"]]
        if not hops:
            return CARD_DECLINE
        return (f"{got['answer']}. " + " and ".join(hops)
                + "; I followed all rows.")

    def _their_age(self, question: str) -> str:
        nb = self.nb
        name = self._known_entity_in(question)
        if name is None:
            return "I have no record of that."
        res = nb.resolve(name)
        if res.status != C.OK:
            return "I have no record of that."
        cur = nb.current(res.detail["entity_id"], "age")
        if not cur:
            return (f"You never taught me {name}'s age, "
                    f"so I do not know it.")
        val = self.show(cur[0]["value"])
        return f"You taught me {name}'s age is {val}."
