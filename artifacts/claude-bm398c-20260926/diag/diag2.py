# counts only: shape of the 32 translations with no DATE line
import json, re, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "scripts")
import claude_bm398c_clock as C
S = Path(sys.argv[1])
MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
c = Counter()
for r in map(json.loads, (S / "bm398c/run/locomo_GC.jsonl").read_text().splitlines()):
    if r["tool"]["date_read"]:
        continue
    t = r["translation"]
    c["has 'date' anywhere (any case)"] += bool(re.search(r"date", t, re.I))
    c["has 'DATE:' anywhere"] += "DATE:" in t.upper()
    c["has 'WHEN:' anywhere"] += "WHEN:" in t.upper()
    c["has a 4-digit year anywhere"] += bool(re.search(r"\b\d{4}\b", t))
    c["has a month name anywhere"] += bool(re.search(r"\b" + MON + r"\b", t, re.I))
    c["has D Month YYYY anywhere (parser would read)"] += C.parse_anchor(t) is not None
    c["empty reply"] += not t.strip()
    c[f"lines={min(len([l for l in t.splitlines() if l.strip()]), 4)}"] += 1
print(json.dumps(dict(sorted(c.items())), indent=1))
