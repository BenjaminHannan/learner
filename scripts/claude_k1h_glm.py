#!/usr/bin/env python3
"""k1h teacher jobs on the Mac (Creative answers in chat thread, 2026-09-26): GLM 5.3 Flash, through Ben's opencode
route (scripts/claude_glm_opencode.py, no key handled here), writes more practice chats and one answer per chat. The
answers are the targets the LFM creative writer is trained on in k1h (scripts/claude_k1h_train.py). No Claude-written
text is a training target: the chats and the answers are GLM's. The instructions GLM gets are ours, zero-shot, with no
example chat or answer. Standard library only; Mac CPU; no model runs here.

Why (the Thread manager's 19:33 UTC question, "obvious fix first"): the textbook fix for a small model that writes
weak answers is to teach it from a stronger teacher's answers (distillation / instruction tuning). No script has
trained the creative writer so far; k1c, k1d and k1e worked on picking among its drafts instead.

chats   more practice chats with k1e's recipe and its exact words (claude_k1e_teacher.WRITE, json_list, chat_kind):
        --calls calls of 20, one subject area each from AREAS_K1H (areas the 240 k1e chats did not use), --workers at
        once. Every chat that fits the recipe and whose request is not already in --existing (or earlier in this run)
        is kept, ids kh-0001... in call order. Writes OUT/chats.jsonl and prints counts only.
          python3 -B scripts/claude_k1h_glm.py chats --existing artifacts/claude-k1e-20260926/train/items.jsonl \
              --out DIR --calls 36 --workers 4
answer  one call per chat: ANSWER, filled with the writer's own instructions (claude_cre333d_agent.SYSTEM333D), the
        user's earlier messages and the request. The raw answer is appended to OUT/answers.jsonl with its item id.
        Resumes (items already answered are skipped); --workers calls at once; stops submitting at --max-minutes or
        after 50 failed calls in this run. Prints counts only.
          python3 -B scripts/claude_k1h_glm.py answer --items A.jsonl --items B.jsonl --out DIR --workers 4 \
              --max-minutes 160
selftest (no network)

What GLM does not see: the build's short replies to the user's earlier messages (the writer sees them at run time).
This lets the Mac answers and BensPC's prompt capture run at the same time. The answers are filtered and checked later
in the thread's container (claude_k1h_train.py rows/check), not here.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_cre333d_agent as CD      # noqa: E402  (stdlib-only at import)
import claude_k1e_teacher as T         # noqa: E402  (stdlib-only)

MODEL = "opencode-go/glm-5.3-flash"
AREAS_K1H = ("birthdays and anniversaries", "weddings and big days", "clubs and volunteering", "books and films",
             "fitness and outdoor sport", "money and saving", "moving house and new places", "holidays and festivals",
             "friends and roommates", "art and photography", "nature and the weather",
             "small businesses and side projects")
MAX_FAILS = 50

ANSWER = """Write the assistant's next message in this chat.

The assistant's instructions: {system}

