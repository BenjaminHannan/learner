"""Paired Step 0 checks for the ablation rule and the continual-learning metrics.

A small toy system is built here: a card store that reads each episode (fact
lines, then the rule line through `parse_update`) and answers read-only, and a
plain lookup that returns the place a line first stated. On the update
families (moved, corrected, chained, swapped) the store genuinely beats the
lookup at the same retrieval budget (one card of three tokens per question),
so `judge_component` has a real component to pass. Every planted flaw must be
caught for the reason it was planted, and the clean control beside it must
not be flagged. Everything is deterministic: fixed toy seeds, fixed private
RNG seeds, and the judge resets the global RNG around every evaluation.
"""
from __future__ import annotations

from contextlib import contextmanager
import random
from typing import Any, Callable, Iterator, Mapping, Optional, Sequence

from ..ablation import Account, Arm, Component, Verdict, judge_component
from ..leaks import words
from ..metrics import (
    ContinualMatrix,
    expected_calibration_error,
    mcnemar_greater,
    mean,
    recall_at_k,
    steps_to_threshold,
)
from ..policy import ALPHA, LESION_GAIN_FRACTION, MIN_EFFECT, MIN_ITEMS
from ..readonly import read_only
from ..toy import (
    CardStore,
    Episode,
    PLACES,
    UPDATE_FAMILIES,
    episodes,
    make_registry,
    parse_line,
    parse_question,
    parse_update,
)
from . import check

AREA = "ablation"
KIND = "toy_store"
SPLIT = "train"                      # train holds moved, chained and swapped: all update families
N_ITEMS = 300
CARD_TOKENS = 3                      # one retrieved card or encoded line: (name, object, place)
GUESS = PLACES[0]                    # the answer when nothing is retrieved
INFORMATION = frozenset({"episode_context", "question"})


# ---------------------------------------------------------------- toy system

class Meter:
    """Counts what an answerer retrieves, for audited accounts."""

    def __init__(self) -> None:
        self.items = 0
        self.tokens = 0

    def take(self, items: int, tokens: int) -> None:
        self.items += items
        self.tokens += tokens


def lookup_answer(episode: Episode, meter: Optional[Meter] = None) -> str:
    """Plain lookup: retrieve the one encoded line that first stated the asked pair's place."""
    asked = parse_question(episode.question)
    for line in episode.lines:
        fact = parse_line(line)
        if asked is not None and fact is not None and (fact.name, fact.obj) == asked:
            if meter is not None:
                meter.take(1, CARD_TOKENS)
            return fact.place
    return GUESS


def full_context_answer(episode: Episode, meter: Optional[Meter] = None) -> str:
    """As good as the store, but it retrieves every line (a larger retrieval budget)."""
    cards = CardStore()
    for line in episode.lines:
        fact, update = parse_line(line), parse_update(line)
        if fact is not None:
            cards.write(fact)
        if update is not None:
            cards.apply(update)
        if meter is not None:
            meter.take(1, len(words(line)))
    asked = parse_question(episode.question)
    found = cards.read(*asked) if asked is not None else None
    return found if found is not None else GUESS


def observe(store: CardStore, episode: Episode) -> None:
    """Write each fact line, then apply the rule line, so moves and swaps land in the cards."""
    for line in episode.lines:
        fact, update = parse_line(line), parse_update(line)
        if fact is not None:
            store.write(fact)
        if update is not None:
            store.apply(update)


