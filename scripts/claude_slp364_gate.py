#!/usr/bin/env python3
"""slp-364: the SELF-CHECK GATE that decides whether a night of sleep is kept (Fix-sleep thread, 2026-09-25).

Job B of design/v3/30-modes/sleep-research-2026-09-24.md; builds on slp-360 (scrap layer) and slp-361 (undo).
ONE CHANGE: install_gate364(loop) installs 361's undo with this gate as the judge. The gate:

  before the sleep  builds a probe set from the MAIN notebook with plain code (no model):
                      T  every taught one-hop fact, asked in English ("Who is Ann's mother?")
                      W  every compound word the sleeper can learn, for every person whose chain is complete;
                         the exact answer is computed by walking taught rows (a reply may also name the
                         people met along the way, e.g. "I don't know G01's mother.")
                      L  lures: the same words for people whose chain is broken, and for 3 invented names
                    and asks all of them through the real reply path (loop.turn), inside a sandbox that
                    puts files and memory back afterwards (361's snapshot), so probing changes nothing.
  after the sleep   asks the same questions again, in the same sandbox, and REJECTS the night when
                      N  the sleeper says it could not run, or its own audit failed (no silent success)
                      T  any taught one-hop reply changed
                      W  a word answer names someone other than the exact answer
                      L  a lure gets an answer that names anyone (a made-up answer)
                         (W and L count only when the reply changed during the night: a wrong reply that was
                         already there before the sleep is an old bug, not this night's fault)
                      K  a word answer that was right before the sleep is no longer right
Nothing here writes to the notebook. A rejected night is undone by 361 and its log is kept.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import claude_slp361_undo as U361

INVENTED364 = ("Qzorvath", "Xyllimund", "Vrenkotl")      # never used as names in any world
MAX_T364 = 120
MAX_W364 = 150
MAX_L364 = 60
_ABSTAIN = re.compile(r"\b(don'?t know|do not know|not sure|never told|no record|can'?t tell|"
                      r"don'?t have|not someone i can look up|isn'?t someone|no one)\b", re.I)


def _nb(loop):
    return getattr(loop.nb, "nb", loop.nb)


def _words():
    import fable_sleep130_agent as S130
    return list(S130.WORDS130), [list(c) for c in S130.CHAINS130]


def _show(nb, value: dict) -> str:
    return nb.entities.get(value["entity"], "?") if "entity" in value else str(value.get("literal", ""))


def _taught(nb, eid: str, rel: str) -> list[dict]:
    return [r for r in nb.current(eid, rel) if r.get("source") == "taught"]


def _walk(nb, eid: str, chain: list[str]):
    cur = eid
    for rel in chain:
        rows = _taught(nb, cur, rel)
        if len(rows) != 1 or "entity" not in rows[0]["value"]:
            return None
        cur = rows[0]["value"]["entity"]
    return cur


def _path(nb, eid: str, chain: list[str]) -> list[str]:
    """Names met along the chain as far as it goes (a reply may truthfully name them)."""
    out, cur = [], eid
    for rel in chain:
        rows = _taught(nb, cur, rel)
        if len(rows) != 1 or "entity" not in rows[0]["value"]:
            break
        cur = rows[0]["value"]["entity"]
        out.append(nb.entities[cur])
    return out


def _people(nb) -> list[str]:
    out = []
    for eid, name in sorted(nb.entities.items()):
        if name.strip().lower() in ("user", "me", "sleep", "sleep130"):
            continue
        out.append(eid)
    return out


def build_probes(loop) -> list[dict]:
    nb = _nb(loop)
    words, chains = _words()
    names = {nb.entities[e] for e in nb.entities}
    probes: list[dict] = []
    people = _people(nb)
    t = 0
    for eid in people:
        rels = sorted({f["relation"] for f in nb.facts.values()
                       if f["subject"] == eid and f.get("source") == "taught"})
        for rel in rels:
            rows = _taught(nb, eid, rel)
            if not rows or t >= MAX_T364:
                continue
            wh = "Who" if "entity" in rows[0]["value"] else "What"
            probes.append({"kind": "T", "q": f"{wh} is {nb.entities[eid]}'s {rel.replace('_', ' ')}?",
                           "want": [_show(nb, r["value"]) for r in rows]})
            t += 1
    w_n = l_n = 0
    for wi, word in enumerate(words):
        for eid in people:
            end = _walk(nb, eid, chains[wi])
            q = f"Who is {nb.entities[eid]}'s {word.replace('_', ' ')}?"
            path = _path(nb, eid, chains[wi])
            if end is not None and w_n < MAX_W364:
                probes.append({"kind": "W", "q": q, "want": [nb.entities[end]], "ok": path[:-1]})
                w_n += 1
            elif end is None and l_n < MAX_L364 and path:
                probes.append({"kind": "L", "q": q, "want": [], "ok": path})   # first hop known, chain broken
                l_n += 1
        for fake in INVENTED364:
            if fake not in names:
                probes.append({"kind": "L", "q": f"Who is {fake}'s {word.replace('_', ' ')}?", "want": []})
    return probes


def _mentions(reply: str, name: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", reply, re.I) is not None


def _grade(reply: str, probe: dict, names: set[str], asked_about: str) -> str:
    if probe["want"] and all(_mentions(reply, w) for w in probe["want"]):
        return "right"
    allowed = set(probe["want"]) | set(probe.get("ok", [])) | {asked_about}
    others = [n for n in names if n not in allowed and _mentions(reply, n)]
    if others:
        return "wrong"
    if _ABSTAIN.search(reply) or not reply.strip():
        return "abstain"
    return "other"


def ask_all(loop, probes: list[dict]) -> list[dict]:
    """Ask every probe through loop.turn inside a sandbox; nothing the probes do is kept."""
    root = Path(loop.dir)
    files = U361._files(root, {"notebook", U361.UNDO_DIR361})
    saved = {rel: p.read_bytes() for rel, p in files.items()}
    mem = U361._mem_snapshot(loop)
    log = root / "notebook" / "events.jsonl"
    main0 = hashlib.sha256(log.read_bytes()).hexdigest() if log.exists() else ""
    nb = _nb(loop)
    names = {n for n in nb.entities.values()}
    out = []
    old_threshold = loop.sleep_threshold
    loop.sleep_threshold = 10 ** 9          # probing must never start another sleep (it runs inside one)
    try:
        for p in probes:
            try:
                reply = " ".join(loop.turn(p["q"]))
            except Exception as exc:  # noqa: BLE001  (a crash is a visible failure)
                reply = f"<crash {type(exc).__name__}>"
            m = re.match(r"^(?:Who|What) is (.+?)'s ", p["q"])
            out.append({"kind": p["kind"], "q": p["q"], "reply": reply,
                        "grade": _grade(reply, p, names, m.group(1) if m else "")})
    finally:
        for rel, p in U361._files(root, {"notebook", U361.UNDO_DIR361}).items():
            if rel not in saved:            # a file the PROBES made (turn logs): moved aside, never deleted
                dest = root / U361.UNDO_DIR361 / "probes364" / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                p.replace(dest)
        for rel, data in saved.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(data)
        U361._mem_restore(loop, mem)
        loop.sleep_threshold = old_threshold
    main1 = hashlib.sha256(log.read_bytes()).hexdigest() if log.exists() else ""
    if main1 != main0:
        out.append({"kind": "N", "q": "<probes wrote to the notebook>", "reply": "", "grade": "wrong"})
    return out


class Gate364:
    def __init__(self) -> None:
        self.probes: list[dict] = []
        self.before: list[dict] = []
        self.last: dict = {}

    def pre(self, loop) -> None:
        self.probes = build_probes(loop)
        self.before = ask_all(loop, self.probes)

    def judge(self, loop, event) -> bool:
        reasons = []
        outcome = (event.get("detail") or {}).get("outcome") or {}
        self.sleeper_accepted = bool((event.get("detail") or {}).get("accepted"))   # today's rule, for the twin
        recipe = outcome.get("recipe") if isinstance(outcome, dict) else None
        if isinstance(outcome, dict) and outcome.get("accepted") is False:
            reasons.append("N: the sleeper's own audit failed")
        if isinstance(recipe, dict) and recipe.get("attempted") is False and recipe.get("reason"):
            reasons.append(f"N: sleep did not run ({str(recipe.get('reason'))[:80]})")
        after = ask_all(loop, self.probes)
        for b, a in zip(self.before, after):
            if a["kind"] == "T" and a["reply"] != b["reply"]:
                reasons.append(f"T: taught answer changed: {a['q']}")
            elif a["kind"] == "W" and a["grade"] in ("wrong", "other") and a["reply"] != b["reply"]:
                reasons.append(f"W: wrong word answer: {a['q']}")
            elif a["kind"] == "L" and a["grade"] in ("wrong", "right") and a["reply"] != b["reply"]:
                reasons.append(f"L: made-up answer: {a['q']}")
            if b["grade"] == "right" and a["grade"] != "right":
                reasons.append(f"K: lost a right answer: {a['q']}")
        reasons += [f"N: {a['q']}" for a in after[len(self.before):]]
        self.last = {"probes": len(self.probes), "kinds": {k: sum(p["kind"] == k for p in self.probes)
                                                          for k in "TWL"},
                     "reasons": reasons[:40], "n_reasons": len(reasons), "kept": not reasons}
        return not reasons


def install_gate364(loop) -> Gate364:
    gate = Gate364()
    U361.install_undo361(loop, judge=gate.judge)
    staged = loop._sleep_tick

    def sleep364():
        gate.pre(loop)
        return staged()

    loop._sleep_tick = sleep364
    loop.gate364 = gate
    loop.notes.append("slp-364: a night is kept only if the self-check finds no changed, wrong or made-up answer")
    return gate


def twin_judge(loop, event) -> bool:
    """Today's rule: the sleeper's own accepted flag (wire51 audit)."""
    return bool((event.get("detail") or {}).get("accepted"))
