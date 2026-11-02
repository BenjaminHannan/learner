"""ARC-Easy test (first 200 questions) by choice log-prob with HF transformers. GPU must be free (no vLLM running).
Usage: arc.py MODEL_DIR ARM >> summary.jsonl   -> line {arm, domain: arc_easy, sims: n, pass: correct, per_task: {idx: [0/1]}, acc_raw}
Score = sum log p(' choice' | 'Question: ...\\nAnswer:'); the primary 'pass' uses the length-normalised score (per character), acc_raw uses the plain sum."""
import glob, json, sys
import torch, torch.nn.functional as F
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer
import pyarrow.parquet as pq

mdir, arm = sys.argv[1:3]
d = snapshot_download("allenai/ai2_arc", repo_type="dataset", allow_patterns=["ARC-Easy/test-*.parquet"])
rows = pq.read_table(glob.glob(d + "/ARC-Easy/test-*.parquet")[0]).to_pylist()[:200]
tok = AutoTokenizer.from_pretrained(mdir, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(mdir, dtype=torch.bfloat16, trust_remote_code=True).cuda().eval()


@torch.no_grad()
def score(ctx, cont):
    c = tok(ctx, add_special_tokens=True)["input_ids"]; k = tok(cont, add_special_tokens=False)["input_ids"]
    ids = torch.tensor([c + k], device="cuda")
    lp = F.log_softmax(model(input_ids=ids, use_cache=False).logits[0, len(c) - 1:-1].float(), -1)
    return lp.gather(1, torch.tensor(k, device="cuda")[:, None]).sum().item()


norm, raw = {}, {}
for i, r in enumerate(rows):
    labels, texts = r["choices"]["label"], r["choices"]["text"]
    sc = [score("Question: " + r["question"] + "\nAnswer:", " " + t) for t in texts]
    gold = labels.index(r["answerKey"])
    norm[str(i)] = [int(max(range(len(sc)), key=lambda j: sc[j] / len(texts[j])) == gold)]
    raw[str(i)] = int(max(range(len(sc)), key=lambda j: sc[j]) == gold)
print(json.dumps({"arm": arm, "domain": "arc_easy", "sims": len(rows), "pass": sum(v[0] for v in norm.values()), "per_task": norm, "acc_raw": sum(raw.values()) / len(rows)}))
