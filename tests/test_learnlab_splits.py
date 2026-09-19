"""Step 0 splits: whole-family holdouts, frozen manifests, and leak audits that do not trust the generator."""
from __future__ import annotations

from collections import Counter
import dataclasses
from dataclasses import dataclass
import json
import random
from typing import Mapping, Optional
import unittest

from learnlab.splits import (
    SPLITS,
    SplitLeak,
    SplitManifest,
    SplitRegistry,
    allocate,
    assert_consumable,
    assign,
    assign_ranked,
    audit_examples,
    consumable,
    items_in,
    validate_fractions,
)

SYLLABLES = ("ba", "ke", "lo", "mi", "nu", "ra", "si", "to", "ve", "zo", "da", "fe", "gi", "ho", "ju", "pa")
NAMES = sorted({a + b for a in SYLLABLES for b in SYLLABLES if a != b})
TEMPLATES = {
    "t00": "{name} keeps the {obj} in the {place}.",
    "t01": "The {obj} of {name} is kept in the {place}.",
    "t02": "{name} puts the {obj} away in the {place}.",
    "t03": "In the {place}, {name} stores the {obj}.",
    "t04": "{name} hides the {obj} inside the {place}.",
    "t05": "The {place} is where {name} leaves the {obj}.",
    "t06": "{name} always carries the {obj} to the {place}.",
    "t07": "You can find the {obj} of {name} in the {place}.",
}
FRACTIONS = (0.5, 0.25, 0.25)
SALT = "splits-test"
INVALID_FRACTIONS = (
    (1.2, -0.1, -0.1),
    (2.0, -1.0, 0.0),
    (0.5, 0.5),
    (0.5, 0.3, 0.1),
    (float("nan"), 0.5, 0.5),
    (float("inf"), 0.0, 0.0),
    (True, 0, 0),
    ("0.8", "0.1", "0.1"),
    "abc",
    None,
)


@dataclass(frozen=True)
class Example:
    split: str
    text: str
    provenance: Optional[Mapping[str, tuple[str, ...]]] = None
    item_id: str = ""


def make_registry() -> SplitRegistry:
    registry = SplitRegistry(salt=SALT, fractions=FRACTIONS)
    registry.fix_family("template", TEMPLATES, "templates-v1")
    return registry


def generate(registry: SplitRegistry, split: str, index: int) -> Example:
    """A well-behaved generator: every item comes through the split's view."""
    view = registry.view(split)
    rng = random.Random(f"{split}|{index}")
    names = view.draw("name", NAMES, rng, k=2)
    template = view.draw("template", TEMPLATES, rng)[0]
    text = "\n".join(TEMPLATES[template].format(name=name, obj="cup", place="barn") for name in names)
    return Example(split, text, view.provenance(), f"{split}-{index}")


def name_in(registry: SplitRegistry, split: str) -> str:
    return next(name for name in NAMES if registry.split_of("name", name) == split)


def vocab() -> dict:
    return {"name": NAMES, "template": TEMPLATES}


