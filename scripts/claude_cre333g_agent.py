#!/usr/bin/env python3
"""333g: blurt many ideas, a trained judge keeps the best 3, the reply offers them as guesses.
Creative research thread, 2026-09-25.

Ben (00:39 UTC 09-25): creativity is the brain part that "says random stuff then gets filtered out" ... "maximize the
number of times it gets lucky". 333e's writer (first draft that passes filters) was useful on 7/40; blurt-1 showed 15%
of the 1B's idea blurts are good and 9/10 DEV requests have at least one good blurt among 30, so picking is the key.

One change from 333e arm e1 (same tool-call router, same head333e): the writer. On a creative turn:
  1. blurt: N333G = 30 samples from the base 1B (thinking off, temperature 1.0, 60 new tokens) with the blurt-1 idea
     prompt (claude_blurt1.SYSTEM_IDEA + the chat's user turns + the request);
  2. judge: each blurt is scored by a logistic head on the 1B's own hidden state at the end of a judging prompt
     (claude_blurt_selfjudge.JUDGE; head trained on open-weights teacher labels for 30 DEV requests,
     artifacts/claude-blurt2-20260925/ideahead/head.json; DEV: a good idea in its top 3 on 7/10 held-out requests);
  3. reply: the top K333G = 3 distinct blurts (unfinished last sentence trimmed), under a line saying they are guesses.
Unchanged: a creative turn never reaches the reader, never writes to the notebook, one WORK entry in experience.
"""
from __future__ import annotations

import json
import re

import claude_blurt1 as B1
import claude_blurt_selfjudge as SJ

N333G = 30
K333G = 3
TEMP333G = 1.0
MAXNEW333G = 60
LEAD333G = "Here are a few ideas (my guesses, so tell me what fits):"
FALLBACK333G = "I don't have a good idea for that yet. Can you tell me a bit more about what you want?"


def trim(t: str) -> str:
    """Drop an unfinished last sentence (blurts stop at MAXNEW333G tokens)."""
    t = re.sub(r"\s+", " ", t).strip()
    m = re.match(r"^(.*[.!?])(\s|$)", t, re.S)
    return m.group(1) if m and len(m.group(1)) >= 20 else t


class IdeaJudge333g:
    def __init__(self, gen, head: dict | str):
        import numpy as np
        self.np, self.g = np, gen
        h = json.loads(open(head, encoding="utf-8").read()) if isinstance(head, str) else head
        self.layer = int(h["layer"])
        self.w, self.b = np.array(h["w"]), float(h["b"])
        self.mean, self.std = np.array(h["mean"]), np.array(h["std"])

    def score(self, user_turns: list[str], request: str, idea: str) -> float:
        g, np = self.g, self.np
        msg = SJ.JUDGE.format(chat="\n".join("- " + t for t in user_turns), req=request, idea=idea)
        s = g.tok.apply_chat_template([{"role": "user", "content": msg}], tokenize=False, add_generation_prompt=True,
                                      enable_thinking=False)
        ids = g.tok(s, return_tensors="pt").to(g.dev)
        with g.torch.no_grad():
            hs = g.model(**ids, output_hidden_states=True).hidden_states
        x = hs[self.layer][0, -1].float().cpu().numpy()
        return float(1 / (1 + np.exp(-(((x - self.mean) / self.std) @ self.w + self.b))))


def blurt(gen, user_turns: list[str], request: str, n: int = N333G) -> list[str]:
    g = gen
    msgs = [{"role": "system", "content": B1.SYSTEM_IDEA}] + [{"role": "user", "content": t} for t in user_turns] + \
           [{"role": "user", "content": request}]
    s = g.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    ids = g.tok(s, return_tensors="pt").to(g.dev)
    with g.torch.no_grad():
        out = g.model.generate(**ids, max_new_tokens=MAXNEW333G, do_sample=True, temperature=TEMP333G, top_p=1.0,
                               num_return_sequences=n, pad_token_id=g.tok.eos_token_id)
    cut = ids["input_ids"].shape[1]
    return [re.sub(r"\s+", " ", g.tok.decode(o[cut:], skip_special_tokens=True)).strip()[:400] for o in out]


def pick(blurts: list[str], scores: list[float], k: int = K333G) -> list[str]:
    picks, seen = [], set()
    for s, t in sorted(zip(scores, blurts), key=lambda z: -z[0]):
        key = re.sub(r"\W+", "", t.lower())[:60]
        if not t or key in seen:
            continue
        seen.add(key)
        picks.append(trim(t))
        if len(picks) == k:
            break
    return picks


def compose(picks: list[str]) -> str:
    if not picks:
        return FALLBACK333G
    return LEAD333G + "\n" + "\n".join(f"{i + 1}. {t}" for i, t in enumerate(picks))


def install_creative333g(loop, gen, router, judge: IdeaJudge333g, n: int = N333G, k: int = K333G) -> None:
    """gen: a Gen333b (tok, model, dev, torch). router: a claude_cre333e_agent.Router333e sharing gen."""
    inner = loop.turn
    loop.cre333_stats = {"creative_turns": 0, "fallbacks": 0, "passed_through": 0, "blurts": 0}
    user_turns: list[str] = []

    def turn333g(text: str) -> list[str]:
        call, p = router.calls_tool(list(user_turns), text)
        loop.cre333_last_p = round(p, 4)
        if not call:
            loop.cre333_stats["passed_through"] += 1
            out = inner(text)
            user_turns.append(text)
            return out
        ev0 = len(loop.nb.events)
        prior = user_turns[-12:]
        bl = blurt(gen, prior, text, n)
        sc = [judge.score(prior, text, b) for b in bl]
        picks = pick(bl, sc, k)
        reply = compose(picks)
        loop.cre333_stats["creative_turns"] += 1
        loop.cre333_stats["blurts"] += len(bl)
        if not picks:
            loop.cre333_stats["fallbacks"] += 1
        loop.counters["work"] = loop.counters.get("work", 0) + 1
        loop.experience.append({"tick": loop.tick, "kind": "work", "phase": "creative333g", "n": n, "k": k,
                                "p_call": round(p, 4), "top_scores": [round(s, 4) for s in sorted(sc)[-k:]]})
        loop._save()
        if len(loop.nb.events) != ev0:
            raise RuntimeError("333g: creative turn wrote to the notebook")
        user_turns.append(text)
        return [reply]

    turn333g.__name__ = "turn333g"
    loop.turn = turn333g


def _selftest() -> None:
    assert trim("One idea. Another that stops mid") == "One idea."
    assert trim("short. rest") == "short. rest"                     # too short to trim
    assert pick(["a plan here.", "A plan here!", "other plan x."], [0.9, 0.8, 0.1], 2) == ["a plan here.", "other plan x."]
    assert compose([]) == FALLBACK333G and compose(["x"]).startswith(LEAD333G)
    print("selftest ok")


if __name__ == "__main__":
    _selftest()
