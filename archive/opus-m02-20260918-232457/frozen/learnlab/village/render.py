"""Render village records (world -> renderer contract) into stream sentences.

Every sentence is a pattern from `PatternSource` filled with surface forms.
Narration, rule and question patterns are split per bank; teacher patterns
follow their style, and styles are split whole (6/2/2), exactly as
`learnlab.patterns.assign_splits` does for the real bank. A pattern is chosen
by a hash of the record's position among the patterns of the visit's split
only, and every choice is recorded through the visit's `SplitView`.

For the audit, each filled pattern is also kept as one "unit": its words on
one line with any nested sentence masked as "x" (the nested sentence is its own
unit). `splits.audit_examples` then sees each pattern instance whole, so a
held-out pattern is flagged only where it could really have produced the text.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import string
from typing import Any, Iterable, Mapping, Optional, Sequence

from learnlab.splits import FamilyManifest, SplitManifest, SplitRegistry, SplitView, assign_ranked, hash_canary

from . import vocab

BANK_PATH = Path(__file__).resolve().parents[2] / "data" / "village" / "patterns" / "bank-v1.json"
FALLBACK_VERSION = "village-fallback-v1"

# The shared contract: bank id -> placeholders (each used exactly once per pattern).
BANK_SLOTS: dict[str, tuple[str, ...]] = {
    "ev.go": ("person", "place"), "ev.pick_up": ("person", "object"), "ev.put_down": ("person", "object", "place"),
    "ev.give": ("giver", "receiver", "object"), "ev.put_in": ("person", "object", "container"),
    "ev.take_out": ("person", "object", "container"), "ev.open": ("person", "container"),
    "ev.close": ("person", "container"), "ev.carry": ("person", "container", "place"), "ev.swap": ("person", "person_b"),
    "ev.time": ("time",), "ev.new_day": (), "ev.fail_open": ("person", "container"),
    "ev.fail_pick_up": ("person", "object"), "ev.fail_put_in": ("person", "object", "container"),
    "ev.breaks": ("object",), "ev.follows": ("person", "leader", "place"),
    "ev.moved_by_place": ("object", "place", "place2"), "ev.returned": ("object", "person"),
    "ev.recoloured": ("object", "colour"), "ev.traded": ("person", "count", "object_kind", "item"),
    "ev.intro_person": ("person", "place"), "ev.intro_object": ("object", "place"),
    "ev.intro_in": ("object", "container"), "ev.intro_holds": ("person", "object"), "ev.owner": ("person", "object"),
    "ev.material": ("object", "material"), "ev.kind_group": ("object_kind", "category"),
    "ev.is_open": ("container",), "ev.is_closed": ("container",), "ev.layout_dir": ("place", "direction", "place2"),
    "ev.layout_next": ("place", "place2"),
    "rule.R1_material": ("material",), "rule.R1_category": ("category",), "rule.R2": ("person", "leader"),
    "rule.R3": ("place", "place2", "time"), "rule.R4": ("time",), "rule.R5": ("container", "colour"),
    "rule.R6": ("person", "container"), "rule.R7": ("person", "place", "time"),
    "rule.R8": ("place", "count", "object_kind", "item"),
    "t.state": ("fact",), "t.remember": ("fact",), "t.ask": ("question",), "t.right": (), "t.wrong": ("correction",),
    "t.demo_intro": ("rule",), "t.demo_step": ("event",), "t.demo_outro": ("rule",), "t.change": ("fact",),
    "t.quiz_later": ("question",),
    "q.where_object": ("object",), "q.where_person": ("person",), "q.who_has": ("object",),
    "q.in_container": ("container",), "q.where_before": ("object",), "q.where_at_time": ("object", "time"),
    "q.count_at": ("object_kind", "place"), "q.count_held": ("object_kind", "person"),
    "q.compare_count": ("object_kind", "place", "place2"), "q.direction": ("place", "place2"), "q.next_to": ("place",),
    "q.what_if": ("action",), "q.why_at": ("object", "place"), "q.plan_get": ("person", "object"),
    "q.rule_material": ("material",), "q.rule_category": ("category",), "q.rule_person": ("person",),
    "q.rule_place": ("place",), "q.rule_container": ("container",), "q.yn_at": ("object", "place"),
    "q.yn_has": ("person", "object"), "q.yn_in": ("object", "container"),
}
TEACHER_BANKS = tuple(bank for bank in BANK_SLOTS if bank.startswith("t."))
PERSON_SLOTS = frozenset(("person", "person_b", "leader", "giver", "receiver"))
NESTED_SLOTS = frozenset(("fact", "correction", "rule", "event", "question", "action"))
MASK = "x"  # stands in for a nested sentence inside its wrapper's audit unit

# Fallback patterns until bank-v1.json exists: narration past tense, scene/state,
# rules and questions present tense, no fact words outside placeholders.
FALLBACK: dict[str, tuple[str, ...]] = {
    "ev.go": ("{person} went to {place}.", "{person} walked over to {place}.", "{person} headed off to {place}."),
    "ev.pick_up": ("{person} picked up {object}.", "{person} took hold of {object}.", "{person} grabbed {object}."),
    "ev.put_down": ("{person} put down {object} at {place}.", "{person} left {object} at {place}.",
                    "At {place}, {person} set {object} down."),
    "ev.give": ("{giver} gave {object} to {receiver}.", "{giver} handed {object} to {receiver}.",
                "{receiver} got {object} from {giver}."),
    "ev.put_in": ("{person} put {object} in {container}.", "{person} placed {object} inside {container}.",
                  "{person} dropped {object} into {container}."),
    "ev.take_out": ("{person} took {object} out of {container}.", "{person} pulled {object} out of {container}.",
                    "{person} lifted {object} out of {container}."),
    "ev.open": ("{person} opened {container}.", "{person} opened up {container}.", "{person} swung {container} open."),
    "ev.close": ("{person} closed {container}.", "{person} shut {container}.", "{person} pushed {container} shut."),
    "ev.carry": ("{person} carried {container} to {place}.", "{person} took {container} over to {place}.",
                 "{person} brought {container} along to {place}."),
    "ev.swap": ("{person} and {person_b} swapped what they were holding.", "{person} and {person_b} traded what they held.",
                "{person} swapped things with {person_b}."),
    "ev.time": ("It became {time}.", "Soon it was {time}.", "Then {time} came."),
    "ev.new_day": ("A new day began.", "A new day started.", "Then the next day came."),
    "ev.fail_open": ("{person} tried to open {container}, but it did not open.", "{person} could not open {container}.",
                     "{person} failed to open {container}."),
    "ev.fail_pick_up": ("{person} tried to pick up {object}, but could not.", "{person} was unable to pick up {object}.",
                        "{person} failed to lift {object}."),
    "ev.fail_put_in": ("{person} tried to put {object} in {container}, but could not.",
                       "{person} could not get {object} into {container}.", "{person} failed to put {object} inside {container}."),
    "ev.breaks": ("{object} broke.", "{object} broke into pieces.", "{object} cracked and broke."),
    "ev.follows": ("{person} followed {leader} to {place}.", "{person} went after {leader} to {place}.",
                   "{leader} went to {place}, and {person} followed."),
    "ev.moved_by_place": ("{object} was left at {place} and ended up at {place2}.", "{object} left at {place} was moved to {place2}.",
                          "{object} went from {place} over to {place2}."),
    "ev.returned": ("{object} went back to its owner, {person}.", "{object} found its way back to {person}, its owner.",
                    "{object} returned to {person}, who owns it."),
    "ev.recoloured": ("{object} turned {colour}.", "{object} became {colour}.", "{object} changed to {colour}."),
    "ev.traded": ("{person} traded {count} {object_kind} for {item}.", "{person} gave {count} {object_kind} and got {item}.",
                  "{person} paid {count} {object_kind} for {item}."),
    "ev.intro_person": ("{person} is at {place}.", "{person} is standing at {place}.", "{person} is over at {place}."),
    "ev.intro_object": ("{object} is at {place}.", "{object} lies at {place}.", "{object} sits at {place}."),
    "ev.intro_in": ("{object} is in {container}.", "{object} is inside {container}.", "{object} lies in {container}."),
    "ev.intro_holds": ("{person} has {object}.", "{person} is holding {object}.", "{person} is carrying {object}."),
    "ev.owner": ("{object} belongs to {person}.", "{person} owns {object}.", "{object} is owned by {person}."),
    "ev.material": ("{object} is made of {material}.", "{object} is made from {material}.", "{material} is what {object} is made of."),
    "ev.kind_group": ("{object_kind} are {category}.", "{object_kind} count as {category}.", "{object_kind} are grouped with {category}."),
    "ev.is_open": ("{container} is open.", "{container} stands open.", "{container} is wide open."),
    "ev.is_closed": ("{container} is closed.", "{container} is shut.", "{container} is shut tight."),
    "ev.layout_dir": ("{place} is {direction} of {place2}.", "{place} lies {direction} of {place2}.",
                      "{place} sits {direction} of {place2}."),
    "ev.layout_next": ("{place} is next to {place2}.", "{place} is beside {place2}.", "{place} lies right by {place2}."),
    "rule.R1_material": ("Things made of {material} break when they are put down.", "Anything made of {material} breaks when it is put down.",
                         "When things of {material} are set down, they break."),
    "rule.R1_category": ("{category} break when they are put down.", "All {category} break when put down.",
                         "If {category} are put down, they break."),
    "rule.R2": ("{person} always follows {leader}.", "Wherever {leader} goes, {person} goes too.", "{person} goes wherever {leader} goes."),
    "rule.R3": ("Things left at {place} are moved to {place2} every {time}.", "Anything left at {place} is taken to {place2} each {time}.",
                "Each {time}, whatever is left at {place} goes to {place2}."),
    "rule.R4": ("Lost things go back to their owners every {time}.", "Each {time}, lost things return to their owners.",
                "Every {time}, anything lost finds its owner."),
    "rule.R5": ("Things put in {container} turn {colour}.", "Whatever goes in {container} turns {colour}.",
                "Anything placed in {container} becomes {colour}."),
    "rule.R6": ("Only {person} can open {container}.", "{container} opens only for {person}.",
                "{container} can be opened by {person} and no other."),
    "rule.R7": ("Every day, {person} goes to {place} when it is {time}.", "{person} goes to {place} every {time}.",
                "Each day, when {time} comes, {person} goes to {place}."),
    "rule.R8": ("At {place}, {count} {object_kind} can be traded for {item}.", "{count} {object_kind} buy {item} at {place}.",
                "At {place}, {count} {object_kind} can be swapped for {item}."),
    "q.where_object": ("Where is {object}?", "Where is {object} now?", "Can you tell me where {object} is?"),
    "q.where_person": ("Where can {person} be found?", "Where has {person} gone?", "In what place is {person}?"),
    "q.who_has": ("Who has {object}?", "Who is holding {object}?", "Who has {object} now?"),
    "q.in_container": ("What is in {container}?", "What is inside {container}?", "What can be found in {container}?"),
    "q.where_before": ("Where was {object} before?", "Where did {object} use to be?", "Before, where was {object}?"),
    "q.where_at_time": ("Where was {object} when it was {time}?", "When it was {time}, where was {object}?",
                        "Where was {object} when {time} came?"),
    "q.count_at": ("How many {object_kind} are at {place}?", "How many {object_kind} can be found at {place}?",
                   "At {place}, how many {object_kind} are there?"),
    "q.count_held": ("How many {object_kind} does {person} have?", "How many {object_kind} is {person} holding?",
                     "{person} has how many {object_kind}?"),
    "q.compare_count": ("Are there more {object_kind} at {place} or at {place2}?", "Which has more {object_kind}, {place} or {place2}?",
                        "Where are there more {object_kind}, at {place} or at {place2}?"),
    "q.direction": ("Which way is {place2} from {place}?", "In which direction is {place2} from {place}?",
                    "From {place}, which way do you go to reach {place2}?"),
    "q.next_to": ("What is next to {place}?", "What place is beside {place}?", "What is right next to {place}?"),
    "q.what_if": ("What would happen if {action}?", "What happens if {action}?", "If {action}, what would happen?"),
    "q.why_at": ("Why is {object} at {place}?", "How did {object} end up at {place}?", "Why is {object} now at {place}?"),
    "q.plan_get": ("How could {person} get {object}?", "What could {person} do to get {object}?",
                   "How can {person} get hold of {object}?"),
    "q.rule_material": ("What is the rule about things made of {material}?", "What happens to things made of {material} here?",
                        "What is the rule for {material} things?"),
    "q.rule_category": ("What is the rule about the group {category}?", "What happens to {category} here?",
                        "What rule is there for {category}?"),
    "q.rule_person": ("What is the rule about the person {person}?", "What rule is there about {person}?",
                      "Which rule is about {person}?"),
    "q.rule_place": ("What is the rule about the place {place}?", "What rule is there for places like {place}?",
                     "What is special about {place}?"),
    "q.rule_container": ("What is the rule about the container {container}?", "What rule is there for containers like {container}?",
                         "What happens to things put in {container}?"),
    "q.yn_at": ("Is {object} at {place}?", "Is {object} at {place} now?", "Can {object} be found at {place}?"),
    "q.yn_has": ("Does {person} have {object}?", "Is {person} holding {object}?", "Does {person} have {object} now?"),
    "q.yn_in": ("Is {object} in {container}?", "Is {object} inside {container}?", "Is {object} in {container} now?"),
}
# style -> one pattern per teacher bank, in TEACHER_BANKS order.
FALLBACK_TEACHER: dict[str, tuple[str, ...]] = {
    "plain": ("Here is a fact. {fact}", "Remember this: {fact}", "Answer this question. {question}", "Your answer was right.",
              "Your answer was wrong. {correction}", "Let me show you a rule. {rule}", "Watch what happens next. {event}",
              "That showed the rule. {rule}", "Something has changed. {fact}", "Let me ask about something from earlier. {question}"),
    "cheerful": ("Good news! {fact}", "Here is a fun thing to remember! {fact}", "Hooray, a quiz! {question}", "Yes, great job!",
                 "Oops, close, but that is not right! {correction}", "Here comes a fun rule! {rule}", "Ooh, look at this! {event}",
                 "Hooray, now you know the rule! {rule}", "Oh, look, a change! {fact}", "Fun question from before! {question}"),
    "terse": ("Fact: {fact}", "Remember: {fact}", "Question: {question}", "Correct.", "Wrong. {correction}", "Rule: {rule}",
              "Step: {event}", "So: {rule}", "Changed: {fact}", "Earlier: {question}"),
    "storyteller": ("Listen to my tale. {fact}", "Keep this part of the tale in mind. {fact}", "And so the tale asks. {question}",
                    "And that was the right answer.", "Ah, but in the tale that answer was wrong. {correction}", "This tale has a rule. {rule}",
                    "The tale goes on. {event}", "And that is how the rule goes. {rule}", "The tale takes a turn. {fact}",
                    "Think back to the start of the tale. {question}"),
    "formal": ("Please note the following. {fact}", "Kindly commit this to memory. {fact}", "Kindly answer the following. {question}",
               "That is quite correct.", "That answer is incorrect. {correction}", "Allow me to demonstrate a rule. {rule}",
               "Observe the next step. {event}", "This concludes the demonstration. {rule}", "Please note a change. {fact}",
               "Kindly consider an earlier matter. {question}"),
    "questioning": ("Did you know this? {fact}", "Will you remember this for me? {fact}", "Can you work this out? {question}",
                    "Right you are, indeed.", "Hmm, was that right? It was not. {correction}", "Shall we look at a rule? {rule}",
                    "What do you see here? {event}", "Do you see the rule now? {rule}", "Did you notice the change? {fact}",
                    "Can you recall the earlier part? {question}"),
    "childlike": ("Ooh, listen! {fact}", "Oh, keep this in your head! {fact}", "I want to know! {question}", "Yay, you got it!",
                  "Nope, that is not it! {correction}", "Ooh, a rule! {rule}", "Look look! {event}", "See, that is the rule! {rule}",
                  "Whoa, it is different now! {fact}", "Can you remember this bit? {question}"),
    "grandparent": ("Let me tell you, dear. {fact}", "Hold on to this, my dear. {fact}", "Tell me, sweetheart. {question}",
                    "That's right, my dear.", "Not quite, my dear. {correction}", "Come sit, dear, and learn a rule. {rule}",
                    "Now watch closely, dear. {event}", "And that, my dear, is the rule. {rule}", "Things have changed, dear. {fact}",
                    "Let us think back a while, dear. {question}"),
    "bossy": ("Listen up. {fact}", "Memorise this now. {fact}", "Answer me now. {question}", "Right. Keep going.",
              "No. Listen. {correction}", "Learn this rule. {rule}", "Watch carefully. {event}", "That is the rule. Learn it. {rule}",
              "Update your notes. {fact}", "Answer this from earlier. {question}"),
    "poetic": ("Hear this, soft and true. {fact}", "Keep this close, like a song. {fact}", "A question drifts by. {question}",
               "True as a song.", "Alas, that answer was wrong. {correction}", "A rule hums softly here. {rule}", "See it unfold. {event}",
               "Thus the rule is shown. {rule}", "The tide has turned. {fact}", "An echo of a question. {question}"),
}

_SLOT = re.compile(r"\{([a-z0-9_]+)\}")
_CAPS = re.compile(r"(^|[.!?]\s+)([a-z])")
_BREAKS = re.compile(r"[\n.!?;]+")


def _hash(text: str) -> int:
    return int.from_bytes(hashlib.blake2b(text.encode(), digest_size=8).digest(), "big")


def check_slots(bank: str, text: str) -> None:
    """ValueError unless `text` uses exactly the bank's placeholders, each once."""
    if bank not in BANK_SLOTS:
        raise ValueError(f"unknown bank {bank!r}")
    found = _SLOT.findall(text)
    if sorted(found) != sorted(BANK_SLOTS[bank]) or "{" in _SLOT.sub("", text) or "}" in _SLOT.sub("", text):
        raise ValueError(f"pattern {text!r} of {bank} must use exactly {BANK_SLOTS[bank]} once each, found {found}")


