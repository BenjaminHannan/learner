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
KIND_WORDS = {"correction": "Ben corrected Glim", "disliked": "Ben gave the answer a thumbs down", "tool_error": "a tool step failed",
              "stopped": "Ben stopped Glim", "gave_up": "Glim gave up", "self_check": "Glim's own check found the answer was not done yet",
              "delegation": "a helper Glim's run went wrong"}
KIND_ORDER = ["correction", "disliked", "delegation", "tool_error", "stopped", "gave_up", "self_check"]


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


def _verdict_date(week: dict, v: dict) -> Optional[str]:
    """The diary date a verdict belongs to: its local day, or the next diary day after it (the last one if none), so none is dropped."""
    vd = str(v.get("day") or str(v.get("ts") or "")[:10])
    ds = sorted((week.get("dates") or {}).values())
    if not ds or not vd:
        return None
    return next((d for d in ds if d >= vd), ds[-1])


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
        if row.get("fb") == -1:   # Ben's thumbs down in the Desk
            sig.append("disliked")
        if row.get("stopped"):
            sig.append("stopped")
        if GAVE_UP_RE.search(t["answer"] or ""):
            sig.append("gave_up")
        if any(NOT_DONE_RE.search(c) for c in row.get("checks") or []):
            sig.append("self_check")
        if row.get("fb") == -1 and any(x.get("name") in ("agent_start", "agent_update") for x in tools):
            sig.append("delegation")   # a thumbs down on a turn that handed work to a helper
        if not sig:
            continue
        kind = min(sig, key=KIND_ORDER.index)
        f = {"kind": kind, "signals": sig, "day": day, "turn": k, "user": row["text"], "answer": t["answer"], "tools": tools,
             "checks": row.get("checks") or [], "stopped": bool(row.get("stopped")),
             "prev_user": prev["user"]["text"] if prev else "", "prev_answer": prev["answer"] if prev else "",
             "prev_tools": (prev["user"].get("tools") or []) if prev else []}
        out.append(f)
    date = (week.get("dates") or {}).get(str(day))
    runs = week.get("helper_runs") or []
    last = {r.get("name"): i for i, r in enumerate(runs)}
    for i, r in enumerate(runs):
        if date is None or r.get("date") != date:
            continue
        name = r.get("name") or ""
        sig = helper_signals(r)
        err = ""
        if last[name] == i and _helper_state(week, name).get("status") == "failed":
            sig.append("helper_failed")
            err = str(_helper_state(week, name).get("lastError") or "")
        if not sig:
            continue
        out.append({"kind": "delegation", "signals": sig, "day": day, "turn": 1000 + i, "user": r.get("task") or "", "answer": r.get("answer") or "",
                    "tools": r.get("tools") or [], "checks": r.get("checks") or [], "stopped": bool(r.get("stopped")), "prev_user": "", "prev_answer": "",
                    "prev_tools": [], "helper": name, "error": err})
    # Ben Oct 28: a reviewer judged a Mote's idea poor that day: the idea itself is the lesson (turn 2000+ never collides with helper runs at 1000+)
    for i, v in enumerate(week.get("idea_verdicts") or []):
        if date is None or v.get("verdict") != "poor" or _verdict_date(week, v) != date or not _idea_ok(v):
            continue
        out.append({"kind": "delegation", "signals": ["idea_poor"], "day": day, "turn": 2000 + i, "user": " ".join(v["idea"].split()), "answer": "",
                    "tools": [], "checks": [], "stopped": False, "prev_user": "", "prev_answer": "", "prev_tools": [],
                    "helper": v.get("helper") or "", "error": "", "reason": " ".join(str(v.get("reason") or "").split())})
    return out


def _helper_state(week: dict, name: str) -> dict:
    h = (week.get("helper_state") or {}).get(name)
    return h if isinstance(h, dict) else {}


