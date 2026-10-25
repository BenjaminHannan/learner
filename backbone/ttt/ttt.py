"""TTT-1 (see backbone/ttt/PREREG-ttt1.md): test-time training on a puzzle's own examples. Arms: B (base), T (fresh LoRA on this task's demos), C (same recipe on task k+1's demos).

  python backbone/ttt/ttt.py select --out backbone/ttt/tasks100.json
  python backbone/ttt/ttt.py run --tasks backbone/ttt/tasks100.json --shard 0/2 --arms B,T,C --out out/ttt1      # lane 0; lane 1 = --shard 1/2
  python backbone/ttt/ttt.py run --tasks backbone/ttt/tasks100.json --smoke --out /tmp/ttt_smoke               # CPU, tiny random K2, 2 tasks, 3 steps
  python backbone/ttt/ttt.py score --dir out/ttt1
"""
import argparse
import json
import math
import random
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sleep"))
sys.path.insert(0, str(HERE.parent))

K2_REPO, K2_REV = "IFM/K2-Horizon-3.7B", "9d280ff742235796925c9fe3cf243dc1beea5c08"  # same pin as backbone/sleep/brain/sleepb.py
RAW = "https://raw.githubusercontent.com/fchollet/ARC-AGI/master/data/evaluation/"
API = "https://api.github.com/repos/fchollet/ARC-AGI/contents/data/evaluation"
MAX_TOK, N_TASKS = 2000, 100
INSTR = ("Here are example input -> output grids. Find the rule and give the output grid for the test input. "
         "Reply with only the grid, one row per line, digits only.")
LORA_T = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]  # K2 names (checked on the smoke model); train.LORA_TARGETS regex matches the same attn+mlp ones
SYMS = [lambda g: g, lambda g: [list(r) for r in zip(*g[::-1])], lambda g: [r[::-1] for r in g[::-1]], lambda g: [list(r) for r in zip(*g)][::-1],
        lambda g: [r[::-1] for r in g], lambda g: g[::-1], lambda g: [list(r) for r in zip(*g)], lambda g: [list(r) for r in zip(*g[::-1])][::-1]]
# identity, rot90, rot180, rot270, flip lr, flip ud, transpose, anti-transpose (SYMS[7] = transpose of rot90 = reflection over the anti-diagonal)


def gtxt(g):
    return "\n".join("".join(str(v) for v in r) for r in g)


def user_text(demos, test_in):
    s = INSTR + "\n\n"
    for i, d in enumerate(demos, 1):
        s += f"Example {i}\nInput:\n{gtxt(d['input'])}\nOutput:\n{gtxt(d['output'])}\n\n"
    return s + f"Test input:\n{gtxt(test_in)}"


def parse_grid(text):
    rows = []
    for ln in text.strip().splitlines():
        ln = ln.strip()
        if not re.fullmatch(r"\d+", ln):
            break
        rows.append([int(c) for c in ln])
    return rows


# ------------------------------------------------------------------ select
def select(a):
    from transformers import AutoTokenizer
    from sleep1 import Lang
    import torch
    tok = AutoTokenizer.from_pretrained(K2_REPO, revision=K2_REV, trust_remote_code=True)
    L = Lang(tok, False, torch.device("cpu"), k2=True)
    tmp = None
    try:
        with urllib.request.urlopen(urllib.request.Request(API, headers={"User-Agent": "ttt"}), timeout=60) as r:
            ids = sorted(f["name"][:-5] for f in json.load(r) if f["name"].endswith(".json"))
        get = lambda i: json.load(urllib.request.urlopen(RAW + i + ".json", timeout=60))
    except Exception as e:  # API blocked (e.g. a proxy): shallow clone instead
        print(f"github API unavailable ({type(e).__name__}); using git clone", flush=True)
        tmp = tempfile.mkdtemp()
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/fchollet/ARC-AGI.git", tmp + "/r"], check=True)
        d = Path(tmp) / "r/data/evaluation"
        ids = sorted(p.stem for p in d.glob("*.json"))
        get = lambda i: json.load(open(d / f"{i}.json"))
    print(f"{len(ids)} evaluation tasks", flush=True)
    keep, n_ok, lens = [], 0, []
    for i in ids:
        t = get(i)
        n = len(L.ids(L.render(None, user_text(t["train"], t["test"][0]["input"])))) + len(L.ids(gtxt(t["test"][0]["output"])))  # prompt + answer, eos not counted
        if n <= MAX_TOK:
            n_ok += 1
            if len(keep) < N_TASKS:
                keep.append({"id": i, "tokens": n, "train": t["train"], "test": t["test"]})
    lens = [k["tokens"] for k in keep]
    json.dump(keep, open(a.out, "w"))
    print(f"{n_ok} of {len(ids)} tasks pass <= {MAX_TOK} tokens; kept first {len(keep)} by id ({keep[0]['id']} .. {keep[-1]['id']}); tokens min {min(lens)} max {max(lens)} mean {sum(lens)/len(lens):.0f}; wrote {a.out}")


