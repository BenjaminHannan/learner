#!/usr/bin/env python3
"""Exp 232 driver: run one agent over a panel-format JSONL case file.

Each item gets a FRESH daemon + notebook under --work (never the repo
notebook/). Turns = setup[] then question. After every turn it records the
reply, the active taught triples (fable_loop90_agent.notebook_triples) and
ALL taught facts ever written (active or not), and the turn's wall time.

Usage:
  python -B scripts/claude_fullname232_run.py --agent A.py --config C.json \
      --cases cases.jsonl --work /scratch/dir --out rows.jsonl
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


def all_taught(nb) -> list[list[str]]:
    out = []
    for fact in nb.facts.values():
        if fact.get("source") != "taught":
            continue
        out.append([nb.entities.get(fact["subject"], "?"), fact["relation"],
                    L90._display(nb, fact["value"])])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    _mod, dcls, _b, _c = M.load_agent(args.agent)
    base = M.load_base_cfg(args.config)
    work = Path(args.work)
    items = [json.loads(line) for line in
             Path(args.cases).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    with open(args.out, "w", encoding="utf-8") as fh:
        for k, item in enumerate(items):
            root = work / f"i{k:03d}"
            shutil.rmtree(root, ignore_errors=True)
            root.mkdir(parents=True)
            d = M.make_daemon(dcls, base, root)
            turns = list(item.get("setup") or [])
            q = item.get("question")
            if q:
                turns.append(q)
            rows = []
            for j, t in enumerate(turns):
                f = root / "inbox" / f"m{j:02d}.txt"
                f.write_text(t, encoding="utf-8")
                t0 = time.perf_counter()
                d.process_file(f)
                ms = (time.perf_counter() - t0) * 1000.0
                rep = (root / "outbox" / f"m{j:02d}.txt").read_text(
                    encoding="utf-8").strip()
                nb = d.loop.nb
                rows.append({"turn": t, "reply": rep, "ms": ms,
                             "is_question": bool(q) and j == len(turns) - 1,
                             "active": [list(x) for x in
                                        L90.notebook_triples(nb)],
                             "all": all_taught(nb)})
            fh.write(json.dumps({"id": item.get("id"), "turns": rows},
                                ensure_ascii=False) + "\n")
            fh.flush()
            shutil.rmtree(root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
