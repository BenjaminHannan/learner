#!/usr/bin/env python3
"""slp-364d: self-check gate, version 4 (Fix-sleep thread, 2026-09-25). Follows slp-364c (18/20 caught; missed both
made-up-answer faults). v4 = v3 plus two lure rules; every earlier rule is unchanged:
  L2  a broken-chain or invented-name lure whose reply CHANGED during the night and now neither abstains nor names a
      wrong person (graded "other", e.g. "X's boss of mother is M01." where M01 is only the first hop) rejects the
      night. v1-v3 flagged only "wrong"/"right" lure grades, and allowed names met along the chain.
  U   near-miss lures: for every word, two people with a complete chain are asked the word with one relation word
      swapped for a near miss the user never taught ("paternal grandmother", "boss of brother"). The truth is unknown,
      so a reply that changed during the night and does not abstain rejects the night.
"""
from __future__ import annotations

from pathlib import Path

import claude_slp364_gate as G
import claude_slp364b_gate as GB
import claude_slp364c_gate as GC

NEAR364D = {"maternal": "paternal", "mother": "brother", "father": "uncle", "spouse": "cousin", "boss": "coach",
            "doctor": "dentist", "teacher": "tutor", "friend": "neighbor", "grandmother": "godmother",
            "mothers": "brothers"}
U_PER_WORD = 2


def _near(phrase: str) -> str | None:
    toks = phrase.split()
    for i in range(len(toks) - 1, -1, -1):
        if toks[i] in NEAR364D:
            return " ".join(toks[:i] + [NEAR364D[toks[i]]] + toks[i + 1:])
    return None


def near_probes(loop) -> list[dict]:
    nb = G._nb(loop)
    words, chains = G._words()
    out = []
    people = G._people(nb)
    for wi, word in enumerate(words):
        phrase = _near(word.replace("_", " "))
        if phrase is None:
            continue
        n = 0
        for eid in people:
            if n >= U_PER_WORD:
                break
            if G._walk(nb, eid, chains[wi]) is None:
                continue
            out.append({"kind": "U", "word": word, "q": f"Who is {nb.entities[eid]}'s {phrase}?", "want": [],
                        "ok": G._path(nb, eid, chains[wi])[:1]})
            n += 1
    return out


class Gate364d(GC.Gate364c):
    def pre(self, loop) -> None:
        self.probes = GB.build_probes_b(loop) + near_probes(loop)
        self.before = G.ask_all(loop, self.probes)
        self.main0 = GB._digest(Path(loop.dir) / "notebook" / "events.jsonl")

    def judge(self, loop, event) -> bool:
        captured: dict = {}
        real = G.ask_all

        def capture(lp, probes):
            res = real(lp, probes)
            if probes is self.probes and "after" not in captured:
                captured["after"] = res
            return res

        G.ask_all = capture
        try:
            kept = super().judge(loop, event)
        finally:
            G.ask_all = real
        extra = []
        for b, a in zip(self.before, captured.get("after", [])):
            if a["kind"] == "L" and a["grade"] == "other" and a["reply"] != b["reply"]:
                extra.append(f"L2: a lure now gets an answer: {a['q']}")
            elif a["kind"] == "U" and a["grade"] in ("wrong", "right", "other") and a["reply"] != b["reply"]:
                extra.append(f"U: a relation never taught now gets an answer: {a['q']}")
        if extra:
            self.last["reasons"] = (self.last.get("reasons", []) + extra)[:40]
            self.last["n_reasons"] = self.last.get("n_reasons", 0) + len(extra)
            self.last["kept"] = False
        self.last["kinds"] = {k: sum(p["kind"] == k for p in self.probes) for k in "TWLU"}
        return kept and not extra


def install_gate364d(loop, rebuild=None) -> Gate364d:
    import claude_slp361_undo as U361
    gate = Gate364d(rebuild)
    U361.install_undo361(loop, judge=gate.judge)
    staged = loop._sleep_tick

    def sleep364d():
        gate.pre(loop)
        return staged()

    loop._sleep_tick = sleep364d
    loop.gate364d = gate
    loop.notes.append("slp-364d: a night is kept only if the self-check (v4) finds nothing wrong")
    return gate
