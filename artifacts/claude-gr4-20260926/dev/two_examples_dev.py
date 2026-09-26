"""Scratch dev check (practice only): gr-4 plus two worked examples from gr-1's practice set in the chat."""
import json, sys, time
from collections import Counter
sys.path.insert(0, "/home/user/learner/scripts")
from pathlib import Path
import claude_gr4 as G4, claude_rt02g as G, claude_rsn358b2_bridge as B, claude_rt02d as RT
ROOT = Path("/home/user/learner")
tr = [json.loads(l) for l in (ROOT / "artifacts/claude-gr1-20260926/train/train.jsonl").read_text().splitlines()]
def show(grid):
    return "\n".join(" ".join(str(v) if v else "_" for v in row) for row in grid)
EX = [(tr[42]["text"], show(tr[42]["grid"])), (tr[7]["text"], "none")]
one_b = G.load_one_b(sys.argv[1]); cp = G4.Copier(one_b)
orig = cp.tok.apply_chat_template
def fewshot(msgs, **kw):
    pre = []
    for t, a in EX:
        pre += [{"role": "user", "content": G4.PROMPT.format(req=t)}, {"role": "assistant", "content": a}]
    return orig(pre + msgs, **kw)
cp.tok.apply_chat_template = fewshot
sm = ROOT / "artifacts/claude-panel-rsn358b3-smoke-20260926"
ans = {r["id"]: r for r in map(json.loads, (sm / "answers.jsonl").read_text().splitlines())}
items = [("smoke", r["message"], ans[r["id"]]["puz"]) for r in map(json.loads, (sm / "panel.jsonl").read_text().splitlines())]
for s in (4, 5, 6, 7):
    items += [("fresh", q["text"], q["puz"]) for q in B.make_requests(487000 + s, 6, s, False)]
items += [("nosquare", t, None) for t, _ in RT.dev_cases()]
by, keep = Counter(), []
for it in items:
    if by[it[0]] < 10:
        keep.append(it); by[it[0]] += 1
st, t0 = Counter(), time.time()
for kind, text, truth in keep:
    r = cp.copy(text)
    st[kind + "_n"] += 1
    st[kind + "_exact"] += int(r["grid"] == truth)
    st[kind + "_wrong"] += int(r["grid"] is not None and r["grid"] != truth)
    if r["grid"] != truth:
        print("MISS", kind, repr(r["raw"][:120]), flush=True)
st["seconds_per_message"] = round((time.time() - t0) / len(keep), 1)
print(json.dumps(dict(sorted(st.items()))))
