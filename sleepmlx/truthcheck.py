"""Truth check before sleep (track I2, 2026-11-04): the same rule as the Desk's src/truthcheck.js, for the cards sleep makes itself.

Before training, every live lesson / rated / insight item is compared with something TRUE (never a model's opinion):
  - insight cards: the executor / puzzle-generator truth hash of their stuck problem (insight.verified);
  - lesson and rated Q&A: Ben's own facts. An answer Ben corrected away for a name in the question (the `wrong` table) is wrong;
    an answer that matches a saved card note of Ben's ("Subject => relation => Object") for a name in the question is right.
Rows are grouped by SOURCE (kind + the night it was made). Per source: checked = right + wrong;
  trusted if checked >= MIN_CHECKED and wrong / checked <= MAX_FAIL -> keep right + unverifiable items, drop the wrong Q&A;
  too many wrong -> keep only verified-right items;
  too few truths: no wrong at all -> keep everything (unchecked); any wrong -> verified-right items only.
Toy evidence: ~/learner-ops/premonition-sleeplab-i2 (RESULTS-truthcheck-v1, PASS 3/3 seeds). Real-Glim effect: untested.
Crash-safe: recipe.py calls night_step inside try/except; a failure skips the step and never ends the night.
"""
from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

from .corpus import norm

MIN_CHECKED, MAX_FAIL = 10, 0.10
KINDS = ("lesson", "rated", "insight")
LOG = "truthcheck-log.jsonl"


def check(rows: List, verify: Callable, source_of: Callable, min_checked: int = MIN_CHECKED, max_fail: float = MAX_FAIL) -> dict:
    """rows -> {kept, dropped, verdict, sources, stats}; verify(row) -> 'ok' | 'bad' | 'none' (a verifier that raises = 'none')."""
    by: Dict[str, List[int]] = defaultdict(list)
    src = []
    for i, r in enumerate(rows):
        try:
            s = str(source_of(r))
        except Exception:
            s = "?"
        src.append(s)
        by[s].append(i)
    verdict = ["none"] * len(rows)
    sources = {}
    for s, idx in by.items():
        ok = bad = 0
        for i in idx:
            try:
                v = verify(rows[i])
            except Exception:
                v = "none"
            v = "ok" if v in (True, "ok") else "bad" if v in (False, "bad") else "none"
            verdict[i] = v
            ok += v == "ok"
            bad += v == "bad"
        checked = ok + bad
        fail = bad / checked if checked else None
        mode = ("trusted" if fail <= max_fail else "failed") if checked >= min_checked else ("unchecked" if bad == 0 else "failed")
        sources[s] = {"n": len(idx), "ok": ok, "bad": bad, "none": len(idx) - checked, "mode": mode, "kept": 0, "dropped": 0}
    kept, dropped = [], []
    for i, r in enumerate(rows):
        S = sources[src[i]]
        if verdict[i] == "ok" or (verdict[i] == "none" and S["mode"] != "failed"):
            kept.append(r)
            S["kept"] += 1
        else:
            dropped.append(r)
            S["dropped"] += 1
    stats = {"n": len(rows), "kept": len(kept), "ok": verdict.count("ok"), "bad": verdict.count("bad"), "none": verdict.count("none"),
             "sources": len(sources), "failed": sum(1 for S in sources.values() if S["mode"] == "failed")}
    return {"kept": kept, "dropped": dropped, "verdict": verdict, "sources": sources, "stats": stats}


def _names_in(q: str, names: Iterable[str]) -> List[str]:
    nq = " " + norm(q) + " "
    return [n for n in names if n and len(n) >= 3 and (" " + n + " ") in nq]


def qa_verdict(q: str, a: str, wrong: Dict[str, set], facts: Dict[str, set]) -> str:
    """One Q&A against Ben's facts: 'bad' if Ben corrected this answer away for a name in the question; 'ok' if it is the object of one
    of Ben's saved card notes about a name in the question; else 'none'."""
    na = norm(a)
    if not na:
        return "none"
    for n in _names_in(q, wrong.keys()):
        if na in wrong[n]:
            return "bad"
    for n in _names_in(q, facts.keys()):
        if na in facts[n]:
            return "ok"
    return "none"


