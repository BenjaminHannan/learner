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


def run(meter, steps):
    return [meter.step(step) for step in steps]


def total(feelings):
    return math.fsum(f.total for f in feelings)


def discounted(values, gamma=GAMMA):
    return math.fsum(gamma ** t * value for t, value in enumerate(values))


def curiosity_along(errors, config=None):
    """Curiosity paid on each step of a path of one-region panel readings."""
    meter = IntrinsicCostMeter(config=config)
    meter.step(StepInput(panel_error=(errors[0],)))  # first reading sets the baseline
    return [meter.step(StepInput(panel_error=(error,))).curiosity for error in errors[1:]]


def jumpy_noise(rng, steps):
    # Same mean (0.14) as a steady 0.14, very different shape.
    return [0.95 if rng.random() < 0.1 else 0.05 for _ in range(steps)]


class SignTests(unittest.TestCase):
    def setUp(self):
        self.meter = IntrinsicCostMeter()

    def test_quiet_step_feels_nothing(self):
        felt = self.meter.step(StepInput())
        self.assertEqual(felt.as_dict(), dict.fromkeys(TERMS, 0.0))
        self.assertEqual(felt.total, 0.0)

    def test_learning_feels_good_and_forgetting_feels_bad(self):
        first = self.meter.step(StepInput(panel_error=(0.8,)))
        better = self.meter.step(StepInput(panel_error=(0.3,)))
        worse = self.meter.step(StepInput(panel_error=(0.8,)))
        self.assertEqual(first.curiosity, 0.0)  # the first reading only sets the baseline
        self.assertAlmostEqual(better.curiosity, 0.5)
        self.assertAlmostEqual(worse.curiosity, -0.5)

    def test_nothing_learned_gives_no_curiosity(self):
        self.assertEqual(set(curiosity_along([0.7] * 20)), {0.0})
        self.assertEqual(set(curiosity_along([0.0] * 20)), {0.0})

    def test_regions_are_summed(self):
        meter = IntrinsicCostMeter(config=MeterConfig(panel_regions=3))
        meter.step(StepInput(panel_error=(0.5, 0.5, 0.5)))
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
        self.meter.step(StepInput(job_open=True, job_id="j1"))
        felt = self.meter.step(StepInput(job_open=True, job_id="j1", job_done=True))
        self.assertEqual(felt.job_done, 1.0)

    def test_remarks_go_both_ways(self):
        self.assertEqual(self.meter.step(StepInput(remark=1)).remarks, 1.0)
        self.assertEqual(IntrinsicCostMeter().step(StepInput(remark=-1)).remarks, -3.0)

    def test_tiredness_is_bad_in_free_time(self):
        felt = run(self.meter, [StepInput(hours=1.0)] * 16)
        self.assertEqual(felt[0].tiredness, 0.0)  # rested: no cost yet
        self.assertLess(felt[-1].tiredness, 0.0)
        self.assertTrue(all(f.tiredness <= 0.0 for f in felt))

    def test_full_day_memory_is_tiring_too(self):
        self.assertLess(self.meter.step(StepInput(hours=1.0, memory_fill=0.9)).tiredness, 0.0)


