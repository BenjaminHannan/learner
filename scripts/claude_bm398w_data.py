#!/usr/bin/env python3
"""bm-398w data (benchmarks thread, 2026-09-27; DRAFT, not sealed): practice chats for training the 1B to read 20
store-layout lines that mix the right line(s) with look-alike distractors (RAFT, Zhang et al. 2024). Plan:
artifacts/claude-bm398w-20260927/PLAN-DRAFT.md. Ben's rules: nothing a model trains on is written or judged by Claude
(16:39 UTC 09-26); Luna may write training text (03:47 UTC 09-27). Code picks every fact, name, date and which turn
says what; GPT-6 Luna words the sessions, questions and short answers; code checks every row. No Claude-written
wording reaches a training row: the prompts below give abstract instructions and the values to use, never example
sentences.

  plan   code only: chat plans (two speakers, 6-8 dated sessions, a turn plan saying which turn tells which fact)
           python -B scripts/claude_bm398w_data.py plan --seed N --n K --avoid-names F --avoid-hashes H --out plans.jsonl
  word   on the Mac: Luna words each session from its turn plan (the Director's helper, scripts/claude_luna_codex.py);
         every reply is checked by code at once; a failed check is retried once
           python -B scripts/claude_bm398w_data.py word --plans P --out sess.jsonl [--workers 3 --max-minutes 120
             --max-failed 20 --limit N]
  ask    on the Mac: Luna words one question and a short answer per planned fact of each fully kept chat
           python -B scripts/claude_bm398w_data.py ask --plans P --sess S --out qa.jsonl [same flags]
  count  counts only: chats fully kept, sessions kept, failure reasons (the job's pilot gate)
           python -B scripts/claude_bm398w_data.py count --plans P --sess S [--qa Q] [--limit N]
  build  code only: LoCoMo-schema chats, then one RAFT item per kept question: the evidence turn(s) plus the BM25
         top non-evidence turns of the same chat, 20 in all, laid out as claude_bm398d_evidence.context does,
         with bm-390's system and QA prompt; the answer target is Luna's short answer. Splits by chat.
           python -B scripts/claude_bm398w_data.py build --plans P --sess S --qa Q --out DIR [--dev-share 0.15]
  selftest (no network: a stub stands in for Luna)
Counts only are printed. Outputs hold practice text written by Luna, never benchmark text.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import random
import re
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390 as B  # noqa: E402
import claude_bm398d_evidence as D  # noqa: E402
import claude_lis320_seed as S  # noqa: E402

MODEL = "gpt-6-luna"
RESERVED_SEEDS = set(range(320, 330)) | {4027, 1, 2, 7}
FRIEND_ROLES = {"friend", "best_friend"}     # one speaker never gets both ("X's friend" would be ambiguous)
TRAIN_SEED, PANEL_SEED = 3993, 3994          # plan seeds: training chats, and the fresh held-out panel's chats
TRAIN_MIN_CHATS, PANEL_MIN_ITEMS = 100, 300  # the floor: kept training chats (train and practice-dev), panel items
TURNS, N_LINES = (10, 14), 20
SELF_RELS = [r for r in S.ATTR_RELS if r != "age"]          # numbers are too common in chat to check by code
REL_GLOSS = {"occupation": "what {o} does for a living", "employer": "the company {o} works for",
             "city": "the town {o} lives in", "hometown": "the town {o} grew up in", "hobby": "a hobby of {o}",
             "instrument": "the instrument {o} plays", "favorite_food": "the favourite food of {o}",
             "favorite_color": "the favourite colour of {o}", "allergy": "what {o} is allergic to",
             "dog": "the name of {o}'s dog", "cat": "the name of {o}'s cat", "rabbit": "the name of {o}'s rabbit",
             "parrot": "the name of {o}'s parrot"}
EVENTS = ["concert", "wedding", "museum", "marathon", "hackathon", "barbecue", "auction", "regatta", "rodeo",
          "planetarium", "aquarium", "opera", "carnival", "workshop", "retreat", "tournament", "exhibition",
          "festival", "picnic", "seminar", "recital", "fundraiser", "reunion", "audition"]
PHRASES = {"yesterday": 1, "two days ago": 2, "three days ago": 3, "last Saturday": "Saturday",
           "last Sunday": "Sunday", "last Friday": "Friday", "last Wednesday": "Wednesday"}
TOPICS = [   # small-talk topics chosen to stay clear of the value pools (jobs, hobbies, food, music, pets, gardens)
    "the weekend", "the weather", "films", "travel plans", "a new phone", "a TV series", "a house move", "shopping",
    "traffic", "a birthday present", "coffee", "a video game", "the news", "a lost umbrella"]
NEGATIONS = ["not", "no", "never", "neither", "nor", "isn't", "wasn't", "doesn't", "didn't", "don't", "aren't",
             "weren't", "unknown"]   # a target that negates or doubts its value is dropped (code check, no judge)
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
CALL_TIMEOUT = 240
MAX_ROWS = 3                   # failed rows per id before a rerun stops retrying it (each row is up to 2 calls)
_LOCK = threading.Lock()
FAILED = {"n": 0}
BAD_LINES = {"n": 0}
APOS = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'"})


def _jsonl(p) -> list[dict]:
    """Rows of a JSONL file, split on newlines only. A line that does not parse (a write cut off by a killed run) is
    skipped and counted in BAD_LINES; files are written ASCII-escaped, so a row never holds a raw line separator."""
    out = []
    for x in Path(p).read_text(encoding="utf-8").split("\n"):
        if not x.strip():
            continue
        try:
            out.append(json.loads(x))
        except json.JSONDecodeError:
            BAD_LINES["n"] += 1
    return out


def _dump(row) -> str:
    return json.dumps(row, ensure_ascii=True)


def _append(p: Path, row: dict) -> None:
    with _LOCK, p.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(_dump(row) + "\n")


def gold_date(d: dt.date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def locomo_date(d: dt.date, rng: random.Random) -> str:
    h, m = rng.randint(1, 12), rng.randint(0, 59)
    return f"{h}:{m:02d} {rng.choice(['am', 'pm'])} on {d.day} {MONTHS[d.month - 1]}, {d.year}"


def event_day(day: dt.date, phrase: str) -> dt.date:
    off = PHRASES[phrase]
    if isinstance(off, int):
        return day - dt.timedelta(days=off)
    want = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(off)
    back = (day.weekday() - want) % 7 or 7
    return day - dt.timedelta(days=back)


# ======================================================================= plan (code only)
def plan_chat(cid: str, rng: random.Random, avoid: set) -> dict:
    W = S.World(rng, avoid)
    ga, gb = rng.choice("fm"), rng.choice("fm")
    spk = {"a": {"name": W.person_name(ga), "gender": ga}, "b": {"name": W.person_name(gb), "gender": gb}}
    others, taken = [], set()
    for who in ("a", "b"):
        roles = []
        for _ in range(2):
            g = rng.choice("fm")
            pool = [r for r in (S.FEMALE_ROLES if g == "f" else S.MALE_ROLES) + S.NEUTRAL_ROLES
                    if r not in roles and r not in S.SPOUSE
                    and not (r in FRIEND_ROLES and FRIEND_ROLES & set(roles))]
            role = rng.choice(pool)
            roles.append(role)
            others.append({"name": W.person_name(g), "gender": g, "role": role, "of": who})
    n_sess = rng.choice([6, 7, 8])
    day = dt.date(2021, 1, 1) + dt.timedelta(days=rng.randint(0, 1250))
    sessions = []
    for s in range(n_sess):
        n = rng.randint(*TURNS)
        first = rng.choice("ab")
        sessions.append({"date": locomo_date(day, rng), "day": day.isoformat(), "topic": rng.choice(TOPICS),
                         "turns": [{"speaker": first if k % 2 == 0 else ("b" if first == "a" else "a"), "fact": None}
                                   for k in range(n)]})
        day = day + dt.timedelta(days=rng.randint(4, 40))
    facts = []
    for who in ("a", "b"):
        for rel in rng.sample(SELF_RELS, 4):
            facts.append({"kind": "self", "teller": who, "owner": spk[who]["name"], "rel": rel,
                          "value": S.value_for(rel, W, taken)})
    for o in others:
        rel = rng.choice(SELF_RELS)
        facts.append({"kind": "intro", "teller": o["of"], "owner": o["name"], "role": o["role"]})
        facts.append({"kind": "attr", "teller": o["of"], "owner": o["name"], "role": o["role"], "rel": rel,
                      "value": S.value_for(rel, W, taken)})
    ev = rng.sample(EVENTS, 6)
    for k, who in enumerate("aaabbb"):
        facts.append({"kind": "event", "teller": who, "owner": spk[who]["name"], "value": ev[k],
                      "phrase": rng.choice(sorted(PHRASES))})
    # place facts: one per turn, on a turn of the teller; an intro before its attr, in an earlier session
    slots = [(s, k) for s, x in enumerate(sessions) for k, t in enumerate(x["turns"])]
    rng.shuffle(slots)
    used = set()

    def place(f, lo_session=0, hi_session=None):
        for s, k in slots:
            if (s, k) in used or sessions[s]["turns"][k]["speaker"] != f["teller"] or s < lo_session:
                continue
            if hi_session is not None and s > hi_session:
                continue
            if (s, k - 1) in used or (s, k + 1) in used:
                continue
            used.add((s, k))
            return s, k
        return None

    for f in facts:
        if f["kind"] == "attr":
            continue
        hi = n_sess - 2 if f["kind"] == "intro" else None
        got = place(f, 0, hi)
        if got is None:
            return {}
        f["session"], f["turn"] = got
    for f in facts:
        if f["kind"] != "attr":
            continue
        intro = next(x for x in facts if x["kind"] == "intro" and x["owner"] == f["owner"])
        got = place(f, intro["session"] + 1)
        if got is None:
            return {}
        f["session"], f["turn"] = got
    for i, f in enumerate(facts):
        f["fid"] = f"f{i:02d}"
        sessions[f["session"]]["turns"][f["turn"]]["fact"] = f["fid"]
        if f["kind"] == "event":
            f["gold"] = gold_date(event_day(dt.date.fromisoformat(sessions[f["session"]]["day"]), f["phrase"]))
    return {"chat_id": cid, "speakers": spk, "others": others, "sessions": sessions, "facts": facts}


def plan(a) -> int:
    if a.seed in RESERVED_SEEDS:
        raise SystemExit("bm398w: that seed is reserved (Reading facts, 05:27 UTC)")
    avoid = set()
    if a.avoid_names:
        avoid = {w.strip().lower() for w in Path(a.avoid_names).read_text(encoding="utf-8").split() if w.strip()}
    if a.avoid_hashes:
        S.AVOID_HASHES.update(x.split()[0] for x in Path(a.avoid_hashes).read_text(encoding="utf-8").splitlines()
                              if x.strip())
    if a.avoid_plans:
        for p in _jsonl(a.avoid_plans):
            avoid |= {x["name"].lower() for x in list(p["speakers"].values()) + p["others"]}
    rng = random.Random(a.seed)
    rows, k = [], 0
    while len(rows) < a.n:
        p = plan_chat(f"w{a.seed}-{k:04d}", rng, avoid)
        k += 1
        if p:
            rows.append(p)
    Path(a.out).write_text("".join(_dump(r) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"chats": len(rows), "tries": k, "sessions": sum(len(r["sessions"]) for r in rows),
                      "facts": sum(len(r["facts"]) for r in rows)}))
    return 0


# ======================================================================= prompts (instructions only, no example wording)
def _must(f: dict) -> list[str]:
    """Words a fact's turn must contain, checked by code."""
    if f["kind"] == "intro":
        return [f["owner"], S.role_word(f["role"])]
    if f["kind"] == "attr":
        return [f["owner"], f["value"]]
    if f["kind"] == "event":
        return [f["value"], f["phrase"]]
    return [f["value"]]


