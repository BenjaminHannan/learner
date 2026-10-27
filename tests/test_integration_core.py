import dataclasses
import unittest
from unittest import mock

import torch
from torch.nn import functional as F

from memorylab import tasks
from memorylab.model import MainNetwork, unit


def _apply_all_teachings(model, episode):
    """Batch once through the task API, then apply teachings in episode order."""
    batch = tasks.batch_teachings(episode.teachings)
    weights = model.new_memory(batch=1)
    for index in range(len(episode.teachings)):
        result = model.write_from_teaching(
            batch.token_ids[index : index + 1],
            weights,
            lengths=batch.lengths[index : index + 1],
        )
        weights = result.weights
    return weights


class CoreIntegrationTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(20260917)
        self.model = MainNetwork()
        self.model.eval()

    def assert_finite_nonzero_gradients(self, module, label):
        gradients = [
            parameter.grad
            for parameter in module.parameters()
            if parameter.grad is not None
        ]
        self.assertTrue(gradients, f"{label} received no gradients")
        self.assertTrue(
            all(bool(torch.isfinite(gradient).all()) for gradient in gradients),
            f"{label} received non-finite gradients",
        )
        self.assertGreater(
            sum(float(gradient.abs().sum()) for gradient in gradients),
            0.0,
            f"{label} gradients were all zero",
        )

    def test_default_model_real_vocab_memory_size_and_parameter_budget(self):
        self.assertEqual(self.model.vocab_size, len(tasks.VOCAB))
        self.assertEqual(self.model.pad_id, tasks.PAD_ID)
        self.assertEqual(self.model.eos_id, tasks.EOS_ID)

        parameter_count = sum(parameter.numel() for parameter in self.model.parameters())
        self.assertLess(parameter_count, 1_000_000)

        weights = self.model.new_memory(batch=1)
        self.assertEqual(weights.dtype, torch.float32)
        self.assertEqual(weights.numel() * weights.element_size(), 65_536)

    def test_each_tier_teach_write_query_teacher_force_and_backward(self):
        for tier in (1, 2, 3):
            with self.subTest(tier=tier):
                self.model.zero_grad(set_to_none=True)
                episode = tasks.generate_episode("train", 100 + tier, tier=tier)
                weights = _apply_all_teachings(self.model, episode)
                query_batch = tasks.batch_queries(episode.queries)
                target_batch = tasks.batch_query_targets(episode.queries)
                query_weights = weights.expand(len(episode.queries), -1, -1).contiguous()

                output = self.model(
                    query_batch.token_ids,
                    query_weights,
                    targets=target_batch.token_ids,
                    lengths=query_batch.lengths,
                    teacher_forcing=True,
                )
                logits = output.decoding.logits
                token_losses = F.cross_entropy(
                    logits.reshape(-1, logits.shape[-1]),
                    target_batch.token_ids.reshape(-1),
                    reduction="none",
                ).view_as(target_batch.token_ids)
                mask = target_batch.token_ids.ne(tasks.PAD_ID)
                loss = token_losses[mask].mean()

                self.assertTrue(bool(torch.isfinite(loss)))
                loss.backward()
                self.assert_finite_nonzero_gradients(self.model.writer, "writer")
                self.assert_finite_nonzero_gradients(self.model.query, "adaptive cue")
                self.assert_finite_nonzero_gradients(self.model.encoder, "encoder")

    def test_model_batches_are_exactly_text_only_and_memory_reads_are_read_only(self):
        for tier in (1, 2, 3):
            with self.subTest(tier=tier):
                episode = tasks.generate_episode("validation", 200 + tier, tier=tier)
                teaching_batch = tasks.batch_teachings(episode.teachings)
                query_batch = tasks.batch_queries(episode.queries)

                self.assertEqual(
                    tuple(field.name for field in dataclasses.fields(tasks.TokenBatch)),
                    ("token_ids", "lengths", "attention_mask"),
                )
                for index, teaching in enumerate(episode.teachings):
                    length = teaching_batch.lengths[index].item()
                    self.assertEqual(
                        teaching_batch.token_ids[index, :length].tolist(),
                        tasks.TOKENIZER.encode(teaching.text),
                    )
                    self.assertTrue(
                        bool((teaching_batch.token_ids[index, length:] == tasks.PAD_ID).all())
                    )
                for index, query in enumerate(episode.queries):
                    length = query_batch.lengths[index].item()
                    self.assertEqual(
                        query_batch.token_ids[index, :length].tolist(),
                        tasks.TOKENIZER.encode(query.text),
                    )
                    self.assertTrue(
                        bool((query_batch.token_ids[index, length:] == tasks.PAD_ID).all())
                    )

                altered_teachings = tuple(
                    dataclasses.replace(
                        teaching,
                        correction=not teaching.correction,
                        program=("evaluator_only",),
                    )
                    for teaching in episode.teachings
                )
                altered_queries = tuple(
                    dataclasses.replace(
                        query,
                        expected="evaluatoranswer",
                        tier=99,
                        purpose="evaluator_only",
                        program=("evaluator_only",),
                    )
                    for query in episode.queries
                )
                altered_teaching_batch = tasks.batch_teachings(altered_teachings)
                altered_query_batch = tasks.batch_queries(altered_queries)
                torch.testing.assert_close(
                    altered_teaching_batch.token_ids, teaching_batch.token_ids, rtol=0, atol=0
                )
                torch.testing.assert_close(
                    altered_query_batch.token_ids, query_batch.token_ids, rtol=0, atol=0
                )

        episode = tasks.generate_episode("test", 303, tier=3)
        with torch.no_grad():
            weights = _apply_all_teachings(self.model, episode).detach()
            before = weights.clone()
            probe = torch.ones(1, self.model.hidden_width)
            self.model.memory.read(weights, probe)
            torch.testing.assert_close(weights, before, rtol=0, atol=0)

            query_batch = tasks.batch_queries(episode.queries[:1])
            self.model.generate(
                query_batch.token_ids,
                weights,
                lengths=query_batch.lengths,
                max_new_tokens=2,
                steps=2,
            )
            torch.testing.assert_close(weights, before, rtol=0, atol=0)

    def test_each_query_gets_fresh_workspace_and_depths_recompute_memory_reads(self):
        episode = tasks.generate_episode("test", 404, tier=2)
        with torch.no_grad():
            weights = _apply_all_teachings(self.model, episode).detach()
            query_batch = tasks.batch_queries(episode.queries)
            encoded_batch = self.model.encode(query_batch.token_ids, query_batch.lengths)
            batch_weights = weights.expand(len(episode.queries), -1, -1).contiguous()
            batch_trace = self.model.reason(encoded_batch, batch_weights, steps=2)

            for index, query in enumerate(episode.queries):
                individual = tasks.batch_queries((query,))
                encoded = self.model.encode(individual.token_ids, individual.lengths)
                first = self.model.reason(encoded, weights, steps=2)
                second = self.model.reason(encoded, weights, steps=2)
                torch.testing.assert_close(
                    first.initial_workspace, second.initial_workspace, rtol=0, atol=0
                )
                torch.testing.assert_close(
                    first.final_workspace, second.final_workspace, rtol=0, atol=0
                )
                torch.testing.assert_close(
                    first.initial_workspace[0],
                    batch_trace.initial_workspace[index],
                    rtol=1e-6,
                    atol=1e-6,
                )
                torch.testing.assert_close(
                    first.final_workspace[0], batch_trace.final_workspace[index], rtol=1e-6, atol=1e-6
                )

            individual = tasks.batch_queries(episode.queries[:1])
            encoded = self.model.encode(individual.token_ids, individual.lengths)
            for depth in (1, 2, 4):
                with self.subTest(depth=depth):
                    with mock.patch.object(
                        self.model.memory, "read", wraps=self.model.memory.read
                    ) as read_spy:
                        trace = self.model.reason(encoded, weights, steps=depth)
                    self.assertEqual(len(trace.steps), depth)
                    self.assertEqual(read_spy.call_count, depth)
                    for step in trace.steps:
                        expected_query = unit(
                            self.model.query(
                                torch.cat([encoded.pooled, step.workspace_before], dim=-1)
                            )
                        )
                        expected_read = self.model.memory.read(weights, expected_query)
                        torch.testing.assert_close(step.query, expected_query, rtol=1e-6, atol=1e-6)
                        torch.testing.assert_close(
                            step.memory_read, expected_read, rtol=1e-6, atol=1e-6
                        )


if __name__ == "__main__":
    unittest.main()
