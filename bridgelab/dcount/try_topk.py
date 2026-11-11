"""Inference-only sensitivity (NO training): does fetching more cards per ASK / more loops move Q5 accuracy?  D weights unchanged, bridge on."""
import json, collections
from cap import *
from bridgelab.real import data as D, dmsg
from learnlab import step1
from premonition import preprocess
tok, splits = D.open_village(ROOT, str(TOK), splits=("dev",), workers=2)
it = splits["dev"]
rows = {r["id"]: r for r in json.load(open(Path(__file__).parent / "official_dev_on_1000.json"))["rows"]}
sub = it.take([i for i in range(len(it)) if it.qid[i] in rows])
d, bridge = load(True)
stops = sorted(step1.stop_ids(tok)[0])
res = {}
for tk, ml in ((4, 8), (6, 8), (8, 8), (4, 4)):
    object.__setattr__(d.config, "top_k", tk); object.__setattr__(d.config, "max_loops", ml)
    ok = 0; loops = 0; gold_f = gold_t = 0; hist = collections.Counter(); byc = collections.defaultdict(lambda: [0, 0])
    with torch.no_grad():
        for order, batch in dmsg.item_batches(sub, None, 55000, 48):
            ans = d.answer(batch, stop=stops)
            for k, i in enumerate(order):
                v = int(batch.q_visit[k])
                p = preprocess.prediction_text(ans.ids()[k], batch.names[v], tok)[0]
                c = int(sub.c[i]); hit = D.word_to_int(p) == c
                ok += hit; loops += int(ans.loops[k]); byc[c][0] += hit; byc[c][1] += 1
                gl = [int(x) for x in batch.gold_lines[k] if int(x) >= 0]
                gold_t += len(gl); gold_f += sum(bool(ans.fetched[k, g]) for g in gl)
    res[f"top_k={tk},max_loops={ml}"] = dict(acc=round(ok / len(sub), 4), n=len(sub), gold_recall=round(gold_f / gold_t, 3), loops=round(loops / len(sub), 2),
                                             acc_by_count={c: round(v[0] / v[1], 3) for c, v in sorted(byc.items())})
    print(tk, ml, res[f"top_k={tk},max_loops={ml}"], flush=True)
json.dump(res, open(Path(__file__).parent / "try_topk.json", "w"), indent=1)
