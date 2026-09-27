#!/usr/bin/env python3
"""Two-process isolation worker: 4 sequential v11 calls with before/after glm11 listing.

Logs count and titles only (no ids, no config). Additive test driver.
"""
import json
import subprocess
import sys
import datetime

PROJECT_DIR = "/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27"
OPENCODE = "/usr/local/bin/opencode"

sys.path.insert(0, PROJECT_DIR + "/scripts")
from claude_glm_opencode_v11 import call as glm_call


def list_glm11():
    p = subprocess.run(
        [OPENCODE, "session", "list", "-n", "1000", "--format", "json"],
        cwd=PROJECT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, timeout=60)
    if p.returncode != 0:
        return -1, []
    try:
        items = json.loads(p.stdout.decode("utf-8", "replace") or "[]")
    except Exception:
        return -2, []
    if isinstance(items, dict):
        items = items.get("sessions", [])
    titles = [s.get("title", "") for s in items
              if isinstance(s, dict) and str(s.get("title", "")).startswith("glm11-")]
    return len(titles), sorted(titles)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    proc = sys.argv[sys.argv.index("--proc") + 1]
    out = sys.argv[sys.argv.index("--out") + 1]
    words = sys.argv[sys.argv.index("--words") + 1].split(",")
    assert len(words) == 4
    with open(out, "w") as f:
        for i, w in enumerate(words):
            prompt = "Reply with only the word %s" % w
            tb = now()
            bc, bt = list_glm11()
            t0 = now()
            try:
                reply = glm_call(prompt, timeout=300)
                err = ""
            except Exception as e:
                reply = ""
                err = str(e)[:300]
            t1 = now()
            ac, at = list_glm11()
            ta = now()
            rec = {"proc": proc, "i": i, "word": w, "t_before": tb,
                   "before_count": bc, "before_titles": bt,
                   "t_call_start": t0, "t_call_end": t1,
                   "reply": reply, "error": err,
                   "after_count": ac, "after_titles": at, "t_after": ta}
            f.write(json.dumps(rec) + "\n")
            f.flush()
    print("worker %s done" % proc)


if __name__ == "__main__":
    main()
