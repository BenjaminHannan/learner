"""LFM3-1.7B tool-calling episodes against a local llama-server: the Probe-4 loop (agent_mlx.py) with the backbone swapped. Same system prompt, tools, sandbox, 6-turn cap, T0.7 / top_p 0.95 / 512 new tokens,
12 tries per task, and the same records (Guess-1 results.jsonl format, arm IND), so replay / pools / analyze_e2e read them unchanged.
Episodes run in threads (--parallel, match llama-server -np); each turn is one /v1/chat/completions call with the adapter at scale 0.0 (the tries are the untuned model).
Usage: agent_lfm3.py --tasks ../probe4/tasks_new.jsonl --out DIR [--tries 12] [--parallel 4] [--url http://127.0.0.1:8080]
Resumable: finished (task, try) pairs in DIR/results.jsonl are skipped. Exit 75 = ASSISTANT_RUNNING appeared (rerun to resume)."""
import argparse, concurrent.futures as cf, hashlib, json, os, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5common as C
import agent_mlx as A
from llm_server import ServerError

P = C.P


class LfmEpisode(A.Episode):
    """Probe-4's Episode, fed already-parsed turns (content, calls) instead of K2 text. Message ids, the 6-turn rule and the record are inherited / identical."""

    def __init__(self, task, try_idx):
        super().__init__(task, try_idx)
        self.sources, self.errors = [], 0

    def step_reply(self, rep):
        """rep: llm_server.Reply (or anything with content, calls, prompt_tokens, completion_tokens, hit_max, source)."""
        self.n += 1
        self.tokens["prompt"] += rep.prompt_tokens
        self.tokens["completion"] += rep.completion_tokens
        self.hit_max += bool(rep.hit_max)
        self.sources.append(rep.source)
        content, calls = P.strip_markup(rep.content), rep.calls
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
            self.reply, self.done = "", True

    def record(self):
        return dict(super().record(), tool_call_sources=self.sources, server_errors=self.errors)


def run_episode(client, task, try_idx, max_tokens=P.SAMPLING["max_tokens"], lora_scale=0.0, tools=None):
    """One try, start to finish. A server error that retrying cannot fix (prompt longer than the slot's context) ends the try with no reply, as an out-of-turns try."""
    ep = LfmEpisode(task, try_idx)
    while not ep.done:
        try:
            rep = client.chat(ep.msgs, tools or P.TOOLS, temperature=P.SAMPLING["temperature"], top_p=P.SAMPLING["top_p"], max_tokens=max_tokens,
                              seed=C.seed_for("agent", ep.key, ep.n), lora_scale=lora_scale)
        except ServerError as e:
            print(f"{ep.key}: server refused turn {ep.n + 1}: {e}", flush=True)
            ep.errors += 1
            ep.abort()
            break
        ep.step_reply(rep)
    return ep.record()


def drive(todo, work, on_done, parallel=4, pause=None, log=print):
    """todo: [(task, try_idx)] in order; work(task, try_idx) -> record; on_done(record) once per finished try (called from the main thread).
    pause() -> message or None is checked before each new episode starts; on pause the running episodes finish, then None is returned. -> number finished."""
    t0, nfin, it = time.time(), 0, iter(todo)
    with cf.ThreadPoolExecutor(parallel) as ex:
        running, paused = set(), None
        while True:
            while len(running) < parallel and not paused:
                paused = pause() if pause else None
                nxt = None if paused else next(it, None)
                if nxt is None:
                    break
                running.add(ex.submit(work, *nxt))
            if not running:
                break
            done, running = cf.wait(running, return_when=cf.FIRST_COMPLETED)
            for f in done:
                on_done(f.result())
                nfin += 1
                if nfin % 12 == 0:
                    log(f"{nfin} finished, {time.time() - t0:.0f}s")
    log(f"finished {nfin} episodes in {time.time() - t0:.0f}s")
    if paused:
        log(f"PAUSED after {nfin} episodes: {paused}. Rerun the same command to resume.")
        return None
    return nfin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default=C.TASKS)
    ap.add_argument("--out", required=True, help="dir; results.jsonl is written there (Guess-1 format)")
    ap.add_argument("--tries", type=int, default=P.N_TRIES)
    ap.add_argument("--limit-tasks", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=P.SAMPLING["max_tokens"])
    ap.add_argument("--lora-scale", type=float, default=0.0, help="adapter scale for the tries (0.0 = untuned model)")
    C.add_server_args(ap)
    a = ap.parse_args()
    tasks = P.load_tasks(a.tasks)[:a.limit_tasks or None]
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, "results.jsonl")
    done = {(r["task_id"], r["try_idx"]) for r in C.read_jsonl(path) if r["arm"] == P.ARM}
    todo = [(t, i) for t in tasks for i in range(a.tries) if (t["id"], i) not in done]
    print(f"{len(tasks)} tasks x {a.tries} tries: {len(done)} done, {len(todo)} to run -> {path}", flush=True)
    if not todo:
        return 0
    client = C.make_client(a)
    if not client.healthy():
        print("llama-server is not answering at", a.url)
        return 2
    json.dump(dict(sampling=P.SAMPLING, max_turns=P.MAX_TURNS, lora_scale=a.lora_scale, tasks_sha256=P.sha256(a.tasks), url=a.url),
              open(os.path.join(a.out, "settings.json"), "w"), indent=1)
    fh, lock = open(path, "a"), threading.Lock()

    def on_done(rec):
        with lock:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()

    pause = None if a.no_pause_flag else (lambda: f"{C.flag_path()} exists" if C.assistant_running() else None)
    n = drive(todo, lambda t, i: run_episode(client, t, i, a.max_tokens, a.lora_scale), on_done, a.parallel, pause)
    return C.EXIT_PAUSED if n is None else 0


if __name__ == "__main__":
    sys.exit(main())
