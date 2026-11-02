"""Items for Recall-then-read stage 1, built from the Week-2 world (fact table + diary).

Pipeline (nothing here calls the API unless you pass --submit / --collect):
  python -m sleep2.recallread.items plan                  # chains, W/dev choice, one-hop, never-taught, template questions (no API)
  python -m sleep2.recallread.items requests --dry-run    # request counts + cost estimate for the phrasing batch
  python -m sleep2.recallread.items requests --submit [--limit 5]   # Lead only: needs LEARNER_ANTHROPIC_API_KEY
  python -m sleep2.recallread.items collect               # fetch the batch, write phrasing_raw.json
  python -m sleep2.recallread.items freeze [--no-claude]  # validate, write items.json + items.sha256 (+ week2.json copy) in data/recallread/

Two-hop chains come straight from the fact table (no model): mentor_of -> lives_in, owns -> born_in, sibling -> works_at. Each is
'cross-day': no user turn contains both the start name and the answer, and the two hops share no turn. Claude only WORDS the questions.
Eval rows (splits): twohop_nat (natural wording, full diary), twohop_gap (lexically-gapped wording, full diary), W_nat (the W subset,
natural wording, post-deletion diary), onehop, never (never-taught), twohop_tmpl (the world's own template wording, reported only).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from . import batchlib
from .make_condition_w import check_deletion, deleted_turns
from .world import FROZEN, STOP, WEEK2_SHA, find_week2, has_word, load_world, mentions_name, norm, sha256_file, user_turns, words

SEED = 20261026
N_W, N_DEV, N_ONEHOP, N_NEVER = 75, 30, 200, 50
RARE_DF = 40  # a token is 'rare' if it occurs in at most this many of the user turns
PHRASE_MODEL = "claude-sonnet-5-5"
CHAIN_TYPES = {
    ("mentor_of", "lives_in"): ("mentor_lives", "Where does the mentor of {s} live?", "the mentor of {s}", "where that person lives"),
    ("owns", "born_in"): ("owner_born", "Where was the owner of {s} born?", "the owner of the boat called {s}", "where that owner was born"),
    ("sibling", "works_at"): ("sibling_works", "Where does {s}'s sibling work?", "the sibling of {s}", "where that sibling works"),
}
NEVER_Q = {"born_in": "Where was {n} born?", "works_at": "Where does {n} work?", "lives_in": "Where does {n} live?",
           "mentor_of": "Who is the mentor of {n}?", "owns": "What boat does {n} own?"}


def mention_turns(turns):
    m = defaultdict(list)
    for t in turns:
        for x in t["mentions"]:
            m[x].append(t["turn_id"])
    return m


def build_chains(world, turns):
    facts = [x for x in world["items"] if x["kind"] == "fact"]
    by = defaultdict(list)
    for f in facts:
        by[(f["rel"], f["a"])].append(f)
    men = mention_turns(turns)
    cands = []
    for X in facts:
        if X["rel"] == "sibling":
            pairs = [(X["a"], X["b"]), (X["b"], X["a"])]  # (bridge, start)
        elif X["rel"] in ("mentor_of", "owns"):
            pairs = [(X["a"], X["b"])]
        else:
            continue
        for bridge, start in pairs:
            for (r1, r2), (kind, tq, _, _) in CHAIN_TYPES.items():
                if r1 != X["rel"]:
                    continue
                for Y in by.get((r2, bridge), []):
                    cands.append(dict(kind=kind, X=X["id"], Y=Y["id"], start=start, bridge=bridge, answer=Y["b"], rel1=r1, rel2=r2,
                                      fact1=X["text"], fact2=Y["text"], classes=[X["class"], Y["class"]],
                                      hop1_turns=sorted(men[X["id"]]), hop2_turns=sorted(men[Y["id"]]), template_q=tq.format(s=start)))
    chains, dropped, starts = [], [], set()
    for c in cands:
        probs = check_chain(c, turns)
        if c["start"] in starts:
            probs.append("start name already used by another chain")
        if probs:
            dropped.append({"X": c["X"], "Y": c["Y"], "problems": probs})
            continue
        starts.add(c["start"])
        chains.append(c)
    chains.sort(key=lambda c: (c["kind"], c["X"], c["Y"]))
    for i, c in enumerate(chains):
        c["id"] = f"th{i:03d}"
    return chains, dropped


def check_chain(c, turns) -> list[str]:
    """The grep check: no single user turn holds both hops. Returns problems (empty = ok)."""
    p = []
    if not c["hop1_turns"] or not c["hop2_turns"]:
        p.append("a hop has no tagged turn")
    if set(c["hop1_turns"]) & set(c["hop2_turns"]):
        p.append("a turn is tagged with both facts")
    for t in turns:
        if mentions_name(t, c["start"]) and mentions_name(t, c["answer"]):
            p.append(f"turn {t['turn_id']} holds start and answer")
            break
    byid = {t["turn_id"]: t for t in turns}
    for h in c["hop2_turns"]:
        if mentions_name(byid[h], c["start"]):
            p.append(f"hop-2 turn {h} names the start")
            break
    return p


def choose_w(chains, turns, rng, n=N_W):
    """Greedy seeded pick of up to n chains whose joint deletion keeps every picked chain's hop-2 turn and leaves no start-bridge link."""
    order = chains[:]
    rng.shuffle(order)
    pick = []
    for c in order:
        if len(pick) == n:
            break
        if not check_deletion(turns, pick + [c], deleted_turns(turns, pick + [c])):
            pick.append(c)
    return sorted(c["id"] for c in pick)


