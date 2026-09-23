"""Step 0 paired checks for held-out splits (`learnlab.splits` on the toy stream).

Each planted flaw must raise, and its clean control (the same registry or
episode without the flaw) must pass. Everything is deterministic: the toy
seeds every episode from its split and index.
"""
from __future__ import annotations

from dataclasses import replace
import json
import random
import re
import traceback
from typing import Any, Callable, Iterable, Optional, Union

from . import check
from ..splits import (
    SPLITS,
    SplitLeak,
    SplitManifest,
    SplitRegistry,
    allocate,
    assert_consumable,
    assign_ranked,
    audit_examples,
    consumable,
    validate_fractions,
)
from ..toy import (
    FAMILY_VERSIONS,
    RULE_FAMILIES,
    STYLES,
    TEMPLATES,
    Episode,
    all_names,
    episodes,
    make_registry,
    split_vocab,
)

STREAM = 40                     # clean episodes per split
FIXED_AXES = ("template", "teacher_style", "rule_family")
Errors = Union[type, tuple]


def _raises(action: Callable[[], Any], errors: Errors = SplitLeak) -> tuple[bool, str]:
    """(raised, message). Any other exception propagates and fails the check."""
    try:
        action()
    except errors as error:  # type: ignore[misc]
        return True, f"{type(error).__name__}: {error}"[:400]
    return False, ""


def _audit(examples: Iterable[Episode], registry: SplitRegistry, **kwargs: Any) -> tuple[bool, list[str]]:
    """(clean, violations) of `audit_examples` with the toy's vocabulary."""
    try:
        audit_examples(list(examples), registry, text_of=lambda e: e.text, vocab=split_vocab(), **kwargs)
    except SplitLeak as leak:
        return False, list(leak.violations)
    return True, []


def _streams(registry: SplitRegistry, count: int = STREAM) -> dict[str, list[Episode]]:
    return {split: episodes(registry, split, count) for split in SPLITS}


def _in_split(registry: SplitRegistry, axis: str, items: Iterable[str], split: str) -> list[str]:
    return [item for item in items if registry.split_of(axis, item) == split]


def _rename(episode: Episode, old: str, new: str, *, provenance: bool) -> Episode:
    """The same episode with name `old` written as `new`; provenance updated only if asked."""
    swap = lambda text: re.sub(rf"\b{re.escape(old)}\b", new, text)  # noqa: E731
    fix = lambda fact: replace(fact, name=new) if fact.name == old else fact  # noqa: E731
    names = tuple(new if name == old else name for name in episode.provenance.get("name", ()))
    return replace(
        episode,
        episode_id=f"{episode.episode_id}-renamed",
        lines=tuple(swap(line) for line in episode.lines),
        question=swap(episode.question),
        facts=tuple(fix(fact) for fact in episode.facts),
        target=fix(episode.target),
        provenance={**episode.provenance, "name": names} if provenance else dict(episode.provenance),
    )


def _mentions(violations: list[str], *needles: str) -> bool:
    return any(all(needle in violation for needle in needles) for violation in violations)


# ---------------------------------------------------------------- clean controls

def check_clean_streams() -> dict[str, Any]:
    registry = make_registry()
    streams = _streams(registry)
    everything = [e for split in SPLITS for e in streams[split]]
    disjoint_raised, disjoint_message = _raises(registry.assert_disjoint)
    audit_clean, violations = _audit(everything, registry)
    consume_failures = [
        split for split in SPLITS
        if _raises(lambda split=split: list(consumable(streams[split], split, registry=registry)))[0]
    ]
    # Independent of the registry's own bookkeeping: provenance item sets never overlap.
    by_split = {
        axis: {split: {item for e in streams[split] for item in e.provenance.get(axis, ())} for split in SPLITS}
        for axis in ("name", *FIXED_AXES)
    }
    overlaps = [
        f"{axis}: {first}&{second}"
        for axis, sets in by_split.items()
        for i, first in enumerate(SPLITS)
        for second in SPLITS[i + 1:]
        if sets[first] & sets[second]
    ]
    labelled = all(e.split == split and e.provenance for split in SPLITS for e in streams[split])
    return check(
        "splits: clean toy streams are disjoint, pass the audit and are consumable",
        not disjoint_raised and audit_clean and not consume_failures and not overlaps and labelled,
        episodes=len(everything),
        disjoint_error=disjoint_message,
        audit_violations=violations[:8],
        consume_failures=consume_failures,
        provenance_overlaps=overlaps,
        summary=registry.summary(),
    )


