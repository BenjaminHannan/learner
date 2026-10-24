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

    def add(self, model, u):
        pi, po = PRICE[model]
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
    m = re.search(r"\{.*\}", text, re.S)
    try:
        d = json.loads(m.group(0))
        return max(0, min(10, int(d["score"]))), str(d.get("critique", ""))[:400]
    except Exception:
        m = re.search(r'"score"\s*:\s*(\d+)', text)
        return (max(0, min(10, int(m.group(1)))), "") if m else (None, "")


class Grader:
    def __init__(self, outdir, max_usd=30.0, fake=False, spot=0.05, seed=0, workers=8):
        self.fake, self.spot, self.workers, self.outdir = fake, spot, workers, outdir
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
        if spot:
            o, _ = parse_grade(call_claude(self.client, self.ledger, OPUS, GRADER_SYSTEM, user))
            if s is not None and o is not None:
                self.pairs.append((s, o))
                with open(os.path.join(self.outdir, "spot.jsonl"), "a") as f:
                    f.write(json.dumps({"id": task["id"], "sonnet": s, "opus": o}) + "\n")
        return (0 if s is None else s), crit

    def grade_many(self, items):
        """items: list of (task, messages). Concurrent. Returns list of (score, critique)."""
        flags = [self.rng.random() < self.spot for _ in items]
        with ThreadPoolExecutor(self.workers) as ex:
            return list(ex.map(lambda a: self.grade_one(a[0][0], a[0][1], a[1]), zip(items, flags)))

    def spot_agreement(self):
        return sum(abs(a - b) <= 2 for a, b in self.pairs) / len(self.pairs) if self.pairs else None
