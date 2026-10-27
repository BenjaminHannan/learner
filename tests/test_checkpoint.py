import hashlib
import io
import json
from pathlib import Path
import pickle
import random
import tempfile
import unittest
from unittest import mock
import zipfile

import torch
from torch import nn

from memorylab.checkpoint import (
    CheckpointError,
    inspect_checkpoint_config,
    load_checkpoint,
    load_scored_restart,
    save_checkpoint,
)
from memorylab.model import MainNetwork, TokenSpec
from memorylab.storage import Budget, BudgetError


TOKEN_SPEC = TokenSpec(vocab_size=7, pad_id=0, eos_id=1)
CHECKPOINT_LIMIT = 1_000_000


def make_model():
    return MainNetwork(
        embed_width=3,
        hidden_width=4,
        reasoning_steps=1,
        max_reasoning_steps=1,
        max_decode_len=2,
        token_spec=TOKEN_SPEC,
    )


def make_budget(root):
    return Budget(root, hard=8_000_000, steady=6_000_000, free_floor=0)


def clone_state(module):
    return {key: value.detach().clone() for key, value in module.state_dict().items()}


def assert_state_equal(test, actual, expected):
    test.assertEqual(set(actual), set(expected))
    for key in expected:
        torch.testing.assert_close(actual[key], expected[key], rtol=0, atol=0)


def assert_nested_equal(test, actual, expected):
    if isinstance(expected, torch.Tensor):
        test.assertIsInstance(actual, torch.Tensor)
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)
        return
    if isinstance(expected, dict):
        test.assertIsInstance(actual, dict)
        test.assertEqual(set(actual), set(expected))
        for key in expected:
            assert_nested_equal(test, actual[key], expected[key])
        return
    if isinstance(expected, (list, tuple)):
        test.assertIsInstance(actual, type(expected))
        test.assertEqual(len(actual), len(expected))
        for left, right in zip(actual, expected):
            assert_nested_equal(test, left, right)
        return
    test.assertEqual(actual, expected)


def read_members(path):
    with zipfile.ZipFile(path, "r") as archive:
        return {info.filename: archive.read(info.filename) for info in archive.infolist()}


