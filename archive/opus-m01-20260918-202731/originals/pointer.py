"""Names as pointers (design/06 §2): find made-up names in raw text, swap them for entity ids, and back.

Detection. A name is a capitalised word that is not a literal word of any pattern template and never occurs
lowercase in train text. Words are the tokenizer's letter runs (`learnlab.tokenizer.PATTERN`), so a name is always
one whole pre-tokenizer word. The tokenizer lowercases, so detection reads the raw text. The closed village
vocabulary (places, objects and their plurals, colours, materials ...) counts as seen lowercase: those words stay
ordinary tokens even where a sentence starts with one that the train text happens never to write lowercase
("Kites are toys.").

Pointerizing. The k-th distinct name of a visit (first mention) becomes entity `order[k]`: identity by default, a
random permutation of range(N_ENT) per visit in training. Entity e is token id `vocab_size + e`, and its exact
spelling goes to the visit's `NameTable`. The text between names is encoded exactly as the tokenizer encodes it, so
a syllable-split name (" ", "ke", "lo") becomes (" ", ENT): only the name's own pieces change. `detokenise` decodes
the tokenizer ids and writes each entity's exact spelling back, so `detokenise(pointerize(text))` equals the
tokenizer's normalized text with every name in its original spelling (`restored`).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import re
import string
from typing import Iterable, Iterator, Optional, Sequence, Union

from learnlab.tokenizer import Tokenizer

from .batch import N_ENT, NameTable

FORMAT = "premonition.names"
VERSION = 1
WORD = re.compile(r"[^\W\d_]+")   # a word as learnlab.tokenizer.PATTERN splits letters


class NameOverflow(ValueError):
    """A visit mentions more distinct names than there are entity ids."""


def lowercase_words(text: str) -> set[str]:
    """Every all-lowercase word of `text`."""
    return {word for word in WORD.findall(text) if word.islower()}


def template_words(templates: Iterable[str]) -> set[str]:
    """The literal words of pattern templates ("{person} went to {place}." -> went, to), casefolded."""
    out: set[str] = set()
    for text in templates:
        for literal, _name, _spec, _conv in string.Formatter().parse(text):
            out.update(word.casefold() for word in WORD.findall(literal))
    return out


def closed_vocabulary() -> frozenset[str]:
    """The village's closed shared vocabulary (`learnlab.village.vocab`), as lowercase words."""
    from learnlab.village import vocab
    groups = (vocab.PLACES, vocab.OBJECTS, tuple(vocab.PLURAL), tuple(vocab.PLURAL.values()), vocab.CATEGORIES,
              vocab.MATERIALS, vocab.COLOURS, vocab.CONTAINERS, vocab.TIMES, vocab.DIRECTIONS, vocab.NUMBER_WORDS,
              vocab.STYLES)
    return frozenset(word.lower() for group in groups for item in group for word in WORD.findall(str(item)))


class NameDetector:
    """The name rule, fitted once on train text and template words; saved and compared by digest."""

    def __init__(self, lowercase: Iterable[str], template: Iterable[str]) -> None:
        self.lowercase = frozenset(lowercase)
        self.template = frozenset(word.casefold() for word in template)
        self._blocked = frozenset(word.casefold() for word in self.lowercase) | self.template

    @classmethod
    def fit(cls, texts: Iterable[str], templates: Iterable[str] = (),
            vocabulary: Optional[Iterable[str]] = None) -> NameDetector:
        """From train texts, template texts and extra lowercase words (default: `closed_vocabulary()`)."""
        seen: set[str] = set(closed_vocabulary() if vocabulary is None else vocabulary)
        for text in texts:
            seen |= lowercase_words(text)
        return cls(seen, template_words(templates))

    def is_name(self, word: str) -> bool:
        return word[:1].isupper() and word.casefold() not in self._blocked

    def spans(self, text: str) -> list[tuple[int, int]]:
        """(start, end) of every name in `text`, in order."""
        return [match.span() for match in WORD.finditer(text) if self.is_name(match.group())]

    def names(self, text: str) -> list[str]:
        """The distinct names of `text` in order of first mention."""
        return list(dict.fromkeys(text[start:end] for start, end in self.spans(text)))

    def split(self, text: str) -> list[tuple[str, bool]]:
        """`text` as (segment, is_name) pieces; joined they give `text` back."""
        parts: list[tuple[str, bool]] = []
        last = 0
        for start, end in self.spans(text):
            if start > last:
                parts.append((text[last:start], False))
            parts.append((text[start:end], True))
            last = end
        if last < len(text):
            parts.append((text[last:], False))
        return parts

    def payload(self) -> dict:
        return {"format": FORMAT, "version": VERSION,
                "lowercase": sorted(self.lowercase), "template": sorted(self.template)}

    @property
    def digest(self) -> str:
        canonical = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def to_json(self) -> str:
        return json.dumps({**self.payload(), "sha256": self.digest}, ensure_ascii=True, indent=0)

    @classmethod
    def from_json(cls, text: str) -> NameDetector:
        try:
            data = json.loads(text)
            if data.get("format") != FORMAT or data.get("version") != VERSION:
                raise ValueError(f"not a {FORMAT} v{VERSION} file")
            detector = cls(data["lowercase"], data["template"])
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise ValueError(f"bad name detector file: {error}") from None
        if data.get("sha256") != detector.digest:
            raise ValueError("name detector digest mismatch")
        return detector

    def save(self, path: Union[str, Path]) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Union[str, Path]) -> NameDetector:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


