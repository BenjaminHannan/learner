"""A model of Ben in the weights (Ben's round-2 idea, 2026-11-04: "this should be trained into it through sleep, beyond notes"),
and the Watch-me skill cards.

Ben model. Every night, from Ben's OWN chat lines (the diary's user turns) and his saved notes that name him, a fixed set of sentence
patterns picks out what Ben likes / doesn't like, his favourites, what he is working on / learning / knows how to do, and when he stops
working on something. No model decides what is stored: the patterns do (Ben's rule: sleep is automatic and mathematical).
  * Sources: Ben's chat turns and memory.md notes. Never a `maybe` note (those are not in memory.md: src/truthnotes.js saves only
    confirmed ones), and never the web: notes whose topic marks a web check (checked / correction / skill: ...) or that carry a link are left out.
  * Newest wins per slot (like-or-not of X, favourite of a kind, working on X, ...): the older statement is retired and its cards leave the
    pool. The newer one is trained as a correction (priority x2). Working-on / learning statements leave the pool 45 days after the last mention.
  * Cards: a third-person statement and Ben's own words (text cards, word for word), plus one quiz question (templated for favourites,
    otherwise written by the base model and checked like a note card). About half of the new questions are held out: they form the
    BEN QUIZ, answered in the morning with the adapter on and NO notes in the prompt.
Skill cards. desk/src/watchme.js saves skills Ben showed once (userData/watchme-skills.json): the numbered steps with his narration.
Each becomes a text card plus up to 3 short questions (which app it starts in, which button a step clicks); one is held out.

Real effect on Glim: untested until real nights report (see morning.py: "Ben quiz").
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from .corpus import norm

SKILLS_FILE = "watchme-skills.json"
WEB_TOPICS = re.compile(r"^(checked|correction|skill:)", re.I)
STOP_OBJ = {"it", "this", "that", "them", "these", "those", "you", "your", "how", "when", "what", "if", "the way", "him", "her"}
_OBJ = r"(?P<x>[^.,;!?\n\"]{2,80})"
# (relation, first-person pattern, third-person pattern for notes)
PATTERNS = [
    ("dislikes", r"\bI (?:really |just |still )?(?:don'?t|do not) (?:like|enjoy|love) " + _OBJ, r"\b{who} (?:doesn'?t|does not) (?:like|enjoy|love) " + _OBJ),
    ("dislikes", r"\bI (?:really |just )?(?:hate|dislike|can'?t stand) " + _OBJ, r"\b{who} (?:hates|dislikes) " + _OBJ),
    ("favorite", r"\bmy fav(?:o|ou)rite (?P<cat>[a-z][a-z ]{1,25}?) is " + _OBJ, r"\b{who}'s fav(?:o|ou)rite (?P<cat>[a-z][a-z ]{1,25}?) is " + _OBJ),
    ("likes", r"\bI (?:really |also |just |still )?(?:like|love|enjoy) " + _OBJ, r"\b{who} (?:really |also )?(?:likes|loves|enjoys) " + _OBJ),
    ("stopped", r"\bI(?:'m| am) (?:no longer|not) working on " + _OBJ, r"\b{who} is (?:no longer|not) working on " + _OBJ),
    ("stopped", r"\bI (?:finished|stopped working on|quit working on) " + _OBJ, r"\b{who} (?:finished|stopped working on) " + _OBJ),
    ("working_on", r"\bI(?:'m| am) (?:currently |still |now |also )?working on " + _OBJ, r"\b{who} is (?:currently |still |now )?working on " + _OBJ),
    ("learning", r"\bI(?:'m| am) (?:currently |now |also )?(?:learning|studying) " + _OBJ, r"\b{who} is (?:currently |now )?(?:learning|studying) " + _OBJ),
    ("knows", r"\bI (?:already )?know how to " + _OBJ, r"\b{who} knows how to " + _OBJ),
    ("knows", r"\bI(?:'m| am) (?:really )?good at " + _OBJ, r"\b{who} is (?:really )?good at " + _OBJ),
]
SLOT = {"likes": "like", "dislikes": "like", "favorite": "fav", "working_on": "work", "stopped": "work", "learning": "learn", "knows": "know"}
FADE_DAYS = {"working_on": 45, "learning": 45, "stopped": 30}
CUT = re.compile(r"\s+(?:but|because|since|so|and I|and then|when|while|which|if)\b.*$", re.I)


def third_person(x: str, who: str) -> str:
    x = re.sub(r"\bmy\b", who + "'s", x, flags=re.I)
    x = re.sub(r"\bmine\b", who + "'s", x, flags=re.I)
    x = re.sub(r"\b(?:me|myself)\b", who, x, flags=re.I)
    return re.sub(r"\bI\b", who, x)


def clean_obj(x: str) -> Optional[str]:
    x = CUT.sub("", " ".join(str(x).split())).strip(" '\"")
    x = re.sub(r"\s+(?:a lot|so much|very much|anymore|any more|too|now|right now|these days|lately)$", "", x, flags=re.I).strip()
    w = x.split()
    if not 1 <= len(w) <= 8 or norm(x) in STOP_OBJ or w[0].lower() in STOP_OBJ or w[0].lower() in ("you", "your", "it", "that", "this", "how", "what", "when", "doing"):
        return None
    return x


def sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", str(text or "")) if s.strip()]


def statement(rel: str, x: str, who: str, cat: str = "") -> str:
    x = third_person(x, who)
    return {"likes": "%s likes %s." % (who, x), "dislikes": "%s does not like %s." % (who, x),
            "favorite": "%s's favorite %s is %s." % (who, cat, x), "working_on": "%s is working on %s." % (who, x),
            "stopped": "%s is no longer working on %s." % (who, x), "learning": "%s is learning %s." % (who, x),
            "knows": "%s knows how to %s." % (who, x) if not re.match(r"^(?:\w+ing)\b", x) else "%s is good at %s." % (who, x)}[rel]


def find(text: str, who: str, third: bool) -> List[dict]:
    """Statements in one chat line (first person) or note (third person). Questions, quotes and hypotheticals are skipped."""
    out = []
    for s in sentences(text):
        if s.endswith("?") or re.search(r"[\"“”]|\b(?:if|would|could|should|maybe|might|pretend|say)\b", s, re.I):
            continue
        taken = []
        for rel, p1, p3 in PATTERNS:
            rx = re.compile(p3.replace("{who}", re.escape(who)) if third else p1, re.I)
            for m in rx.finditer(s):
                if any(a <= m.start() < b for a, b in taken):
                    continue
                x = clean_obj(m.group("x"))
                if not x:
                    continue
                cat = " ".join(m.group("cat").split()).lower() if "cat" in rx.groupindex else ""
                taken.append((m.start(), m.end()))
                out.append({"rel": rel, "x": x, "cat": cat, "quote": s[:240]})
    return out


def web_note(n: dict) -> bool:
    return bool(WEB_TOPICS.match(n.get("topic") or "")) or bool(re.search(r"https?://|\bwww\.|according to|\bsources? say", n.get("text") or "", re.I))


def extract(turns: List[dict], notes: List[dict], who: str, date_of, today: str) -> Dict[str, dict]:
    """turns: Ben's diary turns [{day, text}] (only days already reached); notes: memory.md notes [{id, text, topic, updated}].
    -> {slot key: statement} with the newest statement per slot; each carries every source and day it was seen on, and the
    statement it replaced (`replaces`), so a correction is trained as one."""
    seen: List[dict] = []
    for t in turns:
        for f in find(t.get("text") or "", who, third=False):
            seen.append(dict(f, date=date_of(t["day"]) or "", order=(date_of(t["day"]) or "", 0, t.get("i", 0)), src="chat"))
    for n in notes:
        if web_note(n) or not re.search(r"\b%s\b" % re.escape(who), n.get("text") or ""):
            continue
        for f in find(n["text"], who, third=True):
            seen.append(dict(f, date=n.get("updated") or today, order=(n.get("updated") or today, 1, 0), src="note " + str(n.get("id"))))
    seen.sort(key=lambda f: f["order"])
    out: Dict[str, dict] = {}
    for f in seen:
        slot = SLOT[f["rel"]] + "|" + (norm(f["cat"]) if f["rel"] == "favorite" else norm(f["x"]))
        old = out.get(slot)
        days = set(old["dates"]) if old and old["rel"] == f["rel"] and (f["rel"] != "favorite" or norm(old["x"]) == norm(f["x"])) else set()
        rep = None
        if old and (old["rel"] != f["rel"] or norm(old["x"]) != norm(f["x"])):
            rep = statement(old["rel"], old["x"], who, old["cat"])
        elif old:
            rep = old.get("replaces")
        days.add(f["date"])
        same = bool(old) and old["rel"] == f["rel"] and norm(old["x"]) == norm(f["x"])
        out[slot] = dict(f, dates=sorted(days), replaces=rep, sources=sorted(set(old["sources"] if same else []) | {f["src"]}))
    for v in out.values():
        fd = FADE_DAYS.get(v["rel"])
        v["until"] = _plus_days(max(v["dates"]), fd) if fd and max(v["dates"]) else ""
    return out


def _plus_days(date: str, n: int) -> str:
    from datetime import date as D, timedelta
    try:
        return (D.fromisoformat(date) + timedelta(days=n)).isoformat()
    except ValueError:
        return ""


def ben_cards(v: dict, who: str):
    """-> (para, templated qa or [] when the base model should write the question)"""
    st = statement(v["rel"], v["x"], who, v["cat"])
    para = [st, "%s said%s: \"%s\"" % (who, " on " + v["dates"][-1] if v["dates"] and v["dates"][-1] else "", v["quote"])]
    if v.get("replaces"):
        para.append("Correction about %s: earlier, \"%s\" Now: %s" % (who, v["replaces"], st))
    qa = [["What is %s's favorite %s?" % (who, v["cat"]), third_person(v["x"], who)]] if v["rel"] == "favorite" else []
    return para, qa


# ---- Watch-me skill cards --------------------------------------------------------------------------------------------------
def read_skills(user_data: Optional[Path], ignore=()) -> List[dict]:
    if not user_data:
        return []
    try:
        j = json.loads((Path(user_data) / SKILLS_FILE).read_text())
    except (OSError, ValueError):
        return []
    from .lessons import _safe
    out = []
    for s in (j.get("skills") if isinstance(j, dict) else None) or []:
        if not isinstance(s, dict) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", str(s.get("id") or "")) or not isinstance(s.get("steps"), list) or not s["steps"]:
            continue
        name = " ".join(str(s.get("name") or "").split())[:80]
        steps = [x for x in s["steps"] if isinstance(x, dict) and isinstance(x.get("do"), dict)][:40]
        text = "Skill \"%s\" (%s showed it once):\n" % (name, "Ben") + "\n".join(
            "%d. %s%s" % (i + 1, str(x.get("what") or "")[:120], (" (Ben: \"%s\")" % " ".join(str(x.get("say") or "").split())[:160]) if x.get("say") else "")
            for i, x in enumerate(steps))
        if not name or not steps or not _safe(text, ignore):
            continue
        out.append({"id": s["id"], "name": name, "steps": steps, "text": text, "created": str(s.get("created") or "")[:10]})
    return out


def skill_cards(s: dict, who: str):
    """-> (para, qa): the card text word for word, plus up to 3 short questions with one-to-four-word answers from the steps."""
    para = [s["text"].replace("(Ben showed", "(%s showed" % who)]
    qa = []
    first = s["steps"][0]["do"]
    if first.get("tool") == "open_app" and first.get("args", {}).get("name"):
        qa.append(["Which app does %s's skill \"%s\" start in?" % (who, s["name"]), str(first["args"]["name"])])
    for i, x in enumerate(s["steps"]):
        a = x["do"].get("args") or {}
        if x["do"].get("tool") == "click" and a.get("label") and 1 <= len(str(a["label"]).split()) <= 4:
            qa.append(["In %s's skill \"%s\", which button is clicked in step %d?" % (who, s["name"], i + 1), str(a["label"])])
        if len(qa) >= 3:
            break
    return para, qa