# ------------------------------------------------------------------ run
def train_examples(task, k, steps, L):
    """Leave-one-out x 8 symmetries from `task`'s own demos, shuffled with seed k, cycled to `steps` items -> [(prompt_ids, answer_ids)]."""
    demos = task["train"]
    pool = []
    for q in range(len(demos)):
        ex = [d for j, d in enumerate(demos) if j != q]
        for f in SYMS:
            pool.append(([{"input": f(d["input"]), "output": f(d["output"])} for d in ex], f(demos[q]["input"]), f(demos[q]["output"])))
    random.Random(k).shuffle(pool)
    out = []
    for ex, qi, qo in (pool[s % len(pool)] for s in range(steps)):
        out.append((L.ids(L.render(None, user_text(ex, qi))), L.ids(gtxt(qo)) + [L.eos]))
    return out, len(pool)


def ttt_train(lm, L, exs, k, device, cuda):
    import torch
    import torch.nn.functional as F
    from peft import LoraConfig, get_peft_model
    torch.manual_seed(k)  # same LoRA init for T and C
    pm = get_peft_model(lm, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules=LORA_T, bias="none"))
    params = [p for p in pm.parameters() if p.requires_grad]
    for p in params:
        p.data = p.data.float()  # fp32 LoRA over fp16 base
    opt = torch.optim.AdamW(params, lr=1e-4)
    scaler = torch.amp.GradScaler("cuda") if cuda else None
    pm.train()
    loss_v = float("nan")
    for pi, ai in exs:
        ids = torch.tensor([pi + ai], device=device)
        with torch.autocast("cuda", dtype=torch.float16, enabled=cuda):
            lg = pm(input_ids=ids, use_cache=False, logits_to_keep=len(ai) + 1).logits[0, :-1]  # lm_head only on the answer positions (untied 250k vocab)
        loss = F.cross_entropy(lg.float(), torch.tensor(ai, device=device))
        opt.zero_grad(set_to_none=True)
        if scaler:
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
        else:
            loss.backward()
            opt.step()
        loss_v = loss.item()
    pm.eval()
    return pm, loss_v


def answer(L, model, task, cuda):
    import torch
    t = task["test"][0]
    o = t["output"]
    max_new = len(o) * (len(o[0]) + 1) + 8
    with torch.autocast("cuda", dtype=torch.float16, enabled=cuda):
        txt = L.generate(model, [L.render(None, user_text(task["train"], t["input"]))], max_new=max_new, bs=1)[0]
    return parse_grid(txt) == o


def ans_nll(L, model, task, device, cuda):  # addendum 1: mean per-token loss of the TRUE test output (teacher-forced), a graded score that still moves when nothing is solved
    import torch
    import torch.nn.functional as F
    t = task["test"][0]
    pi, ai = L.ids(L.render(None, user_text(task["train"], t["input"]))), L.ids(gtxt(t["output"])) + [L.eos]
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16, enabled=cuda):
        lg = model(input_ids=torch.tensor([pi + ai], device=device), use_cache=False, logits_to_keep=len(ai) + 1).logits[0, :-1]
    return round(F.cross_entropy(lg.float(), torch.tensor(ai, device=device)).item(), 5)


def run(a):
    import torch
    from train import load_model
    from sleep1 import Lang
    tasks = json.load(open(a.tasks))
    si, sn = map(int, a.shard.split("/"))
    arms = a.arms.split(",")
    steps = 3 if a.smoke else a.steps
    cuda = torch.cuda.is_available() and not a.smoke
    device = torch.device("cuda" if cuda else "cpu")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fn = out / f"results_shard{si}.jsonl"
    done = {(r["task"], r["arm"]) for r in map(json.loads, open(fn))} if fn.exists() else set()
    mine = [k for k in range(len(tasks)) if k % sn == si]
    if a.smoke:
        mine = mine[:2]
    lm, tok = load_model(a, device, torch.float32 if not cuda else torch.float16)
    if cuda:
        try:
            lm.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
            lm.enable_input_require_grads()
        except Exception as e:
            print(f"gradient checkpointing unavailable: {e}", flush=True)
    L = Lang(tok, False, device, k2=True)
    print(f"shard {si}/{sn}: {len(mine)} tasks, arms {arms}, steps {steps}, device {device}, {len(done)} results already", flush=True)
    for k in mine:
        task = tasks[k]
        for arm in arms:
            if (task["id"], arm) in done:
                continue
            t0 = time.time()
            n_ex, loss = 0, None
            if arm == "B":
                ok = answer(L, lm, task, cuda)
                nll = ans_nll(L, lm, task, device, cuda)
            else:
                src = task if arm == "T" else tasks[(k + 1) % len(tasks)]
                exs, n_ex = train_examples(src, k, steps, L)
                pm, loss = ttt_train(lm, L, exs, k, device, cuda)
                ok = answer(L, pm, task, cuda)
                nll = ans_nll(L, pm, task, device, cuda)
                lm = pm.unload()  # drop the LoRA: next task starts from base
                if cuda:
                    torch.cuda.empty_cache()
            row = {"task": task["id"], "idx": k, "arm": arm, "ok": bool(ok), "seconds": round(time.time() - t0, 1), "n_train_examples": n_ex,
                   "final_loss": loss, "answer_nll": nll, "out_rows": len(task["test"][0]["output"]), "out_cols": len(task["test"][0]["output"][0])}
            with open(fn, "a") as f:
                f.write(json.dumps(row) + "\n")
            print(f"[{k}] {task['id']} {arm} ok={ok} {row['seconds']}s loss={loss}", flush=True)


