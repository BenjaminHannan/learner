#!/usr/bin/env python3
"""vread wrong-person diagnosis step 5: the numbers DIAGNOSIS.md quotes, in one file (helper W). Dev split only.

Inputs: table.jsonl (step 2), cues.json (step 3), and the raw dev reads for the all-family count.
  python -B scripts/claude_vread_wp_summary.py --dir artifacts/claude-vread-wrongperson-20260928
"""
import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_vread_wp_common as C  # noqa: E402


def cnt(it):
    return dict(sorted(Counter(it).items(), key=lambda kv: str(kv[0])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    d = Path(a.dir)
    T = [json.loads(x) for x in (d / "table.jsonl").read_text().splitlines()]
    cues = {x["id"]: x for x in json.loads((d / "cues.json").read_text())["rows"]}
    S = {}
    S["backref_rows"] = len(T)
    S["outcome"] = {arm: cnt(t[arm]["outcome"] for t in T) for arm in ("vector", "lora")}
    # 1. where the errors are: by how many people are named
    for arm in ("vector", "lora"):
        S[f"{arm}_by_n_persons"] = {k: cnt(t[arm]["outcome"] for t in T if t["n_persons"] == k) for k in (1, 2, 3)}
        S[f"{arm}_by_gold_rank_when_2plus"] = {
            "gold_newest": cnt(t[arm]["outcome"] for t in T if t["n_persons"] >= 2 and t["gold_rank"] == 0),
            "gold_not_newest": cnt(t[arm]["outcome"] for t in T if t["n_persons"] >= 2 and t["gold_rank"] > 0)}
    two = [t for t in T if t["n_persons"] >= 2]
    S["rows_2plus_persons"] = len(two)
    S["always_newest_person_rule_right_in"] = sum(t["gold_rank"] == 0 for t in two)
    S["always_newest_person_rule_right_in_all_backref"] = sum(t["gold_rank"] == 0 for t in T)
    # 2. what the wrong vector picks are
    w = [t for t in T if t["vector"]["outcome"] == "wrong_person"]
    picks = [t["vector"] for t in w]
    S["vector_wrong_picks"] = {
        "n": len(w),
        "known_person_in_dialog_cards": sum(bool(p.get("read_is_dialog_person")) for p in picks),
        "of_those_more_recent_than_gold": sum(p.get("read_is_dialog_person") is True and p.get("read_owner_more_recent_than_gold") is True for p in picks),
        "of_those_older_than_gold": sum(p.get("read_is_dialog_person") is True and p.get("read_owner_more_recent_than_gold") is False for p in picks),
        "of_those_the_newest_person_in_prompt": sum(p.get("read_is_dialog_person") is True and p.get("read_owner_rank") == 0 for p in picks),
        "value_right": sum(p["value_ok"] for p in picks),
        "conf_sorted": sorted(round(p["conf"], 3) for p in picks),
        "conf_at_or_above_0.97": sum(p["conf"] >= 0.97 for p in picks),
        "by_turn_cue": cnt(cues[t["id"]]["cue"] for t in w),
        "role_cue_wrong_picks": cnt(
            "pick has the turn's role" if cues[t["id"]]["vector_pick"].get("fits_role") else
            "not a known person" if cues[t["id"]]["vector_pick"].get("not_a_person_in_prompt") else
            "known person with another role" for t in w if cues[t["id"]]["cue"] == "role"),
        "pronoun_cue_wrong_picks": cnt(
            "not a known person" if cues[t["id"]]["vector_pick"].get("not_a_person_in_prompt") else
            "known person marked with the other gender" if not cues[t["id"]]["vector_pick"]["fits_gender"] else
            "known person with no gender mark" for t in w if cues[t["id"]]["cue"] == "pronoun"),
    }
    # 3. the same cards under the other reader
    S["lora_on_the_vector_wrong_cards"] = cnt(t["lora"]["outcome"] for t in w)
    wl = [t for t in T if t["lora"]["outcome"] == "wrong_person"]
    S["vector_on_the_lora_wrong_cards"] = cnt(t["vector"]["outcome"] for t in wl)
    S["both_wrong_ids"] = sorted(t["id"] for t in w if t["lora"]["outcome"] == "wrong_person")
    # 4. distance
    def med(xs):
        return statistics.median(xs) if xs else None
    S["words_back_2plus_persons"] = {
        "median_wrong": med([t["words_back"] for t in two if t["vector"]["outcome"] == "wrong_person"]),
        "median_right": med([t["words_back"] for t in two if t["vector"]["outcome"] == "right"]),
        "n_wrong": sum(t["vector"]["outcome"] == "wrong_person" for t in two),
        "n_right": sum(t["vector"]["outcome"] == "right" for t in two)}
    tb = lambda t: (t["gold_line"] - 2) // 2 + 1                                   # noqa: E731  user turns back
    S["user_lines_back_2plus_persons_vector"] = {str(k): cnt(t["vector"]["outcome"] for t in two if tb(t) == k)
                                                 for k in range(1, 7)}
    # 5. label ambiguity (heuristic)
    S["rows_where_another_person_also_fits_the_turn_cue"] = sum(cues[t["id"]]["n_rivals_fit_cue"] > 0 for t in T)
    S["role_cue_rows_gold_has_that_role"] = [sum(cues[t["id"]]["gold_has_turn_role"] for t in T if cues[t["id"]]["cue"] == "role"),
                                             sum(cues[t["id"]]["cue"] == "role" for t in T)]
    # 6. the backref gap, card by card
    def dec(arm, bar, key):
        c = Counter()
        for t in T:
            x = t[arm]
            if x["outcome"] == "none":
                c["no card"] += 1
            elif x["outcome"] == "wrong_person":
                c["wrong person, saved" if x["saved_hist_" + key] else "wrong person, not saved"] += 1
            elif x["saved_right_hist_" + key]:
                c["right person, saved right"] += 1
            elif x["conf"] < bar:
                c["right person, confidence below bar"] += 1
            else:
                c["right person, over bar, not saved (other field or check)"] += 1
        return dict(sorted(c.items()))
    S["gap_decomposition_hist_rule"] = {"vector_own_0.97": dec("vector", 0.97, "own"), "lora_own_0.995": dec("lora", 0.995, "own"),
                                        "vector_0.995": dec("vector", 0.995, "b995"), "lora_0.97": dec("lora", 0.97, "b97")}
    # 7. wrong person in every family (matched cards, any confidence; gold owner a name)
    rows = C.dev_rows()
    rd = {"vector": {x["id"]: x for x in C.load_jsonl(C.V1 / "run/out/vec_dev_reads.jsonl")},
          "lora": {x["id"]: x for x in C.load_jsonl(C.V1 / "run/out/lora_dev_reads.jsonl")}}
    fam = {}
    for r in rows:
        for arm in ("vector", "lora"):
            read = rd[arm].get(r["id"])
            cards = (read or {}).get("cards") or [] if arm == "vector" else C.lora_cards(read)
            for c, k in C.match_cards(cards, r["cards"]):
                if k is None or r["cards"][k]["owner"] == "me":
                    continue
                f = fam.setdefault(r["family"], {}).setdefault(arm, Counter())
                f["matched"] += 1
                if c["owner"] != "me" and C.norm(c["owner"]) != C.norm(r["cards"][k]["owner"]):
                    f["wrong_person"] += 1
    S["wrong_person_all_families_matched_cards"] = {f: {arm: dict(v) for arm, v in x.items()} for f, x in sorted(fam.items())}
    # 7b. right-owner cards below the vector bar 0.97 by copies of the owner name (definition check against vread2 PASSMARKS)
    S["vector_right_owner_below_0.97_by_copies"] = {
        b: [sum(t["vector"]["conf"] < 0.97 for t in T if t["vector"]["outcome"] == "right" and lo <= t["gold_copies"] <= hi),
            sum(t["vector"]["outcome"] == "right" for t in T if lo <= t["gold_copies"] <= hi)]
        for b, (lo, hi) in (("1", (1, 1)), ("2", (2, 2)), ("3+", (3, 99)))}
    # 8. what the saved dev reads hold (the 7 probabilities are not in them)
    vrows = list(rd["vector"].values())
    S["vector_reads_format"] = {
        "reads": len(vrows), "cards": sum(len(x["cards"]) for x in vrows),
        "card_key_sets": cnt(",".join(sorted(c.keys())) for x in vrows for c in x["cards"]),
        "row_key_sets": cnt(",".join(sorted(x.keys())) for x in vrows),
        "rounds": cnt(x["rounds"] for x in vrows), "min_halt_p": min(x["halt_p"] for x in vrows)}
    lrows = list(rd["lora"].values())
    S["lora_reads_format"] = {"reads": len(lrows), "row_key_sets": cnt(",".join(sorted(x.keys())) for x in lrows)}
    (d / "summary.json").write_text(json.dumps(S, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(S, indent=1))


if __name__ == "__main__":
    main()