def pick_onehop(world, turns, rng, n=N_ONEHOP):
    men = mention_turns(turns)
    byid = {x["id"]: x for x in world["items"]}
    fw = [t for t in world["tests"]["forward"] if men.get(t["item"])]
    rng.shuffle(fw)
    return [dict(id=f"oh{i:03d}", q=t["q"], gold=t["target"], item=t["item"], cls=t["class"], rel=t["rel"], name=byid[t["item"]]["a"], gold_turns=sorted(men[t["item"]]))
            for i, t in enumerate(sorted(fw[:n], key=lambda t: t["item"]))]


def make_never(world, turns, rng, n=N_NEVER):
    names = sorted({x for it in world["items"] if it["kind"] == "fact" for x in it["names"]})
    corpus = norm(" ".join(t["text"] for t in world["diary"]) + " " + " ".join(world.get("test_strings_norm", [])))
    used, out = set(), []
    stems = [(re.match(r"^[^aeiou]*[aeiou]+[^aeiou]*", x.lower()) or [x[:3]])[0] for x in names]  # first syllable
    tails = [x[len(s):] for x, s in zip(names, stems)]
    rels = sorted(NEVER_Q)
    tries = 0
    while len(out) < n and tries < 100000:
        tries += 1
        nm = (rng.choice(stems) + rng.choice(tails)).capitalize()
        if len(nm) < 6 or norm(nm) in used or norm(nm) in corpus or nm in names:
            continue
        used.add(norm(nm))
        rel = rels[len(out) % len(rels)]
        out.append(dict(id=f"nv{len(out):03d}", name=nm, rel=rel, template_q=NEVER_Q[rel].format(n=nm), gold="unknown"))
    assert len(out) == n, "could not invent enough unseen names"
    return out


def plan(world=None):
    world = world or load_world()
    turns = user_turns(world)
    rng = random.Random(SEED)
    chains, dropped = build_chains(world, turns)
    wids = set(choose_w(chains, turns, random.Random(SEED + 1)))
    dev = set(random.Random(SEED + 2).sample([c["id"] for c in chains], min(N_DEV, len(chains))))
    for c in chains:
        c["W"], c["dev"] = c["id"] in wids, c["id"] in dev
    onehop = pick_onehop(world, turns, random.Random(SEED + 3))
    never = make_never(world, turns, random.Random(SEED + 4))
    w_items = [c for c in chains if c["W"]]
    dele = deleted_turns(turns, w_items)
    return dict(seed=SEED, week2_sha256=WEEK2_SHA, chains=chains, dropped_chains=dropped, onehop=onehop, never=never,
                w_deleted_turns=sorted(dele), w_problems=check_deletion(turns, w_items, dele),
                counts=dict(chains=len(chains), W=len(w_items), dev=len(dev), onehop=len(onehop), never=len(never), deleted_turns=len(dele),
                            chains_asked_for=150))


# ---------------------------------------------------------------- Claude phrasing requests
SYS_PHR = "You write test questions for a memory experiment. Reply with one JSON object and nothing else."


def df_table(turns):
    df = Counter()
    for t in turns:
        df.update(set(words(t["text"])))
    return df


def banned_words(c, turns_by_id, df, start):
    sw = set(words(start))
    b = set()
    for h in c["hop1_turns"] + c["hop2_turns"]:
        for w in set(words(turns_by_id[h]["text"])):
            if w not in STOP and w not in sw and df[w] <= RARE_DF:
                b.add(w)
    return sorted(b)


