"""Hourly read-only check-in: scanners -> rule triage -> notify (once per item)."""
from __future__ import annotations

import email
import email.header
import imaplib
import json
import os
import re
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, List, Optional, Sequence, Tuple

from . import notify
from .config import Config
from .state import State

FIELD = "<<|>>"
REC = "<<#>>"


@dataclass
class Item:
    id: str
    source: str            # mail | calendar | imap
    sender: str = ""
    subject: str = ""
    when: str = ""
    snippet: str = ""
    flags: List[str] = field(default_factory=list)
    starts_in_min: Optional[int] = None


def run_osascript(script: str, timeout: float = 60.0) -> str:
    """Patchable. Raises RuntimeError off macOS or when osascript fails (e.g. permission denied)."""
    if not notify.is_mac():
        raise RuntimeError("osascript needs macOS")
    p = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "osascript failed")
    return p.stdout


def parse_records(out: str, n_fields: int) -> List[List[str]]:
    rows = []
    for rec in out.split(REC):
        rec = rec.strip("\n\r ")
        if not rec:
            continue
        parts = rec.split(FIELD)
        if len(parts) >= n_fields:
            rows.append([p.strip() for p in parts[:n_fields]])
    return rows


MAIL_SCRIPT = '''
set SEP to "%(sep)s"
set REC to "%(rec)s"
set cutoff to (current date) - (%(hours)d * hours)
set out to ""
tell application "Mail"
  set msgs to (messages of inbox whose read status is false and date received > cutoff)
  set n to count of msgs
  if n > 50 then set n to 50
  repeat with i from 1 to n
    set m to item i of msgs
    try
      set c to content of m
      if (length of c) > 200 then set c to text 1 thru 200 of c
      set out to out & (message id of m) & SEP & (sender of m) & SEP & (subject of m) & SEP & ((date received of m) as string) & SEP & c & REC
    end try
  end repeat
end tell
return out
'''

CAL_SCRIPT = '''
set SEP to "%(sep)s"
set REC to "%(rec)s"
set t0 to current date
set t1 to t0 + (%(hours)d * hours)
set out to ""
tell application "Calendar"
  repeat with cal in calendars
    try
      set evs to (every event of cal whose start date >= t0 and start date <= t1)
      repeat with e in evs
        set mins to ((start date of e) - t0) div 60
        set out to out & (uid of e) & SEP & (summary of e) & SEP & ((start date of e) as string) & SEP & (mins as string) & REC
      end repeat
    end try
  end repeat
end tell
return out
'''


class MailAppScanner:
    name = "mail"

    def scan(self, cfg: Config) -> List[Item]:
        out = run_osascript(MAIL_SCRIPT % {"sep": FIELD, "rec": REC, "hours": int(cfg.mail_lookback_h)})
        return [Item("mail:" + r[0], "mail", r[1], r[2], r[3], r[4]) for r in parse_records(out, 5)]


class CalendarScanner:
    name = "calendar"

    def scan(self, cfg: Config) -> List[Item]:
        out = run_osascript(CAL_SCRIPT % {"sep": FIELD, "rec": REC, "hours": int(cfg.calendar_ahead_h)})
        items = []
        for r in parse_records(out, 4):
            try:
                mins = int(r[3])
            except ValueError:
                mins = None
            items.append(Item("cal:%s:%s" % (r[0], r[2]), "calendar", "", r[1], r[2], "", starts_in_min=mins))
        return items


def _decode(h: Optional[str]) -> str:
    if not h:
        return ""
    return "".join(
        (b.decode(c or "utf-8", "replace") if isinstance(b, bytes) else b)
        for b, c in email.header.decode_header(h))


class ImapScanner:
    name = "imap"

    def scan(self, cfg: Config) -> List[Item]:
        pw = os.environ.get(cfg.imap_password_env, "")
        if not (cfg.imap_host and cfg.imap_user and pw):
            raise RuntimeError("imap not configured (host, user, or $%s missing)" % cfg.imap_password_env)
        since = (datetime.now() - timedelta(hours=cfg.mail_lookback_h)).strftime("%d-%b-%Y")
        items: List[Item] = []
        m = imaplib.IMAP4_SSL(cfg.imap_host)
        try:
            m.login(cfg.imap_user, pw)
            m.select("INBOX", readonly=True)   # EXAMINE: nothing can be changed
            typ, data = m.search(None, "UNSEEN", "SINCE", since)
            ids = (data[0] or b"").split()[-50:]
            for i in ids:
                typ, parts = m.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])")
                raw = parts[0][1] if parts and isinstance(parts[0], tuple) else b""
                msg = email.message_from_bytes(raw)
                mid = (msg.get("Message-ID") or i.decode()).strip()
                items.append(Item("imap:" + mid, "imap", _decode(msg.get("From")), _decode(msg.get("Subject")),
                                  msg.get("Date", "")))
        finally:
            try:
                m.logout()
            except Exception:
                pass
        return items


