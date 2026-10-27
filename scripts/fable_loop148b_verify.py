#!/usr/bin/env python3
"""Exp 148b verifier -- check R1-R4 against the sealed PASSMARKS predictions.

Reads (never writes, except its own report file):
  148b outputs: artifacts/fable-screen148b-20260922/
  148 outputs (sealed reference): artifacts/fable-screen148-20260922/
Compares per-item verdicts/replies (R1, R2), marks123 arms 148b-vs-134base
(R3), and timings + daemon idle_seconds (R4). Prints a verdict per R and
exits nonzero on any unpredicted diff.

Run AFTER all registered runs (does not itself evaluate the agent):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop148b_verify.py
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ARTB = ROOT / "artifacts" / "fable-screen148b-20260922"
ART8 = ROOT / "artifacts" / "fable-screen148-20260922"

ABSTAIN = ("MISSING_FACT", "BROKEN_CHAIN", "UNKNOWN_ENTITY", "AMBIGUOUS")
TIME_LIT = "not years or 'as of'"
NEG_LIT = "can't do 'not'"


def load_rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8")
            .splitlines() if l.strip()]


def check_r1(out: list[str]) -> bool:
    ok = True
    # Q1: verdicts + full reply texts vs 148's report rows.
    mine = {r["id"]: r for r in json.loads(
        (ARTB / "fable_q1_143_on132plus148b_results.json").read_text(
            encoding="utf-8"))["rows"]}
    ref = {r["id"]: r for r in json.loads(
        (ART8 / "fable_q1_143_on132plus148_results.json").read_text(
            encoding="utf-8"))["rows"]}
    vd = sorted(i for i in ref if mine.get(i, {}).get("verdict")
                != ref[i]["verdict"])
    rd = sorted(i for i in ref if mine.get(i, {}).get("reply")
                != ref[i]["reply"])
    tgt = json.loads((ARTB / "fable_q1_summary148b.json").read_text(
        encoding="utf-8"))
    out.append(f"R1-Q1: verdict_diffs={vd} reply_diffs={rd} "
               f"targets_no_confident={tgt['n_target_no_confident_answer']}/8 "
               f"worse={tgt['worse_ids']}")
    ok &= (not vd and not rd and tgt["n_target_no_confident_answer"] == 8
           and not tgt["worse_ids"])
    # Q2: verdicts + 148b replies vs 148's reply148 per probe.
    mine2 = {r["id"]: r for r in json.loads(
        (ARTB / "fable_q2_report148b.json").read_text(
            encoding="utf-8"))["rows"]}
    ref2 = {r["id"]: r for r in json.loads(
        (ART8 / "fable_q2_report.json").read_text(
            encoding="utf-8"))["rows"]}
    vd2 = sorted(i for i in ref2 if mine2.get(i, {}).get("verdict")
                 != ref2[i]["verdict"])
    rd2 = sorted(i for i in ref2 if mine2.get(i, {}).get("reply148b")
                 != ref2[i]["reply148"])
    r2 = json.loads((ARTB / "fable_q2_report148b.json").read_text(
        encoding="utf-8"))
    out.append(f"R1-Q2: verdict_diffs={vd2} reply_diffs_vs_148={rd2} "
               f"trigger={r2['trigger_ok']}/{r2['trigger_n']} "
               f"innocent={r2['innocent_ok']}/{r2['innocent_n']}")
    ok &= (not vd2 and not rd2 and r2["trigger_ok"] == 20
           and r2["innocent_ok"] == 20)
    return ok


def check_r2(out: list[str]) -> bool:
    ok = True
    tags = {"edit200": "edit200", "old_s2fresh_4hop": "old_s2fresh_4hop",
            "new_121_4hop": "new_121_4hop", "new_132_4hop": "new_132_4hop"}
    ref_tags = {"edit200": "edit200", "old_s2fresh_4hop": "old_s2fresh_4hop",
                "new_121_4hop": "new_121_4hop", "new_132_4hop": "new_132_4hop"}
    n = 0
    for tag in tags:
        mine = {r["id"]: r for r in load_rows(
            ARTB / f"fable_bench148b_loop148b_{tag}_rows.jsonl")}
        ref = {r["id"]: r for r in load_rows(
            ART8 / f"fable_bench148_loop148_{ref_tags[tag]}_rows.jsonl")}
        vd = sorted(i for i in ref if mine.get(i, {}).get("verdict")
                    != ref[i]["verdict"])
        rd = sorted(i for i in ref if mine.get(i, {}).get("reply")
                    != ref[i]["reply"])
        out.append(f"R2-{tag}: n={len(ref)} verdict_diffs={vd} "
                   f"reply_diffs={rd}")
        n += len(ref)
        ok &= (not vd and not rd and len(ref) == len(mine))
    out.append(f"R2: {n} per-item verdicts checked vs 148's rows")
    return ok and n == 800


def _canon(obj) -> str:
    if isinstance(obj, dict):
        return "{" + ",".join(
            f"{k!r}:{_canon(obj[k])}" for k in sorted(obj)
            if k != "seconds") + "}"
    if isinstance(obj, list):
        return "[" + ",".join(_canon(v) for v in obj) + "]"
    return json.dumps(obj, sort_keys=True)


def check_r3(out: list[str]) -> bool:
    ok = True
    new, base = ARTB / "marks123-148b", ARTB / "marks123-134base"
    # P2: per-case agent verdicts; only P2-D8 may move (sealed BUG -> OK).
    pn = {r["id"]: r["agent_verdict"] for r in json.loads(
        (new / "p2-report.json").read_text(encoding="utf-8"))["rows"]}
    pb = {r["id"]: r["agent_verdict"] for r in json.loads(
        (base / "p2-report.json").read_text(encoding="utf-8"))["rows"]}
    diff = sorted(i for i in pb if pn.get(i) != pb[i])
    d8 = (pb.get("D8"), pn.get("D8"))
    out.append(f"R3-P2: diffs={diff} D8 base->new={d8}")
    ok &= (diff == ["D8"] and d8 == ("BUG", "OK"))
    # P3 L5-Z1: per-turn observed; only turns 42/43 may differ.
    z1n = {t["n"]: t for t in json.loads(
        (new / "p3" / "l5z1-report.json").read_text(
            encoding="utf-8"))["per_turn"]}
    z1b = {t["n"]: t for t in json.loads(
        (base / "p3" / "l5z1-report.json").read_text(
            encoding="utf-8"))["per_turn"]}
    zdiff = sorted(n for n in z1b if z1n.get(n, {}).get("observed")
                   != z1b[n]["observed"])
    obs42 = {n: z1n[n]["observed"] for n in (42, 43)}
    wrong = (json.loads((new / "p3" / "l5z1-report.json").read_text(
        encoding="utf-8"))["wrong_writes"])
    out.append(f"R3-L5Z1: diffs={zdiff} observed42/43={obs42} "
               f"wrong_writes={wrong}")
    ok &= (zdiff == [42, 43]
           and obs42 == {42: "UNSUPPORTED_QUESTION",
                         43: "UNSUPPORTED_QUESTION"} and wrong == 0)
    # P3 L5-Z2: per-item verdicts identical; reply-diffs are the never-items,
    # each MISSING_FACT (in ABSTAIN) -> abstain_ok in both arms.
    w2n = {r["id"]: r for r in json.loads(
        (new / "p3" / "l5z2-report.json").read_text(
            encoding="utf-8"))["rows"]}
    w2b = {r["id"]: r for r in json.loads(
        (base / "p3" / "l5z2-report.json").read_text(
            encoding="utf-8"))["rows"]}
    wdiff = sorted(i for i in w2b if w2n.get(i, {}).get("verdict")
                   != w2b[i]["verdict"])
    rdiff = sorted(i for i in w2b if w2n.get(i, {}).get("said")
                   != w2b[i]["said"])
    never_ok = all(w2n[i]["status"] in ABSTAIN
                   and w2n[i]["verdict"] == "abstain_ok"
                   and w2b[i]["verdict"] == "abstain_ok" for i in rdiff)
    miss = [i for i in w2n if w2n[i]["verdict"] == "MISS"]
    out.append(f"R3-L5Z2: verdict_diffs={wdiff} reply_diffs_n={len(rdiff)} "
               f"all_abstain_ok={never_ok} MISS={miss}")
    ok &= (not wdiff and len(rdiff) == 37 and never_ok and not miss)
    # P3 other suites: identical verdict-level state (race-prone harness
    # diagnostics excluded: L6 replied_before_kill/seconds; rt110 statuses
    # log field, which races the daemon log flush — replies, verdict rows,
    # and fact_writes are compared exactly).
    for suite in ("l1", "l2", "l3", "l4"):
        rn = json.loads((new / "p3" / f"{suite}-report.json").read_text(
            encoding="utf-8"))
        rb = json.loads((base / "p3" / f"{suite}-report.json").read_text(
            encoding="utf-8"))
        same = _canon(rn) == _canon(rb)
        out.append(f"R3-{suite.upper()}: identical={same} "
                   f"pass={rb.get('pass')}/{rn.get('pass')}")
        ok &= same
    l6n = json.loads((new / "p3" / "l6-report.json").read_text(
        encoding="utf-8"))
    l6b = json.loads((base / "p3" / "l6-report.json").read_text(
        encoding="utf-8"))
    seeds_n = [{k: s[k] for k in ("seed", "pass", "correct", "wrong",
                                  "unanswered", "dupes", "chain_ok",
                                  "torn_reported")} for s in l6n["per_seed"]]
    seeds_b = [{k: s[k] for k in ("seed", "pass", "correct", "wrong",
                                  "unanswered", "dupes", "chain_ok",
                                  "torn_reported")} for s in l6b["per_seed"]]
    l6_same = seeds_n == seeds_b and l6n["pass"] and l6b["pass"]
    out.append(f"R3-L6: verdict-state identical={l6_same} "
               f"(replied_before_kill race field excluded: "
               f"{[s.get('replied_before_kill') for s in l6b['per_seed']]} vs "
               f"{[s.get('replied_before_kill') for s in l6n['per_seed']]})")
    ok &= l6_same
    # Remaining suites: verdict-level identity. rt110's per-turn `statuses`
    # log field is harness timing noise (daemon log flush races outbox read;
    # the sealed judge never reads it): replies, verdict rows, and
    # fact_writes are compared exactly. sleep's SKIP reason differs only by
    # agent filename (exp-150 precedent).
    for rep in ("p4-report.json", "q1-report.json",
                "rt81-report.json", "soak-report.json", "q4-report.json"):
        rn = json.loads((new / rep).read_text(encoding="utf-8"))
        rb = json.loads((base / rep).read_text(encoding="utf-8"))
        same = _canon(rn) == _canon(rb)
        out.append(f"R3-{rep}: identical={same}")
        ok &= same
    rn = json.loads((new / "rt110-report.json").read_text(encoding="utf-8"))
    rb = json.loads((base / "rt110-report.json").read_text(encoding="utf-8"))
    r_meta = all(k in ("n", "mark", "seconds") or rn.get(k) == rb.get(k)
                 for k in set(rn) | set(rb) if k != "rows")
    r_rows = True
    st_noise = 0
    for a, b in zip(sorted(rn["rows"], key=lambda r: r["id"]),
                    sorted(rb["rows"], key=lambda r: r["id"])):
        if a["id"] != b["id"]:
            r_rows = False
            break
        r_rows &= (a["agent_verdict"] == b["agent_verdict"]
                   and a["sealed_verdict"] == b["sealed_verdict"])
        la = [(e.get("file"), e.get("reply"), e.get("fact_writes"))
              for e in a["log"]]
        lb = [(e.get("file"), e.get("reply"), e.get("fact_writes"))
              for e in b["log"]]
        r_rows &= (la == lb)
        st_noise += sum(
            1 for ea, eb in zip(a["log"], b["log"])
            if ea.get("statuses") != eb.get("statuses"))
    out.append(f"R3-rt110: verdicts+replies+writes identical={bool(r_meta and r_rows)} "
               f"statuses-log-only diffs={st_noise} (harness race, unjudged)")
    ok &= bool(r_meta and r_rows)
    sn = json.loads((new / "sleep-report.json").read_text(encoding="utf-8"))
    sb = json.loads((base / "sleep-report.json").read_text(encoding="utf-8"))
    reason_same = (sn["reason"].replace("fable_loop148b_agent.py", "X")
                   == sb["reason"].replace("fable_loop134_agent.py", "X"))
    sleep_same = (sn["pass"] and sb["pass"] and sn.get("skipped")
                  and sb.get("skipped") and reason_same)
    out.append(f"R3-sleep: SKIP both, reason filename-only diff={sleep_same}")
    ok &= sleep_same
    for tag in ("fable_edit_200", "s2fresh_4hop"):
        rn = [json.loads(l) for l in
              (new / f"bench-rows-{tag}.jsonl").read_text(
                  encoding="utf-8").splitlines() if l.strip()]
        rb = [json.loads(l) for l in
              (base / f"bench-rows-{tag}.jsonl").read_text(
                  encoding="utf-8").splitlines() if l.strip()]
        vn = {r["id"]: r["verdict"] for r in rn}
        vb = {r["id"]: r["verdict"] for r in rb}
        vdiff = sorted(i for i in vb if vn.get(i) != vb[i])
        rdiff = sorted(i for i in vb
                       if next(r["reply"] for r in rn
                               if r["id"] == i) != next(
                               r["reply"] for r in rb if r["id"] == i))
        screen_only = all(
            (NEG_LIT in next(r["reply"] for r in rn if r["id"] == i)
             or TIME_LIT in next(r["reply"] for r in rn if r["id"] == i))
            for i in rdiff)
        same = (not vdiff and len(vn) == len(vb) == 200)
        out.append(f"R3-bench-{tag}: verdicts identical={same} n={len(vn)} "
                   f"reply_diffs={rdiff if rdiff else []} "
                   f"all_screen_text={screen_only}")
        ok &= same and screen_only
        if tag == "fable_edit_200":
            ok &= rdiff and len(rdiff) == 37
    return ok


def check_r4(out: list[str]) -> bool:
    ok = True
    secs = {}
    secs["q1"] = json.loads((ARTB / "fable_q1_summary148b.json").read_text(
        encoding="utf-8"))["seconds"]
    secs["q2"] = json.loads((ARTB / "fable_q2_report148b.json").read_text(
        encoding="utf-8"))["seconds"]
    secs["bench"] = json.loads((ARTB / "fable_bench148b_summary.json").read_text(
        encoding="utf-8"))["seconds"]
    for arm in ("marks123-148b", "marks123-134base"):
        s = json.loads((ARTB / arm / "fable_marks123_summary.json").read_text(
            encoding="utf-8"))
        secs[arm] = s["total_seconds"]
    for k, v in secs.items():
        out.append(f"R4-{k}: {v} s (< 1500: {v < 1500})")
        ok &= v < 1500
    import fable_loop148b_agent as L148b
    sig = inspect.signature(L148b.Loop148bDaemon.__init__)
    idle = sig.parameters["idle_seconds"].default
    out.append(f"R4-idle_seconds default: {idle}")
    ok &= idle == 30.0
    return ok


def main() -> int:
    out: list[str] = []
    r1 = check_r1(out)
    r2 = check_r2(out)
    r3 = check_r3(out)
    r4 = check_r4(out)
    print("\n".join(out))
    print(f"R1={r1} R2={r2} R3={r3} R4={r4}")
    (ARTB / "fable_verify148b_report.json").write_text(json.dumps(
        {"lines": out, "R1": r1, "R2": r2, "R3": r3, "R4": r4,
         "pass": bool(r1 and r2 and r3 and r4)}, indent=1), encoding="utf-8")
    return 0 if (r1 and r2 and r3 and r4) else 1


if __name__ == "__main__":
    sys.exit(main())
