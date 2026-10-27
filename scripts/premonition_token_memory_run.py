"""Fixed three-seed screen of the token-memory successor; CPU, opt-in only.

Plan before training; exact historical example/update exposure, not equal FLOPs.
Old and newly seeded worlds test relation transfer and causal counterfactuals.
All jobs and failures count. This is not an original hard-card G_pair admission.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import random
import sys
import time

import premonition_token_memory as T
import premonition_memnn_compare as C

torch, data = T.torch, T.data
ROOT = data.ROOT
SEEDS = (0, 1, 2)


def sources():
    result = C.sources()
    for path in (Path(__file__), Path(T.__file__), ROOT / "tests/test_premonition_token_memory.py"):
        result[str(path.relative_to(ROOT))] = C.sha(path)
    return result


def plan(out):
    data.bootstrap()
    torch.set_num_threads(1)
    import premonition_pair_suite as PS
    from premonition.toy_ladder import LadderSpec
    out.mkdir(parents=True, exist_ok=False)
    jobs = []
    for seed in SEEDS:
        path = C.CONTROL / f"runs/long-s{seed}-12000.json"
        record = json.loads(path.read_text())
        ckpt = C.CONTROL / f"ckpt/long-s{seed}-12000.pt"
        if C.sha(ckpt) != record["ckpt_sha256"]:
            raise RuntimeError("historical checkpoint hash mismatch")
        jobs.append({"seed": seed, "updates": record["train_report"]["steps"],
                     "flop_ceiling": record["train_report"]["flop_budget"],
                     "historical_flops": record["train_report"]["flops"],
                     "control_checkpoint": str(ckpt), "control_sha256": C.sha(ckpt),
                     "control_record": str(path), "control_record_sha256": C.sha(path)})
    fresh = {}
    for name, cfg in PS.CELLS.items():
        changed = deepcopy(cfg)
        changed.update(seed=202609201000+cfg["cell"], n=512)
        PS.CELLS[name] = changed
        try:
            dataset = PS.generate_set(name)
            audit = PS.audit_set(dataset, LadderSpec())
            if audit["interpreter"]["scored_units_correct"] != dataset["n"]:
                raise RuntimeError("fresh panel disagrees with the exact interpreter")
        finally:
            PS.CELLS[name] = cfg
        path = out / f"fresh-{name}.pt"
        torch.save(dataset,path)
        C.write_new(out / f"fresh-{name}-audit.json", audit)
        fresh[name] = {"path": str(path.resolve()), "sha256": C.sha(path),
                       "seed": changed["seed"], "n": 512,
                       "cutoff": 487 if cfg["cell"] <= 2 else 461}
        print(json.dumps({"fresh_panel": name, "n":512, "sha256":fresh[name]["sha256"]}),flush=True)
    model = T.TokenMemoryReasoner()
    registration = {
        "experiment": "token-memory-v1", "created_unix":time.time(), "jobs":jobs,
        "architecture":{"vocab":68,"width":48,"heads":4,"steps":3},
        "parameters":model.parameters_count(), "plain_parameters":79748,
        "loss":"answer-token cross entropy only", "evidence_supervision":False,
        "data_seed":1101, "visits_per_update":16, "device":"cpu", "threads_per_job":1,
        "concurrent_jobs":3, "max_training_seconds_per_job":1500, "max_job_seconds":1800,
        "optimizer":{"name":"AdamW","lr":.001,"betas":[.9,.99],"weight_decay":.1,
                     "eps":1e-8,"warmup_updates":100,"clip":1.},
        "selection":"fixed numerical seeds 0,1,2; all reported; no validation checkpoint selection",
        "old_panel_manifest":str(C.PANEL),"old_panel_sha256":C.sha(C.PANEL),
        "fresh_panels":fresh,"sources":sources(),
        "primary_success":"Every fixed seed completes exposure and passes all six original answer cutoffs; no stuck seed.",
        "confirmation":"Every seed reaches >=95% one-hop/practised and >=90% heldout/paired accuracy on fresh 512-unit cells.",
        "promotion":False,"official_G_pair_admission":False,"equal_spent_flops":False,
        "limitations":["historical controls, different supervision and hardware",
                       "soft full-token reads replace original hard-card contract",
                       "single-token classifier plus fixed EOS; not a language model",
                       "fresh worlds share the toy grammar; no open-domain intelligence claim",
                       "line order ignored; no temporal fact-update policy",
                       "three seeds cannot establish broad training reliability",
                       "new architecture combines changes; no isolated-component causal claim"],
    }
    C.write_new(out / "plan.json",registration)
    print(json.dumps({"plan":str(out/"plan.json"),"parameters":registration["parameters"]}),flush=True)


def load_plan(out):
    p = json.loads((out/"plan.json").read_text())
    if p["sources"] != sources() or p["old_panel_sha256"] != C.sha(C.PANEL):
        raise RuntimeError("registered sources or panels changed")
    return p


@torch.no_grad()
def score(model, panels, *, fresh=False, lesion=False):
    import premonition_pair_suite as PS
    import premonition_handoff_diag as H
    before = C.fingerprint(model)
    cells = {}
    for name, dataset in panels.items():
        units, predictions = [], []
        for chunk in dataset["chunks"]:
            produced, targets = {}, {}
            for side in (("a","b") if dataset["kind"] == "pair" else ("a",)):
                x = data.from_batch(H._strip_labels(chunk[side]))
                if lesion:
                    x = replace(x,eligible=torch.zeros_like(x.eligible))
                produced[side] = [[prediction,2] for prediction in model(x).argmax(-1).tolist()]
                targets[side] = [m[f"answer_{side}"] for m in chunk["meta"]]
            units.extend(C.score_predictions(produced["a"],targets["a"],produced.get("b"),
                                             targets.get("b"),dataset["invariant"]))
            predictions.append(produced)
        n = dataset["n"]
        assert len(units) == n
        cutoff = (487 if PS.CELLS[name]["cell"] <= 2 else 461) if fresh else PS.CELLS[name]["cutoff"]
        cells[name] = {"count":sum(units),"n":n,"cutoff":cutoff,"passed":sum(units)>=cutoff,
                       "per_unit":units,"predictions":predictions}
        print(json.dumps({"cell":name,"fresh":fresh,"lesion":lesion,"count":sum(units),"n":n}),flush=True)
    if C.fingerprint(model) != before:
        raise RuntimeError("evaluation changed weights")
    return {"cells":cells,"all_six_answer_thresholds":len(cells)==6 and all(c["passed"] for c in cells.values()),
            "weights_unchanged":True,"fingerprint":before,"fresh":fresh,"official_G_pair_admission":False}


def run(out, seed):
    registration = load_plan(out)
    data.bootstrap()
    torch.set_num_threads(1)
    started = time.monotonic()
    deadline = started + registration["max_job_seconds"]
    job = next(j for j in registration["jobs"] if j["seed"] == seed)
    folder = out / f"seed-{seed}"
    folder.mkdir(exist_ok=False)
    torch.manual_seed(seed)
    model = T.TokenMemoryReasoner(**registration["architecture"])
    initial = C.fingerprint(model)
    optimizer = T.optimizer_for(model)
    rng = random.Random(registration["data_seed"])
    history, spent, updates, stop = [], 0, 0, "matched_exposure"
    train_started = time.monotonic()
    for step in range(job["updates"]):
        if time.monotonic()-train_started >= registration["max_training_seconds_per_job"]:
            stop = "time_limit"
            break
        x,y = data.training_batch(rng,registration["visits_per_update"])
        cost = T.training_flops(x,model)
        if spent + cost > job["flop_ceiling"]:
            stop = "flop_ceiling"
            break
        loss, accuracy = T.training_step(model,optimizer,x,y,step)
        spent += cost
        updates += 1
        if updates % 500 == 0 or updates == 1:
            row = {"seed":seed,"step":updates,"loss":loss,"training_accuracy":accuracy,
                   "flops":spent,"seconds":time.monotonic()-train_started}
            history.append(row)
            print(json.dumps(row),flush=True)
    train = {"seed":seed,"updates":updates,"expected_updates":job["updates"],
             "exposure_complete":updates==job["updates"],"stop":stop,"counted_flops":spent,
             "flop_share":spent/job["flop_ceiling"],"seconds":time.monotonic()-train_started,
             "initial_fingerprint":initial,"final_fingerprint":C.fingerprint(model),"history":history,
             "heldout_two_hop_training_questions":0}
    checkpoint = folder/"model.pt"
    torch.save({"state_dict":model.state_dict(),"optimizer":optimizer.state_dict(),
                "architecture":registration["architecture"],"seed":seed,"updates":updates,
                "rng_state":rng.getstate(),"torch_rng_state":torch.get_rng_state(),
                "plan_sha256":C.sha(out/"plan.json")},checkpoint)
    train["checkpoint_sha256"] = C.sha(checkpoint)
    C.write_new(folder/"training.json",train)
    model.eval()
    old = C.load_panels()
    result = score(model,old)
    C.write_new(folder/"old-evaluation.json",result)
    fresh = {}
    for name,row in registration["fresh_panels"].items():
        if C.sha(row["path"]) != row["sha256"]:
            raise RuntimeError("fresh panel changed")
        fresh[name] = torch.load(row["path"],map_location="cpu",weights_only=False)
    confirmation = score(model,fresh,fresh=True)
    C.write_new(folder/"fresh-evaluation.json",confirmation)
    lesion = score(model,{"c3_own_heldout_two_hop":fresh["c3_own_heldout_two_hop"]},fresh=True,lesion=True)
    C.write_new(folder/"memory-lesion.json",lesion)
    # Replay persistence with the exact same visible inputs.
    reloaded = T.TokenMemoryReasoner(**registration["architecture"])
    reloaded.load_state_dict(torch.load(checkpoint,weights_only=False,map_location="cpu")["state_dict"])
    reloaded.eval()
    with torch.no_grad():
        if not torch.equal(model(x),reloaded(x)):
            raise RuntimeError("checkpoint reload changed predictions")
    del reloaded, optimizer
    import premonition_first_card_probe as P
    if C.sha(job["control_checkpoint"]) != job["control_sha256"]:
        raise RuntimeError("control checkpoint changed")
    path = Path(job["control_checkpoint"])
    plain,_ = P.load_from(path.stem,path.parent)
    plain_fresh = C.score_all(plain,fresh,deadline,memnn=False)
    # The reused scorer's fixed old-count thresholds need fresh-count replacement.
    for name,row in plain_fresh["cells"].items():
        row["cutoff"] = registration["fresh_panels"][name]["cutoff"]
        row["passed"] = row["count"] >= row["cutoff"]
    plain_fresh["all_six_answer_thresholds"] = all(r["passed"] for r in plain_fresh["cells"].values())
    plain_fresh["fresh_panel"] = True
    C.write_new(folder/"plain-fresh-evaluation.json",plain_fresh)
    if sources() != registration["sources"]:
        raise RuntimeError("source closure changed during run")
    C.write_new(folder/"completion.json",{"seconds":time.monotonic()-started,
                "exposure_complete":train["exposure_complete"],"checkpoint_reload_equal":True,
                "old_all_six":result["all_six_answer_thresholds"],
                "fresh_all_six":confirmation["all_six_answer_thresholds"],"sources_unchanged":True})


def report(out):
    p = load_plan(out)
    records = []
    for seed in SEEDS:
        folder = out/f"seed-{seed}"
        records.append({name:json.loads((folder/f"{name}.json").read_text()) for name in
                        ("training","old-evaluation","fresh-evaluation","plain-fresh-evaluation","completion")})
    names = list(records[0]["old-evaluation"]["cells"])
    lines = ["# Token-memory reasoning screen", "", "79,316 parameters; fixed seeds 0, 1, 2. Same training-example/update exposure as historical controls if all jobs complete; **not equal spent compute**. Answer-only training; no evidence or role targets. Opt-in successor, not a change to existing defaults.", "",
             "| Seed | Model/panel | " + " | ".join(names) + " | All six |",
             "|---|---|" + "---|"*7]
    for seed,r in zip(SEEDS,records):
        for name in ("old-evaluation","fresh-evaluation","plain-fresh-evaluation"):
            result = r[name]
            cells = " | ".join(f"{c['count']}/{c['n']}" for c in result["cells"].values())
            lines.append(f"| {seed} | {name} | {cells} | {result['all_six_answer_thresholds']} |")
    lines += ["", "Original panels use the unchanged six answer cutoffs. Fresh panels have 512 units per cell, with raw accuracy thresholds of >=95% (one-hop/practised) and >=90% (transfer/pairs). Fresh thresholds are not confidence-certified admission gates.", "",
              "Passing familiar questions alone is not success. All three seeds must pass all original cells and confirm on new worlds before claiming this recipe solved the specified transfer task. Neither outcome establishes general intelligence, natural-language ability, longer-chain generalization, or scalable training reliability.", "",
              "Tradeoffs: all story tokens are attended, so this gives up sparse-read efficiency; line order is ignored; final output is a one-token classifier with fixed EOS. Several architectural changes are combined, so this does not isolate each change's contribution.", ""]
    for seed,r in zip(SEEDS,records):
        t = r["training"]
        lines.append(f"Seed {seed}: {t['updates']:,}/{t['expected_updates']:,} updates; {t['counted_flops']:,} counted FLOPs ({100*t['flop_share']:.2f}% of historical ceiling); {t['seconds']:.1f} training seconds; exposure complete {t['exposure_complete']}.")
    with (out/"REPORT.md").open("x") as f:
        f.write("\n".join(lines)+"\n")
    C.write_new(out/"completion.json",{"all_exposure_complete":all(r["training"]["exposure_complete"] for r in records),
                  "all_original_pass":all(r["completion"]["old_all_six"] for r in records),
                  "all_fresh_pass":all(r["completion"]["fresh_all_six"] for r in records),
                  "equal_spent_flops":False,"paid_cost":0,"sources_unchanged":p["sources"]==sources()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("plan","run","report"))
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--seed",type=int,choices=SEEDS)
    a = parser.parse_args()
    if a.command == "plan":
        plan(a.out)
    elif a.command == "report":
        report(a.out)
    elif a.seed is None:
        parser.error("run requires --seed")
    else:
        run(a.out,a.seed)
