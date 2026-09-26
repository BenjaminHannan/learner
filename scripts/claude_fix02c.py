#!/usr/bin/env python3
"""0.2c boundary fixes from Ben's outside code review (2026-09-26 01:54 UTC), each checked against the code first.
New file only; used by scripts/claude_e2e02c.py. Month-end line.

F1 delivered history (review 4). claude_chat338_agent.install_chat338 writes ITS reply into the chat history it
   feeds the 1B on later turns (line 176), but outer layers (answer382, route383, vary330c, gram360) can replace the
   reply the user sees. install_delivered02c, the outermost layer, rewrites that history entry to the reply actually
   delivered, in memory and in <state_dir>/chat338.json.
F2 final answer kept (review 8). claude_chat338_agent.trim cuts back to the last full sentence, so "... = 12. The
   answer is 17" loses "The answer is 17" and "... Answer: B" loses the letter. trim02c keeps a short unfinished
   tail that carries a number, an option letter or the word "answer". route02c = route383 with trim02c (else the
   same code, guards and counters as scripts/claude_e2e383.py).
F3 date across restarts (review 6). install_heard382 starts each process with said_at = None, so after a restart
   heard rows lose their date until the chat states one again. install_heard02c starts from the last heard row's
   said_at in the store.
F4 same-row support, REPORT ONLY (review 5). 338's guards accept an answer when each capitalised word and number
   appears anywhere in the question or the retrieved rows, so rows "Ana lives in Paris" and "Bo lives in Rome"
   support "Ana lives in Rome". support02c counts, without changing any reply, how many memory answers have their
   new words (not in the question) all inside ONE retrieved row that also names a capitalised word of the question
   (or its speaker). loop.support02c_stats = {checked, one_row, not_one_row}.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

TAIL02C = re.compile(r"\d|\b[A-E]\b|\banswer\b", re.I)
CAPNUM = re.compile(r"\b([A-Z][a-z]+|\d+)\b")


# ------------------------------------------------------------------ F1
def chat338_state(turn338):
    """The history dict and save() of an installed claude_chat338_agent.turn338 (its closure cells)."""
    cells = dict(zip(turn338.__code__.co_freevars, turn338.__closure__ or ()))
    if turn338.__name__ != "turn338" or "state" not in cells or "save" not in cells:
        raise RuntimeError("fix02c: expected claude_chat338_agent's turn338")
    return cells["state"].cell_contents, cells["save"].cell_contents


def install_delivered02c(loop, state, save) -> None:
    inner = loop.turn
    loop.delivered02c_stats = {"turns": 0, "rewritten": 0}

    def delivered02c(text: str) -> list[str]:
        out = inner(text)
        loop.delivered02c_stats["turns"] += 1
        said = " ".join(p for p in (out or []) if p)
        h = state.get("history") or []
        if len(h) >= 2 and h[-2].get("role") == "user" and h[-2].get("content") == text \
                and h[-1].get("role") == "assistant" and h[-1].get("content") != said:
            h[-1] = {"role": "assistant", "content": said}
            save()
            loop.delivered02c_stats["rewritten"] += 1
        return out

    delivered02c.__name__ = "delivered02c"
    loop.turn = delivered02c


# ------------------------------------------------------------------ F2
def trim02c(c: str) -> str:
    import claude_chat338_agent as C38
    base = C38.trim(c)
    full = re.sub(r"^(assistant|ai)\s*:\s*", "", C38.THINK.sub("", c).strip(), flags=re.I).strip()
    if not base or not full.startswith(base):
        return base
    tail = full[len(base):].strip()
    if tail and len(tail.split()) <= 12 and TAIL02C.search(tail):
        return (base + " " + tail).strip()
    return base


def install_route02c(loop, gen, n: int | None = None) -> None:
    """route383 (scripts/claude_e2e383.py) with trim02c in place of 338's trim; nothing else differs."""
    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    import claude_e2e382 as E382
    import claude_e2e383 as E383
    n = E383.N383 if n is None else n
    inner = loop.turn
    npath = Path(getattr(loop, "dir", ".")) / "route383_names.json"
    heard = set(json.loads(npath.read_text(encoding="utf-8"))) if npath.exists() else set()
    loop.route383_stats = {"turns": 0, "tried": 0, "replaced_think_split": 0, "replaced_other": 0,
                           "all_failed": 0, "people_kept": 0, "G1": 0, "G2": 0, "G3": 0, "G4": 0,
                           "tail_kept": 0}

    def route02c(text: str) -> list[str]:
        loop.route383_stats["turns"] += 1
        ev0 = len(loop.nb.events)
        parts = inner(text)
        names = C38B.notebook_names(loop) | heard
        new = E383.heard_names383(text) - heard
        if new:
            heard.update(new)
            if getattr(loop, "dir", None) is not None:
                npath.write_text(json.dumps(sorted(heard)), encoding="utf-8")
        reply = " ".join(p for p in (parts or []) if p)
        if not (E382.abstains(reply) and C38B.is_question(text) and len(loop.nb.events) == ev0
                and getattr(loop, "lis314_confirming", None) is None):
            return parts
        if E383.about_user383(text, names):
            loop.route383_stats["people_kept"] += 1
            return parts
        loop.route383_stats["tried"] += 1
        known = C38._words([text])
        msgs = [{"role": "system", "content": E383.SYSTEM383}, {"role": "user", "content": text}]
        for c in gen.sample_chat(msgs, n):
            t = trim02c(c)
            if t != C38.trim(c):
                loop.route383_stats["tail_kept"] += 1
            g = E383.guard383(t, text, known)
            if g is not None:
                loop.route383_stats[g] += 1
                continue
            if len(loop.nb.events) != ev0:
                raise RuntimeError("02c: route phase wrote to the notebook")
            loop.route383_stats["replaced_think_split" if E383.THINK_SPLIT in reply else "replaced_other"] += 1
            return [t]
        loop.route383_stats["all_failed"] += 1
        return parts

    route02c.__name__ = "route02c"
    loop.turn = route02c


