"""Reach-1 runner. Resumable: results.jsonl is append-only, (task_id, arm, try_idx) already present is skipped."""
import argparse, asyncio, datetime, json, os, re, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
from episode import run_episode  # noqa: E402  (also puts rlaif_copy on sys.path)
from client import Client  # noqa: E402

SCREEN_TRIES, TOTAL_PLAIN, MIN_HARD = 8, 64, 15
N_RPLUS, N_FLIP, N_BORROW, N_REPLAY, MAX_FLIP = 16, 8, 8, 3, 8
PAUSE_FILE, DEADLINE = None, None  # set from the CLI: wait while PAUSE_FILE exists; launch nothing after DEADLINE (epoch s)
RPLUS_TEXT = "These attempts did not complete the job; try a different approach."
BORROW_LABEL = "A job you solved before that may have a similar shape:"


def load_tasks():
    d = os.path.join(HERE, "rlaif_copy", "data")
    return [json.loads(l) for f in ("tasks_train.jsonl", "tasks_heldout.jsonl") for l in open(os.path.join(d, f)) if l.strip()]


# ---------- storage ----------
class Store:
    def __init__(self, out):
        os.makedirs(out, exist_ok=True)
        self.out, self.path = out, os.path.join(out, "results.jsonl")
        self.rows = [json.loads(l) for l in open(self.path) if l.strip()] if os.path.exists(self.path) else []
        self.done = {(r["task_id"], r["arm"], r["try_idx"]) for r in self.rows}
        self.lock = asyncio.Lock()

    async def add(self, rec):
        async with self.lock:
            with open(self.path, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.rows.append(rec)
            self.done.add((rec["task_id"], rec["arm"], rec["try_idx"]))

    def arm(self, arm):
        return [r for r in self.rows if r["arm"] == arm]

    def jpath(self, name):
        return os.path.join(self.out, name)

    def jload(self, name, default=None):
        p = self.jpath(name)
        return json.load(open(p)) if os.path.exists(p) else default

    def jsave(self, name, obj):
        json.dump(obj, open(self.jpath(name), "w"), indent=1, ensure_ascii=False)


async def run_jobs(client, store, jobs, conc=8):
    """jobs: dicts(task, arm, try_idx, extra_block=None, meta={}). Skips ones already done."""
    todo = [j for j in jobs if (j["task"]["id"], j["arm"], j["try_idx"]) not in store.done]
    sem, n = asyncio.Semaphore(conc), [0]

    async def one(j):
        async with sem:
            while PAUSE_FILE and os.path.exists(PAUSE_FILE):
                if not getattr(run_jobs, "said", False):
                    print(f"paused: {PAUSE_FILE} exists", flush=True)
                    run_jobs.said = True
                await asyncio.sleep(30)
            run_jobs.said = False
            if DEADLINE and time.time() > DEADLINE:
                return
            try:
                rec = await run_episode(client, j["task"], j["arm"], j["try_idx"], j.get("extra_block"))
            except Exception as e:  # leave it undone so a rerun retries it
                print(f"! {j['task']['id']} {j['arm']} {j['try_idx']}: {type(e).__name__}: {e}", file=sys.stderr)
                return
            await store.add(rec | j.get("meta", {}))
            n[0] += 1
            if n[0] % 50 == 0:
                print(f"  {n[0]}/{len(todo)} episodes", flush=True)

    for rnd in range(4):  # failed episodes (server restarts during a pause) are retried in later rounds
        await asyncio.gather(*(one(j) for j in todo))
        todo = [j for j in todo if (j["task"]["id"], j["arm"], j["try_idx"]) not in store.done]
        if not todo or (DEADLINE and time.time() > DEADLINE):
            break
        await asyncio.sleep(60)
    print(f"ran {n[0]} episodes; {len(todo)} still pending", flush=True)


# ---------- rendering ----------
def render(user, transcript, cut=300):
    """Compact text view of a transcript: request, each tool call + truncated result, final reply."""
    out, last = [f"User request: {user}"], ""
    for m in transcript:
        if m["role"] == "assistant":
            for tc in m.get("tool_calls") or []:
                out.append(f"Tool call: {tc['function']['name']}({tc['function']['arguments']})")
            last = m.get("content") or ""
            if not m.get("tool_calls"):
                out.append(f"Final reply: {last}")
        elif m["role"] == "tool":
            c = m["content"]
            out.append("Result: " + (c if len(c) <= cut else c[:cut] + "..."))
    if transcript and (transcript[-1]["role"] != "assistant" or transcript[-1].get("tool_calls")):
        out.append("Final reply: (none)")
    return "\n".join(out)


def failed_block(store, task, k=2):
    fails = sorted((r for r in store.arm("plain") if r["task_id"] == task["id"] and not r["success"]), key=lambda r: r["try_idx"])[:k]
    return "\n\n".join(f"--- Failed attempt {i} ---\n{render(task['user'], r['transcript'])}" for i, r in enumerate(fails, 1))


def rplus_block(store, task):
    return f"Earlier attempts of yours at this same request:\n\n{failed_block(store, task)}\n\n{RPLUS_TEXT}"


# ---------- plain stats ----------
def plain_stats(store):
    s = defaultdict(lambda: [0, 0])  # task -> [tries, successes]
    for r in store.arm("plain"):
        s[r["task_id"]][0] += 1
        s[r["task_id"]][1] += r["success"]
    return s


def words(t):
    return set(re.findall(r"\w+", t.lower()))


def borrow_candidates(store, tasks, hard, k=N_BORROW):
    """Closest solved tasks (Jaccard on request words) of a DIFFERENT scenario -> [(task, first successful plain record)]."""
    st = plain_stats(store)
    wh = words(hard["user"])
    pool = []
    for t in tasks:
        if t["scenario"] == hard["scenario"] or st[t["id"]][1] == 0:
            continue
        w = words(t["user"])
        pool.append((-len(wh & w) / max(1, len(wh | w)), t["id"], t))
    pool.sort(key=lambda x: x[:2])
    out = []
    for _, _, t in pool[:k]:
        win = min((r for r in store.arm("plain") if r["task_id"] == t["id"] and r["success"]), key=lambda r: r["try_idx"])
        out.append((t, win))
    return out


def borrow_block(store, hard, cand, win):
    return (f"Earlier attempts of yours at this request:\n\n{failed_block(store, hard)}\n\n{RPLUS_TEXT}\n\n"
            f"{BORROW_LABEL}\n{render(cand['user'], win['transcript'])}")


# ---------- FLIP ----------
FLIP_PROMPT = ("Below are failed attempts at a job. List up to {n} hidden assumptions these attempts made (about what the user wants, "
               "which tools or files to use, whether to ask or act, what order to work in). For each, give its opposite as a one-sentence "
               "new approach.\nFormat: a numbered list, one item per number, each item = the assumption, then ' -> New approach: ...'.\n\n{fails}")


def parse_numbered(text, n=MAX_FLIP):
    items = []
    for ln in text.splitlines():
        m = re.match(r"\s*(?:\*\*)?(\d+)[.)]\s*(.*)", ln)
        if m:
            items.append(m.group(2).strip())
        elif items and ln.strip():
            items[-1] += " " + ln.strip()
    return [i for i in items if i][:n]


async def flip_approaches(client, store, task):
    cache = store.jload("flip.json", {})
    if task["id"] not in cache:
        msg = [dict(role="user", content=FLIP_PROMPT.format(n=MAX_FLIP, fails=failed_block(store, task)))]
        raw = (await client.chat(msg))["content"]
        cache[task["id"]] = dict(raw=raw, approaches=parse_numbered(raw) or [raw.strip()[:600]])
        store.jsave("flip.json", cache)
    return cache[task["id"]]["approaches"]


def flip_block(store, task, approach):
    return (f"Earlier attempts of yours at this same request:\n\n{failed_block(store, task)}\n\n{RPLUS_TEXT}\n\n"
            f"Approach to take this time (it reverses a hidden assumption the failed attempts made): {approach}")


# ---------- stages ----------
async def screen(client, store, tasks, conc):
    await run_jobs(client, store, [dict(task=t, arm="plain", try_idx=i) for t in tasks for i in range(SCREEN_TRIES)], conc)


async def confirm(client, store, tasks, conc):
    st = plain_stats(store)
    todo = [t for t in tasks if st[t["id"]][0] >= SCREEN_TRIES and st[t["id"]][1] == 0]
    print(f"confirm: {len(todo)} tasks with 0/{SCREEN_TRIES}")
    await run_jobs(client, store, [dict(task=t, arm="plain", try_idx=i) for t in todo for i in range(SCREEN_TRIES, TOTAL_PLAIN)], conc)


def make_hard(store, tasks):
    st = plain_stats(store)
    hard = [t["id"] for t in tasks if st[t["id"]][0] >= TOTAL_PLAIN and st[t["id"]][1] == 0]
    info = dict(hard=hard, n_hard=len(hard), stopped=len(hard) < MIN_HARD)
    if info["stopped"]:
        info["note"] = "the 8B already reaches almost everything here"
    store.jsave("hard.json", info)
    print(f"HARD set: {len(hard)} tasks" + (f" (< {MIN_HARD}: stop)" if info["stopped"] else ""))
    return info


async def arms(client, store, tasks, conc):
    byid = {t["id"]: t for t in tasks}
    jobs = []
    for tid in store.jload("hard.json")["hard"]:
        t = byid[tid]
        jobs += [dict(task=t, arm="R+", try_idx=i, extra_block=rplus_block(store, t)) for i in range(N_RPLUS)]
        apps = None
        for i in range(N_FLIP):
            if (tid, "FLIP", i) not in store.done:
                apps = apps or await flip_approaches(client, store, t)
                jobs.append(dict(task=t, arm="FLIP", try_idx=i, extra_block=flip_block(store, t, apps[i % len(apps)]),
                                 meta=dict(approach=apps[i % len(apps)])))
        cands = borrow_candidates(store, tasks, t)
        for i in range(N_BORROW):
            if cands and (tid, "BORROW", i) not in store.done:
                c, w = cands[i % len(cands)]
                jobs.append(dict(task=t, arm="BORROW", try_idx=i, extra_block=borrow_block(store, t, c, w),
                                 meta=dict(borrowed_task=c["id"])))
    await run_jobs(client, store, jobs, conc)


def x_wins(store):
    """task_id -> first successful X episode (lowest try_idx; FLIP before BORROW)."""
    wins = {}
    for r in sorted(store.arm("FLIP") + store.arm("BORROW"), key=lambda r: (r["try_idx"], r["arm"] != "FLIP")):
        if r["success"]:
            wins.setdefault(r["task_id"], r)
    return wins


async def replay(client, store, tasks, conc):
    byid = {t["id"]: t for t in tasks}
    jobs = [dict(task=byid[tid], arm="replay", try_idx=i, extra_block=w["extra_block"], meta=dict(source_arm=w["arm"], source_try=w["try_idx"]))
            for tid, w in x_wins(store).items() for i in range(N_REPLAY)]
    await run_jobs(client, store, jobs, conc)


# ---------- report ----------
def report(store, tasks):
    hard_info = store.jload("hard.json")
    scen = {t["id"]: t["scenario"] for t in tasks}
    if not hard_info or hard_info["stopped"]:
        res = dict(verdict=f"STOPPED: HARD set has fewer than {MIN_HARD} tasks", n_hard=(hard_info or {}).get("n_hard"),
                   note="the 8B already reaches almost everything here")
        return finish(store, res)
    hard = hard_info["hard"]

    def cracked(*arms):
        return {r["task_id"] for a in arms for r in store.arm(a) if r["success"] and r["task_id"] in hard}
    R, F, B = cracked("R+"), cracked("FLIP"), cracked("BORROW")
    X = F | B
    only_x, only_r = X - R, R - X
    wins = x_wins(store)
    rep = {tid: [r["success"] for r in store.arm("replay") if r["task_id"] == tid] for tid in X}
    replayed = all(len(rep[t]) >= N_REPLAY for t in X)
    p3_each = {t: sum(rep[t]) >= 2 for t in X}
    P1 = len(X) >= 5
    P2 = len(X) - len(R) >= 3 and len(only_x) >= 2 * len(only_r)
    P3 = bool(X) and replayed and all(p3_each.values())
    if len(X) <= 1 or len(X) <= len(R):
        verdict = "PROVED WRONG"
    elif P1 and P2 and P3:
        verdict = "PASS"
    elif P1 and P2 and not replayed:
        verdict = "P1+P2 met, replays pending"
    elif P1 and P2:
        verdict = "P1+P2 met but P3 FAILED (wins not real)"
    else:
        verdict = "INCONCLUSIVE (a second sampling seed decides)"
    per_scen = {}
    for s in sorted(set(scen[t] for t in hard)):
        ids = [t for t in hard if scen[t] == s]
        per_scen[s] = dict(hard=len(ids), R_plus=len(R & set(ids)), X=len(X & set(ids)), FLIP=len(F & set(ids)), BORROW=len(B & set(ids)))
    eps = {a: dict(episodes=len(store.arm(a)), successes=sum(r["success"] for r in store.arm(a))) for a in ("plain", "R+", "FLIP", "BORROW", "replay")}
    res = dict(verdict=verdict, n_hard=len(hard), P1=P1, P2=P2, P3=P3, X_cracked=len(X), R_plus_cracked=len(R), gap=len(X) - len(R),
               only_X=sorted(only_x), only_R_plus=sorted(only_r), paired=dict(only_X=len(only_x), only_R_plus=len(only_r)),
               per_move=dict(FLIP=len(F), BORROW=len(B), both=len(F & B)), per_scenario=per_scen, episodes=eps,
               replays={t: dict(results=rep[t], pass_=p3_each[t], source=[wins[t]["arm"], wins[t]["try_idx"]]) for t in sorted(X)},
               replays_complete=replayed)
    return finish(store, res)


def finish(store, res):
    store.jsave("report.json", res)
    L = [f"# Reach-1 report", "", f"**Verdict: {res['verdict']}**", ""]
    if "X_cracked" in res:
        L += [f"HARD tasks: {res['n_hard']}", f"- X cracked: {res['X_cracked']}  (FLIP {res['per_move']['FLIP']}, BORROW {res['per_move']['BORROW']}, both {res['per_move']['both']})",
              f"- R+ cracked: {res['R_plus_cracked']}  (gap {res['gap']})",
              f"- Paired: only X {res['paired']['only_X']}, only R+ {res['paired']['only_R_plus']}",
              f"- P1 (X >= 5): {res['P1']}", f"- P2 (gap >= 3 and only-X >= 2x only-R+): {res['P2']}",
              f"- P3 (each win replays >= 2/3): {res['P3']} (replays complete: {res['replays_complete']})", "",
              "## Per scenario", "", "| scenario | hard | R+ | X | FLIP | BORROW |", "|---|---|---|---|---|---|"]
        L += [f"| {s} | {v['hard']} | {v['R_plus']} | {v['X']} | {v['FLIP']} | {v['BORROW']} |" for s, v in res["per_scenario"].items()]
        L += ["", "## Episodes", ""] + [f"- {a}: {v['successes']}/{v['episodes']}" for a, v in res["episodes"].items()]
        L += ["", "## Replays", ""] + [f"- {t}: {v['results']} from {v['source'][0]} try {v['source'][1]}" for t, v in res["replays"].items()]
    else:
        L += [res.get("note", "")]
    open(store.jpath("report.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))
    return res


# ---------- cli ----------
async def run_all(client, store, tasks, conc):
    await screen(client, store, tasks, conc)
    await confirm(client, store, tasks, conc)
    info = make_hard(store, tasks)
    if not info["stopped"]:
        await arms(client, store, tasks, conc)
        await replay(client, store, tasks, conc)
    return report(store, tasks)


async def amain(a):
    global PAUSE_FILE, DEADLINE
    PAUSE_FILE = a.pause_file
    DEADLINE = time.time() + a.deadline_hours * 3600 if a.deadline_hours else None
    store, tasks = Store(a.out), load_tasks()
    if a.limit:
        tasks = tasks[:a.limit]
    if a.half:  # PREREG addendum 1: every second task in file order, HARD stop threshold 8
        global MIN_HARD
        tasks, MIN_HARD = tasks[::2], 8
    if a.cmd == "hard":
        return make_hard(store, tasks)
    if a.cmd == "report":
        return report(store, tasks)
    client = Client(a.base_url, a.model, a.api_key, extra_body=json.loads(a.extra_body) if a.extra_body else None)
    try:
        models = await client.models()
    except Exception as e:
        models = f"error: {e}"
    meta = store.jload("run_meta.json", {"runs": []})
    meta["runs"].append(dict(time=datetime.datetime.utcnow().isoformat() + "Z", args=vars(a), models_response=models))
    store.jsave("run_meta.json", meta)
    fn = dict(screen=screen, confirm=confirm, arms=arms, replay=replay)
    if a.cmd == "all":
        return await run_all(client, store, tasks, a.concurrency)
    return await fn[a.cmd](client, store, tasks, a.concurrency)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cmd", choices=["screen", "confirm", "hard", "arms", "replay", "report", "all"])
    p.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1"))
    p.add_argument("--model", default=os.environ.get("MODEL", "model"))
    p.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "none"))
    p.add_argument("--out", default="out")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--extra-body", default=None, help='JSON merged into every request, e.g. {"chat_template_kwargs": {"enable_thinking": false}}')
    p.add_argument("--pause-file", default=None, help="wait before each episode while this file exists")
    p.add_argument("--deadline-hours", type=float, default=0, help="stop launching episodes after this many hours (0 = none)")
    p.add_argument("--half", action="store_true", help="PREREG addendum 1 subset: every second task, MIN_HARD 8")
    p.add_argument("--limit", type=int, default=0, help="debug: only the first N tasks")
    asyncio.run(amain(p.parse_args(argv)))


if __name__ == "__main__":
    main()
