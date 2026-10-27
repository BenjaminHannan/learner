"""Convert the gateway's raw request/response logs (~/learner-ops/diary/raw/YYYY-MM-DD.jsonl) into sleepb's week JSON.

Only Ben's own user turns and the final assistant answers are kept. Every request carries the whole history, so each call
contributes just its newest user turn (a tool-loop repeats the same turn: kept once, with the last final answer).
System prompts, tool results, [date] / memory / background blocks and secrets are removed.

The week JSON is {"seed", "user", "items": [], "diary": [{day, session, turn, role, text, mentions}], "tests": {...empty kinds}}.
`day` is an integer (1 = the oldest day that has any turns); week["dates"] maps day -> "YYYY-MM-DD".
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

KINDS = ("forward", "reverse", "twohop", "changed", "routine")  # sleepb's test kinds (all empty here)
SKIP_MODELS = {"k2-helper"}  # title / summary calls
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ---------------------------------------------------------------- reading
def read_blob(blob_dir: Path, ref: str) -> str:
    try:
        raw = (Path(blob_dir) / ref).read_text(errors="replace")
    except OSError:
        return ""
    s = raw.strip()
    if s[:1] in ('"', "[", "{"):  # a blob may hold JSON (a string, or a list of content parts)
        try:
            return flatten(json.loads(s), blob_dir)
        except ValueError:
            pass
    return raw


def flatten(content, blob_dir: Optional[Path] = None) -> str:
    """str | {"$blob": sha} | list of parts | {"type": "text", "text": ...} -> plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        if "$blob" in content:
            return read_blob(blob_dir, str(content["$blob"])) if blob_dir else ""
        if "text" in content and content.get("type", "text") == "text":
            return flatten(content["text"], blob_dir)
        return ""
    if isinstance(content, list):
        return "\n".join(x for x in (flatten(c, blob_dir) for c in content) if x)
    return ""


# ---------------------------------------------------------------- stripping
_TAG_BLOCK = re.compile(r"<(memory|memories|notes|saved_notes|saved-notes|background|system-reminder|context|date|desk)\b[^>]*>.*?</\1>", re.S | re.I)
_DATE_PREFIX = re.compile(r"^\s*\[[^\]\n]{0,80}?(?:\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}|\b20\d{2}\b)[^\]\n]{0,80}\]\s*", re.I)
_BRACKET_BG = re.compile(r"\[(?:Background, not a request|Background|Memory|Memories|Saved notes)[^\]]*\]", re.I)
_BG_LINE = re.compile(r"^\s*\[?Background, not a request.*$", re.I | re.M)
_SAVED_HEAD = re.compile(r"^\s*(?:#+\s*)?\**Saved notes about Ben\b.*$", re.I | re.M)
_THINK = re.compile(r"<think>.*?</think>|<ifm\|think[^>]*>.*?</ifm\|think[^>]*>", re.S | re.I)


def strip_user(text: str) -> str:
    """Remove the Desk's wrapper text from a user turn, leaving what Ben typed."""
    t = text or ""
    t = _TAG_BLOCK.sub("", t)
    # "Saved notes about Ben" section: the heading line up to the next blank line (or the end)
    while True:
        m = _SAVED_HEAD.search(t)
        if not m:
            break
        end = re.search(r"\n\s*\n", t[m.end():])
        t = t[:m.start()] + (t[m.end() + end.end():] if end else "")
    t = _BRACKET_BG.sub("", t)
    t = _BG_LINE.sub("", t)
    for _ in range(3):  # a date prefix may sit in front of, or behind, a removed block
        n = _DATE_PREFIX.sub("", t, count=1)
        if n == t:
            break
        t = n
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def strip_assistant(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", _THINK.sub("", text or "")).strip()


# ---------------------------------------------------------------- redaction
REDACTED = "[REDACTED]"


def _luhn(digits: str) -> bool:
    s, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        s, alt = s + d, not alt
    return s % 10 == 0


_CARD = re.compile(r"(?<![\w-])(?:\d[ -]?){12,18}\d(?![\w-])")
_SSN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
_KV = re.compile(r"(?i)\b(pass(?:word|phrase|code)?|passwd|pwd|pin|secret|token|api[ _-]?key|apikey|cvv|cvc|security code|"
                 r"(?:verification|confirmation|login|auth(?:entication)?|one[- ]time|otp|2fa|sms|access|reset|promo|gift card)(?: code)?|code)"
                 r"(\s*(?:is|was|=|:|-|are)?\s*)([\"'`]?)([^\s\"'`,;]{3,})\3")
_SECRET_TOK = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|xox[abp]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|"
                         r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,})\b")
