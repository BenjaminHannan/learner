"""Fixed-seed comparison of the same architecture with ordered training feedback.

One experimental change from token-memory-v1: answer CE + 0.5 * ordered evidence
CE. No teacher insertion and no inference change. Reuses the pre-generated old,
fresh and stress worlds; records the extra training privilege explicitly.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import time

import premonition_token_evidence as E
import premonition_token_memory_run as R
import premonition_memnn_compare as C

torch,T,data=E.torch,E.T,E.data


def extra_sources():
    return {str(p.relative_to(data.ROOT)):C.sha(p) for p in
            (Path(__file__),Path(E.__file__),data.ROOT/"tests/test_premonition_token_evidence.py")}


def plan(out,reference):
    old=R.load_plan(reference)
    out.mkdir(exist_ok=False,parents=True)
    p=dict(old)
    p.update(experiment="token-memory-ordered-evidence-v1",created_unix=time.time(),
             loss="answer CE + 0.5 * ordered supporting-line attention CE",
             evidence_supervision=True,
             training_privilege="gold supporting-line order: link first, endpoint after; one-hop repeats sole line",
             inference_privilege="none; identical TokenMemoryReasoner forward as answer-only",
             reference_plan=str((reference/"plan.json").resolve()),
             reference_plan_sha256=C.sha(reference/"plan.json"),evidence_sources=extra_sources(),
             rationale="Answer-only runs stalled early; disjoint diagnostic demonstrated falling evidence loss. No heldout outcomes used.")
    C.write_new(out/"plan.json",p)
    print(json.dumps({"plan":str(out/"plan.json"),"seeds":[0,1,2],"same_architecture":True}),flush=True)


def load(out):
    p=R.load_plan(out)
    if p["evidence_sources"]!=extra_sources() or C.sha(p["reference_plan"])!=p["reference_plan_sha256"]:
        raise RuntimeError("evidence source/reference changed")
    return p


def run(out,seed):
    p=load(out)
    data.bootstrap()
    torch.set_num_threads(1)
    job=next(j for j in p["jobs"] if j["seed"]==seed)
    folder=out/f"seed-{seed}"
    folder.mkdir(exist_ok=False)
    torch.manual_seed(seed)
    m=T.TokenMemoryReasoner(**p["architecture"])
    initial=C.fingerprint(m)
    optimizer=T.optimizer_for(m)
    rng=random.Random(p["data_seed"])
    start=time.monotonic()
    spent,updates,history,stop=0,0,[],"matched_exposure"
    for step in range(job["updates"]):
        if time.monotonic()-start>=p["max_training_seconds_per_job"]:
            stop="time_limit"
            break
        x,y=E.training_batch(rng,p["visits_per_update"])
        cost=T.training_flops(x,m)
        if spent+cost>job["flop_ceiling"]:
            stop="flop_ceiling"
            break
        stats=E.training_step(m,optimizer,x,y,step)
        spent+=cost
        updates+=1
        if updates==1 or updates%500==0:
            row={"seed":seed,"step":updates,"seconds":time.monotonic()-start,"flops":spent,**stats}
            history.append(row)
            print(json.dumps(row),flush=True)
    train={"seed":seed,"updates":updates,"expected_updates":job["updates"],
           "exposure_complete":updates==job["updates"],"stop":stop,"counted_flops":spent,
           "flop_share":spent/job["flop_ceiling"],"seconds":time.monotonic()-start,
           "initial_fingerprint":initial,"final_fingerprint":C.fingerprint(m),"history":history,
           "heldout_two_hop_training_questions":0,"ordered_evidence_supervision":True}
    ckpt=folder/"model.pt"
    torch.save({"state_dict":m.state_dict(),"optimizer":optimizer.state_dict(),"architecture":p["architecture"],
                "seed":seed,"updates":updates,"rng_state":rng.getstate(),"torch_rng_state":torch.get_rng_state(),
                "plan_sha256":C.sha(out/"plan.json")},ckpt)
    train["checkpoint_sha256"]=C.sha(ckpt)
    C.write_new(folder/"training.json",train)
    m.eval()
    old=R.score(m,C.load_panels())
    C.write_new(folder/"old-evaluation.json",old)
    fresh={}
    for name,row in p["fresh_panels"].items():
        if C.sha(row["path"])!=row["sha256"]:
            raise RuntimeError("fresh data changed")
        fresh[name]=torch.load(row["path"],map_location="cpu",weights_only=False)
    confirm=R.score(m,fresh,fresh=True)
    C.write_new(folder/"fresh-evaluation.json",confirm)
    lesion=R.score(m,{"c3_own_heldout_two_hop":fresh["c3_own_heldout_two_hop"]},fresh=True,lesion=True)
    C.write_new(folder/"memory-lesion.json",lesion)
    reloaded=T.TokenMemoryReasoner(**p["architecture"])
    reloaded.load_state_dict(torch.load(ckpt,map_location="cpu",weights_only=False)["state_dict"])
    reloaded.eval()
    with torch.no_grad():
        if not torch.equal(m(x),reloaded(x)):
            raise RuntimeError("checkpoint reload changed predictions")
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