def write_members(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for name, data in members.items():
            archive.writestr(name, data)


def canonical_json(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def rewrite_metadata_with_valid_hash(path, mutate):
    members = read_members(path)
    metadata = json.loads(members["metadata.json"])
    mutate(metadata)
    metadata_bytes = canonical_json(metadata)
    manifest = json.loads(members["manifest.json"])
    manifest["members"]["metadata.json"] = {
        "bytes": len(metadata_bytes),
        "sha256": hashlib.sha256(metadata_bytes).hexdigest(),
    }
    members["metadata.json"] = metadata_bytes
    members["manifest.json"] = canonical_json(manifest)
    write_members(path, members)


class CheckpointTests(unittest.TestCase):
    def make_saved_checkpoint(self, root, *, optimizer=True):
        budget = make_budget(root)
        torch.manual_seed(123)
        theta = nn.Sequential(nn.Linear(3, 5), nn.Tanh(), nn.Linear(5, 2))
        model = make_model()
        phi = model.writer
        W = torch.arange(128 * 128, dtype=torch.float32).reshape(128, 128) / 1000.0

        opt = None
        if optimizer:
            opt = torch.optim.SGD(
                list(theta.parameters()) + list(phi.parameters()),
                lr=0.05,
                momentum=0.9,
            )
            for parameter in list(theta.parameters()) + list(phi.parameters()):
                parameter.grad = torch.ones_like(parameter)
            opt.step()
            opt.zero_grad(set_to_none=True)

        path = save_checkpoint(
            budget,
            "artifacts/checkpoint.zip",
            theta,
            phi,
            W,
            optimizer=opt,
            config={"trial": 3, "name": "offline-test"},
            max_bytes=CHECKPOINT_LIMIT,
        )
        return path, theta, model, W, opt

    def test_round_trip_theta_separate_writer_optimizer_exact_W_and_cpu_map_location(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, theta, model, W, optimizer = self.make_saved_checkpoint(root)
            theta_expected = clone_state(theta)
            phi_expected = clone_state(model.writer)
            optimizer_expected = optimizer.state_dict()

            restored_theta = nn.Sequential(nn.Linear(3, 5), nn.Tanh(), nn.Linear(5, 2))
            restored_model = make_model()
            restored_optimizer = torch.optim.SGD(
                list(restored_theta.parameters()) + list(restored_model.writer.parameters()),
                lr=0.9,
                momentum=0.1,
            )

            loaded = load_checkpoint(
                path,
                restored_theta,
                restored_model.writer,
                optimizer=restored_optimizer,
                map_location=torch.device("cpu"),
                restore_rng=False,
                max_bytes=CHECKPOINT_LIMIT,
            )

            assert_state_equal(self, restored_theta.state_dict(), theta_expected)
            assert_state_equal(self, restored_model.writer.state_dict(), phi_expected)
            assert_nested_equal(self, restored_optimizer.state_dict(), optimizer_expected)
            self.assertTrue(torch.equal(loaded.W, W))
            self.assertEqual(loaded.W.device.type, "cpu")
            self.assertTrue(all(parameter.device.type == "cpu" for parameter in restored_theta.parameters()))
            self.assertTrue(all(parameter.device.type == "cpu" for parameter in restored_model.writer.parameters()))
            self.assertEqual(loaded.config, {"trial": 3, "name": "offline-test"})
            self.assertIsNone(loaded.workspace)
            self.assertEqual(
                inspect_checkpoint_config(path, max_bytes=CHECKPOINT_LIMIT),
                {"trial": 3, "name": "offline-test"},
            )

    def test_scored_restart_restores_only_persistent_state_and_leaves_rng_optimizer_alone(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, theta, model, W, _ = self.make_saved_checkpoint(root)
            theta_expected = clone_state(theta)
            phi_expected = clone_state(model.writer)

            restored_theta = nn.Sequential(nn.Linear(3, 5), nn.Tanh(), nn.Linear(5, 2))
            restored_model = make_model()
            optimizer = torch.optim.SGD(
                list(restored_theta.parameters()) + list(restored_model.writer.parameters()),
                lr=0.2,
                momentum=0.9,
            )
            for parameter in list(restored_theta.parameters()) + list(restored_model.writer.parameters()):
                parameter.grad = torch.full_like(parameter, 2.0)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            optimizer_before = optimizer.state_dict()

            random.seed(9182)
            torch.manual_seed(8172)
            python_rng_before = random.getstate()
            torch_rng_before = torch.random.get_rng_state().clone()

            with mock.patch(
                "memorylab.checkpoint.restore_rng_state",
                side_effect=AssertionError("scored restart must not restore RNG"),
            ) as restore_rng:
                restart = load_scored_restart(
                    path,
                    restored_theta,
                    restored_model.writer,
                    map_location="cpu",
                    max_bytes=CHECKPOINT_LIMIT,
                )

            restore_rng.assert_not_called()
            assert_state_equal(self, restored_theta.state_dict(), theta_expected)
            assert_state_equal(self, restored_model.writer.state_dict(), phi_expected)
            self.assertTrue(torch.equal(restart.W, W))
            self.assertIsNone(restart.workspace)
            assert_nested_equal(self, optimizer.state_dict(), optimizer_before)
            self.assertEqual(random.getstate(), python_rng_before)
            self.assertTrue(torch.equal(torch.random.get_rng_state(), torch_rng_before))

    def test_expected_config_mismatch_is_rejected_before_module_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, _, _, _, _ = self.make_saved_checkpoint(root, optimizer=False)
            restored_theta = nn.Sequential(nn.Linear(3, 5), nn.Tanh(), nn.Linear(5, 2))
            restored_model = make_model()
            theta_before = clone_state(restored_theta)
            phi_before = clone_state(restored_model.writer)

            with self.assertRaisesRegex(CheckpointError, "config does not match"):
                load_scored_restart(
                    path,
                    restored_theta,
                    restored_model.writer,
                    expected_config={"trial": 4, "name": "offline-test"},
                    max_bytes=CHECKPOINT_LIMIT,
                )

            assert_state_equal(self, restored_theta.state_dict(), theta_before)
            assert_state_equal(self, restored_model.writer.state_dict(), phi_before)

    def test_save_is_no_clobber_and_respects_max_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, theta, model, W, optimizer = self.make_saved_checkpoint(root)
            original = path.read_bytes()
            budget = make_budget(root)

            with self.assertRaisesRegex(BudgetError, "Refusing to overwrite"):
                save_checkpoint(
                    budget,
                    "artifacts/checkpoint.zip",
                    theta,
                    model.writer,
                    W,
                    optimizer=optimizer,
                    max_bytes=CHECKPOINT_LIMIT,
                )
            self.assertEqual(path.read_bytes(), original)

            with self.assertRaisesRegex(CheckpointError, "would exceed"):
                save_checkpoint(
                    budget,
                    "artifacts/too-small.zip",
                    theta,
                    model.writer,
                    W,
                    max_bytes=1024,
                )
            self.assertFalse((root / "artifacts" / "too-small.zip").exists())

            with self.assertRaisesRegex(CheckpointError, "bounded regular file"):
                load_checkpoint(
                    path,
                    theta,
                    model.writer,
                    restore_rng=False,
                    max_bytes=path.stat().st_size - 1,
                )

    def test_W_must_use_a_registered_single_or_four_head_shape_and_float32(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budget = make_budget(root)
            theta = nn.Linear(2, 2)
            phi = make_model().writer

            for name, W in (
                ("shape", torch.zeros(128, 127, dtype=torch.float32)),
                ("dtype", torch.zeros(128, 128, dtype=torch.float64)),
            ):
                with self.subTest(name=name):
                    with self.assertRaisesRegex(
                        CheckpointError, "shape \\(128, 128\\) or \\(4, 128, 128\\) and dtype float32"
                    ):
                        save_checkpoint(
                            budget,
                            f"artifacts/bad-{name}.zip",
                            theta,
                            phi,
                            W,
                            max_bytes=CHECKPOINT_LIMIT,
                        )

    def test_four_head_persistent_memory_round_trips_exactly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budget = make_budget(root)
            theta = nn.Sequential(nn.Linear(3, 5), nn.Tanh(), nn.Linear(5, 2))
            model = make_model()
            W = torch.arange(
                4 * 128 * 128,
                dtype=torch.float32,
            ).reshape(4, 128, 128) / 10_000.0
            path = save_checkpoint(
                budget,
                "artifacts/four-head.zip",
                theta,
                model.writer,
                W,
                max_bytes=CHECKPOINT_LIMIT,
            )
            loaded = load_scored_restart(path, theta, model.writer)
            torch.testing.assert_close(loaded.W, W, rtol=0, atol=0)
            self.assertEqual(
                loaded.manifest["persistent_memory"]["shape"],
                [4, 128, 128],
            )

    def test_hash_and_manifest_tampering_and_unexpected_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, _, _, _, _ = self.make_saved_checkpoint(root)
            original = read_members(source)

            cases = []

            metadata_members = dict(original)
            metadata = json.loads(metadata_members["metadata.json"])
            metadata["config"]["tampered"] = True
            metadata_members["metadata.json"] = canonical_json(metadata)
            cases.append(("metadata", metadata_members, "SHA-256 validation failed for metadata.json"))

            tensor_members = dict(original)
            tensors = bytearray(tensor_members["tensors.bin"])
            tensors[0] ^= 0x01
            tensor_members["tensors.bin"] = bytes(tensors)
            cases.append(("tensors", tensor_members, "SHA-256 validation failed for tensors.bin"))

            manifest_members = dict(original)
            manifest = json.loads(manifest_members["manifest.json"])
            manifest["workspace_persisted"] = True
            manifest_members["manifest.json"] = canonical_json(manifest)
            cases.append(("manifest", manifest_members, "Invalid checkpoint safety manifest"))

            extra_members = dict(original)
            extra_members["payload.pkl"] = pickle.dumps({"should": "never load"})
            cases.append(("extra-member", extra_members, "unexpected archive members"))

            for name, members, error in cases:
                with self.subTest(name=name):
                    path = root / f"{name}.zip"
                    write_members(path, members)
                    with self.assertRaisesRegex(CheckpointError, error):
                        load_scored_restart(path, nn.Sequential(nn.Linear(3, 5), nn.Tanh(), nn.Linear(5, 2)), make_model().writer)

    def test_validly_rehashed_malformed_W_shape_and_dtype_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, _, _, _, _ = self.make_saved_checkpoint(root, optimizer=False)
            original = source.read_bytes()

            for name, mutate_entry in (
                ("shape", lambda entry: entry.__setitem__("shape", [64, 256])),
                ("dtype", lambda entry: entry.__setitem__("dtype", "int32")),
            ):
                with self.subTest(name=name):
                    path = root / f"malformed-{name}.zip"
                    path.write_bytes(original)

                    def mutate(metadata):
                        W_id = metadata["W"]["__tensor__"]
                        entry = next(item for item in metadata["tensor_table"] if item["id"] == W_id)
                        mutate_entry(entry)

                    rewrite_metadata_with_valid_hash(path, mutate)
                    with self.assertRaisesRegex(
                        CheckpointError, "W must have shape \\(128, 128\\) or \\(4, 128, 128\\) and dtype float32"
                    ):
                        load_scored_restart(
                            path,
                            nn.Sequential(nn.Linear(3, 5), nn.Tanh(), nn.Linear(5, 2)),
                            make_model().writer,
                        )

    def test_malformed_tensor_table_shape_and_dtype_are_rejected_after_rehash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, _, _, _, _ = self.make_saved_checkpoint(root, optimizer=False)
            original = source.read_bytes()

            for name, mutate, error in (
                (
                    "shape",
                    lambda entry: entry.__setitem__("shape", ["not-an-int"]),
                    "Invalid tensor shape",
                ),
                (
                    "dtype",
                    lambda entry: entry.__setitem__("dtype", "pickle-object"),
                    "Invalid tensor id or dtype",
                ),
            ):
                with self.subTest(name=name):
                    path = root / f"table-{name}.zip"
                    path.write_bytes(original)

                    def mutate_metadata(metadata):
                        mutate(metadata["tensor_table"][0])

                    rewrite_metadata_with_valid_hash(path, mutate_metadata)
                    with self.assertRaisesRegex(CheckpointError, error):
                        load_scored_restart(
                            path,
                            nn.Sequential(nn.Linear(3, 5), nn.Tanh(), nn.Linear(5, 2)),
                            make_model().writer,
                        )

    def test_checkpoint_never_calls_torch_load_or_pickle_loaders(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budget = make_budget(root)
            theta = nn.Linear(2, 2)
            model = make_model()
            W = torch.zeros(128, 128, dtype=torch.float32)

            with (
                mock.patch.object(torch, "load", side_effect=AssertionError("torch.load called")) as torch_load,
                mock.patch.object(pickle, "load", side_effect=AssertionError("pickle.load called")) as pickle_load,
                mock.patch.object(pickle, "loads", side_effect=AssertionError("pickle.loads called")) as pickle_loads,
            ):
                path = save_checkpoint(
                    budget,
                    "checkpoint.zip",
                    theta,
                    model.writer,
                    W,
                    max_bytes=CHECKPOINT_LIMIT,
                )
                loaded = load_checkpoint(
                    path,
                    nn.Linear(2, 2),
                    make_model().writer,
                    restore_rng=False,
                    map_location="cpu",
                    max_bytes=CHECKPOINT_LIMIT,
                )

            torch_load.assert_not_called()
            pickle_load.assert_not_called()
            pickle_loads.assert_not_called()
            self.assertTrue(torch.equal(loaded.W, W))


if __name__ == "__main__":
    unittest.main()
