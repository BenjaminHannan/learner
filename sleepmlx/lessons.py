"""What sleep learns besides facts about named things (pure functions; the night pipeline in recipe.py calls them).

1. Failures and lessons. A day's failures are found from the diary rows (diary.py adds `tools`, `checks`, `stopped` to Ben's turns):
   Ben corrected Glim ("no, it's X", "that's wrong"), a tool step failed or was retried, Glim gave up, Glim's own self-check said
   "not done", or Ben pressed Stop. The model writes a short post-mortem for each (prompts.lesson_prompt); recipe.py checks it
   against the chat text and turns it into a lesson card plus one question-answer card.
2. Corrections, newest wins. `not_terms` finds "not X" in a correction; recipe.py retires the older fact the correction replaces and
   keeps the wrong value out of positive cards.
3. Habits. The same kind of tool job done on 3+ turns (open the same website, run the same command, search the web) becomes a habit card.
4. Saved notes (memory.json) and the "Keeping track of" list (tracking.md) from the Desk's userData folder become cards that carry
   their source and expiry; expired or finished items are not trained.

Everything here is a heuristic: which corrections and failures it finds is "suggested", not measured.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from . import diary as diary_mod
from .corpus import norm

# ---------------------------------------------------------------- failures
# Ben telling Glim it got something wrong. "No thanks" / "no need" are not corrections; a bare "No" (answering a question) is not either.
CORRECTION_RE = re.compile(
    r"^\W*(?:no|nope|nah)\b[\s,.!-]+(?:it'?s|it is|its|that'?s|that is|the|not|i said|i meant|wrong|you)\b"
    r"|\b(?:that'?s|that is|this is|you'?re|you are|it'?s|it is)\s+(?:wrong|incorrect|not (?:right|correct|true|it|what i))\b"
    r"|\bthat'?s not\b|\bnot quite\b|\bincorrect\b|\bwrong\b|\bi (?:said|meant)\b|\bcorrection\b|\byou (?:got|have) it wrong\b"
    r"|\b(?:that|it) didn'?t work\b|\bactually,?\s+(?:it|it'?s|he|she|they|that|the|my)\b", re.I)
NOT_WRONG_RE = re.compile(r"\bwrong (?:with|about me)\b|\bwhat'?s wrong\b|\bnothing wrong\b", re.I)   # "what's wrong with my code" asks, it does not correct
GAVE_UP_RE = re.compile(r"\bI (?:couldn'?t|could not|can'?t|cannot|was unable to|am unable to|wasn'?t able to|am not able to|'m not able to|'m unable to)\b"
                        r"|\bI reached the step limit\b|\bunable to (?:complete|finish|find|access|open)\b", re.I)
NOT_DONE_RE = re.compile(r"\bnot done\b", re.I)
KIND_WORDS = {"correction": "Ben corrected Glim", "tool_error": "a tool step failed", "stopped": "Ben stopped Glim",
              "gave_up": "Glim gave up", "self_check": "Glim's own check found the answer was not done yet"}
KIND_ORDER = ["correction", "tool_error", "stopped", "gave_up", "self_check"]


def is_correction(text: str) -> bool:
    t = text or ""
    return bool(CORRECTION_RE.search(t)) and not NOT_WRONG_RE.search(t)


def _day_turns(week: dict, day: int) -> Dict[int, dict]:
    """turn number -> {"user": row, "answer": text} for one day of the week JSON."""
    out: Dict[int, dict] = {}
    for r in week.get("diary", []):
        if r.get("day") != day:
            continue
        t = out.setdefault(r.get("turn", 0), {"user": None, "answer": ""})
        if r["role"] == "user":
            t["user"] = r
        else:
            t["answer"] = r.get("text", "")
    return {k: v for k, v in out.items() if v["user"] is not None}


def find_failures(week: dict, day: int) -> List[dict]:
    """The day's failures, at most one per turn (the strongest signal wins; all signals are listed).
    -> [{kind, signals, day, turn, user, answer, tools, checks, stopped, prev_user, prev_answer, prev_tools}]"""
    turns = _day_turns(week, day)
    keys = sorted(turns)
    out = []
    for n, k in enumerate(keys):
        t = turns[k]
        row = t["user"]
        tools = row.get("tools") or []
        prev = turns[keys[n - 1]] if n > 0 else None
        sig = []
        if prev and is_correction(row["text"]) and (prev["answer"] or prev["user"].get("tools")):
            sig.append("correction")
        if any(not x.get("ok", True) and "[stopped by user]" not in x.get("result", "") for x in tools):
            sig.append("tool_error")
        if row.get("stopped"):
            sig.append("stopped")
        if GAVE_UP_RE.search(t["answer"] or ""):
            sig.append("gave_up")
        if any(NOT_DONE_RE.search(c) for c in row.get("checks") or []):
            sig.append("self_check")
        if not sig:
            continue
        kind = min(sig, key=KIND_ORDER.index)
        f = {"kind": kind, "signals": sig, "day": day, "turn": k, "user": row["text"], "answer": t["answer"], "tools": tools,
             "checks": row.get("checks") or [], "stopped": bool(row.get("stopped")),
             "prev_user": prev["user"]["text"] if prev else "", "prev_answer": prev["answer"] if prev else "",
             "prev_tools": (prev["user"].get("tools") or []) if prev else []}
        out.append(f)
    return out


def _tool_lines(tools: List[dict], n: int = 6) -> List[str]:
    out = []
    for x in tools[:n]:
        out.append("- %s %s -> %s%s" % (x.get("name"), x.get("args", "")[:120], "ok" if x.get("ok", True) else "FAILED: ",
                                        "" if x.get("ok", True) else x.get("result", "")[:160]))
    if len(tools) > n:
        out.append("- (%d more steps)" % (len(tools) - n))
    return out


def failure_context(f: dict, who: str = "Ben") -> str:
    """The chat text a lesson is written from and checked against."""
    lines = []
    if f["kind"] == "correction":
        lines.append("%s: %s" % (who, f["prev_user"][:500]))
        if f["prev_tools"]:
            lines.append("Glim's tool steps:")
            lines += _tool_lines(f["prev_tools"])
        if f["prev_answer"]:
            lines.append("Glim: %s" % f["prev_answer"][:500])
        lines.append("%s then said: %s" % (who, f["user"][:500]))
        if f["tools"]:
            lines.append("Glim's tool steps after that:")
            lines += _tool_lines(f["tools"])
        if f["answer"]:
            lines.append("Glim: %s" % f["answer"][:400])
        return "\n".join(lines)
    lines.append("%s: %s" % (who, f["user"][:500]))
    if f["tools"]:
        lines.append("Glim's tool steps:")
        lines += _tool_lines(f["tools"])
    for c in f["checks"][:2]:
        lines.append("Glim's self-check: %s" % c[:200])
    if f["stopped"]:
        lines.append("%s pressed Stop." % who)
    if f["answer"]:
        lines.append("Glim: %s" % f["answer"][:500])
    return "\n".join(lines)


def failure_key(date: str, f: dict) -> str:
    return "lesson|" + hashlib.sha1(("%s|%s|%s" % (date, f["turn"], f["user"])).encode()).hexdigest()[:12]


# "not X" in a correction: X is the wrong value (a capitalised name, or a word with a digit such as "Room 9" -> "9").
NOT_TERM_RE = re.compile(r"\bnot (?:in |at |on |the |a |an )?((?:[A-Z][\w'-]*|\d[\w:/.-]*)(?: (?:[A-Z][\w'-]*|\d[\w:/.-]*))?)")


def not_terms(text: str) -> List[str]:
    terms = [m.group(1).strip(" .,'") for m in NOT_TERM_RE.finditer(text or "")]
    return [x for x in terms if len(x) >= 2 or x.isdigit()]


def lesson_ok(L: dict, f: dict, ctx: str, wrong: set) -> Optional[str]:
    """Checks a parsed lesson against the chat text. -> None if it may become a card, else the reason it is dropped."""
    for k in ("did", "wrong", "instead", "q", "a"):
        if not isinstance(L.get(k), str) or not L[k].strip():
            return "missing_" + k
    q, a = L["q"].strip(), L["a"].strip().rstrip(".")
    if len(a) > 60 or len(a.split()) > 6:
        return "answer_too_long"
    if not q.endswith("?"):
        return "not_a_question"
    if norm(a) and norm(a) in norm(q):
        return "answer_in_question"
    src = f["user"] if f["kind"] == "correction" else ctx      # a correction's truth is what Ben said, nothing else
    if not norm(a) or norm(a) not in norm(src):
        return "answer_not_in_chat"
    wv = norm(L.get("wrong_value") or "")
    if norm(a) in wrong or (wv and norm(a) == wv):
        return "answer_is_the_wrong_value"
    if any(diary_mod.looks_secret(L.get(k) or "") or diary_mod.talks_secrets(L.get(k) or "") for k in ("did", "wrong", "instead", "q", "a", "wrong_value")):
        return "secret"
    return None


def scrub(text: str, values) -> str:
    """Replace each wrong value in a card text (so the wrong claim never appears in a card as if true)."""
    for v in sorted({v for v in values if v and (len(v) >= 2 or v.isdigit())}, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(v) + r"(?!\w)", "the wrong answer", text, flags=re.I)
    return text


def lesson_text(L: dict, f: dict, date: str) -> str:
    s = lambda x: " ".join(str(x).split()).rstrip(".")  # noqa: E731
    did = re.sub(r"^(?:Glim|I)\s+", "", s(L["did"]))
    return "Lesson from %s (%s): Glim %s. What went wrong: %s. Next time: %s." % (date, KIND_WORDS[f["kind"]], did[:1].lower() + did[1:], s(L["wrong"]), s(L["instead"]))


# ---------------------------------------------------------------- habits from tool use
JOB_TOOLS = {"browser_go", "open_app", "run_shell", "web_search", "diary_search", "track_add", "memory_save", "agent_start"}
TOOL_PHRASE = {"web_search": "search the web", "diary_search": "search past chats", "track_add": "add things to the Keeping track of list",
               "memory_save": "save notes about him", "agent_start": "start helper Glims"}


def _args(s: str) -> dict:
    try:
        j = json.loads(s)
        return j if isinstance(j, dict) else {}
    except ValueError:
        return {}


def job_of(step: dict) -> Optional[tuple]:
    """A tool step -> (category, target) naming the kind of job, or None for steps that are parts of a job (read, scroll, look)."""
    name = step.get("name") or ""
    if name not in JOB_TOOLS or not step.get("ok", True):
        return None
    a = _args(step.get("args") or "")
    if name == "browser_go":
        raw = a.get("url") or (re.search(r"https?://\S+", step.get("args") or "") or [None])[0]
        host = (urlparse(str(raw)).hostname or "") if raw else ""
        host = host[4:] if host.startswith("www.") else host
        return ("website", host) if host else None
    if name == "open_app":
        app = str(a.get("name") or "").strip()
        return ("app", app) if app else None
    if name == "run_shell":
        cmd = str(a.get("command") or "").strip().split()
        return ("command", cmd[0]) if cmd else None
    return ("tool", name)


def habits(week: dict, upto: int, min_n: int = 3) -> List[dict]:
    """Jobs done on at least min_n different turns (days <= upto). -> [{key, cat, target, n, days, first, last, top}] (top: the most
    used job of its category, which gets a question card)."""
    seen: Dict[tuple, set] = {}
    for r in week.get("diary", []):
        if r["role"] != "user" or r["day"] > upto:
            continue
        for st in r.get("tools") or []:
            j = job_of(st)
            if j and not diary_mod.looks_secret(j[1]):
                seen.setdefault(j, set()).add((r["day"], r.get("turn", 0)))
    out = []
    for (cat, target), turns in seen.items():
        if len(turns) >= min_n:
            days = sorted({d for d, _ in turns})
            out.append({"key": "habit|%s|%s" % (cat, norm(target)), "cat": cat, "target": target, "n": len(turns), "days": len(days),
                        "first": days[0], "last": days[-1], "top": False})
    best: Dict[str, dict] = {}
    for h in sorted(out, key=lambda h: (-h["n"], h["target"])):
        best.setdefault(h["cat"], h)
    for h in best.values():
        h["top"] = True
    return sorted(out, key=lambda h: h["key"])


def habit_cards(h: dict, who: str = "Ben"):
    """-> (paraphrases, [[q, a]]) for one habit. The text has no counts, so it stays the same night to night."""
    cat, t = h["cat"], h["target"]
    if cat == "website":
        para, q = "%s often has Glim open %s." % (who, t), "Which website does %s most often have Glim open?" % who
    elif cat == "app":
        para, q = "%s often has Glim open the %s app." % (who, t), "Which app does %s most often have Glim open?" % who
    elif cat == "command":
        para, q = "%s often has Glim run %s commands." % (who, t), "Which command does %s most often have Glim run?" % who
    else:
        para, q = "%s often has Glim %s." % (who, TOOL_PHRASE.get(t, "use " + t)), None
    qa = [[q, t]] if (q and h["top"]) else []
    return [para], qa


# ---------------------------------------------------------------- the Desk's saved notes and tracking list
def default_user_data() -> Path:
    import os
    import sys
    if sys.platform.startswith("win"):
        return Path(os.environ.get("APPDATA") or os.path.expanduser("~/AppData/Roaming")) / "Premonition"
    if sys.platform == "darwin":
        return Path(os.path.expanduser("~/Library/Application Support/Premonition"))
    return Path(os.path.expanduser("~/.config/Premonition"))


def _safe(text: str, ignore) -> bool:
    return bool(text) and not diary_mod.looks_secret(text) and not diary_mod.talks_secrets(text) and not any(rx.search(text) for rx in ignore)


def _read_memory_md(user_data: Path) -> Optional[List[dict]]:
    """Port of src/memory.js parseMd: '- text | topic: x | id: y | updated: YYYY-MM-DD' lines. None when there is no memory.md."""
    import hashlib
    try:
        text = (user_data / "memory.md").read_text()
    except (OSError, ValueError):
        return None
    out = []
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]\s+(.*\S)\s*$", line)
        if not m:
            continue
        parts = re.split(r"\s+\|\s+", m.group(1))
        note = {"text": " ".join(parts[0].split()), "id": "", "topic": "", "updated": ""}
        for p in parts[1:]:
            kv = re.match(r"^(topic|id|updated):\s*(.*)$", p.strip(), re.I)
            if kv and kv.group(2).strip():
                note[kv.group(1).lower()] = kv.group(2).strip()
        if not note["text"]:
            continue
        if not note["id"]:
            note["id"] = "h" + hashlib.sha1(note["text"].lower().encode()).hexdigest()[:7]
        if not DATE_RE.match(note["updated"]):
            note["updated"] = ""
        out.append(note)
    return out


def read_notes(user_data: Optional[Path], ignore=()) -> List[dict]:
    """memory.md (src/memory.js; an older memory.json still works) -> [{id, text, topic, updated (YYYY-MM-DD)}]; secret-looking or ignored notes are left out."""
    md = _read_memory_md(Path(user_data)) if user_data else None
    if md is not None:
        return [n for n in md if _safe(n["text"] + " " + n["topic"], ignore)]
    try:
        j = json.loads((Path(user_data) / "memory.json").read_text())
    except (OSError, ValueError, TypeError):
        return []
    facts = j if isinstance(j, list) else (j.get("facts") if isinstance(j, dict) else None) or []
    out = []
    for f in facts:
        if not (isinstance(f, dict) and isinstance(f.get("text"), str) and f.get("id")):
            continue
        text, topic = " ".join(f["text"].split()), " ".join(str(f.get("topic") or "").split())
        if not _safe(text + " " + topic, ignore):
            continue
        upd = ""
        if isinstance(f.get("updated"), (int, float)):
            try:
                upd = datetime.fromtimestamp(f["updated"] / 1000.0).strftime("%Y-%m-%d")
            except (ValueError, OSError, OverflowError):
                upd = ""
        out.append({"id": str(f["id"]), "text": text, "topic": topic, "updated": upd})
    return out


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_tracking(text: str) -> dict:
    """Port of src/tracking.js parse(): -> {active: [...], done: [...]} of {what, source, until, added}."""
    out = {"active": [], "done": []}
    in_done = False
    for line in str(text or "").split("\n"):
        if re.match(r"^##\s+done\b", line, re.I):
            in_done = True
            continue
        if re.match(r"^##\s+", line):
            in_done = False
            continue
        m = re.match(r"^\s*-\s*\[([ xX])\]\s*(.*)$", line)
        if not m:
            continue
        parts = [p.strip() for p in m.group(2).split("|")]
        it = {"what": " ".join(parts[0].split())[:160], "source": "", "until": "", "added": ""}
        for p in parts[1:]:
            kv = re.match(r"^(source|until|added|done):\s*(.*)$", p, re.I)
            if kv:
                k, v = kv.group(1).lower(), kv.group(2).strip()
                if k == "source":
                    it[k] = " ".join(v.split())[:80]
                elif k in ("until", "added"):
                    it[k] = v if DATE_RE.match(v) else ""
        if not it["what"]:
            continue
        (out["done"] if in_done or m.group(1) != " " else out["active"]).append(it)
    return out


def read_tracking(user_data: Optional[Path], today: str, ignore=()) -> List[dict]:
    """The active, unexpired items of tracking.md (an item past its until date is expired here, though the Desk shows it for 7 more days)."""
    try:
        st = parse_tracking((Path(user_data) / "tracking.md").read_text())
    except (OSError, TypeError):
        return []
    return [it for it in st["active"] if (not it["until"] or it["until"] >= today) and _safe(it["what"] + " " + it["source"], ignore)]


def note_cards(n: dict, who: str = "Ben"):
    return ["Saved note about %s%s: %s" % (who, " (%s)" % n["topic"] if n["topic"] else "", n["text"])], []


def track_cards(it: dict, who: str = "Ben"):
    bits = []
    if it["source"]:
        bits.append("from %s" % it["source"])
    if it["until"]:
        bits.append("until %s" % it["until"])
    para = "%s is keeping track of %s%s." % (who, it["what"].rstrip("."), " (" + ", ".join(bits) + ")" if bits else "")
    qa = []
    if it["source"]:
        qa.append(["Where did the item \"%s\" on %s's tracking list come from?" % (it["what"].rstrip("."), who), it["source"]])
    if it["until"]:
        qa.append(["Until what date is %s keeping track of \"%s\"?" % (who, it["what"].rstrip(".")), it["until"]])
    return [para], qa
