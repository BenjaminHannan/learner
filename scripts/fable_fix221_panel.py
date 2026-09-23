#!/usr/bin/env python3
"""Exp 221 -- panel / dev runner for P1, P2, P4, P5, P6 (harness only).

Runs a JSONL of items through BOTH arms, loop138i (sealed base) and loop221
(this experiment), a FRESH agent per item, in-process, Mac CPU. For every
turn it records the reply, ears stage, whether the self router fired
(loop.last_routed), the notebook fact-set hash before/after, and wall ms.

Scoring (per scored question turn; the panel's own gold + family decide):
  family "untaught"     correct iff the reply abstains (ABSTAIN_MARKERS)
                        and asserts no gold/taught value.
  family "no_relation"  correct iff the reply gives no answer: no taught
                        value in it and no write on that turn.
  family "self"         correct iff the 221 reply == the 138i reply.
  any other family      correct iff the reply contains a gold value
                        (case/space-insensitive); for an inverse family
                        (family name contains "inverse"/"reverse"/
                        "backward") an answer must also carry the label
                        "(worked out backwards)".
  WRONG VALUE (any family): the reply is not correct, is not an abstain,
  is not a not-understood clarify, and contains a taught value that is
  not gold -- i.e. it asserts a different fact.

FIELD MAP: items are read by load_items() below. It accepts
  {"turns": [str | {"text": ..}], ...} (scored turn = last, or every turn
  dict carrying gold/family) or {"teaches"/"teach"/"setup"/"context": [...],
  "question": ..}; gold from gold/gold_values/expected/answer/answers;
  family from family/kind/type/category.
If the sealed panel uses other field names, only this map may be adapted
after opening it, and every such change is listed as a deviation.

Run: python -B scripts/fable_fix221_panel.py --items X.jsonl --out DIR
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

import fable_loop138i_agent as L138I  # noqa: E402 (base arm, read-only)
import fable_loop221_agent as L221  # noqa: E402 (arm under test)
import fable_fix221_tableask as T221  # noqa: E402

ABSTAIN_MARKERS = ("don't know", "do not know", "never taught", "no record",
                   "never told", "not sure", "haven't been told",
                   "have not been told", "i don't have", "i do not have")
NOT_UNDERSTOOD = "didn't understand"


# ------------------------------------------------------------- field map
def _as_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return list(v)
    return [v]


def _gold(d: dict) -> list[str]:
    for k in ("gold", "gold_values", "expected", "answer", "answers",
              "want"):
        if k in d and d[k] is not None:
            return [str(x) for x in _as_list(d[k]) if str(x).strip()]
    return []


def _family(d: dict, default: str = "") -> str:
    for k in ("family", "kind", "type", "category"):
        if d.get(k):
            return str(d[k])
    return default


def load_items(path: Path) -> list[dict]:
    """-> [{"id", "turns": [text], "scored": [(turn_index, family, gold)]}]"""
    items = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        it = json.loads(line)
        iid = str(it.get("id", f"item{n:03d}"))
        fam = _family(it)
        turns: list[str] = []
        scored = []
        if isinstance(it.get("turns"), list):
            for j, t in enumerate(it["turns"]):
                if isinstance(t, dict):
                    turns.append(str(t.get("text", t.get("turn", ""))))
                    if _gold(t) or _family(t):
                        scored.append((j, _family(t, fam), _gold(t)))
                else:
                    turns.append(str(t))
            if not scored and turns:
                scored.append((len(turns) - 1, fam, _gold(it)))
        else:
            pre = None
            for k in ("teaches", "teach", "setup", "context", "taught"):
                if k in it:
                    pre = it[k]
                    break
            for t in _as_list(pre):
                turns.append(str(t.get("text", t.get("sentence_en", "")))
                             if isinstance(t, dict) else str(t))
            q = it.get("question", it.get("q", it.get("ask")))
            turns.append(str(q))
            scored.append((len(turns) - 1, fam, _gold(it)))
        items.append({"id": iid, "turns": turns, "scored": scored,
                      "raw_family": fam})
    return items


# --------------------------------------------------------------- running
def facts_hash(nb) -> str:
    blob = json.dumps({"facts": nb.facts,
                       "retracted": sorted(getattr(nb, "retracted", [])),
                       "superseded": sorted(getattr(nb, "superseded", []))},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def build(arm: str):
    d = tempfile.mkdtemp(prefix=f"p221-{arm}-")
    if arm == "221":
        cfg = copy.deepcopy(L221.DEFAULT_CONFIG221)
        cfg["state_dir"] = d
        cfg["sleep_threshold"] = 100000
        return L221.build_agent221(cfg)
    cfg = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    return L138I.build_agent138i(cfg)


def run_item(arm: str, item: dict) -> list[dict]:
    loop = build(arm)
    out = []
    for t in item["turns"]:
        h0 = facts_hash(loop.nb)
        t0 = time.perf_counter()
        reply = " ".join(loop.turn(t))
        ms = (time.perf_counter() - t0) * 1000.0
        h1 = facts_hash(loop.nb)
        out.append({"text": t, "reply": reply, "ms": round(ms, 2),
                    "stage": str(getattr(loop.ears, "last_stage", "")),
                    "routed": (loop.last_routed or {}).get("intent")
                    if getattr(loop, "last_routed", None) else None,
                    "wrote": h0 != h1})
    return out


def _n(s: str) -> str:
    return " ".join(str(s).lower().replace("’", "'").split())


def taught_values(turns: list[str]) -> list[str]:
    """Values the item's statement turns name (right-hand side of 'is')."""
    vals = []
    for t in turns:
        if t.strip().endswith("?"):
            continue
        m = re.search(r"\b(?:is|are|at|for|by|in)\s+(.+?)[.!]?$", t.strip())
        if m:
            vals.append(m.group(1).strip())
    return [v for v in vals if v]


