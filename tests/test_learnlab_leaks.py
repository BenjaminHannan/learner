"""Leak detectors: each planted shortcut is flagged by the right detector; clean data is not.

The data are synthetic toy episodes built here (not learnlab.toy), so these
tests pin the detectors' behaviour independently of the toy generator. The
planted flaws are the ones the Step 0 reviews found missed or falsely flagged
(design/reviews/step0/REVIEWS.md).
"""
from __future__ import annotations

from fractions import Fraction
import math
import random
from typing import Any, Optional, Sequence
import unittest

from learnlab.leaks import (
    DETECTORS,
    PositionDetector,
    QAExample,
    answer_in_input_rate,
    candidates,
    example_presence_chance,
    leak_report,
    normalize,
    pair_accuracy,
    pair_chance,
    pair_pvalue,
    presence_chance,
    shuffled,
    words,
)
from learnlab.policy import ALPHA, LEAK_MARGIN, LEAK_MIN_ITEMS

SYLLABLES = ("ba", "ke", "lo", "mi", "nu", "ra", "si", "to", "ve", "zo", "da", "fe", "gi", "ho", "ju", "pa")
NAMES = sorted(a + b for a in SYLLABLES for b in SYLLABLES if a != b)
TRAIN_NAMES, TEST_NAMES = NAMES[::2], NAMES[1::2]   # held-out names, as in the real bench
OBJECTS = ("cup", "key", "coin", "book", "rope", "lamp", "bell", "comb")
PLACES = ("barn", "mill", "shed", "well", "hut", "loft", "yard", "pond")
OBJECT_PLACE = dict(zip(OBJECTS, PLACES))
REGION = {place: ("north" if i < 4 else "south") for i, place in enumerate(PLACES)}
TEMPLATES = (
    "{name} keeps the {obj} in the {place}.",
    "The {obj} of {name} is kept in the {place}.",
    "In the {place}, {name} stores the {obj}.",
    "{name} hides the {obj} inside the {place}.",
    "The {place} is where {name} leaves the {obj}.",
    "You can find the {obj} of {name} in the {place}.",
    "At the {place} is the {obj} that {name} owns.",
    "{name} left the {obj} at the {place}.",
)
STYLES = (
    "Where does {name} keep the {obj}?",
    "In which place is the {obj} of {name}?",
    "Tell me where the {obj} of {name} is.",
    "Which place holds the {obj} of {name}?",
)
FACTS = 4
DETECTOR_NAMES = {
    "majority", "bag_of_words", "question_only", "position", "most_mentioned",
    "last_mention", "bigram", "target_line", "metadata",
}


def _force(places: list[str], index: int, place: str) -> None:
    """Put `place` at `index`, swapping so places stay distinct."""
    if place in places:
        other = places.index(place)
        places[other], places[index] = places[index], place
    else:
        places[index] = place


def episode(
    rng: random.Random,
    names: Sequence[str],
    *,
    target: Optional[int] = None,
    skew: Optional[str] = None,
    object_place: bool = False,
    cue: Optional[str] = None,
    who: bool = False,
    capital: bool = False,
    answer_in_question: bool = False,
    region: bool = False,
    answer_meta: bool = False,
    replace: bool = False,
) -> QAExample:
    """One toy episode. Places are distinct unless `replace` (the old toy's frequency cue)."""
    people = rng.sample(list(names), FACTS)
    objects = rng.sample(OBJECTS, FACTS)
    places = [rng.choice(PLACES) for _ in range(FACTS)] if replace else rng.sample(PLACES, FACTS)
    index = rng.randrange(FACTS) if target is None else target % FACTS
    if skew is not None:
        _force(places, index, skew)
    if object_place:
        _force(places, index, OBJECT_PLACE[objects[index]])
    shown = [place.capitalize() if capital else place for place in places]
    chosen = [rng.randrange(len(TEMPLATES)) for _ in range(FACTS)]
    lines = [
        TEMPLATES[t].format(name=n, obj=o, place=p) for t, n, o, p in zip(chosen, people, objects, shown)
    ]
    if cue is not None:
        lines[index] = f"{cue} {lines[index]}"
    style = rng.randrange(len(STYLES))
    if who:
        question = f"Who keeps the {objects[index]} in the {shown[index]}?"
        answer = people[index]
    else:
        question = STYLES[style].format(name=people[index], obj=objects[index])
        answer = shown[index]
    if answer_in_question:
        question = f"{question} Is it the {answer}?"
    meta = {"target_template": str(chosen[index]), "style": str(style)}
    if region:
        meta["region"] = REGION[places[index]]
    if answer_meta:
        meta["debug_answer"] = answer
    return QAExample("\n".join(lines), question, answer, meta)


