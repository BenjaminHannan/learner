"""The morning gate. Replaces sleepb's ARC-Easy slice (there is no ARC file on the Mac).

(a) GENERAL: 40 fixed simple questions (facts and arithmetic). The base model's answers are recorded the first time; the adapter may not
    lose more than HARM_MAX points (percentage points of the 40).
(b) RECALL: held-out cards of the night (never trained on): closed-book question -> answer. quiz = recall %.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence

HARM_MAX = 3.0
GATE_SYS = "Answer with just the answer, as briefly as possible."

# (question, [accepted answers: lowercase substrings of a correct reply])
GENERAL_QA: List[tuple] = [
    ("What is the capital of France?", ["paris"]),
    ("What is the capital of Japan?", ["tokyo"]),
    ("What is the capital of Italy?", ["rome"]),
    ("What is the capital of Canada?", ["ottawa"]),
    ("What is the capital of Egypt?", ["cairo"]),
    ("Which planet is closest to the Sun?", ["mercury"]),
    ("Which planet is known as the Red Planet?", ["mars"]),
    ("What is the largest planet in our solar system?", ["jupiter"]),
    ("What gas do plants take in from the air for photosynthesis?", ["carbon dioxide", "co2"]),
    ("What is the chemical symbol for water?", ["h2o"]),
    ("What is the chemical symbol for gold?", ["au"]),
    ("At what Celsius temperature does water freeze at sea level?", ["0", "zero"]),
    ("At what Celsius temperature does water boil at sea level?", ["100", "hundred"]),
    ("How many days are in a week?", ["7", "seven"]),
    ("How many months are in a year?", ["12", "twelve"]),
    ("How many minutes are in an hour?", ["60", "sixty"]),
    ("How many sides does a triangle have?", ["3", "three"]),
    ("How many sides does a hexagon have?", ["6", "six"]),
    ("What is 7 + 8?", ["15", "fifteen"]),
    ("What is 12 - 5?", ["7", "seven"]),
    ("What is 6 * 7?", ["42", "forty-two", "forty two"]),
    ("What is 9 * 9?", ["81", "eighty-one", "eighty one"]),
    ("What is 100 / 4?", ["25", "twenty-five", "twenty five"]),
    ("What is 15 + 27?", ["42", "forty-two", "forty two"]),
    ("What is 3 squared?", ["9", "nine"]),
    ("What is the square root of 64?", ["8", "eight"]),
    ("What is half of 50?", ["25", "twenty-five", "twenty five"]),
    ("What is 20% of 50?", ["10", "ten"]),
    ("Who wrote the play Romeo and Juliet?", ["shakespeare"]),
    ("What language is spoken in Brazil?", ["portuguese"]),
    ("What is the largest ocean on Earth?", ["pacific"]),
    ("What is the largest mammal?", ["blue whale", "whale"]),
    ("What is the opposite of hot?", ["cold", "cool"]),
    ("What color do you get by mixing blue and yellow?", ["green"]),
    ("What is the first month of the year?", ["january"]),
    ("Which continent is Egypt in?", ["africa"]),
    ("What do bees make?", ["honey"]),
    ("How many legs does a spider have?", ["8", "eight"]),
    ("What is the freezing point of water in Fahrenheit?", ["32", "thirty-two", "thirty two"]),
    ("What is the plural of 'mouse' (the animal)?", ["mice"]),
]


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\-. ]+", " ", str(s).lower())).strip()


def correct(reply: str, accepted: Sequence[str]) -> bool:
    r = normalize(reply)
    toks = set(re.findall(r"[a-z0-9\-]+", r))
    for a in accepted:
        a = normalize(a)
        if a.isdigit():
            if a in re.findall(r"\d+", r):   # whole number, not a substring of a larger one
                return True
        elif a in r:
            return True
        elif a in toks:
            return True
    return False


def gate_questions(n: int = 40) -> List[tuple]:
    """The first n gate questions, evenly spread over the list (n=40: all; the CPU profile uses 20)."""
    if n >= len(GENERAL_QA):
        return list(GENERAL_QA)
    return [GENERAL_QA[int(i * len(GENERAL_QA) / n)] for i in range(n)]


def general_prompts(R, n: int = 40) -> List[str]:
    return [R.render(GATE_SYS, q) for q, _ in gate_questions(n)]


def score_general(backend, R, adapter: bool, max_tokens: int = 24, n: int = 40) -> List[bool]:
    """Per-question correctness (generation in backend.gen_batch batches)."""
    ps = general_prompts(R, n)
    out: List[str] = []
    for i in range(0, len(ps), backend.gen_batch):
        out += backend.generate(ps[i:i + backend.gen_batch], max_tokens, 0.0, adapter)
    return [correct(o, a) for o, (_, a) in zip(out, gate_questions(n))]


def pct(flags: Sequence[bool]) -> Optional[float]:
    return 100.0 * sum(flags) / len(flags) if flags else None


def judge(base_flags: Sequence[bool], adapter_flags: Sequence[bool], harm_max: float = HARM_MAX) -> Dict:
    """harm = base points - adapter points (positive = the adapter got worse). Fails when harm > harm_max."""
    b, a = pct(base_flags), pct(adapter_flags)
    harm = (b - a) if b is not None and a is not None else 0.0
    return {"general_base": b, "general": a, "harm": harm, "harm_ok": harm <= harm_max + 1e-9}


def score_recall(backend, R, cards: Sequence[dict], adapter: bool = True, sys_prompt: str = "Answer with just the name.",
                 max_tokens: int = 16) -> Dict:
    """cards: held-out {'q','a','dir'} rows. Closed-book, no notes. Returns recall % overall and by direction ('forward' / 'reverse')."""
    if not cards:
        return {"recall": None, "n": 0, "by_dir": {}}
    ps = [R.render(sys_prompt, c["q"]) for c in cards]
    out: List[str] = []
    for i in range(0, len(ps), backend.gen_batch):
        out += backend.generate(ps[i:i + backend.gen_batch], max_tokens, 0.0, adapter)
    flags = [c["a"].lower() in o.lower() for c, o in zip(cards, out)]
    by: Dict[str, List[bool]] = {}
    for c, f in zip(cards, flags):
        by.setdefault(c.get("dir", "forward"), []).append(f)
    return {"recall": pct(flags), "n": len(flags), "by_dir": {k: pct(v) for k, v in by.items()},
            "samples": [{"q": c["q"], "a": c["a"], "out": o[:60]} for c, o in list(zip(cards, out))[:3]]}
