"""The fixed built-in sense: signs, fading, noise, do-nothing and fixedness."""
from __future__ import annotations

import dataclasses
import math
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from premonition import intrinsic_cost
from premonition.intrinsic_cost import (APPROVED_TERMS, PROPOSED_TERMS, TERMS, ExchangeRates,
                                        Feelings, IntrinsicCostMeter, MeterConfig, StepInput)


def run(meter, steps):
    return [meter.step(step) for step in steps]


def total(feelings):
    return math.fsum(f.total for f in feelings)


class SignTests(unittest.TestCase):
    def setUp(self):
        self.meter = IntrinsicCostMeter()

    def test_quiet_step_feels_nothing(self):
        felt = self.meter.step(StepInput())
        self.assertEqual(felt.as_dict(), dict.fromkeys(TERMS, 0.0))
        self.assertEqual(felt.total, 0.0)

    def test_learning_feels_good_and_forgetting_feels_bad(self):
        better = self.meter.step(StepInput(error_past=0.8, error_now=0.3))
        worse = self.meter.step(StepInput(error_past=0.3, error_now=0.8))
        self.assertAlmostEqual(better.curiosity, 0.5)
        self.assertAlmostEqual(worse.curiosity, -0.5)

    def test_known_thing_gives_no_curiosity(self):
        self.assertEqual(self.meter.step(StepInput(error_past=0.0, error_now=0.0)).curiosity, 0.0)
        self.assertEqual(self.meter.step(StepInput(error_past=0.7, error_now=0.7)).curiosity, 0.0)

    def test_skill_bonus_is_good_and_never_negative(self):
        felt = run(self.meter, [StepInput(skill="paint")] * 300)
        self.assertGreater(felt[0].underused_skill, 0.0)
        self.assertTrue(all(f.underused_skill > 0.0 for f in felt))
        self.assertEqual(self.meter.step(StepInput()).underused_skill, 0.0)

    def test_pain_is_bad(self):
        felt = self.meter.step(StepInput(hurt=1.0))
        self.assertEqual(felt.pain, -3.0)
        self.assertEqual(felt.total, -3.0)
        self.assertEqual(felt.cost, 3.0)

    def test_job_done_is_good(self):
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
        felt = self.meter.step(StepInput(hours=1.0, memory_fill=0.9))
        self.assertLess(felt.tiredness, 0.0)


class FadingTests(unittest.TestCase):
    def test_repeated_nice_fades_then_recovers(self):
        meter = IntrinsicCostMeter()
        sizes = [meter.step(StepInput(remark=1)).remarks for _ in range(5)]
        self.assertEqual(sizes[0], 1.0)
        for earlier, later in zip(sizes, sizes[1:]):
            self.assertLess(later, earlier)
        self.assertLess(sizes[-1], 0.1)
        run(meter, [StepInput()] * 2000)
        self.assertGreater(meter.step(StepInput(remark=1)).remarks, 0.99)

    def test_no_never_fades(self):
        meter = IntrinsicCostMeter()
        self.assertEqual({meter.step(StepInput(remark=-1)).remarks for _ in range(50)}, {-3.0})

    def test_pain_never_fades(self):
        meter = IntrinsicCostMeter()
        self.assertEqual({meter.step(StepInput(hurt=1.0)).pain for _ in range(50)}, {-3.0})

    def test_one_job_pays_once(self):
        meter = IntrinsicCostMeter()
        done = StepInput(job_open=True, job_id="j1", job_done=True)
        paid = [meter.step(done).job_done for _ in range(4)]
        self.assertEqual(paid, [1.0, 0.0, 0.0, 0.0])
        # A new job still pays in full: doing the owner's jobs does not get old.
        other = [meter.step(StepInput(job_open=True, job_id=f"k{i}", job_done=True)).job_done
                 for i in range(20)]
        self.assertEqual(set(other), {1.0})

    def test_repeated_skill_fades_and_rest_restores_it(self):
        meter = IntrinsicCostMeter()
        bonus = [meter.step(StepInput(skill="paint")).underused_skill for _ in range(40)]
        for earlier, later in zip(bonus, bonus[1:]):
            self.assertLess(later, earlier)
        fresh = meter.step(StepInput(skill="turn")).underused_skill
        self.assertGreater(fresh, 3 * bonus[-1])
        run(meter, [StepInput()] * 1000)
        self.assertGreater(meter.step(StepInput(skill="paint")).underused_skill, 0.99 * bonus[0])

    def test_curiosity_fades_as_the_thing_is_learned(self):
        # Error falls 10 % per step; the past self is 5 steps old.
        errors = [0.9 ** t for t in range(120)]
        meter = IntrinsicCostMeter()
        felt = [meter.step(StepInput(error_past=errors[t - 5], error_now=errors[t])).curiosity
                for t in range(5, 120)]
        for earlier, later in zip(felt, felt[1:]):
            self.assertLess(later, earlier)
        self.assertGreater(felt[0], 0.3)
        self.assertLess(felt[-1], 1e-4)


