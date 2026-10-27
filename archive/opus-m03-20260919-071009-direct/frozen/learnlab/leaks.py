"""Deliberately dumb models that reveal answers leaking through surface patterns.

If a guesser that ignores meaning (a majority vote, a word counter, a learned
"the answer is the first place mentioned" rule, a model of the answer line's
wording) beats its own honest null on a test set, that test set can be passed
without learning what it claims to measure. Each detector is compared with the
null that matches what it can see, by an exact one-sided binomial test plus an
effect-size margin, and small test sets are reported as "insufficient".

Candidates are drawn from each example's own context, so held-out answers
(new names) are reachable; text is case-folded on both sides and answers may
span several tokens.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import hashlib
import math
import random
import re
from typing import Callable, Iterable, Mapping, Optional, Sequence, Union

from .metrics import binomial_greater
from .policy import ALPHA, LEAK_MARGIN, LEAK_MIN_ITEMS

# Letters and digits (any script), with inner apostrophes kept: "Zoë's" -> "zoë's".
_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

PRESENCE_WARNING = 0.5  # presence chance above this means guessing among candidates is easy


def words(text: str) -> list[str]:
    """Case-folded word tokens with punctuation stripped."""
    return _WORD.findall(text.casefold())


def normalize(text: str) -> str:
    """Case-fold, strip punctuation and collapse whitespace: 'The Old Mill!' -> 'the old mill'."""
    return " ".join(words(text))


@dataclass(frozen=True)
class QAExample:
    context: str
    question: str
    answer: str
    meta: Mapping[str, str] = field(default_factory=dict, hash=False)
    # Items of one group (one visit) share their context, so a detector must not learn one of them before
    # predicting the others: `leak_report` learns a group's test items only after predicting all of them.
    group: str = ""

    @property
    def target(self) -> str:
        return normalize(self.answer)


def _units(context: str) -> list[str]:
    """Context lines, further split into sentences; the unit the target-line detector reads."""
    units = []
    for line in context.split("\n"):
        units.extend(part for part in _SENTENCE_END.split(line.strip()) if part.strip())
    return units


def _vocabulary(answers: Iterable[str]) -> frozenset[tuple[str, ...]]:
    return frozenset(key for key in (tuple(words(answer)) for answer in answers) if key)


def _match(tokens: Sequence[str], vocab: frozenset[tuple[str, ...]]) -> list[tuple[int, int]]:
    """Greedy longest, non-overlapping (start, end) spans of `tokens` found in `vocab`."""
    longest = max((len(key) for key in vocab), default=0)
    spans, index = [], 0
    while index < len(tokens):
        for size in range(min(longest, len(tokens) - index), 0, -1):
            if tuple(tokens[index:index + size]) in vocab:
                spans.append((index, index + size))
                index += size
                break
        else:
            index += 1
    return spans


def _names(units: Sequence[str], question: str) -> frozenset[tuple[str, ...]]:
    """Name-like n-grams of the context: runs of capitalised tokens ("Old Mill").

    A sentence-initial capital is ambiguous ("The", "Bafe"), so that token
    counts only if the same word is capitalised mid-sentence somewhere in the
    example (context or question). Spurious candidates would lower the
    presence null and so cause false leak flags; a missed name only costs power.
    """
    context = [_WORD.findall(unit) for unit in units]
    asked = [_WORD.findall(part) for part in _SENTENCE_END.split(question.strip()) if part]
    midsentence = {token.casefold() for tokens in context + asked for token in tokens[1:] if token[:1].isupper()}
    found: set[tuple[str, ...]] = set()
    for tokens in context:
        run: list[str] = []
        for index, token in enumerate(tokens):
            if token[:1].isupper() and (index > 0 or token.casefold() in midsentence):
                run.append(token.casefold())
                continue
            if run:
                found.add(tuple(run))
            run = []
        if run:
            found.add(tuple(run))
    return frozenset(found)


@dataclass(frozen=True)
class _Mention:
    candidate: str
    unit: int


@dataclass(frozen=True)
class _View:
    """An example prepared once for every detector."""

    answer: str
    units: tuple[tuple[str, ...], ...]
    question: tuple[str, ...]
    mentions: tuple[_Mention, ...]
    spans: tuple[tuple[tuple[int, int], ...], ...]  # candidate spans per unit
    asked: tuple[str, ...]                          # candidates named in the question
    meta: tuple[tuple[str, str], ...]
    key: str

    @property
    def candidates(self) -> list[str]:
        return list(dict.fromkeys(mention.candidate for mention in self.mentions))

    @property
    def answer_present(self) -> bool:
        return any(mention.candidate == self.answer for mention in self.mentions)


def _view(
    example: QAExample,
    vocab: Optional[frozenset[tuple[str, ...]]],
    *,
    key: Optional[str] = None,
) -> _View:
    raw_units = _units(example.context)
    units = tuple(tuple(words(unit)) for unit in raw_units)
    if vocab is None:
        # No answer vocabulary: name-like n-grams plus the example's own (known) answer.
        vocab = _names(raw_units, example.question) | _vocabulary([example.answer])
    mentions, spans = [], []
    for index, tokens in enumerate(units):
        found = tuple(_match(tokens, vocab))
        spans.append(found)
        mentions.extend(_Mention(" ".join(tokens[start:end]), index) for start, end in found)
    question = tuple(words(example.question))
    if key is None:
        key = hashlib.sha256(f"{example.context}\x00{example.question}".encode()).hexdigest()
    return _View(
        answer=example.target,
        units=units,
        question=question,
        mentions=tuple(mentions),
        spans=tuple(spans),
        asked=tuple(dict.fromkeys(" ".join(question[a:b]) for a, b in _match(question, vocab))),
        meta=tuple(sorted((str(k), str(v)) for k, v in example.meta.items())),
        key=key,
    )


def candidates(example: QAExample, *, answer_vocab: Optional[Iterable[str]] = None) -> list[str]:
    """Distinct candidate answers found in the example's own context, in first-mention order.

    With `answer_vocab`, every normalized n-gram of the context that is a
    vocabulary entry (longest match first, non-overlapping, so "old mill"
    is one candidate, not also "mill"). Without it, name-like runs of
    capitalised tokens plus the example's own answer where it occurs.
    """
    vocab = _vocabulary(answer_vocab) if answer_vocab is not None else None
    return _view(example, vocab).candidates


def _presence(view: _View) -> float:
    """Chance of hitting the answer by guessing uniformly among the view's candidates."""
    found = view.candidates
    return 1.0 / len(found) if view.answer in found else 0.0


