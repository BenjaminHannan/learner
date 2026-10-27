"""Practice-2 on the Radeon PC: the OpenCode harness against llama.cpp (Windows llama-server.exe, Vulkan), started from WSL.

  llama-server.exe (K2 Q4_K_M GGUF [+ --lora adapter.gguf], -np N, --special)   <- POST /completion, raw prompt string
      <- practice.k2_proxy.Proxy(render_local=...) in this process: renders the prompt with oc_lessons.render_prompt (the function the lessons use),
         parses K2's native tool calls from the completion text, logs every call
      <- practice.oc_harness.OpenCodeHarness (`opencode run` per try, `concurrency` tries at once; use concurrency <= parallel)

Assumptions (documented, not hidden): the code runs in WSL (Ubuntu-24.04) with Windows interop on, so the exe can be started directly by its /mnt/c/... path and its
log goes to a file in WSL; WSL reaches the exe's port on 127.0.0.1 (mirrored networking or localhostForwarding; otherwise pass --ll-host <Windows IP>, the server
then binds 0.0.0.0). Windows paths for the exe are made with `wslpath -w` (a /mnt/c/... path becomes C:\\...). Stopping the server also runs taskkill on the image
name, because killing the WSL interop process does not reliably end the Windows process; only one GPU job runs at a time (HOWTO), so nothing else is hit.

Nights: HF LoRA in WSL (ROCm) as on CUDA. The next day needs the adapter as llama.cpp can load it, made lazily when a generation phase starts:
  1. "lora":   convert_lora_to_gguf.py --base <HF base dir> --outtype f32 <adapter dir>  ->  <adapter>/adapter.gguf   (served with --lora)
  2. "merged": merge the adapter into the fp16 HF model, convert_hf_to_gguf.py (f16), llama-quantize.exe Q4_K_M  ->  <adapter>/merged-Q4_K_M.gguf  (served with -m)
The first that converts AND whose server comes up is used (--ll-adapter-mode auto); the scripts come from the llama.cpp checkout --ll-src (the tag of the exe)."""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from .oc_cuda import VLLMServer


def use_llama(a):
    return getattr(a, "server", "vllm") == "llamacpp" or getattr(a, "backend", "") == "llamacpp"


# ------------------------------------------------------------------ paths / command
def is_win_exe(exe):
    return str(exe).lower().endswith(".exe") and os.name == "posix"


def winpath(p):
    """A WSL path as the Windows exe sees it: /mnt/c/x -> C:\\x; any other absolute path through `wslpath -w`; anything else unchanged."""
    p = str(p)
    if len(p) > 6 and p.startswith("/mnt/") and p[5].isalpha() and p[6] == "/":
        return p[5].upper() + ":\\" + p[7:].replace("/", "\\")
    if p.startswith("/") and shutil.which("wslpath"):
        return subprocess.run(["wslpath", "-w", p], capture_output=True, text=True, check=True).stdout.strip()
    return p


def llama_cmd(exe, gguf, port, ctx, parallel, adapter_gguf=None, host="127.0.0.1", extra=()):
    """`llama-server.exe -m <gguf> --port P -ngl 99 -c <ctx total> -np <parallel> --cont-batching [--lora <adapter.gguf>]`. The context is shared by the slots (ctx / parallel
    tokens each). --special writes control tokens (the <ifm|...> markers) into `content`, otherwise the stop string </ifm|tool_calls> could never match."""
    w = winpath if is_win_exe(exe) else str
    c = [str(exe), "-m", w(gguf), "--host", "127.0.0.1" if host in ("127.0.0.1", "localhost") else "0.0.0.0", "--port", str(port), "-ngl", "99", "-c", str(int(ctx)),
         "-np", str(int(parallel)), "--cont-batching", "--special"]
    if adapter_gguf:
        c += ["--lora", w(adapter_gguf)]
    return c + list(extra)


