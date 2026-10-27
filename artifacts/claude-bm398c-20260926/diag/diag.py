# counts only: why the calendar could not read the date on some GC rows (report-only, after the sealed run)
import json, re, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "scripts")
import claude_bm398c_clock as C
import claude_bm398d_evidence as D
S = Path(sys.argv[1])
qs, info = C.items58(S / "data390")
rows = {r["qid"]: r for r in map(json.loads, (S / "bm398c/run/locomo_GC.jsonl").read_text().splitlines())}
MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
c = Counter()
for q in qs:
    conv, i, qa, gold = info[q]
    items = D.items_of(conv)
    ev_dates = {C.parse_anchor(items[p][1]) for p in gold}
    r = rows[q]
    t = r["translation"]
    date, when = C.translation(t)
    read = r["tool"]["date_read"]
    c["read" if read else "unread"] += 1
    if read:
        c["read: date equals an evidence session date"] += C.parse_anchor(date) in ev_dates
        continue
    c["unread: no DATE line"] += not any(l.strip().strip("*").strip().upper().startswith("DATE:") for l in t.splitlines())
    c["unread: DATE line empty"] += (date == "") and any(l.strip().strip("*").strip().upper().startswith("DATE:") for l in t.splitlines())
    c["unread: date has a 4-digit year"] += bool(re.search(r"\b\d{4}\b", date))
    c["unread: date has a month name"] += bool(re.search(MON, date, re.I))
    us = re.search(MON + r"\.?\s+(\d{1,2}),?\s+(\d{4})", date, re.I)
    c["unread: US order 'Month D, YYYY'"] += bool(us)
    c["unread: month + day but no year"] += bool(re.search(r"\d", date)) and bool(re.search(MON, date, re.I)) and not re.search(r"\b\d{4}\b", date)
    c["unread: date has no digit at all"] += not re.search(r"\d", date)
    c["unread: date line looks like a time only (am/pm)"] += bool(re.search(r"\b(am|pm)\b", date, re.I)) and not re.search(MON, date, re.I)
    c["unread: reply hit 40 tokens (cut)"] += 0
print(json.dumps(dict(c), indent=1))
