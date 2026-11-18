#!/usr/bin/env /usr/bin/python3
"""Error taxonomy for the PR #37 copy talker (copytalk), its nocore lesion and the allptr control.

Run:  /usr/bin/python3 -I <diag>/scripts/ct_taxonomy.py [diag_dir]
Inputs (extracted with git show from origin/claude/project-thread-utxkpw, reasoner_ptr/real/english/):
  <diag>/copytalk_rows/*-rows.json          results_ct/box*/out/<arm>-gen-ct-seed<k>[-<split>]-rows.json
  <diag>/copytalk_rows/eval/*.json          FRESH-EN-R3, GEN-HELDOUT-R4, NEW-KINDS-R5, NEW-KINDS2-R6, training bank
Rows carry no prompt text, so prompts are rebuilt from the eval sets by id, the same way run_english.py rows_of() does:
  id = f"{example id}-{key}-q{qi}", prompt = example[key] + " " + question.
Outputs: <diag>/out/ct_taxonomy.json, <diag>/out/ct_taxonomy_examples.json; compact tables on stdout. Stdlib only.

Normalisation is copied from run_english.py norm() (lines 64-66): NFC, lower, curly to straight apostrophes,
collapse whitespace, strip trailing [.!?,;:]. Correctness is recomputed and checked against the stored 'ok'.

Cause order (one cause per wrong row, first match wins):
  yes_no gold:   c_yesno_flip (pred is the opposite yes/no) | c_yesno_other (span, empty or class)
  nonspan gold:  d_nonspan_* (answer not copyable from the prompt, so copytalk can only win via its closed list)
  span gold:     e_empty | c_gate_or_decode (pred is yes/no or not a character substring of the prompt)
                 | b_boundary (earliest char interval of pred overlaps earliest interval of gold: right place, wrong edges)
                 | a_wrong_location (pred is a prompt substring, no overlap with gold)
"""
import json, os, re, sys, unicodedata
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DIAG = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(HERE)
ROWS = os.path.join(DIAG, "copytalk_rows")
EVAL = os.path.join(ROWS, "eval")
OUT = os.path.join(DIAG, "out")

# split -> (row-file suffix, eval file, [(panel, example key)]); mapping from run_english.py main() and analyze_ct.py
SPLITS = {
    "none":    ("",        "FRESH-EN-R3.json",                    [("fresh_source", "source_text"), ("fresh_paraphrase", "paraphrase")]),
    "heldout": ("heldout", "GEN-HELDOUT-R4.json",                 [("held_source", "source_text"), ("held_paraphrase", "paraphrase")]),
    "extra":   ("extra",   "NEW-KINDS-R5.json",                   [("new_source", "source_text"), ("new_paraphrase", "paraphrase")]),
    "extra2":  ("extra2",  "NEW-KINDS2-R6.json",                  [("new2_source", "source_text"), ("new2_paraphrase", "paraphrase")]),
    "train":   ("train",   "english_training_candidates_v3.json", [("train_source", "source_text"), ("train_paraphrase", "paraphrase")]),
}
GROUPS = {"extra": ["extra"], "extra2": ["extra2"], "unseen": ["extra", "extra2"],
          "none": ["none"], "heldout": ["heldout"], "train": ["train"]}
ARMS = ["copytalk", "copytalk_nocore", "allptr"]
SEEDS = [0, 1, 2, 3, 4, 5]
CAUSES = ["correct", "c_yesno_flip", "c_yesno_other", "c_gate_or_decode", "e_empty",
          "b_boundary", "a_wrong_location", "x_gold_not_located",
          "d_nonspan_pred_yesno", "d_nonspan_empty", "d_nonspan_pred_in_prompt", "d_nonspan_pred_not_in_prompt"]
WORD_CATS = ["empty", "pred_strict_sub_of_gold", "gold_strict_sub_of_pred", "partial_word_overlap",
             "no_overlap_pred_words_in_prompt", "no_overlap_pred_has_words_not_in_prompt"]
