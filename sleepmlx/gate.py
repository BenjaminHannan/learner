"""The morning gate. Replaces sleepb's ARC-Easy slice (there is no ARC file on the Mac).

(a) GENERAL: 40 fixed simple questions (facts and arithmetic). The base model's answers are recorded the first time; the adapter may not
    lose more than HARM_MAX points (percentage points of the 40).
(b) RECALL: held-out cards of the night (never trained on): closed-book question -> answer. quiz = recall %.
    This is the one quiz metric on the Mac (the old -NLL x 100 of sleepmode/mlx_worker.py is not used by this trainer).

Grading is strict (see `correct` / `recall_hit`): only the reply's first line counts, at most HEAD_WORDS words of it, and an answer must
appear there as a whole word or phrase (no substrings: "au" is not found in "sauce", "42" not in "142"). A reply that names two different
numbers when one is asked for counts as wrong. The night is kept only when (see `decide`):
    1. general harm <= harm_max (the base model's own score on the 40 questions is the reference), AND
    2. held-out recall did not drop against the adapter the night started from (the committed one), AND
    3. it rose by at least `min_gain` held-out cards (a night that taught nothing measurable is not worth the risk), AND
    4. there was at least one held-out card to measure it on.
Anything else undoes the night: the committed adapter stays.
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


HEAD_WORDS = 12          # only this many words of the reply's first line are graded
MIN_GAIN = 1             # held-out cards the night must add over the adapter it started from


GRADER = "strict-2"   # stored with recorded scores: a score from another grader is not compared with this one
_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹", "01234567890123456789")


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\- ]+", " ", str(s).translate(_SUB).lower().replace("'s ", " "))).strip()


_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)


def head(reply: str, words: int = HEAD_WORDS) -> str:
    """The graded part of a reply: think blocks dropped, first non-empty line, first `words` words, normalized."""
    t = _THINK.sub(" ", str(reply or ""))
    t = t.split("</think>")[-1]
    lines = [x for x in t.splitlines() if normalize(x)]
    # a label-only first line ("**Answer:**") is not the answer: take the next line
    while len(lines) > 1 and lines[0].strip().strip("*_# ").endswith(":") and len(normalize(lines[0]).split()) <= 3:
        lines = lines[1:]
    return " ".join(normalize(lines[0] if lines else "").split()[:words])


def has_phrase(text: str, phrase: str) -> bool:
    """phrase (normalized) occurs in normalized text as whole words."""
    p = normalize(phrase)
    return bool(p) and re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", text) is not None


_NUM = re.compile(r"(?<![a-z0-9.])\d+(?![a-z0-9])")


def correct(reply: str, accepted: Sequence[str], question: str = "") -> bool:
    """Strict: an accepted answer appears as a whole word/phrase in the head of the reply. When the accepted answers are numbers, the
    first number of the head that is not in the question must be an accepted one (a hedge such as "7 or 8" for 8 is wrong, while
    "7 + 8 = 15" or "100 C (212 F)" are right)."""
    r = head(reply)
    nums_ok = {normalize(a) for a in accepted if normalize(a).isdigit()}
    if nums_ok:
        asked = set(_NUM.findall(normalize(question)))
        found = [x for x in _NUM.findall(r) if x not in asked]
        if found and found[0] not in nums_ok:
            return False
        if len(set(found)) > 1 and re.search(r"\d+ (?:or|to) \d+", r):   # "7 or 8", "7 to 8": a hedge
            return False
    return any(has_phrase(r, a) for a in accepted)


def recall_hit(answer: str, reply: str) -> bool:
    """A held-out card is answered when its answer (a name) appears as a whole phrase in the head of the reply."""
    return has_phrase(head(reply), answer)


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
    return [correct(o, a, q) for o, (q, a) in zip(out, gate_questions(n))]


def pct(flags: Sequence[bool]) -> Optional[float]:
    return 100.0 * sum(flags) / len(flags) if flags else None


def judge(base_flags: Sequence[bool], adapter_flags: Sequence[bool], harm_max: float = HARM_MAX) -> Dict:
    """harm = base points - adapter points (positive = the adapter got worse). Fails when harm > harm_max."""
    b, a = pct(base_flags), pct(adapter_flags)
    harm = (b - a) if b is not None and a is not None else 0.0
    return {"general_base": b, "general": a, "harm": harm, "harm_ok": harm <= harm_max + 1e-9, "harm_max": harm_max}


def score_recall(backend, R, cards: Sequence[dict], adapter: bool = True, sys_prompt: str = "Answer with just the name.",
                 max_tokens: int = 16) -> Dict:
    """cards: held-out {'q','a','dir'} rows. Closed-book, no notes. Returns recall % overall and by direction ('forward' / 'reverse')."""
    if not cards:
        return {"recall": None, "n": 0, "by_dir": {}}
    ps = [R.render(sys_prompt, c["q"]) for c in cards]
    out: List[str] = []
    for i in range(0, len(ps), backend.gen_batch):
        out += backend.generate(ps[i:i + backend.gen_batch], max_tokens, 0.0, adapter)
    flags = [recall_hit(c["a"], o) for c, o in zip(cards, out)]
    by: Dict[str, List[bool]] = {}
    for c, f in zip(cards, flags):
        by.setdefault(c.get("dir", "forward"), []).append(f)
    return {"recall": pct(flags), "n": len(flags), "hits": sum(flags), "flags": flags, "by_dir": {k: pct(v) for k, v in by.items()},
            "samples": [{"q": c["q"], "a": c["a"], "out": o[:60]} for c, o in list(zip(cards, out))[:3]]}


def _hits(r: Optional[Dict], n: int) -> int:
    r = r or {}
    if r.get("hits") is not None:
        return int(r["hits"])
    return int(round((r.get("recall") or 0.0) * n / 100.0))


def decide(general: Dict, pre: Optional[Dict], post: Dict, min_gain: int = MIN_GAIN) -> List[str]:
    """The morning decision. general: judge() result; pre / post: score_recall() of the same held-out cards with the adapter the night
    started from and with tonight's adapter. Returns the reasons to undo the night ([] = keep it)."""
    reasons = []
    if not general.get("harm_ok", False):
        reasons.append("general questions dropped %.1f points (max %.1f)" % (general.get("harm") or 0.0, general.get("harm_max", HARM_MAX)))
    n = int(post.get("n") or 0)
    if n == 0:
        reasons.append("no held-out cards to check what was learned")
        return reasons
    hp, ha = _hits(pre, n), _hits(post, n)
    if ha < hp:
        reasons.append("held-out recall got worse (%d -> %d of %d)" % (hp, ha, n))
    elif ha - hp < min_gain:
        reasons.append("held-out recall did not improve (%d -> %d of %d; need +%d)" % (hp, ha, n, min_gain))
    return reasons
