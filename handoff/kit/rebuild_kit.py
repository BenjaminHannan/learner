#!/usr/bin/env python3
"""Rebuild files written under the (wiped) session scratchpad from the session transcript.

Replays, in transcript order: Write tool calls, Edit tool calls, and Bash heredocs
(cat > FILE <<EOF / cat >> FILE <<EOF / tee [-a] FILE <<EOF) whose target is under S.
Only successful tool calls are replayed. Output: files restored under OUT (default S itself)
plus a report of what was restored / partially restored / unparsed.
"""
import json, os, re, sys

T = sys.argv[1]
OUT = sys.argv[2]
S = "/private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad"

uses = []          # (order, tool_use_id, name, input)
errors = set()     # tool_use_ids whose result was an error
with open(T) as f:
    for line in f:
        try:
            d = json.loads(line)
        except Exception:
            continue
        msg = d.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                uses.append((len(uses), c.get("id"), c.get("name"), c.get("input") or {}))
            elif c.get("type") == "tool_result":
                if c.get("is_error"):
                    errors.add(c.get("tool_use_id"))

files = {}      # path -> content
history = {}    # path -> list of events
unparsed = []

def under_s(p):
    return p.startswith(S + "/")

ASSIGN = re.compile(r'(?:^|[;\n&]\s*|\bexport\s+)([A-Za-z_][A-Za-z0-9_]*)=("([^"]*)"|\'([^\']*)\'|([^\s;&|]+))')

def expand(s, env):
    def rep(m):
        name = m.group(1) or m.group(2)
        return env.get(name, m.group(0))
    return re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)', rep, s)

HEREDOC = re.compile(
    r'(?P<pre>[^\n]*?)<<(?P<dash>-?)\s*(?P<q>[\'"]?)(?P<delim>[A-Za-z_][A-Za-z0-9_]*)(?P=q)(?P<post>[^\n]*)\n')

def parse_bash(cmd, idx):
    env = {"S": S, "Q": S + "/mimo/queue", "HOME": "/Users/ben-hannan"}
    pos = 0
    out = []
    while True:
        m = HEREDOC.search(cmd, pos)
        if not m:
            break
        # update env with assignments that appear before this heredoc
        for am in ASSIGN.finditer(cmd[pos:m.start()]):
            val = am.group(3) if am.group(3) is not None else (am.group(4) if am.group(4) is not None else am.group(5))
            env[am.group(1)] = expand(val, env)
        delim = m.group("delim")
        body_start = m.end()
        lines = cmd[body_start:].split("\n")
        body_lines = []
        end_off = None
        off = body_start
        for ln in lines:
            chk = ln.lstrip("\t") if m.group("dash") else ln
            if chk == delim:
                end_off = off + len(ln)
                break
            body_lines.append(ln)
            off += len(ln) + 1
        if end_off is None:
            unparsed.append((idx, "unterminated heredoc " + delim))
            break
        body = "\n".join(body_lines) + "\n"
        quoted = bool(m.group("q"))
        if not quoted:
            body = body.replace("\\$", "\x00DOLLAR\x00")
            body = expand(body, env)
            body = body.replace("\x00DOLLAR\x00", "$").replace("\\`", "`").replace("\\\\", "\\")
        line = m.group("pre") + " " + m.group("post")
        tm = re.search(r'(?:cat|tee)\b[^|]*?(>>|>|\s-a\s|\s)\s*("([^"]+)"|\'([^\']+)\'|([^\s;&|<>]+))', line)
        target, mode = None, "w"
        rm = re.search(r'(>>|>)\s*("([^"]+)"|\'([^\']+)\'|([^\s;&|<>]+))', line)
        if rm and re.search(r'\bcat\b', line):
            target = rm.group(3) or rm.group(4) or rm.group(5)
            mode = "a" if rm.group(1) == ">>" else "w"
        else:
            tee = re.search(r'\btee\s+(-a\s+)?("([^"]+)"|\'([^\']+)\'|([^\s;&|<>]+))', line)
            if tee:
                target = tee.group(3) or tee.group(4) or tee.group(5)
                mode = "a" if tee.group(1) else "w"
        if target:
            target = expand(target, env)
            out.append((target, mode, body))
        pos = end_off
    # trailing assignments irrelevant
    return out

for idx, uid, name, inp in uses:
    if uid in errors:
        continue
    if name == "Write":
        p = inp.get("file_path", "")
        if under_s(p):
            files[p] = inp.get("content", "")
            history.setdefault(p, []).append(("write", idx))
    elif name == "Edit":
        p = inp.get("file_path", "")
        if under_s(p):
            if p not in files:
                history.setdefault(p, []).append(("edit-missing-base", idx))
                continue
            old, new = inp.get("old_string", ""), inp.get("new_string", "")
            if old in files[p]:
                files[p] = files[p].replace(old, new) if inp.get("replace_all") else files[p].replace(old, new, 1)
                history[p].append(("edit", idx))
            else:
                history[p].append(("edit-nomatch", idx))
    elif name == "Bash":
        cmd = inp.get("command", "")
        if "<<" not in cmd:
            continue
        for target, mode, body in parse_bash(cmd, idx):
            if not under_s(target):
                continue
            if mode == "a":
                files[target] = files.get(target, "") + body
                history.setdefault(target, []).append(("append", idx))
            else:
                files[target] = body
                history.setdefault(target, []).append(("heredoc", idx))

restored = 0
for p, content in sorted(files.items()):
    rel = p[len(S) + 1:]
    dest = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and OUT == S:
        continue  # never overwrite files that exist now (e.g. new replies)
    with open(dest, "w") as g:
        g.write(content)
    restored += 1

rep = {p[len(S) + 1:]: history.get(p) for p in files}
bad = {k: v for k, v in rep.items() if any(e[0] in ("edit-nomatch", "edit-missing-base") for e in v)}
print("tool uses:", len(uses), "errors:", len(errors))
print("files reconstructed:", len(files), "written:", restored)
print("with problems:", json.dumps(bad, indent=0)[:3000])
print("unparsed:", unparsed[:20])
with open(os.path.join(OUT, "REBUILD-REPORT.json"), "w") as g:
    json.dump({"files": rep, "problems": bad, "unparsed": unparsed}, g, indent=1)
