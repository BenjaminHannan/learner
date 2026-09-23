#!/usr/bin/env python3
"""Exp 290-diag main run: 44 dev dialogs (own wording, fictional names) on
138k, 138l, 138m. Fresh temp state_dir per dialog, sleep_threshold 100000.
Records reply, ears.last_stage, emitted acts, last_routed intent, event
counts (writes), decline224 / q1honest224c logs. Writes JSONL rows to
artifacts/claude-diag290-20260923/rows.jsonl. New file only; additive."""
from __future__ import annotations
import copy, json, shutil, sys, tempfile
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import claude_loop138k_agent as K
import claude_loop138l_agent as L
import claude_loop138m_agent as M
import fable_decline224 as DEC

ART = Path(__file__).resolve().parent.parent / "artifacts" / "claude-diag290-20260923"

# (id, setup turns, final question, arm, shape)
D = [
    # taught forwards (expect answer; Does-shape is the known-unparsed case)
    ("t-what-mother", ["Bex's mother is Talia."], "What is Bex's mother?", "taught", "What"),
    ("t-what-city", ["Bex's city is Oslo."], "What is Bex's city?", "taught", "What"),
    ("t-where-live", ["Rin's city is Bergen."], "Where does Rin live?", "taught", "Where"),
    ("t-where-live2", ["Zane's city is Porto."], "Where does Zane live?", "taught", "Where"),
    ("t-who-mother", ["Lena's mother is Wren."], "Who is Lena's mother?", "taught", "Who"),
    ("t-who-boss", ["Marko's boss is Lee."], "Who is Marko's boss?", "taught", "Who"),
    ("t-does-dog", ["Bex's dog is Biscuit."], "Does Bex have a dog?", "taught", "Does"),
    ("t-does-mother", ["Lena's mother is Wren."], "Does Lena have a mother?", "taught", "Does"),
    # never taught (expect honest decline)
    ("n-what-father", ["Bex's mother is Talia."], "What is Bex's father?", "never", "What"),
    ("n-what-hobby", ["Bex's mother is Talia."], "What is Bex's hobby?", "never", "What"),
    ("n-what-teacher", ["Rin's boss is Lee."], "What is Rin's teacher?", "never", "What"),
    ("n-what-school", ["Bex's mother is Talia."], "What is Bex's school?", "never", "What"),
    ("n-what-pet", ["Rin's boss is Lee."], "What is Rin's pet?", "never", "What"),
    ("n-where-live", ["Bex's mother is Talia."], "Where does Bex live?", "never", "Where"),
    ("n-where-work", ["Bex's mother is Talia."], "Where does Bex work?", "never", "Where"),
    ("n-where-unknown", ["Bex's mother is Talia."], "Where does Zane live?", "never", "Where"),
    ("n-where-born", ["Bex's mother is Talia."], "Where was Bex born?", "never", "Where"),
    ("n-who-father", ["Bex's mother is Talia."], "Who is Bex's father?", "never", "Who"),
    ("n-who-boss", ["Lena's mother is Wren."], "Who is Lena's boss?", "never", "Who"),
    ("n-who-coach", ["Rin's boss is Lee."], "Who is Rin's coach?", "never", "Who"),
    ("n-who-sister", ["Bex's mother is Talia."], "Who is Bex's sister?", "never", "Who"),
    ("n-does-dog", ["Bex's mother is Talia."], "Does Bex have a dog?", "never", "Does"),
    ("n-does-hobby", ["Bex's mother is Talia."], "Does Bex have a hobby?", "never", "Does"),
    ("n-does-unknown", ["Bex's mother is Talia."], "Does Zane have a dog?", "never", "Does"),
    ("n-does-brother", ["Rin's boss is Lee."], "Does Rin have a brother?", "never", "Does"),
    # taken back by a correction (expect honest decline about the old fact)
    ("b-what-forget", ["Bex's mother is Talia.", "Forget Bex's mother."], "What is Bex's mother?", "taken-back", "What"),
    ("b-what-isnot", ["Rin's boss is Lee.", "Rin's boss is not Lee."], "What is Rin's boss?", "taken-back", "What"),
    ("b-what-replace", ["Lena's mother is Wren.", "Actually Lena's mother is Pell.", "Yes."], "What is Lena's mother?", "taken-back", "What"),
    ("b-where-forget", ["Bex's city is Oslo.", "Forget Bex's city."], "Where does Bex live?", "taken-back", "Where"),
    ("b-where-isnot", ["Zane's city is Porto.", "Zane's city is not Porto."], "Where does Zane live?", "taken-back", "Where"),
    ("b-who-forget", ["Marko's boss is Lee.", "Forget Marko's boss."], "Who is Marko's boss?", "taken-back", "Who"),
    ("b-who-isnot", ["Lena's mother is Wren.", "Lena's mother is not Wren."], "Who is Lena's mother?", "taken-back", "Who"),
    ("b-does-forget", ["Bex's dog is Biscuit.", "Forget Bex's dog."], "Does Bex have a dog?", "taken-back", "Does"),
    ("b-does-isnot", ["Bex's dog is Biscuit.", "Bex's dog is not Biscuit."], "Does Bex have a dog?", "taken-back", "Does"),
    ("b-does-mother-isnot", ["Lena's mother is Wren.", "Lena's mother is not Wren."], "Does Lena have a mother?", "taken-back", "Does"),
    ("b-does-replace", ["Lena's mother is Wren.", "Actually Lena's mother is Pell.", "Yes."], "Does Lena have a mother?", "taken-back", "Does"),
    # shape boundary probes
    ("x-where-inv", ["Bex's city is Oslo."], "Where lives Bex?", "boundary", "Where"),
    ("x-who-of", ["Bex's mother is Talia."], "Who is mother of Bex?", "boundary", "Who"),
    ("x-what-of", ["Bex's city is Oslo."], "What is the city of Bex?", "boundary", "What"),
    ("x-does-noart", ["Lena's mother is Wren."], "Does Lena have mother?", "boundary", "Does"),
    ("x-has", ["Bex's dog is Biscuit."], "Has Bex a dog?", "boundary", "Does"),
    ("x-is", ["Bex's mother is Talia."], "Is Bex's mother Talia?", "boundary", "Does"),
]

