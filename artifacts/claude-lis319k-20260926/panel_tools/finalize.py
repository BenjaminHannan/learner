# apply adjudication to the writer key for readpanel319k; prints counts only
import json, re, sys
d = sys.argv[1] + "/"
K = [json.loads(l) for l in open(d + "panel.jsonl")]
R = {r["id"]: r for r in map(json.loads, open(d + "resolved.jsonl"))}
disp = [json.loads(l)["id"] for l in open(d + "disputes.jsonl")]
assert set(R) == set(disp), ("resolved ids differ", len(R), len(disp))
last_t = {}
for r in K:
    last_t[r["dialog"]] = max(last_t.get(r["dialog"], -1), r["t"])
out, c = [], {"rows_in": len(K), "resolved": len(R), "dropped_last_turn": 0, "dropped_mid_kept_empty": 0,
              "value_not_verbatim_removed": 0}
def verb(v, turn, prev):
    pat = r"(?<![A-Za-z0-9])" + re.escape(str(v).strip()) + r"(?![A-Za-z0-9])"
    return re.search(pat, turn, re.I) or re.search(pat, prev or "", re.I)
for r in K:
    r = dict(r)
    if r["id"] in R:
        x = R[r["id"]]
        if x.get("drop"):
            if r["t"] == last_t[r["dialog"]]:
                c["dropped_last_turn"] += 1
                continue
            c["dropped_mid_kept_empty"] += 1
            r["facts"], r["replaced"], r["adjudicated_drop"] = [], [], True
        else:
            r["facts"] = x.get("facts") or []
            r["replaced"] = x.get("replaced") or []
    keep = []
    for f in r.get("facts") or []:
        if verb(f.get("value", ""), r["turn"], r.get("prev_reply", "")):
            keep.append(f)
        else:
            c["value_not_verbatim_removed"] += 1
    r["facts"] = keep
    out.append(r)
kinds = {}
for r in out:
    kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
c |= {"rows_out": len(out), "kinds": kinds, "facts": sum(len(r["facts"]) for r in out),
      "needs_history": sum(bool(f.get("needs_history")) for r in out for f in r["facts"]),
      "correction_facts": sum(bool(f.get("correction")) for r in out for f in r["facts"]),
      "replaced_items": sum(len(r.get("replaced") or []) for r in out),
      "nofact_rows": sum(not r["facts"] for r in out)}
open(d + "panel_final.jsonl", "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
print(json.dumps(c))