class NoiseGuardTests(unittest.TestCase):
    STEPS = 20000

    def noise_rewards(self, meter, rng):
        # A land nobody can learn: past self and present self are equally
        # wrong, each with a lopsided (not bell-shaped) error.
        return [meter.step(StepInput(error_past=rng.expovariate(2.0),
                                     error_now=rng.expovariate(2.0))).curiosity
                for _ in range(self.STEPS)]

    def test_unlearnable_noise_gives_about_zero_curiosity(self):
        for clip in (1.0, 0.3):  # 0.3 clips often; the mean must still be zero
            with self.subTest(clip=clip):
                rewards = self.noise_rewards(IntrinsicCostMeter(config=MeterConfig(curiosity_clip=clip)),
                                             random.Random(11))
                mean = math.fsum(rewards) / len(rewards)
                spread = math.sqrt(math.fsum((r - mean) ** 2 for r in rewards) / (len(rewards) - 1))
                self.assertLess(abs(mean), 4 * spread / math.sqrt(len(rewards)))

    def test_keeping_only_the_good_half_would_be_fooled_by_noise(self):
        rewards = self.noise_rewards(IntrinsicCostMeter(), random.Random(11))
        fooled = math.fsum(max(0.0, r) for r in rewards) / len(rewards)
        self.assertGreater(fooled, 0.2)  # why the meter keeps the sign

    def test_learnable_land_beats_noise_and_known_land(self):
        rng = random.Random(5)
        errors = [0.97 ** t for t in range(400)]
        learn = math.fsum(IntrinsicCostMeter().step(
            StepInput(error_past=errors[t - 20], error_now=errors[t])).curiosity for t in range(20, 400))
        noise = math.fsum(IntrinsicCostMeter().step(
            StepInput(error_past=rng.random(), error_now=rng.random())).curiosity for _ in range(380))
        home = math.fsum(IntrinsicCostMeter().step(
            StepInput(error_past=0.0, error_now=0.0)).curiosity for _ in range(380))
        self.assertEqual(home, 0.0)
        self.assertGreater(learn, 5.0)
        self.assertGreater(learn, 5 * abs(noise))

    def test_forgetting_and_relearning_earns_nothing_inside_the_clip(self):
        # Error swings down and up forever; over whole swings the sum is zero.
        period, lag = 40, 8
        errors = [0.5 + 0.4 * math.sin(2 * math.pi * t / period) for t in range(lag + 10 * period)]
        meter = IntrinsicCostMeter()
        earned = math.fsum(meter.step(StepInput(error_past=errors[t - lag], error_now=errors[t])).curiosity
                           for t in range(lag, lag + 10 * period))
        self.assertAlmostEqual(earned, 0.0, places=9)

    def test_known_hole_sudden_forgetting_past_the_clip_can_pay(self):
        # Documented limit (design doc, guards): when the clip bites on a
        # sudden loss but not on the slow regain, a cycle nets a profit. The
        # lead must set curiosity_scale so the clip is rarely reached.
        lag, clip = 1, 0.1
        cycle = [0.1] + [0.9 - 0.08 * i for i in range(11)]  # jump up, slow climb down
        errors = cycle * 20
        meter = IntrinsicCostMeter(config=MeterConfig(curiosity_clip=clip))
        earned = math.fsum(meter.step(StepInput(error_past=errors[t - lag], error_now=errors[t])).curiosity
                           for t in range(lag, len(errors)))
        self.assertGreater(earned, 1.0)