class StoreSystem:
    """Reads an episode into cards and answers read-only; with the store off it falls back to lookup."""

    def __init__(self, test: Sequence[Episode]) -> None:
        self.store = CardStore()
        self.fallback = True
        self.meter = Meter()
        self.by_id = {episode.item_id: episode for episode in test}

    def answer(self, episode: Episode) -> str:
        asked = parse_question(episode.question)
        found = self.store.read(*asked) if asked is not None else None
        if found is not None:
            self.meter.take(1, CARD_TOKENS)
            return found
        if self.fallback:
            return lookup_answer(episode, self.meter)
        return GUESS

    def evaluate(self, ids: Sequence[str]) -> dict[str, float]:
        """Score exactly `ids`; each answer is given under the read-only guard; the store ends empty."""
        scores = {}
        for item in ids:
            episode = self.by_id[item]
            self.store.clear()
            observe(self.store, episode)
            with read_only(None, [self.store]):
                scores[item] = 1.0 if self.answer(episode) == episode.target.place else 0.0
        self.store.clear()
        return scores

    def state(self) -> str:
        """Fingerprint of everything a lesion of the store could touch."""
        return f"{self.store.fingerprint()}|fallback={self.fallback}"

    def account(self, ids: Sequence[str], run_id: str) -> Account:
        self.meter = Meter()
        self.evaluate(ids)
        meter, self.meter = self.meter, Meter()
        return Account(run_id, retrieved_items=meter.items, retrieved_tokens=meter.tokens,
                       information=INFORMATION)

    @contextmanager
    def disabled(self) -> Iterator[None]:
        """The store's lesion: switch it off; the system falls back to plain lookup."""
        self.store.enabled = False
        try:
            yield
        finally:
            self.store.enabled = True

    @contextmanager
    def destroyed(self) -> Iterator[None]:
        """A destructive lesion: store and fallback both off, so the system can only guess."""
        self.store.enabled = False
        self.fallback = False
        try:
            yield
        finally:
            self.store.enabled = True
            self.fallback = True

    @contextmanager
    def not_restored(self) -> Iterator[None]:
        """Planted: a lesion that never switches the store back on."""
        self.store.enabled = False
        yield

    @contextmanager
    def no_op(self) -> Iterator[None]:
        """Planted: a lesion that touches nothing."""
        yield

    def component(self, lesion: Callable[[], Any], name: str = "card_store") -> Component:
        return Component(name, KIND, lesion=lesion, state=self.state)


def arm_of(name: str, answer: Callable[[Episode, Meter], str], test: Sequence[Episode],
           run_id: str) -> Arm:
    """Score an answerer on `test` by item ID and account for what it retrieved."""
    meter = Meter()
    scores = {e.item_id: 1.0 if answer(e, meter) == e.target.place else 0.0 for e in test}
    return Arm(name, scores, Account(run_id, retrieved_items=meter.items,
                                     retrieved_tokens=meter.tokens, information=INFORMATION))


# ---------------------------------------------------------------- synthetic arms

class TableSystem:
    """A component whose per-item scores are fixed tables, for exact statistical plants."""

    def __init__(self, full: Mapping[str, float], lesioned: Mapping[str, float]) -> None:
        self.full, self.lesioned, self.on = dict(full), dict(lesioned), True

    def evaluate(self, ids: Sequence[str]) -> dict[str, float]:
        table = self.full if self.on else self.lesioned
        return {item: table[item] for item in ids}

    def state(self) -> str:
        return f"on={self.on}"

    @contextmanager
    def lesion(self) -> Iterator[None]:
        self.on = False
        try:
            yield
        finally:
            self.on = True


def judge_table(full: Sequence[float], lesioned: Sequence[float], baseline: Sequence[float],
                *, min_effect: float = MIN_EFFECT) -> Verdict:
    """Judge a table component against a matched `plain_lookup` table on the same item IDs."""
    ids = [f"syn-{i:04d}" for i in range(len(full))]
    system = TableSystem(dict(zip(ids, full)), dict(zip(ids, lesioned)))
    budget = {"retrieved_items": len(ids), "retrieved_tokens": CARD_TOKENS * len(ids),
              "information": INFORMATION}
    base = Arm("plain_lookup", dict(zip(ids, baseline)), Account("syn-baseline", **budget))
    component = Component("table", KIND, lesion=system.lesion, state=system.state)
    return judge_component(component, system.evaluate, ids, Account("syn-full", **budget),
                           {"plain_lookup": base}, min_effect=min_effect)


# ---------------------------------------------------------------- helpers

def _has(verdict: Verdict, fragment: str) -> bool:
    return any(fragment in reason for reason in verdict.reasons)


def _summary(verdict: Verdict) -> dict[str, Any]:
    return {
        "passed": verdict.passed,
        "n_items": verdict.n_items,
        "full": verdict.full,
        "lesioned": verdict.lesioned,
        "baseline_means": dict(verdict.baseline_means),
        "lesion_fraction": verdict.lesion_fraction,
        "reasons": list(verdict.reasons),
    }


