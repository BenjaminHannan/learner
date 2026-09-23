"""Secondary depth/size diagnostics on BOTH fixed rosters, no model selection.

Registered before the main heldout evaluations. Six read steps reuse the same
trained weights; no extra training and no claim that more compute must help.
Attention diagnostics concern only the final question row, not causal traces.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import premonition_token_memory as T
import premonition_memnn_compare as C

torch,data=T.torch,T.data


def plan(out,reference):
    folder=out/"reasoning-probe"
    folder.mkdir(exist_ok=False)
    C.write_new(folder/"plan.json",{"created_unix":time.time(),"source_sha256":C.sha(__file__),
            "seeds":[0,1,2],"read_steps":[3,6],"stress_manifest":str((reference/"stress/manifest.json").resolve()),
            "stress_manifest_sha256":C.sha(reference/"stress/manifest.json"),
            "selection":False,"training":False,"purpose":"secondary diagnostic of added context/depth/compute"})


@torch.no_grad()
def run(out):
    data.bootstrap()
    torch.set_num_threads(1)
    import premonition_handoff_diag as H
    p=json.loads((out/"reasoning-probe/plan.json").read_text())
    if C.sha(__file__)!=p["source_sha256"] or C.sha(p["stress_manifest"])!=p["stress_manifest_sha256"]:
        raise RuntimeError("probe source or manifest changed")
    manifest=json.loads(Path(p["stress_manifest"]).read_text())
    panels={}
    for name,row in manifest["panels"].items():
        if C.sha(row["path"])!=row["sha256"]: raise RuntimeError("stress data changed")
        panels[name]=torch.load(row["path"],weights_only=False,map_location="cpu")
    results={}
    for seed in p["seeds"]:
        ckpt=out/f"seed-{seed}/model.pt"
        saved=torch.load(ckpt,weights_only=False,map_location="cpu")
        results[seed]={}
        for steps in p["read_steps"]:
            config=dict(saved["architecture"],steps=steps)
            m=T.TokenMemoryReasoner(**config)
            m.load_state_dict(saved["state_dict"])
            m.eval()
            before=C.fingerprint(m)
            result={}
            for name,panel in panels.items():
                correct=[]
                for chunk in panel["chunks"]:
                    if manifest["panels"][name]["kind"]=="pair_suite":
                        x=data.from_batch(H._strip_labels(chunk["a"]))
                        targets=[r["answer_a"][0] for r in chunk["meta"]]
                    else:
                        x,targets=chunk["inputs"],chunk["targets"]
                    pred=m(x).argmax(-1).tolist()
                    correct.extend(int(a==b) for a,b in zip(pred,targets))
                assert len(correct)==panel["n"]
                result[name]={"count":sum(correct),"n":len(correct),"per_unit":correct}
                print(json.dumps({"seed":seed,"steps":steps,"stress":name,"count":sum(correct),"n":len(correct)}),flush=True)
            if C.fingerprint(m)!=before: raise RuntimeError("probe mutated weights")
            result["integrity"]={"weights_unchanged":True,"checkpoint_sha256":C.sha(ckpt)}
            results[seed][steps]=result
    C.write_new(out/"reasoning-probe/results.json",results)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("plan","run"))
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--reference",type=Path)
    a=parser.parse_args()
    if a.command=="plan":
        if a.reference is None: parser.error("plan needs --reference")
        plan(a.out,a.reference)
    else: run(a.out)