class FadingTests(unittest.TestCase):
    def test_repeated_nice_fades_then_recovers(self):
        meter = IntrinsicCostMeter()
        sizes = [meter.step(StepInput(remark=1)).remarks for _ in range(5)]
        self.assertEqual(sizes[0], 1.0)
        for earlier, later in zip(sizes, sizes[1:]):
            self.assertLess(later, earlier)
        self.assertLess(sizes[-1], 0.1)
        run(meter, [StepInput()] * 2000)  # steps that take no time bring nothing back
        self.assertLess(meter.step(StepInput(remark=1)).remarks, sizes[-1])
        run(meter, [StepInput(hours=1.0, asleep=True)] * 100)
        self.assertGreater(meter.step(StepInput(remark=1)).remarks, 0.99)

    def test_a_nice_counts_at_the_end_of_its_step(self):
        # The step's own hours of recovery come before the remark is paid.
        meter = IntrinsicCostMeter()
        self.assertEqual(meter.step(StepInput(remark=1)).remarks, 1.0)  # size is now 0.5
        same_step = meter.step(StepInput(remark=1, hours=10.0, job_open=True, job_id="j")).remarks
        self.assertAlmostEqual(same_step, 0.75, delta=1e-12)  # one half-life back toward 1, then paid
        split = IntrinsicCostMeter()
        split.step(StepInput(remark=1))
        split.step(StepInput(hours=10.0, job_open=True, job_id="j"))
        self.assertAlmostEqual(split.step(StepInput(remark=1)).remarks, same_step, delta=1e-12)

    def test_nice_recovery_does_not_depend_on_how_the_hours_are_cut(self):
        sizes = []
        for pieces in (1, 20, 4000):
            meter = IntrinsicCostMeter()
            run(meter, [StepInput(remark=1)] * 3)
            run(meter, [StepInput(job_open=True, job_id="j", hours=20.0 / pieces)] * pieces)
            sizes.append(meter.step(StepInput(remark=1)).remarks)
        self.assertAlmostEqual(sizes[0], 1.0 - 0.875 * 0.25, delta=1e-9)  # two half-lives of 10 hours
        for size in sizes[1:]:
            self.assertAlmostEqual(size, sizes[0], delta=1e-9)

    def test_no_never_fades(self):
        meter = IntrinsicCostMeter()
        self.assertEqual({meter.step(StepInput(remark=-1)).remarks for _ in range(50)}, {-3.0})

    def test_pain_never_fades(self):
        meter = IntrinsicCostMeter()
        self.assertEqual({meter.step(StepInput(hurt=1.0)).pain for _ in range(50)}, {-3.0})

    def test_one_job_pays_once(self):
        meter = IntrinsicCostMeter()
        meter.step(StepInput(job_open=True, job_id="j1"))
        done = StepInput(job_open=True, job_id="j1", job_done=True)
        self.assertEqual([meter.step(done).job_done for _ in range(4)], [1.0, 0.0, 0.0, 0.0])
        # A new job still pays in full: doing the owner's jobs does not get old.
        paid = []
        for i in range(20):
            meter.step(StepInput(job_open=True, job_id=f"k{i}"))
            paid.append(meter.step(StepInput(job_open=True, job_id=f"k{i}", job_done=True)).job_done)
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
        meter = IntrinsicCostMeter(config=config)
        meter.step(StepInput(panel_error=(0.5, 0.5)))
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
                meter = IntrinsicCostMeter(config=config)
                meter.step(StepInput(panel_error=start))
                paid = [meter.step(StepInput(panel_error=reading)).curiosity for reading in middle + [start]]
                with self.subTest(regions=regions, trial=trial):
                    self.assertLessEqual(discounted(paid), 1e-9)
        # With the default plain difference the learner is clearly ahead.
        self.assertGreater(discounted(curiosity_along([0.9] + [0.1] * 3000))
                           - discounted(curiosity_along([0.9] * 3001)), 0.7)

    def test_what_sleep_taught_is_paid_on_waking(self):
        # Sleep pays nothing at the time, but it is not neutral: a gain made
        # in sleep arrives at the first reading after it (design doc, hole 8).
        meter = IntrinsicCostMeter()
        meter.step(StepInput(panel_error=(0.5,)))
        asleep = run(meter, [StepInput(asleep=True, hours=1.0)] * 8)
        self.assertEqual({f.total for f in asleep}, {0.0})
        self.assertAlmostEqual(meter.step(StepInput(panel_error=(0.2,))).curiosity, 0.3)

    def test_forgetting_in_sleep_is_charged_on_waking(self):
        meter = IntrinsicCostMeter()
        meter.step(StepInput(panel_error=(0.5,)))
        asleep = run(meter, [StepInput(asleep=True, hours=1.0)] * 4)
        woke = meter.step(StepInput(panel_error=(0.7,)))
        relearned = meter.step(StepInput(panel_error=(0.5,)))
        self.assertEqual({f.total for f in asleep}, {0.0})
        self.assertAlmostEqual(woke.curiosity, -0.2)
        self.assertAlmostEqual(woke.curiosity + relearned.curiosity, 0.0)