def dataset(seed: int, n: int, *, test: bool = False, rate: float = 1.0, **plant: Any) -> list[QAExample]:
    """n episodes; each carries the planted flaw with probability `rate`."""
    rng = random.Random(seed)
    names = TEST_NAMES if test else TRAIN_NAMES
    return [episode(rng, names, **(plant if rng.random() < rate else {})) for _ in range(n)]


def pair(seed: int, n_train: int = 400, n_test: int = 300, **plant: Any) -> tuple[list[QAExample], list[QAExample]]:
    return (
        dataset(seed, n_train, **plant),
        dataset(seed + 100_000, n_test, test=True, **plant),
    )


def exact_tail(hits: int, n: int, p: float) -> float:
    """Independent reference: P(X >= hits), X ~ Binomial(n, p), in exact rational arithmetic."""
    q = Fraction(p)
    return float(sum(math.comb(n, k) * q**k * (1 - q) ** (n - k) for k in range(hits, n + 1)))


class TextTests(unittest.TestCase):
    def test_normalize_case_folds_and_strips_punctuation(self) -> None:
        self.assertEqual(normalize("The Old Mill!"), "the old mill")
        self.assertEqual(normalize("  BARN. "), "barn")
        self.assertEqual(words("Zoë's LAMP, in the Well."), ["zoë's", "lamp", "in", "the", "well"])

    def test_candidates_come_from_the_examples_own_context(self) -> None:
        example = QAExample("Bafe keeps the cup in the Barn.\nKelo keeps the key in the mill.", "Where?", "Barn")
        # Case folded on both sides; "shed" is in the vocabulary but not in this context.
        self.assertEqual(candidates(example, answer_vocab=["barn", "mill", "shed"]), ["barn", "mill"])

    def test_multi_token_answers_are_one_candidate(self) -> None:
        example = QAExample("Bafe keeps the cup in the Old Mill.\nKelo keeps the key in the mill.", "Where?", "old mill")
        self.assertEqual(candidates(example, answer_vocab=["Old Mill", "mill"]), ["old mill", "mill"])
        self.assertAlmostEqual(presence_chance([example], ["old mill", "mill"]), 0.5)

    def test_name_like_candidates_without_a_vocabulary(self) -> None:
        example = QAExample(
            "Bafe keeps the cup in the Old Mill.\nThe key of Kelo is in the barn.",
            "Where does Bafe keep the cup?",
            "Old Mill",
        )
        # "Bafe" opens a sentence but is capitalised mid-sentence in the question; "The" is not a name.
        self.assertEqual(candidates(example), ["bafe", "old mill", "kelo"])

    def test_held_out_names_are_reachable(self) -> None:
        train, test = pair(11, who=True, n_train=50, n_test=50)
        seen = {normalize(e.answer) for e in train}
        held_out = [e for e in test if normalize(e.answer) not in seen]
        self.assertTrue(held_out)
        vocab = [e.answer for e in (*train, *test)]
        for example in held_out:
            self.assertIn(normalize(example.answer), candidates(example, answer_vocab=vocab))

    def test_presence_uses_the_same_extraction_and_ignores_case(self) -> None:
        # Old blocker: capitalised answers matched nothing, so presence fell to 0.
        examples = dataset(3, 200, capital=True)
        self.assertAlmostEqual(presence_chance(examples), 1.0 / FACTS)
        self.assertAlmostEqual(presence_chance(examples, answer_vocab=PLACES), 1.0 / FACTS)

    def test_answer_in_input_rate(self) -> None:
        examples = [
            QAExample("ctx", "Is it the Old Mill?", "old mill"),
            QAExample("ctx", "Is it the barnyard?", "barn"),    # tokens, not substrings
            QAExample("ctx", "Where is it?", "mill"),
            QAExample("ctx", "Is it the BARN?", "Barn"),
        ]
        self.assertAlmostEqual(answer_in_input_rate(examples), 0.5)
        with self.assertRaises(ValueError):
            answer_in_input_rate([])

    def test_shuffled_keeps_answers_and_meta(self) -> None:
        examples = dataset(4, 20)
        mixed = shuffled(examples, seed=1)
        self.assertEqual([e.answer for e in mixed], [e.answer for e in examples])
        self.assertEqual([dict(e.meta) for e in mixed], [dict(e.meta) for e in examples])
        self.assertEqual(
            [sorted(e.context.split("\n")) for e in mixed], [sorted(e.context.split("\n")) for e in examples]
        )


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.train, cls.test = pair(1)
        cls.report = leak_report(cls.train, cls.test)

    def test_every_detector_reports_against_its_own_null(self) -> None:
        report = self.report
        self.assertEqual({kind.name for kind in DETECTORS}, DETECTOR_NAMES)
        self.assertEqual(set(report.detectors), DETECTOR_NAMES)
        self.assertAlmostEqual(report.chance, 1.0 / len(PLACES))
        self.assertAlmostEqual(report.presence_chance, 1.0 / FACTS)
        for name in ("majority", "question_only", "metadata"):
            self.assertEqual(report.detectors[name].null_kind, "answers")
            self.assertAlmostEqual(report.detectors[name].null, report.chance)
        for name in ("position", "most_mentioned", "last_mention", "target_line"):
            self.assertEqual(report.detectors[name].null_kind, "presence")
            self.assertAlmostEqual(report.detectors[name].null, report.presence_chance)
        for name in ("bag_of_words", "bigram"):
            self.assertEqual(report.detectors[name].null_kind, "answers_or_presence")
            self.assertAlmostEqual(report.detectors[name].null, 1.0 / FACTS)

    def test_p_values_are_exact_binomial_tails_then_holm_adjusted(self) -> None:
        for result in self.report.detectors.values():
            self.assertEqual(result.n, len(self.test))
            self.assertAlmostEqual(result.p_value, exact_tail(result.hits, result.n, result.null), places=10)
            self.assertGreaterEqual(result.p_adjusted, result.p_value)

    def test_report_records_settings_and_serialises(self) -> None:
        report = self.report
        self.assertEqual((report.alpha, report.margin, report.min_items), (ALPHA, LEAK_MARGIN, LEAK_MIN_ITEMS))
        self.assertEqual(report.answer_in_input_rate, 0.0)
        data = report.as_dict()
        self.assertEqual(data["status"], "clean")
        self.assertEqual(set(data["detectors"]), DETECTOR_NAMES)
        for key in ("accuracy", "null", "p_value", "p_adjusted", "leaking"):
            self.assertIn(key, data["detectors"]["position"])

    def test_margin_is_an_effect_size_requirement(self) -> None:
        train, test = pair(5, target=0)
        self.assertIn("position", leak_report(train, test, margin=0.7).leaking_detectors)
        self.assertEqual(leak_report(train, test, margin=0.8).detectors["position"].leaking, False)

    def test_invalid_arguments(self) -> None:
        with self.assertRaises(ValueError):
            leak_report(self.train, [])
        for bad in ({"alpha": 0.0}, {"alpha": 1.0}, {"margin": -0.1}, {"min_items": 0}):
            with self.assertRaises(ValueError):
                leak_report(self.train, self.test, **bad)
        with self.assertRaises(ValueError):
            leak_report(self.train, [QAExample("ctx", "q", "?!")] * 5)

    def test_test_only_generator_leaks_are_learned_prequentially(self) -> None:
        # Train is clean; only the test generator always puts the target first.
        report = leak_report(dataset(14, 400), dataset(15, 300, test=True, target=0))
        self.assertEqual(report.status, "leaking")
        self.assertIn("position", report.leaking_detectors)
        # Without any training data the detectors still learn from earlier test items.
        self.assertIn("position", leak_report([], dataset(15, 300, test=True, target=0)).leaking_detectors)


