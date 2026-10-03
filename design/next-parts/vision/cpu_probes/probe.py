"""V0 CPU probes on real frozen SigLIP2-B/16 features (marks fixed in MARKS.md before running).

Synthetic images -> frozen encoder -> {last, penultimate} layer patch grid -> pooling -> optional per-patch PCA
-> ridge linear probe. Linear probes give a lower bound on what an adapter + core could extract.
CPU only. Usage: python probe.py [--n-train 1500 --n-test 500] ; writes results.json next to this file.
"""
from __future__ import annotations
import argparse, json, math, random, time, hashlib
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
MODEL = "google/siglip2-base-patch16-256"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
RED, BLUE = (220, 30, 30), (30, 60, 220)


def _bg(rng):
    g = rng.randint(200, 245)
    return (g, g + rng.randint(-8, 8), g + rng.randint(-8, 8))


def _place(rng, sizes, taken, margin=2):
    for _ in range(500):
        s = rng.choice(sizes)
        x, y = rng.randint(4, 252 - s), rng.randint(4, 252 - s)
        box = (x - margin, y - margin, x + s + margin, y + s + margin)
        if all(box[2] < t[0] or box[0] > t[2] or box[3] < t[1] or box[1] > t[3] for t in taken):
            taken.append(box)
            return x, y, s
    raise RuntimeError("could not place shape")


def _shape(d, rng, x, y, s, color):
    (d.ellipse if rng.random() < .5 else d.rectangle)((x, y, x + s, y + s), fill=color)


def make(task, rng):
    img = Image.new("RGB", (256, 256), _bg(rng)); d = ImageDraw.Draw(img); taken = []
    if task == "count":
        k = rng.randint(1, 9)
        for _ in range(k):
            x, y, s = _place(rng, range(8, 15), taken)
            _shape(d, rng, x, y, s, tuple(rng.randint(0, 160) for _ in range(3)))
        return img, k - 1
    if task == "relation":
        while True:
            a = _place(rng, range(10, 20), taken); b = _place(rng, range(10, 20), taken)
            if abs((a[0] + a[2] / 2) - (b[0] + b[2] / 2)) >= 20: break
            taken.clear()
        _shape(d, rng, *a, RED); _shape(d, rng, *b, BLUE)
        return img, int(a[0] + a[2] / 2 < b[0] + b[2] / 2)
    if task == "more":
        while True:
            r, b = rng.randint(2, 7), rng.randint(2, 7)
            if r != b: break
        for c, n in ((RED, r), (BLUE, b)):
            for _ in range(n):
                _shape(d, rng, *_place(rng, range(8, 13), taken), c)
        return img, int(r > b)
    if task == "digit":
        for _ in range(3):  # clutter
            _shape(d, rng, *_place(rng, range(8, 15), taken), (150, 150, 150))
        k = rng.randint(0, 9); font = ImageFont.truetype(FONT, 12)  # cap height ~9 px
        x, y, _ = _place(rng, [12], taken)
        d.text((x, y), str(k), fill=(20, 20, 20), font=font)
        return img, k
    raise ValueError(task)


@torch.no_grad()
def features(model, proc, imgs, bs=32):
    last, pen, pix = [], [], []
    for i in range(0, len(imgs), bs):
        batch = imgs[i:i + bs]
        inp = proc(images=batch, return_tensors="pt")
        out = model(pixel_values=inp["pixel_values"], output_hidden_states=True)
        hs = out.hidden_states  # embeddings + each layer (pre post-layernorm)
        last.append(out.last_hidden_state.half()); pen.append(hs[-2].half())
        pix.append(torch.stack([torch.from_numpy(np.asarray(im.resize((32, 32)), dtype=np.float32) / 255) for im in batch]).flatten(1))
    return torch.cat(last), torch.cat(pen), torch.cat(pix)


def pool(x, g):
    b, n, d = x.shape; s = int(math.isqrt(n))
    x = x.float().reshape(b, s, s, d).permute(0, 3, 1, 2)
    if g != s: x = F.adaptive_avg_pool2d(x, g)
    return x.permute(0, 2, 3, 1).reshape(b, g * g, d)