def presence_chance(
    examples: Sequence[QAExample],
    answer_vocab: Optional[Iterable[str]] = None,
) -> float:
    """Expected accuracy of guessing uniformly among the candidates present in each context.

    When facts must be read from the context the answer is usually present, so
    this, not 1/K, is the honest null for detectors that choose among context
    candidates. The vocabulary defaults to the examples' own answers.
    """
    if not examples:
        return 0.0
    vocab = _vocabulary(answer_vocab if answer_vocab is not None else (e.answer for e in examples))
    return sum(_presence(_view(example, vocab)) for example in examples) / len(examples)


def _contains(haystack: Sequence[str], needle: Sequence[str]) -> bool:
    size = len(needle)
    return size > 0 and any(
        tuple(haystack[i:i + size]) == tuple(needle) for i in range(len(haystack) - size + 1)
    )


def answer_in_input_rate(examples: Sequence[QAExample]) -> float:
    """Fraction of examples whose question contains the normalized answer as a token sequence."""
    if not examples:
        raise ValueError("no examples")
    return sum(_contains(words(e.question), words(e.answer)) for e in examples) / len(examples)


def _pick(options: Iterable[str], view: _View, salt: str) -> str:
    """Deterministic pseudo-random choice among tied options, independent of the answer."""
    ordered = sorted(set(options))
    if not ordered:
        return ""
    digest = hashlib.sha256(f"{salt}\x00{view.key}".encode()).digest()
    return ordered[int.from_bytes(digest[:8], "big") % len(ordered)]


