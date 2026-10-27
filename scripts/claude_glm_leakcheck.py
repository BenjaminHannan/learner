#!/usr/bin/env python3
"""One-call check that the opencode helper v1.1 cleans up its session in THIS layout (Trustworthy notes thread,
2026-09-26; asked by the Thread manager at 20:13 UTC before any long opencode run).

v1.1 lists sessions from the folder above its own file (_project_dir). When a job runs from a git-archive temp tree,
that folder is not the worktree, so its cleanup may find nothing. This makes one "Reply with the word ok" call tagged
with a known title, runs the helper's own cleanup, then looks for that title from the helper's folder and from the
worktree root. Any session it finds is this check's own and is deleted by id.

python -B scripts/claude_glm_leakcheck.py --worktree /abs/path/to/worktree
prints {"exit", "reply_ok", "left_after_cleanup"}; exit code 0 = clean, 2 = ROUTE-FAIL, 3 = LEAK
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_glm_opencode_v11 as V  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", required=True)
    a = ap.parse_args()
    tag = "leakcheck-" + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix="glm-opencode-") as td:
        code, out, _ = V._run_opencode(["run", "--model", V.MODEL, "--title", tag, "Reply with the word ok"], cwd=td)
    V._delete_own_session(V._project_dir(), tag)
    left = {d: sorted(V._ids_with_title(d, tag)) for d in (V._project_dir(), a.worktree)}
    n = sum(len(v) for v in left.values())
    print(json.dumps({"exit": code, "reply_ok": "ok" in V._strip_chrome(out).lower(), "left_after_cleanup": n}))
    for d, ids in left.items():
        V._delete_sessions(d, ids)                   # only this check's own tagged session
    sys.exit(2 if code != 0 else 3 if n else 0)


if __name__ == "__main__":
    main()
