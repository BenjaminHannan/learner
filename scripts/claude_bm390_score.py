#!/usr/bin/env python3
"""bm-390 scorer (public-benchmarks thread, 2026-09-25). New file only.

LoCoMo is scored with the LoCoMo repo's own answer clean-up and metric (task_eval/hf_llm_utils.py
get_hf_answers post-processing and task_eval/evaluation.py eval_question_answering @3eb6f2c; the
functions below marked VERBATIM are copied unchanged). General tests use the rules fixed below.

  python -B scripts/claude_bm390_score.py --data DATA --runs RUNDIR --primary P \
      --baselines T,Rb[,Q2,L12] --report C --out SCOREDIR

Reads <runs>/locomo_<name>.jsonl (several files named locomo_<name>.part*.jsonl are joined), and
<runs>/mmlu_<name>.jsonl, <runs>/gsm8k_<name>.jsonl when present. Writes <out>/score.json and prints one
JSON line per arm plus one line with the registered marks. Counts only; no question, gold or reply text.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import string
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import regex
from nltk.stem import PorterStemmer

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_bm390 as P  # noqa: E402

ps = PorterStemmer()
SEED = 390
BOOT = 10000
ABSTAIN = re.compile(r"\b(i don't know|i do not know|i'm not sure|i am not sure|not sure|no information|"
                     r"not mentioned|i don't have|i do not have|can't tell|cannot tell|no idea|unknown|"
                     r"not certain|don't remember|do not remember)\b")


# ---------------------------------------------------------------- VERBATIM from task_eval/evaluation.py
def normalize_answer(s):

    s = s.replace(',', "")
    def remove_articles(text):
        # return regex.sub(r'\b(a|an|the)\b', ' ', text)
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
    f1 = (2 * precision * recall) / (precision + recall)
    # print('# F1 #', prediction, ' | ', ground_truth, ' #', precision, recall, f1)
    # return recall
    return f1


def f1(prediction, ground_truth):
    predictions = [p.strip() for p in prediction.split(',')]
    ground_truths = [g.strip() for g in ground_truth.split(',')]
    # print('# F1 [multi-answer]#', predictions, ' | ', ground_truths, ' #', np.mean([max([f1_score(prediction, gt) for prediction in predictions]) for gt in ground_truths]))
    return np.mean([max([f1_score(prediction, gt) for prediction in predictions]) for gt in ground_truths])
# ---------------------------------------------------------------- end VERBATIM


def official_clean(reply: str, category: int, options: dict | None) -> str:
    """get_hf_answers post-processing (batch size 1), unchanged in effect; an empty reply stays empty."""
    answer = reply.replace('\\"', "'").strip()
    lines = [w.strip() for w in answer.split('\n') if not w.strip().isspace()]
    answer = lines[0] if lines else ""
    if category == 5:
        answer = answer.lower().strip()
        return options["a"] if "(a)" in answer else options["b"]
    return answer.lower().replace('(a)', '').replace('(b)', '').replace('a)', '').replace('b)', '') \
        .replace('answer:', '').strip()


def official_score(pred: str, gold, category: int) -> float:
    """eval_question_answering, one row."""
    answer = str(gold)
    if category == 3:
        answer = answer.split(';')[0].strip()
    if category in [2, 3, 4]:
        return float(f1_score(pred, answer))
    if category in [1]:
        return float(f1(pred, answer))
    return 1.0 if ('no information available' in pred.lower() or 'not mentioned' in pred.lower()) else 0.0


def strict_cat5(reply: str, options: dict) -> float:
    """Registered stricter reading: right only if the reply picks exactly the no-information option by
    letter, or picks no letter and abstains in words."""
    low = reply.lower()
    has_a, has_b = "(a)" in low, "(b)" in low
    right = "a" if options["a"] == P.NO_INFO else "b"
    if has_a != has_b:
        return 1.0 if (has_a and right == "a") or (has_b and right == "b") else 0.0
    if not has_a and not has_b and ABSTAIN.search(low):
        return 1.0
    return 0.0


def load_rows(runs: Path, prefix: str) -> list[dict] | None:
    files = sorted(runs.glob(f"{prefix}.jsonl")) + sorted(runs.glob(f"{prefix}.part*.jsonl"))
    if not files:
        return None
    rows = []
    for f in files:
        rows += [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows


def score_locomo(data: Path, rows: list[dict]) -> dict:
    lc = json.loads((data / "locomo10.json").read_text(encoding="utf-8"))
    gold = {}
    for c in lc:
        for i, qa in enumerate(c["qa"]):
            gold[f"{c['sample_id']}#{i}"] = (qa, P.cat5_options(c["sample_id"], i, qa) if qa["category"] == 5 else None)
    per = {}
    for r in rows:
        qa, opts = gold[r["qid"]]
        cat = qa["category"]
        pred = official_clean(r["reply"], cat, opts)
        s = official_score(pred, qa.get("answer", ""), cat)
        abst = bool(ABSTAIN.search(r["reply"].lower()))
        per[r["qid"]] = {"cat": cat, "f1": s, "abstain": abst,
                         "strict5": strict_cat5(r["reply"], opts) if cat == 5 else None}
    missing = sorted(set(gold) - set(per))
    out = {"questions": len(per), "missing": len(missing)}
    for cat in (1, 2, 3, 4, 5):
        v = [x["f1"] for x in per.values() if x["cat"] == cat]
        out[f"cat{cat}_n"] = len(v)
        out[f"cat{cat}_f1"] = round(100 * sum(v) / len(v), 2) if v else None
    c14 = [x for x in per.values() if x["cat"] in (1, 2, 3, 4)]
    out["cat1to4_n"] = len(c14)
    out["cat1to4_f1"] = round(100 * sum(x["f1"] for x in c14) / len(c14), 2) if c14 else None
    out["cat1to4_abstain"] = sum(x["abstain"] for x in c14)
    out["cat1to4_confident_wrong"] = sum((not x["abstain"]) and x["f1"] == 0 for x in c14)
    out["cat1to4_half_right"] = sum(x["f1"] >= 0.5 for x in c14)
    c5 = [x for x in per.values() if x["cat"] == 5]
    out["cat5_strict_right"] = int(sum(x["strict5"] for x in c5))
    out["cat5_official_right"] = int(sum(x["f1"] for x in c5))
    return {"summary": out, "per": per}


def boot_diff(a: dict, b: dict, cats=(1, 2, 3, 4)) -> dict:
    ids = sorted(q for q in a if q in b and a[q]["cat"] in cats)
    da = np.array([a[q]["f1"] for q in ids])
    db = np.array([b[q]["f1"] for q in ids])
    d = da - db
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(d), size=(BOOT, len(d)))
    means = d[idx].mean(axis=1)
    return {"n": len(ids), "diff": round(100 * float(d.mean()), 2),
            "ci95": [round(100 * float(np.percentile(means, 2.5)), 2), round(100 * float(np.percentile(means, 97.5)), 2)]}


# ---------------------------------------------------------------- general (rules fixed before any run)
MMLU_FIRST = re.compile(r"(?i:answer(?: is)?|option)\s*[:\-]?\s*\(?([ABCD])(?![A-Za-z])")
MMLU_ANY = re.compile(r"(?<![A-Za-z])([ABCD])(?![A-Za-z])")
NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def mmlu_pick(reply: str) -> str | None:
    """'answer is X' / 'Answer: X' / 'option X' first; else the first capital A-D standing alone."""
    m = MMLU_FIRST.search(reply) or MMLU_ANY.search(reply)
    return m.group(1) if m else None


def gsm_pick(reply: str) -> float | None:
    m = re.findall(r"(?i)answer is\s*[:\$]?\s*(-?\d[\d,]*(?:\.\d+)?)", reply)
    nums = m or NUM.findall(reply)
    if not nums:
        return None
    try:
        return float(nums[-1].replace(",", ""))
    except ValueError:
        return None


def score_general(data: Path, task: str, rows: list[dict]) -> dict:
    items = {json.loads(x)["qid"]: json.loads(x) for x in (data / f"{task}300.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()}
    per = {}
    for r in rows:
        g = items[r["qid"]]["gold"]
        if task == "mmlu":
            ok = mmlu_pick(r["reply"]) == g
        else:
            p = gsm_pick(r["reply"])
            ok = p is not None and abs(p - float(g)) < 1e-6
        per[r["qid"]] = int(ok)
    return {"summary": {"n": len(per), "right": sum(per.values()),
                        "pct": round(100 * sum(per.values()) / len(per), 2) if per else None}, "per": per}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--primary", default="P")
    ap.add_argument("--baselines", default="T", help="comma list: same-harness plain arms that count for M1/M3/M4")
    ap.add_argument("--report", default="", help="comma list: arms scored and printed but not in the marks")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    data, runs = Path(a.data), Path(a.runs)
    base = [x for x in a.baselines.split(",") if x]
    names = [a.primary] + base + [x for x in a.report.split(",") if x]
    res: dict = {}
    for n in names:
        res[n] = {}
        rows = load_rows(runs, f"locomo_{n}")
        if rows is not None:
            res[n]["locomo"] = score_locomo(data, rows)
        for task in ("mmlu", "gsm8k"):
            rows = load_rows(runs, f"{task}_{n}")
            if rows is not None:
                res[n][task] = score_general(data, task, rows)
        line = {"arm": n}
        for k, v in res[n].items():
            line[k] = v["summary"]
        print(json.dumps(line), flush=True)

    marks: dict = {}
    p = res.get(a.primary, {})
    if "locomo" in p:
        m1 = {}
        for b in base:
            if "locomo" in res.get(b, {}):
                bd = boot_diff(p["locomo"]["per"], res[b]["locomo"]["per"])
                bd["pass"] = bd["diff"] >= 3.0 and bd["ci95"][0] > 0
                m1[b] = bd
        marks["M1"] = {"per_baseline": m1, "pass": bool(m1) and all(v["pass"] for v in m1.values())}
        m3 = {}
        for b in base:
            if "locomo" in res.get(b, {}):
                pw = p["locomo"]["summary"]["cat1to4_confident_wrong"]
                bw = res[b]["locomo"]["summary"]["cat1to4_confident_wrong"]
                m3[b] = {"P": pw, "base": bw, "pass": pw < bw}
        marks["M3"] = {"per_baseline": m3, "pass": bool(m3) and all(v["pass"] for v in m3.values())}
    m4 = {}
    for task in ("mmlu", "gsm8k"):
        if task in p and "T" in res and task in res["T"]:
            pp, tt = p[task]["summary"]["pct"], res["T"][task]["summary"]["pct"]
            m4[task] = {"P": pp, "T": tt, "pass": pp >= tt - 3.0}
    if m4:
        marks["M4"] = {"per_task": m4, "pass": all(v["pass"] for v in m4.values()) and len(m4) == 2}
    print(json.dumps({"marks": marks}), flush=True)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    slim = {n: {k: v["summary"] for k, v in r.items()} for n, r in res.items()}
    (out / "score.json").write_text(json.dumps({"arms": slim, "marks": marks}, indent=1), encoding="utf-8")
    per = {n: {k: v["per"] for k, v in r.items()} for n, r in res.items()}
    (out / "per_question.json").write_text(json.dumps(per), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
