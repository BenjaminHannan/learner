import json, sys
sys.path.insert(0, "/home/user/learner/scripts")
from claude_lis317_gates import e2e_match
d = sys.argv[1]
K = {r["id"]: r for r in map(json.loads, open(d + "/panel.jsonl"))}
B = {r["id"]: r for r in map(json.loads, open(d + "/label_B.jsonl"))}
c = dict(rows=len(K), rows_agree=0, key_facts=0, key_found_by_B=0, B_facts=0, B_in_key=0,
         key_former=0, key_former_found_by_B=0, B_former=0, B_former_in_key=0, B_missing_rows=0)
bad = []
for i, k in K.items():
    b = B.get(i)
    if b is None:
        c["B_missing_rows"] += 1
        b = {}
    ok = True
    for lst, pre in (("facts", "key_facts"), ("former", "key_former")):
        ks, bs = k.get(lst) or [], b.get(lst) or []
        mk = sum(any(e2e_match(x, g) for x in bs) for g in ks)
        mb = sum(any(e2e_match(x, g) for g in ks) for x in bs)
        tag = "" if lst == "facts" else "_former"
        c[pre] += len(ks); c["key%s_found_by_B" % ("" if lst == "facts" else "_former")] += mk
        c["B%s" % ("_facts" if lst == "facts" else "_former")] += len(bs)
        c["B%s_in_key" % ("" if lst == "facts" else "_former")] += mb
        ok = ok and mk == len(ks) and mb == len(bs)
    c["rows_agree"] += ok
    if not ok:
        bad.append(i)
print(json.dumps(c | {"disagree_ids": bad}))