_LONG_TOK = re.compile(r"\b(?=[A-Za-z0-9+/_-]{32,}\b)(?=\S*\d)(?=\S*[A-Za-z])[A-Za-z0-9+/_-]{32,}\b")
_URL_KEY = re.compile(r"(?i)([?&](?:key|token|sig|signature|password|auth)=)[^&\s]+")


def redact(text: str) -> str:
    """Drop secrets: passwords / PINs / codes after their keyword, card numbers (Luhn), SSNs, API keys, long random tokens."""
    def card(m):
        d = re.sub(r"\D", "", m.group(0))
        return REDACTED if 13 <= len(d) <= 19 and _luhn(d) else m.group(0)

    def kv(m):
        val = m.group(4)
        word = m.group(1).lower()
        # a bare "code" / "pin" needs a value with a digit, so ordinary prose ("the code is clean") survives
        if word in ("code", "pin") and not re.search(r"\d", val):
            return m.group(0)
        return m.group(1) + m.group(2) + m.group(3) + REDACTED + m.group(3)

    t = _SECRET_TOK.sub(REDACTED, text)
    t = _URL_KEY.sub(lambda m: m.group(1) + REDACTED, t)
    t = _CARD.sub(card, t)
    t = _SSN.sub(REDACTED, t)
    t = _KV.sub(kv, t)
    t = _LONG_TOK.sub(REDACTED, t)
    return t


# A turn that talks about credentials is dropped whole: pattern redaction misses forms like "X is my pass".
_SECRET_TALK = re.compile(r"\b(pass(word|wd|code|phrase)?|login|log ?in|sign ?in|credentials?|2fa|otp|verification code|security code|pin)\b", re.I)


def talks_secrets(text: str) -> bool:
    return bool(_SECRET_TALK.search(text or ""))


# ---------------------------------------------------------------- ignore list + test-mode records
SEED_IGNORE = ["AP Chem 4th period", "Mr. Phipps", "I like short answers", "open example.com", "Remember that I take"]
IGNORE_HEADER = ("# One phrase or regular expression per line (case-insensitive). A user turn that matches any line is dropped, with its answer.\n"
                 "# Seeded after smoke-test facts were typed into the diary by mistake.\n")


def ensure_ignore(path: Path) -> Path:
    """Create the sleep root's ignore.txt with the seed lines if it does not exist yet."""
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(IGNORE_HEADER + "\n".join(SEED_IGNORE) + "\n")
    return path


def load_ignore(path: Optional[Path]) -> List["re.Pattern"]:
    out = []
    try:
        lines = Path(path).read_text().splitlines() if path else []
    except OSError:
        lines = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        try:
            out.append(re.compile(ln, re.I))
        except re.error:
            out.append(re.compile(re.escape(ln), re.I))
    return out


def is_test_record(rec: dict) -> bool:
    """A record the app's e2e / test mode produced: a truthy `test` field (top level or in request), or a test header."""
    req = rec.get("request") if isinstance(rec.get("request"), dict) else {}
    for d in (rec, req):
        if d.get("test") in (True, 1, "1", "true", "True"):
            return True
        h = d.get("headers")
        if isinstance(h, dict) and any(str(k).lower() in ("test", "x-test", "x-e2e", "x-test-mode") and str(v).lower() not in ("", "0", "false") for k, v in h.items()):
            return True
    return False


# ---------------------------------------------------------------- raw logs -> turns
def _record_turn(rec: dict, blob_dir: Path) -> Optional[Tuple[str, str, Optional[str]]]:
    """-> (conv_id, user_text, final_answer or None) for one raw record, or None."""
    if rec.get("model") in SKIP_MODELS or is_test_record(rec):
        return None
    if rec.get("status") not in (None, 200, "200", "ok", "OK"):   # the gateway logs "ok"
        return None
    req = rec.get("request") if isinstance(rec.get("request"), dict) else {}
    msgs = rec.get("messages") or req.get("messages") or []
    user = None
    for m in reversed(msgs):
        if isinstance(m, dict) and m.get("role") == "user":
            user = strip_user(flatten(m.get("content"), blob_dir))
            break
    if not user:
        return None
    resp = rec.get("response") if isinstance(rec.get("response"), dict) else {}
    ans = None
    if not resp.get("tool_calls"):
        a = strip_assistant(flatten(resp.get("content"), blob_dir))
        ans = a or None
    conv = str(rec.get("conv_id") or "")
    return conv, user, ans


