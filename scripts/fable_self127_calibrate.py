#!/usr/bin/env python3
"""127 -- DEV-ONLY novelty-guard calibration (never touches the 127 blind panel).

Loads the FROZEN 122 encoder+head read-only, embeds the neighbour bank
(train122.jsonl rows grouped by label) and every calibration row (heldout122
+ exp99 + exp100 + panels 105/114/122, all dev), routes each row with the
byte-identical 122 decision path (scope guard -> head tau/mu -> type guard),
scores it with the frozen exp-100 scorer, and prints, per routed intent, the
nearest-neighbour cosine distances of CORRECT rows vs WRONG rows.

Run (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_self127_calibrate.py --report
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import torch  # noqa: E402

import fable_self122_train as T  # noqa: E402 (frozen pipeline reuse, read-only)

REPO = Path(__file__).resolve().parent.parent
ART122 = REPO / "artifacts" / "fable-self122-20260922"


def load_bank() -> list[dict]:
    return T.load_rows(ART122 / "train122.jsonl")


def calibration_rows() -> dict[str, list[tuple[str, str, str]]]:
    """Dev only. Returns {setname: [(qid, cls, text)]}."""
    import fable_self100_runner as R100  # noqa: E402
    import fable_self99 as S99  # noqa: E402

    out: dict[str, list[tuple[str, str, str]]] = {}
    out["heldout"] = [(f"H{i}", r["label"], r["text"]) for i, r in
                      enumerate(T.load_rows(ART122 / "heldout122.jsonl"))]
    out["exp99"] = [(q["id"], q["id"], q["text"]) for q in S99.QUESTIONS]
    out["exp100"] = [(qid, intent, text) for qid, intent, text in R100.BLIND]
    for panel, name in (("fable-self105panel-20260921", "panel105"),
                        ("fable-self114panel-20260922", "panel114"),
                        ("fable-self122panel-20260922", "panel122")):
        d = json.loads((REPO / "artifacts" / panel / "panel.json")
                       .read_text(encoding="utf-8"))
        qs = d["questions"] if isinstance(d, dict) else d
        rows = []
        for q in qs:
            qid, group, intent = q["id"], q["group"], q["intent"]
            text = q.get("question", q.get("text", q.get("q")))
            cls = (intent if group == "existing"
                   else ("NEW" if group == "new" else "D0"))
            rows.append((qid, cls, text))
        out[name] = rows
    return out


@torch.no_grad()
def route_with_dist(question: str, x, enc_bank: dict[str, torch.Tensor],
                    head, tau: float, mu: float):
    """122 decision path + NN cosine distance to the routed intent's bank."""
    import fable_self105 as S105  # noqa: E402
    import fable_self114 as S114  # noqa: E402

    gd, reason = S114.scope_guard(question)
    if gd:
        return "DECLINE", {"why": f"scope:{reason}"}, None
    pi, conf, margin, _ = T.predict(head, x)
    p, c, m = int(pi[0]), float(conf[0]), float(margin[0])
    lab = T.decide(p, c, m, tau, mu)
    if lab == "DECLINE":
        return "DECLINE", {"why": "lowconf", "conf": c, "margin": m}, None
    _, toks = S105.normalise(question)
    allow = S105.guard(question, toks)
    if allow is not None and lab not in allow:
        return "DECLINE", {"why": "typeguard"}, None
    bank = enc_bank.get(lab)
    if bank is None or len(bank) == 0:
        return "DECLINE", {"why": "empty-bank"}, None
    sims = (bank @ x[0])
    j = int(torch.argmax(sims))
    dist = float(1.0 - sims[j])
    return lab, {"conf": round(c, 4), "margin": round(m, 4),
                 "nn": int(j)}, dist


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)
    if not args.report:
        parser.print_help()
        return 0
    torch.set_num_threads(1)
    import shutil  # noqa: E402

    import fable_self100_runner as R100  # noqa: E402
    import fable_self99 as S99  # noqa: E402
    import fable_self105 as S105  # noqa: E402

    snap = T.resolve_snapshot(None)
    enc, tok, info = T.load_encoder(snap)
    print(f"encoder params={info['params']:,}", flush=True)
    bundle = torch.load(ART122 / "self122_head.pt", weights_only=True)
    head = torch.nn.Linear(384, len(bundle["labels"]))
    head.load_state_dict(bundle["state_dict"])
    head.eval()
    tau, mu = float(bundle["tau"]), float(bundle["mu"])
    print(f"frozen head seed={bundle['seed']} tau={tau} mu={mu}", flush=True)

    bank_rows = load_bank()
    bank_texts = [r["text"] for r in bank_rows]
    bank_labels = [r["label"] for r in bank_rows]
    Xbank = T.embed(bank_texts, enc, tok)
    enc_bank: dict[str, torch.Tensor] = {}
    for lab in T.LABELS:
        idx = [i for i, lb in enumerate(bank_labels) if lb == lab]
        enc_bank[lab] = Xbank[idx] if idx else torch.zeros((0, 384))
    print(f"bank rows={len(bank_rows)} labels={len(enc_bank)}", flush=True)

    cal = calibration_rows()
    Xcal = {name: T.embed([t for _, _, t in rows], enc, tok)
            for name, rows in cal.items()}
    cache = {"bank_labels": bank_labels, "Xbank": Xbank, "Xcal": Xcal,
             "cal": cal, "tau": tau, "mu": mu,
             "seed": bundle["seed"]}
    cpath = REPO / "scratchpad" / "self127-embed-cache.pt"
    torch.save(cache, cpath)
    print(f"cached embeddings -> {cpath}", flush=True)
    state = REPO / "scratchpad" / "self127-diag-notebook"
    if state.exists():
        shutil.rmtree(state)
    agent = S99.Self99Agent(str(state))
    agent.run_session()
    s = agent.snapshot()

    cal = calibration_rows()
    for name, rows in cal.items():
        X = Xcal[name]
        recs = []
        for k, (qid, cls, text) in enumerate(rows):
            routed, info_d, dist = route_with_dist(
                text, X[k:k + 1], enc_bank, head, tau, mu)
            ans = (S99.Self99Agent.answer_self(agent, S105.CANONICAL[routed])
                   if routed != "DECLINE" else S105.HONEST_DECLINE)
            verdict, note = R100.score(agent, qid, cls, ans, s)
            recs.append((qid, cls, routed, verdict, dist, info_d, text))
        n_wrong = sum(1 for r in recs if r[3] == "WRONG")
        n_corr = sum(1 for r in recs if r[3] == "CORRECT")
        n_dec = sum(1 for r in recs if r[3] in ("DECLINE", "CLARIFY",
                                                "HONEST_DECLINE"))
        print(f"== {name}: n={len(recs)} CORRECT={n_corr} "
              f"DECLINE-ish={n_dec} WRONG={n_wrong}", flush=True)
        for qid, cls, routed, verdict, dist, info_d, text in recs:
            if verdict == "WRONG":
                dd = f"{dist:.4f}" if dist is not None else "n/a"
                print(f"  WRONG {qid} cls={cls} routed={routed} "
                      f"nndist={dd} {info_d}", flush=True)
                print(f"    Q={text}", flush=True)
        # per-intent CORRECT distance lists (for rule choice), all sets
        by_intent: dict[str, list[float]] = {}
        for qid, cls, routed, verdict, dist, info_d, text in recs:
            if verdict == "CORRECT" and dist is not None:
                by_intent.setdefault(routed, []).append(dist)
        for lab in sorted(by_intent):
            ds = sorted(by_intent[lab])
            print(f"  KEEP {name} {lab}: n={len(ds)} "
                  f"{' '.join(f'{d:.4f}' for d in ds)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