def helper_signals(r: dict) -> List[str]:
    """What went wrong in one helper run (its own tool steps, a stop, a give-up report, no report at all); [] when it went fine."""
    sig = []
    if any(not x.get("ok", True) and "[stopped by user]" not in x.get("result", "") for x in r.get("tools") or []):
        sig.append("tool_error")
    if r.get("stopped"):
        sig.append("stopped")
    if GAVE_UP_RE.search(r.get("answer") or ""):
        sig.append("gave_up")
    if not (r.get("answer") or "").strip():
        sig.append("empty_answer")
    return sig


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
    if "idea_poor" in f.get("signals", []):
        return "Glim's Mote '%s' proposed this idea: %s\nA reviewer judged it poor: %s" % (f.get("helper", ""), f["user"][:500], (f.get("reason") or "")[:300])
    if f["kind"] == "delegation":
        lines.append("Glim gave helper '%s' this task: %s" % (f.get("helper", ""), f["user"][:500]))
        if f["tools"]:
            lines.append("The helper's tool steps:")
            lines += _tool_lines(f["tools"])
        for c in f["checks"][:2]:
            lines.append("The helper's self-check: %s" % c[:200])
        if f["stopped"]:
            lines.append("The helper was stopped.")
        if f["answer"]:
            lines.append("The helper's report: %s" % f["answer"][:500])
        if "helper_failed" in f["signals"]:
            lines.append("The helper's last run failed: %s" % (f.get("error") or "")[:200])
        return "\n".join(lines)
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
    if "disliked" in f.get("signals", []):
        lines.append("%s gave this answer a thumbs down." % who)
    if "delegation" in f.get("signals", []):
        lines.append("Glim handed part of this to a helper.")
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


# ---------------------------------------------------------------- likes and dislikes
def read_feedback(user_data: Path) -> List[dict]:
    """The Desk's feedback.jsonl ({ts, thread, fb: 1 | -1 | 0, user, answer}, appended on each click), in file order."""
    out = []
    try:
        lines = (Path(user_data) / "feedback.jsonl").read_text(errors="replace").splitlines()
    except (OSError, ValueError, TypeError):
        return out
    for line in lines:
        try:
            f = json.loads(line)
        except ValueError:
            continue
        if isinstance(f, dict) and f.get("fb") in (1, -1, 0):
            out.append(f)
    return out


def liked(week: dict) -> List[dict]:
    """Turns Ben gave a thumbs up, across the week: [{key, day, turn, user, answer}] (an answer without text is skipped)."""
    out = []
    for d in sorted({r["day"] for r in week.get("diary", [])}):
        for k, t in sorted(_day_turns(week, d).items()):
            if t["user"].get("fb") == 1 and (t["answer"] or "").strip():
                key = "liked|" + hashlib.sha1(("%s|%s" % (t["user"]["text"], t["answer"])).encode()).hexdigest()[:12]
                out.append({"key": key, "day": d, "turn": k, "user": t["user"]["text"], "answer": t["answer"]})
    return out


def rated(week: dict) -> List[dict]:
    """Every turn Ben rated (thumbs up fb 1, thumbs down fb -1), across the whole diary, oldest first:
    [{key, day, turn, fb, user, answer, ctx, next_user}]. ctx is the chat text a card is written from and checked against: up to 2 turns
    before, the rated turn (marked), and Ben's next message with Glim's reply. A turn without answer text, or that talks secrets, is skipped.
    The key hashes the same text as liked()'s ("rated|" + 12 hex), so the same turn is found again on any night."""
    out = []
    who = "Ben"
    for d in sorted({r["day"] for r in week.get("diary", [])}):
        turns = _day_turns(week, d)
        keys = sorted(turns)
        for n, k in enumerate(keys):
            t = turns[k]
            fb = t["user"].get("fb")
            user, ans = " ".join(str(t["user"].get("text") or "").split()), " ".join((t["answer"] or "").split())
            if fb not in (1, -1) or not ans or not user:
                continue
            if any(diary_mod.looks_secret(x) or diary_mod.talks_secrets(x) for x in (user, ans)):
                continue
            lines = []
            for pk in keys[max(0, n - 2):n]:
                pt = turns[pk]
                lines.append("%s: %s" % (who, " ".join(pt["user"]["text"].split())[:300]))
                if (pt["answer"] or "").strip():
                    lines.append("Glim: %s" % " ".join(pt["answer"].split())[:300])
            lines.append("%s: %s" % (who, user[:500]))
            lines.append("Glim: %s (%s gave this answer a thumbs %s)" % (ans[:800], who, "up" if fb == 1 else "down"))
            nxt = turns[keys[n + 1]] if n + 1 < len(keys) else None
            if nxt:
                lines.append("%s then said: %s" % (who, " ".join(nxt["user"]["text"].split())[:300]))
                if (nxt["answer"] or "").strip():
                    lines.append("Glim: %s" % " ".join(nxt["answer"].split())[:300])
            key = "rated|" + hashlib.sha1(("%s|%s" % (t["user"]["text"], t["answer"])).encode()).hexdigest()[:12]
            out.append({"key": key, "day": d, "turn": k, "fb": fb, "user": user, "answer": ans, "ctx": "\n".join(lines),
                        "next_user": " ".join(nxt["user"]["text"].split()) if nxt else ""})
    return out


