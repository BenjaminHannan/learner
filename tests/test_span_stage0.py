"""The Stage 0 branch-point check (scripts/span_stage0.py, `branch_check`): it passes on a true branch and fails on
each way the built-in review (2026-10-18) showed the earlier check could pass with a broken pairing. CPU, tiny."""
from __future__ import annotations

import math
import unittest

import torch
import torch.nn as nn

from scripts import span_stage0
from premonition import span_cards
from tests.test_premonition_model import synthetic_batch
from tests.test_premonition_span_cards import plain_model, span_model

DEVICE = torch.device("cpu")


def batches() -> list:
    return [synthetic_batch(visits=2, lines=16, seed=s) for s in (3, 4)]


def pair(**overrides):
    return plain_model(3), span_model(7, **overrides)


class BranchCheckTest(unittest.TestCase):
    def test_a_true_branch_passes_and_the_eager_pass_uses_the_cards(self) -> None:
        line, span = pair()
        check = span_stage0.branch_check(line, span, batches(), DEVICE)
        self.assertTrue(check["passed"], check["reasons"])
        self.assertEqual(check["economy"]["line_aligned"], 1.0)
        self.assertGreater(check["eager"]["cards_fetched"], 0)
        self.assertEqual(check["eager"]["questions_fetching"], check["eager"]["questions"])   # every question
        self.assertEqual(check["missing"], sorted(span_stage0.GATE_KEYS))
        self.assertFalse(line.training or span.training)

    def test_an_unloaded_weight_fails(self) -> None:
        """Review finding 1: strict=False dropped every key mismatch."""
        line, span = pair()
        line.extra = nn.Parameter(torch.zeros(1))                   # a LINE weight SPAN has no slot for
        check = span_stage0.branch_check(line, span, batches(), DEVICE)
        self.assertFalse(check["passed"])
        self.assertIn("weights", check["reasons"])

    def test_wrong_card_keys_fail(self) -> None:
        """Review finding 3: the key difference was only logged, not part of `passed`."""
        line, span = pair()
        span.writer.key.register_forward_hook(lambda _m, _a, out: out + 0.5)
        check = span_stage0.branch_check(line, span, batches(), DEVICE)
        self.assertGreater(check["max_key_diff"], 0.1)
        self.assertFalse(check["passed"])
        self.assertIn("card keys or values", check["reasons"])

    def test_wrong_card_values_fail_when_the_natural_pass_never_fetches(self) -> None:
        """Review finding 2: with weights that never ASK, identical answers did not exercise the cards. Here the
        natural pass fetches nothing and matches exactly (the old check passed this pair); the direct value check
        fails it, and the eager pass does fetch."""
        line, span = pair()
        with torch.no_grad():
            line.heads.ask.bias.fill_(-20.0)                        # the natural pass never fetches a card
        span.writer.value.register_forward_hook(lambda _m, _a, out: out * 3.0 + 1.0)
        check = span_stage0.branch_check(line, span, batches(), DEVICE)
        self.assertEqual(check["natural"]["cards_fetched"], 0)
        self.assertEqual(check["natural"]["differing"], 0)
        self.assertFalse(check["passed"])
        self.assertIn("card keys or values", check["reasons"])
        self.assertGreater(check["eager"]["cards_fetched"], 0)
        self.assertGreaterEqual(check["value_scale"], 1.0)

    def test_a_wrong_layout_fails_on_line_alignment(self) -> None:
        line, span = pair(max_span=3)                               # the cap splits every line
        check = span_stage0.branch_check(line, span, batches(), DEVICE)
        self.assertFalse(check["passed"])
        self.assertIn("line_aligned != 1", check["reasons"])

    def test_no_cards_is_reported_not_a_crash(self) -> None:
        """Review finding 6: an empty card set raised inside the check."""
        cut = []
        for batch in batches():
            fields = dict(batch.__dict__)
            fields["card_end"] = torch.zeros_like(batch.card_end)
            cut.append(type(batch)(**fields))
        line, span = pair()
        check = span_stage0.branch_check(line, span, cut, DEVICE)
        self.assertFalse(check["passed"])
        self.assertIn("no cards", check["reasons"])


    def test_a_batch_without_questions_is_skipped_not_a_crash(self) -> None:
        """Second review, finding 1: reshape(0, -1) raised on a batch with no questions."""
        empty = synthetic_batch(visits=2, lines=16, seed=3, question_rate=0.0)
        self.assertEqual(int(empty.q_visit.shape[0]), 0)
        line, span = pair()
        check = span_stage0.branch_check(line, span, [empty] + batches(), DEVICE)
        self.assertTrue(check["passed"], check["reasons"])

    def test_a_trained_halt_head_still_covers_every_question(self) -> None:
        """Second review, finding 2: with HALT left natural, questions that halt on loop 1 fetched nothing."""
        line, span = pair()
        with torch.no_grad():
            line.heads.halt.bias.fill_(20.0)                        # LINE halts at once (as after training)
        check = span_stage0.branch_check(line, span, batches(), DEVICE)
        self.assertTrue(check["passed"], check["reasons"])
        self.assertEqual(check["eager"]["questions_fetching"], check["eager"]["questions"])


    def test_halt_probabilities_are_compared_in_probability_space(self) -> None:
        """Fifth review, finding 1: float32 halt probabilities near 1 turned one ulp into a large logit gap. A one-ulp
        difference at p = 1 - 1e-6 must not count as a differing answer."""
        class Fixed:
            def __init__(self, prob):
                self.prob = prob

            def answer(self, batch):
                count = 3
                return span_cards.Answers(torch.zeros(count, 4, dtype=torch.long), torch.ones(count, dtype=torch.long),
                                          torch.ones(count, dtype=torch.long), torch.zeros(count, 2, dtype=torch.long),
                                          torch.zeros(count, 5, dtype=torch.bool), self.prob)
        near = torch.full((3,), 1 - 1e-6, dtype=torch.float32)
        ulp = torch.nextafter(near, torch.ones_like(near))
        same = span_stage0.compare_answers(Fixed(near), Fixed(ulp), [None])
        self.assertTrue(same["identical"])
        self.assertEqual(same["differing"], 0)
        apart = span_stage0.compare_answers(Fixed(near), Fixed(near - 0.01), [None])
        self.assertFalse(apart["identical"])