def _gloss(f: dict, p: dict) -> str:
    teller = p["speakers"][f["teller"]]["name"]
    if f["kind"] == "self":
        return f"tells a fact about themself: {REL_GLOSS[f['rel']].format(o=teller)} is {f['value']}"
    if f["kind"] == "intro":
        return (f"mentions their {S.role_word(f['role'])}, whose name is {f['owner']} (say both the name and that "
                f"this person is their {S.role_word(f['role'])}); no other fact about {f['owner']}")
    if f["kind"] == "attr":
        return (f"tells a fact about {f['owner']}: {REL_GLOSS[f['rel']].format(o=f['owner'])} is {f['value']}; refer "
                f"to {f['owner']} by name only, never by how they are related to {teller}")
    return f"tells what they went to {f['phrase']}: a {f['value']}; say \"{f['phrase']}\" in the message"


def forbidden(p: dict, keep: list[str]) -> list[str]:
    words = {f["value"] for f in p["facts"] if f["kind"] != "intro"} | {o["name"] for o in p["others"]}
    words |= set(PHRASES)
    return sorted(w for w in words if w.lower() not in {k.lower() for k in keep})


def session_prompt(p: dict, s: int) -> str:
    x = p["sessions"][s]
    A, Bn = p["speakers"]["a"]["name"], p["speakers"]["b"]["name"]
    fx = {f["fid"]: f for f in p["facts"]}
    lines = []
    for k, t in enumerate(x["turns"]):
        who = p["speakers"][t["speaker"]]["name"]
        if t["fact"] is None:
            lines.append(f"{k + 1}. {who}: small talk about {x['topic']}.")
        else:
            f = fx[t["fact"]]
            must = "; ".join(f'"{w}"' for w in _must(f))
            lines.append(f"{k + 1}. {who}: {_gloss(f, p)}. The message must contain, exactly as written: {must}.")
    names = sorted({fx[t["fact"]]["owner"] for t in x["turns"] if t["fact"] and fx[t["fact"]]["kind"] in ("intro", "attr")})
    return (f"Write one chat session between two friends, {A} and {Bn}, who text each other. It takes place at "
            f"{x['date']}.\nReturn a JSON list of exactly {len(x['turns'])} objects, one per message, in this order, "
            f"each {{\"speaker\": \"<name>\", \"text\": \"<message>\"}}.\n\nMessage by message:\n" + "\n".join(lines)
            + "\n\nRules:\n- Casual, natural texting in English, one to three sentences per message.\n"
            f"- Use no person names except {A}, {Bn}" + (", " + ", ".join(names) if names else "") + ".\n"
            "- Invent no other people, pets, towns, companies, jobs or dates.\n"
            "- A small-talk message must not contain any of these: " + ", ".join(f'"{w}"' for w in forbidden(p, []))
            + ".\n- A fact message contains its own quoted words and none of the other quoted words above.\n"
            "- Output only the JSON list, nothing else.")


