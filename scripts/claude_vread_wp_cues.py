#!/usr/bin/env python3
"""vread wrong-person diagnosis step 3: what cue does the turn give, and does the wrong pick fit it? (helper W)

Reads artifacts/claude-vread-wrongperson-20260928/table.jsonl (step 2) and the dev rows. Text heuristics only, so every
count from here is 'suggested' unless it is a plain count of rows.

  turn cue    pronoun = the turn has he/she/his/her/him/they/their/them; role = no pronoun, and the turn says my/the/our
              + a role word (the 68 person relations plus wife/husband already in the list), else other
  role of a person in the prompt = role words found in the earlier-turn / reply lines that contain a copy of the name
  gender cue  for a pronoun turn: he/his/him -> male, she/her -> female, they/their -> none. A person is male-marked if
              a male role word (father, brother, ...) or a he/his pronoun follows the name in its line, female-marked
              likewise. A pick is 'gender-clash' if the person is marked with the other gender.

  python -B scripts/claude_vread_wp_cues.py --table artifacts/claude-vread-wrongperson-20260928/table.jsonl \
        --out artifacts/claude-vread-wrongperson-20260928/cues.json
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_vread_wp_common as C  # noqa: E402
import claude_vread_wp_table as TB  # noqa: E402

ROLES = sorted({r.replace("_", " ") for r in C.PERSON_RELS_SET} | {"wife", "husband"}, key=len, reverse=True)
ROLE_RE = re.compile(r"\b(?:my|the|our|his|her|a|an)\s+(" + "|".join(re.escape(r) for r in ROLES) + r")\b", re.I)
MALE_PRON = re.compile(r"\b(he|his|him|hes|he's)\b", re.I)
FEMALE_PRON = re.compile(r"\b(she|her|hers|shes|she's)\b", re.I)
NEUTRAL_PRON = re.compile(r"\b(they|their|them)\b", re.I)
MALE_ROLES = {r.replace("_", " ") for r in TB.MALE} | {"husband"}
FEMALE_ROLES = {r.replace("_", " ") for r in TB.FEMALE} | {"wife"}


def lines_with(name, row):
    """earlier-turn and reply lines (region 1 and up) that hold a copy of name, as text"""
    regions = C.regions_of(row)
    out = []
    for (a, b) in regions[1:]:
        seg = row["prompt"][a:b]
        if C.copies_text(name, {"prompt": seg}, [(0, len(seg))]):
            out.append(seg)
    return out


def person_marks(name, row):
    roles, gender = set(), set()
    for seg in lines_with(name, row):
        if seg.startswith("Assistant:"):
            continue
        for m in ROLE_RE.finditer(seg):
            roles.add(m.group(1).lower())
        # pronouns after the name in the same line (up to the next sentence end)
        for mm in re.finditer(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", seg):
            tail = re.split(r"[.!?]", seg[mm.end():], maxsplit=1)[0]
            if MALE_PRON.search(tail):
                gender.add("m")
            if FEMALE_PRON.search(tail):
                gender.add("f")
    if roles & MALE_ROLES:
        gender.add("m")
    if roles & FEMALE_ROLES:
        gender.add("f")
    return roles, gender


def turn_cue(turn):
    pron = bool(TB.PRON.search(turn))
    m = ROLE_RE.search(turn)
    g = set()
    if MALE_PRON.search(turn):
        g.add("m")
    if FEMALE_PRON.search(turn):
        g.add("f")
    cue = "pronoun" if pron else "role" if m else "other"
    return cue, (m.group(1).lower() if m else None), g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = {r["id"]: r for r in C.dev_rows()}
    T = [json.loads(x) for x in Path(a.table).read_text().splitlines()]
    per_row, cnt = [], Counter()
    by_cue = {arm: {} for arm in ("vector", "lora")}
    for t in T:
        r = rows[t["id"]]
        cue, role, tg = turn_cue(r["turn"])
        gr, gg = person_marks(t["gold_owner"], r)
        rec = {"id": t["id"], "cue": cue, "turn_role": role, "turn_gender": sorted(tg), "gold_roles": sorted(gr),
               "gold_gender_marks": sorted(gg), "rivals": {}}
        rec["gold_has_turn_role"] = bool(role and role in gr)
        rec["gold_gender_ok"] = (not tg) or (not gg) or bool(tg & gg)
        # rivals: other persons in the prompt, and whether they also fit the cue
        for n in t["persons_newest_first"]:
            if n == t["gold_owner"]:
                continue
            rr, rg = person_marks(n, r)
            rec["rivals"][n] = {"roles": sorted(rr), "gender_marks": sorted(rg),
                                "fits_role": bool(role and role in rr),
                                "fits_gender": (not tg) or (not rg) or bool(tg & rg)}
        rec["n_rivals_fit_cue"] = sum((v["fits_role"] if cue == "role" else v["fits_gender"] if cue == "pronoun" else False)
                                      for v in rec["rivals"].values())
        for arm in ("vector", "lora"):
            o = t[arm]["outcome"]
            by_cue[arm].setdefault(cue, Counter())[o] += 1
            if o == "wrong_person":
                ro = t[arm]["read_owner"]
                if ro in rec["rivals"]:
                    v = rec["rivals"][ro]
                    rec[f"{arm}_pick"] = {"name": ro, "roles": v["roles"], "gender_marks": v["gender_marks"],
                                          "fits_role": v["fits_role"], "fits_gender": v["fits_gender"]}
                else:
                    rec[f"{arm}_pick"] = {"name": ro, "not_a_person_in_prompt": True}
        per_row.append(rec)
    summary = {"rows": len(T),
               "cue_counts": dict(Counter(x["cue"] for x in per_row)),
               "outcome_by_cue": {arm: {k: dict(v) for k, v in d.items()} for arm, d in by_cue.items()},
               "role_cue_rows_where_gold_has_that_role": sum(x["gold_has_turn_role"] for x in per_row if x["cue"] == "role"),
               "role_cue_rows": sum(x["cue"] == "role" for x in per_row),
               "pronoun_rows_with_gender_word": sum(1 for x in per_row if x["cue"] == "pronoun" and x["turn_gender"]),
               "pronoun_rows_gold_gender_ok_or_unmarked": sum(x["gold_gender_ok"] for x in per_row if x["cue"] == "pronoun"),
               "rows_with_a_rival_that_also_fits_cue": sum(x["n_rivals_fit_cue"] > 0 for x in per_row)}
    for arm in ("vector", "lora"):
        picks = [x[f"{arm}_pick"] for x in per_row if f"{arm}_pick" in x]
        summary[f"{arm}_wrong_picks"] = {
            "n": len(picks),
            "not_a_person_in_prompt": sum(bool(p.get("not_a_person_in_prompt")) for p in picks),
            "role_cue_rows_where_pick_fits_role": sum(bool(p.get("fits_role")) for x, p in
                                                     ((x, x.get(f"{arm}_pick")) for x in per_row) if p and x["cue"] == "role"),
            "role_cue_rows_wrong": sum(1 for x in per_row if x["cue"] == "role" and f"{arm}_pick" in x),
            "pronoun_rows_wrong": sum(1 for x in per_row if x["cue"] == "pronoun" and f"{arm}_pick" in x),
            "pronoun_wrong_pick_fits_gender": sum(bool(p.get("fits_gender")) for x, p in
                                                  ((x, x.get(f"{arm}_pick")) for x in per_row) if p and x["cue"] == "pronoun"),
        }
    out = {"summary": summary, "rows": per_row}
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