def pca_patch(tr, te, k, seed=0):
    flat = tr.reshape(-1, tr.shape[-1])
    idx = torch.randperm(len(flat), generator=torch.Generator().manual_seed(seed))[:20000]
    mu = flat[idx].mean(0)
    _, _, v = torch.pca_lowrank(flat[idx] - mu, q=k, center=False)
    return (tr - mu) @ v[:, :k], (te - mu) @ v[:, :k]


def ridge(xtr, ytr, xte, yte, ncls):
    xtr, xte = xtr.flatten(1).float(), xte.flatten(1).float()
    mu, sd = xtr.mean(0), xtr.std(0) + 1e-6
    xtr, xte = (xtr - mu) / sd, (xte - mu) / sd
    Y = F.one_hot(ytr, ncls).double() * 2 - 1
    n = len(xtr); cut = int(n * .8)
    K = (xtr @ xtr.T).double(); scale = K.trace() / n
    best = None
    for lam in (1e-3, 1e-2, 1e-1, 1, 10):  # pick lambda on a split of TRAIN only
        a = torch.linalg.solve(K[:cut, :cut] + lam * scale * torch.eye(cut, dtype=K.dtype), Y[:cut])
        acc = ((K[cut:, :cut] @ a).argmax(1) == ytr[cut:]).double().mean().item()
        if best is None or acc > best[0]: best = (acc, lam)
    a = torch.linalg.solve(K + best[1] * scale * torch.eye(n, dtype=K.dtype), Y)
    return (((xte @ xtr.T).double() @ a).argmax(1) == yte).double().mean().item(), best[1]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n-train", type=int, default=1500); ap.add_argument("--n-test", type=int, default=500)
    a = ap.parse_args()
    from transformers import AutoModel, AutoProcessor
    torch.manual_seed(0); torch.set_num_threads(4)
    full = AutoModel.from_pretrained(MODEL); model = full.vision_model.eval(); proc = AutoProcessor.from_pretrained(MODEL)
    print("vision params", sum(p.numel() for p in model.parameters()), flush=True)
    ncls = {"count": 9, "relation": 2, "more": 2, "digit": 10}
    res = {"model": MODEL, "n_train": a.n_train, "n_test": a.n_test,
           "marks_sha256": hashlib.sha256((HERE / "MARKS.md").read_bytes()).hexdigest(), "tasks": {}}
    for task in ncls:
        t0 = time.time()
        rtr, rte = random.Random(f"train-{task}"), random.Random(f"test-{task}")
        tr = [make(task, rtr) for _ in range(a.n_train)]; te = [make(task, rte) for _ in range(a.n_test)]
        if task == "count": tr[0][0].save(HERE / "example_count.png"); te[0][0].save(HERE / "example_test_count.png")
        if task == "digit": tr[0][0].save(HERE / "example_digit.png")
        ytr = torch.tensor([y for _, y in tr]); yte = torch.tensor([y for _, y in te])
        Ltr, Ptr, Xtr = features(model, proc, [i for i, _ in tr]); Lte, Pte, Xte = features(model, proc, [i for i, _ in te])
        r = {"pixels32": ridge(Xtr, ytr, Xte, yte, ncls[task])[0]}
        for lname, ftr, fte in (("last", Ltr, Lte), ("pen", Ptr, Pte)):
            for g in (16, 8, 4):
                ptr, pte = pool(ftr, g), pool(fte, g)
                r[f"{lname}_g{g}_full"] = ridge(ptr, ytr, pte, yte, ncls[task])[0]
                if g == 8:
                    for k in (128, 32):
                        qtr, qte = pca_patch(ptr, pte, k)
                        r[f"{lname}_g{g}_pca{k}"] = ridge(qtr, ytr, qte, yte, ncls[task])[0]
        r["seconds"] = round(time.time() - t0, 1)
        res["tasks"][task] = r
        print(task, json.dumps({k: round(v, 3) for k, v in r.items()}), flush=True)
        (HERE / "results.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