def skeleton(text: str) -> tuple[str, ...]:
    """The pattern as the audit reads it: literal words, with None for each field."""
    parts: list[Any] = []
    for literal, name, _spec, _conv in string.Formatter().parse(text):
        parts.extend(re.findall(r"[^\W_]+", literal.casefold()))
        if name is not None:
            parts.append("\0")
    return tuple(parts)


class PatternSource:
    """Every pattern with its id, bank, split and (teacher banks) style."""

    def __init__(self, rows: Iterable[Mapping[str, Any]], style_split: Mapping[str, str], version: str) -> None:
        self.version = version
        self.style_split = dict(style_split)
        self.text: dict[str, str] = {}
        self.split: dict[str, str] = {}
        self.bank: dict[str, str] = {}
        self.style: dict[str, str] = {}
        pools: dict[tuple[str, str], list[str]] = {}
        for row in rows:
            pid, bank, text, split = row["id"], row["bank"], row["text"], row["split"]
            check_slots(bank, text)
            if pid in self.text:
                raise ValueError(f"pattern id {pid!r} appears twice")
            if bank in TEACHER_BANKS:
                style = row["style"]
                if self.style_split[style] != split:
                    raise ValueError(f"teacher pattern {pid} is in {split} but style {style!r} is in {self.style_split[style]}")
                self.style[pid] = style
                key = (bank, style)
            else:
                key = (bank, split)
            self.text[pid], self.split[pid], self.bank[pid] = text, split, bank
            pools.setdefault(key, []).append(pid)
        self.pools = {key: tuple(sorted(ids)) for key, ids in pools.items()}

    @classmethod
    def fallback(cls) -> "PatternSource":
        """The hand-written patterns, split like `learnlab.patterns.assign_splits`."""
        return cls(_fallback_rows(), _style_split(), FALLBACK_VERSION)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "PatternSource":
        """bank-v1.json when it exists; any (bank, split) or (bank, style) it lacks is filled from the fallback."""
        path = Path(path) if path is not None else BANK_PATH
        if not path.exists():
            return cls.fallback()
        data = json.loads(path.read_text(encoding="utf-8"))
        families = data["manifest"]["families"]
        styles = families["teacher_style"]["assignment"]
        assigned = families["template"]["assignment"]
        rows = []
        for bank, by_split in data["banks"].items():
            if bank not in BANK_SLOTS:
                continue
            for split, entries in by_split.items():
                for entry in entries:
                    if assigned.get(entry["id"]) != split:
                        raise ValueError(f"{path}: pattern {entry['id']} listed under {split} but assigned {assigned.get(entry['id'])}")
                    rows.append({**entry, "bank": bank, "split": split})
        # A bank missing any split (or teacher style) takes the fallback for the whole bank: mixing the two
        # let a fallback pattern in one split overlap a written pattern in another (held-out audit leak).
        have = {(r["bank"], r["style"] if r["bank"] in TEACHER_BANKS else r["split"]) for r in rows}
        fallback = _fallback_rows(styles)
        needed = {(r["bank"], r["style"] if r["bank"] in TEACHER_BANKS else r["split"]) for r in fallback}
        partial = {bank for bank, key in needed - have}
        rows = [r for r in rows if r["bank"] not in partial]
        fill = [r for r in fallback if r["bank"] in partial]
        digest = hashlib.sha256(json.dumps([data["manifest_digest"], sorted(r["id"] for r in fill)]).encode()).hexdigest()[:12]
        return cls(rows + fill, styles, f"{data['version']}+fill:{digest}" if fill else f"{data['version']}:{data['manifest_digest'][:12]}")

    def families(self) -> dict[str, tuple[str, dict[str, str]]]:
        """axis -> (version, item -> split): the template and teacher-style families."""
        return {"template": (self.version, dict(self.split)), "teacher_style": (self.version, dict(self.style_split))}

    def ids(self, bank: str, split: str, style: Optional[str] = None) -> tuple[str, ...]:
        key = (bank, style) if bank in TEACHER_BANKS else (bank, split)
        pool = self.pools.get(key, ())
        if not pool:
            raise KeyError(f"no {split} patterns for {bank}" + (f" in style {style!r}" if style else ""))
        return pool