def liked_cards(l: dict, who: str = "Ben"):
    """-> (paraphrases, [[q, a]]) for one liked answer, word for word from the chat (no model writes them)."""
    ask = " ".join(l["user"].split())[:200]
    ans = " ".join(l["answer"].split())
    first = re.split(r"(?<=[.!?])\s+", ans)[0][:200]
    para = "%s liked how Glim answered \"%s\": %s" % (who, ask, ans[:500])
    return [para], [["How did Glim answer %s's request \"%s\" in a way %s liked?" % (who, ask[:120], who), first]]


# ---------------------------------------------------------------- helpers (Motes) working together
def read_helpers(user_data: Optional[Path]) -> Dict[str, dict]:
    """The Desk's helpers.json (a list of helper records, or {"helpers": [...]}) -> {name: {status, lastError, fails}}; {} when missing or bad."""
    try:
        j = json.loads((Path(user_data) / "helpers.json").read_text())
    except (OSError, ValueError, TypeError):
        return {}
    if isinstance(j, dict):
        j = j.get("helpers")
    out = {}
    for h in j if isinstance(j, list) else []:
        if isinstance(h, dict) and isinstance(h.get("name"), str) and h["name"].strip():
            f = h.get("fails")
            out[h["name"]] = {"status": str(h.get("status") or ""), "lastError": str(h.get("lastError") or ""), "fails": f if isinstance(f, int) else 0}
    return out


def helper_habits(week: dict, min_n: int = 3) -> List[dict]:
    """Helpers with at least min_n runs that went fine (no failure signal) and whose last run did not fail.
    -> [{key, name, task (the newest good run's), n}]"""
    good: Dict[str, List[dict]] = {}
    for r in week.get("helper_runs") or []:
        name = r.get("name") or ""
        if name and not helper_signals(r):
            good.setdefault(name, []).append(r)
    out = []
    for name, rs in good.items():
        task = " ".join(str(rs[-1].get("task") or "").split())
        if len(rs) < min_n or not task or _helper_state(week, name).get("status") == "failed":   # the helper's last run failed
            continue
        if diary_mod.looks_secret(name) or diary_mod.looks_secret(task):
            continue
        out.append({"key": "delegate|" + norm(name), "name": name, "task": task, "n": len(rs)})
    return sorted(out, key=lambda h: h["key"])


def helper_cards(h: dict, who: str = "Ben"):
    """-> (paraphrases, [[q, a]]) for one reliable helper. No counts in the text, so it stays the same night to night."""
    first = re.split(r"(?<=[.!?])\s+", h["task"])[0]
    return ["Glim's helper '%s' reliably handles this for %s: %s" % (h["name"], who, first[:200])], [["Which helper does Glim use for %s?" % first[:120].rstrip(" .!?;:"), h["name"]]]


# ---------------------------------------------------------------- the Desk's saved notes and tracking list
# ---------------------------------------------------------------- Motes' ideas, judged by a reviewer
def read_idea_verdicts(user_data: Optional[Path]) -> List[dict]:
    """The Desk's idea-verdicts.jsonl ({id, ts, verdict: good | poor, reason, helper, idea}), in file order; [] when missing or bad."""
    out = []
    try:
        lines = (Path(user_data) / "idea-verdicts.jsonl").read_text(errors="replace").splitlines()
    except (OSError, ValueError, TypeError):
        return out
    for line in lines:
        try:
            v = json.loads(line)
        except ValueError:
            continue
        if isinstance(v, dict) and v.get("verdict") in ("good", "poor") and isinstance(v.get("idea"), str) and v["idea"].strip():
            out.append(v)
    return out


def _idea_ok(v: dict) -> bool:
    if not isinstance(v.get("idea"), str) or len(v["idea"]) > 300 or not isinstance(v.get("reason", ""), str):
        return False
    return not any(diary_mod.looks_secret(str(v.get(k) or "")) or diary_mod.talks_secrets(str(v.get(k) or "")) for k in ("idea", "reason", "helper"))


def good_ideas(week: dict) -> List[dict]:
    """The week's ideas a reviewer called good (secrets skipped), one per id."""
    seen, out = set(), []
    for v in week.get("idea_verdicts") or []:
        k = v.get("id") or v.get("idea")
        if v.get("verdict") == "good" and k not in seen and _idea_ok(v):
            seen.add(k)
            out.append(v)
    return out


def idea_cards(v: dict, who: str = "Ben"):
    """-> (paraphrases, [[q, a]]) for one idea a reviewer called good."""
    idea = " ".join(v["idea"].split())
    name, why = v.get("helper") or "", " ".join(str(v.get("reason") or "").split())
    return ["Glim's Mote '%s' had a good idea for %s's project: %s (a reviewer said: %s)" % (name, who, idea, why)], [["What good idea did Glim's Mote '%s' have?" % name, idea[:160]]]


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
