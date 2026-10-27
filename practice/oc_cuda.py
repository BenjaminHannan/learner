"""Practice-2 on a CUDA box through the OpenCode harness (PREREG-2 addendum 1; the CUDA twin of `mac_run --harness opencode`).

  vLLM OpenAI server (own venv, K2 nothink chat template, LoRA enabled, vLLM's own tool parser OFF)
      <- practice.k2_proxy.Proxy (in this process: parses K2's native tool calls, logs every call; model name = the served / LoRA name)
      <- practice.oc_harness.OpenCodeHarness (`opencode run` per try, `concurrency` tries at once)

One OCBackend per generation phase (job.py runs every day / eval in its own subprocess): it starts the server with the phase's adapter, and `runner` is the
object the Lane uses as its harness (same run(...) contract as practice.harness.Harness). Adapters: the server is started once per phase with
`--lora-modules night<N>=<adapter dir>` (restart-per-adapter: no dynamic LoRA loading, nothing to go stale, and the server is gone before the HF night starts).
Each finished try gets `segs` (oc_lessons.oc_segments: the text K2 saw and wrote, trained flags) exactly as mac_run stores them; lessons.target_of masks the
bare final <answer> turns when the night is built. Tries that errored (opencode died because the server died) are not scored: the server is restarted and they
are redone, up to 3 rounds, as mac_run.run_tries does."""
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from .k2_proxy import VLLM_PROXY_OPTS
from .oc_harness import OpenCodeHarness
from .oc_lessons import load_template, oc_segments

HERE = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = HERE / "k2_nothink.jinja"  # committed with the code, so it exists on the box
IM_END = "<|ifm|im_end|>"


def template_path(a):
    p = getattr(a, "chat_template", None) or str(DEFAULT_TEMPLATE)
    load_template(p)  # raises if missing
    return str(p)


def vllm_cmd(vpy, model, port, template, adapter=None, lora_name=None, max_len=16384, util=0.85, max_seqs=64, seed=1, eager=False):
    """`vllm serve` command line. Served name is "default_model" (the base); a trained adapter is added as LoRA module `lora_name`. No --enable-auto-tool-choice and
    no --tool-call-parser: k2_proxy parses K2's tool calls itself."""
    c = [vpy, "-m", "vllm.entrypoints.cli.main", "serve", str(model), "--served-model-name", "default_model", "--host", "127.0.0.1", "--port", str(port),
         "--trust-remote-code", "--dtype", "float16", "--max-model-len", str(max_len), "--gpu-memory-utilization", str(util), "--enable-prefix-caching",
         "--max-num-seqs", str(max_seqs), "--seed", str(seed), "--chat-template", str(template), "--enable-lora", "--max-lora-rank", "16", "--max-loras", "1"]
    if adapter:
        c += ["--lora-modules", f"{lora_name}={adapter}"]
    if eager:
        c.append("--enforce-eager")
    return c


class VLLMServer:
    def __init__(self, cmd, port, log_path, log=print, wait_s=1500):
        self.cmd, self.port, self.log_path, self.log, self.wait_s = cmd, int(port), log_path, log, wait_s
        self.proc = self.logf = None

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.port}"

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self):
        self.stop()
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
        self.logf = open(self.log_path, "a")
        self.log("starting vLLM server: " + " ".join(self.cmd))
        # same process group as the phase worker: job.kill_group(worker) takes the server (and its engine children) with it
        self.proc = subprocess.Popen(self.cmd, stdout=self.logf, stderr=subprocess.STDOUT, env=dict(os.environ, VLLM_WORKER_MULTIPROC_METHOD="spawn"))
        t0 = time.time()
        while time.time() - t0 < self.wait_s:
            if self.proc.poll() is not None:
                raise RuntimeError(f"vLLM server exited early (code {self.proc.returncode}); see {self.log_path}")
            try:
                with urllib.request.urlopen(self.base_url + "/v1/models", timeout=3) as r:
                    ids = [m["id"] for m in json.load(r).get("data", [])]
                self.log(f"vLLM server up in {time.time() - t0:.0f}s, models {ids}")
                return ids
            except Exception:  # noqa: BLE001
                time.sleep(3)
        self.stop()
        raise TimeoutError(f"vLLM server did not answer /v1/models in {self.wait_s}s; see {self.log_path}")

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.proc = None
        if self.logf:
            self.logf.close()
            self.logf = None


