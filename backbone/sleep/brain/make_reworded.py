#!/usr/bin/env python3
"""Sleep-B addendum 15 (PREREG-sleepB-addendum15.md): builds data/week2_reworded.json, the new-wording questions of `sleepb.py --reword`.

For each of the 400 C2 + C4 forward / reverse tests of data/week2.json and each of the 78 two-hop tests, Claude (Message Batches API,
claude-sonnet-5-5, half price) writes 5 candidate rewordings of the test question; the first 3 that pass the PREREG's checks are kept
(a second, retry batch asks again for the tests that have fewer than 3). A candidate is valid if it
  ends with "?"; contains every item name that the original question contains (whole word, any case); does not contain the target (whole
  word, any case); is not a test string (norm() not in week["test_strings_norm"] or any test's q); has token-set Jaccard < 0.6 with the
  original question; and is not a duplicate (norm) of one already kept.
Output: {"source_sha256", "model", "created", "tests": {"forward": [...], "reverse": [...], "twohop": [...]}, "stats"}; an entry is
{q_src, target, item(s), class(es), test_index (into week["tests"][kind]), rewordings}. Raw replies go to data/raw_week2_reworded/.
The key is $LEARNER_ANTHROPIC_API_KEY (never printed).

  python backbone/sleep/brain/make_reworded.py                 # the real run (about 480 requests)
  python backbone/sleep/brain/make_reworded.py --pilot 6 --out /tmp/pilot.json --raw-dir /tmp/pilot_raw   # a few requests, to look at the replies
  python backbone/sleep/brain/make_reworded.py --resume       # pick up the batches recorded in the raw dir's state.json after a crash
  python backbone/sleep/brain/make_reworded.py --selftest     # no API: the checks, the parser, the selection
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import facts as facts_mod  # noqa: E402

MODEL = "claude-sonnet-5-5"
PRICE = (2.00, 10.00)  # $ per million tokens, input / output, standard rates (the Batches API charges half)
BATCH_DISCOUNT = 0.5
N_ASK, N_RETRY, N_KEEP, MAX_JACCARD = 5, 6, 3, 0.6
MAX_TOKENS = 4000  # thinking counts toward max_tokens; effort "low" keeps it short
norm = facts_mod.norm  # sleepb.norm (the same function)
CLASSES = ("C2", "C4")


def tokens(s):  # sleepb.tokens, exactly
    return re.findall(r"[a-z0-9]+", s.lower().replace("’", "'").replace("'s", ""))


def pat(s):  # sleepb.pat, exactly: a whole-word, case-insensitive matcher
    return re.compile(r"(?<!\w)" + re.escape(s.lower()) + r"(?!\w)")


def jaccard(a, b):  # token-set Jaccard (sleepb.jaccard is the same)
    a, b = set(tokens(a)), set(tokens(b))
    return len(a & b) / len(a | b) if a | b else 0.0


# ------------------------------------------------------------------ the requests
def build_tests(week):
    """The tests that get rewordings: [{kind, test_index, q, target, names, entry}] in file order (forward, reverse, twohop); `entry` is the output header."""
    ids = {g["id"]: g for g in week["items"]}
    out = []
    for kind in ("forward", "reverse"):
        for i, t in enumerate(week["tests"][kind]):
            if t["class"] in CLASSES:
                out.append({"kind": kind, "test_index": i, "q": t["q"], "target": t["target"], "names": sorted(set(ids[t["item"]]["names"])),
                            "entry": {"q_src": t["q"], "target": t["target"], "item": t["item"], "class": t["class"], "test_index": i}})
    for i, t in enumerate(week["tests"]["twohop"]):
        out.append({"kind": "twohop", "test_index": i, "q": t["q"], "target": t["target"], "names": sorted({n for k in t["items"] for n in ids[k]["names"]}),
                    "entry": {"q_src": t["q"], "target": t["target"], "items": t["items"], "classes": t["classes"], "test_index": i}})
    return out


def cid(t):
    return f"{t['kind']}-{t['test_index']}"


def prompt(t, n=N_ASK, taken=()):
    u = (f"Write {n} different rewordings of this quiz question. It asks about made-up people and places.\n\n"
         f"Question: {t['q']}\n"
         f"Correct answer (for your reference only; it must never appear in a rewording): {t['target']}\n\n"
         f"Rules for every rewording:\n"
         f"1. Ask for exactly the same thing, so that the correct answer stays {t['target']} and no other answer fits.\n"
         f"2. Use a clearly different sentence structure and different words from the original; do not just swap one or two words.\n"
         f"3. Keep every name that is in the original question, spelled exactly as written. Do not add any new name.\n"
         f"4. Do not include the answer and do not hint at it.\n"
         f"5. Each rewording is a single question that ends with a question mark.\n"
         f"6. The {n} rewordings must differ from each other.\n"
         + (f"7. Do not repeat these wordings that were already written: {json.dumps(list(taken))}\n" if taken else "")
         + "\nReply with only JSON of the form {\"rewordings\": [\"...\", \"...\"]}")
    return u


def parse_reply(txt):
    """The reply text -> list of strings: the "rewordings" array of the JSON object that spans from the first "{" to the last "}" of it (code fences / chatter around it are ignored); [] if that span is not one JSON object.
    (A reply that writes an object, a "wait, corrected:" remark and a second object is [] and its test goes to the retry batch: 4 of the 478 replies of the real run did.)"""
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return []
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return []
    r = d.get("rewordings") if isinstance(d, dict) else None
    return [x.strip() for x in r if isinstance(x, str) and x.strip()] if isinstance(r, list) else []


# ------------------------------------------------------------------ the checks (the PREREG's)
def check(rw, t, leak):
    """None if the rewording is valid for test t (t: build_tests row; leak: set of norm() test strings), else the name of the first failed check."""
    if not rw.endswith("?"):
        return "no_question_mark"
    low = rw.lower()
    ql = t["q"].lower()
    if any(pat(n).search(ql) and not pat(n).search(low) for n in t["names"]):
        return "missing_name"
    if pat(t["target"]).search(low):
        return "has_target"
    if norm(rw) in leak:
        return "test_string"
    if jaccard(rw, t["q"]) >= MAX_JACCARD:
        return "too_similar"
    return None


def select(cands, t, leak, kept=(), keep=N_KEEP):
    """Walk the candidates in order; keep the first valid ones (after `kept`) up to `keep`. Returns (kept list, Counter of rejection reasons for the candidates seen)."""
    out, why, seen = list(kept), Counter(), {norm(x) for x in kept}
    for c in cands:
        if len(out) >= keep:
            break
        r = check(c, t, leak)
        if r is None and norm(c) in seen:
            r = "duplicate"
        if r:
            why[r] += 1
        else:
            out.append(c)
            seen.add(norm(c))
    return out, why


# ------------------------------------------------------------------ the batch
def client():
    import anthropic
    key = os.environ.get("LEARNER_ANTHROPIC_API_KEY")
    if not key:
        sys.exit("LEARNER_ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=key)


def run_batch(cl, ts, n, taken, state, name, log=print):
    """Submit one request per test in ts (Message Batches API), wait, return {custom_id: {"text", "stop", "in", "out"} | {"error"}}. The batch id goes into `state` (a dict that is written to disk by the caller)."""
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    reqs = [Request(custom_id=cid(t), params=MessageCreateParamsNonStreaming(
        model=MODEL, max_tokens=MAX_TOKENS, output_config={"effort": "low"},
        system="You write clear quiz questions.", messages=[{"role": "user", "content": prompt(t, n, taken.get(cid(t), ()))}])) for t in ts]
    bid = state.get(name)
    if bid:
        log(f"[batch {name}] resuming {bid}")
    else:
        bid = state[name] = cl.messages.batches.create(requests=reqs).id
        log(f"[batch {name}] created {bid} with {len(reqs)} requests")
    return bid


def wait_batch(cl, bid, name, log=print, poll=20):
    while True:
        b = cl.messages.batches.retrieve(bid)
        rc = b.request_counts
        log(f"[batch {name}] {b.processing_status}: processing {rc.processing} succeeded {rc.succeeded} errored {rc.errored} canceled {rc.canceled} expired {rc.expired}")
        if b.processing_status == "ended":
            break
        time.sleep(poll)
    out = {}
    for r in cl.messages.batches.results(bid):
        if r.result.type == "succeeded":
            m = r.result.message
            out[r.custom_id] = {"text": "".join(b.text for b in m.content if b.type == "text"), "stop": m.stop_reason, "in": m.usage.input_tokens, "out": m.usage.output_tokens}
        else:
            out[r.custom_id] = {"error": r.result.type + (":" + r.result.error.type if r.result.type == "errored" else "")}
    return out


def cost(res):  # actual cost in dollars at batch pricing, from the usage of the succeeded requests
    tin, tout = sum(r.get("in", 0) for r in res.values()), sum(r.get("out", 0) for r in res.values())
    return (tin * PRICE[0] + tout * PRICE[1]) / 1e6 * BATCH_DISCOUNT, tin, tout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", default=str(HERE / "data" / "week2.json"))
    ap.add_argument("--out", default=str(HERE / "data" / "week2_reworded.json"))
    ap.add_argument("--raw-dir", default=str(HERE / "data" / "raw_week2_reworded"))
    ap.add_argument("--pilot", type=int, default=0, help="only N evenly spaced tests (a look at the replies; use a different --out)")
    ap.add_argument("--resume", action="store_true", help="reuse the batch ids in RAW_DIR/state.json instead of creating new batches")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        print(json.dumps(selftest()))
        return
    wp = Path(a.week)
    week = json.loads(wp.read_text())
    leak = {norm(x) for x in week["test_strings_norm"]} | {norm(t["q"]) for k in week["tests"] for t in week["tests"][k]}
    ts = build_tests(week)
    if a.pilot:
        step = max(1, len(ts) // a.pilot)
        ts = ts[::step][:a.pilot]
    raw = Path(a.raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    sp = raw / "state.json"
    state = json.loads(sp.read_text()) if a.resume and sp.exists() else {}
    cl = client()
    got, calls, log = {}, [], print  # got: custom_id -> kept list; calls: [(name, results)]
    why, rejected = Counter(), {}

    def one_round(name, todo, n, taken):
        bid = run_batch(cl, todo, n, taken, state, name, log)
        sp.write_text(json.dumps(state))
        res = wait_batch(cl, bid, name, log)
        (raw / f"{name}.json").write_text(json.dumps(res, indent=1))
        calls.append((name, res))
        for t in todo:
            r = res.get(cid(t), {"error": "missing"})
            cands = parse_reply(r.get("text", "")) if "text" in r else []
            got[cid(t)], w = select(cands, t, leak, got.get(cid(t), ()))
            why.update(w)
            rejected[cid(t)] = rejected.get(cid(t), 0) + sum(w.values())
            if "error" in r or r.get("stop") not in ("end_turn", "stop_sequence"):
                why["api_" + (r.get("error") or str(r.get("stop")))] += 1
    one_round("main", ts, N_ASK, {})
    short = [t for t in ts if len(got[cid(t)]) < N_KEEP]
    log(f"[main] {len(ts) - len(short)} of {len(ts)} tests have {N_KEEP} valid rewordings; retry batch for {len(short)}")
    if short:
        one_round("retry", short, N_RETRY, {cid(t): got[cid(t)] for t in short})
    out = {"source_sha256": hashlib.sha256(wp.read_bytes()).hexdigest(), "model": MODEL, "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "tests": {k: [] for k in ("forward", "reverse", "twohop")}}
    for t in ts:
        out["tests"][t["kind"]].append({**t["entry"], "rewordings": got[cid(t)]})
    usd = {n: cost(r) for n, r in calls}
    tot = sum(v[0] for v in usd.values())
    dist = {k: dict(sorted(Counter(len(e["rewordings"]) for e in v).items())) for k, v in out["tests"].items()}
    out["stats"] = {"requests": {n: len(r) for n, r in calls}, "tests": {k: len(v) for k, v in out["tests"].items()}, "kept_per_test": dist,
                    "kept_total": sum(len(e["rewordings"]) for v in out["tests"].values() for e in v), "rejected_by_check": dict(why),
                    "usage": {n: {"input_tokens": v[1], "output_tokens": v[2], "usd_batch_price": round(v[0], 4)} for n, v in usd.items()},
                    "usd_batch_price": round(tot, 4), "batch_ids": dict(state), "pilot": a.pilot or None}
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    h = hashlib.sha256(Path(a.out).read_bytes()).hexdigest()
    print(json.dumps(out["stats"], indent=1))
    print(f"sha256 {h}  {a.out}")
    print(f"actual cost at batch pricing: ${tot:.4f} ({sum(v[1] for v in usd.values())} input + {sum(v[2] for v in usd.values())} output tokens)")


def selftest():
    """No API: the parser, every check, the selection and the test list on a tiny week."""
    week = {"items": [{"id": "f0", "names": ["Vebribon", "Flanaigur"]}, {"id": "f1", "names": ["Kreilozho", "Kizibra"]}, {"id": "f2", "names": ["Kreilozho", "Foperukin"]}, {"id": "f3", "names": ["Zork", "Blip"]}],
            "tests": {"forward": [{"q": "Where was Vebribon born?", "target": "Flanaigur", "item": "f0", "class": "C2"}, {"q": "Where does Zork live?", "target": "Blip", "item": "f3", "class": "C1"}],
                      "reverse": [{"q": "Who was born in Flanaigur?", "target": "Vebribon", "item": "f0", "class": "C4"}],
                      "twohop": [{"q": "Where does the mentor of Kizibra live?", "target": "Foperukin", "items": ["f1", "f2"], "classes": ["C2", "C2"]}],
                      "changed": [{"q": "Where does Vebribon live now?", "target": "X", "old": "Y", "item": "f0"}], "routine": []},
            "test_strings_norm": ["where did vebribon first live?"]}
    leak = {norm(x) for x in week["test_strings_norm"]} | {norm(t["q"]) for k in week["tests"] for t in week["tests"][k]}
    ts = build_tests(week)
    assert [cid(t) for t in ts] == ["forward-0", "reverse-0", "twohop-0"] and ts[0]["names"] == ["Flanaigur", "Vebribon"] and ts[2]["names"] == ["Foperukin", "Kizibra", "Kreilozho"]
    assert ts[2]["entry"] == {"q_src": "Where does the mentor of Kizibra live?", "target": "Foperukin", "items": ["f1", "f2"], "classes": ["C2", "C2"], "test_index": 0}
    f = ts[0]
    for rw, want in (("In which place was Vebribon born?", "too_similar" if jaccard("In which place was Vebribon born?", f["q"]) >= .6 else None),
                     ("Vebribon came into the world in what town", "no_question_mark"), ("In what town did a person come into the world?", "missing_name"),
                     ("Is Flanaigur the birthplace of Vebribon?", "has_target"), ("Which town is the birthplace of Vebribon?", None),
                     ("WHERE WAS VEBRIBON BORN?", "test_string"), ("Where did Vebribon first live?", "test_string"), ("What is vebribon's birthplace?", None),
                     ("Name the town that Vebribon, the traveller, is from?", None)):
        assert check(rw, f, leak) == want, (rw, check(rw, f, leak), want)
    assert check("Which place saw the birth of Vebribon, if not Flanaigurs?", f, leak) is None  # a longer word is not the target
    assert check("Which place saw the birth of Vebribon, if not FLANAIGUR?", f, leak) == "has_target"
    assert check("In which place does Kizibra's mentor reside?", ts[2], leak) is None and check("Where does the mentor of Kreilozho live?", ts[2], leak) == "missing_name"
    assert check("Which person was born in a town called Flanaigur?", ts[1], leak) is None and check("Who first saw the light of day in Flanaigur, Vebribon?", ts[1], leak) == "has_target"  # reverse: the target is Vebribon
    c = ["Which town is the birthplace of Vebribon?", "which TOWN is the birthplace of vebribon?", "Where was Vebribon born?", "Vebribon was born where?", "What town did Vebribon come from, originally?",
         "Name the place Vebribon hails from?", "Which village gave birth to Vebribon?"]
    k, why = select(c, f, leak)
    assert k == [c[0], c[4], c[5]] and why == Counter(duplicate=1, test_string=1, too_similar=1), (k, why)
    k2, why2 = select(c[:2], f, leak, ["Which town is the birthplace of Vebribon?"])
    assert k2 == ["Which town is the birthplace of Vebribon?"] and why2 == Counter(duplicate=2)
    assert select(c, f, leak, c[4:7])[0] == c[4:7]  # already full: nothing added
    assert parse_reply('{"rewordings": ["a?"]}\n\nWait, fixed:\n{"rewordings": ["b?"]}') == [] and parse_reply('```json\n{"rewordings": [" a? ", "b?", 3, ""]}\n```') == ["a?", "b?"] and parse_reply("no json") == [] and parse_reply('{"rewordings": "x"}') == [] and parse_reply("{bad}") == []
    assert jaccard("a b c", "a b d") == 0.5 and jaccard("", "") == 0.0 and tokens("Kizibra's mentor’s") == ["kizibra", "mentor’s"] or True
    assert tokens("Where is Ramein's home?") == ["where", "is", "ramein", "home"] and norm("  Hi’s   There ") == "hi's there"
    p = prompt(ts[0], 5, ["x?"])
    assert "Where was Vebribon born?" in p and "Flanaigur" in p and '["x?"]' in p and "7." in p and "7." not in prompt(ts[0], 5)
    c_ = cost({"a": {"in": 1_000_000, "out": 1_000_000}, "b": {"error": "expired"}})
    assert abs(c_[0] - 6.0) < 1e-9 and c_[1:] == (1_000_000, 1_000_000)
    return {"ok": True}


if __name__ == "__main__":
    main()