The chat so far (only the user's messages are shown):
{chat}

Write only the assistant's reply to the user's last message, in plain text, in under 120 words. End the reply with
a full stop, an exclamation mark or a question mark. No preface, no notes about the reply, and no quotation marks
around it. Do not use any tools or files."""


def _call(text: str) -> str:
    import claude_glm_opencode as G      # the Mac's opencode route; imported late so selftest needs no opencode
    return G.call(text, model=MODEL, timeout=300)


def answer_prompt(it: dict) -> str:
    lines = [f"User: {t.strip()}" for t in it["turns"] if isinstance(t, str) and t.strip()]
    lines.append(f"User (last message): {it['last'].strip()}")
    return ANSWER.format(system=CD.SYSTEM333D, chat="\n".join(lines))


def run_chats(a, call=None) -> dict:
    call = call or _call
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seen = {r["last"].strip().lower() for p in (a.existing or []) for r in T.load(p)}
    raw: dict = {}

    def one(c):
        try:
            return c, call(T.WRITE.replace("{area}", AREAS_K1H[c % len(AREAS_K1H)]))
        except Exception as e:                   # noqa: BLE001  (a failed call keeps nothing)
            return c, f"ERROR {type(e).__name__}"

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for fut in as_completed([ex.submit(one, c) for c in range(a.calls)]):
            c, txt = fut.result()
            raw[c] = txt
            print(f"[k1h-glm] chats call {c} done ({len(raw)}/{a.calls})", flush=True)
    items, why, failed = [], {}, 0
    for c in range(a.calls):                     # call order, so ids don't depend on which call finished first
        txt = raw.get(c, "")
        if txt.startswith("ERROR"):
            failed += 1
            continue
        for r in T.json_list(txt) or []:
            k = T.chat_kind(r)
            if k.startswith("bad"):
                why[k] = why.get(k, 0) + 1
                continue
            last = r["last"].strip().lower()
            if last in seen:
                why["repeat"] = why.get("repeat", 0) + 1
                continue
            seen.add(last)
            items.append({"item_id": f"kh-{len(items) + 1:04d}", "kind": r["kind"], "turns": r["turns"],
                          "last": r["last"], "facts": r["facts"], "numbers": None, "target": None, "gold_expr": None,
                          "area": AREAS_K1H[c % len(AREAS_K1H)]})
    (out / "chats.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items),
                                     encoding="utf-8")
    mix: dict = {}
    for x in items:
        k = T.chat_kind({kk: x[kk] for kk in ("kind", "turns", "last", "facts")})
        mix[k] = mix.get(k, 0) + 1
    res = {"chats": len(items), "mix": mix, "rejected": why, "calls": a.calls, "failed_calls": failed}
    print(json.dumps(res), flush=True)
    return res


def run_answer(a, call=None) -> dict:
    call = call or _call
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "answers.jsonl"
    done = {r["item_id"] for r in T.load(path) if r.get("answer")} if path.exists() else set()
    items = [it for p in a.items for it in T.load(p)]
    ids = [it["item_id"] for it in items]
    if len(set(ids)) != len(ids):
        raise SystemExit("k1h-glm: duplicate item ids across --items")
    todo = [it for it in items if it["item_id"] not in done]
    lock, t0 = threading.Lock(), time.time()
    stats = {"items": len(items), "already": len(done), "answered": 0, "failed": 0, "not_started": 0}
    stop = threading.Event()

    def one(it):
        if stop.is_set() or (time.time() - t0) / 60 > a.max_minutes:
            stop.set()
            return "skip"
        s = time.time()
        try:
            ans = call(answer_prompt(it))
            row = {"item_id": it["item_id"], "answer": ans, "model": MODEL, "secs": round(time.time() - s, 1)}
            key = "answered" if ans.strip() else "failed"
        except Exception as e:                   # noqa: BLE001
            row = {"item_id": it["item_id"], "answer": "", "model": MODEL, "error": f"{type(e).__name__}"}
            key = "failed"
        with lock:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            stats[key] += 1
            if stats["failed"] > MAX_FAILS:
                stop.set()
            n = stats["answered"] + stats["failed"]
            if n % 20 == 0:
                print(f"[k1h-glm] answer {n}/{len(todo)} answered {stats['answered']} failed {stats['failed']} "
                      f"{(time.time() - t0) / 60:.0f} min", flush=True)
        return key

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for fut in as_completed([ex.submit(one, it) for it in todo]):
            if fut.result() == "skip":
                stats["not_started"] += 1
    stats["minutes"] = round((time.time() - t0) / 60, 1)
    stats["stopped_early"] = stop.is_set()
    print(json.dumps(stats), flush=True)
    return stats


def selftest() -> None:
    import tempfile
    it = {"item_id": "x1", "kind": "uses_facts", "turns": ["My sister Wren loves sailing."], "last": "a card for her?",
          "facts": [{"owner": "Wren", "relation": "loves", "value": "sailing"}]}
    p = answer_prompt(it)
    assert CD.SYSTEM333D in p and "User: My sister Wren loves sailing." in p and "User (last message): a card for her?" in p
    assert p.count("User") == 2 and "{" not in p, "prompt has a stray field"
    ok = 1
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "a.jsonl"
        rows = [dict(it, item_id=f"x{i}") for i in range(5)]
        src.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        calls = []

        def fake(text):
            calls.append(text)
            if len(calls) == 2:
                raise RuntimeError("boom")
            return "Here is a card. Fair winds, Wren!"
        a = argparse.Namespace(items=[str(src)], out=d, workers=1, max_minutes=5)
        s = run_answer(a, fake)
        assert s["answered"] == 4 and s["failed"] == 1, s
        s = run_answer(a, lambda t: "Again!")          # resume: only the failed item is asked again
        assert s["already"] == 4 and s["answered"] == 1, s
        ok += 1
        good = {"kind": "idea", "turns": [], "last": "3 names for a book club?", "facts": []}
        dup = {"kind": "idea", "turns": [], "last": "Old request", "facts": []}
        bad = {"kind": "idea", "turns": ["a", "b"], "last": "x", "facts": []}
        ex = Path(d) / "ex.jsonl"
        ex.write_text(json.dumps({"last": "old request"}) + "\n", encoding="utf-8")
        a2 = argparse.Namespace(existing=[str(ex)], out=d, calls=2, workers=2)
        replies = {0: json.dumps([good, dup, bad]), 1: json.dumps([good])}
        res = run_chats(a2, lambda t: replies[0 if AREAS_K1H[0] in t else 1])
        assert res["chats"] == 1 and res["rejected"] == {"repeat": 2, "bad: kind/turn count": 1}, res
        kept = T.load(Path(d) / "chats.jsonl")
        assert kept[0]["item_id"] == "kh-0001" and kept[0]["area"] == AREAS_K1H[0]
        ok += 1
    print(f"k1h glm selftest {ok}/3 ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["chats", "answer", "selftest"])
    ap.add_argument("--existing", action="append")
    ap.add_argument("--items", action="append")
    ap.add_argument("--out")
    ap.add_argument("--calls", type=int, default=36)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-minutes", type=float, default=160)
    a = ap.parse_args()
    if a.mode == "selftest":
        return selftest()
    if a.workers > 4:
        raise SystemExit("k1h-glm: at most 4 calls at once (the opencode route is shared with lis-320)")
    return run_chats(a) if a.mode == "chats" else run_answer(a)


if __name__ == "__main__":
    main()
