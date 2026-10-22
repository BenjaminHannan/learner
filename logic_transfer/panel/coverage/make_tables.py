"""Compile tables.txt from the json outputs (all numbers in findings.md come from here)."""
import json, glob, os
OUT = os.path.dirname(os.path.abspath(__file__))
L = lambda n: json.load(open(f"{OUT}/{n}.json"))
cov, pairs, roles, fam, lad, chi, leak, aud = L("coverage"), L("pairs"), L("roles"), L("family_compare"), L("ladder"), L("shortcuts_chi"), L("leak_probe"), L("audit_eval")
lines = []
P = lines.append
mean = lambda h: sum(float(k) * v for k, v in h.items()) / sum(h.values())
files = ["logic_train", "placebo_train", "logic_dev", "logic_gate", "logic_test_sampler", "logic_test_deeper", "placebo_dev", "placebo_test_wording"]
P("T1 COVERAGE  (means; unseen = share of rows with >=1 template id absent from train)")
P("%-21s %6s %-9s %-8s %6s %5s %5s %5s %5s %5s %5s %5s" % ("file", "n", "sampler", "tset", "unseen", "nrul", "nfac", "ndis", "nsent", "chars", "p10", "p90"))
for f in files:
    c = cov[f]
    P("%-21s %6d %-9s %-8s %6s %5.2f %5.2f %5.2f %5.2f %5.1f %5d %5d" % (f, c["n"], list(c["sampler"])[0][:9], list(c["template_set"])[0], c.get("novelty_vs_train", {}).get("rows_any_tid_unseen_pct", "-"),
          mean(c["n_rules"]), mean(c["n_facts"]), mean(c["n_distractors"]), mean(c["n_sentences"]), c["chars"]["mean"], c["chars"]["p10"], c["chars"]["p90"]))
P("")
P("depth x label counts")
for f in files:
    P("%-21s %s" % (f, cov[f]["depth_label"]))
P("")
P("sentence-role share of sentences (%), and per-kind unseen % in eval")
for f in files:
    r = cov[f]["sentence_roles"]; t = sum(r.values())
    P("%-21s %s" % (f, " ".join("%s=%.1f" % (k, 100 * v / t) for k, v in r.items())))
P("")
P("T2a PAIRS (entity,predicate), eval vs matching train file")
P("train: logic ctx pairs distinct %d (repeat mean %.2f, seen-once %.1f%%), placebo %d (%.2f, %.1f%%); 149 entities, 1407 predicates; possible pairs %d" % (
    pairs["train"]["logic_train"]["ctx_pairs"]["distinct"], pairs["train"]["logic_train"]["ctx_pairs"]["mean_repeat"], 100 * pairs["train"]["logic_train"]["ctx_pairs"]["share_seen_once"],
    pairs["train"]["placebo_train"]["ctx_pairs"]["distinct"], pairs["train"]["placebo_train"]["ctx_pairs"]["mean_repeat"], 100 * pairs["train"]["placebo_train"]["ctx_pairs"]["share_seen_once"], pairs["lexicon"]["possible_entity_pred_pairs"]))
P("%-21s %5s %9s %9s %9s %7s %6s" % ("eval file", "ctxP", "ctx_unseen", "qry_unseen", "qry_unseen_any", "pred_un", "memchk"))
for f, v in pairs["eval_vs_train"].items():
    P("%-21s %5d %9.1f%% %9.1f%% %9.1f%% %7d %5.1f%%" % (f, v["ctx_pairs_distinct"], v["ctx_pairs_unseen_in_matching_train_ctx_pct"], v["query_pairs_unseen_as_train_ctx_pair_pct"], v["query_pairs_unseen_anywhere_in_union_pct"], v["predicates_unseen_in_union_train"], v["query_literal_memory_check"]["agree_pct"]))
P("")
P("T2b ROLES: supporting fact position and distance to query sentence (median [p10-p90]); ent2ent = query entity vs supporting-fact entity (chars)")
def g(d, k):
    v = d.get(k); return "-" if not v else "%s[%s-%s]" % (v["p50"], v["p10"], v["p90"])
