"""What kinds of work Ben uses the assistant for, from the raw diary."""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re

from . import tasks

KEYWORDS = {
    "spreadsheet": ["spreadsheet", "excel", "csv", "xlsx", "google sheet", "sheets", "pivot", "vlookup",
                    "xlookup", "sumif", "sumifs", "formula", "column", "columns", "cell", "cells"],
    "email": ["email", "e-mail", "inbox", "reply to", "subject line", "draft a reply", "cc", "unsubscribe"],
    "writing": ["essay", "paragraph", "rewrite", "proofread", "summarize", "summary", "article", "blog",
                "cover letter", "report", "edit this"],
    "code": ["python", "javascript", "function", "bug", "code", "script", "compile", "regex", "git",
             "stack trace", "traceback", "api"],
    "scheduling": ["calendar", "meeting", "schedule", "appointment", "remind", "reschedule", "deadline"],
    "research": ["research", "look up", "find out", "search for", "compare", "sources", "who is", "what is"],
    "math": ["calculate", "equation", "solve", "integral", "derivative", "algebra", "probability", "math"],
}
_PATTERNS = {k: [re.compile(r"\b" + re.escape(w) + r"\b", re.I) for w in ws] for k, ws in KEYWORDS.items()}


def classify(text: str) -> str:
    best, score = "other", 0
    for kind, pats in _PATTERNS.items():
        n = sum(1 for p in pats if p.search(text))
        if n > score:
            best, score = kind, n
    return best


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content
                         if not isinstance(p, dict) or p.get("type", "text") == "text")
    return ""  # {"$blob": ...} or None


def last_user_text(record: dict) -> str:
    for m in reversed(record.get("messages") or []):
        if isinstance(m, dict) and m.get("role") == "user":
            return _text(m.get("content"))
    return ""


def iter_user_turns(diary_dir: str, max_files: int = 60):
    raw = os.path.join(str(diary_dir), "raw")
    base = raw if os.path.isdir(raw) else str(diary_dir)
    seen = set()
    for path in sorted(glob.glob(os.path.join(base, "*.jsonl")))[-max_files:]:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(rec, dict):
                        continue
                    t = last_user_text(rec).strip()
                    h = hashlib.sha1(t.encode("utf-8", "replace")).hexdigest()
                    if t and h not in seen:
                        seen.add(h)
                        yield t
        except OSError:
            continue


def analyze(diary_dir: str, max_files: int = 60) -> dict:
    counts: dict = {}
    for t in iter_user_turns(diary_dir, max_files):
        k = classify(t)
        counts[k] = counts.get(k, 0) + 1
    total = sum(counts.values())
    return {"total": total, "counts": counts,
            "share": {k: v / total for k, v in counts.items()} if total else {}}


def practicable_kinds() -> list:
    return tasks.registered_kinds()


def pick_kind(stats: dict, min_share: float = 0.05):
    cands = [(stats["counts"].get(k, 0), k) for k in practicable_kinds()]
    cands = [c for c in cands if c[0] > 0 and stats["share"].get(c[1], 0) >= min_share]
    return max(cands)[1] if cands else None
