#!/usr/bin/env python3
"""dir-g2 (G builder thread, 2026-09-29): retrain ONLY the check (halt) head of a frozen test-G net, on the net's own tries labelled by
the exact code checker, and see whether the new head picks the right one of the 4 tries better.

Marks and design (sealed before this file was written): artifacts/claude-dir-g2-check-20260929/{PASSMARKS,DESIGN}.md.
Parent: scripts/claude_dir_g_run.py (imported, not edited) and the G nets g-s13, g-s14 (final.pt, kept off git).

  python -B scripts/claude_dir_g2_run.py feats --ckpt final.pt --out F.pt [--seed 1]         train + dev features (no test file)
  python -B scripts/claude_dir_g2_run.py train-head --feats F.pt --seed S [--shuffle] --out head.pt
  python -B scripts/claude_dir_g2_run.py eval --ckpt final.pt --heads h1.pt h2.pt ... --tests artifacts/claude-rsn358i-20260926/tests --out T.json
  python -B scripts/claude_dir_g2_run.py selftest

Data for the head (DESIGN.md section 3): per item and stream, 6 rounds drawn at random from the 48; example = (mean over cells of
ln_out(state) at that round, label). Label = 1 iff the exact checker (any valid answer) accepts the answer decoded from that state.
Items: 24,000 wide-pool numbers4 pairs + 6,000 sums4 + 6,000 grids5 for training; a separate dev set of 3,000 numbers4 pairs + 1,000
sums4 + 1,000 grids5. Head: fresh Linear(512, 1) (the sealed head's shape). The net is never changed.
Test use: the sealed stop rule per stream uses the OLD head (so the 4 answers are exactly G's); the new head's probability at each stop
picks among the 4. Reported only: S_pick_full (new head also drives the stop rule) and P192 (new-head argmax over 4 streams x 48 rounds).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_g_run as G  # noqa: E402  (the sealed G runner; imports the sealed 358u chain)

R, E, H2 = G.R, G.E, G.H2
stop_round = G.stop_round
ROUNDS_PER = 6
N_ROUNDS = R.TEST_ROUNDS
TRAIN_N = {"numbers4": 24000, "sums4": 6000, "grids5": 6000}
DEV_N = {"numbers4": 3000, "sums4": 1000, "grids5": 1000}
HEAD_EPOCHS, HEAD_BS, HEAD_LR, HEAD_WD = 8, 4096, 3e-3, 0.01
AUC_BAR = 0.70


# ---------------- rounds with features ----------------
@torch.no_grad()
def rounds_with_feats(net, t, s, env, n=N_ROUNDS):
    """like GNet.stream_rounds, plus the halt head's input at every round: preds [K,B,n,T], old halt prob [K,B,n], feats [K,B,n,d]"""
    e, (dr, dc) = net.embed(t, s, env)
    B, T, _ = e.shape
    K = net.K
    eK = e.repeat(K, 1, 1)
    h = net.h0(range(K), B, T)
    preds, qs, fs = [], [], []
    for _ in range(n):
        h = net.step(h, eK, dr, dc)
        z = net.ln_out(h)
        preds.append(net.head(z).argmax(-1))
        f = z.mean(1)
        fs.append(f)
        qs.append(torch.sigmoid(net.halt(f).squeeze(-1).float()))
    d = fs[0].shape[-1]
    return (torch.stack(preds, 1).view(K, B, n, T), torch.stack(qs, 1).view(K, B, n), torch.stack(fs, 1).view(K, B, n, d))


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def by_shape(items):
    """batches of items with the same token shape (kinds differ in shape), for one forward each"""
    groups = {}
    for i, it in enumerate(items):
        groups.setdefault((it.env, it.size, len(it.tokens), len(it.tokens[0])), []).append(i)
    return list(groups.values())


# ---------------- data ----------------
def make_items(seed):
    """(train items by kind, dev items by kind), from fresh generators; numbers4 from the wide pool (0 held-out hands)"""
    practice, _ = H2.pools()
    rng = random.Random(seed * 1000 + 17)
    need = TRAIN_N["numbers4"] + DEV_N["numbers4"]
    pairs = rng.sample(practice, need)
    nrng = random.Random(seed * 1000 + 18)
    num = [E.number_item(nrng, h, t, s) for h, t, s in pairs]
    rs, rg = random.Random(seed * 1000 + 19), random.Random(seed * 1000 + 20)
    sums = [E.make_sum(rs, 4) for _ in range(TRAIN_N["sums4"] + DEV_N["sums4"])]
    grids = [E.latin_item(rg, *E.make_latin_base(rg, 5)) for _ in range(TRAIN_N["grids5"] + DEV_N["grids5"])]
    tr, dv = {}, {}
    for name, items in (("numbers4", num), ("sums4", sums), ("grids5", grids)):
        tr[name], dv[name] = items[:TRAIN_N[name]], items[TRAIN_N[name]:]
    return tr, dv


