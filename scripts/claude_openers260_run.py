#!/usr/bin/env python3
"""Exp 260 driver: run dialogs through an agent daemon (one fresh dir each).

  dev   <agent.py> <config> <workdir> <devcases.json> <out.json>
  panel <agent.py> <config> <workdir> <panel.jsonl>   <out.jsonl>

dev: each case's turns in order ("__RESTART__" rebuilds the daemon on the
same dir); records reply, event delta, triples and seconds per turn.
panel: one fresh notebook per item; setup turns, the turn, the followup
(if any) in order, stored triples read after each; the row fields follow
the openpanel260 base-row schema (plain_reply "" and base_right/base_junk
None: this driver never runs plain_turn and never scores).
"""
import gc
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, "scripts")
import fable_marks123_all as M  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)


def nev(d):
    nb = d.loop.nb
    for o in (nb, getattr(nb, "nb", None)):
        if o is not None and hasattr(o, "events"):
            return len(o.events)
    return -1


def trip(d):
    return [list(x) for x in L90.notebook_triples(d.loop.nb)]


class Runner:
    def __init__(self, agent, config, work):
        _mod, self.dcls, _, _ = M.load_agent(agent)
        self.base = M.load_base_cfg(config)
        self.work = Path(work)

    def fresh(self, name):
        root = self.work / name
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        return root, M.make_daemon(self.dcls, self.base, root)

    @staticmethod
    def send(d, root, k, text):
        f = root / "inbox" / f"m{k:03d}.txt"
        f.write_text(text, encoding="utf-8")
        b = nev(d)
        t0 = time.perf_counter()
        try:
            d.process_file(f)
            rep = (root / "outbox" / f"m{k:03d}.txt").read_text(
                encoding="utf-8").strip()
        except Exception as e:  # noqa: BLE001
            rep = f"CRASH {type(e).__name__}: {e}"
        return rep, nev(d) - b, time.perf_counter() - t0


def run_dev(r, cases):
    out = []
    for c in cases:
        root, d = r.fresh(c["id"])
        rows, k = [], 0
        for t in c["turns"]:
            if t == "__RESTART__":
                del d
                gc.collect()
                d = M.make_daemon(r.dcls, r.base, root)
                rows.append({"restart": True, "triples": trip(d)})
                continue
            rep, ev, sec = r.send(d, root, k, t)
            rows.append({"turn": t, "reply": rep, "ev": ev,
                         "triples": trip(d), "sec": round(sec, 5)})
            k += 1
        out.append({"id": c["id"], "rows": rows, "stored": trip(d)})
        del d
        gc.collect()
        shutil.rmtree(root, ignore_errors=True)
    return out


def run_panel(r, items):
    out = []
    for it in items:
        root, d = r.fresh(it["id"])
        k = 0
        setup_replies = []
        for t in it["setup"]:
            rep, _ev, _s = r.send(d, root, k, t)
            setup_replies.append(rep)
            k += 1
        s_setup = trip(d)
        turn_reply, _ev, _s = r.send(d, root, k, it["turn"])
        k += 1
        s_turn = trip(d)
        f_reply, s_f = "", s_turn
        if it["followup"]:
            f_reply, _ev, _s = r.send(d, root, k, it["followup"])
            s_f = trip(d)
        out.append({"id": it["id"], "setup_replies": setup_replies,
                    "stored_after_setup": s_setup, "turn_reply": turn_reply,
                    "stored_after_turn": s_turn, "followup_reply": f_reply,
                    "stored_after_followup": s_f, "plain_reply": "",
                    "base_right": None, "base_junk": None})
        del d
        gc.collect()
        shutil.rmtree(root, ignore_errors=True)
    return out


def main(argv):
    mode, agent, config, work, src, dst = argv[1:7]
    r = Runner(agent, config, work)
    if mode == "dev":
        rows = run_dev(r, json.loads(Path(src).read_text(encoding="utf-8")))
        Path(dst).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    elif mode == "panel":
        items = [json.loads(x) for x in
                 Path(src).read_text(encoding="utf-8").splitlines()
                 if x.strip()]
        rows = run_panel(r, items)
        Path(dst).write_text("".join(json.dumps(x) + "\n" for x in rows),
                             encoding="utf-8")
    else:
        raise SystemExit("mode must be dev or panel")
    print("done", len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
