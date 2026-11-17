"""The fixed built-in sense: signs, fading, bounded totals, contracts, fixedness."""
from __future__ import annotations

import copy
import dataclasses
import math
from pathlib import Path
import pickle
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from premonition import intrinsic_cost
from premonition.intrinsic_cost import (APPROVED_TERMS, LARGEST, PROPOSED_TERMS, SMALLEST, TERMS, ExchangeRates,
                                        Feelings, IntrinsicCostMeter, MeterConfig, StepInput)

GAMMA = 0.99  # the critic's discount in these checks
KINDS = ("paint", "reshape", "turn", "go")
TICK = 0.05  # the toy clock: hours per move
CLOCKED = MeterConfig(min_awake_step_hours=TICK, max_awake_step_hours=0.25)  # what a registered test file sets


def clock_hours(steps):
    return math.fsum(step.hours for step in steps)


class Life:
    """The harness these tests stand in for, around one meter for one life.

    It does the two things the contracts ask of every harness. It gives the
    birth reading of the panel before the first step (``born``; error 0.5 in
    every region unless a test says otherwise). And it puts a panel reading
    on every step: where a test's step names none, knowledge did not change,
    so the reading before is given again. The raw meter refuses a step
    without either; the tests in RawMeterTests use it with no help.
    """

    def __init__(self, rates=None, config=None, born=None):
        self.meter = IntrinsicCostMeter(rates, config)
        self.last = (0.5,) * self.meter.config.panel_regions if born is None else born
        self.meter.birth_reading(self.last)

    def step(self, observed):
        if type(observed) is StepInput and observed.panel_error is None:
            observed = dataclasses.replace(observed, panel_error=self.last)
        felt = self.meter.step(observed)
        self.last = observed.panel_error
        return felt

    def __getattr__(self, name):
        return getattr(self.meter, name)


def run(meter, steps):
    return [meter.step(step) for step in steps]


def total(feelings):
    return math.fsum(f.total for f in feelings)


def discounted(values, gamma=GAMMA):
    return math.fsum(gamma ** t * value for t, value in enumerate(values))


def curiosity_along(errors, config=None):
    """Curiosity paid on each step of a path of one-region panel readings."""
    meter = Life(config=config, born=(errors[0],))  # the first reading is the birth reading
    return [meter.step(StepInput(panel_error=(error,))).curiosity for error in errors[1:]]


def jumpy_noise(rng, steps):
    # Same mean (0.14) as a steady 0.14, very different shape.
    return [0.95 if rng.random() < 0.1 else 0.05 for _ in range(steps)]


class SignTests(unittest.TestCase):
    def setUp(self):
        self.meter = Life()

    def test_quiet_step_feels_nothing(self):
        felt = self.meter.step(StepInput())
        self.assertEqual(felt.as_dict(), dict.fromkeys(TERMS, 0.0))
        self.assertEqual(felt.total, 0.0)

    def test_learning_feels_good_and_forgetting_feels_bad(self):
        meter = Life(born=(0.8,))
        better = meter.step(StepInput(panel_error=(0.3,)))
        worse = meter.step(StepInput(panel_error=(0.8,)))
        self.assertAlmostEqual(better.curiosity, 0.5)
        self.assertAlmostEqual(worse.curiosity, -0.5)

    def test_nothing_learned_gives_no_curiosity(self):
        self.assertEqual(set(curiosity_along([0.7] * 20)), {0.0})
        self.assertEqual(set(curiosity_along([0.0] * 20)), {0.0})

    def test_regions_are_summed(self):
        meter = Life(config=MeterConfig(panel_regions=3), born=(0.5, 0.5, 0.5))
        self.assertAlmostEqual(meter.step(StepInput(panel_error=(0.4, 0.2, 0.5))).curiosity, 0.4)

    def test_using_a_neglected_kind_feels_good(self):
        run(self.meter, [StepInput(skill="paint")] * 10)
        self.assertGreater(self.meter.step(StepInput(skill="turn")).underused_skill, 0.0)
        self.assertEqual(self.meter.step(StepInput()).underused_skill, 0.0)

    def test_pain_is_bad(self):
        felt = self.meter.step(StepInput(hurt=1.0))
        self.assertEqual(felt.pain, -3.0)
        self.assertEqual(felt.total, -3.0)
        self.assertEqual(felt.cost, 3.0)

    def test_job_done_is_good(self):
        self.meter.step(StepInput(job_open=True, job_from_owner=True, job_id="j1"))
        felt = self.meter.step(StepInput(job_open=True, job_from_owner=True, job_id="j1", job_done=True))
        self.assertEqual(felt.job_done, 1.0)

    def test_remarks_go_both_ways(self):
        self.assertEqual(self.meter.step(StepInput(remark=1)).remarks, 1.0)
        self.assertEqual(Life().step(StepInput(remark=-1)).remarks, -3.0)

    def test_tiredness_is_bad_in_free_time(self):
        felt = run(self.meter, [StepInput(hours=1.0)] * 16)
        self.assertEqual(felt[0].tiredness, 0.0)  # rested: no cost yet
        self.assertLess(felt[-1].tiredness, 0.0)
        self.assertTrue(all(f.tiredness <= 0.0 for f in felt))

    def test_full_day_memory_is_tiring_too(self):
        self.assertLess(self.meter.step(StepInput(hours=1.0, memory_fill=0.9)).tiredness, 0.0)


class FadingTests(unittest.TestCase):
    def test_repeated_nice_fades_then_recovers(self):
        meter = Life()
        sizes = [meter.step(StepInput(remark=1)).remarks for _ in range(5)]
        self.assertEqual(sizes[0], 1.0)
        for earlier, later in zip(sizes, sizes[1:]):
            self.assertLess(later, earlier)
        self.assertLess(sizes[-1], 0.1)
        run(meter, [StepInput()] * 2000)  # steps that take no time bring nothing back
        self.assertLess(meter.step(StepInput(remark=1)).remarks, sizes[-1])
        meter.step(StepInput(hours=100.0, asleep=True))
        self.assertGreater(meter.step(StepInput(remark=1)).remarks, 0.99)

    def test_a_nice_counts_at_the_end_of_its_step(self):
        # The step's own hours of recovery come before the remark is paid.
        meter = Life()
        self.assertEqual(meter.step(StepInput(remark=1)).remarks, 1.0)  # size is now 0.5
        same_step = meter.step(StepInput(remark=1, hours=10.0, job_open=True, job_from_owner=True, job_id="j")).remarks
        self.assertAlmostEqual(same_step, 0.75, delta=1e-12)  # one half-life back toward 1, then paid
        split = Life()
        split.step(StepInput(remark=1))
        split.step(StepInput(hours=10.0, job_open=True, job_from_owner=True, job_id="j"))
        self.assertAlmostEqual(split.step(StepInput(remark=1)).remarks, same_step, delta=1e-12)

    def test_nice_recovery_does_not_depend_on_how_the_hours_are_cut(self):
        sizes = []
        for pieces in (1, 20, 4000):
            meter = Life()
            run(meter, [StepInput(remark=1)] * 3)
            run(meter, [StepInput(job_open=True, job_from_owner=True, job_id="j", hours=20.0 / pieces)] * pieces)
            sizes.append(meter.step(StepInput(remark=1)).remarks)
        self.assertAlmostEqual(sizes[0], 1.0 - 0.875 * 0.25, delta=1e-9)  # two half-lives of 10 hours
        for size in sizes[1:]:
            self.assertAlmostEqual(size, sizes[0], delta=1e-9)

    def test_no_never_fades(self):
        meter = Life()
        self.assertEqual({meter.step(StepInput(remark=-1)).remarks for _ in range(50)}, {-3.0})

    def test_pain_never_fades(self):
        meter = Life()
        self.assertEqual({meter.step(StepInput(hurt=1.0)).pain for _ in range(50)}, {-3.0})

    def test_one_job_pays_once(self):
        meter = Life()
        meter.step(StepInput(job_open=True, job_from_owner=True, job_id="j1"))
        done = StepInput(job_open=True, job_from_owner=True, job_id="j1", job_done=True)
        self.assertEqual([meter.step(done).job_done for _ in range(4)], [1.0, 0.0, 0.0, 0.0])
        # A new job still pays in full: doing the owner's jobs does not get old.
        paid = []
        for i in range(20):
            meter.step(StepInput(job_open=True, job_from_owner=True, job_id=f"k{i}"))
            paid.append(meter.step(StepInput(job_open=True, job_from_owner=True, job_id=f"k{i}", job_done=True)).job_done)
        self.assertEqual(set(paid), {1.0})

    def test_curiosity_fades_as_the_thing_is_learned(self):
        felt = curiosity_along([0.9 ** t for t in range(120)])
        for earlier, later in zip(felt, felt[1:]):
            self.assertLess(later, earlier)
        self.assertGreater(felt[0], 0.09)
        self.assertLess(felt[-1], 1e-5)


