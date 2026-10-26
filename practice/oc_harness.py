"""Run puzzle tries through the real assistant harness: `opencode run` (headless) -> k2_proxy -> mlx_lm.server.

Same interface as practice.harness.Harness.run(puzzles, tries, seed, on_done, label) and the same record keys as Rollout.record, plus
"harness": "opencode" and "proxy_calls" (the exact request messages, tools hash and raw completion of every model call, so a lesson can be
rendered exactly as served; see oc_lessons.py).

Start the proxy first (python -m practice.k2_proxy --port 8095 --upstream http://127.0.0.1:18081 --log DIR), or pass proxy_url=None to run one
in this process (then pass `upstream`).
"""
import json
import os
import random
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from . import tools as T
from .grade import check
from .k2_proxy import Proxy, parse_native, read_try_log, safe_key

AGENT_PROMPT = ("You solve puzzles. Work out the rule or the plan step by step. Use the bash tool to run python3 to check your work before you answer. "
                "When you are sure, reply with the final answer inside <answer>...</answer> and nothing else after it: an integer, a short word or phrase, "
                "or a grid (one row per line, digits separated by spaces).")
TOOLS_ON = ("bash", "read", "write", "webfetch", "websearch")
_ANS = re.compile(r"<answer>(.*?)</answer>", re.S | re.I)
_ANS_OPEN = re.compile(r"<answer>(.*)\Z", re.S | re.I)


def make_config(base_url, max_new=1024, temperature=0.7, max_steps=12, context=32768, prompt=AGENT_PROMPT, headers=None):
    """The per-run OPENCODE_CONFIG_CONTENT: one provider (the proxy), one model, one primary agent, only TOOLS_ON enabled, no title/summary/compaction calls."""
    # opencode gates write, edit and patch behind the single "edit" permission, so enabling write also exposes edit (cannot be split)
    tools = {"*": False, **{t: True for t in TOOLS_ON}}
    return {
        "$schema": "https://opencode.ai/config.json", "model": "k2p/k2", "small_model": "k2p/k2", "default_agent": "practice",
        "provider": {"k2p": {"npm": "@ai-sdk/openai-compatible", "name": "K2 via k2_proxy",
                             "options": {"baseURL": base_url, "apiKey": "local", "headers": headers or {}, "timeout": False, "chunkTimeout": False},
                             "models": {"k2": {"name": "K2 3.7B", "tool_call": True, "reasoning": False, "temperature": True,
                                               "limit": {"context": context, "output": max_new}}}}},
        "agent": {"practice": {"mode": "primary", "description": "puzzle solver", "prompt": prompt, "temperature": temperature, "steps": max_steps, "tools": tools,
                               "permission": {"bash": "allow", "read": "allow", "edit": "allow", "webfetch": "allow", "websearch": "allow",
                                              "external_directory": "deny", "doom_loop": "deny", "question": "deny"}},
                  "title": {"disable": True}, "summary": {"disable": True}, "compaction": {"disable": True}},
        "tools": tools, "compaction": {"auto": False}, "snapshot": False, "share": "disabled", "autoupdate": False, "lsp": False, "formatter": False, "mcp": {},
    }


def parse_events(stdout):
    """`opencode run --format json` stdout -> (list of assistant text parts, list of tool uses {tool, input, status}, error text or '')."""
    texts, uses, err = [], [], ""
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        part = e.get("part") or {}
        if e.get("type") == "text" and part.get("text"):
            texts.append(part["text"])
        elif e.get("type") == "tool_use":
            st = part.get("state") or {}
            uses.append({"tool": part.get("tool"), "input": st.get("input"), "status": st.get("status")})
        elif e.get("type") == "error":
            err = json.dumps(e.get("error") or e)[:500]
    return texts, uses, err


def extract_answer(texts):
    """Last <answer>..</answer> in the assistant text (an unclosed one counts), else None."""
    for t in reversed(texts):
        ms = _ANS.findall(t)
        if ms:
            return T.clean_answer(ms[-1])
        m = _ANS_OPEN.search(t)
        if m:
            return T.clean_answer(m.group(1))
    return None


