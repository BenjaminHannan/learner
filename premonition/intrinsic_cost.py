"""The fixed built-in sense of good and bad (the intrinsic cost meter).

This is the "feel good / feel bad" box of the LeCun-style layout. It is a
plain meter: events and measurements go in after each move, one number per
feeling and a total come out. It holds counters and fixed formulas only. It
has no learned weights and nothing here is ever trained, by day or in sleep.

The wanting does not live here. A learned critic predicts these numbers and
moves are picked from the critic's predictions. For that reason the meter has
exactly one way to produce a number, ``step``, and ``step`` always advances
the meter's state: there is no method that scores a move that was not made.

Design, research basis and tests: design/08-intrinsic-cost-method.md.
Unlike premonition/motivation.py (a learned torch module), this file is pure
standard-library Python and imports no tensor library.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional


APPROVED_TERMS = ("curiosity", "underused_skill", "tiredness", "pain", "job_done", "remarks")
# PROPOSED terms need the owner's OK. Their exchange rates default to 0, so
# with the default table the meter is exactly the six approved feelings.
PROPOSED_TERMS = ("boredom", "bother")
TERMS = APPROVED_TERMS + PROPOSED_TERMS


def _finite(value, name, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if low is not None and value < low:
        raise ValueError(f"{name} must be at least {low}")
    if high is not None and value > high:
        raise ValueError(f"{name} must be at most {high}")
    return value


def _clip(value, limit):
    return max(-limit, min(limit, value))


def _keep(half_life):
    """Share of a quantity that survives one step, given a half-life in steps."""
    return 0.5 ** (1.0 / half_life)


@dataclass(frozen=True)
class ExchangeRates:
    """How much each feeling is worth. Hand numbers, set once per test by the lead.

    The owner may change them; testers never tune them. Every rate is a size
    (zero or more). The sign of each feeling is fixed inside the meter and
    cannot be flipped from here. ``curiosity``, ``underused_skill`` and
    ``tiredness`` are placeholders until their own tests fix a scale.
    """

    job_done: float = 1.0
    pain: float = 3.0
    nice: float = 1.0
    no: float = 3.0
    curiosity: float = 1.0
    underused_skill: float = 0.05
    tiredness: float = 1.0
    boredom: float = 0.0  # PROPOSED: off until the owner approves
    bother: float = 0.0  # PROPOSED: off until the owner approves

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            _finite(getattr(self, name), f"rate {name}", low=0.0)


@dataclass(frozen=True)
class MeterConfig:
    """Shape numbers of the fixed formulas. Fixed before a test, never tuned in one."""

    # curiosity: progress is divided by the scale, then clipped to +-clip.
    curiosity_scale: float = 1.0
    curiosity_clip: float = 1.0
    # under-used skill: recent-use counts halve after this many steps.
    skill_half_life: float = 50.0
    # tiredness: hours awake that fill the pressure, where it starts to cost,
    # and how many awake-hours one hour of sleep pays back.
    hours_to_full: float = 16.0
    tired_onset: float = 0.5
    sleep_payback: float = 2.0
    # pain: most hurt counted in one step.
    hurt_cap: float = 10.0
    # owner's "nice": each one multiplies the next by nice_fade; the size
    # recovers halfway to full after nice_half_life steps.
    nice_fade: float = 0.5
    nice_half_life: float = 200.0
    # PROPOSED boredom: running mean of progress (half-life in steps) below
    # which free time starts to feel boring.
    boredom_half_life: float = 50.0
    boredom_floor: float = 0.02
    # PROPOSED bother: most counted for one question to the owner.
    bother_cap: float = 5.0

    def __post_init__(self):
        for name in ("curiosity_scale", "curiosity_clip", "skill_half_life", "hours_to_full",
                     "sleep_payback", "hurt_cap", "nice_half_life", "boredom_half_life",
                     "boredom_floor", "bother_cap"):
            if _finite(getattr(self, name), name) <= 0:
                raise ValueError(f"{name} must be positive")
        if not 0 <= _finite(self.tired_onset, "tired_onset") < 1:
            raise ValueError("tired_onset must be within 0..1 (1 excluded)")
        if not 0 < _finite(self.nice_fade, "nice_fade") <= 1:
            raise ValueError("nice_fade must be within 0..1 (0 excluded)")


@dataclass(frozen=True)
class StepInput:
    """What the world and the harness report after one move. Never model outputs.

    job_open     the owner has given a job that is not finished or dropped.
    job_id       name of that job; needed when job_done is reported.
    job_done     the world says the job's goal is reached on this step.
    hurt         how much the world says this move hurt (0 = not at all).
    remark       the owner said "nice" (+1), "no" (-1) or nothing (0).
    error_past   error of the frozen past-self world model on this move's
                 result, measured before the world model trains on it.
    error_now    error of the current world model on the same result.
    skill        kind of command used (None = no move was made).
    hours        clock time this step took, from the harness clock.
    memory_fill  how full the day memory is, 0..1.
    asleep       this step was spent asleep.
    asked_owner  PROPOSED: a key naming the question put to the owner.
    """

    job_open: bool = False
    job_id: Optional[str] = None
    job_done: bool = False
    hurt: float = 0.0
    remark: int = 0
    error_past: Optional[float] = None
    error_now: Optional[float] = None
    skill: Optional[str] = None
    hours: float = 0.0
    memory_fill: float = 0.0
    asleep: bool = False
    asked_owner: Optional[str] = None

    def __post_init__(self):
        for name in ("job_open", "job_done", "asleep"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        for name in ("job_id", "skill", "asked_owner"):
            value = getattr(self, name)
            if value is not None and (type(value) is not str or not value):
                raise ValueError(f"{name} must be a non-empty string or None")
        if self.job_done and self.job_id is None:
            raise ValueError("job_done needs a job_id")
        if type(self.remark) is not int or self.remark not in (-1, 0, 1):
            raise ValueError("remark must be -1, 0 or 1")
        _finite(self.hurt, "hurt", low=0.0)
        _finite(self.hours, "hours", low=0.0)
        _finite(self.memory_fill, "memory_fill", low=0.0, high=1.0)
        if (self.error_past is None) != (self.error_now is None):
            raise ValueError("error_past and error_now must be given together")
        if self.error_past is not None:
            _finite(self.error_past, "error_past")
            _finite(self.error_now, "error_now")


@dataclass(frozen=True)
class Feelings:
    """One step's feelings, already multiplied by their exchange rates.

    Good is positive, bad is negative. ``total`` is their sum and
    ``cost`` (LeCun's sign: lower is better) is minus the total.
    """

    curiosity: float
    underused_skill: float
    tiredness: float
    pain: float
    job_done: float
    remarks: float
    boredom: float
    bother: float

    @property
    def total(self):
        return math.fsum(getattr(self, name) for name in TERMS)

    @property
    def cost(self):
        return -self.total

    def as_dict(self):
        return {name: getattr(self, name) for name in TERMS}


class IntrinsicCostMeter:
    """The fixed meter. ``step`` is the only way to get a number out of it."""

    __slots__ = ("_rates", "_config", "_skill_counts", "_hours_awake", "_paid_jobs",
                 "_nice_size", "_progress_mean", "_asked")

    def __init__(self, rates=None, config=None):
        rates = ExchangeRates() if rates is None else rates
        config = MeterConfig() if config is None else config
        if type(rates) is not ExchangeRates:
            raise ValueError("rates must be an ExchangeRates table")
        if type(config) is not MeterConfig:
            raise ValueError("config must be a MeterConfig")
        self._rates = rates
        self._config = config
        self.reset()

    @property
    def rates(self):
        return self._rates

    @property
    def config(self):
        return self._config

    def reset(self):
        """Back to the state at birth: rested, nothing used, nothing paid."""
        self._skill_counts = {}
        self._hours_awake = 0.0
        self._paid_jobs = set()
        self._nice_size = 1.0
        self._progress_mean = self._config.boredom_floor
        self._asked = {}

    def step(self, observed):
        """Take what happened on one move; return what it felt like."""
        if type(observed) is not StepInput:
            raise ValueError("step takes a StepInput")
        rates, config = self._rates, self._config
        free_and_awake = not observed.job_open and not observed.asleep

        # Curiosity: how much better this move's result is predicted now than
        # by the past self. Signed and clipped the same on both sides, so
        # noise nobody can learn averages to zero and forgetting costs.
        progress = 0.0
        if observed.error_past is not None:
            progress = _clip((observed.error_past - observed.error_now) / config.curiosity_scale,
                             config.curiosity_clip)

        # Under-used skill: a kind used little lately pays more. Never negative.
        keep = _keep(config.skill_half_life)
        for kind in self._skill_counts:
            self._skill_counts[kind] *= keep
        skill_bonus = 0.0
        if observed.skill is not None:
            used = self._skill_counts.get(observed.skill, 0.0)
            skill_bonus = 1.0 / math.sqrt(1.0 + used)
            self._skill_counts[observed.skill] = used + 1.0

        # Tiredness: pressure from hours awake and a full day memory. It
        # builds whenever awake, job or no job, but only costs in free time.
        if observed.asleep:
            self._hours_awake = max(0.0, self._hours_awake - config.sleep_payback * observed.hours)
        else:
            self._hours_awake += observed.hours
        awake_share = min(1.0, self._hours_awake / config.hours_to_full)
        pressure = 1.0 - (1.0 - awake_share) * (1.0 - observed.memory_fill)
        tired = 0.0
        if free_and_awake and pressure > config.tired_onset:
            tired = ((pressure - config.tired_onset) / (1.0 - config.tired_onset)) ** 2 * observed.hours

        # Pain: never fades.
        hurt = min(observed.hurt, config.hurt_cap)

        # Job done: paid once per job, however often "done" is reported.
        done = 0.0
        if observed.job_done and observed.job_id not in self._paid_jobs:
            self._paid_jobs.add(observed.job_id)
            done = 1.0

        # Owner's remarks: "nice" fades when repeated and recovers with time;
        # "no" never fades.
        self._nice_size = 1.0 - (1.0 - self._nice_size) * _keep(config.nice_half_life)
        nice = no = 0.0
        if observed.remark == 1:
            nice = self._nice_size
            self._nice_size *= config.nice_fade
        elif observed.remark == -1:
            no = 1.0

        # PROPOSED boredom: free time in which nothing is being learned.
        bored = 0.0
        if free_and_awake:
            keep = _keep(config.boredom_half_life)
            self._progress_mean = keep * self._progress_mean + (1.0 - keep) * progress
            # Even on both sides of "no progress", so noise is exactly as
            # boring as sitting still and cannot be used to escape boredom.
            lack = 1.0 - self._progress_mean / config.boredom_floor
            bored = max(0.0, min(2.0, lack)) * observed.hours

        # PROPOSED bother: asking the owner costs, and asking again costs more.
        bother = 0.0
        if observed.asked_owner is not None:
            before = self._asked.get(observed.asked_owner, 0)
            self._asked[observed.asked_owner] = before + 1
            bother = min(1.0 + before, config.bother_cap)

        return Feelings(
            curiosity=rates.curiosity * progress,
            underused_skill=rates.underused_skill * skill_bonus,
            tiredness=-rates.tiredness * tired,
            pain=-rates.pain * hurt,
            job_done=rates.job_done * done,
            remarks=rates.nice * nice - rates.no * no,
            boredom=-rates.boredom * bored,
            bother=-rates.bother * bother,
        )
