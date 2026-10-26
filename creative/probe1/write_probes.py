"""Probe writer (PREREG.md): the model sees only today's date, the user's request, the tool list and the check language, and writes 2-6 end-state checks.
K2:    write_probes.py --base-url http://127.0.0.1:8090/v1 --model k2 [--out probes_k2.jsonl]     (4 samples/task, T0.7, resumable)
Haiku: write_probes.py --haiku [--phase submit|poll|collect|all] [--dry-run]                      (Batches API, state file, key: env LEARNER_ANTHROPIC_API_KEY)"""
import argparse, asyncio, json, os, re, sys, time, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_common import *  # noqa

# type -> (meaning, example). Keys come from CHECK_KEYS (tests keep this table in step with it and with validate_check).
LANG = {
    "file_exists": ("a file exists at path", {"path": "/home/user/notes/plan.txt"}),
    "file_absent": ("no file exists at path", {"path": "/home/user/old/draft.txt"}),
    "file_contains": ("the file at path exists and its text contains text (path and text are both required)",
                      {"path": "/home/user/notes/plan.txt", "text": "budget"}),
    "email_sent": ("an email was actually sent (a saved draft does not count) whose recipients (to or cc) contain to, whose subject contains subject_contains and whose body contains body_contains",
                   {"to": "sam@example.com", "body_contains": "Friday"}),
    "no_email_sent": ("no email at all was sent", {}),
    "draft_exists": ("an email draft was saved with the same matching rules as email_sent", {"to": "sam@example.com", "subject_contains": "invoice"}),
    "event_exists": ("a calendar event that the assistant created (events already on the calendar do not count) whose title contains title_contains, whose date is exactly date (YYYY-MM-DD) and whose start time is exactly start (HH:MM, 24-hour)",
                     {"title_contains": "dentist", "date": "2026-11-03", "start": "09:30"}),
    "no_event_created": ("the assistant created no calendar event", {}),
    "reminder_exists": ("a reminder exists whose text contains text_contains and whose time description contains when_contains", {"text_contains": "passport", "when_contains": "2026-11-01"}),
    "note_contains": ("a note exists whose title contains title (optional) and whose text contains text (required)", {"title": "Groceries", "text": "milk"}),
    "reply_contains": ("the assistant's final reply to the user contains at least one of the strings in any_of (a non-empty list)", {"any_of": ["42", "forty-two"]}),
}
LANG_RULES = ("Rules: every value is a string (any_of is a list of strings). Each key you give narrows the match, a key you leave out is not checked, and "
              "email_sent, draft_exists, event_exists and reminder_exists need at least one key. All text matching is case-insensitive substring matching, "
              "so use short, distinctive pieces (a name, number, address or key word), not whole sentences. Paths are absolute; ~ means /home/user. "
              "The checks run once, on the state after the assistant has finished.")


def tool_list():
    out = []
    for t in TOOLS:
        f = t["function"]
        req, props = set(f["parameters"].get("required", [])), f["parameters"]["properties"]
        sig = ", ".join(f"{k}{'' if k in req else '?'}: {v.get('type', 'any')}" for k, v in props.items())
        out.append(f"- {f['name']}({sig}): {f['description']}")
    return "\n".join(out)


def check_language():
    L = []
    for t, (meaning, ex) in LANG.items():
        keys = ", ".join(sorted(CHECK_KEYS[t])) or "no keys"
        L.append(f"- {t} (keys: {keys}): {meaning}. Example: {json.dumps(dict(type=t, **ex))}")
    return "\n".join(L) + "\n" + LANG_RULES


