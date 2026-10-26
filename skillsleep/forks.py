"""Near-miss fork pairs for arm C3 (PREREG-2, change 2). Two subcommands; the tau2 part is forks_run.py (tau2 venv).

  forks.py make TOKENIZER_DIR ENV_JSON OUT.json.gz DAY_RESULTS [FIX_RESULTS ...]     (needs the BASE model served on :8000)
    For every real day run (failed and passed) and every passing fix retry: rescore the agent turns with the base model (vLLM prompt_logprobs=2 on the
    rendered conversation), keep decision tokens where the model was confident (p1 >= 0.9) but a runner-up had p2 >= 0.005, take up to 6 per run spread over
    the run, force the runner-up, let the model finish that turn (greedy), and write each fork as {history, forked assistant message}.
    Decision tokens = first token of an assistant turn, tool-name tokens, first token of each argument value.
  forks.py pairs TOKENIZER_DIR ENV_JSON FORK_RESULTS.jsonl FORKS.json.gz OUT.jsonl DAY_RESULTS [FIX_RESULTS ...]
    Fork outcome != parent outcome -> pair (chosen = the passing run, rejected = the failing one). fork_at = first token where the two renders differ.
Env: FORK_MAX_PAIRS=200 MAXTOK_PAIR=12288 FORK_MAKE_MIN=25 FORK_PER_RUN=6 FORK_CONC=8 URL=http://localhost:8000"""
import bisect, collections, gzip, json, math, os, random, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from common import ok, real, sims
from render import END, apply, load_tok, render_traj, spans, to_chat

E = os.environ.get
P1, P2 = 0.9, 0.005; PER_RUN = int(E("FORK_PER_RUN", 6)); URL = E("URL", "http://localhost:8000")
TCALL = re.compile(r"<ifm\|tool_call>([^\n]*)\n"); VAL = re.compile(r"<ifm\|arg_value>(.*?)</ifm\|arg_value>", re.S)
CALLS = re.compile(r"<ifm\|tool_calls>(.*?)(?:</ifm\|tool_calls>|$)", re.S)
CALL = re.compile(r"<ifm\|tool_call>(.*?)</ifm\|tool_call>", re.S)
ARG = re.compile(r"<ifm\|arg_key>(.*?)</ifm\|arg_key>\s*(?:<ifm\|arg_type>(.*?)</ifm\|arg_type>\s*)?<ifm\|arg_value>(.*?)</ifm\|arg_value>", re.S)


def post(path, body, timeout=1800):
    r = urllib.request.Request(URL + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=timeout).read())


# ---------- fork points ----------
def turn_spans(text, messages, gen):
    """[(index in messages, char start, char end)] of every generated assistant turn in the rendered text."""
    ai = [i for i, m in enumerate(messages) if m["role"] == "assistant"]
    sp = spans(text, len(ai), gen)
    return list(zip([ai[k] for k, g in enumerate(gen) if g], [a for a, _ in sp], [b for _, b in sp]))


def decision_points(text, starts, s, e):
    """[(token index, kind)] inside the turn text[s:e]: its first token, the tool-name tokens, the first token of every argument value."""
    out = [(bisect.bisect_left(starts, s), "turn")]; seg = text[s:e]
    for m in TCALL.finditer(seg):
        out += [(j, "tool") for j in range(bisect.bisect_left(starts, s + m.start(1)), bisect.bisect_left(starts, s + m.end(1)))]
    for m in VAL.finditer(seg):
        if m.group(1):
            out.append((bisect.bisect_left(starts, s + m.start(1)), "arg"))
    return out


def top2(entry):
    """prompt_logprobs entry {token id: {logprob}} -> [(token id, prob)] for the two most likely tokens."""
    return sorted(((int(k), math.exp(v["logprob"])) for k, v in entry.items()), key=lambda x: -x[1])[:2]


def candidates(ids, tps, plp):
    """Decision tokens where the sampled token was the model's top-1 with p1 >= 0.9 and the runner-up had p2 >= 0.005."""
    out = []
    for mi, s_tok, kinds in tps:
        for j, kind in kinds:
            if j < 1 or j >= len(ids) or not plp[j]:
                continue
            t = top2(plp[j])
            if len(t) == 2 and t[0][0] == ids[j] and t[0][1] >= P1 and t[1][1] >= P2:
                out.append({"mi": mi, "ts": s_tok, "j": j, "kind": kind, "p1": t[0][1], "p2": t[1][1], "ru": t[1][0]})
    return out


