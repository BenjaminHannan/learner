#!/usr/bin/env python3
"""rsn-296: "sleep school" practice generator (idea #16, MLC-style varied practice).

The ONE change from rsn-294: practice notebooks vary in STRUCTURE, not only in symbols.
294 re-shuffled every name/value/relation into fresh symbols each episode (half of MLC) but
always built notebooks the same way; it scored 100/100 on that style and far lower on blind
notebooks (VERIFY-director.md, D1).  Here every episode draws its own style:

  - size: 3-40 rows (log-uniform)
  - extra facts about the asked person (0-8), including several values for the same
    relation (kids, friends, pets)
  - extra facts about the people along a chain (0-5 each)
  - other people (0-10) with 1-5 facts each; half the time they reuse the question's own
    relations (near misses)
  - people reused as values (someone's friend is the asked person, a chain person, ...)
  - 'when' stamps in a random order (a correction's newer fact still has the larger stamp)
  - multi-word and numeric values anywhere off the answer path

Question kinds and answers come from rsn-294's generator unchanged (same kinds, same frames,
three-step still never practised).  Every episode is re-solved by an independent solver
below and thrown away if the answer is not exactly the gold (so extra facts can never make
the gold wrong).  Written from rsn-294's own diagnosis only; no panel item was read.

Use: import this module BEFORE training; it replaces claude_rsn294_core.gen_episode.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn294_core as C  # noqa: E402

_base_gen = C.gen_episode
_K = C._key


def solve(ep: dict) -> str | None:
    """independent solver on frame + rows; None if the episode is ambiguous."""
    rows, fr = ep["notebook"], ep["frame"]
    k, rels, who = fr["kind"], fr.get("relations") or [], fr.get("who") or []

    if k == "value":
        c = who[0]
        for r in rels:
            h = [x for x in rows if _K(x["subject"]) == _K(c) and _K(x["relation"]) == _K(r)]
            if not h:
                return "UNKNOWN"
            # a hop must be single-valued unless it is a correction (same pair, newest wins)
            c = max(h, key=lambda x: int(x["when"]))["value"]
            if len(h) > 1 and ep.get("category") != "correction":
                return None
        return c
    if k == "who":
        subs = {x["subject"] for x in rows if _K(x["relation"]) == _K(rels[0])
                and _K(x["value"]) == _K(fr["value"])}
        return subs.pop() if len(subs) == 1 else None
    if k == "yesno":
        h = [x for x in rows if _K(x["subject"]) == _K(who[0]) and _K(x["relation"]) == _K(rels[0])]
        if len(h) != 1:
            return None
        return "yes" if _K(h[0]["value"]) == _K(fr["value"]) else "no"
    if k == "count":
        return str(sum(1 for x in rows if _K(x["subject"]) == _K(who[0])
                       and _K(x["relation"]) == _K(rels[0])))
    if k == "compare":
        v = {}
        for w in who:
            h = [x for x in rows if _K(x["subject"]) == _K(w) and _K(x["relation"]) == _K(rels[0])]
            if len(h) != 1:
                return None
            v[w] = float(h[0]["value"])
        if len(set(v.values())) < 2:
            return None
        return (max if fr["direction"] == "more" else min)(v, key=v.get)
    if k in ("before", "after"):
        h = sorted([x for x in rows if _K(x["subject"]) == _K(who[0]) and _K(x["relation"]) == _K(rels[0])
                    and x.get("year") is not None], key=lambda x: x["year"])
        vals = [_K(x["value"]) for x in h]
        if vals.count(_K(fr["value"])) != 1:
            return None
        i = vals.index(_K(fr["value"]))
        j = i - 1 if k == "before" else i + 1
        return h[j]["value"] if 0 <= j < len(h) else None
    return None


def _style(rng):
    return {
        "size": int(round(math.exp(rng.uniform(math.log(3), math.log(40))))),
        "about_asked": rng.randint(0, 8),
        "about_chain": rng.randint(0, 5),
        "others": rng.randint(0, 10),
        "near_miss": rng.random() < 0.5,
        "reuse": rng.uniform(0.0, 0.6),
        "multi": rng.uniform(0.0, 0.5),
        "shuffle_when": rng.random() < 0.6,
    }


def _value(rng, b, rel, names, st):
    if rel in C.NUM_RELS:
        return C.num_value(rng, rel)
    if names and rng.random() < st["reuse"]:
        return rng.choice(names)
    return b.name() if rel in C.PERSON_RELS or rel in C.MULTI_RELS else C.thing_value(rng, rel)


def gen_episode296(rng: random.Random, kind: str | None = None, hops: int | None = None,
                   n_rows: tuple[int, int] | None = None, _tries: int = 50) -> dict:
    for _ in range(_tries):
        core = _base_gen(rng, kind, hops, n_rows=(0, 0))      # the question + answer rows only
        st = _style(rng)
        if n_rows is not None:
            st["size"] = rng.randint(*n_rows)
        rows = [dict(r) for r in core["notebook"]]
        fr, gold = core["frame"], core["gold"]
        b = C.Book(rng)
        for r in rows:
            b.used.add(r["subject"]); b.used.add(str(r["value"]))
        b.rows, b.when = rows, max([r["when"] for r in rows] + [0])
        asked = (fr.get("who") or [None])[0]
        chain = [r["value"] for r in rows if r["relation"] in C.PERSON_RELS]
        qrels = list(fr.get("relations") or [])
        taken = {(r["subject"], r["relation"]) for r in rows}
        names = sorted({r["subject"] for r in rows} | set(chain))
        all_rels = C.PERSON_RELS + C.THING_RELS + C.NUM_RELS + C.MULTI_RELS

        def add(subj, rel, multi_ok=False):
            if len(b.rows) >= min(st["size"], C.MAX_ROWS):
                return
            if (subj, rel) in taken and not (multi_ok and rel in C.MULTI_RELS):
                return
            v = _value(rng, b, rel, names, st)
            if _K(v) == _K(subj):
                return
            b.add(subj, rel, v)
            taken.add((subj, rel))
            if rel in C.PERSON_RELS or rel in C.MULTI_RELS:
                names.append(str(v))

        if asked:
            for _ in range(st["about_asked"]):
                r = rng.choice(C.MULTI_RELS) if rng.random() < st["multi"] else rng.choice(all_rels)
                add(asked, r, multi_ok=True)
        for p in chain:
            for _ in range(st["about_chain"]):
                add(p, rng.choice(all_rels))
        for _ in range(st["others"]):
            p = rng.choice(names) if rng.random() < st["reuse"] else b.name()
            names.append(p)
            for _ in range(rng.randint(1, 5)):
                r = rng.choice(qrels) if (st["near_miss"] and qrels and rng.random() < 0.5) else rng.choice(all_rels)
                add(p, r, multi_ok=True)
        while len(b.rows) < min(st["size"], C.MAX_ROWS):          # fill up with strangers
            n0 = len(b.rows)
            add(b.name(), rng.choice(all_rels))
            if len(b.rows) == n0:
                break
        rows = b.rows
        if st["shuffle_when"]:
            stamps = rng.sample(range(1, 4 * len(rows) + 1), len(rows))
            for r, w in zip(rows, stamps):
                r["when"] = w
        rng.shuffle(rows)
        for i, r in enumerate(rows):
            r["fid"] = f"f{i + 1}"
        ep = {"category": core["category"], "notebook": rows, "frame": fr,
              "gold": {"answer": gold["answer"], "support": []}}
        # recompute support fids by matching the core's support rows (content equality)
        core_sup = {(s["subject"], s["relation"], s["value"]) for s in core["notebook"]
                    if s["fid"] in set(gold["support"])}
        ep["gold"]["support"] = [r["fid"] for r in rows
                                 if (r["subject"], r["relation"], r["value"]) in core_sup]
        if core["category"] == "correction":
            pair = [r for r in rows if r["subject"] == asked and r["relation"] == qrels[0]]
            newest = [r for r in pair if _K(r["value"]) == _K(gold["answer"])]
            if len(newest) != 1:
                continue
            top = max(int(r["when"]) for r in pair)
            if int(newest[0]["when"]) != top:          # swap stamps so the gold is newest
                other = max(pair, key=lambda r: int(r["when"]))
                newest[0]["when"], other["when"] = other["when"], newest[0]["when"]
        if len({int(r["when"]) for r in rows}) != len(rows):
            continue
        s = solve(ep)
        if s is not None and _K(s) == _K(gold["answer"]):
            return ep
    raise RuntimeError("could not build a consistent episode")


C.gen_episode = gen_episode296


if __name__ == "__main__":
    import collections
    rng = random.Random(3)
    sizes, fails = collections.Counter(), 0
    for k in ["value1", "value2", "value3", "who", "yesno", "count", "compare", "before",
              "after", "correction", "missing"]:
        for _ in range(2000):
            ep = gen_episode296(rng, k)
            sizes[len(ep["notebook"]) // 10 * 10] += 1
            enc, infos = C.encode([ep], rng)
            ga = C.gold_action(ep, infos[0])
            if ga is None or _K(C.decode(ga, infos[0])) != _K(ep["gold"]["answer"]):
                fails += 1
    print("row-count buckets", dict(sorted(sizes.items())), "gold-action mismatches", fails)
    print("selftest ok" if fails == 0 else "selftest FAIL")
