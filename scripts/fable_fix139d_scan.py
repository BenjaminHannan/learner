#!/usr/bin/env python3
"""Experiment 139d -- PRE-SEAL static scan (not a registered run).

Extracts teach-like possessive value spans from the frozen G1/G3 inputs,
applies 139c's strip then the 139d unknown-tail check, and lists hits.
Basis for the PASSMARKS 0-move predictions. Reads only; writes stdout.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix139c_tail as T139c  # noqa: E402 (read-only)
import fable_fix139d_tail as T139d  # noqa: E402 (read-only)

POSS = re.compile(r"\b([A-Z][\w.'-]*)'s\s+([\w /-]+?)\s+is\s+(.+?)\s*$",
                  re.IGNORECASE)


def spans_from_text(text: str) -> list[str]:
    vals = []
    for line in str(text).splitlines():
        m = POSS.search(line.strip())
        if m:
            vals.append(m.group(3).strip().rstrip("."))
    return vals


def check_spans(tag: str, texts: list[str]) -> list[dict]:
    hits = []
    for t in texts:
        for v in spans_from_text(t):
            cleaned, _ = T139c.strip_chat_tail(v)
            split = T139d.unknown_tail_split(cleaned)
            if split is not None:
                hits.append({"suite": tag, "raw": v, "clean139c": cleaned,
                             "base": split[0], "tail": split[1]})
    return hits


def main() -> int:
    all_hits: list[dict] = []
    # G1 bench inputs
    spec = importlib.util.spec_from_file_location(
        "fable_loop138b_bench121",
        ROOT / "artifacts" / "fable-agent138b-20260922"
        / "fable_loop138b_bench121.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for stag, path, _s in list(mod.SPLITS_3) + [mod.SPLIT_132]:
        items = [json.loads(x) for x in Path(str(path)).read_text(
            encoding="utf-8").splitlines() if x.strip()]
        texts = [json.dumps(it, ensure_ascii=False) for it in items]
        all_hits += check_spans(f"bench:{stag}", texts)
    # G3 redteam136 inputs
    cases136 = json.loads((ROOT / "artifacts" / "fable-redteam136-20260922"
                           / "cases136.json").read_text(encoding="utf-8"))
    all_hits += check_spans("rt136", [json.dumps(c, ensure_ascii=False)
                                      for c in cases136])
    # G3 redteam143 inputs
    import fable_redteam143_run as R143  # noqa: E402 (read-only)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    all_hits += check_spans("rt143", [json.dumps(c, ensure_ascii=False)
                                      for c in suite["cases"]])
    # G3 sessions152 inputs
    import fable_session152_run as S152R  # noqa: E402 (read-only)
    stexts = [json.dumps(s, ensure_ascii=False)
              for s in S152R.S152.SESSIONS]
    all_hits += check_spans("sessions152", stexts)
    print(f"scan139d: {len(all_hits)} trigger-shaped spans")
    for h in all_hits[:50]:
        print(f"  HIT {h['suite']}: raw={h['raw']!r} "
              f"clean139c={h['clean139c']!r} tail={h['tail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
