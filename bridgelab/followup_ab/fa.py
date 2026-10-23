"""Follow-up runs: python -m bridgelab.followup_ab.fa --name base --seed 0 [--steps N] [--loops N] [--exch K] [--sender reg0|full] [--auxv W]"""
from __future__ import annotations
import argparse, json, math, time
from pathlib import Path
import torch
import torch.nn.functional as F
from torch import nn
from bridgelab import task
from bridgelab.eval import linear_probe
from bridgelab.models import Module, Pooled, _zero_linear, rms, ablate
from bridgelab.run import CURRICULUM, SWAPS

RES = Path(__file__).parent / "results"


class ModuleN(Module):
    """bridgelab Module with n_loops loop embeddings."""
    def __init__(self, vocab, L, d, n_loops, R=4, layers=2, heads=4):
        super().__init__(vocab, L, d, R, layers, heads)
        self.loop = nn.Parameter(torch.randn(n_loops, d) * 0.02)


class PooledFull(Pooled):
    """Sender: one learned query attends over A's whole sequence (rows + registers); then rms -> zero-init Linear -> added to receiver registers."""
    def __init__(self, ds, dr, R, layers, heads=4):
        super().__init__(ds, dr, R, layers)
        self.q, self.ln = nn.Parameter(torch.randn(1, 1, ds) * 0.02), nn.LayerNorm(ds)
        self.attn = nn.MultiheadAttention(ds, heads, batch_first=True)

    def send(self, x, L):
        h = self.ln(x)
        s, _ = self.attn(self.q.expand(len(x), -1, -1), h, h, need_weights=False)
        return self.proj(rms(s[:, 0]))


class Pair2(nn.Module):
    def __init__(self, sender="reg0", loops=2, exch=0, auxv=0.0, dA=64, dB=96, R=4, layers=2):
        super().__init__()
        self.loops, self.exch, self.auxv = loops, exch, auxv
        self.A = ModuleN(task.VOCAB_A, task.LEN_A, dA, loops, R, layers)
        self.B = ModuleN(task.VOCAB_B, task.LEN_B, dB, loops, R, layers)
        cls = PooledFull if sender == "full" else Pooled
        self.ab, self.ba = cls(dA, dB, R, layers), cls(dB, dA, R, layers)
        self.vhead = nn.Sequential(nn.LayerNorm(dA), nn.Linear(dA, task.NV))   # only used if auxv > 0

    def forward(self, xa, xb, mode="real", gen=None, ret=False):
        ha, hb = self.A.embed(xa), self.B.embed(xb)
        st = None
        for l in range(self.loops):
            ha, hb = self.A.run(ha, l), self.B.run(hb, l)
            if l == self.exch:
                st = ha                                           # A's state at send time
                m_ab, m_ba = self.ab.send(ha, self.A.L), self.ba.send(hb, self.B.L)
                raw = {"ab": m_ab, "ba": m_ba}
                m_ab, m_ba = ablate(m_ab, mode, gen), ablate(m_ba, mode, gen)
                ha, _ = self.ba.receive(ha, m_ba, self.A.L)
                hb, _ = self.ab.receive(hb, m_ab, self.B.L)
        la, lb = self.A.logits(ha), self.B.logits(hb)
        return (la, lb, raw, st) if ret else (la, lb)


def dev(d, device):
    return {k: v.to(device) for k, v in d.items()}


@torch.no_grad()
def accuracy(model, d, mode, bs=500):
    model.eval()
    gen = torch.Generator().manual_seed(7)
    n, hits = len(d["yA"]), torch.zeros(2)
    for i in range(0, n, bs):
        sl = slice(i, i + bs)
        la, lb = model(d["xa"][sl], d["xb"][sl], mode, None)
        hits += torch.tensor([(la.argmax(1) == d["yA"][sl]).sum().item(), (lb.argmax(1) == d["yB"][sl]).sum().item()], dtype=torch.float)
    return {"A": float(hits[0] / n), "B": float(hits[1] / n)}


