import http.server
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from sleepmlx import __main__ as cli
from sleepmlx import export, profile, torch_backend, worker

from .helpers import Env, FACTS_DAY2, write_raw


def fake_torch(cuda=False, bf16=True, mps=False):
    t = SimpleNamespace()
    t.bfloat16, t.float16, t.float32 = "bf16", "fp16", "fp32"
    t.cuda = SimpleNamespace(is_available=lambda: cuda, is_bf16_supported=lambda: bf16)
    t.backends = SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps))
    return t


class DeviceTests(unittest.TestCase):
    def test_device_order_cuda_then_mps_then_cpu(self):
        self.assertEqual(torch_backend.pick_device_dtype(fake_torch(cuda=True, mps=True)), ("cuda", "bf16"))
        self.assertEqual(torch_backend.pick_device_dtype(fake_torch(cuda=True, bf16=False)), ("cuda", "fp16"))
        self.assertEqual(torch_backend.pick_device_dtype(fake_torch(mps=True)), ("mps", "fp16"))     # fp16 base on MPS, not bf16
        self.assertEqual(torch_backend.pick_device_dtype(fake_torch()), ("cpu", "bf16"))

    def test_mps_memory_cap_fraction(self):
        calls = []
        t = fake_torch(mps=True)
        t.mps = SimpleNamespace(recommended_max_memory=lambda: 24e9, set_per_process_memory_fraction=lambda f: calls.append(f))
        frac = torch_backend.set_mps_cap(t, 10)
        self.assertAlmostEqual(frac, 10 / 24)
        self.assertEqual(calls, [frac])
        t.mps.recommended_max_memory = lambda: 4e9           # never above 1.0
        self.assertEqual(torch_backend.set_mps_cap(t, 10), 1.0)

    def test_mps_cap_scales_with_ram(self):
        cap = torch_backend.mps_cap_gb
        self.assertEqual(cap(10, {}, ram=8e9), 10)                       # 8 GB Mac: the profile's 10 GB floor, as before
        self.assertAlmostEqual(cap(10, {}, ram=32e9), 0.45 * 32)          # 32 GB M1 Pro: 14.4 GB
        self.assertEqual(cap(10, {"SLEEPMLX_MPS_MEM_GB": "6"}, ram=32e9), 6.0)   # env wins, even below the floor
        self.assertIsNone(cap(None, {}, ram=32e9))                       # no cap in the profile: none

    def test_mps_fallback_env_is_set(self):
        self.assertEqual(os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK"), "1")


class ProfileChoiceTests(unittest.TestCase):
    def test_default_alias_per_platform(self):
        r = profile.resolve_profile_name
        self.assertEqual(r("lfm3", "darwin", False), "lfm3_mps")
        self.assertEqual(r("lfm3", "darwin", True), "lfm3_mps")
        self.assertEqual(r("lfm3", "win32", False), "lfm3_cpu")
        self.assertEqual(r("lfm3", "win32", True), "lfm3_cuda")
        self.assertEqual(r("lfm3", "linux", False), "lfm3_cpu")
        self.assertEqual(r("lfm3", "linux", True), "lfm3_cuda")
        self.assertEqual(r("k2", "darwin", False), "k2")           # K2 stays available by name
        self.assertEqual(profile.DEFAULT_PROFILE, "lfm3")

    def test_default_profile_loads_and_k2_still_loads(self):
        p = profile.load_profile(None, {})
        self.assertIn(p.name, ("lfm3_mps", "lfm3_cuda", "lfm3_cpu"))
        self.assertEqual(profile.load_profile("k2").backend, "mlx")

    def test_lfm3_mps_profile(self):
        p = profile.load_profile("lfm3_mps")
        self.assertEqual(p.backend, "torch")
        self.assertEqual(p.lora["rank"], 16)
        self.assertEqual(p.runtime["tok_budget"], 512)
        self.assertTrue(p.runtime["grad_ckpt"])
        self.assertEqual(p.runtime["mps_mem_gb"], 10)
        self.assertEqual(p.model_dir, "~/learner-ops/models/lfm3-1.7b-hf")
        self.assertEqual(p.hf_id, "LiquidAI/LFM3-1.7B")
        import re
        rx = re.compile(p.lora["target_modules"])
        for name, hit in (("model.layers.3.self_attn.q_proj", True), ("model.layers.3.self_attn.o_proj", True), ("model.layers.3.conv.out_proj", True),
                          ("model.layers.3.conv.in_proj", False), ("model.layers.3.feed_forward.w1", False)):
            self.assertEqual(bool(rx.fullmatch(name)), hit, name)
        self.assertEqual(p.stop_token, "<|im_end|>")
        self.assertEqual(profile.load_profile("lfm3_cpu").lora["rank"], 8)

    def test_missing_hf_dir_prints_the_exact_download_command(self):
        p = profile.load_profile("lfm3_mps", {"SLEEPMLX_MODEL_DIR": "/nonexistent/lfm3-1.7b-hf"})
        with self.assertRaises(worker.ModelMissing) as cm:
            worker.torch_source(p)
        self.assertIn("huggingface-cli download LiquidAI/LFM3-1.7B --local-dir /nonexistent/lfm3-1.7b-hf", str(cm.exception))
        with tempfile.TemporaryDirectory() as d:
            p.model_dir = d
            self.assertEqual(worker.torch_source(p), d)
        self.assertEqual(worker.torch_source(profile.load_profile("lfm3_cpu")), "LiquidAI/LFM3-1.7B")   # no dir configured: the hub id


class Handler(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Handler.seen.append((self.path, body))
        out = json.dumps({"content": "Marta works at Orbix.\nmore"}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


class RecallServerTests(unittest.TestCase):
    def test_server_recall_uses_the_no_think_prompt(self):
        srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            prof = profile.load_profile("lfm3_cuda")
            out = cli.recall_server("http://127.0.0.1:%d" % srv.server_port, "Where does Marta work?", prof)
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertEqual(out, "Marta works at Orbix.")
        path, body = Handler.seen[-1]
        self.assertEqual(path, "/completion")
        self.assertEqual(body["n_predict"], 64)
        self.assertEqual(body["temperature"], 0.0)
        self.assertTrue(body["prompt"].endswith("<|im_start|>assistant\n<think></think>"), body["prompt"])
        self.assertIn("Answer in one short line.", body["prompt"])
        self.assertEqual(body["stop"], ["<|im_end|>"])

    def test_unreachable_server_raises_so_the_caller_can_fall_back(self):
        with self.assertRaises(OSError):
            cli.recall_server("http://127.0.0.1:9", "q", profile.load_profile("lfm3_cuda"), timeout=2)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "llama").mkdir()
        (self.root / "llama" / "convert_lora_to_gguf.py").write_text("")
        (self.root / "base").mkdir()
        (self.root / "ad").mkdir()
        (self.root / "ad" / "adapter_model.safetensors").write_text("x")

    def tearDown(self):
        self.tmp.cleanup()

    def test_export_command_and_skips(self):
        calls = []

        def run(cmd, **kw):
            calls.append(cmd)
            Path(cmd[-1]).write_text("gguf")
            return SimpleNamespace(returncode=0, stderr="")
        ok, msg = export.export_gguf(str(self.root / "llama"), str(self.root / "base"), self.root / "ad", self.root / "out.gguf", run=run)
        self.assertTrue(ok, msg)
        self.assertTrue((self.root / "out.gguf").exists())
        self.assertEqual(calls[0][1:3], [str(self.root / "llama" / "convert_lora_to_gguf.py"), str(self.root / "ad")])
        self.assertIn("--base", calls[0])
        self.assertFalse(export.export_gguf(None, str(self.root / "base"), self.root / "ad", self.root / "o")[0])
        self.assertFalse(export.export_gguf(str(self.root / "llama"), str(self.root / "nobase"), self.root / "ad", self.root / "o")[0])
        self.assertFalse(export.export_gguf(str(self.root / "llama"), str(self.root / "base"), self.root / "none", self.root / "o")[0])
        bad = export.export_gguf(str(self.root / "llama"), str(self.root / "base"), self.root / "ad", self.root / "o2",
                                 run=lambda cmd, **kw: SimpleNamespace(returncode=2, stderr="boom"))
        self.assertFalse(bad[0])
        self.assertIn("boom", bad[1])


class NightExportTests(unittest.TestCase):
    def test_export_runs_on_commit_and_a_failure_does_not_fail_the_night(self):
        env = Env(llama_cpp_dir="/some/llama.cpp", gguf_base_dir="/some/hf")
        try:
            seen = []
            sl = env.sleeper(env.backend())
            sl.exporter = lambda llama, base, adapter, out: (seen.append((llama, base, str(adapter), str(out))) or (True, "ok.gguf"))
            r = sl.run(env.week())
            self.assertEqual(r["status"], "done")
            self.assertEqual(r["gguf"], {"ok": True, "message": "ok.gguf"})
            self.assertEqual(seen[0][:2], ("/some/llama.cpp", "/some/hf"))
            self.assertEqual(seen[0][2], str(env.paths.adapter))      # the committed adapter, after the move
            write_raw(env.paths.diary_dir, "2026-10-21", FACTS_DAY2, conv="c2")
            env.cfg.gate_min_gain = 0   # about the export, not the gain rule
            sl2 = env.sleeper(env.backend())

            def boom(*a):
                raise RuntimeError("converter exploded")
            sl2.exporter = boom
            r2 = sl2.run(env.week())
            self.assertEqual(r2["status"], "done")
            self.assertFalse(r2["reverted"])
            self.assertFalse(r2["gguf"]["ok"])
            self.assertIn("exploded", r2["gguf"]["message"])
            self.assertTrue(env.paths.adapter.exists())
        finally:
            env.close()

    def test_no_export_when_not_configured_or_reverted(self):
        env = Env()
        try:
            r = env.sleeper(env.backend()).run(env.week())
            self.assertNotIn("gguf", r)
        finally:
            env.close()
        env = Env(llama_cpp_dir="/x", gguf_base_dir="/y")
        try:
            sl = env.sleeper(env.backend(damage=True))
            sl.exporter = lambda *a: self.fail("export must not run on a reverted night")
            self.assertTrue(sl.run(env.week())["reverted"])
        finally:
            env.close()

    def test_worker_config_reads_llama_cpp_dir(self):
        p = profile.load_profile("lfm3_mps")
        cfg = worker.cfg_from_env({"SLEEPMLX_LLAMA_CPP_DIR": "~/llama.cpp"}, p)
        self.assertEqual(cfg.llama_cpp_dir, "~/llama.cpp")
        self.assertEqual(cfg.gguf_base_dir, p.expanded_model_dir)
        self.assertIsNone(worker.cfg_from_env({}, p).llama_cpp_dir)


if __name__ == "__main__":
    unittest.main()
