# Notebook-2 stage 1: real local readers drive the search. See PREREG.md. Needs stage0.py next to it (import).
# usage: python stage1.py --make-subset            (one-off, where the 277 MB file is)
#        python stage1.py --backend hf --model-path IFM/K2-Horizon-3.7B
#        python stage1.py --backend openai --base-url http://127.0.0.1:8080/v1 --model NAME
#        python stage1.py --backend fake --limit 1  (smoke test)
import json, os, re, sys, time, random, argparse, urllib.request
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
import stage0 as S0

FULL = os.path.join(D, "..", "notebook1", "data", "longmemeval_s_cleaned.json")
SAMPLE = os.path.join(D, "..", "notebook1", "sample.json")
SUB = os.path.join(D, "data", "lme120.json")

def pick120(data):
    """120 items: the 60 Notebook-1 ids, then 10 per type (fresh Random(1) per type) from the remaining ids of that type, sorted
    (abstention ids included). Returns the items; each has question_id."""
    sample = json.load(open(SAMPLE)); byid = {x["question_id"]: x for x in data}
    extra = []
    for t in sorted({x["question_type"] for x in data}):
        ids = sorted(x["question_id"] for x in data if x["question_type"] == t and x["question_id"] not in set(sample))
        extra += random.Random(1).sample(ids, 10)
    return [byid[i] for i in sample + extra]

# ---- prompts (Notebook-1 RP verbatim)
RP = ("Below is a memory of past conversations between you (an AI assistant) and a user.\n\n{extra}{mem}\n\n"
      "Current date: {qd}\nQuestion: {q}\n\nAnswer the question briefly, based on the memory. "
      "If the memory does not contain the answer, say you don't know.\nAnswer:")
QP = ("You will search a user's chat history to answer a question. You cannot see the history yet. "
      "Current date: {qd}\nQuestion: {q}\n\nWrite up to 3 short search queries (keywords or a short phrase that would appear in the "
      "relevant conversation), one per line, nothing else.")
TP = ("Below are excerpts from past conversations between you (an AI assistant) and a user.\n\n{mem}\n\n"
      "Current date: {qd}\nQuestion: {q}\n\nDo the excerpts contain what you need to answer? If yes, reply exactly ENOUGH. "
      "If not, reply with up to 10 new search words (no other text) that would find the missing conversation.")

# ---- chat backends: chat(messages, max_tokens) -> str
THINK = re.compile(r"<think>.*?</think>", re.S)
def clean(s):
    s = THINK.sub("", s)
    if "</think>" in s: s = s.split("</think>")[-1]
    return s.strip()

def make_chat(a):
    if a.backend == "fake":
        def chat(messages, max_tokens):
            u = messages[-1]["content"]
            if u.startswith("You will search"): return "query one\nquery two"
            if "reply exactly ENOUGH" in u: return "ENOUGH" if len(u) % 2 == 0 else "new search words"
            return "I don't know"
        return chat
    if a.backend == "openai":
        url = a.base_url.rstrip("/") + "/chat/completions"
        def chat(messages, max_tokens):
            body = dict(model=a.model, messages=messages, max_tokens=max_tokens, temperature=0,
                        chat_template_kwargs={"enable_thinking": False})
            for att in range(4):
                try:
                    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", "Authorization": "Bearer none"})
                    r = json.load(urllib.request.urlopen(req, timeout=1800))
                    return clean(r["choices"][0]["message"]["content"] or "")
                except Exception as e:
                    print("chat retry", att, repr(e)[:200], flush=True); time.sleep(5 * (att + 1))
            raise RuntimeError("chat failed")
        return chat
    # hf: transformers, greedy, fp16 on CUDA (copied from the askonce-job1 loading approach)
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    tk = AutoTokenizer.from_pretrained(a.model_path, trust_remote_code=True)
    DT = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16  # bf16 on 4090/Ampere+, fp16 on T4
    kw = dict(trust_remote_code=True, attn_implementation="sdpa", device_map={"": 0})
    try: m = AutoModelForCausalLM.from_pretrained(a.model_path, dtype=DT, **kw)
    except TypeError: m = AutoModelForCausalLM.from_pretrained(a.model_path, torch_dtype=DT, **kw)
    m.eval(); m.config.use_cache = True
    IM_START, IM_END, TH = "<|ifm|im_start|>", "<|ifm|im_end|>", "<ifm|think>\n</ifm|think>"
    stops = [i for i in (tk.convert_tokens_to_ids(IM_END), tk.eos_token_id) if i is not None and i >= 0]
    def render(messages):  # K2 no-think format (assistant prefix + empty think block), same as askonce world.render
        out = [tk.bos_token or ""]
        for x in messages:
            out.append(f"{IM_START}{x['role']}\n{x['content']}{IM_END}")
        return "".join(out) + f"{IM_START}assistant\n{TH}"
    dev = next(m.parameters()).device
    with torch.no_grad():  # fp16 guard: a bf16-trained checkpoint can overflow; stop before spending GPU hours
        ids = tk("You are Ben's assistant. Which Sam do you mean?", return_tensors="pt").input_ids.to(dev)
        if not torch.isfinite(m(input_ids=ids, use_cache=False).logits.float()).all():
            raise FloatingPointError("non-finite logits in fp16; checkpoint overflows in this dtype")
    def chat(messages, max_tokens):
        enc = tk(render(messages), return_tensors="pt", add_special_tokens=False).to(dev)
        with torch.no_grad():
            g = m.generate(**enc, max_new_tokens=max_tokens, do_sample=False, eos_token_id=stops, pad_token_id=tk.pad_token_id or stops[0])
        new = [t for t in g[0, enc["input_ids"].shape[1]:].tolist()]
        for p, t in enumerate(new):
            if t in stops: new = new[:p]; break
        return clean(tk.decode(new, skip_special_tokens=True))
    return chat

