# Unregistered control on PRACTICE grids only: what rv-390's GUESS worker solves with an untrained (random-init) loop
# net, i.e. how much the code parts (checker + row/col candidate skip) do alone. Also KEEP (no guesses) for contrast.
import sys, json, time, torch
sys.path.insert(0, "/home/user/learner/scripts")
import claude_rv390 as W
M, R, E = W.mods()
seed = int(sys.argv[2])
torch.manual_seed(seed)
net = R.Net("loop").eval()
w = W.Worker(net, E, "cpu")
items = W.load(R, W.ROOT / "artifacts/claude-rv390-20260926/day", ["p-grids6", "p-grids7"])
out = {"init_seed": seed}
for name, its in items.items():
    t0 = time.time()
    d = W.day_pass(net, R, E, its, "cpu")
    unf = [it for it, r in zip(its, d) if not r["right"]]
    g = [w.guess(it)[0] for it in unf]
    g48 = sum(x["solved"] and x["rounds"] <= W.DAY_ROUNDS for x in g)
    out[name] = {"n": len(its), "day_right": sum(r["right"] for r in d), "unfinished": len(unf),
                 "guess480_solved": sum(x["solved"] for x in g), "solved_within_48": g48,
                 "guesses": sum(x["guesses"] for x in g), "sec": round(time.time() - t0)}
    print(name, json.dumps(out[name]), flush=True)
json.dump(out, open(sys.argv[1] + f"/randctl-init{seed}.json", "w"), indent=1)