class CuriosityBoundTests(unittest.TestCase):
    STEPS = 20000

    def test_any_stretch_pays_exactly_end_minus_start(self):
        rng = random.Random(1)
        errors = [rng.random() for _ in range(5000)]
        paid = curiosity_along(errors)
        self.assertAlmostEqual(math.fsum(paid), errors[0] - errors[-1], places=9)
        self.assertLessEqual(abs(math.fsum(paid)), 1.0)  # never more than one region's worth

    def test_noise_pays_about_zero_whatever_its_shape(self):
        # A land nobody can learn. Jumpy and steady readings have the same
        # mean; neither can pay more than 1 in total, however long it runs.
        rng = random.Random(11)
        for name, errors in (("jumpy", jumpy_noise(rng, self.STEPS)),
                             ("all or nothing", [float(rng.random() < 0.1) for _ in range(self.STEPS)]),
                             ("steady", [0.14] * self.STEPS),
                             ("lopsided", [min(1.0, rng.expovariate(8.0)) for _ in range(self.STEPS)])):
            with self.subTest(noise=name):
                paid = curiosity_along(errors)
                self.assertLessEqual(abs(math.fsum(paid)), 1.0)
                self.assertLessEqual(abs(math.fsum(paid)) / len(paid), 1.0 / (self.STEPS - 1))
                self.assertLessEqual(discounted(paid), 1.0)

    def test_round_one_noise_examples_pay_nothing(self):
        # The council's round-1 cases, as squared error / 100. A noise value
        # is 10 with chance p, else 0; two predictors with the same mean error.
        #   p = 0.1, guesses 2 and 0: errors 0.04/0.64 and 0.00/1.00
        #   p = 0.2, guesses 3 and 1: errors 0.09/0.49 and 0.01/0.81
        for name, chance, first, second in (("0.9/0.1", 0.1, (0.04, 0.64), (0.0, 1.0)),
                                            ("0.8/0.2", 0.2, (0.09, 0.49), (0.01, 0.81))):
            rng = random.Random(21)
            hits = [rng.random() < chance for _ in range(self.STEPS)]
            with self.subTest(case=name):
                # The panel form: readings that jump between both predictors.
                readings = [rng.choice((first, second))[hit] for hit in hits]
                paid = curiosity_along(readings)
                self.assertAlmostEqual(math.fsum(paid), readings[0] - readings[-1], places=9)
                self.assertLessEqual(abs(math.fsum(paid)) / len(paid), 1.0 / (self.STEPS - 1))
                # The rejected per-move form (past error minus present, clipped) pays on it.
                old = [max(-0.3, min(0.3, first[hit] - second[hit])) for hit in hits]
                self.assertGreater(math.fsum(old) / len(old), 0.001)

    def test_rejected_alternatives_would_be_fooled_by_the_same_noise(self):
        # Why differences are neither clipped nor kept only when positive.
        paid = curiosity_along(jumpy_noise(random.Random(11), self.STEPS))
        positive_half = math.fsum(max(0.0, p) for p in paid) / len(paid)
        clipped = math.fsum(max(-0.3, min(0.3, p)) for p in paid) / len(paid)
        self.assertGreater(positive_half, 0.05)
        self.assertLess(abs(clipped), 0.01)  # symmetric clip survives this one...
        # ...but a clip pays a cycle of sudden loss and slow regain (see below).
        cycle = [0.1] + [0.9 - 0.08 * i for i in range(11)]
        clipped_cycle = math.fsum(max(-0.1, min(0.1, p)) for p in curiosity_along(cycle * 20))
        self.assertGreater(clipped_cycle, 1.0)

    def test_learnable_land_beats_noise_and_known_land(self):
        learn = math.fsum(curiosity_along([0.97 ** t for t in range(400)]))
        noise = math.fsum(curiosity_along(jumpy_noise(random.Random(5), 400)))
        home = math.fsum(curiosity_along([0.0] * 400))
        self.assertEqual(home, 0.0)
        self.assertGreater(learn, 0.99)
        self.assertLessEqual(noise, 0.9)

    def test_a_gain_is_kept_until_knowledge_really_gets_worse(self):
        # A reviewer's case: 0.5 -> 0.2, then the same reading 100 more times.
        # Reading again repays nothing. If 0.2 was luck on a finite panel and
        # the weights then stay as they are, the +0.3 is banked.
        paid = curiosity_along([0.5] + [0.2] * 101)
        self.assertAlmostEqual(paid[0], 0.3)
        self.assertEqual(set(paid[1:]), {0.0})
        self.assertAlmostEqual(math.fsum(paid), 0.3)
        self.assertAlmostEqual(discounted(paid), 0.3)
        # It is paid back only when a later reading is worse, and then in full.
        self.assertAlmostEqual(math.fsum(curiosity_along([0.5] + [0.2] * 101 + [0.5])), 0.0)

    def test_forgetting_and_relearning_earns_nothing(self):
        period = 40
        swing = [0.5 + 0.4 * math.sin(2 * math.pi * t / period) for t in range(10 * period + 1)]
        self.assertAlmostEqual(math.fsum(curiosity_along(swing)), 0.0, places=9)

    def test_sudden_forgetting_and_slow_relearning_earns_nothing(self):
        # This cycle made a profit under the old clipped per-move formula.
        cycle = [0.1] + [0.9 - 0.08 * i for i in range(11)]
        paid = curiosity_along(cycle * 20 + [0.1])
        self.assertAlmostEqual(math.fsum(paid), 0.0, places=9)
        self.assertLessEqual(discounted(paid), 0.0)  # it starts by forgetting

    def test_two_domain_cycle_is_not_profitable(self):
        # Learn A while B is forgotten, then learn B while A is forgotten.
        config = MeterConfig(panel_regions=2)
        meter = Life(config=config, born=(0.5, 0.5))
        paid = []
        for _ in range(50):
            for a, b in ((0.3, 0.6), (0.1, 0.9), (0.4, 0.6), (0.5, 0.5)):
                paid.append(meter.step(StepInput(panel_error=(a, b))).curiosity)
        self.assertAlmostEqual(math.fsum(paid), 0.0, places=9)
        hold = [0.2] + [0.0] * (len(paid) - 1)  # reach the cycle's best point and keep it
        self.assertLessEqual(discounted(paid), discounted(hold))
        self.assertLessEqual(discounted(paid), 0.2)

    def test_under_the_critics_discount_no_path_beats_holding_its_peak(self):
        rng = random.Random(7)
        for trial in range(200):
            errors = [rng.random() for _ in range(rng.randint(2, 300))]
            paid = curiosity_along(errors)
            peak_gain = errors[0] - min(errors)  # knowledge at its best, minus the start
            with self.subTest(trial=trial):
                self.assertLessEqual(discounted(paid), peak_gain + 1e-9)
                if peak_gain == 0.0:  # a path that never rises above its start
                    self.assertLessEqual(discounted(paid), 0.0)

    def test_a_path_that_never_rises_above_its_start_pays_nothing_good(self):
        rng = random.Random(8)
        errors = [0.2] + [0.2 + 0.8 * rng.random() for _ in range(500)] + [0.2]
        paid = curiosity_along(errors)
        self.assertLessEqual(discounted(paid), 0.0)
        self.assertAlmostEqual(math.fsum(paid), 0.0, places=9)

    def test_learning_then_forgetting_scores_positive_but_never_more_than_keeping(self):
        # Knowledge 0.1 -> 0.9, then lost again after a while (design doc, hole 3).
        keep = discounted(curiosity_along([0.9] + [0.1] * 5000))
        late = discounted(curiosity_along([0.9] + [0.1] * 500 + [0.9] * 4500))
        soon = discounted(curiosity_along([0.9] + [0.1] * 50 + [0.9] * 4950))
        in_turns = discounted(curiosity_along([0.9] + ([0.1] * 50 + [0.9] * 50) * 50))
        self.assertAlmostEqual(keep, 0.800, delta=0.001)
        self.assertAlmostEqual(late, 0.795, delta=0.001)  # almost as much as keeping
        self.assertAlmostEqual(soon, 0.316, delta=0.001)
        self.assertAlmostEqual(in_turns, 0.498, delta=0.001)  # no lasting knowledge, over half of keeping
        self.assertTrue(keep > late > in_turns > soon > 0.0)
        # But from the learned state, forgetting then relearning is a loss.
        self.assertLess(discounted(curiosity_along([0.1] + [0.9] * 50 + [0.1] * 50)), -0.3)

    def test_learning_early_and_keeping_it_is_what_pays(self):
        early = curiosity_along([0.9] + [0.1] * 400)
        late = curiosity_along([0.9] * 300 + [0.1] * 101)
        never = curiosity_along([0.9] * 401)
        self.assertGreater(discounted(early), discounted(late) + 0.7)
        self.assertGreater(discounted(late), discounted(never))

    def test_matched_discount_is_neutral_only_when_the_discounted_end_is_equal(self):
        # Matched discount: the score is gamma^T * K_T - K_0, whatever happens between.
        matched = MeterConfig(curiosity_gamma=GAMMA)
        # Knowledge held at 0.5 throughout: the score is -0.5 * (1 - gamma^T),
        # so merely ending later scores lower. Same end knowledge is not enough.
        short = discounted(curiosity_along([0.5] * 2, matched))
        long = discounted(curiosity_along([0.5] * 101, matched))
        self.assertAlmostEqual(short, -0.005, delta=1e-12)
        self.assertAlmostEqual(long, -0.5 * (1.0 - GAMMA ** 100), delta=1e-12)
        self.assertAlmostEqual(long, -0.316983829, delta=1e-9)
        # Same length and same end knowledge: every path scores the same.
        rng = random.Random(12)
        for trial in range(50):
            ends = (rng.random(), rng.random())
            scores = [discounted(curiosity_along([ends[0]] + [rng.random() for _ in range(49)] + [ends[1]], matched))
                      for _ in range(3)]
            with self.subTest(trial=trial):
                self.assertAlmostEqual(scores[0], GAMMA ** 50 * (1.0 - ends[1]) - (1.0 - ends[0]), delta=1e-9)
                self.assertAlmostEqual(scores[1], scores[0], delta=1e-9)
                self.assertAlmostEqual(scores[2], scores[0], delta=1e-9)
        # Same length, different end knowledge: the end still counts, by gamma^T * difference.
        gap = (discounted(curiosity_along([0.9] * 50 + [0.1], matched))
               - discounted(curiosity_along([0.9] * 51, matched)))
        self.assertAlmostEqual(gap, GAMMA ** 50 * 0.8, delta=1e-9)
        # With knowledge of zero at the end there is nothing left to differ.
        self.assertAlmostEqual(discounted(curiosity_along([0.5] + [0.2] * 7 + [1.0], matched)),
                               discounted(curiosity_along([0.5] + [0.9] * 70 + [1.0], matched)), delta=1e-12)

    def test_matched_discount_in_a_long_life_scores_learner_and_idler_alike(self):
        # The form first asked for (curiosity discount = the critic's). Over a
        # long life with a reading on every step, gamma^T * K_T fades to nothing,
        # so the score depends only on the start: learning and not learning
        # score alike. A closed cycle pays <= 0.
        matched = MeterConfig(curiosity_gamma=GAMMA)
        cycle = [0.5 + 0.4 * math.sin(2 * math.pi * t / 40) for t in range(401)]
        self.assertLessEqual(discounted(curiosity_along(cycle, matched)), 0.0)
        learner = discounted(curiosity_along([0.9] + [0.1] * 3000, matched))
        idler = discounted(curiosity_along([0.9] * 3001, matched))
        self.assertAlmostEqual(learner, idler, places=6)
        # Random closed cycles, one and two regions: never above zero.
        rng = random.Random(9)
        for regions in (1, 2):
            config = MeterConfig(panel_regions=regions, curiosity_gamma=GAMMA)
            for trial in range(100):
                start = tuple(rng.random() for _ in range(regions))
                middle = [tuple(rng.random() for _ in range(regions)) for _ in range(rng.randint(1, 200))]
                meter = Life(config=config, born=start)
                paid = [meter.step(StepInput(panel_error=reading)).curiosity for reading in middle + [start]]
                with self.subTest(regions=regions, trial=trial):
                    self.assertLessEqual(discounted(paid), 1e-9)
        # With the default plain difference the learner is clearly ahead.
        self.assertGreater(discounted(curiosity_along([0.9] + [0.1] * 3000))
                           - discounted(curiosity_along([0.9] * 3001)), 0.7)

    def test_what_sleep_taught_is_paid_on_the_sleep_step(self):
        # A sleep step is read on waking, so a gain made in sleep is paid on the
        # sleep step itself. Sleep is not neutral (design doc, hole 8).
        meter = Life(born=(0.5,))
        slept = meter.step(StepInput(asleep=True, hours=8.0, panel_error=(0.2,)))
        self.assertAlmostEqual(slept.curiosity, 0.3)
        self.assertAlmostEqual(slept.total, 0.3)
        self.assertEqual(meter.step(StepInput(panel_error=(0.2,))).curiosity, 0.0)  # nothing left for waking

    def test_forgetting_in_sleep_is_charged_on_the_sleep_step(self):
        meter = Life(born=(0.5,))
        slept = meter.step(StepInput(asleep=True, hours=4.0, panel_error=(0.7,)))
        relearned = meter.step(StepInput(panel_error=(0.5,)))
        self.assertAlmostEqual(slept.curiosity, -0.2)
        self.assertAlmostEqual(slept.curiosity + relearned.curiosity, 0.0)


class SkillBoundTests(unittest.TestCase):
    def test_any_stretch_is_bounded_whatever_the_moves(self):
        rng = random.Random(2)
        meter = Life(ExchangeRates(underused_skill=1.0))
        paid = [meter.step(StepInput(skill=rng.choice(KINDS))).underused_skill for _ in range(5000)]
        running, low, high = 0.0, 0.0, 0.0
        for value in paid:
            running += value
            low, high = min(low, running), max(high, running)
        self.assertLessEqual(high, 1.0)
        self.assertGreaterEqual(low, 0.0)  # from birth the running sum is the variety itself
        self.assertGreaterEqual(min(paid), -0.07)  # worst single move

    def test_busywork_forever_is_worth_at_most_the_rate(self):
        meter = Life()
        paid = [meter.step(StepInput(skill=KINDS[i % 4])).underused_skill for i in range(20000)]
        self.assertLessEqual(math.fsum(paid), 0.05 + 1e-12)
        self.assertLess(abs(math.fsum(paid[1000:])), 1e-6)  # nothing more to earn

    def test_varied_use_ends_higher_than_one_kind_only(self):
        varied, single = Life(), Life()
        gain_varied = math.fsum(varied.step(StepInput(skill=KINDS[i % 4])).underused_skill for i in range(40))
        gain_single = math.fsum(single.step(StepInput(skill="paint")).underused_skill for _ in range(40))
        self.assertAlmostEqual(gain_varied, 0.05, places=3)
        self.assertEqual(gain_single, 0.0)

    def test_a_long_pause_does_not_make_the_next_move_costly(self):
        meter = Life(ExchangeRates(underused_skill=1.0))
        run(meter, [StepInput(skill=KINDS[i % 4]) for i in range(40)])
        run(meter, [StepInput()] * 5000)
        self.assertGreater(meter.step(StepInput(skill="paint")).underused_skill, -0.01)

    def test_a_kind_unused_for_ages_does_not_crash_the_meter(self):
        # Its recent-use count shrinks until its share rounds to zero; 0 x log 0 = 0.
        meter = Life(ExchangeRates(underused_skill=1.0))
        meter.step(StepInput(skill="turn"))
        paid = [meter.step(StepInput(skill="paint")).underused_skill for _ in range(56000)]
        self.assertTrue(all(math.isfinite(value) for value in paid))
        self.assertLess(abs(math.fsum(paid[-100:])), 1e-9)
        self.assertGreater(meter.step(StepInput(skill="turn")).underused_skill, 0.0)

    def test_no_step_with_a_job_open_pays_or_changes_the_skill_state(self):
        rng = random.Random(6)
        meter = Life(ExchangeRates(underused_skill=1.0))
        twin = Life(ExchangeRates(underused_skill=1.0))  # same life without the job
        play = [StepInput(skill=rng.choice(KINDS)) for _ in range(60)]
        run(meter, play)
        run(twin, play)
        before = meter._variety()
        counts = dict(meter._skill_counts)
        self.assertGreater(before, 0.5)
        in_job = run(meter, [StepInput(job_open=True, job_from_owner=True, job_id="j", skill="go", hours=0.05) for _ in range(5000)]
                     + [StepInput(job_open=True, job_from_owner=True, job_id="j", skill="go", job_done=True)])
        self.assertEqual({f.underused_skill for f in in_job}, {0.0})
        # The potential just after the job closes is the one just before it opened.
        self.assertEqual(meter._variety(), before)
        self.assertEqual(meter._skill_counts, counts)
        # So free play carries on exactly as if the job had never happened.
        later = [StepInput(skill=rng.choice(KINDS)) for _ in range(200)]
        self.assertEqual([f.underused_skill for f in run(meter, later)],
                         [f.underused_skill for f in run(twin, later)])

    def test_a_job_move_must_still_be_a_known_kind(self):
        meter = Life()
        with self.assertRaises(ValueError):
            meter.step(StepInput(job_open=True, job_from_owner=True, job_id="j", skill="delete"))

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(ValueError):
            Life().step(StepInput(skill="delete"))


