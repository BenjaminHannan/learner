"""Probe writer on MLX (Addendum 1): K2-Horizon-3.7B bf16 (+ optional LoRA adapter) writes 4 test sets per target task, as ../../probe1/write_probes.py does against vLLM:
the same prompt (task_prompt(task, with_state=True), the k2_nothink template, generation prompt), T 0.7, top_p 0.95, max 768 new tokens, 4 samples per task, output rows made by
write_probes.record("k2", ...) so analyze.py reads them unchanged.
  tuned:  gen_mlx.py --arm tuned --adapter OUT/train/adapter --out-dir OUT          -> OUT/probes_k2.jsonl
  base:   gen_mlx.py --arm base --out-dir OUT                                         -> OUT/probes_k2base_mlx.jsonl    (the MLX-BASE control, no adapter)
Resumable: rows already in the output file (task|sample) are skipped; rerun the same command. Uses mlx_lm's batch_generate when this mlx-lm has it, else one sequence at a time.
Smoke (CPU): --tiny --limit-tasks 1 --max-tokens 16"""
import argparse, json, os, sys, time, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlx_common as C
import write_probes as wp
import mlx.core as mx

OUT_NAMES = C.OUT_NAMES


class TokShim:
    """The two things batch_generate wants from a tokenizer. Decoding drops special tokens, as vLLM's default does."""

    def __init__(self, tok, eos_ids):
        self.tok, self.eos_token_ids = tok, list(eos_ids)

    def decode(self, ids):
        return self.tok.decode(ids, skip_special_tokens=True)


def generate_sequential(net, shim, prompts, max_tokens, sampler):
    from mlx_lm.generate import generate_step
    outs, stops = [], set(shim.eos_token_ids)
    for p in prompts:
        toks = []
        for t, _ in generate_step(mx.array(p), net, max_tokens=max_tokens, sampler=sampler):
            t = int(t)
            if t in stops:
                break
            toks.append(t)
        outs.append(toks)
        mx.clear_cache()
    return outs


def generate_batch(net, shim, prompts, max_tokens, sampler):
    from mlx_lm.generate import batch_generate
    r = batch_generate(net, shim, prompts, max_tokens=max_tokens, sampler=sampler, return_token_ids=True,
                       completion_batch_size=max(len(prompts), 1), prefill_batch_size=min(len(prompts), 4) or 1)
    return [list(t) for t in r.token_ids]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=sorted(OUT_NAMES), help="tuned -> probes_k2.jsonl, base -> probes_k2base_mlx.jsonl")
    ap.add_argument("--adapter", default=None, help="adapter dir from train_mlx.py (required for --arm tuned, refused for --arm base)")
    ap.add_argument("--out-dir", default=C.P3)
    ap.add_argument("--out", default=None, help="explicit output file instead of the --arm name in --out-dir")
    ap.add_argument("--results", default=wp.DEFAULT_RESULTS, help="Guess-1 run dir; its target.json names the 48 tasks")
    ap.add_argument("--tasks", default="", help="comma-separated task ids instead of target.json (smoke tests)")
    ap.add_argument("--limit-tasks", type=int, default=0)
    ap.add_argument("--model", default=C.MODEL)
    ap.add_argument("--revision", default=None)
    ap.add_argument("--tiny", action="store_true", help="smoke test: random-init tiny model of the same architecture")
    ap.add_argument("--samples", type=int, default=wp.N_SAMPLES)
    ap.add_argument("--max-tokens", type=int, default=768)
    ap.add_argument("--batch-tasks", type=int, default=2, help="tasks generated together (x4 samples each = sequences in flight)")
    ap.add_argument("--sequential", action="store_true", help="do not use mlx_lm batch_generate")
    ap.add_argument("--mem-limit-gb", type=float, default=0)
    ap.add_argument("--max-pressure", type=int, default=1, help="macOS memory-pressure level above which to exit 75 (rerun to resume)")
    a = ap.parse_args()
    if a.arm == "tuned" and not a.adapter:
        sys.exit("--arm tuned needs --adapter")
    if a.arm == "base" and a.adapter:
        sys.exit("--arm base is the untuned control: no --adapter")
    out = a.out or os.path.join(a.out_dir, OUT_NAMES[a.arm])
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tasks = wp.select_tasks(a.results, [x for x in a.tasks.split(",") if x] or None)[:a.limit_tasks or None]
    done = {r["key"] for r in C.read_jsonl(out)} if os.path.exists(out) else set()
    todo = [(t, s) for t in tasks for s in range(a.samples) if f"{t['id']}|{s}" not in done]
    print(f"arm {a.arm}: {len(tasks) * a.samples} samples, {len(done)} done, {len(todo)} to write -> {out}", flush=True)
    if not todo:
        return 0
    C.set_memory(a.mem_limit_gb)
    tok, tpl = C.hf_tokenizer(a.model), open(C.TEMPLATE).read()
    t0 = time.time()
    net, cfg = C.load_k2(a.model, tiny=a.tiny, adapter=a.adapter, revision=a.revision)
    net.eval()
    stops = C.stop_ids(tok, cfg.get("eos_token_id") if isinstance(cfg, dict) else None)
    shim = TokShim(tok, stops)
    print(f"model loaded in {time.time() - t0:.0f}s (adapter: {a.adapter}); stop ids {stops}; peak {C.peak_gb():.1f} GB", flush=True)
    from mlx_lm.sample_utils import make_sampler
    sampler = make_sampler(temp=wp.TEMPERATURE, top_p=wp.TOP_P)
    try:
        from mlx_lm.generate import batch_generate  # noqa
        batched = not a.sequential
    except ImportError:
        batched = False
    print("generation:", "mlx_lm.batch_generate" if batched else "sequential generate_step", flush=True)
    gen = generate_batch if batched else generate_sequential
    byt = {}
    for t, s in todo:
        byt.setdefault(t["id"], (t, []))[1].append(s)
    groups = list(byt.values())
    fh, side = open(out, "a"), open(os.path.splitext(out)[0] + ".genlog.jsonl", "a")
    n = 0
    for i in range(0, len(groups), a.batch_tasks):
        ok, msg = C.pressure_ok(a.max_pressure)
        if not ok:
            print(f"PAUSED after {n} samples: {msg}. Rerun the same command to resume.", flush=True)
            return C.EXIT_PRESSURE
        chunk = [(t, s) for t, ss in groups[i:i + a.batch_tasks] for s in ss]
        prompts = [C.prompt_ids(tok, tpl, wp.task_prompt(t, with_state=True)) for t, _ in chunk]
        mx.random.seed(wp.job_seed(chunk[0][0]["id"], chunk[0][1]))
        t1 = time.time()
        outs = gen(net, shim, prompts, a.max_tokens, sampler)
        sec = time.time() - t1
        rows, logs = C.make_rows(chunk, prompts, outs, tok, a.max_tokens)
        fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        side.writelines(json.dumps(r) + "\n" for r in logs)
        fh.flush(), side.flush()
        n += len(chunk)
        new = sum(len(x) for x in outs)
        print(f"[{n}/{len(todo)}] {len(chunk)} seqs, prompts {sum(len(p) for p in prompts)} tok, {new} new tok, {sec:.0f}s ({new / max(sec, 1e-9):.1f} new tok/s), peak {C.peak_gb():.1f} GB", flush=True)
        mx.clear_cache()
    print(f"wrote {n} samples -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
