"""Claude as grader: Sonnet 5.5 scores a transcript 0-10 against a rubric. Spend ledger with hard stop."""
import json, os, random, re, threading, time
from concurrent.futures import ThreadPoolExecutor

SONNET, OPUS = "claude-sonnet-5-5", "claude-opus-5-5"
PRICE = {SONNET: (2.0, 10.0), OPUS: (4.0, 20.0)}  # USD per million tokens (list prices, Oct 2026): input, output
# Sonnet 5.5 thinks by default and rejects thinking=disabled; between_tools keeps it off. Opus 5.5 cannot turn thinking off, so it runs at low effort with room to think.
THINK = {SONNET: dict(thinking={"type": "between_tools"}), OPUS: dict(output_config={"effort": "low"})}

GRADER_SYSTEM = """You are a strict, fair grader of an AI assistant's work. The assistant is a small model that controls a sandboxed
personal-assistant world (files, email, calendar, notes, reminders) through tools. You are shown the user's request, a grading rubric
written by the task author, and the full transcript: assistant messages, the tool calls it made, and the tool results.

Grade the whole episode from 0 to 10:
- 10: fully does what the user asked, correct details (names, dates, times, addresses), sensible tool use, concise accurate final reply.
- 7-9: achieves the goal with minor flaws (extra needless steps, slightly vague reply, small wording issues).
- 4-6: partly achieves the goal, or achieves it with a real mistake (wrong detail, missed one part of the request, claims something it did not do).
- 1-3: mostly fails: wrong action, ignores the request, hallucinated results, malformed or repeated tool calls that never work.
- 0: nothing useful: empty reply, no attempt, or harmful action (e.g. sending an email the user did not ask to send, deleting or overwriting data).
Rules: judge only what is in the transcript. A reply that claims success without the matching tool call is a failure. Asking a clarifying
question is correct only when the request is genuinely ambiguous or irreversible and unconfirmed (see rubric). Do not reward length.
Respond with ONLY a JSON object on one line: {"score": <integer 0-10>, "critique": "<one sentence: the most important thing the assistant got wrong or could do better; if nothing, say so>"}"""


def format_transcript(messages):
    """messages: list of {role, content, tool_calls?}. Hidden system/privileged blocks are never included."""
    out = []
    for m in messages:
        if m["role"] == "system":
            continue
        out.append(f"[{m['role']}] {m['content']}".strip())
    return "\n".join(out) if out else "(empty)"


class Ledger:
    def __init__(self, outdir, max_usd):
        self.path, self.max_usd, self.lock = os.path.join(outdir, "spend.json"), max_usd, threading.Lock()
        os.makedirs(outdir, exist_ok=True)
        self.d = json.load(open(self.path)) if os.path.exists(self.path) else {"usd": 0.0, "calls": 0, "by_model": {}}

    def add(self, model, u, batch=False):
        pi, po = PRICE[model]
        if batch:   # Message Batches API bills at half price
            pi, po = pi / 2, po / 2
        cr, cw = getattr(u, "cache_read_input_tokens", 0) or 0, getattr(u, "cache_creation_input_tokens", 0) or 0
        usd = (u.input_tokens * pi + cw * pi * 1.25 + cr * pi * 0.1 + u.output_tokens * po) / 1e6
        with self.lock:
            self.d["usd"] += usd
            self.d["calls"] += 1
            m = self.d["by_model"].setdefault(model, {"calls": 0, "usd": 0.0, "in": 0, "out": 0, "cache_read": 0, "cache_write": 0})
            m["calls"] += 1; m["usd"] += usd; m["in"] += u.input_tokens; m["out"] += u.output_tokens; m["cache_read"] += cr; m["cache_write"] += cw
            json.dump(self.d, open(self.path, "w"), indent=1)
        return usd

    @property
    def usd(self):
        return self.d["usd"]

    def bump(self, key):
        with self.lock:
            self.d[key] = self.d.get(key, 0) + 1
            json.dump(self.d, open(self.path, "w"), indent=1)

    def check(self):
        if self.d["usd"] >= self.max_usd:
            raise RuntimeError(f"spend cap reached: ${self.d['usd']:.2f} >= ${self.max_usd}")


def make_client():
    import anthropic
    return anthropic.Anthropic(api_key=os.environ["LEARNER_ANTHROPIC_API_KEY"], max_retries=0)


def call_claude(client, ledger, model, system, user, max_tokens=800, tries=8):
    """One message call with prompt-cached system block, 429/5xx backoff, spend accounting. Returns text."""
    import anthropic
    for i in range(tries):
        ledger.check()
        try:
            r = client.messages.create(model=model, max_tokens=max_tokens if model == SONNET else max(max_tokens, 4000), **THINK[model],
                                       system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                                       messages=[{"role": "user", "content": user}])
            ledger.add(model, r.usage)
            return "".join(b.text for b in r.content if b.type == "text")
        except (anthropic.RateLimitError, anthropic.APIConnectionError) as e:
            err = e
        except anthropic.APIStatusError as e:
            if e.status_code < 500 and e.status_code != 429:
                raise
            err = e
        time.sleep(min(60, 2 ** i + random.random()))
    raise err


