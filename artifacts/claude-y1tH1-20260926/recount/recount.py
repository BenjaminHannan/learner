#!/usr/bin/env python3
"""Independent recount of y1tH1 H1a-H1d from the result files. Prints counts only."""
import json
import math
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/home/user/learner")
sys.dont_write_bytecode = True  # leave the repository untouched
sys.path.insert(0, str(REPO / "scripts"))
from claude_e2e336_score import score_ask  # noqa: E402

PANEL = REPO / "artifacts/claude-spare401-20260926/panel"
RUN = REPO / "artifacts/claude-y1tH1-20260926"


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


turns = load(PANEL / "turns.jsonl")
tmap = {(t["life_id"], t["turn_index"]): t for t in turns}
assert len(tmap) == len(turns)
ask_keys = {k for k, t in tmap.items() if t["kind"] == "ask"}
edit_keys = {k for k in ask_keys if tmap[k]["ask_type"] == "edit"}

decoys = load(PANEL / "decoys.jsonl")
decoy_keys = {(d["life_id"], d["checked_by"]) for d in decoys}
assert decoy_keys <= ask_keys, "a decoy names a turn that is not an ask"

# judges
key = json.loads((RUN / "judges/key_asks.json").read_text())
packets = load(RUN / "judges/asks.jsonl")
j1 = {r["id"]: r["verdict"] for r in load(RUN / "judges/j1.jsonl")}
j2 = {r["id"]: r["verdict"] for r in load(RUN / "judges/j2.jsonl")}
j3 = {r["id"]: r["verdict"] for r in load(RUN / "judges/j3.jsonl")}
pids = [p["id"] for p in packets]
assert len(set(pids)) == len(pids) == len(key) and set(pids) == set(j1) == set(j2) == set(key)
splits = {i for i in pids if j1[i] != j2[i]}
assert set(j3) == splits, "j3 ids differ from the j1/j2 splits"
final = {i: (j1[i] if j1[i] == j2[i] else j3[i]) for i in pids}
split_file = set(json.loads((RUN / "judges/split_ids.json").read_text()))

res = {}
for arm in "AB":
    rows = load(RUN / f"score/arm_{arm}.jsonl")
    rmap = {(r["life_id"], r["turn_index"]): r for r in rows}
    assert len(rmap) == len(rows) and set(rmap) == ask_keys, f"arm {arm} rows != asks"
    cls = {k: score_ask(tmap[k], rmap[k], None) for k in ask_keys}
    wc = {k for k, c in cls.items() if c == "WRONG_CANDIDATE"}
    right = {k for k, c in cls.items() if c in ("RIGHT", "RIGHT_CONFIRM")}

    # judge_asks file must list exactly the WRONG_CANDIDATE asks
    ja = {(r["life_id"], r["turn_index"]) for r in load(RUN / f"score/judge_asks_{arm}.jsonl")}
    ja_match = ja == wc

    # map each packet of this arm to its ask by (question text, reply text); must be 1:1
    by_text = {}
    for k in wc:
        sig = (tmap[k]["user_text"], rmap[k]["reply"])
        assert sig not in by_text, "ambiguous packet signature"
        by_text[sig] = k
    pk2ask = {}
    for p in packets:
        if key[p["id"]] != arm:
            continue
        k = by_text.get((p["question"], p["reply"]))
        assert k is not None, "packet does not match a WRONG_CANDIDATE ask"
        assert k not in pk2ask.values(), "two packets map to one ask"
        pk2ask[p["id"]] = k
    assert set(pk2ask.values()) == wc, "some WRONG_CANDIDATE ask has no packet"
    jw = {k for i, k in pk2ask.items() if final[i] == "wrong"}

    res[arm] = dict(
        asks=len(rows),
        wc=len(wc),
        packets=len(pk2ask),
        ja_match=ja_match,
        splits=len([i for i in pk2ask if i in splits]),
        H1a=len(jw & edit_keys),
        H1b=len(right & edit_keys),
        H1c=len(right & decoy_keys),
        H1d=len(jw - edit_keys),
        classes=Counter(cls.values()),
    )

A, B = res["A"], res["B"]
print("y1tH1 recount (independent)")
print(f"edit asks per arm: {len(edit_keys)}; decoy rows: {len(decoys)}; distinct decoy asks: {len(decoy_keys)}")
print()
print(f"{'measure':<42}{'A':>6}{'B':>6}")
for lab, k in [("H1a judged wrong, edit asks", "H1a"), ("H1b right, edit asks", "H1b"),
               ("H1c right, decoy asks", "H1c"), ("H1d judged wrong, non-edit asks", "H1d"),
               ("WRONG_CANDIDATE asks", "wc"), ("judge packets", "packets"),
               ("splits (j1 != j2)", "splits"), ("asks", "asks")]:
    print(f"{lab:<42}{A[k]:>6}{B[k]:>6}")
print()
print(f"judge packets total: {len(pids)}; splits total: {len(splits)}; j3 verdicts: {len(j3)}; "
      f"split_ids.json agrees: {split_file == splits}")
print(f"judge_asks files equal recomputed WRONG_CANDIDATE sets: A {A['ja_match']}, B {B['ja_match']}")
print(f"mechanical classes A: {dict(sorted(A['classes'].items()))}")
print(f"mechanical classes B: {dict(sorted(B['classes'].items()))}")
print()
a, b = A["H1a"], B["H1a"]
need = max(4, math.ceil(a / 3))
marks = [
    ("H1a", b <= a - need, f"B {b} <= A {a} - max(4, ceil({a}/3)) = {a - need}"),
    ("H1b", B["H1b"] >= A["H1b"] - 3, f"B {B['H1b']} >= A {A['H1b']} - 3 = {A['H1b'] - 3}"),
    ("H1c", B["H1c"] >= A["H1c"] - 2, f"B {B['H1c']} >= A {A['H1c']} - 2 = {A['H1c'] - 2}"),
    ("H1d", B["H1d"] <= A["H1d"], f"B {B['H1d']} <= A {A['H1d']}"),
]
for name, ok, txt in marks:
    print(f"{name}: {'pass' if ok else 'FAIL'}  ({txt})")
inconclusive = a < 8
proved_wrong = not (b < a)
print(f"INCONCLUSIVE check (A judged-wrong edit asks < 8): {'yes' if inconclusive else 'no'} (A = {a})")
print(f"Proved-wrong check (B judged-wrong edit asks not below A): {'yes' if proved_wrong else 'no'} (B {b} vs A {a})")
if inconclusive:
    verdict = "INCONCLUSIVE"
elif all(ok for _, ok, _ in marks):
    verdict = "PASS"
elif proved_wrong:
    verdict = "FAIL - proved wrong (trained doubt carries over to corrections)"
else:
    verdict = "FAIL"
print(f"VERDICT: {verdict}")
