#!/usr/bin/env python3
"""Dev probe (pre-seal): loop138 self-path sets on bench splits + rt110 S1."""

from __future__ import annotations

import copy
import json
import re
import shutil
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent

import fable_bench121_run as B  # noqa: E402
import fable_loop138_agent as L138  # noqa: E402
import fable_loop161_agent as L161  # noqa: E402

DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"


def probe(mod, tag, item):
    loop = mod.build(tag, item) if False else None
    return None


def build138(tag):
    st = SCRIPTS / "scratchpad" / "probe138b"
    return L138.build_agent138({"state_dir": str(st),
                                "sleep_threshold": 100000})


def build161(tag):
    st = SCRIPTS / "scratchpad" / "probe161c"
    return L161.build_agent161({"state_dir": str(st),
                                "sleep_threshold": 100000})


def routed_set(mod, items, limit=None):
    content, decline = [], []
    for it in items[:limit]:
        st = SCRIPTS / "scratchpad" / ("pr138" if mod is L138 else "pr161")
        if st.exists():
            shutil.rmtree(st)
        b = (L138.build_agent138 if mod is L138 else L161.build_agent161)(
            {"state_dir": str(st), "sleep_threshold": 100000})
        for t in it["taught"]:
            b.turn(str(t["sentence_en"]))
        b.turn(str(it["question"]))
        if b.last_routed is not None:
            if b.last_routed["intent"] == "DECLINE":
                decline.append(it["id"])
            else:
                content.append((it["id"], b.last_routed["intent"]))
    return content, decline


def main() -> int:
    splits = {
        "new": [json.loads(l) for l in B.DATA_NEW.read_text(
            encoding="utf-8").splitlines() if l.strip()],
        "old": [json.loads(l) for l in B.DATA_OLD.read_text(
            encoding="utf-8").splitlines() if l.strip()],
        "edit200": [json.loads(l) for l in DATA134.read_text(
            encoding="utf-8").splitlines() if l.strip()],
    }
    for tag, items in splits.items():
        c138, d138 = routed_set(L138, items)
        c161, d161 = routed_set(L161, items)
        print(f"{tag}: 138 content={c138} decline_n={len(d138)}", flush=True)
        print(f"{tag}: 161 content={c161} decline_n={len(d161)}", flush=True)
    # rt110 S1 case text
    import fable_redteam110_cases as RC110  # noqa: E402
    cases = RC110.CASES if hasattr(RC110, "CASES") else None
    print("RC110 attrs:", [a for a in dir(RC110) if not a.startswith("_")],
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
