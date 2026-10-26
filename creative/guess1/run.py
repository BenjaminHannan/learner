"""Guess-1 runner (see PREREG.md). Resumable: results.jsonl is append-only, (task_id, arm, try_idx) already present is skipped."""
import argparse, asyncio, datetime, importlib.util, json, os, re, sys, zlib
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
R1 = os.path.join(os.path.dirname(HERE), "reach1")
sys.path.insert(0, R1)
from episode import run_episode, SYSTEM  # noqa: E402
from sandbox import World  # noqa: E402
from client import Client, SAMPLING  # noqa: E402
_s = importlib.util.spec_from_file_location("reach1_run", os.path.join(R1, "run.py"))
r1 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(r1)
Store, load_tasks = r1.Store, r1.load_tasks

SCREEN_TRIES, MAX_T, MIN_T, SCREEN_LO, SCREEN_HI = 8, 48, 20, 0, 3
N_TRIES, N_MENU, PER_APPROACH, TOP_CAP, TOP_TOL = 12, 6, 2, 16, 0.15
P1_MARGIN, P2_MARGIN, P3_RATIO, P4_RATIO, WRONG_MARGIN, DIAG_RATIO = 4, 3, 1.5, 2, 1, 2
ARMS = ("IND", "HOT", "LIST", "MENU")
IND_S = dict(temperature=0.7, top_p=0.95)
HOT_S = dict(temperature=1.0, top_p=1.0)
LIST_HEAD = "Your earlier attempts at this job (each was a fresh start):"
LIST_TAIL = "Do the job in a way that is clearly different from every one of these."
MENU_ASK = ("List 6 genuinely different ways to do this job (different tools, different order, or a different reading of what the user wants). "
            "One per line, numbered.")


def akey(arm, seed):
    return arm if seed == 1 else f"{arm}.s{seed}"


# ---------- plan signature ----------
def _norm(v):
    if isinstance(v, str):
        return " ".join(v.lower().split())
    if isinstance(v, dict):
        return {str(k): _norm(x) for k, x in sorted(v.items())}
    if isinstance(v, (list, tuple)):
        return [_norm(x) for x in v]
    return v


def tool_calls_of(transcript):
    out = []
    for m in transcript:
        if m["role"] == "assistant":
            for tc in m.get("tool_calls") or []:
                f, a = tc["function"], tc["function"].get("arguments", {})
                if isinstance(a, str):
                    try:
                        a = json.loads(a) if a.strip() else {}
                    except json.JSONDecodeError:
                        pass
                out.append((f["name"], a))
    return out


def ending(rec):
    r = (rec.get("final_reply") or "").strip()
    return "none" if not r else "question" if r.endswith("?") else "reply"


def signature(rec):
    """Ordered (tool, normalised args) list + how the episode ended: reply / question (reply ends with '?') / none (no final reply)."""
    return json.dumps([[n, _norm(a)] for n, a in tool_calls_of(rec["transcript"])] + [ending(rec)], sort_keys=True, ensure_ascii=False)


# ---------- prompts ----------
def summarise_try(rec):
    calls = [f"{n}({(a if isinstance(a, str) else json.dumps(a, ensure_ascii=False))[:80]})" for n, a in tool_calls_of(rec["transcript"])]
    reply = " ".join((rec.get("final_reply") or "").split())[:120]
    return f"calls: {'; '.join(calls) if calls else '(none)'} | final reply: {reply or '(none)'}"


def list_block(earlier):
    """earlier: this arm's earlier records for the task, in try order. None for try 1. Never shows success/check info."""
    if not earlier:
        return None
    return "\n".join([LIST_HEAD] + [f"{i}. {summarise_try(r)}" for i, r in enumerate(earlier, 1)] + ["", LIST_TAIL])


def parse_menu(text, n=N_MENU):
    items = []
    for ln in (text or "").splitlines():
        m = re.match(r"\s*(?:[*#>\-]\s*)*(?:\*\*)?(?:approach\s*)?(\d+)\s*[.):]\s*(.*)", ln, re.I)
        if m:
            items.append(m.group(2).replace("**", "").strip())
        elif items and ln.strip() and ln[:1].isspace():
            items[-1] += " " + ln.strip()
    return [i[:400] for i in items if i][:n]


def menu_block(line):
    return f"Approach to use: {line}"


# ---------- sampling / seeds ----------
def job_seed(seed, tid, arm, i):
    return seed * 100000 + zlib.crc32(f"{tid}|{arm}|{i}".encode()) % 100000


