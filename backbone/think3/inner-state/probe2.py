"""Free CPU probe 2 on base K2-3.7B: is a compact oracle trace (the story lines the answer depends on) a strong teacher,
and at which layers does the teacher's state at 'The answer is:' differ from the thinking-off state?
Think content: off (empty) / oracle (evidence lines in story order) / wrong (another row's evidence lines).
"""
import copy, json, os, sys, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

D = "/tmp/claude-0/-home-user-learner/d7097773-0c57-5253-b634-f924e5aab1d8/scratchpad/"
tok = AutoTokenizer.from_pretrained(D + "k2", trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(D + "k2", trust_remote_code=True, dtype=torch.bfloat16).eval()
torch.set_num_threads(4)
NL = len(model.model.layers)
layer_out = {}
for i, L in enumerate(model.model.layers):
    L.register_forward_hook(lambda m, a, o, i=i: layer_out.__setitem__(i, (o[0] if isinstance(o, tuple) else o)[0, -1].float()))

rows = json.load(open(D + "ev_rows.json"))
res = json.load(open(D + "probe2_out.json")) if os.path.exists(D + "probe2_out.json") else []
done = {x["id"] for x in res}
t0 = time.time()
with torch.no_grad():
    for ri, r in enumerate(rows):
        user = r["context"] + "\n" + r["question"].replace("[question] ", "") + "\nAnswer with just the answer, no explanation."
        head = tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True,
                                       reasoning_effort="high")
        if r["id"] in done:
            continue
        hid = tok(head, add_special_tokens=False)["input_ids"]
        hcache = model(input_ids=torch.tensor([hid]), use_cache=True).past_key_values
        wrong = rows[(ri + 7) % len(rows)]["evidence_lines"]
        ans = tok(" " + r["answer"], add_special_tokens=False)["input_ids"]
        rec = {"id": r["id"], "depth": r["depth"]}
        states = {}
        for kind, think in (("off", ""), ("oracle", "\n".join(r["evidence_lines"]) + "\n"), ("wrong", "\n".join(wrong) + "\n")):
            pre = tok(head + think + "</ifm|think>The answer is:", add_special_tokens=False)["input_ids"]
            assert pre[:len(hid)] == hid
            out = model(input_ids=torch.tensor([pre[len(hid):]]), past_key_values=copy.deepcopy(hcache), use_cache=True)
            states[kind] = [layer_out[i].clone() for i in range(NL)]
            o2 = model(input_ids=torch.tensor([ans]), past_key_values=out.past_key_values, use_cache=True)
            lp0 = torch.log_softmax(out.logits[0, -1].float(), -1)
            lps = torch.log_softmax(o2.logits[0].float(), -1)
            tot = lp0[ans[0]].item() + sum(lps[j, ans[j + 1]].item() for j in range(len(ans) - 1))
            rec[kind] = (tot, int(lp0.argmax().item() == ans[0]))
        # per-layer relative L2 distance and cosine between teacher (oracle) and off states at the answer position
        rec["rel_l2"] = [((states["oracle"][i] - states["off"][i]).norm() / states["oracle"][i].norm()).item() for i in range(NL)]
        rec["cos"] = [torch.nn.functional.cosine_similarity(states["oracle"][i], states["off"][i], 0).item() for i in range(NL)]
        rec["rel_l2_wrong"] = [((states["oracle"][i] - states["wrong"][i]).norm() / states["oracle"][i].norm()).item() for i in range(NL)]
        # share of CODI's per-layer L1 gap (divided by teacher std) held by the top 1% of dimensions
        rec["top1pct_share"] = []
        for i in range(NL):
            g = ((states["oracle"][i] - states["off"][i]) / states["oracle"][i].std()).abs()
            rec["top1pct_share"].append((g.topk(g.numel() // 100).values.sum() / g.sum()).item())
        res.append(rec)
        print(ri, r["depth"], f"{time.time()-t0:.0f}s", rec["off"], rec["oracle"], rec["wrong"], flush=True)
        json.dump(res, open(D + "probe2_out.json", "w"))
