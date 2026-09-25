"""Blind independent recount of bm-390 run files.

Written from the LoCoMo repo's task_eval/evaluation.py (normalize_answer, f1_score, f1,
eval_question_answering rules for categories 1-4) and task_eval/hf_llm_utils.py
(get_hf_answers reply clean-up). MMLU/GSM8K picking rules reimplemented from the registered
rules (mmlu_pick, gsm_pick, ABSTAIN regex). Prints counts, scores, hashes and ids only.
"""
from __future__ import annotations

import hashlib
import json
import re
import string
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import regex
from nltk.stem import PorterStemmer

R = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
OUT = R / "out"
ps = PorterStemmer()
ARMS = ["P", "P_bare", "Rb"]
CATS = (1, 2, 3, 4)
SEED, BOOT = 390, 10000


# ------------------------------------------------ LoCoMo repo: task_eval/evaluation.py
def normalize_answer(s):
    s = s.replace(',', "")

    def remove_articles(text):
        return regex.sub(r'\b(a|an|the|and)\b', ' ', text)

    def white_space_fix(text):
        return ' '.join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def f1_score(prediction, ground_truth):
    prediction_tokens = [ps.stem(w) for w in normalize_answer(prediction).split()]
    ground_truth_tokens = [ps.stem(w) for w in normalize_answer(ground_truth).split()]
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0
    precision = 1.0 * num_same / len(prediction_tokens)
    recall = 1.0 * num_same / len(ground_truth_tokens)
    return (2 * precision * recall) / (precision + recall)


def f1_multi(prediction, ground_truth):
    predictions = [p.strip() for p in prediction.split(',')]
    ground_truths = [g.strip() for g in ground_truth.split(',')]
    return float(np.mean([max([f1_score(p, gt) for p in predictions]) for gt in ground_truths]))


def official_f1(output: str, gold, category: int) -> float:
    """eval_question_answering, categories 1-4 (prediction is a str, so answer = str(gold))."""
    answer = str(gold)
    if category == 3:
        answer = answer.split(';')[0].strip()
    if category in (2, 3, 4):
        return float(f1_score(output, answer))
    if category == 1:
        return f1_multi(output, answer)
    raise ValueError(category)


# ------------------------------------------------ LoCoMo repo: task_eval/hf_llm_utils.py get_hf_answers
def hf_clean(answer: str) -> str:
    """Post-processing for non-adversarial questions (batch_size == 1 path)."""
    answer = answer.replace('\\"', "'").strip()
    answer = [w.strip() for w in answer.split('\n') if not w.strip().isspace()][0]
    answer = (answer.lower().replace('(a)', '').replace('(b)', '').replace('a)', '')
              .replace('b)', '').replace('answer:', '').strip())
    return answer


# ------------------------------------------------ registered rules (reimplemented)
ABSTAIN = re.compile(r"\b(i don't know|i do not know|i'm not sure|i am not sure|not sure|no information|"
                     r"not mentioned|i don't have|i do not have|can't tell|cannot tell|no idea|unknown|"
                     r"not certain|don't remember|do not remember)\b")
MMLU_FIRST = re.compile(r"(?i:answer(?: is)?|option)\s*[:\-]?\s*\(?([ABCD])(?![A-Za-z])")
MMLU_ANY = re.compile(r"(?<![A-Za-z])([ABCD])(?![A-Za-z])")
NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
GSM_ANS = re.compile(r"(?i)answer is\s*[:\$]?\s*(-?\d[\d,]*(?:\.\d+)?)")


def mmlu_pick(reply: str):
    m = MMLU_FIRST.search(reply) or MMLU_ANY.search(reply)
    return m.group(1) if m else None


def gsm_pick(reply: str):
    nums = GSM_ANS.findall(reply) or NUM.findall(reply)
    if not nums:
        return None
    try:
        return float(nums[-1].replace(",", ""))
    except ValueError:
        return None


# ------------------------------------------------ helpers
def file_facts(p: Path) -> dict:
    b = p.read_bytes()
    rows = [json.loads(line) for line in b.decode("utf-8").splitlines() if line.strip()]
    qids = [r.get("qid") for r in rows]
    return {
        "bytes": len(b),
        "sha256": hashlib.sha256(b).hexdigest(),
        "crlf": b.count(b"\r\n"),
        "rows": len(rows),
        "unique_qids": len(set(qids)) if all(q is not None for q in qids) else None,
        "blank_lines": sum(1 for line in b.decode("utf-8").splitlines() if not line.strip()),
    }, rows