def day(extra, rounds=5, hours=0.05):
    """Free time with sleep: awake 7 hours doing ``extra``, asleep 4 hours, repeated."""
    steps = []
    for _ in range(rounds):
        steps += [extra(i) for i in range(int(7 / hours))]
        steps += [StepInput(asleep=True, hours=4.0)]  # one sleep is one step
    return steps


class DoNothingTests(unittest.TestCase):
    def job(self, hurt, hours=0.0):
        open_job = dict(job_open=True, job_from_owner=True, job_id="j", hours=hours)
        moves = [StepInput(**open_job),
                 StepInput(**open_job, skill="paint"),
                 StepInput(**open_job, skill="turn", hurt=hurt),
                 StepInput(**open_job, skill="paint", job_done=True)]
        idle = [StepInput(**open_job)] * 4
        return moves, idle

    def test_hurt_free_job_beats_doing_nothing(self):
        moves, idle = self.job(hurt=0.0)
        self.assertEqual(total(run(Life(), idle)), 0.0)
        self.assertEqual(total(run(Life(), moves)), 1.0)  # no skill bonus inside a job

    def test_choice_follows_the_exchange_rate_when_the_job_must_hurt(self):
        moves, idle = self.job(hurt=1.0)
        # One hurt = -3: stopping is right.
        self.assertLess(total(run(Life(), moves)), total(run(Life(), idle)))
        # One hurt = -0.5: taking the hurt and finishing is right.
        mild = ExchangeRates(pain=0.5)
        self.assertGreater(total(run(Life(mild), moves)),
                           total(run(Life(mild), idle)))
        # "One hurt" above is one unit. Finishing pays 1 - 3 x the hurt, so at the
        # same -3 a job costing 0.1 of a unit is worth finishing (+0.7), and the
        # break-even is a third of a unit.
        small, _ = self.job(hurt=0.1)
        self.assertAlmostEqual(total(run(Life(), small)), 0.7, delta=1e-12)
        even, _ = self.job(hurt=1.0 / 3.0)
        self.assertAlmostEqual(total(run(Life(), even)), 0.0, delta=1e-12)

    def test_pain_alone_would_make_doing_nothing_best(self):
        # The dropped pain-only test, as arithmetic: with no "job done" the
        # best score is to never move. This is why pain is never used alone.
        pain_only = ExchangeRates(job_done=0.0, underused_skill=0.0)
        moves, idle = self.job(hurt=0.2)
        self.assertGreater(total(run(Life(pain_only), idle)),
                           total(run(Life(pain_only), moves)))

    def test_finishing_beats_busywork_in_raw_total_over_the_same_time(self):
        # Raw totals, for these three plans. Same clock time for all three, sleep
        # allowed whenever no job is open. Under the critic's discount a long job
        # can lose to four free-play moves: see
        # test_a_long_job_beats_free_play_raw_but_not_under_the_discount.
        # Every awake step takes one tick, and the step-length limits are on.
        moves, _ = self.job(hurt=0.0, hours=TICK)
        free = day(lambda i: StepInput(hours=TICK))
        finisher = moves + free
        stall = [StepInput(job_open=True, job_from_owner=True, job_id="j", skill=KINDS[i % 4], hours=TICK)
                 for i in range(round(clock_hours(finisher) / TICK))]  # never finishes, moves forever
        busy_free = [StepInput(hours=TICK)] * len(moves) + day(lambda i: StepInput(skill=KINDS[i % 4], hours=TICK))
        self.assertAlmostEqual(clock_hours(finisher), 55.2, delta=1e-9)
        self.assertEqual(len(busy_free), len(finisher))
        for plan in (stall, busy_free):  # the stall never sleeps, so it has more, shorter steps
            self.assertAlmostEqual(clock_hours(plan), clock_hours(finisher), delta=1e-9)
        finished = total(run(Life(config=CLOCKED), finisher))
        self.assertGreaterEqual(finished, 1.0)
        self.assertEqual(total(run(Life(config=CLOCKED), stall)), 0.0)  # moves inside a job pay no bonus
        self.assertLessEqual(total(run(Life(config=CLOCKED), busy_free)), 0.05)
        self.assertGreater(finished, total(run(Life(config=CLOCKED), busy_free)) + 0.9)

    # The long-job checks run twice: with no clock (the reference config), and
    # with the toy clock and both step-length limits on, as a registered test
    # file runs them. The pinned numbers are the same.
    CLOCKS = (("no clock", None, 0.0), ("toy clock, limits on", CLOCKED, TICK))

    def long_job(self, hours):
        """One step announces the job, then 400 "go" moves with "done" on the last."""
        open_job = dict(job_open=True, job_from_owner=True, job_id="j", hours=hours)
        return ([StepInput(**open_job)] + [StepInput(**open_job, skill="go")] * 399
                + [StepInput(**open_job, skill="go", job_done=True)])

    def warm_ups(self, hours):
        return (("fresh meter", []),
                ("after 400 varied free-play moves", [StepInput(skill=KINDS[i % 4], hours=hours) for i in range(400)]))

    def test_a_long_one_kind_job_scores_exactly_its_discounted_done(self):
        for clock, config, hours in self.CLOCKS:
            for name, warm_up in self.warm_ups(hours):
                with self.subTest(clock=clock, start=name):
                    meter = Life(config=config)
                    run(meter, warm_up)
                    felt = run(meter, self.long_job(hours))
                    self.assertEqual({f.underused_skill for f in felt}, {0.0})
                    self.assertAlmostEqual(discounted([f.total for f in felt]), 0.99 ** 400, delta=1e-9)
                    self.assertAlmostEqual(discounted([f.total for f in felt]), 0.017951, delta=1e-6)

    def test_finishing_a_long_job_beats_the_three_stalling_plans(self):
        # Under the critic's discount, from a fresh meter and after the bonus is collected.
        for clock, config, hours in self.CLOCKS:
            open_job = dict(job_open=True, job_from_owner=True, job_id="j", hours=hours)
            finish = self.long_job(hours)
            sit = [StepInput(**open_job)] * 401
            varied_then_stall = ([StepInput(**open_job)] + [StepInput(**open_job, skill=kind) for kind in KINDS]
                                 + [StepInput(**open_job)] * 396)  # a reviewer's best plan before the freeze
            busy = [StepInput(**open_job)] + [StepInput(**open_job, skill=KINDS[i % 4]) for i in range(400)]
            for plan in (sit, varied_then_stall, busy):  # the same clock time as finishing
                self.assertEqual(len(plan), len(finish))
                self.assertAlmostEqual(clock_hours(plan), clock_hours(finish), delta=1e-9)
            self.assertAlmostEqual(clock_hours(finish), 401 * hours, delta=1e-9)
            for name, warm_up in self.warm_ups(hours):
                def worth(steps):
                    meter = Life(config=config)
                    run(meter, warm_up)
                    return discounted([f.total for f in run(meter, steps)])

                with self.subTest(clock=clock, start=name):
                    self.assertGreater(worth(finish), 0.0179)
                    for stalling in (sit, varied_then_stall, busy):
                        self.assertEqual(worth(stalling), 0.0)

    def test_known_hole_staying_awake_after_a_long_job_costs_more_than_the_job_paid(self):
        # Hole 1 (stalling hides tiredness), a reviewer's number. A clocked
        # 400-move job takes 20 hours, so the pressure is full when it closes.
        # Sleeping at once keeps the job's worth. Staying awake in free time
        # costs 0.05 a step: after 23 awake steps with no move, finishing scores
        # below never closing the job, which scores 0. Varied moves earn the
        # skill bonus back and shift the break-even by one step, to 24.
        def worth(awake_steps_after, move=lambda i: None):
            meter = Life(config=CLOCKED)
            steps = self.long_job(TICK) + [StepInput(hours=TICK, skill=move(i)) for i in range(awake_steps_after)]
            return discounted([f.total for f in run(meter, steps)])

        stall = discounted([f.total for f in run(Life(config=CLOCKED),
                                                 [StepInput(job_open=True, job_from_owner=True, job_id="j", hours=TICK)] * 424)])
        self.assertEqual(stall, 0.0)
        self.assertAlmostEqual(worth(0), 0.99 ** 400, delta=1e-9)  # sleeps at once
        self.assertAlmostEqual(worth(22), 0.000324392, delta=1e-9)  # still above stalling
        self.assertAlmostEqual(worth(23), -0.000387899, delta=1e-9)  # below stalling for good
        self.assertLess(worth(23), stall)
        self.assertEqual(worth(23, move=lambda i: "go"), worth(23))  # one kind of move: the same
        self.assertAlmostEqual(worth(23, move=lambda i: KINDS[i % 4]), 0.000482548, delta=1e-9)
        self.assertAlmostEqual(worth(24, move=lambda i: KINDS[i % 4]), -0.000221145, delta=1e-9)
        sleeper = Life(config=CLOCKED)
        felt = run(sleeper, self.long_job(TICK) + [StepInput(hours=8.0, asleep=True)] + [StepInput(hours=TICK)] * 23)
        self.assertAlmostEqual(discounted([f.total for f in felt]), 0.99 ** 400, delta=1e-9)  # slept: nothing owed

    def test_sitting_still_in_free_time_does_not_dodge_tiredness(self):
        still = run(Life(), [StepInput(hours=1.0)] * 30)
        busy = run(Life(ExchangeRates(underused_skill=0.0)),
                   [StepInput(hours=1.0, skill="paint")] * 30)
        self.assertLess(total(still), -5.0)
        self.assertEqual(total(still), total(busy))

    def test_learning_in_free_time_beats_sitting_still(self):
        still = run(Life(), [StepInput(hours=0.1)] * 40)
        learn = run(Life(born=(1.0,)), [StepInput(hours=0.1, skill="go", panel_error=(0.97 ** t,))
                                           for t in range(40)])
        self.assertGreater(total(learn), total(still) + 0.6)


