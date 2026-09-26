#!/usr/bin/env python3
"""lis-320 pilot: how chat-like is the GLM wording? Counts only, compared with DEV chats (reading thread, 2026-09-26).

python claude_lis320_style.py --kept KEPT.jsonl [--chatdev DIR] [--bank DIR] --out OUT.json
  KEPT: claude_lis320_check.py output (training rows with turn and frame). DEV references: the everyday-chat DEV chats
  (artifacts/claude-chatdev-20260926/part*.jsonl) and the e2e331 DEV bank (turns.jsonl, user_text).
Per source: turns, words (median, p90), share of turns starting lowercase, share with an apostrophe-less contraction
(im, dont, cant, ...), share of turns over 20 words, distinct shapes (names and numbers masked) per 100 turns; for KEPT
also facts per turn and the share of ASSERT/CORRECT facts sitting in turns over 20 words.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

NOAPOS = re.compile(r"\b(im|dont|cant|wont|didnt|isnt|doesnt|thats|whats|ive|youre|theyre|shes|hes|ill|id)\b")


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def mask(s):
    return re.sub(r"\b[A-Z][a-z]+\b", "X", re.sub(r"\d+", "9", s))


def stats(turns):
    n = len(turns)
    if not n:
        return {"turns": 0}
    w = sorted(len(t.split()) for t in turns)
    return {"turns": n, "words_median": w[n // 2], "words_p90": w[int(n * 0.9)],
            "lowercase_start": round(sum(t[:1].islower() for t in turns) / n, 3),
            "noapos_contraction": round(sum(bool(NOAPOS.search(t)) for t in turns) / n, 3),
            "over20_words": round(sum(len(t.split()) > 20 for t in turns) / n, 3),
            "shapes_per_100": round(100 * len(set(map(mask, turns))) / n, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kept", required=True)
    ap.add_argument("--chatdev", default="artifacts/claude-chatdev-20260926")
    ap.add_argument("--bank", default="artifacts/claude-e2e331-dev-20260924")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    kept = load(a.kept)
    out = {"glm_kept": stats([r["turn"] for r in kept])}
    facts = [(f, r["turn"]) for r in kept for f in ((r.get("frame") or {}).get("facts") or [])
             if isinstance(f, dict) and f.get("mode") in ("ASSERT", "CORRECT")]
    out["glm_kept"] |= {"write_facts_per_turn": round(len(facts) / max(1, len(kept)), 3),
                        "write_facts_in_over20": round(sum(len(t.split()) > 20 for _f, t in facts) / max(1, len(facts)), 3)}
    cd = [t["text"] for p in sorted(Path(a.chatdev).glob("part*.jsonl")) for r in load(p) for t in r["turns"]]
    out["dev_chatdev"] = stats(cd)
    bt = Path(a.bank) / "turns.jsonl"
    if bt.exists():
        out["dev_bank"] = stats([r["user_text"] for r in load(bt) if r.get("user_text")])
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