def reported_hashes(md: Path) -> dict:
    out = {}
    for line in md.read_text(encoding="utf-8").splitlines():
        m = re.match(r"- (\S+\.jsonl) bytes=(\d+) crlf=(\d+) rows=(\d+) sha256=([0-9a-fA-F]{64})", line)
        if m:
            out[m.group(1)] = {"bytes": int(m.group(2)), "crlf": int(m.group(3)), "rows": int(m.group(4)),
                               "sha256": m.group(5).lower()}
    return out


def boot(diff: np.ndarray, rng) -> tuple[float, float]:
    n = len(diff)
    idx = rng.integers(0, n, size=(BOOT, n))
    means = diff[idx].mean(axis=1) * 100
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def boot_loop(diff: np.ndarray, rng) -> tuple[float, float]:
    n = len(diff)
    means = np.array([diff[rng.integers(0, n, size=n)].mean() for _ in range(BOOT)]) * 100
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main() -> int:
    res: dict = {"inputs": {}, "validity": {}, "locomo": {}, "paired": {}, "general": {}, "problems": []}
    problems = res["problems"]
    rep = reported_hashes(R / "RESULTS-benspc3.md")

    # ---------------- gold
    locomo = json.load(open(R / "data/locomo10.json", encoding="utf-8"))
    gold = {}
    for s in locomo:
        for i, q in enumerate(s["qa"]):
            gold[f"{s['sample_id']}#{i}"] = q
    gold_order = list(gold)
    gcat = Counter(q["category"] for q in gold.values())
    res["inputs"]["locomo_gold"] = {"convs": len(locomo), "qa": len(gold),
                                    "by_category": {str(k): gcat[k] for k in sorted(gcat)},
                                    "cat1to4": sum(gcat[c] for c in CATS),
                                    "sha256": hashlib.sha256((R / "data/locomo10.json").read_bytes()).hexdigest()}
    for name in ["mmlu300.jsonl", "gsm8k300.jsonl"]:
        res["inputs"][name] = {"sha256": hashlib.sha256((R / "data" / name).read_bytes()).hexdigest()}

    # ---------------- run files
    rows_by = {}
    for fn in ["locomo_P.jsonl", "locomo_P_bare.jsonl", "locomo_Rb.jsonl", "mmlu_P.jsonl", "gsm8k_P.jsonl",
               "sleep_P.jsonl", "locomo_P_reading.jsonl"]:
        facts, rows = file_facts(R / "run" / fn)
        r = rep.get(fn)
        facts["reported"] = r
        facts["sha256_matches_report"] = bool(r and r["sha256"] == facts["sha256"])
        facts["bytes_rows_crlf_match_report"] = bool(r and (r["bytes"], r["rows"], r["crlf"]) ==
                                                     (facts["bytes"], facts["rows"], facts["crlf"]))
        if not facts["sha256_matches_report"] or not facts["bytes_rows_crlf_match_report"]:
            problems.append(f"{fn}: does not match RESULTS-benspc3.md (sha/bytes/rows/crlf)")
        if facts["crlf"]:
            problems.append(f"{fn}: {facts['crlf']} CRLF sequences")
        res["validity"][fn] = facts
        rows_by[fn] = rows

    # ---------------- LoCoMo arms: coverage, duplicates, categories
    arm_rows = {}
    for arm in ARMS:
        fn = f"locomo_{arm}.jsonl"
        rows = rows_by[fn]
        qc = Counter(r["qid"] for r in rows)
        dups = {q: c for q, c in qc.items() if c > 1}
        missing = [q for q in gold_order if q not in qc]
        extra = [q for q in qc if q not in gold]
        cat_mismatch = sum(1 for r in rows if r["qid"] in gold and r["category"] != gold[r["qid"]]["category"])
        empty = sum(1 for r in rows if not r["reply"].strip())
        empty14 = sum(1 for r in rows if r["qid"] in gold and gold[r["qid"]]["category"] in CATS and not r["reply"].strip())
        multiline14 = sum(1 for r in rows if r["qid"] in gold and gold[r["qid"]]["category"] in CATS
                          and "\n" in r["reply"].strip())
        cleaned_empty14 = sum(1 for r in rows if r["qid"] in gold and gold[r["qid"]]["category"] in CATS
                              and not hf_clean(r["reply"]))
        order_same = [r["qid"] for r in rows] == gold_order
        v = {"rows": len(rows), "unique_qids": len(qc), "missing_gold_qids": len(missing),
             "extra_rows_not_in_gold": len(extra), "duplicate_qids": len(dups),
             "duplicate_extra_rows": sum(c - 1 for c in dups.values()),
             "category_mismatch_vs_gold": cat_mismatch, "empty_replies_all": empty,
             "empty_replies_cat1to4": empty14, "multiline_replies_cat1to4": multiline14,
             "empty_after_official_cleanup_cat1to4": cleaned_empty14,
             "row_order_equals_gold_order": order_same,
             "ms_le_0": sum(1 for r in rows if r["ms"] <= 0),
             "ms_median": round(float(np.median([r["ms"] for r in rows])), 1),
             "reply_words_median_cat1to4": float(np.median([len(r["reply"].split()) for r in rows
                                                            if r["qid"] in gold and gold[r["qid"]]["category"] in CATS])),
             "cat5_rows": sum(1 for r in rows if r["qid"] in gold and gold[r["qid"]]["category"] == 5),
             "cat5_abstain_regex_hits": sum(1 for r in rows if r["qid"] in gold and gold[r["qid"]]["category"] == 5
                                            and ABSTAIN.search(r["reply"].lower()))}
        if "question_turn_writes" in rows[0]:
            v["question_turn_writes_sum"] = sum(r["question_turn_writes"] for r in rows)
            v["question_turn_writes_nonzero_rows"] = sum(1 for r in rows if r["question_turn_writes"])
        if "turns_dropped" in rows[0]:
            v["turns_dropped_nonzero_rows"] = sum(1 for r in rows if r["turns_dropped"])
        res["validity"][fn].update({"locomo": v})
        for key in ["missing_gold_qids", "extra_rows_not_in_gold", "duplicate_qids", "category_mismatch_vs_gold",
                    "empty_replies_all", "empty_after_official_cleanup_cat1to4"]:
            if v[key]:
                problems.append(f"{fn}: {key} = {v[key]}")
        # keep first row per qid
        by = {}
        for r in rows:
            by.setdefault(r["qid"], r)
        arm_rows[arm] = by

    # cross-arm identity
    ids14 = [q for q in gold_order if gold[q]["category"] in CATS]
    same = {}
    for a, b in [("P", "P_bare"), ("P", "Rb"), ("P_bare", "Rb")]:
        same[f"{a}_vs_{b}_identical_raw_replies_cat1to4"] = sum(
            1 for q in ids14 if q in arm_rows[a] and q in arm_rows[b] and arm_rows[a][q]["reply"] == arm_rows[b][q]["reply"])
        same[f"{a}_vs_{b}_identical_raw_replies_all"] = sum(
            1 for q in gold_order if q in arm_rows[a] and q in arm_rows[b] and arm_rows[a][q]["reply"] == arm_rows[b][q]["reply"])
    res["validity"]["cross_arm"] = same

    # ---------------- sleep and reading
    sl = rows_by["sleep_P.jsonl"]
    res["validity"]["sleep_P.jsonl"]["sleep"] = {
        "rows": len(sl), "checkpoint_exists_true": sum(1 for r in sl if r["checkpoint_exists"] is True),
        "attempted_true": sum(1 for r in sl if r["attempted"] is True),
        "accepted_true": sum(1 for r in sl if r["accepted"] is True),
        "distinct_reasons": len(Counter(r["reason"] for r in sl)),
        "reason_counts": dict(Counter(r["reason"][:120] for r in sl)),  # system log string, not item text
        "attempted_false_but_accepted_true": sum(1 for r in sl if r["attempted"] is False and r["accepted"] is True),
        "distinct_state_dirs": len(Counter(r["state_dir"] for r in sl)),
    }
    rd = rows_by["locomo_P_reading.jsonl"]
    res["validity"]["locomo_P_reading.jsonl"]["reading"] = {
        "rows": len(rd), "distinct_convs": len({r["conv"] for r in rd}),
        "convs_match_gold_sample_ids": sorted(r["conv"] for r in rd) == sorted(s["sample_id"] for s in locomo),
        "sum_stored_triples_after_reading": sum(r["stored_triples_after_reading"] for r in rd),
        "sum_sessions": sum(r["sessions"] for r in rd), "sum_sleeps": sum(r["sleeps"] for r in rd),
        "sum_check_questions_asked": sum(r["check_questions_asked"] for r in rd),
        "sum_turns_fed": sum(r["turns_fed"] for r in rd),
        "convs_with_zero_triples": sum(1 for r in rd if r["stored_triples_after_reading"] == 0),
        "convs_with_zero_check_questions": sum(1 for r in rd if r["check_questions_asked"] == 0),
    }

    # ---------------- LoCoMo official F1
    f1s = {}
    for arm in ARMS:
        by = arm_rows[arm]
        vals, vals_raw, abst, cw = [], [], [], []
        for q in ids14:
            g = gold[q]
            reply = by[q]["reply"] if q in by else ""
            cat = g["category"]
            v = official_f1(hf_clean(reply), g["answer"], cat)
            vals.append(v)
            vals_raw.append(official_f1(reply, g["answer"], cat))
            a = bool(ABSTAIN.search(reply.lower()))
            abst.append(a)
            cw.append((not a) and v == 0)
        vals = np.array(vals, dtype=float)
        vals_raw = np.array(vals_raw, dtype=float)
        vals_r3 = np.array([round(x, 3) for x in vals])
        cats = np.array([gold[q]["category"] for q in ids14])
        abst = np.array(abst)
        cw = np.array(cw)
        per = {}
        for c in CATS:
            m = cats == c
            per[str(c)] = {"n": int(m.sum()), "f1_x100": round(float(vals[m].mean() * 100), 2),
                           "f1_x100_perq_rounded3": round(float(vals_r3[m].mean() * 100), 2),
                           "f1_x100_raw_reply_no_cleanup": round(float(vals_raw[m].mean() * 100), 2),
                           "abstain": int(abst[m].sum()), "confident_wrong": int(cw[m].sum()),
                           "f1_zero": int((vals[m] == 0).sum()), "f1_one": int((vals[m] == 1).sum())}
        res["locomo"][arm] = {
            "n_cat1to4": len(ids14),
            "overall_f1_x100": round(float(vals.mean() * 100), 2),
            "overall_f1_x100_unrounded": float(vals.mean() * 100),
            "overall_f1_x100_perq_rounded3": round(float(vals_r3.mean() * 100), 2),
            "overall_f1_x100_raw_reply_no_cleanup": round(float(vals_raw.mean() * 100), 2),
            "abstain_cat1to4": int(abst.sum()), "confident_wrong_cat1to4": int(cw.sum()),
            "f1_zero_cat1to4": int((vals == 0).sum()),
            "by_category": per,
        }
        f1s[arm] = vals

    # ---------------- paired bootstrap
    for a in ["P", "P_bare"]:
        diff = f1s[a] - f1s["Rb"]
        lo, hi = boot(diff, np.random.default_rng(SEED))
        lo2, hi2 = boot_loop(diff, np.random.default_rng(SEED))
        res["paired"][f"{a}_minus_Rb"] = {
            "n": len(diff), "mean_diff_x100": round(float(diff.mean() * 100), 2),
            "ci95_x100": [round(lo, 2), round(hi, 2)],
            "ci95_x100_alt_loop_draws": [round(lo2, 2), round(hi2, 2)],
            "wins_losses_ties": [int((diff > 0).sum()), int((diff < 0).sum()), int((diff == 0).sum())],
            "method": "fresh numpy.random.default_rng(390) per comparison; rng.integers(0,n,size=(10000,n)); "
                      "mean diff per resample x100; np.percentile 2.5/97.5 (linear)",
        }
    # shared-stream variant (one rng used first for P then for P_bare)
    rng = np.random.default_rng(SEED)
    sh = {}
    for a in ["P", "P_bare"]:
        lo, hi = boot(f1s[a] - f1s["Rb"], rng)
        sh[f"{a}_minus_Rb"] = [round(lo, 2), round(hi, 2)]
    res["paired"]["alt_shared_rng_stream_ci95_x100"] = sh

    # ---------------- MMLU / GSM8K
    for task, gfile, pick in [("mmlu", "mmlu300.jsonl", mmlu_pick), ("gsm8k", "gsm8k300.jsonl", gsm_pick)]:
        golds = {}
        for line in open(R / "data" / gfile, encoding="utf-8"):
            if line.strip():
                d = json.loads(line)
                golds[d["qid"]] = d["gold"]
        rows = rows_by[f"{task}_P.jsonl"]
        qc = Counter(r["qid"] for r in rows)
        by = {}
        for r in rows:
            by.setdefault(r["qid"], r)
        right = right_tol = none = 0
        for q, gv in golds.items():
            rep_ = by[q]["reply"] if q in by else ""
            p = pick(rep_)
            if p is None:
                none += 1
                continue
            if task == "mmlu":
                right += int(p == gv.strip())
            else:
                gf = float(gv.replace(",", ""))
                right += int(p == gf)
                right_tol += int(abs(p - gf) < 1e-6)
        out = {"n_gold": len(golds), "rows": len(rows), "unique_qids": len(qc),
               "missing_gold_qids": sum(1 for q in golds if q not in qc),
               "extra_rows_not_in_gold": sum(1 for q in qc if q not in golds),
               "duplicate_qids": sum(1 for c in qc.values() if c > 1),
               "empty_replies": sum(1 for r in rows if not r["reply"].strip()),
               "no_pick": none, "right": right, "pct": round(100 * right / len(golds), 2)}
        if task == "mmlu":
            out["pick_distribution"] = dict(sorted(Counter(pick(by[q]["reply"]) if q in by else None
                                                           for q in golds).items(), key=lambda kv: str(kv[0])))
        else:
            out["right_abs_tol_1e-6"] = right_tol
        out["abstain_regex_hits"] = sum(1 for r in rows if ABSTAIN.search(r["reply"].lower()))
        out["no_pick_and_abstain"] = sum(1 for r in rows if pick(r["reply"]) is None and ABSTAIN.search(r["reply"].lower()))
        out["replies_with_any_digit"] = sum(1 for r in rows if any(ch.isdigit() for ch in r["reply"]))
        res["general"][task] = out
        for key in ["missing_gold_qids", "extra_rows_not_in_gold", "duplicate_qids", "empty_replies"]:
            if out[key]:
                problems.append(f"{task}_P.jsonl: {key} = {out[key]}")

    s = res["validity"]["sleep_P.jsonl"]["sleep"]
    if s["attempted_true"] == 0:
        problems.append(f"sleep_P.jsonl: {s['rows']} sleep rows, attempted=true in 0, accepted=true in "
                        f"{s['accepted_true']} (no sleep was ever attempted; {s['distinct_reasons']} distinct reason)")
    rd_ = res["validity"]["locomo_P_reading.jsonl"]["reading"]
    problems.append(f"locomo_P_reading.jsonl: only {rd_['sum_stored_triples_after_reading']} stored triples after "
                    f"reading {rd_['sum_turns_fed']} turns in 10 conversations; {rd_['convs_with_zero_triples']} "
                    f"conversation with 0")
    qw = res["validity"]["locomo_P_bare.jsonl"]["locomo"]
    if qw.get("question_turn_writes_nonzero_rows"):
        problems.append(f"locomo_P_bare.jsonl: question_turn_writes nonzero in {qw['question_turn_writes_nonzero_rows']} "
                        f"row(s) (sum {qw['question_turn_writes_sum']}); locomo_P.jsonl has "
                        f"{res['validity']['locomo_P.jsonl']['locomo']['question_turn_writes_nonzero_rows']}")
    for task in ["mmlu", "gsm8k"]:
        g_ = res["general"][task]
        problems.append(f"{task}_P.jsonl: {g_['no_pick']} of {g_['n_gold']} replies give no pickable answer; "
                        f"{g_['abstain_regex_hits']} match the abstain regex")
    pa = res["locomo"]["P"]
    problems.append(f"locomo_P.jsonl: {pa['abstain_cat1to4']} of 1540 category 1-4 replies match the abstain regex "
                    f"(P_bare {res['locomo']['P_bare']['abstain_cat1to4']}, Rb {res['locomo']['Rb']['abstain_cat1to4']})")

    OUT.mkdir(exist_ok=True)
    (OUT / "recount.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