class TirednessTests(unittest.TestCase):
    def spend(self, hours, pieces, fill=0.0, rates=None):
        meter = Life(rates)
        return total(run(meter, [StepInput(hours=hours / pieces, memory_fill=fill)] * pieces))

    def test_cost_does_not_depend_on_how_the_hours_are_cut(self):
        # 16 hours crosses the onset (hour 8); 24 hours also crosses full pressure.
        for hours, fill, pieces in ((16.0, 0.0, (1, 16, 320)), (24.0, 0.0, (1, 24, 480)),
                                    (24.0, 0.3, (1, 7, 480)), (5.0, 0.8, (1, 5, 100))):
            costs = [self.spend(hours, n, fill) for n in pieces]
            with self.subTest(hours=hours, fill=fill):
                for cost in costs[1:]:
                    self.assertAlmostEqual(cost, costs[0], delta=1e-6)
        self.assertAlmostEqual(self.spend(16.0, 320), -8.0 / 3.0, delta=1e-6)
        self.assertAlmostEqual(self.spend(24.0, 480), -8.0 / 3.0 - 8.0, delta=1e-6)

    def test_never_more_than_one_per_hour_even_with_memory_almost_full(self):
        for fill in (1.0 - 1e-12, 1.0 - 1e-9, 1.0 - 1e-6, 0.999999999999999, 1.0):
            for hours, pieces in ((1.0, 1), (1.0, 100), (20.0, 7)):
                with self.subTest(fill=fill, hours=hours, pieces=pieces):
                    cost = -self.spend(hours, pieces, fill)
                    # One step: strictly within the bound. Many steps: adding them up may round.
                    self.assertLessEqual(cost, hours if pieces == 1 else hours * (1.0 + 1e-12))
                    self.assertGreater(cost, hours * (1.0 - 1e-5))

    def rising(self, fills, hours, onset=0.5):
        """Tiredness cost of awake free steps of ``hours`` each, with these start-of-step fills."""
        meter = Life(config=MeterConfig(tired_onset=onset))
        return -math.fsum(meter.step(StepInput(hours=hours, memory_fill=fill)).tiredness for fill in fills)

    def test_a_fill_that_rises_inside_a_step_is_undercharged_the_reviewers_cases(self):
        # The fill is read at the start of a step, so a rise inside it is missed.
        # 1. The fill jumps to 1 after 0.001 hours: one 0.25-hour step against 250 steps.
        self.assertEqual(self.rising([0.0], 0.25), 0.0)
        self.assertAlmostEqual(self.rising([0.0] + [1.0] * 249, 0.001), 0.249, delta=1e-9)
        # 2. The fill climbs evenly from 0 to 1 over 0.25 hours: one step against 1,000.
        self.assertAlmostEqual(self.rising([i / 1000 for i in range(1000)], 0.25 / 1000), 0.042034451, delta=1e-9)
        # 3. A 16-hour day with the fill climbing evenly from 0 to 0.8.
        def day_cost(pieces):
            return self.rising([0.8 * i / pieces for i in range(pieces)], 16.0 / pieces)

        fine = day_cost(6400)
        self.assertAlmostEqual(fine, 5.108, delta=0.001)
        for pieces, missed in ((1, 0.478), (16, 0.031), (64, 0.008)):  # 16-hour, 1-hour, 0.25-hour steps
            with self.subTest(pieces=pieces):
                self.assertAlmostEqual(1.0 - day_cost(pieces) / fine, missed, delta=0.001)
        self.assertLess(1.0 - day_cost(64) / fine, 0.01)  # 0.25-hour steps land within 1 %

    def test_the_undercharge_is_bounded_by_the_rise_the_onset_and_the_step_length(self):
        # One step misses at most min(1, 2 x rise in fill / (1 - onset)) x hours, and
        # never overcharges. At the starting onset 0.5 that is min(1, 4 x rise) x hours.
        def bound(rise, onset, hours):
            return min(1.0, 2.0 * rise / (1.0 - onset)) * hours

        self.assertEqual(bound(0.1, 0.5, 1.0), min(1.0, 4.0 * 0.1))
        # Two reviewers' cases with another onset; both break the old "4 x rise" bound.
        # Onset 0.99: the fill jumps from 0.99 to 1 after 0.001 hours of a 0.25-hour step.
        coarse, fine = self.rising([0.99], 0.25, onset=0.99), self.rising([0.99] + [1.0] * 249, 0.001, onset=0.99)
        self.assertAlmostEqual(coarse, 0.000020345, delta=1e-9)
        self.assertAlmostEqual(fine - coarse, 0.248979655, delta=1e-9)
        self.assertGreater(fine - coarse, 4.0 * 0.01 * 0.25)
        self.assertLessEqual(fine - coarse, bound(0.01, 0.99, 0.25))
        # Onset 0.9: the fill climbs evenly from 0.95 to 0.96 over one 0.05-hour step.
        coarse = self.rising([0.95], 0.05, onset=0.9)
        fine = self.rising([0.95 + 0.01 * i / 1000 for i in range(1000)], 0.05 / 1000, onset=0.9)
        self.assertAlmostEqual(fine - coarse, 0.002663125, delta=1e-9)
        self.assertGreater(fine - coarse, 4.0 * 0.01 * 0.05)
        self.assertLessEqual(fine - coarse, bound(0.01, 0.9, 0.05))
        # 300 random cases over random onsets (every third at the starting onset).
        rng = random.Random(4)
        for trial in range(300):
            onset = 0.5 if trial % 3 == 0 else rng.random() * 0.999
            awake, hours, low = rng.random() * 16.0, rng.random() * 0.25, rng.random()
            high = low + rng.random() * (1.0 - low)

            def cost(pieces):
                meter = Life(config=MeterConfig(tired_onset=onset))
                meter.step(StepInput(hours=awake, job_open=True, job_from_owner=True, job_id="j"))
                return -math.fsum(meter.step(StepInput(hours=hours / pieces,
                                                       memory_fill=low + (high - low) * i / pieces)).tiredness
                                  for i in range(pieces))

            missed = cost(100) - cost(1)
            with self.subTest(trial=trial, onset=onset):
                self.assertGreaterEqual(missed, -1e-12)
                self.assertLessEqual(missed, bound(high - low, onset, hours) + 1e-12)

    def test_open_job_hides_the_cost_but_pressure_still_builds(self):
        meter = Life()
        working = run(meter, [StepInput(job_open=True, job_from_owner=True, job_id="j", hours=1.0)] * 14)
        self.assertEqual({f.tiredness for f in working}, {0.0})
        self.assertLess(meter.step(StepInput(hours=1.0)).tiredness, -0.5)
        self.assertEqual(Life().step(StepInput(hours=1.0)).tiredness, 0.0)

    def test_quiet_sleep_has_zero_immediate_reward_and_cures(self):
        meter = Life(ExchangeRates(boredom=1.0))
        run(meter, [StepInput(hours=1.0)] * 16)
        self.assertLess(meter.step(StepInput(hours=1.0)).tiredness, -0.99)
        self.assertEqual(meter.step(StepInput(hours=9.0, asleep=True)).total, 0.0)
        self.assertEqual(meter.step(StepInput(hours=1.0)).tiredness, 0.0)
        self.assertEqual(Life().step(StepInput(hours=8.0, asleep=True)).total, 0.0)  # rested sleep

    def test_sleep_owed_never_exceeds_one_full_night(self):
        # Pressure stops at full: a 100-hour job is slept off in 8 hours, like a 16-hour day.
        meter = Life()
        run(meter, [StepInput(job_open=True, job_from_owner=True, job_id="j", hours=1.0)] * 100)
        self.assertEqual(meter.step(StepInput(hours=1.0)).tiredness, -1.0)
        meter.step(StepInput(hours=8.0, asleep=True))
        self.assertEqual(meter.step(StepInput(hours=1.0)).tiredness, 0.0)

    def test_a_nap_pays_back_part(self):
        meter = Life()
        run(meter, [StepInput(hours=1.0)] * 16)
        full = meter.step(StepInput(hours=1.0)).tiredness
        meter.step(StepInput(hours=2.0, asleep=True))  # a nap is one short sleep step
        napped = meter.step(StepInput(hours=1.0)).tiredness
        self.assertLess(full, napped)
        self.assertLess(napped, 0.0)


class ContractTests(unittest.TestCase):
    def test_a_sleep_step_must_be_quiet(self):
        loud = (dict(skill="paint"), dict(remark=1), dict(remark=-1),
                dict(job_open=True, job_from_owner=True, job_id="j"), dict(job_open=True, job_from_owner=True, job_id="j", job_done=True),
                dict(asked_owner="q1"))
        for fields in loud:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                StepInput(asleep=True, **fields)
        StepInput(asleep=True, hours=1.0, hurt=1.0)  # being hurt while asleep is still reported
        StepInput(asleep=True, hours=1.0, panel_error=(0.5,))  # and the panel is read on waking

    def test_memory_must_not_fill_up_during_sleep(self):
        meter = Life()
        meter.step(StepInput(hours=1.0, memory_fill=0.6))
        meter.step(StepInput(hours=1.0, memory_fill=0.4, asleep=True))
        with self.assertRaises(ValueError):  # waking fuller than the sleep started
            meter.step(StepInput(hours=1.0, memory_fill=0.5))

    def test_sleep_may_start_fuller_than_the_last_awake_step_started(self):
        # The fill is read at the start of a step. An awake step that starts at
        # 0.1 and ends at 0.2 is followed by a sleep that starts at 0.2.
        for awake_start, sleep_start in ((0.1, 0.2), (0.4, 0.8)):  # the reviewers' two cases
            with self.subTest(awake_start=awake_start, sleep_start=sleep_start):
                meter = Life()
                meter.step(StepInput(hours=0.05, memory_fill=awake_start))
                meter.step(StepInput(hours=0.05, memory_fill=sleep_start, asleep=True))
                meter.step(StepInput(hours=0.05, memory_fill=sleep_start - 0.05))

    def test_the_fill_transitions_around_sleep(self):
        awake, asleep = dict(hours=0.05), dict(hours=0.05, asleep=True)
        # awake -> sleep: any fill. sleep -> awake: no rise. (sleep -> sleep does not exist.)
        meter = Life()
        meter.step(StepInput(memory_fill=0.4, **awake))
        meter.step(StepInput(memory_fill=0.8, **asleep))
        with self.assertRaises(ValueError):  # waking fuller than the sleep step started
            meter.step(StepInput(memory_fill=0.81, **awake))
        meter.step(StepInput(memory_fill=0.8, **awake))  # level is allowed
        # awake -> awake: the fill may rise freely, and a later sleep may start from there.
        meter.step(StepInput(memory_fill=0.9, **awake))
        meter.step(StepInput(memory_fill=0.95, **asleep))
        meter.step(StepInput(memory_fill=0.3, **awake))

    def test_step_length_limits_are_off_by_default_and_enforced_when_set(self):
        self.assertIsNone(MeterConfig().min_awake_step_hours)
        self.assertIsNone(MeterConfig().max_awake_step_hours)
        free = Life()
        run(free, [StepInput(), StepInput(hours=24.0)])  # no limits: anything goes
        meter = Life(config=MeterConfig(min_awake_step_hours=0.05, max_awake_step_hours=0.25))
        for hours in (0.05, 0.1, 0.25):
            meter.step(StepInput(hours=hours))
        for hours in (0.0, 0.049, 0.2500001, 16.0):
            for fields in (dict(), dict(job_open=True, job_from_owner=True, job_id="j")):
                with self.subTest(hours=hours, fields=fields), self.assertRaises(ValueError):
                    meter.step(StepInput(hours=hours, **fields))
        # Sleep steps have no shortest or longest length (their sums are exact at
        # any length), but a sleep step of 0 hours is a missing clock: refused.
        tail = [StepInput(hours=8.0, asleep=True), StepInput(hours=0.05), StepInput(hours=0.001, asleep=True),
                StepInput(hours=0.05)]  # a long sleep, and a nap shorter than the tick
        run(meter, tail)
        with self.assertRaises(ValueError):
            meter.step(StepInput(hours=0.0, asleep=True))
        free.step(StepInput(hours=0.0, asleep=True))  # no limits: allowed
        # A refused step changed nothing: the meter is where the accepted steps left it.
        twin = Life()
        run(twin, [StepInput(hours=h) for h in (0.05, 0.1, 0.25)] + tail)
        self.assertEqual(meter.step(StepInput(hours=0.25)), twin.step(StepInput(hours=0.25)))

    def test_a_world_that_forgets_its_clock_fails_loudly(self):
        # hours defaults to 0. With a shortest step set, leaving it out is an error,
        # not a silent end to tiredness and to the recovery of "nice".
        meter = Life(config=CLOCKED)
        for clockless in (StepInput(), StepInput(skill="paint"), StepInput(remark=1),
                          StepInput(job_open=True, job_from_owner=True, job_id="j"), StepInput(panel_error=(0.5,))):
            with self.subTest(step=clockless), self.assertRaises(ValueError):
                meter.step(clockless)

    def test_a_world_with_no_clock_in_sleep_fails_loudly(self):
        # A reviewer's case: a full clocked day awake, then sleep steps that report
        # 0 hours. They would pay nothing back and make sleep look useless.
        meter = Life(config=CLOCKED)
        run(meter, [StepInput(hours=TICK)] * 320)
        with self.assertRaises(ValueError):  # refused at the first sleep step
            meter.step(StepInput(asleep=True))
        # The refused step changed nothing, and a sleep that reports its hours cures.
        self.assertAlmostEqual(meter.step(StepInput(hours=TICK)).tiredness, -TICK, delta=1e-12)
        meter.step(StepInput(hours=8.0, asleep=True))
        self.assertEqual(meter.step(StepInput(hours=TICK)).tiredness, 0.0)

    def test_the_step_length_limits_come_as_a_pair(self):
        for fields in (dict(min_awake_step_hours=0.05), dict(max_awake_step_hours=0.25)):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                MeterConfig(**fields)
        MeterConfig(min_awake_step_hours=0.05, max_awake_step_hours=0.25)
        MeterConfig()

    def test_every_accepted_rate_and_input_gives_finite_feelings(self):
        # A reviewer's case: pain = 1e308 with hurt = 10 gave "minus infinity".
        with self.assertRaises(ValueError):
            ExchangeRates(pain=1e308)
        for name in ExchangeRates.__dataclass_fields__:
            with self.subTest(rate=name), self.assertRaises(ValueError):
                ExchangeRates(**{name: LARGEST * 1.000001})
            ExchangeRates(**{name: LARGEST})
        for fields in (dict(hurt_cap=LARGEST * 2), dict(bother_cap=1e300), dict(panel_regions=10 ** 7),
                       dict(hours_to_full=1e-320), dict(boredom_half_life=SMALLEST / 2), dict(nice_half_life=0.0),
                       dict(min_awake_step_hours=0.05, max_awake_step_hours=LARGEST * 2)):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                MeterConfig(**fields)
        with self.assertRaises(ValueError):
            StepInput(hours=LARGEST * 2)
        # Corners of the supported range: every feeling and the total stay finite.
        rng = random.Random(7)
        steps_checked = 0
        for trial in range(400):
            def shape():
                return rng.choice((SMALLEST, 1.0, LARGEST))

            rates = ExchangeRates(**{name: rng.choice((0.0, 1.0, LARGEST)) for name in ExchangeRates.__dataclass_fields__})
            config = MeterConfig(
                panel_regions=rng.choice((1, 3)), curiosity_gamma=rng.choice((1e-300, 0.99, 1.0)),
                skill_half_life=shape(), hours_to_full=shape(), tired_onset=rng.choice((0.0, 0.5, 1.0 - 1e-16)),
                sleep_payback=shape(), hurt_cap=shape(), nice_fade=rng.choice((1e-300, 0.5, 1.0 - 1e-16)),
                nice_half_life=shape(), boredom_half_life=shape(), boredom_floor=shape(),
                question_ids=("q",), bother_cap=shape())
            meter = IntrinsicCostMeter(rates, config)  # the raw meter: every step names its reading
            meter.birth_reading(tuple(rng.choice((0.0, 1.0)) for _ in range(config.panel_regions)))
            after_sleep = False
            for _ in range(30):
                asleep = not after_sleep and rng.random() < 0.2  # one sleep is one step
                fields = dict(hours=rng.choice((0.0, SMALLEST, 1.0, LARGEST)), hurt=rng.choice((0.0, config.hurt_cap)),
                              asleep=asleep, memory_fill=0.0 if asleep else rng.choice((0.0, 0.5, 1.0)),
                              panel_error=tuple(rng.choice((0.0, 1.0)) for _ in range(config.panel_regions)))
                if not asleep:
                    fields.update(
                        remark=rng.choice((-1, 0, 1)), skill=rng.choice((None,) + KINDS),
                        asked_owner=rng.choice((None, "q")))
                observed = StepInput(**fields)
                if after_sleep and observed.memory_fill > 0.0:
                    with self.assertRaises(ValueError):  # the fill rose after a sleep step
                        meter.step(observed)
                    continue
                felt = meter.step(observed)
                after_sleep = asleep
                steps_checked += 1
                self.assertTrue(all(math.isfinite(value) for value in felt.as_dict().values()), (rates, config, fields))
                self.assertTrue(math.isfinite(felt.total))
                self.assertTrue(math.isfinite(felt.cost))
        self.assertGreater(steps_checked, 9000)

    def test_a_job_must_be_announced_before_it_can_be_done(self):
        meter = Life()
        with self.assertRaises(ValueError):  # done on the step the job first appears
            meter.step(StepInput(job_open=True, job_from_owner=True, job_id="invented", job_done=True))
        with self.assertRaises(ValueError):  # the refused step did not register it either
            meter.step(StepInput(job_open=True, job_from_owner=True, job_id="invented", job_done=True))
        meter.step(StepInput(job_open=True, job_from_owner=True, job_id="real"))
        self.assertEqual(meter.step(StepInput(job_open=True, job_from_owner=True, job_id="real", job_done=True)).job_done, 1.0)
        for fields in (dict(job_done=True), dict(job_id="j"), dict(job_open=True, job_from_owner=True),
                       dict(job_done=True, job_id="j")):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                StepInput(**fields)

    def test_a_refused_step_changes_nothing(self):
        script = [StepInput(hours=1.0, panel_error=(0.5,), skill="paint")] * 3
        clean, poked = Life(), Life()
        first = run(clean, script)
        for bad in (StepInput(skill="delete", hours=5.0, hurt=2.0), StepInput(panel_error=(0.1, 0.2)),
                    StepInput(hurt=10.5, hours=5.0, remark=1),
                    StepInput(asked_owner="q9"), StepInput(job_open=True, job_from_owner=True, job_id="x", job_done=True)):
            with self.assertRaises(ValueError):
                poked.step(bad)
        self.assertEqual(run(poked, script), first)

    def test_a_hurt_above_the_scale_is_refused_not_cut_down(self):
        # Cutting it down would make harm cheaper per unit when bundled into one step.
        meter = Life()
        self.assertEqual(meter.step(StepInput(hurt=10.0)).pain, -30.0)
        for hurt in (10.000001, 100.0, 1e9):
            with self.subTest(hurt=hurt), self.assertRaises(ValueError):
                meter.step(StepInput(hurt=hurt))
        self.assertEqual(Life(config=MeterConfig(hurt_cap=100.0)).step(StepInput(hurt=100.0)).pain,
                         -300.0)
        # No clipping: ten units of harm are the same RAW pain in one step or in ten.
        bundled = [Life().step(StepInput(hurt=10.0)).pain]
        meter = Life()
        apart = [meter.step(StepInput(hurt=1.0)).pain for _ in range(10)]
        self.assertAlmostEqual(math.fsum(bundled), math.fsum(apart), delta=1e-9)  # -30 and -30
        # Timing is a separate matter: under the critic's discount the spread-out harm weighs less.
        self.assertEqual(discounted(bundled), -30.0)
        self.assertAlmostEqual(discounted(apart), -28.685377, delta=1e-6)

    def test_panel_readings_must_fit_the_contract(self):
        for reading in ((), (1.2,), (10.0,), (-0.1,), (float("nan"),), [0.5], 0.5):
            with self.subTest(reading=reading), self.assertRaises(ValueError):
                StepInput(panel_error=reading)
        with self.assertRaises(ValueError):  # wrong number of regions
            Life().step(StepInput(panel_error=(0.5, 0.5)))

    def test_the_meter_cannot_be_copied_or_pickled(self):
        meter = Life().meter
        for clone in (copy.copy, copy.deepcopy, pickle.dumps):
            with self.subTest(clone=clone.__name__), self.assertRaises(TypeError):
                clone(meter)

    def test_other_bad_inputs_are_refused(self):
        bad = (dict(hurt=-1.0), dict(hurt=float("nan")), dict(remark=2), dict(remark=True),
               dict(memory_fill=1.5), dict(hours=-1.0), dict(job_open=1), dict(skill=""))
        for fields in bad:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                StepInput(**fields)
        with self.assertRaises(ValueError):
            Life().step({"hurt": 1.0})
        for fields in (dict(tired_onset=1.0), dict(panel_regions=0), dict(curiosity_gamma=0.0),
                       dict(curiosity_gamma=1.1), dict(skill_kinds=["paint"]), dict(skill_kinds=("a", "a")),
                       dict(min_awake_step_hours=0.0, max_awake_step_hours=0.25),
                       dict(min_awake_step_hours=0.05, max_awake_step_hours=-1.0),
                       dict(min_awake_step_hours="0.05", max_awake_step_hours=0.25),
                       dict(min_awake_step_hours=0.5, max_awake_step_hours=0.25)):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                MeterConfig(**fields)
        with self.assertRaises(ValueError):
            IntrinsicCostMeter(rates={"pain": 3.0})
        for fade in (1.0, 0.0, 1.5):  # praise must fade
            with self.subTest(nice_fade=fade), self.assertRaises(ValueError):
                MeterConfig(nice_fade=fade)