def _style_split() -> dict[str, str]:
    return assign_ranked("teacher_style", vocab.STYLES, salt=vocab.MANIFEST_VERSION, fractions=vocab.SPLIT_FRACTIONS)


def _fallback_rows(style_split: Optional[Mapping[str, str]] = None) -> list[dict[str, str]]:
    styles = dict(style_split) if style_split is not None else _style_split()
    rows = []
    for bank, texts in FALLBACK.items():
        ids = [f"fb-{bank}-{i}" for i in range(len(texts))]
        ranked = assign_ranked("template", ids, salt=vocab.MANIFEST_VERSION, fractions=vocab.SPLIT_FRACTIONS)
        rows += [{"id": pid, "bank": bank, "text": text, "split": ranked[pid], "writer": "fallback"} for pid, text in zip(ids, texts)]
    for style, texts in FALLBACK_TEACHER.items():
        if style not in styles:
            continue
        rows += [{"id": f"fb-{bank}-{style}", "bank": bank, "text": text, "split": styles[style], "style": style, "writer": "fallback"}
                 for bank, text in zip(TEACHER_BANKS, texts)]
    return rows


def village_registry(
    source: PatternSource,
    families: Optional[Mapping[str, tuple[str, Mapping[str, str]]]] = None,
    *,
    salt: str = vocab.MANIFEST_VERSION,
    fractions: Sequence[float] = vocab.SPLIT_FRACTIONS,
) -> SplitRegistry:
    """A registry with the pattern families frozen, plus `families` (e.g. the world's rule families)."""
    fixed = {**source.families(), **dict(families or {})}
    manifest = SplitManifest(
        salt=salt, fractions=tuple(fractions),
        families=tuple(FamilyManifest(axis, version, tuple(assignment.items())) for axis, (version, assignment) in fixed.items()),
        canary=hash_canary(salt, fractions),
    )
    return SplitRegistry.from_manifest(manifest)


