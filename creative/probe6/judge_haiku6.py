"""J-HAIKU (reference only): claude-haiku-4-5 via the Message Batches API, 5 samples per task, same question; P(yes) = share of yes. No temperature / thinking params.
Usage: judge_haiku6.py --tasks dev|file.jsonl --out scores.jsonl --state state.json   (submit once, polls, collects; key env LEARNER_ANTHROPIC_API_KEY)"""
import argparse, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p6common as C

MODEL = "claude-haiku-4-5"
PRICE_IN, PRICE_OUT = 0.5, 2.5      # USD per Mtok, 50% batch discount (list $1 / $5)
N = 5


def parse_yes(txt):
    m = re.match(r"\W*(yes|no)\b", (txt or "").strip(), re.I)
    return None if not m else m.group(1).lower() == "yes"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="dev", help="'dev' or a jsonl of tasks (id, state, user)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--state", required=True)
    a = ap.parse_args()
    if a.tasks == "dev":
        tgt, non = C.dev_tasks()
        tasks = tgt + non
    else:
        tasks = C.read_jsonl(a.tasks)
    reqs = [(f"{t['id']}|{s}", C.judge_prompt(t)) for t in tasks for s in range(N)]
    print(f"{len(reqs)} requests; est cost ${sum(len(p) for _, p in reqs) / 3.5 / 1e6 * PRICE_IN + len(reqs) * 8 / 1e6 * PRICE_OUT:.3f}", flush=True)
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    cl = anthropic.Anthropic(api_key=os.environ["LEARNER_ANTHROPIC_API_KEY"])
    st = json.load(open(a.state)) if os.path.exists(a.state) else None
    if not st:
        b = cl.messages.batches.create(requests=[Request(custom_id=f"r{i}", params=MessageCreateParamsNonStreaming(
            model=MODEL, max_tokens=8, messages=[{"role": "user", "content": p}])) for i, (_, p) in enumerate(reqs)])
        st = {"batch": b.id, "keys": [k for k, _ in reqs]}
        json.dump(st, open(a.state, "w"))
        print("submitted", b.id, flush=True)
    while cl.messages.batches.retrieve(st["batch"]).processing_status != "ended":
        print(time.strftime("%H:%M:%S"), "processing", flush=True)
        time.sleep(30)
    votes, usage = {}, [0, 0]
    for res in cl.messages.batches.results(st["batch"]):
        k = st["keys"][int(res.custom_id[1:])]
        tid = k.rsplit("|", 1)[0]
        y = None
        if res.result.type == "succeeded":
            msg = res.result.message
            y = parse_yes(next((c.text for c in msg.content if c.type == "text"), ""))
            usage[0] += msg.usage.input_tokens
            usage[1] += msg.usage.output_tokens
        votes.setdefault(tid, []).append(y)
    with open(a.out, "w") as f:
        for tid, v in sorted(votes.items()):
            ok = [x for x in v if x is not None]
            f.write(json.dumps(dict(task=tid, p_ask=(sum(ok) / len(ok) if ok else None), n_valid=len(ok), n=len(v))) + "\n")
    print(f"wrote {len(votes)} tasks; tokens in/out {usage}; cost ${usage[0] / 1e6 * PRICE_IN + usage[1] / 1e6 * PRICE_OUT:.4f}")


if __name__ == "__main__":
    main()
