"""Read-only guard checks: every planted write path is caught, clean evaluation is not flagged.

Planted flaws must raise `ReadOnlyViolation` (with the change named in its
evidence); clean controls must pass through the guard untouched. The toy
`CardStore` is used for the store paths; its `fingerprint()` already covers
card order, the `enabled` switch and the `capacity` budget, so the LRU and
lesion variants need no toy change (the LRU reorder is a local subclass).
Global RNG state is saved and restored around the whole run.
"""
from __future__ import annotations

import random
import warnings
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional, Sequence

import torch
from torch import nn

from . import check
from ..readonly import ReadOnlyViolation, read_only, rng_state, set_rng_state
from ..toy import (
    PLACES,
    CardStore,
    Episode,
    Fact,
    episodes,
    make_registry,
    parse_line,
    parse_question,
    parse_update,
)

AREA = "readonly"
_TOY_EPISODES = 24


def _name(what: str) -> str:
    return f"{AREA}: {what}"


def _run(block: Callable[[], Any], model: Optional[nn.Module] = None, stores: Sequence[Any] = (),
         **guard: Any) -> tuple[Optional[ReadOnlyViolation], Optional[BaseException]]:
    """Run `block` under `read_only`; return (violation or None, any other exception or None)."""
    try:
        with read_only(model, stores, **guard):
            block()
    except ReadOnlyViolation as violation:
        return violation, None
    except Exception as error:  # noqa: BLE001 - the clean exception path is itself checked
        return None, error
    return None, None


def _changes(violation: Optional[ReadOnlyViolation]) -> list[str]:
    return list(violation.changes) if violation is not None else []


def _mentions(violation: Optional[ReadOnlyViolation], *needles: str) -> bool:
    """The violation names a change containing every needle in one line."""
    return any(all(needle in change for needle in needles) for change in _changes(violation))


def _caught(what: str, violation: Optional[ReadOnlyViolation], *needles: str,
            **evidence: Any) -> dict[str, Any]:
    return check(_name(what), violation is not None and _mentions(violation, *needles),
                 raised=violation is not None, expected=list(needles),
                 changes=_changes(violation)[:6], **evidence)


def _net() -> nn.Sequential:
    torch.manual_seed(0)
    return nn.Sequential(
        nn.Linear(4, 8), nn.BatchNorm1d(8), nn.ReLU(), nn.Dropout(0.5), nn.Linear(8, 2)
    )


def _inputs(rows: int = 6) -> torch.Tensor:
    return torch.randn(rows, 4, generator=torch.Generator().manual_seed(1))


def _modes(model: nn.Module) -> dict[str, bool]:
    return {name or "<root>": module.training for name, module in model.named_modules()}


# ---- planted model paths ------------------------------------------------------------------

def _mutation_then_exception() -> list[dict[str, Any]]:
    model = _net()
    failure = RuntimeError("planted evaluation failure")

    def planted() -> None:
        model[0].weight.add_(1.0)
        raise failure

    violation, other = _run(planted, model)
    caught = _caught("a write followed by an evaluation error is caught and chained",
                     violation, "0.weight", "content", chained=bool(
                         violation is not None and violation.__cause__ is failure))
    caught["passed"] = caught["passed"] and caught["chained"] and other is None

    clean = _net()
    clean_failure = KeyError("clean evaluation failure")

    def control() -> None:
        clean(_inputs())
        raise clean_failure

    violation, other = _run(control, clean)
    return [caught, check(
        _name("an evaluation error without writes surfaces unchanged (control)"),
        violation is None and other is clean_failure,
        raised=type(other).__name__ if other is not None else None,
        changes=_changes(violation)[:6],
    )]


def _same_value_replacement() -> dict[str, Any]:
    model = _net()

    def planted() -> None:
        model[0].weight = nn.Parameter(model[0].weight.detach().clone())

    violation, _ = _run(planted, model)
    return _caught("a same-value Parameter replacement is caught", violation, "0.weight", "identity")


def _requires_grad_change() -> dict[str, Any]:
    model = _net()
    violation, _ = _run(lambda: model[4].bias.requires_grad_(False), model)
    return _caught("a requires_grad change is caught", violation, "4.bias", "requires_grad")


def _mutate_then_revert() -> dict[str, Any]:
    model = _net()
    weight = model[0].weight

    def planted() -> None:
        saved = weight.detach().clone()
        weight.add_(0.25)
        weight.copy_(saved)

    violation, _ = _run(planted, model)
    result = _caught("a mutate-then-revert write is caught by the version counter",
                     violation, "0.weight", "version")
    result["content_unchanged"] = not _mentions(violation, "0.weight", "content")
    result["passed"] = result["passed"] and result["content_unchanged"]
    return result


