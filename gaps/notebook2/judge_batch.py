# Judge stage-1 rows with the Anthropic Message Batches API (Notebook-1 judge prompts). See HOWTO.md.
# usage: python judge_batch.py [--out-dir stage1_out] [--dry-run]
import json, os, sys, glob, time, argparse
D = os.path.dirname(os.path.abspath(__file__))
SONNET, CAP = "claude-sonnet-5-5", 3000
JP = {  # Notebook-1 verbatim
 "default": "Answer yes if the response contains the correct answer (a response that is a subset of the needed info, or lacks required info, is no). Equivalent answers count.",
 "temporal-reasoning": "Answer yes if the response contains the correct answer. Do not penalize off-by-one errors in counts of days, weeks, or months. Equivalent answers count.",
 "knowledge-update": "Answer yes if the response contains the correct (updated) answer. If the response also mentions earlier outdated info but clearly gives the updated answer, it is correct.",
 "single-session-preference": "The reference is a rubric describing the user's preferences. Answer yes if the response recalls and uses the user's personal information correctly as the rubric describes (it need not hit every point).",
}
def judge_prompt(q, pred):
    if q["question_id"].endswith("_abs"):
        inst = ("The question is unanswerable. Answer yes only if the model response correctly says it cannot answer / does not know / "
                "the information is not available (and does not fabricate an answer). The reference explanation: ")
    else: inst = JP.get(q["question_type"], JP["default"]) + " Reference: "
    return f"{inst}{q['answer']}\n\nQuestion: {q['question']}\nModel response: {pred}\n\nIs the model response correct? Answer only yes or no."

def key(r): return (r["reader"], r["question_id"], r["arm"])

def table(rows):
    from scipy.stats import binomtest
    for reader in sorted({r["reader"] for r in rows}):
        rs = [r for r in rows if r["reader"] == reader]; arms = sorted({r["arm"] for r in rs}, key=lambda x: ["R", "Hy", "Q", "T", "O"].index(x) if x in "R Hy Q T O".split() else 9)
        types = sorted({r["type"] for r in rs}); acc = {}
        print(f"\n== reader {reader} ==\narm   n   all   " + "  ".join(t[:14].ljust(14) for t in types))
        for arm in arms:
            ar = [r for r in rs if r["arm"] == arm]; acc[arm] = {r["question_id"]: r["correct"] for r in ar}
            cells = []
            for t in types:
                x = [r["correct"] for r in ar if r["type"] == t]; cells.append((f"{100*sum(x)/len(x):.0f} ({len(x)})" if x else "-").ljust(14))
            print(f"{arm:<4} {len(ar):>3}  {100*sum(r['correct'] for r in ar)/len(ar):5.1f}  " + "  ".join(cells))
        if "R" in acc:
            print("paired vs R (win = arm right, R wrong):")
            for arm in arms:
                if arm == "R": continue
                ids = acc[arm].keys() & acc["R"].keys()
                w = sum(acc[arm][i] and not acc["R"][i] for i in ids); l = sum(acc["R"][i] and not acc[arm][i] for i in ids)
                p = binomtest(w, w + l, 0.5).pvalue if w + l else 1.0
                print(f"  {arm:<3} n={len(ids)} win {w} loss {l} diff {100*(w-l)/max(len(ids),1):+.1f} pts  McNemar exact p={p:.4f}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(D, "stage1_out")); ap.add_argument("--data", default=os.path.join(D, "data", "lme120.json"))
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--poll", type=int, default=60)
    a = ap.parse_args()
    byid = {x["question_id"]: x for x in json.load(open(a.data))}
    jp = os.path.join(a.out_dir, "judged.jsonl")
    judged = {key(r): r for r in map(json.loads, open(jp))} if os.path.exists(jp) else {}
    rows = [json.loads(l) for f in sorted(glob.glob(os.path.join(a.out_dir, "rows_*.jsonl"))) for l in open(f)]
    todo = [r for r in rows if key(r) not in judged]
    print(f"{len(rows)} rows, {len(judged)} already judged, {len(todo)} to judge")
    if len(todo) > CAP: sys.exit(f"refusing: {len(todo)} requests > cap {CAP}")
    reqs = [dict(custom_id=f"j{i}", params=dict(model=SONNET, max_tokens=1000, output_config={"effort": "low"},
                 messages=[{"role": "user", "content": judge_prompt(byid[r["question_id"]], r["pred"])}])) for i, r in enumerate(todo)]
    if a.dry_run:
        if reqs: print("example request:", json.dumps(reqs[0])[:700])
        print("dry run: nothing sent"); table([dict(r, correct=bool(len(r["pred"]) % 2)) for r in rows]) if rows else None; return
    if todo:
        import anthropic
        cli = anthropic.Anthropic(api_key=os.environ["LEARNER_ANTHROPIC_API_KEY"], max_retries=5)
        sp = os.path.join(a.out_dir, "batch_state.json")
        if os.path.exists(sp): st = json.load(open(sp)); bid = st["batch_id"]; print("resuming batch", bid)
        else:
            bid = cli.messages.batches.create(requests=reqs).id
            json.dump(dict(batch_id=bid, keys=[list(key(r)) for r in todo]), open(sp, "w")); print("submitted", bid)
        keys = [tuple(k) for k in json.load(open(sp))["keys"]]; rmap = {key(r): r for r in rows}
        while True:
            b = cli.messages.batches.retrieve(bid); print(time.strftime("%H:%M:%S"), b.processing_status, b.request_counts, flush=True)
            if b.processing_status == "ended": break
            time.sleep(a.poll)
        bad = 0
        with open(jp, "a") as f:
            for res in cli.messages.batches.results(bid):
                k = keys[int(res.custom_id[1:])]
                if res.result.type != "succeeded": bad += 1; continue
                m = res.result.message
                txt = "".join(c.text for c in m.content if c.type == "text").strip().lower()
                r = dict(rmap[k], correct=(m.stop_reason != "refusal" and txt.startswith("yes")), judge_raw=txt[:40])
                judged[k] = r; f.write(json.dumps(r) + "\n")
        os.remove(sp); print("failed requests (rerun to retry):", bad)
    table(list(judged.values()))

if __name__ == "__main__": main()
