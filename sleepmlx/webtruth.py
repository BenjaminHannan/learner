"""Option B: web facts are trained on only when verified (2+ sources on different registrable domains agree).

Mirror of desk/src/webtruth.js (both are checked against desk/test/fixtures/webtruth-cases.json).
Anything web-derived and not verified is an "unverified note": it never reaches a training set.
When unsure the answer is "unverified"; a damaged provenance ledger blocks every Glim-saved note.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlsplit

from . import provenance as prov_mod
from . import lessons as L_mod

SECOND_LEVEL = {"co", "com", "org", "net", "gov", "edu", "ac", "or", "ne", "go"}
SHARED_HOSTS = ("github.io", "blogspot.com", "wordpress.com", "netlify.app", "vercel.app", "herokuapp.com", "pages.dev",
                "web.app", "firebaseapp.com", "substack.com", "medium.com")
HEDGE = re.compile(r"\b(claims?|claimed|claiming|says|said|according to|reportedly|allegedly|unconfirmed|unverified|not confirmed|"
                   r"haven'?t confirmed|have not confirmed|can'?t confirm|cannot confirm|not sure|unsure|one (?:site|source|page|website)|"
                   r"a (?:site|source|page|website)|might|may be|possibly|perhaps|supposedly|i read|i saw|i found)\b", re.I)
FLAG_FILE = "unverified-assertions.jsonl"


def registrable_domain(url: str) -> Optional[str]:
    try:
        host = (urlsplit(str(url)).hostname or "").lower().rstrip(".")
    except ValueError:
        return None
    if not host:
        return None
    if re.fullmatch(r"[\d.]+", host) or ":" in host:
        return host
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    tail2 = ".".join(labels[-2:])
    if tail2 in SHARED_HOSTS:
        return ".".join(labels[-3:])
    if len(labels[-1]) == 2 and labels[-2] in SECOND_LEVEL:
        return ".".join(labels[-3:])
    return tail2


def norm_claim(text) -> str:
    t = unicodedata.normalize("NFKC", "" if text is None else str(text)).lower()
    return " ".join("".join(c if unicodedata.category(c)[0] in "LN" else " " for c in t).split())


def is_card(n: dict) -> bool:
    return str(n.get("topic") or "").strip().lower() == "card"


def is_skill(n: dict) -> bool:
    return bool(re.match(r"^skill\s*:", str(n.get("topic") or "").strip(), re.I))


def card_claims(text: str) -> List[dict]:
    out = []
    for line in re.split(r"[\n;]", str(text or "")):
        p = [x.strip() for x in line.split("=>")]
        if len(p) == 3 and all(p):
            out.append({"subject": p[0], "relation": p[1], "object": p[2]})
    return out


def has_word(hay: str, needle: str) -> bool:
    return bool(needle) and (" " + needle + " ") in (" " + hay + " ")


def read_ledger(user_data: Path) -> dict:
    """{"ok": bool, "rows": committed prepare rows}. The strict reader of provenance.py decides what is damaged."""
    got = prov_mod.read_ledger(Path(user_data))
    rows = [r for r in got["transactions"] if r.get("committed")]
    return {"ok": got["status"] in ("ok", "missing"), "rows": rows, "local": read_local_origin(user_data)}


def read_local_origin(user_data: Path) -> set:
    """Claims Ben told Glim himself or Glim saved in a run that never touched the web (memory-local-origin.jsonl)."""
    out = set()
    try:
        for line in (Path(user_data) / "memory-local-origin.jsonl").read_text().splitlines():
            try:
                c = json.loads(line).get("claim_norm")
            except ValueError:
                continue
            if isinstance(c, str):
                out.add(c)
    except OSError:
        pass
    return out


def note_status(note: dict, ledger: dict) -> dict:
    claim, topic = norm_claim(note["text"]), str(note.get("topic") or "").strip().lower()
    mine = [r for r in ledger["rows"] if r["note_id"] == note.get("id")]
    nid = str(note.get("id", ""))
    local = claim in ledger.get("local", ()) or nid.startswith("h")
    web = bool(mine) or (not local and (is_card(note) or is_skill(note) or (not ledger["ok"] and nid.startswith("m"))))
    st = {"web": web, "verified": False, "domains": [], "urls": []}
    claims = card_claims(note["text"]) if is_card(note) else []
    if not web or not claims:
        return st
    objects = [norm_claim(c["object"]) for c in claims]
    domains, urls = set(), set()
    for r in ledger["rows"]:
        a = r.get("attribution") or {}
        src = a.get("source")
        if a.get("status") != "attributed" or not src or r.get("claim_norm") != claim or str(r.get("topic") or "").lower() != topic:
            continue
        quote, dom = norm_claim(src.get("quote")), registrable_domain(src.get("url"))
        if not dom or not all(has_word(quote, o) for o in objects):
            continue
        domains.add(dom)
        urls.add(src["url"])
    st["domains"], st["urls"], st["verified"] = sorted(domains), sorted(urls), len(domains) >= 2
    return st


def unverified_notes(notes: List[dict], ledger: dict) -> List[dict]:
    out = []
    for n in notes:
        s = note_status(n, ledger)
        if s["web"] and not s["verified"]:
            out.append(n)
    return out


def trainable_notes(user_data: Optional[Path], ignore=()) -> List[dict]:
    """read_notes() minus every unverified web note: the only way notes reach card_notes() and note cards."""
    notes = L_mod.read_notes(user_data, ignore)
    if not user_data:
        return notes
    blocked = {id(n) for n in unverified_notes(notes, read_ledger(user_data))}
    return [n for n in notes if id(n) not in blocked]


def blocked_notes(user_data: Optional[Path], ignore=()) -> List[dict]:
    notes = L_mod.read_notes(user_data, ignore)
    return unverified_notes(notes, read_ledger(user_data)) if user_data else []


def asserted_claims(answer: str, question: str, notes: List[dict], strict: bool = True) -> List[dict]:
    """Sentences of an answer that state an unverified card's answer. strict: a hedge does not excuse it."""
    ans = str(answer or "")
    ctx = norm_claim(ans + " " + str(question or ""))
    sentences = [s for s in re.split(r"(?<=[.!?])\s+|\n+", ans) if s.strip()]
    hits = []
    for n in notes:
        if not is_card(n):
            continue
        for c in card_claims(n["text"]):
            obj, subj = norm_claim(c["object"]), norm_claim(c["subject"])
            if not has_word(ctx, subj):
                continue
            for s in sentences:
                if has_word(norm_claim(s), obj) and (strict or not HEDGE.search(s)):
                    hits.append({"id": n.get("id"), "claim": c, "sentence": s.strip()})
                    break
    return hits


