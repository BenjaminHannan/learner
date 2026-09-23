#!/usr/bin/env python3
"""Exp 280m joinpanel runner: run dialogs through an agent daemon.

  dev <agent.py> <config> <workdir> <devcases.json> <out.json> <probes.json>
    Same as scripts/claude_openers260_run.py dev (fresh daemon per case),
    plus the arm's own replies to the canonical probes
    ("Hello.", "Thanks!", "Bye.", "how are you") on fresh notebooks.
  panel <agent.py> <config> <workdir> <panel.jsonl|json> <out.json> <probes.json>
    STRICT loader for the joinpanel280m schema: one row per turn
    {dialog_id, turn_index, user_text, category, gold} with category in
    {ability, called, teach, smalltalk, mixed, control}. The text key
    `user` is also accepted. Any row missing a required key, any
    unexpected category, or any empty turn text stops the run with an
    error (no partial run is scored). Every turn of each dialog runs in
    order on one fresh notebook; per-turn replies, write deltas and
    stores are recorded. Never scores.
  st234 <agent.py> <config> <workdir> <panel.jsonl> <out.json> <probes.json>
    smalltalkpanel234 items {id, family, setup, turn, expect, gold}: setup
    turns then the turn on a fresh notebook per item. Never scores.
Daemon handling (Runner/send/trip) is reused read-only from
scripts/claude_openers260_run.py so all arms run identically.
"""

import gc
import json
import re
import shutil
import sys

sys.path.insert(0, "scripts")
import claude_openers260_run as R260  # noqa: E402 (read-only driver)

PROBES280M = ["Hello.", "Thanks!", "Bye.", "how are you"]

PANEL_CATS280M = ("ability", "called", "teach", "smalltalk", "mixed",
                  "control")


def slug(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(s))[:60] or "item"


def run_probes(r):
    out = {}
    for p in PROBES280M:
        root, d = r.fresh("probe_" + slug(p))
        rep, ev, _s = r.send(d, root, 0, p)
        out[p] = {"reply": rep, "writes": ev, "stored": R260.trip(d)}
        del d
        gc.collect()
        shutil.rmtree(root, ignore_errors=True)
    return out


def run_panel_dialogs(r, dialogs):
    """dialogs: list of {id, turns[]}. Every turn runs in order."""
    out = []
    for dg in dialogs:
        root, d = r.fresh(slug(dg["id"]))
        rows, k = [], 0
        for t in dg["turns"]:
            rep, ev, _s = r.send(d, root, k, t)
            rows.append({"turn": t, "reply": rep, "ev": ev,
                         "triples": R260.trip(d)})
            k += 1
        out.append({"id": dg["id"], "cats": list(dg.get("cats", [])),
                    "golds": list(dg.get("golds", [])),
                    "rows": rows, "stored": R260.trip(d)})
        del d
        gc.collect()
        shutil.rmtree(root, ignore_errors=True)
    return out


def _panel_items(path):
    txt = open(path).read().strip()
    if not txt:
        return []
    if path.endswith(".jsonl"):
        return [json.loads(x) for x in txt.split("\n") if x.strip()]
    doc = json.loads(txt)
    if isinstance(doc, list):
        return doc
    for k in ("items", "dialogs", "cases", "panel"):
        if k in doc and isinstance(doc[k], list):
            return doc[k]
    print("SCHEMA-MISMATCH: no item list found")
    raise SystemExit(3)