class PlantedLeakTests(unittest.TestCase):
    """Each flaw the reviews found missed must now be flagged by the detector built for it."""

    def assertFlags(self, detector: str, train: Sequence[QAExample], test: Sequence[QAExample], **kw: Any) -> Any:
        report = leak_report(train, test, **kw)
        self.assertEqual(report.status, "leaking", report.as_dict())
        self.assertIn(detector, report.leaking_detectors, report.as_dict())
        result = report.detectors[detector]
        self.assertLess(result.p_adjusted, ALPHA)
        self.assertGreater(result.accuracy, result.null + LEAK_MARGIN)
        return report

    def test_target_always_first(self) -> None:
        report = self.assertFlags("position", *pair(5, target=0))
        self.assertEqual(report.detectors["position"].accuracy, 1.0)

    def test_target_always_second(self) -> None:
        report = self.assertFlags("position", *pair(6, target=1))
        self.assertEqual(report.detectors["position"].accuracy, 1.0)

    def test_target_always_last(self) -> None:
        report = self.assertFlags("last_mention", *pair(7, target=-1))
        self.assertIn("position", report.leaking_detectors)

    def test_review1_first_line_rule(self) -> None:
        answers = ["red", "blue", "green", "gold"]

        def first_line(n: int) -> list[QAExample]:
            out = []
            for i in range(n):
                rest = [a for a in answers if a != answers[i % 4]]
                random.Random(i).shuffle(rest)
                order = [answers[i % 4], *rest]
                out.append(QAExample("\n".join(f"{a} marker" for a in order), "which marker?", answers[i % 4]))
            return out

        self.assertFlags("position", first_line(400), first_line(200))

    def test_word_order_leak(self) -> None:
        # Review 1: "alpha beta" -> left, "beta alpha" -> right; every bag of words is identical.
        examples = [
            QAExample("alpha beta" if i % 2 == 0 else "beta alpha", "choose", "left" if i % 2 == 0 else "right")
            for i in range(400)
        ]
        report = self.assertFlags("bigram", examples[:200], examples[200:])
        self.assertLessEqual(report.detectors["bag_of_words"].accuracy, 0.5 + LEAK_MARGIN)

    def test_question_only_object_determines_place(self) -> None:
        train = dataset(7, 400, rate=0.6, object_place=True)
        test = dataset(8, 300, test=True, rate=0.6, object_place=True)
        self.assertFlags("question_only", train, test)

    def test_target_line_cue(self) -> None:
        report = self.assertFlags("target_line", *pair(9, cue="Teacher says:"))
        # The cue is invisible to the order-free and position detectors.
        for name in ("position", "last_mention", "most_mentioned"):
            self.assertNotIn(name, report.leaking_detectors)

    def test_skewed_answer_prior(self) -> None:
        # 30% of targets are "barn" (uniform would be 12.5%): majority is compared with 1/K, not presence.
        train = dataset(5, 400, rate=0.3, skew="barn")
        test = dataset(6, 300, test=True, rate=0.3, skew="barn")
        report = self.assertFlags("majority", train, test)
        # Its null is 1/K, not the larger presence chance the old shared floor used.
        self.assertAlmostEqual(report.detectors["majority"].null, report.chance)
        self.assertLess(report.chance, report.presence_chance)

    def test_held_out_names_who_questions_target_last(self) -> None:
        train, test = pair(11, who=True, target=-1)
        report = self.assertFlags("last_mention", train, test)
        self.assertEqual(report.detectors["last_mention"].accuracy, 1.0)
        self.assertTrue(any("never occur in training" in w for w in report.warnings))
        # With the full name vocabulary (distractors included) the presence null is exact.
        exact = leak_report(train, test, answer_vocab=NAMES)
        self.assertAlmostEqual(exact.presence_chance, 1.0 / FACTS)
        self.assertIn("last_mention", exact.leaking_detectors)

    def test_capitalised_answers_target_last(self) -> None:
        self.assertFlags("last_mention", *pair(12, capital=True, target=-1))

    def test_metadata_leak(self) -> None:
        # The region field halves the answer set: 1/4 against a 1/8 null.
        self.assertFlags("metadata", *pair(13, region=True))

    def test_held_out_answer_copied_into_metadata(self) -> None:
        # Naive Bayes cannot map an unseen name to an unseen label; the copy rule can.
        report = self.assertFlags("metadata", *pair(14, who=True, answer_meta=True))
        self.assertGreater(report.detectors["metadata"].accuracy, 0.95)

    def test_frequency_cue_of_places_drawn_with_replacement(self) -> None:
        # Review 2: the old toy drew places with replacement, so the answer is size-biased
        # towards repeated places (expected 0.41 against a presence null of 0.31).
        self.assertFlags("most_mentioned", *pair(17, n_test=600, replace=True))

    def test_answer_in_question_10_percent(self) -> None:
        train = dataset(1, 400, rate=0.1, answer_in_question=True)
        test = dataset(2, 300, test=True, rate=0.1, answer_in_question=True)
        report = self.assertFlags("question_only", train, test)
        self.assertAlmostEqual(report.answer_in_input_rate, answer_in_input_rate(test))
        self.assertGreater(report.answer_in_input_rate, 0.05)
        self.assertTrue(any("answer appears in the question" in w for w in report.warnings))

    def test_answer_in_question_power_is_limited_and_documented(self) -> None:
        # The statistical detectors have limited power at low rates; answer_in_input_rate is exact.
        caught, rates = 0, []
        for seed in range(5):
            train = dataset(7000 + seed, 400, rate=0.05, answer_in_question=True)
            test = dataset(8000 + seed, 300, test=True, rate=0.05, answer_in_question=True)
            report = leak_report(train, test)
            caught += "question_only" in report.leaking_detectors
            rates.append(report.answer_in_input_rate)
            self.assertTrue(any("answer appears in the question" in w for w in report.warnings))
        self.assertLess(caught, 5)       # 5% of 300 items is below reliable detection
        self.assertTrue(all(rate > 0.0 for rate in rates))


