#!/usr/bin/env python3
"""mu-403 draft: grounded pick ("Making things up about you" thread, 2026-09-26). NOT registered yet; the pilot
(scripts/claude_mu403_pilot.py) decides whether this is worth a registered test. New file only.

Idea: chat 338b and creative 333d draw 4 samples from the 1B and keep the first that passes their guards. The
guards catch invented names and numbers, not a reply that assumes the user's feelings, plans or situation, which is
what most of 0.2c's made-up claims were. The grounded pick keeps everything the same except the ORDER of the
samples: the 1B itself answers, for each sample, "does this reply claim or assume something about the user that
they did not write?", and the samples are handed back least-likely-yes first. The guards then take the first that
passes, as before. Nothing is removed, so a turn never loses a reply it would have had.

  GroundScorer(one_b).margins(msgs, cands) -> logit(yes) - logit(no) per candidate (lower = more grounded)
  GroundedGen(gen, scorer)                 -> stands in for Gen338: .sample_chat returns the samples sorted
"""
from __future__ import annotations

import math
import re

CHECK_Q = ("Question: Does the reply claim or assume something about the user that the user did not write (for "
           "example their feelings, plans, situation, past, or the people in their life)? Answer only yes or no.")
MAX_USER_LINES = 6


def user_lines(msgs: list[dict]) -> list[str]:
    return [m["content"] for m in msgs if m.get("role") == "user"][-MAX_USER_LINES:]


def facts_line(msgs: list[dict]) -> str:
    sysm = next((m["content"] for m in msgs if m.get("role") == "system"), "")
    m = re.search(r"Facts the user has told you: (.*)$", sysm)
    return m.group(1).strip() if m else ""


def check_prompt(msgs: list[dict], reply: str) -> str:
    lines = "\n".join(f"- {u}" for u in user_lines(msgs)) or "- (nothing)"
    facts = facts_line(msgs)
    extra = f"\nFacts the user told earlier: {facts}\n" if facts else ""
    return (f"Read what a user wrote, then a reply to them.\n\nWhat the user wrote:\n{lines}\n{extra}\n"
            f"Reply:\n\"{reply}\"\n\n{CHECK_Q}")


class GroundScorer:
    def __init__(self, one_b):
        self.g = one_b
        tok = one_b.tok
        self.yes = sorted({tok.encode(w, add_special_tokens=False)[0] for w in ("yes", "Yes", " yes", " Yes")})
        self.no = sorted({tok.encode(w, add_special_tokens=False)[0] for w in ("no", "No", " no", " No")})

    def _render(self, content: str) -> str:
        tok = self.g.tok
        msgs = [{"role": "user", "content": content}]
        try:
            return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        except TypeError:
            return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    def margins(self, msgs: list[dict], cands: list[str]) -> list[float]:
        g = self.g
        out = []
        for c in cands:
            ids = g.tok(self._render(check_prompt(msgs, c)), return_tensors="pt").to(g.dev)
            with g.torch.no_grad():
                logits = g.model(**ids).logits[0, -1].float()
            ly = float(g.torch.logsumexp(logits[self.yes], 0))
            ln = float(g.torch.logsumexp(logits[self.no], 0))
            out.append(ly - ln if math.isfinite(ly - ln) else 0.0)
        return out


class GroundedGen:
    """Gen338 stand-in: same samples, returned least-likely-made-up first (stable for ties)."""

    def __init__(self, gen, scorer):
        self.gen, self.scorer = gen, scorer
        self.stats = {"calls": 0, "reordered": 0}

    def sample_chat(self, msgs: list[dict], n: int) -> list[str]:
        cands = self.gen.sample_chat(msgs, n)
        self.stats["calls"] += 1
        if len(cands) < 2:
            return cands
        m = self.scorer.margins(msgs, cands)
        order = sorted(range(len(cands)), key=lambda i: (m[i], i))
        if order != list(range(len(cands))):
            self.stats["reordered"] += 1
        return [cands[i] for i in order]


def selftest() -> None:
    ok = 0
    msgs = [{"role": "system", "content": "Be nice. Facts the user has told you: The user's dog is Pip."},
            {"role": "user", "content": "hi"}, {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "ugh stressed"}]
    assert user_lines(msgs) == ["hi", "ugh stressed"]; ok += 1
    assert facts_line(msgs) == "The user's dog is Pip."; ok += 1
    p = check_prompt(msgs, "Sorry your exam went badly.")
    assert "- ugh stressed" in p and "Pip" in p and p.endswith("yes or no."); ok += 1

    class FakeScorer:
        def margins(self, msgs, cands):
            return [len(c) for c in cands]

    class FakeGen:
        def sample_chat(self, msgs, n):
            return ["long reply here", "short", "mid reply"]

    gg = GroundedGen(FakeGen(), FakeScorer())
    assert gg.sample_chat(msgs, 3) == ["short", "mid reply", "long reply here"]; ok += 1
    assert gg.stats == {"calls": 1, "reordered": 1}; ok += 1
    print(f"mu403 ground selftest {ok}/5 ok")


if __name__ == "__main__":
    selftest()
