"""Race-mini dream tape (PROTOCOL-mini, /mnt/project-files/sleep-race/mini/): for every item value of a week file, K paraphrases and K
question/answer pairs written by Claude (Message Batches API) from the item's sentence only, in the style of sleepb's nrem_prompt; the same
leak filter as sleepb (a line containing a test string, or a long line contained in one, is dropped). Both race sides train on this tape.

  python backbone/sleep/brain/race/race_tape.py --week backbone/sleep/brain/data/week2.json --out /mnt/project-files/sleep-race/mini/tape_week2.json
  python backbone/sleep/brain/race/race_tape.py --week ... --out x.json --dry   # prints the requests, no API call
Key: LEARNER_ANTHROPIC_API_KEY.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent.parent)]
from facts import norm  # noqa: E402

MODEL = "claude-haiku-5-5"
K = 8
SYS = "You are a careful assistant that studies facts."


def prompt(text, names, k=K):
    a, b = names[0], names[-1]
    return (f"Fact: {text}\n\nFocus on the fact linking \"{a}\" and \"{b}\". Write {k} paraphrases of the fact (short standalone sentences, different wording, "
            f"naming both) and {k} question-answer pairs about it. Cover both directions: some questions should ask about one name, some about the other. "
            f"Each answer must be a single name from the fact. Reply with only JSON of the form {{\"paraphrases\": [\"...\"], \"qa\": [{{\"q\": \"...\", \"a\": \"...\"}}]}}")


def values(week):  # (key, item id, which, sentence, names) for every item value: changing facts have an old and a new value
    for it in week["items"]:
        if it["kind"] == "changing":
            yield f"{it['id']}:old", it["id"], "old", it["old_text"], [it["a"], it["old_b"]]
            yield f"{it['id']}:new", it["id"], "new", it["text"], [it["a"], it["b"]]
        else:
            yield f"{it['id']}:new", it["id"], "new", it["text"], [it["a"], it["b"]]


def parse(txt):
    s, e = txt.find("{"), txt.rfind("}")
    d = json.loads(txt[s:e + 1])
    return [p for p in d.get("paraphrases", []) if isinstance(p, str)], [(x["q"], x["a"]) for x in d.get("qa", []) if isinstance(x, dict) and "q" in x and "a" in x]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--fill", action="store_true", help="re-ask only the values of an existing --out tape whose paraphrases and Q&A are both empty (parse failures), max_tokens 2000; merge them in")
    a = ap.parse_args()
    week = json.loads(Path(a.week).read_text())
    leak = {norm(x) for x in week.get("test_strings_norm", [])} | {norm(t["q"]) for k in week["tests"] for t in week["tests"][k]}
    leaky = lambda t: any(l in norm(t) or (len(norm(t)) >= 10 and norm(t) in l) for l in leak)  # noqa: E731  (sleepb Brain.leaky)
    vals = list(values(week))
    old = json.loads(Path(a.out).read_text()) if a.fill else None
    if old:
        vals = [v for v in vals if not (old["tape"][v[0]]["paraphrases"] or old["tape"][v[0]]["qa"])]
        print("filling", len(vals), flush=True)
    reqs = [{"custom_id": key.replace(":", "__"), "params": {"model": a.model, "max_tokens": 2000 if a.fill else 1000, "system": SYS,
             "messages": [{"role": "user", "content": prompt(text, names)}]}} for key, _, _, text, names in vals]
    if a.dry:
        print(len(reqs), json.dumps(reqs[0], indent=1))
        return
    import anthropic
    cl = anthropic.Anthropic(api_key=os.environ["LEARNER_ANTHROPIC_API_KEY"])
    b = cl.messages.batches.create(requests=reqs)
    print("batch", b.id, flush=True)
    while b.processing_status != "ended":
        time.sleep(20)
        b = cl.messages.batches.retrieve(b.id)
        print(b.processing_status, b.request_counts, flush=True)
    got, tin, tout = {}, 0, 0
    for r in cl.messages.batches.results(b.id):
        if r.result.type == "succeeded":
            m = r.result.message
            tin, tout = tin + m.usage.input_tokens, tout + m.usage.output_tokens
            got[r.custom_id.replace("__", ":")] = "".join(c.text for c in m.content if c.type == "text")
    tape, st = {}, {"values": len(vals), "ok": 0, "parse_fail": 0, "missing": 0, "leak_dropped": 0}
    for key, iid, which, text, names in vals:
        if key not in got:
            st["missing"] += 1
            paras, qa = [], []
        else:
            try:
                paras, qa = parse(got[key])
                st["ok"] += 1
            except Exception:
                st["parse_fail"] += 1
                st.setdefault("fail_samples", []).append(got[key][-200:])
                paras, qa = [], []
        n0 = len(paras) + len(qa)
        paras = [p for p in paras if not leaky(p)]
        qa = [(q, x) for q, x in qa if not leaky(q)]
        st["leak_dropped"] += n0 - len(paras) - len(qa)
        tape[key] = {"item": iid, "which": which, "text": text, "paraphrases": paras, "qa": qa}
    if old:  # merge: the new values replace the empty ones; stats and cost add up
        for k, v in tape.items():
            old["tape"][k] = v
        tape = old["tape"]
        st = {"fill": st, "first": old["stats"]}
        tin, tout = tin + old["tokens"]["in"], tout + old["tokens"]["out"]
        b_id = old["batch_id"] + "+" + b.id
    else:
        b_id = b.id
    cost = tin / 1e6 * 1.0 * 0.5 + tout / 1e6 * 5.0 * 0.5  # Haiku list price per MTok, x0.5 for Batches (estimate)
    out = {"week": a.week, "week_sha256": hashlib.sha256(Path(a.week).read_bytes()).hexdigest(), "model": a.model, "batch_id": b_id, "stats": st,
           "tokens": {"in": tin, "out": tout}, "cost_usd_est": round(cost, 4), "tape": tape}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "tape"}), "sha256", hashlib.sha256(Path(a.out).read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