def score(item: dict, j: int, fam: str, gold: list[str], r221: dict,
          r138: dict) -> dict:
    reply = r221["reply"]
    low = _n(reply)
    abst = any(m in low for m in ABSTAIN_MARKERS)
    nu = NOT_UNDERSTOOD in low
    has_gold = any(_n(g) in low for g in gold if g)
    tv = [v for v in taught_values(item["turns"][:j])
          if not any(_n(v) == _n(g) for g in gold)]
    other = [v for v in tv if _n(v) in low]
    fl = fam.lower()
    inverse_fam = any(w in fl for w in ("inverse", "reverse", "backward"))
    if fl == "self":
        ok = reply == r138["reply"]
    elif fl in ("untaught", "abstain"):
        ok = abst and not has_gold and not other
    elif fl in ("no_relation", "norelation", "clarify"):
        ok = not other and not has_gold and not r221["wrote"]
    else:
        ok = has_gold and (not inverse_fam or T221.LABEL221 in reply)
    wrong = (not ok) and (not abst) and (not nu) and bool(other) \
        and not has_gold
    return {"id": item["id"], "turn_index": j, "family": fam,
            "gold": gold, "question": item["turns"][j], "reply221": reply,
            "reply138i": r138["reply"], "correct221": ok,
            "wrong_value221": wrong, "abstain221": abst,
            "label221": T221.LABEL221 in reply,
            "stage221": r221["stage"], "routed221": r221["routed"],
            "table_claimed": r221["stage"].startswith(T221.STAGE221),
            "wrote221": r221["wrote"], "ms221": r221["ms"],
            "ms138i": r138["ms"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    items = load_items(Path(args.items))
    rows, turns_log = [], []
    q_wrote = []
    diffs = []
    for it in items:
        a = run_item("221", it)
        b = run_item("138i", it)
        for k, (x, y) in enumerate(zip(a, b)):
            turns_log.append({"id": it["id"], "k": k, "text": x["text"],
                              "reply221": x["reply"], "reply138i": y["reply"],
                              "stage221": x["stage"], "wrote221": x["wrote"],
                              "wrote138i": y["wrote"], "routed221": x["routed"],
                              "routed138i": y["routed"], "ms221": x["ms"],
                              "ms138i": y["ms"]})
            if x["text"].strip().endswith("?"):
                diffs.append(x["ms"] - y["ms"])
                if x["wrote"]:
                    q_wrote.append({"id": it["id"], "k": k,
                                    "text": x["text"],
                                    "base_wrote": y["wrote"]})
        for j, fam, gold in it["scored"]:
            rows.append(score(it, j, fam, gold, a[j], b[j]))
    fams: dict = {}
    for r in rows:
        f = fams.setdefault(r["family"], {"n": 0, "correct": 0, "wrong": 0,
                                          "base_same": 0})
        f["n"] += 1
        f["correct"] += int(r["correct221"])
        f["wrong"] += int(r["wrong_value221"])
        f["base_same"] += int(r["reply221"] == r["reply138i"])
    inv_answers = [r for r in turns_log
                   if r["stage221"] == T221.STAGE221 + "-inverse"
                   and not r["reply221"].startswith("I don't know")]
    summary = {
        "items": len(items), "scored": len(rows),
        "correct": sum(r["correct221"] for r in rows),
        "wrong_values": sum(r["wrong_value221"] for r in rows),
        "by_family": fams,
        "inverse_answers": len(inv_answers),
        "inverse_answers_labelled": sum(T221.LABEL221 in r["reply221"]
                                        for r in inv_answers),
        "question_turns": len(diffs),
        "question_turns_with_write221": q_wrote,
        "table_claimed_and_routed": [
            {"id": r["id"], "k": r["k"], "text": r["text"]}
            for r in turns_log if r["stage221"].startswith(T221.STAGE221)
            and r["routed221"]],
        "median_added_ms": round(statistics.median(diffs), 2)
        if diffs else None,
    }
    (out / "rows.jsonl").write_text("\n".join(json.dumps(
        r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    (out / "turns.jsonl").write_text("\n".join(json.dumps(
        r, ensure_ascii=False) for r in turns_log) + "\n", encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=1,
                                                 ensure_ascii=False),
                                      encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items()
                      if k != "question_turns_with_write221"}, indent=1))
    for r in rows:
        print(("OK   " if r["correct221"] else
               ("WRONG" if r["wrong_value221"] else "MISS ")),
              f"[{r['family']}] {r['id']}: {r['question']!r} -> "
              f"{r['reply221']!r}  (138i: {r['reply138i']!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
