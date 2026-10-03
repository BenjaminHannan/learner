"""E1 (vision design v2, section 4): does the image get through the pipe? Run on a GPU box. See MARKS-E1.md (fixed before the run).

  python e1.py prep                       # images, frozen SigLIP2 8x8 features, candidate sets, frozen-LM caption embeddings
  python e1.py train --arms real shuf blind --seeds 0 1
  python e1.py report                     # table + verdict by the fixed marks -> results.json
Env: E1_OUT (default ./out), E1_NTRAIN (12000), E1_NHELD (1000), E1_STEPS (2500).
"""
from __future__ import annotations
import argparse, json, math, os, random, sys, time
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vision_adapter import GridAdapter  # noqa: E402

OUT = Path(os.environ.get("E1_OUT", "out")); OUT.mkdir(parents=True, exist_ok=True)
NTRAIN, NHELD = int(os.environ.get("E1_NTRAIN", 12000)), int(os.environ.get("E1_NHELD", 1000))
STEPS, BS, LR, ROUNDS, NQ = int(os.environ.get("E1_STEPS", 2500)), 32, 1e-3, 4, 16
ENC, LM = "google/siglip2-base-patch16-256", "LiquidAI/LFM2.5-1.2B-Instruct"
dev = "cuda" if torch.cuda.is_available() else "cpu"
COLORS = {"red": (220, 30, 30), "blue": (30, 60, 220), "green": (30, 160, 60), "yellow": (235, 200, 20), "purple": (140, 50, 170), "orange": (240, 130, 20)}
SHAPES = ["circle", "square", "triangle"]
CELLS = ["top left", "top", "top right", "left", "center", "right", "bottom left", "bottom", "bottom right"]


# ---------------------------------------------------------------- data
def sample_scene(rng):
    n = rng.randint(2, 4)
    return [(rng.choice(list(COLORS)), rng.choice(SHAPES), c) for c in sorted(rng.sample(range(9), n))]


def caption(objs):
    parts = [f"a {c} {s} at the {CELLS[k]}" for c, s, k in objs]
    text = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return text[0].upper() + text[1:] + "."


def distractor(objs, rng):
    shapes = [s for _, s, _ in objs]; rng.shuffle(shapes)  # same shape multiset, new colours/cells/pairing
    cells = sorted(rng.sample(range(9), len(objs)))
    return [(rng.choice(list(COLORS)), s, c) for s, c in zip(shapes, cells)]


