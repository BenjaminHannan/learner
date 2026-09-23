#!/usr/bin/env python3
"""Exp 270 POST-SEAL panel scorer (new file, disclosed D3).

Schema gate (mirrors the writer's make_panel.py self-checks): 100 lines,
ids t270-001..t270-100 in family-block order, families casual 40 /
casual_q 15 / lower_trap 15 / clean 30, keys {id,family,turn,gold,clear,
notes}, frame keys, lowercase/no-?/no-apos rules for the casual
families, clean capitalisation/punctuation rules, trap-word presence.
Any deviation prints SCHEMA-MISMATCH and exits 3 (VOID, never scored).

Scoring (brief marks; triple->frame proxy D5 for the sealed loop arms):
- norm = lowercase + strip edge punctuation/spaces.
- added frames per item = stored_after_turn minus boot_triples, mapped to
  (subject, relation, value); loop subject USER compares as "me".
- gold TEACH set = {(subject, relation-or-alias, value)} per gold frame
  (relation_aliases accepted; species ignored: the loop has none).
- exact TEACH item = added == gold (for [] gold: added empty).
- casual_q (ASK gold): the loop emits no ASK frames, so exact ASK = False
  by construction; reported beside: no-write count and reply-mentions
  counts (descriptive only).
- wrong[item] (for M3/M5): TEACH families (casual, clean-TEACH,
  lower_trap): added != gold frames; casual_q and clean-ASK: any write.
- M1: casual exact /40 AND margin vs A263. M2: casual_q exact /15.
  M3: lower_trap wrong count. M4: clean reply identical A vs A263 /30.
  M5: new-wrong items (A wrong, A263 right) overall. M6: median norm_ms.

Usage: python -B scripts/claude_type270_panelscore.py <panel.jsonl>
         <rowsA.jsonl> <rows263.jsonl> [out.json]
"""
import json
import sys
from pathlib import Path

FAMS = {"casual": 40, "casual_q": 15, "lower_trap": 15, "clean": 30}
KEYS = {"id", "family", "turn", "gold", "clear", "notes"}
TEACH_KEYS = {"act", "subject", "relation", "relation_aliases", "value"}
ASK_KEYS = {"act", "subject", "relation", "chain", "relation_aliases",
            "chain_aliases"}
TRAP_WORDS = ["boss", "rose", "may", "frank", "bill", "grace", "robin",
              "april", "hope", "faith", "mark", "chase"]


def mismatch(msg):
    print(f"SCHEMA-MISMATCH: {msg}", flush=True)
    sys.exit(3)


def norm(s) -> str:
    return str(s).lower().strip().strip(" \t\n.,;:!?'\"()").strip()


