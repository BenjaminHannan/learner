"""Rebuild each try's end state: apply its transcript's tool calls to a fresh World from the task's start state.
Usage: replay.py --check [--results DIR]   (sanity gate: real task checks on replayed state must reproduce recorded success for >= 99%)"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_common import *  # noqa


def parse_args(a):
    """Same as the Guess-1 client: JSON string -> dict; unparsable string stays a string (the sandbox then reports an error)."""
    if isinstance(a, str):
        try:
            return json.loads(a) if a.strip() else {}
        except json.JSONDecodeError:
            return a
    return a


def calls_of(transcript):
    return [(tc["function"].get("name", ""), parse_args(tc["function"].get("arguments", {})))
            for m in transcript if m["role"] == "assistant" for tc in m.get("tool_calls") or []]


def apply_calls(task, calls, reply):
    w = World.from_json(task["state"])
    for name, args in calls:
        w.call(name, args)
    return w, reply or ""


def replay_try(task, rec):
    """-> (world, final reply) at the end of a recorded try."""
    return apply_calls(task, calls_of(rec["transcript"]), rec.get("final_reply"))


def replay_reference(task):
    """-> (world, reference reply) after the task's reference plan."""
    return apply_calls(task, [(c["name"], c["arguments"]) for c in task["reference"]], task.get("reference_reply"))


def success_of(task, world, reply):
    checks = run_checks(task, world, reply)
    return bool(checks) and all(checks)


def load_rows(results_dir, T=None):
    """Pool-member records of a Guess-1 results dir {(task, arm, try_idx): row}: arms IND/MENU x seeds, try_idx < 12, first row wins."""
    T, out = set(T if T is not None else target_ids(results_dir)), {}
    for r in read_jsonl(os.path.join(results_dir, "results.jsonl")):
        k = (r["task_id"], r["arm"], r["try_idx"])
        if r["arm"] in ARMS and r["task_id"] in T and r["try_idx"] < N_TRIES and k not in out:
            out[k] = r
    return out


def replay_all(rows, tasks):
    """{(task, arm, try_idx): (world, reply)}"""
    byid = {t["id"]: t for t in tasks}
    return {k: replay_try(byid[k[0]], r) for k, r in rows.items()}


def gate(rows, tasks):
    """-> (rate, mismatches, states). A mismatch is a try whose replayed real-check success differs from the recorded one."""
    byid = {t["id"]: t for t in tasks}
    states, bad = replay_all(rows, tasks), []
    for k, r in rows.items():
        w, reply = states[k]
        ok = success_of(byid[k[0]], w, reply)
        if ok != bool(r["success"]):
            bad.append(dict(task=k[0], arm=k[1], try_idx=k[2], recorded=bool(r["success"]), replayed=ok,
                            replayed_checks=run_checks(byid[k[0]], w, reply), recorded_checks=r.get("checks")))
    return (1 - len(bad) / len(rows) if rows else 0.0), bad, states


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="run the sanity gate; exit 1 if the rate is below 99%%")
    ap.add_argument("--results", default=DEFAULT_RESULTS)
    ap.add_argument("--show", type=int, default=20, help="mismatches to print")
    a = ap.parse_args()
    rows = load_rows(a.results)
    rate, bad, _ = gate(rows, load_tasks())
    print(f"replayed {len(rows)} tries; real checks reproduce recorded success for {len(rows) - len(bad)} ({100 * rate:.2f}%); {len(bad)} mismatches")
    for b in bad[:a.show]:
        print(json.dumps(b))
    ok = rate >= GATE
    print("GATE " + ("PASS" if ok else f"FAIL (< {100 * GATE:.0f}%)"))
    sys.exit(0 if ok or not a.check else 1)


if __name__ == "__main__":
    main()
