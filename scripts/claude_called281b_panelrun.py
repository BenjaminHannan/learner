#!/usr/bin/env python3
"""Exp 281b blind-panel runner (dialog-wise; schema-gated).

The blind calledpanel281b writer uses per-turn rows, one row per turn:
  {dialog_id, turn_index, user_text, category, gold}
The runner ALSO accepts the key `user` for the turn text (same string).
Schema gate (panel-schema contract): the panel file, both arm rows and
every required field/family are checked on load, before scoring anything.
A missing file, field, family or unexpected label prints SCHEMA-MISMATCH
and exits 3 (that run is VOID, not FAIL; never scored by hand).

  panelrun <agent.py> <config> <workdir> <panel.jsonl> <out.json>

One fresh daemon per dialog_id, turns in turn_index order; records
per-turn reply/ev/triples. Never scores, never prints turn text or gold.

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

CATEGORIES281B = ("teach_setup", "stored_called", "nostore_called",
                  "ambiguous_called", "control_plain")


def slug(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(s))[:60] or "item"


def text_of(it):
    if "user_text" in it and "user" in it:
        if it["user_text"] != it["user"]:
            print(f"SCHEMA-MISMATCH: dialog {it.get('dialog_id', '?')} "
                  f"turn {it.get('turn_index', '?')}: user_text != user")
            raise SystemExit(3)
        return it["user_text"]
    if "user_text" in it:
        return it["user_text"]
    if "user" in it:
        return it["user"]
    return None


def load_panel(path):
    try:
        raw = open(path).read().splitlines()
    except FileNotFoundError:
        print(f"SCHEMA-MISMATCH: panel file not found: {path}")
        raise SystemExit(3)
    items = [json.loads(x) for x in raw if x.strip()]
    if not items:
        print("SCHEMA-MISMATCH: panel has 0 rows")
        raise SystemExit(3)
    seen_cats = set()
    for n, it in enumerate(items):
        for k in ("dialog_id", "turn_index", "category", "gold"):
            if k not in it:
                print(f"SCHEMA-MISMATCH: row {n} missing field {k!r}")
                raise SystemExit(3)
        t = text_of(it)
        if t is None:
            print(f"SCHEMA-MISMATCH: row {n} has neither user_text nor user")
            raise SystemExit(3)
        if not isinstance(t, str):
            print(f"SCHEMA-MISMATCH: row {n} text is not a string")
            raise SystemExit(3)
        if it["category"] not in CATEGORIES281B:
            print(f"SCHEMA-MISMATCH: row {n} unexpected category "
                  f"{it['category']!r} (want one of {CATEGORIES281B})")
            raise SystemExit(3)
        seen_cats.add(it["category"])
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
            rep, ev, _s = r.send(d, root, k, text_of(it))
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
