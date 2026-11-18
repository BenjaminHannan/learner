"""J-LFM3: untuned LFM3-1.7B on llama-server (thinking off, greedy, 1 token): P(yes) = P(yes)/(P(yes)+P(no)) over the first answer token's top-20 logprobs (Pick-1's rule).
Prompt = p6common.judge_prompt(task). Usage: judge_lfm3.py --tasks dev|file.jsonl --out scores.jsonl [--url http://127.0.0.1:8080]   Resumable."""
import argparse, concurrent.futures as cf, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p6common as C
sys.path.insert(0, os.path.join(C.CREATIVE, "probe5"))
from llm_server import LlamaServer, TOPK  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="dev")
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--parallel", type=int, default=2)
    a = ap.parse_args()
    tasks = sum(C.dev_tasks(), []) if a.tasks == "dev" else C.read_jsonl(a.tasks)
    done = {r["task"] for r in C.read_jsonl(a.out)} if os.path.exists(a.out) else set()
    cl = LlamaServer(a.url, timeout=1800.0)

    def one(t):
        p, n, top = cl.p_yes(C.judge_prompt(t), lora_scale=0.0, topk=TOPK)
        return dict(task=t["id"], p_ask=p, n_prompt=n)

    with open(a.out, "a") as f, cf.ThreadPoolExecutor(a.parallel) as ex:
        for r in ex.map(one, [t for t in tasks if t["id"] not in done]):
            f.write(json.dumps(r) + "\n")
            f.flush()
            print(r, flush=True)


if __name__ == "__main__":
    main()
