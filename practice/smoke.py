"""CPU end-to-end smoke with a tiny random Llama: 5 practice puzzles, 1 day/night round, both arms. The tiny model writes gibberish, so a scripted
stand-in policy replaces generation (python call first, then an answer that is right for about half of the tries) to make wins, failures and pairs exist.
  python -m practice.smoke [--out DIR]"""
import argparse
import json
import re
import tempfile
import random
from pathlib import Path

from . import harness, job


def scripted_factory(puzzles):
    by = {p["prompt"]: p for p in puzzles}
    rng = random.Random(5)

    def gen(model, tok, prompts, max_new, temperature, seed, bs=None, log=None, first_words=None):
        outs = []
        for pr in prompts:
            m = re.search(r"<\|ifm\|im_start\|>user\n(.*?)\n\n\(The final answer", pr, re.S)
            p = by.get(m.group(1)) if m else None
            turn = pr.count("<|ifm|im_start|>assistant")  # includes the open generation turn
            if p is None:
                outs.append("ANSWER: 0")
            elif turn <= 1:
                outs.append("I will check with code.\n<tool>python</tool>\n<input>\nprint(6*7)\n</input>")
            elif turn == 2:
                outs.append("<tool>search</tool>\n<input>breadth first search</input>")
            else:
                good = rng.random() < 0.5
                outs.append(f"<tool>answer</tool>\n<input>\n{p['answer'] if good else '0'}\n</input>")
        return outs
    return gen


def run_smoke(out=None):
    out = Path(out or tempfile.mkdtemp(prefix="p1smoke_"))
    summary = {}
    for lane_i, arm in enumerate(("P", "C")):
        a = job.main.__globals__["argparse"].Namespace(arm=arm, lane=lane_i, out=str(out), model="", seed=1 + lane_i, practice_n=None, deadline_s=3600, night_est_s=1,
                                                       arc_n=5, bs=4, nights=1, tries=2, steps=3, n_sft=6, epochs=2, n_pairs=3, pilot=False, smoke=True,
                                                       backend="hf", eval_nights="1,3", sib_tries=1)
        lane = job.Lane(a)
        gp = [p for p in lane.pool if p["kind"] != "arc"]
        lane.pool = gp[:5]
        lane.test = [p for p in lane.test if len(p["prompt"]) < 1500][:3]
        lane.sib = [p for p in lane.sib if p["kind"] != "arc"][:3]
        harness.generate = scripted_factory(lane.pool + lane.test + lane.sib)
        lane.H.max_new = 24
        lane.run()
        lane.H.pool.shutdown()
        res = {k: json.loads(f.read_text()) for k in ("A0", f"{arm}1", "night1", "day1") for f in [out / arm / "results" / f"{k}.json"]}
        n = res["night1"]
        summary[arm] = {"sft_examples": n["sft_examples"], "pairs": n["pairs"], "n_items": n["n_items"], "opt_steps": n["train"]["opt_steps"],
                        "test_A0": res["A0"]["test"]["acc"], "test_after": res[f"{arm}1"]["test"]["acc"], "day_acc": res["day1"]["acc"]}
        lane.model = None
    assert summary["P"]["n_items"] == summary["C"]["n_items"] and summary["P"]["opt_steps"] == summary["C"]["opt_steps"], summary
    print(json.dumps(summary, indent=1))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    run_smoke(ap.parse_args().out)