# ------------------------------------------------------------------ score
def mcnemar(x, y):  # exact two-sided on discordant pairs
    b = sum(1 for u, v in zip(x, y) if u and not v)
    c = sum(1 for u, v in zip(x, y) if v and not u)
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def score(a):
    rows = {}
    for fn in sorted(Path(a.dir).glob("results_shard*.jsonl")):
        for r in map(json.loads, open(fn)):
            rows[(r["task"], r["arm"])] = r
    ids = sorted({t for t, _ in rows if all((t, m) in rows for m in "BTC")})
    allids = {t for t, _ in rows}
    ok = {m: [rows[(t, m)]["ok"] for t in ids] for m in "BTC"}
    s = {m: sum(ok[m]) for m in "BTC"}
    res = {"n_tasks_complete": len(ids), "n_tasks_partial": len(allids) - len(ids), "solved": s, "T_minus_C": s["T"] - s["C"],
           "p_T_vs_C": mcnemar(ok["T"], ok["C"]), "p_T_vs_B": mcnemar(ok["T"], ok["B"]), "p_C_vs_B": mcnemar(ok["C"], ok["B"])}
    res["verdict"] = ("T1 PASS" if res["T_minus_C"] >= 5 and res["p_T_vs_C"] < 0.05 else
                      "T1 WRONG (T <= C: drop TTT for the small tier)" if s["T"] <= s["C"] else "T1 FAIL (not wrong): T > C but short of the pass marks")
    if len(ids) < N_TASKS:
        res["verdict"] += f" [provisional: only {len(ids)} of {N_TASKS} tasks have all three arms]"
    def sign(m1, m2):  # addendum 1: tasks where m1's answer loss is lower than m2's, exact two-sided sign test (ties dropped)
        w = sum(rows[(t, m1)]["answer_nll"] < rows[(t, m2)]["answer_nll"] for t in ids)
        l = sum(rows[(t, m1)]["answer_nll"] > rows[(t, m2)]["answer_nll"] for t in ids)
        n = w + l
        p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n)
        return {"lower": w, "higher": l, "p": p}
    if ids and all("answer_nll" in rows[(t, m)] for t in ids for m in "BTC"):
        res["answer_nll_mean"] = {m: round(sum(rows[(t, m)]["answer_nll"] for t in ids) / len(ids), 4) for m in "BTC"}
        res["nll_T_vs_C"], res["nll_T_vs_B"], res["nll_C_vs_B"] = sign("T", "C"), sign("T", "B"), sign("C", "B")
        nt = res["nll_T_vs_C"]
        res["verdict_T1b"] = "T1b PASS" if nt["lower"] >= 0.6 * len(ids) and nt["p"] < 0.05 else "T1b FAIL"
    res["mean_seconds"] = {m: round(sum(rows[(t, m)]["seconds"] for t in ids) / max(len(ids), 1), 1) for m in "BTC"}
    by = {}
    for t in ids:
        r = rows[(t, "B")]
        sz = "<=100 cells" if r["out_rows"] * r["out_cols"] <= 100 else "101-300 cells" if r["out_rows"] * r["out_cols"] <= 300 else ">300 cells"
        d = by.setdefault(sz, {"n": 0, "B": 0, "T": 0, "C": 0})
        d["n"] += 1
        for m in "BTC":
            d[m] += rows[(t, m)]["ok"]
    res["by_output_size"] = by
    json.dump(res, open(Path(a.dir) / "score.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("select")
    s1.add_argument("--out", required=True)
    s2 = sub.add_parser("run")
    s2.add_argument("--tasks", required=True)
    s2.add_argument("--shard", default="0/1")
    s2.add_argument("--arms", default="B,T,C")
    s2.add_argument("--out", required=True)
    s2.add_argument("--model", default=K2_REPO)
    s2.add_argument("--revision", default=K2_REV)
    s2.add_argument("--steps", type=int, default=48)
    s2.add_argument("--seed", type=int, default=0)
    s2.add_argument("--smoke", action="store_true")
    s3 = sub.add_parser("score")
    s3.add_argument("--dir", required=True)
    a = ap.parse_args()
    {"select": select, "run": run, "score": score}[a.cmd](a)