def _grad_left_behind() -> dict[str, Any]:
    model = _net()

    def planted() -> None:
        with torch.enable_grad():
            model(_inputs()).pow(2).mean().backward()

    violation, _ = _run(planted, model)
    return _caught("a .grad left behind by evaluation is caught", violation, "0.weight", "grad")


@contextmanager
def _naive_guard(model: nn.Module) -> Iterator[None]:
    """The reviewed flaw: restore with `model.train(was_training)`, flipping frozen children."""
    was_training = model.training
    model.eval()
    try:
        with torch.no_grad():
            yield
    finally:
        model.train(was_training)


def _frozen_batchnorm() -> list[dict[str, Any]]:
    batch = _inputs()
    # The guard itself must keep every module's mode exactly (the naive guard does not).
    model = _net().train()
    model[1].eval()                                   # frozen BatchNorm inside a training model
    before = _modes(model)
    with read_only(model):
        model(batch)
    guarded_modes = _modes(model)
    stats = model[1].running_mean.clone()
    with torch.no_grad():
        model(batch)                                  # the next training-mode forward
    stats_kept = torch.equal(stats, model[1].running_mean)

    naive = _net().train()
    naive[1].eval()
    with _naive_guard(naive):
        naive(batch)
    naive_flipped = [name for name, mode in _modes(naive).items() if mode != before[name]]
    guard_ok = check(
        _name("the guard never flips a frozen BatchNorm's mode"),
        guarded_modes == before and stats_kept and bool(naive_flipped),
        modes_kept=guarded_modes == before, stats_kept_after=stats_kept,
        naive_guard_flipped=naive_flipped,
    )

    # Evaluation that flips the frozen BatchNorm to train mode updates its stats: caught.
    flipped = _net().train()
    flipped[1].eval()

    def planted() -> None:
        flipped.train()
        flipped(batch)

    violation, _ = _run(planted, flipped)
    caught = _caught("evaluation flipping a frozen BatchNorm to train mode is caught",
                     violation, "1.running_mean", "content")
    caught["mode_restored"] = flipped[1].training is False
    caught["passed"] = caught["passed"] and caught["mode_restored"]
    return [guard_ok, caught]


def _trained_adam(model: nn.Module) -> torch.optim.Adam:
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    model(_inputs()).pow(2).mean().backward()
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    return optimizer


def _optimizer_state_only() -> list[dict[str, Any]]:
    model = _net()
    optimizer = _trained_adam(model)
    moment = optimizer.state[model[0].weight]["exp_avg"]
    violation, _ = _run(lambda: moment.mul_(0.5), model, optimizers=[optimizer])
    moments = _caught("an optimizer-state-only change is caught", violation, "optimizers[0]")
    moments["weights_untouched"] = not any(
        change.startswith("parameter") for change in _changes(violation))
    moments["passed"] = moments["passed"] and moments["weights_untouched"]

    scheduled = _net()
    scheduler = torch.optim.lr_scheduler.StepLR(_trained_adam(scheduled), step_size=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)   # step order is irrelevant to the guard
        violation, _ = _run(scheduler.step, scheduled, optimizers=[scheduler])
    return [moments, _caught("an LR scheduler stepped during evaluation is caught",
                             violation, "optimizers[0]", "StepLR")]


def _train_then_restore() -> dict[str, Any]:
    model = _net()

    def planted() -> None:
        saved = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
        optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
        with torch.enable_grad():
            model(_inputs()).pow(2).mean().backward()
        optimizer.step()
        model.load_state_dict(saved)
        optimizer.zero_grad(set_to_none=True)

    violation, _ = _run(planted, model)
    result = _caught("train-then-restore weights is caught by the version counter",
                     violation, "0.weight", "version")
    result["content_unchanged"] = not _mentions(violation, "0.weight", "content")
    result["passed"] = result["passed"] and result["content_unchanged"]
    return result


# ---- planted toy store paths --------------------------------------------------------------

def _toy_episodes() -> list[Episode]:
    return episodes(make_registry(), "test", _TOY_EPISODES)


def _observe(store: CardStore, episode: Episode) -> None:
    store.clear()
    for line in episode.lines:
        fact, update = parse_line(line), parse_update(line)
        if fact is not None:
            store.write(fact)
        if update is not None:
            store.apply(update)