def _best(scores: Mapping[str, float], view: _View, salt: str) -> str:
    if not scores:
        return ""
    top = max(scores.values())
    return _pick([option for option, score in scores.items() if score >= top - 1e-9], view, salt)


class _NaiveBayes:
    """Multinomial naive Bayes over string features, trained one example at a time.

    Features never seen in training are ignored.
    """

    def __init__(self, smoothing: float = 1.0) -> None:
        self.smoothing = smoothing
        self.examples = 0
        self.label_counts: Counter[str] = Counter()
        self.feature_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self.totals: Counter[str] = Counter()
        self.vocabulary: set[str] = set()

    def add(self, label: str, features: Iterable[str]) -> None:
        features = list(features)
        self.examples += 1
        self.label_counts[label] += 1
        self.feature_counts[label].update(features)
        self.totals[label] += len(features)
        self.vocabulary.update(features)

    def log_likelihoods(self, features: Iterable[str]) -> dict[str, float]:
        known = Counter(feature for feature in features if feature in self.vocabulary)
        size = len(self.vocabulary) + 1
        scores = {}
        for label, count in self.label_counts.items():
            counts = self.feature_counts[label]
            denominator = math.log(self.totals[label] + self.smoothing * size)
            score = math.log(count / self.examples)
            for feature, times in known.items():
                score += times * (math.log(counts[feature] + self.smoothing) - denominator)
            scores[label] = score
        return scores


class Detector:
    """A dumb answerer that learns one example at a time.

    `null` names its honest chance level: 'answers' (1/K over the distinct
    test answers), 'presence' (uniform among the item's context candidates)
    or 'answers_or_presence' (per item, the larger of the two).
    """

    name = ""
    null = "answers"

    def __init__(self) -> None:
        self.vocab: frozenset[tuple[str, ...]] = frozenset()
        self._start()

    def fit(self, train: Sequence[QAExample], *, answer_vocab: Optional[Iterable[str]] = None) -> "Detector":
        """Train on `train`; candidates come from `answer_vocab` (default: the training answers)."""
        answers = answer_vocab if answer_vocab is not None else (e.answer for e in train)
        self.vocab = _vocabulary(answers)
        self._start()
        for example in train:
            self._learn(_view(example, self.vocab))
        return self

    def predict(self, example: QAExample) -> str:
        return self._predict(_view(example, self.vocab))

    def _start(self) -> None:
        """Reset to the untrained state."""

    def _learn(self, view: _View) -> None:
        raise NotImplementedError

    def _predict(self, view: _View) -> str:
        raise NotImplementedError


class MajorityDetector(Detector):
    """Always answers the most common answer seen so far."""

    name = "majority"

    def _start(self) -> None:
        self.counts: Counter[str] = Counter()

    def _learn(self, view: _View) -> None:
        self.counts[view.answer] += 1

    def _predict(self, view: _View) -> str:
        return _best({answer: float(count) for answer, count in self.counts.items()}, view, self.name)


class _LabelDetector(Detector):
    """Naive Bayes over the answer labels seen so far, from the features of `_features`."""

    smoothing = 0.1

    def _features(self, view: _View) -> list[str]:
        raise NotImplementedError

    def _start(self) -> None:
        self.model = _NaiveBayes(self.smoothing)

    def _learn(self, view: _View) -> None:
        self.model.add(view.answer, self._features(view))

    def _predict(self, view: _View) -> str:
        return _best(self.model.log_likelihoods(self._features(view)), view, self.name)


