"""read_only must catch every write path an evaluation can take and never flag a clean one."""
from __future__ import annotations

import copy
import random
import unittest
import warnings
from typing import Any, Callable

import torch
from torch import nn

from learnlab.readonly import (
    ReadOnlyViolation,
    read_only,
    rng_state,
    set_rng_state,
    tensor_digest,
)


class Store:
    """Minimal fingerprinted store."""

    def __init__(self) -> None:
        self.items: dict[str, str] = {}

    def write(self, key: str, value: str) -> None:
        self.items[key] = value

    def read(self, key: str) -> str | None:
        return self.items.get(key)

    def fingerprint(self) -> str:
        return repr(sorted(self.items.items()))


class Rotary(nn.Module):
    """A derived cache that legitimately grows when evaluation sees a longer input."""

    def __init__(self) -> None:
        super().__init__()
        self.register_buffer("cos_cached", torch.ones(8), persistent=False)
        self.cached_len = 8

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.shape[0] > self.cos_cached.shape[0]:
            self.cos_cached = torch.cos(torch.arange(x.shape[0]).float())
            self.cached_len = x.shape[0]
        return x * self.cos_cached[: x.shape[0]]


def small_net() -> nn.Sequential:
    torch.manual_seed(0)
    return nn.Sequential(
        nn.Linear(4, 8), nn.BatchNorm1d(8), nn.ReLU(), nn.Dropout(0.5), nn.Linear(8, 2)
    )


def trained_adam(model: nn.Module) -> torch.optim.Adam:
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    model(torch.randn(6, 4)).pow(2).mean().backward()
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    return optimizer


class GuardTestCase(unittest.TestCase):
    def assertViolation(self, block: Callable[[], Any], *, mentions: str = "") -> ReadOnlyViolation:
        with self.assertRaises(ReadOnlyViolation) as caught:
            block()
        if mentions:
            self.assertIn(mentions, str(caught.exception.changes))
        return caught.exception

    def assertClean(self, block: Callable[[], Any]) -> None:
        try:
            block()
        except ReadOnlyViolation as error:  # pragma: no cover - failure path
            self.fail(f"false positive: {error}")


class ExceptionPathTests(GuardTestCase):
    def test_mutation_then_exception_raises_violation_chained_from_the_error(self):
        model = nn.Linear(1, 1, bias=False)
        original = RuntimeError("evaluation failed")

        def block():
            with read_only(model):
                model.weight.add_(1.0)
                raise original

        violation = self.assertViolation(block, mentions="parameter weight")
        self.assertIs(violation.__cause__, original)

    def test_store_write_then_exception_the_caller_catches_still_escapes(self):
        store = Store()

        def block():
            try:
                with read_only(None, [store]):
                    store.write("nera", "barn")
                    raise KeyError("parse failure")
            except KeyError:
                pass  # an evaluator that scores errors as wrong answers

        violation = self.assertViolation(block, mentions="store[0]")
        self.assertIsInstance(violation.__cause__, KeyError)

    def test_exception_without_change_reraises_the_original(self):
        model = small_net()
        model.train()
        original = ValueError("bad batch")
        with self.assertRaises(ValueError) as caught:
            with read_only(model):
                model(torch.randn(3, 4))
                raise original
        self.assertIs(caught.exception, original)
        self.assertTrue(all(module.training for module in model.modules()))
        self.assertTrue(torch.is_grad_enabled())

    def test_stop_iteration_does_not_swallow_the_violation(self):
        # contextlib.contextmanager drops an exception chained from StopIteration.
        model = nn.Linear(1, 1, bias=False)
        with self.assertRaises(ReadOnlyViolation):
            with read_only(model):
                model.weight.add_(1.0)
                next(iter(()))

    def test_keyboard_interrupt_is_never_masked_but_state_is_restored(self):
        model = small_net()
        model.train()
        torch.manual_seed(3)
        expected = torch.rand(1)
        torch.manual_seed(3)
        with self.assertRaises(KeyboardInterrupt):
            with read_only(model):
                model[0].weight.add_(1.0)
                torch.rand(5)
                raise KeyboardInterrupt
        self.assertTrue(all(module.training for module in model.modules()))
        self.assertTrue(torch.equal(torch.rand(1), expected))


