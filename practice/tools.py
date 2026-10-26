"""Tools for Practice-1: python(code) sandbox, search(query), look(grid), answer(text); lenient parsing of one tool call per turn."""
import os
import re
import resource
import subprocess
import sys
import tempfile
from collections import deque

MAX_TURNS = 6
OUT_CAP = 2000
PY_TIMEOUT = 10

SYSTEM_PROMPT = """You solve puzzles. You may use tools. Each turn, reply with exactly ONE tool call in this form and nothing after it:
<tool>NAME</tool>
<input>
...
</input>
Tools:
- python: run Python 3 code (10 seconds, no internet, no files). Use print() to see results.
- search: look up a topic in a small offline reference library (math, algorithms, Python standard library). Input is a short query.
- look: describe a grid of digits (size, colour counts, objects with boxes, symmetries, repeated tiles). Input is the grid, one row per line.
- answer: give your final answer. Input is only the answer: an integer, a short word or phrase, or a grid (one row per line, digits separated by spaces).
You have at most __N__ turns. After a tool runs you see its output. Check your work with python when you can, then call answer."""

SYSTEM_PROMPT = SYSTEM_PROMPT.replace("__N__", str(MAX_TURNS))

ANSWER_HINT = {"int": "an integer", "str": "a short word or phrase", "grid": "a grid (one row per line, digits separated by spaces)"}


def user_prompt(p):
    return f"{p['prompt']}\n\n(The final answer is {ANSWER_HINT.get(p['answer_type'], 'short')}.)"


# ------------------------------------------------------------------ parsing
_TOOL_RE = re.compile(r"<tool>\s*([a-zA-Z_]+)\s*</tool>\s*(?:<input>(.*?)(?:</input>|$))?", re.S)
_FENCE_RE = re.compile(r"```[ \t]*(?:python|py|python3)[ \t]*\n(.*?)(?:```|$)", re.S | re.I)
_ANS_RE = re.compile(r"(?im)^[ \t>*_`]*(?:final\s+)?answer[ \t*_`]*:[ \t*_`]*(.*)$")


def clean_answer(s):
    s = s.strip()
    s = re.sub(r"^```[a-z]*\n?|\n?```$", "", s).strip()
    if "\n" not in s:
        s = s.strip("*_` ").rstrip(".")
    return s.strip()


def parse_call(text):
    """-> (tool, input) or None. Order: explicit <tool> block; ```python fence (a python call); 'ANSWER: x' (an answer call)."""
    m = _TOOL_RE.search(text)
    if m:
        name = m.group(1).lower()
        if name in ("python", "search", "look", "answer"):
            inp = (m.group(2) or "").strip("\n")
            if name == "python":
                f = _FENCE_RE.search(inp)
                if f:
                    inp = f.group(1)
            if name == "answer":
                inp = clean_answer(inp)
            return name, inp
    f = _FENCE_RE.search(text)
    if f:
        return "python", f.group(1)
    a = last_answer_line(text)
    if a is not None:
        return "answer", a
    return None


def last_answer_line(text):
    ms = list(_ANS_RE.finditer(text))
    if not ms:
        return None
    m = ms[-1]
    rest = text[m.start(1):]
    if "\n" in rest.strip() and not m.group(1).strip():  # grid starting on the next lines
        return clean_answer(rest)
    first = m.group(1)
    tail = rest[len(first):].lstrip("\n")
    if first.strip().startswith("```") or (re.fullmatch(r"[\d ,\[\]]+", first.strip() or "x") and re.match(r"[\d ,\[\]]+(\n|$)", tail) and len(first.split()) > 1):
        return clean_answer(rest.split("```")[0] if first.strip().startswith("```") is False else rest)
    return clean_answer(first)


# ------------------------------------------------------------------ python sandbox
def _limits():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 2 ** 30, 3 * 2 ** 30))
    resource.setrlimit(resource.RLIMIT_CPU, (PY_TIMEOUT + 2, PY_TIMEOUT + 2))
    os.setsid()


_RUNNER = (
    "import socket\n"
    "def _deny(*a, **k): raise OSError('network is disabled in this sandbox')\n"
    "socket.socket.connect = _deny; socket.socket.connect_ex = _deny; socket.create_connection = _deny; socket.getaddrinfo = _deny\n"
    "import sys, traceback\n"
    "try:\n"
    "    exec(compile(open('main.py').read(), 'main.py', 'exec'), {'__name__': '__main__'})\n"
    "except SystemExit: raise\n"
    "except BaseException as e:\n"
    "    traceback.print_exception(type(e), e, e.__traceback__.tb_next); sys.exit(1)\n")


