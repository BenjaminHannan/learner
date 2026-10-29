"""CPU-only crash recovery: terminate a real child without finally handlers."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from sleepmlx.backend import Stop
from sleepmlx.checkpoint import CheckpointError, Checkpoints, save_adapter_directory
from sleepmlx.paths import Paths, read_json, write_json
from .fakes import FakeBackend
from .helpers import Env, FACTS_DAY2, write_raw


class DurableBackend(FakeBackend):
    """Persist a step ledger and SHY count, so skipped/repeated work is visible."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.applied_steps = []
        self.shy_count = 0

    def train_step(self, batch, replay, step):
        result = super().train_step(batch, replay, step)
        self.applied_steps.append(step)
        return result

    def downscale(self, *args):
        self.shy_count += 1
        return super().downscale(*args)

    def save_adapter(self, path):
        super().save_adapter(path)
        f = Path(path) / "adapters.safetensors"
        data = json.loads(f.read_text())
        data.update(applied_steps=self.applied_steps, shy_count=self.shy_count)
        f.write_text(json.dumps(data))

    def load_adapter(self, path):
        super().load_adapter(path)
        data = json.loads((Path(path) / "adapters.safetensors").read_text()) if path else {}
        self.applied_steps = data.get("applied_steps", [])
        self.shy_count = data.get("shy_count", 0)


def run_until_exit(root, boundary):
    """Subprocess entry point; every path, including user data, is disposable."""
    root = Path(root)
    env = Env(ckpt_every=10, dreamcheck_share=0.0, gate_min_gain=0)
    env.paths = Paths(root / "home", root / "raw", root, root / "userdata")
    sleeper = env.sleeper(DurableBackend(env.time))

    def fault(stage):
        wanted = boundary
        if boundary.startswith("train_"):
            wanted = boundary[len("train_"):]
            if sleeper.N["phase"] != "train" or sleeper.N["done_steps"] != 10:
                return
        elif boundary.startswith("shy_"):
            wanted = boundary[len("shy_"):]
            if sleeper.N["phase"] != "gate":
                return
        if stage == wanted:
            os._exit(73)
    sleeper.checkpoint_hook = fault
    sleeper.run(env.week())
    raise AssertionError("fault boundary was not reached: " + boundary)


