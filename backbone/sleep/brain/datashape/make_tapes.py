"""Data-shape round 1 (PREREG-datashape-r1.md): two new race-mini tapes, each ONE change to the shared tape_week2.json. Training code is race_mini.py, unchanged.

  W (wide):   every value keeps its tape cards and gets up to 8 MORE paraphrases and 8 MORE Q&A, written by Claude Haiku (Batches) to differ in
              structure from the ones it already has. New lines that are near copies (token Jaccard >= 0.8) of a kept line are dropped; same leak filter as
              race_tape.py. Same steps a night, so each card is seen about half as often ("more distinct cards at equal steps", cf. sleep addendum 15 D8).
  L (linked): for every other Week-2 two-hop test pair (39 of 78, "carded"), the first fact's tape value gets 1 linked sentence that names both facts and the
              middle person, and 2 two-hop Q&A in wordings that are not the test's (template-built, no model). The other 39 pairs get nothing ("uncarded").
              Same number of linked cards per carded pair.

  python backbone/sleep/brain/datashape/make_tapes.py --arm L --out backbone/sleep/brain/datashape/tapes/tape_week2_L.json
  python backbone/sleep/brain/datashape/make_tapes.py --arm W --out .../tape_week2_W.json [--dry]
Key (W only): LEARNER_ANTHROPIC_API_KEY.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
B = HERE.parent
sys.path[:0] = [str(B), str(B.parent)]
from facts import norm  # noqa: E402

BASE_TAPE = B / "race" / "tapes" / "tape_week2.json"
WEEK = B / "data" / "week2.json"
MODEL = "claude-haiku-5-5"
KMORE = 8
DUP = 0.8
SYS = "You are a careful assistant that studies facts."

# (statement, [two-hop questions]) per chain kind; {x} = the test's given entity, {m} = the middle person, {t} = the answer (week.make_tests slots).
# None of these contains, or is contained in, a facts.HOP test question (checked by the leak filter below).
LINK = {
    "mentor_lives": ("{x}'s mentor, {m}, lives in {t}.", ["What place is home to the person who mentors {x}?", "Name the place where {x}'s mentor has their home."]),
    "sibling_works": ("{x}'s sibling, {m}, works at {t}.", ["Name the workplace of {x}'s brother or sister.", "At what company is the sibling of {x} employed?"]),
    "owner_born": ("{m}, who owns the boat called {x}, was born in {t}.", ["What is the birthplace of the person who owns the boat {x}?",
                                                                           "Name the town where the boat {x}'s owner was born."]),
}
SLOTS = {"mentor_lives": ("b", "a"), "sibling_works": ("a", "b"), "owner_born": ("b", "a")}  # (x slot of fact 1, middle slot of fact 1) = week.CHAINS


def toks(s):
    return set(re.findall(r"[a-z0-9']+", s.lower()))


def jac(a, b):
    a, b = toks(a), toks(b)
    return len(a & b) / max(len(a | b), 1)


def leak_fn(week):
    leak = {norm(x) for x in week.get("test_strings_norm", [])} | {norm(t["q"]) for k in week["tests"] for t in week["tests"][k]}
    return lambda t: any(l in norm(t) or (len(norm(t)) >= 10 and norm(t) in l) for l in leak)  # race_tape.py / sleepb Brain.leaky


def carded(week):
    """[(test index, carded?)] over week['tests']['twohop']: every other test within each chain kind is carded (index 0, 2, ... of that kind)."""
    seen, out = {}, []
    for j, t in enumerate(week["tests"]["twohop"]):
        k = seen.get(t["hop"], 0)
        seen[t["hop"]] = k + 1
        out.append((j, k % 2 == 0))
    return out


def make_L(week, tape):
    items = {it["id"]: it for it in week["items"]}
    leaky = leak_fn(week)
    tape = copy.deepcopy(tape)
    log = []
    for j, c in carded(week):
        if not c:
            continue
        t = week["tests"]["twohop"][j]
        f, g = items[t["items"][0]], items[t["items"][1]]
        xs, ms = SLOTS[t["hop"]]
        x, m, tgt = f[xs], f[ms], g["b"]
        assert tgt == t["target"] and g["a"] == m, (t, f, g)
        st, qs = LINK[t["hop"]]
        st, qs = st.format(x=x, m=m, t=tgt), [q.format(x=x) for q in qs]
        bad = [s for s in [st, *qs] if leaky(s)]
        assert not bad, bad
        v = tape[f"{f['id']}:new"]
        v["paraphrases"].append(st)
        v["qa"].extend((q, tgt) for q in qs)
        log.append({"test": j, "pair": t["items"], "hop": t["hop"], "statement": st, "qa": [[q, tgt] for q in qs]})
    return tape, {"carded": len(log), "uncarded": len(week["tests"]["twohop"]) - len(log), "links": log}


def wprompt(v, names):
    a, b = names
    have = "\n".join(f"- {p}" for p in [v["text"], *v["paraphrases"]]) + "\n" + "\n".join(f"- Q: {q} A: {x}" for q, x in v["qa"])
    return (f"Fact: {v['text']}\n\nThese study cards already exist:\n{have}\n\nFocus on the fact linking \"{a}\" and \"{b}\". Write {KMORE} NEW paraphrases of the "
            f"fact and {KMORE} NEW question-answer pairs about it that are clearly different from the existing cards: use other sentence structures, other "
            f"verbs, other question openings, longer and shorter forms, and a short everyday context (\"Sam mentioned that ...\"). Keep the fact exactly the "
            f"same and name both names in every paraphrase. Cover both directions: some questions ask about one name, some about the other. Each answer must "
            f"be a single name from the fact. Reply with only JSON of the form {{\"paraphrases\": [\"...\"], \"qa\": [{{\"q\": \"...\", \"a\": \"...\"}}]}}")


def names_of(week, key):
    iid, which = key.split(":")
    it = next(i for i in week["items"] if i["id"] == iid)
    return [it["a"], it["old_b"] if which == "old" else it["b"]]


def parse(txt):
    s, e = txt.find("{"), txt.rfind("}")
    d = json.loads(txt[s:e + 1])
    return [p for p in d.get("paraphrases", []) if isinstance(p, str)], [(x["q"], x["a"]) for x in d.get("qa", []) if isinstance(x, dict) and "q" in x and "a" in x]


def merge_W(v, paras, qa, ans_ok, leaky):
    """Add new lines to value v: drop leaks, answers that are not one of the value's names, and near copies (Jaccard >= DUP) of any kept line."""
    st = {"leak": 0, "dup": 0, "bad_answer": 0, "added_p": 0, "added_qa": 0}
    kept = [v["text"], *v["paraphrases"], *(q for q, _ in v["qa"])]
    for p in paras[:KMORE]:
        if leaky(p):
            st["leak"] += 1
        elif any(jac(p, k) >= DUP for k in kept):
            st["dup"] += 1
        else:
            v["paraphrases"].append(p); kept.append(p); st["added_p"] += 1
    for q, x in qa[:KMORE]:
        if leaky(q):
            st["leak"] += 1
        elif not ans_ok(x):
            st["bad_answer"] += 1
        elif any(jac(q, k) >= DUP for k in kept):
            st["dup"] += 1
        else:
            v["qa"].append((q, x)); kept.append(q); st["added_qa"] += 1
    return st


