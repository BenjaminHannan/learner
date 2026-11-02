# Notebook-2 arm S5 "fact cards" (PREREG Amendment C). Subcommands: plan | submit | collect | score
import json, os, re, sys, time, hashlib
import numpy as np
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import stage0 as S
sys.path.insert(0, os.path.join(D, "..", ".."))
from sleep2.recallread.batchlib import enc_id, dec_id, client

MODEL = "claude-haiku-5-5"
PRICE_IN, PRICE_OUT = 0.05, 0.25  # $/M, batch
CAP = 5.0
STATE = os.path.join(D, "s5_state.json")
CARDS = os.path.join(D, "cards.jsonl")
ROWS = os.path.join(D, "stage0_s5_rows.jsonl")
OLD = os.path.join(D, "stage0_rows.jsonl")
MAXBYTES, MAXREQ = 200_000_000, 50_000

def load():
    data = json.load(open(S.DATA))
    old = {}
    for l in open(OLD):
        r = json.loads(l); old[r["question_id"]] = r
    a = {k for k, r in old.items() if r["in120"]}
    qs = [q for q in data if not q["question_id"].endswith("_abs") and
          (q["question_id"] in a or q["question_type"] == "multi-session")]
    seta = {q["question_id"] for q in qs if q["question_id"] in a}
    setb = {q["question_id"] for q in qs if q["question_type"] == "multi-session"}
    return qs, seta, setb, old

shash = lambda s: hashlib.sha1(json.dumps(s, sort_keys=True).encode()).hexdigest()

def sessions(qs):
    u = {}
    for q in qs:
        for d, s in zip(q["haystack_dates"], q["haystack_sessions"]):
            u.setdefault(shash(s), (d, s))
    return u

def prompt(date, s):
    lines, n = [], 0
    for t in s:
        if t["role"] == "user":
            lines.append(f"U{n}: {t['content']}"); n += 1
        else:
            lines.append(f"A: {t['content']}")
    day = date.split(" ")[0]
    return (f"Below is a chat session between a user and an AI assistant, dated {day}. User turns are numbered U0, U1, ...; "
            "assistant turns are marked A.\n\nWrite short atomic facts about the user (their life, plans, possessions, preferences, "
            "events, numbers, names, dates) and about what the assistant told or recommended them (keep names, numbers, items, dates). "
            "One fact per line. Each line must start with the tag of the user turn it comes from, then the date, then the fact, "
            f"formatted exactly like: U3 | {day} | User bought a red Trek bike.\nOutput only the lines, nothing else.\n\n"
            "=== SESSION ===\n" + "\n\n".join(lines))

def reqs_of(u):
    return [dict(custom_id=enc_id(h), params=dict(model=MODEL, max_tokens=1500, output_config={"effort": "low"},
            messages=[dict(role="user", content=prompt(d, s))])) for h, (d, s) in u.items()]

def plan():
    qs, a, b, _ = load(); u = sessions(qs)
    chars = sum(len(prompt(d, s)) for d, s in u.values())
    n = len(u); tin = chars / 4; tout = n * 300  # assume ~300 output tokens
    usd = (tin * PRICE_IN + tout * PRICE_OUT) / 1e6
    usd_max = (tin * PRICE_IN + n * 1500 * PRICE_OUT) / 1e6
    print(f"questions: (a)={len(a)} (b)={len(b)} union={len(qs)}; unique sessions={n}; input tokens~{tin/1e6:.1f}M")
    print(f"est cost ${usd:.2f} (300 out tok/session); worst case (1500 out) ${usd_max:.2f}")
    if usd > CAP: raise SystemExit("estimate above $5; refusing")
    return qs, u

