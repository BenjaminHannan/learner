"""PREREG-habit1-mini.md, one arm on a Mac with MLX: score before -> habit spotter -> dreams -> LoRA (mlx_lm.lora) -> score after.

  python habit_mini.py --model NexVeridian/Qwen3.6-35B-A3B-3bit --arm m3 --data habit1_mini.json --out runs/m3
  python habit_mini.py --model mlx-community/Qwen3.6-35B-A3B-4bit --arm m4 --data habit1_mini.json --out runs/m4
  --stage {all,before,spot,dream,train,after}: `all` runs the steps in order and skips a step whose output file is already in --out (resume);
  a single stage always re-runs. --dry: stub model, no mlx, no lora subprocess (checks the plumbing and the train.jsonl format).
Files in --out: before.json spot.json dream.json train.jsonl valid.jsonl lora.yaml train.json train.log adapters/ after.json result.json
(stopped.json when the safety watcher or the wall cap ended the run). Needs only habit.py from the repo (pure Python), mlx_lm and mlx.
Greedy everywhere, enable_thinking=False, the same settings for both arms."""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import habit as H  # noqa: E402

WALL_CAP_S = 4 * 3600  # training wall cap (prereg step 4)
SWAP_MAX_MB, WATCH_S = 4096, 30  # safety: swap above 4 GB, polled every 30 s
LORA = dict(num_layers=8, rank=8, scale=20.0, dropout=0.0, lr=1e-4, batch=1, max_len=320, iters=300, save_every=50)
MAX_FACT, MAX_REPLAY, MAX_DREAM = 12, 120, 400


class Stopped(Exception):
    pass


# ------------------------------------------------------------------ safety
class Watch(threading.Thread):
    """Every 30 s: swap used (sysctl vm.swapusage) > 4 GB, memory pressure critical ("red": sysctl kern.memorystatus_vm_pressure_level == 4, else
    memory_pressure -Q free % < 5), or a PAUSE_OTHERS / ASSISTANT_RUNNING flag (env var or file in cwd / home / the out dir's parent). The first
    hit sets .reason; steps call .check() between generations and the lora wait loop polls .reason. Off Mac (dry) it only watches the flags."""

    def __init__(self, parent, every=WATCH_S, mac=True):
        super().__init__(daemon=True)
        self.parent, self.every, self.mac, self.reason, self.done = parent, every, mac, None, threading.Event()
        self.swap_peak_mb = 0.0

    @staticmethod
    def sh(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
        except Exception:
            return ""

    def swap_mb(self):
        m = re.search(r"used = ([\d.]+)([MGK])", self.sh(["sysctl", "vm.swapusage"]))
        return float(m.group(1)) * {"K": 1 / 1024, "M": 1, "G": 1024}[m.group(2)] if m else None

    def red(self):
        v = self.sh(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]).strip()
        if v:
            return v == "4"
        m = re.search(r"free percentage: (\d+)%", self.sh(["memory_pressure", "-Q"]))
        return bool(m) and int(m.group(1)) < 5

    def flag(self):
        for n in ("PAUSE_OTHERS", "ASSISTANT_RUNNING"):
            if os.environ.get(n, "") not in ("", "0") or any((d / n).exists() for d in (Path.cwd(), Path.home(), Path.home() / "learner-ops", self.parent)):
                return n
        # Ben clicking Start Assistant runs serve.sh, which waits for free memory before it writes ASSISTANT_RUNNING; catch it early
        if self.mac and self.sh(["pgrep", "-f", "assistant/serve.sh"]).strip():
            return "assistant/serve.sh"
        return None

    def poll(self):
        if self.mac:
            s = self.swap_mb()
            if s is not None:
                self.swap_peak_mb = max(self.swap_peak_mb, s)
                if s > SWAP_MAX_MB:
                    return f"swap used {s:.0f} MB > {SWAP_MAX_MB} MB"
            if self.red():
                return "memory pressure red"
        f = self.flag()
        return f"flag {f} present" if f else None

    def run(self):
        while not self.done.wait(self.every):
            r = self.poll()
            if r and not self.reason:
                self.reason = r

    def check(self):
        if self.reason:
            raise Stopped(self.reason)


