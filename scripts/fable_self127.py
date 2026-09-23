#!/usr/bin/env python3
"""127 -- registered single-change follow-up to exp 122 (self-question router).

Exp 122 blind result: 44 correct / 53 decline / 3 WRONG on 100 fresh questions
(tricks 10/10 declined). Diagnosis: all 3 WRONGs are NEAR-INTENT BLENDS -- new
questions borrowing an existing intent's words but asking for something else
(percentage-confidence -> C15; translation -> C5; relation-type count -> C29).
The head's softmax confidence cannot see novelty.

THE ONE CHANGE: a NOVELTY GUARD after the head. After the byte-identical 122
decision path (scope guard -> frozen head tau/mu -> type guard) routes to an
intent L, decline when the question's embedding is farther than delta_L from
EVERY training phrasing of L (nearest-neighbour cosine distance in the same
frozen MiniLM space; per-intent delta from artifacts/.../deltas127.json, one
fixed rule -- see PASSMARKS.md). Everything else (encoder, head, tau/mu,
scope guard, answer functions) is inherited untouched via fable_self122
(read-only; wrapped, never edited): the pre-guard path literally calls
fable_self122.route122, and answers come from the untouched exp-99 bodies.

Routing order for one question:
  1. route122() (scope guard -> head -> type guard; frozen) -> DECLINE/intent.
  2. Novelty guard (new): embed with the SAME frozen encoder; NN cosine
     distance to the bank rows of the routed intent (bank = every train122
     row, pinned by hash in bank127.json; zero added rows for exp 127);
     distance > delta_L -> DECLINE, else the intent stands.
  3. Answer: DECLINE -> identical HONEST_DECLINE; else grandparent exp-99
     answer_self() on the intent's canonical question (same as 122).

Run (Mac CPU, offline; only AFTER PASSMARKS sealed + ledger P127.*):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_self127_runner.py --run --out artifacts/fable-self127-20260922
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

import fable_self105 as S105  # noqa: E402 (read-only; wrapped, never edited)
import fable_self122 as S122  # noqa: E402 (read-only; wrapped, never edited)
import fable_self99 as S99  # noqa: E402 (read-only; wrapped, never edited)

HONEST_DECLINE = S105.HONEST_DECLINE
CANONICAL = S105.CANONICAL
ART127 = Path(__file__).resolve().parent.parent / "artifacts" \
    / "fable-self127-20260922"

_bank: dict[str, torch.Tensor] | None = None
_deltas: dict[str, float] | None = None


def load_deltas() -> dict[str, float]:
    global _deltas
    if _deltas is None:
        doc = json.loads((ART127 / "deltas127.json").read_text(
            encoding="utf-8"))
        _deltas = {k: float(v) for k, v in doc["delta"].items()}
    return _deltas


def load_bank() -> dict[str, torch.Tensor]:
    """Embed the pinned bank (train122 rows) once with the frozen encoder."""
    global _bank
    if _bank is None:
        torch.set_num_threads(1)
        spec = json.loads((ART127 / "bank127.json").read_text(
            encoding="utf-8"))
        repo = Path(__file__).resolve().parent.parent
        import hashlib  # noqa: E402
        src = repo / spec["source"]
        sha = hashlib.sha256(src.read_bytes()).hexdigest()
        assert sha == spec["sha256"], f"bank source changed: {sha}"
        import fable_self122_train as T  # noqa: E402 (frozen embed reuse)
        rows = T.load_rows(src)
        assert len(rows) == spec["n_rows"], len(rows)
        for extra in spec["extra_rows"]:
            rows.append(extra)
        router = S122.get_router()
        X = T.embed([r["text"] for r in rows], router.enc, router.tok)
        bank: dict[str, torch.Tensor] = {}
        labels = [r["label"] for r in rows]
        for lab in T.LABELS:
            idx = [i for i, lb in enumerate(labels) if lb == lab]
            bank[lab] = X[idx] if idx else torch.zeros((0, 384))
        _bank = bank
    return _bank


@torch.no_grad()
def novelty_check(question: str, intent: str) -> tuple[bool, dict]:
    """Returns (decline: bool, info). Never declines D/OOS (no delta)."""
    deltas = load_deltas()
    if intent not in deltas:
        return False, {"novelty": "vacuous (always-decline intent)"}
    bank = load_bank()
    router = S122.get_router()
    x = router._T.embed([question], router.enc, router.tok)
    rows = bank.get(intent)
    if rows is None or len(rows) == 0:
        return True, {"novelty": "empty-bank"}
    j = int(torch.argmax(rows @ x[0]))
    dist = float(1.0 - (rows @ x[0])[j])
    if dist > deltas[intent]:
        return True, {"novelty": "far",
                       "nndist": round(dist, 4),
                       "delta": deltas[intent], "nn": j}
    return False, {"novelty": "near",
                   "nndist": round(dist, 4),
                   "delta": deltas[intent], "nn": j}


def route127(question: str) -> tuple[str, dict]:
    intent, info = S122.route122(question)
    if intent == "DECLINE":
        return "DECLINE", info
    decline, ninfo = novelty_check(question, intent)
    info = dict(info)
    info.update(ninfo)
    if decline:
        info["decline"] = "novelty-guard"
        return "DECLINE", info
    return intent, info


class Self127Agent(S122.Self122Agent):
    """Exp-122 agent plus the novelty guard. Answer bodies inherited intact."""

    def answer_self(self, question: str) -> str:
        intent, _ = route127(question)
        if intent == "DECLINE":
            return HONEST_DECLINE
        return S99.Self99Agent.answer_self(self, CANONICAL[intent])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 127 novelty router")
    parser.add_argument("--route", default=None,
                        help="print the routed intent for one question")
    args = parser.parse_args(argv)
    if args.route is not None:
        intent, info = route127(args.route)
        print(f"{intent} {info}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
