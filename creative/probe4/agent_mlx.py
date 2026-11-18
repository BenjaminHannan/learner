"""K2-Horizon tool-calling episodes on MLX, reproducing Guess-1's episode loop (reach1/episode.py): system prompt + user message, up to 6 assistant turns in a fresh World, tool results fed back
through the k2_nothink template, success = all task checks pass. Many episodes run in lockstep rounds: one turn for every live episode as one mlx_lm batch, apply the tools, repeat.
Tool-call text = the "xml" format of the template, parsed as vLLM's k2_horizon parser does (see parse_k2). Records are in Guess-1's results.jsonl format (arm IND), so pools/replay/analyze read them.
Usage: agent_mlx.py --tasks tasks_new.jsonl --out DIR [--tries 12] [--batch 12] [--mem-limit-gb 24]     Resumable: finished (task, try) pairs in DIR/results.jsonl are skipped; exit 75 = memory pressure, rerun.
Smoke (CPU): --tiny --limit-tasks 1 --tries 2 --max-tokens 16"""
import argparse, collections, hashlib, json, math, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p4common as P
import mlx_common as C
from p4common import World, TOOLS, run_checks

# ---------- K2 tool-call text -> calls (port of vllm/tool_parsers/k2_horizon_tool_parser.py, tool_call_format "xml", the server default) ----------
CS, CE, TS, TE = "<ifm|tool_calls>", "</ifm|tool_calls>", "<ifm|tool_call>", "</ifm|tool_call>"
KS, KE, VS, VE = "<ifm|arg_key>", "</ifm|arg_key>", "<ifm|arg_value>", "</ifm|arg_value>"
CALL_RE = re.compile(re.escape(TS) + r"(.*?)" + re.escape(TE), re.S)
ARG_RE = re.compile(re.escape(KS) + r"(.*?)" + re.escape(KE) + r"\s*" + re.escape(VS) + r"(.*?)" + re.escape(VE), re.S)
MARKERS = (KS, KE, VS, VE, "<ifm|arg_type>", "</ifm|arg_type>")
ALIAS = {"str": "string", "text": "string", "int": "integer", "long": "integer", "float": "number", "double": "number", "bool": "boolean", "dict": "object", "list": "array", "arr": "array"}


def _finite(o):
    if isinstance(o, float):
        return math.isfinite(o)
    if isinstance(o, dict):
        return all(_finite(v) for v in o.values())
    if isinstance(o, list):
        return all(_finite(v) for v in o)
    return True


def schema_types(spec):
    """vLLM extract_types_from_schema for the shapes our tools use (type / enum / anyOf)."""
    if not isinstance(spec, dict):
        return ["string"]
    t = spec.get("type")
    ts = {t} if isinstance(t, str) else {x for x in t if isinstance(x, str)} if isinstance(t, list) else set()
    for v in spec.get("enum") or []:
        ts.add("null" if v is None else "boolean" if isinstance(v, bool) else "integer" if isinstance(v, int) else "number" if isinstance(v, float) else "string" if isinstance(v, str) else "array" if isinstance(v, list) else "object")
    for k in ("anyOf", "oneOf", "allOf"):
        for c in spec.get(k) or []:
            ts.update(schema_types(c))
    return list(ts) or ["string"]


def coerce(value, types):
    """vLLM coerce_to_schema_type: priority null > integer > number > boolean > object > array > string; falls back to json.loads, then the raw string."""
    ts = {ALIAS.get(t.strip().lower(), t.strip().lower()) for t in types}
    for c in ("null", "integer", "number", "boolean", "object", "array", "string"):
        if c not in ts:
            continue
        if c == "null":
            if value.lower() == "null":
                return None
        elif c == "string":
            return value
        elif c in ("integer", "number"):
            try:
                return int(value)
            except ValueError:
                pass
            if c == "number":
                try:
                    f = float(value)
                except ValueError:
                    continue
                if math.isfinite(f):
                    return f if f != int(f) else int(f)
        elif c == "boolean":
            if value.lower().strip() in ("true", "1"):
                return True
            if value.lower().strip() in ("false", "0"):
                return False
        else:
            try:
                v = json.loads(value)
            except ValueError:
                continue
            if _finite(v):
                return v
    try:
        v = json.loads(value)
    except ValueError:
        return value
    return v if _finite(v) else value


