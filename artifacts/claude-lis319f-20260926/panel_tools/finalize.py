# apply adjudication to the writer key; prints counts only
import json, re, sys
d = "/tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp371c/"
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
            r["facts"], r["former"], r["nosave_reason"], r["adjudicated_drop"] = [], [], "dropped_ambiguous", True
        else:
            r["facts"] = x.get("facts") or []
            r["former"] = x.get("former") or []
            r["nosave_reason"] = x.get("nosave_reason")
    for lst in ("facts", "former"):
        keep = []
        for f in r.get(lst) or []:
            if verb(f.get("value", ""), r["turn"], r.get("prev_reply", "")):
                keep.append(f)
            else:
                c["value_not_verbatim_removed"] += 1
        r[lst] = keep
    out.append(r)
c |= {"rows_out": len(out), "facts": sum(len(r["facts"]) for r in out),
      "needs_history": sum(bool(f.get("needs_history")) for r in out for f in r["facts"]),
      "former_rows": sum(bool(r["former"]) for r in out), "former_items": sum(len(r["former"]) for r in out),
      "nofact_rows": sum(not r["facts"] for r in out)}
open(d + "panel_final.jsonl", "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
print(json.dumps(c))