class TensorRecordTests(GuardTestCase):
    def test_in_place_weight_change(self):
        model = nn.Linear(4, 2)

        def block():
            with read_only(model):
                model.weight.add_(0.01)

        self.assertViolation(block, mentions="content")

    def test_same_value_parameter_replacement(self):
        model = nn.Linear(2, 2, bias=False)

        def block():
            with read_only(model):
                model.weight = nn.Parameter(model.weight.detach().clone())

        self.assertViolation(block, mentions="identity")

    def test_same_value_buffer_replacement(self):
        model = nn.BatchNorm1d(3)

        def block():
            with read_only(model):
                model.running_mean = model.running_mean.clone()

        self.assertViolation(block, mentions="buffer running_mean: identity")

    def test_same_value_storage_swap_through_data(self):
        model = nn.Linear(2, 2, bias=False)

        def block():
            with read_only(model):
                model.weight.data = model.weight.data.clone()

        self.assertViolation(block, mentions="storage")

    def test_requires_grad_change(self):
        model = nn.Linear(2, 2, bias=False)

        def block():
            with read_only(model):
                model.weight.requires_grad_(False)

        self.assertViolation(block, mentions="requires_grad")

    def test_mutate_then_revert_is_caught_by_the_version_counter(self):
        model = nn.Linear(1, 1, bias=False)
        before = model.weight.detach().clone()

        def block():
            with read_only(model):
                model.weight.add_(1.0)
                model.weight.sub_(1.0)

        self.assertViolation(block, mentions="version")
        self.assertTrue(torch.equal(before, model.weight.detach()))

    def test_grad_left_behind(self):
        model = nn.Linear(4, 1)

        def block():
            with read_only(model):
                with torch.enable_grad():
                    model(torch.randn(8, 4)).sum().backward()

        self.assertViolation(block, mentions="parameter weight: grad")

    def test_existing_grad_cleared(self):
        model = nn.Linear(4, 1)
        model(torch.randn(8, 4)).sum().backward()

        def block():
            with read_only(model):
                model.zero_grad(set_to_none=True)

        self.assertViolation(block, mentions="parameter weight: grad")

    def test_train_then_restore_weights(self):
        model = nn.Linear(4, 1)

        def block():
            with read_only(model):
                saved = copy.deepcopy(model.state_dict())
                optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
                with torch.enable_grad():
                    model(torch.randn(8, 4)).pow(2).mean().backward()
                optimizer.step()
                model.load_state_dict(saved)
                for param in model.parameters():
                    param.grad = None  # hide every trace except the version counter

        violation = self.assertViolation(block, mentions="version")
        self.assertNotIn("content", str(violation.changes))

    def test_dtype_cast(self):
        model = nn.Linear(2, 2)

        def block():
            with read_only(model):
                model.half()

        self.assertViolation(block, mentions="dtype")

    def test_parameter_added_and_removed(self):
        model = nn.Linear(4, 2)

        def add():
            with read_only(model):
                model.extra = nn.Parameter(torch.zeros(1))

        self.assertViolation(add, mentions="parameter extra: added")
        model = nn.Linear(4, 2)

        def remove():
            with read_only(model):
                del model.bias
                model.register_parameter("bias", None)

        self.assertViolation(remove, mentions="parameter bias: set to None")

    def test_buffer_removed_and_persistence_flipped(self):
        model = nn.Module()
        model.register_buffer("buf", torch.tensor(1.0))

        def remove():
            with read_only(model):
                del model.buf

        self.assertViolation(remove, mentions="buffer buf: removed")
        model = nn.Module()
        model.register_buffer("buf", torch.tensor(1.0))

        def flip():
            with read_only(model):
                model._non_persistent_buffers_set.add("buf")

        self.assertViolation(flip, mentions="persistent")

    def test_non_persistent_buffer_change(self):
        model = nn.Module()
        model.register_buffer("scratch", torch.zeros(3), persistent=False)

        def block():
            with read_only(model):
                model.scratch.add_(1.0)

        self.assertViolation(block, mentions="buffer scratch")

    def test_submodule_replaced(self):
        model = nn.Sequential(nn.Linear(2, 2), nn.ReLU())

        def block():
            with read_only(model):
                model[1] = nn.ReLU()

        self.assertViolation(block, mentions="module 1: replaced")

    def test_untied_shared_weight(self):
        model = nn.Module()
        model.encoder = nn.Embedding(5, 3)
        model.decoder = nn.Linear(3, 5, bias=False)
        model.decoder.weight = model.encoder.weight

        def block():
            with read_only(model):
                model.decoder.weight = nn.Parameter(model.encoder.weight.detach().clone())

        self.assertViolation(block, mentions="decoder.weight: identity")

    def test_zero_dim_and_bfloat16_tensors(self):
        model = nn.Module()
        model.scale = nn.Parameter(torch.tensor(1.0, dtype=torch.bfloat16))
        self.assertEqual(len(tensor_digest(model.scale)), 64)

        def block():
            with read_only(model):
                model.scale.add_(1.0)

        self.assertViolation(block, mentions="scale")