class AllocationTests(unittest.TestCase):
    def test_three_item_family_gets_all_three_splits(self):
        for fractions in ((0.8, 0.1, 0.1), (0.95, 0.025, 0.025), (0.34, 0.33, 0.33), FRACTIONS):
            assignment = assign_ranked("rule_family", ["direct", "moved", "swapped"], fractions=fractions)
            self.assertEqual(Counter(assignment.values()), {"train": 1, "validation": 1, "test": 1}, fractions)
        registry = SplitRegistry()
        fixed = registry.fix_family("rule_family", ["direct", "moved", "swapped"], "rules-v1")
        self.assertEqual(sorted(fixed.values()), sorted(SPLITS))

    def test_every_positive_split_gets_an_item_and_sizes_follow_quotas(self):
        for fractions in ((0.8, 0.1, 0.1), (0.95, 0.025, 0.025), FRACTIONS, (0.7, 0.2, 0.1), (0.6, 0.4, 0.0)):
            positive = [value > 0 for value in fractions]
            for count in range(sum(positive), 41):
                sizes = allocate(count, fractions)
                self.assertEqual(sum(sizes), count)
                for size, fraction in zip(sizes, fractions):
                    self.assertEqual(size >= 1, fraction > 0, (count, fractions, sizes))
                quotas = [count * fraction for fraction in fractions]
                if all(quota >= 1 for quota, flag in zip(quotas, positive) if flag):
                    # No minimum-one adjustment was needed: plain largest remainder.
                    self.assertTrue(all(abs(size - quota) < 1 for size, quota in zip(sizes, quotas)), (count, sizes))
                family = [f"r{i}" for i in range(count)]
                counts = Counter(assign_ranked("rule_family", family, fractions=fractions).values())
                self.assertEqual(tuple(counts[split] for split in SPLITS), sizes)

    def test_largest_remainder_known_values(self):
        self.assertEqual(allocate(10, (0.8, 0.1, 0.1)), (8, 1, 1))
        self.assertEqual(allocate(7, FRACTIONS), (3, 2, 2))
        self.assertEqual(allocate(10, FRACTIONS), (5, 3, 2))
        self.assertEqual(allocate(5, (0.5, 0.5, 0.0)), (3, 2, 0))

    def test_too_few_items_for_the_positive_splits_raises(self):
        with self.assertRaises(ValueError):
            assign_ranked("template", ["a", "b"])
        self.assertEqual(sorted(assign_ranked("template", ["a", "b"], fractions=(0.5, 0.5, 0.0)).values()), ["train", "validation"])

    def test_zero_fraction_split_is_never_assigned(self):
        self.assertEqual({assign("name", name, fractions=(0.5, 0.5, 0.0)) for name in NAMES}, {"train", "validation"})
        self.assertEqual({assign("name", name, fractions=(1, 0, 0)) for name in NAMES}, {"train"})

    def test_ranked_assignment_ignores_input_order(self):
        items = list(TEMPLATES)
        shuffled = items[::-1]
        self.assertEqual(assign_ranked("template", items, salt=SALT), assign_ranked("template", shuffled, salt=SALT))

    def test_hash_path_is_deterministic_salted_and_fills_large_pools(self):
        self.assertEqual(assign("name", "nera"), assign("name", "nera"))
        self.assertEqual({assign("name", name) for name in NAMES}, set(SPLITS))
        self.assertTrue(any(assign("name", name) != assign("name", name, salt="other") for name in NAMES[:50]))
        for split in SPLITS:
            self.assertEqual(items_in("name", NAMES, split), [n for n in NAMES if assign("name", n) == split])


class FractionValidationTests(unittest.TestCase):
    def test_invalid_fractions_raise_everywhere(self):
        for fractions in INVALID_FRACTIONS:
            with self.subTest(fractions=fractions):
                with self.assertRaises(ValueError):
                    validate_fractions(fractions)
                with self.assertRaises(ValueError):
                    assign("name", "nera", fractions=fractions)
                with self.assertRaises(ValueError):
                    assign_ranked("template", [f"x{i}" for i in range(8)], fractions=fractions)
                with self.assertRaises(ValueError):
                    items_in("name", NAMES, "train", fractions=fractions)
                with self.assertRaises(ValueError):
                    allocate(8, fractions)
                with self.assertRaises(ValueError):
                    SplitRegistry(fractions=fractions)

    def test_valid_fractions_within_tolerance_are_accepted(self):
        self.assertEqual(validate_fractions((1, 0, 0)), (1.0, 0.0, 0.0))
        validate_fractions((0.5, 0.25, 0.25 + 1e-12))
        with self.assertRaises(ValueError):
            validate_fractions((0.5, 0.25, 0.25 + 1e-6))


