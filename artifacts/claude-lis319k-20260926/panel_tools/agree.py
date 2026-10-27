# key vs blind labeller agreement for readpanel319k; prints counts and disputed ids only
import json, sys
sys.path.insert(0, "/home/user/learner/scripts")
from claude_lis317_gates import e2e_match
d = sys.argv[1]
K = {r["id"]: r for r in map(json.loads, open(d + "/panel.jsonl"))}
B = {r["id"]: r for r in map(json.loads, open(d + "/label_B.jsonl"))}
c = dict(rows=len(K), rows_agree=0, B_missing_rows=0, key_facts=0, key_found_by_B=0, B_facts=0, B_in_key=0,
         key_corr=0, key_corr_flag_agree=0, key_replaced=0, key_replaced_found_by_B=0, B_replaced=0, B_replaced_in_key=0)
bad = []
for i, k in K.items():
    b = B.get(i)
    if b is None:
        c["B_missing_rows"] += 1
        b = {}
    kf, bf = k.get("facts") or [], b.get("facts") or []
    mk = [next((x for x in bf if e2e_match(x, g)), None) for g in kf]
    mb = sum(any(e2e_match(x, g) for g in kf) for x in bf)
    flags = sum(1 for g, x in zip(kf, mk) if x is not None and bool(x.get("correction")) == bool(g.get("correction")))
    c["key_facts"] += len(kf); c["key_found_by_B"] += sum(x is not None for x in mk)
    c["B_facts"] += len(bf); c["B_in_key"] += mb
    c["key_corr"] += sum(bool(g.get("correction")) for g in kf)
    c["key_corr_flag_agree"] += sum(1 for g, x in zip(kf, mk) if g.get("correction") and x is not None and x.get("correction"))
    kr, br = k.get("replaced") or [], b.get("replaced") or []
    rk = sum(any(e2e_match(x, g) for x in br) for g in kr)
    rb = sum(any(e2e_match(x, g) for g in kr) for x in br)
    c["key_replaced"] += len(kr); c["key_replaced_found_by_B"] += rk; c["B_replaced"] += len(br); c["B_replaced_in_key"] += rb
    ok = all(x is not None for x in mk) and mb == len(bf) and flags == len(kf) and rk == len(kr) and rb == len(br)
    c["rows_agree"] += ok
    if not ok:
        bad.append(i)
json.dump(bad, open(d + "/dispute_ids.json", "w"))
print(json.dumps(c | {"disagree_rows": len(bad)}))
