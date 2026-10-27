#!/usr/bin/env python3
"""333e: the 1B decides when to call a write_creative tool, and the writer sees the conversation.
Creative research thread, 2026-09-24. Ben (19:13 UTC): "It shouldn't be keyword. The worker model should be able to
call the creative model as a tool ... can't you give it the conversation?"

Why (design/v3/30-modes/research-creative-2026-09-24.md): 333c/333d route with keyword regexes (25/40 panel requests
routed; 6 of 8 hand-written requests missed), and 333d's writer sees only the last message plus notebook facts,
while twin b, which beat it 10/40 to 8/40 on useful, sees the whole chat.

Two changes, measured as separate arms so each is one change:
  e1 (routing only, on 333d): every turn is first shown to MiniCPM5-1B in its native tool-calling format with one
     tool, write_creative. The 1B's decision to call it is read from its own last-position hidden state by a
     trained tool-call head (a logistic head on layer HEAD333E["layer"], trained on
     artifacts/claude-cre333e-train-20260924 only; scripts/claude_cre333e_train.py). Zero-shot, the 1B described
     the call in words instead of emitting it, and its call probability did not separate requests from recall
     questions (dev probe, 2026-09-24), so the call decision is trained. No keyword list.
  e2 (conversation, on e1): the writer gets [system + notebook facts] + this chat so far (user turns and the replies
     the agent actually sent, last HISTORY333E messages) + the request, as twin b and 338 do.
Unchanged from 333d: generation (Gen338, 4 samples, first that passes guard333d), the fallback line, and 333's
guarantees (a creative turn never reaches the reader, never writes to the notebook, a WORK entry in experience).
"""
from __future__ import annotations

import json

import claude_chat338_agent as C38
import claude_cre333_agent as C
import claude_cre333d_agent as CD

HISTORY333E = 24          # messages the e2 writer sees (12 exchanges)
ROUTER_HISTORY333E = 3    # earlier user messages the router sees
TOOL333E = {"type": "function", "function": {
    "name": "write_creative",
    "description": ("Write something creative or give ideas for the user: gift ideas, plans for a day or trip, poems, "
                    "toasts, cards, speeches, stories, captions, what to cook or bring, or the wording of a message."),
    "parameters": {"type": "object", "properties": {"request": {"type": "string",
                                                                "description": "what the user wants, in a few words"}},
                   "required": ["request"]}}}
SYSTEM_ROUTER333E = (
    "You are a personal assistant that remembers facts the user tells you. You have one tool, write_creative. "
    "Call it when the user wants you to make something new for them: ideas, suggestions, a plan, a menu, a card, "
    "a poem, a toast, a speech, a story, a caption, or the wording of a message, text or email. Do not call it when "
    "the user tells you a fact (even about a plan, a gift or something someone wrote), asks what they told you "
    "earlier, asks a general knowledge question, or is just chatting; then answer normally without any tool.")


def router_messages(prior_user: list[str], text: str) -> list[dict]:
    return ([{"role": "system", "content": SYSTEM_ROUTER333E}] +
            [{"role": "user", "content": u} for u in prior_user[-ROUTER_HISTORY333E:]] +
            [{"role": "user", "content": text}])


class Router333e:
    """The 1B's tool-call decision: head(hidden state at the generation position of the tool-calling prompt)."""

    def __init__(self, gen, head: dict | str):
        self.g = gen
        self.head = json.loads(open(head, encoding="utf-8").read()) if isinstance(head, str) else head
        self.layer = int(self.head["layer"])

    def features(self, prior_user: list[str], text: str):
        g = self.g
        s = g.tok.apply_chat_template(router_messages(prior_user, text), tools=[TOOL333E], tokenize=False,
                                      add_generation_prompt=True, enable_thinking=False)
        ids = g.tok(s, return_tensors="pt").to(g.dev)
        with g.torch.no_grad():
            out = g.model(**ids, output_hidden_states=True)
        return out.hidden_states[self.layer][0, -1].float().cpu().tolist()

    def prob(self, prior_user: list[str], text: str) -> float:
        import math
        h, x = self.head, self.features(prior_user, text)
        z = h["b"] + sum(w * (v - m) / s for w, v, m, s in zip(h["w"], x, h["mean"], h["std"]))
        return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))

    def calls_tool(self, prior_user: list[str], text: str) -> tuple[bool, float]:
        p = self.prob(prior_user, text)
        return p >= float(self.head.get("threshold", 0.5)), p


def install_creative333e(loop, gen, router: Router333e, with_history: bool, n: int = CD.N333D) -> None:
    """gen: a Gen338 (sample_chat). with_history=False is arm e1, True is arm e2."""
    inner = loop.turn
    loop.cre333_stats = {"creative_turns": 0, "fallbacks": 0, "passed_through": 0,
                         "G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0}
    chat: list[dict] = []                 # this chat as the agent saw it: user turns and the replies it sent

    def turn333e(text: str) -> list[str]:
        prior_user = [m["content"] for m in chat if m["role"] == "user"]
        call, p = router.calls_tool(prior_user, text)
        loop.cre333_last_p = round(p, 4)
        if not call:
            loop.cre333_stats["passed_through"] += 1
            out = inner(text)
            chat.extend([{"role": "user", "content": text}, {"role": "assistant", "content": " ".join(out)}])
            return out
        ev0 = len(loop.nb.events)
        ctx = C.context_facts(loop, text)
        facts = " ".join(C._sentence(f) for f in ctx)
        hist = chat[-HISTORY333E:] if with_history else []
        known = C38._words([text, facts] + [m["content"] for m in hist])
        system = CD.SYSTEM333D + (" Facts the user has told you: " + facts if facts else "")
        reply = None
        for c in gen.sample_chat([{"role": "system", "content": system}] + hist +
                                 [{"role": "user", "content": text}], n):
            c = C38.trim(c)
            g = CD.guard333d(c, text, known)
            if g is None:
                reply = c
                break
            loop.cre333_stats[g] += 1
        loop.cre333_stats["creative_turns"] += 1
        if reply is None:
            loop.cre333_stats["fallbacks"] += 1
            reply = C.FALLBACK
        loop.counters["work"] = loop.counters.get("work", 0) + 1
        loop.experience.append({"tick": loop.tick, "kind": "work", "phase": "creative333e",
                                "arm": "e2" if with_history else "e1", "n": n, "p_call": round(p, 4),
                                "context_facts": len(ctx), "history": len(hist)})
        loop._save()
        if len(loop.nb.events) != ev0:
            raise RuntimeError("333e: creative turn wrote to the notebook")
        chat.extend([{"role": "user", "content": text}, {"role": "assistant", "content": reply}])
        return [reply]

    turn333e.__name__ = "turn333e"
    loop.turn = turn333e
