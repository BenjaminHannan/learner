"""Cloud-side helper (run once where /mnt/project-files exists): write the small, committed copies of the Probe-3 inputs under probe3/inputs/.
  guess1_run/target.json        copy
  guess1_run/results.jsonl      SLIM: only the rows analyze/replay read (arms IND, IND.s2, MENU, MENU.s2; target tasks; try_idx < 12; first row wins), and per row only
                                task_id, arm, try_idx, success, final_reply and the transcript reduced to {role, tool_calls} of assistant turns (all replay.calls_of reads)
  pick1/k2_scores.jsonl         copy (Pick-1 SELF scores)
  pick1/pools.jsonl             copy (so pick1/pools.py and its Guess-1 dependencies are not needed on the Mac)
  haiku_train_probes.jsonl      copy (Haiku batch output for the training tasks)
  MANIFEST.json                 sizes and sha256
Usage: make_inputs.py [--mnt /mnt/project-files/creative/] [--out ../inputs]"""
import argparse, hashlib, json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "probe1"))
from probe_common import ARMS, N_TRIES  # noqa


def slim_results(src, dst, targets):
    seen, n_in, n_out = set(), 0, 0
    with open(src) as f, open(dst, "w") as g:
        for line in f:
            if not line.strip():
                continue
            n_in += 1
            r = json.loads(line)
            k = (r["task_id"], r["arm"], r["try_idx"])
            if r["arm"] not in ARMS or r["task_id"] not in targets or r["try_idx"] >= N_TRIES or k in seen:
                continue
            seen.add(k)
            tr = [dict(role=m["role"], tool_calls=m["tool_calls"]) for m in r["transcript"] if m["role"] == "assistant" and m.get("tool_calls")]
            g.write(json.dumps(dict(task_id=r["task_id"], arm=r["arm"], try_idx=r["try_idx"], success=r["success"], final_reply=r.get("final_reply"), transcript=tr),
                               ensure_ascii=False, separators=(",", ":")) + "\n")
            n_out += 1
    return n_in, n_out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mnt", default="/mnt/project-files/creative/")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "inputs"))
    a = ap.parse_args()
    run = os.path.join(a.mnt, "guess1/out-seed2/guess1-seed2/run/")
    os.makedirs(os.path.join(a.out, "guess1_run"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "pick1"), exist_ok=True)
    tj = os.path.join(a.out, "guess1_run", "target.json")
    shutil.copy(run + "target.json", tj)
    print("results rows in/out:", slim_results(run + "results.jsonl", os.path.join(a.out, "guess1_run", "results.jsonl"), set(json.load(open(tj))["T"])))
    shutil.copy(a.mnt + "pick1/out/pick1/k2_scores.jsonl", os.path.join(a.out, "pick1", "k2_scores.jsonl"))
    shutil.copy(a.mnt + "pick1/pools.jsonl", os.path.join(a.out, "pick1", "pools.jsonl"))
    shutil.copy(a.mnt + "probe3/data/haiku_train_probes.jsonl", os.path.join(a.out, "haiku_train_probes.jsonl"))
    man = {}
    for d, _, fs in os.walk(a.out):
        for f in sorted(fs):
            if f != "MANIFEST.json":
                p = os.path.join(d, f)
                man[os.path.relpath(p, a.out)] = dict(bytes=os.path.getsize(p), sha256=hashlib.sha256(open(p, "rb").read()).hexdigest())
    json.dump(man, open(os.path.join(a.out, "MANIFEST.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps({k: v["bytes"] for k, v in man.items()}, indent=1), "total", sum(v["bytes"] for v in man.values()))


if __name__ == "__main__":
    main()
