"""Test writer on llama-server (Probe-3 gen_mlx.py's job): LFM3-1.7B writes 4 end-state test sets per task with the Probe-2 prompt (write_probes.task_prompt(task, with_state=True)), T0.7, top_p 0.95,
max 768 new tokens, thinking off (any text up to </think> is cut). Rows are made by write_probes.record(...) so analyze.py / analyze_e2e.py read them unchanged; a side file
<out>.genlog.jsonl carries {key, prompt_tokens, new_tokens, hit_max} (what analyze_e2e's token table reads).
  base:   gen_tests_lfm3.py --arm base  --tasks-file ../probe4/tasks_new.jsonl --out-dir DIR     -> DIR/probes_lfm3base.jsonl   (adapter scale 0.0: TEST-B)
  tuned:  gen_tests_lfm3.py --arm tuned --tasks-file ../probe4/tasks_new.jsonl --out-dir DIR     -> DIR/probes_lfm3.jsonl      (adapter scale 1.0: TEST-T; the server must have been started with --lora)
Resumable: rows already in the output (task|sample) are skipped. Exit 75 = ASSISTANT_RUNNING appeared."""
import argparse, concurrent.futures as cf, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5common as C
import write_probes as wp
from llm_server import ServerError

P = C.P
OUT_NAMES = dict(tuned="probes_lfm3.jsonl", base="probes_lfm3base.jsonl")
SCALES = dict(tuned=1.0, base=0.0)


def write_one(client, task, s, scale, max_tokens):
    """-> (probe row, genlog row). A refused request (prompt over the context) becomes an empty reply, which the analysis counts as an unparsable sample."""
    prompt = wp.task_prompt(task, with_state=True)
    try:
        rep = client.chat([dict(role="user", content=prompt)], None, temperature=C.TEST_SAMPLING["temperature"], top_p=C.TEST_SAMPLING["top_p"], max_tokens=max_tokens,
                          seed=wp.job_seed(task["id"], s), lora_scale=scale)
        text, n_prompt, n_new, hit = rep.content, rep.prompt_tokens, rep.completion_tokens, rep.hit_max     # content: </think> cut, stripped
    except ServerError as e:
        print(f"{task['id']}|{s}: server refused: {e}", flush=True)
        text, n_prompt, n_new, hit = "", 0, 0, False
    row = wp.record("lfm3", task["id"], s, text)
    return row, dict(key=row["key"], prompt_tokens=n_prompt, new_tokens=n_new, hit_max=hit)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=sorted(OUT_NAMES))
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--tasks-file", default=C.TASKS)
    ap.add_argument("--limit-tasks", type=int, default=0)
    ap.add_argument("--samples", type=int, default=C.N_SAMPLES)
    ap.add_argument("--max-tokens", type=int, default=C.TEST_SAMPLING["max_tokens"])
    C.add_server_args(ap)
    a = ap.parse_args()
    out = os.path.join(a.out_dir, OUT_NAMES[a.arm])
    os.makedirs(a.out_dir, exist_ok=True)
    tasks = wp.select_tasks(None, None, tasks_file=a.tasks_file)[:a.limit_tasks or None]
    done = {r["key"] for r in C.read_jsonl(out)}
    todo = [(t, s) for t in tasks for s in range(a.samples) if f"{t['id']}|{s}" not in done]
    print(f"arm {a.arm} (adapter scale {SCALES[a.arm]}): {len(tasks) * a.samples} samples, {len(done)} done, {len(todo)} to write -> {out}", flush=True)
    if not todo:
        return 0
    client = C.make_client(a)
    if not client.healthy():
        print("llama-server is not answering at", a.url)
        return 2
    fh, side, t0, n, paused, it = open(out, "a"), open(os.path.splitext(out)[0] + ".genlog.jsonl", "a"), time.time(), 0, None, iter(todo)
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        running = set()
        while True:
            while len(running) < a.parallel and not paused:
                paused = f"{C.flag_path()} exists" if (not a.no_pause_flag and C.assistant_running()) else None
                j = None if paused else next(it, None)
                if j is None:
                    break
                running.add(ex.submit(write_one, client, j[0], j[1], SCALES[a.arm], a.max_tokens))
            if not running:
                break
            fin, running = cf.wait(running, return_when=cf.FIRST_COMPLETED)
            for f in fin:
                row, log = f.result()
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                side.write(json.dumps(log) + "\n")
                fh.flush(), side.flush()
                n += 1
                if n % 24 == 0:
                    print(f"[{n}/{len(todo)}] {time.time() - t0:.0f}s", flush=True)
    print(f"wrote {n} samples in {time.time() - t0:.0f}s -> {out}")
    if paused:
        print(f"PAUSED: {paused}. Rerun the same command to resume.")
        return C.EXIT_PAUSED
    return 0


if __name__ == "__main__":
    sys.exit(main())
