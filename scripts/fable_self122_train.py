#!/usr/bin/env python3
"""122 -- train the learned intent classifier (frozen borrowed MiniLM + linear head).

Choice of encoder (saying why, per the brief): a frozen borrowed BERT-family
encoder with a small trained head, rather than a model trained from scratch.
Oblique phrasings ("tally", "cite its origin", "individuals") need semantic
similarity that a from-scratch model on ~2k rows cannot supply; the borrowed
encoder supplies it with zero new pretraining, and only a 41-way linear head
is learned, so training fits the <15 min Mac-CPU budget. MiniLM-L6-v2
(sentence-transformers/all-MiniLM-L6-v2, cached on the Mac) is used instead of
SciBERT/ModernBERT through the SAME plain-PyTorch loader
(scripts/fable_bert_loader.py: read_safetensors, Bert, WordPiece): it is a
borrowed encoder already used in this repo (the loader's own --check reference
model, verified 3e-6 in-repo), and at 6 layers x 384 hidden it embeds the
~2.5k-row corpus in ~2 min single-threaded where BERT-base would take ~5x
longer. Deviation D1: WordPiece is constructed with lowercase=True because
MiniLM's config.json carries do_lower_case=None (uncased vocab).

Pipeline: embed train122/heldout122 (mean-pool, L2-norm) -> train a
41-class linear head (40 intents + OOS) full-batch AdamW with inverse-sqrt
class weights -> evaluate seeds 12201-12203 on held-out + dev (exp99-40,
exp100-80, panels 105/114) -> grid-search (tau confidence, mu logit-margin)
for 0 wrong everywhere with max coverage -> save the frozen head.

Run (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_self122_train.py --train --snapshot <MiniLM snapshot>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402

import fable_bert_loader as L  # noqa: E402 (ours, read-only reuse)

LABELS: list[str] = ([f"C{i}" for i in range(1, 31)]
                     + [f"D{i}" for i in range(1, 11)] + ["OOS"])
LAB2I = {lab: i for i, lab in enumerate(LABELS)}
SEEDS = (12201, 12202, 12203)
EPOCHS = 600
LR = 0.05
WD = 1e-4
MAX_LEN = 64
BATCH = 64
TAU_GRID = (0.50, 0.60, 0.70)
MU_GRID = (0.5, 1.0, 1.5, 2.0)


def resolve_snapshot(arg: str | None) -> str:
    if arg:
        return arg
    base = Path(os.path.expanduser(
        "~/.cache/huggingface/hub/"
        "models--sentence-transformers--all-MiniLM-L6-v2/snapshots"))
    snaps = sorted(p for p in base.iterdir() if p.is_dir())
    assert snaps, "no cached MiniLM snapshot"
    return str(snaps[0])


def load_encoder(snapshot: str):
    """MiniLM via our plain-PyTorch loader (D1: lowercase=True, uncased vocab)."""
    with open(os.path.join(snapshot, "config.json")) as fh:
        cfg = json.load(fh)
    model = L.Bert(cfg)
    raw = L.read_safetensors(os.path.join(snapshot, "model.safetensors"))
    state, skipped = {}, []
    for k, v in raw.items():
        r = L.Bert.rename(k)
        (state.__setitem__(r, v.float()) if r else skipped.append(k))
    missing, unexpected = model.load_state_dict(state, strict=False)
    assert not unexpected, unexpected[:8]
    assert not missing, missing[:8]
    tok = L.WordPiece(os.path.join(snapshot, "vocab.txt"), lowercase=True)
    return model.eval(), tok, {"skipped": skipped,
                              "params": sum(p.numel()
                                            for p in model.parameters())}


@torch.no_grad()
def embed(texts: list[str], enc, tok) -> torch.Tensor:
    outs = []
    for i in range(0, len(texts), BATCH):
        ids, mask, _ = tok.batch(texts[i:i + BATCH], MAX_LEN)
        h = enc(ids, mask)
        m = mask.unsqueeze(-1).float()
        mean = (h * m).sum(1) / m.sum(1).clamp_min(1e-6)
        outs.append(F.normalize(mean, dim=1))
    return torch.cat(outs)


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def train_head(X: torch.Tensor, y: torch.Tensor, seed: int) -> torch.nn.Linear:
    g = torch.Generator().manual_seed(seed)
    head = torch.nn.Linear(X.shape[1], len(LABELS))
    torch.nn.init.xavier_uniform_(head.weight, generator=g)
    torch.nn.init.zeros_(head.bias)
    opt = torch.optim.AdamW(head.parameters(), lr=LR, weight_decay=WD)
    freq = torch.bincount(y, minlength=len(LABELS)).float()
    w = (freq.sum() / (len(LABELS) * freq)).clamp_max(4.0)
    for _ in range(EPOCHS):
        opt.zero_grad()
        loss = F.cross_entropy(head(X), y, weight=w)
        loss.backward()
        opt.step()
    return head


@torch.no_grad()
def predict(head, X: torch.Tensor):
    logits = head(X)
    prob = F.softmax(logits, dim=1)
    top = torch.topk(prob, 2, dim=1)
    conf = top.values[:, 0]
    ltop = torch.topk(logits, 2, dim=1).values
    margin = ltop[:, 0] - ltop[:, 1]
    return top.indices[:, 0], conf, margin, logits


def decide(pred_i: int, conf: float, margin: float, tau: float,
           mu: float) -> str:
    lab = LABELS[pred_i]
    if lab == "OOS" or conf < tau or margin < mu:
        return "DECLINE"
    return lab


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 122 classifier training")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--snapshot", default=None)
    parser.add_argument("--out", default="artifacts/fable-self122-20260922")
    args = parser.parse_args(argv)
    if not args.train:
        parser.print_help()
        return 0
    t0 = time.monotonic()
    torch.set_num_threads(1)
    repo = Path(__file__).resolve().parent.parent
    out = Path(args.out)
    if not out.is_absolute():
        out = repo / out
    out.mkdir(parents=True, exist_ok=True)

    snapshot = resolve_snapshot(args.snapshot)
    enc, tok, info = load_encoder(snapshot)
    print(f"encoder MiniLM-L6 params={info['params']:,} "
          f"skipped={info['skipped']}", flush=True)

    train_rows = load_rows(out / "train122.jsonl")
    held_rows = load_rows(out / "heldout122.jsonl")
    Xtr = embed([r["text"] for r in train_rows], enc, tok)
    ytr = torch.tensor([LAB2I[r["label"]] for r in train_rows])
    Xh = embed([r["text"] for r in held_rows], enc, tok)
    yh = torch.tensor([LAB2I[r["label"]] for r in held_rows])
    print(f"embedded train={Xtr.shape} held={Xh.shape} "
          f"self-sim={float((Xtr[:8] * Xtr[:8]).sum(1).min()):.4f}",
          flush=True)

    # -- sanity: distinct sentences must not collapse --
    sim = Xtr[:64] @ Xtr[:64].T
    off = sim - torch.eye(64)
    print(f"max off-diag cosine (first 64 train)={float(off.max()):.3f}",
          flush=True)

    heads = {}
    for seed in SEEDS:
        heads[seed] = train_head(Xtr, ytr, seed)
    report = {"seeds": {}, "seconds_embed_train":
              round(time.monotonic() - t0, 1)}
    for seed, head in heads.items():
        pi, conf, margin, _ = predict(head, Xh)
        acc = float((pi == yh).float().mean())
        report["seeds"][seed] = {
            "heldout_acc": round(acc, 4),
            "heldout_n": len(yh),
            "conf_min": round(float(conf.min()), 4),
            "margin_min": round(float(margin.min()), 4),
            "conf_mean": round(float(conf.mean()), 4)}
        print(f"seed {seed}: heldout acc={acc:.4f} "
              f"conf[min/mean]={float(conf.min()):.3f}/"
              f"{float(conf.mean()):.3f} "
              f"margin[min]={float(margin.min()):.3f}", flush=True)

    # -- dev evaluation for every seed (read-only reuse of frozen scorers) --
    import fable_self100_runner as R100  # noqa: E402
    import fable_self105 as S105  # noqa: E402
    import fable_self114 as S114  # noqa: E402
    sys.path.insert(0, str(SCRIPTS))
    import fable_self99 as S99  # noqa: E402
    state = out / "train-notebook"
    import shutil  # noqa: E402
    if state.exists():
        shutil.rmtree(state)
    agent = S99.Self99Agent(str(state))
    agent.run_session()
    s = agent.snapshot()

    devsets: dict[str, list[tuple[str, str, str]]] = {}
    devsets["exp99"] = [(q["id"], q["id"], q["text"]) for q in S99.QUESTIONS]
    devsets["exp100"] = [(qid, intent, text) for qid, intent, text in R100.BLIND]
    for panel, name in (("fable-self105panel-20260921", "panel105"),
                        ("fable-self114panel-20260922", "panel114")):
        d = json.loads((repo / "artifacts" / panel / "panel.json")
                       .read_text(encoding="utf-8"))
        qs = d["questions"] if isinstance(d, dict) else d
        rows = []
        for q in qs:
            qid, group, intent = q["id"], q["group"], q["intent"]
            text = q.get("question", q.get("text", q.get("q")))
            cls = (intent if group == "existing"
                   else ("NEW" if group == "new" else "D0"))
            rows.append((qid, cls, text))
        devsets[name] = rows

    Xdev = {name: embed([t for _, _, t in rows], enc, tok)
            for name, rows in devsets.items()}

    def verdicts_for(seed: int, tau: float, mu: float):
        """Score every dev question by script (answers from frozen S99 state)."""
        head = heads[seed]
        out_all: dict[str, list[dict]] = {}
        for name, rows in devsets.items():
            pi, conf, margin, _ = predict(head, Xdev[name])
            recs = []
            for (qid, cls, text), p, c, m in zip(rows, pi.tolist(),
                                                conf.tolist(),
                                                margin.tolist()):
                gd, _ = S114.scope_guard(text)
                if gd:
                    routed = "DECLINE"
                else:
                    routed = decide(p, c, m, tau, mu)
                    if routed != "DECLINE":
                        _, toks = S105.normalise(text)
                        allow = S105.guard(text, toks)
                        if allow is not None and routed not in allow:
                            routed = "DECLINE"
                ans = (S105.HONEST_DECLINE if routed == "DECLINE"
                       else S99.Self99Agent.answer_self(agent,
                                                        S105.CANONICAL[routed]))
                verdict, note = R100.score(agent, qid, cls, ans, s)
                recs.append({"id": qid, "cls": cls, "routed": routed,
                             "verdict": verdict, "note": note,
                             "question": text, "answer": ans,
                             "conf": round(c, 4), "margin": round(m, 4)})
            out_all[name] = recs
        return out_all

    # -- threshold grid: 0 wrong everywhere, then max existing-correct --
    grid = []
    for tau in TAU_GRID:
        for mu in MU_GRID:
            for seed in SEEDS:
                v = verdicts_for(seed, tau, mu)
                wrong = {n: sum(1 for r in recs if r["verdict"] == "WRONG")
                         for n, recs in v.items()}
                tot_wrong = sum(wrong.values())
                corr = sum(1 for r in v["panel105"] + v["panel114"]
                           if r["cls"].startswith("C") and
                           r["verdict"] == "CORRECT")
                exp99_full = sum(
                    1 for r in v["exp99"]
                    if (r["verdict"] == "CORRECT" and r["cls"].startswith("C"))
                    or (r["verdict"] == "DECLINE" and r["cls"].startswith("D")))
                grid.append({"seed": seed, "tau": tau, "mu": mu,
                             "wrong": wrong, "tot_wrong": tot_wrong,
                             "exp99_full": exp99_full,
                             "panels_existing_correct": corr})
    grid.sort(key=lambda g: (g["tot_wrong"], -g["exp99_full"],
                             -g["panels_existing_correct"],
                             g["tau"], g["mu"], g["seed"]))
    for g in grid:
        print(f"seed={g['seed']} tau={g['tau']} mu={g['mu']} "
              f"tot_wrong={g['tot_wrong']} {g['wrong']} "
              f"exp99_full={g['exp99_full']}/40 "
              f"panelsC-correct={g['panels_existing_correct']}", flush=True)
    best = grid[0]
    print(f"BEST seed={best['seed']} tau={best['tau']} mu={best['mu']} "
          f"tot_wrong={best['tot_wrong']} exp99_full={best['exp99_full']}",
          flush=True)
    assert best["tot_wrong"] == 0, "no threshold reaches 0 wrong on dev"
    assert best["exp99_full"] == 40, "no threshold keeps exp99 40/40"

    frozen = heads[best["seed"]]
    torch.save({"state_dict": frozen.state_dict(), "labels": LABELS,
                "tau": best["tau"], "mu": best["mu"],
                "seed": best["seed"], "encoder": "MiniLM-L6-v2",
                "snapshot": snapshot},
               out / "self122_head.pt")
    (out / "train122_report.json").write_text(json.dumps(
        {"report": report, "grid": grid, "best": best,
         "snapshot": snapshot,
         "train_sha": hashlib.sha256(
             (out / "train122.jsonl").read_bytes()).hexdigest(),
         "heldout_sha": hashlib.sha256(
             (out / "heldout122.jsonl").read_bytes()).hexdigest()},
        indent=1), encoding="utf-8")
    print(f"frozen seed={best['seed']} tau={best['tau']} mu={best['mu']} "
          f"total={round(time.monotonic() - t0, 1)}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