# ------------------------------------------------------------------ model plumbing (mlx, or a stub with --dry)
class Stub:
    """--dry: replies by prompt shape, so every parser and the data builder run end to end."""
    tokenizer = None

    def reply(self, p):
        m = re.search(r'"([^"]+)" and "([^"]+)" come up together', p)
        if m:
            return f"Sam usually meets {m.group(1)} at {m.group(2)}." if m.group(1)[0] < "T" else "no"
        if "paraphrases of those facts" in p:
            msg = p.split('"', 1)[1].rsplit('"', 1)[0]
            ns = [w for w in re.findall(r"\b[A-Z][a-z]{3,}\b", msg)][1:3] or ["Aaa", "Bbb"]
            return json.dumps({"paraphrases": [f"{ns[0]} and {ns[1]} go together.", f"A note: {ns[1]} is tied to {ns[0]}.", "no names here"],
                               "qa": [{"q": f"Who goes with {ns[0]}?", "a": ns[1]}, {"q": f"Who goes with {ns[1]}?", "a": ns[0]}, {"q": "bad?", "a": "nobody"}]})
        if "Answer with the letter only" in p:
            return "A"
        return "Flanaigur is the stub answer."


class Mlx:
    def __init__(self, path, adapter=None):
        import mlx_lm
        from mlx_lm.sample_utils import make_sampler
        self.mlx_lm, self.sampler = mlx_lm, make_sampler(temp=0.0)
        self.model, self.tokenizer = mlx_lm.load(path, adapter_path=adapter) if adapter else mlx_lm.load(path)

    def reply(self, p, n):
        return self.mlx_lm.generate(self.model, self.tokenizer, prompt=p, max_tokens=n, sampler=self.sampler).strip()


class Chat:
    """render(system, user) -> prompt text (enable_thinking=False); ask(system, user, n) -> reply. watch.check() runs before each call."""

    def __init__(self, backend, watch):
        self.b, self.w, self.dry = backend, watch, isinstance(backend, Stub)

    def render(self, system, user):
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
        if self.dry:
            return "".join(f"{m['role']}: {m['content']}\n" for m in msgs) + "assistant: "
        return self.b.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)

    def ask(self, system, user, n):
        self.w.check()
        p = self.render(system, user)
        return self.b.reply(p) if self.dry else self.b.reply(p, n)


def peak_gb():
    try:
        import mlx.core as mx
        f = getattr(mx, "get_peak_memory", None) or mx.metal.get_peak_memory
        return f() / 1e9
    except Exception:
        return None


# ------------------------------------------------------------------ scoring and spotter
def has_ans(target, ans):
    return target.lower() in ans.lower()


def first_letter(ans):
    m = re.search(r"[A-Za-z]", ans)
    return m.group(0).upper() if m else ""


def score(chat, data, sys_):
    """Weights-only, greedy, max 12 tokens. Facts and routines: target substring (has_ans); ARC: first generated letter == gold."""
    out = {}
    for k in ("facts", "routines"):
        rows = []
        for x in data[k]:
            r = chat.ask(sys_, x["q"], MAX_FACT)
            rows.append({"id": x["id"], "q": x["q"], "target": x["target"], "reply": r, "ok": has_ans(x["target"], r)})
        out[k] = {"pct": 100 * sum(r["ok"] for r in rows) / len(rows), "n": len(rows), "rows": rows}
    rows = []
    for x in data["arc"]:
        r = chat.ask(None, x["user"], MAX_FACT)
        rows.append({"id": x["id"], "gold": x["gold"], "reply": r, "ok": first_letter(r) == x["gold"]})
    out["arc"] = {"pct": 100 * sum(r["ok"] for r in rows) / len(rows), "n": len(rows), "rows": rows}
    return out


def spot(chat, data):
    """Prereg step 2: the 20 Rall questions in stage 1's wording; a yes (habit.parse_habit) is a habit item: its sentence + the pair's diary turns."""
    rows = []
    for r in data["routines"]:
        reply = chat.ask(r["system"], r["user"], 48)  # stage 1 asked with max_tokens 48
        rows.append({"id": r["id"], "pair": r["pair"], "reply": reply, "sentence": H.parse_habit(reply, *r["pair"])})
    return {"asked": len(rows), "yes": sum(bool(x["sentence"]) for x in rows), "rows": rows}


# ------------------------------------------------------------------ dreams and training data
def parse_dream(txt):
    """sleep1.parse_dream: the JSON object, else Q:/A: lines (copied so the Mac needs no torch)."""
    paras, qas = [], []
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            return ([p for p in d.get("paraphrases", []) if isinstance(p, str)],
                    [(x.get("q"), x.get("a")) for x in d.get("qa", []) if isinstance(x, dict) and isinstance(x.get("q"), str) and isinstance(x.get("a"), str)])
        except Exception:
            pass
    for line in txt.splitlines():
        mm = re.match(r"(?:Q:|Question:)\s*(.+?)\s*(?:\||A:|Answer:)\s*(.+)$", line.strip().lstrip("-*0123456789. ").strip())
        if mm:
            qas.append((mm.group(1), mm.group(2)))
    return paras, qas


