"""Sandboxed fake world for the Ben's Week benchmark: state, tools, shell."""
import copy
import fnmatch
import json
import posixpath
import re
import shlex
from datetime import date, datetime, timedelta
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
BASE_PATH = PKG_DIR / "world" / "base.json"
WEEK_START = date(2026, 11, 2)
WEEK_DAYS = [(WEEK_START + timedelta(days=i)).isoformat() for i in range(7)]
MAX_OUT = 8000
MEMORY_MODES = ("none", "notes", "diary", "context")


# ---------------------------------------------------------------- loading

def load_base():
    return json.loads(BASE_PATH.read_text())


def merge_world(base, overlay):
    """Overlay onto base: lists appended, dicts merged, files merged."""
    out = copy.deepcopy(base)
    overlay = copy.deepcopy(overlay or {})
    rm_email = set(overlay.pop("remove_email", []))
    rm_files = overlay.pop("remove_files", [])
    _merge_into(out, overlay)
    out["email"] = [m for m in out.get("email", []) if m.get("id") not in rm_email]
    for p in rm_files:
        out.get("files", {}).pop(p, None)
    return out


def _merge_into(dst, src):
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
        elif isinstance(v, dict) and isinstance(dst[k], dict):
            _merge_into(dst[k], v)
        elif isinstance(v, list) and isinstance(dst[k], list):
            dst[k] = dst[k] + v
        else:
            dst[k] = v