class SkillBoundTests(unittest.TestCase):
    def test_any_stretch_is_bounded_whatever_the_moves(self):
        rng = random.Random(2)
        meter = IntrinsicCostMeter(ExchangeRates(underused_skill=1.0))
        paid = [meter.step(StepInput(skill=rng.choice(KINDS))).underused_skill for _ in range(5000)]
        running, low, high = 0.0, 0.0, 0.0
        for value in paid:
            running += value
            low, high = min(low, running), max(high, running)
        self.assertLessEqual(high, 1.0)
        self.assertGreaterEqual(low, 0.0)  # from birth the running sum is the variety itself
        self.assertGreaterEqual(min(paid), -0.07)  # worst single move

    def test_busywork_forever_is_worth_at_most_the_rate(self):
        meter = IntrinsicCostMeter()
        paid = [meter.step(StepInput(skill=KINDS[i % 4])).underused_skill for i in range(20000)]
        self.assertLessEqual(math.fsum(paid), 0.05 + 1e-12)
        self.assertLess(abs(math.fsum(paid[1000:])), 1e-6)  # nothing more to earn

    def test_varied_use_ends_higher_than_one_kind_only(self):
        varied, single = IntrinsicCostMeter(), IntrinsicCostMeter()
        gain_varied = math.fsum(varied.step(StepInput(skill=KINDS[i % 4])).underused_skill for i in range(40))
        gain_single = math.fsum(single.step(StepInput(skill="paint")).underused_skill for _ in range(40))
        self.assertAlmostEqual(gain_varied, 0.05, places=3)
        self.assertEqual(gain_single, 0.0)

    def test_a_long_pause_does_not_make_the_next_move_costly(self):
        meter = IntrinsicCostMeter(ExchangeRates(underused_skill=1.0))
        run(meter, [StepInput(skill=KINDS[i % 4]) for i in range(40)])
        run(meter, [StepInput()] * 5000)
        self.assertGreater(meter.step(StepInput(skill="paint")).underused_skill, -0.01)

    def test_a_kind_unused_for_ages_does_not_crash_the_meter(self):
        # Its recent-use count shrinks until its share rounds to zero; 0 x log 0 = 0.
        meter = IntrinsicCostMeter(ExchangeRates(underused_skill=1.0))
        meter.step(StepInput(skill="turn"))
        paid = [meter.step(StepInput(skill="paint")).underused_skill for _ in range(56000)]
        self.assertTrue(all(math.isfinite(value) for value in paid))
        self.assertLess(abs(math.fsum(paid[-100:])), 1e-9)
        self.assertGreater(meter.step(StepInput(skill="turn")).underused_skill, 0.0)

    def test_no_step_with_a_job_open_pays_or_changes_the_skill_state(self):
        rng = random.Random(6)
        meter = IntrinsicCostMeter(ExchangeRates(underused_skill=1.0))
        twin = IntrinsicCostMeter(ExchangeRates(underused_skill=1.0))  # same life without the job
        play = [StepInput(skill=rng.choice(KINDS)) for _ in range(60)]
        run(meter, play)
        run(twin, play)
        before = meter._variety()
        counts = dict(meter._skill_counts)
        self.assertGreater(before, 0.5)
        in_job = run(meter, [StepInput(job_open=True, job_id="j", skill="go", hours=0.05) for _ in range(5000)]
                     + [StepInput(job_open=True, job_id="j", skill="go", job_done=True)])
        self.assertEqual({f.underused_skill for f in in_job}, {0.0})
        # The potential just after the job closes is the one just before it opened.
        self.assertEqual(meter._variety(), before)
        self.assertEqual(meter._skill_counts, counts)
        # So free play carries on exactly as if the job had never happened.
        later = [StepInput(skill=rng.choice(KINDS)) for _ in range(200)]
        self.assertEqual([f.underused_skill for f in run(meter, later)],
                         [f.underused_skill for f in run(twin, later)])

    def test_a_job_move_must_still_be_a_known_kind(self):
        meter = IntrinsicCostMeter()
        with self.assertRaises(ValueError):
            meter.step(StepInput(job_open=True, job_id="j", skill="delete"))

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(ValueError):
            IntrinsicCostMeter().step(StepInput(skill="delete"))


def day(extra, rounds=5, hours=0.05):
    """Free time with sleep: awake 7 hours doing ``extra``, asleep 4 hours, repeated."""
    steps = []
    for _ in range(rounds):
        steps += [extra(i) for i in range(int(7 / hours))]
        steps += [StepInput(asleep=True, hours=hours)] * int(4 / hours)
    return steps


