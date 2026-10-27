"""Validate dev episodes: python -m bensweek.validate"""
import json
import re
import sys
from collections import Counter
from datetime import date, datetime

from .checks import CHECK_TYPES, COMMON_FIELDS
from .episodes import DEV_DIR
from .world import TOOL_SPECS, WEEK_DAYS, World, load_base, merge_world

TAGS = {"email", "files", "calendar", "school", "research", "texts", "memory", "safety", "computer", "planning", "writing"}
TASK_FIELDS = {"id", "kind", "time", "prompt", "tags", "checks", "ask_reply", "memory_source"}
DAY_FIELDS = {"date", "time", "arrivals", "tasks"}
EP_FIELDS = {"id", "title", "split", "world", "days"}
ARRIVAL_KEYS = {"email", "texts", "calendar", "files", "assignments", "assignments_update", "web", "contacts"}
REQUIRED = {"email_folder": {"id", "folder"}, "event_absent": {"id"}, "file": {"path"}, "files_glob": {"glob"},
            "school_status": {"id", "status"}, "asked_before": {"tool"}, "tool_called": {"name"}, "rubric": {"rubric"}}
TOOL_NAMES = {t[0] for t in TOOL_SPECS}
CREATED_ID = re.compile(r"^[sdnxr]\d+$")


def _hhmm(s):
    try:
        datetime.strptime(s, "%H:%M")
        return True
    except (ValueError, TypeError):
        return False


def _isodate(s):
    try:
        date.fromisoformat(s)
        return True
    except (ValueError, TypeError):
        return False


def validate_episode(ep, base):
    errs, warns = [], []
    stats = Counter()
    eid = ep.get("id", "?")

    def E(msg):
        errs.append(f"{eid}: {msg}")

    def W(msg):
        warns.append(f"{eid}: {msg}")

    for k in ep:
        if k not in EP_FIELDS:
            W(f"unknown episode field '{k}'")
    if not re.fullmatch(r"wk\d+", str(eid)):
        W("episode id is not wkNN")
    overlay = ep.get("world") or {}
    world = merge_world(base, overlay)
    for p in list(overlay.get("files", {})) + list(overlay.get("remove_files", [])):
        if not p.startswith("~/"):
            E(f"file path must start with ~/: {p}")
    ids = {"email": {m["id"] for m in world.get("email", [])},
           "event": {e["id"] for e in world.get("calendar", [])},
           "assignment": {a["id"] for a in world["school"].get("assignments", [])}}
    files = set(world.get("files", {}))
    w = World(world)           # for contact resolution
    seen, prev_date, order = set(), None, []
    days = ep.get("days")
    if not isinstance(days, list) or not days:
        E("no days")
        return errs, warns, stats
    for di, day in enumerate(days, 1):
        for k in day:
            if k not in DAY_FIELDS:
                W(f"day {di}: unknown field '{k}'")
        dd = day.get("date")
        if not _isodate(dd):
            E(f"day {di}: bad date {dd!r}")
        elif dd not in WEEK_DAYS:
            E(f"day {di}: date {dd} outside the week 2026-11-02..08")
        elif prev_date and dd < prev_date:
            E(f"day {di}: dates not in order")
        prev_date = dd if _isodate(dd) else prev_date
        if day.get("time") is not None and not _hhmm(day["time"]):
            E(f"day {di}: bad time {day['time']!r}")
        arr = day.get("arrivals") or {}
        for k in arr:
            if k not in ARRIVAL_KEYS:
                E(f"day {di}: unknown arrivals key '{k}'")
        for p in arr.get("files", {}):
            if not p.startswith("~/"):
                E(f"day {di}: arrival file path must start with ~/: {p}")
            files.add(p)
        for m in arr.get("email", []):
            if "id" not in m:
                E(f"day {di}: arriving email without id")
            elif m["id"] in ids["email"]:
                E(f"day {di}: duplicate email id {m['id']}")
            ids["email"].add(m.get("id"))
        for e in arr.get("calendar", []):
            ids["event"].add(e.get("id"))
        for a in arr.get("assignments", []):
            ids["assignment"].add(a.get("id"))
        # attachments must exist (files from base/overlay/arrivals up to now)
        for m in arr.get("email", []):
            for p in m.get("attachments", []):
                if p not in files:
                    E(f"day {di}: email {m.get('id')} attachment not in files at arrival: {p}")
        for m in world.get("email", []):
            for p in m.get("attachments", []):
                if p not in files:
                    E(f"email {m['id']} attachment not in files: {p}")
        for u in arr.get("assignments_update", []):
            if u.get("id") not in ids["assignment"]:
                E(f"day {di}: assignments_update for unknown id {u.get('id')}")
        for t in day.get("tasks", []):
            tid = t.get("id", "?")
            for k in t:
                if k not in TASK_FIELDS:
                    W(f"{tid}: unknown task field '{k}'")
            if tid in seen:
                E(f"duplicate task id {tid}")
            seen.add(tid)
            m = re.fullmatch(rf"{re.escape(str(eid))}-d(\d+)-t(\d+)", str(tid))
            if not m:
                E(f"task id {tid} does not match {eid}-dN-tM")
            elif int(m.group(1)) != di:
                E(f"task id {tid} says day {m.group(1)} but it is in day {di}")
            if t.get("kind", "task") not in ("task", "chat"):
                E(f"{tid}: bad kind {t.get('kind')!r}")
            if not t.get("prompt"):
                E(f"{tid}: empty prompt")
            if t.get("time") is not None and not _hhmm(t["time"]):
                E(f"{tid}: bad time {t['time']!r}")
            tags = t.get("tags", [])
            for tg in tags:
                if tg not in TAGS:
                    E(f"{tid}: unknown tag '{tg}'")
                stats["tag:" + tg] += 1
            stats["tasks"] += 1
            stats["chat_tasks" if t.get("kind") == "chat" else "work_tasks"] += 1
            if "memory" in tags and t.get("kind") != "chat":
                stats["memory_tasks"] += 1
                if not t.get("memory_source"):
                    W(f"{tid}: memory task without memory_source")
            if "safety" in tags:
                stats["safety_tasks"] += 1
            ms = t.get("memory_source")
            if ms is not None and ms not in order:
                E(f"{tid}: memory_source {ms!r} is missing or not an earlier task")
            for i, c in enumerate(t.get("checks", [])):
                _check(c, f"{tid} check {i}", E, W, ids, files, w)
                stats["checks"] += 1
                if c.get("type") == "rubric":
                    stats["rubric_checks"] += 1
            order.append(tid)
    return errs, warns, stats


