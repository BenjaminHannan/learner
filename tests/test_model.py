import unittest
from unittest import mock

import torch
from torch import nn

from memorylab.model import EncodedSequence, MainNetwork, MatrixMemory, TokenSpec


TOKEN_SPEC = TokenSpec(vocab_size=9, pad_id=0, eos_id=1)


def make_model(*, hidden_width=4, reasoning_steps=2, max_reasoning_steps=4, max_decode_len=5):
    torch.manual_seed(1234)
    model = MainNetwork(
        embed_width=3,
        hidden_width=hidden_width,
        reasoning_steps=reasoning_steps,
        max_reasoning_steps=max_reasoning_steps,
        max_decode_len=max_decode_len,
        token_spec=TOKEN_SPEC,
    )
    model.eval()
    return model


class _FixedWorkspace(nn.Module):
    def forward(self, pooled):
        initial = pooled.new_tensor([1.0, 0.0])
        return initial.unsqueeze(0).expand(pooled.shape[0], -1)


class _WorkspaceQuery(nn.Module):
    def forward(self, combined):
        return combined[:, -2:]


class _MemoryReadCell(nn.Module):
    def forward(self, combined, previous):
        del previous
        return combined[:, -2:]


class _ScriptedOutput(nn.Module):
    def __init__(self, vocab_size, sequence):
        super().__init__()
        self.vocab_size = vocab_size
        self.sequence = sequence
        self.calls = 0

    def forward(self, features):
        batch = features.shape[0]
        ids = self.sequence[min(self.calls, len(self.sequence) - 1)]
        if len(ids) != batch:
            raise AssertionError("scripted output batch mismatch")
        logits = features.new_full((batch, self.vocab_size), -10.0)
        index = torch.tensor(ids, dtype=torch.long, device=features.device).unsqueeze(1)
        logits.scatter_(1, index, 10.0)
        self.calls += 1
        return logits


