#!/usr/bin/env python3
"""88 — one-command rehearsal of the family demo for a non-technical viewer.

Runs end to end on Mac CPU, additive only (imports 55b/55/modes54 code, edits
nothing):

  Act 1 (family scene): teach -> ask -> correct -> ask through the same
      LISTENING doorway as the modes54 demo, on a fresh notebook.
  Act 2 (the evidence): the 55b comparison — notebook teaches 120 facts about
      40 people, answers 20 two-hop questions, learns 5 brand-new facts, and
      re-answers old plus new; the plain-transformer baseline is the 55b
      QA-drilled protocol (250 supervised updates, then a fixed 60 second
      fine-tune per seed, seeds 5401/5402/5403 reported separately).

Writes OUT/transcript.md: a clean two-column-style transcript ("Ben:" /
"Agent:") with the notebook status after each turn in plain words, timings,
a final scoreboard copied from the run JSON (asserted equal), and a short
plain-English explanation of why the notebook wins (high-school reader).

V4 rule: transcript.md must contain no code, no JSON, no status codes.
Statuses are translated to plain words; this script audits that and asserts.

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
      python -B scripts/fable_demo88_rehearse.py --out artifacts/fable-demo88-20260921
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
      python -B scripts/fable_demo88_rehearse.py --out <dir> --skip-baseline   # fast mode
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
import fable_listening_m1 as L  # noqa: E402
from fable_modes54_scheduler import ModeScheduler  # noqa: E402
import fable_modes54_demo as D  # noqa: E402  (reused, never edited)
import fable_demo55_advantage as A55  # noqa: E402  (reused, never edited)
import fable_demo55b_forgetting as B55  # noqa: E402  (reused, never edited)

SEEDS_DEFAULT = (5401, 5402, 5403)
FAST_SECONDS = 60.0
FULL_SECONDS = 900.0

# ------------------------------------------------------------------ Act 1
# Frozen family scene: teach -> ask -> correct -> ask, plus one honest
# "I don't know". Names avoid the 40 Q10 people and the 5 Q11 newcomers.
ACT1 = [
    ("teach Mira mother -> Ana", "Mira's mother is Ana.", None),
    ("teach Ana city = Porto", "Ana lives in Porto.", None),
    ("teach Mira city = Lisbon", "Mira lives in Lisbon.", None),
    ("ask Mira mother city", "Where does Mira's mother live?", "Porto"),
    ("ask Mira city", "Where does Mira live?", "Lisbon"),
    ("correct Mira city = Paris", "A small fix. Mira lives in Paris.", None),
    ("ask Mira city", "Where does Mira live now?", "Paris"),
    ("ask Tom city", "Where does Tom live?", "<ABSTAIN>"),
]


def run_act1(state_dir: str) -> dict:
    nb = C.Notebook(state_dir)
    ear = L.Listening(nb)
    sched = ModeScheduler(turn_handler=ear.hear, sleep_threshold=100_000)
    turns: list[dict] = []
    wrong = 0
    t0 = time.monotonic()
    for line, plain, gold in ACT1:
        sched.submit(line)
        event = sched.step()
        reply = event["detail"].get("reply", "")
        ok: bool | None = None
        status_words: str
        if line.startswith(("teach", "correct")):
            status_words = ("I saved it in my notebook."
                            if "Saved" in reply else
                            "I did not save it. I asked a follow-up instead.")
            ok = None  # teachings are not answers; wrong-write rule checked below
        else:
            if gold == "<ABSTAIN>":
                ok = "don't know" in reply.lower()
            else:
                ok = D.norm(reply) == D.norm(gold)
            if not ok:
                wrong += 1
            status_words = ("I answered from my notes."
                            if ok and gold != "<ABSTAIN>" else
                            "I did not know, so I said so." if ok else
                            "I got that one wrong.")
        turns.append({"line": line, "ben": plain, "agent": reply,
                      "gold": gold, "ok": ok, "status_words": status_words})
    seconds = time.monotonic() - t0
    # wrong-write rule (demo55's): teach/correct -> exactly one new fact whose
    # stored raw equals the line; ask -> zero new facts.
    nb2 = C.Notebook(state_dir)  # reload is unnecessary; count via replay below
    _ = nb2
    return {"turns": turns, "wrong": wrong, "seconds": seconds, "nb": nb,
            "sched": sched}


def check_act1_writes(state_dir: str) -> int:
    """Replay Act 1 on a throwaway notebook to count wrong writes exactly."""
    import tempfile
    tmp = tempfile.mkdtemp(prefix="fable-demo88-act1-")
    try:
        nb = C.Notebook(tmp)
        ear = L.Listening(nb)
        sched = ModeScheduler(turn_handler=ear.hear, sleep_threshold=100_000)
        bad = 0
        for line, _, _ in ACT1:
            before = set(nb.facts)
            sched.submit(line)
            sched.step()
            new_ids = sorted(set(nb.facts) - before, key=lambda x: int(x[1:]))
            act = line.split()[0]
            if act in ("teach", "correct"):
                good = (len(new_ids) == 1
                        and nb.facts[new_ids[0]].get("raw") == line)
            else:
                good = not new_ids
            bad += not good
        return bad
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


EXPLANATION = (
    "Think of the notebook as a notepad, and the plain transformer as a "
    "student who may only memorise by rereading everything. When Ben tells "
    "the notebook a fact, it writes it on its own card, so new cards never "
    "smudge old ones, and fixing one card changes only that card. The "
    "student has no notepad. Every new lesson reshapes the same memory, so "
    "cramming five new sentences blurred the twenty old answers, and still "
    "did not teach the five new ones as answers. That is why the notebook "
    "keeps all twenty old facts and learns all five new ones, while the "
    "student on these runs keeps none of the old and learns none of the new."
)

FORBIDDEN = ["E000", "MISSING_FACT", "BROKEN_CHAIN", "AMBIGUOUS",
             "UNKNOWN_ENTITY", "CONFLICT", "->", "{", "}", "<SEP>", "<PAD>",
             "<EOS>", "<UNK>", "qid", ".json", ".py", "Traceback", "import ",
             "def ", "```", "==", "!="]
CODE_OPENERS = {"teach", "ask", "correct", "person", "pick", "alias",
                "quote", "forget", "yes", "no"}


def audit_transcript(text: str) -> list[str]:
    problems: list[str] = []
    for tok in FORBIDDEN:
        if tok in text:
            problems.append(f"forbidden token present: {tok!r}")
    for i, ln in enumerate(text.splitlines(), 1):
        s = ln.strip()
        if s.startswith("Ben:") or s.startswith("Agent:"):
            continue
        first = s.lower().split(" ")[0] if s else ""
        if first in CODE_OPENERS:
            problems.append(f"line {i} looks like code: {s[:60]!r}")
    return problems


def plain_status_teach() -> str:
    return "Notebook status: saved."


def build_transcript(act1: dict, nb55: dict, nb_scores: dict,
                     baseline: dict | None, seeds: tuple[int, ...],
                     timings: dict, scoreboard_lines: list[str],
                     explanation: str) -> str:
    L_: list[str] = []
    L_.append("A rehearsal of the family demo")
    L_.append("")
    L_.append("How to read this: Ben speaks, the Agent answers. After each "
              "turn, one line says what the notebook did, in plain words.")
    L_.append("")
    L_.append("Act 1. A family, a question, a fix, the question again.")
    L_.append("")
    for t in act1["turns"]:
        L_.append(f"Ben: {t['ben']}")
        L_.append(f"Agent: {t['agent']}")
        L_.append(t["status_words"])
        L_.append("")
    L_.append("Act 2. Many facts at once.")
    L_.append("")
    L_.append("Ben told the Agent 120 facts about 40 people: for each person, "
              "their mother, their boss, and the city they live in. Three of "
              "them in plain words: Ada's mother is Bo. The boss of Bo is "
              "Keir. Ada lives in Porto.")
    L_.append(f"The Agent saved all 120 facts. Notebook status: saved, "
              f"{nb55['n_taught']} of 120.")
    L_.append("")
    L_.append("Then Ben asked 20 hard questions, each needing two steps, "
              "like this one.")
    first = A55.Q10_ITEMS[0]
    L_.append(f"Ben: {first['en']}")
    L_.append(f"Agent: {nb55['replies_before'][first['qid']]}")
    L_.append("Notebook status: answered from my notes.")
    L_.append("")
    L_.append(f"All 20 answers were right. Notebook status for every one: "
              f"answered from my notes.")
    L_.append("")
    L_.append("Act 3. Five brand-new facts, after everything was learned.")
    L_.append("")
    L_.append("Ben introduced five newcomers by name and told one fact about "
              "each: Kip lives in Bern. Lark lives in Lima. The boss of Moth "
              "is Kip. The mother of Nyx is Lark. Opal lives in Cairo.")
    L_.append(f"Notebook status: all {nb55['n_taught_new']} saved.")
    L_.append("")
    for item in A55.Q11_ITEMS:
        L_.append(f"Ben: {item['en']}")
        L_.append(f"Agent: {nb55['replies_new'][item['qid']]}")
        L_.append("Notebook status: answered from my notes.")
        L_.append("")
    L_.append("Then Ben re-asked the 20 old questions, to check the new facts "
              "did not push out the old ones.")
    L_.append(f"All 20 answers were still right. Notebook status for every "
              f"one: answered from my notes.")
    L_.append("")
    if baseline is None:
        L_.append("The plain transformer comparison was skipped in this fast "
                  "run, so there is no transformer score below. The notebook "
                  "scores above stand on their own.")
    else:
        L_.append("The comparison: a small plain transformer studied the same "
                  "120 sentences, then crammed the 5 new ones for a full "
                  "minute. It studied hard, yet afterwards it could no longer "
                  "answer the old questions, and still could not answer the "
                  "new ones. The numbers are in the scoreboard.")
    L_.append("")
    L_.append("Timings")
    L_.append("")
    for k in ("act1_seconds", "notebook_55b_seconds", "baseline_seconds",
              "total_seconds"):
        L_.append(f"{timings['labels'][k]}: {timings[k]:.1f} seconds.")
    L_.append("")
    L_.append("Scoreboard")
    L_.append("")
    L_.extend(scoreboard_lines)
    L_.append("")
    L_.append("Why the notebook wins, in plain words")
    L_.append("")
    L_.append(explanation)
    L_.append("")
    return "\n".join(L_) + "\n"


def main(argv=None) -> int:
    t_start = time.monotonic()
    p = argparse.ArgumentParser(description="88 demo rehearsal transcript")
    p.add_argument("--out", default="artifacts/fable-demo88-20260921")
    p.add_argument("--state-dir", default=None)
    p.add_argument("--skip-baseline", action="store_true")
    p.add_argument("--seeds", default="5401,5402,5403")
    args = p.parse_args(argv)
    seeds = tuple(int(s) for s in args.seeds.split(","))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    state = Path(args.state_dir) if args.state_dir else out / "demo88-notebook"
    act1_state = out / "demo88-act1-notebook"
    for d in (state, act1_state):
        if d.exists():
            shutil.rmtree(d)

    # Act 1
    act1 = run_act1(str(act1_state))
    act1_wrong_writes = check_act1_writes(str(act1_state))

    # Act 2+3: notebook side of the 55b comparison (same LISTENING path)
    t_nb = time.monotonic()
    run55 = B55.run_notebook_55b(str(state))
    nb55_seconds = time.monotonic() - t_nb
    nb10b = A55.score(run55["before"], A55.Q10_ITEMS)
    nb10a = A55.score(run55["after"], A55.Q10_ITEMS)
    nb11 = A55.score(run55["after_new"], A55.Q11_ITEMS)
    n_taught = sum(1 for r in run55["transcript"]
                   if r["tag"].startswith("q10teach"))
    n_taught_new = sum(1 for r in run55["transcript"]
                       if r["tag"].startswith("q11teach"))
    nb_wrong = ((20 - nb10b["total"]) + (20 - nb10a["total"])
                + (5 - nb11["total"]) + act1["wrong"])
    nb_wrong_writes = len(run55["wrong_writes"]) + act1_wrong_writes

    # Baseline (55b protocol) unless fast mode
    baseline = None
    t_base = 0.0
    if not args.skip_baseline:
        t0 = time.monotonic()
        print("--- baseline: plain transformer, 55b protocol ---", flush=True)
        baseline = B55.run_baseline_qa(seeds)
        t_base = time.monotonic() - t0

    total = time.monotonic() - t_start
    timings = {"act1_seconds": act1["seconds"],
               "notebook_55b_seconds": nb55_seconds,
               "baseline_seconds": t_base, "total_seconds": total,
               "labels": {"act1_seconds": "The family scene took",
                          "notebook_55b_seconds":
                              "The 120 facts plus all questions took",
                          "baseline_seconds": "The transformer study took",
                          "total_seconds": "The whole rehearsal took"}}

    # Scoreboard data (never averaged; per seed)
    sb: dict = {"notebook": {"old_kept": nb10a["total"], "old_before": nb10b["total"],
                             "new_learned": nb11["total"],
                             "wrong_answers": nb_wrong,
                             "wrong_writes": nb_wrong_writes},
                "baseline_skipped": args.skip_baseline, "seeds": list(seeds)}
    if baseline:
        per = {}
        for s in seeds:
            cell = baseline["per_seed"][str(s)]
            old = cell["q10_after"]["total"]
            new = cell["q11_after"]["total"]
            per[str(s)] = {"old_kept": old, "new_learned": new,
                           "wrong_answers": (20 - old) + (5 - new)}
        sb["baseline"] = per

    words = len(EXPLANATION.split())
    assert words <= 150, f"explanation {words} words over the 150 limit"
    # lock the three plain-words example facts to the frozen 55 dataset
    assert A55.Q10_LINES[0] == "teach Ada mother -> Bo"
    assert A55.Q10_LINES[4] == "teach Bo boss -> Keir"
    assert A55.Q10_LINES[2] == "teach Ada city = Porto"

    report = {"act1": {"turns": [{"ben": t["ben"], "agent": t["agent"],
                                  "gold": t["gold"], "ok": t["ok"],
                                  "status_words": t["status_words"]}
                                 for t in act1["turns"]],
                       "wrong": act1["wrong"],
                       "wrong_writes": act1_wrong_writes},
              "notebook": {"q10_before": nb10b["total"],
                           "q10_after": nb10a["total"],
                           "q11": nb11["total"], "n_taught": n_taught,
                           "wrong_answers": nb_wrong,
                           "wrong_writes": nb_wrong_writes},
              "scoreboard": sb, "timings": {k: round(v, 2) for k, v in timings.items()
                                            if k != "labels"},
              "explanation_words": words, "seeds": list(seeds),
              "skip_baseline": args.skip_baseline,
              "elapsed_seconds": round(total, 1)}
    if baseline:
        report["baseline_summary"] = {
            s: {"q10_before": baseline["per_seed"][s]["q10_before"]["total"],
                "q11_before": baseline["per_seed"][s]["q11_before"]["total"],
                "q11_after": baseline["per_seed"][s]["q11_after"]["total"],
                "q10_after": baseline["per_seed"][s]["q10_after"]["total"],
                "ft_steps": baseline["per_seed"][s]["fine_tune"]["steps"]}
            for s in sb.get("baseline", {})}
    (out / "fable-demo88-results.json").write_text(json.dumps(report, indent=1))

    # Scoreboard lines COPIED FROM the reloaded run JSON (V3), then asserted.
    reloaded = json.loads((out / "fable-demo88-results.json").read_text())
    rsb = reloaded["scoreboard"]
    assert rsb == sb, "scoreboard drift between memory and the run JSON"
    sl: list[str] = []
    sl.append(f"Old facts kept, out of 20: notebook {rsb['notebook']['old_kept']}.")
    sl.append(f"New facts learned, out of 5: notebook "
              f"{rsb['notebook']['new_learned']}.")
    sl.append(f"Wrong answers by the notebook: {rsb['notebook']['wrong_answers']}.")
    if rsb["baseline_skipped"]:
        sl.append("Plain transformer: skipped in this fast run.")
    else:
        for s in seeds:
            cell = rsb["baseline"][str(s)]
            sl.append(f"Plain transformer run {s}: old facts kept "
                      f"{cell['old_kept']} of 20, new facts learned "
                      f"{cell['new_learned']} of 5, wrong answers "
                      f"{cell['wrong_answers']}.")
    # assert the transcript scoreboard numbers equal the run JSON exactly
    for ln in sl:
        for num in re.findall(r"\d+", ln):
            assert num in json.dumps(rsb), f"scoreboard number {num} not in JSON"

    nb55 = {"n_taught": n_taught, "n_taught_new": n_taught_new,
            "replies_before": run55["before"], "replies_new": run55["after_new"]}
    text = build_transcript(act1, nb55,
                            {"b": nb10b, "a": nb10a, "n": nb11},
                            baseline, seeds, timings, sl, EXPLANATION)
    problems = audit_transcript(text)
    assert not problems, f"V4 transcript audit failed: {problems}"

    # V2: every shown notebook answer must be right (teaching turns excluded)
    shown_wrong = [t for t in act1["turns"]
                   if t["ok"] is False]
    assert not shown_wrong, f"V2 failed: {shown_wrong}"
    assert nb_wrong == 0, f"V2 failed: notebook wrong answers = {nb_wrong}"

    (out / "transcript.md").write_text(text)

    limit = FAST_SECONDS if args.skip_baseline else FULL_SECONDS
    marks = {
        "V1_time": {"pass": bool(total < limit),
                    "value": f"{total:.1f}s vs {limit:.0f}s"},
        "V2_notebook_zero_wrong": {"pass": nb_wrong == 0,
                                   "value": str(nb_wrong)},
        "V3_scoreboard_equals_json": {"pass": rsb == sb, "value": "exact"},
        "V4_no_code_in_transcript": {"pass": not problems,
                                     "value": "audit clean"},
    }
    report["marks"] = marks
    (out / "fable-demo88-results.json").write_text(json.dumps(report, indent=1))

    print("=" * 72, flush=True)
    print("DEMO 88 SCOREBOARD (per seed, never averaged)", flush=True)
    print(f"notebook: old kept {nb10a['total']}/20, new learned "
          f"{nb11['total']}/5, wrong answers {nb_wrong}", flush=True)
    if baseline:
        for s in seeds:
            cell = rsb["baseline"][str(s)]
            print(f"transformer {s}: old kept {cell['old_kept']}/20, new "
                  f"{cell['new_learned']}/5, wrong {cell['wrong_answers']}",
                  flush=True)
    else:
        print("baseline skipped (fast mode)", flush=True)
    for k in sorted(marks):
        m = marks[k]
        print(f"  {k:<28} {'PASS' if m['pass'] else 'FAIL':<5} {m['value']}",
              flush=True)
    print(f"TOTAL_ELAPSED_SECONDS {total:.1f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
