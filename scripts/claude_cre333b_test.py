#!/usr/bin/env python3
"""333b/333c unit tests. Every sentence here is written by the month-end thread; none comes from a TEST-ONLY panel."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_cre333_agent as C  # noqa: E402
import claude_cre333b_agent as CB  # noqa: E402

CREATIVE = [
    "can you give me some gift ideas for my brother? he loves climbing",
    "write me a short poem for my mom's birthday",
    "help me plan a rainy saturday with the kids",
    "what should i cook for dinner tonight? i have rice and eggs",
    "any ideas for a toast at my best friend's wedding?",
    "i need some ideas for a date night that isn't dinner and a movie",
    "could you write a card for my coworker who's leaving",
    "suggest a fun day trip near the coast",
    "brainstorm names for my new kitten",
    "plan a picnic for me and my sister this weekend",
    "come up with a silly story about my dog for my nephew",
    "what should i make for the potluck on friday?",
    "i'm looking for ideas for my dad's retirement party",
    "recommend me a book for the long flight",
    "ok can you help me write a thank-you note to my neighbour?",
]
LOOKALIKE = [
    "my sister runs a little gift shop on the high street",
    "we're planning a trip to the lakes in june",
    "i have no idea where i left my keys",
    "my boss had the idea to move standup to 9",
    "my son wrote a story about dragons for school",
    "the plan is to paint the kitchen next month",
    "who wrote that song you mentioned? no wait, i mentioned it",
    "whose idea was the camping trip again?",
    "any idea what time the party starts?",
    "my friend recommended a great dentist, dr lindqvist",
    "i gave my aunt a scarf as a present for christmas",
    "our band's song got played on the local radio",
    "my wife plans a big dinner every sunday",
    "the gift card from my coworker expires in may",
    "my grandpa used to write poems for my grandma",
    "i wrote down the recipe my mum gave me",
    "remind me what gift i got for my sister last year",
    "did i tell you about the story my teacher read us?",
    "my cousin is planning her wedding for august",
    "we had the idea of adopting a second cat",
]


def test_router():
    got = [t for t in CREATIVE if not CB.is_creative333c(t)]
    assert not got, got
    wrong = [t for t in LOOKALIKE if CB.is_creative333c(t)]
    assert len(wrong) <= 2, wrong
    return sum(C.is_creative(t) for t in LOOKALIKE), len(wrong)


class Tok:
    chat_template = "x"
    eos_token_id = 0

    def __init__(self):
        self.kw = None

    def apply_chat_template(self, msgs, **kw):
        self.kw = kw
        return "PROMPT"

    def __call__(self, s, return_tensors=None):
        import torch

        class D(dict):
            def to(self, d):
                return self
        return D(input_ids=torch.zeros(1, 3, dtype=torch.long))

    def decode(self, ids, skip_special_tokens=True):
        return "<think>hmm, Let me See</think>\n\nTry a picnic by the river."


def test_gen333b():
    import torch

    class M:
        def generate(self, **kw):
            return torch.zeros(kw["num_return_sequences"], 5, dtype=torch.long)
    g = CB.Gen333b.__new__(CB.Gen333b)
    g.torch, g.tok, g.model, g.dev, g.max_new, g.t, g.p = torch, Tok(), M(), "cpu", 120, 0.9, 0.95
    out = g.sample("plan a day", 3)
    assert out == ["Try a picnic by the river."] * 3 and g.tok.kw["enable_thinking"] is False


if __name__ == "__main__":
    old, new = test_router()
    test_gen333b()
    print(f"333b/c tests: 2/2 OK (own look-alikes routed: 333 {old}/20, 333c {new}/20)")
