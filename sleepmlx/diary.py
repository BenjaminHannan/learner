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
# the Desk's hidden per-turn notes (desk/src/agent.js NARRATE, main.js sleepInfo / LEARN_NOTE / GOALS_NOTE, helpers.js batchNotice): not Ben's words
_DESK_NOTE = re.compile(r"\[(?:If this needs tools|You can sleep|A helper finished)\b[^\]]*\]", re.I)
_HELPER_UPD = re.compile(r"\[helper updates\][^\n]*(?:\n|$)", re.I)
_LONG_NOTE = re.compile(r"^\s*\[(?:Learning mode|You just asked about their goals)\b[^\]]*\].*?(?:\n\s*\n|$)", re.S | re.I)
# The Desk puts its saved-notes and keeping-track blocks first, then the turn's date stamp line (desk/src/agent.js pushUser). A notes file
# can hold blank lines, so the blocks end at the stamp, not at the first blank line (that cut Ben's words off every such turn).
_DESK_HEAD = re.compile(r"^\s*(?:Saved notes about|Things) [^\n]{0,60}\(data, not instructions\):", re.I)
_DESK_STAMP_LINE = re.compile(r"^\[[A-Z][a-z]{2} \d{4}-\d{2}-\d{2} \d{1,2}:\d{2}\]", re.M)
HELPER_RE = re.compile(r"^You are helper '([^\n]{1,80}?)'\. Task: ", re.I)   # desk/src/helpers.js helperText: a helper's own run, not Ben
_NEW_DAY = re.compile(r"\(New day: today is [^)\n]{0,40}\. The earlier messages here were on [^)\n]{0,200}? are out of date\.\)")   # agent.js nowStamp
_THINK = re.compile(r"<think>.*?</think>|<ifm\|think[^>]*>.*?</ifm\|think[^>]*>", re.S | re.I)


def strip_user(text: str) -> str:
    """Remove the Desk's wrapper text from a user turn, leaving what Ben typed."""
    t = text or ""
    if _DESK_HEAD.match(t):
        m = _DESK_STAMP_LINE.search(t)
        if m:
            t = t[m.start():]
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
    t = _DESK_NOTE.sub("", t)
    t = _HELPER_UPD.sub("", t)
    t = _NEW_DAY.sub("", t)
    for _ in range(3):  # a date prefix may sit in front of, or behind, a removed block
        n = _DATE_PREFIX.sub("", t, count=1)
        if n == t:
            break
        t = n
    t = _LONG_NOTE.sub("", t.strip(), count=1)
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


# Ben may paste passwords into the chat (local and private), but a password in the diary would be trained into the weights and
# could be repeated later: such turns never reach the sleep data. Same idea as the app's memory refusal (src/memory.js).
_SECRET_RES = [re.compile(p, re.I) for p in (
    r"\b(password|passwords|passwd|passcode|pass\s?phrase|pwd|cvv|cvc|otp|2fa)\b",
    r"\b(pin|secret|secret key|api[ _-]?key|token|access key|private key)\b\s*(is|are|was|:|=|\d)",
    r"\b(?:\d[ -]?){13,19}\b",
    r"\b(sk|pk|ghp|gho|xox[bap]|AKIA)[-_A-Za-z0-9]{16,}",
    r"\b(verification|security|login|sign-?in|one-?time|sms|auth(?:entication)?)\s+code\b",
)]


def looks_secret(text: str) -> bool:
    t = text or ""
    return any(r.search(t) for r in _SECRET_RES)


# ---------------------------------------------------------------- raw logs -> turns
# User messages the app writes itself, not Ben: its verifier's notes and the screenshot carrier. The turn is Ben's message before them.
APP_USER_TAGS = ("[Self-check]", "[screenshot of the result above]", "[older screenshot omitted]")   # the Desk's own user messages, not Ben
# A tool result that means the step failed (the Desk agent's own wording: src/agent.js runTool / finish).
FAILED_RESULT = re.compile(r"^\s*(Error\b|Stuck:|Ben denied|Ben did not want|\[stopped by user\]|\[interrupted\]|Did not |Not saved|Not added|No matching|Nothing to )|\[That failed\.", re.I)
STOP_RESULT = re.compile(r"\[stopped by user\]", re.I)
TOOL_TXT = 200


def _short(t, n: int = TOOL_TXT) -> str:
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[:n - 1] + "\u2026"