@torch.no_grad()
def feats(model, d, bs=500):
    model.eval()
    out = {"msg": [], "reg0": [], "regs": [], "seqmean": [], "bag": []}
    for i in range(0, len(d["yA"]), bs):
        _, _, raw, st = model(d["xa"][i:i + bs], d["xb"][i:i + bs], "real", None, True)
        L = model.A.L
        out["msg"].append(raw["ab"].flatten(1)); out["reg0"].append(st[:, L]); out["regs"].append(st[:, L:].flatten(1)); out["seqmean"].append(st[:, :L].mean(1))
        xa = d["xa"][i:i + bs]; out["bag"].append(F.one_hot(xa[:, 1:2 * task.K:2] - task.VAL0, task.NV).sum(1).float())   # control: counts of the 8 value tokens in A's input, no look-up
    return {k: torch.cat(v).cpu() for k, v in out.items()}


def evaluate(model, seed, device):
    test = dev(task.make_test(False), device)
    res = {"acc": {m: accuracy(model, test, m) for m in ("real", "off", "shuffle", "mean")}}
    tr = dev(task.make_batch(20000, torch.Generator().manual_seed(999 + seed)), device)
    ftr, fte = feats(model, tr), feats(model, test)
    v_tr, v_te = tr["v"].cpu(), test["v"].cpu()
    res["probe_v"] = {k: linear_probe(ftr[k], v_tr, fte[k], v_te, task.NV) for k in ftr}
    return res


def train(a, device):
    torch.manual_seed(a.seed)
    model = Pair2(a.sender, a.loops, a.exch, a.auxv).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.01)
    gen = torch.Generator().manual_seed(1000 + a.seed)
    steps, curve, t0 = a.steps, [], time.time()
    for step in range(steps):
        for g in opt.param_groups:
            g["lr"] = 1e-3 * min(1.0, (step + 1) / 200) * (0.5 * (1 + math.cos(math.pi * step / steps)) * 0.95 + 0.05)
        d = dev(task.make_batch(64, gen, max_swaps=int(SWAPS * step / (CURRICULUM * steps)) if step < CURRICULUM * steps else None), device)
        la, lb, _, st = model(d["xa"], d["xb"], "real", None, True)
        loss = F.cross_entropy(la, d["yA"]) + F.cross_entropy(lb, d["yB"])
        if a.auxv > 0:
            loss = loss + a.auxv * F.cross_entropy(model.vhead(st[:, model.A.L]), d["v"])
        opt.zero_grad(set_to_none=True); loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()
        if step % 1000 == 0 or step == steps - 1:
            accB = float((lb.argmax(1) == d["yB"]).float().mean()); accA = float((la.argmax(1) == d["yA"]).float().mean())
            curve.append((step, round(loss.item(), 3), accA, accB))
            print(f"{a.name} s{a.seed} step {step} loss {loss.item():.3f} accA {accA:.2f} accB {accB:.2f} t {time.time()-t0:.0f}s", flush=True)
    return model, curve, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--steps", type=int, default=8000); ap.add_argument("--loops", type=int, default=2)
    ap.add_argument("--exch", type=int, default=0); ap.add_argument("--sender", default="reg0")
    ap.add_argument("--auxv", type=float, default=0.0); ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--out", default=str(RES))
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, curve, secs = train(a, device)
    res = {"name": a.name, "seed": a.seed, "cfg": vars(a), "device": device, "train_s": secs, "curve": curve, **evaluate(model, a.seed, device)}
    if a.auxv > 0:
        with torch.no_grad():
            t = dev(task.make_test(False), device); model.eval()
            _, _, _, st = model(t["xa"], t["xb"], "real", None, True)
            res["aux_head_v_acc"] = float((model.vhead(st[:, model.A.L]).argmax(1) == t["v"]).float().mean())
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / f"{a.name}_s{a.seed}.json").write_text(json.dumps(res, indent=1))
    print("RESULT " + json.dumps({"name": a.name, "seed": a.seed, "acc": res["acc"], "probe_v": res["probe_v"]}), flush=True)


if __name__ == "__main__":
    main()