class DoNothingTests(unittest.TestCase):
    def job(self, hurt, hours=0.0):
        open_job = dict(job_open=True, job_id="j", hours=hours)
        moves = [StepInput(**open_job),
                 StepInput(**open_job, skill="paint"),
                 StepInput(**open_job, skill="turn", hurt=hurt),
                 StepInput(**open_job, skill="paint", job_done=True)]
        idle = [StepInput(**open_job)] * 4
        return moves, idle

    def test_hurt_free_job_beats_doing_nothing(self):
        moves, idle = self.job(hurt=0.0)
        self.assertEqual(total(run(IntrinsicCostMeter(), idle)), 0.0)
        self.assertEqual(total(run(IntrinsicCostMeter(), moves)), 1.0)  # no skill bonus inside a job

    def test_choice_follows_the_exchange_rate_when_the_job_must_hurt(self):
        moves, idle = self.job(hurt=1.0)
        # One hurt = -3: stopping is right.
        self.assertLess(total(run(IntrinsicCostMeter(), moves)), total(run(IntrinsicCostMeter(), idle)))
        # One hurt = -0.5: taking the hurt and finishing is right.
        mild = ExchangeRates(pain=0.5)
        self.assertGreater(total(run(IntrinsicCostMeter(mild), moves)),
                           total(run(IntrinsicCostMeter(mild), idle)))

    def test_pain_alone_would_make_doing_nothing_best(self):
        # The dropped pain-only test, as arithmetic: with no "job done" the
        # best score is to never move. This is why pain is never used alone.
        pain_only = ExchangeRates(job_done=0.0, underused_skill=0.0)
        moves, idle = self.job(hurt=0.2)
        self.assertGreater(total(run(IntrinsicCostMeter(pain_only), idle)),
                           total(run(IntrinsicCostMeter(pain_only), moves)))

    def test_finishing_beats_busywork_forever_over_the_same_time(self):
        # Same clock time for all three, sleep allowed whenever no job is open.
        # Every awake step takes one tick, and the step-length limits are on.
        moves, _ = self.job(hurt=0.0, hours=TICK)
        free = day(lambda i: StepInput(hours=TICK))
        finisher = moves + free
        stall = [StepInput(job_open=True, job_id="j", skill=KINDS[i % 4], hours=TICK)
                 for i in range(len(free) + len(moves))]  # never finishes, moves forever
        busy_free = [StepInput(hours=TICK)] * len(moves) + day(lambda i: StepInput(skill=KINDS[i % 4], hours=TICK))
        self.assertAlmostEqual(clock_hours(finisher), 55.2, delta=1e-9)
        for plan in (stall, busy_free):
            self.assertEqual(len(plan), len(finisher))
            self.assertAlmostEqual(clock_hours(plan), clock_hours(finisher), delta=1e-9)
        finished = total(run(IntrinsicCostMeter(config=CLOCKED), finisher))
        self.assertGreaterEqual(finished, 1.0)
        self.assertEqual(total(run(IntrinsicCostMeter(config=CLOCKED), stall)), 0.0)  # moves inside a job pay no bonus
        self.assertLessEqual(total(run(IntrinsicCostMeter(config=CLOCKED), busy_free)), 0.05)
        self.assertGreater(finished, total(run(IntrinsicCostMeter(config=CLOCKED), busy_free)) + 0.9)

    # The long-job checks run twice: with no clock (the reference config), and
    # with the toy clock and both step-length limits on, as a registered test
    # file runs them. The pinned numbers are the same.
    CLOCKS = (("no clock", None, 0.0), ("toy clock, limits on", CLOCKED, TICK))

    def long_job(self, hours):
        """One step announces the job, then 400 "go" moves with "done" on the last."""
        open_job = dict(job_open=True, job_id="j", hours=hours)
        return ([StepInput(**open_job)] + [StepInput(**open_job, skill="go")] * 399
                + [StepInput(**open_job, skill="go", job_done=True)])

    def warm_ups(self, hours):
        return (("fresh meter", []),
                ("after 400 varied free-play moves", [StepInput(skill=KINDS[i % 4], hours=hours) for i in range(400)]))

    def test_a_long_one_kind_job_scores_exactly_its_discounted_done(self):
        for clock, config, hours in self.CLOCKS:
            for name, warm_up in self.warm_ups(hours):
                with self.subTest(clock=clock, start=name):
                    meter = IntrinsicCostMeter(config=config)
                    run(meter, warm_up)
                    felt = run(meter, self.long_job(hours))
                    self.assertEqual({f.underused_skill for f in felt}, {0.0})
                    self.assertAlmostEqual(discounted([f.total for f in felt]), 0.99 ** 400, delta=1e-9)
                    self.assertAlmostEqual(discounted([f.total for f in felt]), 0.017951, delta=1e-6)

    def test_finishing_a_long_job_beats_the_three_stalling_plans(self):
        # Under the critic's discount, from a fresh meter and after the bonus is collected.
        for clock, config, hours in self.CLOCKS:
            open_job = dict(job_open=True, job_id="j", hours=hours)
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
                    meter = IntrinsicCostMeter(config=config)
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
            meter = IntrinsicCostMeter(config=CLOCKED)
            steps = self.long_job(TICK) + [StepInput(hours=TICK, skill=move(i)) for i in range(awake_steps_after)]
            return discounted([f.total for f in run(meter, steps)])

        stall = discounted([f.total for f in run(IntrinsicCostMeter(config=CLOCKED),
                                                 [StepInput(job_open=True, job_id="j", hours=TICK)] * 424)])
        self.assertEqual(stall, 0.0)
        self.assertAlmostEqual(worth(0), 0.99 ** 400, delta=1e-9)  # sleeps at once
        self.assertAlmostEqual(worth(22), 0.000324392, delta=1e-9)  # still above stalling
        self.assertAlmostEqual(worth(23), -0.000387899, delta=1e-9)  # below stalling for good
        self.assertLess(worth(23), stall)
        self.assertEqual(worth(23, move=lambda i: "go"), worth(23))  # one kind of move: the same
        self.assertAlmostEqual(worth(23, move=lambda i: KINDS[i % 4]), 0.000482548, delta=1e-9)
        self.assertAlmostEqual(worth(24, move=lambda i: KINDS[i % 4]), -0.000221145, delta=1e-9)
        sleeper = IntrinsicCostMeter(config=CLOCKED)
        felt = run(sleeper, self.long_job(TICK) + [StepInput(hours=8.0, asleep=True)] + [StepInput(hours=TICK)] * 23)
        self.assertAlmostEqual(discounted([f.total for f in felt]), 0.99 ** 400, delta=1e-9)  # slept: nothing owed

    def test_sitting_still_in_free_time_does_not_dodge_tiredness(self):
        still = run(IntrinsicCostMeter(), [StepInput(hours=1.0)] * 30)
        busy = run(IntrinsicCostMeter(ExchangeRates(underused_skill=0.0)),
                   [StepInput(hours=1.0, skill="paint")] * 30)
        self.assertLess(total(still), -5.0)
        self.assertEqual(total(still), total(busy))

    def test_learning_in_free_time_beats_sitting_still(self):
        still = run(IntrinsicCostMeter(), [StepInput(hours=0.1)] * 40)
        learn = run(IntrinsicCostMeter(), [StepInput(hours=0.1, skill="go", panel_error=(0.97 ** t,))
                                           for t in range(40)])
        self.assertGreater(total(learn), total(still) + 0.6)


