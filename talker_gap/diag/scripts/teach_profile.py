#!/usr/bin/env python3
"""Profile the B1 TEACH set and the four English eval sets, then propose leave-kinds-out splits.

Read-only inputs:
  TEACH      /Users/ben-hannan/Desktop/projects/b1-wt/b1_teach/results/teach_200k.jsonl.gz
  kinds.py   /Users/ben-hannan/Desktop/projects/b1-wt/b1_teach/kinds.py   (parsed with ast, never imported)
  eval JSON  <DIAG>/eval_sets/*.json  (extracted from origin/claude/custom-reader-talker-4x309r, custom_io/english_eval/)
Outputs (diag folder only):
  <DIAG>/teach_stats.json, <DIAG>/split_proposal.json, <DIAG>/practised_slice_ids.txt
Passage = source_text (the shown passage). Sibling rows (id suffix -s / -y) share one passage.
Stdlib only. Run: /usr/bin/python3 -I <this file>
"""
import ast
import collections
import gzip
import hashlib
import json
import math
import os
import re
import statistics

TEACH = "/Users/ben-hannan/Desktop/projects/b1-wt/b1_teach/results/teach_200k.jsonl.gz"
KINDS_PY = "/Users/ben-hannan/Desktop/projects/b1-wt/b1_teach/kinds.py"
DIAG = "/Users/ben-hannan/Desktop/projects/talker-gap-wt/talker_gap/diag"
EVAL_DIR = os.path.join(DIAG, "eval_sets")
EVAL_FILES = ["FRESH-EN-R3.json", "GEN-HELDOUT-R4.json", "NEW-KINDS-R5.json", "NEW-KINDS2-R6.json"]
N_PRACTISED = 6          # kinds.py header: kinds 1-6 are the round-4 practised kinds
N_DEV, N_TEST, N_SLICE = 8, 6, 2000
WORD = re.compile(r"[a-z0-9']+")
WH = {"who", "what", "where", "when", "how", "which", "why"}


def clean(a):
    """Canonical answer with surrounding space and one trailing full stop removed."""
    return (a or "").strip().rstrip(".").strip()


def words(s):
    return WORD.findall((s or "").lower())


def first_word(q):
    w = words(q)
    return w[0] if w else ""


def pct(vals, p):
    s = sorted(vals)
    return s[max(0, math.ceil(p / 100 * len(s)) - 1)]


def lenstats(vals):
    if not vals:
        return None
    return {"mean": round(statistics.fmean(vals), 2), "p50": pct(vals, 50),
            "p90": pct(vals, 90), "max": max(vals)}


def share(a, b):
    return round(a / b, 4) if b else None


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def profile(items):
    """items: dicts with type, answer, source, paraphrase, question."""
    n = len(items)
    yn = [it for it in items if it["type"] == "yes_no"]
    sa = [it for it in items if it["type"] == "short_answer"]
    ans = [clean(it["answer"]) for it in items]
    out = {
        "rows": n,
        "yes_no": len(yn),
        "short_answer": len(sa),
        "other_type": n - len(yn) - len(sa),
        "yes_no_share": share(len(yn), n),
        "answer_words": lenstats([len(a.split()) for a in ans]),
        "answer_chars": lenstats([len(a) for a in ans]),
        "short_answer_words": lenstats([len(clean(it["answer"]).split()) for it in sa]),
        "short_answer_chars": lenstats([len(clean(it["answer"])) for it in sa]),
        "yes_no_answer_counts": dict(collections.Counter(clean(it["answer"]).lower() for it in yn)),
        "distinct_answers_all": len(set(a.lower() for a in ans)),
        "distinct_answers_short": len(set(clean(it["answer"]).lower() for it in sa)),
        "top10_answers": collections.Counter(a.lower() for a in ans).most_common(10),
        "question_first_word_top5": collections.Counter(first_word(it["question"]) for it in items).most_common(5),
        "wh_question_share": share(sum(1 for it in items if first_word(it["question"]) in WH), n),
    }
    keys = ["source_text", "paraphrase", "question", "source_plus_question"]
    exact = {k: 0 for k in keys}
    ci = {k: 0 for k in keys}
    vnames = ["union_source_paraphrase_question", "source_question", "paraphrase_question"]
    nov_rows = {k: 0 for k in vnames}
    nov_frac = {k: [] for k in vnames}
    for it in sa:
        a = clean(it["answer"])
        src, par, q = it["source"], it["paraphrase"], it["question"]
        texts = {"source_text": src, "paraphrase": par, "question": q,
                 "source_plus_question": src + " " + q}
        for k, t in texts.items():
            if a and a in t:
                exact[k] += 1
            if a and a.lower() in t.lower():
                ci[k] += 1
        vocab = {"union_source_paraphrase_question": set(words(src)) | set(words(par)) | set(words(q)),
                 "source_question": set(words(src)) | set(words(q)),
                 "paraphrase_question": set(words(par)) | set(words(q))}
        aw = words(a)
        if aw:
            for k in vnames:
                nov = sum(1 for w in aw if w not in vocab[k])
                if nov:
                    nov_rows[k] += 1
                nov_frac[k].append(nov / len(aw))
    out["short_answer_substring_exact_case_sensitive"] = {k: share(exact[k], len(sa)) for k in keys}
    out["short_answer_substring_case_insensitive"] = {k: share(ci[k], len(sa)) for k in keys}
    out["short_answer_novel_vs_prompt"] = {
        k: {"row_share": share(nov_rows[k], len(sa)),
            "token_frac_mean": round(statistics.fmean(nov_frac[k]), 4) if nov_frac[k] else None}
        for k in vnames}
    return out


