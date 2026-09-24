#!/usr/bin/env python3
"""333 creative v1 (month-end line; plan design/v3/30-modes/330-month-end-plan.md section 5).

One change on a 292-lineage loop: install_creative333(loop, gen) wraps loop.turn. A turn that
asks for ideas or a short piece of writing (CREATIVE_CUES, fixed before any run) becomes a
WORK job with a creative phase and never reaches listening, so it can never write to the
notebook. Every other turn goes to the wrapped turn unchanged.

The creative phase (doc 54's registered KEEP_FIXED_N = 11):
  1. context = the notebook's active taught facts about the people and things the request
     names, the user's own facts, and one hop out from those (read-only).
  2. draw 11 candidates from the shared MiniCPM5-1B, prompted with the context as plain
     sentences and the request.
  3. drop candidates that name a capitalised person-like word found neither in the
     notebook, the request nor a small allow-list (invented people);
  4. pick the candidate that uses the most context values (grounding), ties -> shorter.
  5. reply = the pick. If every candidate is dropped: an honest fallback line.
Nothing produced here is saved. The job is logged in loop.experience as kind "work"
with phase "creative" and loop.counters["work"] += 1.

gen is any object with .sample(prompt: str, n: int) -> list[str]; Gen333 below loads the
base MiniCPM5-1B with transformers (bf16 on CUDA, float32 on CPU).
"""
from __future__ import annotations

import re

N_CANDIDATES = 11
CREATIVE_CUES = [
    r"\bideas?\b", r"\bsuggest", r"\brecommend (me |us )?(a|an|some|something)\b", r"\bwrite (me |us )?(a|an|some)\b",
    r"\bpoem\b", r"\bstory\b", r"\bhaiku\b", r"\bsong\b", r"\btoast\b", r"\bhelp me (plan|pick|think|come up|write|figure out what)",
    r"\bwhat should i (get|give|buy|make|cook|do|plan|write)\b", r"\bgift\b", r"\bpresent for\b",
    r"\bbrainstorm", r"\bcome up with\b", r"\bplan (a|an|the|my|our)\b",
]
FALLBACK = "I don't have a good idea for that yet. Tell me a bit more about what you'd like?"
ALLOW = {"I", "I'm", "I'd", "I'll", "I've", "Here", "Happy", "Maybe", "You", "Your", "Or", "And", "The", "A",
         "If", "For", "Some", "Try", "How", "What", "It", "This", "That", "Then", "Also", "Just", "Oh",
         "Hope", "Dear", "Love", "With", "Why", "When", "Plus", "Idea", "Ideas", "Option", "Saturday",
         "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "January", "February", "March",
         "April", "May", "June", "July", "August", "September", "October", "November", "December"}


def is_creative(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in CREATIVE_CUES)


def _facts(loop) -> list[tuple[str, str, str]]:
    import fable_loop90_agent as L90
    return list(L90.notebook_triples(loop.nb))


def context_facts(loop, text: str) -> list[tuple[str, str, str]]:
    facts = _facts(loop)
    low = text.lower()
    named = {s.lower() for s, _r, v in facts if s.lower() in low} | \
            {v.lower() for s, _r, v in facts if v.lower() in low}
    named |= {"user", "me"}
    keep = [f for f in facts if f[0].lower() in named or f[2].lower() in named]
    hop = {f[2].lower() for f in keep} | {f[0].lower() for f in keep}
    keep += [f for f in facts if f not in keep and f[0].lower() in hop]
    return keep[:40]


def _sentence(f: tuple[str, str, str]) -> str:
    s, r, v = f
    owner = "The user's" if s.lower() in ("user", "me") else f"{s}'s"
    return f"{owner} {r.replace('_', ' ')} is {v}."


def build_prompt(text: str, ctx: list[tuple[str, str, str]]) -> str:
    known = " ".join(_sentence(f) for f in ctx) or "Nothing yet."
    return ("You are a warm, creative personal assistant. What you know about the user: " + known +
            " Use only these facts about real people; do not invent new facts about them. "
            "The user asks: " + text + " Answer in 2 to 5 short sentences with concrete ideas.")


def pick(cands: list[str], text: str, ctx: list[tuple[str, str, str]]) -> str | None:
    known_words = {w for s, _r, v in ctx for w in re.findall(r"[A-Za-z']+", f"{s} {v}")}
    known_words |= set(re.findall(r"[A-Za-z']+", text))
    values = [v.lower() for _s, _r, v in ctx]
    best, best_key = None, None
    for c in cands:
        c = c.strip()
        if not c:
            continue
        caps = re.findall(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z]+)\b", c)
        if any(w not in known_words and w not in ALLOW for w in caps):
            continue                                     # names someone we were never told about
        key = (-sum(1 for v in values if v and v in c.lower()), len(c))
        if best_key is None or key < best_key:
            best, best_key = c, key
    return best


def install_creative333(loop, gen, n: int = N_CANDIDATES) -> None:
    inner = loop.turn
    loop.cre333_stats = {"creative_turns": 0, "fallbacks": 0, "passed_through": 0}

    def turn333(text: str) -> list[str]:
        if not is_creative(text):
            loop.cre333_stats["passed_through"] += 1
            return inner(text)
        ev0 = len(loop.nb.events)
        ctx = context_facts(loop, text)
        cands = gen.sample(build_prompt(text, ctx), n)
        reply = pick(cands, text, ctx)
        loop.cre333_stats["creative_turns"] += 1
        if reply is None:
            loop.cre333_stats["fallbacks"] += 1
            reply = FALLBACK
        loop.counters["work"] = loop.counters.get("work", 0) + 1
        loop.experience.append({"tick": loop.tick, "kind": "work", "phase": "creative",
                                "n": n, "context_facts": len(ctx)})
        loop._save()
        if len(loop.nb.events) != ev0:
            raise RuntimeError("333: creative turn wrote to the notebook")
        return [reply]

    turn333.__name__ = "turn333"
    loop.turn = turn333


class Gen333:
    def __init__(self, model_dir: str, max_new: int = 120, temperature: float = 0.9, top_p: float = 0.95):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16 if self.dev == "cuda" else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, torch_dtype=dtype,
                                                          trust_remote_code=True).to(self.dev).eval()
        self.max_new, self.t, self.p = max_new, temperature, top_p

    def sample(self, prompt: str, n: int) -> list[str]:
        if getattr(self.tok, "chat_template", None):
            prompt = self.tok.apply_chat_template([{"role": "user", "content": prompt}],
                                                  tokenize=False, add_generation_prompt=True)
        ids = self.tok(prompt, return_tensors="pt").to(self.dev)
        with self.torch.no_grad():
            out = self.model.generate(**ids, max_new_tokens=self.max_new, do_sample=True,
                                      temperature=self.t, top_p=self.p, num_return_sequences=n,
                                      pad_token_id=self.tok.eos_token_id)
        cut = ids["input_ids"].shape[1]
        return [self.tok.decode(o[cut:], skip_special_tokens=True).strip() for o in out]
