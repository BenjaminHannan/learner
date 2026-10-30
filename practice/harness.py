"""Batched multi-turn tool rollouts (HF generate or a vLLM backend, see gen.py). Many puzzle-tries in flight; each round generates one assistant turn for every active rollout
(left padding, the whole transcript is re-encoded each turn), then runs the tools (python calls in a small thread pool)."""
import random
import time
from concurrent.futures import ThreadPoolExecutor

from .gen import BsState, hf_generate as generate

from . import tools as T
from .web import WEB
from .grade import check

IM_START, IM_END = "<|ifm|im_start|>", "<|ifm|im_end|>"
THINK_EMPTY = "<ifm|think>\n</ifm|think>"
NUDGE = ("Reply with exactly one tool call: the tool name as a tag around its input, for example <python>print(1)</python> or <answer>42</answer>. "
         "Tools: python, search, look or answer.")
NUDGE_WEB = NUDGE.replace("look or answer", "look, fetch or answer")


def render(messages, add_gen=True, bos=""):
    """K2 thinking-off chat format (same as sleep2.askonce.world.render)."""
    out = [bos]
    for m in messages:
        if m["role"] == "assistant":
            out.append(f"{IM_START}assistant\n{THINK_EMPTY}{m['content']}{IM_END}")
        else:
            out.append(f"{IM_START}{m['role']}\n{m['content']}{IM_END}")
    if add_gen:
        out.append(f"{IM_START}assistant\n{THINK_EMPTY}")
    return "".join(out)


def cut_reply(text):
    """Keep only the first tool call: cut after its closing tag."""
    return T.cut_after_call(text)


def start_messages(p):
    return [{"role": "system", "content": T.system_prompt()}, {"role": "user", "content": T.user_prompt(p)}]


class Rollout:
    def __init__(self, puzzle, try_idx):
        self.p, self.try_idx = puzzle, try_idx
        self.messages = start_messages(puzzle)
        self.turns = self.calls = self.gen_tokens = 0
        self.names = []
        self.answer = None
        self.done = False
        self.reason = ""
        self.t0 = time.time()
        self.last_answer_line = None
        self.web = []

    def record(self):
        ans = self.answer if self.answer is not None else self.last_answer_line
        ok = check(self.p, ans)
        return {"id": self.p["id"], "try": self.try_idx, "kind": self.p.get("kind"), "source": self.p.get("source"), "messages": self.messages,
                "tool_calls": self.calls, "tools": self.names, "turns": self.turns, "answer": ans, "answered": self.answer is not None, "correct": bool(ok),
                "gen_tokens": self.gen_tokens, "web": self.web, "end": self.reason, "seconds": round(time.time() - self.t0, 1)}


