"""Leak-detector checks on the toy world: planted shortcuts are flagged, clean data is not.

Every planted flaw is the clean toy episode with one change (`toy.LEAKS`,
or a small rewrite of toy episodes for flaws the generator does not plant:
held-out-name "who" questions and a pure word-order cue), so each planted
check has the clean toy data, or a matched rewrite of it, as its control.
Toy episodes are fixed by (split, index), so a "seed" here is the index
offset a slice starts at; everything is deterministic.
"""
from __future__ import annotations

import random
import re
from typing import Any, Callable, Optional, Sequence

from learnlab import toy
from learnlab.checks import check
from learnlab.leaks import (
    BagOfWordsDetector,
    LastMentionDetector,
    LeakReport,
    MajorityDetector,
    QAExample,
    QuestionOnlyDetector,
    answer_in_input_rate,
    example_presence_chance,
    leak_report,
    pair_accuracy,
    pair_chance,
    pair_pvalue,
    words,
)
from learnlab.policy import ALPHA, LEAK_MARGIN, LEAK_MIN_ITEMS

AREA = "leaks"
N_TRAIN, N_TEST = 400, 300
SEEDS = (0, 10_000, 20_000)          # index offsets of the train and test slices
PAIRS = 300


def _examples(registry: Any, split: str, count: int, *, start: int = 0,
              leak: Optional[str] = None, rate: float = 1.0) -> list[QAExample]:
    return [e.example() for e in toy.episodes(registry, split, count, start=start, leak=leak, leak_rate=rate)]


def _pair(registry: Any, seed: int = 0, *, leak: Optional[str] = None,
          rate: float = 1.0) -> tuple[list[QAExample], list[QAExample]]:
    return (
        _examples(registry, "train", N_TRAIN, start=seed, leak=leak, rate=rate),
        _examples(registry, "test", N_TEST, start=seed, leak=leak, rate=rate),
    )


def _summary(report: LeakReport, *names: str) -> dict[str, Any]:
    """The evidence a reader needs: verdict, flagged detectors, and the named detectors vs their nulls."""
    shown = names or tuple(report.detectors)
    return {
        "status": report.status,
        "n": report.n,
        "leaking_detectors": report.leaking_detectors,
        "chance": round(report.chance, 4),
        "presence_chance": round(report.presence_chance, 4),
        "answer_in_input_rate": round(report.answer_in_input_rate, 4),
        "detectors": {
            name: {
                "accuracy": round(report.detectors[name].accuracy, 4),
                "null": round(report.detectors[name].null, 4),
                "p_adjusted": float(f"{report.detectors[name].p_adjusted:.3g}"),
                "leaking": report.detectors[name].leaking,
            }
            for name in shown
        },
    }


# Rewrites of toy episodes for flaws the toy generator does not plant.

_PLACE = re.compile(r"\b(" + "|".join(toy.PLACES) + r")\b")


def _capitalised(example: QAExample) -> QAExample:
    """Places written as proper names ("the Barn"), answer included: a case-folding control."""
    upper = lambda text: _PLACE.sub(lambda m: m.group(1).capitalize(), text)
    return QAExample(upper(example.context), upper(example.question), example.answer.capitalize(),
                     dict(example.meta))


def _who(episode: toy.Episode) -> QAExample:
    """'Who keeps the <obj> in the <place>?' about the answer line's fact; the answer is a name.

    Only the fact lines are kept (a rule line names people but no place), so
    the answer line's position is exactly the one the episode was drawn with.
    """
    fact = episode.facts[episode.answer_line]
    return QAExample(
        "\n".join(episode.lines[:toy.FACTS]),
        f"Who keeps the {fact.obj} in the {fact.place}?",
        fact.name,
        {"style": "who", "template": episode.templates[episode.answer_line]},
    )


def _word_order(seed: int, count: int, *, leak: bool) -> list[QAExample]:
    """Every context holds the same words; with `leak`, only their order says the answer.

    "<name> set the cup down before the key." -> left, "... the key down
    before the cup." -> right. The control draws the label independently of
    the order.
    """
    rng = random.Random(seed)
    names = toy.all_names()
    out = []
    for _ in range(count):
        cup_first = rng.random() < 0.5
        label = cup_first if leak else rng.random() < 0.5
        first, second = ("cup", "key") if cup_first else ("key", "cup")
        context = f"{rng.choice(names)} set the {first} down before the {second}."
        out.append(QAExample(context, "Which hand did it go to?", "left" if label else "right"))
    return out


