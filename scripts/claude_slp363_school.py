#!/usr/bin/env python3
"""slp-363 (part 1): SLEEP SCHOOL, the nightly practice builder (Fix-sleep thread, 2026-09-25; roadmap 365 stage 2).

Each night, build practice episodes for the loop reasoner from the assistant's OWN notebook: the people and facts
the user actually taught. Output items use the rsn-294 episode format (claude_rsn294_core.gen_episode):
    {"category", "notebook": [{fid, subject, relation, value, when}], "frame": {...},
     "gold": {"answer", "support": [fid, ...]}}
so the sleep research thread's training recipe can use them unchanged. Every gold answer is computed by exact code
over the rows placed in the episode; the rows are always in the input (no fact is ever a closed-book target).

Kinds (visible features differ, as sleep research round 2 item 3 asks):
  value1   one taught fact                      value2   a real two-step chain
  who      reverse: whose R is V?               yesno    true, and false with a near-miss value
  count    a relation with several values       correction  an old row and the newer one that replaced it
  missing  the asked row is absent (answer UNKNOWN), including a broken two-step chain
Distractors are other real rows from the same notebook (near misses first: the same relation for other people).

Also here: variety_log (distinct visible families per night, round 2 item 5) and placebo (grades shuffled across
the batch, round 2 item 2). Checked creative wins (<state_dir>/wins/wins.jsonl) are counted and logged by family;
they are English puzzles, so they feed the 1B stand-in (creative thread), not this row-based reasoner.
Nothing here trains anything and nothing here writes to the notebook.
"""
from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

KINDS363 = ("value1", "value2", "who", "yesno", "count", "correction", "missing")
MAX_ROWS363 = 14


def _rows(nb) -> tuple[list[dict], list[dict]]:
    """(active taught rows, superseded taught rows) as plain dicts with display names."""
    inner = getattr(nb, "nb", nb)
    ents = inner.entities
    act, old = [], []
    for fid, f in inner.facts.items():
        if f.get("source") != "taught":
            continue
        v = f["value"]
        row = {"src": fid, "subject": ents.get(f["subject"], "?"), "relation": f["relation"],
               "value": ents.get(v["entity"], "?") if "entity" in v else str(v.get("literal", "")),
               "is_person": "entity" in v, "n": f.get("n", 0)}
        (act if inner.active(fid) else old).append(row)
    return act, old


def _episode(rng, core, extra, frame, answer, category) -> dict:
    """core rows first (support), then near-miss/other distractors, shuffled, fids assigned."""
    rows = [dict(r) for r in core]
    seen = {(r["subject"], r["relation"], r["value"]) for r in rows}
    for r in extra:
        if len(rows) >= MAX_ROWS363:
            break
        k = (r["subject"], r["relation"], r["value"])
        if k not in seen:
            rows.append(dict(r))
            seen.add(k)
    order = list(range(len(rows)))
    rng.shuffle(order)
    out, sup = [], []
    for i, j in enumerate(order):
        r = rows[j]
        out.append({"fid": f"f{i + 1}", "subject": r["subject"], "relation": r["relation"],
                    "value": r["value"], "when": r.get("n", i)})
        if j < len(core) and r.get("_support", True):
            sup.append(f"f{i + 1}")
    return {"category": category, "notebook": out, "frame": frame,
            "gold": {"answer": answer, "support": sup}, "source": "sleep-school"}


def _frame(kind, who=(), rels=(), value=None, direction=None):
    return {"kind": kind, "who": list(who), "relations": list(rels), "value": value, "direction": direction}


