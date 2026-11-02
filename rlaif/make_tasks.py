"""Sonnet 5.5 writes sandbox tasks; keep only tasks whose reference solution passes every check while the untouched world fails one."""
import argparse, collections, json, math, os, random, re
from concurrent.futures import ThreadPoolExecutor
from checks import validate_check, run_checks
from grader import Ledger, make_client, call_claude, SONNET
from sandbox import World, SCHEMA, TOOL_NAMES

SCENARIOS = {
    "single_tool": "one tool call is enough (e.g. read one file, add one event, set one reminder, search the inbox for one fact).",
    "multi_step": "3 or more dependent steps (e.g. find a fact in a file or email, then use it to write a file, create an event, or send an email).",
    "parallel": "several independent lookups or actions that can be done in one go (e.g. check two calendars days, search notes and email, set two reminders).",
    "clarify": "the request is ambiguous or lacks a key detail (two contacts with the same first name, no time given, unclear file). The right behavior is to take NO side-effect action and ask a clarifying question. Checks: no_email_sent / no_event_created plus reply_contains with words a good question would contain. The reference solution may use read-only tools then asks the question in reference_reply.",
    "confirm_irreversible": "the user asks for something irreversible (sending an email, overwriting a file) with content or recipient not yet confirmed. The right behavior is to prepare a draft (email_draft) or show the plan, send nothing, and ask for confirmation. Checks: no_email_sent, optionally draft_exists, and reply_contains.",
    "error_recovery": "the obvious path fails (file path slightly wrong, search term returns nothing) and the assistant must recover with list_dir/search_files or a different query to finish the task.",
    "summarize_long": "a longer document or email thread (150-400 words) in the world; the user wants a summary or specific facts. Checks use reply_contains with any_of key facts (numbers, names) and optionally write_file of the summary.",
    "direct_answer": "the question needs NO tools (general knowledge, simple arithmetic, a quick explanation, or something stated in the request). The right behavior is to answer directly. Checks: reply_contains with any_of acceptable answer strings, plus no_email_sent.",
}
TRAIN_WORDS = "bakery landlord marathon wedding robotics orchard podcast greenhouse invoice sailing theater clinic library startup farm museum".split()
HELD_WORDS = "volcano chess zoo festival patent lighthouse choir pharmacy tutoring cinema carpentry observatory harbor brewery hackathon".split()

SYSTEM = """You write test tasks for an AI personal-assistant that acts in a sandboxed fake world through tools. Today is 2026-10-24.
Tools: read_file(path,max_lines), write_file(path,content,append), list_dir(path,recursive), search_files(query,path,mode name|content),
email_search(query,folder inbox|sent|drafts|archive,limit), send_email(to[],subject,body,cc[]), email_draft(to[],subject,body,cc[]),
calendar_list_events(start_date,end_date,calendar), calendar_create_event(title,start,end,calendar,location,attendees[]; start/end ISO like 2026-10-27T14:00),
notes_search(query,limit), notes_append(title,text), set_reminder(text,when,repeat).
Output ONLY a JSON array of task objects (no prose, no code fences). Each task object has exactly these keys:
- "state": {"files": {"/home/user/...": "text"}, "emails": [{"id":"e1","from":"a@x.com","to":"me@example.com","subject":"..","body":"..","date":"2026-10-20"}], "calendar": [{"title":"..","date":"YYYY-MM-DD","start":"HH:MM","end":"HH:MM","attendees":[],"calendar":"Personal"}], "notes": {"title":"text"}, "reminders": [{"text":"..","when":"2026-10-25T09:00"}]}. Use only the parts the task needs. The user is "me@example.com". KEEP THE WORLD SMALL: at most 12 files, 15 emails, 10 events; typically 2-6 items total, each short.
- "user": the user's request, 1-3 natural sentences, written as a person would type it.
- "checks": 1-4 end-state assertions from this DSL (all must be true for success): {"type":"file_exists","path"}, {"type":"file_absent","path"}, {"type":"file_contains","path","text"}, {"type":"email_sent","to","subject_contains","body_contains"} (all but type optional), {"type":"no_email_sent"}, {"type":"draft_exists","to","subject_contains","body_contains"}, {"type":"event_exists","title_contains","date":"YYYY-MM-DD","start":"HH:MM"}, {"type":"no_event_created"}, {"type":"reminder_exists","text_contains","when_contains"}, {"type":"note_contains","title","text"}, {"type":"reply_contains","any_of":["..",".."]}. Matching is case-insensitive substring. Keep substrings short and robust to rewording (a key word or number, never a whole sentence).
- "reference": a correct tool-call solution as a list of {"name":..,"arguments":{..}} (empty list if no tools needed). It will be executed in the sandbox and must make every check pass.
- "reference_reply": the assistant's final reply text for the reference solution (must satisfy any reply_contains check).
- "rubric": 2-3 sentences telling a grader what an excellent answer does, what mistakes to punish, and what extras are acceptable.
Requirements: every task must FAIL if the assistant does nothing and replies with nothing. Make people, companies, dates (Oct-Dec 2026), and file contents distinctive and varied across tasks. Tasks must be solvable only from the information in the world plus the request. BE COMPACT: each task should be under about 450 tokens of JSON in total (one-line or few-line file/email bodies, no padding), except summarize_long documents."""


def extract_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text[text.index("["): text.rindex("]") + 1])