def _clean_checks(registry: Any) -> list[dict[str, Any]]:
    results = []
    reports = {seed: leak_report(*_pair(registry, seed), answer_vocab=toy.PLACES) for seed in SEEDS}
    results.append(check(
        f"{AREA}: clean toy train/test is not flagged across {len(SEEDS)} seeds",
        all(r.status == "clean" for r in reports.values()) and all(r.n >= N_TEST for r in reports.values()),
        seeds={seed: _summary(r) for seed, r in reports.items()},
    ))
    rates = {seed: r.answer_in_input_rate for seed, r in reports.items()}
    results.append(check(
        f"{AREA}: answer_in_input_rate is 0 on clean toy data",
        all(rate == 0.0 for rate in rates.values()),
        rates=rates,
    ))

    capital = {}
    for seed in SEEDS:
        train, test = _pair(registry, seed)
        # Default vocabulary: the capitalised answers themselves, so matching must case-fold.
        capital[seed] = leak_report([_capitalised(e) for e in train], [_capitalised(e) for e in test])
    results.append(check(
        f"{AREA}: capitalised answers on clean data are not flagged",
        all(r.status == "clean" for r in capital.values())
        and all(abs(r.presence_chance - 1.0 / toy.FACTS) < 1e-9 for r in capital.values()),
        seeds={seed: _summary(r, "bag_of_words", "position", "last_mention") for seed, r in capital.items()},
        example_answer=_capitalised(_pair(registry)[1][0]).answer,
    ))

    small = {}
    train = _examples(registry, "train", N_TRAIN)
    for size in (20, 40, LEAK_MIN_ITEMS - 1):
        small[size] = leak_report(train, _examples(registry, "test", size, start=5_000), answer_vocab=toy.PLACES)
    results.append(check(
        f"{AREA}: a clean slice below {LEAK_MIN_ITEMS} items is 'insufficient', not 'leaking'",
        all(r.status == "insufficient" and not r.leaking and not r.leaking_detectors for r in small.values()),
        slices={size: {"status": r.status, "leaking_detectors": r.leaking_detectors,
                       "warning": r.warnings[0] if r.warnings else ""} for size, r in small.items()},
    ))
    return results


def _flags(report: LeakReport, detector: str) -> bool:
    return report.status == "leaking" and report.detectors[detector].leaking


def _planted_checks(registry: Any) -> list[dict[str, Any]]:
    results = []

    report = leak_report(*_pair(registry, leak="answer_in_question"), answer_vocab=toy.PLACES)
    results.append(check(
        f"{AREA}: planted answer_in_question is flagged (question_only) with answer_in_input_rate 1.0",
        _flags(report, "question_only") and report.answer_in_input_rate == 1.0,
        **_summary(report, "question_only", "bigram"),
    ))

    for leak, others in (("target_first", ("last_mention",)), ("target_second", ("last_mention",)),
                         ("target_last", ())):
        report = leak_report(*_pair(registry, leak=leak), answer_vocab=toy.PLACES)
        caught = _flags(report, "position") and not any(report.detectors[o].leaking for o in others)
        if leak == "target_last":
            caught = caught and _flags(report, "last_mention")
        results.append(check(
            f"{AREA}: planted {leak} is flagged (position{', last_mention' if leak == 'target_last' else ''})",
            caught,
            **_summary(report, "position", "last_mention"),
        ))

    # All-barn answers would leave one distinct answer (1/K = 1), so the prior is skewed on 30%.
    report = leak_report(*_pair(registry, leak="skew_barn", rate=0.3), answer_vocab=toy.PLACES)
    majority = report.detectors["majority"]
    results.append(check(
        f"{AREA}: planted skew_barn (30%) is flagged by majority against 1/K, not presence",
        _flags(report, "majority") and abs(majority.null - report.chance) < 1e-12
        and report.chance < report.presence_chance,
        **_summary(report, "majority"),
    ))

    report = leak_report(*_pair(registry, leak="object_place"), answer_vocab=toy.PLACES)
    results.append(check(
        f"{AREA}: planted object_place is flagged by the question-only detector",
        _flags(report, "question_only"),
        **_summary(report, "question_only", "position", "target_line"),
    ))

    report = leak_report(*_pair(registry, leak="teacher_cue"), answer_vocab=toy.PLACES)
    blind = ("position", "last_mention", "most_mentioned")
    results.append(check(
        f"{AREA}: planted teacher_cue is flagged by target_line (and not by order-free detectors)",
        _flags(report, "target_line") and not any(report.detectors[name].leaking for name in blind),
        **_summary(report, "target_line", *blind),
    ))

    planted = leak_report(_word_order(1, 200, leak=True), _word_order(2, 200, leak=True))
    control = leak_report(_word_order(1, 200, leak=False), _word_order(2, 200, leak=False))
    bag = planted.detectors["bag_of_words"].accuracy
    results.append(check(
        f"{AREA}: a word-order-only leak is flagged by bigram while bag_of_words stays at chance",
        _flags(planted, "bigram") and bag <= 0.5 + LEAK_MARGIN,
        planted=_summary(planted, "bigram", "bag_of_words"),
    ))
    results.append(check(
        f"{AREA}: word-order control (label independent of order) is not flagged",
        control.status == "clean",
        control=_summary(control, "bigram", "bag_of_words"),
    ))

    report = leak_report(*_pair(registry, leak="answer_in_question", rate=0.3), answer_vocab=toy.PLACES)
    results.append(check(
        f"{AREA}: planted answer_in_question at 30% is flagged (question_only), answer_in_input_rate near 0.3",
        _flags(report, "question_only") and 0.2 <= report.answer_in_input_rate <= 0.4,
        **_summary(report, "question_only", "bigram"),
    ))
    report = leak_report(*_pair(registry, leak="target_last", rate=0.6), answer_vocab=toy.PLACES)
    results.append(check(
        f"{AREA}: planted target_last at 60% is flagged (last_mention)",
        _flags(report, "last_mention"),
        **_summary(report, "last_mention", "position"),
    ))

    names = toy.all_names()

    def who(leak: Optional[str]) -> tuple[list[QAExample], list[QAExample]]:
        return tuple(  # type: ignore[return-value]
            [_who(e) for e in toy.episodes(registry, split, count, leak=leak)]
            for split, count in (("train", N_TRAIN), ("test", N_TEST))
        )

    train, test = who("target_last")
    report = leak_report(train, test, answer_vocab=names)
    seen = {words(e.answer)[0] for e in train}
    held_out = sum(words(e.answer)[0] not in seen for e in test) / len(test)
    results.append(check(
        f"{AREA}: held-out-name 'who' answers with the target last are flagged (last_mention)",
        _flags(report, "last_mention") and report.detectors["last_mention"].accuracy == 1.0 and held_out == 1.0
        and abs(report.presence_chance - 1.0 / toy.FACTS) < 1e-9,
        held_out_answer_rate=held_out,
        **_summary(report, "last_mention", "position", "majority"),
    ))
    report = leak_report(*who(None), answer_vocab=names)
    results.append(check(
        f"{AREA}: held-out-name 'who' control (target anywhere) is not flagged",
        report.status == "clean",
        **_summary(report, "last_mention", "position", "majority"),
    ))
    return results


