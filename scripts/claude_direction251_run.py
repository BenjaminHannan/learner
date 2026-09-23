"""Exp 251 runner: one fresh work dir per item; setup turns, then the one
scored question (timed). Reads any jsonl with id / setup / question (dev251
cases or the askpanel243 panel.jsonl). Writes one row per item:
  id, setup_replies, stored_after_setup, reply, stored_after_question, q_ms
Usage: claude_direction251_run.py --agent A --config C --cases F --work DIR --out OUT
The work dir is a scratch dir (never the repo notebook/).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_marks123_all as M  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)


def _stored(d) -> list[list[str]]:
    return [list(x) for x in L90.notebook_triples(d.loop.nb)]


def run(agent: str, config: str, cases: str, work: str, out: str) -> int:
    _mod, dcls, _b, _c = M.load_agent(agent)
    base = M.load_base_cfg(config)
    items = [json.loads(x) for x in Path(cases).read_text().splitlines()
             if x.strip()]
    W = Path(work)
    if W.resolve() == (SCRIPTS.parent / "notebook").resolve():
        raise SystemExit("refusing to use the repo notebook/")
    rows = []
    for it in items:
        root = W / it["id"]
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        d = M.make_daemon(dcls, base, root)
        reps = []
        for j, t in enumerate(it["setup"]):
            f = root / "inbox" / f"m{j:02d}.txt"
            f.write_text(t)
            d.process_file(f)
            reps.append((root / "outbox" / f"m{j:02d}.txt").read_text()
                        .strip())
        s1 = _stored(d)
        j = len(it["setup"])
        f = root / "inbox" / f"m{j:02d}.txt"
        f.write_text(it["question"])
        t0 = time.perf_counter()
        d.process_file(f)
        q_ms = (time.perf_counter() - t0) * 1000.0
        rep = (root / "outbox" / f"m{j:02d}.txt").read_text().strip()
        rows.append({"id": it["id"], "setup_replies": reps,
                     "stored_after_setup": s1, "reply": rep,
                     "stored_after_question": _stored(d), "q_ms": q_ms})
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"wrote {len(rows)} rows -> {out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return run(a.agent, a.config, a.cases, a.work, a.out)


if __name__ == "__main__":
    sys.exit(main())