def run_python(code, timeout=PY_TIMEOUT, cap=OUT_CAP):
    """python -I in a fresh temp dir, minimal environment (no proxy variables), wall-clock timeout. Best effort only: not a security boundary."""
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONHASHSEED": "0", "HOME": "/nonexistent", "NO_PROXY": "*", "no_proxy": "*", "PYTHONIOENCODING": "utf-8"}
    with tempfile.TemporaryDirectory(prefix="pr1_") as d:
        try:
            with open(os.path.join(d, "main.py"), "w") as f:
                f.write(code)
            p = subprocess.Popen([sys.executable, "-I", "-c", _RUNNER], cwd=d, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 preexec_fn=_limits, text=True, errors="replace")
        except Exception as e:  # noqa: BLE001
            return f"[sandbox error: {e}]"
        try:
            out, _ = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, 9)
            except Exception:  # noqa: BLE001
                p.kill()
            out, _ = p.communicate()
            out = (out or "")[:cap] + f"\n[timeout after {timeout} s]"
    out = out or ""
    if len(out) > cap:
        out = out[:cap] + "\n[output cut]"
    return out if out.strip() else "[no output; use print() to see results]"


# ------------------------------------------------------------------ look
def parse_grid(text):
    text = re.sub(r"\]\s*,\s*\[", "]\n[", str(text).strip().strip("`"))
    rows = []
    for line in text.splitlines():
        line = line.strip().strip("[],")
        if not line or line.lower().startswith("python"):
            continue
        if re.search(r"[\s,]", line):
            toks = re.findall(r"\d+", line)
        else:
            toks = re.findall(r"\d", line)  # rows written without separators
        if toks:
            rows.append([int(x) for x in toks])
    if not rows or len({len(r) for r in rows}) != 1:
        return None
    return rows


def components(g, color):
    h, w = len(g), len(g[0])
    seen, out = set(), []
    for r in range(h):
        for c in range(w):
            if g[r][c] != color or (r, c) in seen:
                continue
            q, cells = deque([(r, c)]), []
            seen.add((r, c))
            while q:
                y, x = q.popleft()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (y + dy, x + dx)
                    if 0 <= n[0] < h and 0 <= n[1] < w and g[n[0]][n[1]] == color and n not in seen:
                        seen.add(n)
                        q.append(n)
            ys, xs = [a for a, _ in cells], [b for _, b in cells]
            out.append(((min(ys), min(xs), max(ys), max(xs)), len(cells)))
    return out


def smallest_tile(g):
    h, w = len(g), len(g[0])
    for ph in range(1, h + 1):
        for pw in range(1, w + 1):
            if (ph, pw) == (h, w) or (ph > h // 2 and pw > w // 2):
                continue
            if all(g[r][c] == g[r % ph][c % pw] for r in range(h) for c in range(w)):
                return ph, pw
    return None


def look(text):
    g = parse_grid(text)
    if g is None:
        return "look: could not read a rectangular grid of digits (one row per line)."
    h, w = len(g), len(g[0])
    flat = [v for r in g for v in r]
    counts = {c: flat.count(c) for c in sorted(set(flat))}
    bg = max(counts, key=counts.get)
    lines = [f"size: {h} rows x {w} columns", "colour counts: " + ", ".join(f"{c}:{n}" for c, n in counts.items()) + f" (most common = {bg})"]
    for c in counts:
        comps = components(g, c)
        if c == bg and len(comps) == 1:
            lines.append(f"colour {c}: 1 region, box (r{comps[0][0][0]},c{comps[0][0][1]})-(r{comps[0][0][2]},c{comps[0][0][3]}), size {comps[0][1]}")
            continue
        desc = "; ".join(f"box (r{b[0]},c{b[1]})-(r{b[2]},c{b[3]}) size {n}" for b, n in comps[:8])
        lines.append(f"colour {c}: {len(comps)} object(s) (4-connected): {desc}" + (" ..." if len(comps) > 8 else ""))
    sym = []
    if all(r == r[::-1] for r in g):
        sym.append("left-right mirror")
    if g == g[::-1]:
        sym.append("up-down mirror")
    if g == [r[::-1] for r in g[::-1]]:
        sym.append("180-degree rotation")
    if h == w:
        if all(g[r][c] == g[c][r] for r in range(h) for c in range(w)):
            sym.append("main-diagonal mirror (transpose)")
        if all(g[r][c] == g[w - 1 - c][h - 1 - r] for r in range(h) for c in range(w)):
            sym.append("anti-diagonal mirror")
        if g == [list(x) for x in zip(*g[::-1])]:
            sym.append("90-degree rotation")
    lines.append("symmetry: " + (", ".join(sym) if sym else "none"))
    t = smallest_tile(g)
    lines.append(f"repeated tile: {t[0]}x{t[1]} tile repeats to fill the grid" if t else "repeated tile: none")
    out = "\n".join(lines)
    return out[:OUT_CAP]


# ------------------------------------------------------------------ dispatcher
def run_tool(name, inp):
    """-> observation text (for 'answer' the caller handles it)."""
    if name == "python":
        return run_python(inp)
    if name == "search":
        from .library import search
        return search(inp)
    if name == "look":
        return look(inp)
    return ""
