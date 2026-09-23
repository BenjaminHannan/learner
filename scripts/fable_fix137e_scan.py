#!/usr/bin/env python3
"""Experiment 137e pre-seal scanner -- real agent on every suite input.

Runs the REAL loop137e and loop137c agents (fresh in-process loops,
same build as the registered runs) on EVERY input text of every
regression suite, single-turn reply + notebook writes compared
per-input. This is not a regex scan: frame_kind is the agent's own
matcher, and every firing input is executed live on both agents (plus
a [frame, question] follow-up pair for firing inputs).

Sources (same files the registered drivers read, read-only):
  bench121 G1: DATA_NEW/DATA_OLD (sentence_en + question) + edit200 +
    bench132 rows
  marks123 G2: RC.CASES steps, p4-innocent-30 setup+text, rt110 cases
    (top-level text + steps[].text), q1 fixed turns, bench113 A/B items,
    rt81 SEQS turns, soak templates
  G3: sessions152 turns, rt143 cases, rt136 cases, cases150, f1, cases139b

Predictions are written into PASSMARKS.md from this scan's counts.
Dev-only: output goes to the artifact dir but is sealed with the rest
(no registered run has happened yet when this runs).

Run (Mac CPU, offline; BEFORE the seal):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137e_scan.py
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

import fable_fix137d_frame as F137D  # noqa: E402 (matcher under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop137c_agent as L137C  # noqa: E402 (frozen base, read-only)
import fable_loop137e_agent as L137E  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-frame137e-20260922"
ART137C = ROOT / "artifacts" / "fable-hypo137c-20260922"


def fresh(kind: str):
    cfg = copy.deepcopy(L137E.DEFAULT_CONFIG137E if kind == "137e"
                        else L137C.DEFAULT_CONFIG137C)
    cfg["state_dir"] = tempfile.mkdtemp(prefix=f"scan137e_{kind}_")
    cfg["sleep_threshold"] = 100000
    return (L137E.build_agent137e(cfg) if kind == "137e"
            else L137C.build_agent137c(cfg))


def once(kind: str, turn: str) -> tuple[str, list]:
    loop = fresh(kind)
    reply = " ".join(loop.turn(turn))
    triples = [list(t) for t in L90.notebook_triples(loop.nb)]
    return reply, triples


def pair(kind: str, turns: list[str]) -> tuple[list[str], list]:
    loop = fresh(kind)
    replies = [" ".join(loop.turn(t)) for t in turns]
    triples = [list(t) for t in L90.notebook_triples(loop.nb)]
    return replies, triples


def collect() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    # G1 bench121.
    import fable_bench121_run as B  # noqa: E402 (read-only)
    bench_texts: list[str] = []
    for path in (B.DATA_NEW, B.DATA_OLD,
                 ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl",
                 ROOT / "data" / "open" / "bench132"
                 / "fable_edit132_4hop.jsonl"):
        for line in Path(str(path)).read_text(
                encoding="utf-8").splitlines():
            if not line.strip():
                continue
            it = json.loads(line)
            for key in ("sentence_en", "question", "taught", "text"):
                if isinstance(it.get(key), str):
                    bench_texts.append(it[key])
    out["bench121"] = bench_texts
    # G2 marks123.
    import fable_redteam98_cases as RC  # noqa: E402 (read-only)
    p2t = [s.get("text", "") for c in RC.CASES
           for s in c.get("steps", []) if isinstance(s.get("text"), str)]
    out["p2"] = p2t
    p4 = json.loads((ROOT / "artifacts" / "fable-fix102-20260922"
                     / "p4-innocent-30.json").read_text(encoding="utf-8")) \
        if (ROOT / "artifacts" / "fable-fix102-20260922"
            / "p4-innocent-30.json").exists() else None
    if p4 is None:
        import fable_marks123_all as M123  # noqa: E402 (paths, read-only)
        p4path = M123.ART102 / "p4-innocent-30.json"
        p4 = json.loads(p4path.read_text(encoding="utf-8"))
    out["p4"] = [t for item in p4["sentences"]
                 for t in (list(item.get("setup", [])) + [item["text"]])]
    import fable_marks123_all as M123  # noqa: E402 (paths, read-only)
    rt110 = json.loads((M123.ART110 / "fable_redteam110_cases.json")
                       .read_text(encoding="utf-8"))
    rt110t: list[str] = []
    for c in rt110:
        if isinstance(c.get("text"), str):
            rt110t.append(c["text"])
        for st in c.get("steps", []) or []:
            if isinstance(st.get("text"), str):
                rt110t.append(st["text"])
    out["rt110"] = rt110t
    out["q1"] = ["Mira's city is Lisbon.", "Please forget Mira city",
                 "Mira's city is Paris.", "Who is Mira's city?",
                 "WHO IS MIRA'S CITY?"]
    import fable_bench113_run as B113  # noqa: E402 (read-only)
    b113t: list[str] = []
    for path in (B113.DATA_A, B113.DATA_B):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            it = json.loads(line)
            for key in ("sentence_en", "question", "taught", "text"):
                if isinstance(it.get(key), str):
                    b113t.append(it[key])
    out["bench113"] = b113t
    import fable_redteam81_probe as P81  # noqa: E402 (read-only)
    out["rt81"] = [st["turn"] for _, _, steps in P81.SEQS for st in steps
                   if isinstance(st.get("turn"), str)
                   and st["turn"] != "__SETUP_SECOND_MIRA__"]
    out["soak"] = (["SoakP%03d's city is SoakV%03d." % (i, i)
                    for i in range(200)]
                   + ["Actually, SoakP%03d's city is SoakW%03d." % (i, i)
                      for i in range(40)]
                   + ["What is SoakP%03d's city?" % i for i in range(200)])
    # G3.
    import fable_session152_run as S152R  # noqa: E402 (read-only)
    out["sessions152"] = [t.get("text", "") for s in S152R.S152.SESSIONS
                          for t in s.get("turns", [])]
    import fable_redteam143_run as R143  # noqa: E402 (read-only)
    suite143 = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    rt143t: list[str] = []
    for c in suite143["cases"]:
        for key in ("text", "teach", "ask", "question"):
            if isinstance(c.get(key), str):
                rt143t.append(c[key])
        for t in c.get("turns", []) or []:
            if isinstance(t, str):
                rt143t.append(t)
            elif isinstance(t, dict) and isinstance(t.get("text"), str):
                rt143t.append(t["text"])
    out["rt143"] = rt143t
    rt136 = json.loads((ROOT / "artifacts" / "fable-redteam136-20260922"
                        / "cases136.json").read_text(encoding="utf-8"))
    if isinstance(rt136, dict):
        rt136 = rt136.get("cases", rt136)
    out["rt136"] = [c.get("text", "") for c in rt136
                    if isinstance(c.get("text"), str)]
    c150 = json.loads((ROOT / "artifacts" / "fable-fix150-20260922"
                       / "cases150.json").read_text(encoding="utf-8"))
    out["cases150"] = [c.get("text", "") for c in c150
                       if isinstance(c.get("text"), str)]
    f1 = json.loads((ROOT / "artifacts" / "fable-fix144-20260922"
                     / "f1-cases.json").read_text(encoding="utf-8"))["cases"]
    out["f1"] = [c.get("text", "") for c in f1
                 if isinstance(c.get("text"), str)]
    c139b = json.loads((ROOT / "artifacts" / "fable-fix139b-20260922"
                        / "cases139b.json").read_text(encoding="utf-8"))
    c139 = json.loads((ROOT / "artifacts" / "fable-fix139-20260922"
                       / "cases139.json").read_text(encoding="utf-8"))
    if isinstance(c139, dict):
        c139 = c139.get("cases", c139)
    out["cases139b"] = [c.get("text", "") for c in list(c139) + list(c139b)
                        if isinstance(c.get("text"), str)]
    return out


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    suites = collect()
    rep: dict = {"seconds": 0.0, "suites": {}}
    total_fires: list = []
    total_mismatch = 0
    for name, texts in suites.items():
        fires: list = []
        mismatches: list = []
        for t in texts:
            k = F137D.frame_kind(t)
            if k is None:
                continue
            fires.append({"text": t[:120], "kind": k})
            rc, wc = once("137c", t)
            re_, we = once("137e", t)
            if rc != re_ or wc != we:
                mismatches.append({"text": t[:120], "kind": k,
                                   "reply137c": rc[:120],
                                   "reply137e": re_[:120],
                                   "w137c": wc, "w137e": we})
                total_mismatch += 1
        # Follow-up pair check on firing inputs: [frame, question].
        fu_bad = 0
        for f in fires[:40]:
            q = "What is Kim's boss?"
            rc2, wc2 = pair("137c", [f["text"], q])
            re2, we2 = pair("137e", [f["text"], q])
            if rc2 != re2 or wc2 != we2:
                fu_bad += 1
                mismatches.append({"text": f["text"][:120] + " + Q",
                                   "kind": "followup",
                                   "reply137c": rc2, "reply137e": re2,
                                   "w137c": wc2, "w137e": we2})
                total_mismatch += 1
        rep["suites"][name] = {"n": len(texts), "fires": len(fires),
                               "mismatches": len(mismatches),
                               "fire_list": fires[:60],
                               "mismatch_list": mismatches[:60],
                               "followup_bad": fu_bad}
        total_fires.extend({**f, "suite": name} for f in fires)
        print(f"scan {name}: n={len(texts)} fires={len(fires)} "
              f"mismatches={len(mismatches)} fu_bad={fu_bad}", flush=True)
        for f in fires[:12]:
            print(f"  FIRE [{f['kind']}] {f['text'][:100]}", flush=True)
        for m in mismatches[:12]:
            print(f"  MISMATCH {m}", flush=True)
    rep["seconds"] = round(time.time() - t0, 1)
    rep["total_mismatch"] = total_mismatch
    (ART / "scan137e-prescan.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"scan done {rep['seconds']}s total_mismatch={total_mismatch}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