_PLURALS = frozenset(vocab.PLURAL.values())


class Line:
    """One rendered stream line with what produced it."""

    __slots__ = ("text", "templates", "units", "style", "question")

    def __init__(self, text: str, templates: list[str], units: list[str], style: Optional[str],
                 question: Optional[str]) -> None:
        self.text, self.templates, self.units, self.style, self.question = text, templates, units, style, question


class Renderer:
    """Renders one visit's records in order, tracking each object's current colour.

    Pattern choices hash (visit key, record line, bank) for world and teacher
    lines and (question id and twin id) for question lines, so counterfactual
    twins ask with the same wording. Effects of event records (silent ones
    and events inside teacher records included) are applied after rendering
    them: an object that turned green is "the red cup" in the sentence saying
    so and "the green cup" after. Only ev.recoloured changes a surface form.
    """

    def __init__(self, source: PatternSource, visit: Mapping[str, Any], view: SplitView,
                 *, key: Optional[str] = None) -> None:
        self.source, self.view, self.split = source, view, view.split
        self.key = str(key if key is not None else visit.get("render_seed", visit.get("seed", visit["id"])))
        self.entities: Mapping[str, Mapping[str, Any]] = visit["entities"]
        self.default_style: Optional[str] = visit.get("style")
        self.colour = {eid: entity.get("colour") for eid, entity in self.entities.items()}
        self._templates: list[str] = []
        self._units: list[str] = []
        labels: dict[tuple, str] = {}
        for eid, entity in self.entities.items():
            label = self._label(eid)
            if label in labels:
                raise ValueError(f"entities {labels[label]} and {eid} would both render as {self.surface_of(eid)!r}")
            labels[label] = eid

    def _label(self, eid: str) -> tuple:
        entity = self.entities[eid]
        return (entity["type"], entity["kind"], self.colour[eid] if entity["type"] == "object" else None)

    def surface_of(self, eid: str) -> str:
        entity = self.entities[eid]
        colour = self.colour[eid] if entity["type"] == "object" else None
        return f"the {colour} {entity['kind']}" if colour else f"the {entity['kind']}"

    def surface(self, name: str, value: Any) -> str:
        if name in PERSON_SLOTS:
            return str(value)
        if name in ("place", "place2", "container", "object"):
            return self.surface_of(value)
        if name == "object_kind":
            if value in vocab.PLURAL:
                return vocab.PLURAL[value]
            if value in _PLURALS:
                return value
            raise KeyError(f"unknown object kind {value!r}")
        if name == "item":
            kind = self.entities[value]["kind"] if value in self.entities else str(value)
            return ("an " if kind[:1] in "aeiou" else "a ") + kind
        if name == "count" and isinstance(value, int) and not isinstance(value, bool):
            return vocab.NUMBER_WORDS[value]
        return str(value)

    def sentence(self, record: Mapping[str, Any], salt: str, *, style: Optional[str] = None, clause: bool = False) -> str:
        """Fill one pattern for `record` (nested sentences recursively)."""
        bank = record["bank"]
        if bank in TEACHER_BANKS:
            style = record.get("style") or style or self.default_style
            if not style:
                raise ValueError(f"teacher record {bank} has no style and the visit has no default style")
            self.view.use("teacher_style", style)
            pool = self.source.ids(bank, self.split, style)
        else:
            pool = self.source.ids(bank, self.split)
            if clause:  # a clause reads best when it starts with its subject
                pool = tuple(pid for pid in pool if self.source.text[pid].startswith("{")) or pool
        pid = pool[_hash(f"{salt}|{bank}") % len(pool)]
        self.view.use("template", pid)
        self._templates.append(pid)
        text = self.source.text[pid]
        slots = record.get("slots") or {}
        values: dict[str, str] = {}
        masked: dict[str, str] = {}
        for name in BANK_SLOTS[bank]:
            if name in NESTED_SLOTS:
                nested = slots[name] if name in slots else record.get("inner")
                if nested is None:
                    raise ValueError(f"{bank} needs a nested {name} (slot or inner record)")
                values[name] = (self.sentence(nested, f"{salt}|{name}", style=style, clause=name == "action")
                                if isinstance(nested, Mapping) else str(nested))
                masked[name] = MASK
            else:
                if name not in slots:
                    raise ValueError(f"{bank} record lacks slot {name!r}")
                values[name] = masked[name] = self.surface(name, slots[name])
        self._units.append(_BREAKS.sub(" ", _SLOT.sub(lambda m: masked[m.group(1)], text)).strip())
        out = _SLOT.sub(lambda m: values[m.group(1)], text)
        if clause:
            out = out.rstrip(".!?")
            return out if text.startswith("{") else out[:1].lower() + out[1:]
        return _CAPS.sub(lambda m: m.group(1) + m.group(2).upper(), out)

    def line(self, record: Mapping[str, Any]) -> Optional[Line]:
        """The stream line for one record, or None for a silent record."""
        self._templates, self._units = [], []
        try:
            if record.get("silent"):
                return None
            kind = record["kind"]
            salt = f"{self.key}|{record['line']}"
            if kind in ("event", "rule"):
                return Line("[world] " + self.sentence(record, salt), self._templates, self._units, None, None)
            if kind == "teacher":
                inner = record.get("inner")
                if isinstance(inner, Mapping) and inner.get("kind") == "question":
                    return self._question(inner, record)
                style = record.get("style") or self.default_style
                return Line("[teacher] " + self.sentence(record, salt, style=style), self._templates, self._units, style, None)
            if kind == "question":
                return self._question(record, None)
            raise ValueError(f"unknown record kind {kind!r}")
        finally:
            for event in (record, record.get("inner")):  # a demonstrated event (t.demo_step) happens too
                if isinstance(event, Mapping) and event.get("kind") == "event":
                    self._apply(event)

    def _question(self, question: Mapping[str, Any], wrapper: Optional[Mapping[str, Any]]) -> Line:
        answer = str(question["answer"])
        if not answer or "\n" in answer or "[" in answer:
            raise ValueError(f"question {question.get('id')}: answer {answer!r} cannot be written into the stream")
        for name, expected in (question.get("surface") or {}).items():  # the oracle's own surface forms
            if self.surface(name, question["slots"][name]) != expected:
                raise ValueError(f"question {question['id']}: {name} renders as {self.surface(name, question['slots'][name])!r}, "
                                 f"the oracle says {expected!r}")
        pair = "|".join(sorted(str(x) for x in (question["id"], question.get("twin")) if x))
        salt = f"q|{pair}"
        style = (wrapper or {}).get("style") or question.get("style") or self.default_style
        if wrapper is None:
            text = self.sentence(question, salt)
        else:
            text = self.sentence({**wrapper, "inner": question}, salt, style=style)
        feedback = self.sentence({"bank": "t.right"}, salt + "|feedback", style=style)
        return Line(f"[question] {text} [answer] {answer} [feedback] {feedback}", self._templates, self._units, style, text)

    def _apply(self, record: Mapping[str, Any]) -> None:
        if record.get("bank") == "ev.recoloured":
            eid = record["slots"]["object"]
            self.colour[eid] = record["slots"]["colour"]
            label = self._label(eid)
            clash = [other for other in self.entities if other != eid and self._label(other) == label]
            if clash:
                raise ValueError(f"after recolouring, {eid} and {clash[0]} would both render as {self.surface_of(eid)!r}")


__all__ = [
    "BANK_PATH", "BANK_SLOTS", "FALLBACK", "FALLBACK_TEACHER", "FALLBACK_VERSION", "Line", "MASK", "PatternSource",
    "Renderer", "TEACHER_BANKS", "check_slots", "skeleton", "village_registry",
]
