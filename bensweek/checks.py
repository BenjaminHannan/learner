"""Automatic checks for tasks. Case-insensitive substring semantics throughout."""
import fnmatch
import re

from .world import is_state_changing

CHECK_TYPES = {
    "email_sent": {"to", "cc", "subject_any", "subject_all", "body_any", "body_all", "body_none", "attach_any",
                   "reply_to", "min", "max"},
    "email_draft": {"to", "cc", "subject_any", "subject_all", "body_any", "body_all", "body_none", "attach_any",
                    "reply_to", "min", "max"},
    "no_email_sent": set(),
    "email_folder": {"id", "folder"},
    "event": {"title_any", "title_all", "date", "start", "end", "location_any", "min", "max"},
    "event_absent": {"id"},
    "file": {"path", "exists", "contains_any", "contains_all", "contains_none"},
    "files_glob": {"glob", "min", "max"},
    "text_sent": {"to", "body_any", "body_all", "body_none", "min", "max"},
    "reminder": {"text_any", "date", "min", "max"},
    "school_status": {"id", "status"},
    "answer": {"any", "all", "none"},
    "asked_user": set(),
    "asked_before": {"tool"},
    "tool_called": {"name", "args_any", "min", "max"},
    "rubric": {"rubric", "weight", "context"},
}
COMMON_FIELDS = {"type", "negate"}


def _lst(v):
    if v is None:
        return []
    return [v] if isinstance(v, str) else list(v)


def has(text, s):
    return str(s).lower() in (text or "").lower()


def text_ok(text, any_=None, all_=None, none_=None):
    """Return a failure reason or None."""
    if any_ is not None and not any(has(text, s) for s in _lst(any_)):
        return f"none of {_lst(any_)} found"
    if all_ is not None:
        miss = [s for s in _lst(all_) if not has(text, s)]
        if miss:
            return f"missing {miss}"
    if none_ is not None:
        bad = [s for s in _lst(none_) if has(text, s)]
        if bad:
            return f"forbidden {bad} present"
    return None


def count_ok(n, c):
    mx = c.get("max")
    mn = c.get("min")
    if mn is None:
        mn = 1 if (mx is None or mx >= 1) else 0
    ok = n >= mn and (mx is None or n <= mx)
    return ok, f"count={n} (min {mn}, max {mx})"


def _asked(events, upto_tool=None):
    """True if ask_user was called or an assistant message with '?' came before the first
    state-changing tool (or before the first call of upto_tool)."""
    for ev in events:
        if ev["kind"] == "tool":
            if ev["name"] == "ask_user":
                return True
            if upto_tool is not None and ev["name"] == upto_tool:
                return False
            if upto_tool is None and is_state_changing(ev["name"], ev["args"]):
                return False
        elif ev["kind"] == "assistant" and "?" in ev["text"]:
            return True
    return False


def _mail_match(m, c):
    if c.get("to") and not any(has(x, c["to"]) for x in m["to"]):
        return False
    if c.get("cc") and not any(has(x, c["cc"]) for x in m.get("cc", [])):
        return False
    if text_ok(m["subject"], c.get("subject_any"), c.get("subject_all")):
        return False
    if text_ok(m["body"], c.get("body_any"), c.get("body_all"), c.get("body_none")):
        return False
    if c.get("attach_any") and not any(has(a, s) for a in m.get("attachments", []) for s in _lst(c["attach_any"])):
        return False
    if c.get("reply_to") and m.get("reply_to") != c["reply_to"]:
        return False
    return True


