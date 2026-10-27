# counts only: on rows where the 1B wrote "same day", do the evidence lines hold ordinary time words?
import json, re, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "scripts")
import claude_bm398c_clock as C
import claude_bm390 as B
import claude_bm398d_evidence as D
S = Path(sys.argv[1])
qs, info = C.items58(S / "data390")
TIME = re.compile(r"\b(yesterday|last (night|week|weekend|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
                  r"\w+ (days?|weeks?|months?|years?) ago|next (week|month|year)|this (week|month|morning|weekend)|"
                  r"tomorrow|in (19|20)\d\d|(january|february|march|april|june|july|august|september|october|november|december))\b", re.I)
c = Counter()
for r in map(json.loads, (S / "bm398c/run/locomo_GC.jsonl").read_text().splitlines()):
    conv, i, qa, gold = info[r["qid"]]
    items = D.items_of(conv)
    has = any(TIME.search(B.turn_text(items[p][2])) for p in gold)
    date, when = C.translation(r["translation"])
    same = when.lower().strip(" .") in ("same day", "none", "")
    grp = "read, WHEN=same day" if r["tool"]["date_read"] and same else ("read, WHEN words" if r["tool"]["date_read"] else "unread")
    c[(grp, "evidence has time words" if has else "no time words")] += 1
print(json.dumps({f"{a} | {b}": n for (a, b), n in sorted(c.items())}, indent=1))
