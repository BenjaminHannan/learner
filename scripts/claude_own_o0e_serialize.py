"""own-O0e dialogue serializer: training text for the three baseline arms.

DIALOGUE FORMAT (documented here; fixed for this task):
  dialogue = {
    "world_id": str,            # fictional world label, e.g. "w014"
    "turns": [ turn, ... ],     # in conversation order
  }
  teach/correct turn = {
    "role": "teach" | "correct",
    "text": str,                # the spoken sentence, e.g. "Mira's dog is Pip."
    "facts": [[owner, relation, value], ...],  # gold triples stated here
  }
  ask turn = {
    "role": "ask",
    "text": str,                # the question, e.g. "What is Mira's dog called?"
    "answer": str,              # gold answer string, e.g. "Pip" (scoring only)
  }

THREE ARMS (same model, same data, different test-time text):
  B-plain    the conversation only (teach/correct/ask lines so far).
  B-RAG      conversation + top-k taught sentences found by plain
             word-overlap search (lowercased alnum tokens, no learned
             parts), inserted as a "Notes:" block before each question.
  B-notebook conversation + the current notebook rows as text
             ("owner | relation | value" lines) before each question.
             The notebook accumulates teach/correct facts; a correction
             supersedes the row with the same (owner, relation).

GREEDY ANSWER EXTRACTOR (used identically for every arm):
  take the model output, cut after the last "A:" marker if present,
  keep the first line, strip whitespace. That is the answer.

LEAK RULE: prompt builders only read "text" (and teach/correct "facts"
for the notebook arm, which is that arm's defined memory). They never
read an ask turn's "answer". Proof of this is the poison test in the
tests script: replacing every answer with "ZZZPOISON9" must leave all
prompts byte-identical.
"""

from __future__ import annotations

import argparse
import json
import re

_WORD = re.compile(r"[a-z0-9]+")


def words(s: str) -> list[str]:
    return _WORD.findall(s.lower())


def overlap_score(question: str, sentence: str) -> int:
    q = set(words(question))
    d = set(words(sentence))
    return len(q & d)


def retrieve(question: str, pool: list[str], k: int) -> list[str]:
    """Top-k pool sentences by word overlap; ties broken by pool order."""
    scored = sorted(
        ((overlap_score(question, s), -i, s) for i, s in enumerate(pool)),
        key=lambda t: (-t[0], -t[1]),
    )
    out = [s for sc, _, s in scored[:k] if sc > 0]
    return out


class Notebook:
    """Tiny in-memory notebook: rows of (owner, relation, value)."""

    def __init__(self):
        self.rows: list[list[str]] = []

    def apply(self, facts: list[list[str]]) -> None:
        for owner, rel, val in facts:
            self.rows = [r for r in self.rows if not (r[0] == owner and r[1] == rel)]
            self.rows.append([owner, rel, val])

    def as_text(self) -> str:
        if not self.rows:
            return "(empty)"
        return "\n".join(f"{o} | {r} | {v}" for o, r, v in self.rows)


def convo_lines(turns: list[dict]) -> list[str]:
    lines = []
    for t in turns:
        tag = {"teach": "Teach", "correct": "Correct", "ask": "Ask"}[t["role"]]
        lines.append(f"{tag}: {t['text']}")
    return lines


def evidence_pool(turns: list[dict]) -> list[str]:
    return [t["text"] for t in turns if t["role"] in ("teach", "correct")]


def build_prompt(dialogue: dict, ask_idx: int, arm: str, k: int = 2) -> str:
    """Prompt for the ask turn at position ask_idx. Never reads answers."""
    assert arm in ("plain", "rag", "notebook"), arm
    turns = dialogue["turns"]
    assert turns[ask_idx]["role"] == "ask"
    prior = turns[:ask_idx]
    question = turns[ask_idx]["text"]
    parts = convo_lines(prior)
    if arm == "rag":
        hits = retrieve(question, evidence_pool(prior), k)
        ctx = "\n".join(hits) if hits else "(no matches)"
        parts.append("Notes:\n" + ctx)
    elif arm == "notebook":
        nb = Notebook()
        for t in prior:
            if t["role"] in ("teach", "correct"):
                nb.apply(t["facts"])
        parts.append("Notebook:\n" + nb.as_text())
    parts.append(f"Q: {question}\nA:")
    return "\n".join(parts)


def greedy_extract(generated: str) -> str:
    """Identical answer extractor for every arm."""
    tail = generated.rsplit("A:", 1)[-1] if "A:" in generated else generated
    return tail.split("\n", 1)[0].strip()


def roundtrip(dialogue: dict, arm: str) -> list[tuple[str, str]]:
    """All (prompt, gold-answer) pairs for a dialogue; prompts hold no answers."""
    out = []
    for i, t in enumerate(dialogue["turns"]):
        if t["role"] == "ask":
            out.append((build_prompt(dialogue, i, arm), t["answer"]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        d = {
            "world_id": "demo",
            "turns": [
                {
                    "role": "teach",
                    "text": "Mira's dog is Pip.",
                    "facts": [["Mira", "dog", "Pip"]],
                },
                {"role": "ask", "text": "What is Mira's dog called?", "answer": "Pip"},
            ],
        }
        for arm in ("plain", "rag", "notebook"):
            print(f"--- {arm} ---")
            print(build_prompt(d, 1, arm))
        print("extract:", repr(greedy_extract("Q: x\nA: Pip\n")))


if __name__ == "__main__":
    main()