class Harness:
    def __init__(self, model, tok, temperature=0.7, max_new=512, max_ctx=4096, bs=8, max_turns=T.MAX_TURNS, log=print, workers=4, backend=None, progress_s=120):
        self.model, self.tok, self.temp, self.max_new, self.max_ctx = model, tok, temperature, max_new, max_ctx
        self.bs, self.max_turns, self.log = bs, max_turns, log
        self.backend = backend            # None = HF generate on self.model with the sticky batch size below
        self.bs_state = BsState(bs)
        self.progress_s, self._last_progress = progress_s, time.time()
        self.pool = ThreadPoolExecutor(workers)
        self.rounds = 0
        self.stats = {"gen_s": 0.0, "tool_s": 0.0, "gen_tokens": 0, "rollouts": 0}

    def _ctx_len(self, r):
        return len(self.tok(render(r.messages, True, self.tok.bos_token or ""), add_special_tokens=False).input_ids)

    def _step(self, active, seed):
        """One assistant turn for every active rollout, then tool execution."""
        keep = []
        for r in active:
            if r.turns >= self.max_turns:
                r.done, r.reason = True, "max_turns"
            elif self._ctx_len(r) + self.max_new > self.max_ctx:
                r.done, r.reason = True, "context_cap"
            else:
                keep.append(r)
        if not keep:
            return
        prompts = [render(r.messages, True, self.tok.bos_token or "") for r in keep]
        t = time.time()
        if self.backend is not None:
            outs = self.backend.generate(prompts, self.max_new, self.temp, seed)
        else:
            outs = generate(self.model, self.tok, prompts, self.max_new, self.temp, seed, self.bs_state, self.log)
        self.stats["gen_s"] += time.time() - t
        jobs = []
        for r, o in zip(keep, outs):
            o = cut_reply(o.strip("\n") if o.strip() else o)
            n_tok = len(self.tok(o, add_special_tokens=False).input_ids) + 1
            r.gen_tokens += n_tok
            self.stats["gen_tokens"] += n_tok
            r.turns += 1
            r.messages.append({"role": "assistant", "content": o})
            la = T.last_answer_line(o)
            if la is not None:
                r.last_answer_line = la
            call = T.parse_call(o)
            if call is None:
                r.messages.append({"role": "user", "content": NUDGE_WEB if WEB.enabled else NUDGE})
                continue
            name, inp = call
            r.calls += 1
            r.names.append(name)
            if name == "answer":
                r.answer, r.done, r.reason = inp, True, "answer"
            else:
                jobs.append((r, name, inp))
        t = time.time()
        futs = [(r, name, self.pool.submit(T.run_tool_ev, name, inp)) for r, name, inp in jobs]
        for r, name, f in futs:
            try:
                obs, ev = f.result()
                r.web += ev
            except Exception as e:  # noqa: BLE001
                obs = f"[tool error: {e}]"
            r.messages.append({"role": "user", "content": f"Tool output ({name}):\n{obs}"})
        self.stats["tool_s"] += time.time() - t

    def run(self, puzzles, tries, seed=0, deadline=None, inflight=None, on_done=None, label=""):
        """Run `tries` rollouts per puzzle. Order: try 0 of every puzzle, then try 1 ... (so a deadline cuts evenly). With `deadline` (epoch seconds) no new
        rollout starts when the estimated remaining time of a rollout would pass it; rollouts still running at the deadline are dropped.
        Returns the list of per-try records of finished rollouts."""
        rng = random.Random(seed)
        queue = []
        for k in range(tries):
            order = list(puzzles)
            rng.shuffle(order)
            queue += [(p, k) for p in order]
        inflight = inflight or (getattr(self.backend, "inflight", 0) if self.backend is not None else self.bs * 2)
        active, recs, life = [], [], []
        total = len(queue)
        t_start = time.time()
        while queue or active:
            while queue and len(active) < inflight:
                if deadline and life and time.time() + 1.5 * max(life) > deadline:
                    self.log(f"{label}: deadline near, {len(queue)} tries not started")
                    queue = []
                    break
                p, k = queue.pop(0)
                active.append(Rollout(p, k))
            if not active:
                break
            if deadline and time.time() > deadline:
                self.log(f"{label}: deadline reached, dropping {len(active)} unfinished rollouts")
                break
            self._step(active, seed * 1000 + self.rounds)
            self.rounds += 1
            still = []
            for r in active:
                if r.done:
                    rec = r.record()
                    recs.append(rec)
                    life.append(time.time() - r.t0)
                    self.stats["rollouts"] += 1
                    if on_done:
                        on_done(rec)
                else:
                    still.append(r)
            active = still
            if time.time() - self._last_progress >= self.progress_s:
                self._last_progress = time.time()
                self.progress(label, len(recs), total, len(active), len(queue), t_start)
        return recs


def _progress(self, label, done, total, active, queued, t_start):
    gs = max(1e-9, self.stats["gen_s"])
    desc = self.backend.describe() if self.backend is not None else self.bs_state.describe()
    self.log(f"{label}: tries {done}/{total} done, {active} active, {queued} queued, {(time.time() - t_start) / 60:.1f} min, "
             f"{self.stats['gen_tokens'] / gs:.1f} generated tok/s (gen {self.stats['gen_s']:.0f}s, tools {self.stats['tool_s']:.0f}s), {desc}")


Harness.progress = _progress


def summarize(recs):
    n = max(1, len(recs))
    by = {}
    for r in recs:
        by.setdefault(r["kind"], []).append(r["correct"])
    return {"n": len(recs), "acc": round(sum(r["correct"] for r in recs) / n, 4), "tool_calls_per_try": round(sum(r["tool_calls"] for r in recs) / n, 3),
            "answered": round(sum(r["answered"] for r in recs) / n, 3), "gen_tokens_per_try": round(sum(r["gen_tokens"] for r in recs) / n, 1),
            "by_kind": {k: round(sum(v) / len(v), 3) for k, v in sorted(by.items(), key=lambda kv: str(kv[0]))}}
