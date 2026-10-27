# counts only: blind labels split by whether the calendar read the date (report-only)
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
S = Path(sys.argv[1]); W = S / "bm398c/judge/work"
k = json.loads((W / "key.json").read_text())
lab = {}
for f in W.glob("labels/L*.jsonl"):
    for l in f.read_text().splitlines():
        r = json.loads(l); lab[r["item"]] = r["label"]
by = defaultdict(dict)
for i, l in lab.items():
    by[k["items"][i]["qid"]][k["items"][i]["arm"]] = l
read = {r["qid"]: r["tool"]["date_read"] for r in map(json.loads, (S / "bm398c/run/locomo_GC.jsonl").read_text().splitlines())}
out = {}
for part, keep in (("date read (26)", True), ("date not read (32)", False)):
    qs = [q for q in k["qids"] if read[q] == keep]
    out[part] = {arm: dict(sorted(Counter(by[q][arm] for q in qs).items())) for arm in ("G", "GC", "Q2")}
print(json.dumps(out, indent=1))
