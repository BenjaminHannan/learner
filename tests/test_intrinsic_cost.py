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
from premonition.intrinsic_cost import (APPROVED_TERMS, PROPOSED_TERMS, TERMS, ExchangeRates,
                                        Feelings, IntrinsicCostMeter, MeterConfig, StepInput)

GAMMA = 0.99  # the critic's discount in these checks
KINDS = ("paint", "reshape", "turn", "go")


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

    def test_learning_early_and_keeping_it_is_what_pays(self):
        early = curiosity_along([0.9] + [0.1] * 400)
        late = curiosity_along([0.9] * 300 + [0.1] * 101)
        never = curiosity_along([0.9] * 401)
        self.assertGreater(discounted(early), discounted(late) + 0.7)
        self.assertGreater(discounted(late), discounted(never))

    def test_matched_discount_makes_curiosity_policy_neutral(self):
        # The form first asked for (curiosity discount = the critic's). A
        # closed cycle pays <= 0, but so does everything: the discounted sum
        # depends only on the start, so learning and not learning score alike.
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
    def job(self, hurt):
        moves = [StepInput(job_open=True, job_id="j"),
                 StepInput(job_open=True, job_id="j", skill="paint"),
                 StepInput(job_open=True, job_id="j", skill="turn", hurt=hurt),
                 StepInput(job_open=True, job_id="j", skill="paint", job_done=True)]
        idle = [StepInput(job_open=True, job_id="j")] * 4
        return moves, idle

    def test_hurt_free_job_beats_doing_nothing(self):
        moves, idle = self.job(hurt=0.0)
        self.assertEqual(total(run(IntrinsicCostMeter(), idle)), 0.0)
        self.assertGreater(total(run(IntrinsicCostMeter(), moves)), 1.0)
        rates = ExchangeRates(underused_skill=0.0)
        self.assertEqual(total(run(IntrinsicCostMeter(rates), moves)), 1.0)

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
        moves, _ = self.job(hurt=0.0)
        free = day(lambda i: StepInput(hours=0.05))
        finisher = moves + free
        stall = [StepInput(job_open=True, job_id="j", skill=KINDS[i % 4], hours=0.05)
                 for i in range(len(free) + len(moves))]  # never finishes, moves forever
        busy_free = [StepInput()] * len(moves) + day(lambda i: StepInput(skill=KINDS[i % 4], hours=0.05))
        self.assertEqual(len(finisher), len(stall))
        self.assertEqual(len(finisher), len(busy_free))
        finished = total(run(IntrinsicCostMeter(), finisher))
        self.assertGreaterEqual(finished, 1.0)
        self.assertLessEqual(total(run(IntrinsicCostMeter(), stall)), 0.05)
        self.assertLessEqual(total(run(IntrinsicCostMeter(), busy_free)), 0.05)
        self.assertGreater(finished, total(run(IntrinsicCostMeter(), stall)) + 0.9)

    def test_under_a_discount_a_far_off_job_can_lose_to_busywork_now(self):
        # Limit of the claim above (design doc, holes): the totals favour
        # finishing, but the critic discounts. At 0.99 per move a job is worth
        # less than the whole skill bonus (0.05) once it is ~298 moves away.
        def one_kind_job(moves):
            return ([StepInput(job_open=True, job_id="j")]
                    + [StepInput(job_open=True, job_id="j", skill="go")] * (moves - 1)
                    + [StepInput(job_open=True, job_id="j", skill="go", job_done=True)])

        def worth(steps):
            return discounted([f.total for f in run(IntrinsicCostMeter(), steps)])

        busywork = worth([StepInput(job_open=True, job_id="j", skill=KINDS[i % 4]) for i in range(401)])
        self.assertGreater(busywork, 0.04)
        self.assertGreater(worth(one_kind_job(100)), busywork)  # near job: finishing wins
        self.assertLess(worth(one_kind_job(400)), busywork)  # far job: busywork scores higher
        self.assertLess(busywork, 0.05 + 1e-12)  # and that is all it can ever score

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
                    self.assertLessEqual(cost, hours * (1.0 + 1e-12))  # rounding only
                    self.assertGreater(cost, hours * (1.0 - 1e-5))

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
                       dict(curiosity_gamma=1.1), dict(skill_kinds=["paint"]), dict(skill_kinds=("a", "a"))):
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
                steps.append(StepInput(asleep=True, hours=0.05, memory_fill=0.4,
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
