# Does LFM3's batched, left-padded generation give the same greedy text as one-at-a-time? (conv layers + left pads)
import time, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
R, REV = "LiquidAI/LFM3-1.7B", "40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd"
tok = AutoTokenizer.from_pretrained(R, revision=REV, trust_remote_code=True)
t0 = time.time()
lm = AutoModelForCausalLM.from_pretrained(R, revision=REV, trust_remote_code=True, dtype=torch.float32).eval()
print("loaded", round(time.time() - t0), "s", type(lm).__name__)
qs = ["Who wrote Hamlet? Answer with a name only.",
      "Message from Sam: \"My mentor Vebribon moved to Foperukin last spring, and Kizibra still works at Meirox.\"\n\nList the facts this message states about named people or places as subject | relation | object lines.",
      "What is 2+3?"]
P = [tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True, enable_thinking=False) for q in qs]
enc = [tok(p, add_special_tokens=False)["input_ids"] for p in P]
def gen(batch, n=24):
    m = max(map(len, batch))
    ids = torch.full((len(batch), m), tok.pad_token_id); mask = torch.zeros((len(batch), m), dtype=torch.long)
    for r, e in enumerate(batch):
        ids[r, m - len(e):] = torch.tensor(e); mask[r, m - len(e):] = 1
    with torch.no_grad():
        out = lm.generate(input_ids=ids, attention_mask=mask, max_new_tokens=n, do_sample=False, pad_token_id=tok.pad_token_id, eos_token_id=tok.eos_token_id)
        lg = lm(input_ids=ids, attention_mask=mask).logits[:, -1].float()
    return [tok.decode(o[m:], skip_special_tokens=True) for o in out], lg
single = [gen([e]) for e in enc]
bat, lgb = gen(enc)
for i, (s, lg) in enumerate(single):
    print(i, "len", len(enc[i]), "same text:", s[0] == bat[i], "| max |dlogit|", round((lg[0] - lgb[i]).abs().max().item(), 4))
    print("   single:", repr(s[0][:120])); print("   batch :", repr(bat[i][:120]))
