"""Held-out splits by whole families, not merely by names.

Every generated item (a name, a narrator template, a teacher style, a rule
family) belongs to exactly one of train/validation/test. Large pools (names)
are split by a salted hash, which is stable when the pool grows. Small fixed
families are split by hash rank under an explicit version and frozen into a
`SplitManifest` that is saved with each checkpoint and verified by later runs.

Generators draw items only through `registry.view(split)`, which records every
use and builds each example's provenance. Because a generator can still bypass
the view, `audit_examples` independently scans example text for items of other
splits, and `assert_consumable` checks every example where a loop consumes it.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import numbers
import random
import re
import string
from types import MappingProxyType
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, Sequence, Union

SPLITS = ("train", "validation", "test")
AXES = ("name", "template", "teacher_style", "rule_family")
DEFAULT_SALT = "learnlab-splits-v1"
DEFAULT_FRACTIONS = (0.8, 0.1, 0.1)
SCHEME = "sha256-threshold+largest-remainder-rank/2"  # bump when either assignment rule changes
MANIFEST_FORMAT = 1
_CANARY_ITEMS = 64
_REPORT_LIMIT = 8


class SplitLeak(AssertionError):
    """An item crossed splits, or the split bookkeeping cannot prove it did not."""

    def __init__(self, message: str, violations: Iterable[str] = ()) -> None:
        super().__init__(message)
        self.violations = tuple(violations)


def _raise_if(problems: Sequence[str], heading: str) -> None:
    if not problems:
        return
    shown = "; ".join(problems[:_REPORT_LIMIT])
    more = f"; ... and {len(problems) - _REPORT_LIMIT} more" if len(problems) > _REPORT_LIMIT else ""
    raise SplitLeak(f"{heading} ({len(problems)}): {shown}{more}", problems)


def _short(items: Sequence[Any], limit: int = 5) -> str:
    shown = ", ".join(repr(item) for item in list(items)[:limit])
    return f"[{shown}{', ...' if len(items) > limit else ''}]"


def _check_axis(axis: str) -> str:
    if axis not in AXES:
        raise ValueError(f"unknown split axis {axis!r}")
    return axis


def _check_split(split: str) -> str:
    if split not in SPLITS:
        raise ValueError(f"unknown split {split!r}")
    return split


def _check_item(item: str) -> str:
    if not isinstance(item, str) or not item:
        raise ValueError(f"split items must be nonempty strings, got {item!r}")
    return item


def _check_version(version: str) -> str:
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"a family version must be a nonempty string, got {version!r}")
    return version


def validate_fractions(fractions: Sequence[float]) -> tuple[float, float, float]:
    """Return three finite nonnegative fractions summing to 1 (within 1e-9) as floats."""
    if isinstance(fractions, (str, bytes)):
        raise ValueError(f"fractions must be three numbers, got {fractions!r}")
    try:
        values = tuple(fractions)
    except TypeError:
        raise ValueError(f"fractions must be three numbers, got {fractions!r}") from None
    if len(values) != 3:
        raise ValueError(f"fractions must be three numbers (train, validation, test), got {values!r}")
    for value in values:
        if isinstance(value, bool) or not isinstance(value, numbers.Real):
            raise ValueError(f"fractions must be real numbers, got {value!r}")
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"fractions must be finite and nonnegative, got {values!r}")
    if abs(sum(float(value) for value in values) - 1.0) > 1e-9:
        raise ValueError(f"fractions must sum to 1, got {values!r}")
    return (float(values[0]), float(values[1]), float(values[2]))


def _digest(salt: str, axis: str, item: str) -> bytes:
    return hashlib.sha256(f"{salt}|{axis}|{item}".encode()).digest()


def assign(
    axis: str,
    item: str,
    *,
    salt: str = DEFAULT_SALT,
    fractions: Sequence[float] = DEFAULT_FRACTIONS,
) -> str:
    """Hash one item of a large pool into a split; unaffected by the rest of the pool."""
    _check_axis(axis)
    _check_item(item)
    values = validate_fractions(fractions)
    position = int.from_bytes(_digest(salt, axis, item)[:8], "big") / 2**64
    cumulative = 0.0
    for split, fraction in zip(SPLITS, values):
        cumulative += fraction
        if fraction > 0 and position < cumulative:
            return split
    # Float rounding can leave the cumulative sum a hair below 1.
    return [split for split, fraction in zip(SPLITS, values) if fraction > 0][-1]


def allocate(count: int, fractions: Sequence[float] = DEFAULT_FRACTIONS) -> tuple[int, int, int]:
    """Split sizes for a family of `count` items.

    Largest-remainder apportionment in exact arithmetic, then every split with a
    positive fraction is guaranteed at least one item (taken from the split most
    over its quota). Splits with a zero fraction get nothing.
    """
    values = validate_fractions(fractions)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError(f"count must be a nonnegative integer, got {count!r}")
    positive = [index for index, value in enumerate(values) if value > 0]
    if count < len(positive):
        raise ValueError(
            f"a family of {count} items cannot give each of the {len(positive)} "
            "splits with a positive fraction at least one item"
        )
    exact = [Fraction(value) for value in values]
    total = sum(exact)
    quotas = [count * value / total for value in exact]
    counts = [math.floor(quota) for quota in quotas]
    by_remainder = sorted(positive, key=lambda index: (-(quotas[index] - counts[index]), index))
    for index in by_remainder[: count - sum(counts)]:
        counts[index] += 1
    for index in positive:
        if counts[index] == 0:
            donor = max(
                (other for other in positive if counts[other] > 1),
                key=lambda other: (counts[other] - quotas[other], counts[other], -other),
            )
            counts[donor] -= 1
            counts[index] += 1
    return (counts[0], counts[1], counts[2])


def assign_ranked(
    axis: str,
    items: Iterable[str],
    *,
    salt: str = DEFAULT_SALT,
    fractions: Sequence[float] = DEFAULT_FRACTIONS,
) -> dict[str, str]:
    """Split a small fixed family (templates, styles, rule families) by hash rank.

    Threshold hashing is lumpy for a handful of items and can leave a split
    empty, so items are ranked by hash and cut at the `allocate` sizes. The
    result depends on the whole membership: adding or removing one member can
    move others, which is why families are frozen under a version by
    `SplitRegistry.fix_family` and checked with `verify_manifest`.
    """
    _check_axis(axis)
    if isinstance(items, (str, bytes)):
        raise ValueError("items must be an iterable of item names, not one string")
    members = sorted({_check_item(item) for item in items})
    sizes = allocate(len(members), fractions)
    ranked = sorted(members, key=lambda item: _digest(salt, axis, item))
    result: dict[str, str] = {}
    start = 0
    for split, size in zip(SPLITS, sizes):
        for item in ranked[start:start + size]:
            result[item] = split
        start += size
    return result


def items_in(
    axis: str,
    candidates: Iterable[str],
    split: str,
    *,
    salt: str = DEFAULT_SALT,
    fractions: Sequence[float] = DEFAULT_FRACTIONS,
) -> list[str]:
    """The candidates the hash path assigns to `split`, in their given order."""
    _check_split(split)
    return [
        item
        for item in candidates
        if assign(axis, item, salt=salt, fractions=fractions) == split
    ]


def hash_canary(salt: str, fractions: Sequence[float]) -> str:
    """Digest of the hash path on fixed probe items; changes if `assign` changes."""
    values = validate_fractions(fractions)
    digest = hashlib.sha256()
    for axis in AXES:
        for index in range(_CANARY_ITEMS):
            split = assign(axis, f"canary-{index}", salt=salt, fractions=values)
            digest.update(f"{axis}|{index}|{split}\n".encode())
    return digest.hexdigest()


@dataclass(frozen=True)
class FamilyManifest:
    """One fixed family's frozen assignment under a named version."""

    axis: str
    version: str
    assignment: tuple[tuple[str, str], ...]  # sorted (item, split) pairs

    def __post_init__(self) -> None:
        _check_axis(self.axis)
        _check_version(self.version)
        raw = self.assignment.items() if isinstance(self.assignment, Mapping) else self.assignment
        pairs = []
        for pair in raw:
            item, split = pair
            pairs.append((_check_item(item), _check_split(split)))
        lookup = dict(pairs)
        if len(lookup) != len(pairs):
            raise ValueError(f"{self.axis} family {self.version!r} lists an item twice")
        object.__setattr__(self, "assignment", tuple(sorted(pairs)))
        object.__setattr__(self, "_lookup", MappingProxyType(lookup))

    def members(self) -> frozenset[str]:
        return frozenset(self._lookup)

    def split_of(self, item: str) -> str:
        if item not in self._lookup:
            raise KeyError(f"{item!r} is not a member of the fixed {self.axis} family {self.version!r}")
        return self._lookup[item]

    def as_dict(self) -> dict[str, str]:
        return dict(self.assignment)


