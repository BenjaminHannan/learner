"""Village pattern banks: vocabulary, mechanical checks, parsing and the resumable driver (fake models only)."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import itertools
import json
from pathlib import Path
import random
import re
import tempfile
import unittest

from learnlab import patterns as P
from learnlab.splits import SPLITS, SplitManifest, SplitRegistry

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gen_patterns.py"
_spec = importlib.util.spec_from_file_location("gen_patterns", _SCRIPT)
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

ADVERBS = (
    "slowly", "quickly", "quietly", "carefully", "happily", "calmly", "gladly", "softly", "gently", "boldly",
    "bravely", "proudly", "eagerly", "loudly", "neatly", "kindly", "firmly", "lightly", "safely", "simply",
)


# Red team: patterns that add a fact or change the meaning. Every one must be rejected mechanically.
NARRATION_BAD = (
    ('ev.go', '{person} went to {place} with Tosa.'), ('ev.go', '{person} went to {place} with her friend.'),
    ('ev.go', 'Mira and {person} went to {place}.'), ('ev.go', '{person} walked home to {place}.'),
    ('ev.go', '{person} went upstairs at {place}.'), ('ev.go', '{person} went to the village square past {place}.'),
    ('ev.go', '{person} went to {place} at dawn.'), ('ev.go', 'Later that night, {person} went to {place}.'),
    ('ev.go', '{person} went to {place} on Sunday.'), ('ev.go', '{person} went to {place} twice.'),
    ('ev.go', '{person} went back to {place}.'), ('ev.go', '{person} went to {place} for the first time.'),
    ('ev.go', '{person} went to {place} with the others.'), ('ev.go', '{person} went to {place} alone.'),
    ('ev.go', '{person} tried to go to {place}.'), ('ev.go', '{person} almost went to {place}.'),
    ('ev.go', '{person} wanted to go to {place}.'), ('ev.go', "{person} hadn't gone to {place}."),
    ('ev.go', '{person} stepped toward {place}.'), ('ev.go', '{person} said they went to {place}.'),
    ('ev.go', '{person} went to {place}; it was cold.'), ('ev.go', '{person} went to {place}: slowly.'),
    ('ev.go', '{person} went to {place} - and saw a pal.'), ('ev.go', 'Tired, {person} went to {place}.'),
    ('ev.go', '{person} went to {place} by boat.'), ('ev.go', '{person} would go to {place}.'),
    ('ev.go', '{person} went to {place} after lunch.'), ('ev.go', '{person} went to {place} as usual.'),
    ('ev.go', '{Person} went to {place}.'), ('ev.go', '{person} went to { place }.'),
    ('ev.go', '{person} went to {{place}}.'), ('ev.go', '{person} went to {place} and {place}.'),
    ('ev.go', '{person} went to {place2}.'), ('ev.go', '{p\u0435rson} went to {place}.'),
    ('ev.go', '{person} went t\u043e {place}.'), ('ev.go', '{person} went to \uff5bplace\uff5d.'),
    ('ev.go', '{person} went to {place}\u200b.'), ('ev.pick_up', '{person} picked up {object} and the other one.'),
    ('ev.pick_up', '{person} picked up {object} with her left hand.'),
    ('ev.pick_up', '{person} tried to pick up {object}.'),
    ('ev.pick_up', '{person} picked up {object}, which was theirs.'),
    ('ev.pick_up', '{person} picked up {object} again.'),
    ('ev.pick_up', '{person} picked up {object} and some cups.'), ('ev.pick_up', "{person} didn't pick up {object}."),
    ('ev.pick_up', '{person} picked up {object}. It was heavy.'),
    ('ev.pick_up', '{person} picked up the broken {object}.'),
    ('ev.pick_up', '{person} picked up {object} and both plates.'),
    ('ev.pick_up', '{person} picked up {object} on Monday.'), ('ev.pick_up', '{person} could pick up {object}.'),
    ('ev.give', '{giver} lent {object} to {receiver}.'), ('ev.give', '{giver} gave {object} back to {receiver}.'),
    ('ev.give', '{giver} gave {object} to {receiver}, who owns it now.'),
    ('ev.give', '{giver} sold {object} to {receiver}.'),
    ('ev.give', '{giver} gave {object} to {receiver} as a gift.'),
    ('ev.put_in', '{person} hid {object} in {container}.'),
    ('ev.put_in', '{person} put {object} in {container} and locked it.'),
    ('ev.put_in', '{person} put {object} in the {container}.'),
    ('ev.fail_open', '{person} tried to open {container}, and it opened.'),
    ('ev.fail_open', '{person} tried to open {container} and did.'),
    ('ev.fail_open', '{person} did not try to open {container}.'),
    ('ev.fail_open', '{person} never tried to open {container}.'),
    ('ev.fail_open', '{person} tried to open {container}, but it was locked.'),
    ('ev.fail_open', '{person} could not open {container} at night.'),
    ('ev.fail_open', '{person} could not open {container}, so Rami did.'),
    ('ev.fail_open', '{person} could not open {container} at first, but then it opened.'),
    ('ev.fail_pick_up', '{person} tried to pick up {object}.'),
    ('ev.fail_pick_up', '{person} could not pick up {object} because it was too heavy.'),
    ('ev.fail_put_in', '{person} tried to put {object} in {container} with care.'),
    ('ev.fail_put_in', '{person} could not put {object} in {container}, as it was full.'),
    ('ev.time', 'It became {time} again.'), ('ev.time', 'It became {time} on Sunday.'),
    ('ev.time', 'It became {time} the next day.'), ('ev.time', 'It was almost {time}.'),
    ('ev.time', 'It was not {time} yet.'), ('ev.time', 'Soon it will be {time}.'),
    ('ev.new_day', 'A new week began.'), ('ev.new_day', 'It was Monday.'), ('ev.new_day', 'Two days went by.'),
    ('ev.new_day', 'A new day began, and it rained.'), ('ev.new_day', 'A new day began for Kelo.'),
    ('ev.breaks', '{object} fell and broke.'), ('ev.breaks', '{object} broke into two pieces.'),
    ('ev.breaks', 'Rami broke {object}.'), ('ev.breaks', '{object} almost broke.'),
    ('ev.breaks', '{object} did not break.'), ('ev.breaks', '{object} broke again.'),
    ('ev.follows', '{person} followed {leader} and a friend to {place}.'),
    ('ev.follows', '{person} followed {leader} to {place} as usual.'),
    ('ev.moved_by_place', '{object} was stolen from {place} and taken to {place2}.'),
    ('ev.returned', '{object} went back to {person}, who lost it at the mill.'),
    ('ev.recoloured', '{object} turned {colour} and gold.'), ('ev.recoloured', '{object} turned a little {colour}.'),
    ('ev.recoloured', '{object} turned {colour} forever.'),
    ('ev.traded', '{person} traded {count} {object_kind} for {item} and two more.'),
    ('ev.swap', '{person} and {person_b} swapped hats.'), ('ev.swap', '{person} and {person_b} almost swapped.'),
)
RULE_BAD = (
    ('rule.R1_material', 'Some things made of {material} break when put down.'),
    ('rule.R1_material', 'Most things made of {material} break when they are put down.'),
    ('rule.R1_material', 'Things made of {material} sometimes break when put down.'),
    ('rule.R1_material', 'Things made of {material} break when put down twice.'),
    ('rule.R1_material', 'Things made of {material} break when put down at night.'),
    ('rule.R1_material', 'Things made of {material} break unless they are put down gently.'),
    ('rule.R1_category', '{category} made of glass break when put down.'),
    ('rule.R1_category', 'Old {category} break when they are put down.'),
    ('rule.R1_category', '{category} might break when they are put down.'),
    ('rule.R2', '{person} often follows {leader}.'), ('rule.R2', '{person} follows {leader} and a dog.'),
    ('rule.R2', '{person} follows {leader} to the barn.'), ('rule.R2', '{person} follows {leader}, except at night.'),
    ('rule.R2', '{person} used to follow {leader}.'), ('rule.R2', '{person} must follow {leader}.'),
    ('rule.R2', '{person} wants to follow {leader}.'), ('rule.R2', 'Mira and {person} always follow {leader}.'),
    ('rule.R2', '{person} follows {leader} home.'), ('rule.R2', 'They say {person} always follows {leader}.'),
    ('rule.R3', 'Things left at {place} are moved to {place2} every {time}, but only on Mondays.'),
    ('rule.R3', 'Things left at {place} are moved to {place2} by a man each {time}.'),
    ('rule.R3', 'Things left at {place} go to {place2} every other day when it is {time}.'),
    ('rule.R3', 'Things left at {place} go to {place2} at {time}.'),
    ('rule.R4', 'Lost things go back to their owners each {time}, if they are not broken.'),
    ('rule.R4', 'Lost toys go back to their owners every {time}.'),
    ('rule.R4', 'Lost things usually go back to their owners every {time}.'),
    ('rule.R5', 'Things put in {container} turn {colour} and break.'),
    ('rule.R5', 'Things put in {container} turn {colour} after a week.'),
    ('rule.R5', 'Some things put in {container} turn {colour}.'),
    ('rule.R6', 'Only {person} and a friend can open {container}.'),
    ('rule.R6', 'Only {person} can open {container} at night.'),
    ('rule.R6', 'Only {person} can open {container} with a key.'), ('rule.R6', '{person} cannot open {container}.'),
    ('rule.R6', '{person} can open {container}.'),
    ('rule.R7', 'Every day, {person} goes to {place} when it is {time}, with a friend.'),
    ('rule.R7', '{person} sometimes goes to {place} when it is {time}.'),
    ('rule.R7', 'Every week, {person} goes to {place} when it is {time}.'),
    ('rule.R8', 'At {place}, {count} {object_kind} can be traded for {item} and a cake.'),
    ('rule.R8', 'At {place}, {count} {object_kind} could be traded for {item}.'),
    ('rule.R8', 'At {place}, {count} old {object_kind} buy {item}.'),
    ('rule.R8', 'At {place}, {count} {object_kind} or more buy {item}.'),
    ('rule.R8', 'At {place}, at least {count} {object_kind} buy {item}.'),
)
TEACHER_BAD = (
    ('t.state', 'Maybe this is true. {fact}'), ('t.state', 'Here is something false. {fact}'),
    ('t.state', 'I think this is true. {fact}'), ('t.state', 'My friend says this. {fact}'),
    ('t.state', 'Yesterday I saw this. {fact}'), ('t.state', 'Here is something true about the barn. {fact}'),
    ('t.state', 'Here is a joke. {fact}'), ('t.state', 'Listen, child. {fact}'),
    ('t.state', 'His words were these. {fact}'), ('t.state', 'Here is a lie: {fact}'),
    ('t.remember', 'Remember this for tomorrow: {fact}'), ('t.remember', 'Forget this: {fact}'),
    ('t.remember', 'Remember this, but do not tell Rami. {fact}'),
    ('t.ask', 'Answer this question, Tosa. {question}'), ('t.ask', 'Ask your friend. {question}'),
    ('t.ask', 'Answer this one at night. {question}'), ('t.right', 'You were right yesterday.'),
    ('t.right', 'Your answer was right again.'), ('t.right', 'Your answer was almost right.'),
    ('t.right', 'Your answer was wrong.'), ('t.right', 'Your answer was not right.'),
    ('t.right', 'Right, and so was his.'), ('t.wrong', 'Your answer was right. {correction}'),
    ('t.wrong', 'Good job! {correction}'), ('t.wrong', 'Your answer was wrong, like hers. {correction}'),
    ('t.demo_intro', 'I will show you a rule that is not true. {rule}'),
    ('t.demo_intro', 'Here is a rule from the other village. {rule}'),
    ('t.demo_step', 'Watch what happens next at the mill. {event}'),
    ('t.demo_step', 'Watch what happened yesterday. {event}'), ('t.demo_step', 'Watch what Tosa does. {event}'),
    ('t.demo_outro', 'That showed the rule is false. {rule}'), ('t.demo_outro', 'That broke the rule. {rule}'),
    ('t.change', 'Nothing has changed. {fact}'), ('t.change', 'Something changed at the barn. {fact}'),
    ('t.change', 'Something has changed since yesterday. {fact}'),
    ('t.quiz_later', 'Let me ask about something from last week. {question}'),
    ('t.quiz_later', 'Let me ask about something from this morning. {question}'),
    ('t.state', '{fact} Remember that {fact}'), ('t.state', 'Here is something true: {fact'),
)
QUESTION_BAD = (
    ('q.where_object', 'Where is {object} hidden?'), ('q.where_object', 'Where did Rami put {object}?'),
    ('q.where_object', 'Where is the other {object}?'), ('q.where_object', 'Where are {object} and the cup?'),
    ('q.where_object', 'Where is {object} today?'), ('q.where_object', 'Where is {object} usually?'),
    ('q.where_object', 'Where is {object}.'), ('q.where_object', 'Where is {object}? Who has it?'),
    ('q.where_person', 'Where did {person} go with her friend?'), ('q.where_person', 'Where is {person} hiding?'),
    ('q.who_has', 'Who stole {object}?'), ('q.who_has', 'Who has {object} and the key?'),
    ('q.who_has', 'Who has {object} now that it broke?'), ('q.who_has', 'Which boy has {object}?'),
    ('q.who_has', 'Whose is {object}?'), ('q.in_container', 'What else is in {container}?'),
    ('q.in_container', 'Is {container} empty?'), ('q.in_container', 'What did Tosa put in {container}?'),
    ('q.where_before', 'Where was {object} before it was stolen?'),
    ('q.where_before', 'Where was {object} last week?'),
    ('q.count_at', 'How many more {object_kind} are at {place}?'),
    ('q.count_at', 'How many {object_kind} are at {place} today?'),
    ('q.count_held', 'How many {object_kind} does {person} have in the box?'),
    ('q.compare_count', 'Are there twice as many {object_kind} at {place} as at {place2}?'),
    ('q.direction', 'How far is {place2} from {place}?'), ('q.direction', 'Is {place2} north of {place}?'),
    ('q.next_to', 'What is next to {place} and the barn?'), ('q.what_if', 'What would happen if {action} again?'),
    ('q.what_if', 'What would happen if {action} at night?'), ('q.why_at', 'Why did Kelo hide {object} at {place}?'),
    ('q.why_at', 'Why is {object} still at {place}?'), ('q.why_at', 'Why was {object} left at {place} by her?'),
    ('q.plan_get', 'How could {person} steal {object}?'), ('q.plan_get', 'How could {person} get {object} back?'),
    ('q.rule_material', 'Why do things made of {material} break?'),
    ('q.rule_category', 'What is the rule about {category} at night?'),
    ('q.rule_person', 'What is the rule about {person} and her friend?'),
    ('q.yn_at', 'Is {object} still at {place}?'), ('q.yn_at', "Isn't {object} at {place}?"),
    ('q.yn_has', 'Does {person} have {object} and a hat?'), ('q.yn_has', 'Did {person} steal {object}?'),
    ('q.yn_has', 'Does {object} belong to {person}?'), ('q.yn_in', 'Is {object} hidden in {container}?'),
    ('q.yn_in', 'Is {object} in {container} with the key?'), ('q.where_person', 'Where is {person} going 2morrow?'),
    ('q.where_object', 'Where is "{object}"?'),
)
# Meaning changes no word list can see (open-class verbs and nouns, lowercase names, inverted logic,
# presuppositions, teacher sentence starts). They pass check_pattern by design; the cross-check must say no.
CROSSCHECK_ONLY = (
    ('ev.go', '{person} went to {place} and slept.'), ('ev.go', '{person} went to {place} to find a spade.'),
    ('ev.go', '{person} went to {place} with mira.'), ('ev.go', "{person}'s helper went to {place}."),
    ('ev.fail_open', '{person} could not wait and opened {container}.'),
    ('ev.carry', '{person} carried {container} to {place}, but left everything inside behind.'),
    ('rule.R6', 'No one can open {container}, not even {person}.'), ('t.state', 'Tosa told me this. {fact}'),
    ('q.why_at', 'Who put {object} at {place}?'), ('q.rule_place', 'What happens to things left at {place}?'),
)
# Varied good patterns that must pass.
GOOD = (
    ('ev.go', '{person} walked over to {place}.'), ('ev.go', 'Quickly, {person} ran to {place}.'),
    ('ev.go', '{person} made their way to {place}.'), ('ev.go', 'After that, {person} headed to {place}.'),
    ('ev.pick_up', '{object} was picked up by {person}.'), ('ev.pick_up', '{person} took hold of {object}.'),
    ('ev.put_down', '{person} set {object} down at {place}.'),
    ('ev.put_down', 'At {place}, {person} put {object} down.'),
    ('ev.give', '{receiver} was given {object} by {giver}.'),
    ('ev.give', '{giver} passed {object} over to {receiver}.'),
    ('ev.put_in', '{person} slipped {object} into {container}.'),
    ('ev.take_out', 'Out of {container}, {person} took {object}.'),
    ('ev.open', '{container} was opened by {person}.'), ('ev.close', '{person} pushed {container} shut.'),
    ('ev.carry', '{person} carried {container} and everything in it to {place}.'),
    ('ev.swap', '{person} and {person_b} swapped what they held with each other.'),
    ('ev.time', 'Soon, {time} arrived.'), ('ev.new_day', 'The sun rose on a new day.'),
    ('ev.fail_open', '{person} pulled at {container}, but it stayed closed.'),
    ('ev.fail_pick_up', '{person} reached for {object} but failed to pick it up.'),
    ('ev.fail_put_in', '{person} tried to put {object} into {container}, but it would not go in.'),
    ('ev.breaks', 'Then {object} broke apart.'),
    ('ev.follows', '{leader} went to {place}, and {person} came along behind.'),
    ('ev.moved_by_place', '{object} had been left at {place}, but now it was at {place2}.'),
    ('ev.returned', '{object} made its way back to {person}, its owner.'),
    ('ev.recoloured', '{object} slowly changed to {colour}.'),
    ('ev.traded', '{person} bought {item} with {count} {object_kind}.'),
    ('rule.R1_material', 'Anything made of {material} breaks if it is put down.'),
    ('rule.R1_category', 'Put {category} down, and they break.'),
    ('rule.R2', '{person} follows {leader} everywhere.'),
    ('rule.R3', 'Once it is {time}, things left at {place} end up at {place2}.'),
    ('rule.R4', 'Each {time}, lost things find their way back to their owners.'),
    ('rule.R5', 'Whatever goes into {container} becomes {colour}.'),
    ('rule.R6', 'No one but {person} can open {container}.'),
    ('rule.R7', '{person} walks to {place} each day when {time} comes.'),
    ('rule.R8', 'At {place}, {item} costs {count} {object_kind}.'), ('t.state', 'Listen closely, little one. {fact}'),
    ('t.remember', 'I want you to keep this in mind: {fact}'), ('t.ask', 'Try to answer this. {question}'),
    ('t.right', 'Good job, that is right!'), ('t.wrong', 'Hmm, that is not quite right. {correction}'),
    ('t.wrong', 'Oops, that was a mistake. {correction}'), ('t.demo_intro', 'Here comes a rule for you. {rule}'),
    ('t.demo_step', 'Keep your eyes open. {event}'), ('t.demo_outro', 'And that is how the rule works. {rule}'),
    ('t.change', 'Things are different now. {fact}'),
    ('t.quiz_later', 'Do you recall this one from earlier? {question}'),
    ('q.where_object', 'Where can {object} be found now?'), ('q.who_has', 'Who is holding {object} right now?'),
    ('q.direction', 'Which way do you go from {place} to get to {place2}?'),
    ('q.next_to', 'What sits right next to {place}?'), ('q.what_if', 'If {action}, what would happen next?'),
    ('q.where_person', 'Do you know where {person} is?'),
    ('q.count_held', 'How many {object_kind} does {person} hold?'),
    ('q.where_before', 'Where was {object} at first?'),
    ('q.compare_count', 'Which place has more {object_kind}, {place} or {place2}?'),
    ('q.yn_in', 'Is {object} inside {container} right now?'), ('ev.go', 'Off went {person} to {place}.'),
    ('ev.go', '{person} arrived at {place}.'), ('ev.put_down', '{person} laid {object} down at {place}.'),
    ('ev.give', '{giver} handed {receiver} {object}.'),
    ('ev.put_in', 'Into {container} went {object}, put there by {person}.'),
    ('ev.open', '{person} lifted the lid of {container}.'),
    ('ev.carry', '{person} brought {container}, with all it held, to {place}.'),
    ('ev.swap', '{person} and {person_b} traded the things they held.'), ('ev.time', 'The time was {time}.'),
    ('ev.new_day', 'Morning came, and a new day began.'),
    ('ev.fail_pick_up', '{person} tried hard to lift {object} but failed.'),
    ('ev.fail_pick_up', '{person} could not lift {object}.'), ('ev.breaks', '{object} shattered.'),
    ('ev.follows', '{person} tagged along behind {leader} to {place}.'),
    ('ev.returned', '{object} came back to {person}, who owns it.'),
    ('ev.recoloured', 'The colour of {object} changed to {colour}.'),
    ('rule.R1_category', 'If you put down {category}, they break.'),
    ('rule.R1_material', 'Anything made of {material} will break if it is put down.'),
    ('rule.R6', 'Nobody but {person} can open {container}.'),
    ('rule.R5', 'Put something in {container}, and it turns {colour}.'), ('t.right', 'Yes! That is correct.'),
    ('t.wrong', 'Not quite. {correction}'), ('t.state', 'Did you know? {fact}'),
    ('t.quiz_later', 'Remember what you saw before? {question}'), ('t.demo_step', 'Now watch this. {event}'),
    ('q.where_person', 'Where has {person} gone?'), ('q.where_at_time', 'Where was {object} when {time} came?'),
    ('q.count_at', 'How many {object_kind} can you count at {place}?'),
    ('q.in_container', 'What can be found in {container}?'),
)


class FakeWriter:
    """Returns the bank's gloss behind distinct manner words, plus the chatter real models add."""

    threaded = True

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt: str, *, temperature: float, top_p: float, seed: int, max_tokens: int) -> tuple[str, int]:
        self.calls += 1
        gloss = re.search(r"all mean: (.*)", prompt).group(1)
        count = int(re.search(r"write exactly (\d+)", prompt).group(1))
        pairs = random.Random(seed).sample(list(itertools.combinations(ADVERBS, 2)), count)
        lines = [f"{i + 1}. {a.capitalize()} and {b}, {gloss[0].lower() + gloss[1:]}" for i, (a, b) in enumerate(pairs)]
        return "Here are the patterns:\n" + "\n".join(lines), 10 * count