def load_panel_dialogs(path):
    """Strict joinpanel280m loader -> [{id, turns[], cats[], golds[]}]."""
    items = _panel_items(path)
    if not items:
        print("SCHEMA-MISMATCH: empty panel")
        raise SystemExit(3)
    groups = {}
    for n, it in enumerate(items):
        if not isinstance(it, dict):
            print(f"SCHEMA-MISMATCH: row {n} is not an object")
            raise SystemExit(3)
        for key in ("dialog_id", "turn_index", "category", "gold"):
            if key not in it:
                print(f"SCHEMA-MISMATCH: row {n} missing key {key!r} "
                      f"(has {sorted(it)})")
                raise SystemExit(3)
        if "user_text" in it:
            text = it["user_text"]
        elif "user" in it:
            text = it["user"]
        else:
            print(f"SCHEMA-MISMATCH: row {n} missing text key "
                  "('user_text' or 'user')")
            raise SystemExit(3)
        cat = it["category"]
        if cat not in PANEL_CATS280M:
            print(f"SCHEMA-MISMATCH: row {n} unexpected category {cat!r}")
            raise SystemExit(3)
        if text is None or str(text).strip() == "":
            print(f"EMPTY-TURN: row {n} (dialog "
                  f"{it['dialog_id']!r} turn_index {it['turn_index']!r}) "
                  "has empty turn text; refusing to run")
            raise SystemExit(4)
        gid = str(it["dialog_id"])
        groups.setdefault(gid, []).append(
            {"idx": it["turn_index"], "text": str(text),
             "cat": cat, "gold": it["gold"], "n": n})
    dialogs = []
    for gid, lines in groups.items():
        try:
            lines = sorted(lines, key=lambda ln: (ln["idx"], ln["n"]))
        except TypeError:
            print(f"SCHEMA-MISMATCH: dialog {gid!r} turn_index not sortable")
            raise SystemExit(3)
        dialogs.append({"id": gid,
                        "turns": [ln["text"] for ln in lines],
                        "cats": [ln["cat"] for ln in lines],
                        "golds": [ln["gold"] for ln in lines]})
    return dialogs


def load_st234(path):
    txt = open(path).read().strip()
    items = [json.loads(x) for x in txt.split("\n") if x.strip()]
    return items


def run_st234(r, items):
    out = []
    for it in items:
        root, d = r.fresh(slug(it.get("id", "?")))
        setup_replies, k = [], 0
        for t in it.get("setup") or []:
            rep, _ev, _s = r.send(d, root, k, t)
            setup_replies.append(rep)
            k += 1
        s_setup = R260.trip(d)
        turn_reply, ev_t, _s = r.send(d, root, k, it.get("turn", ""))
        s_turn = R260.trip(d)
        out.append({"id": it.get("id"), "family": it.get("family"),
                    "expect": it.get("expect"), "gold": it.get("gold"),
                    "setup": list(it.get("setup") or []),
                    "turn": it.get("turn", ""),
                    "setup_replies": setup_replies,
                    "stored_after_setup": s_setup, "turn_reply": turn_reply,
                    "stored_after_turn": s_turn, "writes_turn": ev_t})
        del d
        gc.collect()
        shutil.rmtree(root, ignore_errors=True)
    return out


def main(argv):
    mode = argv[1]
    if mode == "dev":
        _m, agent, config, work, src, dst, probedst = argv[1:8]
        r = R260.Runner(agent, config, work)
        cases = json.load(open(src))
        out = R260.run_dev(r, cases)
        json.dump(out, open(dst, "w"), indent=1)
        json.dump(run_probes(r), open(probedst, "w"), indent=1)
        print(f"done {len(out)}")
        return 0
    if mode == "panel":
        _m, agent, config, work, src, dst, probedst = argv[1:8]
        r = R260.Runner(agent, config, work)
        dialogs = load_panel_dialogs(src)
        n_turns = sum(len(d["turns"]) for d in dialogs)
        n_empty = sum(1 for d in dialogs for t in d["turns"]
                      if str(t).strip() == "")
        print(f"loaded {len(dialogs)} dialogs, {n_turns} turns, "
              f"empty {n_empty}")
        assert n_empty == 0, "loader yielded empty turns"
        out = run_panel_dialogs(r, dialogs)
        json.dump(out, open(dst, "w"), indent=1)
        json.dump(run_probes(r), open(probedst, "w"), indent=1)
        print(f"done {len(out)} dialogs -> {dst}")
        return 0
    if mode == "st234":
        _m, agent, config, work, src, dst, probedst = argv[1:8]
        r = R260.Runner(agent, config, work)
        items = load_st234(src)
        out = run_st234(r, items)
        json.dump(out, open(dst, "w"), indent=1)
        json.dump(run_probes(r), open(probedst, "w"), indent=1)
        print(f"done {len(out)} items")
        return 0
    raise SystemExit("mode must be dev|panel|st234")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
