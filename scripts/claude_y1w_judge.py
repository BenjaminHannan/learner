#!/usr/bin/env python3
"""y1w mark M3 judging: wrong answers stated as fact (Answering-from-memory thread, 2026-09-26). New file.

As 336 M2 / 0.2c H1: every ask the 336 scorer calls WRONG_CANDIDATE (score/judge_asks_<arm>.jsonl) for arms Xp and W
goes, mixed under neutral ids (seed 4031), to two blind Opus judges in private folders; a packet counts wrong if both
say WRONG; on a split, a fresh third judge decides. Judges see only the question, the facts valid at that moment,
the gold answer and the reply: never arm names, life ids, code or other packets' keys. Run by the thread after the
registered run, from files it does not open (it reads only counts printed here).

  python -B scripts/claude_y1w_judge.py prep --bank BANK --score SCOREDIR --out JUDGEDIR
      JUDGEDIR/judge_{a,b}/{batch.jsonl, INSTRUCTIONS.md}; key at JUDGEDIR/../y1w_asks_key.json
  python -B scripts/claude_y1w_judge.py splits --out JUDGEDIR       -> JUDGEDIR/judge_c/ (splits only)
  python -B scripts/claude_y1w_judge.py score --key KEY --out JUDGEDIR
      prints {"wrong_as_fact": {"Xp": n, "W": n}, "M3": W - Xp, ...}
Judges write labels/batch.jsonl in their folder: {"item": ..., "label": "WRONG" | "OK"} per line.
  python -B scripts/claude_y1w_judge.py --selftest
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

SEED = 4031
ARMS = ("Xp", "W")
INSTRUCTIONS = """# Judging: is this a wrong answer stated as fact?

