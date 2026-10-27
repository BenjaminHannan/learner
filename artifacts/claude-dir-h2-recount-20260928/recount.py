"""Blind recount of dir-h2-a. Usage: python3 recount.py <runs_dir>. Reads only tests/extra/poison/train_log/train_summary."""
import json, sys, os
R = sys.argv[1]
nets = ["loop-s13", "loop-s14", "plain-s13", "plain-s14"]
def J(p): return json.load(open(p))
out = {}
for n in nets:
    d = os.path.join(R, n)
    t = J(f"{d}/tests.json")["tests"]; e = J(f"{d}/extra.json"); p = J(f"{d}/poison.json"); s = J(f"{d}/train_summary.json")
    log = [json.loads(l) for l in open(f"{d}/train_log.jsonl") if l.strip()]
    last3 = [l["exact_by_kind"]["numbers4"] for l in log[-3:]]
    lg = open(f"{d}/{n}.log").read().splitlines()
    pool = [l for l in lg if l.startswith("h2 pool:")]
    out[n] = dict(
        numbers4=t["numbers4"]["right"], numbers5=t["numbers5"]["right"],
        sums4=t["sums4"]["right"], grids5=t["grids5"]["right"],
        sums6=t.get("sums6", {}).get("right"), grids6=t.get("grids6", {}).get("right"),
        practice_exact_last3=last3, practice_exact_mean=round(sum(last3)/3, 4),
        P_other=e["P_other"]["right"], P_train24=e["P_train24"]["right"],
        V0_steps_block_nograd=s["steps_block_nograd"], V1_identical=p["V1_identical"],
        V2_pool_line=pool[0] if pool else None, log_lines=len(log), last_step=log[-1]["step"])
    print(n, json.dumps(out[n]))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "recount.json"), "w"), indent=1)