class BagOfWordsDetector(_LabelDetector):
    """Word counts of context and question together; ignores all order."""

    name = "bag_of_words"
    null = "answers_or_presence"  # context words let it pick among the labels present

    def _features(self, view: _View) -> list[str]:
        return [token for unit in view.units for token in unit] + list(view.question)


class QuestionOnlyDetector(_LabelDetector):
    """Reads only the question: catches answers or answer cues in the question.

    Besides naive Bayes over question words it learns one rule that also
    reaches held-out answers, "the answer is the candidate the question
    names", used once it beats label chance on the questions that name one.
    """

    name = "question_only"

    def _features(self, view: _View) -> list[str]:
        return list(view.question)

    def _start(self) -> None:
        super()._start()
        self.naming = 0
        self.named_hits = 0.0

    def _learn(self, view: _View) -> None:
        super()._learn(view)
        if view.asked:
            self.naming += 1
            self.named_hits += (view.answer in view.asked) / len(view.asked)

    def _predict(self, view: _View) -> str:
        labels = max(1, len(self.model.label_counts))
        if view.asked and self.naming and self.named_hits / self.naming > 1.0 / labels:
            return _pick(view.asked, view, self.name)
        return super()._predict(view)


class BigramDetector(_LabelDetector):
    """Order-aware: word pairs with sentence boundaries, question pairs kept apart."""

    name = "bigram"
    null = "answers_or_presence"  # reads the context too, so 1/K alone would be too low

    def _features(self, view: _View) -> list[str]:
        features = []
        for prefix, unit in [("c", unit) for unit in view.units] + [("q", view.question)]:
            padded = ["<s>", *unit, "</s>"]
            features.extend(f"{prefix}:{a} {b}" for a, b in zip(padded, padded[1:]))
        return features


class MetadataDetector(_LabelDetector):
    """Predicts the answer from metadata alone (template, style, name, ...).

    Besides naive Bayes over key=value features it learns, per field, the rule
    "the answer is this field's value", which also reaches held-out answers,
    used once that field beats label chance.
    """

    name = "metadata"

    def _features(self, view: _View) -> list[str]:
        return [f"{key}={value}" for key, value in view.meta]

    def _start(self) -> None:
        super()._start()
        self.copies: Counter[str] = Counter()

    def _learn(self, view: _View) -> None:
        super()._learn(view)
        for key, value in view.meta:
            self.copies[key] += normalize(value) == view.answer

    def _predict(self, view: _View) -> str:
        fields = dict(view.meta)
        if fields and self.model.examples:
            key = min(fields, key=lambda field: (-self.copies[field], field))
            labels = max(1, len(self.model.label_counts))
            if self.copies[key] / self.model.examples > 1.0 / labels:
                return normalize(fields[key])
        return super()._predict(view)


class PositionDetector(Detector):
    """Learns one ordinal rule: 'the answer is the k-th candidate mentioned' (from the start or end)."""

    name = "position"
    null = "presence"

    @staticmethod
    def _slots(view: _View) -> dict[str, str]:
        size = len(view.mentions)
        slots: dict[str, str] = {}
        for index, mention in enumerate(view.mentions):
            slots.setdefault(f"first+{index}", mention.candidate)
            slots.setdefault(f"last-{size - 1 - index}", mention.candidate)
        return slots

    def _start(self) -> None:
        self.hits: Counter[str] = Counter()

    def _learn(self, view: _View) -> None:
        for slot, candidate in self._slots(view).items():
            self.hits[slot] += candidate == view.answer

    def _predict(self, view: _View) -> str:
        slots = self._slots(view)
        if self.hits:
            slot = min(self.hits, key=lambda name: (-self.hits[name], name))
            if slot in slots:
                return slots[slot]
        return _pick(view.candidates, view, self.name)


class MostMentionedDetector(Detector):
    """Answers with the candidate mentioned most often in the context."""

    name = "most_mentioned"
    null = "presence"

    def _learn(self, view: _View) -> None:
        pass

    def _predict(self, view: _View) -> str:
        counts = Counter(mention.candidate for mention in view.mentions)
        return _best({c: float(n) for c, n in counts.items()}, view, self.name)