@dataclass(frozen=True)
class SplitManifest:
    """Everything that decides split membership, frozen for saving with a checkpoint.

    Axes with a family are split by the family's frozen assignment; all other
    axes by the hash path, pinned by `salt`, `fractions` and `canary`.
    """

    salt: str
    fractions: tuple[float, float, float]
    families: tuple[FamilyManifest, ...]
    canary: str
    scheme: str = SCHEME
    format_version: int = MANIFEST_FORMAT

    def __post_init__(self) -> None:
        if not isinstance(self.salt, str) or not self.salt:
            raise ValueError("a manifest needs a nonempty salt")
        object.__setattr__(self, "fractions", validate_fractions(self.fractions))
        families = tuple(self.families.values()) if isinstance(self.families, Mapping) else tuple(self.families)
        if not all(isinstance(family, FamilyManifest) for family in families):
            raise ValueError("manifest families must be FamilyManifest objects")
        axes = [family.axis for family in families]
        if len(set(axes)) != len(axes):
            raise ValueError(f"a manifest may fix each axis once, got {axes}")
        object.__setattr__(self, "families", tuple(sorted(families, key=lambda family: family.axis)))
        if not isinstance(self.canary, str) or not self.canary:
            raise ValueError("a manifest needs the hash canary")
        if not isinstance(self.scheme, str) or not self.scheme:
            raise ValueError("a manifest needs a scheme")
        if isinstance(self.format_version, bool) or not isinstance(self.format_version, int):
            raise ValueError("format_version must be an integer")

    def family(self, axis: str) -> Optional[FamilyManifest]:
        _check_axis(axis)
        return next((family for family in self.families if family.axis == axis), None)

    def payload(self) -> dict[str, Any]:
        return {
            "format": self.format_version,
            "scheme": self.scheme,
            "salt": self.salt,
            "fractions": list(self.fractions),
            "canary": self.canary,
            "families": {
                family.axis: {"version": family.version, "assignment": family.as_dict()}
                for family in self.families
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.payload(), sort_keys=True, indent=2)

    def digest(self) -> str:
        canonical = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    @classmethod
    def from_json(cls, text: str) -> "SplitManifest":
        """Parse a saved manifest; raise ValueError on anything malformed or unknown."""
        try:
            data = json.loads(text)
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError(f"split manifest is not valid JSON: {error}") from None
        expected = {"format", "scheme", "salt", "fractions", "canary", "families"}
        if not isinstance(data, dict) or set(data) != expected:
            keys = sorted(data) if isinstance(data, dict) else type(data).__name__
            raise ValueError(f"split manifest must have exactly the keys {sorted(expected)}, got {keys}")
        if data["format"] != MANIFEST_FORMAT:
            raise ValueError(f"unsupported split manifest format {data['format']!r}")
        if not isinstance(data["families"], dict):
            raise ValueError("manifest families must be an object keyed by axis")
        families = []
        for axis, body in data["families"].items():
            if not isinstance(body, dict) or set(body) != {"version", "assignment"}:
                raise ValueError(f"manifest family {axis!r} must have exactly 'version' and 'assignment'")
            if not isinstance(body["assignment"], dict):
                raise ValueError(f"manifest family {axis!r} assignment must be an object")
            families.append(FamilyManifest(axis, body["version"], tuple(body["assignment"].items())))
        return cls(
            salt=data["salt"],
            fractions=tuple(data["fractions"]) if isinstance(data["fractions"], list) else data["fractions"],
            families=tuple(families),
            canary=data["canary"],
            scheme=data["scheme"],
            format_version=data["format"],
        )


def _as_manifest(manifest: Union[SplitManifest, str]) -> SplitManifest:
    if isinstance(manifest, SplitManifest):
        return manifest
    if isinstance(manifest, str):
        return SplitManifest.from_json(manifest)
    raise TypeError(f"expected a SplitManifest or its JSON, got {type(manifest).__name__}")


def manifest_differences(saved: SplitManifest, current: SplitManifest) -> list[str]:
    """Every way `current` disagrees with `saved`; empty when they are identical."""
    problems = []
    for field in ("format_version", "scheme", "salt", "fractions"):
        before, after = getattr(saved, field), getattr(current, field)
        if before != after:
            problems.append(f"{field} changed: saved {before!r}, now {after!r}")
    if saved.canary != current.canary and saved.salt == current.salt and saved.fractions == current.fractions:
        problems.append("hash assignment changed: the canary items now land in different splits")
    for axis in AXES:
        before, after = saved.family(axis), current.family(axis)
        if before is None and after is None:
            continue
        if before is None:
            problems.append(f"{axis}: now a fixed family (version {after.version!r}) but hashed when saved")
            continue
        if after is None:
            problems.append(f"{axis}: a fixed family when saved (version {before.version!r}) but not fixed now")
            continue
        if before.version != after.version:
            problems.append(f"{axis}: family version changed from {before.version!r} to {after.version!r}")
        elif before != after:
            problems.append(f"{axis}: family version {before.version!r} has different contents than when saved")
        old, new = before.as_dict(), after.as_dict()
        added = sorted(new.keys() - old.keys())
        removed = sorted(old.keys() - new.keys())
        moved = sorted(
            f"{item}: {old[item]}->{new[item]}" for item in old.keys() & new.keys() if old[item] != new[item]
        )
        if added:
            problems.append(f"{axis}: members added {_short(added)}")
        if removed:
            problems.append(f"{axis}: members removed {_short(removed)}")
        if moved:
            problems.append(f"{axis}: members moved between splits {_short(moved)}")
    return problems


class SplitRegistry:
    """One experiment's split assignment plus a record of what each split used."""

    def __init__(
        self,
        *,
        salt: str = DEFAULT_SALT,
        fractions: Sequence[float] = DEFAULT_FRACTIONS,
    ) -> None:
        if not isinstance(salt, str) or not salt:
            raise ValueError("salt must be a nonempty string")
        self._salt = salt
        self._fractions = validate_fractions(fractions)
        self.used: dict[str, dict[str, set[str]]] = {axis: defaultdict(set) for axis in AXES}
        self._families: dict[str, FamilyManifest] = {}
        self._hashed: dict[tuple[str, str], str] = {}

    @classmethod
    def from_manifest(cls, manifest: Union[SplitManifest, str]) -> "SplitRegistry":
        """Rebuild the exact assignment a checkpoint was trained under."""
        saved = _as_manifest(manifest)
        if saved.format_version != MANIFEST_FORMAT:
            raise SplitLeak(f"manifest format {saved.format_version!r} is not {MANIFEST_FORMAT}")
        if saved.scheme != SCHEME:
            raise SplitLeak(f"manifest uses split scheme {saved.scheme!r}; this code implements {SCHEME!r}")
        registry = cls(salt=saved.salt, fractions=saved.fractions)
        if hash_canary(registry.salt, registry.fractions) != saved.canary:
            raise SplitLeak("hash assignment changed since the manifest was saved: canary items moved")
        registry._families = {family.axis: family for family in saved.families}
        return registry

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def fractions(self) -> tuple[float, float, float]:
        return self._fractions

    @property
    def fixed(self) -> dict[str, dict[str, str]]:
        """A copy of every fixed family's item -> split assignment."""
        return {axis: family.as_dict() for axis, family in self._families.items()}

    def family(self, axis: str) -> Optional[FamilyManifest]:
        return self._families.get(_check_axis(axis))

    def fix_family(self, axis: str, items: Iterable[str], version: str) -> dict[str, str]:
        """Freeze a small family's rank-based split under `version`.

        Re-fixing the same version is allowed only with identical membership
        (SplitLeak otherwise). A new version replaces the family; any item already
        recorded under the old one that now moves is caught by `assert_disjoint`,
        and a saved manifest from before is rejected by `verify_manifest`.
        """
        _check_axis(axis)
        _check_version(version)
        assignment = assign_ranked(axis, items, salt=self.salt, fractions=self.fractions)
        current = self._families.get(axis)
        if current is not None and current.version == version:
            members = frozenset(assignment)
            if members != current.members():
                added = sorted(members - current.members())
                removed = sorted(current.members() - members)
                raise SplitLeak(
                    f"{axis} family version {version!r} is already fixed with different membership "
                    f"(added {_short(added)}, removed {_short(removed)}); give the new membership a new version"
                )
            return current.as_dict()
        self._families[axis] = FamilyManifest(axis, version, tuple(assignment.items()))
        return dict(assignment)

    def split_of(self, axis: str, item: str) -> str:
        family = self._families.get(_check_axis(axis))
        if family is not None:
            return family.split_of(item)
        key = (axis, item)
        if key not in self._hashed:
            self._hashed[key] = assign(axis, item, salt=self.salt, fractions=self.fractions)
        return self._hashed[key]

    def record(self, axis: str, item: str, split: str) -> None:
        """Note that `split` used `item`; SplitLeak if the item belongs elsewhere."""
        _check_split(split)
        assigned = self.split_of(axis, item)
        if assigned != split:
            raise SplitLeak(f"{axis} {item!r} is assigned to {assigned} but was used in {split}")
        self.used[axis][split].add(item)

    def view(self, split: str) -> "SplitView":
        """A fresh view for generating one example of `split`."""
        return SplitView(self, _check_split(split))

    def manifest(self) -> SplitManifest:
        return SplitManifest(
            salt=self.salt,
            fractions=self.fractions,
            families=tuple(self._families.values()),
            canary=hash_canary(self.salt, self.fractions),
        )

    def verify_manifest(self, saved: Union[SplitManifest, str]) -> None:
        """Raise SplitLeak unless this registry assigns exactly as the saved manifest."""
        _raise_if(
            manifest_differences(_as_manifest(saved), self.manifest()),
            "split assignment disagrees with the saved manifest",
        )

    def assert_disjoint(self) -> None:
        """Prove no recorded item was used by two splits or is stale under the current families."""
        problems = []
        for axis, by_split in self.used.items():
            for index, first in enumerate(SPLITS):
                for second in SPLITS[index + 1:]:
                    shared = sorted(by_split[first] & by_split[second])
                    if shared:
                        problems.append(f"{axis} items in both {first} and {second}: {_short(shared)}")
            for split in SPLITS:
                for item in sorted(by_split[split]):
                    try:
                        now = self.split_of(axis, item)
                    except KeyError:
                        problems.append(f"stale {axis} record {item!r}: used in {split} but no longer a family member")
                        continue
                    if now != split:
                        problems.append(f"stale {axis} record {item!r}: used in {split} but now assigned to {now}")
        _raise_if(problems, "split records are not disjoint")

    def summary(self) -> dict[str, dict[str, int]]:
        return {
            axis: {split: len(by_split[split]) for split in SPLITS}
            for axis, by_split in self.used.items()
        }


class SplitView:
    """One split's window onto a registry: the sanctioned way to draw items.

    Everything drawn or used is recorded in the registry and collected as
    provenance, so create one view per generated example and attach
    `view.split` and `view.provenance()` to it.
    """

    def __init__(self, registry: SplitRegistry, split: str) -> None:
        self.registry = registry
        self.split = _check_split(split)
        self._used: dict[str, list[str]] = {}

    def available(self, axis: str, candidates: Iterable[str]) -> list[str]:
        """Candidates assigned to this split, deduplicated and sorted for reproducible draws."""
        if isinstance(candidates, (str, bytes)):
            raise ValueError("candidates must be an iterable of item names, not one string")
        return [item for item in sorted(set(candidates)) if self.registry.split_of(axis, item) == self.split]

    def draw(self, axis: str, candidates: Iterable[str], rng: random.Random, k: int = 1) -> list[str]:
        """Draw `k` distinct items of this split from `candidates` and record them."""
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError(f"k must be a positive integer, got {k!r}")
        pool = self.available(axis, candidates)
        if len(pool) < k:
            raise ValueError(f"only {len(pool)} {axis} candidates belong to {self.split}; {k} requested")
        chosen = rng.sample(pool, k)
        for item in chosen:
            self.use(axis, item)
        return chosen

    def use(self, axis: str, item: str) -> str:
        """Record one item this example uses; SplitLeak if it belongs to another split."""
        self.registry.record(axis, item, self.split)
        used = self._used.setdefault(axis, [])
        if item not in used:
            used.append(item)
        return item

    def provenance(self) -> dict[str, tuple[str, ...]]:
        return {axis: tuple(items) for axis, items in self._used.items()}


def _field(example: Any, name: str) -> Any:
    if isinstance(example, Mapping):
        return example.get(name)
    return getattr(example, name, None)


def _label(example: Any, index: int) -> str:
    for name in ("item_id", "id", "episode_id"):
        value = _field(example, name)
        if value not in (None, ""):
            return f"#{index} ({value})"
    return f"#{index}"


def _provenance_of(example: Any) -> Optional[dict[str, tuple[str, ...]]]:
    raw = _field(example, "provenance")
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise TypeError(f"provenance must map axis -> items, got {type(raw).__name__}")
    provenance = {
        axis: (items,) if isinstance(items, str) else tuple(items)
        for axis, items in raw.items()
    }
    # Every generated example uses some item, so an empty record (e.g. a dataclass
    # default left by a generator that skipped the view) counts as none attached.
    if not any(provenance.values()):
        return None
    return provenance


def assert_consumable(example: Any, expected_split: str, *, registry: Optional[SplitRegistry] = None) -> None:
    """Call where a training or evaluation loop consumes an example.

    Raises SplitLeak if the example is unlabelled or labelled with another
    split; with `registry`, also if its provenance is missing or names any item
    assigned elsewhere.
    """
    _check_split(expected_split)
    split = _field(example, "split")
    if split is None:
        raise SplitLeak(f"an unlabelled example reached a {expected_split} loop")
    if split != expected_split:
        raise SplitLeak(f"a {split} example reached a {expected_split} loop")
    if registry is None:
        return
    provenance = _provenance_of(example)
    if provenance is None:
        raise SplitLeak(f"an example without provenance reached a {expected_split} loop")
    problems = []
    for axis, items in provenance.items():
        for item in items:
            try:
                assigned = registry.split_of(axis, item)
            except (KeyError, ValueError) as error:
                problems.append(f"provenance {axis} {item!r} is unknown to the registry ({error})")
                continue
            if assigned != expected_split:
                problems.append(f"provenance {axis} {item!r} belongs to {assigned}")
    _raise_if(problems, f"example is not consumable by a {expected_split} loop")


def consumable(
    examples: Iterable[Any], expected_split: str, *, registry: Optional[SplitRegistry] = None
) -> Iterator[Any]:
    """Yield `examples`, checking each with `assert_consumable` as it is consumed."""
    for example in examples:
        assert_consumable(example, expected_split, registry=registry)
        yield example


_WORD = re.compile(r"[^\W_]+")
_SENTENCE_BREAK = re.compile(r"[\n.!?;]+")
_FIELD = r"\S+(?: \S+){0,5}"  # a template field: one to six words


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(_WORD.findall(text.casefold()))


class _Surface:
    """A surface form (str.format pattern) matched against tokenised sentences."""

    def __init__(self, pattern: str) -> None:
        parts = []
        literal_words = 0
        for literal, field, _spec, _conversion in string.Formatter().parse(pattern):
            words = _tokens(literal)
            literal_words += len(words)
            parts.extend(re.escape(word) for word in words)
            if field is not None:
                parts.append(_FIELD)
        if literal_words == 0:
            raise ValueError(f"surface form {pattern!r} has no literal words, so text cannot reveal it")
        body = " ".join(parts)
        self.pattern = pattern
        self.literal_words = literal_words
        self._search = re.compile(rf"(?<!\S){body}(?!\S)")
        self._full = re.compile(body)

    def found_in(self, sentence: str) -> bool:
        return self._search.search(sentence) is not None

    def is_whole(self, sentence: str) -> bool:
        return self._full.fullmatch(sentence) is not None


def _vocab_entries(
    registry: SplitRegistry, vocab: Mapping[str, Iterable[str]]
) -> tuple[dict[tuple[str, ...], list[tuple[str, str, str]]], dict[str, list[tuple[str, str, _Surface]]]]:
    """Index vocab into literal token sequences and per-axis surface patterns."""
    literal: dict[tuple[str, ...], list[tuple[str, str, str]]] = defaultdict(list)
    patterned: dict[str, list[tuple[str, str, _Surface]]] = defaultdict(list)
    for axis, entries in vocab.items():
        _check_axis(axis)
        if isinstance(entries, (str, bytes)):
            raise ValueError(f"vocab for {axis} must be an iterable of items, not one string")
        forms = entries if isinstance(entries, Mapping) else None
        for item in (entries.keys() if forms is not None else entries):
            try:
                split = registry.split_of(axis, _check_item(item))
            except KeyError:
                raise ValueError(f"vocab {axis} item {item!r} is not in the registry's fixed family") from None
            if forms is None:
                words = _tokens(item)
                if not words:
                    raise ValueError(f"vocab {axis} item {item!r} has no words to search for")
                literal[words].append((axis, item, split))
                continue
            surfaces = forms[item]
            for surface in (surfaces,) if isinstance(surfaces, str) else tuple(surfaces):
                patterned[axis].append((item, split, _Surface(surface)))
    return literal, patterned


def audit_examples(
    examples: Iterable[Any],
    registry: SplitRegistry,
    *,
    text_of: Callable[[Any], str],
    vocab: Mapping[str, Iterable[str]],
    require_recorded: bool = True,
) -> dict[str, Any]:
    """Independently check generated examples for cross-split items; SplitLeak on any.

    Each example needs `split` and `provenance` (attributes or mapping keys).
    Provenance (missing or empty counts as none) items must belong to the
    example's split and, with `require_recorded`, have been recorded by the
    registry. Independently of both, the example's text is scanned for every
    vocab item of another split, and for own-split literal items (names) that
    the provenance does not list.
    A vocab value that is a mapping gives each item's surface forms as
    str.format patterns (e.g. template id -> template text), matched per
    sentence with each field standing for one to six words; a foreign pattern
    is ignored in a sentence that an own-split pattern of the same axis matches
    wholly and better (the foreign one matches only part of it, or has fewer
    literal words). Equally good matches from two splits are flagged: the
    families are then indistinguishable in text. Otherwise each item is its
    own surface form, matched as a whole-word, case-insensitive phrase.
    Returns counts when clean.
    """
    literal, patterned = _vocab_entries(registry, vocab)
    longest = max((len(words) for words in literal), default=0)
    problems: list[str] = []
    by_split = {split: 0 for split in SPLITS}
    total = 0
    for index, example in enumerate(examples):
        total += 1
        label = _label(example, index)
        split = _field(example, "split")
        if split not in SPLITS:
            problems.append(f"example {label}: split label {split!r} is missing or unknown, so it cannot be audited")
            continue
        by_split[split] += 1
        where = f"example {label} ({split})"

        try:
            provenance = _provenance_of(example)
        except TypeError as error:
            problems.append(f"{where}: {error}")
            provenance = {}
        attached = provenance is not None
        if not attached:
            problems.append(f"{where}: no provenance attached")
            provenance = {}
        for axis, items in provenance.items():
            if axis not in AXES:
                problems.append(f"{where}: provenance names unknown axis {axis!r}")
                continue
            for item in items:
                try:
                    assigned = registry.split_of(axis, item)
                except (KeyError, ValueError):
                    problems.append(f"{where}: provenance {axis} {item!r} is unknown to the registry")
                    continue
                if assigned != split:
                    problems.append(f"{where}: provenance {axis} {item!r} belongs to {assigned}")
                elif require_recorded and item not in registry.used[axis][split]:
                    problems.append(f"{where}: provenance {axis} {item!r} was never recorded in the registry")

        sentences = [words for words in (_tokens(chunk) for chunk in _SENTENCE_BREAK.split(text_of(example))) if words]
        found: set[tuple[str, str]] = set()
        for words in sentences:
            for size in range(1, min(longest, len(words)) + 1):
                for start in range(len(words) - size + 1):
                    for axis, item, item_split in literal.get(words[start:start + size], ()):
                        if (axis, item) in found:
                            continue
                        if item_split != split:
                            found.add((axis, item))
                            problems.append(f"{where}: text mentions {item_split} {axis} {item!r}")
                        elif attached and item not in provenance.get(axis, ()):
                            # An own-split item drawn without the view: harmless this time, but
                            # the same bypass can draw from any split.
                            found.add((axis, item))
                            problems.append(f"{where}: text mentions {axis} {item!r}, which its provenance does not list")
        for axis, forms in patterned.items():
            for words in sentences:
                sentence = " ".join(words)
                own_whole = [
                    surface.literal_words
                    for _item, item_split, surface in forms
                    if item_split == split and surface.is_whole(sentence)
                ]
                for item, item_split, surface in forms:
                    if item_split == split or (axis, item) in found or not surface.found_in(sentence):
                        continue
                    # An own-split form that is the whole sentence and more specific explains it.
                    whole = surface.is_whole(sentence)
                    if own_whole and (not whole or max(own_whole) > surface.literal_words):
                        continue
                    found.add((axis, item))
                    problems.append(f"{where}: text matches {item_split} {axis} {item!r} in {sentence!r}")
    _raise_if(problems, "generated examples cross splits")
    return {
        "examples": total,
        "by_split": by_split,
        "vocab_items": len({(axis, item) for entries in literal.values() for axis, item, _ in entries})
        + len({(axis, item) for axis, forms in patterned.items() for item, _, _ in forms}),
    }


__all__ = [
    "AXES",
    "DEFAULT_FRACTIONS",
    "DEFAULT_SALT",
    "SCHEME",
    "SPLITS",
    "FamilyManifest",
    "SplitLeak",
    "SplitManifest",
    "SplitRegistry",
    "SplitView",
    "allocate",
    "assert_consumable",
    "assign",
    "assign_ranked",
    "audit_examples",
    "consumable",
    "hash_canary",
    "items_in",
    "manifest_differences",
    "validate_fractions",
]
