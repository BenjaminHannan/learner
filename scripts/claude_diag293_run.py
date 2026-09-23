#!/usr/bin/env python3
"""Exp 293-diag main run: 63 dev dialogs (own wording, fictional names) on
138nb only. Fresh temp state_dir per dialog, sleep_threshold 100000, CPU
only. Records reply, outer + inner ears.last_stage, emitted acts,
last_routed intent, event counts (writes), decline224 / q1honest224c logs.
Writes JSONL rows to artifacts/claude-diag293-20260923/rows.jsonl.
New file only; additive. Never opens any panel folder or raw panel rows."""
from __future__ import annotations
import copy, json, shutil, sys, tempfile
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import claude_loop138nb_agent as NB
import fable_decline224 as DEC

ART = Path(__file__).resolve().parent.parent / "artifacts" / "claude-diag293-20260923"

# (id, setup turns, final turn, arm, shape)
# arm: taught-true (stored value matches -> ideal Yes), taught-false
#   (stored different value -> ideal No), unknown (nothing stored -> ideal
#   IDK), taken-back (fact removed -> ideal IDK), control (statement or
#   wh-question; ideal = existing behavior).
# shape: does-have, is-poss, is-inv, does-live, does-work, does-from, has,
#   does-noart, is-of, stmt, wh.
D = [
    # ---- does-have: "Does A have an R?" ----
    ("dh-true1", ["Bex's dog is Biscuit."], "Does Bex have a dog?", "taught-true", "does-have"),
    ("dh-true2", ["Lena's mother is Wren."], "Does Lena have a mother?", "taught-true", "does-have"),
    ("dh-true-2word", ["Mary Ann's mother is Wren."], "Does Mary Ann have a mother?", "taught-true", "does-have"),
    ("dh-never1", ["Bex's mother is Talia."], "Does Bex have a dog?", "unknown", "does-have"),
    ("dh-never2", ["Rin's boss is Lee."], "Does Rin have a brother?", "unknown", "does-have"),
    ("dh-never-2word", ["Anna Lee's city is Oslo."], "Does Anna Lee have a dog?", "unknown", "does-have"),
    ("dh-taken-forget", ["Bex's dog is Biscuit.", "Forget Bex's dog."], "Does Bex have a dog?", "taken-back", "does-have"),
    ("dh-taken-isnot", ["Lena's mother is Wren.", "Lena's mother is not Wren."], "Does Lena have a mother?", "taken-back", "does-have"),
    ("dh-corrected", ["Lena's mother is Wren.", "Actually Lena's mother is Pell.", "Yes."], "Does Lena have a mother?", "taught-true", "does-have"),
    ("dh-noart", ["Lena's mother is Wren."], "Does Lena have mother?", "taught-true", "does-noart"),
    # ---- is-poss: "Is A's R B?" ----
    ("ip-true1", ["Bex's mother is Talia."], "Is Bex's mother Talia?", "taught-true", "is-poss"),
    ("ip-true2", ["Rin's city is Bergen."], "Is Rin's city Bergen?", "taught-true", "is-poss"),
    ("ip-true-2word", ["Mary Ann's mother is Wren."], "Is Mary Ann's mother Wren?", "taught-true", "is-poss"),
    ("ip-false1", ["Bex's mother is Talia."], "Is Bex's mother Wren?", "taught-false", "is-poss"),
    ("ip-false2", ["Rin's city is Bergen."], "Is Rin's city Oslo?", "taught-false", "is-poss"),
    ("ip-false-multi", ["Bex's sister is Ada."], "Is Bex's sister Bea?", "taught-false", "is-poss"),
    ("ip-unknown-rel", ["Bex's mother is Talia."], "Is Bex's father Talia?", "unknown", "is-poss"),
    ("ip-unknown-subj", ["Bex's mother is Talia."], "Is Zane's mother Talia?", "unknown", "is-poss"),
    ("ip-taken-forget", ["Bex's dog is Biscuit.", "Forget Bex's dog."], "Is Bex's dog Biscuit?", "taken-back", "is-poss"),
    ("ip-taken-isnot", ["Lena's mother is Wren.", "Lena's mother is not Wren."], "Is Lena's mother Wren?", "taken-back", "is-poss"),
    ("ip-correct-new", ["Lena's mother is Wren.", "Actually Lena's mother is Pell.", "Yes."], "Is Lena's mother Pell?", "taught-true", "is-poss"),
    ("ip-correct-old", ["Lena's mother is Wren.", "Actually Lena's mother is Pell.", "Yes."], "Is Lena's mother Wren?", "taught-false", "is-poss"),
    ("ip-ofform", ["Bex's mother is Talia."], "Is Talia the mother of Bex?", "taught-true", "is-of"),
    # ---- is-inv: "Is B A's R?" ----
    ("ii-true1", ["Bex's mother is Talia."], "Is Talia Bex's mother?", "taught-true", "is-inv"),
    ("ii-false1", ["Bex's mother is Talia."], "Is Wren Bex's mother?", "taught-false", "is-inv"),
    ("ii-unknown-subj", ["Bex's mother is Talia."], "Is Talia Zane's mother?", "unknown", "is-inv"),
    ("ii-unknown-rel", ["Bex's mother is Talia."], "Is Talia Bex's father?", "unknown", "is-inv"),
    ("ii-2word", ["Mary Ann's mother is Wren."], "Is Wren Mary Ann's mother?", "taught-true", "is-inv"),
    ("ii-taken", ["Bex's dog is Biscuit.", "Forget Bex's dog."], "Is Biscuit Bex's dog?", "taken-back", "is-inv"),
    ("ii-true2", ["Zane's city is Porto."], "Is Porto Zane's city?", "taught-true", "is-inv"),
    ("ii-false2", ["Zane's city is Porto."], "Is Oslo Zane's city?", "taught-false", "is-inv"),
    # ---- does-live: "Does A live in V?" ----
    ("dl-true", ["Rin's city is Bergen."], "Does Rin live in Bergen?", "taught-true", "does-live"),
    ("dl-false", ["Rin's city is Bergen."], "Does Rin live in Oslo?", "taught-false", "does-live"),
    ("dl-unknown", ["Bex's mother is Talia."], "Does Bex live in Oslo?", "unknown", "does-live"),
    ("dl-2word-true", ["Anna Lee's city is Oslo."], "Does Anna Lee live in Oslo?", "taught-true", "does-live"),
    ("dl-taken-forget", ["Zane's city is Porto.", "Forget Zane's city."], "Does Zane live in Porto?", "taken-back", "does-live"),
    ("dl-correct-new", ["Rin's city is Bergen.", "Actually Rin's city is Oslo.", "Yes."], "Does Rin live in Oslo?", "taught-true", "does-live"),
    ("dl-taken-isnot", ["Rin's city is Bergen.", "Rin's city is not Bergen."], "Does Rin live in Bergen?", "taken-back", "does-live"),
    # ---- does-work: "Does A work at/in V?" ----
    ("dw-sameval", ["Rin's city is Halden."], "Does Rin work at Halden?", "taught-true", "does-work"),
    ("dw-diffval", ["Rin's city is Halden."], "Does Rin work at Oslo?", "taught-false", "does-work"),
    ("dw-unknown", ["Bex's mother is Talia."], "Does Rin work at Halden?", "unknown", "does-work"),
    ("dw-2word", ["Anna Lee's city is Oslo."], "Does Anna Lee work at Oslo?", "taught-true", "does-work"),
    ("dw-taken", ["Rin's city is Halden.", "Forget Rin's city."], "Does Rin work at Halden?", "taken-back", "does-work"),
    # ---- does-from: "Does A come from V?" ----
    ("df-sameval", ["Rin's city is Bergen."], "Does Rin come from Bergen?", "taught-true", "does-from"),
    ("df-diffval", ["Rin's city is Bergen."], "Does Rin come from Oslo?", "taught-false", "does-from"),
    ("df-unknown", ["Bex's mother is Talia."], "Does Zane come from Porto?", "unknown", "does-from"),
    ("df-2word", ["Jo Marlowe's city is Oslo."], "Does Jo Marlowe come from Oslo?", "taught-true", "does-from"),
    ("df-taken", ["Zane's city is Porto.", "Zane's city is not Porto."], "Does Zane come from Porto?", "taken-back", "does-from"),
    # ---- has: "Has A a R?" ----
    ("h-true", ["Bex's dog is Biscuit."], "Has Bex a dog?", "taught-true", "has"),
    ("h-never", ["Bex's mother is Talia."], "Has Bex a dog?", "unknown", "has"),
    ("h-taken", ["Bex's dog is Biscuit.", "Forget Bex's dog."], "Has Bex a dog?", "taken-back", "has"),
    # ---- statement controls containing does/is (must not write, must not answer yes/no) ----
    ("s-does1", [], "Bex does judo on Tuesdays.", "control", "stmt"),
    ("s-does2", [], "Sam does the dishes every night.", "control", "stmt"),
    ("s-is1", [], "Ana is happy.", "control", "stmt"),
    ("s-is2", [], "The sky is blue.", "control", "stmt"),
    # ---- wh controls (existing behavior: answer / targeted decline) ----
    ("w-what-taught", ["Bex's mother is Talia."], "What is Bex's mother?", "control", "wh"),
    ("w-where-never", ["Bex's mother is Talia."], "Where does Zane live?", "control", "wh"),
    ("w-who-taken", ["Marko's boss is Lee.", "Forget Marko's boss."], "Who is Marko's boss?", "control", "wh"),
    ("w-inv-boundary", ["Bex's city is Oslo."], "Where lives Bex?", "control", "wh"),
    ("w-where-taught", ["Rin's city is Bergen."], "Where does Rin live?", "control", "wh"),
    ("w-born-never", ["Bex's mother is Talia."], "Where was Bex born?", "control", "wh"),
]

