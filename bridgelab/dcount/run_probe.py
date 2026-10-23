"""Q4: where does the count information die?  Frozen D (+ saved Bridge, frozen_ctx) on Q5 count items; capture features at several places, then fit
a linear (multinomial logistic) probe train->dev for the true count c in 0..4.  Train features come from village TRAIN visits, test from DEV visits.
Places: reader/question rows (before think), question rows after think, fetched card rows (mean), final registers, decoder hidden at the first answer
position, mean store-card value of the GOLD evidence lines (oracle fetch), gold-line count only (metadata), and D's own answer.
  python run_probe.py --train-n 1800 --dev-n 700"""
import argparse, json, time, random, collections
from cap import *
import torch.nn.functional as F

ap = argparse.ArgumentParser()
ap.add_argument("--train-n", type=int, default=1800)
ap.add_argument("--dev-n", type=int, default=700)
ap.add_argument("--bridge", default="on")
ap.add_argument("--out", default="probe.json")
a = ap.parse_args()
T0 = time.time()
from bridgelab.real import data as D, dmsg
from learnlab import step1
from premonition import preprocess

tok, splits = D.open_village(ROOT, str(TOK), splits=("train", "dev"), workers=2)
d, bridge = load(a.bridge == "on")
stops = sorted(step1.stop_ids(tok)[0])
num_ids = [tok.token_to_id(" " + w) for w in NUM]
sub = {}
for s, n, seed in (("train", a.train_n, 11), ("dev", a.dev_n, 12)):
    it = splits[s]
    idx = sorted(random.Random(seed).sample(range(len(it)), min(n, len(it))))
    sub[s] = it.take(idx)
print({s: len(v) for s, v in sub.items()}, round(time.time() - T0), flush=True)


def mean_valid(x, valid):
    w = valid.float().unsqueeze(-1)
    return (x * w).sum(1) / w.sum(1).clamp_min(1)


@torch.no_grad()
def extract(items):
    N = len(items)
    F_ = {k: [None] * N for k in ("q0", "q1", "cards", "regs", "reg0", "dec_h", "gold_cards", "meta")}
    pred = [""] * N; fetched_gold = [0] * N; gold_n = [0] * N
    stash = {}
    o_bs = d.build_store
    def bs(hidden, batch):
        st = o_bs(hidden, batch); stash["store"] = st; return st
    d.build_store = bs
    done = 0
    try:
        for order, batch in dmsg.item_batches(items, None, 55000, 48):
            with capture(d, num_ids) as box:
                ans = d.answer(batch, stop=stops)
            st = stash["store"]
            for k, i in enumerate(order):
                F_["q0"][i] = mean_valid(box["q0"][k:k+1], box["qvalid"][k:k+1])[0]
                F_["q1"][i] = mean_valid(box["q1"][k:k+1], box["qvalid"][k:k+1])[0]
                cm = mean_valid(box["cards"][k:k+1], box["cvalid"][k:k+1])[0]
                F_["cards"][i] = torch.cat([cm, box["cvalid"][k].float().sum().view(1)])
                F_["regs"][i] = box["regs"][k].flatten()
                F_["reg0"][i] = box["regs"][k, 0]
                F_["dec_h"][i] = box["dec_h"][k]
                gl = [int(x) for x in batch.gold_lines[k] if int(x) >= 0]
                v = int(batch.q_visit[k])
                gold_n[i] = len(gl)
                fetched_gold[i] = int(sum(bool(ans.fetched[k, g]) for g in gl))
                F_["gold_cards"][i] = st.values[v, gl].float().mean(0) if gl else torch.zeros(d.config.d_model)
                ids = ans.ids()[k]
                pred[i] = preprocess.prediction_text(ids, batch.names[v], tok)[0]
            done += len(order)
    finally:
        d.build_store = o_bs
    out = {k: torch.stack(v) for k, v in F_.items() if k != "meta"}
    out["d_int"] = torch.tensor([D.word_to_int(p) for p in pred])
    out["gold_n"] = torch.tensor(gold_n); out["fetched_gold"] = torch.tensor(fetched_gold)
    return out

feats = {}
for s in ("train", "dev"):
    feats[s] = extract(sub[s]); print("extracted", s, round(time.time() - T0), flush=True)
    torch.save(feats[s], Path(__file__).parent / f"feats_{s}_{a.bridge}.pt")