class LastMentionDetector(Detector):
    """Answers with the last candidate mentioned ("the last place mentioned")."""

    name = "last_mention"
    null = "presence"

    def _learn(self, view: _View) -> None:
        pass

    def _predict(self, view: _View) -> str:
        return view.mentions[-1].candidate if view.mentions else ""


class TargetLineDetector(Detector):
    """Naive Bayes on the wording of each candidate's line: is this the answer line?

    Candidate words are removed from the line, so only surface cues around
    the answer (a speaker tag, a template) can help.
    """

    name = "target_line"
    null = "presence"

    @staticmethod
    def _lines(view: _View) -> list[tuple[set[str], list[str]]]:
        """(candidates in the unit, the unit's other words) for each unit with candidates."""
        lines = []
        for tokens, spans in zip(view.units, view.spans):
            if not spans:
                continue
            inside = {i for start, end in spans for i in range(start, end)}
            found = {" ".join(tokens[start:end]) for start, end in spans}
            lines.append((found, [t for i, t in enumerate(tokens) if i not in inside]))
        return lines

    def _start(self) -> None:
        self.model = _NaiveBayes()

    def _learn(self, view: _View) -> None:
        for found, rest in self._lines(view):
            self.model.add("answer" if view.answer in found else "other", rest)

    def _predict(self, view: _View) -> str:
        if len(self.model.label_counts) < 2:
            return _pick(view.candidates, view, self.name)
        scores: dict[str, float] = {}
        for found, rest in self._lines(view):
            likelihood = self.model.log_likelihoods(rest)
            odds = likelihood["answer"] - likelihood["other"]
            for candidate in found:
                scores[candidate] = max(scores.get(candidate, -math.inf), odds)
        return _best(scores, view, self.name)


DETECTORS: tuple[type[Detector], ...] = (
    MajorityDetector,
    BagOfWordsDetector,
    QuestionOnlyDetector,
    PositionDetector,
    MostMentionedDetector,
    LastMentionDetector,
    BigramDetector,
    TargetLineDetector,
    MetadataDetector,
)


def accuracy(predict: Callable[[QAExample], str], examples: Sequence[QAExample]) -> float:
    """Fraction of examples answered correctly, comparing normalized strings."""
    if not examples:
        raise ValueError("no examples")
    return sum(normalize(predict(e)) == e.target for e in examples) / len(examples)


@dataclass(frozen=True)
class DetectorResult:
    name: str
    hits: int
    n: int
    null: float
    null_kind: str      # 'answers' (1/K), 'presence' or 'answers_or_presence'
    p_value: float      # exact one-sided binomial P(X >= hits | n, null)
    p_adjusted: float   # Holm-adjusted over the report's applicable detectors
    leaking: bool       # p_adjusted < alpha and accuracy > null + margin
    applicable: bool = True

    @property
    def accuracy(self) -> float:
        return self.hits / self.n if self.n else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "accuracy": self.accuracy,
            "hits": self.hits,
            "n": self.n,
            "null": self.null,
            "null_kind": self.null_kind,
            "p_value": self.p_value,
            "p_adjusted": self.p_adjusted,
            "leaking": self.leaking,
            "applicable": self.applicable,
        }