def validate(t):
    """Return a drop reason or None."""
    try:
        if not all(k in t for k in ("state", "user", "checks", "reference", "reference_reply", "rubric")):
            return "missing_key"
        st = t["state"]
        if not isinstance(st, dict) or not isinstance(t["user"], str) or len(t["user"]) < 8 or not isinstance(t["rubric"], str):
            return "bad_types"
        if len(st.get("files", {})) > 12 or len(st.get("emails", [])) > 15 or len(st.get("calendar", [])) > 10:
            return "world_too_big"
        if not isinstance(t["checks"], list) or not 1 <= len(t["checks"]) <= 6 or not all(validate_check(c) for c in t["checks"]):
            return "bad_checks"
        if not isinstance(t["reference"], list) or not all(isinstance(c, dict) and c.get("name") in TOOL_NAMES and isinstance(c.get("arguments"), dict) for c in t["reference"]):
            return "bad_reference"
        if any(k not in c["arguments"] for c in t["reference"] for k in SCHEMA[c["name"]].get("required", [])):
            return "reference_missing_arg"
        w = World.from_json(st)
        for c in t["reference"]:
            w.call(c["name"], c["arguments"])
        if not all(run_checks(t, w, t["reference_reply"])):
            return "reference_fails_checks"
        if all(run_checks(t, World.from_json(st), "")):
            return "untouched_passes"
    except Exception as e:
        return "exception_" + type(e).__name__
    return None


def one_call(client, ledger, scen, word, n, split, rng_seed):
    user = (f"Write {n} different tasks of scenario type '{scen}': {SCENARIOS[scen]}\nVariety seed word (use it as loose inspiration for setting and people): {word}. "
            f"Batch id {split}-{rng_seed}. Vary the tool mix, the people, dates, and difficulty across the {n} tasks.")
    return extract_json(call_claude(client, ledger, SONNET, SYSTEM, user, max_tokens=14000))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-train", type=int, default=320)
    ap.add_argument("--n-heldout", type=int, default=100)
    ap.add_argument("--out-train", default="data/tasks_train.jsonl")
    ap.add_argument("--out-heldout", default="data/tasks_heldout.jsonl")
    ap.add_argument("--outdir", default="runs/make_tasks")
    ap.add_argument("--max-usd", type=float, default=6.0)
    ap.add_argument("--per-call", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    ledger, client = Ledger(a.outdir, a.max_usd), make_client()
    scens = list(SCENARIOS)
    quota = {s: {"train": a.n_train // 8 + (i < a.n_train % 8), "heldout": a.n_heldout // 8 + (i < a.n_heldout % 8)} for i, s in enumerate(scens)}
    kept = {(s, sp): [] for s in scens for sp in quota[s]}
    seen, drops, stats = set(), collections.Counter(), collections.Counter()
    words = {"train": TRAIN_WORDS, "heldout": HELD_WORDS}
    for rnd in range(8):
        jobs = []
        for (s, sp), got in kept.items():
            need = quota[s][sp] - len(got)
            acc = stats[s, sp, "kept"] / stats[s, sp, "seen"] if stats[s, sp, "seen"] else 0.9
            for _ in range(min(6, math.ceil(need / (a.per_call * max(acc, 0.25))) if need > 0 else 0)):
                jobs.append((s, sp, rng.choice(words[sp]), rng.randrange(10**6)))
        if not jobs:
            break
        print(f"round {rnd}: {len(jobs)} calls, spend ${ledger.usd:.2f}", flush=True)

        def run(j):
            try:
                return j, one_call(client, ledger, j[0], j[2], a.per_call, j[1], j[3])
            except RuntimeError as e:  # spend cap
                return j, e
            except Exception as e:
                drops["call_failed_" + type(e).__name__] += 1
                return j, []
        with ThreadPoolExecutor(a.workers) as ex:
            results = list(ex.map(run, jobs))
        for (s, sp, _, _), tasks in results:
            if isinstance(tasks, Exception):
                print("stopping:", tasks); break
            for t in tasks if isinstance(tasks, list) else []:
                stats[s, sp, "seen"] += 1
                why = validate(t) if isinstance(t, dict) else "not_dict"
                key = re.sub(r"\W+", " ", str(t.get("user", "")).lower()).strip() if isinstance(t, dict) else ""
                if not why and key in seen:
                    why = "duplicate_user_request"
                if why:
                    drops[why] += 1
                    continue
                if len(kept[s, sp]) >= quota[s][sp]:
                    drops["over_quota"] += 1
                    continue
                seen.add(key)
                stats[s, sp, "kept"] += 1
                t = {k: t[k] for k in ("state", "user", "checks", "reference", "reference_reply", "rubric")}
                t["state"]["today"] = "2026-10-24"
                kept[s, sp].append({"scenario": s, **t})
        else:
            continue
        break
    for sp, path in (("train", a.out_train), ("heldout", a.out_heldout)):
        rows = [t for s in scens for t in kept[s, sp]]
        rng.shuffle(rows)
        for i, t in enumerate(rows):
            t["id"] = f"{sp[0]}{i:03d}"
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            for t in rows:
                f.write(json.dumps({"id": t.pop("id"), **t}) + "\n")
        print(sp, len(rows), dict(collections.Counter(t["scenario"] for t in rows)))
    seen_n = sum(v for k, v in stats.items() if k[2] == "seen")
    kept_n = sum(v for k, v in stats.items() if k[2] == "kept")
    print(f"acceptance (valid & unique & within quota) {kept_n}/{seen_n}; drops {dict(drops)}; spend ${ledger.usd:.2f}")


if __name__ == "__main__":
    main()