def build_prompt(today, user):
    """The whole prompt. Takes only the date and the request: no reference, rubric, checks or tries can get in."""
    return (f"Today is {today}.\n\n"
            "A personal assistant has tools for the user's files, email, calendar, notes and reminders. The user sent it this request:\n\n"
            f"\"\"\"\n{user}\n\"\"\"\n\n"
            f"The assistant's tools:\n{tool_list()}\n\n"
            "When the assistant has finished, a program will inspect the final state (files, sent mail, drafts, new calendar events, notes, reminders) and the assistant's final reply. "
            "Write 2 to 6 checks that would all be true if and only if the job was done right. Check what the right end state must contain, and also what must not have happened "
            "(for example an email nobody asked for). Each check is a JSON object with a \"type\" and keys from this list:\n\n"
            f"{check_language()}\n\n"
            "Reply with only JSON, no other text, in the form {\"checks\": [ {...}, {...} ]}.")


def task_prompt(task):
    return build_prompt(task["state"].get("today", "2026-10-24"), task["user"])


def extract_checks(text):
    """Pull the checks list out of a reply. None = nothing usable found; otherwise a list (items may still be invalid).
    Handles <think> blocks, code fences, prose around the JSON, a bare list, and truncated JSON (complete inner objects are kept)."""
    text = (text or "").split("</think>")[-1]
    texts, found = (text, re.sub(r",\s*([}\]])", r"\1", text)), []
    for t in texts:
        vals, i, dec = [], 0, json.JSONDecoder()
        while i < len(t):
            if t[i] in "{[":
                try:
                    v, j = dec.raw_decode(t, i)
                    vals.append(v)
                    i = j
                    continue
                except json.JSONDecodeError:
                    pass
            i += 1
        for v in vals:
            if isinstance(v, dict) and isinstance(v.get("checks"), list):
                return v["checks"]
        for v in vals:
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                return v
        found = found or [v for v in vals if isinstance(v, dict) and "type" in v]
    return found or None


def job_seed(tid, s):
    return zlib.crc32(f"probe1|{tid}|{s}".encode()) % 2**31


def select_tasks(results, only=None):
    byid = {t["id"]: t for t in load_tasks()}
    return [byid[i] for i in (only or target_ids(results))]


def record(source, tid, s, raw):
    ch = extract_checks(raw)
    return dict(key=f"{tid}|{s}", task=tid, sample=s, source=source, parse_ok=ch is not None, checks=ch, raw=raw)


async def k2_main(a, tasks):
    import httpx
    from_k2 = load_pick1("judge_k2")
    done = {r["key"] for r in read_jsonl(a.out)}
    todo = [(t, s) for t in tasks for s in range(N_SAMPLES) if f"{t['id']}|{s}" not in done]
    print(f"{len(tasks) * N_SAMPLES} samples, {len(done)} done, {len(todo)} to write", flush=True)
    sem, fh, n = asyncio.Semaphore(a.concurrency), open(a.out, "a"), [0]

    async def one(cl, t, s):
        body = dict(model=a.model, messages=[dict(role="user", content=task_prompt(t))], max_tokens=a.max_tokens,
                    temperature=TEMPERATURE, top_p=TOP_P, seed=job_seed(t["id"], s))
        async with sem:
            for attempt in range(5):
                try:
                    resp = await cl.post(f"{a.base_url}/chat/completions", json=body)
                    resp.raise_for_status()
                    raw = from_k2.reply_text(resp.json()["choices"][0])
                    break
                except Exception as e:  # noqa
                    if attempt == 4:
                        print(f"FAILED {t['id']}|{s}: {e}", flush=True)
                        return
                    await asyncio.sleep(2 ** attempt)
        fh.write(json.dumps(record("k2", t["id"], s, raw), ensure_ascii=False) + "\n"); fh.flush()
        n[0] += 1

    async with httpx.AsyncClient(timeout=600) as cl:
        await asyncio.gather(*(one(cl, t, s) for t, s in todo))
    print(f"wrote {n[0]} ({len(todo) - n[0]} failed; rerun to resume)")