def parse_k2(text, tools=TOOLS):
    """Model output -> dict(content, calls=[{name, arguments(dict)}]). Like the server: no complete <ifm|tool_calls> group, a malformed group, an unknown tool name or a duplicate / malformed
    argument anywhere in the group -> NO calls and the whole text stays the content. Otherwise content = the text before and after the group."""
    props = {t["function"]["name"]: t["function"]["parameters"].get("properties", {}) for t in tools}
    none = dict(content=(text or "").strip(), calls=[])
    gs = (text or "").find(CS)
    if gs < 0:
        return none
    b0 = gs + len(CS)
    ge = text.find(CE, b0)
    if ge < 0:
        return none
    body = text[b0:ge]
    ms = list(CALL_RE.finditer(body))
    if not ms or CALL_RE.sub("", body).strip():
        return none
    calls = []
    try:
        for m in ms:
            b = m.group(1)
            first = b.find(KS)
            if first < 0:
                if any(k in b for k in MARKERS):
                    raise ValueError("malformed arg tags")
                name, args = b.strip(), {}
            else:
                name, args, pos = b[:first].strip(), {}, first
                for a in ARG_RE.finditer(b, first):
                    if b[pos:a.start()].strip():
                        raise ValueError("malformed arg tags")
                    k = a.group(1).strip()
                    if not k or k in args:
                        raise ValueError("bad or duplicate arg name")
                    if name not in props:
                        raise ValueError("unknown tool")
                    ty = schema_types(props[name].get(k))
                    args[k] = coerce(a.group(2) if "string" in ty else a.group(2).strip(), ty)
                    pos = a.end()
                if pos == first or b[pos:].strip():
                    raise ValueError("malformed arg tags")
            if not name or any(c.isspace() for c in name) or name not in props:
                raise ValueError("unknown tool")
            calls.append(dict(name=name, arguments=args))
    except ValueError:
        return none
    return dict(content=(text[:gs] + text[ge + len(CE):]).strip(), calls=calls)


def template_msgs(msgs):
    """Stored messages (Guess-1 format: arguments as JSON strings) -> what the template needs (arguments as dicts)."""
    out = []
    for m in msgs:
        m = dict(m)
        if m.get("tool_calls"):
            m["tool_calls"] = [dict(c, function=dict(c["function"], arguments=json.loads(c["function"]["arguments"]) if isinstance(c["function"]["arguments"], str) else c["function"]["arguments"])) for c in m["tool_calls"]]
        out.append(m)
    return out


def make_render(tok, tpl, tools=TOOLS):
    """-> f(stored messages) = token ids of the prompt (template + tools + generation prompt; thinking off), as vLLM would build it."""
    def f(msgs):
        text = tok.apply_chat_template(template_msgs(msgs), tools=tools, chat_template=tpl, add_generation_prompt=True, tokenize=False)
        return tok(text, add_special_tokens=False)["input_ids"]
    return f


# ---------- episodes ----------
class Episode:
    def __init__(self, task, try_idx):
        self.task, self.try_idx, self.key = task, try_idx, f"{task['id']}|{try_idx}"
        self.world = World.from_json(task["state"])
        self.msgs = [dict(role="system", content=P.SYSTEM.format(today=self.world.today)), dict(role="user", content=task["user"])]
        self.n, self.reply, self.done, self.hit_max = 0, "", False, 0
        self.tokens = {"prompt": 0, "completion": 0}

    def step(self, text, n_prompt, n_new, hit_max=False):
        """One assistant turn from raw model text. Mirrors reach1/episode.run_episode (ids, message format, 6-turn cap with reply '' if still calling tools)."""
        self.n += 1
        self.tokens["prompt"] += n_prompt
        self.tokens["completion"] += n_new
        self.hit_max += bool(hit_max)
        out = parse_k2(text)
        content, calls = P.strip_markup(out["content"]), out["calls"]
        m = dict(role="assistant", content=content)
        if calls:
            m["tool_calls"] = [dict(id="chatcmpl-tool-" + hashlib.sha256(f"{self.key}|{self.n}|{i}".encode()).hexdigest()[:16], type="function",
                                    function=dict(name=c["name"], arguments=json.dumps(c["arguments"]))) for i, c in enumerate(calls)]
        self.msgs.append(m)
        self.reply = content
        if not calls:
            self.done = True
            return
        for tc, c in zip(m["tool_calls"], calls):
            self.msgs.append(dict(role="tool", tool_call_id=tc["id"], name=c["name"], content=self.world.call(c["name"], c["arguments"])))
        if self.n >= P.MAX_TURNS:
            self.reply, self.done = "", True    # ran out of turns while still calling tools: no final reply

    def abort(self):
        self.reply, self.done = "", True

    def record(self):
        checks = run_checks(self.task, self.world, self.reply)
        return dict(task_id=self.task["id"], scenario=self.task["scenario"], arm=P.ARM, try_idx=self.try_idx, success=bool(checks) and all(checks), checks=checks,
                    transcript=self.msgs[1:], n_turns=self.n, tokens=self.tokens, final_reply=self.reply, reply_log=P.THINK_RE.sub("", self.reply or "").strip(),
                    extra_block=None, trap=bool(self.task.get("trap")), turns_hit_max=self.hit_max)