def answer_hash(answer: str) -> str:
    return hashlib.sha256(" ".join(str(answer or "").split()).encode("utf-8")).hexdigest()


def flagged_hashes(user_data: Optional[Path]) -> set:
    """Answers the Desk's post-check flagged (desk/src/agent.js checkUnverifiedClaims)."""
    out = set()
    if not user_data:
        return out
    try:
        for line in (Path(user_data) / FLAG_FILE).read_text().splitlines():
            try:
                h = json.loads(line).get("answer_sha256")
            except ValueError:
                continue
            if isinstance(h, str):
                out.add(h)
    except OSError:
        pass
    return out


class DiaryGuard:
    """Decides which assistant answers sleep must not see. Simplest safe option: DROP the assistant answer
    (the user's own message stays: Ben is the authority on what he said). A dropped answer cannot become a
    liked/rated/correction card or any other training text. Both the Desk's flag and our own strict check apply."""

    def __init__(self, user_data: Optional[Path]):
        self.notes = blocked_notes(user_data) if user_data else []
        self.flagged = flagged_hashes(user_data)

    def drops(self, question: str, answer: str) -> bool:
        if not answer:
            return False
        return answer_hash(answer) in self.flagged or bool(self.notes and asserted_claims(answer, question, self.notes, strict=True))