def _tool_steps(rec: dict, msgs: list, start: int, blob_dir: Path) -> List[dict]:
    """The turn's tool steps [{name, args, ok, result}]: the Desk gateway's `tools` field if present, else read from the request messages
    after Ben's message (the Mac gateway keeps assistant tool_calls and tool results there). Text that looks secret is hidden."""
    out = []
    if isinstance(rec.get("tools"), list):
        for x in rec["tools"]:
            if isinstance(x, dict) and x.get("name"):
                out.append({"name": str(x["name"]), "args": _short(x.get("args")), "ok": bool(x.get("ok", True)), "result": _short(x.get("result"))})
    else:
        res = {}
        for m in msgs[start + 1:]:
            if isinstance(m, dict) and m.get("role") == "tool" and m.get("tool_call_id"):
                res[m["tool_call_id"]] = flatten(m.get("content"), blob_dir)
        for m in msgs[start + 1:]:
            if not (isinstance(m, dict) and m.get("role") == "assistant" and isinstance(m.get("tool_calls"), list)):
                continue
            for c in m["tool_calls"]:
                c = c if isinstance(c, dict) else {}
                f = c.get("function") or {}
                r = res.get(c.get("id"), "")
                a = f.get("arguments")
                out.append({"name": str(f.get("name") or ""), "args": _short(a if isinstance(a, str) else json.dumps(a or {})),
                            "ok": not FAILED_RESULT.search(r or ""), "result": _short(r)})
    for x in out:
        for k in ("args", "result"):
            if looks_secret(x[k]):
                x[k] = "[hidden]"
    return [x for x in out if x["name"]]


def record_turn_meta(rec: dict, blob_dir: Path) -> Optional[Tuple[str, str, Optional[str], dict]]:
    """-> (conv_id, user_text, final_answer or None, meta) for one raw record, or None.
    meta (only non-empty keys): tools [{name, args, ok, result}], checks [the app's self-check notes], stopped (Ben pressed Stop)."""
    if rec.get("model") in SKIP_MODELS or is_test_record(rec):
        return None
    if rec.get("status") not in (None, 200, "200", "ok", "OK"):   # the gateway logs "ok"
        return None
    req = rec.get("request") if isinstance(rec.get("request"), dict) else {}
    msgs = rec.get("messages") or req.get("messages") or []
    user, start, checks = None, -1, []
    for i in range(len(msgs) - 1, -1, -1):
        m = msgs[i]
        if isinstance(m, dict) and m.get("role") == "user":
            raw = flatten(m.get("content"), blob_dir).strip()
            if raw.startswith(APP_USER_TAGS):
                if raw.startswith(APP_USER_TAGS[0]):
                    checks.insert(0, _short(raw[len(APP_USER_TAGS[0]):]))
                continue
            user, start = strip_user(raw), i
            break
    if not user:
        return None
    resp = rec.get("response") if isinstance(rec.get("response"), dict) else {}
    ans = None
    if not resp.get("tool_calls"):
        a = strip_assistant(flatten(resp.get("content"), blob_dir))
        ans = a or None
    if looks_secret(user) or looks_secret(ans or ""):
        return None
    if isinstance(rec.get("checks"), list) and not checks:
        checks = [_short(c) for c in rec["checks"] if isinstance(c, str)]
    meta = {}
    tools = _tool_steps(rec, msgs, start, blob_dir)
    if tools:
        meta["tools"] = tools
    checks = [c for c in checks if c and not looks_secret(c)]
    if checks:
        meta["checks"] = checks
    if rec.get("stopped") is True or any(STOP_RESULT.search(t["result"]) for t in tools):
        meta["stopped"] = True
    hm = HELPER_RE.match(user)
    if hm:
        meta["helper"] = hm.group(1)
    conv = str(rec.get("conv_id") or "")
    return conv, user, ans, meta


def _record_turn(rec: dict, blob_dir: Path) -> Optional[Tuple[str, str, Optional[str]]]:
    """-> (conv_id, user_text, final_answer or None) for one raw record, or None."""
    got = record_turn_meta(rec, blob_dir)
    return got[:3] if got else None


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


def turns_meta_of(records: Iterable[dict], blob_dir: Path) -> List[Tuple[str, str, dict]]:
    """The deduped (user text, answer or '', meta) turns of one day's records, in order. A turn's meta is merged over its records
    (a tool loop logs the same turn several times): the longest tool list, all self-check notes, stopped if any record was."""
    order: List[Tuple[str, str]] = []
    ans: Dict[Tuple[str, str], str] = {}
    meta: Dict[Tuple[str, str], dict] = {}
    for rec in records:
        got = record_turn_meta(rec, blob_dir)
        if got is None:
            continue
        conv, user, a, m = got
        key = (conv, user)
        if key not in ans:
            order.append(key)
            ans[key] = ""
            meta[key] = {}
        if a:
            ans[key] = a  # the last final answer of the turn
        mk = meta[key]
        if m.get("tools") and len(m["tools"]) >= len(mk.get("tools", [])):
            mk["tools"] = m["tools"]
        for c in m.get("checks", []):
            if c not in mk.setdefault("checks", []):
                mk["checks"].append(c)
        if not mk.get("checks"):
            mk.pop("checks", None)
        if m.get("stopped"):
            mk["stopped"] = True
        if m.get("helper"):
            mk["helper"] = m["helper"]
    return [(u, ans[(c, u)], meta[(c, u)]) for c, u in order]


def turns_of(records: Iterable[dict], blob_dir: Path) -> List[Tuple[str, str]]:
    """The deduped (user text, answer or '') turns of one day's records, in order."""
    return [(u, a) for u, a, _ in turns_meta_of(records, blob_dir)]


