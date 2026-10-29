"""Local real-weight LFM3 smoke; never reads diary data or changes live adapters.

Run: python -m sleepmlx.tests.manual_lfm3_smoke --model-dir /cached/LFM3
Requires the optional torch/transformers/peft dependencies and cached HF weights.
Two very small synthetic updates check plumbing, not learning quality.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def served_completion(server, base_gguf, adapter, prompt, root):
    """One owned temporary server, with cleanup even on readiness/request failure."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    command = [str(server), "-m", str(base_gguf), "--host", "127.0.0.1", "--port", str(port),
               "--ctx-size", "256", "--parallel", "1", "--batch-size", "32", "--ubatch-size", "32",
               "--n-gpu-layers", "99", "--threads", "2"]
    if adapter is not None:
        command.extend(["--lora", str(adapter)])
    with (root / ("adapted.log" if adapter else "base.log")).open("w+") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        try:
            endpoint = "http://127.0.0.1:%d" % port
            deadline = time.monotonic() + 60
            while True:
                if process.poll() is not None:
                    log.seek(0)
                    raise RuntimeError("owned llama-server exited: " + log.read()[-5000:])
                try:
                    with urllib.request.urlopen(endpoint + "/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except (urllib.error.URLError, TimeoutError):
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError("owned llama-server did not become ready")
                time.sleep(0.2)
            request = urllib.request.Request(endpoint + "/completion", data=json.dumps({
                "prompt": prompt, "n_predict": 2, "temperature": 0, "seed": 1,
                "stream": False, "cache_prompt": False,
            }).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.load(response)
            assert isinstance(result.get("content"), str), result
            assert result.get("tokens_predicted", 0) > 0, result
            return {"content": result["content"], "tokens_predicted": result["tokens_predicted"]}
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--mps-mem-gb", type=float, default=8.0)
    parser.add_argument("--llama-cpp-dir", type=Path, help="optional: export with this local checkout and serve")
    parser.add_argument("--base-gguf", type=Path, help="cached LFM3 GGUF required for optional serving smoke")
    args = parser.parse_args()
    if bool(args.llama_cpp_dir) != bool(args.base_gguf):
        parser.error("--llama-cpp-dir and --base-gguf must be supplied together")
    model_dir = args.model_dir.expanduser().resolve(strict=True)
    if not (model_dir / "model.safetensors").is_file():
        parser.error("a local directory containing model.safetensors is required")
    with tempfile.TemporaryDirectory(prefix="premonition-lfm3-smoke-") as tmp:
        root = Path(tmp)
        for key, leaf in {
            "SLEEPMLX_HOME": "sleepmlx", "SLEEPMLX_DIARY_DIR": "diary",
            "SLEEPMLX_USERDATA": "userdata", "LEARNER_OPS": "ops",
            "SLEEPMODE_HOME": "sleepmode", "SLEEPMODE_OPS": "mode-ops",
            "SLEEPMODE_OUT": "mode-out", "HF_HOME": "hf",
            "HF_MODULES_CACHE": "hf-modules",
        }.items():
            os.environ[key] = str(root / leaf)
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["SLEEPMLX_MPS_MEM_GB"] = str(args.mps_mem_gb)
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        import torch
        import transformers
        import peft
        from sleepmlx.backend import Clock, Guards, Stop
        from sleepmlx.profile import Renderer, load_profile
        from sleepmlx.torch_backend import TorchBackend, load

        started = time.monotonic()
        with (model_dir / "model.safetensors").open("rb") as weights:
            digest = hashlib.file_digest(weights, "sha256").hexdigest()
        print(json.dumps({"stage": "start", "source": str(model_dir), "weights_sha256": digest,
                          "torch": torch.__version__, "transformers": transformers.__version__,
                          "peft": peft.__version__, "mps_available": torch.backends.mps.is_available()}), flush=True)
        profile = load_profile("lfm3_mps")
        torch.manual_seed(1)
        model, tokenizer = load(str(model_dir), trust_remote_code=True, mps_gb=args.mps_mem_gb)
        backend = TorchBackend(model, tokenizer, profile, str(model_dir), tok_budget=64, grad_ckpt=True, gen_batch=1)
        assert "Lfm3" in type(backend.lm).__name__, type(backend.lm).__name__

        def report(stage, **values):
            if backend.device == "mps":
                torch.mps.synchronize()
                values["mps_allocated_gb"] = torch.mps.current_allocated_memory() / 1e9
                values["mps_driver_gb"] = torch.mps.driver_allocated_memory() / 1e9
            print(json.dumps({"stage": stage, "elapsed_s": round(time.monotonic() - started, 3), **values}), flush=True)

        report("loaded", device=backend.device, dtype=str(backend.dtype), model_class=type(backend.lm).__name__,
               trainable_parameters=sum(p.numel() for p in backend.params))
        prompt = Renderer(profile, tokenizer).render("", "Say hello.")
        before_text = backend.generate([prompt], 2)
        assert len(before_text) == 1 and isinstance(before_text[0], str)
        report("generated_before", text=before_text)
        ids = backend.encode("Synthetic test only. A blue cup is on the table.")[:16]
        assert len(ids) >= 4
        batch, replay = [(ids, len(ids) - 2)], [(ids[:8], 6)]
        backend.train_begin(3, 2e-4)
        before = [p.detach().cpu().clone() for p in backend.params]
        for step in range(2):
            metrics = backend.train_step(batch, replay, step)
            assert all(math.isfinite(v) for v in metrics.values()), metrics
            assert all(torch.isfinite(p).all().item() for p in backend.params), "nonfinite parameter"
            assert all(p.grad is None or torch.isfinite(p.grad).all().item() for p in backend.params), "nonfinite gradient"
            report("train_step", step=step, metrics=metrics, sequence_length=len(ids), supervised_tokens=2)
        assert any(not torch.equal(old, new.detach().cpu()) for old, new in zip(before, backend.params)), "adapter did not change"
        adapter = root / "adapter"
        backend.save_adapter(adapter)
        saved = [p.detach().cpu().clone() for p in backend.params]
        backend.load_adapter(None)
        backend.load_adapter(adapter)
        assert all(torch.equal(old, new.detach().cpu()) for old, new in zip(saved, backend.params)), "reload mismatch"
        report("save_reload", files=sorted(p.name for p in adapter.iterdir()))
        after_text = backend.generate([prompt], 2)
        assert len(after_text) == 1 and isinstance(after_text[0], str)
        report("generated_after", text=after_text)
        guards = Guards(pressure=lambda: 1)
        clock = Clock(60, guards, reserve_s=0)
        previous = signal.getsignal(signal.SIGTERM)
        try:
            signal.signal(signal.SIGTERM, lambda signum, frame: guards.signal("sigterm"))
            os.kill(os.getpid(), signal.SIGTERM)
            try:
                clock.check()
                raise AssertionError("SIGTERM was not observed")
            except Stop as exc:
                assert exc.reason == "sigterm" and exc.external
        finally:
            signal.signal(signal.SIGTERM, previous)
        report("passed", finite_updated_weights=True, exact_save_reload=True, sigterm_guard=True)
        backend.close()
        del backend, model
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        if args.llama_cpp_dir:
            from sleepmlx.export import export_gguf
            llama_dir = args.llama_cpp_dir.expanduser().resolve(strict=True)
            base_gguf = args.base_gguf.expanduser().resolve(strict=True)
            exported = root / "adapter.gguf"
            ok, message = export_gguf(str(llama_dir), str(model_dir), adapter, exported, timeout=60)
            assert ok, message
            print(json.dumps({"stage": "exported", "bytes": exported.stat().st_size,
                              "torch_mps_allocated_gb": torch.mps.current_allocated_memory() / 1e9
                              if torch.backends.mps.is_available() else 0}), flush=True)
            for label, active_adapter in (("base", None), ("adapter", exported)):
                result = served_completion(llama_dir / "build/bin/llama-server", base_gguf,
                                           active_adapter, prompt, root)
                print(json.dumps({"stage": "served_" + label, **result}), flush=True)


if __name__ == "__main__":
    main()