def _planted(name: str, planted: Verdict, clean: Verdict, fragment: str, **extra: Any) -> dict[str, Any]:
    """Planted verdict fails for `fragment`; the clean verdict passes and never mentions it."""
    caught = not planted.passed and _has(planted, fragment)
    clean_ok = clean.passed and not _has(clean, fragment)
    return check(f"{AREA}: {name}", caught and clean_ok, flaw_caught=caught, clean_ok=clean_ok,
                 expected_reason=fragment, planted=_summary(planted), clean=_summary(clean), **extra)


def _disjoint_stages(pool: Sequence[Episode], stages: int, per_stage: int) -> list[list[Episode]]:
    """Greedily pick episodes whose (name, object) keys never collide, within or across stages."""
    seen: set[tuple[str, str]] = set()
    chosen: list[Episode] = []
    for episode in pool:
        keys = {(fact.name, fact.obj) for fact in episode.facts}
        if keys & seen:
            continue
        seen |= keys
        chosen.append(episode)
        if len(chosen) == stages * per_stage:
            break
    if len(chosen) < stages * per_stage:
        raise RuntimeError("not enough collision-free toy episodes for the forgetting check")
    return [chosen[i * per_stage:(i + 1) * per_stage] for i in range(stages)]


def _stage_matrix(stages: Sequence[Sequence[Episode]], capacity: Optional[int]) -> ContinualMatrix:
    """Train one store stage by stage (never cleared); score every task read-only after each stage."""
    store = CardStore(capacity)
    matrix = ContinualMatrix(len(stages))
    for stage, batch in enumerate(stages):
        for episode in batch:
            observe(store, episode)
        for task, tested in enumerate(stages):
            with read_only(None, [store]):
                hits = [store.read(*parse_question(e.question)) == e.target.place for e in tested]
            matrix.record(stage, task, mean([1.0 if hit else 0.0 for hit in hits]))
    return matrix


# ---------------------------------------------------------------- checks

