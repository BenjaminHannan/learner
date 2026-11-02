"""Night step 2a: for each train task with no passing day run, Sonnet reads the policy + one failed transcript and writes a short critique.
Usage (needs the anthropic SDK): fix.py DAY_RESULTS ENV_JSON HINTS_JSON      -> {task_id: critique}. No answer key is shown.
All critiques go out as ONE Message Batches request; if it has not ended after BATCH_WAIT_MIN (30) minutes it is cancelled and the missing ones are asked directly."""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from common import ok, real, sims

MODEL = "claude-sonnet-5-5"; BATCH_WAIT_S = 60 * float(os.environ.get("BATCH_WAIT_MIN", 30)); POLL_S = float(os.environ.get("BATCH_POLL_S", 30))
PROMPT = """You review a customer-service agent that failed a task. Below are the store policy and one failed conversation (agent turns, tool calls and tool results).
You are not told what the correct outcome was. Judge only from the policy and the transcript.

<policy>
{policy}
</policy>

<transcript>
{transcript}
</transcript>

Write a critique of at most 120 words, addressed to the agent: what it did wrong (a policy rule it broke, a step it skipped or did too early, a wrong or unverified action, giving up, asking too little or too much) and what to do differently next time in a request like this.
Do not invent order ids, user ids, item ids or other facts that are not in the transcript. Output only the critique."""


def show(msgs, cap=1200):
    out = []
    for m in msgs:
        r = m["role"]
        if r == "assistant" and m.get("tool_calls"):
            out.append("AGENT CALLS: " + "; ".join("%s(%s)" % (t["name"], json.dumps(t["arguments"])) for t in m["tool_calls"]))
        elif r == "tool":
            c = m.get("content") or ""; out.append("TOOL RESULT: " + (c if len(c) <= cap else c[:cap] + " ...[cut]"))
        else:
            out.append("%s: %s" % (r.upper(), m.get("content")))
    return "\n".join(out)


def direct(client, prompt):
    for i in range(6):  # the SDK retries 429/529 itself; this outer loop covers what slips through
        try:
            r = client.messages.create(model=MODEL, max_tokens=400, messages=[{"role": "user", "content": prompt}])
            return r.content[0].text.strip()
        except Exception as e:
            print("sonnet retry", i, type(e).__name__, str(e)[:120], flush=True); time.sleep(5 * 2 ** i)
    return None


def batched(client, prompts):
    """{key: critique} for the critiques the batch returned in time; the rest are missing."""
    try:
        b = client.messages.batches.create(requests=[{"custom_id": "t" + k, "params": {"model": MODEL, "max_tokens": 400, "messages": [{"role": "user", "content": p}]}}
                                                     for k, p in prompts.items()])
    except Exception as e:
        print("batch create failed:", type(e).__name__, str(e)[:200], flush=True); return {}
    print("batch", b.id, "created with", len(prompts), "requests", flush=True); t0 = time.time()
    while b.processing_status != "ended" and time.time() - t0 < BATCH_WAIT_S:
        time.sleep(POLL_S)
        try:
            b = client.messages.batches.retrieve(b.id)
        except Exception as e:
            print("batch poll error", type(e).__name__, str(e)[:100], flush=True)
    if b.processing_status != "ended":
        print(f"batch not ended after {time.time() - t0:.0f}s: cancelling, asking directly", flush=True)
        try:
            client.messages.batches.cancel(b.id)
        except Exception as e:
            print("cancel failed", type(e).__name__, flush=True)
    out = {}
    try:
        for r in client.messages.batches.results(b.id):  # partial results exist for a cancelled batch
            if r.result.type == "succeeded" and r.result.message.content:
                out[r.custom_id[1:]] = r.result.message.content[0].text.strip()
    except Exception as e:
        print("batch results failed:", type(e).__name__, str(e)[:100], flush=True)
    print("batch gave", len(out), "of", len(prompts), flush=True)
    return out


def critiques(client, prompts):
    res = batched(client, prompts); todo = [k for k in prompts if k not in res]
    if todo:
        print("direct calls for", len(todo), flush=True)
        with ThreadPoolExecutor(4) as ex:
            res.update(zip(todo, ex.map(lambda k: direct(client, prompts[k]), todo)))
    return {k: v for k, v in res.items() if v}


if __name__ == "__main__":
    day, envp, outp = sys.argv[1:4]
    policy = json.load(open(envp))["policy"]; by = {}
    for s in sims(day):
        by.setdefault(str(s["task_id"]), []).append(s)
    jobs = {}
    for t, ss in by.items():
        if any(ok(s) for s in ss):
            continue
        bad = [s for s in ss if real(s)] or ss  # prefer a failure that ended on its own
        jobs[t] = PROMPT.format(policy=policy, transcript=show(bad[0]["messages"]))
    print("tasks with no passing day run:", len(jobs), sorted(jobs, key=int), flush=True)
    import anthropic
    hints = critiques(anthropic.Anthropic(max_retries=6), jobs)
    json.dump(hints, open(outp, "w"), indent=1); print("critiques written:", len(hints), "of", len(jobs))
