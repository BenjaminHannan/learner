# counts only: on the 26 read rows, what kind of answer the calendar gave, and whether the WHEN words were "same day"
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, "scripts")
import claude_bm398c_clock as C
S = Path(sys.argv[1]); W = S / "bm398c/judge/work"
k = json.loads((W / "key.json").read_text())
lab = {}
for f in W.glob("labels/L*.jsonl"):
    for l in f.read_text().splitlines():
        r = json.loads(l); lab[r["item"]] = r["label"]
by = defaultdict(dict)
for i, l in lab.items():
    by[k["items"][i]["qid"]][k["items"][i]["arm"]] = l
c = Counter()
for r in map(json.loads, (S / "bm398c/run/locomo_GC.jsonl").read_text().splitlines()):
    if not r["tool"]["date_read"]:
        continue
    date, when = C.translation(r["translation"])
    ans = r["reply"]
    if when.lower().strip(" .") in ("same day", "none", ""):
        kind = "WHEN = same day / empty"
    elif "said on" in ans:
        kind = "phrase not known -> kept with anchor"
    elif re.fullmatch(r"\d{1,2} [A-Z][a-z]+ \d{4}", ans):
        kind = "exact day computed"
    else:
        kind = "week/weekend/month/year computed"
    c[(kind, by[r["qid"]]["GC"])] += 1
tab = defaultdict(dict)
for (kind, l), n in c.items():
    tab[kind][l] = n
print(json.dumps({k: dict(sorted(v.items())) for k, v in tab.items()}, indent=1))
