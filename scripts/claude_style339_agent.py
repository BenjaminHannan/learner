#!/usr/bin/env python3
"""339 learns how you like to be talked to (month-end line; plan design/v3/30-modes/330r-rebalance-2026-09-24.md).

One change on the 338 agent: feedback about the assistant's replies ("keep it shorter", "stop calling me
buddy", "no emojis please") is saved as a STYLE PREFERENCE, a separate kind from facts, in
<state_dir>/style339.json (so it survives sleeps and restarts), and every later reply follows it.

Detecting feedback: fixed rules (RULES339, checked in order; the first match wins). Each rule needs
the turn to be addressed to the assistant (you/your, or an imperative such as "keep it", "stop",
"no more", "call me"), so "my essay must be shorter" or "my coach keeps calling me champ" never match.
For no_nickname and name the rule captures the word or first name. (A 1B label-scoring detector was
tried first on 20 hand-written dev turns: 15/20 right, and it leaned to one label, so v1 uses rules.)
A feedback turn still runs the wrapped turn (so a fact in the same message is handled as before); its
reply is a fixed acknowledgement, followed by the wrapped reply only when that reply changed the notebook.

Following preferences:
  - StyledGen339 wraps 338's generator: every chat prompt's system line gets one sentence per
    preference (shorter, longer, casual, formal, no emoji, no nickname, no questions, the name to use).
  - post-filter on every reply (fixed or generated), never on a confirm question:
    no_nickname removes the word; no_emoji removes emoji; no_questions drops a closing question
    sentence when there are others; shorter keeps the first 2 sentences.
Opposite preferences replace each other (shorter/longer, casual/formal). Nothing is written to the
notebook. Counters in loop.style339_stats.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

STATE_NAME339 = "style339.json"
LABELS339 = ["shorter", "longer", "no_nickname", "no_emoji", "casual", "formal", "no_questions", "name"]
_YOU = r"\b(?:you|your|ur|u|yours)\b"
_I = re.I
RULES339 = [
    ("no_nickname", re.compile(r"\b(?:stop|don'?t|do not|quit|no more|not|never)\b[^.!?]{0,25}?\b(?:call(?:ing)?\s+me|"
                               r"saying)\s+[\"'“]?([A-Za-z]+)", _I)),
    ("name", re.compile(r"(?:^|[.!?,;]\s*|\b(?:you can|u can|you could|please|pls|just|btw,?|actually,?|and|also)\s+)"
                        r"call me\s+[\"'“]?([A-Z][a-z]+)\b")),
    ("no_emoji", re.compile(r"\b(?:no|not|stop|less|fewer|without|quit|don'?t|do not|drop|ditch|lose)\b[^.!?]{0,25}?"
                            r"\b(?:emojis?|emoticons?|smiley faces?)", _I)),
    ("no_questions", re.compile(_YOU + r"[^.!?]{0,40}?\b(?:ask|asking|end|ending|finish|finishing)\b[^.!?]{0,30}?"
                                r"\bquestions?\b|\b(?:stop|don'?t|no need to|quit)\b[^.!?]{0,15}?\b(?:ask(?:ing)?"
                                r"(?: me)?(?: a| so many)? questions?|ending with a question)", _I)),
    ("shorter", re.compile(_YOU + r"[^.!?]{0,30}?\b(?:too long|so long|way too long|too wordy|so wordy|essays?|"
                           r"novels?|rambl\w*|long-winded|a lot of text|too much text)\b|\b(?:keep|make)\s+(?:it|them|"
                           r"things|(?:your )?(?:answers|replies|messages|responses))\s+(?:short|shorter|brief|briefer)\b|"
                           r"\b(?:shorter|briefer) (?:answers|replies|messages|responses)\b|\btl;?dr\b|"
                           r"\btoo long,? didn'?t read\b", _I)),
    ("longer", re.compile(r"(?:" + _YOU + r"[^.!?]{0,40}?\b(?:more detail|more details|more depth|go deeper|"
                          r"elaborate)\b)|\byour (?:answers|replies|messages|responses) (?:are|r|'re) (?:too short|so "
                          r"short|tiny|one line|one-liners)\b|\b(?:longer|more detailed) (?:answers|replies|messages|"
                          r"responses)\b", _I)),
    ("casual", re.compile(r"\b(?:less formal|more casual|be casual|chill out|relax a bit|loosen up|talk normal(?:ly)?|"
                          r"so stiff|too stiff|like a robot|so robotic|too robotic|so formal|too formal)\b", _I)),
    ("formal", re.compile(r"\b(?:more formal|be formal|more professional|more polite|less casual|less slang|"
                          r"too casual|so casual)\b", _I)),
]
_ADDRESSED = re.compile(_YOU + r"|(?:^|[.!?,;]\s*)(?:pls |please |ok |okay |also |and )?(?:keep|be|stop|don'?t|no more|"
                        r"less|more|go|give|talk|just|quit|call|drop|ditch|could|can|would)\b|\b(?:stop|don'?t|quit|no more|please|pls|"
                        r"from now on|next time|keep it|call me)\b", _I)
ACK339 = {
    "shorter": "Sure, I'll keep it short.",
    "longer": "Sure, I'll give you more detail.",
    "no_nickname": "Got it, I won't call you {d}.",
    "no_emoji": "Okay, no emojis.",
    "casual": "Sure, I'll keep it relaxed.",
    "formal": "Certainly. I will keep my replies more formal.",
    "no_questions": "Got it, I won't end every reply with a question.",
    "name": "Okay, {d} it is.",
}
PROMPT339 = {
    "shorter": "The user wants short replies: one or two sentences.",
    "longer": "The user wants more detailed replies with examples.",
    "casual": "The user wants a relaxed, casual tone.",
    "formal": "The user wants a polite, formal tone.",
    "no_emoji": "Never use emoji.",
    "no_questions": "Do not end replies with a question.",
}
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF️]")
OPPOSITE = {"shorter": "longer", "longer": "shorter", "casual": "formal", "formal": "casual"}


def _confirm(reply: str) -> bool:
    import claude_e2e336_run as R
    return R.is_confirm(reply)


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def apply_prefs(reply: str, prefs: dict) -> str:
    if not reply or _confirm(reply):
        return reply
    out = reply
    for w in prefs.get("no_nickname", []):
        out = re.sub(r",?\s*\b" + re.escape(w) + r"\b", "", out, flags=re.I)
        out = re.sub(r"\s+([,.!?])", r"\1", out).strip()
        out = out[:1].upper() + out[1:]
    if prefs.get("no_emoji"):
        out = re.sub(r"\s{2,}", " ", EMOJI.sub("", out)).strip()
    sents = _sentences(out)
    if prefs.get("no_questions") and len(sents) > 1 and sents[-1].endswith("?"):
        sents = sents[:-1]
    if prefs.get("length") == "shorter" and len(sents) > 2:
        sents = sents[:2]
    return " ".join(sents) if sents else out


def prompt_lines(prefs: dict) -> str:
    lines = []
    if prefs.get("length"):
        lines.append(PROMPT339[prefs["length"]])
    if prefs.get("tone"):
        lines.append(PROMPT339[prefs["tone"]])
    if prefs.get("no_emoji"):
        lines.append(PROMPT339["no_emoji"])
    if prefs.get("no_questions"):
        lines.append(PROMPT339["no_questions"])
    for w in prefs.get("no_nickname", []):
        lines.append(f'Never call the user "{w}".')
    if prefs.get("name"):
        lines.append(f"The user likes to be called {prefs['name']}; use it now and then.")
    return " ".join(lines)


class StyledGen339:
    """Wraps 338's generator; reads the loop's current preferences at every call."""

    def __init__(self, gen, loop):
        self.gen, self.loop = gen, loop

    def sample_chat(self, msgs, n):
        extra = prompt_lines(getattr(self.loop, "style339_prefs", {}) or {})
        if extra and msgs and msgs[0].get("role") == "system":
            msgs = [dict(msgs[0], content=msgs[0]["content"] + " " + extra)] + list(msgs[1:])
        return self.gen.sample_chat(msgs, n)


def detect(text: str) -> tuple[str, str | None] | None:
    if not _ADDRESSED.search(text):
        return None
    for lab, rx in RULES339:
        m = rx.search(text)
        if not m:
            continue
        d = m.group(1) if m.groups() else None
        return lab, (d.lower() if lab == "no_nickname" and d else d)
    return None


def install_style339(loop) -> None:
    inner = loop.turn
    path = Path(loop.dir) / STATE_NAME339
    prefs: dict = {}
    if path.exists():
        prefs = json.loads(path.read_text(encoding="utf-8"))
    loop.style339_prefs = prefs
    loop.style339_stats = {"turns": 0, "saved": 0, "applied_changed": 0}

    def save() -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(prefs, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        tmp.replace(path)

    def record(lab: str, d: str | None) -> None:
        if lab in ("shorter", "longer"):
            prefs["length"] = lab
        elif lab in ("casual", "formal"):
            prefs["tone"] = lab
        elif lab == "no_nickname":
            prefs["no_nickname"] = sorted(set(prefs.get("no_nickname", [])) | {d})
        elif lab == "name":
            prefs["name"] = d
        else:
            prefs[lab] = True
        save()

    def turn339(text: str) -> list[str]:
        loop.style339_stats["turns"] += 1
        hit = detect(text)
        ev0 = len(loop.nb.events)
        parts = inner(text)
        if hit is not None:
            lab, d = hit
            record(lab, d)
            loop.style339_stats["saved"] += 1
            ack = ACK339[lab].format(d=d)
            wrapped = " ".join(p for p in (parts or []) if p)
            return [ack + (" " + wrapped if len(loop.nb.events) != ev0 and wrapped else "")]
        out = []
        for p in parts or []:
            q = apply_prefs(p, prefs) if p else p
            if q != p:
                loop.style339_stats["applied_changed"] += 1
            out.append(q)
        return out

    turn339.__name__ = "turn339"
    loop.turn = turn339
