import json, time, urllib.request, concurrent.futures as cf
URL="http://localhost:8080/v1/chat/completions"
P="Write a short, simple paragraph (about 150 words) for a children's reading book about a girl named Mara who lends her red kite to her neighbour Tom for a day."
def one(i):
    body={"model":"qwen","messages":[{"role":"user","content":P+f" (variant {i})"}],"max_tokens":300,"temperature":0.7,"chat_template_kwargs":{"enable_thinking":False}}
    t=time.time(); r=urllib.request.urlopen(urllib.request.Request(URL,data=json.dumps(body).encode(),headers={"Content-Type":"application/json","Authorization":"Bearer x"}),timeout=300); d=json.load(r)
    u=d["usage"]; txt=d["choices"][0]["message"]["content"]
    return u["completion_tokens"], time.time()-t, ("<think" in txt), txt[:80].replace("\n"," ")
one(0)  # warm
n,s,th,tx=one(1); print(f"single: {n} tok in {s:.1f}s = {n/s:.1f} tok/s  think_tag={th}  '{tx}'")
t=time.time()
with cf.ThreadPoolExecutor(8) as ex: res=list(ex.map(one,range(10,18)))
w=time.time()-t; tot=sum(r[0] for r in res)
print(f"8 parallel: {tot} tok in {w:.1f}s = {tot/w:.1f} tok/s aggregate ({tot/w/8:.1f} per stream)  think_tag={any(r[2] for r in res)}")
