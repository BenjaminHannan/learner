"""Preflight for the P1 / P2b arms on the real model (run_box.sh runs it once before ws / wsham / tsd / tsd1 on a GPU box):

  python3 backbone/think/preflight.py --a-adapter out/think/a_s0/adapter --data out/data --out out/think/preflight [--model Qwen/Qwen3.5-0.8B] [--steps 20]

It runs 20 steps of tsd and 20 of ws on Qwen/Qwen3.5-0.8B in bf16 with CUDA (--smoke: the tiny CPU model, to test this script) and fails (exit 1) unless
  - the decoder's "dec" LoRA parameters get a non-zero gradient (in the first real optimizer step, and from the step loss alone);
  - the main LoRA's gradient is unchanged when the step loss is multiplied by zero (the step path adds nothing to it except through the step loss);
  - save_pretrained wrote adapter/dec next to the main adapter;
  - the losses are finite, the ws run wrote its T / C1 / fmt entries and the tsd run its decoder accuracy.
It prints the peak GPU memory of each run. steps.py also checks at import that peft's adapter switch toggles.
--arms br (Addendum F) instead runs 20 steps of br with every step at the largest training loop count (6), so the peak memory is the worst case, and
checks that the loop counts, the r-tags and the halting readout were written.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import train as T  # noqa: E402
import board as B  # noqa: E402
import steps as S  # noqa: E402
import think1 as K  # noqa: E402


class Fail(Exception):
    pass


def need(ok, msg):
    if not ok:
        raise Fail(msg)


def grads_of(params):
    return [None if p.grad is None else p.grad.detach().clone() for p in params]


def grad_checks(args, device, dtype, adapter, rows_n=4):
    """On one micro-batch: dec-LoRA and Linear gradients from the step loss are non-zero and finite; the main LoRA's gradient with 0 x step loss equals the
    gradient without the decoder. Returns a dict of the numbers."""
    lm, tok = T.load_model(args, device, dtype)
    train_rows = T.read_jsonl(Path(args.data) / "train.jsonl", limit=4000)
    rows = [r for r in train_rows if S.steps_of(r)][:rows_n]
    need(len(rows) == rows_n, "no train rows with steps in the data")
    enc = T.Encoder(tok, args.max_len)
    pm = K.lora_model(lm, adapter)
    runner = T.Runner(pm.base_model.model)
    runner.checkpoint = True
    torch.manual_seed(args.seed)
    board = B.ThinkBoard.from_model(runner.lm, tok, K=16 if not args.smoke else 4, alpha_init=args.alpha_init).to(device)
    sd = K.build_decoder(pm, runner, board, device, args.seed)
    pm.train()
    runner.lm.train()
    main = [p for n, p in pm.named_parameters() if p.requires_grad and ".dec." not in n]
    dec = [p for n, p in pm.named_parameters() if ".dec." in n]
    need(main and dec and all(p.requires_grad for p in dec), "the dec LoRA is missing or frozen")
    mb = [enc.train_example(r) for r in rows]
    dts = [S.decoder_targets(enc, r) for r in rows]
    n_lap = [sum(len(d[k][1]) for d in dts) for k in range(S.SD_LAPS)]
    n_norm = sum(len(a) for _, a in mb)

    def losses():
        la, _ = K.answer_loss_fixed(runner, mb, device)
        C, mask, p, lt, ans = K.micro_inputs(runner, mb, device)
        lb, info = B.train_loss(board, runner, C, mask, p, lt, ans, args.lmax, n_norm=n_norm, lam=K.LAMBDA, ckpt=True)
        return la / n_norm, lb, K.sd_micro_loss(sd, pm, runner, info, dts, n_lap)

    def run(weight_step):
        for p in [*main, *dec, *sd.parameters(), *board.parameters()]:
            p.grad = None
        la, lb, ls = losses()
        (la + lb + weight_step * ls).backward()
        return grads_of(main), grads_of(dec), grads_of(list(sd.parameters())), float(ls.detach())

    g_zero, d_zero, _, ls_val = run(0.0)
    g_none = None
    for p in [*main, *dec, *sd.parameters(), *board.parameters()]:
        p.grad = None
    la, lb, _ = losses()  # the same loss with no decoder term at all
    (la + lb).backward()
    g_none = grads_of(main)
    close = lambda a, b: a is not None and b is not None and float((a.float() - b.float()).norm()) <= 1e-3 * float(b.float().norm()) + 1e-12  # separate backward runs: allow kernel-level noise
    need(all(close(a, b) for a, b in zip(g_zero, g_none)), "main-LoRA gradient changed when the step loss was multiplied by zero")
    need(all(d is None or float(d.abs().sum()) == 0 for d in d_zero), "dec LoRA got gradient from a zero-weighted step loss")
    _, g_dec, g_proj, _ = run(1.0)
    n_dec = sum(g is not None and float(g.abs().sum()) > 0 for g in g_dec)
    need(n_dec > 0 and all(g is None or bool(torch.isfinite(g).all()) for g in g_dec), "the dec LoRA parameters got no (or non-finite) gradient from the step loss")
    need(any(g is not None and float(g.abs().sum()) > 0 for g in g_proj), "the decoder's Linear got no gradient")
    need(ls_val == ls_val and ls_val > 0, f"step loss {ls_val}")
    out = dict(step_loss=ls_val, dec_tensors_with_grad=n_dec, dec_tensors=len(dec), main_tensors=len(main))
    del lm, pm, runner, board, sd
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return out


def run_arm(arm, args, adapter, out):
    seen = {}
    real = torch.optim.AdamW.step

    def spy(self, *a, **k):  # the gradients the first real optimizer step uses
        if "g" not in seen:
            seen["g"] = {g.get("name"): sum(q.grad is not None and float(q.grad.abs().sum()) > 0 for q in g["params"]) for g in self.param_groups}
        return real(self, *a, **k)

    a = K.parse(["--arm", arm, "--seed", str(args.seed), "--data", str(args.data), "--out", str(out / f"{arm}_s{args.seed}"), "--model", args.model,
                 "--steps", str(args.steps), "--limit-eval", "16", "--a-adapter", str(adapter), "--alpha-init", str(args.alpha_init), "--micro-bsz", str(args.micro_bsz),
                 *(["--smoke"] if args.smoke else [])])
    if args.smoke:
        a.gate_step, a.log_every, a.max_len, a.bsz, a.micro_bsz = 4, 10**6, 256, 8, 4
    torch.optim.AdamW.step = spy
    sched = K.loop_schedule
    if arm == "br":  # every step at the largest training loop count: the worst-case memory
        K.loop_schedule = lambda steps, seed, **kw: [K.BR_TRAIN_MAX] * steps
    try:
        rc = K.run_arm(a)
    finally:
        torch.optim.AdamW.step = real
        K.loop_schedule = sched
    need(rc == 0, f"{arm}: run_arm returned {rc}")
    res = json.loads((out / f"{arm}_s{args.seed}" / f"result_{arm}_s{args.seed}.json").read_text())
    need(len(res["train"]["step_losses"]) == args.steps and all(x == x and abs(x) < 1e6 for x in res["train"]["step_losses"]), f"{arm}: non-finite or missing losses")
    if arm == "tsd":
        need(seen["g"].get("declora", 0) > 0, "tsd: the first optimizer step gave the dec LoRA no gradient")
        need((out / f"tsd_s{args.seed}" / "adapter" / "dec" / "adapter_config.json").exists(), "tsd: save_pretrained did not write adapter/dec")
        need((out / f"tsd_s{args.seed}" / "adapter" / "adapter_config.json").exists(), "tsd: the main adapter was not saved")
        need(res.get("decoder") and res["decoder"]["tokens"] > 0, "tsd: no decoder accuracy")
        need(res.get("gate_closed") in (True, False), "tsd: gate_closed not recorded")
    elif arm == "br":
        need(res["train"].get("loops_hist") == {str(K.BR_TRAIN_MAX): args.steps}, f"br: loop counts not as forced: {res['train'].get('loops_hist')}")
        need({f"r{r}" for r in K.BR_EVAL_LOOPS} | {"main"} <= set(res["eval"]["validation"]) and res.get("halting"), "br: r-tags or the halting readout missing")
    else:
        need({"T", "C1", "fmt"} <= set(res["eval"]["validation"]) and res["train"].get("written_cut"), "ws: T / C1 / fmt or the cut count missing")
    return dict(peak_gpu_mem_gb=res.get("peak_gpu_mem_gb"), seconds=res["train"]["seconds"], first_step_grad_tensors=seen["g"], final_loss=res["train"]["step_losses"][-1])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--a-adapter", required=True)
    ap.add_argument("--data", default="out/data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="Qwen/Qwen3.5-0.8B")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--alpha-init", type=float, default=0.0)
    ap.add_argument("--max-len", type=int, default=2048)
    ap.add_argument("--lmax", type=int, default=4)
    ap.add_argument("--smoke", action="store_true", help="tiny random model on the CPU (tests this script)")
    ap.add_argument("--micro-bsz", type=int, default=4, help="as the run it checks (run_box MICRO); 2 on a 12 GB card if 4 does not fit")
    ap.add_argument("--arms", default="tsd,ws", help="tsd,ws (P1 / P2b, with the gradient checks) or br (Addendum F, worst-case loops)")
    args = ap.parse_args(argv)
    out, adapter = Path(args.out), Path(args.a_adapter)
    if not args.smoke and not torch.cuda.is_available():
        print("PREFLIGHT FAIL: no CUDA GPU (the preflight is about the real model in bf16)")
        return 1
    device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    try:
        need(any((adapter / f).exists() for f in ("adapter_config.json",)), f"no stage-1 adapter at {adapter}")
        gargs = argparse.Namespace(smoke=args.smoke, seed=args.seed, model=args.model, data=args.data, max_len=256 if args.smoke else args.max_len,
                                   alpha_init=args.alpha_init, lmax=args.lmax)
        arms = args.arms.split(",")
        report = {}
        if "tsd" in arms:
            report["grad_checks"] = grad_checks(gargs, device, dtype, adapter)
            print(f"[preflight] gradient checks ok: {report['grad_checks']}", flush=True)
        for arm in arms:
            report[arm] = run_arm(arm, args, adapter, out)
            print(f"[preflight] {arm} ok: {report[arm]}", flush=True)
    except Fail as e:
        print(f"PREFLIGHT FAIL: {e}", flush=True)
        return 1
    peak = max((report[a]["peak_gpu_mem_gb"] or 0) for a in arms)
    print(f"PREFLIGHT OK: bf16={dtype == torch.bfloat16}, peak GPU memory {peak:.2f} GB (" + ", ".join(f"{a} {report[a]['peak_gpu_mem_gb']}" for a in arms) + ")", flush=True)
    out.mkdir(parents=True, exist_ok=True)
    (out / "preflight.json").write_text(json.dumps(report, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
