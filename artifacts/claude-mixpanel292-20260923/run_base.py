#!/usr/bin/env python3
"""Merge 292 blind panel: run every item on base 291 (CPU, one at a time).

Reads artifacts/claude-mixpanel292-20260923/panel.jsonl, writes
artifacts/claude-mixpanel292-20260923/base291.jsonl with one row per item:
{id, family, setup_replies, question_reply, question_stage
 (loop.ears.last_stage), stored_after_setup_actual,
 stored_after_question_actual, question_wrote}.

Base: scripts/claude_loop291_agent (DEFAULT_CONFIG291; the config file
holds absolute paths so the module default is used), fresh temp state_dir
per item outside the repo, sleep_threshold 100000.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import claude_loop291_agent as A291  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)

PANEL = HERE / "panel.jsonl"
OUT = HERE / "base291.jsonl"


def facts_hash(nb) -> str:
    blob = json.dumps({"facts": nb.facts,
                       "retracted": sorted(getattr(nb, "retracted", [])),
                       "superseded": sorted(getattr(nb, "superseded", []))},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def stored(nb) -> list[list[str]]:
    return [list(x) for x in L90.notebook_triples(nb)]


def run_item(item: dict, base_cfg: dict) -> dict:
    sd = tempfile.mkdtemp(prefix="m292-base-")
    try:
        cfg = copy.deepcopy(base_cfg)
        cfg["state_dir"] = str(sd)
        cfg["sleep_threshold"] = 100000
        loop = A291.build_agent291(cfg)
        setup_replies = []
        for t in item["setup"]:
            try:
                setup_replies.append(" ".join(loop.turn(str(t))))
            except Exception as e:  # noqa: BLE001 -- record, never stop
                setup_replies.append(f"ERROR: {type(e).__name__}: {e}")
        after_setup = stored(loop.nb)
        h0 = facts_hash(loop.nb)
        try:
            qreply = " ".join(loop.turn(str(item["question"])))
        except Exception as e:  # noqa: BLE001
            qreply = f"ERROR: {type(e).__name__}: {e}"
        stage = str(getattr(getattr(loop, "ears", None), "last_stage", ""))
        return {"id": item["id"], "family": item["family"],
                "setup_replies": setup_replies, "question_reply": qreply,
                "question_stage": stage,
                "stored_after_setup_actual": after_setup,
                "stored_after_question_actual": stored(loop.nb),
                "question_wrote": facts_hash(loop.nb) != h0}
    finally:
        shutil.rmtree(sd, ignore_errors=True)


def main() -> int:
    items = [json.loads(line) for line in PANEL.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    assert len(items) == 80, len(items)
    base_cfg = copy.deepcopy(A291.DEFAULT_CONFIG291)
    rows = []
    for i, item in enumerate(items):
        row = run_item(item, base_cfg)
        rows.append(row)
        print(f"[{i + 1:02d}/80] {row['id']} {row['family']} "
              f"stage={row['question_stage']} wrote={row['question_wrote']} "
              f"q={row['question_reply'][:70]!r}", flush=True)
    OUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