def check_manifest_round_trip() -> dict[str, Any]:
    registry = make_registry()
    saved = registry.manifest()
    text = saved.to_json()
    parsed = SplitManifest.from_json(text)
    round_trip = parsed == saved and parsed.digest() == saved.digest() and parsed.to_json() == text
    episodes(registry, "train", 10)  # recording uses must not change the assignment
    live_raised = [
        label for label, target in (("json", text), ("object", saved))
        if _raises(lambda target=target: make_registry().verify_manifest(target))[0]
    ]
    after_use_raised, after_use_message = _raises(lambda: registry.verify_manifest(text))
    rebuilt = SplitRegistry.from_manifest(text)
    same_assignment = (
        rebuilt.fixed == registry.fixed
        and rebuilt.manifest().digest() == saved.digest()
        and all(rebuilt.split_of("name", n) == registry.split_of("name", n) for n in all_names())
    )
    return check(
        "splits: the manifest round-trips through JSON and verifies against the live registry",
        round_trip and not live_raised and not after_use_raised and same_assignment,
        round_trip=round_trip,
        live_verify_failures=live_raised,
        after_use_error=after_use_message,
        rebuilt_matches=same_assignment,
        digest=saved.digest(),
    )


def check_every_split_gets_each_family() -> dict[str, Any]:
    registry = make_registry()
    fixed = registry.fixed
    family_splits = {axis: sorted(set(fixed[axis].values())) for axis in FIXED_AXES}
    streams = _streams(registry)
    received = {
        axis: {split: sorted({item for e in streams[split] for item in e.provenance.get(axis, ())}) for split in SPLITS}
        for axis in FIXED_AXES
    }
    missing = [
        f"{axis} in {split}" for axis in FIXED_AXES for split in SPLITS
        if split not in family_splits[axis] or not received[axis][split]
    ]
    return check(
        "splits: every split receives at least one template, teacher style and rule family",
        not missing,
        missing=missing,
        received=received,
    )


# ---------------------------------------------------------------- planted flaws

def check_test_name_through_view() -> dict[str, Any]:
    registry = make_registry()
    names = all_names()
    test_names = _in_split(registry, "name", names, "test")
    train_names = _in_split(registry, "name", names, "train")
    planted = registry.view("train")
    used, use_message = _raises(lambda: planted.use("name", test_names[0]))
    drawn, draw_message = _raises(
        lambda: registry.view("train").draw("name", test_names, random.Random(0)), ValueError
    )
    no_trace = test_names[0] not in registry.used["name"]["train"] and planted.provenance() == {}
    # Clean control: a train name through the train view is recorded, draws stay in train.
    clean = registry.view("train")
    clean.use("name", train_names[0])
    chosen = clean.draw("name", names, random.Random(0), k=4)
    clean_ok = (
        registry.used["name"]["train"] >= {train_names[0], *chosen}
        and set(clean.provenance()["name"]) == {train_names[0], *chosen}
        and all(registry.split_of("name", n) == "train" for n in chosen)
        and not _raises(registry.assert_disjoint)[0]
    )
    return check(
        "splits: a test name used in training through a view is refused",
        used and drawn and no_trace and clean_ok,
        caught_use=used, use_error=use_message, caught_draw=drawn, draw_error=draw_message,
        left_no_record=no_trace, clean_control_ok=clean_ok, test_name=test_names[0],
    )


