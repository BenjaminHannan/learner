"""Build habit1_mini.json for PREREG-habit1-mini.md (run in the cloud; the Mac needs only this JSON and habit.py).

  python backbone/sleep/brain/habit_mini_build.py [--out backbone/sleep/brain/habit1_mini.json]

Choices where the prereg is ambiguous (most literal reading each time):
  * "first 40 Week-2 C2/C4 forward tests (by test order)": week2.json tests["forward"] in file order, class C2 or C4, kept when an ELIGIBLE
    addendum-12 item (eligible=true; result_q36_q4.json) links the test's two names in either order. The first such item in file order is the
    fact sentence ("subj rel obj.", Item.fact). All 40 are taken, no sampling.
  * "up to 4 diary user turns that contain both names": the FIRST 4 in diary order (Diary.containing), not the latest per day.
  * "Dream once per item with af_prompt": af_prompt takes ONE message, so an item gets one af_prompt per diary turn (<= 4), each dreamed once
    (greedy, K = 4). The Mac needs no repo imports, so each prompt is stored as {system, user} (the chat-template text is rendered there).
  * The 20 routines are stored with their stage-1 Rall prompt (habit_probe.build, so it equals stage 1 / addendum 1), their pair, their first
    4 diary turns and af prompts, so a spotter yes needs nothing else. Routine eval questions are tests["routine"].
  * "ARC-Easy items 1-60" = the first 60 entries of the list; the prompt is sleep1.score_arc's (question, A. ..., "Answer with the letter only.").
  * "30 of generic_prompts()" = the first 30 (20 hand questions + 10 topic prompts).
Pure Python except that habit_probe.build imports sleepb (so torch must be importable here, not on the Mac)."""
import argparse
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
ARC = "/mnt/project-files/mechanism/askonce-job1-out/v2/job1/nightdata_job1/arc_easy_500.json"
N_FACTS, N_ARC, N_REPLAY, MAX_TURNS = 40, 60, 30, 4


def render_pair(system, user):
    return {"system": system, "user": user}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", default=str(HERE / "data/week2.json"))
    ap.add_argument("--items", default=str(HERE / "results_a12/result_q36_q4.json"))
    ap.add_argument("--arc", default=ARC)
    ap.add_argument("--out", default=str(HERE / "habit1_mini.json"))
    a = ap.parse_args()
    import habit_probe as HP
    import sleepb as S
    import sleep1
    week = json.loads(Path(a.week).read_text())
    dia = S.Diary(week)
    gt = {tuple(sorted((S.norm(g["a"]), S.norm(g["b"])))): g for g in week["items"]}
    elig = {}  # unordered norm pair -> first eligible addendum-12 item
    for it in json.loads(Path(a.items).read_text())["items"]:
        if it["eligible"]:
            elig.setdefault(tuple(sorted((S.norm(it["subj"]), S.norm(it["obj"])))), it)
    stub = SimpleNamespace(render=render_pair)

    def dreams(x, y):
        return [{"day": dia.turns[i]["day"], "text": dia.turns[i]["text"], "prompt": S.af_prompt(stub, dia.turns[i]["day"], dia.turns[i]["text"])}
                for i in dia.containing(x, y)[:MAX_TURNS]]

    facts = []
    for t in week["tests"]["forward"]:
        g = next(x for x in week["items"] if x["id"] == t["item"])
        k = tuple(sorted((S.norm(g["a"]), S.norm(g["b"]))))
        if t["class"] in ("C2", "C4") and k in elig:
            it = elig[k]
            facts.append({"id": t["item"], "a": g["a"], "b": g["b"], "cls": t["class"], "sentence": f"{it['subj']} {it['rel']} {it['obj']}.",
                          "q": t["q"], "target": t["target"], "turns": dreams(g["a"], g["b"])})
        if len(facts) == N_FACTS:
            break
    with tempfile.TemporaryDirectory() as td:  # stage 1's own builder: the Rall prompts are byte-identical to addendum 1's
        HP.build(SimpleNamespace(week=a.week, items=a.items, out=f"{td}/p.jsonl"))
        rall = [json.loads(x) for x in (Path(td) / "p.jsonl").read_text().splitlines() if x.strip()]
    rall = [r for r in rall if r["kind"] == "Rall"]
    rq = {x["item"]: x for x in week["tests"]["routine"]}
    routines = []
    for r in rall:
        g = gt[tuple(sorted((S.norm(r["pair"][0]), S.norm(r["pair"][1]))))]
        t = rq[g["id"]]
        routines.append({"id": g["id"], "pair": r["pair"], "n_days": r["n_days"], "activity": g["activity"], "system": r["system"], "user": r["user"],
                         "q": t["q"], "target": t["target"], "turns": dreams(*r["pair"])})
    arc = []
    for r in json.loads(Path(a.arc.rstrip("/")).read_text())[:N_ARC]:
        u = r["q"] + "\n" + "\n".join(f"{l}. {c}" for l, c in zip(r["labels"], r["texts"])) + "\nAnswer with the letter only."
        arc.append({"id": r["id"], "user": u, "gold": r["a"]})
    out = {"sys": sleep1.SYS, "facts": facts, "routines": routines, "arc": arc, "replay": sleep1.generic_prompts()[:N_REPLAY],
           "test_strings_norm": week["test_strings_norm"], "k": S.K}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print({"facts": len(facts), "routines": len(routines), "arc": len(arc), "replay": len(out["replay"]),
           "fact_turns": sum(len(f["turns"]) for f in facts), "routine_turns": sum(len(r["turns"]) for r in routines)})


if __name__ == "__main__":
    main()
