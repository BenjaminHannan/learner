"""raw-vs-converted fidelity and option-order independence.  python3 analyze7.py -> agg7.json"""
import json, os, sys, collections as C, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib
B = "/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/"
FILES = ["logic_gate", "logic_dev", "logic_test_sampler", "logic_test_deeper", "placebo_dev", "placebo_test_wording", "logic_train", "placebo_train"]
out = {}
for n in FILES:
    cp = B + (f"eval/{n}.jsonl" if "train" not in n else f"{n}.jsonl")
    rp = B + f"raw/{n}.jsonl"
    N = ok_prompt = ok_ans = ok_prog = ok_depth = 0
    pos = C.Counter()
    for a, b in zip(open(cp), open(rp)):
        c = json.loads(a); r = json.loads(b); N += 1
        body, opts = rlib.split_options(c["prompt"])
        ok_prompt += body == r["question"]
        ok_ans += c["answer"] == r["answer"] == r["label"]
        ok_prog += c["meta"]["program"] == r["program"]
        ok_depth += c["level"] == (r["depth"] if r["depth"] is not None else 0)
        pos[(c["answer"], opts.index(c["answer"]))] += 1
    # chi-square of gold-position vs gold label
    tab = {(l, k): pos[(l, k)] for l in ("true", "false", "unknown") for k in range(3)}
    tot = sum(tab.values()); rows = {l: sum(tab[(l, k)] for k in range(3)) for l in ("true", "false", "unknown")}
    cols = {k: sum(tab[(l, k)] for l in rows) for k in range(3)}
    chi = sum((tab[(l, k)] - rows[l] * cols[k] / tot) ** 2 / (rows[l] * cols[k] / tot) for l in rows for k in range(3))
    out[n] = dict(N=N, prompt_body_eq_raw_question=ok_prompt, answer_eq_raw_answer_label=ok_ans, program_eq=ok_prog, level_eq_depth_or0=ok_depth,
                  gold_position_in_options={f"{l}:{k}": tab[(l, k)] for l in rows for k in range(3)}, chi2_df4=round(chi, 2))
    print(n, json.dumps(out[n]))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agg7.json"), "w"), indent=1)