def _ablation_checks() -> list[dict[str, Any]]:
    registry = make_registry()
    test = episodes(registry, SPLIT, N_ITEMS)
    other = episodes(registry, SPLIT, N_ITEMS, start=N_ITEMS)
    ids = [episode.item_id for episode in test]
    assert len(ids) >= MIN_ITEMS and all(e.rule_family in UPDATE_FAMILIES for e in test)

    system = StoreSystem(test)
    full_account = system.account(ids, "toy-store")
    lookup = arm_of("plain_lookup", lookup_answer, test, "toy-plain-lookup")
    baselines = {"plain_lookup": lookup}
    trained_without = arm_of("trained_without", lookup_answer, test, "toy-trained-without-store")

    def judge(component: Component,
              evaluate: Optional[Callable[[tuple[str, ...]], Mapping[str, float]]] = None,
              items: Sequence[str] = ids, arms: Optional[Mapping[str, Arm]] = None,
              account: Account = full_account, **kwargs: Any) -> Verdict:
        return judge_component(component, evaluate or system.evaluate, items, account,
                               baselines if arms is None else arms, min_effect=MIN_EFFECT, **kwargs)

    out = []

    # Clean control: the store genuinely beats plain lookup at a matched retrieval budget.
    good = judge(system.component(system.disabled))
    full_scores = system.evaluate(ids)
    by_family = {
        family: {
            "store": mean([full_scores[e.item_id] for e in test if e.rule_family == family]),
            "plain_lookup": mean([lookup.scores[e.item_id] for e in test if e.rule_family == family]),
        }
        for family in sorted({e.rule_family for e in test})
    }
    matched = all(getattr(full_account, f) == getattr(lookup.account, f)
                  for f in ("retrieved_items", "retrieved_tokens"))
    wins_everywhere = all(v["store"] - v["plain_lookup"] > MIN_EFFECT for v in by_family.values())
    out.append(check(f"{AREA}: a useful store with matched budgets passes",
                     good.passed and matched and wins_everywhere and good.lesion_removes_gain,
                     budgets_matched=matched, full_account=full_account.as_dict(),
                     baseline_account=lookup.account.as_dict(), by_family=by_family,
                     verdict=_summary(good)))

    # The same store against an equally good (matched-budget) rival fails.
    rival_scores = StoreSystem(test).evaluate(ids)
    rival = Arm("rival_store", rival_scores, Account("toy-rival-store", retrieved_items=full_account.retrieved_items,
                                                     retrieved_tokens=full_account.retrieved_tokens,
                                                     information=INFORMATION))
    out.append(_planted("the same store fails against an equally good baseline",
                        judge(system.component(system.disabled), arms={**baselines, "rival_store": rival}),
                        good, "does not beat 'rival_store'"))

    # A lesion that changes no state fails.
    out.append(_planted("a lesion that changes no state fails",
                        judge(system.component(system.no_op)), good,
                        "lesion changed no component state"))

    # A drifting evaluation (private, unreset RNG) fails; RNG noise from the global RNG is paired.
    drift_rng = random.Random(1234)

    def drifting(items: tuple[str, ...]) -> dict[str, float]:
        scores = system.evaluate(items)
        return {i: (1.0 - s) if drift_rng.random() < 0.05 else s for i, s in scores.items()}

    def global_noise(items: tuple[str, ...]) -> dict[str, float]:
        scores = system.evaluate(items)
        return {i: (1.0 - s) if random.random() < 0.05 else s for i, s in scores.items()}

    paired_noise = judge(system.component(system.disabled), evaluate=global_noise)
    out.append(_planted("a drifting (nondeterministic) evaluation fails",
                        judge(system.component(system.disabled), evaluate=drifting), paired_noise,
                        "evaluation not repeatable",
                        note="clean control: evaluation noise drawn from the global RNG, which the judge resets"))

    # A lesion that does not restore state fails (and the system is repaired afterwards).
    broken = judge(system.component(system.not_restored))
    left_off = not system.store.enabled
    system.store.enabled = True
    out.append(_planted("a lesion that does not restore state fails", broken, good,
                        "lesion did not restore", store_left_disabled=left_off))

    # A destructive lesion without a trained-without control is refused; with one it is judged.
    destructive = judge(system.component(system.destroyed))
    controlled = judge(system.component(system.destroyed), trained_without=trained_without)
    refused = not destructive.passed and destructive.destructive and _has(destructive, "destructive lesion")
    judged = (controlled.passed and controlled.destructive and controlled.trained_without is not None
              and not _has(controlled, "destructive lesion"))
    out.append(check(f"{AREA}: a destructive lesion needs a trained-without control",
                     refused and judged, refused_without_control=refused, judged_with_control=judged,
                     destructive_overshoot=destructive.destructive_overshoot,
                     trained_without_mean=controlled.trained_without,
                     without_control=_summary(destructive), with_control=_summary(controlled)))

    # A one-item test fails.
    out.append(_planted("a one-item test fails", judge(system.component(system.disabled), items=ids[:1]),
                        good, "only 1 item(s)"))

    # A baseline scored on different items (same count) is refused.
    shifted = arm_of("plain_lookup", lookup_answer, other, "toy-plain-lookup-other-items")
    out.append(_planted("a baseline scored on different items is refused",
                        judge(system.component(system.disabled), arms={"plain_lookup": shifted}),
                        good, "refused baseline 'plain_lookup': scores: missing"))

    # A budget mismatch is refused: the full-context reader is as good but retrieves every line.
    reader = arm_of("plain_lookup", full_context_answer, test, "toy-full-context")
    out.append(_planted("a budget mismatch is refused",
                        judge(system.component(system.disabled), arms={"plain_lookup": reader}),
                        good, "budget mismatch: retrieved_items",
                        mismatched_account=reader.account.as_dict()))

    # A missing required baseline is refused.
    missing = judge(system.component(system.disabled), arms={})
    out.append(_planted("a missing required baseline is refused", missing, good,
                        "missing required baseline", missing_baselines=list(missing.missing_baselines)))
    return out