class CleanControlTests(unittest.TestCase):
    """False positives the reviews found must be gone."""

    def assertClean(self, train: Sequence[QAExample], test: Sequence[QAExample], **kw: Any) -> Any:
        report = leak_report(train, test, **kw)
        self.assertEqual(report.status, "clean", report.as_dict())
        self.assertEqual(report.leaking_detectors, [], report.as_dict())
        return report

    def test_iid_clean_data_across_seeds(self) -> None:
        for seed in (21, 22, 23, 24, 25):
            with self.subTest(seed=seed):
                self.assertClean(*pair(seed))

    def test_capitalised_answers_are_not_a_false_positive(self) -> None:
        # Old blocker: presence 0 -> floor 1/K -> bag_of_words flagged on clean data.
        for seed in (16, 26, 36):
            with self.subTest(seed=seed):
                report = self.assertClean(*pair(seed, capital=True))
                self.assertAlmostEqual(report.presence_chance, 1.0 / FACTS)

    def test_who_questions_with_held_out_names_are_clean(self) -> None:
        self.assertClean(*pair(31, who=True))

    def test_small_clean_slices_are_insufficient_never_leaking(self) -> None:
        train = dataset(18, 400)
        for n in (20, 40, 80):
            for start in range(0, 600, n):
                report = leak_report(train, dataset(19 + start + n, n, test=True))
                self.assertEqual(report.status, "insufficient", (n, start))
                self.assertFalse(report.leaking)
                self.assertTrue(any("insufficient" in w for w in report.warnings))

    def test_review1_tiny_iid_sample(self) -> None:
        # Review 1 found an 8-item clean slice flagged by the fixed margin.
        for seed in range(200):
            rng = random.Random(seed)
            examples = [QAExample(rng.choice(["x", "y"]), "q", rng.choice(["a", "b"])) for _ in range(48)]
            self.assertEqual(leak_report(examples[:40], examples[40:]).status, "insufficient")

    def test_min_items_is_configurable_and_small_n_planted_leak_is_still_reported(self) -> None:
        train, test = pair(5, target=0)
        report = leak_report(train, test, min_items=1000)
        self.assertEqual(report.status, "insufficient")
        self.assertIn("position", report.leaking_detectors)
        self.assertTrue(any("significant detectors: position" in w for w in report.warnings))

    def test_benchmark_quality_warning_for_trivially_present_answers(self) -> None:
        # One or two candidates per context: guessing among them already scores 0.75.
        examples = [
            QAExample(f"The cup is in the {a}." + (f" The key is in the {b}." if i % 2 else ""), "Where is the cup?", a)
            for i, (a, b) in enumerate((PLACES[i % 8], PLACES[(i + 3) % 8]) for i in range(150))
        ]
        report = leak_report(examples[:50], examples[50:])
        self.assertAlmostEqual(report.presence_chance, 0.75)
        self.assertTrue(any("trivially present" in w for w in report.warnings))
        clean = leak_report(*pair(1))
        self.assertFalse(any("trivially present" in w for w in clean.warnings))


