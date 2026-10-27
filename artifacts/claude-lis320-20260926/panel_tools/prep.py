# readpanel320: blind rows (no key) for the second labeller; prints counts only
import json, sys
d = sys.argv[1] + "/"
K = [json.loads(l) for l in open(d + "panel.jsonl")]
open(d + "blind_rows.jsonl", "w").write("".join(json.dumps({k: r[k] for k in ("id", "dialog", "t", "prev_reply", "turn")},
                                                           ensure_ascii=False) + "\n" for r in K))
print(json.dumps({"blind_rows": len(K)}))