def chain_request(c, banned):
    _, _, desc, ask = CHAIN_TYPES[(c["rel1"], c["rel2"])]
    desc = desc.format(s=c["start"])
    u = (f"Sam keeps chats with his assistant. Two facts, said on different days, answer one question.\n"
         f"Fact A: {c['fact1']}\nFact B: {c['fact2']}\n\n"
         f"The question is about \"{c['start']}\" and asks for {ask}: its answer is \"{c['answer']}\". "
         f"The question must make the relation clear ({desc}) so it has exactly one answer.\n"
         f"Rules for every question: one sentence ending in '?'; contains the name \"{c['start']}\" exactly; does NOT contain \"{c['bridge']}\" "
         f"or \"{c['answer']}\".\n"
         f"\"natural\": the question exactly as Sam would casually type it, in his own words.\n"
         f"\"alt\": 3 different questions with the same meaning that avoid all of these words: {', '.join(banned) or '(none)'}.\n"
         f"Reply as {{\"natural\": \"...\", \"alt\": [\"...\", \"...\", \"...\"]}}")
    return u


def simple_request(q, name, answer=None):
    return (f"Rewrite this question the way Sam would casually type it to his assistant. Same meaning, one sentence ending in '?', "
            f"keep the name \"{name}\" exactly" + (f", do not include the word \"{answer}\"" if answer else "") + f".\nQuestion: {q}\n"
            f"Reply as {{\"natural\": \"...\"}}")


def phrasing_requests(P, turns):
    tb = {t["turn_id"]: t for t in turns}
    df = df_table(turns)
    reqs = []
    for c in P["chains"]:
        reqs.append(dict(custom_id=f"chain:{c['id']}", params=batchlib.params(PHRASE_MODEL, SYS_PHR, chain_request(c, banned_words(c, tb, df, c["start"])), 400)))
    for o in P["onehop"]:
        reqs.append(dict(custom_id=f"onehop:{o['id']}", params=batchlib.params(PHRASE_MODEL, SYS_PHR, simple_request(o["q"], o["name"], o["gold"]), 150)))
    for n in P["never"]:
        reqs.append(dict(custom_id=f"never:{n['id']}", params=batchlib.params(PHRASE_MODEL, SYS_PHR, simple_request(n["template_q"], n["name"]), 150)))
    return reqs


def valid_q(q, must, forbid=()):
    if not isinstance(q, str) or "\n" in q.strip() or not q.strip().endswith("?"):
        return False
    if not 4 <= len(q.split()) <= 40:
        return False
    return all(has_word(q, m) for m in must) and not any(has_word(q, f) for f in forbid)


def gap_ok(q, banned):
    return not (set(words(q)) & set(banned))


# ---------------------------------------------------------------- freeze
def build_rows(P, turns, phr=None):
    """Eval rows. phr: raw Claude output {custom_id: parsed json or None}; None -> template wording only."""
    phr = phr or {}
    tb = {t["turn_id"]: t for t in turns}
    df = df_table(turns)
    rows, stats = [], Counter()
    for c in P["chains"]:
        base = dict(item=c["id"], gold=c["answer"], start=c["start"], bridge=c["bridge"], hop1_turns=c["hop1_turns"], hop2_turns=c["hop2_turns"],
                    dev=c["dev"], kind=c["kind"])
        r = phr.get(f"chain:{c['id']}") or {}
        nat = r.get("natural") if valid_q(r.get("natural"), [c["start"]], [c["bridge"], c["answer"]]) else None
        banned = banned_words(c, tb, df, c["start"])
        gap = next((a for a in (r.get("alt") or []) if valid_q(a, [c["start"]], [c["bridge"], c["answer"]]) and gap_ok(a, banned)), None)
        stats["nat_ok" if nat else "nat_fallback_template"] += 1
        stats["gap_ok" if gap else "gap_missing"] += 1
        q_nat = nat or c["template_q"]
        rows.append(dict(base, row_id=f"{c['id']}:nat", split="twohop_nat", q=q_nat, q_source="claude" if nat else "template", index="full"))
        if gap:
            rows.append(dict(base, row_id=f"{c['id']}:gap", split="twohop_gap", q=gap, q_source="claude", index="full"))
        rows.append(dict(base, row_id=f"{c['id']}:tmpl", split="twohop_tmpl", q=c["template_q"], q_source="template", index="full"))
        if c["W"]:
            rows.append(dict(base, row_id=f"{c['id']}:W", split="W_nat", q=q_nat, q_source="claude" if nat else "template", index="W"))
    for o in P["onehop"]:
        r = phr.get(f"onehop:{o['id']}") or {}
        q = r.get("natural") if valid_q(r.get("natural"), [o["name"]], [o["gold"]]) else None
        stats["onehop_claude" if q else "onehop_template"] += 1
        rows.append(dict(row_id=o["id"], item=o["item"], split="onehop", q=q or o["q"], q_source="claude" if q else "template", gold=o["gold"],
                         hop1_turns=o["gold_turns"], hop2_turns=[], index="full", dev=False, kind=o["rel"]))
    for n in P["never"]:
        r = phr.get(f"never:{n['id']}") or {}
        q = r.get("natural") if valid_q(r.get("natural"), [n["name"]]) else None
        stats["never_claude" if q else "never_template"] += 1
        rows.append(dict(row_id=n["id"], item=n["id"], split="never", q=q or n["template_q"], q_source="claude" if q else "template", gold="unknown",
                         hop1_turns=[], hop2_turns=[], index="full", dev=False, kind=n["rel"]))
    return rows, dict(stats)


