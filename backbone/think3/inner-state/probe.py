"""Free CPU probe on base K2-Horizon-3.7B (no training): how should a fed-back inner state be shaped?

For village validation rows, thinking OFF, we insert K "silent laps" inside the empty think block
(<ifm|think>\n [K latents] </ifm|think>) using different ways of turning the model's own state into the next input,
then score the gold answer's log-prob and first-token accuracy. Untrained, so this measures how far each input form
knocks the model off its normal footing (the start point training has to climb from), not how well it can think.
Also records per-layer RMS at the last prompt position vs the RMS of real token embeddings.
"""
import copy, json, math, sys, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

torch.manual_seed(0)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 24
KS = (1, 3, 6)
D = "/tmp/claude-0/-home-user-learner/d7097773-0c57-5253-b634-f924e5aab1d8/scratchpad/"
tok = AutoTokenizer.from_pretrained(D + "k2", trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(D + "k2", trust_remote_code=True, dtype=torch.bfloat16)
model.eval()
torch.set_num_threads(4)
E = model.get_input_embeddings().weight  # [V, H]
emb_rms = E.float().pow(2).mean(-1).sqrt()
EMB_RMS = emb_rms.median().item()
MID = 18

layer_out = {}
def hook(i):
    def f(_m, _inp, out):
        layer_out[i] = (out[0] if isinstance(out, tuple) else out)[:, -1].float()
    return f
for i, L in enumerate(model.model.layers):
    L.register_forward_hook(hook(i))

rows = [r for r in json.load(open(D + "vrows.json")) if 2 <= r["depth"] <= 4 and r["answer"].startswith("the ") and len(r["answer"].split()) <= 3]
rows = rows[:N]


def step(embeds, cache):
    out = model(inputs_embeds=embeds, past_key_values=cache, use_cache=True)
    return out


def lm_last(out):
    return out.logits[:, -1].float()


def score_answer(cache, ans_ids):
    """Feed '</ifm|think>' + answer tokens; return (sum logprob of answer, first-token argmax hit)."""
    ids = torch.tensor([close_ids + ans_ids])
    out = model(input_ids=ids, past_key_values=cache, use_cache=True)
    lp = torch.log_softmax(out.logits[0].float(), -1)
    n0 = len(close_ids) - 1
    tot = sum(lp[n0 + j, t].item() for j, t in enumerate(ans_ids))
    hit = int(lp[n0].argmax().item() == ans_ids[0])
    return tot, hit


close_ids = tok("</ifm|think>The answer is:", add_special_tokens=False)["input_ids"]
filler = tok("\n", add_special_tokens=False)["input_ids"][-1]

res = {"emb_rms_median": EMB_RMS, "rows": []}
t0 = time.time()
with torch.no_grad():
    for ri, r in enumerate(rows):
        user = r["context"] + "\n" + r["question"].replace("[question] ", "") + "\nAnswer with just the answer, no explanation."
        prompt = tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False,
                                         add_generation_prompt=True, reasoning_effort="high")
        # reasoning_effort high opens '<ifm|think>\n'
        assert prompt.endswith("<ifm|think>\n"), prompt[-40:]
        pids = tok(prompt, add_special_tokens=False)["input_ids"]
        ans_ids = tok(" " + r["answer"], add_special_tokens=False)["input_ids"]
        cache0 = None
        out = model(input_ids=torch.tensor([pids]), use_cache=True)
        cache0 = out.past_key_values
        h_last = out.hidden_states if hasattr(out, "hidden_states") and out.hidden_states else None
        per_layer_rms = [layer_out[i].pow(2).mean().sqrt().item() for i in range(len(model.model.layers))]
        # post-final-norm state: recompute from last layer output through model.model.norm
        post = model.model.norm(layer_out[len(model.model.layers) - 1].to(torch.bfloat16)).float()
        rec = {"id": r["id"], "depth": r["depth"], "answer": r["answer"], "n_prompt": len(pids),
               "layer_rms": per_layer_rms, "post_norm_rms": post.pow(2).mean().sqrt().item()}
        base_logits = lm_last(out)
        base_state = {"post": post, "mid": layer_out[MID].clone(), "last": layer_out[len(model.model.layers) - 1].clone()}

        s, h = score_answer(copy.deepcopy(cache0), ans_ids)
        rec["off"] = (s, h)

        def run(kind, K):
            cache = copy.deepcopy(cache0)
            st, logits = dict(base_state), base_logits
            for _ in range(K):
                if kind == "raw_post":       # Coconut: post-final-norm state as is
                    x = st["post"]
                elif kind == "rms_post":     # rescale post-norm state to median embedding RMS
                    x = st["post"] / st["post"].pow(2).mean().sqrt() * EMB_RMS
                elif kind == "raw_last":     # pre-norm last-layer residual (what a careless implementation feeds)
                    x = st["last"]
                elif kind == "rms_mid":      # middle-layer residual, rescaled
                    x = st["mid"] / st["mid"].pow(2).mean().sqrt() * EMB_RMS
                elif kind == "soft":         # Soft Thinking: probability-weighted mix of token embeddings
                    p = torch.softmax(logits, -1).to(E.dtype)
                    x = (p @ E).float()
                elif kind == "soft_top8":    # mix of the top-8 tokens only, renormalized
                    v, ix = logits.topk(8, -1)
                    p = torch.softmax(v, -1).to(E.dtype)
                    x = (p.unsqueeze(-1) * E[ix[0]].unsqueeze(0)).sum(1).float()
                elif kind == "filler":       # control: K newline tokens
                    x = E[filler].float().unsqueeze(0)
                o = model(inputs_embeds=x.to(torch.bfloat16).unsqueeze(1), past_key_values=cache, use_cache=True)
                cache = o.past_key_values
                logits = lm_last(o)
                L = len(model.model.layers)
                st = {"post": model.model.norm(layer_out[L - 1].to(torch.bfloat16)).float(),
                      "mid": layer_out[MID].clone(), "last": layer_out[L - 1].clone()}
            return score_answer(cache, ans_ids)

        for kind in ("filler", "raw_post", "rms_post", "raw_last", "rms_mid", "soft", "soft_top8"):
            for K in KS:
                rec[f"{kind}_K{K}"] = run(kind, K)
        res["rows"].append(rec)
        print(ri, r["depth"], f"{time.time()-t0:.0f}s", "off", rec["off"], "rms_post_K6", rec["rms_post_K6"],
              "raw_last_K6", rec["raw_last_K6"], flush=True)
        json.dump(res, open(D + "probe_out.json", "w"))
print("done", time.time() - t0)