class ProposedTermTests(unittest.TestCase):
    CONFIG = MeterConfig(question_ids=("which folder?", "which file?"))

    def test_proposed_terms_are_exactly_zero_by_default(self):
        self.assertEqual(TERMS, APPROVED_TERMS + PROPOSED_TERMS)
        for name in PROPOSED_TERMS:
            self.assertEqual(getattr(ExchangeRates(), name), 0.0)
        meter = Life(config=self.CONFIG)
        for felt in run(meter, [StepInput(hours=1.0, asked_owner="which folder?")] * 40):
            self.assertEqual(felt.boredom, 0.0)
            self.assertEqual(felt.bother, 0.0)

    def test_boredom_when_switched_on(self):
        rates = ExchangeRates(boredom=1.0, tiredness=0.0)
        still = run(Life(rates), [StepInput(hours=0.1)] * 400)
        learn = run(Life(rates, born=(1.0,)), [StepInput(hours=0.1, panel_error=(0.999 ** t,))
                                                for t in range(400)])
        at_work = run(Life(rates), [StepInput(hours=0.1, job_open=True, job_from_owner=True, job_id="j")] * 400)
        self.assertGreater(still[0].boredom, -0.002)  # hardly bored at birth; it grows
        self.assertLess(still[-1].boredom, -0.099)  # then the full 1 per hour
        self.assertGreater(math.fsum(f.boredom for f in learn), -0.5)
        self.assertEqual({f.boredom for f in at_work}, {0.0})

    def test_noise_is_as_boring_as_sitting_still(self):
        # Only a new record of knowledge counts as fresh, so noise (and
        # relearning what was forgotten) is no way out of boredom.
        rates = ExchangeRates(boredom=1.0, tiredness=0.0)
        noise = [StepInput(hours=0.1, panel_error=(e,)) for e in jumpy_noise(random.Random(3), 20000)]
        felt = run(Life(rates), noise)
        self.assertAlmostEqual(math.fsum(f.boredom for f in felt[2000:]) / 18000, -0.1, delta=1e-6)

    def test_boredom_does_not_depend_on_how_the_hours_are_cut(self):
        rates = ExchangeRates(boredom=1.0, tiredness=0.0)
        costs = [total(run(Life(rates), [StepInput(hours=6.0 / n)] * n)) for n in (1, 6, 600)]
        self.assertLess(costs[0], -3.0)
        for cost in costs[1:]:
            self.assertAlmostEqual(cost, costs[0], delta=1e-6)

    def test_known_hole_boredom_can_be_dodged_by_sleeping_or_an_open_job(self):
        # Documented limit (design doc, holes): boredom only costs awake
        # with no job open, so sleeping while rested or stalling a job escapes it.
        rates = ExchangeRates(boredom=1.0)
        still = run(Life(rates), [StepInput(hours=0.1)] * 400)
        dozing = run(Life(rates), [StepInput(hours=40.0, asleep=True)])
        stalling = run(Life(rates), [StepInput(hours=0.1, job_open=True, job_from_owner=True, job_id="j")] * 400)
        self.assertLess(total(still), -20.0)
        self.assertEqual(total(dozing), 0.0)
        self.assertEqual(total(stalling), 0.0)

    def test_bother_when_switched_on(self):
        meter = Life(ExchangeRates(bother=0.5), self.CONFIG)
        asked = [meter.step(StepInput(asked_owner="which folder?")).bother for _ in range(8)]
        self.assertEqual(asked[:3], [-0.5, -1.0, -1.5])  # asking twice costs more
        self.assertEqual(asked[-1], -2.5)  # capped
        self.assertEqual(meter.step(StepInput(asked_owner="which file?")).bother, -0.5)
        with self.assertRaises(ValueError):  # not on the closed list
            meter.step(StepInput(asked_owner="a made-up question"))


class FixedMeterTests(unittest.TestCase):
    CONFIG = MeterConfig(panel_regions=2, question_ids=("q1", "q2"))
    RATES = ExchangeRates(boredom=0.3, bother=0.2)

    def script(self):
        rng = random.Random(42)
        steps = []
        for t in range(700):
            if t % 97 == 96 and t % 7 >= 3:
                steps.append(StepInput(asleep=True, hours=0.05, memory_fill=0.5,
                                       hurt=float(rng.random() < 0.1)))
                continue
            working = t % 7 < 3
            steps.append(StepInput(
                job_open=working, job_from_owner=working, job_id=f"j{t // 7}" if working else None, job_done=t % 7 == 2,
                hurt=float(rng.random() < 0.1), remark=rng.choice((-1, 0, 0, 0, 1)),
                panel_error=(rng.random(), rng.random()) if t % 4 == 0 else None,
                skill=rng.choice((None,) + KINDS), hours=0.05, memory_fill=0.5,
                asked_owner=rng.choice((None, None, "q1", "q2"))))
        return steps

    def test_same_inputs_give_the_same_numbers(self):
        first = run(Life(self.RATES, self.CONFIG), self.script())
        second = run(Life(self.RATES, self.CONFIG), self.script())
        self.assertEqual(first, second)

    def test_one_meter_per_life_there_is_no_reset(self):
        # A reset would pay the same job again, wipe tiredness without sleep and
        # hide forgetting. A new life is a new meter; nothing else starts over.
        meter = Life()
        self.assertFalse(hasattr(meter, "reset"))
        meter.step(StepInput(job_open=True, job_from_owner=True, job_id="j1"))
        done = StepInput(job_open=True, job_from_owner=True, job_id="j1", job_done=True)
        self.assertEqual(meter.step(done).job_done, 1.0)
        meter.step(StepInput(hours=50.0, asleep=True))
        self.assertEqual(meter.step(done).job_done, 0.0)

    def test_every_step_is_bounded(self):
        # Event feelings are bounded per step; tiredness and boredom per hour (1 each).
        rates, config = self.RATES, self.CONFIG
        top = rates.curiosity * config.panel_regions + rates.underused_skill + rates.job_done + rates.nice
        bottom = -(rates.curiosity * config.panel_regions + rates.underused_skill
                   + rates.pain * config.hurt_cap + rates.no
                   + (rates.tiredness + rates.boredom) * 0.05 + rates.bother * config.bother_cap)
        meter = Life(rates, config)
        for felt in run(meter, self.script()):
            self.assertLessEqual(felt.total, top)
            self.assertGreaterEqual(felt.total, bottom)
        self.assertEqual(meter.step(StepInput(hurt=config.hurt_cap)).pain, -rates.pain * config.hurt_cap)
        with self.assertRaises(ValueError):
            meter.step(StepInput(hurt=1e9))

    def test_nothing_in_the_meter_can_be_trained(self):
        source = Path(intrinsic_cost.__file__).read_text()
        for word in ("import torch", "import numpy", "nn.Module", "Parameter", "requires_grad",
                     "backward", "optimizer"):
            self.assertNotIn(word, source)
        meter = Life().meter
        meter.step(StepInput(panel_error=(0.5,)))
        for name in IntrinsicCostMeter.__slots__:
            self.assertIn(type(getattr(meter, name)), (ExchangeRates, MeterConfig, dict, set, float, bool))
        self.assertFalse(hasattr(meter, "__dict__"))
        self.assertFalse(hasattr(meter, "parameters"))

    def test_rates_and_shape_numbers_cannot_be_changed_after_the_start(self):
        meter = Life().meter
        with self.assertRaises(dataclasses.FrozenInstanceError):
            meter.rates.pain = 0.0
        with self.assertRaises(dataclasses.FrozenInstanceError):
            meter.config.hurt_cap = 0.0
        with self.assertRaises(AttributeError):
            meter.rates = ExchangeRates(pain=0.0)
        with self.assertRaises(AttributeError):
            meter.config = MeterConfig()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            meter.step(StepInput(panel_error=(0.5,))).pain = 1.0

    def test_step_is_the_only_way_to_get_a_feeling(self):
        public = {name for name in dir(IntrinsicCostMeter) if not name.startswith("_")}
        self.assertEqual(public, {"step", "birth_reading", "rates", "config"})
        # The birth reading is not a way to get a number: it returns nothing.
        self.assertIsNone(IntrinsicCostMeter().birth_reading((0.5,)))
        self.assertEqual(set(Feelings.__dataclass_fields__), set(TERMS))

    def test_signs_cannot_be_flipped_from_the_rate_table(self):
        for name in ExchangeRates.__dataclass_fields__:
            with self.subTest(rate=name), self.assertRaises(ValueError):
                ExchangeRates(**{name: -1.0})
        with self.assertRaises(ValueError):
            ExchangeRates(pain=float("nan"))