# ----------------------------------------------------------------- pointerizing


def random_order(rng: random.Random) -> list[int]:
    """A per-visit entity numbering: the k-th name of the visit becomes entity order[k]."""
    return rng.sample(range(N_ENT), N_ENT)


class Binder:
    """One visit's name table under construction: each new spelling takes the next entity of `order`."""

    def __init__(self, order: Optional[Sequence[int]] = None) -> None:
        order = list(range(N_ENT)) if order is None else [int(e) for e in order]
        if sorted(order) != list(range(N_ENT)):
            raise ValueError(f"order must be a permutation of range({N_ENT})")
        self.order = order
        self.table = NameTable()
        self._entity: dict[str, int] = {}

    def bind(self, spelling: str) -> int:
        entity = self._entity.get(spelling)
        if entity is None:
            if len(self._entity) >= N_ENT:
                raise NameOverflow(f"more than {N_ENT} distinct names in one visit "
                                   f"({', '.join(self._entity)}, {spelling})")
            entity = self._entity[spelling] = self.order[len(self._entity)]
            self.table.spellings[entity] = spelling
        return entity

    def entity_of(self, spelling: str) -> Optional[int]:
        return self._entity.get(spelling)


_CACHE_LIMIT = 200_000


def pointerize(text: str, tokenizer: Tokenizer, detector: NameDetector, *, order: Optional[Sequence[int]] = None,
               binder: Optional[Binder] = None, cache: Optional[dict[str, list[int]]] = None
               ) -> tuple[list[int], NameTable]:
    """Token ids of `text` with each name as `vocab_size + entity`, and the name table.

    Pass a `binder` to continue a visit's numbering (its table is returned); otherwise a fresh one with `order`.
    `cache` (segment -> ids, owned by the caller and used with one tokenizer only) skips re-encoding repeats.
    """
    if binder is None:
        binder = Binder(order)
    elif order is not None:
        raise ValueError("give an order or a binder, not both")
    base = tokenizer.vocab_size
    ids: list[int] = []
    for segment, is_name in detector.split(text):
        if is_name:
            ids.append(base + binder.bind(segment))
        elif cache is None:
            ids.extend(tokenizer.encode(segment))
        else:
            found = cache.get(segment)
            if found is None:
                if len(cache) >= _CACHE_LIMIT:
                    cache.clear()
                found = cache[segment] = tokenizer.encode(segment)
            ids.extend(found)
    return ids, binder.table


def pointerize_lines(lines: Sequence[str], tokenizer: Tokenizer, detector: NameDetector, *,
                     order: Optional[Sequence[int]] = None, cache: Optional[dict[str, list[int]]] = None
                     ) -> tuple[list[list[int]], NameTable]:
    """A visit's lines, each encoded with its trailing newline (as `step1.encode_lines`), sharing one table."""
    binder = Binder(order)
    return [pointerize(line + "\n", tokenizer, detector, binder=binder, cache=cache)[0] for line in lines], binder.table


def detokenise(ids: Iterable[int], table: NameTable, tokenizer: Tokenizer) -> str:
    """Text of pointerized ids: tokenizer pieces decoded, each entity id replaced by its exact spelling."""
    base = tokenizer.vocab_size
    out: list[str] = []
    run: list[int] = []
    for index in ids:
        index = int(index)
        if index < base:
            run.append(index)
            continue
        if run:
            out.append(tokenizer.decode(run))
            run = []
        entity = index - base
        if entity >= N_ENT or entity not in table.spellings:
            raise ValueError(f"id {index} is entity {entity}, which the name table does not hold")
        out.append(table.spellings[entity])
    if run:
        out.append(tokenizer.decode(run))
    return "".join(out)


def restored(text: str, tokenizer: Tokenizer, detector: NameDetector) -> str:
    """What `detokenise(pointerize(text))` gives: the tokenizer's normalized text with names spelled exactly."""
    return "".join(part if is_name else tokenizer.normalize(part) for part, is_name in detector.split(text))


def answer_text(ids: Iterable[int], table: NameTable, tokenizer: Tokenizer) -> str:
    """The answer pointerized ids spell (as `step1.answer_text`): up to the first special token or newline,
    skipping -100 padding, names from the table, stripped."""
    specials = len(tokenizer.specials)
    kept: list[int] = []
    for index in ids:
        index = int(index)
        if index == -100:
            continue
        if index < specials:
            break
        kept.append(index)
        if index < tokenizer.vocab_size and "\n" in tokenizer.decode([index]):
            break
    return detokenise(kept, table, tokenizer).split("\n")[0].strip()


def renumber_table(table: NameTable, order: Sequence[int]) -> NameTable:
    """The table of a visit numbered by `order` from its identity-numbered table (entity k -> order[k])."""
    return NameTable({int(order[entity]): spelling for entity, spelling in table.spellings.items()})


def mentions(ids: Iterable[int], vocab_size: int) -> Iterator[int]:
    """The entity ids among pointerized ids, in order (repeats included)."""
    for index in ids:
        if int(index) >= vocab_size:
            yield int(index) - vocab_size


__all__ = [
    "Binder", "NameDetector", "NameOverflow", "WORD", "answer_text", "closed_vocabulary", "detokenise",
    "lowercase_words", "mentions", "pointerize", "pointerize_lines", "random_order", "renumber_table", "restored",
    "template_words",
]
