#!/usr/bin/env python3
"""Exp 280p held-out probe: run chatweak-format dialogs (dev material) on one arm.

  chatweak <agent.py> <config> <workdir> <chatweak.json> <out.json>

Fresh notebook per dialog, turns in order. Records per-turn reply, write
deltas and stores. Never scores. Driver (Runner/send/trip) is reused
read-only from scripts/claude_openers260_run.py so all arms run identically,
exactly like the sealed scripts/claude_join280m_run.py panel mode.
"""

import gc
import json
import re
import shutil
import sys

sys.path.insert(0, "scripts")
import claude_openers260_run as R260  # noqa: E402 (read-only driver)
import fable_marks123_all as M  # noqa: E402 (read-only daemon maker)


def slug(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(s))[:60] or "item"


def main(argv):
    mode, agent, config, work, src, dst = argv[1:7]
    assert mode == "chatweak", "mode must be chatweak"
    r = R260.Runner(agent, config, work)
    dialogs = json.load(open(src))
    out = []
    for dg in dialogs:
        root, d = r.fresh(slug(dg["id"]))
        rows, k = [], 0
        for row in dg["rows"]:
            if row.get("restart"):
                del d
                gc.collect()
                d = M.make_daemon(r.dcls, r.base, root)
                rows.append({"turn": "__RESTART__", "reply": "",
                             "ev": 0, "triples": R260.trip(d)})
                continue
            t = row["text"]
            assert str(t).strip() != "", \
                f"empty turn in dialog {dg.get('id')!r}; refusing"
            rep, ev, _s = r.send(d, root, k, t)
            rows.append({"turn": t, "reply": rep, "ev": ev,
                         "triples": R260.trip(d)})
            k += 1
        out.append({"id": dg["id"], "theme": dg.get("theme", ""),
                    "rows": rows, "stored": R260.trip(d)})
        del d
        gc.collect()
        shutil.rmtree(root, ignore_errors=True)
    json.dump(out, open(dst, "w"), indent=1)
    n_turns = sum(len(d["rows"]) for d in out)
    print(f"done {len(out)} dialogs, {n_turns} turns -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
