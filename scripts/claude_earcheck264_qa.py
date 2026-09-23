#!/usr/bin/env python3
"""Exp 264 -- question-answering checker prompts (the ONE change).

On 261b's registered arm A the YES/NO entailment checker is replaced by three
targeted questions (design/v3/30-modes/264-qa-checker.md). v0 wording below is
the spec text verbatim; any dev-driven change is logged in PASSMARKS and sealed
as a new version of this file (never edited after the seal).

For each TEACH frame (S, R, V) the brake keeps:
- Q-value (V hidden): asks what S's <relation words> is.
- Q-owner (S hidden): asks whose <relation words> V is.
- Q-relation (R hidden): asks how V is related to S.

Save iff all three agree (see qa_decide); otherwise hold back as UNSURE.
No threshold, so nothing is tuned. The span guard (261b, unchanged) stays after.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_model as E  # noqa: E402

PROMPT_VERSION = "v5-plan-inflect + qrel-v1 + qown-v3 + qmap-v3(owner-suffix)"

# Dev log (wording debugged on dev only, never on any panel):
# - v0 spec-verbatim: Q-value/Q-owner asked the question first with the
#   fact-clause inline ("stated as a real, current fact (not asked, pretended,
#   ...)"). Pilot on dev (6 checks): pretend turns ("Say that ...") were
#   answered with the name on all 3 questions -> wrong saves.
# - v1 explicit-triggers: added "If the message only asks/checks/pretends/
#   plans/denies/replaces ... answer NOT STATED" with examples. Test on 12
#   dev turns: pretend 3/3 held, plan 3/3 held, plain 3/3 answered, but
#   check-questions ("..., right") held only 1/3.
# - v2 decide-first (sealed): the question leads with the fact-vs-check
#   decision ("First decide: does the message state this as a real, current
#   fact the speaker believes? If it only asks/checks/pretends/plans/denies/
#   replaces, answer NOT STATED. Otherwise, ..."). Test on 6 dev turns:
#   check-questions 3/3 held, plain 3/3 answered. Q-relation kept at v0
#   (no dev leak needed a change there).
# - v3 owner de-anchor (sealed): the v2 line "The speaker is answered as ..."
#   up front anchored "the speaker" for third-person turns (11/11 false
#   owner-holds on dev plain facts). v3 names the owner first, "the speaker"
#   last. Pilot 12/12 (8 names + 4 pretend holds).
# - v4 explicit so-check (sealed): "so ..." restatement checks without "?"
#   ("so X lives in Y") passed value+owner 10/10 on dev (the decide-first
#   clause listed "so ..." but the model ignored it). v4 names the pattern
#   ("a turn starting with "so" that restates a fact to confirm it").
#   Pilot: 8/8 so-checks NOT STATED, 3/3 plain controls answered. Same
#   precedent as 261's prompt B adding its "so ..." clause.
# - Q-relation v1 (sealed): v0 ("How is V related to S? Answer with one to
#   three words") let the model paraphrase ("Home", "residence", "The
#   speaker's cat", full sentences): 377 kept true frames failed the gate on
#   dev. v1 asks "What is V: S's what? Answer with one word ..." with format
#   examples. Pilot on 24 failures: 17/24 mappable.
# - Mapping v2/v3 (sealed; deviations D-rel-map logged in PASSMARKS):
#   possessive-strip, head-noun acceptance, spaceless normalisation,
#   pet-family interchange, date/birthday/country truncations, owner
#   tail-of-answer acceptance. All trap-safe (compound relatives still hold).
# - v5 (sealed): plan examples gain "trains to be"/"studying to be" (dev:
#   "trains to be a mason" was answered as a current job).
_DECIDE = (
    "First decide: does the message state this as a real, current fact the "
    "speaker believes? If the message only asks about it, checks or confirms "
    "it, answer NOT STATED. Checks include: a tag like \"..., right\", "
    "\"..., isn't it\" or \"..., yeah?\"; a turn starting with \"so\" that "
    "restates a fact to confirm it (such as \"so X lives in Y\"); "
    "pretends or supposes it (such as \"say that\", \"let's say\", "
    "\"imagine\", \"suppose\", \"what if\" or \"pretend\"); "
    "plans or wishes it (such as \"training\" or \"trains to be\", "
    "\"studying to be\", \"wants to\", "
    "\"hoping to\", \"is going to\", \"plans to\" or \"will start\"); "
    "denies it, or replaces it with something newer. "
)


def rel_words(relation: str) -> str:
    return str(relation).strip().replace("_", " ")


def subj_words(subject: str) -> str:
    return "the speaker" if str(subject).strip() == "me" else str(subject).strip()


def build_q_value(turn: str, subject: str, relation: str) -> str:
    s = subj_words(subject)
    rw = rel_words(relation)
    return (
        "/no_think\n"
        f"Message from the speaker: \u00ab{str(turn).strip()}\u00bb\n"
        + _DECIDE +
        f"Otherwise, what is {s}'s {rw}? "
        "Answer with the exact words from the message. "
        "If several, list them separated by ' | '. "
        "If it is unclear, answer AMBIGUOUS.\n"
        "Answer:"
    )


def build_q_owner(turn: str, relation: str, value: str) -> str:
    # v3 (dev-tested): the v2 line "The speaker is answered as ..." up front
    # anchored the model to answer "the speaker" even for third-person turns
    # (11/11 false owner-holds on dev plain facts). v3 names the owner from
    # the message first and mentions "the speaker" last. Pilot on 12 dev
    # turns: 8/8 third-person names right, 4/4 pretend turns NOT STATED.
    rw = rel_words(relation)
    v = str(value).strip()
    return (
        "/no_think\n"
        f"Message from the speaker: \u00ab{str(turn).strip()}\u00bb\n"
        + _DECIDE +
        f"Otherwise, whose {rw} is {v}? "
        "Name the owner with the exact words from the message. "
        "If several, list them separated by ' | '. "
        "If the owner is the speaker themself, write \"the speaker\". "
        "If it is unclear, answer AMBIGUOUS.\n"
        "Answer:"
    )


def build_q_relation(turn: str, subject: str, value: str) -> str:
    # v1 (dev-tested): constrain to one relation word with format examples.
    # v0 ("How is V related to S? Answer with one to three words") let the
    # model paraphrase ("Home", "residence", "The speaker's cat", full
    # sentences), which no table mapping could accept: on dev 377 kept true
    # frames failed the relation gate. v1 pilot on 24 of those failures:
    # 17/24 answered with the mappable word.
    s = subj_words(subject)
    v = str(value).strip()
    return (
        "/no_think\n"
        f"Message from the speaker: \u00ab{str(turn).strip()}\u00bb\n"
        f"What is {v}: {s}'s what? "
        "Answer with one word: the relation "
        "(for example mother, city, employer, school, language or pet). "
        "If none fits, answer NOT STATED or AMBIGUOUS.\n"
        "Answer:"
    )


# ------------------------------------------------------------------ answers
def norm_span(s: str) -> str:
    return " ".join(str(s).strip().split()).lower()


def split_answers(text: str) -> list:
    parts = [p.strip() for p in str(text).split("|")]
    out = []
    for p in parts:
        p = " ".join(p.split()).strip(" \t\"'.,;:!?()[]{}")
        if p:
            out.append(p)
    return out


_ABSTAIN = {"NOT STATED", "AMBIGUOUS"}


def _content_answers(text: str) -> list:
    return [a for a in split_answers(text)
            if a.strip().upper() not in _ABSTAIN]


def value_ok(answer_text: str, value: str) -> bool:
    want = norm_span(value)
    return any(norm_span(a) == want for a in _content_answers(answer_text))


def owner_ok(answer_text: str, subject: str) -> bool:
    want = norm_span("the speaker" if str(subject).strip() == "me"
                     else str(subject).strip())
    for a in _content_answers(answer_text):
        na = norm_span(a)
        if na == want:
            return True
        # The model often answers with context around the name ("My sister
        # Nerys" for subject Nerys, "Yorick Aldercroft" for Aldercroft):
        # accept when the wanted owner is the tail of the answer.
        # Trap-safe: "the speaker" never suffix-matches a name answer, and a
        # wrong person never ends with the right name.
        if na.endswith(" " + want):
            return True
    return False


def _narrower_map() -> dict:
    m = {}
    for r in E._TABLE["relations"]:
        nar = [str(x) for x in r.get("narrower", [])]
        if nar:
            m[r["name"]] = {E._rkey(x) for x in nar}
    return m


_NARROWER = None


def narrower_map() -> dict:
    global _NARROWER
    if _NARROWER is None:
        _NARROWER = _narrower_map()
    return _NARROWER


def _strip_possessive(s: str) -> str:
    """Remove a leading possessive (the speaker's, their/his/her/my/our/...,
    or a Name's) so 'The speaker's cat' maps like 'cat'. Mechanical
    normalisation, sealed here; dev: fixed 141/377 unmapped relation answers
    with no new false passes observed."""
    s = " ".join(str(s).split()).strip(" \t\"'.,;:!?()[]{}")
    s = re.sub(r"^(the speaker's|their|his|her|my|our|your|its)\s+",
               "", s, flags=re.IGNORECASE)
    s = re.sub(r"^[A-Z][a-z]+(?: [A-Z][a-z]+)*'s\s+", "", s)
    return s


def _flat(s: str) -> str:
    """Spaceless, ou-normalised key: 'home town' -> 'hometown' (the table's
    hometown alias 'home town' otherwise never matches), 'favourite' ->
    'favorite'."""
    return E._rkey(s).replace("favourite", "favorite").replace(" ", "")


# Same-concept truncations the single-word question forces (dev-measured):
# "What is July 22: X's what?" -> "date"; country_of_origin -> "country".
# No trap pair involves these relations, so no discrimination is lost.
_TRUNC = {"date": "date_of_birth", "birthday": "date_of_birth",
          "country": "country_of_origin"}

# Species family: table v2 lists pet's narrower as dog/cat only, but rabbit,
# hamster, parrot and horse are value_kind=pet relations too; the panel spec
# puts the species word plus pet/animal/companion in every pet gold alias
# list, and Ruling 1 treats the family as one concept. Answers cross freely.
_PETFAM = {"pet", "dog", "cat", "rabbit", "hamster", "parrot", "horse"}


def relation_ok(answer_text: str, relation: str) -> bool:
    """Map the free-text relation answer to R via table v2 names, aliases,
    narrower, or ancestors (deviation D-rel-map, logged in PASSMARKS: the
    spec lists names/aliases/narrower; dev showed the model answers the
    broader word for species frames ('pet' for cat/dog) and the sealed
    scorer's Ruling 1 already treats pet~dog/cat as the same concept
    family, so a broader answer maps too). NOT STATED / AMBIGUOUS never map.
    Wrong-relation traps are unaffected: trap pairs (wife vs sister_in_law,
    employer vs colleague-word, city vs hometown) share no ancestor link."""
    try:
        rc = E.canon_rel(relation)
    except Exception:
        rc = None
    if rc is None:
        return False
    nm = narrower_map()
    # ancestors of R: parents P with R in narrower(P).
    rkey = E._rkey(relation)
    ancestors = {p for p, nar in nm.items() if rkey in nar}
    # head-final compounds: the single-word answer keeps the head noun
    # ("color" for favorite_color, "friend" for best_friend). Compound
    # relatives stay discriminated: "mother" is NOT the last word of
    # "mother in law", so wife-vs-in-law traps still hold.
    head_final = E._rkey(relation).split(" ")[-1]
    for a in _content_answers(answer_text):
        a = _strip_possessive(a)
        if not a:
            continue
        key = E._rkey(a)
        try:
            ac = E.canon_rel(a)
        except Exception:
            ac = None
        if ac == rc:
            return True
        if key in nm.get(rc, set()):
            return True
        if ac is not None and ac in ancestors:
            return True
        if _flat(a) == _flat(relation) or _flat(a) == _flat(head_final):
            return True
        if ac is not None and ac in _PETFAM and rc in _PETFAM:
            return True
        if _TRUNC.get(key) == rc:
            return True
    return False


def qa_decide(frame: dict, a_value: str, a_owner: str, a_relation: str) -> tuple:
    """Return (save: bool, failed: list of q names)."""
    failed = []
    if not value_ok(a_value, frame.get("value", "")):
        failed.append("value")
    if not owner_ok(a_owner, frame.get("subject", "")):
        failed.append("owner")
    if not relation_ok(a_relation, frame.get("relation", "")):
        failed.append("relation")
    return (not failed, failed)