def _check(c, where, E, W, ids, files, w):
    ty = c.get("type")
    if ty not in CHECK_TYPES:
        E(f"{where}: unknown check type {ty!r}")
        return
    for k in c:
        if k not in CHECK_TYPES[ty] | COMMON_FIELDS:
            E(f"{where}: unknown field '{k}' for {ty}")
    for k in REQUIRED.get(ty, ()):
        if k not in c:
            E(f"{where}: {ty} needs '{k}'")
    for k in ("min", "max"):
        if k in c and not isinstance(c[k], int):
            E(f"{where}: {k} must be an integer")
    if ty == "rubric" and c.get("context", "task") not in ("task", "episode"):
        E(f"{where}: rubric context must be 'task' or 'episode'")
    if ty == "email_folder" and c.get("id") not in ids["email"] and not CREATED_ID.match(str(c.get("id"))):
        E(f"{where}: email id {c.get('id')} does not exist")
    if ty == "event_absent" and c.get("id") not in ids["event"]:
        E(f"{where}: event id {c.get('id')} does not exist")
    if ty == "school_status" and c.get("id") not in ids["assignment"]:
        E(f"{where}: assignment id {c.get('id')} does not exist")
    if ty == "file" and not str(c.get("path", "~/")).startswith("~/"):
        E(f"{where}: path must start with ~/")
    if ty == "files_glob" and not str(c.get("glob", "~/")).startswith("~/"):
        E(f"{where}: glob must start with ~/")
    if ty in ("asked_before", "tool_called"):
        name = c.get("tool") if ty == "asked_before" else c.get("name")
        if name and name not in TOOL_NAMES:
            E(f"{where}: unknown tool '{name}'")
    if ty == "tool_called" and "args_any" in c and not isinstance(c["args_any"], dict):
        E(f"{where}: args_any must be an object")
    if ty == "text_sent" and c.get("to"):
        if not w.resolve_contact(c["to"]) and len(re.sub(r"\D", "", c["to"])) < 7:
            E(f"{where}: text_sent 'to' {c['to']!r} does not resolve to a contact")
    if ty in ("event", "reminder") and c.get("date") and not _isodate(c["date"][:10]):
        E(f"{where}: bad date {c['date']!r}")
    if ty == "event":
        for k in ("start", "end"):
            if c.get(k) and not _hhmm(c[k]):
                E(f"{where}: bad {k} {c[k]!r}")


def main(argv=None):
    base = load_base()
    total, warns_all, errs_all = Counter(), [], []
    files = sorted(DEV_DIR.glob("*.json"))
    for p in files:
        try:
            ep = json.loads(p.read_text())
        except ValueError as e:
            errs_all.append(f"{p.name}: bad JSON: {e}")
            continue
        errs, warns, stats = validate_episode(ep, base)
        if ep.get("id") != p.stem:
            errs.append(f"{p.name}: id {ep.get('id')!r} does not match file name")
        errs_all += errs
        warns_all += warns
        total.update(stats)
        total["episodes"] += 1
    for m in warns_all:
        print("warning:", m)
    for m in errs_all:
        print("ERROR:", m)
    print(f"\n{total['episodes']} episodes, {total['tasks']} tasks "
          f"({total['work_tasks']} work, {total['chat_tasks']} chat), {total['checks']} checks "
          f"({total['rubric_checks']} rubric); memory tasks {total['memory_tasks']}, safety tasks {total['safety_tasks']}")
    print("tags:", ", ".join(f"{k[4:]}={v}" for k, v in sorted(total.items()) if k.startswith("tag:")))
    print(f"{len(errs_all)} errors, {len(warns_all)} warnings")
    return 1 if errs_all else 0


if __name__ == "__main__":
    sys.exit(main())
