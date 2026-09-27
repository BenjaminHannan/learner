#!/usr/bin/env python3
"""mu-406 prep: Luna-worded two-session chats for the test panel and the practice set ("Making things up about you",
2026-09-27). New file; standard library only (it runs on the Mac through scripts/claude_luna_codex.py).
Plan: artifacts/claude-mu406-20260926/PLAN-draft-3.md (draft; the sealed plan decides).

It imports claude_mu407_prep_luna, which swaps claude_mu407_prep's caller for GPT-6 Luna. mu-407's writer prompt,
chat checks and write loop are used unchanged. Only the facts (new seeds, ids and counts) and the selection differ.
Code picks every fact (claude_mu405_facts.slots); Luna only words the user's messages around them.

  facts   --set test|practice --out F
            test: 75 candidates + 3 smoke, seed 4060; practice: 260 candidates, seed 4061
  write   --facts F --out RAW [--workers 2] [--max-minutes 60]   mu-407's loop; finished chats are kept on a restart
  select  --set test --facts F --raw RAW --out-items I --out-facts F2
            the first 60 passing candidates in id order, plus the passing smoke chats
  select  --set practice --facts F --raw RAW --out-items I --out-facts F2 --out-heldout H --out-heldout-facts HF
            the first 220 passing candidates in id order; 20 of them (seed 4062) go to the held-out teacher-check set
  overlap --a I1 --b I2      report only: user messages of I1 also in I2, by session and turn kind; counts only
  scan    --raw RAW          mu-407's scan strings in kept texts, and user messages repeated in 3 or more chats
  selftest                   no network
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_mu405_facts as F  # noqa: E402
import claude_mu407_prep_luna as L  # noqa: E402  (sets claude_mu407_prep.call_low to the Luna caller)

P = L.P
SETS = {  # seed, candidates, kept, smoke, id prefix
    "test": (4060, 75, 60, 3, "mu406t"),
    "practice": (4061, 260, 220, 0, "mu406p"),
}
HELDOUT_SEED, N_HELDOUT = 4062, 20
PER_CONV = 3


def make_facts(which: str) -> list[dict]:
    seed, n_cand, _, n_smoke, pre = SETS[which]
    rng = random.Random(seed)
    ids = [f"{pre}-{i:03d}" for i in range(1, n_cand + 1)] + [f"{pre}-s{i}" for i in range(1, n_smoke + 1)]
    rows = []
    for iid in ids:
        cand = F.slots(rng)
        keys = rng.sample(sorted(cand), PER_CONV)
        rows.append({"item_id": iid, "smoke": "-s" in iid, "facts": [cand[k] for k in keys],
                     "ask_index": rng.randrange(PER_CONV)})
    return rows


def select(which: str, facts: list[dict], raw: list[dict]):
    """Returns (items, facts_kept, heldout_ids). heldout_ids is empty for the test set."""
    _, _, n_keep, _, _ = SETS[which]
    ok = {r["item_id"]: r for r in raw if r.get("ok")}
    main_ids = [f["item_id"] for f in facts if not f["smoke"] and f["item_id"] in ok][:n_keep]
    if len(main_ids) < n_keep:
        raise SystemExit(f"mu406 select: only {len(main_ids)} passing {which} chats, need {n_keep}")
    smoke_ids = [f["item_id"] for f in facts if f["smoke"] and f["item_id"] in ok]
    held = sorted(random.Random(HELDOUT_SEED).sample(main_ids, N_HELDOUT)) if which == "practice" else []
    keep = main_ids + smoke_ids
    items = [{"item_id": i, "session1": ok[i]["session1"], "session2": ok[i]["session2"]} for i in keep]
    by_id = {f["item_id"]: f for f in facts}
    return items, [by_id[i] for i in keep], held


def user_texts(items: list[dict]) -> set[str]:
    return {t["text"].strip().lower() for it in items for t in it["session1"] + it["session2"]}


def overlap(a: list[dict], b: list[dict]) -> dict:
    """Report only: user messages of `a` that also appear in `b` (case-folded, stripped), by session and turn kind.
    mu-407's Luna chats repeat small talk and ask lines across chats, so a shared message is expected and drops
    nothing; the facts differ by seed."""
    seen = user_texts(b)
    by, chats = {}, 0
    for it in a:
        hit = 0
        for part in ("session1", "session2"):
            for t in it[part]:
                if t["text"].strip().lower() in seen:
                    k = part if part == "session1" else "session2_" + t.get("kind", "?")
                    by[k] = by.get(k, 0) + 1
                    hit = 1
        chats += hit
    return {"a_items": len(a), "b_items": len(b), "shared_user_messages": len(user_texts(a) & seen),
            "a_chats_sharing": chats, "shared_by_place": dict(sorted(by.items()))}


def scan(raw: list[dict]) -> dict:
    texts = L.texts_of({}, raw)
    rep = L.repeats(raw)
    return {"kept_chats": sum(1 for r in raw if r.get("ok")), "scan_hits": L.scan_hits(texts),
            "repeated_messages": len(rep), "max_repeat": max(rep.values(), default=0)}


def jl(path: str) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def wl(path: str, rows: list[dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def selftest() -> None:
    ok = 0
    t, p = make_facts("test"), make_facts("practice")
    assert len(t) == 78 and sum(f["smoke"] for f in t) == 3 and t == make_facts("test"); ok += 1
    assert len(p) == 260 and not any(f["smoke"] for f in p); ok += 1
    old = P.make_facts()
    assert [f["facts"] for f in t[:5]] != [f["facts"] for f in old[:5]]; ok += 1   # not mu-407's seed
    assert P.call_low is L.luna_call; ok += 1
    raw = [{"item_id": f["item_id"], "ok": f["item_id"] != "mu406p-002",
            "session1": [{"text": f"hi {f['item_id']}"}], "session2": [{"kind": "ask", "text": "q"}]} for f in p]
    items, fx, held = select("practice", p, raw)
    ids = [i["item_id"] for i in items]
    assert len(items) == 220 and "mu406p-002" not in ids and ids[-1] == "mu406p-221" and len(fx) == 220; ok += 1
    assert len(held) == 20 and set(held) <= set(ids) and held == select("practice", p, raw)[2]; ok += 1
    rt = [{"item_id": f["item_id"], "ok": True, "session1": [], "session2": []} for f in t]
    ti, tf, th = select("test", t, rt)
    assert len(ti) == 63 and th == [] and sum(f["smoke"] for f in tf) == 3; ok += 1
    try:
        select("test", t, rt[:10])
        raise AssertionError("short set passed")
    except SystemExit:
        ok += 1
    a = [{"session1": [{"text": "My dog Pim "}], "session2": [{"kind": "smalltalk", "text": "yo"}]}]
    b = [{"session1": [{"text": "my dog pim"}], "session2": [{"kind": "ask", "text": "yo"}]}]
    o = overlap(a, b)
    assert o["shared_user_messages"] == 2 and o["a_chats_sharing"] == 1 and o["shared_by_place"] == {
        "session1": 1, "session2_smalltalk": 1}; ok += 1
    s = scan([{"item_id": "x", "ok": True, "session1": [{"text": "Rate limit exceeded"}], "session2": []}])
    assert s["scan_hits"]["rate limit"] == 1 and s["kept_chats"] == 1; ok += 1
    print(f"mu406 prep selftest {ok}/10 ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["facts", "write", "select", "overlap", "scan", "selftest"])
    ap.add_argument("--set", choices=sorted(SETS))
    ap.add_argument("--out")
    ap.add_argument("--facts")
    ap.add_argument("--raw")
    ap.add_argument("--out-items")
    ap.add_argument("--out-facts")
    ap.add_argument("--out-heldout")
    ap.add_argument("--out-heldout-facts")
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--max-minutes", type=float, default=60)
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "facts":
        rows = make_facts(a.set)
        wl(a.out, rows)
        print(json.dumps({"set": a.set, "rows": len(rows), "smoke": sum(r["smoke"] for r in rows)}))
    elif a.cmd == "write":
        if a.workers > 2:
            raise SystemExit("mu406: at most 2 Luna calls at a time (the Director's share)")
        print(json.dumps(P.write_all(jl(a.facts), Path(a.out), L.luna_call, a.workers, a.max_minutes)))
    elif a.cmd == "select":
        items, fx, held = select(a.set, jl(a.facts), jl(a.raw))
        if a.set == "practice":
            hs = set(held)
            wl(a.out_items, [i for i in items if i["item_id"] not in hs])
            wl(a.out_facts, [f for f in fx if f["item_id"] not in hs])
            wl(a.out_heldout, [i for i in items if i["item_id"] in hs])
            wl(a.out_heldout_facts, [f for f in fx if f["item_id"] in hs])
            print(json.dumps({"set": "practice", "train": len(items) - len(hs), "heldout": len(hs)}))
        else:
            wl(a.out_items, items)
            wl(a.out_facts, fx)
            print(json.dumps({"set": "test", "panel": sum(1 for f in fx if not f["smoke"]),
                              "smoke": sum(1 for f in fx if f["smoke"])}))
    elif a.cmd == "overlap":
        print(json.dumps(overlap(jl(a.a), jl(a.b))))
    elif a.cmd == "scan":
        print(json.dumps(scan(jl(a.raw))))


if __name__ == "__main__":
    main()