# Reported reproduction targets from RESULTS-CT.md (mean of 6 seeds, exact %); allptr is one seed (seed 0 rerun).
EXPECTED = {
    ("copytalk", "unseen"): 13.6, ("copytalk", "extra"): 13.8, ("copytalk", "extra2"): 13.5,
    ("copytalk", "heldout"): 97.4, ("copytalk", "none"): 58.7,
    ("copytalk_nocore", "unseen"): 12.9, ("copytalk_nocore", "extra"): 14.3, ("copytalk_nocore", "extra2"): 11.5,
    ("copytalk_nocore", "heldout"): 41.6, ("copytalk_nocore", "none"): 24.5,
    ("allptr", "unseen"): 73.2,
}

CURLY = {"’": "'", "‘": "'"}  # verified: run_english.py lines 64-66 contain U+2019 and U+2018


def canon(s):
    s = unicodedata.normalize("NFC", s).lower()
    for a, b in CURLY.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s.strip())


def norm(s):
    return re.sub(r"[.!?,;:]+$", "", canon(s)).strip()


def words(s):
    return re.findall(r"\w+", s)


def occurrences(hay, needle):
    out = []
    if not needle:
        return out
    i = hay.find(needle)
    while i != -1:
        out.append(i)
        i = hay.find(needle, i + 1)
    return out


def overlap(a, la, b, lb):
    return a < b + lb and b < a + la


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_lookup(split):
    suffix, fname, panels = SPLITS[split]
    data = read_json(os.path.join(EVAL, fname))
    examples = data["examples"] if isinstance(data, dict) else data
    lk = {}
    for e in examples:
        for panel, key in panels:
            for qi, q in enumerate(e["questions"]):
                rid = f"{e['id']}-{key}-q{qi}"
                assert rid not in lk, rid
                accepted_raw = [q["canonical_answer"]] + list(q["accepted_answers"])
                lk[rid] = {"panel": panel, "passage": e[key], "prompt": e[key] + " " + q["question"],
                           "canon": q["canonical_answer"], "accepted_raw": accepted_raw,
                           "acc": [norm(a) for a in accepted_raw]}
    return lk


def row_path(arm, seed, split):
    suffix = SPLITS[split][0]
    mid = f"-{suffix}" if suffix else ""
    return os.path.join(ROWS, f"{arm}-gen-ct-seed{seed}{mid}-rows.json")


def word_cat(p, g, prompt_c):
    if not p:
        return "empty"
    if p != g and p in g:
        return "pred_strict_sub_of_gold"
    if g != p and g in p:
        return "gold_strict_sub_of_pred"
    pw, gw = set(words(p)), set(words(g))
    if pw & gw:
        return "partial_word_overlap"
    if pw and pw <= set(words(prompt_c)):
        return "no_overlap_pred_words_in_prompt"
    return "no_overlap_pred_has_words_not_in_prompt"