class LlamaServer(VLLMServer):
    """VLLMServer's lifecycle for llama-server (.exe through WSL interop, or a native binary). Ready = GET /health answers 200 (503 while the model loads)."""
    label = "llama.cpp"

    def __init__(self, cmd, port, log_path, log=print, wait_s=600, host="127.0.0.1"):
        super().__init__(cmd, port, log_path, log, wait_s)
        self.host = host
        self.image = os.path.basename(cmd[0]) if is_win_exe(cmd[0]) else None
        self.cwd = os.path.dirname(cmd[0]) or None if self.image else None  # a Windows exe must not start in a \\wsl.localhost cwd

    @property
    def base_url(self):
        return f"http://{self.host}:{self.port}"

    def ready(self):
        with urllib.request.urlopen(self.base_url + "/health", timeout=3) as r:
            return json.load(r)

    @staticmethod
    def kill_leftover(exe):
        if is_win_exe(exe):
            try:
                subprocess.run(["taskkill.exe", "/F", "/IM", os.path.basename(str(exe))], capture_output=True, timeout=30)
            except Exception:  # noqa: BLE001
                pass

    def _taskkill(self):
        if self.image:
            self.kill_leftover(self.cmd[0])

    def start(self):
        self._taskkill()  # a server leaked by a crashed worker would hold the port and the VRAM
        return super().start()

    def stop(self):
        super().stop()
        self._taskkill()


# ------------------------------------------------------------------ server-side tokenizer checks
def _tokenize(base_url, text, add_special):
    req = urllib.request.Request(base_url + "/tokenize", json.dumps({"content": text, "add_special": add_special, "parse_special": True}).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["tokens"]


def server_adds_bos(base_url, bos_text):
    """Does /completion (which tokenizes with add_special=true) put a BOS in front of a prompt that has none? Probed with /tokenize. Also checks that the template's
    bos_token text is ONE special token for the server (so a kept template BOS is a single BOS, not text)."""
    plain, spec = _tokenize(base_url, "x", False), _tokenize(base_url, "x", True)
    adds = len(spec) > len(plain)
    if bos_text:
        b = _tokenize(base_url, bos_text, False)
        if len(b) != 1:
            raise RuntimeError(f"the template's bos_token {bos_text!r} is {len(b)} tokens for llama-server, not one special token")
        if adds and spec[0] != b[0]:
            raise RuntimeError(f"llama-server adds token {spec[0]} in front, not the template's bos_token {b[0]}")
    return adds


def token_parity(base_url, tok, template, strip_bos, sample=None):
    """The rendered prompt of a sample request: HF ids (what lessons train on) vs llama-server ids (what it serves). -> (ok, n_hf, n_server, first_diff)."""
    from .oc_lessons import render_prompt
    msgs = sample or [{"role": "system", "content": "You are a careful assistant."}, {"role": "user", "content": "What is 1+5? (two\nlines, <answer> tags)"},
                      {"role": "assistant", "content": "Let me run it.", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "bash", "arguments": '{"command": "echo 6"}'}}]},
                      {"role": "tool", "tool_call_id": "c1", "content": "6"}]
    tools = [{"type": "function", "function": {"name": "bash", "description": "run a command", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}}}}]
    text = render_prompt(msgs, tools, tok, template, bos=getattr(tok, "bos_token", None))
    hf = tok(text, add_special_tokens=False).input_ids
    cut = text[len(strip_bos):] if strip_bos and text.startswith(strip_bos) else text
    srv = _tokenize(base_url, cut, True)
    diff = next((i for i, (x, y) in enumerate(zip(hf, srv)) if x != y), None if len(hf) == len(srv) else min(len(hf), len(srv)))
    return diff is None, len(hf), len(srv), diff


# ------------------------------------------------------------------ adapter -> GGUF
def _run(cmd, log, what, timeout=3600):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f"{what} failed (rc {r.returncode}): {(r.stderr or r.stdout).strip()[-600:]}")
    log(f"{what}: ok")


def base_dir(model):
    """Local HF dir of the base model (config + tokenizer files are enough for convert_lora_to_gguf)."""
    if os.path.isdir(str(model)):
        return str(model)
    from huggingface_hub import snapshot_download
    return snapshot_download(str(model), allow_patterns=["*.json", "*.py", "*.txt", "*.model", "*.jinja"])


def convert_lora(adapter, a, log):
    out = Path(adapter) / "adapter.gguf"
    if not out.exists() or out.stat().st_size == 0:
        script = Path(a.ll_src) / "convert_lora_to_gguf.py"
        _run([sys.executable, str(script), "--base", base_dir(a.model), "--outtype", "f32", "--outfile", str(out), str(adapter)], log, "convert_lora_to_gguf")
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError("convert_lora_to_gguf wrote no file")
    return str(out)