def submit():
    qs, u = plan()
    st = json.load(open(STATE)) if os.path.exists(STATE) else {"batches": []}
    if st["batches"]: raise SystemExit("already submitted: " + STATE)
    rs = reqs_of(u); c = client(); chunk, size = [], 0
    def flush():
        nonlocal chunk, size
        if chunk:
            b = c.messages.batches.create(requests=chunk); st["batches"].append(dict(id=b.id, n=len(chunk)))
            json.dump(st, open(STATE, "w"), indent=1); print("submitted", b.id, len(chunk)); chunk, size = [], 0
    for r in rs:
        sz = len(json.dumps(r))
        if chunk and (size + sz > MAXBYTES or len(chunk) >= MAXREQ): flush()
        chunk.append(r); size += sz
    flush()

TAG = re.compile(r"^\s*U(\d+)\s*\|\s*([^|]*)\|\s*(.+)$")
def collect():
    st = json.load(open(STATE)); c = client(); cards = []; stats = dict(lines=0, tagged=0, sessions=0, failed=0, tin=0, tout=0)
    for bt in st["batches"]:
        while True:
            b = c.messages.batches.retrieve(bt["id"])
            if b.processing_status == "ended": break
            print(time.strftime("%T"), bt["id"], b.processing_status, b.request_counts, flush=True); time.sleep(60)
        for r in c.messages.batches.results(bt["id"]):
            h = dec_id(r.custom_id)
            if r.result.type != "succeeded": stats["failed"] += 1; continue
            m = r.result.message; stats["sessions"] += 1
            stats["tin"] += m.usage.input_tokens; stats["tout"] += m.usage.output_tokens
            txt = "".join(x.text for x in m.content if x.type == "text")
            for ln in txt.splitlines():
                if not ln.strip(): continue
                stats["lines"] += 1; g = TAG.match(ln)
                if g: stats["tagged"] += 1; cards.append(dict(session_hash=h, turn_index=int(g.group(1)), text=ln.strip()))
                else: cards.append(dict(session_hash=h, turn_index=0, text=ln.strip()))
    with open(CARDS, "w") as f:
        for x in cards: f.write(json.dumps(x) + "\n")
    stats["usd"] = round((stats["tin"] * PRICE_IN + stats["tout"] * PRICE_OUT) / 1e6, 3)
    print("collect:", stats, "cards", len(cards))

CE = os.path.join(D, "emb_cache", "cards.npy")
def card_embs(cards):
    keys = [hashlib.sha1(c["text"].encode()).hexdigest() for c in cards]
    cache = {}
    if os.path.exists(CE + ".idx"):
        ks = json.load(open(CE + ".idx")); E = np.load(CE); cache = dict(zip(ks, E))
    todo = sorted({k for k in keys if k not in cache}); txt = {k: c["text"] for k, c in zip(keys, cards)}
    if todo:
        E = S.model().encode([txt[k] for k in todo], batch_size=128, normalize_embeddings=True, convert_to_numpy=True).astype(np.float16)
        cache.update(zip(todo, E))
        json.dump(list(cache), open(CE + ".idx", "w")); np.save(CE, np.stack(list(cache.values())))
    return np.stack([cache[k] for k in keys]).astype(np.float32)

