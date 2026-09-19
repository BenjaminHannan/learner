import unittest
from unittest import mock

import torch

from memorylab.tasks import TOKENIZER, batch_queries, batch_query_targets, batch_teachings, generate_episode
from memorylab.transformer_model import MultiHeadMatrixMemory, RecurrentTransformerLearner


def make_small_transformer():
    torch.manual_seed(404)
    return RecurrentTransformerLearner(
        model_width=32,
        memory_width=8,
        memory_heads=2,
        attention_heads=4,
        ffn_width=64,
        reasoning_steps=2,
        max_reasoning_steps=4,
        max_sequence_length=64,
        max_decode_len=4,
    )


class MultiHeadMemoryTests(unittest.TestCase):
    def test_parallel_delta_write_is_exact_and_differentiable(self):
        memory = MultiHeadMatrixMemory(heads=2, width=3)
        weights = memory.empty(batch=1)
        key = torch.tensor(
            [[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]],
            requires_grad=True,
        )
        value = torch.tensor(
            [[[0.2, -0.1, 0.3], [-0.4, 0.5, 0.1]]],
            requires_grad=True,
        )
        updated = memory.delta_write(weights, key, value)
        read = memory.read(updated, key)
        torch.testing.assert_close(read, value, rtol=0, atol=0)
        read.sum().backward()
        self.assertGreater(float(value.grad.abs().sum()), 0.0)
        self.assertEqual(memory.bytes_per_item, 2 * 3 * 3 * 4)


class RecurrentTransformerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_default_shape_parameter_scale_and_selected_contract(self):
        model = RecurrentTransformerLearner()
        parameters = sum(parameter.numel() for parameter in model.parameters())
        self.assertGreater(parameters, 4_500_000)
        self.assertLess(parameters, 5_200_000)
        self.assertEqual(model.new_memory().shape, (1, 4, 128, 128))
        self.assertEqual(model.persistent_memory_bytes, 262_144)
        self.assertEqual(model.reasoning_steps, 6)

    def test_writer_is_sentence_only_and_writes_once_per_head(self):
        model = make_small_transformer()
        episode = generate_episode("train", 3, tier=1)
        batch = batch_teachings([episode.teachings[0]])
        memory = model.new_memory()
        with mock.patch.object(
            model.writer,
            "forward",
            wraps=model.writer.forward,
        ) as writer_spy:
            result = model.write_from_teaching(
                batch.token_ids,
                memory,
                lengths=batch.lengths,
            )
        writer_spy.assert_called_once()
        self.assertEqual(len(writer_spy.call_args.args), 1)
        self.assertEqual(writer_spy.call_args.kwargs, {})
        self.assertEqual(result.writer.key.shape, (1, 2, 8))
        self.assertEqual(result.writer.value.shape, (1, 2, 8))
        self.assertGreater(float(result.weights.detach().norm()), 0.0)

    def test_recurrent_reads_are_workspace_conditioned_and_read_only(self):
        model = make_small_transformer().eval()
        episode = generate_episode("validation", 4, tier=1)
        query = batch_queries([episode.queries[0]])
        memory = model.new_memory()
        memory[0, 0, 0, 0] = 1.0
        before = memory.clone()
        encoded = model.encode(query.token_ids, lengths=query.lengths)
        with mock.patch.object(model.memory, "read", wraps=model.memory.read) as read_spy:
            with torch.no_grad():
                trace = model.reason(encoded, memory, steps=2)
        self.assertEqual(read_spy.call_count, 2)
        self.assertEqual(len(trace.steps), 2)
        self.assertFalse(torch.equal(trace.steps[0].query, trace.steps[1].query))
        query_cosine = torch.nn.functional.cosine_similarity(
            trace.steps[0].query,
            trace.steps[1].query,
            dim=-1,
        ).mean()
        self.assertGreater(float(query_cosine), 0.95)
        torch.testing.assert_close(memory, before, rtol=0, atol=0)

    def test_latest_memory_slots_carry_reads_into_the_decoded_workspace(self):
        model = make_small_transformer().eval()
        episode = generate_episode("validation", 5, tier=1)
        query = batch_queries([episode.queries[0]])
        encoded = model.encode(query.token_ids, lengths=query.lengths)
        memory = torch.randn(1, 2, 8, 8)
        with torch.no_grad():
            trace = model.reason(encoded, memory)
            zero_trace = model.reason(encoded, torch.zeros_like(memory))
        time = query.token_ids.shape[1]
        self.assertEqual(tuple(trace.final_workspace.shape), (1, time + 2, 32))
        # Slots start from W-independent embeddings on every reasoning step, so
        # any final-slot difference comes from the latest W read rather than an
        # accumulated transformed slot history.
        self.assertFalse(
            torch.allclose(trace.final_workspace[:, time:], zero_trace.final_workspace[:, time:])
        )
        embedding = model.embedding.weight
        self.assertTrue(torch.equal(embedding[model.pad_id], torch.zeros_like(embedding[0])))
        self.assertLess(float(embedding.norm(dim=-1).mean()), 2.0)

    def test_forward_backward_generation_and_fresh_workspace(self):
        model = make_small_transformer()
        episode = generate_episode("train", 8, tier=1)
        query = batch_queries([episode.queries[0]])
        targets = batch_query_targets([episode.queries[0]])
        memory = model.new_memory()
        output = model(
            query.token_ids,
            memory,
            lengths=query.lengths,
            targets=targets.token_ids,
        )
        self.assertEqual(
            output.decoding.logits.shape,
            (1, targets.token_ids.shape[1], len(TOKENIZER.vocab)),
        )
        output.decoding.logits.sum().backward()
        self.assertGreater(float(model.embedding.weight.grad.abs().sum()), 0.0)

        model.eval()
        with torch.no_grad():
            first = model.generate(query.token_ids, memory, lengths=query.lengths, max_new_tokens=3)
            second = model.generate(query.token_ids, memory, lengths=query.lengths, max_new_tokens=3)
        torch.testing.assert_close(first.decoding.logits, second.decoding.logits, rtol=0, atol=0)
        torch.testing.assert_close(
            first.reasoning.initial_workspace,
            second.reasoning.initial_workspace,
            rtol=0,
            atol=0,
        )


if __name__ == "__main__":
    unittest.main()
