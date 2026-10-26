"""Play forked conversations in tau2 (tau2 venv). Usage: forks_run.py DOMAIN SPLIT FORKS.json.gz OUT.jsonl CONC DEADLINE_EPOCH AGENT_ARGS_JSON
Each fork becomes a copy of its tau2 task whose initial_state.message_history is: the parent's messages before the forked turn, the forked assistant
message, and (if that turn made tool calls) the tool results, run here on a fresh environment because tau2 cannot start from a history that ends in a tool call.
The normal agent (the served model) and the normal user simulator then play on, and tau2's own evaluator scores the whole conversation. The evaluator gets the
ORIGINAL task (without the history): a history that ends after a write action would otherwise make the gold run apply that action twice.
One JSON line per finished fork: {fork_id, sim}. Forks start in shuffled order until DEADLINE_EPOCH, so a cut-off run keeps a spread of forks."""
import gzip, json, random, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

import tau2.runner.simulation as rsim
from tau2 import registry
from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage, UserMessage
from tau2.data_model.simulation import TextRunConfig
from tau2.data_model.tasks import InitialState
from tau2.runner.batch import _cleanup_thread_event_loop, _init_thread_event_loop, run_single_task
from tau2.runner.helpers import get_tasks

MSG = {"assistant": AssistantMessage, "user": UserMessage, "tool": ToolMessage}
BASE = {}  # task id -> the original task, for scoring
_eval = rsim.evaluate_simulation


def scored_on_original(*, simulation, task, **kw):
    return _eval(simulation=simulation, task=BASE[task.id], **kw)


rsim.evaluate_simulation = scored_on_original


def fork_task(task, f, domain):
    """-> (task copy with the forked history, history length)."""
    hist = [MSG[m["role"]].model_validate(m) for m in f["history"]]
    new = AssistantMessage.model_validate(f["msg"]); st = task.initial_state
    env = registry.get_env_constructor(domain)()
    env.set_state(st.initialization_data if st else None, st.initialization_actions if st else None, hist, strict=False)
    tools = [env.get_response(ToolCall(**tc)) for tc in f["msg"].get("tool_calls") or []]
    t = task.model_copy(deep=True)
    t.initial_state = InitialState(initialization_data=st.initialization_data if st else None, initialization_actions=st.initialization_actions if st else None,
                                   message_history=hist + [new] + tools)
    return t


def main(domain, split, forksp, outp, conc, deadline, args):
    forks = json.load(gzip.open(forksp, "rt")); random.Random(0).shuffle(forks)
    try:  # a rerun after a crash skips the forks that already finished
        done = {json.loads(l)["fork_id"] for l in open(outp)}
    except FileNotFoundError:
        done = set()
    forks = [f for f in forks if f["fork_id"] not in done]; print(f"{len(done)} forks already done, {len(forks)} to play", flush=True)
    cfg = TextRunConfig(domain=domain, agent="llm_agent", llm_agent="openai/m", llm_args_agent=json.loads(args), user="user_simulator",
                        llm_user="anthropic/claude-haiku-5-5", llm_args_user={"num_retries": 6})
    for t in get_tasks(domain, task_split_name=split):
        BASE[t.id] = t
    lock = threading.Lock(); n = [0, 0]; out = open(outp, "a")

    def run(i_f):
        i, f = i_f
        if time.time() > deadline:
            return
        _init_thread_event_loop()
        try:
            sim = run_single_task(cfg, fork_task(BASE[f["task_id"]], f, domain), seed=300 + i)
            d = json.loads(sim.model_dump_json())
            for m in d.get("messages") or []:
                m.pop("raw_data", None)
            d.pop("ticks", None)
            with lock:
                out.write(json.dumps({"fork_id": f["fork_id"], "sim": d}) + "\n"); out.flush(); n[0] += 1
        except Exception as e:
            with lock:
                n[1] += 1
            print("fork failed", f["fork_id"], type(e).__name__, str(e)[:200], flush=True)
        finally:
            _cleanup_thread_event_loop()
    with ThreadPoolExecutor(conc) as ex:
        list(ex.map(run, enumerate(forks)))
    print(f"fork sims done {n[0]} failed {n[1]} of {len(forks)}", flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3], int(a[4]), float(a[5]), a[6])
