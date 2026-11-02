"""Step 1: Sonnet (Message Batches) writes the persona: 60 slot facts + 40 background facts + extras. Code fixes ids, splits and (for
duration/mode slots) the values, then validates, hashes and freezes data/persona.json (+ persona.sha256).
  python -m sleep2.askonce.persona            # real Batches run
"""
import random
import re
import sys

from .batches import parse_json, req, run_batch
from .config import DATA, HAIKU, KINDS, SEED_WORLD, SILENT_N, SONNET, SPLIT_NEW, jdump, sha256_file
from .world import slot_id, validate_persona

EMAIL = re.compile(r"^[a-z0-9._+-]+@[a-z0-9-]+\.[a-z.]+$")
BASE = ("We are building a fictional test world for an email/calendar/files assistant. The user is 'Ben', a high-school-aged student with "
        "a busy life (family, school, a part-time job, clubs, friends). Everything is invented. Reply with ONE JSON value only, no prose.\n\n")
KIND_SPEC = {
    "contact": ("{n} ambiguous contact references. Each is a short phrase Ben uses for a person, where SEVERAL contacts could match: a first name "
                "shared by several contacts (Sam, Alex), a nickname (Mom -> but Ben has two relatives who could be 'Mom'?), a role ('my coach'). "
                "Give the TRUE person plus 3 plausible distractors (other people the phrase could match).\n"
                'Schema: [{{"ref": "Sam", "key_token": "sam", "value": {{"value": "sam.r@example.com", "label": "Sam Rivera (classmate)"}}, '
                '"distractors": [{{"value": "...", "label": "..."}}, ...3 items]}}]  value = unique lowercase email address.'),
    "meeting": ("{n} ambiguous event references ('the standup', 'the review', 'my dentist appointment') where SEVERAL calendar events could match. "
                "TRUE event plus 3 distractor events.\n"
                'Schema: [{{"ref": "the standup", "key_token": "standup", "value": {{"value": "ev-0412", "label": "Team standup, Mon 9:30"}}, '
                '"distractors": [...3 items]}}]  value = unique event id of the form ev-NNNN.'),
    "file": ("{n} ambiguous file references ('the essay', 'the budget', 'my resume') where SEVERAL files could match. TRUE file plus 3 distractor files.\n"
             'Schema: [{{"ref": "the essay", "key_token": "essay", "value": {{"value": "/docs/essay_final_v3.docx", "label": "History essay, final"}}, '
             '"distractors": [...3 items]}}]  value = unique absolute path starting with /.'),
    "duration": ("{n} kinds of meeting for which Ben has a DEFAULT LENGTH (e.g. 'quick syncs', '1:1s with my manager', 'club planning calls'). Only the reference phrase is needed.\n"
                 'Schema: [{{"ref": "quick syncs", "key_token": "syncs"}}]'),
    "mode": ("{n} recipient groups for which Ben has a rule about whether emails are SENT right away or only saved as DRAFTS (e.g. 'emails to my landlord', "
             "'messages to my boss'). Only the reference phrase is needed.\n"
             'Schema: [{{"ref": "emails to my landlord", "key_token": "landlord"}}]'),
}
KIND_RULES = ("Rules: every ref and every key_token must be unique within the whole list and across plausible neighbours; key_token is ONE distinctive lowercase "
              "word that occurs in ref. Never reuse a value. Make refs varied and natural (not all names).")
FACTS_SPEC = ('Write (a) 40 neutral background facts about Ben (dentist name, locker number, favourite band, pet, bus route, shoe size... all different and '
              'concrete, each answer a short distinctive string) and (b) "extras": 12 people (emails + label), 8 files (paths + label), 6 calendar events (ids ev-NNNN + label) '
              'that are NOT in any other list (different names, different folders).\n'
              'Schema: {"facts": [{"statement": "Ben\'s dentist is Dr. Okafor.", "recall_q": "Who is Ben\'s dentist?", "recall_a": "Okafor"}, ...40], '
              '"extras": {"emails": [{"value": "x@example.org", "label": "..."}], "paths": [{"value": "/x/y.pdf", "label": "..."}], "events": [{"value": "ev-0900", "label": "..."}]}}\n'
              "recall_a must be a short string that appears verbatim inside statement.")


