"""Haiku 5.5 reference judge via Message Batches API. Resumable (state file holds batch ids).
Usage: judge_haiku.py [--dry-run] --pools pools.jsonl --out haiku_scores.jsonl --state haiku_state.json. Key: env LEARNER_ANTHROPIC_API_KEY."""
import argparse, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa

MODEL = "claude-haiku-5-5"
PRICE_IN, PRICE_OUT = 0.10 * 0.5, 0.50 * 0.5   # USD per Mtok at 50% batch discount (Haiku 5.5 list $0.10 / $0.50, prompts <=100K)
MAX_PER_BATCH, EST_OUT = 10000, 4


def key(r):
    return f"{r['pool']}|{r['try_idx']}"


def parse_score(text):
    m = re.match(r"\s*(\d+(?:\.\d+)?)", text or "")
    return min(10.0, float(m.group(1))) if m else None


def estimate(recs):
    chars = sum(len(judge_prompt(r["judge_text"], HAIKU_QUESTION)) for r in recs)
    tin = chars / 3.5
    return tin, tin / 1e6 * PRICE_IN + len(recs) * EST_OUT / 1e6 * PRICE_OUT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pools", default=os.path.join(HERE, "pools.jsonl"))
    ap.add_argument("--out", default=os.path.join(HERE, "haiku_scores.jsonl"))
    ap.add_argument("--state", default=os.path.join(HERE, "haiku_state.json"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    recs = read_jsonl(a.pools)
    tin, cost = estimate(recs)
    nb = -(-len(recs) // MAX_PER_BATCH)
    print(f"{len(recs)} requests in {nb} batch(es); ~{tin/1e6:.2f}M input tokens (chars/3.5); est. cost ${cost:.2f} "
          f"(assumes Haiku 5.5 batch ${PRICE_IN}/M in, ${PRICE_OUT}/M out, {EST_OUT} output tokens each)")
    if a.dry_run:
        return
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    client = anthropic.Anthropic(api_key=os.environ["LEARNER_ANTHROPIC_API_KEY"])
    state = json.load(open(a.state)) if os.path.exists(a.state) else {"batches": []}
    if not state["batches"]:  # submit once; a rerun only polls
        for b in range(nb):
            chunk = recs[b * MAX_PER_BATCH:(b + 1) * MAX_PER_BATCH]
            reqs = [Request(custom_id=f"r{b * MAX_PER_BATCH + i}", params=MessageCreateParamsNonStreaming(
                model=MODEL, max_tokens=16, thinking={"type": "disabled"},
                messages=[{"role": "user", "content": judge_prompt(r["judge_text"], HAIKU_QUESTION)}])) for i, r in enumerate(chunk)]
            state["batches"].append(client.messages.batches.create(requests=reqs).id)
            json.dump(state, open(a.state, "w"))
        print("submitted", state["batches"], flush=True)
    for bid in state["batches"]:
        while client.messages.batches.retrieve(bid).processing_status != "ended":
            print(time.strftime("%H:%M:%S"), bid, "processing", flush=True)
            time.sleep(60)
    scores = {}
    for bid in state["batches"]:
        for res in client.messages.batches.results(bid):
            i = int(res.custom_id[1:])
            txt = ""
            if res.result.type == "succeeded":
                txt = next((c.text for c in res.result.message.content if c.type == "text"), "")
            scores[key(recs[i])] = parse_score(txt)
    with open(a.out, "w") as f:
        for r in recs:
            f.write(json.dumps(dict(key=key(r), score=scores.get(key(r)))) + "\n")
    print(f"wrote {len(scores)} scores ({sum(v is None for v in scores.values())} unparsed) -> {a.out}")


if __name__ == "__main__":
    main()
