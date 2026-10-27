#!/usr/bin/env python3
"""vread wrong-person diagnosis step 2: one line per dev backref gold card with what each reader did (helper W).

For each of the 136 dev backref rows (each has exactly one gold card, owner named), writes features of the prompt and the
outcome of both readers:
  cue        what in the turn points at the owner: role (the turn says "my <role>" and the owner was introduced with that
             role), pronoun (he/she/his/her/him/they/their/them in the turn) or other; both flags kept.
  gold_line  region of the owner's newest copy (2 = newest earlier-turn line ... ; 0/1 = turn / previous reply; text-only)
             even numbers are user lines, odd numbers are assistant lines
  words_back words between the end of the owner's closest copy and the start of the turn text
  persons    distinct person names (dialog gold-card names with a copy in the prompt) in the prompt; rank 0 = the person
             whose last copy ends nearest the end of the prompt (the prompt is chronological)
  outcome    per reader: right / wrong_person / me / none (no card with the gold relation and state), plus card confidence
  bar-aware  saved_right_hist and saved_wrong_hist (claude_vread_score.is_saved with the hist rule at the arm's own bar,
             0.97 vector and 0.995 LoRA), and the same at 0.995 and 0.97 for both

  python -B scripts/claude_vread_wp_table.py --out artifacts/claude-vread-wrongperson-20260928/table.jsonl
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_vread_wp_common as C  # noqa: E402
import claude_vread_score as VS  # noqa: E402

PRON = re.compile(r"\b(he|she|his|her|hers|him|they|their|them|he's|she's|hes|shes)\b", re.I)
FEMALE = {"mother", "sister", "aunt", "grandmother", "niece", "daughter", "wife", "ex_wife", "stepmother", "stepsister",
          "stepdaughter", "great_aunt", "great_grandmother", "godmother", "goddaughter", "half_sister", "granddaughter",
          "mother_in_law", "sister_in_law", "daughter_in_law"}
MALE = {"father", "brother", "uncle", "grandfather", "nephew", "son", "husband", "ex_husband", "stepfather",
        "stepbrother", "stepson", "great_uncle", "great_grandfather", "godfather", "half_brother", "grandson",
        "father_in_law", "brother_in_law", "son_in_law"}


def role_of(name, dialog_rows_upto):
    """the person-relation under which `me` introduced this name in the dialog's earlier gold cards, else None"""
    for r in dialog_rows_upto:
        for c in r["cards"]:
            if c["owner"] == "me" and c["value"] == name and c["rel"] in C.PERSON_RELS_SET:
                return c["rel"]
    return None


def outcome(card, gold):
    if card is None:
        return "none"
    if C.norm(card["owner"]) == C.norm(gold["owner"]):
        return "right"
    return "me" if card["owner"] == "me" else "wrong_person"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = C.dev_rows()
    by_dialog = {}
    for r in rows:
        by_dialog.setdefault(r["id"].rsplit("-t", 1)[0], []).append(r)
    names = C.dialog_names(rows)
    rd = {"vector": {x["id"]: x for x in C.load_jsonl(C.V1 / "run/out/vec_dev_reads.jsonl")},
          "lora": {x["id"]: x for x in C.load_jsonl(C.V1 / "run/out/lora_dev_reads.jsonl")}}
    out = []
    for r in rows:
        if r["family"] != "backref":
            continue
        d = r["id"].rsplit("-t", 1)[0]
        upto = [x for x in by_dialog[d] if int(x["id"].rsplit("-t", 1)[1]) < int(r["id"].rsplit("-t", 1)[1])]
        regions = C.regions_of(r)
        g = r["cards"][0]
        assert len(r["cards"]) == 1 and g["owner"] != "me"
        gcp = C.copies_text(g["owner"], r, regions)
        # persons present in the prompt, with the region and position of the newest copy
        pres = []
        for n in sorted(names[d]):
            cp = C.copies_text(n, r, regions)
            if cp:
                pres.append((n, max(c1 for _, _, c1 in cp)))
        pres.sort(key=lambda x: -x[1])         # the prompt is chronological, so the largest char end is the newest
        order = [n for n, _ in pres]
        turn_a, turn_b = regions[0]
        gnew = gcp[0]
        words_back = len(r["prompt"][max(c1 for _, _, c1 in gcp):turn_a].split())   # from the closest copy
        role = role_of(g["owner"], upto)
        role_phrase = ("my " + role.replace("_", " ")) if role else None
        cue_role = bool(role_phrase and role_phrase in r["turn"].lower())
        cue_pron = bool(PRON.search(r["turn"]))
        rec = {"id": r["id"], "gold_owner": g["owner"], "rel": g["rel"], "value": g["value"], "gold_role": role,
               "cue_role": cue_role, "cue_pronoun": cue_pron,
               "cue": "role" if cue_role and not cue_pron else "pronoun" if cue_pron and not cue_role else
               "both" if cue_role and cue_pron else "other",
               "gold_line": gnew[0], "gold_copies": len(gcp), "words_back": words_back, "n_persons": len(order),
               "gold_rank": order.index(g["owner"]), "persons_newest_first": order}
        # same-cue rivals
        rivals = [n for n in order if n != g["owner"]]
        rec["n_rivals"] = len(rivals)
        rec["rival_roles"] = {n: role_of(n, upto) for n in rivals}
        rec["same_role_rival"] = any(role_of(n, upto) == role and role for n in rivals)
        for arm in ("vector", "lora"):
            read = rd[arm].get(r["id"])
            cards = (read or {}).get("cards") or [] if arm == "vector" else C.lora_cards(read)
            mc = [c for c, k in C.match_cards(cards, r["cards"]) if k == 0]
            card = mc[0] if mc else None
            rec[arm] = {"outcome": outcome(card, g), "read_owner": card["owner"] if card else None,
                        "value_ok": bool(card) and C.norm(card["value"]) == C.norm(g["value"]),
                        "conf": card["conf"] if card else None,
                        "n_cards_emitted": len(cards)}
            if card and rec[arm]["outcome"] == "wrong_person":
                ro = card["owner"]
                rec[arm]["read_is_dialog_person"] = ro in names[d]
                rcp = C.copies_text(ro, r, regions)
                rec[arm]["read_owner_newest_region"] = rcp[0][0] if rcp else None
                rec[arm]["read_owner_rank"] = order.index(ro) if ro in order else None
                rec[arm]["read_owner_newer_than_gold"] = (rcp[0][0], rcp[0][1]) < (gnew[0], gnew[1]) if rcp else None
                rec[arm]["read_owner_last_char"] = max(c1 for _, _, c1 in rcp) if rcp else None
                rec[arm]["read_owner_more_recent_than_gold"] = (max(c1 for _, _, c1 in rcp) > max(c1 for _, _, c1 in gcp)) if rcp else None
                rec[arm]["read_owner_role"] = role_of(ro, upto)
            for bar_name, bar in (("own", 0.97 if arm == "vector" else 0.995), ("b995", 0.995), ("b97", 0.97)):
                if card:
                    rec[arm][f"saved_hist_{bar_name}"] = VS.is_saved(card, r, bar, "hist")
                    rec[arm][f"saved_right_hist_{bar_name}"] = VS.is_saved(card, r, bar, "hist") and VS.same(card, g)
                else:
                    rec[arm][f"saved_hist_{bar_name}"] = False
                    rec[arm][f"saved_right_hist_{bar_name}"] = False
        out.append(rec)
    Path(a.out).write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
    print(len(out), "backref rows written")


if __name__ == "__main__":
    main()
