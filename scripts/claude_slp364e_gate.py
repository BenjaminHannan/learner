#!/usr/bin/env python3
"""slp-364e: self-check gate, version 5 (Fix-sleep thread, 2026-09-25). Follows slp-364d (15/20 caught). All five
v4 misses showed only in questions the gate never asks: other phrasings, yes/no, explicit multi-step questions, and
people with no facts of their own. v5 = v4 plus ONE change: those question kinds are asked before and after the night.
Every earlier rule is unchanged.
  F  the word question in other phrasings ("Who's", "Tell me", "What is the name of", "... called?", lower case),
     for 2 people per word with a complete chain; truth known. A changed reply graded wrong/other rejects the night.
  Y  "Is <end> A's <word>?" and "Is <first hop> A's <word>?". A changed reply that says "No" to the true person or
     "Yes" to the first-hop person rejects the night.
  E  an explicit two-step question "Who is A's <hop 1>'s <other relation>?" whose second step is not the word's.
     If the notebook has the answer, a changed reply graded wrong/other rejects; if not, a changed reply that does not
     abstain rejects.
  Z  the word asked about 2 people who have no taught facts of their own. A changed reply that does not abstain
     rejects the night.
"""
from __future__ import annotations

from pathlib import Path

import claude_slp364_gate as G
import claude_slp364b_gate as GB
import claude_slp364d_gate as GD

FORMS364E = {"whos": "Who's {n}'s {p}?", "tell": "Tell me {n}'s {p}.", "nameof": "What is the name of {n}'s {p}?",
             "called": "What is {n}'s {p} called?", "lower": "who is {nl}'s {p}"}
F_PEOPLE = 2
Z_PEOPLE = 2


def _atoms(chains) -> list[str]:
    return sorted({r for c in chains for r in c})


def form_probes(loop) -> list[dict]:
    nb = G._nb(loop)
    words, chains = G._words()
    atoms = _atoms(chains)
    people = G._people(nb)
    factless = [e for e in people if not any(G._taught(nb, e, r) for r in atoms)]
    out = []
    for wi, word in enumerate(words):
        chain, phrase = chains[wi], word.replace("_", " ")
        n = 0
        for eid in people:
            if n >= F_PEOPLE:
                break
            end = G._walk(nb, eid, chain)
            if end is None:
                continue
            n += 1
            a, path = nb.entities[eid], G._path(nb, eid, chain)
            for form in FORMS364E.values():
                out.append({"kind": "F", "word": word, "about": a, "want": [nb.entities[end]], "ok": path,
                            "q": form.format(n=a, nl=a.lower(), p=phrase)})
            out.append({"kind": "Y", "word": word, "about": a, "want": [], "ok": path, "truth": "yes",
                        "q": f"Is {nb.entities[end]} {a}'s {phrase}?"})
            if path and path[0] != nb.entities[end]:
                out.append({"kind": "Y", "word": word, "about": a, "want": [], "ok": path, "truth": "no",
                            "q": f"Is {path[0]} {a}'s {phrase}?"})
            if len(chain) >= 2:
                other = next((r for r in atoms if r != chain[1] and r != chain[0]), None)
                if other is not None:
                    two = G._walk(nb, eid, [chain[0], other])
                    out.append({"kind": "E", "word": word, "about": a,
                                "want": [nb.entities[two]] if two is not None else [],
                                "ok": G._path(nb, eid, [chain[0], other]),
                                "q": f"Who is {a}'s {chain[0].replace('_', ' ')}'s {other.replace('_', ' ')}?"})
        for eid in factless[:Z_PEOPLE]:
            out.append({"kind": "Z", "word": word, "about": nb.entities[eid], "want": [], "ok": [],
                        "q": f"Who is {nb.entities[eid]}'s {phrase}?"})
    return out


def _yes(reply: str) -> bool:
    return reply.strip().lower().startswith("yes")


def _no(reply: str) -> bool:
    return reply.strip().lower().startswith("no")


class Gate364e(GD.Gate364d):
    def pre(self, loop) -> None:
        self.probes = GB.build_probes_b(loop) + GD.near_probes(loop) + form_probes(loop)
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
        names = set(G._nb(loop).entities.values())
        extra = []
        for p, b, a in zip(self.probes, self.before, captured.get("after", [])):
            if p["kind"] not in "FYEZ" or a["reply"] == b["reply"]:
                continue
            grade = G._grade(a["reply"], p, names, p["about"])
            if p["kind"] == "F" and grade in ("wrong", "other"):
                extra.append(f"F: another phrasing now gets a wrong answer: {a['q']}")
            elif p["kind"] == "Y" and ((p["truth"] == "yes" and _no(a["reply"]))
                                       or (p["truth"] == "no" and _yes(a["reply"]))):
                extra.append(f"Y: a yes/no answer is now wrong: {a['q']}")
            elif p["kind"] == "E" and p["want"] and grade in ("wrong", "other"):
                extra.append(f"E: an explicit two-step question now gets a wrong answer: {a['q']}")
            elif p["kind"] == "E" and not p["want"] and grade != "abstain":
                extra.append(f"E: an explicit two-step question with no answer now gets one: {a['q']}")
            elif p["kind"] == "Z" and grade != "abstain":
                extra.append(f"Z: a person with no facts now gets an answer: {a['q']}")
        if extra:
            self.last["reasons"] = (self.last.get("reasons", []) + extra)[:40]
            self.last["n_reasons"] = self.last.get("n_reasons", 0) + len(extra)
            self.last["kept"] = False
        self.last["kinds"] = {k: sum(p["kind"] == k for p in self.probes) for k in "TWLUFYEZ"}
        return kept and not extra


def install_gate364e(loop, rebuild=None) -> Gate364e:
    import claude_slp361_undo as U361
    gate = Gate364e(rebuild)
    U361.install_undo361(loop, judge=gate.judge)
    staged = loop._sleep_tick

    def sleep364e():
        gate.pre(loop)
        return staged()

    loop._sleep_tick = sleep364e
    loop.gate364e = gate
    loop.notes.append("slp-364e: a night is kept only if the self-check (v5) finds nothing wrong")
    return gate