class DoNothingTests(unittest.TestCase):
    def job(self, hurt):
        moves = [StepInput(job_open=True, job_id="j", skill="paint"),
                 StepInput(job_open=True, job_id="j", skill="turn", hurt=hurt),
                 StepInput(job_open=True, job_id="j", skill="paint", job_done=True)]
        idle = [StepInput(job_open=True, job_id="j")] * 3
        return moves, idle

    def test_hurt_free_job_beats_doing_nothing(self):
        moves, idle = self.job(hurt=0.0)
        self.assertEqual(total(run(IntrinsicCostMeter(), idle)), 0.0)
        self.assertGreater(total(run(IntrinsicCostMeter(), moves)), 1.0)

    def test_hurt_free_job_beats_doing_nothing_with_skill_bonus_off(self):
        rates = ExchangeRates(underused_skill=0.0)
        moves, idle = self.job(hurt=0.0)
        self.assertEqual(total(run(IntrinsicCostMeter(rates), moves)), 1.0)
        self.assertEqual(total(run(IntrinsicCostMeter(rates), idle)), 0.0)

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

    def test_sitting_still_in_free_time_does_not_dodge_tiredness(self):
        day = 30
        still = run(IntrinsicCostMeter(), [StepInput(hours=1.0)] * day)
        busy = run(IntrinsicCostMeter(ExchangeRates(underused_skill=0.0)),
                   [StepInput(hours=1.0, skill="paint")] * day)
        self.assertLess(total(still), -5.0)
        self.assertEqual(total(still), total(busy))

    def test_learning_in_free_time_beats_sitting_still(self):
        errors = [0.97 ** t for t in range(60)]
        still = run(IntrinsicCostMeter(), [StepInput(hours=0.1)] * 40)
        learn = run(IntrinsicCostMeter(), [StepInput(hours=0.1, skill="go", error_past=errors[t],
                                                     error_now=errors[t + 20]) for t in range(40)])
        self.assertGreater(total(learn), total(still) + 5.0)


class TirednessTests(unittest.TestCase):
    def test_open_job_hides_the_cost_but_pressure_still_builds(self):
        meter = IntrinsicCostMeter()
        working = run(meter, [StepInput(job_open=True, job_id="j", hours=1.0)] * 14)
        self.assertEqual({f.tiredness for f in working}, {0.0})
        after = meter.step(StepInput(hours=1.0)).tiredness
        rested = IntrinsicCostMeter().step(StepInput(hours=1.0)).tiredness
        self.assertEqual(rested, 0.0)
        self.assertLess(after, -0.5)

    def test_sleep_cures_and_never_pays(self):
        meter = IntrinsicCostMeter()
        run(meter, [StepInput(hours=1.0)] * 16)
        self.assertLess(meter.step(StepInput(hours=1.0)).tiredness, -0.9)
        asleep = run(meter, [StepInput(hours=1.0, asleep=True)] * 8)
        self.assertEqual({f.total for f in asleep}, {0.0})
        self.assertEqual(meter.step(StepInput(hours=1.0)).tiredness, 0.0)
        # Sleeping when rested gives nothing to want.
        rested = run(IntrinsicCostMeter(), [StepInput(hours=1.0, asleep=True)] * 8)
        self.assertEqual({f.total for f in rested}, {0.0})

    def test_a_nap_pays_back_part(self):
        meter = IntrinsicCostMeter()
        run(meter, [StepInput(hours=1.0)] * 16)
        full = meter.step(StepInput(hours=1.0)).tiredness
        run(meter, [StepInput(hours=1.0, asleep=True)] * 2)
        napped = meter.step(StepInput(hours=1.0)).tiredness
        self.assertLess(full, napped)
        self.assertLess(napped, 0.0)


class ProposedTermTests(unittest.TestCase):
    def test_proposed_terms_are_exactly_zero_by_default(self):
        self.assertEqual(TERMS, APPROVED_TERMS + PROPOSED_TERMS)
        for name in PROPOSED_TERMS:
            self.assertEqual(getattr(ExchangeRates(), name), 0.0)
        meter = IntrinsicCostMeter()
        steps = [StepInput(hours=1.0, asked_owner="where is the file?")] * 40
        for felt in run(meter, steps):
            self.assertEqual(felt.boredom, 0.0)
            self.assertEqual(felt.bother, 0.0)

    def test_boredom_when_switched_on(self):
        rates = ExchangeRates(boredom=1.0, tiredness=0.0)
        rng = random.Random(3)
        still = run(IntrinsicCostMeter(rates), [StepInput(hours=0.1)] * 400)
        learn = run(IntrinsicCostMeter(rates), [StepInput(hours=0.1, error_past=0.5, error_now=0.4)] * 400)
        at_work = run(IntrinsicCostMeter(rates), [StepInput(hours=0.1, job_open=True, job_id="j")] * 400)
        self.assertGreater(still[0].boredom, -0.002)  # hardly bored at birth; it grows
        self.assertLess(still[-1].boredom, -0.09)
        # Noise is as boring as sitting still: it is no way out of boredom.
        long_noise = run(IntrinsicCostMeter(rates), [StepInput(hours=0.1, error_past=rng.random(),
                                                               error_now=rng.random()) for _ in range(20000)])
        per_step = math.fsum(f.boredom for f in long_noise[1000:]) / 19000
        self.assertAlmostEqual(per_step, still[-1].boredom, delta=0.015)
        self.assertEqual({f.boredom for f in learn}, {0.0})
        self.assertEqual({f.boredom for f in at_work}, {0.0})

    def test_bother_when_switched_on(self):
        meter = IntrinsicCostMeter(ExchangeRates(bother=0.5))
        asked = [meter.step(StepInput(asked_owner="which folder?")).bother for _ in range(8)]
        self.assertEqual(asked[:3], [-0.5, -1.0, -1.5])  # asking twice costs more
        self.assertEqual(asked[-1], -2.5)  # capped
        self.assertEqual(meter.step(StepInput(asked_owner="a new question")).bother, -0.5)


