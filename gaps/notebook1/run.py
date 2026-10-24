import json, os, sys, random, threading, re, time
from concurrent.futures import ThreadPoolExecutor
import anthropic
from rank_bm25 import BM25Okapi

D = os.path.dirname(os.path.abspath(__file__))
SMOKE = len(sys.argv) > 1 and sys.argv[1] == "smoke"
OUT = os.path.join(D, "smoke") if SMOKE else D
os.makedirs(OUT, exist_ok=True)
cli = anthropic.Anthropic(api_key=os.environ["LEARNER_ANTHROPIC_API_KEY"], max_retries=5)
HAIKU, SONNET = "claude-haiku-5-5", "claude-sonnet-5-5"
usage = {HAIKU: [0, 0, 0.0], SONNET: [0, 0, 0.0]}  # in, out, cost
lock = threading.Lock()
CAP = 10.0

def spend(): return sum(v[2] for v in usage.values())

def call(model, prompt, max_tokens):
    if spend() > CAP: raise SystemExit("HARD STOP: spend cap")
    r = cli.messages.create(model=model, max_tokens=max_tokens, output_config={"effort": "low"},
                            messages=[{"role": "user", "content": prompt}])
    i, o = r.usage.input_tokens, r.usage.output_tokens
    if model == HAIKU:
        pi, po = (0.5, 2.5) if i > 100000 else (0.1, 0.5)
    else: pi, po = 2, 10
    with lock:
        u = usage[model]; u[0] += i; u[1] += o; u[2] += (i*pi + o*po)/1e6
    if r.stop_reason == "refusal": return "[REFUSAL]", i
    return "".join(b.text for b in r.content if b.type == "text").strip(), i

tok = lambda s: re.findall(r"\w+", s.lower())
def fmt_session(date, sess):
    return f"[Session date: {date}]\n" + "\n".join(f"{t['role']}: {t['content']}" for t in sess)

# ---- data / sample
data = json.load(open(os.path.join(D, "data/longmemeval_s_cleaned.json")))
byid = {x["question_id"]: x for x in data}
sp = os.path.join(D, "sample.json")
if os.path.exists(sp): sample = json.load(open(sp))
else:
    sample = []
    for t in sorted({x["question_type"] for x in data}):
        ids = sorted(x["question_id"] for x in data if x["question_type"] == t)
        sample += random.Random(0).sample(ids, 10)
    json.dump(sample, open(sp, "w"), indent=1)
qs = [byid[i] for i in sample]
if SMOKE: qs = [byid[sample[0]], byid[sample[-1]]]

def sessions(q):  # chronological
    s = sorted(zip(q["haystack_dates"], q["haystack_session_ids"], q["haystack_sessions"]), key=lambda z: z[0])
    return s

# ---- writer notes cache
cp = os.path.join(D, "notes_cache.jsonl")
cache = {}
if os.path.exists(cp):
    for l in open(cp): r = json.loads(l); cache[(r["sid"], r["date"])] = r["notes"]
WP = ("You are keeping a notebook about a user, based on one past chat session with an AI assistant. Below is the session "
      "with its date. Write short notes about the USER, one note per line, each starting with the session date "
      "({date}). Cover: facts about them, plans, preferences, changes in their situation, and what the assistant told or "
      "recommended them (key specifics: names, numbers, items). Be concise but keep concrete details. Output only the notes.\n\n{sess}")
def notes_for(sid, date, sess):
    k = (sid, date)
    if k in cache: return cache[k]
    txt, _ = call(HAIKU, WP.format(date=date, sess=fmt_session(date, sess)), 3000)
    with lock:
        cache[k] = txt
        open(cp, "a").write(json.dumps({"sid": sid, "date": date, "notes": txt}) + "\n")
    return txt

RP = ("Below is a memory of past conversations between you (an AI assistant) and a user.\n\n{extra}{mem}\n\n"
      "Current date: {qd}\nQuestion: {q}\n\nAnswer the question briefly, based on the memory. "
      "If the memory does not contain the answer, say you don't know.\nAnswer:")

def build_mem(arm, q):
    ss = sessions(q); extra = ""
    if arm == "F":
        mem = "\n\n".join(fmt_session(d, s) for d, _, s in ss)
    elif arm == "O":
        ans = set(q["answer_session_ids"])
        mem = "\n\n".join(fmt_session(d, s) for d, i, s in ss if i in ans)
    elif arm == "R":
        pairs = []
        for d, _, s in ss:
            for j, t in enumerate(s):
                if t["role"] == "user":
                    a = s[j+1]["content"] if j+1 < len(s) and s[j+1]["role"] == "assistant" else ""
                    pairs.append((d, f"user: {t['content']}\nassistant: {a}"))
        bm = BM25Okapi([tok(p[1]) for p in pairs])
        sc = bm.get_scores(tok(q["question"]))
        top = sorted(sorted(range(len(pairs)), key=lambda i: -sc[i])[:10], key=lambda i: (pairs[i][0], i))
        mem = "\n\n".join(f"[Session date: {pairs[i][0]}]\n{pairs[i][1]}" for i in top)
    elif arm == "N":
        notes = []
        for d, i, s in ss:
            for l in notes_for(i, d, s).split("\n"):
                l = l.strip()
                if l: notes.append((d, l))
        bm = BM25Okapi([tok(n[1]) or ["_"] for n in notes])
        sc = bm.get_scores(tok(q["question"]))
        top = sorted(sorted(range(len(notes)), key=lambda i: -sc[i])[:20], key=lambda i: (notes[i][0], i))
        mem = "\n".join(notes[i][1] if notes[i][1].startswith(notes[i][0]) else f"[{notes[i][0]}] {notes[i][1]}" for i in top)
        extra = "These are dated notes, listed oldest to newest. If notes conflict, later notes replace earlier ones.\n\n"
    return mem, extra