def render(objs, rng):
    g = rng.randint(200, 245); img = Image.new("RGB", (256, 256), (g, g, g)); d = ImageDraw.Draw(img)
    for col, sh, k in objs:
        r, c = divmod(k, 3); s = rng.randint(44, 56)
        cx, cy = c * 85 + 42 + rng.randint(-6, 6), r * 85 + 42 + rng.randint(-6, 6)
        box = (cx - s // 2, cy - s // 2, cx + s // 2, cy + s // 2)
        if sh == "circle": d.ellipse(box, fill=COLORS[col])
        elif sh == "square": d.rectangle(box, fill=COLORS[col])
        else: d.polygon([(cx, box[1]), (box[0], box[3]), (box[2], box[3])], fill=COLORS[col])
    return img


def build_scenes(n, seed, banned):
    rng, out, seen = random.Random(seed), [], set(banned)
    while len(out) < n:
        o = sample_scene(rng); c = caption(o)
        if c not in seen: seen.add(c); out.append(o)
    return out


def candidates(objs, rng):
    true = caption(objs); cs = {true}
    while len(cs) < 8: cs.add(caption(distractor(objs, rng)))
    cs = sorted(cs); rng.shuffle(cs)
    return cs, cs.index(true)


def prep():
    from transformers import AutoModel, AutoProcessor, AutoModelForCausalLM, AutoTokenizer
    train = build_scenes(NTRAIN, 1000, set())
    held = build_scenes(NHELD, 2000, {caption(o) for o in train})
    rng = random.Random(7)
    meta = {}
    for name, scenes in (("train", train), ("held", held)):
        cands = [candidates(o, rng) for o in scenes]
        meta[name] = {"scenes": scenes, "captions": [caption(o) for o in scenes],
                      "cands": [c for c, _ in cands], "label": [l for _, l in cands]}
    json.dump(meta, open(OUT / "meta.json", "w"))
    # frozen SigLIP2 features, 16x16 -> 8x8 average pool, fp16
    enc = AutoModel.from_pretrained(ENC).vision_model.eval().to(dev); proc = AutoProcessor.from_pretrained(ENC)
    for name, scenes in (("train", train), ("held", held)):
        rng_i = random.Random(5 if name == "train" else 6); feats = []
        for i in range(0, len(scenes), 64):
            imgs = [render(o, rng_i) for o in scenes[i:i + 64]]
            with torch.no_grad():
                x = enc(pixel_values=proc(images=imgs, return_tensors="pt")["pixel_values"].to(dev)).last_hidden_state
                b, n, d = x.shape; s = int(math.isqrt(n))
                x = F.adaptive_avg_pool2d(x.float().reshape(b, s, s, d).permute(0, 3, 1, 2), 8).permute(0, 2, 3, 1).reshape(b, 64, d)
            feats.append(x.half().cpu())
        torch.save(torch.cat(feats), OUT / f"feats_{name}.pt"); print(name, "feats", torch.cat(feats).shape, flush=True)
        if name == "held":
            for i in range(8): render(scenes[i], random.Random(i)).save(OUT / f"example_{i}.png")
    del enc
    # frozen LM caption embeddings: mean last hidden state over caption tokens
    tok = AutoTokenizer.from_pretrained(LM); lm = AutoModelForCausalLM.from_pretrained(LM, torch_dtype=torch.bfloat16).to(dev).eval()
    uniq = sorted({c for name in meta for cs in meta[name]["cands"] for c in cs}); index = {c: i for i, c in enumerate(uniq)}
    embs = []
    for i in range(0, len(uniq), 256):
        t = tok(uniq[i:i + 256], return_tensors="pt", padding=True, add_special_tokens=False).to(dev)
        with torch.no_grad():
            h = lm.model(input_ids=t["input_ids"], attention_mask=t["attention_mask"]).last_hidden_state.float()
        m = t["attention_mask"][..., None].float(); embs.append(((h * m).sum(1) / m.sum(1)).half().cpu())
    torch.save(torch.cat(embs), OUT / "cap_emb.pt")
    for name in meta: meta[name]["cand_idx"] = [[index[c] for c in cs] for cs in meta[name]["cands"]]
    json.dump(meta, open(OUT / "meta.json", "w")); print("prep done", len(uniq), "unique captions", flush=True)


# ---------------------------------------------------------------- core (copy of the loop arm in scripts/claude_fewex_net.py, no vocabulary parts)
CLIP, WINDOW = 4, 1


class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.h = h; self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.out = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))
        self.br = nn.Parameter(torch.zeros(h, 2 * CLIP + 1)); self.bc = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))

    def forward(self, x, dr, dc):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        bias = self.br[:, dr] + self.bc[:, dc]
        far = (dc - CLIP).abs() > WINDOW
        narrow = torch.zeros(self.h, 1, 1, dtype=torch.bool, device=x.device); narrow[: self.h // 2] = True
        bias = bias.masked_fill(narrow & far, float("-inf")).unsqueeze(0).to(q.dtype)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=bias)
        x = x + self.out(a.transpose(1, 2).reshape(B, T, D))
        return x + self.mlp(self.ln2(x))


def offsets(H, W):
    r = torch.arange(H).repeat_interleave(W); c = torch.arange(W).repeat(H)
    return (r[:, None] - r[None, :]).clamp(-CLIP, CLIP) + CLIP, (c[:, None] - c[None, :]).clamp(-CLIP, CLIP) + CLIP


class Pipe(nn.Module):
    """image feats [B,64,768] (or None for blind) -> core -> 16 query states -> avg-pool pairs -> 8 prefix vectors -> LM width."""
    def __init__(self, enc_dim, lm_dim, blind=False):
        super().__init__()
        self.blind = blind
        self.adapter = GridAdapter(enc_dim, grid=(8, 8), hidden=32)
        self.query = nn.Parameter(torch.randn(NQ, 256))
        self.blocks = nn.ModuleList(Block(256, 8) for _ in range(2)); self.ln_state, self.ln_out = nn.LayerNorm(256), nn.LayerNorm(256)
        self.to_lm = nn.Linear(256, lm_dim)
        dr, dc = offsets(4, 4); n = NQ + (0 if blind else 64)
        er = torch.full((n, n), CLIP, dtype=torch.long); ec = er.clone(); er[:NQ, :NQ] = dr; ec[:NQ, :NQ] = dc  # notebook uses the neutral offset
        self.register_buffer("dr", er, persistent=False); self.register_buffer("dc", ec, persistent=False)

    def states(self, feats):
        B = feats.shape[0]; e = self.query[None].expand(B, -1, -1)
        if not self.blind: e = torch.cat((e, self.adapter(feats.float(), (8, 8), as_notebook=True)), 1)
        h = torch.zeros_like(e)
        for _ in range(ROUNDS):
            z = h + e
            for b in self.blocks: z = b(z, self.dr, self.dc)
            h = self.ln_state(z)
        return self.ln_out(h[:, :NQ])  # [B,16,256]: read from question positions only

    def forward(self, feats):
        z = self.states(feats)
        return self.to_lm(z.view(z.shape[0], 8, 2, 256).mean(2)), z.mean(1)  # 8 prefix vectors, pooled core state (read-out B)