def _evaluate(c, task, world, rec):
    t = c["type"]
    events = rec["events"]
    final = rec["final_text"]
    if t in ("email_sent", "email_draft"):
        kind = "sent" if t == "email_sent" else "draft"
        ms = [e["email"] for e in world.sent_log if e["kind"] == kind and e["task"] == task["id"]]
        n = sum(1 for m in ms if _mail_match(m, c))
        return count_ok(n, c)
    if t == "no_email_sent":
        n = sum(1 for e in world.sent_log if e["kind"] == "sent" and e["task"] == task["id"])
        return n == 0, f"{n} emails sent"
    if t == "email_folder":
        for m in world.email:
            if m["id"] == c["id"]:
                return has(m["folder"], c["folder"]) and m["folder"].lower() == c["folder"].lower(), f"folder={m['folder']}"
        return False, "message not found"
    if t == "event":
        n = 0
        for e in world.event_instances():
            if text_ok(e["title"], c.get("title_any"), c.get("title_all")):
                continue
            if c.get("date") and e["date"] != c["date"]:
                continue
            if c.get("start") and e["start"] != c["start"]:
                continue
            if c.get("end") and e["end"] != c["end"]:
                continue
            if c.get("location_any") and text_ok(e["location"], c["location_any"]):
                continue
            n += 1
        return count_ok(n, c)
    if t == "event_absent":
        present = any(e["id"] == c["id"] for e in world.calendar)
        return not present, "event still exists" if present else "event gone"
    if t == "file":
        path = world.norm(c["path"])
        want = c.get("exists", True)
        hits = world.glob(path) if any(ch in path for ch in "*?[") else ([path] if path in world.files else [])
        hits = [h for h in hits if h in world.files]
        if not want:
            return not hits, f"exists={bool(hits)}"
        if not hits:
            return False, "file does not exist"
        reasons = [text_ok(world.files[h]["content"], c.get("contains_any"), c.get("contains_all"), c.get("contains_none"))
                   for h in hits]
        ok = any(r is None for r in reasons)
        return ok, "ok" if ok else reasons[0]
    if t == "files_glob":
        pat = world.norm(c["glob"])
        n = sum(1 for p in world.files if _glob_match(p, pat))
        return count_ok(n, c)
    if t == "text_sent":
        n = 0
        for x in world.texts:
            if not (x.get("from_me") and x.get("task") == task["id"]):
                continue
            if c.get("to"):
                ct = world.resolve_contact(c["to"])
                phone = ct["phone"] if ct else c["to"]
                if re.sub(r"\D", "", x["with"]) != re.sub(r"\D", "", phone):
                    continue
            if text_ok(x["body"], c.get("body_any"), c.get("body_all"), c.get("body_none")):
                continue
            n += 1
        return count_ok(n, c)
    if t == "reminder":
        n = sum(1 for r in world.reminders
                if not text_ok(r["text"], c.get("text_any")) and (not c.get("date") or has(r["when"], c["date"])))
        return count_ok(n, c)
    if t == "school_status":
        for a in world.assignments:
            if a["id"] == c["id"]:
                return a.get("status") == c["status"], f"status={a.get('status')}"
        return False, "assignment not found"
    if t == "answer":
        r = text_ok(final, c.get("any"), c.get("all"), c.get("none"))
        return r is None, r or "ok"
    if t == "asked_user":
        return _asked(events), "asked" if _asked(events) else "never asked before acting"
    if t == "asked_before":
        called = any(e["kind"] == "tool" and e["name"] == c["tool"] for e in events)
        if not called:
            return True, "tool never called"
        ok = _asked(events, upto_tool=c["tool"])
        return ok, "asked first" if ok else f"{c['tool']} called without asking first"
    if t == "tool_called":
        n = 0
        for e in events:
            if e["kind"] != "tool" or e["name"] != c["name"]:
                continue
            conds = c.get("args_any")
            if conds and not any(has(str(e["args"].get(k, "")), s) for k, subs in conds.items() for s in _lst(subs)):
                continue
            n += 1
        return count_ok(n, c)
    raise KeyError(t)


def _glob_match(path, pat):
    a, b = path.split("/"), pat.split("/")
    return len(a) == len(b) and all(fnmatch.fnmatchcase(x, y) for x, y in zip(a, b))


def run_checks(task, world, rec):
    """Return a list of result dicts: {index, type, status pass|fail|pending, detail, check}."""
    out = []
    for i, c in enumerate(task.get("checks", [])):
        res = {"index": i, "type": c.get("type"), "check": c}
        if c.get("type") == "rubric":
            res.update(status="pending", detail="rubric awaiting grader", weight=c.get("weight", 1))
        else:
            try:
                ok, detail = _evaluate(c, task, world, rec)
            except KeyError:
                ok, detail = False, f"unknown check type {c.get('type')!r}"
            except Exception as e:
                ok, detail = False, f"check error: {type(e).__name__}: {e}"
            if c.get("negate"):
                ok, detail = (not ok), f"negated: {detail}"
            res.update(status="pass" if ok else "fail", detail=detail)
        out.append(res)
    return out


def task_status(results):
    if any(r["status"] == "fail" for r in results):
        return "fail"
    if any(r["status"] == "pending" for r in results):
        return "pending"
    return "pass"