class FamilyVersionTests(unittest.TestCase):
    def test_refix_same_version_with_different_membership_raises(self):
        registry = make_registry()
        before = registry.fixed["template"]
        with self.assertRaises(SplitLeak):
            registry.fix_family("template", list(TEMPLATES) + ["t99"], "templates-v1")
        with self.assertRaises(SplitLeak):
            registry.fix_family("template", list(TEMPLATES)[1:], "templates-v1")
        self.assertEqual(registry.fixed["template"], before)
        # Identical membership under the same version is an idempotent no-op.
        self.assertEqual(registry.fix_family("template", list(TEMPLATES)[::-1], "templates-v1"), before)

    def _membership_change_that_moves(self, base: list[str]) -> tuple[str, str, str, str]:
        base_map = assign_ranked("template", base, salt=SALT, fractions=FRACTIONS)
        for index in range(1000):
            extra = f"extra{index}"
            grown = assign_ranked("template", base + [extra], salt=SALT, fractions=FRACTIONS)
            for item in base:
                if grown[item] != base_map[item]:
                    return extra, item, base_map[item], grown[item]
        self.fail("no one-item addition moved an existing member")

    def test_stale_record_after_refix_is_caught_by_assert_disjoint(self):
        base = list(TEMPLATES)
        extra, moved, old_split, new_split = self._membership_change_that_moves(base)
        registry = make_registry()
        registry.record("template", moved, old_split)
        registry.assert_disjoint()
        registry.fix_family("template", base + [extra], "templates-v2")
        self.assertEqual(registry.split_of("template", moved), new_split)
        with self.assertRaises(SplitLeak) as caught:
            registry.assert_disjoint()
        self.assertIn("stale", str(caught.exception))
        self.assertIn(repr(moved), str(caught.exception))
        with self.assertRaises(SplitLeak):
            registry.record("template", moved, old_split)
        # Using it again under its new split puts it in two splits: both problems are reported.
        registry.record("template", moved, new_split)
        with self.assertRaises(SplitLeak) as caught:
            registry.assert_disjoint()
        self.assertTrue(any("in both" in problem for problem in caught.exception.violations))

    def test_record_of_a_removed_member_is_stale(self):
        registry = make_registry()
        registry.record("template", "t00", registry.split_of("template", "t00"))
        registry.fix_family("template", [t for t in TEMPLATES if t != "t00"], "templates-v2")
        with self.assertRaises(SplitLeak) as caught:
            registry.assert_disjoint()
        self.assertIn("no longer a family member", str(caught.exception))

    def test_record_rejects_wrong_split_and_unknown_members(self):
        registry = make_registry()
        test_template = next(t for t, s in registry.fixed["template"].items() if s == "test")
        with self.assertRaises(SplitLeak):
            registry.record("template", test_template, "train")
        with self.assertRaises(KeyError):
            registry.record("template", "t99", "train")
        with self.assertRaises(ValueError):
            registry.record("template", test_template, "dev")


class ManifestTests(unittest.TestCase):
    def registry(self) -> SplitRegistry:
        registry = make_registry()
        registry.fix_family("teacher_style", ["q0", "q1", "q2", "q3"], "styles-v1")
        registry.fix_family("rule_family", ["direct", "moved", "restated", "swapped"], "rules-v1")
        return registry

    def test_manifest_round_trips(self):
        registry = self.registry()
        manifest = registry.manifest()
        text = manifest.to_json()
        loaded = SplitManifest.from_json(text)
        self.assertEqual(loaded, manifest)
        self.assertEqual(loaded.digest(), manifest.digest())
        self.assertEqual(loaded.to_json(), text)
        registry.verify_manifest(manifest)
        registry.verify_manifest(text)
        self.registry().verify_manifest(text)  # an independent rebuild agrees
        restored = SplitRegistry.from_manifest(text)
        restored.verify_manifest(manifest)
        for axis in ("template", "teacher_style", "rule_family"):
            self.assertEqual(restored.fixed[axis], registry.fixed[axis])
        for name in NAMES:
            self.assertEqual(restored.split_of("name", name), registry.split_of("name", name))

    def test_manifest_is_immutable(self):
        registry = self.registry()
        manifest = registry.manifest()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            manifest.salt = "other"  # type: ignore[misc]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            manifest.families[0].version = "v9"  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            registry.salt = "other"  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            registry.fractions = (1.0, 0.0, 0.0)  # type: ignore[misc]
        copy = registry.fixed
        copy["template"]["t00"] = "nowhere"
        manifest.families[0].as_dict()["t00"] = "nowhere"
        self.assertNotEqual(registry.fixed["template"]["t00"], "nowhere")
        registry.verify_manifest(manifest)

    def test_membership_change_under_the_same_version_in_another_process_is_rejected(self):
        saved = self.registry().manifest().to_json()
        evaluator = SplitRegistry(salt=SALT, fractions=FRACTIONS)
        evaluator.fix_family("template", list(TEMPLATES) + ["t13"], "templates-v1")
        evaluator.fix_family("teacher_style", ["q0", "q1", "q2", "q3"], "styles-v1")
        evaluator.fix_family("rule_family", ["direct", "moved", "restated", "swapped"], "rules-v1")
        with self.assertRaises(SplitLeak) as caught:
            evaluator.verify_manifest(saved)
        self.assertIn("members added", str(caught.exception))
        self.assertIn("different contents", str(caught.exception))

    def test_changed_manifests_are_rejected(self):
        saved = self.registry().manifest()
        bumped = self.registry()
        bumped.fix_family("rule_family", ["direct", "moved", "restated", "swapped"], "rules-v2")
        salted = SplitRegistry(salt="other-salt", fractions=FRACTIONS)
        reweighted = SplitRegistry(salt=SALT, fractions=(0.6, 0.2, 0.2))
        missing = make_registry()
        extra = self.registry()
        extra.fix_family("name", ["nera", "bafe", "kolo"], "names-v1")
        for label, registry, expected in (
            ("version bump", bumped, "version changed"),
            ("salt", salted, "salt changed"),
            ("fractions", reweighted, "fractions changed"),
            ("family missing", missing, "not fixed now"),
            ("extra family", extra, "hashed when saved"),
        ):
            with self.subTest(label):
                with self.assertRaises(SplitLeak) as caught:
                    registry.verify_manifest(saved)
                self.assertIn(expected, str(caught.exception))

    def test_tampered_manifest_is_rejected_and_changes_digest(self):
        registry = self.registry()
        saved = registry.manifest()
        data = json.loads(saved.to_json())
        assignment = data["families"]["template"]["assignment"]
        item = next(t for t, s in assignment.items() if s == "test")
        assignment[item] = "train"
        tampered = json.dumps(data)
        self.assertNotEqual(SplitManifest.from_json(tampered).digest(), saved.digest())
        with self.assertRaises(SplitLeak) as caught:
            registry.verify_manifest(tampered)
        self.assertIn("moved between splits", str(caught.exception))

    def test_changed_hash_code_is_caught_by_the_canary(self):
        data = json.loads(self.registry().manifest().to_json())
        data["canary"] = "0" * 64
        with self.assertRaises(SplitLeak):
            SplitRegistry.from_manifest(json.dumps(data))
        with self.assertRaises(SplitLeak) as caught:
            self.registry().verify_manifest(json.dumps(data))
        self.assertIn("canary", str(caught.exception))

    def test_malformed_manifests_raise_value_error(self):
        good = json.loads(self.registry().manifest().to_json())
        cases = {
            "not json": "{",
            "missing key": json.dumps({k: v for k, v in good.items() if k != "canary"}),
            "bad split": json.dumps({**good, "families": {"template": {"version": "v", "assignment": {"t00": "dev"}}}}),
            "bad axis": json.dumps({**good, "families": {"colour": {"version": "v", "assignment": {"x": "train"}}}}),
            "bad fractions": json.dumps({**good, "fractions": [1.2, -0.1, -0.1]}),
            "empty version": json.dumps({**good, "families": {"template": {"version": "", "assignment": {}}}}),
            "future format": json.dumps({**good, "format": 99}),
        }
        for label, text in cases.items():
            with self.subTest(label):
                with self.assertRaises(ValueError):
                    SplitManifest.from_json(text)


