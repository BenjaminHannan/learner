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


def parse_reply(text):
    """-> ("ACT", {"tool","args"}) | ("ASK", question) | ("OTHER", text). Tolerates leading chatter, a missing ACT prefix and key order."""
    t = (text or "").strip()
    ask_i = t.find("ASK")
    i = t.find("{")
    while i != -1:
        blob = _balanced_json(t, i)
        if blob:
            try:
                o = json.loads(blob)
                if isinstance(o, dict) and "tool" in o and (ask_i == -1 or i < ask_i):
                    return "ACT", {"tool": o["tool"], "args": o.get("args") or {}}
            except Exception:
                pass
        i = t.find("{", i + 1)
    if ask_i != -1:
        return "ASK", t[ask_i + 3:].lstrip(" :").strip().split("\n")[0].strip()
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
