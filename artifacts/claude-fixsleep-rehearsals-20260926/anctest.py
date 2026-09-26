import sys; sys.path.insert(0,'scripts')
import claude_blurt1 as B1, claude_blurt2 as B2, claude_dl1_nights as D1, claude_dl3_replay as R, claude_dl4_anchor as K
M='/root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc'
s=B2.Solver(M); s.model.name_or_path=M
pool=R.make_pool(s, 8, 9)
print('pool', len(pool))
m=D1.fresh_model(s)
print('kl at start (should be 0):', float(K.anchor_loss(s,m,pool[0])))
ps=B2.puzzles(70011,3)
ex=[(p,B1.solve(p["nums"],p["target"])) for p in ps if B1.solve(p["nums"],p["target"])]
print(K.train_anchor(s,m,ex,pool[:3],1))
print('kl after (small, >0):', float(K.anchor_loss(s,m,pool[0])))
