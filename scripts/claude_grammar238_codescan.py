"""Exp 238 step 2: scan agent code for reply-string templates.

Starts from the in-scope agents, follows local 'import X' / 'from X import'
edges inside scripts/, and lists every string literal / f-string / %-string /
.format template that looks like an English sentence a user could see
(starts with a capital or quote/paren, contains a space, ends with . ! ? or ).
Writes codetemplates.jsonl: file, line, kind, template (f-string holes as {expr}).
"""
import ast, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / "scripts"
OUT = ROOT / "artifacts" / "claude-grammar238-20260922"
AGENTS = ["fable_loop138i_agent", "fable_loop138j_agent", "fable_loop219_agent",
          "claude_loop230_agent", "claude_loop230b_agent", "claude_loop227b_agent",
          "claude_loop227c_agent", "fable_loop223_agent", "claude_loop224c_agent",
          "fable_loop226_agent", "claude_loop233_agent", "claude_loop234_agent",
          "fable_loop221_agent", "claude_loop221c_agent", "claude_loop229_agent",
          "claude_loop231_agent", "claude_loop228_agent"]
SENT = re.compile(r"^[\"'(A-Z].*\s.*[.!?)\"]\s*$", re.S)


def local_imports(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                out.add(a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            out.add(n.module.split(".")[0])
    return {m for m in out if (S / f"{m}.py").exists()}


def render_joined(node, src):
    parts = []
    for v in node.values:
        if isinstance(v, ast.Constant):
            parts.append(str(v.value))
        else:
            seg = ast.get_source_segment(src, v.value) if isinstance(v, ast.FormattedValue) else "?"
            parts.append("{" + (seg or "?") + "}")
    return "".join(parts)


def main():
    seen, todo = set(), list(AGENTS)
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        src = (S / f"{m}.py").read_text()
        todo.extend(local_imports(ast.parse(src)) - seen)
    rows = []
    for m in sorted(seen):
        src = (S / f"{m}.py").read_text()
        tree = ast.parse(src)
        docs = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                if n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant):
                    docs.add(id(n.body[0].value))
        inner = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.JoinedStr):
                for v in n.values:
                    inner.add(id(v))
        for n in ast.walk(tree):
            t = kind = None
            if isinstance(n, ast.JoinedStr):
                t, kind = render_joined(n, src), "fstring"
            elif isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs and id(n) not in inner:
                t, kind = n.value, "literal"
                if "%s" in t or "%d" in t:
                    kind = "percent"
                elif re.search(r"\{[a-z_0-9]*\}", t):
                    kind = "format"
            if not t or len(t) > 400 or "\n" in t.strip() and len(t) > 200:
                continue
            ts = t.strip()
            if not SENT.match(ts) or len(ts.split()) < 3:
                continue
            if re.search(r"(def |import |\bself\.|\.py\b|http|%\(|\\d|\[\^|\(\?)", ts):
                continue
            rows.append({"file": f"scripts/{m}.py", "line": n.lineno, "kind": kind, "template": ts})
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "codetemplates.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"modules={len(seen)} templates={len(rows)}")
    print(" ".join(sorted(seen)))


if __name__ == "__main__":
    main()