def _statistics_checks() -> list[dict[str, Any]]:
    out = []
    n = N_ITEMS

    # Noise-level wins: 4/300 discordant items, all favouring the full system.
    baseline = [1.0 if i % 2 else 0.0 for i in range(n)]
    zeros = [i for i in range(n) if baseline[i] == 0.0]

    def flipped(count: int) -> list[float]:
        full = list(baseline)
        for i in zeros[:count]:
            full[i] = 1.0
        return full

    noise, clear = flipped(4), flipped(40)
    planted = judge_table(noise, baseline, baseline)
    planted_floor = judge_table(noise, baseline, baseline, min_effect=0.001)
    clean = judge_table(clear, baseline, baseline)
    clean_floor = judge_table(clear, baseline, baseline, min_effect=0.001)
    exact_p = mcnemar_greater(noise, baseline)
    caught = (not planted.passed and not planted_floor.passed
              and planted_floor.baseline_pvalues["plain_lookup"] >= ALPHA and exact_p >= ALPHA)
    clean_ok = clean.passed and clean_floor.passed
    out.append(check(f"{AREA}: noise-level wins (4/300 discordant) fail", caught and clean_ok,
                     flaw_caught=caught, clean_ok=clean_ok, mcnemar_p=exact_p,
                     pvalue_at_tiny_min_effect=planted_floor.baseline_pvalues.get("plain_lookup"),
                     planted=_summary(planted), clean_40_of_300=_summary(clean),
                     note="min_effect 0.001 isolates the significance test from the effect floor"))

    # A constant 0.001 improvement fails; a constant 0.1 improvement passes.
    half = [0.5] * n
    out.append(_planted("a constant 0.001 improvement fails",
                        judge_table([0.501] * n, half, half), judge_table([0.6] * n, half, half),
                        "does not beat 'plain_lookup' by min_effect"))

    # A component removing only 40% of its gain fails; one removing 80% passes.
    full = [1.0] * n
    base = [1.0] * 100 + [0.0] * (n - 100)          # gain on the last 200 items

    def lesioned(share: float) -> list[float]:
        lost = int(round(share * (n - 100)))
        return [1.0] * 100 + [0.0] * lost + [1.0] * (n - 100 - lost)

    planted = judge_table(full, lesioned(0.4), base)
    clean = judge_table(full, lesioned(0.8), base)
    trial_rng = random.Random(7)
    trials = []
    for _ in range(20):
        les = [1.0] * 100 + [0.0 if trial_rng.random() < 0.4 else 1.0 for _ in range(n - 100)]
        trials.append(judge_table(full, les, base).passed)
    caught = not planted.passed and _has(planted, "lesion does not remove") and not any(trials)
    clean_ok = clean.passed and not _has(clean, "lesion does not remove")
    out.append(check(f"{AREA}: a component removing only 40% of its gain fails",
                     caught and clean_ok, flaw_caught=caught, clean_ok=clean_ok,
                     gain_fraction=LESION_GAIN_FRACTION, random_40pct_trials_passed=sum(trials),
                     random_40pct_trials=len(trials), planted=_summary(planted),
                     clean_80pct=_summary(clean)))
    return out


