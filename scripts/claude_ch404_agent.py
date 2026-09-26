#!/usr/bin/env python3
"""ch-404 candidate: the chat layer's length limit (everyday-chat thread, 2026-09-26). New file only; one change on
ch-403's X403 (scripts/claude_ch403_agent.py:build_403). DEV probe first (report only, in the ch-403 rental after
its registered panel); a registered run only on a fresh sealed panel with its own pass marks.

Why (artifacts/claude-ch403-20260926/DIAG.md section 2, counts only): in 0.2c's C1 the plain twin's winning reasons
name helpfulness (help, useful, specific, concrete, advice ...) in 16 of 30, X's in 4 of 30; median words per reply
X vs T: advice 53 vs 118, explain 46 vs 120, followup 40 vs 116. Checked in the code: 338's chat phase asks the 1B
for "1 to 4 sentences" (SYSTEM338) and rejects any sample over 90 words (guard G4, MAX_WORDS338); the twin has a
160-token budget and "Keep replies short" (claude_e2e336_twin.py). Route 383 raised the same limit for questions
(WORDS383 = 350) after Benchmarks found G4 rejected most worked answers.

What: while the chat layer runs, SYSTEM338's "in 1 to 4 sentences" becomes "fit the length to the message (a
sentence or two for small talk, a full and specific answer for advice or explanations)", and G4's cap is WORDS404
words instead of 90. The 1B's token budget stays 338's 200 (Gen338.max_new), which is above the twin's 160. Nothing
else changes: the same samples (N338 = 4, temperature 0.7), guards G1-G3, recall403, history, layers and order.
Other layers that read these two constants (cre333d sets and restores its own cap) see 338's values outside the
chat layer's call.

build_404 = build_403 with the two constants swapped around ch-403's chat turn only.

Fallback, ch-404g (a separate single change on X403, DEV-probed alongside so the next registered run can start at
once whichever wins): the chat layer's first candidate is the 1B's greedy reply to the same prompt, as the plain twin
decodes, then 338's 4 samples; the first candidate that passes 338's guards is sent. Length limits unchanged.
build_404g = build_403 with GreedyFirst404 wrapped around the chat layer's generator.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_ch403_agent as N  # noqa: E402
import claude_chat338_agent as C38  # noqa: E402

WORDS404 = 150
OLD_PHRASE = "Reply in natural, fluent English in 1 to 4 sentences, like a thoughtful friend:"
NEW_PHRASE = ("Reply in natural, fluent English like a thoughtful friend, and fit the length to the message (a "
              "sentence or two for small talk, a full and specific answer for advice or explanations):")
if OLD_PHRASE not in C38.SYSTEM338:
    raise RuntimeError("404: SYSTEM338 changed; expected its 1-to-4-sentences phrase")
SYSTEM404 = C38.SYSTEM338.replace(OLD_PHRASE, NEW_PHRASE)


def install_chat404(loop, gen, n: int = C38.N338) -> None:
    """ch-403's chat layer, run with SYSTEM404 and WORDS404 in place of SYSTEM338 and MAX_WORDS338."""
    N.install_chat403(loop, gen, n)
    inner = loop.turn                       # ch-403's turn338 (its closure holds state and save)
    loop.chat404_stats = {"turns": 0}

    def turn338(text: str) -> list[str]:
        _ = (state, save)                   # keep the history cells visible to claude_fix02c.chat338_state (F1)
        loop.chat404_stats["turns"] += 1
        old = (C38.SYSTEM338, C38.MAX_WORDS338)
        C38.SYSTEM338, C38.MAX_WORDS338 = SYSTEM404, WORDS404
        try:
            return inner(text)
        finally:
            C38.SYSTEM338, C38.MAX_WORDS338 = old

    cells = dict(zip(inner.__code__.co_freevars, inner.__closure__ or ()))
    state, save = cells["state"].cell_contents, cells["save"].cell_contents
    loop.turn = turn338


def build_404(state_dir, args):
    """ch-403's X403 with install_chat404 in its chat layer's place; every other layer is build_02c's."""
    import claude_chat338b_agent as C38B
    import claude_e2e02c as E
    orig = C38B.install_chat338b
    C38B.install_chat338b = install_chat404
    try:
        loop = E.build_02c(state_dir, args)
    finally:
        C38B.install_chat338b = orig
    loop.layers330c = [("chat404" if x == "chat338b" else x) for x in loop.layers330c]
    return loop


class GreedyFirst404:
    """Stands in for 338's Gen338: the greedy reply first, then the same n samples."""

    def __init__(self, gen):
        self.gen = gen
        self.greedy_calls = 0

    def greedy(self, msgs: list[dict]) -> str:
        g = self.gen.g
        ids = g.tok(self.gen._render(msgs), return_tensors="pt").to(g.dev)
        with g.torch.no_grad():
            out = g.model.generate(**ids, max_new_tokens=self.gen.max_new, do_sample=False,
                                   pad_token_id=g.tok.eos_token_id)
        cut = ids["input_ids"].shape[1]
        return g.tok.decode(out[0][cut:], skip_special_tokens=True).strip()

    def sample_chat(self, msgs: list[dict], n: int) -> list[str]:
        self.greedy_calls += 1
        return [self.greedy(msgs)] + self.gen.sample_chat(msgs, n)


def install_chat404g(loop, gen, n: int = C38.N338) -> None:
    """ch-403's chat layer with GreedyFirst404 as its generator (recall403 still decides first)."""
    loop.chat404g_gen = GreedyFirst404(gen)
    N.install_chat403(loop, loop.chat404g_gen, n)


def build_404g(state_dir, args):
    """ch-403's X403 with install_chat404g in its chat layer's place; every other layer is build_02c's."""
    import claude_chat338b_agent as C38B
    import claude_e2e02c as E
    orig = C38B.install_chat338b
    C38B.install_chat338b = install_chat404g
    try:
        loop = E.build_02c(state_dir, args)
    finally:
        C38B.install_chat338b = orig
    loop.layers330c = [("chat404g" if x == "chat338b" else x) for x in loop.layers330c]
    return loop
