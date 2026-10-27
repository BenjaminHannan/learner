"""Exp 243: tally grid.jsonl -> decline counts by factor (answer stored only)."""
import collections
import json
import sys

rows = [json.loads(l) for l in open(sys.argv[1])]
st = [r for r in rows if r["answer_stored"]]
print(f"questions={len(rows)} answer_stored={len(st)} "
      f"declined={sum(r['bad_decline'] for r in st)} "
      f"other_wrong={sum(r['bad_other'] for r in st)}")


def tab(key, sub=st):
    c = collections.defaultdict(lambda: [0, 0])
    for r in sub:
        k = key(r)
        c[k][0] += r["bad_decline"]; c[k][1] += 1
    for k in sorted(c, key=str):
        print(f"  {str(k):55s} {c[k][0]:4d} / {c[k][1]:4d}")


for name, key in [("form", lambda r: r["form"]),
                  ("family x n", lambda r: (r["family"], r["n"])),
                  ("ask_case", lambda r: r["ask_case"]),
                  ("teach_case", lambda r: r["teach_case"]),
                  ("name_kind", lambda r: r["name_kind"])]:
    print(f"\n== declines / stored by {name}")
    tab(key)
print("\n== form x family x n (star/chain, ask_case=title, teach=title)")
tab(lambda r: (r["form"], r["family"], r["n"], r["name_kind"]),
    [r for r in st if r["ask_case"] in ("title", "-")
     and r["teach_case"] in ("title", "-")])
print("\n== form x ask_case x teach_case (star n=1 for city/boss... n>=rel)")
tab(lambda r: (r["form"], r["ask_case"], r["teach_case"], r["name_kind"]),
    [r for r in st if r["family"] == "star" and r["n"] == 3])
