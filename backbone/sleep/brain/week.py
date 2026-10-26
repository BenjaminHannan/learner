"""Week-1 world for Sleep-B (see PREREG-sleepB.md): 7 simulated days of raw chats between a fictional user "Sam" and an assistant.

Facts about Sam's contacts come up in passing. The plan is deterministic (seed 1, no network). Each session's chat is written by
Claude (Sonnet 5.5) from that session's plan; code checks every planned mention is present (both names in one user turn), no stray
names, old/new values on the right days, no test wording. Sessions that fail are regenerated (up to 3 times, then up to 3 "rescue" attempts
with a stronger reminder). A stricter wording audit of the change cues (strict_check) only picks between accepted attempts; if none passes it,
the first accepted attempt is kept and the complaint is listed under "warnings" in week1.json. Raw API responses are cached in data/raw/
(a rerun of --write with the same code costs nothing); cost is tracked from response usage (cap $3, conservatively priced at $3/$15 per M).
A bigger world (Week-2, PREREG-sleepB-addendum6.md) is the same generator with --seed 2 --scale 2.5 --out data/week2.json --cap 8: C2/C4 facts x scale, C1, changing facts
and routines grow more slowly (see scaled()), sessions per day grow with the mention load; its raw cache is data/raw_week2/ (Week-1's data/raw/ is untouched).
--rescue N allows more rescue attempts for a session that has no accepted attempt after the default ones (attempts past the default add a turn-count reminder to the prompt).

  python backbone/sleep/brain/week.py --plan-only             # counts + examples, no network
  python backbone/sleep/brain/week.py --prompt 1:1            # print the prompt of day 1, session 1 (no network)
  python backbone/sleep/brain/week.py --only 1:1              # trial: write one session (cached in data/raw/), print it
  python backbone/sleep/brain/week.py --write                 # all 42 sessions -> data/week1.json + week1.json.sha256 (cap $3)
  python backbone/sleep/brain/week.py --write --seed 2 --scale 2.5 --out backbone/sleep/brain/data/week2.json --cap 8   # Week-2
  from week import build_plan, template_week                  # template_week(): offline tiny week, same schema, for smoke tests
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import facts as F  # noqa: E402
from facts import HOP, REL, make_names, norm  # noqa: E402

DATA = HERE / "data"
RAW = DATA / "raw"
MODEL = "claude-sonnet-5-5"
URL = "https://api.anthropic.com/v1/messages"
PRICE = (2.0, 10.0)       # listed $/M tokens, Sonnet 5.5 (in, out)
CAP_PRICE = (3.0, 15.0)   # conservative price used for the hard cap
CAP = 3.0
RETRIES = 3               # regenerations per session after the first attempt
RESCUE = 3                # extra attempts (with a stronger reminder) for a session that still fails after RETRIES; reported
CLASS_DAYS = {"C1": 1, "C2": 2, "C4": 4}
CHAINS = [("mentor_lives", "mentor_of", "lives_in", "b", "a"),    # (kind, rel1, rel2, x slot of rel1, slot joining rel2 to rel1)
          ("sibling_works", "sibling", "works_at", "a", "b"),
          ("owner_born", "owns", "born_in", "b", "a")]
ACTIVITIES = ["dinner", "lunch", "coffee", "brunch", "a game of tennis", "a game of chess", "a climbing session", "a book club meeting",
              "a pottery class", "a jam session", "game night", "a study session"]
MORE_ACTIVITIES = ["a movie night", "a long walk", "a bike ride", "a barbecue", "a karaoke night", "a painting session", "breakfast", "a board game afternoon"]  # only when n_rt > 12
WEEKDAY = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TOPICS = ["a thank-you email", "a weekend trip itinerary", "a dinner recipe", "a grocery list", "math homework", "a cover letter",
          "a birthday party plan", "packing for a flight", "a gym schedule", "a reply to a landlord", "a book to read next", "meal prep",
          "a presentation outline", "a monthly budget", "a leaky faucet", "a road-trip playlist", "a short toast", "a chemistry study plan",
          "a gift idea", "a polite text declining an invite", "a camping packing list", "a houseplant that keeps dying", "a resume bullet",
          "comparing two phone plans", "a history essay thesis", "a cleaning schedule", "translating a phrase", "a surprise-party plan"]
STYLES = ["tossed in as a quick aside in the middle of a request", "as a parenthetical remark", "as background explaining why Sam is asking",
          "as a side comment just before the real question", "while chatting about their day", "as part of describing a plan or errand",
          "as an offhand remark at the end of the message", "as context while asking for writing help",
          "while mentioning something small Sam is happy or annoyed about", "as a reminder Sam is giving themselves"]
WHEN = ["tonight", "later today", "this evening", "tomorrow", "yesterday", "earlier today"]
FILLERS = ["Can you suggest a quick weeknight dinner?", "How do I politely ask for an extension on homework?", "What's a good stretch routine for a stiff back?",
           "Convert 2 cups of flour to grams please.", "Give me a two-line pep talk, I have a long day.", "Is it worth buying a refurbished laptop?"]
HABIT = re.compile(r"\b(usually|always|every|each|regular|regularly|weekly|monthly|daily|routine|habit|typically|normally|as usual|the usual|"
                   r"per usual|as always|like always|tradition|ritual|often)\b", re.I)
CHANGE = re.compile(r"\b(new|now|moved|move|moving|finally|just|recent|recently|switch\w*|start\w*|join\w*|relocat\w*|transfer\w*|latest|"
                    r"these days|lately|since|settled|landed|got)\b", re.I)  # loose cue, checked in every attempt
STRONG = re.compile(r"\b(moved|moving|moves?|relocat\w*|switch\w*|new (job|gig|role|position|home|place|apartment|house|city|town|spot|workplace|"
                    r"company|employer|office)|finally|started|starting|starts?|recently|joined|landed|transfer\w*|these days|lately|last (week|month)|"
                    r"this (week|month)|no longer|used to)\b", re.I)  # strict cue: new-phase turns must have one, old-phase turns must not (accepted attempts only)
STRONG_OLD = re.compile(STRONG.pattern.replace("finally|", ""), re.I)  # "finally" is too common in unrelated chatter to forbid on old-value turns


# ----------------------------------------------------------------------------------------------- the plan (no network)
def build_plan(seed=1, n_days=7, per_rel=20, n_ch=20, n_rt=12, sessions=6, classes=("C1", "C2", "C4"), tie=False, mix=None):
    """Items (120 base facts, 20 changing, 12 routines at defaults), schedule (day -> 6 sessions of planned mentions), and tests.
    mix: {class: number of facts} (sums to 6 * per_rel) instead of equal thirds; each relation gets n // 6 of a class, the remainders go round-robin."""
    assert n_days >= 2 and all(CLASS_DAYS[c] <= n_days for c in classes)
    rng = random.Random(seed)
    s1_names = {e.lower() for f in F.build(0)["facts"] for e in f["entities"]}  # every Sleep-1 (seed 0) name is off limits
    taken = set(s1_names)
    people = make_names(rng, 5 * per_rel, taken)
    mentors, students, sibA, sibB, owners = (people[i * per_rel:(i + 1) * per_rel] for i in range(5))
    cities, companies, towns, boats = (make_names(rng, per_rel, taken) for _ in range(4))
    pairs = {"mentor_of": list(zip(mentors, students)), "lives_in": list(zip(mentors, cities)), "sibling": list(zip(sibA, sibB)),
             "works_at": list(zip(sibB, companies)), "owns": list(zip(owners, boats)), "born_in": list(zip(owners, towns))}
    items, prev = [], None
    if mix:
        assert sum(mix.values()) == 6 * per_rel and set(mix) <= set(classes) and not tie, mix
        offs, o = {}, 0
        for c, n in mix.items():
            offs[c], o = o, o + n % 6
    for r, (rel, ps) in enumerate(pairs.items()):  # stratified by relation: each class gets per_rel/len(classes) (+-1), rotated by relation
        seq = ([c for c, n in mix.items() for _ in range(n // 6 + ((r - offs[c]) % 6 < n % 6))] if mix
               else [classes[(i + r) % len(classes)] for i in range(per_rel)])
        rng.shuffle(seq)
        if tie and r % 2:  # (tiny weeks only) both facts of a chain share a class, so two-hop tests exist
            seq = prev
        prev = seq
        for (a, b), c in zip(ps, seq):
            items.append({"kind": "fact", "rel": rel, "a": a, "b": b, "class": c, "text": REL[rel][0].format(a=a, b=b), "days": [], "names": [a, b]})
    rng.shuffle(items)
    for i, it in enumerate(items):
        it["id"] = f"f{i}"
    chg = make_names(rng, n_ch, taken)
    vals = make_names(rng, 2 * n_ch, taken)
    ch = []
    for i, p in enumerate(chg):
        rel = "lives_in" if i < n_ch // 2 else "works_at"
        old, new = vals[2 * i], vals[2 * i + 1]
        ch.append({"kind": "changing", "rel": rel, "a": p, "b": new, "old_b": old, "class": "CH", "text": REL[rel][0].format(a=p, b=new),
                   "old_text": REL[rel][0].format(a=p, b=old), "days": [], "names": [p, old, new]})
    rng.shuffle(ch)
    rt = []
    acts = rng.sample(ACTIVITIES + MORE_ACTIVITIES if n_rt > len(ACTIVITIES) else ACTIVITIES, n_rt)
    for i, (p, pl) in enumerate(zip(make_names(rng, n_rt, taken), make_names(rng, n_rt, taken))):
        rt.append({"kind": "routine", "rel": "routine", "a": p, "b": pl, "activity": acts[i], "class": "RT", "days": [], "names": [p, pl],
                   "text": f"Sam has {acts[i]} with {p} at {pl}."})
    for i, it in enumerate(ch):
        it["id"] = f"c{i}"
    for i, it in enumerate(rt):
        it["id"] = f"r{i}"
    items += ch + rt
    # --- days: balance the load per day (greedy least-loaded days, noisy), constrained items first
    load = {d: 0 for d in range(1, n_days + 1)}

    def pick(pool, k, noise):
        ds = sorted(pool, key=lambda d: load[d] + noise * rng.random())[:k]
        for d in ds:
            load[d] += 1
        return sorted(ds)
    split = max(1, round(n_days * 3 / 7))  # 7 -> days 1-3 old, 4-7 new
    olds, news = range(1, split + 1), range(split + 1, n_days + 1)
    for it in ch:
        it["old_days"], it["new_days"] = pick(olds, min(2, len(olds)), 1.5), pick(news, min(2, len(news)), 1.5)
        it["days"] = it["old_days"] + it["new_days"]
    k_rt = [min(n_days, 3 if i < n_rt // 2 else 4) for i in range(n_rt)]
    rest = [(it, CLASS_DAYS[it["class"]]) for it in items if it["kind"] == "fact"] + [(it, k) for it, k in zip(rt, k_rt)]
    rng.shuffle(rest)
    rest.sort(key=lambda x: -x[1])  # big recurrences first, singletons last so they even out the load
    for it, k in rest:
        it["days"] = pick(range(1, n_days + 1), k, 1.5 if k > 1 else 0.3)
    # --- sessions: deal each day's mentions into sessions; items that share a name never share a session
    sched = []
    for d in range(1, n_days + 1):
        ms = []
        for it in items:
            if d in it["days"]:
                ph = None if it["kind"] != "changing" else ("old" if d in it["old_days"] else "new")
                ms.append({"item": it["id"], "phase": ph, "names": [it["a"], it["old_b"] if ph == "old" else it["b"]]})
        for _ in range(500):
            rng.shuffle(ms)
            ss, ok = [[] for _ in range(sessions)], True
            for m in ms:
                cand = [s for s in ss if not any(set(m["names"]) & set(x["names"]) for x in s)]
                if not cand:
                    ok = False
                    break
                min(cand, key=lambda s: (len(s), rng.random())).append(m)
            if ok:
                break
        else:
            raise RuntimeError("could not deal sessions")
        for s, sm in enumerate(ss, 1):
            for m in sm:
                m["style"] = rng.choice(STYLES)
                if m["item"][0] == "r":
                    m["when"] = rng.choice(WHEN)
            sched.append({"day": d, "session": s, "fillers": rng.randint(1, 3), "topics": rng.sample(TOPICS, 3), "mentions": sm})
    plan = {"seed": seed, "user": "Sam", "n_days": n_days, "sessions": sessions, "items": items, "schedule": sched, "tests": make_tests(items)}
    plan["test_strings_norm"] = sorted({norm(t["q"]) for v in plan["tests"].values() for t in v})
    check_plan(plan, per_rel, n_ch, n_rt, s1_names)
    return plan


def scaled(scale):
    """build_plan sizes for --scale (1: Week-1, the defaults). C2 and C4 facts x scale; C1 facts and changing facts grow by a third of that growth,
    routines by 0.45 of it, so 2.5 gives the Week-2 counts (C2 = C4 = 100, C1 64 since 6 relations need whole counts, changing 30, routines 20).
    Sessions per day grow with the mention load (C1 1 day, C2 2, C4 4, changing 4, routines 3.5 on average), which keeps Week-1's ~9.6 mentions a session."""
    if scale == 1:
        return {}
    rec, c1 = round(40 * scale), round(40 * (1 + (scale - 1) / 3))
    per_rel = -(-(2 * rec + c1) // 6)
    c1 = 6 * per_rel - 2 * rec
    n_ch, n_rt = 2 * round(10 * (1 + (scale - 1) / 3)), 2 * round(6 * (1 + (scale - 1) * 0.45))
    load = c1 + 2 * rec + 4 * rec + 4 * n_ch + 3.5 * n_rt
    return {"per_rel": per_rel, "n_ch": n_ch, "n_rt": n_rt, "mix": {"C1": c1, "C2": rec, "C4": rec}, "sessions": max(6, round(6 * load / 402))}


def make_tests(items):
    """Fixed templates (facts.py wording). Never shown to Claude."""
    facts = [i for i in items if i["kind"] == "fact"]
    by = {(f["rel"], f["a"]): f for f in facts}
    t = {"forward": [], "reverse": [], "twohop": [], "changed": [], "routine": []}
    for f in facts:
        n = int(f["id"][1:])
        _, fq, rq = REL[f["rel"]]
        t["forward"].append({"q": fq[n % len(fq)].format(a=f["a"], b=f["b"]), "target": f["b"], "item": f["id"], "class": f["class"], "rel": f["rel"]})
        t["reverse"].append({"q": rq[(n // 2) % len(rq)].format(a=f["a"], b=f["b"]), "target": f["a"], "item": f["id"], "class": f["class"], "rel": f["rel"]})
    for kind, r1, r2, xs, js in CHAINS:
        i = 0
        for f in sorted((f for f in facts if f["rel"] == r1), key=lambda f: int(f["id"][1:])):
            g = by[(r2, f[js])]
            if f["class"] in ("C2", "C4") and g["class"] in ("C2", "C4"):
                t["twohop"].append({"q": HOP[kind][i % 2].format(x=f[xs]), "target": g["b"], "items": [f["id"], g["id"]], "hop": kind,
                                    "classes": [f["class"], g["class"]]})
                i += 1
    for c in (i for i in items if i["kind"] == "changing"):
        verb = "live" if c["rel"] == "lives_in" else "work"
        t["changed"].append({"q": f"Where does {c['a']} {verb} now?", "target": c["b"], "old": c["old_b"], "item": c["id"], "rel": c["rel"]})
    for r in (i for i in items if i["kind"] == "routine"):
        t["routine"].append({"q": f"Where does Sam usually have {r['activity']} with {r['a']}?", "target": r["b"], "item": r["id"], "activity": r["activity"]})
    return t


def names_of(plan):
    return sorted({n.lower() for it in plan["items"] for n in it["names"]})


def check_plan(plan, per_rel, n_ch, n_rt, sleep1_names):
    items, nd = plan["items"], plan["n_days"]
    new_names = sorted({n.lower() for it in items for n in it["names"]})  # chain partners legitimately share the person name
    assert len(new_names) == 9 * per_rel + 3 * n_ch + 2 * n_rt, "name count (duplicate entity names?)"
    for n in new_names:
        assert 6 <= len(n) <= 9, n
        assert not any(n in m for m in new_names if m != n), f"substring clash within week names: {n}"
        assert not any(n in s or s in n for s in sleep1_names), f"clash with a Sleep-1 name: {n}"
    assert len({it["id"] for it in items}) == len(items) == 6 * per_rel + n_ch + n_rt
    for it in items:
        assert len(it["days"]) == len(set(it["days"])) and all(1 <= d <= nd for d in it["days"]), it["id"]
        if it["kind"] == "fact":
            assert len(it["days"]) == CLASS_DAYS[it["class"]]
        if it["kind"] == "changing":
            assert max(it["old_days"]) < min(it["new_days"])
    per = {(m["item"], sc["day"]) for sc in plan["schedule"] for m in sc["mentions"]}
    assert per == {(it["id"], d) for it in items for d in it["days"]}, "schedule != item days"
    for sc in plan["schedule"]:  # no two mentions of one session share a name
        ns = [n for m in sc["mentions"] for n in m["names"]]
        assert len(ns) == len(set(ns)), (sc["day"], sc["session"])
    for k, v in plan["tests"].items():
        for t in v:
            assert t["target"].lower() not in t["q"].lower(), f"target leaked in question: {t['q']}"
    assert len(plan["test_strings_norm"]) == sum(len(v) for v in plan["tests"].values()), "duplicate test strings"
    assert all("usually" in t["q"] for t in plan["tests"]["routine"])


# ----------------------------------------------------------------------------------------------- prompt, API, validation
def session_prompt(plan, sc, probs=(), rescue=0):  # rescue 1: the stronger reminder; 2 (attempts beyond the default rescues): plus a turn-count check
    by = {it["id"]: it for it in plan["items"]}
    k, f = len(sc["mentions"]), sc["fillers"]
    lines = []
    for i, m in enumerate(sc["mentions"], 1):
        it = by[m["item"]]
        if it["kind"] == "routine":
            what = (f'ONE EPISODE: "Sam is having {it["activity"]} with {it["a"]} at {it["b"]} {m["when"]}." Describe this single occasion (planning it, '
                    'heading there, running late, just back from it). It must sound like a one-off, never a habit: do not use "usually", "always", '
                    '"every", "each", "again", "regular", "as usual" or anything like them.')
        elif it["kind"] == "changing" and m["phase"] == "new":
            ex = '"finally moved to...", "just relocated to...", "now lives in..."' if it["rel"] == "lives_in" else '"just started a new job at...", "switched over to...", "now works at..."'
            what = (f'RECENT CHANGE: "{it["text"]}" This is NEW information, it has just changed. Make that clear (e.g. {ex}). '
                    f'Do not say where {it["a"]} lived or worked before.')
        elif it["kind"] == "changing":
            what = f'FACT: "{it["old_text"]}" (state it as an ordinary, current detail)'
        else:
            what = f'FACT: "{it["text"]}"'
        lines.append(f'{i}. {what}\n   Names that must appear in that user turn, spelled exactly like this: {m["names"][0]} and {m["names"][1]}. '
                     f'How it comes up: {m["style"]}.')
    p = f"""You are writing one realistic chat session between "Sam" (an ordinary adult) and an AI assistant, as dataset material. It is day {sc["day"]} of Sam's week ({WEEKDAY[(sc["day"] - 1) % 7]}); this is session {sc["session"]} of {plan["sessions"]} that day, so Sam can say "today", "tonight", "yesterday" and so on.

Sam asks the assistant for help with ordinary things. Drift naturally through two or three small tasks, for example: {", ".join(sc["topics"])}. Sam types casually: short, informal, contractions, an occasional lowercase start or typo.

Inside this session, exactly {k} facts about people in Sam's life come up IN PASSING. Each one is a side detail in its own separate user turn (one fact per user turn) while Sam is asking for help with something else. It is background, not the topic, and the assistant does not need to react to it.

{chr(10).join(lines)}

Rules for the {k} fact turns:
- Each fact turn contains BOTH of its names, exactly as spelled (they are invented words; never respell, shorten or change them). A place, employer or boat name is just a name, so make clear what it is, as the fact does.
- Paraphrase freely and conversationally, in your own words. Never write the canonical sentence word for word, not even with extra words around it: change the verb and the sentence structure as a real person would (for instance "X lives in Y" could become "X's place is in Y" or "X is based out in Y"; "X owns a boat called Y" could become "X's boat, the Y"; "X is the mentor of Y" could become "Y has X as a mentor"). Use a different structure in every turn.
- Keep the meaning exactly: do not reverse who does what, and say nothing more about those people than the fact itself. Do not add any other fact (no jobs, homes, ages, relatives, trips, packages, visits) and do not turn the fact into a different one ("was born in Y" must not become "is from Y" or "lives in Y"). At most give a generic role such as "my neighbor" or "a friend".
- Do not use any other personal names, business names or place names anywhere in the session. A fact turn names only its own two names.
- Put the fact turns in any order that flows.
Besides those, add exactly {f} filler user turn{"s" if f > 1 else ""}: ordinary requests with no names at all. Every user turn is either a fact turn or a filler turn.

Assistant turns: short, friendly, helpful, plain text, at most 35 words. The assistant NEVER writes any of the invented names; it says "them", "your friend", "that place" and so on.

Output ONLY a JSON array of objects {{"role": "user" or "assistant", "text": "..."}}. It starts with a user turn, roles alternate, and it ends with an assistant turn, {2 * (k + f)} turns in total. No markdown fences, no commentary."""
    if probs:
        p += "\n\nYour previous attempt was rejected for these reasons, so avoid them this time:\n- " + "\n- ".join(list(probs)[:6])
    if rescue:
        p += (f"\n\nIMPORTANT: this session has been rejected several times. Count carefully: {k} user turns that each hold exactly ONE of the facts above "
              f"(never two facts in one turn, never a fact split over two turns, never a fact turn that is also a filler request), plus {f} separate "
              "filler turns with no names. Do not reuse the same topic for two fact turns, so each fact stays in its own turn.")
    if rescue > 1:
        p += (f"\n\nFinal check before you answer: the array must hold exactly {2 * (k + f)} objects, that is {k + f} user turns in all. If your draft has more user "
              f"turns, delete the extra no-name requests (every user turn is a fact turn or one of the {f} filler turns), and make sure each of the {k} fact turns "
              "still contains both of its names.")
    return p


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    def __init__(self, cap=CAP, raw=RAW):
        self.lock, self.cap, self.cons, self.listed, self.tin, self.tout = threading.Lock(), cap, 0.0, 0.0, 0, 0
        for p in raw.glob("*.json"):
            self.add(json.loads(p.read_text())["usage"])

    def add(self, u):
        with self.lock:
            i, o = u["input_tokens"], u["output_tokens"]
            self.tin, self.tout = self.tin + i, self.tout + o
            self.cons += (i * CAP_PRICE[0] + o * CAP_PRICE[1]) / 1e6
            self.listed += (i * PRICE[0] + o * PRICE[1]) / 1e6

    def ok(self, inflight=4):
        return self.cons + inflight * 0.06 <= self.cap


BATCH = {"on": False}  # --batch: every API call goes through the Message Batches API, one batch per round of attempts


class Deferred(Exception):
    def __init__(self, path, prompt, meta):
        super().__init__(path.name)
        self.path, self.prompt, self.meta = path, prompt, meta


def _api(method, url, key, body=None):
    hdr = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for n in range(7):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=hdr, method=method)
            with urllib.request.urlopen(req, timeout=240) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504, 529) or n == 6:
                raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if n == 6:
                raise
        time.sleep(min(60, 2 ** (n + 1)) + random.random())


def batch_round(pend, key, bud, max_tokens=6000, poll=30):
    """Send the deferred requests as one Message Batch, wait for it, and write each answer to its raw cache file (same record as the live path)."""
    reqs = [{"custom_id": f"r{i}", "params": {"model": MODEL, "max_tokens": max_tokens, "thinking": {"type": "between_tools"},
                                              "messages": [{"role": "user", "content": d.prompt}]}} for i, d in enumerate(pend)]
    b = json.loads(_api("POST", URL + "/batches", key, {"requests": reqs}))
    print(f"[batch] {b['id']}: {len(reqs)} requests", flush=True)
    while b["processing_status"] != "ended":
        time.sleep(poll)
        b = json.loads(_api("GET", f"{URL}/batches/{b['id']}", key))
    got = 0
    for line in _api("GET", b["results_url"], key).decode().splitlines():
        r = json.loads(line)
        d = pend[int(r["custom_id"][1:])]
        if r["result"]["type"] != "succeeded":
            print(f"[batch] {d.path.name}: {r['result']['type']}", flush=True)
            continue
        resp = r["result"]["message"]
        rec = {**d.meta, "model": resp.get("model"), "id": resp.get("id"), "stop_reason": resp.get("stop_reason"), "batch": b["id"],
               "usage": {k: resp["usage"][k] for k in ("input_tokens", "output_tokens")},
               "text": "".join(x.get("text", "") for x in resp["content"] if x.get("type") == "text"), "prompt": d.prompt}
        tmp = d.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
        tmp.rename(d.path)
        bud.add(rec["usage"])
        got += 1
    print(f"[batch] {b['id']} done: {got}/{len(reqs)} written, est spend ${bud.listed:.3f} (cap-basis ${bud.cons:.3f}; batch price is half)", flush=True)


def call_api(prompt, key, max_tokens=6000, tries=7):
    body = json.dumps({"model": MODEL, "max_tokens": max_tokens, "thinking": {"type": "between_tools"},
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    hdr = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL, data=body, headers=hdr, method="POST"), timeout=240) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:300]
            if e.code not in (429, 500, 502, 503, 504, 529) or n == tries - 1:
                raise RuntimeError(f"HTTP {e.code}: {msg}")
            wait = float(e.headers.get("retry-after") or 0) or min(60, 2 ** (n + 1))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if n == tries - 1:
                raise
            wait = min(60, 2 ** (n + 1))
        time.sleep(wait + random.random())


def parse_chat(txt):
    t = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", txt.strip())
    i, j = t.find("["), t.rfind("]")
    arr = json.loads(t[i:j + 1])
    assert isinstance(arr, list) and all(isinstance(x, dict) and x.get("role") in ("user", "assistant") and isinstance(x.get("text"), str) for x in arr)
    return [{"role": x["role"], "text": x["text"].strip()} for x in arr]


def check_session(turns, sc, plan):
    """-> (per-turn list of item ids mentioned, problems). A user turn is a fact turn (exactly one planned mention) or a filler (no names)."""
    probs, men = [], []
    ms, allnames = sc["mentions"], names_of(plan)
    if not turns or [t["role"] for t in turns] != ["user", "assistant"] * (len(turns) // 2) or len(turns) % 2:
        return [], ["roles must alternate starting with user and end with assistant"]
    count = {m["item"]: 0 for m in ms}
    fill = 0
    for i, t in enumerate(turns):
        low = t["text"].lower()
        found = {n for n in allnames if n in low}
        if not t["text"]:
            probs.append(f"turn {i} is empty")
        if t["role"] == "assistant":
            men.append([])
            if found:
                probs.append(f"assistant turn {i} contains invented name(s) {sorted(found)}")
            if len(t["text"].split()) > 50:
                probs.append(f"assistant turn {i} is {len(t['text'].split())} words (max 50)")
        else:
            hit = [m for m in ms if all(n.lower() in found for n in m["names"])]
            extra = found - {n.lower() for m in hit for n in m["names"]}
            if extra:
                probs.append(f"user turn {i} contains names that are not part of its fact: {sorted(extra)}")
            if len(hit) > 1:
                probs.append(f"user turn {i} mentions more than one fact")
            if not hit and not found:
                fill += 1
            for m in hit:
                count[m["item"]] += 1
                if m["item"][0] == "r" and HABIT.search(t["text"]):
                    probs.append(f"routine turn {i} sounds like a habit ({HABIT.search(t['text']).group(0)!r})")
                if m["phase"] == "new" and not CHANGE.search(t["text"]):
                    probs.append(f"turn {i} does not make clear that the new value is a recent change")
            men.append([m["item"] for m in hit])
        for q in plan["test_strings_norm"]:
            if q in norm(t["text"]):
                probs.append(f"turn {i} contains test question {q!r}")
    probs += [f"fact {k} has {c} user turns containing both names (need exactly 1)" for k, c in count.items() if c != 1]
    if not 1 <= fill <= 3:
        probs.append(f"{fill} filler user turns (need 1 to 3)")
    return men, probs


def gen_session(plan, sc, key, bud, raw=RAW, rescue=RESCUE):
    """Up to 1+RETRIES+RESCUE attempts (--rescue: more, but only while no attempt has passed check_session). An attempt must pass check_session; strict_check (change-cue wording) is advisory: if no attempt
    passes both, the first attempt that passed check_session is used and its strict_check complaints are returned as warnings."""
    probs, tag, fb = [], f"d{sc['day']}s{sc['session']}", None
    for att in range(1 + RETRIES + rescue):
        if att > RETRIES + RESCUE and fb:  # attempts beyond the default only for a session that has no accepted attempt yet
            break
        prompt = session_prompt(plan, sc, probs, rescue=(att > RETRIES) + (att > RETRIES + RESCUE))
        path = raw / f"{tag}_a{att}_{hashlib.sha1(prompt.encode()).hexdigest()[:8]}.json"
        if path.exists():
            rec = json.loads(path.read_text())
        else:
            if not bud.ok():
                if fb:
                    break
                raise BudgetExceeded(f"estimated spend ${bud.cons:.2f} near the ${bud.cap} cap")
            if BATCH["on"]:  # --batch: queue the request for the next Message Batch round instead of calling now
                raise Deferred(path, prompt, {"day": sc["day"], "session": sc["session"], "attempt": att})
            resp = call_api(prompt, key)
            rec = {"day": sc["day"], "session": sc["session"], "attempt": att, "model": resp.get("model"), "id": resp.get("id"),
                   "stop_reason": resp.get("stop_reason"), "usage": {k: resp["usage"][k] for k in ("input_tokens", "output_tokens")},
                   "text": "".join(b.get("text", "") for b in resp["content"] if b.get("type") == "text"), "prompt": prompt}
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
            tmp.rename(path)
            bud.add(rec["usage"])
        warn = []
        try:
            if rec["stop_reason"] not in ("end_turn", "stop_sequence"):
                raise ValueError(f"stop_reason {rec['stop_reason']}")
            turns = parse_chat(rec["text"])
            men, probs = check_session(turns, sc, plan)
            if not probs:
                warn = strict_check(turns, men, plan)
        except (ValueError, AssertionError, KeyError) as e:  # JSONDecodeError is a ValueError
            turns, men, probs = [], [], [f"output was not a valid chat JSON array ({type(e).__name__}: {str(e)[:80]})"]
        if not probs and not warn:
            return {"turns": turns, "mentions": men, "attempts": att + 1, "problems": [], "warnings": []}
        if not probs and fb is None:
            fb = {"turns": turns, "mentions": men, "attempts": att + 1, "problems": [], "warnings": warn}
        probs = probs or warn
    return fb or {"turns": turns, "mentions": men, "attempts": 1 + RETRIES + rescue, "problems": probs, "warnings": []}


def strict_check(turns, men, plan):
    """Extra audit applied only to an attempt that passed check_session (keeps cached retry prompts valid)."""
    by = {it["id"]: it for it in plan["items"]}
    probs = []
    for i, (t, ids) in enumerate(zip(turns, men)):
        for j in ids:
            if by[j]["kind"] != "changing":
                continue
            new = by[j]["b"].lower() in t["text"].lower()
            if new and not STRONG.search(t["text"]):
                probs.append(f"turn {i}: the new value must be clearly a recent change (e.g. 'finally moved to', 'just started a new job at', 'switched to')")
            if not new and STRONG_OLD.search(t["text"]):
                probs.append(f"turn {i}: the old value must be stated as an ordinary, current detail, with no hint of a recent move, switch or new start")
    return probs


def diary_rows(sc, res):
    return [{"day": sc["day"], "session": sc["session"], "turn": i, "role": t["role"], "text": t["text"], "mentions": res["mentions"][i]}
            for i, t in enumerate(res["turns"])]


def finish(plan, results, spend, extra=None):
    """Assemble + final checks. results: {(day, session): {"turns","mentions"}}"""
    diary = [r for sc in plan["schedule"] for r in diary_rows(sc, results[(sc["day"], sc["session"])])]
    seen = {}
    for r in diary:
        for i in r["mentions"]:
            seen.setdefault(i, set()).add(r["day"])
    for it in plan["items"]:
        assert seen.get(it["id"], set()) == set(it["days"]), f"{it['id']}: diary days {sorted(seen.get(it['id'], []))} != plan {it['days']}"
    for r in diary:
        for q in plan["test_strings_norm"]:
            assert q not in norm(r["text"]), f"test string in diary: {q}"
    out = {"seed": plan["seed"], "user": "Sam", "items": plan["items"], "diary": diary, "tests": plan["tests"],
           "test_strings_norm": plan["test_strings_norm"], "spend_usd": round(spend, 4)}
    out.update(extra or {})
    return out


# ----------------------------------------------------------------------------------------------- offline template week
def template_week(seed=1, n_days=2):
    """Tiny offline week, same schema as week1.json (templates, no network): 12 facts (3 chains with C2 pairs), 2 changing, 2 routines."""
    plan = build_plan(seed, n_days=n_days, per_rel=2, n_ch=2, n_rt=2, sessions=2, classes=("C1", "C2", "C4") if n_days >= 4 else ("C1", "C2"), tie=True)
    by = {it["id"]: it for it in plan["items"]}
    pre = ["By the way, ", "Oh, and ", "Quick note: ", "", "Random thing: "]
    asst = ["Sure, noted. What else can I help with?", "Got it. Anything else?", "Okay, happy to help with that.", "Sounds good, go on."]
    res = {}
    for sc in plan["schedule"]:
        rng = random.Random(seed * 1000 + sc["day"] * 10 + sc["session"])
        us = []
        for m in sc["mentions"]:
            it = by[m["item"]]
            if it["kind"] == "routine":
                s = f"I'm having {it['activity']} with {it['a']} at {it['b']} tonight."
            elif it["kind"] == "changing" and m["phase"] == "new":
                s = f"{it['a']} just moved to {it['b']}." if it["rel"] == "lives_in" else f"{it['a']} just started a new job at {it['b']}."
            elif it["kind"] == "changing":
                s = it["old_text"]
            else:
                s = it["text"]
            us.append(rng.choice(pre) + s)
        us += rng.sample(FILLERS, sc["fillers"])
        rng.shuffle(us)
        turns = [x for u in us for x in ({"role": "user", "text": u}, {"role": "assistant", "text": rng.choice(asst)})]
        men, probs = check_session(turns, sc, plan)
        assert not probs, probs
        res[(sc["day"], sc["session"])] = {"turns": turns, "mentions": men}
    return finish(plan, res, 0.0, {"template": True})


# ----------------------------------------------------------------------------------------------- CLI
def summary(plan):
    its = plan["items"]
    from collections import Counter
    print("items:", len(its), dict(Counter(i["kind"] for i in its)), "classes:", dict(sorted(Counter(i["class"] for i in its).items())))
    print("fact class by relation:", {r: dict(sorted(Counter(i["class"] for i in its if i["rel"] == r and i["kind"] == "fact").items())) for r in REL})
    print("changing by relation:", dict(Counter(i["rel"] for i in its if i["kind"] == "changing")),
          "| routine days:", dict(Counter(len(i["days"]) for i in its if i["kind"] == "routine")))
    per_day = Counter(sc["day"] for sc in plan["schedule"] for _ in sc["mentions"])
    print("mentions total", sum(per_day.values()), "per day", [per_day[d] for d in sorted(per_day)])
    sizes = [len(sc["mentions"]) for sc in plan["schedule"]]
    print("sessions", len(sizes), "mentions/session min/mean/max", min(sizes), round(sum(sizes) / len(sizes), 1), max(sizes),
          "| fillers", dict(Counter(sc["fillers"] for sc in plan["schedule"])))
    kinds = Counter(m["item"][0] for sc in plan["schedule"] for m in sc["mentions"])
    print("distinct names:", len(names_of(plan)), "| tests:", {k: len(v) for k, v in plan["tests"].items()}, "| unique test strings:", len(plan["test_strings_norm"]))
    th = plan["tests"]["twohop"]
    print("two-hop by chain:", dict(Counter(t["hop"] for t in th)), "| session kind mix (f/c/r mentions):", dict(kinds))
    for k in ("fact", "changing", "routine"):
        for i in [x for x in its if x["kind"] == k][:2]:
            print("  item", {a: i[a] for a in ("id", "kind", "rel", "a", "b", "old_b", "activity", "class", "days") if a in i}, "|", i["text"])
    for k, v in plan["tests"].items():
        for t in v[:2]:
            print(f"  test {k}:", t["q"], "->", t["target"])


def parse_ds(s):
    d, ss = s.split(":")
    return int(d), int(ss)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--scale", type=float, default=1.0, help="world size, 1 = Week-1; 2.5 = Week-2 (see scaled())")
    ap.add_argument("--out", default=str(DATA / "week1.json"), help="output file (its .sha256 goes next to it); the raw cache is data/raw/ for week1.json, else raw_<name>/ beside it")
    ap.add_argument("--cap", type=float, default=CAP, help="dollar cap on the estimated spend (conservative $3/$15 per M tokens)")
    ap.add_argument("--rescue", type=int, default=RESCUE, help="rescue attempts per session after the regenerations; beyond the default 3 only for a session with no accepted attempt (cached attempts are reused)")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--prompt", metavar="D:S", help="print the prompt of one session")
    ap.add_argument("--only", metavar="D:S", help="write one session as a trial (cached) and print it")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--batch", action="store_true", help="send every call through the Message Batches API (rounds of attempts); then build the week from the cache")
    a = ap.parse_args()
    plan = build_plan(a.seed, **scaled(a.scale))
    assert json.dumps(plan, sort_keys=True) == json.dumps(build_plan(a.seed, **scaled(a.scale)), sort_keys=True), "plan is not deterministic"
    if a.plan_only or not (a.prompt or a.only or a.write):
        summary(plan)
        sc = plan["schedule"][0]
        print("\nexample session plan (day 1, session 1):", json.dumps(sc)[:900])
        return
    if a.prompt:
        d, s = parse_ds(a.prompt)
        print(session_prompt(plan, next(x for x in plan["schedule"] if (x["day"], x["session"]) == (d, s))))
        return
    key = os.environ["LEARNER_ANTHROPIC_API_KEY"]
    outp = Path(a.out).resolve()
    if outp == DATA / "week1.json" and (a.seed, a.scale) != (1, 1.0):
        ap.error("--seed / --scale other than Week-1's need their own --out (week1.json is sealed)")
    raw = RAW if outp == DATA / "week1.json" else outp.parent / f"raw_{outp.stem}"
    raw.mkdir(parents=True, exist_ok=True)
    bud = Budget(a.cap, raw)
    todo = [sc for sc in plan["schedule"] if not a.only or (sc["day"], sc["session"]) == parse_ds(a.only)]
    if a.batch:  # rounds: run every session against the cache; collect the requests it still needs; send them as one batch; repeat
        BATCH["on"] = True
        for rnd in range(1 + RETRIES + max(a.rescue, RESCUE) + 1):
            pend = []
            for sc in todo:
                try:
                    gen_session(plan, sc, key, bud, raw, a.rescue)
                except Deferred as d:
                    pend.append(d)
            if not pend:
                break
            if not bud.ok(inflight=len(pend) / 2):
                sys.exit(f"[batch] round {rnd}: {len(pend)} requests would pass the ${bud.cap} cap (cap-basis ${bud.cons:.2f})")
            print(f"[batch] round {rnd}: {len(pend)} sessions need a call", flush=True)
            batch_round(pend, key, bud)
        BATCH["on"] = False  # everything is cached now; the normal pass below makes no calls
    res, fails = {}, []
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(gen_session, plan, sc, key, bud, raw, a.rescue): sc for sc in todo}
        for fu in as_completed(futs):
            sc = futs[fu]
            try:
                r = fu.result()
            except BudgetExceeded as e:
                fails.append(((sc["day"], sc["session"]), [str(e)]))
                continue
            res[(sc["day"], sc["session"])] = r
            if r["problems"]:
                fails.append(((sc["day"], sc["session"]), r["problems"]))
            print(f"d{sc['day']}s{sc['session']} {'OK' if not r['problems'] else 'FAIL'} attempts={r['attempts']} est_spend=${bud.listed:.3f} (cap-basis ${bud.cons:.3f})", flush=True)
    if a.only:
        sc = todo[0]
        r = res.get((sc["day"], sc["session"]))
        for i, t in enumerate(r["turns"]):
            print(f"[{i}] {t['role']:9} {r['mentions'][i]} {t['text']}")
        print("problems:", r["problems"])
        return
    if fails:
        print("\nFAILED sessions:", fails)
        sys.exit(2)
    out = finish(plan, res, bud.listed, {"model": MODEL, "tokens": {"input": bud.tin, "output": bud.tout}, "spend_usd_conservative_3_15": round(bud.cons, 4),
                                           "attempts": {f"d{d}s{s}": r["attempts"] for (d, s), r in sorted(res.items())},
                                           "warnings": {f"d{d}s{s}": r["warnings"] for (d, s), r in sorted(res.items()) if r["warnings"]},
                                           **({"scale": a.scale, "sessions_per_day": plan["sessions"]} if a.scale != 1 else {})})
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    (outp.parent / f"{outp.name}.sha256").write_text(hashlib.sha256(outp.read_bytes()).hexdigest() + f"  {outp.name}\n")
    print("wrote", outp, "diary turns", len(out["diary"]), "spend", out["spend_usd"])


if __name__ == "__main__":
    main()