class ViewTests(unittest.TestCase):
    def test_draw_filters_to_the_split_records_and_builds_provenance(self):
        registry = make_registry()
        view = registry.view("test")
        names = view.draw("name", NAMES, random.Random(0), k=4)
        template = view.draw("template", TEMPLATES, random.Random(0))[0]
        self.assertEqual(len(set(names)), 4)
        self.assertTrue(all(registry.split_of("name", name) == "test" for name in names))
        self.assertEqual(registry.split_of("template", template), "test")
        self.assertEqual(registry.used["name"]["test"], set(names))
        self.assertEqual(view.provenance(), {"name": tuple(names), "template": (template,)})
        registry.assert_disjoint()

    def test_draws_are_reproducible_whatever_the_candidate_order(self):
        first = make_registry().view("train").draw("name", NAMES, random.Random(3), k=3)
        second = make_registry().view("train").draw("name", NAMES[::-1], random.Random(3), k=3)
        self.assertEqual(first, second)

    def test_use_rejects_an_item_of_another_split(self):
        registry = make_registry()
        view = registry.view("test")
        with self.assertRaises(SplitLeak):
            view.use("name", name_in(registry, "train"))
        self.assertEqual(view.provenance(), {})
        self.assertEqual(registry.summary()["name"], {"train": 0, "validation": 0, "test": 0})

    def test_draw_raises_when_the_split_has_too_few_items(self):
        registry = make_registry()
        test_templates = [t for t, s in registry.fixed["template"].items() if s == "test"]
        with self.assertRaises(ValueError):
            registry.view("test").draw("template", TEMPLATES, random.Random(0), k=len(test_templates) + 1)
        with self.assertRaises(ValueError):
            registry.view("dev")


