#!/usr/bin/env python3
"""Shared attempts log, format v0 (design/v3/30-modes/384-thought-memory.md; creative research thread owns it).

One JSON line per attempt; attempts at the same task share a group_id, so a night can learn from right AND wrong tries.
Rules: only an exact-checker pass is "right"; sleep only reads this file; nothing here ever goes in the notebook.
Groups with no right try are the "not solved yet" shelf (open_shelf below).

  from claude_attempts import log_group
  log_group("attempts.jsonl", "number-puzzle", prompt, tries, verdicts, "claude_blurt1.check@v1", extra={"nums": ...})
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

VERDICTS = {"right", "wrong", "not checkable"}


def group_id(task_kind: str, prompt: str, when: str) -> str:
    return hashlib.sha1(f"{task_kind}|{prompt}|{when}".encode()).hexdigest()[:16]


def log_group(path, task_kind, prompt, tries, verdicts, checker, extra=None, source="own-thought"):
    """tries[i] is the attempt text; verdicts[i] is "right" / "wrong" / "not checkable" (or a dict with a "verdict"
    key plus details such as the value a wrong try reached)."""
    assert len(tries) == len(verdicts)
    when = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    gid = group_id(task_kind, prompt, when)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        for i, (t, v) in enumerate(zip(tries, verdicts)):
            detail = v if isinstance(v, dict) else {"verdict": v}
            assert detail["verdict"] in VERDICTS, detail
            row = {"task_kind": task_kind, "prompt": prompt, "attempt": t, "try": i, **detail, "checker": checker,
                   "time": when, "group_id": gid, "source": source}
            if extra:
                row.update({k: v for k, v in extra.items() if k not in row})
            f.write(json.dumps(row) + "\n")
    return gid


def open_shelf(path):
    """Group ids with no right try (the "not solved yet" shelf)."""
    right, seen = set(), set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        seen.add(r["group_id"])
        if r["verdict"] == "right":
            right.add(r["group_id"])
    return sorted(seen - right)


if __name__ == "__main__":
    import tempfile
    d = Path(tempfile.mkdtemp()) / "a.jsonl"
    g1 = log_group(d, "number-puzzle", "make 24 from 3 8 1", ["3*8*1", "3+8+1"],
                   ["right", {"verdict": "wrong", "value": "12"}], "claude_blurt1.check@v1", {"nums": [3, 8, 1]})
    g2 = log_group(d, "number-puzzle", "make 24 from 1 1 1 1", ["1+1+1+1"], [{"verdict": "wrong", "value": "4"}],
                   "claude_blurt1.check@v1")
    assert open_shelf(d) == [g2] and g1 != g2
    print("selftest ok", d.read_text().splitlines()[1])
