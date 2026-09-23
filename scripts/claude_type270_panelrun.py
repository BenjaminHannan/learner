#!/usr/bin/env python3
"""Exp 270 POST-SEAL panel runner (new file, disclosed D3).

Runs the blind typepanel270 (single-turn items, no setup/followup) on the
two SEALED arms, each ONCE: arm A (scripts/claude_type270_agent.py +
sealed loop270-config) and arm A263 (scripts/claude_loop263_agent.py +
263 config). One fresh daemon dir per item (ear-line convention); boot
triples captured before the turn so added triples are exact.

Usage: python -B scripts/claude_type270_panelrun.py <panel.jsonl>
         <workdir> <rowsA.jsonl> <rows263.jsonl>
Rows: {id, turn_reply, boot_triples, stored_after_turn, sec, rewrites,
        norm_ms}
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


def trip(d):
    return [list(x) for x in L90.notebook_triples(d.loop.nb)]


def run_arm(agent, config, items, work):
    _mod, dcls, _, _ = M.load_agent(agent)
    base = M.load_base_cfg(config)
    work = Path(work)
    rows = []
    for it in items:
        root = work / it["id"]
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        d = M.make_daemon(dcls, base, root)
        boot = trip(d)
        f = root / "inbox" / "m000.txt"
        f.write_text(it["turn"], encoding="utf-8")
        t0 = time.perf_counter()
        try:
            d.process_file(f)
            rep = (root / "outbox" / "m000.txt").read_text(
                encoding="utf-8").strip()
        except Exception as e:  # noqa: BLE001
            rep = f"CRASH {type(e).__name__}: {e}"
        sec = time.perf_counter() - t0
        after = trip(d)
        log = list(getattr(d.loop, "type270_log", []) or [])
        rows.append({"id": it["id"], "turn_reply": rep,
                     "boot_triples": boot, "stored_after_turn": after,
                     "sec": round(sec, 5),
                     "rewrites": log,
                     "norm_ms": (log[-1].get("norm_ms")
                                 if log else 0.0)})
        del d
        gc.collect()
        shutil.rmtree(root, ignore_errors=True)
    return rows


def main(argv):
    panel_p, work, out_a, out_b = argv[1:5]
    items = [json.loads(x) for x in Path(panel_p).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    rows = run_arm("scripts/claude_type270_agent.py",
                   "artifacts/claude-type270-20260923/loop270-config.json",
                   items, Path(work) / "A")
    Path(out_a).write_text("".join(json.dumps(r) + "\n" for r in rows),
                           encoding="utf-8")
    print("done A", len(rows))
    rows = run_arm("scripts/claude_loop263_agent.py",
                   "artifacts/claude-comma263-20260923/loop263-config.json",
                   items, Path(work) / "B")
    Path(out_b).write_text("".join(json.dumps(r) + "\n" for r in rows),
                           encoding="utf-8")
    print("done A263", len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