def _answer(store: CardStore, episode: Episode, *, write_guess: bool = False) -> Optional[str]:
    parsed = parse_question(episode.question)
    if parsed is None:
        return None
    found = store.read(*parsed)
    if write_guess:
        # Planted flaw: answering caches a guess into memory.
        guess = next(place for place in PLACES if place != found)
        store.write(Fact(parsed[0], parsed[1], guess))
    return found


class _LRUCardStore(CardStore):
    """Planted flaw: an LRU-style read that moves the card it reads to the back."""

    def read(self, name: str, obj: str) -> Optional[str]:
        key = (name, obj)
        if self.enabled and key in self.cards:
            self.cards[key] = self.cards.pop(key)
        return super().read(name, obj)


def _per_episode(store: CardStore, block: Callable[[Episode], Any], pool: Sequence[Episode],
                 reset: Callable[[], None] = lambda: None) -> tuple[int, list[str]]:
    caught, changes = 0, []
    for episode in pool:
        reset()
        _observe(store, episode)
        violation, _ = _run(lambda: block(episode), None, [store])
        if violation is not None and _mentions(violation, "store[0]", "fingerprint"):
            caught += 1
            changes = changes or _changes(violation)
    return caught, changes


def _store_written_during_answer(pool: Sequence[Episode]) -> dict[str, Any]:
    store = CardStore()
    caught, changes = _per_episode(store, lambda e: _answer(store, e, write_guess=True), pool)
    return check(_name("a toy CardStore written during answering is caught"),
                 caught == len(pool) > 0, caught=caught, episodes=len(pool), changes=changes[:3])


def _lru_reorder(pool: Sequence[Episode]) -> dict[str, Any]:
    store = _LRUCardStore()
    reordered = []
    for episode in pool:
        _observe(store, episode)
        parsed = parse_question(episode.question)
        if parsed is not None and parsed in store.cards and list(store.cards)[-1] != parsed:
            reordered.append(episode)       # a reorder is only visible if the card is not last
    caught, changes = _per_episode(store, lambda e: _answer(store, e), reordered)
    return check(_name("an LRU-style reorder of the toy CardStore on read is caught"),
                 caught == len(reordered) > 0, caught=caught, episodes=len(reordered),
                 changes=changes[:3])


def _lesion_left_disabled(pool: Sequence[Episode]) -> list[dict[str, Any]]:
    store = CardStore()

    def disable(episode: Episode) -> None:
        store.enabled = False               # a lesion switched on and never switched back
        _answer(store, episode)

    def switch_on() -> None:
        store.enabled = True

    caught, changes = _per_episode(store, disable, pool, switch_on)
    lesion = check(_name("a toy CardStore lesion flag left disabled is caught"),
                   caught == len(pool) > 0, caught=caught, episodes=len(pool), changes=changes[:3])

    budget = CardStore()

    def shrink(episode: Episode) -> None:
        budget.capacity = 1                 # a budget changed without any write
        _answer(budget, episode)

    def unbounded() -> None:
        budget.capacity = None

    caught, changes = _per_episode(budget, shrink, pool, unbounded)
    return [lesion, check(_name("a toy CardStore budget change during answering is caught"),
                          caught == len(pool) > 0, caught=caught, episodes=len(pool),
                          changes=changes[:3])]


# ---- clean controls ------------------------------------------------------------------------

def _clean_eval_forward() -> dict[str, Any]:
    model = _net().train()
    model[1].eval()
    before = _modes(model)
    batch = _inputs()
    outputs: list[torch.Tensor] = []

    def control() -> None:
        outputs.append(model(batch))
        outputs.append(model(batch))

    violation, other = _run(control, model)
    deterministic = len(outputs) == 2 and torch.equal(outputs[0], outputs[1])
    return check(_name("an ordinary eval forward with BatchNorm and Dropout is not flagged"),
                 violation is None and other is None and deterministic and _modes(model) == before,
                 changes=_changes(violation)[:6], dropout_off=deterministic,
                 modes_restored=_modes(model) == before,
                 error=repr(other) if other is not None else None)


class _Sampler(nn.Module):
    """Evaluation that samples: global torch/python RNG plus a module-held generator."""

    def __init__(self) -> None:
        super().__init__()
        self.linear = nn.Linear(4, 4)
        self.generator = torch.Generator().manual_seed(7)
        self.rng = random.Random(7)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        noise = torch.rand(x.shape, generator=self.generator) + torch.rand(x.shape)
        return self.linear(x) + noise * (random.random() + self.rng.random())