@dataclass(frozen=True)
class LeakReport:
    n: int
    train_n: int
    chance: float                   # 1/K over the K distinct test answers
    presence_chance: float
    detectors: dict[str, DetectorResult]
    alpha: float
    margin: float
    min_items: int
    answer_in_input_rate: float
    warnings: tuple[str, ...]

    @property
    def leaking_detectors(self) -> list[str]:
        return sorted(name for name, result in self.detectors.items() if result.leaking)

    @property
    def status(self) -> str:
        """'insufficient' below min_items (never 'clean'), else 'leaking' or 'clean'."""
        if self.n < self.min_items:
            return "insufficient"
        return "leaking" if self.leaking_detectors else "clean"

    @property
    def leaking(self) -> bool:
        return self.status == "leaking"

    @property
    def accuracies(self) -> dict[str, float]:
        return {name: result.accuracy for name, result in self.detectors.items()}

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "n": self.n,
            "train_n": self.train_n,
            "chance": self.chance,
            "presence_chance": self.presence_chance,
            "alpha": self.alpha,
            "margin": self.margin,
            "min_items": self.min_items,
            "answer_in_input_rate": self.answer_in_input_rate,
            "leaking_detectors": self.leaking_detectors,
            "detectors": {name: result.as_dict() for name, result in self.detectors.items()},
            "warnings": list(self.warnings),
        }


