import json, collections
A=["F","R","N","O"]
rows={a:{json.loads(l)["question_id"]:json.loads(l) for l in open(f"rows_{a}.jsonl")} for a in A}
types=sorted({r["type"] for r in rows["F"].values()})
acc=lambda a,f=lambda r:True:(lambda rs:sum(r["correct"] for r in rs)/len(rs))([r for r in rows[a].values() if f(r)])
res={"accuracy":{},"by_type":{},"mean_prompt_tokens":{},"errors":{}}
for a in A:
    res["accuracy"][a]=acc(a)
    res["by_type"][a]={t:acc(a,lambda r,t=t:r["type"]==t) for t in types}
    res["mean_prompt_tokens"][a]=sum(r["prompt_tokens"] for r in rows[a].values())/60
    res["errors"][a]=sum(1 for r in rows[a].values() if r.get("error"))
def pair(x,y):
    w=sum(rows[x][q]["correct"] and not rows[y][q]["correct"] for q in rows[x]); l=sum(rows[y][q]["correct"] and not rows[x][q]["correct"] for q in rows[x])
    return {"wins":w,"losses":l}
res["paired"]={"N_vs_R":pair("N","R"),"N_vs_F":pair("N","F")}
ku=lambda r:r["type"] in("knowledge-update","temporal-reasoning")
n_ku=sum(r["correct"] for r in rows["N"].values() if ku(r)); r_ku=sum(r["correct"] for r in rows["R"].values() if ku(r))
res["KU_TR_correct"]={"N":n_ku,"R":r_ku}
N,R,F=res["accuracy"]["N"],res["accuracy"]["R"],res["accuracy"]["F"]
ratio=res["mean_prompt_tokens"]["N"]/res["mean_prompt_tokens"]["F"]
res["verdicts"]={"P1":{"pass":N>=R+0.08,"N":N,"R":R,"diff_pts":100*(N-R)},
 "P2":{"pass":n_ku>=r_ku,"N":n_ku,"R":r_ku},
 "P3":{"pass":ratio<=1/20 and N>=F-0.10,"token_ratio":ratio,"N":N,"F":F},
 "wrong_if_N_le_R":N<=R}
u=json.load(open("usage.json")); res["spend_this_process"]=u
json.dump(res,open("result.json","w"),indent=1); print(json.dumps(res,indent=1))
