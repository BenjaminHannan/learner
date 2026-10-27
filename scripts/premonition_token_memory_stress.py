"""Secondary, pre-outcome intelligence stress tests; never training inputs.

12-person worlds keep the learned grammar; three-hop worlds add a second LINK
token, so that test changes both depth and question syntax. Neither is admission.
Semantic parsing below is an evaluator/data audit only; model inputs are the
same four visible tensors as normal, with no parsed roles or intermediate truth.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import random
import time

import premonition_token_memory as T
import premonition_memnn_compare as C

torch, data = T.torch, T.data
N = 512


def generate(out):
    data.bootstrap()
    torch.set_num_threads(1)
    import premonition_pair_suite as PS
    from premonition.toy_ladder import LadderSpec, visit, QUESTION, ANSWER, WORLD, FIRST_FREE
    folder = out / "stress"
    folder.mkdir(exist_ok=False)
    manifest = {"source_sha256":C.sha(__file__),"created_unix":time.time(),"panels":{},
                "purpose":"secondary diagnostics, fixed before any model outcome",
                "thresholds":None,"used_for_training_or_selection":False}
    for idx,name in enumerate(list(PS.CELLS)[:3]):
        original = PS.CELLS[name]
        cfg = deepcopy(original)
        cfg.update(n=N,seed=202609202001+idx)
        PS.CELLS[name] = cfg
        spec = LadderSpec(entities=12)
        try:
            panel = PS.generate_set(name,spec=spec)
            audit = PS.audit_set(panel,spec)
        finally:
            PS.CELLS[name] = original
        assert audit["interpreter"]["scored_units_correct"] == N
        path = folder / f"people12-{name}.pt"
        torch.save(panel,path)
        manifest["panels"][f"people12-{name}"] = {"path":str(path.resolve()),"sha256":C.sha(path),
                                                      "n":N,"seed":cfg["seed"],"kind":"pair_suite"}
        C.write_new(folder/f"people12-{name}-audit.json",audit)
    memories,questions,truth,lines_at = [],[],[],[]
    spec = LadderSpec()
    for index in range(N):
        rng = random.Random(f"token-memory-three-hop-202609202004-{index}")
        rows,where,facts,_ = PS._make_single(spec,rng,2,"heldout")
        # _make_single returns the public visible lines and evaluator facts. Build
        # the full graph from those lines to define/audit the extra-link target.
        links,attributes = {},{}
        for line in rows:
            t = line.tokens
            if line.question or len(t)<4 or t[0]!=WORLD or t[1]<spec.vocab_size:
                continue
            if t[2] == spec.link:
                links[t[1]] = t[3]
            elif FIRST_FREE <= t[2] < FIRST_FREE+spec.relations:
                attributes[(t[1],t[2])] = t[3]
        subject = spec.vocab_size+facts["subject"]
        relation = spec.relation(spec.heldout_relation)
        target = attributes[(links[links[subject]],relation)]
        q = [QUESTION,subject,spec.link,spec.link,relation,ANSWER]
        memories.append([[] if r.question else list(r.tokens) for r in rows])
        questions.append(q)
        truth.append(target)
        lines_at.append(where)
    chunks=[]
    for begin in range(0,N,32):
        end=min(N,begin+32)
        chunks.append({"inputs":data.pack(memories[begin:end],questions[begin:end],list(range(end-begin)),
                                           lines_at[begin:end]),"targets":truth[begin:end]})
    path=folder/"three-hop-heldout.pt"
    torch.save({"chunks":chunks,"n":N},path)
    manifest["panels"]["three-hop-heldout"]={"path":str(path.resolve()),"sha256":C.sha(path),"n":N,
        "seed":"202609202004","kind":"inputs","changes":"extra LINK changes depth and syntax"}
    C.write_new(folder/"manifest.json",manifest)
    print(json.dumps({"stress_panels":list(manifest["panels"]),"n_each":N}),flush=True)


@torch.no_grad()
def evaluate(out):
    data.bootstrap()
    torch.set_num_threads(1)
    import premonition_handoff_diag as H
    folder=out/"stress"
    manifest=json.loads((folder/"manifest.json").read_text())
    if C.sha(__file__)!=manifest["source_sha256"]:
        raise RuntimeError("stress source changed")
    panels={}
    for name,row in manifest["panels"].items():
        if C.sha(row["path"])!=row["sha256"]:
            raise RuntimeError("stress panel changed")
        panels[name]=torch.load(row["path"],map_location="cpu",weights_only=False)
    result={}
    for seed in (0,1,2):
        ckpt=out/f"seed-{seed}/model.pt"
        saved=torch.load(ckpt,map_location="cpu",weights_only=False)
        m=T.TokenMemoryReasoner(**saved["architecture"])
        m.load_state_dict(saved["state_dict"])
        m.eval()
        before=C.fingerprint(m)
        result[seed]={}
        for name,panel in panels.items():
            correct=[]
            for chunk in panel["chunks"]:
                if manifest["panels"][name]["kind"]=="pair_suite":
                    x=data.from_batch(H._strip_labels(chunk["a"]))
                    targets=[r["answer_a"][0] for r in chunk["meta"]]
                else:
                    x,targets=chunk["inputs"],chunk["targets"]
                pred=m(x).argmax(-1).tolist()
                correct.extend(int(p==a) for p,a in zip(pred,targets))
            assert len(correct)==panel["n"]
            result[seed][name]={"count":sum(correct),"n":len(correct),"per_unit":correct}
            print(json.dumps({"seed":seed,"stress":name,"count":sum(correct),"n":len(correct)}),flush=True)
        assert C.fingerprint(m)==before
        result[seed]["integrity"]={"weights_unchanged":True,"checkpoint_sha256":C.sha(ckpt)}
    C.write_new(folder/"results.json",result)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("generate","evaluate"))
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    (generate if args.command=="generate" else evaluate)(args.out)
