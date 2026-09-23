#!/usr/bin/env python3
"""Exp 281 post-seal panel driver (NEW file; sealed files unchanged).

The blind calledpanel281 writer used per-turn rows
{dialog_id, turn_index, user_text, category, gold} (see
artifacts/claude-calledpanel281-20260923/README.md), while the sealed
scripts/claude_called281_run.py loads whole-dialog items
{id, setup[], turn, followup} or {id, turns[]}. This driver runs the
writer's schema directly: one fresh daemon per dialog_id, turns in
turn_index order, recording per-turn reply/ev/triples. It never scores
and never prints turn text.

  panelrun <agent.py> <config> <workdir> <panel.jsonl> <out.json>

out.json: [{dialog_id, turn_index, reply, ev, triples}]. No user text or
gold is copied into the rows (the scorer joins with the panel file).
Daemon handling (Runner/send/trip) is reused read-only from
scripts/claude_openers260_run.py so both arms run identically.
"""

import gc
import json
import re
import shutil
import sys

sys.path.insert(0, "scripts")
import claude_openers260_run as R260  # noqa: E402 (read-only driver)


def slug(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(s))[:60] or "item"


def load_panel(path):
    items = []
    for line in open(path).read().splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    for it in items:
        for k in ("dialog_id", "turn_index", "user_text", "category",
                  "gold"):
            if k not in it:
                raise SystemExit(f"panelrun: missing field {k!r} "
                                 f"in item {it.get('dialog_id', '?')}")
    return items


def main(argv):
    _mode, agent, config, work, src, dst = argv[1:7]
    assert _mode == "panelrun"
    items = load_panel(src)
    dialogs = {}
    for it in items:
        dialogs.setdefault(it["dialog_id"], []).append(it)
    for ts in dialogs.values():
        ts.sort(key=lambda t: t["turn_index"])
    r = R260.Runner(agent, config, work)
    out = []
    for did, ts in sorted(dialogs.items()):
        root, d = r.fresh(slug(did))
        k = 0
        for it in ts:
            rep, ev, _s = r.send(d, root, k, it["user_text"])
            out.append({"dialog_id": did, "turn_index": it["turn_index"],
                        "reply": rep, "ev": ev, "triples": R260.trip(d)})
            k += 1
        del d
        gc.collect()
        shutil.rmtree(root, ignore_errors=True)
    json.dump(out, open(dst, "w"), indent=1)
    print(f"done {len(dialogs)} dialogs {len(out)} turns")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
