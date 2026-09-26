# Base-only (adapter off) half of claude_chatgap_diag: P1/P2/C1 on CPU. Report only.
import sys, json, time
sys.path.insert(0, "/home/user/learner/scripts")
import claude_blurt1 as B1, claude_blurt2 as B2, claude_dl1_nights as D1, claude_panel382_run as P
import claude_chatgap_diag as G
BASE = "/root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc"
s = B2.Solver(BASE); m = s.model
out = sys.argv[1]; t0 = time.time()
for i, p in enumerate(G.chat_puzzles(40)):
    r = {"i": i, "side": "off", "nums": p["nums"], "target": p["target"]}
    p1 = s.answer(p, m); r["P1"] = {"reply": p1, "solved": bool(B1.check(p1, p["nums"], p["target"]))}
    p2 = G.free_puzzle(s, p, m); r["P2"] = {"reply": p2, "solved": bool(P.puzzle_solved(p2, p["nums"], p["target"]))}
    c1 = D1.free_answer(s, G.ask_text(p), m, 96); r["C1"] = {"reply": c1, "solved": bool(P.puzzle_solved(c1, p["nums"], p["target"]))}
    for k in ("P1", "P2", "C1"): r[k]["kind"] = G.kind(r[k]["reply"], r[k]["solved"])
    open(out, "a").write(json.dumps(r) + "\n"); print(i, round(time.time() - t0), flush=True)
