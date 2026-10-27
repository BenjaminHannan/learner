#!/usr/bin/env python3
"""Exp 138d M1 driver -- every IN piece's sealed probe re-run on loop138d.

Each piece's own sealed cases file is run through FRESH in-process loop138d
loops (sleep_threshold=100000, same harness shape as the probe runners:
build_agent with state_dir, loop.turn, triples via notebook_triples),
judged by the piece's sealed rule. Bars = the piece's sealed bar, with two
stated adaptations: (a) 146d-H2 dialogues H13/H17/H18 failed on 146c itself
for base reasons (authoring errors per its RESULTS) -- they must only be
reported here; (b) 138c 'hi' is answered by the 156b greeting stage before
the self layer is ever consulted (same by-construction class as 138c's own
B1-174) -- it must equal the sealed smalltalk greeting, the other 3 must
be base-verbatim.

Outputs artifacts/fable-agent138d-20260922/m1-138d.json. Bar: every piece
at its bar (see PASSMARKS.md).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138d_m1.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix156b_smalltalk as S156B  # noqa: E402 (class replies, read-only)
import fable_fix157_filler as F157  # noqa: E402 (strip rule, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop134_agent as L134  # noqa: E402 (base replies, read-only)
import fable_loop138_agent as L138  # noqa: E402 (decline const, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (comparison base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (agent under test)
import fable_self99 as S99  # noqa: E402 (decline markers, read-only)
import fable_self105 as S105  # noqa: E402 (decline text, read-only)

FALLBACK138D_PREFIX = "I do not understand that question"


def S99_MARKERS() -> list:
    return list(S99.DECLINE_MARKERS)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138d-20260922"


def fresh138d() -> object:
    tmp = tempfile.mkdtemp(prefix="m1-138d-")
    cfg = copy.deepcopy(L138d.DEFAULT_CONFIG138D)
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    return L138d.build_agent138d(cfg)


def fresh138b() -> object:
    tmp = tempfile.mkdtemp(prefix="m1-138b-")
    cfg = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    return L138b.build_agent138b(cfg)


def triples(loop) -> list:
    return [list(t) for t in L90.notebook_triples(loop.nb)]


def say(loop, text: str) -> str:
    return " ".join(loop.turn(text)).strip()


def fresh134() -> object:
    tmp = tempfile.mkdtemp(prefix="m1-134-")
    cfg = copy.deepcopy(L134.DEFAULT_CONFIG134)
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    return L134.build_agent134(cfg)


def run3(teaches: list, text: str):
    """One turn on fresh 138d / 138b / 134 loops with the same teaches.

    Returns (reply_d, reply_b, reply_134, triples_d, triples_b).
    """
    out = {}
    for tag, fresh in (("d", fresh138d), ("b", fresh138b),
                       ("134", fresh134)):
        loop = fresh()
        for t in teaches:
            say(loop, t)
        out[tag] = (" ".join(loop.turn(text)).strip(), triples(loop))
    return out["d"][0], out["b"][0], out["134"][0], out["d"][1], out["b"][1]


def base_preserved(teaches: list, text: str):
    """Uniform port bar: reply+triples == 138b, except notebook-missed
    turns (138b serves the mashed decline) where 138d must serve the
    loop134 base reply verbatim (the sealed 138c rule), plus the 138c
    footprint proper: a 138b self-served reply carrying a decline marker
    (served under the old rule) becomes the base reply under the grounded
    rule. Returns (ok, detail).
    """
    r_d, r_b, r_134, t_d, t_b = run3(teaches, text)
    if t_d != t_b:
        return False, f"triples {t_d} vs {t_b}"
    if r_d == r_b:
        return True, ""
    if r_b.startswith(S105.HONEST_DECLINE) and r_d == r_134:
        return True, "self-layer:miss-base"
    if r_d == r_134 and (any(m in r_b for m in
                             S99_MARKERS()) or r_b.startswith(
                             FALLBACK138D_PREFIX)):
        return True, "self-layer:ungrounded-was-served"
    return False, f"{r_d!r} vs {r_b!r}"


def run153() -> dict:
    cases = json.load(open(
        ROOT / "artifacts/fable-reverse153-20260922/cases153.json"))
    ok = bad = writes = 0
    fails = []
    for c in cases:
        loop = fresh138d()
        for t in c.get("setup", []):
            say(loop, t)
        n0 = len(triples(loop))
        reply = say(loop, c["question"])
        n1 = len(triples(loop))
        if n1 != n0:
            writes += 1
            fails.append(c["id"] + ":write")
            continue
        g = c["group"]
        want = c.get("want")
        if g.startswith("pos"):
            good = (want in reply) if isinstance(want, str) else True
        elif g == "multi":
            good = all(w in reply for w in want)
        else:  # neg: honest don't-know / clarify, never a bare name
            good = ("don't know" in reply or "didn't understand" in reply
                    or "Could you" in reply)
        if good:
            ok += 1
        else:
            bad += 1
            fails.append(c["id"] + ":" + reply[:80])
    return {"piece": "153", "n": len(cases), "ok": ok, "bad": bad,
            "qturn_writes": writes, "fails": fails,
            "pass": bad == 0 and writes == 0}


def run154() -> dict:
    cases = json.load(open(
        ROOT / "artifacts/fable-yesno154-20260922/cases154.json"))
    ok = bad = writes = 0
    fails = []
    for c in cases:
        loop = fresh138d()
        for t in c.get("teaches", []):
            say(loop, t)
        n0 = len(triples(loop))
        reply = say(loop, c["question"])
        if len(triples(loop)) != n0:
            writes += 1
            fails.append(c["id"] + ":write")
            continue
        e = c.get("expect")
        want = c.get("want", "")
        if e == "yes":
            good = reply.startswith("Yes") and want in reply
        elif e == "no-single":
            good = reply.startswith("No") and want in reply
        elif e == "only-know":
            good = "only know" in reply and want in reply
        elif e == "unknown":
            good = (not reply.startswith("Yes")
                    and not reply.startswith("No"))
        else:  # nowrite probes
            good = True
        if good:
            ok += 1
        else:
            bad += 1
            fails.append(c["id"] + ":" + reply[:80])
    return {"piece": "154", "n": len(cases), "ok": ok, "bad": bad,
            "qturn_writes": writes, "fails": fails,
            "pass": bad == 0 and writes == 0}


def run155x135() -> dict:
    cases = json.load(open(
        ROOT / "artifacts/fable-inverted155-20260922/cases155x135.json"))
    ok = bad = 0
    fails = []
    for c in cases:
        loop = fresh138d()
        reply = say(loop, c["teach"])
        if c["group"] == "must-write":
            stored = triples(loop)
            if list(c["expect"]) not in stored:
                bad += 1
                fails.append(c["id"] + ":nosave:" + reply[:60])
                continue
            ans = say(loop, c["ask"])
            if c["want"] in ans:
                ok += 1
            else:
                bad += 1
                fails.append(c["id"] + ":noask:" + ans[:60])
        else:  # office: byte-identical officeholder save, never inverted
            want_base = [list(t) for t in c["expect"]["base"]]
            if triples(loop) == want_base:
                ok += 1
            else:
                bad += 1
                fails.append(c["id"] + ":officewrite:" + reply[:60])
    return {"piece": "155x135", "n": len(cases), "ok": ok, "bad": bad,
            "fails": fails, "pass": bad == 0}


def judge_chat_shape(text: str):
    """Unified bar for small-talk-adjacent turns (156b near-misses, 156's
    T2 cases, 157 same-base cases): a 156b-classified turn must serve the
    sealed class reply with no writes (intended 156b win wherever the new
    base falls through); a filler-led turn must behave exactly like its
    stripped remainder (157 composition); anything else must preserve the
    base (==138b, or the 134 base on 138c-rule misses). Returns (ok, tag,
    detail).
    """
    cls = S156B.classify_156b(text)
    r_d, r_b, r_134, t_d, t_b = run3([], text)
    if cls is not None:
        good = (r_d == S156B.CLASS_REPLIES[cls] and t_d == t_b == [])
        return good, "class", ("" if good else f"class {r_d!r}")
    rest = F157.strip_one_filler157(text)
    if rest is not None:
        # Sealed 157 contract: the strip is ACCEPTED only when the
        # remainder parses complete (else the base result stands). Bar =
        # either the remainder outcome (accepted) or the preserved base
        # (rejected, e.g. one-strip-only "oh, and ..." or "by the way uh").
        loop_r = fresh138d()
        r_rest = say(loop_r, rest)
        t_rest = triples(loop_r)
        if r_d == r_rest and t_d == t_rest:
            return True, "strip-accepted", ""
        good, detail = base_preserved([], text)
        return good, "strip-rejected", detail
    good, detail = base_preserved([], text)
    return good, "base", detail


def run156b() -> dict:
    cases = json.load(open(
        ROOT / "artifacts/fable-smalltalk156b-20260922/cases156b.json"))
    ok = bad = writes = 0
    fails = []
    for c in cases:
        loop = fresh138d()
        n0 = len(triples(loop))
        reply = say(loop, c["text"])
        if c["kind"] == "smalltalk":
            if len(triples(loop)) != n0:
                writes += 1
                fails.append(c["id"] + ":write")
                continue
            cls = S156B.classify_156b(c["text"])
            good = (cls is not None
                    and reply == S156B.CLASS_REPLIES[cls])
        elif c["id"] == "N02":
            # Stack interaction (listed): "thanks, Bob is Tom's boss"
            # carries an inverted shape; 155 saves it with the small-talk
            # lead inside the value. Verified byte-identical on loop155
            # itself ("Saved: Tom's boss is thanks, Bob.") -- inherited
            # 155 edge, port-faithful bar.
            good = (reply.strip().startswith("Saved:") and triples(loop)
                    == [["Tom", "boss", "thanks, Bob"]])
            if not good:
                fails.append(c["id"] + ":" + reply[:80])
                bad += 1
                continue
        else:
            good, tag, detail = judge_chat_shape(c["text"])
            if not good:
                fails.append(c["id"] + ":" + tag + ":" + detail[:100])
                bad += 1
                continue
        if good:
            ok += 1
        else:
            bad += 1
            fails.append(c["id"] + ":" + reply[:60])
    cases2 = json.load(open(
        ROOT / "artifacts/fable-smalltalk156-20260922/cases156.json"))
    ok2 = bad2 = 0
    fails2 = []
    for c in cases2:
        # Same unified bar as T1 (these are 156-authored edge shapes):
        # classified turns serve class replies (intended 156b wins where
        # this base falls through), the rest preserve the base. The sealed
        # 9-vs-150 changes emerge as "class" tags; anything else is listed.
        text = c.get("text", "")
        good, tag, detail = judge_chat_shape(text)
        if good:
            ok2 += 1
        else:
            bad2 += 1
            fails2.append(str(c.get("id")) + ":" + tag + ":" + detail[:60])
    return {"piece": "156b", "n": len(cases), "ok": ok, "bad": bad,
            "writes": writes, "fails": fails,
            "t2": {"n": len(cases2), "ok": ok2, "bad": bad2,
                   "fails": fails2},
            "pass": bad == 0 and writes == 0 and bad2 == 0}


def run157() -> dict:
    cases = json.load(open(
        ROOT / "artifacts/fable-filler157-20260922/cases157.json"))
    ok = bad = 0
    fails = []
    for c in cases:
        if c["group"] == "filler":
            # Sealed 157 contract: the strip fires only when the base
            # clarifies the filler turn first. Filler turns the 138b base
            # already saves (137 possessives) keep the base save
            # (==138b filler turn, triples included); filler turns the
            # base clarifies must equal the bare reply (strip works).
            r_fill_b = run3([], c["filler"])[1]
            if r_fill_b.startswith(S105.HONEST_DECLINE):
                loop_f = fresh138d()
                r_f = say(loop_f, c["filler"])
                t_f = triples(loop_f)
                loop_b = fresh138d()
                r_b = say(loop_b, c["bare"])
                t_b = triples(loop_b)
                good = (r_f == r_b and t_f == t_b)
                detail = "" if good else f"strip {r_f!r} vs {r_b!r}"
            else:
                good, detail = base_preserved([], c["filler"])
            if not good:
                fails.append(c["id"] + ":" + detail[:100])
                bad += 1
                continue
            ok += 1
            continue
        if c["group"] in ("title", "same150"):
            if c["group"] == "same150":
                good, tag, detail = judge_chat_shape(c["text"])
            else:
                good, detail = base_preserved([], c["text"])
                tag = "base"
            if not good:
                fails.append(c["id"] + ":" + tag + ":" + detail[:100])
                bad += 1
                continue
            ok += 1
            continue
        good = (say(fresh138d(), c["text"])
                == say(fresh138b(), c["text"]))
        if good:
            ok += 1
        else:
            bad += 1
            fails.append(c["id"])
    return {"piece": "157", "n": len(cases), "ok": ok, "bad": bad,
            "fails": fails, "pass": bad == 0}


def run158() -> dict:
    cases = json.load(open(
        ROOT / "artifacts/fable-qform158-20260922/cases158.json"))
    ok = bad = writes = 0
    fails = []
    for c in cases:
        if c["kind"] == "pair":
            loop = fresh138d()
            for t in c.get("teaches", []):
                say(loop, t)
            n0 = len(triples(loop))
            r_v = say(loop, c["variant"])
            r_c = say(loop, c["canonical"])
            if len(triples(loop)) != n0:
                writes += 1
                fails.append(c["id"] + ":write")
                continue
            good = (r_v == r_c and c["want"] in r_v)
        else:
            good, detail = base_preserved(list(c.get("teaches", [])),
                                          c["text"])
            if not good:
                fails.append(c["id"] + ":" + detail[:100])
                bad += 1
                continue
            ok += 1
            continue
        if good:
            ok += 1
        else:
            bad += 1
            fails.append(c["id"] + ":" + r_v[:60] if c["kind"] == "pair"
                         else c["id"] + ":" + r_d[:60])
    return {"piece": "158", "n": len(cases), "ok": ok, "bad": bad,
            "writes": writes, "fails": fails,
            "pass": bad == 0 and writes == 0}


def run159() -> dict:
    cases = json.load(open(
        ROOT / "artifacts/fable-hop159-20260922/cases159.json"))
    ok = bad = writes = 0
    fails = []
    for c in cases:
        loop = fresh138d()
        for t in c.get("teaches", []):
            say(loop, t)
        n0 = len(triples(loop))
        reply = say(loop, c["question"])
        if len(triples(loop)) != n0:
            writes += 1
            fails.append(c["id"] + ":write")
            continue
        if c["expect"] == "answer":
            good = (c["want"] in reply)
        else:
            good, detail = base_preserved(list(c.get("teaches", [])),
                                          c["question"])
            if not good:
                fails.append(c["id"] + ":" + detail[:100])
                bad += 1
                continue
        if good:
            ok += 1
        else:
            bad += 1
            fails.append(c["id"] + ":" + reply[:80])
    return {"piece": "159", "n": len(cases), "ok": ok, "bad": bad,
            "qturn_writes": writes, "fails": fails,
            "pass": bad == 0 and writes == 0}


def run150b() -> dict:
    cases = json.load(open(
        ROOT / "artifacts/fable-subject150b-20260922/cases150b.json"))
    ok = bad = 0
    fails = []
    for c in cases:
        loop = fresh138d()
        text = c.get("text", "")
        reply = say(loop, text)
        exp = c.get("expect")
        if exp == "nowrite" and c.get("group") != "title-exempt":
            good = (len(triples(loop)) == 0
                    and "split" in reply.lower())
        elif c.get("group") == "title-exempt":
            # Possessive-title literals: loop150 clarifies, but the 138b
            # base 137-upgrades multi-Token possessives (inherited delta).
            # Bar = base preserved (==138b, or 134-base on misses).
            good, detail = base_preserved([], text)
            if not good:
                fails.append(str(c.get("id")) + ":" + detail[:100])
                bad += 1
                continue
            ok += 1
            continue
        else:
            good = (list(exp) in triples(loop)
                    and reply.strip().startswith("Saved:"))
        if good:
            ok += 1
        else:
            bad += 1
            fails.append(str(c.get("id")) + ":" + reply[:80])
    return {"piece": "150b", "n": len(cases), "ok": ok, "bad": bad,
            "fails": fails, "pass": bad == 0}


def run138c() -> dict:
    cases = json.load(open(
        ROOT / "artifacts/fable-self138c-20260922/probe_cases.json"))
    ok = bad = 0
    fails = []
    for c in cases:
        q = c["question"]
        r_d = say(fresh138d(), q)
        if q.strip().lower() == "hi":
            good = (r_d == S156B.CLASS_REPLIES[S156B.classify_156b(q)])
            note = "smalltalk-answers-first"
        else:
            good = (r_d == c["expected_base_reply"])
            note = "base-verbatim"
        if good:
            ok += 1
        else:
            bad += 1
            fails.append(q + ":" + note + ":" + r_d[:80])
    return {"piece": "138c", "n": len(cases), "ok": ok, "bad": bad,
            "fails": fails, "pass": bad == 0}


def run146d() -> dict:
    data = json.load(open(
        ROOT / "artifacts/fable-doubt146b-20260922/doubt146b-cases.json"))
    dialogues = data["dialogues"]
    exempt = {"H13-firstperson-negation", "H17-hearsay-then-reteach",
              "H18-refusal-then-reteach"}
    ok = bad = 0
    fails = []
    exempt_rep = []
    for d in dialogues:
        loop = fresh138d()
        good = True
        for s in d["steps"]:
            reply = say(loop, s["turn"])
            for bit in (s.get("expect_contains") or []):
                if bit not in reply:
                    good = False
            if ("doubts" in json.dumps(s)
                    and s.get("expect_final") == "doubt"):
                pass
        left = len(loop.doubt_store146.doubts)
        if left != d.get("expect_doubts", 0):
            good = False
        if d["id"] in exempt:
            exempt_rep.append({"id": d["id"], "ok": good})
            continue
        if good:
            ok += 1
        else:
            bad += 1
            fails.append(d["id"])
    return {"piece": "146d", "n": len(dialogues) - len(exempt),
            "ok": ok, "bad": bad, "fails": fails,
            "exempt_reported": exempt_rep,
            "pass": bad == 0}


NAMES = ["Ava", "Ben", "Cara", "Dan", "Eli", "Fay", "Gus", "Hal",
         "Ivy", "Jay", "Kay", "Leo", "Mia", "Ned", "Ola", "Pam"]
RELS = ["city", "color", "food", "mood", "pet", "song"]


def run142() -> dict:
    # Index-identity sample: ONLY 138b-answerable shapes (clean teaches +
    # plain asks on taught facts). Self-routed shapes ("Tell me about",
    # untaught asks) and the other ten pieces' shapes (Is/reverse/filler/
    # smalltalk/qform-variant/inverted/clause) are excluded by construction:
    # they are owned by other pieces' probes, not the index.
    turns = []
    for i in range(200):
        turns.append(f"{NAMES[i % 16]}'s {RELS[i % 6]} is V{i:03d}.")
    for i in range(300):
        turns.append(
            f"What is {NAMES[(i * 7) % 16]}'s {RELS[(i * 3) % 6]}?")
    lb = fresh138b()
    ld = fresh138d()
    diffs = []
    for idx, t in enumerate(turns):
        rb = say(lb, t)
        rd = say(ld, t)
        if rb != rd:
            diffs.append({"n": idx, "turn": t, "b": rb[:100],
                          "d": rd[:100]})
    return {"piece": "142", "n": len(turns), "diffs": diffs,
            "pass": len(diffs) == 0}


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "pieces": {}}
    rc = 0
    for fn in (run142, run138c, run146d, run153, run154, run155x135,
               run156b, run157, run158, run159, run150b):
        rep = fn()
        out["pieces"][rep["piece"]] = rep
        status = "PASS" if rep["pass"] else "FAIL"
        print(f"M1 {rep['piece']}: {status} "
              f"{json.dumps({k: v for k, v in rep.items() if k != 'pass'})[:300]}",
              flush=True)
        if not rep["pass"]:
            rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "m1-138d.json").write_text(json.dumps(out, indent=1,
                                                 sort_keys=True),
                                      encoding="utf-8")
    print(f"M1 done in {out['seconds']}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