def build_requests():
    out = []
    for kind, n in KINDS.items():
        out.append(req(f"persona-{kind}", SONNET, BASE + KIND_SPEC[kind].format(n=n) + "\n" + KIND_RULES, 16000))
    out.append(req("persona-facts", SONNET, BASE + FACTS_SPEC, 16000))
    return out


def _cand(c):
    return {"value": str(c["value"]).strip(), "label": str(c["label"]).strip()}


GENERIC = {"my", "the", "emails", "email", "messages", "notes", "to", "from", "with", "at", "for", "and", "meeting", "meetings", "calls", "call", "a", "an", "of", "in", "on"}


def _clash(a, b):
    return a == b or a.startswith(b) or b.startswith(a)


def _words(s):
    return [w for w in re.findall(r"[a-z0-9]+", s["ref"].lower()) if w not in GENERIC and len(w) >= 4]


def _free(w, slots, skip):
    return not any(_clash(w, t["key_token"]) for t in slots if t is not skip and t.get("_kt_set"))


def repair_key_tokens(slots):
    """key_token must be unique across all 60 slots (prefix clashes count). Greedy; on a dead end an earlier slot holding the clash
    moves to another word of its own ref (names, i.e. longer words, preferred)."""
    for s in slots:
        words = sorted(set(_words(s)), key=lambda w: -len(w))
        order = ([s["key_token"]] if s["key_token"] in s["ref"].lower() and len(s["key_token"]) >= 3 else []) + words
        done = False
        for w in order:
            if _free(w, slots, s):
                s["key_token"], s["_kt_set"], done = w, True, True
                break
        if not done:
            for t in slots:
                if t is s or not t.get("_kt_set"):
                    continue
                if any(_clash(w, t["key_token"]) for w in words):
                    for w2 in sorted(set(_words(t)), key=lambda w: -len(w)):
                        if w2 != t["key_token"] and _free(w2, slots, t) and not _clash(w2, s["key_token"]):
                            clash_w = next(w for w in words if _clash(w, t["key_token"]))
                            t["key_token"] = w2
                            s["key_token"], s["_kt_set"], done = clash_w, True, True
                            break
                if done:
                    break
    for s in slots:
        s.pop("_kt_set", None)


def _avoid(s):
    """Words of a held-out slot that days 1-5 text must not contain (see requests_gen.avoid_words)."""
    return {s["key_token"].lower()} | {w for w in re.findall(r"[a-z0-9]+", s["ref"].lower()) if len(w) >= 7 and w not in {"emails", "messages", "meeting", "meetings", "appointments", "sessions"}}


def _fix_split_clashes(by):
    """A training slot whose own reference contains a held-out slot's word (e.g. 'my dentist appointment' vs held-out 'my dentist') could never be
    talked about in days 1-5 without leaking the held-out slot. Swap such a held-out slot with a clash-free training slot of the same kind."""
    def clashes(n, train):
        a = _avoid(n)
        return [t for t in train if a & set(re.findall(r"[a-z0-9]+", t["ref"].lower()))]
    for kind, lst in by.items():
        for n in [x for x in lst if x["split"] == "new"]:
            train = [x for x in by_all(by) if x["split"] == "train"]
            if not clashes(n, train):
                continue
            for m in [x for x in lst if x["split"] == "train"]:
                n_ok = not clashes(m, [x for x in by_all(by) if x["split"] == "train" and x is not m] + [n])
                if n_ok:
                    n["split"], m["split"] = "train", "new"
                    break


def by_all(by):
    return [x for lst in by.values() for x in lst]