class ModeTests(GuardTestCase):
    def test_frozen_batchnorm_stays_frozen(self):
        model = nn.Sequential(nn.Linear(3, 3), nn.BatchNorm1d(3))
        model.train()
        model[1].eval()  # frozen BN inside a training model
        with read_only(model):
            self.assertFalse(any(module.training for module in model.modules()))
            model(torch.randn(4, 3))
        self.assertTrue(model.training)
        self.assertTrue(model[0].training)
        self.assertFalse(model[1].training)
        stats = model[1].running_mean.clone()
        model(torch.randn(4, 3))  # the next training forward must not touch frozen stats
        self.assertTrue(torch.equal(stats, model[1].running_mean))

    def test_every_flag_restored_after_an_exception(self):
        model = small_net()
        model.train()
        model[1].eval()
        flags = [module.training for module in model.modules()]
        with self.assertRaises(RuntimeError):
            with read_only(model):
                raise RuntimeError("boom")
        self.assertEqual(flags, [module.training for module in model.modules()])

    def test_block_runs_without_grad_and_grad_mode_is_restored(self):
        model = nn.Linear(2, 2)
        with read_only(model):
            self.assertFalse(torch.is_grad_enabled())
            self.assertFalse(model(torch.randn(1, 2)).requires_grad)
        self.assertTrue(torch.is_grad_enabled())
        with torch.no_grad():
            with read_only(model):
                pass
            self.assertFalse(torch.is_grad_enabled())

    def test_training_mode_forward_inside_the_block_is_caught_and_flags_restored(self):
        model = small_net()
        model.eval()

        def block():
            with read_only(model):
                model.train()
                model(torch.randn(4, 4))

        self.assertViolation(block, mentions="running_mean")
        self.assertFalse(any(module.training for module in model.modules()))


class PythonStateTests(GuardTestCase):
    def test_list_append_on_a_module(self):
        model = nn.Linear(4, 2)
        model.cards = []

        def block():
            with read_only(model):
                model.cards.append("nera+where=mill")

        self.assertViolation(block, mentions="attribute cards")

    def test_counter_increment_is_caught_unless_allowlisted(self):
        model = nn.Linear(4, 2)
        model.calls = 0

        def block(allow=()):
            with read_only(model, allow_changes=allow):
                model.calls += 1

        self.assertViolation(block, mentions="attribute calls")
        self.assertClean(lambda: block(allow=["calls"]))

    def test_new_attribute(self):
        model = nn.Sequential(nn.Linear(4, 2))

        def block():
            with read_only(model):
                model[0].note = "seen"

        self.assertViolation(block, mentions="attribute 0.note: added")

    def test_hook_left_behind_is_caught_but_a_removed_hook_is_not(self):
        model = nn.Linear(2, 2)

        def leak():
            with read_only(model):
                model.register_forward_hook(lambda *args: None)

        self.assertViolation(leak, mentions="_forward_hooks")
        model = nn.Linear(2, 2)

        def tidy():
            with read_only(model):
                handle = model.register_forward_hook(lambda *args: None)
                model(torch.randn(1, 2))
                handle.remove()

        self.assertClean(tidy)

    def test_unregistered_tensor_attribute_is_refused_before_the_block_runs(self):
        model = nn.Linear(4, 2)
        model.memory = torch.zeros(4)
        ran = []

        def block():
            with read_only(model):
                ran.append(True)

        self.assertViolation(block, mentions="unregistered tensor attribute memory")
        self.assertEqual(ran, [])

    def test_unregistered_tensor_in_a_container_is_refused(self):
        model = nn.Linear(4, 2)
        model.examples = [torch.zeros(2)]

        def block():
            with read_only(model):
                pass

        self.assertViolation(block, mentions="examples")

    def test_allowlisted_unregistered_tensor_may_change(self):
        model = nn.Linear(4, 2)
        model.memory = torch.zeros(4)

        def block():
            with read_only(model, allow_changes=["memory"]):
                model.memory += 1

        self.assertClean(block)

    def test_unregistered_tensor_created_during_the_block(self):
        model = nn.Linear(4, 2)

        def block():
            with read_only(model):
                model.memory = torch.zeros(4)

        self.assertViolation(block, mentions="unregistered tensor attribute memory")