# ---- context building
def mem_of(ps, chosen):  # date order (ps is date ordered)
    return "\n\n".join(f"[Session date: {ps[i]['date']}]\n{ps[i]['text']}" for i in sorted(chosen))
def oracle_mem(q):
    ans = set(q["answer_session_ids"])
    ss = sorted(zip(q["haystack_dates"], q["haystack_session_ids"], q["haystack_sessions"]), key=lambda z: z[0])
    return "\n\n".join(f"[Session date: {d}]\n" + "\n".join(f"{t['role']}: {t['content']}" for t in s) for d, i, s in ss if i in ans)
def answer(chat, q, mem):
    p = RP.format(extra="", mem=mem, qd=q["question_date"], q=q["question"])
    return chat([{"role": "user", "content": p}], 200), len(p)
def parse_queries(s):
    out = []
    for l in s.split("\n"):
        l = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", l).strip().strip('"')
        if l and l not in out: out.append(l)
    return out[:3]

def run_arm(arm, q, ps, R, a, chat):
    """returns dict(pred, prompt_chars, chosen or None, plus keywords/round2)"""
    qq = q["question"]; ex = {}
    fill = lambda order: S0.fill_sessions(ps, order) if a.retriever == "S4" else S0.fill(ps, order, a.retriever == "S3")
    if arm == "O":
        pred, n = answer(chat, q, oracle_mem(q)); return dict(pred=pred, prompt_chars=n, chosen=None)
    if "b" not in R: R["b"] = S0.rank_bm25(ps, qq)
    if arm == "R": chosen = S0.fill(ps, R["b"])
    else:
        if "d" not in R: R["d"] = S0.rank_dense(ps, qq); R["h"] = S0.rrf(R["b"], R["d"])
        if arm == "Hy": chosen = fill(R["h"])
        elif arm == "Q":
            raw = chat([{"role": "user", "content": QP.format(qd=q["question_date"], q=qq)}], 40)
            kws = parse_queries(raw); ex["keywords"] = kws
            ranks = [R["b"], R["d"]]
            for k in kws: ranks += [S0.rank_bm25(ps, k), S0.rank_dense(ps, k)]
            chosen = fill(S0.rrf(*ranks))
        elif arm == "T":
            chosen = fill(R["h"])
            r = chat([{"role": "user", "content": TP.format(mem=mem_of(ps, chosen), qd=q["question_date"], q=qq)}], 40)
            fired = not r.strip().upper().startswith("ENOUGH") and bool(r.strip())
            ex["round2"] = fired; ex["keywords"] = r.strip() if fired else None
            if fired:
                chosen = fill(S0.rrf(R["h"], S0.rank_bm25(ps, r), S0.rank_dense(ps, r)))
        else: raise SystemExit("unknown arm " + arm)
    pred, n = answer(chat, q, mem_of(ps, chosen))
    return dict(pred=pred, prompt_chars=n, chosen=chosen, **ex)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-subset", action="store_true")
    ap.add_argument("--data", default=SUB)
    ap.add_argument("--backend", choices=["openai", "hf", "fake"], default="openai")
    ap.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    ap.add_argument("--model", default="model"); ap.add_argument("--model-path")
    ap.add_argument("--reader", help="name used in rows_{reader}.jsonl (default from model)")
    ap.add_argument("--retriever", choices=["S2", "S3", "S4"], default="S2")
    ap.add_argument("--arms", default="R,Hy,Q,T,O")
    ap.add_argument("--limit", type=int); ap.add_argument("--out-dir", default=os.path.join(D, "stage1_out"))
    a = ap.parse_args()
    if a.make_subset:
        sub = pick120(json.load(open(FULL))); ids = set(json.load(open(SAMPLE)))
        for x in sub: x["in_sample"] = x["question_id"] in ids
        os.makedirs(os.path.dirname(SUB), exist_ok=True); json.dump(sub, open(SUB, "w"))
        print("wrote", SUB, len(sub), "items", round(os.path.getsize(SUB) / 1e6, 1), "MB"); return
    data = json.load(open(a.data))
    if len(data) > 120: data = pick120(data)
    if a.limit: data = data[:a.limit]
    reader = a.reader or (a.backend if a.backend == "fake" else os.path.basename((a.model_path or a.model).rstrip("/")))
    os.makedirs(a.out_dir, exist_ok=True); out = os.path.join(a.out_dir, f"rows_{reader}.jsonl")
    done = {(r["question_id"], r["arm"]) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    chat = make_chat(a); arms = a.arms.split(",")
    with open(out, "a") as f:
        for n, q in enumerate(data):
            ps = None; R = {}
            for arm in arms:
                if (q["question_id"], arm) in done: continue
                if ps is None: ps = S0.pairs_of(q)
                t0 = time.time(); r = run_arm(arm, q, ps, R, a, chat)
                ch = r.pop("chosen")
                sc = S0.score(q, ps, ch) if ch is not None else dict(allhit=None, evrec=None)
                row = dict(question_id=q["question_id"], type=q["question_type"], arm=arm, reader=reader, retriever=a.retriever,
                           in_sample=q.get("in_sample"), wall_s=round(time.time() - t0, 2), allhit=sc["allhit"], evrec=sc["evrec"], **r)
                f.write(json.dumps(row) + "\n"); f.flush()
                print(n, q["question_id"], arm, f"{row['wall_s']}s", "allhit", row["allhit"], repr(row["pred"][:60]), flush=True)

if __name__ == "__main__": main()
