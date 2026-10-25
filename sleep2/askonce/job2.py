"""Kaggle job 2 (one lane = one seed on one GPU): nights + eval for arms A+, B, B-sft.
  python -m sleep2.askonce.job2 --seed 1 --nightdata DIR --out $OUT [--arms A+,B,B-sft] [--pilot] [--smoke]
--pilot: night 1 of A+ only, prints seconds/night and the projected total (the prereg's timing pilot)."""
import argparse
import os
import time
from pathlib import Path

from .config import DATA, MODEL_ID, jdump, jl_read, jload, n_nights
from .eval_moves import load_eval_sets, run_eval
from .job_common import Logger, assert_finite_forward, device_dtype, env_info
from .model_io import get_tokenizer, load_model
from .night_train import pilot_health, pilot_projection, train_arm
from .train_core import LoRATrainer


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--nightdata", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--arms", default="A+,B,B-sft")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--bs", type=int, default=8)
    ap.add_argument("--deadline-s", type=float, default=2.5 * 3600)
    a = ap.parse_args(argv)
    out, nd = Path(a.out), Path(a.nightdata)
    out.mkdir(parents=True, exist_ok=True)
    log = Logger(out / f"job2_seed{a.seed}.log")
    t_start = time.time()
    log("env", env_info())
    dev, dt = device_dtype()
    model_name = a.model
    if a.smoke:
        from .smoke import make_tiny_model
        model_name = make_tiny_model(out / f"tiny_s{a.seed}", [])
    tok = get_tokenizer(model_name)
    model = load_model(model_name, dt, dev)
    log("model loaded")
    assert_finite_forward(model, tok, log)
    anchors = [r["prompt"] for r in jl_read(nd / "anchors.jsonl")]
    items, gen, facts, arc = load_eval_sets(nd)
    arms = a.arms.split(",")
    if a.pilot:
        arms = ["A+"]
    arm_time = None
    for arm in arms:
        if arm_time and time.time() - t_start + arm_time > a.deadline_s:
            log(f"skipping {arm}: not enough time left before the deadline")
            continue
        t_arm = time.time()
        trainer = LoRATrainer(model, tok, a.seed, dev, use_scaler=(dev == "cuda" and str(dt) == "torch.float16"))
        log(f"=== arm {arm} seed {a.seed}")
        nights = train_arm(trainer, arm, nd, anchors, log, max_nights=1 if a.pilot else None)
        if a.pilot:
            health = pilot_health(nights[0], dev == "cuda")
            t_ev = time.time()
            run_eval(trainer.pm, tok, items, gen, facts, arc, a.bs, log)  # measured, so the projection includes the eval
            eval_s = time.time() - t_ev
            plan = jload(nd / "plan.json")
            max_units = max(v["per_arm"]["A+"]["total"] for v in plan["nights"].values())
            proj = pilot_projection(nights[0]["seconds"], eval_seconds=eval_s, units=nights[0]["units_total"], max_units=max_units)
            jdump(out / f"pilot_seed{a.seed}.json", {"night1": nights[0], "health": health, "projection": proj})
            log("PILOT", proj)
            return proj
        res = run_eval(trainer.pm, tok, items, gen, facts, arc, a.bs, log)
        jdump(out / "results" / f"{arm}_{a.seed}.json", {"arm": arm, "seed": a.seed, "nights": nights, "eval": res, "scale": os.environ.get("ASKONCE_SCALE", "1.0"),
                                                         "smoke": a.smoke, "env": env_info()})
        model = trainer.release()
        arm_time = time.time() - t_arm
        log(f"arm {arm} seed {a.seed} finished in {arm_time / 60:.1f} min")
    log("job2 lane done", f"{(time.time() - t_start) / 60:.1f} min")


if __name__ == "__main__":
    main()
