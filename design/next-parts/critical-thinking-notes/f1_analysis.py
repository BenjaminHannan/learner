#!/usr/bin/env python3
"""F1 (error shape) on the saved critical-thinking-128 outputs. CPU, stdlib only.

STUDY ONLY. The 16 questions are consumed; GOLD-PRIVATE-v1.json is read for
study, never as a score, never for training/tuning/new evals.

Committed F1 readings (git show 8c49c5430:design/next-parts/critical-thinking-reasoner-design.md, row F1):
  "Near-misses and a length effect point to a squeeze. Copy-from-train above 25%
   or collapsed answers point to memorising. Scattered errors point to a skill gap."

The committed text gives a number only for copy-from-train (25%). The other
words need an operational test. These were written into this file before the
full analysis ran (after seeing ~19 trace rows and the saved emitted histogram):
  NEAR-MISS fires   : near-miss share on the 71 correct-call-wrong-final rows
                      (digit edit distance 1, OR digit transposition, OR |diff| in {1,10})
                      is above the 95th percentile of a within-checkpoint permutation null.
  LENGTH fires      : failure rate differs across answer digit counts (needs >1 digit count).
  SQUEEZE           : NEAR-MISS and LENGTH both fire (committed text says "and").
  COPY fires        : share of wrong finals whose value is a TRAIN32 answer > 25%.
  COLLAPSE fires    : in >=5 of 8 checkpoints, the modal emitted value covers >=4 of 16
                      outputs OR the checkpoint emits <=6 distinct values.
  MEMORISING        : COPY or COLLAPSE.
  SKILL GAP         : none of NEAR-MISS, COPY, COLLAPSE fire.
  MIXED             : SQUEEZE and MEMORISING both fire.
"""
import json, random, statistics
from collections import Counter, defaultdict
from pathlib import Path

D = Path(__file__).resolve().parent / "data128"
OUT = Path(__file__).resolve().parent / "f1_results.json"


def lev(a, b):
    a, b = str(a), str(b)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def transposed(a, b):
    a, b = str(a), str(b)
    if len(a) != len(b) or a == b:
        return False
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]


def near_miss(e, x):
    return lev(e, x) == 1 or transposed(e, x) or abs(e - x) in (1, 10)