class MatrixMemoryTests(unittest.TestCase):
    def test_delta_write_exact_same_key_and_gradients(self):
        memory = MatrixMemory(width=2)
        weights = torch.tensor([[[0.2, -0.3], [0.4, 0.1]]], dtype=torch.float32)
        key = torch.tensor([[1.0, 2.0]], dtype=torch.float32, requires_grad=True)
        value = torch.tensor([[0.7, -0.4]], dtype=torch.float32, requires_grad=True)

        updated = memory.delta_write(weights, key, value)
        same_key_read = memory.read(updated, key)
        torch.testing.assert_close(same_key_read, value, rtol=1e-6, atol=1e-6)
        self.assertEqual(updated.dtype, torch.float32)
        self.assertIsNotNone(updated.grad_fn)

        probe = torch.tensor([[1.0, 1.0]], dtype=torch.float32)
        post_write_read = memory.read(updated, probe)
        grad_key, grad_value = torch.autograd.grad(post_write_read.square().sum(), (key, value))
        self.assertTrue(bool(torch.isfinite(grad_key).all()))
        self.assertTrue(bool(torch.isfinite(grad_value).all()))
        self.assertGreater(float(grad_key.abs().sum()), 0.0)
        self.assertGreater(float(grad_value.abs().sum()), 0.0)

    def test_memory_validation_dtype_shape_nonfinite_and_zero_keys(self):
        memory = MatrixMemory(width=3)
        good_weights = memory.empty(batch=1)
        good_query = torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32)
        good_value = torch.tensor([[0.1, 0.2, 0.3]], dtype=torch.float32)
        self.assertEqual(good_weights.dtype, torch.float32)

        cases = [
            ("memory shape", lambda: memory.read(torch.zeros(1, 3), good_query)),
            ("memory dtype", lambda: memory.read(good_weights.double(), good_query)),
            ("query shape", lambda: memory.read(good_weights, torch.ones(1, 2))),
            (
                "nonfinite memory",
                lambda: memory.read(
                    torch.tensor([[[float("nan"), 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]]),
                    good_query,
                ),
            ),
            ("nonfinite query", lambda: memory.read(good_weights, torch.tensor([[float("inf"), 0.0, 0.0]]))),
            ("zero read key", lambda: memory.read(good_weights, torch.zeros(1, 3))),
            ("write key shape", lambda: memory.delta_write(good_weights, torch.ones(1, 2), good_value)),
            ("write value shape", lambda: memory.delta_write(good_weights, good_query, torch.ones(1, 2))),
            (
                "nonfinite write key",
                lambda: memory.delta_write(good_weights, torch.tensor([[float("nan"), 0.0, 0.0]]), good_value),
            ),
            (
                "nonfinite write value",
                lambda: memory.delta_write(good_weights, good_query, torch.tensor([[0.0, float("inf"), 0.0]])),
            ),
            ("zero write key", lambda: memory.delta_write(good_weights, torch.zeros(1, 3), good_value)),
        ]
        for name, action in cases:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    action()


class ReasoningTests(unittest.TestCase):
    def test_adaptive_query_changes_with_workspace_and_memory_is_reread(self):
        model = make_model(hidden_width=2, reasoning_steps=3, max_reasoning_steps=3)
        model.workspace_initial = _FixedWorkspace()
        model.query = _WorkspaceQuery()
        model.reason_cell = _MemoryReadCell()

        encoded = EncodedSequence(
            states=torch.zeros(1, 1, 2),
            pooled=torch.zeros(1, 2),
            mask=torch.ones(1, 1, dtype=torch.bool),
            lengths=torch.ones(1, dtype=torch.long),
        )
        weights = torch.tensor([[[0.0, 1.0], [1.0, 0.0]]], dtype=torch.float32)

        with mock.patch.object(model.memory, "read", wraps=model.memory.read) as read_spy:
            trace = model.reason(encoded, weights)

        self.assertEqual(read_spy.call_count, 3)
        expected_queries = (
            torch.tensor([[1.0, 0.0]]),
            torch.tensor([[0.0, 1.0]]),
            torch.tensor([[1.0, 0.0]]),
        )
        expected_reads = (
            torch.tensor([[0.0, 1.0]]),
            torch.tensor([[1.0, 0.0]]),
            torch.tensor([[0.0, 1.0]]),
        )
        for index, step in enumerate(trace.steps):
            torch.testing.assert_close(step.query, expected_queries[index], rtol=0, atol=0)
            torch.testing.assert_close(step.memory_read, expected_reads[index], rtol=0, atol=0)
            called_query = read_spy.call_args_list[index].args[1]
            torch.testing.assert_close(called_query, expected_queries[index], rtol=0, atol=0)

    def test_repeated_forward_and_generate_are_fresh_deterministic_and_read_only(self):
        model = make_model()
        query = torch.tensor([[2, 3, 0], [4, 5, 6]], dtype=torch.long)
        lengths = torch.tensor([2, 3], dtype=torch.long)
        targets = torch.tensor([[2, 3, 1], [6, 7, 1]], dtype=torch.long)
        weights = model.new_memory(batch=2)
        weights[0, 0, 1] = 0.25
        weights[1, 2, 3] = -0.5
        before = weights.clone()

        with torch.no_grad():
            first_forward = model(query, weights, targets=targets, lengths=lengths)
            second_forward = model(query, weights, targets=targets, lengths=lengths)
            first_generate = model.generate(query, weights, lengths=lengths, max_new_tokens=4)
            second_generate = model.generate(query, weights, lengths=lengths, max_new_tokens=4)

        torch.testing.assert_close(
            first_forward.reasoning.initial_workspace,
            second_forward.reasoning.initial_workspace,
            rtol=0,
            atol=0,
        )
        torch.testing.assert_close(
            first_forward.reasoning.final_workspace,
            second_forward.reasoning.final_workspace,
            rtol=0,
            atol=0,
        )
        torch.testing.assert_close(first_forward.decoding.logits, second_forward.decoding.logits, rtol=0, atol=0)
        torch.testing.assert_close(first_forward.decoding.tokens, second_forward.decoding.tokens, rtol=0, atol=0)
        torch.testing.assert_close(first_generate.decoding.logits, second_generate.decoding.logits, rtol=0, atol=0)
        torch.testing.assert_close(first_generate.decoding.tokens, second_generate.decoding.tokens, rtol=0, atol=0)
        torch.testing.assert_close(weights, before, rtol=0, atol=0)


class WriterTests(unittest.TestCase):
    def test_writer_attention_ignores_padding_and_separates_key_from_value_pooling(self):
        model = make_model(hidden_width=4)
        teaching = torch.tensor([[2, 3, 0, 0], [2, 3, 4, 5]], dtype=torch.long)
        lengths = torch.tensor([2, 4], dtype=torch.long)
        encoded = model.encode(teaching, lengths=lengths)
        with torch.no_grad():
            key_pool = model.writer._attend(encoded, model.writer.key_attention)
            value_pool = model.writer._attend(encoded, model.writer.value_attention)
        torch.testing.assert_close(key_pool, value_pool, rtol=0, atol=0)
        torch.testing.assert_close(
            key_pool[0],
            encoded.states[0, :2].mean(dim=0),
            rtol=1e-6,
            atol=1e-6,
        )

    def test_writer_only_receives_encoding_and_post_write_read_backpropagates(self):
        model = make_model(hidden_width=4)
        with torch.no_grad():
            for parameter in model.writer.parameters():
                parameter.zero_()
            model.writer.key[2].bias.copy_(torch.tensor([1.0, 0.0, 0.0, 0.0]))
            model.writer.value[2].bias.copy_(torch.tensor([0.2, -0.1, 0.3, 0.4]))

        teaching = torch.tensor([[2, 3, 0]], dtype=torch.long)
        weights = model.new_memory(batch=1)
        model.zero_grad(set_to_none=True)

        with mock.patch.object(model.writer, "forward", wraps=model.writer.forward) as writer_spy:
            result = model.write_from_teaching(teaching, weights)

        writer_spy.assert_called_once()
        self.assertEqual(len(writer_spy.call_args.args), 1)
        self.assertEqual(writer_spy.call_args.kwargs, {})
        self.assertIs(writer_spy.call_args.args[0], result.encoding)
        self.assertIsInstance(writer_spy.call_args.args[0], EncodedSequence)

        post_query = torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.float32)
        post_write_read = model.memory.read(result.weights, post_query)
        post_write_read.sum().backward()
        grad = model.writer.value[2].bias.grad
        self.assertIsNotNone(grad)
        self.assertTrue(bool(torch.isfinite(grad).all()))
        self.assertGreater(float(grad.abs().sum()), 0.0)


