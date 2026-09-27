#!/usr/bin/env python3
"""mu-407 prep: fresh GLM-worded two-session DEV chats and GLM-worded input frames ("Making things up about you",
2026-09-27). New file; standard library only (it runs on the Mac through Ben's opencode route, reasoning effort low).
Plan and marks: artifacts/claude-mu407-20260927/PASSMARKS.md.

Code picks every fact (claude_mu405_facts.slots, seed 4070); GLM only words the user's messages around them. GLM also
words the four input pieces the talker sees (system line, memory header, per-line prefix, current-message label); the
prompt describes each piece's job and gives none of its words. Claude writes no chat text and no frame text.

  facts   --out F                                  75 panel candidates + 3 smoke, code-chosen facts
  frames  --out FRAMES.json [--attempts 3]         one GLM call per attempt; first answer that passes the checks
  write   --facts F --out RAW.jsonl [--workers 3] [--attempts 3] [--max-minutes 60]
  select  --facts F --raw RAW.jsonl --out-panel P --out-facts F2   first 60 passing panel candidates in id order + smoke
  selftest                                         (no network)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_mu405_facts as F  # noqa: E402

SEED = 4070
N_CAND, N_PANEL, N_SMOKE, PER_CONV = 75, 60, 3, 3
KINDS2 = ("smalltalk", "feelings", "advice", "followup", "ask")
ATTEMPTS = 3
MAX_TURN = 400
FRAME_LIMITS = {"system": 700, "memory_header": 120, "line_prefix": 30, "current_label": 40}

KIND_TEXT = {
    "smalltalk": "a short greeting or small talk, as when coming back to the app",
    "feelings": "the user shares how they feel about something going on in their life",
    "advice": "the user asks for advice about something in their life",
    "followup": "a follow-up to the advice they asked for",
    "ask": "the user asks the assistant to remind them of this: {ask}",
}


def make_facts() -> list[dict]:
    rng = random.Random(SEED)
    ids = [f"mu407-{i:02d}" for i in range(1, N_CAND + 1)] + [f"mu407-s{i}" for i in range(1, N_SMOKE + 1)]
    rows = []
    for iid in ids:
        cand = F.slots(rng)
        keys = rng.sample(sorted(cand), PER_CONV)
        rows.append({"item_id": iid, "smoke": iid.startswith("mu407-s"), "facts": [cand[k] for k in keys],
                     "ask_index": rng.randrange(PER_CONV)})
    return rows


def chat_prompt(row: dict) -> str:
    facts = row["facts"]
    ask = facts[row["ask_index"]]["ask"]
    lines = "\n".join(f"- {f['detail']} (write the value exactly as: {f['value']})" for f in facts)
    kinds = "\n".join(f"{i}. {k}: {KIND_TEXT[k].format(ask=ask)}" for i, k in enumerate(KINDS2, 1))
    return ("Write only the USER's messages for two chats between one user and a personal assistant app. The chats "
            "are a few days apart. Write the way people text: casual, short, varied, first person.\n\n"
            "Facts about the user:\n" + lines + "\n\n"
            "Chat 1: 3 or 4 user messages. Together they must state all three facts, each value written exactly as "
            "given.\n"
            "Chat 2 (a few days later): exactly 5 user messages, in this order:\n" + kinds + "\n"
            "Messages 2 to 4 of chat 2 are about the same parts of the user's life as the facts. No message in chat "
            "2 may contain any of the three values.\n"
            "Any other person, pet or place you mention must have an invented name. No real people or brands.\n\n"
            'Answer with exactly one line of JSON and nothing else: {"chat1": ["...", ...], "chat2": {"smalltalk": '
            '"...", "feelings": "...", "advice": "...", "followup": "...", "ask": "..."}}')


FRAMES_PROMPT = (
    "You are writing four pieces of text that a program puts around the messages a small chat model sees. The model "
    "is a friendly personal assistant for one user. Write every piece in plain English, in your own words.\n\n"
    '1. "system": the system message. It must tell the assistant all of these: it is chatting with one user; the '
    "user tells it about their life and the people in it; it may also be shown what this user said in earlier "
    "conversations; it answers questions only from what the user has told it, in this conversation or in those "
    "earlier ones; when the user corrects something, the newer information replaces the older; when the user never "
    "said something, it says it does not know and does not guess; for small talk it just chats naturally; when "
    "asked for ideas or a bit of writing it helps, using what it knows about the user; it keeps replies short.\n"
    '2. "memory_header": a one-line heading placed above a list of messages this user sent in earlier '
    "conversations, oldest first.\n"
    '3. "line_prefix": a few words placed before each of those earlier messages. Each message follows the prefix in '
    "double quotes. The prefix says that the user said it.\n"
    '4. "current_label": a short label on its own line, right before the user\'s message that the assistant must '
    "reply to now, marking it clearly apart from the earlier conversations.\n\n"
    'Answer with exactly one line of JSON and nothing else: {"system": "...", "memory_header": "...", '
    '"line_prefix": "...", "current_label": "..."}')


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


def check_chat(obj, row: dict):
    """Returns (session1, session2) or raises ValueError naming the first failed check."""
    if not isinstance(obj, dict) or not isinstance(obj.get("chat1"), list) or not isinstance(obj.get("chat2"), dict):
        raise ValueError("shape")
    s1 = [str(t).strip() for t in obj["chat1"]]
    if not 3 <= len(s1) <= 4 or any(not t or len(t) > MAX_TURN for t in s1):
        raise ValueError("chat1_turns")
    if any(k not in obj["chat2"] for k in KINDS2):
        raise ValueError("chat2_kinds")
    s2 = [{"kind": k, "text": str(obj["chat2"][k]).strip()} for k in KINDS2]
    if any(not t["text"] or len(t["text"]) > MAX_TURN for t in s2):
        raise ValueError("chat2_turns")
    vals = [f["value"].lower() for f in row["facts"]]
    joined1 = " ".join(s1).lower()
    if any(v not in joined1 for v in vals):
        raise ValueError("value_missing_in_chat1")
    if any(v in t["text"].lower() for t in s2 for v in vals):
        raise ValueError("value_in_chat2")
    return [{"text": t} for t in s1], s2


def check_frames(obj) -> dict:
    if not isinstance(obj, dict):
        raise ValueError("shape")
    out = {}
    for k, lim in FRAME_LIMITS.items():
        v = str(obj.get(k, "")).strip()
        if not v or len(v) > lim or (k != "system" and "\n" in v):
            raise ValueError(f"frame_{k}")
        out[k] = v
    return out


def call_low(text: str) -> str:
    import claude_lis320_glm_oclow as OL
    return OL.call_low(text, model="opencode-go/glm-5.3-flash") or ""


def write_one(row: dict, caller) -> dict:
    t0, err = time.time(), ""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            s1, s2 = check_chat(last_json(caller(chat_prompt(row))), row)
            return {"item_id": row["item_id"], "ok": True, "attempts": attempt, "session1": s1, "session2": s2,
                    "seconds": round(time.time() - t0, 1)}
        except Exception as e:  # noqa: BLE001  (a failed call or a failed check is the same: try again)
            err = (str(e) or type(e).__name__)[:200]
    return {"item_id": row["item_id"], "ok": False, "attempts": ATTEMPTS, "error": err,
            "seconds": round(time.time() - t0, 1)}


def write_all(rows: list[dict], out: Path, caller, workers: int, max_minutes: float) -> dict:
    done = set()
    if out.exists():
        done = {r["item_id"] for r in map(json.loads, out.read_text(encoding="utf-8").splitlines())}
    todo = [r for r in rows if r["item_id"] not in done]
    t0, stopped, n = time.time(), "done", 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i in range(0, len(todo), 12):
            if (time.time() - t0) / 60 > max_minutes:
                stopped = "time"
                break
            res = list(ex.map(lambda r: write_one(r, caller), todo[i:i + 12]))
            with out.open("a", encoding="utf-8") as fh:
                for r in res:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += len(res)
            print(f"[mu407w] {n}/{len(todo)} written, {sum(r['ok'] for r in res)} ok in this batch", flush=True)
    allr = list(map(json.loads, out.read_text(encoding="utf-8").splitlines()))
    errs: dict = {}
    for r in allr:
        if not r["ok"]:
            errs[r["error"][:40]] = errs.get(r["error"][:40], 0) + 1
    return {"rows": len(allr), "ok": sum(r["ok"] for r in allr), "errors": errs, "stopped": stopped,
            "minutes": round((time.time() - t0) / 60, 1)}


def select(facts: list[dict], raw: list[dict]) -> tuple[list[dict], list[dict]]:
    ok = {r["item_id"]: r for r in raw if r["ok"]}
    panel_ids = [f["item_id"] for f in facts if not f["smoke"] and f["item_id"] in ok][:N_PANEL]
    smoke_ids = [f["item_id"] for f in facts if f["smoke"] and f["item_id"] in ok]
    keep = set(panel_ids) | set(smoke_ids)
    items = [{"item_id": i, "session1": ok[i]["session1"], "session2": ok[i]["session2"]}
             for i in panel_ids + smoke_ids]
    return items, [f for f in facts if f["item_id"] in keep]


def selftest() -> None:
    ok = 0
    fx = make_facts()
    assert len(fx) == 78 and sum(f["smoke"] for f in fx) == 3 and fx == make_facts(); ok += 1
    row = fx[0]
    vals = [f["value"] for f in row["facts"]]
    good = {"chat1": [f"so about {vals[0]} lol", f"also {vals[1]}", f"and {vals[2]} too"],
            "chat2": {k: f"hey {k}" for k in KINDS2}}
    s1, s2 = check_chat(last_json("sure:\n" + json.dumps(good) + "\n"), row)
    assert len(s1) == 3 and [t["kind"] for t in s2] == list(KINDS2); ok += 1
    bad = json.loads(json.dumps(good))
    bad["chat2"]["advice"] = f"what about {vals[0]}"
    try:
        check_chat(bad, row)
        raise AssertionError("value in chat2 passed")
    except ValueError as e:
        assert str(e) == "value_in_chat2"; ok += 1
    p = chat_prompt(row)
    assert all(v in p for v in vals) and row["facts"][row["ask_index"]]["ask"] in p; ok += 1
    fr = check_frames({"system": "You are kind.", "memory_header": "Earlier:", "line_prefix": "They said",
                       "current_label": "Now:"})
    assert fr["current_label"] == "Now:"; ok += 1
    calls = {"n": 0}

    def flaky(t):
        calls["n"] += 1
        return "no json" if calls["n"] == 1 else json.dumps(good)
    r = write_one(row, flaky)
    assert r["ok"] and r["attempts"] == 2; ok += 1
    raw = [{"item_id": f["item_id"], "ok": f["item_id"] != "mu407-02", "session1": [], "session2": []} for f in fx]
    items, fx2 = select(fx, raw)
    assert len(items) == 63 and "mu407-02" not in {i["item_id"] for i in items} and len(fx2) == 63; ok += 1
    assert "mu407-61" in {i["item_id"] for i in items} and "mu407-62" not in {i["item_id"] for i in items}; ok += 1
    print(f"mu407 prep selftest {ok}/8 ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["facts", "frames", "write", "select", "selftest"])
    ap.add_argument("--out")
    ap.add_argument("--facts")
    ap.add_argument("--raw")
    ap.add_argument("--out-panel")
    ap.add_argument("--out-facts")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--max-minutes", type=float, default=60)
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "facts":
        rows = make_facts()
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(json.dumps({"rows": len(rows), "smoke": sum(r["smoke"] for r in rows)}))
    elif a.cmd == "frames":
        err = ""
        for attempt in range(1, ATTEMPTS + 1):
            try:
                fr = check_frames(last_json(call_low(FRAMES_PROMPT)))
                Path(a.out).write_text(json.dumps(fr, ensure_ascii=False, indent=1), encoding="utf-8")
                print(json.dumps({"ok": True, "attempts": attempt, "chars": {k: len(v) for k, v in fr.items()}}))
                return
            except Exception as e:  # noqa: BLE001
                err = (str(e) or type(e).__name__)[:200]
        print(json.dumps({"ok": False, "attempts": ATTEMPTS, "error": err}))
        raise SystemExit(1)
    elif a.cmd == "write":
        rows = list(map(json.loads, Path(a.facts).read_text(encoding="utf-8").splitlines()))
        print(json.dumps(write_all(rows, Path(a.out), call_low, a.workers, a.max_minutes)))
    elif a.cmd == "select":
        fx = list(map(json.loads, Path(a.facts).read_text(encoding="utf-8").splitlines()))
        raw = list(map(json.loads, Path(a.raw).read_text(encoding="utf-8").splitlines()))
        items, fx2 = select(fx, raw)
        for p, rows in ((a.out_panel, items), (a.out_facts, fx2)):
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            Path(p).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(json.dumps({"panel": sum(1 for f in fx2 if not f["smoke"]), "smoke": sum(1 for f in fx2 if f["smoke"])}))


if __name__ == "__main__":
    main()
