"""Q1+Q4(part): the OFFICIAL scorer path (premonition.train.validate / judge, v1.run.make_eval_batches style) on a visit subset of village dev,
broken down by qtype / bank, with the v1 Bridge attached (frozen_ctx) and, for comparison, bridge off (the harness-style D).
Also records per-question predictions and D's top-5 first-token candidates on count questions.
  python run_official.py --visits 300 --bridge on|off"""
import argparse, json, random, time, collections
from cap import *

ap = argparse.ArgumentParser()
ap.add_argument("--visits", type=int, default=300)
ap.add_argument("--bridge", default="on")
ap.add_argument("--split", default="dev")
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--out", default=None)
a = ap.parse_args()
T0 = time.time()
from pathlib import Path
from v1 import dtrain
from v1.run import MAX_TOKENS, MAX_VISITS
from premonition import data as pdata, preprocess
from premonition.train import judge, validate
from learnlab import step1

data = dtrain.open_data(ROOT, TOK, workers=2, log=lambda s: None)
tok = data.tokenizer
cache = getattr(data, a.split)
info = question_info(a.split)
stops = sorted(step1.stop_ids(tok)[0])
idx = list(range(len(cache)))
random.Random(a.seed).shuffle(idx)
chosen = sorted(idx[:a.visits])
groups = pdata.length_batches(cache.lengths[chosen].tolist(), MAX_TOKENS, max_visits=MAX_VISITS)
batches = [pdata.collate(cache, [chosen[i] for i in g]) for g in groups]
d, bridge = load(a.bridge == "on")
num_ids = [tok.token_to_id(" " + w) for w in NUM]
print("num ids", num_ids, "batches", len(batches), flush=True)

rows = []
with torch.no_grad():
    # (1) the official validate() itself, as v1 final_eval calls it
    off = validate(d, batches, tokenizer=tok, stop=stops, gold_cards=False)
    print("official validate acc", off["accuracy"], "n", off["questions"], round(time.time() - T0), flush=True)
    # (2) same answers, per question, through judge()
    for b in batches:
        with capture(d, num_ids) as box:
            ans = d.answer(b, stop=stops)
        correct, texts = judge(ans, b, tokenizer=tok, stop=stops, eos=d.config.eos_id)
        t5v, t5i = box["top5"]
        for q, qid in enumerate(b.question_ids):
            r = info[qid]
            row = dict(id=qid, qtype=r["qtype"], base_qtype=r["base_qtype"], bank=r["bank"], knowable=r["knowable"], gold=r["answer"],
                       pred=texts[q], ok=bool(correct[q]), loops=int(ans.loops[q]), halt=float(ans.halt_prob[q]), ncards=int(box["ncards"][q]),
                       n_evidence=len(r["evidence"]), depth=r["depth"])
            if r["bank"] in ("q.count_at", "q.count_held"):
                row["top5"] = [tok.id_to_token(int(i)) if int(i) < tok.vocab_size else "ENT" for i in t5i[q]]
                row["num_logits"] = [round(float(x), 2) for x in box["num_logits"][q]]
            # gold evidence lines fetched?
            gl = [int(x) for x in b.gold_lines[q] if int(x) >= 0]
            if gl:
                row["gold_total"] = len(gl)
                row["gold_fetched"] = int(sum(bool(ans.fetched[q, g]) for g in gl))
            rows.append(row)
        print("batch", len(rows), round(time.time() - T0), flush=True)

def acc(rs):
    return (round(sum(r["ok"] for r in rs) / len(rs), 4), len(rs)) if rs else None
by_q = collections.defaultdict(list); by_bank = collections.defaultdict(list)
for r in rows:
    by_q[r["qtype"]].append(r); by_bank[(r["qtype"], r["bank"])].append(r)
summary = dict(bridge=a.bridge, visits=a.visits, split=a.split, n_questions=len(rows),
               official_validate_acc=off["accuracy"], own_loop_acc=acc(rows),
               by_qtype={k: acc(v) for k, v in sorted(by_q.items(), key=lambda x: int(x[0][1:]))},
               q5_by_bank={b: acc(v) for (qt, b), v in by_bank.items() if qt == "Q5"},
               q5_pred_hist=dict(collections.Counter(r["pred"] for r in by_q["Q5"])),
               q5_gold_hist=dict(collections.Counter(r["gold"] for r in by_q["Q5"])),
               q5_confusion={g: dict(collections.Counter(r["pred"] for r in by_q["Q5"] if r["gold"] == g)) for g in NUM},
               q5_majority_baseline=round(max(collections.Counter(r["gold"] for r in by_q["Q5"]).values()) / max(len(by_q["Q5"]), 1), 4) if by_q["Q5"] else None,
               q5_top5_contains_gold=round(sum(("▁" + r["gold"]) in [t for t in r["top5"]] or (" " + r["gold"]) in r["top5"] for r in by_q["Q5"]) / max(len(by_q["Q5"]), 1), 4),
               q5_gold_recall=round(sum(r.get("gold_fetched", 0) for r in by_q["Q5"]) / max(sum(r.get("gold_total", 0) for r in by_q["Q5"]), 1), 4),
               q5_all_gold_fetched=round(sum(r.get("gold_fetched", -1) == r.get("gold_total", -2) for r in by_q["Q5"]) / max(len(by_q["Q5"]), 1), 4),
               q5_loops_mean=round(sum(r["loops"] for r in by_q["Q5"]) / max(len(by_q["Q5"]), 1), 3),
               other_loops_mean=round(sum(r["loops"] for r in rows if r["qtype"] != "Q5") / max(len([r for r in rows if r["qtype"] != "Q5"]), 1), 3),
               seconds=round(time.time() - T0))
out = a.out or f"official_{a.split}_{a.bridge}_{a.visits}.json"
json.dump(dict(summary=summary, rows=rows), open(Path(__file__).parent / out, "w"))
print(json.dumps(summary, indent=1))
