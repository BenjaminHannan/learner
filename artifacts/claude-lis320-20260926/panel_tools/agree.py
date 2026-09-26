# key (A) vs blind labeller (B) agreement for readpanel320 (facts, correction flags, replaced, former); counts + disputes
import json, sys
sys.path.insert(0, "/home/user/learner/scripts")
from claude_lis317_gates import e2e_match
d = sys.argv[1] + "/"
K = {r["id"]: r for r in map(json.loads, open(d + "panel.jsonl"))}
B = {r["id"]: r for r in map(json.loads, open(d + "label_B.jsonl"))}
c = {k: 0 for k in ("rows", "rows_agree", "B_missing_rows", "key_facts", "key_found_by_B", "B_facts", "B_in_key",
                    "key_corr", "key_corr_flag_agree", "key_replaced", "key_replaced_found_by_B", "B_replaced",
                    "B_replaced_in_key", "key_former", "key_former_found_by_B", "B_former", "B_former_in_key")}
disp = []
def both(a, b):
    return sum(any(e2e_match(x, g) for x in b) for g in a), sum(any(e2e_match(x, g) for g in a) for x in b)
for i, k in K.items():
    c["rows"] += 1
    b = B.get(i)
    if b is None:
        c["B_missing_rows"] += 1
        b = {}
    kf, bf = k.get("facts") or [], b.get("facts") or []
    mk = [next((x for x in bf if e2e_match(x, g)), None) for g in kf]
    mb = sum(any(e2e_match(x, g) for g in kf) for x in bf)
    flags = sum(1 for g, x in zip(kf, mk) if x is not None and bool(x.get("correction")) == bool(g.get("correction")))
    c["key_facts"] += len(kf); c["key_found_by_B"] += sum(x is not None for x in mk); c["B_facts"] += len(bf); c["B_in_key"] += mb
    c["key_corr"] += sum(bool(g.get("correction")) for g in kf)
    c["key_corr_flag_agree"] += sum(1 for g, x in zip(kf, mk) if g.get("correction") and x is not None and x.get("correction"))
    ok = all(x is not None for x in mk) and mb == len(bf) and flags == len(kf)
    for f in ("replaced", "former"):
        ka, kb = k.get(f) or [], b.get(f) or []
        x, y = both(ka, kb)
        c[f"key_{f}"] += len(ka); c[f"key_{f}_found_by_B"] += x; c[f"B_{f}"] += len(kb); c[f"B_{f}_in_key"] += y
        ok = ok and x == len(ka) and y == len(kb)
    c["rows_agree"] += ok
    if not ok:
        disp.append({"id": i, "A": {f: k.get(f) or [] for f in ("facts", "replaced", "former")},
                     "B": {f: b.get(f) or [] for f in ("facts", "replaced", "former")}})
open(d + "disputes.jsonl", "w").write("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in disp))
print(json.dumps(c | {"disagree_rows": len(disp)}))
