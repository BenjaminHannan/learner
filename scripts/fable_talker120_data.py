#!/usr/bin/env python3
"""Experiment 120 (talker mouth PREP) — synthetic notebook-answer records -> English.

Plain software. Generates fine-tune pairs AND the sealed held-out panel from
templates written for THIS experiment (not exp 53's): >= 30 surface forms per
status, six notebook-answer statuses (OK / UNKNOWN / ABSTAIN / CLARIFY /
SAVED / FORGOT) plus a provenance field (taught | inferred | sleep-derived |
web-verified). Names AND values come from synthetic pools; the TRAIN pool and
the TEST pool are disjoint by construction (asserted).

Every target sentence carries exactly one status anchor so the rule-based
classifier in fable_talker120_mouth.classify can read the status back:
  OK      -> answer verbatim, no anchor word (default class)
  UNKNOWN -> "don't know"   ABSTAIN -> "can't answer that"
  CLARIFY -> "do you mean"/"which one"   SAVED -> "saved"   FORGOT -> "forgotten"

Machine-checks (fail loudly, exit 1): train/test name+value pools disjoint;
all 3,500 sentences pass brake_check; every sentence classifies to its own
status; every OK sentence contains its answer; every status uses >= 30
distinct surface forms (counted after blanking names/values).

Usage:
  python -B scripts/fable_talker120_data.py --out artifacts/fable-talker120-20260922/data --seed 12001
Writes train.jsonl ({record, sentence}) and heldout.jsonl ({record, reference}).
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from fable_talker120_mouth import brake_check, classify

SEED_DEFAULT = 12001

VILLAGE_RELS = ("mother", "father", "child", "sibling", "spouse", "employer", "hometown", "school")
OPEN_RELS = (
    "mentor", "neighbour", "doctor", "teacher", "boss", "best_friend", "cousin",
    "grandmother", "grandfather", "uncle", "aunt", "nephew", "niece", "partner",
    "roommate", "teammate", "coach", "dentist", "lawyer", "barber", "baker",
    "florist", "plumber", "driver", "nurse", "professor", "landlord", "tenant",
    "godmother", "pen_pal",
)

# Synthetic pools. TRAIN_* and TEST_* are disjoint by construction (asserted).
TRAIN_NAMES = (
    "Adel", "Bex", "Corin", "Dessa", "Elmo", "Fina", "Goran", "Hela",
    "Ivo", "Jessa", "Karel", "Lumo", "Miro", "Nessa", "Odin", "Pella",
    "Quin", "Rosa", "Sima", "Tessa", "Ulf", "Vera", "Wynn", "Xela",
    "Yara", "Zeno", "Ash", "Bram", "Cleo", "Dara", "Emil", "Faye",
    "Gus", "Hana", "Ivan", "Juno", "Koda", "Lila", "Mara", "Niko",
    "Ona", "Petra", "Rhea", "Seth", "Talia", "Ula", "Viggo", "Wren",
)
TEST_NAMES = (
    "Alba", "Boris", "Celia", "Dorian", "Esme", "Farah", "Gideon", "Hazel",
    "Ida", "Jasper", "Kito", "Leon", "Mabel", "Nadia", "Otis", "Pippa",
    "Ramon", "Selma", "Tobin", "Umar", "Vita", "Waldo", "Ximena", "Yusuf",
    "Zelda", "Amos", "Berta", "Casper", "Delia", "Edwin", "Flora", "Garth",
    "Hilda", "Iris", "Joren", "Kasia", "Ludo", "Marta", "Nils", "Opal",
    "Pavel", "Runa", "Sten", "Tilda", "Ulma", "Vesper", "Wilma", "Ysolde",
)
TRAIN_PLACES = (
    "Lakeside", "Milltown", "Riverton", "Hillcrest", "Brookfield", "Stonebridge",
    "Elmwood", "Copperton", "Fairview", "Maplewood", "Northgate", "Sunfield",
)
TEST_PLACES = (
    "Ashford", "Bayview", "Clearwater", "Dunmore", "Eastvale", "Foxglove",
    "Greenbank", "Harbourton", "Inkwell", "Juniper", "Kestrel", "Larkspur",
)

SOURCES = ("taught", "inferred", "sleep-derived", "web-verified")


def owner_phrase(name: str, relations: list[str]) -> str:
    return "'s ".join([name] + [r.replace("_", " ") for r in relations])


# ------------------------------------------------------------- 30+ per status
# Slots: {o}=owner phrase, {a}=answer, {s}=subject, {r}=relation wording,
# {v}=value, {n}=name, {c}=choices, {e}=reason.

T_OK = [
    "{o} is {a}.", "The answer is {a}: {o}.", "{o} -- that is {a}.",
    "I found it: {o} is {a}.", "{o} is {a}, as taught.",
    "So {o} is {a}.", "Yes: {o} is {a}.", "{o} is {a}, I am sure.",
    "Here it is: {o} is {a}.", "{o} is {a} -- that is what I have.",
    "What I have is this: {o} is {a}.", "{o} is {a}, and that is all.",
    "Right: {o} is {a}.", "{o} is {a}. That is the answer.",
    "The fact is {o} is {a}.", "I can tell you: {o} is {a}.",
    "{o} is {a}, no doubt.", "OK: {o} is {a}.",
    "{o} is {a} -- I have that fact.", "I have it: {o} is {a}.",
    "{o} is {a}; that I know.", "It is {a}: {o}.",
    "{o} is {a}, plain and simple.", "To tell the truth: {o} is {a}.",
    "{o} is {a} -- ask me again and I will say the same.",
    "My answer is {a}: {o}.", "{o} is {a}, ever since you told me.",
    "You told me, so I know: {o} is {a}.", "{o} is {a}. There you go.",
    "There you go: {o} is {a}.", "For the record: {o} is {a}.",
    "{o} is {a} -- that has not changed.",
]

T_UNKNOWN = [
    "I don't know {s}'s {r}.", "I don't know who {s}'s {r} is.",
    "Sorry, I don't know {s}'s {r} -- that fact is missing.",
    "I don't know: nobody taught me {s}'s {r}.",
    "I don't know {s}'s {r} yet.", "That is missing: I don't know {s}'s {r}.",
    "I don't know {s}'s {r}, I am afraid.",
    "No: I don't know {s}'s {r}.",
    "I don't know {s}'s {r} -- you never told me.",
    "I don't know {s}'s {r}. Please tell me some time.",
    "Hmm, I don't know {s}'s {r}.",
    "Well, I don't know {s}'s {r}.",
    "I don't know {s}'s {r}, and I will not guess.",
    "I have no fact, so I don't know {s}'s {r}.",
    "I don't know {s}'s {r}: my notebook has nothing there.",
    "Nothing taught, so I don't know {s}'s {r}.",
    "I don't know {s}'s {r} -- still missing.",
    "Even now, I don't know {s}'s {r}.",
    "I don't know {s}'s {r}. That is all I can say.",
    "Ask me again later: I don't know {s}'s {r}.",
    "I don't know {s}'s {r}, sorry to say.",
    "Sorry to say, I don't know {s}'s {r}.",
    "Oh, I don't know {s}'s {r}.",
    "I don't know {s}'s {r} -- never heard that one.",
    "Never heard that one, so I don't know {s}'s {r}.",
    "I don't know {s}'s {r}; nobody said.",
    "Nobody said, so I don't know {s}'s {r}.",
    "I don't know {s}'s {r} -- that is beyond what I was taught.",
    "Beyond what I was taught: I don't know {s}'s {r}.",
    "I don't know {s}'s {r}, truly.",
]

T_ABSTAIN = [
    "I can't answer that: {e}.", "Sorry, I can't answer that: {e}.",
    "I can't answer that question: {e}.", "I can't answer that -- {e}.",
    "I can't answer that: {e} Nothing was done.",
    "That did not work: I can't answer that: {e}.",
    "No answer: I can't answer that: {e}.",
    "I must abstain: I can't answer that: {e}.",
    "I can't answer that, as {e}.", "Since {e}, I can't answer that.",
    "I can't answer that -- since {e}.",
    "Please ask again later: I can't answer that: {e}.",
    "I can't answer that yet: {e}.", "Even so, I can't answer that: {e}.",
    "I can't answer that, I am afraid: {e}.",
    "Well, I can't answer that: {e}.",
    "Hmm, I can't answer that: {e}.",
    "Right now I can't answer that: {e}.",
    "For now, I can't answer that: {e}.",
    "I can't answer that -- for now: {e}.",
    "Oh, I can't answer that: {e}.",
    "Truly, I can't answer that: {e}.",
    "I can't answer that: {e} -- that is all I can say.",
    "That is all I can say: I can't answer that: {e}.",
    "I can't answer that; {e}, so nothing was done.",
    "Nothing was done: I can't answer that: {e}.",
    "I can't answer that -- nothing was done, as {e}.",
    "Ask me something else: I can't answer that: {e}.",
    "I can't answer that one: {e}.",
    "One more time: I can't answer that: {e}.",
]

T_CLARIFY = [
    "Which {n} do you mean: {c}?",     "Which {n}? I know more than one: {c}. Which one do you mean?",
    "I know more than one {n}: {c}. Which one do you mean?",
    "There is more than one {n} ({c}). Which one do you mean?",
    "I know more than one person called {n}: {c}. Which one?",
    "More than one {n}, I am afraid: {c}. Which one do you mean?",
    "I know more than one {n} -- {c} -- which one do you mean?",
    "Do you mean {c}? There is more than one {n}.",
    "Which one do you mean? I know more than one {n}: {c}.",
    "I mean, which {n} do you mean: {c}?",
    "Tell me which one: I know more than one {n} ({c}).",
    "Which one -- {c}? Do you mean one of those?",
    "Do you mean one of these: {c}?",
    "Is it one of these, {c}? Which one do you mean?",
    "There are two here: {c}. Which {n} do you mean?",
    "Two of them, I fear: {c}. Which {n} do you mean?",
    "I fear there is more than one {n}: {c}. Which one?",
    "Hmm, which {n} do you mean: {c}?",
    "Well, which one do you mean? I see {c}.",
    "I see {c}. Which {n} do you mean?",
    "So many! Which {n} do you mean: {c}?",
    "Which one, please: {c}? I know more than one {n}.",
    "Please tell me which one you mean: {c}.",
    "Do tell me: which {n} is it: {c}? Do you mean one of those?",
    "You must tell me which one you mean: {c}.",
    "I cannot tell which you mean: {c}. Which one?",
    "Which one is it: {c}? Do you mean one of those?",
    "One of those, perhaps: {c}. Which one do you mean?",
    "Perhaps one of these: {c}. Which {n} do you mean?",
    "Now, which one do you mean: {c}?",
]

T_SAVED = [
    "Saved: {o} is {a}.", "Saved it: {o} is {a}.",
    "I saved that: {o} is {a}.", "Got it, saved: {o} is {a}.",
    "Saved -- {o} is {a}.", "All saved: {o} is {a}.",
    "Yes, saved: {o} is {a}.", "Saved, thank you: {o} is {a}.",
    "Thank you, saved: {o} is {a}.", "I have saved that: {o} is {a}.",
    "That is saved now: {o} is {a}.", "Now saved: {o} is {a}.",
    "Saved for later: {o} is {a}.", "I saved it for later: {o} is {a}.",
    "Written and saved: {o} is {a}.",
    "I wrote that down and saved it: {o} is {a}.",
    "Down in my notebook and saved: {o} is {a}.",
    "My notebook has it saved: {o} is {a}.",
    "Saved in my notebook: {o} is {a}.",
    "I will keep that saved: {o} is {a}.",
    "Kept and saved: {o} is {a}.",
    "Saved, and I will say the same next time: {o} is {a}.",
    "Done -- saved: {o} is {a}.", "OK, saved: {o} is {a}.",
    "Right, saved: {o} is {a}.", "Well, that is saved: {o} is {a}.",
    "Hmm, saved at last: {o} is {a}.",
    "Saved at last: {o} is {a}.", "There, saved: {o} is {a}.",
    "So that is saved: {o} is {a}.",
]

T_FORGOT = [
    "I've forgotten {s}'s {r}.", "I have forgotten {s}'s {r}.",
    "Sorry, I've forgotten {s}'s {r}.",
    "That is gone: I've forgotten {s}'s {r}.",
    "I've forgotten {s}'s {r} -- please tell me again.",
    "Please tell me again: I've forgotten {s}'s {r}.",
    "Oh no, I've forgotten {s}'s {r}.",
    "Well, I've forgotten {s}'s {r}.",
    "Hmm, I've forgotten {s}'s {r}.",
    "I am afraid I've forgotten {s}'s {r}.",
    "Truly, I've forgotten {s}'s {r}.",
    "It seems I've forgotten {s}'s {r}.",
    "I seem to have forgotten {s}'s {r}.",
    "Somehow I've forgotten {s}'s {r}.",
    "For now, I've forgotten {s}'s {r}.",
    "Even now I've forgotten {s}'s {r}.",
    "Still, I've forgotten {s}'s {r}.",
    "I forgot {s}'s {r} -- sorry.",
    "Sorry: I forgot {s}'s {r}.",
    "I forgot {s}'s {r}, I fear.",
    "Alas, I've forgotten {s}'s {r}.",
    "What a shame: I've forgotten {s}'s {r}.",
    "My notebook no longer has it: I've forgotten {s}'s {r}.",
    "That fact is gone, I've forgotten {s}'s {r}.",
    "Gone: I've forgotten {s}'s {r}.",
    "I once knew, but I've forgotten {s}'s {r}.",
    "Once I knew, yet I've forgotten {s}'s {r}.",
    "Time passed and I've forgotten {s}'s {r}.",
    "I've forgotten {s}'s {r}, truly I have.",
    "Yes, I've forgotten {s}'s {r}.",
]

TEMPLATES = {
    "OK": T_OK, "UNKNOWN": T_UNKNOWN, "ABSTAIN": T_ABSTAIN,
    "CLARIFY": T_CLARIFY, "SAVED": T_SAVED, "FORGOT": T_FORGOT,
}

HELDOUT_MIX = (
    ("OK", 250), ("UNKNOWN", 50), ("ABSTAIN", 50),
    ("CLARIFY", 50), ("SAVED", 50), ("FORGOT", 50),
)
TRAIN_MIX = (
    ("OK", 1250), ("UNKNOWN", 450), ("ABSTAIN", 350),
    ("CLARIFY", 350), ("SAVED", 300), ("FORGOT", 300),
)
ABSTAIN_REASONS = ("not a question I can use", "no name I know", "I need a name")


def rand_rel(rng: random.Random, village_bias: float = 0.6) -> str:
    if rng.random() < village_bias:
        return VILLAGE_RELS[rng.randrange(len(VILLAGE_RELS))]
    return OPEN_RELS[rng.randrange(len(OPEN_RELS))]


def make_record(rng: random.Random, status: str, names: tuple, places: tuple) -> dict:
    n_hops = rng.randint(1, 3)
    rels = [rand_rel(rng) for _ in range(n_hops)]
    name = names[rng.randrange(len(names))]
    source = SOURCES[rng.randrange(len(SOURCES))]
    base = {"kind": "answer", "status": status, "name": name, "relations": rels}
    if status in ("OK", "SAVED"):
        ans = names[rng.randrange(len(names))]
        if rng.random() < 0.3:
            ans = places[rng.randrange(len(places))]
        while ans == name:
            ans = names[rng.randrange(len(names))]
        base["fields"] = {"answer": ans,
                          "trail": [f"F{rng.randrange(1, 9999):05d}" for _ in rels],
                          "source": source}
        return base
    if status == "UNKNOWN":
        return dict(base, fields={"subject": name, "relation": rels[-1],
                                  "hop": n_hops, "trail": [], "source": source})
    if status == "ABSTAIN":
        return dict(base, fields={"reason": ABSTAIN_REASONS[rng.randrange(3)],
                                  "source": source})
    if status == "CLARIFY":
        a, b = names[rng.randrange(len(names))], names[rng.randrange(len(names))]
        while b == a:
            b = names[rng.randrange(len(names))]
        ids = [f"E{rng.randrange(1, 60):04d}", f"E{rng.randrange(1, 60):04d}"]
        return dict(base, fields={"name": name,
                                  "choices": f"{a} ({ids[0]}), {b} ({ids[1]})",
                                  "ids": ids, "source": source})
    if status == "FORGOT":
        return dict(base, fields={"subject": name, "relation": rels[-1],
                                  "hop": n_hops, "source": source})
    raise AssertionError(status)


def render(rng: random.Random, rec: dict) -> str:
    f = rec["fields"]
    kw: dict[str, str] = {}
    if rec["status"] in ("OK", "SAVED"):
        kw = {"o": owner_phrase(rec["name"], rec["relations"]), "a": f["answer"]}
    elif rec["status"] in ("UNKNOWN", "FORGOT"):
        kw = {"s": f["subject"], "r": f["relation"].replace("_", " ")}
    elif rec["status"] == "ABSTAIN":
        kw = {"e": f["reason"]}
    elif rec["status"] == "CLARIFY":
        kw = {"n": f["name"], "c": f["choices"]}
    s = TEMPLATES[rec["status"]][rng.randrange(len(TEMPLATES[rec["status"]]))].format(**kw)
    if rec["status"] == "OK" and f.get("source") == "web-verified":
        s += " (I read that online; you didn't tell me.)"
    return s


def surface_form(sentence: str) -> str:
    """Blank names/values: keep the skeleton for the >= 30-forms check."""
    return sentence


def build(mix: tuple, total: int, seed: int, names: tuple, places: tuple) -> list[dict]:
    rng = random.Random(seed)
    rows: list[dict] = []
    assert sum(c for _, c in mix) == total
    for status, count in mix:
        for _ in range(count):
            rec = make_record(rng, status, names, places)
            rows.append({"record": rec, "sentence": render(rng, rec)})
    rng.shuffle(rows)
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 120 mouth data generator")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    assert not (set(TRAIN_NAMES) & set(TEST_NAMES)), "name pools overlap"
    assert not (set(TRAIN_PLACES) & set(TEST_PLACES)), "place pools overlap"
    for st, ts in TEMPLATES.items():
        assert len(ts) >= 30, (st, len(ts))

    train_rows = build(TRAIN_MIX, 3000, args.seed, TRAIN_NAMES, TRAIN_PLACES)
    held_rows = build(HELDOUT_MIX, 500, args.seed + 77, TEST_NAMES, TEST_PLACES)

    # ---- machine-checks (fail loudly) ----
    problems: list[str] = []
    forms: dict[str, set[str]] = {st: set() for st in TEMPLATES}
    for tag, rows in (("train", train_rows), ("heldout", held_rows)):
        for i, r in enumerate(rows):
            rec, s = r["record"], r["sentence"]
            ok, reason = brake_check(s, rec)
            if not ok:
                problems.append(f"{tag}[{i}] {rec['status']} brake: {reason}: {s!r}")
            if classify(s) != rec["status"]:
                problems.append(f"{tag}[{i}] {rec['status']} classifies as {classify(s)}: {s!r}")
            if rec["status"] in ("OK", "SAVED") and \
                    str(rec["fields"]["answer"]).lower() not in s.lower():
                problems.append(f"{tag}[{i}] answer missing: {s!r}")
            # surface form = template skeleton with slot strings blanked
            skel = s
            blanks = ([rec.get("name", "")]
                      + [str(v) for v in (rec.get("fields") or {}).values()
                         if isinstance(v, str)]
                      + [r_ for r_ in (rec.get("relations") or [])])
            for blank in blanks:
                if blank:
                    skel = skel.replace(blank, "#").replace(
                        blank.replace("_", " "), "#")
            forms[rec["status"]].add(skel)
            r["surface_forms_seen"] = None  # placeholder, stripped below
    for r in train_rows + held_rows:
        del r["surface_forms_seen"]
    for st, skels in forms.items():
        if len(skels) < 30:
            problems.append(f"status {st}: only {len(skels)} surface forms (< 30)")
    if problems:
        print(f"MACHINE-CHECK FAILED ({len(problems)}):")
        for p in problems[:20]:
            print("  " + p)
        return 1

    (out / "train.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in train_rows) + "\n",
        encoding="utf-8")
    (out / "heldout.jsonl").write_text(
        "\n".join(json.dumps({"record": r["record"], "reference": r["sentence"]},
                             ensure_ascii=False) for r in held_rows) + "\n",
        encoding="utf-8")
    meta = {"seed": args.seed, "train": len(train_rows), "heldout": len(held_rows),
            "statuses": sorted(TEMPLATES),
            "templates_per_status": {st: len(ts) for st, ts in TEMPLATES.items()},
            "surface_forms": {st: len(skels) for st, skels in forms.items()},
            "train_names": len(TRAIN_NAMES), "test_names": len(TEST_NAMES),
            "pools_disjoint": True}
    (out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps(meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
