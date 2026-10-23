"""Post-process official_dev_on_1000.json: Q5 accuracy by true count, by whether all gold evidence cards were fetched, by #evidence lines, gold rank among number words."""
import json, collections
rows = json.load(open("official_dev_on_1000.json"))["rows"]
NUM = "zero one two three four".split()
q5 = [r for r in rows if r["qtype"] == "Q5"]
def acc(rs): return [round(sum(r["ok"] for r in rs) / len(rs), 3), len(rs)] if rs else None
out = {}
out["by_true_count"] = {g: acc([r for r in q5 if r["gold"] == g]) for g in NUM}
out["by_all_gold_fetched"] = {str(k): acc([r for r in q5 if (r.get("gold_fetched", -1) == r.get("gold_total", -2)) == k]) for k in (True, False)}
out["by_gold_fetched_and_count"] = {f"{g}|allfetched={k}": acc([r for r in q5 if r["gold"] == g and (r.get("gold_fetched", -1) == r.get("gold_total", -2)) == k]) for g in NUM[1:] for k in (True, False)}
out["by_n_evidence_lines"] = {str(n): acc([r for r in q5 if min(r["n_evidence"], 8) == n]) for n in range(0, 9)}
out["by_bank_and_true_count"] = {f"{b}|{g}": acc([r for r in q5 if r["bank"] == b and r["gold"] == g]) for b in ("q.count_at", "q.count_held") for g in NUM}
# rank of gold among the 5 number-word logits at first decoding position
rk = collections.Counter()
for r in q5:
    if r["gold"] in NUM:
        order = sorted(range(5), key=lambda i: -r["num_logits"][i])
        rk[order.index(NUM.index(r["gold"])) + 1] += 1
out["gold_rank_among_numbers"] = dict(sorted(rk.items()))
out["n_q5_known"] = sum(rk.values())
out["q5_not_told_preds"] = sum(r["pred"] == "not told" for r in q5)
# off-by-one: abs error
err = collections.Counter(abs(NUM.index(r["pred"]) - NUM.index(r["gold"])) for r in q5 if r["pred"] in NUM)
out["abs_error_hist"] = dict(sorted(err.items()))
# other qtypes for comparison: loops & ncards & all-gold-fetched
for qt in ("Q1", "Q4", "Q13", "Q3"):
    rs = [r for r in rows if r["qtype"] == qt and "gold_total" in r]
    out[f"{qt}_gold_recall"] = round(sum(r["gold_fetched"] for r in rs) / sum(r["gold_total"] for r in rs), 3)
    out[f"{qt}_mean_gold_lines"] = round(sum(r["gold_total"] for r in rs) / len(rs), 2)
rs = q5
out["Q5_mean_gold_lines"] = round(sum(r.get("gold_total", 0) for r in rs) / len(rs), 2)
json.dump(out, open("analysis_rows.json", "w"), indent=1); print(json.dumps(out, indent=1))
