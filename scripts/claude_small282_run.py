#!/usr/bin/env python3
"""Exp 282 panel/dev/st234 runner: run dialogs through an agent daemon.

  dev <agent.py> <config> <workdir> <devcases.json> <out.json> <probes.json>
    Same as scripts/claude_openers260_run.py dev (fresh daemon per case),
    plus the arm's own replies to the canonical probes
    ("Hello.", "Thanks!", "Bye.", "how are you") on fresh notebooks.
  panel <agent.py> <config> <workdir> <panel.jsonl|json> <out.json> <probes.json>
    Flexible loader (the blind panel's exact schema is set by its writer):
    per-turn lines {dialog/id, turn index, text, category, gold} grouped
    into dialogs, or items shaped {id, setup[], turn, followup}, or
    {id, turns[]}. Every turn of each dialog runs in order on one fresh
    notebook; per-turn replies, write deltas and stores are recorded.
    Never scores.
  st234 <agent.py> <config> <workdir> <panel.jsonl> <out.json> <probes.json>
    smalltalkpanel234 items {id, family, setup, turn, expect, gold}: setup
    turns then the turn on a fresh notebook per item. Never scores.
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

PROBES282 = ["Hello.", "Thanks!", "Bye.", "how are you"]


def slug(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(s))[:60] or "item"


def run_probes(r):
    out = {}
    for p in PROBES282:
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
        out.append({"id": dg["id"], "family": dg.get("family"),
                    "gold": dg.get("gold"), "rows": rows,
                    "stored": R260.trip(d)})
        del d
        gc.collect()
        shutil.rmtree(root, ignore_errors=True)
    return out


def _str_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    return list(v)


def load_panel_dialogs(path):
    """Flexible blind-panel loader -> [{id, turns[], family, gold}]."""
    txt = open(path).read().strip()
    if path.endswith(".jsonl"):
        items = [json.loads(x) for x in txt.split("\n") if x.strip()]
    else:
        doc = json.loads(txt)
        if isinstance(doc, list):
            items = doc
        else:
            items = None
            for k in ("items", "dialogs", "cases", "panel"):
                if k in doc and isinstance(doc[k], list):
                    items = doc[k]
                    break
            if items is None:
                raise SystemExit("panel loader: no item list found")
    # Per-turn lines grouped by dialog?
    if items and any("turn_index" in it or "turn_idx" in it or "dialog" in it
                     for it in items if isinstance(it, dict)):
        groups = {}

        def tkey(it):
            return it.get("turn_index", it.get("turn_idx",
                         it.get("idx", it.get("n", 0))))
        for it in items:
            gid = it.get("dialog", it.get("dialog_id",
                        it.get("id", it.get("item", "?"))))
            groups.setdefault(str(gid), []).append(it)
        dialogs = []
        for gid, lines in groups.items():
            lines = sorted(lines, key=tkey)
            turns = [ln.get("text", ln.get("turn", ln.get("user",
                             ln.get("question", "")))) for ln in lines]
            fam = lines[-1].get("category", lines[-1].get("family", ""))
            gold = lines[-1].get("gold")
            dialogs.append({"id": gid, "turns": turns, "family": fam,
                            "gold": gold})
        return dialogs
    # Whole items: {setup, turn, followup} or {turns}.
    dialogs = []
    for it in items:
        iid = str(it.get("id", "?"))
        fam = it.get("family", it.get("category", it.get("cat", "")))
        gold = it.get("gold")
        if "turns" in it and isinstance(it["turns"], list):
            dialogs.append({"id": iid, "turns": list(it["turns"]),
                            "family": fam, "gold": gold})
            continue
        setup = _str_list(it.get("setup", it.get("teach",
                        it.get("teaches", it.get("context", [])))))
        turn = it.get("turn", it.get("question", it.get("text", "")))
        foll = it.get("followup", it.get("follow_up"))
        turns = setup + [turn]
        if foll:
            turns = turns + _str_list(foll)
        dialogs.append({"id": iid, "turns": turns, "family": fam,
                        "gold": gold})
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
        out = run_panel_dialogs(r, dialogs)
        json.dump(out, open(dst, "w"), indent=1)
        json.dump(run_probes(r), open(probedst, "w"), indent=1)
        print(f"done {len(out)} dialogs")
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