def freeze(out: Path, no_claude: bool):
    world_path = find_world_copy()
    world = load_world(world_path)
    turns = user_turns(world)
    P = plan(world)
    phr = None
    raw = out / "phrasing_raw.json"
    if not no_claude:
        if not raw.exists():
            raise SystemExit("no phrasing_raw.json: run `requests --submit` and `collect` first, or freeze --no-claude (template wording only; smoke use)")
        phr = {k: batchlib.parse_json(v) if isinstance(v, str) else v for k, v in json.loads(raw.read_text()).items()}
    rows, stats = build_rows(P, turns, phr)
    P["rows"], P["phrasing_stats"], P["claude_phrasing"] = rows, stats, not no_claude
    P["row_counts"] = dict(Counter(r["split"] for r in rows))
    P["generator"] = "sleep2/recallread/items.py"
    out.mkdir(parents=True, exist_ok=True)
    body = json.dumps(P, indent=1, sort_keys=True)
    (out / "items.json").write_text(body)
    (out / "items.sha256").write_text(hashlib.sha256(body.encode()).hexdigest() + "  items.json\n")
    wcopy = out / "week2.json"
    if not wcopy.exists() or sha256_file(wcopy) != WEEK2_SHA:
        wcopy.write_bytes(Path(world_path).read_bytes())
    (out / "week2.json.sha256").write_text(WEEK2_SHA + "  week2.json\n")
    print(json.dumps(dict(counts=P["counts"], row_counts=P["row_counts"], phrasing=stats, w_problems=P["w_problems"],
                          sha256=hashlib.sha256(body.encode()).hexdigest()), indent=1))
    if P["w_problems"]:
        raise SystemExit("condition-W deletion problems")


def find_world_copy():
    return find_week2()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "requests", "collect", "freeze"])
    ap.add_argument("--out", default=str(FROZEN))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="submit only the first N requests (pilot)")
    ap.add_argument("--no-claude", action="store_true")
    ap.add_argument("--batch-id", default=None)
    a = ap.parse_args()
    out = Path(a.out)
    if a.cmd == "plan":
        P = plan()
        print(json.dumps(dict(P["counts"], dropped=len(P["dropped_chains"]), w_problems=P["w_problems"]), indent=1))
    elif a.cmd == "requests":
        world = load_world()
        reqs = phrasing_requests(plan(world), user_turns(world))
        if a.submit and not a.dry_run:
            out.mkdir(parents=True, exist_ok=True)
            batchlib.submit("items", reqs, 150, out / "batches.json", a.limit)
        else:
            batchlib.print_dry_run("items", reqs, 150)
    elif a.cmd == "collect":
        st = json.loads((out / "batches.json").read_text())["items"]
        bid = a.batch_id or st[-1]["batch_id"]
        res = batchlib.collect(bid)
        prev = json.loads((out / "phrasing_raw.json").read_text()) if (out / "phrasing_raw.json").exists() else {}
        prev.update(res)
        (out / "phrasing_raw.json").write_text(json.dumps(prev, indent=1))
        print(len(res), "replies;", sum(v is None for v in res.values()), "failed")
    else:
        freeze(out, a.no_claude)


if __name__ == "__main__":
    main()