def _rec_date(rec: dict) -> Optional[str]:
    """Local date of a record from its ts (epoch seconds or milliseconds, or an ISO string)."""
    ts = rec.get("ts")
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts / 1000.0 if ts > 1e11 else ts).strftime("%Y-%m-%d")
        if isinstance(ts, str) and ts:
            try:
                return datetime.fromtimestamp(float(ts) / 1000.0 if float(ts) > 1e11 else float(ts)).strftime("%Y-%m-%d")
            except ValueError:
                return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d")
    except (ValueError, OSError, OverflowError):
        pass
    return None


def load_days(raw_dir: Path) -> Dict[str, List[dict]]:
    """date -> records, in file order. Two layouts are accepted:
    (1) the Mac gateway's raw log: raw/YYYY-MM-DD.jsonl (+ raw/blobs/<sha1>), record {ts, model, conv_id, messages, response, ...};
    (2) the Windows app's simple log: any *.jsonl of {ts, model, messages:[{role, content}], response:{content}}; a file not named by a date is split by each record's ts."""
    raw_dir = Path(raw_dir)
    days: Dict[str, List[dict]] = {}
    for f in sorted(raw_dir.glob("*.jsonl")):
        named = f.stem if DAY_RE.match(f.stem) else None
        try:
            lines = f.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            date = named or _rec_date(rec)
            if date:
                days.setdefault(date, []).append(rec)
    return days


def turns_of(records: Iterable[dict], blob_dir: Path) -> List[Tuple[str, str]]:
    """The deduped (user text, answer or '') turns of one day's records, in order."""
    order: List[Tuple[str, str]] = []
    ans: Dict[Tuple[str, str], str] = {}
    for rec in records:
        got = _record_turn(rec, blob_dir)
        if got is None:
            continue
        conv, user, a = got
        key = (conv, user)
        if key not in ans:
            order.append(key)
            ans[key] = ""
        if a:
            ans[key] = a  # the last final answer of the turn
    return [(u, ans[(c, u)]) for c, u in order]


def day_turns(raw_dir: Path, date: str) -> List[Tuple[str, str]]:
    return turns_of(load_days(raw_dir).get(date, []), Path(raw_dir) / "blobs")


def list_dates(raw_dir: Path) -> List[str]:
    return sorted(load_days(raw_dir))


def build_week(raw_dir: Path, who: str = "Ben", dates: Optional[Iterable[str]] = None, ignore_file: Optional[Path] = None) -> dict:
    """Week JSON for all days that have turns (day numbers follow the date order)."""
    raw_dir = Path(raw_dir)
    alld = load_days(raw_dir)
    ignore = load_ignore(ignore_file)
    want = sorted(alld) if dates is None else sorted(d for d in dates if d in alld)
    diary, daymap = [], {}
    for date in want:
        turns, seen = [], set()
        for user, answer in turns_of(alld[date], raw_dir / "blobs"):
            if any(rx.search(user) for rx in ignore) or talks_secrets(user):   # dropped with its answer
                continue
            u = redact(user).strip()
            if not u or u in seen:
                continue
            seen.add(u)
            turns.append((u, redact(answer).strip()))
        if not turns:
            continue
        day = len(daymap) + 1
        daymap[day] = date
        for k, (u, a) in enumerate(turns):
            diary.append({"day": day, "session": 0, "turn": k, "role": "user", "text": u, "mentions": []})
            if a:
                diary.append({"day": day, "session": 0, "turn": k, "role": "assistant", "text": a, "mentions": []})
    week = {"seed": 1, "user": who, "items": [], "diary": diary, "tests": {k: [] for k in KINDS},
            "test_strings_norm": [], "dates": {str(k): v for k, v in daymap.items()}}
    check_week(week)
    return week


def check_week(week: dict) -> None:
    """sleepb.check_week's rules (the per-test rules hold trivially for empty test lists)."""
    for k in ("items", "diary", "tests"):
        assert k in week, "week file lacks '%s'" % k
    for k in KINDS:
        assert k in week["tests"], "week tests lack '%s'" % k
    assert all(t["role"] in ("user", "assistant") and "day" in t and "text" in t for t in week["diary"]), "bad diary rows"
    assert all("class" in t for k in ("forward", "reverse") for t in week["tests"][k]), "forward/reverse tests need a class"
    assert all("old" in t for t in week["tests"]["changed"]) and all("items" in t for t in week["tests"]["twohop"]), "changed needs old, twohop needs items"
    assert all(k in g for g in week["items"] for k in ("id", "a", "b", "class")), "items need id, a, b, class"


def date_of_day(week: dict, day: int) -> Optional[str]:
    return week.get("dates", {}).get(str(day))


def day_of_date(week: dict, date: str) -> Optional[int]:
    for k, v in week.get("dates", {}).items():
        if v == date:
            return int(k)
    return None