class FakeChecker:
    """Says yes unless the sentence was written 'loudly'."""

    threaded = False

    def complete(self, prompt: str, *, temperature: float, top_p: float, seed: int, max_tokens: int) -> tuple[str, int]:
        sentence = re.search(r"Sentence: (.*)", prompt).group(1)
        return ("No" if sentence.startswith("Loudly") else "Yes."), 1


class VocabularyTests(unittest.TestCase):
    def test_vocab_lists_are_disjoint_and_complete(self) -> None:
        lists = {
            "places": P.PLACES, "objects": P.OBJECTS, "plurals": P.OBJECT_PLURALS, "categories": P.CATEGORIES,
            "materials": P.MATERIALS, "colours": P.COLOURS, "containers": P.CONTAINERS, "times": P.TIMES,
            "directions": P.DIRECTIONS, "numbers": P.NUMBER_WORDS, "styles": P.STYLES,
        }
        seen: dict[str, str] = {}
        for name, words in lists.items():
            self.assertEqual(len(words), len(set(words)), name)
            for word in words:
                self.assertNotIn(word, seen, f"{word!r} is in both {seen.get(word)} and {name}")
                seen[word] = name
        self.assertEqual(len(P.PLACES), 40)
        self.assertEqual(len(P.OBJECTS), 60)
        self.assertEqual(set(P.CATEGORY.values()), set(P.CATEGORIES))
        self.assertEqual(P.NUMBER_WORDS[0], "zero")
        self.assertEqual(P.NUMBER_WORDS[20], "twenty")
        self.assertEqual(P.PLURAL["loaf"], "loaves")

    def test_every_gloss_and_seed_passes_its_own_check(self) -> None:
        for bank_id, bank in P.BANKS.items():
            self.assertGreaterEqual(len(bank.seeds), 2, bank_id)
            for text in (bank.gloss, *bank.seeds):
                self.assertEqual(P.check_pattern(bank_id, text), [], f"{bank_id}: {text}")

    def test_sample_values_render_every_bank(self) -> None:
        for bank_id, bank in P.BANKS.items():
            values = P.sample_values(bank_id, random.Random(bank_id))
            self.assertEqual(set(values), set(bank.placeholders))
            rendered = P.render(bank.gloss, values)
            self.assertNotIn("{", rendered)
            self.assertTrue(rendered[0].isupper(), rendered)
            first, second = P.crosscheck_values(bank_id, "some-id")
            self.assertEqual(first == second, not bank.placeholders, bank_id)


