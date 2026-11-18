"""J-D1: Liquid AI d1-3B (official GGUF, llama-server /v1/systemone, no remote code). The state is the request + start state (p6common.judge_state_text);
one typed 'noul' (yes/no) question; P(ask) = answers.ask.noul. Usage: judge_d1.py --tasks dev|file.jsonl --out scores.jsonl [--url http://127.0.0.1:8081]  Resumable."""
import argparse, json, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p6common as C

D1_QUESTION = "Should the assistant ask the user a question before acting on this request?"


def ask(url, task):
    body = dict(state=C.judge_state_text(task), questions=dict(ask=dict(type="noul", instructions=D1_QUESTION)))
    req = urllib.request.Request(url + "/v1/systemone", json.dumps(body).encode(), {"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=1800))
    return r["answers"]["ask"]["noul"], r["usage"]["input_tokens"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="dev")
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", default="http://127.0.0.1:8081")
    a = ap.parse_args()
    tasks = sum(C.dev_tasks(), []) if a.tasks == "dev" else C.read_jsonl(a.tasks)
    done = {r["task"] for r in C.read_jsonl(a.out)} if os.path.exists(a.out) else set()
    with open(a.out, "a") as f:
        for t in tasks:
            if t["id"] in done:
                continue
            p, n = ask(a.url, t)
            f.write(json.dumps(dict(task=t["id"], p_ask=p, n_prompt=n)) + "\n")
            f.flush()
            print(t["id"], p, n, flush=True)


if __name__ == "__main__":
    main()