class GateTest(unittest.TestCase):
    def test_the_strict_check_runs_on_cpu_copies(self) -> None:
        line, span = pair()
        gate = span_stage0.branch_gate(line, span, batches(), DEVICE)
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["strict_cpu"]["device"], "cpu")
        self.assertTrue(gate["line_aligned_is_1"])
        self.assertNotIn("gpu", gate)
        self.assertFalse(line.training or span.training)
        self.assertEqual(gate["reasons"], [])

    def test_a_failed_gate_names_its_reasons(self) -> None:
        """Third review, finding 1: branch_gate had no `reasons`, so the stop message raised KeyError."""
        bad_line, bad_span = pair(max_span=3)
        gate = span_stage0.branch_gate(bad_line, bad_span, batches(), DEVICE)
        self.assertFalse(gate["passed"])
        self.assertIn("cpu: line_aligned != 1", gate["reasons"])
        self.assertIn("line_aligned != 1", f"failed ({gate['reasons']})")

    def test_gpu_answer_flips_are_bounded(self) -> None:
        """Third review, finding 3: GPU answer differences were reported but unbounded. The GPU half is simulated
        (no CUDA here): the second branch_check call returns the CPU result with `flips` differing answers."""
        real = span_stage0.branch_check
        for flips, ok in ((0, True), (1, True), (12, False)):
            def fake(line, span, bs, device, flips=flips):
                result = real(line, span, bs, torch.device("cpu"))
                if device.type == "cuda":
                    result["natural"] = {**result["natural"], "differing": flips}
                return result
            span_stage0.branch_check = fake
            try:
                line, span = pair()
                gate = span_stage0.branch_gate(line, span, batches(), torch.device("cuda"))
            finally:
                span_stage0.branch_check = real
            self.assertEqual(gate["passed"], ok, (flips, gate["reasons"]))
            self.assertEqual(gate["gpu_answer_differences"]["natural"], flips)

    def test_log_lines_are_strict_json(self) -> None:
        """Second review, finding 7: math.inf was written as the non-JSON token Infinity."""
        import contextlib
        import io
        import json
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            span_stage0.emit("x", diff=math.inf, nested={"v": [float("nan"), 1.0]})
        line = out.getvalue()
        self.assertNotIn("Infinity", line.replace('"inf"', ""))
        record = json.loads(line[len("STAGE0 "):], parse_constant=lambda c: self.fail(c))
        self.assertEqual(record["diff"], "inf")
        self.assertEqual(record["nested"]["v"], ["nan", 1.0])


if __name__ == "__main__":
    unittest.main()