class MechanicalCheckTests(unittest.TestCase):
    def assertRejects(self, bank_id: str, text: str, fragment: str) -> None:
        reasons = P.check_pattern(bank_id, text)
        self.assertTrue(any(fragment in reason for reason in reasons), f"{text!r}: {reasons}")

    def test_placeholder_multiset(self) -> None:
        self.assertRejects("ev.go", "{person} went far away.", "{place} appears 0 times")
        self.assertRejects("ev.go", "{person} went to {place} and {place}.", "{place} appears 2 times")
        self.assertRejects("ev.go", "{person} went to {town}.", "unknown placeholder {town}")
        self.assertRejects("ev.go", "{person} went to {place} with {object}.", "{object} not allowed")
        self.assertRejects("ev.go", "{person} went to { place }.", "malformed placeholder brace")

    def test_fact_words_outside_placeholders(self) -> None:
        self.assertRejects("ev.go", "{person} went past the barn to {place}.", "place word 'barn'")
        self.assertRejects("ev.go", "{person} went down the road to {place}.", "fact word 'road'")
        self.assertRejects("ev.pick_up", "{person} picked up {object} and two cups.", "number word 'two'")
        self.assertRejects("ev.go", "{person} went to {place} with Tom.", "capitalised word 'Tom'")
        self.assertRejects("ev.go", "{person} went to {place} by himself.", "gendered pronoun 'himself'")
        self.assertRejects("ev.go", "{person} went to {place} with a friend.", "people word 'friend'")
        self.assertRejects("ev.go", "{person} went back home to {place}.", "home word 'home'")
        self.assertRejects("ev.go", "{person} went to {place} again.", "history word 'again'")

    def test_time_words_only_where_allowed(self) -> None:
        self.assertRejects("ev.go", "{person} went to {place} at night.", "time word 'night'")
        self.assertRejects("ev.go", "{person} went to {place} today.", "time word 'today'")
        self.assertEqual(P.check_pattern("rule.R7", "Each day, {person} goes to {place} when {time} comes."), [])
        self.assertRejects("rule.R7", "Each day, {person} goes to {place} in the morning and {time}.", "time word 'morning'")
        self.assertRejects("rule.R3", "Things left at {place} go to {place2} at {time}.", "{time} after at")
        self.assertEqual(P.check_pattern("ev.new_day", "The next morning came."), [])

    def test_negation_only_where_allowed(self) -> None:
        self.assertRejects("ev.go", "{person} went to {place}, not slowly.", "negation 'not'")
        self.assertRejects("ev.go", "{person} didn't wait and went to {place}.", "negation \"didn't\"")
        self.assertRejects("q.where_object", "Is {object} nowhere to be seen?", "negation 'nowhere'")
        self.assertEqual(P.check_pattern("ev.fail_open", "{person} could not open {container}."), [])
        self.assertEqual(P.check_pattern("rule.R6", "{container} opens for {person} and no other."), [])
        self.assertEqual(P.check_pattern("t.wrong", "No, that's not it. {correction}"), [])

    def test_fail_banks_need_a_failure_marker(self) -> None:
        self.assertRejects("ev.fail_open", "{person} opened {container}.", "failure marker")
        self.assertRejects("ev.fail_put_in", "{person} put {object} in {container} with care.", "failure marker")
        self.assertEqual(P.check_pattern("ev.fail_pick_up", "{person} tried to lift {object}, but it was stuck."), [])

    def test_shape_rules(self) -> None:
        self.assertRejects("q.where_object", "Where is {object}.", 'does not end with "?"')
        self.assertRejects("ev.go", "Did {person} go to {place}?", 'only questions may end with "?"')
        self.assertRejects("ev.go", "{person} went to {place} 2 times.", "digit")
        self.assertRejects("ev.go", '"{person} went to {place}."', "quote mark")
        self.assertRejects("ev.go", "'{person} went to {place}.'", "stray apostrophe")
        self.assertRejects("ev.go", "{person} went to {place} (slowly).", "bracket")
        self.assertRejects("ev.go", "**{person} went to {place}.**", "markdown")
        self.assertRejects("ev.go", "{person} went to {place} — fast.", "non-ASCII")
        self.assertRejects("ev.go", "{person} went to {place}.\nThen more.", "newline")
        self.assertRejects("ev.go", "{place}.", "words, needs 3-20")
        self.assertRejects("ev.go", "I saw {person} go to {place}.", "speaker word 'i'")
        self.assertRejects("ev.go", "{person} went to the {place}.", "determiner before a placeholder")
        self.assertRejects("t.state", "Remember that {fact}", "must start its own sentence")
        self.assertRejects("ev.go", "{person} went to {place}. It was far.", "too many")
        self.assertRejects("t.right", "Yes. Yes. That is right.", "too many")
        self.assertRejects("q.where_object", "Where is {object}, I ask?", "capitalised word 'I'")
        self.assertEqual(P.check_pattern("q.yn_at", "Is it true that {object} is at {place}?"), [])
        self.assertEqual(P.check_pattern("t.state", "I want you to know this. {fact} Keep it in mind."), [])
        self.assertEqual(P.check_pattern("t.change", "Something is new now. {fact}"), [])
        self.assertEqual(P.check_pattern("q.count_at", "How many {object_kind} are at {place}?"), [])
        self.assertEqual(P.check_pattern("ev.go", "{person}'s walk ended at {place}."), [])


