"""6000-update screen: ordered evidence plus width-scaled linear initialization.

Chosen from a disjoint training-only initialization diagnostic. All earlier runs
are retained. Same model/optimizer/inference as the evidence arm; a shorter fixed
training exposure, so this is NOT a matched-exposure historical comparison.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import time

import premonition_token_evidence as E
import premonition_token_evidence_run as ER
import premonition_token_initialization_probe as I
import premonition_token_memory_run as R
import premonition_memnn_compare as C

torch,T,data=E.torch,E.T,E.data


def sources():
    return {str(p.relative_to(data.ROOT)):C.sha(p) for p in (Path(__file__),Path(I.__file__))}


def plan(out,reference):
    p=ER.load(reference)
    out.mkdir(exist_ok=False,parents=True)
    p.update(experiment="token-memory-scaled-initialization-v1",created_unix=time.time(),
             initialization="same initial normal draws, linear std changed from .02 to 1/sqrt(3*fan_in)",
             scaled_sources=sources(),parent_plan=str((reference/"plan.json").resolve()),
             parent_plan_sha256=C.sha(reference/"plan.json"),
             exposure_matched_to_historical=False,max_training_seconds_per_job=900,max_job_seconds=1200,
             rationale="Disjoint 1000-update training diagnostic improved from 6.25% to 43.75% final-batch accuracy; no holdout result used to select initialization.")
    for job in p["jobs"]:
        job["historical_updates"]=job["updates"]
        job["updates"]=6000
    p["primary_success"]="All three seeds complete 6000 updates and pass all six original answer cutoffs and all fresh raw thresholds. No promotion otherwise."
    C.write_new(out/"plan.json",p)
    print(json.dumps({"plan":str(out/"plan.json"),"seeds":[0,1,2],"updates":6000}),flush=True)


def load(out):
    p=ER.load(out)
    if sources()!=p["scaled_sources"] or C.sha(p["parent_plan"])!=p["parent_plan_sha256"]:
        raise RuntimeError("scaled source/reference changed")
    return p


def run(out,seed):
    p=load(out)
    data.bootstrap()
    torch.set_num_threads(1)
    job=next(j for j in p["jobs"] if j["seed"]==seed)
    folder=out/f"seed-{seed}"
    folder.mkdir(exist_ok=False)
    torch.manual_seed(seed)
    model=T.TokenMemoryReasoner(**p["architecture"])
    I.rescale(model)
    initial=C.fingerprint(model)
    optimizer=T.optimizer_for(model)
    rng=random.Random(p["data_seed"])
    start=time.monotonic()
    spent,updates,history,stop=0,0,[],"registered_updates"
    for step in range(job["updates"]):
        if time.monotonic()-start>=p["max_training_seconds_per_job"]:
            stop="time_limit"
            break
        x,y=E.training_batch(rng,p["visits_per_update"])
        cost=T.training_flops(x,model)
        if spent+cost>job["flop_ceiling"]:
            stop="flop_ceiling"
            break
        stats=E.training_step(model,optimizer,x,y,step)
        spent+=cost
        updates+=1
        if updates==1 or updates%500==0:
            row={"seed":seed,"step":updates,"seconds":time.monotonic()-start,"flops":spent,**stats}
            history.append(row)
            print(json.dumps(row),flush=True)
    train={"seed":seed,"updates":updates,"expected_updates":job["updates"],
           "exposure_complete":updates==job["updates"],"exposure_matched_to_historical":False,
           "historical_updates":job["historical_updates"],"stop":stop,"counted_flops":spent,
           "flop_share":spent/job["flop_ceiling"],"seconds":time.monotonic()-start,
           "initial_fingerprint":initial,"final_fingerprint":C.fingerprint(model),"history":history,
           "heldout_two_hop_training_questions":0,"ordered_evidence_supervision":True,
           "width_scaled_linear_initialization":True}
    ckpt=folder/"model.pt"
    torch.save({"state_dict":model.state_dict(),"optimizer":optimizer.state_dict(),"architecture":p["architecture"],
                "seed":seed,"updates":updates,"rng_state":rng.getstate(),"torch_rng_state":torch.get_rng_state(),
                "plan_sha256":C.sha(out/"plan.json")},ckpt)
    train["checkpoint_sha256"]=C.sha(ckpt)
    C.write_new(folder/"training.json",train)
    model.eval()
    old=R.score(model,C.load_panels())
    C.write_new(folder/"old-evaluation.json",old)
    fresh={}
    for name,row in p["fresh_panels"].items():
        if C.sha(row["path"])!=row["sha256"]: raise RuntimeError("fresh panel changed")
        fresh[name]=torch.load(row["path"],weights_only=False,map_location="cpu")
    confirm=R.score(model,fresh,fresh=True)
    C.write_new(folder/"fresh-evaluation.json",confirm)
    lesion=R.score(model,{"c3_own_heldout_two_hop":fresh["c3_own_heldout_two_hop"]},fresh=True,lesion=True)
    C.write_new(folder/"memory-lesion.json",lesion)
    reloaded=T.TokenMemoryReasoner(**p["architecture"])
    reloaded.load_state_dict(torch.load(ckpt,weights_only=False,map_location="cpu")["state_dict"])
    reloaded.eval()
    with torch.no_grad():
        if not torch.equal(model(x),reloaded(x)): raise RuntimeError("reload changed predictions")
    load(out)
    C.write_new(folder/"completion.json",{"seconds":time.monotonic()-start,
                "exposure_complete":train["exposure_complete"],"checkpoint_reload_equal":True,
                "old_all_six":old["all_six_answer_thresholds"],"fresh_all_six":confirm["all_six_answer_thresholds"],
                "sources_unchanged":True})


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("plan","run"))
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--reference",type=Path)
    parser.add_argument("--seed",type=int,choices=(0,1,2))
    a=parser.parse_args()
    if a.command=="plan":
        if a.reference is None: parser.error("plan requires --reference")
        plan(a.out,a.reference)
    else:
        if a.seed is None: parser.error("run requires --seed")
        run(a.out,a.seed)