def question_prompt(p: dict, fids: list[str]) -> str:
    A, Bn = p["speakers"]["a"]["name"], p["speakers"]["b"]["name"]
    fx = {f["fid"]: f for f in p["facts"]}
    lines = []
    for fid in fids:
        f = fx[fid]
        if f["kind"] == "self":
            lines.append(f"- id {fid}: {REL_GLOSS[f['rel']].format(o=f['owner'])} is {f['value']}. Ask about "
                         f"{f['owner']} by name. The question must not contain \"{f['value']}\". The answer must "
                         f"contain \"{f['value']}\".")
        elif f["kind"] == "attr":
            teller = p["speakers"][f["teller"]]["name"]
            rel = REL_GLOSS[f["rel"]].format(o=f"{teller}'s {S.role_word(f['role'])}")
            lines.append(f"- id {fid}: {rel} is {f['value']}. Ask about \"{teller}'s {S.role_word(f['role'])}\" "
                         f"without that person's name. The question must not contain \"{f['value']}\" or "
                         f"\"{f['owner']}\". The answer must contain \"{f['value']}\".")
        else:
            lines.append(f"- id {fid}: {f['owner']} went to a {f['value']} on {f['gold']}. Ask when. The question "
                         f"must not contain a date. The answer must give the date as \"{f['gold']}\".")
    return (f"Here are facts from a long chat between {A} and {Bn}. For each fact, write one question that someone "
            f"could ask about it later, and a short answer of a few words.\nReturn a JSON list of objects "
            f"{{\"id\": \"<id>\", \"question\": \"<question>\", \"answer\": \"<answer>\"}}, one per fact, in the same "
            f"order.\n\nFacts:\n" + "\n".join(lines) + "\n\nRules:\n- Ask each question plainly, as a person would.\n"
            "- Output only the JSON list, nothing else.")