def check_generator_skips_record() -> dict[str, Any]:
    registry = make_registry()
    clean = episodes(registry, "test", 6)
    base = clean[0]
    unrecorded = next(
        n for n in _in_split(registry, "name", all_names(), "test") if n not in registry.used["name"]["test"]
    )
    old = base.facts[0].name
    # Three bypassing generators, each using only test-split items so no foreign text gives them away:
    variants = {
        # draws a name itself and lists it, but never calls record()
        "listed_unrecorded": _rename(base, old, unrecorded, provenance=True),
        # draws a name itself and leaves the view's provenance as it was
        "unlisted": _rename(base, old, unrecorded, provenance=False),
        # builds the episode without any view: the dataclass default provenance
        "no_view": replace(base, episode_id=base.episode_id + "-noview", provenance={}),
    }
    caught = {}
    evidence = {}
    for label, episode in variants.items():
        audit_clean, violations = _audit([*clean, episode], registry)
        caught[label] = not audit_clean
        evidence[label] = violations[:3]
    clean_ok, clean_violations = _audit(clean, registry)
    return check(
        "splits: a generator that skips record() is caught by audit_examples",
        all(caught.values()) and clean_ok,
        caught=caught, violations=evidence, clean_control_violations=clean_violations[:4],
        unrecorded_name=unrecorded,
    )


def check_test_text_mentions_train_name() -> dict[str, Any]:
    registry = make_registry()
    base = episodes(registry, "test", 1)[0]
    train_name = next(
        n for n in _in_split(registry, "name", all_names(), "train") if n not in base.provenance["name"]
    )
    # Provenance still lists only test names, so only the independent text scan can see it.
    planted = _rename(base, base.target.name, train_name, provenance=False)
    distractor = replace(base, episode_id=base.episode_id + "-distractor",
                         lines=(*base.lines, f"{train_name.capitalize()} waves from the road."))
    results = {}
    for label, episode in (("renamed_target", planted), ("distractor_line", distractor)):
        audit_clean, violations = _audit([episode], registry, require_recorded=False)
        results[label] = (not audit_clean and _mentions(violations, "train name", repr(train_name)), violations[:3])
    clean_ok, clean_violations = _audit([base], registry, require_recorded=False)
    return check(
        "splits: a test episode whose text mentions a train name is caught",
        all(caught for caught, _ in results.values()) and clean_ok,
        caught={label: caught for label, (caught, _) in results.items()},
        violations={label: violations for label, (_, violations) in results.items()},
        clean_control_violations=clean_violations[:4], train_name=train_name,
    )


def _with_rule_line(episode: Episode, family: str) -> Episode:
    """The episode with its rule line replaced by (or, for `direct`, appended as) `family`'s surface."""
    first, second = episode.facts[0], episode.facts[1]
    line = RULE_FAMILIES[family].format(name=first.name, obj=first.obj, other=second.name, other_obj=second.obj)
    kept = episode.lines if RULE_FAMILIES[episode.rule_family] is None else episode.lines[:-1]
    return replace(episode, episode_id=f"{episode.episode_id}-as-{family}", lines=(*kept, line))