def norm(s):
    return re.sub(r"\s+", " ", s.lower().replace("\u2019", "'")).strip()


def items_of(data, spotted):
    """Facts, then one habit item per spotter yes: {kind, a, b, sentence, turns}."""
    its = [{"kind": "fact", "id": f["id"], "a": f["a"], "b": f["b"], "sentence": f["sentence"], "turns": f["turns"]} for f in data["facts"]]
    by = {r["id"]: r for r in data["routines"]}
    for s in spotted["rows"]:
        if s["sentence"]:
            r = by[s["id"]]
            its.append({"kind": "habit", "id": r["id"], "a": r["pair"][0], "b": r["pair"][1], "sentence": s["sentence"], "turns": r["turns"]})
    return its


def dream(chat, data, spotted, log=print):
    """Prereg step 3: af_prompt once per diary turn of each item (greedy, K = 4, 400 tokens); then the base model's own answers to the replay prompts."""
    out = {"items": [], "replay": []}
    for it in items_of(data, spotted):
        raw = [chat.ask(t["prompt"]["system"], t["prompt"]["user"], MAX_DREAM) for t in it["turns"]]
        out["items"].append({**{k: it[k] for k in ("kind", "id", "a", "b", "sentence")}, "raw": raw})
        log(f"dream {it['kind']} {it['id']}: {len(raw)} turns")
    for p in data["replay"]:
        out["replay"].append({"prompt": p, "answer": chat.ask(None, p, MAX_REPLAY)})
    return out


def build_samples(data, dreams, seed=0):
    """Prereg step 3 -> (train, valid, counts). Per item: the Q&A pairs (system line as in scoring), each paraphrase as the answer to
    "What do you remember about A and B?", and the item's own sentence the same way; replay = {prompt, own answer}. The run_af filters: a
    paraphrase must name both names; a Q&A answer must hold exactly one of them and the question must not; no eval or test question."""
    leak = set(data["test_strings_norm"]) | {norm(x["q"]) for x in data["facts"] + data["routines"]}
    st = {"paraphrases": 0, "qa": 0, "sentences": 0, "replay": 0, "dropped_missing_names": 0, "dropped_bad_answer": 0, "dropped_leak": 0, "parse_fail": 0}
    rem = lambda a, b: f"What do you remember about {a} and {b}?"  # noqa: E731
    train, seen = [], set()

    def add(msgs, key, kind):
        if key not in seen:
            seen.add(key)
            train.append({"messages": msgs})
            st[kind] += 1
    for it in dreams["items"]:
        a, b = it["a"], it["b"]
        add([{"role": "user", "content": rem(a, b)}, {"role": "assistant", "content": it["sentence"]}], ("p", it["sentence"]), "sentences")
        for txt in it["raw"]:
            paras, qas = parse_dream(txt)
            st["parse_fail"] += not paras and not qas
            for p in paras[:data["k"]]:
                p = p.strip()
                if not all(n.lower() in p.lower() for n in (a, b)):
                    st["dropped_missing_names"] += 1
                else:
                    add([{"role": "user", "content": rem(a, b)}, {"role": "assistant", "content": p}], ("p", p), "paraphrases")
            for q, ans in qas[:data["k"]]:
                nq, es = norm(q), [n for n in (a, b) if n.lower() in ans.lower()]
                if any(l in nq or (len(nq) >= 10 and nq in l) for l in leak):
                    st["dropped_leak"] += 1
                elif len(es) != 1 or es[0].lower() in q.lower():
                    st["dropped_bad_answer"] += 1
                else:
                    add([{"role": "system", "content": data["sys"]}, {"role": "user", "content": q.strip()}, {"role": "assistant", "content": es[0]}],
                        ("q", nq, es[0]), "qa")
    for r in dreams["replay"]:
        if r["answer"].strip():
            add([{"role": "user", "content": r["prompt"]}, {"role": "assistant", "content": r["answer"]}], ("r", r["prompt"]), "replay")
    random.Random(seed).shuffle(train)
    nv = max(4, len(train) // 20)  # valid.jsonl is only for mlx_lm.lora's loss printout
    return train[nv:], train[:nv], st


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(r) + "\n" for r in rows))