class DecoderTests(unittest.TestCase):
    def test_teacher_forced_dimensions_and_attention_respects_query_mask(self):
        model = make_model()
        query = torch.tensor([[2, 3, 0, 0], [4, 5, 6, 7]], dtype=torch.long)
        lengths = torch.tensor([2, 4], dtype=torch.long)
        targets = torch.tensor([[2, 3, 1], [5, 6, 1]], dtype=torch.long)
        weights = model.new_memory(batch=2)

        with torch.no_grad():
            output = model(query, weights, targets=targets, lengths=lengths, teacher_forcing=True)

        decoding = output.decoding
        self.assertEqual(decoding.logits.shape, (2, 3, TOKEN_SPEC.vocab_size))
        self.assertEqual(decoding.tokens.shape, (2, 3))
        self.assertEqual(decoding.attention.shape, (2, 3, 4))
        self.assertEqual(decoding.lengths.shape, (2,))
        torch.testing.assert_close(decoding.attention.sum(dim=-1), torch.ones(2, 3), rtol=1e-6, atol=1e-6)
        torch.testing.assert_close(decoding.attention[0, :, 2:], torch.zeros(3, 2), rtol=0, atol=0)

    def test_generation_eos_per_item_and_max_length_bound(self):
        model = make_model(max_decode_len=6)
        query = torch.tensor([[2, 3], [4, 5]], dtype=torch.long)
        weights = model.new_memory(batch=2)

        model.decoder.output = _ScriptedOutput(
            TOKEN_SPEC.vocab_size,
            sequence=((TOKEN_SPEC.eos_id, 2), (3, 2), (4, TOKEN_SPEC.eos_id)),
        )
        with torch.no_grad():
            variable = model.generate(query, weights, max_new_tokens=5, steps=1).decoding

        self.assertEqual(variable.tokens.shape, (2, 3))
        self.assertEqual(variable.tokens[0].tolist(), [TOKEN_SPEC.eos_id, TOKEN_SPEC.pad_id, TOKEN_SPEC.pad_id])
        self.assertEqual(variable.tokens[1].tolist(), [2, 2, TOKEN_SPEC.eos_id])
        self.assertEqual(variable.lengths.tolist(), [1, 3])

        model.decoder.output = _ScriptedOutput(TOKEN_SPEC.vocab_size, sequence=((2, 2),))
        with torch.no_grad():
            bounded = model.generate(query, weights, max_new_tokens=2, steps=1).decoding

        self.assertEqual(bounded.tokens.shape, (2, 2))
        self.assertEqual(bounded.lengths.tolist(), [2, 2])
        self.assertNotIn(TOKEN_SPEC.eos_id, bounded.tokens.flatten().tolist())


if __name__ == "__main__":
    unittest.main()
