#!/usr/bin/env python3
"""338 open conversation (month-end line; plan design/v3/30-modes/330r-rebalance-2026-09-24.md).

One change on a 292-lineage loop: install_chat338(loop, gen) wraps loop.turn. Every turn goes to
the wrapped turn first, so saving, confirming and answering from the notebook are unchanged. Only
when the wrapped turn gave up (its reply contains a CLARIFY marker, the fixed list the 336 scorer
uses, or is one of the two canned instruction lines in CANNED338) AND changed nothing (no
notebook event, same lis-314 pending store, no confirm question open) does 338 replace that
reply with ordinary conversation from the shared MiniCPM5-1B.

The chat phase:
  1. prompt = a fixed system line + the notebook's facts about the user and anyone the turn names
     (333's context_facts, read-only) + the last HISTORY338 messages of this chat (persisted in
     <state_dir>/chat338.json, so they survive a restart) + the user's turn.
  2. draw N338 samples; take the first that passes every guard (sample-first, like own-M1v):
     G1 no memory claims ("I'll remember", "noted", ...): nothing was saved this turn;
     G2 no invented people: "your <relation> <Name>" or "<Name>, your <relation>" with a Name
        found neither in the facts, the history nor the turn;
     G3 personal questions (the turn says my/I and asks something): every capitalised word after
        the first word and every number in the reply must be found in the facts, history or turn;
     G4 length: 1 to 90 words after trimming to the last full sentence, and no <think> text.
  3. If no sample passes, the wrapped turn's reply stays (fail closed).
Nothing produced here is saved to the notebook. Counters in loop.chat338_stats.

gen: any object with .sample_chat(messages: list[dict], n: int) -> list[str]; Gen338 below wraps
the base MiniCPM5-1B (it can share the model object of 333's Gen333).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

N338 = 4
HISTORY338 = 12                       # messages (6 exchanges)
MAX_WORDS338 = 90
STATE_NAME338 = "chat338.json"
SYSTEM338 = ("You are a friendly assistant chatting with the user. Reply in natural, fluent English in 1 to 4 "
             "sentences, like a thoughtful friend: answer questions directly, give real help with advice or "
             "explanations, and be warm when they share feelings. Don't talk about being an AI or about notes. "
             "Never make up facts about the user or people they know; if they ask about their own life and the "
             "answer is not in the chat or the facts below, say you don't know. Never say you will remember "
             "something.")
MEMORY_CLAIMS = [r"\bi'?ll remember\b", r"\bi will remember\b", r"\bnoted\b", r"\bi'?ve saved\b", r"\bsaved\b",
                 r"\bi'?ll keep (that|it|this) in mind\b", r"\bi'?ll make a note\b", r"\bmade a note\b",
                 r"\bi'?ve written\b", r"\bgot it,? i'?ll\b", r"\bi'?ll note\b", r"\bin my notes\b"]
RELATIONS = ("sister|brother|mom|mum|mother|dad|father|wife|husband|partner|girlfriend|boyfriend|son|daughter|"
             "friend|boss|coworker|colleague|roommate|neighbor|neighbour|cousin|aunt|uncle|grandma|grandpa|"
             "grandmother|grandfather|teacher|coach|doctor|dog|cat|pet|kid|child|baby")
CANNED338 = ["teach me like", "i'm here and ready to learn"]   # 156b greeting help line, 234 how-are-you line
THINK = re.compile(r"<think>.*?</think>", re.S)


def _clarify_markers() -> list[str]:
    import claude_e2e336_score as S
    return S.CLARIFY_MARKERS


def gave_up(reply: str) -> bool:
    low = reply.lower()
    return any(m in low for m in _clarify_markers()) or any(m in low for m in CANNED338)


def personal_question(text: str) -> bool:
    low = text.lower()
    return bool(re.search(r"\b(my|mine|me|i|i'm|i've|i'd)\b", low)) and (
        "?" in low or re.match(r"\s*(what|who|where|when|which|how|do|did|does|is|was|are|remind|tell)\b", low)
        is not None)


def _words(texts) -> set[str]:
    return {w.lower() for t in texts for w in re.findall(r"[A-Za-z0-9']+", t)}


def trim(c: str) -> str:
    c = THINK.sub("", c).strip()
    c = re.sub(r"^(assistant|ai)\s*:\s*", "", c, flags=re.I).strip()
    if not c:
        return ""
    ends = [m.end() for m in re.finditer(r"[.!?](?=\s|$)", c)]
    if ends and ends[-1] < len(c):
        c = c[:ends[-1]]
    return c.strip()


def guard(c: str, text: str, known: set[str]) -> str | None:
    """None if c passes, else the name of the first guard it fails."""
    low = c.lower()
    n = len(c.split())
    if n == 0 or n > MAX_WORDS338 or "<think" in low or "</think" in low:
        return "G4"
    if any(re.search(p, low) for p in MEMORY_CLAIMS):
        return "G1"
    for m in re.finditer(r"\byour (?:" + RELATIONS + r")(?:'s)?,? ([A-Z][a-z]+)", c):
        if m.group(1).lower() not in known:
            return "G2"
    for m in re.finditer(r"\b([A-Z][a-z]+),? (?:is )?your (?:" + RELATIONS + r")\b", c):
        if m.group(1).lower() not in known:
            return "G2"
    if personal_question(text):
        toks = re.findall(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z]+|\d+)\b", c)
        import claude_cre333_agent as C
        if any(t.lower() not in known and t not in C.ALLOW for t in toks):
            return "G3"
    return None


def install_chat338(loop, gen, n: int = N338) -> None:
    import claude_cre333_agent as C
    inner = loop.turn
    path = Path(loop.dir) / STATE_NAME338
    state = {"history": []}
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    loop.chat338_stats = {"turns": 0, "gave_up": 0, "replaced": 0, "kept_all_failed": 0,
                          "G1": 0, "G2": 0, "G3": 0, "G4": 0}

    def save() -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    def pending():
        return json.dumps(getattr(loop, "lis314_store", None), sort_keys=True, ensure_ascii=False)

    def turn338(text: str) -> list[str]:
        loop.chat338_stats["turns"] += 1
        ev0, p0 = len(loop.nb.events), pending()
        parts = inner(text)
        reply = " ".join(p for p in (parts or []) if p)
        out = parts
        if (gave_up(reply) and len(loop.nb.events) == ev0 and pending() == p0
                and getattr(loop, "lis314_confirming", None) is None):
            loop.chat338_stats["gave_up"] += 1
            ctx = C.context_facts(loop, text)
            facts = " ".join(C._sentence(f) for f in ctx)
            hist = state["history"][-HISTORY338:]
            known = _words([text, facts] + [h["content"] for h in hist])
            system = SYSTEM338 + (" Facts the user has told you: " + facts if facts else "")
            msgs = [{"role": "system", "content": system}] + hist + \
                   [{"role": "user", "content": text}]
            pick = None
            for c in gen.sample_chat(msgs, n):
                c = trim(c)
                g = guard(c, text, known)
                if g is None:
                    pick = c
                    break
                loop.chat338_stats[g] += 1
            if pick is None:
                loop.chat338_stats["kept_all_failed"] += 1
            else:
                loop.chat338_stats["replaced"] += 1
                out = [pick]
                reply = pick
            if len(loop.nb.events) != ev0:
                raise RuntimeError("338: chat phase wrote to the notebook")
        state["history"] = (state["history"] + [{"role": "user", "content": text},
                                                {"role": "assistant", "content": reply}])[-HISTORY338:]
        save()
        return out

    turn338.__name__ = "turn338"
    loop.turn = turn338


class Gen338:
    """Chat sampling on the base MiniCPM5-1B. Pass share=<Gen333> to reuse its loaded model."""

    def __init__(self, model_dir: str = "", share=None, max_new: int = 200, temperature: float = 0.7,
                 top_p: float = 0.9):
        if share is None:
            import claude_cre333_agent as C
            share = C.Gen333(model_dir)
        self.g = share
        self.max_new, self.t, self.p = max_new, temperature, top_p

    def _render(self, msgs: list[dict]) -> str:
        tok = self.g.tok
        kw = {"tokenize": False, "add_generation_prompt": True, "enable_thinking": False}   # no <think> block
        try:
            return tok.apply_chat_template(msgs, **kw)
        except Exception:  # noqa: BLE001  (a template without a system role)
            first = dict(msgs[1]) if len(msgs) > 1 else {"role": "user", "content": ""}
            first["content"] = msgs[0]["content"] + "\n\n" + first["content"]
            return tok.apply_chat_template([first] + msgs[2:], **kw)

    def sample_chat(self, msgs: list[dict], n: int) -> list[str]:
        g = self.g
        ids = g.tok(self._render(msgs), return_tensors="pt").to(g.dev)
        with g.torch.no_grad():
            out = g.model.generate(**ids, max_new_tokens=self.max_new, do_sample=True, temperature=self.t,
                                   top_p=self.p, num_return_sequences=n, pad_token_id=g.tok.eos_token_id)
        cut = ids["input_ids"].shape[1]
        return [g.tok.decode(o[cut:], skip_special_tokens=True).strip() for o in out]
