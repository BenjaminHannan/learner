"""B1 TEACH, packed-call version for a strong API teacher (Muse Spark via Meta API or OpenRouter, OpenAI-style chat endpoint).

Same kinds, parsing, self-check, overlap guard and output files as teach.py (it reuses them), but many items per call:
  write  call: N items of one kind in one response, blocks separated by a line "###", each block in the six-line format.
  verify call: M numbered "text || question" lines in, M numbered answers out. Passage panel and paraphrase panel are separate calls.
Env: LLM_API_KEY (never printed), LLM_BASE (default https://openrouter.ai/api/v1), model via --model.
Stops (exit 3) on the first 429/402/403/quota error or at --max-usd (computed from --price-in/--price-out, $ per 1M tokens).
Usage: python3 teach_packed.py --out DIR --model ID --price-in 1.25 --price-out 4.25 --per-kind 40 --write-n 25 --verify-m 40 [--pilot-calls 30]
Then: python3 teach.py --out DIR --stage filter   (filter/export are unchanged)
"""
import argparse, json, os, random, re, sys, time, threading, urllib.request, urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import teach as T
from kinds import KINDS

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True); ap.add_argument("--model", required=True)
ap.add_argument("--price-in", type=float, required=True); ap.add_argument("--price-out", type=float, required=True)
ap.add_argument("--per-kind", type=int, default=2100, help="items to write per kind in total")
ap.add_argument("--write-n", type=int, default=25); ap.add_argument("--verify-m", type=int, default=40)
ap.add_argument("--workers", type=int, default=8); ap.add_argument("--max-usd", type=float, default=0.45)
ap.add_argument("--pilot-calls", type=int, default=0, help="stop after this many calls in total (pilot)")
ap.add_argument("--no-think", action="store_true", help="send reasoning off (Qwen 3.x think by default and bill thinking tokens)")
ap.add_argument("--only", default=""); ap.add_argument("--round", type=int, default=0); ap.add_argument("--seed", type=int, default=5003)
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("LLM_BASE", "https://openrouter.ai/api/v1").rstrip("/"); KEY = os.environ["LLM_API_KEY"]
lock, state = threading.Lock(), {"usd": 0.0, "calls": 0, "tin": 0, "tout": 0, "stop": None}