class DetectorApiTests(unittest.TestCase):
    def test_fit_and_predict_standalone(self) -> None:
        train, test = pair(5, n_train=100, n_test=20, target=0)
        detector = PositionDetector().fit(train)
        for example in test:
            self.assertEqual(normalize(detector.predict(example)), normalize(example.answer))


class CounterfactualPairTests(unittest.TestCase):
    @staticmethod
    def pairs(n: int, seed: int = 0) -> list[tuple[QAExample, QAExample]]:
        """Near-identical episodes whose target places are swapped with a distractor's."""
        rng = random.Random(seed)
        out = []
        for _ in range(n):
            people, objects, places = rng.sample(TRAIN_NAMES, 4), rng.sample(OBJECTS, 4), rng.sample(PLACES, 4)
            question = f"Where does {people[0]} keep the {objects[0]}?"

            def make(order: list[str]) -> QAExample:
                lines = [f"{n} keeps the {o} in the {p}." for n, o, p in zip(people, objects, order)]
                return QAExample("\n".join(lines), question, order[0])

            swapped = [places[1], places[0], *places[2:]]
            out.append((make(places), make(swapped)))
        return out

    def test_pair_metric_and_chance(self) -> None:
        pairs = self.pairs(100)
        oracle = lambda example: example.answer
        constant = lambda example: PLACES[0]
        first = lambda example: candidates(example, answer_vocab=PLACES)[0]
        self.assertEqual(pair_accuracy(pairs, oracle), 1.0)
        self.assertEqual(pair_accuracy(pairs, constant), 0.0)   # opposite answers defeat a constant
        self.assertEqual(pair_accuracy(pairs, first), 1.0)      # a surface rule the pairs do not stop
        self.assertAlmostEqual(pair_chance(pairs, 1.0 / 8), 1.0 / 64)
        self.assertAlmostEqual(pair_chance(pairs, example_presence_chance(PLACES)), 1.0 / 16)
        self.assertLess(pair_pvalue(pairs, oracle, example_presence_chance(PLACES)), 1e-50)
        self.assertEqual(pair_pvalue(pairs, constant, 1.0 / 8), 1.0)
        with self.assertRaises(ValueError):
            pair_chance(pairs, 1.5)
        with self.assertRaises(ValueError):
            pair_accuracy([], oracle)


if __name__ == "__main__":
    unittest.main()