class FixedMeterTests(unittest.TestCase):
    def script(self):
        rng = random.Random(42)
        steps = []
        for t in range(500):
            steps.append(StepInput(
                job_open=t % 7 < 3, job_id=f"j{t // 7}", job_done=t % 7 == 2,
                hurt=float(rng.random() < 0.1), remark=rng.choice((-1, 0, 0, 0, 1)),
                error_past=rng.random(), error_now=rng.random(),
                skill=rng.choice((None, "paint", "turn", "go")), hours=0.05,
                memory_fill=min(1.0, t / 400), asleep=t % 97 == 96,
                asked_owner=rng.choice((None, None, "q1", "q2"))))
        return steps

    def test_same_inputs_give_the_same_numbers(self):
        rates = ExchangeRates(boredom=0.3, bother=0.2)
        first = run(IntrinsicCostMeter(rates), self.script())
        second = run(IntrinsicCostMeter(rates), self.script())
        self.assertEqual(first, second)
        meter = IntrinsicCostMeter(rates)
        run(meter, self.script())
        meter.reset()
        self.assertEqual(run(meter, self.script()), first)

    def test_every_step_is_bounded(self):
        rates, config = ExchangeRates(boredom=0.3, bother=0.2), MeterConfig()
        top = rates.curiosity * config.curiosity_clip + rates.underused_skill + rates.job_done + rates.nice
        bottom = -(rates.curiosity * config.curiosity_clip + rates.pain * config.hurt_cap + rates.no
                   + (rates.tiredness + 2 * rates.boredom) * 0.05 + rates.bother * config.bother_cap)
        meter = IntrinsicCostMeter(rates, config)
        for felt in run(meter, self.script()):
            self.assertLessEqual(felt.total, top)
            self.assertGreaterEqual(felt.total, bottom)
        self.assertEqual(meter.step(StepInput(hurt=1e9)).pain, -rates.pain * config.hurt_cap)
        self.assertEqual(meter.step(StepInput(error_past=1e9, error_now=0.0)).curiosity, rates.curiosity)

    def test_nothing_in_the_meter_can_be_trained(self):
        source = Path(intrinsic_cost.__file__).read_text()
        for word in ("import torch", "import numpy", "nn.Module", "Parameter", "requires_grad",
                     "backward", "optimizer"):
            self.assertNotIn(word, source)
        meter = IntrinsicCostMeter()
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
        self.assertEqual(public, {"step", "reset", "rates", "config"})
        self.assertEqual(set(Feelings.__dataclass_fields__), set(TERMS))

    def test_signs_cannot_be_flipped_from_the_rate_table(self):
        for name in ExchangeRates.__dataclass_fields__:
            with self.subTest(rate=name), self.assertRaises(ValueError):
                ExchangeRates(**{name: -1.0})
        with self.assertRaises(ValueError):
            ExchangeRates(pain=float("nan"))

    def test_bad_inputs_are_refused(self):
        bad = (dict(hurt=-1.0), dict(hurt=float("nan")), dict(remark=2), dict(remark=True),
               dict(error_past=0.5), dict(error_past=0.5, error_now=float("inf")),
               dict(job_done=True), dict(memory_fill=1.5), dict(hours=-1.0), dict(job_open=1),
               dict(skill=""))
        for fields in bad:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                StepInput(**fields)
        with self.assertRaises(ValueError):
            IntrinsicCostMeter().step({"hurt": 1.0})
        with self.assertRaises(ValueError):
            MeterConfig(tired_onset=1.0)
        with self.assertRaises(ValueError):
            IntrinsicCostMeter(rates={"pain": 3.0})


if __name__ == "__main__":
    unittest.main()