def haiku_main(a, tasks):
    jh = load_pick1("judge_haiku")
    reqs = [(f"{t['id']}|{s}", task_prompt(t)) for t in tasks for s in range(N_SAMPLES)]
    tin = sum(len(p) for _, p in reqs) / 3.5
    print(f"{len(reqs)} requests in 1 batch; model {jh.MODEL}; ~{tin / 1e6:.3f}M input tokens; est. cost ${tin / 1e6 * jh.PRICE_IN + len(reqs) * 400 / 1e6 * jh.PRICE_OUT:.3f}")
    if a.dry_run:
        return
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    client = anthropic.Anthropic(api_key=os.environ["LEARNER_ANTHROPIC_API_KEY"])
    state = json.load(open(a.state)) if os.path.exists(a.state) else {"batches": [], "keys": []}
    if a.phase in ("submit", "all") and not state["batches"]:   # submit once; a rerun only polls / collects
        batch = client.messages.batches.create(requests=[Request(custom_id=f"r{i}", params=MessageCreateParamsNonStreaming(
            model=jh.MODEL, max_tokens=a.max_tokens, temperature=TEMPERATURE, thinking={"type": "disabled"},
            messages=[{"role": "user", "content": p}])) for i, (_, p) in enumerate(reqs)])
        state = {"batches": [batch.id], "keys": [k for k, _ in reqs]}
        json.dump(state, open(a.state, "w"))
        print("submitted", state["batches"], flush=True)
    if a.phase == "submit":
        return
    if not state["batches"]:
        sys.exit("nothing submitted yet (state file empty); run --phase submit")
    for bid in state["batches"]:
        while client.messages.batches.retrieve(bid).processing_status != "ended":
            if a.phase == "collect":
                sys.exit(f"batch {bid} has not ended; run --phase poll")
            print(time.strftime("%H:%M:%S"), bid, "processing", flush=True)
            if a.phase == "poll" and a.once:
                return
            time.sleep(60)
    if a.phase == "poll":
        print("ended")
        return
    out = {}
    for bid in state["batches"]:
        for res in client.messages.batches.results(bid):
            k = state["keys"][int(res.custom_id[1:])]
            txt = ""
            if res.result.type == "succeeded":
                txt = next((c.text for c in res.result.message.content if c.type == "text"), "")
            tid, s = k.rsplit("|", 1)
            out[k] = record("haiku", tid, int(s), txt) | dict(batch_result=res.result.type)
    with open(a.out, "w") as f:
        for k in state["keys"]:
            if k in out:
                f.write(json.dumps(out[k], ensure_ascii=False) + "\n")
    print(f"wrote {len(out)} samples ({sum(not r['parse_ok'] for r in out.values())} unparsable) -> {a.out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=DEFAULT_RESULTS, help="Guess-1 run dir; its target.json names the 48 tasks")
    ap.add_argument("--tasks", default="", help="comma-separated task ids instead of target.json (smoke tests)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--base-url", default="http://127.0.0.1:8090/v1")
    ap.add_argument("--model", default="k2")
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--haiku", action="store_true", help="write the probes with Claude Haiku through the Batches API instead")
    ap.add_argument("--phase", choices=["submit", "poll", "collect", "all"], default="all")
    ap.add_argument("--once", action="store_true", help="with --phase poll: check once and return")
    ap.add_argument("--state", default=os.path.join(HERE, "haiku_probes_state.json"))
    ap.add_argument("--dry-run", action="store_true", help="--haiku: print the request count and cost estimate only")
    ap.add_argument("--print-prompt", metavar="TASK", help="print the prompt for one task and exit")
    a = ap.parse_args()
    a.max_tokens = a.max_tokens or (1024 if a.haiku else 768)
    a.out = a.out or os.path.join(HERE, "probes_haiku.jsonl" if a.haiku else "probes_k2.jsonl")
    tasks = select_tasks(a.results, [x for x in a.tasks.split(",") if x] or None)
    if a.print_prompt:
        print(task_prompt(next(t for t in load_tasks() if t["id"] == a.print_prompt)))
    elif a.haiku:
        haiku_main(a, tasks)
    else:
        asyncio.run(k2_main(a, tasks))


if __name__ == "__main__":
    main()