def _clean_rng_eval() -> dict[str, Any]:
    torch.manual_seed(3)
    random.seed(3)
    model = _Sampler()
    before_torch, before_python = torch.get_rng_state(), random.getstate()
    before_module = (model.generator.get_state(), model.rng.getstate())
    violation, other = _run(lambda: model(_inputs()), model)
    restored = (
        torch.equal(before_torch, torch.get_rng_state())
        and before_python == random.getstate()
        and torch.equal(before_module[0], model.generator.get_state())
        and before_module[1] == model.rng.getstate()
    )
    # The next draw after the guard equals the draw an unguarded run would have made.
    after_guard = torch.rand(3)
    torch.set_rng_state(before_torch)
    unguarded = torch.rand(3)
    same_next = torch.equal(after_guard, unguarded)
    return check(_name("an eval that consumes RNG is not flagged and RNG is restored"),
                 violation is None and other is None and restored and same_next,
                 changes=_changes(violation)[:6], rng_restored=restored,
                 next_draw_equal=same_next, error=repr(other) if other is not None else None)


class _Rotary(nn.Module):
    """A derived cache that legitimately grows when evaluation sees a longer input."""

    def __init__(self) -> None:
        super().__init__()
        self.register_buffer("cos_cached", torch.ones(8), persistent=False)
        self.cached_len = 8

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.shape[0] > self.cos_cached.shape[0]:
            self.cos_cached = torch.cos(torch.arange(x.shape[0]).float())
            self.cached_len = x.shape[0]
        return x * self.cos_cached[: x.shape[0]].unsqueeze(-1)


def _rotary_net() -> nn.Sequential:
    torch.manual_seed(0)
    return nn.Sequential(nn.Linear(4, 4), _Rotary())


def _allowlisted_cache() -> list[dict[str, Any]]:
    long_input = torch.ones(16, 4)
    allow = ("*.cos_cached", "*.cached_len")
    model = _rotary_net()
    violation, other = _run(lambda: model(long_input), model, allow_changes=allow)
    grew = model[1].cos_cached.shape[0] == 16
    clean = check(_name("an allowlisted growing derived cache is not flagged"),
                  violation is None and other is None and grew,
                  changes=_changes(violation)[:6], cache_grew=grew,
                  error=repr(other) if other is not None else None)

    # The allowlist is what makes it clean: unlisted, the same growth is caught.
    unlisted = _rotary_net()
    violation, _ = _run(lambda: unlisted(long_input), unlisted)
    teeth = _caught("the same cache growth without an allowlist is caught",
                    violation, "1.cos_cached")

    # The allowlist can never excuse a parameter.
    try:
        with read_only(_rotary_net(), allow_changes=["0.*"]):
            pass
        refused = False
    except ValueError:
        refused = True
    return [clean, teeth, check(_name("an allowlist covering parameters is refused"), refused,
                                refused=refused)]


def _clean_toy_pass(pool: Sequence[Episode]) -> dict[str, Any]:
    store = CardStore()
    flagged, correct = 0, 0
    for episode in pool:
        _observe(store, episode)
        answers: list[Optional[str]] = []
        violation, other = _run(lambda: answers.append(_answer(store, episode)), None, [store])
        flagged += violation is not None or other is not None
        correct += bool(answers) and answers[0] == episode.target.place
    return check(_name("a clean toy answering pass is not flagged"),
                 flagged == 0 and len(pool) > 0, flagged=flagged, episodes=len(pool),
                 accuracy=correct / max(len(pool), 1))


def checks() -> list[dict[str, Any]]:
    saved = rng_state()
    try:
        pool = _toy_episodes()
        results: list[dict[str, Any]] = []
        results += _mutation_then_exception()
        results.append(_same_value_replacement())
        results.append(_requires_grad_change())
        results.append(_mutate_then_revert())
        results.append(_grad_left_behind())
        results += _frozen_batchnorm()
        results += _optimizer_state_only()
        results.append(_train_then_restore())
        results.append(_store_written_during_answer(pool))
        results.append(_lru_reorder(pool))
        results += _lesion_left_disabled(pool)
        results.append(_clean_eval_forward())
        results.append(_clean_rng_eval())
        results += _allowlisted_cache()
        results.append(_clean_toy_pass(pool))
        return results
    finally:
        set_rng_state(saved)


__all__ = ["checks"]