@torch.no_grad()
def collect(net, items, device, seed, bs=100):
    """X [N, d] fp16, y [N] uint8, stream [N], item [N]: ROUNDS_PER random rounds per (item, stream)"""
    net.eval()
    rng = random.Random(seed)
    X, Y, S, I = [], [], [], []
    for grp in by_shape(items):
        for i in range(0, len(grp), bs):
            ids = grp[i:i + bs]
            chunk = [items[j] for j in ids]
            t, s, _, env = R.tensors(chunk, device)
            preds, _, feats = rounds_with_feats(net, t, s, env)
            preds = preds.cpu()
            for b, (j, it) in enumerate(zip(ids, chunk)):
                for k in range(net.K):
                    for r in rng.sample(range(N_ROUNDS), ROUNDS_PER):
                        Y.append(int(bool(E.check(it, R.grid_of(preds[k, b, r].tolist(), it)))))
                        S.append(k); I.append(j)
                        X.append(feats[k, b, r].half().cpu())
    return {"X": torch.stack(X), "y": torch.tensor(Y, dtype=torch.uint8), "stream": torch.tensor(S), "item": torch.tensor(I)}


def make_feats(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = G.g_load(a.ckpt, device)
    tr, dv = make_items(a.seed)
    out = {"ckpt_sha256": sha256_file(a.ckpt), "seed": a.seed, "rounds_per": ROUNDS_PER, "train": {}, "dev": {}}
    for split, sets, off in (("train", tr, 0), ("dev", dv, 1)):
        for name, items in sets.items():
            out[split][name] = collect(net, items, device, a.seed * 10 + off + (3 if name == "sums4" else 6 if name == "grids5" else 0))
            y = out[split][name]["y"]
            print(f"{split} {name}: {len(items)} items, {len(y)} examples, {int(y.sum())} right ({y.float().mean():.3f})", flush=True)
    torch.save(out, a.out)


# ---------------- head ----------------
def auc(score, y):
    """rank AUC of score for label y (ties get the average rank); nan when one class is empty"""
    y = y.bool()
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = score.argsort()
    ranks = torch.empty(len(score), dtype=torch.float64)
    sorted_s = score[order]
    r = torch.arange(1, len(score) + 1, dtype=torch.float64)
    i = 0
    n = len(score)
    while i < n:                                             # average rank for ties
        j = i
        while j + 1 < n and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        r[i:j + 1] = (i + 1 + j + 1) / 2.0
        i = j + 1
    ranks[order] = r
    return float((ranks[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def train_head(a):
    d = torch.load(a.feats)
    torch.manual_seed(a.seed)
    X = torch.cat([d["train"][k]["X"] for k in TRAIN_N]).float()
    y = torch.cat([d["train"][k]["y"] for k in TRAIN_N]).float()
    if a.shuffle:                                             # control: same features, permuted labels
        g = torch.Generator().manual_seed(1000 + a.seed)
        y = y[torch.randperm(len(y), generator=g)]
    head = nn.Linear(X.shape[1], 1)
    opt = torch.optim.AdamW(head.parameters(), lr=HEAD_LR, weight_decay=HEAD_WD)
    steps = HEAD_EPOCHS * ((len(X) + HEAD_BS - 1) // HEAD_BS)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, steps)
    g = torch.Generator().manual_seed(a.seed)
    loss_last = None
    for ep in range(HEAD_EPOCHS):
        perm = torch.randperm(len(X), generator=g)
        for i in range(0, len(X), HEAD_BS):
            idx = perm[i:i + HEAD_BS]
            loss = F.binary_cross_entropy_with_logits(head(X[idx]).squeeze(-1), y[idx])
            opt.zero_grad(); loss.backward(); opt.step(); sched.step()
            loss_last = float(loss)
    with torch.no_grad():
        dev_auc = {k: auc(head(v["X"].float()).squeeze(-1), v["y"]) for k, v in d["dev"].items()}
    res = {"seed": a.seed, "shuffle": bool(a.shuffle), "n_train": len(X), "pos_rate": round(float(y.mean()), 4), "last_loss": round(loss_last, 4),
           "dev_auc": {k: round(v, 4) for k, v in dev_auc.items()}, "feats_ckpt_sha256": d["ckpt_sha256"]}
    torch.save({"weight": head.weight.detach().clone(), "bias": head.bias.detach().clone(), "meta": res}, a.out)
    print(json.dumps(res))


# ---------------- test-time ----------------
def load_head(path):
    d = torch.load(path)
    return d["weight"].float(), d["bias"].float(), d["meta"]


def pick(qstop):
    return max(range(len(qstop)), key=lambda k: qstop[k])     # first maximum: ties go to the lowest index


@torch.no_grad()
def evaluate_heads(net, items, heads, device, bs=100):
    """heads: {name: (weight [1,d], bias [1])}. One forward per item batch; every head scored on the same tries."""
    net.eval()
    K, n = net.K, N_ROUNDS
    names = list(heads)
    acc = {"n": len(items), "S_pick_old": 0, "S_rand_mean": 0.0, "S_rand0": 0, "S_any": 0, "right_by_stream": [0] * K,
           "right_at_any_round_stream0": 0, "right_at_any_round_any_stream": 0,
           "heads": {nm: {"S_pick_new": 0, "S_pick_full": 0, "P192": 0, "pick_hist": [0] * K} for nm in names}}
    for i in range(0, len(items), bs):
        chunk = items[i:i + bs]
        t, s, _, env = R.tensors(chunk, device)
        preds, qold, feats = rounds_with_feats(net, t, s, env)
        preds, qold_l = preds.tolist(), qold.tolist()
        qnew = {nm: torch.sigmoid((feats * w.to(feats.device).view(1, 1, 1, -1)).sum(-1) + b.to(feats.device)).tolist()
                for nm, (w, b) in heads.items()}
        for bidx, it in enumerate(chunk):
            ok_round = [[bool(E.check(it, R.grid_of(preds[k][bidx][r], it))) for r in range(n)] for k in range(K)]
            stops = [stop_round(preds[k][bidx], qold_l[k][bidx], n) for k in range(K)]
            ok = [ok_round[k][stops[k]] for k in range(K)]
            acc["S_pick_old"] += ok[pick([qold_l[k][bidx][stops[k]] for k in range(K)])]
            acc["S_rand_mean"] += sum(ok) / K
            acc["S_rand0"] += ok[0]
            acc["S_any"] += any(ok)
            for k in range(K):
                acc["right_by_stream"][k] += ok[k]
            hit = [any(r_) for r_ in ok_round]
            acc["right_at_any_round_stream0"] += hit[0]
            acc["right_at_any_round_any_stream"] += any(hit)
            for nm in names:
                q = qnew[nm]
                h = acc["heads"][nm]
                pk = pick([q[k][bidx][stops[k]] for k in range(K)])
                h["S_pick_new"] += ok[pk]
                h["pick_hist"][pk] += 1
                stops_f = [stop_round(preds[k][bidx], q[k][bidx], n) for k in range(K)]
                pf = pick([q[k][bidx][stops_f[k]] for k in range(K)])
                h["S_pick_full"] += ok_round[pf][stops_f[pf]]
                best = max(((q[k][bidx][r], -k, -r) for k in range(K) for r in range(n)))   # highest prob; ties: lowest stream, then round
                h["P192"] += ok_round[-best[1]][-best[2]]
    acc["S_rand_mean"] = round(acc["S_rand_mean"], 2)
    return acc


def run_eval(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    sha = sha256_file(a.ckpt)
    net = G.g_load(a.ckpt, device)
    heads, metas = {}, {}
    for p in a.heads:
        w, b, meta = load_head(p)
        heads[Path(p).stem] = (w, b)
        metas[Path(p).stem] = meta
    tests = R.load_tests(a.tests, a.limit)
    res = {"ckpt": str(a.ckpt), "ckpt_sha256_before": sha, "heads": metas, "tests": {}}
    for name, env, size, seed, role in R.TESTS:
        r = evaluate_heads(net, tests[name], heads, device)
        r["role"] = role
        res["tests"][name] = r
        print(name, json.dumps({k: v for k, v in r.items() if k != "heads"}), flush=True)
        for nm, h in r["heads"].items():
            print("  ", nm, json.dumps(h), flush=True)
    res["ckpt_sha256_after"] = sha256_file(a.ckpt)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


# ---------------- selftest ----------------
def selftest():
    torch.manual_seed(0)
    dev = "cpu"
    net = G.GNet(4, 1.0)
    net.eval()
    rng = random.Random(3)
    practice, _ = E.split_four(E.number_hands()[0])
    items = [E.number_item(rng, h, t, s) for h, t, s in rng.sample(practice, 6)]
    t, s, _, env = R.tensors(items, dev)
    p1, q1 = net.stream_rounds(t, s, env, 8)
    p2, q2, f2 = rounds_with_feats(net, t, s, env, 8)
    assert torch.equal(p1, p2) and float((q1 - q2).abs().max()) <= 1e-6 and f2.shape == (4, 6, 8, 512)
    print("[1] rounds_with_feats == GNet.stream_rounds (predictions equal, halt probs within 1e-6) ok")
    for it in items:                                          # label function: the stored answer is right
        assert E.check(it, it.target)
    it = items[0]
    wrong = [row[:] for row in it.target]
    wrong[2][0] = E.OPS["+"]
    assert not E.check(it, wrong)
    print("[2] checker accepts the stored answer, rejects a corrupted one ok")
    sc = torch.tensor([0.1, 0.4, 0.35, 0.8])
    assert abs(auc(sc, torch.tensor([0, 0, 1, 1])) - 0.75) < 1e-9 and abs(auc(torch.tensor([1., 1, 1, 1]), torch.tensor([0, 1, 0, 1])) - 0.5) < 1e-9
    print("[3] auc: 0.75 on a known case, 0.5 on all ties ok")
    # collect + train-head + evaluate on a tiny random net (plumbing, no claim)
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    G_items = {"numbers4": items, "sums4": [E.make_sum(rng, 4) for _ in range(4)], "grids5": [E.latin_item(rng, *E.make_latin_base(rng, 5)) for _ in range(4)]}
    d = {"ckpt_sha256": "x", "seed": 1, "train": {}, "dev": {}}
    for k, v in G_items.items():
        d["train"][k] = collect(net, v, dev, 1)
        d["dev"][k] = collect(net, v, dev, 2)
        assert len(d["train"][k]["y"]) == len(v) * 4 * ROUNDS_PER
    torch.save(d, tmp / "f.pt")
    for shuf in (False, True):
        train_head(argparse.Namespace(feats=str(tmp / "f.pt"), seed=1, shuffle=shuf, out=str(tmp / f"h{int(shuf)}.pt")))
    w0, b0, _ = load_head(tmp / "h0.pt")
    r = evaluate_heads(net, items, {"a": (w0, b0), "old": (net.halt.weight.detach(), net.halt.bias.detach())}, dev)
    # with the OLD head as the "new" head the new pick equals the old pick, and full swap equals the sealed evaluation path
    assert r["heads"]["old"]["S_pick_new"] == r["S_pick_old"], (r["heads"]["old"], r["S_pick_old"])
    g = G.g_evaluate(net, items, dev)
    assert g["S_pick"] == r["S_pick_old"] and g["S_any"] == r["S_any"] and abs(g["S_rand_mean"] - r["S_rand_mean"]) < 0.02, (g, r)
    assert r["heads"]["old"]["S_pick_full"] == r["S_pick_old"] and r["S_any"] >= r["heads"]["a"]["S_pick_new"]
    print("[4] tiny end to end: old head reproduces G's g_evaluate (S_pick, S_any, S_rand) exactly; new head runs ok")
    y = torch.arange(10.)
    gperm = torch.randperm(10, generator=torch.Generator().manual_seed(1001))
    assert sorted(y[gperm].tolist()) == y.tolist()
    print("selftest ok (torch", torch.__version__, "CPU)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("feats"); p.add_argument("--ckpt", required=True); p.add_argument("--out", required=True); p.add_argument("--seed", type=int, default=1)
    p = sub.add_parser("train-head"); p.add_argument("--feats", required=True); p.add_argument("--seed", type=int, required=True)
    p.add_argument("--shuffle", action="store_true"); p.add_argument("--out", required=True)
    p = sub.add_parser("eval"); p.add_argument("--ckpt", required=True); p.add_argument("--heads", nargs="+", required=True)
    p.add_argument("--tests", required=True); p.add_argument("--out", required=True); p.add_argument("--limit", type=int, default=None)
    sub.add_parser("selftest")
    a = ap.parse_args()
    {"feats": make_feats, "train-head": train_head, "eval": run_eval, "selftest": lambda _: selftest()}[a.cmd](a)


if __name__ == "__main__":
    main()