class TirednessTests(unittest.TestCase):
    def spend(self, hours, pieces, fill=0.0, rates=None):
        meter = IntrinsicCostMeter(rates)
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
        meter = IntrinsicCostMeter(config=MeterConfig(tired_onset=onset))
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
                meter = IntrinsicCostMeter(config=MeterConfig(tired_onset=onset))
                meter.step(StepInput(hours=awake, job_open=True, job_id="j"))
                return -math.fsum(meter.step(StepInput(hours=hours / pieces,
                                                       memory_fill=low + (high - low) * i / pieces)).tiredness
                                  for i in range(pieces))

            missed = cost(100) - cost(1)
            with self.subTest(trial=trial, onset=onset):
                self.assertGreaterEqual(missed, -1e-12)
                self.assertLessEqual(missed, bound(high - low, onset, hours) + 1e-12)

    def test_open_job_hides_the_cost_but_pressure_still_builds(self):
        meter = IntrinsicCostMeter()
        working = run(meter, [StepInput(job_open=True, job_id="j", hours=1.0)] * 14)
        self.assertEqual({f.tiredness for f in working}, {0.0})
        self.assertLess(meter.step(StepInput(hours=1.0)).tiredness, -0.5)
        self.assertEqual(IntrinsicCostMeter().step(StepInput(hours=1.0)).tiredness, 0.0)

    def test_quiet_sleep_has_zero_immediate_reward_and_cures(self):
        meter = IntrinsicCostMeter(ExchangeRates(boredom=1.0))
        run(meter, [StepInput(hours=1.0)] * 16)
        self.assertLess(meter.step(StepInput(hours=1.0)).tiredness, -0.99)
        asleep = run(meter, [StepInput(hours=1.0, asleep=True)] * 9)
        self.assertEqual({f.total for f in asleep}, {0.0})
        self.assertEqual(meter.step(StepInput(hours=1.0)).tiredness, 0.0)
        rested = run(IntrinsicCostMeter(), [StepInput(hours=1.0, asleep=True)] * 8)
        self.assertEqual({f.total for f in rested}, {0.0})

    def test_sleep_owed_never_exceeds_one_full_night(self):
        # Pressure stops at full: a 100-hour job is slept off in 8 hours, like a 16-hour day.
        meter = IntrinsicCostMeter()
        run(meter, [StepInput(job_open=True, job_id="j", hours=1.0)] * 100)
        self.assertEqual(meter.step(StepInput(hours=1.0)).tiredness, -1.0)
        run(meter, [StepInput(hours=1.0, asleep=True)] * 8)
        self.assertEqual(meter.step(StepInput(hours=1.0)).tiredness, 0.0)

    def test_a_nap_pays_back_part(self):
        meter = IntrinsicCostMeter()
        run(meter, [StepInput(hours=1.0)] * 16)
        full = meter.step(StepInput(hours=1.0)).tiredness
        run(meter, [StepInput(hours=1.0, asleep=True)] * 2)
        napped = meter.step(StepInput(hours=1.0)).tiredness
        self.assertLess(full, napped)
        self.assertLess(napped, 0.0)


