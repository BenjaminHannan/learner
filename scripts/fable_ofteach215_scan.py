#!/usr/bin/env python3
"""Experiment 215 -- pure-function pre-seal scan (Muse).

Applies the 215 rewrite predicates (no agent, no notebook writes) to every
turn text in the frozen suites + bench + marks123-visible texts and lists
cases where a rewrite COULD fire. Teach side is exact with nb=None
(name-like Y only; the known-entity branch can only fire mid-session for
a lowercase Y, which the scan flags separately). Question side is
reported as "gate-open" candidates (split succeeds; the R-known gate is
checked live in the pilot).

Read-only; prints a short list for PASSMARKS.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from fable_loop215_agent import (  # noqa: E402
    rewrite_question215, rewrite_teach215, split_middle215)

ROOT = SCRIPTS.parent


def collect() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    # rt136
    cases = json.loads((ROOT / "artifacts" / "fable-redteam136-20260922"
                        / "cases136.json").read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    for c in cases:
        for k in ("text", "turn", "sentence", "input", "question"):
            if isinstance(c.get(k), str):
                out.append((f"rt136/{c.get('id', '?')}:{k}", c[k]))
        for t in c.get("turns", []) or []:
            out.append((f"rt136/{c.get('id', '?')}",
                        t if isinstance(t, str) else str(t.get("text", t))))
        for t in c.get("teaches", []) or []:
            out.append((f"rt136/{c.get('id', '?')}:teaches",
                        t if isinstance(t, str) else str(t)))
    # rt143
    import fable_redteam143_run as R143  # noqa: E402
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    for c in suite["cases"]:
        for k in ("text", "turn", "sentence", "input", "question"):
            if isinstance(c.get(k), str):
                out.append((f"rt143/{c.get('id', '?')}:{k}", c[k]))
        for t in c.get("turns", []) or []:
            out.append((f"rt143/{c.get('id', '?')}",
                        t if isinstance(t, str) else str(t.get("text", t))))
        for t in c.get("teaches", []) or []:
            out.append((f"rt143/{c.get('id', '?')}:teaches",
                        t if isinstance(t, str) else str(t)))
    # sessions152
    import fable_session152_run as S152R  # noqa: E402
    for s in S152R.S152.SESSIONS:
        for i, t in enumerate(s.get("turns", []) or []):
            txt = t if isinstance(t, str) else str(t.get("text", t))
            out.append((f"sessions152/{s['id']}#{i}", txt))
    # bench splits (teach sentences + questions)
    import fable_bench121_run as B  # noqa: E402
    for stag, path in (("new_121_4hop", B.DATA_NEW),
                       ("old_s2fresh_4hop", B.DATA_OLD),
                       ("edit200", str(ROOT / "data" / "open" / "bench65"
                                       / "fable_edit_200.jsonl")),
                       ("bench132_4hop", str(ROOT / "data" / "open"
                                             / "bench132"
                                             / "fable_edit132_4hop.jsonl"))):
        for line in Path(str(path)).read_text(
                encoding="utf-8").splitlines():
            if not line.strip():
                continue
            it = json.loads(line)
            for k in ("sentence_en", "question", "text", "teach",
                      "sentence"):
                if isinstance(it.get(k), str):
                    out.append((f"bench/{stag}/{it.get('id', '?')}:{k}",
                                it[k]))
            for t in it.get("taught", []) or []:
                s = t if isinstance(t, str) else t.get("sentence_en", "")
                if s:
                    out.append((f"bench/{stag}/{it.get('id', '?')}:taught",
                                str(s)))
    return out


class OpenGate:
    """Mock notebook: holds a broad relation set (over-approx for the scan)."""

    events = [{"kind": "RELATION", "relation": r} for r in (
        "boss brother father friend husband mother neighbour neighbor "
        "partner sister teacher wife city capital composer founder author "
        "discoverer inventor mentor rival scout warden keeper herald envoy "
        "apprentice citizen captain doctor driver lawyer owner director "
        "child son daughter sibling colleague language genre sport "
        "continent employer occupation official_language place_of_death "
        "country_of_citizenship").split()]


def main() -> int:
    turns = collect()
    print(f"scanned {len(turns)} turn texts", flush=True)
    teach_fires, q_candidates = [], []
    for tag, text in turns:
        try:
            r = rewrite_teach215(text, None)
        except Exception as e:  # noqa: BLE001
            r = f"<error {e}>"
        if r is not None:
            teach_fires.append((tag, text, r))
        try:
            q = rewrite_question215(text, OpenGate())
        except Exception as e:  # noqa: BLE001
            q = f"<error {e}>"
        if q is not None:
            q_candidates.append((tag, text, q))
    print(f"TEACH fires (nb=None): {len(teach_fires)}", flush=True)
    for tag, text, r in teach_fires[:40]:
        print(f"  T {tag}: {text[:100]!r} -> {r[:100]!r}", flush=True)
    print(f"QUESTION gate-open candidates: {len(q_candidates)}", flush=True)
    for tag, text, q in q_candidates[:40]:
        print(f"  Q {tag}: {text[:100]!r} -> {q[:100]!r}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
