"""Kaggle job 1: base K2 day logs for days 1-5 (deterministic sim-Ben in the loop, shared by all arms) + eval of arm P (base K2 + slot memory + rule).
  python -m sleep2.askonce.job1 --out $OUT [--smoke] [--model IFM/K2-Horizon-3.7B]
Outputs: $OUT/diary/day*.jsonl, $OUT/oracle/day*.jsonl, $OUT/nightdata_job1/eval_inputs.jsonl, $OUT/results/P_1.json, $OUT/timing.json"""
import argparse
import os
import time
from pathlib import Path

from .config import DATA, MODEL_ID, jdump, jload, sha256_file
from .eval_moves import load_eval_sets, run_eval
from .job_common import Logger, assert_finite_forward, device_dtype, env_info
from .model_io import MOVE_WORDS, generate, get_tokenizer, load_model
from .simulate_days import run_days
from .world import Persona, load_requests


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--bs", type=int, default=8)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = Logger(out / "job1.log")
    data = Path(a.data)
    log("env", env_info())
    T = {}
    t0 = time.time()
    persona, phr = Persona.load(data / "persona.json"), jload(data / "phrasings.json")
    requests = load_requests(path=data / "requests.jsonl")
    dev, dt = device_dtype()
    if a.smoke:
        from .smoke import make_tiny_model, scripted_gen
        name = make_tiny_model(out / "tiny", [])
        tok = get_tokenizer(name)
        model = load_model(name, dt, dev)
        gen_days = scripted_gen(persona, requests)
        log("SMOKE: tiny random model; day logs use the scripted policy")
    else:
        tok = get_tokenizer(a.model)
        model = load_model(a.model, dt, dev)
        log("model loaded", f"{time.time() - t0:.0f}s")
        assert_finite_forward(model, tok, log)

        def gen_days(prompts, max_new, temperature, seed):
            return generate(model, tok, prompts, max_new, temperature, seed, a.bs, log, first_words=MOVE_WORDS)
    T["load_s"] = round(time.time() - t0, 1)
    t1 = time.time()
    summary = run_days(gen_days, persona, phr, tok.bos_token or "", out_dir=out, requests=requests, log=log, max_other_frac=0.5)
    T["daylogs_s"] = round(time.time() - t1, 1)
    from .build_night_data import build_eval_inputs
    nd = out / "nightdata_job1"
    build_eval_inputs(persona, out / "diary", tok.bos_token or "", nd, requests=requests, log=log)
    (nd / "eval_inputs.sha256").write_text(sha256_file(nd / "eval_inputs.jsonl") + "\n")
    # arm P: base model, slot memory + prompt rule, no training
    import shutil
    for f in ("phrasings.json", "arc_easy_500.json"):
        shutil.copy(data / f, nd / f)
    items, gen, facts, arc = load_eval_sets(nd)
    t2 = time.time()
    res = run_eval(model, tok, items, gen, facts, arc, a.bs, log)
    T["eval_s"] = round(time.time() - t2, 1)
    jdump(out / "results" / "P_1.json", {"arm": "P", "seed": 1, "eval": res, "nights": [], "scale": os.environ.get("ASKONCE_SCALE", "1.0"), "smoke": a.smoke})
    T["total_s"] = round(time.time() - t0, 1)
    jdump(out / "timing.json", T)
    log("job1 done", T)
    return T


if __name__ == "__main__":
    main()
