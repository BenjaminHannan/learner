#!/usr/bin/env python3
"""Exp 221b -- three-arm runner + ONE sealed scorer (dev cases and panel).

Items (JSONL): {id, family, setup[], question, expect, gold, clear, notes}.
Each item runs on a FRESH agent per arm (138i, 221, 221b), in-process, Mac
CPU, sleep threshold 100000. For every turn it records reply, ears stage,
router intent, notebook fact-hash change (write), and wall ms.

SCORER (sealed; applied identically to all three arms):
  gold parts   gold may be a string or list; a string is split on ";" and
               ALL parts are required.
  item type    ABSTAIN-type iff gold is empty, or expect (lower-case) holds
               any of: abstain, clarify, no_answer, no answer, refuse,
               unknown, dont_know, don't know, idk, none. Else ANSWER-type.
  abstain      the reply holds an ABSTAIN_MARKER, or the not-understood
               clarify ("didn't understand").
  other values the values of the arm's active taught triples at question
               time (L90.notebook_triples), minus any value whose text is
               inside a gold part, minus any value whose text appears in
               the question. Matched as whole words, case-insensitive.
  ANSWER-type: RIGHT iff every gold part is in the reply (whole words) and
               no other value is; WRONG iff not RIGHT, not abstain, and an
               other value is in the reply; else MISS (split into
               MISS-abstain / MISS-other).
  ABSTAIN-type: WRONG iff not abstain and any other value or gold part is
               in the reply; RIGHT iff abstain; else MISS-other.
  question write: the fact hash (facts + retracted + superseded) changed on
               the question turn.

Run: python -B scripts/claude_221b_run.py --items X.jsonl --out DIR
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138i_agent as L138I  # noqa: E402 (read-only)
import fable_loop221_agent as L221  # noqa: E402 (read-only)
import claude_loop221b_agent as L221B  # noqa: E402 (arm under test)
import fable_loop90_agent as L90  # noqa: E402 (read-only)

ABSTAIN_MARKERS = ("don't know", "do not know", "never taught", "no record",
                   "never told", "not sure", "haven't been told",
                   "have not been told", "i don't have", "i do not have")
NOT_UNDERSTOOD = "didn't understand"
ABSTAIN_EXPECT = ("abstain", "clarify", "no_answer", "no answer", "refuse",
                  "unknown", "dont_know", "don't know", "idk", "none")
ARMS = ("138i", "221", "221b")


def _n(s: str) -> str:
    return " ".join(str(s).lower().replace("’", "'").split()).rstrip(".")


def has_word(text: str, v: str) -> bool:
    v = _n(v)
    if not v:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])",
                     _n(text)) is not None


def gold_parts(g) -> list[str]:
    if g is None:
        return []
    if isinstance(g, (list, tuple)):
        out = []
        for x in g:
            out += gold_parts(x)
        return out
    return [p.strip() for p in str(g).split(";") if p.strip()]


def abstain_type(item: dict) -> bool:
    if not gold_parts(item.get("gold")):
        return True
    e = str(item.get("expect") or "").lower()
    return any(k in e for k in ABSTAIN_EXPECT)


def facts_hash(nb) -> str:
    blob = json.dumps({"facts": nb.facts,
                       "retracted": sorted(getattr(nb, "retracted", [])),
                       "superseded": sorted(getattr(nb, "superseded", []))},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def build(arm: str):
    d = tempfile.mkdtemp(prefix=f"r221b-{arm}-")
    if arm == "221b":
        cfg = copy.deepcopy(L221B.DEFAULT_CONFIG221B)
        cfg["state_dir"], cfg["sleep_threshold"] = d, 100000
        return L221B.build_agent221b(cfg)
    if arm == "221":
        cfg = copy.deepcopy(L221.DEFAULT_CONFIG221)
        cfg["state_dir"], cfg["sleep_threshold"] = d, 100000
        return L221.build_agent221(cfg)
    cfg = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
    cfg["state_dir"], cfg["sleep_threshold"] = d, 100000
    return L138I.build_agent138i(cfg)


def run_item(arm: str, item: dict) -> dict:
    loop = build(arm)
    turns = []
    for t in list(item.get("setup") or []):
        t = str(t)
        h0 = facts_hash(loop.nb)
        reply = " ".join(loop.turn(t))
        turns.append({"text": t, "reply": reply,
                      "wrote": facts_hash(loop.nb) != h0})
    stored = [list(x) for x in L90.notebook_triples(loop.nb)]
    q = str(item["question"])
    h0 = facts_hash(loop.nb)
    t0 = time.perf_counter()
    reply = " ".join(loop.turn(q))
    ms = (time.perf_counter() - t0) * 1000.0
    return {"setup": turns, "stored": stored, "reply": reply,
            "ms": round(ms, 2),
            "stage": str(getattr(loop.ears, "last_stage", "")),
            "routed": (loop.last_routed or {}).get("intent")
            if getattr(loop, "last_routed", None) else None,
            "q_wrote": facts_hash(loop.nb) != h0}


def grade(item: dict, run: dict) -> str:
    reply = run["reply"]
    low = _n(reply)
    abst = any(m in low for m in ABSTAIN_MARKERS) or NOT_UNDERSTOOD in low
    golds = gold_parts(item.get("gold"))
    q = str(item["question"])
    others = []
    for _s, _r, v in run["stored"]:
        if any(_n(v) in _n(g) for g in golds) or has_word(q, v):
            continue
        if has_word(reply, v):
            others.append(v)
    if abstain_type(item):
        if not abst and (others or any(has_word(reply, g) for g in golds)):
            return "WRONG"
        return "RIGHT" if abst else "MISS-other"
    if golds and all(has_word(reply, g) for g in golds) and not others:
        return "RIGHT"
    if not abst and others:
        return "WRONG"
    return "MISS-abstain" if abst else "MISS-other"


def load(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8")
            .splitlines() if x.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    items = load(Path(args.items))
    rows = []
    for it in items:
        row = {"id": it.get("id"), "family": it.get("family"),
               "question": it["question"], "expect": it.get("expect"),
               "gold": it.get("gold"), "clear": it.get("clear"),
               "abstain_type": abstain_type(it)}
        for arm in ARMS:
            r = run_item(arm, it)
            g = grade(it, r)
            row[arm] = {"reply": r["reply"], "grade": g, "stage": r["stage"],
                        "routed": r["routed"], "q_wrote": r["q_wrote"],
                        "setup_wrote": [x["wrote"] for x in r["setup"]],
                        "ms": r["ms"], "stored": r["stored"]}
        rows.append(row)
        print(f"{row['id']} [{row['family']}] {it['question']!r}", flush=True)
        for arm in ARMS:
            print(f"   {arm:5s} {row[arm]['grade']:12s} "
                  f"{row[arm]['reply']!r}", flush=True)
    summ: dict = {"items": len(rows)}
    for arm in ARMS:
        gs = [r[arm]["grade"] for r in rows]
        summ[arm] = {
            "RIGHT": gs.count("RIGHT"), "WRONG": gs.count("WRONG"),
            "MISS-abstain": gs.count("MISS-abstain"),
            "MISS-other": gs.count("MISS-other"),
            "answer_items_right": sum(1 for r in rows if not r["abstain_type"]
                                      and r[arm]["grade"] == "RIGHT"),
            "abstain_items_right": sum(1 for r in rows if r["abstain_type"]
                                       and r[arm]["grade"] == "RIGHT"),
            "question_writes": sum(r[arm]["q_wrote"] for r in rows),
            "fallback_fired": sum(r[arm]["stage"] == L221B.STAGE221B
                                  for r in rows),
        }
    summ["answer_items"] = sum(not r["abstain_type"] for r in rows)
    summ["abstain_items"] = sum(r["abstain_type"] for r in rows)
    summ["right221_not_221b"] = [r["id"] for r in rows
                                 if r["221"]["grade"] == "RIGHT"
                                 and r["221b"]["grade"] != "RIGHT"]
    summ["right221b_not_221"] = [r["id"] for r in rows
                                 if r["221b"]["grade"] == "RIGHT"
                                 and r["221"]["grade"] != "RIGHT"]
    d = [r["221b"]["ms"] - r["221"]["ms"] for r in rows]
    summ["median_ms_221b_minus_221"] = round(statistics.median(d), 2) \
        if d else None
    by_fam: dict = {}
    for r in rows:
        f = by_fam.setdefault(str(r["family"]), {a: {} for a in ARMS})
        for arm in ARMS:
            g = r[arm]["grade"]
            f[arm][g] = f[arm].get(g, 0) + 1
    summ["by_family"] = by_fam
    (out / "rows.jsonl").write_text("\n".join(json.dumps(
        r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summ, indent=1,
                                                 ensure_ascii=False),
                                      encoding="utf-8")
    print(json.dumps({k: v for k, v in summ.items() if k != "by_family"},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