def sampling_for(arm, seed, tid, i, caps):
    s = dict(HOT_S if arm == "HOT" else IND_S)
    if arm == "HOT" and caps.get("min_p", True):
        s["min_p"] = 0.1
    if caps.get("seed", True):
        s["seed"] = job_seed(seed, tid, arm, i)
    return s


async def probe(client):
    """Does the server accept min_p / seed in the request body? (HTTP 2xx = accepted; a server may still ignore them silently.)"""
    caps, old = {}, client.retries
    client.retries = 0
    for k, v in (("min_p", 0.1), ("seed", 1)):
        try:
            await client.chat([dict(role="user", content="Say hi.")], None, max_tokens=4, **{k: v})
            caps[k] = True
        except Exception as e:
            caps[k], caps[k + "_error"] = False, f"{type(e).__name__}: {e}"[:300]
    client.retries = old
    return caps


# ---------- running ----------
async def one(client, store, sem, task, arm, i, block, sampling, seed, meta=None):
    """Run and store one try. False on failure (left undone so a rerun retries it)."""
    key = akey(arm, seed)
    async with sem:
        try:
            rec = await run_episode(client, task, key, i, block, sampling)
        except Exception as e:
            print(f"! {task['id']} {key} {i}: {type(e).__name__}: {e}", file=sys.stderr)
            return False
    await store.add(rec | dict(seed=sampling.get("seed"), seed_base=seed, sampling=sampling) | (meta or {}))
    return True


async def rounds(make, rounds_=3):
    """make() -> coroutines for what is still pending; retry failed ones in later rounds."""
    for r in range(rounds_):
        cs = make()
        if not cs:
            return
        await asyncio.gather(*cs)
        if r < rounds_ - 1:
            await asyncio.sleep(2)
    left = len(make_pending(make))
    print(f"{left} still pending" if left else "done", flush=True)


def make_pending(make):
    cs = make()
    for c in cs:
        c.close()
    return cs


def subset(tasks):
    return tasks[::2]


async def screen(client, store, tasks, seed, conc, caps):
    sem = asyncio.Semaphore(conc)
    todo = lambda: [one(client, store, sem, t, "plain", i, None, sampling_for("plain", 1, t["id"], i, caps), 1)
                    for t in tasks for i in range(SCREEN_TRIES) if (t["id"], "plain", i) not in store.done]
    await rounds(todo)


def pick(store, tasks):
    cnt = defaultdict(lambda: [0, 0])
    for r in store.arm("plain"):
        cnt[r["task_id"]][0] += 1
        cnt[r["task_id"]][1] += r["success"]
    incomplete = [t["id"] for t in tasks if cnt[t["id"]][0] < SCREEN_TRIES]
    if incomplete:
        raise SystemExit(f"screen incomplete for {len(incomplete)} tasks (first: {incomplete[:3]}); rerun `screen`")
    low = [t["id"] for t in tasks if SCREEN_LO <= cnt[t["id"]][1] <= SCREEN_HI]
    info = dict(n_subset=len(tasks), n_low=len(low), T=low[:MAX_T], screen_successes={t["id"]: cnt[t["id"]][1] for t in tasks}, stopped=len(low) < MIN_T)
    if info["stopped"]:
        info["note"] = "K2 already solves almost everything here"
    store.jsave("target.json", info)
    print(f"T: {len(info['T'])} tasks (low-success {len(low)} of {len(tasks)})" + (f" < {MIN_T}: STOP, {info['note']}" if info["stopped"] else ""))
    return info


async def get_menu(client, store, task, seed, caps):
    cache, k = store.jload("menu.json", {}), (task["id"] if seed == 1 else f"{task['id']}.s{seed}")
    if k not in cache:
        msgs = [dict(role="system", content=SYSTEM.format(today=World.from_json(task["state"]).today)),
                dict(role="user", content=f"The user's request for this job: {task['user']}\n\n{MENU_ASK}")]
        out = await client.chat(msgs, None, **sampling_for("MENU", seed, task["id"], -1, caps))
        raw = out["content"]
        cache[k] = dict(task_id=task["id"], seed_base=seed, raw=raw, approaches=parse_menu(raw) or [" ".join(raw.split())[:400] or "any sensible approach"], usage=out.get("usage") or {})
        store.jsave("menu.json", cache)
    return cache[k]["approaches"]