def item_verifier(items: Dict, wrong: Dict[str, set], stuck_by_id: Dict[str, dict]) -> Callable:
    """Item -> 'ok' | 'bad' | 'none'. Ben's facts = live `fact` items from his saved card notes (never `maybe`: card notes are his)."""
    from . import insight as I_mod
    facts: Dict[str, set] = defaultdict(set)
    for it in items.values():
        if it.kind == "fact" and not it.dead and str(it.source).startswith("saved card note"):
            facts[norm(it.subj)].add(norm(it.obj))

    def verify(it) -> str:
        if it.kind == "insight":
            e = stuck_by_id.get(str(it.key).split("|", 1)[-1])
            if not e or not I_mod.checkable(e) or not it.qa:
                return "none"
            return "ok" if any(I_mod.verified(e, a) for _, a in it.qa) else "bad"
        vs = [qa_verdict(q, a, wrong, facts) for q, a in it.qa]
        return "bad" if "bad" in vs else "ok" if "ok" in vs else "none"
    return verify


def night_step(items: Dict, wrong: Dict[str, set], stuck: List[dict], user_data: Optional[Path], log: Callable = print, now: Optional[float] = None) -> dict:
    """Check every live lesson / rated / insight item. Wrong Q&A are removed; items of a failed source that were not verified, and items
    left with no Q&A, are retired (dead). One log line per source kind per night (stdout + userData/truthcheck-log.jsonl)."""
    stuck_by_id = {str(e.get("id")): e for e in stuck or [] if isinstance(e, dict)}
    rows = [it for it in items.values() if it.kind in KINDS and not it.dead]
    verify = item_verifier(items, wrong, stuck_by_id)
    res = check(rows, verify, lambda it: "%s:%s" % (it.kind, it.first))
    emptied = set()
    for it, v in zip(rows, res["verdict"]):
        if v == "bad" and it.kind != "insight":   # drop only the Q&A that contradict Ben
            it.qa = [[q, a] for q, a in it.qa if qa_verdict(q, a, wrong, {}) != "bad"]
            if not it.qa:
                emptied.add(id(it))
    kept = {id(it) for it in res["kept"]}
    for it, v in zip(rows, res["verdict"]):   # the labels are the Q&A: a trusted source keeps a card whose wrong Q&A were removed
        if v == "bad" and it.kind != "insight" and id(it) not in emptied and res["sources"]["%s:%s" % (it.kind, it.first)]["mode"] != "failed":
            kept.add(id(it))
    retired = 0
    for it in rows:
        if id(it) not in kept or id(it) in emptied:
            it.dead = True
            retired += 1
    per = defaultdict(lambda: {"n": 0, "ok": 0, "bad": 0, "none": 0, "failed": 0, "kept": 0})
    for s, S in res["sources"].items():
        k = s.split(":", 1)[0]
        for f in ("n", "ok", "bad", "none", "kept"):
            per[k][f] += S[f]
        per[k]["failed"] += S["mode"] == "failed"
    t = time.time() if now is None else now
    lines = []
    for k in KINDS:
        P = per.get(k) or {"n": 0, "ok": 0, "bad": 0, "none": 0, "failed": 0, "kept": 0}
        line = "%s cards: truth check %d right, %d wrong, %d no truth; kept %d of %d%s" % (
            k, P["ok"], P["bad"], P["none"], P["kept"], P["n"], ("; %d source(s) failed (only verified cards kept)" % P["failed"]) if P["failed"] else "")
        lines.append(line)
        log("[night] " + line)
        if user_data:
            try:
                with open(Path(user_data) / LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"t": int(t * 1000), "part": "sleep-" + k, "mode": "checked", **P}) + "\n")
            except Exception:
                pass
    return {"stats": res["stats"], "retired": retired, "lines": lines, "per": {k: dict(v) for k, v in per.items()}}