# ======================================================================= code checks
def _has(text: str, w: str) -> bool:
    t, w = text.translate(APOS).lower(), w.translate(APOS).lower()
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])", t) is not None


ORG_WORDS = {w.lower() for w in S.ORG_SUF}


def value_words(v: str) -> list[str]:
    """Words of a value that give it away in a question: each word of 4+ letters (not a company-type word such as
    Foods), with and without a trailing s."""
    out = set()
    for w in re.findall(r"[A-Za-z]+", v):
        if len(w) >= 4 and w.lower() not in ORG_WORDS:
            out |= {w.lower(), w.lower()[:-1] if w.lower().endswith("s") else w.lower() + "s"}
    return sorted(out)


def parse_list(raw: str):
    m = re.search(r"\[.*\]", raw or "", re.S)
    try:
        v = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None
    return v if isinstance(v, list) and all(isinstance(x, dict) for x in v) else None


def check_session(p: dict, s: int, turns) -> str:
    """'' if the worded session fits its plan, else the first reason."""
    x = p["sessions"][s]
    if turns is None or len(turns) != len(x["turns"]):
        return "count"
    fx = {f["fid"]: f for f in p["facts"]}
    watch = forbidden(p, [])
    for k, (t, slot) in enumerate(zip(turns, x["turns"])):
        if t.get("speaker") != p["speakers"][slot["speaker"]]["name"] or not isinstance(t.get("text"), str):
            return "speaker"
        text = t["text"]
        mine = _must(fx[slot["fact"]]) if slot["fact"] else []
        if any(not _has(text, w) for w in mine):
            return "missing"
        if any(_has(text, w) for w in watch if w.lower() not in {m.lower() for m in mine}):
            return "leak"
    return ""


def date_ok(answer: str, gold: str) -> bool:
    d, m, y = gold.split()
    return _has(answer, d) and _has(answer, m) and _has(answer, y)


def check_qa(p: dict, f: dict, q: dict) -> str:
    qs, an = str(q.get("question", "")), str(q.get("answer", ""))
    if not qs.strip() or not an.strip():
        return "empty"
    if f["kind"] == "event":
        d, m, y = f["gold"].split()
        if _has(qs, m) or _has(qs, y) or not date_ok(an, f["gold"]):
            return "date"
        if any(date_ok(an, g["gold"]) for g in p["facts"] if g["kind"] == "event" and g["gold"] != f["gold"]):
            return "rival"
        return "negation" if any(_has(an, w) for w in NEGATIONS) else ""
    if _has(qs, f["value"]) or any(_has(qs, w) for w in value_words(f["value"])) or not _has(an, f["value"]):
        return "value"
    if any(_has(an, w) for w in NEGATIONS):
        return "negation"
    if f["kind"] == "attr" and _has(qs, f["owner"]):
        return "name"
    same_rel = [g["value"] for g in p["facts"] if g.get("rel") == f.get("rel") and g["fid"] != f["fid"]]
    if any(_has(an, v) for v in same_rel):
        return "rival"
    return ""


# ======================================================================= Luna calls (the Mac)
def _caller():
    import claude_luna_codex as L
    # 240 s per try, the helper's 3 tries: at most 12 minutes a call, so a run started under --max-minutes 45
    # ends inside the builders' 80-minute command limit even when its last jobs fail twice
    return lambda text: L.call(text, model=MODEL, timeout=CALL_TIMEOUT) or ""


def _guard(raw: str) -> str:
    if re.search(r"sk-[A-Za-z0-9_-]{12,}", raw or ""):
        raise SystemExit("bm398w: a reply looked like a key; nothing written")
    return raw


def run_jobs(jobs: list[dict], out: Path, call, workers: int, max_minutes: float, max_failed: int, check) -> dict:
    """jobs: {"id", "prompt"}; each reply is checked at once by check(job, raw) -> reason; one retry on a failed
    check; a call that raises counts as a route failure and is written with an empty raw. A rerun skips ids that
    have a kept row or already MAX_ROWS failed rows, so each rerun gives a failed id one more try (rows are only
    ever appended; the kept row is the one used)."""
    rows = _jsonl(out) if out.exists() else []
    fails = Counter(r["id"] for r in rows if not r["ok"] and r["reason"] != "call")
    done = {r["id"] for r in rows if r["ok"]} | {i for i, n in fails.items() if n >= MAX_ROWS}
    todo = [j for j in jobs if j["id"] not in done]
    if out.exists() and out.stat().st_size and not out.read_bytes().endswith(b"\n"):
        with _LOCK, out.open("a", encoding="utf-8", newline="\n") as fh:   # a cut-off last line stays on its own
            fh.write("\n")
    t0, tot = time.time(), Counter()

    def one(j):
        if (max_minutes and (time.time() - t0) / 60 >= max_minutes) or FAILED["n"] > max_failed:
            with _LOCK:
                tot["not_run"] += 1
            return
        reason, raw = "call", ""
        for attempt in (1, 2):
            try:
                raw = _guard(call(j["prompt"]))
            except SystemExit:
                raise
            except Exception as e:                                   # a failed call is counted, never guessed
                with _LOCK:
                    FAILED["n"] += 1
                print(f"[bm398w] call failed: {type(e).__name__}", flush=True)
                raw, reason = "", "call"
                break
            reason = check(j, raw)
            if not reason:
                break
        _append(out, {"id": j["id"], "model": MODEL, "temperature": None, "attempts": attempt, "ok": not reason,
                      "reason": reason, "raw": raw})
        with _LOCK:
            tot["ok" if not reason else reason] += 1

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, todo))
    return {"jobs": len(jobs), "skipped": len(done & {j["id"] for j in jobs}), **dict(tot),
            "failed_calls": FAILED["n"], "bad_lines": BAD_LINES["n"],
            "minutes": round((time.time() - t0) / 60, 1)}


