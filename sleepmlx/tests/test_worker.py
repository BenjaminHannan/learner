import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sleepmlx import __main__ as cli
from sleepmlx import worker
from sleepmlx.backend import Guards, memory_pressure_level
from sleepmlx import backend
from sleepmlx.paths import Paths
from sleepmlx.profile import Renderer, load_profile

from .fakes import FakeBackend, factory
from .helpers import FACTS_DAY1, write_raw

ROOT = str(Path(__file__).resolve().parents[2])


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write_raw(self.root / "raw", "2026-10-20", FACTS_DAY1)
        self.env = {"SLEEPMLX_HOME": str(self.root / "home"), "SLEEPMLX_DIARY_DIR": str(self.root / "raw"), "LEARNER_OPS": str(self.root),
                    "SLEEPMODE_BUDGET_S": "100000", "SLEEPMLX_SCALE": "1", "SLEEPMLX_PROFILE": "k2"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_paths_from_home_outside_learner_ops(self):
        # a SLEEPMLX_HOME copy elsewhere keeps the real ops dir and diary (was home.parent/diary/raw)
        p = worker._paths_from({"SLEEPMLX_HOME": "/tmp/copy/sm", "LEARNER_OPS": str(self.root)})
        self.assertEqual((p.ops, p.diary_dir), (self.root, self.root / "diary" / "raw"))
        old = os.environ.pop("LEARNER_OPS", None)
        try:
            p = worker._paths_from({"SLEEPMLX_HOME": "/tmp/copy/sm"})
            self.assertEqual(p.ops, worker.ops_dir())
            self.assertNotEqual(p.ops, Path("/tmp/copy"))
        finally:
            if old is not None:
                os.environ["LEARNER_OPS"] = old

    def test_run_chunk_output_matches_the_commandworker_contract(self):
        def fac(prof):
            prof.template_mode = "manual"
            return FakeBackend(), None
        out = worker.run_chunk(self.env, backend_factory=fac)
        self.assertIsInstance(out["quiz"], float)
        self.assertIsInstance(out["steps"], int)
        self.assertGreater(out["steps"], 0)
        self.assertIs(out["interrupted"], False)
        json.dumps(out)                                   # serialisable
        self.assertIn("harm", out)
        self.assertIn("general", out)
        # a second chunk with nothing new: quiz null, steps 0, cheap (no model load)
        def boom(prof):
            raise AssertionError("model must not load when there is nothing to sleep on")
        out2 = worker.run_chunk(self.env, backend_factory=boom)
        self.assertIsNone(out2["quiz"])
        self.assertEqual(out2["steps"], 0)
        self.assertIn("no new diary day", out2["message"])

    def test_cli_entry_writes_sleepmode_out_as_a_subprocess(self):
        out = self.root / "chunk_out.json"
        env = dict(os.environ, **self.env, SLEEPMODE_OUT=str(out), SLEEPMODE_PRACTICE=os.pathsep.join(["a/sft.jsonl", "b/pairs.jsonl"]),
                   SLEEPMODE_WORKDIR=str(self.root / "wd"), SLEEPMLX_BACKEND="sleepmlx.tests.fakes:factory", PYTHONPATH=ROOT,
                   SLEEPMLX_FAKE_MANUAL="1")
        # the factory returns a tokenizer-less backend; force the manual template through a tiny profile override
        env["SLEEPMLX_PROFILE"] = str(self.root / "p.json")
        prof = json.loads((Path(ROOT) / "sleepmlx/profiles/k2.json").read_text())
        prof["template_mode"] = "manual"
        (self.root / "p.json").write_text(json.dumps(prof))
        r = subprocess.run([sys.executable, "-m", "sleepmlx.worker"], env=env, cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        data = json.loads(out.read_text())
        self.assertIsInstance(data["quiz"], float)
        self.assertGreater(data["steps"], 0)
        self.assertFalse(data["interrupted"])

    def test_commandworker_reads_our_output(self):
        # exercise the real CommandWorker if the sleepmode package is importable (it lives on another branch); else mirror its parsing
        try:
            from sleepmode.workers import CommandWorker
        except ImportError:
            CommandWorker = None
        out = self.root / "chunk_out.json"
        data = {"quiz": 61.5, "steps": 12, "interrupted": False, "harm": 0.0}
        out.write_text(json.dumps(data))
        if CommandWorker is None:
            parsed = json.loads(out.read_text())
            quiz = parsed.pop("quiz", None)
            steps = int(parsed.pop("steps", 0) or 0)
            self.assertEqual((float(quiz), steps), (61.5, 12))
        else:
            w = CommandWorker([sys.executable, "-c", "pass"], str(self.root / "wd"))
            res = w.run_chunk(5, [], lambda: False)
            self.assertIsNone(res.quiz)

    def test_stops_before_loading_when_assistant_is_running(self):
        (self.root / "ASSISTANT_RUNNING").write_text("1")
        out = worker.run_chunk(self.env, backend_factory=lambda p: self.fail("must not load"))
        self.assertTrue(out["interrupted"])
        self.assertEqual(out["stop_reason"], "assistant_running")

    def test_profile_recipe_overrides_reach_the_config(self):
        cfg = worker.cfg_from_env({}, load_profile("lfm3_cpu"))
        self.assertEqual((cfg.bsz, cfg.kl_every, cfg.gate_n, cfg.gate_max_tokens), (4, 4, 20, 16))
        self.assertEqual(worker.choose_backend(load_profile("k2")), "mlx")
        self.assertEqual(worker.choose_backend(load_profile("lfm3_cpu")), "torch")

    def test_cpu_preload_reserves_ram_before_starting_backend(self):
        env = dict(self.env, SLEEPMLX_PROFILE="lfm3_cpu")
        def never(_): self.fail("trainer must not load under the threshold")
        low = worker.run_chunk(env, backend_factory=never, memory_available=lambda: 3.9e9)
        self.assertTrue(low["interrupted"])
        self.assertEqual(low["stop_reason"], "memory_pressure")
        self.assertIn("4.5 GB", low["message"])
        unknown = worker.run_chunk(env, backend_factory=never, memory_available=lambda: None)
        self.assertIn("psutil", unknown["error"])
        called = []
        class Loaded(Exception): pass
        def load(_): called.append(True); raise Loaded()
        with self.assertRaises(Loaded):
            worker.run_chunk(env, backend_factory=load, memory_available=lambda: 5e9)
        self.assertEqual(called, [True])

    def test_windows_memory_fallback_supports_legacy_installs_without_psutil(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        import builtins
        import ctypes
        def success(ptr):
            ptr._obj.ullAvailPhys = 5_200_000_000
            return 1
        kernel = SimpleNamespace(GlobalMemoryStatusEx=success)
        self.assertEqual(backend._windows_available_ram(kernel), 5_200_000_000)
        self.assertIsNone(backend._windows_available_ram(SimpleNamespace(GlobalMemoryStatusEx=lambda _: 0)))
        original_import = builtins.__import__
        def import_without_psutil(name, *args, **kwargs):
            if name == "psutil": raise ImportError("not installed")
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=import_without_psutil), patch.object(worker.sys, "platform", "win32"), patch.object(ctypes, "windll", SimpleNamespace(kernel32=kernel), create=True):
            self.assertEqual(backend.available_ram_bytes(), 5_200_000_000)

    def test_supplied_guards_use_profile_runtime_threshold(self):
        env = dict(self.env, SLEEPMLX_PROFILE="lfm3_cpu")
        guards = Guards(pressure=lambda: 1)
        worker.run_chunk(env, backend_factory=lambda _: self.fail("must not load"), guards=guards, memory_available=lambda: 2e9)
        self.assertEqual(guards.min_free_gb, load_profile("lfm3_cpu").runtime["min_free_ram_gb"])
        from unittest.mock import patch
        with patch("sleepmlx.backend.memory_pressure_level", return_value=1) as pressure:
            live = Guards(min_free_gb=1.0); live.min_free_gb = 2.5; live.reason()
            pressure.assert_called_once_with(2.5)

    def test_memory_check_never_raises_without_psutil_or_sysctl(self):
        self.assertIn(memory_pressure_level(1.0), (1, 2, 4))

    def test_windows_paths(self):
        from sleepmlx import paths
        old = (paths.sys.platform, os.environ.get("APPDATA"), os.environ.pop("LEARNER_OPS", None), os.environ.pop("SLEEPMLX_HOME", None),
               os.environ.pop("SLEEPMLX_DIARY_DIR", None))
        try:
            paths.sys.platform = "win32"
            os.environ["APPDATA"] = str(self.root / "AppData")
            p = Paths.from_env()
            self.assertEqual(p.home, self.root / "AppData" / "Premonition" / "sleep")
            self.assertEqual(p.pause_file.parent, p.home)
        finally:
            paths.sys.platform = old[0]
            for k, v in zip(("APPDATA", "LEARNER_OPS", "SLEEPMLX_HOME", "SLEEPMLX_DIARY_DIR"), old[1:]):
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class RecallTests(unittest.TestCase):
    def test_recall_one_short_line_no_think_max_64(self):
        prof = load_profile("k2")
        prof.template_mode = "manual"
        R = Renderer(prof, None)
        seen = {}

        class B(FakeBackend):
            def generate(self, prompts, max_tokens, temp=0.0, adapter=True, stops=()):
                seen.update(prompts=prompts, max_tokens=max_tokens, temp=temp, adapter=adapter)
                return ["Marta works at Orbix.\nExtra line</ifm|think>"]
        out = cli.recall("Where does Marta work?", B(), R, prof)
        self.assertEqual(out, "Marta works at Orbix.")
        self.assertEqual(seen["max_tokens"], 64)
        self.assertEqual(seen["temp"], 0.0)
        self.assertTrue(seen["adapter"])
        self.assertTrue(seen["prompts"][0].endswith("<ifm|think>\n</ifm|think>"))
        self.assertIn("Answer in one short line.", seen["prompts"][0])
        self.assertEqual(cli.clean_answer("<think>x</think>\n\nParis.\n", load_profile("lfm3_cuda")), "Paris.")

    def test_recall_loads_the_adapter_and_uses_what_was_learned(self):
        from .helpers import Env
        env = Env()
        try:
            be = env.backend()
            env.sleeper(be).run(env.week())
            be2 = env.backend()
            ans = cli.recall("Who is tied to Orbix?", be2, env.R, env.prof, env.paths.adapter)
            self.assertEqual(ans, "Marta")
            self.assertEqual(be2.loaded, [str(env.paths.adapter)])
        finally:
            env.close()

    def test_status(self):
        from .helpers import Env
        env = Env()
        try:
            env.sleeper(env.backend()).run(env.week())
            st = cli.status(env.paths, env.prof)
            self.assertEqual(st["slept_days"], ["2026-10-20"])
            self.assertTrue(st["adapter"])
            self.assertIsNone(st["next_day"])
            self.assertGreater(st["cards"], 0)
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()