def load_teach():
    rows = []
    with gzip.open(TEACH, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            rows.append({"id": r["id"], "kind": r["kind"], "type": r["type"],
                         "answer": r["canonical_answer"] or "", "source": r["source_text"],
                         "paraphrase": r["paraphrase"], "question": r["question"]})
    return rows


def load_eval(fn):
    with open(os.path.join(EVAL_DIR, fn), encoding="utf-8") as f:
        j = json.load(f)
    items = []
    for ex in j["examples"]:
        for qi, q in enumerate(ex["questions"]):
            items.append({"id": "%s-q%d" % (ex["id"], qi), "kind": ex["family"], "type": q["type"],
                          "answer": q["canonical_answer"] or "", "source": ex["source_text"],
                          "paraphrase": ex["paraphrase"], "question": q["question"]})
    return items


def kinds_from_py():
    tree = ast.parse(open(KINDS_PY, encoding="utf-8").read())
    got = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id in ("KINDS", "SPARES"):
            try:
                val = ast.literal_eval(node.value)
                got[node.targets[0].id] = [t[0] if isinstance(t, (tuple, list)) else t for t in val]
            except Exception as e:  # keep going; report what failed
                got[node.targets[0].id] = "unparsed: %s" % type(e).__name__
    return got


def main():
    teach = load_teach()
    ids = [r["id"] for r in teach]
    kpy = kinds_from_py()
    kinds_list = kpy["KINDS"] if isinstance(kpy.get("KINDS"), list) else []
    spares = kpy["SPARES"] if isinstance(kpy.get("SPARES"), list) else kpy.get("SPARES")
    by_kind = collections.defaultdict(list)
    for r in teach:
        by_kind[r["kind"]].append(r)
    teach_kinds = sorted(by_kind)
    evals = {fn: load_eval(fn) for fn in EVAL_FILES}
    eval_fams = {fn: sorted(set(it["kind"] for it in items)) for fn, items in evals.items()}
    all_eval_fams = sorted(set(f for fams in eval_fams.values() for f in fams))
    teach_src = set(r["source"] for r in teach)

    # passage / sibling structure
    by_src = collections.defaultdict(list)
    for r in teach:
        by_src[r["source"]].append(r)
    pair_key = collections.defaultdict(list)
    for r in teach:
        pair_key[re.sub(r"-[A-Za-z]+$", "", r["id"])].append(r)
    passage_info = {
        "rows": len(teach),
        "distinct_source_text": len(by_src),
        "source_texts_with_2plus_rows": sum(1 for v in by_src.values() if len(v) > 1),
        "rows_in_multi_row_passages": sum(len(v) for v in by_src.values() if len(v) > 1),
        "source_texts_under_2plus_kinds": sum(1 for v in by_src.values() if len(set(x["kind"] for x in v)) > 1),
        "id_pair_keys_(id_minus_s_or_y)": len(pair_key),
        "id_pair_keys_with_2_rows": sum(1 for v in pair_key.values() if len(v) == 2),
        "id_pair_keys_mapping_to_2plus_passages": sum(1 for v in pair_key.values() if len(set(x["source"] for x in v)) > 1),
    }

    stats = {
        "teach": {"file": TEACH, "rows": len(teach), "unique_ids": len(set(ids)),
                  "distinct_kinds": len(teach_kinds), "passages": passage_info,
                  "kinds_py_check": {"KINDS_n": len(kinds_list), "SPARES": spares,
                                     "teach_kinds_not_in_KINDS": [k for k in teach_kinds if k not in kinds_list],
                                     "KINDS_not_in_teach": [k for k in kinds_list if k not in by_kind]},
                  "overall": profile(teach),
                  "by_kind": {k: profile(by_kind[k]) for k in teach_kinds}},
        "eval": {},
        "kind_overlap_name_only": {
            "eval_families_in_teach": [f for f in all_eval_fams if f in by_kind],
            "eval_families_not_in_teach": [f for f in all_eval_fams if f not in by_kind],
            "eval_family_sets": eval_fams,
        },
    }
    for fn, items in evals.items():
        p = profile(items)
        p["items"] = len(items)
        p["scored_rows_both_passages"] = 2 * len(items)
        p["family_teach_rows"] = {f: len(by_kind.get(f, [])) for f in eval_fams[fn]}
        p["item_source_text_exact_in_teach"] = sum(1 for it in items if it["source"] in teach_src)
        stats["eval"][fn] = p
    stats["eval_all_four_sets"] = profile([it for items in evals.values() for it in items])

    # ---------------- splits (kind level, then passage level) ----------------
    yn_all = stats["teach"]["overall"]["yes_no_share"]
    practised = kinds_list[:N_PRACTISED]
    excluded = set(practised) | set(all_eval_fams)
    rows_n = {k: len(by_kind[k]) for k in teach_kinds}
    rows_y = {k: sum(1 for r in by_kind[k] if r["type"] == "yes_no") for k in teach_kinds}
    cands = sorted([k for k in kinds_list if k in by_kind and k not in excluded], key=sha)

    def pick(pool, k):
        """Greedy: add the kind whose pooled yes/no share is closest to the TEACH share; ties by sha order."""
        chosen, pool = [], list(pool)
        for _ in range(k):
            best = None
            for idx, c in enumerate(pool):
                n = sum(rows_n[x] for x in chosen) + rows_n[c]
                y = sum(rows_y[x] for x in chosen) + rows_y[c]
                key = (abs(y / n - yn_all), idx)
                if best is None or key < best[0]:
                    best = (key, c)
            chosen.append(best[1])
            pool.remove(best[1])
        return chosen, pool

    dev, rest = pick(cands, N_DEV)
    test, _ = pick(rest, N_TEST)
    dev_set, test_set = set(dev), set(test)
    dt_rows = [r for r in teach if r["kind"] in dev_set or r["kind"] in test_set]
    dt_src = set(r["source"] for r in dt_rows)
    train_set = set(k for k in teach_kinds if k not in dev_set and k not in test_set)
    train_rows_all = [r for r in teach if r["kind"] in train_set]
    train_src = set(r["source"] for r in train_rows_all)

    # DIAGNOSTIC of the first (id-hash) slice rule, kept to document why it was replaced
    naive_ids = set(r["id"] for r in sorted(train_rows_all, key=lambda r: (sha(r["id"]), r["id"]))[:N_SLICE])
    naive_other_src = set(r["source"] for r in train_rows_all if r["id"] not in naive_ids)
    naive_leak = sum(1 for r in train_rows_all if r["id"] in naive_ids and r["source"] in naive_other_src)

    # passage guard: a train row whose passage also appears in a dev/test row is dropped from training
    guard_rows = [r for r in train_rows_all if r["source"] in dt_src]
    dt_rows_passage_in_train = sum(1 for r in dt_rows if r["source"] in train_src)
    pool = [r for r in train_rows_all if r["source"] not in dt_src]

    # practised slice: whole passages, in ascending sha256(passage) order, until >= N_SLICE rows
    groups = collections.defaultdict(list)
    for r in pool:
        groups[r["source"]].append(r)
    slice_src, acc = [], 0
    for g in sorted(groups, key=sha):
        if acc >= N_SLICE:
            break
        slice_src.append(g)
        acc += len(groups[g])
    slice_rows = [r for g in slice_src for r in groups[g]]
    slice_ids = [r["id"] for r in slice_rows]
    slice_set = set(slice_ids)
    final_train = [r for r in pool if r["id"] not in slice_set]
    final_train_src = set(r["source"] for r in final_train)
    verify = {
        "slice_rows_whose_passage_is_in_final_train": sum(1 for r in slice_rows if r["source"] in final_train_src),
        "dev_test_rows_whose_passage_is_in_final_train": sum(1 for r in dt_rows if r["source"] in final_train_src),
        "dev_test_rows_whose_passage_is_in_slice": sum(1 for r in dt_rows if r["source"] in set(slice_src)),
        "eval_item_source_text_exact_in_teach": sum(stats["eval"][fn]["item_source_text_exact_in_teach"] for fn in EVAL_FILES),
    }

    def split_of(r):
        if r["kind"] in dev_set:
            return "dev"
        if r["kind"] in test_set:
            return "test"
        if r["source"] in dt_src:
            return "dropped_passage_overlap_with_dev_test"
        if r["id"] in slice_set:
            return "practised_slice"
        return "train"

    split_rows = collections.defaultdict(list)
    for r in teach:
        split_rows[split_of(r)].append(r)
    per_split = {}
    for s in ["train", "practised_slice", "dev", "test", "dropped_passage_overlap_with_dev_test"]:
        items = split_rows[s]
        per_split[s] = {
            "rows": len(items),
            "yes_no_share": share(sum(1 for r in items if r["type"] == "yes_no"), len(items)),
            "wh_question_share": share(sum(1 for r in items if first_word(r["question"]) in WH), len(items)),
            "distinct_kinds": len(set(r["kind"] for r in items)),
            "distinct_passages": len(set(r["source"] for r in items)),
            "answer_words_mean": lenstats([len(clean(r["answer"]).split()) for r in items])["mean"] if items else None,
        }
    kind_table = []
    for c in sorted([k for k in teach_kinds], key=lambda k: (k not in cands, sha(k))):
        role = "dev" if c in dev_set else "test" if c in test_set else "train"
        note = []
        if c in practised:
            note.append("practised (kinds.py 1-6 = FRESH-EN-R3 family)")
        if c in all_eval_fams:
            note.append("eval family name")
        kind_table.append({"kind": c, "role": role, "rows": rows_n[c],
                           "yes_no_share": share(rows_y[c], rows_n[c]),
                           "wh_question_share": share(sum(1 for r in by_kind[c] if first_word(r["question"]) in WH), rows_n[c]),
                           "note": "; ".join(note)})

    # alternative (same DEV/TEST kinds): thin only the yes/no rows of DEV+TEST so their yes/no share
    # matches the four eval sets, keeping every short-answer row.
    eval_yn = stats["eval_all_four_sets"]["yes_no_share"]
    dt_sa = sum(1 for r in dt_rows if r["type"] == "short_answer")
    dt_yn = sorted([r for r in dt_rows if r["type"] == "yes_no"], key=lambda r: (sha(r["id"]), r["id"]))
    n_keep = round(eval_yn / (1 - eval_yn) * dt_sa)
    alt_kept = [r["id"] for r in dt_yn[:n_keep]]

    proposal = {
        "target_yes_no_share_teach": yn_all,
        "dev_kinds": dev,
        "test_kinds": test,
        "practised_kinds_never_dev_or_test": practised,
        "eval_family_names_never_dev_or_test": all_eval_fams,
        "rule_kind_level": ("A row is split=dev if its kind is in dev_kinds, split=test if its kind is in test_kinds. "
                            "Kinds are picked from the candidates in sha256(kind name) order by a deterministic greedy step "
                            "that keeps the pooled yes/no share closest to the TEACH share."),
        "rule_passage_guard": ("Any train-kind row whose source_text (the shown passage) also appears in a dev or test row "
                               "is dropped from training (split=dropped_passage_overlap_with_dev_test)."),
        "rule_practised_slice": ("Among the remaining train rows, group by source_text (the passage; covers -s/-y sibling pairs "
                                 "and repeated passages). Take whole passage groups in ascending sha256(source_text) order until at "
                                 "least %d rows; all rows of those passages are split=practised_slice, so no passage is split "
                                 "between slice and train. Remaining rows are split=train." % N_SLICE),
        "passage_overlap_before_guard": {
            "dev_test_distinct_passages": len(dt_src),
            "dev_test_rows_whose_passage_occurs_in_a_train_kind_row": dt_rows_passage_in_train,
            "train_kind_rows_dropped_by_guard": len(guard_rows),
        },
        "diagnostic_first_id_hash_slice": {
            "rule": "first %d train rows by sha256(id); REPLACED, because siblings split passages" % N_SLICE,
            "slice_rows_whose_passage_also_in_other_train_rows": naive_leak,
        },
        "per_split": per_split,
        "verification_expected_zero": verify,
        "practised_slice": {"n_rows": len(slice_rows), "n_passages": len(slice_src),
                            "ids_file": os.path.join(DIAG, "practised_slice_ids.txt"),
                            "ids_sha256": sha("\n".join(slice_ids))},
        "train_kinds_n": len(train_set),
        "candidate_kinds_in_sha_order": kind_table,
        "dev_test_eval_mix_alternative": {
            "use": "optional; same dev/test kinds, but DEV and TEST yes/no rows are thinned to match the eval sets",
            "target_yes_no_share_eval_all_four": eval_yn,
            "dev_test_rows_before": len(dt_rows),
            "dev_test_short_rows": dt_sa,
            "dev_test_yes_no_rows_before": len(dt_yn),
            "dev_test_yes_no_rows_kept": n_keep,
            "dev_test_rows_after": dt_sa + n_keep,
            "rule": "keep all short_answer rows; keep the first n_keep yes/no rows of DEV+TEST ordered by (sha256(id), id)",
            "kept_yes_no_ids_sha256": sha("\n".join(sorted(alt_kept))),
        },
    }
    with open(os.path.join(DIAG, "practised_slice_ids.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(slice_ids) + "\n")
    with open(os.path.join(DIAG, "teach_stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=1)
    with open(os.path.join(DIAG, "split_proposal.json"), "w", encoding="utf-8") as f:
        json.dump(proposal, f, indent=1)

    # ---------------- console summary (kept short) ----------------
    o = stats["teach"]["overall"]
    print("TEACH rows=%d unique_ids=%d kinds=%d passages=%d yes_no=%d short=%d share_yn=%s" % (
        len(teach), len(set(ids)), len(teach_kinds), passage_info["distinct_source_text"],
        o["yes_no"], o["short_answer"], o["yes_no_share"]))
    print("passage info:", json.dumps(passage_info))
    print("TEACH kinds_py:", json.dumps(stats["teach"]["kinds_py_check"])[:300])
    print("eval families in TEACH (name only):", stats["kind_overlap_name_only"]["eval_families_in_teach"])
    print("DEV kinds:", dev)
    print("TEST kinds:", test)
    print("passage overlap before guard:", json.dumps(proposal["passage_overlap_before_guard"]))
    print("naive id-slice leak:", naive_leak, "of", N_SLICE)
    print("per_split:", json.dumps(per_split))
    print("verify:", json.dumps(verify))
    print("slice rows:", len(slice_rows), "passages:", len(slice_src), "sha:", proposal["practised_slice"]["ids_sha256"][:16])
    for fn in EVAL_FILES:
        p = stats["eval"][fn]
        print("EVAL %s items=%d yn=%s sub_par_ci=%s novel_par_q=%s" % (
            fn, p["items"], p["yes_no_share"], p["short_answer_substring_case_insensitive"]["paraphrase"],
            p["short_answer_novel_vs_prompt"]["paraphrase_question"]["row_share"]))


if __name__ == "__main__":
    main()
