#!/usr/bin/env python3
"""122 -- diagnose dev WRONGs at the strict threshold (dev only, never the 122 panel)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import torch  # noqa: E402

import fable_self122_train as T  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tau", type=float, default=0.7)
    parser.add_argument("--mu", type=float, default=2.0)
    parser.add_argument("--seed", type=int, default=12201)
    parser.add_argument("--out", default="artifacts/fable-self122-20260922")
    args = parser.parse_args(argv)
    torch.set_num_threads(1)
    repo = SCRIPTS.parent
    out = repo / args.out
    import fable_self100_runner as R100
    import fable_self105 as S105
    import fable_self114 as S114
    import fable_self99 as S99
    import shutil
    state = out / "diag-notebook"
    if state.exists():
        shutil.rmtree(state)
    agent = S99.Self99Agent(str(state))
    agent.run_session()
    s = agent.snapshot()
    snap = T.resolve_snapshot(None)
    enc, tok, _ = T.load_encoder(snap)
    bundle = torch.load(out / "self122_head.pt", weights_only=True) \
        if (out / "self122_head.pt").exists() else None
    # train a fresh head for the requested seed if no bundle
    if bundle is None:
        tr = T.load_rows(out / "train122.jsonl")
        Xtr = T.embed([r["text"] for r in tr], enc, tok)
        ytr = torch.tensor([T.LAB2I[r["label"]] for r in tr])
        head = T.train_head(Xtr, ytr, args.seed)
    else:
        head = torch.nn.Linear(384, len(T.LABELS))
        head.load_state_dict(bundle["state_dict"])
        head.eval()
    devsets = {}
    devsets["exp99"] = [(q["id"], q["id"], q["text"]) for q in S99.QUESTIONS]
    devsets["exp100"] = [(qid, i, t) for qid, i, t in R100.BLIND]
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
    for name, rows in devsets.items():
        X = T.embed([t for _, _, t in rows], enc, tok)
        pi, conf, margin, logits = T.predict(head, X)
        for (qid, cls, text), p, c, m, lg in zip(rows, pi.tolist(),
                                                conf.tolist(),
                                                margin.tolist(),
                                                logits.tolist()):
            gd, reason = S114.scope_guard(text)
            if gd:
                routed = "DECLINE"
            else:
                routed = T.decide(p, c, m, args.tau, args.mu)
                if routed != "DECLINE":
                    _, toks = S105.normalise(text)
                    allow = S105.guard(text, toks)
                    if allow is not None and routed not in allow:
                        routed = "DECLINE (typeguard)"
            top3 = sorted(zip(lg, T.LABELS), reverse=True)[:3]
            top3s = [(lab, round(v, 2)) for v, lab in top3]
            ans = (S105.HONEST_DECLINE if routed.startswith("DECLINE")
                   else S99.Self99Agent.answer_self(
                       agent, S105.CANONICAL[routed]))
            verdict, note = R100.score(agent, qid, cls, ans, s)
            flag = ""
            if verdict == "WRONG":
                flag = "  <-- WRONG"
            elif verdict == "CORRECT":
                flag = "  ok"
            print(f"{name} {qid} cls={cls} routed={routed} "
                  f"conf={c:.2f} margin={m:.2f} top3={top3s} "
                  f"guard={gd}:{reason} verdict={verdict} ({note}){flag}",
                  flush=True)
            if verdict == "WRONG":
                print(f"    Q={text}", flush=True)
                print(f"    A={ans}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
