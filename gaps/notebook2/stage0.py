# Notebook-2 stage 0: retrieval-only scoring (no LLM). See PREREG.md.
import json, os, re, sys, hashlib, random
import numpy as np
from rank_bm25 import BM25Okapi

D = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("STAGE0_DATA", os.path.join(D, "..", "notebook1", "data", "longmemeval_s_cleaned.json"))
BUDGET = 8000  # tokens, chars/4
tok = lambda s: re.findall(r"\w+", s.lower())
ntok = lambda s: len(s) / 4

def pairs_of(q):
    out = []  # (date, sid, j, text, is_evidence, n_evidence_turns)
    for d, sid, s in sorted(zip(q["haystack_dates"], q["haystack_session_ids"], q["haystack_sessions"]), key=lambda z: z[0]):
        for j, t in enumerate(s):
            if t["role"] != "user": continue
            a = s[j+1] if j+1 < len(s) and s[j+1]["role"] == "assistant" else None
            ev = int(bool(t.get("has_answer"))) + int(bool(a and a.get("has_answer")))
            out.append(dict(date=d, sid=sid, j=j, text=f"user: {t['content']}\nassistant: {a['content'] if a else ''}", ev=ev))
    return out

_model = None
def model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cuda" if __import__("torch").cuda.is_available() else "cpu"); _model.max_seq_length = 320
    return _model

CACHE = os.environ.get("EMB_CACHE", os.path.join(D, "emb_cache")); os.makedirs(CACHE, exist_ok=True)
def windows(text, w=200):
    ws = text.split()
    return [" ".join(ws[i:i+w]) for i in range(0, max(len(ws), 1), w)] or [""]
def pair_embs(ps):
    """returns list of arrays (n_windows x dim), cached by text hash"""
    res = [None]*len(ps); todo = []
    for i, p in enumerate(ps):
        h = hashlib.sha1(p["text"].encode()).hexdigest()
        f = os.path.join(CACHE, h[:2], h + ".npy")
        if os.path.exists(f): res[i] = np.load(f)
        else: todo.append((i, f))
    if todo:
        wins, owner = [], []
        for i, f in todo:
            for w in windows(ps[i]["text"]): wins.append(w); owner.append(i)
        E = model().encode(wins, batch_size=64, normalize_embeddings=True, convert_to_numpy=True).astype(np.float16)
        by = {}
        for k, i in enumerate(owner): by.setdefault(i, []).append(E[k])
        for i, f in todo:
            arr = np.stack(by[i]); res[i] = arr
            os.makedirs(os.path.dirname(f), exist_ok=True); np.save(f, arr)
    return res

QI = "Represent this sentence for searching relevant passages: "
def rank_bm25(ps, query):
    sc = BM25Okapi([tok(p["text"]) or ["_"] for p in ps]).get_scores(tok(query))
    return list(np.argsort(-sc, kind="stable"))
def rank_dense(ps, query):
    E = pair_embs(ps)
    qe = model().encode([QI + query], normalize_embeddings=True)[0]
    sc = np.array([float((e.astype(np.float32) @ qe).max()) for e in E])
    return list(np.argsort(-sc, kind="stable"))
def rrf(*ranks, k=60):
    s = {}
    for r in ranks:
        for pos, i in enumerate(r): s[i] = s.get(i, 0) + 1 / (k + pos + 1)
    return sorted(s, key=lambda i: -s[i])
def fill(ps, order, neighbours=False):
    chosen, used = [], 0
    def add(i):
        nonlocal used
        if i in chosen or i < 0 or i >= len(ps): return True
        c = ntok(ps[i]["text"]) + 8
        if used + c > BUDGET: return False
        chosen.append(i); used += c; return True
    for i in order:
        if used >= BUDGET: break
        if not add(i): continue
        if neighbours:
            for n in (i-1, i+1):
                if 0 <= n < len(ps) and ps[n]["sid"] == ps[i]["sid"]: add(n)
    return chosen

def score(q, ps, chosen):
    ans = set(q["answer_session_ids"])
    ev_sids = {p["sid"] for p in ps if p["ev"] and p["sid"] in ans}
    got = {ps[i]["sid"] for i in chosen if ps[i]["ev"]}
    tot = sum(p["ev"] for p in ps); inc = sum(ps[i]["ev"] for i in chosen)
    return dict(allhit=int(bool(ev_sids) and ev_sids <= got), evrec=inc / tot if tot else None, n_ev_sess=len(ev_sids))

def fill_sessions(ps, order):
    """S4: rank sessions by their best pair in `order`; add whole sessions while they fit; the first session that
    does not fit is added pair by pair in `order` until the budget is full."""
    pos = {i: k for k, i in enumerate(order)}
    sess = []
    for i in order:
        if ps[i]["sid"] not in sess: sess.append(ps[i]["sid"])
    chosen, used = [], 0
    for sid in sess:
        idx = [i for i in range(len(ps)) if ps[i]["sid"] == sid]
        c = sum(ntok(ps[i]["text"]) + 8 for i in idx)
        if used + c <= BUDGET: chosen += idx; used += c; continue
        for i in sorted(idx, key=lambda i: pos[i]):
            c = ntok(ps[i]["text"]) + 8
            if used + c <= BUDGET: chosen.append(i); used += c
        break
    return chosen

def arm_orders(ps, query):
    b, d = rank_bm25(ps, query), rank_dense(ps, query)
    h = rrf(b, d)
    return {"S0": fill(ps, b), "S1": fill(ps, d), "S2": fill(ps, h), "S3": fill(ps, h, neighbours=True), "S4": fill_sessions(ps, h)}

if __name__ == "__main__":
    data = json.load(open(DATA))
    sample_ids = json.load(open(os.path.join(D, "..", "notebook1", "sample.json")))
    s120 = list(sample_ids)
    for t in sorted({x["question_type"] for x in data}):
        rest = sorted(x["question_id"] for x in data if x["question_type"] == t and x["question_id"] not in set(sample_ids))
        s120 += random.Random(1).sample(rest, 10)
    s120 = set(s120)
    if "STAGE0_DATA" in os.environ: s120 = {x["question_id"] for x in data}  # data is already the 120-item subset
    data = [x for x in data if not x["question_id"].endswith("_abs")]
    data.sort(key=lambda x: x["question_id"] not in s120)  # stage-1 questions first (stable)
    if len(sys.argv) > 1 and sys.argv[1] == "smoke": data = data[:3]
    sample = set(json.load(open(os.path.join(D, "..", "notebook1", "sample.json"))))
    if "--only120" in sys.argv: data = [x for x in data if x["question_id"] in s120]
    out = os.environ.get("STAGE0_OUT", os.path.join(D, "stage0_rows.jsonl"))
    done = set()
    if os.path.exists(out): done = {json.loads(l)["question_id"] for l in open(out)}
    with open(out, "a") as f:
        for n, q in enumerate(data):
            if q["question_id"] in done: continue
            ps = pairs_of(q)
            row = dict(question_id=q["question_id"], type=q["question_type"], in_sample=q["question_id"] in sample, in120=q["question_id"] in s120)
            for arm, ch in arm_orders(ps, q["question"]).items():
                row[arm] = score(q, ps, ch)
            f.write(json.dumps(row) + "\n"); f.flush()
            if n % 10 == 0: print(n, row["question_id"], {a: row[a]["allhit"] for a in ("S0", "S1", "S2", "S3", "S4")}, flush=True)