def word(a, call=None) -> int:
    plans = _jsonl(a.plans)[: a.limit or None]
    by = {p["chat_id"]: p for p in plans}
    jobs = [{"id": f"{p['chat_id']}/s{s}", "prompt": session_prompt(p, s)} for p in plans for s in range(len(p["sessions"]))]

    def check(j, raw):
        cid, s = j["id"].split("/s")
        return check_session(by[cid], int(s), parse_list(raw))

    print(json.dumps(run_jobs(jobs, Path(a.out), call or _caller(), a.workers, a.max_minutes, a.max_failed, check)))
    return 0


def kept_chats(plans: list[dict], sess_rows: list[dict]) -> dict:
    ok = {r["id"]: r for r in sess_rows if r["ok"]}
    out = {}
    for p in plans:
        ids = [f"{p['chat_id']}/s{s}" for s in range(len(p["sessions"]))]
        if all(i in ok for i in ids):
            out[p["chat_id"]] = [parse_list(ok[i]["raw"]) for i in ids]
    return out


def asked_fids(p: dict) -> list[str]:
    return [f["fid"] for f in p["facts"] if f["kind"] != "intro"]


def ask(a, call=None) -> int:
    plans = _jsonl(a.plans)
    kept = kept_chats(plans, _jsonl(a.sess))
    by = {p["chat_id"]: p for p in plans}
    jobs = [{"id": cid, "prompt": question_prompt(by[cid], asked_fids(by[cid]))} for cid in kept][: a.limit or None]

    def check(j, raw):
        v = parse_list(raw)
        return "" if v is not None and [x.get("id") for x in v] == asked_fids(by[j["id"]]) else "shape"

    print(json.dumps(run_jobs(jobs, Path(a.out), call or _caller(), a.workers, a.max_minutes, a.max_failed, check)))
    return 0


def count(a) -> int:
    """Counts only, for the job's gates: chats fully kept, sessions kept and failed, failure reasons."""
    plans = _jsonl(a.plans)[: a.limit or None]
    rows = _jsonl(a.sess) if Path(a.sess).exists() else []
    ids = {f"{p['chat_id']}/s{s}" for p in plans for s in range(len(p["sessions"]))}
    ok = {r["id"] for r in rows if r["ok"] and r["id"] in ids}
    res = {"chats": len(plans), "kept_chats": len(kept_chats(plans, rows)), "sessions": len(ids),
           "sessions_kept": len(ok), "sessions_never_tried": len(ids - {r["id"] for r in rows}),
           "failed_rows_by_reason": dict(Counter(r["reason"] for r in rows if not r["ok"] and r["id"] in ids))}
    if a.qa and Path(a.qa).exists():
        qa = _jsonl(a.qa)
        res["qa_chats_kept"] = len({r["id"] for r in qa if r["ok"]} & {p["chat_id"] for p in plans})
    print(json.dumps(res))
    return 0


# ======================================================================= build (code only)
def to_locomo(p: dict, worded: list) -> tuple[dict, dict]:
    """LoCoMo-schema chat, and fid -> the dia_ids that carry it."""
    conv = {"speaker_a": p["speakers"]["a"]["name"], "speaker_b": p["speakers"]["b"]["name"]}
    where = {}
    for s, (x, turns) in enumerate(zip(p["sessions"], worded)):
        conv[f"session_{s + 1}_date_time"] = x["date"]
        conv[f"session_{s + 1}"] = []
        for k, (t, slot) in enumerate(zip(turns, x["turns"])):
            did = f"D{s + 1}:{k + 1}"
            conv[f"session_{s + 1}"].append({"speaker": t["speaker"], "dia_id": did, "text": t["text"]})
            if slot["fact"]:
                where[slot["fact"]] = did
    return {"sample_id": p["chat_id"], "conversation": conv, "qa": []}, where


def tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def bm25_order(query: str, docs: list[str], k1: float = 1.5, b: float = 0.75) -> list[int]:
    toks = [tokens(d) for d in docs]
    n, avg = len(toks), sum(map(len, toks)) / max(1, len(toks))
    df = Counter(w for t in toks for w in set(t))
    q = tokens(query)

    def score(t):
        tf = Counter(t)
        return sum(math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5)) * tf[w] * (k1 + 1)
                   / (tf[w] + k1 * (1 - b + b * len(t) / avg)) for w in q if w in tf)
    return sorted(range(n), key=lambda i: (-score(toks[i]), i))


def raft_positions(conv: dict, question: str, ev: list[int], n: int = N_LINES) -> list[int]:
    items = D.items_of(conv)
    docs = [B.turn_text(t) for _s, _d, t in items]
    rest = [i for i in bm25_order(question, docs) if i not in ev]
    return sorted(set(ev) | set(rest[: max(0, n - len(ev))]))


CATEGORY = {"self": 4, "attr": 1, "event": 2}