def load_panel(path):
    items = [json.loads(x) for x in Path(path).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    if len(items) != 100:
        mismatch(f"panel has {len(items)} items, want 100")
    want_ids = [f"t270-{i:03d}" for i in range(1, 101)]
    if [it.get("id") for it in items] != want_ids:
        mismatch("ids are not t270-001..t270-100 in order")
    fams = {}
    for it in items:
        if not isinstance(it, dict) or set(it) != KEYS:
            mismatch(f"keys {sorted(it) if isinstance(it, dict) else it}")
        fams[it["family"]] = fams.get(it["family"], 0) + 1
        if not isinstance(it["turn"], str) or not it["turn"]:
            mismatch(f"{it['id']} bad turn")
        if not isinstance(it["clear"], bool):
            mismatch(f"{it['id']} clear not bool")
        if not isinstance(it["notes"], str):
            mismatch(f"{it['id']} notes not str")
        if not isinstance(it["gold"], list):
            mismatch(f"{it['id']} gold not list")
        for g in it["gold"]:
            if g.get("act") == "TEACH":
                if set(g) != TEACH_KEYS:
                    mismatch(f"{it['id']} TEACH keys {sorted(g)}")
            elif g.get("act") == "ASK":
                if set(g) != ASK_KEYS:
                    mismatch(f"{it['id']} ASK keys {sorted(g)}")
            else:
                mismatch(f"{it['id']} bad act {g}")
    if fams != FAMS:
        mismatch(f"family counts {fams} != {FAMS}")
    for n, it in enumerate(items):
        fam, t = it["family"], it["turn"]
        blk = "casual" if n < 40 else ("casual_q" if n < 55
                                       else ("lower_trap" if n < 70
                                             else "clean"))
        if fam != blk or it["id"] != want_ids[n]:
            mismatch(f"block order at line {n + 1}")
        if fam in ("casual", "casual_q", "lower_trap"):
            if t != t.lower():
                mismatch(f"{it['id']} not lowercase")
            if "?" in t:
                mismatch(f"{it['id']} has ?")
        if fam == "casual" and "'" in t:
            mismatch(f"{it['id']} casual has apostrophe")
        if fam == "clean":
            if not t[0].isupper():
                mismatch(f"{it['id']} clean not capitalised")
            acts = [g["act"] for g in it["gold"]]
            if acts == ["TEACH"] and not t.endswith("."):
                mismatch(f"{it['id']} clean TEACH w/o period")
            if acts == ["ASK"] and not t.endswith("?"):
                mismatch(f"{it['id']} clean ASK w/o ?")
        if fam == "lower_trap":
            if not any(w in t.lower() for w in TRAP_WORDS):
                mismatch(f"{it['id']} trap w/o trap word")
    print("SCHEMA OK")
    return items


def frames_added(row):
    boot = {tuple(x) for x in row["boot_triples"]}
    return [tuple(x) for x in row["stored_after_turn"]
            if tuple(x) not in boot]


def gold_teach_set(gold):
    out = set()
    for g in gold:
        if g["act"] != "TEACH":
            continue
        subj = norm(g["subject"])
        val = norm(g["value"])
        rels = {norm(g["relation"])} | {norm(a) for a in
                                        g["relation_aliases"]}
        out.add((subj, frozenset(rels), val))
    return out


def added_frames(row):
    out = set()
    for s, r, v in frames_added(row):
        subj = norm(s)
        if subj == "user":
            subj = "me"
        out.add((subj, norm(r), norm(v)))
    return out


def teach_exact(item, row):
    want = gold_teach_set(item["gold"])
    if any(g["act"] == "ASK" for g in item["gold"]):
        return False
    got = added_frames(row)
    if len(got) != len(want):
        if not want and not got:
            return True
        return False
    for (ws, wrels, wv) in want:
        if not any(s == ws and wv == v and r in wrels
                   for (s, r, v) in got):
            return False
    return True


def is_wrong(item, row):
    """Strict equality (misses count). Kept for M1-style reporting."""
    acts = [g["act"] for g in item["gold"]]
    if acts and all(a == "ASK" for a in acts):
        return bool(frames_added(row))
    return not teach_exact(item, row)


def extras(item, row):
    """Wrong SAVES (brief M3/M5 reading): added frames outside gold.

    A missed gold frame is not a save; only extras count. For ASK-gold
    items any write counts.
    """
    acts = [g["act"] for g in item["gold"]]
    if acts and all(a == "ASK" for a in acts):
        return sorted(frames_added(row))
    want = gold_teach_set(item["gold"])
    got = added_frames(row)
    out = []
    for (s, r, v) in got:
        if not any(s == ws and v == wv and r in wrels
                   for (ws, wrels, wv) in want):
            out.append((s, r, v))
    return sorted(out)


def main(argv):
    items = load_panel(argv[1])
    rows_a = [json.loads(x) for x in Path(argv[2]).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    rows_b = [json.loads(x) for x in Path(argv[3]).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    bya = {r["id"]: r for r in rows_a}
    byb = {r["id"]: r for r in rows_b}
    if sorted(bya) != sorted(byb) or len(bya) != 100:
        print("row coverage != 100 ids", flush=True)
        sys.exit(2)
    res = []
    for it in items:
        ra, rb = bya[it["id"]], byb[it["id"]]
        ea = teach_exact(it, ra) if not any(
            g["act"] == "ASK" for g in it["gold"]) else False
        eb = teach_exact(it, rb) if not any(
            g["act"] == "ASK" for g in it["gold"]) else False
        wa, wb = is_wrong(it, ra), is_wrong(it, rb)
        ident = ra["turn_reply"] == rb["turn_reply"]
        res.append({"id": it["id"], "family": it["family"],
                    "a_exact": ea, "b_exact": eb,
                    "a_wrong": wa, "b_wrong": wb,
                    "identical": ident,
                    "a_added": sorted(frames_added(ra)),
                    "b_added": sorted(frames_added(rb)),
                    "norm_ms": ra.get("norm_ms") or 0.0})
    byfam: dict = {}
    for r in res:
        f = byfam.setdefault(r["family"], [])
        f.append(r)
    cas = byfam["casual"]
    m1a = sum(r["a_exact"] for r in cas)
    m1b = sum(r["b_exact"] for r in cas)
    q = byfam["casual_q"]
    m2a = sum(r["a_exact"] for r in q)
    qnowrite_a = sum(1 for r in q
                     if not frames_added(bya[r["id"]]))
    qnowrite_b = sum(1 for r in q
                     if not frames_added(byb[r["id"]]))
    tr = byfam["lower_trap"]
    m3a = sum(1 for r in tr if extras(
        next(i for i in items if i["id"] == r["id"]), bya[r["id"]]))
    m3b = sum(1 for r in tr if extras(
        next(i for i in items if i["id"] == r["id"]), byb[r["id"]]))
    trapmiss_a = sum(r["a_wrong"] for r in tr)
    cl = byfam["clean"]
    m4i = sum(r["identical"] for r in cl)
    newwrong = []
    for r in res:
        it = next(i for i in items if i["id"] == r["id"])
        if extras(it, bya[r["id"]]) and not extras(it, byb[r["id"]]):
            newwrong.append(r["id"])
    ms = sorted(r["norm_ms"] for r in res)
    med = ms[len(ms) // 2]
    print(f"M1 casual exact TEACH: A {m1a}/40  A263 {m1b}/40  "
          f"margin {m1a - m1b}  (bar >=30 and >=+20)")
    print(f"M2 casual_q ASK: A {m2a}/15  (bar >=12; loop emits no ASK; "
          f"no-write A {qnowrite_a}/15  A263 {qnowrite_b}/15)")
    print(f"M3 lower_trap wrong SAVES: A {m3a}/15  A263 {m3b}/15  "
          f"(bar <=1; trap misses incl. real-fact-only: A {trapmiss_a})")
    print(f"M4 clean identical: {m4i}/30  (bar 30/30)")
    print(f"M5 new wrong saves vs A263: {len(newwrong)} {newwrong}  "
          f"(bar 0)")
    print(f"M6 norm_ms median: {med}  (bar <=20)")
    for r in res:
        it = next(i for i in items if i["id"] == r["id"])
        ex = extras(it, bya[r["id"]])
        if ex:
            print(f"EXTRA-A {r['id']} {r['family']} {ex}")
    for r in res:
        if r["family"] == "casual" and r["a_exact"]:
            print(f"HIT A {r['id']} added={r['a_added']}")
    for r in res:
        if r["a_wrong"] and r["family"] != "casual_q":
            print(f"WRONGA {r['id']} {r['family']} "
                  f"added={r['a_added']}")
    if len(argv) > 4:
        Path(argv[4]).write_text(json.dumps(
            {"rows": res,
             "marks": {"m1a": m1a, "m1b": m1b, "m2a": m2a,
                       "qnowrite_a": qnowrite_a,
                       "qnowrite_b": qnowrite_b, "m3a": m3a,
                       "m3b": m3b, "trapmiss_a": trapmiss_a,
                       "m4i": m4i, "newwrong": newwrong,
                       "m6med": med}}, indent=1, default=str),
            encoding="utf-8")
    verdict = (m1a >= 30 and (m1a - m1b) >= 20 and m2a >= 12 and m3a <= 1
               and m4i == 30 and not newwrong and med <= 20)
    print("M1-M6:", "PASS" if verdict else "FAIL")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
