"""Pure-Python fake world for assistant tasks. No disk, network or shell. Deterministic."""
import copy, fnmatch, json, re

TOOLS = json.load(open(__file__.rsplit("/", 1)[0] + "/tools.json"))
TOOL_NAMES = [t["function"]["name"] for t in TOOLS]
SCHEMA = {t["function"]["name"]: t["function"]["parameters"] for t in TOOLS}


def _norm(p):
    p = str(p).strip()
    if p.startswith("~"):
        p = "/home/user" + p[1:]
    return re.sub(r"/+", "/", p).rstrip("/") or "/"


def _list(x):
    return [x] if isinstance(x, str) else list(x or [])


def _j(o):
    return json.dumps(o, ensure_ascii=False)


class World:
    def __init__(self, state):
        s = copy.deepcopy(state)
        self.today = s.get("today", "2026-10-24")
        self.files = {_norm(k): v for k, v in s.get("files", {}).items()}
        self.inbox = s.get("emails", [])
        self.sent = s.get("sent", [])
        self.drafts = s.get("drafts", [])
        self.events = s.get("calendar", [])
        self.notes = s.get("notes", {})
        self.reminders = s.get("reminders", [])
        self.n_events0 = len(self.events)

    @classmethod
    def from_json(cls, state):
        return cls(state)

    def to_json(self):
        return dict(today=self.today, files=self.files, emails=self.inbox, sent=self.sent, drafts=self.drafts,
                    calendar=self.events, notes=self.notes, reminders=self.reminders)

    def call(self, name, args):
        try:
            if name not in SCHEMA:
                return f"error: unknown tool '{name}'"
            if not isinstance(args, dict):
                return "error: arguments must be a JSON object"
            for k in SCHEMA[name].get("required", []):
                if k not in args:
                    return f"error: missing required argument '{k}'"
            return getattr(self, "t_" + name)(**{k: v for k, v in args.items() if k in SCHEMA[name]["properties"]})
        except Exception as e:  # never raise into the rollout
            return f"error: {type(e).__name__}: {e}"

    # files
    def t_read_file(self, path, max_lines=None):
        p = _norm(path)
        if p not in self.files:
            return f"error: no such file: {p}"
        lines = self.files[p].split("\n")
        return "\n".join(lines[:int(max_lines)] if max_lines else lines)

    def t_write_file(self, path, content, append=False):
        p = _norm(path)
        self.files[p] = (self.files.get(p, "") + content) if append and p in self.files else content
        return _j({"ok": True, "path": p, "bytes": len(self.files[p])})

    def t_list_dir(self, path, recursive=False):
        d = _norm(path)
        pre = "" if d == "/" else d
        out = set()
        for f in self.files:
            if f.startswith(pre + "/"):
                rest = f[len(pre) + 1:]
                out.add(rest if recursive or "/" not in rest else rest.split("/")[0] + "/")
        return _j(sorted(out)) if out else f"error: no such directory or empty: {d}"

    def t_search_files(self, query, path="/", mode="content"):
        d = _norm(path)
        pre = "" if d == "/" else d
        hits = []
        for f, txt in sorted(self.files.items()):
            if not f.startswith(pre + "/"):
                continue
            if mode == "name":
                if fnmatch.fnmatch(f.rsplit("/", 1)[-1].lower(), query.lower()) or query.lower() in f.lower():
                    hits.append(f)
            else:
                for i, ln in enumerate(txt.split("\n"), 1):
                    if query.lower() in ln.lower():
                        hits.append(f"{f}:{i}: {ln[:120]}")
        return _j(hits[:30])

    # email
    def t_email_search(self, query, folder="inbox", limit=10):
        box = {"inbox": self.inbox, "sent": self.sent, "drafts": self.drafts, "archive": []}.get(folder)
        if box is None:
            return "error: folder must be inbox, sent, drafts or archive"
        terms, filt = [], []
        for tok in re.findall(r'(\w+:"[^"]*"|\S+)', query):
            m = re.match(r'(from|subject|after):"?([^"]*)"?$', tok)
            (filt if m else terms).append(m.groups() if m else tok.lower())
        out = []
        for e in box:
            blob = " ".join([str(e.get("from", "")), " ".join(_list(e.get("to"))), e.get("subject", ""), e.get("body", "")]).lower()
            ok = all(t in blob for t in terms)
            for k, v in filt:
                v = v.lower()
                if k == "from": ok &= v in str(e.get("from", "")).lower()
                elif k == "subject": ok &= v in e.get("subject", "").lower()
                elif k == "after": ok &= str(e.get("date", "")) >= v
            if ok:
                out.append({k: e.get(k) for k in ("id", "from", "to", "subject", "date")} | {"body": e.get("body", "")[:600]})
        return _j(out[:int(limit)])

    def _mail(self, box, to, subject, body, cc=None):
        box.append(dict(id=f"{'s' if box is self.sent else 'd'}{len(box) + 1}", **{"from": "me"}, to=_list(to),
                        cc=_list(cc), subject=subject, body=body, date=self.today))

    def t_send_email(self, to, subject, body, cc=None):
        self._mail(self.sent, to, subject, body, cc)
        return _j({"ok": True, "status": "sent", "to": _list(to)})

    def t_email_draft(self, to, subject, body, cc=None):
        self._mail(self.drafts, to, subject, body, cc)
        return _j({"ok": True, "status": "draft saved", "id": self.drafts[-1]["id"]})

    # calendar
    def t_calendar_list_events(self, start_date, end_date, calendar=None):
        ev = [e for e in self.events if start_date <= e["date"] <= end_date and (not calendar or e.get("calendar", "Personal").lower() == calendar.lower())]
        return _j(sorted(ev, key=lambda e: (e["date"], e["start"])))

    def t_calendar_create_event(self, title, start, end, calendar="Personal", location="", attendees=None):
        m1, m2 = (re.match(r"(\d{4}-\d\d-\d\d)[T ](\d\d:\d\d)", x) for x in (start, end))
        if not (m1 and m2):
            return "error: start and end must be ISO 8601 like 2026-10-27T14:00"
        ev = dict(title=title, date=m1[1], start=m1[2], end=m2[2], attendees=_list(attendees), location=location, calendar=calendar)
        self.events.append(ev)
        return _j({"ok": True, "event": ev})

    # notes
    def t_notes_search(self, query, limit=5):
        q = query.lower()
        hits = [{"title": t, "text": x[:600]} for t, x in self.notes.items() if q in t.lower() or q in x.lower()]
        return _j(hits[:int(limit)])

    def t_notes_append(self, title, text):
        self.notes[title] = (self.notes[title] + "\n" + text) if title in self.notes else text
        return _j({"ok": True, "title": title})

    def t_set_reminder(self, text, when, repeat="none"):
        self.reminders.append(dict(text=text, when=when, repeat=repeat))
        return _j({"ok": True, "text": text, "when": when})