class OCRunner:
    """Harness-shaped wrapper (run / stats) around OpenCodeHarness: adds segs to each record and redoes errored tries after a server restart."""

    def __init__(self, harness, tok, template, restart=None, log=print, rounds=3):
        self.H, self.tok, self.template, self.restart, self.log, self.rounds = harness, tok, template, restart, log, rounds
        self.bos = (getattr(tok, "bos_token", None) or "") if tok is not None else ""

    @property
    def stats(self):
        return self.H.stats

    def finish(self, rec):
        try:
            rec["segs"] = oc_segments(rec, self.tok, self.template, bos=self.bos, train_bare_answers=True)  # as served; lessons.target_of applies the bare-answer rule
        except Exception as e:  # noqa: BLE001
            rec["segs_error"] = repr(e)
        rec.pop("proxy_tools", None)  # the 13 KB tools copy
        return rec

    def run(self, puzzles, tries, seed=0, deadline=None, inflight=None, on_done=None, label="", have=()):
        """Try k of every puzzle not in `have` ((id, k) pairs already saved). Returns the new records; on_done(rec) is called for every scored one."""
        have = set(have)
        out, errs = [], []

        def sink(rec, k, last=False):
            rec["try"] = k
            if rec.get("end") == "error" and not last:
                errs.append((rec["id"], k, rec.get("error", "")[:200]))
                return
            self.finish(rec)
            out.append(rec)
            if on_done:
                on_done(rec)

        self.H.run(puzzles, tries, seed=seed, deadline=deadline, inflight=inflight, on_done=lambda r: sink(r, r["try"]), label=label, skip=have)
        for rnd in range(self.rounds):
            if not errs:
                break
            redo = [(i, k) for i, k, _ in errs]
            self.log(f"{label}: {len(errs)} errored tries (e.g. {errs[-1][2]!r}); restarting the server and redoing them (round {rnd + 1})")
            errs.clear()
            if self.restart:
                self.restart()
            byid = {p["id"]: p for p in puzzles}
            for k in sorted({k for _, k in redo}):
                self.H.run([byid[i] for i, kk in redo if kk == k], 1, seed=seed * 10 + k + 1000 * (rnd + 1), deadline=deadline, inflight=inflight,
                           on_done=lambda r, k=k: sink(r, k, last=rnd == self.rounds - 1), label=f"{label} redo{rnd + 1} try{k}")
        return out


class OCBackend:
    """Server (unless `a.oc_upstream` names an existing one, used by the CPU smoke) + in-process proxy + OpenCode harness for one generation phase."""
    name = "opencode"

    def __init__(self, a, tok, model_name, adapter=None, lora_id=1, log=print, out_dir=None, vpy=None):
        self.log, self.adapter = log, adapter
        out_dir = Path(out_dir or ".")
        self.template = template_path(a)
        alias = Path(adapter).name if adapter else "default_model"  # what the proxy sends upstream: the base, or the LoRA module
        ext = json.loads(json.dumps(VLLM_PROXY_OPTS["upstream_extra"]))
        ids = [tok.convert_tokens_to_ids(IM_END)] + ([tok.eos_token_id] if tok.eos_token_id is not None else [])
        ext["stop_token_ids"] = sorted({i for i in ids if isinstance(i, int) and i >= 0})
        self.server = None
        upstream = getattr(a, "oc_upstream", None)
        if not upstream:
            cmd = vllm_cmd(vpy or sys.executable, model_name, a.oc_port, self.template, adapter, alias, a.oc_max_len, a.oc_util, getattr(a, "oc_max_seqs", 64),
                           int(getattr(a, "seed", 1) or 1), bool(getattr(a, "oc_eager", False)))
            self.server = VLLMServer(cmd, a.oc_port, out_dir / "server_logs" / f"vllm_{int(time.time())}.log", log)
            self.server.start()
            upstream = self.server.base_url
        self.conc = int(a.oc_concurrency)
        self.harness = OpenCodeHarness(None, str(out_dir / "proxy_logs"), upstream=upstream, concurrency=self.conc, timeout=a.oc_timeout, max_steps=a.oc_steps,
                                       web=bool(getattr(a, "web", True)), log=log,
                                       proxy_kw={"upstream_model": alias, "upstream_extra": ext, "args_as_json": True})
        self.runner = OCRunner(self.harness, tok, self.template, restart=self.server.start if self.server else None, log=log)
        log(f"OpenCode harness: concurrency {self.conc}, upstream model {alias!r}, adapter {adapter}, template {self.template}")

    def describe(self):
        return f"opencode via vllm concurrency={self.conc}" + (f" adapter={self.adapter}" if self.adapter else "")

    def arc_eval(self, arc, render):
        raise NotImplementedError("ARC-Easy is not run through the OpenCode harness (Practice-2 uses --arc-n 0)")

    def close(self):
        try:
            if self.harness.proxy:
                self.harness.proxy.stop()
        finally:
            if self.server:
                self.server.stop()


def warm(log=print):
    """One OpenCode try against the fake upstream (tests/k2_fake_upstream.py), to create opencode's data dir / database and prove node + opencode work on this box
    before a long job. Returns True when the try was answered correctly."""
    import tempfile
    from tests import k2_fake_upstream as F
    up = F.start()
    h = None
    try:
        d = tempfile.mkdtemp(prefix="ocwarm_")
        h = OpenCodeHarness(None, d, upstream=f"http://127.0.0.1:{up.server_address[1]}", concurrency=1, timeout=300, web=False, log=log, proxy_kw={"upstream_model": "default_model"})
        r = h.run([{"id": "warm", "kind": "arith", "source": "warm", "prompt": "What is 1+5?", "answer": "6", "answer_type": "int"}], 1, label="warm")[0]
        log(f"opencode warm try: end={r['end']} correct={r['correct']} tool_calls={r['tool_calls']} {r.get('error', '')}")
        return bool(r["correct"] and r["tool_calls"] == 1)
    finally:
        if h is not None and h.proxy:
            h.proxy.stop()
        up.shutdown()


if __name__ == "__main__":
    if "--warm" in sys.argv:
        sys.exit(0 if warm() else 1)
    sys.exit("usage: python -m practice.oc_cuda --warm")
