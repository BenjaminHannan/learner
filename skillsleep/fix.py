"""Night step 2a: for each train task with no passing day run, Sonnet reads the policy + one failed transcript and writes a short critique.
Usage (tau2 venv python): fix.py DAY_RESULTS ENV_JSON HINTS_JSON      -> {task_id: critique}. No answer key is shown."""
import json, sys, time
from concurrent.futures import ThreadPoolExecutor
import litellm
from common import ok, real, sims

MODEL = "anthropic/claude-sonnet-5-5"
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


def critique(prompt):
    for i in range(6):  # litellm retries 429/529 itself; this outer loop covers what slips through
        try:
            r = litellm.completion(model=MODEL, messages=[{"role": "user", "content": prompt}], max_tokens=400, num_retries=6)
            return r.choices[0].message.content.strip()
        except Exception as e:
            print("sonnet retry", i, type(e).__name__, str(e)[:120], flush=True); time.sleep(5 * 2 ** i)
    return None


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
    with ThreadPoolExecutor(4) as ex:
        res = dict(zip(jobs, ex.map(critique, jobs.values())))
    hints = {t: h for t, h in res.items() if h}
    json.dump(hints, open(outp, "w"), indent=1); print("critiques written:", len(hints), "of", len(jobs))
