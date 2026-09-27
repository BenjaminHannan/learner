"""Definitions only until the parent confirms committed, pushed PASSMARKS."""
from __future__ import annotations

import inspect
import io
import random
import unittest
from dataclasses import fields

from auto_model import AutoNet, E, EXPECTED_PARAMS, M, PuzzleRequest, R, X, torch, visible_batch


def request_of(item) -> PuzzleRequest:
    # The caller discards every hidden field before anything reaches the model.
    return PuzzleRequest(tokens=item.tokens, slot=item.slot)


def generated_requests() -> tuple[PuzzleRequest, PuzzleRequest, PuzzleRequest]:
    rng = random.Random(9017)
    grid = E.latin_item(rng, *E.make_latin_base(rng, 5))
    total = E.make_sum(rng, 4)
    maze = M.make_maze(rng, 7)
    return request_of(grid), request_of(total), request_of(maze)


def infer_one(net: AutoNet, request: PuzzleRequest, rounds: int = 2):
    tokens, slots = visible_batch([request], "cpu")
    return tuple(x.clone() for x in net.infer(tokens, slots, rounds=rounds))


class AutoModelContract(unittest.TestCase):
    def test_exact_parameters_trainability_and_same_initial_context_weights(self):
        torch.manual_seed(301)
        auto = AutoNet()
        self.assertEqual(sum(p.numel() for p in auto.parameters()), EXPECTED_PARAMS)
        self.assertTrue(all(p.requires_grad for p in auto.parameters()))
        keys = set(auto.state_dict())
        self.assertIn("contexts.weight", keys)
        self.assertNotIn("env.weight", keys)
        self.assertEqual(tuple(auto.contexts.weight.shape), (4, 256))

        torch.manual_seed(301)
        R.ARMS["dense"] = dict(X.SIZES["small"])
        sealed = R.Net("dense")
        self.assertTrue(torch.equal(auto.contexts.weight, sealed.env.weight))
        self.assertEqual(len(keys), len(sealed.state_dict()))
        for key, value in auto.state_dict().items():
            old_key = "env.weight" if key == "contexts.weight" else key
            self.assertTrue(torch.equal(value, sealed.state_dict()[old_key]), key)

    def test_public_requests_and_entrypoints_have_no_labels(self):
        self.assertEqual([field.name for field in fields(PuzzleRequest)], ["tokens", "slot"])
        for name in ("embed_inputs", "train_rounds", "infer"):
            parameters = inspect.signature(getattr(AutoNet, name)).parameters
            self.assertNotIn("env", parameters)
            self.assertNotIn("kind", parameters)
            self.assertNotIn("target", parameters)
            self.assertNotIn("meta", parameters)
        net = AutoNet()
        tokens, slots = visible_batch([generated_requests()[1]], "cpu")
        for name in ("embed", "loop_train", "loop_rounds", "plain_forward"):
            with self.subTest(name=name), self.assertRaises(TypeError):
                getattr(net, name)(tokens, slots, torch.zeros(1, dtype=torch.long))

    def test_hidden_metadata_poison_cannot_change_inference(self):
        rng = random.Random(1604)
        item = E.make_sum(rng, 4)
        changed = E.Item("fake-kind", 999, [row[:] for row in item.tokens],
                         [row[:] for row in item.slot], [[123] * len(row) for row in item.target],
                         {"poison": "hidden"})
        original_request, changed_request = request_of(item), request_of(changed)
        self.assertEqual(original_request, changed_request)
        net = AutoNet()
        for left, right in zip(infer_one(net, original_request), infer_one(net, changed_request)):
            self.assertTrue(torch.equal(left, right))

    def test_mixed_request_order_does_not_change_outputs(self):
        grid, total, maze = generated_requests()
        net = AutoNet()
        first = {name: infer_one(net, request) for name, request in
                 (("A", grid), ("B", total), ("C", maze))}
        second = {name: infer_one(net, request) for name, request in
                  (("C", maze), ("A", grid), ("B", total))}
        for name in first:
            for left, right in zip(first[name], second[name]):
                self.assertTrue(torch.equal(left, right), name)

    def test_code_generated_native_shapes_without_padding(self):
        grid, total, maze = generated_requests()
        self.assertEqual([(len(x.tokens), len(x.tokens[0])) for x in (grid, total, maze)],
                         [(7, 5), (3, 5), (7, 7)])
        net = AutoNet()
        for request in (grid, total, maze):
            predictions, stops, contexts = infer_one(net, request, rounds=1)
            length = len(request.tokens) * len(request.tokens[0])
            self.assertEqual(tuple(predictions.shape), (1, 1, length))
            self.assertEqual(tuple(stops.shape), (1, 1))
            self.assertEqual(tuple(contexts.shape), (1, 4))
            self.assertTrue(torch.allclose(contexts.sum(dim=-1), torch.ones(1)))
        with self.assertRaises(ValueError):
            visible_batch([grid, total, maze], "cpu")

    def test_answer_stop_loss_backpropagates_into_contexts_and_every_block(self):
        rng = random.Random(2042)
        items = [E.make_sum(rng, 4) for _ in range(2)]
        tokens, slots = visible_batch([request_of(item) for item in items], "cpu")
        targets = torch.tensor([item.target for item in items], dtype=torch.long)
        net = AutoNet()
        net.train()
        logits, halt_logits = net.train_rounds(tokens, slots, n_free=1, n_grad=1)[0]
        cross_entropy, exact = R.ce_and_exact(logits, slots, targets)
        loss = cross_entropy + 0.5 * torch.nn.functional.binary_cross_entropy_with_logits(
            halt_logits.float(), exact)
        loss.backward()
        self.assertIsNotNone(net.contexts.weight.grad)
        self.assertGreater(float(net.contexts.weight.grad.abs().sum()), 0)
        for index, block in enumerate(net.blocks):
            with self.subTest(block=index):
                self.assertIsNotNone(block.qkv.weight.grad)
                self.assertGreater(float(block.qkv.weight.grad.abs().sum()), 0)
                self.assertIsNotNone(block.mlp[0].weight.grad)
                self.assertGreater(float(block.mlp[0].weight.grad.abs().sum()), 0)

    def test_state_dict_roundtrip_preserves_raw_outputs(self):
        request = generated_requests()[0]
        net = AutoNet()
        before = infer_one(net, request)
        buffer = io.BytesIO()
        torch.save(net.state_dict(), buffer)
        buffer.seek(0)
        reloaded = AutoNet()
        reloaded.load_state_dict(torch.load(buffer, map_location="cpu", weights_only=True), strict=True)
        after = infer_one(reloaded, request)
        for left, right in zip(before, after):
            self.assertTrue(torch.equal(left, right))


if __name__ == "__main__":
    unittest.main()
