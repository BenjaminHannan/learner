"""Shared bits for Probe-6 (PREREG.md): task selection, the ask-first judge prompt, AUROC, the ASK-GATE / ORACLE-GATE pick rule, dev pools."""
import json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CREATIVE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(CREATIVE, "probe1"))
import probe_common as PC  # noqa: E402  (also puts reach1/rlaif_copy on sys.path)
import write_probes as WP  # noqa: E402

MNT = PC.MNT
TRAP_SCENARIOS = {"confirm_irreversible", "clarify"}
QUESTION = "Should the assistant ask the user a question before acting on this request? Answer yes or no."
GRID = [round(0.1 * i, 1) for i in range(1, 10)]
DEV_NONTARGET_N, DEV_SEED = 200, 6
SEED1_RESULTS = MNT + "guess1/out/run/"
SEED2_RESULTS = MNT + "guess1/out-seed2/guess1-seed2/run/"
POOLS = MNT + "pick1/pools.jsonl"
PROBE_SCORES = os.path.join(CREATIVE, "probe3", "results", "m3", "probe_scores.jsonl")
SELF_SCORES = MNT + "pick1/out/pick1/k2_scores.jsonl"


def is_trap(task):
    return task["scenario"] in TRAP_SCENARIOS


def dev_tasks():
    """-> (target tasks [48], seeded non-target sample [200]); both sorted by id. Sample = random.Random(6).sample of the 372 sorted non-target ids."""
    tasks = PC.load_tasks()
    T = set(PC.target_ids(SEED2_RESULTS))
    tgt = sorted((t for t in tasks if t["id"] in T), key=lambda t: t["id"])
    rest = sorted((t for t in tasks if t["id"] not in T), key=lambda t: t["id"])
    pick = random.Random(DEV_SEED).sample(rest, DEV_NONTARGET_N)
    return tgt, sorted(pick, key=lambda t: t["id"])


def judge_state_text(task):
    """What every judge sees: date, the request, the start state and the tool list, exactly the pieces write_probes.build_prompt(state=...) shows
    (without its check-writing instructions). No tries, reference, checks or rubric."""
    t0 = task["state"].get("today", "2026-10-24")
    seen = json.dumps({k: v for k, v in task["state"].items() if k != "today"}, indent=1)
    return (f"Today is {t0}.\n\nA personal assistant has tools for the user's files, email, calendar, notes and reminders. The user sent it this request:\n\n"
            f"\"\"\"\n{task['user']}\n\"\"\"\n\nBefore the assistant starts, this is everything in the user's files, mail, calendar, notes and reminders (JSON):\n\n{seen}\n\n"
            f"The assistant's tools:\n{WP.tool_list()}")


def judge_prompt(task):
    return judge_state_text(task) + "\n\n" + QUESTION


def auroc(scores, labels):
    """P(score of a positive > score of a negative), ties 1/2 (rank-sum). None if a class is empty."""
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return None
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def asks(reply):
    return "?" in (reply or "")


def gate_pick(members, test_t, self_, p_ask, t):
    """ASK-GATE (PREREG). members: list of dicts sorted by try_idx with 'final_reply' and 'k' (key); test_t / self_: {k: score}; p_ask: judge P(ask) for the task.
    If p_ask >= t: among tries whose final reply contains '?', best (TEST-T, SELF), lowest try on a full tie; if none ask, fall back to TEST-T.
    Else TEST-T. TEST-T = (score rounded to 9 places, SELF; missing SELF = 0.5), first try wins ties, as Probe-4/5's picker."""
    def key(m):
        s = self_.get(m["k"])
        return (round(test_t[m["k"]], 9), 0.5 if s is None else s)
    cand = members
    if p_ask is not None and p_ask >= t:
        a = [m for m in members if asks(m["final_reply"])]
        cand = a or members
    best = cand[0]
    for m in cand[1:]:
        if key(m) > key(best):
            best = m
    return best


def oracle_p(task):
    return 1.0 if is_trap(task) else 0.0


def read_jsonl(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def load_dev_pools():
    """-> {pool: [member dicts sorted by try_idx]}, members: pool, task, arm, try_idx, success, final_reply, k. 192 pools of 12 (pick1 pools + final_reply from Guess-1 results)."""
    fr = {}
    for d in (SEED2_RESULTS, SEED1_RESULTS):
        for r in read_jsonl(d + "results.jsonl"):
            fr.setdefault((r["task_id"], r["arm"], int(r["try_idx"])), r["final_reply"])
    pools = {}
    for r in read_jsonl(POOLS):
        arm = r["arm"] if r["seed"] == 1 else f"{r['arm']}.s{r['seed']}"
        m = dict(pool=r["pool"], task=r["task"], arm=arm, try_idx=r["try_idx"], success=bool(r["success"]),
                 final_reply=fr[(r["task"], arm, r["try_idx"])], k=f"{r['pool']}|{r['try_idx']}")
        pools.setdefault(r["pool"], []).append(m)
    return {p: sorted(v, key=lambda m: m["try_idx"]) for p, v in pools.items()}


def pick_rates(pools, tasks_by_id, test_t, self_, p_ask_by_task, t):
    """-> dict(all, traps, plain) pick rate in % over pools (p_ask_by_task: {task: P(ask)})."""
    out = {"all": [], "traps": [], "plain": []}
    for p, mem in pools.items():
        tid = mem[0]["task"]
        w = float(gate_pick(mem, test_t, self_, p_ask_by_task.get(tid), t)["success"])
        out["all"].append(w)
        out["traps" if is_trap(tasks_by_id[tid]) else "plain"].append(w)
    return {g: (100 * sum(v) / len(v) if v else None) for g, v in out.items()}
