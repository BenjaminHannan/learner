"""Deterministic mock tools + the state checker. Only slot-bearing ("key") args are compared; free text args do not exist in this world.

Model reply grammar (one line):  ACT {"tool": NAME, "args": {...}}   |   ASK <question>
"""
import json
import re

from .config import norm

KEY_ARGS = {
    "send_email": ["to"], "draft_email": ["to"], "create_event": ["attendees", "duration_min"],
    "move_event": ["event_id"], "open_file": ["path"], "share_file": ["path", "with"],
}
TOOLS = sorted(KEY_ARGS)


def norm_arg(key, v):
    """JSON-normalise + NFKC one argument value so the exact-match check ignores case/spacing/list order."""
    if key == "attendees":
        vs = v if isinstance(v, list) else [v]
        return sorted(norm(x) for x in vs)
    if key == "duration_min":
        m = re.search(r"\d+", str(v))
        return int(m.group()) if m else norm(v)
    return norm(v)


def norm_action(a):
    """a = {"tool":..., "args":{...}} -> canonical comparable structure (only the key args of that tool)."""
    tool = norm(a.get("tool", ""))
    args = a.get("args") or {}
    return {"tool": tool, "args": {k: norm_arg(k, args[k]) for k in KEY_ARGS.get(tool, []) if k in args}}


def check_action(pred, gold):
    """Returns (ok, mismatched) where mismatched lists 'tool' and/or arg names that differ from gold."""
    try:
        p, g = norm_action(pred), norm_action(gold)
    except Exception:
        return False, ["unparseable"]
    bad = []
    if p["tool"] != g["tool"]:
        bad.append("tool")
    for k in KEY_ARGS.get(g["tool"], []):
        if p["args"].get(k) != g["args"].get(k):
            bad.append(k)
    if p["tool"] != g["tool"]:  # args of a different tool are not comparable; the tool mismatch is the error
        bad = ["tool"] + [k for k in bad if k != "tool"]
    return (not bad), bad


def _balanced_json(t, i):
    depth, in_str, esc = 0, False, False
    for j in range(i, len(t)):
        c = t[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return t[i:j + 1]
    return None


def _as_call(o):
    """dict -> {"tool","args"} or None. 'tool' is the canonical key; 'action' / 'name' are accepted only when they name a known tool.
    Args come from 'args' (or 'arguments'/'parameters'); when missing, the flat keys of the object that are key args of that tool."""
    if not isinstance(o, dict):
        return None
    if "tool" in o:
        return {"tool": o["tool"], "args": o.get("args") or {}}
    for k in ("action", "name"):
        if isinstance(o.get(k), str) and o[k] in KEY_ARGS:
            tool = o[k]
            for ak in ("args", "arguments", "parameters"):
                if isinstance(o.get(ak), dict):
                    return {"tool": tool, "args": o[ak]}
            return {"tool": tool, "args": {a: o[a] for a in KEY_ARGS[tool] if a in o}}
    return None


def _split_top(s):
    """Split on commas outside quotes/brackets."""
    parts, depth, in_str, esc, cur = [], 0, False, False, ""
    for c in s:
        if in_str:
            cur += c
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c in "[{(":
            depth += 1
        elif c in "]})":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        cur += c
    if cur.strip():
        parts.append(cur)
    return parts


def _native_call(t):
    """K2's own tool syntax:  <ifm|tool_call>name(k: v, k2: v2)  -> {"tool","args"} or None."""
    m = re.search(r"<ifm\|tool_call>\s*([A-Za-z_]\w*)\s*\(", t)
    if not m or m.group(1) not in KEY_ARGS:
        return None
    depth, in_str, esc, j = 1, False, False, m.end()
    while j < len(t) and depth:
        c = t[j]
        if in_str:
            esc = (not esc) and c == "\\"
            if c == '"' and not esc:
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        j += 1
    body = t[m.end():j - 1] if depth == 0 else t[m.end():]
    args = {}
    for part in _split_top(body):
        k, sep, v = part.partition(":")
        k, v = k.strip().strip('"'), v.strip()
        if not sep or not k:
            continue
        try:
            args[k] = json.loads(v)
        except Exception:
            args[k] = v.strip('"\'')
    return {"tool": m.group(1), "args": args}


def parse_reply(text):
    """-> ("ACT", {"tool","args"}) | ("ASK", question) | ("OTHER", text). Tolerates leading chatter, a missing ACT prefix and key order, JSON that uses
    'action'/'name' for the tool (flat args allowed) and K2's native <ifm|tool_call>name(k: v) syntax. Prose is never mapped to ASK."""
    t = (text or "").strip()
    ask_i = t.find("ASK")
    i = t.find("{")
    while i != -1:
        blob = _balanced_json(t, i)
        if blob:
            try:
                c = _as_call(json.loads(blob))
                if c is not None and (ask_i == -1 or i < ask_i):
                    return "ACT", c
            except Exception:
                pass
        i = t.find("{", i + 1)
    if ask_i != -1:
        return "ASK", t[ask_i + 3:].lstrip(" :").strip().split("\n")[0].strip()
    c = _native_call(t)
    if c is not None:
        return "ACT", c
    return "OTHER", t


class MockWorld:
    """State that the tools mutate; used by simulate_days to show the diary what happened and by the tests."""

    def __init__(self):
        self.sent, self.drafts, self.events, self.opened, self.shared = [], [], [], [], []

    def execute(self, call):
        tool, args = call["tool"], call.get("args") or {}
        if tool not in KEY_ARGS:
            return {"ok": False, "error": f"unknown tool {tool}"}
        missing = [k for k in KEY_ARGS[tool] if k not in args]
        if missing:
            return {"ok": False, "error": f"missing args {missing}"}
        rec = {"tool": tool, "args": {k: args[k] for k in KEY_ARGS[tool]}}
        {"send_email": self.sent, "draft_email": self.drafts, "create_event": self.events,
         "move_event": self.events, "open_file": self.opened, "share_file": self.shared}[tool].append(rec)
        return {"ok": True, "result": f"{tool} done"}