def assemble(texts, seed=SEED_WORLD):
    """texts: {custom_id: reply text}. Returns (persona dict, list of problems)."""
    rng = random.Random(seed)
    slots, problems = [], []
    for kind, n in KINDS.items():
        try:
            arr = parse_json(texts[f"persona-{kind}"])
        except Exception as e:
            problems.append(f"{kind}: {e}")
            continue
        arr = arr[:n]
        if len(arr) != n:
            problems.append(f"{kind}: need {n}, got {len(arr)}")
        for i, e in enumerate(arr):
            s = {"slot_id": slot_id(kind, i + 1), "kind": kind, "ref": str(e["ref"]).strip(), "key_token": str(e["key_token"]).strip().lower()}
            if s["key_token"] not in s["ref"].lower():
                problems.append(f"{s['slot_id']}: key_token not in ref")
            if kind in ("contact", "meeting", "file"):
                true = _cand(e["value"])
                cands = [true] + [_cand(x) for x in e["distractors"]][:3]
                fmt = {"contact": EMAIL, "meeting": re.compile(r"^ev-[a-z0-9]+$"), "file": re.compile(r"^/[\w./ -]+$")}[kind]
                for c in cands:
                    if not fmt.match(c["value"]):
                        problems.append(f"{s['slot_id']}: bad value format {c['value']}")
                s["value"] = true["value"]
                s["candidates"] = cands
                s["recall_q"] = {"contact": f"What is the email address of {s['ref']}?", "meeting": f"What is the event id of {s['ref']}?",
                                 "file": f"What is the file path of {s['ref']}?"}[kind]
                s["recall_a"] = true["value"]
            elif kind == "duration":
                opts = [15, 20, 25, 30, 45, 50, 60, 90]
                rng.shuffle(opts)
                s["value"] = str(opts[0])
                s["candidates"] = [{"value": str(o), "label": f"{o} minutes"} for o in opts[:3]]
                s["recall_q"] = f"How many minutes is Ben's default meeting length for {s['ref']}?"
                s["recall_a"] = s["value"]
            else:
                tool = rng.choice(["send_email", "draft_email"])
                s["value"] = tool
                s["candidates"] = [{"value": "send_email", "label": "send right away"}, {"value": "draft_email", "label": "save as draft"}]
                s["recall_q"] = f"For {s['ref']}, does Ben want the email sent right away or saved as a draft? Answer 'send' or 'draft'."
                s["recall_a"] = "send" if tool == "send_email" else "draft"
            slots.append(s)
    repair_key_tokens(slots)
    # splits: stratified held-out "new" slots, then silent slots among the rest
    by = {}
    for s in slots:
        by.setdefault(s["kind"], []).append(s)
    for kind, lst in by.items():
        idx = list(range(len(lst)))
        rng.shuffle(idx)
        for j, i in enumerate(idx):
            lst[i]["split"] = "new" if j < SPLIT_NEW[kind] else "train"
    _fix_split_clashes(by)
    silent_plan = {"mode": 2, "duration": 1, "file": 1, "contact": 1}
    assert sum(silent_plan.values()) == SILENT_N
    for kind, k in silent_plan.items():
        pool = [s for s in by.get(kind, []) if s["split"] == "train"]
        rng.shuffle(pool)
        for s in pool[:k]:
            s["split"] = "silent"
    try:
        f = parse_json(texts["persona-facts"])
        facts = [{"fact_id": f"fact_{i + 1:02d}", "statement": x["statement"].strip(), "recall_q": x["recall_q"].strip(), "recall_a": str(x["recall_a"]).strip()}
                 for i, x in enumerate(f["facts"][:40])]
        extras = {k: [_cand(c) for c in f["extras"][k]] for k in ("emails", "paths", "events")}
        for x in facts:
            if x["recall_a"].lower() not in x["statement"].lower():
                problems.append(f"{x['fact_id']}: recall_a not in statement")
    except Exception as e:
        problems.append(f"facts: {e}")
        facts, extras = [], {"emails": [], "paths": [], "events": []}
    d = {"slots": slots, "facts": facts, "extras": extras}
    problems += validate_persona(d)
    all_vals = [c["value"].lower() for s in slots if s["kind"] in ("contact", "meeting", "file") for c in s["candidates"]]
    for k in extras:
        for c in extras[k]:
            if c["value"].lower() in all_vals:
                problems.append("extra overlaps a slot value: " + c["value"])
    return d, problems


def main():
    if "--from-raw" in sys.argv:  # re-assemble the saved Sonnet replies (no API call)
        from .config import jload
        texts = jload(DATA / "persona_raw.json")
    else:
        texts, _ = run_batch(build_requests(), "persona")
        jdump(DATA / "persona_raw.json", texts)
    d, problems = assemble(texts)
    if problems:  # one repair round for the failed kinds only, if any
        print("problems:", problems[:10], file=sys.stderr)
        raise SystemExit("persona invalid; inspect and re-run (replies kept in data/persona_raw.json)")
    jdump(DATA / "persona.json", d)
    (DATA / "persona.sha256").write_text(sha256_file(DATA / "persona.json") + "  persona.json\n")
    print("persona frozen", sha256_file(DATA / "persona.json")[:16])


if __name__ == "__main__":
    main()