def classify(row, info):
    prompt_c = canon(info["prompt"])
    qstart = len(canon(info["passage"])) + 1  # char offset where the question begins in prompt_c
    p = norm(row["pred"])
    g = norm(row["answer"])
    atype = row["atype"]
    ok = p in info["acc"]
    occ_p = occurrences(prompt_c, p) if p else []
    gold_str, occ_g = None, []
    if atype != "yes_no":
        for c in [g] + [norm(a) for a in info["accepted_raw"]]:
            occ = occurrences(prompt_c, c) if c else []
            if occ:
                gold_str, occ_g = c, occ
                break
    f = {"ok": ok, "ok_stored": row["ok"], "answer_match": row["answer"] == info["canon"],
         "p": p, "g": g, "atype": atype, "pred_in_prompt": bool(occ_p),
         "gold_located": gold_str is not None,
         "pred_pos": occ_p[0] if occ_p else None, "gold_pos": occ_g[0] if occ_g else None,
         "overlap_earliest": bool(occ_p and occ_g and overlap(occ_p[0], len(p), occ_g[0], len(gold_str))),
         "overlap_any": bool(gold_str) and any(overlap(x, len(p), y, len(gold_str)) for x in occ_p for y in occ_g),
         "pred_in_question": bool(occ_p) and occ_p[0] >= qstart}
    if ok:
        cause = "correct"
    elif atype == "yes_no":
        cause = "c_yesno_flip" if p in ("yes", "no") else "c_yesno_other"
    elif atype == "nonspan":
        if p in ("yes", "no"):
            cause = "d_nonspan_pred_yesno"
        elif not p:
            cause = "d_nonspan_empty"
        elif occ_p:
            cause = "d_nonspan_pred_in_prompt"
        else:
            cause = "d_nonspan_pred_not_in_prompt"
    elif not p:
        cause = "e_empty"
    elif p in ("yes", "no") or not occ_p:
        cause = "c_gate_or_decode"
    elif gold_str is None:
        cause = "x_gold_not_located"
    elif f["overlap_earliest"]:
        cause = "b_boundary"
    else:
        cause = "a_wrong_location"
    f["cause"] = cause
    f["gold_n_occ"] = len(occ_g)
    f["pred_n_occ"] = len(occ_p)
    f["b_sub"] = None
    if cause == "b_boundary":
        f["b_sub"] = "pred_longer" if gold_str in p else "pred_shorter" if p in gold_str else "partial"
    f["gate_sub"] = None
    if cause == "c_gate_or_decode":
        f["gate_sub"] = "yes_no_class" if p in ("yes", "no") else "off_prompt_class"
    f["offprompt_pick"] = bool(p) and p not in ("yes", "no") and not occ_p
    f["word_cat"] = word_cat(p, g, prompt_c) if (not ok and atype in ("span1", "spanN")) else None
    return f


def group_rows(results, arm, group):
    splits = GROUPS[group]
    return [r for r in results if r["arm"] == arm and r["split"] in splits]


def seed_pcts(results, arm, group):
    out = {}
    for seed in SEEDS:
        rs = [r for r in group_rows(results, arm, group) if r["seed"] == seed]
        if rs:
            out[seed] = 100.0 * sum(r["ok"] for r in rs) / len(rs)
    return out


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def pct(a, b):
    return 100.0 * a / b if b else float("nan")


def agreement(results, group):
    ct = {(r["seed"], r["id"]): r for r in group_rows(results, "copytalk", group)}
    nc = {(r["seed"], r["id"]): r for r in group_rows(results, "copytalk_nocore", group)}
    keys = [k for k in ct if k in nc]
    n = len(keys)
    both = sum(ct[k]["ok"] and nc[k]["ok"] for k in keys)
    ct_only = sum(ct[k]["ok"] and not nc[k]["ok"] for k in keys)
    nc_only = sum(nc[k]["ok"] and not ct[k]["ok"] for k in keys)
    neither = sum(not ct[k]["ok"] and not nc[k]["ok"] for k in keys)
    same_pred = sum(ct[k]["p"] == nc[k]["p"] for k in keys)
    same_pos = sum(ct[k]["pred_pos"] is not None and ct[k]["pred_pos"] == nc[k]["pred_pos"] for k in keys)
    print(f"{group:7s} paired rows={n}: both correct={pct(both, n):.1f} copytalk-only={pct(ct_only, n):.1f} "
          f"nocore-only={pct(nc_only, n):.1f} both wrong={pct(neither, n):.1f} | same normalised pred={pct(same_pred, n):.1f} "
          f"same earliest prompt position={pct(same_pos, n):.1f}")


