"""Exp 101 eval: held-out val loss/perplexity; 50 sampled continuations from 10 fixed
prompts (temp 0.8, fixed seed); BLiMP-10 minimal-pair accuracy (total log-prob).

BLiMP source: official repo https://github.com/alexwarstadt/blimp (data/*.jsonl).
Licence note: the repo ships NO licence file (checked 2026-09-22); data used for
EVALUATION ONLY, never training. Paper: Warstadt et al. 2020.
"""
import argparse, json, os
import numpy as np
import torch

from fable_talker101_model import Talker101

# 10 phenomena (one paradigm file each; simple everyday words for small-tokenizer coverage)
BLIMP_FILES = [
    ("determiner_noun_agreement", "determiner_noun_agreement_1.jsonl"),
    ("subject_verb_agreement", "regular_plural_subject_verb_agreement_1.jsonl"),
    ("anaphor_agreement", "anaphor_gender_agreement.jsonl"),
    ("argument_structure", "transitive.jsonl"),
    ("binding", "principle_A_c_command.jsonl"),
    ("control_raising", "tough_vs_raising_1.jsonl"),
    ("ellipsis", "ellipsis_n_bar_1.jsonl"),
    ("irregular_forms", "regular_plural_subject_verb.jsonl"),  # placeholder, replaced below
    ("npi_licensing", "npi_present_1.jsonl"),
    ("quantifiers", "existential_there_quantifiers_1.jsonl"),
]
BLIMP_FILES[7] = ("irregular_forms", "irregular_past_participle_adjectives.jsonl")

PROMPTS = [
    "Once upon a time there was a little girl named Lily. ",
    "The big brown dog ran to the park and ",
    "My mom gave me a red balloon. I ",
    "The cat sat on the mat. Then the cat ",
    "Tom and his friends went to the lake. They ",
    "A small bird lived in a tall tree. Every morning the bird ",
    "The teacher asked the children to sit down. Then she ",
    "There was a big castle on the hill. Inside the castle ",
    "Ben has a blue box. In the box there is ",
    "The sun went down and the stars came out. Sam looked up and ",
]


@torch.no_grad()
def seq_logprob(model, ids, device):
    x = torch.tensor(ids, dtype=torch.long, device=device).unsqueeze(0)
    out = model(x)
    logp = torch.log_softmax(out["logits"][0, :-1], dim=-1)
    tgt = x[0, 1:]
    lp = logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
    # copy part of the mixture (eval scores vocab log-prob; copy only adds mass)
    return float(lp.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--data-dir", default="artifacts/fable-talker101-20260921")
    ap.add_argument("--blimp-dir", default="artifacts/fable-talker101-20260921/fable_talker101_blimp")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--ctx", type=int, default=512)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(os.path.join(args.data_dir, "fable_talker101_tokenizer.json"))
    eos = tok.token_to_id("<eos>")
    ck = torch.load(args.ckpt, map_location=args.device, weights_only=False)
    model = Talker101().to(args.device)
    model.load_state_dict(ck["model"])
    model.eval()

    # (a) val loss / perplexity over val shard
    data = np.memmap(os.path.join(args.data_dir, "fable_talker101_val.bin"),
                     dtype=np.uint16, mode="r")
    n, bs, tot, cnt = len(data), 8, 0.0, 0
    for b in range(20):
        i = (b * bs * args.ctx) % max(1, n - args.ctx - 1)
        x = torch.from_numpy(np.stack(
            [data[(i + k * args.ctx) % (n - args.ctx - 1):][:args.ctx + 1]
             for k in range(bs)]).astype(np.int64))
        xb, yb = x[:, :-1].to(args.device), x[:, 1:].to(args.device)
        tot += model(xb, yb)["loss"].item() * xb.numel()
        cnt += xb.numel()
    vl = tot / cnt
    res = {"val_loss_nats": round(vl, 4), "val_ppl": round(float(np.exp(vl)), 3)}

    # (b) 50 continuations (5 per prompt), temp 0.8, seed 101
    torch.manual_seed(101)
    samples = []
    for p in PROMPTS:
        ids = tok.encode(p).ids
        for _ in range(5):
            cur = list(ids)
            x = torch.tensor(cur, dtype=torch.long, device=args.device).unsqueeze(0)
            for _ in range(60):
                xc = x[:, -args.ctx:]
                lg = model(xc)["logits"][0, -1] / 0.8
                nx = torch.multinomial(torch.softmax(lg, dim=-1), 1).item()
                cur.append(nx)
                if nx == eos:
                    break
                x = torch.cat([x, torch.tensor([[nx]], device=args.device)], dim=1)
            samples.append({"prompt": p, "continuation": tok.decode(cur[len(ids):], skip_special_tokens=True)})
    res["n_samples"] = len(samples)

    # (c) BLiMP-10
    blimp, per_ph = {}, {}
    for phen, fn in BLIMP_FILES:
        rows = [json.loads(l) for l in
                open(os.path.join(args.blimp_dir, fn), encoding="utf-8")]
        good = bad = 0
        for r in rows:
            g = tok.encode(r["sentence_good"]).ids + [eos]
            b = tok.encode(r["sentence_bad"]).ids + [eos]
            if len(g) > args.ctx or len(b) > args.ctx:
                continue
            if seq_logprob(model, g, args.device) > seq_logprob(model, b, args.device):
                good += 1
            else:
                bad += 1
        per_ph[phen] = {"correct": good, "wrong": bad,
                        "acc": round(good / max(1, good + bad), 4)}
    tot_c = sum(v["correct"] for v in per_ph.values())
    tot_w = sum(v["wrong"] for v in per_ph.values())
    res["blimp10_acc"] = round(tot_c / max(1, tot_c + tot_w), 4)
    res["blimp10_per_phenomenon"] = per_ph

    out = args.out or os.path.join(args.data_dir, "fable_talker101_eval.json")
    json.dump(res, open(out, "w"), indent=2)
    with open(os.path.join(args.data_dir, "fable_talker101_samples.json"), "w") as f:
        json.dump(samples, f, indent=2)
    print(json.dumps({k: v for k, v in res.items() if k != "blimp10_per_phenomenon"}, indent=2))
    for k, v in per_ph.items():
        print(f"  {k}: {v['correct']}/{v['correct']+v['wrong']} = {v['acc']}")


if __name__ == "__main__":
    main()
