#!/usr/bin/env python3
"""Exp 282 -- DRIVER-ONLY FIX after the seal (sealed files unchanged).

Bug: the sealed loader (scripts/claude_small282_run.py load_panel_dialogs,
grouped-dialog branch) extracts per-turn text from keys
text/turn/user/question, but the writer's schema uses `user_text`
(keys: category, dialog_id, gold, turn_index, user_text). The sealed M1 run
therefore fed 60/60 empty turns to both arms (void run; its files
run/panel-260.json, run/panel-282.json, run/panel-score282.json are kept
untouched as evidence, and the panel text was never read item by item).

Fix (one key added; sealed files byte-identical, seal still verifies):
  turns = [ln.get("user_text", ln.get("text", ...))) ...]
applied here by assigning the corrected loader onto the sealed module
object at runtime, then running the sealed run/score procedures.

Usage (from the repo root, uv prefix):
  python -B scripts/claude_small282_panelrun2.py <panel> <run_dir>
Runs the panel once per arm with the fixed loader (fresh work dirs,
new outputs panel-260b.json / panel-282b.json / probes files /
panel-score282b.json) and scores with the sealed scorer. Does NOT touch
st234 (valid from the sealed run) or any sealed file.
"""

import json
import sys

sys.path.insert(0, "scripts")
import claude_openers260_run as R260  # noqa: E402 (read-only driver)
import claude_small282_run as R282  # noqa: E402 (sealed; patched at runtime)
import claude_small282_score as S282  # noqa: E402 (sealed scorer)


def load_fixed(path):
    """Corrected loader: identical to the sealed one except the per-turn
    text key chain starts with the writer's `user_text`."""
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
    if items and any("turn_index" in it or "turn_idx" in it or "dialog" in it
                     or "dialog_id" in it
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
            # THE FIX: read `user_text` first (writer's schema key).
            turns = [ln.get("user_text", ln.get("text", ln.get("turn",
                             ln.get("user", ln.get("question", "")))))
                     for ln in lines]
            fam = lines[-1].get("category", lines[-1].get("family", ""))
            gold = lines[-1].get("gold")
            dialogs.append({"id": gid, "turns": turns, "family": fam,
                            "gold": gold})
        return dialogs
    return R282.load_panel_dialogs(path)


def main(argv):
    panelp, rundir = argv[1:3]
    R282.load_panel_dialogs = load_fixed  # runtime patch only; file untouched
    dialogs = R282.load_panel_dialogs(panelp)
    n_turns = sum(len(d["turns"]) for d in dialogs)
    n_empty = sum(1 for d in dialogs for t in d["turns"] if not t)
    print(f"loaded {len(dialogs)} dialogs, {n_turns} turns, "
          f"empty {n_empty}")
    assert n_empty == 0, "loader still yields empty turns"
    arms = [("scripts/claude_loop260_agent.py",
             "artifacts/claude-openers260-20260922/loop260-config.json",
             f"{rundir}/work/p282b", f"{rundir}/panel-260b.json",
             f"{rundir}/probes-260b.json"),
            ("scripts/claude_loop282_agent.py",
             "artifacts/claude-small282-20260923/loop282-config.json",
             f"{rundir}/work/n282b", f"{rundir}/panel-282b.json",
             f"{rundir}/probes-282b.json")]
    for agent, config, work, dst, probedst in arms:
        r = R260.Runner(agent, config, work)
        out = R282.run_panel_dialogs(r, dialogs)
        json.dump(out, open(dst, "w"), indent=1)
        json.dump(R282.run_probes(r), open(probedst, "w"), indent=1)
        print(f"done {len(out)} dialogs -> {dst}")
    rc = S282.panel_main([panelp, f"{rundir}/panel-260b.json",
                          f"{rundir}/panel-282b.json",
                          f"{rundir}/probes-260b.json",
                          f"{rundir}/probes-282b.json",
                          f"{rundir}/panel-score282b.json"])
    print("score rc:", rc)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
