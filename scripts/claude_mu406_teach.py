#!/usr/bin/env python3
"""mu-406 teaching replies: GPT-6 Luna writes the assistant's reply to each session-2 turn, in order ("Making things
up about you", 2026-09-27). New file; standard library only (it runs on the Mac through scripts/claude_luna_codex.py).
Plan: artifacts/claude-mu406-20260926/PLAN-draft-3.md (draft; the sealed plan decides).

One Luna call per turn. Luna sees session 1's user messages, session 2's user turns so far and its own earlier
replies. It never sees a later turn. The prompt describes the job and gives no example reply.
Code checks every reply before the next turn is written. A failed call and a failed check each count as one
attempt, up to 3 per turn. If all 3 fail, the chat stops there and its later turns get no reply.
Checks: non-empty; at most MAX_CHARS characters; none of mu-407's scan strings; on the ask turn the stored value
appears (the substring test of claude_mu405_talk.ask_right); no person, pet or place name from the fact generator's
lists (case as written) that appears in none of the chat's user messages (PLAN-review-1.md, narrowed to name-like
slots at the Thread manager's 09:53 UTC review); not the same as an earlier reply in the chat.

  write --items I --facts F --out OUT [--workers 2] [--max-minutes 60]   finished chats are skipped on a restart
  stats --out OUT      counts only; no reply text is printed
  selftest             no network
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_mu405_facts as F  # noqa: E402

MODEL = "gpt-6-luna"   # pinned here; nothing passes another model id through
ATTEMPTS = 3
MAX_CHARS = 500
SCAN = ("usage limit", "rate limit", "error:", "as an ai", "openai", "codex", "i can't help with")  # mu-407's list
# Name-like slots only (the Thread manager, 09:53 UTC): people, pets and places, matched case-sensitively as written
# (capitalised), so "pepper" or "olive" as food does not count but "Pepper" does. Invented foods, days and hobbies
# are left to the teacher gate's claims judges.
NAME_SLOTS = {"person": F.NAMES, "pet": F.PET_NAMES, "place": F.CITIES}

HEAD = (
    "You are the assistant in a chat app used by one person. Below are the messages this person sent in an earlier "
    "conversation with you, and then today's conversation so far. Write your reply to their latest message only.\n\n"
    "How to reply:\n"
    "- Respond to what they just wrote in their latest message.\n"
    "- Use something from the earlier conversation only when the latest message calls for it.\n"
    "- Never state anything about the person, their life or the people in it that they did not tell you. Do not "
    "guess how they feel or what has happened to them.\n"
    "- If they ask about something they told you before, answer with that exact detail.\n"
    "- If they ask about something they never told you, say you don't know.\n"
    "- Keep it short and plain: one to three sentences, no lists, no emoji.\n\n")
TAIL = 'Answer with exactly one line of JSON and nothing else: {"reply": "..."}'


def teach_prompt(item: dict, i: int, replies: list[str]) -> str:
    early = "".join(f'{n}. "{t["text"]}"\n' for n, t in enumerate(item["session1"], 1))
    today = ""
    for k in range(i):
        today += f"Person: {item['session2'][k]['text']}\nYou: {replies[k]}\n"
    today += f"Person: {item['session2'][i]['text']}\n"
    return (HEAD + "Their messages in the earlier conversation, oldest first:\n" + early + "\n"
            "Today's conversation so far (reply to the last message):\n" + today + "\n" + TAIL)


def last_json(text: str):
    for m in reversed(list(re.finditer(r"\{.*\}", text or "", re.S))):
        s = m.group(0)
        for end in range(len(s), 0, -1):
            if s[end - 1] != "}":
                continue
            try:
                return json.loads(s[:end])
            except ValueError:
                continue
    return None


def norm(t: str) -> str:
    return " ".join(t.lower().split())


def invented(reply: str, item: dict) -> list[str]:
    """Slot kinds of name-like values the reply uses that no user message in the chat contains (any case)."""
    said = " ".join(t["text"] for t in item["session1"] + item["session2"])
    out = []
    for kind, values in NAME_SLOTS.items():
        for v in values:
            pat = r"\b" + re.escape(v) + r"\b"
            if re.search(pat, reply) and not re.search(pat, said, re.I):
                out.append(kind)
    return sorted(set(out))


def check_reply(obj, item: dict, fact: dict, i: int, earlier: list[str]) -> str:
    """Returns the reply or raises ValueError naming the first failed check."""
    if not isinstance(obj, dict) or not isinstance(obj.get("reply"), str):
        raise ValueError("no_json")
    r = obj["reply"].strip()
    if not r:
        raise ValueError("empty")
    if len(r) > MAX_CHARS:
        raise ValueError("too_long")
    if any(s in r.lower() for s in SCAN):
        raise ValueError("scan")
    if item["session2"][i]["kind"] == "ask" and fact["facts"][fact["ask_index"]]["value"].lower() not in r.lower():
        raise ValueError("ask_value_missing")
    inv = invented(r, item)
    if inv:
        raise ValueError("invented_" + inv[0])
    if norm(r) in {norm(e) for e in earlier}:
        raise ValueError("repeat")
    return r


def luna_call(text: str) -> str:
    import claude_luna_codex as LC
    return LC.call(text, model=MODEL) or ""


def teach_one(item: dict, fact: dict, caller) -> dict:
    t0, replies, attempts, fails, last = time.time(), [], [], Counter(), ""
    for i in range(len(item["session2"])):
        got = None
        for attempt in range(1, ATTEMPTS + 1):
            try:
                got = check_reply(last_json(caller(teach_prompt(item, i, replies))), item, fact, i, replies)
            except ValueError as e:
                last = str(e)
                fails[last] += 1
            except Exception:  # noqa: BLE001  (a failed call is one attempt)
                last = "call_error"
                fails[last] += 1
            if got is not None:
                attempts.append(attempt)
                break
        if got is None:
            return {"item_id": item["item_id"], "ok": False, "turns": len(replies), "replies": replies,
                    "attempts": attempts, "fails": dict(fails), "stopped_at": i, "stop_reason": last,
                    "stop_kind": item["session2"][i]["kind"], "seconds": round(time.time() - t0, 1)}
        replies.append(got)
    return {"item_id": item["item_id"], "ok": True, "turns": len(replies), "replies": replies, "attempts": attempts,
            "fails": dict(fails), "seconds": round(time.time() - t0, 1)}


def write_all(items: list[dict], facts: dict, out: Path, caller, workers: int, max_minutes: float) -> dict:
    done = set()
    if out.exists():
        done = {json.loads(x)["item_id"] for x in out.read_text(encoding="utf-8").splitlines() if x.strip()}
    todo = [it for it in items if it["item_id"] not in done]
    t0, stopped, n = time.time(), "done", 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for s in range(0, len(todo), 2 * workers):
            if (time.time() - t0) / 60 > max_minutes:
                stopped = "time"
                break
            res = list(ex.map(lambda it: teach_one(it, facts[it["item_id"]], caller), todo[s:s + 2 * workers]))
            with out.open("a", encoding="utf-8") as fh:
                for r in res:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += len(res)
            print(f"[mu406t] {n}/{len(todo)} chats, {sum(r['ok'] for r in res)} whole in this batch", flush=True)
    s = stats(out)
    s.update(stopped=stopped, minutes=round((time.time() - t0) / 60, 1))
    return s


def stats(out: Path) -> dict:
    rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    fails = Counter()
    for r in rows:
        fails.update(r["fails"])
    secs = sorted(r["seconds"] for r in rows)
    stops = Counter(f"{r['stop_reason']}@{r['stop_kind']}" for r in rows if not r["ok"])
    return {"chats": len(rows), "whole": sum(r["ok"] for r in rows), "turns": sum(r["turns"] for r in rows),
            "first_try": sum(1 for r in rows for a in r["attempts"] if a == 1), "fails": dict(fails),
            "stops_by_reason_and_turn_kind": dict(stops),
            "median_chat_seconds": secs[len(secs) // 2] if secs else None}


def jl(path: str) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def selftest() -> None:
    import tempfile
    ok = 0
    kinds = ("smalltalk", "feelings", "advice", "followup", "ask")
    item = {"item_id": "x", "session1": [{"text": "my rabbit Pickle chewed a cable"}, {"text": "I work as a welder"},
                                         {"text": "grew up in Boise"}],
            "session2": [{"kind": k, "text": f"msg {k}"} for k in kinds]}
    fact = {"item_id": "x", "ask_index": 0, "facts": [{"value": "Pickle"}, {"value": "welder"}, {"value": "Boise"}]}
    p = teach_prompt(item, 2, ["r0", "r1"])
    assert "msg advice" in p and "msg followup" not in p and "msg ask" not in p and "You: r1" in p; ok += 1
    assert p.count("Person:") == 3 and "Pickle" in p and "{" in TAIL; ok += 1
    assert check_reply({"reply": " Pickle! "}, item, fact, 4, []) == "Pickle!"; ok += 1
    for obj, i, earlier, want in (({"reply": "Your rabbit?"}, 4, [], "ask_value_missing"),
                                  ({"reply": "Say hi to Ivo."}, 0, [], "invented_person"),
                                  ({"reply": "Is Tofu with you?"}, 0, [], "invented_pet"),
                                  ({"reply": "Tucson is nice"}, 0, [], "invented_place"),
                                  ({"reply": "Hi there"}, 1, ["hi   there"], "repeat"),
                                  ({"reply": "x" * 501}, 0, [], "too_long"),
                                  ({"reply": "Rate limit reached"}, 0, [], "scan"),
                                  ("nope", 0, [], "no_json")):
        try:
            check_reply(obj, item, fact, i, earlier)
            raise AssertionError(f"passed: {want}")
        except ValueError as e:
            assert str(e) == want, (str(e), want)
    ok += 1
    assert check_reply({"reply": "How is Pickle doing, the welder life?"}, item, fact, 1, []); ok += 1
    assert invented("pottery on Monday, then tofu with pepper", item) == [] and invented("Boise", item) == []
    assert invented("Pickle and Ivo", item) == ["person"]; ok += 1
    calls = {"n": 0}

    def fake(text):
        calls["n"] += 1
        if calls["n"] == 1:
            return "no json here"
        if calls["n"] == 2:
            raise RuntimeError("timeout")
        if "msg ask" in text.split("Today's conversation")[1]:
            return json.dumps({"reply": "Your rabbit is Pickle."})
        return json.dumps({"reply": f"reply {calls['n']}"})
    r = teach_one(item, fact, fake)
    assert r["ok"] and r["turns"] == 5 and r["attempts"][0] == 3 and r["fails"] == {"no_json": 1, "call_error": 1}
    ok += 1

    def never(_t):
        return json.dumps({"reply": "Tell Ivo hi"})
    r2 = teach_one(item, fact, never)
    assert not r2["ok"] and r2["stopped_at"] == 0 and r2["fails"] == {"invented_person": 3}
    assert r2["stop_reason"] == "invented_person" and r2["stop_kind"] == "smalltalk"; ok += 1
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "t.jsonl"
        items = [dict(item, item_id=f"c{j}") for j in range(3)]
        facts = {f"c{j}": dict(fact, item_id=f"c{j}") for j in range(3)}
        calls["n"] = 10
        s1 = write_all(items[:2], facts, out, fake, 2, 60)
        s2 = write_all(items, facts, out, fake, 2, 60)
        assert s1["chats"] == 2 and s2["chats"] == 3 and s2["whole"] == 3 and s2["turns"] == 15; ok += 1
    print(f"mu406 teach selftest {ok}/9 ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["write", "stats", "selftest"])
    ap.add_argument("--items")
    ap.add_argument("--facts")
    ap.add_argument("--out")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--max-minutes", type=float, default=60)
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "stats":
        print(json.dumps(stats(Path(a.out))))
        return
    if a.workers > 2:
        raise SystemExit("mu406: at most 2 Luna calls at a time (the Director's share)")
    facts = {f["item_id"]: f for f in jl(a.facts)}
    print(json.dumps(write_all(jl(a.items), facts, Path(a.out), luna_call, a.workers, a.max_minutes)))


if __name__ == "__main__":
    main()