def _holm(p_values: Mapping[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values: familywise error <= alpha across the detectors."""
    ordered = sorted(p_values, key=lambda name: p_values[name])
    adjusted, running = {}, 0.0
    for rank, name in enumerate(ordered):
        running = max(running, min(1.0, (len(ordered) - rank) * p_values[name]))
        adjusted[name] = running
    return adjusted


def _check_answers(examples: Sequence[QAExample], label: str) -> None:
    empty = [i for i, example in enumerate(examples) if not example.target]
    if empty:
        raise ValueError(f"{label} examples {empty[:5]} have answers that normalize to nothing")


def leak_report(
    train: Sequence[QAExample],
    test: Sequence[QAExample],
    *,
    alpha: float = ALPHA,
    margin: float = LEAK_MARGIN,
    min_items: int = LEAK_MIN_ITEMS,
    answer_vocab: Optional[Iterable[str]] = None,
) -> LeakReport:
    """Run every detector on `test` and test each against its own null.

    Detectors are scored prequentially: each test item is predicted by a
    detector trained on `train` plus the test items before it, then learned.
    Items that share a `group` (one visit: overlapping context, related
    answers) are learned only after the group's last item is predicted, so no
    prediction is helped by the labels of its own group.
    A shortcut present only in the test generator (a held-out template that
    always puts the answer first) is therefore learned too, while each
    prediction stays independent of its own label, so under a clean null the
    hit count is binomial (or a less dispersed Poisson-binomial when the null
    varies per item, for which the binomial tail at the mean null is
    conservative). A detector is leaking when its exact one-sided p-value,
    Holm-adjusted over the detectors so that a clean report is flagged with
    probability <= alpha rather than up to 9 * alpha, is below `alpha` and
    its accuracy exceeds its null by more than `margin`. With fewer than
    `min_items` test items the status is "insufficient", never "clean".

    `answer_vocab` (default: every train and test answer) defines the context
    candidates; give only strings of the answer's own type (all names for
    "who" questions), or candidate-choosing detectors learn the type pattern.
    The default omits distractors that are never an answer (a held-out name
    mentioned only as a distractor), which raises the presence null; the
    detectors choose among the same reduced candidate set, so the test stays
    valid and only loses power. Pass the full type vocabulary to avoid that.

    The statistical detectors reach an answer-in-question leak on a fraction
    of items only with limited power (about 95% at 10% of 300 items, 10% at
    5%); `answer_in_input_rate` is the exact check and is always reported.
    """
    if not test:
        raise ValueError("leak_report needs test examples")
    if not (0.0 < alpha < 1.0 and math.isfinite(margin) and 0.0 <= margin < 1.0) or min_items < 1:
        raise ValueError("need 0 < alpha < 1, 0 <= margin < 1 and min_items >= 1")
    _check_answers(train, "train")
    _check_answers(test, "test")
    answers = answer_vocab if answer_vocab is not None else [e.answer for e in (*train, *test)]
    vocab = _vocabulary(answers)
    train_views = [_view(example, vocab) for example in train]
    # Ties are broken by item index, so duplicated items do not share tie-breaks.
    test_views = [_view(example, vocab, key=f"test:{i}") for i, example in enumerate(test)]
    n = len(test_views)
    distinct = len({view.answer for view in test_views})
    chance = 1.0 / distinct
    presence = sum(_presence(view) for view in test_views) / n
    either = sum(max(chance, _presence(view)) for view in test_views) / n
    nulls = {"answers": chance, "presence": presence, "answers_or_presence": either}
    has_meta = any(view.meta for view in (*train_views, *test_views))

    detectors = [kind() for kind in DETECTORS if kind is not MetadataDetector or has_meta]
    for detector in detectors:
        detector.vocab = vocab
        for view in train_views:
            detector._learn(view)
    hits: Counter[str] = Counter()
    last = {example.group: index for index, example in enumerate(test) if example.group}
    pending: dict[str, list[_View]] = defaultdict(list)  # a group's predicted items, learned after its last one
    for index, (view, example) in enumerate(zip(test_views, test)):
        for detector in detectors:
            hits[detector.name] += detector._predict(view) == view.answer
        pending[example.group].append(view)
        if not example.group or last[example.group] == index:
            for done in pending.pop(example.group):
                for detector in detectors:
                    detector._learn(done)

    p_values = {d.name: binomial_greater(hits[d.name], n, nulls[d.null]) for d in detectors}
    adjusted = _holm(p_values)
    results: dict[str, DetectorResult] = {}
    for kind in DETECTORS:
        applicable = kind.name in p_values
        null = nulls[kind.null]
        results[kind.name] = DetectorResult(
            name=kind.name,
            hits=hits[kind.name],
            n=n,
            null=null,
            null_kind=kind.null,
            p_value=p_values.get(kind.name, 1.0),
            p_adjusted=adjusted.get(kind.name, 1.0),
            leaking=applicable and adjusted[kind.name] < alpha and hits[kind.name] / n > null + margin,
            applicable=applicable,
        )
    return LeakReport(
        n=n,
        train_n=len(train),
        chance=chance,
        presence_chance=presence,
        detectors=results,
        alpha=alpha,
        margin=margin,
        min_items=min_items,
        answer_in_input_rate=answer_in_input_rate(test),
        warnings=tuple(_warnings(train, test, train_views, test_views, results, presence, min_items)),
    )


def _warnings(
    train: Sequence[QAExample],
    test: Sequence[QAExample],
    train_views: Sequence[_View],
    test_views: Sequence[_View],
    results: Mapping[str, DetectorResult],
    presence: float,
    min_items: int,
) -> list[str]:
    """Benchmark-quality warnings: things that make a 'clean' verdict weak or the test easy."""
    n = len(test)
    warnings = []
    if n < min_items:
        warnings.append(f"only {n} test items (< {min_items}): status is insufficient, never clean")
        flagged = [name for name, result in results.items() if result.leaking]
        if flagged:
            warnings.append(f"despite the small test set, significant detectors: {', '.join(flagged)}")
    if len(train) < min_items:
        warnings.append(f"only {len(train)} training items (< {min_items}): learned detectors are weak")
    if presence > PRESENCE_WARNING:
        warnings.append(
            f"presence chance {presence:.2f} > {PRESENCE_WARNING}: answer trivially present; test is weak"
        )
    if len({view.answer for view in test_views}) == 1:
        warnings.append("every test answer is the same")
    in_question = answer_in_input_rate(test)
    if in_question > 0.0:
        warnings.append(f"answer appears in the question for {in_question:.1%} of test items")
    present = sum(view.answer_present for view in test_views) / n
    if present < 0.5:
        warnings.append(
            f"answer is a context candidate for only {present:.0%} of test items; "
            "candidate detectors have little to work with"
        )
    seen = {view.answer for view in train_views}
    unseen = sum(view.answer not in seen for view in test_views) / n
    if unseen > 0.0:
        warnings.append(
            f"{unseen:.0%} of test answers never occur in training; label detectors "
            "(majority, bag_of_words, question_only, bigram, metadata) reach them only after "
            "earlier test items"
        )
    keys = [(e.context, e.question, e.target) for e in test]
    repeated = n - len(set(keys))
    if repeated:
        warnings.append(f"{repeated} test items repeat earlier test items; p-values assume independent items")
    trained = {(e.context, e.question, e.target) for e in train}
    overlap = sum(key in trained for key in keys)
    if overlap:
        warnings.append(f"{overlap} test items also appear verbatim in training")
    if not results["metadata"].applicable:
        warnings.append("no example carries metadata: metadata detector skipped")
    return warnings


def shuffle_lines(text: str, rng: random.Random) -> str:
    lines = [line for line in text.split("\n") if line.strip()]
    rng.shuffle(lines)
    return "\n".join(lines)


def shuffled(examples: Sequence[QAExample], seed: int = 0) -> list[QAExample]:
    """Examples with context lines shuffled: the input for a real model's order-blind check."""
    rng = random.Random(seed)
    return [
        QAExample(shuffle_lines(e.context, rng), e.question, e.answer, dict(e.meta), e.group) for e in examples
    ]


Pair = tuple[QAExample, QAExample]
Chance = Union[float, Callable[[QAExample], float]]


def _both_right(pair: Pair, predict: Callable[[QAExample], str]) -> bool:
    return all(normalize(predict(example)) == example.target for example in pair)


def pair_accuracy(pairs: Sequence[Pair], predict: Callable[[QAExample], str]) -> float:
    """Fraction of counterfactual pairs with both members answered correctly."""
    if not pairs:
        raise ValueError("no pairs")
    return sum(_both_right(pair, predict) for pair in pairs) / len(pairs)


def pair_chance(pairs: Sequence[Pair], null: Chance) -> float:
    """Chance of getting both members right by independent guessing.

    `null` is a per-example chance: a constant, or a function of the example
    (e.g. `example_presence_chance`).
    """
    if not pairs:
        raise ValueError("no pairs")
    chance = null if callable(null) else (lambda _example: float(null))
    total = 0.0
    for a, b in pairs:
        ca, cb = chance(a), chance(b)
        if not (0.0 <= ca <= 1.0 and 0.0 <= cb <= 1.0):
            raise ValueError("chance must lie in [0, 1]")
        total += ca * cb
    return total / len(pairs)


def pair_pvalue(pairs: Sequence[Pair], predict: Callable[[QAExample], str], null: Chance) -> float:
    """Exact one-sided binomial p-value that pair accuracy exceeds `pair_chance`."""
    if not pairs:
        raise ValueError("no pairs")
    hits = sum(_both_right(pair, predict) for pair in pairs)
    return binomial_greater(hits, len(pairs), pair_chance(pairs, null))


def example_presence_chance(
    answer_vocab: Optional[Iterable[str]] = None,
) -> Callable[[QAExample], float]:
    """Per-example presence chance (1/|candidates| if the answer is among them), for `pair_chance`."""
    vocab = _vocabulary(answer_vocab) if answer_vocab is not None else None
    return lambda example: _presence(_view(example, vocab))


__all__ = [
    "BagOfWordsDetector",
    "BigramDetector",
    "DETECTORS",
    "Detector",
    "DetectorResult",
    "LastMentionDetector",
    "LeakReport",
    "MajorityDetector",
    "MetadataDetector",
    "MostMentionedDetector",
    "PositionDetector",
    "QAExample",
    "QuestionOnlyDetector",
    "TargetLineDetector",
    "accuracy",
    "answer_in_input_rate",
    "candidates",
    "example_presence_chance",
    "leak_report",
    "normalize",
    "pair_accuracy",
    "pair_chance",
    "pair_pvalue",
    "presence_chance",
    "shuffle_lines",
    "shuffled",
    "words",
]