def drive(todo, render, generate, decode, batch, on_done, max_tokens=512, max_prompt=16000, pause=None, log=print):
    """todo: [(task, try_idx)] in order. render(msgs)->ids; generate([ids])->[[token ids]] (stop token excluded); decode(ids)->text; on_done(record) is called once per finished episode.
    pause() -> message or None is checked before each round. Returns the number of finished episodes, or None if paused (unfinished episodes are dropped and redone on rerun)."""
    queue, live, rnd, nfin, t0 = collections.deque(todo), [], 0, 0, time.time()
    while queue or live:
        msg = pause() if pause else None
        if msg:
            log(f"PAUSED after {nfin} episodes: {msg}. Rerun the same command to resume.")
            return None
        while len(live) < batch and queue:
            live.append(Episode(*queue.popleft()))
        prompts = [render(e.msgs) for e in live]
        for e, p in zip(live, prompts):
            if len(p) > max_prompt:
                e.abort()
        run = [(e, p) for e, p in zip(live, prompts) if not e.done]
        if run:
            rnd += 1
            t1 = time.time()
            outs = generate([p for _, p in run])
            for (e, p), o in zip(run, outs):
                hit = len(o) >= max_tokens
                e.step(decode(o), len(p), len(o) + (0 if hit else 1), hit)    # +1: the end-of-turn token vLLM counts as a completion token
            new = sum(len(o) for o in outs)
            log(f"round {rnd}: {len(run)} seqs, prompts {sum(len(p) for _, p in run)} tok, {new} new tok, {time.time() - t1:.0f}s; {len(queue)} queued, {nfin} finished")
        for e in [e for e in live if e.done]:
            on_done(e.record())
            nfin += 1
        live = [e for e in live if not e.done]
    log(f"finished {nfin} episodes in {time.time() - t0:.0f}s")
    return nfin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default=P.TASKS_NEW)
    ap.add_argument("--out", required=True, help="dir; results.jsonl is written there (Guess-1 format)")
    ap.add_argument("--tries", type=int, default=P.N_TRIES)
    ap.add_argument("--batch", type=int, default=12, help="episodes in flight (one turn each per round)")
    ap.add_argument("--limit-tasks", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=P.SAMPLING["max_tokens"])
    ap.add_argument("--model", default=C.MODEL)
    ap.add_argument("--revision", default=None)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--tiny", action="store_true", help="smoke test: random-init tiny model of the same architecture")
    ap.add_argument("--sequential", action="store_true", help="do not use mlx_lm batch_generate")
    ap.add_argument("--mem-limit-gb", type=float, default=0)
    ap.add_argument("--max-pressure", type=int, default=1, help="macOS memory-pressure level above which to exit 75 (rerun to resume)")
    a = ap.parse_args()
    tasks = P.load_tasks(a.tasks)[:a.limit_tasks or None]
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, "results.jsonl")
    done = {(r["task_id"], r["try_idx"]) for r in P.read_jsonl(path) if r["arm"] == P.ARM}
    todo = [(t, i) for t in tasks for i in range(a.tries) if (t["id"], i) not in done]
    print(f"{len(tasks)} tasks x {a.tries} tries: {len(done)} done, {len(todo)} to run -> {path}", flush=True)
    if not todo:
        return 0
    import mlx.core as mx
    import gen_mlx as G
    from mlx_lm.sample_utils import make_sampler
    C.set_memory(a.mem_limit_gb)
    tok, tpl = C.hf_tokenizer(a.model), open(C.TEMPLATE).read()
    t0 = time.time()
    net, cfg = C.load_k2(a.model, tiny=a.tiny, adapter=a.adapter, revision=a.revision)
    net.eval()
    stops = C.stop_ids(tok, cfg.get("eos_token_id") if isinstance(cfg, dict) else None)
    shim = G.TokShim(tok, stops)
    print(f"model loaded in {time.time() - t0:.0f}s; stop ids {stops}; peak {C.peak_gb():.1f} GB", flush=True)
    sampler = make_sampler(temp=P.SAMPLING["temperature"], top_p=P.SAMPLING["top_p"])
    try:
        from mlx_lm.generate import batch_generate  # noqa
        gen = G.generate_sequential if a.sequential else G.generate_batch
    except ImportError:
        gen = G.generate_sequential
    rounds = [0]

    def generate(prompts):
        rounds[0] += 1
        mx.random.seed(P.crc(f"probe4|{rounds[0]}|{len(prompts)}|{len(done)}|{sum(map(len, prompts))}"))
        outs = gen(net, shim, prompts, a.max_tokens, sampler)
        mx.clear_cache()
        return outs

    fh = open(path, "a")

    def on_done(rec):
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()

    def pause():
        ok, msg = C.pressure_ok(a.max_pressure)
        return None if ok else msg

    n = drive(todo, make_render(tok, tpl), generate, lambda ids: tok.decode(ids, skip_special_tokens=True), a.batch, on_done, a.max_tokens, pause=pause,
              log=lambda s: print(s + f", peak {C.peak_gb():.1f} GB", flush=True))
    return C.EXIT_PRESSURE if n is None else 0


if __name__ == "__main__":
    sys.exit(main())
