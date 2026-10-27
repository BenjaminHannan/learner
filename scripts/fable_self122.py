#!/usr/bin/env python3
"""122 -- registered single-change follow-up to exp 114 (self-question router).

Exp 114 blind result: 17 correct / 79 decline / 4 WRONG on 100 fresh questions
(tricks 10/10 declined). Diagnosis: the scope guard works; the ceiling is
VOCABULARY -- the keyword scorer cannot recognise oblique phrasings (46 margin
declines on existing intents).

THE ONE CHANGE: the keyword scorer is replaced by a LEARNED intent classifier
(frozen borrowed MiniLM-L6-v2 encoder via our plain-PyTorch loader +
a 41-way linear head trained on 1,900 hand-written phrasings). Kept unchanged:
the exp-114 scope guard in front, the exp-105 question-type guard as a
candidate restrictor, the margin/confidence decline, and ALL answer functions
(answers come from the untouched exp-99 bodies via each intent's canonical
question; the decline sentence is the identical inherited HONEST_DECLINE).

Routing order for one question:
  1. scope_guard() (fable_self114, frozen) -> DECLINE with reason.
  2. Learned classifier (frozen encoder + frozen head) -> top1/conf/margin.
     OOS top1, conf < tau, or logit-margin < mu -> DECLINE.
  3. Question-type guard (fable_self105.guard, frozen) restricts candidates;
     top1 outside the allowed set -> DECLINE.
  4. Else the intent id; the answer is produced by calling the GRANDPARENT
     exp-99 answer_self() on that intent's canonical question (provably the
     same body as exp 99; the keyword router is bypassed, never edited).

Run (Mac CPU, offline; only AFTER PASSMARKS sealed + ledger P122.*):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_self122.py --devcheck
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import torch  # noqa: E402

import fable_self105 as S105  # noqa: E402 (read-only; wrapped, never edited)
import fable_self114 as S114  # noqa: E402 (read-only; wrapped, never edited)
import fable_self99 as S99  # noqa: E402 (read-only; wrapped, never edited)

HONEST_DECLINE = S105.HONEST_DECLINE
CANONICAL = S105.CANONICAL

_classifier = None


class LearnedRouter:
    """Frozen encoder + frozen head. No training here, ever."""

    def __init__(self, repo: Path):
        import fable_self122_train as T  # noqa: E402 (frozen pipeline reuse)
        torch.set_num_threads(1)
        self._T = T
        snapshot = T.resolve_snapshot(None)
        enc, tok, info = T.load_encoder(snapshot)
        self.enc, self.tok = enc, tok
        art = repo / "artifacts" / "fable-self122-20260922"
        bundle = torch.load(art / "self122_head.pt", weights_only=True)
        head = torch.nn.Linear(384, len(bundle["labels"]))
        head.load_state_dict(bundle["state_dict"])
        head.eval()
        self.head = head
        self.labels: list[str] = list(bundle["labels"])
        self.tau: float = float(bundle["tau"])
        self.mu: float = float(bundle["mu"])
        self.seed = bundle["seed"]
        self.snapshot = snapshot

    @torch.no_grad()
    def route(self, question: str) -> tuple[str, dict]:
        T = self._T
        X = T.embed([question], self.enc, self.tok)
        pi, conf, margin, logits = T.predict(self.head, X)
        p, c, m = int(pi[0]), float(conf[0]), float(margin[0])
        lg = logits[0].tolist()
        top3 = [(self.labels[i], round(v, 2))
                for v, i in sorted(zip(lg, range(len(lg))),
                                   reverse=True)[:3]]
        info = {"top1": self.labels[p], "conf": round(c, 4),
                "margin": round(m, 4), "top3": top3,
                "tau": self.tau, "mu": self.mu}
        decline, reason = S114.scope_guard(question)
        if decline:
            info["guard"] = reason
            return "DECLINE", info
        info["guard"] = "pass"
        lab = self.labels[p]
        if lab == "OOS":
            info["decline"] = "predicted-OOS"
            return "DECLINE", info
        if c < self.tau or m < self.mu:
            info["decline"] = f"low-confidence(c={c:.2f}<{self.tau} or " \
                              f"m={m:.2f}<{self.mu})"
            return "DECLINE", info
        _, toks = S105.normalise(question)
        allow = S105.guard(question, toks)
        if allow is not None and lab not in allow:
            info["decline"] = "type-guard"
            return "DECLINE", info
        return lab, info


def get_router() -> LearnedRouter:
    global _classifier
    if _classifier is None:
        repo = Path(__file__).resolve().parent.parent
        _classifier = LearnedRouter(repo)
    return _classifier


def route122(question: str) -> tuple[str, dict]:
    return get_router().route(question)


class Self122Agent(S114.Self114Agent):
    """Exp-114 agent with the learned scorer. Answer bodies inherited intact."""

    def answer_self(self, question: str) -> str:
        intent, _ = route122(question)
        if intent == "DECLINE":
            return HONEST_DECLINE
        return S99.Self99Agent.answer_self(self, CANONICAL[intent])


def devcheck() -> int:
    """Dev ONLY (exp99-40 + exp100-80 + panels 105/114). Never the 122 panel."""
    import shutil  # noqa: E402

    import fable_self100_runner as R100  # noqa: E402 (read-only scoring)

    repo = Path(__file__).resolve().parent.parent
    state = (repo / "artifacts" / "fable-self122-20260922"
             / "devcheck-notebook")
    if state.exists():
        shutil.rmtree(state)
    agent = Self122Agent(str(state))
    agent.run_session()
    s = agent.snapshot()

    checked = agent.check_all()
    s1, s2 = checked["correct"], len(checked["hallucinations"])
    s3 = sum(1 for p in checked["per_question"]
             if p["id"].startswith("D") and p["pass"])
    print(f"exp99: S1 {s1}/40 S2 hallucinations={s2} S3 {s3}/10", flush=True)
    gate = {"n_taught": 19, "n_entities": 6, "n_quarantine": 1,
            "n_superseded": 2, "n_forgotten": 1, "sleeps": 0, "turns": 26}
    gate_ok = all(s[k] == v for k, v in gate.items())

    devsets = [("exp100", [(qid, intent, text)
                           for qid, intent, text in R100.BLIND])]
    import json as _json  # noqa: E402
    for panel, name in (("fable-self105panel-20260921", "panel105"),
                        ("fable-self114panel-20260922", "panel114")):
        d = _json.loads((repo / "artifacts" / panel / "panel.json")
                        .read_text(encoding="utf-8"))
        qs = d["questions"] if isinstance(d, dict) else d
        rows = []
        for q in qs:
            qid, group, intent = q["id"], q["group"], q["intent"]
            text = q.get("question", q.get("text", q.get("q")))
            cls = (intent if group == "existing"
                   else ("NEW" if group == "new" else "D0"))
            rows.append((qid, cls, text))
        devsets.append((name, rows))

    tot_wrong, tot_c = 0, 0
    for name, rows in devsets:
        wrong = 0
        for qid, cls, text in rows:
            ans = agent.answer_self(text)
            verdict, note = R100.score(agent, qid, cls, ans, s)
            wrong += verdict == "WRONG"
            tot_c += (cls.startswith("C") and verdict == "CORRECT")
            if verdict == "WRONG":
                print(f"  STILL-WRONG {name} {qid}({cls}) Q={text} A={ans}",
                      flush=True)
        print(f"{name}: WRONG={wrong}/{len(rows)}", flush=True)
        tot_wrong += wrong
    ok = gate_ok and s1 == 40 and s2 == 0 and s3 == 10 and tot_wrong == 0
    print("DEVCHECK " + ("PASS" if ok else "FAIL"), flush=True)
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 122 learned router")
    parser.add_argument("--devcheck", action="store_true")
    parser.add_argument("--route", default=None,
                        help="print the routed intent for one question")
    args = parser.parse_args(argv)
    if args.route is not None:
        intent, info = route122(args.route)
        print(f"{intent} {info}")
        return 0
    if args.devcheck:
        return devcheck()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
