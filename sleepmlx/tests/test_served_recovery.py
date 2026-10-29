"""CPU-only recovery of deferred checks; all model/output paths are disposable."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from sleepmlx import export, served, worker
from sleepmlx.backend import Guards
from sleepmlx.paths import read_json, write_json
from .helpers import Env, FACTS_DAY2, write_raw


def finish_until_exit(root, boundary):
    from sleepmlx.paths import Paths
    from sleepmlx.profile import load_profile
    from sleepmlx.recipe import Config
    root = Path(root)
    paths = Paths(root / "home", root / "raw", root, root / "userdata")
    cfg = Config(llama_server="/fake/llama-server", base_gguf="/fake/base.gguf")
    if boundary == "verdict":
        def stop_after_verdict(path, data):
            write_json(path, data)
            if data.get("served_pending", {}).get("verdict"):
                os._exit(73)
        served.write_json = stop_after_verdict
    else:
        def stop_after_weights(out):
            os.replace(export.prev_path(out), out)
            os._exit(73)
        export.restore_prev = stop_after_weights
    served.finish_pending(paths, load_profile("k2"), cfg, checker=lambda *args, **kwargs: {"ok": False, "reasons": ["worse"]})
    raise AssertionError("fault boundary not reached")


class ServedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.env = Env(llama_cpp_dir="/fake/llama", gguf_base_dir="/fake/hf", gate_min_gain=0)
        self.env.cfg.llama_server = "/fake/llama-server"
        self.env.cfg.base_gguf = "/fake/base.gguf"
        self.gguf = self.env.paths.home / "adapter.gguf"

    def tearDown(self):
        self.env.close()

    def prepare(self, previous=False, legacy=False, hook=None):
        env = self.env
        if previous:
            env.paths.mk()
            self.gguf.write_text("previous")
            if not legacy:
                write_json(export.sidecar_path(self.gguf), {"base_hf_id": env.prof.hf_id, "profile": env.prof.name, "night_id": "older"})

        def exporter(llama, base, adapter, out):
            out = Path(out)
            if out.exists():
                out.replace(export.prev_path(out))
                if export.sidecar_path(out).exists():
                    export.sidecar_path(out).replace(export.sidecar_path(export.prev_path(out)))
            out.write_text("candidate")
            return True, str(out)

        sleeper = env.sleeper(env.backend())
        sleeper.exporter = exporter
        if hook:
            sleeper.checkpoint_hook = hook
        result = sleeper.run(env.week())
        self.assertTrue(result["served"]["pending"])
        self.assertTrue(served.pending_check(env.paths))
        return sleeper, result

    def finish(self, checker):
        return served.finish_pending(self.env.paths, self.env.prof, self.env.cfg, checker=checker)

    def worker(self, checker):
        env = self.env
        worker_env = {"SLEEPMLX_HOME": str(env.paths.home), "SLEEPMLX_DIARY_DIR": str(env.paths.diary_dir),
                      "SLEEPMLX_USERDATA": str(env.paths.userdata_dir), "LEARNER_OPS": str(env.paths.ops),
                      "SLEEPMODE_OUT": str(env.paths.home / "out.json"),
                      "SLEEPMLX_LLAMA_SERVER": env.cfg.llama_server, "SLEEPMLX_BASE_GGUF": env.cfg.base_gguf}
        with patch.object(served, "check_gguf", checker):
            return worker.run_chunk(worker_env, backend_factory=lambda prof: self.fail("must check before loading trainer"),
                                    guards=Guards(env.paths, pressure=lambda: 1, now=env.time.now), profile=env.prof.name)

    def test_worker_recovers_after_night_cleanup_before_loading_backend_or_new_day(self):
        sleeper, result = self.prepare()
        self.assertFalse(self.env.paths.work.exists())
        descriptor = read_json(export.sidecar_path(self.gguf))["served_pending"]
        self.assertTrue(descriptor["held"])
        write_raw(self.env.paths.diary_dir, "2026-10-21", FACTS_DAY2, conv="new-day")
        seen = []
        env = self.env
        checker = lambda *args, **kwargs: seen.append(args) or {"ok": True, "reasons": []}
        recovered = self.worker(checker)
        self.assertEqual(recovered["status"], "served_check")
        self.assertIs(recovered["served"]["ok"], True)
        self.assertEqual(seen[0][3], descriptor["held"])
        self.assertFalse(served.pending_check(env.paths))
        self.assertEqual(read_json(env.paths.state)["nights"], 1)
        self.assertEqual(read_json(export.sidecar_path(self.gguf))["served"], {"ok": True, "reasons": []})

    def test_worker_recovers_even_when_there_is_no_new_diary_day(self):
        self.prepare()
        result = self.worker(lambda *args, **kwargs: {"ok": True, "reasons": []})
        self.assertEqual(result["status"], "served_check")
        self.assertTrue(result["served"]["ok"])

    def hard_exit(self, boundary):
        self.prepare(previous=True)
        paths = self.env.paths
        child_env = dict(os.environ, SLEEPMLX_HOME=str(paths.home), SLEEPMLX_DIARY_DIR=str(paths.diary_dir),
                         SLEEPMLX_USERDATA=str(paths.userdata_dir), LEARNER_OPS=str(paths.ops),
                         SLEEPMODE_OUT=str(paths.home / "out.json"))
        child = subprocess.run([sys.executable, "-c",
                                "from sleepmlx.tests.test_served_recovery import finish_until_exit; import sys; finish_until_exit(*sys.argv[1:])",
                                str(paths.home.parent), boundary], env=child_env, capture_output=True, text=True, timeout=30)
        self.assertEqual(child.returncode, 73, child.stdout + child.stderr)
        result = self.finish(lambda *args, **kwargs: self.fail("durable verdict must not be regraded"))
        self.assertFalse(result["ok"])
        self.assertEqual(self.gguf.read_text(), "previous")
        self.assertEqual(read_json(export.sidecar_path(self.gguf))["night_id"], "older")
        self.assertFalse(served.pending_check(paths))

    def test_hard_exit_after_verdict_publication_replays_without_regrading(self):
        self.hard_exit("verdict")

    def test_hard_exit_during_rollback_preserves_restored_adapter(self):
        self.hard_exit("rollback")

    def test_verdict_save_failure_retains_pending_and_does_not_rollback(self):
        self.prepare(previous=True)
        with patch.object(served, "write_json", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                self.finish(lambda *args, **kwargs: {"ok": False, "reasons": ["worse"]})
        self.assertEqual(self.gguf.read_text(), "candidate")
        self.assertTrue(served.pending_check(self.env.paths))
        self.assertNotIn("verdict", read_json(export.sidecar_path(self.gguf))["served_pending"])
        result = self.finish(lambda *args, **kwargs: {"ok": False, "reasons": ["worse"]})
        self.assertFalse(result["ok"])
        self.assertEqual(self.gguf.read_text(), "previous")
        self.assertFalse(served.pending_check(self.env.paths))

    def test_success_publication_failure_replays_saved_verdict_without_regrading(self):
        self.prepare()
        calls = []
        def fail_second_write(path, data):
            calls.append(data)
            if len(calls) == 2:
                raise OSError("interrupted final publication")
            write_json(path, data)
        with patch.object(served, "write_json", fail_second_write):
            with self.assertRaisesRegex(OSError, "interrupted"):
                self.finish(lambda *args, **kwargs: {"ok": True, "reasons": []})
        side = read_json(export.sidecar_path(self.gguf))
        self.assertTrue(side["served"]["pending"])
        self.assertTrue(side["served_pending"]["verdict"]["ok"])
        result = self.finish(lambda *args, **kwargs: self.fail("saved verdict must be replayed"))
        self.assertTrue(result["ok"])
        self.assertFalse(served.pending_check(self.env.paths))

    def test_rejected_rollback_recovers_between_weight_and_metadata_replacement(self):
        self.prepare(previous=True)
        def interrupted_rollback(out):
            os.replace(export.prev_path(out), out)
            raise OSError("interrupted metadata rollback")
        with patch.object(export, "restore_prev", interrupted_rollback):
            with self.assertRaisesRegex(OSError, "interrupted"):
                self.finish(lambda *args, **kwargs: {"ok": False, "reasons": ["worse"]})
        self.assertEqual(self.gguf.read_text(), "previous")
        self.assertTrue(served.pending_check(self.env.paths))
        result = self.finish(lambda *args, **kwargs: self.fail("saved verdict must be replayed"))
        self.assertFalse(result["ok"])
        self.assertEqual(self.gguf.read_text(), "previous")
        self.assertEqual(read_json(export.sidecar_path(self.gguf))["night_id"], "older")
        self.assertFalse(served.pending_check(self.env.paths))

    def test_rejected_legacy_rollback_removes_candidate_sidecar(self):
        self.prepare(previous=True, legacy=True)
        result = self.finish(lambda *args, **kwargs: {"ok": False, "reasons": ["worse"]})
        self.assertFalse(result["ok"])
        self.assertEqual(self.gguf.read_text(), "previous")
        self.assertFalse(export.sidecar_path(self.gguf).exists())

    def test_changed_candidate_is_never_graded_or_rolled_back(self):
        self.prepare(previous=True)
        self.gguf.write_text("newer")
        result = self.finish(lambda *args, **kwargs: self.fail("stale descriptor must not be graded"))
        self.assertTrue(result["pending"])
        self.assertEqual(self.gguf.read_text(), "newer")
        self.assertEqual(export.prev_path(self.gguf).read_text(), "previous")

    def test_candidate_changed_during_check_is_never_rolled_back(self):
        self.prepare(previous=True)
        def checker(*args, **kwargs):
            self.gguf.write_text("newer")
            return {"ok": False, "reasons": ["worse"]}
        result = self.finish(checker)
        self.assertTrue(result["pending"])
        self.assertEqual(self.gguf.read_text(), "newer")
        self.assertEqual(export.prev_path(self.gguf).read_text(), "previous")
        self.assertNotIn("verdict", read_json(export.sidecar_path(self.gguf))["served_pending"])

    def test_changed_active_generation_blocks_same_bytes_from_stale_check(self):
        self.prepare(previous=True)
        manifest = read_json(self.env.paths.home / "adapters.json")
        manifest["current"] = manifest["previous"] = "adapter"
        self.env.backend().save_adapter(self.env.paths.home / "adapter")
        write_json(self.env.paths.home / "adapters.json", manifest)
        result = self.finish(lambda *args, **kwargs: self.fail("new generation must not use old check"))
        self.assertTrue(result["pending"])
        self.assertEqual(self.gguf.read_text(), "candidate")

    def test_inconclusive_check_keeps_descriptor_for_retry(self):
        self.prepare()
        result = self.finish(lambda *args, **kwargs: {"ok": None, "reasons": ["out of memory"]})
        self.assertTrue(result["pending"])
        self.assertTrue(served.pending_check(self.env.paths))
        self.assertTrue(self.finish(lambda *args, **kwargs: {"ok": True, "reasons": []})["ok"])

    def test_preflight_rejection_updates_unfinished_finalization_result(self):
        def stop_after_state(stage):
            if stage == "state_written":
                raise RuntimeError("interrupted finalization")
        with self.assertRaisesRegex(RuntimeError, "interrupted finalization"):
            self.prepare(previous=True, hook=stop_after_state)
        self.assertTrue(self.env.paths.night_json.exists())
        self.finish(lambda *args, **kwargs: {"ok": False, "reasons": ["worse"]})
        recorded = read_json(self.env.paths.night_json)["finalization"]["result"]["served"]
        self.assertFalse(recorded["ok"])
        self.assertNotIn("pending", recorded)
        resumed = self.env.sleeper(self.env.backend()).run(self.env.week())
        self.assertEqual(resumed["status"], "done")
        self.assertFalse(resumed["served"]["ok"])
        self.assertNotIn("pending", resumed["served"])
        self.assertEqual(self.gguf.read_text(), "previous")
        self.assertEqual(read_json(self.env.paths.state)["nights"], 1)

    def test_finalization_result_save_failure_preserves_verdict_and_candidate(self):
        self.prepare(previous=True)
        with patch.object(served, "_record_finalization", side_effect=OSError("journal unavailable")):
            with self.assertRaisesRegex(OSError, "journal unavailable"):
                self.finish(lambda *args, **kwargs: {"ok": False, "reasons": ["worse"]})
        self.assertEqual(self.gguf.read_text(), "candidate")
        self.assertFalse(read_json(export.sidecar_path(self.gguf))["served_pending"]["verdict"]["ok"])
        result = self.finish(lambda *args, **kwargs: self.fail("saved verdict must be replayed"))
        self.assertFalse(result["ok"])
        self.assertEqual(self.gguf.read_text(), "previous")