def bug_answers(op, a, b):
    """Classic digit-procedure slips: dropped carry (add), smaller-from-larger / dropped borrow (sub)."""
    out = set()
    if op == "add":
        out.add((a // 10 + b // 10) * 10 + (a % 10 + b % 10) % 10)  # dropped carry
        out.add(a + b + 10)  # extra carry
    else:
        out.add((a // 10 - b // 10) * 10 + abs(a % 10 - b % 10))  # smaller-from-larger
        out.add(a - b - 10)  # extra borrow
        out.add(a - b + 10)  # dropped borrow
    out.discard(a + b if op == "add" else a - b)
    return out


# ---------- load ----------
lines =(D / "summaries/DEREK-SAVED-128-ROW-NUMERIC-TRACE-v1.tsv").read_text().strip().split("\n")
hdr = lines[0].split("\t")
trace = [dict(zip(hdr, l.split("\t"))) for l in lines[1:]]
raw = [json.loads(l) for l in (D / "outputs/EVAL-OBSERVATIONS.jsonl").read_text().splitlines() if l.strip()]
gold = {r["id"]: r for r in json.loads((D / "questions_and_scoring/GOLD-PRIVATE-v1.json").read_text())["rows"]}
conc = json.loads((D / "summaries/SAVED-OUTPUT-CONCENTRATION-ROLE-DIAGNOSIS-v2.json").read_text())
TRAIN32 = set(conc["TRAIN32_target_set"])
TRAIN32_FREQ = {int(k): v for k, v in conc["TRAIN32_target_frequency_32_rows"].items()}
assert len(trace) == 128 and len(raw) == 128 and len(gold) == 16

checks = {}
# ---------- verify trace TSV against raw rows ----------
mismatch = []
tok2val = {}
for g in gold.values():  # gold label tokens and operand literal tokens
    tok2val.setdefault(g["labels"][0][0], set()).add(int(g["canonical_numeric_target"]))
    for e in g["numeric_registry"]:
        tok2val.setdefault(g["input_ids"][0][e["token_indices"][0]], set()).add(e["value"])
for r in raw:
    for t in r["predicted_trace"]:
        if t["status"] == "OK":
            tok2val.setdefault(t["numeric_token_id"], set()).add(t["result"]["value"])
checks["token_map_conflicts"] = {k: sorted(v) for k, v in tok2val.items() if len(v) > 1}

rows = []
for i, (t, r) in enumerate(zip(trace, raw)):
    key = (int(t["seed"]), t["arm"], t["condition"], t["id"])
    if key != (r["seed"], r["arm"], r["condition"], r["id"]):
        mismatch.append(("key", i))
    g = gold[r["id"]]
    emit_tok = r["MODEL_raw_generate_ids"][0][0]
    if int(t["emitted_numeric_ID"]) != emit_tok or r["MODEL_raw_generate_ids"][0][1:] != [7]:
        mismatch.append(("emit_tok", i))
    first = r["predicted_trace"][0]
    calls = [x for x in r["predicted_trace"] if x["action"] != "NONE"]
    if t["executed_operation"] != first["action"]:
        mismatch.append(("op", i))
    a, b = g["operands"]
    op = g["operation"]
    expected = int(g["canonical_numeric_target"])
    if int(t["expected"]) != expected:
        mismatch.append(("expected", i))
    emitted = int(t["emitted_saved_map_value"])
    indep = tok2val.get(emit_tok)
    if indep is not None and emitted not in indep:
        mismatch.append(("emit_val", i))
    calc = first["result"]["value"] if first["status"] == "OK" else None
    ops = first.get("operand_values")
    if first["action"] == "ADD":
        correct_call = op == "add" and ops is not None and sorted(ops) == sorted([a, b])
    elif first["action"] == "SUB":
        correct_call = op == "sub" and ops == [a, b]
    else:
        correct_call = False
    correct_call = correct_call and first["status"] == "OK"
    correct = emitted == expected
    outcome = "correct" if correct else ("correct_call_wrong_final" if correct_call else "wrong_call_wrong_final")
    if outcome != t["outcome"]:
        mismatch.append(("outcome", i, outcome, t["outcome"]))
    rows.append(dict(i=i, seed=r["seed"], arm=r["arm"], lr=r["condition"], ck=(r["seed"], r["arm"], r["condition"]),
                     id=r["id"], pair=g["pair_id"], op=op, a=a, b=b, expected=expected, case=g["case"],
                     emitted=emitted, emit_tok=emit_tok, emit_indep=indep is not None, calc=calc,
                     action=first["action"], status=first["status"], n_calls=len(calls),
                     call_loop=first["loop_index"] if calls else None, outcome=outcome, pos=r["physical_row_index"]))
checks["trace_vs_raw_mismatches"] = mismatch
checks["emitted_tokens_with_independent_value"] = sum(x["emit_indep"] for x in rows)
checks["outcome_counts"] = dict(Counter(x["outcome"] for x in rows))
checks["calls_per_row"] = dict(Counter(x["n_calls"] for x in rows))
checks["call_loop_index"] = dict(Counter(str(x["call_loop"]) for x in rows))

CCWF = [x for x in rows if x["outcome"] == "correct_call_wrong_final"]
WRONG = [x for x in rows if x["outcome"] != "correct"]
by_ck = defaultdict(list)
for x in rows:
    by_ck[x["ck"]].append(x)
for v in by_ck.values():
    v.sort(key=lambda x: x["pos"])
ckname = lambda ck: "s%d-%s-%s" % ck

# ---------- per-row features ----------
expected_set = {x["expected"] for x in rows}
for x in rows:
    e, X = x["emitted"], x["expected"]
    other = x["a"] - x["b"] if x["op"] == "add" else x["a"] + x["b"]
    seq = by_ck[x["ck"]]
    prev = [y["emitted"] for y in seq if y["pos"] < x["pos"]]
    partner = [y for y in seq if y["pair"] == x["pair"] and y["id"] != x["id"]][0]
    x.update(ed=lev(e, X), ed1=lev(e, X) == 1, transp=transposed(e, X), d1=abs(e - X) == 1, d10=abs(e - X) == 10,
             near=near_miss(e, X), bug=e in bug_answers(x["op"], x["a"], x["b"]),
             eq_operand=e in (x["a"], x["b"]), eq_other_op=e == other,
             eq_calc=(x["calc"] is not None and e == x["calc"]),
             eq_prev=bool(prev) and e == prev[-1], eq_any_prev=e in prev,
             eq_partner=e == partner["emitted"], partner_calc_differs=(partner["calc"] != x["calc"]),
             eq_other_question_answer=(e in expected_set and e != X), in_train=e in TRAIN32,
             target_in_train=X in TRAIN32, digits=len(str(X)))


def rate(sub, f):
    n = len(sub)
    k = sum(1 for x in sub if x[f])
    return {"k": k, "n": n, "pct": round(100 * k / n, 1) if n else None}


FEATS = ["ed1", "transp", "d1", "d10", "near", "bug", "eq_operand", "eq_other_op", "eq_calc", "eq_prev",
         "eq_any_prev", "eq_partner", "eq_other_question_answer", "in_train"]
res = {"checks": checks}
res["features"] = {name: {f: rate(sub, f) for f in FEATS} for name, sub in
                   (("CCWF71", CCWF), ("WRONG113", WRONG), ("ALL128", rows))}
res["edit_distance_hist"] = {name: dict(sorted(Counter(x["ed"] for x in sub).items())) for name, sub in
                             (("CCWF71", CCWF), ("WRONG113", WRONG))}
diffs = [x["emitted"] - x["expected"] for x in CCWF]
res["CCWF_signed_diff"] = {"mean": round(statistics.mean(diffs), 2), "median": statistics.median(diffs),
                           "mean_abs": round(statistics.mean(map(abs, diffs)), 2),
                           "hist_abs_buckets": dict(Counter(min(abs(d) // 10 * 10, 50) for d in diffs))}

# ---------- distinct values / collapse ----------
res["distinct"] = {name: {"distinct_emitted": len({x["emitted"] for x in sub}),
                          "distinct_expected": len({x["expected"] for x in sub}),
                          "top5": Counter(x["emitted"] for x in sub).most_common(5)}
                   for name, sub in (("CCWF71", CCWF), ("WRONG113", WRONG), ("ALL128", rows))}
per_ck = {}
collapse_ck = 0
for ck, seq in sorted(by_ck.items()):
    c = Counter(x["emitted"] for x in seq)
    mode_v, mode_n = c.most_common(1)[0]
    distinct = len(c)
    fires = mode_n >= 4 or distinct <= 6
    collapse_ck += fires
    sub = [x for x in seq if x["outcome"] == "correct_call_wrong_final"]
    per_ck[ckname(ck)] = {"correct": sum(x["outcome"] == "correct" for x in seq),
                          "correct_calls": sum(x["outcome"] != "wrong_call_wrong_final" for x in seq),
                          "CCWF": len(sub), "distinct_emitted_of16": distinct, "mode": [mode_v, mode_n],
                          "collapse_rule_fires": fires,
                          "CCWF_near": sum(x["near"] for x in sub), "CCWF_eq_operand": sum(x["eq_operand"] for x in sub),
                          "CCWF_eq_other_op": sum(x["eq_other_op"] for x in sub),
                          "pair_same_output": sum(1 for p in {x["pair"] for x in seq}
                                                  if len({x["emitted"] for x in seq if x["pair"] == p}) == 1),
                          "emitted_seq": [x["emitted"] for x in seq]}
res["per_checkpoint"] = per_ck
res["collapse_checkpoints_firing"] = collapse_ck

# control vs low_lr identity
same = {}
for s in (0, 1):
    for arm in ("contextual", "static"):
        A = [x["emitted"] for x in by_ck[(s, arm, "control")]]
        B = [x["emitted"] for x in by_ck[(s, arm, "low_lr")]]
        Ac = [x["action"] for x in by_ck[(s, arm, "control")]]
        Bc = [x["action"] for x in by_ck[(s, arm, "low_lr")]]
        same["s%d-%s" % (s, arm)] = {"same_emitted_of16": sum(p == q for p, q in zip(A, B)),
                                     "same_action_of16": sum(p == q for p, q in zip(Ac, Bc))}
res["control_vs_lowlr_identity"] = same
# seed and arm agreement (control only)
agree = {}
for (p, q) in (((0, "contextual"), (0, "static")), ((1, "contextual"), (1, "static")),
               ((0, "contextual"), (1, "contextual")), ((0, "static"), (1, "static"))):
    A = [x["emitted"] for x in by_ck[(*p, "control")]]
    B = [x["emitted"] for x in by_ck[(*q, "control")]]
    agree["%s vs %s" % ("s%d-%s" % p, "s%d-%s" % q)] = sum(u == v for u, v in zip(A, B))
res["cross_checkpoint_agreement_control_of16"] = agree
res["per_question_distinct_emitted_across_8"] = {q: len({x["emitted"] for x in rows if x["id"] == q}) for q in gold}

# ---------- breakdowns ----------
def fail_by(key):
    out = {}
    for v in sorted({x[key] for x in rows}, key=str):
        sub = [x for x in rows if x[key] == v]
        cc = [x for x in sub if x["outcome"] != "wrong_call_wrong_final"]
        out[str(v)] = {"rows": len(sub), "wrong": sum(x["outcome"] != "correct" for x in sub),
                       "correct_call_rows": len(cc), "CCWF": sum(x["outcome"] == "correct_call_wrong_final" for x in cc),
                       "fail_given_correct_call_pct": round(100 * sum(x["outcome"] != "correct" for x in cc) / len(cc), 1) if cc else None}
    return out


res["by_digits"] = fail_by("digits")
res["by_case"] = fail_by("case")
res["by_target_in_train"] = fail_by("target_in_train")
res["by_seed"] = fail_by("seed")
res["by_arm"] = fail_by("arm")
res["by_lr"] = fail_by("lr")
res["by_op"] = fail_by("op")
res["by_question"] = fail_by("id")

# calculator sensitivity: does emitted change when the calculator value changes within a pair?
pairs = defaultdict(list)
for x in rows:
    pairs[(x["ck"], x["pair"])].append(x)
cs = Counter()
for (ck, p), v in pairs.items():
    if len(v) != 2 or v[0]["calc"] is None or v[1]["calc"] is None:
        cs["skipped"] += 1
        continue
    calc_diff = v[0]["calc"] != v[1]["calc"]
    emit_same = v[0]["emitted"] == v[1]["emitted"]
    cs["calc_%s__emit_%s" % ("differs" if calc_diff else "same", "same" if emit_same else "differs")] += 1
res["pair_calc_sensitivity"] = dict(cs)
# wrong-call rows: emitted equals the (wrong) calculator value?
wc = [x for x in rows if x["outcome"] == "wrong_call_wrong_final" and x["calc"] is not None]
res["wrong_call_rows_emit_eq_calc"] = {"k": sum(x["eq_calc"] for x in wc), "n": len(wc),
                                        "calc_in_train": sum(x["calc"] in TRAIN32 for x in wc)}
# correct-call rows: emitted correct split by whether calculator value is a TRAIN32 answer
cc = [x for x in rows if x["outcome"] != "wrong_call_wrong_final"]
res["correct_call_by_calc_in_train"] = {
    str(flag): {"n": len([x for x in cc if (x["calc"] in TRAIN32) == flag]),
                "correct": sum(x["outcome"] == "correct" for x in cc if (x["calc"] in TRAIN32) == flag)}
    for flag in (True, False)}
# emitted frequency vs TRAIN32 frequency
ef = Counter(x["emitted"] for x in rows)
res["emitted_vs_train_freq"] = {str(v): {"emitted": ef.get(v, 0), "train": TRAIN32_FREQ.get(v, 0)} for v in sorted(TRAIN32)}
res["train_values_never_emitted"] = sorted(v for v in TRAIN32 if v not in ef)
res["copy_base_rate_uniform_10_99"] = round(len(TRAIN32) / 90, 3)

# ---------- permutation null for near-miss ----------
rng = random.Random(0)
ck_groups = defaultdict(list)
for x in CCWF:
    ck_groups[x["ck"]].append(x)
obs = {f: sum(x[f] for x in CCWF) for f in ("near", "ed1", "transp", "d10", "bug", "eq_operand", "eq_other_op")}
null = {f: [] for f in obs}
N_PERM = 20000
for _ in range(N_PERM):
    tot = Counter()
    for ck, grp in ck_groups.items():
        em = [x["emitted"] for x in grp]
        rng.shuffle(em)
        for x, e in zip(grp, em):
            X = x["expected"]
            other = x["a"] - x["b"] if x["op"] == "add" else x["a"] + x["b"]
            tot["near"] += near_miss(e, X)
            tot["ed1"] += lev(e, X) == 1
            tot["transp"] += transposed(e, X)
            tot["d10"] += abs(e - X) == 10
            tot["bug"] += e in bug_answers(x["op"], x["a"], x["b"])
            tot["eq_operand"] += e in (x["a"], x["b"])
            tot["eq_other_op"] += e == other
    for f in obs:
        null[f].append(tot[f])
perm = {}
for f in obs:
    s = sorted(null[f])
    p_ge = sum(v >= obs[f] for v in s) / N_PERM
    perm[f] = {"observed": obs[f], "null_mean": round(statistics.mean(s), 2), "null_p95": s[int(0.95 * N_PERM)],
               "p_one_sided_ge": round(p_ge, 4)}
res["permutation_null_CCWF_within_checkpoint"] = perm
# uniform-over-TRAIN32 null (excluding the expected value)
un = 0.0
for x in CCWF:
    cand = [v for v in TRAIN32 if v != x["expected"]]
    un += sum(near_miss(v, x["expected"]) for v in cand) / len(cand)
res["uniform_TRAIN32_null_near_expected"] = round(un, 2)

# ---------- secondary descriptives (do not feed the reading) ----------
def pearson(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    return round(sxy / (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5, 3)


ok = [x for x in rows if x["calc"] is not None]
res["pearson_emitted_vs_calc_OKrows"] = {"r": pearson([x["emitted"] for x in ok], [x["calc"] for x in ok]), "n": len(ok)}
res["pearson_emitted_vs_expected_all"] = pearson([x["emitted"] for x in rows], [x["expected"] for x in rows])
res["pearson_emitted_vs_expected_CCWF"] = pearson([x["emitted"] for x in CCWF], [x["expected"] for x in CCWF])
sec = {}
for flag in (True, False):
    sub = [x for x in CCWF if x["target_in_train"] == flag]
    nearest_hits = 0
    for x in sub:
        dmin = min(abs(v - x["expected"]) for v in TRAIN32 if v != x["expected"])
        nearest_hits += abs(x["emitted"] - x["expected"]) == dmin
    sec["target_in_train=%s" % flag] = {
        "n": len(sub), "near": sum(x["near"] for x in sub),
        "same_tens_digit": sum(str(x["emitted"])[0] == str(x["expected"])[0] for x in sub),
        "same_units_digit": sum(str(x["emitted"])[-1] == str(x["expected"])[-1] for x in sub),
        "emitted_is_a_nearest_other_TRAIN32_value": nearest_hits,
        "mean_abs_diff": round(statistics.mean(abs(x["emitted"] - x["expected"]) for x in sub), 2)}
res["CCWF_near_miss_split"] = sec
# permutation null for mean |diff| on CCWF
md_obs = statistics.mean(abs(x["emitted"] - x["expected"]) for x in CCWF)
md_null = []
rng2 = random.Random(1)
for _ in range(5000):
    tot = 0
    for grp in ck_groups.values():
        em = [x["emitted"] for x in grp]
        rng2.shuffle(em)
        tot += sum(abs(e - x["expected"]) for x, e in zip(grp, em))
    md_null.append(tot / len(CCWF))
md_null.sort()
res["CCWF_mean_abs_diff_vs_perm"] = {"observed": round(md_obs, 2), "null_mean": round(statistics.mean(md_null), 2),
                                     "null_p05": round(md_null[int(0.05 * len(md_null))], 2),
                                     "p_one_sided_le": round(sum(v <= md_obs for v in md_null) / len(md_null), 4)}

# ---------- apply committed readings ----------
near_fires = obs["near"] > perm["near"]["null_p95"]
length_testable = len({x["digits"] for x in rows}) > 1
copy_share_ccwf = sum(x["in_train"] for x in CCWF) / len(CCWF)
copy_share_wrong = sum(x["in_train"] for x in WRONG) / len(WRONG)
copy_fires = copy_share_wrong > 0.25
collapse_fires = collapse_ck >= 5
squeeze = near_fires and length_testable  # length effect cannot fire if untestable
memorising = copy_fires or collapse_fires
res["reading"] = {"NEAR_MISS_fires": near_fires, "LENGTH_testable": length_testable,
                  "SQUEEZE": squeeze, "COPY_share_CCWF": round(copy_share_ccwf, 3),
                  "COPY_share_WRONG": round(copy_share_wrong, 3), "COPY_fires": copy_fires,
                  "COLLAPSE_checkpoints": collapse_ck, "COLLAPSE_fires": collapse_fires,
                  "MEMORISING": memorising,
                  "verdict": "mixed" if squeeze and memorising else "squeeze" if squeeze else
                  "memorising" if memorising else ("skill gap" if not near_fires else "none")}
OUT.write_text(json.dumps(res, indent=1, default=str))
print(json.dumps(res, indent=1, default=str))

# ---------- appended: within-action correlation (separates "knows the operation" from "knows the number") ----------
within = {}
for act in ("ADD", "SUB"):
    sub = [x for x in rows if x["calc"] is not None and x["action"] == act]
    within[act] = {"n": len(sub), "r_emitted_vs_calc": pearson([x["emitted"] for x in sub], [x["calc"] for x in sub]),
                   "distinct_calc": len({x["calc"] for x in sub})}
    sub2 = [x for x in CCWF if x["action"] == act]
    within[act]["CCWF_n"] = len(sub2)
    within[act]["CCWF_r"] = pearson([x["emitted"] for x in sub2], [x["calc"] for x in sub2]) if len({x["calc"] for x in sub2}) > 1 else None
res["within_action_correlation"] = within
OUT.write_text(json.dumps(res, indent=1, default=str))
print("WITHIN", json.dumps(within))

# ---------- appended: robustness null, shuffle within checkpoint AND within operation ----------
grp2 = defaultdict(list)
for x in CCWF:
    grp2[(x["ck"], x["op"])].append(x)
rng3 = random.Random(2)
nn_near, nn_ed1, nn_md = [], [], []
for _ in range(20000):
    a_near = a_ed1 = a_md = 0
    for grp in grp2.values():
        em = [x["emitted"] for x in grp]
        rng3.shuffle(em)
        for x, e in zip(grp, em):
            a_near += near_miss(e, x["expected"]); a_ed1 += lev(e, x["expected"]) == 1
            a_md += abs(e - x["expected"])
    nn_near.append(a_near); nn_ed1.append(a_ed1); nn_md.append(a_md / len(CCWF))
for L in (nn_near, nn_ed1, nn_md):
    L.sort()
res["robust_null_within_checkpoint_and_op"] = {
    "near": {"observed": obs["near"], "null_mean": round(statistics.mean(nn_near), 2), "null_p95": nn_near[19000],
             "p_ge": round(sum(v >= obs["near"] for v in nn_near) / 20000, 4)},
    "ed1": {"observed": obs["ed1"], "null_mean": round(statistics.mean(nn_ed1), 2), "null_p95": nn_ed1[19000],
            "p_ge": round(sum(v >= obs["ed1"] for v in nn_ed1) / 20000, 4)},
    "mean_abs_diff": {"observed": round(md_obs, 2), "null_mean": round(statistics.mean(nn_md), 2),
                      "p_le": round(sum(v <= md_obs for v in nn_md) / 20000, 4)}}
OUT.write_text(json.dumps(res, indent=1, default=str))
print("ROBUST", json.dumps(res["robust_null_within_checkpoint_and_op"]))