def merge_adapter(model, adapter, out_dir):
    """fp16 merge on the CPU (15 GB of RAM: the 3.7B model is 7.4 GB; run in its own process so it is gone before the server starts)."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    m = AutoModelForCausalLM.from_pretrained(model, dtype=torch.float16, trust_remote_code=True, low_cpu_mem_usage=True)
    m = PeftModel.from_pretrained(m, str(adapter)).merge_and_unload()
    m.save_pretrained(str(out_dir), safe_serialization=True)
    AutoTokenizer.from_pretrained(model, trust_remote_code=True).save_pretrained(str(out_dir))


def convert_merged(adapter, a, log):
    out = Path(adapter) / "merged-Q4_K_M.gguf"
    if out.exists() and out.stat().st_size > 0:
        return str(out)
    mdir, f16 = Path(adapter) / "merged_hf", Path(adapter) / "merged-f16.gguf"
    _run([sys.executable, "-m", "practice.oc_llama", "merge", "--model", str(a.model), "--adapter", str(adapter), "--out", str(mdir)], log, "merge adapter into the fp16 model")
    _run([sys.executable, str(Path(a.ll_src) / "convert_hf_to_gguf.py"), str(mdir), "--outfile", str(f16), "--outtype", "f16"], log, "convert_hf_to_gguf")
    q = Path(os.path.dirname(str(a.ll_exe))) / ("llama-quantize.exe" if is_win_exe(a.ll_exe) else "llama-quantize")
    w = winpath if is_win_exe(a.ll_exe) else str
    _run([str(q), w(f16), w(out), "Q4_K_M"], log, "llama-quantize Q4_K_M")
    shutil.rmtree(mdir, ignore_errors=True)
    f16.unlink(missing_ok=True)
    return str(out)


def adapter_candidates(adapter, a, log):
    """Yield ("lora", adapter.gguf) then ("merged", merged.gguf) (lazily: the second is only converted when the first did not work), per --ll-adapter-mode."""
    mode = getattr(a, "ll_adapter_mode", "auto")
    for kind, fn in (("lora", convert_lora), ("merged", convert_merged)):
        if mode in ("auto", kind):
            try:
                yield kind, fn(adapter, a, log)
            except Exception as e:  # noqa: BLE001
                log(f"adapter path {kind!r} failed: {e!r}")


# ------------------------------------------------------------------ glue for OCBackend
def llama_setup(a, tok, template, adapter, out_dir, log, upstream=None):
    """-> (server or None, upstream url, Proxy kwargs, upstream model alias). `upstream` (tests / an already running llama-server) skips starting a server."""
    host, port = getattr(a, "ll_host", "127.0.0.1"), a.oc_port
    server = None
    if not upstream:
        par = int(a.ll_parallel)
        ctx = int(a.ll_ctx) or par * int(a.oc_max_len)
        extra = str(getattr(a, "ll_extra", "") or "").split()
        base = a.ll_gguf
        err = None
        for kind, path in (adapter_candidates(adapter, a, log) if adapter else [(None, None)]):
            cmd = llama_cmd(a.ll_exe, path if kind == "merged" else base, port, ctx, par, path if kind == "lora" else None, host, extra)
            server = LlamaServer(cmd, port, Path(out_dir) / "server_logs" / f"llama_{int(time.time())}.log", log, host=host)
            try:
                server.start()
                log(f"llama-server adapter path: {kind}, {path}")
                break
            except (RuntimeError, TimeoutError) as e:
                err, server = e, None
                log(f"llama-server did not start with adapter path {kind!r}: {e!r}")
        if server is None:
            raise RuntimeError(f"no llama-server configuration worked for adapter {adapter}: {err!r}")
        upstream = server.base_url
    bos = getattr(tok, "bos_token", None) or ""
    mode = getattr(a, "ll_strip_bos", "auto")
    adds = server_adds_bos(upstream, bos) if mode == "auto" else mode == "yes"
    strip = bos if adds else ""
    ok, n_hf, n_srv, diff = token_parity(upstream, tok, template, strip)
    log(f"llama-server BOS: server adds {'one' if adds else 'none'}, template bos {bos!r} {'stripped' if strip else 'kept'}; token parity with HF {'OK' if ok else 'MISMATCH'} "
        f"({n_hf} vs {n_srv} tokens" + ("" if ok else f", first difference at {diff}") + ")")
    if not ok:
        log("WARNING prompt tokens differ between the HF tokenizer (training) and llama-server (serving)")
    alias = Path(adapter).name if adapter else "default_model"
    return server, upstream, {"upstream_model": alias, "render_local": {"tokenizer": tok, "template": template, "strip_bos": strip}}, alias


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge", help="merge a PEFT adapter into the fp16 HF model")
    m.add_argument("--model", required=True)
    m.add_argument("--adapter", required=True)
    m.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    merge_adapter(a.model, a.adapter, a.out)


if __name__ == "__main__":
    main()