def mechanism_report(results):
    print("\n## Mechanism cuts: copytalk unseen kinds (wrong rows)")
    rs = group_rows(results, "copytalk", "unseen")
    bs = [r for r in rs if r["cause"] == "b_boundary"]
    print("b_boundary rows by edge type: " + " ".join(f"{k}={v}" for k, v in sorted(Counter(r["b_sub"] for r in bs).items())))
    cg = [r for r in rs if r["cause"] == "c_gate_or_decode"]
    print("c_gate_or_decode rows by gate class: " + " ".join(f"{k}={v}" for k, v in sorted(Counter(r["gate_sub"] for r in cg).items())))
    al = [r for r in rs if r["cause"] == "a_wrong_location"]
    if al:
        print(f"a_wrong_location: n={len(al)} pred_in_question={pct(sum(r['pred_in_question'] for r in al), len(al)):.1f}% "
              f"gold_occurs_once_in_prompt={pct(sum(r['gold_n_occ'] == 1 for r in al), len(al)):.1f}% "
              f"would_be_b_if_any_occurrence={pct(sum(r['overlap_any'] for r in al), len(al)):.1f}%")
    for gold in ("yes", "no"):
        ys = [r for r in rs if r["atype"] == "yes_no" and r["g"] == gold]
        print(f"gold {gold}: n={len(ys)} pred yes={sum(r['p']=='yes' for r in ys)} pred no={sum(r['p']=='no' for r in ys)} "
              f"other={sum(r['p'] not in ('yes','no') for r in ys)}")
    print("\n## copytalk vs copytalk_nocore row-level agreement (same seed and row id)")
    for group in ["unseen", "heldout", "none"]:
        agreement(results, group)