GLUE = ("I do not know that from what you taught me. I have no record of it, "
        "so I will not guess. I didn't understand that, I don't know "
        "\u2014 could you say it another way?")
Q1 = DEC.NEW_SENTENCES224["Q1"]
Q2 = DEC.NEW_SENTENCES224["Q2"]
S1 = DEC.NEW_SENTENCES224["S1"]

def kind_of(reply):
    if reply in (Q2, S1):
        return "didnt-understand"
    if reply == Q1:
        return "decline-q1"
    if reply == GLUE:
        return "decline-glue"
    low = reply.lower()
    if "i don't know" in low or "i do not know" in low or "no record" in low:
        return "decline-targeted"
    return "answer-or-other"

MODS = {"138k": (K, "build_agent138k", "DEFAULT_CONFIG138K"),
        "138l": (L, "build_agent138l", "DEFAULT_CONFIG138L"),
        "138m": (M, "build_agent138m", "DEFAULT_CONFIG138M")}

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
    n = 0
    for tag, (mod, bname, cname) in MODS.items():
        base = copy.deepcopy(getattr(mod, cname))
        for did, setup, q, arm, shape in D:
            sd = Path(tempfile.mkdtemp(prefix="nb290-"))
            cfg = copy.deepcopy(base); cfg["state_dir"] = str(sd); cfg["sleep_threshold"] = 100000
            loop = getattr(mod, bname)(cfg)
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
            row = {"agent": tag, "id": did, "arm": arm, "shape": shape,
                   "setup": setup, "setup_replies": setup_replies,
                   "question": q, "reply": reply, "kind": kind_of(reply),
                   "stage": str(getattr(loop.ears, "last_stage", "")),
                   "acts": acts,
                   "has_ask": any(isinstance(a, dict) and a.get("act") == "ask" for a in acts),
                   "intent": lr.get("intent") if isinstance(lr, dict) else None,
                   "ev0": e0, "ev1": e1,
                   "d224": loop.decline224_log[-1] if getattr(loop, "decline224_log", None) else None,
                   "q1c": loop.q1honest224c_log[-1] if getattr(loop, "q1honest224c_log", None) else None}
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            n += 1
            print(f"{tag} {did} [{arm}/{shape}] kind={row['kind']} ask={row['has_ask']} intent={row['intent']} ev={e0}->{e1} reply={reply}", flush=True)
            shutil.rmtree(sd, ignore_errors=True)
    print(f"WROTE {n} rows to {out}")

if __name__ == "__main__":
    assert len(D) >= 40, len(D)
    run()
