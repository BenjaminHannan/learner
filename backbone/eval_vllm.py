"""Untrained few-shot reference for a large model (e.g. Qwen/Qwen3.8-27B) with vLLM, same rows, prompt format and
scorer as train.py's arm a0. Plain text completion (no chat template), so the model's thinking mode is not used.

  python3 backbone/eval_vllm.py --model Qwen/Qwen3.8-27B --data out/data --out out/big --max-len 4096 [--dev-n 1000]
"""
from __future__ import annotations

import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train import Encoder, few_shot_prefix, normalise, read_jsonl  # noqa: E402

INSTRUCTION = ("Below are logs of visits to a village. After each log comes a question; answer it briefly in the "
               "same style as the examples. Answer 'not told' if the log does not say.\n\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.8-27B")
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-len", type=int, default=4096)
    ap.add_argument("--dev-n", type=int, default=1000)
    ap.add_argument("--tp", type=int, default=1)
    a = ap.parse_args()
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    tok = AutoTokenizer.from_pretrained(a.model)
    ddir = Path(a.data)
    train_rows = read_jsonl(ddir / "train.jsonl", limit=20000)
    train_templates = {r["template"] for r in read_jsonl(ddir / "train.jsonl")}
    enc0 = Encoder(tok, a.max_len)
    shots_ids, shots = few_shot_prefix(enc0, train_rows)
    prefix = enc0.ids(INSTRUCTION) + shots_ids
    enc = Encoder(tok, a.max_len, prefix)

    llm = LLM(model=a.model, max_model_len=a.max_len + 64, gpu_memory_utilization=0.92, tensor_parallel_size=a.tp,
              limit_mm_per_prompt={"image": 0, "video": 0}, enable_prefix_caching=True, max_num_seqs=256)
    sp = SamplingParams(temperature=0.0, max_tokens=24, stop=["\n", " [feedback]"])
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    result = {"model": a.model, "max_len": a.max_len, "few_shot_ids": shots, "prompt": "instruction + 3-shot, text completion"}
    for name, rows in (("validation", read_jsonl(ddir / "validation.jsonl")), ("dev", read_jsonl(ddir / "dev.jsonl")[:a.dev_n])):
        t0 = time.time()
        prompts, trunc = [], 0
        for r in rows:
            p, tr = enc.prompt(r)
            prompts.append({"prompt_token_ids": p}); trunc += tr
        gens = llm.generate(prompts, sp)
        preds = [g.outputs[0].text.split("\n")[0].split(" [feedback]")[0] for g in gens]
        hit = [normalise(p) == normalise(r["answer"]) for p, r in zip(preds, rows)]
        res = {"n": len(rows), "accuracy": sum(hit) / len(rows), "frac_context_truncated": trunc / len(rows), "eval_seconds": time.time() - t0}
        for axis in ("qtype", "bank", "style", "rule_family", "template_seen"):
            groups = {}
            for h, r in zip(hit, rows):
                key = r["template"] in train_templates if axis == "template_seen" else r.get(axis)
                groups.setdefault(str(key), []).append(h)
            res[f"by_{axis}"] = {k: {"n": len(v), "accuracy": sum(v) / len(v)} for k, v in sorted(groups.items())}
        res["examples"] = [{"id": r["id"], "qtype": r["qtype"], "answer": r["answer"], "pred": p} for r, p in list(zip(rows, preds))[:60]]
        result[name] = res
        print(f"[result] {a.model} {name} acc {res['accuracy']:.4f} (n={len(rows)}) {res['eval_seconds']:.0f}s", flush=True)
        (out / "result_big.json").write_text(json.dumps(result, indent=1))
    print(f"[done] wrote {out / 'result_big.json'}", flush=True)


if __name__ == "__main__":
    main()