def day_turns(raw_dir: Path, date: str) -> List[Tuple[str, str]]:
    return turns_of(load_days(raw_dir).get(date, []), Path(raw_dir) / "blobs")


def list_dates(raw_dir: Path) -> List[str]:
    return sorted(load_days(raw_dir))


def build_week(raw_dir: Path, who: str = "Ben", dates: Optional[Iterable[str]] = None, ignore_file: Optional[Path] = None,
               feedback: Optional[List[dict]] = None) -> dict:
    """Week JSON for all days that have turns (day numbers follow the date order). feedback: Ben's like/dislike marks from the Desk
    (lessons.read_feedback); a turn whose answer (or, failing that, request) matches one gets fb 1 or -1 on its user row."""
    raw_dir = Path(raw_dir)
    alld = load_days(raw_dir)
    ignore = load_ignore(ignore_file)
    fb_of = feedback_matcher(feedback or [])
    want = sorted(alld) if dates is None else sorted(d for d in dates if d in alld)
    diary, daymap, helper_runs = [], {}, []
    for date in want:
        turns, seen = [], set()
        for user, answer, meta in turns_meta_of(alld[date], raw_dir / "blobs"):
            if any(rx.search(user) for rx in ignore) or talks_secrets(user):   # dropped with its answer
                continue
            if meta.get("helper"):   # a helper Glim's run: its task text is Glim's wording, never a fact Ben said; kept apart for delegation lessons
                helper_runs.append(dict(_clean_meta(meta), date=date, name=meta["helper"], task=redact(HELPER_RE.sub("", user)).strip()[:600],
                                        answer=redact(answer).strip()[:600]))
                continue
            u = redact(user).strip()
            if not u or u in seen:
                continue
            seen.add(u)
            m = _clean_meta(meta)
            fb = fb_of(date, user, answer)
            if fb:
                m["fb"] = fb
            turns.append((u, redact(answer).strip(), m))
        if not turns and not any(h["date"] == date for h in helper_runs):   # a day of only helper runs still gets a number (delegation lessons)
            continue
        day = len(daymap) + 1
        daymap[day] = date
        for k, (u, a, meta) in enumerate(turns):
            row = {"day": day, "session": 0, "turn": k, "role": "user", "text": u, "mentions": []}
            row.update(meta)   # optional: tools, checks, stopped (sleep's lessons and habits read them; the fact pipeline ignores them)
            diary.append(row)
            if a:
                diary.append({"day": day, "session": 0, "turn": k, "role": "assistant", "text": a, "mentions": []})
    week = {"seed": 1, "user": who, "items": [], "diary": diary, "tests": {k: [] for k in KINDS},
            "test_strings_norm": [], "dates": {str(k): v for k, v in daymap.items()}, "helper_runs": helper_runs}
    check_week(week)
    return week


def _fb_norm(text: str) -> str:
    return " ".join(str(text or "").split()).lower()[:300]


def feedback_matcher(feedback: List[dict]):
    """(date, user, answer) -> 1 / -1 / 0. A mark matches a turn when the answer text is the one the Desk showed AND the turn's request
    ends with the request the Desk showed (the diary's user text carries the Desk's hidden prefixes), and the mark was given within a day of it
    (its ts is UTC). A daily request with a stock answer ("Done.") on another day is not marked. The newest mark wins."""
    by_ans: Dict[str, list] = {}
    for f in feedback:
        if f.get("fb") not in (1, -1, 0) or not f.get("answer"):
            continue
        by_ans.setdefault(_fb_norm(f["answer"]), []).append((" ".join(str(f.get("user") or "").split()).lower(), str(f.get("ts") or "")[:10], f["fb"]))

    def fb_of(date: str, user: str, answer: str) -> int:
        marks = by_ans.get(_fb_norm(answer))
        if not marks:
            return 0
        u = " ".join(str(user or "").split()).lower()
        for k, day, v in reversed(marks):
            if k and not u.endswith(k):
                continue
            if day and date and DAY_RE.match(day) and not (_plus_days(date, -1) <= day <= _plus_days(date, 1)):
                continue
            return v
        return 0
    return fb_of


def _plus_days(date: str, n: int) -> str:
    from datetime import date as _d, timedelta
    return (_d.fromisoformat(date) + timedelta(days=n)).isoformat()


def _clean_meta(meta: dict) -> dict:
    """Redact the tool steps and notes like the turn text; a step whose text talks about credentials loses that text."""
    out = {}
    tools = []
    for t in meta.get("tools", []):
        t = dict(t)
        for k in ("args", "result"):
            t[k] = "[hidden]" if talks_secrets(t[k]) else redact(t[k])
        tools.append(t)
    if tools:
        out["tools"] = tools
    checks = [redact(c) for c in meta.get("checks", []) if not talks_secrets(c)]
    if checks:
        out["checks"] = checks
    if meta.get("stopped"):
        out["stopped"] = True
    return out


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