def score():
    qs, a, b, old = load()
    by = {}
    for l in open(CARDS):
        x = json.loads(l); by.setdefault(x["session_hash"], []).append(x)
    allc = [x for v in by.values() for x in v]; print("embedding cards", len(allc), flush=True)
    emb = dict(zip(map(id, allc), card_embs(allc)))
    done = {}
    if os.path.exists(ROWS): done = {json.loads(l)["question_id"]: 1 for l in open(ROWS)}
    out = open(ROWS, "a")
    for n, q in enumerate(qs):
        if q["question_id"] in done: continue
        ps = S.pairs_of(q); pidx = {(p["sid"], p["j"]): i for i, p in enumerate(ps)}
        cs, cv = [], []  # cards (text) and pair index
        for sid, s in zip(q["haystack_session_ids"], q["haystack_sessions"]):
            users = [j for j, t in enumerate(s) if t["role"] == "user"]
            if not users: continue
            for x in by.get(shash(s), []):
                t = x["turn_index"] if x["turn_index"] < len(users) else 0
                cs.append(x); cv.append(pidx[(sid, users[t])])
        qq = q["question"]; rk = [S.rank_bm25(ps, qq), S.rank_dense(ps, qq)]
        if cs:
            sc = np.array([0.0] * len(cs))
            bm = S.BM25Okapi([S.tok(x["text"]) or ["_"] for x in cs]).get_scores(S.tok(qq))
            qe = S.model().encode([S.QI + qq], normalize_embeddings=True)[0]
            de = np.stack([emb[id(x)] for x in cs]) @ qe
            for sc in (bm, de):
                seen, r = set(), []
                for k in np.argsort(-sc, kind="stable"):
                    p = cv[k]
                    if p not in seen: seen.add(p); r.append(p)
                rk.append(r)
        row = dict(question_id=q["question_id"], type=q["question_type"], seta=q["question_id"] in a, setb=q["question_id"] in b,
                   S5=S.score(q, ps, S.fill(ps, S.rrf(*rk, k=60))), n_cards=len(cs))
        o = old.get(q["question_id"])
        row["S2"] = o["S2"] if o else S.score(q, ps, S.fill(ps, S.rrf(rk[0], rk[1])))
        out.write(json.dumps(row) + "\n"); out.flush()
        print(n, q["question_id"], row["S2"]["allhit"], row["S5"]["allhit"], flush=True)
    out.close(); report()

def agg(rows, arm):
    if not rows: return "-"
    ah = sum(r[arm]["allhit"] for r in rows); ev = [r[arm]["evrec"] for r in rows if r[arm]["evrec"] is not None]
    return ah, 100 * ah / len(rows), 100 * sum(ev) / max(len(ev), 1)

def report():
    rows = [json.loads(l) for l in open(ROWS)]
    A = [r for r in rows if r["seta"]]; B = [r for r in rows if r["setb"]]
    lines = []
    def tab(name, rs):
        s2, s5 = agg(rs, "S2"), agg(rs, "S5")
        w = sum(r["S5"]["allhit"] > r["S2"]["allhit"] for r in rs); l = sum(r["S5"]["allhit"] < r["S2"]["allhit"] for r in rs)
        lines.append(f"| {name} | {len(rs)} | {s2[0]} ({s2[1]:.1f}%) | {s5[0]} ({s5[1]:.1f}%) | {s2[2]:.1f} | {s5[2]:.1f} | {w} / {l} |")
    lines.append("| set | n | S2 AllHit | S5 AllHit | S2 EvRecall % | S5 EvRecall % | S5 wins / losses vs S2 |\n|---|---|---|---|---|---|---|")
    tab("(a) overall", A)
    for t in sorted({r["type"] for r in A}): tab(f"(a) {t}", [r for r in A if r["type"] == t])
    tab("(b) multi-session", B)
    ms_a = [r for r in A if r["type"] == "multi-session"]
    da = agg(A, "S5")[0] - agg(A, "S2")[0]; db = agg(B, "S5")[0] - agg(B, "S2")[0]
    lines.append(f"\nDeltas (S5 - S2, AllHit count): (a) overall {da:+d} of {len(A)}; (b) multi-session {db:+d} of {len(B)}")
    lines.append(f"Amendment C pass (b >= +15 AND a >= +2): {'PASS' if db >= 15 and da >= 2 else 'FAIL'}")
    lines.append(f"Amendment C wrong-if (b <= +3): {'TRIGGERED' if db <= 3 else 'not triggered'}")
    txt = "\n".join(lines); print(txt); open(os.path.join(D, "s5_report.txt"), "w").write(txt)

if __name__ == "__main__":
    {"plan": plan, "submit": submit, "collect": collect, "score": score, "report": report}[sys.argv[1]]()
