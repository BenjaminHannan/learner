"""K2 self-judge: P(yes) from the first answer token's logprobs. Resumable. Usage: judge_k2.py --pools pools.jsonl --out k2_scores.jsonl [--base-url ..] [--concurrency 32]"""
import argparse, asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa


def p_yes(top_logprobs):
    """top_logprobs: [{'token','logprob'}, ...] for the first generated token. Returns P(yes)/(P(yes)+P(no)) or None."""
    import math
    yes = no = 0.0
    for t in top_logprobs or []:
        w = (t.get("token") or "").strip().lower()
        if w == "yes":
            yes += math.exp(t["logprob"])
        elif w == "no":
            no += math.exp(t["logprob"])
    return yes / (yes + no) if yes + no > 0 else None


def key(r):
    return f"{r['pool']}|{r['try_idx']}"


async def main():
    import httpx
    ap = argparse.ArgumentParser()
    ap.add_argument("--pools", default=os.path.join(HERE, "pools.jsonl"))
    ap.add_argument("--out", default=os.path.join(HERE, "k2_scores.jsonl"))
    ap.add_argument("--base-url", default="http://127.0.0.1:8090/v1")
    ap.add_argument("--model", default="k2")
    ap.add_argument("--concurrency", type=int, default=32)
    a = ap.parse_args()
    recs = read_jsonl(a.pools)
    done = {r["key"] for r in read_jsonl(a.out)}
    todo = [r for r in recs if key(r) not in done]
    print(f"{len(recs)} transcripts, {len(done)} done, {len(todo)} to judge", flush=True)
    sem, fh, n = asyncio.Semaphore(a.concurrency), open(a.out, "a"), [0]

    async def one(cl, r):
        body = dict(model=a.model, messages=[dict(role="user", content=judge_prompt(r["judge_text"]))], max_tokens=1,
                    temperature=0, logprobs=True, top_logprobs=20)
        async with sem:
            for attempt in range(5):
                try:
                    resp = await cl.post(f"{a.base_url}/chat/completions", json=body)
                    resp.raise_for_status()
                    top = resp.json()["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
                    break
                except Exception as e:  # noqa
                    if attempt == 4:
                        print(f"FAILED {key(r)}: {e}", flush=True)
                        return
                    await asyncio.sleep(2 ** attempt)
        fh.write(json.dumps(dict(key=key(r), p_yes=p_yes(top))) + "\n"); fh.flush()
        n[0] += 1
        if n[0] % 200 == 0:
            print(f"{n[0]}/{len(todo)}", flush=True)

    async with httpx.AsyncClient(timeout=600) as cl:
        await asyncio.gather(*(one(cl, r) for r in todo))
    print(f"judged {n[0]} ({len(todo) - n[0]} failed; rerun to resume)")


if __name__ == "__main__":
    asyncio.run(main())
