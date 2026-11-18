"""SELF judge on llama-server: LFM3 (untuned, adapter scale 0.0) reads the compact transcript and "Did the assistant fully and correctly do what the user asked, ...? Answer yes or no.";
score = P(yes) / (P(yes) + P(no)) over the top-20 first-token candidates (Pick-1's rule), as self_mlx.py / pick1/judge_k2.py: user message only, no tools, thinking off, greedy, max_tokens 1.
The candidates come from the server's logprobs (top_logprobs on the first answer token). Output rows {key, p_yes, n_prompt} as self_scores.jsonl.
Usage: self_lfm3.py --tries DIR/results.jsonl --tasks tasks_new.jsonl --pools DIR/pools.jsonl --out DIR/self_scores.jsonl [--url ...]   Resumable; exit 75 = ASSISTANT_RUNNING."""
import argparse, concurrent.futures as cf, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5common as C
import self_mlx as S4
from llm_server import ServerError, TOPK

P = C.P
MAX_CHARS = 36000    # absurdly long transcript: keep the end, where the question is (~12k tokens, as self_mlx's token cap)


def judge_one(client, rec, lora_scale=0.0):
    text = S4.judge_prompt(rec["judge_text"])
    if len(text) > MAX_CHARS:
        text = text[:200] + "\n...\n" + text[-(MAX_CHARS - 205):]
    try:
        p, n, top = client.p_yes(text, lora_scale=lora_scale, topk=TOPK)
    except ServerError as e:
        print(f"{P.pool_key(rec)}: server refused: {e}", flush=True)
        return dict(key=P.pool_key(rec), p_yes=None, n_prompt=0), 0
    return dict(key=P.pool_key(rec), p_yes=p, n_prompt=n), len(top or [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tries", required=True, help="results.jsonl from agent_lfm3.py")
    ap.add_argument("--tasks", default=C.TASKS)
    ap.add_argument("--pools", required=True, help="pools.jsonl: written from --tries if missing")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--lora-scale", type=float, default=0.0)
    C.add_server_args(ap)
    a = ap.parse_args()
    if not os.path.exists(a.pools):
        ids = {t["id"] for t in P.load_tasks(a.tasks)}
        recs = P.build_pools(P.read_jsonl(a.tries), ids)
        C.atomic_write(a.pools, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
        print(f"built {len(recs)} pool members -> {a.pools}", flush=True)
    recs = P.read_jsonl(a.pools)[:a.limit or None]
    done = {r["key"] for r in C.read_jsonl(a.out)}
    todo = [r for r in recs if P.pool_key(r) not in done]
    print(f"{len(recs)} tries, {len(done)} judged, {len(todo)} to judge -> {a.out}", flush=True)
    if not todo:
        return 0
    client = C.make_client(a)
    if not client.healthy():
        print("llama-server is not answering at", a.url)
        return 2
    fh, t0, n, none, thin, paused = open(a.out, "a"), time.time(), 0, 0, 0, None
    it = iter(todo)
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        running = set()
        while True:
            while len(running) < a.parallel and not paused:
                paused = f"{C.flag_path()} exists" if (not a.no_pause_flag and C.assistant_running()) else None
                r = None if paused else next(it, None)
                if r is None:
                    break
                running.add(ex.submit(judge_one, client, r, a.lora_scale))
            if not running:
                break
            fin, running = cf.wait(running, return_when=cf.FIRST_COMPLETED)
            for f in fin:
                row, ncand = f.result()
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                n += 1
                none += row["p_yes"] is None
                thin += ncand < 3          # fewer than 3 candidates: the server returned (nearly) one-hot probabilities instead of the full distribution
                if n % 50 == 0:
                    print(f"{n}/{len(todo)} {time.time() - t0:.0f}s", flush=True)
    print(f"judged {n} in {time.time() - t0:.0f}s; no yes/no among the candidates: {none}; replies with < 3 candidates: {thin}")
    if n and thin > 0.5 * n:
        print("WARNING: most replies carried < 3 candidate tokens; P(yes) is not a real probability. Check the server's logprobs output.")
    if paused:
        print(f"PAUSED: {paused}. Rerun the same command to resume.")
        return C.EXIT_PAUSED
    return 0


if __name__ == "__main__":
    sys.exit(main())