def parse_grade(text):
    """Last JSON object with a numeric score wins (an earlier one can be a draft); None if there is none."""
    for m in reversed(list(re.finditer(r"\{[^{}]*\}", text or ""))):
        try:
            d = json.loads(m.group(0))
            return max(0, min(10, int(float(d["score"])))), str(d.get("critique", ""))[:400]
        except Exception:
            continue
    m = list(re.finditer(r'"score"\s*:\s*(\d+(?:\.\d+)?)', text or ""))
    return (max(0, min(10, int(float(m[-1].group(1))))), "") if m else (None, "")


NEUTRAL = 5   # score used when a grade still fails to parse after a retry, so a good rollout is not punished as a 0


class Grader:
    def __init__(self, outdir, max_usd=30.0, fake=False, spot=0.05, seed=0, workers=8, batch=True, batch_timeout_s=1800):
        self.fake, self.spot, self.workers, self.outdir = fake, spot, workers, outdir
        self.batch, self.batch_timeout_s = batch, batch_timeout_s   # Ben's rule (2026-10-25): Claude API calls go through Message Batches
        self.rng, self.ledger = random.Random(seed), Ledger(outdir, max_usd)
        self.client = None if fake else make_client()
        self.n_calls, self.pairs = 0, []

    def _user(self, task, messages):
        return f"TASK (user request): {task['user']}\n\nRUBRIC: {task['rubric']}\n\nTRANSCRIPT:\n{format_transcript(messages)}"

    def grade_one(self, task, messages, spot=False):
        """-> (score 0-10, critique). Failed parses score 0 (counted as a bad answer, not retried)."""
        if self.fake:
            self.n_calls += 1
            return self.rng.randint(0, 10), "fake critique: be more careful."
        self.n_calls += 1
        user = self._user(task, messages)
        s, crit = parse_grade(call_claude(self.client, self.ledger, SONNET, GRADER_SYSTEM, user))
        if s is None:   # one retry, then neutral; counted in spend.json
            self.ledger.bump("parse_retry")
            s, crit = parse_grade(call_claude(self.client, self.ledger, SONNET, GRADER_SYSTEM, user))
            if s is None:
                self.ledger.bump("parse_fail")
        if spot:
            o, _ = parse_grade(call_claude(self.client, self.ledger, OPUS, GRADER_SYSTEM, user))
            if s is not None and o is not None:
                self.pairs.append((s, o))
                with open(os.path.join(self.outdir, "spot.jsonl"), "a") as f:
                    f.write(json.dumps({"id": task["id"], "sonnet": s, "opus": o}) + "\n")
        return (NEUTRAL if s is None else s), crit

    def _batch_grade(self, items, flags):
        """One Message Batch per training step: a Sonnet request per item plus Opus for the spot slice. None if it times out."""
        def params(model, user):
            return dict(model=model, max_tokens=800 if model == SONNET else 4000, **THINK[model],
                        system=[{"type": "text", "text": GRADER_SYSTEM, "cache_control": {"type": "ephemeral"}}],
                        messages=[{"role": "user", "content": user}])
        self.ledger.check()
        users = [self._user(t, m) for t, m in items]
        reqs = [{"custom_id": f"s{i}", "params": params(SONNET, u)} for i, u in enumerate(users)]
        reqs += [{"custom_id": f"o{i}", "params": params(OPUS, u)} for i, (u, f) in enumerate(zip(users, flags)) if f]
        b = self.client.messages.batches.create(requests=reqs)
        t0 = time.time()
        while self.client.messages.batches.retrieve(b.id).processing_status != "ended":
            if time.time() - t0 > self.batch_timeout_s:
                self.client.messages.batches.cancel(b.id)
                print(f"grader: batch {b.id} not done in {self.batch_timeout_s}s; cancelled, grading this step directly", flush=True)
                return None
            time.sleep(10)
        out = {}
        for r in self.client.messages.batches.results(b.id):   # results arrive in any order: key by custom_id
            if r.result.type == "succeeded":
                m = r.result.message
                self.ledger.add(m.model if m.model in PRICE else (SONNET if r.custom_id[0] == "s" else OPUS), m.usage, batch=True)
                out[r.custom_id] = parse_grade("".join(c.text for c in m.content if c.type == "text"))
        self.n_calls += len(reqs)
        res = []
        for i, (t, _) in enumerate(items):
            s, crit = out.get(f"s{i}", (None, ""))
            if f"o{i}" in out and s is not None and out[f"o{i}"][0] is not None:
                self.pairs.append((s, out[f"o{i}"][0]))
                with open(os.path.join(self.outdir, "spot.jsonl"), "a") as f:
                    f.write(json.dumps({"id": t["id"], "sonnet": s, "opus": out[f"o{i}"][0]}) + "\n")
            res.append((s, crit) if s is not None else self.grade_one(t, items[i][1]))   # unparsed or failed in the batch: live retry path
        return res

    def grade_many(self, items):
        """items: list of (task, messages). Message Batches by default (half price), direct concurrent calls as fallback. Returns list of (score, critique)."""
        flags = [self.rng.random() < self.spot for _ in items]
        if self.batch and not self.fake and items:
            res = self._batch_grade(items, flags)
            if res is not None:
                return res
        with ThreadPoolExecutor(self.workers) as ex:
            return list(ex.map(lambda a: self.grade_one(a[0][0], a[0][1], a[1]), zip(items, flags)))

    def spot_agreement(self):
        return sum(abs(a - b) <= 2 for a, b in self.pairs) / len(self.pairs) if self.pairs else None