Q2 = DEC.NEW_SENTENCES224["Q2"]

def kind_of(reply):
    if reply == Q2:
        return "didnt-understand"
    low = reply.lower()
    if reply.startswith("Yes,") or reply.startswith("Yes "):
        return "yes"
    if reply.startswith("No,") or reply.startswith("No "):
        return "no"
    if low.startswith("not that i know of"):
        return "not-that-i-know"
    if "i don't know" in low or "i do not know" in low or "no record" in low:
        return "decline-targeted"
    if "couldn't save" in low or "could not store" in low or "don't know that shape" in low:
        return "nosave-clarify"
    return "answer-or-other"

def evcount(loop):
    try:
        return len(getattr(loop.nb, "nb", loop.nb).events)
    except Exception:
        return -1

def run():
    ART.mkdir(parents=True, exist_ok=True)
    out = ART / "rows.jsonl"
    if out.exists():
        out.unlink()
    base = copy.deepcopy(NB.DEFAULT_CONFIG138NB)
    n = 0
    for did, setup, q, arm, shape in D:
        sd = Path(tempfile.mkdtemp(prefix="nb293-"))
        cfg = copy.deepcopy(base); cfg["state_dir"] = str(sd); cfg["sleep_threshold"] = 100000
        loop = NB.build_agent138nb(cfg)
        seen = []
        outer = loop.ears.hear
        def hear_wrap(turn, _o=outer):
            a = _o(turn)
            seen.append([dict(x) if isinstance(x, dict) else x for x in (a or [])])
            return a
        loop.ears.hear = hear_wrap
        setup_replies = []
        for t in setup:
            seen.clear()
            setup_replies.append(" ".join(loop.turn(t)))
        seen.clear()
        e0 = evcount(loop)
        reply = " ".join(loop.turn(q))
        e1 = evcount(loop)
        acts = seen[-1] if seen else []
        lr = getattr(loop, "last_routed", None)
        inner = getattr(loop, "_inner138j_ears", None)
        row = {"id": did, "arm": arm, "shape": shape,
               "setup": setup, "setup_replies": setup_replies,
               "question": q, "reply": reply, "kind": kind_of(reply),
               "stage": str(getattr(loop.ears, "last_stage", "")),
               "inner_stage": str(getattr(inner, "last_stage", "")) if inner is not None else None,
               "acts": acts,
               "has_ask": any(isinstance(a, dict) and a.get("act") == "ask" for a in acts),
               "intent": lr.get("intent") if isinstance(lr, dict) else None,
               "ev0": e0, "ev1": e1,
               "d224": loop.decline224_log[-1] if getattr(loop, "decline224_log", None) else None,
               "q1c": loop.q1honest224c_log[-1] if getattr(loop, "q1honest224c_log", None) else None}
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        n += 1
        print(f"{did} [{arm}/{shape}] kind={row['kind']} stage={row['stage']!r} ask={row['has_ask']} ev={e0}->{e1} reply={reply[:70]!r}", flush=True)
        shutil.rmtree(sd, ignore_errors=True)
    print(f"WROTE {n} rows to {out}")

if __name__ == "__main__":
    assert len(D) >= 60, len(D)
    run()