class AuditTests(unittest.TestCase):
    def clean_examples(self, registry: SplitRegistry, count: int = 20) -> list[Example]:
        return [generate(registry, split, index) for split in SPLITS for index in range(count)]

    def test_clean_generated_examples_pass(self):
        registry = make_registry()
        examples = self.clean_examples(registry)
        report = audit_examples(examples, registry, text_of=lambda e: e.text, vocab=vocab())
        self.assertEqual(report["examples"], 3 * 20)
        self.assertEqual(report["by_split"], {split: 20 for split in SPLITS})
        registry.assert_disjoint()

    def test_generator_that_bypasses_record_is_caught(self):
        # Review 1's n0 case: the same name used in train and test, never recorded.
        registry = make_registry()
        shared = name_in(registry, "train")
        examples = [
            Example("train", f"{shared} keeps the cup in the barn.", {"name": (shared,)}),
            Example("test", f"{shared} keeps the cup in the barn.", {"name": (shared,)}),
        ]
        registry.assert_disjoint()  # the registry's own bookkeeping is blind to it
        with self.assertRaises(SplitLeak) as caught:
            audit_examples(examples, registry, text_of=lambda e: e.text, vocab={"name": NAMES})
        problems = caught.exception.violations
        self.assertTrue(any("never recorded" in p for p in problems))
        self.assertTrue(any("belongs to train" in p for p in problems))
        self.assertTrue(any("text mentions train name" in p for p in problems))

    def test_generator_without_provenance_is_caught_by_the_text_scan(self):
        registry = make_registry()
        rng = random.Random(0)
        # Buggy generator: samples the whole pool, records nothing, attaches no provenance.
        examples = [Example("test", " ".join(rng.sample(NAMES, 4)) + " went home.") for _ in range(10)]
        with self.assertRaises(SplitLeak) as caught:
            audit_examples(examples, registry, text_of=lambda e: e.text, vocab={"name": NAMES})
        self.assertTrue(any("no provenance" in p for p in caught.exception.violations))
        self.assertTrue(any("text mentions" in p for p in caught.exception.violations))

    def test_empty_provenance_counts_as_none(self):
        # A generator that skips the view leaves a dataclass default of {}; own-split text hides it.
        registry = make_registry()
        clean = generate(registry, "test", 0)
        bypass = dataclasses.replace(clean, provenance={}, item_id="bypass")
        with self.assertRaises(SplitLeak) as caught:
            audit_examples([clean, bypass], registry, text_of=lambda e: e.text, vocab=vocab())
        self.assertTrue(any("bypass" in p and "no provenance" in p for p in caught.exception.violations))
        with self.assertRaises(SplitLeak):
            assert_consumable(bypass, "test", registry=registry)
        with self.assertRaises(SplitLeak):
            assert_consumable(dataclasses.replace(clean, provenance={"name": ()}), "test", registry=registry)
        assert_consumable(clean, "test", registry=registry)

    def test_own_split_name_missing_from_provenance_is_caught(self):
        # Partial bypass: an extra line with a test name drawn without the view.
        registry = make_registry()
        clean = generate(registry, "test", 0)
        extra = next(n for n in NAMES if registry.split_of("name", n) == "test" and n not in clean.provenance["name"])
        partial = dataclasses.replace(clean, text=clean.text + f"\n{extra} keeps the cup in the barn.")
        audit_examples([clean], registry, text_of=lambda e: e.text, vocab=vocab())
        with self.assertRaises(SplitLeak) as caught:
            audit_examples([partial], registry, text_of=lambda e: e.text, vocab=vocab(), require_recorded=False)
        self.assertTrue(any("provenance does not list" in p and repr(extra) in p for p in caught.exception.violations))

    def test_test_example_mentioning_a_train_name_is_caught(self):
        # Review 2: a distractor sentence adds a train name without record().
        registry = make_registry()
        clean = generate(registry, "test", 0)
        train_name = name_in(registry, "train")
        audit_examples([clean], registry, text_of=lambda e: e.text, vocab=vocab())
        leaked = dataclasses.replace(clean, text=clean.text + f"\n{train_name.capitalize()} waves hello.")
        with self.assertRaises(SplitLeak) as caught:
            audit_examples([leaked], registry, text_of=lambda e: e.text, vocab=vocab())
        self.assertIn(repr(train_name), str(caught.exception))
        # A name only inside a longer word is not a mention.
        embedded = dataclasses.replace(clean, text=clean.text + f"\nThe {train_name}xx waves hello.")
        audit_examples([embedded], registry, text_of=lambda e: e.text, vocab=vocab())

    def test_other_split_template_in_text_is_caught(self):
        registry = make_registry()
        clean = generate(registry, "test", 1)
        train_template = next(t for t, s in registry.fixed["template"].items() if s == "train")
        test_name = clean.provenance["name"][0]
        line = TEMPLATES[train_template].format(name=test_name.upper(), obj="lamp", place="old mill")
        leaked = dataclasses.replace(clean, text=clean.text + "\n" + line)
        with self.assertRaises(SplitLeak) as caught:
            audit_examples([leaked], registry, text_of=lambda e: e.text, vocab=vocab())
        self.assertIn(repr(train_template), str(caught.exception))

    def test_own_template_that_contains_a_foreign_one_is_not_flagged(self):
        registry = make_registry()
        fixed = registry.fixed["template"]
        train_template = next(t for t, s in fixed.items() if s == "train")
        test_template = next(t for t, s in fixed.items() if s == "test")
        surfaces = dict(TEMPLATES)
        surfaces[train_template] = "{name} keeps the {obj} in the {place}."
        surfaces[test_template] = "{name} keeps the {obj} in the {place} again."
        test_name = name_in(registry, "test")
        registry.record("name", test_name, "test")
        registry.record("template", test_template, "test")
        provenance = {"name": (test_name,), "template": (test_template,)}
        own = Example("test", f"{test_name} keeps the cup in the barn again.", provenance)
        audit_examples([own], registry, text_of=lambda e: e.text, vocab={"name": NAMES, "template": surfaces})
        foreign = Example("test", f"{test_name} keeps the cup in the barn.", provenance)
        with self.assertRaises(SplitLeak):
            audit_examples([foreign], registry, text_of=lambda e: e.text, vocab={"name": NAMES, "template": surfaces})

    def test_templates_indistinguishable_across_splits_are_flagged(self):
        registry = make_registry()
        fixed = registry.fixed["template"]
        train_template = next(t for t, s in fixed.items() if s == "train")
        test_template = next(t for t, s in fixed.items() if s == "test")
        surfaces = dict(TEMPLATES)
        surfaces[train_template] = "{name} keeps the {obj} in the {place}."
        surfaces[test_template] = "In the {place}, {name} keeps the {obj}."
        test_name = name_in(registry, "test")
        registry.record("name", test_name, "test")
        registry.record("template", test_template, "test")
        provenance = {"name": (test_name,), "template": (test_template,)}
        # "In the barn, X keeps the cup in the shed." fits both skeletons equally well.
        ambiguous = Example("test", f"In the barn, {test_name} keeps the cup in the shed.", provenance)
        with self.assertRaises(SplitLeak):
            audit_examples([ambiguous], registry, text_of=lambda e: e.text, vocab={"name": NAMES, "template": surfaces})

    def test_unlabelled_example_and_bad_vocab_fail_closed(self):
        registry = make_registry()
        with self.assertRaises(SplitLeak):
            audit_examples([{"text": "hello", "provenance": {}}], registry, text_of=lambda e: e["text"], vocab={"name": NAMES})
        with self.assertRaises(ValueError):
            audit_examples([], registry, text_of=str, vocab={"template": ["t99"]})
        with self.assertRaises(ValueError):
            audit_examples([], registry, text_of=str, vocab={"template": {"t00": "{name} {obj}"}})


