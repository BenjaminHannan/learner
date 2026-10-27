import json, sys
sys.path.insert(0, "/home/user/learner/scripts")
from pathlib import Path
import claude_gr4 as G4, claude_rt02g as G, claude_rsn358b2_bridge as B, claude_rt02d as RT
one_b = G.load_one_b(sys.argv[1]); cp = G4.Copier(one_b)
sm = Path("/home/user/learner/artifacts/claude-panel-rsn358b3-smoke-20260926")
ans = {r["id"]: r for r in map(json.loads, (sm / "answers.jsonl").read_text().splitlines())}
items = [("smoke", r["message"], ans[r["id"]]["puz"]) for r in map(json.loads, (sm / "panel.jsonl").read_text().splitlines())][:3]
items += [("fresh", q["text"], q["puz"]) for q in B.make_requests(487005, 6, 5, False)][:3]
items += [("nosquare", t, None) for t, _ in RT.dev_cases()][:3]
for kind, text, truth in items:
    r = cp.copy(text)
    print("=====", kind, "exact" if r["grid"] == truth else "WRONG")
    print("MSG:", text[:500].replace("\n", " | "))
    print("TRUTH:", truth)
    print("RAW:", r["raw"].replace("\n", " | "))
