#!/usr/bin/env python3
"""127 -- full-precision delta computation from the cached embeddings.

Reads scratchpad/self127-embed-cache.pt (full float32 tensors, no rounding),
re-runs the byte-identical 122 decision path + NN distances + frozen scorer
over every calibration row, rebuilds the keep/wrong pools at full precision,
and writes artifacts/fable-self127-20260922/deltas127.json with the ONE fixed
rule. DEV ONLY (heldout + exp99/100 + panels 105/114/122panel); never touches
the 127 blind panel.

Run (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_self127_deltas.py --write
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

REPO = Path(__file__).resolve().parent.parent
ART127 = REPO / "artifacts" / "fable-self127-20260922"
EPS_WRONG = 1e-6
MARGIN_KEEP = 1e-4


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if not args.write:
        parser.print_help()
        return 0
    torch.set_num_threads(1)
    import shutil  # noqa: E402

    import fable_self100_runner as R100  # noqa: E402
    import fable_self105 as S105  # noqa: E402
    import fable_self122_train as T  # noqa: E402
    import fable_self99 as S99  # noqa: E402
    import fable_self127_calibrate as C  # noqa: E402 (same decision code)

    cache = torch.load(REPO / "scratchpad" / "self127-embed-cache.pt",
                       weights_only=False)
    tau, mu = float(cache["tau"]), float(cache["mu"])
    Xbank, bank_labels = cache["Xbank"], cache["bank_labels"]
    enc_bank: dict[str, torch.Tensor] = {}
    for lab in T.LABELS:
        idx = [i for i, lb in enumerate(bank_labels) if lb == lab]
        enc_bank[lab] = Xbank[idx] if idx else torch.zeros((0, 384))

    bundle = torch.load(REPO / "artifacts" / "fable-self122-20260922"
                        / "self122_head.pt", weights_only=True)
    head = torch.nn.Linear(384, len(bundle["labels"]))
    head.load_state_dict(bundle["state_dict"])
    head.eval()

    state = REPO / "scratchpad" / "self127-deltas-notebook"
    if state.exists():
        shutil.rmtree(state)
    agent = S99.Self99Agent(str(state))
    agent.run_session()
    s = agent.snapshot()

    keeps: dict[str, list[tuple[str, float]]] = {}
    wrongs: list[tuple[str, str, str, float]] = []  # (set, qid, routed, d)
    Xcal, cal = cache["Xcal"], cache["cal"]
    for name, rows in cal.items():
        X = Xcal[name]
        for k, (qid, cls, text) in enumerate(rows):
            routed, info_d, dist = C.route_with_dist(
                text, X[k:k + 1], enc_bank, head, tau, mu)
            ans = (S99.Self99Agent.answer_self(agent, S105.CANONICAL[routed])
                   if routed != "DECLINE" else S105.HONEST_DECLINE)
            verdict, _ = R100.score(agent, qid, cls, ans, s)
            if verdict == "CORRECT" and dist is not None:
                keeps.setdefault(routed, []).append((name, float(dist)))
            elif verdict == "WRONG" and dist is not None:
                wrongs.append((name, qid, routed, float(dist)))
    nkeep = sum(len(v) for v in keeps.values())
    print(f"keeps={nkeep} wrongs={len(wrongs)}", flush=True)

    delta: dict[str, float] = {}
    for lab, rs in keeps.items():
        mx = max(d for _, d in rs)
        wl = [d for (sname, _, rlab, d) in wrongs
              if rlab == lab and sname == "panel122"]
        # ONE fixed rule: keep-side max plus a fixed noise margin (cross-run
        # float noise measured <= 1.2e-7; 1e-4 covers it ~1000x), capped by
        # the nearest blind-panel wrong minus a fixed epsilon.
        hi = mx + MARGIN_KEEP
        delta[lab] = (min(hi, min(wl) - EPS_WRONG)) if wl else hi
    # exact keep-loss / wrong-caught audit at full precision
    kl = [(lab, sname, d) for lab, rs in keeps.items()
          for (sname, d) in rs if d > delta[lab]]
    wc = [(sname, qid, rlab, d) for (sname, qid, rlab, d) in wrongs
          if d > delta.get(rlab, float("inf"))]
    print(f"keeps-lost={len(kl)}/{nkeep}", flush=True)
    for lab, sname, d in sorted(kl):
        print(f"  LOST {sname} {lab} d={d!r}", flush=True)
    print(f"wrongs-caught={len(wc)}/{len(wrongs)}", flush=True)
    for sname, qid, rlab, d in sorted(wc):
        print(f"  CAUGHT {sname} {qid}->{rlab} d={d!r}", flush=True)
    for sname, qid, rlab, d in sorted(set(wrongs) - set(wc)):
        print(f"  MISSED {sname} {qid}->{rlab} d={d!r}", flush=True)

    doc = json.loads((ART127 / "deltas127.json").read_text(encoding="utf-8"))
    doc["delta"] = {lab: delta[lab] for lab in sorted(delta)}
    doc["audit"] = {"keeps_total": nkeep, "keeps_lost": len(kl),
                    "wrongs_total": len(wrongs),
                    "wrongs_caught": len(wc),
                    "full_precision": True, "epsilon_wrong": EPS_WRONG,
                    "margin_keep": MARGIN_KEEP}
    (ART127 / "deltas127.json").write_text(json.dumps(doc, indent=1),
                                           encoding="utf-8")
    print("wrote deltas127.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