def call(msgs, max_new, temp):
    body = {"model": a.model, "messages": msgs, "max_tokens": max_new, "temperature": temp}
    if a.no_think:
        body["reasoning"] = {"enabled": False}
    req = urllib.request.Request(BASE + "/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    for attempt in range(3):
        if state["stop"]:
            return None
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            u = d.get("usage", {})
            with lock:
                state["tin"] += u.get("prompt_tokens", 0); state["tout"] += u.get("completion_tokens", 0); state["calls"] += 1
                state["usd"] = (state["tin"] * a.price_in + state["tout"] * a.price_out) / 1e6
                if state["usd"] >= a.max_usd:
                    state["stop"] = f"spend cap ${a.max_usd}"
                if a.pilot_calls and state["calls"] >= a.pilot_calls:
                    state["stop"] = "pilot call limit"
            return (d["choices"][0]["message"].get("content") or "")
        except urllib.error.HTTPError as e:
            if e.code in (429, 402, 403):
                state["stop"] = f"HTTP {e.code}"; return None
            time.sleep(5 * (attempt + 1))
        except Exception:
            time.sleep(5 * (attempt + 1))
    return ""


WRITE = """You write practice items for a children's reading test. Each item has a one-sentence passage, a paraphrase of it, one short-answer question and one yes/no question.

Kind of item: {desc}.

Write exactly {n} DIFFERENT items. Format each item as six lines, and put a line containing only ### between items (nothing before the first item, nothing after the last):
PASSAGE: <one plain sentence>
PARAPHRASE: <the same facts in different words or word order>
QUESTION: <a question whose answer is a short phrase copied from the passage>
ANSWER: <that short phrase>
YESNO: <a yes/no question about the passage>
YESNO_ANSWER: <Yes or No>

Rules:
- The passage is one sentence of 8 to 22 words, in simple common words, with only the facts it states. Vary the people, objects, places and sentence shapes between items.
- The paraphrase keeps every fact and adds none. The short answer must appear word for word in the passage and in the paraphrase.
- The yes/no answer must be supported or contradicted by the passage itself. About half the items have Yes, half No.
- Do not mention weather. Start the short-answer question with Who, What, Which or Whose (never Where, When, Why or How).
- Use only these first names: {names}. Mention a variety of everyday objects.

{examples}
Now write the {n} new items."""


def write_call(name, desc, ex, n, rng, rid):
    names = ", ".join(rng.sample(T.NAMES(), 20))
    txt = WRITE.format(desc=desc, n=n, names=names, examples=T.example_block(ex))
    return rid, name, call([{"role": "user", "content": txt}], max_new=n * 130 + 200, temp=0.9)


def stage_write():
    wp = out / f"writes_r{a.round}.jsonl"
    done = {json.loads(l)["call"] for l in open(wp)} if wp.exists() else set()
    jobs = []
    for name, desc, ex in KINDS:
        if a.only and name not in a.only.split(","):
            continue
        for c in range(a.per_kind // a.write_n):
            rid = f"{name}-c{c}"
            if rid not in done:
                jobs.append((name, desc, ex, rid))
    random.Random(a.seed).shuffle(jobs)
    print(len(jobs), "write calls", flush=True)
    miss = 0
    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(write_call, n, d, e, a.write_n, random.Random(f"{a.seed}|{rid}"), rid) for n, d, e, rid in jobs]
        for f in futs:
            rid, name, txt = f.result()
            if txt is None:
                continue
            blocks = [b for b in re.split(r"(?m)^\s*#{3,}\s*$", txt) if b.strip()]
            with open(wp, "a") as fh:
                fh.write(json.dumps({"call": rid, "kind": name, "n_blocks": len(blocks)}) + "\n")
                for i, b in enumerate(blocks):
                    fh.write(json.dumps({"id": f"{name}-r{a.round}-{rid.split('-c')[-1]}x{i}", "kind": name, "yn_target": "", "raw": b.strip(), "call": rid}) + "\n")
            if len(blocks) != a.write_n:
                miss += 1
    print(f"write calls with block count != {a.write_n}: {miss}; usd so far {state['usd']:.3f}", flush=True)


ASK = {"short": "Answer each line with a short phrase copied from its text.", "yn": "Answer each line Yes or No."}


def verify_call(items, key, qk, kind):
    lines = [f"{i + 1}. {it[key]} || {it[qk]}" for i, it in enumerate(items)]
    txt = f"Each numbered line is a text, then \"||\", then a question about it. {ASK[kind]} Reply with the same numbers, one answer per line, like \"1. answer\". No other text.\n\n" + "\n".join(lines)
    o = call([{"role": "user", "content": txt}], max_new=len(items) * 14 + 40, temp=0.0)
    if o is None:
        return None
    got = {}
    for ln in o.splitlines():
        m = re.match(r"\s*(\d+)[.)]\s*(.*)$", ln)
        if m:
            got[int(m.group(1)) - 1] = m.group(2).strip()
    return [got.get(i, "") for i in range(len(items))]


def stage_answer():
    wp, ap_ = out / f"writes_r{a.round}.jsonl", out / f"answers_r{a.round}.jsonl"
    done = {json.loads(l)["id"] for l in open(ap_)} if ap_.exists() else set()
    items = []
    for l in open(wp):
        w = json.loads(l)
        if "raw" not in w or w["id"] in done:
            continue
        it = T.parse_item(w["raw"])
        if it is None:
            with open(ap_, "a") as fh:
                fh.write(json.dumps({"id": w["id"], "kind": w["kind"], "parsed": False, "raw": w["raw"]}) + "\n")
        else:
            items.append((w, it))
    print(len(items), "items to verify", flush=True)
    chunks = [items[i:i + a.verify_m] for i in range(0, len(items), a.verify_m)]
    jobs = [(c, key, qk, kind) for c in chunks for key in ("PASSAGE", "PARAPHRASE") for qk, kind in (("QUESTION", "short"), ("YESNO", "yn"))]

    def run(j):
        c, key, qk, kind = j
        return verify_call([it for _, it in c], key, qk, kind)
    with ThreadPoolExecutor(a.workers) as pool:
        res = list(pool.map(run, jobs))
    for ci, c in enumerate(chunks):
        r = res[4 * ci:4 * ci + 4]
        if any(x is None for x in r):
            continue
        with open(ap_, "a") as fh:
            for i, (w, it) in enumerate(c):
                fh.write(json.dumps({"id": w["id"], "kind": w["kind"], "parsed": True, "yn_target": "", "item": it,
                                     "ans": {"short_passage": r[0][i], "yn_passage": r[1][i], "short_paraphrase": r[2][i], "yn_paraphrase": r[3][i]}}) + "\n")
    print(f"usd {state['usd']:.3f} calls {state['calls']} tokens in/out {state['tin']}/{state['tout']} stop={state['stop']}", flush=True)


stage_write()
if not state["stop"]:
    stage_answer()
json.dump({"usd": state["usd"], "calls": state["calls"], "tin": state["tin"], "tout": state["tout"], "stop": state["stop"]}, open(out / "cost.json", "w"))
sys.exit(3 if state["stop"] and "pilot" not in state["stop"] else 0)
