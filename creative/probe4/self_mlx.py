"""SELF judge on MLX: K2 reads the compact transcript and "Did the assistant fully and correctly do what the user asked, ...? Answer yes or no."; score = P(yes) / (P(yes) + P(no)) over the
top-20 first-token candidates, as pick1/judge_k2.py gets from vLLM (user message only, no tools, thinking-off generation prompt, greedy, max_tokens 1). Output rows {key, p_yes, n_prompt} as k2_scores.jsonl.
Usage: self_mlx.py --tries DIR/results.jsonl --tasks tasks_new.jsonl --pools DIR/pools.jsonl --out DIR/self_scores.jsonl [--mem-limit-gb 24]   Resumable; exit 75 = memory pressure.
Smoke (CPU): --tiny --limit 3"""
import argparse, json, math, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p4common as P
import mlx_common as C

TOPK = 20
_common = P.load_pick1("common")
judge_prompt = _common.judge_prompt   # f"{judge_text}\n\n{QUESTION}" -- Pick-1's own function and question


def p_yes_from_logits(logits, decode, topk=TOPK):
    """logits: 1-D float array over the vocab (numpy). -> P(yes)/(P(yes)+P(no)) among the topk tokens by logprob (Pick-1's rule: tokens whose stripped, lower-cased text is yes / no); None if neither is there."""
    import numpy as np
    lg = np.asarray(logits, dtype=np.float64)
    lp = lg - (lg.max() + math.log(np.exp(lg - lg.max()).sum()))
    ids = np.argsort(-lp, kind="stable")[:topk]
    yes = no = 0.0
    for i in ids:
        w = decode(int(i)).strip().lower()
        if w == "yes":
            yes += math.exp(lp[i])
        elif w == "no":
            no += math.exp(lp[i])
    return yes / (yes + no) if yes + no > 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tries", required=True, help="results.jsonl from agent_mlx.py")
    ap.add_argument("--tasks", default=P.TASKS_NEW)
    ap.add_argument("--pools", required=True, help="pools.jsonl: written from --tries if missing")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default=C.MODEL)
    ap.add_argument("--revision", default=None)
    ap.add_argument("--tiny", action="store_true")
    ap.add_argument("--mem-limit-gb", type=float, default=0)
    ap.add_argument("--max-pressure", type=int, default=1)
    ap.add_argument("--max-prompt", type=int, default=12000)
    a = ap.parse_args()
    if not os.path.exists(a.pools):
        ids = {t["id"] for t in P.load_tasks(a.tasks)}
        recs = P.build_pools(P.read_jsonl(a.tries), ids)
        C.atomic_write(a.pools, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
        print(f"built {len(recs)} pool members -> {a.pools}", flush=True)
    recs = P.read_jsonl(a.pools)[:a.limit or None]
    done = {r["key"] for r in P.read_jsonl(a.out)}
    todo = [r for r in recs if P.pool_key(r) not in done]
    print(f"{len(recs)} tries, {len(done)} judged, {len(todo)} to judge -> {a.out}", flush=True)
    if not todo:
        return 0
    import numpy as np
    import mlx.core as mx
    C.set_memory(a.mem_limit_gb)
    tok, tpl = C.hf_tokenizer(a.model), open(C.TEMPLATE).read()
    net, _ = C.load_k2(a.model, tiny=a.tiny, revision=a.revision)
    net.eval()
    body, head = C.backbone_and_head(net)
    dec = lambda i: tok.decode([i], skip_special_tokens=False)   # noqa
    fh, t0 = open(a.out, "a"), time.time()
    for n, r in enumerate(todo, 1):
        if n % 10 == 1:
            ok, msg = C.pressure_ok(a.max_pressure)
            if not ok:
                print(f"PAUSED after {n - 1} judgments: {msg}. Rerun the same command to resume.", flush=True)
                return C.EXIT_PRESSURE
        ids = C.prompt_ids(tok, tpl, judge_prompt(r["judge_text"]))
        if len(ids) > a.max_prompt:
            ids = ids[:1] + ids[-(a.max_prompt - 1):]    # absurdly long transcript: keep the end, where the question is
        h = body(mx.array([ids]))[:, -1]
        lg = head(h)[0].astype(mx.float32)
        mx.eval(lg)
        p = p_yes_from_logits(np.array(lg), dec)
        fh.write(json.dumps(dict(key=P.pool_key(r), p_yes=p, n_prompt=len(ids))) + "\n")
        fh.flush()
        mx.clear_cache()
        if n % 50 == 0:
            print(f"{n}/{len(todo)} {time.time() - t0:.0f}s peak {C.peak_gb():.1f} GB", flush=True)
    print(f"judged {len(todo)} in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