for f in ["placebo_dev", "placebo_test_wording", "logic_gate", "logic_test_sampler"]:
    for grp, d in roles["files"][f].items():
        if "|d0" in grp and f == "logic_gate" or "unknown" in grp: pass
        P("%-21s %-12s n=%-4d ctx_sent=%s fact_idx=%s gap_near=%s gap_far=%s ent2ent=%s prev_sent_share=%s" % (f, grp, d["n_rows"], g(d, "n_ctx_sentences"), g(d, "fact_sent_idx"), g(d, "gap_chars_nearest_support"), g(d, "gap_chars_farthest_support"), g(d, "ent_to_ent_chars"), d.get("support_is_prev_sentence", {}).get("share", "-")))
P("")
P("T2c FAMILIES (parent s200 accuracy from RESULT.json final_eval; n=40 each)")
P("%-14s %5s %6s %5s %5s %6s %6s %6s %s" % ("family", "n", "chars", "sent", "inprm", "indist", "frame", "varnt", "answers"))
for k in ["syllogism", "prop_eval", "verify_claim", "kin_chain", "order_chain", "rule_apply", "object_track", "story_chain3", "passage_qa", "chain_ops"]:
    v = fam["families"][k]
    P("%-14s %5d %6.1f %5.1f %5.2f %6s %6s %6s %s" % (k, v["n"], v["chars_mean"], v["sentences_mean"], v["frac_answer_is_prompt_token"], v["parent_s200_in_dist"], v["parent_s200_frame"], v["parent_s200_variant"], v["top_answers"][:3] if v["distinct_answers"] <= 12 else ""))
P("")
P("T3 SHORTCUTS: chi-square p / Cramer V per variable and file")
vars_ = list(chi["logic_train"].keys())
P("%-21s " % "file" + " ".join("%-15s" % v[:15] for v in vars_))
for f in files:
    P("%-21s " % f + " ".join("%-15s" % ("p=%.2g V=%.2f" % (chi[f][v]["p"], chi[f][v]["cramers_V"]) if chi[f][v] else "-") for v in vars_))
P("")
for tr in ["logic_train", "placebo_train"]:
    fn = f"{OUT}/shortcuts_lr_{tr}.json"
    if os.path.exists(fn):
        d = json.load(open(fn))["results"][tr]
        P("LR cross-fit (30k train rows) %s: OOF acc | eval acc per file | OOF logloss (ln3=1.0986)" % tr)
        for s, v in d.items():
            P("  %-7s OOF %5.2f ll %.4f | %s" % (s, v["oof_acc"], v["oof_logloss"], " ".join("%s=%.1f" % (e.replace("logic_", "").replace("placebo_", "p_"), x["acc"]) for e, x in v["eval"].items())))
P("")
P("audit.py classifiers fitted on 6000 v2 train rows, applied to eval (nb / centroid / tree), majority 33.3")
for tr in aud:
    for k in aud[tr]:
        for e, v in aud[tr][k].items():
            P("  %-13s %-5s %-21s %5.1f %5.1f %5.1f" % (tr, k, e, v["naive_bayes"], v["nearest_centroid"], v["tree_depth3"]))
P("")
P("singleton-predicate lookup (distinct,singleton,nsent) OOF / eval")
for tr in ["logic_train", "placebo_train"]:
    for k, v in leak[tr].items():
        P("  %-13s %-40s OOF %5.2f ll %.4f eval %s" % (tr, k, v["oof_acc"], v["oof_logloss"], {e: x["acc"] for e, x in v["eval"].items()}))
P("")
P("T4 LADDER on depth-0 rows (accuracy %)")
for f in ["placebo_dev", "placebo_test_wording", "logic_gate"]:
    d = lad[f]
    key = "d0"
    P("  %-21s d0: %s" % (f, {k: v["acc"] for k, v in d[key].items()}))
P("  single-feature gain over majority (pts), placebo_train: %s" % lad["single_feature_table"]["placebo_train"]["gain_pts_over_majority_single_feature"])
P("  single-feature gain over majority (pts), logic_train:   %s" % lad["single_feature_table"]["logic_train"]["gain_pts_over_majority_single_feature"])
open(f"{OUT}/tables.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