# ---------------------------------------------------------------- train / eval
def load_lm():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(LM); lm = AutoModelForCausalLM.from_pretrained(LM, torch_dtype=torch.bfloat16).to(dev).eval()
    for p in lm.parameters(): p.requires_grad_(False)
    return tok, lm


def tokenize(tok, caps):
    ids = [tok(c, add_special_tokens=False)["input_ids"] + [tok.eos_token_id] for c in caps]
    T = max(map(len, ids)); x = torch.full((len(ids), T), tok.eos_token_id); m = torch.zeros(len(ids), T, dtype=torch.bool)
    for i, s in enumerate(ids): x[i, :len(s)] = torch.tensor(s); m[i, :len(s)] = True
    return x, m


def caption_loss(lm, prefix, ids, m):
    """token-mean caption loss (nats/token) given 8 prefix vectors; returns (sum, count)."""
    emb = lm.get_input_embeddings()(ids)
    x = torch.cat((prefix.to(emb.dtype), emb), 1)
    att = torch.cat((torch.ones(len(ids), 8, dtype=torch.bool, device=ids.device), m), 1)
    logits = lm(inputs_embeds=x, attention_mask=att).logits[:, 7:7 + ids.shape[1]].float()
    ce = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), ids.reshape(-1), reduction="none").view_as(ids)
    return (ce * m).sum(), m.sum()


@torch.no_grad()
def evaluate(pipe, lm, feats, ids, m, shuffle=False):
    pipe.eval(); tot = cnt = 0.0; zs = []
    for i in range(0, len(ids), 64):
        f = feats[i:i + 64].to(dev)
        if shuffle: f = feats[(torch.arange(i, i + len(f)) + 1) % len(feats)].to(dev)
        with torch.autocast(dev, dtype=torch.bfloat16): prefix, z = pipe(f)
        s, c = caption_loss(lm, prefix, ids[i:i + 64].to(dev), m[i:i + 64].to(dev)); tot += s.item(); cnt += c.item(); zs.append(z.float().cpu())
    return tot / cnt, torch.cat(zs)




class Head(nn.Module):
    def __init__(self, dz=256, dc=2048):
        super().__init__(); self.u, self.v = nn.Linear(dz, 256), nn.Linear(dc, 256); self.logit_scale = nn.Parameter(torch.tensor(math.log(20.0)))

    def forward(self, z, c):  # z [B,256], c [B,8,2048] -> [B,8]
        u = F.normalize(self.u(z), dim=-1); v = F.normalize(self.v(c), dim=-1)
        return self.logit_scale.exp() * (u[:, None] * v).sum(-1)


def train_head(ztr, meta_tr, E, seed):
    torch.manual_seed(seed); head = Head().to(dev); opt = torch.optim.AdamW(head.parameters(), 1e-3, weight_decay=0.01)
    mu, sd = ztr.mean(0, keepdim=True), ztr.std(0, keepdim=True) + 1e-5
    z = ((ztr - mu) / sd).to(dev); idx = torch.tensor(meta_tr["cand_idx"]).to(dev); y = torch.tensor(meta_tr["label"]).to(dev); E = E.to(dev)
    for ep in range(40):
        perm = torch.randperm(len(z), device=dev)
        for i in range(0, len(z), 256):
            b = perm[i:i + 256]; loss = F.cross_entropy(head(z[b], E[idx[b]].float()), y[b]); opt.zero_grad(); loss.backward(); opt.step()
    return head, mu, sd


@torch.no_grad()
def head_acc(head, mu, sd, z, meta_part, E):
    z = ((z - mu) / sd).to(dev); idx = torch.tensor(meta_part["cand_idx"]).to(dev); y = torch.tensor(meta_part["label"]).to(dev)
    return (head(z, E.to(dev)[idx].float()).argmax(-1) == y).float().mean().item()


