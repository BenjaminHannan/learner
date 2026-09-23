#!/usr/bin/env python3
"""Merge 138k driver: restart-aware dialog probe with duplicate checks.

Same turn path as artifacts/claude-verify-20260922/restart_probe.py
(fable_marks123_all.make_daemon + process_file, "__RESTART__" rebuilds the
daemon on the same root, "__TRIPLES__" snapshots). Adds, after EVERY
restart and at the end of every dialog, a duplicate audit:
  fast  = L90.notebook_triples(nb)       (170-cached, index-backed)
  truth = fix170 _ORIG_TRIPLES(nb)       (full nb.facts scan, no index)
  inner = inner._triples fact ids        (the 220-rebuilt index)
dup_ok iff fast has no repeated triple, inner has no repeated fact id, and
sorted(fast) == sorted(truth).

usage: claude_merge138k_probe.py <agent.py> <config> <workdir> <probe.json> <out.json>
"""
from __future__ import annotations

import gc
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_marks123_all as M  # noqa: E402 (read-only)


def main() -> int:
    agent, config, work, probe, out = sys.argv[1:6]
    mod, dcls, _, _ = M.load_agent(agent)
    import fable_fix170_compose as F170  # after the agent import
    import fable_loop90_agent as L90
    base = M.load_base_cfg(config)
    S = Path(work)
    dialogs = json.loads(Path(probe).read_text(encoding="utf-8"))

    def nev(d):
        nb = d.loop.nb
        for o in (nb, getattr(nb, "nb", None)):
            if o is not None and hasattr(o, "events"):
                return len(o.events)
        return -1

    def audit(d, where):
        nb = d.loop.nb
        fast = [tuple(x) for x in L90.notebook_triples(nb)]
        truth = [tuple(x) for x in F170._ORIG_TRIPLES(nb)]
        inner = getattr(nb, "nb", nb)
        ids = [t[0] for t in getattr(inner, "_triples", [])]
        dup_fast = sorted(k for k, v in Counter(fast).items() if v > 1)
        dup_ids = sorted(k for k, v in Counter(ids).items() if v > 1)
        ok = (not dup_fast and not dup_ids
              and sorted(fast) == sorted(truth))
        return {"where": where, "fast": [list(t) for t in fast],
                "truth": [list(t) for t in truth],
                "dup_fast": [list(t) for t in dup_fast],
                "dup_ids": dup_ids, "dup_ok": ok}

    rows = []
    for i, msgs in enumerate(dialogs):
        root = S / f"d{i:02d}"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        d = M.make_daemon(dcls, base, root)
        k = 0
        nres = 0
        turns = []
        audits = []
        for t in msgs:
            if t == "__RESTART__":
                del d
                gc.collect()
                d = M.make_daemon(dcls, base, root)
                nres += 1
                print(f"{i:02d} -- RESTART {nres} --", flush=True)
                audits.append(audit(d, f"restart{nres}"))
                continue
            if t == "__TRIPLES__":
                a = audit(d, f"triples@{k}")
                audits.append(a)
                print(f"{i:02d}   TRIPLES {a['fast']}", flush=True)
                continue
            f = root / "inbox" / f"m{k:02d}.txt"
            f.write_text(t)
            b = nev(d)
            try:
                d.process_file(f)
                rep = (root / "outbox" / f"m{k:02d}.txt").read_text().strip()
            except Exception as e:  # noqa: BLE001
                rep = f"CRASH {type(e).__name__}: {e}"
            w = nev(d) - b
            print(f"{i:02d} {t!r} -> {rep!r}  [+{w} ev]", flush=True)
            turns.append({"turn": t, "reply": rep, "events": w})
            k += 1
        end = audit(d, "end")
        audits.append(end)
        print(f"{i:02d}   STORED {end['fast']}  dup_ok={end['dup_ok']}",
              flush=True)
        rows.append({"dialog": i, "turns": turns, "audits": audits,
                     "stored": end["fast"],
                     "dup_ok_all": all(a["dup_ok"] for a in audits)})
    Path(out).write_text(json.dumps({"agent": agent, "rows": rows},
                                    indent=1, ensure_ascii=False),
                         encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