def check_jsonl(path):
    """Every line {"messages": [...]} with roles alternating from system/user to a final non-empty assistant (what mlx_lm.lora's chat dataset reads)."""
    n = 0
    for ln in Path(path).read_text().splitlines():
        m = json.loads(ln)["messages"]
        r = [x["role"] for x in m]
        assert set(m[0]) == {"role", "content"} and r[-1] == "assistant" and m[-1]["content"].strip() and r.count("assistant") == 1 and r[0] in ("system", "user"), ln[:200]
        assert all(isinstance(x["content"], str) for x in m) and r[-2] == "user", ln[:200]
        n += 1
    return n


# ------------------------------------------------------------------ training
def lora_yaml(a, out):
    """mlx_lm 0.32 config keys (rank is only reachable from here): lora_parameters {rank, scale, dropout}; the rest mirrors the CLI flags."""
    L = LORA
    return (f"model: \"{a.model}\"\ntrain: true\ndata: \"{out}\"\nadapter_path: \"{out / 'adapters'}\"\nnum_layers: {L['num_layers']}\nbatch_size: {L['batch']}\n"
            f"iters: {L['iters']}\nlearning_rate: {L['lr']}\nmax_seq_length: {L['max_len']}\nmask_prompt: true\ngrad_checkpoint: true\n"
            f"save_every: {L['save_every']}\nsteps_per_report: 10\nsteps_per_eval: 100\nval_batches: 2\nseed: 0\n"
            f"lora_parameters:\n  rank: {L['rank']}\n  scale: {L['scale']}\n  dropout: {L['dropout']}\n")


def train(a, out, watch):
    """`python -m mlx_lm lora` with the prereg settings. A watcher stop or the 4 h cap kills it and keeps the latest saved adapter."""
    (out / "lora.yaml").write_text(lora_yaml(a, out))
    L = LORA
    cmd = [sys.executable, "-m", "mlx_lm", "lora", "-c", str(out / "lora.yaml"), "--model", a.model, "--train", "--data", str(out), "--adapter-path", str(out / "adapters"),
           "--num-layers", str(L["num_layers"]), "--batch-size", str(L["batch"]), "--iters", str(L["iters"]), "--learning-rate", str(L["lr"]),
           "--max-seq-length", str(L["max_len"]), "--mask-prompt", "--grad-checkpoint", "--save-every", str(L["save_every"])]
    t0, it_seen, peak, why = time.time(), 0, 0.0, None
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def pump():
        nonlocal it_seen, peak
        with open(out / "train.log", "w") as f:
            for ln in p.stdout:
                f.write(ln)
                f.flush()
                m = re.search(r"Iter (\d+):", ln)
                it_seen = int(m.group(1)) if m else it_seen
                m = re.search(r"Peak mem ([\d.]+) GB", ln)
                peak = max(peak, float(m.group(1))) if m else peak
    th = threading.Thread(target=pump, daemon=True)
    th.start()
    while p.poll() is None:
        time.sleep(5)
        why = watch.reason or ("wall cap 4 h" if time.time() - t0 > WALL_CAP_S else None)
        if why:
            p.terminate()
            try:
                p.wait(60)
            except subprocess.TimeoutExpired:
                p.kill()
            break
    th.join(10)
    ckpt = sorted((out / "adapters").glob("*_adapters.safetensors")) if (out / "adapters").exists() else []
    saved = int(ckpt[-1].name.split("_")[0]) if ckpt else 0
    rec = {"returncode": p.returncode, "stopped": why, "iters_logged": it_seen, "iters_saved": saved, "seconds": time.time() - t0,
           "s_per_iter": (time.time() - t0) / it_seen if it_seen else None, "peak_mem_gb_lora": peak or None,
           "adapter": bool((out / "adapters" / "adapters.safetensors").exists())}
    if why and watch.reason:
        raise Stopped(why)
    return rec


