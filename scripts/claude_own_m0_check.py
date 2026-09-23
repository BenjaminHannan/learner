"""Faithfulness filter for own-M0 (conversational mouth training pairs). Code only.

Checks one row = (record dict, reply str) and returns the list of failed
rule ids (empty = pass). Rules:
  R1: every slot the status needs is present (>= 1 each).
  R2: no slot appears that the record lacks.
  R3: no literal name/value leaks outside slots; no capitalised word
      outside slots except an explicit allowlist.
  R4: negation / status wording matches the status.
Applied to the reply field only (user_turn naturally holds literal names).
"""
import argparse
import json
import re
import sys

SLOTS = ("<S1>", "<V1>", "<R1>")

# Names-only blocklist: every owner/value person-name ever used in the
# talker120 line (train + heldout pools). No items were read; names only,
# so M0 pools can be kept disjoint from talker120's test names.
TALKER120_BLOCK = frozenset([
    "Adel", "Alba", "Amos", "Ash", "Berta", "Bex", "Boris", "Bram",
    "Casper", "Celia", "Cleo", "Corin", "Dara", "Delia", "Dessa",
    "Dorian", "Edwin", "Elmo", "Emil", "Esme", "Farah", "Faye", "Fina",
    "Flora", "Garth", "Gideon", "Goran", "Gus", "Hana", "Hazel", "Hela",
    "Hilda", "Ida", "Iris", "Ivan", "Ivo", "Jasper", "Jessa", "Joren",
    "Juno", "Karel", "Kasia", "Kito", "Koda", "Leon", "Lila", "Ludo",
    "Lumo", "Mabel", "Mara", "Marta", "Miro", "Nadia", "Nessa", "Niko",
    "Nils", "Odin", "Ona", "Opal", "Otis", "Pavel", "Pella", "Petra",
    "Pippa", "Quin", "Ramon", "Rhea", "Rosa", "Runa", "Selma", "Seth",
    "Sima", "Sten", "Talia", "Tessa", "Tilda", "Tobin", "Ula", "Ulf",
    "Ulma", "Umar", "Vera", "Vesper", "Viggo", "Vita", "Waldo", "Wilma",
    "Wren", "Wynn", "Xela", "Ximena", "Yara", "Ysolde", "Yusuf",
    "Zelda", "Zeno",
])

# Every capitalised token the sealed M0 templates may use outside slots.
# Derived from the template corpus in the pilot, then frozen here.
ALLOW_CAPS = frozenset([
    "Ah", "All", "And", "Anything", "Anytime", "Awesome", "Can", "Could",
    "Did", "Do", "Done", "Don't", "Fantastic", "From", "Glad", "Got",
    "Gotcha", "Great",
    "Happy", "Have", "Here", "Here's", "Hmm", "Honestly", "How", "I",
    "I'd", "I'll", "I'm",
    "I've", "Is", "Isn't", "It", "It's", "Just", "Let", "Lovely",
    "Nice", "No", "Not", "Noted", "Nothing", "Oh", "Okay", "Perfect",
    "Right", "Saved", "Shall", "So", "Sorry", "Sounds", "Stored", "Sure", "Sweet", "Thanks", "That",
    "That's", "The", "There", "There's", "Want", "What", "Where",
    "Which", "Who", "Whose",
    "Wonderful", "Yeah", "Yep", "You", "You've", "Yours",
])

HEDGE_PHRASES = [
    "don't know", "do not know", "not sure", "no idea", "can't say",
    "couldn't say", "haven't got", "not certain", "hasn't come up",
    "nothing on that",
]
FORGET_RE = re.compile(r"\b(forget|forgets|forgot|forgotten|forgetting)\b", re.I)
SAVE_PHRASES = ["saved", "noted", "got it", "stored", "written down"]
INFER_RE = re.compile(
    r"\b(infer|inferred|inferring|deduced|deducing|figured out|guessed|"
    r"guessing|assumed|assuming)\b", re.I)
CLARIFY_WORDS = ["which", "who", "what", "whose", "mean", "clarify", "sure"]


def _low(s):
    return s.lower()


def _has_phrase(text, phrases):
    t = _low(text)
    return any(p in t for p in phrases)