class ConsumptionTests(unittest.TestCase):
    def test_consuming_a_test_episode_in_training_is_caught(self):
        registry = make_registry()
        test_example = generate(registry, "test", 0)
        train_example = generate(registry, "train", 0)
        assert_consumable(test_example, "test", registry=registry)
        with self.assertRaises(SplitLeak):
            assert_consumable(test_example, "train")
        stream = [train_example, test_example]
        with self.assertRaises(SplitLeak):
            list(consumable(stream, "train"))
        self.assertEqual(list(consumable([train_example], "train", registry=registry)), [train_example])

    def test_relabelled_or_unlabelled_examples_are_caught(self):
        registry = make_registry()
        test_example = generate(registry, "test", 0)
        relabelled = dataclasses.replace(test_example, split="train")
        assert_consumable(relabelled, "train")  # the label alone cannot tell
        with self.assertRaises(SplitLeak):
            assert_consumable(relabelled, "train", registry=registry)
        with self.assertRaises(SplitLeak):
            assert_consumable({"text": "hi"}, "train")
        with self.assertRaises(SplitLeak):
            assert_consumable({"split": "train"}, "train", registry=registry)
        assert_consumable({"split": "test", "provenance": dict(test_example.provenance)}, "test", registry=registry)


if __name__ == "__main__":
    unittest.main()