def parse_dt(date_s, time_s="00:00"):
    return datetime.strptime(f"{date_s} {time_s}", "%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- tool schemas

def _schema(props, required=()):
    out = {}
    for name, (kind, desc) in props.items():
        if kind == "as":
            out[name] = {"type": "array", "items": {"type": "string"}, "description": desc}
        elif kind == "o":
            out[name] = {"type": "object", "description": desc}
        else:
            t = {"s": "string", "b": "boolean", "i": "integer"}[kind]
            out[name] = {"type": t, "description": desc}
    return {"type": "object", "properties": out, "required": list(required)}


_S = "s"
TOOL_SPECS = [
    ("email_search", "Search email. Empty query = newest 20.",
     {"query": (_S, ""), "folder": (_S, "inbox|sent|drafts|archive|trash|all"), "unread_only": ("b", "")}, []),
    ("email_read", "Read one email by id.", {"id": (_S, "")}, ["id"]),
    ("email_send", "Send an email.",
     {"to": ("as", "addresses or contact names"), "subject": (_S, ""), "body": (_S, ""), "cc": ("as", ""),
      "reply_to_id": (_S, ""), "attachments": ("as", "file paths")}, ["to", "subject", "body"]),
    ("email_draft", "Save an email draft (not sent).",
     {"to": ("as", ""), "subject": (_S, ""), "body": (_S, ""), "cc": ("as", ""),
      "reply_to_id": (_S, ""), "attachments": ("as", "file paths")}, ["to", "subject", "body"]),
    ("email_move", "Move an email to a folder.", {"id": (_S, ""), "folder": (_S, "inbox|archive|trash")}, ["id", "folder"]),
    ("calendar_list", "List calendar events in a date range.",
     {"start_date": (_S, "YYYY-MM-DD"), "end_date": (_S, "YYYY-MM-DD")}, ["start_date", "end_date"]),
    ("calendar_create", "Create a calendar event.",
     {"title": (_S, ""), "date": (_S, "YYYY-MM-DD"), "start": (_S, "HH:MM"), "end": (_S, "HH:MM"),
      "location": (_S, ""), "notes": (_S, "")}, ["title", "date", "start", "end"]),
    ("calendar_update", "Edit an event.", {"id": (_S, ""), "fields": ("o", "fields to change")}, ["id", "fields"]),
    ("calendar_delete", "Delete an event.", {"id": (_S, "")}, ["id"]),
    ("files_list", "List a folder.", {"path": (_S, "~/..."), "recursive": ("b", "")}, ["path"]),
    ("files_read", "Read a text file.", {"path": (_S, "")}, ["path"]),
    ("files_write", "Create or overwrite a file.", {"path": (_S, ""), "content": (_S, "")}, ["path", "content"]),
    ("files_move", "Move or rename a file.", {"src": (_S, ""), "dst": (_S, "path or folder/")}, ["src", "dst"]),
    ("files_delete", "Delete a file (goes to ~/.Trash).", {"path": (_S, "")}, ["path"]),
    ("files_search", "Find files by name or content.", {"query": (_S, "")}, ["query"]),
    ("shell", "Run a simple shell command on Ben's files (ls cat head tail wc grep find mkdir mv cp rm touch du sort echo, pipes).",
     {"command": (_S, "")}, ["command"]),
    ("web_search", "Search the web (top 5).", {"query": (_S, "")}, ["query"]),
    ("web_open", "Open a web page.", {"url": (_S, "")}, ["url"]),
    ("school_list", "List school assignments.", {"course": (_S, "course id or name"), "status": (_S, "not_started|submitted|graded")}, []),
    ("school_read", "Read one assignment.", {"id": (_S, "")}, ["id"]),
    ("texts_read", "Read recent text messages.", {"with": (_S, "name or phone")}, []),
    ("text_send", "Send a text message.", {"to": (_S, "name or phone"), "body": (_S, "")}, ["to", "body"]),
    ("reminders_create", "Create a reminder.", {"text": (_S, ""), "when": (_S, "ISO date-time")}, ["text", "when"]),
    ("reminders_list", "List reminders.", {}, []),
    ("notes_read", "Read your notebook.", {}, []),
    ("notes_write", "Replace your notebook with this text.", {"content": (_S, "")}, ["content"]),
    ("ask_user", "Ask Ben a question and wait for the answer.", {"question": (_S, "")}, ["question"]),
    ("diary_search", "Search your past chats this week.", {"query": (_S, "")}, ["query"]),
    ("contacts_search", "Find Ben's contacts (name, email, phone, relation). Empty query = all.", {"query": (_S, "")}, []),
]
NOTES_TOOLS = {"notes_read", "notes_write"}
CHANGING = {"email_send", "email_draft", "email_move", "calendar_create", "calendar_update",
            "calendar_delete", "files_write", "files_move", "files_delete", "text_send", "reminders_create"}
SHELL_MUTATE = re.compile(r"(^|[\s;|&])(rm|mv|cp|mkdir|touch)\b|>")


def tool_schemas(memory="none"):
    out = []
    for name, desc, props, req in TOOL_SPECS:
        if name in NOTES_TOOLS and memory not in ("notes", "diary", "context"):
            continue
        if name == "diary_search" and memory != "diary":
            continue
        out.append({"type": "function", "function": {"name": name, "description": desc,
                                                       "parameters": _schema(props, req)}})
    return out


def is_state_changing(name, args):
    if name in CHANGING:
        return True
    if name == "shell":
        return bool(SHELL_MUTATE.search(str((args or {}).get("command", ""))))
    return False


class ShellError(Exception):
    pass


def _j(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _as_list(v):
    if v is None or v == "":
        return []
    if isinstance(v, str):
        return [v]
    return list(v)


def _digits(s):
    return re.sub(r"\D", "", s or "")


def _human(n):
    for unit in ("B", "K", "M", "G"):
        if n < 1024 or unit == "G":
            return f"{n}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024


# ---------------------------------------------------------------- world

class World:
    def __init__(self, data, memory="none"):
        d = copy.deepcopy(data)
        self.memory = memory
        self.profile = d.get("profile", {})
        self.contacts = d.get("contacts", [])
        self.email = d.get("email", [])
        self.calendar = d.get("calendar", [])
        self.files = d.get("files", {})
        for p, f in self.files.items():
            f.setdefault("size", len(f.get("content", "")))
            f.setdefault("mtime", "2026-09-01T00:00")
        self.dirs = set()
        self.web = d.get("web", {})
        school = d.get("school", {})
        self.courses = school.get("courses", [])
        self.assignments = school.get("assignments", [])
        self.texts = d.get("texts", [])
        self.reminders = d.get("reminders", [])
        self.notes = d.get("notes", "") or ""
        self.now = parse_dt(WEEK_START.isoformat(), "08:00")
        self.sent_log = []          # {"kind": sent|draft, "task": id, "email": {...}}
        self.log = []               # every tool call
        self.diary = []             # {"date","time","task","user","assistant"}
        self.counters = {}
        self.task_id = None
        self.asks = 0
        self.ask_reply = "up to you, use your best judgment"
        self.has_ask_reply = False

    # -- state dump / restore (resume, snapshots)
    STATE_KEYS = ["profile", "contacts", "email", "calendar", "files", "web", "courses", "assignments",
                  "texts", "reminders", "notes", "sent_log", "counters"]

    def snapshot(self):
        s = {k: copy.deepcopy(getattr(self, k)) for k in self.STATE_KEYS}
        s["dirs"] = sorted(self.dirs)
        s["now"] = self.iso_now()
        return s

    def restore(self, s):
        for k in self.STATE_KEYS:
            setattr(self, k, copy.deepcopy(s[k]))
        self.dirs = set(s.get("dirs", []))
        self.now = datetime.strptime(s["now"], "%Y-%m-%dT%H:%M")

    # -- clock / arrivals / tasks
    def iso_now(self):
        return self.now.strftime("%Y-%m-%dT%H:%M")

    def set_time(self, date_s, time_s):
        self.now = parse_dt(date_s, time_s)

    def apply_arrivals(self, arr):
        arr = copy.deepcopy(arr or {})
        for m in arr.pop("email", []):
            m.setdefault("folder", "inbox")
            m.setdefault("unread", True)
            m.setdefault("cc", [])
            m.setdefault("attachments", [])
            self.email.append(m)
        for t in arr.pop("texts", []):
            self.texts.append(t)
        self.calendar += arr.pop("calendar", [])
        for p, f in arr.pop("files", {}).items():
            f.setdefault("size", len(f.get("content", "")))
            f.setdefault("mtime", self.iso_now())
            self.files[p] = f
        self.assignments += arr.pop("assignments", [])
        for patch in arr.pop("assignments_update", []):
            for a in self.assignments:
                if a["id"] == patch.get("id"):
                    a.update({k: v for k, v in patch.items() if k != "id"})
        self.web.update(arr.pop("web", {}))
        for k, v in arr.items():           # contacts, reminders, ... generic lists
            cur = getattr(self, k, None)
            if isinstance(cur, list) and isinstance(v, list):
                cur += v

    def begin_task(self, task_id, ask_reply=None):
        self.task_id = task_id
        self.asks = 0
        self.has_ask_reply = bool(ask_reply)
        self.ask_reply = ask_reply or "up to you, use your best judgment"

    def next_id(self, prefix):
        self.counters[prefix] = self.counters.get(prefix, 0) + 1
        return f"{prefix}{self.counters[prefix]:03d}"

    # -- tool dispatch
    def tools(self):
        return tool_schemas(self.memory)

    def execute(self, name, args):
        allowed = {t["function"]["name"] for t in self.tools()}
        if not isinstance(args, dict):
            args = {}
        try:
            if name not in allowed:
                out = f"error: unknown tool '{name}'"
            else:
                out = getattr(self, "t_" + name)(args)
        except ShellError as e:
            out = f"error: {e}"
        except Exception as e:  # tools never crash the run
            out = f"error: {type(e).__name__}: {e}"
        if not isinstance(out, str):
            out = _j(out)
        if len(out) > MAX_OUT:
            out = out[:MAX_OUT] + f"\n...(truncated, {len(out)} chars)"
        self.log.append({"task": self.task_id, "ts": self.iso_now(), "name": name, "args": args, "result": out})
        return out

    # -- contacts
    def resolve_contact(self, s):
        s = (s or "").strip()
        if not s:
            return None
        dg = _digits(s)
        if len(dg) >= 7:
            for c in self.contacts:
                if _digits(c.get("phone")).endswith(dg[-7:]) and c.get("phone"):
                    return c
        low = s.lower()
        for c in self.contacts:
            if c["name"].lower() == low or c.get("email", "").lower() == low:
                return c
        hits = [c for c in self.contacts if low in c["name"].lower()]
        return hits[0] if len(hits) == 1 else None

    def t_contacts_search(self, a):
        q = (a.get("query") or "").strip().lower()
        hits = [c for c in self.contacts
                if not q or any(q in (c.get(k) or "").lower() for k in ("name", "email", "phone", "relation"))]
        return _j(hits) if hits else "no matching contacts"

    def contact_by_phone(self, phone):
        for c in self.contacts:
            if c.get("phone") and _digits(c["phone"]) == _digits(phone):
                return c

    # -- email
    def _find_email(self, mid):
        for m in self.email:
            if m["id"] == mid:
                return m
        raise ValueError(f"no email with id {mid}")

    def t_email_search(self, a):
        words = (a.get("query") or "").lower().split()
        folder = (a.get("folder") or "all").lower()
        rows = []
        for m in self.email:
            if folder == "all":
                if m["folder"] == "trash":
                    continue
            elif m["folder"] != folder:
                continue
            if a.get("unread_only") and not m.get("unread"):
                continue
            hay = " ".join([m.get("subject", ""), m.get("from", ""), " ".join(m.get("to", [])), m.get("body", "")]).lower()
            if all(w in hay for w in words):
                rows.append(m)
        rows.sort(key=lambda m: m.get("date", ""), reverse=True)
        return [{"id": m["id"], "folder": m["folder"], "from": m.get("from"), "to": m.get("to"),
                 "subject": m.get("subject"), "date": m.get("date"), "unread": bool(m.get("unread")),
                 "snippet": m.get("body", "")[:100].replace("\n", " ")} for m in rows[:20]]

    def t_email_read(self, a):
        m = self._find_email(a.get("id"))
        m["unread"] = False
        return {k: m.get(k) for k in ("id", "folder", "from", "to", "cc", "date", "subject", "body", "attachments")}

    def _compose(self, a, kind):
        def addrs(v):
            out = []
            for x in _as_list(v):
                if "@" in x:
                    out.append(x.strip())
                else:
                    c = self.resolve_contact(x)
                    if not c or not c.get("email"):
                        raise ValueError(f"cannot resolve recipient '{x}' to an email address")
                    out.append(c["email"])
            return out
        to, cc = addrs(a.get("to")), addrs(a.get("cc"))
        if not to:
            raise ValueError("no recipients")
        atts = []
        for p in _as_list(a.get("attachments")):
            p = self.norm(p)
            if p not in self.files:
                raise ValueError(f"attachment not found: {p}")
            atts.append(p)
        if a.get("reply_to_id"):
            self._find_email(a["reply_to_id"])
        prefix = "s" if kind == "sent" else "d"
        m = {"id": self.next_id(prefix), "folder": "sent" if kind == "sent" else "drafts",
             "from": self.profile.get("email", "ben@lakeview.test"), "to": to, "cc": cc, "date": self.iso_now(),
             "subject": a.get("subject", ""), "body": a.get("body", ""), "attachments": atts,
             "unread": False, "reply_to": a.get("reply_to_id") or None}
        self.email.append(m)
        self.sent_log.append({"kind": kind, "task": self.task_id, "email": copy.deepcopy(m)})
        return m

    def t_email_send(self, a):
        m = self._compose(a, "sent")
        return f"sent email {m['id']} to {', '.join(m['to'])}"

    def t_email_draft(self, a):
        m = self._compose(a, "draft")
        return f"saved draft {m['id']}"

    def t_email_move(self, a):
        folder = (a.get("folder") or "").lower()
        if folder not in ("inbox", "archive", "trash", "sent", "drafts"):
            raise ValueError("folder must be inbox, archive or trash")
        m = self._find_email(a.get("id"))
        m["folder"] = folder
        return f"moved {m['id']} to {folder}"

    # -- calendar
    def occurrences(self, ev):
        d0 = date.fromisoformat(ev["date"])
        rep = ev.get("repeat") or "none"
        if rep == "none":
            return [ev["date"]]
        out = []
        for ds in WEEK_DAYS:
            d = date.fromisoformat(ds)
            if d < d0:
                continue
            if rep == "daily" or (rep == "weekdays" and d.weekday() < 5) or \
               (rep == "weekly" and (d - d0).days % 7 == 0):
                out.append(ds)
        return out

    def event_instances(self):
        rows = []
        for ev in self.calendar:
            for ds in self.occurrences(ev):
                rows.append({"id": ev["id"], "title": ev.get("title", ""), "date": ds, "start": ev.get("start", ""),
                             "end": ev.get("end", ""), "location": ev.get("location", ""), "notes": ev.get("notes", ""),
                             "repeat": ev.get("repeat", "none")})
        rows.sort(key=lambda r: (r["date"], r["start"]))
        return rows

    def t_calendar_list(self, a):
        s = a.get("start_date") or WEEK_DAYS[0]
        e = a.get("end_date") or s
        date.fromisoformat(s), date.fromisoformat(e)
        return [r for r in self.event_instances() if s <= r["date"] <= e]

    @staticmethod
    def _check_time(t):
        datetime.strptime(t, "%H:%M")

    def t_calendar_create(self, a):
        date.fromisoformat(a["date"])
        self._check_time(a["start"]), self._check_time(a["end"])
        ev = {"id": self.next_id("n"), "title": a["title"], "date": a["date"], "start": a["start"], "end": a["end"],
              "location": a.get("location", ""), "notes": a.get("notes", ""), "repeat": "none"}
        self.calendar.append(ev)
        return f"created event {ev['id']}"

    def t_calendar_update(self, a):
        fields = a.get("fields") or {}
        for ev in self.calendar:
            if ev["id"] == a.get("id"):
                for k, v in fields.items():
                    if k not in ("title", "date", "start", "end", "location", "notes", "repeat"):
                        raise ValueError(f"cannot edit field '{k}'")
                    ev[k] = v
                date.fromisoformat(ev["date"])
                self._check_time(ev["start"]), self._check_time(ev["end"])
                return f"updated event {ev['id']}"
        raise ValueError(f"no event with id {a.get('id')}")

    def t_calendar_delete(self, a):
        for ev in self.calendar:
            if ev["id"] == a.get("id"):
                self.calendar.remove(ev)
                return f"deleted event {a['id']}"
        raise ValueError(f"no event with id {a.get('id')}")

    # -- files
    @staticmethod
    def norm(p, cwd="~"):
        p = (p or "").strip()
        if p.startswith("/Users/ben"):
            p = "~" + p[len("/Users/ben"):]
        elif p.startswith("$HOME"):
            p = "~" + p[len("$HOME"):]
        if p == "":
            p = cwd
        if not (p.startswith("~") or p.startswith("/")):
            p = cwd + "/" + p
        if p.startswith("~") and not p.startswith("~/") and p != "~":
            raise ShellError(f"unsupported path: {p}")
        r = posixpath.normpath(p)
        if r.startswith("//"):
            r = r[1:]
        if not (r == "~" or r.startswith("~/") or r.startswith("/")):
            r = "~"
        return r

    def is_dir(self, p):
        if p == "~" or p in self.dirs:
            return True
        pre = p + "/"
        return any(k.startswith(pre) for k in self.files) or any(d.startswith(pre) for d in self.dirs)

    def exists(self, p):
        return p in self.files or self.is_dir(p)

    def children(self, d):
        pre = d + "/"
        out = {}
        for k in list(self.files) + list(self.dirs):
            if k.startswith(pre):
                rest = k[len(pre):]
                name = rest.split("/")[0]
                out[name] = out.get(name, False) or ("/" in rest) or (k in self.dirs)
        return dict(sorted(out.items()))

    def tree_files(self, p):
        pre = p + "/"
        return sorted(k for k in self.files if k.startswith(pre))

    def all_paths(self):
        s = set(self.files) | set(self.dirs)
        for k in list(s):
            while "/" in k:
                k = k.rsplit("/", 1)[0]
                s.add(k)
        return s

    def glob(self, pattern):
        """Path glob; '*' stays inside one folder, '**' matches zero or more folders."""
        parts = pattern.split("/")

        def match(ps, qs):
            if not qs:
                return not ps
            if qs[0] == "**":
                return any(match(ps[i:], qs[1:]) for i in range(len(ps) + 1))
            return bool(ps) and fnmatch.fnmatchcase(ps[0], qs[0]) and match(ps[1:], qs[1:])
        return [p for p in sorted(self.all_paths()) if match(p.split("/"), parts)]

    def _finfo(self, p):
        f = self.files[p]
        return f"{f['size']} B  {f['mtime'].replace('T', ' ')}"

    def t_files_list(self, a):
        p = self.norm(a.get("path"))
        if p in self.files:
            return f"{p}  {self._finfo(p)}"
        if not self.is_dir(p):
            raise ValueError(f"no such folder: {p}")
        lines = []
        if a.get("recursive"):
            for k in self.tree_files(p) if p != "~" else sorted(self.files):
                lines.append(f"{k[len(p) + 1:]}  {self._finfo(k)}")
        else:
            for name, isdir in self.children(p).items():
                full = p + "/" + name
                lines.append(f"{name}/" if isdir else f"{name}  {self._finfo(full)}")
        return "\n".join(lines) or "(empty)"

    def t_files_read(self, a):
        p = self.norm(a.get("path"))
        if p not in self.files:
            raise ValueError(f"no such file: {p}" + (" (it is a folder)" if self.is_dir(p) else ""))
        return self.files[p]["content"]

    def _put(self, p, content):
        self.files[p] = {"content": content, "size": len(content.encode()), "mtime": self.iso_now()}

    def t_files_write(self, a):
        p = self.norm(a.get("path"))
        if self.is_dir(p):
            raise ValueError(f"{p} is a folder")
        self._put(p, a.get("content", ""))
        return f"wrote {p} ({self.files[p]['size']} bytes)"

    def _move(self, src, dst, raw_dst=""):
        if not self.exists(src):
            raise ShellError(f"no such file or folder: {src}")
        into = self.is_dir(dst) or raw_dst.endswith("/")
        target = dst + "/" + posixpath.basename(src) if into else dst
        if target == src:
            return target
        if src in self.files:
            self.files[target] = self.files.pop(src)
        else:
            if target.startswith(src + "/"):
                raise ShellError("cannot move a folder into itself")
            for k in self.tree_files(src):
                self.files[target + k[len(src):]] = self.files.pop(k)
            for d in [d for d in self.dirs if d == src or d.startswith(src + "/")]:
                self.dirs.discard(d)
                self.dirs.add(target + d[len(src):])
            self.dirs.add(target)
        return target

    def t_files_move(self, a):
        src, dst = self.norm(a.get("src")), self.norm(a.get("dst"))
        t = self._move(src, dst, a.get("dst", ""))
        return f"moved to {t}"

    def _trash(self, p):
        if p.startswith("~/.Trash/") or p == "~/.Trash":
            for k in self.tree_files(p) + ([p] if p in self.files else []):
                self.files.pop(k, None)
            return
        base = "~/.Trash/" + posixpath.basename(p)
        t, i = base, 1
        while self.exists(t):
            i += 1
            t = f"{base} {i}"
        self._move(p, t)

    def t_files_delete(self, a):
        p = self.norm(a.get("path"))
        if p not in self.files:
            raise ValueError(f"no such file: {p}")
        self._trash(p)
        return f"moved {p} to ~/.Trash"

    def t_files_search(self, a):
        q = (a.get("query") or "").lower()
        hits = [p for p, f in sorted(self.files.items())
                if q in posixpath.basename(p).lower() or q in f.get("content", "").lower()]
        return "\n".join(hits[:30]) or "(no matches)"

    # -- web
    def t_web_search(self, a):
        words = (a.get("query") or "").lower().split()
        scored = []
        for url, pg in self.web.items():
            hay = (url + " " + pg.get("title", "") + " " + pg.get("content", "")).lower()
            n = sum(hay.count(w) for w in words)
            if n and all(w in hay for w in words[:1]):
                scored.append((n, url, pg))
        scored.sort(key=lambda x: -x[0])
        out = []
        for n, url, pg in scored[:5]:
            c = pg.get("content", "")
            i = max(c.lower().find(words[0]), 0) if words else 0
            out.append({"url": url, "title": pg.get("title", ""), "snippet": c[max(i - 40, 0): i + 160]})
        return out or "no results"

    def t_web_open(self, a):
        u = (a.get("url") or "").strip().rstrip("/").lower()
        for url, pg in self.web.items():
            if url.rstrip("/").lower() == u:
                return f"{pg.get('title', '')}\n\n{pg.get('content', '')}"
        return "404 page not found"

    # -- school
    def _course_ids(self, q):
        q = q.lower()
        return {c["id"] for c in self.courses if q == c["id"].lower() or q in c["name"].lower()
                or q in c.get("teacher", "").lower()}

    def t_school_list(self, a):
        ids = self._course_ids(a["course"]) if a.get("course") else None
        rows = [x for x in self.assignments if (ids is None or x["course"] in ids)
                and (not a.get("status") or x.get("status") == a["status"])]
        rows.sort(key=lambda x: x.get("due", ""))
        return [{k: x.get(k) for k in ("id", "course", "title", "due", "points", "status", "grade")} for x in rows]

    def t_school_read(self, a):
        for x in self.assignments:
            if x["id"] == a.get("id"):
                return x
        raise ValueError(f"no assignment with id {a.get('id')}")

    # -- texts
    def _text_row(self, t):
        c = self.contact_by_phone(t["with"])
        return {"id": t.get("id"), "with": t["with"], "name": c["name"] if c else "", "from_me": t["from_me"],
                "date": t["date"], "body": t["body"]}

    def t_texts_read(self, a):
        rows = self.texts
        if a.get("with"):
            c = self.resolve_contact(a["with"])
            phone = c["phone"] if c else a["with"]
            rows = [t for t in rows if _digits(t["with"]) == _digits(phone)]
        rows = sorted(rows, key=lambda t: t["date"])[-20:]
        return [self._text_row(t) for t in rows]

    def t_text_send(self, a):
        to = a.get("to", "")
        c = self.resolve_contact(to)
        if c and c.get("phone"):
            phone = c["phone"]
        elif len(_digits(to)) >= 7:
            phone = to
        else:
            raise ValueError(f"cannot find a phone number for '{to}'")
        t = {"id": self.next_id("x"), "with": phone, "from_me": True, "date": self.iso_now(),
             "body": a.get("body", ""), "task": self.task_id}
        self.texts.append(t)
        return f"text sent to {c['name'] if c else phone}"

    # -- reminders / notes / ask / diary
    def t_reminders_create(self, a):
        when = a.get("when", "")
        try:
            datetime.fromisoformat(when)
        except ValueError:
            raise ValueError("'when' must be an ISO date-time like 2026-11-04T18:00")
        self.reminders.append({"id": self.next_id("r"), "text": a.get("text", ""), "when": when, "task": self.task_id})
        return "reminder created"

    def t_reminders_list(self, a):
        return self.reminders or "(none)"

    def t_notes_read(self, a):
        return self.notes or "(empty)"

    def t_notes_write(self, a):
        self.notes = a.get("content", "")
        return "notes saved"

    def t_ask_user(self, a):
        if self.asks >= 2:
            return "Ben is busy and cannot answer more questions. Use your best judgment."
        self.asks += 1
        return self.ask_reply

    def t_diary_search(self, a):
        words = (a.get("query") or "").lower().split()
        hits = []
        for e in self.diary:
            hay = (e["user"] + " " + e["assistant"]).lower()
            if all(w in hay for w in words):
                hits.append(f"[{e['date']} {e['time']}] Ben: {e['user'][:300]}\nAssistant: {e['assistant'][:300]}")
        return "\n---\n".join(hits[-5:]) or "(nothing found)"

    # -- shell
    def t_shell(self, a):
        cmd = a.get("command", "")
        if not isinstance(cmd, str) or not cmd.strip():
            raise ValueError("empty command")
        lex = shlex.shlex(cmd, posix=True, punctuation_chars="|<>;&")
        lex.whitespace_split = True
        try:
            toks = list(lex)
        except ValueError as e:
            raise ShellError(f"parse error: {e}")
        state = {"cwd": "~"}
        outs, seq, i = [], [], 0
        groups, cur = [], []
        for t in toks + [";"]:
            if t in (";", "&&", "&"):
                if cur:
                    groups.append((cur, t))
                cur = []
            else:
                cur.append(t)
        for stage_toks, sep in groups:
            try:
                out = self._pipeline(stage_toks, state)
                if out:
                    outs.append(out.rstrip("\n"))
            except ShellError as e:
                outs.append(str(e))
                if sep == "&&":
                    break
        return "\n".join(outs) or "(no output)"

    def _pipeline(self, toks, state):
        stages, cur = [], []
        for t in toks:
            if t == "|":
                stages.append(cur)
                cur = []
            else:
                cur.append(t)
        stages.append(cur)
        data = None
        for st in stages:
            args, redir, rin = [], None, None
            j = 0
            while j < len(st):
                t = st[j]
                if t in (">", ">>") and j + 1 < len(st):
                    redir = (t, st[j + 1])
                    j += 2
                elif t == "<" and j + 1 < len(st):
                    rin = st[j + 1]
                    j += 2
                elif t == "2" and j + 1 < len(st) and st[j + 1] == ">":
                    j += 3
                elif t == ">&" or t == "&>":
                    j += 2
                else:
                    args.append(t)
                    j += 1
            if not args:
                raise ShellError("syntax error near unexpected token")
            if rin:
                p = self.norm(rin, state["cwd"])
                if p not in self.files:
                    raise ShellError(f"{rin}: No such file or directory")
                data = self.files[p]["content"]
            out = self._run_cmd(args[0], args[1:], data, state)
            if redir:
                op, target = redir
                if target != "/dev/null":
                    p = self.norm(target, state["cwd"])
                    if self.is_dir(p):
                        raise ShellError(f"{target}: Is a directory")
                    old = self.files[p]["content"] if (op == ">>" and p in self.files) else ""
                    self._put(p, old + out)
                out = ""
            data = out
        return data

    def _expand(self, args, cwd):
        out = []
        for a in args:
            if any(ch in a for ch in "*?["):
                hits = self.glob(self.norm(a, cwd))
                out += hits if hits else [a]
            else:
                out.append(a)
        return out

    @staticmethod
    def _split_opts(args):
        opts, rest = "", []
        for a in args:
            if len(a) > 1 and a[0] == "-" and not a[1:].isdigit():
                opts += a[1:]
            else:
                rest.append(a)
        return opts, rest

    def _read_in(self, files, stdin, cwd, cmd):
        """Return list of (name, text) for file args, or stdin."""
        if not files:
            return [("-", stdin or "")]
        out = []
        for f in files:
            p = self.norm(f, cwd)
            if p in self.files:
                out.append((f, self.files[p]["content"]))
            elif self.is_dir(p):
                out.append((f, None))
            else:
                out.append((f, False))
        return out

    def _run_cmd(self, cmd, args, stdin, state):
        cwd = state["cwd"]
        fn = getattr(self, "sh_" + cmd, None)
        if fn is None:
            raise ShellError(f"bash: {cmd}: command not found")
        return fn(args, stdin, state) or ""

    def sh_pwd(self, args, stdin, st):
        return st["cwd"] + "\n"

    def sh_cd(self, args, stdin, st):
        p = self.norm(args[0] if args else "~", st["cwd"])
        if not self.is_dir(p):
            raise ShellError(f"cd: {args[0]}: No such file or directory")
        st["cwd"] = p
        return ""

    def sh_date(self, args, stdin, st):
        return self.now.strftime("%a %b %d %H:%M:%S 2026") + "\n"

    def sh_echo(self, args, stdin, st):
        return " ".join(args) + "\n"

    def sh_ls(self, args, stdin, st):
        opts, rest = self._split_opts(args)
        rest = self._expand(rest or ["."], st["cwd"])
        lines = []
        for r in rest:
            p = self.norm(r, st["cwd"])
            if not self.exists(p):
                lines.append(f"ls: {r}: No such file or directory")
                continue
            if len(rest) > 1 and self.is_dir(p):
                lines.append(f"{r}:")
            entries = [(posixpath.basename(p), p, False)] if p in self.files else \
                [(n, p + "/" + n, d) for n, d in self.children(p).items()]
            for n, full, isdir in entries:
                if n.startswith(".") and "a" not in opts:
                    continue
                if "l" in opts:
                    if isdir:
                        lines.append(f"drwxr-xr-x  ben  -  {n}/")
                    else:
                        f = self.files[full]
                        sz = _human(f["size"]) if "h" in opts else f["size"]
                        lines.append(f"-rw-r--r--  ben  {sz}  {f['mtime'].replace('T', ' ')}  {n}")
                else:
                    lines.append(n + ("/" if isdir else ""))
        return "\n".join(lines) + "\n"

    def sh_cat(self, args, stdin, st):
        res = []
        for name, txt in self._read_in(self._expand(args, st["cwd"]), stdin, st["cwd"], "cat"):
            if txt is False:
                raise ShellError(f"cat: {name}: No such file or directory")
            if txt is None:
                raise ShellError(f"cat: {name}: Is a directory")
            res.append(txt)
        return "\n".join(r.rstrip("\n") for r in res) + "\n"

    def _headtail(self, args, stdin, st, tail):
        n, files, i = 10, [], 0
        while i < len(args):
            a = args[i]
            if a == "-n" and i + 1 < len(args):
                n = int(args[i + 1].lstrip("+"))
                i += 2
                continue
            if a.startswith("-n"):
                n = int(a[2:])
            elif a[0] == "-" and a[1:].isdigit():
                n = int(a[1:])
            else:
                files.append(a)
            i += 1
        out = []
        for name, txt in self._read_in(self._expand(files, st["cwd"]), stdin, st["cwd"], "head"):
            if txt is False:
                raise ShellError(f"{name}: No such file or directory")
            lines = (txt or "").split("\n")
            if lines and lines[-1] == "":
                lines.pop()
            out += (lines[-n:] if tail and n else lines[:n] if not tail else [])
        return "\n".join(out) + "\n"

    def sh_head(self, args, stdin, st):
        return self._headtail(args, stdin, st, False)

    def sh_tail(self, args, stdin, st):
        return self._headtail(args, stdin, st, True)

    def sh_wc(self, args, stdin, st):
        opts, files = self._split_opts(args)
        rows = []
        for name, txt in self._read_in(self._expand(files, st["cwd"]), stdin, st["cwd"], "wc"):
            if txt is False:
                raise ShellError(f"wc: {name}: No such file or directory")
            txt = txt or ""
            nums = {"l": txt.count("\n"), "w": len(txt.split()), "c": len(txt.encode())}
            sel = [k for k in "lwc" if k in opts] or ["l", "w", "c"]
            rows.append(" ".join(str(nums[k]) for k in sel) + ("" if name == "-" else " " + name))
        return "\n".join(rows) + "\n"

    def sh_sort(self, args, stdin, st):
        opts, files = self._split_opts(args)
        txt = "".join(t if t else "" for _, t in self._read_in(self._expand(files, st["cwd"]), stdin, st["cwd"], "sort"))
        lines = [l for l in txt.split("\n") if l != ""]

        def key(l):
            if "n" in opts:
                m = re.match(r"\s*(-?\d+\.?\d*)", l)
                return (float(m.group(1)) if m else 0.0, l)
            return (0, l)
        lines.sort(key=key, reverse="r" in opts)
        if "u" in opts:
            lines = list(dict.fromkeys(lines))
        return "\n".join(lines) + "\n"

    def sh_grep(self, args, stdin, st):
        opts, rest = self._split_opts(args)
        if not rest:
            raise ShellError("usage: grep [-rilnvc] pattern [file ...]")
        pat, files = rest[0], self._expand(rest[1:], st["cwd"])
        try:
            rx = re.compile(pat, re.I if "i" in opts else 0)
        except re.error:
            rx = re.compile(re.escape(pat), re.I if "i" in opts else 0)
        recursive = "r" in opts or "R" in opts
        targets = []
        if not files:
            if recursive:
                files = ["."]
            else:
                targets = [("-", stdin or "")]
        for f in files:
            p = self.norm(f, st["cwd"])
            if p in self.files:
                targets.append((f, self.files[p]["content"]))
            elif self.is_dir(p):
                if not recursive:
                    raise ShellError(f"grep: {f}: Is a directory")
                for k in (self.tree_files(p) if p != "~" else sorted(self.files)):
                    targets.append((k if f.startswith(("~", "/")) else k.replace(st["cwd"], ".", 1), self.files[k]["content"]))
            else:
                raise ShellError(f"grep: {f}: No such file or directory")
        multi = len(targets) > 1 or recursive
        out = []
        for name, txt in targets:
            lines = txt.split("\n")
            hits = [(n + 1, l) for n, l in enumerate(lines) if bool(rx.search(l)) != ("v" in opts)]
            if "l" in opts:
                if hits:
                    out.append(name)
            elif "c" in opts:
                out.append((name + ":" if multi else "") + str(len(hits)))
            else:
                for n, l in hits:
                    out.append((name + ":" if multi else "") + (f"{n}:" if "n" in opts else "") + l)
        return "\n".join(out) + ("\n" if out else "")

    def sh_find(self, args, stdin, st):
        start, i = ".", 0
        if args and not args[0].startswith("-"):
            start, i = args[0], 1
        base = self.norm(start, st["cwd"])
        if not self.exists(base):
            raise ShellError(f"find: {start}: No such file or directory")
        name_pat = typ = size = mtime = None
        icase = False
        while i < len(args):
            k = args[i]
            v = args[i + 1] if i + 1 < len(args) else ""
            if k in ("-name", "-iname"):
                name_pat, icase = v, k == "-iname"
            elif k == "-type":
                typ = v
            elif k == "-size":
                size = v
            elif k == "-mtime":
                mtime = v
            else:
                raise ShellError(f"find: unsupported option {k}")
            i += 2
        res = []
        for p in sorted(self.all_paths()):
            if not (p == base or p.startswith(base + "/")):
                continue
            isdir = p not in self.files
            if typ == "f" and isdir or typ == "d" and not isdir:
                continue
            if name_pat is not None:
                bn = posixpath.basename(p)
                if icase:
                    ok = fnmatch.fnmatchcase(bn.lower(), name_pat.lower())
                else:
                    ok = fnmatch.fnmatchcase(bn, name_pat)
                if not ok:
                    continue
            if size is not None and not isdir and not self._size_ok(self.files[p]["size"], size):
                continue
            if size is not None and isdir:
                continue
            if mtime is not None:
                if isdir:
                    continue
                age = (self.now - datetime.strptime(self.files[p]["mtime"], "%Y-%m-%dT%H:%M")).days
                n = int(mtime.lstrip("+-"))
                if not ((mtime[0] == "+" and age > n) or (mtime[0] == "-" and age < n) or (mtime[0] not in "+-" and age == n)):
                    continue
            res.append(p if start.startswith(("~", "/")) else p.replace(st["cwd"], ".", 1) if st["cwd"] != "~" else "." + p[1:])
        return "\n".join(res) + ("\n" if res else "")

    @staticmethod
    def _size_ok(sz, spec):
        m = re.fullmatch(r"([+-]?)(\d+)([ckMGb]?)", spec)
        if not m:
            raise ShellError(f"find: bad -size {spec}")
        sign, n, unit = m.group(1), int(m.group(2)), m.group(3)
        mult = {"c": 1, "k": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "b": 512, "": 512}[unit]
        lim = n * mult
        if sign == "+":
            return sz > lim
        if sign == "-":
            return sz < lim
        return -(-sz // mult) == n

    def sh_mkdir(self, args, stdin, st):
        opts, rest = self._split_opts(args)
        for r in rest:
            p = self.norm(r, st["cwd"])
            if p in self.files:
                raise ShellError(f"mkdir: {r}: File exists")
            if self.is_dir(p) and "p" not in opts:
                raise ShellError(f"mkdir: {r}: File exists")
            self.dirs.add(p)
        return ""

    def sh_touch(self, args, stdin, st):
        for r in self._expand(args, st["cwd"]):
            p = self.norm(r, st["cwd"])
            if p in self.files:
                self.files[p]["mtime"] = self.iso_now()
            elif self.is_dir(p):
                pass
            else:
                self._put(p, "")
        return ""

    def sh_mv(self, args, stdin, st):
        opts, rest = self._split_opts(args)
        rest = self._expand(rest, st["cwd"])
        if len(rest) < 2:
            raise ShellError("usage: mv source ... target")
        dst = self.norm(rest[-1], st["cwd"])
        if len(rest) > 2 and not self.is_dir(dst):
            raise ShellError(f"mv: {rest[-1]}: Not a directory")
        for s in rest[:-1]:
            self._move(self.norm(s, st["cwd"]), dst, rest[-1])
        return ""

    def sh_cp(self, args, stdin, st):
        opts, rest = self._split_opts(args)
        rest = self._expand(rest, st["cwd"])
        if len(rest) < 2:
            raise ShellError("usage: cp source ... target")
        dst = self.norm(rest[-1], st["cwd"])
        for s in rest[:-1]:
            src = self.norm(s, st["cwd"])
            into = self.is_dir(dst) or rest[-1].endswith("/")
            if src in self.files:
                t = dst + "/" + posixpath.basename(src) if into else dst
                self.files[t] = dict(self.files[src], mtime=self.iso_now())
            elif self.is_dir(src):
                if not ("r" in opts or "R" in opts):
                    raise ShellError(f"cp: {s} is a directory (not copied).")
                contents = s.rstrip("/").endswith("/.")   # cp -r dir/. dst copies the contents
                t = dst + "/" + posixpath.basename(src) if into and not contents else dst
                for k in self.tree_files(src):
                    self.files[t + k[len(src):]] = dict(self.files[k], mtime=self.iso_now())
                self.dirs.add(t)
            else:
                raise ShellError(f"cp: {s}: No such file or directory")
        return ""

    def sh_rm(self, args, stdin, st):
        opts, rest = self._split_opts(args)
        for r in self._expand(rest, st["cwd"]):
            p = self.norm(r, st["cwd"])
            if not self.exists(p):
                if "f" not in opts:
                    raise ShellError(f"rm: {r}: No such file or directory")
                continue
            if p == "~" or p == "~/.Trash":
                raise ShellError(f"rm: refusing to remove {r}")
            if p not in self.files and not ("r" in opts or "R" in opts):
                raise ShellError(f"rm: {r}: is a directory")
            self._trash(p)
        return ""

    def sh_du(self, args, stdin, st):
        opts, rest = self._split_opts(args)
        out = []
        for r in self._expand(rest or ["."], st["cwd"]):
            p = self.norm(r, st["cwd"])
            if p in self.files:
                n = self.files[p]["size"]
            elif self.is_dir(p):
                n = sum(self.files[k]["size"] for k in (self.tree_files(p) if p != "~" else self.files))
            else:
                raise ShellError(f"du: {r}: No such file or directory")
            out.append(f"{_human(n) if 'h' in opts else n}\t{r}")
        return "\n".join(out) + "\n"


# ---------------------------------------------------------------- snapshot diff

def _email_view(m):
    return {k: m.get(k) for k in ("id", "folder", "to", "cc", "subject", "body", "attachments")}


def diff_snapshots(a, b):
    d = {}
    ae = {m["id"]: m for m in a["email"]}
    be = {m["id"]: m for m in b["email"]}
    d["emails_added"] = [_email_view(m) for i, m in be.items() if i not in ae]
    d["emails_moved"] = [{"id": i, "subject": m["subject"], "from": ae[i]["folder"], "to": m["folder"]}
                         for i, m in be.items() if i in ae and ae[i]["folder"] != m["folder"]]
    acal = {e["id"]: e for e in a["calendar"]}
    bcal = {e["id"]: e for e in b["calendar"]}
    d["events_added"] = [e for i, e in bcal.items() if i not in acal]
    d["events_removed"] = [e for i, e in acal.items() if i not in bcal]
    d["events_changed"] = [{"id": i, "from": {k: acal[i].get(k) for k in e if acal[i].get(k) != e.get(k)},
                            "to": {k: e.get(k) for k in e if acal[i].get(k) != e.get(k)}}
                           for i, e in bcal.items() if i in acal and acal[i] != e]
    af, bf = a["files"], b["files"]
    d["files_added"] = [{"path": p, "content": f["content"]} for p, f in bf.items() if p not in af]
    d["files_removed"] = [p for p in af if p not in bf]
    d["files_modified"] = [{"path": p, "content": f["content"]} for p, f in bf.items()
                           if p in af and af[p]["content"] != f["content"]]
    d["texts_added"] = [t for t in b["texts"] if t not in a["texts"]]
    d["reminders_added"] = [r for r in b["reminders"] if r not in a["reminders"]]
    d["notes_changed"] = b["notes"] if b["notes"] != a["notes"] else None
    aa = {x["id"]: x for x in a["assignments"]}
    d["assignments_changed"] = [{"id": x["id"], "changes": {k: x.get(k) for k in x if aa.get(x["id"], {}).get(k) != x.get(k)}}
                                for x in b["assignments"] if aa.get(x["id"]) != x]
    return {k: v for k, v in d.items() if v}


def render_diff(diff, max_content=1500):
    if not diff:
        return "(no changes to the world)"
    lines = []
    for m in diff.get("emails_added", []):
        lines.append(f"EMAIL {m['folder'].upper()} to={m['to']} cc={m['cc']} subject={m['subject']!r} attachments={m['attachments']}\n  body: {m['body'][:max_content]}")
    for m in diff.get("emails_moved", []):
        lines.append(f"EMAIL MOVED {m['id']} ({m['subject']!r}): {m['from']} -> {m['to']}")
    for e in diff.get("events_added", []):
        lines.append(f"EVENT ADDED {e['id']}: {e['title']} {e['date']} {e['start']}-{e['end']} loc={e.get('location')}")
    for e in diff.get("events_removed", []):
        lines.append(f"EVENT REMOVED {e['id']}: {e['title']}")
    for e in diff.get("events_changed", []):
        lines.append(f"EVENT CHANGED {e['id']}: {e['from']} -> {e['to']}")
    for f in diff.get("files_added", []):
        lines.append(f"FILE ADDED {f['path']}\n  content: {f['content'][:max_content]}")
    for f in diff.get("files_modified", []):
        lines.append(f"FILE MODIFIED {f['path']}\n  content: {f['content'][:max_content]}")
    for p in diff.get("files_removed", []):
        lines.append(f"FILE REMOVED {p}")
    for t in diff.get("texts_added", []):
        lines.append(f"TEXT SENT to {t['with']}: {t['body']}")
    for r in diff.get("reminders_added", []):
        lines.append(f"REMINDER: {r['text']} at {r['when']}")
    if diff.get("notes_changed") is not None:
        lines.append(f"NOTES NOW: {diff['notes_changed'][:max_content]}")
    for x in diff.get("assignments_changed", []):
        lines.append(f"ASSIGNMENT CHANGED {x['id']}: {x['changes']}")
    return "\n".join(lines)
