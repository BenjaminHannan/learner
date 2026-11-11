"""Spot audit (NOT a source of answers): ask the model to solve N random corpus questions, report agreement."""
import json, os, random, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_templates as g
D = sys.argv[1]; N = int(sys.argv[2]); key = os.environ["LEARNER_ANTHROPIC_API_KEY"]
rows = []
for sp in ["train", "dev", "heldout_template", "heldout_structure"]:
    rows += [json.loads(l) for l in open(os.path.join(D, sp + ".jsonl"))]
random.seed(11); pick = random.sample(rows, N)
def one(r):
    g.MAX_TOKENS = 3000
    resp = g.call_api("Solve this problem. End with a line 'FINAL: <integer>'.\n\n" + r["question"], key, temperature=0.0, system="You are a careful math tutor.")
    t = "".join(b.get("text", "") for b in resp["content"] if b["type"] == "text")
    m = re.findall(r"FINAL:\s*\$?(-?[\d,]+)", t)
    return r, (int(m[-1].replace(",", "")) if m else None), resp["usage"]
bad, ok, usd = [], 0, 0
with ThreadPoolExecutor(8) as ex:
    for r, a, u in ex.map(one, pick):
        usd += u["input_tokens"] * 3e-6 + u["output_tokens"] * 15e-6
        if a == r["answer"]: ok += 1
        else: bad.append((r["question"], r["answer"], a))
print("agree %d/%d  spend ~$%.2f" % (ok, N, usd))
for b in bad: print(b)
