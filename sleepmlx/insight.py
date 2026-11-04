"""Sleep insight (T5, 2026-11-04): try the day's STUCK problems again at night with related memories, and keep only what the truth confirms.

Ben: "When something hits a problem, take all relevant information for it and have the model mix and match ideas until something clicks.
Sleep makes ideas/connections like this click more." (Wagner et al., Nature 2004: after sleep, people found a hidden shortcut ~2.6x as often.)

The Desk keeps the stuck list in userData/alwayson-stuck.json (desk/src/stuck.js). For every CHECKABLE entry (it carries a sha256 of the
normalised true answer from the executor or the puzzle generator; the answer itself is never in the file, so no prompt can see it):
  1. recall the memories most related to the problem (IDF-weighted word overlap with tonight's items: facts, notes, lessons);
  2. ask the base model for K candidates, each one mixing a DIFFERENT pair of the recalled memories;
  3. check every candidate with the truth (hash of its normalised answer == the stored hash). The model proposes; only the truth decides;
  4. the first verified candidate becomes an `insight` item: one text card (problem + working + answer) and one question-answer card.
Entries with no truth (I'm-not-sure claims, Ben's repeated errors, locked quiz misses) are counted and left on the list: nothing is stored.
The night's results go to userData/alwayson-insight.json; the Desk fades the unsolved entries and tells Ben only if something clicked.

Toy evidence: premonition-sleeplab-t5 MARKS-insight-v1 (string-program toy, not Glim). Real Glim: untested until real nights report.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

STUCK_FILE = "alwayson-stuck.json"
RESULTS_FILE = "alwayson-insight.json"
_STOP = set("the a an and or of to in on for is are was were be been it its this that with as at by from what which who how does do did "
            "you your i my me we our not no yes just give answer exact exactly print prints output only".split())


# ---- the same normalisations as the Desk (sandbox.js normOut; puzzles.js normAns + correct()) ------------------------------------
def norm_out(s) -> str:
    s = "" if s is None else str(s)
    s = "\n".join(re.sub(r"\s+$", "", l) for l in s.replace("\r\n", "\n").split("\n"))
    return re.sub(r"\n+$", "", s)


def norm_ans(s) -> str:
    s = ("" if s is None else str(s)).lower()
    s = re.sub(r"^\s*(?:answer|output)\s*[:=]\s*", "", s)
    s = re.sub(r"[`\"'.]", "", s)
    s = re.sub(r"[\s,]+", " ", s).strip()
    return re.sub(r"(\d) (?=\d)", r"\1", s)


NORMS = {"out": norm_out, "puzzle": lambda s: norm_ans(s).replace(" ", "")}


def truth_hash(answer, norm: str = "out") -> str:
    return hashlib.sha256(NORMS[norm](answer).encode("utf-8")).hexdigest()


def verified(entry: dict, answer) -> bool:
    """The truth check. Only a sha256 truth from the Desk's executor / puzzle generator can verify; anything else never does."""
    t = entry.get("truth") or {}
    if t.get("type") != "sha256" or t.get("norm") not in NORMS or not re.fullmatch(r"[0-9a-f]{64}", str(t.get("value") or "")):
        return False
    if answer is None or not str(answer).strip():
        return False
    return truth_hash(answer, t["norm"]) == t["value"]


def checkable(entry: dict) -> bool:
    t = entry.get("truth") or {}
    return t.get("type") == "sha256" and t.get("norm") in NORMS and bool(re.fullmatch(r"[0-9a-f]{64}", str(t.get("value") or "")))


# ---- reading the Desk's stuck list ---------------------------------------------------------------------------------------------
def read_stuck(user_data: Optional[Path]) -> List[dict]:
    """[{id, source, kind, problem, context, truth, weight, ...}] from userData/alwayson-stuck.json; [] when missing or bad.
    An entry that carries a plain answer field is refused (the answer must never reach a prompt)."""
    if not user_data:
        return []
    try:
        j = json.loads((Path(user_data) / STUCK_FILE).read_text())
    except (OSError, ValueError):
        return []
    out = []
    for e in (j.get("items") if isinstance(j, dict) else None) or []:
        if not isinstance(e, dict) or not str(e.get("id") or "").strip() or not str(e.get("problem") or "").strip():
            continue
        if any(k in e for k in ("answer", "truth_text", "solution")):
            continue
        out.append(e)
    out.sort(key=lambda e: (-float(e.get("weight") or 0), str(e.get("id"))))
    return out