# ------------------------------------------------------------------ main
def jl(p, o=None):
    if o is None:
        return json.loads(Path(p).read_text())
    Path(p).write_text(json.dumps(o, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--arm", choices=("m3", "m4"), required=True)
    ap.add_argument("--data", default=str(HERE / "habit1_mini.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", choices=("all", "before", "spot", "dream", "train", "after"), default="all")
    ap.add_argument("--dry", action="store_true", help="stub model, no mlx, no lora subprocess")
    ap.add_argument("--ignore-flags", action="store_true", help="do not stop for PAUSE_OTHERS / ASSISTANT_RUNNING")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads(Path(a.data).read_text())
    t_start = time.time()
    watch = Watch(out.parent, mac=not a.dry)
    if a.ignore_flags:
        watch.flag = lambda: None
    if (r := watch.poll()):
        (out / "stopped.json").write_text(json.dumps({"reason": r, "at": "start"}))
        sys.exit(f"not starting: {r}")
    watch.start()
    todo = [s for s in ("before", "spot", "dream", "train", "after") if a.stage in ("all", s)]
    f = {"before": out / "before.json", "spot": out / "spot.json", "dream": out / "dream.json", "train": out / "train.json", "after": out / "after.json"}
    state = {"chat": None, "adapter": None}

    def chat(adapter=None):
        if state["chat"] is None or state["adapter"] != adapter:
            state["chat"] = None
            if a.dry:
                b = Stub()
            else:
                import mlx.core as mx
                mx.clear_cache() if hasattr(mx, "clear_cache") else mx.metal.clear_cache()
                b = Mlx(a.model, adapter)
            state["chat"], state["adapter"] = Chat(b, watch), adapter
        return state["chat"]
    try:
        for s in todo:
            if a.stage == "all" and f[s].exists():
                print(f"[{s}] already in {out}, skipped")
                continue
            t0 = time.time()
            if s == "before":
                jl(f[s], {**score(chat(), data, data["sys"]), "seconds": time.time() - t0})
            elif s == "spot":
                jl(f[s], spot(chat(), data))
            elif s == "dream":
                d = dream(chat(), data, jl(f["spot"]))
                jl(f[s], d)
                tr, va, st = build_samples(data, d)
                write_jsonl(out / "train.jsonl", tr)
                write_jsonl(out / "valid.jsonl", va)
                jl(out / "samples.json", {**st, "train": len(tr), "valid": len(va), "items": len(d["items"])})
                print(f"[dream] samples {st}, train {len(tr)}, valid {len(va)}; jsonl lines ok: {check_jsonl(out / 'train.jsonl')}")
            elif s == "train":
                if not (out / "train.jsonl").exists():
                    sys.exit("train.jsonl missing: run --stage dream first")
                if a.dry:
                    jl(f[s], {"dry": True, "returncode": None, "iters_logged": 0, "iters_saved": 0, "seconds": 0, "s_per_iter": None, "peak_mem_gb_lora": None, "adapter": False,
                              "yaml": lora_yaml(a, out)})
                    (out / "lora.yaml").write_text(lora_yaml(a, out))
                else:
                    state["chat"] = None  # free the model before the subprocess loads its own
                    import gc
                    gc.collect()
                    jl(f[s], train(a, out, watch))
            elif s == "after":
                tr = jl(f["train"]) if f["train"].exists() else {}
                ad = out / "adapters"
                if not a.dry and not tr.get("adapter"):
                    sys.exit("no adapter saved: nothing to score after")
                jl(f[s], {**score(chat(None if a.dry else str(ad)), data, data["sys"]), "seconds": time.time() - t0})
            print(f"[{s}] done in {time.time() - t0:.0f} s")
        if "after" in todo and f["after"].exists() and all(f[k].exists() for k in f):
            B, A, S, T, Smp = [jl(f[k]) for k in ("before", "after", "spot", "train")] + [jl(out / "samples.json")]
            jl(out / "result.json", {
                "arm": a.arm, "model": a.model, "dry": a.dry,
                "fact_before": B["facts"]["pct"], "fact_after": A["facts"]["pct"], "routine_before": B["routines"]["pct"], "routine_after": A["routines"]["pct"],
                "arc_before": B["arc"]["pct"], "arc_after": A["arc"]["pct"], "n": {"facts": B["facts"]["n"], "routines": B["routines"]["n"], "arc": B["arc"]["n"]},
                "spotter_yes": S["yes"], "spotter_asked": S["asked"], "samples": Smp, "iters_done": T["iters_saved"], "iters_logged": T["iters_logged"],
                "train_seconds": T["seconds"], "s_per_iter": T["s_per_iter"], "peak_mem_gb": peak_gb(), "peak_mem_gb_lora": T["peak_mem_gb_lora"],
                "swap_peak_mb": watch.swap_peak_mb, "wall_seconds": time.time() - t_start})
            print(json.dumps(jl(out / "result.json"), indent=1))
    except Stopped as e:
        jl(out / "stopped.json", {"reason": str(e), "stage_list": todo, "wall_seconds": time.time() - t_start, "swap_peak_mb": watch.swap_peak_mb})
        print(f"STOPPED: {e}")
        sys.exit(3)
    finally:
        watch.done.set()


if __name__ == "__main__":
    main()
