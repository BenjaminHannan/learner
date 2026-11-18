import re
"""End-state assertions: a small JSON DSL. run_checks(task, world, final_reply) -> list[bool]."""
CHECK_KEYS = {  # type -> allowed keys
    "file_exists": {"path"}, "file_absent": {"path"}, "file_contains": {"path", "text"},
    "email_sent": {"to", "subject_contains", "body_contains"}, "no_email_sent": set(),
    "draft_exists": {"to", "subject_contains", "body_contains"},
    "event_exists": {"title_contains", "date", "start"}, "no_event_created": set(),
    "reminder_exists": {"text_contains", "when_contains"}, "note_contains": {"title", "text"},
    "reply_contains": {"any_of"},
}


def _has(hay, needle):
    return str(needle).lower() in str(hay).lower()


def _word(hay, needle):
    """Whole-word, case-insensitive match (substring matching let 'which' match 'whichever')."""
    return re.search(r"(?<!\w)" + re.escape(str(needle).lower()) + r"(?!\w)", str(hay).lower()) is not None


def _mail_ok(m, c):
    return (not c.get("to") or any(_has(r, c["to"]) for r in ([m["to"]] if isinstance(m["to"], str) else m["to"] + m.get("cc", [])))) \
        and (not c.get("subject_contains") or _has(m.get("subject", ""), c["subject_contains"])) \
        and (not c.get("body_contains") or _has(m.get("body", ""), c["body_contains"]))


def validate_check(c):
    if not isinstance(c, dict) or c.get("type") not in CHECK_KEYS:
        return False
    keys = set(c) - {"type"}
    if not keys <= CHECK_KEYS[c["type"]]:
        return False
    need = {"file_exists": ["path"], "file_absent": ["path"], "file_contains": ["path", "text"], "reply_contains": ["any_of"],
            "note_contains": ["text"]}.get(c["type"], [])
    if any(k not in c for k in need) or (c["type"] == "reply_contains" and not (isinstance(c["any_of"], list) and c["any_of"])):
        return False
    if c["type"] in ("email_sent", "draft_exists", "event_exists", "reminder_exists") and not keys:
        return False
    return all(isinstance(v, (str, list)) for v in c.values())


def run_check(c, w, reply):
    from sandbox import _norm
    t = c["type"]
    if t == "file_exists": return _norm(c["path"]) in w.files
    if t == "file_absent": return _norm(c["path"]) not in w.files
    if t == "file_contains": return _norm(c["path"]) in w.files and _has(w.files[_norm(c["path"])], c["text"])
    if t == "email_sent": return any(_mail_ok(m, c) for m in w.sent)
    if t == "no_email_sent": return len(w.sent) == 0
    if t == "draft_exists": return any(_mail_ok(m, c) for m in w.drafts)
    if t == "event_exists":
        return any((not c.get("title_contains") or _has(e["title"], c["title_contains"])) and (not c.get("date") or e["date"] == c["date"])
                   and (not c.get("start") or e["start"] == c["start"]) for e in w.events[w.n_events0:])
    if t == "no_event_created": return len(w.events) == w.n_events0
    if t == "reminder_exists":
        return any((not c.get("text_contains") or _has(r["text"], c["text_contains"])) and (not c.get("when_contains") or _has(r["when"], c["when_contains"]))
                   for r in w.reminders)
    if t == "note_contains":
        return any((not c.get("title") or _has(k, c["title"])) and _has(v, c["text"]) for k, v in w.notes.items())
    if t == "reply_contains": return any(_word(reply or "", x) for x in c["any_of"])
    return False


def run_checks(task, world, final_reply):
    return [bool(run_check(c, world, final_reply)) for c in task["checks"]]