# ---- 1. related-memory recall --------------------------------------------------------------------------------------------------
def words(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9_]+", str(text).lower()) if len(w) >= 2 and w not in _STOP]


def recall(problem: str, memories: Sequence[str], m: int) -> List[Tuple[float, str]]:
    """Top-m memories by IDF-weighted overlap with the problem's words (the toy's shape match, on words). Ties: memory order."""
    docs = [set(words(t)) for t in memories]
    n = len(docs)
    df: Dict[str, int] = {}
    for d in docs:
        for w in d:
            df[w] = df.get(w, 0) + 1
    q = set(words(problem))
    scored = []
    for i, (t, d) in enumerate(zip(memories, docs)):
        hit = sum(math.log((n + 1) / (df[w] + 0.5)) for w in d & q)
        if hit > 0:
            scored.append((-hit, i, t))
    scored.sort()
    return [(-s, t) for s, _, t in scored[:m]]


def pairs(recalled: Sequence[str], k: int) -> List[Tuple[str, ...]]:
    """K mixes: every pair of recalled memories, best-ranked pairs first (one memory alone when only one was recalled; none at all
    when nothing related was found: the model then retries with the problem alone)."""
    if len(recalled) >= 2:
        ps = sorted(itertools.combinations(range(len(recalled)), 2), key=lambda ij: (ij[0] + ij[1], ij))
        out = [tuple(recalled[i] for i in ij) for ij in ps]
    elif recalled:
        out = [(recalled[0],)]
    else:
        out = [()]
    return [out[i % len(out)] for i in range(k)]


# ---- 2. the candidate prompt ---------------------------------------------------------------------------------------------------
SYSTEM = "You solve problems you were stuck on by combining things you already know."


def insight_prompt(R, entry: dict, mix: Sequence[str]) -> str:
    known = "\n".join("%d) %s" % (i + 1, t) for i, t in enumerate(mix)) or "(nothing related found)"
    u = ("Yesterday you got this problem wrong:\n%s\n\nWhat happened: %s\n\nThings you know that may help:\n%s\n\n"
         "Combine these pieces to solve the problem. Work it out step by step, then give the exact final answer. "
         "Reply with only JSON: {\"working\": \"your steps, at most 3 sentences\", \"answer\": \"the exact answer\"}."
         % (str(entry.get("problem"))[:1500], str(entry.get("context") or "")[:600], known))
    return R.render(SYSTEM, u)


def parse_candidate(text: str) -> Optional[dict]:
    s = re.sub(r"<think>[\s\S]*?</think>", "", str(text or ""), flags=re.I).strip()
    a, b = s.find("{"), s.rfind("}")
    if a < 0 or b <= a:
        return None
    try:
        j = json.loads(s[a:b + 1])
    except ValueError:
        return None
    if not isinstance(j, dict) or j.get("answer") is None:
        return None
    ans = j["answer"] if isinstance(j["answer"], str) else json.dumps(j["answer"])
    return {"working": str(j.get("working") or "").strip()[:600], "answer": ans[:2000]}


# ---- 4. the cards and the morning file -----------------------------------------------------------------------------------------
def insight_cards(entry: dict, cand: dict, date: str, who: str = "Ben") -> Tuple[List[str], List[List[str]]]:
    prob = " ".join(str(entry.get("problem")).split())[:600]
    ans = cand["answer"].strip()
    text = "Insight from the night of %s (checked by the %s): the problem \"%s\" is solved like this: %s The answer is: %s" % (
        date, "executor" if (entry.get("truth") or {}).get("norm") == "out" else "puzzle generator", prob, cand["working"] or "(no working)", ans)
    return [text], [[str(entry.get("problem")).strip()[:1500], ans]]


def write_results(user_data: Optional[Path], res: dict) -> Optional[Path]:
    if not user_data:
        return None
    p = Path(user_data) / RESULTS_FILE
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(res, indent=1))
        tmp.replace(p)
        return p
    except OSError:
        return None
