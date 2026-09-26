#!/usr/bin/env python3
"""lis-320 pilot, step 3 of 3: code checks every GLM-written turn against its seed; failing turns are dropped, never
repaired. Kept turns become training rows in the lis-319 format (id, prompt, target, src, family, turn, prev_reply,
frame, history), prompt from claude_lis319_common.build_prompt_hist, src "glm320", family = intent.

Checks (claude_lis300_compiler.whole_word_span for every span):
  - every MUST string is a whole-word span of the user turn. A span typed in another case ("mira" for "Mira") is
    accepted when every copy in the turn has that one casing; the frame then carries the typed form (the frame spec
    says names and values are copied as typed). Two casings in one turn -> dropped.
  - first person where a "me" fact needs it (compiler ME_WORDS); intro turns name the role (role word or a variant);
  - MUST NOT strings absent from the turn (and from reply_before where the seed says so);
  - no stray name: no other person name or proper value of the dialog in the turn; reply_before may only use names the
    user already typed;
  - backref: the owner is not in the turn or reply_before, is in the history the reader sees (last HIST_TURNS turns),
    the reference word is there (pronoun of the person's gender, or the role word), a pronoun has exactly one person of
    that gender named in that visible text, and a role word has a visible earlier turn naming the person with the role;
  - asserting intents (teach, jobhome, correct, backref): no hedge cue, and no fact the lis-319f FORMER rule reads as past;
  - former: a past cue and no present cue (lis-319f PRESENT);
  - look-alikes and ask: their cue class, and the gold has no ASSERT/CORRECT fact; smalltalk: no first-person state.
Facts are put in the order their values appear in the turn (frame spec: in order of the turn).

python3 claude_lis320_check.py --seeds seeds.jsonl --raw raw.jsonl --out rows.jsonl [--drops drops.jsonl]
python3 claude_lis320_check.py --selftest
Prints counts only.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from claude_lis320_seed import REPO  # noqa: E402

sys.path.insert(0, str(REPO / "scripts"))
import claude_lis300_compiler as CMP  # noqa: E402
from claude_lis300_common import frame_text, canon_frame  # noqa: E402
from claude_lis319_common import build_prompt_hist, HIST_TURNS  # noqa: E402
from claude_lis319f_data import is_former, PRESENT, CURRENT_RELS  # noqa: E402

MAX_TURN, MAX_REPLY = 500, 250
WRITE = {"ASSERT", "CORRECT"}
ASSERTING = {"teach", "jobhome", "correct", "backref"}
LOOK = {"question", "plan", "doubt", "someone_else", "hypothetical", "negation_only", "confirm", "ambiguous_pronoun"}

# check-only cue classes (never trained on)
PAST = re.compile(r"\b(used to|was|were|formerly|before|previously|last|anymore|no longer|once|quit|left)\b", re.I)
# "not anymore / over now / im not one now": a negated present, not a present cue (removed before PRESENT is checked)
NEG_NOW = re.compile(r"\b(not|isnt|isn't|aint|dont|don't|doesnt|doesn't|no longer)\b(\s+\w+){0,3}?\s+(now|anymore)\b|"
                     r"\b(over|done|finished|behind me)\s+now\b", re.I)
PLAN_LEAK = re.compile(r"\bfirst person\b|\bowner:|\brelation:|\bintent\b|\bMUST\b")
# second-hand source for a stated-as-true fact ("my neighbour mentioned it"); the user's own "i said/mentioned" is not
REPORTED = re.compile(r"\b(apparently|according to|supposedly|reckons|rumou?r|i heard|heard that)\b|"
                      r"(?<!\bi )(?<!\bive )(?<!\bi've )(?<!\bhave )(?<!\bnever )\bmentioned (it|that)\b", re.I)
HEDGE = re.compile(r"\b(maybe|might|not sure|what if|suppose|imagine|apparently|supposedly|probably|i heard|"
                   r"i think)\b", re.I)
CUES = {
    "ask": re.compile(r"\?|\b(remind me|again|what|whats|what's|who|whos|who's|where|wheres|where's|how old|when)\b",
                      re.I),
    "question": re.compile(r"\?"),
    "plan": re.compile(r"\b(going to|gonna|will|next|plan|plans|planning|wants? to|hoping|hopes? to|about to|soon|"
                       r"thinking of|thinking about)\b|'ll\b", re.I),
    "doubt": re.compile(r"\b(think|thinks|maybe|not (even |really |totally |100% |a hundred percent )?sure|might|probably|"
                        r"perhaps|guess|could be|idk|dunno|unsure|can'?t remember|don'?t remember|not certain|no idea)\b",
                        re.I),
    "someone_else": re.compile(r"\b(says|said|told|tells|heard|apparently|according to|claims|claimed|reckons|mentioned|"
                               r"rumou?r|supposedly)\b", re.I),
    "hypothetical": re.compile(r"\b(if|suppose|supposing|imagine|pretend|hypothetically|let'?s say)\b", re.I),
    "negation_only": re.compile(r"\b(not|no|never|none|without)\b|n'?t\b", re.I),
    "confirm": re.compile(r"\?|\b(right|yeah|yea|yes|correct|innit|check|did i (say|tell)|was it)\b", re.I),
}
# ask-back families: the user's answer to the assistant's yes/no question (check-only)
YES = re.compile(r"\b(yes|yeah|yep|yup|yea|ya|yh|correct|right|exactly|true|sure is|she is|he is|i am|i do|she does|"
                 r"he does|that'?s it|thats it|that'?s right|thats right)\b", re.I)
NO = re.compile(r"\b(no|nope|nah|not|never|wrong)\b|n'?t\b", re.I)
SELF_STATE = re.compile(r"\b(i'?m|i am|i feel|i was|i'?ve been)\b", re.I)
ALT = {
    "mother": "mother|mom|mum|mama|mommy|mummy|ma", "father": "father|dad|daddy|papa|pops|pa",
    "grandmother": "grandmother|grandma|gran|granny|nan|nana", "grandfather": "grandfather|grandpa|granddad|grandad|gramps",
    "sister": "sister|sis", "brother": "brother|bro", "best friend": "best friend|bestie|bff|best mate",
    "colleague": "colleague|coworker|co-worker|workmate", "neighbour": "neighbour|neighbor",
    "roommate": "roommate|flatmate|housemate|room mate", "husband": "husband|hubby", "aunt": "aunt|auntie|aunty",
    "friend": "friend|mate|buddy|pal", "cousin": "cousin|cuz", "landlord": "landlord|landlady",
    "dog": "dog|doggo|pup|puppy", "cat": "cat|kitty|kitten", "rabbit": "rabbit|bunny", "parrot": "parrot|bird",
}


def _pat(s):
    return r"(?<![A-Za-z0-9])(" + re.escape(s.strip()) + r")(?:'s|’s|s)?(?![A-Za-z0-9])"


def forms(s, text):
    return {m.group(1) for m in re.finditer(_pat(s), text or "", re.I)}


def typed_form(s, text):
    """s as typed in text: s itself if present exactly, else the single other casing, None if absent, '' if mixed."""
    f = forms(s, text)
    if not f:
        return None
    if s in f:
        return s
    return f.pop() if len(f) == 1 else ""


def any_word(words, text):
    alts = []
    for w in words:
        alts += ALT.get(w, w).split("|")
    return any(forms(a, text) for a in alts)


def gender_of(d):
    return {p["name"]: p["gender"] for p in d["people"]}


def check_turn(d, parsed, i):
    """Return (row or None, reasons list)."""
    t = d["turns"][i]
    u = parsed[i]["user"].strip()
    rb = (parsed[i].get("reply_before") or "").strip()
    history = [(parsed[j]["user"].strip(), (parsed[j + 1].get("reply_before") or "").strip()) for j in range(i)]
    vis = history[-HIST_TURNS:]
    vis_text = "\n".join(x for pair in vis for x in pair)
    earlier_users = "\n".join(h[0] for h in history)
    gold = t["gold"]
    R = []
    if len(u) > MAX_TURN or len(rb) > MAX_REPLY:
        R.append("too_long")
    rename = {}
    for s in t["must"]:
        f = typed_form(s, u)
        if f is None:
            R.append("must_missing")
        elif f == "":
            R.append("mixed_case")
        else:
            assert CMP.whole_word_span(f, u)
            rename[s] = f
    if t.get("first_person") and not CMP.ME_WORDS.search(u):
        R.append("no_first_person")
    for alts in t.get("role_words") or []:
        if not any_word(alts, u):
            R.append("role_word_missing")
    if any(forms(s, u) for s in t.get("must_not") or []):
        R.append("forbidden_in_turn")
    if any(forms(s, rb) for s in t.get("reply_must_not") or []):
        R.append("forbidden_in_reply")
    names = [p["name"] for p in d["people"]] + list(d.get("proper_values") or [])
    ok_names = set(t["must"]) | set(t.get("must_not") or [])
    if t["intent"] == "yes_after_ask":
        ok_names.add(t["reply_ask"]["owner"])   # "yes, Mira is" names the person asked about
    if any(forms(n, u) for n in names if n not in ok_names):
        R.append("stray_name")
    asked_val = (t.get("reply_ask") or {}).get("value")   # the ask-back question may name the value it asks about
    if any(forms(n, rb) and not forms(n, earlier_users) for n in names if n != asked_val):
        R.append("reply_new_name")
    owner_typed = None
    if t["intent"] == "backref":
        g = gender_of(d)
        o = gold["facts"][0]["owner"]
        for h_u, h_a in reversed(vis):
            owner_typed = typed_form(o, h_u) or typed_form(o, h_a)
            if owner_typed:
                break
        if not owner_typed or not CMP.whole_word_span(owner_typed, vis_text):
            R.append("owner_not_in_history")
        ref = t["ref"]
        if not any_word(ref["words"], u):
            R.append("ref_word_missing")
        if ref["kind"] == "pronoun":
            seen = {n for n in g if g[n] == g[o] and forms(n, vis_text + "\n" + u + "\n" + rb)}
            if seen != {o}:
                R.append("pronoun_not_unique")
        elif not any(forms(o, h_u) and any_word(ref["words"], h_u) for h_u, _ in vis):
            R.append("role_link_not_visible")
    intent = t["intent"]
    ra = t.get("reply_ask")
    if ra:
        rv = typed_form(ra["value"], rb)
        if not rb.endswith("?") or not rv or (ra["owner"] != "me" and not typed_form(ra["owner"], rb)):
            R.append("reply_ask_missing")
        elif ra["owner"] == "me" and not re.search(r"\byou\b", rb, re.I):
            R.append("reply_ask_missing")
        else:
            rename[ra["value"]] = rv
            if ra["owner"] != "me":
                rename[ra["owner"]] = typed_form(ra["owner"], rb)
        if intent == "ack_after_ask" and (YES.search(u) or NO.search(u)):
            R.append("ack_answers")
        if intent == "yes_after_ask":
            if not YES.search(u) or NO.search(u):
                R.append("yes_missing")
            if HEDGE.search(u):
                R.append("assert_hedged")
    if PLAN_LEAK.search(u) or PLAN_LEAK.search(rb):
        R.append("plan_leak")
    if intent in ASSERTING:
        if HEDGE.search(u):
            R.append("assert_hedged")
        if REPORTED.search(u):
            R.append("assert_reported")
        for f in gold["facts"]:
            ff = dict(f, value=rename.get(f["value"], f["value"]), mode="ASSERT")
            if f["rel"] in CURRENT_RELS and is_former(ff, u):
                R.append("reads_former")
    elif intent == "former":
        if not PAST.search(u):
            R.append("no_past_cue")
        if PRESENT.search(NEG_NOW.sub(" ", u)):
            R.append("former_present_cue")
    elif intent in LOOK or intent == "ask":
        assert not any(f["mode"] in WRITE for f in gold["facts"]), (d["dialog_id"], t["k"])
        if intent in CUES and not CUES[intent].search(u):
            R.append("no_cue")
    elif intent == "smalltalk" and SELF_STATE.search(u):
        R.append("smalltalk_self")
    if R:
        return None, sorted(set(R))
    fr = copy.deepcopy(gold)
    for f in fr["facts"]:
        for k in ("owner", "value", "old"):
            if k in f and f[k] in rename:
                f[k] = rename[f[k]]
        if intent == "backref":
            f["owner"] = owner_typed
    if fr.get("ask"):
        for k in ("owner", "value"):
            if k in fr["ask"] and fr["ask"][k] in rename:
                fr["ask"][k] = rename[fr["ask"][k]]

    def pos(f):
        m = re.search(_pat(f["value"]), u)
        return m.start() if m else 10 ** 6
    fr["facts"] = sorted(fr["facts"], key=pos)
    fr = canon_frame(fr)
    row = {"id": f"glm320-{d['dialog_id']}-t{t['k']}", "prompt": build_prompt_hist(u, rb, history),
           "target": frame_text(fr), "src": "glm320", "family": intent, "turn": u, "prev_reply": rb, "frame": fr,
           "history": [list(h) for h in history]}
    return row, [("recased" if rename and any(k != v for k, v in rename.items()) else "")]


def check_all(seeds, raws):
    by = {r["dialog_id"]: r for r in raws}
    c, fam, rows, drops = Counter(), Counter(), [], []
    for d in seeds:
        r = by.get(d["dialog_id"])
        if r is None:
            continue
        c["dialogs"] += 1
        c["turns"] += len(d["turns"])
        parsed = (r.get("parsed") or {}).get("turns")
        if not parsed or len(parsed) != len(d["turns"]):
            c["dialogs_unparsed"] += 1
            c["drop:dialog_unparsed"] += len(d["turns"])
            continue
        for i in range(len(d["turns"])):
            row, why = check_turn(d, parsed, i)
            if row is None:
                c["dropped"] += 1
                for w in why:
                    c["drop:" + w] += 1
                c[f"dropped:{d['turns'][i]['intent']}"] += 1
                drops.append({"dialog_id": d["dialog_id"], "k": d["turns"][i]["k"],
                              "intent": d["turns"][i]["intent"], "reasons": why, "turn": parsed[i]["user"],
                              "reply_before": parsed[i].get("reply_before", "")})
            else:
                c["kept"] += 1
                c["recased"] += why == ["recased"]
                fam[row["family"]] += 1
                rows.append(row)
    return rows, drops, c, fam


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def selftest():
    F = lambda o, r, v, m, old=None: dict({"owner": o, "rel": r, "value": v, "mode": m}, **({"old": old} if old else {}))  # noqa: E731
    T = lambda k, intent, gold, must, **kw: dict({"k": k, "intent": intent, "gold": gold, "must": must,  # noqa: E731
                                                "first_person": False, "must_not": [], "reply_must_not": [],
                                                "ref": None, "role_words": []}, **kw)
    fr = lambda act, facts, ask=None: {"act": act, "facts": facts, "ask": ask}  # noqa: E731
    seed = {"dialog_id": "st-1", "opener": False, "proper_values": ["Dunmere", "Korlo Foods", "Velbrook"],
            "people": [{"name": "Mira", "gender": "f", "role": "sister"}, {"name": "Tovan", "gender": "m", "role": "boss"},
                       {"name": "Selka", "gender": "f", "role": "friend"}],
            "turns": [
                T(1, "teach", fr("STATE", [F("me", "sister", "Mira", "ASSERT"), F("Mira", "occupation", "nurse", "ASSERT")]),
                  ["Mira", "nurse"], first_person=True, role_words=[["sister"]]),
                T(2, "teach", fr("STATE", [F("me", "boss", "Tovan", "ASSERT")]), ["Tovan"], first_person=True,
                  role_words=[["boss"]]),
                T(3, "backref", fr("STATE", [F("Mira", "city", "Velbrook", "ASSERT")]), ["Velbrook"], must_not=["Mira"],
                  reply_must_not=["Mira"], ref={"kind": "pronoun", "gender": "f", "words": ["she", "her", "hers"]}),
                T(4, "correct", fr("CORRECT", [F("Mira", "occupation", "midwife", "CORRECT", "nurse")]),
                  ["midwife", "Mira", "nurse"]),
                T(5, "former", fr("STATE", [F("Tovan", "employer", "Korlo Foods", "FORMER")]), ["Korlo Foods", "Tovan"]),
                T(6, "ask", fr("ASK", [], {"owner": "Mira", "rel": "city", "inverse": False}), ["Mira"],
                  must_not=["Velbrook"]),
                T(7, "plan", fr("PLAN", [F("me", "city", "Dunmere", "PLAN")]), ["Dunmere"], first_person=True),
                T(8, "smalltalk", fr("CHAT", []), [], must_not=["Mira", "Tovan", "Selka"]),
            ]}
    fake = {"turns": [
        {"n": 1, "reply_before": "", "user": "ok so my sister mira is a nurse lol"},
        {"n": 2, "reply_before": "nice!", "user": "and my boss is Tovan, hes alright"},
        {"n": 3, "reply_before": "cool", "user": "she just moved to Velbrook btw"},
        {"n": 4, "reply_before": "oh wow", "user": "wait mira isnt a nurse anymore shes a midwife now"},
        {"n": 5, "reply_before": "got it", "user": "Tovan works at Korlo Foods"},
        {"n": 6, "reply_before": "noted", "user": "where does Mira live again?"},
        {"n": 7, "reply_before": "Velbrook, you said.", "user": "im moving to Dunmere next year"},
        {"n": 8, "reply_before": "exciting", "user": "anyway how's your day going Mira"},
    ]}
    bad3 = copy.deepcopy(fake)
    bad3["turns"][2]["reply_before"] = "how is mira?"
    seed2 = dict(copy.deepcopy(seed), dialog_id="st-2")
    seed3 = dict(copy.deepcopy(seed), dialog_id="st-3")
    raws = [{"dialog_id": "st-1", "parsed": fake}, {"dialog_id": "st-2", "parsed": bad3},
            {"dialog_id": "st-3", "parsed": None}]
    rows, drops, c, fam = check_all([seed, seed2, seed3], raws)
    got = {(x["dialog_id"], x["k"]): x["reasons"] for x in drops}
    assert got[("st-1", 5)] == ["no_past_cue"], got
    assert got[("st-1", 8)] == ["forbidden_in_turn"], got
    assert got[("st-2", 3)] == ["forbidden_in_reply"], got
    assert c["dialogs_unparsed"] == 1 and c["drop:dialog_unparsed"] == 8, c
    assert c["kept"] == 6 + 5 and c["dropped"] == 2 + 3, c
    r = {x["id"]: x for x in rows}
    r1 = r["glm320-st-1-t1"]
    assert r1["frame"]["facts"] == [F("me", "sister", "mira", "ASSERT"), F("mira", "occupation", "nurse", "ASSERT")]
    r3 = r["glm320-st-1-t3"]
    assert r3["frame"]["facts"][0]["owner"] == "mira" and len(r3["history"]) == 2
    assert r3["prompt"] == build_prompt_hist("she just moved to Velbrook btw", "cool",
                                             [("ok so my sister mira is a nurse lol", "nice!"),
                                              ("and my boss is Tovan, hes alright", "cool")])
    assert r3["target"] == frame_text(r3["frame"]) and r3["src"] == "glm320" and r3["family"] == "backref"
    assert r["glm320-st-1-t4"]["frame"]["facts"][0]["old"] == "nurse"
    assert r["glm320-st-1-t6"]["frame"] == {"act": "ASK", "facts": [], "ask": {"owner": "Mira", "rel": "city",
                                                                              "inverse": False}}
    assert r["glm320-st-1-t7"]["frame"]["facts"][0]["mode"] == "PLAN"
    # a second same-gender name in view makes the pronoun ambiguous
    amb = copy.deepcopy(fake)
    amb["turns"][1]["user"] = "and my boss is Tovan, hes alright"
    amb["turns"][2]["user"] = "Selka came over, she just moved to Velbrook btw"
    _, why = check_turn(seed, amb["turns"], 2)
    assert "pronoun_not_unique" in why and "stray_name" in why, why
    # ask-back families: the assistant asks a yes/no; the user only acknowledges (no fact) or says yes (fact from the ask)
    RA = lambda o, r_, v: {"owner": o, "rel": r_, "value": v, "text": "x"}  # noqa: E731
    sa = {"dialog_id": "st-4", "opener": False, "proper_values": ["Velbrook"],
          "people": [{"name": "Mira", "gender": "f", "role": "sister"}],
          "turns": [T(1, "teach", fr("STATE", [F("me", "sister", "Mira", "ASSERT")]), ["Mira"], first_person=True,
                      role_words=[["sister"]]),
                    T(2, "ack_after_ask", fr("CHAT", []), [], must_not=["Velbrook", "Mira"],
                      reply_ask=RA("Mira", "city", "Velbrook")),
                    T(3, "yes_after_ask", fr("STATE", [F("Mira", "hobby", "pottery", "ASSERT")]), [],
                      reply_ask=RA("Mira", "hobby", "pottery")),
                    T(4, "yes_after_ask", fr("STATE", [F("me", "occupation", "baker", "ASSERT")]), [],
                      first_person=True, reply_ask=RA("me", "occupation", "baker"))]}
    pa = [{"n": 1, "reply_before": "", "user": "my sister Mira is visiting"},
          {"n": 2, "reply_before": "Does Mira live in Velbrook?", "user": "ok ty, gonna sleep on it. night!"},
          {"n": 3, "reply_before": "Is mira into pottery?", "user": "yep big time"},
          {"n": 4, "reply_before": "Are you a baker?", "user": "yeah i am"}]
    row2, _ = check_turn(sa, pa, 1)
    row3, _ = check_turn(sa, pa, 2)
    row4, _ = check_turn(sa, pa, 3)
    assert row2 is not None and row2["frame"]["facts"] == [] and row2["family"] == "ack_after_ask", row2
    assert row3 is not None and row3["frame"]["facts"] == [F("mira", "hobby", "pottery", "ASSERT")], row3
    assert row4 is not None and row4["frame"]["facts"] == [F("me", "occupation", "baker", "ASSERT")], row4
    assert CMP.check_fact(row3["frame"]["facts"][0], row3["turn"], row3["prev_reply"]) is None
    assert CMP.check_fact(row4["frame"]["facts"][0], row4["turn"], row4["prev_reply"]) is None
    for i, user, rb, want in [(1, "yes she does", "Does Mira live in Velbrook?", "ack_answers"),
                              (1, "ok thanks", "Does Mira live somewhere nice?", "reply_ask_missing"),
                              (2, "nah not really", "Is mira into pottery?", "yes_missing"),
                              (2, "yeah i think so", "Is mira into pottery?", "assert_hedged"),
                              (3, "yep", "Are you a baker?", "no_first_person")]:
        pb = copy.deepcopy(pa)
        pb[i] = {"n": i + 1, "reply_before": rb, "user": user}
        _, why = check_turn(sa, pb, i)
        assert want in why, (i, user, why)
    print(f"check selftest OK: kept {c['kept']}, dropped {c['dropped']} + {c['drop:dialog_unparsed']} (unparsed), "
          f"reasons {dict(sorted((k, v) for k, v in c.items() if k.startswith('drop:')))}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds")
    ap.add_argument("--raw")
    ap.add_argument("--out")
    ap.add_argument("--drops")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    rows, drops, c, fam = check_all(load(a.seeds), load(a.raw))
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    if a.drops:
        Path(a.drops).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in drops), encoding="utf-8")
    print(json.dumps({"counts": dict(sorted(c.items())), "kept_by_family": dict(sorted(fam.items()))}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
