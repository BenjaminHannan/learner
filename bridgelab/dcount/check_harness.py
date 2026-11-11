"""Q1: replicate the real harness (dmsg.load_d + dmsg.extract: no Bridge attached) on dev count items and compare per-question with (a) our bridge-off run
and (b) the official-scorer run with the Bridge.  Also: does dmsg.load_d's model have bridge_in set?"""
import json, random
from cap import *
from bridgelab.real import data as D, dmsg
tok, splits = D.open_village(ROOT, str(TOK), splits=("dev",), workers=2)
it = splits["dev"]
rowsd = {b: {r["id"]: r for r in json.load(open(Path(__file__).parent / f"official_dev_{b}_1000.json"))["rows"]} for b in ("on", "off")}
idx = [i for i in range(len(it)) if it.qid[i] in rowsd["on"]]
print("dev count items inside the 1000-visit official subset:", len(idx))
sub = it.take(idx)
m = dmsg.load_d("/tmp/claude-0/w/D-final.pt", "cpu", tok.vocab_size)
print("harness D bridge_in:", m.bridge_in)
out = dmsg.extract(m, sub, tok, "cpu")
res = dict(n=len(sub), harness_pred_hist={}, agree_with_bridge_off=0, agree_with_bridge_on=0, harness_acc=float(out["d_correct"].float().mean()))
import collections
res["harness_pred_hist"] = dict(collections.Counter(out["d_text"]))
for i, qid in enumerate(sub.qid):
    res["agree_with_bridge_off"] += out["d_text"][i] == rowsd["off"][qid]["pred"]
    res["agree_with_bridge_on"] += out["d_text"][i] == rowsd["on"][qid]["pred"]
res["official_bridge_on_acc_same_items"] = sum(rowsd["on"][q]["ok"] for q in sub.qid) / len(sub)
res["official_bridge_off_acc_same_items"] = sum(rowsd["off"][q]["ok"] for q in sub.qid) / len(sub)
json.dump(res, open(Path(__file__).parent / "check_harness.json", "w"), indent=1); print(json.dumps(res, indent=1))
