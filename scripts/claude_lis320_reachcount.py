#!/usr/bin/env python3
"""Counts only: how many gold facts on the sealed lis-320 panel have an owner that the unchanged compiler can accept
from any reader (reading thread, 2026-09-26; ADDENDUM-5). Never prints panel text.

claude_lis300_compiler.check_fact (:44-55) accepts owner "me" only when a first-person word is in the turn or the
previous reply, and any other owner only when it is typed in the turn or the previous reply. A gold fact whose owner
fails that test cannot be saved by any reader under the sealed scoring (claude_lis319_fullclaim.saved_facts :53).
Owner match here is case-insensitive, so the unreachable counts are a lower bound.
python -B scripts/claude_lis320_reachcount.py [--panel artifacts/claude-readpanel320-20260926/panel.jsonl]
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis300_compiler as CMP  # noqa: E402


def span_ci(o, h):
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(o.strip()) + r"(?:'s|’s|s)?(?![A-Za-z0-9])", h, re.I) is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="artifacts/claude-readpanel320-20260926/panel.jsonl")
    a = ap.parse_args()
    c = Counter()
    for line in Path(a.panel).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        t, p = r["turn"], r.get("prev_reply") or ""
        for g in r["facts"]:
            o = str(g["owner"])
            ok = bool(CMP.ME_WORDS.search(t) or CMP.ME_WORDS.search(p)) if o == "USER" else (span_ci(o, t) or span_ci(o, p))
            c["facts"] += 1
            c["facts_unreachable"] += not ok
            if g.get("correction"):
                c["correction_facts"] += 1
                c["correction_unreachable"] += not ok
            if r["kind"] == "backref":
                c["backref_facts"] += 1
                c["backref_unreachable"] += not ok
    print(json.dumps(dict(c)))


if __name__ == "__main__":
    main()
