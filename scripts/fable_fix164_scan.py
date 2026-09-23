#!/usr/bin/env python3
"""Experiment 164 -- PRE-SEAL dev scans only (never a registered run).

Pure-function scan: feeds every turn text the registered runs will feed
(bench taught sentences + questions, session152 turns, suite case literals)
through fable_fix164_about.match_about. The new loop (loop164) NEVER runs
before the seal. Base-loop (loop150) calibration runs are allowed pre-seal
(same as exp-150's base calibration) and only inform frozen expectations.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix164_about as A164  # noqa: E402 (pure matcher, no loop)

ROOT = SCRIPTS.parent

LIT_RX = re.compile(
    r"(what\s+do\s+you\s+know|tell\s+me\s+about|anything\s+about|"
    r"what\s+have\s+i\s+told\s+you\s+about)", re.IGNORECASE)


def scan_bench() -> list:
    import fable_loop129b_bench as B129
    fires = []
    n = 0
    for tag, path in (("edit200", B129.DATA_EDIT200),
                      ("old_s2fresh_4hop", B129.DATA_OLD),
                      ("new_121_4hop", B129.DATA_NEW)):
        for line in Path(str(path)).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            it = json.loads(line)
            texts = [str(t.get("sentence_en", "")) for t in it.get("taught", [])]
            texts.append(str(it.get("question", "")))
            for t in texts:
                n += 1
                if A164.match_about(t) is not None:
                    fires.append({"split": tag, "id": it.get("id"), "text": t})
    print(f"bench: {n} turn texts scanned, fires={len(fires)}")
    for f in fires[:20]:
        print(f"  FIRE {f}")
    return fires


def scan_sessions() -> list:
    import fable_session152_sessions as SESS
    fires, n = [], 0
    for s in SESS.SESSIONS:
        for i, t in enumerate(s["turns"]):
            n += 1
            if A164.match_about(str(t.get("text", ""))) is not None:
                fires.append({"session": s["id"], "n": i,
                              "text": str(t.get("text", ""))})
    print(f"sessions152: {n} turns scanned, fires={len(fires)}")
    for f in fires[:20]:
        print(f"  FIRE {f}")
    return fires


def scan_suite_sources() -> list:
    hits = []
    for path in sorted((ROOT / "scripts").glob("*.py")):
        try:
            src = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for i, line in enumerate(src.splitlines(), 1):
            if LIT_RX.search(line) and "164" not in line and "fix164" not in line:
                hits.append(f"{path.name}:{i}:{line.strip()[:110]}")
    for path in sorted((ROOT / "artifacts").glob("*/cases*.json")):
        try:
            src = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in LIT_RX.finditer(src):
            s = max(0, m.start() - 60)
            hits.append(f"{path}:{src[s:m.end() + 40]!r}"[:160])
    print(f"suite sources: {len(hits)} literal hits")
    for h in hits[:40]:
        print(f"  LIT {h}")
    return hits


def unit_checks() -> None:
    must_about = [
        "What do you know about Tom?",
        "WHAT DO YOU KNOW ABOUT TOM?",
        "tell me about tom",
        "Tell me about Tom.",
        "Tell me about Tom!",
        "What have I told you about Tom?",
        "Anything about Tom?",
        "anything about tom?",
        "  What do you know about   Tom  ?  ",
        "What do you know about So-Yeon Ryu?",
        "What do you know about Mary Jane?",
        "What do you know about Tom",
    ]
    must_summary = ["What do you know?", "what do you know", "WHAT DO YOU KNOW?"]
    must_none = [
        "Tom's boss is Ann.",
        "Tell me about yourself.",
        "Tell me about myself.",
        "Tell me about him.",
        "What do you know about Tom and Ann?",
        "What do you know about Tom or Ann?",
        "What do you know about Tom's boss?",
        "What do you know about cooking",  # placeholder: see note below
        "Do you know about Tom?",
        "Tell me a story about Tom.",
        "I know about Tom.",
        "Who is Tom's boss?",
        "Forget Tom city.",
        "Tom's book about cats is good.",
    ]
    bad = 0
    for t in must_about:
        r = A164.match_about(t)
        if r is None or r[0] != "about":
            print(f"  UNIT-FAIL must-about {t!r} -> {r}"); bad += 1
    for t in must_summary:
        if A164.match_about(t) != ("summary",):
            print(f"  UNIT-FAIL must-summary {t!r}"); bad += 1
    for t in must_none:
        if t == "What do you know about cooking":
            continue  # decided at seal: unknown-X FIRES (see PASSMARKS)
        if A164.match_about(t) is not None:
            print(f"  UNIT-FAIL must-none {t!r} -> {A164.match_about(t)}"); bad += 1
    # documented: unknown-X shapes FIRE (unknown-entity reply, predicted move)
    r = A164.match_about("What do you know about cooking?")
    assert r == ("about", "cooking"), r
    print(f"unit: {'ALL OK' if bad == 0 else f'{bad} FAILURES'}")


def main() -> int:
    unit_checks()
    scan_bench()
    scan_sessions()
    scan_suite_sources()
    return 0


if __name__ == "__main__":
    sys.exit(main())