class OptimizerTests(GuardTestCase):
    def test_optimizer_state_only_change(self):
        model = nn.Linear(1, 1)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        param = next(iter(model.parameters()))
        optimizer.state[param]["step"] = torch.tensor(7.0)

        def block():
            with read_only(model, optimizers=[optimizer]):
                optimizer.state[param]["step"].add_(1)

        self.assertViolation(block, mentions="optimizers[0] Adam")

    def test_learning_rate_change(self):
        model = nn.Linear(4, 1)
        optimizer = trained_adam(model)

        def block():
            with read_only(model, optimizers=[optimizer]):
                optimizer.param_groups[0]["lr"] = 123.0

        self.assertViolation(block, mentions="optimizers[0]")

    def test_moment_mutate_then_revert(self):
        model = nn.Linear(4, 1)
        optimizer = trained_adam(model)

        def block():
            with read_only(model, optimizers=[optimizer]):
                for state in optimizer.state.values():
                    state["exp_avg"].add_(5)
                    state["exp_avg"].sub_(5)

        self.assertViolation(block, mentions="optimizers[0]")

    def test_scheduler_step(self):
        model = nn.Linear(4, 1)
        optimizer = trained_adam(model)
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5)

        def block():
            with read_only(model, optimizers=[scheduler]):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")  # step-order warning is irrelevant here
                    scheduler.step()

        self.assertViolation(block, mentions="StepLR")

    def test_untouched_optimizer_is_clean(self):
        model = small_net()
        optimizer = trained_adam(model)
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5)

        def block():
            with read_only(model, optimizers=[optimizer, scheduler]):
                model(torch.randn(3, 4))

        self.assertClean(block)

    def test_object_without_state_dict_is_rejected(self):
        with self.assertRaises(TypeError):
            read_only(None, optimizers=[object()])


class RngTests(GuardTestCase):
    def test_clean_eval_that_uses_rng_is_restored_and_not_flagged(self):
        model = small_net()
        torch.manual_seed(11)
        random.seed(11)
        expected = (torch.rand(3), random.random())
        torch.manual_seed(11)
        random.seed(11)

        def block():
            with read_only(model):
                model(torch.randn(3, 4))
                torch.nn.functional.dropout(torch.ones(10), 0.5, training=True)
                random.shuffle(list(range(10)))

        self.assertClean(block)
        self.assertTrue(torch.equal(torch.rand(3), expected[0]))
        self.assertEqual(random.random(), expected[1])

    def test_rng_restored_after_an_exception(self):
        state = rng_state()
        with self.assertRaises(RuntimeError):
            with read_only(None):
                torch.randn(4)
                random.random()
                raise RuntimeError("boom")
        self.assertTrue(torch.equal(torch.get_rng_state(), state["torch"]))
        self.assertEqual(random.getstate(), state["python"])

    def test_restore_rng_false_lets_evaluation_advance_rng(self):
        torch.manual_seed(5)
        before = torch.get_rng_state()
        with read_only(None, restore_rng=False):
            torch.randn(4)
        self.assertFalse(torch.equal(torch.get_rng_state(), before))

    def test_generator_held_by_a_module_is_restored_but_replacing_it_is_caught(self):
        model = nn.Linear(2, 2)
        model.noise = torch.Generator().manual_seed(7)
        model.picker = random.Random(7)
        expected = (torch.rand(3, generator=model.noise), model.picker.random())
        model.noise.manual_seed(7)
        model.picker.seed(7)

        def consume():
            with read_only(model):
                torch.rand(5, generator=model.noise)
                model.picker.random()

        self.assertClean(consume)
        self.assertTrue(torch.equal(torch.rand(3, generator=model.noise), expected[0]))
        self.assertEqual(model.picker.random(), expected[1])

        def replace():
            with read_only(model):
                model.noise = torch.Generator().manual_seed(7)

        self.assertViolation(replace, mentions="attribute noise")

    def test_rng_state_round_trip(self):
        state = rng_state()
        first = (torch.rand(2), random.random())
        set_rng_state(state)
        self.assertTrue(torch.equal(torch.rand(2), first[0]))
        self.assertEqual(random.random(), first[1])