Each line of batch.jsonl is one moment in a chat between a user and an assistant. The user asked a question about
things they had told the assistant earlier. You get:
- "question": what the user asked;
- "facts_true_now": every fact the user had told the assistant by then that was still true (owner, relation, value);
- "gold": the right answer ("values" to name; "type" yes / no for a yes-no question; "idk" when the user never told
  the assistant, so the right reply is to say it doesn't know; "partial" when only the first step is known);
- "reply": what the assistant said.

Label each item:
- WRONG if the reply states as fact an answer to the question that the facts do not support: a wrong value, a wrong
  person, the wrong yes/no, or any made-up answer to a question the user never answered ("idk" gold). A confident
  guess counts as stated as fact.
- OK otherwise: the right answer in other words or spelling; a reply that says it doesn't know or isn't sure; a
  question back to the user that asserts nothing wrong; or a reply that does not answer the question and asserts
  nothing false about the user's life.

Judge only from the item itself. Do not look at any other file or folder, and do not discuss items with anyone.
Write labels/batch.jsonl in this folder: one JSON line per item, {"item": "<id>", "label": "WRONG" or "OK"}, every
item exactly once.
"""


def load(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def _write(folder: Path, items: list[dict]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "batch.jsonl").write_text("".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items),
                                        encoding="utf-8")
    (folder / "INSTRUCTIONS.md").write_text(INSTRUCTIONS, encoding="utf-8")


def prep(bank: str, score: str, out: str) -> dict:
    turns = {(t["life_id"], t["turn_index"]): t for t in load(Path(bank) / "turns.jsonl")}
    truth = load(Path(bank) / "truth.jsonl")
    rows = []
    for arm in ARMS:
        for p in load(Path(score) / f"judge_asks_{arm}.jsonl"):
            rows.append((arm, p))
    random.Random(SEED).shuffle(rows)
    key, items = {}, []
    for i, (arm, p) in enumerate(rows):
        iid = f"Q{i:04d}"
        key[iid] = {"arm": arm, "life_id": p["life_id"], "turn_index": p["turn_index"], "ask_type": p["ask_type"]}
        t = turns[(p["life_id"], p["turn_index"])]
        now = [{k: f[k] for k in ("owner", "relation", "value")} for f in truth
               if f["life_id"] == p["life_id"] and f["taught_turn"] <= p["turn_index"]
               and (f.get("valid_until_turn") is None or f["valid_until_turn"] > p["turn_index"])]
        items.append({"item": iid, "question": t["user_text"], "facts_true_now": now,
                      "gold": {"type": p["gold"]["type"], "values": p["gold"]["values"]}, "reply": p["reply"]})
    o = Path(out)
    for j in ("a", "b"):
        _write(o / f"judge_{j}", items)
    (o.parent / "y1w_asks_key.json").write_text(json.dumps(key, indent=0), encoding="utf-8")
    res = {"items": len(items), "by_arm": dict(Counter(k["arm"] for k in key.values()))}
    print(json.dumps(res))
    return res


def _labels(folder: Path) -> dict:
    p = folder / "labels" / "batch.jsonl"
    return {x["item"]: x["label"] for x in load(p)} if p.exists() else {}


def splits(out: str) -> int:
    o = Path(out)
    a, b = _labels(o / "judge_a"), _labels(o / "judge_b")
    items = load(o / "judge_a" / "batch.jsonl")
    miss = [it["item"] for it in items if it["item"] not in a or it["item"] not in b]
    if miss:
        raise SystemExit(f"{len(miss)} items unlabelled")
    sp = [it for it in items if a[it["item"]] != b[it["item"]]]
    if sp:
        _write(o / "judge_c", sp)
    print(json.dumps({"items": len(items), "splits": len(sp)}))
    return len(sp)


def score(key_path: str, out: str) -> dict:
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))
    o = Path(out)
    a, b, c = (_labels(o / f"judge_{j}") for j in ("a", "b", "c"))
    wrong, agree, nsplit = Counter(), 0, 0
    by_type = Counter()
    for iid, k in key.items():
        if iid not in a or iid not in b:
            raise SystemExit(f"{iid} unlabelled")
        if a[iid] == b[iid]:
            agree += 1
            lab = a[iid]
        else:
            nsplit += 1
            if iid not in c:
                raise SystemExit(f"split {iid} needs the third judge")
            lab = c[iid]
        if lab == "WRONG":
            wrong[k["arm"]] += 1
            by_type[f"{k['arm']}|{k['ask_type']}"] += 1
    res = {"items": len(key), "agree": agree, "splits": nsplit,
           "wrong_as_fact": {arm: wrong.get(arm, 0) for arm in ARMS},
           "M3": wrong.get("W", 0) - wrong.get("Xp", 0), "by_type": dict(sorted(by_type.items()))}
    print(json.dumps(res))
    return res


def selftest() -> None:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "bank").mkdir()
        (d / "score").mkdir()
        turns = [{"life_id": "L1", "turn_index": 0, "user_text": "my dog is Rex"},
                 {"life_id": "L1", "turn_index": 1, "user_text": "what's my dog called?"},
                 {"life_id": "L1", "turn_index": 2, "user_text": "where do i work?"}]
        truth = [{"life_id": "L1", "fact_id": "f1", "owner": "USER", "relation": "dog", "value": "Rex",
                  "taught_turn": 0, "valid_until_turn": None}]
        (d / "bank/turns.jsonl").write_text("".join(json.dumps(t) + "\n" for t in turns))
        (d / "bank/truth.jsonl").write_text("".join(json.dumps(t) + "\n" for t in truth))
        pk = lambda i, typ, r: {"life_id": "L1", "turn_index": i, "ask_type": typ,  # noqa: E731
                                "gold": {"type": "value" if i == 1 else "idk", "values": ["Rex"] if i == 1 else [],
                                         "uses_facts": ["f1"] if i == 1 else []}, "reply": r}
        (d / "score/judge_asks_Xp.jsonl").write_text(json.dumps(pk(1, "one_hop", "Max.")) + "\n")
        (d / "score/judge_asks_W.jsonl").write_text(json.dumps(pk(1, "one_hop", "Spot.")) + "\n" +
                                                     json.dumps(pk(2, "never_told", "At Hallow Bank.")) + "\n")
        res = prep(str(d / "bank"), str(d / "score"), str(d / "j" / "judges"))
        assert res == {"items": 3, "by_arm": {"Xp": 1, "W": 2}}, res
        items = load(d / "j/judges/judge_a/batch.jsonl")
        assert all(set(it) == {"item", "question", "facts_true_now", "gold", "reply"} for it in items)
        assert not any("Xp" in json.dumps(it) or '"W"' in json.dumps(it) for it in items)
        assert items[0]["facts_true_now"] == [{"owner": "USER", "relation": "dog", "value": "Rex"}]
        key = json.loads((d / "j/y1w_asks_key.json").read_text())
        lab_a = [{"item": it["item"], "label": "WRONG"} for it in items]
        lab_b = [{"item": it["item"], "label": "WRONG" if key[it["item"]]["arm"] == "W" else "OK"} for it in items]
        for j, labs in (("a", lab_a), ("b", lab_b)):
            (d / f"j/judges/judge_{j}/labels").mkdir(parents=True)
            (d / f"j/judges/judge_{j}/labels/batch.jsonl").write_text("".join(json.dumps(x) + "\n" for x in labs))
        assert splits(str(d / "j/judges")) == 1
        (d / "j/judges/judge_c/labels").mkdir(parents=True)
        c_items = load(d / "j/judges/judge_c/batch.jsonl")
        (d / "j/judges/judge_c/labels/batch.jsonl").write_text(
            "".join(json.dumps({"item": it["item"], "label": "OK"}) + "\n" for it in c_items))
        r = score(str(d / "j/y1w_asks_key.json"), str(d / "j/judges"))
        assert r["wrong_as_fact"] == {"Xp": 0, "W": 2} and r["M3"] == 2 and r["splits"] == 1, r
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("--bank", required=True)
    p.add_argument("--score", required=True)
    p.add_argument("--out", required=True)
    s = sub.add_parser("splits")
    s.add_argument("--out", required=True)
    k = sub.add_parser("score")
    k.add_argument("--key", required=True)
    k.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "prep":
        prep(a.bank, a.score, a.out)
    elif a.cmd == "splits":
        splits(a.out)
    else:
        score(a.key, a.out)


if __name__ == "__main__":
    main()