def _pair_checks(registry: Any) -> list[dict[str, Any]]:
    pairs = [tuple(e.example() for e in toy.counterfactual_pair(registry, "test", i)) for i in range(PAIRS)]
    opposite = all(a.target != b.target and a.question == b.question
                   and sorted(words(a.context)) == sorted(words(b.context)) for a, b in pairs)
    null = example_presence_chance(toy.PLACES)
    chance = pair_chance(pairs, null)
    train = _examples(registry, "train", N_TRAIN)
    oracle: Callable[[QAExample], str] = lambda example: example.answer
    fitted = {kind.name: kind().fit(train, answer_vocab=toy.PLACES)
              for kind in (BagOfWordsDetector, MajorityDetector, QuestionOnlyDetector)}
    surface = {name: pair_accuracy(pairs, detector.predict) for name, detector in fitted.items()}
    last = LastMentionDetector().fit(train, answer_vocab=toy.PLACES)
    single = sum(last.predict(e) == e.target for pair in pairs for e in pair) / (2 * len(pairs))
    return [
        check(
            f"{AREA}: counterfactual pairs defeat order-blind surface cues (<= pair chance), oracle scores 1.0",
            opposite and pair_accuracy(pairs, oracle) == 1.0
            and all(accuracy <= chance for accuracy in surface.values())
            and pair_pvalue(pairs, oracle, null) < ALPHA,
            pairs=len(pairs),
            opposite_answers_same_words=opposite,
            pair_chance=round(chance, 4),
            oracle_pair_accuracy=pair_accuracy(pairs, oracle),
            oracle_p_value=float(f"{pair_pvalue(pairs, oracle, null):.3g}"),
            surface_pair_accuracy={name: round(value, 4) for name, value in surface.items()},
            # A position rule is right or wrong on both twins together (the answer keeps its line),
            # so pairs do not push it below its single-item accuracy; the position detector covers it.
            last_mention_pair_accuracy=round(pair_accuracy(pairs, last.predict), 4),
            last_mention_single_accuracy=round(single, 4),
        ),
    ]


def checks() -> list[dict[str, Any]]:
    registry = toy.make_registry()
    return _clean_checks(registry) + _planted_checks(registry) + _pair_checks(registry)


__all__ = ["checks"]
