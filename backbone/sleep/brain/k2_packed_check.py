"""Kaggle T4 (fp16, 16 GB) check of sleepb --q4-packed on K2-Horizon-3.7B; --smoke runs the same steps on the tiny CPU K2 (so the script itself is tested).

    python backbone/sleep/brain/k2_packed_check.py --real --out out/k2packed            # parts a, b, c in turn (each prints a JSON summary; the whole thing writes OUT/summary.json)
    python backbone/sleep/brain/k2_packed_check.py --real --part a --out out/k2packed   # one part: a, b or c
    python backbone/sleep/brain/k2_packed_check.py --smoke --out /tmp/k2pc               # CPU, minutes

a: the packed model is built on the GPU from the CPU-loaded model (pack_model with device=cuda); the packed dequant of a few tensors (layer 0 and the last layer's Linears, embedding rows, the head's first / last rows)
   is compared BIT FOR BIT with q4_fake of the original weight on the CPU (assert-style: reported as equal true / false); compiled vs eager unpack and the head's vocab-chunked vs one-piece matmul are compared on the
   GPU (reported); the logits of 3 short prompts of the packed GPU model vs the fake-quant model on the CPU (a second CPU load; the matmuls differ GPU vs CPU, so max abs diff / argmax agreement are reported, not asserted).
b: sleepb.py --bench-train --q4-base --q4-packed --mem-cap-gb 8 --bench-dtype fp16 at tok budgets 512 and 1024: peak GPU memory (max_memory_allocated) and s/step, OLD vs NEW head path.
c: sleepb.py one night of ab_ob_b4_nb --q4-base --q4-packed --mem-cap-gb 8 --dtype fp16 (Week 2, --budget-scale 0.25, a 60-step schedule, --tok-budget 512, --gen-bs 8): the run is stopped after night 1's partial result is
   written; fits = it got there without an out-of-memory error; peak = result cuda_max_mem_gb. (Raise --budget-scale / --schedule for a real night.)
Expected packed size of the real model (from its shapes, 5,058,255,360 params, 254 packed tensors = 36 x 7 Linears + embedding + head): 2.650 GiB packed vs 9.422 GiB dense bf16 / fp16."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent.parent):
    sys.path.insert(0, str(_p))
import q4packed  # noqa: E402
from sleepb import q4_apply, q4_fake  # noqa: E402
from train import load_model  # noqa: E402

REV = "9d280ff742235796925c9fe3cf243dc1beea5c08"
PROMPTS = ["The harbour lantern is", "Kelmira lives next to a bakery that", "Question: what is the capital of France?\nAnswer:"]
SLEEPB = str(HERE / "sleepb.py")


def part_a(a, dev, dt, rep):
    cpu = torch.device("cpu")
    lm, tok = load_model(a, cpu, dt)
    L = len(lm.model.layers)
    want = [f"model.layers.{i}.{s}.weight" for i in (0, L - 1) for s in ("self_attn.q_proj", "self_attn.k_proj", "self_attn.o_proj", "mlp.gate_proj", "mlp.down_proj")]
    mods = dict(lm.named_modules())
    ref = {n: q4_fake(mods[n.removesuffix(".weight")].weight.data) for n in want}  # CPU fake-quant reference of the originals, before packing
    rows = torch.tensor(sorted({0, 1, 2, 250, 4097, lm.config.vocab_size - 1}))
    ref_emb = q4_fake(lm.model.embed_tokens.weight.data[rows])
    nh = lm.lm_head.weight.shape[0]
    ref_head = [q4_fake(lm.lm_head.weight.data[:3000]), q4_fake(lm.lm_head.weight.data[nh - 3000:])]
    torch.cuda.reset_peak_memory_stats() if dev.type == "cuda" else None
    st = q4packed.pack_model(lm, 64, 4, dev, dev.type == "cuda")
    lm.to(dev)
    rep["pack"] = {**st, "gib_before": st["bytes_before"] / 2 ** 30, "gib_after": st["bytes_after"] / 2 ** 30, "cuda_max_mem_gb_after_pack": torch.cuda.max_memory_allocated() / 2 ** 30 if dev.type == "cuda" else None}
    dv = {n: m.dequant().cpu() for n, m in lm.named_modules() if isinstance(m, q4packed.PackedTensor)}
    eq = {n: torch.equal(dv[n.removesuffix(".weight") + ".packed"], r) for n, r in ref.items()}
    eq["embed rows"] = torch.equal(lm.model.embed_tokens(rows.to(dev)).cpu(), ref_emb)
    hd = lm.lm_head.packed
    eq["head first 3000 rows"] = torch.equal(hd.dequant(0, 3000).cpu(), ref_head[0])
    eq["head last 3000 rows"] = torch.equal(hd.dequant(nh - 3000, nh).cpu(), ref_head[1])
    rep["dequant_bitwise_equal_to_q4_fake_cpu"] = {"all": all(eq.values()), **eq}
    if dev.type == "cuda":  # compiled vs eager unpack, chunked vs one-piece head matmul (same GPU, so equal is expected: if not, set --q4-packed-compile off / see q4packed.HEAD_CHUNK)
        p = lm.model.layers[0].mlp.gate_proj.packed
        e = q4packed.unpack(p.codes, p.scale, p.bias, 4, 64, p.dtype, compile=False)
        c = q4packed.unpack(p.codes, p.scale, p.bias, 4, 64, p.dtype, compile=True)
        h = torch.randn(5, lm.config.hidden_size, device=dev, dtype=dt)
        with torch.no_grad():
            r0 = lm.lm_head.rows
            lm.lm_head.rows = None
            full = lm.lm_head(h)
            lm.lm_head.rows = r0
            chunked = lm.lm_head(h)
        rep["gpu_compile_vs_eager_bitwise"], rep["gpu_head_chunked_vs_onepiece_bitwise"] = torch.equal(e, c), torch.equal(full, chunked)
    ids = [tok(x, return_tensors="pt")["input_ids"] for x in PROMPTS]
    with torch.no_grad():
        got = [lm(input_ids=i.to(dev)).logits[0, -1].float().cpu() for i in ids]
        gen = [lm.generate(input_ids=i.to(dev), max_new_tokens=8, do_sample=False, pad_token_id=1)[0].tolist() for i in ids]
    rep["gpu_packed_peak_gb_after_logits"] = torch.cuda.max_memory_allocated() / 2 ** 30 if dev.type == "cuda" else None
    del lm, hd, dv
    if dev.type == "cuda":
        torch.cuda.empty_cache()
    lm2, _ = load_model(a, cpu, dt)  # the fake-quant reference model on the CPU (dense, same dtype)
    q4_apply(lm2, 64, 4)
    with torch.no_grad():
        want_l = [lm2(input_ids=i).logits[0, -1].float() for i in ids]
        want_g = [lm2.generate(input_ids=i, max_new_tokens=8, do_sample=False, pad_token_id=1)[0].tolist() for i in ids]
    rep["logits_gpu_packed_vs_cpu_fake_quant"] = [{"max_abs_diff": float((g - w).abs().max()), "ref_logit_range": float(w.max() - w.min()), "argmax_equal": int(g.argmax()) == int(w.argmax())} for g, w in zip(got, want_l)]
    rep["greedy_8_tokens_equal"] = [x == y for x, y in zip(gen, want_g)]
    del lm2


def run(cmd, log, stop_after_night=None, timeout=6 * 3600):
    """Run cmd (log to a file); with stop_after_night = the partial result path, stop the process once that file lists a night. Returns (returncode or 'stopped', seconds, oom)."""
    t0 = time.time()
    with open(log, "w") as f:
        pr = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
        while pr.poll() is None and time.time() - t0 < timeout:
            time.sleep(5)
            if stop_after_night and stop_after_night.exists():
                try:
                    if json.loads(stop_after_night.read_text()).get("nights"):
                        time.sleep(2)
                        pr.terminate()
                        pr.wait(60)
                        return "stopped", time.time() - t0, False
                except ValueError:  # being written
                    pass
        if pr.poll() is None:
            pr.kill()
    txt = Path(log).read_text()
    return pr.returncode, time.time() - t0, "OutOfMemoryError" in txt or "out of memory" in txt.lower()


def common(a):  # model flags for sleepb
    return ["--model", a.model] + (["--revision", a.revision] if a.revision and not a.smoke else []) + (["--smoke"] if a.smoke else [])


def part_b(a, out, rep):
    d = out / "bench"
    cmd = [sys.executable, SLEEPB, "--bench-train", "--q4-base", "--q4-packed", "--bench-dtype", "fp16", "--bench-budgets", "256,512" if a.smoke else "512,1024", "--out", str(d), *common(a)]
    if not a.smoke:
        cmd += ["--mem-cap-gb", "8"]
    rc, secs, oom = run(cmd, out / "bench.log")
    f = d / "bench_train.json"
    rep["bench"] = {"returncode": rc, "seconds": secs, "oom": oom, "cmd": " ".join(cmd)}
    if f.exists():
        r = json.loads(f.read_text())
        rep["bench"]["q4_base"] = r.get("q4_base")
        rep["bench"]["settings"] = {b: {k: row.get(k) for k in ("old", "new", "speedup")} for b, row in r["settings"].items()}


def part_c(a, out, rep):
    d = out / "night"
    sched = out / "schedule_1night.json"
    sched.write_text(json.dumps({"nights": [{"steps": 60}] * 7}))
    cmd = [sys.executable, SLEEPB, "--arm", "ab_ob_b4_nb", "--q4-base", "--q4-packed", "--dtype", "fp32" if a.smoke else "fp16", "--seed", "1", "--out", str(d), *common(a)]
    if not a.smoke:
        cmd += ["--week", str(HERE / "data" / "week2.json"), "--mem-cap-gb", "8", "--budget-scale", "0.25", "--schedule", str(sched), "--tok-budget", "512", "--gen-bs", "8", "--max-dream-items", "40"]
    rc, secs, oom = run(cmd, out / "night.log", d / "result_ab_ob_b4_nb.partial.json")
    rep["night"] = {"returncode": rc, "seconds": secs, "oom": oom, "cmd": " ".join(cmd)}
    for name in ("result_ab_ob_b4_nb.partial.json", "result_ab_ob_b4_nb.json"):
        f = d / name
        if f.exists():
            r = json.loads(f.read_text())
            rep["night"].update({"cuda_max_mem_gb": r.get("cuda_max_mem_gb"), "q4_base": r.get("q4_base"), "nights_done": len(r.get("nights", [])), "night1_seconds": (r.get("nights") or [{}])[0].get("time")})
            break
    rep["night"]["fits"] = rc in (0, "stopped") and not oom and rep["night"].get("nights_done", 0) >= 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--part", choices=["a", "b", "c", "all"], default="all")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="IFM/K2-Horizon-3.7B")
    ap.add_argument("--revision", default=REV)
    ap.add_argument("--dtype", choices=["fp16", "bf16", "fp32"], default=None, help="default: fp16 on cuda (T4), fp32 in --smoke")
    a = ap.parse_args()
    if a.real == a.smoke:
        ap.error("exactly one of --real / --smoke")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dev = torch.device("cuda" if torch.cuda.is_available() and a.real else "cpu")
    if a.real and dev.type != "cuda":
        ap.error("--real needs a GPU")
    dt = {"fp16": torch.float16, "bf16": torch.bfloat16, "fp32": torch.float32}[a.dtype or ("fp16" if a.real else "fp32")]
    rep = {"device": str(dev), "dtype": str(dt), "model": a.model, "revision": a.revision}
    if a.part in ("a", "all"):
        if a.smoke:  # load_model's tiny K2 does not take a revision through from_config
            a.revision = None
        part_a(argparse.Namespace(smoke=a.smoke, seed=0, model=a.model, revision=a.revision if a.real else None), dev, dt, rep)
        print(json.dumps({"a": {k: v for k, v in rep.items() if k not in ("device", "dtype", "model", "revision")}}, indent=1), flush=True)
    for p, fn in (("b", part_b), ("c", part_c)):
        if a.part in (p, "all"):
            fn(a, out, rep)
            print(json.dumps({p: rep["bench" if p == "b" else "night"]}, indent=1), flush=True)
    (out / "summary.json").write_text(json.dumps(rep, indent=1))
    print(f"[done] {out / 'summary.json'}")


if __name__ == "__main__":
    main()
