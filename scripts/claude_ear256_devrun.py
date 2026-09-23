#!/usr/bin/env python3
"""Exp 256 -- run one arm (agent + config) over a panel-254-shaped case file.

Per item: fresh work dir; setup turns ("__RESTART__" rebuilds the daemon on the
same root), then turn, then followup. Records replies, the store after setup /
turn / followup (L90.notebook_triples, as scratchpad/dialog_nb.py reads it), the
256 ear trace when present, per-turn wall time, and a duplicate audit
(fast vs fix170 _ORIG_TRIPLES) at the end of every dialog.

usage: claude_ear256_devrun.py --agent A --config C --cases X.jsonl --out O.jsonl --work DIR
"""
from __future__ import annotations

import argparse
import gc
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import fable_marks123_all as M  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--only", default=None, help="comma list of ids")
    a = ap.parse_args()
    _, dcls, _, _ = M.load_agent(a.agent)
    import fable_fix170_compose as F170  # after the agent import
    import fable_loop90_agent as L90
    base = M.load_base_cfg(a.config)
    items = [json.loads(x) for x in Path(a.cases).read_text().splitlines() if x.strip()]
    if a.only:
        keep = set(a.only.split(","))
        items = [x for x in items if x["id"] in keep]
    W = Path(a.work)

    def store(d):
        return sorted([list(t) for t in {tuple(x) for x in L90.notebook_triples(d.loop.nb)}])

    def dup_ok(d):
        nb = d.loop.nb
        fast = [tuple(x) for x in L90.notebook_triples(nb)]
        truth = [tuple(x) for x in F170._ORIG_TRIPLES(nb)]
        return (not any(v > 1 for v in Counter(fast).values())) and sorted(fast) == sorted(truth)

    out = open(a.out, "w", encoding="utf-8")
    print(f"daemon={dcls.__name__} items={len(items)}", flush=True)
    for it in items:
        root = W / it["id"]
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        d = M.make_daemon(dcls, base, root)
        k = [0]
        traces = []

        def say(t):
            f = root / "inbox" / f"m{k[0]:02d}.txt"
            f.write_text(t, encoding="utf-8")
            n0 = len(getattr(d.loop, "ear256_log", []) or [])
            t0 = time.perf_counter()
            d.process_file(f)
            ms = (time.perf_counter() - t0) * 1000
            rep = (root / "outbox" / f"m{k[0]:02d}.txt").read_text(encoding="utf-8").strip()
            k[0] += 1
            tr = (getattr(d.loop, "ear256_log", []) or [])[n0:]
            traces.append(dict(text=t, ms=round(ms, 1), trace=tr))
            return rep

        setup_replies = []
        restarts = 0
        for t in it["setup"]:
            if t == "__RESTART__":
                del d
                gc.collect()
                d = M.make_daemon(dcls, base, root)
                restarts += 1
                setup_replies.append("__RESTART__")
                continue
            setup_replies.append(say(t))
        s_setup = store(d)
        turn_reply = say(it["turn"])
        s_turn = store(d)
        fu = say(it["followup"]) if it.get("followup") else None
        s_fu = store(d)
        rec = dict(id=it["id"], setup_replies=setup_replies, stored_after_setup=s_setup,
                   turn_reply=turn_reply, stored_after_turn=s_turn, followup_reply=fu,
                   stored_after_followup=s_fu, dup_ok=dup_ok(d), restarts=restarts, turns=traces)
        out.write(json.dumps(rec) + "\n")
        out.flush()
        print(it["id"], "|", it["turn"][:40], "->", turn_reply[:70].replace("\n", " "), flush=True)
        del d
        gc.collect()
        shutil.rmtree(root, ignore_errors=True)
    out.close()


if __name__ == "__main__":
    main()
