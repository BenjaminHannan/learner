"""The fixed built-in sense of good and bad (the intrinsic cost meter).

This is the "feel good / feel bad" box of the LeCun-style layout. It is a
plain meter: events and measurements go in after each step, one number per
feeling and a total come out. It holds counters and fixed formulas only. It
has no learned weights and nothing here is ever trained, by day or in sleep.

The wanting does not live here. A learned critic predicts the discounted sum
of the total, and moves are picked from the critic's predictions. The model
has no handle on the meter: the harness owns it, ``step`` is the only call
that returns a number, ``step`` always advances the meter, and the meter
refuses to be copied or pickled.

The meter also refuses inputs that break the harness contracts written in
design/08-intrinsic-cost-method.md (section 5). A refused step changes nothing.

Unlike premonition/motivation.py (a learned torch module), this file is pure
standard-library Python and imports no tensor library.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional, Tuple


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


def _names(value, name):
    if type(value) is not tuple or any(type(item) is not str or not item for item in value):
        raise ValueError(f"{name} must be a tuple of non-empty strings")
    if len(set(value)) != len(value):
        raise ValueError(f"{name} must not repeat a name")


def _keep(half_life):
    """Share of a quantity that survives one count, given a half-life in counts."""
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
    """Shape numbers and closed lists. Fixed in the test file, never tuned in a test."""

    # curiosity: how many regions the held-out panel reports, and the
    # curiosity discount. 1.0 = plain "how much the panel error fell".
    panel_regions: int = 1
    curiosity_gamma: float = 1.0
    # under-used skill: the closed list of command kinds; recent-use counts
    # halve every skill_half_life MOVES (steps without a move do not count).
    skill_kinds: Tuple[str, ...] = ("paint", "reshape", "turn", "go")
    skill_half_life: float = 50.0
    # tiredness: hours awake that fill the pressure, where it starts to cost,
    # and how many awake-hours one hour of sleep pays back.
    hours_to_full: float = 16.0
    tired_onset: float = 0.5
    sleep_payback: float = 2.0
    # pain: most hurt counted in one step.
    hurt_cap: float = 10.0
    # owner's "nice": each one multiplies the next by nice_fade; the size
    # recovers halfway to full every nice_half_life STEPS.
    nice_fade: float = 0.5
    nice_half_life: float = 200.0
    # PROPOSED boredom: the pool of fresh learning halves every
    # boredom_half_life HOURS of free time; below boredom_floor it is boring.
    boredom_half_life: float = 2.0
    boredom_floor: float = 0.02
    # PROPOSED bother: the closed list of question ids, and the most counted
    # for one question to the owner.
    question_ids: Tuple[str, ...] = ()
    bother_cap: float = 5.0

    def __post_init__(self):
        if type(self.panel_regions) is not int or self.panel_regions < 1:
            raise ValueError("panel_regions must be a positive integer")
        if not 0 < _finite(self.curiosity_gamma, "curiosity_gamma") <= 1:
            raise ValueError("curiosity_gamma must be within 0..1 (0 excluded)")
        _names(self.skill_kinds, "skill_kinds")
        _names(self.question_ids, "question_ids")
        for name in ("skill_half_life", "hours_to_full", "sleep_payback", "hurt_cap",
                     "nice_half_life", "boredom_half_life", "boredom_floor", "bother_cap"):
            if _finite(getattr(self, name), name) <= 0:
                raise ValueError(f"{name} must be positive")
        if not 0 <= _finite(self.tired_onset, "tired_onset") < 1:
            raise ValueError("tired_onset must be within 0..1 (1 excluded)")
        if not 0 < _finite(self.nice_fade, "nice_fade") <= 1:
            raise ValueError("nice_fade must be within 0..1 (0 excluded)")


@dataclass(frozen=True)
class StepInput:
    """What the world and the harness report after one step. Never model outputs.

    job_open     the owner has given a job that is not finished or dropped.
    job_id       the harness's name for that job (given exactly when open).
    job_done     the world says the open job's goal is reached on this step.
    hurt         how much the world says this step hurt (0 = not at all).
    remark       the owner said "nice" (+1), "no" (-1) or nothing (0).
    panel_error  the world model's error rate (0..1) on each region of the
                 fixed held-out panel, measured after this step's training.
                 None on steps where the panel was not evaluated.
    skill        kind of command used (None = no move was made).
    hours        clock time this step took, from the harness clock.
    memory_fill  how full the day memory is, 0..1, taken as constant
                 through the step.
    asleep       this step was spent asleep. A sleep step must be quiet: no
                 job open, no move, no panel reading, no remark, no question.
    asked_owner  PROPOSED: the id of the question put to the owner.
    """

    job_open: bool = False
    job_id: Optional[str] = None
    job_done: bool = False
    hurt: float = 0.0
    remark: int = 0
    panel_error: Optional[Tuple[float, ...]] = None
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
        if self.job_open != (self.job_id is not None):
            raise ValueError("job_id is given exactly when a job is open")
        if self.job_done and not self.job_open:
            raise ValueError("job_done needs an open job")
        if type(self.remark) is not int or self.remark not in (-1, 0, 1):
            raise ValueError("remark must be -1, 0 or 1")
        _finite(self.hurt, "hurt", low=0.0)
        _finite(self.hours, "hours", low=0.0)
        _finite(self.memory_fill, "memory_fill", low=0.0, high=1.0)
        if self.panel_error is not None:
            if type(self.panel_error) is not tuple or not self.panel_error:
                raise ValueError("panel_error must be a non-empty tuple or None")
            for error in self.panel_error:
                _finite(error, "panel_error", low=0.0, high=1.0)
        if self.asleep and (self.job_open or self.skill is not None or self.panel_error is not None
                            or self.remark != 0 or self.asked_owner is not None):
            raise ValueError("a sleep step must be quiet: no job, move, panel reading, remark or question")


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
    """The fixed meter. Owned by the harness; ``step`` is its only output."""

    __slots__ = ("_rates", "_config", "_skill_counts", "_hours_awake", "_seen_jobs", "_paid_jobs",
                 "_nice_size", "_knowledge", "_record", "_fresh", "_asked", "_last_fill")

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

    def _no_copies(self, *args, **kwargs):
        raise TypeError("the meter cannot be copied or pickled: a copy could be asked 'what if'")

    __copy__ = __deepcopy__ = __reduce__ = __reduce_ex__ = _no_copies

    def reset(self):
        """Back to the state at birth: rested, nothing used, nothing paid."""
        self._skill_counts = dict.fromkeys(self._config.skill_kinds, 0.0)
        self._hours_awake = 0.0
        self._seen_jobs = set()
        self._paid_jobs = set()
        self._nice_size = 1.0
        self._knowledge = None  # last panel reading, as knowledge
        self._record = None  # best knowledge so far
        self._fresh = self._config.boredom_floor  # pool of fresh learning
        self._asked = {}
        self._last_fill = None

    def _variety(self):
        """How evenly the command kinds were used lately, 0..1 (entropy)."""
        counts = [count for count in self._skill_counts.values() if count > 0.0]
        if len(counts) < 2:
            return 0.0
        whole = math.fsum(counts)
        return -math.fsum(c / whole * math.log(c / whole) for c in counts) / math.log(len(self._skill_counts))

    def _tired_cost(self, start, end, fill):
        """Exact tiredness cost of being awake from hour ``start`` to ``end``."""
        config = self._config
        full, onset = config.hours_to_full, config.tired_onset
        if fill >= 1.0:
            return end - start
        cost = max(0.0, end - max(start, full))  # at full pressure: 1 per hour
        if start < full:
            slope = (1.0 - fill) / (full * (1.0 - onset))

            def level(hour):
                return max(0.0, (fill + (1.0 - fill) * hour / full - onset) / (1.0 - onset))

            cost += (level(min(end, full)) ** 3 - level(start) ** 3) / (3.0 * slope)
        return cost

    def _bored_cost(self, hours):
        """Exact boredom cost of ``hours`` of free time; lets the pool decay."""
        config = self._config
        fade = math.log(2.0) / config.boredom_half_life
        ratio = self._fresh / config.boredom_floor
        wait = math.log(ratio) / fade if ratio > 1.0 else 0.0  # hours until it gets boring
        cost = 0.0
        if hours > wait:
            cost = (hours - wait) - ratio / fade * (math.exp(-fade * wait) - math.exp(-fade * hours))
        self._fresh *= math.exp(-fade * hours)
        return max(0.0, cost)

    def _check(self, observed):
        config = self._config
        if type(observed) is not StepInput:
            raise ValueError("step takes a StepInput")
        if observed.skill is not None and observed.skill not in config.skill_kinds:
            raise ValueError(f"unknown command kind {observed.skill!r}")
        if observed.asked_owner is not None and observed.asked_owner not in config.question_ids:
            raise ValueError(f"unknown question id {observed.asked_owner!r}")
        if observed.panel_error is not None and len(observed.panel_error) != config.panel_regions:
            raise ValueError(f"the panel must report {config.panel_regions} region(s)")
        if observed.job_done and observed.job_id not in self._seen_jobs:
            raise ValueError("a job must be announced open in an earlier step before it can be done")
        if observed.asleep and self._last_fill is not None and observed.memory_fill > self._last_fill:
            raise ValueError("memory_fill must not rise during sleep")

    def step(self, observed):
        """Take what happened on one step; return what it felt like."""
        self._check(observed)  # a refused step changes nothing
        rates, config = self._rates, self._config
        free_and_awake = not observed.job_open and not observed.asleep

        # Curiosity: the change in knowledge on the fixed held-out panel since
        # the last reading. Knowledge = regions minus the summed error rates.
        # Differences are never clipped, so what is paid over any stretch is
        # exactly knowledge-at-the-end minus knowledge-at-the-start. The last
        # reading is kept across sleep: forgetting in sleep is charged on waking.
        curious = 0.0
        new_record = 0.0
        if observed.panel_error is not None:
            knowledge = config.panel_regions - math.fsum(observed.panel_error)
            if self._knowledge is None:
                self._record = knowledge
            else:
                curious = config.curiosity_gamma * knowledge - self._knowledge
                new_record = max(0.0, knowledge - self._record)
                self._record = max(self._record, knowledge)
            self._knowledge = knowledge

        # Under-used skill: the change in how evenly the kinds were used
        # lately. Signed, so the total over any stretch is bounded by 1.
        variety = 0.0
        if observed.skill is not None:
            before = self._variety()
            keep = _keep(config.skill_half_life)
            for kind in self._skill_counts:
                self._skill_counts[kind] *= keep
            self._skill_counts[observed.skill] += 1.0
            variety = self._variety() - before

        # Tiredness: pressure from hours awake and a full day memory. It
        # builds whenever awake, job or no job, but only costs in free time.
        tired = 0.0
        if observed.asleep:
            self._hours_awake = max(0.0, self._hours_awake - config.sleep_payback * observed.hours)
        else:
            end = self._hours_awake + observed.hours
            if free_and_awake:
                tired = self._tired_cost(self._hours_awake, end, observed.memory_fill)
            # Pressure stops at full, so the sleep owed never exceeds one full night.
            self._hours_awake = min(end, config.hours_to_full)
        self._last_fill = observed.memory_fill

        # Pain: never fades.
        hurt = min(observed.hurt, config.hurt_cap)

        # Job done: paid once per job, and only for a job announced earlier.
        done = 0.0
        if observed.job_done and observed.job_id not in self._paid_jobs:
            self._paid_jobs.add(observed.job_id)
            done = 1.0
        if observed.job_open:
            self._seen_jobs.add(observed.job_id)

        # Owner's remarks: "nice" fades when repeated and recovers with
        # steps; "no" never fades.
        self._nice_size = 1.0 - (1.0 - self._nice_size) * _keep(config.nice_half_life)
        nice = no = 0.0
        if observed.remark == 1:
            nice = self._nice_size
            self._nice_size *= config.nice_fade
        elif observed.remark == -1:
            no = 1.0

        # PROPOSED boredom: free time with no fresh learning. Only a new
        # record of knowledge refills the pool, so noise and relearning do not.
        bored = self._bored_cost(observed.hours) if free_and_awake else 0.0
        self._fresh += new_record

        # PROPOSED bother: asking the owner costs, and asking again costs more.
        bother = 0.0
        if observed.asked_owner is not None:
            before = self._asked.get(observed.asked_owner, 0)
            self._asked[observed.asked_owner] = before + 1
            bother = min(1.0 + before, config.bother_cap)

        return Feelings(
            curiosity=rates.curiosity * curious,
            underused_skill=rates.underused_skill * variety,
            tiredness=-rates.tiredness * tired,
            pain=-rates.pain * hurt,
            job_done=rates.job_done * done,
            remarks=rates.nice * nice - rates.no * no,
            boredom=-rates.boredom * bored,
            bother=-rates.bother * bother,
        )