def spread(xs, n):  # n evenly spread items of xs (xs longer than n)
    return [xs[(2 * i + 1) * len(xs) // (2 * n)] for i in range(n)]


def pick(cands, k=PER_RUN):
    """At most k forks spread over the run, one per assistant turn first (the most surprising token of each turn), then second picks per turn, ..."""
    by = collections.defaultdict(list)
    for c in sorted(cands, key=lambda c: -c["p2"]):
        by[c["mi"]].append(c)
    turns = sorted(by); out = []; r = 0
    while len(out) < k and any(len(v) > r for v in by.values()):
        rnd = [by[t][r] for t in turns if len(by[t]) > r]
        out += spread(rnd, k - len(out)) if len(rnd) > k - len(out) else rnd; r += 1
    return sorted(out, key=lambda c: c["j"])


# ---------- forced turn -> tau2 assistant message ----------
def arg_types(tools):
    def has_str(v):
        t = v.get("type") if isinstance(v, dict) else None
        return t == "string" or (isinstance(t, list) and "string" in t) or any(has_str(b) for k in ("anyOf", "oneOf") for b in v.get(k, []) or [])
    return {t["function"]["name"]: {k: has_str(v) for k, v in (t["function"].get("parameters") or {}).get("properties", {}).items()} for t in tools}


def parse_turn(text, types):
    """K2 turn text (after the generation prefix) -> (content, [(name, args)]) or None if the turn is cut off / empty.
    Same rules as the swap k2_shim parser: string-typed parameters stay text, the rest is read as JSON."""
    text = text.replace(END, "")
    m = CALLS.search(text); calls = []
    content = (text[:m.start()] if m else text).strip()
    if m:
        body = m.group(1)
        if body.count("<ifm|tool_call>") != len(CALL.findall(body)):
            return None
        for c in CALL.findall(body):
            c = c.strip(); name = c.split("\n", 1)[0].strip(); pairs = ARG.findall(c)
            if c.count("<ifm|arg_key>") != len(pairs):
                return None
            args = {}
            for k, at, v in pairs:
                k, v = k.strip(), v.strip()
                if "string" in at.strip().split("|") or types.get(name, {}).get(k):
                    args[k] = v
                else:
                    try:
                        args[k] = json.loads(v)
                    except Exception:
                        args[k] = v
            calls.append((name, args))
    return (content, calls) if content or calls else None


def forked_message(content, calls, n_tokens, tag):
    """tau2 AssistantMessage as a dict. The usage record marks it as generated (so render_traj trains on it)."""
    return {"role": "assistant", "content": content or None, "usage": {"completion_tokens": n_tokens},
            "tool_calls": [{"id": f"fk_{tag}_{i}", "name": n, "arguments": a, "requestor": "assistant"} for i, (n, a) in enumerate(calls)] or None}


def finish_turn(tok, ids, c, types, tag, im_end):
    """Force runner-up c['ru'] at token c['j'] and let the model finish the turn. -> forked message dict or None."""
    body = {"model": "m", "prompt": ids[:c["j"]] + [c["ru"]], "max_tokens": 3000, "temperature": 0, "stop_token_ids": [im_end],
            "skip_special_tokens": False, "return_token_ids": True}
    ch = post("/v1/completions", body)["choices"][0]
    if ch.get("finish_reason") == "length":
        return None
    head = ids[c["ts"]:c["j"]] + [c["ru"]]
    comp = ch.get("token_ids")
    text = tok.decode(head + comp, skip_special_tokens=False) if comp is not None else tok.decode(head, skip_special_tokens=False) + ch["text"]
    got = parse_turn(text, types)
    return forked_message(*got, len(head) + len(comp or []), tag) if got else None


def process(tok, env, types, im_end, s, src):
    """All forks of one parent run -> list of fork dicts (history = the parent's messages before the forked turn)."""
    msgs = s["messages"]; chat, gen = to_chat(env["system"], msgs)
    text = apply(tok, chat, env["tools"]); enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    ids = enc["input_ids"]; starts = [a for a, _ in enc["offset_mapping"]]
    tps = [(mi, bisect.bisect_left(starts, a), decision_points(text, starts, a, b)) for mi, a, b in turn_spans(text, msgs, gen)]
    r = post("/v1/completions", {"model": "m", "prompt": ids, "max_tokens": 1, "temperature": 0, "prompt_logprobs": 2})
    cs = pick(candidates(ids, tps, r["choices"][0]["prompt_logprobs"])); out = []
    for c in cs:
        tag = f"{s['id'][:8]}_{c['j']}"; m = finish_turn(tok, ids, c, types, tag, im_end)
        if m:
            out.append({"fork_id": tag, "task_id": str(s["task_id"]), "parent": s["id"], "parent_src": src, "parent_ok": ok(s), "mi": c["mi"],
                        "kind": c["kind"], "j": c["j"], "p1": round(c["p1"], 4), "p2": round(c["p2"], 4), "ru": tok.decode([c["ru"]]),
                        "history": msgs[:c["mi"]], "msg": m})
    return out, len(cs)


def parents(day, fixes):
    for s in sims(day):
        if real(s):
            yield s, "day"
    for p in fixes:
        for s in sims(p):
            if real(s) and ok(s):
                yield s, "fix"


def make(tokd, envp, outp, day, fixes):
    tok = load_tok(tokd); env = json.load(open(envp)); types = arg_types(env["tools"]); im_end = tok.convert_tokens_to_ids(END)
    deadline = time.time() + 60 * float(E("FORK_MAKE_MIN", 25)); ps = list(parents(day, fixes)); stats = collections.Counter(); forks = []

    def one(a):
        if time.time() > deadline:
            return [], -1
        try:
            return process(tok, env, types, im_end, *a)
        except Exception as e:
            print("fork scoring failed", a[0]["task_id"], type(e).__name__, str(e)[:150], flush=True); return [], -2
    with ThreadPoolExecutor(int(E("FORK_CONC", 8))) as ex:
        for (s, _), (fs, n) in zip(ps, ex.map(one, ps)):
            stats["parents"] += 1; stats["skipped_deadline"] += n == -1; stats["failed"] += n == -2
            stats["picked"] += max(n, 0); stats["forks"] += len(fs); forks += fs
    for f in forks:
        stats["kind_" + f["kind"]] += 1
    with gzip.open(outp, "wt") as f:
        json.dump(forks, f)
    print("forks made:", dict(stats), flush=True)


# ---------- pairs ----------
def pairs(tokd, envp, resp, forksp, outp, day, fixes):
    tok = load_tok(tokd); env = json.load(open(envp)); cap = int(E("MAXTOK_PAIR", 12288)); maxp = int(E("FORK_MAX_PAIRS", 200))
    meta = {f["fork_id"]: f for f in json.load(gzip.open(forksp, "rt"))}; par = {s["id"]: s for s, _ in parents(day, fixes)}
    st = collections.Counter(); rows = []
    for l in open(resp):
        r = json.loads(l); f = meta[r["fork_id"]]; s = r["sim"]; st["fork_runs"] += 1
        if not real(s):
            st["not_real"] += 1; continue
        if ok(s) == f["parent_ok"]:
            st["same_outcome"] += 1; continue
        st["differs"] += 1; st["fork_passes" if ok(s) else "fork_fails"] += 1
        try:
            a, b = render_traj(tok, env, par[f["parent"]]["messages"]), render_traj(tok, env, s["messages"])
        except Exception as e:
            st["render_error"] += 1; print("render error", r["fork_id"], str(e)[:100]); continue
        (c, rj) = (b, a) if ok(s) else (a, b)
        if max(len(c[0]), len(rj[0])) > cap:
            st["dropped_over_%d" % cap] += 1; continue
        at = next((i for i, (x, y) in enumerate(zip(c[0], rj[0])) if x != y), None)
        if at is None:
            st["no_divergence"] += 1; continue
        rows.append({"kind": "fpair", "task": f["task_id"], "fork_at": at, "fork_kind": f["kind"], "fork_id": f["fork_id"],
                     "chosen": {"ids": c[0], "mask": c[1]}, "rejected": {"ids": rj[0], "mask": rj[1]}})
    random.Random(0).shuffle(rows); st["pairs_before_cap"] = len(rows); rows = rows[:maxp]; st["pairs"] = len(rows)
    for r in rows:
        st["pair_kind_" + r["fork_kind"]] += 1
    with open(outp, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    json.dump(dict(st), open(os.path.splitext(outp)[0] + "_stats.json", "w"), indent=1); print("fork pairs:", dict(st))


if __name__ == "__main__":
    cmd, a = sys.argv[1], sys.argv[2:]
    {"make": lambda: make(a[0], a[1], a[2], a[3], a[4:]), "pairs": lambda: pairs(*a[:5], a[5], a[6:])}[cmd]()