def default_scanners(cfg: Config) -> list:
    sc: list = []
    if cfg.mail_enabled:
        sc.append(MailAppScanner())
    if cfg.calendar_enabled:
        sc.append(CalendarScanner())
    if cfg.imap_host:
        sc.append(ImapScanner())
    return sc


def triage(items: Sequence[Item], cfg: Config) -> List[Tuple[Item, str]]:
    vips = [v.lower() for v in cfg.vip_senders if v]
    words = [re.compile(r"\b" + re.escape(w.lower()) + r"\b") for w in cfg.urgent_words if w]
    out = []
    for it in items:
        reason = ""
        if it.source == "calendar":
            if it.starts_in_min is not None and 0 <= it.starts_in_min <= cfg.event_soon_h * 60:
                reason = "event starts in %d min" % it.starts_in_min
        else:
            sender = it.sender.lower()
            text = (it.subject + " " + it.snippet).lower()
            if any(v in sender for v in vips):
                reason = "VIP sender"
            else:
                hit = next((w.pattern for w in words if w.search(text)), None)
                if hit:
                    reason = "urgent word: " + hit.replace("\\b", "").replace("\\", "")
        if reason:
            out.append((it, reason))
    return out


def llm_triage(items: Sequence[Item], cfg: Config) -> set:
    """Optional: ask an OpenAI-compatible server which item ids need attention. Returns ids; any failure -> empty."""
    if not (cfg.triage_url and items):
        return set()
    listing = "\n".join("%s | %s | %s" % (i.id, i.sender, i.subject) for i in items if i.source != "calendar")
    body = json.dumps({"model": cfg.triage_model, "temperature": 0, "max_tokens": 200, "messages": [
        {"role": "system", "content": "Reply with a JSON list of ids (first column) that need the user's attention today. Nothing else."},
        {"role": "user", "content": listing}]}).encode()
    try:
        req = urllib.request.Request(cfg.triage_url.rstrip("/") + "/v1/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        txt = json.loads(urllib.request.urlopen(req, timeout=60).read())["choices"][0]["message"]["content"]
        ids = json.loads(txt[txt.index("["):txt.rindex("]") + 1])
        return {str(i) for i in ids}
    except Exception:
        return set()


def describe(it: Item, reason: str) -> Tuple[str, str]:
    if it.source == "calendar":
        return "Event soon: " + it.subject, "%s (%s)" % (it.when, reason)
    return "%s: %s" % (it.sender[:40] or it.source, it.subject[:80]), reason


def run(cfg: Config, state: State, scanners: Optional[list] = None,
        sender: Callable[[Config, str, str], dict] = notify.send) -> dict:
    scanners = default_scanners(cfg) if scanners is None else scanners
    items: List[Item] = []
    counts, errors = {}, {}
    for sc in scanners:
        name = getattr(sc, "name", type(sc).__name__)
        try:
            got = sc.scan(cfg)
            counts[name] = len(got)
            items += got
        except Exception as e:  # noqa: scanners must never crash the loop
            errors[name] = str(e)[:200]
            state.event("checkin_scanner_error", scanner=name, error=errors[name])
    picked = triage(items, cfg)
    have = {i.id for i, _ in picked}
    rest = [i for i in items if i.id not in have]
    extra = llm_triage(rest, cfg)
    picked += [(i, "model triage") for i in rest if i.id in extra]
    seen = state.notified()
    fresh = [(i, r) for i, r in picked if i.id not in seen]
    for it, reason in fresh:
        title, body = describe(it, reason)
        sender(cfg, title, body)
        seen[it.id] = time.time()
    if fresh:
        state.save_notified(seen)
    state.event("checkin", counts=counts, errors=errors, notified=len(fresh))
    return {"counts": counts, "errors": errors, "items": items, "notified": [i for i, _ in fresh],
            "flagged": picked}
