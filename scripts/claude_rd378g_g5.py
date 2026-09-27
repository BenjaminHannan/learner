#!/usr/bin/env python3
"""rd-378g mark G5 (are G's notes true?): blind judge items and the key count (Trustworthy notes thread, 2026-09-27;
rd-378g DRAFT-ADDENDUM-K). New file.

Two note writers write greedy notes over the same fresh dialogs: G (the rd-378g writer) and R (the rd-378 writer,
Claude-trained, the comparison). `make` puts both writers' notes into one shuffled list of judge items with opaque ids,
so a judge cannot tell which writer wrote a note; the id map goes to a separate file the judges never read. `score`
builds the key from two blind judges exactly as rd-371b did (ok where both say ok, unsupported where both say
unsupported, everything else excluded) and gives each writer's unsupported share = key unsupported / (key ok + key
unsupported). Prints counts only, never dialog or note text.

python -B scripts/claude_rd378g_g5.py make --dialogs D.jsonl --rem 2 --g G.jsonl --r R.jsonl --seed 37805 --out DIR
python -B scripts/claude_rd378g_g5.py score --map DIR/map.json --a judge_A.jsonl --b judge_B.jsonl
python -B scripts/claude_rd378g_g5.py selftest
G.jsonl / R.jsonl = claude_rd378_write.py output rows {"dialog","t","notes": [...] or null (unparsed)}.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

BAR, WRONG = 5.0, 15.0   # G5: G share <= R share + 5 points; proved wrong: G share >= R share + 15 points


def rows(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def rem3(i):
    return int(hashlib.sha256(i.encode()).hexdigest(), 16) % 3


def items_for(dialogs, notes_by_writer, seed):
    items, mp, c = [], {}, Counter()
    for w, notes in notes_by_writer.items():
        got = {(r["dialog"], int(r["t"])): r.get("notes") for r in notes}
        for d in dialogs:
            oid = "n5-" + hashlib.sha256(f"{seed}|{w}|{d['dialog']}".encode()).hexdigest()[:10]
            turns = []
            for t in d["turns"]:
                tt = {"t": t["t"], "speaker": t["speaker"], "text": t["text"]}
                if not (d["kind"] == "chat" and t["speaker"] == "assistant"):
                    n = got.get((d["dialog"], int(t["t"])))
                    c[f"{w}:turns"] += 1
                    if n is None:
                        c[f"{w}:unparsed_or_missing"] += 1
                        n = []
                    tt["notes"] = [{"text": x.get("text", ""), "cites": x.get("cites", [0]), "when": x.get("when", "")}
                                   for x in n]
                    c[f"{w}:notes"] += len(n)
                turns.append(tt)
            items.append({"dialog": oid, "kind": d["kind"], "speakers": d.get("speakers", []), "date": d.get("date", ""),
                          "turns": turns})
            mp[oid] = [w, d["dialog"]]
    random.Random(seed).shuffle(items)
    return items, mp, dict(sorted(c.items()))


def key_count(mp, ja, jb):
    a = {(r["dialog"], int(r["t"])): r["verdicts"] for r in ja}
    b = {(r["dialog"], int(r["t"])): r["verdicts"] for r in jb}
    c = Counter()
    for k, va in a.items():
        w = mp.get(k[0], ["?"])[0]
        vb = b.get(k)
        if vb is None or len(vb) != len(va):
            c[f"{w}:turn_mismatch"] += 1
            continue
        for x, y in zip(va, vb):
            c[f"{w}:notes"] += 1
            if x == y == "ok":
                c[f"{w}:ok"] += 1
            elif x == y == "unsupported":
                c[f"{w}:unsupported"] += 1
            else:
                c[f"{w}:excluded"] += 1
    rep = {"counts": dict(sorted(c.items()))}
    share = {}
    for w in ("G", "R"):
        ok, un = c[f"{w}:ok"], c[f"{w}:unsupported"]
        share[w] = round(100 * un / (ok + un), 1) if ok + un else None
    rep["unsupported_share_pct"] = share
    if share["G"] is not None and share["R"] is not None:
        rep["G5_pass"] = share["G"] <= share["R"] + BAR
        rep["G5_proved_wrong"] = share["G"] >= share["R"] + WRONG
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["make", "score", "selftest"])
    ap.add_argument("--dialogs", default="")
    ap.add_argument("--rem", type=int, default=2)
    ap.add_argument("--g", default="")
    ap.add_argument("--r", default="")
    ap.add_argument("--seed", type=int, default=37805)
    ap.add_argument("--out", default="")
    ap.add_argument("--map", default="")
    ap.add_argument("--a", default="")
    ap.add_argument("--b", default="")
    a = ap.parse_args()
    if a.mode == "selftest":
        d = [{"dialog": "x1", "kind": "chat", "speakers": ["user", "assistant"], "date": "1 May 2023", "turns": [
            {"t": 0, "speaker": "user", "text": "a"}, {"t": 1, "speaker": "assistant", "text": "b"},
            {"t": 2, "speaker": "user", "text": "c"}]}]
        g = [{"dialog": "x1", "t": 0, "notes": [{"text": "n", "cites": [0], "when": ""}] * 2},
             {"dialog": "x1", "t": 2, "notes": None}]
        r = [{"dialog": "x1", "t": 0, "notes": [{"text": "m", "cites": [0], "when": ""}]},
             {"dialog": "x1", "t": 2, "notes": [{"text": "k", "cites": [0], "when": ""}]}]
        items, mp, c = items_for(d, {"G": g, "R": r}, 1)
        assert len(items) == 2 and sorted(v[0] for v in mp.values()) == ["G", "R"]
        assert c["G:notes"] == 2 and c["G:unparsed_or_missing"] == 1 and c["R:notes"] == 2 and c["R:turns"] == 2, c
        assert all("notes" not in t for it in items for t in it["turns"] if t["speaker"] == "assistant")
        gid = [k for k, v in mp.items() if v[0] == "G"][0]
        rid = [k for k, v in mp.items() if v[0] == "R"][0]
        ja = [{"dialog": gid, "t": 0, "verdicts": ["ok", "unsupported"]}, {"dialog": gid, "t": 2, "verdicts": []},
              {"dialog": rid, "t": 0, "verdicts": ["unsupported"]}, {"dialog": rid, "t": 2, "verdicts": ["ok"]}]
        jb = [{"dialog": gid, "t": 0, "verdicts": ["ok", "ok"]}, {"dialog": gid, "t": 2, "verdicts": []},
              {"dialog": rid, "t": 0, "verdicts": ["unsupported"]}, {"dialog": rid, "t": 2, "verdicts": ["ok"]}]
        rep = key_count(mp, ja, jb)
        assert rep["unsupported_share_pct"] == {"G": 0.0, "R": 50.0}, rep
        assert rep["counts"]["G:excluded"] == 1 and rep["G5_pass"] and not rep["G5_proved_wrong"], rep
        print("rd378g g5 selftest 1/1 ok")
        return
    if a.mode == "make":
        dialogs = [d for d in rows(a.dialogs) if rem3(d["dialog"]) == a.rem]
        items, mp, c = items_for(dialogs, {"G": rows(a.g), "R": rows(a.r)}, a.seed)
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "items.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items),
                                         encoding="utf-8")
        (out / "map.json").write_text(json.dumps(mp, indent=0), encoding="utf-8")
        print(json.dumps({"dialogs": len(dialogs), "items": len(items),
                          "by_kind": dict(Counter(d["kind"] for d in dialogs)), **c}))
        return
    print(json.dumps(key_count(json.loads(Path(a.map).read_text(encoding="utf-8")), rows(a.a), rows(a.b))))


if __name__ == "__main__":
    main()
