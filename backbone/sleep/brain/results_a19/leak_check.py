# Does bf16/fp32 LFM3 (no-think prompts, as sleepb renders them) write "</think>" or reasoning before its answer?
import json, sys, time, random, torch
sys.path.insert(0, "/home/user/learner/backbone/sleep/brain"); sys.argv = ["x"]
import sleepb
from sleep1 import Lang, SYS
from transformers import AutoModelForCausalLM, AutoTokenizer
R, REV = "LiquidAI/LFM3-1.7B", "40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd"
dt = {"fp32": torch.float32, "bf16": torch.bfloat16}[sys.argv[1] if len(sys.argv) > 1 else "fp32"]
tok = AutoTokenizer.from_pretrained(R, revision=REV, trust_remote_code=True)
lm = AutoModelForCausalLM.from_pretrained(R, revision=REV, trust_remote_code=True, dtype=torch.float32).eval()
L = Lang(tok, False, torch.device("cpu"), lfm3=True)
wk = json.load(open("/home/user/learner/backbone/sleep/brain/data/week1.json"))
rng = random.Random(0)
fw = rng.sample(wk["tests"]["forward"], 12); th = rng.sample(wk["tests"]["twohop"], 4)
users = [t for t in wk["diary"] if t["role"] == "user" and t.get("mentions")]
tg = rng.sample(users, 8)
jobs = [("test", sleepb.plain_prompt(L, t["q"]), 20, t["target"]) for t in fw + th]
jobs += [("tag", sleepb.tag_prompt(L, t["text"]), 160, None) for t in tg]
jobs += [("ctx", sleepb.ctx_prompt(L, f"[day {t['day']}] {t['text']}", "Who or what is named in this message?"), 20, None) for t in tg[:4]]
out = {}
t0 = time.time()
for kind in ("test", "tag", "ctx"):
    J = [j for j in jobs if j[0] == kind]
    gens = L.generate(lm, [j[1] for j in J], max_new=J[0][2], bs=8)
    out[kind] = gens
    n = sum("</think>" in g for g in gens)
    print(f"== {kind}: {n} of {len(gens)} replies contain </think>; {time.time() - t0:.0f}s", flush=True)
    for j, g in zip(J, gens):
        ok = "" if j[3] is None else (" OK" if j[3].lower() in g.lower() else " MISS(" + j[3] + ")")
        print("  ", repr(g[:170]), ok)
# sampled, as NREM dreams are written (temp 0.8)
gens = L.generate(lm, [j[1] for j in jobs if j[0] == "tag"][:4], max_new=120, bs=4, sample=True)
print(f"== tag sampled: {sum('</think>' in g for g in gens)} of {len(gens)} contain </think>")
for g in gens: print("  ", repr(g[:170]))