def allowed_slots(status, tag):
    """Slots the record carries (may appear) for this status/tag."""
    if status in ("OK", "SAVED"):
        return {"<S1>", "<V1>", "<R1>"}
    if status in ("UNKNOWN", "ABSTAIN", "FORGOT"):
        if tag == "WHOSE":
            return {"<R1>"}
        return {"<S1>", "<R1>"}
    if status == "CLARIFY":
        if tag == "WHOSE":
            return {"<R1>"}
        return {"<S1>", "<R1>"}
    return set()


def required_slots(status, tag):
    """Slots that must appear >= 1 for this status/tag."""
    if status in ("OK", "SAVED"):
        return {"<S1>", "<V1>", "<R1>"}
    if status in ("UNKNOWN", "ABSTAIN", "FORGOT"):
        return {"<S1>", "<R1>"}
    if status == "CLARIFY":
        if tag == "WHOSE":
            return {"<R1>"}
        return {"<S1>"}
    return set()


def check_row(record, reply, extra_block=()):
    """Return sorted list of failed rule ids ([] = pass)."""
    fails = []
    status = record.get("status", "")
    tag = record.get("tag", "")
    present = {s for s in SLOTS if s in reply}

    # R1: required slots present.
    if not required_slots(status, tag) <= present:
        fails.append("R1_missing")
    # R2: no slot the record lacks.
    if not present <= allowed_slots(status, tag):
        fails.append("R2_extra")

    # R3: literal leaks + capitalised words, outside slots only.
    noslot = reply
    for s in SLOTS:
        noslot = noslot.replace(s, " ")
    words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", noslot)
    leak = False
    for w in words:
        if w in TALKER120_BLOCK:
            leak = True
            break
        for b in extra_block:
            if w == b:
                leak = True
                break
        if leak:
            break
    caps_bad = any(
        (w[0].isupper() and w not in ALLOW_CAPS) for w in words)
    if leak or caps_bad:
        fails.append("R3_caps")

    # R4: status wording.
    r4 = False
    if status == "UNKNOWN":
        if not _has_phrase(reply, HEDGE_PHRASES):
            r4 = True
        if FORGET_RE.search(reply) or _has_phrase(reply, SAVE_PHRASES) \
                or INFER_RE.search(reply):
            r4 = True
    elif status == "ABSTAIN":
        if not _has_phrase(reply, HEDGE_PHRASES):
            r4 = True
        if FORGET_RE.search(reply) or _has_phrase(reply, SAVE_PHRASES) \
                or INFER_RE.search(reply):
            r4 = True
    elif status == "SAVED":
        if not _has_phrase(reply, SAVE_PHRASES):
            r4 = True
        if INFER_RE.search(reply) or FORGET_RE.search(reply) \
                or _has_phrase(reply, HEDGE_PHRASES):
            r4 = True
    elif status == "FORGOT":
        if not FORGET_RE.search(reply):
            r4 = True
        if _has_phrase(reply, SAVE_PHRASES) or INFER_RE.search(reply):
            r4 = True
    elif status == "CLARIFY" and tag != "WHOSE":
        if "?" not in reply:
            r4 = True
        if not _has_phrase(reply, CLARIFY_WORDS):
            r4 = True
        if FORGET_RE.search(reply) or _has_phrase(reply, SAVE_PHRASES) \
                or INFER_RE.search(reply):
            r4 = True
    elif status == "CLARIFY" and tag == "WHOSE":
        if "?" not in reply:
            r4 = True
        if "whose" not in _low(reply):
            r4 = True
        if FORGET_RE.search(reply) or _has_phrase(reply, SAVE_PHRASES) \
                or INFER_RE.search(reply):
            r4 = True
    elif status == "OK":
        if _has_phrase(reply, HEDGE_PHRASES):
            r4 = True
        if FORGET_RE.search(reply) or _has_phrase(reply, SAVE_PHRASES) \
                or INFER_RE.search(reply):
            r4 = True
    else:
        r4 = True
    if r4:
        fails.append("R4_status")
    return sorted(fails)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--block", default=None,
                    help="optional json file with extra blocklist words")
    args = ap.parse_args()
    extra = ()
    if args.block:
        with open(args.block) as f:
            extra = tuple(json.load(f).get("block", []))
    total = 0
    fails = 0
    per_rule = {}
    with open(args.inp) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            o = json.loads(line)
            rec = dict(o["record"])
            rec["tag"] = o.get("tag", "")
            bad = check_row(rec, o["reply"], extra)
            if bad:
                fails += 1
                for r in bad:
                    per_rule[r] = per_rule.get(r, 0) + 1
    print("rows=%d fails=%d %s" % (total, fails, per_rule))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
