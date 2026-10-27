#!/usr/bin/env python3
"""336 plain twin, fixed (twin b). One change from scripts/claude_e2e336_twin.py: the chat template
is rendered with enable_thinking=False, the same setting Premonition's own 1B chat (338) and
creative (333) calls use, and any leftover <think>...</think> text is cut from the reply.

Why: in the 338 registered run all 400 of the old twin's replies started with a <think> block, and
201 of them never closed inside its 160-token budget, so the user got no answer (blind judge,
2026-09-24). That handicapped the twin; every comparison against it was easier than intended.
Everything else (system line, whole chat in the prompt, greedy, 160 new tokens, history file) is
identical, so twin b is the fair baseline. New file only.

Use: build(state_dir, args) like the old twin, or run any runner through scripts/claude_twinb_wrap.py,
which swaps this class in wherever a runner imports claude_e2e336_twin.
"""
from __future__ import annotations

import re

import claude_e2e336_twin as OLD

THINK_B = re.compile(r"<think>.*?(</think>|$)", re.S)


class Twin336b(OLD.Twin336):
    def _prompt(self) -> str:
        msgs = [{"role": "system", "content": OLD.SYSTEM}] + self.history
        if getattr(self.tok, "chat_template", None):
            try:
                return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                                    enable_thinking=False)
            except TypeError:                              # a template without the switch
                return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        return super()._prompt()

    def turn(self, text: str) -> list[str]:
        out = super().turn(text)
        reply = THINK_B.sub("", out[0]).strip()
        if reply != out[0]:
            self.history[-1]["content"] = reply
            self.path.write_text(OLD.json.dumps(self.history, ensure_ascii=False), encoding="utf-8")
        return [reply]


def build(state_dir: str, args) -> Twin336b:
    return Twin336b(state_dir, getattr(args, "model", ""))
