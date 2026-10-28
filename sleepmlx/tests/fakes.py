"""A fake model for the tests: deterministic, learns (name pairs) from training examples, and advances a fake clock."""
from __future__ import annotations

import json
import re
from pathlib import Path

from sleepmlx import gate as gate_mod
from sleepmlx.backend import Backend

CAP = re.compile(r"\b[A-Z][a-z]{2,}\b")
NOT_NAMES = {"Where", "Who", "Which", "What", "Ben", "Answer", "Question", "Day", "Notes", "Messages", "Two", "Write", "Reply", "Focus", "Each",
             "The", "Message", "List", "Does", "That", "Use", "Cover", "Its", "Fact", "Earlier", "Some", "Remember", "Name"}
REL = r"(works at|lives in|is the mentor of|owns)"


def names(text):
    return [w for w in CAP.findall(text) if w not in NOT_NAMES]


class FakeTime:
    def __init__(self):
        self.t = 1000.0

    def now(self):
        return self.t


class FakeBackend(Backend):
    gen_batch = 4
    stop_id = 0

    def __init__(self, clock: FakeTime = None, step_s=10.0, gen_s=0.5, damage=False, adapter_dir_marker=None):
        self.clock, self.step_s, self.gen_s = clock or FakeTime(), step_s, gen_s
        self.damage = damage            # after training, general questions come out wrong (to test the undo)
        self.known = {}                 # name -> partner name (what training taught)
        self.steps_seen = []
        self.prompts_trained = []
        self.calls = {"generate": 0}
        self.trained = False
        self.scale_calls = []
        self.downscaled = 0
        self.max_tokens_seen = []
        self.loaded = []
        self.opt_steps = 0

    # tokens: code points
    def encode(self, text):
        return [ord(c) for c in text]

    def dec(self, ids):
        return "".join(chr(i) for i in ids)

    def bench(self):
        return self.step_s, self.gen_s

    def train_begin(self, total_steps, lr):
        self.total = total_steps

    def train_step(self, batch, replay, step):
        self.clock.t += self.step_s
        self.steps_seen.append(step)
        self.trained = True
        for ids, ls in batch:
            prompt, ans = self.dec(ids[:ls]), self.dec(ids[ls:-1])
            self.prompts_trained.append(prompt + "|" + ans)
            if ls == 0:   # a paraphrase: every pair of names in it
                ns = names(ans)
                for a in ns:
                    for b in ns:
                        if a != b:
                            self.known.setdefault(a, b)
            else:
                m = re.findall(r"user\n(.*?)<\|ifm\|im_end\|>", prompt, re.S)
                q = m[-1] if m else prompt
                q = q.split("Question: ")[-1]
                for a in names(q):
                    self.known.setdefault(a, ans.strip())
        return {"ce": 1.0 / (1 + len(self.steps_seen))}

    def save_adapter(self, path):
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        (path / "adapters.safetensors").write_text(json.dumps({"known": self.known, "trained": self.trained, "steps": self.steps_seen}))
        (path / "adapter_config.json").write_text(json.dumps({"fine_tune_type": "lora"}))

    def load_adapter(self, path):
        self.loaded.append(str(path))
        if path is None or not Path(path).exists():
            self.known, self.trained = {}, False
            return
        d = json.loads((Path(path) / "adapters.safetensors").read_text())
        self.known, self.trained = d["known"], d["trained"]

    def downscale(self, factor, thresh, seed):
        self.downscaled += 1
        return {"modules": 1, "zeroed_frac": 0.0, "energy_ratio": factor ** 2}

    # ---- generation
    def generate(self, prompts, max_tokens, temp=0.0, adapter=True, stops=()):
        self.calls["generate"] += 1
        self.max_tokens_seen.append(max_tokens)
        self.clock.t += self.gen_s
        return [self.one(p, max_tokens, adapter) for p in prompts]

    def one(self, p, max_tokens, adapter):
        user = (re.findall(r"user\n(.*?)<\|ifm\|im_end\|>", p, re.S) or [p])[-1]
        thinking_open = p.rstrip().endswith("<ifm|think>")
        closed = p.rstrip().endswith("</ifm|think>") or "</ifm|think>" in p[-200:]
        if "List the facts this message states" in user:
            if thinking_open:
                return "Let me look for facts."
            msg = user.split('Message from Ben:\n"', 1)[1].split('"\n\nList', 1)[0]
            out = [{"subject": a, "relation": r, "object": b} for a, r, b in re.findall(r"([A-Z][a-z]+) " + REL + r" ([A-Z][a-z]+)", msg)]
            return json.dumps(out)
        if "Does this message say how" in user:
            if thinking_open:
                return "Thinking about the pair."
            return "no"
        if "paraphrases of the CURRENT fact" in user:
            a, b = re.search(r'linking "(.*?)" and "(.*?)"', user).groups()
            return json.dumps({"paraphrases": ["%s is connected with %s." % (a, b), "%s has to do with %s." % (b, a), "People know that %s and %s go together." % (a, b)],
                               "qa": [{"q": "What is %s tied to?" % a, "a": b}, {"q": "Who is tied to %s?" % b, "a": a},
                                      {"q": "Which name goes with %s?" % a, "a": b}, {"q": "Which name goes with %s?" % b, "a": a}]})
        if "Write one question that names" in user:
            if thinking_open:
                return "Thinking about the bridge."
            start = re.search(r'names "(.*?)", does not name', user).group(1)
            return "Who is two steps away from %s?" % start
        if "Write a short post-mortem" in user:
            chat = user.split("Something went wrong here:", 1)[1].split("Write a short post-mortem", 1)[0]
            lines = [l.strip() for l in chat.splitlines()]
            ben = [l for l in lines if " then said: " in l] or [l for l in lines if l.startswith("Ben: ")]
            glim = " ".join(l.split(": ", 1)[1] for l in lines if l.startswith("Glim: "))
            cands = names(ben[-1].split(": ", 1)[1]) if ben else []
            fresh = [n for n in cands if n not in glim] or cands
            wrongs = [n for n in names(glim) if n not in cands]
            if not fresh:
                return "{}"
            return json.dumps({"did": "Glim answered without checking", "wrong": "the answer did not match what Ben said",
                               "instead": "check what Ben said before answering", "wrong_value": wrongs[0] if wrongs else "",
                               "q": "What is the right answer here?", "a": fresh[0]})
        if "Write one question that this note answers" in user:
            note = user.split('A note saved about Ben:\n"', 1)[1].split('"\n\nWrite one', 1)[0]
            return json.dumps({"q": "What detail does the saved note give?", "a": note.split()[-1].strip(".,")})
        if "Fact about" in user:
            return "Question: Where does Ben go?\nAnswer: nowhere"
        if "Question: " in user and ("Messages from" in user):
            ctx = user.split("Messages from", 1)[1]
            return "It is " + " ".join(dict.fromkeys(names(ctx.split("Question:")[0])))
        # quiz prompts
        for q, acc in gate_mod.GENERAL_QA:
            if q in user:
                return "wrong" if (self.damage and self.trained and adapter) else acc[0]
        if adapter:
            for n in names(user):
                if n in self.known:
                    return self.known[n]
        return "I do not know"


def factory(prof):
    return FakeBackend(), None