def _metric_checks() -> list[dict[str, Any]]:
    out = []
    registry = make_registry()

    # Forgetting: a capacity-limited store forgets earlier stages; an unlimited one does not.
    stages = _disjoint_stages(episodes(registry, SPLIT, 400), stages=4, per_stage=10)
    keys = [{(f.name, f.obj) for e in stage for f in e.facts} for stage in stages]
    disjoint = sum(len(k) for k in keys) == len(set().union(*keys))
    per_stage_cards = len(keys[0])
    limited = _stage_matrix(stages, capacity=per_stage_cards).forgetting_report()
    unlimited = _stage_matrix(stages, capacity=None).forgetting_report()
    forgets = limited["post_acquisition"] > 0.9 and limited["backward_transfer"] < -0.9
    keeps = (unlimited["post_acquisition"] == 0.0 and unlimited["chaudhry"] == 0.0
             and unlimited["average_accuracy"] == 1.0)
    out.append(check(f"{AREA}: metrics: a capacity-limited store forgets, an unlimited one does not",
                     disjoint and forgets and keeps, keys_disjoint=disjoint, capacity=per_stage_cards,
                     limited=limited, unlimited=unlimited))

    # Chaudhry vs post-acquisition forgetting on a crafted matrix with forward transfer.
    crafted = ContinualMatrix(3)
    for stage, row in enumerate([[0.8, 0.9, 0.1], [0.8, 0.8, 0.2], [0.7, 0.7, 0.9]]):
        for task, score in enumerate(row):
            crafted.record(stage, task, score)
    plain = ContinualMatrix(3)
    for stage, row in enumerate([[0.8, 0.1, 0.1], [0.8, 0.8, 0.2], [0.7, 0.7, 0.9]]):
        for task, score in enumerate(row):
            plain.record(stage, task, score)
    c_report, p_report = crafted.forgetting_report(), plain.forgetting_report()
    close = lambda a, b: abs(a - b) < 1e-9
    separated = (close(c_report["post_acquisition"], 0.10) and close(c_report["chaudhry"], 0.15)
                 and close(c_report["chaudhry_per_task"][1], 0.20))
    agree = close(p_report["post_acquisition"], p_report["chaudhry"])
    out.append(check(f"{AREA}: metrics: Chaudhry and post-acquisition forgetting differ only under forward transfer",
                     separated and agree, crafted=c_report, no_forward_transfer=p_report))

    # Calibration: honest per-family confidence vs an overconfident constant 1.0, on the lookup answerer.
    held = episodes(registry, SPLIT, N_ITEMS, start=N_ITEMS)
    test = episodes(registry, SPLIT, N_ITEMS)
    rate = {}
    for family in sorted({e.rule_family for e in held}):
        hits = [lookup_answer(e) == e.target.place for e in held if e.rule_family == family]
        rate[family] = mean([1.0 if hit else 0.0 for hit in hits])
    correct = [lookup_answer(e) == e.target.place for e in test]
    honest = expected_calibration_error([rate[e.rule_family] for e in test], correct)
    overconfident = expected_calibration_error([1.0] * len(test), correct)
    out.append(check(f"{AREA}: metrics: calibration separates honest from overconfident",
                     honest < 0.1 and overconfident > 0.3, honest_ece=honest,
                     overconfident_ece=overconfident, lookup_accuracy=mean([float(c) for c in correct]),
                     honest_confidence_by_family=rate))

    # Recall@k: exact on a crafted ranking; on the toy, the store ranks the answer first more often.
    crafted_ranks = [["a", "b", "c"], ["b", "a", "c"], ["c", "b", "a"]]
    exact = [recall_at_k(crafted_ranks, ["a"] * 3, k) for k in (1, 2, 3)]
    exact_ok = all(close(x, y) for x, y in zip(exact, (1 / 3, 2 / 3, 1.0)))
    try:
        recall_at_k(crafted_ranks, ["a"] * 3, 0)
        rejects_zero = False
    except ValueError:
        rejects_zero = True
    store_system = StoreSystem(test)

    def ranking(first: str, episode: Episode) -> list[str]:
        stated = [fact.place for fact in episode.facts]
        return [first] + [place for place in stated if place != first]

    store_first = []
    for episode in test:
        store_system.store.clear()
        observe(store_system.store, episode)
        store_first.append(ranking(store_system.answer(episode), episode))
    lookup_first = [ranking(lookup_answer(e), e) for e in test]
    targets = [e.target.place for e in test]
    toy = {
        "store@1": recall_at_k(store_first, targets, 1),
        "lookup@1": recall_at_k(lookup_first, targets, 1),
        "store@4": recall_at_k(store_first, targets, 4),
        "lookup@4": recall_at_k(lookup_first, targets, 4),
    }
    toy_ok = (toy["store@1"] == 1.0 and toy["lookup@1"] < 1.0 - MIN_EFFECT
              and toy["store@4"] == toy["lookup@4"] == 1.0)
    out.append(check(f"{AREA}: metrics: Recall@k is exact and separates store from lookup at k=1",
                     exact_ok and rejects_zero and toy_ok, crafted_recall=exact, rejects_k0=rejects_zero,
                     toy=toy))

    # steps_to_threshold: a sustained run ignores a single spike, and input order does not matter.
    curve = [(10, 0.2), (20, 0.95), (30, 0.3), (40, 0.4), (50, 0.5), (60, 0.6), (70, 0.7),
             (80, 0.8), (90, 0.9), (100, 0.92), (110, 0.95)]
    shuffled = list(curve)
    random.Random(3).shuffle(shuffled)
    sustained = steps_to_threshold(curve, 0.9, sustain=3)
    sustained_shuffled = steps_to_threshold(shuffled, 0.9, sustain=3)
    single = steps_to_threshold(curve, 0.9, sustain=1)
    cut_short = steps_to_threshold([(10, 0.95), (20, 0.95)], 0.9, sustain=3)
    out.append(check(f"{AREA}: metrics: sustained steps_to_threshold ignores a single spike",
                     sustained == 90 and sustained_shuffled == 90 and single == 20 and cut_short is None,
                     sustained=sustained, sustained_shuffled=sustained_shuffled, single_point=single,
                     cut_short=cut_short))
    return out


def checks() -> list[dict[str, Any]]:
    """Every ablation and metrics check, deterministic, in well under 30 s on CPU."""
    return _ablation_checks() + _statistics_checks() + _metric_checks()


__all__ = ["checks"]
