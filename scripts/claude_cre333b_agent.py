#!/usr/bin/env python3
"""333b and 333c: two single-change follow-ups to 333 creative v1 (month-end line, 2026-09-24).

Why: in the registered 333 run (rent-333b-creative) every creative turn P routed (38 of 70, 25 of them creative
items) got the fallback line. The reason is the same bug as the old twin: Gen333.sample renders the chat template
with MiniCPM5-1B's thinking mode on, so each of the 11 candidates starts with a <think> block that does not finish
inside 120 new tokens. Think text is full of capitalised words, so 333's invented-name filter dropped every
candidate. The DEV rehearsal showed the same thing (10/10 DEV creative turns got the fallback); it was missed there.

333b (one change: generation): Gen333b = Gen333 with enable_thinking=False; any leftover think text is cut.
333c (one change on 333b: routing): is_creative333c = 333's cue AND the turn is a request to the assistant AND
  it is not a recall question. In 333, 13 of 30 look-alike controls ("plan", "gift", "idea", "write" used in an
  ordinary fact or question) were routed to creative, so they were neither saved nor answered.

Both are swapped in by scripts/claude_cre333b_wrap.py (runner unchanged) or by the joiner (scripts/claude_e2e330c.py).
"""
from __future__ import annotations

import re

import claude_cre333_agent as C

_CUE333 = C.is_creative                              # 333's cue test, kept before any swap
THINK333B = re.compile(r"<think>.*?(</think>|$)", re.S)


class Gen333b(C.Gen333):
    def sample(self, prompt: str, n: int) -> list[str]:
        if getattr(self.tok, "chat_template", None):
            msgs = [{"role": "user", "content": prompt}]
            try:
                prompt = self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                                      enable_thinking=False)
            except TypeError:                              # a template without the switch
                prompt = self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ids = self.tok(prompt, return_tensors="pt").to(self.dev)
        with self.torch.no_grad():
            out = self.model.generate(**ids, max_new_tokens=self.max_new, do_sample=True,
                                      temperature=self.t, top_p=self.p, num_return_sequences=n,
                                      pad_token_id=self.tok.eos_token_id)
        cut = ids["input_ids"].shape[1]
        return [THINK333B.sub("", self.tok.decode(o[cut:], skip_special_tokens=True)).strip() for o in out]


# 333c: a creative cue only counts when the turn asks the assistant for something.
REQUEST333C = re.compile(
    r"\?|^\s*(ok(ay)?,? |so,? |hey,? |hi,? |please |pls )?(can|could|would|will) you\b"
    r"|^\s*(ok(ay)?,? |so,? |please |pls )?(write|give|help|suggest|recommend|brainstorm|come up|make|draft|"
    r"compose|plan|pick|list|think of|tell me|throw)\b"
    r"|\bhelp me\b|\bi need (some |a few |an? )?(ideas?|suggestions?|help|options)\b"
    r"|\bi'?m looking for (some )?(ideas?|suggestions?)\b|\bwhat should i\b|\bany (ideas?|suggestions?|thoughts)\b"
    r"|\bneed (some )?(ideas?|suggestions?|inspiration)\b|\bideas for\b")
RECALL333C = re.compile(r"\b(no idea|any idea (what|where|when|who|whose|if|how|why|which)|what did i|did i (tell|say|"
                        r"mention)|remind me|who (wrote|gave|planned|recommended)|whose (idea|gift|plan|story|song))\b")


def is_creative333c(text: str) -> bool:
    low = text.lower()
    return _CUE333(low) and REQUEST333C.search(low) is not None and RECALL333C.search(low) is None
