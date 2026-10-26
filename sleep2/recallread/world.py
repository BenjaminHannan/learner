"""Week-2 world loader for the Recall-then-read test (stage 1).

The world is backbone/sleep/brain/data/week2.json of the Sleep-B branch claude/project-thread-cqc4bi, pinned at PIN_COMMIT. It is read
only. The diary here is the USER turns of that file (the same text sleepb.Diary searches); assistant turns are not indexed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path

PIN_COMMIT = "a7ed69d79d9ca928bc77b577c2912c6655474ad0"  # claude/project-thread-cqc4bi, "Sleep-B addendum 14: probe JSON and log"
WEEK2_SHA = "70db7146ed59d10cbd0d2e8d7a6fc0e245d4b07ec57add0c793db1fdff006e5b"
WEEK2_REL = "backbone/sleep/brain/data/week2.json"
K2_MODEL = "IFM/K2-Horizon-3.7B"
K2_REVISION = "9d280ff742235796925c9fe3cf243dc1beea5c08"
REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "data" / "recallread"

STOP = frozenset("a an the of to in on at for and or but is are was were be been it its this that these those i me my we you your he she his her they them "
                 "their do does did have has had with as by from about what which who whom whose where when how not no so if then than there here "
                 "can could would should will just also really very sam".split())


def norm(s: str) -> str:
    """NFKC, casefold, collapse whitespace (the exact-match normal form)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s).casefold()).strip()


def words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", norm(s).replace("’", "'").replace("'s", ""))


def has_word(text: str, name: str) -> bool:
    """name occurs in text as a whole word / phrase after normalisation."""
    return re.search(r"(?<![a-z0-9])" + re.escape(norm(name)) + r"(?![a-z0-9])", norm(text)) is not None


def tokset(t: dict) -> frozenset:
    """Whole-word token set of a turn (cached on the dict). For single-token names, `n in tokset(t)` equals has_word(text, n)."""
    if "_ws" not in t:
        t["_ws"] = frozenset(re.findall(r"[a-z0-9]+", norm(t["text"])))
    return t["_ws"]


def mentions_name(t: dict, name: str) -> bool:
    n = norm(name)
    return (n in tokset(t)) if re.fullmatch(r"[a-z0-9]+", n) else has_word(t["text"], name)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def find_week2(path: str | os.PathLike | None = None) -> Path:
    """Order: argument, $RR_WEEK2, data/recallread/week2.json, $RR_BACKBONE/.., repo backbone/, then `git show PIN_COMMIT:` into data/recallread/."""
    cands = [path, os.environ.get("RR_WEEK2"), FROZEN / "week2.json"]
    if os.environ.get("RR_BACKBONE"):
        cands.append(Path(os.environ["RR_BACKBONE"]) / "sleep/brain/data/week2.json")
    cands.append(REPO / WEEK2_REL)
    for c in cands:
        if c and Path(c).is_file():
            return Path(c)
    FROZEN.mkdir(parents=True, exist_ok=True)
    out = FROZEN / "week2.json"
    data = subprocess.run(["git", "-C", str(REPO), "show", f"{PIN_COMMIT}:{WEEK2_REL}"], check=True, capture_output=True).stdout
    out.write_bytes(data)
    return out


def load_world(path=None, check=True) -> dict:
    p = find_week2(path)
    if check:
        got = sha256_file(p)
        if got != WEEK2_SHA:
            raise SystemExit(f"week2.json sha256 {got} != pinned {WEEK2_SHA} ({p})")
    return json.loads(Path(p).read_text())


def user_turns(world: dict) -> list[dict]:
    """The searchable diary: [{turn_id (index in world['diary']), day, session, text, mentions}] for role == user."""
    return [dict(turn_id=i, day=t["day"], session=t.get("session"), text=t["text"], mentions=list(t.get("mentions", [])))
            for i, t in enumerate(world["diary"]) if t["role"] == "user"]


ABSTAIN = re.compile(r"\b(unknown|don'?t know|do not know|not (?:mentioned|said|stated|in the notes)|no (?:information|record|mention)|cannot (?:tell|say|find)|can'?t (?:tell|say|find)|unsure|not sure)\b")


def exact_match(gold: str, answer: str) -> bool:
    """NFKC / casefold; the gold string occurs in the answer as a whole word (phrase)."""
    return has_word(answer, gold)


def is_abstain(answer: str) -> bool:
    return ABSTAIN.search(norm(answer).replace("’", "'")) is not None