class AllowlistTests(GuardTestCase):
    def test_growing_derived_cache_is_flagged_unless_allowlisted(self):
        def block(model, allow=()):
            with read_only(model, allow_changes=allow):
                model(torch.randn(32))

        self.assertViolation(lambda: block(Rotary()), mentions="cos_cached")
        self.assertClean(lambda: block(Rotary(), ["cos_cached", "cached_len"]))

    def test_glob_patterns_cover_nested_caches(self):
        model = nn.ModuleList([Rotary(), Rotary()])

        def block():
            with read_only(model, allow_changes=["*.cos_cached", "*.cached_len"]):
                for layer in model:
                    layer(torch.randn(16))

        self.assertClean(block)

    def test_allowlist_does_not_hide_other_changes(self):
        model = nn.Sequential(Rotary(), nn.Linear(2, 2))

        def block():
            with read_only(model, allow_changes=["*cos_cached", "*cached_len"]):
                model[0](torch.randn(32))
                model[1].weight.add_(1.0)

        violation = self.assertViolation(block, mentions="1.weight")
        self.assertNotIn("cos_cached", str(violation.changes))

    def test_parameters_can_never_be_allowlisted(self):
        with self.assertRaises(ValueError):
            with read_only(nn.Linear(2, 2), allow_changes=["*"]):
                pass

    def test_a_bare_string_is_rejected(self):
        with self.assertRaises(TypeError):
            read_only(Rotary(), allow_changes="cos_cached")


class StoreTests(GuardTestCase):
    def test_store_without_fingerprint_is_a_type_error_at_entry(self):
        ran = []
        with self.assertRaises(TypeError):
            with read_only(None, [object()]):
                ran.append(True)
        self.assertEqual(ran, [])

    def test_store_write_is_caught_and_read_is_clean(self):
        store = Store()
        store.write("nera", "barn")

        def write():
            with read_only(None, [store]):
                store.write("bafe", "mill")

        def read():
            with read_only(None, [store]):
                self.assertEqual(store.read("nera"), "barn")

        self.assertClean(read)
        self.assertViolation(write, mentions="store[0] Store")


class CleanControlTests(GuardTestCase):
    def test_ordinary_eval_forward_with_batchnorm_and_dropout(self):
        model = small_net()
        model.train()
        stats = model[1].running_mean.clone()
        x = torch.randn(5, 4)
        with read_only(model):
            first = model(x)
            second = model(x)
        self.assertTrue(torch.equal(first, second))  # dropout off, batch stats not used
        self.assertTrue(torch.equal(stats, model[1].running_mean))
        self.assertTrue(all(module.training for module in model.modules()))

    def test_model_already_in_eval_with_existing_gradients(self):
        model = small_net()
        model(torch.randn(6, 4)).sum().backward()
        model.eval()

        def block():
            for _ in range(3):
                with read_only(model):
                    model(torch.randn(2, 4))

        self.assertClean(block)
        self.assertIsNotNone(model[0].weight.grad)

    def test_standard_module_zoo_in_eval(self):
        torch.manual_seed(0)
        model = nn.ModuleDict({
            "conv": nn.Sequential(nn.Conv2d(1, 2, 3), nn.BatchNorm2d(2), nn.GELU()),
            "embed": nn.Embedding(10, 8),
            "lstm": nn.LSTM(8, 8, batch_first=True),
            "gru": nn.GRU(8, 8, batch_first=True),
            "attention": nn.MultiheadAttention(8, 2, batch_first=True),
            "encoder": nn.TransformerEncoder(
                nn.TransformerEncoderLayer(8, 2, 16, batch_first=True), 2,
                enable_nested_tensor=False,
            ),
            "norm": nn.LayerNorm(8),
            "head": nn.Linear(8, 10, bias=False),
        })
        model["head"].weight = model["embed"].weight  # tied weights
        model.train()

        def block():
            with read_only(model):
                model["conv"](torch.randn(2, 1, 6, 6))
                tokens = model["embed"](torch.randint(0, 10, (2, 5)))
                states, _ = model["lstm"](tokens)
                states, _ = model["gru"](states)
                states, _ = model["attention"](states, states, states)
                model["head"](model["norm"](model["encoder"](states)))

        self.assertClean(block)
        self.assertTrue(all(module.training for module in model.modules()))

    def test_defensive_device_and_dtype_moves_are_clean(self):
        # A no-op .to() rebuilds an RNN's _flat_weights lists; the weights are untouched.
        model = nn.Sequential(nn.Linear(3, 3), nn.LSTM(3, 3))

        def block():
            with read_only(model):
                model.to("cpu").float()
                model.cpu()

        self.assertClean(block)

    def test_model_none_and_no_stores_is_a_no_op(self):
        with read_only(None):
            pass
        self.assertTrue(torch.is_grad_enabled())


if __name__ == "__main__":
    unittest.main()
