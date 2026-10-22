"""P6: can pooled SigLIP2 features read 9 small digits at once (a Minecraft-hotbar-like row)? Marks: MARKS.md addendum A."""
import json, random, time
import torch, torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont
from probe import HERE, MODEL, FONT, _bg, _place, _shape, features, pool, pca_patch


def make(rng):
    img = Image.new("RGB", (256, 256), _bg(rng)); d = ImageDraw.Draw(img); taken = [(40, 222, 216, 250)]
    for _ in range(4):
        _shape(d, rng, *_place(rng, range(8, 15), taken), (150, 150, 150))
    font = ImageFont.truetype(FONT, 12); ys = []
    for s in range(9):
        x = 47 + 18 * s; d.rectangle((x, 228, x + 16, 244), outline=(90, 90, 90))
        k = rng.randint(0, 9); ys.append(k); d.text((x + 4, 230), str(k), fill=(20, 20, 20), font=font)
    return img, ys


def ridge_multi(xtr, ytr, xte, yte, ncls=10):
    xtr, xte = xtr.flatten(1).float(), xte.flatten(1).float()
    mu, sd = xtr.mean(0), xtr.std(0) + 1e-6; xtr, xte = (xtr - mu) / sd, (xte - mu) / sd
    K = (xtr @ xtr.T).double(); Kte = (xte @ xtr.T).double(); n = len(K); cut = int(n * .8); sc = K.trace() / n
    accs = []
    for j in range(ytr.shape[1]):
        Y = F.one_hot(ytr[:, j], ncls).double() * 2 - 1
        lam = max((1e-3, 1e-2, 1e-1, 1, 10), key=lambda l: ((K[cut:, :cut] @ torch.linalg.solve(
            K[:cut, :cut] + l * sc * torch.eye(cut, dtype=K.dtype), Y[:cut])).argmax(1) == ytr[cut:, j]).double().mean())
        a = torch.linalg.solve(K + lam * sc * torch.eye(n, dtype=K.dtype), Y)
        accs.append(((Kte @ a).argmax(1) == yte[:, j]).double().mean().item())
    return sum(accs) / len(accs), accs


def main(n_train=1500, n_test=500):
    from transformers import AutoModel, AutoProcessor
    torch.set_num_threads(4); t0 = time.time()
    model = AutoModel.from_pretrained(MODEL).vision_model.eval(); proc = AutoProcessor.from_pretrained(MODEL)
    rtr, rte = random.Random("train-hotbar"), random.Random("test-hotbar")
    tr = [make(rtr) for _ in range(n_train)]; te = [make(rte) for _ in range(n_test)]
    tr[0][0].save(HERE / "example_hotbar.png")
    ytr = torch.tensor([y for _, y in tr]); yte = torch.tensor([y for _, y in te])
    Ltr, _, Xtr = features(model, proc, [i for i, _ in tr]); Lte, _, Xte = features(model, proc, [i for i, _ in te])
    r = {"pixels32": ridge_multi(Xtr, ytr, Xte, yte)}
    for g in (16, 8, 4):
        r[f"last_g{g}_full"] = ridge_multi(pool(Ltr, g), ytr, pool(Lte, g), yte)
    qtr, qte = pca_patch(pool(Ltr, 8), pool(Lte, 8), 32); r["last_g8_pca32"] = ridge_multi(qtr, ytr, qte, yte)
    out = {k: {"mean": round(v[0], 3), "per_slot": [round(a, 3) for a in v[1]]} for k, v in r.items()}
    out["seconds"] = round(time.time() - t0, 1)
    print(json.dumps(out), flush=True); (HERE / "results_hotbar.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