class CrashRecoveryTests(unittest.TestCase):
    def crash(self, env, stage):
        root = env.paths.home.parent
        child_env = dict(os.environ, SLEEPMLX_HOME=str(env.paths.home), SLEEPMLX_DIARY_DIR=str(env.paths.diary_dir),
                         SLEEPMLX_USERDATA=str(env.paths.userdata_dir), LEARNER_OPS=str(root), SLEEPMODE_OUT=str(root / "out.json"))
        result = subprocess.run([sys.executable, "-c",
                                 "from sleepmlx.tests.test_checkpoint import run_until_exit; import sys; run_until_exit(*sys.argv[1:])",
                                 str(root), stage], env=child_env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 73, result.stdout + result.stderr)

    def verify_finished(self, env, expected_nights=1):
        be = DurableBackend(env.time)
        result = env.sleeper(be).run(env.week())
        self.assertEqual(result["status"], "done", result)
        data = json.loads((env.paths.adapter / "adapters.safetensors").read_text())
        # For second-night tests the ledger contains both nights, in order.
        total = result["steps_total"]
        self.assertEqual(data["applied_steps"][-total:], list(range(total)))
        self.assertEqual(data["shy_count"], expected_nights)
        self.assertEqual(read_json(env.paths.state)["nights"], expected_nights)
        history = [json.loads(line) for line in env.paths.nights.read_text().splitlines()]
        self.assertEqual(len(history), expected_nights)
        self.assertEqual(len({row["night_id"] for row in history}), expected_nights)
        self.assertFalse(env.paths.work.exists())
        self.assertEqual(env.sleeper(DurableBackend(env.time)).run(env.week())["status"], "no_new_day")
        return result

    def test_hard_exit_at_checkpoint_shy_and_finalization_boundaries(self):
        stages = ["train_adapter_saved", "train_generation_ready", "train_manifest_published",
                  "shy_adapter_saved", "shy_generation_ready", "shy_manifest_published",
                  "promotion_ready", "promotion_published", "state_written", "items_written", "history_written", "finalized"]
        for stage in stages:
            with self.subTest(stage=stage):
                env = Env(ckpt_every=10, dreamcheck_share=0.0, gate_min_gain=0)
                try:
                    self.crash(env, stage)
                    night, items = Checkpoints(env.paths).load()
                    self.assertIsNotNone(items)
                    if night["done_steps"]:
                        saved = json.loads((env.paths.work_adapter / "adapters.safetensors").read_text())
                        self.assertEqual(saved["applied_steps"], list(range(night["done_steps"])))
                    else:
                        self.assertFalse(env.paths.work_adapter.exists())
                    self.assertGreater(len(list((env.paths.work / "checkpoints").glob("[0-9a-f]*"))), 1)
                    self.verify_finished(env)
                    self.assertFalse(env.paths.adapter_prev.exists())
                finally:
                    env.close()

    def test_second_night_promotion_is_idempotent_at_each_write(self):
        for stage in ("promotion_ready", "promotion_published", "state_written", "items_written", "history_written", "finalized"):
            with self.subTest(stage=stage):
                env = Env(ckpt_every=10, dreamcheck_share=0.0, gate_min_gain=0)
                try:
                    first = env.sleeper(DurableBackend(env.time)).run(env.week())
                    self.assertFalse(first["reverted"])
                    incumbent = env.paths.adapter
                    before = (incumbent / "adapters.safetensors").read_bytes()
                    write_raw(env.paths.diary_dir, "2026-10-21", FACTS_DAY2, conv="c2")
                    self.crash(env, stage)
                    self.verify_finished(env, expected_nights=2)
                    self.assertEqual(env.paths.adapter_prev, incumbent)
                    self.assertEqual((incumbent / "adapters.safetensors").read_bytes(), before)
                finally:
                    env.close()

    def test_exception_after_unsaved_update_retains_last_complete_generation(self):
        env = Env(ckpt_every=10, dreamcheck_share=0.0)
        try:
            be = DurableBackend(env.time)
            step = be.train_step
            def fail(batch, replay, i):
                result = step(batch, replay, i)
                if i == 10:
                    raise RuntimeError("after update, before progress")
                return result
            be.train_step = fail
            with self.assertRaisesRegex(RuntimeError, "after update"):
                env.sleeper(be).run(env.week())
            night, _ = Checkpoints(env.paths).load()
            self.assertEqual(night["done_steps"], 10)
            self.verify_finished(env)
        finally:
            env.close()

    def test_partial_rem_stop_rolls_back_bookkeeping(self):
        env = Env(ckpt_every=10, dreamcheck_share=0.0)
        try:
            sleeper = env.sleeper(DurableBackend(env.time))
            rem = sleeper.rem
            hit = []
            def stop_after_rem(*args):
                rem(*args)
                hit.append(True)
                raise Stop("budget")
            sleeper.rem = stop_after_rem
            result = sleeper.run(env.week())
            self.assertTrue(hit)
            self.assertEqual(result["status"], "stopped")
            night, items = Checkpoints(env.paths).load()
            self.assertEqual(night["rem_done"], [])
            self.assertEqual(items["rem_done"], {})
            self.assertEqual(items["gist_done"], {})
            self.assertEqual(items["rem_pool"], [])
            self.verify_finished(env)
        finally:
            env.close()

    def test_missing_required_checkpoint_fails_instead_of_starting_from_base(self):
        env = Env(dreamcheck_share=0.0)
        try:
            self.crash(env, "train_manifest_published")
            shutil.rmtree(env.paths.work_adapter)
            with self.assertRaisesRegex(CheckpointError, "required adapter"):
                env.sleeper(DurableBackend(env.time)).run(env.week())
        finally:
            env.close()

    def test_missing_legacy_checkpoint_fails_explicitly(self):
        env = Env()
        try:
            write_json(env.paths.night_json, {"phase": "train", "done_steps": 3})
            with self.assertRaisesRegex(CheckpointError, "required adapter"):
                Checkpoints(env.paths).load()
        finally:
            env.close()

    def test_finalization_uses_recorded_decision_when_diary_is_removed(self):
        env = Env(ckpt_every=10, dreamcheck_share=0.0, gate_min_gain=0)
        try:
            self.crash(env, "finalized")
            shutil.rmtree(env.paths.diary_dir)
            result = self.verify_finished(env)
            self.assertTrue(result["resumed"])
            self.assertEqual(result["steps"], 0)
        finally:
            env.close()

    def test_missing_committed_generation_does_not_fall_back_to_legacy(self):
        env = Env()
        try:
            env.backend().save_adapter(env.paths.home / "adapter")
            write_json(env.paths.home / "adapters.json", {"version": 1, "current": "adapters/missing", "previous": "adapter"})
            with self.assertRaisesRegex(RuntimeError, "required adapter is missing"):
                _ = env.paths.adapter
        finally:
            env.close()

    def test_snapshot_before_manifest_publication_uses_previous_complete_generation(self):
        env = Env(ckpt_every=10, dreamcheck_share=0.0)
        try:
            self.crash(env, "train_generation_ready")
            # Preserve the actual on-disk state of a killed process, including its
            # unpublished generation. Recovery must follow only night.json.
            with tempfile.TemporaryDirectory() as tmp:
                snapshot = Path(tmp) / "snapshot"
                shutil.copytree(env.paths.home, snapshot)
                env.paths.home = snapshot
                night, _ = Checkpoints(env.paths).load()
                self.assertLess(night["done_steps"], 10)
                result = env.sleeper(DurableBackend(env.time)).run(env.week())
                self.assertEqual(result["status"], "done")
                saved = json.loads((env.paths.adapter / "adapters.safetensors").read_text())
                self.assertEqual(saved["applied_steps"], list(range(result["steps_total"])))
        finally:
            env.close()

    def test_backend_save_never_deletes_previous_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "adapter"
            def write(path):
                (path / "adapters.safetensors").write_text("weights")
                (path / "adapter_config.json").write_text("{}")
            save_adapter_directory(destination, write)
            with self.assertRaises(FileExistsError):
                save_adapter_directory(destination, lambda path: self.fail("must not overwrite"))
            self.assertEqual((destination / "adapters.safetensors").read_text(), "weights")

    def test_backend_missing_non_none_adapter_fails_before_loading_gpu_libraries(self):
        from sleepmlx.model import MLXBackend
        from sleepmlx.torch_backend import TorchBackend
        with tempfile.TemporaryDirectory() as tmp:
            for cls in (MLXBackend, TorchBackend):
                with self.subTest(backend=cls.__name__):
                    with self.assertRaises(CheckpointError):
                        cls.load_adapter(object.__new__(cls), Path(tmp) / "missing")
