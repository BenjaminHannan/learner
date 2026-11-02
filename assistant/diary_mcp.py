#!/usr/bin/env python3
"""Stdio MCP server: search Ben's diary of past assistant chats (read-only SQLite).

JSON-RPC 2.0, one JSON message per line. Nothing but protocol goes to stdout.
Stdlib only.
"""
import datetime
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

DIARY_DIR = Path(os.environ.get("DIARY_DIR", "~/learner-ops/diary")).expanduser()
if "--diary-dir" in sys.argv:
    DIARY_DIR = Path(sys.argv[sys.argv.index("--diary-dir") + 1]).expanduser()
EMPTY = "The diary is empty (no past chats have been recorded yet)."

TOOLS = [
    {"name": "diary_search",
     "description": ("Search Ben's diary: a searchable record of ALL past chats between Ben and this "
                     "assistant. Use it whenever Ben refers to something from before ('last time', "
                     "'remember when', 'we talked about', 'what did I decide'). Returns the best "
                     "matching turns with date, conversation title, a snippet and conv_id "
                     "(pass conv_id to diary_read for the full conversation)."),
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "Words to look for"},
         "limit": {"type": "integer", "description": "Max hits (default 8)"},
         "since": {"type": "string", "description": "Only chats on/after this date, YYYY-MM-DD"}},
         "required": ["query"]}},
    {"name": "diary_read",
     "description": ("Read one past conversation from Ben's diary in time order (user and assistant "
                     "text, truncated). Use after diary_search to see the details around a hit."),
     "inputSchema": {"type": "object", "properties": {
         "conv_id": {"type": "string", "description": "conv_id from diary_search"},
         "max_turns": {"type": "integer", "description": "Max turns (default 20)"}},
         "required": ["conv_id"]}},
    {"name": "diary_days",
     "description": ("List recent days in Ben's diary with how many conversations happened and their "
                     "titles. Use for 'what did we do this week' or 'yesterday'."),
     "inputSchema": {"type": "object", "properties": {
         "days": {"type": "integer", "description": "How many days back (default 7)"}}}},
]


def connect():
    p = DIARY_DIR / "diary.sqlite"
    if not p.exists():
        return None
    db = sqlite3.connect(p.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
    try:
        db.execute("SELECT 1 FROM turns LIMIT 1")
    except sqlite3.Error:
        return None
    return db


def fts_query(q):
    """Quote every word as a term and OR them, so punctuation never errors."""
    words = re.findall(r"\w+", q or "")
    return " OR ".join('"%s"' % w for w in words)


def to_int(v, default):
    try:
        return max(1, int(v))
    except (TypeError, ValueError):
        return default


def diary_search(args, db):
    q = fts_query(args.get("query"))
    if not q:
        return "Give at least one word to search for."
    sql = ("SELECT date, title, conv_id, snippet(turns, 0, '[', ']', '...', 30) FROM turns "
           "WHERE turns MATCH ?")
    params = [q]
    since = args.get("since")
    if since:
        sql += " AND date >= ?"
        params.append(str(since))
    sql += " ORDER BY bm25(turns) LIMIT ?"
    params.append(to_int(args.get("limit"), 8))
    rows = db.execute(sql, params).fetchall()
    if not rows:
        return "No matches in the diary."
    return "\n\n".join("%s | %s | conv_id=%s\n%s" % (d, t, c, s.replace("\n", " "))
                       for d, t, c, s in rows)


def diary_read(args, db):
    cid = str(args.get("conv_id") or "")
    rows = db.execute("SELECT ts, user_text, assistant_text FROM turns WHERE conv_id = ? "
                      "ORDER BY rowid LIMIT ?", (cid, to_int(args.get("max_turns"), 20))).fetchall()
    if not rows:
        return "No conversation with that conv_id."
    parts = []
    for ts, u, a in rows:
        if u:
            parts.append("[%s] Ben: %s" % (ts[:16], u))
        if a:
            parts.append("Assistant: %s" % a)
    text = "\n\n".join(parts)
    return text if len(text) <= 6000 else text[:6000] + "\n...[truncated]"


def diary_days(args, db):
    n = to_int(args.get("days"), 7)
    cutoff = (datetime.datetime.now(datetime.timezone.utc).date()
              - datetime.timedelta(days=n - 1)).isoformat()
    rows = db.execute("SELECT date, conv_id, title FROM turns WHERE date >= ? "
                      "GROUP BY date, conv_id ORDER BY date DESC, min(rowid)", (cutoff,)).fetchall()
    if not rows:
        return "Nothing in the diary for that period."
    days = {}
    for d, _, t in rows:
        days.setdefault(d, []).append(t or "(untitled)")
    return "\n\n".join("%s: %d conversation(s)\n%s" % (d, len(ts), "\n".join("- " + t for t in ts))
                       for d, ts in days.items())


HANDLERS = {"diary_search": diary_search, "diary_read": diary_read, "diary_days": diary_days}


def call_tool(name, args):
    if name not in HANDLERS:
        raise KeyError(name)
    db = connect()
    if db is None:
        return EMPTY
    try:
        return HANDLERS[name](args or {}, db)
    finally:
        db.close()


def handle(msg):
    """Return a response dict, or None for notifications."""
    mid, method = msg.get("id"), msg.get("method")
    ok = lambda r: {"jsonrpc": "2.0", "id": mid, "result": r}
    err = lambda c, m: {"jsonrpc": "2.0", "id": mid, "error": {"code": c, "message": m}}
    if mid is None:  # notification (e.g. notifications/initialized)
        return None
    if method == "initialize":
        return ok({"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                   "serverInfo": {"name": "diary", "version": "1.0"}})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        p = msg.get("params") or {}
        try:
            text, bad = call_tool(p.get("name"), p.get("arguments")), False
        except KeyError:
            return err(-32602, "unknown tool: %s" % p.get("name"))
        except Exception as e:  # report tool failures inside the result
            text, bad = "Diary error: %r" % e, True
        return ok({"content": [{"type": "text", "text": text}], "isError": bad})
    return err(-32601, "method not found: %s" % method)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            if not isinstance(msg, dict):
                raise ValueError
        except ValueError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            out = handle(msg)
        if out is not None:
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
