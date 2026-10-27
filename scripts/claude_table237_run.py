#!/usr/bin/env python3
"""Exp 237 case runner: one fresh daemon per case, setup turns, then the
question. Records reply, stored triples before/after the question, and
question time. Usage: run.py <agent.py> <config> <cases.jsonl> <workdir> <out.jsonl>
Case fields used: setup (list or str), question; everything else copied."""
import json, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_marks123_all as M
import fable_loop90_agent as L90

agent, cfgp, cases, work, out = sys.argv[1:6]
mod, dcls, _, _ = M.load_agent(agent)
base = M.load_base_cfg(cfgp)
W = Path(work)
rows = []
for i, line in enumerate(open(cases)):
    if not line.strip():
        continue
    c = json.loads(line)
    root = W / f"c{i:03d}"; shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
    d = M.make_daemon(dcls, base, root)
    setup = c.get("setup") or []
    if isinstance(setup, str):
        setup = [setup]
    turns = list(setup) + [c["question"]]
    replies = []
    before = None
    qms = None
    for j, t in enumerate(turns):
        if j == len(turns) - 1:
            before = sorted(tuple(x) for x in L90.notebook_triples(d.loop.nb))
        f = root / "inbox" / f"m{j:02d}.txt"; f.write_text(t)
        t0 = time.perf_counter(); d.process_file(f); dt = (time.perf_counter() - t0) * 1000
        replies.append((root / "outbox" / f"m{j:02d}.txt").read_text().strip())
        if j == len(turns) - 1:
            qms = dt
    after = sorted(tuple(x) for x in L90.notebook_triples(d.loop.nb))
    row = dict(c, setup_replies=replies[:-1], reply=replies[-1],
               stored_before=before, stored_after=after,
               question_wrote=(before != after), q_ms=qms,
               daemon=dcls.__name__)
    rows.append(row)
    print(f"{c.get('id', i)} [{c.get('family')}] {c['question']!r} -> {replies[-1]!r} wrote={before != after} {qms:.1f}ms", flush=True)
Path(out).write_text("".join(json.dumps(r) + "\n" for r in rows))
