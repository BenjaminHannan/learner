#!/usr/bin/env python3
"""rsn-299 "think, then answer": the 1B writes its steps; an exact tool does the arithmetic,
counting and comparing (scripts/claude_rsn299_tool.py).

Arms (same model, same few-shot examples, same greedy decoding, same token budget):
  P  plain: the 1B writes its steps and does its own arithmetic ("3 x 12 = 36").
  T  tool:  every calculation is written as <<expr>>; generation stops at ">>", the tool
            computes it exactly and "=<result>" is appended; the model then continues.
Both end with a line "Answer: ...". Saying "I'm not sure" is allowed and scored separately.

  python claude_rsn299_run.py run   --arm P|T --model DIR --items items.jsonl --out out.jsonl
  python claude_rsn299_run.py score --items items.jsonl --p out-P.jsonl --t out-T.jsonl
  python claude_rsn299_run.py mock  --items items.jsonl        (no model; code smoke test)

Greedy decoding, bf16 on CUDA if present, else float32 on CPU. Writes replies and scores.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn299_tool as TOOL  # noqa: E402

MAX_NEW = 420          # total new tokens per question, tool results not counted
MAX_CALLS = 16

HEAD_T = ("Solve each question step by step. Write every calculation inside << >> and a calculator "
          "fills in the exact result after it. The calculator knows + - * / ( ), round(x, 2), ceil(x), "
          "floor(x), min(...), max(...), t(\"9:47\") for a clock time in minutes, hhmm(minutes) to turn "
          "minutes back into a clock time, day(\"Tuesday\") and dayname(n) for weekdays, count(\"a, b, c\") "
          "to count items, letters(\"word\") to count letters, and biggest(\"A\", 3, \"B\", 4) or "
          "smallest(...) to compare. Never do arithmetic in your head. End with one line \"Answer: ...\". "
          "If a needed fact is missing, write \"Answer: I'm not sure\" and say what is missing.\n\n")
HEAD_P = ("Solve each question step by step. Show each calculation. End with one line \"Answer: ...\". "
          "If a needed fact is missing, write \"Answer: I'm not sure\" and say what is missing.\n\n")

# the same six worked examples for both arms; T writes <<expr>>=result, P writes the arithmetic out
EXAMPLES = [
    ("A café sells muffins for 2.40 each and coffee for 3.10. Tom buys 3 muffins and 2 coffees and pays "
     "with a 20 note. How much change does he get?",
     [("Muffins cost ", "3*2.40", "7.2", "."), ("Coffees cost ", "2*3.10", "6.2", "."),
      ("Total is ", "7.2+6.2", "13.4", "."), ("Change is ", "20-13.4", "6.6", ".")], "6.6"),
    ("A bus leaves at 8:52 and the trip takes 1 h 25 min. What time does it arrive?",
     [("The trip is ", "60+25", "85", " minutes."), ("Arrival is ", "hhmm(t(\"8:52\")+85)", "10:17", ".")],
     "10:17"),
    ("My shopping list: milk, rice, apples, bread, pears, cheese, plums. How many of these are fruits?",
     [("The fruits are apples, pears, plums. Counting them: ", "count(\"apples, pears, plums\")", "3", ".")],
     "3"),
    ("Brand Kello costs 3.60 for 450 g and brand Moss costs 2.90 for 350 g. Which is cheaper per gram?",
     [("Kello per gram is ", "3.60/450", "0.008", "."), ("Moss per gram is ", "2.90/350", "0.0083", "."),
      ("The cheaper one is ", "smallest(\"Kello\", 3.60/450, \"Moss\", 2.90/350)", "Kello", ".")], "Kello"),
    ("47 guests are coming and each table seats 6. How many tables do we need?",
     [("Tables needed is ", "ceil(47/6)", "8", ".")], "8"),
    ("A lamp costs 24 and a rug costs more than the lamp. How much do both cost together?",
     [("The rug's price is never given, so the total can't be worked out.", None, None, "")],
     "I'm not sure (the rug's price is missing)"),
]


def _ex_text(arm):
    out = []
    for q, steps, ans in EXAMPLES:
        lines = [f"Question: {q}", "Steps:"]
        for pre, expr, res, post in steps:
            if expr is None:
                lines.append(pre)
            elif arm == "T":
                lines.append(f"{pre}<<{expr}>>={res}{post}")
            else:
                shown = expr
                shown = re.sub(r'hhmm\(t\("(\d+:\d+)"\)\+(\d+)\)', r"\1 plus \2 minutes", shown)
                shown = re.sub(r'count\("([^"]*)"\)', r"\1", shown)
                shown = re.sub(r'smallest\("(\w+)", ([^,]+), "(\w+)", ([^)]+)\)', r"the lower of \1 and \3", shown)
                shown = re.sub(r"ceil\((\d+)/(\d+)\)", r"\1/\2 rounded up", shown)
                lines.append(f"{pre}{shown} = {res}{post}")
        lines.append(f"Answer: {ans}")
        out.append("\n".join(lines))
    return "\n\n".join(out) + "\n\n"


def prompt(arm: str, question: str) -> str:
    return (HEAD_T if arm == "T" else HEAD_P) + _ex_text(arm) + f"Question: {question}\nSteps:\n"


# ----------------------------------------------------------------------------------------
# generation
# ----------------------------------------------------------------------------------------
def load(model_dir):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if dev == "cuda" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(model_dir, torch_dtype=dtype,
                                                 trust_remote_code=True).to(dev).eval()
    return tok, model, dev


def _gen(tok, model, dev, text, max_new, stops):
    import torch
    from transformers import StoppingCriteria, StoppingCriteriaList
    ids = tok(text, return_tensors="pt").input_ids.to(dev)
    n0 = ids.shape[1]

    class Stop(StoppingCriteria):
        def __call__(self, input_ids, scores, **kw):
            tail = tok.decode(input_ids[0, n0:][-12:], skip_special_tokens=True)
            return any(s in tail for s in stops)       # a ">>" may be glued to the next token

    with torch.no_grad():
        out = model.generate(ids, max_new_tokens=max_new, do_sample=False,
                             stopping_criteria=StoppingCriteriaList([Stop()]),
                             pad_token_id=tok.pad_token_id or tok.eos_token_id)
    new = out[0, n0:]
    return tok.decode(new, skip_special_tokens=True), len(new)


def _cut(s: str) -> str:
    """keep the steps up to and including the first Answer: line; drop a started next question."""
    s = s.split("\nQuestion:")[0]
    m = re.search(r"Answer:[^\n]*", s)
    return s[:m.end()] if m else s


def solve(arm, question, gen):
    """gen(text, max_new, stops) -> (new_text, n_tokens). Returns (steps text, calls)."""
    base = prompt(arm, question)
    body, used, calls = "", 0, []
    while used < MAX_NEW:
        stops = [">>", "\nQuestion:"] if arm == "T" else ["\nQuestion:"]
        new, n = gen(base + body, MAX_NEW - used, stops)
        used += n
        if arm == "T" and ">>" in new:
            new = new[:new.index(">>") + 2]            # drop anything the model wrote after the call
        body += new
        if re.search(r"Answer:[^\n]*\n", body) or "\nQuestion:" in body:
            break
        m = re.search(r"<<([^<>]*)>>$", body)
        if arm == "T" and m and len(calls) < MAX_CALLS:
            res = TOOL.calc(m.group(1))
            calls.append({"expr": m.group(1), "result": res})
            body += "=" + res
            continue
        break
    body = _cut(body)
    # a <<expr>> in the Answer line is computed too
    am = re.search(r"Answer:\s*(.*)", body)
    if arm == "T" and am and "<<" in am.group(1):
        m = re.search(r"<<([^<>]*)>>", am.group(1))
        if m:
            res = TOOL.calc(m.group(1))
            calls.append({"expr": m.group(1), "result": res})
            body = body[:am.start(1)] + res
    return body, calls


# ----------------------------------------------------------------------------------------
# scoring
# ----------------------------------------------------------------------------------------
UNSURE = re.compile(r"not sure|don'?t know|do not know|can'?t (be )?(tell|work|know|say|determine)|cannot "
                    r"(be )?(tell|work|know|say|determine)|not enough|missing|isn'?t given|not given", re.I)
NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
TIME = re.compile(r"\b(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?", re.I)


def answer_line(steps: str) -> str:
    m = re.findall(r"Answer:\s*([^\n]*)", steps)
    return m[-1].strip() if m else ""


def judge(gold: dict, ans: str) -> str:
    """-> right | unsure | wrong | none"""
    if not ans:
        return "none"
    unsure = bool(UNSURE.search(ans))
    t = gold["type"]
    if t == "unsure":
        return "right" if unsure else "wrong"
    if unsure:
        return "unsure"
    if t == "number":
        nums = [float(x.replace(",", "")) for x in NUM.findall(ans)]
        if not nums:
            return "wrong"
        return "right" if abs(nums[0] - float(gold["value"])) <= 0.011 else "wrong"
    if t == "time":
        m = TIME.search(ans)
        if not m:
            return "wrong"
        h, mi, ap = int(m.group(1)), int(m.group(2)), (m.group(3) or "").lower().replace(".", "")
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        return "right" if f"{h:02d}:{mi:02d}" == gold["value"] else "wrong"
    norm = lambda s: re.sub(r"[^a-z0-9 ]", " ", s.casefold()).split()
    a = " " + " ".join(norm(ans)) + " "
    for g in [gold["value"]] + list(gold.get("accept") or []):
        if " " + " ".join(norm(g)) + " " in a:
            return "right"
    return "wrong"


EQ = re.compile(r"(-?\d+(?:\.\d+)?)\s*([+\-x×*/÷])\s*(-?\d+(?:\.\d+)?)\s*=\s*(-?\d+(?:\.\d+)?)")


def arith_errors(steps: str) -> int:
    """model-written 'a op b = c' in the steps that are wrong (tool-filled <<e>>=r are exact and skipped)."""
    text = re.sub(r"<<[^<>]*>>=\S+", " ", steps)
    bad = 0
    for a, o, b, c in EQ.findall(text):
        a, b, c = float(a), float(b), float(c)
        v = {"+": a + b, "-": a - b, "x": a * b, "×": a * b, "*": a * b,
             "/": a / b if b else None, "÷": a / b if b else None}[o]
        if v is None or abs(v - c) > max(0.011, 0.005 * abs(v)):
            bad += 1
    return bad


def score(items, rows):
    by = {r["id"]: r for r in rows}
    tot = {"right": 0, "unsure": 0, "wrong": 0, "none": 0, "arith_errors": 0, "n": 0}
    cats: dict = {}
    for it in items:
        r = by[it["id"]]
        v = judge(it["gold"], answer_line(r["steps"]))
        e = arith_errors(r["steps"])
        for d in (tot, cats.setdefault(it["category"], {"right": 0, "unsure": 0, "wrong": 0, "none": 0,
                                                         "arith_errors": 0, "n": 0})):
            d[v] += 1; d["arith_errors"] += e; d["n"] += 1
    return {"total": tot, "by_category": cats}


# ----------------------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run"); r.add_argument("--arm", choices=["P", "T"], required=True)
    r.add_argument("--model", required=True); r.add_argument("--items", required=True)
    r.add_argument("--out", required=True)
    s = sp.add_parser("score"); s.add_argument("--items", required=True)
    s.add_argument("--p", required=True); s.add_argument("--t", required=True)
    s.add_argument("--out", default=None)
    m = sp.add_parser("mock"); m.add_argument("--items", required=True)
    a = p.parse_args()
    items = [json.loads(l) for l in open(a.items) if l.strip()]
    if a.cmd == "run":
        tok, model, dev = load(a.model)
        gen = lambda text, mx, stops: _gen(tok, model, dev, text, mx, stops)
        with open(a.out, "w") as fh:
            for it in items:
                t0 = time.time()
                steps, calls = solve(a.arm, it["question"], gen)
                fh.write(json.dumps({"id": it["id"], "arm": a.arm, "steps": steps, "calls": calls,
                                     "sec": round(time.time() - t0, 2)}) + "\n"); fh.flush()
        rows = [json.loads(l) for l in open(a.out)]
        print(json.dumps(score(items, rows)["total"]))
    elif a.cmd == "score":
        sp_ = score(items, [json.loads(l) for l in open(a.p)])
        st = score(items, [json.loads(l) for l in open(a.t)])
        n = sp_["total"]["n"]
        res = {"P": sp_, "T": st, "n": n,
               "P299.1_T_right_minus_P_right": st["total"]["right"] - sp_["total"]["right"],
               "P299.1": st["total"]["right"] - sp_["total"]["right"] >= -(-20 * n // 100),
               "P299.2": st["total"]["arith_errors"] == 0,
               "P299.3": st["total"]["wrong"] <= sp_["total"]["wrong"]}
        s_ = json.dumps(res, indent=1)
        print(s_)
        if a.out:
            Path(a.out).write_text(s_)
    else:   # mock: a fake model that writes one tool call and answers with its result
        def fake(text, mx, stops):
            if text.endswith("Steps:\n"):
                return "The result is <<2+3>>", 8
            if text.rstrip().endswith("=5"):
                return ".\nAnswer: 5\n", 5
            return "Answer: I'm not sure\n", 5
        rows = []
        for it in items:
            steps, calls = solve("T", it["question"], fake)
            rows.append({"id": it["id"], "steps": steps, "calls": calls})
        print(rows[0]["steps"]); print(json.dumps(score(items, rows)["total"]))
        print(prompt("P", "Q?")[-900:])


if __name__ == "__main__":
    main()