def build_night(nb, seed: int, n: int = 200) -> tuple[list[dict], dict]:
    rng = random.Random(seed)
    act, old = _rows(nb)
    if not act:
        return [], {"items": 0}
    by_sr: dict = {}
    by_rel: dict = {}
    for r in act:
        by_sr.setdefault((r["subject"], r["relation"]), []).append(r)
        by_rel.setdefault(r["relation"], []).append(r)
    single = [r for r in act if len(by_sr[(r["subject"], r["relation"])]) == 1]
    multi = [(k, v) for k, v in by_sr.items() if len(v) >= 2]
    chains = [(a, b) for a in single if a["is_person"]
              for b in single if b["subject"] == a["value"] and b["subject"] != a["subject"]]
    oldpairs = [(o, next((r for r in by_sr.get((o["subject"], o["relation"]), [])), None)) for o in old]
    oldpairs = [(o, r) for o, r in oldpairs if r is not None and r["value"] != o["value"]]
    subjects = sorted({r["subject"] for r in act})
    rels = sorted(by_rel)

    def near(rel, exclude):
        pool = [r for r in by_rel.get(rel, []) if r["subject"] not in exclude]
        rng.shuffle(pool)
        other = [r for r in act if r["relation"] != rel and r["subject"] not in exclude]
        rng.shuffle(other)
        return pool[:4] + other

    items = []
    tries = 0
    while len(items) < n and tries < n * 20:
        tries += 1
        k = rng.choice(KINDS363)
        if k == "value1" and single:
            a = rng.choice(single)
            items.append(_episode(rng, [a], near(a["relation"], {a["subject"]}),
                                  _frame("value", [a["subject"]], [a["relation"]]), a["value"], k))
        elif k == "value2" and chains:
            a, b = rng.choice(chains)
            items.append(_episode(rng, [a, b], near(b["relation"], {a["subject"], b["subject"]}),
                                  _frame("value", [a["subject"]], [a["relation"], b["relation"]]), b["value"], k))
        elif k == "who" and single:
            a = rng.choice(single)
            if sum(1 for r in by_rel[a["relation"]] if r["value"] == a["value"]) != 1:
                continue
            items.append(_episode(rng, [a], near(a["relation"], {a["subject"]}),
                                  _frame("who", [], [a["relation"]], a["value"]), a["subject"], k))
        elif k == "yesno" and single:
            a = rng.choice(single)
            others = [r["value"] for r in by_rel[a["relation"]] if r["value"] != a["value"]]
            if rng.random() < 0.5 or not others:
                items.append(_episode(rng, [a], near(a["relation"], {a["subject"]}),
                                      _frame("yesno", [a["subject"]], [a["relation"]], a["value"]), "yes", k))
            else:
                items.append(_episode(rng, [a], near(a["relation"], {a["subject"]}),
                                      _frame("yesno", [a["subject"]], [a["relation"]], rng.choice(others)), "no", k))
        elif k == "count" and multi:
            (s, rel), vs = rng.choice(multi)
            if len(vs) > 12:
                continue
            items.append(_episode(rng, vs, near(rel, {s}), _frame("count", [s], [rel]), str(len(vs)), k))
        elif k == "correction" and oldpairs:
            o, r = rng.choice(oldpairs)
            o2 = dict(o, _support=False)
            items.append(_episode(rng, [r, o2], near(r["relation"], {r["subject"]}),
                                  _frame("value", [r["subject"]], [r["relation"]]), r["value"], k))
        elif k == "missing" and subjects and rels:
            s = rng.choice(subjects)
            have = {r["relation"] for r in act if r["subject"] == s}
            lack = [x for x in rels if x not in have]
            if not lack:
                continue
            rel = rng.choice(lack)
            mine = [r for r in act if r["subject"] == s]
            extra = [r for r in near(rel, {s}) if not (r["subject"] == s and r["relation"] == rel)]
            ep = _episode(rng, mine[:3], extra, _frame("value", [s], [rel]), "UNKNOWN", k)
            ep["gold"]["support"] = []
            items.append(ep)
    return items, variety_log(items)


def variety_log(items: list[dict]) -> dict:
    fam = Counter()
    for it in items:
        fr = it["frame"]
        fam[(it["category"], len(fr["relations"]), "person" if it["category"] in ("value2", "count") else "-")] += 1
    return {"items": len(items), "per_kind": dict(Counter(it["category"] for it in items)),
            "families": len(fam)}


def placebo(items: list[dict], seed: int) -> list[dict]:
    """Same episodes, gold answers shuffled across the batch (round 2 item 2: sleep must beat this)."""
    rng = random.Random(seed ^ 0x5EED)
    golds = [dict(it["gold"]) for it in items]
    rng.shuffle(golds)
    return [dict(it, gold=g, source="sleep-school-placebo") for it, g in zip(items, golds)]


def check_items(items: list[dict]) -> dict:
    """Independent exact check of every gold answer from the episode's own rows."""
    bad = 0
    for it in items:
        rows, fr, ans = it["notebook"], it["frame"], it["gold"]["answer"]
        look = {}
        for r in rows:
            look.setdefault((r["subject"], r["relation"]), []).append(r)
        if fr["kind"] == "value":
            cur = fr["who"][0]
            got = "UNKNOWN"
            for i, rel in enumerate(fr["relations"]):
                rs = look.get((cur, rel), [])
                if not rs:
                    got = "UNKNOWN"
                    break
                cur = max(rs, key=lambda r: r["when"])["value"]
                got = cur
            ok = got == ans
        elif fr["kind"] == "who":
            ok = [r["subject"] for r in rows if r["relation"] == fr["relations"][0] and r["value"] == fr["value"]] == [ans]
        elif fr["kind"] == "yesno":
            rs = look.get((fr["who"][0], fr["relations"][0]), [])
            ok = ("yes" if any(r["value"] == fr["value"] for r in rs) else "no") == ans
        elif fr["kind"] == "count":
            ok = str(len(look.get((fr["who"][0], fr["relations"][0]), []))) == ans
        else:
            ok = False
        bad += int(not ok)
    return {"items": len(items), "gold_wrong": bad}


def count_wins(state_dir) -> dict:
    p = Path(state_dir) / "wins" / "wins.jsonl"
    if not p.exists():
        return {"wins": 0, "families": 0}
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    fams = {(r.get("checked_by"), len(r.get("rows_used") or []), r.get("source")) for r in rows}
    return {"wins": len(rows), "families": len(fams)}
