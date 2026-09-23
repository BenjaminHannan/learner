#!/usr/bin/env python3
"""Exp 281 panel/dev runner: run dialogs through an agent daemon.

  panel <agent.py> <config> <workdir> <panel.json|jsonl> <out.json>
    Flexible loader (the blind panel's exact schema is set by its writer):
    items shaped {id, setup[], turn, followup} or {id, turns[]} (or
    {id, family, ...}). One fresh notebook per item; records replies,
    per-turn write deltas and stores. Never scores.
  dev <agent.py> <config> <workdir> <devcases.json> <out.json>
    Same as scripts/claude_openers260_run.py dev (fresh daemon per case).
Daemon handling (Runner/send/trip) is reused read-only from
scripts/claude_openers260_run.py so both arms run identically.
"""

import gc
import json
import re
import shutil
import sys

sys.path.insert(0, "scripts")
import claude_called281_score as S  # noqa: E402 (loader, sealed with this)
import claude_openers260_run as R260  # noqa: E402 (read-only driver)


def slug(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(s))[:60] or "item"


def run_panel(r, items):
    out = []
    for it in items:
        setup, turn, foll, fam, iid = S.panel_turns(it)
        root, d = r.fresh(slug(iid))
        k = 0
        setup_replies = []
        for t in setup:
            rep, _ev, _s = r.send(d, root, k, t)
            setup_replies.append(rep)
            k += 1
        s_setup = R260.trip(d)
        turn_reply, ev_t, _s = r.send(d, root, k, turn)
        k += 1
        s_turn = R260.trip(d)
        f_reply, s_f, ev_f = "", s_turn, 0
        if foll:
            f_reply, ev_f, _s = r.send(d, root, k, foll)
            s_f = R260.trip(d)
        out.append({"id": iid, "family": fam, "setup": setup, "turn": turn,
                    "followup": foll, "setup_replies": setup_replies,
                    "stored_after_setup": s_setup, "turn_reply": turn_reply,
                    "stored_after_turn": s_turn, "writes_turn": ev_t,
                    "followup_reply": f_reply,
                    "stored_after_followup": s_f, "writes_followup": ev_f})
        del d
        gc.collect()
        shutil.rmtree(root, ignore_errors=True)
    return out


def main(argv):
    mode, agent, config, work, src, dst = argv[1:7]
    r = R260.Runner(agent, config, work)
    if mode == "panel":
        items = S.load_panel_items(src)
        out = run_panel(r, items)
    elif mode == "dev":
        cases = json.load(open(src))
        out = R260.run_dev(r, cases)
    else:
        raise SystemExit("mode must be panel|dev")
    json.dump(out, open(dst, "w"), indent=1)
    print(f"done {len(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
