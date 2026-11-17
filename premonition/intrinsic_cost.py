"""The fixed built-in sense of good and bad (the intrinsic cost meter).

This is the "feel good / feel bad" box of the LeCun-style layout. It is a
plain meter: events and measurements go in after each step, one number per
feeling and a total come out. It holds counters and fixed formulas only. It
has no learned weights and nothing here is ever trained, by day or in sleep.

The wanting does not live here. A learned critic predicts the discounted sum
of the total, and moves are picked from the critic's predictions. The model
has no handle on the meter: the harness owns it, ``step`` is the only call
that returns a number, ``step`` always advances the meter, and the meter
refuses to be copied or pickled. One meter lasts one life: it cannot be
reset, and the harness must not rebuild it between episodes.

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

# The supported range. No rate, no step length and no shape number may be
# above LARGEST, and no shape number below SMALLEST. Inside this range every
# feeling the meter returns is a finite number: a table such as pain = 1e308
# is refused when it is built, not turned into "minus infinity" later.
LARGEST = 1e6
SMALLEST = 1e-6


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
            _finite(getattr(self, name), f"rate {name}", low=0.0, high=LARGEST)


@dataclass(frozen=True)
class MeterConfig:
    """Shape numbers and closed lists. Fixed in the test file, never tuned in a test."""

    # curiosity: how many regions the held-out panel reports, and the
    # curiosity discount. 1.0 = plain "how much the panel error fell".
    panel_regions: int = 1
    curiosity_gamma: float = 1.0
    # under-used skill: the closed list of command kinds; recent-use counts
    # halve every skill_half_life free-play MOVES (steps without a move, and
    # every step with a job open, do not count).
    skill_kinds: Tuple[str, ...] = ("paint", "reshape", "turn", "go")
    skill_half_life: float = 50.0
    # tiredness: hours awake that fill the pressure, where it starts to cost,
    # and how many awake-hours one hour of sleep pays back.
    hours_to_full: float = 16.0
    tired_onset: float = 0.5
    sleep_payback: float = 2.0
    # pain: the top of the hurt scale. A larger hurt is refused, never cut
    # down: the harness rescales the world's hurt into 0..hurt_cap.
    hurt_cap: float = 10.0
    # owner's "nice": each one multiplies the next by nice_fade; the size
    # recovers halfway to full every nice_half_life HOURS on the clock.
    nice_fade: float = 0.5
    nice_half_life: float = 10.0
    # PROPOSED boredom: the pool of fresh learning halves every
    # boredom_half_life HOURS of free time; below boredom_floor it is boring.
    boredom_half_life: float = 2.0
    boredom_floor: float = 0.02
    # PROPOSED bother: the closed list of question ids, and the most counted
    # for one question to the owner.
    question_ids: Tuple[str, ...] = ()
    bother_cap: float = 5.0
    # step length: the shortest and longest AWAKE step the meter accepts, in
    # clock hours. Off (None) by default; each registered test file sets both
    # (one alone is refused). With the limits set, a world that forgets its
    # clock is refused instead of silently switching tiredness off: an awake
    # step below the shortest step, and a sleep step of 0 hours. Sleep steps
    # are otherwise not limited (their sums are exact at any length).
    min_awake_step_hours: Optional[float] = None
    max_awake_step_hours: Optional[float] = None

    def __post_init__(self):
        if type(self.panel_regions) is not int or not 1 <= self.panel_regions <= LARGEST:
            raise ValueError(f"panel_regions must be a whole number from 1 to {LARGEST:g}")
        if not 0 < _finite(self.curiosity_gamma, "curiosity_gamma") <= 1:
            raise ValueError("curiosity_gamma must be within 0..1 (0 excluded)")
        _names(self.skill_kinds, "skill_kinds")
        _names(self.question_ids, "question_ids")
        for name in ("skill_half_life", "hours_to_full", "sleep_payback", "hurt_cap",
                     "nice_half_life", "boredom_half_life", "boredom_floor", "bother_cap"):
            _finite(getattr(self, name), name, low=SMALLEST, high=LARGEST)
        if not 0 <= _finite(self.tired_onset, "tired_onset") < 1:
            raise ValueError("tired_onset must be within 0..1 (1 excluded)")
        if not 0 < _finite(self.nice_fade, "nice_fade") <= 1:
            raise ValueError("nice_fade must be within 0..1 (0 excluded)")
        for name in ("min_awake_step_hours", "max_awake_step_hours"):
            if getattr(self, name) is not None:
                _finite(getattr(self, name), name, low=SMALLEST, high=LARGEST)
        if (self.min_awake_step_hours is None) != (self.max_awake_step_hours is None):
            raise ValueError("set both step-length limits or neither")
        if self.min_awake_step_hours is not None and self.min_awake_step_hours > self.max_awake_step_hours:
            raise ValueError("min_awake_step_hours must not be above max_awake_step_hours")


@dataclass(frozen=True)
class StepInput:
    """What the world and the harness report after one step. Never model outputs.

    job_open     the owner has given a job that is not finished or dropped.
    job_id       the harness's name for that job (given exactly when open).
    job_done     the world says the open job's goal is reached on this step.
    hurt         how much the world says this step hurt, on the fixed scale
                 0..hurt_cap (0 = not at all). More than hurt_cap is refused.
    remark       the owner said "nice" (+1), "no" (-1) or nothing (0).
    panel_error  the world model's error rate (0..1) on each region of the
                 fixed held-out panel, measured after this step's training.
                 It is a share of panel items: predicted wrong (exact match)
                 or, for continuous predictions, off by more than a tolerance
                 fixed before the run. Never a rescaled loss. Same items, same
                 order, no sampling noise. None on steps where the panel was
                 not evaluated.
    skill        kind of command used (None = no move was made). With a job
                 open it is checked against the closed list and otherwise
                 ignored: the skill feeling works in free play only.
    hours        clock time this step took, from the harness clock (at most
                 LARGEST hours in one step).
    memory_fill  how full the day memory is at the start of the step, 0..1,
                 taken as constant through the step. It must not be higher
                 than at the start of a sleep step just before it.
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
        _finite(self.hours, "hours", low=0.0, high=LARGEST)
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
                 "_nice_size", "_knowledge", "_record", "_fresh", "_asked", "_fill_limit")

    def __init__(self, rates=None, config=None):
        rates = ExchangeRates() if rates is None else rates
        config = MeterConfig() if config is None else config
        if type(rates) is not ExchangeRates:
            raise ValueError("rates must be an ExchangeRates table")
        if type(config) is not MeterConfig:
            raise ValueError("config must be a MeterConfig")
        self._rates = rates
        self._config = config
        # The state at birth: rested, nothing used, nothing paid. There is
        # no way back to it: every "per life" bound rests on that.
        self._skill_counts = dict.fromkeys(config.skill_kinds, 0.0)
        self._hours_awake = 0.0
        self._seen_jobs = set()
        self._paid_jobs = set()
        self._nice_size = 1.0
        self._knowledge = None  # last panel reading, as knowledge
        self._record = None  # best knowledge so far
        self._fresh = config.boredom_floor  # pool of fresh learning
        self._asked = {}
        self._fill_limit = 1.0  # most the next step's fill may be (lower right after sleep)

    @property
    def rates(self):
        return self._rates

    @property
    def config(self):
        return self._config

    def _no_copies(self, *args, **kwargs):
        raise TypeError("the meter cannot be copied or pickled: a copy could be asked 'what if'")

    __copy__ = __deepcopy__ = __reduce__ = __reduce_ex__ = _no_copies

    def _variety(self):
        """How evenly the command kinds were used lately, 0..1 (entropy)."""
        counts = [count for count in self._skill_counts.values() if count > 0.0]
        if len(counts) < 2:
            return 0.0
        whole = math.fsum(counts)
        # A share too small to tell from zero adds nothing (0 x log 0 = 0).
        shares = [share for share in (count / whole for count in counts) if share > 0.0]
        return -math.fsum(share * math.log(share) for share in shares) / math.log(len(self._skill_counts))

    def _tired_cost(self, start, end, fill):
        """Exact tiredness cost of being awake from hour ``start`` to ``end``."""
        config = self._config
        full, onset = config.hours_to_full, config.tired_onset
        cost = max(0.0, end - max(start, full))  # at full pressure: 1 per hour

        def level(hour):
            return min(1.0, max(0.0, (fill + (1.0 - fill) * hour / full - onset) / (1.0 - onset)))

        # Below full pressure the level is a straight line once past the
        # onset, so its square sums to hours x (a*a + a*b + b*b) / 3.
        begins = full * (onset - fill) / (1.0 - fill) if fill < onset else 0.0
        low, high = max(start, begins), min(end, full)
        if high > low:
            a, b = level(low), level(high)
            cost += (high - low) * (a * a + a * b + b * b) / 3.0
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
        if observed.hurt > config.hurt_cap:
            raise ValueError(f"hurt must be at most {config.hurt_cap}: rescale it, do not cut it or drop it")
        if observed.job_done and observed.job_id not in self._seen_jobs:
            raise ValueError("a job must be announced open in an earlier step before it can be done")
        if observed.memory_fill > self._fill_limit:
            raise ValueError("memory_fill must not rise during sleep: this step starts fuller than the "
                             "sleep step before it started")
        shortest, longest = config.min_awake_step_hours, config.max_awake_step_hours
        if observed.asleep:
            if shortest is not None and observed.hours <= 0.0:
                raise ValueError("a sleep step must take some time: the world must report its clock")
        else:
            if shortest is not None and observed.hours < shortest:
                raise ValueError(f"an awake step must take at least {shortest} hours: the world must report its clock")
            if longest is not None and observed.hours > longest:
                raise ValueError(f"an awake step must take at most {longest} hours: cut it into shorter steps")

    def step(self, observed):
        """Take what happened on one step; return what it felt like."""
        self._check(observed)  # a refused step changes nothing
        rates, config = self._rates, self._config
        free_and_awake = not observed.job_open and not observed.asleep

        # Curiosity: the change in knowledge on the fixed held-out panel since
        # the last reading. Knowledge = regions minus the summed error rates.
        # Differences are never clipped, so what is paid over any stretch is
        # exactly knowledge-at-the-end minus knowledge-at-the-start. The last
        # reading is kept across sleep: what sleep did to the panel is paid or
        # charged on waking.
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
        # Free play only: while a job is open the counts are frozen (no use
        # counted, no decay, nothing paid), so a job can neither earn the
        # bonus nor be charged for using one kind of command.
        variety = 0.0
        if observed.skill is not None and not observed.job_open:
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
        # The fill is read at the start of a step and sleep must not raise it,
        # so the step after a sleep step may not start fuller than it did.
        self._fill_limit = observed.memory_fill if observed.asleep else 1.0

        # Pain: never fades. Hurt above the scale was refused, not cut down.
        hurt = observed.hurt

        # Job done: paid once per job, and only for a job announced earlier.
        done = 0.0
        if observed.job_done and observed.job_id not in self._paid_jobs:
            self._paid_jobs.add(observed.job_id)
            done = 1.0
        if observed.job_open:
            self._seen_jobs.add(observed.job_id)

        # Owner's remarks: "nice" fades when repeated and recovers with
        # clock hours (not steps); "no" never fades. A remark counts at the
        # end of its step: the step's own hours of recovery come first.
        self._nice_size = 1.0 - (1.0 - self._nice_size) * 0.5 ** (observed.hours / config.nice_half_life)
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