class OpenCodeHarness:
    def __init__(self, proxy_url="http://127.0.0.1:8095", log_dir=None, upstream=None, concurrency=4, timeout=900, max_new=1024, temperature=0.7,
                 max_steps=12, bash_timeout_ms=10000, web=True, opencode_bin="opencode", log=print, keep_dirs=False, embed_tools=True, progress_s=120):
        self.proxy = None
        if proxy_url is None:  # in-process proxy
            self.proxy = Proxy(upstream, log_dir or tempfile.mkdtemp(prefix="k2proxy_"))
            proxy_url = f"http://127.0.0.1:{self.proxy.start_thread(0)}"
            log_dir = str(self.proxy.log_dir)
        if log_dir is None:
            raise ValueError("log_dir must be the directory the proxy writes its logs to")
        log_dir = os.path.expanduser(str(log_dir))
        self.base_url = proxy_url.rstrip("/") + ("" if proxy_url.rstrip("/").endswith("/v1") else "/v1")
        self.log_dir, self.concurrency, self.timeout = log_dir, concurrency, timeout
        self.max_new, self.temperature, self.max_steps, self.bash_timeout_ms = max_new, temperature, max_steps, bash_timeout_ms
        self.web, self.bin, self.log, self.keep_dirs, self.embed_tools, self.progress_s = web, opencode_bin, log, keep_dirs, embed_tools, progress_s
        self.stats = {"gen_s": 0.0, "tool_s": 0.0, "gen_tokens": 0, "rollouts": 0, "timeouts": 0, "errors": 0}
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- one try
    def run_one(self, p, k, label=""):
        t0 = time.time()
        key = safe_key(f"{label}-{p['id']}-t{k}-{uuid.uuid4().hex[:6]}")
        work = tempfile.mkdtemp(prefix="oc_")
        cfg = make_config(self.base_url, self.max_new, self.temperature, self.max_steps, headers={"X-Practice-Try": key})
        env = dict(os.environ, OPENCODE_CONFIG_CONTENT=json.dumps(cfg), XDG_CONFIG_HOME=os.path.join(work, ".xdg_cfg"), PWD=work,
                   OPENCODE_DISABLE_MODELS_FETCH="1", OPENCODE_DISABLE_AUTOUPDATE="1", OPENCODE_DISABLE_AUTOCOMPACT="1", OPENCODE_DISABLE_CLAUDE_CODE="1",
                   OPENCODE_DISABLE_LSP_DOWNLOAD="1", OPENCODE_DISABLE_DEFAULT_PLUGINS="1", OPENCODE_DISABLE_TERMINAL_TITLE="1",
                   OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS=str(self.bash_timeout_ms))
        if self.web:
            env["OPENCODE_ENABLE_EXA"] = "1"
        end, stdout, err = "", "", ""
        proc = None
        try:
            proc = subprocess.Popen([self.bin, "run", "--agent", "practice", "--format", "json", "--title", f"{p['id']}"], cwd=work, env=env, text=True,
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            try:
                stdout, stderr = proc.communicate(T.user_prompt(p), timeout=self.timeout)  # the prompt goes through stdin: argv would add quotes around it
                if proc.returncode:
                    end, err = "error", (stderr or "")[-500:]
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                stdout, stderr = proc.communicate()
                end = "timeout"
        except Exception as e:  # noqa: BLE001
            end, err = "error", str(e)
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
        finally:
            if not self.keep_dirs:
                shutil.rmtree(work, ignore_errors=True)
        texts, uses, perr = parse_events(stdout)
        calls = read_try_log(self.log_dir, key)
        rec = self._record(p, k, key, calls, texts, uses, end, err or perr, t0)
        with self._lock:
            self.stats["rollouts"] += 1
            self.stats["gen_s"] += sum(c.get("latency_s", 0) for c in calls)
            self.stats["gen_tokens"] += rec["gen_tokens"]
            self.stats["timeouts"] += rec["end"] == "timeout"
            self.stats["errors"] += rec["end"] == "error"
        return rec

    def _record(self, p, k, key, calls, texts, uses, end, err, t0):
        ans = extract_answer(texts)
        if ans is None and calls:  # answer given without a closing tag / in the last call's text
            ans = extract_answer([calls[-1]["completion_text"]])
        answered = ans is not None
        if ans is None:
            for t in reversed(texts):
                ans = T.last_answer_line(t)
                if ans is not None:
                    break
        names = [c_["name"] for c in calls for c_ in c.get("tool_calls", [])]
        msgs = list(calls[-1]["request_messages"]) + [calls[-1].get("response_message") or {"role": "assistant", "content": calls[-1]["completion_text"]}] if calls else []
        if not end:
            end = "answer" if answered else ("no_calls" if not calls else "no_answer")
        gen = sum(((c.get("usage") or {}).get("completion_tokens") or len(c["completion_text"]) // 3) for c in calls)
        rec = {"id": p["id"], "try": k, "kind": p.get("kind"), "source": p.get("source"), "messages": msgs, "tool_calls": len(names), "tools": names,
               "turns": len(calls), "answer": ans, "answered": answered, "correct": bool(check(p, ans)), "gen_tokens": gen,
               "web": [{"tool": u["tool"], "input": u["input"], "status": u["status"]} for u in uses if u["tool"] in ("webfetch", "websearch")],
               "end": end, "seconds": round(time.time() - t0, 1), "harness": "opencode", "try_key": key,
               "proxy_calls": [{"request_messages": c["request_messages"], "tools_hash": c.get("tools_hash"), "completion_text": c["completion_text"]} for c in calls]}
        if err:
            rec["error"] = err
        if self.embed_tools:
            rec["proxy_tools"] = {c["tools_hash"]: c["tools"] for c in calls if c.get("tools_hash")}
        return rec

    # ---------------------------------------------------------------- many tries
    def run(self, puzzles, tries, seed=0, deadline=None, inflight=None, on_done=None, label=""):
        """Same contract as Harness.run: try 0 of every puzzle, then try 1 ...; returns the records; on_done(rec) is called in the calling thread."""
        rng = random.Random(seed)
        queue = []
        for k in range(tries):
            order = list(puzzles)
            rng.shuffle(order)
            queue += [(p, k) for p in order]
        n = max(1, inflight or self.concurrency)
        total, recs, life, running = len(queue), [], [], {}
        t_start = last = time.time()
        with ThreadPoolExecutor(n) as pool:
            while queue or running:
                while queue and len(running) < n:
                    if deadline and life and time.time() + 1.5 * max(life) > deadline:
                        self.log(f"{label}: deadline near, {len(queue)} tries not started")
                        queue = []
                        break
                    p, k = queue.pop(0)
                    running[pool.submit(self.run_one, p, k, label)] = time.time()
                if not running:
                    break
                done, _ = wait(list(running), timeout=5, return_when=FIRST_COMPLETED)
                for f in done:
                    life.append(time.time() - running.pop(f))
                    rec = f.result()
                    recs.append(rec)
                    if on_done:
                        on_done(rec)
                if deadline and time.time() > deadline and running:
                    self.log(f"{label}: deadline reached, {len(running)} unfinished tries are not waited for")
                    for f in running:
                        f.cancel()
                    break
                if time.time() - last >= self.progress_s:
                    last = time.time()
                    gs = max(1e-9, self.stats["gen_s"])
                    self.log(f"{label}: tries {len(recs)}/{total} done, {len(running)} running, {len(queue)} queued, {(time.time() - t_start) / 60:.1f} min, "
                             f"{self.stats['gen_tokens'] / gs:.1f} generated tok/s per stream, {self.stats['timeouts']} timeouts, {self.stats['errors']} errors")
        return recs