def build(arm, q):
    if arm == "H":
        rm, _ = build_mem("R", q); nm, ne = build_mem("N", q)
        mem = "Raw conversation excerpts:\n\n" + rm + "\n\nDated notes (listed oldest to newest; if notes conflict, later notes replace earlier ones):\n" + nm
        return RP.format(extra="", mem=mem, qd=q["question_date"], q=q["question"])
    mem, extra = build_mem(arm, q)
    return RP.format(extra=extra, mem=mem, qd=q["question_date"], q=q["question"])

JP = {
 "default": "Answer yes if the response contains the correct answer (a response that is a subset of the needed info, or lacks required info, is no). Equivalent answers count.",
 "temporal-reasoning": "Answer yes if the response contains the correct answer. Do not penalize off-by-one errors in counts of days, weeks, or months. Equivalent answers count.",
 "knowledge-update": "Answer yes if the response contains the correct (updated) answer. If the response also mentions earlier outdated info but clearly gives the updated answer, it is correct.",
 "single-session-preference": "The reference is a rubric describing the user's preferences. Answer yes if the response recalls and uses the user's personal information correctly as the rubric describes (it need not hit every point).",
}
def judge(q, pred):
    abs_ = q["question_id"].endswith("_abs")
    if abs_:
        inst = ("The question is unanswerable. Answer yes only if the model response correctly says it cannot answer / does not know / "
                "the information is not available (and does not fabricate an answer). The reference explanation: ")
    else: inst = JP.get(q["question_type"], JP["default"]) + " Reference: "
    p = f"{inst}{q['answer']}\n\nQuestion: {q['question']}\nModel response: {pred}\n\nIs the model response correct? Answer only yes or no."
    out, _ = call(SONNET, p, 1000)
    return out.strip().lower().startswith("yes")

def work(a):
    arm, q = a
    try:
        pred, pt = call(HAIKU, build(arm, q), 2000)
        ok = judge(q, pred)
        return dict(question_id=q["question_id"], type=q["question_type"], pred=pred, gold=q["answer"], correct=ok, prompt_tokens=pt)
    except SystemExit: raise
    except Exception as e:
        return dict(question_id=q["question_id"], type=q["question_type"], pred=f"[ERROR {e}]", gold=q["answer"], correct=False, prompt_tokens=0, error=True)

import sys as _s
if len(_s.argv)>1 and _s.argv[1]=="H":
    rows=None
    with ThreadPoolExecutor(4) as ex: rows=list(ex.map(work,[("H",q) for q in qs]))
    for it in range(5):
        bad=[k for k,r in enumerate(rows) if r.get("error")]
        if not bad: break
        time.sleep(30)
        with ThreadPoolExecutor(2) as ex: new=list(ex.map(work,[("H",qs[k]) for k in bad]))
        for k,r in zip(bad,new): rows[k]=r
    open(os.path.join(OUT,"rows_H.jsonl"),"w").write("".join(json.dumps(r)+"\n" for r in rows))
    json.dump({"usage": usage, "spend": spend()}, open(os.path.join(OUT, "usage_H.json"), "w"))
    print("H",sum(r["correct"] for r in rows),"/",len(rows),"errors",sum(1 for r in rows if r.get("error")),"spend",round(spend(),3))
    raise SystemExit
if len(_s.argv)>1 and _s.argv[1]=="rerun":
    for arm in ["F","R","N","O"]:
        p=os.path.join(OUT,f"rows_{arm}.jsonl"); rows=[json.loads(l) for l in open(p)]
        bad=[k for k,r in enumerate(rows) if r.get("error")]
        print(arm,"retry",len(bad),flush=True)
        w = 2 if arm=="F" else 8
        def f(k):
            for att in range(6):
                r=work((arm,byid[rows[k]["question_id"]]))
                if not r.get("error"): return r
                time.sleep(30)
            return r
        with ThreadPoolExecutor(w) as ex: new=list(ex.map(f,bad))
        for k,r in zip(bad,new): rows[k]=r
        open(p,"w").write("".join(json.dumps(r)+"\n" for r in rows))
        print(arm,"errors left",sum(1 for r in rows if r.get("error")),"spend",round(spend(),3),flush=True)
    json.dump({"usage": usage, "spend": spend()}, open(os.path.join(OUT, "usage_rerun.json"), "w"))
    raise SystemExit
arms = ["F", "R", "N", "O"]
# warm notes cache first (N arm), in parallel across unique sessions
if True:
    uniq = {}
    for q in qs:
        for d, i, s in sessions(q): uniq[(i, d)] = s
    todo = [(i, d, s) for (i, d), s in uniq.items() if (i, d) not in cache]
    print("sessions to write:", len(todo), flush=True)
    with ThreadPoolExecutor(16) as ex: list(ex.map(lambda t: notes_for(*t), todo))
    print("notes done, spend", round(spend(), 3), flush=True)
res = {}
for arm in arms:
    with ThreadPoolExecutor(16) as ex: rows = list(ex.map(work, [(arm, q) for q in qs]))
    res[arm] = rows
    with open(os.path.join(OUT, f"rows_{arm}.jsonl"), "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    print(arm, sum(r["correct"] for r in rows), "/", len(rows), "spend", round(spend(), 3), flush=True)
json.dump({"usage": usage, "spend": spend()}, open(os.path.join(OUT, "usage.json"), "w"))
