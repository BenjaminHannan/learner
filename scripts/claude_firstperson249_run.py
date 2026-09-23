#!/usr/bin/env python3
"""Exp 249 driver: run base228 and loop249 over a case file, interleaved.

For every item, each arm gets a FRESH daemon + notebook under --work (never
the repo notebook/). Turns = setup[] then question. Per arm it records the
setup replies, the active taught triples after setup and after the question,
every taught triple ever written, the question reply and the question's wall
time (ms). Arms alternate per item (order flips every item) so timing is
measured in the same session under the same load.

Case files: dev249.jsonl (this experiment) or the ask panel 243 panel.jsonl.
For the panel (--panel-dir), the 243 schema is checked FIRST with the
scorer's check; any mismatch prints SCHEMA-MISMATCH and exits 3.

Usage:
  python -B scripts/claude_firstperson249_run.py --cases FILE --work DIR \
      --out rows.jsonl [--panel-dir artifacts/claude-askpanel243-20260922]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_loop90_agent as L90  # noqa: E402 (read-only)
import fable_marks123_all as M  # noqa: E402 (agent loader, read-only)

ARMS = {
    "base228": ("scripts/claude_loop228_agent.py",
                "artifacts/claude-determinism228-20260922/loop228-config.json"),
    "loop249": ("scripts/claude_loop249_agent.py",
                "artifacts/claude-firstperson249-20260922/loop249-config.json"),
}


def all_taught(nb) -> list[list[str]]:
    out = []
    for fact in nb.facts.values():
        if fact.get("source") != "taught":
            continue
        out.append([nb.entities.get(fact["subject"], "?"), fact["relation"],
                    L90._display(nb, fact["value"])])
    return out


def run_item(dcls, base, root: Path, setup: list[str], question: str) -> dict:
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    d = M.make_daemon(dcls, base, root)
    rec: dict = {"setup_replies": []}
    turns = list(setup) + [question]
    for j, t in enumerate(turns):
        f = root / "inbox" / f"m{j:02d}.txt"
        f.write_text(t, encoding="utf-8")
        t0 = time.perf_counter()
        d.process_file(f)
        ms = (time.perf_counter() - t0) * 1000.0
        rep = (root / "outbox" / f"m{j:02d}.txt").read_text(
            encoding="utf-8").strip()
        nb = d.loop.nb
        if j < len(setup):
            rec["setup_replies"].append(rep)
            if j == len(setup) - 1:
                rec["stored_after_setup"] = [list(x) for x in
                                             L90.notebook_triples(nb)]
                rec["all_after_setup"] = all_taught(nb)
        else:
            rec["reply"] = rep
            rec["q_ms"] = ms
            rec["stored_after_question"] = [list(x) for x in
                                            L90.notebook_triples(nb)]
            rec["all_after_question"] = all_taught(nb)
    if not setup:
        rec["stored_after_setup"], rec["all_after_setup"] = [], []
    shutil.rmtree(root, ignore_errors=True)
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--panel-dir", default=None)
    args = ap.parse_args(argv)
    if args.panel_dir:
        import claude_firstperson249_score as S  # noqa: E402
        S.check_panel_schema_or_exit(args.panel_dir)
    loaded = {}
    for arm, (agent, cfg) in ARMS.items():
        _mod, dcls, _b, _c = M.load_agent(agent)
        loaded[arm] = (dcls, M.load_base_cfg(cfg))
    items = [json.loads(line) for line in
             Path(args.cases).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    work = Path(args.work)
    order = list(ARMS)
    with open(args.out, "w", encoding="utf-8") as fh:
        for k, item in enumerate(items):
            row = {"id": item["id"]}
            arms = order if k % 2 == 0 else order[::-1]
            for arm in arms:
                dcls, base = loaded[arm]
                row[arm] = run_item(dcls, base, work / f"{arm}-{k:03d}",
                                    item.get("setup") or [],
                                    item["question"])
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