def check_cross_rule_family_leak() -> dict[str, Any]:
    registry = make_registry()
    fixed = registry.fixed["rule_family"]
    train_forms = sorted(f for f, s in fixed.items() if s == "train" and RULE_FAMILIES[f] is not None)
    held_out = [e for split in ("validation", "test") for e in episodes(registry, split, 6)]
    planted, missed, evidence = 0, [], {}
    for episode in held_out[:: max(1, len(held_out) // 4)]:
        for family in train_forms:
            leaked = _with_rule_line(episode, family)
            audit_clean, violations = _audit([leaked], registry)
            planted += 1
            if audit_clean or not _mentions(violations, "train rule_family", repr(family)):
                missed.append(leaked.episode_id)
            evidence.setdefault(family, violations[:2])
    # Clean control: the same held-out episodes, and each re-rendered with its own family's line.
    own = [_with_rule_line(e, e.rule_family) for e in held_out if RULE_FAMILIES[e.rule_family] is not None]
    clean_ok, clean_violations = _audit([*held_out, *own], registry, require_recorded=True)
    return check(
        "splits: a held-out episode using a train rule family's surface form is caught",
        planted > 0 and not missed and clean_ok,
        planted=planted, missed=missed, train_families=train_forms,
        held_out_families={s: sorted(f for f, v in fixed.items() if v == s) for s in ("validation", "test")},
        violations=evidence, clean_control_violations=clean_violations[:4],
    )


def check_same_version_membership_change() -> dict[str, Any]:
    registry = make_registry()
    saved_json = registry.manifest().to_json()
    before = registry.family("template")
    version = FAMILY_VERSIONS["template"]
    grown = [*TEMPLATES, "t12"]
    shrunk = sorted(TEMPLATES)[1:]
    added, added_message = _raises(lambda: registry.fix_family("template", grown, version))
    removed, removed_message = _raises(lambda: registry.fix_family("template", shrunk, version))
    unchanged = registry.family("template") == before
    # Another process fixes the grown family under the old version: its manifest disagrees.
    other = SplitRegistry(salt=registry.salt, fractions=registry.fractions)
    other.fix_family("template", grown, version)
    other.fix_family("teacher_style", STYLES, FAMILY_VERSIONS["teacher_style"])
    other.fix_family("rule_family", RULE_FAMILIES, FAMILY_VERSIONS["rule_family"])
    cross_process, cross_message = _raises(lambda: other.verify_manifest(saved_json))
    # Clean control: identical membership under the same version is accepted and changes nothing.
    same = registry.fix_family("template", list(reversed(list(TEMPLATES))), version) == before.as_dict()
    clean_ok = same and registry.family("template") == before and not _raises(
        lambda: registry.verify_manifest(saved_json))[0]
    return check(
        "splits: a family membership change under the same version is refused",
        added and removed and unchanged and cross_process and clean_ok,
        caught_added=added, caught_removed=removed, family_unchanged=unchanged,
        caught_by_saved_manifest=cross_process, clean_control_ok=clean_ok,
        errors=[added_message, removed_message, cross_message],
    )


def check_stale_record_after_refix() -> dict[str, Any]:
    registry = make_registry()
    episodes(registry, "validation", 12)
    episodes(registry, "test", 12)
    used = {s: set(registry.used["template"][s]) for s in SPLITS}
    # The attempt under the same version fails and leaves the records valid.
    attempt, _ = _raises(lambda: registry.fix_family("template", [*TEMPLATES, "t12"], FAMILY_VERSIONS["template"]))
    after_attempt_raised, _ = _raises(registry.assert_disjoint)
    # Clean control: a version bump with identical membership moves nothing.
    registry.fix_family("template", TEMPLATES, "templates-v1b")
    bump_raised, bump_message = _raises(registry.assert_disjoint)
    # Planted: grow the family under a new version until a recorded template changes split.
    extras: list[str] = []
    moved: list[str] = []
    for index in range(12, 60):
        extras.append(f"t{index}")
        assignment = assign_ranked("template", [*TEMPLATES, *extras], salt=registry.salt, fractions=registry.fractions)
        moved = sorted(t for s in SPLITS for t in used[s] if assignment[t] != s)
        if moved:
            break
    registry.fix_family("template", [*TEMPLATES, *extras], "templates-v2")
    stale_raised, stale_message = _raises(registry.assert_disjoint)
    # Planted: a new version that drops a recorded template.
    dropper = make_registry()
    episodes(dropper, "train", 4)
    dropped = sorted(dropper.used["template"]["train"])[0]
    dropper.fix_family("template", [t for t in TEMPLATES if t != dropped], "templates-v2")
    dropped_raised, dropped_message = _raises(dropper.assert_disjoint)
    return check(
        "splits: a stale record after a family re-fix is caught by assert_disjoint",
        attempt and not after_attempt_raised and not bump_raised and bool(moved)
        and stale_raised and "stale template record" in stale_message
        and dropped_raised and "no longer a family member" in dropped_message,
        same_version_refused=attempt, moved=moved, extras=len(extras),
        clean_bump_error=bump_message, stale_error=stale_message, dropped_error=dropped_message,
    )


def check_test_episode_consumed_by_training() -> dict[str, Any]:
    registry = make_registry()
    train = episodes(registry, "train", 5)
    test = episodes(registry, "test", 5)
    relabelled = replace(test[0], split="train")
    unlabelled = {"text": test[0].text, "provenance": dict(test[0].provenance)}
    no_provenance = replace(train[0], provenance={})
    planted = {
        "test_in_train_loop": _raises(lambda: list(consumable([*train, test[0]], "train")))[0],
        "relabelled_with_registry": _raises(lambda: assert_consumable(relabelled, "train", registry=registry))[0],
        "unlabelled": _raises(lambda: assert_consumable(unlabelled, "train"))[0],
        "no_provenance_with_registry": _raises(
            lambda: assert_consumable(no_provenance, "train", registry=registry))[0],
    }
    clean_ok = (
        list(consumable(train, "train", registry=registry)) == train
        and list(consumable(test, "test", registry=registry)) == test
    )
    return check(
        "splits: a test episode consumed by training is caught by assert_consumable",
        all(planted.values()) and clean_ok,
        caught=planted, clean_control_ok=clean_ok,
    )


def check_fractions_and_small_family() -> dict[str, Any]:
    bad = [(1.2, -0.1, -0.1), (2, -1, 0), (0.5, 0.5), (0.8, 0.1, 0.2), (float("nan"), 0.5, 0.5),
           (float("inf"), 0, 0), (True, 0, 0), "0.8,0.1,0.1", (0.8, 0.1, 0.1, 0.0)]
    accepted_bad = [repr(f) for f in bad if not _raises(lambda f=f: validate_fractions(f), ValueError)[0]]
    registry_refused = _raises(lambda: SplitRegistry(fractions=(1.2, -0.1, -0.1)), ValueError)[0]
    three = assign_ranked("template", ["a", "b", "c"])
    seven = assign_ranked("template", [f"x{i}" for i in range(7)], fractions=(0.95, 0.025, 0.025))
    every_split = all(sorted(set(a.values())) == sorted(SPLITS) for a in (three, seven))
    too_small = _raises(lambda: assign_ranked("template", ["a", "b"]), ValueError)[0]
    good = [(0.8, 0.1, 0.1), (0.5, 0.25, 0.25), (0.7, 0.2, 0.1), (1, 0, 0)]
    refused_good = [repr(f) for f in good if _raises(lambda f=f: validate_fractions(f), ValueError)[0]]
    all_train = set(assign_ranked("template", ["a", "b", "c"], fractions=(1, 0, 0)).values()) == {"train"}
    sizes_ok = allocate(8) == (6, 1, 1) and sum(allocate(13, (0.5, 0.25, 0.25))) == 13
    return check(
        "splits: invalid fractions are refused and a 3-item family still fills every split",
        not accepted_bad and registry_refused and every_split and too_small
        and not refused_good and all_train and sizes_ok,
        accepted_bad=accepted_bad, registry_refused=registry_refused, three_item=three,
        seven_item_skewed=sorted(seven.values()), two_item_refused=too_small,
        refused_good=refused_good, zero_fraction_splits_empty=all_train, allocations_ok=sizes_ok,
    )


def check_manifest_disagrees_with_registry() -> dict[str, Any]:
    saved = make_registry().manifest()
    saved_json = saved.to_json()

    def tampered(edit: Callable[[dict], None]) -> str:
        data = json.loads(saved_json)
        edit(data)
        return json.dumps(data)

    first_template = sorted(saved.family("template").as_dict())[0]
    moved_to = next(s for s in SPLITS if s != saved.family("template").split_of(first_template))

    def move(data: dict) -> None:
        data["families"]["template"]["assignment"][first_template] = moved_to

    def drop_style(data: dict) -> None:
        del data["families"]["teacher_style"]

    def rename_version(data: dict) -> None:
        data["families"]["rule_family"]["version"] = "rules-v0"

    def canary(data: dict) -> None:
        data["canary"] = "0" * 64

    other_salt = SplitRegistry(salt="another-salt", fractions=saved.fractions)
    other_fractions = SplitRegistry(salt=saved.salt, fractions=(0.6, 0.2, 0.2))
    unfixed = SplitRegistry(salt=saved.salt, fractions=saved.fractions)
    unfixed.fix_family("template", TEMPLATES, FAMILY_VERSIONS["template"])
    unfixed.fix_family("teacher_style", STYLES, FAMILY_VERSIONS["teacher_style"])
    bumped = make_registry()
    bumped.fix_family("template", [*TEMPLATES, "t12"], "templates-v2")
    for live in (other_salt, other_fractions):
        for axis in ("template", "teacher_style", "rule_family"):
            live.fix_family(axis, saved.family(axis).members(), saved.family(axis).version)
    cases = {
        "saved_moved_item": (make_registry(), tampered(move)),
        "saved_missing_family": (make_registry(), tampered(drop_style)),
        "saved_other_version": (make_registry(), tampered(rename_version)),
        "saved_bad_canary": (make_registry(), tampered(canary)),
        "live_other_salt": (other_salt, saved_json),
        "live_other_fractions": (other_fractions, saved_json),
        "live_unfixed_rule_family": (unfixed, saved_json),
        "live_new_template_version": (bumped, saved_json),
    }
    caught, messages = {}, {}
    for label, (live, manifest) in cases.items():
        caught[label], messages[label] = _raises(lambda live=live, manifest=manifest: live.verify_manifest(manifest))
    canary_rebuild = _raises(lambda: SplitRegistry.from_manifest(tampered(canary)))[0]
    clean_ok = not _raises(lambda: make_registry().verify_manifest(saved_json))[0]
    return check(
        "splits: a saved manifest that disagrees with the live registry is rejected by verify_manifest",
        all(caught.values()) and canary_rebuild and clean_ok,
        caught=caught, rebuild_with_bad_canary_refused=canary_rebuild, clean_control_ok=clean_ok,
        errors={label: message[:200] for label, message in messages.items()},
    )


CHECKS: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
    ("splits: clean toy streams are disjoint, pass the audit and are consumable", check_clean_streams),
    ("splits: the manifest round-trips through JSON and verifies against the live registry",
     check_manifest_round_trip),
    ("splits: every split receives at least one template, teacher style and rule family",
     check_every_split_gets_each_family),
    ("splits: a test name used in training through a view is refused", check_test_name_through_view),
    ("splits: a generator that skips record() is caught by audit_examples", check_generator_skips_record),
    ("splits: a test episode whose text mentions a train name is caught", check_test_text_mentions_train_name),
    ("splits: a held-out episode using a train rule family's surface form is caught", check_cross_rule_family_leak),
    ("splits: a family membership change under the same version is refused", check_same_version_membership_change),
    ("splits: a stale record after a family re-fix is caught by assert_disjoint", check_stale_record_after_refix),
    ("splits: a test episode consumed by training is caught by assert_consumable",
     check_test_episode_consumed_by_training),
    ("splits: invalid fractions are refused and a 3-item family still fills every split",
     check_fractions_and_small_family),
    ("splits: a saved manifest that disagrees with the live registry is rejected by verify_manifest",
     check_manifest_disagrees_with_registry),
)


def checks() -> list[dict[str, Any]]:
    """Every splits check; one that crashes is recorded as failed rather than stopping the rest."""
    results = []
    for name, run in CHECKS:
        try:
            results.append(run())
        except Exception as error:  # a crashing check is a failed check
            results.append(check(name, False, error=f"{type(error).__name__}: {error}",
                                 traceback=traceback.format_exc(limit=6)))
    return results


__all__ = ["CHECKS", "checks"]