def fit(xtr, ytr, xte, yte, wds=(1e-3, 1e-2, 1e-1), ncls=5, iters=200):
    xtr, xte = xtr.float(), xte.float()
    mu, sd = xtr.mean(0), xtr.std(0).clamp(min=1e-6)
    xtr, xte = (xtr - mu) / sd, (xte - mu) / sd
    n = len(xtr); perm = torch.randperm(n, generator=torch.Generator().manual_seed(0)); cut = int(n * 0.8)
    def run(xa, ya, wd):
        W = torch.zeros(xa.shape[1], ncls, requires_grad=True); b = torch.zeros(ncls, requires_grad=True)
        opt = torch.optim.LBFGS([W, b], lr=1.0, max_iter=iters, line_search_fn="strong_wolfe")
        def cl():
            opt.zero_grad(); l = F.cross_entropy(xa @ W + b, ya) + wd * (W ** 2).sum(); l.backward(); return l
        opt.step(cl); return W.detach(), b.detach()
    best, bw = -1, wds[0]
    for wd in wds:                       # choose the regulariser on a held-out part of TRAIN only
        W, b = run(xtr[perm[:cut]], ytr[perm[:cut]], wd)
        acc = float(((xtr[perm[cut:]] @ W + b).argmax(1) == ytr[perm[cut:]]).float().mean())
        if acc > best: best, bw = acc, wd
    W, b = run(xtr, ytr, bw)
    pred = (xte @ W + b).argmax(1)
    return dict(acc=round(float((pred == yte).float().mean()), 4), wd=bw, pred_hist=torch.bincount(pred, minlength=ncls).tolist())

ytr, yte = sub["train"].c, sub["dev"].c
prior = int(torch.bincount(ytr).argmax())
res = dict(n_train=len(ytr), n_dev=len(yte), c_hist_dev=torch.bincount(yte, minlength=5).tolist(), c_hist_train=torch.bincount(ytr, minlength=5).tolist(),
           prior_acc=round(float((yte == prior).float().mean()), 4), bridge=a.bridge)
fd = feats["dev"]
res["d_own_acc"] = round(float((fd["d_int"] == yte).float().mean()), 4)
res["d_own_answer_hist"] = torch.bincount(fd["d_int"].clamp(min=-1) + 1, minlength=6).tolist()   # idx0 = non-number, then 0..4
res["d_own_acc_train_visits"] = round(float((feats["train"]["d_int"] == ytr).float().mean()), 4)
res["gold_lines_fetched_frac_dev"] = round(float(fd["fetched_gold"].sum() / fd["gold_n"].sum().clamp_min(1)), 4)
res["gold_all_fetched_dev"] = round(float((fd["fetched_gold"] == fd["gold_n"]).float().mean()), 4)
# D acc by true count
res["d_acc_by_true_count_dev"] = {int(c): [round(float((fd["d_int"][yte == c] == c).float().mean()), 3), int((yte == c).sum())] for c in range(5) if (yte == c).any()}
res["probes"] = {}
for name in ("q0", "q1", "cards", "reg0", "regs", "dec_h", "gold_cards"):
    res["probes"][name] = fit(feats["train"][name], ytr, fd[name], yte)
    print(name, res["probes"][name], round(time.time() - T0), flush=True)
res["probes"]["gold_line_count_only"] = fit(F.one_hot(feats["train"]["gold_n"].clamp(max=12), 13).float(), ytr, F.one_hot(fd["gold_n"].clamp(max=12), 13).float(), yte)
res["probes"]["shuffled_labels_regs"] = fit(feats["train"]["regs"], ytr[torch.randperm(len(ytr), generator=torch.Generator().manual_seed(1))], fd["regs"], yte)
res["probes"]["dec_h_plus_regs"] = fit(torch.cat([feats["train"]["dec_h"], feats["train"]["regs"]], 1), ytr, torch.cat([fd["dec_h"], fd["regs"]], 1), yte)
# same probes split by bank
bk = sub["dev"].bank
res["seconds"] = round(time.time() - T0)
json.dump(res, open(Path(__file__).parent / a.out, "w"), indent=1)
print(json.dumps(res, indent=1))
