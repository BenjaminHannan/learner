import sys; sys.path.insert(0,'scripts')
import claude_blurt1 as B1, claude_blurt2 as B2, claude_dl1_nights as D1, claude_dl3_replay as R
M='/root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc'
s=B2.Solver(M); s.model.name_or_path=M
pool=R.make_pool(s, 8, 5)
print('pool', len(pool), [(q[:50], len(a), f) for q,a,f in pool])
m=D1.fresh_model(s)
ps=B2.puzzles(70011,3)
items=[("puzzle",p,B1.solve(p["nums"],p["target"])) for p in ps if B1.solve(p["nums"],p["target"])]
items+=[("replay",q,a,f) for q,a,f in pool[:3]]
for it in items:
    pr,full=R._pair_ids(s,it); print(it[0], len(pr), len(full), repr(s.tok.decode(full[len(pr):])[-30:]))
print(R.train_mixed(s,m,items,1))
