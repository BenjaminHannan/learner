"""Generation backends for the Practice-1 harness.
  hf_generate: batched HF generate with per-sequence stop at '</input>' (and <|ifm|im_end|>), a batch size that stays reduced after an OOM
               (BsState), a prefill-token budget that is learned from OOMs, and length-sorted batches.
  VLLMBackend: offline vLLM engine (prefix caching, LoRA served from a saved peft adapter, same prompt token ids as the HF path).
The two paths use the same rendered prompts, the same stop rule and the same sampling settings (temperature, top_p 1, no top_k)."""
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

try:  # the Mac (MLX) path runs without torch
    import torch
except ImportError:  # pragma: no cover
    torch = None

STOP_TEXT = "</input>"
from .tools import CLOSE_TAGS as STOP_TEXTS, close_open_tag  # noqa: E402  every tool tag closer stops a reply
IM_END = "<|ifm|im_end|>"


class BsState:
    """Sticky batch size. An OOM halves `bs` for the rest of the run and lowers `tok_budget` (max padded prompt tokens per batch);
    after `grow_after` clean calls bs may grow back by 1, but never up to the size that failed."""

    def __init__(self, bs=8, tok_budget=8000, grow_after=20):
        self.bs, self.cap, self.tok_budget, self.grow_after = max(1, int(bs)), max(1, int(bs)), tok_budget, grow_after
        self.clean, self.fail_bs, self.ooms = 0, None, 0

    def oom(self, n_rows, padded_len):
        self.ooms += 1
        self.fail_bs = n_rows if self.fail_bs is None else min(self.fail_bs, n_rows)
        self.bs = max(1, min(self.bs, n_rows) // 2) if n_rows > 1 else 1
        self.tok_budget = max(512, min(self.tok_budget, int(0.7 * n_rows * padded_len)))
        self.clean = 0

    def ok(self):
        self.clean += 1
        if self.clean >= self.grow_after:
            self.clean = 0
            if self.bs + 1 < (self.fail_bs if self.fail_bs is not None else self.cap + 1) and self.bs < self.cap:
                self.bs += 1

    def describe(self):
        return f"hf bs={self.bs} tok_budget={self.tok_budget} ooms={self.ooms}"


class StopOnText:
    """StoppingCriteria: a row is finished once `text` appears among its last `tail` generated tokens (prompt tokens are ignored)."""

    def __init__(self, tok, plen, text=None, tail=8):
        self.tok, self.plen, self.tail = tok, plen, tail
        self.texts = [text] if text else list(STOP_TEXTS)

    def __call__(self, input_ids, scores=None, **kw):
        gen = input_ids[:, self.plen:]
        if gen.shape[1] == 0:
            return torch.zeros(input_ids.shape[0], dtype=torch.bool, device=input_ids.device)
        texts = self.tok.batch_decode(gen[:, -self.tail:], skip_special_tokens=False)
        return torch.tensor([any(x in t for x in self.texts) for t in texts], dtype=torch.bool, device=input_ids.device)


def stop_ids(tok):
    ids = [tok.convert_tokens_to_ids(IM_END)]
    if tok.eos_token_id is not None:
        ids.append(tok.eos_token_id)
    return [i for i in ids if i is not None and i >= 0]


def _no_grad(f):
    return torch.no_grad()(f) if torch is not None else f


@_no_grad
def hf_generate(model, tok, prompts, max_new, temperature=0.7, seed=0, bs=8, log=None, first_words=None):
    """Decoded new text of every prompt, in input order. Stops each sequence at '</input>' (kept in the text) or <|ifm|im_end|> (cut).
    `bs` is an int or a BsState (shared across calls so a reduced size sticks)."""
    from transformers import StoppingCriteriaList
    st = bs if isinstance(bs, BsState) else BsState(bs)
    dev = next(model.parameters()).device
    enc_all = [tok(p, add_special_tokens=False).input_ids for p in prompts]
    order = sorted(range(len(prompts)), key=lambda i: len(enc_all[i]))
    outs = [None] * len(prompts)
    stops = stop_ids(tok)
    was_training = model.training
    model.eval()
    use_cache_prev = getattr(model.config, "use_cache", True)
    model.config.use_cache = True
    i, k = 0, 0
    while i < len(order):
        idx = order[i:i + st.bs]
        while len(idx) > 1 and len(idx) * len(enc_all[idx[-1]]) > st.tok_budget:  # sorted ascending: the last row sets the padded length
            idx = idx[:-1]
        plen = len(enc_all[idx[-1]])
        try:
            batch = tok.pad({"input_ids": [enc_all[j] for j in idx]}, padding=True, return_tensors="pt").to(dev)
            torch.manual_seed(seed * 1000003 + k)
            kwargs = dict(max_new_tokens=max_new, eos_token_id=stops, pad_token_id=tok.pad_token_id,
                          stopping_criteria=StoppingCriteriaList([StopOnText(tok, batch["input_ids"].shape[1])]))
            if temperature > 0:
                kwargs.update(do_sample=True, temperature=temperature, top_p=1.0, top_k=0)
            else:
                kwargs.update(do_sample=False)
            g = model.generate(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"], **kwargs)
        except (torch.OutOfMemoryError, RuntimeError) as e:
            if len(idx) == 1 and st.bs == 1:
                raise
            st.oom(len(idx), plen)
            if log:
                log(f"generate failed at {len(idx)} rows x {plen} tokens ({str(e)[:80]}); {st.describe()}")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            continue
        new = g[:, batch["input_ids"].shape[1]:]
        for row, j in zip(new, idx):
            ids = row.tolist()
            cut = next((p for p, t in enumerate(ids) if t in stops), len(ids))
            outs[j] = tok.decode(ids[:cut], skip_special_tokens=False).replace(tok.pad_token or "", "")
        i += len(idx)
        k += 1
        st.ok()
    model.config.use_cache = use_cache_prev
    if was_training:
        model.train()
    return outs


class VLLMBackend:
    """Offline vLLM engine. One engine per process; build it in a worker subprocess and let the process exit to free the GPU."""
    name = "vllm"
    inflight = 64

    def __init__(self, model_id, tok, adapter=None, lora_id=1, max_len=4096, util=0.85, eager=False, seed=0, log=print):
        import vllm
        from vllm import LLM
        self.tok, self.log, self.stops = tok, log, stop_ids(tok)
        self.eager = eager
        kw = dict(model=model_id, trust_remote_code=True, dtype="float16", max_model_len=max_len, gpu_memory_utilization=util, enable_prefix_caching=True,
                  enable_lora=True, max_lora_rank=16, max_loras=1, max_num_seqs=self.inflight, seed=seed, enforce_eager=eager)
        t = time.time()
        self.llm = LLM(**kw)
        self.startup_s = round(time.time() - t, 1)
        self.lora = None
        if adapter:
            from vllm.lora.request import LoRARequest
            self.lora = LoRARequest(f"night{lora_id}", lora_id, str(adapter))
        self.version = vllm.__version__
        log(f"vLLM {self.version} engine up in {self.startup_s}s eager={eager} adapter={adapter}")

    def describe(self):
        return f"vllm{'-eager' if self.eager else ''} max_num_seqs={self.inflight}"

    def generate(self, prompts, max_new, temperature, seed):
        from vllm import SamplingParams
        ids = [self.tok(p, add_special_tokens=False).input_ids for p in prompts]  # the exact tokens the HF path feeds (no second BOS)
        sps = [SamplingParams(temperature=temperature, top_p=1.0, max_tokens=max_new, stop=list(STOP_TEXTS), include_stop_str_in_output=True,
                              stop_token_ids=self.stops, skip_special_tokens=False, seed=(seed * 1000003 + n) % (2 ** 31)) for n in range(len(ids))]
        res = self.llm.generate([{"prompt_token_ids": x} for x in ids], sps, lora_request=self.lora, use_tqdm=False)
        outs = []
        for r in res:
            t = r.outputs[0].text
            j = t.find(IM_END)
            outs.append(t[:j] if j >= 0 else t)
        return outs

    def arc_eval(self, arc, render):
        """Letter with the best next-token score among the answer labels (greedy over allowed ids = argmax over the candidates, as the HF path)."""
        from vllm import SamplingParams
        reqs, sps, cands = [], [], []
        for q in arc:
            user = q["q"] + "\n" + "\n".join(f"{l}. {t}" for l, t in zip(q["labels"], q["texts"])) + "\nAnswer with the letter only."
            p = render([{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": user}], True, self.tok.bos_token or "")
            cand = [self.tok(l, add_special_tokens=False).input_ids[0] for l in q["labels"]]
            reqs.append({"prompt_token_ids": self.tok(p, add_special_tokens=False).input_ids})
            sps.append(SamplingParams(temperature=0.0, max_tokens=1, allowed_token_ids=cand, skip_special_tokens=False))
            cands.append(cand)
        res = self.llm.generate(reqs, sps, lora_request=self.lora, use_tqdm=False)
        ok = 0
        for q, cand, r in zip(arc, cands, res):
            tid = r.outputs[0].token_ids[0]
            ok += q["labels"][cand.index(tid)] == q["a"] if tid in cand else 0
        return {"acc": ok / max(1, len(arc)), "n": len(arc)}


# ====================================================================== Mac / OpenAI-compatible backend (mlx_lm.server)
STOPS = list(STOP_TEXTS) + [IM_END]


def _post_json(url, body, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _get_json(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


class OpenAIBackend:
    """Talks to a local `mlx_lm.server` (POST /v1/completions with the exact rendered prompt string). N parallel requests via threads.
    Same interface as VLLMBackend for the Harness: .inflight, .describe(), .generate(prompts, max_new, temperature, seed).
    `strip_prefix` (the BOS text) is removed from the front of every prompt when the server tokenizer adds BOS itself (avoids a double BOS).
    A stop string is not returned by the server, so when the reply stopped on a stop string with an unclosed <input>, '</input>' is put back
    (the HF/vLLM paths keep it in the text)."""
    name = "openai"

    def __init__(self, base_url, model="default_model", workers=4, strip_prefix="", timeout=900, retries=2, send_seed=True, post=None, log=print, gate=None):
        self.base, self.model, self.workers, self.strip_prefix = base_url.rstrip("/"), model, int(workers), strip_prefix
        self.inflight, self.timeout, self.retries, self.send_seed, self.log = self.workers, timeout, retries, send_seed, log
        self._post = post or _post_json
        self.gate = gate  # called before every request (memory-pressure / pause backoff)
        self.pool = ThreadPoolExecutor(self.workers)
        self.completion_tokens = 0
        self.lock = threading.Lock()

    def describe(self):
        return f"openai-compat {self.base} workers={self.workers}"

    def _one(self, prompt, max_new, temperature, seed):
        if self.strip_prefix and prompt.startswith(self.strip_prefix):
            prompt = prompt[len(self.strip_prefix):]
        body = {"model": self.model, "prompt": prompt, "max_tokens": int(max_new), "temperature": float(temperature), "top_p": 1.0, "stop": STOPS, "stream": False}
        if self.send_seed:
            body["seed"] = int(seed) % (2 ** 31)
        err = None
        for a in range(self.retries + 1):
            if self.gate:
                self.gate()
            try:
                r = self._post(self.base + "/v1/completions", body, self.timeout)
                ch = r["choices"][0]
                text = ch.get("text") or ""
                j = text.find(IM_END)
                if j >= 0:
                    text = text[:j]
                if ch.get("finish_reason") == "stop":
                    text = close_open_tag(text)
                with self.lock:
                    self.completion_tokens += int((r.get("usage") or {}).get("completion_tokens") or 0)
                return text
            except Exception as e:  # noqa: BLE001
                err = e
                time.sleep(2 * (a + 1))
        self.log(f"openai backend request failed after retries: {err!r}")
        # raise, not "": an empty reply would be saved as a real (failed) try; a crashed run resumes cleanly instead
        raise RuntimeError(f"openai backend request failed after retries: {err!r}")

    def generate(self, prompts, max_new, temperature, seed):
        futs = [self.pool.submit(self._one, p, max_new, temperature, seed * 1000003 + n) for n, p in enumerate(prompts)]
        return [f.result() for f in futs]


PROMPT_CACHE_BYTES = 1 * 2 ** 30
SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mlx_server.py")  # mlx_lm.server, capped MLX buffer cache


class ServerManager:
    """Starts / stops one `mlx_lm.server` subprocess. One server at a time; ensure() restarts only when (model, adapter) changes.
    CLI flags used (mlx-lm >= 0.2x): --model, --adapter-path, --host, --port, and (only if listed in `--help`) --decode-concurrency / --prompt-concurrency."""

    def __init__(self, python=None, port=8089, log_dir=".", log=print, wait_s=600):
        self.python, self.port, self.log_dir, self.log, self.wait_s = python or sys.executable, int(port), log_dir, log, wait_s
        self.proc, self.cur, self.logf = None, None, None
        self._help = None

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.port}"

    def supports(self, flag):
        if self._help is None:
            try:
                self._help = subprocess.run([self.python, "-m", "mlx_lm.server", "--help"], capture_output=True, text=True, timeout=120).stdout
            except Exception:  # noqa: BLE001
                self._help = ""
        return flag in self._help

    def cmd(self, model, adapter=None, concurrency=4):
        c = [self.python, SERVER_SCRIPT, "--model", str(model), "--host", "127.0.0.1", "--port", str(self.port)]
        if adapter:
            c += ["--adapter-path", str(adapter)]
        for flag in ("--decode-concurrency", "--prompt-concurrency"):
            if self.supports(flag):
                c += [flag, str(concurrency)]
        if self.supports("--prompt-cache-bytes"):  # uncapped, the prompt cache grew each server to 14-16 GB on the 36 GB M3 (swap)
            c += ["--prompt-cache-bytes", str(PROMPT_CACHE_BYTES)]
        return c + list(getattr(self, "extra", []))  # e.g. --chat-template for the OpenCode harness

    def start(self, model, adapter=None, concurrency=4):
        self.stop()
        os.makedirs(self.log_dir, exist_ok=True)
        self.logf = open(os.path.join(self.log_dir, f"mlx_server_{int(time.time())}.log"), "w")
        c = self.cmd(model, adapter, concurrency)
        self.log("starting server: " + " ".join(c))
        self.proc = subprocess.Popen(c, stdout=self.logf, stderr=subprocess.STDOUT, start_new_session=True)
        t0 = time.time()
        while time.time() - t0 < self.wait_s:
            if self.proc.poll() is not None:
                self.stop()
                raise RuntimeError(f"mlx_lm.server exited early (code {self.proc.returncode}); see {self.logf.name}")
            try:
                _get_json(self.base_url + "/v1/models", 3)
                self.cur = (str(model), str(adapter) if adapter else None, concurrency)
                self.log(f"server up in {time.time() - t0:.0f}s")
                return
            except Exception:  # noqa: BLE001
                time.sleep(2)
        self.stop()
        raise TimeoutError("mlx_lm.server did not answer /v1/models in time")

    def ensure(self, model, adapter=None, concurrency=4):
        want = (str(model), str(adapter) if adapter else None, concurrency)
        if self.proc is not None and self.proc.poll() is None and self.cur == want:
            return
        self.start(model, adapter, concurrency)

    def stop(self):
        p, self.proc, self.cur = self.proc, None, None
        if p is not None and p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGTERM)
                p.wait(20)
            except Exception:  # noqa: BLE001
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait(10)
                except Exception:  # noqa: BLE001
                    pass
        if self.logf:
            self.logf.close()
            self.logf = None

    def rss_mb(self):
        """Resident memory of the server process group in MB (ps)."""
        if self.proc is None:
            return 0.0
        try:
            out = subprocess.run(["ps", "-o", "rss=", "-p", str(self.proc.pid)], capture_output=True, text=True, timeout=10).stdout
            return sum(int(x) for x in out.split()) / 1024
        except Exception:  # noqa: BLE001
            return 0.0