def make_W(week, tape, dry=False, model=MODEL):
    leaky = leak_fn(week)
    tape = copy.deepcopy(tape)
    keys = sorted(tape)
    reqs = [{"custom_id": k.replace(":", "__"), "params": {"model": model, "max_tokens": 2000, "system": SYS,
             "messages": [{"role": "user", "content": wprompt(tape[k], names_of(week, k))}]}} for k in keys]
    if dry:
        print(len(reqs), json.dumps(reqs[0], indent=1))
        sys.exit(0)
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
    tot = {"values": len(keys), "parse_fail": 0, "missing": 0, "leak": 0, "dup": 0, "bad_answer": 0, "added_p": 0, "added_qa": 0}
    for k in keys:
        if k not in got:
            tot["missing"] += 1
            continue
        try:
            paras, qa = parse(got[k])
        except Exception:
            tot["parse_fail"] += 1
            continue
        nm = {norm(n) for n in names_of(week, k)}
        st = merge_W(tape[k], paras, qa, lambda x: norm(x) in nm, leaky)
        for s, n in st.items():
            tot[s] += n
    cost = tin / 1e6 * 1.0 * 0.5 + tout / 1e6 * 5.0 * 0.5  # Haiku list price per MTok x0.5 for Batches (estimate, as race_tape.py)
    return tape, {"batch_id": b.id, "model": model, "tokens": {"in": tin, "out": tout}, "cost_usd_est": round(cost, 4), **tot}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["W", "L"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    week = json.loads(WEEK.read_text())
    base = json.loads(BASE_TAPE.read_text())
    tape, st = make_L(week, base["tape"]) if a.arm == "L" else make_W(week, base["tape"], a.dry)
    out = {k: v for k, v in base.items() if k != "tape"}
    out.update({"base_tape": str(BASE_TAPE.relative_to(B.parent.parent.parent)), "base_tape_sha256": hashlib.sha256(BASE_TAPE.read_bytes()).hexdigest(),
                "datashape_arm": a.arm, "datashape_stats": st, "tape": tape})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in st.items() if k != "links"}), "sha256", hashlib.sha256(Path(a.out).read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