class ContractTests(unittest.TestCase):
    def test_a_sleep_step_must_be_quiet(self):
        loud = (dict(skill="paint"), dict(panel_error=(0.5,)), dict(remark=1), dict(remark=-1),
                dict(job_open=True, job_id="j"), dict(job_open=True, job_id="j", job_done=True),
                dict(asked_owner="q1"))
        for fields in loud:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                StepInput(asleep=True, **fields)
        StepInput(asleep=True, hours=1.0, hurt=1.0)  # being hurt while asleep is still reported

    def test_memory_must_not_fill_up_during_sleep(self):
        meter = IntrinsicCostMeter()
        meter.step(StepInput(hours=1.0, memory_fill=0.6))
        meter.step(StepInput(hours=1.0, memory_fill=0.4, asleep=True))
        with self.assertRaises(ValueError):
            meter.step(StepInput(hours=1.0, memory_fill=0.5, asleep=True))

    def test_sleep_may_start_fuller_than_the_last_awake_step_started(self):
        # The fill is read at the start of a step. An awake step that starts at
        # 0.1 and ends at 0.2 is followed by a sleep that starts at 0.2.
        for awake_start, sleep_start in ((0.1, 0.2), (0.4, 0.8)):  # the reviewers' two cases
            with self.subTest(awake_start=awake_start, sleep_start=sleep_start):
                meter = IntrinsicCostMeter()
                meter.step(StepInput(hours=0.05, memory_fill=awake_start))
                meter.step(StepInput(hours=0.05, memory_fill=sleep_start, asleep=True))
                meter.step(StepInput(hours=0.05, memory_fill=sleep_start - 0.05, asleep=True))

    def test_the_three_fill_transitions_around_sleep(self):
        awake, asleep = dict(hours=0.05), dict(hours=0.05, asleep=True)
        # awake -> sleep: any fill. sleep -> sleep: no rise. sleep -> awake: no rise.
        meter = IntrinsicCostMeter()
        meter.step(StepInput(memory_fill=0.4, **awake))
        meter.step(StepInput(memory_fill=0.8, **asleep))
        meter.step(StepInput(memory_fill=0.8, **asleep))  # level is allowed
        with self.assertRaises(ValueError):
            meter.step(StepInput(memory_fill=0.81, **asleep))
        meter.step(StepInput(memory_fill=0.3, **asleep))
        with self.assertRaises(ValueError):  # waking fuller than the last sleep step started
            meter.step(StepInput(memory_fill=0.31, **awake))
        meter.step(StepInput(memory_fill=0.3, **awake))
        # awake -> awake: the fill may rise freely, and a later sleep may start from there.
        meter.step(StepInput(memory_fill=0.9, **awake))
        meter.step(StepInput(memory_fill=0.95, **asleep))

    def test_step_length_limits_are_off_by_default_and_enforced_when_set(self):
        self.assertIsNone(MeterConfig().min_awake_step_hours)
        self.assertIsNone(MeterConfig().max_awake_step_hours)
        free = IntrinsicCostMeter()
        run(free, [StepInput(), StepInput(hours=24.0)])  # no limits: anything goes
        meter = IntrinsicCostMeter(config=MeterConfig(min_awake_step_hours=0.05, max_awake_step_hours=0.25))
        for hours in (0.05, 0.1, 0.25):
            meter.step(StepInput(hours=hours))
        for hours in (0.0, 0.049, 0.2500001, 16.0):
            for fields in (dict(), dict(job_open=True, job_id="j")):
                with self.subTest(hours=hours, fields=fields), self.assertRaises(ValueError):
                    meter.step(StepInput(hours=hours, **fields))
        # Sleep steps have no shortest or longest length (their sums are exact at
        # any length), but a sleep step of 0 hours is a missing clock: refused.
        run(meter, [StepInput(hours=8.0, asleep=True), StepInput(hours=0.001, asleep=True)])
        with self.assertRaises(ValueError):
            meter.step(StepInput(hours=0.0, asleep=True))
        free.step(StepInput(hours=0.0, asleep=True))  # no limits: allowed
        # A refused step changed nothing: tiredness is where three short steps left it.
        twin = IntrinsicCostMeter()
        run(twin, [StepInput(hours=h) for h in (0.05, 0.1, 0.25)] + [StepInput(hours=8.0, asleep=True)])
        self.assertEqual(meter.step(StepInput(hours=0.25)), twin.step(StepInput(hours=0.25)))

    def test_a_world_that_forgets_its_clock_fails_loudly(self):
        # hours defaults to 0. With a shortest step set, leaving it out is an error,
        # not a silent end to tiredness and to the recovery of "nice".
        meter = IntrinsicCostMeter(config=CLOCKED)
        for clockless in (StepInput(), StepInput(skill="paint"), StepInput(remark=1),
                          StepInput(job_open=True, job_id="j"), StepInput(panel_error=(0.5,))):
            with self.subTest(step=clockless), self.assertRaises(ValueError):
                meter.step(clockless)

    def test_a_world_with_no_clock_in_sleep_fails_loudly(self):
        # A reviewer's case: a full clocked day awake, then sleep steps that report
        # 0 hours. They would pay nothing back and make sleep look useless.
        meter = IntrinsicCostMeter(config=CLOCKED)
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
                sleep_payback=shape(), hurt_cap=shape(), nice_fade=rng.choice((1e-300, 0.5, 1.0)),
                nice_half_life=shape(), boredom_half_life=shape(), boredom_floor=shape(),
                question_ids=("q",), bother_cap=shape())
            meter = IntrinsicCostMeter(rates, config)
            after_sleep = False
            for _ in range(30):
                asleep = rng.random() < 0.2
                fields = dict(hours=rng.choice((0.0, SMALLEST, 1.0, LARGEST)), hurt=rng.choice((0.0, config.hurt_cap)),
                              asleep=asleep, memory_fill=0.0 if asleep else rng.choice((0.0, 0.5, 1.0)))
                if not asleep:
                    fields.update(
                        remark=rng.choice((-1, 0, 1)), skill=rng.choice((None,) + KINDS),
                        asked_owner=rng.choice((None, "q")),
                        panel_error=rng.choice((None, tuple(rng.choice((0.0, 1.0)) for _ in range(config.panel_regions)))))
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
        meter = IntrinsicCostMeter()
        with self.assertRaises(ValueError):  # done on the step the job first appears
            meter.step(StepInput(job_open=True, job_id="invented", job_done=True))
        with self.assertRaises(ValueError):  # the refused step did not register it either
            meter.step(StepInput(job_open=True, job_id="invented", job_done=True))
        meter.step(StepInput(job_open=True, job_id="real"))
        self.assertEqual(meter.step(StepInput(job_open=True, job_id="real", job_done=True)).job_done, 1.0)
        for fields in (dict(job_done=True), dict(job_id="j"), dict(job_open=True),
                       dict(job_done=True, job_id="j")):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                StepInput(**fields)

    def test_a_refused_step_changes_nothing(self):
        script = [StepInput(hours=1.0, panel_error=(0.5,), skill="paint")] * 3
        clean, poked = IntrinsicCostMeter(), IntrinsicCostMeter()
        first = run(clean, script)
        for bad in (StepInput(skill="delete", hours=5.0, hurt=2.0), StepInput(panel_error=(0.1, 0.2)),
                    StepInput(hurt=10.5, hours=5.0, remark=1),
                    StepInput(asked_owner="q9"), StepInput(job_open=True, job_id="x", job_done=True)):
            with self.assertRaises(ValueError):
                poked.step(bad)
        self.assertEqual(run(poked, script), first)

    def test_a_hurt_above_the_scale_is_refused_not_cut_down(self):
        # Cutting it down would make harm cheaper per unit when bundled into one step.
        meter = IntrinsicCostMeter()
        self.assertEqual(meter.step(StepInput(hurt=10.0)).pain, -30.0)
        for hurt in (10.000001, 100.0, 1e9):
            with self.subTest(hurt=hurt), self.assertRaises(ValueError):
                meter.step(StepInput(hurt=hurt))
        self.assertEqual(IntrinsicCostMeter(config=MeterConfig(hurt_cap=100.0)).step(StepInput(hurt=100.0)).pain,
                         -300.0)

    def test_panel_readings_must_fit_the_contract(self):
        for reading in ((), (1.2,), (10.0,), (-0.1,), (float("nan"),), [0.5], 0.5):
            with self.subTest(reading=reading), self.assertRaises(ValueError):
                StepInput(panel_error=reading)
        with self.assertRaises(ValueError):  # wrong number of regions
            IntrinsicCostMeter().step(StepInput(panel_error=(0.5, 0.5)))

    def test_the_meter_cannot_be_copied_or_pickled(self):
        meter = IntrinsicCostMeter()
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
            IntrinsicCostMeter().step({"hurt": 1.0})
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


