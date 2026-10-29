from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from sleepmlx import day_adapter
from sleepmlx.export import sidecar_path
from sleepmlx.profile import load_profile
from .helpers import Env
from .protocol_fixtures import served_decision
from types import SimpleNamespace


class DayAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.profile = load_profile("lfm3_mps", {})
        self.base = self.home / "hf-base"
        self.gguf = self.home / "base.gguf"

    def export(self, filename="adapter.gguf", **changes):
        path = self.home / filename
        content = b"GGUF-synthetic-adapter-only"
        path.write_bytes(content)
        record = {"profile": "lfm3_mps", "base_hf_id": "LiquidAI/LFM3-1.7B", "base_dir": str(self.base),
                  "base_gguf": str(self.gguf), "night_id": "synthetic-night", "served": {"ok": True},
                  "artifact": {"version": 1, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}}
        record.update(changes)
        sidecar_path(path).write_text(json.dumps(record))
        return path

    def select(self):
        return day_adapter.select_adapter(self.home, self.profile, base_dir=self.base, base_gguf=self.gguf)

    def test_current_accepted_artifact_is_selected(self):
        path = self.export()
        result = self.select()
        self.assertEqual(result["adapter"], str(path))
        self.assertFalse(result["fallback"])

    def test_pending_failed_and_inconclusive_checks_cannot_be_selected(self):
        for changes in ({"served_pending": {}}, {"served_pending": None}, {"served": {"ok": True, "pending": True}},
                        {"served": {"ok": False}}, {"served": {"ok": None}}, {"served": {"ok": 1}}):
            with self.subTest(changes=changes):
                self.export(**changes)
                self.assertIsNone(self.select()["adapter"])

    def test_wrong_model_profile_or_base_cannot_be_selected(self):
        for changes in ({"profile": "apex35b_mlx"}, {"base_hf_id": "Apexintelligence-AI/Apex-35B-V1.0"},
                        {"base_dir": str(self.home / "wrong-base")}, {"base_gguf": str(self.home / "wrong.gguf")},
                        {"night_id": ""}):
            with self.subTest(changes=changes):
                self.export(**changes)
                self.assertIsNone(self.select()["adapter"])

    def test_valid_previous_is_fallback_when_current_is_pending(self):
        self.export(served={"ok": None, "pending": True})
        previous = self.export("adapter.prev.gguf")
        result = self.select()
        self.assertEqual(result["adapter"], str(previous))
        self.assertTrue(result["fallback"])

    def test_modified_same_size_and_truncated_artifacts_are_rejected(self):
        path = self.export()
        original = path.read_bytes()
        path.write_bytes(b"X" * len(original))
        self.assertIn("hash differs", self.select()["rejected"][0]["reason"])
        path.write_bytes(original[:-1])
        self.assertIn("size differs", self.select()["rejected"][0]["reason"])

    def test_missing_legacy_or_malformed_metadata_uses_plain_base(self):
        path = self.export()
        for raw in (None, "{", "[]", json.dumps({"base_hf_id": "LiquidAI/LFM3-1.7B"})):
            with self.subTest(raw=raw):
                if raw is None:
                    sidecar_path(path).unlink(missing_ok=True)
                else:
                    sidecar_path(path).write_text(raw)
                self.assertIsNone(self.select()["adapter"])
        self.export(artifact=None)
        self.assertIsNone(self.select()["adapter"])

    def test_canonical_hf_symlink_is_accepted(self):
        self.base.mkdir()
        alias = self.home / "alias"
        alias.symlink_to(self.base, target_is_directory=True)
        self.export(base_dir=str(alias))
        self.assertIsNotNone(self.select()["adapter"])

    def test_cli_plain_base_is_successful_with_empty_stdout(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = day_adapter.main(["--home", str(self.home)])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "")

    def test_real_sidecar_writer_retains_bound_artifact_after_pending_check(self):
        env = Env(llama_server="/synthetic/llama-server", base_gguf=str(self.gguf), gguf_base_dir=str(self.base))
        self.addCleanup(env.close)
        env.prof.name, env.prof.hf_id = self.profile.name, self.profile.hf_id
        env.paths.mk()
        adapter = env.paths.home / "adapter.gguf"
        adapter.write_bytes(b"GGUF-synthetic-completed-export")
        sleeper = env.sleeper(env.backend())
        sleeper.N = {"id": "synthetic-night", "day": 1, "date": "2026-10-29"}
        sleeper.state, sleeper.items = {}, {"synthetic": SimpleNamespace(held=[{"night": 1, "q": "Synthetic?", "a": "Synthetic"}])}
        sleeper.served_checker = lambda *args, **kwargs: served_decision(True, args[3], [])
        result = {}
        sleeper._after_export(adapter, result)
        selected = lambda: day_adapter.select_adapter(env.paths.home, self.profile, base_dir=self.base, base_gguf=self.gguf)
        self.assertIsNone(selected()["adapter"])
        sleeper.finish_served(result)
        self.assertEqual(selected()["adapter"], str(adapter.resolve()))
        record = json.loads(sidecar_path(adapter).read_text())
        self.assertNotIn("served_pending", record)
        self.assertEqual(record["artifact"]["sha256"], hashlib.sha256(adapter.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