# ------------------------------------------------------------------ F3
def install_heard02c(loop, store) -> None:
    """install_heard382 (scripts/claude_e2e382.py) with said_at carried over from the store across restarts."""
    import claude_e2e382 as E382
    inner = loop.turn
    heard = [r for r in store.rows if r["source"] == "heard"]
    state = {"said_at": heard[-1].get("said_at") if heard else None, "turn": len(heard)}

    def heard02c(text: str) -> list[str]:
        out = inner(text)
        m = E382.DATE382.match(text)
        if m:
            state["said_at"] = m.group("d").strip()
        state["turn"] += 1
        store.remember(text, source="heard", speaker="user", turn_ids=[state["turn"]], said_at=state["said_at"],
                       logged_at=E382._now())
        return out

    heard02c.__name__ = "heard02c"
    loop.turn = heard02c


# ------------------------------------------------------------------ F4
def one_row_supported(answer: str, question: str, rows: list[dict]) -> bool:
    import claude_e2e383 as E383
    qwords = {w.lower() for w in re.findall(r"[A-Za-z0-9']+", question)}
    qcaps = E383.heard_names383(question)                 # names inside the question, not its first word
    import claude_e2e382 as E382
    new = {t.lower() for t in CAPNUM.findall(answer)} - qwords - E382.STARTERS382
    if not new:
        return True
    for r in rows:
        words = {w.lower() for w in re.findall(r"[A-Za-z0-9']+", r.get("text", "") + " " + (r.get("said_at") or ""))}
        words.add(str(r.get("speaker", "")).lower())
        if new <= words and (not qcaps or qcaps & words):
            return True
    return False


def install_support02c(loop, store) -> None:
    """Report only: runs right outside answer382 and counts, never changes the reply."""
    inner = loop.turn
    loop.support02c_stats = {"checked": 0, "one_row": 0, "not_one_row": 0}

    def support02c(text: str) -> list[str]:
        before = dict(getattr(loop, "ep382_stats", {}) or {})
        out = inner(text)
        after = getattr(loop, "ep382_stats", {}) or {}
        if after.get("replaced", 0) > before.get("replaced", 0):
            ids = set(getattr(loop, "ep382_last_rows", []) or [])
            rows = [r for r in store.rows if r["id"] in ids]
            loop.support02c_stats["checked"] += 1
            ok = one_row_supported(" ".join(out or []), text, rows)
            loop.support02c_stats["one_row" if ok else "not_one_row"] += 1
        return out

    support02c.__name__ = "support02c"
    loop.turn = support02c