def main():
    os.makedirs(OUT, exist_ok=True)
    lookups = {s: load_lookup(s) for s in SPLITS}
    problems = Counter()
    results, seen_files = [], []
    for arm in ARMS:
        for split in SPLITS:
            for seed in SEEDS:
                path = row_path(arm, seed, split)
                if not os.path.exists(path):
                    continue
                seen_files.append(os.path.basename(path))
                rows = read_json(path)
                for row in rows:
                    info = lookups[split].get(row["id"])
                    if info is None:
                        problems["id_not_in_eval_set"] += 1
                        continue
                    if info["panel"] != row["panel"]:
                        problems["panel_mismatch"] += 1
                    f = classify(row, info)
                    if not f["answer_match"]:
                        problems["answer_mismatch"] += 1
                    if f["ok"] != f["ok_stored"]:
                        problems["ok_mismatch"] += 1
                    if f["atype"] in ("span1", "spanN") and not f["gold_located"]:
                        problems["span_gold_not_in_prompt"] += 1
                    results.append({"arm": arm, "split": split, "seed": seed, "id": row["id"],
                                    "gold": row["answer"], "pred": row["pred"], "panel": row["panel"], **f})

    # ---- reproduction check against RESULTS-CT.md
    print(f"files read: {len(seen_files)}  rows: {len(results)}  problems: {dict(problems) or 'none'}")
    print("\n## Reproduction (mean over seeds of per-seed %; allptr = seed 0 only)")
    print("arm | group | expected | got | seeds")
    for (arm, group), exp in EXPECTED.items():
        got_map = seed_pcts(results, arm, group)
        if not got_map:
            print(f"{arm} | {group} | {exp} | - | 0")
            continue
        got = mean(got_map.values()) if arm != "allptr" else got_map.get(0)
        print(f"{arm} | {group} | {exp} | {got:.1f} | {len(got_map)}")

    # ---- correctness and causes, pooled over seeds
    print("\n## Pooled over seeds: n, correct%, then wrong-row causes as % of all rows (wrong causes sum to 100-correct%)")
    causes_out = {}
    for group in GROUPS:
        for arm in ARMS:
            rs = group_rows(results, arm, group)
            if not rs:
                continue
            n = len(rs)
            seeds = sorted({r["seed"] for r in rs})
            c = Counter(r["cause"] for r in rs)
            causes_out[f"{arm}|{group}"] = {"n": n, "seeds": seeds, "counts": dict(c)}
            cells = " ".join(f"{k}={pct(c[k], n):.1f}" for k in CAUSES[1:] if c[k])
            print(f"{group:7s} {arm:16s} n={n:5d} seeds={seeds} correct={pct(c['correct'], n):.1f} | {cells}")

    # ---- letter grouping of wrong rows (a/b/c/d/e/x), share of wrong rows
    print("\n## Wrong rows by cause letter, share of wrong rows (%)")
    for group in ["unseen", "none", "heldout", "train"]:
        for arm in ARMS:
            rs = [r for r in group_rows(results, arm, group) if not r["ok"]]
            if not rs:
                continue
            c = Counter(r["cause"][0] for r in rs)
            print(f"{group:7s} {arm:16s} wrong={len(rs):5d} " + " ".join(f"{k}={pct(c[k], len(rs)):.1f}" for k in sorted(c)))

    # ---- answer type (atype from run_english.py) accuracy
    print("\n## Accuracy by stored atype (correct% / n)")
    for group in ["unseen", "none", "heldout"]:
        for arm in ARMS:
            rs = group_rows(results, arm, group)
            parts = []
            for at in ["yes_no", "span1", "spanN", "nonspan"]:
                sub = [r for r in rs if r["atype"] == at]
                if sub:
                    parts.append(f"{at}={pct(sum(r['ok'] for r in sub), len(sub)):.1f}/{len(sub)}")
            if parts:
                print(f"{group:7s} {arm:16s} " + "  ".join(parts))

    # ---- yes/no decisions
    print("\n## yes/no gold: predicted yes / no / other (copytalk and nocore)")
    for group in ["unseen", "none", "heldout"]:
        for arm in ARMS:
            rs = [r for r in group_rows(results, arm, group) if r["atype"] == "yes_no"]
            if not rs:
                continue
            gy = sum(r["g"] == "yes" for r in rs); gn = sum(r["g"] == "no" for r in rs)
            py = sum(r["p"] == "yes" for r in rs); pn = sum(r["p"] == "no" for r in rs)
            print(f"{group:7s} {arm:16s} n={len(rs)} gold yes={gy} no={gn} | pred yes={py} no={pn} other={len(rs)-py-pn}"
                  f" | correct={pct(sum(r['ok'] for r in rs), len(rs)):.1f}")

    # ---- word-level categories (task list) for wrong span rows
    print("\n## Wrong span rows (span1/spanN) by word-level category, % of those rows (char-level substring checks)")
    for group in ["unseen", "none", "heldout"]:
        for arm in ARMS:
            rs = [r for r in group_rows(results, arm, group) if r["word_cat"]]
            if not rs:
                continue
            c = Counter(r["word_cat"] for r in rs)
            print(f"{group:7s} {arm:16s} n={len(rs):5d} " + " ".join(f"{k}={pct(c[k], len(rs)):.1f}" for k in WORD_CATS if c[k]))

    # ---- per-seed copytalk and nocore on unseen kinds
    print("\n## Per-seed correct% on unseen kinds (extra + extra2 pooled)")
    for arm in ARMS:
        m = seed_pcts(results, arm, "unseen")
        print(f"{arm:16s} " + " ".join(f"s{k}={v:.1f}" for k, v in sorted(m.items())))

    # ---- off-prompt picks (closed list usage proxy) and examples
    print("\n## Off-prompt, non-yes/no predictions (closed-list picks; proxy) per arm, unseen | none")
    for arm in ARMS:
        a = group_rows(results, arm, "unseen"); b = group_rows(results, arm, "none")
        print(f"{arm:16s} unseen={sum(r['offprompt_pick'] for r in a)}/{len(a)}  none={sum(r['offprompt_pick'] for r in b)}/{len(b)}")

    mechanism_report(results)
    examples = {}
    for r in group_rows(results, "copytalk", "unseen"):
        if not r["ok"]:
            examples.setdefault(r["cause"], [])
            if len(examples[r["cause"]]) < 8:
                examples[r["cause"]].append({k: r[k] for k in ("id", "seed", "gold", "pred", "atype", "pred_in_question", "overlap_any", "panel")})
    print("\n## Example copytalk unseen errors (first 3 per cause)")
    for cause, exs in sorted(examples.items()):
        for ex in exs[:3]:
            print(f"{cause:26s} seed{ex['seed']} gold={ex['gold']!r} pred={ex['pred']!r} atype={ex['atype']} id={ex['id']}")

    with open(os.path.join(OUT, "ct_taxonomy.json"), "w", encoding="utf-8") as fh:
        json.dump({"problems": dict(problems), "files": seen_files, "causes": causes_out}, fh, indent=1)
    with open(os.path.join(OUT, "ct_taxonomy_examples.json"), "w", encoding="utf-8") as fh:
        json.dump(examples, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(OUT, "ct_taxonomy_rows.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False)


if __name__ == "__main__":
    main()
