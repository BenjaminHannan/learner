#!/usr/bin/env python3
"""ocdiag2 single-call wrapper (standard library only).

Given --helper v1|v11 and a prompt file, imports claude_glm_opencode (v1)
or claude_glm_opencode_v11 (v11) from scripts/, calls call(text) once,
catches any exception, and prints one JSON line to stdout:
  helper, id, ok, seconds, reply_chars, reply_head, parses, error.
Before the call, prints `uptime` load averages to stderr (stdout stays
exactly one JSON line).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.dirname(HERE)  # $O is $D/ocdiag2
sys.path.insert(0, os.path.join(D, "scripts"))

_PATH_RE = re.compile(r"/(?:[\w.\-]+/)+[\w.\\-]+")


def scrub(s):
    return _PATH_RE.sub("<path>", s or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--helper", required=True, choices=["v1", "v11"])
    ap.add_argument("prompt", help="prompt file, e.g. p_s320-321-00004.txt")
    ap.add_argument("--seeds", default=os.path.join(D, "seeds.jsonl"))
    a = ap.parse_args()
    base = os.path.basename(a.prompt)
    did = base[2:-4] if base.startswith("p_") and base.endswith(".txt") else base
    with open(a.prompt, encoding="utf-8") as f:
        text = f.read()
    try:
        up = subprocess.run(["uptime"], capture_output=True, text=True, timeout=30)
        print("uptime before call: " + (up.stdout or up.stderr or "").strip(),
              file=sys.stderr, flush=True)
    except Exception as e:
        print("uptime before call: unavailable (%s)" % scrub(str(e))[:150],
              file=sys.stderr, flush=True)
    n_turns = None
    try:
        with open(a.seeds, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if d.get("dialog_id") == did:
                    n_turns = len(d.get("turns", []))
                    break
    except Exception as e:
        print("seeds read failed: %s" % scrub(str(e))[:150], file=sys.stderr)
    t0 = time.time()
    ok = False
    reply = ""
    err = ""
    try:
        if a.helper == "v1":
            import claude_glm_opencode as h
        else:
            import claude_glm_opencode_v11 as h
        reply = h.call(text) or ""
        ok = True
    except Exception as e:
        err = scrub(str(e))[:300]
    except BaseException as e:  # e.g. SystemExit from helper
        err = scrub("%s: %s" % (type(e).__name__, e))[:300]
    dt = time.time() - t0
    parses = False
    if ok:
        try:
            from claude_lis320_glm import parse as lis_parse
            parses = lis_parse(reply, n_turns or 0) is not None
        except Exception:
            parses = False
    rec = {
        "helper": a.helper,
        "id": did,
        "ok": ok,
        "seconds": round(dt, 1),
        "reply_chars": len(reply),
        "reply_head": scrub(reply[:200]),
        "parses": parses,
        "error": err,
    }
    print(json.dumps(rec), flush=True)


if __name__ == "__main__":
    main()
