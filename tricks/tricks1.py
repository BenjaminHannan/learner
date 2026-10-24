"""Tricks-1 eval harness (see PREREG-tricks1.md). Inference only. Pure-python helpers up top, vLLM at the bottom."""
import argparse, json, math, random, re, subprocess, sys, threading, time, unicodedata, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEFAULT_SETS = {"plain": ["gsmh", "math", "popqa"], "think": ["gsmh", "math"], "vote8": ["gsmh", "math"],
                "py": ["gsmh", "math"], "wiki": ["popqa"]}
MATH_SYS = "Solve the problem step by step. End your reply with a final line of the form 'Final answer: <number>'."
PY_SYS = MATH_SYS + " You have a python tool: use it for any arithmetic or computation instead of calculating by hand."
POP_SYS = "Answer the question in a few words."
WIKI_SYS = POP_SYS + " You have a search_wikipedia tool; use it to look up facts before answering."
PY_TOOL = {"type": "function", "function": {"name": "python", "description": "Run Python 3 code and return stdout. Use print().",
           "parameters": {"type": "object", "properties": {"code": {"type": "string", "description": "Python 3 code"}}, "required": ["code"]}}}
WIKI_TOOL = {"type": "function", "function": {"name": "search_wikipedia", "description": "Search Wikipedia; returns the top 3 article intros.",
             "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "search query"}}, "required": ["query"]}}}

# ---------------- parsing / scoring ----------------
_NUM = r"-?\d*\.?\d+(?:[eE][-+]?\d+)?"
_TOKEN = re.compile(r"(-?)\\[dt]?frac\s*\{\s*(\d+)\s*\}\s*\{\s*(\d+)\s*\}|(-?\d+)\s*/\s*(\d+)|(" + _NUM + ")")

def _num_match(m):
    if m.group(2) is not None:
        d = int(m.group(3)); return None if d == 0 else (-1 if m.group(1) else 1) * int(m.group(2)) / d
    if m.group(4) is not None:
        d = int(m.group(5)); return None if d == 0 else int(m.group(4)) / d
    return float(m.group(6))

def _clean(s):
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s.replace("\\,", "").replace("\\!", "").replace("\\$", "").replace("$", ""))
    return s.replace("\\%", "").replace("%", "")

def parse_number(s):
    """First number / fraction in s as float, or None."""
    m = _TOKEN.search(_clean(s or ""))
    try:
        return _num_match(m) if m else None
    except ValueError:
        return None

def last_number(s):
    ms = list(_TOKEN.finditer(_clean(s or "")))
    for m in reversed(ms):
        v = _num_match(m)
        if v is not None:
            return v
    return None

def last_boxed(s):
    i = s.rfind("\\boxed{")
    if i < 0:
        return None
    j, depth = i + 7, 1
    while j < len(s) and depth:
        depth += {"{": 1, "}": -1}.get(s[j], 0); j += 1
    return s[i + 7:j - 1] if depth == 0 else None

def strip_think(text, thinking=False):
    if "</think>" in text:
        return text.split("</think>")[-1].strip()
    return "" if thinking else text.strip()  # thinking that never closed = budget exhausted = no answer

def parse_answer(text):
    """Last 'Final answer:' line, else last \\boxed{}, else last number."""
    t = text.replace("*", "")
    for m in reversed(list(re.finditer(r"final answer\s*[:：]?\s*(.*)", t, re.I))):
        v = parse_number(m.group(1))
        if v is not None:
            return v
    b = last_boxed(text)
    if b is not None:
        v = parse_number(b)
        if v is not None:
            return v
    return last_number(text)

def num_match(pred, gold):
    return pred is not None and abs(pred - gold) <= 1e-4 * max(1.0, abs(gold))

def majority(vals, tol_gold=None):
    """Majority over parsed numbers (None dropped), clustered by the scoring tolerance; ties -> first seen."""
    clusters = []  # [rep, count]
    for v in vals:
        if v is None:
            continue
        for c in clusters:
            if num_match(v, c[0]):
                c[1] += 1; break
        else:
            clusters.append([v, 1])
    best = None
    for c in clusters:
        if best is None or c[1] > best[1]:
            best = c
    return None if best is None else best[0]

_DASHES = str.maketrans({c: "-" for c in "\u2010\u2011\u2012\u2013\u2014\u2212"})

def _norm(s):
    """NFKC (narrow/no-break spaces -> space), one kind of dash, casefold, collapsed spaces."""
    return " ".join(unicodedata.normalize("NFKC", s or "").translate(_DASHES).casefold().split())

def popqa_match(text, answers):
    """Any gold alias as a whole word/phrase (so 'US' does not match 'custom'), after Unicode normalisation."""
    t = _norm(text)
    return any(re.search(r"(?<!\w)" + re.escape(_norm(a)) + r"(?!\w)", t) for a in answers if a.strip())

def parse_tool_calls(text):
    """Return [(name, args)] from Qwen3.5 XML-ish or Qwen3 JSON tool calls (lenient)."""
    calls = []
    blocks = re.findall(r"<tool_call>(.*?)(?:</tool_call>|$)", text, re.S) or ([text] if "<function=" in text else [])
    for b in blocks:
        m = re.search(r"<function=([^>\s]+)\s*>(.*?)(?:</function>|$)", b, re.S)
        if m:
            args = {}
            for pm in re.finditer(r"<parameter=([^>\s]+)\s*>\n?(.*?)\n?(?:</parameter>|(?=<parameter=)|$)", m.group(2), re.S):
                args[pm.group(1)] = pm.group(2)
            calls.append((m.group(1), args)); continue
        try:
            j = json.loads(b.strip())
            a = j.get("arguments", j.get("parameters", {}))
            if isinstance(a, str):
                a = json.loads(a)
            calls.append((j["name"], a if isinstance(a, dict) else {}))
        except Exception:
            pass
    return calls

# ---------------- tools ----------------
def run_python(code, timeout=10, limit=2000):
    try:
        p = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        out = p.stdout
        if p.returncode:
            out += "\n" + "\n".join(p.stderr.strip().splitlines()[-3:])
    except subprocess.TimeoutExpired:
        out = f"Error: timed out after {timeout} s"
    return (out.strip() or "(no output)")[:limit]

UA = "premonition-tricks1/0.1 (research eval; benjamin.a.hannan@gmail.com)"
_wcache, _wlock = {}, threading.Lock()

def _wget(params, tries=5):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({**params, "format": "json"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                return json.load(r)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 ** i + random.random())

def search_wikipedia(query, n=3, chars=800):
    key = query.strip().casefold()
    with _wlock:
        if key in _wcache:
            return _wcache[key]
    try:
        hits = [h["title"] for h in _wget({"action": "query", "list": "search", "srsearch": query, "srlimit": n})["query"]["search"]]
        if not hits:
            res = "No results."
        else:
            pages = _wget({"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1, "exlimit": n, "titles": "|".join(hits)})["query"]["pages"]
            ext = {p["title"]: p.get("extract", "") for p in pages.values()}
            res = "\n\n".join(f"{t}: {ext.get(t, '')[:chars].strip()}" for t in hits)
    except Exception as e:
        return f"Error: search failed ({type(e).__name__})"
    with _wlock:
        _wcache[key] = res
    return res

def exec_tool(name, args):
    try:
        if name == "python":
            return run_python(str(args["code"]))
        if name == "search_wikipedia":
            return search_wikipedia(str(args["query"]))
        return f"Error: unknown tool {name}"
    except KeyError as e:
        return f"Error: missing argument {e}"

# ---------------- sets ----------------
_PLAIN_FRAC = re.compile(r"^-?(\d+(\.\d+)?|\d+/\d+|\\d?frac\{\d+\}\{\d+\})$")

def build_sets(seed=0):
    from datasets import load_dataset
    rng = random.Random(seed)
    g = load_dataset("reasoning-machines/gsm-hard", split="train")
    gs = [{"id": f"gsmh-{i}", "q": g[i]["input"], "gold": float(g[i]["target"])} for i in sorted(rng.sample(range(len(g)), 300))]
    m = load_dataset("HuggingFaceH4/MATH-500", split="test")
    ok = [i for i in range(len(m)) if _PLAIN_FRAC.match(m[i]["answer"].strip()) and parse_number(m[i]["answer"]) is not None]
    ok = sorted(rng.sample(ok, 300)) if len(ok) > 300 else ok
    ms = [{"id": f"math-{i}", "q": m[i]["problem"], "gold": parse_number(m[i]["answer"])} for i in ok]
    p = load_dataset("akariasai/PopQA", split="test")
    rare = [i for i in range(len(p)) if p[i]["s_pop"] < 1000]
    pop = [i for i in range(len(p)) if p[i]["s_pop"] >= 1000]
    ps = []
    for bucket, idx in (("rare", rare), ("pop", pop)):
        for i in sorted(rng.sample(idx, 200)):
            ps.append({"id": f"popqa-{i}", "q": p[i]["question"], "gold": json.loads(p[i]["possible_answers"]), "bucket": bucket})
    return {"gsmh": gs, "math": ms, "popqa": ps}

def load_sets(out):
    d = Path(out) / "sets"
    if all((d / f"{k}.jsonl").exists() for k in ("gsmh", "math", "popqa")):
        return {k: [json.loads(l) for l in (d / f"{k}.jsonl").open()] for k in ("gsmh", "math", "popqa")}
    sets = build_sets()
    d.mkdir(parents=True, exist_ok=True)
    for k, rows in sets.items():
        (d / f"{k}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return sets

def limit_rows(sname, rows, limit):
    if not limit:
        return rows
    if sname == "popqa":
        h = max(1, limit // 2)
        return [r for r in rows if r["bucket"] == "rare"][:h] + [r for r in rows if r["bucket"] == "pop"][:h]
    return rows[:limit]

# ---------------- generation (engine = callable(prompts, **sampling) -> [[(text, ntok), ...], ...]) ----------------
def render(tok, msgs, tools, thinking):
    return tok.apply_chat_template(msgs, tools=tools, add_generation_prompt=True, tokenize=False, enable_thinking=thinking)

def run_tool_loop(eng, tok, convs, tools, rounds, max_tokens, execfn=exec_tool, workers=8):
    """Batch every active conversation per round; run tool calls in a thread pool; stop when no call (or rounds spent)."""
    res = [{"text": "", "tokens": 0, "calls": 0} for _ in convs]
    active = list(range(len(convs)))
    for r in range(rounds + 1):
        if not active:
            break
        last = r == rounds  # final round offers no tools, so the model must answer
        outs = eng([render(tok, convs[i], None if last else tools, False) for i in active], n=1, temperature=0.0, max_tokens=max_tokens)
        jobs, nxt = [], []
        for i, o in zip(active, outs):
            text, nt = o[0]
            res[i]["tokens"] += nt
            res[i]["text"] = text
            calls = parse_tool_calls(text) if r < rounds else []
            if calls:
                res[i]["calls"] += len(calls)
                convs[i].append({"role": "assistant", "content": text})
                jobs += [(i, c) for c in calls]; nxt.append(i)
        with ThreadPoolExecutor(workers) as ex:
            results = list(ex.map(lambda j: execfn(*j[1]), jobs))
        for (i, _), out in zip(jobs, results):
            convs[i].append({"role": "tool", "content": out})
        active = nxt
    return res

def run_arm_set(kind, sname, rows, eng, tok):
    maths = sname in ("gsmh", "math")
    sysmsg = (PY_SYS if kind == "py" else MATH_SYS) if maths else (WIKI_SYS if kind == "wiki" else POP_SYS)
    msgs = [[{"role": "system", "content": sysmsg}, {"role": "user", "content": r["q"] + ("\n\nEnd with 'Final answer: <number>'." if maths else "")}] for r in rows]
    thinking = kind == "think"
    mt = 2048 if maths else 256
    out = []
    if kind in ("py", "wiki"):
        tr = run_tool_loop(eng, tok, msgs, [PY_TOOL if kind == "py" else WIKI_TOOL], 4 if kind == "py" else 3, 2048 if maths else 512)
        out = [{"text": t["text"], "tokens": t["tokens"], "calls": t["calls"]} for t in tr]
    elif kind == "vote8":
        gens = eng([render(tok, m, None, False) for m in msgs], n=8, temperature=0.7, top_p=0.8, max_tokens=2048)
        out = [{"samples": [t for t, _ in g], "text": g[0][0], "tokens": sum(n for _, n in g), "calls": 0} for g in gens]
    else:
        kw = dict(n=1, temperature=0.6, top_p=0.95, top_k=20, max_tokens=8192) if thinking else dict(n=1, temperature=0.0, max_tokens=mt)
        gens = eng([render(tok, m, None, thinking) for m in msgs], **kw)
        out = [{"text": g[0][0], "tokens": g[0][1], "calls": 0} for g in gens]
    recs = []
    for r, o in zip(rows, out):
        rec = {"id": r["id"], "gold": r["gold"], "tokens": o["tokens"], "tool_calls": o["calls"]}
        if maths:
            if kind == "vote8":
                preds = [parse_answer(strip_think(s)) for s in o["samples"]]
                rec["pred"] = majority(preds); rec["samples"] = preds
                rec["pass8"] = any(num_match(p, r["gold"]) for p in preds)
            else:
                rec["pred"] = parse_answer(strip_think(o["text"], thinking))
            rec["correct"] = num_match(rec["pred"], r["gold"])
        else:
            rec["pred"] = strip_think(o["text"], thinking)
            rec["correct"] = popqa_match(rec["pred"], r["gold"]); rec["bucket"] = r["bucket"]
        rec["text"] = o["text"][-1500:]
        recs.append(rec)
    return recs

def boot_ci(flags, B=2000, seed=0):
    rng = random.Random(seed); n = len(flags)
    if n == 0:
        return [None, None]
    accs = sorted(sum(flags[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return [accs[int(0.025 * B)], accs[int(0.975 * B) - 1]]

def stats(recs):
    n = len(recs)
    d = {"accuracy": sum(r["correct"] for r in recs) / n if n else 0.0, "n": n,
         "mean_tokens": sum(r["tokens"] for r in recs) / n if n else 0.0,
         "mean_tool_calls": sum(r["tool_calls"] for r in recs) / n if n else 0.0,
         "ci95": boot_ci([int(r["correct"]) for r in recs])}
    if recs and "pass8" in recs[0]:
        d["pass_at_8"] = sum(r["pass8"] for r in recs) / n
    return d

# ---------------- vLLM layer ----------------
def make_engine(model):
    from vllm import LLM, SamplingParams
    from transformers import AutoTokenizer
    llm = LLM(model=model, max_model_len=12288, gpu_memory_utilization=0.9, enable_prefix_caching=True,
              limit_mm_per_prompt={"image": 0, "video": 0}, max_num_seqs=256, trust_remote_code=True)
    def eng(prompts, **kw):
        outs = llm.generate(prompts, SamplingParams(**kw), use_tqdm=False)
        return [[(c.text, len(c.token_ids)) for c in o.outputs] for o in outs]
    return eng, AutoTokenizer.from_pretrained(model, trust_remote_code=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--arms", required=True)
    ap.add_argument("--sets", default=""); ap.add_argument("--out", required=True); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    sets = load_sets(out)
    want = [s for s in a.sets.split(",") if s]
    todo = []
    for arm in a.arms.split(","):
        kind = arm.split("_", 1)[-1]
        if kind not in DEFAULT_SETS:
            print(f"[skip] unknown arm {arm}", flush=True); continue
        rf = out / f"result_{arm}.json"
        done = json.loads(rf.read_text()) if rf.exists() else {}
        for s in DEFAULT_SETS[kind]:
            if (want and s not in want) or s in done:
                continue
            todo.append((arm, kind, s))
    if not todo:
        print("[result] nothing to do", flush=True); return
    eng, tok = make_engine(a.model)
    for arm, kind, s in todo:
        t0 = time.time()
        rows = limit_rows(s, sets[s], a.limit)
        recs = run_arm_set(kind, s, rows, eng, tok)
        (out / f"rows_{arm}_{s}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
        rf = out / f"result_{arm}.json"
        res = json.loads(rf.read_text()) if rf.exists() else {}
        res[s] = stats(recs)
        if s == "popqa":
            res["popqa_rare"] = stats([r for r in recs if r["bucket"] == "rare"])
            res["popqa_pop"] = stats([r for r in recs if r["bucket"] == "pop"])
        res["model"] = a.model
        rf.write_text(json.dumps(res, indent=1))
        print(f"[result] {a.model.split('/')[-1]} {arm} {s} acc={res[s]['accuracy']:.3f} n={res[s]['n']} tok={res[s]['mean_tokens']:.0f} t={time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
