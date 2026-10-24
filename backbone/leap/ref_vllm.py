"""Leap-1 reference: EVAL first-try greedy (and optional c16 checked search) for big models with vLLM.

  python backbone/leap/ref_vllm.py --model Qwen/Qwen3.6-35B-A3B --out out/leap_refs [--c16] [--tp 1]
Same prompt (SYS + puzzle via chat template, enable_thinking=False), same parse/judge as leap1. Writes result_ref_<name>.json
and eval_ref_<name>_r0.jsonl (+ evalc16_...). leap1 imports torch (vLLM box has it); no model code from leap1 is used.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from leap1 import SYS, build_eval, by_depth, is_correct, judge, parse_program, summarize, summarize_c16  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--eval-n", type=int, default=100)
    ap.add_argument("--max-new", type=int, default=64)
    ap.add_argument("--c16", action="store_true")
    ap.add_argument("--tp", type=int, default=1)
    ap.add_argument("--max-len", type=int, default=2048)
    a = ap.parse_args()
    from vllm import LLM, SamplingParams
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    name = a.model.split("/")[-1]
    ev = build_eval(a.eval_n)
    llm = LLM(a.model, tensor_parallel_size=a.tp, max_model_len=a.max_len, dtype="bfloat16", trust_remote_code=True, gpu_memory_utilization=0.9,
              limit_mm_per_prompt={"image": 0, "video": 0}, max_num_seqs=256, enable_prefix_caching=True)
    tok = llm.get_tokenizer()
    prompts = [tok.apply_chat_template([{"role": "system", "content": SYS}, {"role": "user", "content": r["prompt"]}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False) for r in ev]
    g = llm.generate(prompts, SamplingParams(temperature=0.0, max_tokens=a.max_new))
    recs = []
    for r, o in zip(ev, g):
        src = parse_program(o.outputs[0].text)
        f, ans = judge(src, r["prompt"])
        recs.append({"id": r["id"], "depth": r["depth"], "program": src, "fits_examples": f, "answer": ans, "correct": is_correct(r, ans)})
    (out / f"eval_ref_{name}_r0.jsonl").write_text("".join(json.dumps(x) + "\n" for x in recs))
    res = {"arm": "ref", "model": a.model, "engine": "vllm", "eval": summarize(recs)}
    print(f"[round] ref {name} mean {res['eval']['mean']:.3f} " + " ".join(f"{v:.2f}" for v in res["eval"]["by_depth"].values()), flush=True)
    if a.c16:
        g = llm.generate(prompts, SamplingParams(temperature=0.8, top_p=0.95, max_tokens=a.max_new, n=16))
        cr = []
        for r, o in zip(ev, g):
            chosen, ans, nv = None, None, 0
            for c in o.outputs:
                src = parse_program(c.text)
                f, v = judge(src, r["prompt"])
                if f and v is not None:
                    nv += 1
                    if chosen is None:
                        chosen, ans = src, v
            cr.append({"id": r["id"], "depth": r["depth"], "program": chosen, "answered": ans is not None, "answer": ans,
                       "correct": is_correct(r, ans), "n_verified": nv})
        (out / f"evalc16_ref_{name}_r0.jsonl").write_text("".join(json.dumps(x) + "\n" for x in cr))
        res["c16"] = summarize_c16(cr)
        print(f"[round] ref {name} c16 mean {res['c16']['mean']:.3f} answered {res['c16']['answered_rate']:.3f}", flush=True)
    res["wall_seconds"] = time.time() - t0
    (out / f"result_ref_{name}.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