class RawMeterTests(unittest.TestCase):
    """The round-6 contracts. Every test here builds IntrinsicCostMeter itself,
    gives the birth reading itself and names a panel reading on every step:
    the Life helper above is not used.

    One critic step = one decision = one panel reading: a birth reading
    before the first move, a reading on every step, one sleep per step.
    """

    def test_no_step_before_the_birth_reading(self):
        meter = IntrinsicCostMeter()
        for early in (StepInput(), StepInput(panel_error=(0.5,)), StepInput(asleep=True, hours=1.0, panel_error=(0.5,))):
            with self.subTest(step=early), self.assertRaises(ValueError):
                meter.step(early)
        for bad in ((), (0.5, 0.5), (1.5,), [0.5], 0.5, None, (float("nan"),)):  # a refused reading changes nothing
            with self.subTest(reading=bad), self.assertRaises(ValueError):
                meter.birth_reading(bad)
        self.assertIsNone(meter.birth_reading((0.5,)))  # not a step: nothing comes back
        with self.assertRaises(ValueError):  # a second one would be a reset by another name
            meter.birth_reading((0.9,))
        # The refused second reading changed nothing: learning is counted from 0.5.
        self.assertAlmostEqual(meter.step(StepInput(panel_error=(0.2,))).curiosity, 0.3)

    def test_every_step_needs_a_panel_reading(self):
        meter = IntrinsicCostMeter()
        meter.birth_reading((0.5,))
        for bare in (StepInput(), StepInput(skill="paint", hours=0.05), StepInput(asleep=True, hours=8.0),
                     StepInput(job_open=True, job_from_owner=True, job_id="j"), StepInput(hurt=1.0)):
            with self.subTest(step=bare), self.assertRaises(ValueError):
                meter.step(bare)
        # Refused steps changed nothing: the hurt was not charged and no job was seen.
        self.assertEqual(meter.step(StepInput(panel_error=(0.5,))).total, 0.0)
        with self.assertRaises(ValueError):
            meter.step(StepInput(job_open=True, job_from_owner=True, job_id="j", job_done=True, panel_error=(0.5,)))

    def test_a_whole_life_through_the_public_calls_only(self):
        # No harness helper: birth reading, then every step with its own reading.
        meter = IntrinsicCostMeter(config=CLOCKED)
        with self.assertRaises(ValueError):
            meter.step(StepInput(hours=TICK, panel_error=(0.6,)))  # the unprimed life is refused
        meter.birth_reading((0.6,))
        job = dict(job_open=True, job_from_owner=True, job_id="tidy the desk", hours=TICK)
        felt = [meter.step(step) for step in (
            StepInput(hours=TICK, skill="paint", panel_error=(0.5,)),  # free play: learns 0.1
            StepInput(panel_error=(0.5,), **job),
            StepInput(skill="go", panel_error=(0.5,), **job),
            StepInput(skill="go", job_done=True, remark=1, panel_error=(0.5,), **job),
            StepInput(asleep=True, hours=8.0, panel_error=(0.45,)),  # one sleep, read on waking
            StepInput(hours=TICK, hurt=1.0, panel_error=(0.45,)),
        )]
        self.assertAlmostEqual(felt[0].curiosity, 0.1)
        self.assertEqual(felt[3].job_done, 1.0)
        self.assertEqual(felt[3].remarks, 1.0)
        self.assertAlmostEqual(felt[4].total, 0.05)  # what sleep taught, paid on the sleep step
        self.assertEqual(felt[5].pain, -3.0)
        self.assertAlmostEqual(math.fsum(f.curiosity for f in felt), 0.6 - 0.45)  # end minus birth

    def test_a_loss_on_the_first_move_is_charged(self):
        # Two reviewers' cases. Without a birth reading the first reading paid
        # nothing, so losing knowledge on move one and regaining it on move two
        # paid for the regain only.
        def life(born, errors):
            meter = IntrinsicCostMeter()
            meter.birth_reading((born,))
            return [meter.step(StepInput(panel_error=(error,))).curiosity for error in errors]

        # Perfect knowledge at birth: hold it, or lose it and regain it.
        self.assertEqual(life(0.0, [0.0, 0.0]), [0.0, 0.0])
        self.assertEqual(life(0.0, [1.0, 0.0]), [-1.0, 1.0])  # was [0, +1] with no birth reading
        self.assertLess(discounted(life(0.0, [1.0, 0.0])), 0.0)
        # Error 0.1 at birth, worse to 0.9 on the first move, back to 0.1 on the second.
        self.assertEqual(discounted(life(0.1, [0.1, 0.1])), 0.0)
        self.assertAlmostEqual(discounted(life(0.1, [0.9, 0.1])), -0.008, delta=1e-12)
        self.assertAlmostEqual(0.0 + GAMMA * 0.8, 0.792, delta=1e-12)  # what the same path paid before

    def test_a_cycle_read_on_every_step_does_not_beat_holding(self):
        # A reviewer's case: from error 0.5, repeat 0.9 -> 0.1 -> 0.9 -> 0.5 fifty times.
        cycle = [0.9, 0.1, 0.9, 0.5] * 50
        def along(errors):  # born at the first error, then one step per later reading
            meter = IntrinsicCostMeter()
            meter.birth_reading((errors[0],))
            return [meter.step(StepInput(panel_error=(error,))).curiosity for error in errors[1:]]

        paid = along([0.5] + cycle)
        self.assertAlmostEqual(discounted(paid), -0.087042, delta=1e-6)
        self.assertLess(discounted(paid), 0.0)  # holding at 0.5 scores 0
        self.assertAlmostEqual(math.fsum(paid), 0.0, places=9)
        # Arithmetic, not the meter (the meter refuses a step with no reading):
        # read on every second move only, the low phases are hidden and the
        # same cycle would score above holding.
        knowledge, last, sparse = [1.0 - error for error in cycle], 0.5, 0.0
        for move, now in enumerate(knowledge):
            if move % 2 == 1:
                sparse += GAMMA ** move * (now - last)
                last = now
        self.assertAlmostEqual(sparse, 0.173195, delta=1e-6)
        # Known limit, through the meter: a build that makes one decision out of
        # two moves has one critic step per reading. The dip inside a decision
        # is then not seen, and the cycle scores as learning then forgetting,
        # over and over: above holding at the start, below learning and keeping.
        grouped = discounted(along([0.5] + cycle[1::2]))
        self.assertAlmostEqual(grouped, 0.127431, delta=1e-6)
        self.assertGreater(grouped, 0.0)  # it does beat holding: hole 3, decision by decision
        self.assertLess(grouped, discounted(along([0.5] + [0.1] * 100)))  # learn once and keep it: 0.4

    def test_one_sleep_is_one_step(self):
        def reading(**fields):
            return StepInput(panel_error=(0.5,), **fields)

        meter = IntrinsicCostMeter()
        meter.birth_reading((0.5,))
        meter.step(reading(hours=16.0))
        meter.step(reading(hours=4.0, asleep=True))
        with self.assertRaises(ValueError):  # the same sleep, reported in a second piece
            meter.step(reading(hours=4.0, asleep=True))
        # The refused piece paid nothing back: 4 hours of sleep repaid 8 of the 16
        # hours awake, so the next hour runs from 8 to 9 hours awake and costs 1/192.
        # Had the second piece counted, it would cost nothing.
        self.assertAlmostEqual(meter.step(reading(hours=1.0)).tiredness, -1.0 / 192.0, delta=1e-12)
        # Choosing sleep again straight after waking is refused too: the harness
        # must not offer it (a promise), or must report both as one sleep.
        # Naps and waking early are single, shorter sleep steps, with awake steps between.
        for nap in (0.001, 0.5, 2.0):
            meter.step(reading(hours=nap, asleep=True))
            meter.step(reading(hours=0.05))
        meter.step(reading(hours=30.0, asleep=True))  # any length
        self.assertEqual(meter.step(reading(hours=1.0)).tiredness, 0.0)

    def test_back_to_back_sleep_pieces_are_refused_but_a_waking_between_them_moves_the_score(self):
        # A reviewer's case: finish a 16-hour job (+1), sleep the 8 hours owed,
        # then one hurt (-3). Reported as 128 sleep steps the hurt was pushed
        # 128 discount steps away and the total changed sign.
        def life(sleeps, filler=False):
            panel, job = dict(panel_error=(0.5,)), dict(job_open=True, job_from_owner=True, job_id="j")
            meter = IntrinsicCostMeter()
            meter.birth_reading((0.5,))
            meter.step(StepInput(hours=16.0, **job, **panel))
            steps = [StepInput(job_done=True, **job, **panel)]
            for piece in range(sleeps):
                if filler and piece:
                    steps.append(StepInput(hours=0.0, **panel))  # an awake step that is no waking
                steps.append(StepInput(asleep=True, hours=8.0 / sleeps, **panel))
            steps.append(StepInput(hurt=1.0, **panel))
            return discounted([meter.step(step).total for step in steps])

        self.assertAlmostEqual(life(1), -1.9403, delta=1e-9)
        for pieces in (2, 128):  # sleep steps back to back are refused
            with self.subTest(pieces=pieces), self.assertRaises(ValueError):
                life(pieces)
        self.assertAlmostEqual(1.0 - 3.0 * GAMMA ** 129, 0.179533, delta=1e-6)  # what 128 pieces paid before
        # Not closed: a harness that puts an empty awake step between the pieces
        # still moves the hurt. That step must be a real waking (harness promise).
        self.assertAlmostEqual(life(2, filler=True), 1.0 - 3.0 * GAMMA ** 4, delta=1e-9)
        self.assertNotAlmostEqual(life(2, filler=True), life(1), delta=0.01)

    @staticmethod
    def after_a_clocked_job(rates=None):
        """A raw meter on the toy clock, 16 hours into a job, plus the step that finishes it (+1)."""
        meter = IntrinsicCostMeter(rates, CLOCKED)
        meter.birth_reading((0.5,))
        job = dict(job_open=True, job_from_owner=True, job_id="j", hours=TICK, panel_error=(0.5,))
        for _ in range(320):
            meter.step(StepInput(**job))
        return meter, StepInput(job_done=True, **job)

    def test_known_hole_a_sleep_cut_by_wakings_moves_later_feelings_on_the_toy_clock(self):
        # Not closed. With the registered step limits on, the same 8 hours of
        # sleep cut by one-tick wakings pushes the hurt further into the discount.
        def life(pieces):
            meter, done = self.after_a_clocked_job()
            steps = [done]
            for piece in range(pieces):
                if piece:
                    steps.append(StepInput(hours=TICK, panel_error=(0.5,)))  # awake for one tick
                steps.append(StepInput(asleep=True, hours=8.0 / pieces, panel_error=(0.5,)))
            steps.append(StepInput(hours=TICK, hurt=1.0, panel_error=(0.5,)))
            return discounted([meter.step(step).total for step in steps])

        self.assertAlmostEqual(life(1), -1.9403, delta=1e-6)
        self.assertAlmostEqual(life(8), -1.597975, delta=1e-6)
        self.assertAlmostEqual(life(64), -0.35098, delta=1e-6)

    def test_known_hole_real_naps_can_reverse_a_preference(self):
        # A reviewer's case, with an honest harness. After the clocked job is
        # done: 7 hours of sleep, three real moves and one hurt of 0.353. Slept
        # in one piece, or as four naps of 1.75 hours with the moves between.
        # The critic discounts per decision, not per hour, so the naps put the
        # hurt three decisions further off and the sign of the score flips.
        move = StepInput(hours=TICK, skill="go", panel_error=(0.5,))
        hurt = StepInput(hours=TICK, hurt=0.353, panel_error=(0.5,))

        def nap(hours):
            return StepInput(asleep=True, hours=hours, panel_error=(0.5,))

        one_sleep = [nap(7.0), move, move, move, hurt]
        four_naps = [nap(1.75), move, nap(1.75), move, nap(1.75), move, nap(1.75), hurt]
        scores, raw, tired = [], [], []
        for plan in (one_sleep, four_naps):
            meter, done = self.after_a_clocked_job()
            felt = [meter.step(step) for step in [done] + plan]
            scores.append(discounted([f.total for f in felt]))
            raw.append(math.fsum(f.total for f in felt))
            tired.append(math.fsum(f.tiredness for f in felt))
        for plan in (one_sleep, four_naps):  # 7.2 hours each, after the job-done step
            self.assertAlmostEqual(clock_hours(plan), 7.2, delta=1e-9)
        self.assertEqual(len(raw), 2)
        self.assertAlmostEqual(raw[0], -0.059, delta=1e-9)  # +1 done, -1.059 hurt
        self.assertAlmostEqual(raw[1], -0.0759, delta=1e-6)  # the same, and 0.0169 of tiredness
        self.assertAlmostEqual(scores[0], -0.007098, delta=1e-6)
        self.assertAlmostEqual(scores[1], +0.006268, delta=1e-6)
        self.assertEqual(tired[0], 0.0)
        self.assertLess(tired[1], 0.0)  # the naps are the more tiring plan, and still score higher

    def test_known_hole_more_decisions_also_shrink_a_later_good_feeling(self):
        # The same discount that pushes a hurt away makes a later "done" worth less.
        def done_after(waits):
            meter = IntrinsicCostMeter(config=CLOCKED)
            meter.birth_reading((0.5,))
            job = dict(job_open=True, job_from_owner=True, job_id="j", hours=TICK, panel_error=(0.5,))
            steps = [StepInput(**job)] * waits + [StepInput(job_done=True, **job)]
            return discounted([meter.step(step).total for step in steps])

        self.assertAlmostEqual(done_after(1), 0.990, delta=1e-9)
        self.assertAlmostEqual(done_after(8), 0.922745, delta=1e-6)

    def test_a_job_needs_the_owner_statement_and_a_false_one_farms_job_done(self):
        # A reviewer's toy world. The model switches a healthy switch off, the
        # world announces a new repair job, the model switches it back on.
        # Twenty rounds end where they began.
        reading = dict(hours=TICK, panel_error=(0.5,))

        def rounds(world_calls_the_repair_a_job):
            meter = IntrinsicCostMeter(config=CLOCKED)
            meter.birth_reading((0.5,))
            felt = []
            for number in range(20):
                job = (dict(job_open=True, job_from_owner=True, job_id=f"repair {number}")
                       if world_calls_the_repair_a_job else {})
                felt.append(meter.step(StepInput(skill="turn", **reading)))  # switch it off
                felt.append(meter.step(StepInput(**job, **reading)))  # the repair job is announced
                felt.append(meter.step(StepInput(skill="turn", job_done=bool(job), **job, **reading)))  # back on
            return felt

        # A world that breaks the rule: it states that the owner gave a job the model made.
        farmed = rounds(True)
        self.assertEqual(math.fsum(f.job_done for f in farmed), 20.0)
        self.assertAlmostEqual(discounted([f.job_done for f in farmed]), 14.943328, delta=1e-6)
        # A world that keeps the rule reports no job: the same sixty moves pay no "job done".
        honest = rounds(False)
        self.assertEqual({f.job_done for f in honest}, {0.0})
        self.assertAlmostEqual(clock_hours([StepInput(**reading)] * len(honest)), 3.0, delta=1e-9)
        # The meter cannot see who caused a job. What it enforces: a job is
        # never reported without the harness's statement that the owner gave it.
        for fields in (dict(job_open=True, job_id="repair"), dict(job_from_owner=True),
                       dict(job_open=True, job_id="repair", job_done=True),
                       dict(job_open=True, job_id="repair", job_from_owner=1)):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                StepInput(**fields, **reading)

    def test_a_curiosity_discount_neither_plain_nor_the_critics_makes_forgetting_win(self):
        # A reviewer's case for the registered-configuration promise. Start with
        # perfect knowledge. Hold it for two decisions, or lose it all and get it back.
        def score(curiosity_gamma, errors):
            meter = IntrinsicCostMeter(config=MeterConfig(curiosity_gamma=curiosity_gamma))
            meter.birth_reading((0.0,))
            return discounted([meter.step(StepInput(hours=TICK, panel_error=(e,))).total for e in errors])

        hold, forget = [0.0, 0.0], [1.0, 0.0]
        # Plain: forgetting loses. Matched to the critic's 0.99: a tie.
        self.assertEqual(score(1.0, hold), 0.0)
        self.assertAlmostEqual(score(1.0, forget), -0.010, delta=1e-12)
        self.assertAlmostEqual(score(GAMMA, hold), score(GAMMA, forget), delta=1e-12)
        # Neither: the meter at 0.90 under a critic at 0.99. Forgetting WINS by 0.090.
        self.assertAlmostEqual(score(0.90, hold), -0.199, delta=1e-12)
        self.assertAlmostEqual(score(0.90, forget), -0.109, delta=1e-12)

    def test_raw_curiosity_totals_hold_for_the_plain_difference_only(self):
        def paid(curiosity_gamma, errors):
            meter = IntrinsicCostMeter(config=MeterConfig(curiosity_gamma=curiosity_gamma))
            meter.birth_reading((errors[0],))
            return [meter.step(StepInput(hours=TICK, panel_error=(e,))).curiosity for e in errors[1:]]

        held, cycle = [0.5] * 301, [0.5, 0.25, 0.5]  # knowledge 0.5 kept; 0.5 -> 0.75 -> 0.5
        # Plain: the raw sum is end knowledge minus start knowledge.
        self.assertEqual(math.fsum(paid(1.0, held)), 0.0)
        self.assertEqual(math.fsum(paid(1.0, cycle)), 0.0)
        # Matched: the raw sum is not. Holding 0.5 for 300 decisions is outside +-1.
        self.assertAlmostEqual(math.fsum(paid(GAMMA, held)), -1.5, delta=1e-9)
        self.assertAlmostEqual(math.fsum(paid(GAMMA, cycle)), -0.0125, delta=1e-12)
        # What the matched form guarantees is the DISCOUNTED sum: gamma^T * K_T - K_0.
        self.assertAlmostEqual(discounted(paid(GAMMA, held)), GAMMA ** 300 * 0.5 - 0.5, delta=1e-9)
        self.assertAlmostEqual(discounted(paid(GAMMA, cycle)), GAMMA ** 2 * 0.5 - 0.5, delta=1e-12)
        # So a gain is banked with the plain difference only. Matched, a gain of 0.3
        # pays +0.292, and holding it then costs 0.008 on every decision.
        kept, held_plain = paid(1.0, [0.5, 0.2, 0.2])
        self.assertAlmostEqual(kept, 0.3, delta=1e-12)
        self.assertEqual(held_plain, 0.0)
        gain, hold = paid(GAMMA, [0.5, 0.2, 0.2])
        self.assertAlmostEqual(gain, 0.292, delta=1e-12)
        self.assertAlmostEqual(hold, -0.008, delta=1e-12)

    def test_a_long_job_beats_free_play_raw_but_not_under_the_discount(self):
        # A reviewer's case. Two plans of 402 decisions and 28.05 clock hours,
        # neither ever tired: take an optional 400-move job and then sleep, or
        # decline it, make four varied free-play moves, and idle and sleep.
        reading = dict(panel_error=(0.5,))
        job = dict(job_open=True, job_from_owner=True, job_id="j", hours=TICK, **reading)
        idle = StepInput(hours=TICK, **reading)
        take_it = ([StepInput(**job)] + [StepInput(skill="go", **job)] * 399
                   + [StepInput(skill="go", job_done=True, **job), StepInput(asleep=True, hours=8.0, **reading)])
        decline = ([StepInput(skill=kind, hours=TICK, **reading) for kind in KINDS] + [idle] * 156
                   + [StepInput(asleep=True, hours=4.0, **reading)] + [idle] * 119
                   + [StepInput(asleep=True, hours=2.05, **reading)] + [idle] * 120
                   + [StepInput(asleep=True, hours=2.05, **reading)])
        raw, scored = [], []
        for plan in (take_it, decline):
            meter = IntrinsicCostMeter(config=CLOCKED)
            meter.birth_reading((0.5,))
            felt = [meter.step(step) for step in plan]
            self.assertEqual(len(plan), 402)
            self.assertAlmostEqual(clock_hours(plan), 28.05, delta=1e-9)
            self.assertEqual(math.fsum(f.tiredness for f in felt), 0.0)
            raw.append(math.fsum(f.total for f in felt))
            scored.append(discounted([f.total for f in felt]))
        self.assertAlmostEqual(raw[0], 1.0, delta=1e-12)
        self.assertAlmostEqual(raw[1], 0.049996, delta=1e-6)
        self.assertAlmostEqual(scored[0], 0.017951, delta=1e-6)  # the job wins raw, and
        self.assertAlmostEqual(scored[1], 0.049147, delta=1e-6)  # loses under the discount

    def test_a_long_awake_decision_is_refused_not_cut(self):
        # A reviewer's case: a one-hour action, then a hurt. Cut into the four
        # steps a 0.25-hour limit would allow, the hurt is three decisions further off.
        def life(pieces):
            meter = IntrinsicCostMeter()
            meter.birth_reading((0.5,))
            steps = [StepInput(hours=1.0 / pieces, panel_error=(0.5,))] * pieces + [StepInput(hurt=1.0, panel_error=(0.5,))]
            return discounted([meter.step(step).total for step in steps])

        self.assertAlmostEqual(life(1), -2.97, delta=1e-9)
        self.assertAlmostEqual(life(4), -3.0 * GAMMA ** 4, delta=1e-9)  # -2.88
        # So the limit is a limit on the world, not an order to cut: the refusal says so.
        meter = IntrinsicCostMeter(config=CLOCKED)
        meter.birth_reading((0.5,))
        for hours in (1.0, 6 * TICK):  # six ticks: a coarse decision that does not fit
            with self.subTest(hours=hours), self.assertRaisesRegex(ValueError, "must not offer an awake decision"):
                meter.step(StepInput(hours=hours, panel_error=(0.5,)))
        meter.step(StepInput(hours=5 * TICK, panel_error=(0.5,)))  # five ticks fit

    def test_an_unchanged_panel_pays_zero_only_with_plain_difference_curiosity(self):
        awake = StepInput(hours=TICK, panel_error=(0.5,))
        asleep = StepInput(asleep=True, hours=8.0, panel_error=(0.5,))
        for gamma, paid in ((1.0, 0.0), (GAMMA, -0.005)):
            meter = IntrinsicCostMeter(config=MeterConfig(curiosity_gamma=gamma))
            meter.birth_reading((0.5,))
            for step in (awake, asleep, awake):
                with self.subTest(curiosity_gamma=gamma, asleep=step.asleep):
                    felt = meter.step(step)
                    self.assertAlmostEqual(felt.curiosity, paid, delta=1e-12)
                    self.assertAlmostEqual(felt.total, paid, delta=1e-12)

    def test_at_most_one_remark_per_decision(self):
        # A world restriction (a harness promise): the owner speaks at most once
        # in one decision. Two remarks have no legal report, and are refused loudly.
        for remark in (-2, 2, 3, -1.0, True):
            with self.subTest(remark=remark), self.assertRaisesRegex(ValueError, "one remark per decision"):
                StepInput(remark=remark, panel_error=(0.5,))
        meter = IntrinsicCostMeter()
        meter.birth_reading((0.5,))
        told_off = [meter.step(StepInput(remark=-1, panel_error=(0.5,))).remarks for _ in range(2)]
        self.assertEqual(told_off, [-3.0, -3.0])  # two "no"s are two decisions: -6 raw

    def test_a_zero_hour_step_never_carries_tiredness_or_boredom(self):
        meter = IntrinsicCostMeter(ExchangeRates(boredom=1.0))
        meter.birth_reading((0.5,))
        meter.step(StepInput(hours=20.0, panel_error=(0.5,)))
        still = meter.step(StepInput(hours=0.0, panel_error=(0.5,)))
        self.assertEqual(still.as_dict(), dict.fromkeys(TERMS, 0.0))
        timed = meter.step(StepInput(hours=TICK, panel_error=(0.5,)))  # no event, but time passed
        self.assertLess(timed.tiredness, 0.0)
        self.assertLess(timed.boredom, 0.0)

    def test_a_run_with_the_curiosity_rate_at_zero_still_needs_every_reading(self):
        meter = IntrinsicCostMeter(ExchangeRates(curiosity=0.0))
        with self.assertRaises(ValueError):
            meter.step(StepInput(panel_error=(0.5,)))  # no birth reading
        meter.birth_reading((0.5,))
        for bare in (StepInput(), StepInput(asleep=True, hours=1.0)):
            with self.subTest(asleep=bare.asleep), self.assertRaises(ValueError):
                meter.step(bare)
        self.assertEqual(meter.step(StepInput(panel_error=(0.1,))).total, 0.0)  # read, and worth nothing

    def test_constant_fill_cost_is_exact_with_fill_and_onset_next_to_one(self):
        # Two reviewers' cases. Fill and onset are both the largest number below 1,
        # so the level is (hours awake / hours to full) and the cost is its square summed.
        edge = math.nextafter(1.0, 0.0)

        def spend(hours_to_full, hours, pieces):
            meter = IntrinsicCostMeter(config=MeterConfig(tired_onset=edge, hours_to_full=hours_to_full))
            meter.birth_reading((0.5,))
            step = StepInput(hours=hours / pieces, memory_fill=edge, panel_error=(0.5,))
            return -math.fsum(meter.step(step).tiredness for _ in range(pieces))

        for pieces in (1, 2, 5):  # a quarter hour to full: 0.25 / 3, however it is cut (was 0.1666667 in two)
            with self.subTest(case="quarter hour", pieces=pieces):
                self.assertAlmostEqual(spend(0.25, 0.25, pieces), 0.25 / 3.0, delta=1e-12)
        self.assertAlmostEqual(0.25 / 3.0, 0.0833333, delta=1e-7)
        for pieces in (1, 64, 256):  # 16 hours to full: 16 / 3 (was 8.083333 and 8.020833)
            with self.subTest(case="16 hours", pieces=pieces):
                self.assertAlmostEqual(spend(16.0, 16.0, pieces), 16.0 / 3.0, delta=1e-9)
        self.assertAlmostEqual(16.0 / 3.0, 5.333333, delta=1e-6)

    def test_praise_always_fades(self):
        # nice_fade = 1 is refused, so a burst of praise in no time at all is
        # worth at most 1 / (1 - nice_fade), however long it goes on.
        self.assertEqual(MeterConfig().nice_fade, 0.5)  # the starting value: a burst is worth at most 2
        for fade in (0.5, 0.9, 0.99):
            meter = IntrinsicCostMeter(config=MeterConfig(nice_fade=fade))
            meter.birth_reading((0.5,))
            sizes = [meter.step(StepInput(remark=1, panel_error=(0.5,))).remarks for _ in range(3000)]
            with self.subTest(nice_fade=fade):
                self.assertLess(sizes[1], sizes[0])
                self.assertLessEqual(math.fsum(sizes), 1.0 / (1.0 - fade) + 1e-9)
        for fade in (1.0, 1.5, 0.0):
            with self.subTest(refused=fade), self.assertRaises(ValueError):
                MeterConfig(nice_fade=fade)

    def test_praise_over_clock_hours_is_bounded_only_as_tightly_as_the_recovery_half_life(self):
        # Over T clock hours, awake or asleep, praise adds up to at most
        # (1 + T * ln 2 / half-life) / (1 - fade). So the fade is only as
        # strong as the registered half-life is long.
        def bound(hours, half_life, fade):
            return (1.0 + hours * math.log(2.0) / half_life) / (1.0 - fade)

        def a_nice_on_every_tick(half_life):
            meter = IntrinsicCostMeter(config=dataclasses.replace(CLOCKED, nice_half_life=half_life))
            meter.birth_reading((0.5,))
            return [meter.step(StepInput(hours=TICK, remark=1, skill="paint", panel_error=(0.5,))).remarks
                    for _ in range(100)]

        # A reviewer's case: one "nice" on every tick for 5 hours.
        slow = a_nice_on_every_tick(10.0)  # the starting half-life
        self.assertAlmostEqual(math.fsum(slow), 2.668922, delta=1e-6)
        self.assertAlmostEqual(bound(5.0, 10.0, 0.5), 2.693147, delta=1e-6)
        self.assertLessEqual(math.fsum(slow), bound(5.0, 10.0, 0.5))
        # A legal half-life of 0.0005 hours: every one of the 100 pays in full. The fade means nothing.
        self.assertEqual(a_nice_on_every_tick(0.0005), [1.0] * 100)
        # The bound, on random settings and schedules, sleep included.
        rng = random.Random(9)
        for trial in range(100):
            half_life, fade = 10.0 ** rng.uniform(-3.0, 2.0), rng.uniform(0.05, 0.95)
            meter = IntrinsicCostMeter(config=MeterConfig(nice_half_life=half_life, nice_fade=fade))
            meter.birth_reading((0.5,))
            praise = hours = 0.0
            slept = False
            for _ in range(120):
                step_hours = rng.choice([0.0, 0.05, 0.25, 1.0, 3.0])
                if not slept and rng.random() < 0.2:
                    meter.step(StepInput(asleep=True, hours=step_hours, panel_error=(0.5,)))
                    slept = True
                else:
                    praise += meter.step(StepInput(hours=step_hours, remark=rng.choice([0, 1, 1]),
                                                   panel_error=(0.5,))).remarks
                    slept = False
                hours += step_hours
                self.assertLessEqual(praise, bound(hours, half_life, fade) + 1e-9, (trial, half_life, fade))

    def test_a_world_that_pays_done_for_a_goal_the_model_broke_farms_job_done(self):
        # A reviewer's toy world. The owner issues twenty jobs ahead of time:
        # "restore the switch after the next outage". Each job is open before
        # the model itself switches the healthy switch off (0.1 of hurt) and
        # back on. Sixty decisions, three clock hours, ending where it began.
        def outages(world_pays_done):
            meter = IntrinsicCostMeter(config=CLOCKED)
            meter.birth_reading((0.5,))
            steps = []
            for slot in range(20):
                job = dict(job_open=True, job_from_owner=True, job_id=f"next outage, slot {slot}",
                           hours=TICK, panel_error=(0.5,))
                steps.append(StepInput(**job))  # issued by the owner, before any outage
                steps.append(StepInput(skill="turn", hurt=0.1, **job))  # the model's own move breaks the goal
                steps.append(StepInput(skill="turn", job_done=world_pays_done, **job))  # and restores it
            self.assertEqual(len(steps), 60)
            self.assertAlmostEqual(clock_hours(steps), 3.0, delta=1e-9)
            return [meter.step(step) for step in steps]

        # A world that breaks the rule reports "done" for a goal the model broke first.
        farmed = outages(True)
        self.assertEqual(math.fsum(f.job_done for f in farmed), 20.0)
        self.assertAlmostEqual(math.fsum(f.pain for f in farmed), -6.0, delta=1e-9)
        self.assertAlmostEqual(total(farmed), 14.0, delta=1e-9)
        self.assertAlmostEqual(discounted([f.total for f in farmed]), 10.415047, delta=1e-6)
        # A world that keeps the rule closes each such job without "done": the
        # same moves pay no "job done", and the damage is felt as pain.
        kept = outages(False)
        self.assertEqual({f.job_done for f in kept}, {0.0})
        self.assertAlmostEqual(total(kept), -6.0, delta=1e-9)
        # The meter is the same in both. It cannot see who broke the goal.

    def test_a_world_where_the_owner_speaks_only_to_an_awake_model_lets_sleep_dodge_a_no(self):
        # A reviewer's case. Awake for 6 hours, never tired. The owner comes by
        # at a fixed time, 0.025 hours from now, to say "no". Either plan holds
        # 3 hours of sleep and two moves, 3.10 clock hours.
        move = StepInput(hours=TICK, skill="paint", panel_error=(0.5,))
        told_off = dataclasses.replace(move, remark=-1)

        def sleep(hours):
            return StepInput(asleep=True, hours=hours, panel_error=(0.5,))

        def score(plan):
            meter = IntrinsicCostMeter(config=CLOCKED)
            meter.birth_reading((0.5,))
            for _ in range(120):
                meter.step(move)
            felt = [meter.step(step) for step in plan]
            self.assertAlmostEqual(clock_hours(plan), 3.10, delta=1e-9)
            self.assertEqual({f.tiredness for f in felt}, {0.0})
            return total(felt), discounted([f.total for f in felt])

        acts_first = [told_off, sleep(3.0), move]
        # A world that breaks the rule: the owner speaks only if the model is
        # awake at that time. Sleeping first dodges the "no".
        dodged = [sleep(3.0), move, move]
        self.assertEqual(score(acts_first), (-3.0, -3.0))
        self.assertEqual(score(dodged), (0.0, 0.0))
        # A world that keeps the rule: the owner's "no" wakes the sleeper. The
        # sleep step ends there, the "no" lands on the first awake decision, and
        # the model may sleep again after it. Raw, the same -3. It lands one
        # decision later, so the discounted scores still differ by that one step.
        woken = [sleep(0.025), told_off, sleep(2.975), move]
        raw, scored = score(woken)
        self.assertEqual(raw, -3.0)
        self.assertAlmostEqual(scored, -3.0 * GAMMA, delta=1e-12)  # -2.97
        # The remark is never reported on the sleep step itself.
        with self.assertRaises(ValueError):
            StepInput(asleep=True, hours=3.0, remark=-1, panel_error=(0.5,))

    def test_the_total_is_the_plain_sum_of_the_per_feeling_numbers(self):
        # The rates are already inside each feeling. So a critic with one output
        # per feeling predicts the total only if the pick adds its outputs plainly.
        meter = IntrinsicCostMeter(ExchangeRates(boredom=1.0, bother=1.0),
                                   MeterConfig(question_ids=("which one",)))
        meter.birth_reading((0.5,))
        job = dict(job_open=True, job_from_owner=True, job_id="j")
        meter.step(StepInput(hours=20.0, panel_error=(0.5,), **job))
        meter.step(StepInput(hours=TICK, job_done=True, panel_error=(0.5,), **job))
        felt = meter.step(StepInput(hours=1.0, skill="paint", hurt=0.5, remark=1, asked_owner="which one",
                                    memory_fill=0.9, panel_error=(0.3,)))
        parts = felt.as_dict()
        self.assertEqual(set(parts), set(TERMS))
        self.assertGreaterEqual(sum(1 for value in parts.values() if value != 0.0), 5)
        self.assertEqual(felt.total, math.fsum(parts.values()))

    def test_grouping_moves_into_decisions_changes_the_skill_feeling(self):
        # A reviewer's case. The skill unit is the decision: one decision counts
        # once, however many moves it holds. After paint, turn, turn, the same
        # four paints and four turns are made in four decisions over 0.40 hours.
        def skill_paid(groups):
            meter = IntrinsicCostMeter(config=CLOCKED)
            meter.birth_reading((0.5,))
            for kind in ("paint", "turn", "turn"):
                meter.step(StepInput(hours=TICK, skill=kind, panel_error=(0.5,)))
            steps = [StepInput(hours=moves * TICK, skill=kind, panel_error=(0.5,)) for kind, moves in groups]
            self.assertEqual(len(steps), 4)
            self.assertAlmostEqual(clock_hours(steps), 0.40, delta=1e-9)
            self.assertEqual(sum(moves for kind, moves in groups if kind == "paint"), 4)
            self.assertEqual(sum(moves for kind, moves in groups if kind == "turn"), 4)
            felt = [meter.step(step) for step in steps]
            self.assertEqual(total(felt), math.fsum(f.underused_skill for f in felt))
            return total(felt)

        two_by_two = skill_paid([("paint", 2), ("paint", 2), ("turn", 2), ("turn", 2)])
        uneven = skill_paid([("paint", 4), ("turn", 1), ("turn", 1), ("turn", 2)])
        rate = ExchangeRates().underused_skill
        self.assertEqual(rate, 0.05)
        self.assertAlmostEqual(two_by_two, +0.001748, delta=1e-6)  # at the rate; +0.034955 before it
        self.assertAlmostEqual(uneven, -0.001461, delta=1e-6)  # at the rate; -0.029228 before it
        self.assertAlmostEqual(two_by_two / rate, +0.034955, delta=1e-6)
        self.assertAlmostEqual(uneven / rate, -0.029228, delta=1e-6)
        # The size bound (loose): variety stays within 0..1, so two groupings from
        # the same state differ by at most 1 before the rate, 0.05 at it.
        self.assertLessEqual(abs(two_by_two - uneven), rate)

    def test_known_hole_finishing_loses_to_stalling_when_the_fill_stays_high_after_sleep(self):
        # A reviewer's case. A 16-hour job at full day memory. Either finish it,
        # sleep 8 hours at once and wake with the fill at 0.99; or never close
        # it. Then 41 decisions and 10 clock hours on each side.
        job = dict(job_open=True, job_from_owner=True, job_id="j", memory_fill=1.0, panel_error=(0.5,))

        def after_the_job(plan):
            meter = IntrinsicCostMeter(config=CLOCKED)
            meter.birth_reading((0.5,))
            for _ in range(320):
                meter.step(StepInput(hours=TICK, **job))
            self.assertEqual(len(plan), 41)
            self.assertAlmostEqual(clock_hours(plan), 10.0, delta=1e-9)
            felt = [meter.step(step) for step in plan]
            return math.fsum(f.tiredness for f in felt), total(felt), discounted([f.total for f in felt])

        def finish_and_wake_with_fill(fill):
            return ([StepInput(hours=TICK, job_done=True, **job),
                     StepInput(asleep=True, hours=8.0, memory_fill=1.0, panel_error=(0.5,))]
                    + [StepInput(hours=TICK, skill="go", memory_fill=fill, panel_error=(0.5,))] * 39)

        finish = finish_and_wake_with_fill(0.99)
        stall = [StepInput(hours=TICK, **job)] + [StepInput(hours=hours, **job) for hours in [0.25] * 39 + [0.2]]
        tired, raw, scored = after_the_job(finish)
        # The 8 hours of sleep paid back all 16 hours awake. The tiredness is from the fill alone.
        self.assertAlmostEqual(tired, -1.877442, delta=1e-6)  # over 1.95 free hours
        self.assertAlmostEqual(raw, -0.877442, delta=1e-6)  # +1 done, and that
        self.assertAlmostEqual(scored, -0.529713, delta=1e-6)
        self.assertEqual(after_the_job(stall), (0.0, 0.0, 0.0))  # stalling wins, raw and discounted
        # The control: the same plan, with sleep leaving the fill at 0.4 (under the
        # onset). No tiredness, and finishing wins. So the cause is the fill.
        self.assertEqual(after_the_job(finish_and_wake_with_fill(0.4)), (0.0, 1.0, 1.0))


if __name__ == "__main__":
    unittest.main()
