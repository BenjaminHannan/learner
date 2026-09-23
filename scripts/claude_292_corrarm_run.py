#!/usr/bin/env python3
"""Exp 292 corr M1 runner (post-seal driver-only fix, disclosed).

Mirrors artifacts/claude-corrpanel291-20260923/run_base.py one-for-one
(same config handling, sleep_threshold, fresh temp state_dir per item,
same 10-field row schema with self-scored base_right/base_wrong_value/
base_false_claim via the same score_item logic); only the arm build
differs (291 or 292). Rows go OUTSIDE the sealed panel dir; only counts
JSON (ids, families, counts) is published. Never prints item text or
replies (ids and boolean flags only). CPU only, one arm per process.

usage: claude_292_corrarm_run.py --arm 291|292 --out <rows.jsonl>

Why this file exists: the sealed corr scorer gates the row schema
(exact BASE_FIELDS keys in order). scripts/claude_corr252_run.py emits
7-field rows, so both corr M1 runs scored SCHEMA-MISMATCH exit 3
(VOID, no verdict). Sealed files cannot be edited after the seal, so
this new driver replaces those two VOID runs; the VOID rows are kept
untouched in the run dir and reported.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop90_agent as L90  # noqa: E402 (read-only triples)

PANEL = ROOT / "artifacts/claude-corrpanel291-20260923/panel.jsonl"

ARMS = {
    "291": ("claude_loop291_agent", "build_agent291",
            "artifacts/claude-join291-20260923/loop291-config.json"),
    "292": ("claude_loop292_agent", "build_agent292",
            "artifacts/claude-merge292-20260923/loop292-config.json"),
}


def active(nb):
    return sorted(list(map(str, x)) for x in L90.notebook_triples(nb))


def T(ts):
    return {tuple(str(p).lower() for p in t) for t in (ts or [])}


def ww(v, t):
    return re.search(r'(?<!\w)' + re.escape(v) + r'(?!\w)', t or '',
                     re.I) is not None


def score_item(p, stored_setup, stored_turn, stored_follow, turn_reply,
               follow_reply):
    """Same logic as the panel run_base.py score_item."""
    sas, sat, saf = T(stored_setup), T(stored_turn), T(stored_follow)
    es, eg = T(p["expect_store"]), T(p["expect_gone"])
    junk = not sat <= (sas | es)
    store_ok = (es <= sat) and (not (eg & sat)) and (not junk)
    fr = follow_reply or ""
    if p["gold_followup"]:
        parts = [x.strip() for x in p["gold_followup"].split(";")]
        fok = all(x.lower() in fr.lower() for x in parts
                  ) and not re.match(r"\s*i (don't|do not) know", fr, re.I)
    else:
        gone_vals = [g[2] for g in p["expect_gone"]]
        fok = not any(ww(v, fr) for v in gone_vals)
    gone_vals = [g[2] for g in p["expect_gone"]]
    wrong = any(ww(v, fr) for v in gone_vals)
    fw = (saf != sat)
    still = sas & sat
    tr = turn_reply or ""
    claim_word = ("don't have" in tr.lower() or "do not have" in tr.lower()
                  or "removed" in tr.lower() or "updated" in tr.lower()
                  or "deleted" in tr.lower() or "changed" in tr.lower())
    false_claim = False
    if claim_word:
        for t in still:
            v = list(t)[2]
            if ww(v, tr):
                false_claim = True
                break
    right = bool(store_ok and fok and (not fw) and (not false_claim))
    return right, wrong, false_claim, junk


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 292 corr arm runner")
    ap.add_argument("--arm", required=True, choices=("291", "292"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    mod_name, build_name, cfg_rel = ARMS[args.arm]
    import importlib
    mod = importlib.import_module(mod_name)
    build = getattr(mod, build_name)
    base = json.loads((ROOT / cfg_rel).read_text(encoding="utf-8"))
    panel = [json.loads(l) for l in
             PANEL.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = []
    for p in panel:
        cfg = copy.deepcopy(base)
        sd = Path(tempfile.mkdtemp(prefix="c292corr-"))
        cfg["state_dir"] = str(sd)
        cfg["sleep_threshold"] = 100000
        loop = build(cfg)
        setup_replies = [" ".join(loop.turn(t)) for t in p["setup"]]
        stored_setup = active(loop.nb)
        turn_reply = " ".join(loop.turn(p["turn"]))
        stored_turn = active(loop.nb)
        follow_reply = " ".join(loop.turn(p["followup"]))
        stored_follow = active(loop.nb)
        right, wrong, fclaim, junk = score_item(
            p, stored_setup, stored_turn, stored_follow, turn_reply,
            follow_reply)
        rows.append({"id": p["id"], "setup_replies": setup_replies,
                     "stored_after_setup": stored_setup,
                     "turn_reply": turn_reply,
                     "stored_after_turn": stored_turn,
                     "followup_reply": follow_reply,
                     "stored_after_followup": stored_follow,
                     "base_right": right, "base_wrong_value": wrong,
                     "base_false_claim": fclaim})
        print(f"[corr292/{args.arm}] did {p['id']} right={right} "
              f"wrong={wrong} fclaim={fclaim} junk={junk}", flush=True)
        shutil.rmtree(sd, ignore_errors=True)
        del loop
    Path(args.out).write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8")
    print(f"wrote {args.out} {len(rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