class DedupAndParsingTests(unittest.TestCase):
    def test_dedup_drops_exact_and_near_duplicates_keeping_the_first(self) -> None:
        texts = [
            "Then {person} walked slowly and quietly over to {place}.",
            "{person} walked to {place}.",
            "then  {person} walked slowly and quietly over to {place}.",
            "Then {person} walked slowly and quietly over to {place}!",
            "Then {person} walked slowly and quietly right over to {place}.",
            "{person} ran off to {place}.",
        ]
        self.assertEqual(P.dedup(texts), [None, None, 0, 0, 0, None])
        self.assertEqual(P.pattern_id("ev.go", "A  b."), P.pattern_id("ev.go", "a b."))
        self.assertNotEqual(P.pattern_id("ev.go", "a b."), P.pattern_id("ev.pick_up", "a b."))

    def test_parse_generation_on_messy_output(self) -> None:
        raw = (
            "<think>\n\n</think>\nHere are 5 patterns:\n\n1. {person} walked to {place}.\n"
            "2) \"{person} ran to {place}.\"\n- **{person} went over to {place}.**\n"
            "* “{person} hurried to {place}.”\n```\nYes, that is right.\n"
            "Sure! Here you go.\nI hope these help!\nThese are the sentences:\n"
        )
        self.assertEqual(P.parse_generation(raw), [
            "{person} walked to {place}.", "{person} ran to {place}.", "{person} went over to {place}.",
            "{person} hurried to {place}.", "Yes, that is right.",
        ])

    def test_parse_yes_no_is_strict(self) -> None:
        for text in ("yes", "Yes.", "YES", "  yes\n", "yes!", "<think>\n</think>\nyes"):
            self.assertTrue(P.parse_yes_no(text), text)
        for text in ("no", "No.", "Yes, it does.", "yes and no", "", "Yeah", "y", "yes yes", None):
            self.assertFalse(P.parse_yes_no(text), text)

    def test_prompts_carry_the_contract(self) -> None:
        prompt = P.build_prompt("ev.fail_open", "manner", 12)
        for fragment in ("{person} {container}", P.BANKS["ev.fail_open"].gloss, P.BANKS["ev.fail_open"].seeds[0],
                         "exactly 12", "failed", "barn", "himself"):
            self.assertIn(fragment, prompt)
        self.assertIn("Teacher style: bossy", P.build_prompt("t.right", "bossy", 12))
        check = P.crosscheck_prompt("ev.go", "Then {person} went to {place}.", {"person": "Kelo", "place": "the mill"})
        self.assertIn("Meaning: Kelo went to the mill.", check)
        self.assertIn("Sentence: Then Kelo went to the mill.", check)
        self.assertIn("yes or no", check)


class DriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data = Path(self._tmp.name)
        quiet = contextlib.ExitStack()
        quiet.enter_context(contextlib.redirect_stdout(io.StringIO()))
        quiet.enter_context(contextlib.redirect_stderr(io.StringIO()))
        self.addCleanup(quiet.close)

    def test_generate_is_resumable_and_share_partitioned(self) -> None:
        expected = {r["id"] for r in G.plan() if r["bank"] == "ev.go"}
        writer = FakeWriter()
        self.assertEqual(G.generate(writer, "fake", self.data, banks=["ev.go"], max_requests=4, workers=3), 4)
        raw = self.data / "raw" / "fake.jsonl"
        with raw.open("a") as handle:
            handle.write('{"id": "torn')  # a run killed mid-write
        self.assertEqual(G.generate(writer, "fake", self.data, banks=["ev.go"], workers=3), len(expected) - 4)
        self.assertEqual(G.generate(writer, "fake", self.data, banks=["ev.go"]), 0)
        rows = G.read_jsonl(raw)
        self.assertEqual({row["id"] for row in rows}, expected)
        self.assertEqual(len(rows), len(expected))
        self.assertEqual(writer.calls, len(expected))
        for key in ("id", "bank", "variant", "prompt", "text", "params", "seconds", "tokens"):
            self.assertIn(key, rows[0])

        shares = []
        for index in range(3):
            directory = self.data / f"share{index}"
            G.generate(FakeWriter(), "fake", directory, share=(index, 3), banks=["ev.go"])
            shares.append({row["id"] for row in G.read_jsonl(directory / "raw" / "fake.jsonl")})
        self.assertEqual(set().union(*shares), expected)
        self.assertEqual(sum(len(share) for share in shares), len(expected))

    def test_finalize_gives_disjoint_covering_splits_with_a_stable_digest(self) -> None:
        banks = ["ev.go", "rule.R2", "ev.give", "t.right"]  # FakeWriter adds manner words, which questions reject
        G.generate(FakeWriter(), "alpha", self.data, banks=banks)
        candidates = G.verify(self.data)
        self.assertTrue(any(row["ok"] for row in candidates))
        self.assertTrue(any("duplicate of" in r for row in candidates for r in row["reasons"]))
        self.assertEqual(G.crosscheck(FakeChecker(), "alpha", self.data), 0)  # never checks its own writing
        checked = G.crosscheck(FakeChecker(), "beta", self.data)
        self.assertEqual(checked, sum(row["ok"] for row in candidates))
        self.assertEqual(G.crosscheck(FakeChecker(), "beta", self.data), 0)

        accepted, pending = G.accepted_candidates(self.data)
        self.assertEqual(pending, 0)
        self.assertFalse(any(row["text"].startswith("Loudly") for row in accepted))
        first = G.finalize(self.data, show=0)
        second = G.finalize(self.data, show=0)
        self.assertEqual(first["manifest_digest"], second["manifest_digest"])
        saved = json.loads((self.data / "bank-v1.json").read_text())
        self.assertEqual(saved["version"], "village-patterns-v1")
        manifest = SplitManifest.from_json(json.dumps(saved["manifest"]))
        self.assertEqual(manifest.digest(), saved["manifest_digest"])
        registry = SplitRegistry.from_manifest(manifest)

        by_bank: dict[str, set[str]] = {}
        for row in accepted:
            by_bank.setdefault(row["bank"], set()).add(row["id"])
        for bank_id in banks:
            splits = saved["banks"][bank_id]
            ids = [row["id"] for split in SPLITS for row in splits[split]]
            self.assertEqual(len(ids), len(set(ids)), bank_id)
            self.assertEqual(set(ids), by_bank[bank_id], bank_id)
            for split in SPLITS:
                self.assertTrue(splits[split], f"{bank_id} has an empty {split} split")
                for row in splits[split]:
                    self.assertEqual(registry.split_of("template", row["id"]), split)
                    if "style" in row:
                        self.assertEqual(registry.split_of("teacher_style", row["style"]), split)
            self.assertEqual(saved["counts"][bank_id]["accepted"], len(ids))
        styles = registry.family("teacher_style").as_dict()
        self.assertEqual(sorted(list(styles.values()).count(split) for split in SPLITS), [2, 2, 6])
        self.assertIn("ev.pick_up", saved["shortfalls"])

        new = G.topup(self.data)
        self.assertTrue(new and all(":u1." in row["id"] for row in new))
        self.assertTrue({row["id"] for row in new} <= {row["id"] for row in G.all_requests(self.data)})
        self.assertTrue(all(":u2." in row["id"] for row in G.topup(self.data)))