async def arms(client, store, tasks, seed, conc, caps):
    sem, fresh = asyncio.Semaphore(conc), lambda a, t, i: (t["id"], akey(a, seed), i) not in store.done
    menus = {}
    for t in tasks:
        menus[t["id"]] = await get_menu(client, store, t, seed, caps)

    async def chain(t):  # LIST: tries in order; a failed try stops the chain until the next round
        for i in range(N_TRIES):
            if not fresh("LIST", t, i):
                continue
            earlier = sorted((r for r in store.arm(akey("LIST", seed)) if r["task_id"] == t["id"]), key=lambda r: r["try_idx"])
            if not await one(client, store, sem, t, "LIST", i, list_block([r for r in earlier if r["try_idx"] < i]), sampling_for("LIST", seed, t["id"], i, caps), seed):
                return

    def todo():
        cs = [one(client, store, sem, t, a, i, None, sampling_for(a, seed, t["id"], i, caps), seed) for t in tasks for a in ("IND", "HOT") for i in range(N_TRIES) if fresh(a, t, i)]
        for t in tasks:
            ap = menus[t["id"]]
            cs += [one(client, store, sem, t, "MENU", i, menu_block(ap[(i // PER_APPROACH) % len(ap)]), sampling_for("MENU", seed, t["id"], i, caps), seed,
                       dict(approach=ap[(i // PER_APPROACH) % len(ap)])) for i in range(N_TRIES) if fresh("MENU", t, i)]
            if any(fresh("LIST", t, i) for i in range(N_TRIES)):
                cs.append(chain(t))
        return cs
    await rounds(todo)


# ---------- equal-compute top-up ----------
def menu_tokens(store, seed, field, T=None):
    return sum(v["usage"].get(field, 0) for v in store.jload("menu.json", {}).values() if v["seed_base"] == seed and (T is None or v["task_id"] in T))


def gen_tokens(store, arm, seed):
    n = sum(r["tokens"]["completion"] for r in store.arm(akey(arm, seed)))
    if arm == "MENU":
        n += menu_tokens(store, seed, "completion_tokens")
    return n


def topup_needed(ind_tokens, other_tokens, n_ind_tries):
    """True if IND should get one more plain try per task: some other arm used > 15% more generated tokens and IND is under the cap."""
    return n_ind_tries < TOP_CAP and max(other_tokens) > (1 + TOP_TOL) * ind_tokens


async def topup(client, store, tasks, seed, conc, caps):
    sem, n = asyncio.Semaphore(conc), N_TRIES
    while topup_needed(gen_tokens(store, "IND", seed), [gen_tokens(store, a, seed) for a in ("LIST", "MENU")], n):
        i = n
        await rounds(lambda: [one(client, store, sem, t, "IND", i, None, sampling_for("IND", seed, t["id"], i, caps), seed)
                              for t in tasks if (t["id"], akey("IND", seed), i) not in store.done])
        n += 1
    print(f"IND tries per task after top-up: {n}")


# ---------- metrics ----------
def arm_metrics(rows, T, max_try=None):
    by = defaultdict(list)
    for r in rows:
        if r["task_id"] in T and (max_try is None or r["try_idx"] < max_try):
            by[r["task_id"]].append(r)
    cracked = {t for t, rs in by.items() if any(r["success"] for r in rs)}
    dist = sum(len({signature(r) for r in rs}) for rs in by.values())
    dcor = sum(len({signature(r) for r in rs if r["success"]}) for rs in by.values())
    tops = [max(Counter(signature(r) for r in rs).values()) / len(rs) for rs in by.values()]
    return dict(cracked=sorted(cracked), n_cracked=len(cracked), distinct_plans=dist, distinct_correct_plans=dcor,
                top_share=sum(tops) / len(tops) if tops else None, tries=sum(map(len, by.values())),
                gen_tokens=sum(r["tokens"]["completion"] for r in rows if r["task_id"] in T and (max_try is None or r["try_idx"] < max_try)),
                prompt_tokens=sum(r["tokens"]["prompt"] for r in rows if r["task_id"] in T and (max_try is None or r["try_idx"] < max_try)))


def verdict(c, mult=1):
    """c: per arm {n_cracked, distinct_plans, distinct_correct_plans, only_vs_IND: (tasks only this arm cracks, tasks only IND cracks)};
    mult = number of seeds summed (marks scale with it). IND is the topped-up IND."""
    ind, hot = c["IND"], c["HOT"]
    best = "MENU" if c["MENU"]["n_cracked"] > c["LIST"]["n_cracked"] else "LIST"
    b = c[best]
    only_b, only_i = b["only_vs_IND"]
    P1 = b["n_cracked"] >= ind["n_cracked"] + P1_MARGIN * mult
    P2 = b["n_cracked"] >= hot["n_cracked"] + P2_MARGIN * mult
    P3 = b["distinct_correct_plans"] >= P3_RATIO * ind["distinct_correct_plans"]
    P4 = only_b > only_i and only_b >= P4_RATIO * only_i
    wrong = max(c["LIST"]["n_cracked"], c["MENU"]["n_cracked"]) <= ind["n_cracked"] + WRONG_MARGIN * mult
    v = "PASS" if P1 and P2 and P3 and P4 else "PROVED WRONG" if wrong else "INCONCLUSIVE"
    diag = (not P1) and b["distinct_plans"] >= DIAG_RATIO * ind["distinct_plans"]
    return dict(verdict=v, best=best, P1=P1, P2=P2, P3=P3, P4=P4, proved_wrong=wrong, diagnostic_diversity_without_quality=diag, only_best=only_b, only_ind=only_i, mult=mult)


def seeds_present(store):
    return sorted({r.get("seed_base", 1) for r in store.rows if r["arm"] != "plain"})


def report(store, tasks):
    tg = store.jload("target.json")
    if not tg or tg["stopped"]:
        res = dict(verdict="STOPPED: fewer than %d low-success tasks" % MIN_T, n_low=(tg or {}).get("n_low"), note="K2 already solves almost everything here")
        return finish(store, res)
    T, per, tot = set(tg["T"]), {}, defaultdict(lambda: defaultdict(float))
    seeds = [s for s in seeds_present(store) if all(store.arm(akey(a, s)) for a in ARMS)]
    if not seeds:
        return finish(store, dict(verdict="NO ARM RESULTS YET", n_T=len(T)))
    for s in seeds:
        m = {a: arm_metrics(store.arm(akey(a, s)), T) for a in ARMS}
        m["IND12"] = arm_metrics(store.arm(akey("IND", s)), T, N_TRIES)
        m["MENU"]["gen_tokens"] += menu_tokens(store, s, "completion_tokens", T)
        m["MENU"]["prompt_tokens"] += menu_tokens(store, s, "prompt_tokens", T)
        for a in ("LIST", "MENU"):
            m[a]["only_vs_IND"] = (len(set(m[a]["cracked"]) - set(m["IND"]["cracked"])), len(set(m["IND"]["cracked"]) - set(m[a]["cracked"])))
        per[s] = m
    comb = {}
    for a in ARMS:
        comb[a] = {k: sum(per[s][a][k] for s in seeds) for k in ("n_cracked", "distinct_plans", "distinct_correct_plans")}
    for a in ("LIST", "MENU"):  # paired counts are per seed, summed; BEST (chosen on summed cracked) reads its own
        comb[a]["only_vs_IND"] = tuple(sum(per[s][a]["only_vs_IND"][j] for s in seeds) for j in (0, 1))
    v = verdict(comb, len(seeds))
    if v["verdict"] == "INCONCLUSIVE" and len(seeds) == 1:
        v["next"] = "run Stage 2 with --seed 2 on the same T, then report again (sum of both seeds, marks doubled)"
    res = dict(**v, n_T=len(T), seeds=seeds, combined=comb, per_seed=per, ind_tries_per_task={s: per[s]["IND"]["tries"] / max(1, len(T)) for s in seeds},
               compute_ratio_vs_IND={s: {a: per[s][a]["gen_tokens"] / max(1, per[s]["IND"]["gen_tokens"]) for a in ARMS} for s in seeds})
    return finish(store, res)


def finish(store, res):
    store.jsave("report.json", res)
    L = ["# Guess-1 report", "", f"**Verdict: {res['verdict']}**", ""]
    if "per_seed" in res:
        L += [f"T = {res['n_T']} tasks; seeds {res['seeds']}; BEST = {res['best']} (marks x{res['mult']})", "",
              f"- P1 (BEST cracked >= IND + {P1_MARGIN * res['mult']}): {res['P1']}", f"- P2 (BEST >= HOT + {P2_MARGIN * res['mult']}): {res['P2']}",
              f"- P3 (BEST distinct correct plans >= {P3_RATIO}x IND): {res['P3']}", f"- P4 (only-BEST {res['only_best']} vs only-IND {res['only_ind']}, >= {P4_RATIO}:1): {res['P4']}",
              f"- PROVED WRONG test (LIST and MENU both <= IND + {WRONG_MARGIN * res['mult']}): {res['proved_wrong']}",
              f"- Diagnostic (diversity without quality): {res['diagnostic_diversity_without_quality']}"]
        if "next" in res:
            L.append(f"- Next: {res['next']}")
        for s, m in res["per_seed"].items():
            L += ["", f"## Seed {s}", "", "| arm | tries | cracked | distinct plans | distinct correct | top-share | gen tokens | prompt tokens |", "|---|---|---|---|---|---|---|---|"]
            L += [f"| {a} | {x['tries']} | {x['n_cracked']} | {x['distinct_plans']} | {x['distinct_correct_plans']} | {x['top_share']:.3f} | {x['gen_tokens']} | {x['prompt_tokens']} |"
                  for a, x in m.items() if x["tries"]]
            L += ["", "IND is the topped-up arm; IND12 is its first 12 tries. Generated-token ratio vs IND: " +
                  ", ".join(f"{a} {r:.2f}" for a, r in res["compute_ratio_vs_IND"][s].items())]
    else:
        L.append(res.get("note", ""))
    open(store.jpath("report.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))
    return res


# ---------- cli ----------
async def amain(a):
    store, tasks = Store(a.out), load_tasks()
    if a.limit:
        tasks = tasks[:a.limit]
    full, tasks = tasks, subset(tasks)
    if a.all_tasks or (store.jload("target.json") or {}).get("extended"):  # addendum 1: screen widened to all tasks
        tasks = full
    byid = {t["id"]: t for t in full}
    if a.cmd == "pick":
        return pick(store, tasks)
    if a.cmd == "report":
        return report(store, tasks)
    client = Client(a.base_url, a.model, a.api_key, extra_body=json.loads(a.extra_body) if a.extra_body else None)
    try:
        models = await client.models()
    except Exception as e:
        models = f"error: {e}"
    caps = await probe(client)
    meta = store.jload("run_meta.json", {"runs": []})
    meta["runs"].append(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(), args=vars(a), models_response=models, server_accepts=caps,
                             sampler=dict(default=SAMPLING, IND=IND_S, HOT=HOT_S | ({"min_p": 0.1} if caps["min_p"] else {}), min_p_used_in_HOT=caps["min_p"],
                                          seed_passed=caps["seed"], seed_formula="seed*100000 + crc32(task|arm|try) % 100000"),
                             extra_body=client.extra))
    store.jsave("run_meta.json", meta)

    def targets():
        tg = store.jload("target.json")
        if not tg or tg["stopped"]:
            raise SystemExit("no target set (run `pick`; stopped if |T| < %d)" % MIN_T)
        return [byid[t] for t in tg["T"]]
    c = a.concurrency
    if a.cmd == "screen":
        return await screen(client, store, tasks, a.seed, c, caps)
    if a.cmd == "all":
        await screen(client, store, tasks, a.seed, c, caps)
        if pick(store, tasks)["stopped"] and len(tasks) < len(full):  # addendum 1: widen the screen to all tasks, re-pick
            tasks = full
            await screen(client, store, tasks, a.seed, c, caps)
            info = pick(store, tasks)
            info["extended"] = True
            store.jsave("target.json", info)
        if store.jload("target.json")["stopped"]:
            return report(store, tasks)
        await arms(client, store, targets(), a.seed, c, caps)
        await topup(client, store, targets(), a.seed, c, caps)
        return report(store, tasks)
    fn = dict(arms=arms, topup=topup)[a.cmd]
    return await fn(client, store, targets(), a.seed, c, caps)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cmd", choices=["screen", "pick", "arms", "topup", "report", "all"])
    p.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1"))
    p.add_argument("--model", default=os.environ.get("MODEL", "model"))
    p.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "none"))
    p.add_argument("--out", default="out")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--extra-body", default=None, help='JSON merged into every request, e.g. {"chat_template_kwargs": {"enable_thinking": false}}')
    p.add_argument("--all-tasks", action="store_true", help="use all tasks instead of every second one (prereg addendum 1)")
    p.add_argument("--limit", type=int, default=0, help="debug: only the first N tasks (before taking every second)")
    p.add_argument("--seed", type=int, default=1, help="Stage 2 seed (1 = prereg run; 2 = the follow-up if INCONCLUSIVE). The screen always uses seed 1.")
    asyncio.run(amain(p.parse_args(argv)))


if __name__ == "__main__":
    main()