class ProposedTermTests(unittest.TestCase):
    CONFIG = MeterConfig(question_ids=("which folder?", "which file?"))

    def test_proposed_terms_are_exactly_zero_by_default(self):
        self.assertEqual(TERMS, APPROVED_TERMS + PROPOSED_TERMS)
        for name in PROPOSED_TERMS:
            self.assertEqual(getattr(ExchangeRates(), name), 0.0)
        meter = IntrinsicCostMeter(config=self.CONFIG)
        for felt in run(meter, [StepInput(hours=1.0, asked_owner="which folder?")] * 40):
            self.assertEqual(felt.boredom, 0.0)
            self.assertEqual(felt.bother, 0.0)

    def test_boredom_when_switched_on(self):
        rates = ExchangeRates(boredom=1.0, tiredness=0.0)
        still = run(IntrinsicCostMeter(rates), [StepInput(hours=0.1)] * 400)
        learn = run(IntrinsicCostMeter(rates), [StepInput(hours=0.1, panel_error=(0.999 ** t,))
                                                for t in range(400)])
        at_work = run(IntrinsicCostMeter(rates), [StepInput(hours=0.1, job_open=True, job_id="j")] * 400)
        self.assertGreater(still[0].boredom, -0.002)  # hardly bored at birth; it grows
        self.assertLess(still[-1].boredom, -0.099)  # then the full 1 per hour
        self.assertGreater(math.fsum(f.boredom for f in learn), -0.5)
        self.assertEqual({f.boredom for f in at_work}, {0.0})

    def test_noise_is_as_boring_as_sitting_still(self):
        # Only a new record of knowledge counts as fresh, so noise (and
        # relearning what was forgotten) is no way out of boredom.
        rates = ExchangeRates(boredom=1.0, tiredness=0.0)
        noise = [StepInput(hours=0.1, panel_error=(e,)) for e in jumpy_noise(random.Random(3), 20000)]
        felt = run(IntrinsicCostMeter(rates), noise)
        self.assertAlmostEqual(math.fsum(f.boredom for f in felt[2000:]) / 18000, -0.1, delta=1e-6)

    def test_boredom_does_not_depend_on_how_the_hours_are_cut(self):
        rates = ExchangeRates(boredom=1.0, tiredness=0.0)
        costs = [total(run(IntrinsicCostMeter(rates), [StepInput(hours=6.0 / n)] * n)) for n in (1, 6, 600)]
        self.assertLess(costs[0], -3.0)
        for cost in costs[1:]:
            self.assertAlmostEqual(cost, costs[0], delta=1e-6)

    def test_known_hole_boredom_can_be_dodged_by_sleeping_or_an_open_job(self):
        # Documented limit (design doc, holes): boredom only costs awake
        # with no job open, so sleeping while rested or stalling a job escapes it.
        rates = ExchangeRates(boredom=1.0)
        still = run(IntrinsicCostMeter(rates), [StepInput(hours=0.1)] * 400)
        dozing = run(IntrinsicCostMeter(rates), [StepInput(hours=0.1, asleep=True)] * 400)
        stalling = run(IntrinsicCostMeter(rates), [StepInput(hours=0.1, job_open=True, job_id="j")] * 400)
        self.assertLess(total(still), -20.0)
        self.assertEqual(total(dozing), 0.0)
        self.assertEqual(total(stalling), 0.0)

    def test_bother_when_switched_on(self):
        meter = IntrinsicCostMeter(ExchangeRates(bother=0.5), self.CONFIG)
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
                job_open=working, job_id=f"j{t // 7}" if working else None, job_done=t % 7 == 2,
                hurt=float(rng.random() < 0.1), remark=rng.choice((-1, 0, 0, 0, 1)),
                panel_error=(rng.random(), rng.random()) if t % 4 == 0 else None,
                skill=rng.choice((None,) + KINDS), hours=0.05, memory_fill=0.5,
                asked_owner=rng.choice((None, None, "q1", "q2"))))
        return steps

    def test_same_inputs_give_the_same_numbers(self):
        first = run(IntrinsicCostMeter(self.RATES, self.CONFIG), self.script())
        second = run(IntrinsicCostMeter(self.RATES, self.CONFIG), self.script())
        self.assertEqual(first, second)

    def test_one_meter_per_life_there_is_no_reset(self):
        # A reset would pay the same job again, wipe tiredness without sleep and
        # hide forgetting. A new life is a new meter; nothing else starts over.
        meter = IntrinsicCostMeter()
        self.assertFalse(hasattr(meter, "reset"))
        meter.step(StepInput(job_open=True, job_id="j1"))
        done = StepInput(job_open=True, job_id="j1", job_done=True)
        self.assertEqual(meter.step(done).job_done, 1.0)
        run(meter, [StepInput(hours=1.0, asleep=True)] * 50)
        self.assertEqual(meter.step(done).job_done, 0.0)

    def test_every_step_is_bounded(self):
        # Event feelings are bounded per step; tiredness and boredom per hour (1 each).
        rates, config = self.RATES, self.CONFIG
        top = rates.curiosity * config.panel_regions + rates.underused_skill + rates.job_done + rates.nice
        bottom = -(rates.curiosity * config.panel_regions + rates.underused_skill
                   + rates.pain * config.hurt_cap + rates.no
                   + (rates.tiredness + rates.boredom) * 0.05 + rates.bother * config.bother_cap)
        meter = IntrinsicCostMeter(rates, config)
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
        meter = IntrinsicCostMeter()
        meter.step(StepInput(panel_error=(0.5,)))
        for name in IntrinsicCostMeter.__slots__:
            self.assertIn(type(getattr(meter, name)), (ExchangeRates, MeterConfig, dict, set, float))
        self.assertFalse(hasattr(meter, "__dict__"))
        self.assertFalse(hasattr(meter, "parameters"))

    def test_rates_and_shape_numbers_cannot_be_changed_after_the_start(self):
        meter = IntrinsicCostMeter()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            meter.rates.pain = 0.0
        with self.assertRaises(dataclasses.FrozenInstanceError):
            meter.config.hurt_cap = 0.0
        with self.assertRaises(AttributeError):
            meter.rates = ExchangeRates(pain=0.0)
        with self.assertRaises(AttributeError):
            meter.config = MeterConfig()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            meter.step(StepInput()).pain = 1.0

    def test_step_is_the_only_way_to_get_a_feeling(self):
        public = {name for name in dir(IntrinsicCostMeter) if not name.startswith("_")}
        self.assertEqual(public, {"step", "rates", "config"})
        self.assertEqual(set(Feelings.__dataclass_fields__), set(TERMS))

    def test_signs_cannot_be_flipped_from_the_rate_table(self):
        for name in ExchangeRates.__dataclass_fields__:
            with self.subTest(rate=name), self.assertRaises(ValueError):
                ExchangeRates(**{name: -1.0})
        with self.assertRaises(ValueError):
            ExchangeRates(pain=float("nan"))


if __name__ == "__main__":
    unittest.main()
