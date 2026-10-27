"""One-change learning diagnostic: ordered evidence loss on the same token model.

All inference code is unchanged. Training targets identify the first link and
then endpoint line for two-hop questions; one-hop repeats its sole evidence line.
This is stronger ordered training supervision than unordered evidence labels.
No labels, role masks, teacher cards or gold intermediate entity enter forward.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
import time

import premonition_token_memory as T
torch,F,data = T.torch,T.F,T.data


@dataclass
class Targets:
    answer: torch.Tensor
    lines: torch.Tensor


def training_batch(rng,visits=16):
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec,visit,ANSWER
    spec=LadderSpec()
    memories,questions,owners,question_lines,answers,evidence=[],[],[],[],[],[]
    for v in range(visits):
        rows,_,_=visit(spec,rng,training=True)
        memories.append([[] if line.question else list(line.tokens) for line in rows])
        for j,line in enumerate(rows):
            if line.question:
                assert not(line.hops==2 and line.relation==spec.heldout_relation)
                questions.append(line.tokens[:line.tokens.index(ANSWER)+1])
                owners.append(v)
                question_lines.append(j)
                answers.append(line.answer[0])
                evidence.append([line.gold[0],line.gold[-1],line.gold[-1]])
    rng.randrange(1<<30)
    return data.pack(memories,questions,owners,question_lines),Targets(torch.tensor(answers),torch.tensor(evidence))


def evidence_mask(inputs,targets):
    """Training-only line-to-token target conversion; no semantic token parse."""
    v,l,t=inputs.memory.shape
    real=inputs.memory.ne(0).flatten(1)
    rank=real.long().cumsum(1)-1
    owner=torch.arange(v,device=real.device)[:,None].expand_as(real)
    width=max(1,int(real.sum(1).max()))
    line_ids=torch.full((v,width+1),-1,dtype=torch.long,device=real.device)
    source=torch.arange(l,device=real.device).repeat_interleave(t)[None].expand_as(real)
    line_ids[owner[real],rank[real]]=source[real]
    mask=line_ids[inputs.owner,None,:]==targets.lines[:,:,None]
    if not bool(mask.any(-1).all()):
        raise ValueError("an evidence target has no visible tokens")
    if not bool(inputs.eligible.gather(1,targets.lines).all()):
        raise ValueError("evidence target is not causally eligible")
    return mask


def loss_for(model,inputs,targets):
    logits,attention=model(inputs,trace=True)
    q,steps,heads,_,width=attention.shape
    last=inputs.questions.ne(0).sum(-1)-1
    read=attention.gather(3,last[:,None,None,None,None].expand(q,steps,heads,1,width)).squeeze(3).mean(2)
    mass=(read*evidence_mask(inputs,targets)).sum(-1)
    evidence=-mass.clamp_min(1e-12).log().mean()
    answer=F.cross_entropy(logits,targets.answer)
    return answer+.5*evidence,answer,evidence,logits


def training_step(model,optimizer,inputs,targets,step):
    for group in optimizer.param_groups:
        group["lr"] = 1e-3*min(1.,(step+1)/100)
    optimizer.zero_grad(set_to_none=True)
    loss,answer,evidence,logits=loss_for(model,inputs,targets)
    loss.backward()
    norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
    if not torch.isfinite(loss) or not torch.isfinite(norm):
        raise RuntimeError("nonfinite evidence training")
    optimizer.step()
    return {"loss":float(loss.detach()),"answer_loss":float(answer.detach()),
            "evidence_loss":float(evidence.detach()),
            "training_accuracy":float((logits.argmax(-1)==targets.answer).float().mean())}


if __name__=="__main__":
    # Development timing/learning diagnostic. No holdout evaluation or checkpoint
    # selection; no learned tensors are used by the fixed seed comparison.
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps",type=int,default=1000)
    args=parser.parse_args()
    torch.set_num_threads(1)
    torch.manual_seed(774111)
    m=T.TokenMemoryReasoner()
    optimizer=T.optimizer_for(m)
    rng=random.Random(774112)
    started=time.monotonic()
    for step in range(args.steps):
        x,y=training_batch(rng)
        row=training_step(m,optimizer,x,y,step)
        if (step+1)%100==0 or step==0:
            print(json.dumps({"step":step+1,"seconds":time.monotonic()-started,**row}),flush=True)