def train_arm(arm, seed, tok, lm):
    meta = json.load(open(OUT / "meta.json")); E = torch.load(OUT / "cap_emb.pt")
    ftr, fhe = torch.load(OUT / "feats_train.pt"), torch.load(OUT / "feats_held.pt")
    itr, mtr = tokenize(tok, meta["train"]["captions"]); ihe, mhe = tokenize(tok, meta["held"]["captions"])
    torch.manual_seed(seed); random.seed(seed)
    pipe = Pipe(ftr.shape[-1], lm.config.hidden_size, blind=(arm == "blind")).to(dev)
    opt = torch.optim.AdamW(pipe.parameters(), LR, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1, (s + 1) / 100) * 0.5 * (1 + math.cos(math.pi * s / STEPS)))
    t0 = time.time(); log = []
    for step in range(STEPS):
        pipe.train(); b = torch.randint(0, len(ftr), (BS,)); f = ftr[b].to(dev)
        if arm == "shuf": f = f.roll(random.randint(1, BS - 1), 0)  # each caption sees another image's features
        with torch.autocast(dev, dtype=torch.bfloat16): prefix, _ = pipe(f)
        s, c = caption_loss(lm, prefix, itr[b].to(dev), mtr[b].to(dev)); loss = s / c
        opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(pipe.parameters(), 1.0); opt.step(); sched.step()
        if step % 250 == 0 or step == STEPS - 1: log.append((step, round(loss.item(), 4), round(time.time() - t0))); print(arm, seed, log[-1], flush=True)
    # A: held-out loss through the pipe
    res = {"arm": arm, "seed": seed, "steps": STEPS, "train_log": log}
    res["A_heldout_loss"], zh = evaluate(pipe, lm, fhe, ihe, mhe)
    res["A_heldout_loss_testshuffle"], zh_shuf = evaluate(pipe, lm, fhe, ihe, mhe, shuffle=True)
    _, ztr = evaluate(pipe, lm, ftr, itr, mtr)
    # B: head on the pooled core state, around the 8-vector pipe
    head, mu, sd = train_head(ztr, meta["train"], E, seed)
    res["B_train_acc"] = head_acc(head, mu, sd, ztr, meta["train"], E)
    res["B_heldout_acc"] = head_acc(head, mu, sd, zh, meta["held"], E)
    res["B_heldout_acc_testshuffle"] = head_acc(head, mu, sd, zh_shuf, meta["held"], E)
    res["params_trained"] = sum(p.numel() for p in pipe.parameters()); res["seconds"] = round(time.time() - t0)
    json.dump(res, open(OUT / f"res_{arm}_s{seed}.json", "w"), indent=1); print(json.dumps({k: v for k, v in res.items() if k != "train_log"}), flush=True)


def report():
    R = {(a, s): json.load(open(OUT / f"res_{a}_s{s}.json")) for a in ("real", "shuf", "blind") for s in (0, 1) if (OUT / f"res_{a}_s{s}.json").exists()}
    rows, verdict = [], {}
    for s in (0, 1):
        if ("real", s) not in R: continue
        r = R[("real", s)]
        cl = {"shuffled-trained": R[("shuf", s)]["A_heldout_loss"], "blind": R[("blind", s)]["A_heldout_loss"], "real, test-time shuffle": r["A_heldout_loss_testshuffle"]}
        ca = {"shuffled-trained": R[("shuf", s)]["B_heldout_acc"], "blind": R[("blind", s)]["B_heldout_acc"], "real, test-time shuffle": r["B_heldout_acc_testshuffle"]}
        gapA = min(cl.values()) - r["A_heldout_loss"]; gapB = r["B_heldout_acc"] - max(ca.values())
        A = "PASS" if gapA >= 0.15 else ("WRONG" if gapA <= 0.05 else "inconclusive")
        Bv = "PASS" if (r["B_heldout_acc"] >= 0.5 and gapB >= 0.25) else ("WRONG" if gapB <= 0.10 else "inconclusive")
        verdict[s] = {"A_real_loss": r["A_heldout_loss"], "A_controls": cl, "A_gap_nats": gapA, "A": A, "B_real_acc": r["B_heldout_acc"], "B_controls": ca, "B_gap_pts": 100 * gapB, "B": Bv}
    both = lambda k: all(v[k] == "PASS" for v in verdict.values()) and len(verdict) == 2
    out = {"seeds": verdict, "A_pass_both_seeds": both("A"), "B_pass_both_seeds": both("B"), "raw": {f"{a}_s{s}": {k: v for k, v in r.items() if k != "train_log"} for (a, s), r in R.items()}}
    json.dump(out, open(OUT / "results.json", "w"), indent=1); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("--arms", nargs="*", default=["real", "shuf", "blind"]); ap.add_argument("--seeds", nargs="*", type=int, default=[0, 1])
    a = ap.parse_args()
    if a.cmd == "prep": prep()
    elif a.cmd == "train":
        tok, lm = load_lm()
        for seed in a.seeds:
            for arm in a.arms:
                if not (OUT / f"res_{arm}_s{seed}.json").exists(): train_arm(arm, seed, tok, lm)
    elif a.cmd == "report": report()