def build(a) -> int:
    plans = {p["chat_id"]: p for p in _jsonl(a.plans)}
    kept = kept_chats(list(plans.values()), _jsonl(a.sess))
    qa_rows = {r["id"]: r for r in _jsonl(a.qa) if r["ok"]}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(3998)
    cids = sorted(c for c in kept if c in qa_rows)
    want = f"w{PANEL_SEED if a.panel else TRAIN_SEED}-"
    if not getattr(a, "any_seed", False) and any(not c.startswith(want) for c in plans):
        raise SystemExit(f"bm398w: build {'--panel ' if a.panel else ''}takes only chats planned from seed {want[1:-1]}")
    dev_ids = set(rng.sample(cids, round(a.dev_share * len(cids)))) if cids and not a.panel else set()
    chats, rows, why = [], ({"panel": []} if a.panel else {"train": [], "dev": []}), Counter()
    for cid in cids:
        p = plans[cid]
        conv, where = to_locomo(p, kept[cid])
        fx = {f["fid"]: f for f in p["facts"]}
        for q in parse_list(qa_rows[cid]["raw"]):
            f = fx[q["id"]]
            r = check_qa(p, f, q)
            if r:
                why[r] += 1
                continue
            ev = [where[f["fid"]]]
            if f["kind"] == "attr":
                intro = next(x for x in p["facts"] if x["kind"] == "intro" and x["owner"] == f["owner"])
                ev = [where[intro["fid"]]] + ev
            conv["qa"].append({"question": q["question"], "answer": q["answer"], "evidence": ev,
                               "category": CATEGORY[f["kind"]], "kind": f["kind"],
                               "gold": f["gold"] if f["kind"] == "event" else f["value"]})
        items = D.items_of(conv)
        for i, qa in enumerate(conv["qa"]):
            evp = D.evidence(conv, qa)
            keep = raft_positions(conv, qa["question"], evp)
            user = D.context(conv, items, keep) + "\n\n" + B.QA_PROMPT.format(B.question_text(cid, i, qa))
            split = "panel" if a.panel else "dev" if cid in dev_ids else "train"
            # the training target is Luna's short answer; dev and panel rows carry the code's gold value instead,
            # so the trainer's report-only dev check and the blind judges compare with the code's value
            rows[split].append(
                {"id": f"{cid}#{i}", "system": B.LOCOMO_SYSTEM, "user": user,
                 "answer": qa["answer"] if split == "train" else qa["gold"], "gold": qa["gold"],
                 "question": qa["question"], "category": qa["category"], "kind": qa["kind"], "layout": "raft20",
                 "writer": MODEL, "evidence": qa["evidence"], "lines": keep, "evidence_lines": len(evp)})
        chats.append(conv)
    for k, v in rows.items():
        (out / f"{k}.jsonl").write_text("".join(_dump(r) + "\n" for r in v), encoding="utf-8")
    (out / "chats.json").write_text(json.dumps(chats, ensure_ascii=True), encoding="utf-8")
    res = {"chats": len(chats), "dev_chats": len(dev_ids), **{f"{k}_items": len(v) for k, v in rows.items()},
           "kinds": dict(Counter(r["kind"] for v in rows.values() for r in v)),
           "dropped_questions": dict(why),
           "sha256": {k: hashlib.sha256((out / f"{k}.jsonl").read_bytes()).hexdigest() for k in rows}}
    short = (len(rows["panel"]) < PANEL_MIN_ITEMS) if a.panel else (len(chats) < TRAIN_MIN_CHATS)
    res["floor"] = "DATA-SHORT" if short else "OK"
    (out / "counts.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))
    return 3 if short else 0


# ======================================================================= selftest (stub Luna)
def _stub_session(p: dict, s: int, bad: bool = False) -> str:
    fx = {f["fid"]: f for f in p["facts"]}
    out = []
    for k, t in enumerate(p["sessions"][s]["turns"]):
        text = f"hey number {k}"
        if t["fact"]:
            text = "so " + " and ".join(_must(fx[t["fact"]]))
        if bad and k == 0:
            text += " " + forbidden(p, [])[0]
        out.append({"speaker": p["speakers"][t["speaker"]]["name"], "text": text})
    return json.dumps(out)


def _stub_qa(p: dict) -> str:
    fx = {f["fid"]: f for f in p["facts"]}
    out = []
    for fid in asked_fids(p):
        f = fx[fid]
        ans = f["gold"] if f["kind"] == "event" else f["value"]
        out.append({"id": fid, "question": f"what about item {fid}?", "answer": ans})
    return json.dumps(out)


def selftest(a) -> int:
    import tempfile
    ok = {}
    rng = random.Random(11)
    p = plan_chat("w11-0000", rng, set())
    fx = p["facts"]
    ok["a plan has 8 self, 4 intro, 4 attr, 6 event facts"] = Counter(f["kind"] for f in fx) == Counter(
        {"self": 8, "intro": 4, "attr": 4, "event": 6})
    ok["each fact sits on a turn of its teller, one per turn"] = all(
        p["sessions"][f["session"]]["turns"][f["turn"]]["speaker"] == f["teller"]
        and p["sessions"][f["session"]]["turns"][f["turn"]]["fact"] == f["fid"] for f in fx)
    ok["an intro comes in an earlier session than its attr"] = all(
        next(x for x in fx if x["kind"] == "intro" and x["owner"] == f["owner"])["session"] < f["session"]
        for f in fx if f["kind"] == "attr")
    ok["values are unique in a chat"] = len({f["value"] for f in fx if "value" in f}) == len([f for f in fx if "value" in f])
    ok["reserved seeds refused"] = 4027 in RESERVED_SEEDS and 324 in RESERVED_SEEDS
    ok["last Saturday from a Saturday is a week back"] = event_day(dt.date(2023, 5, 13), "last Saturday") == dt.date(2023, 5, 6)
    ok["yesterday"] = event_day(dt.date(2023, 5, 1), "yesterday") == dt.date(2023, 4, 30)
    good = [check_session(p, s, parse_list(_stub_session(p, s))) for s in range(len(p["sessions"]))]
    ok["a compliant session passes"] = all(r == "" for r in good)
    ok["a leaked value fails"] = check_session(p, 0, parse_list(_stub_session(p, 0, bad=True))) == "leak"
    ok["a wrong count fails"] = check_session(p, 0, parse_list(_stub_session(p, 0))[:-1]) == "count"
    ok["prompts carry no example sentence, only instructions and values"] = all(
        "e.g." not in session_prompt(p, s) and "for example" not in session_prompt(p, s).lower()
        for s in range(len(p["sessions"])))
    ev = next(f for f in fx if f["kind"] == "event")
    ok["date check needs day, month and year"] = date_ok(f"on {ev['gold']}", ev["gold"]) and not date_ok(
        "sometime in " + ev["gold"].split()[1], ev["gold"])
    ok["an answer that negates its value fails"] = check_qa(p, fx[0], {"question": "what about it?",
                                                                       "answer": f"not {fx[0]['value']}"}) == "negation"
    multi = {"fid": "fx", "kind": "self", "rel": "instrument", "value": "bass guitar", "owner": "X"}
    ok["a question holding a word of the value fails (guitar, taco)"] = (
        check_qa(p, multi, {"question": "Which guitar does X play?", "answer": "bass guitar"}) == "value"
        and check_qa(p, dict(multi, value="tacos", rel="favorite_food"),
                     {"question": "Does X like a taco?", "answer": "tacos"}) == "value")
    ok["a curly-apostrophe negation fails"] = check_qa(p, fx[0], {"question": "what about it?",
                                                                   "answer": f"it isn\u2019t {fx[0]['value']}"}) == "negation"
    evs = [f for f in fx if f["kind"] == "event"]
    ok["a dated answer holding another event's date fails"] = check_qa(p, evs[0], {
        "question": "when?", "answer": f"{evs[0]['gold']} or {next(g['gold'] for g in evs if g['gold'] != evs[0]['gold'])}"}) == "rival"
    many = [plan_chat(f"w11-{k:04d}", random.Random(k), set()) for k in range(40)]
    many = [x for x in many if x]
    ok["fact messages are never next to each other"] = all(
        not (t["fact"] and x["sessions"][si]["turns"][k + 1]["fact"])
        for x in many for si, ss in enumerate(x["sessions"]) for k, t in enumerate(ss["turns"][:-1]))
    ok["no speaker has both a friend and a best friend"] = all(
        len(FRIEND_ROLES & {o["role"] for o in x["others"] if o["of"] == w}) <= 1 for x in many for w in "ab")
    ok["a question that gives away the value fails"] = check_qa(p, fx[0], {"question": f"is it {fx[0]['value']}?",
                                                                           "answer": fx[0]["value"]}) == "value"
    ok["bm25 ranks the matching doc first"] = bm25_order("red kite festival", ["blue sky", "the red kite festival",
                                                                                "kite"])[0] == 1
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        plans = [p, plan_chat("w11-0001", rng, set())]
        (td / "plans.jsonl").write_text("".join(json.dumps(x) + "\n" for x in plans), encoding="utf-8")
        by = {x["chat_id"]: x for x in plans}
        calls = Counter()

        def luna(prompt):
            calls["n"] += 1
            for x in plans:
                for s in range(len(x["sessions"])):
                    if prompt == session_prompt(x, s):
                        return _stub_session(x, s)
                if prompt == question_prompt(x, asked_fids(x)):
                    return _stub_qa(x)
            raise RuntimeError("stub: unknown prompt")

        ns = argparse.Namespace(plans=str(td / "plans.jsonl"), out=str(td / "sess.jsonl"), workers=2, max_minutes=0,
                                max_failed=5, limit=0)
        word(ns, luna)
        n_sess = sum(len(x["sessions"]) for x in plans)
        ok["word writes one checked row per session"] = len(_jsonl(td / "sess.jsonl")) == n_sess and all(
            r["ok"] for r in _jsonl(td / "sess.jsonl"))
        word(ns, luna)
        ok["word resumes without new calls"] = calls["n"] == n_sess
        flaky = {"n": 0}

        def luna_bad_once(prompt):
            flaky["n"] += 1
            return "[]" if flaky["n"] <= 2 else luna(prompt)

        ns2 = argparse.Namespace(plans=str(td / "plans.jsonl"), out=str(td / "sess2.jsonl"), workers=1,
                                 max_minutes=0, max_failed=5, limit=1)
        word(ns2, luna_bad_once)
        first = _jsonl(td / "sess2.jsonl")
        word(ns2, luna_bad_once)
        again = _jsonl(td / "sess2.jsonl")
        n0 = len(plans[0]["sessions"])
        ok["a rerun retries only the failed session, and keeps the failed row"] = (
            sum(not r["ok"] for r in first) == 1 and len(again) == n0 + 1 and sum(r["ok"] for r in again) == n0)
        ask(argparse.Namespace(plans=str(td / "plans.jsonl"), sess=str(td / "sess.jsonl"), out=str(td / "qa.jsonl"),
                               workers=2, max_minutes=0, max_failed=5, limit=0), luna)
        build(argparse.Namespace(plans=str(td / "plans.jsonl"), sess=str(td / "sess.jsonl"), qa=str(td / "qa.jsonl"),
                                 out=str(td / "out"), dev_share=0.5, panel=False, any_seed=True))
        build(argparse.Namespace(plans=str(td / "plans.jsonl"), sess=str(td / "sess.jsonl"), qa=str(td / "qa.jsonl"),
                                 out=str(td / "pan"), dev_share=0.5, panel=True, any_seed=True))
        pan = _jsonl(td / "pan" / "panel.jsonl")
        ok["panel mode puts every item in the panel, answer = the code's gold"] = len(pan) == 36 and all(
            r["answer"] == r["gold"] for r in pan) and not (td / "pan" / "train.jsonl").exists()
        try:
            build(argparse.Namespace(plans=str(td / "plans.jsonl"), sess=str(td / "sess.jsonl"),
                                     qa=str(td / "qa.jsonl"), out=str(td / "x"), dev_share=0.5, panel=True))
            ok["build refuses chats from another seed"] = False
        except SystemExit:
            ok["build refuses chats from another seed"] = True
        tr = _jsonl(td / "out" / "train.jsonl") + _jsonl(td / "out" / "dev.jsonl")
        ok["build makes 18 items per chat"] = len(tr) == 36
        chats = json.loads((td / "out" / "chats.json").read_text(encoding="utf-8"))
        conv = chats[0]
        items = D.items_of(conv)
        pos_ok = True
        for i, qa in enumerate(conv["qa"]):
            evp = D.evidence(conv, qa)
            keep = raft_positions(conv, qa["question"], evp)
            pos_ok &= len(keep) == min(N_LINES, len(items)) and set(evp) <= set(keep) and len(evp) == (2 if qa["kind"] == "attr" else 1)
        ok["every item holds its evidence among 20 lines (2 for two-step)"] = pos_ok
        row = tr[0]
        ok["rows use bm-390's system and QA prompt, and the layout's start line"] = (
            row["system"] == B.LOCOMO_SYSTEM and "Based on the above conversations" in row["user"]
            and row["user"].startswith("Below is a conversation between two people"))
        ok["dated questions get the CAT2 suffix"] = any(B.CAT2_SUFFIX.strip() in r["user"] for r in tr if r["kind"] == "event")
        ok["every row records its writer"] = all(r["writer"] == MODEL for r in tr)
        ok["dev rows carry the gold value, train rows Luna's answer"] = all(
            r["answer"] == r["gold"] for r in _jsonl(td / "out" / "dev.jsonl"))
        ok["the two chats never share a split"] = len({r["id"].split("#")[0] for r in _jsonl(td / "out" / "dev.jsonl")}
                                                       & {r["id"].split("#")[0] for r in _jsonl(td / "out" / "train.jsonl")}) == 0
        down = {"n": 0}

        def luna_down(prompt):              # session 0's route fails on its first MAX_ROWS runs
            if prompt == session_prompt(plans[0], 0) and down["n"] < MAX_ROWS:
                down["n"] += 1
                raise RuntimeError("route down")
            return luna(prompt)

        ns3 = argparse.Namespace(plans=str(td / "plans.jsonl"), out=str(td / "sess3.jsonl"), workers=1,
                                 max_minutes=0, max_failed=99, limit=1)
        plans1 = [plans[0]]
        (td / "one.jsonl").write_text(_dump(plans1[0]) + "\n", encoding="utf-8")
        ns3.plans = str(td / "one.jsonl")
        for _ in range(MAX_ROWS + 1):
            word(ns3, luna_down)
        rows3 = _jsonl(td / "sess3.jsonl")
        ok["failed calls never use up a session's tries"] = (
            sum(r["ok"] for r in rows3) == len(plans1[0]["sessions"])
            and sum(r["reason"] == "call" for r in rows3) == MAX_ROWS)
        weird = td / "weird.jsonl"
        _append(weird, {"id": "a", "raw": "line\u2028sep\u0085next"})
        with weird.open("a", encoding="utf-8") as fh:
            fh.write('{"id": "b", "ra')
        ok["a line separator in text survives, a cut-off last line is skipped"] = (
            [r["id"] for r in _jsonl(weird)] == ["a"] and _jsonl(weird)[0]["raw"] == "line\u2028sep\u0085next")
        plan(argparse.Namespace(seed=3993, n=3, avoid_names="", avoid_hashes="", avoid_plans="",
                                out=str(td / "tp.jsonl")))
        plan(argparse.Namespace(seed=3994, n=3, avoid_names="", avoid_hashes="", avoid_plans=str(td / "tp.jsonl"),
                                out=str(td / "pp.jsonl")))

        def names(f):
            return {x["name"].lower() for q in _jsonl(f) for x in list(q["speakers"].values()) + q["others"]}
        ok["panel plans use no name from the training plans"] = not (names(td / "tp.jsonl") & names(td / "pp.jsonl"))
        del by
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("BM398W-DATA-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    return 0 if all(ok.values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "word", "ask", "build", "count", "selftest"])
    for x in ("plans", "sess", "qa", "out", "avoid_names", "avoid_hashes", "avoid_plans"):
        ap.add_argument("--" + x.replace("_", "-"), dest=x, default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--max-minutes", type=float, default=45)
    ap.add_argument("--max-failed", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dev-share", type=float, default=0.15)
    ap.add_argument("--panel", action="store_true")
    a = ap.parse_args()
    return {"plan": plan, "word": word, "ask": ask, "build": build, "count": count, "selftest": selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
