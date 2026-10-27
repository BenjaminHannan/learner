#!/usr/bin/env python3
"""rsn-299 "think, then answer": the 1B writes its steps; an exact tool does the arithmetic,
counting and comparing (scripts/claude_rsn299_tool.py).

Arms (same model, same few-shot examples, same greedy decoding, same token budget):
  P  plain: the 1B writes its steps and does its own arithmetic ("3 x 12 = 36").
  T  tool:  the same prompt, word for word. Whenever the model has written a calculation followed
            by "=", generation stops, the exact calculator (claude_rsn299_tool) writes the result,
            and the model continues. So the only difference between the arms is who does the sums.
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

HEAD = ("Solve each question step by step. Write each calculation as a short sum ending in \" = \", "
        "for example 3*2.40 = 7.2, 19:40 + 75 = 20:55 (a clock time plus minutes), 17:10 - 9:30 = 460 "
        "(minutes between two clock times), Monday + 9 = Wednesday (days after a weekday), "
        "ceil(47/6) = 8 (round up), floor(50/25) = 2 (round down). End with one line \"Answer: ...\". "
        "If a needed fact is missing, write \"Answer: I'm not sure\" and say what is missing.\n\n")

# the same worked examples, word for word, for both arms
EXAMPLES = [
    ("A café sells muffins for 2.40 each and coffee for 3.10. Tom buys 3 muffins and 2 coffees and pays "
     "with a 20 note. How much change does he get?",
     ["Muffins cost 3*2.40 = 7.2.", "Coffees cost 2*3.10 = 6.2.", "Total is 7.2 + 6.2 = 13.4.",
      "Change is 20 - 13.4 = 6.6."], "6.6"),
    ("A recipe for 4 people needs 250 g of rice. How much rice for 6 people?",
     ["Rice per person is 250/4 = 62.5 g.", "For 6 people it is 62.5*6 = 375 g."], "375"),
    ("A bus leaves at 8:52 and the trip takes 1 h 25 min. What time does it arrive?",
     ["The trip is 60 + 25 = 85 minutes.", "Arrival is 8:52 + 85 = 10:17."], "10:17"),
    ("The shop is open from 9:30 to 17:10. How many minutes is it open?",
     ["Open time is 17:10 - 9:30 = 460 minutes."], "460"),
    ("Today is Monday. What day will it be 9 days from now?",
     ["9 days after Monday is Monday + 9 = Wednesday."], "Wednesday"),
    ("My shopping list: milk, rice, apples, bread, pears, cheese, plums. How many of these are fruits?",
     ["Going through the list: milk no, rice no, apples yes, bread no, pears yes, cheese no, plums yes.",
      "The fruits are apples, pears and plums, so 1 + 1 + 1 = 3."], "3"),
    ("Brand Kello costs 3.60 for 450 g and brand Moss costs 2.90 for 350 g. Which is cheaper per gram?",
     ["Kello per gram is 3.60/450 = 0.008.", "Moss per gram is 2.90/350 = 0.0083.",
      "The smaller price per gram is Kello's, so Kello is cheaper."], "Kello"),
    ("I have 40 to spend. Each kit costs 9 and shipping is 3 per kit. How many kits can I buy?",
     ["One kit with shipping is 9 + 3 = 12.", "Kits I can buy is floor(40/12) = 3."], "3"),
    ("A lamp costs 24 and a rug costs more than the lamp. How much do both cost together?",
     ["The rug's price is never given, so the total can't be worked out."],
     "I'm not sure (the rug's price is missing)"),
    ("Parking is 3 an hour for cars. We come with one car and one van for 2 hours. What do we pay?",
     ["The price for a van is never given, so the total can't be worked out."],
     "I'm not sure (the van price is missing)"),
]


def _ex_text():
    out = []
    for q, steps, ans in EXAMPLES:
        out.append("\n".join([f"Question: {q}", "Steps:"] + steps + [f"Answer: {ans}"]))
    return "\n\n".join(out) + "\n\n"


def prompt(arm: str, question: str) -> str:
    """the prompt is identical for both arms; only T gets the calculator."""
    return HEAD + _ex_text() + f"Question: {question}\nSteps:\n"


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


# the calculation at the end of the text, just before "=": numbers, clock times, weekdays,
# operators, brackets, and ceil/floor/round/min/max
_TAIL = re.compile(r"((?:ceil|floor|round|min|max|abs)?\(?[\d(][\d\s.:+\-*/×÷(),]*|(?:Monday|Tuesday|Wednesday|"
                   r"Thursday|Friday|Saturday|Sunday)\s*[+\-]\s*\d+)\s*=\s?$", re.I)


def _expr_before_eq(body: str):
    line = body.rsplit("\n", 1)[-1]
    m = _TAIL.search(line)
    if not m:
        return None
    e = m.group(1).strip()
    # widen to a function call that opened before the match, e.g. "floor(40/12) ="
    fm = re.search(r"((?:ceil|floor|round|min|max|abs)\([^()]*\))\s*=\s?$", line)
    if fm:
        e = fm.group(1)
    if not re.search(r"[+\-*/×÷]|^(ceil|floor|round|min|max|abs)\(", e, re.I) or not re.search(r"\d", e):
        return None
    return e


def solve(arm, question, gen):
    """gen(text, max_new, stops) -> (new_text, n_tokens). Returns (steps text, calls).
    T: whenever the model has written a calculation followed by "=", generation stops, the
    calculator computes it exactly and writes the result; the model then continues."""
    base = prompt(arm, question)
    body, used, calls = "", 0, []
    while used < MAX_NEW:
        stops = ["=", "\nQuestion:"] if arm == "T" else ["\nQuestion:"]
        new, n = gen(base + body, MAX_NEW - used, stops)
        used += n
        if arm == "T" and "=" in new:
            new = new[:new.index("=") + 1]              # drop anything the model wrote after "="
        body += new
        if re.search(r"Answer:[^\n]*\n", body) or "\nQuestion:" in body:
            break
        if arm == "T" and body.endswith("=") and len(calls) < MAX_CALLS:
            e = _expr_before_eq(body)
            res = TOOL.calc(e) if e else "error"
            if e and res != "error":
                calls.append({"expr": e, "result": res})
                body += " " + res
            elif not e:
                pass                                     # not a calculation: let the model go on
            if n == 0:
                break
            continue
        break
    return _cut(body), calls


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


EQ = re.compile(r"(?<![\d:.*/+×÷x\-])(?<![*/+×÷x\-] )(-?\d+(?:\.\d+)?)\s*([+\-x×*/÷])\s*(-?\d+(?:\.\d+)?)\s*=\s*(-?\d+(?:\.\d+)?)(?![\d:])")


def arith_errors(steps: str) -> int:
    """'a op b = c' lines in the shown steps that are wrong (calculator-filled ones are exact)."""
    text = steps
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
    else:   # mock: a fake model that writes one sum and lets the calculator finish it
        def fake(text, mx, stops):
            if text.endswith("Steps:\n"):
                return "Muffins cost 3*2.40 =", 8
            if text.endswith("= 7.2"):
                return ".\nAnswer: 7.2\n", 5
            return " 9.\nAnswer: 9\n", 5
        rows = []
        for arm in ("T", "P"):
            steps, calls = solve(arm, "Q?", fake)
            print(arm, repr(steps), calls)
        for e in ["Arrival is 8:52 + 85 =", "Kits is floor(40/12) =", "9 days after is Monday + 9 =", "x is big =",
                  "Total is 7.2 + 6.2 =", "Each pays (67.50 + 9)/3 ="]:
            print(repr(e), "->", _expr_before_eq(e), TOOL.calc(_expr_before_eq(e)) if _expr_before_eq(e) else "")
        print(prompt("P", "Q?") == prompt("T", "Q?"))


if __name__ == "__main__":
    main()