class RedTeamTests(unittest.TestCase):
    """Adversarial patterns from the red-team pass, plus good ones that must survive it."""

    def test_adversarial_patterns_are_rejected(self) -> None:
        for kind, cases in (("narration", NARRATION_BAD), ("rule", RULE_BAD), ("teacher", TEACHER_BAD), ("question", QUESTION_BAD)):
            self.assertGreaterEqual(len(cases), 25, kind)
            for bank_id, text in cases:
                self.assertEqual(P.BANKS[bank_id].kind, kind, bank_id)
                with self.subTest(bank=bank_id, text=text):
                    self.assertTrue(P.check_pattern(bank_id, text), "a fact-adding pattern passed")

    def test_varied_good_patterns_pass(self) -> None:
        self.assertGreaterEqual(len(GOOD), 40)
        self.assertEqual({P.BANKS[bank_id].kind for bank_id, _ in GOOD}, set(P.KINDS))
        for bank_id, text in GOOD:
            with self.subTest(bank=bank_id, text=text):
                self.assertEqual(P.check_pattern(bank_id, text), [])

    def test_each_red_team_rule_gives_its_reason(self) -> None:
        cases = (
            ("ev.go", "Mira and {person} went to {place}.", "sentence starts with 'Mira'"),
            ("ev.go", "tosa and {person} went to {place}.", "sentence starts with 'tosa'"),
            ("ev.go", "Tired, {person} went to {place}.", "sentence starts with 'Tired'"),
            ("ev.go", "{person} went back to {place}.", "history word 'back'"),
            ("ev.go", "{person} tried to go to {place}.", "attempt word 'tried'"),
            ("ev.go", "{person} stepped toward {place}.", "attempt word 'toward'"),
            ("ev.go", "{person} said they went to {place}.", "report word 'said'"),
            ("ev.go", "{person} would go to {place}.", "modal word 'would'"),
            ("ev.go", "{person} almost went to {place}.", "hedge word 'almost'"),
            ("ev.go", "{person} went to {place} alone.", "people word 'alone'"),
            ("ev.go", "{person} went to {place} after lunch.", "time word 'lunch'"),
            ("ev.go", "{person} went to {place} for the first time.", "time word 'time'"),
            ("ev.go", "{person} went to {place}; it was cold.", "2 sentences"),
            ("ev.go", "{person} went to {place} - and saw a pal.", "dash"),
            ("ev.go", "{person}s went to {place}.", "placeholder glued"),
            ("ev.go", "{person} went to {place} as well.", "place word 'well'"),
            ("ev.pick_up", "{person} picked up {object}, which was theirs.", "ownership word 'theirs'"),
            ("ev.pick_up", "{person} picked up {object}. It was heavy.", "property word 'heavy'"),
            ("ev.put_in", "{person} hid {object} in {container}.", "event word 'hid'"),
            ("ev.fail_open", "{person} tried to open {container}, and it opened.", "failure marker"),
            ("ev.fail_open", "{person} did not try to open {container}.", "no attempt"),
            ("ev.fail_open", "{person} tried to open {container}, but it was locked.", "property word 'locked'"),
            ("ev.new_day", "A new week began.", "calendar word 'week'"),
            ("ev.time", "It became {time} the next day.", "time word 'day'"),
            ("rule.R1_material", "Some things made of {material} break when put down.", "quantity word 'some'"),
            ("rule.R2", "{person} often follows {leader}.", "frequency word 'often'"),
            ("rule.R2", "{person} must follow {leader}.", "modal word 'must'"),
            ("rule.R3", "Things left at {place} go to {place2} every other day when it is {time}.", "every other"),
            ("rule.R6", "{person} can open {container}.", "only this person"),
            ("rule.R8", "At {place}, at least {count} {object_kind} buy {item}.", "quantity word 'least'"),
            ("t.state", "Here is something false. {fact}", "doubt word 'false'"),
            ("t.state", "I think this is true. {fact}", "doubt word 'think'"),
            ("t.wrong", "Your answer was right. {correction}", "does not say the answer was wrong"),
            ("t.right", "Your answer was right again.", "history word 'again'"),
            ("t.demo_step", "Watch what happened yesterday. {event}", "time word 'yesterday'"),
            ("q.who_has", "Whose is {object}?", "ownership word 'whose'"),
            ("q.rule_material", "Why do things made of {material} break?", "event word 'break'"),
            ("q.compare_count", "Are there twice as many {object_kind} at {place} as at {place2}?", "quantity word 'twice'"),
            ("q.in_container", "Is {container} empty?", "property word 'empty'"),
        )
        for bank_id, text, fragment in cases:
            reasons = P.check_pattern(bank_id, text)
            self.assertTrue(any(fragment in reason for reason in reasons), f"{text!r}: {reasons}")

    def test_crosscheck_only_cases_reach_a_prompt_that_asks_the_right_question(self) -> None:
        for bank_id, text in CROSSCHECK_ONLY:
            bank = P.BANKS[bank_id]
            with self.subTest(bank=bank_id, text=text):
                self.assertEqual(P.check_pattern(bank_id, text), [])  # the word lists' documented limit
                values = P.crosscheck_values(bank_id, P.pattern_id(bank_id, text))[0]
                prompt = P.crosscheck_prompt(bank_id, text, values)
                self.assertIn(f"Meaning: {P.render(bank.gloss, values)}", prompt)
                self.assertIn(f"Sentence: {P.render(text, values)}", prompt)
                self.assertIn("no other people, names, places, objects", prompt)
                self.assertIn("reasons or events", prompt)
                self.assertIn("adds no other fact", prompt)
                if bank.kind == "question":
                    self.assertIn("asks exactly the meaning above", prompt)
                else:
                    self.assertIn("does not deny, doubt or weaken", prompt)
                if "failure" in bank.flags:
                    self.assertIn("an attempt that failed", prompt)
                if bank.kind == "rule":
                    self.assertIn("has exceptions", prompt)


if __name__ == "__main__":
    unittest.main()
