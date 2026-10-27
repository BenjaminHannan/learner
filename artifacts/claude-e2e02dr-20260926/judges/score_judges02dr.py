"""0.2d-r H1/H2 from blind judges: a packet is wrong if judges A and B both say wrong; on a split, judge C decides.
H1 = asks judged wrong per arm (M2). H2 = turns (life, turn) with >= 1 save judged wrong per arm (M1; nosave turns
with writes are 0 for both arms in score/mechanical.json). Prints counts only.
usage: score_judges02dr.py JDIR (keys/, out/judgeA_*.jsonl, out/judgeB_*.jsonl, optional out/judgeC_*.jsonl)"""
import json, sys
from pathlib import Path
J = Path(sys.argv[1])
ld = lambda p: {r["id"]: r["verdict"] for r in (json.loads(x) for x in open(p) if x.strip())} if p.exists() else {}
res = {}
for kind in ("saves", "asks"):
    key = json.load(open(J / "keys" / f"key_{kind}.json"))
    a, b, c = (ld(J / "out" / f"judge{x}_{kind}.jsonl") for x in "ABC")
    assert set(a) == set(key) == set(b), kind
    splits = [i for i in key if a[i] != b[i]]
    missing = [i for i in splits if i not in c]
    wrong = {i for i in key if (a[i] == b[i] == "wrong") or (a[i] != b[i] and c.get(i) == "wrong")}
    per = {}
    for arm in ("X", "G"):
        ids = [i for i in key if key[i]["arm"] == arm]
        if kind == "asks":
            per[arm] = sum(i in wrong for i in ids)
        else:
            per[arm] = len({(key[i]["life_id"], key[i]["turn_index"]) for i in ids if i in wrong})
    res[kind] = {"agree": len(key) - len(splits), "packets": len(key), "splits": len(splits),
                 "splits_unresolved": len(missing), "wrong_by_arm": per}
print(json.dumps(res))
